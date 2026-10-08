"""One-shot outer owner for the three bounded navigation-v3 training pairs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "docs/plans/m7-navigation-v3-matched-budget-execution-v1.json"
PROTOCOL_PATH = "docs/plans/m7-navigation-v3-matched-budget-protocol.json"
PROTOCOL_SHA = "ecfafd2b6bedaf5d073e0bf32571d1978084ec7ddfb0e8c6c98a298d38d70732"
DATA_SHA = "47c4523c40e485ba4839cc80c9db891761791b801cc777755028122a1dbacb41"
PYTHON = "/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python"
RUN_NAME = "m7-navigation-v3-matched-budget-v1"
OUTPUT = ROOT / "runs" / RUN_NAME
SEEDS = (10, 11, 12)
ARMS = ("old-corpus", "augmented")
MiB = 1024**2
GiB = 1024**3
MAX_JSON = 4 * MiB
PAIR_BYTES = 64 * MiB
AGGREGATE_BYTES = 256 * MiB
PAIR_INTERNAL_SECONDS = 600
PAIR_OUTER_SECONDS = 660
ALL_INTERNAL_SECONDS = 2100
NORMAL_SECONDS = 2150
HARD_SECONDS = 2160
RSS_BYTES = GiB
MINIMUM_FREE_BYTES = GiB
MAX_PROCESSES = 256
LOG_BYTES = MiB
SELF_ZERO = "0" * 64
PAIR_AUXILIARY_FILES = (
    "protocol.json", "original-graph.json", "old-corpus-schedule.json",
    "augmented-schedule.json", "before-fit.json", "after-old-corpus.json",
    "after-augmented.json", "after-fit.json", "after-final-sync.json",
)
PAIR_FILES = (*PAIR_AUXILIARY_FILES, "old-corpus.pt", "augmented.pt",
              "report.json", "publication.json")
SOURCE_FILES = (
    "docs/plans/m7-navigation-v3-matched-budget-protocol.json",
    "scripts/prepare_male_navigation_v2.py",
    "scripts/prepare_male_recovery_data.py",
    "scripts/run_male_navigation_v3_training.py",
    "scripts/train_male_navigation_v2.py",
    "scripts/train_male_navigation_v3.py",
    "scripts/train_male_recovery.py",
    "scripts/train_male_reduced.py",
    "src/palimpsest/__init__.py",
    "src/palimpsest/artifacts.py",
    "src/palimpsest/evaluate.py",
    "src/palimpsest/male_matched_budget.py",
    "src/palimpsest/male_model.py",
    "src/palimpsest/male_navigation_research.py",
    "src/palimpsest/male_policy.py",
    "src/palimpsest/male_research.py",
    "src/palimpsest/records.py",
    "src/palimpsest/storage.py",
    "tests/test_male_navigation_v3.py",
    "tests/test_male_navigation_v3_execution.py",
    "uv.lock",
)
EXACT_ENVIRONMENT = {
    "CUDA_VISIBLE_DEVICES": "",
    "HOME": "/home/utkarsh",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "MKL_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "PATH": "/usr/bin:/bin",
    "PYTHONHASHSEED": "0",
    "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'scripts'}",
    "TMPDIR": "/tmp",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode() + b"\n"


def _json(payload):
    def pairs(rows):
        value = {}
        for key, item in rows:
            if key in value:
                raise ValueError("Duplicate execution JSON key")
            value[key] = item
        return value
    try:
        return json.loads(payload, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              ValueError("Nonfinite execution JSON")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("Invalid execution JSON") from error


def _read(path, maximum=MAX_JSON):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError(f"Missing, linked, or oversized file: {path.name}")
    with path.open("rb") as stream:
        payload = stream.read(maximum + 1)
    if len(payload) > maximum:
        raise ValueError(f"Oversized file: {path.name}")
    return payload


def _digest(payload):
    return hashlib.sha256(payload).hexdigest()


def protocol():
    payload = _read(ROOT / PROTOCOL_PATH)
    if _digest(payload) != PROTOCOL_SHA:
        raise ValueError("Frozen navigation-v3 protocol changed")
    value = _json(payload)
    if value.get("id") != "M7-NAV-V3-MATCHED-BUDGET-1" or value.get("version") != 1:
        raise ValueError("Wrong navigation-v3 protocol")
    return value


def _normalized_manifest(value):
    result = copy.deepcopy(value)
    result["self_sha256"] = SELF_ZERO
    argv = result.get("invocation", {}).get("runner_argv")
    if isinstance(argv, list) and "--execution-manifest-sha256" in argv:
        index = argv.index("--execution-manifest-sha256") + 1
        if index < len(argv):
            argv[index] = SELF_ZERO
    outer = result.get("invocation", {}).get("outer_argv")
    if isinstance(outer, list) and "--execution-manifest-sha256" in outer:
        index = outer.index("--execution-manifest-sha256") + 1
        if index < len(outer):
            outer[index] = SELF_ZERO
    return result


def execution_digest(value):
    """Digest canonical content with only the two self-references zeroed."""
    return _digest(canonical(_normalized_manifest(value)))


def seal_manifest(value):
    result = copy.deepcopy(value)
    result["self_sha256"] = SELF_ZERO
    argv = result.get("invocation", {}).get("runner_argv")
    if isinstance(argv, list) and "--execution-manifest-sha256" in argv:
        argv[argv.index("--execution-manifest-sha256") + 1] = SELF_ZERO
    outer = result.get("invocation", {}).get("outer_argv")
    if isinstance(outer, list) and "--execution-manifest-sha256" in outer:
        outer[outer.index("--execution-manifest-sha256") + 1] = SELF_ZERO
    digest = execution_digest(result)
    result["self_sha256"] = digest
    argv = result["invocation"]["runner_argv"]
    argv[argv.index("--execution-manifest-sha256") + 1] = digest
    outer = result["invocation"]["outer_argv"]
    outer[outer.index("--execution-manifest-sha256") + 1] = digest
    return result


def _runner_argv(digest):
    return [PYTHON, str(ROOT / "scripts/run_male_navigation_v3_training.py"),
            "--execution-manifest", str(ROOT / MANIFEST_PATH),
            "--execution-manifest-sha256", digest]


def _outer_argv(digest):
    environment = [f"{key}={value}" for key, value in sorted(EXACT_ENVIRONMENT.items())]
    return ["/usr/bin/timeout", "--signal=TERM", "--kill-after=10s", f"{HARD_SECONDS}s",
            "/usr/bin/env", "-i", *environment, *_runner_argv(digest)]


def _pair_rows():
    study = protocol()["immutable_inputs"]
    common = [
        "--graph", study["graph"]["path"],
        "--graph-manifest", study["graph_manifest"]["path"],
        "--cell-source", study["cell_source"]["path"],
    ]
    return [{"seed": seed, "output": str(OUTPUT / f"seed-{seed}"),
             "argv": [PYTHON, str(ROOT / "scripts/train_male_navigation_v3.py"),
                      "--training-seed", str(seed), *common,
                      "--output", str(OUTPUT / f"seed-{seed}")]}
            for seed in SEEDS]


def _limits():
    return {
        "pair_internal_seconds": PAIR_INTERNAL_SECONDS,
        "pair_outer_seconds": PAIR_OUTER_SECONDS,
        "all_internal_seconds": ALL_INTERNAL_SECONDS,
        "normal_through_return_seconds": NORMAL_SECONDS,
        "enclosing_hard_target_seconds": HARD_SECONDS,
        "pair_payload_bytes": PAIR_BYTES, "aggregate_bytes": AGGREGATE_BYTES,
        "rss_bytes": RSS_BYTES, "minimum_free_bytes": MINIMUM_FREE_BYTES,
        "process_inventory_entries": MAX_PROCESSES,
        "log_bytes_per_stream": LOG_BYTES,
    }


def admit_manifest(path, expected_digest):
    payload = _read(path)
    value = _json(payload)
    if canonical(value) != payload:
        raise ValueError("Execution manifest is not canonical")
    if (not isinstance(expected_digest, str) or len(expected_digest) != 64 or
            value.get("self_sha256") != expected_digest or
            execution_digest(value) != expected_digest):
        raise ValueError("Execution manifest self-binding differs")
    if set(value) != {"schema", "attempt", "retry_allowed", "self_sha256",
                      "protocol_sha256", "data_manifest_sha256", "immutable_inputs",
                      "behavior_sources", "runtime", "limits", "output", "pairs",
                      "invocation", "held_out_status", "qualification_claims"}:
        raise ValueError("Execution manifest fields differ")
    if (value["schema"] != "m7-navigation-v3-matched-budget-execution-v1" or
            value["attempt"] != 1 or value["retry_allowed"] is not False or
            value["protocol_sha256"] != PROTOCOL_SHA or
            value["data_manifest_sha256"] != DATA_SHA or
            value["immutable_inputs"] != protocol()["immutable_inputs"] or
            value["runtime"] != {"python": "3.11.15", "cuda_visible_devices": "",
                                 "cpu_threads": 1} or
            value["limits"] != _limits() or value["output"] != str(OUTPUT) or
            value["pairs"] != _pair_rows() or
            value["held_out_status"] != "locked_unopened" or
            value["qualification_claims"] != []):
        raise ValueError("Frozen execution contract differs")
    sources = value["behavior_sources"]
    pinned = protocol()["behavior_source_admission"]["existing_hashes"]
    if (not isinstance(sources, dict) or set(sources) != set(SOURCE_FILES) or
            any(not isinstance(item, str) or len(item) != 64 or
                any(char not in "0123456789abcdef" for char in item)
                for item in sources.values()) or
            any(sources.get(name) != digest for name, digest in pinned.items())):
        raise ValueError("Frozen behavior-source roster differs")
    invocation = value["invocation"]
    if invocation != {"cwd": str(ROOT), "environment": EXACT_ENVIRONMENT,
                      "runner_argv": _runner_argv(expected_digest),
                      "outer_argv": _outer_argv(expected_digest)}:
        raise ValueError("Frozen invocation differs")
    return value


def source_identity(expected=None):
    observed = {}
    for name in SOURCE_FILES:
        path = ROOT / name
        payload = _read(path, 8 * MiB)
        observed[name] = _digest(payload)
    if expected is not None and observed != expected:
        raise ValueError("Navigation-v3 behavior source changed")
    return observed


def runtime_identity():
    observed = {"python": platform.python_version(),
                "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                "cpu_threads": int(os.environ.get("OMP_NUM_THREADS", "0"))}
    if (observed != {"python": "3.11.15", "cuda_visible_devices": "", "cpu_threads": 1} or
            dict(os.environ) != EXACT_ENVIRONMENT or
            {"torch", "mujoco"} & set(sys.modules)):
        raise ValueError("Frozen lazy CPU runtime/environment differs")
    return observed


def _safe_output(path):
    path = Path(os.path.abspath(path))
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError("Output path traverses a symlink")
    return path


def preflight(value):
    output = _safe_output(value["output"])
    if output != OUTPUT or output.parent != ROOT / "runs":
        raise ValueError("Exact aggregate output family required")
    if output.exists():
        raise FileExistsError("Enclosing training attempt is already consumed")
    for item in value["immutable_inputs"].values():
        source = Path(os.path.abspath(item["path"]))
        if output == source or output in source.parents or source in output.parents:
            raise ValueError("Output overlaps an immutable input")


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_new(path, value, maximum=MAX_JSON):
    payload = canonical(value)
    if len(payload) > maximum:
        raise ValueError("Execution receipt exceeds cap")
    with Path(path).open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    return value


def reserve_attempt(output, manifest_digest):
    """Create the enclosing output and durable no-retry marker before any child."""
    output = _safe_output(output)
    if output.exists():
        raise FileExistsError("Enclosing training attempt is already consumed")
    if not output.parent.is_dir():
        raise ValueError("Fresh existing aggregate parent required")
    output.mkdir(exist_ok=False)
    _fsync_directory(output.parent)
    receipt = {
        "id": "male-navigation-v3-enclosing-attempt-v1", "attempt": 1,
        "execution_manifest_sha256": manifest_digest, "output": str(output),
        "pairs": list(SEEDS), "retry_allowed": False,
        "held_out_status": "locked_unopened", "qualification_claims": [],
    }
    _write_new(output / "attempt.json", receipt)
    _fsync_directory(output)
    return receipt


def rss_bytes():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def _tree_bytes(root):
    total = entries = 0
    if not Path(root).exists():
        return 0
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            path = Path(directory) / name
            entries += 1
            if entries > 1024 or path.is_symlink():
                raise ValueError("Aggregate inventory exceeds bounds or contains symlink")
            if path.is_file():
                total += path.stat().st_size
    return total


def check_resources(output, deadline):
    if time.monotonic() > deadline:
        raise TimeoutError("Enclosing training deadline exceeded")
    if rss_bytes() > RSS_BYTES:
        raise MemoryError("Enclosing training RSS cap exceeded")
    output = Path(output)
    existing = output if output.exists() else output.parent
    if shutil.disk_usage(existing).free < MINIMUM_FREE_BYTES:
        raise OSError("Enclosing training free-space floor reached")
    if _tree_bytes(output) > AGGREGATE_BYTES:
        raise ValueError("Enclosing training aggregate byte cap exceeded")


def process_identity(pid):
    try:
        root = Path("/proc") / str(pid)
        fields = (root / "stat").read_text().rsplit(") ", 1)[1].split()
        status = dict(line.split(":", 1) for line in (root / "status").read_text().splitlines()
                      if ":" in line)
        raw = (root / "cmdline").read_bytes().split(b"\0")
        if raw and raw[-1] == b"":
            raw.pop()
        return {"pid": pid, "ppid": int(fields[1]), "group": int(fields[2]),
                "start_ticks": int(fields[19]), "state": fields[0],
                "rss_bytes": int(status.get("VmRSS", "0 kB").split()[0]) * 1024,
                "argv": [os.fsdecode(item) for item in raw],
                "command": b" ".join(raw).decode(errors="replace")[:512]}
    except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError, KeyError):
        return None


def descendants(parent_pid):
    ancestry = {}
    for path in Path("/proc").iterdir():
        if path.name.isdigit():
            try:
                ancestry[int(path.name)] = int(
                    (path / "stat").read_text().rsplit(") ", 1)[1].split()[1])
            except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
                continue
    result, parents = {}, {parent_pid}
    while parents:
        found = {pid for pid, ppid in ancestry.items() if ppid in parents and pid not in result}
        result.update({pid: process_identity(pid) for pid in found})
        parents = found
    return [row for row in result.values() if row is not None]


def admit_process_observation(identity, parent_pid, rows, known, maximum):
    if (not isinstance(identity, dict) or
            any(type(identity.get(key)) is not int for key in ("pid", "ppid", "group", "start_ticks")) or
            identity["pid"] != identity["group"] or identity["ppid"] != parent_pid):
        raise ValueError("Child PID/start/process-group identity differs")
    current = next((row for row in rows if row.get("pid") == identity["pid"]), None)
    if (current is None or current.get("start_ticks") != identity["start_ticks"] or
            current.get("ppid") != parent_pid or current.get("group") != identity["group"]):
        raise ValueError("Child identity disappeared, escaped, or was reused")
    result = dict(known)
    for row in rows:
        key = (row.get("pid"), row.get("start_ticks"))
        if any(type(item) is not int for item in key) or row.get("group") != identity["group"]:
            raise ValueError("Observed child escaped its process group")
        if key not in result and len(result) >= maximum:
            raise ValueError("Finite child process inventory exceeded")
        result[key] = {name: row.get(name) for name in
                       ("pid", "ppid", "group", "start_ticks", "command")}
    return result


def _signal_group(identity, number, signals):
    if identity is None:
        return
    current = process_identity(identity["pid"])
    if (current is not None and current["start_ticks"] == identity["start_ticks"] and
            current["group"] == identity["group"]):
        try:
            os.killpg(identity["group"], number)
        except ProcessLookupError:
            return
        name = signal.Signals(number).name
        if not signals or signals[-1] != name:
            signals.append(name)


def supervise_pair(pair, deadline):
    """Run one trainer in one observed process group with TERM/KILL/drain bounds."""
    # Reuse the repository's bounded-prefix pipe drainer. Import stays after the
    # enclosing attempt and has no Torch/MuJoCo dependency.
    from palimpsest.evaluate import bounded_logs

    parent = os.getpid()
    baseline = {(row["pid"], row["start_ticks"]) for row in descendants(parent)}
    supervision = Path(pair["output"]).parent / "supervision" / f"seed-{pair['seed']}"
    supervision.mkdir(parents=True, exist_ok=False)
    stdout_path, stderr_path = supervision / "stdout.log", supervision / "stderr.log"
    started = time.monotonic()
    known, identity, errors, signals = {}, None, [], []
    process = None
    def log_failure(message):
        if message not in errors:
            errors.append(message)

    with bounded_logs(supervision, LOG_BYTES, log_failure) as (stdout, stderr):
        try:
            process = subprocess.Popen(pair["argv"], cwd=ROOT, env=EXACT_ENVIRONMENT,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            while True:
                now = time.monotonic()
                code = process.poll()
                rows = [row for row in descendants(parent)
                        if (row["pid"], row["start_ticks"]) not in baseline]
                current = process_identity(process.pid)
                if identity is None and current is not None:
                    identity = {key: current[key] for key in
                                ("pid", "ppid", "group", "start_ticks", "command")}
                    if current.get("argv") != pair["argv"]:
                        errors.append("Child argv differs")
                if identity is not None and code is None:
                    try:
                        known = admit_process_observation(identity, parent, rows, known,
                                                          MAX_PROCESSES)
                    except ValueError as error:
                        errors.append(str(error))
                if sum(row.get("rss_bytes", 0) for row in rows) > RSS_BYTES:
                    errors.append("Pair RSS cap exceeded")
                if errors or now >= deadline - 10:
                    _signal_group(identity, signal.SIGTERM, signals)
                if now >= deadline - 5:
                    _signal_group(identity, signal.SIGKILL, signals)
                if code is not None:
                    break
                if now >= deadline:
                    errors.append("Pair outer deadline exceeded")
                    break
                time.sleep(.1)
            if process.poll() is None:
                _signal_group(identity, signal.SIGKILL, signals)
                try:
                    process.wait(timeout=max(0.0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    errors.append("Pair process did not drain by outer deadline")
        except BaseException as error:
            errors.append(f"{type(error).__name__}: {str(error)[:512]}")
            _signal_group(identity, signal.SIGKILL, signals)
            if process is not None and process.poll() is None:
                if identity is None:
                    process.kill()
                try:
                    process.wait(timeout=max(0.0, min(5.0, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    errors.append("Pair leader did not drain after forced termination")
    survivors = []
    for key, row in known.items():
        current = process_identity(key[0])
        if current is not None and current["start_ticks"] == key[1] and current["state"] != "Z":
            survivors.append(row)
            try:
                os.kill(current["pid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
    elapsed = time.monotonic() - started
    code = process.returncode if process is not None else None
    status = "completed" if (code == 0 and identity is not None and not errors and
                              not signals and not survivors and elapsed <= PAIR_OUTER_SECONDS) else "failed"
    result = {"status": status, "returncode": code, "elapsed_seconds": elapsed,
              "identity": identity, "observed": list(known.values()),
              "signals": signals, "survivors": survivors,
              "errors": errors, "stdout_bytes": stdout_path.stat().st_size,
              "stderr_bytes": stderr_path.stat().st_size}
    _write_new(supervision / "supervision.json", result)
    _fsync_directory(supervision)
    return result


def _inventory(root):
    root = _safe_output(root)
    names = []
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Pair inventory contains a link or non-file")
        names.append(path.name)
    if set(names) != set(PAIR_FILES):
        raise ValueError("Pair evidence inventory differs")
    result, total = {}, 0
    for name in names:
        payload = _read(root / name, PAIR_BYTES)
        total += len(payload)
        result[name] = {"sha256": _digest(payload), "size_bytes": len(payload)}
    if total > PAIR_BYTES:
        raise ValueError("Pair evidence exceeds payload cap")
    return result


def admit_pair(output, seed):
    output = _safe_output(output)
    if output.name != f"seed-{seed}" or seed not in SEEDS:
        raise ValueError("Wrong pair output identity")
    failure = output.with_name(output.name + ".failure.json")
    pending = (output / "report.pending", output / "publication.pending")
    if failure.exists() or any(path.exists() for path in pending):
        raise ValueError("Pair has failure or pending evidence")
    attempt = _json(_read(output.with_name(output.name + ".attempt.json")))
    expected_models = [{"seed": item_seed, "arm": arm}
                       for item_seed in SEEDS for arm in ARMS]
    if attempt != {"id": "male-navigation-v3-pair-attempt-v1",
                   "study_protocol_sha256": PROTOCOL_SHA, "training_seed": seed,
                   "output": str(output.absolute()), "models": expected_models,
                   "retry_allowed": False, "qualification_claims": []}:
        raise ValueError("Pair attempt receipt differs")
    inventory = _inventory(output)
    report_payload = _read(output / "report.json")
    report = _json(report_payload)
    if (not isinstance(report, dict) or
            report.get("status") != "completed-navigation-v3-training" or
            report.get("training_completed") is not True or
            report.get("training_seed") != seed or
            report.get("study_protocol_sha256") != PROTOCOL_SHA or
            report.get("data_manifest_sha256") != DATA_SHA or
            report.get("training_attempted") is not True or
            report.get("held_out_status") != "locked_unopened" or
            report.get("held_out_used_for_selection") is not False or
            report.get("qualification_claims") != [] or
            set(report.get("models", {})) != set(ARMS) or
            report.get("protocol_sha256") != inventory["protocol.json"]["sha256"]):
        raise ValueError("Pair completed report differs")
    models = []
    for arm in ARMS:
        row = report["models"][arm]
        checkpoint = row.get("checkpoint", {})
        name = arm + ".pt"
        if (row.get("status") != "completed" or row.get("optimizer_updates") != 1440 or
                row.get("real_row_presentations") != 46080 or
                row.get("selected_optimizer_update") != 1440 or
                row.get("selected_real_row_presentations") != 46080 or
                row.get("graph_variant") != "original" or checkpoint.get("path") != name or
                row.get("schedule_sha256") != inventory[arm + "-schedule.json"]["sha256"] or
                row.get("recorded_development", {}).get("ticks") != 1228 or
                checkpoint.get("sha256") != inventory[name]["sha256"] or
                checkpoint.get("size_bytes") != inventory[name]["size_bytes"]):
            raise ValueError("Pair model/checkpoint receipt differs")
        models.append({"seed": seed, "arm": arm, "checkpoint": checkpoint,
                       "report_sha256": _digest(report_payload)})
    publication = _json(_read(output / "publication.json"))
    if publication != {"id": "male-navigation-v3-publication-v1",
                       "status": "durably-published",
                       "study_protocol_sha256": PROTOCOL_SHA,
                       "report_sha256": _digest(report_payload),
                       "report_size_bytes": len(report_payload),
                       "qualification_claims": []}:
        raise ValueError("Pair publication receipt differs")
    return {"seed": seed, "models": models, "report_sha256": _digest(report_payload),
            "publication_sha256": inventory["publication.json"]["sha256"],
            "inventory": inventory}


def orchestrate(pairs, started, runner, admit, clock=time.monotonic):
    report = {"status": "running-navigation-v3-enclosing-training",
              "training_completed": False,
              "pairs": {str(seed): {"status": "not_started"} for seed in SEEDS},
              "models": [], "held_out_status": "locked_unopened",
              "qualification_claims": []}
    for expected_seed, pair in zip(SEEDS, pairs, strict=True):
        if pair.get("seed") != expected_seed:
            report["failure"] = {"type": "ValueError", "message": "Pair order differs"}
            break
        now = clock()
        if now > started + ALL_INTERNAL_SECONDS or now + PAIR_OUTER_SECONDS > started + ALL_INTERNAL_SECONDS:
            report["failure"] = {"type": "TimeoutError",
                                 "message": "Insufficient enclosing allowance for next pair"}
            break
        row = report["pairs"][str(expected_seed)]
        row["status"] = "running"
        try:
            pair_deadline = min(now + PAIR_OUTER_SECONDS,
                                started + ALL_INTERNAL_SECONDS)
            supervision = runner(pair, pair_deadline)
            row["supervision"] = supervision
            after = clock()
            if (after > pair_deadline or after > started + ALL_INTERNAL_SECONDS or
                    supervision.get("status") != "completed" or
                    supervision.get("returncode") != 0 or
                    supervision.get("identity") is None or
                    supervision.get("survivors") or
                    supervision.get("elapsed_seconds", 0) > PAIR_OUTER_SECONDS):
                raise RuntimeError("Pair supervision did not complete normally")
            evidence = admit(Path(pair["output"]), expected_seed)
            if len(evidence.get("models", ())) != 2:
                raise ValueError("Pair did not admit exactly two models")
            row.update(status="completed", evidence=evidence)
            report["models"].extend(evidence["models"])
        except BaseException as error:
            row["status"] = "failed"
            row["error"] = {"type": type(error).__name__, "message": str(error)[:1024]}
            report["failure"] = row["error"]
            break
    if (all(report["pairs"][str(seed)]["status"] == "completed" for seed in SEEDS) and
            len(report["models"]) == 6):
        if clock() > started + ALL_INTERNAL_SECONDS:
            report["failure"] = {"type": "TimeoutError",
                                 "message": "Enclosing internal deadline exceeded"}
        else:
            report.update(status="completed-navigation-v3-enclosing-training",
                          training_completed=True)
    if not report["training_completed"]:
        report["status"] = "failed-navigation-v3-enclosing-training"
    return report


def _publish_failure(output, report, error):
    report = copy.deepcopy(report)
    report.update(status="failed-navigation-v3-enclosing-training",
                  training_completed=False)
    report.setdefault("failure", {"type": type(error).__name__,
                                  "message": str(error)[:1024]})
    path = Path(output) / "failure.json"
    if not path.exists():
        _write_new(path, report)
        _fsync_directory(output)


def _publish_success(output, report, deadline):
    output = Path(output)
    pending, final = output / "report.pending", output / "report.json"
    receipt_pending, receipt = output / "publication.pending", output / "publication.json"
    if any(path.exists() for path in (pending, final, receipt_pending, receipt,
                                      output / "failure.json")):
        raise FileExistsError("Fresh aggregate publication paths required")
    payload = canonical(report)
    if time.monotonic() > deadline:
        raise TimeoutError("Aggregate normal-return deadline exceeded")
    with pending.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    pending.replace(final)
    _fsync_directory(output)
    completion = {"id": "male-navigation-v3-enclosing-publication-v1",
                  "status": "durably-published",
                  "execution_manifest_sha256": report["execution_manifest_sha256"],
                  "report_sha256": _digest(payload), "report_size_bytes": len(payload),
                  "models": 6, "qualification_claims": []}
    _write_new(receipt_pending, completion)
    if time.monotonic() > deadline:
        raise TimeoutError("Aggregate normal-return deadline exceeded")
    receipt_pending.replace(receipt)
    _fsync_directory(output)  # Last fallible success step.
    return completion


def success_admitted(output, manifest_digest):
    """Admit aggregate success only with six models and the durable receipt."""
    output = Path(output)
    if (not (output / "attempt.json").is_file() or
            not (output / "report.json").is_file() or
            not (output / "publication.json").is_file() or
            any((output / name).exists() for name in
                ("failure.json", "report.pending", "publication.pending"))):
        return False
    try:
        attempt = _json(_read(output / "attempt.json"))
        payload = _read(output / "report.json")
        report = _json(payload)
        receipt = _json(_read(output / "publication.json"))
    except (OSError, ValueError):
        return False
    if (attempt.get("execution_manifest_sha256") != manifest_digest or
            attempt.get("retry_allowed") is not False or
            report.get("status") != "completed-navigation-v3-enclosing-training" or
            report.get("training_completed") is not True or
            report.get("execution_manifest_sha256") != manifest_digest or
            len(report.get("models", ())) != 6 or
            any(report.get("pairs", {}).get(str(seed), {}).get("status") != "completed"
                for seed in SEEDS)):
        return False
    return receipt == {
        "id": "male-navigation-v3-enclosing-publication-v1",
        "status": "durably-published", "execution_manifest_sha256": manifest_digest,
        "report_sha256": _digest(payload), "report_size_bytes": len(payload),
        "models": 6, "qualification_claims": [],
    }


def execute(manifest_path, expected_digest):
    started = time.monotonic()
    value = admit_manifest(manifest_path, expected_digest)
    if Path.cwd().resolve() != Path(value["invocation"]["cwd"]):
        raise ValueError("Execution cwd differs")
    preflight(value)
    before_sources = source_identity(value["behavior_sources"])
    runtime = runtime_identity()
    check_resources(Path(value["output"]).parent, started + ALL_INTERNAL_SECONDS)
    runs = Path(value["output"]).parent
    if not runs.exists():
        if runs != ROOT / "runs" or not runs.parent.is_dir() or runs.parent.is_symlink():
            raise ValueError("Unsafe aggregate output parent")
        runs.mkdir(exist_ok=False)
        _fsync_directory(runs.parent)
    attempt = reserve_attempt(Path(value["output"]), expected_digest)
    report = {"status": "running-navigation-v3-enclosing-training",
              "training_completed": False,
              "execution_manifest_sha256": expected_digest,
              "attempt": attempt, "runtime": runtime,
              "source_before": before_sources,
              "pairs": {str(seed): {"status": "not_started"} for seed in SEEDS},
              "models": [], "held_out_status": "locked_unopened",
              "qualification_claims": []}
    try:
        result = orchestrate(value["pairs"], started, supervise_pair, admit_pair)
        report.update(result)
        if not result["training_completed"]:
            failure = result.get("failure", {"type": "RuntimeError", "message": "training failed"})
            raise RuntimeError(failure.get("message", "training failed"))
        for pair in value["pairs"]:
            admitted = admit_pair(Path(pair["output"]), pair["seed"])
            if admitted["inventory"] != result["pairs"][str(pair["seed"])]["evidence"]["inventory"]:
                raise ValueError("Prior pair evidence changed before publication")
        report["source_after"] = source_identity(before_sources)
        if runtime_identity() != runtime:
            raise ValueError("Execution runtime changed")
        check_resources(value["output"], started + ALL_INTERNAL_SECONDS)
        if len(report["models"]) != 6:
            raise ValueError("Six models were not admitted")
        report["elapsed_seconds_before_publication"] = time.monotonic() - started
        _publish_success(value["output"], report, started + NORMAL_SECONDS)
        return report
    except BaseException as error:
        _publish_failure(value["output"], report, error)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--execution-manifest-sha256", required=True)
    args = parser.parse_args(argv)
    value = admit_manifest(args.execution_manifest, args.execution_manifest_sha256)
    if sys.argv != value["invocation"]["runner_argv"]:
        raise ValueError("Runner argv differs from frozen invocation")
    def interrupted(number, frame):
        raise InterruptedError(f"Execution interrupted by {signal.Signals(number).name}")

    previous = {number: signal.signal(number, interrupted)
                for number in (signal.SIGINT, signal.SIGTERM)}
    try:
        execute(args.execution_manifest, args.execution_manifest_sha256)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


if __name__ == "__main__":
    main()
