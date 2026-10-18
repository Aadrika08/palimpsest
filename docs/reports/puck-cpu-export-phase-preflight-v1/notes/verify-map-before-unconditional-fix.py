"""Verify this portable source map; never import a vendor or execute a study."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--originals', action='store_true')
    parser.add_argument('--git-revision')
    args = parser.parse_args()
    packet = Path(__file__).resolve().parent
    repo = packet.parents[2]
    index = json.loads((packet / 'evidence-index.json').read_text())
    artifacts = index['artifacts']
    names = [row['archived_path'] for row in artifacts]
    assert len(names) == len(set(names))
    assert set(names) == {
        str(path.relative_to(packet)) for path in packet.rglob('*')
        if path.is_file() and path.name != 'evidence-index.json'
    }
    for row in artifacts:
        name = row['archived_path']
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        raw = (packet / name).read_bytes()
        assert len(raw) == row['size_bytes'] and digest(raw) == row['sha256'], name
        if args.originals:
            assert raw == Path(row['original_path']).read_bytes(), name
        if args.git_revision:
            relative = str((packet / name).relative_to(repo))
            blob = subprocess.check_output(
                ['git', 'show', f'{args.git_revision}:{relative}'], cwd=repo)
            assert raw == blob, name

    sources = json.loads((packet / 'source-index.json').read_text())
    assert sources['commit'] == '0fabc3ba44823f257e70ce397d989c8de5e362c1'
    for row in sources['upstream_files']:
        raw = (packet / row['archived_path']).read_bytes()
        assert len(raw) == row['size_bytes'] and digest(raw) == row['sha256']
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw)
        assert blob.hexdigest() == row['git_blob_sha1'], row['path']
    for row in sources['installed_files']:
        raw = (packet / row['archived_path']).read_bytes()
        assert len(raw) == row['size_bytes'] and digest(raw) == row['sha256']

    result = json.loads((packet / 'source-map.json').read_text())
    candidate = (packet / 'candidate-unchanged.json').read_bytes()
    assert digest(candidate) == result['candidate']['sha256']
    assert digest(candidate) == 'ddc770acca34f849b2234db155ea477438560e3e4a58685a2c11632c44e93648'
    declarations = {
        row['name']: row for row in json.loads(candidate)['import_profile']['exports']
        if row['phase'] == 'native_create'
    }
    rows = result['rows']
    assert len(rows) == len({row['name'] for row in rows}) == 35
    assert {row['name'] for row in rows} == set(declarations)
    expected = {'source-supported': 32, 'correction required': 3, 'unresolved': 0}
    assert result['classification_counts'] == expected
    assert Counter(row['classification'] for row in rows) == {
        key: value for key, value in expected.items() if value
    }
    assert {row['name'] for row in rows if row['classification'] == 'correction required'} == {
        'torch._C._distributed_autograd', 'torch._C._distributed_c10d',
        'torch._C._distributed_rpc',
    }
    for row in rows:
        assert row['current_declaration'] == declarations[row['name']]
        assert row['raw_attributes'] and row['build_dispatch_assumptions']
        assert row['closure_scope'] and row['dispatch_contract']
        for evidence in row['evidence']:
            path = evidence['path']
            source = packet / path if path.startswith('installed-source/') else packet / 'upstream' / path
            assert 1 <= evidence['line_start'] <= evidence['line_end'] <= len(source.read_text().splitlines()), path
    assert len(result['unresolved_groups']) == 1
    acceptance = result['acceptance']
    assert acceptance['source_sweep_complete'] is True
    assert acceptance['qualification_claims'] == []
    assert all(value is False for key, value in acceptance.items()
               if key not in {'source_sweep_complete', 'qualification_claims'})
    proposal = packet / 'prospective-observation.md'
    assert proposal.read_bytes() == (repo / result['unresolved_groups'][0]['next_proposal']).read_bytes()
    print(json.dumps({
        'artifacts': len(artifacts), 'bytes': sum(row['size_bytes'] for row in artifacts),
        'upstream_files': len(sources['upstream_files']),
        'selected_installed_files': len(sources['installed_files']),
        'rows': len(rows), 'classification_counts': expected,
        'originals_checked': args.originals, 'git_revision_checked': args.git_revision,
        'runtime_qualified': False,
    }, sort_keys=True))


if __name__ == '__main__':
    main()
