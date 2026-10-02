"""Frozen serial closed-loop evaluation of the two existing male checkpoints.

No training, checkpoint selection, scene replacement, reset or retry. Invoke only
in an exclusive runtime window; the parent must impose the documented timeout.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import signal
import sys
import time
import uuid

from collect_male_teachers import identity as runtime_identity
from palimpsest import artifacts
from palimpsest.lab import LabSupervisor
from palimpsest.male_model import digest, features
from palimpsest.male_policy import resolve_profile
from palimpsest.records import iter_ticks
from palimpsest.snapshots import read_snapshot, state_digest
from palimpsest.storage import StorageLimits


PROTOCOL = {
    'version': 2, 'dataset_id': 'male-closed-loop-seeds128-135-v2',
    'scene_seeds': list(range(128, 136)), 'controller_order': ['male-original', 'male-control'],
    'rejected_v1': {'protocol_sha256': '0a90158f6592e22c180de403ff6a0fec80495d63e35823fe096af3ddf886b384',
                    'report_sha256': '379c7a5f3775a3c5b71c4dfcfc1ab9084fca9a438c661c820abf9906b039bc6d'},
    'initial_sensor_projection': 'exact Engine float32 vector: collision, collision_angle-or-zero, wind_cos, wind_sin',
    'scenario': 'reproduction', 'texture': 'checker', 'device': 'cpu',
    'episodes_per_run': 1, 'max_ticks_per_run': 600, 'control_interval_seconds': .02,
    'natural_termination': ['goal', 'collision', 'stalled', 'time_limit'],
    'reset_count': 0, 'retry_count': 0, 'training_or_selection': False,
    'startup_timeout_seconds': 60, 'progress_timeout_seconds': 30,
    'owner_timeout_seconds': 180, 'total_timeout_seconds': 900,
    'external_timeout_seconds': 960, 'external_kill_grace_seconds': 15,
    'recording_plus_snapshot_limit_bytes': 160 * 1024**2,
    'aggregate_limit_bytes': 3 * 1024**3, 'min_free_bytes': 1024**3,
    'max_report_bytes': 4 * 1024**2, 'max_runs': 16, 'max_snapshots_per_run': 1,
    'qualification_claims': [],
    'scope': 'new fixed-scene closed-loop outcomes for one trained model seed; no topology benefit or generalization claim',
}


def planned_runs():
    return [{'seed': seed, 'controller': controller, 'status': 'not_started'}
            for seed in PROTOCOL['scene_seeds'] for controller in PROTOCOL['controller_order']]


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sources(root):
    result = runtime_identity(root)
    paths = [root / name for name in (
        'scripts/collect_male_teachers.py', 'scripts/evaluate_male_closed_loop.py',
        'docs/plans/m7-closed-loop-protocol.md', 'data/manifests/male-reduced-policy-v1.json',
        'data/manifests/malecns-reduced-neighborhood-v1.json')]
    upstream = sorted((root / 'upstream/fly-gym').rglob('*.py'))
    if not upstream or len(upstream) > 256:
        raise ValueError('Pinned upstream Python source inventory missing or oversized')
    for path in [*paths, *upstream]:
        path = artifacts._safe_path(path)
        if not path.is_file() or path.stat().st_size > 4 * 1024**2:
            raise ValueError('Source file missing or oversized')
        result[path.relative_to(root).as_posix()] = file_sha(path)
    return result


def initial_fingerprint(snapshot, world, seed, identity):
    """Compare scientific start state, excluding intentionally different policies."""
    import numpy as np
    application, policy = snapshot['application'], snapshot['policy']
    expected = {'seed': seed, 'controller': identity['controller'], 'episode': 0,
                'total_tick': 0, 'episode_step': 0, 'phase': 'paused',
                'eyes': {'left': True, 'right': True}}
    if any(application.get(key) != value for key, value in expected.items()):
        raise ValueError('Initial snapshot is not the fresh frozen episode')
    if snapshot['identity']['policy']['provenance']['policy_identity'] != identity:
        raise ValueError('Initial snapshot model identity differs')
    hidden = np.asarray(policy.get('hidden'))
    if (policy.get('kind') != 'male-reduced-v1' or policy.get('failure_diagnostics') != {} or
            hidden.shape != (1, 138) or hidden.dtype != np.float32 or np.any(hidden != 0)):
        raise ValueError('Initial male hidden state is not fresh finite float32 zeros')
    raw = snapshot['observation']
    sensor = raw['sensors']
    # Match Engine._step's actual recorded projection, including its dtype.
    vector = np.array([float(sensor['collision']), 0. if sensor['collision_angle'] is None else float(sensor['collision_angle']),
                       *sensor['wind_direction']], dtype=np.float32)
    inputs = {'cam_left': raw['cam_left'], 'cam_right': raw['cam_right'], 'sensors': vector}
    encoded = features(inputs)  # Validate exact allowlisted shapes, units and finite values.
    integration = np.asarray(snapshot['integration'])
    if integration.ndim != 1 or integration.dtype != np.float64 or not np.isfinite(integration).all():
        raise ValueError('Initial physical state must be a finite float64 vector')
    return {name: state_digest(value) for name, value in {
        'world': artifacts._world(world), 'integration': integration,
        'environment': snapshot['environment'],
        'environment_identity': {key: value for key, value in snapshot['identity'].items()
                                 if key not in ('policy', 'teacher', 'torch')},
        'inputs': inputs, 'features': encoded,
        'environment_rng': {key: snapshot['rng'][key] for key in ('environment', 'environment_seed', 'spaces')},
    }.items()}


def require_matched_initial(original, control):
    differences = [key for key in set(original) | set(control) if original.get(key) != control.get(key)]
    if differences:
        raise ValueError('Paired initial states differ: ' + ', '.join(sorted(differences)))


def step_episode(supervisor, identifier, initial, wait):
    """One bounded episode; wait is the caller's existing owner/deadline check."""
    state = initial['state']
    for tick in range(PROTOCOL['max_ticks_per_run']):
        command_id = uuid.uuid4().hex
        supervisor.call(identifier, 'command', {'id': command_id, 'kind': 'step',
            'expected_state': 'paused', 'expected_episode': 0, 'expected_revision': state['revision']})
        value = wait(identifier, lambda view: any(row['id'] == command_id and row['status'] != 'queued' for row in view['receipts']))
        receipt = next(row for row in value['receipts'] if row['id'] == command_id)
        if receipt['status'] != 'applied':
            raise ValueError('Evaluation step was not applied: ' + str(receipt))
        value = wait(identifier, lambda view: view['state']['total_tick'] == tick + 1)
        state = value['state']
        if state['episode'] != 0 or state['phase'] not in ('paused', 'terminated', 'truncated'):
            raise ValueError('Evaluation reset or entered an unsupported phase')
        if state['phase'] in ('terminated', 'truncated'):
            break
    return state


def timing(values):
    ordered = sorted(values)
    return {'count': len(ordered), 'sum_seconds': sum(ordered),
            'mean_seconds': sum(ordered) / len(ordered),
            'p95_seconds': ordered[math.ceil(.95 * len(ordered)) - 1], 'max_seconds': ordered[-1]}


def validate_recording(run, seed, identity, final_state, initial):
    """Completed validated telemetry is the source of outcomes and timing."""
    import numpy as np
    data = artifacts._load(run)
    manifest, events = data['manifest'], data['events']
    expected = {'controller': identity['controller'], 'seed': seed, 'requested_device': 'cpu',
        'texture': 'checker', 'policy_identity': identity, 'control_interval_seconds': .02,
        'observation_profile': 'two-rgb-eyes-contact-relative-goal-bearing-v1',
        'sensor_order': ['collision', 'collision_angle', 'wind_cos', 'wind_sin']}
    if any(manifest.get(key) != value for key, value in expected.items()) or manifest.get('scenario', {}).get('id') != 'reproduction':
        raise ValueError('Completed run profile/model identity differs')
    if any(manifest.get(key) is not None for key in ('parent_run_id', 'replay_source_run_id', 'replay_mode', 'initial_memory')):
        raise ValueError('Evaluation requires root runs without replay or memory lineage')
    starts = [event for event in events if event['kind'] == 'episode_started']
    policies = [event for event in events if event['kind'] == 'policy_loaded']
    if (len(starts) != 1 or starts[0].get('seed') != seed or starts[0].get('episode') != 0 or
            len(policies) != 1 or policies[0].get('provenance', {}).get('policy_identity') != identity):
        raise ValueError('Episode/model event lineage differs')
    forbidden = {'application_restored', 'controller_replaced', 'replay_started', 'intervention', 'eyes_changed'}
    if any(event['kind'] in forbidden or event['kind'].startswith('memory_') or
           (event['kind'] == 'command_received' and event['command']['kind'] != 'step') for event in events):
        raise ValueError('Unsupported intervention/reset/replay history')
    count = manifest.get('recorded_ticks')
    if (type(count) is not int or not 1 <= count <= PROTOCOL['max_ticks_per_run'] or
            sorted(data['episodes']) != [0] or data['episodes'][0]['ticks'] != list(range(count)) or
            any(manifest.get(key) != final_state[value] for key, value in
                (('total_tick', 'total_tick'), ('final_phase', 'phase'), ('last_outcome', 'last_outcome'), ('metrics', 'metrics')))):
        raise ValueError('Recorded episode differs from the final owned boundary')
    phase, outcome = manifest['final_phase'], manifest['last_outcome']
    finishes = [event for event in events if event['kind'] == 'episode_finished']
    if phase in ('terminated', 'truncated'):
        if (not isinstance(outcome, dict) or outcome.get('reason') not in PROTOCOL['natural_termination'] or
                outcome.get('episode') != 0 or outcome.get('steps') != count or len(finishes) != 1 or
                finishes[0].get('outcome') != outcome or
                (phase == 'truncated') != (outcome['reason'] == 'time_limit')):
            raise ValueError('Natural terminal outcome is missing or inconsistent')
        reason = outcome['reason']
    elif phase == 'paused' and count == PROTOCOL['max_ticks_per_run'] and outcome is None and not finishes:
        reason = 'evaluation_tick_cap'
    else:
        raise ValueError('Incomplete episode is not a natural outcome or the frozen tick cap')
    latency, step_latency, inputs_hash = [], [], hashlib.sha256()
    for row in iter_ticks(run / 'recording'):
        features(row)
        if np.asarray(row['sensors']).dtype != np.float32:
            raise ValueError('Recorded sensor dtype differs from the exact Engine projection')
        input_value = {key: row[key] for key in ('cam_left', 'cam_right', 'sensors')}
        input_sha = state_digest(input_value)
        if row['tick'] == 0 and input_sha != initial['inputs']:
            raise ValueError('First actual policy inputs differ from the matched initial snapshot')
        inputs_hash.update(bytes.fromhex(input_sha))
        for name in ('cam_left', 'cam_right'):
            if not np.array_equal(row[name], row['raw_' + name]):
                raise ValueError('Evaluation cameras were masked or changed')
        if np.asarray(row['eyes']).dtype != np.bool_ or np.asarray(row['eyes']).shape != (2,) or not row['eyes'].all():
            raise ValueError('Evaluation requires both eyes enabled')
        for name, shape in (('action', (2,)), ('raw_output', (2,)), ('encoded_input', (136,)), ('population_stats', (0, 4))):
            value = np.asarray(row[name])
            if value.shape != shape or value.dtype.kind != 'f' or not np.isfinite(value).all():
                raise ValueError('Malformed male action/telemetry: ' + name)
        if np.any(np.abs(row['action']) > np.array([3., math.pi]) + 1e-6):
            raise ValueError('Recorded action units exceed the fixed mapping')
        if not math.isclose(float(row['simulation_time']), (row['tick'] + 1) * .02, abs_tol=1e-8, rel_tol=0):
            raise ValueError('Recorded control time differs')
        latency.append(artifacts._scalar(row['latency'], 'policy latency', True))
        step_latency.append(artifacts._scalar(row['step_latency'], 'physics latency', True))
    episode = data['episodes'][0]
    for name in ('reward', 'path_length', 'contact_ticks'):
        if not math.isclose(episode[name], manifest['metrics'][name], rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError('Recorded metrics differ from the owner')
    goal = artifacts._world(starts[0]['world'])['goal']
    return {'ticks': count, 'final_phase': phase, 'outcome': reason, 'last_outcome': outcome,
        'goal_reached': reason == 'goal', 'metrics': manifest['metrics'],
        'final_distance_metres': math.dist(episode['last_pose'][:2], goal[:2]),
        'simulation_seconds': count * .02, 'policy_timing': timing(latency),
        'physics_timing': timing(step_latency), 'policy_input_sequence_sha256': inputs_hash.hexdigest()}


def recording_paths(run):
    paths = sorted(path for folder in ('recording', 'snapshots') for path in (run / folder).rglob('*') if path.is_file())
    if len(paths) > 64:
        raise ValueError('Run file inventory exceeds the frozen recording bound')
    return paths


def inventory(run):
    paths = recording_paths(run)
    fingerprint = artifacts._fingerprint(paths)
    total = sum(item[2] for item in fingerprint)
    if total > PROTOCOL['recording_plus_snapshot_limit_bytes']:
        raise ValueError('Run recording and initial snapshot exceed 160 MiB')
    files = [{'path': path.relative_to(run).as_posix(), 'size_bytes': path.stat().st_size, 'sha256': file_sha(path)} for path in paths]
    if artifacts._fingerprint(paths) != fingerprint:
        raise ValueError('Run changed while hashing retained evidence')
    return files, fingerprint, total


def evaluate(args):
    root, assets, output = args.repo.resolve(), args.assets.resolve(), artifacts._safe_path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    report = {'version': 2, 'status': 'running', 'protocol': PROTOCOL, 'protocol_sha256': digest(PROTOCOL),
              'qualification_claims': [], 'runs': planned_runs(), 'paired_initial_states': []}
    supervisor, active, interrupted, fingerprints = None, None, [], []
    started = time.monotonic()
    old_handlers = {sig: signal.signal(sig, lambda sig, frame: interrupted.append(sig)) for sig in (signal.SIGTERM, signal.SIGINT)}
    owner_started = started

    def save():
        payload = (json.dumps(report, allow_nan=False, indent=2) + '\n').encode()
        if len(payload) > PROTOCOL['max_report_bytes']:
            raise ValueError('Evaluation report exceeds 4 MiB')
        temporary = output / 'evaluation.tmp'
        if supervisor is not None:
            supervisor.control_budget.check(len(payload), path=temporary)
        temporary.write_bytes(payload)
        temporary.replace(output / 'evaluation.json')

    def check_deadline(owner=True):
        now = time.monotonic()
        if interrupted or now - started > PROTOCOL['total_timeout_seconds'] or (owner and now - owner_started > PROTOCOL['owner_timeout_seconds']):
            raise TimeoutError('Evaluation interrupted or frozen total/owner deadline exceeded')

    def boundary(identifier):
        check_deadline()
        value = supervisor.describe(identifier)
        if value['status'] == 'failed':
            raise RuntimeError('Owner failed: ' + str(value.get('failure')))
        return value

    def wait(identifier, predicate):
        while True:
            value = boundary(identifier)
            if predicate(value):
                return value
            time.sleep(.01)

    try:
        report['sources_before'] = sources(root)
        report['model_identities'] = {name: resolve_profile(root, assets, name)[0] for name in PROTOCOL['controller_order']}
        supervisor = LabSupervisor(root, assets, output / 'runs', export_root=output,
            startup_timeout=PROTOCOL['startup_timeout_seconds'], step_timeout=PROTOCOL['progress_timeout_seconds'],
            storage_limits=StorageLimits(max_bytes=PROTOCOL['aggregate_limit_bytes'], min_free_bytes=PROTOCOL['min_free_bytes'],
                                         max_runs=16, max_snapshots=1, max_exports=1))
        # The shared budget covers reports as well as runs. Admit the full planned
        # per-run allowance before any owner; never silently shorten for storage.
        report['storage_admission'] = supervisor.budget.check(16 * PROTOCOL['recording_plus_snapshot_limit_bytes'], path=output / 'runs')
        (output / 'protocol.json').write_text(json.dumps(PROTOCOL, indent=2, allow_nan=False) + '\n')
        (output / 'evaluator.py').write_bytes(Path(__file__).read_bytes())
        save()
        first = None
        for entry in report['runs']:
            active, owner_started = entry, time.monotonic()
            check_deadline(owner=False)
            seed, controller = entry['seed'], entry['controller']
            identity = report['model_identities'][controller]
            identifier = supervisor.start({'controller': controller, 'device': 'cpu', 'seed': seed,
                'scenario': 'reproduction', 'texture': 'checker', 'policy_identity': identity})
            run = supervisor.path(identifier)
            entry.update(run_id=identifier, status='running', model_identity=identity)
            save()
            initial = wait(identifier, lambda view: view['status'] == 'ready' and view.get('sample') is not None)
            path, registered = supervisor.snapshot(identifier, initial['initial_snapshot_id'])
            if not registered['initial'] or registered['config']['policy_identity'] != identity:
                raise ValueError('Initial snapshot registry identity differs')
            entry['initial_snapshot'] = {'snapshot_id': registered['snapshot_id'], 'sha256': registered['sha256']}
            entry['initial_fingerprint'] = initial_fingerprint(read_snapshot(path), initial['sample']['world'], seed, identity)
            if controller == 'male-original':
                first = entry
            else:
                require_matched_initial(first['initial_fingerprint'], entry['initial_fingerprint'])
                report['paired_initial_states'].append({'seed': seed, 'original_run_id': first['run_id'],
                    'control_run_id': identifier, 'status': 'exact_match', 'fingerprint': entry['initial_fingerprint']})
            preflight = initial['storage_preflight']
            _, _, initial_bytes = inventory(run)
            estimate = initial_bytes + preflight['recording_bytes_estimate']
            entry['storage_preflight'] = {'initial_bytes': initial_bytes, 'estimated_total_bytes': estimate,
                                          'limit_bytes': PROTOCOL['recording_plus_snapshot_limit_bytes']}
            if estimate > PROTOCOL['recording_plus_snapshot_limit_bytes']:
                raise ValueError('Run admission estimate exceeds 160 MiB')
            save()
            state = step_episode(supervisor, identifier, initial, wait)
            owner = supervisor.workers[identifier]
            closed = supervisor.close(identifier)
            entry.update(close_status=closed['status'], owner_exitcode=owner.process.exitcode, owner_alive=owner.process.is_alive())
            if closed['status'] != 'closed' or owner.process.exitcode != 0 or owner.process.is_alive():
                raise ValueError('Owner did not close normally')
            entry.update(validate_recording(run, seed, identity, state, entry['initial_fingerprint']))
            files, fingerprint, size = inventory(run)
            fingerprints.append((run, files, fingerprint))
            check_deadline()
            entry.update(status='completed', files=files, recording_and_snapshot_bytes=size,
                         recording_sha256=digest(files), owner_wall_seconds=time.monotonic() - owner_started)
            save()
            print(json.dumps({key: entry[key] for key in ('seed', 'controller', 'run_id', 'status', 'ticks', 'outcome')}), flush=True)
            active = None
        report['summary'] = {controller: {'episodes': 8,
            'outcomes': dict(Counter(entry['outcome'] for entry in report['runs'] if entry['controller'] == controller)),
            'goal_count': sum(entry['goal_reached'] for entry in report['runs'] if entry['controller'] == controller)}
            for controller in PROTOCOL['controller_order']}
        report['dataset_sha256'] = digest([{'seed': entry['seed'], 'controller': entry['controller'],
            'recording_sha256': entry['recording_sha256'], 'initial_fingerprint': entry['initial_fingerprint']}
            for entry in report['runs']])
        report['status'] = 'completed'
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': str(error)[:2048]}
        report.update(status='failed', error=failure)
        if active is not None:
            active.update(status='failed', failure=failure)
    finally:
        report['cleanup'], report['finalization_errors'] = [], []

        def finalization_failure(stage, error):
            report['status'] = 'failed'
            report['finalization_errors'].append({'stage': stage, 'type': type(error).__name__, 'message': str(error)[:2048]})

        if supervisor is not None:
            # shutdown deliberately closes Process handles. Capture terminal facts
            # before disposal; never inspect a retained Process reference afterward.
            for identifier in list(supervisor.workers):
                try:
                    previous = next((entry for entry in report['runs'] if entry.get('run_id') == identifier and
                                     entry.get('close_status') == 'closed' and entry.get('owner_exitcode') == 0 and
                                     entry.get('owner_alive') is False), None)
                    if previous is not None:
                        detail = {'run_id': identifier, 'status': previous['close_status'],
                                  'owner_exitcode': previous['owner_exitcode'], 'owner_alive': previous['owner_alive']}
                    else:
                        closed = supervisor.close(identifier)
                        owner = supervisor.workers[identifier]
                        detail = {'run_id': identifier, 'status': closed['status'],
                                  'owner_exitcode': owner.process.exitcode, 'owner_alive': owner.process.is_alive()}
                    report['cleanup'].append(detail)
                    if detail['owner_alive']:
                        raise RuntimeError('Evaluation owner remained alive after close')
                except BaseException as error:
                    finalization_failure('owner_close:' + identifier, error)
            try:
                supervisor.shutdown()
                report['supervisor_shutdown'] = 'completed'
            except BaseException as error:
                report['supervisor_shutdown'] = 'failed'
                finalization_failure('supervisor_shutdown', error)
        else:
            report['supervisor_shutdown'] = 'not_created'

        # Each evidence check runs independently, including after cleanup failures.
        report['recording_fingerprints_unchanged'] = True
        for run, files, fingerprint in fingerprints:
            try:
                if (recording_paths(run) != [run / item['path'] for item in files] or
                        artifacts._fingerprint([run / item['path'] for item in files]) != fingerprint):
                    raise ValueError('An earlier recording changed before final publication')
            except BaseException as error:
                report['recording_fingerprints_unchanged'] = False
                finalization_failure('recording_fingerprint:' + run.name, error)
        report['sources_unchanged'] = False
        try:
            report['sources_unchanged'] = sources(root) == report.get('sources_before')
            if not report['sources_unchanged']:
                raise ValueError('Sources changed during evaluation')
        except BaseException as error:
            finalization_failure('source_identity', error)
        model_checks = report['model_identity_checks'] = {}
        for name, value in report.get('model_identities', {}).items():
            model_checks[name] = False
            try:
                model_checks[name] = resolve_profile(root, assets, name)[0] == value
                if not model_checks[name]:
                    raise ValueError('Model identity changed during evaluation')
            except BaseException as error:
                finalization_failure('model_identity:' + name, error)
        report['model_identities_unchanged'] = len(model_checks) == 2 and all(model_checks.values())
        try:
            if interrupted or time.monotonic() - started > PROTOCOL['total_timeout_seconds']:
                raise TimeoutError('Evaluation interrupted or final validation exceeded total deadline')
        except BaseException as error:
            finalization_failure('total_deadline', error)
        if report['status'] != 'completed':
            report.pop('summary', None)
        report['wall_seconds'] = time.monotonic() - started
        try:
            save()
        finally:
            for sig, handler in old_handlers.items():
                signal.signal(sig, handler)
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    sys.exit(evaluate(parser.parse_args()))
