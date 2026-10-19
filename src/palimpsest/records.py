"""Lossless, bounded R0 recording; only published chunks participate in recovery."""

import hashlib
import io
import json
import os
from pathlib import Path
import queue
import re
import threading
import time
import zipfile


FORMAT = "palimpsest-npz-v1"
CHUNK_TICKS = 32
MAX_CHUNK_BYTES = 128 * 1024 * 1024
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
_RESERVED = {"episode", "tick", "file", "allow_pickle"}


def _json(value):
    return json.dumps(value, allow_nan=False, sort_keys=True)


def _atomic_manifest(path, payload):
    temporary = path.with_suffix(".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _integer(value):
    return type(value) is int and value >= 0


def _publish_chunk(path, payload):
    temporary = path.with_suffix(".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class _BackgroundWrites:
    """One FIFO writer thread for chunk files and event lines.

    Items are written in submission order, so events.jsonl keeps its sequence
    order and a chunk file is durable before its chunk event. The queue is
    bounded: a full queue blocks the caller (counted as backpressure) instead of
    growing memory. The first write error stops all later writes; the owner
    raises it on its next call.
    """

    def __init__(self, events, max_items):
        self.queue = queue.Queue(max_items)
        self.lock = threading.Lock()
        self.pending_bytes = 0
        self.error = None
        self.surfaced = False
        self.stats = {"mode": "background", "max_items": max_items, "max_queued_items": 0, "written_items": 0,
                      "backpressure_events": 0, "backpressure_seconds": 0.}
        self.thread = threading.Thread(target=self._run, args=(events,), name="palimpsest-recording-writer", daemon=True)
        self.thread.start()

    def put(self, item, size):
        with self.lock:
            self.pending_bytes += size
        if self.queue.full():
            self.stats["backpressure_events"] += 1
            started = time.monotonic()
            self.queue.put((item, size))
            self.stats["backpressure_seconds"] += time.monotonic() - started
        else:
            self.queue.put((item, size))
        self.stats["max_queued_items"] = max(self.stats["max_queued_items"], self.queue.qsize())

    def _run(self, events):
        while True:
            item, size = self.queue.get()
            try:
                if item is None:
                    return
                if self.error is None:
                    if item[0] == "chunk":
                        _publish_chunk(item[1], item[2])
                    else:
                        events.write(item[1])
                        events.flush()
                        os.fsync(events.fileno())
                    self.stats["written_items"] += 1
            except BaseException as error:
                self.error = error
            finally:
                with self.lock:
                    self.pending_bytes -= size
                self.queue.task_done()

    def stop(self):
        self.queue.put((None, 0))
        self.thread.join()

    def view(self):
        error = None if self.error is None else {"type": type(self.error).__name__, "message": str(self.error)}
        return {**self.stats, "queued_items": self.queue.qsize(), "pending_bytes": self.pending_bytes, "error": error}


def _load_json(value):
    def reject_constant(constant):
        raise ValueError(f"invalid JSON constant: {constant}")

    return json.loads(value, parse_constant=reject_constant)


class RunWriter:
    def __init__(self, path: Path, manifest: dict, max_bytes=None, *, storage_budget=None):
        if max_bytes is not None and (not _integer(max_bytes) or max_bytes == 0):
            raise ValueError("max_bytes must be a positive integer or None")
        self._max_bytes = max_bytes
        self.storage_budget = storage_budget
        self._bytes = self._manifest_bytes = 0
        self._broken = False
        self._background = None
        self.path = Path(path)
        self.manifest = {**manifest, "status": "running", "recording_format": FORMAT,
                         "recording_max_bytes": max_bytes}
        _json(self.manifest)
        self.path.mkdir(parents=True, exist_ok=False)
        (self.path / "chunks").mkdir()
        self._write_manifest(self.manifest)
        self._events = (self.path / "events.jsonl").open("x", encoding="utf-8")
        self._sequence = 0
        self._chunk = 0
        self._tick_count = 0
        self._buffer = []
        self._schema = None
        self._episode = None
        self._last_tick = None
        self._finished = False

    def start_background(self, max_items=16):
        """Move chunk-file and event writes (and their fsyncs) to one bounded thread.

        The caller still validates, sequences, stages and hashes every record and
        checks quotas, counting queued-but-unwritten bytes, so the published bytes
        are identical to the synchronous path. ``flush``, ``finish`` and ``close``
        wait for the queue to drain; a write error fails the next writer call.
        A killed process keeps a valid published prefix, possibly shorter by the
        queued items. Default writers stay synchronous.
        """
        self._active()
        if self._background is not None:
            raise ValueError("background writes already started")
        if not _integer(max_items) or max_items == 0:
            raise ValueError("max_items must be a positive integer")
        self._background = _BackgroundWrites(self._events, max_items)

    def background_stats(self):
        return None if self._background is None else self._background.view()

    def _raise_background_error(self):
        background = self._background
        if background is not None and background.error is not None:
            self._broken = True
            background.surfaced = True
            raise RuntimeError("Background recording write failed") from background.error

    def _drain(self):
        if self._background is not None:
            self._background.queue.join()
            self._raise_background_error()

    def _check_budget(self, additional):
        try:
            pending = 0 if self._background is None else self._background.pending_bytes
            if self._max_bytes is not None and self._bytes + additional > self._max_bytes:
                raise RuntimeError("Recording quota exceeded before publication")
            if self.storage_budget is not None:
                self.storage_budget.check(additional + pending, path=self.path)
        except (OSError, ValueError, RuntimeError):
            self._broken = True
            raise

    def _write_manifest(self, value):
        payload = (_json(value) + "\n").encode("utf-8")
        self._check_budget(len(payload))  # The old manifest survives until atomic replacement.
        try:
            _atomic_manifest(self.path / "manifest.json", payload)
        except OSError:
            self._broken = True
            raise
        self._bytes += len(payload) - self._manifest_bytes
        self._manifest_bytes = len(payload)

    def _active(self):
        if self._events.closed or self._finished or self._broken:
            raise ValueError("run writer is closed or finished")

    def event(self, kind: str, **data):
        self._raise_background_error()
        self._active()
        if not isinstance(kind, str) or not kind or "sequence" in data:
            raise ValueError("event requires a kind and cannot override its sequence")
        payload = _json({**data, "sequence": self._sequence, "kind": kind}) + "\n"
        payload_bytes = len(payload.encode("utf-8"))
        self._check_budget(payload_bytes)
        if self._background is not None:
            self._sequence += 1
            self._bytes += payload_bytes
            self._background.put(("event", payload), payload_bytes)
            return
        try:
            self._events.write(payload)
            self._events.flush()
            os.fsync(self._events.fileno())
        except OSError:
            self._broken = True
            raise
        self._sequence += 1
        self._bytes += payload_bytes

    def tick(self, episode: int, tick: int, **arrays):
        import numpy as np

        self._raise_background_error()
        self._active()
        if not _integer(episode) or not _integer(tick) or not arrays:
            raise ValueError("tick requires nonnegative episode/tick numbers and numeric arrays")
        if self._episode is not None and (episode < self._episode or (episode == self._episode and tick != self._last_tick + 1)):
            raise ValueError("episodes must increase and their ticks must be contiguous")
        values = {}
        for name, value in arrays.items():
            if not _NAME.fullmatch(name) or name in _RESERVED:
                raise ValueError(f"invalid array name: {name}")
            array = np.asarray(value)
            if array.dtype.kind not in "biufc":
                raise ValueError(f"array {name} must have a numeric or boolean dtype")
            values[name] = array.copy()
        schema = {name: {"dtype": value.dtype.str, "shape": list(value.shape)} for name, value in values.items()}
        if self._schema is not None and schema != self._schema:
            raise ValueError("recorded array names, dtypes and shapes must stay constant")
        # Bound bytes as well as ticks; refuse oversized records before buffering.
        if sum(value.nbytes for value in values.values()) * CHUNK_TICKS > MAX_CHUNK_BYTES:
            raise ValueError("record would exceed the 128 MiB chunk limit")
        if episode != self._episode:
            self._flush()
        self._schema = schema
        self._episode, self._last_tick = episode, tick
        self._buffer.append((tick, values))
        self._tick_count += 1
        if len(self._buffer) == CHUNK_TICKS:
            self._flush()

    def _flush(self):
        if not self._buffer:
            return
        import numpy as np

        relative = f"chunks/{self._chunk:06d}.npz"
        path = self.path / relative
        temporary = path.with_suffix(".tmp")
        values = {name: np.stack([row[name] for _, row in self._buffer]) for name in self._schema}
        try:
            self._check_budget(sum(value.nbytes for value in values.values()))
            # One chunk-sized staging buffer permits an exact check before any disk write.
            with io.BytesIO() as staging:
                np.savez(staging, **values)
                payload = staging.getvalue()
            chunk_event = dict(path=relative, sha256=hashlib.sha256(payload).hexdigest(), episode=self._episode,
                               start=self._buffer[0][0], count=len(self._buffer), arrays=self._schema)
            event_bytes = len((_json({**chunk_event, "sequence": self._sequence, "kind": "chunk"}) + "\n").encode("utf-8"))
            self._check_budget(len(payload) + event_bytes)
            if self._background is not None:
                self._background.put(("chunk", path, payload), len(payload))
            else:
                with temporary.open("xb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                temporary.replace(path)
            self._bytes += len(payload)
            self.event("chunk", **chunk_event)
        except Exception:
            self._broken = True
            raise
        finally:
            if self._background is None:  # The writer thread owns its temporary file.
                temporary.unlink(missing_ok=True)
        self._buffer.clear()
        self._chunk += 1

    def flush(self):
        """Publish pending ticks without finishing the run; background writes drain."""
        self._raise_background_error()
        self._active()
        self._flush()
        self._drain()

    def finish(self, summary: dict, status="completed"):
        self._raise_background_error()
        self._active()
        if not isinstance(status, str) or not status or status == "running":
            raise ValueError("finish requires a terminal status")
        manifest = {**self.manifest, **summary, "status": status, "recording_format": FORMAT}
        _json(manifest)
        self._flush()
        self._drain()  # Every chunk and event is durable before the terminal manifest.
        manifest.update(recorded_ticks=self._tick_count, recorded_chunks=self._chunk, recorded_events=self._sequence)
        self._write_manifest(manifest)
        self.manifest = manifest
        self._finished = True
        self._stop_background()
        self._events.close()

    def _stop_background(self):
        if self._background is not None and self._background.thread.is_alive():
            self._background.stop()

    def close(self):
        """Publish pending ticks, retaining a running status unless finish succeeded."""
        if not self._events.closed:
            try:
                if not self._broken and (self._background is None or self._background.error is None):
                    self._flush()
            finally:
                try:
                    self._stop_background()  # Already accepted items still publish in order.
                finally:
                    self._events.close()
            background = self._background
            if background is not None and background.error is not None and not background.surfaced:
                self._raise_background_error()


def iter_ticks(path: Path):
    """Yield validated published ticks. A torn last event is ignored only for running runs."""
    import numpy as np

    path = Path(path).resolve()
    for name in ("manifest.json", "events.jsonl"):
        if (path / name).is_symlink():
            raise ValueError(f"recording metadata cannot be a symlink: {name}")
    manifest = _load_json((path / "manifest.json").read_text())
    if not isinstance(manifest, dict) or manifest.get("recording_format") != FORMAT or not isinstance(manifest.get("status"), str):
        raise ValueError("unknown recording manifest")
    previous = None
    schema = None
    chunk_index = 0
    tick_count = 0
    event_count = 0
    with (path / "events.jsonl").open("rb") as events:
        for sequence, line in enumerate(events):
            if not line.endswith(b"\n"):
                if manifest["status"] == "running":
                    break
                raise ValueError("terminal recording has an incomplete event")
            event = _load_json(line)
            if not isinstance(event, dict) or type(event.get("sequence")) is not int or event["sequence"] != sequence or not isinstance(event.get("kind"), str) or not event["kind"]:
                raise ValueError("invalid event sequence or kind")
            event_count += 1
            if event["kind"] != "chunk":
                continue
            expected_path = f"chunks/{chunk_index:06d}.npz"
            if event.get("path") != expected_path:
                raise ValueError("unsafe or out-of-order chunk path")
            chunk = path / expected_path
            if chunk.is_symlink() or chunk.parent.is_symlink() or not chunk.is_file() or not chunk.resolve().is_relative_to(path):
                raise ValueError("chunk is missing or outside the run")
            if _digest(chunk) != event.get("sha256"):
                raise ValueError("chunk checksum mismatch")
            episode, start, count = (event.get(key) for key in ("episode", "start", "count"))
            if not all(_integer(value) for value in (episode, start, count)) or not 1 <= count <= CHUNK_TICKS:
                raise ValueError("invalid chunk range")
            if previous is not None and (episode < previous[0] or (episode == previous[0] and start != previous[1] + 1)):
                raise ValueError("chunk tick ranges are not contiguous")
            fields = event.get("arrays")
            if not isinstance(fields, dict) or not fields or (schema is not None and fields != schema):
                raise ValueError("invalid or changed array schema")
            for name, description in fields.items():
                if not _NAME.fullmatch(name) or name in _RESERVED or not isinstance(description, dict):
                    raise ValueError("invalid recorded array metadata")
                shape = description.get("shape")
                if not isinstance(shape, list) or not all(_integer(size) for size in shape) or not isinstance(description.get("dtype"), str):
                    raise ValueError("invalid recorded array dtype or shape")
            with zipfile.ZipFile(chunk) as archive:
                members = archive.infolist()
                if len(members) != len(fields) or {member.filename for member in members} != {f"{name}.npy" for name in fields}:
                    raise ValueError("chunk members do not match declared fields")
                if sum(member.file_size for member in members) > MAX_CHUNK_BYTES + 65536 or any(member.compress_type != zipfile.ZIP_STORED for member in members):
                    raise ValueError("unsupported or oversized chunk archive")
                for name, description in fields.items():
                    with archive.open(f"{name}.npy") as stream:
                        version = np.lib.format.read_magic(stream)
                        if version not in {(1, 0), (2, 0)}:
                            raise ValueError("unsupported numeric array format")
                        read_header = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
                        shape, _, dtype = read_header(stream)
                        if dtype.kind not in "biufc" or dtype.str != description["dtype"] or list(shape) != [count, *description["shape"]]:
                            raise ValueError("chunk dtype or shape mismatch")
                        size = dtype.itemsize
                        for dimension in shape:
                            size *= dimension
                        if size > MAX_CHUNK_BYTES or stream.tell() + size != archive.getinfo(f"{name}.npy").file_size:
                            raise ValueError("numeric array size does not match its content")
            with np.load(chunk, allow_pickle=False) as archive:
                if set(archive.files) != set(fields) or len(archive.files) != len(fields):
                    raise ValueError("chunk arrays do not match declared fields")
                arrays = {}
                for name, description in fields.items():
                    array = archive[name]
                    if array.dtype.kind not in "biufc" or array.dtype.str != description.get("dtype") or list(array.shape) != [count, *description.get("shape", [])]:
                        raise ValueError("chunk dtype or shape mismatch")
                    arrays[name] = array
                for offset in range(count):
                    yield {"episode": episode, "tick": start + offset, **{name: array[offset].copy() for name, array in arrays.items()}}
            previous = (episode, start + count - 1)
            schema = fields
            chunk_index += 1
            tick_count += count
    if manifest["status"] != "running":
        for name, count in (("recorded_ticks", tick_count), ("recorded_chunks", chunk_index), ("recorded_events", event_count)):
            if type(manifest.get(name)) is not int or manifest[name] != count:
                raise ValueError(f"terminal recording count mismatch: {name}")
