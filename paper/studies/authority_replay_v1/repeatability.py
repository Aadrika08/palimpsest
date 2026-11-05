"""Sequential fixed-protocol CPU continuation/replay drivers; no implicit retries.

Raw verifiers remain the sole comparison implementations. Fixture runners can be
injected for tests; the CLI always executes the production verifier processes.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from paper.studies.authority_replay_v1.common import (
    append_row, campaign_identity, declared_units, load_protocol, prepare_output_root,
    require, validate_finite, parse_json,
)

PROTOCOL = REPO / 'paper/studies/authority_replay_v1/protocol.json'
# Metadata, supervisor output and bounded logs share the ordinary unit budget.
PAYLOAD_LIMIT = 480 * 1024**2


def _json(path, value):
    validate_finite(value)
    path.write_text(json.dumps(value, allow_nan=False, sort_keys=True, indent=2) + '\n')


def _size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())


def _descendants(pid):
    """Include nested verifier workers, which create their own sessions."""
    result = set()
    try:
        children = Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
    except (FileNotFoundError, ProcessLookupError):
        return result
    for child in children:
        identifier = int(child)
        result.add(identifier)
        result.update(_descendants(identifier))
    return result


def _kill_tree(child):
    descendants = _descendants(child.pid)
    # Capture before killing the leader, which reparents isolated worker sessions.
    for pid in [child.pid, *descendants]:
        try:
            if os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGKILL)
            else:
                os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _process(command, output, *, timeout, max_bytes, minimum_free_bytes):
    """Kill the entire owner process group on timeout/resource crossing.

    Admission reserves the full unit allowance before launch. The lab verifier
    and execution verifiers additionally enforce pre-publication StorageBudget.
    Monitoring guards native logs; it is not a filesystem quota on those logs.
    """
    env = os.environ.copy()
    env.update(MUJOCO_GL='egl', MPLBACKEND='Agg', OMP_NUM_THREADS='2', CUDA_VISIBLE_DEVICES='')
    env['PYTHONPATH'] = os.pathsep.join((str(REPO), str(REPO / 'src'), str(REPO / 'scripts'), env.get('PYTHONPATH', '')))
    started = time.monotonic()
    # Verifiers require a fresh destination, so logs live in its parent.
    with (output.parent / 'stdout.log').open('wb') as stdout, (output.parent / 'stderr.log').open('wb') as stderr:
        child = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        status, reason = 'completed', None
        while child.poll() is None:
            if time.monotonic() - started >= timeout:
                status, reason = 'timeout', 'unit wall-clock cap'
            elif _size(output.parent) >= max_bytes:
                status, reason = 'failed', 'unit output cap'
            elif shutil.disk_usage(output.parent).free < minimum_free_bytes:
                status, reason = 'failed', 'filesystem free-space reserve'
            if reason:
                _kill_tree(child)
                break
            time.sleep(.05)
        code = child.wait()
    if code and status == 'completed':
        status = 'failed'
    return {'status': status, 'returncode': code, 'stop_reason': reason}


def _paired(report):
    continuation = report.get('continuation', {})
    pairs = {'branch': {'agreement': continuation.get('status') == 'passed',
                        'first_divergence': next(iter(continuation.get('divergences', [])), None),
                        'validated_fields': list(continuation.get('max_abs_errors', {})),
                        'executed_computation': {'controller_reexecuted': True, 'inference_executed': True}},
             'playback': {'agreement': report.get('playback', {}).get('mode') == 'playback',
                          'first_divergence': None,
                          'validated_fields': ['recording integrity', 'recorded transition'],
                          'executed_computation': {'controller_reexecuted': False, 'inference_executed': False}}}
    for mode, label in (('actions', 'action_replay'), ('policy', 'policy_replay')):
        raw = report.get('replays', {}).get(mode, {}).get('report', {})
        pairs[label] = {'agreement': raw.get('status') == 'passed'
                        and raw.get('controller_reexecuted') is (mode == 'policy')
                        and raw.get('inference_executed') is (mode == 'policy'),
                        'first_divergence': raw.get('first_divergence'),
                        'validated_fields': raw.get('comparison', {}),
                        'executed_computation': {k: raw.get(k) for k in ('controller_reexecuted', 'inference_executed')},
                        'raw': raw}
    return pairs


def _unit(kind, seed, output, identity, *, protocol=None, repo=REPO, assets=None, runner=_process, timeout=None):
    protocol = protocol or load_protocol(PROTOCOL)
    section = getattr(protocol, kind)
    require(type(seed) is int and seed in section['seeds'], 'undeclared seed')
    output = Path(output).resolve()
    prepare_output_root(output)
    started = time.monotonic()
    row = {'schema_version': 1, 'study_id': protocol.study_id, 'unit_id': f'{kind}/{seed}',
           'kind': kind, 'seed': seed, 'identity': identity, 'status': 'incomplete',
           'comparison_policy': protocol.comparison_policy, 'first_divergence': None,
           'refusal': None, 'paired_raw_values': {}, 'metrics': {'agreement': None}}
    if kind == 'replay':
        row['paired_raw_values'] = {name: {'agreement': None, 'first_divergence': None,
                                         'validated_fields': [], 'executed_computation': None}
                                    for name in section['conditions']}
    try:
        require(shutil.disk_usage(output).free >= protocol.resources['minimum_free_bytes'] +
                protocol.resources['ordinary_unit_max_output_bytes'], 'insufficient free-space reserve for unit admission')
        prefix = section['prefix_ticks']
        count = section['continuation_ticks'] if kind == 'continuation' else section['source_ticks'] - prefix
        script = 'verify_execution.py' if kind == 'continuation' else 'verify_lab.py'
        command = [sys.executable, str(Path(repo) / 'scripts' / script), '--repo', str(Path(repo).resolve()),
                   '--assets', str(Path(assets or REPO / 'data/assets/flynn').resolve()), '--controller', 'flynn',
                   '--seed', str(seed), '--prefix', str(prefix), '--continuation', str(count),
                   '--output', str(output / 'raw')]
        command += ['--device', 'cpu', '--timeout', '900', '--storage-max-bytes', str(448 * 1024**2),
                    '--minimum-free-bytes', str(protocol.resources['minimum_free_bytes'])] if kind == 'continuation' else ['--study']
        _json(output / 'invocation.json', {'command': command, 'python': sys.version, 'identity': identity,
              'environment': {k: os.environ.get(k) for k in ('PYTHONPATH', 'MUJOCO_GL', 'OMP_NUM_THREADS')},
              'source_ticks': prefix + count, 'prefix_ticks': prefix, 'continuation_ticks': count})
        process = runner(command, output / 'raw', timeout=min(protocol.resources['unit_timeout_seconds'], timeout) if timeout is not None else protocol.resources['unit_timeout_seconds'],
                         max_bytes=PAYLOAD_LIMIT, minimum_free_bytes=protocol.resources['minimum_free_bytes'])
        row['process'] = process
        row['status'] = process['status']
        report_path = output / 'raw/verification.json'
        report = parse_json(report_path.read_text()) if report_path.exists() else {}
        row['verifier_report'] = report
        if report:
            row['metrics'].update(snapshot_bytes=report.get('snapshot_bytes'),
                                  snapshot_sha256=report.get('snapshot_sha256'))
            if row['metrics']['snapshot_bytes'] is None and (output / 'raw/continuation.snapshot').exists():
                row['metrics']['snapshot_bytes'] = (output / 'raw/continuation.snapshot').stat().st_size
            require(report.get('prefix_ticks') == prefix and report.get('continuation_ticks') == count,
                    'verifier bounds missing or inconsistent')
            require(isinstance(row['metrics']['snapshot_bytes'], int) and
                    isinstance(report.get('snapshot_sha256'), str) and len(report['snapshot_sha256']) == 64,
                    'snapshot identity incomplete')
            if kind == 'replay':
                row['paired_raw_values'] = _paired(report)
                row['source'] = report.get('source')
                complete = all(p['validated_fields'] and p['executed_computation'] is not None
                               for p in row['paired_raw_values'].values())
                require(complete, 'replay comparison fields incomplete')
                row['metrics'].update(report.get('timings', {}))
                row['first_divergence'] = next((p['first_divergence'] for p in row['paired_raw_values'].values()
                                                if p['first_divergence']), None)
                agrees = all(p['agreement'] for p in row['paired_raw_values'].values())
            else:
                require(all(k in report for k in ('first_divergence', 'max_abs_errors', 'random_draws_match',
                            'source_event_prefix_unchanged', 'branch_identity_distinct', 'queued_command_idempotency')),
                        'continuation comparison fields incomplete')
                row['paired_raw_values'] = {'source_restored': report}
                row['first_divergence'] = report['first_divergence']
                agrees = report['status'] == 'passed'
            row['metrics']['agreement'] = agrees
            if (not agrees or report['status'] != 'passed') and row['status'] != 'timeout':
                row['status'] = 'failed'
        elif row['status'] == 'completed':
            raise ValueError('verifier completed without a comparison report')
    except Exception as exc:
        if row['status'] != 'timeout':
            row['status'] = 'refused' if 'admission' in str(exc) else 'failed'
        row['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        if row['status'] == 'refused':
            row['refusal'] = row['error']
    if row['first_divergence'] is not None:
        raw_divergence = row['first_divergence']
        row['first_divergence'] = {**raw_divergence,
            'field': raw_divergence.get('field', raw_divergence.get('component')),
            'tick': raw_divergence.get('tick')}
    row['metrics']['elapsed_seconds'] = time.monotonic() - started
    row['metrics']['output_bytes'] = _size(output)
    for _ in range(4):
        _json(output / 'row.json', row)
        measured = _size(output)
        if measured == row['metrics']['output_bytes']:
            break
        row['metrics']['output_bytes'] = measured
    _json(output / 'row.json', row)
    return row


def run_continuation_unit(seed: int, output: Path, identity: dict[str, object], **kwargs) -> dict[str, object]:
    return _unit('continuation', seed, output, identity, **kwargs)


def run_replay_unit(seed: int, output: Path, identity: dict[str, object], **kwargs) -> dict[str, object]:
    return _unit('replay', seed, output, identity, **kwargs)


def _campaign_deadline(root, identity, seconds):
    """Reuse one wall-clock deadline across driver invocations, never reset it."""
    path = root / 'campaign-clock.json'
    try:
        with path.open('x') as stream:
            now = time.time()
            json.dump({'identity': identity, 'started_unix': now, 'deadline_unix': now + seconds}, stream)
            stream.write('\n')
    except FileExistsError:
        pass
    clock = json.loads(path.read_text())
    require(clock['identity'] == identity, 'shared campaign clock identity drift')
    return clock['deadline_unix']


def run_campaign(kind, protocol, output, identity, *, repo=REPO, assets=None, protocol_path=PROTOCOL,
                 campaign_root=None, deadline=None):
    prepare_output_root(output)
    _json(output / 'identity.json', identity)
    campaign_root = Path(campaign_root or output.parent).resolve()
    require(output.resolve().is_relative_to(campaign_root), 'driver output must be within campaign root')
    persisted_deadline = _campaign_deadline(campaign_root, identity, protocol.resources['campaign_timeout_seconds'])
    deadline = persisted_deadline if deadline is None else min(deadline, persisted_deadline)
    stopped, rows = None, []
    for unit in declared_units(protocol):
        if unit['kind'] != kind:
            continue
        if time.time() >= deadline:
            stopped = 'campaign wall-clock cap'
        if _size(campaign_root) + protocol.resources['ordinary_unit_max_output_bytes'] > protocol.resources['campaign_max_output_bytes']:
            stopped = 'campaign output admission cap'
        if stopped:
            row = {'schema_version': 1, 'study_id': protocol.study_id, **unit, 'identity': identity,
                   'status': 'incomplete', 'metrics': {}, 'reason': stopped}
        else:
            row = _unit(kind, unit['seed'], output / f"seed-{unit['seed']}", identity,
                        protocol=protocol, repo=repo, assets=assets,
                        timeout=max(.001, deadline - time.time()))
            try:
                require(campaign_identity(repo, protocol_path, assets) == identity, 'campaign identity drift')
            except Exception as exc:
                row.update(status='failed', error={'type': 'IdentityDrift', 'message': str(exc)})
                stopped = 'campaign identity drift'
            if row['status'] in ('timeout', 'refused') or row.get('process', {}).get('stop_reason'):
                stopped = 'previous unit reached resource boundary'
        unit_row_path = output / f"seed-{unit['seed']}" / 'row.json'
        if unit_row_path.exists():
            _json(unit_row_path, row)
        append_row(output / 'rows.jsonl', row)
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('continuation', 'replay'), required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--campaign-root', type=Path, help='shared root for every study driver; defaults to output parent')
    parser.add_argument('--campaign-deadline-epoch', type=float, help='root-issued Unix deadline; otherwise reuse campaign-clock.json')
    args = parser.parse_args()
    protocol = load_protocol(args.protocol)
    identity = campaign_identity(REPO, args.protocol, args.assets)
    rows = run_campaign(args.kind, protocol, args.output, identity, assets=args.assets, protocol_path=args.protocol,
                        campaign_root=args.campaign_root, deadline=args.campaign_deadline_epoch)
    print(json.dumps({'kind': args.kind, 'rows': len(rows), 'completed': sum(r['status'] == 'completed' for r in rows)}))
    return int(any(r['status'] != 'completed' for r in rows))


if __name__ == '__main__':
    raise SystemExit(main())
