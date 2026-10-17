"""Derive the attempt-14 guard and run-once tools from the reviewed-GO 11b copies; never invoke them.

Counted file-specific edits (preparation03 stage guard, 2,768 pins, 126 records, observer 450s outer
term, epoch-14 collector clocks) followed by ordered 11b->14 renames with a stale-name check.
"""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONTROL11B='27780dd5cbc096c26fb353faea7edfde878a4f74'
OLD='docs/plans/puck-cpu-held-qualification-11-control-validation/'
NEW=ROOT/'docs/plans/puck-cpu-held-qualification-14-control-validation'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
MERGE=git('rev-parse','54c8b15').decode().strip()
PREP03_EVIDENCE=git('rev-parse','44e9712').decode().strip()
SPECIFIC={
'pre-admission-guard.py.in':[("assert len(freeze['pins'])==2463","assert len(freeze['pins'])==2768",1),
    ('historical_records_unchanged=103,','historical_records_unchanged=126,',1),
    ("for row in before['preparation02_run_files']:","for row in before['preparation03_run_files']+before['preparation02_run_files']:",1),
    ("payload_census_or_rehash=False,stage_guard=stage,preparation02_run_files=len(before['preparation02_run_files']),",
     "payload_census_or_rehash=False,stage_guard=stage,preparation03_run_files=len(before['preparation03_run_files']),preparation02_run_files=len(before['preparation02_run_files']),",1)],
'guard-path-check.py':[],
'tools/run-admission-once.py.in':[],
'tools/run-observer-once.py.in':[("'--kill-after=5s','250s',","'--kill-after=5s','450s',",1),('timeout=270)','timeout=470)',1)],
'tools/run-audit-once.py.in':[],
'tools/bind-audit-command.py':[],
'tools/make-observer-guard.py':[('historical_missing_receipts=17','historical_missing_receipts=19',1),('historical_records_unchanged=103','historical_records_unchanged=126',2)],
'tools/instantiate.py':[],
'tools/stage_guard.py':[('attempt-11b one-shot step','attempt-14 one-shot step',1),
    ("RESULT='runs/puck-cpu-held-preparation-02/result.json'","RESULT='runs/puck-cpu-held-preparation-03/result.json'",1),
    ("RESULT_SHA='4ef13965e6f312a0bcdef9c49e57190f6a9526988f20f1959357bcc31400e0d4'","RESULT_SHA='c7e6c0e8baf8daf2d221b5a3510cd586fedc50de71c3bd2b21cc8c36e79dfebf'",1),
    ("STAGE='/tmp/palimpsest-puck-cpu-held-02'","STAGE='/tmp/palimpsest-puck-cpu-held-03'",1),
    ('inode=10400+index','inode=43194+index',1),('preparation02','preparation03',3),('Preparation02','Preparation03',2)],
'tools/archive-evidence.py.in':[("preparation02_evidence_commit='facc2a741315867ce98e745edd5d6692abf77603'","preparation03_evidence_commit='"+PREP03_EVIDENCE+"'",1),
    ('"""Archive terminal11 (packet 11b) evidence only,','"""Archive terminal14 evidence only,',1)],
'tools/collect-outcome.py.in':[
    ("for row in before['raw_run_files']+before['preparation02_run_files']:","for row in before['raw_run_files']+before['preparation03_run_files']+before['preparation02_run_files']:",1),
    ("preparation02_run_files_unchanged=len(before['preparation02_run_files']),",
     "preparation03_run_files_unchanged=len(before['preparation03_run_files']),preparation02_run_files_unchanged=len(before['preparation02_run_files']),",1),
    ("audit['kind']=='puck-cpu-held-runtime-independent-audit-v11'","audit['kind']=='puck-cpu-held-runtime-independent-audit-v14'",1),
    ("status='AUDIT_PASS_IMPORT_ROUTE_ONLY' if passed else 'FAILED_CONSUMED'\n",
     "# Review-04 Important 2: extended-clock epoch-14 bounds decide PASS; a wrong registration clock is refused.\n"
     "registration=optional(allocation/'control/worker-registration.json')\n"
     "assert registration is None or registration.get('deadline_seconds')==360,'Epoch-14 worker registration must carry deadline_seconds 360'\n"
     "worker_receipt=None\n"
     "if os.path.lexists(allocation/'logs/stdout.log'):\n"
     "    worker_raw=read(allocation/'logs/stdout.log')\n"
     "    try:worker_receipt=json.loads(worker_raw) if worker_raw else None\n"
     "    except ValueError:worker_receipt=None\n"
     "import_seconds=[row.get('seconds') for row in ((worker_receipt or {}).get('entry_result') or {}).get('imports',[])] if isinstance(worker_receipt,dict) else []\n"
     "clocks=dict(parent_elapsed_below_360=result is not None and type(result.get('elapsed_seconds')) in (int,float) and 0<result['elapsed_seconds']<360,\n"
     "    transport_elapsed_below_400=transport is not None and type(transport.get('elapsed_seconds')) in (int,float) and 0<transport['elapsed_seconds']<400,\n"
     "    registration_deadline_seconds=None if registration is None else registration.get('deadline_seconds'),\n"
     "    import_seconds=import_seconds,imports_below_360=len(import_seconds)==4 and all(type(s) in (int,float) and 0<s<360 for s in import_seconds))\n"
     "passed=(passed and clocks['parent_elapsed_below_360'] and clocks['transport_elapsed_below_400']\n"
     "    and clocks['registration_deadline_seconds']==360 and clocks['imports_below_360'])\n"
     "status='AUDIT_PASS_IMPORT_ROUTE_ONLY' if passed else 'FAILED_CONSUMED'\n",1),
    ('stage_after=stage_after,','stage_after=stage_after,epoch14_clocks=clocks,',1)]}
GENERIC=[('facc2a741315867ce98e745edd5d6692abf77603',MERGE),('8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15','f05bd699af337e44de54584bb334690ec405f994'),
    ('4ab0ef1b3eab7a74d2f6dc03ab56293a65dea2d7363680b7e687aeb399d1afb5','32f8aeb553a534b463f2b7a594ca721273fa251ae743256d6fe23efa74f6bed2'),
    ('research/puck-cpu-held-qualification-11b','research/puck-cpu-held-qualification-14'),
    ("docs/reports/puck-cpu-held-qualification-11b'","docs/reports/puck-cpu-held-qualification-14'"),
    ('qualification-11-control-validation','qualification-14-control-validation'),('qualification-11-execution','qualification-14-execution'),
    ('qualification-11-freeze','qualification-14-freeze'),("puck-cpu-held-qualification-11'","puck-cpu-held-qualification-14'"),
    ('runs/puck-cpu-held-qualification-11','runs/puck-cpu-held-qualification-14'),
    ('palimpsest-held11b-','palimpsest-held14-'),('qualification-11b-','qualification-14-'),('held11b','held14'),
    ('qualification11b','qualification14'),('admission11b_status','admission14_status'),
    ('qualification11_invoked','qualification14_invoked'),('runtime11','runtime14')]
rows=[];outputs={}
for name,pairs in SPECIFIC.items():
    old=git('show',CONTROL11B+':'+OLD+name).decode();text=old
    assert (ROOT/OLD/name).read_text()==old,name
    for a,b,count in pairs:
        assert text.count(a)==count,(name,a[:60],text.count(a))
        text=text.replace(a,b)
    for a,b in GENERIC:text=text.replace(a,b)
    for stale in ('11b','qualification-11','held11','facc2a7','8f3a138','4ab0ef1b','runtime11','held-02','preparation-02/result'):
        assert stale not in text,(name,stale)
    compile(text.replace('@CONTROL@','0'*40).replace('@COUNT@','1'),name,'exec');outputs[name]=text
    rows.append(dict(target=name,source='git '+CONTROL11B+':'+OLD+name,old_sha256=hashlib.sha256(old.encode()).hexdigest(),
        new_sha256=hashlib.sha256(text.encode()).hexdigest(),specific_edits=len(pairs)))
for name,text in outputs.items():
    path=NEW/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as out:out.write(text)
print(json.dumps(dict(derived=rows,generic_renames=[a+' -> '+b for a,b in GENERIC],tools_invoked=False,admission_invoked=False,
    runtime_invoked=False,stages_touched=False),indent=2,sort_keys=True))
