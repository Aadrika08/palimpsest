"""Bounded per-write cost: a payload writer recounts its roots periodically, not per write."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from palimpsest import storage
from palimpsest.records import RunWriter, iter_ticks
from palimpsest.storage import StorageBudget, StorageLimitError, StorageLimits


class Recount(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.clock = [100.]
        patcher = patch.object(storage.time, 'monotonic', side_effect=lambda: self.clock[0])
        patcher.start()
        self.addCleanup(patcher.stop)

    def budget(self, max_bytes=10_000, **kwargs):
        return StorageBudget((self.root,), StorageLimits(max_bytes=max_bytes, min_free_bytes=0), **kwargs)

    def test_default_budget_still_walks_before_every_check(self):
        budget = self.budget()
        with patch.object(StorageBudget, 'usage', wraps=budget.usage) as usage:
            for _ in range(5):
                budget.check(10, path=self.root / 'x')
        self.assertEqual(usage.call_count, 5)

    def test_cached_budget_walks_once_per_interval_and_counts_admitted_bytes(self):
        budget = self.budget(recount_seconds=5.)
        with patch.object(StorageBudget, 'usage', wraps=budget.usage) as usage:
            for _ in range(50):
                budget.check(100, path=self.root / 'x')  # admitted, not yet written
            self.assertEqual(usage.call_count, 1)
            with self.assertRaises(StorageLimitError):  # 5,000 admitted + 5,001 > 10,000: fail closed
                budget.check(5_001, path=self.root / 'x')
            self.clock[0] += 5.
            budget.check(5_001, path=self.root / 'x')  # recount: nothing was actually written
            self.assertEqual(usage.call_count, 2)
        self.assertEqual(budget.recounts, 2)

    def test_files_written_by_this_writer_are_never_undercounted(self):
        budget = self.budget(recount_seconds=5.)
        for index in range(5):
            payload = b'x' * 1_500
            budget.check(len(payload), path=self.root / f'{index}.bin')
            (self.root / f'{index}.bin').write_bytes(payload)
        with self.assertRaises(StorageLimitError):  # 7,500 on disk + 3,000 > 10,000
            budget.check(3_000, path=self.root / 'next.bin')
        self.clock[0] += 5.
        with self.assertRaises(StorageLimitError):  # also after the recount
            budget.check(3_000, path=self.root / 'next.bin')
        budget.check(2_500, path=self.root / 'next.bin')

    def test_free_space_floor_is_checked_on_every_write(self):
        budget = StorageBudget((self.root,), StorageLimits(max_bytes=10_000, min_free_bytes=1_000), recount_seconds=5.)
        budget.check(10, path=self.root / 'x')
        with patch('palimpsest.storage.shutil.disk_usage', return_value=SimpleNamespace(free=500)):
            with self.assertRaisesRegex(StorageLimitError, 'free-space floor'):
                budget.check(10, path=self.root / 'x')

    def test_recording_quota_is_unchanged_with_cached_accounting(self):
        budget = self.budget(max_bytes=40_000, recount_seconds=5.)
        writer = RunWriter(self.root / 'recording', {}, storage_budget=budget)
        for tick in range(32):
            writer.tick(0, tick, camera=np.zeros(500, np.uint8))
        writer.flush()
        with self.assertRaises(StorageLimitError):
            for tick in range(32, 96):
                writer.tick(0, tick, camera=np.zeros(500, np.uint8))
        writer.close()
        self.assertEqual(len(list(iter_ticks(self.root / 'recording'))), 32)
        self.assertLessEqual(budget.usage()['used_bytes'], 40_000)

    def test_invalid_interval_is_rejected(self):
        for value in (0, -1., float('nan'), 'five'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.budget(recount_seconds=value)

    def test_live_owner_budget_uses_the_cached_recount(self):
        from palimpsest import worker
        config = {'roots': [str(self.root)], 'limits': {'max_bytes': 10_000, 'min_free_bytes': 0}, 'headroom_bytes': 0}
        budget = worker.owner_budget(config)
        self.assertEqual(budget.recount_seconds, worker.OWNER_RECOUNT_SECONDS)
        self.assertEqual(worker.OWNER_RECOUNT_SECONDS, 5.)
        self.assertIsNone(worker.owner_budget(None))


if __name__ == '__main__':
    unittest.main()
