"""Shared helpers for the MaleCNS v4 reconstructed S0d/S0e controllers (Amendment 1).

The controllers never account CPU: each runs as one stage under ``run_research_stage.py``,
which owns CPUQuota, RuntimeMaxSec, TimeoutStopSec=5 and the cgroup census. These helpers
only supervise children with wall deadlines, sample owned PID/start identities every
0.25 s (the cadence of the surviving recovery-training and collection-v2 evidence), hash
inventories and write fsynced exclusive JSON documents.
"""
import ctypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import regenerate_male_navigation_v4 as driver  # noqa: E402

ROOT = driver.ROOT
DRIVER = ROOT/'scripts/regenerate_male_navigation_v4.py'
Refusal = driver.Refusal
SAMPLE_SECONDS = 0.25
STOP_GRACE = 5
MAX_ERRORS = 32
LANE = 'navigation'
SCOPE = 'finite 0.25 s PID/start sampling with PID/start recheck before owned containment; not universal transient-process proof'
CLEAN_KEYS = ('forced_signals', 'survivors', 'sample_errors', 'conflicting_owned_identities')


# --------------------------------------------------------------------------- gates

def absolute(name, value):
    if value is None or not Path(value).is_absolute():
        raise Refusal(f'{name} must be an absolute path, got {value!r}')
    return Path(value)


def fresh(name, path):
    if Path(path).exists() or Path(path).is_symlink(): raise Refusal(f'{name} must be a fresh path: {path}')


def protocol_gate(protocol_sha256=None):
    if protocol_sha256 is not None: return protocol_sha256
    if driver.sha256_file(ROOT/driver.PROTOCOL_PATH) != driver.PROTOCOL_SHA256:
        raise Refusal('v4 protocol bytes differ from the pin')
    return driver.PROTOCOL_SHA256


def go_gate(path, stage, protocol_sha256):
    """The GO record must name exactly this stage and the protocol sha256 (driver rule)."""
    return driver.check_go(absolute('--go', path), stage, protocol_sha256)


def research_stage_unit():
    """True only inside run_research_stage.py's unit: this process sits in its ``work`` leaf."""
    try: line = Path('/proc/self/cgroup').read_text().strip().splitlines()[-1]
    except (OSError, IndexError): return False
    parts = line.split(':', 2)[-1].rstrip('/').split('/')
    return len(parts) >= 2 and parts[-1] == 'work' and parts[-2].endswith('.service')


def unit_command(stage, runtime_max_sec, argv, k=1):
    """The run_research_stage.py invocation a reviewed manifest would use (printed in plans)."""
    return [sys.executable, str(ROOT/'scripts/run_research_stage.py'), '--lane', LANE, '--stage', stage,
            '--cpu-quota-k', str(k), '--runtime-max-sec', str(runtime_max_sec),
            '--worst-case-cpu', str(k*(runtime_max_sec + STOP_GRACE)), '--ledger', '<ledger>', '--go-record', '<GO>',
            '--receipt-dir', '<fresh receipt dir>', '--', *argv]


def git_head(worktree):
    done = driver._git(worktree, 'rev-parse', 'HEAD')
    if done.returncode != 0: raise Refusal(f'Not a git worktree: {worktree}')
    return done.stdout.strip()


def port_commit(tree):
    return driver.load_ports()['trees'][tree]['port_commit']


def child_env():
    return {'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', '/nonexistent'), 'LANG': 'C.UTF-8',
            'LC_ALL': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
            'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1', 'CUDA_VISIBLE_DEVICES': '', 'MUJOCO_GL': 'egl'}


# --------------------------------------------------------------------------- documents

def sha256_bytes(payload): return hashlib.sha256(payload).hexdigest()


def digest(value): return sha256_bytes(driver.canonical(value))


def utc_now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_json(path, value):
    """Exclusive, fsynced JSON (file and directory); returns its {path, sha256, bytes} binding."""
    path = Path(path)
    payload = (json.dumps(value, indent=1, sort_keys=True, allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return {'path': str(path), 'sha256': sha256_bytes(payload), 'bytes': len(payload)}


def read_json(path, expected=None):
    raw = driver.read_bounded(path)
    if expected is not None and sha256_bytes(raw) != expected: raise Refusal(f'Bound document changed: {path}')
    return json.loads(raw)


def binding(path):
    raw = driver.read_bounded(path)
    return {'path': str(Path(path)), 'sha256': sha256_bytes(raw), 'bytes': len(raw)}


def write_controller_record(stage, stage_root, producer_records, protocol_sha256, declared_values=()):
    """Bind every controller document under <stage root>/control and the producer records it supervised.

    The driver merges this with the producer records for the next stage (driver.merge_controlled)."""
    root = Path(stage_root); control = root/'control'; target = root/driver.CONTROLLER_RECORD
    documents = {p.relative_to(root).as_posix(): {'sha256': driver.sha256_file(p), 'bytes': p.stat().st_size}
                 for p in files_under(control) if p != target}
    shas = [sha256_bytes(driver.canonical(json.loads(driver.read_bounded(p)))) for p in producer_records]
    return write_json(target, {'schema': driver.CONTROLLER_RECORD_SCHEMA, 'stage': stage, 'protocol_sha256': protocol_sha256,
                               'stage_root': str(root), 'producer_records': shas, 'documents': documents,
                               'declared_values': list(declared_values), 'qualification_claims': []})


def read_invocation(path, sha256):
    raw = driver.read_bounded(path)
    if sha256_bytes(raw) != sha256: raise Refusal('Invocation record changed after launch')
    return json.loads(raw)


# --------------------------------------------------------------------------- inventories

def files_under(path):
    path = Path(path)
    if path.is_symlink(): raise Refusal(f'Inventory refuses symlinks: {path}')
    if path.is_file(): return [path]
    if not path.is_dir(): raise Refusal(f'Inventory path is missing: {path}')
    return sorted(p for p in path.rglob('*') if p.is_file() and not p.is_symlink()
                  and not {'.git', '__pycache__'} & set(p.relative_to(path).parts))


def git_tracked(worktree):
    """Every tracked regular file (gitlinks excluded): 355 at 19d275d, so 355 in the T-d port."""
    done = subprocess.run(['git', 'ls-files', '-s', '-z'], cwd=worktree, capture_output=True, timeout=30,
                          env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
    if done.returncode != 0: raise Refusal(f'Cannot list tracked files in {worktree}')
    entries = [e.decode() for e in done.stdout.split(b'\0') if e]
    return [Path(worktree)/e.split('\t', 1)[1] for e in entries if not e.startswith('160000 ')]


def inventory(parts):
    """{part: [paths]} -> per-part {count, sha256, files} plus one overall sha256."""
    value = {}
    for name, paths in parts.items():
        files = {str(f): driver.sha256_file(f) for p in paths for f in files_under(p)}
        value[name] = {'count': len(files), 'sha256': digest(files), 'files': files}
    return {'parts': value, 'counts': {n: v['count'] for n, v in value.items()},
            'sha256': digest({n: v['sha256'] for n, v in value.items()})}


def tree_sha(path):
    path = Path(path)
    return digest({p.relative_to(path).as_posix(): driver.sha256_file(p) for p in files_under(path)}) if path.is_dir() else None


# --------------------------------------------------------------------------- processes

def set_subreaper():
    """Orphaned descendants reparent to this supervisor so the sampler and cleanup still see them."""
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0: raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')


def _stat(pid):
    try: rest = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    except (OSError, IndexError): return None
    return rest[0], int(rest[1]), int(rest[19])   # state, ppid, start ticks


def alive(pid, start):
    stat = _stat(pid)
    return stat is not None and stat[2] == start and stat[0] not in ('Z', 'X')


def descendants(pid):
    children = {}
    for entry in os.scandir('/proc'):
        if entry.name.isdigit() and (stat := _stat(entry.name)) is not None and stat[0] not in ('Z', 'X'):
            children.setdefault(stat[1], []).append((int(entry.name), stat[2]))
    found, stack = [], [pid]
    while stack:
        for child in children.get(stack.pop(), []):
            found.append(child); stack.append(child[0])
    return found


def reap():
    while True:
        try: pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError: return
        if pid == 0: return


class Sampler:
    """Every 0.25 s, record the PID/start identity of every descendant of this process."""

    def __init__(self, interval=SAMPLE_SECONDS):
        self.interval, self.identities, self.conflicts, self.errors, self.times = interval, {}, [], [], []
        self.stopped, self._stop = False, threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._thread.start(); return self

    def register(self, pid, start):
        known = self.identities.setdefault(pid, start)
        if known != start and (conflict := {'pid': pid, 'start_ticks': [known, start]}) not in self.conflicts:
            self.conflicts.append(conflict)

    def sample(self):
        try:
            for pid, start in descendants(os.getpid()): self.register(pid, start)
            self.times.append(time.monotonic())
        except Exception as error:  # retained, never hidden
            if len(self.errors) < MAX_ERRORS: self.errors.append(f'{type(error).__name__}: {error}'[:256])

    def _loop(self):
        while not self._stop.is_set():
            self.sample(); self._stop.wait(self.interval)

    def stop(self):
        self._stop.set(); self._thread.join(timeout=STOP_GRACE)
        self.stopped = not self._thread.is_alive()


def cleanup(sampler):
    """Stop the sampler; any sampled identity still alive is a survivor and is SIGKILLed (forced)."""
    sampler.stop(); reap()
    for pid, start in descendants(os.getpid()): sampler.register(pid, start)
    observed = sorted(sampler.identities.items())
    live = lambda: [{'pid': p, 'start_ticks': s} for p, s in observed if alive(p, s)]
    survivors, forced = live(), []
    for item in survivors:
        if alive(item['pid'], item['start_ticks']):   # PID/start recheck before signalling
            try: os.kill(item['pid'], signal.SIGKILL); forced.append({**item, 'signal': 'SIGKILL'})
            except ProcessLookupError: pass
    deadline = time.monotonic() + STOP_GRACE
    while live() and time.monotonic() < deadline:
        reap(); time.sleep(0.05)
    gaps = [b - a for a, b in zip(sampler.times, sampler.times[1:])]
    return {'sampler_stopped': sampler.stopped, 'sample_errors': list(sampler.errors), 'forced_signals': forced,
            'survivors': survivors, 'remaining_after_forced': live(), 'conflicting_owned_identities': list(sampler.conflicts),
            'observed_owned_processes': [{'pid': p, 'start_ticks': s} for p, s in observed],
            'samples': len(sampler.times), 'sample_seconds': sampler.interval,
            'max_sample_gap_seconds': max(gaps, default=None), 'scope': SCOPE}


def clean(cleanup_record):
    return cleanup_record.get('sampler_stopped') is True and all(cleanup_record.get(k) == [] for k in CLEAN_KEYS)


class Terminated(Exception):
    """SIGTERM from the enclosing supervisor (or the unit's stop): retain evidence, then exit."""


def on_sigterm():
    def handler(signum, frame): raise Terminated('SIGTERM received')
    signal.signal(signal.SIGTERM, handler)


def _signal_group(pid, sig):
    try: os.killpg(pid, sig)
    except ProcessLookupError: pass


def supervise(command, timeout, log_dir, *, env, cwd=None, sampler=None):
    """Run one child in its own session with a wall deadline; TERM then KILL its group on timeout."""
    log_dir = Path(log_dir); log_dir.mkdir(parents=True)
    started, started_utc = time.monotonic(), utc_now()
    with (log_dir/'stdout.log').open('xb') as out, (log_dir/'stderr.log').open('xb') as err:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, env=env, cwd=cwd,
                                 start_new_session=True)
        if sampler is not None and (stat := _stat(child.pid)) is not None: sampler.register(child.pid, stat[2])
        try:
            returncode, status = child.wait(timeout=max(timeout, 0)), 'completed'
        except BaseException as error:
            if not isinstance(error, subprocess.TimeoutExpired):   # e.g. Terminated by the enclosing supervisor
                _signal_group(child.pid, signal.SIGKILL); child.wait(); raise
            status = 'timeout'; _signal_group(child.pid, signal.SIGTERM)
            try: child.wait(STOP_GRACE)
            except subprocess.TimeoutExpired:
                _signal_group(child.pid, signal.SIGKILL); child.wait()
            returncode = child.returncode
    record = {'schema_version': 1, 'status': status, 'returncode': returncode,
              'elapsed_seconds': time.monotonic() - started, 'timeout_seconds': timeout, 'started_utc': started_utc,
              'pid': child.pid, 'command': [str(c) for c in command]}
    if status != 'completed': record['failure'] = f'wall deadline {timeout:.3f} s exceeded; process group signalled'
    return record


def emit(value):
    print(json.dumps(value, indent=1, sort_keys=True))
