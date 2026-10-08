"""One-shot outer owner for the three bounded navigation-v3 training pairs."""
from __future__ import annotations

import argparse
import ast
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
import stat
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = "docs/plans/m7-navigation-v3-matched-budget-execution-v2.json"
AMENDMENT_PATH = "docs/plans/m7-navigation-v3-matched-budget-execution-v2-amendment.md"
PRIOR_MANIFEST_PATH = "docs/plans/m7-navigation-v3-matched-budget-execution-v1.json"
PRIOR_REPORT_PATH = "docs/reports/m7-navigation-v3-matched-budget-attempt-1.md"
PRIOR_VERIFICATION_PATH = (
    "docs/reports/m7-navigation-v3-matched-budget-attempt-1/verification.json")
PRIOR_JOURNAL_PATH = (
    "docs/reports/m7-navigation-v3-matched-budget-attempt-1/journal.log")
PROTOCOL_PATH = "docs/plans/m7-navigation-v3-matched-budget-protocol.json"
PROTOCOL_SHA = "ecfafd2b6bedaf5d073e0bf32571d1978084ec7ddfb0e8c6c98a298d38d70732"
DATA_SHA = "47c4523c40e485ba4839cc80c9db891761791b801cc777755028122a1dbacb41"
PYTHON = "/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python"
RUN_NAME = "m7-navigation-v3-matched-budget-v2"
OUTPUT = ROOT / "runs" / RUN_NAME
PRIOR_OUTPUT = ROOT / "runs" / "m7-navigation-v3-matched-budget-v1"
ATTEMPT = 2
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
SOURCE_MANUAL_FILES = (
    "docs/plans/m7-navigation-v3-matched-budget-protocol.json",
    "tests/test_male_navigation_v3.py",
    "tests/test_male_navigation_v3_execution.py",
    "uv.lock",
)
SOURCE_ENTRY_FILES = (
    "scripts/run_male_navigation_v3_training.py",
    "scripts/train_male_navigation_v2.py",  # V3 loads this by an admitted importlib string.
    "scripts/train_male_navigation_v3.py",
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
    """Read one stable, singly-linked regular file through an O_NOFOLLOW fd."""
    path = Path(os.path.abspath(path))
    for parent in path.parents:
        info = os.lstat(parent)
        if stat.S_ISLNK(info.st_mode):
            raise ValueError(f"Linked parent refused: {path.name}")
    before = os.lstat(path)
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
            before.st_size > maximum):
        raise ValueError(f"Missing, linked, or oversized file: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        rebound = os.lstat(path)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_mode,
                                 item.st_nlink, item.st_size, item.st_mtime_ns,
                                 item.st_ctime_ns)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or
                identity(opened) != identity(before) or identity(opened) != identity(rebound)):
            raise ValueError(f"File identity rebound while opening: {path.name}")
        chunks, remaining = [], maximum + 1
        while remaining:
            block = os.read(descriptor, min(65536, remaining))
            if not block:
                break
            chunks.append(block); remaining -= len(block)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
        rebound = os.lstat(path)
        if len(payload) > maximum or identity(after) != identity(opened) or identity(rebound) != identity(opened):
            raise ValueError(f"File changed during bounded read: {path.name}")
        return payload
    finally:
        os.close(descriptor)


def _module_path(module):
    if not module:
        return None
    candidates = []
    parts = module.split(".")
    if parts[0] == "palimpsest":
        relative = Path("src").joinpath(*parts)
        candidates.extend((relative.with_suffix(".py"), relative / "__init__.py"))
    elif len(parts) == 1:
        candidates.extend((Path("scripts") / f"{module}.py", Path(f"{module}.py"),
                           Path("src") / f"{module}.py"))
    for candidate in candidates:
        if (ROOT / candidate).is_file():
            return candidate.as_posix()
    return None


def _source_module(name):
    path = Path(name)
    if path.parts[:2] == ("src", "palimpsest"):
        tail = list(path.with_suffix("").parts[1:])
        if tail[-1] == "__init__":
            tail.pop()
        return ".".join(tail)
    if path.parts and path.parts[0] == "scripts":
        return path.stem
    return path.stem


def static_source_roster():
    """Conservative local import closure for both executed entry points."""
    pending, found = list(SOURCE_ENTRY_FILES), set()
    while pending:
        name = pending.pop()
        if name in found:
            continue
        found.add(name)
        tree = ast.parse(_read(ROOT / name, 8 * MiB), filename=name)
        current = _source_module(name)
        package = current if name.endswith("/__init__.py") else current.rpartition(".")[0]
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split(".") if package else []
                    remove = max(0, node.level - 1)
                    if remove:
                        base = base[:-remove]
                    if node.module:
                        base.extend(node.module.split("."))
                    module = ".".join(base)
                else:
                    module = node.module or ""
                modules.append(module)
                modules.extend(f"{module}.{alias.name}" if module else alias.name
                               for alias in node.names if alias.name != "*")
            elif (isinstance(node, ast.Call) and node.args and
                  isinstance(node.args[0], ast.Constant) and
                  isinstance(node.args[0].value, str) and
                  ((isinstance(node.func, ast.Name) and node.func.id == "__import__") or
                   (isinstance(node.func, ast.Attribute) and
                    node.func.attr == "import_module"))):
                modules.append(node.args[0].value)
        for module in modules:
            candidate = _module_path(module)
            if candidate is not None and candidate not in found:
                pending.append(candidate)
            if module.startswith("palimpsest."):
                pending.append("src/palimpsest/__init__.py")
    return tuple(sorted(found | set(SOURCE_MANUAL_FILES)))


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
    return [
        "/usr/bin/systemd-run", "--user", "--wait", "--collect",
        f"--working-directory={ROOT}",
        f"--unit=palimpsest-{RUN_NAME}",
        "--property=Type=exec", "--property=KillMode=control-group",
        f"--property=RuntimeMaxSec={NORMAL_SECONDS}s",
        f"--property=TimeoutStopSec={HARD_SECONDS - NORMAL_SECONDS}s",
        "--property=SendSIGKILL=yes", "--property=TimeoutStopFailureMode=kill",
        "/usr/bin/env", "-i", *environment, *_runner_argv(digest),
    ]


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


def _descriptor(name, maximum=MAX_JSON):
    payload = _read(ROOT / name, maximum)
    return {"path": name, "size_bytes": len(payload), "sha256": _digest(payload)}


def prior_failure():
    verification_payload = _read(ROOT / PRIOR_VERIFICATION_PATH)
    verification = _json(verification_payload)
    journal = _read(ROOT / PRIOR_JOURNAL_PATH)
    prior_manifest_payload = _read(ROOT / PRIOR_MANIFEST_PATH)
    prior_manifest = _json(prior_manifest_payload)
    expected = {
        "attempt": 1,
        "execution_manifest_sha256":
            "c7bbd686b74282ea579662ecf938073152ec1261be89163d37f8f4841c3195f7",
        "held_out_accessed": False,
        "journal": {"lines": 10, "path": PRIOR_JOURNAL_PATH,
                    "sha256":
                        "51773fc00774b4a3f781fbc96df4c5a642a436afb4bae2a581a34b1243071db2",
                    "size_bytes": 2794},
        "models_opened": False, "output_created": False,
        "qualification_claims": [], "reserved": False,
        "schema": "m7-navigation-v3-matched-budget-attempt-1-failure-v1",
        "service": {"cpu_time_display": "431ms", "exit_status": 1,
                    "memory_peak_display": "21.7M", "runtime_display": "700ms"},
        "source_commit": "148142b2086b93bdc1b3f0016ec070f99a20823f",
        "status": "execution-error-before-reservation",
        "torch_imported": False, "training_started": False,
    }
    descriptors = {
        "execution_manifest": _descriptor(PRIOR_MANIFEST_PATH),
        "report": _descriptor(PRIOR_REPORT_PATH),
        "verification": _descriptor(PRIOR_VERIFICATION_PATH),
        "journal": _descriptor(PRIOR_JOURNAL_PATH),
    }
    expected_descriptors = {
        "execution_manifest": {"path": PRIOR_MANIFEST_PATH, "size_bytes": 13438,
            "sha256": "6a1e2fff4c2553000d56009388f4691809fa205aabf3e8124c938b3a18c41326"},
        "report": {"path": PRIOR_REPORT_PATH, "size_bytes": 1498,
            "sha256": "a0230698ef610b514730dbc7b0b6f226560d1a014f69a5d1de97a110bb767629"},
        "verification": {"path": PRIOR_VERIFICATION_PATH, "size_bytes": 744,
            "sha256": "d3ae8f5795fc66f9a4fc05ffe0656ae99b33ecd8bb44b66d7271a3e7bdcb105c"},
        "journal": {"path": PRIOR_JOURNAL_PATH, "size_bytes": 2794,
            "sha256": "51773fc00774b4a3f781fbc96df4c5a642a436afb4bae2a581a34b1243071db2"},
    }
    if (canonical(verification) != verification_payload or verification != expected or
            descriptors != expected_descriptors or len(journal.splitlines()) != 10 or
            prior_manifest.get("self_sha256") != expected["execution_manifest_sha256"] or
            execution_digest(prior_manifest) != expected["execution_manifest_sha256"] or
            journal.count(b"ValueError: Runner argv differs from frozen invocation") != 1):
        raise ValueError("Prior navigation invocation evidence differs")
    return {
        "attempt": 1, "status": "execution-error-before-reservation",
        "output": str(PRIOR_OUTPUT), "output_created": False,
        "correction": "compare-executable-plus-python-sys-argv",
        **descriptors,
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
                      "invocation", "held_out_status", "qualification_claims",
                      "amendment", "prior_failure"}:
        raise ValueError("Execution manifest fields differ")
    if (value["schema"] != "m7-navigation-v3-matched-budget-execution-v2" or
            value["attempt"] != ATTEMPT or value["retry_allowed"] is not False or
            value["protocol_sha256"] != PROTOCOL_SHA or
            value["data_manifest_sha256"] != DATA_SHA or
            value["immutable_inputs"] != protocol()["immutable_inputs"] or
            value["runtime"] != {"python": "3.11.15", "cuda_visible_devices": "",
                                 "cpu_threads": 1} or
            value["limits"] != _limits() or value["output"] != str(OUTPUT) or
            value["pairs"] != _pair_rows() or
            value["amendment"] != _descriptor(AMENDMENT_PATH) or
            value["prior_failure"] != prior_failure() or
            value["held_out_status"] != "locked_unopened" or
            value["qualification_claims"] != []):
        raise ValueError("Frozen execution contract differs")
    sources = value["behavior_sources"]
    pinned = protocol()["behavior_source_admission"]["existing_hashes"]
    if (not isinstance(sources, dict) or set(sources) != set(static_source_roster()) or
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
    for name in static_source_roster():
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


def _lexists(path):
    return os.path.lexists(os.fspath(path))


def preflight(value):
    output = _safe_output(value["output"])
    if output != OUTPUT or output.parent != ROOT / "runs":
        raise ValueError("Exact aggregate output family required")
    if _lexists(output):
        raise FileExistsError("Enclosing training attempt is already consumed")
    if _lexists(PRIOR_OUTPUT):
        raise FileExistsError("Consumed invocation unexpectedly created output")
    for item in value["immutable_inputs"].values():
        source = Path(os.path.abspath(item["path"]))
        if output == source or output in source.parents or source in output.parents:
            raise ValueError("Output overlaps an immutable input")


def _fsync_directory(path):
    path = Path(os.path.abspath(path))
    before = os.lstat(path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                         getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    try:
        opened = os.fstat(descriptor)
        rebound = os.lstat(path)
        if (not stat.S_ISDIR(opened.st_mode) or
                (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino) or
                (opened.st_dev, opened.st_ino) != (rebound.st_dev, rebound.st_ino)):
            raise ValueError("Directory rebound during durability sync")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_bytes_new(path, payload, maximum=MAX_JSON):
    if len(payload) > maximum:
        raise ValueError("Execution receipt exceeds cap")
    path = Path(path)
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) |
             getattr(os, "O_NOFOLLOW", 0))
    descriptor = os.open(path, flags, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("New execution receipt is not a private regular file")
        view = memoryview(payload)
        while view:
            count = os.write(descriptor, view)
            if count <= 0:
                raise OSError("Short execution receipt write")
            view = view[count:]
        os.fsync(descriptor)
        rebound = os.lstat(path)
        if (rebound.st_dev, rebound.st_ino, rebound.st_nlink) != (
                info.st_dev, info.st_ino, 1):
            raise ValueError("Execution receipt path rebound during write")
    finally:
        os.close(descriptor)
    return payload


def _write_new(path, value, maximum=MAX_JSON):
    _write_bytes_new(path, canonical(value), maximum)
    return value


def _exclusive_publish(pending, final):
    """Link a durable pending file into a fresh final name without replacement."""
    pending, final = Path(pending), Path(final)
    if pending.parent != final.parent:
        raise ValueError("Publication names must share one directory")
    payload = _read(pending)
    if _lexists(final):
        raise FileExistsError(f"Publication destination already exists: {final.name}")
    os.link(pending, final, follow_symlinks=False)
    _fsync_directory(final.parent)
    os.unlink(pending)
    _fsync_directory(final.parent)
    if _read(final) != payload:
        raise ValueError("Exclusive publication bytes changed")
    return payload


def reserve_attempt(output, manifest_digest):
    """Create the enclosing output and durable no-retry marker before any child."""
    output = _safe_output(output)
    if _lexists(output):
        raise FileExistsError("Enclosing training attempt is already consumed")
    if not output.parent.is_dir():
        raise ValueError("Fresh existing aggregate parent required")
    output.mkdir(exist_ok=False)
    _fsync_directory(output.parent)
    receipt = {
        "id": "male-navigation-v3-enclosing-attempt-v2", "attempt": ATTEMPT,
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
    if not _lexists(root):
        return 0
    if not stat.S_ISDIR(os.lstat(root).st_mode):
        raise ValueError("Aggregate inventory root is not a directory")
    for directory, directories, files, descriptor in os.fwalk(root, follow_symlinks=False):
        for name in directories + files:
            entries += 1
            if entries > 1024:
                raise ValueError("Aggregate inventory exceeds entry bound")
            info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode) or (not stat.S_ISDIR(info.st_mode) and
                                              not stat.S_ISREG(info.st_mode)):
                raise ValueError("Aggregate inventory contains linked/nonregular entry")
            if stat.S_ISREG(info.st_mode):
                flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
                child = os.open(name, flags, dir_fd=descriptor)
                try:
                    opened = os.fstat(child)
                    rebound = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                    if (opened.st_dev, opened.st_ino, opened.st_nlink, opened.st_size) != (
                            rebound.st_dev, rebound.st_ino, rebound.st_nlink, rebound.st_size) or opened.st_nlink != 1:
                        raise ValueError("Aggregate inventory file rebound or is hard-linked")
                    total += opened.st_size
                finally:
                    os.close(child)
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
    root_descriptor = None
    try:
        root = Path("/proc") / str(pid)
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        root_descriptor = os.open(root, flags)
        root_identity = os.fstat(root_descriptor)

        def read(name, maximum):
            descriptor = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                                 dir_fd=root_descriptor)
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise ValueError("Unsafe proc identity member")
                chunks, remaining = [], maximum + 1
                while remaining:
                    block = os.read(descriptor, min(4096, remaining))
                    if not block:
                        break
                    chunks.append(block); remaining -= len(block)
                payload = b"".join(chunks)
                rebound = os.stat(name, dir_fd=root_descriptor, follow_symlinks=False)
                after = os.fstat(descriptor)
                if (len(payload) > maximum or
                        (opened.st_dev, opened.st_ino, opened.st_nlink) !=
                        (after.st_dev, after.st_ino, after.st_nlink) or
                        (opened.st_dev, opened.st_ino, opened.st_nlink) !=
                        (rebound.st_dev, rebound.st_ino, rebound.st_nlink)):
                    raise ValueError("Proc identity member rebound")
                return payload
            finally:
                os.close(descriptor)

        fields = read("stat", 4096).decode().rsplit(") ", 1)[1].split()
        status = dict(line.split(":", 1) for line in read("status", 64 * 1024).decode().splitlines()
                      if ":" in line)
        raw = read("cmdline", 64 * 1024).split(b"\0")
        if raw and raw[-1] == b"":
            raw.pop()
        rebound = os.stat(root, follow_symlinks=False)
        if (root_identity.st_dev, root_identity.st_ino) != (rebound.st_dev, rebound.st_ino):
            return None
        return {"pid": pid, "ppid": int(fields[1]), "group": int(fields[2]),
                "start_ticks": int(fields[19]), "state": fields[0],
                "rss_bytes": int(status.get("VmRSS", "0 kB").split()[0]) * 1024,
                "argv": [os.fsdecode(item) for item in raw],
                "command": b" ".join(raw).decode(errors="replace")[:512]}
    except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError, KeyError,
            UnicodeError, OSError):
        return None
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)


def process_group_members(group):
    rows = []
    descriptor = os.open("/proc", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                         getattr(os, "O_NOFOLLOW", 0))
    try:
        for name in os.listdir(descriptor):
            if not name.isdigit():
                continue
            row = process_identity(int(name))
            if row is not None and row["group"] == group and row["state"] != "Z":
                rows.append(row)
    finally:
        os.close(descriptor)
    return rows


def _record_group(identity, rows, known, maximum=MAX_PROCESSES):
    if identity["group"] in (os.getpid(), os.getpgrp()):
        raise ValueError("Refusing to supervise the parent process group")
    result = dict(known)
    for row in rows:
        key = (row.get("pid"), row.get("start_ticks"))
        if (any(type(item) is not int for item in key) or
                row.get("group") != identity["group"]):
            raise ValueError("Observed process escaped or changed identity")
        if key not in result and len(result) >= maximum:
            raise ValueError("Finite child process inventory exceeded")
        result[key] = {name: row.get(name) for name in
                       ("pid", "ppid", "group", "start_ticks", "state",
                        "rss_bytes", "command")}
    return result


def drain_process_group(identity, deadline, known, *, group_reader=process_group_members,
                        clock=time.monotonic, sleep=time.sleep, kill=os.killpg):
    """Drain the owned group even after its leader exits and descendants reparent."""
    signals, term_at = [], None
    while True:
        rows = group_reader(identity["group"])
        known = _record_group(identity, rows, known)
        if not rows:
            return {"drained": True, "forced": bool(signals), "signals": signals,
                    "survivors": [], "known": known}
        now = clock()
        number = (signal.SIGKILL if now >= deadline or
                  term_at is not None and now - term_at >= 3 else
                  signal.SIGTERM if term_at is None else None)
        if number is not None:
            try:
                kill(identity["group"], number)
            except ProcessLookupError:
                pass
            name = signal.Signals(number).name
            if not signals or signals[-1] != name:
                signals.append(name)
            if term_at is None:
                term_at = now
        if now >= deadline:
            survivors = group_reader(identity["group"])
            known = _record_group(identity, survivors, known)
            return {"drained": not survivors, "forced": True, "signals": signals,
                    "survivors": survivors, "known": known}
        sleep(.1)


def cleanup_spawn_group(group):
    """Terminate and prove empty a just-spawned PID-as-PGID."""
    result = drain_process_group({"group": group}, time.monotonic() + 5, {})
    if not result["drained"]:
        raise RuntimeError("Spawned process group survived cleanup")


def finish_spawn_handoff(process, handoff, *, abort=False):
    """Restore deferred handlers after the caller owns the spawned identity."""
    caught = None

    def clean():
        if process is None or handoff["cleaned"]:
            return
        handoff["cleanup"](process.pid)
        waiter = getattr(process, "wait", None)
        if waiter is not None:
            waiter(timeout=1)
        handoff["cleaned"] = True

    if abort or handoff["deferred"]:
        try:
            clean()
        except BaseException as error:
            caught = error
    for number in tuple(reversed(handoff["remaining"])):
        try:
            handoff["install_handler"](number, handoff["previous"][number])
        except BaseException as error:
            if caught is None:
                caught = error
        else:
            handoff["remaining"].remove(number)
    if (abort or handoff["deferred"] or caught is not None) and not handoff["cleaned"]:
        try:
            clean()
        except BaseException as error:
            if caught is None:
                caught = error
    if caught is not None:
        raise caught
    if handoff["deferred"]:
        raise InterruptedError(
            f"Execution interrupted by {signal.Signals(handoff['deferred'][0]).name}")


def spawn_contained(command, cwd, environment, stdout, stderr, *,
                    popen=subprocess.Popen, identity_reader=process_identity,
                    install_handler=signal.signal, cleanup=cleanup_spawn_group):
    """Return ownership plus live defer state for caller-side handoff."""
    handoff = {"deferred": [], "previous": {}, "remaining": [],
               "install_handler": install_handler, "cleanup": cleanup,
               "cleaned": False}
    process = None

    def defer(number, frame):
        handoff["deferred"].append(number)

    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            handoff["previous"][number] = install_handler(number, defer)
            handoff["remaining"].append(number)
        process = popen(command, cwd=cwd, env=environment, stdout=stdout, stderr=stderr,
                        start_new_session=True, restore_signals=True)
        current = None
        for _ in range(100):
            current = identity_reader(process.pid)
            if current is not None:
                break
            if process.poll() is not None:
                break
            time.sleep(.01)
        if (current is None or current.get("pid") != process.pid or
                current.get("ppid") != os.getpid() or current.get("group") != process.pid or
                current.get("argv") != command):
            raise ValueError("Spawned trainer PID/start/group/argv identity differs")
        owned = {key: current[key] for key in
                 ("pid", "ppid", "group", "start_ticks", "command")}
        return process, owned, handoff
    except BaseException as error:
        try:
            finish_spawn_handoff(process, handoff, abort=True)
        except BaseException as cleanup_error:
            raise cleanup_error from error
        raise


def admit_process_observation(identity, parent_pid, rows, known, maximum):
    if (not isinstance(identity, dict) or
            any(type(identity.get(key)) is not int for key in ("pid", "ppid", "group", "start_ticks")) or
            identity["pid"] != identity["group"] or identity["ppid"] != parent_pid):
        raise ValueError("Child PID/start/process-group identity differs")
    current = next((row for row in rows if row.get("pid") == identity["pid"]), None)
    if (current is None or current.get("start_ticks") != identity["start_ticks"] or
            current.get("ppid") != parent_pid or current.get("group") != identity["group"]):
        raise ValueError("Child identity disappeared, escaped, or was reused")
    return _record_group(identity, rows, known, maximum)


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
    supervision = Path(pair["output"]).parent / "supervision" / f"seed-{pair['seed']}"
    supervision.mkdir(parents=True, exist_ok=False)
    stdout_path, stderr_path = supervision / "stdout.log", supervision / "stderr.log"
    started = time.monotonic()
    known, identity, errors, signals = {}, None, [], []
    process = handoff = None
    def log_failure(message):
        if message not in errors:
            errors.append(message)

    with bounded_logs(supervision, LOG_BYTES, log_failure) as (stdout, stderr):
        try:
            process, identity, handoff = spawn_contained(
                pair["argv"], ROOT, EXACT_ENVIRONMENT, stdout, stderr)
            finish_spawn_handoff(process, handoff)
            handoff = None
            while True:
                now = time.monotonic()
                code = process.poll()
                rows = process_group_members(identity["group"])
                if code is None:
                    try:
                        known = admit_process_observation(identity, parent, rows, known,
                                                          MAX_PROCESSES)
                    except ValueError as error:
                        errors.append(str(error))
                else:
                    known = _record_group(identity, rows, known)
                    if rows:
                        errors.append("Trainer leader exited with live process-group descendants")
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
        finally:
            if handoff is not None and handoff["remaining"]:
                try:
                    finish_spawn_handoff(process, handoff, abort=True)
                except BaseException as error:
                    errors.append(f"{type(error).__name__}: {str(error)[:512]}")
    drained = ({"drained": False, "forced": False, "signals": [],
                "survivors": [], "known": known} if identity is None else
               drain_process_group(identity, deadline, known))
    known = drained["known"]
    survivors = drained["survivors"]
    for name in drained["signals"]:
        if not signals or signals[-1] != name:
            signals.append(name)
    if drained["forced"]:
        errors.append("Trainer process group required forced drain")
    if not drained["drained"]:
        errors.append("Trainer process group survived the outer deadline")
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
    before = os.lstat(root)
    if not stat.S_ISDIR(before.st_mode):
        raise ValueError("Pair inventory root is not a directory")
    names = sorted(os.listdir(root))
    if set(names) != set(PAIR_FILES):
        raise ValueError("Pair evidence inventory differs")
    result, total = {}, 0
    for name in names:
        payload = _read(root / name, PAIR_BYTES)
        total += len(payload)
        result[name] = {"sha256": _digest(payload), "size_bytes": len(payload)}
    after = os.lstat(root)
    if (names != sorted(os.listdir(root)) or
            (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino) or
            total > PAIR_BYTES):
        raise ValueError("Pair evidence exceeds payload cap")
    return result


def admit_pair(output, seed):
    output = _safe_output(output)
    if output.name != f"seed-{seed}" or seed not in SEEDS:
        raise ValueError("Wrong pair output identity")
    failure = output.with_name(output.name + ".failure.json")
    pending = (output / "report.pending", output / "publication.pending")
    if _lexists(failure) or any(_lexists(path) for path in pending):
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
    if not _lexists(path):
        _write_new(path, report)
        _fsync_directory(output)


def _publish_success(output, report, deadline):
    output = Path(output)
    pending, final = output / "report.pending", output / "report.json"
    receipt_pending, receipt = output / "publication.pending", output / "publication.json"
    if any(_lexists(path) for path in (pending, final, receipt_pending, receipt,
                                      output / "failure.json")):
        raise FileExistsError("Fresh aggregate publication paths required")
    payload = canonical(report)
    if time.monotonic() > deadline:
        raise TimeoutError("Aggregate normal-return deadline exceeded")
    _write_bytes_new(pending, payload)
    _exclusive_publish(pending, final)
    completion = {"id": "male-navigation-v3-enclosing-publication-v1",
                  "status": "durably-published",
                  "execution_manifest_sha256": report["execution_manifest_sha256"],
                  "report_sha256": _digest(payload), "report_size_bytes": len(payload),
                  "models": 6, "qualification_claims": []}
    _write_new(receipt_pending, completion)
    if time.monotonic() > deadline:
        raise TimeoutError("Aggregate normal-return deadline exceeded")
    _exclusive_publish(receipt_pending, receipt)
    if time.monotonic() > deadline:
        raise TimeoutError("Aggregate normal-return deadline exceeded")
    return completion


def success_admitted(output, manifest_digest):
    """Admit aggregate success only with six models and the durable receipt."""
    output = Path(output)
    if (any(not _lexists(output / name) for name in
            ("attempt.json", "report.json", "publication.json")) or
            any(_lexists(output / name) for name in
                ("failure.json", "report.pending", "publication.pending"))):
        return False
    try:
        attempt = _json(_read(output / "attempt.json"))
        payload = _read(output / "report.json")
        report = _json(payload)
        receipt = _json(_read(output / "publication.json"))
    except (OSError, ValueError):
        return False
    if (attempt.get("id") != "male-navigation-v3-enclosing-attempt-v2" or
            attempt.get("attempt") != ATTEMPT or
            attempt.get("execution_manifest_sha256") != manifest_digest or
            attempt.get("retry_allowed") is not False or
            report.get("status") != "completed-navigation-v3-enclosing-training" or
            report.get("training_completed") is not True or
            report.get("execution_manifest_sha256") != manifest_digest or
            len(report.get("models", ())) != 6 or
            any(report.get("pairs", {}).get(str(seed), {}).get("status") != "completed"
                for seed in SEEDS)):
        return False
    if receipt != {
        "id": "male-navigation-v3-enclosing-publication-v1",
        "status": "durably-published", "execution_manifest_sha256": manifest_digest,
        "report_sha256": _digest(payload), "report_size_bytes": len(payload),
        "models": 6, "qualification_claims": [],
    }:
        return False
    admitted_models = []
    try:
        for seed in SEEDS:
            evidence = admit_pair(output / f"seed-{seed}", seed)
            if evidence != report["pairs"][str(seed)].get("evidence"):
                return False
            admitted_models.extend(evidence["models"])
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return report["models"] == admitted_models


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
    if [sys.executable, *sys.argv] != value["invocation"]["runner_argv"]:
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
