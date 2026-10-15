"""Authored fixtures for the fixed wheel-build route; no backend downloads."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "scripts/build_puck_python_louvain.py"
WORKER = ROOT / "scripts/puck_python_louvain_worker.py"


def module(path):
    assert path.is_file(), "bounded wheel-build entry is missing"
    spec = importlib.util.spec_from_file_location(path.stem + "_test", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def transport(raw=b"authored bytes", filename="demo-1.0-py3-none-any.whl"):
    return dict(kind="wheel-build-worker-v1", filename=filename,
        size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
        wheel_base64=base64.b64encode(raw).decode(), source_build_executed=True,
        forbidden_modules_absent=True, backend_version="84.0.0")


def test_transport_returns_exact_bytes_without_importing_them():
    value = module(PARENT)
    raw = b"raise RuntimeError('must never execute')"
    assert value.decode_transport(transport(raw), "demo-1.0-py3-none-any.whl") == raw


@pytest.mark.parametrize("defect", ["filename", "hash", "size", "boolean-size", "base64", "extra", "imports", "backend", "build", "large"])
def test_transport_refuses_unbound_or_oversized_result(defect):
    value = module(PARENT)
    row = transport()
    if defect == "filename": row["filename"] = "../demo.whl"
    elif defect == "hash": row["sha256"] = "0" * 64
    elif defect == "size": row["size_bytes"] += 1
    elif defect == "boolean-size": row["size_bytes"] = True
    elif defect == "base64": row["wheel_base64"] = "%%%"
    elif defect == "extra": row["runtime_qualified"] = True
    elif defect == "imports": row["forbidden_modules_absent"] = False
    elif defect == "backend": row["backend_version"] = "unreviewed"
    elif defect == "build": row["source_build_executed"] = False
    else: row = transport(b"x" * (256 * 1024 + 1))
    with pytest.raises(ValueError):
        value.decode_transport(row, "demo-1.0-py3-none-any.whl")


def test_worker_wheel_transport_is_single_bounded_regular_file(tmp_path):
    value = module(WORKER)
    name = "demo-1.0-py3-none-any.whl"
    (tmp_path / name).write_bytes(b"wheel bytes")
    row = value.pack_wheel(tmp_path, name)
    assert row["wheel_base64"] == base64.b64encode(b"wheel bytes").decode()
    assert row["sha256"] == hashlib.sha256(b"wheel bytes").hexdigest()


@pytest.mark.parametrize("defect", ["extra", "symlink", "hardlink", "large", "name"])
def test_worker_refuses_ambiguous_or_oversized_output(tmp_path, defect):
    value = module(WORKER)
    name = "demo-1.0-py3-none-any.whl"
    output = tmp_path / "wheels"
    output.mkdir()
    path = output / name
    path.write_bytes(b"wheel bytes")
    if defect == "extra": (output / "unexpected").write_text("x")
    elif defect == "symlink":
        path.unlink()
        path.symlink_to(tmp_path / "elsewhere")
    elif defect == "hardlink": os.link(path, tmp_path / "alias")
    elif defect == "large": path.write_bytes(b"x" * (256 * 1024 + 1))
    else: name = "../demo.whl"
    with pytest.raises((ValueError, OSError)):
        value.pack_wheel(output, name)


@pytest.mark.parametrize("name", ["community", "numpy.random", "networkx", "torch", "torchvision", "mujoco"])
def test_target_import_guard_refuses_numerical_and_target_modules(name):
    value = module(WORKER)
    with pytest.raises(ImportError):
        value.BlockTarget().find_spec(name)
    assert value.BlockTarget().find_spec("setuptools") is None


def test_process_filter_denies_creation_session_changes_and_exec_in_owned_child():
    module(WORKER)
    program = """
import ctypes, errno, json, os, runpy, sys
worker = runpy.run_path(sys.argv[1])
worker['disable_process_changes']()
libc = ctypes.CDLL(None, use_errno=True)
checked=[]
for nr in worker['DENIED_SYSCALLS']:
    ctypes.set_errno(0)
    result=libc.syscall(nr, 0, 0, 0, 0, 0, 0)
    error=ctypes.get_errno()
    if result != -1 or error != errno.EPERM:
        os._exit(9)
    checked.append(nr)
print(json.dumps(checked))
"""
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", program, str(WORKER)],
        capture_output=True, text=True, timeout=10, start_new_session=True)
    assert result.returncode == 0, result.stderr
    assert len(json.loads(result.stdout)) >= 10


def test_tree_recheck_refuses_changed_bytes_and_unregistered_entries(tmp_path):
    value = module(PARENT)
    (tmp_path / "pkg").mkdir()
    raw = b"inert"
    path = tmp_path / "pkg/file.py"
    path.write_bytes(raw)
    manifest = dict(files=[dict(path="pkg/file.py", size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())], directories=[])
    value.verify_tree(tmp_path, manifest, time.monotonic() + 5)
    path.write_bytes(b"other")
    with pytest.raises(ValueError): value.verify_tree(tmp_path, manifest, time.monotonic() + 5)
    path.write_bytes(raw)
    (tmp_path / "extra").write_bytes(b"x")
    with pytest.raises(ValueError): value.verify_tree(tmp_path, manifest, time.monotonic() + 5)


def test_baseline_inventory_detects_added_files_and_changed_symlink(tmp_path):
    value = module(PARENT)
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    (prefix / "python").write_bytes(b"host fixture")
    (prefix / "alias").symlink_to("python")
    baseline = dict(python_prefix=str(prefix), **value.prefix_inventory(prefix, time.monotonic() + 5),
        external_libraries=[], bwrap_executable=None)
    value.verify_baseline(baseline, time.monotonic() + 5)
    (prefix / "extra").write_bytes(b"x")
    with pytest.raises(ValueError): value.verify_baseline(baseline, time.monotonic() + 5)
    (prefix / "extra").unlink()
    (prefix / "alias").unlink()
    (prefix / "alias").symlink_to("extra")
    with pytest.raises(ValueError): value.verify_baseline(baseline, time.monotonic() + 5)


def test_stage_retains_failed_child_without_publishing_a_wheel(tmp_path):
    value = module(PARENT)
    stage = tmp_path / "stage"
    stage.mkdir()
    with pytest.raises(RuntimeError):
        value.run_stage([sys.executable, "-I", "-S", "-B", "-c", "print('partial'); raise SystemExit(7)"],
            stage, ROOT, time.monotonic() + 5, time.monotonic() + 8, {})
    observation = json.loads((stage / "supervision.json").read_text())
    assert observation["status"] == "failed"
    assert observation["returncode"] == 7
    assert observation["matching_survivors"] == []
    assert (stage / "stdout.log").read_text() == "partial\n"
    assert list(stage.glob("*.whl")) == []


def authored_configuration(value):
    return dict(kind="puck-python-louvain-build-v1", version=1,
        sources=[dict(path=p, size_bytes=1, sha256="0" * 64) for p in value.CODE_PATHS],
        source_archive=dict(path=value.SOURCE_ARCHIVE, size_bytes=204641,
            sha256="b7ba2df5002fd28d3ee789a49532baad11fe648e4f2117cf0798e7520a1da56b"),
        host_baseline=dict(path=value.BASELINE_PATH, size_bytes=1, sha256="0" * 64),
        backend=dict(value.BACKEND), output="runs/puck-python-louvain-build-01",
        limits=dict(value.LIMITS), claims=dict(value.CLAIMS))


def test_exact_authored_configuration_is_loadable_without_build_execution(tmp_path):
    value = module(PARENT)
    config = authored_configuration(value)
    raw = value.canonical(config)
    (tmp_path / "config.json").write_bytes(raw)
    actual, row = value.load_configuration(tmp_path, "config.json", hashlib.sha256(raw).hexdigest())
    assert actual == config
    assert row["sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("defect", ["authority", "backend", "limits", "output", "archive", "sources", "version", "extra"])
def test_configuration_cannot_change_the_reviewed_input_or_execution_contract(tmp_path, defect):
    value = module(PARENT)
    config = authored_configuration(value)
    if defect == "authority": config["claims"]["study_authorized"] = True
    elif defect == "backend": config["backend"]["url"] = "https://unreviewed.invalid/backend.whl"
    elif defect == "limits": config["limits"]["normal_seconds"] = 121
    elif defect == "output": config["output"] = "runs/puck-python-louvain-build-02"
    elif defect == "archive": config["source_archive"]["sha256"] = "0" * 64
    elif defect == "sources": config["sources"].pop()
    elif defect == "version": config["version"] = True
    else: config["extra"] = True
    raw = value.canonical(config)
    (tmp_path / "config.json").write_bytes(raw)
    with pytest.raises(ValueError):
        value.load_configuration(tmp_path, "config.json", hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize("late_boundary", ["publication", "guard-teardown", "stdout-flush"])
def test_main_denies_late_success_after_publication_teardown_and_output(monkeypatch, late_boundary):
    from contextlib import contextmanager
    from types import SimpleNamespace
    value = module(PARENT)
    elapsed = [0.0]
    monkeypatch.setattr(value, "time", SimpleNamespace(monotonic=lambda: elapsed[0]))
    monkeypatch.setattr(value.os, "getpgrp", value.os.getpid)
    monkeypatch.setattr(value.sys, "argv", [str(PARENT), "--configuration", "authored.json", "--sha256", "0" * 64])
    def parent(*args):
        if late_boundary == "publication": elapsed[0] = 121.0
        return {"status": "wheel_verified"}
    @contextmanager
    def guard(*args):
        yield
        if late_boundary == "guard-teardown": elapsed[0] = 121.0
    def output(*args, **kwargs):
        if late_boundary == "stdout-flush": elapsed[0] = 121.0
    def clock(deadline):
        if elapsed[0] >= deadline: raise TimeoutError("normal deadline exhausted")
    monkeypatch.setattr(value, "parent", parent)
    monkeypatch.setattr(value, "hard_guard", guard)
    monkeypatch.setattr(value, "print", output, raising=False)
    monkeypatch.setattr(value, "clock", clock)
    with pytest.raises(TimeoutError, match="normal deadline"):
        value.main()


def test_flushed_terminal_output_remains_inside_outer_hard_guard(monkeypatch):
    from contextlib import contextmanager
    value = module(PARENT)
    active = [False]
    @contextmanager
    def guard(*args):
        active[0] = True
        try: yield
        finally: active[0] = False
    def output(*args, **kwargs):
        assert active[0], "terminal output escaped the hard guard"
        assert kwargs.get("flush") is True
    monkeypatch.setattr(value.os, "getpgrp", value.os.getpid)
    monkeypatch.setattr(value.sys, "argv", [str(PARENT), "--configuration", "authored.json", "--sha256", "0" * 64])
    monkeypatch.setattr(value, "parent", lambda *args: {"status": "wheel_verified"})
    monkeypatch.setattr(value, "hard_guard", guard)
    monkeypatch.setattr(value, "print", output, raising=False)
    assert value.main() == 0
