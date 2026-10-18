"""One registered exploratory readout of retained restores; never new owners.

The prior failed scientific close is immutable. Recorded owner cleanup is
historical namespace evidence, not a current PID probe or qualification.
"""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import time

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from scripts.memory_waypoint_study import replace_control
from palimpsest.storage import StorageBudget, StorageLimits

SECONDS = 300


def runtime_identity():
    return {'python':list(sys.version_info[:3]),
            'numpy':importlib.metadata.version('numpy'),
            'mujoco':importlib.metadata.version('mujoco')}


def verify_inventory(reference, deadline):
    actual = p.hash_ledger(reference['root'],deadline)
    keyed = lambda rows:{row['path']:(row['bytes'],row['sha256']) for row in rows}
    if len(keyed(reference['files'])) != len(reference['files']) or keyed(actual) != keyed(reference['files']):
        raise ValueError('Immutable retained evidence inventory changed')


def attribute_native_pair(left, right, deadline=None):
    """Map timer bytes on decoded copies only; preserve the scientific state gate."""
    import mujoco
    if mujoco.__version__ != '3.3.6':
        raise ValueError('Byte attribution requires the reviewed MuJoCo 3.3.6 serializer')
    payloads = [state['native_data'] for state in (left,right)]
    if any(type(value) is not bytes or len(value)>16*p.MiB for value in payloads):
        raise ValueError('Attribution requires bounded trusted native bytes')
    if len(payloads[0])!=len(payloads[1]):
        raise ValueError('Native payload lengths differ; no same-layout attribution')
    def offsets(one,two):
        if len(one)!=len(two):raise ValueError('Probe changed serialized layout')
        return [i for i,(x,y) in enumerate(zip(one,two)) if x!=y]
    decoded, sides, ownership = [], [], []
    for payload in payloads:
        p.deadline_check(deadline)
        data=mujoco.MjData.__new__(mujoco.MjData); data.__setstate__(payload)
        if data.__getstate__()!=payload:
            raise ValueError('Native round trip differs; attribution refused')
        decoded.append(data)
        arrays={}
        for name in ('efc_AR_rowadr','efc_AR_rownnz'):
            value=getattr(data,name)
            arrays[name]={'shape':list(value.shape),'dtype':value.dtype.str,
                'numpy_owns_data':bool(value.flags.owndata),'has_base':value.base is not None}
        side={'solver':int(data.model.opt.solver),
            'solver_name':mujoco.mjtSolver(data.model.opt.solver).name,
            'noslip_iterations':int(data.model.opt.noslip_iterations),
            'dual_solver_eligible':bool(data.model.opt.solver==mujoco.mjtSolver.mjSOL_PGS or data.model.opt.noslip_iterations>0),
            'nA':int(data.nA),'nefc':int(data.nefc),'suspect_array_views':arrays,'timer_fields':[]}
        owners={}
        for index,original in enumerate(data.timer.duration.copy()):
            p.deadline_check(deadline)
            original_bytes=struct.pack('=d',float(original))
            if not math.isfinite(float(original)):
                raise ValueError('Nonfinite timer statistic')
            for mask in (1,2):
                probe_bytes=bytes(value^mask for value in original_bytes)
                probe=struct.unpack('=d',probe_bytes)[0]
                if math.isfinite(probe):break
            else:raise ValueError('No finite timer probe')
            try:
                data.timer.duration[index]=probe
                changed=data.__getstate__()
            finally:
                data.timer.duration[index]=original
            changed_offsets=offsets(payload,changed)
            if (len(changed_offsets)!=8 or changed_offsets!=list(range(changed_offsets[0],changed_offsets[0]+8))
                    or payload[changed_offsets[0]:changed_offsets[0]+8]!=original_bytes
                    or changed[changed_offsets[0]:changed_offsets[0]+8]!=probe_bytes
                    or any(offset in owners for offset in changed_offsets)):
                raise ValueError('Timer probe is not one unique contiguous float64 field')
            if data.__getstate__()!=payload:
                raise ValueError('Restoring a timer probe changed native bytes')
            owners.update((offset,index) for offset in changed_offsets)
            side['timer_fields'].append({'index':index,'duration':float(original),
                'start_offset':changed_offsets[0],'end_offset_exclusive':changed_offsets[-1]+1,
                'probe_changed_bytes':8,'probe_sha256':p.hashlib.sha256(changed).hexdigest()})
        sides.append(side); ownership.append(owners)
    different=offsets(*payloads)
    attributed=[offset for offset in different if offset in ownership[0] and ownership[0][offset]==ownership[1].get(offset)]
    attributed_set=set(attributed)
    unexplained=[offset for offset in different if offset not in attributed_set]
    original=decoded[0].timer.duration.copy()
    try:
        decoded[0].timer.duration[:]=decoded[1].timer.duration
        patched=decoded[0].__getstate__()
    finally:
        decoded[0].timer.duration[:]=original
    if decoded[0].__getstate__()!=payloads[0]:
        raise ValueError('Timer attribution copy did not restore exactly')
    p.deadline_check(deadline)
    return {'payload_bytes':[len(value) for value in payloads],'roundtrip_equal':[True,True],
        'different_offsets':different,'attributed_offsets':attributed,'unexplained_offsets':unexplained,
        'all_differences_attributed_to_timer_duration':bool(different) and not unexplained and patched==payloads[1],
        'timer_patch_equal_to_right':patched==payloads[1],
        'timer_patch_sha256':p.hashlib.sha256(patched).hexdigest(),'sides':sides,
        'physics_steps':0,'new_native_owners':0,
        'scope':'Decoded-copy serialization probes only; no snapshot repair, gate change or qualification'}


def recheck_inputs(registration, deadline):
    p.deadline_check(deadline)
    if runtime_identity() != registration['runtime_identity']:
        raise ValueError('Registered offline runtime differs')
    for reference in registration['bound_files']:
        path = p.checked_path(reference['path'])
        if path.stat().st_size != reference['bytes'] or p.file_hash(path) != reference['sha256']:
            raise ValueError('Registered offline implementation/input changed')
        p.deadline_check(deadline)
    if p.source_identity(registration['repo'],registration['assets']) != registration['source_identity']:
        raise ValueError('Frozen source or assets changed')
    for reference in registration['preserved_sets']:
        verify_inventory(reference,deadline)
    p.deadline_check(deadline)


def audit_pair(registration, deadline):
    root = p.checked_path(registration['retained_root']); stage=root/'stage'
    close_path = p.checked_path(registration['failed_close']['path'])
    if close_path != root/'execution.json' or p.file_hash(close_path) != registration['failed_close']['sha256']:
        raise ValueError('Original failed-close binding differs')
    close = p.read_json(close_path)
    if close.get('status') != 'independent-readout-stop' or close.get('native_prerequisites_passed') is not False or close.get('qualification_claims') != []:
        raise ValueError('Original failed disposition differs')
    attempts = close['attempted']; cleanup = close['cleanup']
    if len(attempts)!=2 or len(cleanup)!=2:
        raise ValueError('Offline study requires exactly two recorded owners')
    specs = d.p.travel_specs('travel-feasibility',d.PROFILE)[-2:]
    if [row['job_id'] for row in attempts] != [row['id'] for row in specs]:
        raise ValueError('Retained restore order differs')
    cleanup_by_run = {row['owner']['run_id']:row for row in cleanup}
    if len(cleanup_by_run)!=2 or len({row['run_id'] for row in attempts})!=2:
        raise ValueError('Duplicate restore/cleanup identities')
    allocated = sorted((stage/'jobs').glob('*.json'))
    if {path.name for path in allocated} != {row['run_id']+'.json' for row in attempts}:
        raise ValueError('Extra or missing allocated restore job')
    started = {str(path) for path in (stage/'runs').glob('*/owner.json')}
    expected_started = {str(stage/'runs'/row['run_id']/'owner.json') for row in attempts}
    if started != expected_started:
        raise ValueError('Extra or missing recorded owner')
    rows, posts, ids, sources = [], [], [], []
    for recorded, spec in zip(attempts,specs):
        p.deadline_check(deadline)
        path = stage/'jobs'/(recorded['run_id']+'.json')
        job = p.validate_job(p.read_json(path),read_only=True)
        run = p.checked_path(job['output'])
        if (job['run_id']!=recorded['run_id'] or run!=stage/'runs'/job['run_id']
                or job['spec']!=spec or job['operation']!='repeat'):
            raise ValueError('Retained job identity/spec/output differs')
        owner = p.read_json(run/'owner.json'); historical = cleanup_by_run.get(job['run_id'])
        if (owner.get('run_id')!=job['run_id'] or historical is None or
                historical['owner']!=owner or historical['path']!=str(run/'owner.json') or
                historical['status']!='already-exited'):
            raise ValueError('Recorded same-namespace cleanup does not bind this owner')
        if any(type(owner.get(key)) is not int or owner[key]<=0 for key in ('pid','pgid','starttime')) or owner['pid']!=owner['pgid']:
            raise ValueError('Invalid recorded owner identity')
        sources.append((job['snapshot_path'],job['snapshot_sha256'],job['expected_invariant']))
        if p.file_hash(job['snapshot_path'])!=job['snapshot_sha256']:
            raise ValueError('Retained restore source changed')
        audited = p.audit_run(job,recorded['supervision'],deadline)
        raw = p.read_raw(run,deadline)
        if len(raw['rows'])!=5 or audited.get('continuation_ticks')!=5 or audited.get('invariants_preserved') is not True:
            raise ValueError('Retained restore must have five audited invariant-preserving controls')
        if any(audited.get(key)!=recorded.get(key) for key in
               ('trace_digest','post_state_digest','post_snapshot_sha256','post_state_components')):
            raise ValueError('Offline audit differs from recorded owner receipt')
        post, source_ids = d.audit_post_state(run,audited)
        if post.get('identity',{}).get('mujoco') not in (None,runtime_identity()['mujoco']):
            raise ValueError('Retained native snapshot runtime differs')
        posts.append(post); ids.append(source_ids)
        rows.append({'run_id':job['run_id'],'job_id':spec['id'],'owner':owner,
            'historical_cleanup_status':historical['status'],'raw_rows':len(raw['rows']),
            'raw_audit_pass':True,'retained_post_state_audited':True,
            'trace_digest':audited['trace_digest'],'post_state_digest':audited['post_state_digest'],
            'initial_invariants_preserved':True,'post_snapshot_sha256':audited['post_snapshot_sha256']})
    if sources[0]!=sources[1]:raise ValueError('The restore pair has different sources')
    p.deadline_check(deadline)
    comparison = d.compare_states(posts[0],posts[1],ids[0],ids[1])
    native = d.compare_native_states(posts[0],posts[1]) if 'native_data' in comparison['differing_components'] else None
    p.deadline_check(deadline)
    result = {'owners':rows,'trace_equal':rows[0]['trace_digest']==rows[1]['trace_digest'],
        'comparison':comparison,'native_comparison':native,'independent_restore_attempts':2,
        'controls_per_restore':5,'physics_steps':0,'new_native_owners':0,
        'owner_exit_evidence':'recorded same-namespace cleanup only; current liveness unassessed',
        'qualifier':'Separate exploratory offline audit; original failed close and prerequisite gate unchanged',
        'qualification_claims':[]}
    if registration.get('readout_kind')=='native-byte-attribution-v1':
        result['byte_attribution']=attribute_native_pair(posts[0],posts[1],deadline)
    return result


def main(argv=None):
    started = time.monotonic(); deadline=started+SECONDS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration',type=Path,required=True)
    args=parser.parse_args(argv); registration=p.read_json(args.registration)
    repo=p.checked_path(registration['repo'])
    if (registration.get('schema')!='memory-restore-offline-registration-v1' or
            registration.get('seconds_cap')!=SECONDS or repo!=Path(__file__).resolve().parents[1] or
            registration.get('readout_kind') not in (None,'native-byte-attribution-v1')):
        raise ValueError('Registered offline checkout/schema/allocation differs')
    if subprocess.check_output(['git','status','--porcelain'],cwd=repo):
        raise ValueError('Offline admission requires a clean checkout')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if subprocess.check_output(['git','diff',registration['implementation_commit'],head,'--name-only',
        '--','src','scripts','tests','model_manifests','uv.lock','upstream'],cwd=repo):
        raise ValueError('Registered offline implementation differs')
    protected=p.source_paths(repo,registration['assets'],registration['history_root'])+[p.checked_path(registration['retained_root'])]
    root=p.safe_output(registration['output'],protected)
    recheck_inputs(registration,deadline)
    if shutil.disk_usage(root.parent if root.parent.exists() else repo).free < 10*p.GiB:
        raise ValueError('Offline admission requires at least 10 GiB free')
    storage=StorageBudget((root,),StorageLimits(max_bytes=64*p.MiB,min_free_bytes=2*p.GiB),headroom_bytes=64*p.MiB)
    receipt={'schema':'memory-restore-offline-execution-v1','status':'running',
        'started_utc':datetime.now(timezone.utc).isoformat(),'started_monotonic':started,
        'deadline_monotonic':deadline,'implementation_head':head,'output':str(root),
        'registration_sha256':p.file_hash(args.registration),'original_failed_status':'independent-readout-stop',
        'offline_pair_audit_complete':False,'new_native_owners':0,'physics_steps':0,
        'native_prerequisites_passed':False,'qualification_claims':[],'held_out_used':False,
        'paired_pilot':'unattempted-by-scope','native_retries':0}
    def interrupted(signum,frame):raise RuntimeError('Offline invocation interrupted: '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    root.mkdir(parents=True,exist_ok=False)
    with storage.lock():
        p.write_control(root/'registration.json',registration,storage)
        replace_control(root/'execution.json',receipt,storage)
        try:
            analysis=audit_pair(registration,deadline)
            p.write_control(root/'analysis.json',analysis,storage)
            receipt['summary']={'trace_equal':analysis.get('trace_equal'),
                'state_equal':analysis['comparison']['equal'],
                'differing_components':analysis['comparison'].get('differing_components'),
                'owner_count':len(analysis['owners']),
                'native_fields_equal':(analysis.get('native_comparison') or {}).get('equal')}
            if 'byte_attribution' in analysis:
                receipt['summary']['all_native_differences_are_timer_duration']=analysis['byte_attribution']['all_differences_attributed_to_timer_duration']
            recheck_inputs(registration,deadline)
            receipt['immutable_inputs_unchanged']=True
            receipt['artifact_index']=[row for row in p.hash_ledger(root,deadline) if row['path']!='execution.json']
            receipt['storage_before_close']=storage.usage()
            p.deadline_check(deadline)
            receipt.update(status='offline-audit-complete',offline_pair_audit_complete=True)
        except BaseException as error:
            receipt.update(status='offline-readout-stop',offline_pair_audit_complete=False,
                error={'type':type(error).__name__,'message':str(error)},qualification_claims=[])
        receipt['total_seconds']=time.monotonic()-started
        try:
            p.deadline_check(deadline); replace_control(root/'execution.json',receipt,storage); p.deadline_check(deadline)
        except BaseException as error:
            receipt.update(status='offline-readout-stop',offline_pair_audit_complete=False,
                close_error={'type':type(error).__name__,'message':str(error)},qualification_claims=[])
            replace_control(root/'execution.json',receipt,storage)
    print(json.dumps({key:receipt.get(key) for key in ('status','total_seconds','summary',
        'offline_pair_audit_complete','new_native_owners','physics_steps','qualification_claims')},indent=2),flush=True)
    return 0 if receipt['offline_pair_audit_complete'] else 1


if __name__=='__main__':raise SystemExit(main())
