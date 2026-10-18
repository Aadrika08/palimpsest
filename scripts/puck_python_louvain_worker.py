"""Fixed pure-Python wheel worker. Run only inside the reviewed build namespace."""
import base64
import contextlib
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import socket
import stat
import sys

WHEEL_CAP = 256 * 1024
WORK_BYTES = 256 * 1024 ** 2
# Linux x86_64 ABI, checked against asm/unistd_64.h. No subprocess or session
# changes are needed by this fixed pure-Python build. Filter installation fails
# closed; this is not a claim of a complete hostile-code sandbox.
DENIED_SYSCALLS = (56, 57, 58, 59, 101, 109, 112, 272, 308, 322, 435)
FORBIDDEN = {"community", "numpy", "networkx", "torch", "torchvision", "mujoco", "fixture_package"}


class BlockTarget:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in FORBIDDEN:
            raise ImportError("Target/numerical import is outside the wheel build: " + fullname)
        return None


def disable_process_changes():
    if sys.platform != "linux" or os.uname().machine != "x86_64":
        raise ValueError("Fixed build filter requires Linux x86_64")
    class Filter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                    ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint32)]
    class Program(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(Filter))]
    # Check audit architecture, then refuse x32 and the fixed native syscalls.
    rows = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xc000003e), (0x06, 0, 0, 0x80000000),
            (0x20, 0, 0, 0), (0x35, 0, 1, 0x40000000), (0x06, 0, 0, 0x80000000)]
    for number in DENIED_SYSCALLS:
        rows.extend([(0x15, 0, 1, number), (0x06, 0, 0, 0x00050000 | errno.EPERM)])
    rows.append((0x06, 0, 0, 0x7fff0000))
    filters = (Filter * len(rows))(*(Filter(*row) for row in rows))
    program = Program(len(rows), filters)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise OSError(ctypes.get_errno(), "Cannot install fixed build process filter")


def initialise():
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError("Worker requires -I -S -B")
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 ** 2,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 ** 2,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    disable_process_changes()
    sys.meta_path.insert(0, BlockTarget())


def readonly(directory):
    if not os.statvfs(directory).f_flag & os.ST_RDONLY:
        raise ValueError("Build input/root mount is not read-only: " + directory)
    if directory == "/proc":
        # procfs refuses creating arbitrary root files even on writable mounts.
        # Its kernel-reported read-only mount flag is the relevant check.
        return
    path = Path(directory) / ".palimpsest-write-refusal"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as error:
        if error.errno not in (errno.EROFS, errno.EACCES, errno.EPERM):
            raise
        return
    else:
        os.close(fd)
        raise ValueError("Unexpected writable input/root: " + directory)


def probe(host_net_namespace, hidden_host_path):
    if os.readlink("/proc/self/ns/net") == host_net_namespace:
        raise ValueError("Host network namespace was retained")
    if Path(hidden_host_path).exists():
        raise ValueError("Host project is visible inside the build namespace")
    if os.environ.get("HOME") != "/work/home" or list(Path("/work/home").iterdir()):
        raise ValueError("Build HOME is not fresh and empty")
    expected_env = {"HOME", "TMPDIR", "PATH", "LC_ALL", "LANG", "TZ", "SOURCE_DATE_EPOCH", "PWD"}
    if set(os.environ) != expected_env or os.environ.get("PWD") != "/source" or os.getcwd() != "/source":
        raise ValueError("Worker inherited an undeclared environment")
    for path in ("/", "/source", "/backend", sys.prefix, "/dev", "/proc"):
        readonly(path)
    space = os.statvfs("/work")
    if space.f_blocks * space.f_frsize != WORK_BYTES:
        raise ValueError("Private scratch filesystem has a different capacity")
    (Path("/work/tmp") / "probe").write_bytes(b"scratch")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("192.0.2.1", 9))
        except OSError as error:
            if error.errno not in (errno.ENETUNREACH, errno.EHOSTUNREACH):
                raise
        else:
            raise ValueError("External route is available in private network namespace")
    libc = ctypes.CDLL(None, use_errno=True)
    for number in DENIED_SYSCALLS:
        ctypes.set_errno(0)
        result = libc.syscall(number, 0, 0, 0, 0, 0, 0)
        if result != -1 or ctypes.get_errno() != errno.EPERM:
            os._exit(9)
    return dict(kind="wheel-build-namespace-probe-v1", status="passed",
        private_net_namespace=os.readlink("/proc/self/ns/net"),
        private_pid_namespace=os.readlink("/proc/self/ns/pid"),
        scratch_capacity_bytes=WORK_BYTES, inputs_readonly=True,
        host_project_hidden=True, empty_home=True, external_route_absent=True,
        denied_syscalls=list(DENIED_SYSCALLS), isolated=True, no_site=True)


def pack_wheel(directory, expected_filename):
    if not re.fullmatch(r"[A-Za-z0-9_]+-[A-Za-z0-9_.]+-py3-none-any\.whl", expected_filename):
        raise ValueError("Unexpected output wheel name")
    path = Path(directory) / expected_filename
    if list(Path(directory).iterdir()) != [path]:
        raise ValueError("Build must produce exactly its expected wheel")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= WHEEL_CAP:
            raise ValueError("Wheel output is not a bounded single-link regular file")
        raw = os.pread(fd, WHEEL_CAP + 1, 0)
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mode, s.st_nlink, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) != before.st_size or identity(before) != identity(after):
            raise ValueError("Wheel changed during bounded read")
    finally:
        os.close(fd)
    return dict(filename=expected_filename, size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(), wheel_base64=base64.b64encode(raw).decode("ascii"))


def build(expected_filename):
    if any(name.split(".", 1)[0] in FORBIDDEN for name in sys.modules):
        raise ValueError("Target/numerical module was already imported")
    sys.path.insert(0, "/backend")
    with contextlib.redirect_stdout(sys.stderr):
        import setuptools
        from setuptools import build_meta
        if setuptools.__version__ != "84.0.0":
            raise ValueError("Backend version differs")
        settings = {"--global-option": ["--no-user-cfg", "build", "--build-base", "/work/build",
                    "egg_info", "--egg-base", "/work/egg"],
                    "--build-option": ["--bdist-dir", "/work/bdist"]}
        name = build_meta.build_wheel("/work/wheel-output", config_settings=settings)
    if name != expected_filename or any(key.split(".", 1)[0] in FORBIDDEN for key in sys.modules):
        raise ValueError("Wheel name or target-import boundary differs")
    return dict(kind="wheel-build-worker-v1", **pack_wheel("/work/wheel-output", name),
        source_build_executed=True, forbidden_modules_absent=True, backend_version=setuptools.__version__)


def main():
    initialise()
    if len(sys.argv) == 4 and sys.argv[1] == "probe":
        result = probe(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3 and sys.argv[1] == "build":
        result = build(sys.argv[2])
    else:
        raise ValueError("Unsupported fixed worker invocation")
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    main()
