"""Readout safety tests; fixtures do not qualify native feasibility."""
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest


class ReadoutTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('retained-readout.py')
        if not path.exists():
            self.fail('Independent readout is not implemented')
        spec = importlib.util.spec_from_file_location('recovery_readout', path)
        self.r = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.r)

    def test_restore_launcher_field_does_not_break_independent_comparison(self):
        self.r.compare_scored({'raw_audit_pass': True, 'goal': True,
                               'repeat_matches': True, 'supervision': {}},
                              {'raw_audit_pass': True, 'goal': True})
        with self.assertRaises(ValueError):
            self.r.compare_scored({'raw_audit_pass': True, 'goal': True},
                                  {'raw_audit_pass': True, 'goal': False})

    def test_unscored_started_owner_is_not_unattempted(self):
        self.assertEqual(self.r.disposition(owner_started=True, audit=None, scored=None),
                         'started-incomplete-or-unqualified')
        self.assertEqual(self.r.disposition(owner_started=False, audit=None, scored=None),
                         'unattempted')
        self.assertEqual(self.r.disposition(owner_started=True,
                         audit={'raw_audit_pass': True}, scored=None), 'audited-but-unscored')

    def test_audited_task_failure_is_distinct_from_completed_pass(self):
        self.assertEqual(self.r.disposition(owner_started=True, scored={}, audit={
            'raw_audit_pass': True, 'retained_task_failure': True}), 'audited-task-failure')
        self.assertEqual(self.r.disposition(owner_started=True, scored={}, audit={
            'raw_audit_pass': True, 'goal': True}), 'audited-recording')

    def test_restore_must_match_trace_state_and_exactly_five_ticks(self):
        one = {'raw_audit_pass': True, 'invariants_preserved': True,
               'continuation_ticks': 5, 'trace_digest': 'trace', 'post_state_digest': 'state'}
        self.assertTrue(self.r.repeat_equal([one, dict(one)]))
        for key, value in [('trace_digest', 'different'), ('post_state_digest', None),
                           ('continuation_ticks', 4), ('invariants_preserved', False)]:
            self.assertFalse(self.r.repeat_equal([one, {**one, key: value}]))
        self.assertFalse(self.r.repeat_equal([one]))

    def test_newer_pending_receipt_survives_stale_canonical(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'execution.json').write_text(json.dumps({'elapsed_seconds': 0, 'status': 'running'}))
            (root/'execution.json.pending').write_text(json.dumps({'elapsed_seconds': 20, 'status': 'execution-failed'}))
            receipt, path, available = self.r.execution_receipt(root)
            self.assertEqual(receipt['status'], 'execution-failed')
            self.assertEqual(path.name, 'execution.json.pending')
            self.assertEqual(len(available), 2)
            (root/'execution.json.pending').write_text('{')
            receipt, path, available = self.r.execution_receipt(root)
            self.assertEqual(path.name, 'execution.json')

    def test_index_detects_payload_changes_and_path_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'chunk').write_bytes(b'hello')
            entries = [{'path': 'chunk', 'bytes': 5,
                        'sha256': '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'}]
            self.assertEqual(self.r.verify_index(root, entries, time.monotonic()+10), ['chunk'])
            (root/'chunk').write_bytes(b'wrong')
            with self.assertRaises(ValueError):
                self.r.verify_index(root, entries, time.monotonic()+10)
            with self.assertRaises(ValueError):
                self.r.verify_index(root, [{**entries[0], 'path': '../outside'}], time.monotonic()+10)

    def test_selection_cannot_skip_unattempted_candidate_or_missing_retreat(self):
        specs = [{'id': 'first', 'profile_sha256': 'one'}, {'id': 'second', 'profile_sha256': 'two'}]
        passed = {'raw_audit_pass': True, 'acquired': True, 'goal': True,
                  'first_commitment_blocked': True, 'retreat_completed': True, 'replans': 1}
        rows = [{'job_id': 'first', 'disposition': 'unattempted'},
                {'job_id': 'second', 'audit': passed, 'disposition': 'audited-recording'}]
        self.assertFalse(self.r.selection_valid(specs, rows, 'two'))
        rows[0] = {'job_id': 'first', 'disposition': 'audited-task-failure',
                   'audit': {'raw_audit_pass': True, 'retained_task_failure': True}}
        self.assertTrue(self.r.selection_valid(specs, rows, 'two'))
        rows[1]['audit'] = {**passed, 'retreat_completed': False}
        self.assertFalse(self.r.selection_valid(specs, rows, 'two'))

    def test_restore_cannot_use_historical_or_development_snapshot(self):
        source = {'snapshot_path': '/fresh/south-prefix/initial.snp',
                  'snapshot_sha256': 'hash', 'invariant': 'state'}
        job = {'snapshot_path': source['snapshot_path'], 'snapshot_sha256': 'hash',
               'expected_invariant': 'state'}
        self.r.verify_restore_source(job, source)
        with self.assertRaises(ValueError):
            self.r.verify_restore_source({**job, 'snapshot_path': '/historical/initial.snp'}, source)

    def test_resource_stop_is_not_mislabeled_as_task_failure(self):
        rows = [{'disposition': 'audited-task-failure'}, {'disposition': 'unattempted'}]
        self.assertEqual(self.r.stop_status(rows, [], selection_ok=False),
                         'infrastructure-or-evidence-stop')
        self.assertEqual(self.r.stop_status([{'disposition': 'audited-task-failure'}], [], selection_ok=False),
                         'audited-task-stop')


if __name__ == '__main__':
    unittest.main()
