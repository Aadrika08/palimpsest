"""Explicit admission and bounded publication for the approved selected pilot."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import signal
import sys
import time
import uuid

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from scripts import memory_prerequisites_v2 as m, memory_restore_offline_readout as o

PREREQUISITE_REGISTRATION_SHA256 = '8567bc446b265c36a3063dc5d3fcb2cf354bcd2a3684ec4a068e6c98007f12f9'
PREREQUISITE_CLOSE_SHA256 = '6e33c0c5fd0ec6a407588e6d7f7240f79964706e5cdd638a351bbe5a0b433b76'
PREREQUISITE_INDEX_SHA256 = 'b9e571a8fff0d9c1bc0a2d10b47355ad9cff96fc0e056d5f994789a95748e3a3'
MODE = 'decision-pilot-v2'


def check_file(path, digest, size=None, deadline=None):
    p.deadline_check(deadline)
    path = p.checked_path(path)
    if (not path.is_file() or (size is not None and path.stat().st_size != size)
            or p.file_hash(path) != digest):
        raise ValueError('Immutable input bytes differ: '+str(path))
    p.deadline_check(deadline)


def admit_prerequisites(path, repo, deadline=None):
    """Consume the pinned old close as bytes/metadata, never regrade old physics."""
    path, repo = p.checked_path(path), p.checked_path(repo)
    check_file(path, PREREQUISITE_REGISTRATION_SHA256, deadline=deadline)
    reg = p.read_json(path); m.validate_registration(reg)
    root, pub, control = (p.checked_path(reg[k]) for k in ('output','publication_root','control_root'))
    if reg['mode'] != 'prerequisites-v3' or path != pub/'registration.json':
        raise ValueError('Only the pinned original v3 prerequisite is admitted')
    close_path = root/'scientific-close.json'
    check_file(close_path, PREREQUISITE_CLOSE_SHA256, deadline=deadline)
    close, execution = p.read_json(close_path), p.read_json(root/'execution.json')
    check_file(root/'execution.json', close['driver_execution_sha256'], deadline=deadline)
    required = {'native_prerequisites_passed':True,'candidate_restore_pair_matches':True,
                'trace_equal':True,'immutable_inputs_and_raw_evidence_unchanged':True,
                'restore_pair_matches':False,'r2_complete':False,'held_out_used':False}
    if (close.get('schema') != 'memory-prerequisites-scientific-close-v3'
            or close.get('status') != 'native-prerequisites-passed'
            or any(close.get(k) is not v for k,v in required.items())
            or close.get('qualification_claims') != []
            or close.get('paired_pilot') != 'unattempted-by-scope'
            or close.get('registration_sha256') != PREREQUISITE_REGISTRATION_SHA256
            or close.get('state_contract') != d.STATE_CONTRACT
            or execution.get('status') != 'prerequisites-provisional-pass'
            or execution.get('native_prerequisites_passed') is not False
            or execution.get('unattempted')):
        raise ValueError('Pinned prerequisite authority or scope differs')
    candidate = close['candidate_comparison']; intervals = candidate['timer_duration_intervals']
    if (candidate.get('equal') is not True or candidate.get('contract_id') != d.STATE_CONTRACT
            or candidate.get('excluded_native_bytes_per_side') != 120 or len(intervals) != 15
            or any(type(a) is not int or type(b) is not int or b-a != 8 for a,b in intervals)
            or any(b > c for (_,b),(c,_) in zip(intervals,intervals[1:]))
            or candidate.get('differences') != [] or close['comparison'].get('equal') is not False):
        raise ValueError('Frozen candidate/legacy comparison differs')
    attempts = execution['attempted']; owners = close['owners']; cleanup = execution['cleanup']
    ids = [a['run_id'] for a in attempts]
    if (len(attempts) != 8 or len(set(ids)) != 8 or
            [a['job_id'] for a in attempts] != [s['id'] for s in reg['expected_specs']]
            or len(owners) != 8 or {r['run_id'] for r in owners} != set(ids)
            or len(cleanup) != 8 or {r['owner']['run_id'] for r in cleanup} != set(ids)
            or any(r.get('raw_audit_pass') is not True or r.get('matching_owner_exited') is not True
                   or r.get('disposition') != 'audited-recording' for r in owners)
            or any(not m.cell_pass(spec,a) for spec,a in zip(reg['expected_specs'][:6],attempts[:6]))
            or any(a.get('raw_audit_pass') is not True or a.get('invariants_preserved') is not True
                   or a.get('continuation_ticks') != 5 for a in attempts[-2:])):
        raise ValueError('Complete eight-cell prerequisite binding is required')
    by_run = {r['run_id']:r for r in owners}
    for item in cleanup:
        if (item['owner'] != by_run[item['owner']['run_id']]['owner']
                or item['status'] not in ('already-exited','pid-reused-do-not-touch')
                or not d.owner_exited(item['owner'])):
            raise ValueError('Original prerequisite owner exit proof differs')
    marker = p.read_json(control/'launched.json'); origin = marker['started_monotonic']
    readout = execution['readout_started_monotonic']
    end = min(origin+4900,readout+600)
    times = (origin,readout,close['closed_monotonic'],close['readout_deadline_monotonic'])
    if (any(type(x) not in (int,float) or not math.isfinite(x) for x in times)
            or execution['started_monotonic'] != origin
            or execution['owner_deadline_monotonic'] != origin+4300
            or execution['global_deadline_monotonic'] != origin+4900
            or close['readout_deadline_monotonic'] != end
            or not origin <= readout <= close['closed_monotonic'] <= end
            or marker['registration_sha256'] != PREREQUISITE_REGISTRATION_SHA256):
        raise ValueError('Original prerequisite clock differs')
    check_file(control/'launched.json', execution['launcher_marker_sha256'], deadline=deadline)
    for name in ('driver','auditor','comparator','launcher','shared_launcher',
                 'registration_preparer','campaign_launcher','shared_preparer'):
        check_file(reg[name+'_path'], reg[name+'_sha256'], deadline=deadline)
    check_file(reg['contract'], reg['contract_sha256'], deadline=deadline)
    check_file(Path(reg['repo'])/'scripts/memory_restore_diagnostic.py',
               reg['diagnostic_driver_sha256'],deadline=deadline)
    check_file(Path(reg['repo'])/'scripts/memory_decision_pilot.py',
               reg['source_identity']['pilot_driver_sha256'],deadline=deadline)
    inventory = execution['artifact_index']+[
        {'path':'execution.json','bytes':(root/'execution.json').stat().st_size,
         'sha256':close['driver_execution_sha256']},
        {'path':'scientific-close.json','bytes':close_path.stat().st_size,
         'sha256':PREREQUISITE_CLOSE_SHA256}]
    o.verify_inventory({'root':str(root),'files':inventory},deadline)
    for reference in reg['preserved_sets']: o.verify_inventory(reference,deadline)
    index_path = pub/'publication-index.json'
    check_file(index_path,PREREQUISITE_INDEX_SHA256,deadline=deadline)
    for row in p.read_json(index_path)['files']:
        source = p.checked_path(row['source'])
        if not any(source.is_relative_to(r) for r in (root,pub,control)):
            raise ValueError('Prerequisite byte index escapes its frozen roots')
        check_file(source,row['sha256'],row['bytes'],deadline)
    source = close['fresh_source']
    if (source != p.read_json(root/'fresh-source.json') or source['source_job_id'] != 'south-prefix'
            or source['run_id'] != attempts[4]['run_id'] or
            len(source['source_receipt_ids']) != 727 or len(set(source['source_receipt_ids'])) != 727
            or any(by_run[a['run_id']]['audit'].get('repeat_source_receipt_ids') != source['source_receipt_ids']
                   for a in attempts[-2:])):
        raise ValueError('Fresh prerequisite source binding differs')
    check_file(source['snapshot_path'],source['snapshot_sha256'],source['bytes'],deadline)
    current = p.source_identity(repo,reg['assets']); previous = reg['source_identity']
    if ({k:v for k,v in current.items() if k != 'pilot_driver_sha256'} !=
            {k:v for k,v in previous.items() if k != 'pilot_driver_sha256'}):
        raise ValueError('Scientific source/assets differ; only explicit pilot worker derivation is allowed')
    return {'registration_path':str(path),'registration_sha256':PREREQUISITE_REGISTRATION_SHA256,
            'close_path':str(close_path),'close_sha256':PREREQUISITE_CLOSE_SHA256,
            'index_path':str(index_path),'index_sha256':PREREQUISITE_INDEX_SHA256,
            'old_worker_sha256':previous['pilot_driver_sha256'],
            'new_worker_sha256':current['pilot_driver_sha256']}


def retain_report(root, report, storage):
    """Full audit stays bounded in its own file; all thirty summaries fit the close."""
    path = p.checked_path(root)/'inline-audits'/(report['run_id']+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    p.write_control(path,report,storage)
    compact = {k:v for k,v in report.items() if k not in
               ('final_memory','world_state','commitment_inputs','failed_worker_report')}
    return {**compact,'audit_path':str(path),'audit_sha256':p.file_hash(path)}


def dependencies(repo):
    repo = p.checked_path(repo); pub = repo/'docs/reports/memory-decision-pilot-v2-evidence'
    return {'driver':repo/'scripts/memory_selected_pilot.py',
        'auditor':repo/'scripts/memory_selected_pilot.py',
        'native_worker':repo/'scripts/memory_decision_pilot.py',
        'prerequisite_helper':repo/'scripts/memory_prerequisites_v2.py',
        'inventory_helper':repo/'scripts/memory_restore_offline_readout.py',
        'launcher':pub/'execute-pilot.py','registration_preparer':pub/'register.py',
        'shared_launcher':repo/'docs/reports/restore-qualification-v2-evidence/execute-restore-v2.py',
        'byte_projection':repo/'docs/reports/memory-decision-pilot-v2-software-evidence/resource-preflight.json'}


def build_registration(repo, prerequisite_path, *, stamp, deadline=None):
    repo = p.checked_path(repo); reference = admit_prerequisites(prerequisite_path,repo,deadline)
    baseline = p.read_json(prerequisite_path)
    check_file(repo/'scripts/memory_restore_diagnostic.py',baseline['diagnostic_driver_sha256'],deadline=deadline)
    check_file(repo/'scripts/memory_prerequisites_v2.py',baseline['driver_sha256'],deadline=deadline)
    check_file(repo/'scripts/memory_restore_offline_readout.py',baseline['comparator_sha256'],deadline=deadline)
    if sys.executable != baseline['python'] or d.runtime_v2_identity() != baseline['runtime']:
        raise ValueError('Pilot must use the exact admitted prerequisite runtime and executable')
    preserved = baseline['preserved_sets']+[
        {'root':baseline[k],'files':p.hash_ledger(baseline[k],deadline)}
        for k in ('output','control_root','publication_root')]
    specs = p.selected_pilot_specs()
    from palimpsest import memory_decision_world as world
    slots = [{'job_id':spec['id']+('/'+condition if condition else ''),
              'operation':'condition' if condition else 'prefix','condition':condition,
              'run_id':uuid.uuid4().hex}
             for spec in specs for condition in (None,*p.CONDITIONS)]
    reg = {k:baseline[k] for k in ('assets','history_root','history_inputs','prior_output','prior_inventory')}
    reg.update(schema='memory-decision-pilot-registration-v2',mode=MODE,repo=str(repo),
        output=str(repo/'runs'/('memory-decision-pilot-v2-'+stamp)),
        control_root=str(repo/'.superpowers/sdd/memory-decision-pilot-v2-runtime'),
        publication_root=str(repo/'docs/reports/memory-decision-pilot-v2-evidence'),
        contract=str(repo/'docs/plans/memory-decision-pilot-v2.md'),
        contract_sha256=p.file_hash(repo/'docs/plans/memory-decision-pilot-v2.md'),
        diagnostic_driver_sha256=p.file_hash(d.__file__),python=sys.executable,
        runtime=d.runtime_v2_identity(),source_identity=p.source_identity(repo,baseline['assets']),
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
        prerequisite=reference,state_contract=d.STATE_CONTRACT,profile_sha256=d.PROFILE,
        protocol_sha256=p.SELECTED_PILOT_PROTOCOL_SHA256,expected_specs=specs,
        expected_cases=[world.make_case(s['seed'],s['regime'],s['kind'],s['mirrored'],
            profile_sha256=d.PROFILE) for s in specs],owner_slots=slots,seconds_caps=[6000,600],
        native_invocations=1,native_owners_max=30,corrective_studies=0,preparation_seconds_cap=180,
        preserved_sets=preserved,protected_roots=sorted({x['root'] for x in preserved}),
        qualification_claims=[],r2_complete=False,held_out_used=False)
    for name,target in dependencies(repo).items():
        reg[name+'_path']=str(target);reg[name+'_sha256']=p.file_hash(target)
    validate_registration(reg)
    return reg


def validate_registration(reg):
    if (reg.get('schema') != 'memory-decision-pilot-registration-v2' or reg.get('mode') != MODE
            or reg.get('seconds_caps') != [6000,600] or reg.get('state_contract') != d.STATE_CONTRACT
            or reg.get('profile_sha256') != d.PROFILE
            or reg.get('protocol_sha256') != p.SELECTED_PILOT_PROTOCOL_SHA256
            or reg.get('expected_specs') != p.selected_pilot_specs()
            or any(type(reg.get(k)) is not int or reg[k] != v for k,v in
                {'native_invocations':1,'native_owners_max':30,'corrective_studies':0,
                 'preparation_seconds_cap':180}.items())
            or reg.get('qualification_claims') != [] or reg.get('r2_complete') is not False
            or reg.get('held_out_used') is not False):
        raise ValueError('Unknown or extended selected pilot registration')
    repo = p.checked_path(reg['repo']); roots = [p.checked_path(reg[k]) for k in
        ('output','control_root','publication_root')]
    if (repo != Path(__file__).resolve().parents[1] or roots[0].parent != repo/'runs'
            or not roots[0].name.startswith('memory-decision-pilot-v2-')
            or roots[1] != repo/'.superpowers/sdd/memory-decision-pilot-v2-runtime'
            or roots[2] != repo/'docs/reports/memory-decision-pilot-v2-evidence'):
        raise ValueError('Selected pilot namespace differs')
    from palimpsest import memory_decision_world as world
    cases = [world.make_case(s['seed'],s['regime'],s['kind'],s['mirrored'],
        profile_sha256=d.PROFILE) for s in reg['expected_specs']]
    expected = [(s['id']+('/'+c if c else ''),'condition' if c else 'prefix',c)
                for s in reg['expected_specs'] for c in (None,*p.CONDITIONS)]
    slots = reg.get('owner_slots',[])
    if (reg.get('expected_cases') != cases or len(slots) != 30
            or [(s.get('job_id'),s.get('operation'),s.get('condition')) for s in slots] != expected
            or len({s.get('run_id') for s in slots}) != 30):
        raise ValueError('Thirty exact ordered owner slots/cases required')
    for slot in slots:
        if uuid.UUID(slot['run_id']).hex != slot['run_id']:
            raise ValueError('Invalid registered owner identity')
    protected = [p.checked_path(x) for x in reg.get('protected_roots',[])]
    if (not reg.get('preserved_sets') or {str(x) for x in protected} !=
            {x['root'] for x in reg['preserved_sets']}):
        raise ValueError('Protected pilot inputs are incomplete')
    sources = p.source_paths(repo,reg['assets'],reg['history_root'])+protected
    if (any(p.overlaps(r,s) for r in roots for s in sources)
            or any(p.overlaps(a,b) for i,a in enumerate(roots) for b in roots[i+1:])):
        raise ValueError('Counted roots overlap inputs or each other')
    for name,target in dependencies(repo).items():
        digest = reg.get(name+'_sha256')
        if (reg.get(name+'_path') != str(target) or type(digest) is not str or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('Missing selected pilot '+name+' dependency')


def budget(reg):
    return d.restore_v2_budget(reg)


def recheck_inputs(reg, deadline=None):
    validate_registration(reg)
    required = {k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')}
    required.update(MUJOCO_GL='egl',CUDA_VISIBLE_DEVICES='')
    if (reg['runtime'] != d.runtime_v2_identity() or reg['python'] != reg['runtime']['python_path']
            or reg['runtime']['python_version'] != [3,11,15]
            or reg['runtime']['versions'] != {'numpy':'2.2.5','mujoco':'3.3.6','torch':'2.9.0'}
            or reg['runtime']['environment'] != required):
        raise ValueError('Selected pilot requires the admitted exact CPU runtime')
    for name in dependencies(reg['repo']):
        check_file(reg[name+'_path'],reg[name+'_sha256'],deadline=deadline)
    if admit_prerequisites(reg['prerequisite']['registration_path'],reg['repo'],deadline) != reg['prerequisite']:
        raise ValueError('Registered prerequisite/worker derivation differs')
    baseline=p.read_json(reg['prerequisite']['registration_path'])
    if reg['runtime'] != baseline['runtime'] or reg['python'] != baseline['python']:
        raise ValueError('Pilot runtime differs from the admitted prerequisite runtime')
    check_file(reg['prerequisite_helper_path'],baseline['driver_sha256'],deadline=deadline)
    check_file(reg['inventory_helper_path'],baseline['comparator_sha256'],deadline=deadline)
    d.recheck_inputs(reg,deadline)
    for reference in reg['preserved_sets']: o.verify_inventory(reference,deadline)
    ledger=p.read_json(reg['byte_projection_path'])
    if (ledger.get('aggregate_bytes') != 8*p.GiB or ledger.get('headroom_bytes') != 64*p.MiB
            or type(ledger.get('projected_phase_bytes')) is not int
            or not 0 < ledger['projected_phase_bytes']+64*p.MiB < 8*p.GiB
            or ledger.get('guarantees_all_owners') is not False):
        raise ValueError('Finite fail-closed byte projection is required')


def validate_worker_admission(job):
    path = p.checked_path(job['pilot_registration_path'])
    check_file(path,job['pilot_registration_sha256'])
    reg=p.read_json(path);validate_registration(reg)
    if path != Path(reg['publication_root'])/'registration.json':
        raise ValueError('Worker registration namespace differs')
    label=job['spec']['id']+('/'+job['condition'] if job['condition'] else '')
    slots={s['job_id']:s for s in reg['owner_slots']};slot=slots.get(label)
    if (slot is None or job['run_id'] != slot['run_id'] or job['operation'] != slot['operation']
            or job['condition'] != slot['condition'] or job['phase_root'] != reg['output']
            or job['stage_output'] != str(Path(reg['output'])/'stage')
            or any(job[k] != reg[k] for k in ('repo','assets','history_root','source_identity','protocol_sha256'))):
        raise ValueError('Worker does not occupy its registered pilot slot')
    if job['operation']=='condition':
        source=Path(reg['output'])/'stage/runs'/slots[job['spec']['id']]['run_id']/'snapshots/initial.snp'
        if job['snapshot_path'] != str(source):
            raise ValueError('Condition must restore its registered fresh case prefix')
    recheck_inputs(reg)
    return reg


def validate_clock(reg,path,receipt,*,now=None):
    origin=m.launcher_origin(reg,path)
    readout=receipt['readout_started_monotonic']
    if type(readout) not in (int,float) or not math.isfinite(readout) or readout<origin:
        raise ValueError('Finite original pilot readout start required')
    deadline=min(origin+6600,readout+600)
    if (receipt['started_monotonic'] != origin or receipt['owner_deadline_monotonic'] != origin+6000
            or receipt['global_deadline_monotonic'] != origin+6600
            or receipt['readout_deadline_monotonic'] != deadline
            or type(readout) not in (int,float) or not math.isfinite(readout) or readout<origin
            or not readout <= (time.monotonic() if now is None else now) <= deadline):
        raise ValueError('Independent pilot close clock rebased or expired')
    return deadline


def check_owner_admission(job,storage,deadline=None):
    reg=p.read_json(job['pilot_registration_path'])
    origin=m.launcher_origin(reg,job['pilot_registration_path'])
    end=origin+6000
    if deadline is not None and deadline != end:
        raise ValueError('Selected owner deadline differs from original allocation')
    _,outer=p.owner_allocation('pilot-v2',job['operation'],p.SELECTED_PILOT_PROTOCOL_SHA256)
    if not p.admit_time(time.monotonic(),end,outer,p.PROTOCOL['cleanup_seconds']):
        raise TimeoutError('Original pilot allocation cannot admit owner and cleanup')
    recording=(384 if job['operation']=='condition' else 512)*p.MiB
    copy=p.read_json(reg['byte_projection_path'])['uncompressed_nonraw_copy_allowance']
    storage.check(recording+16*p.MiB+7*p.MiB+copy,path=Path(reg['output'])/'stage/runs')


def fresh_source(reg,spec,result,deadline):
    p.deadline_check(deadline)
    slot=next(s for s in reg['owner_slots'] if s['job_id']==spec['id'])
    path=Path(reg['output'])/'stage/runs'/slot['run_id']/'snapshots/initial.snp'
    if (result.get('snapshot_path') != str(path) or result.get('run_id') != slot['run_id']
            or path.stat().st_size>16*p.MiB or p.file_hash(path) != result['snapshot_sha256']):
        raise ValueError('Fresh case prefix snapshot binding differs')
    state=d.read_snapshot(path)
    if (p.condition_digest(state) != result['invariant']
            or state['application']['memory']['supervisor']['phase'] != 'await_decision'
            or type(state['application']['episode_step']) is not int
            or not 0<state['application']['episode_step']<=1200):
        raise ValueError('Fresh case source invariant or boundary differs')
    return {'snapshot_path':str(path),'snapshot_sha256':result['snapshot_sha256'],
        'invariant':result['invariant'],'run_id':slot['run_id'],'source_job_id':spec['id'],
        'bytes':path.stat().st_size,'source_receipt_ids':sorted(state['application']['receipts'])}


def run(path):
    path=p.checked_path(path);reg=p.read_json(path);validate_registration(reg)
    started=m.launcher_origin(reg,path);end=started+6000;repo=Path(reg['repo'])
    if path != Path(reg['publication_root'])/'registration.json':
        raise ValueError('Pilot registration path differs')
    if subprocess.check_output(['git','status','--porcelain'],cwd=repo):
        raise ValueError('Native pilot requires a clean committed checkout')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if subprocess.check_output(['git','diff',reg['implementation_commit'],head,'--name-only','--',
            'src','scripts','tests','model_manifests','uv.lock','upstream'],cwd=repo):
        raise ValueError('Registered implementation differs')
    root=p.safe_output(reg['output'],p.source_paths(repo,reg['assets'],reg['history_root'])+
        reg['protected_roots']+[reg['control_root'],reg['publication_root']])
    recheck_inputs(reg,end)
    plan=p.preflight(repo,reg['assets'],reg['history_root'],root/'stage',root,end,profile_sha256=d.PROFILE)
    plan.update(protocol=p.SELECTED_PILOT_PROTOCOL,protocol_sha256=p.SELECTED_PILOT_PROTOCOL_SHA256,
        selected_profile_sha256=d.PROFILE,owner_slots=reg['owner_slots'],
        pilot_registration_path=str(path),pilot_registration_sha256=p.file_hash(path))
    storage=budget(reg)
    receipt={'schema':'memory-decision-pilot-execution-v2','mode':MODE,'output':str(root),
        'registration_sha256':p.file_hash(path),'implementation_head':head,
        'launcher_marker_sha256':p.file_hash(Path(reg['control_root'])/'launched.json'),
        'source_identity':reg['source_identity'],'state_contract':reg['state_contract'],
        'process_namespace':os.readlink('/proc/self/ns/pid'),
        'started_utc':datetime.now(timezone.utc).isoformat(),'started_monotonic':started,
        'owner_deadline_monotonic':end,'global_deadline_monotonic':started+6600,'seconds_caps':[6000,600],
        'status':'running','attempted':[],'unattempted':[],'pair_audits':[],
        'mandatory_pass':False,'pilot_complete':False,'mechanism_observed':False,
        'r2_complete':False,'qualification_claims':[],'held_out_used':False,'retries':0}
    def interrupted(signum,frame):raise RuntimeError('Pilot interrupted: '+str(signum))
    previous=signal.signal(signal.SIGTERM,interrupted)
    root.mkdir(parents=True,exist_ok=False)
    try:
        with storage.lock():
            (root/'stage').mkdir()
            p.write_control(root/'registration.json',reg,storage)
            p.write_control(root/'stage/preflight.json',plan,storage)
            def checkpoint(result):
                result=dict(result)
                if result.get('raw_audit_pass') is not True:result.pop('capped_ticks',None)
                compact=retain_report(root,result,storage)
                receipt['attempted'].append(compact)
                d.replace_control(root/'execution.json',receipt,storage)
                return compact
            try:
                stage=p.execute_stage('pilot-v2',plan,storage,end,checkpoint=checkpoint)
                receipt.update({key:stage[key] for key in ('unattempted','pair_audits','mandatory_pass','errors')})
                receipt['mechanism_observed']=stage.get('mechanism_observed',False)
                receipt['status']='pilot-provisional-pass' if stage['mandatory_pass'] else 'owner-or-admission-stop'
                p.deadline_check(end)
            except BaseException as error:
                receipt.update(status='owner-or-admission-stop',error={'type':type(error).__name__,'message':str(error)})
            finally:
                readout=time.monotonic();deadline=min(started+6600,readout+600)
                receipt.update(readout_started_monotonic=readout,readout_deadline_monotonic=deadline)
                try:
                    receipt['cleanup']=d.cleanup_owners(root)
                    if any(row['status'] not in ('already-exited','pid-reused-do-not-touch') or
                           not d.owner_exited(row['owner']) for row in receipt['cleanup']):
                        raise ValueError('Pilot cleanup required termination or matching owner remains')
                    recheck_inputs(reg,deadline)
                    receipt['source_and_prior_evidence_unchanged']=True
                    receipt['artifact_index']=[row for row in p.hash_ledger(root,deadline) if row['path']!='execution.json']
                except BaseException as error:
                    receipt.update(status='owner-or-admission-stop',close_error={'type':type(error).__name__,'message':str(error)})
                ids={row['job_id'] for row in receipt['attempted']}
                receipt['unattempted']=[row['job_id'] for row in reg['owner_slots'] if row['job_id'] not in ids]
                receipt.update(total_seconds=time.monotonic()-started,readout_seconds=time.monotonic()-readout)
                d.replace_control(root/'execution.json',receipt,storage)
                storage.check(0,path=root/'execution.json');p.deadline_check(deadline)
    finally:signal.signal(signal.SIGTERM,previous)
    print(json.dumps({k:receipt[k] for k in ('status','mandatory_pass','mechanism_observed','unattempted')}),flush=True)
    return 0 if receipt['status']=='pilot-provisional-pass' else 1


def read_evidence(reg,receipt,deadline,storage,evidence):
    root=Path(reg['output']);stage=root/'stage';slots=reg['owner_slots']
    jobs=p.hash_ledger(stage/'jobs',deadline)
    started=[row for row in p.hash_ledger(stage/'runs',deadline) if Path(row['path']).name=='owner.json']
    evidence.update(allocated_jobs=jobs,started_owners=started,owners=[],pair_audits=[])
    expected={slot['run_id']+'.json':slot for slot in slots}
    actual={row['path'] for row in jobs}
    attempts=receipt['attempted'];attempted={a['run_id']:a for a in attempts}
    cleanup={row['owner']['run_id']:row for row in receipt.get('cleanup',[])}
    complete=(len(jobs)==len(started)==len(attempts)==len(cleanup)==30
        and len(attempted)==30 and len(receipt.get('cleanup',[]))==30
        and [a['job_id'] for a in attempts]==[s['job_id'] for s in slots])
    errors=[]
    if actual != {s['run_id']+'.json' for s in slots[:len(jobs)]} or not actual<=set(expected):
        errors.append('Allocated jobs are not the registered ordered prefix')
    allocated={expected[name]['run_id'] for name in actual if name in expected}
    if ({row['path'] for row in started}!={rid+'/owner.json' for rid in allocated}
            or set(attempted)!=allocated or set(cleanup)!={row['path'].split('/')[0] for row in started}):
        errors.append('Allocated/started/attempted/cleanup accounting differs')
    full={};sources={}
    for index,slot in enumerate(slots):
        if slot['run_id'] not in allocated:continue
        p.deadline_check(deadline)
        row={**slot,'raw_audit_pass':False,'disposition':'allocated-unstarted'}
        evidence['owners'].append(row)
        try:
            job=p.validate_job(p.read_json(stage/'jobs'/(slot['run_id']+'.json')),read_only=True)
            spec=reg['expected_specs'][index//5]
            if (job['spec']!=spec or job['case']!=reg['expected_cases'][index//5]
                    or job['run_id']!=slot['run_id'] or job['operation']!=slot['operation']
                    or job['condition']!=slot['condition']):
                raise ValueError('Allocated job differs from its registered slot')
            run=Path(job['output']);owner=p.read_json(run/'owner.json')
            row.update(owner=owner,disposition='started-incomplete')
            observed=cleanup.get(slot['run_id'])
            if (owner.get('run_id')!=slot['run_id'] or observed is None or observed['owner']!=owner
                    or observed['path']!=str(run/'owner.json')
                    or observed['status'] not in ('already-exited','pid-reused-do-not-touch')
                    or not d.owner_exited(owner)):
                raise ValueError('Matching native owner exit proof differs')
            row['matching_owner_exited']=True
            supervised_path=stage/'supervision'/slot['run_id']
            supervised=p.read_json(supervised_path/'supervisor.json')
            internal,outer=p.owner_allocation('pilot-v2',slot['operation'],p.SELECTED_PILOT_PROTOCOL_SHA256)
            elapsed=supervised.get('elapsed_seconds');attempt=attempted.get(slot['run_id'],{})
            if (supervised != attempt.get('supervision') or supervised.get('timeout_seconds')!=outer
                    or supervised.get('output')!=str(supervised_path)
                    or type(elapsed) not in (int,float) or not math.isfinite(elapsed) or not 0<=elapsed<=outer
                    or any(x.stat().st_size>p.MiB for x in supervised_path.glob('*.log'))):
                raise ValueError('Original owner supervision differs')
            if slot['operation']=='condition':
                source=sources[spec['id']]
                if tuple(job[k] for k in ('snapshot_path','snapshot_sha256','expected_invariant')) != tuple(
                        source[k] for k in ('snapshot_path','snapshot_sha256','invariant')):
                    raise ValueError('Continuation changed its common fresh case source')
            report=p.read_json(run/'worker-report.json')
            audited=(p.audit_prefix_failure(job,supervised,deadline) if slot['operation']=='prefix'
                and report.get('acquired') is False else p.audit_run(job,supervised,deadline))
            if (audited.get('raw_audit_pass') is not True or audited.get('status')!='recorded'
                    and audited.get('retained_task_failure') is not True):
                raise ValueError('Independent audit did not admit recording or natural task failure')
            wall=audited.get('wall_seconds',report.get('wall_seconds'))
            if (type(wall) not in (int,float) or not math.isfinite(wall) or not 0<=wall<=internal
                    or any(audited.get(k)!=attempt.get(k) for k in ('snapshot_sha256','invariant',
                       'trace_digest','goal','acquired','continuation_ticks','path_length','route_commits',
                       'post_event_samples','retreat_completed','first_commitment_blocked','replans'))):
                raise ValueError('Independent owner metrics or time differs from checkpoint')
            audited.update(job_id=slot['job_id'],run_id=slot['run_id'],condition=slot['condition'])
            if slot['operation']=='prefix':audited.pop('capped_ticks',None)
            compact=retain_report(reg['publication_root'],audited,storage)
            row.update(disposition='audited-recording' if audited['status']=='recorded' else 'audited-task-failure',
                raw_audit_pass=True,audit=compact)
            if slot['operation']=='prefix':
                if not p.prerequisite_pass('prefix',audited):
                    raise ValueError('Fresh acquisition failed; pair remains incomplete')
                sources[spec['id']]=fresh_source(reg,spec,audited,deadline)
            full[slot['job_id']]=audited
            if slot['operation']=='condition':row['capped_ticks']=p.capped_score(audited)
        except Exception as error:
            complete=False;row['audit_error']={'type':type(error).__name__,'message':str(error)}
            errors.append(slot['job_id']+': '+str(error))
    for spec in reg['expected_specs']:
        ids=[spec['id']+'/'+condition for condition in p.CONDITIONS]
        if all(key in full for key in ids):
            pair=p.audit_case_pair(spec,[full[key] for key in ids]);evidence['pair_audits'].append(pair)
            if not pair['own_sham_identical'] or not pair['commitment_before_fresh_sample']:
                complete=False;errors.append(spec['id']+': identity/opportunity gate failed')
    evidence.update(fresh_sources=list(sources.values()),mandatory_pass=complete,
        mechanism_observed=p.mechanism_observed(evidence['pair_audits']),
        unattempted=[slot['job_id'] for slot in slots if slot['run_id'] not in allocated],
        errors=errors,total_new_controls=sum(a['audit'].get('total_ticks',0) if a['operation']=='prefix'
            else a['audit'].get('continuation_ticks',0) for a in evidence['owners'] if a['raw_audit_pass']))


def invalidate(root,storage,error):
    path=Path(root)/'scientific-close.json'
    if path.exists():
        close=p.read_json(path);close.update(status='scientific-close-stop',pilot_complete=False,
            qualification_claims=[],invalidation_error=str(error))
        try:d.replace_control(path,close,storage)
        except BaseException:
            if path.exists() and p.read_json(path).get('pilot_complete') is True:
                path.rename(Path(root)/'scientific-close.invalidated.json')


def audit(path):
    path=p.checked_path(path);reg=p.read_json(path);validate_registration(reg)
    root=Path(reg['output']);target=root/'scientific-close.json';storage=budget(reg)
    if target.exists():raise FileExistsError('Scientific close exists; no repeated readout')
    close={'schema':'memory-decision-pilot-scientific-close-v2','status':'scientific-close-stop',
        'output':str(root),'state_contract':reg['state_contract'],'pilot_complete':False,
        'mandatory_pass':False,'mechanism_observed':False,'r2_complete':False,
        'qualification_claims':[],'held_out_used':False,'physics_steps':0,'new_native_owners':0,
        'owners':[],'unattempted':[slot['job_id'] for slot in reg['owner_slots']]}
    try:
        receipt=p.read_json(root/'execution.json');deadline=validate_clock(reg,path,receipt)
        digest=p.file_hash(path);execution_digest=p.file_hash(root/'execution.json')
        original=p.hash_ledger(root,deadline)
        close.update(registration_sha256=digest,driver_execution_sha256=execution_digest,
            readout_deadline_monotonic=deadline,process_namespace=receipt['process_namespace'])
        jobs=p.hash_ledger(root/'stage/jobs',deadline)
        started=[row for row in p.hash_ledger(root/'stage/runs',deadline) if Path(row['path']).name=='owner.json']
        allocated={row['path'] for row in jobs}
        close.update(allocated_jobs=jobs,started_owners=started,
            owners=[{**slot,'disposition':'started-incomplete' if any(
                row['path']==slot['run_id']+'/owner.json' for row in started) else 'allocated-unstarted',
                'raw_audit_pass':False} for slot in reg['owner_slots'] if slot['run_id']+'.json' in allocated],
            unattempted=[slot['job_id'] for slot in reg['owner_slots'] if slot['run_id']+'.json' not in allocated])
        def recheck():
            p.deadline_check(deadline)
            if (p.file_hash(path)!=digest or p.file_hash(root/'execution.json')!=execution_digest
                    or p.file_hash(Path(reg['control_root'])/'launched.json')!=receipt['launcher_marker_sha256']
                    or Path(reg['auditor_path'])!=Path(__file__).resolve()
                    or os.readlink('/proc/self/ns/pid')!=receipt['process_namespace']):
                raise ValueError('Independent pilot auditor/input/namespace binding differs')
            recheck_inputs(reg,deadline)
        recheck();storage.check(30*p.MiB+2*p.MiB,path=target)
        read_evidence(reg,receipt,deadline,storage,close)
        if (receipt.get('schema')!='memory-decision-pilot-execution-v2' or receipt.get('mode')!=MODE
                or receipt.get('status')!='pilot-provisional-pass' or receipt.get('registration_sha256')!=digest
                or receipt.get('source_identity')!=reg['source_identity'] or receipt.get('output')!=str(root)
                or receipt.get('state_contract')!=reg['state_contract'] or receipt.get('seconds_caps')!=[6000,600]
                or receipt.get('pilot_complete') is not False or receipt.get('r2_complete') is not False
                or receipt.get('qualification_claims')!=[] or receipt.get('held_out_used') is not False
                or receipt.get('unattempted') or receipt.get('source_and_prior_evidence_unchanged') is not True
                or receipt.get('retries')!=0 or any(k in receipt for k in ('error','close_error'))
                or p.read_json(root/'registration.json')!=reg or not close['mandatory_pass']):
            raise ValueError('Pilot did not completely pass all registered controls')
        if receipt['artifact_index'] != [row for row in original if row['path']!='execution.json']:
            raise ValueError('Retained pilot artifact inventory differs')
        if (close['pair_audits']!=receipt['pair_audits']
                or close['mechanism_observed']!=receipt['mechanism_observed']
                or receipt.get('mandatory_pass') is not True):
            raise ValueError('Independent pair/calibration readout differs')
        for row in close['owners']:
            check_file(row['audit']['audit_path'],row['audit']['audit_sha256'],deadline=deadline)
        recheck()
        if p.hash_ledger(root,deadline)!=original:
            raise ValueError('Raw pilot evidence changed during independent audit')
        close.update(immutable_inputs_and_raw_evidence_unchanged=True,storage_before_close=storage.check(0,path=target))
        p.deadline_check(deadline)
        close.update(status='pilot-complete',pilot_complete=True,closed_monotonic=time.monotonic())
        d.replace_control(target,close,storage)
        storage.check(0,path=target);p.deadline_check(deadline)
    except BaseException as error:
        close.update(status='scientific-close-stop',pilot_complete=False,error={'type':type(error).__name__,'message':str(error)})
        try:d.replace_control(target,close,storage)
        except BaseException as publication_error:
            close['failure_publication_error']=str(publication_error);invalidate(root,storage,error)
    print(json.dumps({k:close.get(k) for k in ('status','pilot_complete','mandatory_pass','mechanism_observed','error')}),flush=True)
    return 0 if close['pilot_complete'] else 1


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration',type=Path,required=True);parser.add_argument('--audit',action='store_true')
    args=parser.parse_args(argv)
    return audit(args.registration) if args.audit else run(args.registration)


if __name__=='__main__':raise SystemExit(main())
