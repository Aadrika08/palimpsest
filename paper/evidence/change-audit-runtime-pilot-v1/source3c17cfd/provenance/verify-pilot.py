"""Post-completion engineering audit. Authoring is not execution or qualification.

Run once under separate accounted supervision; never load Torch/native/model
state. Audit CPU is a separate later charge, not part of the pilot's prior CPU.
"""
import argparse
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

SOURCE='3c17cfda8aa4cb101d93c3936fee85625cbdea7d'
ROSTER='d6777f22057f99c227a8945f00656163d79a5d70cf508aaf7ced37c651b79470'
PROJECTION='3dd036e3fe319fa6b5553ce9cbc3900014375242da0e0eb60a483615eba838ff'
PRIOR=5.412801999999999
ROOT=Path(__file__).absolute().parents[2]
BUNDLE=ROOT/'runs/change-audit-pilot-v1-20261105-source3c17cfd'
OLD=ROOT/'runs/change-audit-pilot-v1-20261105-source9e6d5cf'
GAINS=(1.,.5,.75,1.25)
MAX_BYTES=512*1024**2
SCOPE='actual-cpu-flynn-navigation-engineering-pilot'
FIRST=('cam_left','cam_right','raw_cam_left','raw_cam_right','sensors','encoded_input','raw_output')
FIELDS=set(('episode tick cam_left cam_right sensors action control pose next_pose reward simulation_time '
    'latency step_latency encoded_input raw_output raw_cam_left raw_cam_right eyes revision population_stats').split())


def need(value,message):
    if not value: raise ValueError(message)


def regular(path):
    path=Path(path).absolute()
    need(not any(p.is_symlink() for p in (path,*path.parents)) and path.is_file(),'Nonregular/symlink: '+str(path))
    return path


def sha(path):
    with regular(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path,expected=None):
    with regular(path).open('rb') as stream: payload=stream.read(2*1024**2+1)
    need(len(payload)<=2*1024**2,'Oversized JSON')
    if expected is not None: need(re.fullmatch('[0-9a-f]{64}',expected) and hashlib.sha256(payload).hexdigest()==expected,'External JSON pin differs')
    def reject(value): raise ValueError('Nonfinite JSON '+value)
    def floating(value):
        result=float(value); need(math.isfinite(result),'Nonfinite JSON overflow'); return result
    def unique(pairs):
        result={}
        for key,value in pairs:
            need(key not in result,'Duplicate JSON key'); result[key]=value
        return result
    return json.loads(payload,parse_constant=reject,parse_float=floating,object_pairs_hook=unique)


def number(value):
    need(type(value) in (int,float) and 0<=value<1e9 and math.isfinite(value),'Unknown/nonfinite CPU'); return value


def charge(account):
    need(account['accounting_complete'] is True and account['tree_drained'] is True,'Accounting/drain incomplete')
    need(account['status']=='completed' and type(account['returncode']) is int and account['returncode']==0 and account.get('errors',[])==[],'Unsuccessful accounted process')
    return number(account['subtree_cpu_seconds'])+number(account['parent_cpu_seconds'])


def inventory(base):
    rows=[]; total=0
    for directory,dirs,files in os.walk(base,followlinks=False):
        need(not any((Path(directory)/name).is_symlink() for name in dirs),'Symlink directory')
        for name in files:
            path=regular(Path(directory)/name); size=path.stat().st_size; total+=size
            need(len(rows)<4096 and total<=MAX_BYTES,'Evidence inventory exceeds cap')
            rows.append({'path':str(path.relative_to(base)),'size_bytes':size,'sha256':sha(path)})
    return sorted(rows,key=lambda row:row['path'])


def source_check():
    head=subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
    dirty=subprocess.run(['git','-C',str(ROOT),'status','--porcelain','--untracked-files=no'],check=True,capture_output=True,text=True).stdout
    need(head==SOURCE and not dirty,'Source is no longer exact clean frozen HEAD')


def audit(args):
    source_check(); pilot=BUNDLE/'pilot'
    old=read(OLD/'preparation-process-accounting.json',args.old_preparation_sha256)
    current=read(BUNDLE/'preparation-process-accounting.json',args.preparation_sha256)
    outer=read(BUNDLE/'pilot-process-accounting.json',args.outer_sha256)
    need(old['schema']==current['schema']=='change-audit-outer-preparation-accounting-v1' and outer['schema']=='change-audit-outer-pilot-accounting-v1','Outer accounting schema differs')
    need(all(outer[key] is False for key in ('sampling_eligibility_verified','certified_improvement','runtime_qualification')),'Outer claim elevated')
    old_charge,current_charge=charge(old['accounting']),charge(current['accounting'])
    need(old['charged_cpu_seconds']==old_charge and old['research_cpu_prior_seconds']==0,'Old preparation charge differs')
    need(current['charged_cpu_seconds']==current_charge and current['research_cpu_prior_seconds']==old_charge,'Current preparation chain differs')
    prior=old_charge+current_charge
    need(prior==PRIOR==current['aggregate_research_cpu_seconds']==outer['prior_cpu_seconds'],'Two-preparation prior differs')
    pilot_charge=charge(outer['accounting']); aggregate=prior+pilot_charge
    need(outer['pilot_process_cpu_seconds']==pilot_charge and outer['aggregate_audit_and_project_cpu_seconds']==aggregate and aggregate<=3600,'Outer pilot charge/cap differs')
    need(number(outer['accounting']['elapsed_seconds'])<=1800,'Outer wall cap exceeded')
    roster=read(BUNDLE/'inputs/input-roster.json',ROSTER); projection=read(BUNDLE/'inputs/namespace-projection.json',PROJECTION)
    need(read(pilot/'input-roster.json',ROSTER)==roster and read(pilot/'namespace-projection.json',PROJECTION)==projection,'Frozen input copies differ')
    need(roster['source_commit']==SOURCE and Path(roster['repo_root'])==ROOT,'Roster source differs')
    public=projection['source']; need(sha(public['path'])==public['sha256'] and regular(public['path']).stat().st_size==public['size_bytes'],'Public namespace source pin differs')
    roots=[{'root_id':f'audit-navigation-{i+1}','scenario':'reproduction','texture':'checker','seed':91001+i} for i in range(4)]
    need(projection['roots']==roots and projection['scope']=='approved-public-cohort-ids-only' and projection['protected_catalogs_read'] is False,'Frozen public root projection differs')
    for name in ('snapshots','records','velocity_gain_snapshot','velocity_gain','flynn','assets'):
        path=ROOT/'src/palimpsest'/(name+'.py'); row=next(row for row in roster['files'] if row['path']==str(path))
        need(path.stat().st_size==row['size_bytes'] and sha(path)==row['sha256'],'Audited Python source pin differs')
    sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
    import numpy as np
    snapshots=importlib.import_module('palimpsest.snapshots'); records=importlib.import_module('palimpsest.records')
    derive=importlib.import_module('palimpsest.velocity_gain_snapshot').derive_gain_snapshot
    need(not {'torch','mujoco'} & set(sys.modules),'Native/model module unexpectedly imported')
    before=inventory(pilot); present={row['path'] for row in before}
    parent=read(pilot/'parent-report.json'); terminal=read(pilot/'terminal-accounting.json')
    frozen=read(pilot/'condition-manifest.json'); admission=read(pilot/'admission-manifest.json')
    for value in (parent,terminal):
        need(value['status']=='completed' and value['accounting_complete'] is True,'Parent/terminal incomplete')
        need(value['prior_project_cpu_seconds']==prior==value['prior_audit_cpu_seconds'],'Parent prior differs')
    need(parent['errors']==[] and 0<=number(parent['phase_cpu_seconds'])<=number(terminal['phase_cpu_seconds'])<=pilot_charge+1e-6,'Parent CPU reconciliation differs')
    need(number(terminal['wall_seconds'])<=1800,'Terminal wall cap exceeded')
    for value in (parent,frozen,admission):
        need(value['source_commit']==SOURCE and value['input_roster']['sha256']==ROSTER and value['namespace_projection']['sha256']==PROJECTION,'Manifest pins differ')
        need(value['gains']==list(GAINS) and value['ticks']==64 and value['check_parity'] is False,'Manifest execution spec differs')
        need(all(value[key] is False for key in ('sampling_eligibility_verified','certified_improvement','runtime_qualification')),'Scientific flag elevated')
    jobs=parent['jobs']; need(len(jobs)==20 and frozen['condition_count']==16,'Missing/extra jobs')
    expected=[('prepare-anchor',root,1.) for root in roots]+[('execute-condition',root,gain) for root in roots for gain in GAINS]
    allowed={'admission-manifest.json','input-roster.json','namespace-projection.json','condition-manifest.json','parent-report.json','terminal-accounting.json','.palimpsest-storage.lock'}
    ledgers=[read(pilot/f'ledger-{i:03d}.json') for i in range(1,62)]
    allowed.update(f'ledger-{i:03d}.json' for i in range(1,62))
    need(ledgers[12]['kind']=='all-anchors-and-16-conditions-frozen' and ledgers[12]['manifest_sha256']==sha(pilot/'condition-manifest.json'),'Condition freeze ledger differs')
    anchors={}; first={}; results=[]; job_bases=set()
    ledger_jobs=ledgers[:12]+ledgers[13:]
    for root in roots:
        rid=root['root_id']; config=read(pilot/'configs'/(rid+'.json'),frozen['config_sha256'][rid])
        need(all(config[key]==value for key,value in root.items()) and config['ticks']==64 and config['check_parity'] is False and config['controller']=='flynn' and config['device']=='cpu','Config differs')
        need(config['input_files']==roster['files'],'Config roster differs')
        anchors[rid]=read(pilot/'anchors'/(rid+'.json'),frozen['anchor_descriptor_sha256'][rid])
        need(anchors[rid]==frozen['anchors'][rid],'Anchor descriptor differs')
        allowed.update(('configs/'+rid+'.json','anchors/'+rid+'.json'))
    for index,(job,(mode,root,gain)) in enumerate(zip(jobs,expected)):
        rid=root['root_id']; base=f'jobs/{index:02d}-{rid}-{mode}'; artifact=pilot/base/'artifacts'; job_bases.add(base)
        running,accounted,accepted=ledger_jobs[index*3:index*3+3]
        need((running['kind'],accounted['kind'],accepted['kind'])==('job-running','job-accounted','job-accepted') and accepted['job_index']==index,'Lifecycle ledger differs')
        need(accounted['job']['accounting']==job['accounting'] and all(running['job'][key]==job[key] for key in ('mode','root_id','gain','attempt','output')),'Ledger job binding differs')
        need(job['status']=='accepted' and job['attempt']==1 and (job['mode'],job['root_id'],job['gain'])==(mode,rid,gain) and job['output']==str(artifact),'Job order/identity differs')
        charge(job['accounting']); stage=read(artifact/'stage-report.json')
        need(stage['status']=='completed' and stage['actual_scope']==SCOPE and stage['errors']==[] and (stage['mode'],stage['root_id'],stage['gain'])==(mode,rid,gain),'Stage failed/identity differs')
        need(stage['check_parity'] is False and all(stage[key] is False for key in ('sampling_eligibility_verified','certified_improvement','runtime_qualification')),'Stage claim elevated')
        count=stage['ticks']; need(type(count) is int and type(stage['forward_attempts']) is int and stage['forward_attempts']==count,'Reported inference/tick counts differ')
        anchor=anchors[rid]; anchor_path=regular(anchor['path']); need(anchor_path.is_relative_to(pilot/'jobs') and anchor_path.stat().st_size<=16*1024**2 and sha(anchor_path)==anchor['file_sha256'],'Anchor ZIP differs')
        original=snapshots.read_snapshot(anchor_path); need(snapshots.state_digest(original)==anchor['state_sha256'],'Anchor typed-state differs')
        need(original['application']['seed']==root['seed'] and original['application']['total_tick']==0 and original['application']['phase']=='paused','Anchor root differs')
        allowed.update((base+'/stdout.log',base+'/stderr.log',base+'/artifacts/stage-report.json'))
        if mode=='prepare-anchor':
            need(count==0 and stage['stop_reason']=='paused_anchor_prepared' and stage['anchor']==anchor and anchor_path==artifact/'anchor.snp','Preparation not zero-forward anchor')
            allowed.add(base+'/artifacts/anchor.snp')
        else:
            need(1<=count<=64 and stage['anchor']==anchor and stage['before_first_tick_equal'] is True and stage['before_first_tick_expected_sha256']==stage['before_first_tick_observed_sha256'],'Restoration attestation differs')
            need(stage['completed_requested_ticks'] is (count==64),'Tick completion flag differs')
            need(stage['stop_reason']=='tick_limit' and count==64 or stage['stop_reason']=='natural_terminal' and type(stage.get('terminal_outcome')) is dict,'Invalid terminal prefix')
            derivation=derive(original,gain,expected_snapshot_sha256=anchor['state_sha256'])
            normalized=dict(derivation['snapshot']); normalized['application']=dict(normalized['application'])
            del normalized['application']['source_run_id']; del normalized['application']['event_prefix']
            need(snapshots.state_digest(normalized)==stage['before_first_tick_expected_sha256'],'Expected restore hash differs from full derived state')
            need(read(artifact/'derivation-receipt.json')==derivation['receipt'],'Pure derivation receipt differs')
            allowed.add(base+'/artifacts/derivation-receipt.json')
            if gain==1: need(stage['snapshot']==anchor,'Baseline did not reuse original')
            else:
                derived_path=artifact/'derived.snp'; desc=stage['snapshot']
                need(desc['path']==str(derived_path) and derived_path.stat().st_size<=16*1024**2 and sha(derived_path)==desc['file_sha256'],'Derived ZIP differs')
                digest=snapshots.state_digest(snapshots.read_snapshot(derived_path))
                need(digest==desc['state_sha256']==snapshots.state_digest(derivation['snapshot']),'Derived full state differs')
                allowed.add(base+'/artifacts/derived.snp')
        recording=artifact/'recording'; manifest=read(recording/'manifest.json')
        need(manifest['status']=='completed' and manifest['recorded_ticks']==count and manifest['total_tick']==count,'Recording/stage prefix differs')
        rows=list(records.iter_ticks(recording)); need(len(rows)==count,'Verified chunk ticks differ')
        need(sum(row['size_bytes'] for row in before if row['path'].startswith(base+'/artifacts/recording/'))<=15*1024**2,'Recording exceeds cap')
        allowed.update((base+'/artifacts/recording/manifest.json',base+'/artifacts/recording/events.jsonl'))
        allowed.update(base+f'/artifacts/recording/chunks/{chunk:06d}.npz' for chunk in range(manifest['recorded_chunks']))
        if mode=='execute-condition':
            contacts=0; maximum_error=0.
            for tick,row in enumerate(rows):
                need(set(row)==FIELDS and row['episode']==0 and row['tick']==tick,'Tick fields/cursor differs')
                need(all(np.isfinite(value).all() for key,value in row.items() if key not in ('episode','tick')),'Nonfinite recorded arrays')
                raw,action,sensors=row['raw_output'],row['action'],row['sensors']
                need(raw.dtype==action.dtype==sensors.dtype==np.dtype('float32') and raw.shape==action.shape==(2,) and sensors.shape==(4,) and sensors[0] in (0,1),'Action/sensor contract differs')
                expected_action=np.tanh(raw).astype(np.float32)*np.array([3,math.pi],dtype=np.float32); expected_action[0]*=np.float32(gain)
                need(np.allclose(action,expected_action,atol=1e-6,rtol=1e-6),'Outgoing tanh/gain action differs')
                maximum_error=max(maximum_error,float(np.max(np.abs(action-expected_action)))); contacts+=int(sensors[0])
            signature=snapshots.state_digest({key:rows[0][key] for key in FIRST})
            if gain==1: first[rid]=(signature,rows[0]['action'][1].tobytes())
            need(first[rid]==(signature,rows[0]['action'][1].tobytes()),'First-tick input/raw-output/heading differs across gains')
            fraction=contacts/count
            need(stage['engineering_observed_input_contact_fraction']==fraction and manifest['metrics']['contact_ticks']==contacts,'Independently recomputed contact fraction differs')
            if stage['stop_reason']=='natural_terminal': need(stage['terminal_outcome']==manifest['last_outcome'] and manifest['final_phase'] in ('terminated','truncated'),'Terminal outcome differs')
            else: need(manifest['final_phase']=='paused','Tick-limit phase differs')
            results.append({'root_id':rid,'gain':gain,'ticks':count,'contact_ticks':contacts,'contact_fraction':fraction,'max_action_abs_error':maximum_error,'stop_reason':stage['stop_reason']})
    extras=present-allowed
    need(all(re.fullmatch(r'jobs/\d{2}-audit-navigation-[1-4]-(?:prepare-anchor|execute-condition)/matplotlib-cache/fontlist-v\d+\.json',path) and path.split('/matplotlib-cache/')[0] in job_bases for path in extras),'Unexpected pilot artifact files')
    need(allowed<=present and sum(path.endswith('.snp') for path in present)==16,'Missing required artifacts or extra snapshots')
    source_check(); need(inventory(pilot)==before,'Pilot artifact tree changed during audit')
    need(not {'torch','mujoco'} & set(sys.modules),'Native/model module unexpectedly imported')
    controls=[OLD/'preparation-process-accounting.json',BUNDLE/'preparation-process-accounting.json',BUNDLE/'pilot-process-accounting.json',Path(__file__).absolute()]
    need([sha(path) for path in controls[:3]]==[args.old_preparation_sha256,args.preparation_sha256,args.outer_sha256],'External accounting pins changed during audit')
    rows=[{**row,'path':str(pilot/row['path'])} for row in before]+[{'path':str(path),'size_bytes':regular(path).stat().st_size,'sha256':sha(path)} for path in controls]
    return {'conditions':results,'prior_preparation_cpu_seconds':prior,'pilot_cpu_seconds':pilot_charge,'aggregate_before_this_audit_cpu_seconds':aggregate,'counted_charge_formula':'old prep(subtree+parent)+current prep(subtree+parent)+pilot(subtree+parent), once each; no inner worker or terminal re-add'},rows


def write(path,value):
    payload=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    need(len(payload)<=1024**2,'Audit output exceeds 1MiB')
    with path.open('xb') as stream: stream.write(payload); stream.flush(); os.fsync(stream.fileno())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('old-preparation-sha256','preparation-sha256','outer-sha256','output'): parser.add_argument('--'+flag,required=True)
    args=parser.parse_args(); output=Path(args.output).absolute()
    need(not output.is_relative_to(BUNDLE/'pilot') and not any(p.is_symlink() for p in (output,*output.parents)),'Unsafe audit output')
    output.mkdir(exist_ok=False)
    report={'schema':'change-audit-pilot-independent-engineering-audit-v1','status':'failed','source_commit':SOURCE,'sampling_eligibility_verified':False,'certified_improvement':False,'runtime_qualification':False,
        'scope':'NumPy/stdlib artifact, first-tick identity, action arithmetic and accounting checks only',
        'restoration_limit':'Before-first-tick native restoration equality is trusted worker hash evidence, not an independent native rerun; self-reported forward attempts are checked against recorded completed ticks.',
        'action_tolerance':{'atol':1e-6,'rtol':1e-6},'audit_cpu_charge':'External supervisor must charge this audit separately after exit; not included in input pilot prior.','errors':[]}
    try:
        results,manifest=audit(args); report.update(results,status='completed')
        write(output/'artifact-SHAmanifest.json',{'schema':'change-audit-artifact-sha-manifest-v1','pilot_root':str(BUNDLE/'pilot'),'files':manifest})
    except BaseException as error:
        report['status']='failed'; report['errors'].append({'type':type(error).__name__,'message':str(error)[:2048]})
    write(output/'audit-report.json',report)
    return 0 if report['status']=='completed' else 1


if __name__=='__main__': raise SystemExit(main())
