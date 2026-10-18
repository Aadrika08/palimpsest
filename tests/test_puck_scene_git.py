"""Actual Git discovery on authored temporary repositories; never project data."""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

NAME = 'palimpsest.puck_scene_git'


def module():
    assert importlib.util.find_spec(NAME), 'Bounded Git scene source discovery is missing'
    return importlib.import_module(NAME)


def git(repo, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
               GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
               GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
    return subprocess.run(['/usr/bin/git', '-C', str(repo), *args], env=env,
                          check=True, capture_output=True).stdout.decode().strip()


def fixture(tmp_path, object_format='sha1'):
    repo, remote = tmp_path / 'repo', tmp_path / 'remote.git'
    repo.mkdir(); remote.mkdir()
    git(repo, 'init', '-q', '--initial-branch=main', f'--object-format={object_format}')
    (repo / 'old.json').write_bytes(b'{"scene":"authored-old"}\n')
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'authored history')
    old = git(repo, 'rev-parse', 'HEAD')
    git(repo, 'branch', 'history', old)
    (repo / 'old.json').unlink()
    (repo / 'new.md').write_bytes(b'# Authored scene\n')
    (repo / 'ignored.txt').write_bytes(b'not a document')
    git(repo, 'add', '-A'); git(repo, 'commit', '-qm', 'authored current')
    git(repo, 'tag', '-a', 'authored-tag', '-m', 'authored tag')
    git(remote, 'init', '-q', '--bare', f'--object-format={object_format}')
    git(repo, 'remote', 'add', 'origin', str(remote))
    git(repo, 'push', '-q', '--all', 'origin'); git(repo, 'push', '-q', '--tags', 'origin')
    return repo, remote, old


def held(repo, remote, **kwargs):
    return module().HeldGitSceneSources(repo, remote='origin',
        expected_remote_url=str(remote), deadline=time.monotonic() + 30, **kwargs)


@pytest.mark.parametrize('object_format', ['sha1', 'sha256'])
def test_document_read_binds_historical_attachment_and_returns_detached_context(tmp_path, object_format):
    repo, remote, old = fixture(tmp_path, object_format)
    with held(repo, remote) as sources:
        descriptor = next(row for row in sources.snapshot()['documents'] if row['commit'] == old)
        view = sources.read_document(old, descriptor['path'], expected_oid=descriptor['oid'])
        raw = b'{"scene":"authored-old"}\n'
        assert view == {**descriptor, 'repo': str(repo), 'object_format': object_format,
                        'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'raw': raw}
        view['path'] = 'changed.json'
        view['raw'] = b'changed'
        assert sources.read_document(old, 'old.json', expected_oid=descriptor['oid'])['raw'] == raw
        assert sources.snapshot()['inventory_complete'] is False
    with pytest.raises(RuntimeError):
        sources.read_document(old, 'old.json', expected_oid=descriptor['oid'])


def test_document_context_keeps_same_path_history_and_identical_copies_separate(tmp_path):
    repo, remote, old = fixture(tmp_path)
    raw = b'{"scene":"authored-current-variant"}\n'
    (repo / 'old.json').write_bytes(raw)
    (repo / 'copied.json').write_bytes(raw)
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'authored historical variant and copy')
    git(repo, 'push', '-q', 'origin', 'main')
    head = git(repo, 'rev-parse', 'HEAD')
    with held(repo, remote) as sources:
        documents = sources.snapshot()['documents']
        old_entry = next(row for row in documents if row['commit'] == old and row['path'] == 'old.json')
        current = next(row for row in documents if row['commit'] == head and row['path'] == 'old.json')
        copied = next(row for row in documents if row['commit'] == head and row['path'] == 'copied.json')
        (repo / 'old.json').write_bytes(b'{"scene":"uncommitted-live-variant"}\n')
        old_view = sources.read_document(old, 'old.json', expected_oid=old_entry['oid'])
        current_view = sources.read_document(head, 'old.json', expected_oid=current['oid'])
        copied_view = sources.read_document(head, 'copied.json', expected_oid=copied['oid'])
        assert old_view['raw'] == b'{"scene":"authored-old"}\n'
        assert current_view['raw'] == copied_view['raw'] == raw
        assert current_view['oid'] == copied_view['oid'] != old_view['oid']
        assert current_view['path'] != copied_view['path']
        assert old_view['root_tree'] != current_view['root_tree']


@pytest.mark.parametrize('kind', ['wrong-commit', 'wrong-path', 'wrong-oid', 'commit-type',
                                  'path-type', 'oid-type', 'traversal', 'absolute', 'nul'])
def test_invalid_document_attachment_poisons_and_closes_all_descriptors(tmp_path, kind):
    repo, remote, old = fixture(tmp_path)
    before = len(os.listdir('/proc/self/fd'))
    sources = held(repo, remote)
    with pytest.raises(ValueError):
        with sources:
            descriptor = next(row for row in sources.snapshot()['documents'] if row['commit'] == old)
            commit, path, oid = old, 'old.json', descriptor['oid']
            if kind == 'wrong-commit': commit = git(repo, 'rev-parse', 'HEAD')
            elif kind == 'wrong-path': path = 'new.md'
            elif kind == 'wrong-oid': oid = '0' * 40
            elif kind == 'commit-type': commit = None
            elif kind == 'path-type': path = Path('old.json')
            elif kind == 'oid-type': oid = []
            elif kind == 'traversal': path = '../old.json'
            elif kind == 'absolute': path = '/old.json'
            else: path = 'old.json\0'
            sources.read_document(commit, path, expected_oid=oid)
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): sources.snapshot()
    with pytest.raises(RuntimeError): sources.retained_metadata_size_bytes()


def test_metadata_budget_is_bounded_payload_free_and_accounts_for_reads(tmp_path):
    repo, remote, old = fixture(tmp_path)
    with held(repo, remote) as sources:
        snapshot = sources.snapshot()
        initial = sources.retained_metadata_size_bytes()
        assert type(initial) is int and 0 < initial <= module().MAX_METADATA_BYTES
        assert initial >= len(json.dumps(snapshot).encode())
        assert sources.snapshot()['read_records'] == []
        descriptor = next(row for row in snapshot['documents'] if row['commit'] == old)
        sources.read_document(old, 'old.json', expected_oid=descriptor['oid'])
        assert sources.retained_metadata_size_bytes() > initial
    with pytest.raises(RuntimeError): sources.retained_metadata_size_bytes()


@pytest.mark.parametrize('operation', ['document', 'budget'])
@pytest.mark.parametrize('failure', ['drift', 'cap', 'deadline'])
def test_public_document_and_metadata_failures_poison_custody(tmp_path, monkeypatch, operation, failure):
    repo, remote, old = fixture(tmp_path)
    before = len(os.listdir('/proc/self/fd'))
    sources = held(repo, remote)
    with pytest.raises((ValueError, RuntimeError, TimeoutError)):
        with sources:
            descriptor = next(row for row in sources.snapshot()['documents'] if row['commit'] == old)
            if failure == 'drift': git(repo, 'branch', 'later', old)
            elif failure == 'deadline': sources.deadline = time.monotonic() - 1
            elif operation == 'document': monkeypatch.setattr(module(), 'MAX_DOCUMENT_BYTES', 1)
            else: monkeypatch.setattr(module(), 'MAX_METADATA_BYTES', sources.retained_metadata_size_bytes() - 1)
            if operation == 'document': sources.read_document(old, 'old.json', expected_oid=descriptor['oid'])
            else: sources.retained_metadata_size_bytes()
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): sources.snapshot()


@pytest.mark.parametrize('object_format', ['sha1', 'sha256'])
def test_actual_history_advertisement_and_authenticated_unique_documents(tmp_path, object_format):
    repo, remote, old = fixture(tmp_path, object_format)
    with held(repo, remote) as sources:
        snapshot = sources.snapshot()
        assert snapshot['object_format'] == object_format
        assert old in snapshot['commits'] and len(snapshot['commits']) == 2
        assert 'refs/heads/history' in dict(snapshot['advertised_refs'])
        assert 'refs/tags/authored-tag' in dict(snapshot['local_refs'])
        assert {row['path'] for row in snapshot['documents']} == {'old.json', 'new.md'}
        assert len(snapshot['blobs']) == 2
        for row in snapshot['blobs']:
            payload = sources.read_blob(row['oid'])
            assert row == {'oid': row['oid'], 'size_bytes': len(payload), 'object_type': 'blob'}
            assert any(record['oid'] == row['oid'] and record['sha256'] == hashlib.sha256(payload).hexdigest()
                       for record in sources.snapshot()['read_records'])
            hasher = hashlib.new(object_format)
            hasher.update(b'blob ' + str(len(payload)).encode() + b'\0' + payload)
            assert hasher.hexdigest() == row['oid']
        assert snapshot['inventory_complete'] is False
        assert snapshot['native_execution'] is False
        assert snapshot['bootstrap_admission'] is False
        assert snapshot['executable'] is False
        assert snapshot['collection_admission'] is False
        assert snapshot['qualification_claims'] == []
        sources.recheck()
        snapshot['documents'].clear()
        assert sources.snapshot()['documents']
    with pytest.raises(RuntimeError): sources.snapshot()
    with pytest.raises(RuntimeError): sources.read_blob('0' * (40 if object_format == 'sha1' else 64))
    with pytest.raises(RuntimeError): sources.recheck()
    with pytest.raises(RuntimeError):
        with sources: pass


def test_detached_registered_worktree_is_a_reachable_root(tmp_path):
    repo, remote, old = fixture(tmp_path)
    detached = tmp_path / 'detached'
    git(repo, 'worktree', 'add', '-q', '--detach', str(detached), old)
    (detached / 'detached.json').write_text('{"authored":"detached"}')
    git(detached, 'add', '.'); git(detached, 'commit', '-qm', 'only detached root')
    head = git(detached, 'rev-parse', 'HEAD')
    with held(repo, remote) as sources:
        assert head in sources.snapshot()['commits']
        assert any(row['path'] == str(detached) and row['detached'] for row in sources.snapshot()['worktrees'])
        assert 'detached.json' in {row['path'] for row in sources.snapshot()['documents']}


def test_advertised_object_not_locally_available_refuses_without_fetch(tmp_path):
    repo, remote, old = fixture(tmp_path)
    other = tmp_path / 'other'; other.mkdir()
    git(other, 'clone', '-q', str(remote), '.')
    git(other, 'checkout', '-q', '-b', 'unseen', 'origin/main')
    (other / 'unseen.json').write_text('{}')
    git(other, 'add', '.'); git(other, 'commit', '-qm', 'unseen remote source')
    git(other, 'push', '-q', 'origin', 'unseen')
    before = git(repo, 'for-each-ref')
    with pytest.raises((ValueError, RuntimeError)):
        with held(repo, remote): pass
    assert git(repo, 'for-each-ref') == before


@pytest.mark.parametrize('kind', ['local-ref', 'advertised-ref', 'new-worktree', 'source-object', 'source-edit-restore'])
def test_source_closure_drift_fails_and_poisoned_context_cannot_continue(tmp_path, kind):
    repo, remote, old = fixture(tmp_path)
    if kind in ('source-object', 'source-edit-restore'):
        root = repo / '.git' / 'objects'
        leaf = next(path for path in root.glob('*/*') if path.is_file())
        leaf.chmod(0o644)
    source = held(repo, remote)
    with pytest.raises((ValueError, RuntimeError)):
        with source:
            if kind == 'local-ref': git(repo, 'branch', 'later', old)
            elif kind == 'advertised-ref': git(remote, 'update-ref', 'refs/pull/7/head', old)
            elif kind == 'new-worktree': git(repo, 'worktree', 'add', '-q', '--detach', str(tmp_path / 'later'), old)
            else:
                payload = leaf.read_bytes()
                if kind == 'source-object': leaf.write_bytes(b'corrupted authored object')
                else: leaf.write_bytes(payload + b'x'); leaf.write_bytes(payload)
            source.recheck()
    with pytest.raises(RuntimeError): source.snapshot()


@pytest.mark.parametrize('kind', ['shallow', 'grafts', 'alternates', 'replace', 'blob-ref', 'document-symlink', 'bad-document-path', 'worktree-symlink', 'missing-worktree'])
def test_ambiguous_missing_or_noncanonical_sources_refuse(tmp_path, kind):
    repo, remote, old = fixture(tmp_path)
    if kind == 'shallow': (repo / '.git' / 'shallow').write_text(old + '\n')
    elif kind == 'grafts': (repo / '.git' / 'info' / 'grafts').write_text(old + '\n')
    elif kind == 'alternates': (repo / '.git' / 'objects' / 'info' / 'alternates').write_text('/tmp/absent\n')
    elif kind == 'replace': git(repo, 'update-ref', 'refs/replace/' + old, old)
    elif kind == 'blob-ref':
        blob = git(repo, 'rev-parse', 'HEAD:new.md'); git(repo, 'update-ref', 'refs/tags/blob', blob)
    elif kind in ('document-symlink', 'bad-document-path'):
        path = repo / ('linked.json' if kind == 'document-symlink' else 'bad\\name.json')
        if kind == 'document-symlink': path.symlink_to('new.md')
        else: path.write_text('{}')
        git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'invalid authored tracked path')
    else:
        linked = tmp_path / 'linked'
        git(repo, 'worktree', 'add', '-q', '--detach', str(linked), old)
        moved = tmp_path / 'moved'; linked.rename(moved)
        if kind == 'worktree-symlink': linked.symlink_to(moved, target_is_directory=True)
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError, RuntimeError, OSError)):
        with held(repo, remote): pass
    assert len(os.listdir('/proc/self/fd')) == before


def test_remote_url_and_unregistered_blob_are_exact(tmp_path):
    repo, remote, old = fixture(tmp_path)
    with pytest.raises(ValueError):
        with held(repo, tmp_path / 'wrong'): pass
    with pytest.raises(RuntimeError):
        with held(repo, remote) as sources:
            with pytest.raises(ValueError): sources.read_blob('0' * 40)
            with pytest.raises(RuntimeError): sources.snapshot()


@pytest.mark.parametrize('deadline', [True, float('inf'), float('nan'), -1])
def test_deadline_types_and_expiry_refuse(tmp_path, deadline):
    module_ = module()
    with pytest.raises((ValueError, TimeoutError)):
        with module_.HeldGitSceneSources(tmp_path, remote='origin', expected_remote_url='/tmp/authored', deadline=deadline): pass


def test_deadline_cannot_extend_beyond_fixed_ten_minutes(tmp_path):
    with pytest.raises(ValueError):
        module().HeldGitSceneSources(tmp_path, remote='origin', expected_remote_url='/tmp/authored', deadline=time.monotonic() + 601)


@pytest.mark.parametrize('kind', ['stdout', 'stderr', 'deadline', 'surviving-group'])
def test_bounded_command_supervision_actual_owned_children(tmp_path, kind):
    module_ = module()
    marker = tmp_path / 'child-pid'
    if kind == 'stdout': code = 'import os; os.write(1,b"x"*8193)'
    elif kind == 'stderr': code = 'import os; os.write(2,b"x"*1025)'
    elif kind == 'deadline': code = 'import time; time.sleep(5)'
    else:
        code = ('import os,time; pid=os.fork(); '
                f'open({str(marker)!r},"w").write(str(pid)) if pid else None; '
                'os._exit(0) if pid else time.sleep(5)')
    before = time.monotonic()
    with pytest.raises((ValueError, TimeoutError, RuntimeError)):
        module_._bounded_command([sys.executable, '-c', code], cwd=tmp_path,
            env=dict(os.environ), deadline=before + (0.15 if kind == 'deadline' else 2),
            stdout_cap=8192, stderr_cap=1024)
    assert time.monotonic() - before < 3


def test_fixed_metadata_document_and_reference_bounds():
    result = module()
    assert result.MAX_REFS == result.MAX_COMMITS == result.MAX_BLOBS == 4096
    assert result.MAX_DOCUMENT_BYTES == 4 * 1024 ** 2
    assert result.MAX_METADATA_BYTES == 64 * 1024 ** 2
    assert result.MAX_COMMAND_STDOUT == 8 * 1024 ** 2
    assert result.MAX_COMMAND_STDERR == 64 * 1024


def test_original_failure_is_preserved_through_context_exit(tmp_path):
    repo, remote, old = fixture(tmp_path)
    with pytest.raises(ValueError, match='not discovered'):
        with held(repo, remote) as sources:
            sources.read_blob('0' * 40)


def test_changed_ref_rejected_at_close_without_explicit_recheck(tmp_path):
    repo, remote, old = fixture(tmp_path)
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises(RuntimeError):
        with held(repo, remote):
            git(repo, 'branch', 'created-inside', old)
    assert len(os.listdir('/proc/self/fd')) == before


def test_oversized_actual_document_refused_without_retaining_it(tmp_path):
    repo, remote, old = fixture(tmp_path)
    (repo / 'too-large.json').write_bytes(b'x' * (4 * 1024 ** 2 + 1))
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'authored oversized document')
    with pytest.raises(ValueError, match='four MiB'):
        with held(repo, remote): pass


def test_actual_packed_ref_count_exceeds_fixed_bound(tmp_path):
    repo, remote, old = fixture(tmp_path)
    packed = repo / '.git' / 'packed-refs'
    packed.write_text('# pack-refs with: peeled fully-peeled sorted\n' + ''.join(
        f'{old} refs/heads/authored-{index:04d}\n' for index in range(4097)))
    with pytest.raises(ValueError, match='references exceed'):
        with held(repo, remote): pass


def test_packed_objects_and_packed_refs_are_discovered_without_loose_assumption(tmp_path):
    repo, remote, old = fixture(tmp_path)
    git(repo, 'gc', '--prune=now')
    with held(repo, remote) as sources:
        assert old in sources.snapshot()['commits']
        assert len(sources.snapshot()['blobs']) == 2


def test_selected_linked_worktree_uses_common_namespace(tmp_path):
    repo, remote, old = fixture(tmp_path)
    linked = tmp_path / 'linked'
    git(repo, 'worktree', 'add', '-q', '--detach', str(linked), old)
    with held(linked, remote) as sources:
        assert sources.snapshot()['common_git_dir'] == str(repo / '.git')
        assert len(sources.snapshot()['worktrees']) == 2


@pytest.mark.parametrize('kind', ['root-link', 'ancestor-link', 'pointer-link', 'common-link'])
def test_actual_namespace_aliases_fail_without_descriptor_leaks(tmp_path, kind):
    repo, remote, old = fixture(tmp_path)
    if kind == 'root-link':
        alias = tmp_path / 'alias'; alias.symlink_to(repo, target_is_directory=True); repo = alias
    elif kind == 'ancestor-link':
        alias = tmp_path / 'alias'; alias.symlink_to(tmp_path, target_is_directory=True); repo = alias / 'repo'
    elif kind == 'pointer-link':
        moved = tmp_path / 'moved-git'; (repo / '.git').rename(moved)
        (repo / '.git').symlink_to(moved, target_is_directory=True)
    else:
        leaf = repo / '.git' / 'config'; moved = tmp_path / 'moved-config'; leaf.rename(moved); leaf.symlink_to(moved)
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError, OSError)):
        with held(repo, remote): pass
    assert len(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('kind', ['local', 'worktree'])
def test_external_config_includes_are_outside_held_namespace_and_refused(tmp_path, kind):
    repo, remote, old = fixture(tmp_path)
    external = tmp_path / 'external-config'
    external.write_text('[user]\n    name = Authored external config\n')
    if kind == 'local': target = repo / '.git' / 'config'
    else:
        git(repo, 'config', 'extensions.worktreeConfig', 'true')
        target = repo / '.git' / 'config.worktree'
    with target.open('a') as stream:
        stream.write(f'[include]\n    path = {external}\n')
    with pytest.raises(ValueError, match='include'):
        with held(repo, remote): pass


def test_metadata_discovery_never_opens_document_payloads(tmp_path, monkeypatch):
    repo, remote, old = fixture(tmp_path)
    module_ = module()
    original = module_.HeldGitSceneSources._blob
    calls = []
    def track(self, oid):
        calls.append(oid)
        return original(self, oid)
    monkeypatch.setattr(module_.HeldGitSceneSources, '_blob', track)
    with held(repo, remote) as sources:
        assert not calls
        assert sources.snapshot()['read_records'] == []
        sources.recheck()
        assert not calls
        oid = sources.snapshot()['blobs'][0]['oid']
        payload = sources.read_blob(oid)
        assert calls == [oid]
        assert sources.snapshot()['read_records'] == [{'oid': oid,
            'size_bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}]
        sources.recheck()
        assert calls == [oid]
    assert calls == [oid]
    assert module_.MAX_TREES == 65536


@pytest.mark.parametrize('kind', ['deadline', 'copy-error', 'identity-drift'])
def test_snapshot_copy_failure_or_late_or_stale_success_poison_and_close(tmp_path, monkeypatch, kind):
    repo, remote, old = fixture(tmp_path)
    module_ = module()
    before = len(os.listdir('/proc/self/fd'))
    sources = held(repo, remote).__enter__()
    original = module_.copy.deepcopy
    calls = []
    def copied(value):
        calls.append(None)
        if kind == 'copy-error': raise RuntimeError('authored copy failure')
        result = original(value)
        if kind == 'deadline': monkeypatch.setattr(module_.time, 'monotonic', lambda: sources.deadline + 1)
        elif len(calls) == 1: git(repo, 'branch', 'during-copy', old)
        return result
    monkeypatch.setattr(module_.copy, 'deepcopy', copied)
    try:
        with pytest.raises((RuntimeError, TimeoutError)):
            sources.snapshot()
        assert len(os.listdir('/proc/self/fd')) == before
        with pytest.raises(RuntimeError): sources.snapshot()
        sources.__exit__(RuntimeError, RuntimeError('authored body failure'), None)
    finally:
        sources._held.close()


def test_double_leading_absolute_root_refused_before_git_or_descriptors(tmp_path, monkeypatch):
    module_ = module()
    monkeypatch.setattr(module_, '_bounded_command', lambda *args, **kwargs: pytest.fail('Git ran before root admission'))
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises(ValueError, match='canonical'):
        module_.HeldGitSceneSources('/' + str(tmp_path), remote='origin',
            expected_remote_url='/tmp/authored', deadline=time.monotonic() + 30)
    assert len(os.listdir('/proc/self/fd')) == before


def test_owned_group_is_observed_after_kill_even_when_leader_exited(tmp_path, monkeypatch):
    module_ = module()
    observations, killed = [], []
    original_alive, original_signal = module_._group_alive, module_._signal_group
    def alive(pgid):
        observations.append(bool(killed))
        return original_alive(pgid)
    def signal_group(pgid, sig):
        if sig == module_.signal.SIGKILL: killed.append(pgid)
        original_signal(pgid, sig)
    monkeypatch.setattr(module_, '_group_alive', alive)
    monkeypatch.setattr(module_, '_signal_group', signal_group)
    code = 'import os,time; pid=os.fork(); os._exit(0) if pid else time.sleep(5)'
    with pytest.raises(RuntimeError, match='surviving'):
        module_._bounded_command([sys.executable, '-c', code], cwd=tmp_path,
            env=dict(os.environ), deadline=time.monotonic() + 2)
    assert killed and any(observations), 'Post-KILL owned group was never observed'


def test_remaining_group_cleanup_failure_is_retained_on_original_error(tmp_path, monkeypatch):
    module_ = module()
    original_alive, original_signal = module_._group_alive, module_._signal_group
    killed = []
    def signal_group(pgid, sig):
        if sig == module_.signal.SIGKILL: killed.append(pgid)
        original_signal(pgid, sig)
    monkeypatch.setattr(module_, '_signal_group', signal_group)
    # Faithful final-observation seam: simulate the OS still reporting a group
    # after KILL; it is not proof of a hostile descendant's escape/reaping.
    monkeypatch.setattr(module_, '_group_alive', lambda pgid: bool(killed) or original_alive(pgid))
    before = time.monotonic()
    with pytest.raises(ValueError, match='stdout exceeds') as captured:
        module_._bounded_command([sys.executable, '-c', 'import os,time; os.write(1,b"x"*9); time.sleep(5)'],
            cwd=tmp_path, env=dict(os.environ), deadline=before + 2, stdout_cap=8)
    assert any('cleanup' in note and 'group' in note for note in getattr(captured.value, '__notes__', ()))
    assert time.monotonic() - before < 2


def test_linked_worktree_pointer_to_other_admin_is_not_authenticated(tmp_path):
    repo, remote, old = fixture(tmp_path)
    first, second = tmp_path / 'first', tmp_path / 'second'
    git(repo, 'worktree', 'add', '-q', '--detach', str(first), old)
    git(repo, 'worktree', 'add', '-q', '--detach', str(second), old)
    (first / '.git').write_bytes((second / '.git').read_bytes())
    with pytest.raises(ValueError, match='worktree|admin|reciprocal'):
        with held(repo, remote): pass


def test_cleanup_signal_error_does_not_mask_original_and_kill_still_attempted(tmp_path, monkeypatch):
    module_ = module()
    original = module_._signal_group
    seen = []
    def signal_group(pgid, sig):
        seen.append((pgid, sig))
        if sig == module_.signal.SIGTERM: raise OSError('authored TERM failure')
        original(pgid, sig)
    monkeypatch.setattr(module_, '_signal_group', signal_group)
    try:
        with pytest.raises(ValueError, match='stdout exceeds') as captured:
            module_._bounded_command([sys.executable, '-c', 'import os,time; os.write(1,b"x"*9); time.sleep(5)'],
                cwd=tmp_path, env=dict(os.environ), deadline=time.monotonic() + 2, stdout_cap=8)
        assert any(sig == module_.signal.SIGKILL for pgid, sig in seen)
        assert any('authored TERM failure' in note for note in captured.value.__notes__)
    finally:
        for pgid, _ in seen:
            original(pgid, module_.signal.SIGKILL)
            try: os.waitpid(pgid, 0)
            except ChildProcessError: pass


def test_bom_config_include_refused_before_first_git_command(tmp_path, monkeypatch):
    repo, remote, old = fixture(tmp_path)
    external = tmp_path / 'external-config'
    external.write_text('[user]\n    name = Authored outside config\n')
    config = repo / '.git' / 'config'
    config.write_bytes(b'\xef\xbb\xbf[include]\n    path = ' + str(external).encode() + b'\n' + config.read_bytes())
    # Establish that Git itself accepts this syntax on the exact fixture/runtime.
    assert git(repo, 'config', '--get', 'user.name') == 'Authored outside config'
    module_ = module()
    calls = []
    original = module_._bounded_command
    def command(*args, **kwargs):
        calls.append(None)
        return original(*args, **kwargs)
    monkeypatch.setattr(module_, '_bounded_command', command)
    with pytest.raises(ValueError, match='BOM|include'):
        with held(repo, remote): pass
    assert calls == [], 'Git was allowed to interpret a config include before rejection'


def test_active_body_failure_preserved_with_final_source_drift_note(tmp_path):
    repo, remote, old = fixture(tmp_path)
    before = len(os.listdir('/proc/self/fd'))
    sources = held(repo, remote)
    with pytest.raises(LookupError, match='original parser failure') as captured:
        with sources:
            git(repo, 'branch', 'authored-final-drift', old)
            raise LookupError('original parser failure')
    assert any('final' in note and ('changed' in note or 'identity' in note)
               for note in getattr(captured.value, '__notes__', ()))
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): sources.snapshot()
