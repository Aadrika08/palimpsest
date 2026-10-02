import copy
import json
from pathlib import Path
from queue import Queue, Full
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest

from palimpsest.worker import latest_display, authoritative, _ReplayTransport, _ExecutionTiming


class QueueContracts(unittest.TestCase):
    def test_active_timing_excludes_loading_pauses_and_branch_origin(self):
        clock = _ExecutionTiming(100., 50)
        self.assertIsNone(clock.view()["rtf"])
        clock.update(110., 51, True, .01)
        clock.update(110.04, 53, True, .01)
        clock.update(110.05, 53, False)
        clock.update(210., 53, False)
        self.assertAlmostEqual(clock.view()["advanced_simulation_seconds"], .06)
        self.assertAlmostEqual(clock.view()["active_wall_seconds"], .06)
        self.assertAlmostEqual(clock.view()["rtf"], 1.)
        clock.update(220., 54, False, .008)  # A paused single step charges its execution.
        self.assertAlmostEqual(clock.view()["active_wall_seconds"], .068)

    def test_only_display_sample_is_replaced(self):
        queue = Queue(maxsize=1)
        latest_display(queue, {"tick": 1})
        latest_display(queue, {"tick": 2})
        self.assertEqual(queue.get_nowait(), {"tick": 2})

    def test_authoritative_backpressure_is_explicit(self):
        queue = Queue(maxsize=1)
        authoritative(queue, {"receipt": 1}, timeout=.01)
        with self.assertRaises(Full):
            authoritative(queue, {"receipt": 2}, timeout=.01)
        self.assertEqual(queue.get_nowait(), {"receipt": 1})


class ReplayTransport(unittest.TestCase):
    def setUp(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(tmp)
        self.commands, self.messages = Queue(), []
        self.disconnected, self.stop = threading.Event(), threading.Event()
        self.progress = SimpleNamespace(value=0.)
        self.transport = _ReplayTransport(self.path, "actions", self.commands, self.messages.append,
                                          self.disconnected, self.stop, self.progress)
        self.state = {"phase": "running", "episode": 0, "episode_step": 3, "total_tick": 3,
                      "revision": 9, "pending_commands": 2}

    def request(self, identifier, kind, phase, revision):
        self.commands.put({"request_id": identifier, "op": "command", "body": {
            "id": identifier, "kind": kind, "expected_state": phase,
            "expected_episode": 0, "expected_revision": revision}})

    def test_loading_disconnect_pauses_without_changing_underlying_state(self):
        original = copy.deepcopy(self.state)
        self.disconnected.set()
        self.transport("loading")
        thread = threading.Thread(target=self.transport, args=("ready", self.state))
        thread.start()
        deadline = time.monotonic() + 1
        while self.transport.phase != "paused" and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertEqual(self.transport.phase, "paused")
        self.assertTrue(thread.is_alive())
        self.assertGreater(self.progress.value, 0.)
        self.request("resume", "run", "paused", 1)
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.state, original)
        self.assertEqual(self.transport.receipts["resume"]["status"], "applied")
        self.assertEqual(self.transport.view()["underlying_state"]["revision"], 9)
        self.assertEqual(self.transport.view()["state"]["revision"], 2)
        events = [json.loads(line) for line in (self.path / "job-events.jsonl").read_text().splitlines()]
        self.assertEqual([row["type"] for row in events], ["job_disconnected", "job_command"])

    def test_stop_is_receipted_and_live_mutations_rejected(self):
        self.request("edit", "set_action", "running", 0)
        self.request("cancel", "stop", "running", 0)
        with self.assertRaises(InterruptedError):
            self.transport("ready", self.state)
        errors = [message["error"] for message in self.messages if "error" in message]
        self.assertEqual(errors[0]["type"], "ValueError")
        self.assertEqual(self.transport.receipts["cancel"]["status"], "applied")
        self.assertEqual(self.transport.phase, "canceled")

    def test_duplicate_command_does_not_resume_paused_job(self):
        self.request("run", "run", "running", 0)
        self.transport("ready", self.state)
        revision = self.transport.revision
        self.transport.phase = "paused"
        self.transport.command({"id": "run", "kind": "run", "expected_state": "running",
                                "expected_episode": 0, "expected_revision": 0})
        self.assertEqual(self.transport.phase, "paused")
        self.assertEqual(self.transport.revision, revision)
        self.assertEqual(len(self.transport.receipts), 1)

    def test_loading_stop_interrupts_without_waiting_for_ready(self):
        self.stop.set()
        with self.assertRaises(InterruptedError):
            self.transport("loading")


if __name__ == "__main__":
    unittest.main()
