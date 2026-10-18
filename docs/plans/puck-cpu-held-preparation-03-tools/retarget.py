"""Derive the preparation03 one-shot tools from the accepted preparation02 tools once; never invoke them.

Counted replacements on the Git copies at facc2a7: paths/stage/output 02->03, audit v13 /
allocation 13 / auditor 6292b550, a required boot id, and an epoch-14 synthetic acceptance
(QUALIFY14_LIMITS, 32 absent names, hidden roster, candidate D, 360 s worker clock).
"""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
OLD='facc2a741315867ce98e745edd5d6692abf77603'
SRC='docs/plans/puck-cpu-held-preparation-02-tools/'
DST=ROOT/'docs/plans/puck-cpu-held-preparation-03-tools'
P02_SHA='04192a3ba3d7020a5399465aa6da4f7d7ebe3d74172e4b448ea500b09aa9a62b'
P03_SHA='6292b55088a8b4bfb60b2d65688970cd47e6a76e207f771c3d695dd463bae3cd'
LEGACY='19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9'
HIDDEN="['networkx','pandas','sklearn','torch.utils._cxx_pytree']"
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
PLAN={
'common.py':[
    ('one-shot preparation02 tools.','one-shot preparation03 tools.',1),
    ('preparation-02','preparation-03',9),("STAGE='/tmp/palimpsest-puck-cpu-held-02'","STAGE='/tmp/palimpsest-puck-cpu-held-03'",1),
    ('prep02','prep03',13),
    ('# Qualification11 consumes preparation02 with publication candidate D.','# Qualification14 consumes preparation03 with publication candidate D.',1),
    ("ENVIRONMENT=dict(","# Preparation03 runs on the boot that still holds preparation02's untouched stage.\nBOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'\nENVIRONMENT=dict(",1),
    ('identities preparation02 published.','identities preparation03 published.',1),
    ("audit-v12' and audit.get('version')==12","audit-v13' and audit.get('version')==13",1),
    ("and audit.get('allocation_id')==12 and","and audit.get('allocation_id')==13 and",1),
    ("'Preparation02 audit is not the accepted PASS shape'","'Preparation03 audit is not the accepted PASS shape'",1),
    ('''def epoch11(prep03,acceptance,candidate,parent):
    """A synthetic qualification11 configuration that consumes preparation02 exactly as epoch 11 will."""
    config=copy.deepcopy(prep03)
    config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,phase='qualify',
        limits=copy.deepcopy(parent.LIMITS['qualify']),''','''def epoch14(prep03,acceptance,candidate,parent):
    """A synthetic extended-clock qualification14 configuration that consumes preparation03 exactly as epoch 14 will."""
    config=copy.deepcopy(prep03)
    config.update(kind='puck-cpu-held-runtime-allocation-v14',version=14,allocation_id=14,phase='qualify',
        limits=copy.deepcopy(parent.QUALIFY14_LIMITS),''',1),
    ('"""Pure in-memory epoch-11 acceptance','"""Pure in-memory epoch-14 acceptance',1),
    ('config=epoch11(prep03,acceptance,candidate,parent)','config=epoch14(prep03,acceptance,candidate,parent)',1),
    ("    return config,dict(parent_validate_preparation_acceptance='PASS',auditor_configuration='PASS',auditor_preparation_epoch='PASS')\n",
     "    require(config['limits']==parent.QUALIFY14_LIMITS and config['limits']['normal_seconds']==360 and len(config['negative_imports'])==32,'Epoch-14 clock/roster differs')\n"
     "    require(parent.QUALIFY11_HIDDEN_IMPORTS=="+HIDDEN+",'Epoch-14 hidden roster differs')\n"
     "    return config,dict(parent_validate_preparation_acceptance='PASS',auditor_configuration='PASS',auditor_preparation_epoch='PASS',\n"
     "        epoch=14,normal_seconds=360,negative_imports=32,hidden_imports=list(parent.QUALIFY11_HIDDEN_IMPORTS))\n\n\n"
     "def prove_worker(parent,config,depraw):\n"
     "    \"\"\"Epoch-14 worker registration: policy v5, the hidden roster and the exact 360 s worker clock.\"\"\"\n"
     "    files=[row for row in config['sources'] if row['path'] in parent.WORKER_SOURCES]\n"
     "    worker,_=parent.worker_registration(files,depraw,negative_imports=config['negative_imports'],qualification_version=5,\n"
     "        hidden_imports=parent.QUALIFY11_HIDDEN_IMPORTS,deadline_seconds=parent.QUALIFY14_WORKER_SECONDS)\n"
     "    require(worker['deadline_seconds']==360 and worker['qualification']['hidden_imports']==parent.QUALIFY11_HIDDEN_IMPORTS\n"
     "        and worker['qualification']['version']==5,'Epoch-14 worker registration differs')\n"
     "    return dict(worker_registration='PASS',worker_deadline_seconds=360)\n",1)],
'preflight.py':[
    ('preparation02','preparation03',4),('Preparation02','Preparation03',2),('prep02','prep03',4),
    ("glob.glob('/tmp/palimpsest-puck-cpu-held-02*')","glob.glob('/tmp/palimpsest-puck-cpu-held-03*')",1),
    ('parent.PREPARATION02_AUDITOR_SHA256','parent.PREPARATION03_AUDITOR_SHA256',1),
    ("outcome-v12' and result.get('version')==12 and result.get('allocation_id')==12","outcome-v13' and result.get('version')==13 and result.get('allocation_id')==13",1),
    ("    os.chdir(C.ROOT)\n","    os.chdir(C.ROOT)\n    require(C.boot_id()==C.BOOT,'Boot differs from the required preparation boot '+C.BOOT)\n",1)],
'run-observer-once.py':[('preparation02','preparation03',1),('prep02','prep03',4)],
'run-audit-once.py':[('preparation02','preparation03',1),('prep02','prep03',5),
    ('accept it for a synthetic epoch-11\nconfiguration.','accept it for a synthetic extended-clock epoch-14\nconfiguration (and the parent builds its 360 s v5 worker registration).',1),
    ("        _,proof=C.prove_parent(parent,auditor,config_raw,result_raw,audit_raw,raw,paths,candidate)\n",
     "        config14,proof=C.prove_parent(parent,auditor,config_raw,result_raw,audit_raw,raw,paths,candidate)\n"
     "        proof.update(C.prove_worker(parent,config14,C.read(C.ROOT/C.OUTPUT/'payload/dependencies.json')))\n",1)],
'archive.py':[('preparation-02','preparation-03',1),('prep02','prep03',4),('preparation02','preparation03',2),
    ('a qualification11 configuration will bind them.','a qualification14 configuration will bind them.',1),
    ('config11','config14',4),
    ("    proof.update(C.prove_auditor_files(auditor,config14))\n",
     "    proof.update(C.prove_auditor_files(auditor,config14))\n    proof.update(C.prove_worker(parent,config14,C.read(C.ROOT/C.OUTPUT/'payload/dependencies.json')))\n",1)],
'validation/offline-proof.py':[('preparation02','preparation03',3),('prep02','prep03',2),('preparation-02','preparation-03',1),
    ("outcome-v12',version=12,allocation_id=12,","outcome-v13',version=13,allocation_id=13,",1),
    ("independent-audit-v12',version=12,allocation_id=12,","independent-audit-v13',version=13,allocation_id=13,",1),
    ('config11','config14',2),(P02_SHA,P03_SHA,2),
    ('def test_record_is_accepted_by_parent_and_auditor_for_epoch11','def test_record_is_accepted_by_parent_and_auditor_for_epoch14',1),
    ("            auditor_preparation_epoch='PASS',auditor_historical_acceptance='PASS'))\n",
     "            auditor_preparation_epoch='PASS',auditor_historical_acceptance='PASS',epoch=14,normal_seconds=360,negative_imports=32,\n"
     "            hidden_imports="+HIDDEN+"))\n",1),
    ("                dict(kind='puck-cpu-held-runtime-independent-audit-v1',version=1),dict(allocation_id=1)):",
     "                dict(kind='puck-cpu-held-runtime-independent-audit-v1',version=1),dict(allocation_id=1),\n"
     "                dict(auditor_source_sha256='"+P02_SHA+"'),dict(kind='puck-cpu-held-runtime-independent-audit-v12',version=12,allocation_id=12)):",1),
    ("\n\ndef dry_run_preflight():",'''
    def test_qualification11_cannot_consume_preparation03(self):
        value,raw=C.build_record(self.f.command,0,11.5,self.f.published,self.f.stdout,self.f.stderr)
        blobs=dict(configuration=self.f.config_raw,result=self.f.result_raw,independent_audit=self.f.audit_raw,externally_observed_auditor_cli=raw)
        acceptance={role:dict(path=self.f.paths[role],size_bytes=len(b),sha256=C.sha(b)) for role,b in blobs.items()}
        config=C.epoch14(self.f.parent.decode(self.f.config_raw),acceptance,self.f.candidate,self.f.parent)
        config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,limits=dict(self.f.parent.LIMITS['qualify']))
        for stage,output,message in (('/tmp/palimpsest-puck-cpu-held-03','runs/puck-cpu-held-preparation-03','preparation02 tmpfs allocation path'),
                ('/tmp/palimpsest-puck-cpu-held-02','runs/puck-cpu-held-preparation-02','Accepted CPU preparation02 required')):
            config['stage_parent']=stage;config['preparation_acceptance']['result']['path']=output+'/result.json'
            with self.assertRaisesRegex(ValueError,message):self.f.parent.validate_preparation_acceptance(config,blobs)

    def test_epoch14_worker_registration_uses_the_360s_clock(self):
        parent=C.load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','proof_worker_parent')
        config=json.loads(C.read(ROOT/C.CONFIG));config['negative_imports']=list(parent.QUALIFY11_NEGATIVE_IMPORTS)
        depraw=C.read(ROOT/'docs/reports/puck-cpu-held-preparation-01/raw/payload/dependencies.json')
        self.assertEqual(C.prove_worker(parent,config,depraw),dict(worker_registration='PASS',worker_deadline_seconds=360))
        files=[row for row in config['sources'] if row['path'] in parent.WORKER_SOURCES]
        for seconds in (180,361):
            with self.assertRaises(ValueError):
                parent.worker_registration(files,depraw,negative_imports=config['negative_imports'],qualification_version=5,
                    hidden_imports=parent.QUALIFY11_HIDDEN_IMPORTS,deadline_seconds=seconds)

    def test_preflight_requires_the_preparation_boot(self):
        text=(TOOLS/'preflight.py').read_text()
        self.assertIn("require(C.boot_id()==C.BOOT,",text)
        self.assertEqual(C.BOOT,'7f875223-b4cf-421e-b04d-81e3c1f19460')
        self.assertEqual((C.STAGE,C.OUTPUT),('/tmp/palimpsest-puck-cpu-held-03','runs/puck-cpu-held-preparation-03'))


def dry_run_preflight():''',1)]}
rows=[];outputs={}
for name,pairs in PLAN.items():
    source=SRC+('validation/offline-proof.py' if name=='validation/offline-proof.py' else name)
    old=git('show',OLD+':'+source).decode();text=old
    for a,b,count in pairs:
        assert text.count(a)==count,(name,a[:70],text.count(a))
        text=text.replace(a,b)
    for stale in ('prep02','preparation-02','held-02','preparation02','Preparation02','epoch11','epoch-11'):
        allowed=("preparation02's untouched stage","'/tmp/palimpsest-puck-cpu-held-02'","'runs/puck-cpu-held-preparation-02'",'Accepted CPU preparation02 required','preparation02 tmpfs allocation path')
        checked=text
        for phrase in allowed:checked=checked.replace(phrase,'')
        assert stale not in checked,(name,stale)
    compile(text,name,'exec');outputs[name]=text
    rows.append(dict(target=name,source='git '+OLD+':'+source,old_sha256=hashlib.sha256(old.encode()).hexdigest(),
        new_sha256=hashlib.sha256(text.encode()).hexdigest(),replacements=len(pairs)))
for name,text in outputs.items():
    path=DST/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as out:out.write(text)
print(json.dumps(dict(derived=rows,tools_invoked=False,allocation_invoked=False,stages_touched=False),indent=2,sort_keys=True))
