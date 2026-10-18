"""Verify one archived evidence packet; never invokes a runtime allocation.

Does what each packet's archived ``verify_evidence.py`` does (exact archived file
set, sizes and SHA-256s; optional original paths; optional committed copies at a
git revision; every ``source_paths`` copy equals the file at ``source_commit``),
but resolves a source path inside a submodule (``upstream/fly-gym/*``) through
the gitlink recorded at the source commit, which ``git show`` cannot read from
the superproject.

    python scripts/verify_evidence_packet.py docs/reports/puck-cpu-held-episode-16
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def fail(message):
    raise SystemExit('Evidence packet refused: ' + message)


def git(repo, *args):
    result = subprocess.run(['git', *args], cwd=repo, capture_output=True, timeout=120)
    if result.returncode != 0:
        fail('git ' + ' '.join(args) + ' failed: ' + result.stderr.decode('utf-8', 'replace').strip())
    return result.stdout


def gitlinks(repo, commit):
    """Submodule paths at commit mapped to their recorded commits."""
    links = {}
    for line in git(repo, 'ls-tree', '-r', '-z', commit).split(b'\0'):
        if line.startswith(b'160000 commit '):
            meta, path = line.split(b'\t', 1)
            links[path.decode()] = meta.split()[2].decode()
    return links


def blob(repo, commit, path, links):
    """The file bytes at commit, reading through the submodule gitlink when the path is inside one."""
    for prefix, linked in links.items():
        if path.startswith(prefix + '/'):
            return git(repo / prefix, 'show', linked + ':' + path[len(prefix) + 1:]), True
    return git(repo, 'show', commit + ':' + path), False


def safe(name):
    path = PurePosixPath(name)
    if type(name) is not str or path.is_absolute() or '..' in path.parts or not name:
        fail('Unsafe archived path: ' + repr(name))
    return name


def verify(packet, repo, *, originals=False, git_revision=None):
    packet, repo = Path(packet).resolve(), Path(repo).resolve()
    index = json.loads((packet / 'evidence-index.json').read_bytes())
    names = [safe(row['archived_path']) for row in index['artifacts']]
    if len(names) != len(set(names)) or len(names) != index['artifact_count']:
        fail('Artifact count or uniqueness differs')
    present = {path.relative_to(packet).as_posix() for path in packet.rglob('*')
               if path.is_file() and path != packet / 'evidence-index.json'}
    if set(names) != present:
        fail('Archived file set differs: ' + ', '.join(sorted(set(names) ^ present)[:8]))
    for row in index['artifacts']:
        raw = (packet / row['archived_path']).read_bytes()
        if len(raw) != row['size_bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            fail('Archived artifact bytes differ: ' + row['archived_path'])
        if originals and raw != Path(row['original_path']).read_bytes():
            fail('Original differs: ' + row['original_path'])
    if git_revision:
        for name in [*names, 'evidence-index.json']:
            relative = (packet / name).relative_to(repo).as_posix()
            if git(repo, 'show', git_revision + ':' + relative) != (packet / name).read_bytes():
                fail('Committed copy differs at ' + git_revision + ': ' + relative)
    commit = index['source_commit'];links = gitlinks(repo, commit);submodule = 0
    for name in index['source_paths']:
        raw, inside = blob(repo, commit, safe(name), links)
        submodule += inside
        if raw != (packet / 'source' / name).read_bytes():
            fail('Source copy differs from ' + commit + ': ' + name)
    return dict(artifacts=len(names), bytes=sum(row['size_bytes'] for row in index['artifacts']),
                empty_files=sum(row['size_bytes'] == 0 for row in index['artifacts']),
                originals_checked=originals, git_revision_checked=git_revision, source_commit=commit,
                source_paths=len(index['source_paths']), submodule_source_paths=submodule, runtime_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('packet')
    parser.add_argument('--repo', default=str(ROOT))
    parser.add_argument('--originals', action='store_true')
    parser.add_argument('--git-revision')
    args = parser.parse_args()
    summary = verify(args.packet, args.repo, originals=args.originals, git_revision=args.git_revision)
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    sys.exit(main())
