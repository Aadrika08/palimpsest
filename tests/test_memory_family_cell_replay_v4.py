"""Actual pinned upstream cell on temporary tiny model; no production assets."""
import copy
import importlib
import importlib.util
import sys
import time

import numpy as np
import pytest

from palimpsest import snapshots
from test_flynn import FlynnTests, HAS_ML


def replay_module():
    name = 'scripts.memory_family_cell_replay_v4'
    assert importlib.util.find_spec(name) is not None, 'Compact cell replay is missing'
    return importlib.import_module(name)


@pytest.fixture(scope='module')
def fixture_class():
    if not HAS_ML:
        pytest.fail('Pinned synthetic upstream cell tests require simulation dependencies')
    FlynnTests.setUpClass()
    try:
        yield FlynnTests
    finally:
        FlynnTests.tearDownClass()


@pytest.fixture
def sample(fixture_class):
    case = fixture_class()
    case.setUp()
    policy = case.policy
    policy.torch.set_num_threads(1)
    rows = []
    for tick in range(3):
        recorded = policy.act(case.obs)
        rows.append({'episode': 0, 'tick': tick,
                     **{k: recorded[k] for k in ('encoded_input', 'raw_output', 'action')}})
    snapshot = {'policy': {
        'hidden': policy.hidden.detach().cpu().numpy().copy(),
        'left': {k: v.detach().cpu().numpy().copy() for k, v in policy.agent.state_vision_left.items()},
        'right': {k: v.detach().cpu().numpy().copy() for k, v in policy.agent.state_vision_right.items()},
        'failure_diagnostics': {}},
        'application': {'controller_tensors': snapshots.controller_hashes(policy)},
        'identity': {'torch': snapshots._torch_profile()}}
    condition = []
    for tick in range(3, 6):
        recorded = policy.act(case.obs)
        condition.append({'episode': 0, 'tick': tick,
                          **{k: recorded[k] for k in ('encoded_input', 'raw_output', 'action')}})
    return dict(policy=policy, source_snapshot=snapshot, source=rows,
                condition=condition, input_width=policy.agent.cell.Nin)


def request(sample, operation='source'):
    return dict(policy=sample['policy'], rows=sample[operation],
        source_snapshot=sample['source_snapshot'], operation=operation,
        first_tick=0 if operation == 'source' else 3,
        input_width=sample['input_width'], deadline=time.monotonic() + 30)


@pytest.mark.parametrize('operation', ['source', 'condition'])
def test_actual_upstream_cell_matches_recorded_policy_without_retina(sample, operation, monkeypatch):
    module = replay_module()
    before = snapshots.state_digest(sample['policy']._state())
    def forbidden(*args, **kwargs):
        pytest.fail('Encoded cell replay attempted retina or observation processing')
    monkeypatch.setattr(sample['policy'].agent, 'step', forbidden)
    monkeypatch.setattr(sample['policy'].agent, 'obs_to_x', forbidden)
    monkeypatch.setattr(sample['policy'].agent, 'x_to_action', forbidden)
    result = module._replay_rows(**request(sample, operation))
    assert result['rows_checked'] == 3
    assert result['raw_output_equal'] is True
    assert result['action_equal'] is True
    assert result['source_endpoint_verified'] is (operation == 'source')
    assert result['final_hidden_sha256'] != ''
    assert snapshots.state_digest(sample['policy']._state()) == before
    assert 'mujoco' not in sys.modules


@pytest.mark.parametrize('defect', ['input', 'raw', 'action', 'scale-one', 'dtype',
    'shape', 'nonfinite', 'duplicate', 'drop', 'episode', 'source-endpoint',
    'parameters', 'graph', 'runtime', 'deadline'])
def test_replay_rejects_wrong_real_trace_or_state(sample, defect):
    module = replay_module()
    args = request(sample)
    args['rows'] = copy.deepcopy(args['rows'])
    if defect in ('input', 'raw', 'action'):
        key = {'input':'encoded_input', 'raw':'raw_output', 'action':'action'}[defect]
        args['rows'][1][key] += np.float32(100)
    elif defect == 'scale-one':
        args['rows'][0]['action'][0] = np.tanh(args['rows'][0]['raw_output'][0])
    elif defect == 'dtype': args['rows'][1]['encoded_input'] = args['rows'][1]['encoded_input'].astype(np.float64)
    elif defect == 'shape': args['rows'][1]['encoded_input'] = args['rows'][1]['encoded_input'][:-1]
    elif defect == 'nonfinite': args['rows'][1]['raw_output'][0] = np.nan
    elif defect == 'duplicate': args['rows'][1]['tick'] = 0
    elif defect == 'drop': args['rows'].pop(1)
    elif defect == 'episode': args['rows'][0]['episode'] = 1
    elif defect == 'source-endpoint': args['source_snapshot']['policy']['hidden'] += np.float32(100)
    elif defect in ('parameters', 'graph'):
        values = (args['policy'].agent.parameters() if defect == 'parameters'
                  else args['policy'].agent.buffers())
        tensor = next(v for v in values if v.numel())
        with args['policy'].torch.no_grad(): tensor.add_(1)
    elif defect == 'runtime': args['source_snapshot']['identity']['torch']['threads'] = 2
    elif defect == 'deadline': args['deadline'] = time.monotonic() - 1
    before = snapshots.state_digest(args['policy']._state())
    with pytest.raises((ValueError, TimeoutError)):
        module._replay_rows(**args)
    assert snapshots.state_digest(args['policy']._state()) == before


def test_condition_rejects_wrong_acquired_hidden(sample):
    module = replay_module()
    args = request(sample, 'condition')
    args['source_snapshot']['policy']['hidden'] += np.float32(100)
    with pytest.raises(ValueError): module._replay_rows(**args)


def test_public_family_consumer_refuses_fixture_model_identity(sample):
    module = replay_module()
    with pytest.raises(ValueError, match='pinned'):
        module.replay_compact_cell(policy=sample['policy'], bundle={},
            raw_audit_receipt={}, source_snapshot=sample['source_snapshot'],
            deadline=time.monotonic() + 30)
