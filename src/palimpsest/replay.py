"""Sequential executable replay with recorded evidence and first-divergence reports."""
from __future__ import annotations

from collections import deque
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import uuid

from .artifacts import _events, _fingerprint, _id, _load, _safe_path
from .records import iter_ticks
from .male_policy import CONTROLLERS as MALE_CONTROLLERS, validate_identity

ATOL = RTOL = 1e-6
_RUNTIME = tuple(f"src/palimpsest/{name}.py" for name in
                 ("engine", "profiles", "interventions", "flynn", "snapshots", "records", "evaluate", "assets", "doctor",
                  "memory", "memory_task", "memory_world"))
_MALE_RUNTIME = ('src/palimpsest/male_policy.py', 'src/palimpsest/male_model.py')
_EVENTS = {"command_received", "command_applied", "command_rejected", "episode_started",
           "episode_finished", "intervention", "eyes_changed", "browser_disconnected", "runtime_failure",
           "memory_world_changed", "memory_sensed", "memory_decision", "memory_cue", "memory_inspected"}
_IGNORED_EVENT_KEYS = {"sequence", "run_id", "received_run_id", "applied_run_id"}
_PHYSICAL = {"cam_left", "cam_right", "raw_cam_left", "raw_cam_right", "sensors", "action",
             "control", "pose", "next_pose", "reward", "simulation_time", "eyes", "revision"}
_LATENCIES = {"latency", "step_latency"}


class Divergence(Exception):
    def __init__(self, detail):
        self.detail = detail
        super().__init__(detail["reason"])


def _difference(field, reason, **details):
    def finite(value):
        if isinstance(value, dict):
            return {key: finite(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [finite(item) for item in value]
        if isinstance(value, complex) or isinstance(value, float) and not math.isfinite(value):
            return str(value)
        return value
    raise Divergence({"field": field, "reason": reason, **finite(details)})


def _same_json(expected, actual, field="event"):
    """Compare recorded lifecycle evidence, ignoring destination stream identities."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        keys = set(expected) - _IGNORED_EVENT_KEYS
        if keys != set(actual) - _IGNORED_EVENT_KEYS:
            _difference(field, "event keys differ")
        for key in sorted(keys):
            _same_json(expected[key], actual[key], field + "." + key)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            _difference(field, "event list lengths differ")
        for index, (left, right) in enumerate(zip(expected, actual)):
            _same_json(left, right, f"{field}[{index}]")
    elif type(expected) is float and type(actual) in (float, int):
        if not math.isfinite(actual) or not math.isclose(expected, actual, abs_tol=ATOL, rel_tol=RTOL):
            _difference(field, "floating event values differ", expected=expected, actual=actual)
    elif type(expected) is not type(actual) or expected != actual:
        _difference(field, "event values differ", expected=expected, actual=actual)


def _same_tick(expected, actual, mode, global_tick):
    import numpy as np
    context = {"episode": actual["episode"], "tick": actual["tick"], "global_tick": global_tick}
    if (expected["episode"], expected["tick"]) != (actual["episode"], actual["tick"]):
        _difference("tick", "recorded episode/tick differs", **context)
    fields = (_PHYSICAL if mode == "actions" else set(expected) - _LATENCIES - {"episode", "tick"})
    actual_fields = set(actual) - _LATENCIES - {"episode", "tick"}
    if not fields <= set(expected) or not fields <= actual_fields or (mode == "policy" and fields != actual_fields):
        _difference("fields", "recorded tick fields differ", expected=sorted(fields), actual=sorted(actual_fields), **context)
    for field in sorted(fields):
        left, right = np.asarray(expected[field]), np.asarray(actual[field])
        if left.shape != right.shape or left.dtype != right.dtype:
            _difference(field, "array shape or dtype differs", expected_shape=list(left.shape), actual_shape=list(right.shape),
                        expected_dtype=str(left.dtype), actual_dtype=str(right.dtype), **context)
        equal = np.isclose(left, right, atol=ATOL, rtol=RTOL, equal_nan=False) if left.dtype.kind == "f" else left == right
        if not bool(np.all(equal)):
            bad = np.argwhere(~equal)
            index = tuple(bad[0]) if bad.size else ()
            detail = {"index": list(map(int, index)), "expected": left[index].item(), "actual": right[index].item()}
            if left.dtype.kind == "f" and np.isfinite(left).all() and np.isfinite(right).all():
                detail["max_abs_error"] = float(np.max(np.abs(left.astype(np.float64) - right.astype(np.float64))))
            _difference(field, "numeric replay divergence", **context, **detail)


def _same_event(expected, actual):
    try:
        _same_json(expected, actual)
    except Divergence as error:
        error.detail.update(source_sequence=expected["sequence"], episode=expected.get("episode"),
                            tick=expected.get("episode_step"), global_tick=expected.get("tick"))
        raise


def _initial_snapshot(data):
    from .artifacts import registered_snapshots
    from .snapshots import read_snapshot
    entries = [item for item in registered_snapshots(data["run"], data["events"]) if item["initial"]]
    if len(entries) != 1 or entries[0]["filename"] != "initial.snp":
        raise ValueError("replay requires exactly one registered initial snapshot")
    entry = entries[0]
    snapshot = read_snapshot(data["run"] / "snapshots" / entry["filename"])
    application = snapshot.get("application")
    if not isinstance(application, dict) or _id(application.get("source_run_id")) != _id(data["manifest"]["run_id"]):
        raise ValueError("initial snapshot belongs to a different run")
    prefix = application.get("event_prefix")
    if not isinstance(prefix, dict) or set(prefix) != {"sha256", "size_bytes", "event_count"} or any(type(prefix.get(key)) is not int or prefix[key] < 0 for key in ("size_bytes", "event_count")):
        raise ValueError("snapshot lacks a durable event prefix")
    path = data["run"] / "recording/events.jsonl"
    if prefix["size_bytes"] > path.stat().st_size or prefix["event_count"] > len(data["events"]):
        raise ValueError("snapshot event prefix exceeds source history")
    with path.open("rb") as source:
        raw = source.read(prefix["size_bytes"])
    if hashlib.sha256(raw).hexdigest() != prefix["sha256"] or raw.count(b"\n") != prefix["event_count"] or raw and not raw.endswith(b"\n"):
        raise ValueError("snapshot event prefix differs from source history")
    registrations = [event for event in data["events"] if event["kind"] == "snapshot_registered" and event.get("snapshot_id") == entry["snapshot_id"]]
    if len(registrations) != 1 or registrations[0]["sequence"] < prefix["event_count"]:
        raise ValueError("initial snapshot registration precedes its capture")
    return snapshot, entry, data["events"][prefix["event_count"]:]


def _compatible(source, destination, controller=None):
    runtime = _RUNTIME + (_MALE_RUNTIME if controller in MALE_CONTROLLERS else ())
    def environment(events):
        found = [event for event in events if event["kind"] == "environment"]
        if len(found) != 1:
            raise ValueError("replay requires one recorded environment provenance event")
        event = found[0]
        hashes = event.get("source_sha256")
        if not isinstance(hashes, dict) or any(key not in hashes for key in runtime):
            raise ValueError("replay source lacks relevant runtime source hashes")
        return {"upstream_commit": event.get("upstream_commit"), "lock_sha256": event.get("lock_sha256"),
                "source_sha256": {key: hashes[key] for key in runtime}}
    left, right = environment(source), environment(destination)
    if left != right:
        raise ValueError("replay runtime provenance differs (upstream, lock or relevant runtime source)")


def _register_initial(engine, destination, storage_budget=None, preflight_bytes=0):
    from .snapshots import capture, save_snapshot
    path = destination / "snapshots"
    path.mkdir(exist_ok=True)
    snapshot = capture(engine.env, engine.observation, policy=engine.policy, teacher=engine.teacher,
                       application=engine.application_state())
    filename = path / "initial.snp"
    if storage_budget is not None:
        storage_budget.check_count("snapshots", 0)
    save_snapshot(snapshot, filename, storage_budget=storage_budget,
                  preflight_bytes=preflight_bytes if storage_budget is not None else 0)
    with filename.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    identifier = uuid.uuid4().hex
    registry = {identifier: {"snapshot_id": identifier, "filename": "initial.snp", "initial": True,
        "revision": engine.revision, "episode": engine.episode, "tick": engine.episode_step, "sha256": digest,
        "config": {"scenario": engine.scenario, "texture": engine.texture, "controller": engine.controller,
                   "device": engine.writer.manifest["requested_device"], "seed": engine.seed}}}
    if 'policy_identity' in engine.writer.manifest:
        registry[identifier]['config']['policy_identity'] = copy.deepcopy(engine.writer.manifest['policy_identity'])
    payload = (json.dumps({"version": 1, "snapshots": registry}, allow_nan=False) + "\n").encode()
    if storage_budget is not None:
        storage_budget.check(len(payload), path=path / "index.json")
    with (path / "index.json").open("xb") as stream:
        stream.write(payload)
    engine.writer.event("snapshot_registered", run_id=engine.run_id, snapshot_id=identifier, filename="initial.snp",
                        initial=True, sha256=digest, episode=engine.episode, tick=engine.episode_step, revision=engine.revision)
    return identifier


def _write_report(destination, report, storage_budget=None):
    import os
    path = destination / "replay-report.json"
    payload = json.dumps(report, allow_nan=False, indent=2) + "\n"
    temporary = destination / ".replay-report.tmp"
    if len(payload.encode()) > 1024**2:
        raise RuntimeError("Replay report exceeds reserved 1 MiB")
    if storage_budget is not None:
        from .storage import StorageBudget
        StorageBudget(storage_budget.roots, storage_budget.limits).check(len(payload.encode()), path=temporary)
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Atomic publication, never replace another report.
    finally:
        temporary.unlink(missing_ok=True)


def replay_run(source_run_path, destination_run_path, *, mode, repo_root, asset_root, progress=None,
               storage_budget=None):
    """Replay a completed source in a fresh owner process supplied by the caller.

    Action replay restores the same controller for snapshot compatibility, then
    bypasses inference. Policy replay executes it. Neither is recorded playback.
    ``progress`` may block at boundaries or raise InterruptedError to cancel.
    """
    if mode not in {"actions", "policy"}:
        raise ValueError("replay mode must be actions or policy")
    source, destination = _safe_path(source_run_path), _safe_path(destination_run_path)
    _id(source.name)
    _id(destination.name)
    if not destination.is_dir() or source == destination or (destination / "recording").exists() or (destination / "replay-report.json").exists():
        raise ValueError("replay destination must be a fresh UUID run directory")
    report = {"schema_version": 1, "source_run_id": source.name, "run_id": destination.name, "mode": mode,
              "status": "running", "compared_ticks": 0, "compared_events": 0, "first_divergence": None,
              "comparison": {"float_atol": ATOL, "float_rtol": RTOL, "integer_and_camera_exact": True,
                             "excluded": sorted(_LATENCIES | ({"encoded_input", "raw_output", "population_stats"} if mode == "actions" else set())),
                             "fields": sorted(_PHYSICAL) if mode == "actions" else "all recorded fields except wall latencies",
                             "runtime_source_keys": list(_RUNTIME),
                             "upstream_and_lock_exact": True, "snapshot_identity_exact": True},
              "controller_reexecuted": mode == "policy", "inference_executed": False, "errors": []}
    engine = None
    generated = deque()
    close_events = []
    actual_tick = None
    expected_tick = None
    tick_iterator = None
    def notify(stage):
        if progress is not None:
            if engine is None or stage == "loading":
                progress(stage)
            else:
                progress(stage, state=engine.public_state())
    try:
        notify("loading")
        data = _load(source)
        snapshot, registration, events = _initial_snapshot(data)
        notify("loading")
        manifest = data["manifest"]
        male = manifest.get('controller') in MALE_CONTROLLERS
        identity = validate_identity(manifest.get('policy_identity'), manifest['controller']) if male else None
        report["inference_executed"] = mode == "policy" and (male or manifest.get("controller") == "flynn")
        if male:
            report['comparison']['runtime_source_keys'] = list(_RUNTIME + _MALE_RUNTIME)
        report["source_snapshot_id"] = registration["snapshot_id"]
        report["source_snapshot_sha256"] = registration["sha256"]
        profile = manifest.get("scenario")
        if not isinstance(profile, dict) or not isinstance(profile.get("id"), str):
            raise ValueError("replay requires a recorded scenario configuration")
        from .engine import Engine
        engine = Engine.open(Path(repo_root), Path(asset_root), destination / "recording",
            controller=manifest["controller"], device=manifest["requested_device"], seed=manifest["seed"],
            scenario=profile["id"], texture=manifest["texture"], run_id=destination.name,
            storage_budget=storage_budget, expected_policy_identity=identity)
        _compatible(data["events"], _events(destination), manifest['controller'])
        engine.restore_branch(snapshot)
        del snapshot
        engine.writer.manifest.update(execution_mode=mode, inference_executed=report["inference_executed"],
            controller_reexecuted=mode == "policy", replay_mode=mode,
            replay_source_run_id=manifest["run_id"], source_snapshot_id=registration["snapshot_id"])
        if mode == "actions":
            engine.writer.manifest["population_names"] = []
        engine.writer.event("replay_started", run_id=engine.run_id, mode=mode, source_run_id=manifest["run_id"],
                            source_snapshot_id=registration["snapshot_id"], comparison=report["comparison"])
        estimate = sum(path.stat().st_size for path in data["paths"]) + 1024**2
        report["storage_preflight"] = {"source_ticks": manifest.get("recorded_ticks"),
            "recording_bytes_estimate": estimate, "scope": "source recording bytes plus overhead and actual initial snapshot"}
        report["initial_snapshot_id"] = _register_initial(engine, destination, storage_budget, estimate)
        original_tick, original_event = engine.writer.tick, engine.writer.event
        def collect_tick(episode, tick, **arrays):
            nonlocal actual_tick
            original_tick(episode, tick, **arrays)
            actual_tick = {"episode": episode, "tick": tick, **{key: value.copy() for key, value in arrays.items()}}
        def collect_event(kind, **values):
            original_event(kind, **values)
            if kind in _EVENTS:
                if len(generated) >= 512:
                    raise RuntimeError("replay event comparison queue exceeded bound")
                generated.append({"kind": kind, **copy.deepcopy(values)})
        engine.writer.tick, engine.writer.event = collect_tick, collect_event
        tick_iterator = iter(iter_ticks(source / "recording"))
        expected_tick = next(tick_iterator, None)
        if expected_tick is not None and (expected_tick["episode"], expected_tick["tick"]) != (engine.episode, engine.episode_step):
            raise ValueError("initial snapshot is not the source recording's first control boundary")
        notify("ready")
        def advance():
            nonlocal actual_tick, expected_tick
            notify("step")
            actual_tick = None
            before = engine.total_tick
            override = expected_tick["action"] if mode == "actions" and expected_tick is not None else None
            engine.advance(action_override=override)
            notify("step")
            if engine.phase == "failed":
                raise RuntimeError("replay engine failed: " + json.dumps(engine.last_outcome, allow_nan=False))
            if actual_tick is not None:
                if expected_tick is None:
                    _difference("tick", "replay produced an unrecorded extra control tick", global_tick=before)
                _same_tick(expected_tick, actual_tick, mode, before)
                report["compared_ticks"] += 1
                expected_tick = next(tick_iterator, None)
            elif engine.total_tick != before:
                raise RuntimeError("engine advanced without a recorded tick")
            return engine.total_tick != before
        for event in events:
            kind = event["kind"]
            if kind not in _EVENTS:
                continue
            tick = event.get("tick")
            if type(tick) is not int or tick < 0:
                raise ValueError("replay event lacks global control tick")
            if close_events:
                if kind == "command_rejected" and event.get("result", {}).get("reason") == "engine closed before application":
                    close_events.append(event)
                    continue
                raise ValueError("source lifecycle events follow engine close")
            while engine.total_tick < tick:
                if not advance():
                    _difference("event.tick", "source event requires an unavailable control tick", expected=tick, actual=engine.total_tick)
            if not generated:
                if kind == "command_received":
                    engine.submit(event["command"])
                elif kind == "browser_disconnected" or kind == "command_rejected" and event.get("result", {}).get("reason") == "browser disconnected":
                    engine.pause_for_disconnect()
                elif kind == "command_rejected" and event.get("result", {}).get("reason") == "engine closed before application":
                    close_events.append(event)
                    continue
                elif kind == "runtime_failure":
                    raise ValueError("replay cannot reconstruct an unrecorded failed controller invocation")
                else:
                    advance()
            if not generated:
                _difference("event", "source event was not produced", expected_kind=kind)
            actual = generated.popleft()
            _same_event(event, actual)
            report["compared_events"] += 1
        while expected_tick is not None:
            if not advance():
                _difference("tick", "recorded tick has no runnable source command", episode=expected_tick["episode"], tick=expected_tick["tick"])
        if generated:
            _difference("event", "replay produced an extra lifecycle event", actual_kind=generated[0]["kind"])
        _same_json({"total_tick": manifest.get("total_tick"), "phase": manifest.get("final_phase"),
                    "metrics": manifest.get("metrics"), "last_outcome": manifest.get("last_outcome")},
                   {"total_tick": engine.total_tick, "phase": engine.phase, "metrics": engine.metrics,
                    "last_outcome": engine.last_outcome}, "final_state")
        if _fingerprint(data["paths"]) != data["fingerprint"]:
            raise ValueError("source recording changed during replay")
        report["status"] = "passed"
    except InterruptedError as error:
        report["status"] = "cancelled"
        report["errors"].append({"type": type(error).__name__, "message": str(error)[:4096]})
    except Divergence as error:
        report["status"] = "diverged"
        report["first_divergence"] = error.detail
    except Exception as error:
        report["status"] = "failed"
        report["errors"].append({"type": type(error).__name__, "message": str(error)[:4096]})
        from .storage import StorageLimitError
        if engine is not None and isinstance(error, StorageLimitError):
            engine._fail(error)
    finally:
        if tick_iterator is not None:
            tick_iterator.close()
        if engine is not None:
            try:
                engine.writer.event("replay_comparison_before_close", run_id=engine.run_id, status=report["status"],
                    scope="ticks and pre-close lifecycle; final report includes close verification",
                    authoritative_report="replay-report.json", compared_ticks=report["compared_ticks"],
                    first_divergence=report["first_divergence"])
                engine.close()
                if report["status"] == "passed":
                    for expected in close_events:
                        if not generated:
                            _difference("close", "source close rejection was not produced")
                        _same_event(expected, generated.popleft())
                        report["compared_events"] += 1
                    if generated:
                        _difference("close", "replay close produced an extra event", actual_kind=generated[0]["kind"])
            except Divergence as error:
                report["status"] = "diverged"
                report["first_divergence"] = report["first_divergence"] or error.detail
            except Exception as error:
                if report["status"] == "passed":
                    report["status"] = "failed"
                report["errors"].append({"type": type(error).__name__, "message": str(error)[:4096]})
                try:
                    engine.close()
                except Exception:
                    pass
        _write_report(destination, report, storage_budget)
    return report


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit("usage: python -m palimpsest.replay '{JSON configuration}'")
    config = json.loads(argv[0])
    required = {"source_run_path", "destination_run_path", "mode", "repo_root", "asset_root"}
    if not isinstance(config, dict) or not required <= set(config) or set(config) - required - {"storage"}:
        raise SystemExit("replay configuration requires exactly source_run_path,destination_run_path,mode,repo_root,asset_root")
    storage = config.pop("storage", None)
    if storage is not None:
        from .storage import StorageBudget, StorageLimits
        config["storage_budget"] = StorageBudget(tuple(Path(p) for p in storage["roots"]),
            StorageLimits(**storage["limits"]), headroom_bytes=storage["headroom_bytes"])
    report = replay_run(**config)
    print(json.dumps(report, allow_nan=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
