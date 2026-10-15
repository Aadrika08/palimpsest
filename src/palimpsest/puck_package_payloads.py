"""Offline wheel byte verification, with no extraction or package execution.

The caller owns pathname and descriptor custody. This preparation check grants
no installation, runtime, scientific, or licence-audit acceptance. Descriptor
reads use pread, preserving the caller's offset and keeping its descriptor open.
"""

import base64
import csv
from email import policy
from email.parser import BytesParser
import hashlib
import io
import itertools
import math
import os
import re
import stat
import struct
import time
import zipfile
import zlib


_CHUNK = 128 * 1024
_HASHES = ("sha256", "sha384", "sha512")


def _check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise ValueError("wheel verification deadline exceeded")


class _DescriptorReader:
    """A private seek position over a caller-owned descriptor."""

    def __init__(self, fd, size):
        self.fd, self.size, self.position = fd, size, 0

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset + (0 if whence == 0 else self.position if whence == 1 else self.size)
        if self.position < 0:
            raise ValueError("negative archive offset")
        return self.position

    def seekable(self):
        return True

    def read(self, size=-1):
        if size < 0:
            size = max(0, self.size - self.position)
        data = os.pread(self.fd, size, self.position)
        self.position += len(data)
        return data


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _normal_name(value):
    return re.sub(r"[-_.]+", "-", value).lower()


def _single(message, key):
    values = message.get_all(key, [])
    if len(values) != 1:
        raise ValueError(f"wheel requires exactly one {key} field")
    return str(values[0])


def _check_record(data, files, record_path):
    rows = {}
    try:
        for row in csv.reader(io.StringIO(data.decode("utf-8"), newline=""), strict=True):
            if len(row) != 3 or row[0] in rows:
                raise ValueError("invalid or duplicate RECORD row")
            rows[row[0]] = row[1:]
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("invalid wheel RECORD") from exc
    if set(rows) != set(files):
        raise ValueError("RECORD does not cover exactly the archive files")
    for path, (encoded, size) in rows.items():
        if path == record_path:
            if encoded or size:
                raise ValueError("RECORD must leave its own hash and size empty")
            continue
        try:
            algorithm, digest = encoded.split("=", 1)
            if algorithm not in _HASHES or not re.fullmatch(r"[A-Za-z0-9_-]+", digest):
                raise ValueError("unsupported RECORD hash")
            wanted = base64.urlsafe_b64decode(digest + "=" * (-len(digest) % 4))
            if wanted != files[path]["digests"][algorithm]:
                raise ValueError("RECORD hash mismatch")
            if not re.fullmatch(r"0|[1-9][0-9]*", size) or int(size) != files[path]["row"]["size_bytes"]:
                raise ValueError("RECORD size mismatch")
        except (ValueError, KeyError) as exc:
            raise ValueError(f"invalid RECORD evidence for {path}") from exc


def _evidence(expected, limits, deadline):
    expected_keys = {"name", "version", "filename", "size_bytes", "sha256", "metadata_sha256"}
    limit_keys = {"max_members", "max_uncompressed_bytes", "max_member_bytes", "max_metadata_bytes"}
    if not isinstance(expected, dict) or set(expected) != expected_keys:
        raise ValueError("invalid expected wheel evidence fields")
    if not isinstance(limits, dict) or set(limits) != limit_keys:
        raise ValueError("invalid wheel limit fields")
    if any(type(value) is not int or value <= 0 for value in limits.values()):
        raise ValueError("wheel limits must be positive integers")
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError("invalid wheel deadline")
    if any(not isinstance(expected[key], str) for key in ("name", "version", "filename", "sha256")):
        raise ValueError("invalid wheel identity fields")
    if type(expected["size_bytes"]) is not int or expected["size_bytes"] <= 0:
        raise ValueError("invalid wheel size evidence")
    for key in ("sha256", "metadata_sha256"):
        value = expected[key]
        if key == "metadata_sha256" and value is None:
            continue
        if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
            raise ValueError("invalid wheel SHA-256 evidence")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", expected["name"]):
        raise ValueError("expected wheel name must be normalized")
    filename = expected["filename"]
    tokens = filename[:-4].split("-") if filename.endswith(".whl") else []
    if len(tokens) not in (5, 6) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.]*", tokens[0]):
        raise ValueError("invalid wheel filename")
    if _normal_name(tokens[0]) != expected["name"] or tokens[1] not in (expected["version"], re.sub(r"[^A-Za-z0-9.]+", "_", expected["version"])):
        raise ValueError("wheel filename identity mismatch")
    if not re.fullmatch(r"[A-Za-z0-9.!+_]+", expected["version"]) or (len(tokens) == 6 and not re.fullmatch(r"[0-9][A-Za-z0-9_]*", tokens[2])):
        raise ValueError("invalid wheel version or build tag")
    return f"{tokens[0]}-{tokens[1]}.dist-info", _tags("-".join(tokens[-3:]))


def _tags(value):
    parts = value.split("-")
    if len(parts) != 3 or any(not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", part) for part in parts):
        raise ValueError("invalid wheel compatibility tag")
    return {"-".join(items) for items in itertools.product(*(part.split(".") for part in parts))}


def _canonical_path(path, directory=False):
    bare = path[:-1] if directory else path
    if not bare or "\\" in path or any(ord(char) < 32 or 127 <= ord(char) < 160 for char in path):
        raise ValueError("invalid wheel member path")
    parts = bare.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("noncanonical wheel member path")
    return bare


def _check_members(infos, dist_info, limits, deadline):
    if len(infos) > limits["max_members"]:
        raise ValueError("wheel member count limit exceeded")
    paths, total = {}, 0
    for info in infos:
        _check_deadline(deadline)
        directory = info.is_dir()
        path = _canonical_path(info.orig_filename, directory)
        if info.orig_filename != info.filename or path in paths:
            raise ValueError("duplicate or aliased wheel member")
        paths[path] = directory
        mode = stat.S_IFMT(info.external_attr >> 16)
        allowed = (0, stat.S_IFDIR) if directory else (0, stat.S_IFREG)
        if mode not in allowed or (directory and info.file_size):
            raise ValueError("special member or directory containing bytes")
        if info.flag_bits & 0x41 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ValueError("encrypted or unsupported compressed wheel member")
        root = path.split("/", 1)[0]
        if root.endswith(".dist-info") and root != dist_info:
            raise ValueError("wheel contains a different dist-info identity")
        if path in (dist_info + "/RECORD.jws", dist_info + "/RECORD.p7s"):
            raise ValueError("signed wheels are outside this preparation verifier")
        total += info.file_size
        if info.file_size > limits["max_member_bytes"] or total > limits["max_uncompressed_bytes"]:
            raise ValueError("declared wheel decompression limit exceeded")
    for path in paths:
        parts = path.split("/")
        if any(paths.get("/".join(parts[:index])) is False for index in range(1, len(parts))):
            raise ValueError("wheel file/directory prefix collision")


def _member_blocks(fd, info, *, limit, deadline):
    """Read only stored/raw-deflate payloads, independently checking actual size."""
    header = os.pread(fd, 30, info.header_offset)
    if len(header) != 30 or header[:4] != b"PK\x03\x04":
        raise ValueError("invalid wheel local header")
    flags, method = struct.unpack_from("<HH", header, 6)
    if flags != info.flag_bits or method != info.compress_type:
        raise ValueError("wheel local flags or compression mismatch")
    name_size, extra_size = struct.unpack_from("<HH", header, 26)
    offset = info.header_offset + 30 + name_size + extra_size
    remaining, count, crc = info.compress_size, 0, 0
    decoder = zlib.decompressobj(-15) if info.compress_type == zipfile.ZIP_DEFLATED else None
    while remaining:
        _check_deadline(deadline)
        data = os.pread(fd, min(_CHUNK, remaining), offset)
        if not data:
            raise ValueError("truncated wheel compressed payload")
        offset += len(data)
        remaining -= len(data)
        while data:
            _check_deadline(deadline)
            if decoder is not None:
                block = decoder.decompress(data, min(_CHUNK, limit - count + 1))
                data = decoder.unconsumed_tail
                if decoder.unused_data:
                    raise ValueError("trailing data in wheel deflate payload")
            else:
                block, data = data, b""
            count += len(block)
            if count > limit:
                raise ValueError("actual wheel decompression limit exceeded")
            crc = zlib.crc32(block, crc)
            if block:
                yield block
    if decoder is not None and not decoder.eof:
        raise ValueError("incomplete wheel deflate payload")
    if count != info.file_size or crc != info.CRC:
        raise ValueError("wheel actual size or CRC mismatch")


def verify_wheel(fd: int, *, expected: dict, limits: dict, deadline: float) -> dict:
    """Verify pinned bytes and wheel records; reject invalid evidence with ValueError.

    deadline is an absolute time.monotonic() deadline. The caller retains FD and
    path custody. Reads preserve its offset, and the FD stays open. This fixed
    preparation verifier accepts stored/deflated, unsigned wheels; it is not an
    installer or a hostile-code sandbox and grants no host/runtime acceptance.
    """
    dist_info, filename_tags = _evidence(expected, limits, deadline)
    _check_deadline(deadline)
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != expected["size_bytes"]:
        raise ValueError("wheel descriptor type, links, or size mismatch")
    digest = hashlib.sha256()
    offset = 0
    while offset < before.st_size:
        _check_deadline(deadline)
        block = os.pread(fd, min(_CHUNK, before.st_size - offset), offset)
        if not block:
            raise ValueError("wheel ended while hashing")
        digest.update(block)
        offset += len(block)
    archive_sha256 = digest.hexdigest()
    if archive_sha256 != expected["sha256"]:
        raise ValueError("wheel archive SHA-256 mismatch")
    _check_deadline(deadline)
    metadata_path, wheel_path, record_path = (dist_info + "/" + name for name in ("METADATA", "WHEEL", "RECORD"))
    special_paths = {metadata_path, wheel_path, record_path}
    collected, files, special = [], {}, {}
    total = 0
    try:
        with zipfile.ZipFile(_DescriptorReader(fd, before.st_size)) as archive:
            infos = archive.infolist()
            _check_members(infos, dist_info, limits, deadline)
            for info in infos:
                _check_deadline(deadline)
                # Let zipfile validate local filename, overlap and header flags,
                # then stream the bytes ourselves instead of trusting file_size.
                with archive.open(info):
                    pass
                hashes = {name: hashlib.new(name) for name in _HASHES}
                chunks, count = [], 0
                cap = min(limits["max_member_bytes"], limits["max_uncompressed_bytes"] - total)
                if info.filename in special_paths:
                    cap = min(cap, limits["max_metadata_bytes"])
                if info.file_size > cap:
                    raise ValueError("wheel member or metadata limit exceeded")
                for block in _member_blocks(fd, info, limit=cap, deadline=deadline):
                    count += len(block)
                    for item in hashes.values():
                        item.update(block)
                    if info.filename in special_paths:
                        chunks.append(block)
                total += count
                row = dict(path=info.filename, size_bytes=count, sha256=hashes["sha256"].hexdigest(), mode=info.external_attr >> 16)
                collected.append(row)
                if not info.is_dir():
                    files[info.filename] = dict(row=row, digests={name: item.digest() for name, item in hashes.items()})
                if info.filename in special_paths:
                    special[info.filename] = b"".join(chunks)
            if not special_paths <= set(files):
                raise ValueError("wheel is missing METADATA, WHEEL, or RECORD")
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error, struct.error) as exc:
        raise ValueError("invalid wheel ZIP payload") from exc

    metadata_sha256 = hashlib.sha256(special[metadata_path]).hexdigest()
    if expected["metadata_sha256"] is not None and metadata_sha256 != expected["metadata_sha256"]:
        raise ValueError("wheel metadata SHA-256 mismatch")
    special[metadata_path].decode("utf-8")
    metadata = BytesParser(policy=policy.default).parsebytes(special[metadata_path])
    name, version = _single(metadata, "Name"), _single(metadata, "Version")
    if metadata.defects or _normal_name(name) != expected["name"] or version != expected["version"]:
        raise ValueError("wheel metadata identity mismatch")
    wheel = BytesParser(policy=policy.default).parsebytes(special[wheel_path])
    if wheel.defects or wheel.get_payload().strip() or _single(wheel, "Wheel-Version") != "1.0":
        raise ValueError("unsupported WHEEL metadata")
    purelib = _single(wheel, "Root-Is-Purelib")
    wheel_tags = set()
    for value in wheel.get_all("Tag", []):
        wheel_tags.update(_tags(str(value)))
    if purelib not in ("true", "false") or wheel_tags != filename_tags:
        raise ValueError("WHEEL purity or filename tags mismatch")
    _check_record(special[record_path], files, record_path)
    collected.sort(key=lambda row: row["path"])
    result = dict(name=expected["name"], version=version, filename=expected["filename"],
                  size_bytes=before.st_size, sha256=archive_sha256, metadata_sha256=metadata_sha256,
                  member_count=len(collected), uncompressed_bytes=total, members=collected,
                  licence_candidates=[row for row in collected if row["path"] in files and (
                      row["path"].startswith(dist_info + "/licenses/") or
                      row["path"].rsplit("/", 1)[-1].lower().startswith(("license", "licence", "copying", "notice")))],
                  metadata=dict(name=name, version=version, license_expression=metadata.get("License-Expression"),
                                license=metadata.get("License"), license_files=metadata.get_all("License-File", []),
                                requires_dist=metadata.get_all("Requires-Dist", [])),
                  wheel=dict(version="1.0", root_is_purelib=purelib == "true", tags=sorted(wheel_tags)),
                  archive_payload_verified=True, record_verified=True)
    if _identity(os.fstat(fd)) != _identity(before):
        raise ValueError("wheel descriptor identity changed")
    _check_deadline(deadline)
    return result
