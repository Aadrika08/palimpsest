"""Acquire the exact CPU candidate's archives; never install or import them.

This is ordinary trusted preparation tooling, not a hostile-code sandbox.
A successful outcome verifies payloads only and grants no numerical/runtime use.
"""
from contextlib import ExitStack
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from palimpsest.bounded_qualification import (
    hard_guard, publication_directory, read_control, reserve_output,
    supervised, write_new,
)
from palimpsest.puck_execution_files import _HeldFileCore, _identity, _relative
from palimpsest.puck_package_payloads import verify_wheel

MiB = 1024 ** 2
CODE_PATHS = (
    "scripts/acquire_puck_cpu_payloads.py",
    "src/palimpsest/__init__.py",
    "src/palimpsest/bounded_qualification.py",
    "src/palimpsest/evaluate.py",
    "src/palimpsest/puck_execution_files.py",
    "src/palimpsest/puck_package_payloads.py",
    "docs/plans/puck-cpu-payload-acquisition-v1.md",
    "pyproject.toml", "uv.lock",
)
CEILINGS = {
    "normal_seconds": 600, "hard_seconds": 615, "socket_seconds": 20,
    "rss_bytes": 1024 * MiB, "address_space_bytes": 2048 * MiB,
    "output_bytes": 512 * MiB, "max_download_bytes": 400 * MiB,
    "max_archive_bytes": 256 * MiB, "max_requests": 71,
    "max_uncompressed_bytes": 2048 * MiB, "max_members": 32768,
    "max_member_bytes": 1024 * MiB, "max_metadata_bytes": 4 * MiB,
    "max_report_bytes": 16 * MiB, "max_output_files": 160,
    "max_output_directories": 3, "max_fds": 256,
}
FALSE_CLAIMS = {
    "installed": False, "source_build_executed": False,
    "numerical_imports_executed": False, "runtime_qualified": False,
    "collection_authorized": False, "study_authorized": False,
    "executable": False, "licence_contents_audited": False,
    "qualification_claims": [],
}
HOSTS = {"files.pythonhosted.org", "download-r2.pytorch.org"}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_hash(value):
    if type(value) is not str or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError("Expected lowercase SHA-256")
    return value


def positive(value, maximum, label):
    if type(value) is not int or not 0 < value <= maximum:
        raise ValueError("Invalid " + label)
    return value


def descriptor(value):
    if type(value) is not dict or set(value) != {"path", "size_bytes", "sha256"}:
        raise ValueError("Invalid source descriptor")
    _relative(value["path"])
    positive(value["size_bytes"], 32 * MiB, "source size")
    exact_hash(value["sha256"])
    return value


def pinned_json(root, row, deadline):
    descriptor(row)
    with _HeldFileCore(root, [row], deadline, limits=(1, 32 * MiB, 32 * MiB)) as held:
        raw = held.read(row["path"], 4 * MiB)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def bad(value):
        raise ValueError("Nonfinite JSON value")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)


def load_configuration(root, relative, expected_sha256):
    _relative(relative)
    exact_hash(expected_sha256)
    path = root / relative
    # The size is only an opening bound; the supplied SHA authenticates every byte.
    row = {"path": relative, "size_bytes": path.lstat().st_size,
           "sha256": expected_sha256}
    value = pinned_json(root, row, time.monotonic() + 20)
    keys = {"kind", "version", "candidate", "assessment", "sources",
            "interpreter", "output", "limits", "claims"}
    if type(value) is not dict or set(value) != keys:
        raise ValueError("Invalid acquisition configuration fields")
    if value["kind"] != "puck-cpu-payload-acquisition-v1" or type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("Unsupported acquisition configuration")
    if type(value["claims"]) is not dict or canonical(value["claims"]) != canonical(FALSE_CLAIMS):
        raise ValueError("Acquisition cannot grant installation/runtime/study authority")
    for key in ("candidate", "assessment"):
        descriptor(value[key])
    sources = value["sources"]
    if type(sources) is not list:
        raise ValueError("Missing source capsule")
    for source in sources:
        descriptor(source)
    if [s["path"] for s in sources] != sorted(CODE_PATHS):
        raise ValueError("Acquisition source closure differs")
    output = _relative(value["output"])
    if re.fullmatch(r"runs/puck-cpu-payload-acquisition-[0-9]{2}", output) is None:
        raise ValueError("A separately numbered acquisition output is required")
    limits = value["limits"]
    if type(limits) is not dict or set(limits) != set(CEILINGS) | {"min_free_bytes", "min_available_ram_bytes"}:
        raise ValueError("Invalid acquisition limits")
    for name, maximum in CEILINGS.items():
        positive(limits[name], maximum, name)
    for name in ("min_free_bytes", "min_available_ram_bytes"):
        positive(limits[name], 1024 ** 5, name)
    if limits["normal_seconds"] >= limits["hard_seconds"]:
        raise ValueError("Missing cleanup clock reserve")
    if limits["address_space_bytes"] < limits["rss_bytes"]:
        raise ValueError("Address space limit is below the sampled RSS threshold")
    interp = value["interpreter"]
    if type(interp) is not dict or set(interp) != {"path", "size_bytes", "sha256"}:
        raise ValueError("Invalid interpreter identity")
    path = Path(interp["path"])
    if not path.is_absolute() or str(path) != interp["path"] or any(p in (".", "..") for p in path.parts):
        raise ValueError("Interpreter path is not canonical")
    positive(interp["size_bytes"], 64 * MiB, "interpreter size")
    exact_hash(interp["sha256"])
    if Path(sys.executable).resolve() != path:
        raise ValueError("Acquisition interpreter differs")
    return value, row


def select_archives(candidate, assessment):
    if (candidate.get("kind") != "puck-cpu-runtime-candidate-v1"
            or candidate.get("version") != 1
            or assessment.get("kind") != "puck-cpu-wheel-metadata-assessment-v1"
            or assessment.get("version") != 1):
        raise ValueError("Unsupported candidate/metadata evidence")
    pins = candidate["target"]["candidate_pins"]
    if (type(pins) is not list or pins != sorted(set(pins))
            or type(candidate["target"]["candidate_pin_count"]) is not int
            or candidate["target"]["candidate_pin_count"] != len(pins)):
        raise ValueError("Candidate distribution set differs")
    rows = []
    for wheel in assessment["wheels"]:
        rows.append({
            "name": wheel["name"], "version": wheel["version"],
            "filename": wheel["filename"], "url": wheel["url"],
            "size_bytes": wheel["archive_bytes"],
            "sha256": wheel["archive_sha256_index_declared"],
            "metadata_sha256": wheel["metadata_sha256"], "format": "wheel",
        })
    missing = assessment["missing"]
    if (len(missing) != 1 or missing[0]["name"] != "python-louvain"
            or missing[0]["version"] != "0.16"):
        raise ValueError("Unresolved source dependency differs")
    source = missing[0]["sdist"]
    if not source["hash"].startswith("sha256:"):
        raise ValueError("Source archive requires SHA-256")
    rows.append({
        "name": "python-louvain", "version": "0.16",
        "filename": urllib.parse.unquote(urllib.parse.urlsplit(source["url"]).path.rsplit("/", 1)[-1]),
        "url": source["url"], "size_bytes": source["size"],
        "sha256": source["hash"][7:], "metadata_sha256": None, "format": "sdist",
    })
    if sorted(r["name"] + "==" + r["version"] for r in rows) != pins:
        raise ValueError("Selected archives do not cover exactly the candidate")
    if len({r["filename"] for r in rows}) != len(rows):
        raise ValueError("Archive filename collision")
    for row in rows:
        positive(row["size_bytes"], CEILINGS["max_archive_bytes"], "archive size")
        exact_hash(row["sha256"])
        if row["metadata_sha256"] is not None:
            exact_hash(row["metadata_sha256"])
        url = urllib.parse.urlsplit(row["url"])
        if (url.scheme != "https" or url.netloc not in HOSTS
                or url.query or url.fragment
                or urllib.parse.unquote(url.path.rsplit("/", 1)[-1]) != row["filename"]):
            raise ValueError("Archive URL is outside the exact supported HTTPS hosts")
        if (re.fullmatch(r"[A-Za-z0-9_.+-]{1,255}", row["filename"]) is None
                or row["filename"] in (".", "..")):
            raise ValueError("Archive filename is not a safe leaf")
    return sorted(rows, key=lambda row: row["name"])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Package acquisition does not follow redirects")


def clock(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("Package acquisition deadline exhausted")


def write_report(path, value, maximum):
    raw = canonical(value)
    if len(raw) > maximum:
        raise ValueError("Payload manifest exceeds its byte cap")
    with publication_directory(path.parent) as parent:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        try:
            remaining = memoryview(raw)
            while remaining:
                written = os.write(fd, remaining)
                if written < 1:
                    raise OSError("Payload manifest made no write progress")
                remaining = remaining[written:]
            os.fsync(fd)
            expected = _identity(os.fstat(fd))
            if (expected[-1] != 1 or not os.path.samestat(os.fstat(fd), os.stat(path.name, dir_fd=parent, follow_symlinks=False))
                    or _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) != expected):
                raise RuntimeError("Payload manifest publication changed")
            os.fsync(parent)
        finally:
            os.close(fd)


def download_archive(spec, archive_root, limits, deadline):
    clock(deadline)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(spec["url"], headers={"Accept-Encoding": "identity",
        "User-Agent": "Palimpsest-pinned-payload-preparation/1"})
    leaf = spec["filename"]
    count = 0
    started = time.monotonic()
    with publication_directory(archive_root) as parent:
        fd = os.open(leaf, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        try:
            timeout = min(limits["socket_seconds"], max(.001, deadline - time.monotonic()))
            with opener.open(request, timeout=timeout) as response:
                if response.status != 200 or response.geturl() != spec["url"]:
                    raise ValueError("Archive response is not the exact HTTP200 URL")
                length = response.headers.get("Content-Length", "")
                if not length.isascii() or not length.isdecimal() or int(length) != spec["size_bytes"]:
                    raise ValueError("Archive HTTP size differs from pin")
                if response.headers.get("Content-Encoding", "identity") != "identity":
                    raise ValueError("Encoded HTTP archive body is unsupported")
                hasher = hashlib.sha256()
                while True:
                    clock(deadline)
                    block = response.read(min(65536, spec["size_bytes"] + 1 - count))
                    clock(deadline)
                    if not block:
                        break
                    count += len(block)
                    if count > spec["size_bytes"]:
                        raise ValueError("Archive body exceeds pinned size")
                    hasher.update(block)
                    remaining = memoryview(block)
                    while remaining:
                        written = os.write(fd, remaining)
                        if written < 1:
                            raise OSError("Archive write made no progress")
                        remaining = remaining[written:]
                if count != spec["size_bytes"] or hasher.hexdigest() != spec["sha256"]:
                    raise ValueError("Archive body size or SHA-256 differs")
            os.fsync(fd)
            if spec["format"] == "wheel":
                expected = {key: spec[key] for key in
                    ("name", "version", "filename", "size_bytes", "sha256", "metadata_sha256")}
                wheel_limits = {key: limits[key] for key in
                    ("max_members", "max_uncompressed_bytes", "max_member_bytes", "max_metadata_bytes")}
                result = verify_wheel(fd, expected=expected, limits=wheel_limits, deadline=deadline)
            else:
                result = {key: spec[key] for key in ("name", "version", "filename", "size_bytes", "sha256")}
                result.update(archive_payload_verified=True, source_members_inspected=False,
                              source_build_executed=False)
            clock(deadline)
            before = _identity(os.fstat(fd))
            if before != _identity(os.stat(leaf, dir_fd=parent, follow_symlinks=False)) or before[-1] != 1:
                raise RuntimeError("Archive output edge changed")
            # Keep names and single-link identity stable for the concurrent monitor.
            # A file is accepted only with its verified manifest and audited outcome.
            os.fsync(parent)
        finally:
            os.close(fd)
    clock(deadline)
    return result, {"url": spec["url"], "status": 200, "body_bytes": count,
                    "elapsed_seconds": time.monotonic() - started}


def source_rows(config, config_row):
    rows = [*config["sources"], config["candidate"], config["assessment"], config_row]
    if len({row["path"] for row in rows}) != len(rows):
        raise ValueError("Duplicate preparation input path")
    return sorted(rows, key=lambda row: row["path"])


def hold_inputs(stack, root, config, config_row, deadline):
    held = stack.enter_context(_HeldFileCore(root, source_rows(config, config_row), deadline,
                        limits=(32, 32 * MiB, 64 * MiB)))
    interp = config["interpreter"]
    stack.enter_context(_HeldFileCore(Path(interp["path"]).parent,
        [{"path": Path(interp["path"]).name, "size_bytes": interp["size_bytes"], "sha256": interp["sha256"]}],
        deadline, limits=(1, 64 * MiB, 64 * MiB)))
    return held


def selected_inputs(held, config):
    candidate = json.loads(held.read(config["candidate"]["path"], 4 * MiB))
    assessment = json.loads(held.read(config["assessment"]["path"], 4 * MiB))
    if config["assessment"] not in candidate["evidence"]:
        raise ValueError("Assessment descriptor is not bound by the CPU candidate")
    specs = select_archives(candidate, assessment)
    limits = config["limits"]
    if (len(specs) > limits["max_requests"]
            or any(r["size_bytes"] > limits["max_archive_bytes"] for r in specs)
            or sum(r["size_bytes"] for r in specs) > limits["max_download_bytes"]):
        raise ValueError("Selected archive plan exceeds the acquisition allocation")
    return specs


def worker(root, relative, config_hash):
    config, config_row = load_configuration(root, relative, config_hash)
    limits = config["limits"]
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits["max_fds"], limits["max_fds"]))
    resource.setrlimit(resource.RLIMIT_AS, (limits["address_space_bytes"], limits["address_space_bytes"]))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits["max_archive_bytes"], limits["max_archive_bytes"]))
    output = root / config["output"]
    deadline = time.monotonic() + limits["normal_seconds"]
    results = []
    requests = []
    total_members = total_expanded = 0
    with ExitStack() as stack:
        held = hold_inputs(stack, root, config, config_row, deadline)
        specs = selected_inputs(held, config)
        for spec in specs:
            held.recheck()
            result, request = download_archive(spec, output / "archives", limits, deadline)
            requests.append(request)
            total_members += result.get("member_count", 0)
            total_expanded += result.get("uncompressed_bytes", 0)
            if total_members > limits["max_members"] or total_expanded > limits["max_uncompressed_bytes"]:
                raise ValueError("Aggregate decoded package namespace exceeds its allocation")
            report = output / "manifests" / (spec["filename"] + ".json")
            write_report(report, result, limits["max_report_bytes"])
            raw = canonical(result)
            results.append({"name": spec["name"], "version": spec["version"],
                "filename": spec["filename"], "archive_sha256": spec["sha256"],
                "manifest": str(report.relative_to(output)),
                "manifest_size_bytes": len(raw), "manifest_sha256": digest(raw),
                "format": spec["format"]})
        held.recheck()
    clock(deadline)
    result = {"kind": "puck-cpu-payload-worker-result-v1", "version": 1,
        "status": "payloads_verified", "configuration_sha256": config_hash,
        "artifacts": results, "requests": requests,
        "archive_count": len(results), "wheel_count": sum(r["format"] == "wheel" for r in results),
        "downloaded_bytes": sum(r["body_bytes"] for r in requests),
        "wheel_member_count": total_members, "wheel_uncompressed_bytes": total_expanded,
        **FALSE_CLAIMS}
    write_new(output / "worker-result.json", result)
    clock(deadline)
    return result


def available_ram():
    for row in Path("/proc/meminfo").read_text().splitlines():
        if row.startswith("MemAvailable:"):
            return int(row.split()[1]) * 1024
    raise RuntimeError("MemAvailable is unavailable")


def parent(root, relative, config_hash, *, started=None):
    if started is None:
        started = time.monotonic()
    config, config_row = load_configuration(root, relative, config_hash)
    limits = config["limits"]
    if os.environ.get("LD_PRELOAD") or os.environ.get("LD_LIBRARY_PATH"):
        raise ValueError("Acquisition requires the declared ordinary loader baseline")
    if (available_ram() < limits["min_available_ram_bytes"]
            or shutil.disk_usage(root).free < limits["min_free_bytes"]):
        raise ValueError("Acquisition resource preflight failed")
    # Check all identities and selection before reserving the new owned output.
    with ExitStack() as stack:
        held = hold_inputs(stack, root, config, config_row, time.monotonic() + 30)
        specs = selected_inputs(held, config)
    output = root / config["output"]
    reserve_output(output, {"sources": {"root": str(root), "files": source_rows(config, config_row)}})
    (output / "archives").mkdir(mode=0o700)
    (output / "manifests").mkdir(mode=0o700)
    write_new(output / "configuration.json", config)
    normal = started + limits["normal_seconds"]
    hard = started + limits["hard_seconds"]
    state = {}
    result = {"kind": "puck-cpu-payload-acquisition-result-v1", "version": 1,
        "status": "failed", "configuration_sha256": config_hash,
        "expected_archive_count": len(specs), "started_unix": time.time(), **FALSE_CLAIMS}
    with hard_guard(hard, state):
        try:
            with ExitStack() as stack:
                held = hold_inputs(stack, root, config, config_row, normal)
                command = [config["interpreter"]["path"], "-I", "-S", "-B",
                    str(root / "scripts/acquire_puck_cpu_payloads.py"),
                    "--configuration", relative, "--sha256", config_hash, "--worker"]
                observed = supervised(command, output / "outer", cwd=root,
                    normal_deadline=normal, hard_deadline=hard, rss_bytes=limits["rss_bytes"],
                    output_bytes=limits["output_bytes"], min_free_bytes=limits["min_free_bytes"],
                    max_processes=1, output_root=output, guard_state=state,
                    output_namespace_limits=(limits["max_output_files"], limits["max_output_directories"]))
                result["supervision"] = observed
                held.recheck()
                if observed["status"] != "completed":
                    raise RuntimeError("Payload worker did not complete within its allocation")
                worker_result = read_control(output / "worker-result.json")
                if (worker_result["status"] != "payloads_verified"
                        or worker_result["configuration_sha256"] != config_hash
                        or worker_result["archive_count"] != len(specs)):
                    raise ValueError("Payload worker terminal result differs")
                result["worker_result_sha256"] = digest(canonical(worker_result))
                result["archive_count"] = worker_result["archive_count"]
                result["wheel_count"] = worker_result["wheel_count"]
                result["downloaded_bytes"] = worker_result["downloaded_bytes"]
                held.recheck()
            clock(normal)
            result["status"] = "payloads_verified"
        except Exception as error:
            result["error_type"] = type(error).__name__
            result["error"] = str(error)
        result["elapsed_seconds"] = time.monotonic() - started
        write_new(output / "outcome.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker and os.getpgrp() != os.getpid():
        os.setsid()
    if args.worker:
        result = worker(ROOT, args.configuration, args.sha256)
    else:
        started = time.monotonic()
        # Also bound configuration/preflight startup in the dedicated outer group.
        with hard_guard(started + CEILINGS["hard_seconds"], {}):
            result = parent(ROOT, args.configuration, args.sha256, started=started)
    print(canonical(result).decode().strip())
    return 0 if result["status"] == "payloads_verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
