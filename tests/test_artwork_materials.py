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


class FakeOwner:
    """The lab owner's command contract at the generator's client boundary, with the
    engine's per-run idempotency cap (Engine.MAX_IDS) and 600-tick truncation."""
    MAX_IDS = 4096

    def __init__(self, max_steps=600, lengths=()):
        from palimpsest.engine import Engine
        self.cap, self.max_steps = Engine.MAX_IDS, max_steps
        self.ids, self.receipts, self.applied = set(), [], []
        self.state = {'phase': 'paused', 'episode': 0, 'revision': 0, 'total_tick': 0, 'episode_step': 0, 'last_outcome': None}
        self.action, self.snapshots, self.lengths = [0., 0.], [], list(lengths)

    def describe(self, run):
        return {'status': 'ready', 'state': dict(self.state), 'receipts': list(self.receipts[-8:])}

    def tick(self):
        self.applied.append((self.state['episode'], self.state['episode_step'], list(self.action)))
        self.state['total_tick'] += 1
        self.state['episode_step'] += 1
        episode = self.state['episode']
        if episode < len(self.lengths) and self.lengths[episode] < self.max_steps and self.state['episode_step'] >= self.lengths[episode]:
            self.state['phase'] = 'terminated'  # e.g. 'stalled', as in the 8faab2b launch
        elif self.state['episode_step'] >= self.max_steps:
            self.state['phase'] = 'truncated'

    def call(self, run, operation, body):
        if operation == 'snapshot':
            self.snapshots.append((self.state['episode'], self.state['episode_step']))
            return {'snapshot_id': 'a' * 32}
        if len(self.ids) >= self.cap:
            raise RuntimeError('idempotency limit reached; a new session is required')
        self.ids.add(body['id'])
        kind = body['kind']
        assert body['expected_state'] == self.state['phase'] and body['expected_revision'] == self.state['revision']
        if kind == 'set_action':
            self.action = list(body['payload']['action'])
        elif kind == 'step':
            self.tick()
        elif kind == 'run':
            while self.state['phase'] not in ('truncated', 'terminated'):
                self.tick()
        elif kind == 'reset':
            self.state.update(episode=self.state['episode'] + 1, episode_step=0, phase='paused')
            self.action = [0., 0.]  # the engine zeroes manual intent at a new episode
        self.state['revision'] += 1
        self.receipts.append({'id': body['id'], 'status': 'applied'})
        return {'id': body['id'], 'status': 'queued'}


class FullScaleCommandBudget(unittest.TestCase):
    """The full runs must stay inside one run's idempotency cap (the 8faab2b launch did not)."""

    def drive(self, owner, **options):
        from unittest.mock import MagicMock
        session = m.Session(owner, 'r' * 32, MagicMock())
        return m.drive(session, progress=MagicMock(), seed=0, **options)

    def test_full_manual_run_and_branch_point_fit_one_owner(self):
        owner = FakeOwner()
        summaries, snapshot, ticks = self.drive(owner, controller='manual', episodes=5, episode_ticks=600,
                                                total_ticks=0, branch_at=300)
        self.assertEqual((ticks, len(summaries)), (3000, 5))
        self.assertTrue(all(s['ticks'] == 600 and s['ending'] == 'truncated' for s in summaries))
        self.assertEqual(owner.snapshots, [(0, 300)])
        self.assertLess(len(owner.ids), owner.cap)
        # Contiguous episodes in one run, and every tick drives the fixed schedule.
        self.assertEqual([(e, s) for e, s, _ in owner.applied], [(e, s) for e in range(5) for s in range(600)])
        for index, (_, _, action) in enumerate(owner.applied):
            self.assertEqual(action, m.manual_action(index))

    def test_full_flynn_run_fits_one_owner(self):
        owner = FakeOwner()
        summaries, _, ticks = self.drive(owner, controller='flynn', episodes=10, episode_ticks=600,
                                         total_ticks=6000, branch_at=None)
        self.assertEqual((ticks, len(summaries)), (6000, 10))
        self.assertLess(len(owner.ids), 64)
        self.assertEqual([(e, s) for e, s, _ in owner.applied], [(e, s) for e in range(10) for s in range(600)])

    def test_episodes_that_end_early_continue_until_the_declared_total(self):
        owner = FakeOwner(lengths=[600, 255, 526, 600])  # the failed launch's actual episode lengths
        summaries, snapshot, ticks = self.drive(owner, controller='manual', episodes=20, episode_ticks=600,
                                                total_ticks=3000, branch_at=300)
        self.assertEqual(ticks, 3000)
        self.assertEqual([s['ticks'] for s in summaries], [600, 255, 526, 600, 600, 419])
        self.assertEqual([s['ending'] for s in summaries][:3], ['truncated', 'terminated', 'terminated'])
        self.assertEqual(summaries[-1]['ending'], 'declared total reached')
        self.assertEqual(len(owner.applied), 3000)
        self.assertLess(len(owner.ids), owner.cap)
        flynn = FakeOwner(lengths=[600, 300])
        summaries, _, ticks = self.drive(flynn, controller='flynn', episodes=30, episode_ticks=600,
                                         total_ticks=6000, branch_at=None)
        self.assertGreaterEqual(ticks, 6000)
        self.assertEqual([s['ticks'] for s in summaries][:2], [600, 300])
        self.assertEqual(len(summaries), 11)

    def test_full_scale_stage_arguments_target_declared_totals(self):
        full = m.stage_arguments('full', '/nonexistent/root')
        self.assertEqual(full['manual'][full['manual'].index('--total-ticks') + 1], '3000')
        self.assertEqual(full['flynn'][full['flynn'].index('--total-ticks') + 1], '6000')

