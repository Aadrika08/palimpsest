import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from palimpsest.cli import main


class CliTests(unittest.TestCase):
    def test_doctor_dispatches_without_loading_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = io.StringIO()
            with patch('palimpsest.doctor.diagnose', return_value={'ready': True}) as diagnose:
                with contextlib.redirect_stdout(output):
                    code = main(['--repo', str(root), 'doctor', '--probe-renderer'])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue()), {'ready': True})
            diagnose.assert_called_once_with(root, root / 'data/assets/flynn', True)

    def test_missing_assets_is_nonzero(self):
        with patch('palimpsest.assets.verify_assets', return_value={'ok': False}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['assets', 'verify']), 1)

    def test_rejects_unbounded_evaluation_before_launch(self):
        for args in (['--episodes', '0'], ['--max-steps', '601'], ['--timeout', '0']):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(['evaluate', '--controller', 'teacher', *args])
                self.assertEqual(error.exception.code, 2)

    def test_replay_requires_new_uuid_and_successful_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('palimpsest.evaluate.bounded_process', return_value={'status': 'completed'}) as launch:
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(['replay', str(root / 'source'), '--mode', 'actions',
                                           '--output', str(root / 'not-a-uuid')]), 1)
                launch.assert_not_called()
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(['replay', str(root / 'source'), '--mode', 'policy',
                                           '--output', str(root / uuid.uuid4().hex)]), 1)
                # A child exit alone cannot establish replay agreement.
                self.assertEqual(launch.call_count, 1)

    def test_storage_flag_bounds_reject_before_dispatch(self):
        cases = [("--storage-max-bytes", "1048575"), ("--min-free-bytes", "-1"),
                 ("--max-runs", "0"), ("--max-snapshots", "4097"), ("--max-exports", "0"),
                 ("--log-max-bytes", "1023")]
        for flag, value in cases:
            with self.subTest(flag=flag), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(["evaluate", "--controller", "teacher", flag, value])
                self.assertEqual(error.exception.code, 2)

    def test_export_asset_overlap_and_lock_rejected_before_write(self):
        from palimpsest.storage import StorageBudget, StorageLimits
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            with patch("palimpsest.artifacts.export_run") as export:
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["--assets", str(assets), "export", str(root / "source"),
                                           "--format", "svg", "--output", str(root / "report.svg")]), 1)
                export.assert_not_called()
                output = root / "exports/report.svg"
                with StorageBudget((output.parent,), StorageLimits(min_free_bytes=0)).lock():
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(main(["--assets", str(assets), "export", str(root / "source"),
                                               "--format", "svg", "--output", str(output)]), 1)
                export.assert_not_called()

    def test_export_counts_custom_artifacts_and_passes_live_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "exports/report.svg"
            output.parent.mkdir()
            (output.parent / "my-custom-image.png").write_bytes(b"previous")
            with patch("palimpsest.artifacts.export_run", return_value=output) as export:
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["--assets", str(root / "assets"), "export", str(root / "source"),
                                           "--format", "svg", "--output", str(output), "--max-exports", "1"]), 1)
                export.assert_not_called()
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["--assets", str(root / "assets"), "export", str(root / "source"),
                                           "--format", "svg", "--output", str(output), "--min-free-bytes", "0"]), 0)
                self.assertIn("storage_budget", export.call_args.kwargs)
                self.assertEqual(export.call_args.kwargs["storage_budget"].roots, (output.parent,))

    def test_replay_storage_config_holds_lease_and_counts_existing_runs(self):
        from palimpsest.storage import StorageLimitError
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "runs" / uuid.uuid4().hex
            def launch(command, destination, timeout, env, **kwargs):
                budget = kwargs["storage_budget"]
                self.assertEqual(kwargs["log_max_bytes"], 2048)
                self.assertEqual(budget.headroom_bytes, 4096 + 8 * 1024**2)
                config = json.loads(command[-1])
                self.assertEqual(config["storage"]["roots"], [str(output.parent)])
                self.assertEqual(config["storage"]["limits"]["max_runs"], 1)
                with self.assertRaises(StorageLimitError):
                    with budget.lock():
                        pass
                return {"status": "completed"}
            argv = ["--assets", str(root / "assets"), "replay", str(root / "source"), "--mode", "actions",
                    "--output", str(output), "--log-max-bytes", "2048", "--max-runs", "1", "--min-free-bytes", "0"]
            with patch("palimpsest.evaluate.bounded_process", side_effect=launch) as process:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(argv), 1)  # Exit status is not a replay proof.
                process.assert_called_once()
                (output.parent / uuid.uuid4().hex).mkdir()
                process.reset_mock()
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(argv), 1)
                process.assert_not_called()

    def test_evaluation_receives_storage_flags_without_runtime_substitution(self):
        with patch("palimpsest.evaluate.evaluate", return_value={"status": "completed"}) as evaluate:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["evaluate", "--controller", "teacher", "--storage-max-bytes", "1048576",
                                       "--min-free-bytes", "0", "--max-snapshots", "1", "--log-max-bytes", "2048"]), 0)
            args = evaluate.call_args.args[2]
            self.assertEqual((args.storage_max_bytes, args.min_free_bytes, args.max_snapshots, args.log_max_bytes),
                             (1048576, 0, 1, 2048))

    def test_lab_requires_built_ui_and_binds_only_loopback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('palimpsest.lab.create_app') as create, patch('uvicorn.run') as run:
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(['--repo', str(root), 'lab']), 1)
                create.assert_not_called()
                (root / 'ui/dist').mkdir(parents=True)
                (root / 'ui/dist/index.html').write_text('<!doctype html>')
                self.assertEqual(main(['--repo', str(root), 'lab', '--port', '8766']), 0)
                self.assertEqual(run.call_args.kwargs['host'], '127.0.0.1')
                self.assertEqual(run.call_args.kwargs['port'], 8766)
