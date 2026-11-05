"""Fail-closed parent for the fixed engineering-only change-audit pilot.

Importing this stdlib-only module never imports a model or native runtime. The
CLI has no injected runner or alternate runtime. See pilot-parent-contract.md.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'src'))

from paper.studies.change_audit_v1 import pilot_worker as worker
from paper.studies.change_audit_v1.process import run_accounted

MiB = 1024**2
GAINS = (1., .5, .75, 1.25)
SCOPE = 'actual-cpu-flynn-navigation-engineering-pilot'
MAX_BYTES = 512*MiB
FREE_BYTES = 6*1024**3
LOG_BYTES = 256*1024
CONTROL_BYTES = 12*MiB
WORKER_HEADROOM = 16*MiB
WALL_SECONDS = 1800
JOB_SECONDS = 120
AUDIT_CPU_SECONDS = 3600
PROJECT_CPU_SECONDS = 24*3600
ADMIN_CPU_SECONDS = 15
ADMIN_WALL_SECONDS = 5
MAX_JSON_BYTES = 2*MiB


class PilotFailure(RuntimeError):
    """Admission stopped permanently; all already-created artifacts are retained."""


def _json(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: '+key)
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('Nonfinite JSON constant: '+value)


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Nonfinite JSON number')
    if isinstance(value, dict):
        for item in value.values(): _finite(item)
    elif isinstance(value, list):
        for item in value: _finite(item)
    return value


def _path(value):
    return worker._path(value)


def _read(path, expected=None, maximum=MAX_JSON_BYTES):
    path = worker._regular(_path(str(path)))
    with path.open('rb') as stream:
        payload = stream.read(maximum+1)
    if len(payload) > maximum:
        raise ValueError('Control JSON exceeds its declared byte cap')
    if expected is not None and hashlib.sha256(payload).hexdigest() != worker._hash(expected):
        raise ValueError('Externally pinned JSON checksum differs: '+str(path))
    return _finite(json.loads(payload, object_pairs_hook=_unique, parse_constant=_reject_constant))


def _number(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(name+' must be a known finite nonnegative number')
    return value


def _file(row):
    if type(row) is not dict or set(row) != {'path','size_bytes','sha256'}:
        raise ValueError('Malformed file descriptor')
    path = worker._regular(_path(row['path']))
    worker._hash(row['sha256'])
    if type(row['size_bytes']) is not int or row['size_bytes'] < 0:
        raise ValueError('Invalid file size')
    if path.stat().st_size != row['size_bytes'] or worker.file_sha256(path) != row['sha256']:
        raise ValueError('Pinned readonly file differs: '+str(path))


def _source_state(repo):
    """Production binding: exact HEAD and tracked cleanliness, no source refresh."""
    head = subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'], check=True,
                          capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],
                           check=True,capture_output=True,text=True).stdout
    return {'head':head,'tracked_clean':not dirty}


def _phase_cpu():
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime+own.ru_stime+children.ru_utime+children.ru_stime


def _load_admission(roster_path, roster_sha, projection_path, projection_sha, source_commit,
                    source_state):
    if type(source_commit) is not str or re.fullmatch('[0-9a-f]{40}',source_commit) is None:
        raise ValueError('Fixed full source commit required')
    roster = _read(roster_path, roster_sha)
    required = {'schema','repo_root','asset_root','prepared_graph_directory','source_commit','files','runtime_metadata'}
    if type(roster) is not dict or set(roster) != required or roster['schema'] != 'change-audit-input-roster-v1':
        raise ValueError('Malformed externally prepared input roster')
    if roster['source_commit'] != source_commit or type(roster['runtime_metadata']) is not dict or not roster['runtime_metadata']:
        raise ValueError('Source/model/dependency runtime identity is required')
    for key in ('repo_root','asset_root','prepared_graph_directory'): _path(roster[key])
    projection = _read(projection_path, projection_sha)
    required = {'schema','roots','reserved_seed_ids','source','scope','protected_catalogs_read'}
    if type(projection) is not dict or set(projection) != required or projection['schema'] != 'change-audit-pilot-namespace-projection-v1':
        raise ValueError('Malformed externally reviewed namespace projection')
    if projection['scope'] != 'approved-public-cohort-ids-only' or projection['protected_catalogs_read'] is not False:
        raise ValueError('Only independently prepared public ID projections are admitted')
    _file(projection['source'])
    reserved = projection['reserved_seed_ids']
    if type(reserved) is not list or len(reserved)>10000 or any(type(v) is not int or not 0 <= v < 2**31 for v in reserved) or len(set(reserved)) != len(reserved):
        raise ValueError('Invalid bounded reserved seed projection')
    roots = projection['roots']
    if type(roots) is not list or len(roots) != 4:
        raise ValueError('Exactly four frozen roots required')
    configs = []
    for root in roots:
        if type(root) is not dict or set(root) != {'root_id','scenario','texture','seed'}:
            raise ValueError('Malformed frozen root')
        config = {**root, **{key:roster[key] for key in ('repo_root','asset_root','prepared_graph_directory')},
                  'ticks':64,'check_parity':False,'device':'cpu','controller':'flynn','input_files':roster['files']}
        configs.append(worker.validate_config(config))
    if len({c['root_id'] for c in configs}) != 4 or len({c['seed'] for c in configs}) != 4:
        raise ValueError('Root IDs and seeds must each be distinct')
    if set(reserved) & {c['seed'] for c in configs}:
        raise ValueError('Reserved seed intersection')
    # The complete independently supplied roster includes the namespace source.
    if projection['source'] not in roster['files']:
        raise ValueError('Public namespace source absent from the input roster')
    state = source_state(roster['repo_root'])
    if state != {'head':source_commit,'tracked_clean':True}:
        raise ValueError('Actual tracked source is dirty or differs from pinned HEAD')
    for row in roster['files']: _file(row)
    return roster, projection, configs


def _descriptor(value, output):
    if type(value) is not dict or set(value) != {'path','file_sha256','state_sha256'}:
        raise PilotFailure('Malformed worker snapshot descriptor')
    worker._hash(value['file_sha256']); worker._hash(value['state_sha256'])
    path = worker._regular(_path(value['path']))
    if not path.is_relative_to(output) or path.stat().st_size > worker.SNAPSHOT_BYTES:
        raise PilotFailure('Snapshot escaped its admitted directory or cap')
    if worker.file_sha256(path) != value['file_sha256']:
        raise PilotFailure('Snapshot file checksum differs')
    return value


def _accept(report, job, output, anchor=None):
    exact = {'schema':'change-audit-pilot-worker-v1','status':'completed','actual_scope':SCOPE,
             'mode':job['mode'],'root_id':job['root_id'],'gain':job['gain'],'check_parity':False,
             'sampling_eligibility_verified':False,'certified_improvement':False,'runtime_qualification':False}
    for key, value in exact.items():
        if type(report.get(key)) is not type(value) or report[key] != value:
            raise PilotFailure('Worker stage-report identity/status mismatch: '+key)
    if report.get('errors') != []:
        raise PilotFailure('Worker retained an error, including close/input errors')
    ticks, forwards = report.get('ticks'), report.get('forward_attempts')
    if type(ticks) is not int or type(forwards) is not int or not 0 <= ticks <= 64 or ticks != forwards:
        raise PilotFailure('Worker forward/tick accounting differs')
    if job['mode'] == 'prepare-anchor':
        if ticks or forwards or report.get('stop_reason') != 'paused_anchor_prepared':
            raise PilotFailure('Preparation performed a policy forward or tick')
        return _descriptor(report.get('anchor'), output)
    if report.get('anchor') != anchor or report.get('before_first_tick_equal') is not True:
        raise PilotFailure('Original anchor or before-first-tick equality differs')
    expected, observed = report.get('before_first_tick_expected_sha256'), report.get('before_first_tick_observed_sha256')
    worker._hash(expected); worker._hash(observed)
    if expected != observed:
        raise PilotFailure('Before-first-tick state checksums differ')
    if type(report.get('completed_requested_ticks')) is not bool or report['completed_requested_ticks'] != (ticks == 64):
        raise PilotFailure('Requested tick completion is inconsistent')
    reason = report.get('stop_reason')
    if reason == 'tick_limit':
        if ticks != 64: raise PilotFailure('Tick-limit condition has an incomplete prefix')
    elif reason == 'natural_terminal':
        if ticks < 1 or not isinstance(report.get('terminal_outcome'),dict):
            raise PilotFailure('Natural termination lacks its observed prefix/outcome')
    else:
        raise PilotFailure('Unregistered condition stop reason')
    if job['gain'] == 1.:
        if report.get('snapshot') != anchor: raise PilotFailure('Baseline did not reuse original snapshot')
    else:
        _descriptor(report.get('snapshot'), output)
    _read(output/'derivation-receipt.json', maximum=128*1024)
    return None


def _plan(roster, projection, configs, source_commit, roster_path, roster_sha, projection_path, projection_sha):
    return {'schema':'change-audit-pilot-parent-v1','engineering_only':True,
        'sampling_eligibility_verified':False,'certified_improvement':False,'runtime_qualification':False,
        'source_commit':source_commit,'input_roster':{'path':str(roster_path),'sha256':roster_sha},
        'namespace_projection':{'path':str(projection_path),'sha256':projection_sha},
        'namespace_scope':projection['scope'],'namespace_limitations':'ID/seed projection only; no geometry, pretraining, or sampling-disjointness claim',
        'runtime_metadata':roster['runtime_metadata'],'roots':[c['root_id'] for c in configs],
        'gains':list(GAINS),'ticks':64,'check_parity':False,'device':'cpu','controller':'flynn',
        'limits':{'retained_bytes':MAX_BYTES,'min_free_bytes':FREE_BYTES,'wall_seconds':WALL_SECONDS,
            'job_wall_seconds':JOB_SECONDS,'audit_cpu_seconds':AUDIT_CPU_SECONDS,'project_cpu_seconds':PROJECT_CPU_SECONDS,
            'log_bytes_per_stream':LOG_BYTES,'control_bytes':CONTROL_BYTES,'worker_concurrent_headroom_bytes':WORKER_HEADROOM,
            'four_preparations_worst_case_bytes':4*(worker.RECORDING_BYTES+worker.SNAPSHOT_BYTES)+8*LOG_BYTES+CONTROL_BYTES+WORKER_HEADROOM},
        'conditions':[{'index':i*4+j,'root_id':c['root_id'],'mode':'execute-condition','gain':gain}
                      for i,c in enumerate(configs) for j,gain in enumerate(GAINS)]}


def _terminal_accounting(output, *, budget, accounting_complete, status, cpu_seconds, elapsed_seconds,
                         project_prior, audit_prior):
    """Last bounded receipt under the lease; its own write remains explicit."""
    _number(cpu_seconds,'terminal observed CPU'); _number(elapsed_seconds,'terminal elapsed wall')
    if cpu_seconds+audit_prior > AUDIT_CPU_SECONDS or cpu_seconds+project_prior > PROJECT_CPU_SECONDS or elapsed_seconds > WALL_SECONDS:
        status = 'stopped'
    value = {'schema':'change-audit-pilot-terminal-accounting-v1','status':status,
        'accounting_complete':accounting_complete,'phase_cpu_seconds':cpu_seconds if accounting_complete else None,
        'phase_cpu_seconds_observed':cpu_seconds,'wall_seconds':elapsed_seconds,
        'prior_project_cpu_seconds':project_prior,'prior_audit_cpu_seconds':audit_prior,
        'measurement_scope':'SELF+reaped CHILDREN through prior report publication, before terminal publication and lease release',
        'unmetered_tail':'Terminal receipt serialization/write/fsync, lease release and process return remain. The outer trusted lifetime supervisor must reconcile this tail; no exact process-lifetime total claimed.',
        'scientific_claim':False}
    payload = _json(value)
    if len(payload)>64*1024: raise PilotFailure('Terminal accounting receipt exceeds pre-admitted cap')
    budget.check(len(payload),path=output/'terminal-accounting.json')
    with (output/'terminal-accounting.json').open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    return value


def _make_budget(root):
    from palimpsest.storage import StorageBudget, StorageLimits
    return StorageBudget([root],StorageLimits(max_bytes=MAX_BYTES,min_free_bytes=FREE_BYTES))


def _run(*, mode, roster_path, roster_sha, projection_path, projection_sha, source_commit, output,
         project_cpu_used=None, audit_cpu_used=None, _runner=run_accounted,
         _source_state_getter=_source_state, _clock=time.monotonic, _cpu=_phase_cpu, _budget_factory=None):
    """Private test seams never exposed by CLI; no fixture/native alternate mode."""
    started, cpu_started = _clock(), _cpu()
    if mode not in ('plan-only','execute'): raise ValueError('Unknown parent mode')
    output = _path(str(output))
    if output.exists(): raise PilotFailure('Existing pilot output is forbidden')
    if any(path.is_symlink() for path in (output,*output.parents)):
        raise PilotFailure('Output cannot traverse symlinks')
    if mode == 'execute':
        _number(project_cpu_used,'project CPU already used'); _number(audit_cpu_used,'audit CPU already used')
        if audit_cpu_used > project_cpu_used:
            raise ValueError('Audit CPU usage cannot exceed aggregate project usage')
    try:
        roster, projection, configs = _load_admission(roster_path,roster_sha,projection_path,projection_sha,
                                                     source_commit,_source_state_getter)
        source_root = Path(roster['repo_root'])
        # Production must execute the very source tree whose HEAD is pinned.
        if _source_state_getter is _source_state and source_root != Path(__file__).resolve().parents[3]:
            raise ValueError('Pinned repo root differs from the executing supervisor source')
        plan = _plan(roster,projection,configs,source_commit,roster_path,roster_sha,projection_path,projection_sha)
        if mode == 'execute':
            input_paths = [Path(row['path']) for row in roster['files']] + [Path(roster_path),Path(projection_path)]
            if any(path.is_relative_to(output) for path in input_paths):
                raise ValueError('Readonly input cannot live within the writer root')
    except BaseException as exc:
        if mode == 'execute':
            # Preflight hashing/source failures are also research preparation CPU.
            # No worker has started, so SELF+reaped CHILDREN is complete here.
            output.mkdir(parents=False,exist_ok=False)
            failed_budget = (_budget_factory or _make_budget)(output)
            with failed_budget.lock():
                payload = _json({'schema':'change-audit-pilot-admission-failure-v1','status':'stopped',
                    'worker_invocations':0,'accounting_complete':True,'phase_cpu_seconds':_cpu()-cpu_started,
                    'wall_seconds':_clock()-started,'prior_project_cpu_seconds':project_cpu_used,
                    'prior_audit_cpu_seconds':audit_cpu_used,'error':{'type':type(exc).__name__,'message':str(exc)[:2048]}})
                failed_budget.check(len(payload)+64*1024,path=output/'admission-failure.json')
                with (output/'admission-failure.json').open('xb') as stream:
                    stream.write(payload); stream.flush(); os.fsync(stream.fileno())
                _terminal_accounting(output,budget=failed_budget,accounting_complete=True,status='stopped',cpu_seconds=_cpu()-cpu_started,
                    elapsed_seconds=_clock()-started,project_prior=project_cpu_used,audit_prior=audit_cpu_used)
        raise
    if mode == 'plan-only':
        return {**plan,'status':'plan-only','worker_invocations':0,'output_created':False}
    if _budget_factory is None:
        _budget_factory = _make_budget
    output.mkdir(parents=False,exist_ok=False)
    budget = _budget_factory(output)
    jobs = []
    report = {**plan,'status':'running','jobs':jobs,'accounting_complete':True,
              'phase_cpu_seconds':None,'phase_cpu_measurement_scope':'through report preparation; terminal-accounting.json extends measurement',
              'prior_project_cpu_seconds':project_cpu_used,'prior_audit_cpu_seconds':audit_cpu_used,
              'errors':[],'wall_seconds':None}
    event_count = 0
    def charge():
        delta = _cpu()-cpu_started
        if not math.isfinite(delta) or delta < 0: raise PilotFailure('Invalid whole-phase CPU meter')
        return delta
    def write(path, value, maximum=MAX_JSON_BYTES):
        payload = _json(value)
        if len(payload)>maximum: raise PilotFailure('Control artifact exceeds its fixed cap')
        budget.check(len(payload),path=path)
        with path.open('xb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    def event(value):
        nonlocal event_count
        event_count += 1
        if event_count>64: raise PilotFailure('Ledger event-count cap reached')
        write(output/f'ledger-{event_count:03d}.json',value,8*1024)
    def recheck():
        _load_admission(roster_path,roster_sha,projection_path,projection_sha,source_commit,_source_state_getter)
        for c in configs:
            path = output/'configs'/(c['root_id']+'.json')
            if path.exists() and _read(path,config_hashes[c['root_id']]) != c:
                raise PilotFailure('Frozen worker configuration changed')
    config_hashes = {}
    anchors = {}
    anchor_hashes = {}
    lease = budget.lock()
    lease.__enter__()
    try:
        # Predeclared control allocation includes bounded report/receipt/ledger counts.
        base_bytes = sum(len(_json(c)) for c in configs)+len(_json(plan))+len(_json(roster))+len(_json(projection))
        if base_bytes > 4*MiB: raise PilotFailure('Frozen configuration exceeds control allocation')
        # Admit the entire four-preparation block before any worker starts.
        preparation_block = 4*(worker.RECORDING_BYTES+worker.SNAPSHOT_BYTES)+8*LOG_BYTES+CONTROL_BYTES+WORKER_HEADROOM
        budget.check(preparation_block,path=output)
        (output/'configs').mkdir(); (output/'jobs').mkdir(); (output/'anchors').mkdir()
        write(output/'admission-manifest.json',plan)
        write(output/'input-roster.json',roster); write(output/'namespace-projection.json',projection)
        for config in configs:
            config_hashes[config['root_id']] = hashlib.sha256(_json(config)).hexdigest()
            write(output/'configs'/(config['root_id']+'.json'),config)
        def admit(job):
            if report['accounting_complete'] is not True:
                raise PilotFailure('Incomplete accounting forbids further admission')
            used, elapsed = charge(), _clock()-started
            cpu_remaining = min(AUDIT_CPU_SECONDS-audit_cpu_used-used,PROJECT_CPU_SECONDS-project_cpu_used-used)
            if cpu_remaining < JOB_SECONDS+ADMIN_CPU_SECONDS:
                raise PilotFailure('Insufficient remaining audit/project CPU for next fixed job plus administration')
            if WALL_SECONDS-elapsed < JOB_SECONDS+ADMIN_WALL_SECONDS:
                raise PilotFailure('Insufficient remaining whole-pilot wall for next fixed job plus cleanup')
            # Reserve each next job's full per-file payload plus the worker CLI's
            # unused 16MiB safety margin, independently of retained log/control.
            derived = 0 if job['mode']=='execute-condition' and job['gain']==1. else worker.SNAPSHOT_BYTES
            budget.check(worker.RECORDING_BYTES+derived+2*LOG_BYTES+CONTROL_BYTES+WORKER_HEADROOM,path=output)
            return JOB_SECONDS, JOB_SECONDS
        def launch(job, config, anchor=None):
            wall, cpu_limit = admit(job)
            recheck()
            if anchor is not None: _descriptor(anchor,output/'jobs')
            index = len(jobs)
            jobdir = output/'jobs'/f'{index:02d}-{job["root_id"]}-{job["mode"]}'
            jobdir.mkdir(exist_ok=False)
            artifact = jobdir/'artifacts'  # Worker creates this exclusively.
            row = {**job,'status':'running','attempt':1,'output':str(artifact),'accounting':None}
            jobs.append(row)
            event({'kind':'job-running','job':row,'phase_cpu_seconds':charge()})
            config_path = output/'configs'/(config['root_id']+'.json')
            command = [str(Path(sys.executable).resolve()),'-B',str(source_root/'paper/studies/change_audit_v1/pilot_worker.py'),
                '--mode',job['mode'],'--config',str(config_path),'--expected-config-sha256',config_hashes[config['root_id']],
                '--output',str(artifact),'--pilot-root',str(output)]
            if anchor is not None:
                command += ['--anchor',str(output/'anchors'/(job['root_id']+'.json')),'--expected-anchor-sha256',anchor_hashes[job['root_id']],'--gain',str(job['gain'])]
            environment = dict(os.environ)
            environment.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(jobdir/'unused-pycache'),
                MPLBACKEND='Agg',MPLCONFIGDIR=str(jobdir/'matplotlib-cache'),CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',
                PYTHONPATH=str(source_root/'src')+os.pathsep+str(source_root))
            # This callback executes in the forked supervisor. It has no
            # parent-state mutations and performs one bounded storage scan.
            def monitor(_sample):
                budget.check(WORKER_HEADROOM,path=output)
                return None
            try:
                accounting = _runner(command,cwd=str(source_root),env=environment,
                    stdout_path=jobdir/'stdout.log',stderr_path=jobdir/'stderr.log',
                    wall_seconds=wall,cpu_seconds=cpu_limit,max_log_bytes=LOG_BYTES,monitor=monitor)
            except BaseException:
                report['accounting_complete'] = False
                row['status'] = 'accounting-unknown'
                event({'kind':'job-accounting-unknown','job':row,'phase_cpu_seconds_observed':charge()})
                raise
            try:
                if type(accounting) is not dict: raise ValueError('Non-object accounting')
                _finite(accounting)
            except (ValueError,TypeError):
                accounting = {'status':'malformed-accounting','accounting_complete':False,
                    'tree_drained':False,'subtree_cpu_seconds':None,'parent_cpu_seconds':None}
            row['accounting'] = accounting
            complete = accounting.get('accounting_complete') is True and accounting.get('tree_drained') is True
            if complete:
                try:
                    _number(accounting.get('subtree_cpu_seconds'),'subtree CPU')
                    _number(accounting.get('parent_cpu_seconds'),'parent CPU')
                except ValueError: complete = False
            if not complete:
                report['accounting_complete'] = False
                row['status'] = 'accounting-unknown'
            else:
                row['status'] = 'accounted'
            event({'kind':'job-accounted','job':row,'phase_cpu_seconds_observed':charge()})
            if not complete: raise PilotFailure('Unknown CPU or undrained process tree; no further worker may start')
            if accounting.get('status')!='completed' or type(accounting.get('returncode')) is not int or accounting['returncode'] != 0 or accounting.get('errors',[]) != []:
                raise PilotFailure('Worker process failed or resource gate stopped it')
            stage = _read(artifact/'stage-report.json',maximum=128*1024)
            result = _accept(stage,job,artifact,anchor)
            recheck()
            if anchor is not None: _descriptor(anchor,output/'jobs')
            if charge()+audit_cpu_used > AUDIT_CPU_SECONDS or charge()+project_cpu_used > PROJECT_CPU_SECONDS or _clock()-started > WALL_SECONDS:
                raise PilotFailure('Whole-phase resource ceiling exceeded')
            budget.check(WORKER_HEADROOM,path=output)
            row['status'] = 'accepted'
            event({'kind':'job-accepted','job_index':index,'phase_cpu_seconds':charge()})
            return result
        for config in configs:
            job = {'mode':'prepare-anchor','root_id':config['root_id'],'gain':1.}
            anchors[config['root_id']] = launch(job,config)
        # Preparation bytes are now measured. Admit the ENTIRE immutable
        # block before any inference; a large preparation refuses this gate.
        future = 16*worker.RECORDING_BYTES+12*worker.SNAPSHOT_BYTES+32*LOG_BYTES+CONTROL_BYTES+WORKER_HEADROOM
        budget.check(future,path=output)
        recheck()
        for root_id, anchor in anchors.items():
            _descriptor(anchor,output/'jobs')
            write(output/'anchors'/(root_id+'.json'),anchor)
            anchor_hashes[root_id] = worker.file_sha256(output/'anchors'/(root_id+'.json'))
        frozen = {**plan,'anchors':anchors,'condition_count':16,'config_sha256':config_hashes,'anchor_descriptor_sha256':anchor_hashes,
                  'condition_block_reserved_bytes':future,'preparation_used_bytes':budget.usage()['used_bytes']}
        write(output/'condition-manifest.json',frozen,256*1024)
        manifest_sha = worker.file_sha256(output/'condition-manifest.json')
        event({'kind':'all-anchors-and-16-conditions-frozen','manifest_sha256':manifest_sha,'phase_cpu_seconds':charge()})
        by_id = {c['root_id']:c for c in configs}
        for job in plan['conditions']:
            if worker.file_sha256(output/'condition-manifest.json') != manifest_sha:
                raise PilotFailure('Frozen condition manifest changed')
            for root_id, anchor in anchors.items():
                if _read(output/'anchors'/(root_id+'.json'),anchor_hashes[root_id]) != anchor: raise PilotFailure('Frozen anchor descriptor changed')
                _descriptor(anchor,output/'jobs')
            launch(job,by_id[job['root_id']],anchors[job['root_id']])
        recheck()
        report['status'] = 'completed'
    except BaseException as exc:
        report['status'] = 'stopped'
        report['errors'].append({'type':type(exc).__name__,'message':str(exc)[:2048]})
    finally:
        report['phase_cpu_seconds_observed'] = charge()
        report['phase_cpu_seconds'] = report['phase_cpu_seconds_observed'] if report['accounting_complete'] else None
        report['wall_seconds'] = _clock()-started
        # Each result is exclusive. A failed final publication propagates and
        # leaves the running/incomplete ledger as the conservative durable state.
        try:
            # Pre-admit the bounded terminal receipt while holding the lease.
            budget.check(64*1024,path=output/'terminal-accounting.json')
            write(output/'parent-report.json',report,256*1024)
            terminal = _terminal_accounting(output,budget=budget,accounting_complete=report['accounting_complete'],
                status=report['status'],cpu_seconds=charge(),elapsed_seconds=_clock()-started,
                project_prior=project_cpu_used,audit_prior=audit_cpu_used)
            report['terminal_accounting'] = terminal
            report['status'] = terminal['status']
        finally:
            lease.__exit__(None,None,None)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=('plan-only','execute'))
    parser.add_argument('--input-roster',required=True); parser.add_argument('--expected-input-roster-sha256',required=True)
    parser.add_argument('--namespace-projection',required=True); parser.add_argument('--expected-namespace-projection-sha256',required=True)
    parser.add_argument('--source-commit',required=True); parser.add_argument('--output',required=True)
    parser.add_argument('--project-cpu-used-seconds',type=float); parser.add_argument('--audit-cpu-used-seconds',type=float)
    args = parser.parse_args(argv)
    result = _run(mode=args.mode,roster_path=args.input_roster,roster_sha=args.expected_input_roster_sha256,
        projection_path=args.namespace_projection,projection_sha=args.expected_namespace_projection_sha256,
        source_commit=args.source_commit,output=args.output,project_cpu_used=args.project_cpu_used_seconds,
        audit_cpu_used=args.audit_cpu_used_seconds)
    print(_json(result).decode(),end='')
    return 0 if result['status'] in ('completed','plan-only') else 1


if __name__ == '__main__':
    # Absolute script execution must still resolve the repository-owned package.
    raise SystemExit(main())
