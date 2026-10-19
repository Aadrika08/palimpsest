"""Background recording writer: same bytes, durable drain, bounded queue, surfaced errors."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import numpy as np

from palimpsest import records
from palimpsest.records import RunWriter, iter_ticks
from palimpsest.storage import StorageBudget, StorageLimitError, StorageLimits

REPO = Path(__file__).resolve().parents[1]
REAL_FSYNC = os.fsync


def schedule(writer):
    """A fixed mixed schedule: events, two episodes, explicit flush, terminal finish."""
    writer.event('started', controller='manual', seed=3)
    camera = np.arange(128 * 128 * 3, dtype=np.uint8).reshape(128, 128, 3)
    for tick in range(70):
        writer.tick(0, tick, cam_left=(camera + tick).astype(np.uint8), action=np.array([tick, -tick], np.float32))
        if tick % 9 == 0:
            writer.event('command_applied', id=f'c{tick}', tick=tick)
    writer.flush()
    writer.event('reset', episode=1)
    for tick in range(5):
        writer.tick(1, tick, cam_left=camera, action=np.zeros(2, np.float32))
    writer.finish({'episodes': 2})
    writer.close()


def files(path):
    return {str(item.relative_to(path)): item.read_bytes() for item in sorted(path.rglob('*')) if item.is_file()}


class BackgroundWriter(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_recording_is_byte_identical_to_the_synchronous_path(self):
        synchronous = RunWriter(self.root / 'sync', {'run_id': 'same'})
        schedule(synchronous)
        background = RunWriter(self.root / 'background', {'run_id': 'same'})
        background.start_background()
        schedule(background)
        self.assertEqual(files(self.root / 'sync'), files(self.root / 'background'))
        self.assertEqual(len(list(iter_ticks(self.root / 'background'))), 75)

    def test_caller_does_not_wait_for_fsync_and_finish_drains_durably(self):
        synced = []
        def slow(descriptor):
            time.sleep(.15)
            synced.append(descriptor)
            REAL_FSYNC(descriptor)
        writer = RunWriter(self.root / 'run', {})
        writer.start_background()
        with patch('palimpsest.records.os.fsync', side_effect=slow):
            started = time.perf_counter()
            for tick in range(64):  # two chunk publications, each with a chunk event
                writer.tick(0, tick, action=np.zeros(2))
            enqueue_seconds = time.perf_counter() - started
            self.assertLess(enqueue_seconds, .12)
            writer.flush()  # waits for the queue to drain
            self.assertGreaterEqual(len(synced), 4)  # two chunk files and two chunk events
            self.assertEqual([event['kind'] for event in map(json.loads, (self.root / 'run/events.jsonl').read_text().splitlines())],
                             ['chunk', 'chunk'])
            writer.finish({})
        writer.close()
        self.assertEqual(json.loads((self.root / 'run/manifest.json').read_text())['recorded_ticks'], 64)
        self.assertEqual(writer.background_stats()['written_items'], 4)

    def test_caller_never_touches_a_chunk_file_the_writer_is_publishing(self):
        entered, release = threading.Event(), threading.Event()
        def held(descriptor):
            entered.set()
            release.wait(5.)
            REAL_FSYNC(descriptor)
        original = records._BackgroundWrites.put
        def put(self, item, size):
            original(self, item, size)
            if item[0] == 'chunk':
                self.assertion = entered.wait(5.)  # the writer is inside the chunk's fsync
        writer = RunWriter(self.root / 'run', {})
        writer.start_background()
        with patch('palimpsest.records.os.fsync', side_effect=held), patch.object(records._BackgroundWrites, 'put', put):
            for tick in range(32):
                writer.tick(0, tick, action=np.zeros(2))
            release.set()
            writer.finish({})
        writer.close()
        self.assertEqual(len(list(iter_ticks(self.root / 'run'))), 32)

    def test_bounded_queue_blocks_and_counts_backpressure(self):
        gate = threading.Event()
        def blocked(descriptor):
            gate.wait(5.)
            REAL_FSYNC(descriptor)
        writer = RunWriter(self.root / 'run', {})
        writer.start_background(max_items=2)
        with patch('palimpsest.records.os.fsync', side_effect=blocked):
            producer = threading.Thread(target=lambda: [writer.event('e', index=index) for index in range(6)])
            producer.start()
            time.sleep(.3)
            self.assertTrue(producer.is_alive())  # the caller blocks instead of growing memory
            stats = writer.background_stats()
            self.assertLessEqual(stats['queued_items'], 2)
            self.assertGreaterEqual(stats['backpressure_events'], 1)
            gate.set()
            producer.join(5.)
            self.assertFalse(producer.is_alive())
            writer.finish({})
        writer.close()
        stats = writer.background_stats()
        self.assertEqual((stats['written_items'], stats['max_queued_items']), (6, 2))
        self.assertGreater(stats['backpressure_seconds'], 0)

    def test_writer_error_fails_the_run_and_keeps_the_prefix(self):
        calls = []
        def failing(descriptor):
            calls.append(descriptor)
            if len(calls) > 2:
                raise OSError('disk failure')
            REAL_FSYNC(descriptor)
        writer = RunWriter(self.root / 'run', {})
        writer.start_background()
        with patch('palimpsest.records.os.fsync', side_effect=failing):
            for tick in range(64):
                writer.tick(0, tick, action=np.zeros(2))
            with self.assertRaisesRegex(RuntimeError, 'Background recording write failed'):
                writer.flush()
            with self.assertRaisesRegex(RuntimeError, 'Background recording write failed'):
                writer.event('late')
            with self.assertRaisesRegex(RuntimeError, 'Background recording write failed'):
                writer.finish({})
        writer.close()  # does not hang or retry
        self.assertEqual(json.loads((self.root / 'run/manifest.json').read_text())['status'], 'running')
        self.assertEqual(len(list(iter_ticks(self.root / 'run'))), 32)
        self.assertEqual(writer.background_stats()['error']['type'], 'OSError')

    def test_quota_and_budget_count_queued_but_unwritten_bytes(self):
        gate = threading.Event()
        def blocked(descriptor):
            gate.wait(5.)
            REAL_FSYNC(descriptor)
        budget = StorageBudget((self.root,), StorageLimits(max_bytes=60_000, min_free_bytes=0))
        writer = RunWriter(self.root / 'run', {}, storage_budget=budget)
        writer.start_background()
        with patch('palimpsest.records.os.fsync', side_effect=blocked):
            writer.event('holds-the-writer')  # the writer thread blocks in this event's fsync
            for tick in range(32):
                writer.tick(0, tick, camera=np.zeros(1000, np.uint8))  # about 32 KB queued, not on disk
            time.sleep(.1)
            self.assertLess(budget.usage()['used_bytes'], 10_000)
            with self.assertRaises(StorageLimitError):
                for tick in range(32, 64):
                    writer.tick(0, tick, camera=np.zeros(1000, np.uint8))
            gate.set()
        writer.close()
        self.assertLessEqual(budget.usage()['used_bytes'], 60_000)
        self.assertEqual(len(list(iter_ticks(self.root / 'run'))), 32)
        self.assertEqual(writer.background_stats()['error'], None)
        quota = RunWriter(self.root / 'quota', {}, max_bytes=40_000)
        quota.start_background()
        with patch('palimpsest.records.os.fsync', side_effect=blocked):
            gate.clear()
            quota.event('holds-the-writer')
            for tick in range(32):
                quota.tick(0, tick, camera=np.zeros(1000, np.uint8))
            with self.assertRaisesRegex(RuntimeError, 'quota'):
                for tick in range(32, 64):
                    quota.tick(0, tick, camera=np.zeros(1000, np.uint8))
            gate.set()
        quota.close()

    def test_killed_process_leaves_a_valid_published_prefix(self):
        code = f"""
import os, sys, time
sys.path.insert(0, {str(REPO / 'src')!r})
import numpy as np
from pathlib import Path
from palimpsest import records
real = os.fsync
def slow(descriptor):
    time.sleep(.05)
    real(descriptor)
records.os.fsync = slow
writer = records.RunWriter(Path(sys.argv[1]), {{}})
writer.start_background()
for tick in range(100000):
    writer.tick(0, tick, camera=np.full(4096, tick % 251, np.uint8))
    if tick == 200:
        print('ready', flush=True)
"""
        child = subprocess.Popen([sys.executable, '-c', code, str(self.root / 'run')], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'ready')
            time.sleep(.4)
            child.send_signal(signal.SIGKILL)
            child.wait(10)
        finally:
            if child.poll() is None:
                child.kill()
            child.stdout.close()
        ticks = list(iter_ticks(self.root / 'run'))
        self.assertGreater(len(ticks), 0)
        self.assertEqual([tick['tick'] for tick in ticks], list(range(len(ticks))))
        self.assertEqual(len(ticks) % records.CHUNK_TICKS, 0)

    def test_drain_publishes_queued_events_without_changing_chunk_boundaries(self):
        writer = RunWriter(self.root / 'run', {})
        writer.start_background()
        def slow(descriptor):
            time.sleep(.1)
            REAL_FSYNC(descriptor)
        with patch('palimpsest.records.os.fsync', side_effect=slow):
            for tick in range(5):
                writer.tick(0, tick, action=np.zeros(2))
            writer.event('registered', name='x')
            writer.drain()
            self.assertEqual([json.loads(line)['kind'] for line in (self.root / 'run/events.jsonl').read_text().splitlines()],
                             ['registered'])  # the five buffered ticks stay buffered
        for tick in range(5, 32):
            writer.tick(0, tick, action=np.zeros(2))
        writer.finish({})
        writer.close()
        chunks = [event for event in map(json.loads, (self.root / 'run/events.jsonl').read_text().splitlines()) if event['kind'] == 'chunk']
        self.assertEqual([(event['start'], event['count']) for event in chunks], [(0, 32)])
        synchronous = RunWriter(self.root / 'sync', {})
        synchronous.drain()  # a no-op on the synchronous path
        synchronous.close()

    def test_snapshot_registration_is_durable_when_the_snapshot_returns(self):
        from palimpsest import worker
        from test_engine import SmallEnv
        from palimpsest.engine import Engine
        run = self.root / 'source'
        (run / 'snapshots').mkdir(parents=True)
        writer = RunWriter(run / 'recording', {'run_id': 'source'})
        engine = Engine(SmallEnv(), writer)
        writer.start_background()
        armed, gate = threading.Event(), threading.Event()
        def held(descriptor):
            if armed.is_set():
                gate.wait(5.)  # the writer is still busy with an earlier queued item
            REAL_FSYNC(descriptor)
        def save(snapshot, path, **kw):
            path.write_bytes(b'snapshot')
            armed.set()
            writer.event('earlier-queued-work')
            threading.Timer(.3, gate.set).start()
        config = {'scenario': 'sparse-navigation', 'texture': 'checker', 'controller': 'manual', 'device': 'cpu', 'seed': 0}
        with patch('palimpsest.snapshots.capture', return_value={'stub': True}), \
                patch('palimpsest.snapshots.save_snapshot', side_effect=save), \
                patch('palimpsest.records.os.fsync', side_effect=held):
            identifier = worker._snapshot(engine, run, {}, config)
            events = [json.loads(line) for line in (run / 'recording/events.jsonl').read_text().splitlines()]
        self.assertEqual([event['snapshot_id'] for event in events if event['kind'] == 'snapshot_registered'], [identifier])
        engine.close()

    def test_synchronous_default_is_unchanged(self):
        writer = RunWriter(self.root / 'run', {})
        self.assertIsNone(writer.background_stats())
        with patch('palimpsest.records.os.fsync', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):  # raised in the caller, as before
                writer.event('e')
        writer.close()


if __name__ == '__main__':
    unittest.main()
