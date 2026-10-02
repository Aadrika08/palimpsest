"""A delayed output close failure must not publish a partial derivative."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from palimpsest import artifacts, comparison, sonification
import test_artifacts
import test_sonification


class ExportCloseChecks(unittest.TestCase):
    def test_deferred_close_failure_removes_only_new_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            self.root = Path(folder)
            left = test_artifacts.ArtifactTests.run_fixture(self)
            right = test_artifacts.ArtifactTests.run_fixture(self)
            neural = test_sonification.SonificationTests.fixture(self)
            operations = [(suffix, lambda path, kind=kind: artifacts.export_run(left, path, kind))
                          for suffix, kind in (('svg', 'svg'), ('png', 'png'), ('zip', 'bundle'))]
            operations += [('html', lambda path: comparison.export_comparison(left, right, path)),
                           ('wav', lambda path: sonification.sonify(neural, path, populations=['visual_left']))]
            original_open = Path.open
            class CloseFailure:
                def __init__(self, stream): self.stream = stream
                def __getattr__(self, name): return getattr(self.stream, name)
                def __enter__(self): return self
                def __exit__(self, *args):
                    self.stream.close()
                    raise OSError('deferred close failure')
            for suffix, export in operations:
                with self.subTest(format=suffix):
                    output = self.root / ('new.' + suffix)
                    def opened(path, *args, **kwargs):
                        stream = original_open(path, *args, **kwargs)
                        return CloseFailure(stream) if path == output else stream
                    with patch.object(Path, 'open', opened), self.assertRaisesRegex(OSError, 'deferred close'):
                        export(output)
                    self.assertFalse(output.exists(), 'partial output survived failed close')
                    output.write_bytes(b'existing artifact')
                    with self.assertRaises(FileExistsError): export(output)
                    self.assertEqual(output.read_bytes(), b'existing artifact')


if __name__ == '__main__':
    unittest.main()
