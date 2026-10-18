"""Pinned package preparation on real files and authored, non-executing wheels."""
import base64
from email.message import Message
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts/acquire_puck_cpu_payloads.py"


def module():
    assert DRIVER.is_file(), "Pinned CPU payload acquisition entry is missing"
    spec = importlib.util.spec_from_file_location("cpu_payload_acquisition_test", DRIVER)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def authored_wheel():
    metadata = b"Metadata-Version: 2.1\nName: tiny\nVersion: 1.0\n"
    files = {
        "tiny/__init__.py": b"raise RuntimeError('TARGET_PACKAGE_MUST_NOT_EXECUTE')\n",
        "tiny-1.0.dist-info/METADATA": metadata,
        "tiny-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    lines = [
        path + ",sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
        + "," + str(len(raw)) for path, raw in files.items()
    ]
    files["tiny-1.0.dist-info/RECORD"] = ("\n".join(lines) + "\ntiny-1.0.dist-info/RECORD,,\n").encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, raw in files.items():
            info = zipfile.ZipInfo(path)
            info.external_attr = (0o100644 << 16)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    raw = output.getvalue()
    spec = {
        "name": "tiny", "version": "1.0", "filename": "tiny-1.0-py3-none-any.whl",
        "url": "https://files.pythonhosted.org/packages/authored/tiny-1.0-py3-none-any.whl",
        "size_bytes": len(raw), "sha256": sha(raw), "metadata_sha256": sha(metadata),
        "format": "wheel",
    }
    return raw, spec


class Response(io.BytesIO):
    status = 200

    def __init__(self, raw, url, declared=None):
        super().__init__(raw)
        self.url = url
        self.headers = Message()
        self.headers["Content-Length"] = str(len(raw) if declared is None else declared)

    def geturl(self):
        return self.url


def fake_network(monkeypatch, value, raw, spec, *, declared=None):
    opener = types.SimpleNamespace(open=lambda request, timeout:
        Response(raw, spec["url"], declared))
    monkeypatch.setattr(value.urllib.request, "build_opener", lambda *args: opener)


def limits(value):
    return {**value.CEILINGS, "min_free_bytes": 1, "min_available_ram_bytes": 1}


def test_retained_selection_covers_all71_exact_artifacts_without_installation():
    value = module()
    candidate = json.loads((ROOT / "docs/plans/puck-cpu-runtime-candidate-v1.json").read_text())
    assessment = json.loads((ROOT / "docs/reports/puck-cpu-footprint-02/assessment.json").read_text())
    selected = value.select_archives(candidate, assessment)
    assert len(selected) == 71
    assert sum(row["format"] == "wheel" for row in selected) == 70
    assert sum(row["size_bytes"] for row in selected) == 385328518
    assert next(row for row in selected if row["name"] == "python-louvain")["sha256"] == (
        "b7ba2df5002fd28d3ee789a49532baad11fe648e4f2117cf0798e7520a1da56b"
    )


@pytest.mark.parametrize("defect", ["missing-wheel", "wrong-url", "duplicate-file", "wrong-pin"])
def test_selection_refuses_incomplete_or_unpinned_artifacts(defect):
    value = module()
    candidate = json.loads((ROOT / "docs/plans/puck-cpu-runtime-candidate-v1.json").read_text())
    assessment = json.loads((ROOT / "docs/reports/puck-cpu-footprint-02/assessment.json").read_text())
    if defect == "missing-wheel":
        assessment["wheels"].pop()
    elif defect == "wrong-url":
        assessment["wheels"][0]["url"] = "https://unreviewed.example/package.whl"
    elif defect == "duplicate-file":
        assessment["wheels"][1]["filename"] = assessment["wheels"][0]["filename"]
    else:
        candidate["target"]["candidate_pins"][0] = "unreviewed==1"
    with pytest.raises(ValueError):
        value.select_archives(candidate, assessment)


def test_download_verifies_and_publishes_real_wheel_without_executing_package(tmp_path, monkeypatch):
    value = module()
    raw, spec = authored_wheel()
    fake_network(monkeypatch, value, raw, spec)
    result, request = value.download_archive(spec, tmp_path, limits(value), time.monotonic() + 10)
    assert (tmp_path / spec["filename"]).read_bytes() == raw
    assert not (tmp_path / (spec["filename"] + ".partial")).exists()
    assert result["archive_payload_verified"] is result["record_verified"] is True
    assert result["member_count"] == 4
    assert request["body_bytes"] == len(raw)
    assert "tiny" not in sys.modules


@pytest.mark.parametrize("defect", ["hash", "short", "long", "declared-size"])
def test_failed_body_keeps_partial_and_never_publishes_verified_archive(tmp_path, monkeypatch, defect):
    value = module()
    raw, spec = authored_wheel()
    body, declared = raw, len(raw)
    if defect == "hash":
        spec["sha256"] = "0" * 64
    elif defect == "short":
        body = raw[:-1]
    elif defect == "long":
        body = raw + b"x"
    else:
        declared += 1
    fake_network(monkeypatch, value, body, spec, declared=declared)
    with pytest.raises(ValueError):
        value.download_archive(spec, tmp_path, limits(value), time.monotonic() + 10)
    assert (tmp_path / spec["filename"]).exists()
    assert not (tmp_path / (spec["filename"] + ".partial")).exists()


def test_existing_archive_cannot_be_overwritten(tmp_path, monkeypatch):
    value = module()
    raw, spec = authored_wheel()
    target = tmp_path / spec["filename"]
    target.write_bytes(b"retained original")
    fake_network(monkeypatch, value, raw, spec)
    with pytest.raises(FileExistsError):
        value.download_archive(spec, tmp_path, limits(value), time.monotonic() + 10)
    assert target.read_bytes() == b"retained original"
    assert not (tmp_path / (spec["filename"] + ".partial")).exists()


def test_expired_download_does_not_create_output(tmp_path):
    value = module()
    _, spec = authored_wheel()
    with pytest.raises(TimeoutError):
        value.download_archive(spec, tmp_path, limits(value), time.monotonic() - 1)
    assert list(tmp_path.iterdir()) == []


def test_redirects_are_refused_instead_of_following_other_payload_url():
    value = module()
    with pytest.raises(ValueError):
        value.NoRedirect().redirect_request(None, None, 302, "redirect", {},
                                            "https://unreviewed.example/other.whl")


def test_manifest_is_bounded_and_never_replaces_retained_evidence(tmp_path):
    value = module()
    path = tmp_path / "manifest.json"
    with pytest.raises(ValueError):
        value.write_report(path, {"oversize": "x" * 30}, 8)
    assert not path.exists()
    value.write_report(path, {"status": "retained"}, 100)
    with pytest.raises(FileExistsError):
        value.write_report(path, {"status": "changed"}, 100)
    assert json.loads(path.read_text()) == {"status": "retained"}


def configuration(root, value):
    for name in value.CODE_PATHS:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"authored source, not an executable runtime\n")
    raw, wheel = authored_wheel()
    source = b"authored source archive; never unpacked or executed"
    source_url = "https://files.pythonhosted.org/packages/authored/python-louvain-0.16.tar.gz"
    assessment = {
        "kind": "puck-cpu-wheel-metadata-assessment-v1", "version": 1,
        "wheels": [{"name": "tiny", "version": "1.0", "filename": wheel["filename"],
            "url": wheel["url"], "archive_bytes": len(raw),
            "archive_sha256_index_declared": sha(raw), "metadata_sha256": wheel["metadata_sha256"]}],
        "missing": [{"name": "python-louvain", "version": "0.16",
            "sdist": {"url": source_url, "size": len(source), "hash": "sha256:" + sha(source)}}],
    }
    def save(name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = value.canonical(content)
        path.write_bytes(data)
        return {"path": name, "size_bytes": len(data), "sha256": sha(data)}
    evidence = save("assessment.json", assessment)
    candidate = save("candidate.json", {
        "kind": "puck-cpu-runtime-candidate-v1", "version": 1,
        "target": {"candidate_pins": ["python-louvain==0.16", "tiny==1.0"],
                   "candidate_pin_count": 2}, "evidence": [evidence],
    })
    python = Path(sys.executable).resolve()
    sources = []
    for name in sorted(value.CODE_PATHS):
        data = (root / name).read_bytes()
        sources.append({"path": name, "size_bytes": len(data), "sha256": sha(data)})
    config = {
        "kind": "puck-cpu-payload-acquisition-v1", "version": 1,
        "candidate": candidate, "assessment": evidence, "sources": sources,
        "interpreter": {"path": str(python), "size_bytes": python.stat().st_size,
                        "sha256": sha(python.read_bytes())},
        "output": "runs/puck-cpu-payload-acquisition-01",
        "limits": limits(value), "claims": dict(value.FALSE_CLAIMS),
    }
    row = save("configuration.json", config)
    return config, row, {wheel["filename"]: base64.b64encode(raw).decode(),
                        "python-louvain-0.16.tar.gz": base64.b64encode(source).decode()}


@pytest.mark.parametrize("defect", ["hash", "limit-bool", "authority", "source-closure"])
def test_configuration_rejects_unpinned_or_authority_expanding_values(tmp_path, defect):
    value = module()
    config, row, _ = configuration(tmp_path, value)
    if defect == "hash":
        row["sha256"] = "0" * 64
    else:
        if defect == "limit-bool":
            config["limits"]["max_requests"] = True
        elif defect == "authority":
            config["claims"]["installed"] = True
        else:
            config["sources"].pop()
        raw = value.canonical(config)
        (tmp_path / row["path"]).write_bytes(raw)
        row["sha256"] = sha(raw)
    with pytest.raises(ValueError):
        value.load_configuration(tmp_path, row["path"], row["sha256"])


def test_worker_whole_authored_allocation_keeps_exact_manifests_and_false_claims(tmp_path):
    value = module()
    config, row, payloads = configuration(tmp_path, value)
    output = tmp_path / config["output"]
    (output / "archives").mkdir(parents=True)
    (output / "manifests").mkdir()
    fixture = tmp_path / "authored-network.json"
    fixture.write_text(json.dumps(payloads))
    # Isolate irreversible process resource limits; transport alone is authored.
    code = r'''
import base64,importlib.util,io,json,pathlib,sys,types
from email.message import Message
spec=importlib.util.spec_from_file_location("authored_acquisition",sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=pathlib.Path(sys.argv[2]);payloads=json.loads((root/"authored-network.json").read_text())
class Response(io.BytesIO):
    status=200
    def __init__(self,url):
        raw=base64.b64decode(payloads[url.rsplit("/",1)[-1]])
        super().__init__(raw);self.url=url;self.headers=Message()
        self.headers["Content-Length"]=str(len(raw))
    def geturl(self):return self.url
m.urllib.request.build_opener=lambda *args:types.SimpleNamespace(open=lambda req,timeout:Response(req.full_url))
result=m.worker(root,"configuration.json",sys.argv[3])
assert result["status"]=="payloads_verified"
assert "tiny" not in sys.modules
'''
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(DRIVER),
                             str(tmp_path), row["sha256"]], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    receipt = json.loads((output / "worker-result.json").read_text())
    assert receipt["archive_count"] == 2 and receipt["wheel_count"] == 1
    assert receipt["wheel_member_count"] == 4
    assert len(list((output / "archives").iterdir())) == 2
    assert len(list((output / "manifests").iterdir())) == 2
    assert all(receipt[key] is False for key in value.FALSE_CLAIMS if key != "qualification_claims")
    assert receipt["qualification_claims"] == []
    for artifact in receipt["artifacts"]:
        manifest = (output / artifact["manifest"]).read_bytes()
        assert sha(manifest) == artifact["manifest_sha256"]
        assert len(manifest) == artifact["manifest_size_bytes"]


def test_archive_publication_has_no_multi_link_window_for_resource_monitor(tmp_path, monkeypatch):
    value = module()
    raw, spec = authored_wheel()
    fake_network(monkeypatch, value, raw, spec)
    from palimpsest.bounded_qualification import _output_bytes
    original = os.link
    def link_and_sample(*args, **kwargs):
        original(*args, **kwargs)
        # Deterministically sample the real namespace at the old publication gap.
        _output_bytes(tmp_path)
    monkeypatch.setattr(os, "link", link_and_sample)
    result, _ = value.download_archive(spec, tmp_path, limits(value), time.monotonic() + 10)
    assert result["archive_payload_verified"] is True
    assert _output_bytes(tmp_path) == len(raw)


def test_allocated_archive_names_remain_present_for_each_monitor_sample(tmp_path, monkeypatch):
    value = module()
    raw, spec = authored_wheel()
    fake_network(monkeypatch, value, raw, spec)
    observed = {}
    original = os.write
    def write_and_sample(fd, data):
        count = original(fd, data)
        for path in tmp_path.iterdir():
            observed.setdefault(path.name, (path.stat().st_dev, path.stat().st_ino))
        return count
    monkeypatch.setattr(os, "write", write_and_sample)
    value.download_archive(spec, tmp_path, limits(value), time.monotonic() + 10)
    assert observed
    for name, identity in observed.items():
        current = (tmp_path / name).stat()
        assert (current.st_dev, current.st_ino) == identity
        assert current.st_nlink == 1
