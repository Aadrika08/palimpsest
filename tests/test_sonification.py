"""Synthetic fixture verification only, not a model run or exhibition trial."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import wave

import numpy as np

from palimpsest.records import RunWriter


class SonificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, *, means=(1., 0., -1.), dt=.02, start=0, status='completed',
                manifest=None, stats=None, time_offset=0., lineage=None, episode_length=None):
        run = self.root / uuid.uuid4().hex
        header = dict(run_id=run.name, controller='flynn', profile='flynn',
                      scenario={'id': 'fixture-only'}, control_interval_seconds=dt,
                      population_names=['visual_left', 'visual_right', 'descending'],
                      population_columns=['count', 'mean', 'min', 'max'],
                      population_scale=[-1., 1.], evidence_class='synthetic fixture verification')
        header.update(manifest or {})
        writer = RunWriter(run / 'recording', header)
        writer.event('policy_loaded', run_id=lineage or run.name, provenance={
            'edge_sha256': 'a' * 64, 'checkpoint_sha256': 'b' * 64,
            'ordered_neuron_ids_sha256': 'c' * 64,
            'provenance_limit': 'Synthetic fixture identifiers, not model execution.'})
        writer.event('episode_started', run_id=run.name, episode=0, episode_step=start,
                     world={'arena': 7., 'pose': [0., 0., 0.], 'obstacles': [], 'goal': [3., 3., .5]})
        if header.get('parent_event_prefix') is not None:
            writer.event('application_restored', run_id=run.name, episode=0, episode_step=start,
                         parent_run_id=header['parent_run_id'], parent_event_prefix=header['parent_event_prefix'],
                         world={'arena': 7., 'pose': [0., 0., 0.], 'obstacles': [], 'goal': [3., 3., .5]})
        for index, mean in enumerate(means):
            episode = index // episode_length if episode_length else 0
            tick = index % episode_length if episode_length else start + index
            if episode_length and index and tick == 0:
                writer.event('episode_started', run_id=run.name, episode=episode, episode_step=0,
                             world={'arena': 7., 'pose': [0., 0., 0.], 'obstacles': [], 'goal': [3., 3., .5]})
            arrays = dict(pose=np.array([tick * .1, 0., 0.]), next_pose=np.array([(tick + 1) * .1, 0., 0.]),
                          reward=np.array(0.), sensors=np.zeros(4),
                          simulation_time=np.array((tick + 1) * dt + (time_offset if index else 0.)))
            if stats is not False:
                arrays['population_stats'] = np.array(stats if stats is not None else
                    [[8., mean, mean, mean], [8., 0., 0., 0.], [2., .5, .5, .5]])
            writer.tick(episode, tick, **arrays)
        writer.finish({}, status=status)
        return run

    def export(self, run, name='choir.wav', populations=('visual_left',), **kwargs):
        from palimpsest.sonification import sonify
        return sonify(run, self.root / name, populations=populations, **kwargs)

    def read(self, path):
        with wave.open(str(path), 'rb') as audio:
            self.assertEqual((audio.getnchannels(), audio.getsampwidth(), audio.getframerate()), (1, 2, 48000))
            samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2')
        payload = path.read_bytes()
        self.assertEqual(struct.unpack_from('<I', payload, 4)[0], len(payload) - 8)
        position = 12
        while position < len(payload):
            kind, length = struct.unpack_from('<4sI', payload, position)
            body = payload[position + 8:position + 8 + length]
            position += 8 + length + (length % 2)
            if kind == b'plmp':
                return samples, json.loads(body)
        self.fail('WAV lacks embedded provenance')

    def test_actual_means_drive_fixed_carrier_with_silence_and_deterministic_bytes(self):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.sonification'), 'offline sonifier is missing')
        run = self.fixture()
        output = self.export(run)
        samples, metadata = self.read(output)
        self.assertEqual(len(samples), 2880)
        self.assertTrue(np.any(samples[:960]))
        np.testing.assert_array_equal(samples[960:1920], 0)
        # At 48000 Hz, sample 600 is -1 of a 220 Hz sine: quarter-scale negative PCM.
        self.assertEqual(samples[600], -8192)
        self.assertEqual(samples[2100], 5792)  # Negative recorded mean reverses phase.
        self.assertEqual(metadata['source']['run_id'], run.name)
        self.assertEqual(metadata['source']['profile'], 'flynn')
        self.assertEqual(metadata['source']['evidence_class'], 'synthetic fixture verification')
        self.assertEqual(metadata['timing']['sample_boundaries'], [0, 960, 1920, 2880])
        self.assertIn('not biological audio', metadata['label'])
        self.assertEqual(metadata['pcm_sha256'], hashlib.sha256(samples.tobytes()).hexdigest())
        self.assertEqual(output.read_bytes(), self.export(run, 'second.wav').read_bytes())

    def test_fractional_tick_samples_preserve_duration_without_per_tick_rounding_drift(self):
        samples, metadata = self.read(self.export(self.fixture(dt=.00003, start=600)))
        self.assertEqual(len(samples), 4)
        self.assertEqual(metadata['timing']['sample_boundaries'], [0, 1, 3, 4])
        self.assertEqual(metadata['timing']['start_tick'], 600)
        self.assertAlmostEqual(metadata['timing']['simulation_start_seconds'], .018)

    def test_each_population_can_be_selected_without_renormalizing_others(self):
        run = self.fixture()
        samples, metadata = self.read(self.export(run, populations=('descending', 'visual_right')))
        self.assertTrue(np.any(samples))
        self.assertEqual([voice['population'] for voice in metadata['mapping']['voices']], ['visual_right', 'descending'])
        self.assertEqual([voice['frequency_hz'] for voice in metadata['mapping']['voices']], [330., 440.])
        silence, _ = self.read(self.export(run, 'silence.wav', populations=('visual_right',)))
        np.testing.assert_array_equal(silence, 0)

    def test_bad_telemetry_lineage_time_and_terminal_status_never_publish(self):
        bad = [dict(stats=False), dict(stats=[[8., np.nan, -1., 1.]] * 3),
               dict(stats=[[8., 0., 0., 0.]]), dict(stats=[[0., 0., 0., 0.]] * 3),
               dict(stats=[[8., 1.2, 0., 1.2]] * 3), dict(stats=[[8., .5, .6, 1.]] * 3),
               dict(status='running'), dict(status='failed'), dict(time_offset=.005),
               dict(lineage=uuid.uuid4().hex), dict(manifest={'parent_run_id': 'not-a-run'}),
               dict(manifest={'population_names': ['visual_left', 'visual_left', 'descending']}),
               dict(manifest={'control_interval_seconds': 0}), dict(manifest={'controller': 'teacher'}),
               dict(manifest={'population_columns': ['mean', 'count', 'min', 'max']})]
        for case in bad:
            with self.subTest(case=case):
                # Running records arise through interruption, not RunWriter.finish.
                running = case.get('status') == 'running'
                if running:
                    case = dict(case, status='completed')
                run = self.fixture(**case)
                if running:
                    path = run / 'recording/manifest.json'
                    manifest = json.loads(path.read_text())
                    manifest['status'] = 'running'
                    path.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    self.export(run)
                self.assertFalse((self.root / 'choir.wav').exists())

    def test_checksum_and_terminal_aggregate_validation_are_reused(self):
        for failure in ('checksum', 'aggregate'):
            run = self.fixture()
            if failure == 'checksum':
                path = run / 'recording/chunks/000000.npz'
                path.write_bytes(path.read_bytes() + b'corrupt')
            else:
                path = run / 'recording/manifest.json'
                manifest = json.loads(path.read_text())
                manifest['recorded_ticks'] += 1
                path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.export(run)
            self.assertFalse((self.root / 'choir.wav').exists())

    def test_branch_provenance_and_source_hashes_are_retained_and_changed_sources_differ(self):
        parent = uuid.uuid4().hex
        prefix = {'sha256': 'd' * 64, 'size_bytes': 100, 'event_count': 2}
        run = self.fixture(start=8, manifest={'parent_run_id': parent, 'parent_event_prefix': prefix})
        _, metadata = self.read(self.export(run))
        source = metadata['source']
        self.assertEqual(source['provenance']['parent_run_id'], parent)
        self.assertEqual(source['provenance']['parent_event_prefix'], prefix)
        for entry in source['files']:
            self.assertEqual(entry['sha256'], hashlib.sha256((run / entry['path']).read_bytes()).hexdigest())
        same_activity = self.fixture(start=8, manifest={'parent_run_id': parent, 'parent_event_prefix': prefix})
        _, same_sound = self.read(self.export(same_activity, 'same-activity.wav'))
        self.assertEqual(metadata['pcm_sha256'], same_sound['pcm_sha256'])
        self.assertNotEqual(source['recording_sha256'], same_sound['source']['recording_sha256'])
        changed = self.fixture(means=(0., 0., 0.))
        _, different = self.read(self.export(changed, 'changed.wav'))
        self.assertNotEqual(source['recording_sha256'], different['source']['recording_sha256'])

    def test_budgets_invalid_selection_and_existing_output_fail_closed(self):
        from palimpsest import sonification
        run = self.fixture()
        for populations in ((), ('missing',), ('visual_left', 'visual_left')):
            with self.assertRaises(ValueError):
                self.export(run, populations=populations)
        for limit in ('MAX_SOURCE_BYTES', 'MAX_OUTPUT_BYTES', 'MAX_SECONDS'):
            with self.subTest(limit=limit), patch.object(sonification, limit, 1 if limit != 'MAX_SECONDS' else .01):
                with self.assertRaises(ValueError):
                    self.export(run)
                self.assertFalse((self.root / 'choir.wav').exists())
        output = self.export(run)
        original = output.read_bytes()
        with self.assertRaises(FileExistsError):
            self.export(run)
        self.assertEqual(output.read_bytes(), original)

    def test_cli_exports_without_inference_imports(self):
        from palimpsest.cli import main
        run = self.fixture()
        # Keep the real storage lease/checks, isolated from another active lab.
        with patch.object(Path, 'home', return_value=self.root), patch.dict(sys.modules, {'torch': None, 'mujoco': None}), contextlib.redirect_stdout(io.StringIO()) as captured:
            code = main(['sonify', str(run), '--population', 'visual_left',
                         '--output', str(self.root / 'cli.wav'), '--min-free-bytes', '0'])
        self.assertEqual(code, 0)
        self.assertEqual(Path(json.loads(captured.getvalue())['artifact']), self.root / 'cli.wav')
        self.read(self.root / 'cli.wav')

    def test_composition_exact_duration_prefix_and_continuous_carrier(self):
        run = self.fixture(means=[.5] * 6003, episode_length=601)
        samples, meta = self.read(self.export(run, episode=None))
        self.assertEqual(len(samples), 5760000)
        self.assertEqual(meta['version'], 2)
        self.assertEqual(meta['timing']['clock'], 'concatenated simulation time')
        segments = meta['timing']['segments']
        self.assertEqual(len(segments), 10)
        self.assertEqual(segments[1]['output_start_sample'], 601 * 960)
        self.assertEqual(segments[-1]['end_tick_inclusive'], 590)
        self.assertTrue(meta['timing']['final_episode_prefix'])
        positions = np.arange(len(samples), dtype=np.float64)
        expected = np.rint(32767 * .25 * .5 * np.sin(2 * np.pi * 220 * positions / 48000)).astype('<i2')
        np.testing.assert_array_equal(samples, expected)

    def test_composition_rejects_short_wrong_interval_and_corrupt_tail(self):
        for kwargs in (dict(means=[0.] * 5999, episode_length=600),
                       dict(means=[0.] * 6000, episode_length=600, dt=.01),
                       dict(means=[0.] * 6000, start=1)):
            with self.assertRaises(ValueError):
                self.export(self.fixture(**kwargs), episode=None)
        run = self.fixture(means=[0.] * 6001, episode_length=600)
        chunk = sorted((run / 'recording/chunks').glob('*.npz'))[-1]
        chunk.write_bytes(chunk.read_bytes() + b'corrupt')
        with self.assertRaises(ValueError):
            self.export(run, episode=None)
        self.assertFalse((self.root / 'choir.wav').exists())

    def test_composition_cli_and_source_cap_preflight(self):
        from palimpsest import cli, sonification
        run = self.fixture(means=[0.] * 6000, episode_length=600)
        with patch.object(Path, 'home', return_value=self.root), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['sonify', str(run), '--compose-episodes', '--population', 'visual_left',
                                      '--output', str(self.root / 'cli.wav'), '--min-free-bytes', '0']), 0)
        with patch.object(sonification, 'MAX_COMPOSITION_SOURCE_BYTES', 1), patch.object(sonification.artifacts, '_load') as load:
            with self.assertRaises(ValueError):
                self.export(run, episode=None)
            load.assert_not_called()

    def test_composition_metadata_bounds_and_default_remain_distinct(self):
        from palimpsest import sonification
        run = self.fixture(means=[0.] * 6000, episode_length=600)
        single, metadata = self.read(self.export(run))
        self.assertEqual(len(single), 600 * 960)
        self.assertEqual(metadata['version'], 1)
        self.assertEqual(metadata['timing']['episode'], 0)
        with patch.object(sonification, 'MAX_COMPOSITION_METADATA_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'output byte limit'):
                self.export(run, 'bounded.wav', episode=None)
        self.assertFalse((self.root / 'bounded.wav').exists())
        with patch.object(sonification, 'MAX_SOURCE_BYTES', 1):
            self.export(run, 'larger-admission.wav', episode=None)
        too_long = self.fixture(means=[0.] * 6601, episode_length=600)
        with patch.object(sonification.artifacts, '_load') as load:
            with self.assertRaisesRegex(ValueError, '6000'):
                self.export(too_long, 'too-long.wav', episode=None)
            load.assert_not_called()

    def test_render_failure_removes_our_partial_output(self):
        run = self.fixture()
        with patch.object(np, 'sin', side_effect=RuntimeError('synthetic write failure')):
            with self.assertRaisesRegex(RuntimeError, 'synthetic write failure'):
                self.export(run)
        self.assertFalse((self.root / 'choir.wav').exists())


if __name__ == '__main__':
    unittest.main()
