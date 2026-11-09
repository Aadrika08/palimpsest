"""Synthetic S0e collection in the real T-e recording format; a test fixture, never a producer.

Run as ``python -I -B <this> <config json>`` with PALIMPSEST_M7_V4_PINS naming a locator for
the T-e port. It imports the T-e port modules read-only from ``config['port_root']`` and
derives every bound value with the port's own functions (numeric admission, ownership map,
teacher transitions, input hashes, expected controls, snapshot writer, initial fingerprint,
incidence accumulator), so the unchanged ``admit_record`` must accept an untampered owner.
No engine, simulator, model or Torch is used. ``config['tamper']`` corrupts one owner:
``nonfinite`` (a NaN in an unvalidated float array), ``incidence`` (owner incidence differs
from its recording) or ``label`` (returned advice differs from the recorded label).
"""
import hashlib
import importlib
import json
from pathlib import Path
import sys

CONFIG = json.loads(sys.argv[1])
PORT = Path(CONFIG['port_root'])
sys.path[:0] = [str(PORT/'src'), str(PORT/'scripts')]
np = importlib.import_module('numpy')
nav = importlib.import_module('collect_male_navigation_v2')
v1 = importlib.import_module('collect_male_navigation')
recovery = importlib.import_module('collect_male_recovery')
body = importlib.import_module('palimpsest.body_profile')
records = importlib.import_module('palimpsest.records')
snapshots = importlib.import_module('palimpsest.snapshots')


def ownership():
    contacts = nav.CONTACTS
    tree = {**contacts['expected_robot_body_tree'], **{f'obstacle{x}_body': 'world' for x in range(20)}}
    names = ['world', *tree]
    ids = {name: i for i, name in enumerate(names)}
    bodies = [{'body_id': ids[n], 'name': n, 'parent_id': 0 if n == 'world' else ids[tree[n]]} for n in names]
    robot = set(contacts['expected_robot_body_tree'])
    geoms = [{'geom_id': i, 'name': g, 'body_name': b, 'body_id': ids[b], 'owner': 'robot' if b in robot else 'world',
              'contype': contacts['expected_collision_masks'][g][0], 'conaffinity': contacts['expected_collision_masks'][g][1]}
             for i, (g, b) in enumerate(contacts['expected_geom_body_names'].items())]
    value = {'geometries': geoms, 'robot_bodies': [b for b in bodies if b['name'] in robot],
             'world_bodies': [b for b in bodies if b['name'] not in robot], 'base_body_id': ids['base'],
             'model_sha256': hashlib.sha256(b'synthetic-model').hexdigest()}
    nav.ownership_map(value)
    return value


def hexdigest(*parts): return hashlib.sha256(json.dumps(parts).encode()).hexdigest()


def owner(stage, case, ticks, identity, own, tamper):
    run = stage/f'run-{case["id"]}'
    (run/'snapshots').mkdir(parents=True)
    zeros = np.zeros((128, 128, 3), np.uint8)
    world = {'arena': 5.0, 'pose': [0.0, 0.0, 0.0], 'obstacles': [[1.0, 1.0, 0.1]], 'goal': [2.0, 2.0, 0.2]}
    snapshot = {'application': {'seed': case['scene_seed'], 'controller': identity['controller'], 'episode': 0, 'total_tick': 0,
                                'episode_step': 0, 'phase': 'paused', 'eyes': {'left': True, 'right': True}},
                'identity': {'model_sha256': own['model_sha256'], 'policy': {'provenance': {'policy_identity': identity}}},
                'policy': {'kind': 'male-reduced-v1', 'failure_diagnostics': {}, 'hidden': np.zeros((1, 138), np.float32)},
                'observation': {'cam_left': zeros, 'cam_right': zeros,
                                'sensors': {'collision': False, 'collision_angle': None, 'wind_direction': [1.0, 0.0]}},
                'integration': np.zeros(4, np.float64), 'environment': {'scene': case['scene_seed']},
                'rng': {'environment': 'synthetic', 'environment_seed': case['scene_seed'], 'spaces': 'synthetic'}}
    snapshots.save_snapshot(snapshot, run/'snapshots/initial.snp')
    fingerprint = v1.initial_match(run, world, case, identity)
    geometry = {g['name']: g['geom_id'] for g in own['geometries']}
    wheel = next(g for g in sorted(body.GROUND_SUPPORT) if g in geometry)
    pairs = [((geometry[wheel], geometry['floor']), 2), ((geometry['base_geom'], geometry['obstacle0']), 3),
             ((geometry['floor'], geometry['obstacle1']), 1)]
    admission = v1.numeric_admission([zeros]*2, 138)
    teacher = {'phase': None, 'count': 0, 'direction': 1.0, 'previous_bad_contact': False}
    initial_sha = hexdigest(case['id'], 'teacher', -1)
    manifest = {'controller': 'male-original', 'seed': case['scene_seed'], 'scenario': {'id': 'reproduction'},
                'texture': 'checker', 'profile': nav.PROFILE,
                'navigation_collection': {'contact_profile_sha256': nav.PROFILE_SHA, 'study_sha256': nav.PLAN_SHA,
                                          'source_identity': identity, 'case': case,
                                          'label_kind': 'returned-analytic-teacher-advice', 'label_privileged': True,
                                          'generic_replay_qualified': False, 'contact_ownership': own,
                                          'teacher_initial_sha256': initial_sha, 'initial_fingerprint': fingerprint}}
    writer = records.RunWriter(run/'recording', manifest)
    rows, incidence = [], nav.empty_incidence()
    for tick in range(ticks):
        iso = {k: hexdigest(case['id'], k, tick) for k in v1.ISOLATION}
        sensors = np.asarray([0.0, 0.0, 1.0, 0.0], np.float32)
        hashes = v1.input_hashes({'cam_left': zeros, 'cam_right': zeros, 'sensors': sensors})
        iso['student_input'] = hashes['input']
        action = np.asarray([0.25, 0.1*((tick % 3) - 1)], np.float32)
        control = np.asarray(v1.expected_control(action), np.float64)
        query = {'before': dict(teacher), 'after': dict(teacher), 'contact': {'bad': False, 'angle': None},
                 'expert_action': np.asarray([0.5, -0.05], np.float32).tolist()}
        query['transition'] = recovery.validate_query(query)
        n = 1 + tick % 3
        ids = np.zeros((11, 128, 2), np.int16); classes = np.zeros((11, 128), np.uint8); distances = np.zeros((11, 128))
        for s in range(11):
            for j, (pair, code) in enumerate(pairs[:n]):
                ids[s, j], classes[s, j], distances[s, j] = pair, code, -0.001
        start = tick*.02
        raw = {'cam_left': zeros, 'cam_right': zeros, 'sensors': sensors, 'action': action, 'control': control,
               'body_contact_counts': np.full(11, n, np.int16), 'body_contact_ids': ids, 'body_contact_classes': classes,
               'body_contact_distances': distances, 'body_stage_controls': np.tile(control, (10, 1)),
               'body_contact_times': start + np.r_[np.arange(10)*.002, .018], 'body_end_data_time': np.float64(start + .02),
               'nav_advice_action': np.asarray(query['expert_action'], np.float32),
               'nav_teacher_before': np.asarray([0, 1.0, False], np.float64), 'nav_teacher_after': np.asarray([0, 1.0, False], np.float64),
               'nav_transitions': np.asarray([False]*3, bool), 'nav_query_before': v1.hashes_array(iso),
               'nav_query_after': v1.hashes_array(iso), 'nav_position_xyz_before': np.asarray([0.1*tick, 0.0, 0.05]),
               'nav_position_xyz_after': np.asarray([0.1*tick + 0.01, 0.0, 0.05]),
               'nav_quaternion_before': np.asarray([1.0, 0.0, 0.0, 0.0]), 'nav_quaternion_after': np.asarray([1.0, 0.0, 0.0, 0.0]),
               'nav_wheel_speed': np.asarray([0.0, 0.0])}
        if tamper == 'nonfinite' and tick == ticks - 1: raw['nav_wheel_speed'] = np.asarray([np.nan, 0.0])
        writer.tick(0, tick, **raw)
        row = {'tick': tick, 'query_before': iso, 'query_after': dict(iso), 'advice': query,
               'teacher_before_sha256': hexdigest(case['id'], 'teacher', tick - 1), 'teacher_after_sha256': hexdigest(case['id'], 'teacher', tick),
               'input_hashes': hashes, 'policy_calls': 1, 'teacher_queries': 1, 'executed_action': action.tolist(),
               'before_sample': {'position_xyz': raw['nav_position_xyz_before'].tolist(), 'quaternion': [1.0, 0.0, 0.0, 0.0]},
               'after_sample': {'position_xyz': raw['nav_position_xyz_after'].tolist(), 'quaternion': [1.0, 0.0, 0.0, 0.0]},
               'coverage_passed': True, 'callback_count': 10, 'coverage_errors': []}
        contacts = nav.admit_contacts({**raw, 'episode': 0, 'tick': tick}, own, tick)
        row['contacts'] = nav.row_contacts(contacts)
        nav.add_incidence(incidence, contacts)
        if tamper == 'label' and tick == 0: row['advice'] = {**query, 'expert_action': [0.4, -0.05]}
        rows.append(row)
    writer.finish({})
    writer.close()
    if tamper == 'incidence': incidence['robot_world_pair_instances'][0] += 1
    final = {'phase': 'terminated', 'last_outcome': {'reason': 'stalled'}, 'total_tick': ticks, 'episode': 0}
    result = {'status': 'completed-recording', 'case': case, 'rows': rows, 'engine_closed': True, 'callback_restored': True,
              'numeric_admission': admission, 'contact_ownership': own, 'initial_teacher_sha256': initial_sha,
              'contact_incidence': incidence, 'final_state': final, 'outcome': nav.natural_boundary(ticks, final),
              'initial_world': world, 'initial_fingerprint': fingerprint}
    (stage/'result.json').write_text(json.dumps(result))
    return run, result


def main():
    out = Path(CONFIG['output']); out.mkdir()
    own, cases, identities = ownership(), {}, {}
    for seed in (10, 11, 12):
        identities[str(seed)] = {'controller': 'male-original', 'variant': 'original', 'training_seed': seed}
    for case, ticks in zip(v1.CASES, CONFIG['ticks']):
        tamper = CONFIG.get('tamper') if case['id'] == CONFIG.get('tamper_case') else None
        run, result = owner(out/case['id'], case, ticks, identities[str(case['learner_seed'])], own, tamper)
        cases[case['id']] = {'status': 'completed-recording', 'case': case, 'run': str(run), 'outcome': result['outcome'],
                             'initial_fingerprint': result['initial_fingerprint'], 'contact_incidence': result['contact_incidence'],
                             'supervision': {'status': 'completed', 'returncode': 0}}
    files = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    report = {'status': 'completed-collection', 'profile': nav.PROFILE, 'study_sha256': nav.PLAN_SHA,
              'contact_profile_sha256': nav.PROFILE_SHA, 'qualification_claims': [], 'owners_completed': 12,
              'numeric_ticks': sum(CONFIG['ticks']), 'cases': cases, 'source_pins': {'synthetic': True},
              'final_source_pins': {'synthetic': True}, 'assets_before': {'ok': True}, 'assets_after': {'ok': True},
              'identities_before': identities, 'identities_after': identities, 'artifacts_sha256': files}
    (out/'report.json').write_text(json.dumps(report))


main()
