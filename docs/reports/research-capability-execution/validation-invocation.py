"""Run regression checks with a private in-process user-cache fixture.

The sandbox makes the real user's ~/.cache read-only. Keep HOME untouched and
exercise real cache/lease operations under an owned temporary Path.home fixture.
No production sources, validation predicates, or source hashes are patched.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

def main():
    # Match ``python -m pytest`` discovery for a harness living in /tmp.
    sys.path.insert(0, str(Path.cwd()))
    with tempfile.TemporaryDirectory(prefix='palimpsest-check-user-') as directory:
        task_user_fixture = Path(directory)
        print('Verification cache fixture: owned temporary Path.home; HOME unchanged', flush=True)
        with patch('pathlib.Path.home', return_value=task_user_fixture):
            return pytest.main(sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
