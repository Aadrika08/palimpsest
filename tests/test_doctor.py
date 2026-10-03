import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from palimpsest.doctor import diagnose, UPSTREAM_PIN


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / "missing" / "assets"
        self.metadata = patch("palimpsest.doctor.metadata.version", return_value="1.0")
        self.metadata.start()
        self.addCleanup(self.metadata.stop)

    def run_command(self, args, **kwargs):
        if args[0] == "git":
            if "--show-toplevel" in args:
                output = str(self.root / "upstream" / "fly-gym") + "\n"
            else:
                output = UPSTREAM_PIN + "\n" if "rev-parse" in args else ""
        elif args[0] == "nvidia-smi":
            output = "NVIDIA RTX 4050, 580.0, 6144, 4096\n"
        elif args[0] == sys.executable:
            output = json.dumps({"backend": "egl", "version": "3.3.6", "device": "GPU", "shape": [32, 32, 3]})
        else:
            output = "Linux\n"
        return subprocess.CompletedProcess(args, 0, output, "")

    def report(self, **kwargs):
        with patch("palimpsest.doctor.subprocess.run", side_effect=self.run_command):
            return diagnose(self.root, self.assets, **kwargs)

    def check(self, report, name):
        return next(check for check in report["checks"] if check["name"] == name)

    def test_schema_and_missing_assets_are_explicit(self):
        report = self.report()
        self.assertEqual(report["schema_version"], 1)
        self.assertIs(report["ready"], False)
        self.assertTrue(report["checks"])
        for check in report["checks"]:
            self.assertEqual(set(check), {"name", "status", "detail"})
            self.assertIn(check["status"], {"ok", "missing", "error", "info"})
        self.assertIn("palimpsest assets fetch", str(self.check(report, "assets")["detail"]))
        json.dumps(report)

    def test_dependencies_use_metadata_and_show_setup(self):
        with patch("palimpsest.doctor.metadata.version", side_effect=importlib.metadata.PackageNotFoundError("torch")):
            report = self.report()
        check = self.check(report, "dependency:torch")
        self.assertEqual(check["status"], "missing")
        self.assertIn("uv sync --extra simulation", check["detail"])

    def test_module_import_does_not_import_simulation_dependencies(self):
        result = subprocess.run([sys.executable, "-c",
            "import sys; import palimpsest.doctor; "
            "assert not ({'torch', 'numpy', 'mujoco', 'gymnasium', 'OpenGL'} & set(sys.modules))"],
            capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_upstream_pin_and_dirty_state(self):
        def commands(args, **kwargs):
            if args[0] == "git" and "status" in args:
                return subprocess.CompletedProcess(args, 0, " M core/model.py\n", "")
            return self.run_command(args, **kwargs)
        with patch("palimpsest.doctor.subprocess.run", side_effect=commands):
            report = diagnose(self.root, self.assets)
        check = self.check(report, "upstream")
        self.assertEqual(check["status"], "error")
        self.assertEqual(check["detail"]["commit"], UPSTREAM_PIN)
        self.assertTrue(check["detail"]["dirty"])

    def test_wrong_upstream_pin_fails(self):
        def commands(args, **kwargs):
            result = self.run_command(args, **kwargs)
            if args[0] == "git" and "HEAD" in args:
                result.stdout = "badpin\n"
            return result
        with patch("palimpsest.doctor.subprocess.run", side_effect=commands):
            report = diagnose(self.root, self.assets)
        self.assertEqual(self.check(report, "upstream")["status"], "error")

    def test_missing_git_and_gpu_commands_are_reported(self):
        with patch("palimpsest.doctor.subprocess.run", side_effect=FileNotFoundError("command unavailable")):
            report = diagnose(self.root, self.assets)
        self.assertEqual(self.check(report, "upstream")["status"], "missing")
        self.assertEqual(self.check(report, "gpu")["status"], "info")

    def test_gpu_timeout_is_nonfatal_and_bounded(self):
        def commands(args, **kwargs):
            self.assertGreater(kwargs["timeout"], 0)
            if args[0] == "nvidia-smi":
                raise subprocess.TimeoutExpired(args, kwargs["timeout"])
            return self.run_command(args, **kwargs)
        with patch("palimpsest.doctor.subprocess.run", side_effect=commands):
            report = diagnose(self.root, self.assets)
        self.assertEqual(self.check(report, "gpu")["status"], "info")
        self.assertIn("timed out", str(self.check(report, "gpu")["detail"]))

    def test_gpu_reports_device_and_vram(self):
        check = self.check(self.report(), "gpu")
        self.assertEqual(check["status"], "ok")
        self.assertEqual(check["detail"]["devices"][0]["memory_free_mib"], 4096)
        self.assertIn("4050", check["detail"]["devices"][0]["name"])

    def test_default_does_not_run_renderer(self):
        with patch("palimpsest.doctor.subprocess.run", side_effect=self.run_command) as run:
            report = diagnose(self.root, self.assets)
        self.assertEqual(self.check(report, "renderer")["status"], "info")
        self.assertFalse(any(call.args[0][0] == sys.executable for call in run.call_args_list))

    def test_git_parent_repository_is_rejected(self):
        def commands(args, **kwargs):
            result = self.run_command(args, **kwargs)
            if "--show-toplevel" in args:
                result.stdout = str(self.root)
            return result
        with patch("palimpsest.doctor.subprocess.run", side_effect=commands):
            report = diagnose(self.root, self.assets)
        self.assertEqual(self.check(report, "upstream")["status"], "error")
        self.assertIn("not an initialized submodule", self.check(report, "upstream")["detail"])

    def test_disk_reports_existing_parent_of_asset_root(self):
        check = self.check(self.report(), "disk")
        self.assertEqual(check["status"], "ok")
        self.assertEqual(check["detail"]["path"], str(self.root))
        self.assertGreater(check["detail"]["free_bytes"], 0)

    def test_disk_failure_is_not_reported_ready(self):
        with patch("palimpsest.doctor.shutil.disk_usage", side_effect=OSError("disk unavailable")):
            report = self.report()
        self.assertEqual(self.check(report, "disk")["status"], "error")
        self.assertFalse(report["ready"])

    def test_probe_sets_linux_default_in_child_only(self):
        before = dict(os.environ)
        with patch.dict(os.environ, {}, clear=True), patch("palimpsest.doctor.platform.system", return_value="Linux"):
            with patch("palimpsest.doctor.subprocess.run", side_effect=self.run_command) as run:
                report = diagnose(self.root, self.assets, probe_renderer=True)
            renderer_call = next(call for call in run.call_args_list if call.args[0][0] == sys.executable)
            self.assertEqual(renderer_call.kwargs["env"]["MUJOCO_GL"], "egl")
            self.assertNotIn("MUJOCO_GL", os.environ)
        self.assertEqual(dict(os.environ), before)
        check = self.check(report, "renderer")
        self.assertEqual(check["status"], "ok")
        self.assertEqual(check["detail"]["backend_selection"], "Linux default (MUJOCO_GL unset)")

    def test_renderer_timeout_is_an_error(self):
        def commands(args, **kwargs):
            if args[0] == sys.executable:
                raise subprocess.TimeoutExpired(args, kwargs["timeout"])
            return self.run_command(args, **kwargs)
        with patch("palimpsest.doctor.subprocess.run", side_effect=commands):
            report = diagnose(self.root, self.assets, probe_renderer=True)
        self.assertEqual(self.check(report, "renderer")["status"], "error")
        self.assertIn("timed out", str(self.check(report, "renderer")["detail"]))

    def test_renderer_missing_dependency_shows_setup(self):
        def commands(args, **kwargs):
            if args[0] == sys.executable:
                return subprocess.CompletedProcess(args, 1, "", "ModuleNotFoundError: No module named 'mujoco'")
            return self.run_command(args, **kwargs)
        with patch("palimpsest.doctor.subprocess.run", side_effect=commands):
            report = diagnose(self.root, self.assets, probe_renderer=True)
        self.assertIn("uv sync --extra simulation", str(self.check(report, "renderer")["detail"]))

    def test_probe_preserves_explicit_backend(self):
        with patch.dict(os.environ, {"MUJOCO_GL": "osmesa"}):
            with patch("palimpsest.doctor.subprocess.run", side_effect=self.run_command) as run:
                report = diagnose(self.root, self.assets, probe_renderer=True)
            call = next(call for call in run.call_args_list if call.args[0][0] == sys.executable)
            self.assertEqual(call.kwargs["env"]["MUJOCO_GL"], "osmesa")
            self.assertEqual(os.environ["MUJOCO_GL"], "osmesa")
        self.assertEqual(self.check(report, "renderer")["detail"]["backend_selection"], "explicit MUJOCO_GL")

    def test_renderer_invalid_output_is_not_success(self):
        def commands(args, **kwargs):
            if args[0] == sys.executable:
                return subprocess.CompletedProcess(args, 0, "[]", "")
            return self.run_command(args, **kwargs)
        with patch("palimpsest.doctor.subprocess.run", side_effect=commands):
            report = diagnose(self.root, self.assets, probe_renderer=True)
        self.assertEqual(self.check(report, "renderer")["status"], "error")


if __name__ == "__main__":
    unittest.main()
