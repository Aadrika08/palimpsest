import copy
from pathlib import Path
import pytest
from paper.studies.authority_replay_v1 import overhead as o
from paper.studies.authority_replay_v1.null_writer import NullWriter


@pytest.mark.parametrize('field', ['actions_sha256', 'tick_count', 'final_state_sha256'])
def test_whole_seed_exclusion(field):
    rows = [dict(seed=0, condition=c, status='completed', metrics={}, actions_sha256='a', tick_count=220,
                 final_state_sha256='f') for c in o.CONDITIONS]
    rows[-1][field] = 'different'
    assert not o.match_seed(rows)
    assert all(r['timing_eligible'] is False for r in rows)


def test_match_and_nonfinite():
    rows = [dict(seed=0, condition=c, status='completed', metrics={'wall_seconds': 1.}, actions_sha256='a',
                 tick_count=220, final_state_sha256='f') for c in o.CONDITIONS]
    assert o.match_seed(rows)
    rows[0]['metrics']['wall_seconds'] = float('nan')
    with pytest.raises(ValueError, match='finite'):
        o.match_seed(rows)


def test_rotation():
    assert [o.condition_order(i) for i in range(4)] == [o.CONDITIONS[i:] + o.CONDITIONS[:i] for i in range(4)]


@pytest.mark.parametrize('condition', o.CONDITIONS)
def test_writer_dispatch(tmp_path, condition, monkeypatch):
    from collections import namedtuple
    disk = namedtuple("disk", "total used free")
    monkeypatch.setattr(o.shutil, "disk_usage", lambda _: disk(100 * o.GiB, 0, 100 * o.GiB))
    writer = o.make_writer(condition, tmp_path / condition, {})
    try:
        assert isinstance(writer, NullWriter) == (condition == 'null')
        assert (writer.background_stats() is not None) == condition.startswith('background')
        assert (writer.storage_budget is not None) == (condition == 'background_storage')
    finally:
        writer.close()


class FakeEngine:
    def __init__(self):
        self.total_tick = 0
        self.last_transition = {}
        self.writer = type('Writer', (), {'flush': lambda s: None, 'background_stats': lambda s: None})()
    def advance(self):
        self.total_tick += 1
        self.last_transition = {'action': [self.total_tick, 0], 'latency': .01, 'step_latency': .02}


def test_exact_tick_window():
    engine = FakeEngine()
    result = o.measure_ticks(engine)
    assert engine.total_tick == result['tick_count'] == 220
    assert result['measured_tick_count'] == 200
    assert result['metrics']['policy_seconds'] == pytest.approx(2.)
    assert result['metrics']['physics_seconds'] == pytest.approx(4.)
    assert result['metrics']['wall_seconds_per_tick'] == result['metrics']['wall_seconds'] / 200


def test_null_writer_lifecycle(tmp_path):
    writer = NullWriter(tmp_path / 'null', {'run_id': 'null'})
    writer.event('anything', value=1)
    writer.tick(0, 0, action=[0, 1])
    writer.flush()
    writer.finish({'total_tick': 1}, status='completed')
    writer.close()
    assert writer.manifest['status'] == 'completed'
    assert list(writer.path.iterdir()) == [writer.path / 'events.jsonl']
    assert (writer.path / 'events.jsonl').read_bytes() == b''
    with pytest.raises(ValueError):
        writer.tick(0, 1, action=[0, 1])


def test_operations_reject_null_source_before_runtime(tmp_path):
    (tmp_path / 'manifest.json').write_text('{"status":"completed"}')
    with pytest.raises(ValueError, match='retained.*replay|full.writer'):
        o.run_operation_cost_unit(0, tmp_path, output=tmp_path / 'dest')


def test_failed_condition_excludes_whole_seed():
    rows = [dict(seed=0, condition=c, status='completed', metrics={}, actions_sha256='a', tick_count=220,
                 final_state_sha256='f') for c in o.CONDITIONS]
    rows[-1]['status'] = 'timeout'
    assert not o.match_seed(rows)
    assert all(not r['timing_eligible'] for r in rows)
    with pytest.raises(ValueError, match='four distinct'):
        o.match_seed(rows[:-1])


def test_source_requires_explicit_replay_provenance(tmp_path):
    run = tmp_path / ('a' * 32)
    recording = run / 'recording'
    recording.mkdir(parents=True)
    (recording / 'manifest.json').write_text('{"status":"completed"}')
    snapshot = run / 'prefix.snp'
    snapshot.write_bytes(b'source fixture')
    row = {'kind': 'replay', 'status': 'completed', 'seed': 0,
           'source': {'seed': 0, 'condition': 'background_storage', 'recording_writer': 'background',
                      'storage_accounting': True, 'prefix_ticks': 8, 'source_ticks': 100, 'run_path': str(run), 'snapshot_path': str(snapshot)}}
    source = tmp_path / 'row.json'
    import json
    source.write_text(json.dumps(row))
    assert o._source(0, source)[2] == recording
    row['source']['condition'] = 'null'
    source.write_text(json.dumps(row))
    with pytest.raises(ValueError, match='full-writer'):
        o._source(0, source)


def test_execution_fixture_real_writers(tmp_path, monkeypatch):
    from palimpsest.engine import Engine
    from palimpsest import records
    import numpy as np
    from collections import namedtuple
    disk = namedtuple('disk', 'total used free')
    monkeypatch.setattr(o.shutil, 'disk_usage', lambda _: disk(100 * o.GiB, 0, 100 * o.GiB))
    class Fixture(FakeEngine):
        def __init__(self, writer):
            super().__init__()
            self.writer = writer
            self.env = type('Env', (), {'_render_camera': lambda s: None})()
        def advance(self):
            super().advance()
            self.env._render_camera()
            self.writer.tick(0, self.total_tick - 1, action=np.asarray(self.last_transition['action']))
        def close(self):
            self.writer.finish({'total_tick': self.total_tick})
            self.writer.close()
    def opened(repo, assets, output, **kwargs):
        return Fixture(records.RunWriter(output, {}, max_bytes=kwargs['max_bytes']))
    monkeypatch.setattr(Engine, 'open', opened)
    monkeypatch.setattr(o, '_final_digest', lambda e: str(e.total_tick))
    rows = []
    for condition in o.CONDITIONS:
        output = tmp_path / condition
        output.mkdir()
        result = o._execution(0, condition, output, tmp_path, tmp_path, tmp_path)
        rows.append({'seed': 0, 'condition': condition, 'status': 'completed', **result})
        assert result['tick_count'] == 220
        assert result['metrics']['open_seconds'] >= 0
        assert result['metrics']['camera_seconds'] >= 0
        assert (result['metrics']['bytes_per_tick'] == 0) == (condition == 'null')
    assert o.match_seed(rows)
    assert rows[-1]['metrics']['storage_recount_count'] >= 0


def test_expired_global_deadline_prevents_process_start(tmp_path, monkeypatch):
    from collections import namedtuple
    disk = namedtuple('disk', 'total used free')
    monkeypatch.setattr(o.shutil, 'disk_usage', lambda _: disk(100 * o.GiB, 0, 100 * o.GiB))
    def forbidden(*args, **kwargs):
        pytest.fail('expired campaign must not launch a child')
    monkeypatch.setattr(o.subprocess, 'Popen', forbidden)
    row = o.run_execution_overhead_unit(0, 'null', output=tmp_path / 'unit', assets=tmp_path,
                                         campaign_root=tmp_path, campaign_deadline_epoch=1.)
    assert row['status'] == 'failed'
    assert 'deadline' in row['error']['message']
    assert row['timing_eligible'] is False


def test_unit_must_be_below_shared_campaign_root(tmp_path):
    row = o.run_execution_overhead_unit(0, 'null', output=tmp_path / 'unit', assets=tmp_path,
                                         campaign_root=tmp_path / 'different')
    assert row['status'] == 'failed'
    assert 'below campaign root' in row['error']['message']


def test_persisted_campaign_clock_cannot_extend(tmp_path, monkeypatch):
    monkeypatch.setattr(o.time, 'time', lambda: 100.)
    identity = {'commit': 'fixture'}
    assert o.campaign_deadline(tmp_path, identity) == 14500.
    monkeypatch.setattr(o.time, 'time', lambda: 1000.)
    assert o.campaign_deadline(tmp_path, identity, 99999.) == 14500.
    assert o.campaign_deadline(tmp_path, identity, 2000.) == 2000.
    with pytest.raises(ValueError, match='identity drift'):
        o.campaign_deadline(tmp_path, {'commit': 'different'})
