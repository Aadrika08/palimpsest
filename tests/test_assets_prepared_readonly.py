"""Read-only preparation checks on retained, authored bytes, never model assets."""

import builtins
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
from uuid import uuid4

import pytest

from palimpsest import assets


SOURCE_MANIFEST = Path(__file__).resolve().parents[1] / "model_manifests/flynn-full-vision.json"
LIMIT = 1024 * 1024
ROLES = ["archive", "checkpoint", "edge", "metadata", "manifest"] + [
    f"{kind}{i}" for kind in ("mapping", "source") for i in range(7)
]


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


@pytest.fixture
def prepared(tmp_path_factory):
    # No tmp_path cleanup or reused namespace: the invocation's fresh basetemp
    # and all descendants remain as evidence after success and failure.
    home = tmp_path_factory.getbasetemp() / uuid4().hex
    repo, root = home / "repo", home / "assets"
    repo.mkdir(parents=True)
    root.mkdir()
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    paths = {}

    def put(role, path, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        paths[role] = path
        return identity(raw)

    for item, role in zip(manifest["files"], ("archive", "checkpoint")):
        item.update(put(role, root / item["path"], f"authored {role}\n".encode()))
    graph = manifest["graph"]
    archive_hash = manifest["files"][0]["sha256"]
    directory = root / f"graph-{archive_hash}"
    edge = directory / graph["edge_identity"]["archive_member"]
    graph["edge_identity"].update(put("edge", edge, b"pre,post\n1,2\n"))
    graph["edge_identity"]["derived_from_archive_sha256"] = archive_hash
    for i, item in enumerate(graph["mapping_files"]):
        source = f"cell,type\n{i},authored\n".encode()
        archived = source.replace(b"\n", b"\r\n")
        item.update(put(f"source{i}", repo / item["source_path"], source))
        item["archive_identity"] = put(f"mapping{i}", edge.parent / item["path"], archived)
    put("manifest", repo / "model_manifests/flynn-full-vision.json",
        (json.dumps(manifest, indent=2) + "\n").encode())
    metadata = {
        "archive_sha256": archive_hash,
        "edge_path": graph["edge_identity"]["archive_member"],
        "edge_sha256": graph["edge_identity"]["sha256"],
        "upstream_commit": assets.UPSTREAM_COMMIT,
        "mapping_files": copy.deepcopy(graph["mapping_files"]),
        "provenance_limit": manifest["provenance_limit"],
    }
    put("metadata", directory / "palimpsest-prepared.json",
        (json.dumps(metadata, indent=2) + "\n").encode())
    return {"home": home, "repo": repo, "root": root, "paths": paths,
            "manifest": manifest, "metadata": metadata, "directory": directory}


def snapshot(home):
    result = {}
    for path in [home, *sorted(home.rglob("*"))]:
        info = path.lstat()
        raw = path.read_bytes() if stat.S_ISREG(info.st_mode) else None
        target = os.readlink(path) if stat.S_ISLNK(info.st_mode) else None
        result[str(path.relative_to(home))] = (
            info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns, raw, target,
        )
    return result


def guarded_resolve(case, monkeypatch, repo=None, root=None, *, reject_metadata_open=False):
    """Deny mutation/acquisition during the real call and compare retained trees."""
    before = snapshot(case["home"])
    cwd = Path.cwd()
    original_open, original_io_open, original_os_open = builtins.open, io.open, os.open

    def denied(*args, **kwargs):
        raise AssertionError("Resolver attempted mutation or acquisition")

    def safe_open(original):
        def opened(path, mode="r", *args, **kwargs):
            assert not any(char in mode for char in "wax+"), mode
            if not isinstance(path, int):
                candidate = Path(path)
                assert candidate.is_relative_to(case["home"]), candidate
                if candidate == case["paths"]["metadata"]:
                    assert not reject_metadata_open, "Oversized metadata was opened"
                    stream = original(path, mode, *args, **kwargs)

                    class BoundedReader:
                        def __enter__(self):
                            return self

                        def __exit__(self, *exc):
                            stream.close()

                        def read(self, count=-1):
                            assert 0 <= count <= LIMIT + 1, count
                            return stream.read(count)

                    return BoundedReader()
            return original(path, mode, *args, **kwargs)
        return opened

    def safe_os_open(path, flags, *args, **kwargs):
        assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        return original_os_open(path, flags, *args, **kwargs)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "open", safe_open(original_open))
            patch.setattr(io, "open", safe_open(original_io_open))
            patch.setattr(os, "open", safe_os_open)
            for name in ("mkdir", "makedirs", "rename", "replace", "remove", "unlink", "rmdir",
                         "link", "symlink", "chmod", "chown", "truncate", "utime", "write"):
                patch.setattr(os, name, denied)
            for name in ("copyfile", "copy", "copy2", "copytree", "move", "rmtree", "unpack_archive"):
                patch.setattr(shutil, name, denied)
            for name in ("prepare_graph", "fetch_assets", "urlopen"):
                patch.setattr(assets, name, denied)
            patch.setattr(assets.importlib, "import_module", denied)
            return assets.resolve_prepared_assets_readonly(
                case["repo"] if repo is None else repo,
                case["root"] if root is None else root,
            )
    finally:
        assert snapshot(case["home"]) == before
        assert Path.cwd() == cwd


def save_metadata(case):
    case["paths"]["metadata"].write_text(json.dumps(case["metadata"], indent=2) + "\n")


def save_manifest(case):
    case["paths"]["manifest"].write_text(json.dumps(case["manifest"], indent=2) + "\n")


def test_prepared_paths_and_all_seven_original_crlf_pairs_remain_unchanged(prepared, monkeypatch):
    # Catches preparer reuse, omitted mappings, wrong return roles and rewriting.
    result = guarded_resolve(prepared, monkeypatch)
    assert result == {role: prepared["paths"][role] for role in ("archive", "checkpoint", "edge")}
    assert all(isinstance(path, Path) and path.is_absolute() for path in result.values())
    for i in range(7):
        source = prepared["paths"][f"source{i}"].read_bytes()
        archived = prepared["paths"][f"mapping{i}"].read_bytes()
        assert b"\r\n" in archived and b"\r" not in source
        assert archived != source and archived.replace(b"\r\n", b"\n") == source


def test_safe_relative_roots_return_canonical_absolute_paths(prepared, monkeypatch):
    monkeypatch.chdir(prepared["home"])
    result = guarded_resolve(prepared, monkeypatch, repo=Path("repo"), root=Path("assets"))
    assert result == {role: prepared["paths"][role] for role in ("archive", "checkpoint", "edge")}


@pytest.mark.parametrize("role", ROLES)
def test_missing_each_input_refuses_without_repair(prepared, monkeypatch, role):
    path = prepared["paths"][role]
    path.rename(path.with_name(path.name + ".retained"))
    with pytest.raises((ValueError, OSError)):
        guarded_resolve(prepared, monkeypatch)
    assert not path.exists()


@pytest.mark.parametrize("role", [role for role in ROLES if role not in ("metadata", "manifest")])
@pytest.mark.parametrize("corruption", ["size", "hash"])
def test_wrong_size_or_hash_in_every_payload_refuses(prepared, monkeypatch, role, corruption):
    path = prepared["paths"][role]
    raw = path.read_bytes()
    path.write_bytes(raw + b"!" if corruption == "size" else bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError):
        guarded_resolve(prepared, monkeypatch)


@pytest.mark.parametrize("key", ["archive_sha256", "edge_path", "edge_sha256", "upstream_commit",
                                  "mapping_files", "provenance_limit"])
@pytest.mark.parametrize("change", ["different", "missing", "type"])
def test_every_prepared_metadata_identity_is_exact(prepared, monkeypatch, key, change):
    metadata = prepared["metadata"]
    if change == "missing":
        metadata.pop(key)
    elif change == "type":
        metadata[key] = False
    else:
        metadata[key] = [] if key == "mapping_files" else "different"
    save_metadata(prepared)
    with pytest.raises(ValueError):
        guarded_resolve(prepared, monkeypatch)


@pytest.mark.parametrize("i", range(7))
@pytest.mark.parametrize("field", ["path", "source_path", "sha256", "size_bytes", "license", "archive_identity"])
def test_complete_mapping_metadata_is_compared(prepared, monkeypatch, i, field):
    prepared["metadata"]["mapping_files"][i][field] = "different"
    save_metadata(prepared)
    with pytest.raises(ValueError):
        guarded_resolve(prepared, monkeypatch)


@pytest.mark.parametrize("number", [True, 1.0])
def test_mapping_metadata_rejects_python_equal_but_different_json_types(prepared, monkeypatch, number):
    # Set an authored upstream mapping identity to size 1, so bool/int equality
    # and int/float equality would otherwise disguise a metadata mismatch.
    item = prepared["manifest"]["graph"]["mapping_files"][0]
    prepared["paths"]["source0"].write_bytes(b"x")
    prepared["paths"]["mapping0"].write_bytes(b"x")
    item.update(identity(b"x"))
    item["archive_identity"] = identity(b"x")
    prepared["metadata"]["mapping_files"] = copy.deepcopy(prepared["manifest"]["graph"]["mapping_files"])
    prepared["metadata"]["mapping_files"][0]["size_bytes"] = number
    save_manifest(prepared)
    save_metadata(prepared)
    with pytest.raises(ValueError):
        guarded_resolve(prepared, monkeypatch)


@pytest.mark.parametrize("raw", [
    b'{"archive_sha256":"a","archive_sha256":"b"}',
    b'{"mapping_files":[{"size_bytes":1,"size_bytes":2}]}',
    b'{"extra":NaN}', b'{"extra":Infinity}', b'{"extra":-Infinity}',
    b'{"extra":1e999}', b'[]', b'null', b'{', b'\xff',
])
def test_duplicate_nonfinite_nonobject_and_malformed_metadata_refuses(prepared, monkeypatch, raw):
    prepared["paths"]["metadata"].write_bytes(raw)
    with pytest.raises(ValueError):
        guarded_resolve(prepared, monkeypatch)


def test_extra_metadata_key_refuses(prepared, monkeypatch):
    prepared["metadata"]["admitted"] = True
    save_metadata(prepared)
    with pytest.raises(ValueError):
        guarded_resolve(prepared, monkeypatch)


@pytest.mark.parametrize("edge_path", ["elsewhere/connections_princeton.csv", "../connections_princeton.csv",
    "/connections_princeton.csv", "a/../connections_princeton.csv", "a//connections_princeton.csv",
    "a/./connections_princeton.csv", "a\\connections_princeton.csv", "a:connections_princeton.csv", ""])
def test_metadata_cannot_select_another_or_unsafe_edge(prepared, monkeypatch, edge_path):
    prepared["metadata"]["edge_path"] = edge_path
    save_metadata(prepared)
    with pytest.raises(ValueError):
        guarded_resolve(prepared, monkeypatch)


@pytest.mark.parametrize("edge_path", ["../connections_princeton.csv", "/connections_princeton.csv",
    "a/../connections_princeton.csv", "a//connections_princeton.csv", "a\\connections_princeton.csv"])
def test_manifest_edge_member_is_validated_even_when_metadata_matches(prepared, monkeypatch, edge_path):
    prepared["manifest"]["graph"]["edge_identity"]["archive_member"] = edge_path
    prepared["metadata"]["edge_path"] = edge_path
    save_manifest(prepared)
    save_metadata(prepared)
    with pytest.raises(ValueError):
        guarded_resolve(prepared, monkeypatch)


def test_edge_is_not_searched_for_at_an_alternate_location(prepared, monkeypatch):
    path = prepared["paths"]["edge"]
    alternative = prepared["directory"] / "alternate" / path.name
    alternative.parent.mkdir()
    path.rename(alternative)
    with pytest.raises((ValueError, OSError)):
        guarded_resolve(prepared, monkeypatch)


@pytest.mark.parametrize("which", ["repo", "root"])
@pytest.mark.parametrize("spelling", ["symlink", "traversal", "ancestor_symlink"])
def test_root_spelling_refuses_symlinks_and_traversal(prepared, monkeypatch, which, spelling):
    path = prepared[which]
    if spelling == "symlink":
        argument = prepared["home"] / (which + "-link")
        argument.symlink_to(path, target_is_directory=True)
    elif spelling == "ancestor_symlink":
        link = prepared["home"] / "parent-link"
        link.symlink_to(prepared["home"], target_is_directory=True)
        argument = link / path.name
    else:
        argument = path / ".." / path.name
    with pytest.raises((ValueError, OSError)):
        guarded_resolve(prepared, monkeypatch, **{which: argument})


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("replacement", ["symlink", "directory", "fifo"])
def test_named_inputs_must_be_regular_and_never_symlinked(prepared, monkeypatch, role, replacement):
    path = prepared["paths"][role]
    retained = path.with_name(path.name + ".retained")
    path.rename(retained)
    if replacement == "symlink":
        path.symlink_to(retained)
    elif replacement == "directory":
        path.mkdir()
    else:
        os.mkfifo(path)
    with pytest.raises((ValueError, OSError)):
        guarded_resolve(prepared, monkeypatch)


@pytest.mark.parametrize("which", ["directory", "edge_parent", "source_parent", "manifest_parent"])
def test_symlinked_named_directories_refuse(prepared, monkeypatch, which):
    path = {"directory": prepared["directory"], "edge_parent": prepared["paths"]["edge"].parent,
            "source_parent": prepared["paths"]["source0"].parent,
            "manifest_parent": prepared["paths"]["manifest"].parent}[which]
    retained = path.with_name(path.name + ".retained")
    path.rename(retained)
    path.symlink_to(retained, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        guarded_resolve(prepared, monkeypatch)


@pytest.mark.parametrize("which", ["repo", "root", "directory"])
def test_missing_roots_or_prepared_directory_are_not_created(prepared, monkeypatch, which):
    path = prepared[which]
    path.rename(path.with_name(path.name + ".retained"))
    with pytest.raises((ValueError, OSError)):
        guarded_resolve(prepared, monkeypatch)
    assert not path.exists()


def test_metadata_limit_accepts_exact_boundary(prepared, monkeypatch):
    path = prepared["paths"]["metadata"]
    raw = path.read_bytes()
    path.write_bytes(raw + b" " * (LIMIT - len(raw)))
    assert set(guarded_resolve(prepared, monkeypatch)) == {"archive", "checkpoint", "edge"}


def test_metadata_limit_refuses_before_opening_oversize(prepared, monkeypatch):
    prepared["paths"]["metadata"].write_bytes(b" " * (LIMIT + 1))
    with pytest.raises(ValueError):
        guarded_resolve(prepared, monkeypatch, reject_metadata_open=True)


@pytest.mark.parametrize("i", range(7))
def test_pinned_archived_bytes_still_require_the_upstream_crlf_relationship(prepared, monkeypatch, i):
    # Rebind the authored archive identity to different-but-valid bytes. Hash
    # checks pass, so only the existing normalization relationship can refuse.
    item = prepared["manifest"]["graph"]["mapping_files"][i]
    raw = b"different,content\r\n"
    prepared["paths"][f"mapping{i}"].write_bytes(raw)
    item["archive_identity"] = identity(raw)
    prepared["metadata"]["mapping_files"] = copy.deepcopy(prepared["manifest"]["graph"]["mapping_files"])
    save_manifest(prepared)
    save_metadata(prepared)
    with pytest.raises(ValueError, match="CRLF"):
        guarded_resolve(prepared, monkeypatch)
