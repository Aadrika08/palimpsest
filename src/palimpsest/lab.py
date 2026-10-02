"""Loopback HTTP/UI service supervising one spawned simulation owner."""

import asyncio
import contextlib
import copy
from dataclasses import asdict
import json
import multiprocessing as mp
import os
from pathlib import Path
from queue import Empty, Full, Queue
import re
import secrets
import signal
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
import uuid

from .worker import run_worker


ID = re.compile(r"[0-9a-f]{32}\Z")
BODY_LIMIT = 16 * 1024


def _id(value):
    if type(value) is not str or not ID.fullmatch(value):
        raise ValueError("Use a registered generated ID")
    return value


def _json(path, value, budget=None):
    temporary = path.with_suffix(".tmp")
    payload = (json.dumps(value, allow_nan=False, indent=2) + "\n").encode()
    if len(payload) > 4 * 1024**2:
        raise RuntimeError("Supervisor report exceeds 4 MiB")
    if budget is not None:
        budget.check(len(payload), path=temporary)
    temporary.write_bytes(payload)
    temporary.replace(path)


class OwnerError(RuntimeError):
    def __init__(self, error):
        super().__init__(error["message"])
        self.kind = error["type"]


class LabSupervisor:
    """Process/IPC boundaries are injectable only for supervision tests."""
    MAX_COMPLETED = 8
    CLOSE_GRACE_SECONDS = 5.
    def __init__(self, repo_root, asset_root, runs_root, *, startup_timeout=180., step_timeout=30.,
                 headless_continue=False, worker_target=run_worker, export_root=None,
                 storage_limits=None, log_max_bytes=1024**2):
        from .storage import StorageBudget, StorageLimits
        self.repo_root, self.asset_root, self.runs_root = (Path(p).resolve() for p in (repo_root, asset_root, runs_root))
        self.export_root = Path(export_root or self.runs_root / "exports").resolve()
        for root in (self.runs_root, self.export_root):
            if root == self.asset_root or root in self.asset_root.parents or self.asset_root in root.parents:
                raise ValueError("Model assets must be outside managed storage roots")
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.export_root.mkdir(parents=True, exist_ok=True)
        if type(log_max_bytes) is not int or not 1024 <= log_max_bytes <= 64 * 1024**2:
            raise ValueError("Per-stream log limit must be 1 KiB to 64 MiB")
        self.log_max_bytes = log_max_bytes
        roots, limits = (self.runs_root, self.export_root), storage_limits or StorageLimits()
        self.budget = StorageBudget(roots, limits, headroom_bytes=2 * log_max_bytes + 8 * 1024**2)
        self.control_budget = StorageBudget(roots, limits)
        self._storage_lock = self.budget.lock()
        self._storage_lock.__enter__()
        self._storage_closed = False
        self.startup_timeout, self.step_timeout = startup_timeout, step_timeout
        self.headless_continue, self.worker_target = headless_continue, worker_target
        self.context = mp.get_context("spawn")
        self.workers, self.active_run_id = {}, None
        self.lock, self.stopping = threading.RLock(), threading.Event()
        self.subscribers = {}
        self.thread = threading.Thread(target=self._monitor, name="palimpsest-supervisor", daemon=True)
        self.thread.start()

    def path(self, identifier):
        identifier = _id(identifier)
        path = self.runs_root / identifier
        if path.is_symlink() or not path.is_dir() or path.resolve().parent != self.runs_root:
            raise FileNotFoundError("Unregistered run ID")
        return path

    def start(self, config):
        with self.lock:
            if self.stopping.is_set():
                raise RuntimeError("Lab has shut down")
            if self.active_run_id is not None:
                raise RuntimeError("Close the active run before creating another")
            if any(owner.process.is_alive() for owner in self.workers.values()):
                raise RuntimeError("Previous owner is still closing; wait for process exit")
            identifier = uuid.uuid4().hex
            path = self.runs_root / identifier
            self.budget.check_count("runs", sum(p.is_dir() and ID.fullmatch(p.name) is not None for p in self.runs_root.iterdir()))
            self.budget.check(1024**2, path=path)
            path.mkdir()
            config = {**config, "run_id": identifier, "run_path": str(path),
                      "repo_root": str(self.repo_root), "asset_root": str(self.asset_root),
                      "headless_continue": self.headless_continue,
                      "log_max_bytes": self.log_max_bytes,
                      "storage": {"roots": [str(p) for p in self.budget.roots],
                                  "limits": asdict(self.budget.limits), "headroom_bytes": self.budget.headroom_bytes}}
            commands, replies, display = (self.context.Queue(maxsize=size) for size in (128, 256, 1))
            # A dead owner makes outstanding requests uncertain; _settle reports
            # that failure. Its abandoned command pipe need not print EPIPEs.
            commands._ignore_epipe = True
            disconnected, stop = self.context.Event(), self.context.Event()
            progress = self.context.Value("d", time.monotonic())
            process = self.context.Process(target=self.worker_target,
                args=(config, commands, replies, display, disconnected, stop, progress), name="palimpsest-" + identifier)
            owner = SimpleNamespace(process=process, commands=commands, replies=replies, display=display,
                disconnected=disconnected, stop=stop, progress=progress, pending={}, exit_seen=None,
                started=time.monotonic(), config=config, done=threading.Event(), exited=threading.Event(),
                closed_seen=None, ipc_closed=False,
                view={"version": 1, "run_id": identifier, "status": "loading", "state": None,
                      "sample": None, "receipts": [], "snapshots": [], "initial_snapshot_id": None})
            if config.get("job") == "replay":
                owner.view.update(job="replay", replay_mode=config["replay_mode"], jobstate="loading", underlying_state=None)
            self.workers[identifier], self.active_run_id = owner, identifier
            _json(path / "supervisor.json", {key: value for key, value in owner.view.items() if key != "sample"}, self.control_budget)
            try:
                process.start()
                # Only the child produces these queues. CPython Queue retains
                # both pipe ends; close our unused writers so a child dying
                # mid-frame produces EOF instead of an unbounded recv_bytes.
                replies._writer.close()
                display._writer.close()
                commands._reader.close()
            except BaseException as error:
                self._fail(identifier, "SpawnError", str(error), kill=False)
                raise
            return identifier

    def describe(self, identifier):
        with self.lock:
            if identifier in self.workers:
                return copy.deepcopy(self.workers[identifier].view)
        path = self.path(identifier)
        supervisor = path / "supervisor.json"
        if not supervisor.is_file() or supervisor.is_symlink():
            raise FileNotFoundError("Unregistered lab run ID")
        report = json.loads(supervisor.read_text())
        return {"version": 1, "run_id": identifier, "state": None, "sample": None, "receipts": [],
                "snapshots": [], "initial_snapshot_id": None, "status": "failed", **report,
                "snapshots": self.snapshots(identifier)}

    def snapshots(self, identifier):
        path = self.path(identifier) / "snapshots/index.json"
        if not path.exists():
            return []
        if path.is_symlink() or path.stat().st_size > BODY_LIMIT * 256:
            raise ValueError("Invalid snapshot registry")
        registry = json.loads(path.read_text())
        if registry.get("version") != 1 or type(registry.get("snapshots")) is not dict:
            raise ValueError("Invalid snapshot registry")
        return list(registry["snapshots"].values())

    def snapshot(self, run_id, snapshot_id):
        snapshot_id = _id(snapshot_id)
        from .artifacts import registered_snapshots
        registered = {item['snapshot_id'] for item in registered_snapshots(self.path(run_id))}
        if snapshot_id not in registered:
            raise FileNotFoundError('Snapshot lacks authoritative registration')
        for item in self.snapshots(run_id):
            if item.get("snapshot_id") == snapshot_id:
                filename = "initial.snp" if item.get("initial") is True else snapshot_id + ".snp"
                if item.get("filename") != filename:
                    raise ValueError("Invalid registered snapshot filename")
                path = self.path(run_id) / "snapshots" / filename
                if path.is_symlink() or not path.is_file() or path.resolve().parent != (self.path(run_id) / "snapshots").resolve():
                    raise ValueError("Invalid registered snapshot path")
                return path, item
        raise FileNotFoundError("Unregistered snapshot ID")

    def call(self, identifier, operation, body, timeout=35.):
        with self.lock:
            owner = self.workers.get(identifier)
            if owner is None or owner.view["status"] != "ready":
                raise RuntimeError("Owner is not ready")
            request_id, event, result = uuid.uuid4().hex, threading.Event(), {}
            if len(owner.pending) >= 128:
                raise RuntimeError("Owner request queue is full")
            owner.pending[request_id] = (event, result)
            try:
                owner.commands.put_nowait({"request_id": request_id, "op": operation, "body": copy.deepcopy(body)})
            except Full:
                del owner.pending[request_id]
                raise RuntimeError("Owner command queue is full") from None
        if not event.wait(timeout):
            with self.lock:
                owner.pending.pop(request_id, None)
            raise RuntimeError("Owner response timeout; inspect authoritative run receipts")
        if "error" in result:
            raise OwnerError(result["error"])
        return result["value"]

    def disconnect(self):
        with self.lock:
            if self.active_run_id and not self.headless_continue:
                self.workers[self.active_run_id].disconnected.set()

    def subscribe(self):
        with self.lock:
            key = uuid.uuid4().hex
            pair = Queue(maxsize=256), threading.Event()
            self.subscribers[key] = pair
            return key, pair

    def unsubscribe(self, key):
        with self.lock:
            self.subscribers.pop(key, None)
            if not self.subscribers:
                self.disconnect()

    def _publish(self, message):
        for queue, overflow in self.subscribers.values():
            try:
                queue.put_nowait(copy.deepcopy(message))
            except Full:
                overflow.set()  # Close slow WS explicitly; reconnect fetches events.

    def _handle(self, identifier, message):
        owner = self.workers[identifier]
        kind = message["type"]
        if kind == "failure" and message.get("failure", {}).get("type") == "LogLimit":
            self._kill(owner)
        if kind == "closed" and owner.view["status"] == "failed":
            message = {**message, "status": "failed"}
            if owner.config.get("job") == "replay":
                message["jobstate"] = "failed"
        if kind == "response":
            pending = owner.pending.pop(message["request_id"], None)
            if pending:
                pending[1].update({key: message[key] for key in ("value", "error") if key in message})
                pending[0].set()
            return
        if kind == "sample":
            state, current = message["state"], owner.view.get("state")
            if current is not None and (state["revision"] < current["revision"] or
                    state["total_tick"] < current["total_tick"]):
                return
            owner.view["sample"] = message
            if current is None or state["revision"] > current["revision"] or state["total_tick"] > current["total_tick"]:
                owner.view["state"] = state
            return
        for key in ("status", "state", "receipts", "snapshots", "initial_snapshot_id", "failure", "replay",
                    "job", "replay_mode", "jobstate", "underlying_state", "storage_preflight"):
            if key in message:
                owner.view[key] = message[key]
        self._publish(message)
        if kind in ("closed", "failure"):
            owner.closed_seen = owner.closed_seen or time.monotonic()
            if kind == "closed" or not owner.process.is_alive():
                owner.done.set()
                if self.active_run_id == identifier:
                    self.active_run_id = None
            try:
                _json(self.path(identifier) / "supervisor.json", {key: value for key, value in owner.view.items() if key != "sample"}, self.control_budget)
            except (OSError, RuntimeError) as error:
                owner.view.update(status="failed", diagnostic_persistence_error=str(error))
            self._settle(owner, "Owner closed before response")

    def _settle(self, owner, reason):
        for event, result in owner.pending.values():
            result["error"] = {"type": "RuntimeError", "message": reason}
            event.set()
        owner.pending.clear()

    def _dispose_queues(self, owner):
        if not owner.ipc_closed:
            for queue in (owner.commands, owner.replies, owner.display):
                queue.cancel_join_thread()
                queue.close()
                queue._reader.close()
                if queue._thread is None:
                    queue._writer.close()
            owner.ipc_closed = True

    def _evict_completed(self):
        completed = [identifier for identifier, owner in self.workers.items()
                     if owner.done.is_set() and identifier != self.active_run_id and not owner.process.is_alive()]
        for identifier in completed[:-self.MAX_COMPLETED]:
            owner = self.workers[identifier]
            self._dispose_queues(owner)
            if owner.process.pid is not None:
                owner.process.join(timeout=0.)
            owner.process.close()
            del self.workers[identifier]

    def _kill(self, owner):
        if not owner.process.is_alive():
            return
        try:
            if os.getpgid(owner.process.pid) == owner.process.pid:
                os.killpg(owner.process.pid, signal.SIGTERM)
            else:
                owner.process.terminate()
        except ProcessLookupError:
            pass
        owner.process.join(timeout=.3)
        if owner.process.is_alive():
            try:
                if os.getpgid(owner.process.pid) == owner.process.pid:
                    os.killpg(owner.process.pid, signal.SIGKILL)
                else:
                    owner.process.kill()
            except ProcessLookupError:
                pass
            owner.process.join(timeout=1.)

    def _fail(self, identifier, kind, reason, kill=True):
        owner = self.workers[identifier]
        if kill:
            self._kill(owner)
        message = {"version": 1, "type": "failure", "run_id": identifier, "status": "failed",
                   "failure": {"type": kind, "message": reason}, "recording_integrity": "uncertain"}
        if owner.config.get("job") == "replay":
            message["jobstate"] = "failed"
        self._handle(identifier, message)

    def _monitor(self):
        while not self.stopping.wait(.01):
            with self.lock:
                for identifier, owner in list(self.workers.items()):
                    if owner.done.is_set():
                        if not owner.process.is_alive():
                            if owner.process.pid is not None:
                                owner.process.join(timeout=0.)
                            self._dispose_queues(owner)
                            owner.exited.set()
                            continue
                        elif owner.closed_seen is not None and time.monotonic() - owner.closed_seen > self.CLOSE_GRACE_SECONDS:
                            self._fail(identifier, "CloseTimeout", "Owner did not exit after reporting closed")
                            continue
                        # Completion can overtake the independent display feeder.
                        # Drain until exit so normal queue flushing can finish.
                    for _ in range(256):
                        try:
                            self._handle(identifier, owner.replies.get_nowait())
                        except (Empty, EOFError):
                            break
                        except OSError as caught:
                            self._fail(identifier, "OwnerIPCError", str(caught))
                            break
                    if owner.done.is_set() and not owner.process.is_alive():
                        continue
                    try:
                        sample = owner.display.get_nowait()
                        if not owner.done.is_set():
                            self._handle(identifier, sample)
                    except (Empty, EOFError):
                        pass
                    except OSError as caught:
                        self._fail(identifier, "OwnerIPCError", str(caught))
                    if owner.done.is_set():
                        continue
                    if not owner.process.is_alive():
                        if owner.view["status"] == "failed":
                            owner.done.set()
                            if self.active_run_id == identifier:
                                self.active_run_id = None
                            continue
                        owner.exit_seen = owner.exit_seen or time.monotonic()
                        if time.monotonic() - owner.exit_seen > .3:
                            self._fail(identifier, "WorkerExit", f"Owner exited without completion (code {owner.process.exitcode})", kill=False)
                    else:
                        limit = self.startup_timeout if owner.view["status"] == "loading" else self.step_timeout
                        if time.monotonic() - owner.progress.value > limit:
                            self._fail(identifier, "WorkerTimeout", f"Owner made no boundary progress for {limit:g} seconds")
                self._evict_completed()

    def close(self, identifier):
        with self.lock:
            owner = self.workers.get(identifier)
            if owner is None:
                return self.describe(identifier)
            owner.stop.set()
        if not owner.done.wait(5.):
            with self.lock:
                self._fail(identifier, "CloseTimeout", "Owner did not close within 5 seconds")
        # Let the monitor drain the final queues; joining while holding its lock
        # deadlocks a child whose display feeder still has bytes to write.
        # Model/interpreter finalization can outlast one second after closed.
        # Use the same bounded grace as the monitor, which keeps draining IPC.
        owner.exited.wait(self.CLOSE_GRACE_SECONDS)
        with self.lock:
            if identifier not in self.workers:
                return self.describe(identifier)
            if owner.process.pid is not None:
                owner.process.join(timeout=0.)
            if owner.process.is_alive():
                self._fail(identifier, "CloseTimeout", "Owner did not exit after closing")
            if not owner.process.is_alive():
                self._dispose_queues(owner)
        return self.describe(identifier)

    def shutdown(self):
        with self.lock:
            identifiers = [key for key, owner in self.workers.items() if owner.process.is_alive()]
        for identifier in identifiers:
            self.close(identifier)
        self.stopping.set()
        self.thread.join(timeout=2.)
        if self.thread.is_alive():
            raise RuntimeError("Supervisor monitor did not exit")
        for owner in self.workers.values():
            self._dispose_queues(owner)
            feeder = owner.commands._thread
            if feeder is not None:
                feeder.join(timeout=1.)
                if feeder.is_alive():
                    raise RuntimeError("Command feeder did not exit")
            owner.commands._writer.close()
            if owner.process.pid is not None:
                owner.process.join(timeout=0.)
            owner.process.close()
        self.workers.clear()
        self.subscribers.clear()
        self.active_run_id = None
        # Drop the last loop reference before uvicorn re-raises SIGTERM. SemLock
        # finalizers must run now, not depend on interpreter atexit cleanup.
        owner = None
        if not self._storage_closed:
            self._storage_lock.__exit__(None, None, None)
            self._storage_closed = True

    def export(self, identifier, format):
        from .artifacts import export_run
        with self.lock:
            if self.active_run_id is not None or any(o.process.is_alive() for o in self.workers.values()):
                raise RuntimeError("Close the active owner before exporting")
            count = sum(p.is_file() and p.suffix in (".svg", ".png", ".zip") for p in self.export_root.iterdir())
            self.budget.check_count("exports", count)
            artifact_id = uuid.uuid4().hex
            path = self.export_root / (artifact_id + {"svg": ".svg", "png": ".png", "bundle": ".zip"}[format])
            export_run(self.path(identifier), path, format, storage_budget=self.budget)
            return artifact_id, path


class LocalGuard:
    def __init__(self, app, token, port):
        self.app, self.token, self.port = app, token, port

    async def __call__(self, scope, receive, send):
        from starlette.responses import JSONResponse
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        headers = {key.decode().lower(): value.decode() for key, value in scope.get("headers", [])}
        host = headers.get("host", "")
        try:
            address = urlsplit("http://" + host)
            allowed = address.hostname in ("127.0.0.1", "localhost", "::1") and address.port == self.port and not address.username and not address.password
        except ValueError:
            allowed = False
        origin = headers.get("origin")
        if origin is not None:
            allowed = allowed and origin == "http://" + host
        allowed = allowed and headers.get("sec-fetch-site", "same-origin") in ("same-origin", "none")
        if not allowed:
            if scope["type"] == "websocket":
                return await send({"type": "websocket.close", "code": 1008})
            return await JSONResponse({"detail": "Loopback host/same-origin required"}, status_code=403)(scope, receive, send)
        if scope["type"] == "websocket":
            return await self.app(scope, receive, send)
        if scope["path"].startswith("/api/") and scope["path"] != "/api/v1/session" and not secrets.compare_digest(headers.get("x-palimpsest-session", "").encode(), self.token.encode()):
            return await JSONResponse({"detail": "Session token required"}, status_code=401)(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            body.extend(message.get("body", b""))
            if len(body) > BODY_LIMIT:
                return await JSONResponse({"detail": "Request body exceeds 16 KiB"}, status_code=413)(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False
        async def replay_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        await self.app(scope, replay_receive, send)


def create_app(repo_root, asset_root, runs_root, export_root=None, *, port=8765,
               startup_timeout=180., step_timeout=30., headless_continue=False,
               storage_limits=None, log_max_bytes=1024**2):
    from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    token = secrets.token_urlsafe(32)
    supervisor = LabSupervisor(repo_root, asset_root, runs_root, startup_timeout=startup_timeout,
        step_timeout=step_timeout, headless_continue=headless_continue, export_root=export_root,
        storage_limits=storage_limits, log_max_bytes=log_max_bytes)
    exports = supervisor.export_root
    artifacts = {}
    @contextlib.asynccontextmanager
    async def lifespan(app):
        yield
        await asyncio.to_thread(supervisor.shutdown)
    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.lab = supervisor
    app.add_middleware(LocalGuard, token=token, port=port)

    def error(caught):
        if isinstance(caught, FileNotFoundError):
            return HTTPException(404, str(caught))
        if isinstance(caught, OwnerError):
            return HTTPException(409 if caught.kind == "Conflict" else 400 if caught.kind in ("ValueError", "KeyError", "TypeError") else 503, str(caught))
        return HTTPException(400 if isinstance(caught, (ValueError, TypeError)) else 409, str(caught))

    async def body(request, keys, required=()):
        try:
            value = await request.json()
        except Exception as caught:
            raise HTTPException(400, "Finite JSON object required") from caught
        if type(value) is not dict or set(value).difference(keys) or set(required).difference(value):
            raise HTTPException(400, "Unknown/missing fields; paths are forbidden")
        try:
            json.dumps(value, allow_nan=False)
        except (ValueError, TypeError) as caught:
            raise HTTPException(400, "Finite JSON object required") from caught
        return value

    def configuration(value):
        result = {"scenario": "reproduction", "texture": "checker", "controller": "manual", "device": "cpu", "seed": 0, **value}
        if result["controller"] not in ("manual", "teacher", "flynn") or result["device"] not in ("cpu", "cuda") or result["controller"] != "flynn" and result["device"] != "cpu":
            raise ValueError("Choose a supported controller and explicit device; manual/teacher use cpu")
        if type(result["seed"]) is not int or not 0 <= result["seed"] < 2**31:
            raise ValueError("seed must be an integer in [0, 2**31)")
        from .profiles import list_profiles, validate
        validate(result["scenario"], result["texture"], result["controller"])
        selected = next(item for item in list_profiles(supervisor.repo_root, supervisor.asset_root)["controllers"] if item["id"] == result["controller"])
        if not selected["available"]:
            raise RuntimeError(selected["reason"])
        return result

    @app.get("/api/v1/session")
    def session():
        return {"token": token}

    @app.get("/api/v1/profiles")
    def profiles():
        from .profiles import list_profiles
        return list_profiles(supervisor.repo_root, supervisor.asset_root)

    @app.get("/api/v1/runs")
    def runs():
        from .artifacts import list_runs
        with supervisor.lock:
            idle = supervisor.active_run_id is None and not any(o.process.is_alive() for o in supervisor.workers.values())
            return {"runs": list_runs(supervisor.runs_root, rebuild_index=idle,
                                      storage_budget=supervisor.control_budget)}

    @app.post("/api/v1/runs", status_code=202)
    async def start(request: Request):
        value = await body(request, {"scenario", "texture", "controller", "device", "seed"})
        try:
            config = await asyncio.to_thread(configuration, value)
            identifier = supervisor.start(config)
            return {"run_id": identifier, "status": "loading"}
        except (ValueError, RuntimeError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.get("/api/v1/runs/{identifier}")
    def state(identifier: str):
        try:
            return supervisor.describe(_id(identifier))
        except (ValueError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.post("/api/v1/runs/{identifier}/commands")
    async def command(identifier: str, request: Request):
        value = await body(request, {"id", "kind", "expected_state", "expected_episode", "expected_revision", "payload"},
                           {"id", "kind", "expected_state", "expected_episode", "expected_revision"})
        try:
            _id(identifier)
            return await asyncio.to_thread(supervisor.call, identifier, "command", value)
        except (ValueError, RuntimeError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.post("/api/v1/runs/{identifier}/previews")
    async def preview(identifier: str, request: Request):
        value = await body(request, {"payload", "expected_revision"}, {"payload", "expected_revision"})
        try:
            _id(identifier)
            return await asyncio.to_thread(supervisor.call, identifier, "preview", value)
        except (ValueError, RuntimeError) as caught:
            raise error(caught) from caught

    @app.post("/api/v1/runs/{identifier}/snapshot")
    async def snapshot(identifier: str, request: Request):
        value = await body(request, {"expected_revision"}, {"expected_revision"})
        try:
            _id(identifier)
            return await asyncio.to_thread(supervisor.call, identifier, "snapshot", value)
        except (ValueError, RuntimeError) as caught:
            raise error(caught) from caught

    @app.post("/api/v1/runs/{identifier}/close")
    def close(identifier: str):
        try:
            return supervisor.close(_id(identifier))
        except (ValueError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.post("/api/v1/branches", status_code=202)
    async def branch(request: Request):
        value = await body(request, {"source_run_id", "snapshot_id", "controller", "intervention"}, {"source_run_id", "snapshot_id"})
        try:
            source = _id(value["source_run_id"])
            snapshot_path, item = supervisor.snapshot(source, value["snapshot_id"])
            from .snapshots import read_snapshot
            source_snapshot = await asyncio.to_thread(read_snapshot, snapshot_path)
            if source_snapshot['application'].get('execution_mode') == 'actions':
                raise ValueError('Action-replay snapshots require their recorded action stream; use replay')
            del source_snapshot
            config = dict(item["config"])
            previous = config["controller"]
            config["controller"] = value.get("controller", previous)
            if config["controller"] != "flynn":
                config["device"] = "cpu"
            config = await asyncio.to_thread(configuration, config)
            if supervisor.active_run_id is not None:
                await asyncio.to_thread(supervisor.close, supervisor.active_run_id)
            config.update(snapshot_path=str(snapshot_path), snapshot_sha256=item["sha256"], snapshot_id=value["snapshot_id"],
                source_run_path=str(supervisor.path(source)), replace_controller=config["controller"] != previous)
            if "intervention" in value:
                config["intervention"] = value["intervention"]
            identifier = supervisor.start(config)
            return {"run_id": identifier, "status": "loading"}
        except (ValueError, RuntimeError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.post("/api/v1/memory/branches", status_code=202)
    async def memory_branch(request: Request):
        value = await body(request, {'source_run_id', 'snapshot_id', 'u'}, {'source_run_id', 'snapshot_id', 'u'})
        def create():
            import hashlib
            from .memory import validate_u
            from .memory_task import validate_state as validate_memory
            from .memory_world import validate_state as validate_world_state
            from .snapshots import read_snapshot
            u = validate_u(value['u'])
            source, snapshot_id = _id(value['source_run_id']), _id(value['snapshot_id'])
            # Admission and source validation are atomic; failed requests never
            # close a live source or allocate a destination.
            with supervisor.lock:
                if supervisor.active_run_id is not None or any(o.process.is_alive() for o in supervisor.workers.values()):
                    raise RuntimeError('Release the active owner before a U-only branch')
                if supervisor.describe(source)['status'] != 'closed':
                    raise ValueError('U-only branch requires a cleanly closed source')
                path, item = supervisor.snapshot(source, snapshot_id)
                if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                    raise ValueError('Registered snapshot hash differs')
                snapshot = read_snapshot(path)
                application = snapshot['application']
                if (application.get('schema_version') != 3 or application.get('scenario') != 'memory-passages'
                        or application.get('source_run_id') != source or application.get('phase') != 'paused'
                        or application.get('execution_mode') not in ('live', 'policy')):
                    raise ValueError('U-only branch requires a complete paused memory snapshot')
                validate_memory(application.get('memory'))
                validate_world_state(application.get('world_task_state'))
                config = configuration(dict(item['config']))
                config.update(snapshot_path=str(path), snapshot_sha256=item['sha256'], snapshot_id=snapshot_id,
                              source_run_path=str(supervisor.path(source)), memory_u=u)
                return supervisor.start(config)
        try:
            identifier = await asyncio.to_thread(create)
            return {'run_id': identifier, 'status': 'loading'}
        except (ValueError, RuntimeError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.get("/api/v1/runs/{identifier}/events")
    def events(identifier: str, after: int = 0, limit: int = 200, stream: str = "auto"):
        if not 0 <= after <= 1_000_000 or not 1 <= limit <= 1000 or stream not in ("auto", "engine", "transport"):
            raise HTTPException(400, "Invalid event cursor/limit")
        try:
            root = supervisor.path(identifier)
            transport = stream == "transport" or stream == "auto" and (root / "job-events.jsonl").exists()
            path = root / ("job-events.jsonl" if transport else "recording/events.jsonl")
            if path.is_symlink():
                raise ValueError("Invalid event path")
            result = []
            with path.open() as source:
                for ordinal in range(after + limit):
                    line = source.readline(65537)
                    if not line:
                        break
                    if len(line) > 65536:
                        raise ValueError("Event exceeds bounded record size")
                    if ordinal >= after:
                        if not line.endswith("\n"):
                            break  # Live append is not yet durable/complete.
                        result.append(json.loads(line))
                        if len(result) == limit:
                            break
            return {"events": result, "next": after + len(result), "stream": "transport" if transport else "engine"}
        except (ValueError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.get("/api/v1/runs/{identifier}/playback")
    def playback(identifier: str, episode: int = 0, tick: int = 0):
        from .artifacts import playback
        try:
            return playback(supervisor.path(identifier), episode, tick)
        except (ValueError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.get("/api/v1/compare")
    def compare(left: str, right: str):
        from .artifacts import compare_runs
        try:
            return compare_runs(supervisor.path(left), supervisor.path(right))
        except (ValueError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.post("/api/v1/runs/{identifier}/replay", status_code=202)
    async def replay(identifier: str, request: Request):
        value = await body(request, {"mode"}, {"mode"})
        if value["mode"] not in ("actions", "policy"):
            raise HTTPException(400, "Replay mode must be actions or policy")
        try:
            path = supervisor.path(identifier)
            if supervisor.active_run_id is not None:
                raise RuntimeError("Close the active run before replay")
            config = {"job": "replay", "source_run_path": str(path), "replay_mode": value["mode"]}
            run = supervisor.start(config)
            return {"run_id": run, "status": "loading"}
        except (ValueError, RuntimeError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.post("/api/v1/runs/{identifier}/exports")
    async def export(identifier: str, request: Request):
        value = await body(request, {"format"}, {"format"})
        if value["format"] not in ("svg", "png", "bundle"):
            raise HTTPException(400, "Unknown export format")
        try:
            artifact_id, path = await asyncio.to_thread(supervisor.export, identifier, value["format"])
            artifacts[artifact_id] = path
            return {"artifact_id": artifact_id, "download_url": "/api/v1/artifacts/" + artifact_id}
        except (ValueError, FileNotFoundError, RuntimeError) as caught:
            raise error(caught) from caught

    @app.get("/api/v1/artifacts/{identifier}")
    def artifact(identifier: str):
        try:
            identifier = _id(identifier)
            path = artifacts.get(identifier)
            if path is None or path.is_symlink() or not path.is_file() or path.resolve().parent != exports:
                raise FileNotFoundError("Unregistered artifact ID")
            return FileResponse(path, filename=path.name)
        except (ValueError, FileNotFoundError) as caught:
            raise error(caught) from caught

    @app.websocket("/api/v1/stream")
    async def stream(socket: WebSocket):
        await socket.accept()
        key = None
        try:
            first = await asyncio.wait_for(socket.receive(), timeout=5.)
            text = first.get("text")
            if not isinstance(text, str) or len(text.encode()) > BODY_LIMIT:
                await socket.close(code=1009)
                return
            message = json.loads(text)
            if type(message) is not dict or set(message) != {"token"} or type(message["token"]) is not str or not secrets.compare_digest(message["token"].encode(), token.encode()):
                await socket.close(code=1008)
                return
            key, (queue, overflow) = supervisor.subscribe()
            last_sample = None
            while True:
                if overflow.is_set():
                    await socket.close(code=1013, reason="Status backpressure; reconnect and fetch events")
                    return
                try:
                    while True:
                        await socket.send_json(queue.get_nowait())
                except Empty:
                    pass
                identifier = supervisor.active_run_id
                if identifier:
                    view = supervisor.describe(identifier)
                    sample = view["sample"]
                    marker = (identifier, sample["wall_elapsed"]) if sample else None
                    if marker is not None and marker != last_sample:
                        await socket.send_json(sample)
                        last_sample = marker
                try:
                    incoming = await asyncio.wait_for(socket.receive(), timeout=.01)
                    if incoming["type"] == "websocket.disconnect":
                        return
                    if len((incoming.get("text") or "").encode()) + len(incoming.get("bytes", b"") or b"") > BODY_LIMIT:
                        await socket.close(code=1009)
                        return
                except asyncio.TimeoutError:
                    pass
        except (WebSocketDisconnect, asyncio.TimeoutError, ValueError):
            pass
        finally:
            if key:
                supervisor.unsubscribe(key)

    ui = supervisor.repo_root / "ui/dist"
    app.mount("/", StaticFiles(directory=ui, html=True, check_dir=False), name="ui")
    return app
