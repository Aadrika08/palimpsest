"""Process and recorder fault boundaries; fixture physics is labelled explicitly."""

import errno
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

from palimpsest.engine import Engine
from palimpsest.lab import LabSupervisor
from palimpsest.records import RunWriter, iter_ticks
from test_engine import SmallEnv


REPO = Path(__file__).resolve().parents[1]


def writer_owner(config, commands, replies, display, disconnected, stop, progress):
    """A real spawned writer crashes after receiving one request, without cleanup."""
    os.setsid()
    writer = RunWriter(Path(config['run_path']) / 'recording', {'run_id': config['run_id']})
    if not config.get('crash', True):
        writer.finish({})
        replies.put({'version': 1, 'type': 'closed', 'run_id': config['run_id'], 'status': 'closed',
                     'state': {'phase': 'stopped', 'episode': 0, 'total_tick': 0}})
        replies.close()
        replies.join_thread()
        return
    for tick in range(33):
        writer.tick(0, tick, action=np.array([tick, -tick], dtype=np.float32))
    progress.value = time.monotonic()
    replies.put({'version': 1, 'type': 'status', 'run_id': config['run_id'], 'status': 'ready',
                 'state': {'phase': 'paused', 'episode': 0, 'total_tick': 33, 'revision': 0}})
    request = commands.get(timeout=5.)
    writer.event('command_received', command=request['body'])
    os._exit(17)  # Deliberately omit writer.close(), response and terminal manifest.


@unittest.skipIf(np is None, 'NumPy is provided by the simulation extra')
class RecoveryTests(unittest.TestCase):
    def test_abrupt_owner_exit_settles_rpc_preserves_prefix_and_allows_fresh_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            supervisor = LabSupervisor(REPO, Path(temporary) / 'assets', Path(temporary) / 'runs',
                                       worker_target=writer_owner, startup_timeout=10., step_timeout=10.)
            self.addCleanup(supervisor.shutdown)
            identifier = supervisor.start({})
            deadline = time.monotonic() + 10.
            while supervisor.describe(identifier)['status'] != 'ready' and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertEqual(supervisor.describe(identifier)['status'], 'ready')
            with self.assertRaisesRegex(RuntimeError, 'Owner closed before response'):
                supervisor.call(identifier, 'command', {'id': 'crash-boundary', 'kind': 'step'}, timeout=5.)
            view = supervisor.describe(identifier)
            self.assertEqual(view['failure']['type'], 'WorkerExit')
            self.assertIn('17', view['failure']['message'])
            self.assertFalse(supervisor.workers[identifier].process.is_alive())
            self.assertEqual(supervisor.workers[identifier].pending, {})
            recording = supervisor.path(identifier) / 'recording'
            recovered = list(iter_ticks(recording))
            self.assertEqual([int(row['tick']) for row in recovered], list(range(32)))
            self.assertEqual(json.loads((recording / 'manifest.json').read_text())['status'], 'running')
            events = [json.loads(line) for line in (recording / 'events.jsonl').read_text().splitlines()]
            self.assertEqual(events[-1]['command']['id'], 'crash-boundary')
            self.assertFalse(any(row['kind'] == 'command_applied' for row in events))
            self.assertEqual(json.loads((supervisor.path(identifier) / 'supervisor.json').read_text())['status'], 'failed')
            fresh = supervisor.start({'crash': False})
            self.assertTrue(supervisor.workers[fresh].done.wait(10.))
            self.assertEqual(supervisor.close(fresh)['status'], 'closed')

    def test_postrename_event_failure_preserves_prefix_and_does_not_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'recording'
            writer = RunWriter(path, {})
            for tick in range(32):
                writer.tick(0, tick, action=np.array([tick], dtype=np.float32))
            prefix = (path / 'events.jsonl').read_bytes()
            writer.tick(0, 32, action=np.array([32], dtype=np.float32))
            with patch.object(writer, 'event', side_effect=OSError(errno.ENOSPC, 'event publication failed')):
                with self.assertRaises(OSError):
                    writer.flush()
            self.assertTrue((path / 'chunks/000001.npz').is_file())
            self.assertEqual((path / 'events.jsonl').read_bytes(), prefix)
            writer.close()
            self.assertEqual((path / 'events.jsonl').read_bytes(), prefix)
            self.assertEqual([int(row['tick']) for row in iter_ticks(path)], list(range(32)))
            self.assertEqual(json.loads((path / 'manifest.json').read_text())['status'], 'running')
            self.assertFalse(list((path / 'chunks').glob('*.tmp')))

    def test_real_recorder_disk_failure_stops_engine_fixture_and_releases_world(self):
        # This proves Engine/RunWriter failure propagation, not MuJoCo physics.
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'recording'
            writer, env = RunWriter(path, {'run_id': 'fixture'}), SmallEnv()
            engine = Engine(env, writer)
            for tick in range(63):
                engine.submit({'id': str(tick), 'kind': 'step', 'expected_state': 'paused',
                               'expected_episode': 0, 'expected_revision': engine.revision})
                engine.advance()
            original_tick = writer.tick
            def fail_chunk_fsync(*args, **kwargs):
                with patch('palimpsest.records.os.fsync', side_effect=OSError(errno.ENOSPC, 'disk full')):
                    return original_tick(*args, **kwargs)
            engine.manual_action[:] = [.5, .2]
            engine.submit({'id': 'disk-full', 'kind': 'step', 'expected_state': 'paused',
                           'expected_episode': 0, 'expected_revision': engine.revision})
            with patch.object(writer, 'tick', side_effect=fail_chunk_fsync):
                state = engine.advance()
            self.assertEqual(state['phase'], 'failed')
            self.assertEqual(env.calls, 64)  # The failed recording follows an actual fixture step.
            self.assertIn('disk full', state['last_outcome']['message'])
            np.testing.assert_array_equal(engine.manual_action, [0., 0.])
            self.assertEqual(engine.advance()['total_tick'], 64)
            self.assertEqual(env.calls, 64)
            with self.assertRaisesRegex(RuntimeError, 'recording failed'):
                engine.submit({'id': 'unsafe-reset', 'kind': 'reset', 'expected_state': 'failed',
                               'expected_episode': 0, 'expected_revision': engine.revision})
            engine.close()
            self.assertTrue(env.closed)
            self.assertEqual(len(list(iter_ticks(path))), 32)
            self.assertEqual(json.loads((path / 'manifest.json').read_text())['status'], 'running')
            self.assertFalse(list((path / 'chunks').glob('*.tmp')))


if __name__ == '__main__':
    unittest.main()
