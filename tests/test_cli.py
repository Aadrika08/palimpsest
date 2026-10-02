import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
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
