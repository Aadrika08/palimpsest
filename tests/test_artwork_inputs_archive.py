"""The committed portable artwork input archive (user decision 4) admits under its manifest."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import verify_artwork_handoff

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'docs/reports/artwork-portability-preparation-evidence/palimpsest-artwork-inputs-v1.zip'
MANIFEST = ROOT / 'docs/artwork-handoff.json'


class PortableInputs(unittest.TestCase):
    def test_archive_is_the_reported_deterministic_package(self):
        self.assertEqual(hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
                         '35ff2f665e52d1a0cce9aa90af2874b0fed2c6a801fafc7046144483a45dac4d')
        self.assertEqual(hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                         '9766f285b7f4008f894845cc12d51e34a14dafc5eaf88fba6e13bdec36944982')
        with zipfile.ZipFile(ARCHIVE) as archive:
            infos = archive.infolist()
            self.assertEqual([info.filename for info in infos], sorted(info.filename for info in infos))
            self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED and info.date_time == (1980, 1, 1, 0, 0, 0)
                                for info in infos))

    def test_extracted_inputs_pass_the_existing_handoff_admission(self):
        manifest = json.loads(MANIFEST.read_text())
        with tempfile.TemporaryDirectory() as directory, zipfile.ZipFile(ARCHIVE) as archive:
            archive.extractall(directory)
            admitted = verify_artwork_handoff.admit(Path(directory), manifest)
        self.assertEqual(len(admitted), 19)
        self.assertEqual(sum(row['size_bytes'] for row in admitted.values()), manifest['source_bytes'])


if __name__ == '__main__':
    unittest.main()
