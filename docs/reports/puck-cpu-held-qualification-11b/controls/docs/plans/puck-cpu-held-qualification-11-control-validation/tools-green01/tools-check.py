"""Compile the distinct11b templates and prove guard/collector behavior on isolated fixtures.

Never instantiates into /tmp tool paths, runs a guard, admission, observer, auditor or runtime,
and never touches the preparation02 stage: stage-guard cases use fixture tmpfs directories.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
VALIDATION=ROOT/'docs/plans/puck-cpu-held-qualification-11-control-validation'
TEMPLATES=['pre-admission-guard.py.in','tools/run-admission-once.py.in','tools/make-observer-guard.py','tools/run-observer-once.py.in',
    'tools/bind-audit-command.py','tools/run-audit-once.py.in','tools/collect-outcome.py.in','tools/archive-evidence.py.in','tools/instantiate.py',
    'tools/stage_guard.py']
GUARDED=['pre-admission-guard.py.in','tools/run-admission-once.py.in','tools/run-observer-once.py.in','tools/run-audit-once.py.in']
CONFIG_SHA='4ab0ef1b3eab7a74d2f6dc03ab56293a65dea2d7363680b7e687aeb399d1afb5'


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
            for stale in ('palimpsest-held11-','qualification-11-admission-01','qualification-11-audit-01','1126b710a372a82e932d08073cfc6c13308db437'):
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
        with tempfile.TemporaryDirectory(prefix='palimpsest-held11b-stage-fixture-',dir='/tmp') as directory:
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
        self.assertEqual((guard['BOOT'],guard['STAGE']),('7f875223-b4cf-421e-b04d-81e3c1f19460','/tmp/palimpsest-puck-cpu-held-02'))
        self.assertEqual([(r['device'],r['inode']) for r in guard['ROOTS']],[(55,10400),(55,10401),(55,10402),(55,10403)])

    def test_make_observer_guard_derives_pre_observer_guard_on_fixture(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held11b-tools-',dir='/tmp') as directory:
            fixture=Path(directory)
            (fixture/'palimpsest-held11b-pre-admission-guard.py').write_text(instantiate('pre-admission-guard.py.in'))
            (fixture/'palimpsest-puck-cpu-held-qualification-11b-admission-01.json').write_text('{"fixture":true}\n')
            (fixture/'palimpsest-held11b-independent-admission-review.json').write_text('{"decision":"GO"}\n')
            source=(VALIDATION/'tools/make-observer-guard.py').read_text()
            for line in ("source=Path('/tmp/palimpsest-held11b-pre-admission-guard.py').read_text()\n",
                    "admission=Path('/tmp/palimpsest-puck-cpu-held-qualification-11b-admission-01.json').read_bytes()\n",
                    "review_path=Path('/tmp/palimpsest-held11b-independent-admission-review.json')\nreview_raw",
                    "path=Path('/tmp/palimpsest-held11b-pre-observer-guard.py')\n"):
                self.assertEqual(source.count(line),1,line)
                source=source.replace(line,line.replace('/tmp/',str(fixture)+'/'))
            exec(compile(source,'make-observer-guard.py','exec'),{'__name__':'fixture'})
            derived=(fixture/'palimpsest-held11b-pre-observer-guard.py').read_text()
        compile(derived,'pre-observer-guard.py','exec')
        for present in ('before the sole runtime observer.',"status='PASS_PRE_OBSERVER_GUARD_ONLY'",
                'absence=dict(future_output_paths=future,historical_missing_receipts=17);resources=module.resources()',
                'historical_records_unchanged=103,admission_main_invoked=True,admission_receipt_sha256=',
                "Path('/tmp/palimpsest-held11b-pre-observer-guard01.json').open('x')",'assert len(future)==len(set(future))==12',
                "assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-qualification-11b-admission-02.json')",
                "a['admission_check_id']==1 and a['qualification11_invoked'] is False",
                "stage=stage_namespace['check'](ROOT)","attempt11_d83dab3='NEVER_INVOKED'",
                "before=json.loads((ROOT/(BASE+'-control-validation/historical-before-admission.json')).read_bytes())"):
            self.assertEqual(derived.count(present),1,present)
        for absent in ('PASS_PRE_ADMISSION_GUARD_ONLY','absence=module.absent()','admission_main_invoked=False','@',
                "pre-admission-guard01.json').open('x')"):
            self.assertNotIn(absent,derived)

    def collect(self,fixture,observer,audit,allocation,transport_sha=CONFIG_SHA):
        """Run collect-outcome with its root and /tmp redirected into one fixture."""
        root=fixture/'root';tmp=fixture/'tmp';base=root/'docs/plans/puck-cpu-held-qualification-11-control-validation'
        for path in (tmp,base):path.mkdir(parents=True)
        (base/'historical-before-admission.json').write_text(json.dumps(dict(raw_run_files=[],preparation02_run_files=[],
            historical_empty_directories=[],historical_absent_paths=[],attempt11_d83dab3_absent_outputs=[])))
        (tmp/'palimpsest-puck-cpu-held-qualification-11b-admission-01.json').write_text(json.dumps(dict(status='DATA_ONLY_ADMITTED',configuration_sha256=CONFIG_SHA)))
        for phase,terminal in (('admission',dict(phase='admission',exit_code=0,outer_timeout=False)),('observer',observer),('audit',audit)):
            if terminal is not None:(tmp/('palimpsest-held11b-'+phase+'-tool-terminal.json')).write_text(json.dumps(terminal))
        if allocation:
            (root/'runs/puck-cpu-held-qualification-11/logs').mkdir(parents=True)
            (root/'runs/puck-cpu-held-qualification-11/configuration.json').write_text('{}\n')
            (root/'runs/puck-cpu-held-qualification-11-external-cli-transport.json').write_text(json.dumps(dict(
                configuration_sha256=transport_sha,observed_returncode=None,timed_out=True)))
        source=instantiate('tools/collect-outcome.py.in').replace("'/tmp/","'"+str(tmp)+'/')
        source=source.replace("root=Path('/home/utkarsh/.codex/worktrees/0071/brain')","root=Path('"+str(root)+"')")
        exec(compile(source,'collect-outcome.py','exec'),{'__name__':'fixture'})
        return json.loads((tmp/'palimpsest-held11b-post-outcome-observation.json').read_bytes())

    def test_collect_records_admission_refusal_without_allocation(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held11b-collect-',dir='/tmp') as directory:
            value=self.collect(Path(directory),dict(phase='observer',exit_code=1,outer_timeout=False),None,allocation=False)
        self.assertEqual((value['status'],value['allocation_present'],value['independent_auditor_invocations']),('FAILED_CONSUMED',False,0))
        self.assertTrue(any(p.endswith('runs/puck-cpu-held-qualification-11') for p in value['missing_original_paths']))
        self.assertTrue(any(p.endswith('palimpsest-held11b-audit-tool-terminal.json') for p in value['missing_original_paths']))
        self.assertEqual(value['stage_after']['status'],'STAGE_OR_BOOT_CHANGED')

    def test_collect_records_observer_timeout_without_audit(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held11b-collect-',dir='/tmp') as directory:
            value=self.collect(Path(directory),dict(phase='observer',exit_code=None,outer_timeout=True),None,allocation=True)
        self.assertEqual((value['status'],value['allocation_present'],value['completed_four_import_receipt']),('FAILED_CONSUMED',True,False))
        self.assertTrue(any(p.endswith('runs/puck-cpu-held-qualification-11/result.json') for p in value['missing_original_paths']))

    def test_collect_refuses_a_different_configuration_sha(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held11b-collect-',dir='/tmp') as directory:
            with self.assertRaises(AssertionError):
                self.collect(Path(directory),dict(phase='observer',exit_code=1,outer_timeout=False),None,allocation=True,transport_sha='0'*64)


if __name__=='__main__':unittest.main(verbosity=2)
