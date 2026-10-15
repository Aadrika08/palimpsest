"""Authored byte-only staging fixtures; archive Python contents never execute."""

import gzip
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import stat
import tarfile
import time

import pytest


ROOT = "fixture-0.1"
POISON = b"raise RuntimeError('archive code must not execute')\n"


def _api(name):
    assert importlib.util.find_spec("palimpsest.puck_build_inputs") is not None, "build-input staging API is missing"
    from palimpsest import puck_build_inputs

    return getattr(puck_build_inputs, name)


def _source(tmp_path, entries=None, *, tar_format=tarfile.USTAR_FORMAT, raw=None):
    if raw is None:
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w", format=tar_format) as archive:
            for name, data in entries if entries is not None else [(ROOT + "/setup.py", POISON), (ROOT + "/pkg/__init__.py", POISON)]:
                item = name if isinstance(name, tarfile.TarInfo) else tarfile.TarInfo(name)
                item.size = len(data)
                archive.addfile(item, io.BytesIO(data))
        raw = gzip.compress(stream.getvalue(), mtime=0)
    path = tmp_path / "fixture.tar.gz"
    path.write_bytes(raw)
    return path, dict(root=ROOT, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def _backend(tmp_path, **kwargs):
    from test_puck_package_payloads import _wheel

    return _wheel(tmp_path, **kwargs)


def _run(kind, path, expected, target, *, deadline=None):
    function = _api("extract_source" if kind == "source" else "stage_backend")
    with path.open("rb") as held:
        held.seek(7)
        result = function(held.fileno(), expected=expected, target=target,
                          deadline=time.monotonic() + 15 if deadline is None else deadline)
        assert held.tell() == 7
        assert held.read(1) == path.read_bytes()[7:8]
        return result


def _fixture(kind, tmp_path):
    return _source(tmp_path) if kind == "source" else _backend(tmp_path)


@pytest.mark.parametrize("kind", ["source", "backend"])
def test_stages_regular_bytes_without_executing_contents_and_preserves_descriptor(tmp_path, kind):
    path, expected = _fixture(kind, tmp_path)
    target = tmp_path / "stage"
    result = _run(kind, path, expected, target)
    assert result["kind"] == kind
    assert result["archive_sha256"] == expected["sha256"]
    assert result["files"] == sorted(result["files"], key=lambda row: row["path"])
    assert result["total_bytes"] == sum(row["size_bytes"] for row in result["files"])
    for row in result["files"]:
        actual = target / row["path"]
        data = actual.read_bytes()
        assert row == dict(path=row["path"], size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        assert stat.S_IMODE(actual.stat().st_mode) & 0o111 == 0
    if kind == "source":
        assert {row["path"] for row in result["files"]} == {"pkg/__init__.py", "setup.py"}
        assert (target / "setup.py").read_bytes() == POISON
    else:
        assert result["wheel_verification"]["record_verified"] is True
        assert (target / "demo/__init__.py").read_bytes() == b"raise RuntimeError('wheel code must never execute')\n"


@pytest.mark.parametrize("kind", ["source", "backend"])
@pytest.mark.parametrize("field,value", [("sha256", "0" * 64), ("size_bytes", 1)])
def test_rejects_unpinned_raw_bytes_before_target_creation(tmp_path, kind, field, value):
    path, expected = _fixture(kind, tmp_path)
    target = tmp_path / "stage"
    with pytest.raises(ValueError):
        _run(kind, path, {**expected, field: value}, target)
    assert not target.exists()


@pytest.mark.parametrize("kind", ["source", "backend"])
def test_rejects_hardlinked_archive(tmp_path, kind):
    path, expected = _fixture(kind, tmp_path)
    os.link(path, tmp_path / "archive-alias")
    with pytest.raises(ValueError):
        _run(kind, path, expected, tmp_path / "stage")


@pytest.mark.parametrize("kind", ["source", "backend"])
def test_rejects_directory_descriptor(tmp_path, kind):
    _, expected = _fixture(kind, tmp_path)
    function = _api("extract_source" if kind == "source" else "stage_backend")
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ValueError):
            function(fd, expected=expected, target=tmp_path / "stage", deadline=time.monotonic() + 15)
        os.fstat(fd)
    finally:
        os.close(fd)


@pytest.mark.parametrize("kind", ["source", "backend"])
def test_expired_deadline_refuses_staging(tmp_path, kind):
    path, expected = _fixture(kind, tmp_path)
    with pytest.raises(ValueError, match="deadline"):
        _run(kind, path, expected, tmp_path / "stage", deadline=time.monotonic() - 1)


@pytest.mark.parametrize("kind", ["source", "backend"])
@pytest.mark.parametrize("existing", ["directory", "file", "symlink"])
def test_existing_target_is_never_reused_or_overwritten(tmp_path, kind, existing):
    path, expected = _fixture(kind, tmp_path)
    target, sentinel = tmp_path / "stage", tmp_path / "sentinel"
    sentinel.write_bytes(b"retain me")
    if existing == "directory":
        target.mkdir()
        (target / "retained").write_bytes(b"retain me")
    elif existing == "file":
        target.write_bytes(b"retain me")
    else:
        target.symlink_to(sentinel)
    with pytest.raises(ValueError):
        _run(kind, path, expected, target)
    assert sentinel.read_bytes() == b"retain me"
    assert (target / "retained").read_bytes() == b"retain me" if existing == "directory" else target.read_bytes() == b"retain me"


@pytest.mark.parametrize("name", ["/escape", "../escape", ROOT + "/../escape", ROOT + "//x", ROOT + "/./x", ROOT + "/bad\\x", ROOT + "/line\nx", ROOT + "/\x7fx", "other/x"])
def test_source_rejects_traversal_aliases_controls_and_wrong_root(tmp_path, name):
    path, expected = _source(tmp_path, [(name, b"x")])
    with pytest.raises(ValueError):
        _run("source", path, expected, tmp_path / "stage")
    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize("entries", [
    [(ROOT + "/a", b"first"), (ROOT + "/a", b"again")],
    [(ROOT + "/a", b"file"), (ROOT + "/a/b", b"child")],
    [(ROOT + "/a/b", b"child"), (ROOT + "/a", b"file")],
])
def test_source_rejects_duplicates_and_file_directory_collisions(tmp_path, entries):
    path, expected = _source(tmp_path, entries)
    with pytest.raises(ValueError):
        _run("source", path, expected, tmp_path / "stage")


@pytest.mark.parametrize("entry_type", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.GNUTYPE_SPARSE])
def test_source_rejects_links_and_special_members(tmp_path, entry_type):
    item = tarfile.TarInfo(ROOT + "/special")
    item.type, item.linkname = entry_type, "outside"
    path, expected = _source(tmp_path, [(item, b"")])
    with pytest.raises(ValueError):
        _run("source", path, expected, tmp_path / "stage")


@pytest.mark.parametrize("key,value", [("path", ROOT + "/aliased"), ("linkpath", "outside"), ("size", "1"), ("GNU.sparse.map", "0,1")])
def test_source_rejects_pax_path_size_and_sparse_overrides(tmp_path, key, value):
    item = tarfile.TarInfo(ROOT + "/original")
    item.pax_headers = {key: value}
    path, expected = _source(tmp_path, [(item, b"x")], tar_format=tarfile.PAX_FORMAT)
    with pytest.raises(ValueError):
        _run("source", path, expected, tmp_path / "stage")


def test_source_explicit_directories_do_not_restore_archive_modes(tmp_path):
    directory = tarfile.TarInfo(ROOT + "/pkg/")
    directory.type, directory.mode = tarfile.DIRTYPE, 0o7777
    path, expected = _source(tmp_path, [(directory, b""), (ROOT + "/pkg/a", b"data")])
    target = tmp_path / "stage"
    result = _run("source", path, expected, target)
    assert result["files"] == [dict(path="pkg/a", size_bytes=4, sha256=hashlib.sha256(b"data").hexdigest())]
    assert stat.S_IMODE((target / "pkg").stat().st_mode) == 0o700


@pytest.mark.parametrize("which", ["members", "member_bytes", "decoded_total", "raw_bytes", "not_gzip"])
def test_source_resource_and_format_boundaries(tmp_path, which):
    if which == "members":
        path, expected = _source(tmp_path, [(ROOT + "/f" + str(i), b"") for i in range(513)])
    elif which == "member_bytes":
        path, expected = _source(tmp_path, [(ROOT + "/large", b"x" * (2 * 1024 * 1024 + 1))])
    elif which == "decoded_total":
        path, expected = _source(tmp_path, [(ROOT + "/f" + str(i), b"x" * (2 * 1024 * 1024)) for i in range(9)])
    elif which == "raw_bytes":
        path, expected = _source(tmp_path, raw=b"x" * (2 * 1024 * 1024 + 1))
    else:
        path, expected = _source(tmp_path, raw=b"not a gzip archive")
    with pytest.raises(ValueError):
        _run("source", path, expected, tmp_path / "stage")


@pytest.mark.parametrize("change", [lambda e: {**e, "extra": True}, lambda e: {**e, "root": "../bad"}, lambda e: {**e, "sha256": "not-a-hash"}, lambda e: {**e, "size_bytes": True}])
def test_source_rejects_malformed_expected_evidence(tmp_path, change):
    path, expected = _source(tmp_path)
    with pytest.raises(ValueError):
        _run("source", path, change(expected), tmp_path / "stage")


@pytest.mark.parametrize("kind", ["source", "backend"])
def test_descriptor_identity_change_during_read_is_rejected(tmp_path, kind, monkeypatch):
    path, expected = _fixture(kind, tmp_path)
    _api("extract_source")
    original, changed = os.pread, False
    before = path.stat()

    def pread(fd, size, offset):
        nonlocal changed
        data = original(fd, size, offset)
        if not changed:
            changed = True
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1))
        return data

    monkeypatch.setattr(os, "pread", pread)
    with pytest.raises(ValueError, match="identity"):
        _run(kind, path, expected, tmp_path / "stage")


@pytest.mark.parametrize("extra", ["demo-1.2.data/scripts/tool", "demo-1.2.data/"])
def test_backend_refuses_data_relocation_tree(tmp_path, extra):
    path, expected = _backend(tmp_path, extras=[(extra, b"" if extra.endswith("/") else b"tool")])
    with pytest.raises(ValueError, match="data"):
        _run("backend", path, expected, tmp_path / "stage")


def test_backend_extracts_pth_as_inert_bytes_and_keeps_dist_info(tmp_path):
    path, expected = _backend(tmp_path, extras=[("inert.pth", POISON)])
    target = tmp_path / "stage"
    result = _run("backend", path, expected, target)
    assert (target / "inert.pth").read_bytes() == POISON
    assert (target / "demo-1.2.dist-info/METADATA").is_file()
    actual = {row["path"]: row for row in result["files"]}
    for member in result["wheel_verification"]["members"]:
        assert actual[member["path"]] == {key: member[key] for key in ("path", "size_bytes", "sha256")}


def test_backend_rejects_invalid_record_before_extraction(tmp_path):
    path, expected = _backend(tmp_path, record_transform=lambda rows: rows[1:])
    target = tmp_path / "stage"
    with pytest.raises(ValueError, match="RECORD"):
        _run("backend", path, expected, target)
    assert not target.exists()


def test_source_accepts_only_inert_per_entry_pax_mtime(tmp_path):
    item = tarfile.TarInfo(ROOT + "/setup.py")
    item.pax_headers = {"mtime": "1643471580.890964"}
    path, expected = _source(tmp_path, [(item, POISON)], tar_format=tarfile.PAX_FORMAT)
    target = tmp_path / "stage"
    result = _run("source", path, expected, target)
    assert result["files"] == [dict(path="setup.py", size_bytes=len(POISON), sha256=hashlib.sha256(POISON).hexdigest())]
    assert (target / "setup.py").stat().st_mtime_ns != 1643471580890964000


def test_backend_refuses_archive_above_two_mib_before_staging(tmp_path):
    import zipfile
    path, expected = _backend(tmp_path, updates={"large.bin": b"x" * (2 * 1024 * 1024)}, compression=zipfile.ZIP_STORED)
    target = tmp_path / "stage"
    with pytest.raises(ValueError, match="backend archive size"):
        _run("backend", path, expected, target)
    assert not target.exists()
