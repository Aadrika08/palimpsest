"""Ordinary verification: only the explicitly named source/config below."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import sys

NAMES = (
    'scripts/memory_source_runtime_closure_v1.py',
    'scripts/memory_family_source_runtime_v2.py',
    'scripts/qualify_memory_family_source_v2.py',
    'tests/test_memory_source_runtime_closure_v1.py',
    'tests/test_memory_family_source_runtime_v2.py',
    'tests/test_memory_family_source_qualification_v2.py',
    'tests/test_memory_source_cpu_limits.py',
    'tests/test_memory_family_source_seal_v2.py',
    'scripts/run_tests.sh',
    'scripts/memory_family_source_seal_v2.py',
    'scripts/memory_family_numeric_preservation_v2.py',
    'scripts/memory_directory_census_v1.py',
    'scripts/memory_family_allocation_v3.py',
    'scripts/memory_family_raw_audit_v4.py',
    'src/palimpsest/puck_execution_files.py',
    'src/palimpsest/puck_retained_installation.py',
    'paper/studies/change_audit_v1/process.py',
    'pyproject.toml', 'uv.lock',
    'docs/plans/memory-family-numeric-compact-v2-protocol.json',
    'docs/plans/memory-family-compact-evidence-v4-case-publication-v1-protocol.json',
)
rows = {}
for name in NAMES:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 4*1024*1024:
            raise ValueError(f'Unexpected named source/config type or size: {name}')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        identity = lambda s: (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
        if identity(before) != identity(os.fstat(fd)) or identity(before) != identity(Path(name).lstat()):
            raise ValueError(f'Named source/config changed while hashing: {name}')
        rows[name] = {'size_bytes': before.st_size, 'sha256': digest}
    finally:
        os.close(fd)
value = {'schema': 'named-source-config-continuity-v1',
    'scope': 'Only 21 explicitly named source/config files; no model/data or installed runtime inventory.',
    'head': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(), 'files': rows}
Path(sys.argv[1]).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(f'Snapshotted {len(rows)} explicitly named source/config files.')
