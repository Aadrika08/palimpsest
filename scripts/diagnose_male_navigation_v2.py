"""Bounded read-only diagnosis of the completed navigation-v2 development batch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import zipfile

from palimpsest import records


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "docs/plans/m7-navigation-v2-failure-diagnosis-v1.json"
PROTOCOL_SHA256 = "242fad46433241697bb7d7731e692cd1b42918b3788a8f816c6c8a9e9271b5e3"
MiB = 1024**2


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _constant(value):
    raise ValueError(f"nonfinite JSON value: {value}")


def load_protocol(path=PROTOCOL_PATH):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MiB:
        raise ValueError("diagnosis protocol must be one bounded regular file")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("diagnosis protocol hash differs")
    protocol = json.loads(payload, object_pairs_hook=_pairs, parse_constant=_constant)
    if protocol.get("schema") != "m7-navigation-v2-failure-diagnosis-protocol-v1":
        raise ValueError("unsupported diagnosis protocol")
    validate_protocol(protocol)
    return protocol


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _read_bytes(path, maximum, description):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError(f"expected one bounded regular {description}: {path}")
    return path.read_bytes()


def _read_json(path, maximum=MiB):
    return json.loads(_read_bytes(path, maximum, "JSON file"),
                      object_pairs_hook=_pairs, parse_constant=_constant)


def _hex_digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_protocol(protocol):
    if not isinstance(protocol, dict) or set(protocol) != {
        "analysis", "cases", "input", "limits", "qualification_claims", "schema", "scope", "status"
    }:
        raise ValueError("diagnosis protocol fields differ")
    if (protocol["schema"] != "m7-navigation-v2-failure-diagnosis-protocol-v1" or
            protocol["status"] != "prospective-frozen-before-trajectory-decode" or
            protocol["qualification_claims"] != []):
        raise ValueError("diagnosis protocol identity or claims differ")
    source = protocol["input"]
    if (not isinstance(source, dict) or source.get("expected_runs") != 24 or
            source.get("held_out_scene_ids_forbidden") != list(range(3120, 3128)) or
            not _hex_digest(source.get("development_index_sha256")) or
            type(source.get("expected_numeric_ticks")) is not int or source["expected_numeric_ticks"] <= 0 or
            type(source.get("expected_ledger_files")) is not int or source["expected_ledger_files"] <= 0 or
            type(source.get("expected_ledger_bytes")) is not int or source["expected_ledger_bytes"] <= 0):
        raise ValueError("diagnosis input contract differs")
    limits = protocol["limits"]
    if (limits != {"deadline_seconds": 300, "max_input_bytes": 3 * 1024**3,
                   "max_output_bytes": 16 * MiB, "min_free_bytes": 1024**3} or
            source["expected_ledger_bytes"] > limits["max_input_bytes"]):
        raise ValueError("diagnosis resource limits differ")
    analysis = protocol["analysis"]
    if (analysis.get("numeric_fields") != ["action", "control", "pose", "next_pose", "sensors", "simulation_time"] or
            analysis.get("arms") != ["old-corpus", "augmented"] or
            analysis.get("thresholds") != {"command_deadband": .05, "pair_divergence_absolute": 1e-6,
                                           "stall_step_metres": .002}):
        raise ValueError("diagnosis analysis contract differs")
    cases = protocol["cases"]
    combinations = {(scene, seed, arm) for scene in range(3110, 3114)
                    for seed in (10, 11, 12) for arm in analysis["arms"]}
    if not isinstance(cases, list) or len(cases) != 24:
        raise ValueError("diagnosis requires exactly 24 cases")
    seen_ids, seen_runs, observed = set(), set(), set()
    for case in cases:
        if (not isinstance(case, dict) or set(case) != {"arm", "id", "outcome", "run_id", "scene_seed", "ticks", "training_seed"} or
                case["id"] != f"dev-{case['scene_seed']}-seed-{case['training_seed']}-{case['arm']}" or
                not isinstance(case["run_id"], str) or len(case["run_id"]) != 32 or
                any(c not in "0123456789abcdef" for c in case["run_id"]) or
                case["outcome"] not in {"goal", "stalled", "time_limit"} or
                type(case["ticks"]) is not int or not 1 <= case["ticks"] <= 600 or
                case["scene_seed"] in source["held_out_scene_ids_forbidden"]):
            raise ValueError("invalid diagnosis case")
        seen_ids.add(case["id"]); seen_runs.add(case["run_id"])
        observed.add((case["scene_seed"], case["training_seed"], case["arm"]))
    if len(seen_ids) != 24 or len(seen_runs) != 24 or observed != combinations or sum(c["ticks"] for c in cases) != source["expected_numeric_ticks"]:
        raise ValueError("diagnosis cases are duplicated, missing or inconsistent")
    return protocol


def _deadline(deadline):
    if time.monotonic() > deadline:
        raise TimeoutError("diagnosis deadline exceeded")


def _safe_file(root, relative):
    parts = relative.split("/") if isinstance(relative, str) else []
    if (not isinstance(relative, str) or not relative or relative.startswith("/") or
            "\\" in relative or any(part in {"", ".", ".."} for part in parts)):
        raise ValueError("unsafe ledger path")
    root = Path(root).resolve()
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root):
        raise ValueError("ledger path escapes producer root")
    current = path
    while current != root:
        if current.is_symlink():
            raise ValueError("diagnosis input cannot contain symlinks")
        current = current.parent
    if not path.is_file():
        raise ValueError("diagnosis ledger file is missing")
    return path


def _file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _check_ledger(producer, ledger, protocol, deadline):
    if not isinstance(ledger, dict) or len(ledger) != protocol["input"]["expected_ledger_files"]:
        raise ValueError("diagnosis ledger count differs")
    total = 0
    for relative, pin in sorted(ledger.items()):
        _deadline(deadline)
        if (not isinstance(pin, dict) or set(pin) != {"bytes", "sha256"} or type(pin["bytes"]) is not int or
                pin["bytes"] < 0 or not _hex_digest(pin["sha256"])):
            raise ValueError("invalid diagnosis ledger pin")
        path = _safe_file(producer, relative)
        if path.stat().st_size != pin["bytes"] or _file_sha(path) != pin["sha256"]:
            raise ValueError(f"diagnosis ledger drift: {relative}")
        _deadline(deadline)
        total += pin["bytes"]
    if total != protocol["input"]["expected_ledger_bytes"] or total > protocol["limits"]["max_input_bytes"]:
        raise ValueError("diagnosis ledger bytes differ")
    return {"files": len(ledger), "bytes": total, "sha256": hashlib.sha256(_json_bytes(ledger)).hexdigest()}


def _load_index(producer, path, protocol):
    path = Path(path)
    payload = _read_bytes(path, 16 * MiB, "development index")
    if hashlib.sha256(payload).hexdigest() != protocol["input"]["development_index_sha256"]:
        raise ValueError("development index hash differs")
    index = json.loads(payload, object_pairs_hook=_pairs, parse_constant=_constant)
    run_root = Path(producer) / protocol["input"]["run_root_relative"]
    expected_cases = protocol["cases"]
    cases = [{key: row[key] for key in ("arm", "id", "outcome", "run_id", "scene_seed", "ticks", "training_seed")}
             for row in index.get("cases", [])]
    ledger = index.get("copied_root_raw_files")
    summary = index.get("reference_summary", {})
    if (index.get("status") != "completed-development-negative-gate" or
            index.get("producer_commit") != protocol["input"]["producer_commit"] or
            index.get("numeric_ticks") != protocol["input"]["expected_numeric_ticks"] or
            index.get("events") != protocol["input"]["expected_events"] or
            index.get("held_out_status") != "locked_pending_separate_review" or
            index.get("qualification_claims") != [] or cases != expected_cases or
            Path(index.get("output_root", "")).resolve() != run_root.resolve() or
            Path(index.get("copied_root_raw_files_base", "")).resolve() != Path(producer).resolve() or
            summary.get("copied_root_raw_ledger_entries") != protocol["input"]["expected_ledger_files"] or
            summary.get("copied_root_raw_ledger_bytes") != protocol["input"]["expected_ledger_bytes"] or
            not isinstance(ledger, dict)):
        raise ValueError("development index differs from diagnosis contract")
    return index, run_root


def _suffix(values):
    count = 0
    for value in reversed(values):
        if not value:
            break
        count += 1
    return count


def _sign_changes(values, deadband):
    signs = [1 if value > 0 else -1 for value in values if abs(value) > deadband]
    return sum(left != right for left, right in zip(signs, signs[1:]))


def expected_control(action):
    import numpy as np

    v, heading = np.asarray(action, dtype=np.float32)
    left, right = v - .5 * heading, v + .5 * heading
    maximum = max(abs(left), abs(right))
    if maximum > 1.:
        left, right = left / maximum, right / maximum
    return np.clip(np.asarray([left, right], dtype=np.float32), -1., 1.) * 2.


def _run_rows(result, case, ledger, producer, protocol, deadline):
    import numpy as np

    base = f"{protocol['input']['run_root_relative']}/{case['id']}"
    run_base = f"{base}/{case['run_id']}"
    consumed = [f"{base}/result.json", f"{run_base}/recording/manifest.json",
                f"{run_base}/recording/events.jsonl"]
    if any(relative not in ledger for relative in consumed):
        raise ValueError("consumed recording metadata is absent from the frozen ledger")
    manifest_path = _safe_file(producer, consumed[1])
    events_path = _safe_file(producer, consumed[2])
    manifest = _read_json(manifest_path, 4 * MiB)
    if events_path.stat().st_size > 16 * MiB:
        raise ValueError("recording event stream exceeds diagnosis bound")
    events = []
    with events_path.open("rb") as stream:
        for sequence, line in enumerate(stream):
            _deadline(deadline)
            if not line.endswith(b"\n"):
                raise ValueError("terminal event stream is torn")
            event = json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
            if event.get("sequence") != sequence or not isinstance(event.get("kind"), str):
                raise ValueError("event sequence differs")
            events.append(event)
    starts = [event for event in events if event["kind"] == "episode_started" and event.get("episode") == 0]
    chunks = [event for event in events if event["kind"] == "chunk"]
    if (manifest.get("status") != "completed" or manifest.get("recording_format") != records.FORMAT or
            manifest.get("run_id") != case["run_id"] or manifest.get("recorded_ticks") != case["ticks"] or
            manifest.get("recorded_chunks") != len(chunks) or manifest.get("recorded_events") != len(events) or len(starts) != 1):
        raise ValueError("recording manifest or initial world differs")
    world = starts[0].get("world")
    goal = np.asarray(world.get("goal") if isinstance(world, dict) else None, dtype=np.float64)
    if goal.shape not in {(2,), (3,)} or not np.isfinite(goal).all():
        raise ValueError("recording initial goal differs")
    goal = goal[:2]
    selected = {name: [] for name in protocol["analysis"]["numeric_fields"]}
    previous = -1
    for index, event in enumerate(chunks):
        _deadline(deadline)
        relative = f"{run_base}/recording/chunks/{index:06d}.npz"
        if relative not in ledger:
            raise ValueError("consumed recording chunk is absent from the frozen ledger")
        chunk = _safe_file(producer, relative)
        count, start = event.get("count"), event.get("start")
        if (event.get("path") != f"chunks/{index:06d}.npz" or event.get("episode") != 0 or
                type(count) is not int or not 1 <= count <= records.CHUNK_TICKS or type(start) is not int or start != previous + 1 or
                event.get("sha256") != ledger[relative]["sha256"] or set(selected) - set(event.get("arrays", {}))):
            raise ValueError("recording chunk contract differs")
        fields = event["arrays"]
        with zipfile.ZipFile(chunk) as archive:
            members = archive.infolist()
            if (len(members) != len(fields) or len({item.filename for item in members}) != len(members) or
                    {item.filename for item in members} != {f"{name}.npy" for name in fields} or
                    any(item.compress_type != zipfile.ZIP_STORED for item in members) or
                    sum(item.file_size for item in members) > records.MAX_CHUNK_BYTES + 65536):
                raise ValueError("recording chunk members differ")
            for name, description in fields.items():
                if (not records._NAME.fullmatch(name) or name in records._RESERVED or
                        not isinstance(description, dict) or set(description) != {"dtype", "shape"} or
                        not isinstance(description["dtype"], str) or not isinstance(description["shape"], list) or
                        any(type(size) is not int or size < 0 for size in description["shape"])):
                    raise ValueError("recording chunk metadata differs")
                with archive.open(f"{name}.npy") as stream:
                    version = np.lib.format.read_magic(stream)
                    if version not in {(1, 0), (2, 0)}:
                        raise ValueError("unsupported numeric member version")
                    reader = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                              else np.lib.format.read_array_header_2_0)
                    shape, _, dtype = reader(stream)
                    if list(shape) != [count, *description["shape"]] or dtype.str != description["dtype"]:
                        raise ValueError("recording member header differs")
        with np.load(chunk, allow_pickle=False) as archive:
            for name in selected:
                value = archive[name]
                description = event["arrays"][name]
                if (value.dtype.kind not in "biuf" or list(value.shape) != [count, *description.get("shape", [])] or
                        value.dtype.str != description.get("dtype") or not np.isfinite(value).all()):
                    raise ValueError(f"invalid selected numeric field: {name}")
                selected[name].append(value.copy())
        previous = start + count - 1
    arrays = {name: np.concatenate(values) for name, values in selected.items()}
    count = len(arrays["action"])
    if count != case["ticks"] or previous != count - 1:
        raise ValueError("recording tick count differs")
    expected_shapes = {"action": (count, 2), "control": (count, 2), "pose": (count, 3),
                       "next_pose": (count, 3), "sensors": (count, 4), "simulation_time": (count,)}
    if any(arrays[name].shape != shape for name, shape in expected_shapes.items()):
        raise ValueError("selected numeric shape differs")
    if (arrays["simulation_time"][0] < 0. or
            not np.allclose(np.diff(arrays["simulation_time"]), .02, rtol=0., atol=1e-9)):
        raise ValueError("simulation time is not the fixed contiguous grid")
    if count > 1 and not np.array_equal(arrays["pose"][1:], arrays["next_pose"][:-1]):
        raise ValueError("recorded pose continuity differs")
    projected = np.stack([expected_control(row) for row in arrays["action"]]).astype(np.float64)
    if not np.array_equal(arrays["control"], projected):
        raise ValueError("recorded wheel projection differs")
    contacts = arrays["sensors"][:, 0]
    if not np.isin(contacts, (0, 1)).all():
        raise ValueError("collision sensor is not boolean-valued")
    contacts = contacts.astype(bool)
    steps = np.linalg.norm(arrays["next_pose"][:, :2] - arrays["pose"][:, :2], axis=1)
    distances = np.concatenate((np.linalg.norm(arrays["pose"][:, :2] - goal, axis=1),
                                [np.linalg.norm(arrays["next_pose"][-1, :2] - goal)]))
    action = arrays["action"].astype(np.float64)
    deadband = protocol["analysis"]["thresholds"]["command_deadband"]
    stall_step = protocol["analysis"]["thresholds"]["stall_step_metres"]
    stall_like = (steps < stall_step) & (np.abs(action[:, 0]) > deadband)
    outcome = result.get("outcome", {}).get("reason")
    if (result.get("status") != "completed-recording" or result.get("executed_ticks") != count or
            result.get("case") != {key: case[key] for key in ("id", "scene_seed", "training_seed", "arm")} or
            outcome != case["outcome"]):
        raise ValueError("owner result differs from diagnosis case")
    terminal = bool(contacts[-1])
    terminal_class = ("goal" if outcome == "goal" else
                      f"terminal-{'contact' if terminal else 'clear'}-{'stall' if outcome == 'stalled' else 'time-limit'}")
    row = {
        "case_id": case["id"], "run_id": case["run_id"], "scene_seed": case["scene_seed"],
        "training_seed": case["training_seed"], "arm": case["arm"], "outcome": outcome, "ticks": count,
        "terminal_class": terminal_class,
        "initial_goal_distance_metres": float(distances[0]),
        "minimum_goal_distance_metres": float(distances.min()),
        "final_goal_distance_metres": float(distances[-1]),
        "best_progress_metres": float(distances[0] - distances.min()),
        "net_progress_metres": float(distances[0] - distances[-1]),
        "regression_from_best_metres": float(distances[-1] - distances.min()),
        "path_length_metres": float(steps.sum()),
        "contact_ticks": int(contacts.sum()),
        "terminal_contact_suffix_ticks": _suffix(contacts.tolist()),
        "terminal_stall_like_suffix_ticks": _suffix(stall_like.tolist()),
        "reverse_command_ticks": int((action[:, 0] < -deadband).sum()),
        "stopped_command_ticks": int((np.abs(action[:, 0]) <= deadband).sum()),
        "velocity_sign_changes": _sign_changes(action[:, 0].tolist(), deadband),
        "heading_sign_changes": _sign_changes(action[:, 1].tolist(), deadband),
        "mean_abs_velocity_command": float(np.abs(action[:, 0]).mean()),
        "mean_abs_heading_command": float(np.abs(action[:, 1]).mean()),
    }
    return row, action


def _aggregate(runs, name):
    values = {}
    for row in runs:
        key = str(row[name])
        values[key] = values.get(key, 0) + 1
    return values


def analyze(producer, index_path, protocol, *, deadline=None):
    validate_protocol(protocol)
    started = time.monotonic()
    deadline = started + protocol["limits"]["deadline_seconds"] if deadline is None else deadline
    producer = Path(producer).resolve()
    _deadline(deadline)
    index, _ = _load_index(producer, index_path, protocol)
    before = _check_ledger(producer, index["copied_root_raw_files"], protocol, deadline)
    runs, actions = [], {}
    for case in protocol["cases"]:
        _deadline(deadline)
        result_relative = f"{protocol['input']['run_root_relative']}/{case['id']}/result.json"
        if result_relative not in index["copied_root_raw_files"]:
            raise ValueError("consumed owner result is absent from the frozen ledger")
        result = _read_json(_safe_file(producer, result_relative), 4 * MiB)
        row, action = _run_rows(result, case, index["copied_root_raw_files"], producer, protocol, deadline)
        runs.append(row); actions[(case["scene_seed"], case["training_seed"], case["arm"])] = action
    pairs = []
    threshold = protocol["analysis"]["thresholds"]["pair_divergence_absolute"]
    for scene in range(3110, 3114):
        for seed in (10, 11, 12):
            old = actions[(scene, seed, "old-corpus")]; augmented = actions[(scene, seed, "augmented")]
            common = min(len(old), len(augmented)); difference = abs(old[:common] - augmented[:common])
            divergent = (difference.max(axis=1) > threshold).nonzero()[0]
            old_row = next(row for row in runs if row["scene_seed"] == scene and row["training_seed"] == seed and row["arm"] == "old-corpus")
            augmented_row = next(row for row in runs if row["scene_seed"] == scene and row["training_seed"] == seed and row["arm"] == "augmented")
            pairs.append({"scene_seed": scene, "training_seed": seed, "common_ticks": common,
                          "first_action_divergence_tick": int(divergent[0]) if len(divergent) else None,
                          "mean_absolute_action_difference": float(difference.mean()),
                          "maximum_absolute_action_difference": float(difference.max()),
                          "old_outcome": old_row["outcome"], "augmented_outcome": augmented_row["outcome"],
                          "old_terminal_class": old_row["terminal_class"],
                          "augmented_terminal_class": augmented_row["terminal_class"]})
    after = _check_ledger(producer, index["copied_root_raw_files"], protocol, deadline)
    if before != after:
        raise ValueError("diagnosis input changed during analysis")
    current_index = _read_bytes(index_path, 16 * MiB, "development index")
    if hashlib.sha256(current_index).hexdigest() != protocol["input"]["development_index_sha256"]:
        raise ValueError("development index changed during analysis")
    report = {
        "schema": "m7-navigation-v2-failure-diagnosis-v1",
        "status": "completed-read-only-diagnosis",
        "protocol_sha256": hashlib.sha256(_json_bytes(protocol)).hexdigest(),
        "development_index_sha256": protocol["input"]["development_index_sha256"],
        "input_before": before, "input_after": after,
        "numeric_ticks": sum(row["ticks"] for row in runs), "runs": runs, "pairs": pairs,
        "summary": {"by_arm": _aggregate(runs, "arm"), "by_training_seed": _aggregate(runs, "training_seed"),
                    "by_outcome": _aggregate(runs, "outcome"), "by_terminal_class": _aggregate(runs, "terminal_class")},
        "elapsed_seconds": time.monotonic() - started,
        "held_out_accessed": False, "model_or_simulator_executed": False,
        "r3_complete": False, "qualification_claims": [],
        "scope": protocol["scope"],
    }
    if len(_json_bytes(report)) > protocol["limits"]["max_output_bytes"]:
        raise ValueError("diagnosis output exceeds fixed limit")
    return report


def _write_output(output, name, payload, maximum):
    if not isinstance(payload, bytes):
        payload = _json_bytes(payload) + b"\n"
    existing = sum(path.stat().st_size for path in output.iterdir() if path.is_file())
    if existing + len(payload) > maximum:
        raise ValueError("diagnosis output exceeds fixed limit")
    path = output / name
    temporary = output / f".{name}.tmp"
    if path.exists() or path.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise ValueError(f"diagnosis output already exists: {name}")
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(output, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def _prepare_output(producer, index_path, output, protocol):
    producer, index_path, output = Path(producer).resolve(), Path(index_path).resolve(), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("diagnosis requires a fresh output directory")
    current = output.parent
    while current != current.parent:
        if current.is_symlink():
            raise ValueError("diagnosis output parent cannot be a symlink")
        current = current.parent
    resolved = output.resolve(strict=False)
    if (resolved == producer or resolved.is_relative_to(producer) or producer.is_relative_to(resolved) or
            resolved == index_path or index_path.is_relative_to(resolved)):
        raise ValueError("diagnosis output overlaps an input")
    output.parent.mkdir(parents=True, exist_ok=True)
    parent = output.parent.resolve()
    if shutil.disk_usage(parent).free < protocol["limits"]["min_free_bytes"]:
        raise ValueError("diagnosis free-space floor is unavailable")
    output.mkdir()
    return producer, index_path, output.resolve()


def execute(producer, index_path, output, protocol, *, protocol_payload=None):
    validate_protocol(protocol)
    payload = _json_bytes(protocol) if protocol_payload is None else protocol_payload
    if (not isinstance(payload, bytes) or len(payload) > MiB or
            json.loads(payload, object_pairs_hook=_pairs, parse_constant=_constant) != protocol):
        raise ValueError("diagnosis protocol payload differs")
    producer, index_path, output = _prepare_output(producer, index_path, output, protocol)
    try:
        _write_output(output, "protocol.json", payload, protocol["limits"]["max_output_bytes"])
        source_before = _file_sha(Path(__file__))
        report = analyze(producer, index_path, protocol)
        source_after = _file_sha(Path(__file__))
        if source_before != source_after:
            raise ValueError("diagnosis source changed during analysis")
        report["protocol_sha256"] = hashlib.sha256(payload).hexdigest()
        report["analysis_source_sha256"] = source_after
        report["invocation"] = {"producer_root": str(producer), "development_index": str(index_path),
                                "output": str(output)}
        _write_output(output, "report.json", report, protocol["limits"]["max_output_bytes"])
        return report
    except BaseException as error:
        (output / "report.json").unlink(missing_ok=True)
        failure = {"schema": "m7-navigation-v2-failure-diagnosis-v1", "status": "failed-diagnostic",
                   "error": {"type": type(error).__name__, "message": str(error)[:2048]},
                   "protocol_sha256": hashlib.sha256(payload).hexdigest(), "qualification_claims": [],
                   "r3_complete": False}
        _write_output(output, "failure.json", failure, protocol["limits"]["max_output_bytes"])
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-root", type=Path, required=True)
    parser.add_argument("--index", type=Path, default=ROOT / "docs/reports/m7-navigation-development-v2.json")
    parser.add_argument("--protocol", type=Path, default=PROTOCOL_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        protocol = load_protocol(args.protocol)
        report = execute(args.producer_root, args.index, args.output, protocol,
                         protocol_payload=args.protocol.read_bytes())
        print(json.dumps({"status": report["status"], "runs": len(report["runs"]),
                          "numeric_ticks": report["numeric_ticks"], "output": str(args.output)},
                         sort_keys=True, allow_nan=False))
        return 0
    except BaseException as error:
        print(json.dumps({"status": "failed-diagnostic", "error": str(error)[:2048]},
                         sort_keys=True, allow_nan=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
