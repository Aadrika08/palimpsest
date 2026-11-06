"""Retained authored failure bytes; no native runtime or source qualification."""
import json
from pathlib import Path

import numpy as np
import pytest

from palimpsest import records, snapshots
from palimpsest.records import RunWriter, iter_ticks
from palimpsest.storage import StorageBudget, StorageLimitError, StorageLimits
from test_memory_source_bootstrap_vnext import route  # Reuse the real authored bootstrap.


class DiskFailure(OSError):
    pass


def fail_io(monkeypatch, target, phase):
    """Inject only the target disk operation; retain the real publication path."""
    original_open = Path.open
    original_replace = Path.replace

    class Stream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, payload):
            if phase == 'write':
                self.stream.write(payload[:11])
                self.stream.flush()
                raise DiskFailure('authored partial write')
            return self.stream.write(payload)

        def flush(self):
            self.stream.flush()
            if phase == 'flush':
                raise DiskFailure('authored flush failure')

        def fileno(self):
            return self.stream.fileno()

    def opened(path, mode='r', *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        return Stream(stream) if path == target and mode == 'xb' else stream

    def replaced(path, destination):
        if path == target:
            raise DiskFailure('authored replace failure')
        return original_replace(path, destination)

    if phase in ('write', 'flush'):
        monkeypatch.setattr(Path, 'open', opened)
    elif phase == 'fsync':
        def failed_fsync(descriptor):
            raise DiskFailure('authored fsync failure')
        monkeypatch.setattr(records.os, 'fsync', failed_fsync)
    elif phase == 'replace':
        monkeypatch.setattr(Path, 'replace', replaced)


def options(preserve):
    return {} if preserve is None else {'preserve_failed': preserve}


@pytest.mark.parametrize('bad', [None, 0, 1, '', np.bool_(True)])
@pytest.mark.parametrize('api', ['snapshot', 'writer'])
def test_exact_bool_refuses_before_serialization_and_output(tmp_path, bad, api):
    destination = tmp_path / 'absent'
    with pytest.raises(ValueError, match='preserve_failed'):
        if api == 'snapshot':
            snapshots.save_snapshot(object(), destination, preserve_failed=bad)
        else:
            RunWriter(destination, {'unserializable': object()}, preserve_failed=bad)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('preserve', [None, True])
@pytest.mark.parametrize('phase', ['write', 'flush', 'fsync'])
def test_snapshot_disk_failure_retains_only_opted_in_exclusive_bytes(tmp_path, monkeypatch, preserve, phase):
    destination = tmp_path / 'initial.snp'
    fail_io(monkeypatch, destination, phase)
    with pytest.raises(DiskFailure):
        snapshots.save_snapshot({'authored': np.arange(3, dtype=np.int16)}, destination, **options(preserve))
    assert destination.exists() is (preserve is True)
    if preserve:
        retained = destination.read_bytes()
        assert len(retained) == 11 if phase == 'write' else len(retained) > 11
        with pytest.raises(FileExistsError):
            snapshots.save_snapshot({'different': 1}, destination, preserve_failed=True)
        assert destination.read_bytes() == retained


@pytest.mark.parametrize('preserve', [None, True])
def test_snapshot_never_removes_preexisting_target(tmp_path, preserve):
    destination = tmp_path / 'initial.snp'
    destination.write_bytes(b'preexisting failed snapshot')
    with pytest.raises(FileExistsError):
        snapshots.save_snapshot({'authored': 1}, destination, **options(preserve))
    assert destination.read_bytes() == b'preexisting failed snapshot'


def test_successful_snapshot_bytes_are_unchanged(tmp_path, monkeypatch):
    # ZIP's clock is incidental, so hold it fixed for an exact encoder comparison.
    monkeypatch.setattr(snapshots.zipfile.time, 'localtime', lambda *args: (2026, 1, 2, 3, 4, 6, 4, 2, -1))
    value = {'authored': np.arange(3, dtype=np.float32), 'bytes': b'tiny', 'scalar': 3}
    default, preserved = tmp_path / 'default.snp', tmp_path / 'preserved.snp'
    assert snapshots.save_snapshot(value, default) == snapshots.save_snapshot(value, preserved, preserve_failed=True)
    assert default.read_bytes() == preserved.read_bytes()
    restored = snapshots.read_snapshot(preserved)
    np.testing.assert_array_equal(restored['authored'], value['authored'])
    assert restored['bytes'] == b'tiny' and restored['scalar'] == 3


@pytest.mark.parametrize('background', [False, True])
def test_successful_writer_bytes_and_drain_are_unchanged(tmp_path, background):
    paths = [tmp_path / 'default', tmp_path / 'preserved']
    for path, kwargs in zip(paths, [{}, {'preserve_failed': True}]):
        writer = RunWriter(path, {'authored': True}, **kwargs)
        if background:
            writer.start_background(max_items=2)
        writer.tick(0, 0, action=np.array([.25, -.5], np.float32))
        writer.event('authored')
        writer.finish({})
        writer.close()
        assert writer._events.closed
        assert len(list(iter_ticks(path))) == 1
        assert not list(path.rglob('*.tmp'))
        if background:
            assert not writer._background.thread.is_alive()
            assert writer.background_stats()['pending_bytes'] == 0
    contents = [{str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()} for path in paths]
    assert contents[0] == contents[1]


@pytest.mark.parametrize('background', [False, True])
@pytest.mark.parametrize('kind', ['manifest', 'chunk'])
@pytest.mark.parametrize('phase', ['write', 'flush', 'fsync', 'replace'])
@pytest.mark.parametrize('preserve', [None, True])
def test_real_writer_retains_failed_pending_without_qualified_success(tmp_path, monkeypatch, background, kind, phase, preserve):
    writer = RunWriter(tmp_path / 'run', {}, **options(preserve))
    if background:
        writer.start_background(max_items=2)
    target = writer.path / ('manifest.json' if kind == 'manifest' else 'chunks/000000.npz')
    pending = target.with_suffix('.tmp')
    manifest_before = (writer.path / 'manifest.json').read_bytes()
    if kind == 'chunk':
        writer.tick(0, 0, action=np.ones(2, np.float32))
    fail_io(monkeypatch, pending, phase)
    expected = RuntimeError if background and kind == 'chunk' else DiskFailure
    try:
        with pytest.raises(expected) as caught:
            writer.finish({})
        if background and kind == 'chunk':
            assert isinstance(caught.value.__cause__, DiskFailure)
            assert writer.background_stats()['error']['type'] == 'DiskFailure'
        assert pending.exists() is (preserve is True)
        retained = pending.read_bytes() if preserve else None
        if preserve:
            assert len(retained) == 11 if phase == 'write' else len(retained) > 11
        assert (writer.path / 'manifest.json').read_bytes() == manifest_before
        assert json.loads(manifest_before)['status'] == 'running'
        assert list(iter_ticks(writer.path)) == []
        assert (writer.path / 'events.jsonl').read_bytes() == b''
        with pytest.raises((ValueError, RuntimeError)):
            writer.finish({'must_not_retry': True})
    finally:
        writer.close()
    assert writer._events.closed
    if background:
        assert not writer._background.thread.is_alive()
        assert writer.background_stats()['pending_bytes'] == 0
    if preserve:
        assert pending.read_bytes() == retained


@pytest.mark.parametrize('helper', [records._atomic_manifest, records._publish_chunk])
def test_preexisting_pending_is_never_reused_or_unlinked_in_preservation_mode(tmp_path, helper):
    target = tmp_path / 'target.json'
    pending = target.with_suffix('.tmp')
    target.write_bytes(b'published prefix')
    pending.write_bytes(b'failed pending')
    for _ in range(2):
        with pytest.raises(FileExistsError):
            helper(target, b'replacement forbidden', preserve_failed=True)
        assert pending.read_bytes() == b'failed pending'
        assert target.read_bytes() == b'published prefix'


@pytest.mark.parametrize('background', [False, True])
def test_writer_refuses_preexisting_chunk_pending_and_does_not_retry(tmp_path, background):
    writer = RunWriter(tmp_path / 'run', {}, preserve_failed=True)
    if background:
        writer.start_background()
    pending = writer.path / 'chunks/000000.tmp'
    pending.write_bytes(b'failed prior attempt')
    writer.tick(0, 0, action=np.zeros(2))
    with pytest.raises(RuntimeError if background else FileExistsError):
        writer.flush()
    writer.close()
    assert pending.read_bytes() == b'failed prior attempt'
    assert list(iter_ticks(writer.path)) == []
    with pytest.raises((ValueError, RuntimeError)):
        writer.event('no reuse')


def test_initial_manifest_failure_is_retained(tmp_path, monkeypatch):
    run = tmp_path / 'run'
    pending = run / 'manifest.tmp'
    fail_io(monkeypatch, pending, 'write')
    with pytest.raises(DiskFailure):
        RunWriter(run, {}, preserve_failed=True)
    assert len(pending.read_bytes()) == 11
    assert not (run / 'manifest.json').exists()
    with pytest.raises(FileExistsError):
        RunWriter(run, {}, preserve_failed=True)
    assert len(pending.read_bytes()) == 11


@pytest.mark.parametrize('background', [False, True])
def test_preservation_does_not_bypass_writer_quota(tmp_path, background):
    writer = RunWriter(tmp_path / 'run', {}, max_bytes=500, preserve_failed=True)
    if background:
        writer.start_background()
    writer.tick(0, 0, action=np.zeros(1000, np.uint8))
    with pytest.raises(RuntimeError, match='quota'):
        writer.flush()
    writer.close()
    assert not list(writer.path.rglob('*.tmp'))
    assert list(iter_ticks(writer.path)) == []


def test_retained_snapshot_bytes_remain_chargeable_to_real_storage_budget(tmp_path, monkeypatch):
    budget = StorageBudget([tmp_path], StorageLimits(max_bytes=4096, min_free_bytes=0))
    destination = tmp_path / 'initial.snp'
    fail_io(monkeypatch, destination, 'write')
    with pytest.raises(DiskFailure):
        snapshots.save_snapshot({'authored': 1}, destination, storage_budget=budget, preserve_failed=True)
    assert budget.usage()['used_bytes'] == 11
    with pytest.raises(StorageLimitError, match='quota'):
        budget.check(4090, path=tmp_path / 'next')
    assert destination.read_bytes()


def test_canonical_engine_handoff_preserves_real_writer_manifest_failure(route, monkeypatch):
    engine = route.open()
    assert type(engine.writer) is RunWriter
    pending = route.output / 'manifest.tmp'
    original = DiskFailure('authored partial write')
    # The fault fixture raises this exact object; the group must retain it.
    monkeypatch.setitem(globals(), 'DiskFailure', lambda message: original)
    fail_io(monkeypatch, pending, 'write')
    with pytest.raises(BaseExceptionGroup) as caught:
        engine.close()
    assert caught.value.exceptions == (original,)
    assert len(pending.read_bytes()) == 11
    assert engine.writer._events.closed and engine.env.closed
    assert json.loads((route.output / 'manifest.json').read_text())['status'] == 'running'


def test_default_engine_omits_new_keyword_for_legacy_writer_boundary(route, monkeypatch):
    class LegacyWriterEntry(RuntimeError):
        pass

    def legacy_writer(path, manifest, max_bytes=None, *, storage_budget=None):
        raise LegacyWriterEntry('entered exact legacy writer signature')

    monkeypatch.setattr(records, 'RunWriter', legacy_writer)
    with pytest.raises(LegacyWriterEntry):
        route.open(source_bootstrap_mode=None)
    assert route.trace == [] and route.envs == []
    assert not route.output.exists()
