import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

from palimpsest.records import RunWriter, iter_ticks


@unittest.skipIf(np is None, "NumPy is provided by the simulation extra")
class RecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "run"

    def test_lossless_chunks_episode_boundaries_and_final_manifest(self):
        writer = RunWriter(self.path, {"seed": 7})
        writer.event("started", controller="teacher")
        camera = np.arange(12, dtype=np.uint8).reshape(2, 2, 3)
        for tick in range(35):
            writer.tick(0, tick, camera=camera, action=np.array([tick, -tick], np.float32))
        camera[:] = 0  # Buffered values must not alias mutable sensor buffers.
        writer.tick(1, 0, camera=camera, action=np.zeros(2, np.float32))
        writer.finish({"episodes": 2})
        writer.close()
        manifest = json.loads((self.path / "manifest.json").read_text())
        self.assertEqual((manifest["status"], manifest["seed"], manifest["episodes"]), ("completed", 7, 2))
        events = [json.loads(line) for line in (self.path / "events.jsonl").read_text().splitlines()]
        self.assertEqual([event["sequence"] for event in events], list(range(len(events))))
        chunks = [event for event in events if event["kind"] == "chunk"]
        self.assertEqual([(event["episode"], event["count"]) for event in chunks], [(0, 32), (0, 3), (1, 1)])
        ticks = list(iter_ticks(self.path))
        self.assertEqual([(tick["episode"], tick["tick"]) for tick in ticks], [(0, tick) for tick in range(35)] + [(1, 0)])
        np.testing.assert_array_equal(ticks[34]["camera"], np.arange(12, dtype=np.uint8).reshape(2, 2, 3))
        self.assertEqual(ticks[34]["action"].dtype, np.dtype("float32"))
        np.testing.assert_array_equal(ticks[35]["camera"], camera)

    def test_running_recovery_ignores_unpublished_chunks_and_partial_event(self):
        writer = RunWriter(self.path, {})
        for tick in range(32):
            writer.tick(0, tick, action=np.zeros(2))
        writer.close()
        (self.path / "chunks" / "unpublished.npz").write_bytes(b"incomplete")
        with (self.path / "events.jsonl").open("ab") as stream:
            stream.write(b'{"sequence":1,"kind":"chunk"')
        self.assertEqual(len(list(iter_ticks(self.path))), 32)
        self.assertEqual(json.loads((self.path / "manifest.json").read_text())["status"], "running")

    def test_exclusive_directory_and_rejected_data_do_not_corrupt_pending_ticks(self):
        writer = RunWriter(self.path, {})
        self.addCleanup(writer.close)
        with self.assertRaises(FileExistsError):
            RunWriter(self.path, {})
        for data in ({"bad": np.array([object()])}, {"../bad": np.zeros(1)}, {"file": np.zeros(1)}):
            with self.subTest(data=list(data)):
                with self.assertRaises(ValueError):
                    writer.tick(0, 0, **data)
        writer.tick(0, 0, action=np.zeros(2))
        with self.assertRaises(ValueError):
            writer.tick(0, 2, action=np.zeros(2))
        with self.assertRaises(ValueError):
            writer.tick(0, 1, action=np.zeros(3))
        writer.tick(0, 1, action=np.ones(2))
        writer.finish({})
        self.assertEqual(len(list(iter_ticks(self.path))), 2)
        with self.assertRaises(ValueError):
            writer.event("late")

    def test_corrupt_hash_count_shape_events_and_unsafe_paths_are_rejected(self):
        writer = RunWriter(self.path, {})
        writer.tick(0, 0, action=np.zeros(2))
        writer.finish({})
        events_path = self.path / "events.jsonl"
        original = events_path.read_text()
        event = json.loads(original)
        chunk_path = self.path / event["path"]
        chunk_bytes = chunk_path.read_bytes()
        chunk_path.write_bytes(chunk_bytes + b"corruption")
        with self.assertRaises(ValueError):
            list(iter_ticks(self.path))
        chunk_path.write_bytes(chunk_bytes)
        for change in ({"count": 2}, {"sequence": 5}, {"path": "../outside.npz"}, {"arrays": {"action": {"dtype": "<f8", "shape": [3]}}}):
            with self.subTest(change=change):
                events_path.write_text(json.dumps({**event, **change}) + "\n")
                with self.assertRaises(ValueError):
                    list(iter_ticks(self.path))
        events_path.write_text(original.rstrip("\n"))
        with self.assertRaises(ValueError):
            list(iter_ticks(self.path))
        events_path.write_text("")
        with self.assertRaises(ValueError):
            list(iter_ticks(self.path))
        events_path.write_text(original)
        outside = self.path.parent / "outside.npz"
        outside.write_bytes(chunk_bytes)
        chunk_path.unlink()
        chunk_path.symlink_to(outside)
        with self.assertRaises(ValueError):
            list(iter_ticks(self.path))

    def test_object_archive_is_rejected_even_with_matching_hash(self):
        writer = RunWriter(self.path, {})
        writer.tick(0, 0, action=np.zeros(2))
        writer.finish({})
        events_path = self.path / "events.jsonl"
        event = json.loads(events_path.read_text())
        chunk_path = self.path / event["path"]
        np.savez(chunk_path, action=np.array([[object()]], dtype=object))
        event["sha256"] = hashlib.sha256(chunk_path.read_bytes()).hexdigest()
        event["arrays"]["action"] = {"dtype": "|O", "shape": [1]}
        events_path.write_text(json.dumps(event) + "\n")
        with self.assertRaises(ValueError):
            list(iter_ticks(self.path))

    def test_storage_failure_aborts_publication_and_close_does_not_retry(self):
        writer = RunWriter(self.path, {})
        writer.tick(0, 0, action=np.zeros(2))
        with patch("palimpsest.records.os.fsync", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                writer.finish({})
        writer.close()
        self.assertEqual(json.loads((self.path / "manifest.json").read_text())["status"], "running")
        self.assertEqual(list(iter_ticks(self.path)), [])
        self.assertEqual((self.path / "events.jsonl").read_text(), "")

    def test_final_short_chunk_quota_preserves_published_prefix(self):
        writer = RunWriter(self.path, {}, max_bytes=4200)
        for tick in range(32):
            writer.tick(0, tick, camera=np.zeros(100, dtype=np.uint8))
        writer.flush()
        writer.tick(1, 0, camera=np.ones(100, dtype=np.uint8))
        with self.assertRaisesRegex(RuntimeError, "quota"):
            writer.finish({})
        writer.close()
        self.assertEqual(json.loads((self.path / "manifest.json").read_text())["status"], "running")
        self.assertLessEqual(sum(file.stat().st_size for file in self.path.rglob("*") if file.is_file()), 4200)
        self.assertEqual(len(list(iter_ticks(self.path))), 32)

        short = self.path.parent / "short"
        writer = RunWriter(short, {}, max_bytes=1000)
        writer.tick(0, 0, camera=np.zeros(1200, dtype=np.uint8))
        with self.assertRaisesRegex(RuntimeError, "quota"):
            writer.finish({})
        writer.close()
        self.assertEqual(list(iter_ticks(short)), [])
        self.assertEqual(list((short / "chunks").iterdir()), [])
        self.assertEqual(json.loads((short / "manifest.json").read_text())["status"], "running")

    def test_event_quota_is_checked_before_write_and_successful_bundle_fits(self):
        writer = RunWriter(self.path, {}, max_bytes=1000)
        with self.assertRaisesRegex(RuntimeError, "quota"):
            writer.event("oversized", text="x" * 1000)
        writer.close()
        self.assertEqual((self.path / "events.jsonl").read_text(), "")
        terminal = self.path.parent / "terminal"
        writer = RunWriter(terminal, {}, max_bytes=1000)
        with self.assertRaisesRegex(RuntimeError, "quota"):
            writer.finish({"summary": "x" * 1000})
        writer.close()
        self.assertEqual(json.loads((terminal / "manifest.json").read_text())["status"], "running")
        successful = self.path.parent / "successful"
        writer = RunWriter(successful, {}, max_bytes=2000)
        writer.tick(0, 0, action=np.zeros(2))
        writer.flush()
        writer.finish({})
        self.assertEqual(len(list(iter_ticks(successful))), 1)
        self.assertLessEqual(sum(file.stat().st_size for file in successful.rglob("*") if file.is_file()), 2000)


if __name__ == "__main__":
    unittest.main()
