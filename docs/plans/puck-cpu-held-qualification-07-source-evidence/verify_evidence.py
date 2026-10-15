"""Verify authored publication evidence; never invoke a runtime allocation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--originals', action='store_true')
    parser.add_argument('--git-revision')
    args = parser.parse_args()
    packet = Path(__file__).resolve().parent
    repo = packet.parents[2]
    index = json.loads((packet / 'evidence-index.json').read_text())
    names = [row['archived_path'] for row in index['artifacts']]
    assert len(names) == len(set(names)) == index['artifact_count']
    assert set(names) == {str(path.relative_to(packet)) for path in packet.rglob('*')
                         if path.is_file() and path != packet / 'evidence-index.json'}
    for row in index['artifacts']:
        name = row['archived_path']
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        raw = (packet / name).read_bytes()
        assert len(raw) == row['size_bytes']
        assert hashlib.sha256(raw).hexdigest() == row['sha256'], name
        if args.originals:
            assert raw == Path(row['original_path']).read_bytes(), name
    if args.git_revision:
        for name in [*names, 'evidence-index.json']:
            relative = str((packet / name).relative_to(repo))
            blob = subprocess.check_output(['git', 'show', f'{args.git_revision}:{relative}'], cwd=repo)
            assert blob == (packet / name).read_bytes(), name
    for name in index['source_paths']:
        blob = subprocess.check_output(['git', 'show', f'{index["source_commit"]}:{name}'], cwd=repo)
        assert blob == (packet / 'source' / name).read_bytes(), name
    print(json.dumps(dict(artifacts=len(names), bytes=sum(row['size_bytes'] for row in index['artifacts']),
        empty_files=sum(row['size_bytes'] == 0 for row in index['artifacts']),
        originals_checked=args.originals, git_revision_checked=args.git_revision,
        source_commit=index['source_commit'], runtime_qualified=False), sort_keys=True))


if __name__ == '__main__':
    main()
