"""Bounded semantic fault injections. Runtime units execute full CPU FLYNN in fresh processes.

A run_fault_case argument must be narrowed to one declared seed/variant/condition.
The CLI expands the frozen descriptors; --fixture-only is verification, never a
result campaign. All mutation targets are copies below the exclusive output root.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'src'))
from paper.studies.authority_replay_v1.common import (
    FaultCase, append_row, campaign_identity, declared_units, load_protocol,
    prepare_output_root, require, sha256_file,
)

# A worktree can share the initialized, read-only main-checkout inputs.
MAIN_REPO = Path(subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', '--git-common-dir'], text=True).strip())
if not MAIN_REPO.is_absolute():
    MAIN_REPO = REPO / MAIN_REPO
MAIN_REPO = MAIN_REPO.resolve().parent
ASSETS = MAIN_REPO / 'data/assets/flynn'
FIXTURE_SOURCE = REPO / 'paper/studies/authority_replay_v1/protocol.json'
CAMPAIGN_ROOT = None
CAMPAIGN_DEADLINE_EPOCH = None


def _json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def naive_accepts(case_id, trace):
    """Evaluate the named deliberately weak predicate on the very same trace."""
    flag = lambda key: trace.get(key) is True
    predicates = {
        'A1': lambda: flag('request_accepted') or flag('obstacle_visible'),
        'A2': lambda: flag('request_parsed'),
        'A3': lambda: trace.get('accepted_requests', 0) >= 2,
        'R1': lambda: flag('viewable'),
        'R2': lambda: flag('trajectory_matches') or flag('final_state_matches'),
        'S1': lambda: flag('pose_restored') and flag('continued'),
        'S2': lambda: flag('snapshot_readable') and flag('process_progress'),
        'D1': lambda: flag('initial_setup_succeeded'),
        'D2': lambda: flag('shape_matches'),
        'C1': lambda: flag('start_hash_matches'), 'C2': lambda: flag('exit_hash_matches'),
        'C3': lambda: flag('protected_content_unchanged'),
        'P1': lambda: flag('output_exists') or flag('some_bytes_parse'),
        'B1': lambda: flag('pose_copies_completed'),
        'B2': lambda: flag('reset_pose_copy_completed'),
        'E1': lambda: flag('write_attempted') or flag('prefix_exists'),
        'E2': lambda: flag('producer_returned'),
        'E3': lambda: flag('process_continued') or flag('output_exists'),
    }
    return bool(predicates[case_id]())


def classify_outcome(trace, condition):
    outcome = trace['semantic_outcome']
    benign = condition in ('benign', 'benign_control')
    return {'silent_acceptance': outcome == 'accepted' and trace['semantic_invalid'],
            'explicit_detection': not benign and outcome in ('refused', 'detected'),
            'correct_recovery': not benign and outcome == 'recovered',
            'benign_false_rejection': benign and outcome in ('refused', 'detected')}


def first_divergence(expected, actual):
    """Stable field/tick order; exact discrete state, frozen tolerant float32 state."""
    import numpy as np
    for tick, (left, right) in enumerate(zip(expected, actual)):
        if set(left) != set(right):
            return {'field': 'fields', 'tick': tick, 'reason': 'keys'}
        for field in sorted(left):
            a, b = np.asarray(left[field]), np.asarray(right[field])
            if a.shape != b.shape or a.dtype != b.dtype:
                return {'field': field, 'tick': tick, 'reason': 'shape/dtype'}
            if a.dtype.kind in 'fc' and (not np.isfinite(a).all() or not np.isfinite(b).all()):
                return {'field': field, 'tick': tick, 'reason': 'nonfinite'}
            same = np.allclose(a, b, atol=1e-6, rtol=1e-6) if a.dtype.kind in 'fc' else np.array_equal(a, b)
            if not same:
                return {'field': field, 'tick': tick, 'reason': 'value'}
    if len(expected) != len(actual):
        return {'field': 'ticks', 'tick': min(len(expected), len(actual)), 'reason': 'length'}
    return None


def _custody(case, output):
    from palimpsest.puck_retained_installation import AdmissionInputs
    protected = output / 'copied-custody'
    protected.mkdir()
    leaf = protected / 'held.txt'
    shutil.copyfile(FIXTURE_SOURCE, leaf)
    initial = sha256_file(leaf)
    descriptor = {'path': leaf.name, 'size_bytes': leaf.stat().st_size, 'sha256': initial}
    held = AdmissionInputs(protected.resolve(), [descriptor], time.monotonic() + 30)
    detected = poisoned = False
    error = None
    try:
        with held:
            if case.id == 'C1':
                replacement = output / 'replacement.txt'
                replacement.write_bytes(leaf.read_bytes())
                replacement.replace(leaf)
            elif case.id == 'C2':
                data = leaf.read_bytes()
                leaf.write_bytes(b'changed bytes')
                leaf.write_bytes(data)
            else:
                sibling = output / 'unrelated-sibling'
                operation = case.variants[0]
                if operation.endswith('1'):
                    sibling.write_bytes(b'unrelated')
                elif operation.endswith('2'):
                    sibling.mkdir()
                else:
                    sibling.write_bytes(b'unrelated')
                    sibling.unlink()
            held.recheck()
    except (ValueError, OSError, RuntimeError) as exc:
        detected, error = True, str(exc)
    try:
        held.read(leaf.name, leaf.stat().st_size)
    except RuntimeError:
        poisoned = True
    return {'start_hash_matches': initial == descriptor['sha256'], 'exit_hash_matches': sha256_file(leaf) == initial,
            'protected_content_unchanged': sha256_file(leaf) == initial, 'context_poisoned_or_closed': poisoned,
            'error': error, 'semantic_invalid': case.id != 'C3',
            'semantic_outcome': 'detected' if detected else 'accepted', 'retained_prefix_valid': True}


def _quota(case, output):
    from palimpsest import records
    from palimpsest.storage import StorageBudget, StorageLimits
    size = [128, 4096, 65536][int(case.variants[0][-1]) - 1]
    run = output / 'recording'
    writer = records.RunWriter(run, {})
    used = sum(p.stat().st_size for p in run.rglob('*') if p.is_file())
    event_size = len((records._json({'sequence': 0, 'kind': 'payload', 'payload': 'x' * size}) + '\n').encode())
    cap = used + event_size - 1
    budget = StorageBudget((run,), StorageLimits(max_bytes=cap, min_free_bytes=0))
    writer.storage_budget = budget
    caught = None
    try:
        writer.event('payload', payload='x' * size)
    except RuntimeError as exc:
        caught = str(exc)
    finally:
        writer.close()
    return {'write_attempted': True, 'prefix_exists': run.exists(), 'cap_bytes': cap,
            'required_bytes': used + event_size, 'used_bytes': budget.usage()['used_bytes'], 'error': caught,
            'semantic_invalid': True, 'semantic_outcome': 'refused' if caught else 'accepted',
            'retained_prefix_valid': list(records.iter_ticks(run)) == []}


def _queue(case, output):
    from palimpsest.records import RunWriter
    bound = int(case.variants[0][-1])
    gate, entered = threading.Event(), threading.Event()
    writer = RunWriter(output / 'recording', {})
    writer.start_background(max_items=bound)
    real_fsync = os.fsync
    def blocked(fd):
        entered.set()
        if not gate.wait(10):
            raise RuntimeError('queue injection gate timed out')
        real_fsync(fd)
    errors = []
    count = bound + 4
    def produce():
        try:
            for i in range(count):
                writer.event('accepted', index=i)
        except BaseException as exc:
            errors.append(str(exc))
    try:
        with patch('palimpsest.records.os.fsync', blocked):
            producer = threading.Thread(target=produce)
            producer.start()
            require(entered.wait(5), 'writer did not enter fsync')
            deadline = time.monotonic() + 5
            while writer.background_stats()['backpressure_events'] == 0 and time.monotonic() < deadline:
                time.sleep(.001)
            during = writer.background_stats()
            gate.set()
            producer.join(10)
            require(not producer.is_alive() and not errors, f'producer failed: {errors}')
            writer.finish({})
    finally:
        gate.set()
        writer.close()
    retained = [json.loads(line) for line in (output / 'recording/events.jsonl').read_text().splitlines()]
    stats = writer.background_stats()
    recovered = (len(retained) == count and [e['index'] for e in retained] == list(range(count))
                 and stats['backpressure_events'] >= 1 and during['queued_items'] <= bound)
    return {'producer_returned': True, 'accepted_items': count, 'retained_items': len(retained),
            'queue_bound': bound, 'stats': stats, 'semantic_invalid': True,
            'semantic_outcome': 'recovered' if recovered else 'accepted', 'retained_prefix_valid': recovered}


def _writer_error(case, output):
    import numpy as np
    from palimpsest.records import RunWriter, iter_ticks
    writer = RunWriter(output / 'recording', {})
    for tick in range(32):
        writer.tick(0, tick, action=np.array([tick], np.float32))
    original = writer._events
    calls = 0
    variant = case.variants[0]
    class FaultingStream:
        def __getattr__(self, key):
            return getattr(original, key)
        def write(self, value):
            if variant == 'write':
                fail()
            return original.write(value)
        def flush(self):
            if variant == 'flush':
                fail()
            return original.flush()
    def fail():
        nonlocal calls
        calls += 1
        raise OSError('injected ' + variant + ' failure')
    writer._events = FaultingStream()
    real_fsync = os.fsync
    def fsync(fd):
        if fd == original.fileno():
            fail()
        return real_fsync(fd)
    caught = late = False
    try:
        with patch('palimpsest.records.os.fsync', fsync if variant == 'fsync' else real_fsync):
            try:
                writer.event('fault')
            except OSError:
                caught = True
            try:
                writer.event('must-not-retry')
            except ValueError:
                late = True
    finally:
        writer.close()
    ticks = list(iter_ticks(output / 'recording'))
    return {'output_exists': writer.path.exists(), 'process_continued': True, 'failure_calls': calls,
            'late_rejected': late, 'closed': original.closed, 'published_ticks': len(ticks),
            'semantic_invalid': True, 'semantic_outcome': 'detected' if caught and late else 'accepted',
            'retained_prefix_valid': len(ticks) == 32}


def _publication_child(output, variant):
    """Terminate at actual writer publication boundaries, bypassing cleanup."""
    import numpy as np
    from palimpsest import records
    writer = records.RunWriter(output / 'recording', {})
    # Deliberately weak direct-append writer sees exactly the same tick stream;
    # each parseable line is treated as published without a terminal manifest.
    direct = (output / 'direct-writer.jsonl').open('w')
    def tick_both(tick):
        direct.write(json.dumps({'episode': 0, 'tick': tick, 'action': [tick]}) + '\n')
        direct.flush()
        writer.tick(0, tick, action=np.array([tick], np.float32))
    for tick in range(32):
        tick_both(tick)
    replace = Path.replace
    atomic_manifest = records._atomic_manifest
    def interrupted_replace(source, destination):
        if source.name == '000001.tmp':
            if variant == 'before_chunk_rename':
                os._exit(23)
            result = replace(source, destination)
            if variant == 'after_rename_before_event':
                os._exit(23)
            return result
        return replace(source, destination)
    def interrupted_manifest(path, payload):
        if json.loads(payload)['status'] != 'running':
            os._exit(23)
        return atomic_manifest(path, payload)
    with patch.object(Path, 'replace', interrupted_replace), patch.object(records, '_atomic_manifest', interrupted_manifest):
        for tick in range(32, 64):
            tick_both(tick)
        writer.finish({})
    raise RuntimeError('publication injection did not terminate')


def _publication(case, output):
    from palimpsest.records import iter_ticks
    with (output / 'publication.stdout').open('w') as stdout, (output / 'publication.stderr').open('w') as stderr:
        child = _runtime_process([sys.executable, str(Path(__file__).resolve()), '--publication-child',
                                  str(output), case.variants[0]], stdout, stderr, 30)
    require(child.returncode == 23, 'publication child did not reach injection boundary')
    recording = output / 'recording'
    ticks = list(iter_ticks(recording))
    manifest = json.loads((recording / 'manifest.json').read_text())
    terminal = manifest['status'] != 'running'
    expected = 64 if case.variants[0] == 'before_terminal_manifest' else 32
    valid = len(ticks) == expected and [t['tick'] for t in ticks] == list(range(expected))
    direct_ticks = [json.loads(line) for line in (output / 'direct-writer.jsonl').read_text().splitlines()]
    parsed = len(direct_ticks)
    require([t['tick'] for t in direct_ticks] == list(range(64)), 'direct writer lost the common input trace')
    return {'child_returncode': child.returncode, 'output_exists': recording.exists(),
            'some_bytes_parse': parsed > 0, 'direct_writer_accepted': parsed > 0,
            'direct_writer_ticks': parsed, 'terminal_success': terminal,
            'published_ticks': len(ticks), 'semantic_invalid': True,
            'semantic_outcome': 'detected' if valid and not terminal else 'accepted',
            'retained_prefix_valid': valid}


def _copy_reflink(source, destination):
    subprocess.run(['cp', '--reflink=auto', '--', str(source), str(destination)], check=True, capture_output=True)
    return str(destination)


def _copy_runtime(output):
    repo, assets = output / 'copied-repo', output / 'copied-assets'
    repo.mkdir()
    for name in ('src', 'model_manifests'):
        shutil.copytree(REPO / name, repo / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ('uv.lock', 'pyproject.toml'):
        shutil.copyfile(REPO / name, repo / name)
    (repo / 'upstream').mkdir()
    subprocess.run(['git', 'clone', '--quiet', '--shared', str(MAIN_REPO / 'upstream/fly-gym'),
                    str(repo / 'upstream/fly-gym')], check=True, capture_output=True)
    shutil.copytree(ASSETS, assets, copy_function=_copy_reflink)
    return repo, assets



def _base_hashes(root):
    return {str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '.git' not in p.relative_to(root).parts
            and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def _runtime_inputs(case, output):
    if CAMPAIGN_ROOT is None:
        return _copy_runtime(output)
    require(output.resolve().is_relative_to(CAMPAIGN_ROOT.resolve()), 'unit escapes campaign root')
    base = CAMPAIGN_ROOT / 'runtime-base'
    identity_file = CAMPAIGN_ROOT / 'runtime-base-identity.json'
    if not base.exists():
        base.mkdir()
        repo, assets = _copy_runtime(base)
        _json(identity_file, _base_hashes(base))
        # No normal runtime unit may modify this shared copy. Python tolerates
        # disabled bytecode writes; graph preparation has already been retained.
        for path in sorted(base.rglob('*'), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        base.chmod(0o555)
    require(_base_hashes(base) == json.loads(identity_file.read_text()), 'shared runtime base identity drift')
    repo, assets = base / 'copied-repo', base / 'copied-assets'
    if case.id == 'D1':
        private = output / 'copied-repo'
        shutil.copytree(repo, private, copy_function=_copy_reflink)
        repo = private
    elif case.id == 'D2':
        private = output / 'copied-assets'
        shutil.copytree(assets, private, copy_function=_copy_reflink)
        assets = private
    return repo, assets


def _command(engine, kind, payload=None, *, identifier=None, advance=True, revision=None):
    command = {'id': identifier or uuid.uuid4().hex, 'kind': kind, 'expected_state': engine.phase,
               'expected_episode': engine.episode,
               'expected_revision': engine.revision if revision is None else revision}
    if payload is not None:
        command['payload'] = payload
    receipt = engine.submit(command)
    if advance:
        engine.advance()
        require(engine.phase != 'failed', f'engine failed: {engine.last_outcome}')
    return command, receipt


def _intervention(engine):
    world = engine.world()
    for index, obstacle in enumerate(world['obstacles']):
        for dx, dy in ((.2, 0), (-.2, 0), (0, .2), (0, -.2)):
            payload = {'kind': 'move_obstacle', 'index': index,
                       'xy': [obstacle[0] + dx, obstacle[1] + dy]}
            try:
                engine.preview(payload)
                return payload
            except ValueError:
                pass
    raise RuntimeError('seed has no valid nearby obstacle intervention')


def _capture(engine):
    from palimpsest.snapshots import capture
    return capture(engine.env, engine.observation, policy=engine.policy, application=engine.application_state())


def _scientific_digest(engine):
    from palimpsest.snapshots import state_digest
    # Normalize only destination recorder identity; include every seeded owner
    # RNG (Python, NumPy, environment/spaces and Torch) in isolation checks.
    snapshot = _capture(engine)
    for name in ('source_run_id', 'event_prefix'):
        snapshot['application'].pop(name)
    return state_digest(snapshot)


def _open(repo, assets, run, seed):
    from palimpsest.engine import Engine
    run.mkdir(exist_ok=True)
    return Engine.open(repo, assets, run / 'recording', controller='flynn', device='cpu',
                       seed=seed, scenario='sparse-navigation', run_id=run.name, max_bytes=64 * 1024**2)


def _tick_state(engine):
    import numpy as np
    result = {'qpos': engine.env.data.qpos.copy(), 'qvel': engine.env.data.qvel.copy(),
            'control': engine.env.data.ctrl.copy(),
            'hidden': engine.policy.hidden.detach().cpu().numpy().copy(),
            'action': np.asarray(engine.last_transition['action']).copy(),
            'revision': np.array(engine.revision, np.int64)}
    def retain(prefix, value):
        if isinstance(value, dict):
            for key, item in value.items():
                retain(prefix + '__' + key, item)
        else:
            result[prefix] = (np.array([], np.uint8) if value is None else value.detach().cpu().numpy().copy())
    retain('left_retina', engine.policy.agent.state_vision_left)
    retain('right_retina', engine.policy.agent.state_vision_right)
    return result


def validate_replay_claim(claimed_mode, facts):
    """Study guard: validate a claim against observed execution, not API refusal."""
    require(claimed_mode == facts['executed_mode'], f'{claimed_mode} claim disagrees with executed mode')
    if claimed_mode == 'policy':
        require(facts['inference_executed'] is True and facts['policy_invocations'] > 0,
                'policy claim requires measured controller execution')
    return True


def _claim_guard(claimed_mode, executed_mode, inference_executed, policy_invocations):
    facts = {'executed_mode': executed_mode, 'inference_executed': inference_executed,
             'policy_invocations': policy_invocations}
    try:
        validate_replay_claim(claimed_mode, facts)
    except ValueError as exc:
        return {'scope': 'study_guard', 'claimed_mode': claimed_mode, 'facts': facts,
                'rejected': True, 'error': str(exc)}
    return {'scope': 'study_guard', 'claimed_mode': claimed_mode, 'facts': facts, 'rejected': False}


def _r2_evaluation(report, expected_source, expected_ticks, observed_policy_calls):
    """A failed or mismatched replay is an execution failure, never detection."""
    require(report.get('mode') == 'actions' and report.get('status') == 'passed',
            'R2 requires a successful observed action replay')
    require(type(report.get('compared_ticks')) is int and report['compared_ticks'] == expected_ticks,
            'R2 action replay did not compare the complete source trace')
    require(all(report.get(key) == value for key, value in expected_source.items()),
            'R2 action replay source identity differs')
    require(report.get('controller_reexecuted') is False and report.get('inference_executed') is False
            and observed_policy_calls == 0, 'R2 action replay did not demonstrate controller bypass')
    require(report.get('errors') == [] and report.get('first_divergence') is None,
            'R2 action replay reported errors or divergence')
    guard = _claim_guard('policy', report['mode'], report['inference_executed'], observed_policy_calls)
    return {'claimed_mode': 'policy', 'executed_mode': report['mode'], 'trajectory_matches': True,
            'replay_inference_executed': report['inference_executed'],
            'replay_policy_invocations': observed_policy_calls, 'replay_report': report,
            'expected_replay_source': expected_source, 'expected_source_ticks': expected_ticks,
            'semantic_invalid': True, 'claim_validation': guard, 'detection_scope': 'study_guard',
            'production_outcome': 'actions_replay_' + report['status'],
            'semantic_outcome': 'refused' if guard['rejected'] else 'accepted'}


def _continuation_comparisons(expected, pose, full):
    scientific = lambda rows: [{k: v for k, v in row.items() if k != 'revision'} for row in rows]
    application = lambda rows: [{k: v for k, v in row.items() if k == 'revision'} for row in rows]
    return {'pose_first_divergence': first_divergence(expected, pose),
            'full_first_divergence': first_divergence(expected, full),
            'scientific_first_divergence': first_divergence(scientific(expected), scientific(pose)),
            'application_first_divergence': first_divergence(application(expected), application(pose)),
            'full_scientific_first_divergence': first_divergence(scientific(expected), scientific(full))}


def recompute_continuation_evidence(path):
    import numpy as np
    with np.load(path, allow_pickle=False) as arrays:
        rows = {label: [] for label in ('expected', 'pose', 'full')}
        for label in rows:
            for tick in range(int(arrays[label + '__ticks'])):
                prefix = f'{label}__{tick}__'
                rows[label].append({key[len(prefix):]: arrays[key].copy() for key in arrays.files if key.startswith(prefix)})
    return _continuation_comparisons(rows['expected'], rows['pose'], rows['full'])


def _continuation_evidence(expected, pose, full, output):
    import numpy as np
    arrays = {}
    for label, rows in (('expected', expected), ('pose', pose), ('full', full)):
        arrays[label + '__ticks'] = np.array(len(rows), np.int64)
        for tick, row in enumerate(rows):
            arrays.update({f'{label}__{tick}__{key}': value for key, value in row.items()})
    path = output / 'continuation-pairs.npz'
    np.savez(path, **arrays)
    comparisons = recompute_continuation_evidence(path)
    require(comparisons == _continuation_comparisons(expected, pose, full), 'retained continuation comparison mismatch')
    scope = ('scientific' if comparisons['scientific_first_divergence'] else
             'application_only' if comparisons['application_first_divergence'] else 'none')
    return {**comparisons, 'comparisons': comparisons, 'divergence_scope': scope,
            'arrays_path': path.name, 'arrays_sha256': sha256_file(path)}


def _display_evidence(engine, output, boundary):
    import numpy as np
    from palimpsest.snapshots import state_digest
    display = {key: value.copy() for key, value in engine.effective_cameras().items()}
    path = output / f'display-boundary-{boundary}.npz'
    np.savez(path, **display)
    return {'run_id': engine.run_id, 'episode': engine.episode,
            'observation_total_tick': engine.total_tick, 'last_transition_tick': engine.last_transition['tick'],
            'display_sha256': state_digest(display), 'arrays_path': path.name, 'arrays_sha256': sha256_file(path)}


def _delayed_recovered(states, initial_obstacles, terminal, applied, received_tick, final_obstacles):
    expected_ticks = [received_tick + 1, received_tick + 2]
    return (len(applied) == 1 and terminal.get('applied_tick') == received_tick + 2
            and applied[0]['tick'] == terminal.get('applied_tick')
            and final_obstacles != initial_obstacles and terminal['status'] == 'applied'
            and [s['tick'] for s in states] == expected_ticks
            and all(s['receipt'] == 'queued' and s['obstacles'] == initial_obstacles
                    and s['display']['observation_total_tick'] == s['tick']
                    and s['display']['last_transition_tick'] == s['tick'] - 1 for s in states))


def _owner_facts(engine):
    from palimpsest.snapshots import state_digest
    return {'pid': os.getpid(), 'digest': _scientific_digest(engine),
            'rng_sha256': state_digest(_capture(engine)['rng']),
            'pose_sha256': state_digest({'qpos': engine.env.data.qpos.copy(), 'qvel': engine.env.data.qvel.copy()})}


def _initial_poses_match(parent, branch, sibling):
    return parent['pose_sha256'] == branch['pose_sha256'] == sibling['pose_sha256']


def _branch_child(config):
    from palimpsest.snapshots import read_snapshot
    engine = _open(Path(config['repo']), Path(config['assets']), Path(config['run']), config['seed'])
    try:
        engine.restore_branch(read_snapshot(Path(config['snapshot'])))
        def reply():
            print('FAULT_BRANCH ' + json.dumps(_owner_facts(engine)), flush=True)
        reply()
        for line in sys.stdin:
            operation = line.strip()
            if operation == 'mutate':
                _command(engine, 'intervene', _intervention(engine))
                reply()
            elif operation == 'digest':
                reply()
            elif operation == 'close':
                break
    finally:
        engine.close()


def _branch_response(child):
    while line := child.stdout.readline():
        if line.startswith('FAULT_BRANCH '):
            return json.loads(line[len('FAULT_BRANCH '):])
    raise RuntimeError(f'branch child exited {child.poll()}')


def _branches(engine, repo, assets, output, seed):
    from palimpsest.snapshots import save_snapshot
    snapshot = output / 'branch.snp'
    save_snapshot(_capture(engine), snapshot)
    parent_before = _owner_facts(engine)
    children = []
    try:
        for label in ('sibling-b', 'branch-a'):
            config = {'repo': str(repo), 'assets': str(assets), 'run': str(output / uuid.uuid4().hex),
                      'snapshot': str(snapshot), 'seed': seed}
            config_path = output / (label + '.json')
            _json(config_path, config)
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--branch-child', str(config_path)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            children.append(child)
            initial = _branch_response(child)
            if label == 'sibling-b':
                sibling_before = initial
            else:
                branch_before = initial
        branch = children[1]
        branch.stdin.write('mutate\n'); branch.stdin.flush()
        branch_after = _branch_response(branch)
        sibling = children[0]
        sibling.stdin.write('digest\n'); sibling.stdin.flush()
        sibling_after = _branch_response(sibling)
        parent_after = _owner_facts(engine)
        unchanged = parent_before == parent_after and sibling_before == sibling_after
        poses_match = _initial_poses_match(parent_before, branch_before, sibling_before)
        return {'owner_pids': [os.getpid(), branch_before['pid'], sibling_before['pid']],
                'parent_before': parent_before['digest'], 'parent_after': parent_after['digest'],
                'sibling_before': sibling_before['digest'], 'sibling_after': sibling_after['digest'],
                'branch_before': branch_before['digest'], 'branch_after': branch_after['digest'],
                'owner_states': {'parent_before': parent_before, 'parent_after': parent_after,
                    'branch_before': branch_before, 'branch_after': branch_after,
                    'sibling_before': sibling_before, 'sibling_after': sibling_after},
                'pose_copies_completed': poses_match, 'semantic_invalid': True,
                'semantic_outcome': 'recovered' if poses_match and unchanged and branch_before['digest'] != branch_after['digest'] else 'accepted'}
    finally:
        for child in children:
            if child.poll() is None:
                child.stdin.write('close\n'); child.stdin.flush()
                try:
                    child.wait(15)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait()
            child.stdin.close(); child.stdout.close(); child.stderr.close()


def _asset_schema(target, variant):
    """Parse independently from disk; retain structure rather than assume it."""
    if variant == 'checkpoint':
        import torch
        state = torch.load(target, map_location='cpu', weights_only=True)
        require(isinstance(state, dict) and bool(state), 'checkpoint state dictionary required')
        require(all(isinstance(k, str) and isinstance(v, torch.Tensor) for k, v in state.items()),
                'checkpoint must contain named tensors')
        return {key: {'shape': list(value.shape), 'dtype': str(value.dtype), 'layout': str(value.layout)}
                for key, value in sorted(state.items())}
    import csv
    def scalar_type(value):
        if not value:
            return 'empty'
        try:
            int(value)
            return 'integer'
        except ValueError:
            try:
                float(value)
                return 'float'
            except ValueError:
                return 'text'
    with target.open(newline='') as stream:
        reader = csv.reader(stream)
        columns = next(reader)
        types, count = [set() for _ in columns], 0
        for row in reader:
            require(len(row) == len(columns), 'CSV row schema mismatch')
            count += 1
            for known, value in zip(types, row):
                known.add(scalar_type(value))
    return {'columns': columns, 'row_count': count, 'column_types': [sorted(t) for t in types]}


def _substitute_same_shape(target, variant):
    before = _asset_schema(target, variant)
    target.chmod(0o600)
    if variant == 'checkpoint':
        import torch
        state = torch.load(target, map_location='cpu', weights_only=True)
        key = next(k for k in sorted(state) if state[k].layout == torch.strided
                   and state[k].is_floating_point() and state[k].numel())
        value = state[key].clone()
        original = value.reshape(-1)[0].clone()
        value.reshape(-1)[0] = original + 1
        require(not torch.equal(original, value.reshape(-1)[0]), 'checkpoint substitution did not change a value')
        state[key] = value
        torch.save(state, target)
    else:
        # Preserve every CSV record, header and scalar type. Changing one byte
        # in-place avoids materializing the large graph in host memory.
        import csv
        with target.open('r+b') as stream:
            header = next(csv.reader([stream.readline().decode()]))
            offset = stream.tell()
            line = stream.readline()
            fields = line.rstrip(b'\r\n').split(b',')
            column = header.index('syn_count' if variant == 'graph' else 'flow')
            require(fields[column], 'empty substitution field')
            location = offset + sum(len(f) + 1 for f in fields[:column])
            original = fields[column][0]
            replacement = (ord('2') if original != ord('2') else ord('3')) if variant == 'graph' else (ord('a') if original != ord('a') else ord('e'))
            stream.seek(location)
            stream.write(bytes([replacement]))
    after = _asset_schema(target, variant)
    return {'asset_schema_before': before, 'asset_schema_after': after,
            'shape_matches': before == after, 'schema_parsed': True}


def _runtime(case, output, repo, assets):
    import copy
    import numpy as np
    from palimpsest.records import iter_ticks
    from palimpsest.replay import _register_initial, replay_run
    from palimpsest.snapshots import read_snapshot, save_snapshot, state_digest
    from palimpsest.flynn import FlynnPolicy
    run = output / uuid.uuid4().hex
    invocations = 0
    act = FlynnPolicy.act
    def counted(policy, observation):
        nonlocal invocations
        invocations += 1
        return act(policy, observation)
    FlynnPolicy.act = counted
    engine = _open(repo, assets, run, case.seeds[0])
    trace = {'controller': 'flynn', 'policy_loaded': True, 'retained_prefix_valid': True}
    try:
        # A live prefix ensures every runtime unit executes the actual policy.
        for _ in range(8):
            _command(engine, 'step')
        if case.id.startswith('A'):
            payload = _intervention(engine)
            initial_world, initial_revision = engine.world(), engine.revision
            if case.id == 'A1':
                # Two explicit queued step boundaries precede the intervention in
                # the owner FIFO. Keep the latest policy-produced display frame.
                _command(engine, 'step', advance=False)
                _command(engine, 'step', advance=False, revision=engine.revision + 1)
                command, receipt = _command(engine, 'intervene', payload, advance=False, revision=engine.revision + 2)
                states = []
                for boundary in range(2):
                    engine.advance()
                    states.append({'tick': engine.total_tick, 'receipt': engine.receipts[command['id']]['status'],
                                   'obstacles': engine.world()['obstacles'],
                                   'display': _display_evidence(engine, output, boundary)})
                pending_before = engine.receipts[command['id']]['status']
                engine.advance()
                terminal = engine.receipts[command['id']]
                engine.writer.flush()
                events = [json.loads(line) for line in (run / 'recording/events.jsonl').read_text().splitlines()]
                applied = [e for e in events if e['kind'] == 'command_applied' and e['id'] == command['id']]
                recovered = _delayed_recovered(states, initial_world['obstacles'], terminal, applied,
                                                receipt['received_tick'], engine.world()['obstacles']) and pending_before == 'queued'
                trace.update(request_accepted=receipt['status'] == 'queued',
                             queued_boundaries=states, terminal_receipt=terminal,
                             authoritative_applications=len(applied), authoritative_ticks=[e['tick'] for e in applied],
                             semantic_invalid=True, semantic_outcome='recovered' if recovered else 'accepted')
            elif case.id == 'A2':
                command, receipt = _command(engine, 'intervene', payload, revision=engine.revision - 1)
                terminal = engine.receipts[command['id']]
                detected = terminal['status'] == 'rejected' and engine.world() == initial_world and engine.revision == initial_revision
                trace.update(request_parsed=receipt['status'] == 'queued', terminal_receipt=terminal,
                             world_unchanged=engine.world() == initial_world, semantic_invalid=True,
                             semantic_outcome='refused' if detected else 'accepted')
            else:
                command, first = _command(engine, 'intervene', payload, advance=False)
                second = engine.submit(command)
                engine.advance()
                third = engine.submit(command)
                engine.advance()
                engine.writer.flush()
                events = [json.loads(line) for line in (run / 'recording/events.jsonl').read_text().splitlines()]
                applied = [e for e in events if e['kind'] == 'command_applied' and e['id'] == command['id']]
                recovered = len(applied) == 1 and engine.revision == initial_revision + 1
                trace.update(accepted_requests=sum(r['status'] == 'queued' for r in (first, second)),
                             authoritative_applications=len(applied), authoritative_ticks=[e['tick'] for e in applied],
                             terminal_receipt=third, semantic_invalid=True,
                             semantic_outcome='recovered' if recovered else 'accepted')
        elif case.id.startswith('R') or case.id.startswith('D'):
            # Replay source starts at this live prefix. Existing prefix ticks must
            # not precede the registered initial snapshot, so branch to a new run.
            snapshot = _capture(engine)
            engine.close()
            run = output / uuid.uuid4().hex
            engine = _open(repo, assets, run, case.seeds[0])
            engine.restore_branch(snapshot)
            initial_snapshot_id = _register_initial(engine, run)
            for _ in range(3):
                _command(engine, 'step')
            engine.close()
            source_ticks = list(iter_ticks(run / 'recording'))
            expected_source = {'source_run_id': run.name, 'source_snapshot_id': initial_snapshot_id,
                               'source_snapshot_sha256': sha256_file(run / 'snapshots/initial.snp')}
            trace.update(initial_setup_succeeded=True)
            if case.id == 'R1':
                # Actual validated playback reads retained ticks and renders no policy.
                from palimpsest.artifacts import playback
                before_replay = invocations
                played = playback(run, episode=int(source_ticks[0]['episode']), tick=int(source_ticks[0]['tick']))
                replayed_calls = invocations - before_replay
                guard = _claim_guard('policy', played['mode'], replayed_calls > 0, replayed_calls)
                trace.update(claimed_mode='policy', executed_mode='playback', viewable=bool(played),
                             replay_inference_executed=replayed_calls > 0, replay_policy_invocations=replayed_calls,
                             claim_validation=guard, detection_scope='study_guard',
                             production_outcome='playback_returned',
                             semantic_invalid=True, semantic_outcome='refused' if guard['rejected'] else 'accepted')
            else:
                destination = output / uuid.uuid4().hex
                destination.mkdir()
                mode = 'actions' if case.id == 'R2' else 'policy'
                if case.id == 'D1':
                    variant = case.variants[0]
                    target = repo / {'source': 'src/palimpsest/engine.py', 'lock': 'uv.lock',
                                     'hash': 'src/palimpsest/records.py'}[variant]
                    # Both source variants change actual copied file bytes. The
                    # recorded source trace stays intact and valid; compatibility
                    # rejects the newly computed destination source/lock hash.
                    trace['injection_mechanism'] = {'source': 'engine_source', 'lock': 'lockfile', 'hash': 'runtime_hash'}[variant]
                    trace['copied_target_sha256_before'] = sha256_file(target)
                    target.chmod(0o600)
                    with target.open('a') as stream:
                        stream.write('\n# copied identity fault\n')
                    trace['injected_path'] = str(target)
                    trace['copied_target_sha256_after'] = sha256_file(target)
                elif case.id == 'D2':
                    from palimpsest.assets import prepare_graph
                    edge = prepare_graph(repo, assets)
                    variant = case.variants[0]
                    target = (edge if variant == 'graph' else next(assets.glob('*.pt')) if variant == 'checkpoint'
                              else edge.parent / 'descending_neurons.csv')
                    trace['copied_target_sha256_before'] = sha256_file(target)
                    trace.update(_substitute_same_shape(target, variant))
                    require(trace['shape_matches'], 'copied asset substitution changed parsed schema')
                    trace.update(injected_path=str(target),
                                 copied_target_sha256_after=sha256_file(target))
                before_replay = invocations
                report = replay_run(run, destination, mode=mode, repo_root=repo, asset_root=assets)
                _json(output / 'observed-replay-report.json', report)
                if case.id == 'R2':
                    # Retain the report and expected identity even when admission
                    # to this study comparison fails and no guard runs.
                    trace.update(replay_report=report, expected_replay_source=expected_source,
                                 expected_source_ticks=len(source_ticks))
                    trace.update(_r2_evaluation(report, expected_source, len(source_ticks), invocations - before_replay))
                else:
                    trace.update(replay_ticks=report['compared_ticks'], replay_report=report, semantic_invalid=True,
                                 replay_policy_invocations=invocations - before_replay,
                                 semantic_outcome='refused' if report['status'] == 'failed' and report['compared_ticks'] == 0 and invocations == before_replay else 'accepted')
        elif case.id.startswith('S'):
            snapshot = _capture(engine)
            snapshot_file = output / 'source.snp'
            save_snapshot(snapshot, snapshot_file)
            source_hash = sha256_file(snapshot_file)
            if case.id == 'S1':
                _command(engine, 'step')
                expected = [_tick_state(engine)]
                # Executable integration-only restore omits controller/RNG/application.
                import mujoco
                mujoco.mj_setState(engine.env.model, engine.env.data, snapshot['integration'], snapshot['integration_enum'])
                mujoco.mj_forward(engine.env.model, engine.env.data)
                pose_restored = np.array_equal(engine.env.data.qpos, np.asarray(snapshot['integration'])[1:1 + engine.env.model.nq])
                _command(engine, 'step')
                actual = [_tick_state(engine)]
                destination = output / uuid.uuid4().hex
                engine.close()
                engine = _open(repo, assets, destination, case.seeds[0])
                engine.restore_branch(snapshot)
                _command(engine, 'step')
                evidence = _continuation_evidence(expected, actual, [_tick_state(engine)], output)
                divergence, full_divergence = evidence['pose_first_divergence'], evidence['full_first_divergence']
                trace.update(evidence)
                trace.update(pose_restored=pose_restored, continued=True, first_divergence=divergence,
                             comparison_origin_tick=snapshot['application']['total_tick'],
                             full_snapshot_first_divergence=full_divergence, semantic_invalid=True,
                             semantic_outcome='detected' if divergence is not None and full_divergence is None else 'accepted')
            else:
                bad = copy.deepcopy(snapshot)
                bad['policy'].pop('hidden')
                bad['policy'].pop('left')
                bad['policy'].pop('right')
                copied = output / 'copied-incomplete.snp'
                save_snapshot(bad, copied)
                readable = read_snapshot(copied)
                before = _scientific_digest(engine)
                # restore_branch requires a distinct destination recording identity.
                destination = output / uuid.uuid4().hex
                engine.close()
                engine = _open(repo, assets, destination, case.seeds[0])
                before = _scientific_digest(engine)
                caught = None
                try:
                    engine.restore_branch(readable)
                except ValueError as exc:
                    caught = str(exc)
                unchanged = before == _scientific_digest(engine)
                trace.update(snapshot_readable=True, process_progress=True, error=caught,
                             destination_unchanged=unchanged, semantic_invalid=True,
                             semantic_outcome='refused' if caught and unchanged else 'accepted')
            trace['source_snapshot_unchanged'] = sha256_file(snapshot_file) == source_hash
        elif case.id == 'B1':
            trace.update(_branches(engine, repo, assets, output, case.seeds[0]))
        elif case.id == 'B2':
            shared_b = engine  # Deliberate executable shared-owner ablation.
            pose = engine.env.data.qpos.copy()
            before = _scientific_digest(shared_b)
            _command(engine, 'reset', {'seed': case.seeds[0]})
            engine.env.data.qpos[:] = pose
            _command(engine, 'intervene', _intervention(engine))
            after = _scientific_digest(shared_b)
            trace.update(reset_pose_copy_completed=True, shared_owner_pid=os.getpid(),
                         sibling_before=before, sibling_after=after, semantic_invalid=True,
                         semantic_outcome='detected' if before != after else 'accepted')
    finally:
        trace['policy_invocations'] = invocations
        _json(output / 'runtime-trace.json', trace)
        engine.close()
        FlynnPolicy.act = act
    return trace


def _original_hashes(runtime):
    paths = [FIXTURE_SOURCE]
    if runtime:
        paths = [REPO / 'uv.lock', *sorted((REPO / 'src/palimpsest').glob('*.py')),
                 *sorted((REPO / 'model_manifests').glob('*.json')),
                 *sorted((MAIN_REPO / 'upstream/fly-gym').rglob('*.py')),
                 *sorted(p for p in ASSETS.rglob('*') if p.is_file())]
    return {str(path): sha256_file(path) for path in paths}


def _size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())


def _descriptor(case):
    require(len(case.seeds) <= 1 and len(case.variants) == len(case.conditions) == 1,
            'run_fault_case requires a narrowed single-unit FaultCase')
    seed = case.seeds[0] if case.seeds else None
    return {'unit_id': f"fault/{case.id}/{case.variants[0]}/{case.conditions[0]}/seed-{seed if seed is not None else 'none'}",
            'kind': 'fault', 'case_id': case.id, 'seed': seed,
            'variant': case.variants[0], 'condition': case.conditions[0]}



def _runtime_process(command, stdout, stderr, timeout):
    if CAMPAIGN_DEADLINE_EPOCH is not None:
        timeout = min(timeout, CAMPAIGN_DEADLINE_EPOCH - time.time())
        if timeout <= 0:
            raise subprocess.TimeoutExpired(command, timeout)
    child = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
    try:
        returncode = child.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Branch owners inherit the runtime process group. Killing only the
        # immediate child would leave those model owners executing after timeout.
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()
        raise
    return subprocess.CompletedProcess(command, returncode)


def run_fault_case(case: FaultCase, output: Path, identity: dict[str, object]) -> dict[str, object]:
    descriptor = _descriptor(case)
    prepare_output_root(output)
    started = time.monotonic()
    require(shutil.disk_usage(output).free - case.max_output_bytes >= 6 * 1024**3,
            'filesystem free-space reserve insufficient for unit admission')
    before = _original_hashes(case.path == 'runtime')
    row = {'schema_version': 1, 'study_id': 'authority_replay_v1', **descriptor,
           'identity': identity, 'fault_family': case.family, 'injection_stage': case.injection_stage,
           'execution_path': 'cpu-flynn-runtime' if case.path == 'runtime' else 'fixture-production-interfaces',
           'status': 'completed', 'source_hashes_before': before}
    trace = {}
    try:
        if case.path == 'runtime':
            repo, assets = _runtime_inputs(case, output)
            if CAMPAIGN_ROOT is not None:
                row['shared_base_identity_file'] = str(CAMPAIGN_ROOT / 'runtime-base-identity.json')
                row['shared_base_identity_before'] = sha256_file(CAMPAIGN_ROOT / 'runtime-base-identity.json')
            config = output / 'runtime-config.json'
            _json(config, {'case': dataclasses.asdict(case), 'repo': str(repo), 'assets': str(assets), 'output': str(output)})
            with (output / 'runtime.stdout').open('w') as stdout, (output / 'runtime.stderr').open('w') as stderr:
                child = _runtime_process([sys.executable, str(Path(__file__).resolve()), '--runtime-child', str(config)],
                                         stdout, stderr, max(1, case.timeout_seconds - (time.monotonic() - started)))
            require(child.returncode == 0, f"runtime child failed ({child.returncode}); see runtime.stderr")
            trace = json.loads((output / 'runtime-trace.json').read_text())
        else:
            functions = {'C1': _custody, 'C2': _custody, 'C3': _custody, 'P1': _publication,
                         'E1': _quota, 'E2': _queue, 'E3': _writer_error}
            trace = functions[case.id](case, output)
        require(_size(output) <= case.max_output_bytes, 'ordinary unit output cap crossed')
        require(shutil.disk_usage(output).free >= 6 * 1024**3, 'filesystem free-space reserve crossed')
        row.update(classify_outcome(trace, descriptor['condition']))
        row['retained_prefix_valid'] = trace['retained_prefix_valid']
        row['outcome_scope'] = trace.get('detection_scope', 'production')
        row['palimpsest_outcome'] = trace.get('production_outcome', trace['semantic_outcome'])
        if row['outcome_scope'] == 'study_guard':
            row['study_guard_outcome'] = trace['semantic_outcome']
        baseline = naive_accepts(case.id, trace)
        row['baseline_outcome'] = {'predicate': case.naive_predicate, 'accepted': baseline,
                                   'silent_acceptance': baseline and trace['semantic_invalid']}
    except subprocess.TimeoutExpired as exc:
        row.update(status='timeout', error={'type': type(exc).__name__, 'message': str(exc)})
    except Exception as exc:
        row.update(status='failed', error={'type': type(exc).__name__, 'message': str(exc)})
    finally:
        if not trace and (output / 'runtime-trace.json').is_file():
            try:
                trace = json.loads((output / 'runtime-trace.json').read_text())
            except (OSError, ValueError) as exc:
                row['partial_trace_error'] = str(exc)
        try:
            if case.path == 'runtime' and CAMPAIGN_ROOT is not None and 'shared_base_identity_before' in row:
                expected_base = json.loads((CAMPAIGN_ROOT / 'runtime-base-identity.json').read_text())
                row['shared_base_unchanged'] = _base_hashes(CAMPAIGN_ROOT / 'runtime-base') == expected_base
                row['shared_base_identity_after'] = sha256_file(CAMPAIGN_ROOT / 'runtime-base-identity.json')
                require(row['shared_base_unchanged'], 'shared runtime base drift')
            after = _original_hashes(case.path == 'runtime')
            row['source_hashes_after'] = after
            require(before == after, 'retained original identity drift')
        except (OSError, ValueError) as exc:
            if 'error' in row:
                row['prior_error'] = row['error']
            row.update(status='failed', error={'type': 'SourceMutation', 'message': str(exc),
                                               'identity_error_type': type(exc).__name__})
            row.setdefault('source_hashes_after', None)
        row['metrics'] = {'elapsed_seconds': time.monotonic() - started, 'output_bytes': _size(output)}
        row['trace'] = trace
        _json(output / 'trace.json', trace)
        _json(output / 'row.json', row)
        # Include the retained trace and row themselves in byte accounting.
        for _ in range(3):
            measured = _size(output)
            if measured == row['metrics']['output_bytes']:
                break
            row['metrics']['output_bytes'] = measured
            _json(output / 'row.json', row)
        if row['metrics']['output_bytes'] > case.max_output_bytes:
            row.update(status='failed', error={'type': 'OutputCap', 'message': 'unit output cap crossed'})
            _json(output / 'row.json', row)
    return row


def _campaign_resource_root(output, campaign_root):
    output = Path(output).resolve()
    if campaign_root is None:
        campaign_root = next((p for p in output.parents if p.name == 'paper-authority-replay-v1'), output)
    root = Path(campaign_root).resolve()
    require(output.is_relative_to(root), 'driver output must be within campaign root')
    return root


def _campaign_deadline(root, identity, seconds, explicit):
    import math
    now = time.time()
    path = root / 'campaign-clock.json'
    try:
        with path.open('x') as stream:
            json.dump({'identity': identity, 'started_unix': now, 'deadline_unix': now + seconds}, stream)
    except FileExistsError:
        pass
    clock = json.loads(path.read_text())
    require(clock['identity'] == identity, 'shared campaign clock identity drift')
    require(all(isinstance(clock[k], (int, float)) and math.isfinite(clock[k]) for k in ('started_unix', 'deadline_unix')),
            'shared campaign clock must be finite')
    require(clock['started_unix'] <= clock['deadline_unix'] <= clock['started_unix'] + seconds,
            'shared campaign clock exceeds frozen duration')
    if explicit is not None:
        require(isinstance(explicit, (int, float)) and math.isfinite(explicit), 'campaign deadline must be finite')
    return min(clock['deadline_unix'], explicit) if explicit is not None else clock['deadline_unix']


def run_campaign(protocol, output, identity, *, fixture_only=False, campaign_root=None,
                 campaign_deadline_epoch=None):
    global CAMPAIGN_ROOT, CAMPAIGN_DEADLINE_EPOCH
    previous = CAMPAIGN_ROOT, CAMPAIGN_DEADLINE_EPOCH
    try:
        return _run_campaign(protocol, output, identity, fixture_only=fixture_only,
                             campaign_root=campaign_root, campaign_deadline_epoch=campaign_deadline_epoch)
    finally:
        CAMPAIGN_ROOT, CAMPAIGN_DEADLINE_EPOCH = previous


def _run_campaign(protocol, output, identity, *, fixture_only=False, campaign_root=None,
                  campaign_deadline_epoch=None):
    """Sequential expansion. Dry verification keeps skipped denominator as incomplete.

    Fixture-only output includes explicit placeholders for the other study drivers
    solely so the complete-denominator analyzer can validate this dry fixture. A
    result-producing fault campaign emits only its fault rows for later assembly.
    """
    global CAMPAIGN_ROOT, CAMPAIGN_DEADLINE_EPOCH
    prepare_output_root(output)
    resource_root = _campaign_resource_root(output, campaign_root)
    CAMPAIGN_DEADLINE_EPOCH = _campaign_deadline(resource_root, identity,
                                               protocol.resources['campaign_timeout_seconds'],
                                               campaign_deadline_epoch)
    CAMPAIGN_ROOT = output if not fixture_only else None
    _json(output / 'identity.json', identity)
    _json(output / 'invocation.json', {'argv': sys.argv, 'fixture_only': fixture_only,
          'scope': 'fixture verification; no scientific results' if fixture_only else 'fault campaign',
          'environment': {k: os.environ.get(k) for k in ('PYTHONPATH', 'MUJOCO_GL', 'OMP_NUM_THREADS')},
          'python': sys.version, 'executable': sys.executable,
          'campaign_root': str(resource_root), 'campaign_deadline_epoch': CAMPAIGN_DEADLINE_EPOCH})
    rows, stopped = [], None
    protocol_path = REPO / 'paper/studies/authority_replay_v1/protocol.json'
    if not fixture_only:
        require(campaign_identity(REPO, protocol_path, ASSETS) == identity, 'initial campaign identity drift')
    cases = {c.id: c for c in protocol.fault_cases}
    for unit in declared_units(protocol):
        if unit['kind'] != 'fault' and not fixture_only:
            continue
        is_runtime = unit['kind'] == 'fault' and cases[unit['case_id']].path == 'runtime'
        reason = stopped
        if fixture_only and (unit['kind'] != 'fault' or is_runtime):
            reason = 'outside fixture verification scope; not executed'
        if time.time() >= CAMPAIGN_DEADLINE_EPOCH:
            stopped = reason = 'campaign wall-clock cap reached'
        if _size(resource_root) + protocol.resources['ordinary_unit_max_output_bytes'] > protocol.resources['campaign_max_output_bytes']:
            stopped = reason = 'campaign output cap reached'
        if shutil.disk_usage(output).free < protocol.resources['minimum_free_bytes']:
            stopped = reason = 'filesystem free-space reserve reached'
        if reason:
            row = {'schema_version': 1, 'study_id': protocol.study_id, **unit, 'identity': identity,
                   'status': 'incomplete', 'metrics': {}, 'reason': reason, 'dry_run': fixture_only}
        else:
            case = dataclasses.replace(cases[unit['case_id']], seeds=[] if unit['seed'] is None else [unit['seed']],
                                       variants=[unit['variant']], conditions=[unit['condition']])
            unit_output = output / unit['unit_id'].replace('/', '__')
            try:
                row = run_fault_case(case, unit_output, identity)
            except ValueError as exc:
                # Admission refusals have not executed an experimental unit.
                stopped = str(exc)
                row = {'schema_version': 1, 'study_id': protocol.study_id, **unit, 'identity': identity,
                       'status': 'incomplete', 'metrics': {}, 'reason': stopped}
            row['dry_run'] = fixture_only
            if _size(resource_root) > protocol.resources['campaign_max_output_bytes']:
                row.update(status='failed', error={'type': 'CampaignOutputCap', 'message': 'shared campaign output cap crossed'})
                stopped = 'shared campaign output cap crossed'
            if not fixture_only:
                try:
                    require(campaign_identity(REPO, protocol_path, ASSETS) == identity, 'campaign identity drift')
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    row.update(status='failed', error={'type': 'SourceMutation', 'message': str(exc)})
                    stopped = 'retained original identity drift'
            if row['status'] == 'timeout' or row['metrics'].get('output_bytes', 0) > case.max_output_bytes:
                stopped = 'previous unit crossed a hard cap'
            if row.get('error', {}).get('type') == 'SourceMutation':
                stopped = 'retained original identity drift'
        append_row(output / 'rows.jsonl', row)
        rows.append(row)
    CAMPAIGN_ROOT = None
    return rows


def main():
    global ASSETS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--fixture-only', action='store_true')
    parser.add_argument('--campaign-root', type=Path, help='shared output root for the aggregate byte cap')
    parser.add_argument('--campaign-deadline-epoch', type=float, help='Unix deadline, bounded by campaign-clock.json')
    parser.add_argument('--publication-child', nargs=2)
    parser.add_argument('--runtime-child', type=Path)
    parser.add_argument('--branch-child', type=Path)
    args = parser.parse_args()
    if args.publication_child:
        _publication_child(Path(args.publication_child[0]), args.publication_child[1])
        return 0
    if args.branch_child:
        _branch_child(json.loads(args.branch_child.read_text()))
        return 0
    if args.runtime_child:
        config = json.loads(args.runtime_child.read_text())
        trace = _runtime(FaultCase(**config['case']), Path(config['output']), Path(config['repo']), Path(config['assets']))
        _json(Path(config['output']) / 'runtime-trace.json', trace)
        return 0
    if not (args.protocol and args.output):
        parser.error('--protocol and --output are required')
    protocol = load_protocol(args.protocol)
    if args.assets:
        ASSETS = args.assets.resolve()
    if args.fixture_only:
        # Deliberately permits an implementation worktree: all outputs are labeled
        # dry verification, runtime units never execute, and hashes are still real.
        identity = {'commit': subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
                    'protocol_sha256': sha256_file(args.protocol),
                    'runtime_source_sha256': {str(FIXTURE_SOURCE.relative_to(REPO)): sha256_file(FIXTURE_SOURCE)},
                    'asset_manifest_sha256': {'model_manifests/flynn-full-vision.json': sha256_file(REPO / 'model_manifests/flynn-full-vision.json')},
                    'asset_sha256': {'fixture_protocol_bytes': sha256_file(FIXTURE_SOURCE)}}
    else:
        identity = campaign_identity(REPO, args.protocol, ASSETS)
    rows = run_campaign(protocol, args.output, identity, fixture_only=args.fixture_only,
                        campaign_root=args.campaign_root, campaign_deadline_epoch=args.campaign_deadline_epoch)
    print(json.dumps({'rows': len(rows), 'failed': sum(r['status'] == 'failed' for r in rows), 'fixture_only': args.fixture_only}))
    return int(any(r['status'] in ('failed', 'timeout') for r in rows))


if __name__ == '__main__':
    raise SystemExit(main())
