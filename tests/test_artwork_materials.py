"""Software checks for the artwork materials generators; no lab owner or model runs here."""
import json
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np

import artwork_materials as m
from palimpsest import afterimage
from palimpsest.records import RunWriter


class Generators(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_manual_schedule_is_fixed_and_bounded(self):
        actions = [m.manual_action(tick) for tick in range(3000)]
        self.assertEqual(actions, [m.manual_action(tick) for tick in range(3000)])
        self.assertTrue(all(a[0] == .8 and -1 <= a[1] <= 1 for a in actions))
        self.assertEqual(m.manual_action(0), [.8, 0.])

    def recording(self, lengths=(7, 6)):
        writer = RunWriter(self.root / 'run/recording', {'run_id': 'f' * 32})
        value = 0
        for episode, length in enumerate(lengths):
            for tick in range(length):
                writer.tick(episode, tick, cam_left=np.full((128, 128, 3), value % 251, np.uint8),
                            cam_right=np.full((128, 128, 3), (value + 100) % 251, np.uint8))
                value += 1
        writer.finish({})
        return self.root / 'run/recording'

    def test_stimulus_takes_every_stride_tick_across_consecutive_episodes(self):
        stimulus = m.afterimage_stimulus(self.recording(), self.root / 'stimulus', frames=3, stride=5, run_id='f' * 32)
        spec = json.loads(stimulus.read_text())
        self.assertEqual(spec['source']['ticks'], [[0, 0], [0, 5], [1, 3]])
        self.assertEqual(spec['source_times_seconds'], [0., .1, .2])
        self.assertEqual((spec['schema_version'], spec['eyes']), (2, 'recorded-pair'))
        loaded = afterimage.load_stimulus(stimulus)
        self.assertEqual(loaded['frames'].shape, (3, 2, 128, 128, 3))
        np.testing.assert_array_equal(loaded['frames'][2, 0], np.full((128, 128, 3), 10, np.uint8))
        np.testing.assert_array_equal(loaded['frames'][2, 1], np.full((128, 128, 3), 110, np.uint8))
        with self.assertRaisesRegex(ValueError, 'supplies 3 of 4'):
            m.afterimage_stimulus(self.root / 'run/recording', self.root / 'more', frames=4, stride=5, run_id='f' * 32)

    def test_eye_png_is_lossless(self):
        import zlib
        frame = np.arange(128 * 128 * 3, dtype=np.uint32).astype(np.uint8).reshape(128, 128, 3)
        png = m.eye_png(frame)
        self.assertTrue(png.startswith(b'\x89PNG'))
        raw = zlib.decompress(png[png.index(b'IDAT') + 4:png.index(b'IEND') - 8])
        rows = np.frombuffer(raw, np.uint8).reshape(128, 1 + 128 * 3)[:, 1:].reshape(128, 128, 3)
        np.testing.assert_array_equal(rows, frame)

    def test_progress_heartbeat_is_atomic_and_final(self):
        progress = m.Progress(self.root, 'manual')
        progress.update(step='episode 1/5', total_ticks=50)
        data = json.loads((self.root / 'progress.json').read_text())
        self.assertEqual((data['schema'], data['stage'], data['status'], data['total_ticks']),
                         ('artwork-materials-v1-progress', 'manual', 'running', 50))
        progress.close('completed')
        self.assertEqual(json.loads((self.root / 'progress.json').read_text())['status'], 'completed')
        self.assertFalse(list(self.root.glob('.progress.json.*')))

    def test_detached_commands_need_no_tty_and_queue_on_the_shared_lock(self):
        full = m.commands(self.root, scale='full')
        self.assertEqual(set(full), {'all', 'manual', 'flynn', 'materials'})
        for name, command in full.items():
            self.assertEqual(command[:2], ['systemd-run', '--user'])
            self.assertIn('--property=StandardInput=null', command)
            self.assertFalse({'--pty', '-t', '--wait', '-P', '--pipe'} & set(command))
            self.assertIn(f'--setenv=PATH={m.NODE_BIN}:/usr/bin:/bin', command)
            lock = command.index('/usr/bin/flock')
            self.assertEqual(command[lock + 1], m.LOCK)  # no -w: stages queue in order
            self.assertEqual(command[lock + 2:lock + 4], ['timeout', '--signal=TERM'])
            self.assertEqual(command[command.index('--output') + 1], str(self.root / name))
        self.assertEqual(full['all'][full['all'].index('--scale') + 1], 'full')
        self.assertEqual(full['flynn'][full['flynn'].index('--total-ticks') + 1], '6000')
        self.assertEqual(full['materials'][full['materials'].index('--frames') + 1], '600')
        self.assertEqual(full['materials'][full['materials'].index('--choir-seconds') + 1], '120')
        rehearsal = m.commands(self.root, scale='rehearsal')
        self.assertTrue(all(cmd[2].endswith('-rehearsal') for cmd in rehearsal.values()))


    def test_admission_refuses_when_estimated_outputs_cross_the_floor(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        with patch.object(m.shutil, 'disk_usage', return_value=SimpleNamespace(free=m.FREE_FLOOR + 2 * 1024**3)):
            with self.assertRaisesRegex(RuntimeError, 'would cross'):
                m.admit(self.root, ('manual', 'flynn', 'materials'))
            m.admit(self.root, ('manual',))


if __name__ == '__main__':
    unittest.main()
