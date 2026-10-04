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


def candidate_specs():
    return pilot.waypoint_specs('waypoint-development')


def run_development(plan, storage, deadline, checkpoint=None):
    specs = candidate_specs()
    report = {'stage':'waypoint-development','status':'failed','attempted':[],
        'unattempted':[s['id'] for s in specs],'selected_profile_sha256':None,'errors':[]}
    if not plan.get('geometry_valid'):
        report['errors'].append({'type':'GeometryInvalid','message':'Predeclared candidate geometry failed'})
        return report
    for index, spec in enumerate(specs):
        try:
            pilot.deadline_check(deadline)
            result = pilot.launch_owner('waypoint-development',spec,plan,storage,deadline)
            report['attempted'].append(result)
            report['unattempted'] = [s['id'] for s in specs[index+1:]]
            qualified = (result.get('status') == 'recorded' and result.get('raw_audit_pass') is True
                         and result.get('acquired') is True)
            task_failure = (result.get('status') == 'failed' and result.get('raw_audit_pass') is True
                            and result.get('retained_task_failure') is True and result.get('acquired') is False)
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
    for name in ('repo','assets','history-root','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args(argv)
    def interrupted(signum,frame):
        raise RuntimeError('External phase interruption: '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    repo = pilot.checked_path(args.repo)
    output = pilot.safe_output(args.output,pilot.source_paths(repo,args.assets,args.history_root))
    deadline = started+7200
    from palimpsest import memory_decision_world as world
    development_deadline = min(deadline-600,started+1200)
    plan = pilot.preflight(repo,args.assets,args.history_root,output/'development',output,development_deadline)
    plan.update(protocol=pilot.WAYPOINT_PROTOCOL,protocol_sha256=pilot.WAYPOINT_PROTOCOL_SHA256)
    candidates = []
    for spec in candidate_specs():
        pilot.deadline_check(development_deadline)
        case = world.make_case(spec['seed'],spec['regime'],spec['kind'],spec['mirrored'],profile_sha256=spec['profile_sha256'])
        candidates.append({'spec':spec,'profile':world.registered_profile(spec['profile_sha256']),
            'case':case,'geometry':world.geometry_check(case),'arrival_analysis':world.arrival_analysis(case)})
    plan['geometry'] = candidates
    plan['geometry_valid'] = all(c['geometry']['valid'] for c in candidates)
    storage = pilot.phase_budget(output)
    receipt = {'schema':'memory-waypoint-execution-v1','started_utc':datetime.now(timezone.utc).isoformat(),
        'output':str(output),'implementation_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
        'protocol':pilot.WAYPOINT_PROTOCOL,'protocol_sha256':pilot.WAYPOINT_PROTOCOL_SHA256,
        'source_identity':plan['source_identity'],'stage_caps':{'development':1200,'prerequisites':5400,'readout':600},
        'max_seconds':7200,'max_bytes':8*pilot.GiB,'stages':{},'detached_owner_cleanup':[],
        'qualification_claims':[],'held_out_used':False,'paired_pilot':'unattempted-by-scope',
        'r2_complete':False,'retries':0}
    with storage.lock():
        output.mkdir(parents=True,exist_ok=False)
        (output/'development').mkdir()
        pilot.write_control(output/'candidates.json',{'protocol_sha256':pilot.WAYPOINT_PROTOCOL_SHA256,'candidates':candidates},storage)
        pilot.write_control(output/'development/preflight.json',plan,storage)
        def save():
            receipt['elapsed_seconds'] = time.monotonic()-started
            pilot.write_control(output/'execution.json',receipt,storage)
        def checkpoint(report):
            receipt['detached_owner_cleanup'] = cleanup_owners(output)
            pilot.write_control(output/'development/report.json',report,storage)
            receipt['stages']['development'] = report
            save()
        save()
        try:
            report = run_development(plan,storage,development_deadline,checkpoint)
            checkpoint(report)
            selected = report['selected_profile_sha256']
            if report['status'] == 'passed':
                selected_plan = copy.deepcopy(plan)
                selected_plan.update(output=str(output/'prerequisites'),selected_profile_sha256=selected)
                selected_plan['geometry'] = []
                for spec in pilot.waypoint_specs('waypoint-feasibility',selected):
                    case = world.make_case(spec['seed'],spec['regime'],spec['kind'],spec['mirrored'],profile_sha256=selected)
                    selected_plan['geometry'].append({'id':spec['id'],'case':case,'check':world.geometry_check(case)})
                selected_plan['geometry_valid'] = all(x['check']['valid'] for x in selected_plan['geometry'])
                (output/'prerequisites').mkdir()
                pilot.write_control(output/'selected-profile.json',{'profile_sha256':selected,
                    'development_report_sha256':pilot.file_hash(output/'development/report.json')},storage)
                pilot.write_control(output/'prerequisites/preflight.json',selected_plan,storage)
                prerequisite_deadline = min(deadline-600,time.monotonic()+5400)
                prerequisites = pilot.execute_stage('waypoint-feasibility',selected_plan,storage,prerequisite_deadline)
                prerequisites['status'] = 'passed' if prerequisites['mandatory_pass'] else 'failed'
                pilot.write_control(output/'prerequisites/report.json',prerequisites,storage)
                receipt['stages']['prerequisites'] = prerequisites
            else:
                receipt['stages']['prerequisites'] = {'status':'unattempted','reason':'No independently qualified acquisition candidate',
                    'unattempted':[s['id'] for s in pilot.feasibility_specs()]}
            receipt['status'] = 'finished-bounded-attempt'
        except BaseException as error:
            receipt.update(status='execution-failed',error={'type':type(error).__name__,'message':str(error)})
        finally:
            receipt['detached_owner_cleanup'] = cleanup_owners(output)
            readout_started = time.monotonic()
            readout_deadline = min(deadline,readout_started+600)
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
