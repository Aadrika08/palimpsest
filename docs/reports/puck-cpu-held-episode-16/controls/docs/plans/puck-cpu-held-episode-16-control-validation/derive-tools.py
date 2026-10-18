"""Derive the allocation-16 guard and run-once tools from the reviewed-GO attempt-14 copies; never invoke them.

Counted file-specific edits (preparation04 stage guard, 2,104 pins, 151 records, preparation04/char-04
run files and retired stages, observer 1310 s and audit 340 s outer terms, episode transport/parent,
the allocation-16 collector and archive) followed by ordered 14->16 renames and a stale-name check.
"""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONTROL14='eb34d5c2a66730c248b00229c17ce84e197b3d68'
OLD='docs/plans/puck-cpu-held-qualification-14-control-validation/'
NEW=ROOT/'docs/plans/puck-cpu-held-episode-16-control-validation'
MERGE16='75df4dba55e435eee84d8a0f34b33967b0ac86bf'
SOURCE='cbda0d992c12320e2c9bd8a188f89d2c73d9f77e'
CONFIG16=hashlib.sha256((ROOT/'docs/plans/puck-cpu-held-episode-16.json').read_bytes()).hexdigest()
PREP04_EVIDENCE=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','4b22f2b']).decode().strip()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
COLLECT_PASS_OLD="""passed=(normal('observer') and normal('audit')
    and transport is not None and transport['observed_returncode']==0 and transport['timed_out'] is False
    and result is not None and result['status']=='imports_completed' and result['held_four_imports_observed'] is True
    and audit is not None and audit['status']=='PASS' and audit['kind']=='puck-cpu-held-runtime-independent-audit-v14')
# Review-04 Important 2: extended-clock epoch-14 bounds decide PASS; a wrong registration clock is refused.
registration=optional(allocation/'control/worker-registration.json')
assert registration is None or registration.get('deadline_seconds')==360,'Epoch-14 worker registration must carry deadline_seconds 360'
worker_receipt=None
if os.path.lexists(allocation/'logs/stdout.log'):
    worker_raw=read(allocation/'logs/stdout.log')
    try:worker_receipt=json.loads(worker_raw) if worker_raw else None
    except ValueError:worker_receipt=None
import_seconds=[row.get('seconds') for row in ((worker_receipt or {}).get('entry_result') or {}).get('imports',[])] if isinstance(worker_receipt,dict) else []
clocks=dict(parent_elapsed_below_360=result is not None and type(result.get('elapsed_seconds')) in (int,float) and 0<result['elapsed_seconds']<360,
    transport_elapsed_below_400=transport is not None and type(transport.get('elapsed_seconds')) in (int,float) and 0<transport['elapsed_seconds']<400,
    registration_deadline_seconds=None if registration is None else registration.get('deadline_seconds'),
    import_seconds=import_seconds,imports_below_360=len(import_seconds)==4 and all(type(s) in (int,float) and 0<s<360 for s in import_seconds))
passed=(passed and clocks['parent_elapsed_below_360'] and clocks['transport_elapsed_below_400']
    and clocks['registration_deadline_seconds']==360 and clocks['imports_below_360'])
status='AUDIT_PASS_IMPORT_ROUTE_ONLY' if passed else 'FAILED_CONSUMED'
"""
COLLECT_PASS_NEW="""# Allocation 16: PASS needs the accepted parent result (process attempts 0, 48 ticks, replay passed over 48 ticks without
# divergence, frozen renderer), the pinned episode auditor's PASS over exactly these bytes, and both validated bundles.
EPISODE_AUDITOR_SHA='4d8ac17f0577938ded9fa3845f0e26c1b52be8db11fa5327953c9446b156ba36'
verified=(audit or {}).get('verified') if isinstance((audit or {}).get('verified'),dict) else {}
runs=(result or {}).get('runs') if isinstance((result or {}).get('runs'),dict) else {}
replay=(result or {}).get('replay') if isinstance((result or {}).get('replay'),dict) else {}
renderer=(result or {}).get('renderer') if isinstance((result or {}).get('renderer'),dict) else {}
passed=(normal('observer') and normal('audit')
    and transport is not None and transport['observed_returncode']==0 and transport['timed_out'] is False and transport.get('phase')=='episode'
    and result is not None and result.get('status')=='episode_completed' and result.get('held_episode_observed') is True
    and not {'error','error_type'}&set(result) and result.get('process_creation_attempts')==0 and result.get('ticks_completed')==48
    and replay.get('status')=='passed' and replay.get('compared_ticks')==48 and replay.get('first_divergence') is None
    and renderer.get('vendor')=='Mesa' and 'llvmpipe' in str(renderer.get('renderer')) and renderer.get('backend')=='egl'
    and audit is not None and audit.get('status')=='PASS' and audit.get('kind')=='puck-cpu-held-episode-independent-audit-v1'
    and audit.get('auditor_source_sha256')==EPISODE_AUDITOR_SHA and verified.get('result_sha256')==hashlib.sha256(read(allocation/'result.json')).hexdigest()
    and verified.get('transport_sha256')==(None if transport_raw is None else hashlib.sha256(transport_raw).hexdigest())
    and verified.get('compared_ticks')==48 and verified.get('frames_checked')==384
    and all(verified.get(p+'_bundle_sha256')==(runs.get(p) or {}).get('bundle',{}).get('sha256') is not None for p in ('source','replay')))
# Each worker registration must carry the user-decided 600 s clock; a different clock is refused, not recorded.
registrations={p:optional(allocation/('control/worker-registration-'+p+'.json')) for p in ('source','replay')}
assert all(r is None or r.get('deadline_seconds')==600 for r in registrations.values()),'Allocation-16 worker registrations must carry deadline_seconds 600'
clocks=dict(parent_elapsed_below_1200=result is not None and type(result.get('elapsed_seconds')) in (int,float) and 0<result['elapsed_seconds']<1200,
    transport_elapsed_below_1260=transport is not None and type(transport.get('elapsed_seconds')) in (int,float) and 0<transport['elapsed_seconds']<1260,
    registration_deadline_seconds={p:None if r is None else r.get('deadline_seconds') for p,r in registrations.items()},
    supervision_status={p:None if s is None else s.get('status') for p,s in supervision.items()})
passed=(passed and clocks['parent_elapsed_below_1200'] and clocks['transport_elapsed_below_1260']
    and clocks['registration_deadline_seconds']==dict(source=600,replay=600) and clocks['supervision_status']==dict(source='completed',replay='completed'))
status='AUDIT_PASS_HELD_EPISODE_ONLY' if passed else 'FAILED_CONSUMED'
"""
SPECIFIC={
'pre-admission-guard.py.in':[("assert len(freeze['pins'])==2768","assert len(freeze['pins'])==2128",1),
    ('historical_records_unchanged=126,','historical_records_unchanged=151,',1),
    ("for row in before['preparation03_run_files']+before['preparation02_run_files']:",
     "for row in before['preparation04_run_files']+before['preparation03_run_files']+before['preparation02_run_files']+before['characterization04_run_files']:",1),
    ("assert all(not os.path.lexists(path) for path in before['attempt11_d83dab3_absent_outputs'])",
     "assert all(not os.path.lexists(path) for path in before['attempt11_d83dab3_absent_outputs'])\nassert all(not os.path.lexists(path) for path in before['retired_stage_paths'])",1),
    ("payload_census_or_rehash=False,stage_guard=stage,preparation03_run_files=len(before['preparation03_run_files']),",
     "payload_census_or_rehash=False,stage_guard=stage,preparation04_run_files=len(before['preparation04_run_files']),characterization04_run_files=len(before['characterization04_run_files']),retired_stages_absent=len(before['retired_stage_paths']),preparation03_run_files=len(before['preparation03_run_files']),",1)],
'guard-path-check.py':[],
'tools/run-admission-once.py.in':[],
'tools/run-observer-once.py.in':[("'--kill-after=5s','450s',","'--kill-after=5s','1310s',",1),('timeout=470)','timeout=1330)',1),
    ("scope='sole bounded actual runtime14 observer; no implicit retry'","scope='sole bounded allocation-16 held episode observer; no implicit retry'",1)],
'tools/run-audit-once.py.in':[("'--kill-after=5s','155s',","'--kill-after=5s','340s',",1),('timeout=170)','timeout=360)',1),
    ("scope='sole independent audit of the measured actual runtime14 transport'","scope='sole independent episode audit of the measured allocation-16 transport'",1)],
'tools/bind-audit-command.py':[("assert value['kind']=='puck-cpu-held-cli-transport-v1' and value['phase']=='qualify'",
     "assert value['kind']=='puck-cpu-held-cli-transport-v1' and value['phase']=='episode'",1),
    ("assert value['command'][4]==str(ROOT/'scripts/qualify_puck_cpu_held_runtime.py')","assert value['command'][4]==str(ROOT/'scripts/run_puck_cpu_held_episode.py')",1)],
'tools/make-observer-guard.py':[('historical_records_unchanged=126','historical_records_unchanged=151',2),
    ("a['admission_check_id']==1 and a['qualification14_invoked'] is False","a['admission_check_id']==1 and a['episode16_invoked'] is False",1)],
'tools/instantiate.py':[],
'tools/stage_guard.py':[('attempt-14 one-shot step','allocation-16 one-shot step',1),
    ("RESULT='runs/puck-cpu-held-preparation-03/result.json'","RESULT='runs/puck-cpu-held-preparation-04/result.json'",1),
    ("RESULT_SHA='c7e6c0e8baf8daf2d221b5a3510cd586fedc50de71c3bd2b21cc8c36e79dfebf'","RESULT_SHA='a76b61487a1e5c053032167f1602260a1184b6262fa86e0e62842f0a05e6ebc3'",1),
    ("STAGE='/tmp/palimpsest-puck-cpu-held-03'","STAGE='/tmp/palimpsest-puck-cpu-held-04'",1),
    ('inode=43194+index','inode=317249+index',1),('preparation03','preparation04',3),('Preparation03','Preparation04',2)],
'tools/archive-evidence.py.in':[('"""Archive terminal14 evidence only,','"""Archive terminal allocation-16 evidence only,',1),
    ("end=time.monotonic()+60","end=time.monotonic()+180",1),("total+=len(raw);assert total<=64*1024**2","total+=len(raw);assert total<=192*1024**2",1),
    ("assert post['status'] in ('FAILED_CONSUMED','AUDIT_PASS_IMPORT_ROUTE_ONLY')","assert post['status'] in ('FAILED_CONSUMED','AUDIT_PASS_HELD_EPISODE_ONLY')",1),
    ("expected_review='PASS_FAILED_OUTCOME_RECORD_NO_RUNTIME_ACCEPTANCE';assert post['completed_four_import_receipt'] is False",
     "expected_review='PASS_FAILED_OUTCOME_RECORD_NO_RUNTIME_ACCEPTANCE';assert post['completed_episode_receipt'] is False",1),
    ("    expected_review='PASS_IMPORT_ROUTE_OUTCOME_RECORD_ONLY'\n    assert post['completed_four_import_receipt'] is True and post['parent_result']['status']=='imports_completed'",
     "    expected_review='PASS_HELD_EPISODE_OUTCOME_RECORD_ONLY'\n    assert post['completed_episode_receipt'] is True and post['parent_result']['status']=='episode_completed'",1),
    ("    if revision is not None:assert raw==git('show',revision+':'+str(path.relative_to(root))),name",
     "    if revision is not None:\n        relative=str(path.relative_to(root))\n        # The fly-gym submodule's files are Git-bound at its own pinned commit.\n        assert raw==(git('-C','upstream/fly-gym','show','8d964599119b420de67ee259434d273651a1a76d:'+relative[len('upstream/fly-gym/'):]) if relative.startswith('upstream/fly-gym/') else git('show',revision+':'+relative)),name",1),
    ("auth='docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'\n"
     "sources=sorted({row['path'] for row in config['sources']}|{'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py',auth})\n"
     "assert len(sources)==27",
     "sources=sorted({row['path'] for row in config['sources']}|{'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py',\n"
     "    'scripts/audit_puck_cpu_held_episode.py','scripts/validate_palimpsest_bundle.py','scripts/audit_puck_cpu_runtime_characterization.py'})\n"
     "assert len(sources)==103",1),
    ("preparation03_evidence_commit='44e971274ca3deb10594388a8899b2cc86ec18ba'","preparation04_evidence_commit='"+PREP04_EVIDENCE+"'",1),
    ("completed_four_import_receipt=post['completed_four_import_receipt']","completed_episode_receipt=post['completed_episode_receipt']",1),
    ("A passing import-route audit is not an episode, release or operator qualification.","A passing held-episode audit is not runtime, release, operator or study qualification.",1)],
'tools/collect-outcome.py.in':[("end=time.monotonic()+45","end=time.monotonic()+120",1),
    ("raw=read(path);total+=len(raw);assert total<=32*1024**2","raw=read(path);total+=len(raw);assert total<=96*1024**2",1),
    ("result=optional(allocation/'result.json');supervision=optional(allocation/'supervision.json')",
     "result=optional(allocation/'result.json');supervision={phase:optional(allocation/(phase+'-supervision.json')) for phase in ('source','replay')}",1),
    (COLLECT_PASS_OLD,COLLECT_PASS_NEW,1),
    ("for row in before['raw_run_files']+before['preparation03_run_files']+before['preparation02_run_files']:",
     "for row in before['raw_run_files']+before['preparation04_run_files']+before['preparation03_run_files']+before['preparation02_run_files']+before['characterization04_run_files']:",1),
    ("assert len(missing)==len(set(missing)) and all(not os.path.lexists(p) for p in missing)",
     "assert len(missing)==len(set(missing)) and all(not os.path.lexists(p) for p in missing)\nassert all(not os.path.lexists(p) for p in before['retired_stage_paths'])",1),
    ("for leaf in ('result.json','baseline-after.json','supervision.json'):","for leaf in ('result.json','baseline-after.json','source-supervision.json','replay-supervision.json'):",1),
    ("for row in (supervision or {}).get('tracked_processes',[]):","for row in [r for s in supervision.values() for r in (s or {}).get('tracked_processes',[])]:",1),
    ("raw=read(allocation/'logs/stderr.log') if os.path.lexists(allocation/'logs/stderr.log') else b'';diagnostics=[];other=[]",
     "raw=b''.join(read(allocation/name/'stderr.log') for name in ('logs-source','logs-replay') if os.path.lexists(allocation/name/'stderr.log'));diagnostics=[];other=[]",1),
    ("preparation03_run_files_unchanged=len(before['preparation03_run_files']),preparation02_run_files_unchanged=len(before['preparation02_run_files']),stage_after=stage_after,epoch14_clocks=clocks,",
     "preparation04_run_files_unchanged=len(before['preparation04_run_files']),characterization04_run_files_unchanged=len(before['characterization04_run_files']),preparation03_run_files_unchanged=len(before['preparation03_run_files']),preparation02_run_files_unchanged=len(before['preparation02_run_files']),stage_after=stage_after,episode16_clocks=clocks,",1),
    ("    completed_four_import_receipt=passed,runtime_qualified=False,","    completed_episode_receipt=passed,runtime_qualified=False,",1),
    ("A passing audit is import-route evidence only, not runtime/operator/episode acceptance.","A passing audit is held-episode evidence only, not runtime/operator/collection/study acceptance.",1),
    ("limits='Terminal metadata only; no target import, installed/staged/native payload read, replay/model/study/renderer/physical acceptance.",
     "limits='Terminal metadata only; no target import or installed/staged/native payload read; run files are hashed, never executed; no model/study/physical acceptance.",1)]}
GENERIC=[('54c8b15df97f881570c6e1d6c50f1f8a4e2a45c8',MERGE16),('f05bd699af337e44de54584bb334690ec405f994',SOURCE),
    ('32f8aeb553a534b463f2b7a594ca721273fa251ae743256d6fe23efa74f6bed2',CONFIG16),
    ('research/puck-cpu-held-qualification-14','research/puck-cpu-held-episode-16'),
    ("docs/reports/puck-cpu-held-qualification-14'","docs/reports/puck-cpu-held-episode-16'"),
    ('qualification-14-control-validation','episode-16-control-validation'),('qualification-14-execution','episode-16-execution'),
    ('qualification-14-freeze','episode-16-freeze'),("puck-cpu-held-qualification-14'","puck-cpu-held-episode-16'"),
    ('runs/puck-cpu-held-qualification-14','runs/puck-cpu-held-episode-16'),
    ('palimpsest-held14-','palimpsest-held16-'),('qualification-14-','episode-16-'),('held14','held16'),
    ('qualification14','episode16'),('admission14_status','admission16_status'),('runtime14','episode16')]
rows=[];outputs={}
for name,pairs in SPECIFIC.items():
    old=git('show',CONTROL14+':'+OLD+name).decode();text=old
    assert (ROOT/OLD/name).read_text()==old,name
    for a,b,count in pairs:
        assert text.count(a)==count,(name,a[:70],text.count(a))
        text=text.replace(a,b)
    for a,b in GENERIC:text=text.replace(a,b)
    for stale in ('qualification-14','held14','runtime14','qualification14','f05bd69','32f8aeb5','54c8b15','held-03','preparation-03/result','43194','epoch14','imports_completed'):
        assert stale not in text,(name,stale)
    compile(text.replace('@CONTROL@','0'*40).replace('@COUNT@','1'),name,'exec');outputs[name]=text
    rows.append(dict(target=name,source='git '+CONTROL14+':'+OLD+name,old_sha256=hashlib.sha256(old.encode()).hexdigest(),
        new_sha256=hashlib.sha256(text.encode()).hexdigest(),specific_edits=len(pairs)))
for name,text in outputs.items():
    path=NEW/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as out:out.write(text)
print(json.dumps(dict(derived=rows,generic_renames=[a+' -> '+b for a,b in GENERIC],tools_invoked=False,admission_invoked=False,
    episode_invoked=False,stages_touched=False),indent=2,sort_keys=True))
