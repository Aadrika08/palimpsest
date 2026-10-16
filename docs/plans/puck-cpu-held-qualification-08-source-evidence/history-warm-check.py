"""Small control checks only: no admission main, payload census or runtime."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import types
import unittest

SOURCE=Path('/home/utkarsh/.codex/worktrees/0071/brain/docs/plans/puck-cpu-held-qualification-08-admission.py')
spec=importlib.util.spec_from_file_location('held08_history_control',SOURCE)
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
raw=control.AUDITOR.read_bytes()
assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()==control.AUDITOR_SHA
auditor=types.ModuleType('held08_history_byte_holder');auditor.__file__=str(control.AUDITOR)
exec(compile(raw,str(control.AUDITOR),'exec'),auditor.__dict__)


class HistoryChecks(unittest.TestCase):
    def test_genuine07_failure_has_no_success_or_closure_receipt(self):
        before=len(os.listdir('/proc/self/fd'))
        held=auditor.Held(time.monotonic()+10)
        try:
            value=control.check_consumed07(held)
            self.assertEqual(value['status'],'FAILED_CONSUMED')
            self.assertFalse(value['parent_closure_receipt'])
            self.assertFalse(value['completed_four_import_receipt'])
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_manifest_first_reads_preserve_historical07_stream_bytes(self):
        freeze=json.loads((control.ROOT/'docs/plans/puck-cpu-held-qualification-08-freeze.json').read_bytes())
        selected={
            'runs/puck-cpu-held-qualification-07-external-cli.stdout',
            'runs/puck-cpu-held-qualification-07-external-cli.stderr',
            'runs/puck-cpu-held-qualification-07/logs/stdout.log',
            'runs/puck-cpu-held-qualification-07/logs/stderr.log',
        }|set(control.HISTORICAL07_JSON)
        pins=[row for row in freeze['pins'] if row['path'] in selected]
        self.assertEqual(len(pins),9)
        before=len(os.listdir('/proc/self/fd'))
        held=auditor.Held(time.monotonic()+10)
        try:
            control.hold_manifest(held,pins,set(control.HISTORICAL07_JSON))
            value=control.check_consumed07(held)
            self.assertEqual(value['status'],'FAILED_CONSUMED')
        finally:held.close()
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_changed_transport_is_refused(self):
        class ChangedTransport:
            def json(self,path,**kwargs):
                value=json.loads(Path(path).read_bytes())
                value['observed_returncode']=0
                return value,(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
        with self.assertRaises(AssertionError):control.check_consumed07(ChangedTransport())

    def check_missing(self,leaf):
        original=control.ROOT
        try:
            with tempfile.TemporaryDirectory(prefix='held08-history-fixture-') as directory:
                control.ROOT=Path(directory)
                path=control.ROOT/'runs/puck-cpu-held-qualification-07'/leaf
                path.parent.mkdir(parents=True);path.write_bytes(b'fabricated receipt\n')
                with self.assertRaises(AssertionError):control.absent()
        finally:control.ROOT=original

    def test_fabricated07_result_is_refused(self):self.check_missing('result.json')
    def test_fabricated07_baseline_after_is_refused(self):self.check_missing('baseline-after.json')


if __name__=='__main__':unittest.main(verbosity=2)
