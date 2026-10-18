import fcntl
import json
import os
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
    def test_existing_readonly_user_lease_still_excludes_another_writer(self):
        import errno
        home = self.root / 'private-home'
        private = home / '.cache/palimpsest'
        private.mkdir(parents=True)
        lease = private / 'writer.lock'
        lease.write_bytes(b'')
        real_open = os.open

        def readonly_user_lease(path, flags, *args, **kwargs):
            if Path(path) == lease and flags & os.O_RDWR:
                raise OSError(errno.EROFS, 'read-only filesystem', str(path))
            return real_open(path, flags, *args, **kwargs)

        with patch('pathlib.Path.home', return_value=home), patch('palimpsest.storage.os.open', side_effect=readonly_user_lease):
            with self.budget([self.root/'runs']).lock():
                with self.assertRaisesRegex(StorageLimitError, 'already owned'):
                    with self.budget([self.root/'other']).lock():
                        self.fail('A second writer must not acquire the user lease')
            with self.budget([self.root/'other']).lock():
                pass

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
        with self.assertRaisesRegex(StorageLimitError, "entry limit"):
            self.budget([managed], max_entries=1).usage()

    def test_configured_entry_limit_is_enforced_without_changing_default(self):
        managed = self.root / "managed"
        managed.mkdir()
        (managed / "one").touch()
        (managed / "two").touch()

        self.assertEqual(StorageLimits().max_entries, 100_000)
        with self.assertRaisesRegex(StorageLimitError, "entry limit"):
            self.budget([managed], max_entries=1).usage()
        self.assertEqual(self.budget([managed], max_entries=2).usage()["files"], 2)

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

    def test_nested_inventory_rejects_special_files_scan_errors_and_changed_root(self):
        managed = self.root / "managed"
        nested = managed / "a/b"
        nested.mkdir(parents=True)
        budget = self.budget([managed])
        file = nested / "native.log"
        file.write_bytes(b"abc")
        self.assertEqual(budget.usage()["used_bytes"], 3)
        file.write_bytes(b"abcdef")
        self.assertEqual(budget.usage()["used_bytes"], 6)
        special = nested / "special"
        os.mkfifo(special)
        with self.assertRaisesRegex(StorageLimitError, "nonregular"):
            budget.usage()
        special.unlink()
        special.symlink_to(nested / "absent")
        with self.assertRaisesRegex(StorageLimitError, "symlink"):
            budget.usage()
        special.unlink()
        nested.chmod(0)
        try:
            with self.assertRaises(PermissionError):
                budget.usage()
        finally:
            nested.chmod(0o700)
        retained = self.root / "retained"
        managed.rename(retained)
        managed.symlink_to(retained, target_is_directory=True)
        with self.assertRaisesRegex(StorageLimitError, "symlink"):
            budget.usage()
        managed.unlink()
        os.mkfifo(managed)
        with self.assertRaisesRegex(StorageLimitError, "root is not a directory"):
            budget.usage()

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
        last.mkdir()
        with (last / ".palimpsest-storage.lock").open("wb") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(StorageLimitError):
                with self.budget([first, last]).lock():
                    self.fail("second lock unexpectedly acquired")
            with self.budget([first]).lock():
                pass

    def test_overlapping_scopes_cannot_bypass_the_single_writer_lease(self):
        outer = self.budget([self.root / "runs"])
        nested = self.budget([self.root / "runs/lab", self.root / "exports"])
        for first, second in ((outer, nested), (nested, outer)):
            with first.lock():
                with self.assertRaisesRegex(StorageLimitError, "another writer"):
                    with second.lock():
                        self.fail("overlapping root scopes both acquired")
            with second.lock():
                pass

    def test_global_lease_rejects_symlinks_and_nonregular_files(self):
        home = self.root / "home"
        home.mkdir()
        budget = self.budget([self.root / "runs"])
        with patch("palimpsest.storage.Path.home", return_value=home):
            (home / ".cache").symlink_to(self.root, target_is_directory=True)
            with self.assertRaisesRegex(StorageLimitError, "symlink"):
                with budget.lock():
                    self.fail("symlink cache accepted")
            (home / ".cache").unlink()
            private = home / ".cache/palimpsest"
            private.mkdir(parents=True)
            lease = private / "writer.lock"
            lease.symlink_to(self.root / "other")
            with self.assertRaisesRegex(StorageLimitError, "symlink"):
                with budget.lock():
                    self.fail("symlink lease accepted")
            lease.unlink()
            os.mkfifo(lease)
            with self.assertRaisesRegex(StorageLimitError, "regular file"):
                with budget.lock():
                    self.fail("FIFO lease accepted")
            lease.unlink()
            lease.touch()
            wrong_owner = SimpleNamespace(st_mode=0o100600, st_uid=os.getuid() + 1)
            with patch("palimpsest.storage.os.fstat", return_value=wrong_owner):
                with self.assertRaisesRegex(StorageLimitError, "owned by the current user"):
                    with budget.lock():
                        self.fail("foreign-owned lease accepted")
            with budget.lock():
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
