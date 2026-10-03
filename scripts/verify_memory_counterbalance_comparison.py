"""Two fixed four-cell DEVELOPMENT profiles; no execution without a GO."""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

import numpy as np
from palimpsest import artifacts, memory, memory_experiment as experiment, memory_task, memory_world
from palimpsest.evaluate import bounded_process
from palimpsest.replay import _initial_snapshot, _register_initial
from palimpsest.snapshots import capture, invariant_hashes, read_snapshot, state_digest
from palimpsest.storage import GiB, MiB, StorageBudget, StorageLimits

HELPER = Path(__file__).with_name('verify_memory_counterbalance.py')
spec = importlib.util.spec_from_file_location('counterbalance_admission_helpers', HELPER)
admission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admission)
neural, common = admission.neural, admission.common
CELLS = ((24, 'local_cue', 'change'), (29, 'paired_cue', 'change'),
         (30, 'local_cue', 'null'), (27, 'paired_cue', 'no-event'))
B_PLAN_SHA256 = 'ecaedc5c9341063eaa619635da69bda2149dd66e46ed1d01a7ffe13834515131'
B_REPORT_SHA256 = '2eaba8d84f4d206c0f415362088ba7cec3139b77e10829b6cdc84b055624ea1f'
# Historical protocol pin; current executor helper bytes remain in source_identity.
LEGACY_ADMISSION_HELPER_SHA256 = 'ffb7fa9d3b84441c6fa05945b893d4c4028481502d80355f8e951e5238d30927'


def pinned_json(path, digest, maximum=MiB):
    path = artifacts._safe_path(path)
    if common._hash(path) != digest:
        raise ValueError('Retained admission input hash differs')
    result = artifacts._json(artifacts._read(path, maximum))
    if common._hash(path) != digest:
        raise ValueError('Retained admission input changed while reading')
    return result


def derive_anchor(plan, terminal, cell, *, protocol_sha256=None):
    """Join the declared owner to its completed report; never choose by UUID alone."""
    key = admission.cell_key(cell)
    cells, protocol = fixed_profile(protocol_sha256)
    if remaining_profile(protocol_sha256) and plan['protocol_sha256']!=protocol['admission_protocol_sha256']:
        raise ValueError('Admission plan belongs to another fixed chunk')
    if tuple(cell) not in cells or terminal.get('status') != 'admission_checked' or not all(
            terminal.get(k) is True for k in ('source_unchanged', 'retained_unchanged')):
        raise ValueError('Unsupported cell or incomplete immutable admission')
    if (terminal.get('protocol_sha256') != plan['protocol_sha256']
            or terminal.get('source_identity') != plan['source_identity']
            or terminal.get('final_source_identity') != plan['source_identity']
            or terminal.get('unattempted_stages')):
        raise ValueError('Admission protocol/source/terminal identity differs')
    lineage = {}
    for stage in admission.STAGES:
        jobs = [j for j in plan['jobs'] if j['cell'] == list(cell) and j['stage'] == stage]
        rows = [r for r in terminal['runs'] if r['cell'] == key and r['stage'] == stage]
        if len(jobs) != 1 or len(rows) != 1:
            raise ValueError('Admission cell/stage join is not unique')
        job, row = jobs[0], rows[0]
        if (row['run_id'] != job['run_id'] or row['run_path'] != job['output']
                or row.get('admission_pass') is not True or row.get('final_phase') != 'paused'
                or row.get('supervisor', {}).get('status') != 'completed'
                or row['supervisor'].get('returncode') != 0):
            raise ValueError('Admission owner was substituted or did not pass')
        lineage[stage] = (copy.deepcopy(job), copy.deepcopy(row))
    if len({j['run_id'] for j, _ in lineage.values()}) != 3:
        raise ValueError('Admission source/anchor/probe identities overlap')
    return lineage


def policy_boundary(data, native, case):
    """Application is at 300; the last committed sensor cursor/detector is 299."""
    app = native['application']
    state = memory_task.validate_state(app['memory'])
    if (data['rows'] or data['manifest'].get('controller') != 'flynn'
            or data['manifest'].get('requested_device') != 'cpu'
            or app['controller'] != 'flynn' or app['execution_mode'] != 'live'
            or app['phase'] != 'paused' or (app['episode'], app['episode_step'], app['total_tick']) != (0, 300, 300)
            or state['version'] != 1 or state['cursor']['tick'] != 299 or state['detector']['tick'] != 299
            or native['policy'] is None or app['controller_tensors'] is None
            or native['identity']['policy']['device'] != 'cpu'
            or app['world_task_state']['case'] != case or app['world_task_state']['applied']
            or state['u'] != memory.artifact(method='empty-v1') or state['e']['episodes']
            or state['requests'] or state['active'] is not None
            or any(e['kind'] in ('selector_configured', 'neural_policy_call') for e in data['events'])):
        raise ValueError('Admission ancestor is not the zero-row pre-event CPU policy anchor')
    return state


def load_bindings(plan_path, report_path, *, protocol_sha256=None, admission_lineage=None):
    """Validate all three original owners per cell, retaining their actual provenance."""
    plan_sha,report_sha=admission_pins(protocol_sha256,admission_lineage)
    if admission_lineage is not None and (str(plan_path)!=admission_lineage['plan_path'] or str(report_path)!=admission_lineage['report_path']):
        raise ValueError('Admission paths differ from frozen lineage')
    plan = admission.validate_plan(pinned_json(plan_path, plan_sha))
    terminal = pinned_json(report_path, report_sha)
    result = {}
    cells, _ = fixed_profile(protocol_sha256)
    for cell in cells:
        lineage = derive_anchor(plan, terminal, cell, protocol_sha256=protocol_sha256)
        checked = {}
        pins = []
        for stage, (prepared, summary) in lineage.items():
            path = Path(plan['output']) / f"{prepared['run_id']}-job.json"
            job = artifacts._json(artifacts._read(path, 128 * 1024))
            admission.validate_job(job)
            dynamic = ('snapshot_path', 'snapshot_sha256', 'expected_non_u', 'replacement_preserved')
            if any(memory.canonical_bytes(job[k]) != memory.canonical_bytes(prepared[k])
                   for k in prepared if k not in dynamic):
                raise ValueError('Loaded runtime job differs from its frozen admission plan')
            if stage == 'source':
                expected = dict.fromkeys(dynamic)
            else:
                ancestor = checked['source' if stage == 'policy-anchor' else 'policy-anchor']
                expected = {'snapshot_path': ancestor[1]['snapshot_path'],
                    'snapshot_sha256': ancestor[1]['snapshot_sha256'],
                    'expected_non_u': ancestor[1]['non_u'] if stage == 'probe' else None,
                    'replacement_preserved': neural.replacement_preserved(ancestor[2]) if stage == 'policy-anchor' else None}
            if any(memory.canonical_bytes(job[k]) != memory.canonical_bytes(v) for k, v in expected.items()):
                raise ValueError('Loaded runtime restoration does not join its declared predecessor')
            data, report, native, entry = admission.validate_stage(job, summary['supervisor'])
            files = [{'path': str(p.relative_to(data['run'])), 'bytes': p.stat().st_size,
                      'sha256': common._hash(p)} for p in data['paths']]
            worker = data['run'] / 'admission-worker.json'
            if (files != summary['files'] or common._hash(worker) != summary['worker_report_sha256']
                    or entry['sha256'] != summary['snapshot_sha256']
                    or common.baseline_invariants(native) != summary['initial_non_u']):
                raise ValueError('Retained admission artifacts differ from the terminal report')
            pins.extend({'path': str(p), 'sha256': common._hash(p)} for p in
                [*data['paths'], path, worker, data['run'] / 'snapshots/initial.snp',
                 data['run'] / 'snapshots/index.json'])
            checked[stage] = (data, report, native, entry)
        data, report, native, _ = checked['policy-anchor']
        policy_boundary(data, native, lineage['policy-anchor'][0]['case'])
        if checked['probe'][1]['before_circles'] != checked['source'][1]['before_circles']:
            raise ValueError('Original source/probe geometry differs')
        key = admission.cell_key(cell)
        result[key] = {'cell': list(cell), 'run_id': data['manifest']['run_id'],
            'case': lineage['policy-anchor'][0]['case'], 'snapshot_path': report['snapshot_path'],
            'snapshot_sha256': report['snapshot_sha256'], 'non_u': report['non_u'],
            'before_circles': report['before_circles'], 'pins': pins,
            'plan_path': str(Path(plan_path).resolve()), 'plan_sha256': plan_sha,
            'report_path': str(Path(report_path).resolve()), 'report_sha256': report_sha}
    return result


def verify_binding(binding, *, protocol_sha256=None, admission_lineage=None):
    """Reconcile a supplied binding with pinned plan/report before native restoration."""
    validate_binding_lineage(binding,protocol_sha256,admission_lineage)
    plan_sha,report_sha=admission_pins(protocol_sha256,admission_lineage)
    plan = admission.validate_plan(pinned_json(binding['plan_path'], plan_sha))
    terminal = pinned_json(binding['report_path'], report_sha)
    joined = derive_anchor(plan, terminal, binding['cell'], protocol_sha256=protocol_sha256)
    job, row = joined['policy-anchor']
    if (binding['run_id'] != job['run_id'] or memory.canonical_bytes(binding['case']) != memory.canonical_bytes(job['case'])
            or binding['snapshot_path'] != str(Path(job['output']) / 'snapshots/initial.snp')
            or binding['snapshot_sha256'] != row['snapshot_sha256'] or binding['non_u'] != row['initial_non_u']
            or binding['plan_sha256'] != plan_sha or binding['report_sha256'] != report_sha):
        raise ValueError('Policy binding was replaced by another owner/case/native state')
    expected_paths, reported_hashes = set(), {}
    for prepared, summary in joined.values():
        run = Path(prepared['output'])
        for item in summary['files']:
            path = str(run / item['path'])
            expected_paths.add(path)
            reported_hashes[path] = item['sha256']
        controls = [Path(plan['output']) / f"{prepared['run_id']}-job.json",
                    run / 'admission-worker.json', run / 'snapshots/initial.snp', run / 'snapshots/index.json']
        expected_paths.update(map(str, controls))
        reported_hashes[str(controls[1])] = summary['worker_report_sha256']
        reported_hashes[str(controls[2])] = summary['snapshot_sha256']
    paths = [pin['path'] for pin in binding['pins']]
    if len(paths) != len(set(paths)) or set(paths) != expected_paths:
        raise ValueError('Admission input-pin path coverage is incomplete or duplicated')
    for pin in binding['pins']:
        if (common._hash(pin['path']) != pin['sha256']
                or pin['path'] in reported_hashes and pin['sha256'] != reported_hashes[pin['path']]):
            raise ValueError('Original admission artifact changed')
    worker = pinned_json(Path(job['output']) / 'admission-worker.json', row['worker_report_sha256'])
    if memory.canonical_bytes(binding['before_circles']) != memory.canonical_bytes(worker['before_circles']):
        raise ValueError('Bound before geometry differs from the hash-pinned admission worker')
    data = common.read_run(Path(job['output']))
    native, entry, _ = _initial_snapshot(data)
    policy_boundary(data, native, job['case'])
    if common._hash(binding['snapshot_path']) != row['snapshot_sha256'] or entry['sha256'] != row['snapshot_sha256']:
        raise ValueError('Registered admission snapshot differs')
    return native

# Runtime composition intentionally uses the unchanged B/neural/manual helpers.
STAGES = ('anchor', *common.CONDITIONS)
PROTOCOL = {'version': 1, 'claim': 'four-cell-fixed-cpu-flynn-development-comparison',
    'cells': [list(c) for c in CELLS], 'stages': list(STAGES), 'total_owners': 40,
    'remaining_ticks': 300, 'max_numeric_ticks': 10800, 'controller': 'flynn', 'device': 'cpu',
    'allowed_branch_differences': ['u', 'declared-selector-configuration-and-resources'],
    'continuation_access': 'unchanged-policy.act-declared-cameras-and-sensors-only',
    'target_limit': 1, 'retries': 0, 'timeout_seconds': 160, 'internal_wall_seconds': 150,
    'outer_timeout_seconds': 6460, 'recording_max_bytes': 192*MiB, 'snapshot_max_bytes': 16*MiB,
    'aggregate_max_bytes': 10*GiB, 'min_free_bytes': 2*GiB, 'headroom_bytes': 64*MiB,
    'log_max_bytes': MiB, 'initial_snapshots_per_owner': 1,
    'admission_plan_sha256': B_PLAN_SHA256, 'admission_report_sha256': B_REPORT_SHA256,
    'admission_helper_sha256': LEGACY_ADMISSION_HELPER_SHA256,
    'neural_helper_sha256': common._hash(admission.HELPER),
    'manual_helper_sha256': common._hash(neural.HELPER),
    'resource_reference': neural.PROTOCOL['resource_reference']}
PROTOCOL_SHA256 = memory.sha256(PROTOCOL)
C4_CELLS = ((25, 'local_cue', 'change'), (28, 'paired_cue', 'change'),
            (26, 'paired_cue', 'null'), (31, 'local_cue', 'no-event'))
CORE_CONDITIONS = ('own', 'swapped', 'sham', 'no-U')
C4_PROTOCOL = {**copy.deepcopy(PROTOCOL), 'version': 2,
    'claim': 'remaining-four-b-cells-fixed-cpu-flynn-development-comparison',
    'cells': [list(c) for c in C4_CELLS],
    'strict_u_only_conditions': list(CORE_CONDITIONS),
    'core_selector': 'shared-own-dispatch-inherited-from-own-u-anchor',
    'allowed_branch_differences': {
        'core': ['u'], 'other-five': ['u', 'declared-selector-configuration-and-resources']}}
C4_PROTOCOL_SHA256 = memory.sha256(C4_PROTOCOL)

REMAINING_PROTOCOLS = {name: {**copy.deepcopy(C4_PROTOCOL), 'version':3,
    'claim':'fixed-remaining-development-comparison','chunk':i,
    'cells':[list(c) for c in cells],
    'admission_plan_sha256':None,'admission_report_sha256':None,
    'admission_protocol_sha256':admission.profile_digest(name),
    'admission_helper_sha256':common._hash(HELPER),
    'lineage':'separately-frozen-plan-and-terminal-report'}
    for i,(name,cells) in enumerate(zip(admission.REMAINING_NAMES,admission.REMAINING_CHUNKS),1)}


def remaining_profile(protocol_sha256):
    return type(protocol_sha256) is str and protocol_sha256 in {
        memory.sha256(p) for p in REMAINING_PROTOCOLS.values()}


def strict_profile(protocol_sha256):
    return protocol_sha256==C4_PROTOCOL_SHA256 or remaining_profile(protocol_sha256)


def profile_digest(name=None):
    if name is None or name=='c3':return PROTOCOL_SHA256
    if name=='c4':return C4_PROTOCOL_SHA256
    if name not in REMAINING_PROTOCOLS:raise ValueError('Unknown fixed comparison profile')
    return memory.sha256(REMAINING_PROTOCOLS[name])


def validate_lineage(value, protocol_sha256):
    """New chunks require independent plan-level pins; legacy B constants stay exact."""
    if not remaining_profile(protocol_sha256):
        if value is not None:raise ValueError('Historical comparison forbids new admission lineage')
        return None
    memory._fields(value,'version protocol_sha256 plan_path plan_sha256 report_path report_sha256')
    memory._version(value['version']);memory._bounded(value,4096)
    _,protocol=fixed_profile(protocol_sha256)
    if value['protocol_sha256']!=protocol['admission_protocol_sha256']:
        raise ValueError('Admission lineage belongs to another fixed chunk')
    for key in ('plan_sha256','report_sha256'):memory._digest(value[key])
    for key in ('plan_path','report_path'):
        if type(value[key]) is not str or not Path(value[key]).is_absolute():
            raise ValueError('Admission lineage paths must be absolute')
        artifacts._safe_path(Path(value[key]))
    if value['plan_path']==value['report_path']:raise ValueError('Distinct admission plan/report required')
    return copy.deepcopy(value)


def validate_executor_provenance(identity, protocol_sha256):
    if not remaining_profile(protocol_sha256):return
    _,protocol=fixed_profile(protocol_sha256)
    if (type(identity) is not dict or identity.get('admission_helper_sha256')!=common._hash(HELPER)
            or identity.get('admission_helper_sha256')!=protocol['admission_helper_sha256']
            or identity.get('driver_sha256')!=common._hash(Path(__file__))):
        raise ValueError('Current executor helper/driver bytes differ from the new chunk protocol')


def admission_pins(protocol_sha256, lineage=None):
    value=validate_lineage(lineage,protocol_sha256)
    return (B_PLAN_SHA256,B_REPORT_SHA256) if value is None else (value['plan_sha256'],value['report_sha256'])


def validate_binding_lineage(binding, protocol_sha256, lineage=None):
    plan_sha,report_sha=admission_pins(protocol_sha256,lineage)
    if (binding['plan_sha256']!=plan_sha or binding['report_sha256']!=report_sha
            or lineage is not None and (binding['plan_path']!=lineage['plan_path']
                                       or binding['report_path']!=lineage['report_path'])):
        raise ValueError('Binding differs from separately frozen admission lineage')


def fixed_profile(protocol_sha256=None):
    """Only historical C3/C4 and the ten declared remaining profiles are admissible."""
    if protocol_sha256 is None or protocol_sha256 == PROTOCOL_SHA256:
        return CELLS, copy.deepcopy(PROTOCOL)
    if protocol_sha256 == C4_PROTOCOL_SHA256:
        return C4_CELLS, copy.deepcopy(C4_PROTOCOL)
    for name,cells in zip(admission.REMAINING_NAMES,admission.REMAINING_CHUNKS):
        protocol=REMAINING_PROTOCOLS[name]
        if protocol_sha256==memory.sha256(protocol):return cells,copy.deepcopy(protocol)
    raise ValueError('Unknown fixed comparison profile')


def strict_core(job):
    return strict_profile(job['protocol_sha256']) and job['stage'] in CORE_CONDITIONS


def branch_invariants(native, job):
    """Strict core forks retain selector/version and every scientific state except U."""
    return invariant_hashes(native) if strict_core(job) else common.baseline_invariants(native)


def source_identity(repo, assets):
    result = neural.source_identity(repo, assets)
    result.update(driver_sha256=common._hash(Path(__file__)), admission_helper_sha256=common._hash(HELPER))
    return result


def budget(output):
    return StorageBudget((Path(output),), StorageLimits(max_bytes=10*GiB, min_free_bytes=2*GiB,
        max_runs=40, max_snapshots=1), headroom_bytes=64*MiB)


def histories_for(cell, histories):
    return copy.deepcopy(histories if cell[1] == 'local_cue' else
                         {'own': histories['swapped'], 'swapped': histories['own']})


def history_pins(root, histories):
    return {k: {'path': str(Path(root)/v['path']), 'sha256': v['sha256'],
        'e_sha256': memory.sha256(v['e']), 'u_sha256': memory.sha256(v['u'])} for k, v in histories.items()}


def selector_config(stage, histories, oracle=None, *, protocol_sha256=None):
    _, protocol = fixed_profile(protocol_sha256)
    digest = memory.sha256(protocol)
    if strict_profile(digest) and stage in ('anchor', *CORE_CONDITIONS):
        return {'version': 1, 'condition': 'own', 'limit': 1, 'resource': None,
            'resource_sha256': memory.sha256(None), 'provenance_sha256': digest}
    result = common.selector_config(stage, histories, oracle)
    if stage in ('no-U', 'hand-authored', 'history-independent', 'traversal'):
        result['provenance_sha256'] = digest
    return result


def make_plan(repo, assets, output, history_root, admission_plan, admission_report, *, protocol_sha256=None, admission_lineage=None):
    cells, protocol = fixed_profile(protocol_sha256)
    digest = memory.sha256(protocol)
    repo, assets, output, history_root = map(artifacts._safe_path, (repo, assets, output, history_root))
    lineage=validate_lineage(admission_lineage,digest)
    bindings = load_bindings(admission_plan, admission_report, protocol_sha256=digest,admission_lineage=lineage)
    histories = common.load_histories(history_root)
    result = {'version': 1, 'protocol': protocol, 'protocol_sha256': digest,
        'repo': str(repo), 'assets': str(assets), 'output': str(output), 'history_root': str(history_root),
        'source_identity': source_identity(repo, assets), 'history_inputs': history_pins(history_root, histories),
        'bindings': bindings, 'jobs': [{'cell': list(c), 'stage': s, 'run_id': uuid.uuid4().hex}
                                     for c in cells for s in STAGES]}
    if lineage is not None:result['admission_lineage']=lineage
    return result


def validate_plan(plan):
    memory._fields(plan, 'version protocol protocol_sha256 repo assets output history_root source_identity history_inputs bindings jobs'
                   + (' admission_lineage' if remaining_profile(plan.get('protocol_sha256')) else ''))
    memory._version(plan['version']); memory._bounded(plan, MiB)
    memory._digest(plan['protocol_sha256'])
    cells, protocol = fixed_profile(plan['protocol_sha256'])
    lineage=validate_lineage(plan.get('admission_lineage'),plan['protocol_sha256'])
    validate_executor_provenance(plan['source_identity'],plan['protocol_sha256'])
    if (memory.canonical_bytes(plan['protocol']) != memory.canonical_bytes(protocol)
            or Path(plan['repo']) != Path(__file__).resolve().parents[1]
            or [(j['cell'], j['stage']) for j in plan['jobs']] != [(list(c), s) for c in cells for s in STAGES]
            or len({j['run_id'] for j in plan['jobs']}) != 40
            or set(plan['bindings']) != {admission.cell_key(c) for c in cells}):
        raise ValueError('Exactly the declared forty-owner comparison plan is required')
    for name in ('repo', 'assets', 'output', 'history_root'):
        if not Path(plan[name]).is_absolute(): raise ValueError('Comparison paths must be absolute')
    for job in plan['jobs']:
        memory._fields(job, 'cell stage run_id'); artifacts._id(job['run_id'])
    for cell in cells:
        binding = plan['bindings'][admission.cell_key(cell)]
        if lineage is not None:validate_binding_lineage(binding,plan['protocol_sha256'],lineage)
        if memory.canonical_bytes(binding['cell']) != memory.canonical_bytes(list(cell)) or memory.canonical_bytes(binding['case']) != memory.canonical_bytes(admission.make_case(cell)):
            raise ValueError('Comparison binding has another canonical case')
    return copy.deepcopy(plan)


def observed_trigger(state, data, case):
    """Reconstruct only from native 299 and actual 300; never inject an event."""
    packet = admission.admit_packet(data['events'], case, state, 300)
    prior = state['detector']; cue = packet['cues'][0]
    if (prior['tick'] != 299 or prior['cues'] != [{'id': cue['id'], 'state': 0,
            'observation_id': memory_task._sensor_id(state['episode_id'], 299, 'cue', cue['id'])}]):
        raise ValueError('Consecutive pre-event native cue evidence differs')
    events = [e for e in data['events'] if e['kind'] == 'memory_decision'
              and e['detail']['kind'] in ('memory_trigger', 'memory_selection')]
    if any((e.get('episode'), e.get('episode_step'), e.get('tick')) != (0, 300, 300) for e in events):
        raise ValueError('Trigger/selection occurred outside its declared boundary')
    triggers = [e['detail']['trigger'] for e in events if e['detail']['kind'] == 'memory_trigger']
    selections = [e['detail']['selection'] for e in events if e['detail']['kind'] == 'memory_selection']
    expected = None if not case['event_enabled'] else memory.validate_trigger({
        'id': memory_task._sensor_id(state['episode_id'], 300, 'trigger', cue['id']),
        'episode_id': state['episode_id'], 'tick': 300, 'kind': 'cue_changed', 'cue_id': cue['id'],
        'before': 0, 'after': 1, 'before_observation_id': prior['cues'][0]['observation_id'],
        'observation_id': memory_task._sensor_id(state['episode_id'], 300, 'cue', cue['id'])})
    if triggers != ([] if expected is None else [expected]) or len(selections) != int(expected is not None):
        raise ValueError('Actual trigger/selector invocation differs from witnessed cue schedule')
    return expected, selections


def gold_proof(binding, source_native, data, report):
    state = source_native['application']['memory']; case = binding['case']
    trigger, _ = observed_trigger(state, data, case)
    after = artifacts._world_at(data['events'], 0, 300)['obstacles']
    if report['after_circles'] != after: raise ValueError('Donor report differs from actual physical geometry')
    before = binding['before_circles']
    return {'version': 1, 'binding_sha256': memory.sha256(binding),
        'source_snapshot_sha256': binding['snapshot_sha256'], 'pre_m_sha256': memory.sha256(state['m']),
        'post_run_id': data['manifest']['run_id'], 'post_recording_sha256': common.recording_digest(data),
        'post_worker_sha256': common._hash(data['run']/'comparison-worker.json'),
        'before_circles': before, 'after_circles': after, 'trigger': trigger,
        'gold_target_ids': experiment.gold_target_ids(state['m'], common.occupancy(case, before),
                                                    common.occupancy(case, after), trigger)}


def check_oracle(job, source_native):
    proof = job['oracle_evidence']
    artifacts._id(proof['post_run_id'])
    data = common.read_run(Path(job['root_output'])/'runs'/proof['post_run_id'])
    report = artifacts._json(artifacts._read(data['run']/'comparison-worker.json', MiB))
    manifest = data['manifest']
    if (manifest.get('comparison_stage') != 'own' or manifest.get('comparison_cell') != job['cell']
            or manifest.get('comparison_protocol_sha256') != job['protocol_sha256']
            or manifest.get('comparison_binding_sha256') != memory.sha256(job['binding'])
            or manifest.get('memory_case') != job['binding']['case']):
        raise ValueError('Oracle donor belongs to another owner/cell/protocol')
    if memory.canonical_bytes(gold_proof(job['binding'], source_native, data, report)) != memory.canonical_bytes(proof):
        raise ValueError('Oracle resource differs from hash-validated actual donor evidence')


def validate_job(job):
    memory._fields(job, 'repo assets history_root output root_output run_id cell stage binding protocol_sha256 source_identity history_inputs snapshot_path snapshot_sha256 expected_non_u selector oracle_evidence'
                   + (' admission_lineage' if remaining_profile(job.get('protocol_sha256')) else ''))
    memory._bounded(job, 128*1024)
    memory._digest(job['protocol_sha256'])
    cells, _ = fixed_profile(job['protocol_sha256'])
    lineage=validate_lineage(job.get('admission_lineage'),job['protocol_sha256'])
    validate_executor_provenance(job['source_identity'],job['protocol_sha256'])
    if lineage is not None:validate_binding_lineage(job['binding'],job['protocol_sha256'],lineage)
    artifacts._id(job['run_id'])
    if (tuple(job['cell']) not in cells or job['stage'] not in STAGES
            or Path(job['repo']) != Path(__file__).resolve().parents[1]
            or Path(job['output']) != Path(job['root_output'])/'runs'/job['run_id']
            or memory.canonical_bytes(job['binding']['cell']) != memory.canonical_bytes(job['cell'])
            or memory.canonical_bytes(job['binding']['case']) != memory.canonical_bytes(admission.make_case(tuple(job['cell'])))
            or any(not Path(job[k]).is_absolute() for k in ('repo','assets','history_root','output','root_output','snapshot_path'))):
        raise ValueError('Unsupported fixed comparison job')
    memory._digest(job['snapshot_sha256'])
    if type(job['expected_non_u']) is not dict: raise ValueError('Missing native preservation guard')
    histories = common.load_histories(job['history_root'])
    if history_pins(job['history_root'], histories) != job['history_inputs']:
        raise ValueError('Historical E/U source differs')
    histories = histories_for(job['cell'], histories)
    config = selector_config(job['stage'], histories, job['oracle_evidence'], protocol_sha256=job['protocol_sha256'])
    if memory.canonical_bytes(job['selector']) != memory.canonical_bytes(config):
        raise ValueError('Condition-specific resource/provenance differs')
    memory_task.validate_selector(config, memory.seed_m(job['binding']['case']['facts'], []),
                                 common.condition_u(job['stage'], histories))
    if (job['stage'] == 'oracle') != (job['oracle_evidence'] is not None):
        raise ValueError('Only oracle may receive privileged gold')
    return copy.deepcopy(job)


def validate_selector_boundary(job, native, ancestor, events, histories):
    """Bind logical artifacts and the exact core state before the first policy call."""
    app = native['application']
    state = memory_task.validate_state(app['memory'])
    expected = selector_config(job['stage'], histories, job['oracle_evidence'],
                               protocol_sha256=job['protocol_sha256'])
    if (state['u'] != common.condition_u(job['stage'], histories)
            or state.get('selector') != expected or job['selector'] != expected
            or branch_invariants(native, job) != job['expected_non_u']
            or branch_invariants(ancestor, job) != job['expected_non_u']):
        raise ValueError('Logical condition artifact or native selector/preservation guard differs')
    configured = [e for e in events if e['kind'] == 'selector_configured']
    if strict_core(job):
        source = memory_task.validate_state(ancestor['application']['memory'])
        restored = [e for e in events if e['kind'] == 'application_restored']
        if (source.get('selector') != expected or source['u'] != common.condition_u('anchor', histories)
                or common.baseline_invariants(ancestor) != job['binding']['non_u']
                or configured or len(restored) != 1
                or restored[0].get('parent_run_id') != ancestor['application']['source_run_id']
                or restored[0].get('parent_event_prefix') != ancestor['application']['event_prefix']
                or restored[0]['sequence'] >= app['event_prefix']['event_count']):
            raise ValueError('Strict U-only fork did not inherit its shared anchor selector/prefix')
    elif (len(configured) != 1 or configured[0].get('configuration') != expected
            or configured[0].get('configuration_sha256') != memory.sha256(expected)
            or configured[0].get('episode_step') != 300
            or configured[0]['sequence'] >= app['event_prefix']['event_count']):
        raise ValueError('Registered selector event prefix differs')
    if strict_profile(job['protocol_sha256']):
        swaps = [e for e in events if e['kind'] == 'memory_u_replaced']
        if (len(swaps) != 1 or swaps[0].get('old_u') != ancestor['application']['memory']['u']
                or swaps[0].get('new_u') != state['u']
                or swaps[0].get('invariant_hashes') != invariant_hashes(ancestor)
                or swaps[0]['sequence'] >= app['event_prefix']['event_count']):
            raise ValueError('Exact condition U replacement proof differs')
    return state


def worker(raw):
    from palimpsest.engine import Engine
    job = validate_job(raw)
    _, protocol = fixed_profile(job['protocol_sha256'])
    if source_identity(job['repo'], job['assets']) != job['source_identity']:
        raise ValueError('Worker authoring source/assets changed')
    original = verify_binding(job['binding'], protocol_sha256=job['protocol_sha256'],admission_lineage=job.get('admission_lineage'))
    if common._hash(job['snapshot_path']) != job['snapshot_sha256']:
        raise ValueError('Comparison ancestor snapshot changed')
    ancestor = read_snapshot(job['snapshot_path'])
    if (branch_invariants(ancestor, job) != job['expected_non_u']
            or common.baseline_invariants(ancestor) != job['binding']['non_u']
            or common.baseline_invariants(original) != job['binding']['non_u']):
        raise ValueError('Ancestor changed physics/controller/RNG/task state')
    if job['stage'] == 'oracle': check_oracle(job, original)
    histories = histories_for(job['cell'], common.load_histories(job['history_root']))
    u = common.condition_u(job['stage'], histories)
    run, case = Path(job['output']), job['binding']['case']
    storage = budget(job['root_output']); storage.check(208*MiB, path=run)
    report = {'status':'failed','stage':job['stage'],'run_path':str(run),'task_pass':None}
    engine = None; started = time.monotonic()
    try:
        engine = Engine.open(job['repo'],job['assets'],run/'recording',run_id=job['run_id'],
            controller='flynn',device='cpu',scenario='memory-passages',seed=case['seed'],
            memory_case=case,max_bytes=192*MiB,storage_budget=storage,restore_snapshot=ancestor,memory_u=u)
        engine.writer.manifest.update(comparison_protocol=protocol,comparison_protocol_sha256=job['protocol_sha256'],
            comparison_cell=job['cell'],comparison_stage=job['stage'],comparison_source_identity=job['source_identity'],
            comparison_binding=job['binding'],comparison_binding_sha256=memory.sha256(job['binding']),
            selector_configuration=job['selector'],oracle_evidence=job['oracle_evidence'],
            continuation_access=protocol['continuation_access'])
        if remaining_profile(job['protocol_sha256']):
            engine.writer.manifest.update(comparison_admission_lineage=job['admission_lineage'])
        if strict_profile(job['protocol_sha256']):
            engine.writer.manifest.update(comparison_history_inputs=job['history_inputs'],
                comparison_condition_u_sha256=memory.sha256(u),
                comparison_preservation='u-only' if strict_core(job) else 'declared-u-and-selector')
        if not strict_core(job):
            engine.memory = memory_task.configure_selector(engine.memory,job['selector'])
            engine._event('selector_configured',configuration=job['selector'],configuration_sha256=memory.sha256(job['selector']))
        current = capture(engine.env,engine.observation,policy=engine.policy,application=engine.application_state())
        if branch_invariants(current, job) != job['expected_non_u']:
            raise ValueError('Atomic restore/configuration changed non-U/selector state')
        report['before_circles'] = memory_world.sensing_inputs(engine.env,engine.world_task_state)[2]
        _register_initial(engine,run,neural._SnapshotBudget(storage))
        native = read_snapshot(run/'snapshots/initial.snp')
        validate_selector_boundary(job, native, ancestor, artifacts._events(run), histories)
        report.update(snapshot_path=str(run/'snapshots/initial.snp'),snapshot_sha256=common._hash(run/'snapshots/initial.snp'),
                      non_u=branch_invariants(native, job))
        if job['stage'] != 'anchor':
            neural.audit_policy(engine)
            for _ in range(300):
                if time.monotonic()-started > 150: raise TimeoutError('Continuation internal wall bound')
                tick = engine.episode_step
                state = neural.policy_step(engine,tick)
                if tick == 300:
                    report['after_circles'] = memory_world.sensing_inputs(engine.env,engine.world_task_state)[2]
                    packet = admission.admit_packet(artifacts._events(run),case,engine.memory,300)
                    report['packet300_sha256'] = memory.sha256(packet)
                    report['boundary_memory'] = common.packet_cursor(packet,engine.memory)
                if state['phase'] != 'paused': break
        report['status'] = 'recorded'
    except Exception as error:
        report['error'] = {'type':type(error).__name__,'message':str(error)}
    finally:
        if engine is not None:
            report.update(final_phase=engine.phase,outcome=engine.last_outcome,steps=engine.episode_step,
                final_memory=copy.deepcopy(engine.memory),final_world=copy.deepcopy(engine.world_task_state))
            report['gate_result'] = engine.world_task_state['gate_result']
            try: engine.close()
            except Exception as error:
                report.update(status='cleanup_failed',cleanup_error={'type':type(error).__name__,'message':str(error)})
    report['wall_seconds'] = time.monotonic()-started
    neural.write(run/'comparison-worker.json',report,storage)
    return 0 if report['status']=='recorded' and (report.get('final_phase')!='failed' or neural.task_failure(report)) else 1


def validate_stage(job, supervised):
    _, protocol = fixed_profile(job['protocol_sha256'])
    if supervised['status'] != 'completed' or supervised.get('returncode') != 0:
        raise ValueError('Infrastructure/worker failure; no retry')
    data = common.read_run(Path(job['output']))
    report = artifacts._json(artifacts._read(data['run']/'comparison-worker.json',MiB))
    native, entry, _ = _initial_snapshot(data)
    app, manifest, events = native['application'], data['manifest'], data['events']
    state = memory_task.validate_state(app['memory']); case = job['binding']['case']
    histories = histories_for(job['cell'],common.load_histories(job['history_root']))
    expected = {'memory_case':case,'memory_case_sha256':memory.sha256(case),
        'comparison_protocol':protocol,'comparison_protocol_sha256':job['protocol_sha256'],
        'comparison_cell':job['cell'],'comparison_stage':job['stage'],
        'comparison_source_identity':job['source_identity'],'comparison_binding':job['binding'],
        'comparison_binding_sha256':memory.sha256(job['binding']),
        'selector_configuration':job['selector'],'oracle_evidence':job['oracle_evidence'],
        'continuation_access':protocol['continuation_access']}
    if remaining_profile(job['protocol_sha256']):
        expected['comparison_admission_lineage']=job['admission_lineage']
    if strict_profile(job['protocol_sha256']):
        expected.update(comparison_history_inputs=job['history_inputs'],
            comparison_condition_u_sha256=memory.sha256(common.condition_u(job['stage'], histories)),
            comparison_preservation='u-only' if strict_core(job) else 'declared-u-and-selector')
    if (any(memory.canonical_bytes(manifest.get(k)) != memory.canonical_bytes(v) for k,v in expected.items())
            or manifest.get('run_id') != job['run_id'] or manifest.get('controller') != 'flynn'
            or manifest.get('requested_device') != 'cpu' or manifest.get('seed') != case['seed']
            or manifest.get('recording_max_bytes') != 192*MiB or manifest.get('close_reason') != 'operator_closed'
            or report.get('status') != 'recorded' or report.get('stage') != job['stage']
            or report.get('run_path') != job['output'] or 'cleanup_error' in report or report.get('task_pass') is not None
            or report.get('final_phase') != manifest.get('final_phase') or report.get('outcome') != manifest.get('last_outcome')
            or (manifest['status']=='failed') != (report['final_phase']=='failed')
            or report.get('steps') != manifest.get('total_tick') or report.get('snapshot_sha256') != entry['sha256']
            or report.get('snapshot_path') != str(data['run']/'snapshots/initial.snp')
            or (data['run']/'snapshots/initial.snp').stat().st_size > 16*MiB):
        raise ValueError('Stage terminal/source/case/resource/cleanup identity differs')
    environments = [e for e in events if e['kind']=='environment']
    if len(environments)!=1 or any(environments[0].get(k)!=job['source_identity'][k]
                                  for k in ('source_sha256','lock_sha256','upstream_commit')):
        raise ValueError('Recorded authoring-source identity differs')
    if (app['phase']!='paused' or (app['episode'],app['episode_step'],app['total_tick'])!=(0,300,300)
            or app['controller']!='flynn' or app['execution_mode']!='live'
            or state['cursor']['tick']!=299 or state['detector']['tick']!=299
            or native['policy'] is None or app['controller_tensors'] is None or native['identity']['policy']['device']!='cpu'
            or state['e']['episodes'] or state['u']!=common.condition_u(job['stage'],histories)
            or state.get('selector')!=job['selector'] or state['initial_m']!=memory.seed_m(case['facts'],[])
            or app['world_task_state']['case']!=case or app['world_task_state']['applied']
            or branch_invariants(native,job)!=job['expected_non_u'] or report['non_u']!=job['expected_non_u']
            or not np.array_equal(native['environment']['values']['_goal_xy'],np.asarray(common.effective_goal(),np.float32))):
        raise ValueError('Native CPU/controller/RNG/M/E/U/selector/world boundary differs')
    if common._hash(job['snapshot_path'])!=job['snapshot_sha256']: raise ValueError('Ancestor native changed')
    ancestor = read_snapshot(job['snapshot_path'])
    expected_admission = {'source_run_id':ancestor['application']['source_run_id'],
        'source_controller':ancestor['application']['controller'],'snapshot_state_sha256':state_digest(ancestor),
        'native_sha256':ancestor['native_sha256'],'case_sha256':memory.sha256(case),
        'replace_controller':False,'memory_u_sha256':memory.sha256(common.condition_u(job['stage'],histories))}
    if manifest.get('memory_continuation_admission')!=expected_admission:
        raise ValueError('Atomic restoration or registered selector event prefix differs')
    validate_selector_boundary(job,native,ancestor,events,histories)
    final = memory_task.validate_state(report['final_memory'])
    world = memory_world.validate_state(report['final_world'])
    if (world['case']!=case or world['gate_result']!=report['gate_result']
            or report['before_circles']!=job['binding']['before_circles']
            or any(memory.canonical_bytes(final.get(k))!=memory.canonical_bytes(state.get(k))
                   for k in ('e','u','selector','initial_m'))):
        raise ValueError('Continuation changed its resources/initial bank/world case')
    rows = data['rows']
    if job['stage']=='anchor':
        if (rows or report['steps']!=300 or report['final_phase']!='paused' or manifest['status']!='completed'
                or final!=state or world!=app['world_task_state']
                or any(e['kind'] in ('neural_policy_call','memory_sensed','command_received') for e in events)):
            raise ValueError('Zero-tick own-U anchor advanced or changed state')
    else:
        if (not rows or len(rows)>300 or [r['tick'] for r in rows]!=list(range(300,300+len(rows)))
                or report['steps']!=300+len(rows) or report['final_phase'] not in ('paused','terminated','failed')
                or manifest['status']=='failed' and not neural.task_failure(report)):
            raise ValueError('Continuation exceeded its boundary or has an unsupported runtime failure')
        neural.policy_bindings(data)
        packet, circles = admission.actual_packet(data,case,state)
        if report.get('packet300_sha256')!=memory.sha256(packet) or report['after_circles']!=circles:
            raise ValueError('Packet300/actual geometry differs from the retained worker')
        inspected = [e['memory'] for e in events if e['kind']=='memory_inspected' and e.get('episode_step')==300]
        bearings = [e['bearing'] for e in events if e['kind']=='memory_cue' and e.get('episode_step')==300]
        proof = report['boundary_memory']
        if len(inspected)!=1 or len(bearings)!=1 or inspected[0]['facts_truncated']!=0:
            raise ValueError('Packet300 lacks its complete committed supervisor/bearing')
        committed = {**proof,'active':inspected[0]['active'],'m':{'facts':inspected[0]['facts']}}
        if common.packet_cursor(packet,committed)!=proof or proof['cursor']['bearing']!=bearings[0]:
            raise ValueError('Packet300 native cursor/committed publication differs')
        observed_trigger(state,data,case)
        failures = [e for e in events if e['kind']=='runtime_failure']
        failed = manifest['status']=='failed'
        commands = [e['command'] for e in events if e['kind']=='command_received']
        if ([c['id'] for c in commands]!=[f'neural-{t}' for t in range(300,report['steps']+int(failed))]
                or len(failures)!=int(failed) or failed and (
                    failures[0].get('episode_step')!=report['steps'] or failures[0].get('error')!=report['outcome'])):
            raise ValueError('Attempted-step/retained task-failure boundary accounting differs')
        changes = [e['detail'] for e in events if e['kind']=='memory_world_changed']
        kinds = [] if not case['event_enabled'] else ['memory_cue_changed'] + (
            ['memory_gate_applied'] if case['kind']=='change' else []) + ['memory_passage_geometry']
        if ([v['kind'] for v in changes]!=kinds or any(v['tick']!=300 for v in changes)
                or report['gate_result']!=('closed' if case['kind']=='change' else 'not_requested')
                or any((e.get('episode'),e.get('episode_step'),e.get('tick'))!=(0,300,300)
                       for e in events if e['kind']=='memory_world_changed')
                or changes and (changes[-1]['before']!=common.occupancy(case,report['before_circles'])
                                or changes[-1]['after']!=common.occupancy(case,circles))):
            raise ValueError('Actual cue/gate closure receipts differ from physical clearance')
    return data, report, native, entry


def condition_readout(case, m, trigger, score, data, report, after):
    """Read actual observations/commits; missing timing stays null or censored."""
    decisions = [e['detail'] for e in data['events'] if e['kind']=='memory_decision']
    selections = [d['selection'] for d in decisions if d['kind']=='memory_selection']
    if selections!=([score['selection']] if trigger is not None else []):
        raise ValueError('Recorded selector result/invocation differs from shared pure selector')
    inspections = [d for d in decisions if d['kind']=='memory_inspection']
    final = report['final_memory']
    unresolved = [v['fact_id'] for v in final['requests']] + ([] if final['active'] is None else [final['active']['fact_id']])
    timing = []
    for fact in m['facts']:
        observations = [e['packet']['tick'] for e in data['events'] if e['kind']=='memory_sensed'
            for sample in e['packet']['passages'] if sample['subject_id']==fact['subject_id']
            and sample['passability']==after[fact['subject_id']] and e['packet']['tick']>=300]
        revisions = [d['revision'] for d in decisions if d['kind']=='memory_revision' and d['revision']['fact_id']==fact['id']]
        commits = [v['tick'] for v in revisions if v['after']['status']=='observed'
                   and v['after']['estimate']==after[fact['subject_id']] and v['tick']>=300]
        intervals = []; start = None
        for revision in revisions:
            if revision['after']['status']=='uncertain' and start is None: start=revision['tick']
            elif revision['after']['status']!='uncertain' and start is not None:
                intervals.append({'start_tick':start,'end_tick':revision['tick'],
                                  'duration_ticks':revision['tick']-start,'censored':False}); start=None
        if start is not None:
            intervals.append({'start_tick':start,'end_tick':None,'duration_ticks':report['steps']-start,'censored':True})
        correction = fact['estimate']!=after[fact['subject_id']]
        timing.append({'fact_id':fact['id'],'stale_value_changed':correction,
            'first_correct_observed_tick':min(observations,default=None),'first_correct_committed_tick':min(commits,default=None),
            'first_stale_value_correction_tick':min(commits,default=None) if correction else None,
            'first_confirmation_tick':min(commits,default=None) if not correction else None,
            'uncertainty_intervals':intervals})
    navigation = report['final_phase']=='terminated' and (report['outcome'] or {}).get('reason')=='goal'
    fresh = [f['id'] for f in final['m']['facts'] if f['status']=='observed' and f['evidence']['tick']>=300
             and f['estimate']==after[f['subject_id']]]
    return {'condition':score['condition'],'selector_invocations':len(selections),
        'selector_behavior_bytes':score['behavior_input_bytes'],'target_ids':score['selection']['target_ids'],
        'recording_status':data['manifest']['status'],'final_phase':report['final_phase'],'outcome':report['outcome'],
        'requested':sum(v['status']=='requested' for v in inspections),'started':sum(v['status']=='started' for v in inspections),
        'resolved':sum(v['status']=='resolved' for v in inspections),'timeouts':sum(v['status']=='timeout' for v in inspections),
        'unresolved_fact_ids':unresolved,'fresh_correct_fact_ids':fresh,'navigation_pass':navigation,
        'goal_tick':report['steps'] if navigation else None,'terminal_control_boundary':report['steps'],
        'timing':timing,'worker_task_pass':report['task_pass'],
        'selector_configuration_sha256':memory.sha256(final['selector']),
        'resource_sha256':final['selector']['resource_sha256'],'provenance_sha256':final['selector']['provenance_sha256']}


def evaluate_cell(binding, native, parents, histories):
    case, m = binding['case'], native['application']['memory']['m']
    own_data, own_report, _ = parents['own']
    proof = gold_proof(binding,native,own_data,own_report)
    before, after = [common.occupancy(case,proof[k+'_circles']) for k in ('before','after')]
    gold = proof['gold_target_ids']; trigger = proof['trigger']
    if len([s for s in before if before[s]!=after[s]])!=int(case['kind']=='change') or len(gold)!=int(case['kind']=='change'):
        raise ValueError('Actual acquired-expectation/clearance gold differs from schedule')
    scores = common.score_nine(m,trigger,histories,gold); runtime = []; comparisons = []
    for score in scores:
        data, report, _ = parents[score['condition']]
        actual_trigger, _ = observed_trigger(native['application']['memory'],data,case)
        if report['after_circles']!=proof['after_circles'] or actual_trigger!=trigger:
            raise ValueError('World geometry or witnessed cue differs across conditions')
        row = condition_readout(case,m,trigger,score,data,report,after)
        row['revision_pass'] = not row['unresolved_fact_ids'] and set(gold)<=set(row['fresh_correct_fact_ids'])
        row['task_pass'] = row['navigation_pass'] and row['revision_pass']
        runtime.append(row)
        if score['condition']!='own':
            left,right = own_data['rows'],data['rows']; mismatch = None
            for a,b in zip(left,right):
                try: common._same_tick(a,b,'policy',a['tick'])
                except common.Divergence as error: mismatch=error.detail; break
            comparisons.append({'reference':'own','condition':score['condition'],'shared_ticks':min(len(left),len(right)),
                'same_length':len(left)==len(right),'first_divergence':mismatch,
                'scope':'existing replay tolerances; frames are not independent samples'})
    sham = next(v for v in comparisons if v['condition']=='sham')
    if not sham['same_length'] or sham['first_divergence'] is not None: raise ValueError('Own/sham continuation differs')
    return {'cell':admission.cell_key(binding['cell']),'pre_m_sha256':memory.sha256(m),'trigger':trigger,
        'before_occupancy':before,'after_occupancy':after,'gold_target_ids':gold,
        'oracle_evidence':proof,'oracle_evidence_sha256':memory.sha256(proof),
        'targeting':scores,'runtime':runtime,'trajectory_comparisons':comparisons,
        'r2_complete':False,'held_out_executed':False,'operator_blindness_verified':False}


def run_verifier(raw):
    plan = validate_plan(raw); output = Path(plan['output'])
    _, protocol = fixed_profile(plan['protocol_sha256'])
    first = next(iter(plan['bindings'].values()))
    if memory.canonical_bytes(load_bindings(first['plan_path'],first['report_path'],
            protocol_sha256=plan['protocol_sha256'],admission_lineage=plan.get('admission_lineage'))) != memory.canonical_bytes(plan['bindings']):
        raise ValueError('Prepared policy bindings differ from original admission lineage')
    histories = common.load_histories(plan['history_root'])
    if history_pins(plan['history_root'],histories)!=plan['history_inputs']:
        raise ValueError('Prepared E-only historical evidence changed')
    for binding in plan['bindings'].values():
        if experiment._ids(binding['case']) & set().union(*(experiment._ids(v['e']) for v in histories.values())):
            raise ValueError('Historical evidence overlaps the current instance')
    if source_identity(plan['repo'],plan['assets'])!=plan['source_identity']:
        raise ValueError('Frozen authoring source/assets changed')
    if output.exists(): raise ValueError('Output must be fresh; no retries')
    existing = output.parent
    while not existing.exists(): existing = existing.parent
    if shutil.disk_usage(existing).free < 12*GiB+64*MiB:
        raise ValueError('Comparison requires 10 GiB allowance + 2 GiB free floor + headroom')
    storage = budget(output); summaries = []; parents = {}; retained = []; started = time.monotonic()
    result = {'version':1,'claim':protocol['claim'],'protocol_sha256':plan['protocol_sha256'],
        'status':'comparison_unverified','runs':summaries,'comparisons':[],
        'history_inputs':plan['history_inputs'],'bindings':plan['bindings'],
        'r2_complete':False,'held_out_executed':False,'full_matrix_executed':False}
    env = {**os.environ,'PYTHONPATH':str(Path(plan['repo'])/'src'),
           'MUJOCO_GL':'egl','MPLBACKEND':'Agg','OMP_NUM_THREADS':'2'}
    with storage.lock():
        (output/'runs').mkdir(); storage.check_count('runs',0,40)
        neural.write(output/'comparison-plan.json',plan,storage)
        current_job = current_summary = None
        try:
            for prepared in plan['jobs']:
                current_job = prepared; current_summary = None
                if time.monotonic()-started > 6460-160:
                    raise TimeoutError('No aggregate wall budget for another owner')
                key, stage = admission.cell_key(prepared['cell']), prepared['stage']
                binding = plan['bindings'][key]
                cell_parents = parents.setdefault(key,{})
                source = verify_binding(binding,protocol_sha256=plan['protocol_sha256'],admission_lineage=plan.get('admission_lineage'))
                ancestor = binding if stage=='anchor' else cell_parents['anchor'][1]
                mapped = histories_for(prepared['cell'],histories)
                proof = None if stage!='oracle' else gold_proof(binding,source,*cell_parents['own'][:2])
                job = {**copy.deepcopy(prepared), **{k:plan[k] for k in ('repo','assets','history_root','source_identity','history_inputs')},
                    'root_output':str(output),'output':str(output/'runs'/prepared['run_id']),
                    'binding':binding,'protocol_sha256':plan['protocol_sha256'],
                    'snapshot_path':ancestor['snapshot_path'],'snapshot_sha256':ancestor['snapshot_sha256'],
                    'expected_non_u':invariant_hashes(cell_parents['anchor'][2])
                        if strict_profile(plan['protocol_sha256']) and stage in CORE_CONDITIONS else binding['non_u'],
                    'selector':selector_config(stage,mapped,proof,protocol_sha256=plan['protocol_sha256']),
                    'oracle_evidence':proof}
                if remaining_profile(plan['protocol_sha256']):job['admission_lineage']=copy.deepcopy(plan['admission_lineage'])
                validate_job(job); neural.write(output/f"{job['run_id']}-job.json",job,storage)
                print(json.dumps({'cell':key,'stage':stage,'run_id':job['run_id']}),flush=True)
                supervised = bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',json.dumps(job)],
                    Path(job['output']),160,env,log_max_bytes=MiB,storage_budget=storage)
                summary = {'cell':key,'stage':stage,'run_id':job['run_id'],'run_path':job['output'],'supervisor':supervised}
                summaries.append(summary); current_summary = summary
                data, report, native, entry = validate_stage(job,supervised)
                cell_parents[stage] = (data,report,native); retained.append((data,report,summary))
                summary.update(mechanism_pass=True,task_pass=None,final_phase=report['final_phase'],
                    worker_report_sha256=common._hash(data['run']/'comparison-worker.json'),snapshot_sha256=entry['sha256'],
                    initial_non_u=branch_invariants(native,job),
                    files=[{'path':str(p.relative_to(data['run'])),'bytes':p.stat().st_size,'sha256':common._hash(p)} for p in data['paths']])
                if stage=='oracle':
                    comparison = evaluate_cell(binding,source,cell_parents,mapped)
                    result['comparisons'].append(comparison)
                    for row in comparison['runtime']:
                        next(s for s in summaries if s['cell']==key and s['stage']==row['condition'])['task_pass']=row['task_pass']
            result['status'] = 'comparison_checked'
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,TimeoutError) as error:
            result['first_failure'] = {'type':type(error).__name__,'message':str(error),
                'cell':None if current_job is None else admission.cell_key(current_job['cell']),
                'stage':None if current_job is None else current_job['stage'],
                'run_id':None if current_job is None else current_job['run_id'],
                'scope':'before-owner' if current_summary is None else 'attempted-owner'}
            if current_summary is not None:
                current_summary.update(mechanism_pass=False,failure=result['first_failure'])
        result['unattempted_stages'] = [{'cell':admission.cell_key(j['cell']),'stage':j['stage'],'run_id':j['run_id'],
            'status':'unattempted','reason':'first infrastructure/invariant failure; no retry'} for j in plan['jobs'][len(summaries):]]
        final = None; changed = False
        try:
            final = source_identity(plan['repo'],plan['assets'])
            for binding in plan['bindings'].values(): verify_binding(binding,protocol_sha256=plan['protocol_sha256'],admission_lineage=plan.get('admission_lineage'))
            common.load_histories(plan['history_root'])
            changed = any(artifacts._fingerprint(d['paths'])!=d['fingerprint'] or
                common._hash(r['snapshot_path'])!=r['snapshot_sha256'] or
                common._hash(d['run']/'comparison-worker.json')!=s['worker_report_sha256'] for d,r,s in retained)
        except (OSError,ValueError,KeyError,TypeError) as error:
            changed = True; result.setdefault('first_failure',{'type':type(error).__name__,'message':str(error)})
        result.update(source_identity=plan['source_identity'],final_source_identity=final,
            source_unchanged=final==plan['source_identity'],retained_unchanged=not changed,
            wall_seconds=time.monotonic()-started,storage_usage=storage.usage(),
            ownership_terminal='serialized bounded_process cleanup; independent outer PID/start survey still required')
        if changed or not result['source_unchanged']: result['status']='comparison_unverified'
        neural.write(output/'comparison-report.json',result,storage)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker'); parser.add_argument('--prepared-plan',type=Path)
    parser.add_argument('--prepared-plan-sha256'); parser.add_argument('--plan-only',action='store_true')
    parser.add_argument('--fixed-profile',choices=('c3','c4',*admission.REMAINING_NAMES))
    parser.add_argument('--admission-plan-sha256');parser.add_argument('--admission-report-sha256')
    for name in ('repo','assets','output','history-root','admission-plan','admission-report'):
        parser.add_argument('--'+name,type=Path)
    args = parser.parse_args()
    if args.worker is not None:
        if args.fixed_profile is not None or args.admission_plan_sha256 is not None or args.admission_report_sha256 is not None: parser.error('Worker profile comes only from its validated job')
        return worker(json.loads(args.worker))
    names = ('repo','assets','output','history_root','admission_plan','admission_report')
    if args.prepared_plan is not None:
        if args.plan_only or args.fixed_profile is not None or args.admission_plan_sha256 is not None or args.admission_report_sha256 is not None or any(getattr(args,k) is not None for k in names) or args.prepared_plan_sha256 is None:
            parser.error('Prepared execution requires only an immutable plan and its hash')
        plan = neural.read_prepared_plan(args.prepared_plan,args.prepared_plan_sha256)
    else:
        if args.prepared_plan_sha256 is not None or any(getattr(args,k) is None for k in names):
            parser.error('All six planning paths are required')
        digest=profile_digest(args.fixed_profile);lineage=None
        if remaining_profile(digest):
            if args.admission_plan_sha256 is None or args.admission_report_sha256 is None:
                parser.error('Remaining comparison requires separately frozen admission plan/report hashes')
            lineage={'version':1,'protocol_sha256':fixed_profile(digest)[1]['admission_protocol_sha256'],
                'plan_path':str(args.admission_plan),'plan_sha256':args.admission_plan_sha256,
                'report_path':str(args.admission_report),'report_sha256':args.admission_report_sha256}
        elif args.admission_plan_sha256 is not None or args.admission_report_sha256 is not None:
            parser.error('Historical profiles retain original admission hashes')
        plan = make_plan(*(getattr(args,k) for k in names),protocol_sha256=digest,admission_lineage=lineage)
    if args.plan_only:
        print(json.dumps(validate_plan(plan),indent=2,allow_nan=False)); return 0
    return 0 if run_verifier(plan)['status']=='comparison_checked' else 1


if __name__=='__main__':
    raise SystemExit(main())
