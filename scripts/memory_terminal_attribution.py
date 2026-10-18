"""One registered read-only terminal diagnostic; no supervisor/model replay."""
from collections import deque
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import time

RUN_ID = 'c2ed14671d124705a93616c09cd8985e'
REGISTRATION_SHA = '61b295030e692c580331d5ab282ab380da87e7b7d3718f4e31809238835543a1'
CLOSE_SHA = 'ca92aaf06a964ec26daf651ff9203fa313039179a3840b66e107a2977699102d'
AUDIT_SHA = '49fb72963fc607da5a427cc04dfd5fd4e044b6b72e086853f30a18f5a84d8082'
MiB = 1024**2


def checked(path):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Input/output path must be absolute without a symlink')
    return path


def deadline_check(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('Original diagnostic clock exhausted')


def digest(path):
    with checked(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path, *, registration=False):
    path = checked(path)
    if path.stat().st_size > MiB:
        raise ValueError('Control input exceeds 1 MiB')
    def reject(value):
        raise ValueError('Nonfinite JSON value: '+value)
    payload = path.read_bytes()
    value = json.loads(payload, parse_constant=reject)
    if registration:
        value.update(registration_path=str(path), registration_sha256=hashlib.sha256(payload).hexdigest())
    return value


def verify_registration(reg):
    if digest(Path(reg['registration_path'])) != reg['registration_sha256']:
        raise ValueError('Registration changed after its bytes were read')


def verify_loaded_sources(repo):
    root = checked(repo)/'src/palimpsest'
    for name, module in tuple(sys.modules.items()):
        if name == 'palimpsest' or name.startswith('palimpsest.'):
            path = checked(getattr(module, '__file__', ''))
            if not path.is_relative_to(root) or path.suffix != '.py':
                raise ValueError('Imported project code is outside the hashed checkout: '+name)


def verify_files(rows, deadline):
    paths = []
    for row in rows:
        deadline_check(deadline)
        path = checked(row['path'])
        if (not path.is_file() or path.stat().st_size != row['bytes'] or digest(path) != row['sha256']):
            raise ValueError('Input identity mismatch: '+str(path))
        paths.append(path)
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate registered input')
    deadline_check(deadline)
    return len(paths)


def require_registered(expected, registered):
    found = {str(checked(row['path'])): row for row in registered}
    for row in expected:
        path = str(checked(row['path']))
        if path not in found:
            raise ValueError('Unregistered consumed file: '+path)
        if any(found[path].get(key) != row[key] for key in ('bytes', 'sha256') if key in row):
            raise ValueError('Registered identity differs from original inventory: '+path)


def visibility(pose, xy, circles):
    from palimpsest import memory_task, memory_decision_world as world
    x, y, yaw = memory_task._numbers(pose, 3)
    px, py = memory_task._numbers(xy, 2)
    if type(circles) not in (list, tuple) or len(circles) > 20:
        raise ValueError('Invalid bounded occluders')
    circles = [memory_task._numbers(c, 3) for c in circles]
    if any(c[2] <= 0 for c in circles):
        raise ValueError('Invalid occluder radius')
    distance = math.hypot(px-x, py-y)
    if not math.isfinite(distance):
        raise ValueError('Nonfinite displacement')
    angle = 0. if distance == 0 else math.remainder(math.atan2(py-y, px-x)-yaw, 2*math.pi)
    blocked = [i for i, (ox, oy, radius) in enumerate(circles)
               if world._segment_distance([ox, oy], [x, y], [px, py]) <= radius]
    failed = (['range'] if distance > 4. else []) + (['fov'] if abs(angle) > math.pi/2 else [])
    failed += ['occlusion'] if blocked else []
    return {'distance_m': distance, 'bearing_degrees': math.degrees(angle),
            'range_pass': distance <= 4., 'fov_pass': abs(angle) <= math.pi/2,
            'blocking_circle_indices': blocked, 'visible': not failed, 'failed_predicates': failed}


def attribute(case, rows, events, target, terminal_tick, event_tick, deadline=math.inf):
    from palimpsest import memory_decision as decision, memory_decision_world as world
    if not 1 <= len(rows) <= 64:
        raise ValueError('Diagnostic requires 1 to 64 control rows')
    ticks = [int(row['tick']) for row in rows]
    if ticks != list(range(terminal_tick-len(rows), terminal_tick)) or any(row['episode'] != 0 for row in rows):
        raise ValueError('Window must end immediately before the terminal boundary')
    world.validate_case(case)
    route = next(r for r in world.public_graph(case)['routes'] if target in r['waypoint_ids'])
    target_index = route['waypoint_ids'].index(target)
    if target_index == 0:
        raise ValueError('Target has no predecessor')
    predecessor = route['waypoint_ids'][target_index-1]
    packets, selections = {}, []
    for event in events:
        deadline_check(deadline)
        tick = event.get('episode_step')
        if type(tick) is not int or not ticks[0] <= tick <= terminal_tick:
            continue
        if event['kind'] == 'memory_sensed':
            if tick in packets:
                raise ValueError('Duplicate sensed packet')
            packets[tick] = event['packet']
        detail = event.get('detail', {})
        if event['kind'] == 'memory_decision' and detail.get('kind') == 'memory_bridge':
            if detail['tick'] != tick:
                raise ValueError('Bridge tick differs from event')
            selections.append({'tick': tick, 'landmark_id': detail['landmark_id']})
    if set(packets) != set(range(ticks[0], terminal_tick+1)):
        raise ValueError('Missing/extra window packet')
    if [row['tick'] for row in selections] != ticks:
        raise ValueError('Missing, duplicate, out-of-order or terminal bridge')
    if any(row['landmark_id'] not in {item['id'] for item in packets[row['tick']]['landmarks']}
           for row in selections):
        raise ValueError('Selected bridge landmark is absent from its packet')
    poses = [(int(row['tick']), list(map(float, row['pose']))) for row in rows]
    poses.append((terminal_tick, list(map(float, rows[-1]['next_pose']))))
    output = []
    for tick, pose in poses:
        deadline_check(deadline)
        inputs = world.reconstruct_inputs(case, pose, tick, event_tick=event_tick, gate_result='not_requested')
        packet = decision.capture_symbolic(*inputs, episode_id='episode-0', tick=tick)
        if packets[tick] != packet:
            raise ValueError('Recorded packet differs from actual-pose reconstruction')
        detail = visibility(pose, case['landmarks'][target], inputs[2])
        present = any(item['id'] == target for item in packet['landmarks'])
        if detail['visible'] != present:
            raise ValueError('Visibility decomposition differs from sensor packet')
        output.append({'tick': tick, 'pose': pose, **detail,
                       'predecessor_arrived': predecessor in packet['arrivals'],
                       'target_arrived': target in packet['arrivals']})
    selected = [r['tick'] for r in selections if r['landmark_id'] == target]
    first = min(selected) if selected else None
    failed = output[-1]['failed_predicates']
    return {'status': 'attributed' if len(failed) == 1 else 'multiple-predicates' if failed else 'unresolved',
            'target': target, 'predecessor': predecessor, 'window_controls': len(rows),
            'window_start_tick': ticks[0], 'terminal': output[-1], 'observations': output,
            'first_target_selection_in_window': first,
            'selection_scope': 'left-censored' if first == ticks[0] else 'observed-in-window' if selected else 'not-recorded-in-window',
            'selected_targets_in_window': selections,
            'predecessor_arrival_ticks': [r['tick'] for r in output if r['predecessor_arrived']],
            'interpretation': 'Geometric attribution at recorded poses only; no counterfactual fix or new task qualification'}


@contextmanager
def writer_lease():
    path = checked(Path.home()/'.cache/palimpsest/writer.lock')
    with os.fdopen(os.open(path, os.O_RDONLY|os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('Wrong real-user writer lease')
        fcntl.flock(stream, fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def write_json(path, data, budget):
    payload = (json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    if len(payload) > MiB:
        raise ValueError('Control output exceeds 1 MiB')
    budget.check(len(payload), path=path)
    with checked(path).open('xb') as stream:
        stream.write(payload)


def run(reg):
    started = time.monotonic(); deadline = started+300
    output = checked(reg['output'])
    if output.exists():
        raise FileExistsError('Diagnostic already consumed; no retry')
    repo = Path(__file__).resolve().parents[1]
    pub = repo/'docs/reports/memory-terminal-attribution-evidence'
    if (reg.get('schema') != 'memory-terminal-attribution-registration-v1'
            or output != repo/'runs/memory-terminal-attribution-v1'
            or reg.get('publication_root') != str(pub) or reg.get('window_controls') != 64
            or reg.get('seconds_cap') != 300 or reg.get('output_bytes_cap') != 128*MiB
            or reg.get('run_id') != RUN_ID):
        raise ValueError('Registration differs from fixed diagnostic allocation')
    from palimpsest.storage import StorageBudget, StorageLimits, GiB
    budget = StorageBudget((output, pub), StorageLimits(max_bytes=128*MiB, min_free_bytes=2*GiB), headroom_bytes=64*MiB)
    with writer_lease():
        budget.check(MiB, path=output/'consumed.json')
        output.mkdir(parents=True, exist_ok=False)
        write_json(output/'consumed.json', {'started_monotonic': started, 'deadline_monotonic': deadline,
                                          'registration_sha256': reg['registration_sha256']}, budget)
        try:
            if not sys.dont_write_bytecode:
                raise ValueError('Diagnostic requires PYTHONDONTWRITEBYTECODE=1')
            count = verify_files(reg['inputs']+reg['sources'], deadline)
            verify_registration(reg)
            verify_loaded_sources(repo)
            if sys.executable != reg['python'] or digest(Path(sys.executable).resolve()) != reg['python_sha256']:
                raise ValueError('Interpreter identity changed')
            from importlib.metadata import version
            if version('numpy') != reg['numpy_version']:
                raise ValueError('NumPy identity changed')
            if digest(Path(reg['pilot_registration'])) != REGISTRATION_SHA or digest(Path(reg['close'])) != CLOSE_SHA:
                raise ValueError('Wrong authoritative pilot input')
            if digest(Path(reg['audit'])) != AUDIT_SHA:
                raise ValueError('Wrong independent owner audit')
            prior = read_json(reg['pilot_registration']); close = read_json(reg['close'])
            execution_path = checked(reg['execution'])
            if digest(execution_path) != close['driver_execution_sha256']:
                raise ValueError('Execution differs from authoritative close')
            execution = read_json(execution_path)
            original = checked(prior['output'])
            recording = original/'stage/runs'/RUN_ID/'recording'
            job_path = original/'stage/jobs'/(RUN_ID+'.json')
            if checked(reg['recording']) != recording or checked(reg['job']) != job_path:
                raise ValueError('Unregistered recording/job path')
            consumed = [{'path': str(original/row['path']), 'bytes': row['bytes'], 'sha256': row['sha256']}
                        for row in execution['artifact_index']
                        if row['path'].startswith('stage/runs/'+RUN_ID+'/recording/')
                        or row['path'] == 'stage/jobs/'+RUN_ID+'.json']
            if not consumed or {str(p) for p in recording.rglob('*') if p.is_file()} != {
                    row['path'] for row in consumed if row['path'] != str(job_path)}:
                raise ValueError('Recording inventory changed')
            consumed += [{'path': reg[key]} for key in ('pilot_registration', 'close', 'execution', 'audit')]
            require_registered(consumed, reg['inputs'])
            sources = [{'path': str(repo/name), 'sha256': sha}
                       for name, sha in prior['source_identity']['source_sha256'].items()]
            sources += [{'path': str(Path(__file__).resolve())},
                        {'path': str(repo/'docs/plans/memory-terminal-attribution.md')}]
            require_registered(sources, reg['sources'])
            audit = read_json(reg['audit']); job = read_json(reg['job'])
            if (audit['job_id'] != 'local-null/own' or audit['run_id'] != RUN_ID
                    or audit['total_ticks'] != 880 or audit['event_tick'] != 728
                    or audit['outcome']['type'] != 'CueUnavailable' or not audit['raw_audit_pass']
                    or job['run_id'] != RUN_ID or job['condition'] != 'own' or job['case']['kind'] != 'null'):
                raise ValueError('Unexpected diagnostic input owner/terminal')
            manifest = read_json(recording/'manifest.json')
            if manifest['recorded_ticks'] != 153 or manifest['status'] == 'running' or manifest['memory_case'] != job['case']:
                raise ValueError('Unexpected recording identity/count/status')
            from palimpsest.records import iter_ticks
            verify_registration(reg)
            verify_loaded_sources(repo)
            rows = deque(maxlen=64); total = 0
            for row in iter_ticks(recording):
                deadline_check(deadline); total += 1
                if total > 153:
                    raise ValueError('Recording exceeds registered rows')
                rows.append({k: row[k] for k in ('episode', 'tick', 'pose', 'next_pose')})
            if total != 153:
                raise ValueError('Missing registered rows')
            events = []
            path = recording/'events.jsonl'
            if path.stat().st_size > 32*MiB:
                raise ValueError('Event input exceeds bound')
            with path.open('rb') as stream:
                for sequence, line in enumerate(stream):
                    deadline_check(deadline)
                    if len(line) > MiB or not line.endswith(b'\n'):
                        raise ValueError('Malformed bounded event')
                    event = json.loads(line)
                    if event['sequence'] != sequence:
                        raise ValueError('Event sequence mismatch')
                    tick = event.get('episode_step')
                    if type(tick) is int and 816 <= tick <= 880:
                        events.append(event)
            target = audit['outcome']['message'].removeprefix('selected_waypoint_unavailable: ')
            result = attribute(job['case'], list(rows), events, target, 880, 728, deadline)
            verified = verify_files(reg['inputs']+reg['sources'], deadline)
            verify_registration(reg)
            verify_loaded_sources(repo)
            result.update(schema='memory-terminal-attribution-v1', input_files_verified=verified,
                          input_files_before=count, input_bytes_unchanged=True,
                          started_monotonic=started, closed_monotonic=time.monotonic(),
                          deadline_monotonic=deadline, registration_sha256=reg['registration_sha256'],
                          native_owners=0, physics_steps=0, snapshots_decoded=0,
                          r2_complete=False, qualification_claims=[], held_out_used=False,
                          pilot_mechanism_observed=False, pilot_capped_score=900)
            deadline_check(deadline)
            write_json(output/'result.json', result, budget)
            deadline_check(deadline)
            return result
        except Exception as error:
            write_json(output/'failure.json', {'status': 'failed', 'type': type(error).__name__,
                'message': str(error), 'elapsed_seconds': time.monotonic()-started,
                'r2_complete': False, 'qualification_claims': []}, budget)
            raise


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    args = parser.parse_args()
    registration = read_json(args.registration.absolute(), registration=True)
    result = run(registration)
    print(json.dumps({'status': result['status'], 'terminal': result['terminal'],
                      'elapsed_seconds': result['closed_monotonic']-result['started_monotonic']}))
