"""Afterimage with recorded eye pairs (user decision: both eyes, as the model sees them).

Synthetic fixture verification only; the single-frame v1 interface is unchanged.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import uuid
import xml.etree.ElementTree as ET

import numpy as np

from palimpsest import afterimage
from palimpsest.male_policy import IDENTITY_HASHES, PROFILE
from palimpsest.records import iter_ticks
from test_afterimage import StubPolicy

SOURCE = {'kind': 'public lab recording', 'run_id': 'a' * 32, 'episodes': [0, 1], 'tick_stride': 5,
          'recording_files_sha256': {'recording/manifest.json': 'b' * 64}}


class PairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        left = [np.full((128, 128, 3), value, np.uint8) for value in (10, 20, 30)]
        right = [np.full((128, 128, 3), value, np.uint8) for value in (200, 210, 220)]
        self.frames = np.stack([np.stack(pair) for pair in zip(left, right)])
        np.save(self.root / 'frames.npy', self.frames)
        self.spec = {'schema_version': 2, 'title': 'Recorded eyes', 'creator': 'Palimpsest public lab run',
                     'frame_file': 'frames.npy', 'frame_file_sha256': hashlib.sha256((self.root / 'frames.npy').read_bytes()).hexdigest(),
                     'source_times_seconds': [0., .1, .2], 'eyes': 'recorded-pair', 'source': SOURCE,
                     'rights': {'basis': 'self_created', 'statement': 'Simulator camera frames from a public lab recording.',
                                'attribution': 'Palimpsest', 'authorized_processing_and_retention': True,
                                'subject_consent': 'no_identifiable_people'}}
        (self.root / 'stimulus.json').write_text(json.dumps(self.spec))
        self.identity = {'controller': 'male-original', 'variant': 'original', 'profile': PROFILE,
                         **{name: 'a' * 64 for name in IDENTITY_HASHES}}

    def record(self):
        run = self.root / uuid.uuid4().hex
        policy = StubPolicy()
        afterimage._record(afterimage.load_stimulus(self.root / 'stimulus.json'), policy, run, self.identity,
                           evidence='synthetic fixture verification')
        return run, policy

    def test_each_eye_reaches_its_own_channel(self):
        run, policy = self.record()
        self.assertEqual(policy.resets, 1)
        for index, observation in enumerate(policy.calls):
            np.testing.assert_array_equal(observation['cam_left'], self.frames[index, 0])
            np.testing.assert_array_equal(observation['cam_right'], self.frames[index, 1])
        for index, row in enumerate(iter_ticks(run / 'recording')):
            np.testing.assert_array_equal(row['cam_left'], self.frames[index, 0])
            np.testing.assert_array_equal(row['cam_right'], self.frames[index, 1])
        manifest, rows, _, _ = afterimage._load_recording(run)
        self.assertEqual(manifest['interface'], afterimage.INTERFACE_PAIR)
        self.assertEqual(manifest['stimulus']['manifest']['source'], SOURCE)
        self.assertEqual([r['frame_sha256'] for r in rows],
                         [[hashlib.sha256(f[0].tobytes()).hexdigest(), hashlib.sha256(f[1].tobytes()).hexdigest()] for f in self.frames])

    def test_render_records_the_pair_interface_without_embedding_frames(self):
        run, _ = self.record()
        output = self.root / 'portrait.svg'
        afterimage.render(run, output)
        svg = ET.fromstring(output.read_bytes())
        meta = json.loads(svg.find('{http://www.w3.org/2000/svg}metadata').text)
        self.assertEqual(meta['interface'], afterimage.INTERFACE_PAIR)
        self.assertEqual(len(meta['alignment']), 3)
        self.assertNotIn('<image', output.read_text())

    def test_pair_shape_and_declaration_are_strict(self):
        for change in ({'eyes': 'same-frame'}, {'source': None}, {'schema_version': 3}):
            with self.subTest(change=change):
                (self.root / 'stimulus.json').write_text(json.dumps({**self.spec, **change}))
                with self.assertRaises(ValueError):
                    afterimage.load_stimulus(self.root / 'stimulus.json')
        np.save(self.root / 'frames.npy', self.frames[:, 0])  # a single eye is not a pair
        spec = {**self.spec, 'frame_file_sha256': hashlib.sha256((self.root / 'frames.npy').read_bytes()).hexdigest()}
        (self.root / 'stimulus.json').write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, 'T×2×128×128×3'):
            afterimage.load_stimulus(self.root / 'stimulus.json')

    def test_six_hundred_pairs_fit_the_input_and_record_caps(self):
        pair_bytes = 600 * 2 * 128 * 128 * 3
        self.assertLessEqual(pair_bytes + 4096, afterimage.MAX_PAIR_INPUT_BYTES)
        self.assertLess(pair_bytes + 600 * 4096, afterimage.MAX_RECORD_BYTES)

    def test_single_frame_v1_interface_is_unchanged(self):
        self.assertEqual(afterimage.INTERFACE['eyes'], 'same supplied RGB frame in both channels')
        self.assertEqual(afterimage.MAX_INPUT_BYTES, 32 * 1024**2)


if __name__ == '__main__':
    unittest.main()
