"""Storage bounds for one admitted writer; no persisted accounting ledger."""
from contextlib import contextmanager
from dataclasses import dataclass
import errno
import fcntl
import os
from pathlib import Path
import shutil
import stat

MiB = 1024**2
GiB = 1024**3
MAX_SCAN_ENTRIES = 100_000
LOCK_NAME = ".palimpsest-storage.lock"


class StorageLimitError(RuntimeError):
    """A storage operation must stop before publishing more data."""


@dataclass(frozen=True)
class StorageLimits:
    max_bytes: int = 20 * GiB
    min_free_bytes: int = GiB
    max_runs: int = 1024
    max_snapshots: int = 64  # Per run, including its initial snapshot.
    max_exports: int = 1024

    def __post_init__(self):
        for name in ("max_bytes", "max_runs", "max_snapshots", "max_exports"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.min_free_bytes) is not int or self.min_free_bytes < 0:
            raise ValueError("min_free_bytes must be a nonnegative integer")


def _safe_path(path):
    result = Path(os.path.abspath(path))
    if any(part.is_symlink() for part in (result, *result.parents)):
        raise StorageLimitError("Storage paths cannot traverse symlinks")
    return result


def _nonnegative(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


class StorageBudget:
    """Recount configured roots before a write, with fixed concurrent headroom.

    The caller admits only one payload writer. Capped native logs and parent
    status files may run concurrently only within ``headroom_bytes``. Hold
    ``lock()`` for the service/CLI operation; the admitted child shares its
    parent's lease and receives this roots/limits configuration, not a new lock.
    """
    def __init__(self, roots, limits: StorageLimits, *, headroom_bytes=0):
        if not isinstance(limits, StorageLimits):
            raise TypeError("limits must be StorageLimits")
        _nonnegative(headroom_bytes, "headroom_bytes")
        self.roots = tuple(sorted({_safe_path(root) for root in roots}))
        if not self.roots:
            raise ValueError("At least one storage root is required")
        if any(root.exists() and not root.is_dir() for root in self.roots):
            raise ValueError("Storage roots must be directories")
        self.limits, self.headroom_bytes = limits, headroom_bytes
        self._count_roots = tuple(root for root in self.roots
                                  if not any(root != other and root.is_relative_to(other) for other in self.roots))

    def usage(self):
        # ponytail: O(files) recount avoids a crash-recovery ledger; one payload
        # writer and a bounded inventory are adequate for this local lab.
        total = files = entries = 0
        def scan_error(error):
            raise error
        for root in self._count_roots:
            root = _safe_path(root)
            try:
                mode = root.stat(follow_symlinks=False).st_mode
            except FileNotFoundError:
                continue
            if not stat.S_ISDIR(mode):
                raise StorageLimitError("Storage inventory root is not a directory")
            # fwalk anchors descendants to directory descriptors and guards
            # against symlink swaps without rechecking every ancestor per folder.
            for _, directories, names, descriptor in os.fwalk(root, follow_symlinks=False, onerror=scan_error):
                for name in directories + names:
                    entries += 1
                    if entries > MAX_SCAN_ENTRIES:
                        raise StorageLimitError("Storage inventory exceeds entry limit")
                    try:
                        info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                    except FileNotFoundError:
                        # Parent status files may be atomically replaced; their
                        # maximum concurrent footprint is reserved as headroom.
                        continue
                    if stat.S_ISLNK(info.st_mode):
                        raise StorageLimitError("Storage inventory contains a symlink")
                    if stat.S_ISREG(info.st_mode):
                        total += info.st_size
                        files += 1
                    elif not stat.S_ISDIR(info.st_mode):
                        raise StorageLimitError("Storage inventory contains a nonregular file")
        return {"used_bytes": total, "files": files, "remaining_bytes": max(0, self.limits.max_bytes - total),
                "max_bytes": self.limits.max_bytes, "headroom_bytes": self.headroom_bytes,
                "min_free_bytes": self.limits.min_free_bytes}

    def check(self, additional_bytes, *, path):
        _nonnegative(additional_bytes, "additional_bytes")
        destination = _safe_path(path)
        if not any(destination.is_relative_to(root) for root in self.roots):
            raise StorageLimitError("Destination is outside configured storage roots")
        report = self.usage()
        required = additional_bytes + self.headroom_bytes
        if report["used_bytes"] + required > self.limits.max_bytes:
            raise StorageLimitError(f"Storage quota exceeded: used={report['used_bytes']}, additional={additional_bytes}, "
                                    f"headroom={self.headroom_bytes}, limit={self.limits.max_bytes}")
        existing = destination
        while not existing.exists():
            existing = existing.parent
        free = shutil.disk_usage(existing).free
        if free - required < self.limits.min_free_bytes:
            raise StorageLimitError(f"Storage free-space floor reached: free={free}, additional={additional_bytes}, "
                                    f"headroom={self.headroom_bytes}, floor={self.limits.min_free_bytes}")
        return {**report, "additional_bytes": additional_bytes, "free_bytes": free}

    def check_count(self, kind, current, additional=1):
        _nonnegative(current, "current")
        _nonnegative(additional, "additional")
        if kind not in {"runs", "snapshots", "exports"}:
            raise ValueError("Count kind must be runs, snapshots or exports")
        maximum = getattr(self.limits, "max_" + kind)
        if current + additional > maximum:
            raise StorageLimitError(f"Storage {kind} count limit reached ({maximum})")

    @contextmanager
    def lock(self):
        """One payload writer per user, plus leases on each configured root."""
        streams = []
        try:
            # ponytail: A per-user ceiling also covers differently configured,
            # overlapping roots. Add overlap-aware leases only if independent
            # concurrent labs become necessary; no lease registry is needed now.
            cache = _safe_path(Path.home() / ".cache")
            cache.mkdir(mode=0o700, exist_ok=True)
            private = _safe_path(cache / "palimpsest")
            private.mkdir(mode=0o700, exist_ok=True)
            if private.stat().st_uid != os.getuid():
                raise StorageLimitError("Writer lease directory belongs to another user")
            for root in self.roots:
                _safe_path(root).mkdir(parents=True, exist_ok=True)
            paths = [private / "writer.lock", *(root / LOCK_NAME for root in self.roots)]
            for path in paths:
                path = _safe_path(path)
                flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
                writable = True
                try:
                    descriptor = os.open(path, flags, 0o600)
                except OSError as error:
                    if path != paths[0] or error.errno != errno.EROFS:
                        raise
                    # flock needs no file writes. Reuse an existing user lease
                    # on a read-only mount while preserving ownership and the
                    # same exclusive lock; never create an alternative lease.
                    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                    writable = False
                try:
                    info = os.fstat(descriptor)
                    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                        raise StorageLimitError("Writer lease must be a regular file owned by the current user")
                    stream = os.fdopen(descriptor, "r+b" if writable else "rb")
                except BaseException:
                    os.close(descriptor)
                    raise
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as error:
                    stream.close()
                    raise StorageLimitError("Storage is already owned by another writer for this user") from error
                except BaseException:
                    stream.close()
                    raise
                streams.append(stream)
            yield self
        finally:
            for stream in reversed(streams):
                fcntl.flock(stream, fcntl.LOCK_UN)
                stream.close()
