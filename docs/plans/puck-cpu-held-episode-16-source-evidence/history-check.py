"""Allocation-16 small history checks; never run admission main, census, observer, auditor or vendors.

Only small existing history records and authenticated Held are exercised; neither the retired
preparation02/03 stages nor the live preparation04 stage (/tmp/palimpsest-puck-cpu-held-04) is
opened or stat-checked. Ported attempt-14 cases (07-11, admissions 10-01/02 and 11b, preparation02,
d83dab3, empty directories, absences) plus runtime14 accepted and consumed, admission14 consumed by
runtime14, preparation03 accepted, consumed and retired, preparation02 retired, characterization-04
accepted, preparation04 bound to the frozen allocation-16 configuration, and preparations 01-03
refused for allocation 16. Changed and fabricated cases are refused at the authenticated hash pins
(immutability), not by semantics.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import types
import unittest

SOURCE=Path('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-episode-16-admission.py')
spec=importlib.util.spec_from_file_location('held16_history_control',SOURCE)
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
raw=control.AUDITOR.read_bytes()
assert hashlib.sha256(raw).hexdigest()==control.AUDITOR_SHA
auditor=types.ModuleType('held16_history_byte_holder');auditor.__file__=str(control.AUDITOR)
exec(compile(raw,str(control.AUDITOR),'exec'),auditor.__dict__)
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(Path(path).read_bytes(),str(path),'exec'),value.__dict__);return value
QUALIFIER=load(control.ROOT/'scripts/qualify_puck_cpu_held_runtime.py','held16_history_qualifier')
EPISODE=load(control.ROOT/'scripts/run_puck_cpu_held_episode.py','held16_history_episode')


class Changed:
    """A holder whose JSON for one path suffix is edited before it reaches the check."""
    def __init__(self,suffix,**changes):self.suffix=suffix;self.changes=changes
    def json(self,path,*args,**kwargs):
        raw=Path(path).read_bytes();value=json.loads(raw)
        if str(path).endswith(self.suffix):
            value.update(self.changes);raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
        return value,raw
    def file(self,path,*args,raw=False,**kwargs):
        data=Path(path).read_bytes()
        return data if raw else dict(size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


class HistoryChecks(unittest.TestCase):
    def setUp(self):
        fds=len(os.listdir('/proc/self/fd'))
        # Registered first, so it runs after every Held cleanup: no descriptor may outlive a case.
        self.addCleanup(lambda:self.assertEqual(len(os.listdir('/proc/self/fd')),fds))
    def held(self,seconds=30):
        held=auditor.Held(time.monotonic()+seconds);self.addCleanup(held.close);return held

    def frozen(self):return json.loads(control.CONFIGURATION.read_bytes())

    def acceptance(self,config=None):
        config=config or self.frozen()
        blobs={role:(control.ROOT/row['path']).read_bytes() for role,row in config['preparation_acceptance'].items()}
        return EPISODE.validate_acceptance(config,blobs,QUALIFIER)

    def genuine(self,epoch):
        value=getattr(control,'check_consumed'+epoch)(self.held())
        self.assertEqual(value['status'],'FAILED_CONSUMED')
        self.assertFalse(value['parent_closure_receipt'])
        self.assertFalse(value['completed_four_import_receipt'])
        self.assertEqual(value['independent_audit_status'],'FAIL')
        self.assertEqual(value['missing_receipts'],['runs/puck-cpu-held-qualification-'+epoch+'/'+leaf for leaf in ('result.json','baseline-after.json')])
        if epoch=='08':
            self.assertEqual(control.absent()['historical_missing_receipts'],19)
            self.assertEqual(value['diagnostic_stream']['records'],11)

    def test_genuine07_failure_has_no_success_or_closure_receipt(self):self.genuine('07')
    def test_genuine08_failure_has_no_success_or_closure_receipt(self):self.genuine('08')
    def test_genuine09_failure_has_no_success_or_closure_receipt(self):self.genuine('09')
    def test_genuine11_failure_has_no_success_or_closure_receipt(self):self.genuine('11')

    def test_manifest_first_reads_preserve_historical07_to_14_stream_bytes(self):
        selected=set()
        for rows in (control.HISTORICAL07_JSON,control.HISTORICAL08_JSON,control.HISTORICAL09_JSON,control.HISTORICAL10_JSON,
                control.HISTORICAL11_JSON,control.HISTORICAL14_JSON):selected.update(rows)
        for epoch in ('07','08','09','10','11'):
            selected.update('runs/puck-cpu-held-qualification-'+epoch+'-external-cli.'+name for name in ('stdout','stderr'))
            selected.update('runs/puck-cpu-held-qualification-'+epoch+'/logs/'+name+'.log' for name in ('stdout','stderr'))
        # Runtime14's streams and baselines are pinned too and must survive manifest-first holds (selfcheck trial finding).
        selected.update('runs/puck-cpu-held-qualification-14-external-cli.'+name for name in ('stdout','stderr'))
        selected.update('runs/puck-cpu-held-qualification-14/baseline-'+name+'.json' for name in ('before','after'))
        pins=[]
        for path in sorted(selected):
            data=(control.ROOT/path).read_bytes();pins.append(dict(path=path,size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        held=self.held()
        raw_roles=set()
        for rows in (control.HISTORICAL07_JSON,control.HISTORICAL08_JSON,control.HISTORICAL09_JSON,control.HISTORICAL10_JSON,
                control.HISTORICAL11_JSON,control.HISTORICAL14_JSON):raw_roles.update(rows)
        control.hold_manifest(held,pins,raw_roles)
        for epoch in ('07','08','09','10','11'):self.assertEqual(getattr(control,'check_consumed'+epoch)(held)['status'],'FAILED_CONSUMED')
        self.assertEqual(control.check_runtime14(held)['status'],'ACCEPTED_IMPORT_ROUTE_CONSUMED')

    def changed_transport(self,epoch):
        with self.assertRaises(AssertionError):getattr(control,'check_consumed'+epoch)(Changed('-external-cli-transport.json',observed_returncode=0))
    def test_changed07_transport_is_refused(self):self.changed_transport('07')
    def test_changed08_transport_is_refused(self):self.changed_transport('08')
    def test_changed09_transport_is_refused(self):self.changed_transport('09')
    def test_changed10_transport_is_refused(self):self.changed_transport('10')
    def test_changed11_transport_is_refused(self):self.changed_transport('11')

    def check_missing(self,epoch,leaf):
        original=control.ROOT
        try:
            with tempfile.TemporaryDirectory(prefix='palimpsest-held16-history-fixture-') as directory:
                control.ROOT=Path(directory)
                path=control.ROOT/('runs/puck-cpu-held-qualification-'+epoch)/leaf
                path.parent.mkdir(parents=True);path.write_bytes(b'fabricated receipt\n')
                with self.assertRaises(AssertionError):control.absent()
        finally:control.ROOT=original
    def test_fabricated07_result_is_refused(self):self.check_missing('07','result.json')
    def test_fabricated08_baseline_after_is_refused(self):self.check_missing('08','baseline-after.json')
    def test_fabricated09_result_is_refused(self):self.check_missing('09','result.json')
    def test_fabricated10_baseline_after_is_refused(self):self.check_missing('10','baseline-after.json')
    def test_fabricated11_result_is_refused(self):self.check_missing('11','result.json')

    def test_genuine10_failure_has_fail_result_but_no_success_receipt(self):
        value=control.check_consumed10(self.held())
        self.assertEqual((value['status'],value['parent_failure_result'],value['first_refusal']),
            ('FAILED_CONSUMED',True,'Unregistered local or external dependency import: backports_abc'))

    def test_fabricated10_success_result_is_refused(self):
        with self.assertRaises(AssertionError):
            control.check_consumed10(Changed('runs/puck-cpu-held-qualification-10/result.json',status='imports_completed',held_four_imports_observed=True))

    def admitted(self,name):return json.loads((control.ROOT/name).read_bytes())

    def test_genuine_admissions10_were_consumed(self):
        held=self.held();admitted=self.admitted(control.ADMITTED10_CONFIGURATION)
        self.assertEqual(control.check_consumed_admission01(held,admitted)['status'],'FAILED_CONSUMED')
        self.assertEqual(control.check_consumed_admission02(held,admitted)['status'],'ADMITTED_CONSUMED_BY_RUNTIME10')

    def test_admissions_manifest_first_raw_reservations(self):
        held=self.held()
        for pins in (control.ADMISSION01_PINS,control.ADMISSION02_PINS,control.ADMISSION11B_PINS,control.ADMISSION14_PINS):
            control.hold_manifest(held,[dict(path=name,**row) for name,row in pins.items()],set(pins))
        admitted=self.admitted(control.ADMITTED10_CONFIGURATION)
        self.assertEqual(control.check_consumed_admission01(held,admitted)['status'],'FAILED_CONSUMED')
        self.assertEqual(control.check_consumed_admission02(held,admitted)['status'],'ADMITTED_CONSUMED_BY_RUNTIME10')
        self.assertEqual(control.check_consumed_admission11b(held,self.admitted('docs/plans/puck-cpu-held-qualification-11.json'))['status'],'ADMITTED_CONSUMED_BY_RUNTIME11')
        self.assertEqual(control.check_consumed_admission14(held,self.admitted('docs/plans/puck-cpu-held-qualification-14.json'))['status'],'ADMITTED_CONSUMED_BY_RUNTIME14')

    def test_changed_admission11b_and_14_transports_are_refused(self):
        with self.assertRaises(AssertionError):
            control.check_consumed_admission11b(Changed('palimpsest-held11b-admission-external.json',returncode=1),self.admitted('docs/plans/puck-cpu-held-qualification-11.json'))
        with self.assertRaises(AssertionError):
            control.check_consumed_admission14(Changed('palimpsest-held14-admission-external.json',returncode=1),self.admitted('docs/plans/puck-cpu-held-qualification-14.json'))

    def test_genuine_admission14_was_consumed_by_sole_runtime14(self):
        value=control.check_consumed_admission14(self.held(),self.admitted('docs/plans/puck-cpu-held-qualification-14.json'))
        self.assertEqual((value['status'],value['current_admission_authority'],value['review_decision']),('ADMITTED_CONSUMED_BY_RUNTIME14',False,'GO'))

    def test_genuine_runtime14_accepted_import_route_is_consumed(self):
        value=control.check_runtime14(self.held())
        self.assertEqual(value['status'],'ACCEPTED_IMPORT_ROUTE_CONSUMED')
        self.assertTrue(value['completed_four_import_receipt'])
        self.assertEqual(value['independent_audit_status'],'PASS')
        self.assertEqual(value['tracked_processes'],[dict(pid=493563,start_ticks=7246806),dict(pid=493564,start_ticks=7246807),dict(pid=493565,start_ticks=7246808)])
        self.assertFalse(value['runtime_qualified'])

    def test_changed_runtime14_receipts_are_refused(self):
        for suffix,changes in (('-external-cli-transport.json',dict(observed_returncode=1)),('qualification-14/result.json',dict(status='FAIL')),
                ('qualification-14-audit-01.json',dict(status='FAIL')),('post-outcome-observation.json',dict(status='FAILED_CONSUMED'))):
            with self.subTest(suffix=suffix),self.assertRaises(AssertionError):control.check_runtime14(Changed(suffix,**changes))

    def test_fabricated_episode16_receipt_is_refused(self):
        original=control.os.path.lexists
        try:
            for fabricated in (str(control.OUTPUT),str(control.ROOT/'runs/puck-cpu-held-episode-16'),'/tmp/palimpsest-puck-cpu-held-episode-16-audit-01.json'):
                control.os.path.lexists=lambda path,f=fabricated: str(path)==f or original(path)
                with self.subTest(path=fabricated),self.assertRaises(AssertionError):control.absent()
        finally:control.os.path.lexists=original

    def test_absence_names_the_six_episode16_paths(self):
        value=control.absent()
        self.assertEqual(len(value['new_paths']),6);self.assertEqual(value['historical_missing_receipts'],19)
        self.assertIn(str(control.ROOT/'runs/puck-cpu-held-episode-16'),value['new_paths'])

    def test_preparation02_was_accepted_consumed_and_retired(self):
        value=control.check_preparation02_consumed(self.held())
        self.assertEqual((value['status'],value['stage_inspected'],value['retirement']['status']),('ACCEPTED_CONSUMED_BY_RUNTIME11_STAGE_RETIRED',False,'RETIRED'))

    def test_preparation03_was_accepted_consumed_by_runtime14_and_retired(self):
        value=control.check_preparation03_consumed(self.held())
        self.assertEqual((value['status'],value['retirement']['status']),('ACCEPTED_CONSUMED_BY_RUNTIME14_STAGE_RETIRED','RETIRED'))
        self.assertEqual([(r['device'],r['inode']) for r in value['staged_roots']],[(55,43194),(55,43195),(55,43196),(55,43197)])

    def test_a_present_retired_stage_or_changed_retirement_is_refused(self):
        original=control.os.path.lexists
        try:
            control.os.path.lexists=lambda path: str(path)=='/tmp/palimpsest-puck-cpu-held-03' or original(path)
            with self.assertRaises(AssertionError):control.check_preparation03_consumed(self.held())
        finally:control.os.path.lexists=original
        with self.assertRaises(AssertionError):control.check_retired_stage(Changed('retire-consumed-stages.json',boot_id='0'*36),
            '/tmp/palimpsest-puck-cpu-held-02',control.PREP02_ACCEPTANCE['result']['sha256'])
        with self.assertRaises(AssertionError):control.check_retired_stage(self.held(),'/tmp/palimpsest-puck-cpu-held-04',control.RESULT_SHA)

    def test_genuine_characterization04_was_accepted(self):
        value=control.check_characterization04(self.held(),json.loads((control.ROOT/control.PREP_CONFIGURATION).read_bytes()))
        self.assertEqual((value['status'],value['ticks_completed'],value['process_creation_attempts'],value['undeclared_import_misses']),
            ('ACCEPTED_OBSERVATION',48,0,0))

    def test_changed_characterization04_audit_is_refused(self):
        with self.assertRaises(AssertionError):
            control.check_characterization04(Changed('outcome-audit-04.json',status='FAIL'),json.loads((control.ROOT/control.PREP_CONFIGURATION).read_bytes()))

    def test_genuine_preparation04_binds_allocation16(self):
        prior,prepared=self.acceptance();held=self.held()
        config,_,prep,_,value=control.check_preparation04(held,auditor,prior,prepared)
        self.assertEqual((value['status'],value['stage_parent']),('ACCEPTED_PREPARATION04','/tmp/palimpsest-puck-cpu-held-04'))
        self.assertEqual([(r['device'],r['inode']) for r in value['staged_roots']],[(55,317249),(55,317250),(55,317251),(55,317252)])
        self.assertEqual(config,prior);self.assertEqual(prep,prepared);self.assertEqual(value['capsule_files'],97)

    def test_preparation04_pin_drift_is_refused(self):
        prior,prepared=self.acceptance();original=control.RESULT_SHA
        try:
            control.RESULT_SHA='0'*64
            with self.assertRaises(AssertionError):control.check_preparation04(self.held(),auditor,prior,prepared)
        finally:control.RESULT_SHA=original

    def test_preparations01_to03_cannot_satisfy_allocation16(self):
        for number,acceptance in (('01',None),('02',control.PREP02_ACCEPTANCE),('03',control.PREP03_ACCEPTANCE)):
            config=self.frozen()
            if acceptance is None:
                acceptance=dict(configuration=dict(path='docs/plans/puck-cpu-held-preparation-01.json'),result=dict(path='runs/puck-cpu-held-preparation-01/result.json'),
                    independent_audit=dict(path='docs/reports/puck-cpu-held-preparation-01/audit/palimpsest-puck-cpu-held-preparation-01-audit-01.json'),
                    externally_observed_auditor_cli=dict(path='docs/reports/puck-cpu-held-preparation-01/audit/palimpsest-puck-cpu-held-preparation-01-audit-01.external-cli.json'))
                for row in acceptance.values():
                    data=(control.ROOT/row['path']).read_bytes();row.update(size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
            config['preparation_acceptance']=copy.deepcopy(acceptance)
            with self.subTest(preparation=number),self.assertRaises(ValueError):
                blobs={role:(control.ROOT/row['path']).read_bytes() for role,row in config['preparation_acceptance'].items()}
                EPISODE.validate_acceptance(config,blobs,QUALIFIER)

    def test_preparation01_is_recorded_as_superseded(self):
        value=control.record_preparation01()
        self.assertEqual((value['status'],value['required']),('ACCEPTED_SUPERSEDED_STAGE_LOST',False))

    def test_unexecuted_d83dab3_packet_is_recorded_never_invoked(self):
        value=control.check_unexecuted11(self.held())
        self.assertEqual((value['status'],value['control_commit']),('NEVER_INVOKED','d83dab3c92387c80e81af528fea25dd3f8931598'))

    def test_fabricated_d83dab3_receipt_is_refused(self):
        original=control.os.path.lexists
        try:
            control.os.path.lexists=lambda path: str(path)=='/tmp/palimpsest-puck-cpu-held-qualification-11-admission-01.json' or original(path)
            with self.assertRaises(AssertionError):control.check_unexecuted11(self.held())
        finally:control.os.path.lexists=original

    def test_historical_empty_directories_remain_empty(self):
        self.assertEqual(control.check_empty_directories()['directories'],46)

    def test_inserted_file_in_historical_empty_directory_is_refused(self):
        original=control.ROOT
        try:
            with tempfile.TemporaryDirectory(prefix='palimpsest-held16-empty-fixture-') as directory:
                control.ROOT=Path(directory)
                for name in control.EMPTY_DIRECTORIES:(control.ROOT/name).mkdir(parents=True)
                self.assertEqual(control.check_empty_directories()['directories'],46)
                (control.ROOT/control.EMPTY_DIRECTORIES[0]/'fabricated.json').write_bytes(b'{}\n')
                with self.assertRaises(AssertionError):control.check_empty_directories()
        finally:control.ROOT=original

    def test_process_identities_add_runtime14_to_the_eighteen(self):
        self.assertEqual(len(control.PROCESS_IDENTITIES),21)
        self.assertEqual(control.PROCESS_IDENTITIES[-3:],[(493563,7246806),(493564,7246807),(493565,7246808)])


if __name__=='__main__':unittest.main(verbosity=2)
