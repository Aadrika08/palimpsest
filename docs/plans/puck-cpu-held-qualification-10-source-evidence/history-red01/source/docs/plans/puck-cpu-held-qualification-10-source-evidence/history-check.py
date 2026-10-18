"""Prospective10 small history checks; do not run before root's safe assembly.

Only existing small07/08/09 records and authenticated Held are exercised. Never
call admission main, resource/census support, observer, auditor audit or vendors.
Thirteen unittest cases: genuine07/08, changed transports07/08, four fabricated
historical receipt absences, and combined manifest-first warm-read custody.
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

SOURCE=Path('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-qualification-10-admission.py')
spec=importlib.util.spec_from_file_location('held10_history_control',SOURCE)
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
raw=control.AUDITOR.read_bytes()
assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()==control.AUDITOR_SHA
auditor=types.ModuleType('held10_history_byte_holder');auditor.__file__=str(control.AUDITOR)
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
                self.assertEqual(control.absent()['historical_missing_receipts'],16)
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
        selected=set(control.HISTORICAL07_JSON)|set(control.HISTORICAL08_JSON)|set(control.HISTORICAL09_JSON)
        for epoch in ('07','08','09'):
            selected.update('runs/puck-cpu-held-qualification-'+epoch+'-external-cli.'+name for name in ('stdout','stderr'))
            selected.update('runs/puck-cpu-held-qualification-'+epoch+'/logs/'+name+'.log' for name in ('stdout','stderr'))
        pins=[]
        for path in sorted(selected):
            data=(control.ROOT/path).read_bytes()
            pins.append(dict(path=path,size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        self.assertEqual(len(pins),29)
        before=len(os.listdir('/proc/self/fd'))
        held=auditor.Held(time.monotonic()+10)
        try:
            # JSON and stream raw roles must survive first reads in hold_manifest;
            # an old07-only reservation fails when08 bytes are requested below.
            control.hold_manifest(held,pins,set(control.HISTORICAL07_JSON)|set(control.HISTORICAL08_JSON)|set(control.HISTORICAL09_JSON))
            self.assertEqual(control.check_consumed07(held)['status'],'FAILED_CONSUMED')
            self.assertEqual(control.check_consumed08(held)['status'],'FAILED_CONSUMED')
            self.assertEqual(control.check_consumed09(held)['status'],'FAILED_CONSUMED')
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
            with tempfile.TemporaryDirectory(prefix='held10-history-fixture-') as directory:
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


if __name__=='__main__':unittest.main(verbosity=2)
