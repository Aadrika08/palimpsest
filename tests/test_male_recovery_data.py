"""Research admission fixtures; no Torch, native decoder, or simulation."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_male_recovery_data as data
import collect_male_recovery as recovery
from test_male_recovery_collection import teacher_fixture


def fixture():
    teacher, env = teacher_fixture()
    ownership = {'geometries': [{'geom_id': 0, 'name': 'floor', 'owner': 'world'},
        {'geom_id': 1, 'name': 'base_geom', 'owner': 'robot'},
        {'geom_id': 2, 'name': 'obstacle1', 'owner': 'world'}]}
    rows, raw_rows, active = [], [], True
    for tick in range(67):
        env.contact = 21 <= tick <= 23
        query = recovery.query_teacher(teacher, env)
        active = recovery.prefix_for_query(tick, active, query['contact']['bad'])
        action = recovery.executed_action(tick, query['expert_action'], active)
        row = {**query, 'tick': tick, 'prefix': active, 'action': action,
               'stage0_intended_contact': env.contact, 'callback_count': 10}
        raw = {'episode': np.array(0), 'tick': np.array(tick),
            'simulation_time': np.array((tick+1)*.02), 'eyes': np.ones(2, bool),
            'cam_left': np.zeros((128, 128, 3), np.uint8),
            'cam_right': np.zeros((128, 128, 3), np.uint8),
            'sensors': np.array([env.contact, .1 if env.contact else 0., 1., 0.], np.float32),
            'action': np.array(action, np.float32),
            'recovery_expert_action': np.array(query['expert_action'], np.float32),
            'recovery_prefix': np.array(active),
            'recovery_teacher_before': np.array([query['before'][k] for k in ('count', 'direction', 'previous_bad_contact')]),
            'recovery_teacher_after': np.array([query['after'][k] for k in ('count', 'direction', 'previous_bad_contact')]),
            'recovery_transitions': np.array([query['transition'][k] for k in ('started', 'completed', 'old_label_replaced')]),
            'body_contact_ids': np.zeros((11, 128, 2), np.int16),
            'body_contact_counts': np.zeros(11, np.int16),
            'body_contact_classes': np.zeros((11, 128), np.uint8),
            'body_contact_distances': np.zeros((11, 128), np.float64)}
        if env.contact:
            raw['body_contact_counts'][:] = 1
            raw['body_contact_ids'][:, 0] = [1, 2]
            raw['body_contact_classes'][:, 0] = 3
            raw['body_contact_distances'][:, 0] = -.001
        row['contact_counts'] = raw['body_contact_counts'].tolist()
        rows.append(row); raw_rows.append(raw)
    result = {'rows': rows, 'contact_ownership': ownership,
        'collection_boundary': 'coverage_complete',
        'final_state': {'phase': 'paused', 'last_outcome': None},
        'coverage': recovery.score_coverage(rows)}
    return raw_rows, result


class RecoveryData(unittest.TestCase):
    def test_full_executed_targets_right_censored_windows_and_private_fields(self):
        raw, result = fixture()
        episode, admission = data.admit_rows(raw, result, 'fixture')
        self.assertEqual(episode['features'].shape, (67, 388))
        np.testing.assert_array_equal(episode['targets'], np.stack([row['action'] for row in raw]))
        self.assertFalse(np.array_equal(episode['targets'][:21], np.stack([row['recovery_expert_action'] for row in raw[:21]])))
        self.assertEqual(admission['windows'], [32, 32, 3])
        self.assertEqual(admission['ending'], 'right_censored_coverage_complete')
        self.assertEqual(admission['final_phase'], 'paused')
        changed = copy.deepcopy(raw)
        for row in changed: row['teacher_private_pose'] = np.array([999., 999.])
        np.testing.assert_array_equal(data.admit_rows(changed, result, 'fixture')[0]['features'], episode['features'])

    def test_rejects_substituted_expert_cropped_prefix_forged_clearance_and_history(self):
        raw, result = fixture()
        changed = copy.deepcopy(raw); changed[0]['action'] = changed[0]['recovery_expert_action'].copy()
        with self.assertRaises(ValueError): data.admit_rows(changed, result, 'fixture')
        with self.assertRaises(ValueError): data.admit_rows(raw[21:], {**result, 'rows': result['rows'][21:]}, 'fixture')
        forged = copy.deepcopy(result); forged['rows'][66]['stage0_intended_contact'] = True
        with self.assertRaisesRegex(ValueError, 'clearance'): data.admit_rows(raw, forged, 'fixture')
        changed = copy.deepcopy(raw); changed[32]['recovery_teacher_after'][0] += 1
        with self.assertRaises(ValueError): data.admit_rows(changed, result, 'fixture')

    def test_protocol_exact_split_pair_and_no_held_out_admission(self):
        p = data.protocol()
        self.assertEqual(p['counts'], {'baseline_train': 1983, 'recovery_train': 134, 'train': 2117, 'dev': 1228, 'held_out': 0})
        self.assertEqual([(v['training_seed'], v['variant']) for v in p['models']],
                         [(seed, variant) for seed in (10, 11, 12) for variant in ('original', 'degree_rewired')])
        self.assertEqual(p['training']['epochs'], 20)
        self.assertEqual(p['training']['window'], 32)
        self.assertEqual(p['recovery_windows'], [32, 32, 3])
        self.assertEqual(p['qualification_claims'], [])
        # Enabled runtime suites may already have imported either module. Inspect
        # adapter imports in a fresh interpreter without changing parent state.
        completed = subprocess.run([sys.executable, '-c',
            "import prepare_male_recovery_data, sys; assert not ({'torch', 'mujoco'} & set(sys.modules))"],
            cwd=ROOT, env={**os.environ, 'PYTHONPATH': os.pathsep.join((str(ROOT/'src'), str(ROOT/'scripts')))},
            capture_output=True, text=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr[-1024:])

    def test_frozen_file_inventory_rejects_changed_missing_and_extra_bytes(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'recording').mkdir()
            file = root/'recording/manifest.json'; file.write_bytes(b'{}')
            entries = [{'path': 'recording/manifest.json', 'bytes': 2, 'sha256': hashlib.sha256(b'{}').hexdigest()}]
            self.assertEqual(data.inventory(root, entries)[0]['bytes'], 2)
            file.write_bytes(b'[]')
            with self.assertRaises(ValueError): data.inventory(root, entries)
            file.write_bytes(b'{}'); (root/'recording/extra').write_bytes(b'x')
            with self.assertRaises(ValueError): data.inventory(root, entries)
            (root/'recording/extra').unlink(); file.unlink()
            with self.assertRaises(ValueError): data.inventory(root, entries)

    def test_duplicate_episode_split_and_payload_rejected(self):
        episode = {'run_id': 'a', 'episode': 0, 'features': np.zeros((1, 388), np.float32),
                   'targets': np.zeros((1, 2), np.float32)}
        with self.assertRaises(ValueError): data.validate_splits({'train': [episode], 'dev': [episode], 'held_out': []}, check_counts=False)
        different_id = {**episode, 'run_id': 'b'}
        with self.assertRaises(ValueError): data.validate_splits({'train': [episode], 'dev': [different_id], 'held_out': []}, check_counts=False)
        with self.assertRaises(ValueError): data.validate_splits({'train': [episode], 'dev': [], 'held_out': [different_id]}, check_counts=False)

    def test_v2_loader_contract_still_rejects_paused_recovery_source(self):
        from palimpsest.male_research import validate_collection
        source = {'scenario': 'reproduction', 'texture': 'checker', 'episodes': [{'episode': 0, 'seed': 1000, 'ticks': 67}],
                  'final_phase': 'paused', 'last_outcome': None}
        with self.assertRaisesRegex(ValueError, 'natural terminal'):
            validate_collection({'splits': {'train': [source], 'dev': [], 'held_out': []}}, 'development')

    def test_publication_fsync_deadline_failure_retains_pending_only_and_no_overwrite(self):
        for failure in ('fsync', 'deadline', None):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest = {'status': 'fixture', **data.reader_identity()}
                if failure == 'fsync':
                    with patch.object(data.os, 'fsync', side_effect=OSError('injected fsync failure')):
                        with self.assertRaises(OSError): data.publish_manifest(root, manifest, time.monotonic()+1)
                elif failure == 'deadline':
                    with self.assertRaises(TimeoutError): data.publish_manifest(root, manifest, 0.)
                else:
                    data.publish_manifest(root, manifest, time.monotonic()+1)
                    before = (root/'data-manifest.json').read_bytes()
                    with self.assertRaises(FileExistsError): data.publish_manifest(root, {**manifest, 'status': 'changed'}, time.monotonic()+1)
                    self.assertEqual((root/'data-manifest.json').read_bytes(), before)
                self.assertEqual((root/'data-manifest.json').exists(), failure is None)
                self.assertEqual((root/'data-manifest.pending').exists(), failure is not None)

    def test_output_overlap_rejected_before_directory_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root/'baseline'/'collection.json'; baseline.parent.mkdir()
            recovery_report = root/'recovery'/'report.json'; recovery_report.parent.mkdir()
            for output in (baseline.parent/'new', recovery_report.parent/'new', root):
                with self.assertRaisesRegex(ValueError, 'corpus trees'):
                    data.output_path(output, baseline, recovery_report)
            self.assertFalse((baseline.parent/'new').exists())
            self.assertFalse((recovery_report.parent/'new').exists())
            self.assertEqual(data.output_path(root/'fresh', baseline, recovery_report), root/'fresh')

    def test_reader_and_adapter_late_drift_cannot_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = {'status': 'fixture', **data.reader_identity()}
            original = data.artifacts._read
            drift = False
            def changed_read(path, maximum):
                payload = original(path, maximum)
                return payload+b'\n' if drift and Path(path) == Path(data.__file__) else payload
            def fsync(_):
                nonlocal drift
                drift = True
            with patch.object(data.artifacts, '_read', side_effect=changed_read), patch.object(data.os, 'fsync', side_effect=fsync):
                with self.assertRaisesRegex(ValueError, 'drift'): data.publish_manifest(root, manifest, time.monotonic()+1)
            self.assertTrue((root/'data-manifest.pending').exists())
            self.assertFalse((root/'data-manifest.json').exists())


if __name__ == '__main__': unittest.main()
