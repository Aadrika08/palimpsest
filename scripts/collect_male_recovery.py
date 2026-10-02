"""M7-REC-COVER-1: two standalone development sources, no training admission."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
import uuid

from palimpsest import body_profile as body
from verify_body_adaptation import read_json, cleanup_observed
from verify_body_gains import write_json
from verify_body_runtime import digest
from verify_task_starts import storage
from verify_task_phases import initial_ready
from verify_body_calibration import sample
from verify_endurance import source_identity, descendants
from verify_tasks import file_hashes

MiB = 1024**2
PROFILE = 'teacher-recovery-development-v2'
TEACHER_SHA256 = '5edca9a587dea0a2996856e42a96013aab1b1b0a277eacb74b7fc4270c55c586'
CASES = [{'id': 'recovery-north-2100', 'seed': 2100, 'start_pose': [-.95, .12, 0.]},
         {'id': 'recovery-south-2101', 'seed': 2101, 'start_pose': [-.95, -.12, 0.]}]
PROTOCOL = {'id': 'M7-REC-COVER-1', 'version': 2, 'profile': PROFILE, 'cases': CASES,
    'goal_xy': [2., 0.], 'scenario': 'reproduction', 'texture': 'checker', 'controller': 'teacher', 'device': 'cpu',
    'teacher_sha256': TEACHER_SHA256, 'upstream_commit': '8d964599119b420de67ee259434d273651a1a76d',
    'prefix_max_ticks': 32, 'prefix_action': [.7, 0.], 'source_max_ticks': 120,
    'prefix_handoff': 'Permanent before-action handoff to same expert on first independently sampled bad contact or 32-interval cap; no reactivation',
    'expert': 'Exactly one unchanged teacher.act before every interval, including prefix; no teacher reset at handoff',
    'labels': 'expert_action is separate from recorded actual action; post-prefix equality exact; old training loader rejects profile',
    'numeric_columns': {'recovery_teacher_before': ['count', 'direction', 'previous_bad_contact'],
        'recovery_teacher_after': ['count', 'direction', 'previous_bad_contact'],
        'recovery_transitions': ['started', 'completed', 'old_label_replaced']},
    'counter': '45 back queries (40+5), no turn/forward phase; final query may complete and restart, replacing old emitted action',
    'coverage': 'each first cycle: observed contact/sign at start, 45 emitted back targets without replacement, actual post-prefix reverse, later observed clearance',
    'contact': 'independent prior contact-cache sensor plus ten actual pre-control caches/end; intentional robot-obstacle1 allowed, no continuous collision claim',
    'owners': 2, 'maximum_numeric_ticks': 240, 'snapshot_files': 2, 'snapshot_max_bytes': 16*MiB,
    'recording_max_bytes': 144*MiB, 'recording_plus_snapshot_max_bytes': 160*MiB,
    'output_max_bytes': 1024*MiB, 'min_free_bytes': 1024*MiB,
    'result_max_bytes': 4*MiB, 'report_max_bytes': 4*MiB, 'log_max_bytes': MiB, 'headroom_bytes': 8*MiB,
    'child_timeout_seconds': 180, 'inner_timeout_seconds': 420, 'outer_timeout_seconds': 480,
    'outcomes': 'collect both valid natural/capped sources before scoring; infrastructure/invariant/storage stops remaining not_started',
    'pipeline': body.PROTOCOL['pipeline'], 'student': 'unchanged 388 RGB/contact/bearing features; privileged teacher/private history not student inputs',
    'scope': 'two mirrored development contact/reverse sources only; no training, held-out reads, learned/general/task/body/physical qualification'}
PROTOCOL_SHA256 = hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def harness_hashes():
    return {name: digest(Path(__file__).with_name(name)) for name in ('collect_male_recovery.py',
        'verify_task_starts.py', 'verify_task_phases.py', 'verify_body_adaptation.py', 'verify_body_gains.py',
        'verify_body_runtime.py', 'verify_body_calibration.py', 'verify_endurance.py', 'verify_tasks.py')}


def upstream_contract(root):
    path = Path(root)/'upstream/fly-gym/agents/teacher_analytic_agent.py'
    if digest(path) != TEACHER_SHA256:
        raise ValueError('Pinned teacher source differs')
    return TEACHER_SHA256


def geometry_preflight():
    from palimpsest.memory_world import validate_layout
    return {case['id']: validate_layout(start_pose=case['start_pose'], goal_xy=PROTOCOL['goal_xy']) for case in CASES}


def admission(observation):
    import numpy as np
    images = [observation[key] for key in ('cam_left', 'cam_right')]
    if any(a.dtype != np.uint8 or a.shape != (128, 128, 3) for a in images):
        raise ValueError('Pinned 128x128 RGB eyes required')
    per_tick = 2*sum(a.nbytes for a in images) + body.MAX_TICK_BYTES + 8192
    allowances = {'numeric_bytes': 240*per_tick, 'snapshot_bytes': 2*16*MiB,
        'result_bytes': 2*4*MiB, 'native_logs_bytes': 8*MiB, 'control_bytes': 16*MiB,
        'atomic_native_staging_bytes': 128*MiB, 'headroom_bytes': 8*MiB}
    total = sum(allowances.values()); recording = 120*per_tick + 4*MiB
    if total > PROTOCOL['output_max_bytes'] or recording > PROTOCOL['recording_max_bytes']:
        raise ValueError('Frozen recovery storage estimate exceeds quotas')
    return {'aggregate_bytes': total, 'per_recording_bytes': recording, 'allowances': allowances}


def teacher_state(teacher):
    state = {'phase': teacher._rec_phase, 'count': teacher._rec_step_count,
             'direction': teacher._rec_turn_dir, 'previous_bad_contact': teacher._prev_bad_contact}
    if (state['phase'] not in (None, 'back') or type(state['count']) is not int or
            state['count'] not in (range(1, 45) if state['phase'] else (0,)) or
            state['direction'] not in (-1., 1.) or type(state['previous_bad_contact']) is not bool or
            (teacher.recovery_back_steps, teacher.recovery_turn_steps) != (40, 5)):
        raise ValueError('Pinned teacher recovery state/defaults differ')
    return state


def validate_query(row):
    import numpy as np
    before, after, contact = row['before'], row['after'], row['contact']
    completed = before['phase'] == 'back' and before['count'] == 44
    started = after['phase'] == 'back' and after['count'] == 1
    if before['phase'] == 'back' and not completed:
        if after != {**before, 'count': before['count']+1}:
            raise ValueError('Active recovery counter/latch/direction changed unexpectedly')
    else:
        expected_start = contact['bad'] and not before['previous_bad_contact']
        if started != expected_start or after['previous_bad_contact'] != contact['bad'] or (
                not started and (after['phase'] is not None or after['count'] != 0 or after['direction'] != before['direction'])):
            raise ValueError('Recovery edge/completion state differs from pinned teacher')
        if started and after['direction'] != (-1. if contact['angle'] > 0 else 1.):
            raise ValueError('Recovery heading sign differs from independently sampled angle')
    expert = np.asarray(row['expert_action'])
    if expert.shape != (2,) or not np.isfinite(expert).all():
        raise ValueError('Invalid expert target')
    if before['phase'] == 'back' or started:
        direction = after['direction'] if started else before['direction']
        if row['expert_action'] != np.array([-.35, .1*direction], np.float32).tolist():
            raise ValueError('Pinned back action differs')
    return {'started': started, 'completed': completed, 'old_label_replaced': completed and started}


def query_teacher(teacher, env):
    bad, _, angle = env._has_collision()  # Independently sample the prior cached sensor before teacher query.
    if type(bad) not in (bool,) or (bad and (angle is None or not math.isfinite(float(angle)) or abs(angle) > math.pi)) or (not bad and angle is not None):
        raise ValueError('Invalid independent contact sensor')
    row = {'before': teacher_state(teacher), 'contact': {'bad': bad, 'angle': None if angle is None else float(angle)}}
    started = time.perf_counter(); action = teacher.act(env)
    row.update(after=teacher_state(teacher), expert_action=action.tolist(), expert_latency_seconds=time.perf_counter()-started)
    row['transition'] = validate_query(row)
    return row


def prefix_for_query(tick, active, bad):
    if type(tick) is not int or not 0 <= tick < 120 or type(active) is not bool or type(bad) is not bool:
        raise ValueError('Exact bounded tick and boolean prefix/contact state required')
    return active and tick < 32 and not bad


def executed_action(tick, expert, prefix):
    import numpy as np
    if type(tick) is not int or not 0 <= tick < 120 or type(prefix) is not bool:
        raise ValueError('Exact bounded recovery tick required')
    # Engine._action(..., manual=False) applies exactly this float32 conversion.
    return np.asarray(PROTOCOL['prefix_action'] if prefix else expert, np.float32).tolist()


def bind_action(tick, raw, active):
    sensor = float(raw['sensors'][0])
    if sensor not in (0., 1.): raise ValueError('Invalid raw contact selector')
    active = prefix_for_query(tick, active, bool(sensor))
    if (bool(raw['recovery_prefix']) != active or
            raw['action'].tolist() != executed_action(tick, raw['recovery_expert_action'].tolist(), active)):
        raise ValueError('Raw sensor/persistent prefix/actual action binding differs')
    return active


def score_coverage(rows):
    if [row['tick'] for row in rows] != list(range(len(rows))) or len(rows) > 120:
        raise ValueError('Missing/out-of-order recovery query interval')
    for index, row in enumerate(rows):
        if row['transition'] != validate_query(row) or (index and rows[index-1]['after'] != row['before']):
            raise ValueError('Recovery history/transition discontinuity')
    first = next((row['tick'] for row in rows if row['transition']['started']), None)
    window = [] if first is None else rows[first:first+45]
    complete = (len(window) == 45 and window[-1]['transition']['completed'] and
                not window[-1]['transition']['old_label_replaced'])
    start_contact = bool(window and window[0]['contact']['bad'] and window[0]['stage0_intended_contact'])
    actual_reverse = any(row['prefix'] is False and row['action'][0] < 0 for row in window)
    clearance = bool(complete and any(not row['contact']['bad'] and not row['stage0_intended_contact'] for row in rows[first+45:]))
    return {'passed': complete and start_contact and actual_reverse and clearance,
        'first_cycle': {'start_tick': first, 'queries': len(window), 'completed': complete,
                        'emitted_old_cycle_targets': len(window)-int(bool(window and window[-1]['transition']['old_label_replaced'])),
                        'old_label_replaced': bool(window and window[-1]['transition']['old_label_replaced'])},
        'start_contact': start_contact, 'actual_post_prefix_reverse': actual_reverse, 'subsequent_clearance': clearance,
        'sensor_contact_rows': sum(row['contact']['bad'] for row in rows),
        'stage0_contact_rows': sum(row['stage0_intended_contact'] for row in rows)}


def contact_admission(interval, robot_names):
    if not interval['coverage_passed'] or interval['callback_count'] != 10 or len(interval['stages']) != 10:
        raise ValueError('Incomplete read-only contact-stage coverage')
    for packet in [*interval['stages'], interval['end']]:
        for pair in packet['pairs']:
            if pair['classification'] == 'unexpected_robot_contact':
                names = pair['geom_names']
                if len(names) != 2 or sum(name in robot_names for name in names) != 1 or 'obstacle1' not in names:
                    raise ValueError('Unexpected robot/self/world contact outside declared obstacle1 approach')
    return any(pair['classification'] == 'unexpected_robot_contact' for pair in interval['stages'][0]['pairs'])


def fresh_boundary(engine):
    import numpy as np
    from palimpsest.engine import _teacher_fingerprint
    env = engine.env
    if (engine.controller != 'teacher' or engine.phase != 'paused' or engine.total_tick or engine.episode_step or engine.episode or
            engine.task_state is not None or engine.memory is not None or env.data.time != 0. or env._t != 0 or
            env._speed != 0. or env._stall_steps != 0 or np.any(env.data.qvel) or np.any(env.data.ctrl) or np.any(env._last_action) or
            env.path_to_draw is not None or env.target_to_draw is not None or
            env.visited != {env._bin_of(env._base_xy(), env.explore_binsize)} or not np.array_equal(env._prev_xy, env._base_xy()) or
            any(getattr(env.planner, key) is not None for key in ('_cached_occ', '_cached_obstacles_hash', '_cached_clearance')) or
            teacher_state(engine.teacher) != {'phase': None, 'count': 0, 'direction': 1., 'previous_bad_contact': False} or
            engine.teacher._xy_prev is not None or engine.teacher._path is not None or
            _teacher_fingerprint(engine.teacher) != engine._teacher_reset_identity):
        raise ValueError('Requires untouched fresh teacher/pose-dependent episode state')


def author_world(engine, case):
    import mujoco
    from palimpsest import memory_world
    from palimpsest.profiles import validate_world
    from palimpsest.snapshots import _model_digest
    if case not in CASES: raise ValueError('Only the two predeclared development cases are allowed')
    geometry_preflight(); fresh_boundary(engine)
    env = engine.env; old = engine.world(); original_model = _model_digest(env.model)
    if env.model.actuator_gear.tolist() != [[3., 0., 0., 0., 0., 0.]]*2:
        raise ValueError('Pinned unmodified two-motor gears required')
    memory_world.configure(env, memory_world.initial_state(close_subject_id=None))
    env._goal_xy[:] = PROTOCOL['goal_xy']; env.model.site_pos[env.goal_site_id, :2] = PROTOCOL['goal_xy']
    env.place_robot(*case['start_pose'], env.data.qpos.copy(), env.data.qvel.copy())
    mujoco.mj_forward(env.model, env.data)
    env._prev_xy = env._base_xy().copy(); env._reset_exploration(); engine.observation = env._get_obs()
    validate_world(env); fresh_boundary(engine)
    if math.dist(sample(env)['pose'], case['start_pose']) > 1e-7 or env._has_collision()[0]:
        raise ValueError('Declared start differs or starts with robot contact; refusing relocation')
    context = {'case': case, 'old_world': old, 'new_world': engine.world(), 'original_model_sha256': original_model,
        'actual_model_sha256': _model_digest(env.model), 'world_profile': memory_world.PROFILE,
        'world_profile_sha256': memory_world.PROFILE_SHA256, 'protocol_sha256': PROTOCOL_SHA256,
        'scope': 'standalone authored world; original episode_started remains history; generic playback not qualified'}
    engine.revision += 1
    override_sha256 = hashlib.sha256(json.dumps(context, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    engine.writer.manifest.update(profile=PROFILE, recovery_protocol=PROTOCOL, recovery_protocol_sha256=PROTOCOL_SHA256,
        recovery_world_override=context, recovery_world_override_sha256=override_sha256, initial_world=context['new_world'])
    engine.writer.event('recovery_world_authored', context=context, override_sha256=override_sha256,
                        revision=engine.revision, harness_sha256=harness_hashes())
    return context


def step_override(engine, tick, action):
    message = {'id': f'recovery-step-{tick}', 'kind': 'step', 'expected_state': engine.phase,
               'expected_episode': engine.episode, 'expected_revision': engine.revision}
    before = engine.total_tick
    if engine.submit(message)['status'] != 'queued': raise ValueError('Recovery step was not queued')
    engine.advance(action_override=action)
    if engine.submit(message)['status'] != 'applied' or engine.total_tick != before+1:
        raise ValueError('Recovery step did not apply exactly one interval')


def worker(config):
    import numpy as np
    import mujoco
    from palimpsest.engine import Engine
    from palimpsest.replay import _register_initial
    from palimpsest.snapshots import _model_digest
    stage, run = Path(config['stage']), Path(config['run']); budget = storage(config); engine = probe = None
    result = {'status': 'failed-infrastructure', 'case': config['case'], 'run': str(run), 'rows': []}; pending = []
    try:
        upstream_contract(Path(config['repo']))
        if source_identity(Path(config['repo'])) != config['runtime_source'] or harness_hashes() != config['harness_sha256']:
            raise ValueError('Frozen source/harness changed before owner')
        if mujoco.get_mjcb_control() is not None: raise ValueError('Refusing existing global control callback')
        prospective = admission({key: np.zeros((128, 128, 3), np.uint8) for key in ('cam_left', 'cam_right')})
        budget.check(prospective['aggregate_bytes'] if config['first_owner'] else prospective['per_recording_bytes']+16*MiB, path=run)
        run.mkdir(exist_ok=False)
        engine = Engine.open(Path(config['repo']), Path(config['assets']), run/'recording', controller='teacher', device='cpu',
            seed=config['case']['seed'], scenario='reproduction', texture='checker', run_id=run.name, max_bytes=144*MiB, storage_budget=budget)
        result['override'] = author_world(engine, config['case']); result['admission'] = admission(engine.observation)
        if result['admission'] != prospective: raise ValueError('Actual eyes differ from prospective storage admission')
        probe = body.ContactProbe(mujoco, engine.env)
        robot_names = {entry['name'] for entry in probe.ownership['geometries'] if entry['owner'] == 'robot'}
        result['contact_ownership'] = {**probe.ownership, 'model_sha256': _model_digest(engine.env.model)}
        headers = Path(mujoco.__file__).parent/'include/mujoco'
        result['pipeline_evidence'] = {'mujoco_version': mujoco.__version__,
            'installed_headers_sha256': {name: digest(headers/name) for name in ('mjmodel.h', 'mujoco.h')},
            'upstream_files_sha256': {name: digest(Path(config['repo'])/'upstream/fly-gym/environment'/name)
                for name in ('mujoco_two_cam_env_random_obstacles.py', 'mujoco_model_random_obstacles.xml')},
            'integrator_enum': int(engine.env.model.opt.integrator), 'physics_dt_s': float(engine.env.model.opt.timestep),
            'frame_skip': engine.env.frame_skip, 'disableflags': int(engine.env.model.opt.disableflags)}
        engine.writer.manifest['recovery_contact_ownership'] = result['contact_ownership']
        _register_initial(engine, run, budget); initial_ready(run, 'ready')
        original_tick = engine.writer.tick
        def defer_tick(episode, tick, **arrays):
            if pending: raise ValueError('More than one unpublished interval')
            pending.append((episode, tick, arrays))
        engine.writer.tick = defer_tick; probe.install(); prefix = True
        for tick in range(120):
            before = sample(engine.env); row = query_teacher(engine.teacher, engine.env)
            prefix = prefix_for_query(tick, prefix, row['contact']['bad'])
            row.update(tick=tick, prefix=prefix, before_sample=before)
            result['first_failure_packet'] = row  # Replaced/cleared only after a fully admitted interval.
            actual = executed_action(tick, row['expert_action'], prefix); probe.begin(tick)
            step_override(engine, tick, actual); interval = probe.end()
            row.update(action=engine.last_transition['action'].tolist(), after_sample=sample(engine.env), interval_contacts=interval)
            # Complete callback packets are published before unexpected-pair rejection.
            if len(pending) != 1 or pending[0][:2] != (0, tick): raise ValueError('Missing numeric interval')
            episode, recorded_tick, arrays = pending.pop()
            arrays.update(body.contact_arrays(interval), recovery_expert_action=np.asarray(row['expert_action'], np.float32),
                recovery_prefix=np.array(prefix), recovery_teacher_before=np.array([row['before']['count'], row['before']['direction'], row['before']['previous_bad_contact']], np.float64),
                recovery_teacher_after=np.array([row['after']['count'], row['after']['direction'], row['after']['previous_bad_contact']], np.float64),
                recovery_transitions=np.array([row['transition'][name] for name in ('started', 'completed', 'old_label_replaced')], bool),
                recovery_expert_latency=np.array(row['expert_latency_seconds']))
            original_tick(episode, recorded_tick, **arrays)
            result['rows'].append(row)
            row['stage0_intended_contact'] = contact_admission(interval, robot_names)
            sensor = engine.last_transition['sensors']
            if (row['action'] != actual or bool(sensor[0]) != row['contact']['bad'] or
                    float(sensor[1]) != float(np.float32(row['contact']['angle'] or 0.))):
                raise ValueError('Actual action/pre-observation contact differs from declared expert/prefix/cache')
            row.update(contact_counts=arrays['body_contact_counts'].tolist(), callback_count=interval['callback_count'])
            row.pop('interval_contacts')  # Full successful packets are in the lossless numeric arrays.
            result.pop('first_failure_packet', None)
            if engine.phase != 'paused': break
        result.update(status='completed-recording', recorded_ticks=len(result['rows']), final_state=engine.public_state(),
            coverage=score_coverage(result['rows']), model_unchanged=_model_digest(engine.env.model) == result['override']['actual_model_sha256'])
        reason = (engine.last_outcome or {}).get('reason')
        if ((engine.phase == 'paused' and len(result['rows']) != 120) or
                (engine.phase == 'terminated' and reason not in ('collision', 'stalled', 'goal')) or
                (engine.phase == 'truncated' and reason != 'time_limit') or
                engine.phase not in ('paused', 'terminated', 'truncated') or not result['model_unchanged']):
            raise ValueError('Invalid outcome/model mutation')
    except Exception as error:
        result.update(status='failed-infrastructure', error={'type': type(error).__name__, 'message': str(error)[:1024]})
    finally:
        if probe is not None:
            try: probe.close()
            except Exception as error: result.update(status='failed-infrastructure', callback_error=str(error)[:512])
        if engine is not None:
            if result['status'] == 'failed-infrastructure':
                try:
                    import io
                    images = ({key: value for key, value in pending[0][2].items() if 'cam_' in key} if pending else
                              {key: engine.observation[key] for key in ('cam_left', 'cam_right')})
                    buffer = io.BytesIO(); np.savez(buffer, **images); payload = buffer.getvalue()
                    if len(payload) > MiB: raise ValueError('Failure cameras exceed bound')
                    path = stage/'failure-cameras.npz'; budget.check(len(payload), path=path)
                    with path.open('xb') as stream: stream.write(payload)
                    result['failure_cameras_sha256'] = digest(path)
                except Exception as error: result['diagnostic_error'] = str(error)[:512]
            try: engine.close(); result['engine_closed'] = True
            except Exception as error: result.update(status='failed-infrastructure', cleanup_error=str(error)[:512])
        result['callback_restored'] = mujoco.get_mjcb_control() is None
        if not result['callback_restored']: result['status'] = 'failed-infrastructure'
        write_json(stage/'result.json', result, max_bytes=4*MiB, storage_budget=storage(config, True))
    return result['status'] == 'completed-recording'


def gate(config):
    from palimpsest.evaluate import bounded_process
    from palimpsest.assets import verify_assets
    from palimpsest.records import iter_ticks
    output = Path(config['output']); root = Path(config['repo']); budget = storage(config); report = read_json(output/'report.json', maximum=4*MiB)
    try:
        geometry_preflight(); upstream_contract(root)
        report['assets_before'] = verify_assets(root, Path(config['assets']))
        if not report['assets_before']['ok']: raise ValueError('Pinned assets unavailable')
        env = {**os.environ, 'PYTHONPATH': str(root/'src'), 'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '2', 'MPLBACKEND': 'Agg'}
        for number, case in enumerate(CASES):
            budget.check_count('runs', number); stage = output/case['id']; run = stage/uuid.uuid4().hex
            child = {**config, 'stage': str(stage), 'run': str(run), 'case': case, 'first_owner': number == 0,
                     'runtime_source': report['runtime_source'], 'harness_sha256': report['harness_sha256']}
            item = report['cases'][case['id']]; item['status'] = 'running'
            write_json(output/'report.json', report, max_bytes=4*MiB, storage_budget=storage(config, True))
            supervision = bounded_process([sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(child)], stage, 180,
                env, log_max_bytes=MiB, storage_budget=budget)
            item.update(status='failed-infrastructure', supervision=supervision)
            result = read_json(stage/'result.json', maximum=4*MiB)
            item.update(result_path=str(stage/'result.json'), result_sha256=digest(stage/'result.json'),
                result={key: value for key, value in result.items() if key not in ('rows', 'first_failure_packet')})
            if (supervision.get('status') != 'completed' or supervision.get('returncode') != 0 or
                    'error' in supervision or 'failure' in supervision or result['status'] != 'completed-recording' or
                    not result.get('engine_closed') or not result['callback_restored']): raise ValueError('Owner/cleanup failed')
            rows = list(iter_ticks(run/'recording')); manifest = read_json(run/'recording/manifest.json')
            if manifest['status'] != 'completed' or manifest['profile'] != PROFILE or not 1 <= len(rows) <= 120 or len(rows) != len(result['rows']):
                raise ValueError('Incomplete or incorrectly admitted standalone recording')
            prefix = True
            for tick, (raw, row) in enumerate(zip(rows, result['rows'])):
                prefix = bind_action(tick, raw, prefix)
                if (int(raw['episode']) != 0 or int(raw['tick']) != tick or raw['action'].tolist() != row['action'] or
                        raw['recovery_expert_action'].tolist() != row['expert_action'] or bool(raw['recovery_prefix']) != row['prefix'] or
                        raw['body_contact_counts'].tolist() != row['contact_counts'] or row['callback_count'] != 10 or
                        raw['recovery_teacher_before'].tolist() != [row['before'][key] for key in ('count', 'direction', 'previous_bad_contact')] or
                        raw['recovery_teacher_after'].tolist() != [row['after'][key] for key in ('count', 'direction', 'previous_bad_contact')] or
                        raw['recovery_transitions'].tolist() != [row['transition'][key] for key in ('started', 'completed', 'old_label_replaced')] or
                        row['action'] != executed_action(tick, row['expert_action'], prefix)): raise ValueError('Expert/executed label/cursor binding differs')
                validate_query(row)
            item['status'] = 'completed-recording'; report['owners_completed'] += 1; report['numeric_ticks'] += len(rows)
            item['coverage'] = score_coverage(result['rows'])
            initial_ready(run, 'ready')
        if len(list(output.rglob('*.snp'))) != 2 or report['numeric_ticks'] > 240: raise ValueError('Frozen count limits differ')
        report.update(protocol_status='completed', snapshot_files=2,
            status='passed' if all(item['coverage']['passed'] for item in report['cases'].values()) else 'failed-functional')
    except Exception as error:
        report.update(status='failed-infrastructure', protocol_status='incomplete', error={'type': type(error).__name__, 'message': str(error)[:1024]})
    finally:
        report['assets_after'] = verify_assets(root, Path(config['assets']))
        if report.get('assets_before') != report['assets_after']: report['status'] = 'failed-infrastructure'
        write_json(output/'report.json', report, max_bytes=4*MiB, storage_budget=storage(config, True))
    return report['status'] == 'passed'


def supervision_matches(report, supervision):
    if 'error' in supervision or 'failure' in supervision: return False
    if report.get('status') == 'passed': return supervision.get('status') == 'completed' and supervision.get('returncode') == 0
    return (report.get('status') == 'failed-functional' and report.get('protocol_status') == 'completed' and
        report.get('owners_completed') == 2 and report.get('snapshot_files') == 2 and
        all(item.get('status') == 'completed-recording' for item in report['cases'].values()) and
        supervision.get('status') == 'failed' and supervision.get('returncode') == 1)


def verify(args):
    from dataclasses import asdict
    from palimpsest.storage import StorageBudget, StorageLimits
    from palimpsest.evaluate import bounded_process
    root, assets, output = args.repo.resolve(), args.assets.resolve(), args.output.resolve()
    geometry_preflight(); upstream_contract(root)
    if assets.is_relative_to(output) or output.is_relative_to(assets): raise ValueError('Output overlaps immutable assets')
    output.mkdir(parents=True, exist_ok=False)
    limits = StorageLimits(max_bytes=1024*MiB, min_free_bytes=1024*MiB, max_runs=2, max_snapshots=1, max_exports=1)
    budget = StorageBudget((output,), limits, headroom_bytes=8*MiB)
    config = {'repo': str(root), 'assets': str(assets), 'output': str(output),
              'storage': {'roots': [str(output)], 'limits': asdict(limits), 'headroom_bytes': 8*MiB}}
    report = {'status': 'running', 'protocol': PROTOCOL, 'protocol_sha256': PROTOCOL_SHA256,
        'runtime_source': source_identity(root), 'harness_sha256': harness_hashes(), 'numeric_ticks': 0, 'owners_completed': 0,
        'cases': {case['id']: {'status': 'not_started', 'case': case} for case in CASES}}
    known = {}; errors = []; stop = threading.Event()
    def sample_owned():
        try:
            while not stop.is_set():
                for row in descendants(os.getpid()):
                    if row['pid'] not in known and len(known) >= 256: raise ValueError('Finite PID inventory exceeds bound')
                    known[row['pid']] = row['start_ticks']
                stop.wait(.25)
        except Exception as error: errors.append(str(error)[:512]); stop.set()
    sampler = threading.Thread(target=sample_owned, daemon=True); started = time.monotonic()
    with budget.lock():
        write_json(output/'report.json', report, max_bytes=4*MiB, storage_budget=storage(config, True)); sampler.start()
        try:
            env = {**os.environ, 'PYTHONPATH': str(root/'src'), 'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '2'}
            supervision = bounded_process([sys.executable, str(Path(__file__).resolve()), '--gate', json.dumps(config)],
                output/'inner-supervision', 420, env, log_max_bytes=MiB, storage_budget=budget)
            report = read_json(output/'report.json', maximum=4*MiB); report['inner_supervision'] = supervision
            if not supervision_matches(report, supervision): report['status'] = 'failed-infrastructure'
        except Exception as error: report.update(status='failed-infrastructure', error={'type': type(error).__name__, 'message': str(error)[:1024]})
        finally:
            stop.set(); sampler.join(timeout=2.)
            report['cleanup'] = {**cleanup_observed(dict(known)), 'sampler_stopped': not sampler.is_alive(), 'sample_errors': errors,
                'observed_owned_processes': [{'pid': pid, 'start_ticks': value} for pid, value in sorted(known.items())],
                'scope': 'finite .25s PID/start sampling; not universal transient-process proof'}
            report.update(wall_seconds=time.monotonic()-started, final_source=source_identity(root), final_harness=harness_hashes())
            if (report['cleanup']['forced_signals'] or report['cleanup']['survivors'] or errors or sampler.is_alive() or
                    report['runtime_source'] != report['final_source'] or report['harness_sha256'] != report['final_harness']): report['status'] = 'failed-infrastructure'
            report['usage'] = budget.usage(); report['artifacts_sha256'] = {key: value for key, value in file_hashes(output).items() if key not in ('report.json', '.palimpsest-storage.lock')}
            write_json(output/'report.json', report, max_bytes=4*MiB, storage_budget=storage(config, True))
    return report


def main():
    if len(sys.argv) == 3 and sys.argv[1] in ('--worker', '--gate'):
        return 0 if (worker if sys.argv[1] == '--worker' else gate)(json.loads(sys.argv[2])) else 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    report = verify(parser.parse_args()); print(json.dumps({'status': report['status'], 'numeric_ticks': report['numeric_ticks'], 'error': report.get('error')}))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
