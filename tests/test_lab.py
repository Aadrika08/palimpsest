import os
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from palimpsest.lab import LabSupervisor, create_app
from palimpsest.storage import StorageLimits, StorageLimitError


REPO = Path(__file__).resolve().parents[1]


def hung_owner(config, commands, replies, display, disconnected, stop, progress):
    os.setsid()
    while True:
        time.sleep(.05)


def stalled_ready_owner(config, commands, replies, display, disconnected, stop, progress):
    os.setsid()
    replies.put({"version": 1, "type": "status", "run_id": config["run_id"], "status": "ready", "state": {"phase": "running"}})
    progress.value = time.monotonic()
    while True:
        time.sleep(.05)


def hung_owner_with_child(config, commands, replies, display, disconnected, stop, progress):
    os.setsid()
    child = os.fork()
    if child == 0:
        while True:
            time.sleep(.05)
    (Path(config["run_path"]) / "child.pid").write_text(str(child))
    progress.value = time.monotonic()
    while True:
        time.sleep(.05)


def completed_owner(config, commands, replies, display, disconnected, stop, progress):
    os.setsid()
    replies.put({"version": 1, "type": "closed", "run_id": config["run_id"], "status": "closed",
                 "state": {"phase": "stopped", "episode": 0, "total_tick": 0}, "receipts": []})


def flooding_owner(*args):
    from palimpsest import worker
    def flood(*unused):
        os.write(1, b"native diagnostic\n" * 100000)
        time.sleep(30)
    worker._own = flood
    worker.run_worker(*args)


class ApiGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        app = create_app(REPO, Path(self.temp.name) / "assets", Path(self.temp.name) / "runs")
        self.client = self.enterContext(TestClient(app, base_url="http://127.0.0.1:8765"))
        response = self.client.get("/api/v1/session")
        self.assertEqual(response.status_code, 200)
        self.token = response.json()["token"]
        self.headers = {"X-Palimpsest-Session": self.token, "Origin": "http://127.0.0.1:8765"}

    def test_native_owner_log_limit_is_terminal_and_bounded(self):
        supervisor = self.client.app.state.lab
        supervisor.worker_target = flooding_owner
        supervisor.log_max_bytes = 4096
        run = supervisor.start({"log_max_bytes": 4096})
        owner = supervisor.workers[run]
        self.assertTrue(owner.done.wait(5.))
        result = supervisor.close(run)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure"]["type"], "LogLimit")
        self.assertEqual((supervisor.path(run) / "stdout.log").stat().st_size, 4096)
        self.assertFalse(owner.process.is_alive())

    def test_active_owner_prevents_export_and_second_service_on_same_roots(self):
        supervisor = self.client.app.state.lab
        with self.assertRaises(StorageLimitError):
            LabSupervisor(REPO, supervisor.asset_root, supervisor.runs_root)
        supervisor.worker_target = hung_owner
        identifier = supervisor.start({})
        with self.assertRaisesRegex(RuntimeError, "Close the active owner"):
            supervisor.export(identifier, "svg")
        self.assertEqual(list(supervisor.export_root.glob("*.svg")), [])

    def test_host_origin_and_session_guards(self):
        for headers in ({"Host": "evil.example:8765"}, {"Origin": "https://evil.example"},
                        {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.client.get("/api/v1/session", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/v1/runs").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/runs", headers={"X-Palimpsest-Session": "bad"}).status_code, 401)

    def test_bounded_body_and_path_fields_rejected_before_launch(self):
        response = self.client.post("/api/v1/runs", content=b"x" * 16385, headers=self.headers)
        self.assertEqual(response.status_code, 413)
        for body in ({"output": "/tmp/escape"}, {"controller": "invented"}, {"seed": True},
                     {"device": "cuda", "controller": "manual"}):
            self.assertEqual(self.client.post("/api/v1/runs", json=body, headers=self.headers).status_code, 400)
        self.assertIsNone(self.client.app.state.lab.active_run_id)

    def test_unregistered_ids_and_traversal_rejected(self):
        response = self.client.get("/api/v1/runs/" + "a" * 32, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        response = self.client.post("/api/v1/branches", json={"source_run_id": "../escape", "snapshot_id": "b" * 32}, headers=self.headers)
        self.assertEqual(response.status_code, 400)

    def test_command_requires_explicit_revision(self):
        response = self.client.post("/api/v1/runs/" + "a" * 32 + "/commands", json={
            "id": "pause", "kind": "pause", "expected_state": "running", "expected_episode": 0}, headers=self.headers)
        self.assertEqual(response.status_code, 400)

    def test_transport_events_have_separate_bounded_cursor(self):
        root = self.client.app.state.lab.runs_root / ("a" * 32)
        root.mkdir()
        (root / "job-events.jsonl").write_text('{"type":"job_disconnected"}\n{"type":"job_command"}\n')
        response = self.client.get("/api/v1/runs/" + "a" * 32 + "/events?limit=1", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"events": [{"type": "job_disconnected"}], "next": 1, "stream": "transport"})
        response = self.client.get("/api/v1/runs/" + "a" * 32 + "/events?after=1", headers=self.headers)
        self.assertEqual(response.json()["events"], [{"type": "job_command"}])
        response = self.client.get("/api/v1/runs/" + "a" * 32 + "/events?after=1000001", headers=self.headers)
        self.assertEqual(response.status_code, 400)

    def test_websocket_first_message_authentication(self):
        with self.client.websocket_connect("ws://127.0.0.1:8765/api/v1/stream") as socket:
            socket.send_json({"token": "wrong"})
            with self.assertRaises(WebSocketDisconnect):
                socket.receive_json()


class Supervision(unittest.TestCase):
    def test_completed_owner_cache_is_bounded_and_evicted_ids_remain_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            supervisor = LabSupervisor(REPO, Path(tmp) / "assets", Path(tmp) / "runs",
                                       startup_timeout=5., worker_target=completed_owner)
            self.addCleanup(supervisor.shutdown)
            identifiers = []
            for _ in range(11):
                identifier = supervisor.start({})
                identifiers.append(identifier)
                owner = supervisor.workers[identifier]
                self.assertTrue(owner.done.wait(5.))
                self.assertEqual(supervisor.close(identifier)["status"], "closed")
            deadline = time.monotonic() + 2.
            while len(supervisor.workers) > 8 and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertLessEqual(len(supervisor.workers), 8)
            self.assertNotIn(identifiers[0], supervisor.workers)
            self.assertEqual(supervisor.describe(identifiers[0])["state"]["total_tick"], 0)
            self.assertEqual(supervisor.describe(identifiers[0])["status"], "closed")

    def test_stale_display_cannot_overwrite_authoritative_pause(self):
        supervisor = object.__new__(LabSupervisor)
        owner = SimpleNamespace(view={"state": {"revision": 2, "total_tick": 3, "phase": "paused"},
                                      "receipts": [{"id": "pause", "status": "applied"}], "sample": None})
        supervisor.workers = {"run": owner}
        supervisor._handle("run", {"type": "sample", "state": {"revision": 1, "total_tick": 3, "phase": "running"}})
        self.assertIsNone(owner.view["sample"])
        self.assertEqual(owner.view["state"]["phase"], "paused")
        self.assertEqual(owner.view["receipts"][0]["status"], "applied")

    def test_spawned_loading_owner_watchdog_and_single_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            supervisor = LabSupervisor(REPO, Path(tmp) / "assets", Path(tmp) / "runs",
                startup_timeout=.2, step_timeout=.2, worker_target=hung_owner)
            self.addCleanup(supervisor.shutdown)
            run = supervisor.start({"scenario": "reproduction", "texture": "checker",
                                    "controller": "manual", "device": "cpu", "seed": 0})
            with self.assertRaises(RuntimeError):
                supervisor.start({"scenario": "reproduction", "texture": "checker",
                                  "controller": "manual", "device": "cpu", "seed": 1})
            deadline = time.monotonic() + 5
            while supervisor.describe(run)["status"] != "failed" and time.monotonic() < deadline:
                time.sleep(.03)
            self.assertEqual(supervisor.describe(run)["status"], "failed")
            self.assertFalse(supervisor.workers[run].process.is_alive())
            self.assertTrue((Path(tmp) / "runs" / run / "supervisor.json").exists())

    @unittest.skipUnless(hasattr(os, "fork") and Path("/proc").is_dir(), "Linux process-group proof")
    def test_watchdog_terminates_owner_process_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            supervisor = LabSupervisor(REPO, Path(tmp) / "assets", Path(tmp) / "runs",
                startup_timeout=1., worker_target=hung_owner_with_child)
            self.addCleanup(supervisor.shutdown)
            run = supervisor.start({})
            pid_file = supervisor.path(run) / "child.pid"
            deadline = time.monotonic() + 5
            while not pid_file.exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(pid_file.exists())
            child = int(pid_file.read_text())
            while supervisor.describe(run)["status"] != "failed" and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertEqual(supervisor.describe(run)["failure"]["type"], "WorkerTimeout")
            stat = Path(f"/proc/{child}/stat")
            self.assertTrue(not stat.exists() or stat.read_text().split(") ", 1)[1][0] == "Z")

    def test_step_watchdog_stays_active_after_disconnect(self):
        with tempfile.TemporaryDirectory() as tmp:
            supervisor = LabSupervisor(REPO, Path(tmp) / "assets", Path(tmp) / "runs",
                startup_timeout=5., step_timeout=.15, worker_target=stalled_ready_owner)
            self.addCleanup(supervisor.shutdown)
            run = supervisor.start({"scenario": "reproduction", "texture": "checker", "controller": "manual", "device": "cpu", "seed": 0})
            deadline = time.monotonic() + 5
            while supervisor.describe(run)["status"] == "loading" and time.monotonic() < deadline:
                time.sleep(.02)
            supervisor.disconnect()
            while supervisor.describe(run)["status"] != "failed" and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertEqual(supervisor.describe(run)["failure"]["type"], "WorkerTimeout")
            self.assertFalse(supervisor.workers[run].process.is_alive())


@unittest.skipUnless(os.environ.get("PALIMPSEST_SIMULATION_TESTS") == "1", "opt-in real manual/EGL owner integration")
class ActualOwner(unittest.TestCase):
    def test_storage_preflight_and_snapshot_count_stop_before_more_physics(self):
        for limits, expected_kind in ((StorageLimits(max_bytes=16 * 1024**2, min_free_bytes=0), "preflight"),
                                      (StorageLimits(max_snapshots=1), "snapshot")):
            with self.subTest(kind=expected_kind), tempfile.TemporaryDirectory() as tmp:
                supervisor = LabSupervisor(REPO, Path(tmp) / "assets", Path(tmp) / "runs", storage_limits=limits)
                try:
                    run = supervisor.start({"scenario": "sparse-navigation", "texture": "checker",
                                            "controller": "manual", "device": "cpu", "seed": 0})
                    deadline = time.monotonic() + 60
                    while supervisor.describe(run)["status"] == "loading" and time.monotonic() < deadline:
                        time.sleep(.02)
                    if expected_kind == "snapshot":
                        self.assertEqual(supervisor.describe(run)["status"], "ready")
                        with self.assertRaises(RuntimeError):
                            supervisor.call(run, "snapshot", {"expected_revision": 0})
                    self.assertTrue(supervisor.workers[run].done.wait(10.))
                    view = supervisor.close(run)
                    self.assertEqual(view["status"], "failed")
                    self.assertEqual(view["failure"]["type"], "StorageLimitError")
                    manifest = json.loads((supervisor.path(run) / "recording/manifest.json").read_text())
                    self.assertEqual(manifest["status"], "failed")
                    self.assertEqual(manifest["total_tick"], 0)
                    self.assertEqual(len(list((supervisor.path(run) / "snapshots").glob("*.snp"))),
                                     0 if expected_kind == "preflight" else 1)
                finally:
                    supervisor.shutdown()

    def test_actual_spawned_manual_step_snapshot_branch_and_disconnect(self):
        with tempfile.TemporaryDirectory() as tmp:
            supervisor = LabSupervisor(REPO, Path(tmp) / "assets", Path(tmp) / "runs", startup_timeout=60.)
            self.addCleanup(supervisor.shutdown)
            run = supervisor.start({"scenario": "sparse-navigation", "texture": "checker", "controller": "manual", "device": "cpu", "seed": 0})
            def wait(identifier, predicate):
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    view = supervisor.describe(identifier)
                    if view["status"] == "failed":
                        self.fail(str(view.get("failure")))
                    if predicate(view):
                        return view
                    time.sleep(.03)
                self.fail("Actual owner boundary timeout")
            view = wait(run, lambda v: v["status"] == "ready" and v["sample"] is not None)
            self.assertEqual(view["state"]["total_tick"], 0)
            self.assertEqual(view["sample"]["inputs"]["stage"], "next")
            self.assertTrue(view["sample"]["inputs"]["cam_left"].startswith("data:image/png;base64,"))
            supervisor.call(run, "command", {"id": "one-step", "kind": "step", "expected_state": "paused", "expected_episode": 0, "expected_revision": 0})
            view = wait(run, lambda v: v["state"]["total_tick"] == 1 and v["sample"]["inputs"]["stage"] == "used")
            revision = view["state"]["revision"]
            result = supervisor.call(run, "snapshot", {"expected_revision": revision})
            registry_path = supervisor.path(run) / 'snapshots/index.json'
            original_registry = registry_path.read_bytes()
            changed = json.loads(original_registry)
            changed['snapshots'][result['snapshot_id']]['sha256'] = '0' * 64
            registry_path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'registry differs'):
                supervisor.snapshot(run, result['snapshot_id'])
            registry_path.write_bytes(original_registry)
            path, item = supervisor.snapshot(run, result["snapshot_id"])
            supervisor.close(run)
            branch = supervisor.start({**item["config"], "snapshot_path": str(path), "snapshot_sha256": item["sha256"],
                "snapshot_id": result["snapshot_id"], "source_run_path": str(supervisor.path(run)), "replace_controller": False})
            view = wait(branch, lambda v: v["status"] == "ready" and v["sample"] is not None)
            self.assertEqual(view["state"]["total_tick"], 1)
            self.assertEqual(view["state"]["parent_run_id"], run)
            state = view["state"]
            for name, kind, payload in (("intent", "set_action", {"action": [1., .2]}), ("go", "run", {})):
                supervisor.call(branch, "command", {"id": name, "kind": kind, "expected_state": "paused", "expected_episode": 0,
                    "expected_revision": state["revision"], "payload": payload})
            wait(branch, lambda v: v["state"]["phase"] == "running")
            supervisor.disconnect()
            view = wait(branch, lambda v: v["state"]["phase"] == "paused")
            self.assertEqual(view["state"]["pending_commands"], 0)
            self.assertEqual(supervisor.close(branch)["status"], "closed")


if __name__ == "__main__":
    unittest.main()
