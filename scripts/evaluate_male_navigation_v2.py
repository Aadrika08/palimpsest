"""Fixed 24-root teacher-free navigation development; held-out stays locked."""
import argparse
import copy
from dataclasses import asdict
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

from palimpsest import artifacts, male_model, male_navigation_research as research
from palimpsest.evaluate import bounded_process
from palimpsest.records import iter_ticks
from palimpsest.storage import StorageBudget, StorageLimits
import collect_male_navigation as common
import collect_male_navigation_v2 as contacts
from evaluate_male_closed_loop import require_matched_initial, validate_recording, inventory
from prepare_male_navigation_v2 import geometry_digests, raw_payload_update

ROOT = Path(__file__).resolve().parents[1]
MiB = 1024**2
PROFILE = 'male-navigation-development-v2'
CASES = tuple({'id': f'dev-{scene}-seed-{seed}-{arm}', 'scene_seed': scene,
               'training_seed': seed, 'arm': arm}
              for scene in range(3110, 3114) for seed in research.PAIR_SEEDS for arm in research.ARMS)


def check_case(case):
    if (not isinstance(case, dict) or set(case) != {'id', 'scene_seed', 'training_seed', 'arm'} or
            type(case['scene_seed']) is not int or type(case['training_seed']) is not int or case not in CASES):
        raise ValueError('Exact fresh development scene/seed/arm required')


def source_pins(root):
    p = contacts.plan(root)
    for name, pin in p['generator']['source_sha256'].items():
        if common.digest(Path(root)/'upstream/fly-gym'/name) != pin:
            raise ValueError('Frozen navigation generator changed')
    # Current reader/Engine identity, separate from the index's historical producer.
    scripts = sorted((Path(root)/'scripts').glob('*.py'))
    if len(scripts) > 256: raise ValueError('Current script inventory exceeds bound')
    return {'study_sha256': contacts.PLAN_SHA, 'contact_profile_sha256': contacts.PROFILE_SHA,
        'runtime_source': common.source_identity(root), 'reader': research.reader_sources(Path(root)),
        'scripts': {p.name: common.digest(p) for p in scripts},
        'upstream': p['generator']['source_sha256']}


def check_pins(root, expected):
    if source_pins(root) != expected: raise ValueError('Development source changed')


def admission(p):
    limits = p['limits']; per_tick = common.admission()['bytes_per_tick']
    aggregate = sum(limits['stage_allowances_bytes']['development'].values())
    # 4074 MiB inherited ledger + 8 MiB unspent writer headroom + 10 MiB
    # failure extras = 4092 MiB. Extras: pending numeric NPZ 1, owner result
    # pending 1, owner fallback JSON 4, extra final pending/failure JSON 4.
    # The inherited report allowance already covers the first final JSON.
    failure_extra = 10*MiB
    if (aggregate != limits['allowance_totals_bytes']['development'] or aggregate+8*MiB+failure_extra > 4*1024**3 or
            600*per_tick+4*MiB > 144*MiB or limits['per_owner_seconds'] != 180 or
            limits['per_owner_recording_plus_snapshot_bytes'] != 160*MiB):
        raise ValueError('Frozen development resource contract differs')
    return {'bytes_per_tick': per_tick, 'recording_bytes': 600*per_tick+4*MiB, 'aggregate_bytes': aggregate,
            'failure_extra_bytes': failure_extra, 'unspent_headroom_bytes': 8*MiB}


def owner_payload(value):
    """Exactly the bytes common.publish writes, including indentation/newline."""
    payload = (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()
    if len(payload) > MiB: raise ValueError('Owner result exceeds fixed one-MiB allowance')
    return payload


def native_sample(env):
    value = common.sample(env)
    # Shaft angles and ncon duplicate other telemetry and are unused by this
    # navigation admission. Preserve the four native fields that it checks.
    return {key: value[key] for key in ('pose', 'time_s', 'position_xyz', 'quaternion')}


def prior_metadata(root):
    index = research._index(root, root/research.INDEX_PATH, research.INDEX_SHA256)
    data = research._document(index['data_manifest'], {})
    rows = data['old_sources'] + data['new_sources']
    if len(rows) != 26 or data['counts']['held_out_sources'] != 0:
        raise ValueError('Exact admitted parent source metadata required')
    return {'data_manifest_sha256': index['data_manifest']['sha256'], 'sources': [
        {key: row[key] for key in ('run_id', 'episode', 'geometry', 'raw_payload_sha256')} |
        ({'initial_fingerprint': row['initial_fingerprint']} if 'initial_fingerprint' in row else {}) for row in rows]}


def initial_admission(world, fingerprint, case, prior, earlier, expected=None):
    """Evaluator-only metadata checks; no scene mutation or teacher access."""
    check_case(case)
    geometry = geometry_digests(world)
    for row in prior['sources']:
        if any(geometry[key] == row['geometry'][key] for key in ('layout', 'full_scene')):
            raise ValueError('Development geometry repeats admitted parent data')
        if row.get('initial_fingerprint', {}).get('inputs') == fingerprint['inputs']:
            raise ValueError('Development initial input repeats admitted parent data')
    for scene, previous in earlier.items():
        if int(scene) != case['scene_seed'] and (any(geometry[key] == previous['geometry'][key] for key in geometry) or
                fingerprint['inputs'] == previous['fingerprint']['inputs']):
            raise ValueError('Distinct development scenes repeat geometry or initial input')
    if expected is not None: require_matched_initial(expected, fingerprint)
    return geometry


def retained_packet(stage, arrays, result, budget):
    """One failed, otherwise unpublished packet; no fabricated missing fields."""
    import numpy as np
    if any(np.asarray(value).dtype.kind not in 'biuf' for value in arrays.values()):
        raise ValueError('Pending packet must contain numeric arrays only')
    if sum(np.asarray(value).nbytes for value in arrays.values()) > MiB:
        raise ValueError('Pending packet exceeds fixed diagnostic cap')
    stream = io.BytesIO(); np.savez(stream, **arrays); payload = stream.getvalue()
    if len(payload) > MiB: raise ValueError('Pending NPZ exceeds fixed diagnostic cap')
    path = Path(stage)/'first-rejected-packet.npz'; budget.check(len(payload), path=path)
    with path.open('xb') as file: file.write(payload); file.flush(); os.fsync(file.fileno())
    result['pending_packet'] = {'path': path.name, 'size_bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
        'fields': {key: {'shape': list(np.asarray(value).shape), 'dtype': np.asarray(value).dtype.str,
            'sha256': hashlib.sha256(np.asarray(value).tobytes(order='C')).hexdigest()} for key, value in arrays.items()}}


def bind_interval(raw, row, ownership, tick):
    import numpy as np
    if (raw['episode'], raw['tick']) != (0, tick) or row.get('tick') != tick:
        raise ValueError('Development interval index differs')
    if row.get('policy_calls') != 1 or type(row.get('policy_calls')) is not int or row.get('input_hashes') != common.input_hashes(raw):
        raise ValueError('Exactly one declared-input prediction required')
    if row.get('coverage_passed') is not True or type(row.get('callback_count')) is not int or row['callback_count'] != 10 or row.get('coverage_errors') != []:
        raise ValueError('Complete native callback coverage required')
    action, control = np.asarray(raw['action']), np.asarray(raw['control'])
    if (action.shape != (2,) or action.dtype != np.float32 or not np.isfinite(action).all() or
            control.shape != (2,) or control.dtype != np.float64 or not np.isfinite(control).all() or
            not np.array_equal(control, common.expected_control(action).astype(np.float64))):
        raise ValueError('Recorded navigation control differs from the one model action')
    if row.get('executed_action') != action.tolist(): raise ValueError('Retained action receipt differs')
    for suffix, sample in (('before', row['before_sample']), ('after', row['after_sample'])):
        for name, field, shape in (('position_xyz', 'position_xyz', (3,)), ('quaternion', 'quaternion', (4,))):
            value = np.asarray(raw['nav_dev_'+name+'_'+suffix])
            if value.shape != shape or value.dtype != np.float64 or not np.isfinite(value).all() or value.tolist() != sample[field]:
                raise ValueError('Evaluator native pose binding differs')
            if name == 'quaternion' and not math.isclose(float(np.linalg.norm(value)), 1., abs_tol=1e-8, rel_tol=0.):
                raise ValueError('Evaluator quaternion is not unit length')
        if not math.isclose(sample['time_s'], (tick+(suffix == 'after'))*.02, abs_tol=1e-9, rel_tol=0.):
            raise ValueError('Evaluator native time differs')
    if not np.array_equal(raw['pose'], row['before_sample']['pose']) or not np.array_equal(raw['next_pose'], row['after_sample']['pose']):
        raise ValueError('Recorded/evaluator poses differ')
    if any(key.startswith(('nav_advice', 'nav_teacher', 'nav_query', 'nav_transitions')) for key in raw):
        raise ValueError('Teacher telemetry is forbidden in development')
    return contacts.admit_contacts(raw, ownership, tick)


def run_episode(engine, probe, result, deadline, stage, budget):
    import numpy as np
    pending = []; calls = []; original_tick = engine.writer.tick; original_act = engine.policy.act
    def defer(episode, tick, **arrays):
        if pending: raise ValueError('More than one pending numeric interval')
        pending.append((episode, tick, arrays))
    def act(observation):
        calls.append(common.input_hashes(common.input_row(observation)))
        if len(calls) != 1: raise ValueError('Multiple policy predictions in one interval')
        return original_act(observation)
    engine.writer.tick = defer; engine.policy.act = act
    try:
        for tick in range(600):
            if time.monotonic() > deadline: raise TimeoutError('Development owner deadline')
            if engine.teacher is not None: raise ValueError('Development cannot access a teacher')
            calls.clear(); row = {'tick': tick, 'before_sample': native_sample(engine.env)}
            result['first_failure_packet'] = row
            probe.begin(tick)
            def end_interval():
                try:
                    interval = probe.end(); row['interval_contacts'] = interval
                    return interval
                except Exception as error:
                    row['contact_capture_error'] = type(error).__name__+': '+str(error)[:512]
                    stages = getattr(probe, 'stages', [])
                    row['obtainable_stage_count'] = len(stages)
                    row['obtainable_stages'] = copy.deepcopy(stages[:10])
                    raise
                finally: row['engine_total_tick_after'] = engine.total_tick
            try: common.command(engine, 'development-step-'+str(tick), 'step')
            except BaseException:
                try: end_interval()
                except Exception: pass  # Retained capture error cannot replace the step failure.
                raise
            interval = end_interval()
            if len(pending) != 1 or pending[0][:2] != (0, tick): raise ValueError('Missing raw executed interval')
            episode, recorded_tick, raw = pending[0]
            row.update(callback_count=interval['callback_count'], coverage_passed=interval['coverage_passed'],
                coverage_errors=interval['coverage_errors'], after_sample=native_sample(engine.env),
                policy_calls=len(calls), input_hashes=calls[0] if calls else None)
            raw.update(common.body.contact_arrays(interval))
            for suffix, sample in (('before', row['before_sample']), ('after', row['after_sample'])):
                for key in ('position_xyz', 'quaternion'): raw['nav_dev_'+key+'_'+suffix] = np.asarray(sample[key], np.float64)
            if sum(np.asarray(value).nbytes for value in raw.values()) > result['numeric_admission']['bytes_per_tick']:
                raise ValueError('Actual numeric interval exceeds admitted storage')
            row['executed_action'] = raw['action'].tolist()
            original_tick(episode, recorded_tick, **raw)  # Complete packet before any contact refusal.
            pending.pop(); result['rows'].append(row)
            incidence = bind_interval({'episode': episode, 'tick': tick, **raw}, row, result['contact_ownership'], tick)
            row['contacts'] = contacts.row_contacts(incidence); contacts.add_incidence(result['contact_incidence'], incidence)
            row.pop('interval_contacts'); row.pop('engine_total_tick_after'); result.pop('first_failure_packet')
            if engine.phase != 'paused': break
        return common.natural_boundary(len(result['rows']), engine.public_state())
    except BaseException:
        if pending:
            try: retained_packet(stage, pending[0][2], result, budget)
            except Exception as error: result['pending_packet_error'] = type(error).__name__+': '+str(error)[:512]
        raise
    finally:
        engine.writer.tick = original_tick; engine.policy.act = original_act
        result['executed_ticks'] = engine.total_tick
        result['published_rows'] = len(result['rows'])
        result['telemetry_wrappers_restored'] = True


def reduce_results(report):
    cases = report['cases']
    if list(cases) != [case['id'] for case in CASES] or any(cases[c['id']]['case'] != c for c in CASES):
        raise ValueError('Fixed 24-row development plan differs')
    counts = {f'{seed}:{arm}': 0 for seed in research.PAIR_SEEDS for arm in research.ARMS}
    complete = all(row['status'] == 'completed-recording' for row in cases.values())
    for row in cases.values():
        if row['status'] == 'completed-recording':
            if row['outcome'] not in ('goal', 'collision', 'stalled', 'time_limit'):
                raise ValueError('Unsupported natural development outcome')
            case = row['case']; counts[f"{case['training_seed']}:{case['arm']}"] += int(row['outcome'] == 'goal')
    return {'status': ('passed-development-gate' if all(counts[f'{seed}:augmented'] >= 3 for seed in research.PAIR_SEEDS)
            else 'failed-development-gate') if complete else 'not_admitted_infrastructure',
            'operational_status': 'completed' if complete else 'failed-infrastructure',
            'goals_by_seed_arm': counts, 'all_24_complete': complete,
            'held_out_status': 'locked_pending_separate_review', 'qualification_claims': []}


def worker(config):
    started = time.monotonic(); deadline = started+180
    root, run, stage = map(Path, (config['repo'], config['run'], config['stage']))
    budget = common.storage(config); engine = probe = None
    result = {'status': 'failed-infrastructure', 'case': config['case'], 'rows': [],
              'contact_incidence': contacts.empty_incidence(), 'executed_ticks': 0, 'published_rows': 0}
    try:
        check_case(config['case']); check_pins(root, config['source_pins'])
        if os.environ.get('CUDA_VISIBLE_DEVICES') != '': raise ValueError('CUDA must be explicitly hidden')
        import numpy as np
        import torch
        import mujoco
        from palimpsest.engine import Engine
        from palimpsest.replay import _register_initial
        from palimpsest.snapshots import _model_digest
        from palimpsest.profiles import validate_world
        # Only a fresh spawned owner may enter here. Establish both CPU thread
        # settings before checkpoint/model construction; no runtime fallback.
        torch.set_num_threads(1); torch.set_num_interop_threads(1)
        if (torch.cuda.is_initialized() or torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1 or
                mujoco.__version__ != '3.3.6' or mujoco.get_mjcb_control() is not None):
            raise ValueError('Fresh pinned one-thread CPU/native owner required')
        result['runtime'] = {**research.runtime_identity(), 'torch_build': torch.__version__, 'mujoco': mujoco.__version__,
            'intraop_threads': torch.get_num_threads(), 'interop_threads': torch.get_num_interop_threads(), 'cuda_initialized': False}
        budget.check(admission(contacts.plan(root))['recording_bytes']+16*MiB, path=run)
        run.mkdir(exist_ok=False)
        case = config['case']; binding = research.Binding(root/research.INDEX_PATH, research.INDEX_SHA256, case['training_seed'], case['arm'])
        engine = Engine.open(root, Path(config['assets']), run/'recording', controller='male-original', device='cpu',
            seed=case['scene_seed'], scenario='reproduction', texture='checker', run_id=run.name,
            max_bytes=144*MiB, storage_budget=budget, research_binding=binding, expected_policy_identity=config['identity'])
        if (engine.total_tick or engine.episode or engine.phase != 'paused' or engine.teacher is not None or
                np.any(engine.env.data.qvel) or np.any(engine.env.data.ctrl) or engine.env.data.time or engine.env._t or
                engine.env._speed or engine.env._stall_steps or np.any(engine.env._last_action) or
                not np.array_equal(engine.env._prev_xy, engine.env._base_xy()) or engine.eyes != {'left': True, 'right': True} or
                engine.env.max_steps != 600 or engine.env.n_obstacles != 20 or engine.env._action_scale != 2 or engine.env.end_on_collision):
            raise ValueError('Exact untouched reproduction boundary required')
        # This unchanged estimate includes spare teacher-array space; no teacher
        # arrays are recorded. It bounds the smaller development numeric schema.
        result['numeric_admission'] = common.numeric_admission([engine.observation[k] for k in ('cam_left', 'cam_right')], engine.policy.agent.cell.Nin)
        validate_world(engine.env)
        probe = common.body.ContactProbe(mujoco, engine.env)
        ownership = contacts.compiled_ownership(mujoco, engine.env.model, _model_digest(engine.env.model))
        result['contact_ownership'] = ownership
        if (ownership['base_body_id'] != probe.ownership['base_body_id'] or ownership['robot_bodies'] != probe.ownership['robot_bodies'] or
                any({k: actual[k] for k in original} != original for actual, original in
                    zip(ownership['geometries'], probe.ownership['geometries'], strict=True))):
            raise ValueError('Probe and compiled contact ownership differ')
        metadata = {'study_sha256': contacts.PLAN_SHA, 'model_index_sha256': research.INDEX_SHA256,
            'case': case, 'source_identity': config['identity'], 'contact_profile_sha256': contacts.PROFILE_SHA,
            'contact_ownership': ownership, 'teacher_queries': 0, 'generic_replay_qualified': False,
            'runtime': result['runtime'], 'data_manifest_sha256': config['prior']['data_manifest_sha256']}
        engine.writer.manifest.update(profile=PROFILE, navigation_development=metadata)
        _register_initial(engine, run, budget); common.initial_ready(run, 'ready')
        if (run/'snapshots/initial.snp').stat().st_size > 16*MiB: raise ValueError('Initial SNP exceeds cap')
        contacts.initial_contact_binding(run, ownership)
        result['initial_world'] = engine.world()
        fingerprint = common.initial_match(run, result['initial_world'], case, config['identity'], config.get('scene_initial'))
        result['initial_fingerprint'] = fingerprint
        result['geometry'] = initial_admission(result['initial_world'], fingerprint, case, config['prior'], config['earlier_scenes'], config.get('scene_initial'))
        metadata['initial_fingerprint'] = fingerprint; metadata['geometry'] = result['geometry']
        probe.install()  # All scientific initial/disjointness checks precede action 1.
        result['outcome'] = run_episode(engine, probe, result, deadline, stage, budget)
        result['final_state'] = engine.public_state(); result['status'] = 'completed-recording'
    except BaseException as error:
        result.update(status='failed-infrastructure', error={'type': type(error).__name__, 'message': str(error)[:1024]})
    finally:
        if probe is not None:
            try: probe.close(); result['callback_restored'] = mujoco.get_mjcb_control() is None
            except Exception as error: result.update(status='failed-infrastructure', callback_error=str(error)[:512])
        if engine is not None:
            result['executed_ticks'] = engine.total_tick
            try: engine.close(); result['engine_closed'] = True
            except Exception as error: result.update(status='failed-infrastructure', cleanup_error=str(error)[:512])
    if not result.get('callback_restored') or not result.get('engine_closed') or result['executed_ticks'] != len(result['rows']):
        result['status'] = 'failed-infrastructure'
    result['wall_seconds'] = time.monotonic()-started
    try:
        owner_payload(result)
        common.publish(stage/'result.json', result, budget, deadline, lambda: check_pins(root, config['source_pins']))
    except Exception as error:
        common.write_json(stage/'failure.json', {'status': 'failed-infrastructure', 'error': str(error)[:1024], 'result': result},
                          max_bytes=4*MiB, storage_budget=budget)
        return False
    return result['status'] == 'completed-recording' and time.monotonic() <= deadline


def admit_record(run, result, config):
    import numpy as np
    case = config['case']; check_case(case)
    manifest = common.read_json(run/'recording/manifest.json', maximum=4*MiB)
    meta = manifest.get('navigation_development', {})
    binding = research.Binding(Path(config['repo'])/research.INDEX_PATH, research.INDEX_SHA256, case['training_seed'], case['arm'])
    if (result.get('status') != 'completed-recording' or result.get('case') != case or
            any(result.get(k) is not True for k in ('callback_restored', 'engine_closed', 'telemetry_wrappers_restored')) or
            manifest.get('profile') != PROFILE or manifest.get('teacher_privileged') is not False or
            meta.get('case') != case or meta.get('source_identity') != config['identity'] or
            meta.get('study_sha256') != contacts.PLAN_SHA or meta.get('model_index_sha256') != research.INDEX_SHA256 or
            meta.get('contact_profile_sha256') != contacts.PROFILE_SHA or meta.get('contact_ownership') != result.get('contact_ownership') or
            meta.get('teacher_queries') != 0 or type(meta.get('teacher_queries')) is not int or meta.get('generic_replay_qualified') is not False or
            meta.get('runtime') != result.get('runtime') or meta.get('data_manifest_sha256') != config['prior']['data_manifest_sha256']):
        raise ValueError('Development model/contact/profile/cleanup lineage differs')
    common.initial_ready(run, 'ready'); contacts.initial_contact_binding(run, result['contact_ownership'])
    fingerprint = common.initial_match(run, result['initial_world'], case, config['identity'], config.get('scene_initial'))
    geometry = initial_admission(result['initial_world'], fingerprint, case, config['prior'], config['earlier_scenes'], config.get('scene_initial'))
    if fingerprint != result['initial_fingerprint'] or fingerprint != meta.get('initial_fingerprint') or geometry != result.get('geometry') or geometry != meta.get('geometry'):
        raise ValueError('Initial scientific receipt differs')
    summary = validate_recording(run, case['scene_seed'], config['identity'], result['final_state'], fingerprint,
                                 research_provenance=binding.provenance())
    declared = result['numeric_admission']
    if common.numeric_admission([np.zeros((128, 128, 3), np.uint8)]*2, declared['input_nodes']) != declared:
        raise ValueError('Numeric storage preflight differs')
    incidence = contacts.empty_incidence(); payload = hashlib.sha256(); count = 0
    for count, raw in enumerate(iter_ticks(run/'recording'), 1):
        if count > 600 or count > len(result['rows']): raise ValueError('Unexpected numeric row')
        if sum(np.asarray(value).nbytes for key, value in raw.items() if key not in ('episode', 'tick')) > declared['bytes_per_tick']:
            raise ValueError('Retained numeric interval exceeds cap')
        row = result['rows'][count-1]; observed = bind_interval(raw, row, result['contact_ownership'], count-1)
        if row.get('contacts') != contacts.row_contacts(observed): raise ValueError('Cached contact receipt differs')
        contacts.add_incidence(incidence, observed); raw_payload_update(payload, raw)
    if (count != len(result['rows']) or type(result.get('executed_ticks')) is not int or result['executed_ticks'] != count or
            type(result.get('published_rows')) is not int or result['published_rows'] != count or summary['ticks'] != count or
            result.get('contact_incidence') != incidence or result.get('outcome') != common.natural_boundary(count, result['final_state']) or
            result['outcome'] != summary['outcome']):
        raise ValueError('Complete natural outcome/interval ledger differs')
    if payload.hexdigest() in {row['raw_payload_sha256'] for row in config['prior']['sources']}:
        raise ValueError('Complete development payload repeats admitted parent data')
    if list((run/'snapshots').glob('*.snp')) != [run/'snapshots/initial.snp'] or (run/'snapshots/initial.snp').stat().st_size > 16*MiB:
        raise ValueError('Exactly one bounded initial SNP required')
    files, _, size = inventory(run)
    return {**summary, 'raw_payload_sha256': payload.hexdigest(), 'initial_fingerprint': fingerprint,
            'geometry': geometry, 'contact_incidence': incidence, 'files': files, 'source_bytes': size}


def run_cases(report, owner):
    for case in CASES:
        row = report['cases'][case['id']]
        try:
            row['status'] = 'running'
            admitted = owner(case, row)
            row.update(admitted, status='completed-recording')
            report['owners_completed'] += 1; report['numeric_ticks'] += admitted['ticks']
        except Exception as error:
            row.update(status='failed-infrastructure', error={'type': type(error).__name__, 'message': str(error)[:1024]})
            report['status'] = 'failed-infrastructure'
            return False
    report['status'] = 'completed-development'
    return True


def candidates(root, assets):
    # Each resolve admits the complete six-model index before returning one
    # identity. No Torch/model/native construction occurs in this parent.
    return {f'{seed}:{arm}': research.resolve(root, assets, root/research.INDEX_PATH, research.INDEX_SHA256,
        seed, arm, 'male-original')[0] for seed in research.PAIR_SEEDS for arm in research.ARMS}


def verify(args):
    started = time.monotonic(); deadline = started+1800
    root, assets, output = Path(args.repo).resolve(), Path(args.assets).resolve(), artifacts._safe_path(args.output)
    if root != ROOT or not output.is_relative_to(root/'runs') or output == root/'runs' or output.exists():
        raise ValueError('Exact producer and fresh child of its runs directory required')
    index = research._index(root, root/research.INDEX_PATH, research.INDEX_SHA256)
    producer = artifacts._safe_path(root/index['producer_root'])
    if any(output == path or output.is_relative_to(path) or path.is_relative_to(output) for path in (producer, assets)):
        raise ValueError('Output overlaps frozen producer/assets')
    p = contacts.plan(root); estimates = admission(p); pins = source_pins(root); prior = prior_metadata(root)
    if (p['reserves']['closed_loop_dev_scene_seeds'] != list(range(3110, 3114)) or
            p['reserves']['model_seeds'] != list(research.PAIR_SEEDS) or
            set(p['reserves']['closed_loop_dev_scene_seeds']) & set(p['reserves']['learner_state_train_scene_seeds']+p['reserves']['closed_loop_held_out_scene_seeds'])):
        raise ValueError('Frozen scene/seed disjointness differs')
    output.parent.mkdir(parents=True, exist_ok=True)
    required_free = p['limits']['combined_incremental_free_reservation_bytes']+p['limits']['free_floor_bytes']
    if shutil.disk_usage(output.parent).free < required_free:
        raise ValueError('Whole-study prospective capacity reservation is unavailable')
    output.mkdir(exist_ok=False)
    budget = StorageBudget((output,), StorageLimits(max_bytes=4*1024**3, min_free_bytes=1024**3,
        max_runs=24, max_snapshots=1, max_exports=1), headroom_bytes=8*MiB)
    config = {'repo': str(root), 'assets': str(assets), 'source_pins': pins, 'prior': prior,
        'storage': {'roots': [str(output)], 'limits': asdict(budget.limits), 'headroom_bytes': 8*MiB}}
    report = {'status': 'running', 'study_sha256': contacts.PLAN_SHA, 'model_index_sha256': research.INDEX_SHA256,
        'profile': PROFILE, 'contact_profile_sha256': contacts.PROFILE_SHA, 'source_pins': pins,
        'owners_completed': 0, 'numeric_ticks': 0, 'qualification_claims': [],
        'cases': {case['id']: {'case': case, 'status': 'not_started'} for case in CASES},
        'whole_study_free_required_bytes': required_free, 'admission_estimate': estimates,
        'data_manifest_sha256': prior['data_manifest_sha256'], 'held_out_status': 'locked_pending_separate_review'}
    try:
        with budget.lock():
            from palimpsest.assets import verify_assets
            budget.check(estimates['aggregate_bytes']+estimates['failure_extra_bytes'], path=output)
            report['assets_before'] = verify_assets(root, assets)
            if not report['assets_before']['ok']: raise ValueError('Pinned runtime assets unavailable')
            identities = candidates(root, assets); report['identities_before'] = identities
            scenes = {}; payloads = []
            def owner(case, row):
                if time.monotonic() >= deadline: raise TimeoutError('Development stage deadline')
                check_pins(root, pins)
                stage = output/case['id']; stage.mkdir(); run = stage/uuid.uuid4().hex
                previous = scenes.get(case['scene_seed'])
                child = {**config, 'case': case, 'stage': str(stage), 'run': str(run),
                    'identity': identities[f"{case['training_seed']}:{case['arm']}"], 'earlier_scenes': scenes,
                    'scene_initial': previous['fingerprint'] if previous else None}
                common.write_json(output/'progress.json', report, max_bytes=4*MiB, storage_budget=budget)
                allowance = min(180., deadline-time.monotonic())
                if allowance <= 0: raise TimeoutError('No remaining owner admission time')
                row['supervision'] = bounded_process([sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(child)],
                    stage/'supervision', allowance, {**os.environ, 'PYTHONPATH': str(root/'src'),
                        'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '1', 'CUDA_VISIBLE_DEVICES': ''},
                    log_max_bytes=MiB, storage_budget=budget)
                # Read/retain obtainable owner failure evidence before refusing disposition.
                for name in ('result.json', 'failure.json'):
                    path = stage/name
                    if path.is_file():
                        row[name] = {'path': str(path), 'sha256': common.digest(path), 'size_bytes': path.stat().st_size}
                result = common.read_json(stage/'result.json', maximum=MiB)
                supervision = row['supervision']; elapsed = supervision.get('elapsed_seconds')
                if (supervision.get('status') != 'completed' or type(supervision.get('returncode')) is not int or supervision['returncode'] != 0 or
                        any(key in supervision for key in ('error', 'failure')) or type(elapsed) not in (int, float) or
                        not math.isfinite(elapsed) or not 0 <= elapsed <= allowance):
                    raise ValueError('Owner failed normal bounded disposition')
                admitted = admit_record(run, result, child)
                if any(old_scene != case['scene_seed'] and old_hash == admitted['raw_payload_sha256'] for old_scene, old_hash in payloads):
                    raise ValueError('Distinct development scene repeats complete payload')
                payloads.append((case['scene_seed'], admitted['raw_payload_sha256']))
                scenes.setdefault(case['scene_seed'], {'geometry': admitted['geometry'], 'fingerprint': admitted['initial_fingerprint']})
                if time.monotonic() > deadline: raise TimeoutError('Late owner readmission')
                return {**admitted, 'run': str(run)}
            run_cases(report, owner)
            report['matched_scene_initials'] = scenes
            # Each final check remains independently obtainable after an owner failure.
            errors = []
            for key, operation in (('assets_after', lambda: verify_assets(root, assets)),
                    ('identities_after', lambda: candidates(root, assets)), ('final_source_pins', lambda: source_pins(root)),
                    ('artifacts_sha256', lambda: {k: v for k, v in common.file_hashes(output).items()
                        if k not in ('progress.json', '.palimpsest-storage.lock')})):
                try: report[key] = operation()
                except Exception as error: errors.append(key+': '+str(error)[:512])
            if (report.get('assets_after') != report['assets_before'] or report.get('identities_after') != identities or
                    report.get('final_source_pins') != pins): errors.append('Final source/assets/candidates differ')
            if report['status'] == 'completed-development' and (report['owners_completed'] != 24 or
                    len(scenes) != 4 or len(list(output.rglob('*.snp'))) != 24): errors.append('Incomplete fixed owner/initial plan')
            report['finalization_errors'] = errors
            if errors: report['status'] = 'failed-infrastructure'
            report['admission'] = reduce_results(report)
            report['wall_seconds_before_publication'] = time.monotonic()-started
            budget.check(0, path=output)
        if report['status'] != 'completed-development':
            report['admission'].update(status='not_admitted_infrastructure', operational_status='failed-infrastructure')
        if time.monotonic() > deadline: raise TimeoutError('Late development finalization/lease release')
        common.publish(output/'report.json', report, budget, deadline, lambda: check_pins(root, pins))
        if time.monotonic() > deadline: raise TimeoutError('Late development publication')
    except BaseException as error:
        report.update(status='failed-infrastructure', error={'type': type(error).__name__, 'message': str(error)[:1024]})
        report['admission'] = reduce_results(report)
        report['admission'].update(status='not_admitted_infrastructure', operational_status='failed-infrastructure')
        common.write_json(output/'failure.json', report, max_bytes=4*MiB, storage_budget=budget)
    return report


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--worker': return 0 if worker(json.loads(sys.argv[2])) else 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--assets', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    started = time.monotonic(); report = verify(parser.parse_args())
    print(json.dumps({'status': report['status'], 'owners_completed': report['owners_completed'],
                      'numeric_ticks': report['numeric_ticks'], 'admission': report['admission']}))
    # Actual controls must retain the separate 1850 normal-through-exit and 1860
    # enclosing termination clocks. This script's 1800 limit covers its own work.
    return 0 if report['status'] == 'completed-development' and time.monotonic()-started <= 1800 else 1


if __name__ == '__main__': raise SystemExit(main())
