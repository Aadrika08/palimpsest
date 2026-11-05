"""Sequential fixed-protocol CPU continuation/replay drivers; no implicit retries.

Raw verifiers remain the sole comparison implementations. Fixture runners can be
injected for tests; the CLI always executes the production verifier processes.
"""
from __future__ import annotations
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from paper.studies.authority_replay_v1.common import (
    append_row, campaign_identity, declared_units, load_protocol, prepare_output_root,
    require, validate_finite, parse_json, sha256_file,
)

PROTOCOL = REPO / 'paper/studies/authority_replay_v1/protocol.json'
# Metadata, supervisor output and bounded logs share the ordinary unit budget.
PAYLOAD_LIMIT = 480 * 1024**2


def _json(path, value):
    validate_finite(value)
    path.write_text(json.dumps(value, allow_nan=False, sort_keys=True, indent=2) + '\n')


def _size(root):
    total = 0
    for path in root.rglob('*'):
        try:
            info = path.lstat()
        except (FileNotFoundError, ProcessLookupError):
            continue  # Owner atomically renamed/removed an unpublished staging file.
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
    return total


def _exec_unit(command_path, admission_fd):
    """Replace this pinned launcher only after its guardian authorizes execution."""
    try:
        require(os.read(admission_fd, 3) == b'GO\n', 'unit received no GO admission')
    finally:
        os.close(admission_fd)
    command = parse_json(command_path.read_text())
    os.execvp(command[0], command)


def _supervise_unit(command_path, result_path, coordinator_pid, admission_fd):
    """One private subreaper owns one unit, including detached grandchildren."""
    from paper.studies.authority_replay_v1.campaign import (
        _cleanup, _open_pidfd, _processes, _remember, _send_pidfd,
    )
    child, descriptor, known, result = None, None, {}, {}
    unit_read, unit_write = None, None
    stopped = []
    def record_error(exc, prefix=''):
        message = prefix + str(exc)
        if 'error' in result:
            result['error']['message'] += '; ' + message[:4096]
        else:
            result['error'] = {'type': type(exc).__name__, 'message': message[:4096]}
    def interrupted(number, frame):
        stopped.append(number)
    try:
        for number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(number, interrupted)
        libc = ctypes.CDLL(None, use_errno=True)
        require(libc.prctl(36, 1, 0, 0, 0) == 0, 'cannot enable private unit subreaper')
        require(libc.prctl(1, signal.SIGTERM, 0, 0, 0) == 0, 'cannot bind unit guardian parent death signal')
        require(os.getppid() == coordinator_pid, 'unit coordinator exited before admission')
        require(os.read(admission_fd, 3) == b'GO\n', 'unit guardian received no GO admission')
        require(not stopped, 'unit guardian stopped before launch')
        unit_read, unit_write = os.pipe()
        child = subprocess.Popen(
            [sys.executable, '-B', str(Path(__file__).resolve()), '--exec-unit', str(command_path), str(unit_read)],
            start_new_session=True, pass_fds=(unit_read,))
        os.close(unit_read)
        unit_read = None
        # The direct child is still unreaped, so it cannot be a recycled PID.
        descriptor = _open_pidfd(child.pid)
        initial = _processes().get(child.pid)
        require(initial is not None and initial[0] == os.getpid(), 'unit leader identity unavailable')
        known[child.pid] = {'start_ticks': initial[1], 'provenance': 'guardian_launched_unit',
                            'parent_pid': os.getpid()}
        require(not stopped, 'unit guardian stopped before unit admission')
        require(os.write(unit_write, b'GO\n') == 3, 'unit GO write incomplete')
        os.close(unit_write)
        unit_write = None
        # Preserve leader identity until ancestry discovery/cleanup is complete.
        while os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
            _remember(child, known, os.getpid())
            if stopped:
                break
            time.sleep(.01)
    except Exception as exc:
        record_error(exc)
    finally:
        for channel in (unit_read, unit_write):
            if channel is not None:
                os.close(channel)  # EOF prevents exec when ownership admission fails.
        os.close(admission_fd)
        for number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(number, signal.SIG_IGN)
        if child is not None:
            drain_needed = False
            try:
                _cleanup(child, known, os.getpid())
            except Exception as exc:
                drain_needed = True
                record_error(exc, 'unit ownership cleanup failed: ')
            finally:
                # Even failed identity acquisition/cleanup must reap the direct
                # child. Popen only signals its own unreaped child; no group or
                # discovered numeric PID grants authority in this fallback.
                try:
                    if child.returncode is None:
                        drain_needed = True
                        if descriptor is not None:
                            _send_pidfd(descriptor, signal.SIGKILL)
                        else:
                            child.kill()
                except Exception as exc:
                    record_error(exc, 'direct unit cleanup failed: ')
                    child.kill()
                finally:
                    result['returncode'] = child.wait()
                if drain_needed:
                    # Killing/reaping the direct child can adopt grandchildren.
                    # Re-discover these only through this private guardian and
                    # the retained start identities; preserve any primary error.
                    try:
                        _cleanup(child, known, os.getpid())
                    except Exception as exc:
                        record_error(exc, 'post-reap ownership cleanup failed: ')
        if descriptor is not None:
            os.close(descriptor)
        _json(result_path, result)
    return int('error' in result)


def _process(command, output, *, timeout, max_bytes, minimum_free_bytes):
    """Monitor a privately owned unit without signaling recycled PID/PGIDs.

    The private guardian admits the unit only after its caller pins the guardian.
    It retains the leader unreaped and uses start-verified pidfds for descendants,
    including new sessions adopted by its private subreaper. Native log monitoring
    remains a cooperative resource guard rather than a filesystem quota.
    """
    from paper.studies.authority_replay_v1.campaign import _open_pidfd, _send_pidfd
    env = os.environ.copy()
    env.update(MUJOCO_GL='egl', MPLBACKEND='Agg', OMP_NUM_THREADS='2', CUDA_VISIBLE_DEVICES='')
    env['PYTHONPATH'] = os.pathsep.join((str(REPO), str(REPO / 'src'), str(REPO / 'scripts'), env.get('PYTHONPATH', '')))
    started = time.monotonic()
    status, reason, error, code = 'completed', None, None, None
    # Control records are private and removed on return; verifier logs and raw
    # output retain their existing paths. Their temporary bytes count in _size.
    with tempfile.TemporaryDirectory(prefix='.unit-supervision-', dir=output.parent) as control:
        command_path, result_path = Path(control) / 'command.json', Path(control) / 'result.json'
        _json(command_path, command)
        read_fd, write_fd = os.pipe()
        child, descriptor, guardian_code = None, None, None
        with (output.parent / 'stdout.log').open('wb') as stdout, (output.parent / 'stderr.log').open('wb') as stderr:
            try:
                child = subprocess.Popen(
                    [sys.executable, '-B', str(Path(__file__).resolve()), '--supervise-unit',
                     str(command_path), str(result_path), str(os.getpid()), str(read_fd)],
                    env=env, stdout=stdout, stderr=stderr, pass_fds=(read_fd,))
                os.close(read_fd)
                read_fd = None
                descriptor = _open_pidfd(child.pid)
                require(os.write(write_fd, b'GO\n') == 3, 'unit guardian GO write incomplete')
                os.close(write_fd)
                write_fd = None
                while os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
                    if time.monotonic() - started >= timeout:
                        status, reason = 'timeout', 'unit wall-clock cap'
                    elif _size(output.parent) >= max_bytes:
                        status, reason = 'failed', 'unit output cap'
                    elif shutil.disk_usage(output.parent).free < minimum_free_bytes:
                        status, reason = 'failed', 'filesystem free-space reserve'
                    if reason:
                        break
                    time.sleep(.05)
                # Include fast publication and resource crossings between the
                # last running poll and guardian exit, using the same limits.
                if reason is None:
                    if time.monotonic() - started >= timeout:
                        status, reason = 'timeout', 'unit wall-clock cap'
                    elif _size(output.parent) >= max_bytes:
                        status, reason = 'failed', 'unit output cap'
                    elif shutil.disk_usage(output.parent).free < minimum_free_bytes:
                        status, reason = 'failed', 'filesystem free-space reserve'
            except Exception as exc:
                status, reason = 'failed', 'monitor failure'
                error = {'type': type(exc).__name__, 'message': str(exc)[:4096]}
            finally:
                for channel in (read_fd, write_fd):
                    if channel is not None:
                        os.close(channel)  # EOF forbids an unadmitted unit launch.
                if child is not None:
                    try:
                        if descriptor is not None:
                            _send_pidfd(descriptor, signal.SIGTERM)
                        guardian_code = child.wait(timeout=5)
                    except Exception as exc:
                        if status == 'completed':
                            status, reason = 'failed', 'supervisor cleanup failure'
                        error = error or {'type': type(exc).__name__, 'message': str(exc)[:4096]}
                        try:
                            # A failed pidfd send must still let the guardian
                            # clean its unit. This sole waiter's direct Popen
                            # safely handles an already-exited guardian.
                            child.terminate()
                            guardian_code = child.wait(timeout=5)
                        except Exception:
                            child.kill()
                            guardian_code = child.wait()
                    finally:
                        if descriptor is not None:
                            os.close(descriptor)
        try:
            require(result_path.exists(), 'unit supervisor record unavailable')
            supervised = parse_json(result_path.read_text())
            code = supervised.get('returncode')
            if supervised.get('error'):
                failure = supervised['error']
                if status == 'completed':
                    status, reason = 'failed', 'unit ownership cleanup failure'
                if error:
                    error['message'] += '; unit supervisor: ' + failure['message']
                else:
                    error = failure
            else:
                require(type(code) is int and guardian_code == 0, 'unit supervisor did not complete cleanup')
        except Exception as exc:
            if status == 'completed':
                status, reason = 'failed', 'unit supervisor record unavailable'
            failure = {'type': type(exc).__name__, 'message': str(exc)[:4096]}
            if error:
                error['message'] += '; unit supervisor: ' + failure['message']
            else:
                error = failure
    if code and status == 'completed':
        status = 'failed'
    return {'status': status, 'returncode': code, 'stop_reason': reason, 'error': error}


def _paired(report, expected_ticks):
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
                        and raw.get('mode') == mode
                        and type(raw.get('compared_ticks')) is int and raw['compared_ticks'] == expected_ticks
                        and isinstance(report.get('source_run_id'), str)
                        and raw.get('source_run_id') == report['source_run_id']
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
        row['resource_boundary'] = report.get('resource_boundary')
        if report:
            if report.get('status') == 'passed':
                require(report.get('finite_scientific_arrays') is True, 'finite scientific validation missing')
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
                source = report.get('source', {})
                source_path = Path(source.get('run_path', '')).resolve()
                require(source_path.is_relative_to(output / 'raw'), 'source must belong to this fresh unit')
                manifest_path = source_path / 'recording/manifest.json'
                manifest = parse_json(manifest_path.read_text())
                require(manifest.get('run_id') == report.get('source_run_id') == source_path.name,
                        'recorded replay source identity differs')
                require(manifest.get('status') == 'completed' and manifest.get('recorded_ticks') == section['source_ticks']
                        and manifest.get('controller') == 'flynn' and manifest.get('requested_device') == 'cpu',
                        'recorded replay source scope differs')
                row['source_manifest_sha256'] = sha256_file(manifest_path)
                row['paired_raw_values'] = _paired(report, section['source_ticks'])
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
    try:
        row['metrics']['output_bytes'] = _size(output)
    except OSError as exc:
        row.update(status='failed', error={'type': type(exc).__name__, 'message': str(exc)[:4096]})
        row['metrics']['output_bytes'] = None
    for _ in range(4):
        _json(output / 'row.json', row)
        try:
            measured = _size(output)
        except OSError:
            break
        if measured == row['metrics']['output_bytes']:
            break
        row['metrics']['output_bytes'] = measured
    if (row['metrics']['output_bytes'] is not None and
            row['metrics']['output_bytes'] > protocol.resources['ordinary_unit_max_output_bytes']):
        row.update(status='failed', resource_boundary={'type': 'OutputCap', 'message': 'final unit inventory exceeded cap'})
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
            if (row['status'] in ('timeout', 'refused') or row.get('process', {}).get('stop_reason')
                    or row.get('resource_boundary') or row.get('verifier_report', {}).get('resource_boundary')):
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
    if len(sys.argv) == 4 and sys.argv[1] == '--exec-unit':
        raise SystemExit(_exec_unit(Path(sys.argv[2]), int(sys.argv[3])))
    if len(sys.argv) == 6 and sys.argv[1] == '--supervise-unit':
        raise SystemExit(_supervise_unit(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])))
    raise SystemExit(main())
