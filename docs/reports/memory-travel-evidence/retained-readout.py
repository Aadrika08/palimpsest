"""Document an interrupted publication without upgrading incomplete raw evidence."""
import json,os,sys,time
from pathlib import Path
from scripts import memory_decision_pilot as p
root=Path(sys.argv[1]).resolve();initial=p.read_json(root/'execution.json');pending=p.read_json(root/'execution.json.pending')
deadline=pending['readout_deadline_monotonic'];p.deadline_check(deadline)
result={'schema':'memory-travel-infrastructure-readout-v1','started_monotonic':time.monotonic(),
 'canonical_execution_receipt_stale':True,'pending_execution_sha256':p.file_hash(root/'execution.json.pending'),
 'status':'infrastructure-stop','selected_profile_sha256':None,'native_retries':0,
 'development_disposition':[{'job_id':'candidate-d25','status':'started-incomplete-infrastructure-failure'},
  {'job_id':'candidate-d20','status':'unattempted'},{'job_id':'candidate-d15','status':'unattempted'}],
 'prerequisite_disposition':{'attempted':[],'unattempted':[s['id'] for s in p.feasibility_specs()]},
 'raw_audit_pass':False,'scientific_task_failure_admitted':False,'qualification_claims':[],
 'r2_complete':False,'held_out_used':False,'paired_pilot':'unattempted-by-scope','owners':[]}
verified=[]
for entry in pending['artifact_index']:
 p.deadline_check(deadline)
 if entry['path']=='execution.json.pending':continue # save serialized a later version of this pending receipt
 f=root/entry['path']
 if f.stat().st_size!=entry['bytes'] or p.file_hash(f)!=entry['sha256']:raise ValueError('Indexed file changed: '+entry['path'])
 verified.append(entry['path'])
result['original_indexed_hashes_verified']=verified
result['mutable_pending_execution_excluded_from_original_hash_match']=True
plan=p.read_json(root/'development/preflight.json')
result['source_identity_unchanged']=p.source_identity(Path(plan['repo']),Path(plan['assets']))==plan['source_identity']
if not result['source_identity_unchanged']:raise ValueError('Source identity changed')
for jobfile in sorted((root/'development/jobs').glob('*.json')):
 job=p.read_json(jobfile);run=Path(job['output']);worker=p.read_json(run/'worker-report.json')
 declared=p.read_json(root/'candidates.json')['candidates'][0]
 if (job['version']!=3 or job['protocol_sha256']!=initial['protocol_sha256'] or
     job['case']!=declared['case'] or job['spec']!=declared['spec']):raise ValueError('Started owner differs from frozen first candidate')
 ident=job['run_id'];supervisor=p.read_json(root/'development/supervision'/ident/'supervisor.json')
 terminal_draft=p.read_json(root/'development/supervision'/ident/'supervisor.tmp')
 owner=p.read_json(run/'owner.json');live=False
 try:
  fields=Path(f"/proc/{owner['pid']}/stat").read_text().rsplit(')',1)[1].split()
  live=int(fields[19])==owner['starttime'] and os.getpgid(owner['pid'])==owner['pgid']
 except (FileNotFoundError,ProcessLookupError):pass
 if live:raise ValueError('Matching native owner remains active')
 row={'run_id':ident,'job_id':job['spec']['id'],'profile_sha256':job['case']['profile_sha256'],
  'owner':owner,'matching_owner_exited':True,'supervisor_canonical_status':supervisor['status'],
  'supervisor_unpublished_terminal':terminal_draft,'worker_reported_ticks':worker['total_ticks'],
  'worker_outcome':worker['outcome'],'recording_manifest_status':p.read_json(run/'recording/manifest.json')['status']}
 try:
  data=p.read_raw(run,deadline);row['readable_raw_rows']=len(data['rows'])
  p.audit_prefix_failure(job,terminal_draft,deadline)
 except Exception as error:row['audit_refusal']={'type':type(error).__name__,'message':str(error)}
 else:raise ValueError('Incomplete infrastructure failure was unexpectedly admitted')
 result['owners'].append(row)
result['retained_inventory_before_readout']=p.hash_ledger(root,deadline)
result['output_bytes_before_readout']=sum(f.stat().st_size for f in root.rglob('*') if f.is_file())
result['completed_monotonic']=time.monotonic();result['readout_deadline_monotonic']=deadline
result['conservative_readout_seconds']=result['completed_monotonic']-pending['readout_started_monotonic']
result['conservative_total_seconds']=result['completed_monotonic']-pending['phase_started_monotonic']
p.deadline_check(deadline)
(root/'readout-completion.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('retained_inventory_before_readout','original_indexed_hashes_verified')},indent=2))
