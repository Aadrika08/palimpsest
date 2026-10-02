"""Spawned simulation owner. No simulation imports occur in the API process."""

import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
from queue import Empty, Full
import time
import traceback
import uuid
import sys
import threading


def authoritative(queue, message, timeout=1.):
    """Replies cannot be silently discarded; backpressure fails explicitly."""
    queue.put(message, timeout=timeout)


def latest_display(queue, sample):
    try:
        queue.put_nowait(sample)
    except Full:
        try:
            queue.get(timeout=.01)
        except Empty:
            pass
        try:
            queue.put_nowait(sample)
        except Full:
            pass  # A newer display sample is already pending.


def _json(path, value, budget=None):
    temporary = path.with_suffix(".tmp")
    payload = (json.dumps(value, allow_nan=False, indent=2) + "\n").encode()
    if budget is not None:
        budget.check(len(payload), path=temporary)
    temporary.write_bytes(payload)
    temporary.replace(path)


def _trace(path, application):
    from .records import iter_ticks
    result = []
    for row in iter_ticks(path / "recording"):
        if row["episode"] == application["episode"] and row["tick"] < application["episode_step"]:
            if not result:
                result.append(row["pose"][:2].tolist())
            result.append(row["next_pose"][:2].tolist())
    return result[-601:]


class _ExecutionTiming:
    """Wall time includes active IPC/render/log work, excluding load and pauses."""
    def __init__(self, now, total_tick):
        self.last, self.tick, self.running = now, total_tick, False
        self.active, self.simulated = 0., 0.

    def update(self, now, total_tick, running, step_wall=0.):
        ticks = total_tick - self.tick
        self.active += now - self.last if self.running else step_wall if ticks else 0.
        self.simulated += ticks * .02
        self.last, self.tick, self.running = now, total_tick, running

    def view(self):
        return {"active_wall_seconds": self.active, "advanced_simulation_seconds": self.simulated,
                "rtf": self.simulated / self.active if self.active else None}


def _sample(engine, run_id, trace, started, timing=None):
    from .artifacts import image_data_url
    state = engine.public_state()
    state["receipts"] = list(engine.receipts.values())
    transition = engine.last_transition
    if transition is not None:
        cameras, sensors, eyes = transition, transition["sensors"], transition["eyes"]
        episode, tick, stage = transition["episode"], transition["tick"], "used"
        projected = {key: copy.deepcopy(transition[key]) for key in
                     ("episode", "tick", "action", "control", "populations", "latency", "step_latency")}
        if "raw_output" in transition:
            projected["raw_output"] = transition["raw_output"].tolist()
        for key in ("action", "control"):
            projected[key] = projected[key].tolist()
    else:
        cameras = {key: engine.observation[key].copy() for key in ("cam_left", "cam_right")}
        eyes = state["eyes"]
        for name, enabled in (("cam_left", eyes["left"]), ("cam_right", eyes["right"])):
            if not enabled:
                cameras[name].fill(0)
        raw = engine.observation["sensors"]
        sensors = [float(raw["collision"]), 0. if raw["collision_angle"] is None else float(raw["collision_angle"]),
                   *(map(float, raw["wind_direction"]) if engine.memory is None and engine.task_state is None else (None, None))]
        episode, tick, stage = state["episode"], state["episode_step"], "next"
        if engine.memory is not None:
            stage = 'pending-memory'
        elif engine.task_state is not None:
            stage = 'pending-task'
        projected = None
    memory_view = None
    if engine.memory is not None:
        from .memory_task import inspect as inspect_memory
        memory_view = inspect_memory(engine.memory)
    return {"version": 1, "type": "sample", "run_id": run_id, "mode": "live", "state": state,
            "world": engine.world(), "inputs": {"episode": episode, "tick": tick, "stage": stage,
                "cam_left": image_data_url(cameras["cam_left"]), "cam_right": image_data_url(cameras["cam_right"]),
                "sensors": sensors.tolist() if hasattr(sensors, "tolist") else sensors, "eyes": eyes},
            "transition": projected, "trace": copy.deepcopy(trace[-601:]), "wall_elapsed": time.monotonic() - started,
            "performance": timing.view() if timing else None,
            "memory": memory_view, "task": copy.deepcopy(engine.task_state)}


class Conflict(ValueError):
    pass


class _ReplayTransport:
    """Pause the replay job at callbacks without touching its Engine timeline."""
    def __init__(self, path, mode, commands, send, disconnected, stop, progress, budget=None):
        self.path, self.mode, self.commands, self.send = path, mode, commands, send
        self.disconnected, self.stop, self.progress = disconnected, stop, progress
        self.phase, self.revision, self.underlying = "loading", 0, None
        self.receipts, self.originals, self.event_count = {}, {}, 0
        self.last_status = 0.
        self.budget = budget
        (path / "job-events.jsonl").touch(exist_ok=False)

    def view(self):
        state = copy.deepcopy(self.underlying)
        if state is not None:
            state.update(phase=self.phase, revision=self.revision, pending_commands=0)
        return {"job": "replay", "replay_mode": self.mode, "jobstate": self.phase,
                "state": state, "underlying_state": copy.deepcopy(self.underlying),
                "receipts": list(self.receipts.values())}

    def status(self):
        self.send({"type": "status", "status": "loading" if self.phase == "loading" else "ready", **self.view()})
        self.last_status = time.monotonic()

    def event(self, kind, **fields):
        if self.event_count >= 8192:
            raise RuntimeError("Replay transport event limit reached")
        record = {"version": 1, "type": kind, "scope": "replay_transport",
                  "ordinal": self.event_count, "revision": self.revision, **fields}
        payload = json.dumps(record, allow_nan=False) + "\n"
        if self.budget is not None:
            self.budget.check(len(payload.encode()), path=self.path / "job-events.jsonl")
        with (self.path / "job-events.jsonl").open("a") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        self.event_count += 1

    def command(self, value):
        required = {"id", "kind", "expected_state", "expected_episode", "expected_revision"}
        if type(value) is not dict or not required <= value.keys() or value.keys() - required - {"payload"}:
            raise ValueError("Invalid replay transport command fields")
        identifier = value["id"]
        if type(identifier) is not str or not 1 <= len(identifier) <= 128:
            raise ValueError("Replay command ID must contain 1 to 128 characters")
        if value["kind"] not in ("run", "pause", "stop") or value.get("payload", {}) != {}:
            raise ValueError("Replay jobs accept only run, pause and stop without payload")
        if identifier in self.originals:
            if value != self.originals[identifier]:
                raise Conflict("Replay command ID already has a different body")
            return self.receipts[identifier]
        if len(self.receipts) >= 4096 or self.event_count >= 8192:
            raise RuntimeError("Replay transport command limit reached")
        if (type(value["expected_episode"]) is not int or type(value["expected_revision"]) is not int or
            value["expected_state"] != self.phase or value["expected_episode"] != self.underlying["episode"] or
            value["expected_revision"] != self.revision):
            raise Conflict("Replay transport expected state, episode or revision is stale")
        self.phase = {"run": "running", "pause": "paused", "stop": "canceled"}[value["kind"]]
        self.revision += 1
        receipt = {"id": identifier, "kind": value["kind"], "status": "applied", "scope": "replay_transport",
                   "episode": self.underlying["episode"], "tick": self.underlying["episode_step"],
                   "revision": self.revision}
        self.originals[identifier], self.receipts[identifier] = copy.deepcopy(value), receipt
        self.event("job_command", command=value, receipt=receipt)
        self.send({"type": "receipt", **self.view()})
        self.status()
        return receipt

    def __call__(self, stage, state=None):
        self.progress.value = time.monotonic()
        if self.stop.is_set():
            raise InterruptedError("Replay owner closed")
        if state is not None:
            self.underlying = copy.deepcopy(state)
        if stage == "loading":
            self.status()
            return
        if self.underlying is None:
            raise ValueError("Replay boundary progress requires actual Engine state")
        if self.phase == "loading":
            self.phase = "running"
            self.status()
        while True:
            self.progress.value = time.monotonic()
            if self.stop.is_set():
                raise InterruptedError("Replay owner closed")
            if self.disconnected.is_set():
                self.disconnected.clear()
                if self.phase != "paused":
                    self.phase, self.revision = "paused", self.revision + 1
                    self.event("job_disconnected", episode=self.underlying["episode"], tick=self.underlying["episode_step"])
                    self.status()
            for _ in range(8):
                try:
                    request = self.commands.get_nowait()
                except Empty:
                    break
                try:
                    if request["op"] != "command":
                        raise ValueError("Replay jobs accept only run, pause and stop commands")
                    value = self.command(request["body"])
                    self.send({"type": "response", "request_id": request["request_id"], "value": value})
                except (ValueError, RuntimeError, KeyError, TypeError) as error:
                    from .storage import StorageLimitError
                    if isinstance(error, StorageLimitError):
                        raise
                    self.send({"type": "response", "request_id": request["request_id"],
                               "error": {"type": type(error).__name__, "message": str(error)}})
                if self.phase == "canceled":
                    raise InterruptedError("Replay transport stop applied")
            if time.monotonic() - self.last_status >= .1:
                self.status()
            if self.phase != "paused":
                return
            self.stop.wait(.02)

    def finish(self, report):
        self.phase = {"cancelled": "canceled", "failed": "failed"}.get(report.get("status"), "completed")
        self.event("job_completed", status=self.phase)
        self.send({"type": "closed", "status": "failed" if self.phase == "failed" else "closed", "replay": report, **self.view()})


def _episode_preflight(engine, path, budget):
    cameras = sum(engine.observation[name].nbytes for name in ("cam_left", "cam_right")) * 2
    neural = 0
    if engine.policy is not None:
        neural = (engine.policy.agent.cell.Nin + 2) * engine.policy.hidden.element_size()
    body = 0
    if getattr(engine, 'body_state', None) is not None:
        from .body_profile import MAX_TICK_BYTES
        body = MAX_TICK_BYTES + 4096
    # Numeric scalars, NPZ headers and chunk/event overhead, not full hidden logging.
    estimate = 600 * (cameras + neural + body + 4096) + 1024**2
    report = {"episode_ticks": 600, "recording_bytes_estimate": estimate,
              "raw_and_effective_camera_bytes_per_tick": cameras, "neural_bytes_per_tick": neural,
              "scope": "one episode estimate plus actual initial snapshot; every write and reset remains quota bounded"}
    if body:
        report['body_numeric_and_event_bytes_per_tick_bound'] = body
    if budget is not None:
        report["admission"] = budget.check(estimate, path=path / "recording")
    return report


def _snapshot(engine, path, registry, config, initial=False, budget=None, preflight_bytes=0):
    from .snapshots import capture, save_snapshot
    if engine.phase != "paused":
        raise Conflict("Snapshots require a paused boundary")
    if budget is not None:
        budget.check_count("snapshots", len(registry))
    identifier = uuid.uuid4().hex
    filename = "initial.snp" if initial else identifier + ".snp"
    snapshot = capture(engine.env, engine.observation, policy=engine.policy, teacher=engine.teacher,
                       application=engine.application_state())
    destination = path / "snapshots" / filename
    save_snapshot(snapshot, destination, storage_budget=budget,
                  preflight_bytes=preflight_bytes if budget is not None else 0)
    registry[identifier] = {"snapshot_id": identifier, "filename": filename, "initial": initial,
        "revision": engine.revision, "episode": engine.episode, "tick": engine.episode_step,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "config": {key: config[key] for key in ("scenario", "texture", "controller", "device", "seed")}}
    if 'policy_identity' in engine.writer.manifest:
        registry[identifier]['config']['policy_identity'] = copy.deepcopy(engine.writer.manifest['policy_identity'])
    _json(path / "snapshots/index.json", {"version": 1, "snapshots": registry}, budget)
    engine.writer.event("snapshot_registered", run_id=engine.run_id, snapshot_id=identifier,
                        filename=filename, initial=initial, episode=engine.episode, tick=engine.episode_step,
                        revision=engine.revision, sha256=registry[identifier]["sha256"])
    return identifier


def run_worker(config, commands, replies, display, disconnected, stop, progress):
    """All Engine calls, GL contexts and tensors stay in this process/thread."""
    os.setsid()
    os.environ.setdefault("MUJOCO_GL", "egl")
    os.environ.setdefault("MPLBACKEND", "Agg")
    path = Path(config["run_path"])
    from .evaluate import bounded_logs
    final_messages, log_failed = [], threading.Event()
    def log_failure(reason):
        log_failed.set()
        stop.set()
        with contextlib.suppress(Exception):
            authoritative(replies, {"version": 1, "run_id": config["run_id"], "type": "failure",
                "status": "failed", "failure": {"type": "LogLimit", "message": reason}})
    with bounded_logs(path, config.get("log_max_bytes", 1024**2), log_failure) as (stdout, stderr):
        sys.stdout.flush()
        sys.stderr.flush()
        saved = os.dup(1), os.dup(2)
        try:
            os.dup2(stdout.fileno(), 1)
            os.dup2(stderr.fileno(), 2)
            with os.fdopen(os.dup(1), "w", buffering=1) as out, os.fdopen(os.dup(2), "w", buffering=1) as err:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    _own(config, commands, replies, display, disconnected, stop, progress, final_messages)
        finally:
            for target, original in zip((1, 2), saved):
                os.dup2(original, target)
                os.close(original)
    if not log_failed.is_set():
        for message in final_messages:
            authoritative(replies, message)
    # This isolated owner has closed its engine/renderer/recorder and durable
    # logs. Flush both outgoing queues before exiting; module-finalization GC
    # can fault thousands of cold pages after completion. Parent-owned IPC is
    # released by the supervisor. Never cancel these feeders or truncate frames.
    for queue in (replies, display):
        queue.close()
        queue.join_thread()
    os._exit(0)


def _own(config, commands, replies, display, disconnected, stop, progress, final_messages=None):
    from .storage import StorageBudget, StorageLimits, StorageLimitError
    storage = config.get("storage")
    budget = StorageBudget(tuple(Path(p) for p in storage["roots"]), StorageLimits(**storage["limits"]),
                           headroom_bytes=storage["headroom_bytes"]) if storage else None
    engine, failed, replay_transport = None, False, None
    run_id, path, started = config["run_id"], Path(config["run_path"]), time.monotonic()
    def send(message):
        value = {"version": 1, "run_id": run_id, **message}
        if message["type"] == "closed" and final_messages is not None:
            final_messages.append(value)
        else:
            authoritative(replies, value)
    def heartbeat(*args, **kwargs):
        progress.value = time.monotonic()
    try:
        heartbeat()
        if config.get("job") == "replay":
            from .replay import replay_run
            replay_transport = _ReplayTransport(path, config["replay_mode"], commands, send,
                                               disconnected, stop, progress, budget)
            report = replay_run(Path(config["source_run_path"]), path, mode=config["replay_mode"],
                repo_root=Path(config["repo_root"]), asset_root=Path(config["asset_root"]), progress=replay_transport,
                storage_budget=budget)
            replay_transport.finish(report)
            return
        from .engine import Engine
        engine = Engine.open(Path(config["repo_root"]), Path(config["asset_root"]), path / "recording",
            controller=config["controller"], device=config["device"], seed=config["seed"],
            scenario=config["scenario"], texture=config["texture"], run_id=run_id, storage_budget=budget,
            expected_policy_identity=config.get('policy_identity'))
        heartbeat()
        trace = []
        if config.get("snapshot_path"):
            from .snapshots import read_snapshot
            snp_path = Path(config["snapshot_path"])
            if hashlib.sha256(snp_path.read_bytes()).hexdigest() != config["snapshot_sha256"]:
                raise ValueError("Registered snapshot hash differs")
            snapshot = read_snapshot(snp_path)
            if 'memory_u' in config:
                engine.restore_memory_branch(snapshot, config['memory_u'])
            else:
                engine.restore_branch(snapshot, replace_controller=config.get("replace_controller", False))
            trace = _trace(Path(config["source_run_path"]), snapshot["application"])
            engine.writer.event("branch_created", run_id=run_id, parent_snapshot_id=config["snapshot_id"],
                                controller_replaced=config.get("replace_controller", False))
            if config.get("intervention") is not None:
                if engine.public_state()["pending_commands"]:
                    raise Conflict("Branch edit requires a snapshot without inherited pending commands")
                edit_id = "branch-edit-" + uuid.uuid4().hex
                engine.submit({"id": edit_id, "kind": "intervene",
                    "expected_state": "paused", "expected_episode": engine.episode,
                    "expected_revision": engine.revision, "payload": config["intervention"]})
                engine.advance()
                receipt = engine.receipts[edit_id]
                if receipt["status"] != "applied":
                    raise Conflict("Branch edit rejected: " + receipt.get("reason", receipt["status"]))
        if not trace:
            trace = [engine.world()["pose"][:2]]
        (path / "snapshots").mkdir(exist_ok=True)
        registry = {}
        preflight = _episode_preflight(engine, path, budget)
        initial = _snapshot(engine, path, registry, config, initial=True, budget=budget,
                            preflight_bytes=preflight["recording_bytes_estimate"])
        preflight["initial_snapshot_bytes"] = (path / "snapshots/initial.snp").stat().st_size
        engine.writer.event("storage_preflight", **preflight, headless_continue=config.get("headless_continue", False))
        def status(kind="status"):
            return {"type": kind, "status": "failed" if engine.phase == "failed" else "ready",
                "state": engine.public_state(), "receipts": list(engine.receipts.values()),
                "storage_preflight": preflight,
                "snapshots": [{k: v for k, v in item.items() if k not in ("filename", "config", "sha256")}
                              for item in registry.values()], "initial_snapshot_id": initial}
        send(status())
        timing = _ExecutionTiming(time.monotonic(), engine.total_tick)
        latest_display(display, _sample(engine, run_id, trace, started, timing))
        last_signature, last_tick, last_episode = None, engine.total_tick, engine.episode
        next_display, next_tick = time.monotonic(), time.monotonic()
        while not stop.is_set():
            heartbeat()
            if disconnected.is_set():
                engine.pause_for_disconnect()
                disconnected.clear()
                send(status())
            step_wall = 0.
            for _ in range(8):
                try:
                    request = commands.get_nowait()
                except Empty:
                    break
                heartbeat()
                try:
                    operation, body = request["op"], request["body"]
                    if operation == "command":
                        value = engine.submit(body)
                    elif operation in ("preview", "snapshot"):
                        if type(body.get("expected_revision")) is not int or body["expected_revision"] != engine.revision:
                            raise Conflict("Expected revision is stale")
                        value = engine.preview(body["payload"]) if operation == "preview" else {
                            "snapshot_id": _snapshot(engine, path, registry, config, budget=budget)}
                    elif operation == "state":
                        value = status()
                    else:
                        raise ValueError("Unknown owner operation")
                    send({"type": "response", "request_id": request["request_id"], "value": value})
                except (ValueError, RuntimeError, KeyError, TypeError) as error:
                    if isinstance(error, StorageLimitError) or engine.writer._broken:
                        raise
                    send({"type": "response", "request_id": request["request_id"],
                          "error": {"type": type(error).__name__, "message": str(error)}})
                heartbeat()
            now = time.monotonic()
            running = engine.phase == "running"
            if (not running and engine.public_state()["pending_commands"]) or running and now >= next_tick:
                advance_started = time.monotonic()
                engine.advance()
                step_wall = time.monotonic() - advance_started
                heartbeat()
                # Keep every tick and its deadline across brief log/render stalls.
                # Pausing and resuming establishes a new wall-clock schedule.
                next_tick = next_tick + .02 if running else advance_started + .02
            if engine.episode != last_episode:
                trace, last_episode = [engine.world()["pose"][:2]], engine.episode
            elif engine.total_tick != last_tick:
                trace.append(engine.world()["pose"][:2])
                trace = trace[-601:]
            last_tick = engine.total_tick
            signature = (engine.phase, engine.revision, tuple((k, v["status"]) for k, v in engine.receipts.items()), len(registry))
            if signature != last_signature:
                send(status())
                last_signature = signature
            timing.update(time.monotonic(), engine.total_tick, engine.phase == "running", step_wall)
            if time.monotonic() >= next_display:
                display_started = time.monotonic()
                latest_display(display, _sample(engine, run_id, trace, started, timing))
                next_display = max(next_display + 1 / 30, display_started)
            if engine.phase == "failed":
                failed = True
                break
            delay = max(0., min(.005, next_tick - time.monotonic())) if engine.phase == "running" else .005
            stop.wait(delay)
    except BaseException as error:
        failed = True
        if engine is not None and engine.phase != "failed":
            with contextlib.suppress(Exception):
                engine._fail(error)
        traceback.print_exc()
        with contextlib.suppress(Exception):
            job = {}
            if replay_transport is not None:
                replay_transport.phase = "failed"
                job = replay_transport.view()
            send({"type": "failure", "status": "failed", "failure": {"type": type(error).__name__, "message": str(error)}, **job})
    finally:
        if engine is not None:
            try:
                engine.close()
                heartbeat()
                send({"type": "closed", "status": "failed" if failed else "closed",
                      "state": engine.public_state(), "receipts": list(engine.receipts.values())})
            except BaseException as error:
                traceback.print_exc()
                with contextlib.suppress(Exception):
                    send({"type": "failure", "status": "failed", "failure": {"type": type(error).__name__, "message": str(error)}})
