"""One-pass recorded-development output-support audit for six frozen checkpoints."""
import argparse
import hashlib
import importlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import sys
import time
from types import SimpleNamespace
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

PROTOCOL_PATH = ROOT / "docs/plans/m7-navigation-v2-checkpoint-support-v1.json"
PROTOCOL_SHA256 = "ef1d2e1b86028d1bd360e0bb149610043287ecd3f6e735ce6d2d90c5f3ac2f0b"
TEST_PATH = ROOT / "tests/test_male_navigation_v2_checkpoint_support.py"
MiB = 1024**2
SOURCE_FILES = {
    "src/palimpsest/__init__.py": "palimpsest",
    "scripts/prepare_male_navigation_v2.py": "prepare_male_navigation_v2",
    "scripts/train_male_navigation_v2.py": None,
    "scripts/train_male_reduced.py": "train_male_reduced",
    "src/palimpsest/artifacts.py": "palimpsest.artifacts",
    "src/palimpsest/male_model.py": "palimpsest.male_model",
    "src/palimpsest/male_navigation_research.py": "palimpsest.male_navigation_research",
    "src/palimpsest/male_policy.py": "palimpsest.male_policy",
    "src/palimpsest/male_research.py": "palimpsest.male_research",
    "src/palimpsest/records.py": "palimpsest.records",
    "src/palimpsest/storage.py": "palimpsest.storage",
}
BEHAVIOR_MODULES = {path: module for path, module in SOURCE_FILES.items() if module is not None}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _deadline(deadline, message="checkpoint-support audit exceeded its 180-second internal deadline"):
    if time.monotonic() > deadline:
        raise TimeoutError(message)


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def verify_behavior_sources(protocol, deadline):
    expected = protocol.get("reader_sources")
    if not isinstance(expected, dict) or set(expected) != set(SOURCE_FILES):
        raise ValueError("exact local behavior-source roster required")
    observed = {}
    for name, digest in expected.items():
        path = ROOT / name
        if (not isinstance(digest, str) or len(digest) != 64 or path.is_symlink() or
                not path.is_file() or path.resolve() != path.absolute() or path.stat().st_size > 8 * MiB):
            raise ValueError("bounded regular behavior source required: " + name)
        payload = bytearray()
        with path.open("rb") as stream:
            while True:
                _deadline(deadline)
                block = stream.read(min(MiB, 8 * MiB - len(payload) + 1))
                if not block:
                    break
                payload.extend(block)
                if len(payload) > 8 * MiB:
                    raise ValueError("behavior source exceeds cap: " + name)
        observed[name] = _sha(payload)
        if observed[name] != digest:
            raise ValueError("behavior source differs: " + name)
    return observed


def load_behavior(protocol):
    if set(protocol.get("reader_sources", {})) != set(SOURCE_FILES):
        raise ValueError("exact local behavior-source roster required")
    modules = []
    for path, name in BEHAVIOR_MODULES.items():
        module = importlib.import_module(name)
        if Path(module.__file__).absolute() != (ROOT / path).absolute():
            raise ValueError("behavior module resolved outside audit worktree: " + name)
        modules.append(module)
    by_name = {module.__name__: module for module in modules}
    return SimpleNamespace(
        artifacts=by_name["palimpsest.artifacts"],
        research=by_name["palimpsest.male_navigation_research"],
        male_policy=by_name["palimpsest.male_policy"],
        data_reader=by_name["prepare_male_navigation_v2"],
        loss_for=by_name["train_male_reduced"].loss_for,
        modules=tuple(modules),
    )


def _layout_root(path, suffix, message):
    path, suffix = _path(path), Path(suffix)
    root = path.parents[len(suffix.parts) - 1]
    if root / suffix != path:
        raise ValueError(message)
    return root


def admit_candidates(protocol, index, research):
    graph_root = _layout_root(protocol["immutable_inputs"]["graph_manifest"]["path"],
                              "data/manifests/malecns-reduced-neighborhood-v1.json",
                              "exact common frozen training root required")
    cell_root = _layout_root(protocol["immutable_inputs"]["cell_source"]["path"],
                             "upstream/fly-gym/models/connectome_rnn_model.py",
                             "exact common frozen training root required")
    if graph_root != cell_root:
        raise ValueError("exact common frozen training root required")
    runs_root = graph_root / "runs"
    for item in protocol["checkpoints"] + protocol["pair_reports"]:
        try:
            relative = _path(item["path"]).relative_to(runs_root)
        except (KeyError, ValueError):
            raise ValueError("exact frozen training artifact root required") from None
        if not relative.parts:
            raise ValueError("exact frozen training artifact root required")
    assets = _layout_root(protocol["immutable_inputs"]["graph"]["path"],
                          "male-reduced-v1/source-graph.json", "exact frozen graph asset root required")
    return research._admit(graph_root, assets, index)


def read_pin(pin, cap, deadline=math.inf):
    if (not isinstance(pin, dict) or set(pin) < {"path", "bytes", "sha256"} or
            type(pin["bytes"]) is not int or not 0 < pin["bytes"] <= cap or
            not isinstance(pin["sha256"], str) or len(pin["sha256"]) != 64):
        raise ValueError("bounded file pin required")
    path = _path(pin["path"])
    if path.is_symlink() or not path.is_file() or path.resolve() != path.absolute():
        raise ValueError("pinned input must be a regular non-symlink file")
    if path.stat().st_size != pin["bytes"]:
        raise ValueError("pinned input differs: " + str(path))
    digest = hashlib.sha256(); payload = bytearray()
    with path.open("rb") as stream:
        while True:
            _deadline(deadline)
            block = stream.read(min(MiB, cap - len(payload) + 1))
            if not block:
                break
            payload.extend(block)
            if len(payload) > cap:
                raise ValueError("pinned input exceeds cap")
            digest.update(block)
    if len(payload) != pin["bytes"] or digest.hexdigest() != pin["sha256"]:
        raise ValueError("pinned input differs: " + str(path))
    return bytes(payload)


def selected_budget(epoch, rows, windows):
    if any(type(value) is not int or value <= 0 for value in (epoch, rows, windows)):
        raise ValueError("positive integer budget fields required")
    return {"epoch": epoch, "row_presentations": epoch * rows, "optimizer_updates": epoch * windows}


def validate_budget_accounting(protocol):
    expected_full = {
        "old_corpus": {"rows_per_epoch": 2117, "windows_per_epoch": 72, "epochs": 20,
                       "row_presentations": 42340, "optimizer_updates": 1440},
        "augmented": {"rows_per_epoch": 7197, "windows_per_epoch": 236, "epochs": 20,
                      "row_presentations": 143940, "optimizer_updates": 4720},
    }
    expected_selected = []
    by_seed = {}
    for item in protocol.get("checkpoints", []):
        by_seed.setdefault(item.get("training_seed"), {})[item.get("arm")] = item.get("selected_epoch")
    for seed in (10, 11, 12):
        values = by_seed.get(seed, {})
        expected_selected.append({
            "training_seed": seed,
            "old_corpus": selected_budget(values.get("old-corpus"), 2117, 72),
            "augmented": selected_budget(values.get("augmented"), 7197, 236),
        })
    accounting = protocol.get("budget_accounting", {})
    if accounting.get("full_fit") != expected_full or accounting.get("selected_checkpoints") != expected_selected:
        raise ValueError("frozen budget accounting differs")


def validate_protocol(protocol):
    if (not isinstance(protocol, dict) or protocol.get("id") != "M7-NAV-CHECKPOINT-SUPPORT-V1" or
            protocol.get("version") != 1 or protocol.get("base_commit") !=
            "c8ee6a5bf1f50476412f17b0928c18bdec57ec10" or
            protocol.get("attempt_contract", {}).get("actual_invocations") != 1 or
            protocol["attempt_contract"].get("retry_after_failure") is not False or
            not isinstance(protocol["attempt_contract"].get("durable_reservation"), str) or
            not isinstance(protocol["attempt_contract"].get("output_parent"), str) or
            protocol["attempt_contract"].get("outer_supervisor") != {
                "program": "/usr/bin/timeout", "arguments": ["--signal=TERM", "210s"],
                "through_return_seconds": 210} or
            set(protocol.get("reader_sources", {})) != set(SOURCE_FILES) or
            protocol.get("limits") != {"internal_seconds": 180, "normal_through_return_seconds": 210,
                "output_bytes": 16 * MiB, "log_bytes_each": MiB, "minimum_free_bytes": 1024**3,
                "rss_budget_bytes": 1024**3, "input_file_cap_bytes": 8 * MiB,
                "model_count": 6, "source_count": 4}):
        raise ValueError("frozen checkpoint-support protocol differs")
    development = protocol.get("recorded_development", {})
    if (development.get("rows"), development.get("sources"), development.get("window"),
            development.get("windows_per_model"), development.get("models"),
            development.get("total_rows"), development.get("total_windows")) != (1228, 4, 32, 39, 6, 7368, 234):
        raise ValueError("frozen recorded-development workload differs")
    expected = [(seed, arm) for seed in (10, 11, 12) for arm in ("old-corpus", "augmented")]
    if [(item.get("training_seed"), item.get("arm")) for item in protocol.get("checkpoints", [])] != expected:
        raise ValueError("exact six ordered checkpoints required")
    forbidden = ("3120", "3121", "3122", "3123", "3124", "3125", "3126", "3127",
                 "m7-navigation-development-v2-e3f9a47")
    paths = [item.get("path", "") for item in protocol["immutable_inputs"].values()]
    paths += [item.get("path", "") for item in protocol["checkpoints"] + protocol["pair_reports"]]
    if any(token in path for token in forbidden for path in paths):
        raise ValueError("held-out or consumed development-run path is forbidden")
    validate_budget_accounting(protocol)
    return protocol


def load_protocol(path=PROTOCOL_PATH):
    raw = Path(path).read_bytes()
    if _sha(raw) != PROTOCOL_SHA256:
        raise ValueError("checkpoint-support protocol bytes changed")
    return validate_protocol(json.loads(raw))


def load_execution_manifest(path, expected_sha256, output, protocol=None):
    path = Path(path)
    if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or path.is_symlink() or
            not path.is_file() or path.resolve() != path.absolute() or path.stat().st_size > MiB):
        raise ValueError("execution manifest pin or path differs")
    raw = path.read_bytes()
    if _sha(raw) != expected_sha256:
        raise ValueError("execution manifest bytes differ")
    value = json.loads(raw)
    protocol = load_protocol() if protocol is None else protocol
    if (not isinstance(value, dict) or set(value) != {"schema", "attempt", "retry_allowed", "protocol_sha256",
            "script_sha256", "test_sha256", "behavior_sources", "outer_timeout_seconds", "outer_supervisor", "output"} or
            value.get("schema") != "m7-navigation-v2-checkpoint-support-execution-manifest-v1" or
            value.get("attempt") != 1 or value.get("retry_allowed") is not False or
            value.get("protocol_sha256") != PROTOCOL_SHA256 or
            value.get("script_sha256") != _sha(Path(__file__).read_bytes()) or
            value.get("test_sha256") != _sha(TEST_PATH.read_bytes()) or
            value.get("behavior_sources") != protocol["reader_sources"] or
            value.get("outer_timeout_seconds") != protocol["limits"]["normal_through_return_seconds"] or
            value.get("outer_supervisor") != protocol["attempt_contract"]["outer_supervisor"]):
        raise ValueError("execution manifest source or protocol binding differs")
    if value.get("output") != str(Path(output).absolute()):
        raise ValueError("execution output differs")
    return value


def model_key(seed, arm):
    if type(seed) is not int or seed not in (10, 11, 12) or arm not in ("old-corpus", "augmented"):
        raise ValueError("fixed seed and arm required")
    return f"seed-{seed}/{arm}"


def component_summary(values, source_lengths, deadband, quantiles):
    if (not isinstance(values, np.ndarray) or values.dtype != np.float32 or values.ndim != 1 or
            not np.isfinite(values).all()):
        raise ValueError("component values must be finite float32 vector")
    if (not isinstance(source_lengths, list) or any(type(length) is not int or length <= 0 for length in source_lengths)
            or sum(source_lengths) != len(values)):
        raise ValueError("component source lengths differ")
    if type(deadband) not in (int, float) or not math.isfinite(deadband) or deadband <= 0:
        raise ValueError("positive finite deadband required")
    if (not isinstance(quantiles, list) or not quantiles or any(type(q) not in (int, float) or not 0 <= q <= 1
                                                               for q in quantiles)):
        raise ValueError("bounded quantiles required")
    counts = {"negative": int((values < -deadband).sum()),
              "deadband": int((np.abs(values) <= deadband).sum()),
              "positive": int((values > deadband).sum())}
    changes = 0
    start = 0
    for length in source_lengths:
        part = values[start:start + length]
        signs = np.sign(part[np.abs(part) > deadband])
        changes += int((signs[1:] != signs[:-1]).sum())
        start += length
    return {
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "mean": float(values.astype(np.float64).mean()),
        "standard_deviation": float(values.astype(np.float64).std()),
        "quantiles": [float(value) for value in np.quantile(values.astype(np.float64), quantiles)],
        "sign_counts": counts,
        "within_source_sign_changes": changes,
    }


def support_classification(target, output):
    target_signs = target.get("sign_counts", {})
    output_signs = output.get("sign_counts", {})
    if not target_signs.get("negative") or not target_signs.get("positive"):
        return "target_support_absent"
    if not output_signs.get("negative") or not output_signs.get("positive"):
        return "checkpoint_sign_missing"
    if output.get("within_source_sign_changes") == 0:
        return "checkpoint_signs_present_no_switch"
    return "checkpoint_switches"


def validate_documents(protocol, index, data_manifest):
    if (index.get("held_out_status") != "locked_unopened" or index.get("qualification_claims") != [] or
            any(data_manifest.get("arms", {}).get(arm, {}).get("held_out") != [] for arm in ("old", "augmented"))):
        raise ValueError("held-out inputs must remain locked and empty")
    models = index.get("models", [])
    if [(item.get("training_seed"), item.get("arm")) for item in models] != [
            (item["training_seed"], item["arm"]) for item in protocol["checkpoints"]]:
        raise ValueError("exact six ordered model candidates required")
    published = {}
    reports = {item["training_seed"]: item for item in protocol["pair_reports"]}
    for candidate, frozen in zip(models, protocol["checkpoints"], strict=True):
        checkpoint = candidate.get("checkpoint", {})
        path = checkpoint.get("path")
        if (candidate.get("selected_epoch") != frozen["selected_epoch"] or
                checkpoint.get("size_bytes") != frozen["bytes"] or checkpoint.get("sha256") != frozen["sha256"] or
                not isinstance(path, str) or not frozen["path"].endswith("/" + path)):
            raise ValueError("selected checkpoint identity differs")
        report, frozen_report = candidate.get("report", {}), reports[frozen["training_seed"]]
        if (report.get("size_bytes") != frozen_report["bytes"] or report.get("sha256") != frozen_report["sha256"] or
                not isinstance(report.get("path"), str) or not frozen_report["path"].endswith("/" + report["path"])):
            raise ValueError("pair report identity differs")
        value = candidate.get("selected_recorded_dev")
        if (not isinstance(value, dict) or value.get("ticks") != protocol["recorded_development"]["rows"] or
                any(type(value.get(name)) not in (int, float) or not math.isfinite(value[name])
                    for name in ("loss", "velocity_mae", "wrapped_heading_mae_radians"))):
            raise ValueError("published selected-development metric differs")
        published[model_key(frozen["training_seed"], frozen["arm"])] = value
    return published


def validate_development(protocol, episodes):
    expected = protocol["recorded_development"]["sequence_order"]
    if not isinstance(episodes, list) or len(episodes) != len(expected):
        raise ValueError("exact recorded-development source roster required")
    targets = []
    for episode, frozen in zip(episodes, expected, strict=True):
        features, values = episode.get("features"), episode.get("targets")
        if (episode.get("run_id") != frozen["run_id"] or episode.get("episode") != 0 or
                not isinstance(features, np.ndarray) or features.dtype != np.float32 or features.shape != (frozen["rows"], 388) or
                not isinstance(values, np.ndarray) or values.dtype != np.float32 or values.shape != (frozen["rows"], 2) or
                not np.isfinite(features).all() or not np.isfinite(values).all() or
                _sha(features.tobytes() + values.tobytes()) != frozen["feature_target_sha256"]):
            raise ValueError("recorded-development source bytes differ")
        targets.append(values.copy())
    if sum(len(value) for value in targets) != protocol["recorded_development"]["rows"]:
        raise ValueError("recorded-development row count differs")
    return targets


def _array_list(values, shapes, name):
    if not isinstance(values, list) or len(values) != len(shapes):
        raise ValueError(name + " source roster differs")
    result = []
    for value, rows in zip(values, shapes, strict=True):
        if (not isinstance(value, np.ndarray) or value.dtype != np.float32 or value.shape != (rows, 2) or
                not np.isfinite(value).all()):
            raise ValueError(name + " arrays must be finite float32 rows")
        result.append(value)
    return result


def analyze_outputs(protocol, targets, outputs, published):
    lengths = [item["rows"] for item in protocol["recorded_development"]["sequence_order"]]
    if len(targets) != len(lengths):
        raise ValueError("target source roster differs")
    targets = _array_list(targets, lengths, "target")
    joined_targets = np.concatenate(targets)
    deadband = protocol["metrics"]["deadband"]
    quantiles = protocol["metrics"]["quantiles"]
    target_summary = {
        "velocity": component_summary(joined_targets[:, 0], lengths, deadband, quantiles),
        "heading": component_summary(joined_targets[:, 1], lengths, deadband, quantiles),
    }
    arrays = {f"targets_source_{number:03d}": value for number, value in enumerate(targets)}
    model_rows, joined_actions = [], {}
    expected_rows = protocol["recorded_development"]["rows"]
    expected_windows = protocol["recorded_development"]["windows_per_model"]
    for frozen in protocol["checkpoints"]:
        key = model_key(frozen["training_seed"], frozen["arm"])
        value = outputs.get(key)
        if (not isinstance(value, dict) or value.get("rows") != expected_rows or
                value.get("windows") != expected_windows):
            raise ValueError("checkpoint row/window count differs")
        actions = _array_list(value.get("actions"), lengths, "action")
        raw = _array_list(value.get("raw_outputs"), lengths, "raw output")
        if value.get("scaling_exact") is not True:
            raise ValueError("checkpoint action differs from exact tanh scaling")
        if value.get("metrics") != published.get(key):
            raise ValueError("checkpoint published metric reproduction differs")
        action = np.concatenate(actions)
        raw_output = np.concatenate(raw)
        joined_actions[key] = action
        velocity = component_summary(action[:, 0], lengths, deadband, quantiles)
        heading = component_summary(action[:, 1], lengths, deadband, quantiles)
        raw_velocity = component_summary(raw_output[:, 0], lengths, deadband, quantiles)
        raw_heading = component_summary(raw_output[:, 1], lengths, deadband, quantiles)
        velocity["support"] = support_classification(target_summary["velocity"], velocity)
        heading["support"] = support_classification(target_summary["heading"], heading)
        stream = hashlib.sha256()
        prefix = f"seed_{frozen['training_seed']}_{frozen['arm'].replace('-', '_')}"
        for number, (action_part, raw_part) in enumerate(zip(actions, raw, strict=True)):
            stream.update(action_part.tobytes()); stream.update(raw_part.tobytes())
            arrays[f"{prefix}_actions_source_{number:03d}"] = action_part
            arrays[f"{prefix}_raw_source_{number:03d}"] = raw_part
        model_rows.append({
            "training_seed": frozen["training_seed"], "arm": frozen["arm"],
            "selected_epoch": frozen["selected_epoch"], "rows": expected_rows,
            "windows": expected_windows, "metrics": value["metrics"],
            "velocity": velocity, "heading": heading,
            "raw_velocity": raw_velocity, "raw_heading": raw_heading,
            "reverse_command_ticks": int((action[:, 0] < -deadband).sum()),
            "stopped_command_ticks": int((np.abs(action[:, 0]) <= deadband).sum()),
            "tanh_scaling_exact": True, "output_stream_sha256": stream.hexdigest(),
        })
    if set(outputs) != {model_key(item["training_seed"], item["arm"]) for item in protocol["checkpoints"]}:
        raise ValueError("unexpected checkpoint output")
    pairs = []
    for seed in (10, 11, 12):
        old = joined_actions[model_key(seed, "old-corpus")]
        augmented = joined_actions[model_key(seed, "augmented")]
        difference = np.abs(old.astype(np.float64) - augmented.astype(np.float64))
        differing = np.flatnonzero(np.any(old != augmented, axis=1))
        pairs.append({"training_seed": seed,
                      "first_differing_recorded_development_row": int(differing[0]) if len(differing) else None,
                      "mean_absolute_action_difference": float(difference.mean()),
                      "maximum_absolute_action_difference": float(difference.max())})
    stream = io.BytesIO()
    np.savez(stream, **arrays)
    payload = stream.getvalue()
    if len(payload) > protocol["limits"]["output_bytes"]:
        raise ValueError("compact output exceeds frozen cap")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if any(item.compress_type != zipfile.ZIP_STORED for item in archive.infolist()):
            raise ValueError("compact arrays must be uncompressed")
    report = {
        "schema": "m7-navigation-v2-checkpoint-support-v1",
        "status": "completed-checkpoint-support-audit",
        "protocol_sha256": PROTOCOL_SHA256,
        "rows": expected_rows * len(model_rows), "windows": expected_windows * len(model_rows),
        "targets": target_summary, "models": model_rows, "pairs": pairs,
        "compact_arrays": {"bytes": len(payload), "sha256": _sha(payload), "members": len(arrays)},
        "budget_accounting": protocol["budget_accounting"],
        "held_out_accessed": False, "simulator_executed": False, "training_executed": False,
        "fresh_scene_generated": False, "r3_complete": False, "qualification_claims": [],
        "interpretation": "Recorded-development output-support description; not causal or fresh-scene capability evidence.",
    }
    return report, payload


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_pending(path, payload):
    pending = path.with_name(path.name + ".pending")
    with pending.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    return pending


def _atomic_write(path, payload):
    pending = _write_pending(path, payload)
    pending.replace(path)
    _fsync_directory(path.parent)


def prepare_output_parent(output):
    output = Path(output).absolute()
    expected = ROOT / "runs"
    if output.parent != expected:
        raise ValueError("checkpoint-support output must use the exact audit runs directory")
    if not expected.exists():
        expected.mkdir(parents=False, exist_ok=False)
        _fsync_directory(ROOT)
    if expected.is_symlink() or not expected.is_dir() or expected.resolve() != expected.absolute():
        raise ValueError("checkpoint-support runs directory must be a regular non-symlink directory")


def reserve_attempt(output, receipt):
    output = Path(output)
    if output.exists():
        raise FileExistsError("checkpoint-support attempt already consumed")
    output.mkdir(parents=False, exist_ok=False)
    _fsync_directory(output.parent)
    payload = canonical(receipt)
    _atomic_write(output / "attempt.json", payload)
    return payload


def check_output_cap(protocol, *payloads):
    if sum(len(payload) for payload in payloads) > protocol["limits"]["output_bytes"]:
        raise ValueError("checkpoint-support publication exceeds frozen cap")


def final_prepublication_checks(protocol, deadline, return_deadline, *payloads):
    check_output_cap(protocol, *payloads)
    _deadline(deadline)
    _check_rss(protocol)
    _deadline(return_deadline, "checkpoint-support audit exceeded its 210-second through-return deadline")


def publish_success(output, protocol_payload, arrays_payload, report, execution, fault=None):
    output = Path(output)
    attempt = output / "attempt.json"
    if (not output.is_dir() or attempt.is_symlink() or not attempt.is_file() or
            (output / "failure.json").exists() or (output / "report.json").exists()):
        raise ValueError("durable checkpoint-support attempt reservation required")
    try:
        _atomic_write(output / "protocol.json", protocol_payload)
        _atomic_write(output / "outputs.npz", arrays_payload)
        _atomic_write(output / "execution.json", canonical(execution))
        pending = _write_pending(output / "report.json", canonical(report))
        _fsync_directory(output)
        if fault == "final_rename":
            raise OSError("injected publication failure")
    except BaseException:
        for name in ("report.json", "execution.json", "report.json.pending", "execution.json.pending"):
            try:
                (output / name).unlink(missing_ok=True)
            except OSError:
                pass
        try:
            _fsync_directory(output)
        except OSError:
            pass
        raise
    try:
        pending.replace(output / "report.json")
    except BaseException:
        for name in ("report.json", "execution.json", "report.json.pending", "execution.json.pending"):
            try:
                (output / name).unlink(missing_ok=True)
            except OSError:
                pass
        try:
            _fsync_directory(output)
        except OSError:
            pass
        raise


def publish_failure(output, failure):
    output = Path(output)
    prepare_output_parent(output)
    if not output.exists():
        reserve_attempt(output, {"schema": "m7-navigation-v2-checkpoint-support-attempt-v1",
            "status": "attempt-reserved-by-failure", "attempt": 1, "retry_allowed": False,
            "protocol_sha256": PROTOCOL_SHA256,
            "execution_manifest_sha256": failure.get("execution_manifest_sha256")})
    elif not (output / "attempt.json").is_file():
        _atomic_write(output / "attempt.json", canonical({
            "schema": "m7-navigation-v2-checkpoint-support-attempt-v1",
            "status": "attempt-reserved-by-failure", "attempt": 1, "retry_allowed": False,
            "protocol_sha256": PROTOCOL_SHA256,
            "execution_manifest_sha256": failure.get("execution_manifest_sha256")}))
    if (output / "report.json").exists() or (output / "execution.json").exists():
        raise ValueError("completion marker exists; failure publication refused")
    path = output / "failure.json"
    if path.exists():
        raise FileExistsError("failure evidence already exists")
    _atomic_write(path, canonical(failure))


def _fingerprints(protocol, deadline):
    observed = {}
    for name, pin in protocol["immutable_inputs"].items():
        observed[name] = _sha(read_pin(pin, protocol["limits"]["input_file_cap_bytes"], deadline))
    for item in protocol["checkpoints"]:
        observed[model_key(item["training_seed"], item["arm"])] = _sha(
            read_pin(item, protocol["limits"]["input_file_cap_bytes"], deadline))
    for item in protocol["pair_reports"]:
        observed[f"pair-report-{item['training_seed']}"] = _sha(
            read_pin(item, protocol["limits"]["input_file_cap_bytes"], deadline))
    observed.update(verify_behavior_sources(protocol, deadline))
    return observed


def _runtime_before_torch(protocol):
    if "torch" in sys.modules or "mujoco" in sys.modules:
        raise ValueError("Torch or simulator imported before admission")
    expected = protocol["runtime"]
    actual = {"python": platform.python_version(), "numpy": importlib.metadata.version("numpy"),
              "torch_distribution": importlib.metadata.version("torch")}
    if any(actual[name] != expected[name] for name in actual) or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("pinned hidden-CUDA runtime required")
    return actual


def _check_rss(protocol):
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > protocol["limits"]["rss_budget_bytes"]:
        raise MemoryError("checkpoint-support RSS budget exceeded")


def _forward_window(agent, features, targets, hidden, torch, loss_function):
    inputs = torch.from_numpy(features).unsqueeze(1)
    targets = torch.from_numpy(targets).unsqueeze(1)
    hidden, output, diagnostics = agent(inputs, hidden, diagnostics=True)
    raw = diagnostics["raw_output"]
    scaled = torch.tanh(raw) * raw.new_tensor([3., math.pi])
    exact = torch.equal(output, scaled)
    values = loss_function(output, targets)
    if (not torch.isfinite(hidden).all() or not torch.isfinite(output).all() or
            not torch.isfinite(raw).all() or not torch.isfinite(values).all()):
        raise ValueError("nonfinite checkpoint inference value")
    delta = output[..., 1] - targets[..., 1]
    return (hidden, output.reshape(-1, 2).cpu().numpy().copy(), raw.reshape(-1, 2).cpu().numpy().copy(), exact,
            float(values.sum()), float((output[..., 0] - targets[..., 0]).abs().sum()),
            float(torch.atan2(torch.sin(delta), torch.cos(delta)).abs().sum()))


def _infer(agent, episodes, torch, deadline, loss_function, forward_window=_forward_window):
    if agent.training or any(parameter.requires_grad for parameter in agent.parameters()):
        raise ValueError("inference-only frozen model required")
    actions, raw_outputs = [], []
    total = velocity = heading = 0.0
    rows = windows = 0
    exact = True
    with torch.inference_mode():
        for episode in episodes:
            hidden = agent.reset()
            episode_actions, episode_raw = [], []
            for start in range(0, len(episode["features"]), 32):
                _deadline(deadline)
                (hidden, current_actions, current_raw, window_exact, window_total,
                 window_velocity, window_heading) = forward_window(
                    agent, episode["features"][start:start + 32], episode["targets"][start:start + 32],
                    hidden, torch, loss_function)
                exact = exact and window_exact
                total += window_total; velocity += window_velocity; heading += window_heading
                episode_actions.append(current_actions); episode_raw.append(current_raw)
                rows += len(current_actions); windows += 1
            actions.append(np.concatenate(episode_actions)); raw_outputs.append(np.concatenate(episode_raw))
    return {"actions": actions, "raw_outputs": raw_outputs, "rows": rows, "windows": windows,
            "scaling_exact": exact,
            "metrics": {"ticks": rows, "loss": total / rows, "velocity_mae": velocity / rows,
                        "wrapped_heading_mae_radians": heading / rows,
                        "interpretation": "recorded-input teacher imitation; not closed-loop navigation success"}}


def execute(output, execution_manifest_path, execution_manifest_sha256):
    started = time.monotonic()
    protocol_payload = PROTOCOL_PATH.read_bytes()
    protocol = load_protocol()
    execution_manifest = load_execution_manifest(
        execution_manifest_path, execution_manifest_sha256, output, protocol)
    deadline = started + protocol["limits"]["internal_seconds"]
    return_deadline = started + protocol["limits"]["normal_through_return_seconds"]
    output = Path(output).absolute()
    prepare_output_parent(output)
    if output.exists():
        raise ValueError("fresh output under the audit worktree runs directory required")
    if shutil.disk_usage(output.parent).free < protocol["limits"]["minimum_free_bytes"]:
        raise ValueError("checkpoint-support free-space floor not met")
    attempt = {"schema": "m7-navigation-v2-checkpoint-support-attempt-v1",
        "status": "attempt-reserved", "attempt": 1, "retry_allowed": False,
        "protocol_sha256": PROTOCOL_SHA256,
        "execution_manifest_sha256": execution_manifest_sha256,
        "outer_timeout_seconds": protocol["limits"]["normal_through_return_seconds"],
        "outer_supervisor": execution_manifest["outer_supervisor"]}
    attempt_payload = reserve_attempt(output, attempt)
    source_before = verify_behavior_sources(protocol, deadline)
    behavior = load_behavior(protocol)
    if verify_behavior_sources(protocol, deadline) != source_before:
        raise ValueError("checkpoint-support behavior sources changed during import")
    before = _fingerprints(protocol, deadline)
    runtime = _runtime_before_torch(protocol)
    _check_rss(protocol)
    index = json.loads(read_pin(protocol["immutable_inputs"]["model_index"], 8 * MiB, deadline))
    data_manifest = json.loads(read_pin(protocol["immutable_inputs"]["data_manifest"], 8 * MiB, deadline))
    published = validate_documents(protocol, index, data_manifest)
    old_manifest = json.loads(read_pin(protocol["immutable_inputs"]["old_manifest"], 8 * MiB, deadline))
    transfer_root = _path(protocol["immutable_inputs"]["safe_transfer"]["path"]).parent
    data = behavior.data_reader.read_old_transfer(transfer_root, old_manifest, data_manifest["historical_reader"])
    if data.get("held_out") != []:
        raise ValueError("held-out transfer rows are forbidden")
    targets = validate_development(protocol, data["dev"])
    admitted = admit_candidates(protocol, index, behavior.research)
    if set(admitted) != {(seed, arm) for seed in (10, 11, 12) for arm in ("old-corpus", "augmented")}:
        raise ValueError("six candidate admission differs")
    _deadline(deadline)
    import torch
    if (torch.__version__ != protocol["runtime"]["torch_build"] or torch.cuda.is_initialized() or
            importlib.metadata.version("torch") != protocol["runtime"]["torch_distribution"]):
        raise ValueError("pinned Torch build or hidden CUDA differs")
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    outputs = {}
    for frozen in protocol["checkpoints"]:
        seed, arm = frozen["training_seed"], frozen["arm"]
        graph, payload, provenance = admitted[seed, arm]
        policy = behavior.male_policy._load_checked_policy(graph, payload, dict(provenance),
            _path(protocol["immutable_inputs"]["cell_source"]["path"]), device="cpu", seed=0)
        outputs[model_key(seed, arm)] = _infer(
            policy.agent, data["dev"], torch, deadline, behavior.loss_for)
        del policy
        _check_rss(protocol)
    report, arrays_payload = analyze_outputs(protocol, targets, outputs, published)
    after = _fingerprints(protocol, deadline)
    if after != before:
        raise ValueError("checkpoint-support inputs changed during inference")
    source_after = verify_behavior_sources(protocol, deadline)
    if source_after != source_before:
        raise ValueError("checkpoint-support behavior sources changed during inference")
    elapsed = time.monotonic() - started
    report.update(runtime={**runtime, "torch_build": torch.__version__, "device": "cpu", "threads": torch.get_num_threads()},
                  elapsed_seconds=elapsed, input_before=before, input_after=after,
                  behavior_sources_before=source_before, behavior_sources_after=source_after,
                  attempt_sha256=_sha(attempt_payload), execution_manifest_sha256=execution_manifest_sha256)
    execution = {"schema": "m7-navigation-v2-checkpoint-support-execution-v1",
        "status": "inference-completed-pending-final-report", "attempt": 1, "retry_allowed": False,
        "protocol_sha256": PROTOCOL_SHA256, "report_sha256": _sha(canonical(report)),
        "execution_manifest_sha256": execution_manifest_sha256,
        "attempt_sha256": _sha(attempt_payload),
        "outer_supervisor": execution_manifest["outer_supervisor"],
        "arrays_sha256": _sha(arrays_payload), "rows": report["rows"], "windows": report["windows"],
        "elapsed_seconds": elapsed, "held_out_accessed": False, "simulator_executed": False,
        "training_executed": False, "qualification_claims": [], "r3_complete": False}
    final_prepublication_checks(protocol, deadline, return_deadline, attempt_payload,
                                protocol_payload, arrays_payload, canonical(report), canonical(execution))
    publish_success(output, protocol_payload, arrays_payload, report, execution)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--execution-manifest-sha256", required=True)
    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        execute(args.output, args.execution_manifest, args.execution_manifest_sha256)
    except BaseException as error:
        failure = {"schema": "m7-navigation-v2-checkpoint-support-failure-v1", "status": "failed",
                   "attempt": 1, "retry_allowed": False, "protocol_sha256": PROTOCOL_SHA256,
                   "execution_manifest_sha256": args.execution_manifest_sha256,
                   "elapsed_seconds": time.monotonic() - started,
                   "error": {"type": type(error).__name__, "message": str(error)[:1024]},
                   "held_out_accessed": False, "simulator_executed": False,
                   "training_executed": False, "qualification_claims": [], "r3_complete": False}
        try:
            publish_failure(args.output, failure)
        except BaseException as diagnostic:
            error.add_note("Failure evidence publication also failed: " + str(diagnostic)[:512])
        raise


if __name__ == "__main__":
    main()
