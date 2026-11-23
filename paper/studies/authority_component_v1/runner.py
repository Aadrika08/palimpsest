"""Component-wise restore ablation for the authority_replay_v1 S1 finding.

Each arm restores a hybrid snapshot (named components from the source boundary,
the rest from the post-step donor) into a fresh engine via Engine.restore_branch
and steps the horizon. See protocol.json. Real runs require an owner GO record.
"""
from __future__ import annotations

import argparse
import copy
import json
import resource
import subprocess
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'src'))
from paper.studies.authority_replay_v1.common import (  # noqa: E402
    append_row, campaign_identity, prepare_output_root, read_rows, require, sha256_file)

PROTOCOL = Path(__file__).with_name('protocol.json')
PHYSICS_KEYS = ('native_data', 'native_sha256', 'integration')
POLICY_PARTS = {'controller_hidden': ('hidden', 'failure_diagnostics'),
                'controller_retina': ('left', 'right')}
COMPONENTS = ('physics', 'environment', 'observation', 'controller_hidden',
              'controller_retina', 'rng', 'application')
CONTROLLER_INPUTS = frozenset({'observation', 'controller_hidden', 'controller_retina'})
INVARIANT = ('schema_version', 'identity', 'integration_enum', 'teacher')


def arms():
    """Ordered (name, components from source, components under test). Fixed: 16 per seed."""
    every = frozenset(COMPONENTS)
    out = [('full', every, frozenset()), ('pose_only', frozenset({'physics'}), every - {'physics'})]
    out += [(f'loo:{c}', every - {c}, frozenset({c})) for c in COMPONENTS]
    out += [(f'add:{c}', frozenset({'physics', c}), frozenset({c})) for c in COMPONENTS[1:]]
    out.append(('add:controller_inputs', frozenset({'physics'}) | CONTROLLER_INPUTS, CONTROLLER_INPUTS))
    return out


def _parts(snapshot, component):
    if component == 'physics':
        return {k: snapshot[k] for k in PHYSICS_KEYS}
    if component in POLICY_PARTS:
        return {k: snapshot['policy'][k] for k in POLICY_PARTS[component]}
    return {component: snapshot[component]}


def hybrid(source, donor, from_source):
    """New snapshot: components in from_source come from source, the rest from donor."""
    require(set(from_source) <= set(COMPONENTS), f'unknown component: {set(from_source) - set(COMPONENTS)}')
    out = copy.deepcopy(donor)
    for component in from_source:
        for key, value in copy.deepcopy(_parts(source, component)).items():
            if component in POLICY_PARTS:
                out['policy'][key] = value
            else:
                out[key] = value
    return out


def component_digests(snapshot):
    from palimpsest.snapshots import state_digest
    return {c: state_digest(_parts(snapshot, c)) for c in COMPONENTS}


def exercised(source_digests, donor_digests, tested):
    """None for the reference arm; else whether any component under test differs source vs donor."""
    if not tested:
        return None
    return any(source_digests[c] != donor_digests[c] for c in tested)


def should_start(used, worst, resources):
    """Stop rule: start a seed only if used + worst seen (or the seed timeout) fits the ceiling."""
    return used + (worst if worst is not None else resources['seed_timeout_seconds']) <= resources['study_ceiling_cpu_seconds']


def _verdict(row, field):
    if row['status'] != 'completed':
        return row['status']
    if row['restore_refused']:
        return 'refused'
    if row['exercised'] is False:
        return 'not_exercised'
    return row[field]


def classify(row_by_arm):
    """Per-seed analysis from protocol.analysis. Rows keyed by arm name."""
    full, pose = row_by_arm['full'], row_by_arm['pose_only']
    valid = (full['status'] == 'completed' and not full['restore_refused']
             and full['scientific_first_divergence'] is None and full['application_first_divergence'] is None)
    pose_changed = valid and pose['status'] == 'completed' and pose['first_action_changed'] is True
    result = {'h1_full_agrees': valid, 'h2_pose_only_changes_first_action': _verdict(pose, 'first_action_changed'),
              'necessary_first_action': {}, 'necessary_horizon': {}, 'repairs_first_action': {}}
    for c in COMPONENTS:
        loo = row_by_arm[f'loo:{c}']
        result['necessary_first_action'][c] = _verdict(loo, 'first_action_changed') if valid else None
        horizon = _verdict(loo, 'scientific_first_divergence') if valid else None
        result['necessary_horizon'][c] = None if not valid else horizon if isinstance(horizon, str) else horizon is not None
    for name in [n for n, _, _ in arms() if n.startswith('add:')]:
        verdict = _verdict(row_by_arm[name], 'first_action_changed') if pose_changed else None
        result['repairs_first_action'][name[4:]] = (not verdict) if isinstance(verdict, bool) else verdict
    return result


def _first_action_tick(expected, actual):
    from paper.studies.authority_replay_v1.fault_matrix import first_divergence
    found = first_divergence([{'action': r['action']} for r in expected[:len(actual)]],
                             [{'action': r['action']} for r in actual])
    return None if found is None else found['tick']


def _divergences(expected, actual):
    from paper.studies.authority_replay_v1.fault_matrix import first_divergence
    sci = lambda rows: [{k: v for k, v in r.items() if k != 'revision'} for r in rows]
    app = lambda rows: [{'revision': r['revision']} for r in rows]
    return first_divergence(sci(expected), sci(actual)), first_divergence(app(expected), app(actual))


def _step(engine, rows, ticks):
    """One horizon step; refuses to record a tick that did not advance (terminated episodes)."""
    from paper.studies.authority_replay_v1.fault_matrix import _command, _tick_state
    before = engine.total_tick
    _command(engine, 'step')
    require(engine.total_tick == before + 1, f'tick did not advance (phase {engine.phase})')
    rows.append(_tick_state(engine))
    ticks.append({'total_tick': engine.total_tick, 'phase': engine.phase})


def placeholder(seed, name, from_source, status, reason):
    tested = dict((n, x) for n, _, x in arms())[name]
    return {'unit_id': f'seed-{seed}/{name}', 'seed': seed, 'arm': name, 'run_id': None, 'from_source': sorted(from_source),
            'tested': sorted(tested), 'status': status, 'reason': reason, 'exercised': None, 'restore_refused': False,
            'refusal': None, 'ticks': 0, 'tick_phases': [], 'wall_seconds': None, 'first_action_changed': None, 'first_action_divergence_tick': None,
            'scientific_first_divergence': None, 'application_first_divergence': None}


def run_seed(seed, output, repo, assets, horizon, prefix):
    """One seed: source, donor, expected ticks, then fresh-engine arms. Rows go to output/rows.jsonl as they finish."""
    import numpy as np
    from palimpsest.snapshots import state_digest
    from paper.studies.authority_replay_v1.fault_matrix import _capture, _command, _open
    output.mkdir()
    runs = {'source': uuid.uuid4().hex}
    engine = _open(repo, assets, output / runs['source'], seed)
    expected, source_ticks = [], []
    try:
        for _ in range(prefix):
            _command(engine, 'step')
        source = _capture(engine)
        _step(engine, expected, source_ticks)
        donor = _capture(engine)
        for _ in range(horizon - 1):
            _step(engine, expected, source_ticks)
    finally:
        engine.close()
    for key in INVARIANT:
        require(state_digest(source[key]) == state_digest(donor[key]), f'source/donor invariant differs: {key}')
    src_d, don_d = component_digests(source), component_digests(donor)
    np.savez(output / 'expected.npz', **{f'{t}__{k}': v for t, row in enumerate(expected) for k, v in row.items()})
    precheck = {'source': src_d, 'donor': don_d, 'differs': {c: src_d[c] != don_d[c] for c in COMPONENTS},
                'pending_commands': {'source': len(source['application']['pending_commands']),
                                     'donor': len(donor['application']['pending_commands'])},
                'source_ticks': source_ticks, 'runs': runs, 'horizon_ticks': horizon, 'prefix_ticks': prefix}
    (output / 'precheck.json').write_text(json.dumps(precheck, indent=1, sort_keys=True))
    for index, (name, from_source, tested) in enumerate(arms()):
        runs[name] = uuid.uuid4().hex
        (output / 'precheck.json').write_text(json.dumps(precheck, indent=1, sort_keys=True))
        actual, ticks, refused, failure, started = [], [], None, None, time.monotonic()
        try:
            engine = _open(repo, assets, output / runs[name], seed)
            try:
                try:
                    engine.restore_branch(hybrid(source, donor, from_source))
                except Exception as error:  # a restore refusal is a retained result, not a lost seed
                    refused = f'{type(error).__name__}: {error}'[:512]
                if refused is None:
                    for _ in range(horizon):
                        _step(engine, actual, ticks)
            finally:
                engine.close()
        except Exception as error:  # isolate one arm's runtime failure from the rest of the seed
            failure = f'{type(error).__name__}: {error}'[:512]
        np.savez(output / f'arm-{index:02d}.npz', **{f'{t}__{k}': v for t, row in enumerate(actual) for k, v in row.items()})
        sci, app = _divergences(expected, actual) if actual else (None, None)
        tick = _first_action_tick(expected, actual) if actual else None
        complete = failure is None and (refused is not None or len(actual) == horizon)
        append_row(output / 'rows.jsonl', {
            'unit_id': f'seed-{seed}/{name}', 'seed': seed, 'arm': name, 'run_id': runs[name],
            'from_source': sorted(from_source), 'tested': sorted(tested),
            'status': 'completed' if complete else 'runtime_failure', 'reason': failure,
            'exercised': exercised(src_d, don_d, tested), 'restore_refused': refused is not None, 'refusal': refused,
            'ticks': len(actual), 'tick_phases': ticks, 'wall_seconds': time.monotonic() - started,
            'horizon_ticks': horizon, 'first_action_changed': None if not actual else tick == 0,
            'first_action_divergence_tick': tick,
            'scientific_first_divergence': sci, 'application_first_divergence': app})
    rows = read_rows(output / 'rows.jsonl')
    (output / 'analysis.json').write_text(json.dumps(classify({r['arm']: r for r in rows}), indent=1, sort_keys=True))
    (output / 'child.json').write_text(json.dumps({'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
    return rows


def _go(protocol_sha):
    path = Path(__file__).with_name('go.json')
    require(path.is_file(), 'no owner run GO: go.json missing')
    go = json.loads(path.read_text())
    require(go.get('go') is True and go.get('protocol_sha256') == protocol_sha, 'go.json does not approve this protocol hash')
    require(all(isinstance(go.get(k), str) and go[k] for k in ('by', 'date', 'words')), 'go.json needs by, date and words')
    return go


def collect_seed(seed, seed_dir, status, reason):
    """Child rows, padded with placeholders so every seed contributes exactly len(arms()) rows."""
    names = {n for n, _, _ in arms()}
    try:
        rows = read_rows(seed_dir / 'rows.jsonl') if (seed_dir / 'rows.jsonl').is_file() else []
    except ValueError:  # a child killed mid-append; the raw file stays on disk for inspection
        rows, status, reason = [], 'failed', f'unreadable child rows; {reason}'
    rows = [r for r in rows if r.get('arm') in names and r.get('seed') == seed]
    done = {r['arm'] for r in rows}
    rows += [placeholder(seed, name, src, status, reason) for name, src, _ in arms() if name not in done]
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed-child', type=int)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--horizon', type=int, help='seed-child only: smoke override; the study uses the protocol value')
    parser.add_argument('--prefix', type=int, help='seed-child only: smoke override; the study uses the protocol value')
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL.read_text())
    if args.seed_child is not None:
        smoke = args.horizon is not None or args.prefix is not None
        require(not (smoke and args.seed_child in protocol['seeds']), 'smoke overrides are refused on study seeds')
        run_seed(args.seed_child, args.output, args.repo, args.assets,
                 protocol['horizon_ticks'] if args.horizon is None else args.horizon,
                 protocol['prefix_ticks'] if args.prefix is None else args.prefix)
        return 0
    require(args.horizon is None and args.prefix is None, '--horizon/--prefix are smoke-only seed-child overrides')
    from paper.studies.authority_replay_v1 import fault_matrix
    protocol_sha = sha256_file(PROTOCOL)
    go = _go(protocol_sha)
    prepare_output_root(args.output)
    identity = campaign_identity(REPO, PROTOCOL, fault_matrix.ASSETS)
    (args.output / 'identity.json').write_text(json.dumps(
        {**identity, 'go': go, 'protocol_sha256': protocol_sha, 'python': sys.executable}, indent=1))
    repo, assets = fault_matrix._copy_runtime(args.output)
    res = protocol['resources']
    used, worst, log, stopped = 0.0, None, [], None

    def account():
        own, kids = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
        total = own.ru_utime + own.ru_stime + kids.ru_utime + kids.ru_stime
        (args.output / 'cpu.json').write_text(json.dumps(
            {'seed_cpu_seconds': used, 'total_cpu_seconds_including_parent': total, 'seeds': log}, indent=1))
        return total

    for seed in protocol['seeds']:
        seed_dir = args.output / f'seed-{seed}'
        if stopped or not should_start(used, worst, res):
            stopped = stopped or 'ceiling'
            log.append({'seed': seed, 'status': 'not_started', 'reason': stopped})
            for row in collect_seed(seed, seed_dir, 'not_started', stopped):
                append_row(args.output / 'rows.jsonl', row)
            account()
            continue
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        start, status, reason = time.monotonic(), 'completed', None
        command = [sys.executable, '-B', __file__, '--output', str(seed_dir), '--seed-child', str(seed),
                   '--repo', str(repo), '--assets', str(assets)]
        try:
            done = subprocess.run(command, capture_output=True, text=True, errors='replace', timeout=res['seed_timeout_seconds'])
            (args.output / f'seed-{seed}.stderr').write_text(done.stderr)
            if done.returncode != 0:
                status, reason = 'failed', f'child exit {done.returncode}'
        except subprocess.TimeoutExpired as error:
            (args.output / f'seed-{seed}.stderr').write_text(error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else str(error.stderr or ''))
            status, reason, stopped = 'timeout', 'seed timeout', 'previous seed timed out'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
        used, worst = used + cpu, max(worst or 0.0, cpu)
        log.append({'seed': seed, 'status': status, 'reason': reason, 'cpu_seconds': cpu, 'wall_seconds': time.monotonic() - start})
        for row in collect_seed(seed, seed_dir, status, reason):
            append_row(args.output / 'rows.jsonl', row)
        if campaign_identity(REPO, PROTOCOL, fault_matrix.ASSETS) != identity:
            stopped = 'identity drift'
            log[-1]['identity_drift_after'] = True
        account()
    # ponytail: no automatic retry by design (protocol stop rules); failed seeds stay as retained rows.
    drift = campaign_identity(REPO, PROTOCOL, fault_matrix.ASSETS) != identity
    total = account()
    print(json.dumps({'seed_cpu_seconds': used, 'total_cpu_seconds': total, 'identity_drift': drift, 'seeds': log}))
    return int(drift or any(s['status'] != 'completed' for s in log))


if __name__ == '__main__':
    raise SystemExit(main())
