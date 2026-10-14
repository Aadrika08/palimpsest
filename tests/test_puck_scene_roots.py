"""Root custody on authored tempfile forests; no project/root payload scans."""
import hashlib
import importlib
import importlib.util
import json
import os
import stat
import time

import pytest

NAME = 'palimpsest.puck_scene_roots'


def module():
    assert importlib.util.find_spec(NAME), 'Bounded held root discovery is missing'
    return importlib.import_module(NAME)


def contract(root, opaque=()):
    return json.dumps({'id': 'puck-scene-root-search-v1', 'version': 1,
                      'search_roots': [str(root)], 'opaque_subtrees': list(opaque)},
                      sort_keys=True, separators=(',', ':')).encode()


def held(root, opaque=(), raw=None, **kwargs):
    raw = contract(root, opaque) if raw is None else raw
    return module().HeldSceneInventoryRoots(raw,
        expected_sha256=kwargs.pop('expected_sha256', hashlib.sha256(raw).hexdigest()),
        deadline=kwargs.pop('deadline', time.monotonic() + 30), **kwargs)


def test_nested_repositories_gitfile_and_retained_hints_are_metadata_only(tmp_path, monkeypatch):
    root = tmp_path / 'forest'; root.mkdir()
    repo = root / 'repo'; repo.mkdir(); (repo / '.git').mkdir()
    (repo / '.git' / 'do-not-descend').symlink_to('/authored-nonexistent')
    nested = repo / 'independent'; nested.mkdir(); (nested / '.git').mkdir()
    linked = root / 'linked'; linked.mkdir(); (linked / '.git').write_bytes(b'gitdir: absent\n')
    for name in ('runs', 'registry', 'registries', 'evidence', 'authored-evidence'):
        (root / name).mkdir()
    manifests = root / 'package'; manifests.mkdir()
    for name in ('manifest.json', 'registry.json', 'reservation.json', 'index.json',
                 'authored-manifest.json', 'authored-registry.json'):
        (manifests / name).write_bytes(b'not parsed JSON')
    os.link(manifests / 'manifest.json', root / 'hardlink')
    m = module(); original_open = os.open

    def directory_only(path, flags, *args, **kwargs):
        assert flags & os.O_DIRECTORY, 'inventory opened a leaf payload'
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(m.os, 'open', directory_only)
    with held(root) as inventory:
        receipt = inventory.snapshot()
        assert {(r['path'], r['marker_kind']) for r in receipt['repository_candidates']} == {
            (str(repo), 'directory'), (str(nested), 'directory'), (str(linked), 'regular_file')}
        candidates = {r['path']: r['hints'] for r in receipt['retained_root_candidates']}
        assert set(candidates) == {str(root / n) for n in
            ('runs', 'registry', 'registries', 'evidence', 'authored-evidence', 'package')}
        assert 'manifest.json' in candidates[str(manifests)]
        assert len(receipt['git_control_storage']) == 3
        assert all(r['contents_authenticated'] is False for r in receipt['git_control_storage'])
        assert not any('/.git/' in r['path'] for r in receipt['observed_directories'])
        for key in ('inventory_complete', 'all_repositories_discovered', 'retained_roots_discovered',
                    'executable', 'native_authorized', 'collection_authorized'):
            assert receipt[key] is False
        assert receipt['qualification_claims'] == []
        assert receipt['payload_reads'] == 0
        assert receipt['declared_scope_namespace_stable'] is True
        assert receipt['contract_sha256'] == hashlib.sha256(contract(root)).hexdigest()
        receipt['repository_candidates'].clear()
        assert len(inventory.snapshot()['repository_candidates']) == 3
        inventory.recheck()
    for operation in (inventory.snapshot, inventory.recheck, inventory.__enter__):
        with pytest.raises(RuntimeError): operation()


def test_explicit_opaque_contents_unobserved_and_no_implicit_exclusions(tmp_path):
    root = tmp_path / 'forest'; root.mkdir()
    opaque = root / 'opaque'; opaque.mkdir(); (opaque / 'link').symlink_to('missing')
    (root / 'node_modules').mkdir(); (root / 'node_modules' / 'runs').mkdir()
    exclusions = [{'path': str(opaque), 'reason': 'Authored payload deliberately excluded'}]
    with held(root, exclusions) as inventory:
        receipt = inventory.snapshot()
        assert receipt['excluded_scope'] == [dict(exclusions[0], contents_authenticated=False)]
        assert str(root / 'node_modules' / 'runs') in {
            r['path'] for r in receipt['retained_root_candidates']}
        (opaque / 'new').write_bytes(b'not observed')
        (opaque / 'link').unlink()
        inventory.recheck()
        assert not any(r['path'] == str(opaque) for r in receipt['observed_directories'])


@pytest.mark.parametrize('mutation', ['add', 'remove', 'replace', 'rename', 'leaf-edit', 'mode'])
@pytest.mark.parametrize('check', ['snapshot', 'recheck', 'close'])
def test_namespace_drift_fails_and_poison_closes_descriptors(tmp_path, monkeypatch, mutation, check):
    root = tmp_path / 'forest'; root.mkdir(); child = root / 'child'; child.mkdir()
    leaf = child / 'leaf'; leaf.write_bytes(b'authored')
    m = module(); opened = []; original = os.open

    def remember(*args, **kwargs):
        fd = original(*args, **kwargs); opened.append(fd); return fd

    monkeypatch.setattr(m.os, 'open', remember)
    inventory = held(root)
    with pytest.raises((RuntimeError, OSError)):
        with inventory:
            if mutation == 'add': (child / 'new').write_bytes(b'new')
            elif mutation == 'remove': leaf.unlink()
            elif mutation == 'replace':
                other = child / 'replacement'; other.write_bytes(b'authored'); other.replace(leaf)
            elif mutation == 'rename': child.rename(root / 'renamed')
            elif mutation == 'leaf-edit': leaf.write_bytes(b'edited')
            elif mutation == 'mode': leaf.chmod(0o600)
            if check != 'close': getattr(inventory, check)()
    for fd in opened:
        with pytest.raises(OSError): os.fstat(fd)
    for operation in (inventory.snapshot, inventory.recheck, inventory.__enter__):
        with pytest.raises(RuntimeError): operation()


def test_body_exception_remains_primary_with_drift_note(tmp_path):
    (tmp_path / 'leaf').write_bytes(b'authored')
    error = LookupError('authored body failure'); inventory = held(tmp_path)
    with pytest.raises(LookupError) as caught:
        with inventory:
            (tmp_path / 'new').write_bytes(b'drift')
            raise error
    assert caught.value is error
    assert any('drift' in note.lower() or 'changed' in note.lower()
               for note in caught.value.__notes__)
    with pytest.raises(RuntimeError): inventory.snapshot()


@pytest.mark.parametrize('kind', ['symlink', 'git-symlink', 'fifo', 'directory-alias'])
def test_nonregular_or_symlink_entries_fail_closed(tmp_path, kind):
    if kind in ('symlink', 'git-symlink', 'directory-alias'):
        target = tmp_path / 'target'; target.mkdir()
        (tmp_path / ('.git' if kind == 'git-symlink' else 'alias')).symlink_to(target)
    else: os.mkfifo(tmp_path / 'fifo')
    with pytest.raises((ValueError, OSError)):
        with held(tmp_path): pass


@pytest.mark.parametrize('kind', ['missing', 'root-itself', 'outside', 'overlap', 'duplicate',
                                 'symlink', 'bad-reason', 'unknown-key'])
def test_opaque_contract_paths_require_exact_existing_unambiguous_directories(tmp_path, kind):
    root = tmp_path / 'root'; root.mkdir(); opaque = root / 'opaque'; opaque.mkdir()
    sub = opaque / 'nested'; sub.mkdir(); outside = tmp_path / 'outside'; outside.mkdir()
    rows = [{'path': str(opaque), 'reason': 'authored exclusion'}]
    if kind == 'missing': rows[0]['path'] = str(root / 'missing')
    elif kind == 'root-itself': rows[0]['path'] = str(root)
    elif kind == 'outside': rows[0]['path'] = str(outside)
    elif kind == 'overlap': rows.append({'path': str(sub), 'reason': 'nested'})
    elif kind == 'duplicate': rows.append(dict(rows[0]))
    elif kind == 'symlink':
        link = root / 'alias'; link.symlink_to(opaque); rows[0]['path'] = str(link)
    elif kind == 'bad-reason': rows[0]['reason'] = ' '
    elif kind == 'unknown-key': rows[0]['extra'] = True
    with pytest.raises((ValueError, OSError)):
        with held(root, rows): pass


@pytest.mark.parametrize('kind', ['unknown', 'duplicate-key', 'nonfinite', 'wrong-id', 'bool-version',
                                 'noncanonical-json', 'noncanonical-path', 'relative', 'overlap',
                                 'duplicate-root', 'no-roots', 'too-many-roots', 'too-many-opaque',
                                 'too-large', 'not-bytes', 'bad-hash', 'hash-mismatch'])
def test_strict_external_contract_rejects_ambiguity(tmp_path, kind):
    document = json.loads(contract(tmp_path)); digest = None
    if kind == 'unknown': document['extra'] = True
    elif kind == 'wrong-id': document['id'] = 'other'
    elif kind == 'bool-version': document['version'] = True
    elif kind == 'noncanonical-path': document['search_roots'] = [str(tmp_path) + '/']
    elif kind == 'relative': document['search_roots'] = ['relative']
    elif kind == 'overlap': document['search_roots'] += [str(tmp_path / 'nested')]
    elif kind == 'duplicate-root': document['search_roots'] *= 2
    elif kind == 'no-roots': document['search_roots'] = []
    elif kind == 'too-many-roots': document['search_roots'] = [str(tmp_path / str(i)) for i in range(33)]
    elif kind == 'too-many-opaque': document['opaque_subtrees'] = [
        {'path': str(tmp_path / str(i)), 'reason': 'bounded'} for i in range(1025)]
    raw = json.dumps(document, sort_keys=True, separators=(',', ':')).encode()
    if kind == 'duplicate-key': raw = raw.replace(b'"version":1', b'"version":1,"version":1')
    elif kind == 'nonfinite': raw = raw.replace(b'"version":1', b'"version":NaN')
    elif kind == 'noncanonical-json': raw += b'\n'
    elif kind == 'too-large': raw = b' ' * 65537
    elif kind == 'not-bytes': raw = raw.decode()
    elif kind == 'bad-hash': digest = 'A' * 64
    elif kind == 'hash-mismatch': digest = '0' * 64
    if digest is None: digest = hashlib.sha256(raw if isinstance(raw, bytes) else raw.encode()).hexdigest()
    with pytest.raises(ValueError):
        module().HeldSceneInventoryRoots(raw, expected_sha256=digest, deadline=time.monotonic() + 30)


@pytest.mark.parametrize('deadline', [True, float('inf'), float('nan'), -1])
def test_invalid_deadlines_refuse(tmp_path, deadline):
    with pytest.raises((ValueError, TimeoutError)): held(tmp_path, deadline=deadline)


def test_deadline_extension_refuses(tmp_path):
    with pytest.raises(ValueError): held(tmp_path, deadline=time.monotonic() + 601)


@pytest.mark.parametrize('cap', ['MAX_DEPTH', 'MAX_DIRECTORIES', 'MAX_ENTRIES', 'MAX_METADATA_BYTES'])
def test_fixed_work_bounds_fail_closed(tmp_path, monkeypatch, cap):
    child = tmp_path / 'child'; child.mkdir(); (child / 'leaf').write_bytes(b'authored')
    m = module(); monkeypatch.setattr(m, cap, 0)
    with pytest.raises(ValueError):
        with held(tmp_path): pass


def test_real_depth_limit_refuses_depth_33(tmp_path):
    current = tmp_path
    for i in range(33): current = current / str(i); current.mkdir()
    with pytest.raises(ValueError):
        with held(tmp_path): pass


def test_expiry_during_entry_scan_and_recheck_closes(tmp_path, monkeypatch):
    (tmp_path / 'leaf').write_bytes(b'authored')
    m = module(); inventory = held(tmp_path); original = m.time.monotonic
    with inventory:
        monkeypatch.setattr(m.time, 'monotonic', lambda: original() + 1000)
        with pytest.raises(TimeoutError): inventory.recheck()
        with pytest.raises(RuntimeError): inventory.snapshot()


def test_opaque_directory_replacement_fails_despite_unobserved_contents(tmp_path):
    opaque = tmp_path / 'opaque'; opaque.mkdir()
    with pytest.raises(RuntimeError):
        with held(tmp_path, [{'path': str(opaque), 'reason': 'authored'}]) as inventory:
            opaque.rename(tmp_path / 'moved'); opaque.mkdir()
            inventory.recheck()


def test_constructor_and_failed_entry_close_all_owned_descriptors(tmp_path, monkeypatch):
    child = tmp_path / 'child'; child.mkdir(); os.mkfifo(child / 'fifo')
    m = module(); opened = []; original = m.os.open

    def remember(*args, **kwargs):
        fd = original(*args, **kwargs); opened.append(fd); return fd

    monkeypatch.setattr(m.os, 'open', remember)
    inventory = held(tmp_path)
    assert opened == []
    with pytest.raises(ValueError): inventory.__enter__()
    assert opened
    for fd in opened:
        with pytest.raises(OSError): os.fstat(fd)
    with pytest.raises(RuntimeError): inventory.__enter__()
