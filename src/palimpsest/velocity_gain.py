"""Isolated, snapshot-visible outgoing velocity changes for the audit pilot.

This adapter grants no sampling or runtime qualification. It never clips actions
or substitutes another condition's recorded inference.
"""
import copy
import json

from .flynn import FlynnPolicy


SCHEMA = 'flynn-velocity-gain-v1'
RATIOS = {1.: (1, 1), .5: (1, 2), .75: (3, 4), 1.25: (5, 4)}


def _canonical(value):
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ValueError('Policy provenance requires string keys')
        for child in value.values():
            _canonical(child)
    elif type(value) in (list, tuple):
        for child in value:
            _canonical(child)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class VelocityGainPolicy:
    """One actual FLYNN policy, with an immutable declared action gain.

    Snapshot code writes hidden/diagnostic fields through to the real policy.
    Native conversion and wheel clipping remain the environment's responsibility.
    """
    __slots__ = ('_policy', '_gain', '_base_provenance', '_base_encoding')
    _MUTABLE = frozenset(('hidden', 'failure_diagnostics', '_current_raw_output'))

    def __init__(self, policy, gain):
        if type(policy) is not FlynnPolicy:
            raise TypeError('An exact unwrapped FlynnPolicy is required')
        if type(gain) not in (int, float) or gain not in RATIOS:
            raise ValueError('Gain must be one of 1, 1/2, 3/4, 5/4')
        provenance = copy.deepcopy(policy.provenance)
        object.__setattr__(self, '_policy', policy)
        object.__setattr__(self, '_gain', float(gain))
        object.__setattr__(self, '_base_provenance', provenance)
        object.__setattr__(self, '_base_encoding', _canonical(provenance))

    def __setattr__(self, name, value):
        if name in self._MUTABLE:
            setattr(self._policy, name, value)
        else:
            raise AttributeError('Adapter configuration is read-only')

    def _check_identity(self):
        if type(self._policy) is not FlynnPolicy or _canonical(self._policy.provenance) != self._base_encoding:
            raise ValueError('Base policy identity changed')

    @property
    def gain(self):
        return self._gain

    @property
    def provenance(self):
        self._check_identity()
        numerator, denominator = RATIOS[self._gain]
        return {'schema': SCHEMA,
                'base_policy_class': type(self._policy).__module__ + '.' + type(self._policy).__qualname__,
                'base_policy_provenance': copy.deepcopy(self._base_provenance),
                'velocity_gain': {'numerator': numerator, 'denominator': denominator}}

    @property
    def agent(self):
        return self._policy.agent

    @property
    def torch(self):
        return self._policy.torch

    @property
    def device(self):
        return self._policy.device

    @property
    def dtype(self):
        return self._policy.dtype

    @property
    def hidden(self):
        return self._policy.hidden

    @property
    def failure_diagnostics(self):
        return self._policy.failure_diagnostics

    @property
    def _current_raw_output(self):
        return self._policy._current_raw_output

    def _state(self):
        return self._policy._state()

    def _restore(self, state):
        self._policy._restore(state)

    def reset(self):
        self._check_identity()
        self._policy.reset()

    def act(self, observation, check_parity=False):
        import numpy as np

        self._check_identity()
        before = self._policy._state()
        try:
            result = self._policy.act(observation, check_parity=check_parity)
            action = result['action']
            if (not isinstance(action, np.ndarray) or action.shape != (2,)
                    or action.dtype != np.float32 or not np.isfinite(action).all()):
                raise ValueError('Expected two finite float32 policy outputs')
            changed = action.copy()
            with np.errstate(over='ignore', invalid='ignore'):
                changed[0] = action[0] * np.float32(self._gain)
            if not np.isfinite(changed).all():
                raise ValueError('Velocity gain overflows the finite action range')
            return {**result, 'action': changed}
        except BaseException as error:
            self._policy._restore(before)
            self._policy.failure_diagnostics.update(adapter=SCHEMA,
                adapter_error_type=type(error).__name__)
            raise
