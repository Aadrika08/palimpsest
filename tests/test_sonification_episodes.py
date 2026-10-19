"""Multi-episode choir (user decision): consecutive episodes in order, marked
boundaries, every sample mapped to a recorded tick, explicit declared gain only.
Synthetic fixture verification; not a model run."""
import math
from pathlib import Path
import tempfile
import unittest
import uuid

import numpy as np

from palimpsest.records import RunWriter
from palimpsest import sonification
import test_sonification

FADE = 960  # 20 ms at 48 kHz


class EpisodeChoir(unittest.TestCase):
    read = test_sonification.SonificationTests.read

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, lengths=(4, 3, 5), dt=.02):
        run = self.root / uuid.uuid4().hex
        writer = RunWriter(run / 'recording', dict(
            run_id=run.name, controller='flynn', profile='flynn', scenario={'id': 'fixture-only'},
            control_interval_seconds=dt, population_names=['visual_left', 'visual_right', 'descending'],
            population_columns=['count', 'mean', 'min', 'max'], population_scale=[-1., 1.],
            evidence_class='synthetic fixture verification'))
        writer.event('policy_loaded', run_id=run.name, provenance={'edge_sha256': 'a' * 64, 'checkpoint_sha256': 'b' * 64,
                     'ordered_neuron_ids_sha256': 'c' * 64})
        self.means = []
        for episode, length in enumerate(lengths):
            writer.event('episode_started', run_id=run.name, episode=episode, episode_step=0,
                         world={'arena': 7., 'pose': [0., 0., 0.], 'obstacles': [], 'goal': [3., 3., .5]})
            for tick in range(length):
                mean = math.sin(episode + tick / 3)  # nonzero, varying per tick
                self.means.append((episode, tick, mean))
                writer.tick(episode, tick, pose=np.array([tick * .1, 0., 0.]), next_pose=np.array([(tick + 1) * .1, 0., 0.]),
                            reward=np.array(0.), sensors=np.zeros(4), simulation_time=np.array((tick + 1) * dt),
                            population_stats=np.array([[8., mean, -1., 1.], [8., 0., -1., 1.], [2., .5, -1., 1.]]))
        writer.finish({})
        return run

    def export(self, run, name='choir.wav', **kwargs):
        options = dict(populations=('visual_left',), episodes=[0, 1, 2], max_seconds=120, boundary_fade_seconds=.02,
                       declared_gain=1.)
        options.update(kwargs)
        return sonification.sonify_episodes(run, self.root / name, **options)

    def expected(self, rows, gain=1.):
        samples = []
        for index, (_, _, mean) in enumerate(rows):
            positions = np.arange(index * 960, (index + 1) * 960, dtype=np.float64)
            samples.append(gain * sonification.GAIN * mean * np.sin(2 * np.pi * 220. * positions / 48000))
        return np.concatenate(samples)

    def test_episodes_in_order_with_declared_boundary_fades(self):
        run = self.fixture()
        samples, meta = self.read(self.export(run))
        self.assertEqual(len(samples), 12 * 960)
        timing = meta['timing']
        self.assertEqual(timing['episodes'], [0, 1, 2])
        self.assertEqual(timing['sample_boundaries'], [index * 960 for index in range(13)])
        self.assertEqual(timing['ticks'], [[e, t] for e, t, _ in self.means])
        self.assertEqual([span['first_sample'] for span in timing['episode_spans']], [0, 4 * 960, 7 * 960])
        marker = meta['mapping']['episode_boundary_marker']
        self.assertEqual((marker['fade_samples'], marker['shape']), (FADE, 'linear'))
        self.assertEqual(marker['boundaries_samples'], [4 * 960, 7 * 960])
        envelope = np.ones(12 * 960)
        for boundary in (4 * 960, 7 * 960):
            envelope[boundary - FADE:boundary] = (FADE - np.arange(FADE) - 1) / FADE
            envelope[boundary:boundary + FADE] = (np.arange(FADE) + 1) / FADE
        expected = np.rint(32767 * self.expected(self.means) * envelope).astype('<i2')
        np.testing.assert_array_equal(samples, expected)
        self.assertEqual(meta['gain']['declared_linear'], 1.)
        self.assertIn('no normalization', meta['mapping']['mix'])

    def test_levels_are_recorded_from_the_written_pcm(self):
        samples, meta = self.read(self.export(self.fixture()))
        values = samples.astype(np.float64) / 32767
        peak, rms = np.max(np.abs(values)), math.sqrt(np.mean(values ** 2))
        self.assertAlmostEqual(meta['levels']['peak_dbfs'], 20 * math.log10(peak), places=6)
        self.assertAlmostEqual(meta['levels']['rms_dbfs'], 20 * math.log10(rms), places=6)

    def test_declared_gain_is_explicit_and_never_clips(self):
        run = self.fixture()
        plain, _ = self.read(self.export(run, 'plain.wav'))
        louder, meta = self.read(self.export(run, 'louder.wav', declared_gain=2.))
        self.assertLessEqual(np.max(np.abs(louder.astype(int) - 2 * plain.astype(int))), 2)
        self.assertEqual(meta['gain'], {'declared_linear': 2., 'declared_db': 20 * math.log10(2.),
                                        'applied_to': 'every sample after the fixed mapping and boundary envelope',
                                        'normalization': 'none'})
        with self.assertRaisesRegex(ValueError, 'clip'):
            self.export(run, 'clipped.wav', declared_gain=10.)
        self.assertFalse((self.root / 'clipped.wav').exists())
        for gain in (0., -1., float('nan'), 101.):
            with self.subTest(gain=gain), self.assertRaises(ValueError):
                self.export(run, f'bad-{gain}.wav', declared_gain=gain)

    def test_duration_cap_cuts_at_a_recorded_tick_and_says_so(self):
        samples, meta = self.read(self.export(self.fixture(), max_seconds=.2))
        self.assertEqual(len(samples), 10 * 960)
        self.assertEqual(meta['timing']['ticks'][-1], [2, 2])
        self.assertTrue(meta['timing']['truncated_at_max_seconds'])
        self.assertEqual(meta['timing']['declared_seconds'], .2)

    def test_episodes_must_be_consecutive_and_present(self):
        run = self.fixture()
        for episodes in ([0, 2], [1, 0], [0, 1, 2, 3], []):
            with self.subTest(episodes=episodes), self.assertRaises(ValueError):
                self.export(run, f'bad-{len(episodes)}.wav', episodes=episodes)

    def test_cli_dispatches_episode_range(self):
        from palimpsest import cli
        run = self.fixture()
        output = self.root / 'exports' / 'choir.wav'
        output.parent.mkdir()
        from unittest.mock import patch
        import contextlib, io
        with patch.object(Path, 'home', return_value=self.root), contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(['sonify', str(run), '--population', 'visual_left', '--episodes', '0-2', '--max-seconds', '120',
                             '--boundary-fade-seconds', '0.02', '--declared-gain', '1', '--output', str(output),
                             '--min-free-bytes', '0'])
        self.assertEqual(code, 0)
        samples, meta = self.read(output)
        self.assertEqual(meta['timing']['episodes'], [0, 1, 2])


if __name__ == '__main__':
    unittest.main()
