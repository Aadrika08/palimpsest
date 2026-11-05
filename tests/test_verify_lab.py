"""Backward-compatible bounds for the actual-owner verifier."""
from argparse import Namespace
from pathlib import Path
import pytest
import verify_lab


def test_verifier_exposes_bounded_parameters_and_original_defaults():
    assert hasattr(verify_lab, 'parameters'), 'verifier parameters missing'
    assert verify_lab.parameters(Namespace()) == (0, 4, 4)
    assert verify_lab.parameters(Namespace(seed=9, prefix=8, continuation=92)) == (9, 8, 92)
    for key, value in [('prefix', 0), ('continuation', 101), ('seed', True)]:
        with pytest.raises(ValueError):
            verify_lab.parameters(Namespace(**{key: value}))


def test_requested_seed_and_bounds_reach_owner_and_failure_report(tmp_path, monkeypatch):
    seen = []
    class Supervisor:
        def __init__(self, *args, **kwargs): pass
        def start(self, config):
            seen.append(config)
            raise RuntimeError('fixture owner refusal')
        def shutdown(self): pass
    monkeypatch.setattr(verify_lab, 'LabSupervisor', Supervisor)
    result = verify_lab.verify(Namespace(repo=tmp_path, assets=tmp_path, output=tmp_path / 'out',
                                        controller='manual', seed=7, prefix=8, continuation=92))
    assert seen[0]['seed'] == 7
    assert result['prefix_ticks'] == 8 and result['continuation_ticks'] == 92
    assert result['status'] == 'failed'
    assert result['timings'] == {}


@pytest.mark.parametrize('failed_actions', [False, True])
def test_study_owner_flow_uses_exact_lengths_and_keeps_pair_reports(tmp_path, monkeypatch, failed_actions):
    import numpy as np
    owners = []
    class Supervisor:
        def __init__(self, *args, **kwargs):
            self.root = args[2]
            assert kwargs['storage_limits'].max_bytes < 512 * 1024**2
        def start(self, config):
            identifier = str(len(owners))
            owners.append({'config': config, 'commands': [], 'path': self.root / identifier})
            owners[-1]['path'].mkdir(parents=True)
            return identifier
        def path(self, identifier): return owners[int(identifier)]['path']
        def describe(self, identifier):
            owner = owners[int(identifier)]
            if owner['config'].get('job') == 'replay':
                mode = owner['config']['replay_mode']
                return {'status': 'failed' if failed_actions and mode == 'actions' else 'closed',
                        'replay': {'status': 'failed' if failed_actions and mode == 'actions' else 'passed', 'mode': mode,
                         'compared_ticks': 100, 'comparison': {'fields': ['action']}}}
            return {'status': 'ready', 'sample': {'world': {'goal': [0., 0.]}},
                    'state': {'phase': 'paused', 'episode': 0, 'revision': len(owner['commands'])},
                    'receipts': [{'id': c['id'], 'status': 'applied'} for c in owner['commands']]}
        def call(self, identifier, kind, payload):
            if kind == 'command': owners[int(identifier)]['commands'].append(payload)
            if kind == 'snapshot': return {'snapshot_id': 'snapshot'}
        def snapshot(self, identifier, snapshot_id):
            path = self.path(identifier) / 'snapshot.snp'
            path.write_bytes(b'fixture')
            return path, {'sha256': 'a' * 64, 'config': owners[int(identifier)]['config']}
        def close(self, identifier): pass
        def shutdown(self): pass
    monkeypatch.setattr(verify_lab, 'LabSupervisor', Supervisor)
    def ticks(path):
        branch = path.parent.name == '1'
        return ({'tick': np.asarray(t), 'cam_left': np.zeros(2), 'eyes': np.asarray([False, True])}
                for t in range(8 if branch else 0, 100))
    monkeypatch.setattr(verify_lab, 'iter_ticks', ticks)
    monkeypatch.setattr(verify_lab, 'playback', lambda path, tick: {'mode': 'playback'})
    monkeypatch.setattr(verify_lab, 'compare_runs', lambda *args: {'fixture': True})
    result = verify_lab.verify(Namespace(repo=tmp_path, assets=tmp_path, output=tmp_path / 'out',
                                        controller='flynn', seed=4, prefix=8, continuation=92, study=True))
    assert result['status'] == ('failed' if failed_actions else 'passed'), result
    assert len(owners) == 4  # source, branch, actions, policy; exploratory edit omitted
    assert owners[0]['config']['seed'] == 4
    steps = [c for c in owners[0]['commands'] if c['kind'] == 'step']
    assert len(steps) == 100
    assert len(owners[1]['commands']) == 92
    assert result['source']['source_ticks'] == 100
    assert result['source']['condition'] == 'background_storage'
    assert Path(result['source']['snapshot_path']).read_bytes() == b'fixture'
    assert set(result['timings']) == {'capture_save_seconds', 'branch_seconds', 'playback_seconds',
                                      'action_replay_seconds', 'policy_replay_seconds'}
    assert all(value >= 0 for value in result['timings'].values())


def test_owner_storage_failure_remains_structured(tmp_path, monkeypatch):
    class Supervisor:
        def __init__(self, *args, **kwargs): pass
        def start(self, config): return 'source'
        def describe(self, identifier):
            return {'status': 'failed', 'failure': {'type': 'StorageLimitError', 'message': 'owner quota'}}
        def shutdown(self): pass
    monkeypatch.setattr(verify_lab, 'LabSupervisor', Supervisor)
    report = verify_lab.verify(Namespace(repo=tmp_path, assets=tmp_path, output=tmp_path / 'out',
                                        controller='flynn', seed=0, prefix=8, continuation=92, study=True))
    assert report['status'] == 'failed'
    assert report['resource_boundary'] == {'type': 'StorageLimitError', 'message': 'owner quota'}
