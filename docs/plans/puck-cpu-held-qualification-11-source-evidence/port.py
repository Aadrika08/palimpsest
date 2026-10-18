"""Port the unexecuted d83dab3 attempt-11 packet onto preparation02 once (attempt 11b).

Writes the canonical epoch-11 configuration after offline acceptance, the mechanically
renamed baseline runner and the extended history checks. No admission, census, guard,
observer, auditor main or qualifier main runs; the preparation02 stage is never touched.
"""
from pathlib import Path
import copy,hashlib,json,subprocess,sys,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='docs/plans/puck-cpu-held-qualification-11'
PROOF=ROOT/(BASE+'-source-evidence')
OLD='d83dab3c92387c80e81af528fea25dd3f8931598'
SOURCE='8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15'
EVIDENCE='facc2a7'
PREP02='docs/plans/puck-cpu-held-preparation-02.json'
ARCHIVE='docs/reports/puck-cpu-held-preparation-02/archive-record.json'
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
assert subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',EVIDENCE,'HEAD']).returncode==0
assert git('rev-parse','HEAD').decode().strip()==git('rev-parse',EVIDENCE).decode().strip()
parent=load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','port11b_parent')
auditor=load(ROOT/'scripts/audit_puck_cpu_held_runtime.py','port11b_auditor')
old_raw=git('show',OLD+':'+BASE+'.json');old=json.loads(old_raw);assert parent.canonical(old)==old_raw
prep02_raw=(ROOT/PREP02).read_bytes();prep02=parent.decode(prep02_raw)
acceptance=json.loads((ROOT/ARCHIVE).read_bytes())['acceptance_pins']
blobs={}
for role,row in acceptance.items():
    raw=(ROOT/row['path']).read_bytes();assert (len(raw),sha(raw))==(row['size_bytes'],row['sha256']),role;blobs[role]=raw
assert acceptance['configuration']['sha256']==sha(prep02_raw)=='1acfb10b40d561b8e56c96f4cd0d59ee1f00b4d0a14f62c80ffe64e22e1de3ed'
assert acceptance['result']['sha256']=='4ef13965e6f312a0bcdef9c49e57190f6a9526988f20f1959357bcc31400e0d4'
config=copy.deepcopy(old)
config.update(stage_parent=prep02['stage_parent'],sources=copy.deepcopy(prep02['sources']),preparation_acceptance=copy.deepcopy(acceptance))
for row in config['sources']:
    raw=(ROOT/row['path']).read_bytes()
    assert (len(raw),sha(raw))==(row['size_bytes'],row['sha256']) and raw==git('show',SOURCE+':'+row['path']),row['path']
assert {k for k in old if old[k]!=config[k]}=={'stage_parent','sources','preparation_acceptance'}
assert [a['path'] for a,b in zip(old['sources'],config['sources']) if a!=b]==['scripts/qualify_puck_cpu_held_runtime.py']
assert all(config['inputs'][k]==prep02['inputs'][k] for k in config['inputs'] if k!='candidate') and config['inputs']['candidate']!=prep02['inputs']['candidate']
assert config['negative_imports']==parent.QUALIFY11_NEGATIVE_IMPORTS and config['limits']==parent.LIMITS['qualify']
# Review-02 Important 2: validate the epoch-11 configuration offline before any freeze.
parent.validate_configuration(config)
prior,prep=parent.validate_preparation_acceptance(config,blobs)
auditor.configuration(config,False);auditor.preparation_epoch(config,prior,prep)
held=auditor.Held(time.monotonic()+60)
try:old_prep,accepted,audit=auditor.historical_acceptance(held,config,False)
finally:held.close()
assert old_prep==prior==prep02 and accepted==prep and audit['allocation_id']==12
assert parent.allocation_output(config)==auditor.allocation_output(config)=='runs/puck-cpu-held-qualification-11'
assert parent.preparation_output(config)==auditor.preparation_output(config)=='runs/puck-cpu-held-preparation-02'
config_raw=parent.canonical(config)
with (ROOT/(BASE+'.json')).open('xb') as out:out.write(config_raw)
config_sha=sha(config_raw);auditor_sha=sha((ROOT/'scripts/audit_puck_cpu_held_runtime.py').read_bytes())
assert auditor_sha==parent.PREPARATION02_AUDITOR_SHA256
admission=replace(git('show',OLD+':'+BASE+'-admission.py').decode(),[
    ('"""Fixed DATA-ONLY pre11 admission;','"""Fixed DATA-ONLY pre11b admission;',1),
    ("OUTPUT=Path('/tmp/palimpsest-puck-cpu-held-qualification-11-admission-01.json')",
     "OUTPUT=Path('/tmp/palimpsest-puck-cpu-held-qualification-11b-admission-01.json')",1),
    ("CONFIG_SHA='6e28bef8bebd6daecfdf34e762584312f984e0d77c7a822a119e0c89e136b212'","CONFIG_SHA='"+config_sha+"'",1),
    ("AUDITOR_CURRENT_SHA='62ab513d03d0edb0f6a24910ade7f0e56be1aeaa72c94d4d73ae989570ee5515'","AUDITOR_CURRENT_SHA='"+auditor_sha+"'",1),
    ("paths+=[Path('/tmp/palimpsest-puck-cpu-held-qualification-11-audit-01.json'),OUTPUT]",
     "paths+=[Path('/tmp/palimpsest-puck-cpu-held-qualification-11b-audit-01.json'),OUTPUT]",1),
    ("kind='held11-data-admission-phase-v1',check_id=11","kind='held11b-data-admission-phase-v1',check_id=11",1),
    ("kind='held11-data-admission-failure-v1',check_id=11","kind='held11b-data-admission-failure-v1',check_id=11",1),
    ("kind='puck-cpu-held11-data-only-admission-v1'","kind='puck-cpu-held11b-data-only-admission-v1'",1),
    ("manifest['source_commit']=='1126b710a372a82e932d08073cfc6c13308db437'","manifest['source_commit']=='"+SOURCE+"'",1),
    (",source_commit='1126b710a372a82e932d08073cfc6c13308db437')",",source_commit='"+SOURCE+"')",1),
    ("scope='dated current11/D ","scope='dated current11b/D on preparation02 ",1)])
compile(admission,BASE+'-admission.py','exec')
with (ROOT/(BASE+'-admission.py')).open('x') as out:out.write(admission)
history=replace(git('show',OLD+':'+BASE+'-source-evidence/history-check.py').decode(),[
    ('''"""Prospective11 small history checks; do not run before root's safe assembly.

Only existing small07/08/09/10 records, admission10 01/02 records and authenticated
Held are exercised. Never call admission main, resource/census support, observer,
auditor audit or vendors. Twenty-six unittest cases: six genuine (07-10 and
admission10 01/02), six changed transports, eleven fabricated receipts (07-11 and
admission01/11 outputs) and three manifest-first warm-read custody checks.
"""''','''"""Prospective11b small history checks; do not run before root's safe assembly.

Only existing small07/08/09/10 records, admission10 01/02 records, accepted
preparation02 metadata and authenticated Held are exercised. Never call admission
main, resource/census support, observer, auditor audit or vendors, and never touch
the preparation02 stage. Thirty-three unittest cases: the 26 d83dab3 cases plus
genuine preparation02 binding, preparation02 pin drift, preparation01 refusal for
epoch 11, the unexecuted d83dab3 packet and a fabricated d83dab3 receipt, and
historical empty directories with an inserted-file refusal. Fabricated and changed
cases are refused at the authenticated hash pins (immutability), not by semantics.
"""''',1),
    ("'held11_history_control'","'held11b_history_control'",1),
    ("'held11_history_byte_holder'","'held11b_history_byte_holder'",1),
    ("prefix='held11-history-fixture-'","prefix='palimpsest-held11b-history-fixture-'",1)])
extra='''
    def current(self,held):
        return control.module(held,control.ROOT/'scripts/audit_puck_cpu_held_runtime.py',control.AUDITOR_CURRENT_SHA)

    def frozen(self):
        return json.loads(control.CONFIGURATION.read_bytes())

    def test_genuine_preparation02_binds_epoch11(self):
        before=len(os.listdir('/proc/self/fd'));held=auditor.Held(time.monotonic()+30)
        try:
            value=control.check_preparation02(held,auditor,self.current(held),self.frozen())[-1]
            self.assertEqual(value['status'],'ACCEPTED_PREPARATION02')
            self.assertEqual(value['stage_parent'],'/tmp/palimpsest-puck-cpu-held-02')
            self.assertEqual([(r['device'],r['inode']) for r in value['staged_roots']],[(55,10400),(55,10401),(55,10402),(55,10403)])
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_preparation02_pin_drift_is_refused(self):
        held=auditor.Held(time.monotonic()+30);original=control.RESULT_SHA
        try:
            control.RESULT_SHA='0'*64
            with self.assertRaises(AssertionError):control.check_preparation02(held,auditor,self.current(held),self.frozen())
        finally:control.RESULT_SHA=original;held.close()

    def test_preparation01_is_recorded_but_cannot_satisfy_epoch11(self):
        value=control.record_preparation01()
        self.assertEqual((value['status'],value['required']),('ACCEPTED_SUPERSEDED_STAGE_LOST',False))
        held=auditor.Held(time.monotonic()+30)
        try:
            current=self.current(held)
            prior=json.loads((control.ROOT/'docs/plans/puck-cpu-held-preparation-01.json').read_bytes())
            prep=json.loads((control.ROOT/'runs/puck-cpu-held-preparation-01/result.json').read_bytes())
            with self.assertRaises(ValueError):current.preparation_epoch(self.frozen(),prior,prep)
        finally:held.close()

    def test_unexecuted_d83dab3_packet_is_recorded_never_invoked(self):
        held=auditor.Held(time.monotonic()+30)
        try:
            value=control.check_unexecuted11(held)
            self.assertEqual((value['status'],value['control_commit']),('NEVER_INVOKED','d83dab3c92387c80e81af528fea25dd3f8931598'))
        finally:held.close()

    def test_fabricated_d83dab3_receipt_is_refused(self):
        held=auditor.Held(time.monotonic()+30);original=control.os.path.lexists
        try:
            control.os.path.lexists=lambda path: str(path)=='/tmp/palimpsest-puck-cpu-held-qualification-11-admission-01.json' or original(path)
            with self.assertRaises(AssertionError):control.check_unexecuted11(held)
        finally:control.os.path.lexists=original;held.close()

    def test_historical_empty_directories_remain_empty(self):
        self.assertEqual(control.check_empty_directories()['directories'],35)

    def test_inserted_file_in_historical_empty_directory_is_refused(self):
        original=control.ROOT
        try:
            with tempfile.TemporaryDirectory(prefix='palimpsest-held11b-empty-fixture-') as directory:
                control.ROOT=Path(directory)
                for name in control.EMPTY_DIRECTORIES:(control.ROOT/name).mkdir(parents=True)
                self.assertEqual(control.check_empty_directories()['directories'],35)
                (control.ROOT/control.EMPTY_DIRECTORIES[0]/'fabricated.json').write_bytes(b'{}\\n')
                with self.assertRaises(AssertionError):control.check_empty_directories()
        finally:control.ROOT=original

'''
assert history.count("\nif __name__=='__main__':")==1
history=history.replace("\nif __name__=='__main__':",'\n'+extra+"\nif __name__=='__main__':")
compile(history,'history-check.py','exec')
with (PROOF/'history-check.py').open('x') as out:out.write(history)
print(json.dumps(dict(configuration=dict(size_bytes=len(config_raw),sha256=config_sha),
    configuration_delta_vs_d83dab3=['stage_parent','sources (qualifier row)','preparation_acceptance'],
    offline_acceptance=dict(parent_validate_configuration='PASS',parent_validate_preparation_acceptance='PASS',
        auditor_configuration='PASS',auditor_preparation_epoch='PASS',auditor_historical_acceptance='PASS'),
    current_auditor_sha256=auditor_sha,history_cases=33,admission_or_runtime_invoked=False,stage_touched=False),indent=2,sort_keys=True))
