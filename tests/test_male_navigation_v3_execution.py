"""Synthetic trust-boundary tests for the one-shot navigation-v3 training owner."""
import copy
import contextlib
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
owner = importlib.import_module("run_male_navigation_v3_training")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode() + b"\n"


class FakeClock:
    def __init__(self, values=None):
        self.values = iter(values or ())
        self.value = 0.0

    def __call__(self):
        try:
            self.value = next(self.values)
        except StopIteration:
            pass
        return self.value


class NavigationV3ExecutionTests(unittest.TestCase):
    def production_manifest(self):
        path = ROOT / owner.MANIFEST_PATH
        payload = path.read_bytes()
        value = json.loads(payload)
        return path, payload, value

    def test_manifest_freezes_exact_order_command_environment_inputs_and_limits(self):
        path, payload, value = self.production_manifest()
        admitted = owner.admit_manifest(path, value["self_sha256"])
        self.assertEqual(payload, canonical(value))
        self.assertEqual(admitted["attempt"], 2)
        self.assertEqual([row["seed"] for row in admitted["pairs"]], [10, 11, 12])
        self.assertEqual([Path(row["output"]).name for row in admitted["pairs"]],
                         ["seed-10", "seed-11", "seed-12"])
        self.assertEqual(admitted["runtime"], {
            "python": "3.11.15", "cuda_visible_devices": "", "cpu_threads": 1})
        self.assertEqual(admitted["limits"], {
            "pair_internal_seconds": 600, "pair_outer_seconds": 660,
            "all_internal_seconds": 2100, "normal_through_return_seconds": 2150,
            "enclosing_hard_target_seconds": 2160,
            "pair_payload_bytes": 64 * 1024**2,
            "aggregate_bytes": 256 * 1024**2,
            "rss_bytes": 1024**3, "minimum_free_bytes": 1024**3,
            "process_inventory_entries": 256, "log_bytes_per_stream": 1024**2})
        self.assertEqual(admitted["invocation"]["cwd"], str(ROOT))
        self.assertEqual(admitted["invocation"]["runner_argv"][-1],
                         admitted["self_sha256"])
        self.assertEqual(admitted["invocation"]["outer_argv"][:12], [
            "/usr/bin/systemd-run", "--user", "--wait", "--collect",
            f"--working-directory={ROOT}",
            "--unit=palimpsest-m7-navigation-v3-matched-budget-v2",
            "--property=Type=exec", "--property=KillMode=control-group",
            "--property=RuntimeMaxSec=2150s", "--property=TimeoutStopSec=10s",
            "--property=SendSIGKILL=yes", "--property=TimeoutStopFailureMode=kill"])
        self.assertEqual(admitted["invocation"]["outer_argv"][12], "/usr/bin/env")
        self.assertEqual(admitted["invocation"]["environment"], owner.EXACT_ENVIRONMENT)
        self.assertEqual(admitted["immutable_inputs"], owner.protocol()["immutable_inputs"])
        self.assertEqual(admitted["data_manifest_sha256"], owner.DATA_SHA)
        self.assertEqual(admitted["amendment"]["path"], owner.AMENDMENT_PATH)
        self.assertEqual(admitted["prior_failure"], owner.prior_failure())
        self.assertEqual(admitted["prior_failure"]["attempt"], 1)
        self.assertFalse(admitted["prior_failure"]["output_created"])
        self.assertEqual(admitted["qualification_claims"], [])
        self.assertEqual(admitted["held_out_status"], "locked_unopened")

    def test_manifest_rejects_noncanonical_or_any_bound_field_drift(self):
        path, payload, value = self.production_manifest()
        for mutate in (
            lambda row: row["pairs"].reverse(),
            lambda row: row["pairs"][0].update(seed=11),
            lambda row: row["limits"].update(pair_outer_seconds=661),
            lambda row: row["runtime"].update(python="3.11.16"),
            lambda row: row["invocation"]["environment"].update(OMP_NUM_THREADS="2"),
            lambda row: row["immutable_inputs"]["graph"].update(sha256="0" * 64),
            lambda row: row["behavior_sources"].update({"extra.py": "0" * 64}),
            lambda row: row["prior_failure"]["journal"].update(sha256="0" * 64),
            lambda row: row["amendment"].update(size_bytes=0),
        ):
            changed = copy.deepcopy(value)
            mutate(changed)
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                candidate = Path(directory) / "manifest.json"
                candidate.write_bytes(canonical(owner.seal_manifest(changed)))
                with self.assertRaises(ValueError):
                    owner.admit_manifest(candidate, json.loads(candidate.read_text())["self_sha256"])
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "manifest.json"
            candidate.write_bytes(payload + b" ")
            with self.assertRaises(ValueError):
                owner.admit_manifest(candidate, value["self_sha256"])

    def test_main_accepts_real_python_argv_shape_and_checks_interpreter(self):
        path, _, value = self.production_manifest()
        process_argv = value["invocation"]["runner_argv"][1:]
        arguments = process_argv[1:]
        with patch.object(sys, "argv", process_argv), \
                patch.object(sys, "executable", owner.PYTHON), \
                patch.object(owner, "execute") as execute:
            owner.main(arguments)
        execute.assert_called_once_with(path, value["self_sha256"])

        with patch.object(sys, "argv", process_argv), \
                patch.object(sys, "executable", "/wrong/python"), \
                patch.object(owner, "execute") as execute, \
                self.assertRaisesRegex(ValueError, "Runner argv"):
            owner.main(arguments)
        execute.assert_not_called()

    def test_fresh_reservation_is_durable_and_any_stale_path_consumes_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "study"
            receipt = owner.reserve_attempt(output, "a" * 64)
            self.assertTrue((output / "attempt.json").is_file())
            self.assertEqual(receipt["id"], "male-navigation-v3-enclosing-attempt-v2")
            self.assertEqual(receipt["attempt"], 2)
            self.assertEqual(receipt["retry_allowed"], False)
            self.assertEqual(receipt["pairs"], [10, 11, 12])
            for stale in (output, output / "attempt.json", output / "failure.json"):
                with self.subTest(stale=stale), self.assertRaises(FileExistsError):
                    owner.reserve_attempt(output, "a" * 64)

    def test_attempt_two_preflight_requires_both_output_paths_absent(self):
        value = {"output": str(owner.OUTPUT), "immutable_inputs": {}}
        with patch.object(owner, "_lexists",
                          side_effect=lambda path: Path(path) == owner.PRIOR_OUTPUT), \
                self.assertRaisesRegex(FileExistsError, "Consumed invocation"):
            owner.preflight(value)

    def test_pair_receipt_requires_hash_bound_two_model_success_and_complete_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pair = root / "seed-10"
            pair.mkdir()
            (root / "seed-10.attempt.json").write_bytes(canonical({
                "id": "male-navigation-v3-pair-attempt-v1",
                "study_protocol_sha256": owner.PROTOCOL_SHA,
                "training_seed": 10, "output": str(pair.absolute()),
                "models": [{"seed": seed, "arm": arm}
                           for seed in (10, 11, 12) for arm in owner.ARMS],
                "retry_allowed": False, "qualification_claims": []}))
            for name in owner.PAIR_AUXILIARY_FILES:
                (pair / name).write_bytes(canonical({"synthetic": name}))
            models = {}
            for arm in owner.ARMS:
                name = arm + ".pt"
                payload = (arm + "-synthetic-checkpoint").encode()
                (pair / name).write_bytes(payload)
                models[arm] = {
                    "status": "completed", "optimizer_updates": 1440,
                    "real_row_presentations": 46080,
                    "selected_optimizer_update": 1440,
                    "selected_real_row_presentations": 46080,
                    "graph_variant": "original",
                    "schedule_sha256": hashlib.sha256(
                        (pair / (arm + "-schedule.json")).read_bytes()).hexdigest(),
                    "recorded_development": {"ticks": 1228},
                    "checkpoint": {"path": name, "size_bytes": len(payload),
                                   "sha256": hashlib.sha256(payload).hexdigest()}}
            report = {
                "status": "completed-navigation-v3-training", "training_completed": True,
                "training_attempted": True,
                "training_seed": 10, "study_protocol_sha256": owner.PROTOCOL_SHA,
                "data_manifest_sha256": owner.DATA_SHA, "models": models,
                "protocol_sha256": hashlib.sha256(
                    (pair / "protocol.json").read_bytes()).hexdigest(),
                "held_out_status": "locked_unopened", "held_out_used_for_selection": False,
                "qualification_claims": []}
            report_payload = canonical(report)
            (pair / "report.json").write_bytes(report_payload)
            (pair / "publication.json").write_bytes(canonical({
                "id": "male-navigation-v3-publication-v1", "status": "durably-published",
                "study_protocol_sha256": owner.PROTOCOL_SHA,
                "report_sha256": hashlib.sha256(report_payload).hexdigest(),
                "report_size_bytes": len(report_payload), "qualification_claims": []}))
            admitted = owner.admit_pair(pair, 10)
            self.assertEqual(len(admitted["models"]), 2)
            self.assertEqual(set(admitted["inventory"]), set(owner.PAIR_FILES))
            (pair / "unexpected").write_bytes(b"x")
            with self.assertRaises(ValueError):
                owner.admit_pair(pair, 10)

    def test_orchestration_is_ordered_and_first_failure_leaves_later_pairs_not_started(self):
        rows = [{"seed": seed, "argv": [str(seed)], "output": f"/tmp/seed-{seed}"}
                for seed in (10, 11, 12)]
        calls = []

        def runner(pair, deadline):
            calls.append((pair["seed"], deadline))
            return {"status": "completed" if pair["seed"] == 10 else "failed",
                    "returncode": 0 if pair["seed"] == 10 else 7,
                    "identity": {"pid": pair["seed"], "start_ticks": 1,
                                 "process_group": pair["seed"]},
                    "observed": [], "survivors": []}

        report = owner.orchestrate(rows, 0.0, runner,
                                   lambda pair, seed: {"models": [seed * 2, seed * 2 + 1]},
                                   FakeClock([0, 0, 10, 10, 20, 20]))
        self.assertEqual([seed for seed, _ in calls], [10, 11])
        self.assertEqual(report["pairs"]["10"]["status"], "completed")
        self.assertEqual(report["pairs"]["11"]["status"], "failed")
        self.assertEqual(report["pairs"]["12"]["status"], "not_started")
        self.assertFalse(report["training_completed"])

    def test_global_and_pair_boundaries_fail_closed(self):
        rows = [{"seed": seed, "argv": [str(seed)], "output": f"/tmp/seed-{seed}"}
                for seed in (10, 11, 12)]
        exact = owner.orchestrate(rows, 0.0,
            lambda pair, deadline: {"status": "completed", "returncode": 0,
                                    "identity": {"pid": pair["seed"], "start_ticks": 1,
                                                 "process_group": pair["seed"]},
                                    "observed": [], "survivors": [],
                                    "elapsed_seconds": 660},
            lambda pair, seed: {"models": [seed * 2, seed * 2 + 1]},
            FakeClock([0, 660, 660, 1320, 1320, 1980, 2100]))
        self.assertTrue(exact["training_completed"])
        late = owner.orchestrate(rows, 0.0,
            lambda pair, deadline: {"status": "completed", "returncode": 0,
                                    "identity": {}, "observed": [], "survivors": []},
            lambda pair, seed: {"models": []}, FakeClock([1441]))
        self.assertEqual(late["pairs"]["10"]["status"], "not_started")
        self.assertEqual(late["failure"]["type"], "TimeoutError")

    def test_process_identity_inventory_rejects_escape_reuse_and_overflow(self):
        identity = {"pid": 50, "ppid": 40, "group": 50, "start_ticks": 100,
                    "command": "python trainer"}
        observed = owner.admit_process_observation(identity, 40, [identity], {}, 256)
        self.assertEqual(observed[(50, 100)]["group"], 50)
        for changed in (
            {**identity, "group": 51}, {**identity, "ppid": 41},
            {**identity, "start_ticks": 101},
        ):
            with self.assertRaises(ValueError):
                owner.admit_process_observation(identity, 40, [changed], {}, 256)
        with self.assertRaises(ValueError):
            owner.admit_process_observation(identity, 40,
                [{"pid": n, "ppid": 50, "group": 50, "start_ticks": n,
                  "command": "child"} for n in range(257)], {}, 256)

    def test_leader_exit_never_hides_live_group_descendant_and_forces_drain(self):
        identity = {"pid": 50, "ppid": 40, "group": 50, "start_ticks": 100,
                    "command": "python trainer"}
        descendant = {"pid": 51, "ppid": 1, "group": 50, "start_ticks": 101,
                      "state": "S", "rss_bytes": 10, "command": "worker"}
        rows = iter(([descendant], [descendant], []))
        sent = []
        result = owner.drain_process_group(
            identity, 10.0, {}, group_reader=lambda group: next(rows),
            clock=FakeClock([0.0, 4.0, 4.0]), sleep=lambda _: None,
            kill=lambda group, number: sent.append((group, number)))
        self.assertTrue(result["drained"])
        self.assertTrue(result["forced"])
        self.assertEqual([number for _, number in sent], [signal.SIGTERM, signal.SIGKILL])
        self.assertIn((51, 101), result["known"])

    def test_spawn_defers_external_term_until_pid_start_and_group_are_owned(self):
        events = []
        process = type("Process", (), {"pid": 50, "poll": lambda self: None})()
        prior = {signal.SIGINT: object(), signal.SIGTERM: object()}
        handlers = dict(prior)

        def install(number, handler):
            previous = handlers[number]
            handlers[number] = handler
            events.append(("handler", number, handler))
            return previous

        def popen(*args, **kwargs):
            events.append(("popen", kwargs["start_new_session"]))
            handlers[signal.SIGTERM](signal.SIGTERM, None)
            return process

        def identity(pid):
            events.append(("identity", pid))
            return {"pid": 50, "ppid": os.getpid(), "group": 50,
                    "start_ticks": 100, "argv": ["trainer"], "command": "trainer"}

        cleaned = []
        def cleanup(group):
            events.append(("cleanup", group))
            cleaned.append(group)
        result, owned, handoff = owner.spawn_contained(
            ["trainer"], ROOT, {}, None, None, popen=popen,
            identity_reader=identity, install_handler=install,
            cleanup=cleanup)
        self.assertIs(result, process)
        self.assertEqual(owned["start_ticks"], 100)
        self.assertEqual(cleaned, [])
        with self.assertRaises(InterruptedError):
            owner.finish_spawn_handoff(result, handoff)
        self.assertEqual(cleaned, [50])
        self.assertIs(handlers[signal.SIGINT], prior[signal.SIGINT])
        self.assertIs(handlers[signal.SIGTERM], prior[signal.SIGTERM])
        self.assertEqual([row[0] for row in events],
                         ["handler", "handler", "popen", "identity", "cleanup",
                          "handler", "handler"])

    def test_spawned_exec_has_unblocked_term_without_preexec_in_threads(self):
        command = [sys.executable, "-B", "-c",
                   "import signal,time; print(int(signal.SIGTERM in "
                   "signal.pthread_sigmask(signal.SIG_BLOCK, set())), flush=True); time.sleep(.2)"]
        process, identity, handoff = owner.spawn_contained(
            command, ROOT, dict(os.environ), subprocess.PIPE, subprocess.PIPE)
        owner.finish_spawn_handoff(process, handoff)
        stdout, stderr = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, stderr.decode(errors="replace"))
        self.assertEqual(stdout.strip(), b"0")
        self.assertEqual(identity["group"], process.pid)

    def test_signal_after_spawn_return_waits_for_caller_owned_handoff(self):
        process = type("Process", (), {"pid": 50, "poll": lambda self: None})()
        cleaned = []
        caller = {"process": None, "identity": None}
        def interrupted(number, frame):
            raise InterruptedError("prior handler ran before caller ownership")
        handlers = {signal.SIGINT: interrupted, signal.SIGTERM: interrupted}
        def install(number, handler):
            previous = handlers[number]
            handlers[number] = handler
            return previous
        def identity(pid):
            return {"pid": 50, "ppid": os.getpid(), "group": 50,
                    "start_ticks": 100, "argv": ["trainer"], "command": "trainer"}

        try:
            spawned = owner.spawn_contained(
                ["trainer"], ROOT, {}, None, None, popen=lambda *a, **k: process,
                identity_reader=identity, install_handler=install,
                cleanup=lambda group: cleaned.append(group))
            handlers[signal.SIGTERM](signal.SIGTERM, None)
            caller["process"], caller["identity"], handoff = spawned
            owner.finish_spawn_handoff(caller["process"], handoff)
        except InterruptedError:
            pass
        self.assertIs(caller["process"], process)
        self.assertEqual(caller["identity"]["start_ticks"], 100)
        self.assertEqual(cleaned, [50])
        self.assertIs(handlers[signal.SIGINT], interrupted)
        self.assertIs(handlers[signal.SIGTERM], interrupted)

    def test_handoff_attempts_every_handler_restore_before_failing_closed(self):
        process = type("Process", (), {"pid": 50, "poll": lambda self: None})()
        prior = {signal.SIGINT: object(), signal.SIGTERM: object()}
        handlers, restores, cleaned = dict(prior), [], []
        def install(number, handler):
            previous = handlers[number]
            if handler is prior[number]:
                restores.append(number)
                if number == signal.SIGTERM:
                    raise RuntimeError("synthetic handler restore failure")
            handlers[number] = handler
            return previous
        def identity(pid):
            return {"pid": 50, "ppid": os.getpid(), "group": 50,
                    "start_ticks": 100, "argv": ["trainer"], "command": "trainer"}

        result, _, handoff = owner.spawn_contained(
            ["trainer"], ROOT, {}, None, None, popen=lambda *a, **k: process,
            identity_reader=identity, install_handler=install,
            cleanup=lambda group: cleaned.append(group))
        with self.assertRaisesRegex(RuntimeError, "restore failure"):
            owner.finish_spawn_handoff(result, handoff)
        self.assertEqual(set(restores), {signal.SIGINT, signal.SIGTERM})
        self.assertEqual(cleaned, [50])

    def test_leader_exit_before_identity_drains_forked_group_before_error(self):
        command = [sys.executable, "-B", "-c",
                   "import os,time; child=os.fork(); os._exit(0) if child else time.sleep(30)"]
        created = []
        def popen(*args, **kwargs):
            process = subprocess.Popen(*args, **kwargs)
            created.append(process)
            return process
        try:
            with self.assertRaises(ValueError):
                owner.spawn_contained(
                    command, ROOT, dict(os.environ), subprocess.DEVNULL,
                    subprocess.DEVNULL, popen=popen, identity_reader=lambda pid: None)
            self.assertEqual(len(created), 1)
            self.assertEqual(owner.process_group_members(created[0].pid), [])
        finally:
            if created:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(created[0].pid, signal.SIGKILL)

    def test_execute_reserves_before_child_and_retains_crash_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "aggregate"
            value = {"self_sha256": "a" * 64, "output": str(output),
                     "invocation": {"cwd": str(ROOT)},
                     "behavior_sources": {},
                     "pairs": [{"seed": seed, "output": str(output / f"seed-{seed}"),
                                "argv": [str(seed)]} for seed in (10, 11, 12)]}
            calls = []

            def run(pair, deadline):
                self.assertTrue((output / "attempt.json").is_file())
                calls.append(pair["seed"])
                raise RuntimeError("synthetic crash")

            with (patch.object(owner, "admit_manifest", return_value=value),
                  patch.object(owner, "preflight", return_value=None),
                  patch.object(owner, "source_identity", return_value={}),
                  patch.object(owner, "runtime_identity", return_value={}),
                  patch.object(owner, "check_resources", return_value=None),
                  patch.object(owner, "supervise_pair", side_effect=run)):
                with self.assertRaisesRegex(RuntimeError, "synthetic crash"):
                    owner.execute(Path("synthetic"), "a" * 64)
            self.assertEqual(calls, [10])
            failure = json.loads((output / "failure.json").read_text())
            self.assertEqual(failure["pairs"]["10"]["status"], "failed")
            self.assertEqual(failure["pairs"]["11"]["status"], "not_started")
            with self.assertRaises(FileExistsError):
                owner.reserve_attempt(output, "a" * 64)

    def test_aggregate_success_needs_durable_receipt_and_all_six_models(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "aggregate"
            digest = "a" * 64
            owner.reserve_attempt(output, digest)
            evidence = {str(seed): {
                "seed": seed,
                "models": [{"seed": seed, "arm": arm} for arm in owner.ARMS],
                "report_sha256": str(seed) * 64,
                "publication_sha256": str(seed + 1) * 64,
                "inventory": {"report.json": {"sha256": str(seed) * 64}}}
                for seed in (10, 11, 12)}
            report = {
                "status": "completed-navigation-v3-enclosing-training",
                "training_completed": True, "execution_manifest_sha256": digest,
                "pairs": {str(seed): {"status": "completed", "evidence": evidence[str(seed)]}
                          for seed in (10, 11, 12)},
                "models": [{"seed": seed, "arm": arm}
                           for seed in (10, 11, 12) for arm in owner.ARMS],
                "qualification_claims": [], "held_out_status": "locked_unopened"}
            owner._publish_success(output, report, float("inf"))
            calls = []
            def admit(path, seed):
                calls.append((Path(path).name, seed))
                return copy.deepcopy(evidence[str(seed)])
            with patch.object(owner, "admit_pair", side_effect=admit):
                self.assertTrue(owner.success_admitted(output, digest))
            self.assertEqual(calls, [("seed-10", 10), ("seed-11", 11), ("seed-12", 12)])
            changed = copy.deepcopy(evidence["11"])
            changed["publication_sha256"] = "f" * 64
            with patch.object(owner, "admit_pair",
                              side_effect=[evidence["10"], changed, evidence["12"]]):
                self.assertFalse(owner.success_admitted(output, digest))
            (output / "failure.json").write_bytes(canonical({"status": "failed"}))
            self.assertFalse(owner.success_admitted(output, digest))

    def test_normal_deadline_is_rechecked_after_final_publication_fsync(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = {"execution_manifest_sha256": "a" * 64, "models": [0] * 6}
            with (patch.object(owner.time, "monotonic", side_effect=[0.0, 0.5, 1.1]),
                  self.assertRaises(TimeoutError)):
                owner._publish_success(output, report, 1.0)

    def test_static_source_roster_closes_lazy_navigation_imports(self):
        roster = owner.static_source_roster()
        required = {
            "scripts/collect_male_navigation_v2.py",
            "scripts/collect_male_navigation.py",
            "scripts/verify_body_adaptation.py",
            "src/palimpsest/body_profile.py",
            "src/palimpsest/snapshots.py",
        }
        self.assertTrue(required <= set(roster))
        _, _, manifest = self.production_manifest()
        self.assertEqual(set(manifest["behavior_sources"]), set(roster))

    def test_secure_reads_reject_hardlinks_and_path_rebinding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original, linked = root / "original", root / "linked"
            original.write_bytes(b"original")
            os.link(original, linked)
            with self.assertRaises(ValueError):
                owner._read(linked)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target, replacement = root / "target", root / "replacement"
            target.write_bytes(b"before")
            replacement.write_bytes(b"after")
            real_open = os.open
            def racing_open(path, flags, *args, **kwargs):
                descriptor = real_open(path, flags, *args, **kwargs)
                if Path(path) == target:
                    os.replace(replacement, target)
                return descriptor
            with patch.object(owner.os, "open", side_effect=racing_open):
                with self.assertRaises(ValueError):
                    owner._read(target)

    def test_exclusive_final_publication_never_overwrites_raced_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pending, final = root / "report.pending", root / "report.json"
            pending.write_bytes(b"ours")
            final.write_bytes(b"racer")
            with self.assertRaises(FileExistsError):
                owner._exclusive_publish(pending, final)
            self.assertEqual(final.read_bytes(), b"racer")

    def test_source_drift_after_all_pairs_retains_failure_and_no_success(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "aggregate"
            value = {"self_sha256": "a" * 64, "output": str(output),
                     "invocation": {"cwd": str(ROOT)}, "behavior_sources": {},
                     "pairs": [{"seed": seed, "output": str(output / f"seed-{seed}"),
                                "argv": [str(seed)]} for seed in (10, 11, 12)]}
            supervision = {"status": "completed", "returncode": 0,
                           "identity": {"pid": 1}, "observed": [], "survivors": [],
                           "elapsed_seconds": 1}
            evidence = lambda path, seed: {
                "models": [{"seed": seed, "arm": arm} for arm in owner.ARMS],
                "inventory": {"report.json": {"sha256": str(seed)}}}
            sources = [{}, ValueError("synthetic final source drift")]

            def source(expected=None):
                item = sources.pop(0)
                if isinstance(item, BaseException):
                    raise item
                return item

            with (patch.object(owner, "admit_manifest", return_value=value),
                  patch.object(owner, "preflight", return_value=None),
                  patch.object(owner, "source_identity", side_effect=source),
                  patch.object(owner, "runtime_identity", return_value={}),
                  patch.object(owner, "check_resources", return_value=None),
                  patch.object(owner, "supervise_pair", return_value=supervision),
                  patch.object(owner, "admit_pair", side_effect=evidence)):
                with self.assertRaisesRegex(ValueError, "source drift"):
                    owner.execute(Path("synthetic"), "a" * 64)
            self.assertTrue((output / "failure.json").is_file())
            self.assertFalse((output / "publication.json").exists())


if __name__ == "__main__":
    unittest.main()
