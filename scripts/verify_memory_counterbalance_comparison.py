"""Fixed four-cell Stage C DEVELOPMENT comparison; no execution without a GO."""
import copy
import importlib.util
from pathlib import Path

from palimpsest import artifacts, memory, memory_task
from palimpsest.replay import _initial_snapshot
from palimpsest.snapshots import read_snapshot
from palimpsest.storage import MiB

HELPER = Path(__file__).with_name('verify_memory_counterbalance.py')
spec = importlib.util.spec_from_file_location('counterbalance_admission_helpers', HELPER)
admission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admission)
neural, common = admission.neural, admission.common
CELLS = ((24, 'local_cue', 'change'), (29, 'paired_cue', 'change'),
         (30, 'local_cue', 'null'), (27, 'paired_cue', 'no-event'))
B_PLAN_SHA256 = 'ecaedc5c9341063eaa619635da69bda2149dd66e46ed1d01a7ffe13834515131'
B_REPORT_SHA256 = '2eaba8d84f4d206c0f415362088ba7cec3139b77e10829b6cdc84b055624ea1f'


def pinned_json(path, digest, maximum=MiB):
    path = artifacts._safe_path(path)
    if common._hash(path) != digest:
        raise ValueError('Retained admission input hash differs')
    result = artifacts._json(artifacts._read(path, maximum))
    if common._hash(path) != digest:
        raise ValueError('Retained admission input changed while reading')
    return result


def derive_anchor(plan, terminal, cell):
    """Join the declared owner to its completed report; never choose by UUID alone."""
    key = admission.cell_key(cell)
    if tuple(cell) not in CELLS or terminal.get('status') != 'admission_checked' or not all(
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


def load_bindings(plan_path, report_path):
    """Validate all three original owners per cell, retaining their actual provenance."""
    plan = admission.validate_plan(pinned_json(plan_path, B_PLAN_SHA256))
    terminal = pinned_json(report_path, B_REPORT_SHA256)
    result = {}
    for cell in CELLS:
        lineage = derive_anchor(plan, terminal, cell)
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
            'plan_path': str(Path(plan_path).resolve()), 'plan_sha256': B_PLAN_SHA256,
            'report_path': str(Path(report_path).resolve()), 'report_sha256': B_REPORT_SHA256}
    return result


def verify_binding(binding):
    """Reconcile a supplied binding with pinned plan/report before native restoration."""
    plan = admission.validate_plan(pinned_json(binding['plan_path'], B_PLAN_SHA256))
    terminal = pinned_json(binding['report_path'], B_REPORT_SHA256)
    joined = derive_anchor(plan, terminal, binding['cell'])
    job, row = joined['policy-anchor']
    if (binding['run_id'] != job['run_id'] or binding['case'] != job['case']
            or binding['snapshot_path'] != str(Path(job['output']) / 'snapshots/initial.snp')
            or binding['snapshot_sha256'] != row['snapshot_sha256'] or binding['non_u'] != row['initial_non_u']
            or binding['plan_sha256'] != B_PLAN_SHA256 or binding['report_sha256'] != B_REPORT_SHA256):
        raise ValueError('Policy binding was replaced by another owner/case/native state')
    for pin in binding['pins']:
        if common._hash(pin['path']) != pin['sha256']:
            raise ValueError('Original admission artifact changed')
    data = common.read_run(Path(job['output']))
    native, entry, _ = _initial_snapshot(data)
    policy_boundary(data, native, job['case'])
    if common._hash(binding['snapshot_path']) != row['snapshot_sha256'] or entry['sha256'] != row['snapshot_sha256']:
        raise ValueError('Registered admission snapshot differs')
    return native
