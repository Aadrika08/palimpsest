import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from palimpsest.lab import LabSupervisor


def snapshot_quota_owner(*args):
    """Exhaust the real recorder cap after snapshot/index writes, before registration."""
    from palimpsest import worker
    original_snapshot = worker._snapshot

    def snapshot(engine, path, registry, config, initial=False, budget=None, preflight_bytes=0):
        if not initial:
            original_event = engine.writer.event

            def event(kind, **fields):
                if kind == "snapshot_registered":
                    engine.writer._max_bytes = engine.writer._bytes
                return original_event(kind, **fields)

            engine.writer.event = event
        return original_snapshot(engine, path, registry, config, initial=initial,
                                 budget=budget, preflight_bytes=preflight_bytes)

    with patch.object(worker, "_snapshot", snapshot):
        worker.run_worker(*args)


@unittest.skipUnless(os.environ.get("PALIMPSEST_SIMULATION_TESTS") == "1", "opt-in actual upstream EGL owner")
class SnapshotPublicationFailure(unittest.TestCase):
    def test_recording_quota_failure_after_snapshot_write_is_terminal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            supervisor = LabSupervisor(Path(__file__).resolve().parents[1], root / "assets", root / "runs",
                                       worker_target=snapshot_quota_owner)
            try:
                identifier = supervisor.start({"controller": "manual", "device": "cpu", "seed": 11,
                                               "scenario": "sparse-navigation", "texture": "checker"})
                deadline = time.monotonic() + 20.
                while supervisor.describe(identifier)["status"] == "loading" and time.monotonic() < deadline:
                    time.sleep(.02)
                state = supervisor.describe(identifier)
                self.assertEqual(state["status"], "ready", state)
                with self.assertRaises(RuntimeError):
                    supervisor.call(identifier, "snapshot", {"expected_revision": state["state"]["revision"]})
                owner = supervisor.workers[identifier]
                self.assertTrue(owner.done.wait(5.))
                result = supervisor.close(identifier)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["state"]["phase"], "failed")
                self.assertEqual(result["state"]["total_tick"], 0)
                run = supervisor.path(identifier)
                self.assertEqual(len(list((run / "snapshots").glob("*.snp"))), 2)
                events = [json.loads(line) for line in (run / "recording/events.jsonl").read_text().splitlines()]
                self.assertEqual(sum(item["kind"] == "snapshot_registered" for item in events), 1)
                self.assertNotEqual(json.loads((run / "recording/manifest.json").read_text())["status"], "completed")
                self.assertFalse(owner.process.is_alive())
            finally:
                supervisor.shutdown()


if __name__ == "__main__":
    unittest.main()
