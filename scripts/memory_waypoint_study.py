"""One opt-in bounded waypoint-development and prerequisite study; no pilot.

All three candidates are registered/frozen before execution. Only an independently
audited declared task failure can advance development. A mandatory failure stops.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from datetime import datetime, timezone

from scripts import memory_decision_pilot as pilot
monotonic = time.monotonic


def study_protocol(plan):
    return pilot.TRAVEL_PROTOCOL if plan.get('protocol_sha256')==pilot.TRAVEL_PROTOCOL_SHA256 else pilot.WAYPOINT_PROTOCOL


def candidate_specs(plan=None):
    return (pilot.travel_specs('travel-development') if study_protocol(plan or {}) is pilot.TRAVEL_PROTOCOL
            else pilot.waypoint_specs('waypoint-development'))


def study_stage(plan, suffix):
    return ('travel-' if study_protocol(plan) is pilot.TRAVEL_PROTOCOL else 'waypoint-')+suffix


def mandatory_specs(plan, selected):
    stage = study_stage(plan,'feasibility')
    return pilot.travel_specs(stage,selected) if stage=='travel-feasibility' else pilot.waypoint_specs(stage,selected)



def replace_control(path, value, storage):
    """Mutable progress only; immutable inputs continue to use exclusive writes."""
    path = pilot.checked_path(path)
    pending = path.with_name(path.name+'.pending')
    pilot.write_control(pending,value,storage)
    pending.replace(path)


def run_prerequisites(plan, selected, storage, phase_deadline):
    from palimpsest import memory_decision_world as world
    started = monotonic()
    deadline = min(phase_deadline-600,started+study_protocol(plan)['stage_seconds']['prerequisites'])
    phase_root = Path(plan['phase_root'])
    pilot.write_control(phase_root/'selected-profile.json',{'profile_sha256':selected,
        'candidate_ledger_sha256':pilot.file_hash(phase_root/'candidates.json'),
        'development_report_sha256':pilot.file_hash(phase_root/'development/report.json')},storage)
    selected_plan = copy.deepcopy(plan)
    selected_plan.update(output=str(Path(plan['phase_root'])/'prerequisites'),selected_profile_sha256=selected)
    selected_plan['geometry'] = []
    for spec in mandatory_specs(plan,selected):
        pilot.deadline_check(deadline)
        case = world.make_case(spec['seed'],spec['regime'],spec['kind'],spec['mirrored'],profile_sha256=selected)
        selected_plan['geometry'].append({'id':spec['id'],'case':case,'check':world.geometry_check(case)})
    selected_plan['geometry_valid'] = all(x['check']['valid'] for x in selected_plan['geometry'])
    output = Path(selected_plan['output'])
    output.mkdir()
    pilot.write_control(output/'preflight.json',selected_plan,storage)
    prerequisites = pilot.execute_stage(study_stage(plan,'feasibility'),selected_plan,storage,deadline)
    prerequisites['status'] = 'passed' if prerequisites['mandatory_pass'] else 'failed'
    prerequisites['wall_seconds'] = monotonic()-started
    pilot.write_control(output/'report.json',prerequisites,storage)
    pilot.deadline_check(deadline)
    return prerequisites


def run_development(plan, storage, deadline, checkpoint=None):
    specs = candidate_specs(plan)
    stage = study_stage(plan,'development')
    report = {'stage':stage,'status':'failed','attempted':[],
        'unattempted':[s['id'] for s in specs],'selected_profile_sha256':None,'errors':[]}
    if not plan.get('geometry_valid'):
        report['errors'].append({'type':'GeometryInvalid','message':'Predeclared candidate geometry failed'})
        return report
    for index, spec in enumerate(specs):
        try:
            pilot.deadline_check(deadline)
            result = pilot.launch_owner(stage,spec,plan,storage,deadline)
            report['attempted'].append(result)
            report['unattempted'] = [s['id'] for s in specs[index+1:]]
            qualified = (result.get('status') == 'recorded' and result.get('raw_audit_pass') is True
                         and result.get('acquired') is True)
            task_failure = (result.get('status') == 'failed' and result.get('raw_audit_pass') is True
                            and result.get('retained_task_failure') is True and result.get('acquired') is False)
            if stage=='travel-development':
                qualified = (qualified and pilot.prerequisite_pass('retreat',result)
                             and result.get('first_commitment_blocked') is True and result.get('replans',0)>=1)
                task_failure = (result.get('status') in ('failed','recorded') and result.get('raw_audit_pass') is True
                                and result.get('retained_task_failure') is True and result.get('goal') is False)

            if qualified:
                report.update(status='passed',selected_profile_sha256=spec['profile_sha256'])
            elif not task_failure:
                report['errors'].append({'type':'InfrastructureFailure','message':'Candidate failure lacks independent task-failure admission'})
            if checkpoint is not None:
                checkpoint(report)
            if qualified or not task_failure:
                break
        except Exception as error:
            report['errors'].append({'type':type(error).__name__,'message':str(error)})
            break
    return report


def proc_identity(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    return int(fields[19]),os.getpgid(pid)


def cleanup_owners(root):
    """Touch only exact recorded PID/starttime/PGID identities."""
    rows = []
    for path in sorted(Path(root).rglob('owner.json')):
        owner = pilot.read_json(path)
        pid,starttime,pgid = (owner[k] for k in ('pid','starttime','pgid'))
        if any(type(v) is not int or v <= 0 for v in (pid,starttime,pgid)) or pid != pgid:
            raise ValueError('Invalid native owner identity')
        row = {'path':str(path),'owner':owner,'status':'already-exited'}
        try:
            if proc_identity(pid) != (starttime,pgid):
                row['status'] = 'pid-reused-do-not-touch'
            else:
                os.killpg(pgid,signal.SIGTERM)
                time.sleep(.5)
                try:
                    if proc_identity(pid) == (starttime,pgid):
                        os.killpg(pgid,signal.SIGKILL)
                except (FileNotFoundError,ProcessLookupError):
                    pass
                row['status'] = 'terminated-owned-worker'
        except (FileNotFoundError,ProcessLookupError):
            pass
        rows.append(row)
    return rows


def main(argv=None):
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--amendment',choices=('acquisition-loops','travel-handoff'),default='acquisition-loops')
    for name in ('repo','assets','history-root','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args(argv)
    def interrupted(signum,frame):
        raise RuntimeError('External phase interruption: '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    repo = pilot.checked_path(args.repo)
    output = pilot.safe_output(args.output,pilot.source_paths(repo,args.assets,args.history_root))
    deadline = started+7200
    protocol = pilot.TRAVEL_PROTOCOL if args.amendment=='travel-handoff' else pilot.WAYPOINT_PROTOCOL
    protocol_hash = pilot.sha(protocol)
    from palimpsest import memory_decision_world as world
    development_deadline = min(deadline-600,started+protocol['stage_seconds']['development'])
    plan = pilot.preflight(repo,args.assets,args.history_root,output/'development',output,development_deadline)
    plan.update(protocol=protocol,protocol_sha256=protocol_hash)
    candidates = []
    for spec in candidate_specs(plan):
        pilot.deadline_check(development_deadline)
        case = world.make_case(spec['seed'],spec['regime'],spec['kind'],spec['mirrored'],profile_sha256=spec['profile_sha256'])
        candidates.append({'spec':spec,'profile':world.registered_profile(spec['profile_sha256']),
            'case':case,'geometry':world.geometry_check(case),'arrival_analysis':world.arrival_analysis(case,include_routes=args.amendment=='travel-handoff')})
    plan['geometry'] = candidates
    plan['geometry_valid'] = all(c['geometry']['valid'] for c in candidates)
    storage = pilot.phase_budget(output)
    receipt = {'schema':'memory-waypoint-execution-v1','started_utc':datetime.now(timezone.utc).isoformat(),
        'phase_started_monotonic':started,'phase_deadline_monotonic':deadline,
        'output':str(output),'implementation_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
        'protocol':protocol,'protocol_sha256':protocol_hash,
        'source_identity':plan['source_identity'],'stage_caps':protocol['stage_seconds'],
        'max_seconds':7200,'max_bytes':8*pilot.GiB,'stages':{},'detached_owner_cleanup':[],
        'qualification_claims':[],'held_out_used':False,'paired_pilot':'unattempted-by-scope',
        'r2_complete':False,'retries':0}
    output.mkdir(parents=True,exist_ok=False)
    with storage.lock():
        (output/'development').mkdir()
        pilot.write_control(output/'candidates.json',{'protocol_sha256':protocol_hash,'candidates':candidates},storage)
        pilot.write_control(output/'development/preflight.json',plan,storage)
        def save():
            receipt['elapsed_seconds'] = time.monotonic()-started
            replace_control(output/'execution.json',receipt,storage)
        def checkpoint(report):
            receipt['detached_owner_cleanup'] = cleanup_owners(output)
            report['wall_seconds'] = time.monotonic()-started
            replace_control(output/'development/report.json',report,storage)
            receipt['stages']['development'] = report
            save()
            pilot.deadline_check(development_deadline)
        save()
        try:
            report = run_development(plan,storage,development_deadline,checkpoint)
            checkpoint(report)
            selected = report['selected_profile_sha256']
            if report['status'] == 'passed':
                prerequisites = run_prerequisites(plan,selected,storage,deadline)
                receipt['stages']['prerequisites'] = prerequisites
            else:
                receipt['stages']['prerequisites'] = {'status':'unattempted','reason':'No independently qualified development candidate',
                    'unattempted':[s['id'] for s in pilot.feasibility_specs()]}
            receipt['status'] = 'finished-bounded-attempt'
        except BaseException as error:
            receipt.update(status='execution-failed',error={'type':type(error).__name__,'message':str(error)})
        finally:
            readout_started = time.monotonic()
            readout_deadline = min(deadline,readout_started+600)
            receipt['readout_started_monotonic'] = readout_started
            receipt['readout_deadline_monotonic'] = readout_deadline
            receipt['detached_owner_cleanup'] = cleanup_owners(output)
            try:
                receipt['source_identity_unchanged'] = pilot.source_identity(repo,args.assets) == plan['source_identity']
                if not receipt['source_identity_unchanged']:
                    raise ValueError('Source or assets changed during study')
                # The 7200s cap covers this entire index/readout, not only workers.
                index = pilot.hash_ledger(output,readout_deadline)
                receipt['artifact_index'] = [x for x in index if x['path'] != 'execution.json']
                receipt['storage_usage'] = storage.usage()
                receipt['readout_seconds'] = time.monotonic()-readout_started
                pilot.deadline_check(readout_deadline)
            except BaseException as error:
                receipt.update(status='readout-failed',readout_error={'type':type(error).__name__,'message':str(error)})
            save()
    print(json.dumps({'receipt':str(output/'execution.json'),'status':receipt['status'],
        'development':receipt['stages'].get('development',{}).get('status'),
        'prerequisites':receipt['stages'].get('prerequisites',{}).get('status')},sort_keys=True),flush=True)
    return 0 if receipt['status'] == 'finished-bounded-attempt' else 1


if __name__ == '__main__':
    raise SystemExit(main())
