"""Port the reviewed-GO, consumed 11b packet to extended-clock epoch 14 on preparation03 once.

Writes the canonical epoch-14 configuration after offline acceptance, the mechanically renamed
baseline runner and the extended history checks. No admission, census, guard, observer,
auditor main or qualifier main runs; the preparation02/03 stages are never touched.
"""
from pathlib import Path
import copy,hashlib,json,subprocess,sys,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
OLD='docs/plans/puck-cpu-held-qualification-11'
NEW='docs/plans/puck-cpu-held-qualification-14'
PROOF=ROOT/(NEW+'-source-evidence')
SOURCE='f05bd699af337e44de54584bb334690ec405f994'
MERGE='54c8b15df97f881570c6e1d6c50f1f8a4e2a45c8'
CONTROL11B='27780dd5cbc096c26fb353faea7edfde878a4f74'
PREP03='docs/plans/puck-cpu-held-preparation-03.json'
ARCHIVE='docs/reports/puck-cpu-held-preparation-03/archive-record.json'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
def replace(text,pairs):
    for a,b,count in pairs:
        assert text.count(a)==count,(a[:80],text.count(a))
        text=text.replace(a,b)
    return text
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert sorted(p.name for p in PROOF.iterdir())==['port.py']
assert git('rev-parse','HEAD').decode().strip()==MERGE
for name in (OLD+'.json',OLD+'-admission.py',OLD+'-source-evidence/history-check.py'):
    assert (ROOT/name).read_bytes()==git('show',CONTROL11B+':'+name),name
parent=load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','port14_parent')
auditor=load(ROOT/'scripts/audit_puck_cpu_held_runtime.py','port14_auditor')
old_raw=(ROOT/(OLD+'.json')).read_bytes();old=json.loads(old_raw);assert parent.canonical(old)==old_raw
prep03_raw=(ROOT/PREP03).read_bytes();prep03=parent.decode(prep03_raw)
acceptance=json.loads((ROOT/ARCHIVE).read_bytes())['acceptance_pins']
blobs={}
for role,row in acceptance.items():
    raw=(ROOT/row['path']).read_bytes();assert (len(raw),sha(raw))==(row['size_bytes'],row['sha256']),role;blobs[role]=raw
assert acceptance['configuration']['sha256']==sha(prep03_raw)=='f915023564ace5cfe61bd034fc24f8ee6f33ebce0c783875b52ce2cf49def54d'
assert acceptance['result']['sha256']=='c7e6c0e8baf8daf2d221b5a3510cd586fedc50de71c3bd2b21cc8c36e79dfebf'
config=copy.deepcopy(old)
config.update(kind='puck-cpu-held-runtime-allocation-v14',version=14,allocation_id=14,limits=copy.deepcopy(parent.QUALIFY14_LIMITS),
    stage_parent=prep03['stage_parent'],sources=copy.deepcopy(prep03['sources']),preparation_acceptance=copy.deepcopy(acceptance))
for row in config['sources']:
    raw=(ROOT/row['path']).read_bytes()
    assert (len(raw),sha(raw))==(row['size_bytes'],row['sha256']) and raw==git('show',SOURCE+':'+row['path']),row['path']
assert {k for k in old if old[k]!=config[k]}=={'kind','version','allocation_id','limits','stage_parent','sources','preparation_acceptance'}
assert [a['path'] for a,b in zip(old['sources'],config['sources']) if a!=b]==['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py','src/palimpsest/puck_dependency_files.py']
assert all(config['inputs'][k]==prep03['inputs'][k] for k in config['inputs'] if k!='candidate') and config['inputs']['candidate']!=prep03['inputs']['candidate']
assert config['negative_imports']==parent.QUALIFY11_NEGATIVE_IMPORTS and len(config['negative_imports'])==32
assert (config['limits']['normal_seconds'],config['limits']['child_hard_seconds'],config['limits']['hard_seconds'])==(360,375,390)
# Review-04 Important 2: validate the epoch-14 configuration offline before any freeze.
parent.validate_configuration(config)
prior,prep=parent.validate_preparation_acceptance(config,blobs)
auditor.configuration(config,False);auditor.preparation_epoch(config,prior,prep)
held=auditor.Held(time.monotonic()+60)
try:old_prep,accepted,audit=auditor.historical_acceptance(held,config,False)
finally:held.close()
assert old_prep==prior==prep03 and accepted==prep and audit['allocation_id']==13
assert parent.allocation_output(config)==auditor.allocation_output(config)=='runs/puck-cpu-held-qualification-14'
assert parent.preparation_output(config)==auditor.preparation_output(config)=='runs/puck-cpu-held-preparation-03'
config_raw=parent.canonical(config)
with (ROOT/(NEW+'.json')).open('xb') as out:out.write(config_raw)
config_sha=sha(config_raw);auditor_sha=sha((ROOT/'scripts/audit_puck_cpu_held_runtime.py').read_bytes())
assert auditor_sha==parent.PREPARATION03_AUDITOR_SHA256
admission=replace((ROOT/(OLD+'-admission.py')).read_text(),[
    ('"""Fixed DATA-ONLY pre11b admission;','"""Fixed DATA-ONLY pre14 admission;',1),
    ("OUTPUT=Path('/tmp/palimpsest-puck-cpu-held-qualification-11b-admission-01.json')","OUTPUT=Path('/tmp/palimpsest-puck-cpu-held-qualification-14-admission-01.json')",1),
    ("CONFIGURATION=ROOT/'docs/plans/puck-cpu-held-qualification-11.json'","CONFIGURATION=ROOT/'docs/plans/puck-cpu-held-qualification-14.json'",1),
    ("CONFIG_SHA='4ab0ef1b3eab7a74d2f6dc03ab56293a65dea2d7363680b7e687aeb399d1afb5'","CONFIG_SHA='"+config_sha+"'",1),
    ("AUDITOR_CURRENT_SHA='04192a3ba3d7020a5399465aa6da4f7d7ebe3d74172e4b448ea500b09aa9a62b'","AUDITOR_CURRENT_SHA='"+auditor_sha+"'",1),
    ("ROOT/'docs/plans/puck-cpu-held-qualification-11-freeze.json'","ROOT/'docs/plans/puck-cpu-held-qualification-14-freeze.json'",1),
    ("paths=[ROOT/'runs/puck-cpu-held-qualification-11']+[ROOT/('runs/puck-cpu-held-qualification-11-external-cli'+suffix)",
     "paths=[ROOT/'runs/puck-cpu-held-qualification-14']+[ROOT/('runs/puck-cpu-held-qualification-14-external-cli'+suffix)",1),
    ("paths+=[Path('/tmp/palimpsest-puck-cpu-held-qualification-11b-audit-01.json'),OUTPUT]","paths+=[Path('/tmp/palimpsest-puck-cpu-held-qualification-14-audit-01.json'),OUTPUT]",1),
    ("kind='held11b-data-admission-phase-v1',check_id=11","kind='held14-data-admission-phase-v1',check_id=14",1),
    ("kind='held11b-data-admission-failure-v1',check_id=11","kind='held14-data-admission-failure-v1',check_id=14",1),
    ("kind='puck-cpu-held11b-data-only-admission-v1'","kind='puck-cpu-held14-data-only-admission-v1'",1),
    ("manifest['source_commit']=='8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15'","manifest['source_commit']=='"+SOURCE+"'",1),
    (",source_commit='8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15')",",source_commit='"+SOURCE+"')",1),
    ("scope='dated current11b/D on preparation02 ","scope='dated current14/D on preparation03 ",1)])
compile(admission,NEW+'-admission.py','exec')
with (ROOT/(NEW+'-admission.py')).open('x') as out:out.write(admission)
history=replace((ROOT/(OLD+'-source-evidence/history-check.py')).read_text(),[
    ('''"""Prospective11b small history checks; do not run before root's safe assembly.

Only existing small07/08/09/10 records, admission10 01/02 records, accepted
preparation02 metadata and authenticated Held are exercised. Never call admission
main, resource/census support, observer, auditor audit or vendors, and never touch
the preparation02 stage. Thirty-three unittest cases: the 26 d83dab3 cases plus
genuine preparation02 binding, preparation02 pin drift, preparation01 refusal for
epoch 11, the unexecuted d83dab3 packet and a fabricated d83dab3 receipt, and
historical empty directories with an inserted-file refusal. Fabricated and changed
cases are refused at the authenticated hash pins (immutability), not by semantics.
"""''','''"""Prospective14 small history checks; do not run before root's safe assembly.

Only existing small07-11 records, admission10 01/02 and admission11b records, accepted
preparation02/03 metadata and authenticated Held are exercised. Never call admission
main, resource/census support, observer, auditor audit or vendors, and never touch the
preparation02/03 stages. Forty-one unittest cases: the 33 11b cases (preparation checks
retargeted to preparation03/epoch 14) plus genuine/changed/fabricated runtime11, genuine,
changed and manifest-first admission11b, preparation02 consumed by runtime11 and
preparation02 refused for epoch 14. Fabricated and changed cases are refused at the
authenticated hash pins (immutability), not by semantics.
"""''',1),
    ("SOURCE=Path('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-qualification-11-admission.py')",
     "SOURCE=Path('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-qualification-14-admission.py')",1),
    ("'held11b_history_control'","'held14_history_control'",1),("'held11b_history_byte_holder'","'held14_history_byte_holder'",1),
    ("prefix='palimpsest-held11b-history-fixture-'","prefix='palimpsest-held14-history-fixture-'",1),
    ("prefix='palimpsest-held11b-empty-fixture-'","prefix='palimpsest-held14-empty-fixture-'",1),
    ("control.absent()['historical_missing_receipts'],17)","control.absent()['historical_missing_receipts'],19)",2),
    ("['directories'],35)","['directories'],41)",2),
    ("set(control.HISTORICAL09_JSON)|set(control.HISTORICAL10_JSON)","set(control.HISTORICAL09_JSON)|set(control.HISTORICAL10_JSON)|set(control.HISTORICAL11_JSON)",2),
    ("        for epoch in ('07','08','09','10'):\n","        for epoch in ('07','08','09','10','11'):\n",1),
    ("self.assertEqual(len(pins),40)","self.assertEqual(len(pins),50)",1),
    ("            self.assertEqual(control.check_consumed10(held)['status'],'FAILED_CONSUMED')\n",
     "            self.assertEqual(control.check_consumed10(held)['status'],'FAILED_CONSUMED')\n"
     "            self.assertEqual(control.check_consumed11(held)['status'],'FAILED_CONSUMED')\n",1),
    ("def test_genuine_preparation02_binds_epoch11(self):","def test_genuine_preparation03_binds_epoch14(self):",1),
    ("control.check_preparation02(held,auditor,self.current(held),self.frozen())","control.check_preparation03(held,auditor,self.current(held),self.frozen())",2),
    ("self.assertEqual(value['status'],'ACCEPTED_PREPARATION02')","self.assertEqual(value['status'],'ACCEPTED_PREPARATION03')",1),
    ("self.assertEqual(value['stage_parent'],'/tmp/palimpsest-puck-cpu-held-02')","self.assertEqual(value['stage_parent'],'/tmp/palimpsest-puck-cpu-held-03')",1),
    ("[(55,10400),(55,10401),(55,10402),(55,10403)]","[(55,43194),(55,43195),(55,43196),(55,43197)]",1),
    ("def test_preparation02_pin_drift_is_refused(self):","def test_preparation03_pin_drift_is_refused(self):",1),
    ("def test_preparation01_is_recorded_but_cannot_satisfy_epoch11(self):","def test_preparation01_is_recorded_but_cannot_satisfy_epoch14(self):",1)])
extra='''
    def admitted11(self):
        # Admission11b and runtime11 bind the historical compact 11b values, not current14.
        return json.loads((control.ROOT/'docs/plans/puck-cpu-held-qualification-11.json').read_bytes())

    def test_genuine11_failure_has_no_success_or_closure_receipt(self):self.genuine('11')
    def test_changed11_transport_is_refused(self):self.changed_transport('11')
    def test_fabricated11_baseline_after_is_refused(self):self.check_missing('11','baseline-after.json')

    def test_genuine_admission11b_was_consumed_by_sole_runtime11(self):
        before=len(os.listdir('/proc/self/fd'));held=auditor.Held(time.monotonic()+10)
        try:
            value=control.check_consumed_admission11b(held,self.admitted11())
            self.assertEqual(value['status'],'ADMITTED_CONSUMED_BY_RUNTIME11')
            self.assertFalse(value['current_admission_authority'])
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_admission11b_manifest_first_raw_reservations(self):
        before=len(os.listdir('/proc/self/fd'));held=auditor.Held(time.monotonic()+10)
        try:
            rows=[dict(path=name,**row) for name,row in control.ADMISSION11B_PINS.items()]
            control.hold_manifest(held,rows,set(control.ADMISSION11B_PINS))
            self.assertEqual(control.check_consumed_admission11b(held,self.admitted11())['status'],'ADMITTED_CONSUMED_BY_RUNTIME11')
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_changed_admission11b_transport_is_refused(self):
        class Changed:
            def json(self,path,*args,**kwargs):
                raw=Path(path).read_bytes();value=json.loads(raw)
                if str(path).endswith('palimpsest-held11b-admission-external.json'):
                    value['returncode']=1;raw=(json.dumps(value,sort_keys=True,indent=2)+'\\n').encode()
                return value,raw
        with self.assertRaises(AssertionError):control.check_consumed_admission11b(Changed(),self.admitted11())

    def test_preparation02_was_accepted_and_consumed_by_runtime11(self):
        before=len(os.listdir('/proc/self/fd'));held=auditor.Held(time.monotonic()+10)
        try:
            value=control.check_preparation02_consumed(held)
            self.assertEqual((value['status'],value['stage_inspected']),('ACCEPTED_CONSUMED_BY_RUNTIME11',False))
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_preparation02_cannot_satisfy_epoch14(self):
        held=auditor.Held(time.monotonic()+30)
        try:
            current=self.current(held)
            prior=json.loads((control.ROOT/'docs/plans/puck-cpu-held-preparation-02.json').read_bytes())
            prep=json.loads((control.ROOT/'runs/puck-cpu-held-preparation-02/result.json').read_bytes())
            with self.assertRaises(ValueError):current.preparation_epoch(self.frozen(),prior,prep)
        finally:held.close()

'''
assert history.count("\nif __name__=='__main__':")==1
history=history.replace("\nif __name__=='__main__':",'\n'+extra+"\nif __name__=='__main__':")
compile(history,'history-check.py','exec')
with (PROOF/'history-check.py').open('x') as out:out.write(history)
print(json.dumps(dict(configuration=dict(size_bytes=len(config_raw),sha256=config_sha),
    configuration_delta_vs_11b=['kind','version','allocation_id','limits (QUALIFY14 360/375/390)','stage_parent','sources (bootstrap, qualifier, puck_dependency_files)','preparation_acceptance'],
    offline_acceptance=dict(parent_validate_configuration='PASS',parent_validate_preparation_acceptance='PASS',
        auditor_configuration='PASS',auditor_preparation_epoch='PASS',auditor_historical_acceptance='PASS'),
    current_auditor_sha256=auditor_sha,history_cases=41,admission_or_runtime_invoked=False,stages_touched=False),indent=2,sort_keys=True))
