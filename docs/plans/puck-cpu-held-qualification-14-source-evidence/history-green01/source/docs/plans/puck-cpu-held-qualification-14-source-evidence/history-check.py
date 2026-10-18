"""Prospective14 small history checks; do not run before root's safe assembly.

Only existing small07-11 records, admission10 01/02 and admission11b records, accepted
preparation02/03 metadata and authenticated Held are exercised. Never call admission
main, resource/census support, observer, auditor audit or vendors, and never touch the
preparation02/03 stages. Forty-one unittest cases: the 33 11b cases (preparation checks
retargeted to preparation03/epoch 14) plus genuine/changed/fabricated runtime11, genuine,
changed and manifest-first admission11b, preparation02 consumed by runtime11 and
preparation02 refused for epoch 14. Fabricated and changed cases are refused at the
authenticated hash pins (immutability), not by semantics.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import types
import unittest

SOURCE=Path('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-qualification-14-admission.py')
spec=importlib.util.spec_from_file_location('held14_history_control',SOURCE)
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
raw=control.AUDITOR.read_bytes()
assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()==control.AUDITOR_SHA
auditor=types.ModuleType('held14_history_byte_holder');auditor.__file__=str(control.AUDITOR)
exec(compile(raw,str(control.AUDITOR),'exec'),auditor.__dict__)


class HistoryChecks(unittest.TestCase):
    def genuine(self,epoch):
        before=len(os.listdir('/proc/self/fd'))
        held=auditor.Held(time.monotonic()+10)
        try:
            value=getattr(control,'check_consumed'+epoch)(held)
            self.assertEqual(value['status'],'FAILED_CONSUMED')
            self.assertFalse(value['parent_closure_receipt'])
            self.assertFalse(value['completed_four_import_receipt'])
            self.assertEqual(value['independent_audit_status'],'FAIL')
            self.assertEqual(value['missing_receipts'],[
                'runs/puck-cpu-held-qualification-'+epoch+'/'+leaf for leaf in ('result.json','baseline-after.json')])
            if epoch=='08':
                self.assertEqual(control.absent()['historical_missing_receipts'],19)
                self.assertFalse(value['post_failure_full_payload_custody'])
                self.assertEqual(value['diagnostic_stream']['records'],11)
                self.assertEqual(value['diagnostic_stream']['last_record']['phase'],'import.torchvision.enter')
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_genuine07_failure_has_no_success_or_closure_receipt(self):self.genuine('07')
    def test_genuine08_failure_has_no_success_or_closure_receipt(self):self.genuine('08')

    def test_manifest_first_reads_preserve_historical07_and08_stream_bytes(self):
        # Small exact manifest slice built from genuine local history, independent
        # of whether the prospective full09 freeze has been assembled yet.
        selected=set(control.HISTORICAL07_JSON)|set(control.HISTORICAL08_JSON)|set(control.HISTORICAL09_JSON)|set(control.HISTORICAL10_JSON)|set(control.HISTORICAL11_JSON)
        for epoch in ('07','08','09','10','11'):
            selected.update('runs/puck-cpu-held-qualification-'+epoch+'-external-cli.'+name for name in ('stdout','stderr'))
            selected.update('runs/puck-cpu-held-qualification-'+epoch+'/logs/'+name+'.log' for name in ('stdout','stderr'))
        pins=[]
        for path in sorted(selected):
            data=(control.ROOT/path).read_bytes()
            pins.append(dict(path=path,size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        self.assertEqual(len(pins),50)
        before=len(os.listdir('/proc/self/fd'))
        held=auditor.Held(time.monotonic()+10)
        try:
            # JSON and stream raw roles must survive first reads in hold_manifest;
            # an old07-only reservation fails when08 bytes are requested below.
            control.hold_manifest(held,pins,set(control.HISTORICAL07_JSON)|set(control.HISTORICAL08_JSON)|set(control.HISTORICAL09_JSON)|set(control.HISTORICAL10_JSON)|set(control.HISTORICAL11_JSON))
            self.assertEqual(control.check_consumed07(held)['status'],'FAILED_CONSUMED')
            self.assertEqual(control.check_consumed08(held)['status'],'FAILED_CONSUMED')
            self.assertEqual(control.check_consumed09(held)['status'],'FAILED_CONSUMED')
            self.assertEqual(control.check_consumed10(held)['status'],'FAILED_CONSUMED')
            self.assertEqual(control.check_consumed11(held)['status'],'FAILED_CONSUMED')
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def changed_transport(self,epoch):
        class ChangedTransport:
            def json(self,path,**kwargs):
                raw=Path(path).read_bytes();value=json.loads(raw)
                if str(path).endswith('-external-cli-transport.json'):
                    value['observed_returncode']=0
                    raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
                return value,raw
        with self.assertRaises(AssertionError):getattr(control,'check_consumed'+epoch)(ChangedTransport())

    def test_changed07_transport_is_refused(self):self.changed_transport('07')
    def test_changed08_transport_is_refused(self):self.changed_transport('08')

    def check_missing(self,epoch,leaf):
        original=control.ROOT
        try:
            with tempfile.TemporaryDirectory(prefix='palimpsest-held14-history-fixture-') as directory:
                control.ROOT=Path(directory)
                path=control.ROOT/('runs/puck-cpu-held-qualification-'+epoch)/leaf
                path.parent.mkdir(parents=True);path.write_bytes(b'fabricated receipt\n')
                with self.assertRaises(AssertionError):control.absent()
        finally:control.ROOT=original

    def test_fabricated07_result_is_refused(self):self.check_missing('07','result.json')
    def test_fabricated07_baseline_after_is_refused(self):self.check_missing('07','baseline-after.json')
    def test_fabricated08_result_is_refused(self):self.check_missing('08','result.json')
    def test_fabricated08_baseline_after_is_refused(self):self.check_missing('08','baseline-after.json')


    def test_genuine09_failure_has_no_success_or_closure_receipt(self):
        self.genuine('09')

    def test_changed09_transport_is_refused(self):self.changed_transport('09')
    def test_fabricated09_result_is_refused(self):self.check_missing('09','result.json')
    def test_fabricated09_baseline_after_is_refused(self):self.check_missing('09','baseline-after.json')



    def admission01(self,held):
        config=self.admitted10()
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
                    value['returncode']=0;raw=(json.dumps(value,sort_keys=True)+'\n').encode()
                return value,raw
        with self.assertRaises(AssertionError):self.admission01(Changed())

    def test_fabricated_prior_admission_result_is_refused(self):
        held=auditor.Held(time.monotonic()+10);original=control.os.path.lexists
        try:
            control.os.path.lexists=lambda path: str(path)=='/tmp/palimpsest-puck-cpu-held-qualification-10-admission-01.json' or original(path)
            with self.assertRaises(AssertionError):self.admission01(held)
        finally:control.os.path.lexists=original;held.close()



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
            self.assertEqual(control.absent()['historical_missing_receipts'],19)
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
                    raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
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
                    value['returncode']=1;raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
                return value,raw
        with self.assertRaises(AssertionError):control.check_consumed_admission02(Changed(),self.admitted10())

    def test_fabricated11_admission_receipt_is_refused(self):
        original=control.os.path.lexists
        try:
            control.os.path.lexists=lambda path: str(path)==str(control.OUTPUT) or original(path)
            with self.assertRaises(AssertionError):control.absent()
        finally:control.os.path.lexists=original



    def current(self,held):
        return control.module(held,control.ROOT/'scripts/audit_puck_cpu_held_runtime.py',control.AUDITOR_CURRENT_SHA)

    def frozen(self):
        return json.loads(control.CONFIGURATION.read_bytes())

    def test_genuine_preparation03_binds_epoch14(self):
        before=len(os.listdir('/proc/self/fd'));held=auditor.Held(time.monotonic()+30)
        try:
            value=control.check_preparation03(held,auditor,self.current(held),self.frozen())[-1]
            self.assertEqual(value['status'],'ACCEPTED_PREPARATION03')
            self.assertEqual(value['stage_parent'],'/tmp/palimpsest-puck-cpu-held-03')
            self.assertEqual([(r['device'],r['inode']) for r in value['staged_roots']],[(55,43194),(55,43195),(55,43196),(55,43197)])
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_preparation03_pin_drift_is_refused(self):
        held=auditor.Held(time.monotonic()+30);original=control.RESULT_SHA
        try:
            control.RESULT_SHA='0'*64
            with self.assertRaises(AssertionError):control.check_preparation03(held,auditor,self.current(held),self.frozen())
        finally:control.RESULT_SHA=original;held.close()

    def test_preparation01_is_recorded_but_cannot_satisfy_epoch14(self):
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
        self.assertEqual(control.check_empty_directories()['directories'],41)

    def test_inserted_file_in_historical_empty_directory_is_refused(self):
        original=control.ROOT
        try:
            with tempfile.TemporaryDirectory(prefix='palimpsest-held14-empty-fixture-') as directory:
                control.ROOT=Path(directory)
                for name in control.EMPTY_DIRECTORIES:(control.ROOT/name).mkdir(parents=True)
                self.assertEqual(control.check_empty_directories()['directories'],41)
                (control.ROOT/control.EMPTY_DIRECTORIES[0]/'fabricated.json').write_bytes(b'{}\n')
                with self.assertRaises(AssertionError):control.check_empty_directories()
        finally:control.ROOT=original



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
                    value['returncode']=1;raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
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


if __name__=='__main__':unittest.main(verbosity=2)
