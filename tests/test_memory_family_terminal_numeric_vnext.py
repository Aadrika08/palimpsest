"""Authored PURE codec checks; no source custody, model or native acceptance.

The fixture below reuses Task3a's authored event construction with the real
software profile descriptor and a portable declared SNP reference. It executes
only pure transitions. No actual source/SNP or runtime payload is opened.
"""
import copy
import hashlib
import importlib
import io
import json
import math
from pathlib import Path
import time
import zipfile

import numpy as np
import pytest

from palimpsest import artifacts, memory, snapshots
from palimpsest import memory_decision as decision, memory_decision_world as world
from palimpsest import memory_experiment, memory_transition_vnext as transition
from palimpsest.profiles import validate_decision
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_numeric_preservation_v2 as numeric
from scripts import memory_family_terminal_audit_vnext as audit
from test_memory_family_oracle_v3 import _acquire, _application, _bind_events, _event, _world_record
from test_memory_family_raw_audit_v4 import _policy_row
from test_memory_family_terminal_audit_vnext import SOURCE, OWNER, CONDITIONS, encoded, descriptor, rebind

ROOT = Path(__file__).parents[1]
PROFILE = ROOT / 'docs/plans/memory-terminal-numeric-pure-vnext-v1-protocol.json'


def api():
    path = ROOT / 'scripts/memory_family_terminal_numeric_vnext.py'
    assert path.is_file(), 'Task4a PURE codec is missing'
    return importlib.import_module('scripts.memory_family_terminal_numeric_vnext')

def fixture(condition='oracle', kind='change', count=2, *, normal=False, selected_failure=False, supervisor_failure=False, delayed_route=False, empty_snapshot=False):
    case = world.make_family_case('development', 0, 4, kind)
    source, boundary, pose, source_events, source_projection = _acquire(case)
    source_events.append(_event('memory_acquired_boundary', boundary, boundary_tick=boundary,
        acquired_evidence=copy.deepcopy(source['supervisor']['acquired_evidence'])))
    _bind_events(source_events, SOURCE)
    source_world = world.initial_state(case)
    source_world['last_tick'] = boundary - 1
    application = _application(case, source, boundary, source_world, SOURCE)
    source_payload = b''.join(encoded(e) for e in source_events)
    application['event_prefix'] = {'sha256': hashlib.sha256(source_payload).hexdigest(),
        'size_bytes': len(source_payload), 'event_count': len(source_events)}
    d = descriptor('docs/plans/memory-terminal-vnext-v1-protocol.json', (ROOT / 'docs/plans/memory-terminal-vnext-v1-protocol.json').read_bytes())
    context = {'schema': transition.CONTEXT_SCHEMA,
        **{k: copy.deepcopy(d) for k in transition._DESCRIPTOR_ROLES},
        'source_application_sha256': memory.sha256(application),
        'source_m_sha256': memory.sha256(source['m']), 'source_world_sha256': memory.sha256(source_world),
        'source_run_id': SOURCE, 'case_id': case['case_id'], 'case_sha256': memory.sha256(case),
        'kind': kind, 'run_id': OWNER, 'condition': condition,
        'condition_resources_sha256': 'a' * 64,
        'source_invariant_sha256': transition.terminal_condition_invariant_vnext(application),
        'schedule': {'boundary_tick': boundary,
            'event_tick': None if kind == 'no-event' else boundary + world.registered_profile(case['profile_sha256'])['arm_schedule']['event_offset'],
            'decision_tick': boundary + world.registered_profile(case['profile_sha256'])['arm_schedule']['decision_offset']}}
    context['source_snapshot'] = descriptor(f'cases/{case["case_id"]}/source/snapshots/initial.snp', b'authored SNP identity only')
    if empty_snapshot:
        context['source_snapshot'] = descriptor('authored/snapshot.snp', b'')
    resource = [] if condition == 'oracle' else {'version': 1, 'episodes': []} if condition == 'retrieval' else None
    config = {'version': 1, 'condition': condition, 'limit': 1, 'resource': resource,
        'resource_sha256': memory.sha256(resource),
        'provenance_sha256': transition.pending_provenance_vnext(context) if condition == 'oracle' else 'b' * 64}
    u = memory.artifact('local_cue') if condition == 'hand-authored' else memory.artifact()
    context['condition_resources_sha256'] = memory.sha256({'selector': config, 'u': u})
    state = transition.configure_terminal_condition_vnext(source, config, u, context=context)
    state = transition.arm_terminal_state_vnext(state, boundary_tick=boundary, context=context)
    post_world = world.arm(source_world, boundary, context['source_invariant_sha256'])
    schedule = {**context['schedule'], 'acquired_state_sha256': context['source_invariant_sha256']}
    events = []
    def emit(kind, tick, **values):
        event = _event(kind, tick, **values)
        event.update(run_id=OWNER, sequence=len(events))
        events.append(event)
        return {'sequence': event['sequence'], 'sha256': memory.sha256(event)}
    # Source and condition poses are authored row evidence, not native placement.
    if count == 0:
        pose = [100., 100., 0.]
        source_projection[-1]['next_pose'] = pose.copy()
    emit('application_restored', boundary, parent_run_id=SOURCE,
        parent_event_prefix=application['event_prefix'], world=_world_record(case, pose),
        revision=application['revision'], eyes=application['eyes'])
    retained = {k: v for k, v in source.items() if k not in ('u', 'selector')}
    emit('memory_selector_configured', boundary, selector=config, u=u, retained_memory_sha256=memory.sha256(retained))
    emit('memory_decision_armed', boundary, schedule=schedule)
    binding = transition.OracleBinding(source['m'], case, source_world) if condition == 'oracle' else None
    job = descriptor('authored/job.json', b'actual full job bytes deliberately unavailable in pure API')
    rows, chain = [], (0, memory.sha256(context))
    refs = {'cue_event': None, 'gate_event': None, 'intervention_event': None}
    results = []
    if selected_failure:
        assert count == 1 and kind != 'no-event'
        target = state['supervisor']['waypoint_ids'][state['supervisor']['waypoint_index']]
        poses = ([float(x), float(y), float(a)] for x in np.arange(-6., 6.1, .5)
            for y in np.arange(-6., 6.1, .5) for a in (0., math.pi / 2, math.pi, -math.pi / 2))
        failing_pose = None
        for candidate in poses:
            packet = decision.capture_symbolic(*world.reconstruct_inputs(case, candidate, boundary + 1,
                event_tick=post_world['event_tick'], gate_result='closed' if kind == 'change' else 'not_requested'),
                episode_id='episode-0', tick=boundary + 1)
            if packet['cues'] and target not in {x['id'] for x in packet['landmarks']} and all(p['passability'] == 'unobserved' for p in packet['passages']):
                failing_pose = candidate
                break
        assert failing_pose is not None, 'authored geometry must expose local selection then missing target'
    for offset in range(count if normal else count + 1):
        tick = boundary + offset
        post_world['last_tick'] = tick
        if tick == post_world['event_tick']:
            post_world.update(applied=True, cue_state=1, gate_result='closed' if kind == 'change' else 'not_requested')
            refs['cue_event'] = emit('memory_world_changed', tick,
                detail={'kind': 'memory_cue_changed', 'tick': tick, 'cue_id': case['cue_id'], 'before': 0, 'after': 1})
            if kind == 'change':
                side = case['subjects_by_side'].index(case['closure_subject_id'])
                edit = {'kind': 'move_obstacle', 'index': len(world.POSTS) + side,
                    'old': {'xy': world.PARKED_GATES[side].copy()}, 'new': {'xy': world.CLOSED_GATES[side].copy()},
                    'simulation_time': float(tick)}
                refs['gate_event'] = emit('memory_world_changed', tick,
                    detail={'kind': 'memory_gate_applied', 'tick': tick, 'subject_id': case['closure_subject_id'], 'intervention': edit})
                refs['intervention_event'] = emit('intervention', tick, change=edit, origin='memory_world_schedule')
        private, sensed_pose, circles = world.audit_inputs(post_world, pose)
        packet = decision.capture_symbolic(private, sensed_pose, circles, episode_id='episode-0', tick=tick)
        sensed = emit('memory_sensed', tick, packet=packet)
        reach = {**copy.deepcopy(refs), 'sensed_event': sensed, 'before_occupancy': None,
            'after_occupancy': None, 'actual_circles': circles}
        result = transition.advance_transition_vnext(state, packet, context=context,
            oracle_binding=binding, reach=reach, job_sha256=job['sha256'], chain=chain)
        results.append(result)
        if result.witness is not None:
            emit('memory_transition_witness_vnext', tick, witness=result.witness)
            chain = (chain[0] + 1, memory.sha256(result.witness))
        if result.status == 'raised':
            error = result.witness['exception']
            outcome = {'reason': 'runtime_failure', 'episode': 0, 'steps': tick, **error, 'policy_diagnostics': {}}
            emit('runtime_failure', tick, error=outcome)
            break
        assert result.status in ('ordinary-return', 'witnessed-return'), result.status
        state = result.proposed_state
        if result.witness is not None:
            emit('memory_transition_commit_vnext', tick, commit={'schema': transition.COMMIT_SCHEMA,
                'context_sha256': memory.sha256(context), 'witness_sha256': memory.sha256(result.witness),
                'tick': tick, 'memory_sha256': memory.sha256(state), 'lifecycle': state['terminal_lifecycle']})
        for detail in result.decisions:
            emit('memory_decision', tick, detail=detail, route_anchor={'stage': 'pre-control', 'xy': pose[:2]})
        emit('memory_inspected', tick, memory=transition.inspect_terminal_state_vnext(state, context=context))
        if state['supervisor']['phase'] == 'failure':
            assert supervisor_failure and offset == count
            outcome = {'reason': 'runtime_failure', 'episode': 0, 'steps': tick, 'type': 'ValueError',
                'message': 'Memory-v2 supervisor failure: ' + state['supervisor']['failure_reason'], 'policy_diagnostics': {}}
            emit('runtime_failure', tick, error=outcome)
            break
        emit('memory_cue', tick, bearing=result.bearing, raw_upstream_bearing=[1., 0.])
        next_pose = pose.copy()
        if delayed_route and state['supervisor']['waypoint_deadline_tick'] - tick == 2:
            sup = state['supervisor']
            target = sup['waypoint_ids'][sup['waypoint_index']]
            xy = case['landmarks'][target]
            next_target = sup['waypoint_ids'][min(sup['waypoint_index'] + 1, len(sup['waypoint_ids']) - 1)]
            after = case['landmarks'][next_target]
            next_pose = [*xy, math.atan2(after[1] - xy[1], after[0] - xy[0]) / 2.]
        if not normal and not supervisor_failure and offset == count - 1:
            next_pose = failing_pose.copy() if selected_failure else [100., 100., 0.]
        row = {'episode': 0, 'tick': tick, 'pose': pose.copy(), 'next_pose': next_pose.copy()}
        policy, arrays = _policy_row(row, OWNER)
        policy['sensors']['wind_direction'] = result.bearing.copy()
        arrays['sensors'] = np.asarray([0., 0., *result.bearing], np.float32)
        from palimpsest import snapshots
        policy['observation_sha256'] = snapshots.state_digest({'cam_left': arrays['cam_left'], 'cam_right': arrays['cam_right'], 'sensors': policy['sensors']})
        emit('neural_policy_call', tick, **{k: v for k, v in policy.items() if k not in ('run_id', 'episode', 'episode_step', 'tick')})
        rows.append({'episode': 0, 'tick': tick, **arrays})
        pose = next_pose
    if normal:
        outcome = {'reason': 'time_limit' if count == 900 else 'stalled', 'episode': 0, 'steps': boundary + count, 'final_distance': 10.}
        final_phase, status = ('truncated' if count == 900 else 'terminated'), 'completed'
    else:
        assert results[-1].status == ('witnessed-return' if supervisor_failure else 'raised'), 'authored natural terminal must actually terminate'
        final_phase, status = 'failed', 'failed'
    metrics = {'reward': 0., 'contact_ticks': 0, 'path_length': sum((float(np.linalg.norm(r['next_pose'][:2] - r['pose'][:2])) for r in rows), 0.)}
    if normal:
        emit('episode_finished', boundary + count, outcome=outcome, metrics=metrics)
    for i in range((count + 31) // 32):
        events.append({'sequence': len(events), 'kind': 'chunk', 'path': f'chunks/{i:06d}.npz',
            'sha256': 'c' * 64, 'episode': 0, 'start': boundary + i * 32, 'count': min(32, count-i*32),
            'arrays': {name: {'dtype': value.dtype.str, 'shape': list(value.shape)}
                for name, value in rows[0].items() if name not in ('episode', 'tick')}})
    descriptors = {'context': descriptor('authored/context.json', memory.canonical_bytes(context)),
        'job': job, **{k: descriptor('authored/' + k + '.json', b'placeholder') for k in ('raw_manifest', 'raw_events', 'worker_report')}}
    manifest = {'run_id': OWNER, 'controller': 'flynn', 'requested_device': 'cpu', 'teacher_privileged': False,
        'texture': 'checker', 'seed': case['seed'], 'memory_case': case, 'memory_case_sha256': memory.sha256(case),
        'acquisition_protocol_sha256': case['acquisition_protocol_sha256'], 'parent_run_id': SOURCE,
        'parent_event_prefix': application['event_prefix'], 'status': status, 'recording_format': 'palimpsest-npz-v1',
        'recording_max_bytes': 384 * 1024**2, 'recorded_ticks': count, 'final_phase': final_phase,
        'last_outcome': outcome, 'total_tick': boundary + count, 'world_state': post_world,
        'scenario': validate_decision(world.SCENARIO, 'checker', 'flynn', profile_sha256=case['profile_sha256']),
        'recorded_chunks': (count + 31) // 32, 'recorded_events': len(events),
        'metrics': metrics, 'close_reason': 'operator_closed', 'memory_terminal_vnext_context': descriptors['context'],
        'memory_terminal_vnext_context_sha256': memory.sha256(context), 'memory_terminal_vnext_mode': 'memory-terminal-vnext-v1'}
    report = {'schema': 'memory-family-owner-report-v3', 'run_id': OWNER, 'case_id': case['case_id'],
        'operation': 'condition', 'condition': condition, 'status': 'recorded', 'acquired': True,
        'snapshot_sha256': context['source_snapshot']['sha256'], 'source_snapshot_sha256': context['source_snapshot']['sha256'],
        'total_ticks': boundary + count, 'final_phase': final_phase, 'world_state': post_world}
    source_rows = [{'episode': r['episode'], 'tick': r['tick'], **_policy_row(r, SOURCE)[1]} for r in source_projection]
    return rebind({'raw': {'manifest': manifest, 'events': events, 'rows': rows,
        'worker_report': report, 'job': job, 'descriptors': descriptors}, 'context': context,
        'source_application': application, 'source_events': source_events, 'source_rows': source_rows,
        'results': results})


def sample(count=2, condition='own', kind='change'):
    built = fixture(condition, kind, count)
    # Exercise signed zeros and all three populations, before genuine proof.
    for index, row in enumerate(built['raw']['rows']):
        row['latency'] = np.array(-0.0 if index % 2 else .125, '<f8')
        row['step_latency'] = np.array(-0.0, '<f8')
        row['population_stats'] = np.array([[0., -0., 0., -0.], [2., .25, -.5, 1.], [3., .5, -.75, 2.]], '<f8')
    for event in built['raw']['events']:
        if event['kind'] == 'chunk':
            event['arrays'] = {name: {'dtype': value.dtype.str, 'shape': list(value.shape)} for name, value in built['raw']['rows'][0].items() if name not in ('episode', 'tick')}
    rebind(built)
    proof = audit.prove_terminal_vnext(built['raw'], context=built['context'],
        source_application=built['source_application'], source_events=built['source_events'],
        source_rows=built['source_rows'], deadline=time.monotonic() + 60.)
    c = built['context']
    raw = {'terminal_raw': built['raw'], 'recorded_manifest_bytes': encoded(built['raw']['manifest']),
        'recorded_events_bytes': b''.join(encoded(e) for e in built['raw']['events']),
        'snapshot_reference': {'kind': 'shared-source', 'source_run_id': SOURCE,
            'source_receipt_sha256': 'a' * 64, **c['source_snapshot']}}
    floor = len(memory.canonical_bytes(proof)) + len(memory.canonical_bytes(c)) + sum(proof[k]['size_bytes'] for k in ('raw_manifest', 'worker_report', 'job'))
    return raw, proof, c, floor


def convert(parts):
    raw, proof, context, floor = parts
    return api().convert_terminal_numeric_vnext(raw, receipt=proof, context=context, external_overhead_bytes=floor)


def read(bundle, parts, extra=0):
    return api().read_terminal_numeric_vnext(bundle, receipt=parts[1], external_overhead_bytes=parts[3] + extra)


def json_member(bundle, path, mutate):
    result = dict(bundle)
    value = artifacts._json(result[path]); mutate(value)
    result[path] = memory.canonical_bytes(value)
    return result


def replace_partition(bundle, kind, mutate):
    result = dict(bundle)
    path = f'{kind}/000000.npz'
    with np.load(io.BytesIO(result[path]), allow_pickle=False) as archive:
        values = {name: archive[name].copy() for name in archive.files}
    mutate(values)
    result[path] = compact._npz(values)
    if kind == 'numeric':
        index = artifacts._json(result['numeric-index.json'])
        index['chunks'][0]['companion'] = descriptor(path, result[path])
        result['numeric-index.json'] = memory.canonical_bytes(index)
    else:
        index = artifacts._json(result['base/chunk-index.json'])
        index['chunks'][0]['sha256'] = hashlib.sha256(result[path]).hexdigest()
        result['base/chunk-index.json'] = memory.canonical_bytes(index)
        ni = artifacts._json(result['numeric-index.json'])
        ni['chunks'][0]['base_chunk'] = copy.deepcopy(index['chunks'][0])
        result['numeric-index.json'] = memory.canonical_bytes(ni)
    bm = artifacts._json(result['base/manifest.json'])
    bm['chunk_index'] = descriptor('chunk-index.json', result['base/chunk-index.json'])
    result['base/manifest.json'] = memory.canonical_bytes(bm)
    nm = artifacts._json(result['numeric-pure-vnext.json'])
    nm['base_manifest'] = descriptor('base/manifest.json', result['base/manifest.json'])
    nm['base_files'] = [descriptor(p, result[p]) for p in sorted(result) if p.startswith('base/')]
    nm['numeric_index'] = descriptor('numeric-index.json', result['numeric-index.json'])
    result['numeric-pure-vnext.json'] = memory.canonical_bytes(nm)
    return result


def test_zero_numeric_has_no_partition_and_typed_empty_frames():
    api(); parts = sample(0); bundle = convert(parts); result = read(bundle, parts)
    assert len(bundle) == 9 and not result['rows']
    assert artifacts._json(bundle['base/chunk-index.json'])['chunks'] == []
    assert artifacts._json(bundle['numeric-index.json'])['chunks'] == []
    assert result['manifest']['first_tick'] is result['manifest']['last_tick'] is None
    with np.load(io.BytesIO(bundle['base/audit-frames.npz']), allow_pickle=False) as frames:
        for name, shape, dtype in [('tick', (0,), '<i8'), ('raw_cam_left', (0,128,128,3), '|u1'), ('raw_cam_right', (0,128,128,3), '|u1')]:
            assert frames[name].shape == shape and frames[name].dtype.str == dtype
    assert result['trace_digest'] == hashlib.sha256().hexdigest()
    assert result['preservation']['raw_comparison_performed'] is False
    assert result['preservation']['actual_acceptance'] is False


@pytest.mark.parametrize('count', [1, 2, 31, 32, 33])
def test_fitting_one_two_31_32_33_rows_preserve_all_bytes(count, tmp_path):
    api(); parts = sample(count); bundle = convert(parts)
    compared = api().prove_terminal_numeric_vnext(parts[0], bundle, parts[1], external_overhead_bytes=parts[3])
    assert len(bundle) == 9 + 2 * ((count + 31) // 32)
    assert compared['preservation']['raw_comparison_performed'] is True
    assert compared['preservation']['actual_acceptance'] is False
    assert compared['legacy_manifest_bytes'] == parts[0]['recorded_manifest_bytes']
    assert compared['legacy_events_bytes'] == parts[0]['recorded_events_bytes']
    (tmp_path/f'pure-{count}-ledger.json').write_bytes(memory.canonical_bytes({
        'rows':count,'chunks':(count+31)//32,'members':len(bundle),
        'raw_events_bytes':len(parts[0]['recorded_events_bytes']),
        'ledger':compared['byte_ledger'],
        'arrays':{name:{'dtype':compared['rows'][0][name].dtype.str,'shape':list(compared['rows'][0][name].shape)} for name in (*compact.RETAINED,*numeric.NUMERIC_FIELDS)},
        'files':[descriptor(path,bundle[path]) for path in sorted(bundle)]}))
    for raw, restored in zip(parts[0]['terminal_raw']['rows'], compared['rows']):
        for name in (*compact.RETAINED, *numeric.NUMERIC_FIELDS):
            assert (raw[name].dtype.str, raw[name].shape, raw[name].tobytes()) == (restored[name].dtype.str, restored[name].shape, restored[name].tobytes())


@pytest.mark.parametrize('condition', CONDITIONS)
def test_all_nine_zero_conditions_use_genuine_conditional_proof(condition):
    api(); parts = sample(0, condition); assert read(convert(parts), parts)['rows'] == []


def test_900_numeric_primitive_is_not_proof_admission(tmp_path):
    codec = api()
    from test_memory_family_compact_v4 import _row
    count = 0
    sizes=[]
    # No TerminalProof exists in this test. This is partition-wire coverage only.
    for start in range(0, 900, 32):
        rows = []
        for tick in range(start, min(start + 32, 900)):
            row = _row(tick % 240); row['tick'] = tick
            row['population_stats'] = np.zeros((3, 4), '<f8'); rows.append(row)
        base_bytes, numeric_bytes = codec._encode_partition(rows)
        base = compact._read_npz(base_bytes, {n:(d,s) for n,d,s,_ in compact.ROW_FIELDS}, len(rows), 'authored partition')
        extra = numeric._read_numeric_npz(numeric_bytes, len(rows))
        projected=compact._project_rows(rows,'condition')
        for i, row in enumerate(rows):
            for name in base:
                left,right=projected[i][name],base[name][i]
                assert (left.dtype.str,left.shape,left.tobytes())==(right.dtype.str,right.shape,right.tobytes())
            for name in numeric.NUMERIC_FIELDS:
                left,right=row[name],extra[name][i]
                assert (left.dtype.str,left.shape,left.tobytes())==(right.dtype.str,right.shape,right.tobytes())
        sizes.append({'rows':len(rows),'base_bytes':len(base_bytes),'companion_bytes':len(numeric_bytes)})
        count += len(rows)
    assert count == 900
    (tmp_path/'numeric-primitive-900.json').write_bytes(memory.canonical_bytes({'rows':count,'partitions':sizes,'proof_admission':False}))


def test_signed_zero_latency_population_and_commitments_are_exact():
    api(); parts = sample(2); bundle = convert(parts); result = read(bundle, parts)
    assert np.signbit(result['rows'][1]['latency']) and np.signbit(result['rows'][0]['population_stats'][0,1])
    assert result['trace_digest'] == parts[1]['trace_digest']
    changed = replace_partition(bundle, 'numeric', lambda v: v['step_latency'].__setitem__(0, 0.))
    # The stored reader lacks raw timing authentication. It says so explicitly.
    assert read(changed, parts)['preservation']['raw_comparison_performed'] is False
    with pytest.raises(ValueError):
        api().prove_terminal_numeric_vnext(parts[0], changed, parts[1], external_overhead_bytes=parts[3])


def test_old_reader_refuses_successor_and_new_reader_refuses_old_or_malformed_full():
    api(); parts = sample(1); bundle = convert(parts)
    with pytest.raises(ValueError): compact.read_compact(numeric.extract_base_bundle(bundle), raw_audit_receipt=parts[1])
    with pytest.raises(ValueError): numeric.read_numeric_compact(bundle, raw_audit_receipt=parts[1])
    old_bundle = dict(bundle)
    old_bundle['numeric-v2.json'] = old_bundle.pop('numeric-pure-vnext.json')
    with pytest.raises(ValueError): read(old_bundle, parts)
    changed = json_member(bundle, 'base/manifest.json', lambda v: v.update(schema='memory-family-compact-manifest-vnext-v1'))
    with pytest.raises(ValueError): read(changed, parts)


@pytest.mark.parametrize('defect', ['extra', 'missing', 'duplicate-json', 'duplicate-zip', 'trailing-zip', 'nonnull-audit', 'nonnull-source', 'count-bool', 'context', 'proof', 'array-shape', 'camera', 'digest', 'schedule-boundary'])
def test_extra_duplicate_missing_member_or_census_refuses(defect):
    api(); parts = sample(2); bundle = convert(parts); changed = dict(bundle)
    if defect == 'extra': changed['extra.json'] = b'{}'
    elif defect == 'missing': del changed['numeric/000000.npz']
    elif defect == 'duplicate-json': changed['numeric-index.json'] = b'{"schema":"x","schema":"x","chunks":[]}'
    elif defect == 'duplicate-zip':
        stream = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(bundle['numeric/000000.npz'])) as old, zipfile.ZipFile(stream, 'w') as z:
            for info in old.infolist(): z.writestr(info.filename, old.read(info))
            with pytest.warns(UserWarning, match='Duplicate name'):
                z.writestr('latency.npy', old.read('latency.npy'))
        changed['numeric/000000.npz'] = stream.getvalue()
    elif defect == 'trailing-zip': changed['base/chunks/000000.npz'] += b'x'
    elif defect in ('nonnull-audit', 'nonnull-source'):
        key = 'raw_audit' if defect == 'nonnull-audit' else 'source_identity'
        changed = json_member(bundle, 'numeric-pure-vnext.json', lambda v: v.update({key: parts[1]['job']}))
    elif defect == 'count-bool': changed = json_member(bundle, 'numeric-pure-vnext.json', lambda v: v.update(row_count=True))
    elif defect == 'context': changed = json_member(bundle, 'context.json', lambda v: v.update(condition='sham'))
    elif defect == 'proof': changed = json_member(bundle, 'terminal-proof.json', lambda v: v.update(path_length=0.))
    elif defect == 'array-shape': changed = replace_partition(bundle, 'numeric', lambda v: v.update(population_stats=v['population_stats'][:,:2]))
    elif defect == 'camera': changed = replace_partition(bundle, 'base/chunks', lambda v: v['cam_left_sha256'].__setitem__((0,0), 0))
    elif defect == 'digest': changed = replace_partition(bundle, 'base/chunks', lambda v: v['row_digest'].__setitem__((0,0), 0))
    elif defect == 'schedule-boundary': changed = json_member(bundle, 'base/manifest.json', lambda v: v['audit_schedule'].update(boundary_tick=1))
    with pytest.raises(ValueError): read(changed, parts)


@pytest.mark.parametrize('key', ['row_count', 'chunk_count', 'boundary_tick', 'world_applied', 'goal', 'path_length', 'terminal_sensor_tick', 'capped_ticks', 'schema', 'witnesses', 'commits'])
def test_receipt_schema_types_and_binding_refuse(key):
    api(); parts = sample(1); bundle = convert(parts); proof = copy.deepcopy(parts[1])
    proof[key] = {'row_count': True, 'chunk_count': False, 'boundary_tick': 0, 'world_applied': 1, 'goal': 0, 'path_length': float('inf'), 'terminal_sensor_tick': None, 'capped_ticks': 1, 'schema':'old', 'witnesses': [], 'commits': [{'sequence': 0, 'sha256':'a'*64}]}[key]
    with pytest.raises(ValueError): api().read_terminal_numeric_vnext(bundle, receipt=proof, external_overhead_bytes=parts[3])


@pytest.mark.parametrize('defect', ['manifest-bytes', 'event-bytes', 'job', 'report', 'descriptors', 'snapshot', 'opaque', 'subclass', 'list-array', 'population-shape'])
def test_raw_input_bindings_refuse_without_coercion(defect):
    api(); parts = sample(1); raw = copy.deepcopy(parts[0])
    class Opaque:
        def __array__(self, *a, **kw): pytest.fail('opaque array loader executed')
    class Subclass(np.ndarray): pass
    if defect == 'manifest-bytes': raw['recorded_manifest_bytes'] += b' '
    elif defect == 'event-bytes': raw['recorded_events_bytes'] = raw['recorded_events_bytes'].replace(b' ', b'', 1)
    elif defect == 'job': raw['terminal_raw']['job']['sha256'] = 'b'*64
    elif defect == 'report': raw['terminal_raw']['worker_report']['total_ticks'] += 1
    elif defect == 'descriptors': raw['terminal_raw']['descriptors']['raw_manifest']['path'] = 'other.json'
    elif defect == 'snapshot': raw['snapshot_reference']['source_receipt_sha256'] = None
    elif defect == 'opaque': raw['terminal_raw']['rows'][0]['pose'] = Opaque()
    elif defect == 'subclass': raw['terminal_raw']['rows'][0]['pose'] = raw['terminal_raw']['rows'][0]['pose'].view(Subclass)
    elif defect == 'list-array': raw['terminal_raw']['rows'][0]['pose'] = [0.,0.,0.]
    elif defect == 'population-shape': raw['terminal_raw']['rows'][0]['population_stats'] = np.zeros((1,4), '<f8')
    with pytest.raises(ValueError): api().convert_terminal_numeric_vnext(raw, receipt=parts[1], context=parts[2], external_overhead_bytes=parts[3])


def test_combined_metadata_and_event_caps_include_every_copy(tmp_path):
    api(); parts = sample(2); bundle = convert(parts); result = read(bundle, parts)
    ledger = result['byte_ledger']; assert ledger['external_overhead_bytes'] == parts[3]
    assert ledger['recording_bytes'] == sum(map(len,bundle.values())) + parts[3]
    slack = 1024**2 - ledger['overhead_bytes']
    assert read(bundle, parts, slack)['byte_ledger']['overhead_bytes'] == 1024**2
    with pytest.raises(ValueError): read(bundle, parts, slack + 1)
    with pytest.raises(ValueError): api().read_terminal_numeric_vnext(bundle, receipt=parts[1], external_overhead_bytes=parts[3]-1)
    (tmp_path/'byte-ledger.json').write_bytes(memory.canonical_bytes(ledger))
    too_big = dict(bundle); too_big['base/legacy-events.jsonl'] = b'x' * (5*1024**2+1)
    with pytest.raises(ValueError): read(too_big, parts)


def test_900_normal_remains_genuine_proof_resource_refusal(tmp_path):
    api(); built = fixture('no-U', 'no-event', 900, normal=True, delayed_route=True)
    assert built['raw']['descriptors']['raw_events']['size_bytes'] > 5*1024**2
    (tmp_path/'normal900-resource-descriptor.json').write_bytes(memory.canonical_bytes(built['raw']['descriptors']['raw_events']))
    with pytest.raises(ValueError, match='descriptor byte size'):
        audit.prove_terminal_vnext(built['raw'], context=built['context'], source_application=built['source_application'], source_events=built['source_events'], source_rows=built['source_rows'], deadline=time.monotonic()+60.)


def test_profile_records_pure_scope_and_exact_inherited_layout():
    codec = api(); assert PROFILE.is_file(), 'PURE numeric profile is missing'
    profile = artifacts._json(PROFILE.read_bytes())
    assert profile['schema'] == 'memory-terminal-numeric-pure-protocol-vnext-v1'
    assert codec.PROTOCOL_BYTES == memory.canonical_bytes(profile)
    assert profile['terminal_profile']['sha256'] == hashlib.sha256((ROOT/'docs/plans/memory-terminal-vnext-v1-protocol.json').read_bytes()).hexdigest()
    assert len(profile['row']['base_fields']) == 16 and len(profile['row']['numeric_fields']) == 3
    assert profile['claims']['actual_acceptance'] is False


def _rebind_recorded_events(bundle, proof, change):
    result = dict(bundle); proof = copy.deepcopy(proof)
    events = [artifacts._json(line) for line in result['base/legacy-events.jsonl'].splitlines()]
    change(events)
    result['base/legacy-events.jsonl'] = b''.join(encoded(e) for e in events)
    proof['raw_events'] = descriptor(proof['raw_events']['path'], result['base/legacy-events.jsonl'])
    proof['witnesses'] = [audit._reference(e) for e in events if e['kind']=='memory_transition_witness_vnext']
    proof['commits'] = [audit._reference(e) for e in events if e['kind']=='memory_transition_commit_vnext']
    result['terminal-proof.json'] = memory.canonical_bytes(proof)
    bm = artifacts._json(result['base/manifest.json'])
    bm['legacy_events'] = descriptor('legacy-events.jsonl', result['base/legacy-events.jsonl'])
    bm['terminal_proof'] = descriptor('terminal-proof.json', result['terminal-proof.json'])
    result['base/manifest.json'] = memory.canonical_bytes(bm)
    nm = artifacts._json(result['numeric-pure-vnext.json'])
    nm['terminal_proof'] = bm['terminal_proof']
    nm['base_manifest'] = descriptor('base/manifest.json', result['base/manifest.json'])
    nm['base_files'] = [descriptor(path,result[path]) for path in sorted(result) if path.startswith('base/')]
    result['numeric-pure-vnext.json'] = memory.canonical_bytes(nm)
    return result,proof


def test_read_recomputes_available_path_length_without_claiming_raw_authentication():
    api(); parts = sample(2); bundle = convert(parts)
    changed = replace_partition(bundle, 'base/chunks', lambda v: v['next_pose'].__setitem__((0,0), v['next_pose'][0,0]+1.))
    with pytest.raises(ValueError): read(changed, parts)


@pytest.mark.parametrize('defect', ['packet-hash','sensed-role'])
def test_read_checks_bound_witness_packet_and_reference_roles(defect):
    api(); parts = sample(1); bundle = convert(parts)
    def change(events):
        witness = next(e['witness'] for e in events if e['kind']=='memory_transition_witness_vnext')
        if defect == 'packet-hash': witness['packet_sha256'] = '0'*64
        else: witness['reach']['sensed_event'] = audit._reference(events[0])
    changed,proof = _rebind_recorded_events(bundle,parts[1],change)
    with pytest.raises(ValueError): api().read_terminal_numeric_vnext(changed,receipt=proof,external_overhead_bytes=parts[3]+1024)


@pytest.mark.parametrize('over',[0,1])
def test_inherited_event_line_cap_refuses_even_a_genuine_conditional_proof(over):
    api(); built = fixture('own','change',1)
    # Task3a permits bounded extensible metadata; the inherited compact reader
    # has the stricter 1MiB per-event-line cap, which Task4a must preserve.
    built['raw']['rows'][0]['population_stats'] = np.zeros((3,4),'<f8')
    for event in built['raw']['events']:
        if event['kind']=='chunk': event['arrays']['population_stats']={'dtype':'<f8','shape':[3,4]}
    first=built['raw']['events'][0]
    first['authored_padding']=''
    first['authored_padding']='x'*(1024**2-len(encoded(first).rstrip(b'\n'))+over)
    assert len(encoded(first).rstrip(b'\n'))==1024**2+over
    rebind(built)
    proof = audit.prove_terminal_vnext(built['raw'],context=built['context'],
        source_application=built['source_application'],source_events=built['source_events'],
        source_rows=built['source_rows'],deadline=time.monotonic()+60.)
    c=built['context']
    raw={'terminal_raw':built['raw'],'recorded_manifest_bytes':encoded(built['raw']['manifest']),
        'recorded_events_bytes':b''.join(encoded(e) for e in built['raw']['events']),
        'snapshot_reference':{'kind':'shared-source','source_run_id':SOURCE,
            'source_receipt_sha256':'a'*64,**c['source_snapshot']}}
    floor=len(memory.canonical_bytes(proof))+len(memory.canonical_bytes(c))+sum(proof[k]['size_bytes'] for k in ('raw_manifest','worker_report','job'))
    if over:
        with pytest.raises(ValueError): api().convert_terminal_numeric_vnext(raw,receipt=proof,context=c,external_overhead_bytes=floor)
    else:
        api().convert_terminal_numeric_vnext(raw,receipt=proof,context=c,external_overhead_bytes=floor)


def test_sixteen_selected_pairs_refuse_unchanged_frame_file_cap():
    codec=api()
    frames={'tick':np.arange(16,dtype='<i8'), 'raw_cam_left':np.zeros((16,128,128,3),'|u1'),
        'raw_cam_right':np.zeros((16,128,128,3),'|u1')}
    payload=compact._npz(frames)
    assert 16*98304==1572864 and len(payload)>1572864
    with pytest.raises(ValueError): codec._read_arrays(payload,compact.FRAME_FIELDS,16,1572864,'authored frame boundary')


def test_rewritten_retained_values_are_not_authenticated_by_opaque_row_digests():
    api(); parts=sample(2); bundle=convert(parts)
    changed=replace_partition(bundle,'base/chunks',lambda v:v['encoded_input'].__setitem__((0,0),123.))
    # Internal digests cannot authenticate a rewritten stored field. Future4b
    # must bind bundle identity/origin; current read explicitly makes no claim.
    result=read(changed,parts)
    assert result['preservation']['raw_comparison_performed'] is False
    assert result['preservation']['actual_acceptance'] is False
    with pytest.raises(ValueError): api().prove_terminal_numeric_vnext(parts[0],changed,parts[1],external_overhead_bytes=parts[3])


@pytest.mark.parametrize('external',[True,-1,0,1.0])
def test_external_metadata_type_and_mandatory_floor_are_not_optional(external):
    api(); parts=sample(0); bundle=convert(parts)
    with pytest.raises(ValueError): api().read_terminal_numeric_vnext(bundle,receipt=parts[1],external_overhead_bytes=external)
