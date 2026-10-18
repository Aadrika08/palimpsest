"""Compile the allocation-16 templates and prove guard/collector behavior on isolated fixtures.

Never instantiates into /tmp tool paths, runs a guard, admission, observer, auditor or episode, and never
touches the preparation04 stage: stage-guard cases use fixture tmpfs directories.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
VALIDATION=ROOT/'docs/plans/puck-cpu-held-episode-16-control-validation'
TEMPLATES=['pre-admission-guard.py.in','tools/run-admission-once.py.in','tools/make-observer-guard.py','tools/run-observer-once.py.in',
    'tools/bind-audit-command.py','tools/run-audit-once.py.in','tools/collect-outcome.py.in','tools/archive-evidence.py.in','tools/instantiate.py',
    'tools/stage_guard.py']
GUARDED=['pre-admission-guard.py.in','tools/run-admission-once.py.in','tools/run-observer-once.py.in','tools/run-audit-once.py.in']
CONFIG_SHA=hashlib.sha256((ROOT/'docs/plans/puck-cpu-held-episode-16.json').read_bytes()).hexdigest()
AUDITOR_SHA='4d8ac17f0577938ded9fa3845f0e26c1b52be8db11fa5327953c9446b156ba36'
HISTORY=dict(raw_run_files=[],preparation04_run_files=[],preparation03_run_files=[],preparation02_run_files=[],characterization04_run_files=[],
    historical_empty_directories=[],historical_absent_paths=[],attempt11_d83dab3_absent_outputs=[],retired_stage_paths=[])


def instantiate(name):
    return (VALIDATION/name).read_text().replace('@CONTROL@','f'*40).replace('@COUNT@','99')


def stage_guard():
    namespace={'__name__':'tools_check_stage_guard'}
    exec(compile((VALIDATION/'tools/stage_guard.py').read_bytes(),'stage_guard.py','exec'),namespace);return namespace


class ToolChecks(unittest.TestCase):
    def test_templates_compile_without_unknown_placeholders(self):
        for name in TEMPLATES:
            text=instantiate(name);compile(text,name,'exec')
            if name!='tools/make-observer-guard.py':self.assertNotIn('@',text,name)
            for stale in ('palimpsest-held14','qualification-14-','runtime14','f05bd699af337e44de54584bb334690ec405f994','held-03','43194'):
                self.assertNotIn(stale,text,name)

    def test_every_one_shot_guard_checks_stage_and_boot_before_acting(self):
        for name in GUARDED:
            text=instantiate(name);check=text.index("stage=stage_namespace['check'](")
            self.assertIn("tools/stage_guard.py'",text,name)
            self.assertIn("subprocess.check_output(['git','show',",text[:check],name)
            acting='with Path(str(stem)' if 'tools/' in name else 'module=types.ModuleType('
            self.assertLess(check,text.index(acting),name)

    def test_stage_guard_on_tmpfs_fixture(self):
        guard=stage_guard()
        with tempfile.TemporaryDirectory(prefix='palimpsest-held16-stage-fixture-',dir='/tmp') as directory:
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
        self.assertEqual((guard['BOOT'],guard['STAGE'],guard['RESULT'],guard['RESULT_SHA']),('7f875223-b4cf-421e-b04d-81e3c1f19460','/tmp/palimpsest-puck-cpu-held-04',
            'runs/puck-cpu-held-preparation-04/result.json','a76b61487a1e5c053032167f1602260a1184b6262fa86e0e62842f0a05e6ebc3'))
        self.assertEqual([(r['device'],r['inode']) for r in guard['ROOTS']],[(55,317249),(55,317250),(55,317251),(55,317252)])

    def test_make_observer_guard_derives_pre_observer_guard_on_fixture(self):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held16-tools-',dir='/tmp') as directory:
            fixture=Path(directory)
            (fixture/'palimpsest-held16-pre-admission-guard.py').write_text(instantiate('pre-admission-guard.py.in'))
            (fixture/'palimpsest-puck-cpu-held-episode-16-admission-01.json').write_text('{"fixture":true}\n')
            (fixture/'palimpsest-held16-independent-admission-review.json').write_text('{"decision":"GO"}\n')
            source=(VALIDATION/'tools/make-observer-guard.py').read_text()
            for line in ("source=Path('/tmp/palimpsest-held16-pre-admission-guard.py').read_text()\n",
                    "admission=Path('/tmp/palimpsest-puck-cpu-held-episode-16-admission-01.json').read_bytes()\n",
                    "review_path=Path('/tmp/palimpsest-held16-independent-admission-review.json')\nreview_raw",
                    "path=Path('/tmp/palimpsest-held16-pre-observer-guard.py')\n"):
                self.assertEqual(source.count(line),1,line)
                source=source.replace(line,line.replace('/tmp/',str(fixture)+'/'))
            exec(compile(source,'make-observer-guard.py','exec'),{'__name__':'fixture'})
            derived=(fixture/'palimpsest-held16-pre-observer-guard.py').read_text()
        compile(derived,'pre-observer-guard.py','exec')
        for present in ('before the sole runtime observer.',"status='PASS_PRE_OBSERVER_GUARD_ONLY'",
                'absence=dict(future_output_paths=future,historical_missing_receipts=19);resources=module.resources()',
                'historical_records_unchanged=151,admission_main_invoked=True,admission_receipt_sha256=',
                "Path('/tmp/palimpsest-held16-pre-observer-guard01.json').open('x')",'assert len(future)==len(set(future))==12',
                "assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-episode-16-admission-02.json')",
                "a['admission_check_id']==1 and a['episode16_invoked'] is False",
                "stage=stage_namespace['check'](ROOT)","attempt11_d83dab3='NEVER_INVOKED'",
                "assert all(not os.path.lexists(path) for path in before['retired_stage_paths'])",
                "before=json.loads((ROOT/(BASE+'-control-validation/historical-before-admission.json')).read_bytes())"):
            self.assertEqual(derived.count(present),1,present)
        for absent in ('PASS_PRE_ADMISSION_GUARD_ONLY','absence=module.absent()','admission_main_invoked=False','@',
                "pre-admission-guard01.json').open('x')"):
            self.assertNotIn(absent,derived)

    def fixture(self,fixture,observer=dict(exit_code=0,outer_timeout=False),audit=dict(exit_code=0,outer_timeout=False),allocation=True,
            transport_sha=CONFIG_SHA,transport_elapsed=700.0,result_changes=None,audit_changes=None,deadline=600,complete=True):
        """A fixture allocation-16 outcome; complete=True yields every receipt a passing episode leaves."""
        root=fixture/'root';tmp=fixture/'tmp';base=root/'docs/plans/puck-cpu-held-episode-16-control-validation';alloc=root/'runs/puck-cpu-held-episode-16'
        for path in (tmp,base):path.mkdir(parents=True)
        (base/'historical-before-admission.json').write_text(json.dumps(HISTORY))
        (tmp/'palimpsest-puck-cpu-held-episode-16-admission-01.json').write_text(json.dumps(dict(status='DATA_ONLY_ADMITTED',configuration_sha256=CONFIG_SHA)))
        for phase,terminal in (('admission',dict(exit_code=0,outer_timeout=False)),('observer',observer),('audit',audit)):
            if terminal is not None:(tmp/('palimpsest-held16-'+phase+'-tool-terminal.json')).write_text(json.dumps(dict(terminal,phase=phase)))
        if not allocation:return self.run_collect(root,tmp)
        for path in (alloc/'control',alloc/'logs-source',alloc/'logs-replay'):path.mkdir(parents=True)
        transport=(json.dumps(dict(kind='puck-cpu-held-cli-transport-v1',phase='episode',configuration_sha256=transport_sha,
            observed_returncode=0 if complete else None,timed_out=not complete,elapsed_seconds=transport_elapsed))+'\n').encode()
        (root/'runs/puck-cpu-held-episode-16-external-cli-transport.json').write_bytes(transport)
        if not complete:return self.run_collect(root,tmp)
        runs={p:dict(run_id=p*2,files=[],bundle=dict(path=p+'-bundle.zip',size_bytes=10,sha256=hashlib.sha256(p.encode()).hexdigest())) for p in ('source','replay')}
        result=dict(status='episode_completed',held_episode_observed=True,configuration_sha256=CONFIG_SHA,elapsed_seconds=760.0,process_creation_attempts=0,
            ticks_completed=48,replay=dict(status='passed',compared_ticks=48,compared_events=100,first_divergence=None),runs=runs,
            renderer=dict(vendor='Mesa',renderer='llvmpipe (LLVM 22.1.0, 256 bits)',backend='egl'))
        result.update(result_changes or {});result_raw=(json.dumps(result)+'\n').encode();(alloc/'result.json').write_bytes(result_raw)
        for p in ('source','replay'):
            (alloc/('control/worker-registration-'+p+'.json')).write_text(json.dumps(dict(deadline_seconds=deadline)))
            (alloc/(p+'-supervision.json')).write_text(json.dumps(dict(status='completed',tracked_processes=[])))
            (alloc/('logs-'+p)/'stderr.log').write_bytes(b'')
        verified=dict(result_sha256=hashlib.sha256(result_raw).hexdigest(),transport_sha256=hashlib.sha256(transport).hexdigest(),
            compared_ticks=48,frames_checked=384,source_bundle_sha256=runs['source']['bundle']['sha256'],replay_bundle_sha256=runs['replay']['bundle']['sha256'])
        value=dict(kind='puck-cpu-held-episode-independent-audit-v1',status='PASS',auditor_source_sha256=AUDITOR_SHA,configuration_sha256=CONFIG_SHA,
            transport_sha256=hashlib.sha256(transport).hexdigest(),verified=verified)
        value.update(audit_changes or {});raw=(json.dumps(value)+'\n').encode()
        for path in (tmp/'palimpsest-puck-cpu-held-episode-16-audit-01.json',tmp/'palimpsest-held16-audit-external.stdout'):path.write_bytes(raw)
        return self.run_collect(root,tmp)

    def run_collect(self,root,tmp):
        source=instantiate('tools/collect-outcome.py.in').replace("'/tmp/","'"+str(tmp)+'/')
        source=source.replace("root=Path('/home/utkarsh/.codex/worktrees/0071/brain')","root=Path('"+str(root)+"')")
        exec(compile(source,'collect-outcome.py','exec'),{'__name__':'fixture'})
        return json.loads((tmp/'palimpsest-held16-post-outcome-observation.json').read_bytes())

    def collect(self,**kwargs):
        with tempfile.TemporaryDirectory(prefix='palimpsest-held16-collect-',dir='/tmp') as directory:return self.fixture(Path(directory),**kwargs)

    def test_collect_records_admission_refusal_without_allocation(self):
        value=self.collect(observer=dict(exit_code=1,outer_timeout=False),audit=None,allocation=False)
        self.assertEqual((value['status'],value['allocation_present'],value['independent_auditor_invocations']),('FAILED_CONSUMED',False,0))
        self.assertTrue(any(p.endswith('runs/puck-cpu-held-episode-16') for p in value['missing_original_paths']))
        self.assertTrue(any(p.endswith('palimpsest-held16-audit-tool-terminal.json') for p in value['missing_original_paths']))
        self.assertEqual(value['stage_after']['status'],'STAGE_OR_BOOT_CHANGED')

    def test_collect_records_observer_timeout_without_audit(self):
        value=self.collect(observer=dict(exit_code=None,outer_timeout=True),audit=None,complete=False)
        self.assertEqual((value['status'],value['allocation_present'],value['completed_episode_receipt']),('FAILED_CONSUMED',True,False))
        self.assertTrue(any(p.endswith('runs/puck-cpu-held-episode-16/result.json') for p in value['missing_original_paths']))

    def test_collect_refuses_a_different_configuration_sha(self):
        with self.assertRaises(AssertionError):self.collect(observer=dict(exit_code=1,outer_timeout=False),audit=None,complete=False,transport_sha='0'*64)

    def test_collect_passes_only_a_complete_audited_episode(self):
        sha=lambda raw:hashlib.sha256(raw).hexdigest()
        cases=((dict(),'AUDIT_PASS_HELD_EPISODE_ONLY'),(dict(transport_elapsed=1260.0),'FAILED_CONSUMED'),
            (dict(result_changes=dict(elapsed_seconds=1200.0)),'FAILED_CONSUMED'),(dict(result_changes=dict(process_creation_attempts=1)),'FAILED_CONSUMED'),
            (dict(result_changes=dict(ticks_completed=47)),'FAILED_CONSUMED'),
            (dict(result_changes=dict(replay=dict(status='passed',compared_ticks=48,compared_events=100,first_divergence=dict(tick=3)))),'FAILED_CONSUMED'),
            (dict(result_changes=dict(renderer=dict(vendor='Mesa',renderer='softpipe',backend='egl'))),'FAILED_CONSUMED'),
            (dict(audit_changes=dict(status='FAIL')),'FAILED_CONSUMED'),(dict(audit_changes=dict(auditor_source_sha256='0'*64)),'FAILED_CONSUMED'),
            (dict(audit_changes=dict(verified=dict(result_sha256='0'*64))),'FAILED_CONSUMED'),
            (dict(audit=dict(exit_code=1,outer_timeout=False)),'FAILED_CONSUMED'))
        for changes,expected in cases:
            with self.subTest(changes=sorted(changes)):
                value=self.collect(**changes)
                self.assertEqual(value['status'],expected)
                self.assertEqual(value['completed_episode_receipt'],expected=='AUDIT_PASS_HELD_EPISODE_ONLY')

    def test_collect_refuses_a_bundle_the_audit_did_not_validate(self):
        value=self.collect(audit_changes=dict(verified=dict(result_sha256=None)))
        self.assertEqual(value['status'],'FAILED_CONSUMED')

    def test_collect_refuses_a_registration_without_the_600s_clock(self):
        with self.assertRaises(AssertionError):self.collect(deadline=360)

    def test_envelope_and_wrapper_outlast_every_child_alarm(self):
        envelope=json.loads((ROOT/'docs/plans/puck-cpu-held-episode-16-execution.json').read_bytes())
        self.assertEqual(envelope['normal_external_caps_seconds'],dict(admission=145,audit=330,observer=1300))
        self.assertEqual(envelope['outer_term_seconds'],dict(admission=155,audit=340,observer=1310))
        self.assertEqual([envelope['commands'][p][3] for p in ('admission','observer','audit')],['155s','1310s','340s'])
        wrapper=(ROOT/'docs/plans/puck-cpu-held-episode-16-external.py').read_text()
        self.assertEqual(wrapper.count("budget=1300 if phase=='observer' else 330 if phase=='audit' else 145"),1)
        self.assertIn("'1310s',",instantiate('tools/run-observer-once.py.in'));self.assertIn('timeout=1330)',instantiate('tools/run-observer-once.py.in'))
        self.assertIn("'340s',",instantiate('tools/run-audit-once.py.in'));self.assertIn('timeout=360)',instantiate('tools/run-audit-once.py.in'))
        observer=(ROOT/'scripts/observe_puck_cpu_held_allocation.py').read_text();auditor=(ROOT/'scripts/audit_puck_cpu_held_episode.py').read_text()
        self.assertIn('EPISODE_SECONDS=(1260,1275)',observer);self.assertIn('CLEANUP_SECONDS=5',observer)
        self.assertIn('signal.setitimer(signal.ITIMER_REAL,310)',auditor)
        self.assertGreater(1300,1275+5);self.assertGreater(330,310)

    def test_bind_and_archive_use_the_episode_parent_auditor_and_packet(self):
        bind=instantiate('tools/bind-audit-command.py');archive=instantiate('tools/archive-evidence.py.in')
        self.assertIn("value['phase']=='episode'",bind);self.assertIn("scripts/run_puck_cpu_held_episode.py",bind)
        self.assertIn("runs/puck-cpu-held-episode-16-external-cli-transport.json",bind)
        self.assertIn("packet=root/'docs/reports/puck-cpu-held-episode-16'",archive);self.assertIn('assert len(sources)==103',archive)
        self.assertIn("'scripts/audit_puck_cpu_held_episode.py','scripts/validate_palimpsest_bundle.py'",archive)
        self.assertIn("8d964599119b420de67ee259434d273651a1a76d:",archive)

if __name__=='__main__':unittest.main(verbosity=2)
