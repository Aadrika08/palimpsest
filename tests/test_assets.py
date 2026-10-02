import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from palimpsest.assets import (
    fetch_assets, load_manifest, prepare_graph, sha256_file, verify_assets,
)


REPO = Path(__file__).resolve().parents[1]
HAS_PY7ZR = importlib.util.find_spec("py7zr") is not None


class AssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.assets = Path(self.temp.name) / "assets"
        self.repo.mkdir()
        self.assets.mkdir()
        self.manifest = copy.deepcopy(load_manifest(REPO))
        self.manifest["graph"]["edge_identity"] = {}
        self.set_identity(self.manifest["graph"]["edge_identity"], b"pre,post,weight\n1,2,3\n")
        self.payloads = {"graph_archive": b"tiny graph", "checkpoint": b"tiny model"}
        for item in self.manifest["files"]:
            self.set_identity(item, self.payloads[item["id"]])
        for item in self.manifest["graph"]["mapping_files"]:
            item.pop("archive_identity", None)
            path = self.repo / item["source_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"root_id\n123\n")
            self.set_identity(item, path.read_bytes())
        self.write_manifest()

    @staticmethod
    def set_identity(item, data):
        item["sha256"] = hashlib.sha256(data).hexdigest()
        item["size_bytes"] = len(data)

    def write_manifest(self):
        path = self.repo / "model_manifests/flynn-full-vision.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(self.manifest))

    def write_assets(self):
        for item in self.manifest["files"]:
            (self.assets / item["path"]).write_bytes(self.payloads[item["id"]])

    def test_registry_pins_identity_and_mapping_hashes(self):
        manifest = load_manifest(REPO)
        self.assertEqual(manifest["profile_id"], "flynn-full-vision")
        self.assertEqual(manifest["upstream_commit"], "8d964599119b420de67ee259434d273651a1a76d")
        self.assertEqual(manifest["hf_revision"], "507bef22433c83db3581abd1ab393b25c3aa4989")
        self.assertEqual(len(manifest["graph"]["mapping_files"]), 7)
        for item in manifest["files"]:
            self.assertIn(manifest["hf_revision"], item["url"])
            self.assertEqual(item["license"], "CC-BY-NC-4.0")
        for item in manifest["graph"]["mapping_files"]:
            self.assertEqual(sha256_file(REPO / item["source_path"]), item["sha256"])

    def test_verify_missing_and_checksum_mismatch(self):
        report = verify_assets(self.repo, self.assets)
        self.assertFalse(report["ok"])
        self.assertEqual([item["status"] for item in report["files"]], ["missing", "missing"])
        self.write_assets()
        graph = self.assets / self.manifest["files"][0]["path"]
        graph.write_bytes(b"bad! graph")  # same size, wrong hash
        report = verify_assets(self.repo, self.assets)
        self.assertFalse(report["ok"])
        self.assertEqual(report["files"][0]["status"], "corrupt")
        self.assertEqual(report["files"][1]["status"], "verified")

    def test_verify_size_mismatch(self):
        self.write_assets()
        (self.assets / self.manifest["files"][0]["path"]).write_bytes(b"short")
        self.assertEqual(verify_assets(self.repo, self.assets)["files"][0]["status"], "corrupt")

    def test_manifest_rejects_unsafe_paths_and_wrong_profile(self):
        for bad in ("../escape", "/tmp/escape", "C:\\escape", "nested/../escape"):
            with self.subTest(path=bad):
                self.manifest["files"][0]["path"] = bad
                self.write_manifest()
                with self.assertRaises(ValueError):
                    load_manifest(self.repo)
        self.manifest["files"][0]["path"] = "graph.7z"
        self.manifest["profile_id"] = "arbitrary"
        self.write_manifest()
        with self.assertRaises(ValueError):
            load_manifest(self.repo)

    def test_verify_and_fetch_reject_symlink_destination(self):
        outside = self.repo / "outside"
        outside.write_bytes(self.payloads["graph_archive"])
        (self.assets / self.manifest["files"][0]["path"]).symlink_to(outside)
        self.assertEqual(verify_assets(self.repo, self.assets)["files"][0]["status"], "unsafe")
        with patch("palimpsest.assets.urlopen", return_value=io.BytesIO(b"tiny model")):
            self.assertFalse(fetch_assets(self.repo, self.assets)["ok"])
        self.assertEqual(outside.read_bytes(), self.payloads["graph_archive"])

    def test_fetch_verifies_before_publication_and_preserves_cached_file(self):
        checkpoint = self.assets / self.manifest["files"][1]["path"]
        checkpoint.write_bytes(self.payloads["checkpoint"])
        inode = checkpoint.stat().st_ino
        with patch("palimpsest.assets.urlopen", return_value=io.BytesIO(self.payloads["graph_archive"])) as transport:
            self.assertTrue(fetch_assets(self.repo, self.assets)["ok"])
            self.assertEqual(transport.call_count, 1)
        self.assertEqual(checkpoint.stat().st_ino, inode)
        self.assertEqual(len(list(self.assets.iterdir())), 2)

    def test_fetch_bad_hash_size_and_interruption_leave_no_partial_file(self):
        class Interrupted(io.BytesIO):
            def read(self, size=-1):
                raise OSError("download interrupted")

        for response in (io.BytesIO(b"bad! graph"), io.BytesIO(b"oversized graph"), Interrupted()):
            with self.subTest(response=response):
                with patch("palimpsest.assets.urlopen", return_value=response):
                    report = fetch_assets(self.repo, self.assets)
                self.assertFalse(report["ok"])
                self.assertFalse(any(self.assets.iterdir()))

    def test_prepare_requires_verified_archive_before_import_or_extract(self):
        with patch("palimpsest.assets.importlib.import_module") as loader:
            with self.assertRaisesRegex(ValueError, "graph_archive"):
                prepare_graph(self.repo, self.assets)
            loader.assert_not_called()

    def test_prepare_rejects_cache_even_if_local_metadata_is_rewritten(self):
        self.write_assets()
        graph_hash = self.manifest["files"][0]["sha256"]
        cache = self.assets / f"graph-{graph_hash}"
        cache.mkdir()
        edge = cache / "connections_princeton.csv"
        edge.write_bytes(b"forged edge list")
        for item in self.manifest["graph"]["mapping_files"]:
            (cache / item["path"]).write_bytes((self.repo / item["source_path"]).read_bytes())
        (cache / "palimpsest-prepared.json").write_text(json.dumps({
            "archive_sha256": graph_hash, "edge_path": edge.name,
            "edge_sha256": sha256_file(edge),
        }))
        with self.assertRaisesRegex(ValueError, "edge"):
            prepare_graph(self.repo, self.assets)

    def make_archive(self, entries=None, symlink=False):
        import py7zr
        path = self.assets / self.manifest["files"][0]["path"]
        with py7zr.SevenZipFile(path, "w") as archive:
            if symlink:
                (self.repo / "outside").write_bytes(b"outside target")
                source = self.repo / "linked"
                source.symlink_to(self.repo / "outside")
                archive.write(source, "link")
            for name, data in (entries or {"nested/connections_princeton.csv": b"pre,post,weight\n1,2,3\n"}).items():
                archive.writestr(data, name)
        self.set_identity(self.manifest["files"][0], path.read_bytes())
        self.write_manifest()

    @unittest.skipUnless(HAS_PY7ZR, "requires simulation extra py7zr")
    def test_prepare_real_archive_adds_all_pinned_mappings(self):
        self.make_archive()
        edge = prepare_graph(self.repo, self.assets)
        self.assertEqual(edge.name, "connections_princeton.csv")
        self.assertTrue(edge.is_relative_to(self.assets))
        self.assertTrue(edge.is_file())
        for item in self.manifest["graph"]["mapping_files"]:
            self.assertEqual(sha256_file(edge.parent / item["path"]), item["sha256"])
        self.assertEqual(prepare_graph(self.repo, self.assets), edge)

    @unittest.skipUnless(HAS_PY7ZR, "requires simulation extra py7zr")
    def test_prepare_preserves_pinned_crlf_mapping_and_requires_upstream_equivalence(self):
        item = self.manifest["graph"]["mapping_files"][0]
        for raw in (b"root_id\r\n123\r\n", b"root_id\r\n456\r\n"):
            with self.subTest(raw=raw):
                item["archive_identity"] = {}
                self.set_identity(item["archive_identity"], raw)
                self.make_archive({"connections_princeton.csv": b"pre,post,weight\n1,2,3\n",
                                   item["path"]: raw})
                if b"123" in raw:
                    edge = prepare_graph(self.repo, self.assets)
                    self.assertEqual((edge.parent / item["path"]).read_bytes(), raw)
                    self.assertEqual(prepare_graph(self.repo, self.assets), edge)
                else:
                    with self.assertRaisesRegex(ValueError, item["path"]):
                        prepare_graph(self.repo, self.assets)

    def test_prepare_rejects_archive_traversal_before_extraction(self):
        self.write_assets()
        archive = MagicMock()
        archive.__enter__.return_value = archive
        archive.list.return_value = [SimpleNamespace(filename="../escape", is_symlink=False,
                                                     is_file=True, is_directory=False)]
        module = SimpleNamespace(SevenZipFile=MagicMock(return_value=archive))
        with patch("palimpsest.assets.importlib.import_module", return_value=module):
            with self.assertRaisesRegex(ValueError, "Unsafe archive"):
                prepare_graph(self.repo, self.assets)
        archive.extractall.assert_not_called()
        self.assertFalse((self.assets.parent / "escape").exists())

    @unittest.skipUnless(HAS_PY7ZR, "requires simulation extra py7zr")
    def test_prepare_rejects_real_archive_symlink(self):
        self.make_archive(symlink=True)
        with self.assertRaisesRegex(ValueError, "Unsafe archive"):
            prepare_graph(self.repo, self.assets)
        self.assertEqual(len(list(self.assets.iterdir())), 1)

    @unittest.skipUnless(HAS_PY7ZR, "requires simulation extra py7zr")
    def test_prepare_rejects_missing_edge_or_changed_mapping(self):
        self.make_archive({"other.csv": b"unrelated"})
        with self.assertRaisesRegex(ValueError, "connections_princeton.csv"):
            prepare_graph(self.repo, self.assets)
        mapping = self.manifest["graph"]["mapping_files"][0]
        self.make_archive({"connections_princeton.csv": b"pre,post,weight\n1,2,3\n", mapping["path"]: b"wrong mapping"})
        with self.assertRaisesRegex(ValueError, mapping["path"]):
            prepare_graph(self.repo, self.assets)
        self.assertEqual(len(list(self.assets.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
