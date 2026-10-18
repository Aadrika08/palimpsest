"""Pure frozen collection clock accounting; this never grants execution.

No process, file, model or native observations are made. Callers must separately
supervise the absolute hard deadline. Bucket time cannot be transferred. Control
gaps before the first owner use pre_owner_admission; between owners use
launch_reap; after the last owner before return use reduction. Gaps during return
use the next return bucket, and after return_guard use return_guard itself.
"""
from contextlib import contextmanager
import copy
import math
import time


_PARENT = {'pre_owner_admission': 20, 'launch_reap': 20, 'reduction': 10}
_RETURN = {'final_recheck': 15, 'publication': 20, 'release': 10, 'return_guard': 5}


class CollectionClockLedger:
    """One-shot source ledger with a callable clock seam, never mutable caps."""

    def __init__(self, *, clock=time.monotonic):
        if not callable(clock):
            raise ValueError('Collection clock must be callable')
        self._clock = clock
        self._state = 'active'
        self._failure = None
        self._active = None
        self._last = None
        self._start = self._sample()
        self._used = {name: 0.0 for name in (*_PARENT, *_RETURN)}
        self._child_seconds = 0.0
        self._owners = []
        self._return_index = 0

    def _poison(self, message):
        if self._state != 'completed':
            self._state = 'failed'
            if self._failure is None:
                self._failure = message

    def _sample(self):
        try:
            value = self._clock()
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or value < 0 or self._last is not None and value < self._last):
                raise ValueError('Collection clock is nonfinite, invalid or regressed')
            self._last = value
            return value
        except BaseException as error:
            self._poison(str(error))
            raise

    def _check_stage(self, value):
        elapsed = value - self._start
        if elapsed > 2270:
            raise TimeoutError('Collection hard stage allocation exceeded')
        limit = 2260 if self._return_index or self._active in _RETURN else 2210
        if elapsed > limit:
            raise TimeoutError('Collection normal/internal stage allocation exceeded')

    def _available(self):
        if self._state != 'active':
            raise RuntimeError('Collection clock ledger is failed or completed')
        if self._active is not None:
            self._poison('Nested collection intervals are forbidden')
            raise RuntimeError('Nested collection intervals are forbidden')

    def _charge(self, name, elapsed):
        self._used[name] += elapsed
        if self._used[name] > {**_PARENT, **_RETURN}[name]:
            raise TimeoutError('Collection phase allocation exceeded: ' + name)

    def _control_sample(self):
        previous = self._last
        value = self._sample()
        if self._return_index:
            name = tuple(_RETURN)[min(self._return_index, 3)]
        elif not self._owners:
            name = 'pre_owner_admission'
        elif len(self._owners) < 12:
            name = 'launch_reap'
        else:
            name = 'reduction'
        self._charge(name, value - previous)
        self._check_stage(value)
        return value

    def _begin(self, name, ordinal=None):
        self._available()
        try:
            if name == 'child':
                if (type(ordinal) is not int or ordinal != len(self._owners)
                        or not 0 <= ordinal < 12 or self._return_index):
                    raise ValueError('Collection child must have the next exact ordinal')
            elif name in _RETURN:
                if (len(self._owners) != 12 or self._return_index >= 4
                        or name != tuple(_RETURN)[self._return_index]):
                    raise ValueError('Ordered return phases require all twelve owners')
            elif name not in _PARENT or self._return_index:
                raise ValueError('Unknown or misplaced collection phase')
            elif (name == 'pre_owner_admission' and self._owners
                    or name == 'reduction' and len(self._owners) != 12):
                raise ValueError('Collection parent phase is misplaced')
            started = self._control_sample()
            self._active = name
            return started
        except BaseException as error:
            self._poison(str(error))
            raise

    def _finish(self, name, started, ordinal=None):
        finished = self._sample()
        elapsed = finished - started
        if name == 'child':
            self._child_seconds += elapsed
            if elapsed > 180 or self._child_seconds > 2160:
                raise TimeoutError('Collection child allocation exceeded')
        else:
            self._charge(name, elapsed)
        self._check_stage(finished)
        if self._state != 'active':
            raise RuntimeError('Collection clock ledger was poisoned within its interval')
        if name == 'child':
            self._owners.append({'ordinal': ordinal,
                'owner_id': f'collection-{6110 + ordinal // 3}-seed-{21 + ordinal % 3}',
                'scene_id': 6110 + ordinal // 3, 'model_seed': 21 + ordinal % 3,
                'elapsed_seconds': elapsed})
        elif name in _RETURN:
            self._return_index += 1

    @contextmanager
    def _interval(self, name, ordinal=None):
        started = self._begin(name, ordinal)
        try:
            yield
        except BaseException as error:
            self._poison(str(error))
            try:
                self._finish(name, started, ordinal)
            except BaseException:
                pass  # Preserve the original body failure; failed receipts never grant success.
            raise
        else:
            try:
                self._finish(name, started, ordinal)
            except BaseException as error:
                self._poison(str(error))
                raise
        finally:
            self._active = None

    def phase(self, name):
        if type(name) is not str:
            self._poison('Collection phase must be an exact string')
            raise ValueError('Collection phase must be an exact string')
        return self._interval(name)

    def child(self, ordinal):
        return self._interval('child', ordinal)

    def complete(self):
        self._available()
        try:
            if len(self._owners) != 12 or self._return_index != 4:
                raise ValueError('Collection completion requires twelve owners and all return phases')
            self._control_sample()
            result = self.receipt()
            # Include defensive receipt construction, rather than closing first
            # and making an arbitrarily delayed return look successful.
            self._control_sample()
            result['elapsed_seconds'] = self._last - self._start
            for name, bucket in result['buckets'].items():
                bucket['used_seconds'] = self._used[name]
            self._state = 'completed'
            result['status'] = 'completed'
            return result
        except BaseException as error:
            self._poison(str(error))
            raise

    def receipt(self):
        """Defensive snapshot of last observation; obtaining it does not sample time."""
        return copy.deepcopy({'kind': 'puck-collection-clock-ledger-v1',
            'status': self._state, 'failure': self._failure,
            'elapsed_seconds': self._last - self._start,
            'child_seconds': self._child_seconds, 'owners': self._owners,
            'buckets': {name: {'limit_seconds': limit, 'used_seconds': self._used[name]}
                for name, limit in {**_PARENT, **_RETURN}.items()},
            'stage_limits': {'internal_seconds': 2210, 'normal_seconds': 2260, 'hard_seconds': 2270},
            'qualification_claims': [], 'executable': False,
            'collection_admission': False, 'native_execution': False})
