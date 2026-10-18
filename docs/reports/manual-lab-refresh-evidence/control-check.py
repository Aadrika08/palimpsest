"""Finite controls; one harmless Python cleanup fixture, no native/browser/export."""
import json
import importlib.util
from pathlib import Path
import tempfile
import signal
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

from palimpsest.storage import StorageBudget, StorageLimits

spec = importlib.util.spec_from_file_location('manual_refresh_controls', Path(__file__).with_name('launch.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='palimpsest-manual-control-check-', dir='/tmp') as temporary:
    phase = Path(temporary)
    budget = StorageBudget((phase,), StorageLimits(max_bytes=16 * 1024**2, min_free_bytes=0))
    with patch.object(module, 'PHASE', phase), patch.object(module, 'BUDGET', budget), \
            patch.object(module.subprocess, 'Popen', side_effect=AssertionError('No subprocess may launch')):
        (phase / 'launched.json').write_text('{}')
        try:
            module.launch()
        except AssertionError as error:
            assert 'Consumed allocation' in str(error)
        else:
            raise AssertionError('Retry was admitted')
        module.checked_wait(SimpleNamespace(poll=lambda: 0, returncode=0), 1, time.monotonic())
        try:
            module.checked_wait(SimpleNamespace(poll=lambda: 3, returncode=3), 1, time.monotonic())
            raise AssertionError('Nonzero child accepted')
        except RuntimeError as error:
            assert 'Child exited 3' in str(error)
        pending = SimpleNamespace(poll=lambda: None, returncode=None)
        try:
            module.checked_wait(pending, -1, time.monotonic())
            raise AssertionError('Expired child admitted')
        except TimeoutError:
            pass
        (phase / 'server.stdout.log').write_bytes(b'x' * (1024**2 + 1))
        try:
            module.checked_wait(pending, 1, time.monotonic())
            raise AssertionError('Oversized server log admitted')
        except RuntimeError as error:
            assert 'Server log limit exceeded' in str(error)
with tempfile.TemporaryDirectory(prefix='palimpsest-manual-cleanup-check-', dir='/tmp') as temporary:
    phase = Path(temporary)
    (phase / 'registration.json').write_text(json.dumps({'sources': {}}))
    budget = StorageBudget((phase,), StorageLimits(max_bytes=16 * 1024**2, min_free_bytes=0))
    child = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(30)'])
    original = signal.getsignal(signal.SIGTERM)
    try:
        with patch.object(module, 'PHASE', phase), patch.object(module, 'BUDGET', budget), \
                patch.object(module, 'pins', return_value={}), \
                patch.object(module, 'observe', side_effect=OSError('simulated inventory error')), \
                patch.object(module.subprocess, 'Popen', return_value=child):
            assert module.worker() == 1
        assert child.poll() is not None, 'Observation failure bypassed child cleanup'
        receipt = json.loads((phase / 'worker.json').read_text())
        assert receipt['status'] == 'failed' and receipt['cleanup_observation_failure']['type'] == 'OSError'
    finally:
        signal.signal(signal.SIGTERM, original)
        if child.poll() is None:
            child.kill()
            child.wait(timeout=3)
print('Marker, child failure, deadline, log cap and observation-failure cleanup controls passed.')
