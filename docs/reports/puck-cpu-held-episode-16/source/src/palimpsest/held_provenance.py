"""Doctor-schema diagnostics for a held runtime, derived only from supplied pins.

The ambient doctor inspects the live host (git/nvidia-smi subprocesses,
importlib.metadata, platform, /proc, disk). A held worker instead passes this
record, built from inputs its registration already authenticated: the
interpreter pin, the upstream file roster, the registered distribution rows, the
lock hash and the frozen environment. Nothing here discovers, imports or executes.
"""
import copy
import hashlib
import json
import re


# Mirrors palimpsest.doctor without importing its host-inspection dependencies.
UPSTREAM_PIN = "8d964599119b420de67ee259434d273651a1a76d"
SIMULATION_DISTRIBUTIONS = (
    "torch", "torchvision", "numpy", "scipy", "pandas", "scikit-learn",
    "mujoco", "gymnasium", "glfw", "opencv-python", "matplotlib", "seaborn",
    "networkx", "python-louvain", "py7zr",
)
PYTHON_REQUIRED = "Python 3.11; uv sync --extra simulation"
HARDWARE = "Physical hardware has not been assessed; simulation setup does not qualify a rover"
NOT_INSPECTED = "not inspected in the held runtime"
_HEX64 = re.compile(r"[0-9a-f]{64}")
_HEX40 = re.compile(r"[0-9a-f]{40}")
_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_DISTRIBUTION = re.compile(r"[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?")
_TOKEN = object()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _text(value, maximum=4096):
    if type(value) is not str or not value or len(value) > maximum or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("Held provenance requires bounded printable text")
    return value


def _absolute(value):
    _text(value)
    if not value.startswith("/") or any(part in ("", ".", "..") for part in value[1:].split("/")):
        raise ValueError("Held provenance requires a canonical absolute path")
    return value


def _relative(value):
    _text(value)
    if value.startswith("/") or "\\" in value or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("Held provenance requires a canonical relative path")
    return value


def _fields(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError("Held provenance input has unexpected fields")
    return value


def _hash(value):
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        raise ValueError("Held provenance requires an exact lowercase SHA256")
    return value


def _size(value):
    if type(value) is not int or not 0 <= value <= 2**40:
        raise ValueError("Held provenance requires a bounded integer size")
    return value


def _normalized(name):
    return re.sub(r"[-_.]+", "-", name).lower()


class HeldProvenance:
    """One immutable held diagnostics record; Engine/replay accept only this exact type."""
    __slots__ = ("_raw", "_sha256")

    def __init__(self, token, raw):
        if token is not _TOKEN or type(raw) is not bytes:
            raise TypeError("HeldProvenance is created only by held_provenance()")
        self._raw = raw
        self._sha256 = hashlib.sha256(raw).hexdigest()

    @property
    def sha256(self):
        return self._sha256

    def report(self):
        """A fresh doctor-schema report; callers can never mutate the record."""
        return json.loads(self._raw)


def held_provenance(*, interpreter, upstream, distributions, palimpsest_version, lock_sha256, environment):
    """Build the record from authenticated pins only; refuse malformed inputs."""
    interpreter = copy.deepcopy(_fields(interpreter, ("path", "size_bytes", "sha256", "python_version")))
    _absolute(interpreter["path"]); _size(interpreter["size_bytes"]); _hash(interpreter["sha256"])
    if type(interpreter["python_version"]) is not str or _VERSION.fullmatch(interpreter["python_version"]) is None:
        raise ValueError("Held provenance requires an exact interpreter version")
    _fields(upstream, ("path", "commit", "files"))
    _absolute(upstream["path"])
    if type(upstream["commit"]) is not str or _HEX40.fullmatch(upstream["commit"]) is None:
        raise ValueError("Held provenance requires an exact upstream commit")
    files = upstream["files"]
    if type(files) is not list or not 1 <= len(files) <= 4096:
        raise ValueError("Held provenance requires a bounded upstream file roster")
    rows = []
    for row in files:
        _fields(row, ("path", "size_bytes", "sha256"))
        rows.append(dict(path=_relative(row["path"]), size_bytes=_size(row["size_bytes"]), sha256=_hash(row["sha256"])))
    if [row["path"] for row in rows] != sorted({row["path"] for row in rows}):
        raise ValueError("Held provenance requires a sorted unique upstream file roster")
    if type(distributions) is not list or len(distributions) > 4096:
        raise ValueError("Held provenance requires bounded registered distribution rows")
    versions = {}
    for row in distributions:
        _fields(row, ("name", "version", "root_index", "metadata_path"))
        name, version = _text(row["name"], 512), _text(row["version"], 128)
        if _DISTRIBUTION.fullmatch(name) is None or type(row["root_index"]) is not int or row["root_index"] < 0:
            raise ValueError("Held provenance requires registered distribution rows")
        _relative(row["metadata_path"])
        if _normalized(name) in versions:
            raise ValueError("Held provenance requires unique registered distributions")
        versions[_normalized(name)] = version
    _text(palimpsest_version, 128); _hash(lock_sha256)
    if type(environment) is not dict or len(environment) > 128:
        raise ValueError("Held provenance requires the frozen environment mapping")
    for key, value in environment.items():
        if (type(key) is not str or not key or "=" in key or "\x00" in key or type(value) is not str
                or "\x00" in value or len((key + value).encode()) > 4096):
            raise ValueError("Held provenance requires an exact string environment")

    checks = []
    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})
    version = interpreter["python_version"]
    add("python", "ok" if version.startswith("3.11.") else "error",
        {"version": version, "executable": interpreter["path"], "required": PYTHON_REQUIRED})
    add("platform", "info", {"platform": NOT_INSPECTED, "machine": NOT_INSPECTED})
    add("dependency:palimpsest", "ok", palimpsest_version)
    for distribution in SIMULATION_DISTRIBUTIONS:
        found = versions.get(_normalized(distribution))
        if found is None:
            add(f"dependency:{distribution}", "missing", "Not a registered held distribution")
        else:
            add(f"dependency:{distribution}", "ok", found)
    # The authenticated file roster replaces git; a held tree cannot be dirty.
    add("upstream", "ok" if upstream["commit"] == UPSTREAM_PIN else "error",
        {"path": upstream["path"], "commit": upstream["commit"], "expected_commit": UPSTREAM_PIN,
         "dirty": False, "changes": []})
    add("ram", "info", NOT_INSPECTED)
    add("disk", "info", NOT_INSPECTED)
    add("gpu", "info", {"devices": [], "source": NOT_INSPECTED})
    add("assets", "info", NOT_INSPECTED)
    backend = environment.get("MUJOCO_GL", "platform default")
    add("renderer", "info", {"requested_backend": backend,
        "backend_selection": "explicit MUJOCO_GL" if "MUJOCO_GL" in environment else "MuJoCo platform default",
        "probed": False, "command": "palimpsest doctor --probe-renderer"})
    add("hardware", "info", HARDWARE)
    add("held-provenance", "info", {"kind": "puck-held-provenance-v1", "interpreter": interpreter,
        "upstream": {"commit": upstream["commit"], "file_count": len(rows),
                     "files_sha256": hashlib.sha256(_canonical(rows)).hexdigest()},
        "distributions_sha256": hashlib.sha256(_canonical(sorted(versions.items()))).hexdigest(),
        "environment_sha256": hashlib.sha256(_canonical(environment)).hexdigest(),
        "lock_sha256": lock_sha256, "scope": "authenticated registration pins; " + NOT_INSPECTED + " host"})
    report = {"schema_version": 1, "checks": checks,
              "ready": all(check["status"] not in {"missing", "error"} for check in checks)}
    return HeldProvenance(_TOKEN, _canonical(report))
