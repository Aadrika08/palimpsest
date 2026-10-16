"""Assemble distinct11 baseline controls once; no admission main, census or runtime."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess

root = Path('/home/utkarsh/.codex/worktrees/0071/brain')
base = root / 'docs/plans/puck-cpu-held-qualification-11'
proof = Path(str(base) + '-source-evidence')
amendment = root / 'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
SOURCE = '1126b710a372a82e932d08073cfc6c13308db437'
NEW11 = ['backports_abc', 'fx2trt_oss', 'hypothesis', 'onnx', 'onnx_tf', 'onnxruntime', 'tabulate',
    'tensorflow', 'tensorrt', 'torch2trt', 'tree', 'tvm', 'xarray']


def canonical(value,lf=True):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+('\n' if lf else '')).encode()


assert sorted(p.name for p in proof.iterdir()) == ['assemble.py']
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == SOURCE
# Lesson 1 (admission10-01): derive from the compact canonical amendment02 bytes, never pretty JSON.
old_raw = (amendment / 'configuration.json').read_bytes()
assert len(old_raw) == 8988 and hashlib.sha256(old_raw).hexdigest() == '4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170'
old = json.loads(old_raw)
assert canonical(old) == old_raw
config = copy.deepcopy(old)
config.update(kind='puck-cpu-held-runtime-allocation-v11', version=11, allocation_id=11,
    negative_imports=sorted(old['negative_imports'] + NEW11))
assert len(config['negative_imports']) == 32 == len(set(config['negative_imports']))
for row in config['sources']:
    raw = (root / row['path']).read_bytes()
    assert raw == subprocess.check_output(['git', 'show', SOURCE + ':' + row['path']], cwd=root)
    row.update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
assert [a['path'] for a, b in zip(old['sources'], config['sources']) if a != b] == [
    'scripts/puck_worker_bootstrap.py', 'scripts/qualify_puck_cpu_held_runtime.py',
    'src/palimpsest/puck_runtime_qualification.py']
config_raw = canonical(config)
with Path(str(base) + '.json').open('xb') as f:
    f.write(config_raw)
config_sha = hashlib.sha256(config_raw).hexdigest()
auditor_sha = hashlib.sha256((root / 'scripts/audit_puck_cpu_held_runtime.py').read_bytes()).hexdigest()


def replace(text, pairs):
    for a, b, count in pairs:
        assert text.count(a) == count, (a, text.count(a))
        text = text.replace(a, b)
    return text


admission = replace((amendment / 'admission.py').read_text(), [
    ('"""Fixed DATA-ONLY pre10 admission;', '"""Fixed DATA-ONLY pre11 admission;', 1),
    ("OUTPUT=Path('/tmp/palimpsest-puck-cpu-held-qualification-10-admission-02.json')",
     "OUTPUT=Path('/tmp/palimpsest-puck-cpu-held-qualification-11-admission-01.json')", 1),
    ("CONFIGURATION=ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json'",
     "CONFIGURATION=ROOT/'docs/plans/puck-cpu-held-qualification-11.json'", 1),
    ("CONFIG_SHA='4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170'", "CONFIG_SHA='" + config_sha + "'", 1),
    ("AUDITOR_CURRENT_SHA='7d87485b1bfcbeeb625a2fc71a59f697cdde5850dabec5a5d29bd7b7f7ac16fa'", "AUDITOR_CURRENT_SHA='" + auditor_sha + "'", 1),
    ("ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/freeze.json'",
     "ROOT/'docs/plans/puck-cpu-held-qualification-11-freeze.json'", 1),
    ("kind='held10-admission02-data-admission-phase-v1',check_id=2", "kind='held11-data-admission-phase-v1',check_id=11", 1),
    ("kind='held10-admission02-data-admission-failure-v1',check_id=2", "kind='held11-data-admission-failure-v1',check_id=11", 1),
    ("kind='puck-cpu-held10-admission02-data-only-admission-v1'", "kind='puck-cpu-held11-data-only-admission-v1'", 1),
    ("manifest['source_commit']=='e723db037ed1f790c2618798d59f56913054754f'", "manifest['source_commit']=='" + SOURCE + "'", 1),
    (",source_commit='e723db037ed1f790c2618798d59f56913054754f')", ",source_commit='" + SOURCE + "')", 1),
    ("scope='dated current10/D ", "scope='dated current11/D ", 1),
    ("assert type(names) is list and len(names)==19 ", "assert type(names) is list and len(names)==32 ", 1),
    ("paths=[ROOT/'runs/puck-cpu-held-qualification-10']+[ROOT/('runs/puck-cpu-held-qualification-10-external-cli'+suffix)",
     "paths=[ROOT/'runs/puck-cpu-held-qualification-11']+[ROOT/('runs/puck-cpu-held-qualification-11-external-cli'+suffix)", 1),
    ("paths+=[Path('/tmp/palimpsest-puck-cpu-held-qualification-10-audit-01.json'),OUTPUT]",
     "paths+=[Path('/tmp/palimpsest-puck-cpu-held-qualification-11-audit-01.json'),OUTPUT]", 1)])
compile(admission, str(base) + '-admission.py', 'exec')
with Path(str(base) + '-admission.py').open('x') as f:
    f.write(admission)

history = replace((amendment / 'history-check.py').read_text(), [
    ('''"""Prospective10 small history checks; do not run before root's safe assembly.

Only existing small07/08/09 records and authenticated Held are exercised. Never
call admission main, resource/census support, observer, auditor audit or vendors.
Seventeen unittest cases: genuine07/08, changed transports07/08, four fabricated
historical receipt absences, and combined manifest-first warm-read custody.
"""''', '''"""Prospective11 small history checks; do not run before root's safe assembly.

Only existing small07/08/09/10 records, admission10 01/02 records and authenticated
Held are exercised. Never call admission main, resource/census support, observer,
auditor audit or vendors. Twenty-six unittest cases: six genuine (07-10 and
admission10 01/02), six changed transports, eleven fabricated receipts (07-11 and
admission01/11 outputs) and three manifest-first warm-read custody checks.
"""''', 1),
    ("SOURCE=Path('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/admission.py')",
     "SOURCE=Path('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-qualification-11-admission.py')", 1),
    ("'held10_history_control'", "'held11_history_control'", 1),
    ("'held10_history_byte_holder'", "'held11_history_byte_holder'", 1),
    ("self.assertEqual(control.absent()['historical_missing_receipts'],16)", "self.assertEqual(control.absent()['historical_missing_receipts'],17)", 1),
    ("set(control.HISTORICAL07_JSON)|set(control.HISTORICAL08_JSON)|set(control.HISTORICAL09_JSON)",
     "set(control.HISTORICAL07_JSON)|set(control.HISTORICAL08_JSON)|set(control.HISTORICAL09_JSON)|set(control.HISTORICAL10_JSON)", 2),
    ("        for epoch in ('07','08','09'):\n", "        for epoch in ('07','08','09','10'):\n", 1),
    ("self.assertEqual(len(pins),29)", "self.assertEqual(len(pins),40)", 1),
    ("            self.assertEqual(control.check_consumed09(held)['status'],'FAILED_CONSUMED')\n",
     "            self.assertEqual(control.check_consumed09(held)['status'],'FAILED_CONSUMED')\n"
     "            self.assertEqual(control.check_consumed10(held)['status'],'FAILED_CONSUMED')\n", 1),
    ("prefix='held10-history-fixture-'", "prefix='held11-history-fixture-'", 1),
    ("        config=json.loads(control.CONFIGURATION.read_bytes())\n",
     "        config=self.admitted10()\n", 1)])
extra = '''
    def admitted10(self):
        # Admission01/02 bind the historical compact allocation10 values, not current11.
        path=control.ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json'
        return json.loads(path.read_bytes())

    def test_genuine10_failure_has_fail_result_but_no_success_receipt(self):
        before=len(os.listdir('/proc/self/fd'))
        held=auditor.Held(time.monotonic()+10)
        try:
            value=control.check_consumed10(held)
            self.assertEqual(value['status'],'FAILED_CONSUMED')
            self.assertTrue(value['parent_failure_result'])
            self.assertFalse(value['completed_four_import_receipt'])
            self.assertFalse(value['post_failure_full_payload_custody'])
            self.assertEqual(value['independent_audit_status'],'FAIL')
            self.assertEqual(value['missing_receipts'],['runs/puck-cpu-held-qualification-10/baseline-after.json'])
            self.assertEqual(value['first_refusal'],'Unregistered local or external dependency import: backports_abc')
            self.assertEqual(control.absent()['historical_missing_receipts'],17)
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_changed10_transport_is_refused(self):self.changed_transport('10')
    def test_fabricated10_baseline_after_is_refused(self):self.check_missing('10','baseline-after.json')
    def test_fabricated11_result_is_refused(self):self.check_missing('11','result.json')

    def test_fabricated10_success_result_is_refused(self):
        class ChangedResult:
            def json(self,path,*args,**kwargs):
                raw=Path(path).read_bytes();value=json.loads(raw)
                if str(path).endswith('runs/puck-cpu-held-qualification-10/result.json'):
                    value.update(status='imports_completed',held_four_imports_observed=True)
                    raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\\n').encode()
                return value,raw
        with self.assertRaises(AssertionError):control.check_consumed10(ChangedResult())

    def test_genuine_admission02_was_consumed_by_sole_runtime10(self):
        before=len(os.listdir('/proc/self/fd'));held=auditor.Held(time.monotonic()+10)
        try:
            value=control.check_consumed_admission02(held,self.admitted10())
            self.assertEqual(value['status'],'ADMITTED_CONSUMED_BY_RUNTIME10')
            self.assertFalse(value['current_admission_authority'])
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_admission02_manifest_first_raw_reservations(self):
        before=len(os.listdir('/proc/self/fd'));held=auditor.Held(time.monotonic()+10)
        try:
            rows=[dict(path=name,**row) for name,row in control.ADMISSION02_PINS.items()]
            control.hold_manifest(held,rows,set(control.ADMISSION02_PINS))
            value=control.check_consumed_admission02(held,self.admitted10())
            self.assertEqual(value['status'],'ADMITTED_CONSUMED_BY_RUNTIME10')
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_changed_admission02_transport_is_refused(self):
        class Changed:
            def json(self,path,*args,**kwargs):
                raw=Path(path).read_bytes();value=json.loads(raw)
                if str(path).endswith('palimpsest-held10-amendment02-admission-external.json'):
                    value['returncode']=1;raw=(json.dumps(value,sort_keys=True,indent=2)+'\\n').encode()
                return value,raw
        with self.assertRaises(AssertionError):control.check_consumed_admission02(Changed(),self.admitted10())

    def test_fabricated11_admission_receipt_is_refused(self):
        original=control.os.path.lexists
        try:
            control.os.path.lexists=lambda path: str(path)==str(control.OUTPUT) or original(path)
            with self.assertRaises(AssertionError):control.absent()
        finally:control.os.path.lexists=original

'''
assert history.count("\nif __name__=='__main__':") == 1
history = history.replace("\nif __name__=='__main__':", '\n' + extra + "\nif __name__=='__main__':")
compile(history, str(proof / 'history-check.py'), 'exec')
with (proof / 'history-check.py').open('x') as f:
    f.write(history)
print(json.dumps(dict(configuration_sha256=config_sha, configuration_bytes=len(config_raw),
    configuration_canonical_compact=True, current_auditor_sha256=auditor_sha, baseline_control_created=True,
    history_cases=26, actual11_invoked=False, admission_invoked=False)))
