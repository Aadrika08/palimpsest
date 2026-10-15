"""Build the one missing CPU wheel under a separately frozen, finite allocation.

Ordinary trusted host/tool preparation only; no numerical-runtime installation,
qualification, model inference, collection or scientific allocation is granted.
"""
from contextlib import ExitStack
import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import acquire_puck_cpu_payloads as acquisition
from palimpsest.bounded_qualification import hard_guard, publication_directory, read_control, reserve_output, supervised, write_new
from palimpsest.puck_build_inputs import extract_source, stage_backend
from palimpsest.puck_execution_files import _HeldFileCore, _identity, _relative
from palimpsest.puck_package_payloads import verify_wheel

MiB = 1024 ** 2
canonical = acquisition.canonical
INTERPRETER = "/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11"
SOURCE_ARCHIVE = "runs/puck-cpu-payload-acquisition-01/archives/python-louvain-0.16.tar.gz"
BASELINE_PATH = "docs/plans/puck-python-louvain-host-baseline-v1.json"
OUTPUT = "runs/puck-python-louvain-build-02"
WHEEL_NAME = "python_louvain-0.16-py3-none-any.whl"
FIXTURE_NAME = "palimpsest_build_fixture-0.0-py3-none-any.whl"
BACKEND = dict(name="setuptools", version="84.0.0", filename="setuptools-84.0.0-py3-none-any.whl",
    url="https://files.pythonhosted.org/packages/95/9c/c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/setuptools-84.0.0-py3-none-any.whl",
    size_bytes=818216, sha256="51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670",
    metadata_sha256="3ef2975718dd31cabdd5829455e9b868ca14dbf79ed8fed2de0af4e87347006e", format="wheel")
LIMITS = dict(normal_seconds=120, hard_seconds=135, socket_seconds=20,
    rss_bytes=768 * MiB, output_bytes=128 * MiB, scratch_bytes=256 * MiB,
    min_free_bytes=2048 * MiB, min_available_ram_bytes=1024 * MiB,
    max_members=4096, max_uncompressed_bytes=64 * MiB,
    max_member_bytes=16 * MiB, max_metadata_bytes=4 * MiB,
    max_wheel_bytes=256 * 1024, log_bytes_per_stream=MiB,
    max_processes=3, max_worker_fds=128, worker_address_space_bytes=512 * MiB,
    worker_cpu_seconds=60, worker_file_bytes=8 * MiB)
CLAIMS = dict(installed=False, runtime_qualified=False, collection_authorized=False,
              study_authorized=False, numerical_runtime_authorized=False, qualification_claims=[])
CODE_PATHS = tuple(sorted(("scripts/build_puck_python_louvain.py", "scripts/puck_python_louvain_worker.py",
    "scripts/acquire_puck_cpu_payloads.py", "src/palimpsest/__init__.py",
    "src/palimpsest/bounded_qualification.py", "src/palimpsest/evaluate.py",
    "src/palimpsest/puck_execution_files.py", "src/palimpsest/puck_package_payloads.py",
    "src/palimpsest/puck_build_inputs.py", "docs/plans/puck-python-louvain-build-v1.md",
    "docs/plans/puck-python-louvain-build-v2.md", "pyproject.toml", "uv.lock")))
PYTHON_SYSTEM_FILES = ["/usr/lib/ld-linux-x86-64.so.2", "/usr/lib/libc.so.6", "/usr/lib/libdl.so.2",
    "/usr/lib/libm.so.6", "/usr/lib/libpthread.so.0", "/usr/lib/librt.so.1", "/usr/lib/libutil.so.1"]


def clock(deadline):
    acquisition.clock(deadline)


def file_row(path, deadline, *, single_link=True):
    clock(deadline)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_size > 64 * MiB
                or (single_link and before.st_nlink != 1)):
            raise ValueError("Build input is not a bounded regular file")
        count, digest = 0, hashlib.sha256()
        while True:
            clock(deadline)
            raw = os.read(fd, min(128 * 1024, 64 * MiB + 1 - count))
            if not raw: break
            count += len(raw)
            if count > 64 * MiB: raise ValueError("Build file grew beyond its cap")
            digest.update(raw)
        if (count != before.st_size or _identity(before) != _identity(os.fstat(fd))
                or _identity(before) != _identity(Path(path).lstat())):
            raise ValueError("Build file changed during hashing")
        return dict(size_bytes=count, sha256=digest.hexdigest())
    finally:
        os.close(fd)


def prefix_inventory(prefix, deadline):
    files, links, total = [], [], 0
    for directory, directories, names in os.walk(prefix, followlinks=False):
        clock(deadline)
        for name in sorted([*directories, *names]):
            path = Path(directory) / name
            relative = path.relative_to(prefix).as_posix()
            state = path.lstat()
            if stat.S_ISLNK(state.st_mode):
                target = os.readlink(path)
                try:
                    resolved = path.resolve(strict=True)
                except OSError as error:
                    raise ValueError("Dangling trusted host prefix symlink") from error
                if not resolved.is_relative_to(prefix):
                    raise ValueError("Host prefix symlink leaves the declared prefix")
                links.append([relative, target])
                if name in directories: directories.remove(name)
            elif stat.S_ISREG(state.st_mode):
                row = file_row(path, deadline, single_link=False)
                total += row["size_bytes"]
                files.append([relative, row["size_bytes"], row["sha256"]])
            elif not stat.S_ISDIR(state.st_mode):
                raise ValueError("Special file in trusted host prefix")
            if len(files) + len(links) > 10000 or total > 256 * MiB:
                raise ValueError("Host prefix census exceeded fixed bounds")
    result = dict(files=sorted(files), symlinks=sorted(links))
    result["prefix_manifest_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result


def verify_baseline(baseline, deadline):
    prefix = Path(baseline["python_prefix"])
    actual = prefix_inventory(prefix, deadline)
    for key in ("files", "symlinks", "prefix_manifest_sha256"):
        if actual[key] != baseline[key]:
            raise ValueError("Trusted host Python baseline changed: " + key)
    rows = [*baseline["external_libraries"]]
    if baseline["bwrap_executable"] is not None:
        rows.append(baseline["bwrap_executable"])
    for row in rows:
        path = row.get("realpath", row.get("path"))
        expected = dict(size_bytes=row["size"], sha256=row["sha256"])
        if file_row(Path(path), deadline, single_link=False) != expected:
            raise ValueError("Trusted host executable/library baseline changed")
    return dict(prefix_manifest_sha256=actual["prefix_manifest_sha256"],
        regular_file_count=len(actual["files"]), symlink_count=len(actual["symlinks"]),
        regular_file_bytes=sum(row[1] for row in actual["files"]), external_file_count=len(rows))


def verify_tree(root, manifest, deadline):
    expected = {row["path"]: row for row in manifest["files"]}
    directories = set(manifest.get("directories", []))
    for path in expected:
        _relative(path)
        directories.update(str(parent) for parent in Path(path).parents if str(parent) != ".")
    actual, actual_dirs = {}, set()
    for directory, names, files in os.walk(root, followlinks=False):
        clock(deadline)
        for name in names:
            path = Path(directory) / name
            if not stat.S_ISDIR(path.lstat().st_mode): raise ValueError("Staged directory type changed")
            actual_dirs.add(path.relative_to(root).as_posix())
        for name in files:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            actual[relative] = dict(path=relative, **file_row(path, deadline))
        if len(actual) > 4096 or len(actual_dirs) > 4096: raise ValueError("Staged namespace cap exceeded")
    if actual != expected or actual_dirs != directories:
        raise ValueError("Staged namespace or bytes changed")


def write_bytes_new(path, raw):
    with publication_directory(path.parent) as parent:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            view = memoryview(raw)
            while view:
                count = os.write(fd, view)
                if count < 1: raise OSError("Build publication made no progress")
                view = view[count:]
            os.fsync(fd)
            if _identity(os.fstat(fd)) != _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)):
                raise ValueError("Build publication edge changed")
            os.fsync(parent)
        finally:
            os.close(fd)


def decode_transport(row, filename):
    keys = {"kind", "filename", "size_bytes", "sha256", "wheel_base64", "source_build_executed", "forbidden_modules_absent", "backend_version"}
    if (type(row) is not dict or set(row) != keys or row["kind"] != "wheel-build-worker-v1"
            or row["filename"] != filename or row["source_build_executed"] is not True
            or row["forbidden_modules_absent"] is not True or row["backend_version"] != "84.0.0"
            or type(row["size_bytes"]) is not int or not 0 < row["size_bytes"] <= LIMITS["max_wheel_bytes"]
            or type(row["wheel_base64"]) is not str or len(row["wheel_base64"]) > 4 * ((LIMITS["max_wheel_bytes"] + 2) // 3)):
        raise ValueError("Worker wheel transport differs from the fixed contract")
    try:
        raw = base64.b64decode(row["wheel_base64"], validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("Invalid wheel base64 transport") from error
    if len(raw) != row["size_bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
        raise ValueError("Wheel transport size/hash differs")
    return raw


def run_stage(command, stage, root, normal, hard, state):
    write_new(stage / "invocation.json", dict(argv=command))
    observed = supervised(command, stage, cwd=root, normal_deadline=normal, hard_deadline=hard,
        rss_bytes=LIMITS["rss_bytes"], output_bytes=4 * MiB, min_free_bytes=LIMITS["min_free_bytes"],
        max_processes=3, output_root=stage, guard_state=state)
    write_new(stage / "supervision.json", observed)
    if observed["status"] != "completed":
        raise RuntimeError("Build stage failed within its fixed allocation")
    return read_control(stage / "stdout.log")


def sandbox_command(baseline, source, backend, mode_args):
    prefix = baseline["python_prefix"]
    command = ["/usr/bin/bwrap", "--unshare-all", "--unshare-user", "--die-with-parent", "--disable-userns",
        "--cap-drop", "ALL", "--clearenv", "--hostname", "palimpsest-wheel-build",
        "--ro-bind", prefix, prefix, "--dir", "/usr/lib"]
    for path in PYTHON_SYSTEM_FILES:
        command.extend(["--ro-bind", path, path])
    for path, target in baseline["host_path_aliases"]:
        command.extend(["--symlink", target, path])
    command.extend(["--ro-bind", str(source), "/source", "--ro-bind", str(backend), "/backend",
        "--ro-bind", str(ROOT / "scripts/puck_python_louvain_worker.py"), "/driver.py",
        "--size", str(LIMITS["scratch_bytes"]), "--tmpfs", "/work"])
    for name in ("home", "tmp", "build", "egg", "wheel-output"):
        command.extend(["--dir", "/work/" + name])
    command.extend(["--symlink", "work/tmp", "/tmp", "--proc", "/proc", "--remount-ro", "/proc",
        "--dev", "/dev", "--remount-ro", "/dev", "--remount-ro", "/"])
    for key, value in dict(HOME="/work/home", TMPDIR="/work/tmp", PATH="/nonexistent",
            LC_ALL="C.UTF-8", LANG="C.UTF-8", TZ="UTC", SOURCE_DATE_EPOCH="1720000000").items():
        command.extend(["--setenv", key, value])
    command.extend(["--chdir", "/source", INTERPRETER, "-I", "-S", "-B", "/driver.py", *mode_args])
    return command


def publish_wheel(stage, row, filename, name, version, deadline):
    raw = decode_transport(row, filename)
    path = stage / filename
    write_bytes_new(path, raw)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        result = verify_wheel(fd, expected=dict(name=name, version=version, filename=filename,
            size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), metadata_sha256=None),
            limits=dict(max_members=256, max_uncompressed_bytes=2 * MiB,
                        max_member_bytes=512 * 1024, max_metadata_bytes=512 * 1024), deadline=deadline)
    finally:
        os.close(fd)
    write_new(stage / "wheel-verification.json", result)
    return result


def make_fixture(path):
    path.mkdir(mode=0o700)
    (path / "fixture_package").mkdir(mode=0o700)
    (path / "bin").mkdir(mode=0o700)
    files = {"setup.py": b'from setuptools import setup\nsetup(name="palimpsest-build-fixture", version="0.0", packages=["fixture_package"], scripts=["bin/fixture"], install_requires=["not-installed-for-fixture>=1"])\n',
        "setup.cfg": b"[egg_info]\ntag_build =\ntag_date = 0\n",
        "fixture_package/__init__.py": b"raise RuntimeError('fixture package must never import')\n",
        "bin/fixture": b"#!/usr/bin/env python\nraise RuntimeError('fixture script must never execute')\n"}
    rows = []
    for name, raw in sorted(files.items()):
        write_bytes_new(path / name, raw)
        rows.append(dict(path=name, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    return dict(kind="authored-fixture", files=rows, directories=["bin", "fixture_package"], total_bytes=sum(row["size_bytes"] for row in rows))


def load_configuration(root, relative, expected_hash):
    _relative(relative)
    row = dict(path=relative, size_bytes=(root / relative).lstat().st_size, sha256=expected_hash)
    config = acquisition.pinned_json(root, row, time.monotonic() + 15)
    keys = {"kind", "version", "sources", "source_archive", "host_baseline", "backend", "output", "limits", "claims"}
    if (type(config) is not dict or set(config) != keys or config["kind"] != "puck-python-louvain-build-v1"
            or type(config["version"]) is not int or config["version"] != 1
            or canonical(config["limits"]) != canonical(LIMITS)
            or canonical(config["backend"]) != canonical(BACKEND)
            or canonical(config["claims"]) != canonical(CLAIMS)
            or config["output"] != OUTPUT):
        raise ValueError("Wheel build configuration differs from the fixed prospective contract")
    for item in [*config["sources"], config["source_archive"], config["host_baseline"]]:
        acquisition.descriptor(item)
    if ([item["path"] for item in config["sources"]] != list(CODE_PATHS)
            or config["host_baseline"]["path"] != BASELINE_PATH
            or config["source_archive"] != dict(path=SOURCE_ARCHIVE, size_bytes=204641,
                sha256="b7ba2df5002fd28d3ee789a49532baad11fe648e4f2117cf0798e7520a1da56b")
            or str(Path(sys.executable).resolve()) != INTERPRETER):
        raise ValueError("Build source/interpreter closure differs")
    return config, row


def source_rows(config, config_row):
    rows = [*config["sources"], config["source_archive"], config["host_baseline"], config_row]
    if len({row["path"] for row in rows}) != len(rows): raise ValueError("Duplicate build source path")
    return sorted(rows, key=lambda row: row["path"])


def retained_namespace(output, deadline):
    count = total = dirs = 0
    for directory, directories, files in os.walk(output, followlinks=False):
        clock(deadline)
        dirs += len(directories)
        for name in directories:
            if not stat.S_ISDIR((Path(directory) / name).lstat().st_mode): raise ValueError("Unexpected retained directory")
        for name in files:
            state = (Path(directory) / name).lstat()
            if not stat.S_ISREG(state.st_mode) or state.st_nlink != 1: raise ValueError("Unexpected retained file")
            count += 1
            total += state.st_size
        if count > 8192 or dirs > 4096 or total > LIMITS["output_bytes"]: raise ValueError("Retained build namespace exceeds limits")
    return dict(files=count, directories=dirs, size_bytes=total)


def parent(root, relative, config_hash, started):
    config, config_row = load_configuration(root, relative, config_hash)
    normal, hard = started + LIMITS["normal_seconds"], started + LIMITS["hard_seconds"]
    if os.environ.get("LD_PRELOAD") or os.environ.get("LD_LIBRARY_PATH"):
        raise ValueError("Undeclared loader environment")
    if acquisition.available_ram() < LIMITS["min_available_ram_bytes"] or shutil.disk_usage(root).free < LIMITS["min_free_bytes"]:
        raise ValueError("Build resource preflight failed")
    output = root / config["output"]
    rows = source_rows(config, config_row)
    # Verify before reservation; then reopen through terminal publication.
    with _HeldFileCore(root, rows, normal, limits=(32, 4 * MiB, 16 * MiB)) as held:
        baseline = json.loads(held.read(config["host_baseline"]["path"], MiB))
        if (baseline["python_prefix"] + "/bin/python3.11" != INTERPRETER
                or baseline["recommended_python_system_files"] != PYTHON_SYSTEM_FILES
                or baseline["host_path_aliases"] != [["/lib", "usr/lib"], ["/lib64", "usr/lib"], ["/usr/lib64", "lib"]]
                or baseline["bwrap_executable"]["path"] != "/usr/bin/bwrap"):
            raise ValueError("Unsupported trusted host baseline")
        verify_baseline(baseline, normal)
    reserve_output(output, {"sources": {"root": str(root), "files": rows}})
    for name in ("inputs", "fixture", "build"):
        (output / name).mkdir(mode=0o700)
    (output / "inputs/archives").mkdir(mode=0o700)
    write_new(output / "configuration.json", config)
    result = dict(kind="puck-python-louvain-build-result-v1", version=1,
        status="failed", configuration_sha256=config_hash, started_unix=time.time(),
        backend_request_state="not_started", authored_fixture_build="not_started", target_source_build="not_started", **CLAIMS)
    state = {}
    with hard_guard(hard, state):
        try:
            with _HeldFileCore(root, rows, normal, limits=(32, 4 * MiB, 16 * MiB)) as held:
                before = verify_baseline(baseline, normal)
                write_new(output / "baseline-before.json", before)
                archives = output / "inputs/archives"
                source_copy = archives / "python-louvain-0.16.tar.gz"
                write_bytes_new(source_copy, held.read(config["source_archive"]["path"], 2 * MiB))
                result["backend_request_state"] = "invoked"
                verified_backend, request = acquisition.download_archive(BACKEND, archives, LIMITS, normal)
                result["backend_request_state"] = "completed"
                result["request"] = request
                write_new(output / "backend-archive-verification.json", verified_backend)
                fd = os.open(source_copy, os.O_RDONLY | os.O_NOFOLLOW)
                try:
                    source_manifest = extract_source(fd, expected=dict(root="python-louvain-0.16", size_bytes=204641,
                        sha256=config["source_archive"]["sha256"]), target=output / "inputs/source", deadline=normal)
                finally: os.close(fd)
                fd = os.open(archives / BACKEND["filename"], os.O_RDONLY | os.O_NOFOLLOW)
                try:
                    backend_manifest = stage_backend(fd, expected={k: BACKEND[k] for k in ("name", "version", "filename", "size_bytes", "sha256", "metadata_sha256")},
                        target=output / "inputs/backend", deadline=normal)
                finally: os.close(fd)
                fixture_manifest = make_fixture(output / "inputs/fixture")
                for name, manifest in (("source", source_manifest), ("backend", backend_manifest), ("fixture", fixture_manifest)):
                    write_new(output / (name + "-manifest.json"), manifest)
                    verify_tree(output / "inputs" / name, manifest, normal)
                retained_namespace(output, normal)
                held.recheck()
                probe_command = sandbox_command(baseline, output / "inputs/fixture", output / "inputs/backend",
                    ["probe", os.readlink("/proc/self/ns/net"), str(root)])
                probe_result = run_stage(probe_command, output / "outer", root, normal, hard, state)
                if probe_result.get("kind") != "wheel-build-namespace-probe-v1" or probe_result.get("status") != "passed":
                    raise ValueError("Namespace preflight did not pass")
                write_new(output / "namespace-preflight.json", probe_result)
                result["authored_fixture_build"] = "invoked"
                fixture_result = run_stage(sandbox_command(baseline, output / "inputs/fixture", output / "inputs/backend", ["build", FIXTURE_NAME]),
                    output / "fixture", root, normal, hard, state)
                fixture_wheel = publish_wheel(output / "fixture", fixture_result, FIXTURE_NAME, "palimpsest-build-fixture", "0.0", normal)
                result["authored_fixture_build"] = "completed"
                for name, manifest in (("source", source_manifest), ("backend", backend_manifest), ("fixture", fixture_manifest)):
                    verify_tree(output / "inputs" / name, manifest, normal)
                held.recheck()
                retained_namespace(output, normal)
                result["target_source_build"] = "invoked"
                target_result = run_stage(sandbox_command(baseline, output / "inputs/source", output / "inputs/backend", ["build", WHEEL_NAME]),
                    output / "build", root, normal, hard, state)
                wheel = publish_wheel(output / "build", target_result, WHEEL_NAME, "python-louvain", "0.16", normal)
                if sorted(wheel["metadata"]["requires_dist"]) != ["networkx", "numpy"]:
                    raise ValueError("Target wheel requirements differ from reviewed source")
                result["target_source_build"] = "completed"
                for name, manifest in (("source", source_manifest), ("backend", backend_manifest), ("fixture", fixture_manifest)):
                    verify_tree(output / "inputs" / name, manifest, normal)
                after = verify_baseline(baseline, normal)
                if before != after: raise ValueError("Trusted host baseline changed")
                write_new(output / "baseline-after.json", after)
                held.recheck()
                result["wheel"] = {k: wheel[k] for k in ("filename", "size_bytes", "sha256", "metadata_sha256", "member_count", "uncompressed_bytes")}
                result["fixture_wheel_sha256"] = fixture_wheel["sha256"]
                result["retained_namespace_before_outcome"] = retained_namespace(output, normal)
            clock(normal)
            result["status"] = "wheel_verified"
        except Exception as error:
            result["error_type"], result["error"] = type(error).__name__, str(error)
        result["elapsed_seconds"] = time.monotonic() - started
        write_new(output / "outcome.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    if os.getpgrp() != os.getpid(): os.setsid()
    started = time.monotonic()
    with hard_guard(started + LIMITS["hard_seconds"], {}):
        result = parent(ROOT, args.configuration, args.sha256, started)
        print(canonical(result).decode().strip(), flush=True)
    # Publication, both guard teardowns and flushed stdout are included. A late
    # return fails even if artifact verification had already been published.
    clock(started + LIMITS["normal_seconds"])
    return 0 if result["status"] == "wheel_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
