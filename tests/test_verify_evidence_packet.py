"""The shared evidence-packet verifier resolves submodule sources through the source commit's gitlink.

The archived per-packet verify_evidence.py runs ``git show <source_commit>:<path>``,
which cannot read upstream/fly-gym/* (a submodule gitlink in the superproject).
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'scripts/verify_evidence_packet.py'
PACKET = ROOT / 'docs/reports/puck-cpu-held-episode-16'
pytestmark = pytest.mark.skipif(not (ROOT / 'upstream/fly-gym/.git').exists(),
                                reason='requires the initialized upstream/fly-gym submodule')


def run(*args):
    return subprocess.run([sys.executable, '-I', '-B', str(TOOL), *map(str, args)],
                          capture_output=True, text=True, timeout=300)


def test_episode16_packet_verifies_including_submodule_sources():
    result = run(PACKET, '--repo', ROOT)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    index = json.loads((PACKET / 'evidence-index.json').read_bytes())
    assert summary['artifacts'] == index['artifact_count'] == 283
    assert summary['source_commit'] == index['source_commit']
    assert summary['source_paths'] == len(index['source_paths']) == 103
    assert summary['submodule_source_paths'] == 5 and summary['runtime_qualified'] is False


def copy(tmp_path):
    target = tmp_path / 'packet'
    shutil.copytree(PACKET, target)
    return target


def rehash(packet, archived):
    index = json.loads((packet / 'evidence-index.json').read_bytes())
    raw = (packet / archived).read_bytes()
    row = next(r for r in index['artifacts'] if r['archived_path'] == archived)
    row.update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    (packet / 'evidence-index.json').write_text(json.dumps(index))


@pytest.mark.parametrize('archived', ['source/upstream/fly-gym/core/astar.py', 'source/src/palimpsest/engine.py'])
def test_a_rehashed_but_changed_source_copy_is_refused(tmp_path, archived):
    packet = copy(tmp_path)
    (packet / archived).write_bytes((packet / archived).read_bytes() + b'\n# changed\n')
    rehash(packet, archived)
    result = run(packet, '--repo', ROOT)
    assert result.returncode != 0 and archived.removeprefix('source/') in result.stderr, result.stderr


def test_an_unindexed_or_changed_artifact_is_refused(tmp_path):
    packet = copy(tmp_path)
    (packet / 'stray.txt').write_text('x')
    assert 'Archived file set differs' in run(packet, '--repo', ROOT).stderr
    (packet / 'stray.txt').unlink()
    path = packet / 'source/pyproject.toml'
    path.write_bytes(path.read_bytes() + b'\n')
    result = run(packet, '--repo', ROOT)
    assert result.returncode != 0 and 'source/pyproject.toml' in result.stderr
