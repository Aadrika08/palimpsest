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
