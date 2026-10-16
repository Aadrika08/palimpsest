"""Prospective11 small history checks; do not run before root's safe assembly.

Only existing small07/08/09/10 records, admission10 01/02 records and authenticated
Held are exercised. Never call admission main, resource/census support, observer,
auditor audit or vendors. Twenty-six unittest cases: six genuine (07-10 and
admission10 01/02), six changed transports, eleven fabricated receipts (07-11 and
admission01/11 outputs) and three manifest-first warm-read custody checks.
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

SOURCE=Path('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-qualification-11-admission.py')
spec=importlib.util.spec_from_file_location('held11_history_control',SOURCE)
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
raw=control.AUDITOR.read_bytes()
assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()==control.AUDITOR_SHA
auditor=types.ModuleType('held11_history_byte_holder');auditor.__file__=str(control.AUDITOR)
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
                self.assertEqual(control.absent()['historical_missing_receipts'],17)
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
        selected=set(control.HISTORICAL07_JSON)|set(control.HISTORICAL08_JSON)|set(control.HISTORICAL09_JSON)|set(control.HISTORICAL10_JSON)
        for epoch in ('07','08','09','10'):
            selected.update('runs/puck-cpu-held-qualification-'+epoch+'-external-cli.'+name for name in ('stdout','stderr'))
            selected.update('runs/puck-cpu-held-qualification-'+epoch+'/logs/'+name+'.log' for name in ('stdout','stderr'))
        pins=[]
        for path in sorted(selected):
            data=(control.ROOT/path).read_bytes()
            pins.append(dict(path=path,size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        self.assertEqual(len(pins),40)
        before=len(os.listdir('/proc/self/fd'))
        held=auditor.Held(time.monotonic()+10)
        try:
            # JSON and stream raw roles must survive first reads in hold_manifest;
            # an old07-only reservation fails when08 bytes are requested below.
            control.hold_manifest(held,pins,set(control.HISTORICAL07_JSON)|set(control.HISTORICAL08_JSON)|set(control.HISTORICAL09_JSON)|set(control.HISTORICAL10_JSON))
            self.assertEqual(control.check_consumed07(held)['status'],'FAILED_CONSUMED')
            self.assertEqual(control.check_consumed08(held)['status'],'FAILED_CONSUMED')
            self.assertEqual(control.check_consumed09(held)['status'],'FAILED_CONSUMED')
            self.assertEqual(control.check_consumed10(held)['status'],'FAILED_CONSUMED')
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
            with tempfile.TemporaryDirectory(prefix='held11-history-fixture-') as directory:
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


if __name__=='__main__':unittest.main(verbosity=2)
