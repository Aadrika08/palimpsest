"""Bounded, inert source/backend staging; no installation or execution grant.

Callers retain input descriptor and parent-directory custody. Reads use pread;
partial output is retained on failure. Only authored staging code runs here.
"""

from contextlib import contextmanager
import gzip
import hashlib
import io
import math
import os
from pathlib import Path
import re
import stat
import tarfile
import time
import zipfile
import zlib

from .puck_package_payloads import _DescriptorReader, _identity, verify_wheel


_CHUNK = 128 * 1024
_SOURCE_RAW = 2 * 1024 * 1024
_SOURCE_DECODED = 16 * 1024 * 1024
_SOURCE_MEMBER = 2 * 1024 * 1024
_BACKEND_LIMITS = dict(max_members=4096, max_uncompressed_bytes=64 * 1024 * 1024,
                       max_member_bytes=16 * 1024 * 1024, max_metadata_bytes=4 * 1024 * 1024)


def _deadline(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("invalid staging deadline")
    if time.monotonic() >= value:
        raise ValueError("build-input staging deadline exceeded")


def _unchanged(fd, before):
    if _identity(os.fstat(fd)) != _identity(before):
        raise ValueError("archive descriptor identity changed")


def _canonical(name, directory=False):
    path = name[:-1] if directory and name.endswith("/") else name
    if not path or "\\" in path or any(ord(char) < 32 or 127 <= ord(char) < 160 for char in path):
        raise ValueError("invalid source member path")
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise ValueError("noncanonical source member path")
    return path


def _source_evidence(expected):
    if not isinstance(expected, dict) or set(expected) != {"root", "size_bytes", "sha256"}:
        raise ValueError("invalid source evidence fields")
    root = expected["root"]
    if not isinstance(root, str) or _canonical(root) != root or "/" in root:
        raise ValueError("invalid source root")
    if type(expected["size_bytes"]) is not int or not 0 < expected["size_bytes"] <= _SOURCE_RAW:
        raise ValueError("source archive size limit or evidence mismatch")
    if not isinstance(expected["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", expected["sha256"]):
        raise ValueError("invalid source SHA-256 evidence")


def _source_snapshot(fd, expected, deadline):
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != expected["size_bytes"]:
        raise ValueError("source descriptor type, links, or size mismatch")
    raw, digest = bytearray(), hashlib.sha256()
    try:
        while len(raw) < before.st_size:
            _deadline(deadline)
            block = os.pread(fd, min(_CHUNK, before.st_size - len(raw)), len(raw))
            if not block:
                raise ValueError("source archive ended while hashing")
            raw.extend(block)
            digest.update(block)
        if digest.hexdigest() != expected["sha256"]:
            raise ValueError("source archive SHA-256 mismatch")
    finally:
        _unchanged(fd, before)
    _deadline(deadline)
    return raw, before


def _decode_source(raw, deadline):
    decoded = bytearray()
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
            while True:
                _deadline(deadline)
                block = stream.read(min(_CHUNK, _SOURCE_DECODED - len(decoded) + 1))
                if not block:
                    break
                decoded.extend(block)
                if len(decoded) > _SOURCE_DECODED:
                    raise ValueError("source decoded total limit exceeded")
    except (OSError, EOFError, zlib.error) as exc:
        raise ValueError("invalid gzip source archive") from exc
    return decoded


def _tar_field(raw):
    head, separator, tail = raw.partition(b"\0")
    if separator and any(tail):
        raise ValueError("aliased tar header string")
    return head.decode("utf-8", "strict")


def _pax_mtime(data):
    # Fixed-source compatibility only: one inert POSIX per-entry mtime record.
    raw = bytes(data)
    length, separator, record = raw.partition(b" ")
    if not separator or not re.fullmatch(rb"[1-9][0-9]*", length) or int(length) != len(raw):
        raise ValueError("invalid source PAX record length")
    if not re.fullmatch(rb"mtime=-?[0-9]+(?:\.[0-9]+)?\n", record):
        raise ValueError("source PAX override is outside inert mtime support")


def _source_entries(decoded, root, deadline):
    entries, paths, offset, count, pending_pax = [], {}, 0, 0, False
    while offset < len(decoded):
        _deadline(deadline)
        header = bytes(decoded[offset:offset + 512])
        if len(header) != 512:
            raise ValueError("truncated source tar header")
        if not any(header):
            if pending_pax or len(decoded) - offset < 1024 or any(decoded[offset:]):
                raise ValueError("invalid source tar ending")
            break
        count += 1
        if count > 512:
            raise ValueError("source archive member count limit exceeded")
        try:
            info = tarfile.TarInfo.frombuf(header, "utf-8", "strict")
            name, prefix = _tar_field(header[:100]), _tar_field(header[345:500])
            name = prefix + "/" + name if prefix else name
            linkname = _tar_field(header[157:257])
        except (tarfile.HeaderError, UnicodeError, ValueError) as exc:
            raise ValueError("invalid source tar header") from exc
        if not 0 <= info.size <= _SOURCE_MEMBER:
            raise ValueError("source member byte limit exceeded")
        start, end = offset + 512, offset + 512 + info.size
        following = start + ((info.size + 511) // 512) * 512
        if following > len(decoded) or any(decoded[end:following]):
            raise ValueError("truncated source member or nonzero padding")
        data = memoryview(decoded)[start:end]
        offset = following
        if info.type == tarfile.XHDTYPE:
            if pending_pax or name != "././@PaxHeader" or linkname:
                raise ValueError("invalid or consecutive source PAX headers")
            _pax_mtime(data)
            pending_pax = True
            continue
        if info.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE) or linkname:
            raise ValueError("source links, extensions, or special members are forbidden")
        pending_pax = False
        directory = info.type == tarfile.DIRTYPE
        canonical = _canonical(name, directory)
        if directory and info.size:
            raise ValueError("source directory contains bytes")
        if canonical == root:
            if not directory:
                raise ValueError("source root must be a directory")
            path = ""
        elif canonical.startswith(root + "/"):
            path = canonical[len(root) + 1:]
        else:
            raise ValueError("source member is outside expected root")
        if path in paths:
            raise ValueError("duplicate or aliased source member")
        paths[path] = directory
        entries.append((path, directory, data))
    else:
        raise ValueError("source tar is missing end markers")
    for path in paths:
        parts = path.split("/")
        if any(paths.get("/".join(parts[:index])) is False for index in range(1, len(parts))):
            raise ValueError("source file/directory prefix collision")
    return entries


@contextmanager
def _target_tree(target):
    if not isinstance(target, Path):
        raise ValueError("staging target must be a Path")
    try:
        target.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ValueError("staging target already exists") from exc
    fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield fd
    finally:
        os.close(fd)


def _directories(root_fd, parts, deadline):
    current = os.dup(root_fd)
    try:
        for part in parts:
            _deadline(deadline)
            try:
                os.mkdir(part, mode=0o700, dir_fd=current)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _write_file(root_fd, path, blocks, *, size, sha256, deadline):
    parent = _directories(root_fd, path.split("/")[:-1], deadline)
    try:
        fd = os.open(path.rsplit("/", 1)[-1], os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        count = 0
        for block in blocks:
            _deadline(deadline)
            count += len(block)
            if count > size:
                raise ValueError("extracted member exceeds verified size")
            view = memoryview(block)
            while view:
                _deadline(deadline)
                written = os.write(fd, view)
                if not written:
                    raise ValueError("staged member write made no progress")
                view = view[written:]
        actual = os.fstat(fd)
        if count != size or actual.st_size != size or not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1:
            raise ValueError("staged member size, type, or links mismatch")
        digest, offset = hashlib.sha256(), 0
        while offset < size:
            _deadline(deadline)
            block = os.pread(fd, min(_CHUNK, size - offset), offset)
            if not block:
                raise ValueError("staged member ended during readback")
            digest.update(block)
            offset += len(block)
        if digest.hexdigest() != sha256 or _identity(os.fstat(fd)) != _identity(actual):
            raise ValueError("staged member hash or identity mismatch")
        _deadline(deadline)
        return dict(path=path, size_bytes=size, sha256=sha256)
    finally:
        os.close(fd)


def extract_source(fd: int, *, expected: dict, target: Path, deadline: float) -> dict:
    """Stage pinned gzip-tar regular bytes, stripping its one expected root."""
    _source_evidence(expected)
    _deadline(deadline)
    raw, before = _source_snapshot(fd, expected, deadline)
    try:
        entries = _source_entries(_decode_source(raw, deadline), expected["root"], deadline)
        files, directories = [], []
        with _target_tree(target) as target_fd:
            for path, directory, data in entries:
                _deadline(deadline)
                if directory:
                    if path:
                        directory_fd = _directories(target_fd, path.split("/"), deadline)
                        os.close(directory_fd)
                        directories.append(path)
                else:
                    digest = hashlib.sha256(data).hexdigest()
                    blocks = (data[offset:offset + _CHUNK] for offset in range(0, len(data), _CHUNK))
                    files.append(_write_file(target_fd, path, blocks, size=len(data), sha256=digest, deadline=deadline))
        _deadline(deadline)
        return dict(kind="source", files=sorted(files, key=lambda row: row["path"]),
                    directories=sorted(directories), total_bytes=sum(row["size_bytes"] for row in files),
                    archive_sha256=expected["sha256"])
    finally:
        _unchanged(fd, before)
        _deadline(deadline)


def _zip_blocks(archive, info, deadline):
    with archive.open(info) as member:
        while True:
            _deadline(deadline)
            block = member.read(_CHUNK)
            if not block:
                return
            yield block


def stage_backend(fd: int, *, expected: dict, target: Path, deadline: float) -> dict:
    """Stage verified wheel paths verbatim; .data relocation is unsupported."""
    _deadline(deadline)
    before = os.fstat(fd)
    if before.st_size > 2 * 1024 * 1024:
        raise ValueError("backend archive size exceeds two MiB")
    verified = verify_wheel(fd, expected=expected, limits=_BACKEND_LIMITS, deadline=deadline)
    _unchanged(fd, before)
    members = {row["path"]: row for row in verified["members"]}
    if any(path.split("/", 1)[0].endswith(".data") for path in members):
        raise ValueError("backend .data relocation tree is forbidden")
    files, directories = [], []
    try:
        with zipfile.ZipFile(_DescriptorReader(fd, before.st_size)) as archive:
            infos = archive.infolist()
            if len(infos) != len(members) or {info.filename for info in infos} != set(members):
                raise ValueError("backend inventory changed before staging")
            with _target_tree(target) as target_fd:
                for info in infos:
                    _deadline(deadline)
                    row = members[info.filename]
                    if info.is_dir():
                        directory_fd = _directories(target_fd, info.filename[:-1].split("/"), deadline)
                        os.close(directory_fd)
                        directories.append(info.filename[:-1])
                    else:
                        files.append(_write_file(target_fd, info.filename, _zip_blocks(archive, info, deadline),
                                                 size=row["size_bytes"], sha256=row["sha256"], deadline=deadline))
        return dict(kind="backend", files=sorted(files, key=lambda row: row["path"]),
                    directories=sorted(directories), total_bytes=sum(row["size_bytes"] for row in files),
                    archive_sha256=verified["sha256"], wheel_verification=verified)
    except (zipfile.BadZipFile, EOFError, zlib.error) as exc:
        raise ValueError("invalid backend payload during staging") from exc
    finally:
        _unchanged(fd, before)
        _deadline(deadline)
