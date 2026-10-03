"""Synthetic fixture verification only; no trained model, simulator or exhibition."""
from contextlib import nullcontext, redirect_stdout, redirect_stderr
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import xml.etree.ElementTree as ET

import numpy as np
from palimpsest import afterimage, cli
from palimpsest.male_policy import IDENTITY_HASHES, PROFILE


class StubPolicy:
    def __init__(self, bad=False):
        self.resets, self.calls, self.bad = 0, [], bad

    def reset(self):
        self.resets += 1
        self.state = 0

    def act(self, observation):
        self.calls.append(observation)
        # Equal first/second responses exercise retained coincident points.
        raw = np.array([0., 0.] if self.state < 2 else [1., -1.], dtype=np.float32)
        self.state += 1
        result = {'action': np.tanh(raw) * np.array([3., math.pi], dtype=np.float32),
                  'raw_output': raw, 'encoded_input': np.full(136, self.state, dtype=np.float32)}
        if self.bad:
            result['raw_output'][0] = np.nan
        return result


class AfterimageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.frames = np.stack([np.full((128, 128, 3), value, dtype=np.uint8) for value in (0, 64, 255)])
        self.input = self.root / 'stimulus.json'
        self.identity = {'controller': 'male-original', 'variant': 'original', 'profile': PROFILE,
                         **{name: 'a' * 64 for name in IDENTITY_HASHES}}
        self.spec = {'schema_version': 1, 'title': 'Fixture <portrait>', 'creator': 'test fixture',
                     'frame_file': 'frames.npy', 'frame_file_sha256': '', 'source_times_seconds': [4., 4.04, 4.2],
                     'rights': {'basis': 'self_created', 'statement': 'Authored synthetic test frames.',
                                'attribution': 'Fixture author', 'authorized_processing_and_retention': True,
                                'subject_consent': 'no_identifiable_people'}}
        self.save_frames(self.frames)

    def save_frames(self, frames):
        np.save(self.root / 'frames.npy', frames)
        self.spec['frame_file_sha256'] = hashlib.sha256((self.root / 'frames.npy').read_bytes()).hexdigest()
        self.save_spec()

    def save_spec(self):
        self.input.write_text(json.dumps(self.spec))

    def record(self, policy=None):
        self.run = self.root / uuid.uuid4().hex
        policy = policy or StubPolicy()
        afterimage._record(afterimage.load_stimulus(self.input), policy, self.run, self.identity,
                           evidence='synthetic fixture verification')
        return policy

    def test_exact_alignment_and_one_reset_per_sequence(self):
        policy = self.record()
        self.assertEqual(policy.resets, 1)
        self.assertEqual(len(policy.calls), 3)
        manifest, rows, _, _ = afterimage._load_recording(self.run)
        self.assertEqual(manifest['evidence'], 'synthetic fixture verification')
        self.assertEqual([r['model_time_seconds'] for r in rows], [.02, .04, .06])
        self.assertEqual([r['source_timestamp_seconds'] for r in rows], [4., 4.04, 4.2])
        from palimpsest.records import iter_ticks
        for index, row in enumerate(iter_ticks(self.run / 'recording')):
            np.testing.assert_array_equal(row['cam_left'], self.frames[index])
            np.testing.assert_array_equal(row['cam_right'], self.frames[index])
            np.testing.assert_array_equal(row['encoded_input'], np.full(136, index + 1, np.float32))
            np.testing.assert_array_equal(row['sensors'], np.array([0, 0, 1, 0], np.float32))
            self.assertNotIn('pose', row)

    def test_mapping_coincident_points_determinism_and_accessibility(self):
        self.record()
        left, right = self.root / 'left.svg', self.root / 'right.svg'
        afterimage.render(self.run, left)
        afterimage.render(self.run, right)
        self.assertEqual(left.read_bytes(), right.read_bytes())
        svg = ET.fromstring(left.read_bytes())
        ns = {'s': 'http://www.w3.org/2000/svg'}
        meta = json.loads(svg.find('s:metadata', ns).text)
        rows = meta['alignment']
        self.assertEqual(rows[0]['point'], [0., -0.])
        self.assertEqual(rows[1]['point'], [0., -0.])
        self.assertAlmostEqual(rows[2]['point'][0], 360 * rows[2]['action'][0] / 3)
        self.assertAlmostEqual(rows[2]['point'][1], -360 * rows[2]['action'][1] / math.pi)
        points = svg.find('.//s:polyline', ns).attrib['points'].split()
        self.assertEqual(len(points), 3)
        self.assertEqual(points[0], points[1])
        self.assertEqual(svg.attrib['aria-labelledby'], 'title description')
        self.assertIn('Not fly perception', left.read_text())
        self.assertNotIn('<image', left.read_text())

    def test_input_dtype_shape_layout_and_extra_payload_rejected(self):
        for frames in (self.frames.astype(np.float32), self.frames[:, :64], self.frames[:0], np.asfortranarray(self.frames)):
            with self.subTest(shape=frames.shape, dtype=frames.dtype):
                self.save_frames(frames)
                with self.assertRaises(ValueError):
                    afterimage.load_stimulus(self.input)
        self.save_frames(self.frames)
        with (self.root / 'frames.npy').open('ab') as stream:
            stream.write(b'extra')
        self.spec['frame_file_sha256'] = hashlib.sha256((self.root / 'frames.npy').read_bytes()).hexdigest()
        self.save_spec()
        with self.assertRaisesRegex(ValueError, 'exact C-order'):
            afterimage.load_stimulus(self.input)

    def test_rights_hash_timestamps_and_path_rejected(self):
        original = json.loads(json.dumps(self.spec))
        changes = [('source_times_seconds', [0, 0, 1]), ('source_times_seconds', [0, 1, 121]),
                   ('source_times_seconds', [0, True, 1]), ('source_times_seconds', list(range(601))),
                   ('frame_file_sha256', '0' * 64), ('frame_file', '../frames.npy')]
        for key, value in changes:
            self.spec = {**original, key: value}
            self.save_spec()
            with self.subTest(key=key, value=str(value)[:30]), self.assertRaises(ValueError):
                afterimage.load_stimulus(self.input)
        self.spec = original
        self.spec['rights']['authorized_processing_and_retention'] = False
        self.save_spec()
        with self.assertRaisesRegex(ValueError, 'rights'):
            afterimage.load_stimulus(self.input)
        self.input.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            afterimage.load_stimulus(self.input)

    def test_input_size_checked_before_load(self):
        with patch.object(afterimage, 'MAX_INPUT_BYTES', 64):
            with self.assertRaisesRegex(ValueError, 'oversized'):
                afterimage.load_stimulus(self.input)

    def test_failed_inference_and_changed_source_are_not_renderable(self):
        with self.assertRaisesRegex(ValueError, 'finite'):
            self.record(StubPolicy(bad=True))
        with self.assertRaisesRegex(ValueError, 'completed'):
            afterimage.render(self.run, self.root / 'bad.svg')
        stimulus = afterimage.load_stimulus(self.input)
        self.input.write_text(self.input.read_text() + ' ')
        run = self.root / uuid.uuid4().hex
        with self.assertRaisesRegex(ValueError, 'source changed'):
            afterimage._record(stimulus, StubPolicy(), run, self.identity, evidence='synthetic fixture verification')
        self.assertEqual(json.loads((run / 'recording/manifest.json').read_text())['status'], 'running')

    def test_final_asset_check_failure_does_not_complete(self):
        run = self.root / uuid.uuid4().hex
        def fail():
            raise ValueError('changed assets')
        with self.assertRaisesRegex(ValueError, 'changed assets'):
            afterimage._record(afterimage.load_stimulus(self.input), StubPolicy(), run, self.identity,
                               evidence='synthetic fixture verification', before_finish=fail)
        with self.assertRaisesRegex(ValueError, 'completed'):
            afterimage.render(run, self.root / 'bad.svg')

    def test_corruption_and_alignment_rejected(self):
        self.record()
        path = self.run / 'recording/manifest.json'
        manifest = json.loads(path.read_text())
        manifest['stimulus']['manifest']['source_times_seconds'][1] = 4.1
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'alignment'):
            afterimage.render(self.run, self.root / 'bad.svg')
        manifest['stimulus']['manifest']['source_times_seconds'][1] = 4.04
        path.write_text(json.dumps(manifest))
        chunk = self.run / 'recording/chunks/000000.npz'
        with chunk.open('ab') as stream:
            stream.write(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            afterimage.render(self.run, self.root / 'bad.svg')

    def test_actual_evidence_requires_successful_supervision(self):
        self.record()
        path = self.run / 'recording/manifest.json'
        manifest = json.loads(path.read_text())
        manifest['evidence'] = 'actual model inference'
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'missing'):
            afterimage.render(self.run, self.root / 'bad.svg')
        receipt = self.run / 'supervisor.json'
        receipt.write_text(json.dumps({'status': 'timeout', 'returncode': -15, 'timeout_seconds': 120}))
        with self.assertRaisesRegex(ValueError, 'supervisor'):
            afterimage.render(self.run, self.root / 'bad.svg')

    def test_invalid_response_shape_dtype_and_scaling_rejected(self):
        for name, replacement in [('encoded_input', np.zeros(135, np.float32)),
                                  ('raw_output', np.zeros(2, np.float64)),
                                  ('action', np.array([1, 1], np.float32))]:
            result = {'action': np.zeros(2, np.float32), 'raw_output': np.zeros(2, np.float32),
                      'encoded_input': np.zeros(136, np.float32)}
            result[name] = replacement
            with self.subTest(name=name), self.assertRaises(ValueError):
                afterimage._response(result)

    def test_exclusive_output_budget_and_partial_cleanup(self):
        self.record()
        output = self.root / 'portrait.svg'
        output.write_text('existing')
        with self.assertRaises(FileExistsError):
            afterimage.render(self.run, output)
        self.assertEqual(output.read_text(), 'existing')
        with self.assertRaisesRegex(ValueError, 'outside authoritative'):
            afterimage.render(self.run, self.run / 'portrait.svg')
        missing = self.root / 'missing.svg'
        with patch.object(afterimage, 'MAX_SVG_BYTES', 1), self.assertRaisesRegex(ValueError, 'byte cap'):
            afterimage.render(self.run, missing)
        self.assertFalse(missing.exists())
        manifest, rows, paths, fingerprint = afterimage._load_recording(self.run)
        with patch.object(afterimage, '_load_recording', return_value=(manifest, rows, paths, fingerprint)), \
                patch.object(afterimage.artifacts, '_fingerprint', return_value=('changed',)), \
                self.assertRaisesRegex(ValueError, 'changed during'):
            afterimage.render(self.run, missing)
        self.assertFalse(missing.exists())

    def test_render_in_fresh_process_does_not_import_model_runtime(self):
        self.record()
        script = 'import sys; from palimpsest.afterimage import render; render(sys.argv[1],sys.argv[2]); assert "torch" not in sys.modules; assert "mujoco" not in sys.modules'
        result = subprocess.run([sys.executable, '-c', script, str(self.run), str(self.root / 'pure.svg')],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_record_dispatch_is_bounded_and_separate(self):
        output = self.root / uuid.uuid4().hex
        with patch('palimpsest.storage.StorageBudget.lock', return_value=nullcontext()), \
                patch('palimpsest.male_policy.resolve_profile', return_value=(self.identity, {})), \
                patch('palimpsest.evaluate.bounded_process', return_value={'status': 'timeout'}) as supervisor, \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = cli.main(['--assets', str(self.root.parent / (self.root.name + '-assets')), 'afterimage', 'record', str(self.input),
                               '--controller', 'male-original', '--output', str(output), '--min-free-bytes', '0'])
        self.assertEqual(status, 1)
        call = supervisor.call_args
        self.assertEqual(call.args[2], 120)
        self.assertEqual(call.args[0][1:3], ['-m', 'palimpsest.afterimage'])
        config = json.loads(call.args[0][3])
        self.assertEqual(config['identity'], self.identity)
        self.assertEqual(config['expected_stimulus']['manifest'], self.spec)
        self.assertLessEqual(call.kwargs['log_max_bytes'], 1024**2)

    def test_cli_render_uses_existing_storage_without_model(self):
        self.record()
        output = self.root / 'cli.svg'
        with patch('palimpsest.storage.StorageBudget.lock', return_value=nullcontext()), \
                patch('palimpsest.male_policy.load_pinned_policy', side_effect=AssertionError('no inference')), \
                redirect_stdout(io.StringIO()):
            status = cli.main(['--assets', str(self.root.parent / (self.root.name + '-assets')), 'afterimage', 'render', str(self.run),
                               '--output', str(output), '--min-free-bytes', '0'])
        self.assertEqual(status, 0)
        self.assertTrue(output.is_file())


if __name__ == '__main__':
    unittest.main()
