"""Synthetic no-fit checks; no admitted corpus, checkpoints, or native execution."""
import hashlib
import io
import math
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import control_diagnostics_v2 as diagnostics


def features(n=4):
    x = np.zeros((n, 9), np.float32)
    x[:, 2] = .1
    return x


class DiagnosticsTests(unittest.TestCase):
    def test_heading_bins_keep_exact_zero_out_and_fixed_endpoints(self):
        values = np.array([0, 1e-7, 1e-6, .01, .12, .12000001, -1e-6])
        np.testing.assert_array_equal(diagnostics.heading_bins(values), [-1, 0, 0, 1, 2, 3, 0])

    def test_original_sign_gate_does_not_discard_small_nonzero_targets(self):
        x = features(3); y = np.array([[0, 0], [0, 1e-9], [0, -.2]], np.float64)
        a = np.array([[0, .3], [.06, -1e-9], [0, -.1]], np.float64)
        m = diagnostics.puck_metrics(x, y, a)
        self.assertEqual(m['nonzero_target_heading_count'], 2)
        self.assertEqual(m['heading_sign_agreement'], .5)
        self.assertEqual(m['approach_turn_only_count'], 2)
        self.assertEqual(m['approach_turn_only_leak'], .5)

    def test_empty_strata_report_none_and_do_not_pass(self):
        x = features(1); y = np.zeros((1, 2), np.float64)
        m = diagnostics.puck_metrics(x, y, y)
        self.assertIsNone(m['heading_sign_agreement']); self.assertFalse(m['original_gate_eligible'])
        self.assertEqual(diagnostics.error_summary(y, y)['count'], 1)
        self.assertIsNone(diagnostics.error_summary(y[:0], y[:0])['normalized_mse'])

    def test_nearest_only_training_references_earliest_tie_and_mode_match(self):
        train = features(3); train[:, 8] = [0, 1, 1]
        query = features(1); query[:, 8] = 1
        y = np.array([[0, .1], [0, .2], [0, .3]], np.float64)
        _, distance, indices = diagnostics.nearest(train, y, query, 'exact_mode_geometry', time.monotonic()+5)
        self.assertEqual(indices.tolist(), [1]); self.assertEqual(distance.tolist(), [0])
        _, _, indices = diagnostics.nearest(train, y, features(1), 'all9', time.monotonic()+5)
        self.assertEqual(indices.tolist(), [0])

    def test_exact_mode_without_reference_is_explicit_unsupported(self):
        x = features(2); query = features(1); query[:, 8] = 1
        action, distance, indices = diagnostics.nearest(x, np.zeros((2, 2)), query, 'exact_mode_geometry', time.monotonic()+5)
        self.assertEqual(indices.tolist(), [-1]); self.assertTrue(np.isnan(action).all()); self.assertTrue(np.isinf(distance).all())

    def test_loto_excludes_whole_layout_and_refits_reference_scales(self):
        x = features(4); x[:, 0] = [0, .01, .08, .09]
        seen = []
        actual = diagnostics.nearest
        def spy(ref, target, query, kind, deadline):
            seen.append((ref[:, 0].tolist(), query[:, 0].tolist()))
            return actual(ref, target, query, kind, deadline)
        with patch.object(diagnostics, 'nearest', side_effect=spy):
            calibration = diagnostics.support_calibration(x, np.zeros((4, 2)), np.array([1, 1, 2, 2]), 'all9', time.monotonic()+5)
        self.assertEqual(len(seen), 2)
        self.assertTrue(all(set(ref).isdisjoint(query) for ref, query in seen))
        self.assertEqual(calibration['rows'], 4)

    def test_fsm_freezes_contact_latch_for_active_cycle_and_completes_45th(self):
        state = diagnostics.initial_recovery()
        state, action, transition = diagnostics.recovery_step(state, True, .5, [.7, 0])
        self.assertTrue(transition['started']); self.assertEqual(state['count'], 1)
        for _ in range(43):
            state, action, transition = diagnostics.recovery_step(state, False, None, [.7, 0])
            self.assertTrue(state['previous_bad_contact'])
        state, action, transition = diagnostics.recovery_step(state, False, None, [.7, 0])
        self.assertTrue(transition['completed']); self.assertFalse(transition['started'])
        self.assertEqual(state['count'], 0); self.assertFalse(state['previous_bad_contact'])
        np.testing.assert_array_equal(action, np.array([-.35, -.1], np.float32))

    def test_completion_can_replace_old_action_and_zero_angle_chooses_positive(self):
        state = {'phase': 'back', 'count': 44, 'direction': -1., 'previous_bad_contact': False}
        after, action, change = diagnostics.recovery_step(state, True, 0., [.7, 0])
        self.assertEqual(after['direction'], 1); self.assertTrue(change['old_label_replaced'])
        np.testing.assert_array_equal(action, np.array([-.35, .1], np.float32))

    def test_same_fsm_normal_rule_has_no_panel_or_phase_input(self):
        x = np.zeros((3, 388), np.float32); x[:, 386] = 1; x[:, 385] = 1
        x[:, 384] = [0, 1, 0]
        a, transitions = diagnostics.recovery_rule(x)
        np.testing.assert_array_equal(a[:, 0], np.array([.7, -.35, -.35], np.float32))
        np.testing.assert_array_equal(a[:, 1], np.array([0, -.1, -.1], np.float32))
        self.assertEqual(transitions['started'], 1)

    def test_advice_replay_decodes_collision_angle_over_pi_and_validates_states(self):
        x = np.zeros((2, 388), np.float32); x[:, 386] = 1
        x[0, 384] = 1; x[0, 385] = np.float32(.5)/np.float32(math.pi)
        ep = {'run_id': 'synthetic', 'features': x, 'targets': np.zeros((2, 2), np.float32)}
        state = diagnostics.initial_recovery(); rows = []
        for tick in range(2):
            before = dict(state); bad = tick == 0; angle = .5 if bad else None
            state, action, change = diagnostics.recovery_step(state, bad, angle, [.7, 0])
            ep['targets'][tick] = action
            rows.append({'tick': tick, 'advice': {'before': before, 'after': state,
                'contact': {'bad': bad, 'angle': angle}, 'expert_action': action.tolist(), 'transition': change}})
        replay = diagnostics.advice_replay(ep, rows, time.monotonic()+5)
        self.assertEqual(replay['fsm_before_after_transitions'], 'exact')
        self.assertEqual(replay['started'], 1)
        rows[1]['advice']['before'] = {**rows[1]['advice']['before'], 'previous_bad_contact': False}
        with self.assertRaises(ValueError): diagnostics.advice_replay(ep, rows, time.monotonic()+5)

    def test_nav_circular_seam_error_and_unknown_old_phase(self):
        y = np.array([[.7, np.pi-.01]], np.float32)
        a = np.array([[.7, -np.pi+.01]], np.float32)
        ep = {'run_id': 'synthetic', 'features': np.zeros((1, 388), np.float32), 'targets': y}
        result = diagnostics.nav_decomposition([ep], [a])
        self.assertLess(result['all']['wrapped_heading_mae_radians'], .021)
        self.assertGreater(result['all']['linear_heading_mae_radians'], 6)
        self.assertEqual(result['all']['seam_crossing_rows'], 1)
        self.assertEqual(result['phase_status'], 'unknown')
        self.assertIsNone(result['active_recovery'])

    def test_npz_checks_hash_keys_shapes_dtype_and_trailing_content_before_allocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'synthetic.npz'; stream = io.BytesIO(); np.savez(stream, a=np.zeros((2, 2), np.float32)); path.write_bytes(stream.getvalue())
            pin = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
            actual = diagnostics.read_numeric(path, pin, {'a': (2, 2)}, time.monotonic()+5)
            self.assertEqual(actual['a'].shape, (2, 2))
            with self.assertRaises(ValueError): diagnostics.read_numeric(path, pin, {'a': (3, 2)}, time.monotonic()+5)
            with self.assertRaises(ValueError): diagnostics.read_numeric(path, {**pin, 'sha256': '0'*64}, {'a': (2, 2)}, time.monotonic()+5)
            bad = io.BytesIO()
            with zipfile.ZipFile(bad, 'w') as archive:
                npy = io.BytesIO(); np.save(npy, np.zeros((2, 2), np.float32)); archive.writestr('a.npy', npy.getvalue()+b'extra')
            path.write_bytes(bad.getvalue()); pin = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
            with self.assertRaises(ValueError): diagnostics.read_numeric(path, pin, {'a': (2, 2)}, time.monotonic()+5)

    def test_output_rejects_all_overlap_directions_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); owner = root/'owner'; owner.mkdir()
            for candidate in (owner/'out', root):
                with self.assertRaises(ValueError): diagnostics.guard_output(candidate, [owner])
            link = root/'link'; link.symlink_to(owner, target_is_directory=True)
            with self.assertRaises(ValueError): diagnostics.guard_output(link/'out', [])

    def test_deadline_applies_during_final_hash_and_identity_drift_is_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'x'; path.write_bytes(b'x')
            with self.assertRaises(TimeoutError): diagnostics.file_sha(path, time.monotonic()-1)
            pins = {str(path): diagnostics.file_sha(path, time.monotonic()+5)}
            path.write_bytes(b'y')
            with self.assertRaises(ValueError): diagnostics.verify_pins(pins, time.monotonic()+5)

    def test_bounded_output_refuses_without_partial_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = diagnostics.Output(Path(tmp)/'out', [], 8, min_free=0)
            with self.assertRaises(ValueError): output.write('report.json', b'123456789')
            self.assertFalse((output.path/'report.json').exists())


if __name__ == '__main__': unittest.main()
