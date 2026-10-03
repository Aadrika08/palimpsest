"""Pinned FLYNN file acquisition; file identity does not prove training provenance."""

import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from urllib.request import urlopen


UPSTREAM_COMMIT = "8d964599119b420de67ee259434d273651a1a76d"
HF_REVISION = "507bef22433c83db3581abd1ab393b25c3aa4989"
MAPPING_NAMES = (
    "visual_column_L1_L2_L3_rear_view_left.csv",
    "visual_column_L1_L2_L3_rear_view_right.csv",
    "head_bristles_left.csv", "head_bristles_right.csv", "descending_neurons.csv",
    "consolidated_cell_types.csv", "JO-C_and_JO-E.csv",
)


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _relative(name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe relative path: {name!r}")
    parsed = PurePosixPath(name)
    if parsed.is_absolute() or any(part in ("", ".", "..") for part in name.rstrip("/").split("/")):
        raise ValueError(f"Unsafe relative path: {name!r}")
    return Path(*parsed.parts)


def _inside(root: Path, name: str) -> Path:
    path = root / _relative(name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes asset root: {name}")
    current = path
    while current != root:
        if current.is_symlink():
            raise ValueError(f"Symlink is not a verified asset: {current}")
        current = current.parent
    return path


def _identity(item: dict) -> None:
    digest = item.get("sha256", "")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Manifest requires a lowercase SHA256")
    if type(item.get("size_bytes")) is not int or item["size_bytes"] < 0:
        raise ValueError("Manifest requires a nonnegative size_bytes")


def load_manifest(repo_root: Path) -> dict:
    manifest = json.loads((repo_root / "model_manifests/flynn-full-vision.json").read_text())
    for key, value in (("schema_version", 1), ("profile_id", "flynn-full-vision"),
                       ("upstream_commit", UPSTREAM_COMMIT), ("hf_revision", HF_REVISION)):
        if manifest.get(key) != value:
            raise ValueError(f"Unsupported manifest {key}: {manifest.get(key)!r}")
    files = manifest.get("files", [])
    if len(files) != 2 or {item.get("id") for item in files} != {"graph_archive", "checkpoint"}:
        raise ValueError("Manifest requires graph_archive and checkpoint exactly once")
    if len({item.get("path") for item in files}) != len(files):
        raise ValueError("Duplicate asset path")
    prefix = f"https://huggingface.co/datasets/benquan1/fly-gym-trained-policies/resolve/{HF_REVISION}/"
    for item in files:
        _relative(item["path"])
        _identity(item)
        if not isinstance(item.get("url"), str) or not item["url"].startswith(prefix):
            raise ValueError(f"Asset URL must use pinned Hugging Face revision: {item['id']}")
        if item.get("license") != "CC-BY-NC-4.0":
            raise ValueError(f"Unexpected asset license: {item['id']}")
    graph = manifest["graph"]
    if graph["edge_file"] != "connections_princeton.csv":
        raise ValueError("Unexpected edge filename")
    _identity(graph["edge_identity"])
    mappings = graph["mapping_files"]
    if len(mappings) != 7 or {item["path"] for item in mappings} != set(MAPPING_NAMES):
        raise ValueError("Manifest must pin all seven upstream mapping CSVs")
    for item in mappings:
        _identity(item)
        if "archive_identity" in item:
            _identity(item["archive_identity"])
        if item["source_path"] != f"upstream/fly-gym/connectomes/drosophila adult connectome/{item['path']}":
            raise ValueError(f"Unexpected mapping source: {item['path']}")
    return manifest


def _verified(path: Path, item: dict) -> bool:
    return path.is_file() and path.stat().st_size == item["size_bytes"] and sha256_file(path) == item["sha256"]


def verify_assets(repo_root: Path, asset_root: Path) -> dict:
    manifest = load_manifest(repo_root)
    records = []
    for item in manifest["files"]:
        record = {**item, "status": "missing"}
        try:
            path = _inside(asset_root, item["path"])
            if path.exists():
                record["status"] = "verified" if _verified(path, item) else "corrupt"
        except ValueError as error:
            record.update(status="unsafe", error=str(error))
        except OSError as error:
            record.update(status="error", error=str(error))
        records.append(record)
    return {"ok": all(item["status"] == "verified" for item in records),
            "profile_id": manifest["profile_id"], "files": records,
            "provenance_limit": manifest["provenance_limit"]}


def fetch_assets(repo_root: Path, asset_root: Path) -> dict:
    """Explicit acquisition only; never publish an incomplete or mismatched download."""
    report = verify_assets(repo_root, asset_root)
    for item in report["files"]:
        if item["status"] in ("verified", "unsafe"):
            continue
        temporary = None
        try:
            path = _inside(asset_root, item["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".download-", delete=False) as output:
                temporary = Path(output.name)
                digest, size = hashlib.sha256(), 0
                with urlopen(item["url"], timeout=60) as response:
                    while chunk := response.read(1024 * 1024):
                        size += len(chunk)
                        if size > item["size_bytes"]:
                            raise ValueError(f"Size mismatch for {item['id']}")
                        digest.update(chunk)
                        output.write(chunk)
                if size != item["size_bytes"] or digest.hexdigest() != item["sha256"]:
                    raise ValueError(f"Checksum/size mismatch for {item['id']}")
            temporary.replace(_inside(asset_root, item["path"]))
            item["status"] = "verified"
            item.pop("error", None)
        except (OSError, ValueError) as error:
            item.update(status="error", error=str(error))
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    report["ok"] = all(item["status"] == "verified" for item in report["files"])
    return report


def _check_mappings(repo_root: Path, directory: Path, mappings: list, copy_missing=False) -> None:
    for item in mappings:
        source = _inside(repo_root, item["source_path"])
        if not _verified(source, item):
            raise ValueError(f"Missing or different pinned upstream mapping: {item['path']}")
        path = _inside(directory, item["path"])
        if copy_missing and not path.exists():
            if "archive_identity" in item:
                raise ValueError(f"Missing pinned archived graph mapping: {item['path']}")
            shutil.copyfile(source, path)
        if not _verified(path, item.get("archive_identity", item)):
            raise ValueError(f"Missing or different graph mapping: {item['path']}")
        if "archive_identity" in item:
            normalized = path.read_bytes().replace(b"\r\n", b"\n")
            if len(normalized) != item["size_bytes"] or hashlib.sha256(normalized).hexdigest() != item["sha256"]:
                raise ValueError(f"Archived mapping differs beyond CRLF line endings: {item['path']}")


def prepare_graph(repo_root: Path, asset_root: Path) -> Path:
    """Extract a verified archive into a dedicated directory with pinned mapping CSVs."""
    manifest = load_manifest(repo_root)
    archive_item = next(item for item in manifest["files"] if item["id"] == "graph_archive")
    archive_path = _inside(asset_root, archive_item["path"])
    if not _verified(archive_path, archive_item):
        raise ValueError("graph_archive missing or corrupt; run palimpsest assets fetch/verify")
    graph = manifest["graph"]
    edge_identity = graph["edge_identity"]
    destination = _inside(asset_root, f"graph-{archive_item['sha256']}")
    metadata_name = "palimpsest-prepared.json"
    if destination.exists():
        metadata = json.loads(_inside(destination, metadata_name).read_text())
        edge = _inside(destination, metadata["edge_path"])
        if metadata["archive_sha256"] != archive_item["sha256"] or not _verified(edge, edge_identity):
            raise ValueError("Prepared graph edge differs; remove its dedicated directory and prepare again")
        _check_mappings(repo_root, edge.parent, graph["mapping_files"])
        return edge
    py7zr = importlib.import_module("py7zr")
    with tempfile.TemporaryDirectory(dir=asset_root, prefix=".graph-") as temporary:
        staging = Path(temporary)
        with py7zr.SevenZipFile(archive_path, "r") as archive:
            members = archive.list()
            names = set()
            for member in members:
                try:
                    relative = _relative(member.filename)
                except ValueError as error:
                    raise ValueError(f"Unsafe archive member: {member.filename}") from error
                if member.is_symlink or not (member.is_file or member.is_directory) or relative in names:
                    raise ValueError(f"Unsafe archive member: {member.filename}")
                names.add(relative)
            if sum(member.uncompressed for member in members) > graph["extraction_limit_bytes"]:
                raise ValueError("Graph archive exceeds declared extraction limit")
            archive.extractall(path=staging)
        edges = list(staging.rglob(graph["edge_file"]))
        if len(edges) != 1 or not edges[0].is_file():
            raise ValueError(f"Archive must contain exactly one {graph['edge_file']}")
        edge = edges[0]
        if not _verified(edge, edge_identity):
            raise ValueError(f"Extracted edge differs from pinned identity: {graph['edge_file']}")
        # Reject conflicting archived mapping copies before adding missing upstream inputs.
        for item in graph["mapping_files"]:
            for archived in staging.rglob(item["path"]):
                if not _verified(archived, item.get("archive_identity", item)):
                    raise ValueError(f"Different archived graph mapping: {item['path']}")
        _check_mappings(repo_root, edge.parent, graph["mapping_files"], copy_missing=True)
        relative_edge = str(edge.relative_to(staging))
        metadata = {"archive_sha256": archive_item["sha256"], "edge_path": relative_edge,
                    "edge_sha256": sha256_file(edge), "upstream_commit": UPSTREAM_COMMIT,
                    "mapping_files": graph["mapping_files"], "provenance_limit": manifest["provenance_limit"]}
        (staging / metadata_name).write_text(json.dumps(metadata, indent=2) + "\n")
        staging.rename(destination)
    return destination / relative_edge
