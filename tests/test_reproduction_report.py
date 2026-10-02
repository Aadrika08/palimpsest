import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('reproduction_report',
    Path(__file__).resolve().parents[1] / 'scripts/verify_reproduction.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvidenceRoleTests(unittest.TestCase):
    def test_mislabeled_controller_or_failed_supervisor_cannot_be_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'recording').mkdir()
            manifest = {'status': 'completed', 'profile': 'privileged-teacher',
                        'configuration': {'controller': 'teacher'}, 'teacher_privileged': True}
            (path / 'recording/manifest.json').write_text(json.dumps(manifest))
            (path / 'supervisor.json').write_text(json.dumps({'status': 'completed', 'returncode': 0}))
            with self.assertRaisesRegex(ValueError, 'Wrong controller'):
                module.inspect(path, 'flynn')
            for status, code in (('timeout', -15), ('failed', 1), ('completed', 1)):
                with self.subTest(status=status, code=code):
                    (path / 'supervisor.json').write_text(json.dumps({'status': status, 'returncode': code}))
                    with self.assertRaisesRegex(ValueError, 'Worker did not complete'):
                        module.inspect(path, 'teacher')
