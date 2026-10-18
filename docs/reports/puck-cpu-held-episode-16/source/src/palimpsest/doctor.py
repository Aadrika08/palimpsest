"""Read-only setup diagnostics; importing this module never imports simulation code."""

import csv
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


UPSTREAM_PIN = "8d964599119b420de67ee259434d273651a1a76d"
SIMULATION_DISTRIBUTIONS = (
    "torch", "torchvision", "numpy", "scipy", "pandas", "scikit-learn",
    "mujoco", "gymnasium", "glfw", "opencv-python", "matplotlib", "seaborn",
    "networkx", "python-louvain", "py7zr",
)
RENDERER_PROBE = '''
import json
import mujoco
from mujoco import gl_context

model = mujoco.MjModel.from_xml_string('<mujoco><worldbody><geom type="sphere" size="0.1"/></worldbody></mujoco>')
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)
with mujoco.Renderer(model, height=32, width=32) as renderer:
    renderer.update_scene(data)
    image = renderer.render()
    assert image.shape == (32, 32, 3), image.shape
    from OpenGL import GL
    device = GL.glGetString(GL.GL_RENDERER)
    gl_version = GL.glGetString(GL.GL_VERSION)
    if not device or not gl_version:
        raise RuntimeError("OpenGL device/version query returned no result")
    print(json.dumps({"backend": gl_context.GLContext.__module__.rsplit(".", 1)[-1],
                      "version": mujoco.__version__, "device": device.decode(),
                      "opengl_version": gl_version.decode(), "shape": list(image.shape)}))
'''


def diagnose(repo_root: Path, asset_root: Path, probe_renderer: bool = False) -> dict:
    """Inspect setup without downloads, simulation imports, or parent environment changes."""
    repo_root, asset_root = Path(repo_root).resolve(), Path(asset_root).resolve()
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    add("python", "ok" if sys.version_info[:2] == (3, 11) else "error",
        {"version": platform.python_version(), "executable": sys.executable,
         "required": "Python 3.11; uv sync --extra simulation"})
    add("platform", "info", {"platform": platform.platform(), "machine": platform.machine()})
    try:
        add("dependency:palimpsest", "ok", metadata.version("palimpsest"))
    except metadata.PackageNotFoundError:
        add("dependency:palimpsest", "missing", "Run uv sync --extra simulation")
    for distribution in SIMULATION_DISTRIBUTIONS:
        try:
            add(f"dependency:{distribution}", "ok", metadata.version(distribution))
        except metadata.PackageNotFoundError:
            add(f"dependency:{distribution}", "missing", "Run uv sync --extra simulation")

    upstream = repo_root / "upstream" / "fly-gym"
    try:
        # git -C accepts non-repositories by walking to the parent; verify its root first.
        root = subprocess.run(["git", "-C", str(upstream), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, check=True, timeout=5)
        if Path(root.stdout.strip()).resolve() != upstream:
            raise ValueError("upstream/fly-gym is not an initialized submodule")
        head = subprocess.run(["git", "-C", str(upstream), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True, timeout=5)
        status = subprocess.run(["git", "-C", str(upstream), "status", "--porcelain", "--untracked-files=normal"],
                                capture_output=True, text=True, check=True, timeout=5)
        commit, dirty = head.stdout.strip(), bool(status.stdout.strip())
        add("upstream", "ok" if commit == UPSTREAM_PIN and not dirty else "error",
            {"path": str(upstream), "commit": commit, "expected_commit": UPSTREAM_PIN,
             "dirty": dirty, "changes": status.stdout.splitlines()})
    except FileNotFoundError as exc:
        add("upstream", "missing", f"git unavailable: {exc}; install git and run git submodule update --init upstream/fly-gym")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        add("upstream", "error", f"{exc}; run git submodule update --init upstream/fly-gym")

    try:
        fields = {line.split(":", 1)[0]: int(line.split()[1]) * 1024
                  for line in Path("/proc/meminfo").read_text().splitlines()
                  if line.startswith(("MemTotal:", "MemAvailable:"))}
        add("ram", "ok", {"total_bytes": fields["MemTotal"], "available_bytes": fields["MemAvailable"]})
    except (OSError, ValueError, KeyError) as exc:
        add("ram", "info", f"Available RAM could not be measured: {exc}")
    try:
        disk_path = asset_root
        while not disk_path.exists() and disk_path.parent != disk_path:
            disk_path = disk_path.parent
        disk = shutil.disk_usage(disk_path)
        add("disk", "ok", {"path": str(disk_path), "total_bytes": disk.total, "free_bytes": disk.free})
    except OSError as exc:
        add("disk", "error", f"Free disk could not be measured: {exc}")

    try:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.free",
                              "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, check=True, timeout=5)
        devices = [{"name": row[0].strip(), "driver_version": row[1].strip(),
                    "memory_total_mib": int(row[2]), "memory_free_mib": int(row[3])}
                   for row in csv.reader(gpu.stdout.splitlines()) if row]
        add("gpu", "ok" if devices else "info", {"devices": devices, "source": "nvidia-smi"})
    except subprocess.TimeoutExpired:
        add("gpu", "info", "nvidia-smi timed out after 5 seconds; GPU availability unverified")
    except (OSError, ValueError, IndexError, subprocess.SubprocessError) as exc:
        add("gpu", "info", f"NVIDIA device/VRAM unavailable: {exc}")

    try:
        from palimpsest.assets import verify_assets
        assets = verify_assets(repo_root, asset_root)
        asset_status = "ok" if assets["ok"] else "missing"
        if any(item["status"] in {"corrupt", "unsafe", "error"} for item in assets["files"]):
            asset_status = "error"
        add("assets", asset_status,
            {"root": str(asset_root), "verification": assets, "acquisition": "palimpsest assets fetch"})
    except (ImportError, OSError, ValueError, KeyError) as exc:
        add("assets", "missing", f"Asset verification unavailable: {exc}; run palimpsest assets fetch")

    env = os.environ.copy()
    selection = "explicit MUJOCO_GL" if "MUJOCO_GL" in env else "MuJoCo platform default"
    if "MUJOCO_GL" not in env and platform.system() == "Linux":
        env["MUJOCO_GL"] = "egl"
        selection = "Linux default (MUJOCO_GL unset)"
    backend = env.get("MUJOCO_GL", "platform default")
    if not probe_renderer:
        add("renderer", "info", {"requested_backend": backend, "backend_selection": selection,
                                 "probed": False, "command": "palimpsest doctor --probe-renderer"})
    else:
        try:
            rendered = subprocess.run([sys.executable, "-c", RENDERER_PROBE], env=env,
                                      capture_output=True, text=True, timeout=15)
            if rendered.returncode:
                add("renderer", "error", {"requested_backend": backend, "backend_selection": selection,
                    "exit_code": rendered.returncode, "stderr": rendered.stderr[-4000:],
                    "setup": "uv sync --extra simulation"})
            else:
                result = json.loads(rendered.stdout)
                if not isinstance(result, dict) or result.get("shape") != [32, 32, 3] or not all(result.get(key) for key in ("backend", "version", "device")):
                    raise ValueError("Renderer did not report an image, actual backend, version and device")
                add("renderer", "ok", {**result, "requested_backend": backend, "backend_selection": selection, "probed": True})
        except subprocess.TimeoutExpired:
            add("renderer", "error", f"Renderer timed out after 15 seconds (requested backend {backend})")
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            add("renderer", "error", f"Renderer probe failed: {exc}; run uv sync --extra simulation")

    add("hardware", "info", "Physical hardware has not been assessed; simulation setup does not qualify a rover")
    return {"schema_version": 1, "checks": checks,
            "ready": all(check["status"] not in {"missing", "error"} for check in checks)}
