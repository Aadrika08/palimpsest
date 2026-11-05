"""Authored policy doubles: software semantics, never model qualification."""
import copy
import numpy as np
import pytest

from palimpsest import velocity_gain as module


class Policy:
    provenance = {'checkpoint_sha256': 'a' * 64}
    agent = object()
    torch = object()
    device = 'cpu'
    dtype = 'float32'

    def __init__(self):
        self.hidden = 0
        self.failure_diagnostics = {}
        self._current_raw_output = None
        self.calls = []
        self.action = np.array([2., -.0], dtype=np.float32)

    def _state(self):
        return self.hidden

    def _restore(self, state):
        self.hidden = state

    def reset(self):
        self.hidden = 0

    def act(self, observation, check_parity=False):
        self.calls.append((observation, check_parity))
        self.hidden += 1
        self.result = {'action': self.action, 'encoded_input': object(),
                       'raw_output': object(), 'parity': {'checked': check_parity}}
        return self.result


@pytest.fixture
def base(monkeypatch):
    monkeypatch.setattr(module, 'FlynnPolicy', Policy)
    return Policy()


@pytest.mark.parametrize('gain', [1, .5, .75, 1.25])
def test_one_inference_and_only_velocity_changes(base, gain):
    wrapped = module.VelocityGainPolicy(base, gain)
    observation = object()
    result = wrapped.act(observation, check_parity=True)
    assert base.calls == [(observation, True)]
    assert base.hidden == 1
    assert result['action'].dtype == np.float32
    assert result['action'][0] == np.float32(2 * gain)
    assert result['action'][1:].tobytes() == base.action[1:].tobytes()
    assert base.action.tobytes() == np.array([2., -.0], dtype=np.float32).tobytes()
    for key in ('encoded_input', 'raw_output', 'parity'):
        assert result[key] is base.result[key]


@pytest.mark.parametrize('gain', [True, False, 0, -1, float('nan'), float('inf'), .6, '1'])
def test_invalid_gain_refuses_before_inference(base, gain):
    with pytest.raises(ValueError):
        module.VelocityGainPolicy(base, gain)
    assert base.calls == []


@pytest.mark.parametrize('action', [np.array([np.nan, 0], dtype=np.float32),
    np.zeros(3, dtype=np.float32), np.array([1, 2], dtype=np.int64),
    np.array([np.finfo(np.float32).max, 0], dtype=np.float32)])
def test_rejected_output_rolls_back_without_retry(base, action):
    base.action = action
    wrapped = module.VelocityGainPolicy(base, 1.25)
    with pytest.raises(ValueError):
        wrapped.act(object())
    assert len(base.calls) == 1 and base.hidden == 0
    assert base.failure_diagnostics['adapter'] == 'flynn-velocity-gain-v1'


def test_snapshot_interface_mutations_reach_real_policy(base):
    wrapped = module.VelocityGainPolicy(base, .5)
    wrapped.hidden = 7
    wrapped.failure_diagnostics = {'restored': True}
    wrapped._current_raw_output = 'raw'
    assert base.hidden == 7 and base.failure_diagnostics == {'restored': True}
    assert base._current_raw_output == 'raw'
    assert wrapped.agent is base.agent and wrapped.torch is base.torch
    assert wrapped.device == base.device and wrapped.dtype == base.dtype
    wrapped._restore(3)
    assert wrapped._state() == 3
    wrapped.reset()
    assert base.hidden == 0


def test_gain_identity_is_defensive_readonly_and_detects_base_drift(base):
    wrapped = module.VelocityGainPolicy(base, .75)
    identity = wrapped.provenance
    assert identity['velocity_gain'] == {'numerator': 3, 'denominator': 4}
    identity['base_policy_provenance']['checkpoint_sha256'] = 'b' * 64
    assert wrapped.provenance['base_policy_provenance'] == base.provenance
    with pytest.raises(AttributeError):
        wrapped.gain = .5
    with pytest.raises(AttributeError):
        wrapped._gain = .5
    base.provenance = copy.deepcopy(base.provenance)
    base.provenance['checkpoint_sha256'] = 'b' * 64
    with pytest.raises(ValueError):
        wrapped.act(object())
    with pytest.raises(ValueError):
        _ = wrapped.provenance
    assert base.calls == []


def test_unregistered_and_nested_policy_refuse(base):
    with pytest.raises(TypeError):
        module.VelocityGainPolicy(object(), 1)
    with pytest.raises(TypeError):
        module.VelocityGainPolicy(module.VelocityGainPolicy(base, 1), .5)
