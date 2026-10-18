"""Package-preparation behavior; no acquired package is imported."""
import importlib.util
from pathlib import Path
import time
import pytest


def module():
    path = Path(__file__).resolve().parents[1] / "scripts/install_puck_cpu.py"
    assert path.exists(), "offline CPU installation entry is missing"
    spec = importlib.util.spec_from_file_location("cpu_install", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_explicit_wheels_disable_implicit_work(tmp_path):
    m = module()
    wheels = [tmp_path / "first.whl", tmp_path / "second.whl"]
    argv = m.installer_argv(tmp_path / "site", wheels)
    assert argv[0] == m.UV
    assert argv[argv.index("--") + 1:] == [str(p) for p in wheels]
    for flag in ("--no-deps", "--no-index", "--offline", "--no-build",
                 "--no-cache", "--no-config", "--no-python-downloads", "--no-compile-bytecode"):
        assert flag in argv
    assert argv[argv.index("--link-mode") + 1] == "copy"


@pytest.mark.parametrize("source,expected", [
    ("demo/__init__.py", "demo/__init__.py"),
    ("demo-1.data/data/share/man/demo.1", "share/man/demo.1"),
    ("demo-1.data/scripts/demo", "bin/demo"),
    ("demo-1.data/headers/demo.h", "include/demo/demo.h"),
])
def test_wheel_data_reaches_target_scheme(source, expected):
    assert module().destination(source, "demo") == expected


def test_census_hashes_bytes_and_rejects_linked_or_hook_inputs(tmp_path):
    m = module()
    site = tmp_path / "site"
    site.mkdir()
    (site / "demo.py").write_bytes(b"raise RuntimeError('never execute')\n")
    result = m.census(site, time.monotonic() + 10)
    assert result["file_count"] == 1 and result["directory_count"] == 0
    assert result["total_bytes"] == (site / "demo.py").stat().st_size
    (site / "alias.py").symlink_to("demo.py")
    with pytest.raises(ValueError, match="regular|symlink"):
        m.census(site, time.monotonic() + 10)
    (site / "alias.py").unlink()
    (site / "hook.pth").write_text("import demo\n")
    with pytest.raises(ValueError, match="hook|bytecode"):
        m.census(site, time.monotonic() + 10)


def test_fixture_carries_poison_code_and_unsatisfied_dependency(tmp_path):
    import zipfile
    wheel = module().make_fixture(tmp_path)
    with zipfile.ZipFile(wheel) as archive:
        assert "never import" in archive.read("install_fixture/__init__.py").decode()
        assert "not-installed-for-fixture" in archive.read("install_fixture-0.0.dist-info/METADATA").decode()
        assert "fixture-hook-executed" in archive.read("install_fixture.pth").decode()


def test_namespace_has_private_network_and_clean_environment(tmp_path):
    m = module()
    baseline = {"python_prefix": str(Path(m.PYTHON).parents[1]),
                "external_libraries": [], "host_path_aliases": []}
    cmd = m.sandbox_command(baseline, tmp_path / "site", tmp_path / "scratch", [])
    assert "--unshare-all" in cmd and "--share-net" not in cmd
    assert "--clearenv" in cmd and "--as-pid-1" in cmd
    assert "SETUPTOOLS_USE_DISTUTILS" in cmd
    assert cmd[cmd.index("SETUPTOOLS_USE_DISTUTILS") + 1] == "stdlib"
    assert "--remount-ro" in cmd


@pytest.mark.skipif(__import__("os").environ.get("PALIMPSEST_INSTALL_FIXTURE") != "1",
                    reason="explicit authored namespace/installer fixture only")
def test_real_namespace_installs_without_executing_fixture(tmp_path):
    import json
    import subprocess
    m = module()
    root = Path(__file__).resolve().parents[1]
    program = f"""import importlib.util,json,sys,time
from pathlib import Path
root=Path({str(root)!r})
sys.path.insert(0,str(root/'src'))
spec=importlib.util.spec_from_file_location('cpu_install',root/'scripts/install_puck_cpu.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from palimpsest.bounded_qualification import hard_guard
base=Path({str(tmp_path)!r})
for name in ('site','scratch','scratch/home','logs'):(base/name).mkdir()
fixture=m.make_fixture(base)
baseline=json.loads((root/'docs/plans/puck-python-louvain-host-baseline-v1.json').read_bytes())
normal=time.monotonic()+15;state={{}}
with hard_guard(normal+3,state):
 result=m.run_stage(baseline,base/'site',base/'scratch',[fixture],base/'logs',normal,normal+3,state)
 assert result['status']=='completed' and result['returncode']==0
 assert (base/'site/install_fixture/__init__.py').is_file()
 assert (base/'site/install_fixture.pth').is_file()
 assert not list(base.rglob('fixture-hook-executed'))
 print(json.dumps(result))
"""
    result = subprocess.run([m.PYTHON, '-I', '-S', '-B', '-c', program],
                            capture_output=True, text=True, timeout=22, start_new_session=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["matching_survivors"] == []


def test_mutable_cache_links_are_counted_without_following(tmp_path):
    m = module()
    site, scratch = tmp_path/'site', tmp_path/'scratch'
    site.mkdir(); scratch.mkdir()
    (scratch/'cache-link').symlink_to('/a/target/that/must/not/be/followed')
    assert m.mutable_usage((site,scratch)) == (scratch/'cache-link').lstat().st_size
    (site/'bad-link').symlink_to('/a/target/that/must/not/be/followed')
    with pytest.raises(ValueError, match='special|symlink'):
        m.mutable_usage((site,scratch))
