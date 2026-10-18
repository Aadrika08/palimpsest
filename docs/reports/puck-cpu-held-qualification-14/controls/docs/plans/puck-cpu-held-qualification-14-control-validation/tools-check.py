"""Compile the distinct14 templates and prove guard/collector behavior on isolated fixtures.

Never instantiates into /tmp tool paths, runs a guard, admission, observer, auditor or runtime,
and never touches the preparation02/03 stages: stage-guard cases use fixture tmpfs directories.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
VALIDATION=ROOT/'docs/plans/puck-cpu-held-qualification-14-control-validation'
TEMPLATES=['pre-admission-guard.py.in','tools/run-admission-once.py.in','tools/make-observer-guard.py','tools/run-observer-once.py.in',
    'tools/bind-audit-command.py','tools/run-audit-once.py.in','tools/collect-outcome.py.in','tools/archive-evidence.py.in','tools/instantiate.py',
    'tools/stage_guard.py']
GUARDED=['pre-admission-guard.py.in','tools/run-admission-once.py.in','tools/run-observer-once.py.in','tools/run-audit-once.py.in']
CONFIG_SHA='32f8aeb553a534b463f2b7a594ca721273fa251ae743256d6fe23efa74f6bed2'


def instantiate(name):
    return (VALIDATION/name).read_text().replace('@CONTROL@','f'*40).replace('@COUNT@','99')


def stage_guard():
    namespace={'__name__':'tools_check_stage_guard'}
    exec(compile((VALIDATION/'tools/stage_guard.py').read_bytes(),'stage_guard.py','exec'),namespace);return namespace


class ToolChecks(unittest.TestCase):
    def test_templates_compile_without_unknown_placeholders(self):
        for name in TEMPLATES:
            text=instantiate(name)
            compile(text,name,'exec')
            if name!='tools/make-observer-guard.py':self.assertNotIn('@',text,name)
            for stale in ('palimpsest-held11','qualification-11b-','qualification-11-admission-01','8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15','facc2a741315867ce98e745edd5d6692abf77603'):
                self.assertNotIn(stale,text,name)

    def test_every_one_shot_guard_checks_stage_and_boot_before_acting(self):
        for name in GUARDED:
            text=instantiate(name)
            check=text.index("stage=stage_namespace['check'](")
            self.assertIn("tools/stage_guard.py'",text,name)
            self.assertIn("subprocess.check_output(['git','show',",text[:check],name)
            acting='with Path(str(stem)' if 'tools/' in name else 'module=types.ModuleType('
            self.assertLess(check,text.index(acting),name)

    def test_stage_guard_on_tmpfs_fixture(self):
        guard=stage_guard()
        with tempfile.TemporaryDirectory(prefix='palimpsest-held14-stage-fixture-',dir='/tmp') as directory:
            stage=Path(directory)/'stage';rows=[]
            for path in (stage,stage/'inputs'):path.mkdir();path.chmod(0o700)
            for index in range(4):
                path=stage/'inputs'/('root-'+str(index).zfill(4));path.mkdir();path.chmod(0o700);state=path.stat()
                rows.append(dict(device=state.st_dev,inode=state.st_ino,root_index=index))
            observed=guard['verify'](str(stage),rows,'boot-a','boot-a')
            self.assertEqual(sorted(observed),['inputs','root-0000','root-0001','root-0002','root-0003','stage_parent'])
            with self.assertRaises(RuntimeError):guard['verify'](str(stage),rows,'boot-b','boot-a')
            with self.assertRaises(RuntimeError):guard['verify'](str(stage),[dict(rows[0],inode=rows[0]['inode']+7)]+rows[1:],'boot-a','boot-a')
            (stage/'inputs'/'root-0002').chmod(0o755)
            with self.assertRaises(RuntimeError):guard['verify'](str(stage),rows,'boot-a','boot-a')
            (stage/'inputs'/'root-0002').chmod(0o700)
            with self.assertRaises(FileNotFoundError):guard['verify'](str(Path(directory)/'lost-on-reboot'),rows,'boot-a','boot-a')
        fd=os.open(str(ROOT),os.O_RDONLY|os.O_DIRECTORY)
        try:self.assertFalse(guard['tmpfs'](fd))
        finally:os.close(fd)
        self.assertEqual((guard['BOOT'],guard['STAGE']),('7f875223-b4cf-421e-b04d-81e3c1f19460','/tmp/palimpsest-puck-cpu-held-03'))
        self.assertEqual([(r['device'],r['inode']) for r in guard['ROOTS']],[(55,43194),(55,43195),(55,43196),(55,43197)])

    def test_make_observer_guard_derives_pre_observer_guard_on_fixture(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held14-tools-',dir='/tmp') as directory:
            fixture=Path(directory)
            (fixture/'palimpsest-held14-pre-admission-guard.py').write_text(instantiate('pre-admission-guard.py.in'))
            (fixture/'palimpsest-puck-cpu-held-qualification-14-admission-01.json').write_text('{"fixture":true}\n')
            (fixture/'palimpsest-held14-independent-admission-review.json').write_text('{"decision":"GO"}\n')
            source=(VALIDATION/'tools/make-observer-guard.py').read_text()
            for line in ("source=Path('/tmp/palimpsest-held14-pre-admission-guard.py').read_text()\n",
                    "admission=Path('/tmp/palimpsest-puck-cpu-held-qualification-14-admission-01.json').read_bytes()\n",
                    "review_path=Path('/tmp/palimpsest-held14-independent-admission-review.json')\nreview_raw",
                    "path=Path('/tmp/palimpsest-held14-pre-observer-guard.py')\n"):
                self.assertEqual(source.count(line),1,line)
                source=source.replace(line,line.replace('/tmp/',str(fixture)+'/'))
            exec(compile(source,'make-observer-guard.py','exec'),{'__name__':'fixture'})
            derived=(fixture/'palimpsest-held14-pre-observer-guard.py').read_text()
        compile(derived,'pre-observer-guard.py','exec')
        for present in ('before the sole runtime observer.',"status='PASS_PRE_OBSERVER_GUARD_ONLY'",
                'absence=dict(future_output_paths=future,historical_missing_receipts=19);resources=module.resources()',
                'historical_records_unchanged=126,admission_main_invoked=True,admission_receipt_sha256=',
                "Path('/tmp/palimpsest-held14-pre-observer-guard01.json').open('x')",'assert len(future)==len(set(future))==12',
                "assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-qualification-14-admission-02.json')",
                "a['admission_check_id']==1 and a['qualification14_invoked'] is False",
                "stage=stage_namespace['check'](ROOT)","attempt11_d83dab3='NEVER_INVOKED'",
                "before=json.loads((ROOT/(BASE+'-control-validation/historical-before-admission.json')).read_bytes())"):
            self.assertEqual(derived.count(present),1,present)
        for absent in ('PASS_PRE_ADMISSION_GUARD_ONLY','absence=module.absent()','admission_main_invoked=False','@',
                "pre-admission-guard01.json').open('x')"):
            self.assertNotIn(absent,derived)

    def collect(self,fixture,observer,audit,allocation,transport_sha=CONFIG_SHA):
        """Run collect-outcome with its root and /tmp redirected into one fixture."""
        root=fixture/'root';tmp=fixture/'tmp';base=root/'docs/plans/puck-cpu-held-qualification-14-control-validation'
        for path in (tmp,base):path.mkdir(parents=True)
        (base/'historical-before-admission.json').write_text(json.dumps(dict(raw_run_files=[],preparation03_run_files=[],preparation02_run_files=[],
            historical_empty_directories=[],historical_absent_paths=[],attempt11_d83dab3_absent_outputs=[])))
        (tmp/'palimpsest-puck-cpu-held-qualification-14-admission-01.json').write_text(json.dumps(dict(status='DATA_ONLY_ADMITTED',configuration_sha256=CONFIG_SHA)))
        for phase,terminal in (('admission',dict(phase='admission',exit_code=0,outer_timeout=False)),('observer',observer),('audit',audit)):
            if terminal is not None:(tmp/('palimpsest-held14-'+phase+'-tool-terminal.json')).write_text(json.dumps(terminal))
        if allocation:
            (root/'runs/puck-cpu-held-qualification-14/logs').mkdir(parents=True)
            (root/'runs/puck-cpu-held-qualification-14/configuration.json').write_text('{}\n')
            (root/'runs/puck-cpu-held-qualification-14-external-cli-transport.json').write_text(json.dumps(dict(
                configuration_sha256=transport_sha,observed_returncode=None,timed_out=True)))
        source=instantiate('tools/collect-outcome.py.in').replace("'/tmp/","'"+str(tmp)+'/')
        source=source.replace("root=Path('/home/utkarsh/.codex/worktrees/0071/brain')","root=Path('"+str(root)+"')")
        exec(compile(source,'collect-outcome.py','exec'),{'__name__':'fixture'})
        return json.loads((tmp/'palimpsest-held14-post-outcome-observation.json').read_bytes())

    def test_collect_records_admission_refusal_without_allocation(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held14-collect-',dir='/tmp') as directory:
            value=self.collect(Path(directory),dict(phase='observer',exit_code=1,outer_timeout=False),None,allocation=False)
        self.assertEqual((value['status'],value['allocation_present'],value['independent_auditor_invocations']),('FAILED_CONSUMED',False,0))
        self.assertTrue(any(p.endswith('runs/puck-cpu-held-qualification-14') for p in value['missing_original_paths']))
        self.assertTrue(any(p.endswith('palimpsest-held14-audit-tool-terminal.json') for p in value['missing_original_paths']))
        self.assertEqual(value['stage_after']['status'],'STAGE_OR_BOOT_CHANGED')

    def test_collect_records_observer_timeout_without_audit(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held14-collect-',dir='/tmp') as directory:
            value=self.collect(Path(directory),dict(phase='observer',exit_code=None,outer_timeout=True),None,allocation=True)
        self.assertEqual((value['status'],value['allocation_present'],value['completed_four_import_receipt']),('FAILED_CONSUMED',True,False))
        self.assertTrue(any(p.endswith('runs/puck-cpu-held-qualification-14/result.json') for p in value['missing_original_paths']))

    def test_collect_refuses_a_different_configuration_sha(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held14-collect-',dir='/tmp') as directory:
            with self.assertRaises(AssertionError):
                self.collect(Path(directory),dict(phase='observer',exit_code=1,outer_timeout=False),None,allocation=True,transport_sha='0'*64)


    def passing(self,fixture,transport_elapsed=200.0,result_elapsed=210.0,import_seconds=(8.0,21.0,103.0,25.0),deadline=360):
        """A complete fixture outcome that only the epoch-14 clocks can turn into FAILED_CONSUMED."""
        root=fixture/'root';tmp=fixture/'tmp';base=root/'docs/plans/puck-cpu-held-qualification-14-control-validation';alloc=root/'runs/puck-cpu-held-qualification-14'
        for path in (tmp,base,alloc/'logs',alloc/'control'):path.mkdir(parents=True)
        (base/'historical-before-admission.json').write_text(json.dumps(dict(raw_run_files=[],preparation03_run_files=[],preparation02_run_files=[],
            historical_empty_directories=[],historical_absent_paths=[],attempt11_d83dab3_absent_outputs=[])))
        (tmp/'palimpsest-puck-cpu-held-qualification-14-admission-01.json').write_text(json.dumps(dict(status='DATA_ONLY_ADMITTED',configuration_sha256=CONFIG_SHA)))
        for phase in ('admission','observer','audit'):
            (tmp/('palimpsest-held14-'+phase+'-tool-terminal.json')).write_text(json.dumps(dict(phase=phase,exit_code=0,outer_timeout=False)))
        transport=(json.dumps(dict(configuration_sha256=CONFIG_SHA,observed_returncode=0,timed_out=False,elapsed_seconds=transport_elapsed))+'\n').encode()
        (root/'runs/puck-cpu-held-qualification-14-external-cli-transport.json').write_bytes(transport)
        audit=(json.dumps(dict(status='PASS',kind='puck-cpu-held-runtime-independent-audit-v14',configuration_sha256=CONFIG_SHA,
            transport_sha256=hashlib.sha256(transport).hexdigest()))+'\n').encode()
        for path in (tmp/'palimpsest-puck-cpu-held-qualification-14-audit-01.json',tmp/'palimpsest-held14-audit-external.stdout'):path.write_bytes(audit)
        (alloc/'result.json').write_text(json.dumps(dict(status='imports_completed',held_four_imports_observed=True,configuration_sha256=CONFIG_SHA,elapsed_seconds=result_elapsed)))
        (alloc/'control/worker-registration.json').write_text(json.dumps(dict(deadline_seconds=deadline)))
        (alloc/'logs/stdout.log').write_text(json.dumps(dict(entry_result=dict(imports=[dict(name=n,seconds=s) for n,s in zip(('numpy','torch','torchvision','mujoco'),import_seconds)]))))
        source=instantiate('tools/collect-outcome.py.in').replace("'/tmp/","'"+str(tmp)+'/')
        source=source.replace("root=Path('/home/utkarsh/.codex/worktrees/0071/brain')","root=Path('"+str(root)+"')")
        exec(compile(source,'collect-outcome.py','exec'),{'__name__':'fixture'})
        return json.loads((tmp/'palimpsest-held14-post-outcome-observation.json').read_bytes())

    def test_collect_passes_only_within_epoch14_clocks(self):
        for changes,expected in ((dict(),'AUDIT_PASS_IMPORT_ROUTE_ONLY'),(dict(transport_elapsed=401.0),'FAILED_CONSUMED'),
                (dict(result_elapsed=360.0),'FAILED_CONSUMED'),(dict(import_seconds=(8.0,21.0,103.0,361.0)),'FAILED_CONSUMED')):
            with self.subTest(changes=sorted(changes)),tempfile.TemporaryDirectory(prefix='palimpsest-held14-collect-',dir='/tmp') as directory:
                value=self.passing(Path(directory),**changes)
                self.assertEqual(value['status'],expected)
                self.assertEqual(value['epoch14_clocks']['registration_deadline_seconds'],360)

    def test_collect_refuses_a_registration_without_the_360s_clock(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held14-collect-',dir='/tmp') as directory:
            with self.assertRaises(AssertionError):self.passing(Path(directory),deadline=180)

    def test_envelope_and_wrapper_extend_only_the_observer(self):
        envelope=json.loads((ROOT/'docs/plans/puck-cpu-held-qualification-14-execution.json').read_bytes())
        self.assertEqual(envelope['normal_external_caps_seconds'],dict(admission=145,audit=145,observer=440))
        self.assertEqual(envelope['outer_term_seconds'],dict(admission=155,audit=155,observer=450))
        self.assertEqual(envelope['commands']['observer'][3],'450s')
        wrapper=(ROOT/'docs/plans/puck-cpu-held-qualification-14-external.py').read_text()
        self.assertEqual(wrapper.count("budget=440 if phase=='observer' else 145"),1)
        self.assertIn("'450s',",instantiate('tools/run-observer-once.py.in'))

if __name__=='__main__':unittest.main(verbosity=2)
