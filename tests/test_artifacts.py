import base64
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import xml.etree.ElementTree as ET
import zipfile

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

from palimpsest import artifacts
from palimpsest.records import RunWriter


@unittest.skipIf(np is None, "NumPy is provided by the simulation extra")
class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        artifacts._CACHE.clear()

    def run_fixture(self, count=2, *, seed=7, completed=True, world=True, start=0, parent=None):
        run = self.root / str(uuid.uuid4())
        writer = RunWriter(run / "recording", {"run_id": run.name, "controller": "manual", "seed": seed,
                           "scenario": "reproduction", "texture": "checker", "population_names": [],
                           "parent_run_id": parent, "source_snapshot_id": "initial"})
        geometry = {"arena": 7., "pose": [0., 0., 0.], "obstacles": [[3., 3., .3]], "goal": [5., 5., .5]}
        event = {"episode": 0, "episode_step": start, "tick": start, "run_id": run.name}
        if world:
            event["world"] = geometry
        writer.event("episode_started", **event)
        writer.event("environment", upstream_commit="abc", lock_sha256="123", source_sha256={"env.py": "456"})
        camera = np.arange(12, dtype=np.uint8).reshape(2, 2, 3)
        for tick in range(start, start + count):
            if tick == start + 1:
                writer.event("intervention", episode=0, episode_step=tick, tick=tick, change={
                    "kind": "move_goal", "old": {"xy": [5., 5.]}, "new": {"xy": [4., 2.]}})
            writer.tick(0, tick, cam_left=camera, cam_right=np.zeros_like(camera),
                        raw_cam_left=camera, raw_cam_right=camera, sensors=np.array([0., 1., 0., 1.]),
                        pose=np.array([tick * .1, tick * .2, 0.]), next_pose=np.array([(tick + 1) * .1, (tick + 1) * .2, .25]),
                        action=np.array([1., .25]), control=np.array([2., .5]), reward=np.array(.5),
                        simulation_time=np.array((tick + 1) * .02), latency=np.array(.001), step_latency=np.array(.002),
                        eyes=np.array([True, False]), revision=np.array(tick), population_stats=np.empty((0, 4)))
        if completed:
            writer.finish({"final_phase": "paused", "metrics": {"reward": count * .5}})
        writer.close()
        return run

    def register_snapshot(self, run, *, initial=True, content=None):
        from palimpsest.snapshots import save_snapshot
        identifier = uuid.uuid4().hex
        filename = "initial.snp" if initial else identifier + ".snp"
        snapshots = run / "snapshots"
        snapshots.mkdir(exist_ok=True)
        save_snapshot(content or {"application": {"source_run_id": run.name}, "state": np.zeros(2)}, snapshots / filename)
        record = {"filename": filename, "snapshot_id": identifier, "initial": initial,
                  "sha256": hashlib.sha256((snapshots / filename).read_bytes()).hexdigest()}
        path = run / "recording/events.jsonl"
        events = path.read_text().splitlines()
        with path.open("a") as stream:
            stream.write(json.dumps({"sequence": len(events), "kind": "snapshot_registered", "run_id": run.name, **record}) + "\n")
        path = run / "recording/manifest.json"
        manifest = json.loads(path.read_text())
        manifest["recorded_events"] += 1
        path.write_text(json.dumps(manifest))
        return record

    def test_exact_playback_geometry_eyes_and_used_transition(self):
        run = self.run_fixture()
        first = artifacts.playback(run, tick=0)
        sample = artifacts.playback(run, tick=1)
        self.assertEqual(sample["mode"], "playback")
        self.assertEqual(sample["inputs"]["stage"], "used")
        self.assertEqual(sample["inputs"]["eyes"], {"left": True, "right": False})
        self.assertEqual(first["world"]["goal"], [5., 5., .5])
        self.assertEqual(sample["world"]["goal"], [4., 2., .5])
        self.assertEqual(sample["world"]["pose"], [.2, .4, .25])
        self.assertEqual(sample["trace"], [[0., 0.], [.1, .2], [.2, .4]])
        self.assertEqual(sample["transition"]["action"], [1., .25])
        self.assertEqual(sample["transition"]["populations"], [])
        self.assertNotIn("raw_output", sample["transition"])
        from PIL import Image
        pixels = np.array(Image.open(io.BytesIO(base64.b64decode(sample["inputs"]["cam_left"].split(",")[1]))))
        np.testing.assert_array_equal(pixels, np.arange(12, dtype=np.uint8).reshape(2, 2, 3))
        self.assertEqual(sample["state"]["simulation_time"], .04)

    def test_first_request_exhausts_integrity_and_cache_does_not_keep_cameras(self):
        run = self.run_fixture(count=33)
        reader = artifacts.iter_ticks
        with patch.object(artifacts, "iter_ticks", wraps=reader) as read:
            artifacts.playback(run, tick=0)
            artifacts.playback(run, tick=1)
            self.assertEqual(read.call_count, 1)
        cached = next(iter(artifacts._CACHE.values()))[1]
        self.assertNotIn("cam_left", str(cached["episodes"]))
        chunk = run / "recording/chunks/000001.npz"
        chunk.write_bytes(chunk.read_bytes() + b"corruption")
        with self.assertRaisesRegex(ValueError, "checksum"):
            artifacts.playback(run, tick=0)

    def test_terminal_aggregate_mismatch_rejects_before_first_tick(self):
        run = self.run_fixture()
        manifest_path = run / "recording/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["recorded_ticks"] += 1
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            artifacts.playback(run)

    def test_incomplete_missing_geometry_exact_tick_and_symlink_reject(self):
        for run in (self.run_fixture(completed=False), self.run_fixture(world=False)):
            with self.assertRaises(ValueError):
                artifacts.playback(run)
        run = self.run_fixture(start=8)
        self.assertEqual(artifacts.playback(run, tick=8)["trace"][0], [.8, 1.6])
        with self.assertRaisesRegex(ValueError, "does not exist"):
            artifacts.playback(run, tick=0)
        original = run / "recording/events.jsonl"
        moved = run / "outside.jsonl"
        original.rename(moved)
        original.symlink_to(moved)
        with self.assertRaisesRegex(ValueError, "symlink"):
            artifacts.playback(run, tick=8)

    def test_comparison_provenance_precedes_trace_and_preserves_lineage(self):
        parent = uuid.uuid4().hex
        left, right = self.run_fixture(seed=1, parent=parent), self.run_fixture(seed=2, parent=parent)
        result = artifacts.compare_runs(left, right)
        self.assertEqual(result["differences"], [{"field": "seed", "left": 1, "right": 2}])
        self.assertLess(list(result).index("differences"), list(result).index("left"))
        self.assertEqual(result["lineage"], {"shared_parent": parent, "shared_snapshot": "initial"})
        self.assertEqual(result["left"]["traces"][0]["points"][-1], [.2, .4])
        self.assertEqual(result["right"]["recorded_metrics"][0]["reward"], 1.)
        self.assertEqual(result["left"]["worlds"][0]["world"]["pose"], [.2, .4, .25])

    def test_worker_branch_event_and_runtime_are_comparison_provenance(self):
        left, right = self.run_fixture(), self.run_fixture()
        snapshot = uuid.uuid4().hex
        for run, version in ((left, "3.11.10"), (right, "3.11.11")):
            path = run / "recording/events.jsonl"
            events = [json.loads(line) for line in path.read_text().splitlines()]
            events.append({"sequence": len(events), "kind": "branch_created", "parent_snapshot_id": snapshot, "controller_replaced": False})
            events.append({"sequence": len(events), "kind": "diagnostics", "report": {"checks": [
                {"name": "python", "status": "ok", "detail": {"version": version}}]}})
            path.write_text("".join(json.dumps(event) + "\n" for event in events))
            path = run / "recording/manifest.json"
            manifest = json.loads(path.read_text())
            manifest["recorded_events"] = len(events)
            path.write_text(json.dumps(manifest))
        result = artifacts.compare_runs(left, right)
        self.assertEqual(result["lineage"]["shared_snapshot"], snapshot)
        self.assertEqual([difference["field"] for difference in result["differences"]], ["runtime"])
        result["left"]["provenance"]["runtime"][0]["detail"]["version"] = "mutated caller copy"
        self.assertEqual(artifacts.compare_runs(left, right)["left"]["provenance"]["runtime"][0]["detail"]["version"], "3.11.10")

    def test_svg_png_fixed_projection_and_exclusive_exports(self):
        run = self.run_fixture()
        svg = artifacts.export_run(run, self.root / "trace.svg", "svg")
        root = ET.fromstring(svg.read_bytes())
        ns = {"s": "http://www.w3.org/2000/svg"}
        metadata = json.loads(root.find("s:metadata", ns).text)
        line = root.find(".//s:polyline", ns)
        self.assertEqual([[float(x) for x in pair.split(",")] for pair in line.attrib["points"].split()], metadata["traces"][0]["points"])
        self.assertEqual(root.find("s:g", ns).attrib["transform"], "translate(400 400) scale(51.42857142857143 -51.42857142857143)")
        png = artifacts.export_run(run, self.root / "trace.png", "png")
        from PIL import Image
        with Image.open(png) as image:
            png_metadata = json.loads(image.info["palimpsest"])
            self.assertEqual(image.size, (800, 800))
        self.assertEqual(metadata["projection"], png_metadata["projection"])
        self.assertEqual(metadata["traces"], png_metadata["traces"])
        original = svg.read_bytes()
        with self.assertRaises(FileExistsError):
            artifacts.export_run(run, svg, "svg")
        self.assertEqual(svg.read_bytes(), original)

    def test_bundle_whitelist_checksums_snapshots_and_credential_rejection(self):
        from palimpsest.snapshots import save_snapshot
        run = self.run_fixture()
        (run / ".env").write_text("SESSION_TOKEN=never export")
        (run / "stdout.log").write_text("private local log")
        snapshots = run / "snapshots"
        record = self.register_snapshot(run)
        (snapshots / "notes.txt").write_text("private")
        bundle = artifacts.export_run(run, self.root / "run.zip", "bundle")
        with zipfile.ZipFile(bundle) as archive:
            manifest = json.loads(archive.read("bundle-manifest.json"))
            names = set(archive.namelist())
            self.assertEqual(names, {"bundle-manifest.json", "recording/manifest.json", "recording/events.jsonl", "recording/chunks/000000.npz", "snapshots/initial.snp"})
            for entry in manifest["files"]:
                raw = archive.read(entry["path"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])
                self.assertEqual(len(raw), entry["size_bytes"])
        snapshot = snapshots / "initial.snp"
        snapshot.unlink()
        snapshot.symlink_to(run / ".env")
        with self.assertRaisesRegex(ValueError, "symlink"):
            artifacts.export_run(run, self.root / "bad.zip", "bundle")
        self.assertFalse((self.root / "bad.zip").exists())
        snapshot.unlink()
        save_snapshot({"session_token": "secret"}, snapshot)
        event_path = run / "recording/events.jsonl"
        events = [json.loads(line) for line in event_path.read_text().splitlines()]
        events[-1]["sha256"] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        event_path.write_text("".join(json.dumps(event) + "\n" for event in events))
        with self.assertRaisesRegex(ValueError, "credential"):
            artifacts.export_run(run, self.root / "bad.zip", "bundle")

    def test_registered_snapshots_reject_internal_valid_mutation_before_decode(self):
        from palimpsest.snapshots import save_snapshot
        run = self.run_fixture()
        record = self.register_snapshot(run)
        self.assertEqual(artifacts.registered_snapshots(run), [record])
        destination = run / "snapshots" / record["filename"]
        destination.unlink()
        save_snapshot({"state": np.ones(2)}, destination)
        with patch("palimpsest.snapshots.read_snapshot") as decode:
            with self.assertRaisesRegex(ValueError, "snapshot.*hash"):
                artifacts.registered_snapshots(run)
            decode.assert_not_called()
        with self.assertRaisesRegex(ValueError, "snapshot.*hash"):
            artifacts.export_run(run, self.root / "mutated.zip", "bundle")
        self.assertFalse((self.root / "mutated.zip").exists())

    def test_registered_snapshots_registry_orphans_missing_and_duplicate(self):
        from palimpsest.snapshots import save_snapshot
        run = self.run_fixture()
        record = self.register_snapshot(run)
        snapshots = run / "snapshots"
        index = snapshots / "index.json"
        index.write_text(json.dumps({"version": 1, "snapshots": {record["snapshot_id"]: record}}))
        self.assertEqual(artifacts.registered_snapshots(run), [record])
        index.write_text(json.dumps({"version": 1, "snapshots": {record["snapshot_id"]: {**record, "sha256": "0" * 64}}}))
        with self.assertRaisesRegex(ValueError, "registry"):
            artifacts.registered_snapshots(run)
        index.unlink()
        extra = snapshots / (uuid.uuid4().hex + ".snp")
        save_snapshot({"state": np.zeros(2)}, extra)
        with self.assertRaisesRegex(ValueError, "unregistered snapshot"):
            artifacts.export_run(run, self.root / "orphan.zip", "bundle")
        extra.unlink()
        events = artifacts._events(run)
        with self.assertRaisesRegex(ValueError, "duplicate snapshot"):
            artifacts.registered_snapshots(run, events + [events[-1]])
        (snapshots / "initial.snp").unlink()
        with self.assertRaisesRegex(ValueError, "snapshot"):
            artifacts.registered_snapshots(run)

    def test_replay_outer_artifacts_are_bounded_checked_and_whitelisted(self):
        run = self.run_fixture()
        job = run / "job-events.jsonl"
        report = run / "replay-report.json"
        job.write_text('{"type":"job_completed","ordinal":0}\n')
        report.write_text('{"status":"matched","mode":"actions"}')
        bundle = artifacts.export_run(run, self.root / "replay.zip", "bundle")
        with zipfile.ZipFile(bundle) as archive:
            manifest = json.loads(archive.read("bundle-manifest.json"))
            for name in (job.name, report.name):
                entry = next(item for item in manifest["files"] if item["path"] == name)
                self.assertEqual(entry["sha256"], hashlib.sha256(archive.read(name)).hexdigest())
        for raw, message in (('{"status":NaN}', "nonfinite"), ('{"token":"secret"}', "credential")):
            report.write_text(raw)
            with self.assertRaisesRegex(ValueError, message):
                artifacts.export_run(run, self.root / "bad-replay.zip", "bundle")
            self.assertFalse((self.root / "bad-replay.zip").exists())
        report.write_text('{}')
        job.write_text('{"type":"job_completed"}')
        with self.assertRaisesRegex(ValueError, "incomplete"):
            artifacts.export_run(run, self.root / "bad-replay.zip", "bundle")
        job.write_text('{"type":"job_completed"}\n')
        with patch.object(artifacts, "MAX_EVENT", 8):
            with self.assertRaisesRegex(ValueError, "limit"):
                artifacts.export_run(run, self.root / "bad-replay.zip", "bundle")
        report.unlink()
        report.symlink_to(run / "recording/manifest.json")
        with self.assertRaisesRegex(ValueError, "symlink"):
            artifacts.export_run(run, self.root / "bad-replay.zip", "bundle")

    def test_disposable_index_only_immediate_uuid_matching_manifests(self):
        run = self.run_fixture()
        ignored = self.root / "arbitrary"
        ignored.mkdir()
        nested = ignored / str(uuid.uuid4())
        nested.mkdir()
        alias = self.root / str(uuid.uuid4())
        alias.symlink_to(run, target_is_directory=True)
        (self.root / "index.sqlite3").write_bytes(b"corrupt old derived database")
        self.assertEqual([item["run_id"] for item in artifacts.list_runs(self.root)], [run.name])
        with sqlite3.connect(self.root / "index.sqlite3") as database:
            self.assertEqual(database.execute("SELECT run_id FROM runs").fetchall(), [(run.name,)])
        manifest = run / "recording/manifest.json"
        data = json.loads(manifest.read_text())
        data["run_id"] = uuid.uuid4().hex
        manifest.write_text(json.dumps(data))
        self.assertEqual(artifacts.list_runs(self.root), [])

    def test_empty_completed_bundle_and_malformed_intervention(self):
        empty = self.run_fixture(count=0)
        output = artifacts.export_run(empty, self.root / "empty.zip", "bundle")
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(json.loads(archive.read("bundle-manifest.json"))["derived"]["traces"], [])
        with self.assertRaisesRegex(ValueError, "no trajectory"):
            artifacts.export_run(empty, self.root / "empty.svg", "svg")
        run = self.run_fixture()
        events_path = run / "recording/events.jsonl"
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        next(event for event in events if event["kind"] == "intervention")["change"]["new"] = []
        events_path.write_text("".join(json.dumps(event) + "\n" for event in events))
        with self.assertRaisesRegex(ValueError, "invalid recorded intervention"):
            artifacts.playback(run, tick=0)

    def test_run_summary_normalizes_scenario_without_losing_provenance(self):
        run = self.run_fixture()
        path = run / "recording/manifest.json"
        manifest = json.loads(path.read_text())
        profile = {"id": "reproduction", "version": 1, "arena": 7., "n_obstacles": 20}
        manifest["scenario"] = profile
        path.write_text(json.dumps(manifest))
        self.assertEqual(artifacts.list_runs(self.root)[0]["scenario"], "reproduction")
        with sqlite3.connect(self.root / "index.sqlite3") as database:
            stored = json.loads(database.execute("SELECT summary FROM runs").fetchone()[0])
        self.assertEqual(stored["scenario"], "reproduction")
        self.assertEqual(artifacts.compare_runs(run, run)["left"]["provenance"]["scenario"], profile)

    def test_export_budget_checks_before_publication_and_exact_image_bytes(self):
        from palimpsest.storage import StorageLimitError
        run = self.run_fixture()
        for format in ("svg", "png", "bundle"):
            output = self.root / ("bounded." + format)
            class Budget:
                def check(budget, amount, *, path):
                    self.assertEqual(path, output)
                    self.assertFalse(output.exists())
                    budget.amount = amount
            budget = Budget()
            artifacts.export_run(run, output, format, storage_budget=budget)
            if format == "bundle":
                self.assertGreaterEqual(budget.amount, output.stat().st_size)
            else:
                self.assertEqual(budget.amount, output.stat().st_size)
            rejected = self.root / ("rejected." + format)
            original_open = Path.open
            def guarded_open(path, *args, **kwargs):
                self.assertFalse(path == rejected and (args[0] if args else kwargs.get("mode")) == "xb")
                return original_open(path, *args, **kwargs)
            class Reject:
                def check(budget, amount, *, path):
                    raise StorageLimitError("quota exhausted")
            with patch.object(Path, "open", autospec=True, side_effect=guarded_open):
                with self.assertRaisesRegex(StorageLimitError, "quota"):
                    artifacts.export_run(run, rejected, format, storage_budget=Reject())
            self.assertFalse(rejected.exists())

    def test_budgeted_bundle_partial_cleanup_and_exclusivity(self):
        run = self.run_fixture()
        output = self.root / "partial.zip"
        def fail(data, metadata, stream, **kwargs):
            stream.write(b"partial")
            raise OSError("disk full")
        with patch.object(artifacts, "_bundle", side_effect=fail):
            with self.assertRaisesRegex(OSError, "disk full"):
                artifacts.export_run(run, output, "bundle")
        self.assertFalse(output.exists())
        output.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            artifacts.export_run(run, output, "bundle")
        self.assertEqual(output.read_bytes(), b"existing")

    def test_list_runs_optional_index_and_quota_fallback(self):
        from palimpsest.storage import StorageLimitError
        run = self.run_fixture()
        with patch.object(artifacts.tempfile, "mkstemp", side_effect=AssertionError("must not write")):
            self.assertEqual(artifacts.list_runs(self.root, rebuild_index=False)[0]["run_id"], run.name)
        self.assertFalse((self.root / "index.sqlite3").exists())
        class Reject:
            def check(budget, amount, *, path):
                self.assertEqual(amount, 4 * 1024**2)
                raise StorageLimitError("quota exhausted")
        with patch.object(artifacts.tempfile, "mkstemp", side_effect=AssertionError("must preflight")):
            self.assertEqual(artifacts.list_runs(self.root, storage_budget=Reject())[0]["run_id"], run.name)
        self.assertFalse((self.root / "index.sqlite3").exists())
        artifacts.list_runs(self.root)
        with sqlite3.connect(self.root / "index.sqlite3") as database:
            self.assertLessEqual(database.execute("PRAGMA page_count").fetchone()[0], 1024)
        self.assertEqual(list(self.root.glob(".index-*")), [])

    def test_bounded_metadata_and_no_inference_imports(self):
        run = self.run_fixture()
        with patch.object(artifacts, "MAX_EVENTS", 32):
            with self.assertRaisesRegex(ValueError, "oversized"):
                artifacts.playback(run)
        result = subprocess.run([sys.executable, "-c", "import sys; from palimpsest.artifacts import playback; playback(sys.argv[1]); assert 'torch' not in sys.modules; assert 'mujoco' not in sys.modules", str(run)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
