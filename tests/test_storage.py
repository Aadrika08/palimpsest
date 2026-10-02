import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

from palimpsest.storage import StorageBudget, StorageLimits, StorageLimitError


class _StorageFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def budget(self, roots=None, **kwargs):
        return StorageBudget(roots or [self.root], StorageLimits(min_free_bytes=0, **kwargs))


class StorageTests(_StorageFixture, unittest.TestCase):
    def test_aggregate_recounts_all_files_and_nested_roots_once(self):
        run = self.root / "runs"
        exports = run / "exports"
        snapshots = run / "one/snapshots"
        exports.mkdir(parents=True)
        snapshots.mkdir(parents=True)
        for path, size in ((run / "one/stdout.log", 10), (snapshots / "initial.snp", 20),
                           (exports / "plot.svg", 30), (run / "orphan.tmp", 40)):
            path.write_bytes(b"x" * size)
        budget = self.budget([run, exports], max_bytes=110)
        self.assertEqual(budget.usage()["used_bytes"], 100)
        self.assertEqual(budget.usage()["files"], 4)
        budget.check(10, path=run / "new")
        with self.assertRaisesRegex(StorageLimitError, "quota"):
            budget.check(11, path=run / "new")
        self.assertFalse((run / "new").exists())
        (self.root / "assets").mkdir()
        (self.root / "assets/model.bin").write_bytes(b"x" * 1000)
        self.assertEqual(budget.usage()["used_bytes"], 100)

    def test_headroom_and_free_floor_are_checked_before_write(self):
        limits = StorageLimits(max_bytes=100, min_free_bytes=20)
        budget = StorageBudget([self.root], limits, headroom_bytes=10)
        with patch("palimpsest.storage.shutil.disk_usage", return_value=SimpleNamespace(free=50)):
            budget.check(20, path=self.root / "new")
            with self.assertRaisesRegex(StorageLimitError, "free-space"):
                budget.check(21, path=self.root / "new")
        with patch("palimpsest.storage.shutil.disk_usage", return_value=SimpleNamespace(free=1000)):
            budget.check(90, path=self.root / "new")
            with self.assertRaisesRegex(StorageLimitError, "quota"):
                budget.check(91, path=self.root / "new")

    def test_outside_symlink_and_inventory_bounds_reject(self):
        managed = self.root / "managed"
        managed.mkdir()
        budget = self.budget([managed])
        with self.assertRaisesRegex(StorageLimitError, "outside"):
            budget.check(1, path=self.root / "outside")
        (managed / "alias").symlink_to(self.root)
        with self.assertRaisesRegex(StorageLimitError, "symlink"):
            budget.usage()
        with self.assertRaisesRegex(StorageLimitError, "symlink"):
            budget.check(1, path=managed / "alias/file")
        (managed / "alias").unlink()
        (managed / "one").touch()
        (managed / "two").touch()
        with patch("palimpsest.storage.MAX_SCAN_ENTRIES", 1):
            with self.assertRaisesRegex(StorageLimitError, "entry limit"):
                budget.usage()

    def test_counts_include_initial_snapshot_and_validate_configuration(self):
        budget = self.budget(max_runs=2, max_snapshots=2, max_exports=2)
        for kind in ("runs", "snapshots", "exports"):
            budget.check_count(kind, 1)
            with self.assertRaisesRegex(StorageLimitError, "count limit"):
                budget.check_count(kind, 2)
        for values in ({"max_bytes": True}, {"max_runs": 0}, {"min_free_bytes": -1}):
            with self.assertRaises(ValueError):
                StorageLimits(**values)
        with self.assertRaises(ValueError):
            budget.check(True, path=self.root / "new")

    def test_nested_root_lease_blocks_another_process_and_releases(self):
        run = self.root / "runs"
        exports = run / "exports"
        budget = self.budget([run, exports])
        program = """
from pathlib import Path
import sys
from palimpsest.storage import StorageBudget, StorageLimits, StorageLimitError
try:
    with StorageBudget([Path(sys.argv[1])], StorageLimits()).lock():
        print('acquired')
except StorageLimitError:
    print('busy')
"""
        def probe():
            result = subprocess.run([sys.executable, "-c", program, str(exports)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()
        with budget.lock():
            self.assertEqual(probe(), "busy")
        self.assertEqual(probe(), "acquired")

    def test_failed_multi_root_lock_releases_already_acquired_roots(self):
        first, last = self.root / "a", self.root / "z"
        with self.budget([last]).lock():
            with self.assertRaises(StorageLimitError):
                with self.budget([first, last]).lock():
                    self.fail("second lock unexpectedly acquired")
            with self.budget([first]).lock():
                pass


@unittest.skipIf(np is None, "NumPy is provided by simulation extra")
class StorageWritersTests(_StorageFixture, unittest.TestCase):
    def test_snapshot_exact_container_bytes_preflight_and_reader_limit(self):
        from palimpsest.snapshots import read_snapshot, save_snapshot
        reference = self.root / "reference.snp"
        state = {"array": np.arange(8, dtype=np.float32), "metadata": {"value": 1}}
        size = save_snapshot(state, reference)
        self.assertEqual(size, reference.stat().st_size)
        destination = self.root / "managed"
        destination.mkdir()
        path = destination / "initial.snp"
        with self.assertRaises(StorageLimitError):
            save_snapshot(state, path, storage_budget=self.budget([destination], max_bytes=size - 1))
        self.assertFalse(path.exists())
        with self.assertRaises(StorageLimitError):
            save_snapshot(state, path, storage_budget=self.budget([destination], max_bytes=size + 99), preflight_bytes=100)
        self.assertFalse(path.exists())
        budget = self.budget([destination], max_bytes=size + 100)
        self.assertEqual(save_snapshot(state, path, storage_budget=budget, preflight_bytes=100), size)
        budget.check(100, path=destination / "next")  # An estimate does not become a permanent reservation.
        np.testing.assert_array_equal(read_snapshot(path)["array"], state["array"])
        with self.assertRaises(FileExistsError):
            save_snapshot(state, path)
        with patch("palimpsest.snapshots.MAX_BYTES", 128):
            with self.assertRaisesRegex(ValueError, "container exceeds"):
                save_snapshot({"a": 1}, destination / "oversized.snp")
        self.assertFalse((destination / "oversized.snp").exists())

    def test_aggregate_quota_failure_preserves_published_recording_prefix(self):
        from palimpsest.records import RunWriter, iter_ticks
        budget = self.budget(max_bytes=10_000)
        writer = RunWriter(self.root / "recording", {}, storage_budget=budget)
        for tick in range(32):
            writer.tick(0, tick, action=np.zeros(2))
        remaining = budget.usage()["remaining_bytes"]
        (self.root / "snapshot-or-log.bin").write_bytes(b"x" * (remaining - 1))
        writer.tick(0, 32, action=np.zeros(2))
        with self.assertRaises(StorageLimitError):
            writer.finish({})
        writer.close()
        self.assertEqual(len(list(iter_ticks(self.root / "recording"))), 32)
        self.assertEqual(json.loads((self.root / "recording/manifest.json").read_text())["status"], "running")
        self.assertLessEqual(budget.usage()["used_bytes"], budget.limits.max_bytes)
        self.assertFalse((self.root / "recording/chunks/000001.npz").exists())

    def test_atomic_manifest_check_counts_old_and_new_versions(self):
        from palimpsest.records import RunWriter
        budget = self.budget(max_bytes=10_000)
        writer = RunWriter(self.root / "recording", {}, storage_budget=budget)
        path = self.root / "recording/manifest.json"
        original = path.read_bytes()
        final = {**writer.manifest, "status": "completed", "recorded_ticks": 0, "recorded_chunks": 0, "recorded_events": 0}
        new_size = len((json.dumps(final, allow_nan=False, sort_keys=True) + "\n").encode())
        (self.root / "other-data").write_bytes(b"x" * (budget.usage()["remaining_bytes"] - new_size + 1))
        with self.assertRaises(StorageLimitError):
            writer.finish({})
        writer.close()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(path.with_suffix(".tmp").exists())


if __name__ == "__main__":
    unittest.main()
