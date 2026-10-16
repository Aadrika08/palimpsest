from pathlib import Path
import json
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
REL='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
BASE=ROOT/REL
source=(ROOT/'docs/plans/puck-cpu-held-qualification-10-admission.py').read_text()
for a,b in [
    ('/tmp/palimpsest-puck-cpu-held-qualification-10-admission-01.json','/tmp/palimpsest-puck-cpu-held-qualification-10-admission-02.json'),
    ("ROOT/'docs/plans/puck-cpu-held-qualification-10.json'","ROOT/'"+REL+"/configuration.json'"),
    ('b7da3957cd81f017f7c59beb764577551384d54c634062f9841053c839d12915','4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170'),
    ("ROOT/'docs/plans/puck-cpu-held-qualification-10-freeze.json'","ROOT/'"+REL+"/freeze.json'"),
    ('held10-data-admission-','held10-admission02-data-admission-'),('check_id=10','check_id=2'),
    ('puck-cpu-held10-data-only-admission-v1','puck-cpu-held10-admission02-data-only-admission-v1')]:
    source=source.replace(a,b)
with (BASE/'admission.py').open('x') as out:out.write(source)
test=(ROOT/'docs/plans/puck-cpu-held-qualification-10-source-evidence/history-check.py').read_text()
test=test.replace('docs/plans/puck-cpu-held-qualification-10-admission.py',REL+'/admission.py')
test=test.replace('Thirteen unittest cases','Seventeen unittest cases')
extra='''
    def admission01(self,held):
        config=json.loads(control.CONFIGURATION.read_bytes())
        return control.check_consumed_admission01(held,config)

    def test_genuine_admission01_failure_is_consumed_without_runtime(self):
        before=len(os.listdir('/proc/self/fd'));held=auditor.Held(time.monotonic()+10)
        try:
            value=self.admission01(held)
            self.assertEqual(value['status'],'FAILED_CONSUMED')
            self.assertFalse(value['actual_runtime10_invoked'])
            self.assertFalse(value['full_payload_custody'])
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_admission01_manifest_first_raw_reservations(self):
        before=len(os.listdir('/proc/self/fd'));held=auditor.Held(time.monotonic()+10)
        try:
            rows=[dict(path=name,**row) for name,row in control.ADMISSION01_PINS.items()]
            control.hold_manifest(held,rows,set(control.ADMISSION01_PINS))
            self.assertEqual(self.admission01(held)['status'],'FAILED_CONSUMED')
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_changed_admission01_transport_is_refused(self):
        class Changed:
            def json(self,path,*args,**kwargs):
                raw=Path(path).read_bytes();value=json.loads(raw)
                if str(path).endswith('palimpsest-held10-admission-external.json'):
                    value['returncode']=0;raw=(json.dumps(value,sort_keys=True)+'\\n').encode()
                return value,raw
        with self.assertRaises(AssertionError):self.admission01(Changed())

    def test_fabricated_prior_admission_result_is_refused(self):
        held=auditor.Held(time.monotonic()+10);original=control.os.path.lexists
        try:
            control.os.path.lexists=lambda path: str(path)=='/tmp/palimpsest-puck-cpu-held-qualification-10-admission-01.json' or original(path)
            with self.assertRaises(AssertionError):self.admission01(held)
        finally:control.os.path.lexists=original;held.close()

'''
assert "\nif __name__=='__main__':" in test
test=test.replace("\nif __name__=='__main__':",'\n'+extra+"\nif __name__=='__main__':")
with (BASE/'history-check.py').open('x') as out:out.write(test)
print(json.dumps(dict(baseline_runner_created=True,history_cases=17,admission_or_runtime_invoked=False)))
