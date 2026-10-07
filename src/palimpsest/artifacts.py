"""Read-only views and exports of completed recordings; no simulation imports.

The SQLite index is disposable. Manifests, events and numeric chunks remain the
source of truth. A small stat-keyed cache retains verified metadata and traces,
never cameras or neural arrays.
"""
from __future__ import annotations

import base64
from collections import OrderedDict
import copy
from contextlib import closing
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sqlite3
import struct
import tempfile
import threading
import uuid
import xml.etree.ElementTree as ET
import zipfile
import zlib

from .records import iter_ticks

MAX_MANIFEST = 1024 * 1024
MAX_EVENTS = 32 * 1024 * 1024
MAX_EVENT = 1024 * 1024
MAX_CHUNKS = 4096
MAX_TICKS = 100_000
MAX_RECORDING_BYTES = 16 * 1024**3
_CACHE: OrderedDict = OrderedDict()
_CACHE_LOCK = threading.Lock()
_SECRET_KEYS = {"password", "authorization", "access_token", "refresh_token", "api_key",
                "token", "secret", "session_token", "cookie", "credentials"}
_VISIBLE_EVENTS = {"episode_started", "application_restored", "intervention", "eyes_changed",
                   "episode_finished", "command_applied", "command_rejected", "engine_failed",
                   "controller_replaced", "replay_finished", "replay_divergence", "branch_created", "snapshot_registered",
                   "memory_world_changed", "memory_sensed", "memory_decision", "memory_cue", "memory_u_replaced", "memory_inspected"}


def _json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("nonfinite JSON")
        return number
    try:
        return json.loads(data, object_pairs_hook=pairs,
                          parse_float=finite,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("invalid artifact JSON") from error


def _safe_path(path):
    path = Path(os.path.abspath(path))
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("artifact paths cannot traverse symlinks")
    return path


def _read(path, limit):
    path = _safe_path(path)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f"missing or oversized artifact: {path.name}")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("artifact exceeds read limit")
    return data


def _id(value):
    if not isinstance(value, str):
        raise ValueError("run ID must be a UUID")
    try:
        parsed = uuid.UUID(value)
    except ValueError as error:
        raise ValueError("run ID must be a UUID") from error
    if value not in {parsed.hex, str(parsed)}:
        raise ValueError("run ID must use canonical UUID spelling")
    return parsed


def _manifest(run):
    run = _safe_path(run)
    manifest = _json(_read(run / "recording/manifest.json", MAX_MANIFEST))
    if not isinstance(manifest, dict) or _id(manifest.get("run_id")) != _id(run.name):
        raise ValueError("run directory and manifest identity differ")
    if manifest.get("recording_format") != "palimpsest-npz-v1":
        raise ValueError("unsupported recording format")
    return manifest


def _events(run):
    data = _read(run / "recording/events.jsonl", MAX_EVENTS)
    if data and not data.endswith(b"\n"):
        raise ValueError("completed recording has an incomplete event")
    lines = data.splitlines()
    if len(lines) > 50_000:
        raise ValueError("too many recording events")
    result = []
    for sequence, line in enumerate(lines):
        if len(line) > MAX_EVENT:
            raise ValueError("event exceeds read limit")
        event = _json(line)
        if not isinstance(event, dict) or type(event.get("sequence")) is not int or event["sequence"] != sequence or not isinstance(event.get("kind"), str):
            raise ValueError("invalid event sequence")
        result.append(event)
    return result


def _fingerprint(paths):
    result = []
    total = 0
    for path in paths:
        _safe_path(path)
        if not path.is_file():
            raise ValueError("missing recording file")
        st = path.stat()
        total += st.st_size
        result.append((st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns))
    if total > MAX_RECORDING_BYTES:
        raise ValueError("recording exceeds artifact read budget")
    return tuple(result)


def _vector(value, count, label):
    import numpy as np
    array = np.asarray(value)
    if array.shape != (count,) or array.dtype.kind not in "iuf" or not np.isfinite(array).all():
        raise ValueError(f"invalid recorded {label}")
    return array.astype(float).tolist()


def _scalar(value, label, nonnegative=False):
    import numpy as np
    array = np.asarray(value)
    if array.shape != () or array.dtype.kind not in "iuf" or not np.isfinite(array):
        raise ValueError(f"invalid recorded {label}")
    number = float(array)
    if nonnegative and number < 0:
        raise ValueError(f"negative recorded {label}")
    return number


def _world(value):
    if not isinstance(value, dict) or set(value) != {"arena", "pose", "obstacles", "goal"}:
        raise ValueError("recording lacks complete world geometry")
    result = copy.deepcopy(value)
    result["arena"] = _scalar(value["arena"], "arena", True)
    result["pose"] = _vector(value["pose"], 3, "world pose")
    result["goal"] = _vector(value["goal"], 3, "goal")
    if not isinstance(value["obstacles"], list) or len(value["obstacles"]) > 1024:
        raise ValueError("invalid obstacle geometry")
    result["obstacles"] = [_vector(item, 3, "obstacle") for item in value["obstacles"]]
    if result["arena"] <= 0 or any(item[2] <= 0 for item in [result["goal"], *result["obstacles"]]):
        raise ValueError("invalid world dimensions")
    return result


def _world_at(events, episode, tick, pose=None):
    world = None
    for event in events:
        if event.get("episode") != episode or event.get("kind") not in {"episode_started", "application_restored", "intervention"}:
            continue
        boundary = event.get("episode_step")
        if type(boundary) is not int or boundary < 0:
            raise ValueError("world event lacks a valid episode boundary")
        if boundary > tick:
            continue
        if event["kind"] in {"episode_started", "application_restored"}:
            world = _world(event.get("world"))
        else:
            if world is None:
                raise ValueError("intervention precedes world geometry")
            change = event.get("change")
            if not isinstance(change, dict) or not isinstance(change.get("new"), dict):
                raise ValueError("invalid recorded intervention")
            xy = _vector(change["new"].get("xy"), 2, "intervention")
            if change.get("kind") == "move_goal":
                world["goal"][:2] = xy
            elif change.get("kind") == "move_obstacle":
                index = change.get("index")
                if type(index) is not int or not 0 <= index < len(world["obstacles"]):
                    raise ValueError("invalid recorded obstacle index")
                world["obstacles"][index][:2] = xy
            else:
                raise ValueError("unknown recorded intervention")
    if world is None:
        raise ValueError("recording lacks world geometry for this tick")
    if pose is not None:
        world["pose"] = list(pose)
    return world


def _load(run_path):
    run = _safe_path(run_path)
    paths = [run / "recording" / name for name in ("manifest.json", "events.jsonl")]
    metadata_fingerprint = _fingerprint(paths)
    manifest = _manifest(run)
    if manifest.get("status") != "completed":
        raise ValueError("artifact requires a completed recording")
    events = _events(run)
    chunks = [event for event in events if event["kind"] == "chunk"]
    if len(chunks) > MAX_CHUNKS:
        raise ValueError("too many recording chunks")
    for index, event in enumerate(chunks):
        if event.get("path") != f"chunks/{index:06d}.npz":
            raise ValueError("unsafe or out-of-order chunk path")
    paths += [run / "recording" / event["path"] for event in chunks]
    fingerprint = _fingerprint(paths)
    if fingerprint[:2] != metadata_fingerprint:
        raise ValueError("recording metadata changed during validation")
    key = str(run)
    with _CACHE_LOCK:
        if key in _CACHE and _CACHE[key][0] == fingerprint:
            _CACHE.move_to_end(key)
            return _CACHE[key][1]
    episodes = {}
    count = 0
    # Exhaust the reader: checksums and terminal aggregate counts must all pass.
    for row in iter_ticks(run / "recording"):
        count += 1
        if count > MAX_TICKS:
            raise ValueError("too many recording ticks")
        episode, tick = row["episode"], row["tick"]
        pose = _vector(row.get("pose"), 3, "pose")
        next_pose = _vector(row.get("next_pose"), 3, "next pose")
        item = episodes.setdefault(episode, {"episode": episode, "start_tick": tick,
            "ticks": [], "trace": [pose[:2]], "reward": 0., "path_length": 0., "contact_ticks": 0})
        item["ticks"].append(tick)
        item["trace"].append(next_pose[:2])
        item["last_pose"] = next_pose
        item["reward"] += _scalar(row.get("reward"), "reward")
        item["path_length"] += math.dist(pose[:2], next_pose[:2])
        item["contact_ticks"] += int(bool(_vector(row.get("sensors"), 4, "sensors")[0]))
        _scalar(row.get("simulation_time"), "simulation time", True)
    for episode, item in episodes.items():
        _world_at(events, episode, item["start_tick"])
        _world_at(events, episode, item["ticks"][-1])
    if _fingerprint(paths) != fingerprint:
        raise ValueError("recording changed during validation")
    result = {"run": run, "manifest": manifest, "events": events, "chunks": chunks,
              "paths": paths, "fingerprint": fingerprint, "episodes": episodes}
    with _CACHE_LOCK:
        _CACHE[key] = (fingerprint, result)
        _CACHE.move_to_end(key)
        while len(_CACHE) > 4:
            _CACHE.popitem(last=False)
    return result


def image_data_url(array):
    """Encode an actual uint8 RGB eye image without a rendering/inference import."""
    import numpy as np
    array = np.asarray(array)
    if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] != 3 or not 1 <= min(array.shape[:2]) <= max(array.shape[:2]) <= 2048:
        raise ValueError("camera must be a bounded uint8 RGB image")
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)
    height, width = array.shape[:2]
    raw = b"".join(b"\0" + row.tobytes() for row in array)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def playback(run_path, episode=0, tick=0):
    """Return exactly one recorded transition, after validating the whole run."""
    import numpy as np
    if type(episode) is not int or type(tick) is not int or episode < 0 or tick < 0:
        raise ValueError("episode and tick must be nonnegative integers")
    data = _load(run_path)
    item = data["episodes"].get(episode)
    if item is None or tick not in item["ticks"]:
        raise ValueError("requested recorded tick does not exist")
    event = next(event for event in data["chunks"] if event["episode"] == episode and event["start"] <= tick < event["start"] + event["count"])
    with np.load(data["run"] / "recording" / event["path"], allow_pickle=False) as archive:
        row = {name: archive[name][tick - event["start"]].copy() for name in archive.files}
    if _fingerprint(data["paths"]) != data["fingerprint"]:
        raise ValueError("recording changed during playback")
    world = _world_at(data["events"], episode, tick)
    world["pose"] = _vector(row["next_pose"], 3, "next pose")
    eyes = row.get("eyes")
    if eyes is None or eyes.shape != (2,) or eyes.dtype.kind != "b":
        raise ValueError("recording lacks eye enable state")
    revision = row.get("revision")
    if revision is None or revision.shape != () or revision.dtype.kind not in "iu" or int(revision) < 0:
        raise ValueError("recording lacks revision")
    transition = {"episode": episode, "tick": tick,
                  "action": _vector(row.get("action"), 2, "action"),
                  "control": _vector(row.get("control"), 2, "control"),
                  "latency": _scalar(row.get("latency"), "latency", True),
                  "step_latency": _scalar(row.get("step_latency"), "step latency", True), "populations": []}
    if "raw_output" in row:
        transition["raw_output"] = _vector(row["raw_output"], 2, "raw output")
    names = data["manifest"].get("population_names", [])
    stats = row.get("population_stats", np.empty((0, 4)))
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names) or stats.shape != (len(names), 4) or stats.dtype.kind not in "iuf" or not np.isfinite(stats).all():
        raise ValueError("invalid neural population summaries")
    for name, (count, mean, minimum, maximum) in zip(names, stats.tolist()):
        if count < 1 or count != int(count) or not minimum <= mean <= maximum:
            raise ValueError("invalid neural population statistics")
        transition["populations"].append({"name": name, "count": int(count), "mean": mean, "min": minimum, "max": maximum, "scale": [-1, 1]})
    offset = item["ticks"].index(tick)
    return {"version": 1, "type": "sample", "run_id": data["manifest"]["run_id"], "mode": "playback",
            "state": {"run_id": data["manifest"]["run_id"], "parent_run_id": data["manifest"].get("parent_run_id"),
                      "controller": data["manifest"].get("controller"), "phase": "playback", "episode": episode,
                      "episode_step": tick + 1, "revision": int(revision),
                      "simulation_time": _scalar(row["simulation_time"], "simulation time"),
                      "closed": True, "receipts": {}, "last_outcome": None},
            "world": world, "inputs": {"episode": episode, "tick": tick, "stage": "used",
                "cam_left": image_data_url(row.get("cam_left")), "cam_right": image_data_url(row.get("cam_right")),
                "sensors": _vector(row["sensors"], 4, "sensors"), "eyes": {"left": bool(eyes[0]), "right": bool(eyes[1])}},
            "transition": transition, "trace": copy.deepcopy(item["trace"][:offset + 2]), "wall_elapsed": None,
            "memory": next((copy.deepcopy(event['memory']) for event in reversed(data['events'])
                            if event['kind'] == 'memory_inspected' and event.get('episode') == episode
                            and event.get('episode_step') == tick), None),
            "task": next((copy.deepcopy(event['task']) for event in reversed(data['events'])
                          if event['kind'] == 'task_inspected' and event.get('episode') == episode
                          and event.get('episode_step') == tick), None)}


def _provenance(data):
    manifest = data["manifest"]
    keys = ("controller", "profile", "scenario", "texture", "seed", "requested_device", "teacher_privileged", "initial_world",
            "observation_profile", "control_interval_seconds", "continuation_contract", "parent_run_id",
            "parent_event_prefix", "source_snapshot_id", "snapshot_id", "controller_replacement", "replay_mode", "initial_memory",
            "task_protocol", "task_calibration", "task_profile_sha256")
    result = {key: manifest.get(key) for key in keys}
    result["environment"] = [{key: value for key, value in event.items() if key not in {"sequence", "run_id"}}
                             for event in data["events"] if event["kind"] == "environment"]
    result["policy"] = [event.get("provenance") for event in data["events"] if event["kind"] == "policy_loaded"]
    result["runtime"] = []
    result['memory_swaps'] = []
    for event in data["events"]:
        if event["kind"] == "diagnostics":
            report = event.get("report")
            if not isinstance(report, dict) or not isinstance(report.get("checks"), list):
                raise ValueError("invalid recorded diagnostics")
            for check in report["checks"]:
                if not isinstance(check, dict) or not isinstance(check.get("name"), str):
                    raise ValueError("invalid diagnostic check")
                if check["name"].startswith("dependency:") or check["name"] in {"python", "platform", "renderer"}:
                    result["runtime"].append(check)
                elif check["name"] == "gpu":
                    detail = check.get("detail")
                    if isinstance(detail, dict) and isinstance(detail.get("devices"), list):
                        result["runtime"].append({"name": "gpu", "devices": [
                            {key: value for key, value in device.items() if key != "memory_free_mib"}
                            for device in detail["devices"] if isinstance(device, dict)]})
        elif event["kind"] == "branch_created":
            result["source_snapshot_id"] = event.get("parent_snapshot_id")
            result["controller_replacement"] = event.get("controller_replaced")
        elif event['kind'] == 'memory_u_replaced':
            from .memory import sha256, validate_u
            old, new = validate_u(event['old_u']), validate_u(event['new_u'])
            result['memory_swaps'].append({'old_u_sha256': sha256(old), 'new_u_sha256': sha256(new),
                'old_payload_sha256': old['payload_sha256'], 'new_payload_sha256': new['payload_sha256'],
                'invariant_hashes': event['invariant_hashes']})
    result["interventions"] = [{key: event.get(key) for key in ("kind", "episode", "episode_step", "change", "eyes")}
                               for event in data["events"] if event["kind"] in {"intervention", "eyes_changed", "controller_replaced"}]
    return copy.deepcopy(result)


def _side(data):
    return {"run_id": data["manifest"]["run_id"], "provenance": _provenance(data),
            "geometry_stage": "last recorded transition per episode",
            "worlds": [{"episode": episode, "world": _world_at(data["events"], episode, item["ticks"][-1], item["last_pose"])}
                       for episode, item in data["episodes"].items()],
            "traces": [{"episode": item["episode"], "start_tick": item["start_tick"], "points": copy.deepcopy(item["trace"])} for item in data["episodes"].values()],
            "metrics": copy.deepcopy(data["manifest"].get("metrics")),
            "recorded_metrics": [{key: copy.deepcopy(value) for key, value in item.items() if key not in {"trace", "ticks", "last_pose"}} for item in data["episodes"].values()],
            "events": [copy.deepcopy(event) for event in data["events"] if event["kind"] in _VISIBLE_EVENTS],
            "final_phase": data["manifest"].get("final_phase"), "last_outcome": copy.deepcopy(data["manifest"].get("last_outcome"))}


def compare_runs(left_path, right_path):
    left, right = _side(_load(left_path)), _side(_load(right_path))
    differences = [{"field": key, "left": value, "right": right["provenance"][key]}
                   for key, value in left["provenance"].items() if value != right["provenance"][key]]
    parent = left["provenance"].get("parent_run_id")
    snapshot = left["provenance"].get("source_snapshot_id") or left["provenance"].get("snapshot_id")
    return {"left_run_id": left["run_id"], "right_run_id": right["run_id"], "differences": differences,
            "lineage": {"shared_parent": parent if parent and parent == right["provenance"].get("parent_run_id") else None,
                        "shared_snapshot": snapshot if snapshot and snapshot == (right["provenance"].get("source_snapshot_id") or right["provenance"].get("snapshot_id")) else None},
            "interpretation": "Recorded differences are descriptive; they do not establish causality.", "left": left, "right": right}


def _no_secrets(value, depth=0):
    if depth > 64:
        raise ValueError("export metadata nesting exceeds limit")
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.lower() in _SECRET_KEYS:
                raise ValueError("credential-bearing metadata cannot be exported")
            _no_secrets(item, depth + 1)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _no_secrets(item, depth + 1)


def _export_metadata(data, *, allow_empty=False):
    if not data["episodes"]:
        if not allow_empty:
            raise ValueError("recording has no trajectory to export")
        return {"schema_version": 1, "projection": None, **_side(data)}
    side = _side(data)
    arenas = {entry["world"]["arena"] for entry in side["worlds"]}
    if len(arenas) != 1:
        raise ValueError("episodes use incompatible world projections")
    return {"schema_version": 1, "run_id": data["manifest"]["run_id"],
            "projection": {"arena": arenas.pop(), "width": 800, "height": 800, "padding": 40,
                           "world_y": "up", "pixel_y": "down"},
            **side}


def _svg(metadata):
    ns = "http://www.w3.org/2000/svg"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}svg", {"width": "800", "height": "800", "viewBox": "0 0 800 800",
                      "role": "img", "aria-labelledby": "route-title route-description"})
    ET.SubElement(root, f"{{{ns}}}title", {"id": "route-title"}).text = "Recorded routes"
    ET.SubElement(root, f"{{{ns}}}desc", {"id": "route-description"}).text = (
        f"Recorded world-coordinate routes for run {metadata['run_id']}. "
        "Obstacles and goals show the last recorded world per episode. "
        "This is a recorded view, with no new simulation or physical pen marks.")
    ET.SubElement(root, f"{{{ns}}}metadata").text = json.dumps(metadata, allow_nan=False, separators=(",", ":"))
    ET.SubElement(root, f"{{{ns}}}rect", {"width": "800", "height": "800", "fill": "#edf2f4"})
    arena = metadata["projection"]["arena"]
    scale = 360 / arena
    group = ET.SubElement(root, f"{{{ns}}}g", {"transform": f"translate(400 400) scale({scale} {-scale})"})
    ET.SubElement(group, f"{{{ns}}}rect", {"x": str(-arena), "y": str(-arena), "width": str(2 * arena), "height": str(2 * arena), "fill": "white", "stroke": "#203444", "stroke-width": str(1 / scale)})
    for entry, trace in zip(metadata["worlds"], metadata["traces"]):
        ep = ET.SubElement(group, f"{{{ns}}}g", {"data-episode": str(entry["episode"])})
        for x, y, radius in entry["world"]["obstacles"]:
            ET.SubElement(ep, f"{{{ns}}}circle", {"cx": str(x), "cy": str(y), "r": str(radius), "fill": "#203444", "fill-opacity": ".25"})
        x, y, radius = entry["world"]["goal"]
        ET.SubElement(ep, f"{{{ns}}}circle", {"cx": str(x), "cy": str(y), "r": str(radius), "fill": "#8b5b12", "fill-opacity": ".4"})
        ET.SubElement(ep, f"{{{ns}}}polyline", {"points": " ".join(f"{x},{y}" for x, y in trace["points"]), "fill": "none", "stroke": "#245b84", "stroke-width": str(2 / scale)})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _png(metadata, stream):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.patches import Circle
    figure = Figure(figsize=(8, 8), dpi=100, facecolor="#edf2f4")
    FigureCanvasAgg(figure)
    axes = figure.add_axes([.05, .05, .9, .9], facecolor="white")
    arena = metadata["projection"]["arena"]
    axes.set(xlim=(-arena, arena), ylim=(-arena, arena), aspect="equal")
    axes.set_xticks([])
    axes.set_yticks([])
    for entry, trace in zip(metadata["worlds"], metadata["traces"]):
        for x, y, radius in entry["world"]["obstacles"]:
            axes.add_patch(Circle((x, y), radius, color="#203444", alpha=.25, linewidth=0))
        x, y, radius = entry["world"]["goal"]
        axes.add_patch(Circle((x, y), radius, color="#8b5b12", alpha=.4, linewidth=0))
        axes.plot(*zip(*trace["points"]), color="#245b84", linewidth=1.44)
    figure.savefig(stream, format="png", dpi=100, metadata={"palimpsest": json.dumps(metadata, allow_nan=False)})
    figure.clear()


def registered_snapshots(run_path, events=None):
    """Verify snapshot files against durable registration events, never native-decode."""
    from .snapshots import read_snapshot, MAX_BYTES
    run = _safe_path(run_path)
    manifest = _manifest(run)
    events = _events(run) if events is None else events
    if not isinstance(events, list) or len(events) > 50_000:
        raise ValueError("snapshot registration events exceed limit")
    records, identifiers, filenames = [], set(), set()
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("invalid snapshot registration event")
        if event.get("kind") != "snapshot_registered":
            continue
        identifier, initial, digest = (event.get(key) for key in ("snapshot_id", "initial", "sha256"))
        _id(identifier)
        if type(initial) is not bool or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid registered snapshot identity/hash")
        filename = "initial.snp" if initial else identifier + ".snp"
        if event.get("filename") != filename or _id(event.get("run_id")) != _id(manifest["run_id"]):
            raise ValueError("registered snapshot filename/run identity differs")
        if identifier in identifiers or filename in filenames:
            raise ValueError("duplicate snapshot registration")
        identifiers.add(identifier)
        filenames.add(filename)
        records.append({"filename": filename, "snapshot_id": identifier, "sha256": digest, "initial": initial})
        if len(records) > 4096:
            raise ValueError("snapshot registrations exceed limit")
    directory = run / "snapshots"
    if directory.exists() or directory.is_symlink():
        _safe_path(directory)
        for count, path in enumerate(directory.iterdir()):
            if count >= 4096:
                raise ValueError("snapshot directory exceeds entry limit")
            known = path.name == "initial.snp"
            if not known and path.suffix == ".snp":
                try:
                    _id(path.stem)
                    known = True
                except ValueError:
                    pass
            if known and path.name not in filenames:
                raise ValueError("unregistered snapshot: " + path.name)
    index = directory / "index.json"
    checked_paths = [directory / record["filename"] for record in records]
    for path in checked_paths:
        _safe_path(path)
        if not path.is_file():
            raise ValueError("missing registered snapshot: " + path.name)
    if index.exists() or index.is_symlink():
        checked_paths.append(index)
    fingerprint = _fingerprint(checked_paths)
    if index in checked_paths:
        registry = _json(_read(index, 4 * 1024**2))
        _no_secrets(registry)
        if not isinstance(registry, dict) or type(registry.get("version")) is not int or registry["version"] != 1 or not isinstance(registry.get("snapshots"), dict) or set(registry["snapshots"]) != identifiers:
            raise ValueError("snapshot registry differs from registration events")
        for record in records:
            derived = registry["snapshots"][record["snapshot_id"]]
            if not isinstance(derived, dict) or any(type(derived.get(key)) is not type(value) or derived[key] != value for key, value in record.items()):
                raise ValueError("snapshot registry differs from registration events")
    for record in records:
        path = directory / record["filename"]
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("registered snapshot exceeds file limit")
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                digest.update(block)
        if digest.hexdigest() != record["sha256"]:
            raise ValueError("registered snapshot hash differs: " + record["filename"])
        state = read_snapshot(path)
        _no_secrets(state)
    if _fingerprint(checked_paths) != fingerprint:
        raise ValueError("snapshot changed during registration validation")
    return records


def _bundle_inputs(data):
    paths = [(f"recording/{path.relative_to(data['run'] / 'recording').as_posix()}", path) for path in data["paths"]]
    snapshots = registered_snapshots(data["run"], data["events"])
    expected_hashes = {"snapshots/" + record["filename"]: record["sha256"] for record in snapshots}
    paths += [("snapshots/" + record["filename"], data["run"] / "snapshots" / record["filename"]) for record in snapshots]
    for name in ("job-events.jsonl", "replay-report.json"):
        path = data["run"] / name
        if not path.exists() and not path.is_symlink():
            continue
        raw = _read(path, MAX_EVENTS if name.endswith("jsonl") else MAX_MANIFEST)
        if name.endswith("jsonl"):
            if raw and not raw.endswith(b"\n"):
                raise ValueError("incomplete replay transport event")
            lines = raw.splitlines()
            if len(lines) > 50_000 or any(len(line) > MAX_EVENT for line in lines):
                raise ValueError("replay transport events exceed limit")
            values = [_json(line) for line in lines]
        else:
            values = [_json(raw)]
        for value in values:
            if not isinstance(value, dict):
                raise ValueError("replay artifacts require JSON objects")
            _no_secrets(value)
        expected_hashes[name] = hashlib.sha256(raw).hexdigest()
        paths.append((name, path))
    fingerprint = _fingerprint([path for _, path in paths])
    _no_secrets(data["manifest"])
    _no_secrets(data["events"])
    return paths, expected_hashes, fingerprint


def _bundle_bound(paths, metadata):
    # ZIP_STORED has no compression expansion. Reserve ZIP64 headers, central
    # directory, descriptors and manifest text without buffering the payload.
    files = [{"path": relative, "size_bytes": path.stat().st_size, "sha256": "0" * 64}
             for relative, path in paths]
    manifest = json.dumps({"format": "palimpsest-bundle-v1", "files": files, "derived": metadata}, allow_nan=False).encode()
    return sum(file["size_bytes"] for file in files) + len(manifest) + 4096 + sum(256 + 2 * len(relative.encode()) for relative, _ in paths)


def _bundle(data, metadata, stream, *, prepared=None):
    paths, expected_hashes, fingerprint = prepared or _bundle_inputs(data)
    if _fingerprint([path for _, path in paths]) != fingerprint:
        raise ValueError("artifact changed before export")
    files = []
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for relative, path in paths:
            digest, size = hashlib.sha256(), 0
            with _safe_path(path).open("rb") as source, archive.open(relative, "w", force_zip64=True) as target:
                while block := source.read(1024 * 1024):
                    size += len(block)
                    if size > 512 * 1024**2:
                        raise ValueError("bundle member exceeds size limit")
                    digest.update(block)
                    target.write(block)
            actual_hash = digest.hexdigest()
            if relative in expected_hashes and actual_hash != expected_hashes[relative]:
                raise ValueError("registered bundle artifact hash differs: " + relative)
            files.append({"path": relative, "size_bytes": size, "sha256": actual_hash})
        archive.writestr("bundle-manifest.json", json.dumps({"format": "palimpsest-bundle-v1", "files": files, "derived": metadata}, allow_nan=False))
    if _fingerprint([path for _, path in paths]) != fingerprint:
        raise ValueError("artifact changed during export")


def export_run(run_path, output_path, format, storage_budget=None):
    if format not in {"svg", "png", "bundle"}:
        raise ValueError("export format must be svg, png or bundle")
    data = _load(run_path)
    metadata = _export_metadata(data, allow_empty=format == "bundle")
    _no_secrets(metadata)
    output = _safe_path(output_path)
    prepared, payload = None, None
    if format == "bundle":
        prepared = _bundle_inputs(data)
        bound = _bundle_bound(prepared[0], metadata)
    else:
        payload = io.BytesIO()
        if format == "svg":
            payload.write(_svg(metadata))
        else:
            _png(metadata, payload)
        bound = payload.tell()
        payload.seek(0)
    if storage_budget is not None:
        storage_budget.check(bound, path=output)
    # Reserve exclusively only after validation/preflight. Remove our partial
    # file on error, but never replace an existing artifact.
    stream = output.open("xb")
    try:
        with stream:
            if format == "bundle":
                _bundle(data, metadata, stream, prepared=prepared)
            else:
                while block := payload.read(1024 * 1024):
                    stream.write(block)
            if _fingerprint(data["paths"]) != data["fingerprint"]:
                raise ValueError("recording changed during export")
    except BaseException:
        output.unlink()
        raise
    return output


def list_runs(root, *, rebuild_index=True, storage_budget=None):
    """Rebuild a disposable SQLite index from immediate UUID run manifests.

    Invalid or not-yet-published manifests are excluded. Summary discovery does
    not certify chunk integrity; playback/comparison/export perform that check.
    """
    root = _safe_path(root)
    if not root.is_dir():
        raise ValueError("runs root must be a directory")
    summaries = []
    children = []
    for path in root.iterdir():
        if len(children) >= 4096:
            raise ValueError("runs directory exceeds entry limit")
        children.append(path)
    for path in sorted(children):
        try:
            _id(path.name)
            if path.is_symlink() or not path.is_dir():
                continue
            manifest = _manifest(path)
            keys = ("run_id", "status", "controller", "scenario", "texture", "seed", "parent_run_id",
                    "source_snapshot_id", "final_phase", "last_outcome", "metrics", "recorded_ticks")
            summary = {key: manifest.get(key) for key in keys}
            if isinstance(summary["scenario"], dict):
                summary["scenario"] = summary["scenario"].get("id")
            summaries.append(summary)
        except (ValueError, OSError):
            continue
    if not rebuild_index:
        return summaries
    index = _safe_path(root / "index.sqlite3")
    if storage_budget is not None:
        from .storage import StorageLimitError
        try:
            storage_budget.check(4 * 1024**2, path=index)
        except StorageLimitError:
            return summaries
    fd, name = tempfile.mkstemp(prefix=".index-", suffix=".sqlite3", dir=root)
    os.close(fd)
    temporary = Path(name)
    try:
        with closing(sqlite3.connect(temporary)) as database:
            database.execute("PRAGMA page_size=4096")
            database.execute("PRAGMA max_page_count=1024")
            database.execute("PRAGMA journal_mode=OFF")
            database.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, summary TEXT NOT NULL)")
            database.executemany("INSERT INTO runs VALUES (?, ?)", [(item["run_id"], json.dumps(item, allow_nan=False)) for item in summaries])
            database.commit()
        os.replace(temporary, index)
    finally:
        temporary.unlink(missing_ok=True)
    return summaries
