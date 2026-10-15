"""Offline authored-wheel checks; these fixtures never import wheel contents."""

import base64
import csv
from contextlib import nullcontext
import hashlib
import io
import os
import time
import zipfile

import pytest


DIST = "demo-1.2.dist-info"
METADATA = b"Metadata-Version: 2.4\nName: demo\nVersion: 1.2\nLicense-Expression: MIT\nLicense-File: licenses/LICENSE\n\nA demo.\n"
WHEEL = b"Wheel-Version: 1.0\nGenerator: authored-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n"
LIMITS = dict(max_members=20, max_uncompressed_bytes=65536, max_member_bytes=32768, max_metadata_bytes=8192)


def _hash(data, algorithm="sha256"):
    digest = hashlib.new(algorithm, data).digest()
    return algorithm + "=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _wheel(tmp_path, *, updates=None, omitted=(), extras=(), record_transform=None, compression=zipfile.ZIP_DEFLATED):
    files = {
        "demo/__init__.py": b"raise RuntimeError('wheel code must never execute')\n",
        DIST + "/METADATA": METADATA,
        DIST + "/WHEEL": WHEEL,
        DIST + "/licenses/LICENSE": b"Authored fixture licence.\n",
    }
    files.update(updates or {})
    for name in omitted:
        files.pop(name, None)
    entries = list(files.items()) + list(extras)
    rows = [[name.filename if isinstance(name, zipfile.ZipInfo) else name, _hash(data), str(len(data))]
            for name, data in entries if not (name.filename if isinstance(name, zipfile.ZipInfo) else name).endswith("/")]
    rows.append([DIST + "/RECORD", "", ""])
    if record_transform:
        rows = record_transform(rows)
    stream = io.StringIO(newline="")
    csv.writer(stream).writerows(rows)
    entries.append((DIST + "/RECORD", stream.getvalue().encode()))
    path = tmp_path / "demo-1.2-py3-none-any.whl"
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    payload = path.read_bytes()
    expected = dict(name="demo", version="1.2", filename=path.name,
                    size_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                    metadata_sha256=hashlib.sha256(files.get(DIST + "/METADATA", b"")).hexdigest())
    return path, expected


def _verify(path, expected, *, limits=None, deadline=None):
    from palimpsest.puck_package_payloads import verify_wheel

    with path.open("rb") as source:
        return verify_wheel(source.fileno(), expected=expected, limits=limits or LIMITS,
                            deadline=time.monotonic() + 10 if deadline is None else deadline)


def test_valid_payload_inventory_does_not_execute_package_code(tmp_path):
    path, expected = _wheel(tmp_path)
    result = _verify(path, expected)
    assert result["archive_payload_verified"] is True
    assert result["record_verified"] is True
    assert {key: result[key] for key in expected} == expected
    assert result["member_count"] == 5
    assert result["uncompressed_bytes"] == sum(row["size_bytes"] for row in result["members"])
    assert [row["path"] for row in result["members"]] == sorted(row["path"] for row in result["members"])
    assert result["licence_candidates"] == [next(row for row in result["members"] if row["path"].endswith("/LICENSE"))]
    assert result["metadata"]["license_expression"] == "MIT"


def test_rejects_wrong_archive_hash_even_when_metadata_matches(tmp_path):
    path, expected = _wheel(tmp_path)
    expected["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        _verify(path, expected)


@pytest.mark.parametrize("metadata", [METADATA.replace(b"Name: demo", b"Name: other"), METADATA.replace(b"Version: 1.2", b"Version: 1.3")])
def test_rejects_metadata_identity_mismatch(tmp_path, metadata):
    path, expected = _wheel(tmp_path, updates={DIST + "/METADATA": metadata})
    with pytest.raises(ValueError):
        _verify(path, expected)


def test_rejects_metadata_that_does_not_match_retained_hash(tmp_path):
    path, expected = _wheel(tmp_path)
    expected["metadata_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        _verify(path, expected)


def test_allows_unpinned_metadata_for_separately_built_wheel(tmp_path):
    path, expected = _wheel(tmp_path)
    expected["metadata_sha256"] = None
    assert _verify(path, expected)["metadata_sha256"] == hashlib.sha256(METADATA).hexdigest()


@pytest.mark.parametrize("change", [
    lambda rows: rows[1:],
    lambda rows: rows + [rows[0]],
    lambda rows: rows + [["absent.bin", _hash(b"absent"), "6"]],
    lambda rows: [[row[0], _hash(b"wrong"), row[2]] if row[0] == "demo/__init__.py" else row for row in rows],
    lambda rows: [[row[0], row[1], "1"] if row[0] == "demo/__init__.py" else row for row in rows],
    lambda rows: [[row[0], "", ""] if row[0] == "demo/__init__.py" else row for row in rows],
    lambda rows: [[row[0], _hash(b""), "0"] if row[0].endswith("/RECORD") else row for row in rows],
])
def test_rejects_incomplete_duplicate_or_mismatched_record(tmp_path, change):
    path, expected = _wheel(tmp_path, record_transform=change)
    with pytest.raises(ValueError):
        _verify(path, expected)


@pytest.mark.parametrize("algorithm", ["sha384", "sha512"])
def test_accepts_supported_record_hash_algorithms(tmp_path, algorithm):
    content = b"raise RuntimeError('wheel code must never execute')\n"
    path, expected = _wheel(tmp_path, record_transform=lambda rows: [
        [row[0], _hash(content, algorithm), row[2]] if row[0] == "demo/__init__.py" else row for row in rows])
    assert _verify(path, expected)["record_verified"] is True


@pytest.mark.parametrize("algorithm", ["md5", "sha1"])
def test_rejects_weak_record_hash_algorithms(tmp_path, algorithm):
    content = b"raise RuntimeError('wheel code must never execute')\n"
    path, expected = _wheel(tmp_path, record_transform=lambda rows: [
        [row[0], _hash(content, algorithm), row[2]] if row[0] == "demo/__init__.py" else row for row in rows])
    with pytest.raises(ValueError):
        _verify(path, expected)


@pytest.mark.parametrize("name", ["/absolute", "../escape", "demo/../escape", "demo//x", "demo/./x", "demo\\bad", "demo/line\nx", "demo/\x7fx"])
def test_rejects_noncanonical_member_paths(tmp_path, name):
    path, expected = _wheel(tmp_path, extras=[(name, b"x")])
    with pytest.raises(ValueError):
        _verify(path, expected)


@pytest.mark.parametrize("entries", [
    [("demo/__init__.py", b"duplicate")],
    [("demo", b"file masks package directory")],
    [("demo/__init__.py/child", b"file masks child")],
    [(DIST + "/METADATA/", b"")],
    [("demo/", b"directory contains bytes")],
    [("other-1.2.dist-info/METADATA", b"other distribution")],
    [(DIST + "/RECORD.jws", b"unsupported signature")],
])
def test_rejects_duplicate_paths_prefix_collisions_and_unsupported_identity(tmp_path, entries):
    with pytest.warns(UserWarning) if entries[0][0] == "demo/__init__.py" else nullcontext():
        path, expected = _wheel(tmp_path, extras=entries)
    with pytest.raises(ValueError):
        _verify(path, expected)


def test_explicit_directories_are_inventory_only_and_absent_from_record(tmp_path):
    path, expected = _wheel(tmp_path, extras=[("demo/", b""), (DIST + "/licenses/", b"")])
    result = _verify(path, expected)
    assert result["member_count"] == 7
    assert next(row for row in result["members"] if row["path"] == "demo/")["size_bytes"] == 0


@pytest.mark.parametrize("file_type", [0o120000, 0o010000, 0o020000, 0o140000, 0o040000])
def test_rejects_symlink_special_or_mislabelled_modes(tmp_path, file_type):
    entry = zipfile.ZipInfo("demo/special")
    entry.create_system = 3
    entry.external_attr = (file_type | 0o600) << 16
    path, expected = _wheel(tmp_path, extras=[(entry, b"x")])
    with pytest.raises(ValueError):
        _verify(path, expected)


@pytest.mark.parametrize("wheel", [
    WHEEL.replace(b"Wheel-Version: 1.0", b"Wheel-Version: 2.0"),
    WHEEL.replace(b"Root-Is-Purelib: true", b"Root-Is-Purelib: maybe"),
    WHEEL.replace(b"Tag: py3-none-any", b"Tag: cp311-cp311-linux_x86_64"),
    WHEEL + b"Tag: py2-none-any\n",
])
def test_rejects_wheel_version_purity_or_filename_tag_disagreement(tmp_path, wheel):
    path, expected = _wheel(tmp_path, updates={DIST + "/WHEEL": wheel})
    with pytest.raises(ValueError):
        _verify(path, expected)


@pytest.mark.parametrize("field,value", [("max_members", 4), ("max_uncompressed_bytes", 100), ("max_member_bytes", 50), ("max_metadata_bytes", 30)])
def test_rejects_declared_resource_limit_excess(tmp_path, field, value):
    path, expected = _wheel(tmp_path)
    with pytest.raises(ValueError):
        _verify(path, expected, limits={**LIMITS, field: value})


def _repin(path, expected, data):
    path.write_bytes(data)
    expected.update(size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def test_rejects_decompressed_tail_hidden_by_false_declared_size(tmp_path):
    # CPython ZipExtFile can otherwise expose only the declared ten bytes.
    import struct
    import zlib

    short = b"x" * 10
    path, expected = _wheel(tmp_path, updates={"demo/data.bin": b"x" * 100000}, record_transform=lambda rows: [
        [row[0], _hash(short), "10"] if row[0] == "demo/data.bin" else row for row in rows])
    with zipfile.ZipFile(path) as archive:
        local = archive.getinfo("demo/data.bin").header_offset
    raw = bytearray(path.read_bytes())
    struct.pack_into("<I", raw, local + 14, zlib.crc32(short))
    struct.pack_into("<I", raw, local + 22, len(short))
    central = raw.index(b"PK\x01\x02")
    while True:
        name_size, extra_size, comment_size = struct.unpack_from("<HHH", raw, central + 28)
        if raw[central + 46:central + 46 + name_size] == b"demo/data.bin":
            break
        central += 46 + name_size + extra_size + comment_size
    struct.pack_into("<I", raw, central + 16, zlib.crc32(short))
    struct.pack_into("<I", raw, central + 24, len(short))
    _repin(path, expected, raw)
    with pytest.raises(ValueError):
        _verify(path, expected)


@pytest.mark.parametrize("mutation", ["crc", "encrypted", "nul"])
def test_rejects_corrupted_crc_encryption_and_nul_aliases(tmp_path, mutation):
    import struct

    path, expected = _wheel(tmp_path, compression=zipfile.ZIP_STORED)
    raw = bytearray(path.read_bytes())
    if mutation == "crc":
        pos = raw.index(b"raise RuntimeError")
        raw[pos] ^= 1
    elif mutation == "encrypted":
        struct.pack_into("<H", raw, 6, 1)
        struct.pack_into("<H", raw, raw.index(b"PK\x01\x02") + 8, 1)
    else:
        raw = raw.replace(b"demo/__init__.py", b"demo/\x00_init__.py")
    _repin(path, expected, raw)
    with pytest.raises(ValueError):
        _verify(path, expected)


def test_rejects_unsupported_compression(tmp_path):
    path, expected = _wheel(tmp_path, compression=zipfile.ZIP_BZIP2)
    with pytest.raises(ValueError):
        _verify(path, expected)


def test_expired_deadline_rejects_payload(tmp_path):
    path, expected = _wheel(tmp_path)
    with pytest.raises(ValueError):
        _verify(path, expected, deadline=time.monotonic() - 1)


def test_fd_remains_open_and_offset_is_unchanged(tmp_path):
    from palimpsest.puck_package_payloads import verify_wheel

    path, expected = _wheel(tmp_path)
    with path.open("rb") as source:
        source.seek(7)
        verify_wheel(source.fileno(), expected=expected, limits=LIMITS, deadline=time.monotonic() + 10)
        assert source.tell() == 7
        assert source.read(1) == path.read_bytes()[7:8]


def test_rejects_identity_change_during_read(tmp_path, monkeypatch):
    import palimpsest.puck_package_payloads as verifier

    path, expected = _wheel(tmp_path)
    original, changed = os.pread, False
    before = path.stat()

    def pread(fd, count, offset):
        nonlocal changed
        data = original(fd, count, offset)
        if not changed:
            changed = True
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1))
        return data

    monkeypatch.setattr(verifier.os, "pread", pread)
    with pytest.raises(ValueError):
        _verify(path, expected)


def test_rejects_multiple_hard_links(tmp_path):
    path, expected = _wheel(tmp_path)
    os.link(path, tmp_path / "alias.whl")
    with pytest.raises(ValueError):
        _verify(path, expected)


@pytest.mark.parametrize("change", [lambda value: {**value, "extra": True}, lambda value: {key: val for key, val in value.items() if key != "sha256"}, lambda value: {**value, "filename": "bad.whl"}])
def test_rejects_malformed_expected_evidence(tmp_path, change):
    path, expected = _wheel(tmp_path)
    with pytest.raises(ValueError):
        _verify(path, change(expected))


def test_licence_directory_includes_nonstandard_licence_filenames(tmp_path):
    path, expected = _wheel(tmp_path, extras=[(DIST + "/licenses/MIT", b"Authored MIT text")])
    assert [row["path"] for row in _verify(path, expected)["licence_candidates"]] == [
        DIST + "/licenses/LICENSE", DIST + "/licenses/MIT"]


def test_streams_a_large_deflate_member_without_importing_it(tmp_path):
    data = b"untrusted package bytes\\n" * 20000
    path, expected = _wheel(tmp_path, updates={"demo/data.bin": data})
    limits = {**LIMITS, "max_member_bytes": len(data), "max_uncompressed_bytes": len(data) + 8192}
    result = _verify(path, expected, limits=limits)
    row = next(row for row in result["members"] if row["path"] == "demo/data.bin")
    assert row["size_bytes"] == len(data)
    assert row["sha256"] == hashlib.sha256(data).hexdigest()


def test_checks_deadline_again_after_final_descriptor_check(tmp_path, monkeypatch):
    import palimpsest.puck_package_payloads as verifier

    path, expected = _wheel(tmp_path)
    original, calls, now = os.fstat, 0, 0.0

    def fstat(fd):
        nonlocal calls, now
        result = original(fd)
        calls += 1
        if calls == 2:
            now = 2.0
        return result

    monkeypatch.setattr(verifier.os, "fstat", fstat)
    monkeypatch.setattr(verifier.time, "monotonic", lambda: now)
    with pytest.raises(ValueError):
        _verify(path, expected, deadline=1.0)


@pytest.mark.parametrize("bad", [None, {}, {**LIMITS, "max_members": True}, {**LIMITS, "max_metadata_bytes": 0}, {**LIMITS, "extra": 1}])
def test_rejects_malformed_resource_limits(tmp_path, bad):
    from palimpsest.puck_package_payloads import verify_wheel

    path, expected = _wheel(tmp_path)
    with path.open("rb") as source, pytest.raises(ValueError):
        verify_wheel(source.fileno(), expected=expected, limits=bad, deadline=time.monotonic() + 10)


def test_compressed_filename_tag_set_matches_expanded_wheel_tags(tmp_path):
    path, expected = _wheel(tmp_path, updates={DIST + "/WHEEL": WHEEL.replace(b"Tag: py3-none-any", b"Tag: py2-none-any\nTag: py3-none-any")})
    expected["filename"] = "demo-1.2-py2.py3-none-any.whl"
    assert _verify(path, expected)["wheel"]["tags"] == ["py2-none-any", "py3-none-any"]


def test_directory_descriptor_cannot_be_verified_as_wheel(tmp_path):
    from palimpsest.puck_package_payloads import verify_wheel

    _, expected = _wheel(tmp_path)
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        expected["size_bytes"] = os.fstat(fd).st_size
        with pytest.raises(ValueError):
            verify_wheel(fd, expected=expected, limits=LIMITS, deadline=time.monotonic() + 10)
    finally:
        os.close(fd)


@pytest.mark.parametrize("offset,value", [(6, 1), (8, 99)])
def test_rejects_local_header_flags_or_compression_disagreeing_with_directory(tmp_path, offset, value):
    import struct

    path, expected = _wheel(tmp_path)
    raw = bytearray(path.read_bytes())
    struct.pack_into("<H", raw, offset, value)
    _repin(path, expected, raw)
    with pytest.raises(ValueError):
        _verify(path, expected)
