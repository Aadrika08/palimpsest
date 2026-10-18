"""No exporters: check unsafe paths and retained one-shot failure publication."""
import contextlib
import importlib.util
import json
from pathlib import Path
import signal
import tempfile
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('artwork_prepare', Path(__file__).with_name('prepare.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
for name in ('../escape', '/tmp/escape', 'runs/../escape', 'runs//escape', 'runs\\escape', ''):
    try:
        p.relative(name)
    except ValueError:
        pass
    else:
        raise AssertionError('unsafe archive member admitted: ' + name)
assert str(p.relative('runs/abcd/recording/manifest.json')) == 'runs/abcd/recording/manifest.json'


class UnavailableLease:
    def check(self, *args, **kwargs):
        return {}

    @contextlib.contextmanager
    def lock(self):
        raise OSError('injected unavailable writer lease')
        yield


def write(path, value, budget):
    path.write_text(json.dumps(value))


published = json.loads(p.REUSED_INDEX.read_text())['artifact_files']
def digest(path):
    return published[path.name] if path.parent == p.REVIEW else {'size_bytes': 0, 'sha256': '0' * 64}


with tempfile.TemporaryDirectory(prefix='artwork-controls-') as folder:
    phase = Path(folder)
    handler = signal.getsignal(signal.SIGTERM)
    with patch.object(p, 'PHASE', phase), patch.object(p, 'BUDGET', UnavailableLease()), \
         patch.object(p, 'selections', return_value=([], {})), \
         patch.object(p, 'digest', side_effect=digest), \
         patch.object(p.h, 'sources', return_value={}), patch.object(p.h, 'admit', return_value={}), \
         patch.object(p.h, 'write_json', side_effect=write), \
         patch.object(p.shutil, 'disk_usage', return_value=type('Space', (), {'free': 8 * 1024**3})()), \
         patch.object(p.h, 'bounded_process', side_effect=AssertionError('child must not launch')):
        assert p.main() == 1
        result = json.loads((phase / 'result.json').read_text())
        assert result['status'] == 'failed' and 'injected unavailable writer lease' in result['error']
        assert any('writer lease:' in error for error in result['finalization_errors'])
        assert (phase / 'launched.json').is_file()
        try:
            p.main()
        except ValueError as error:
            assert 'namespace consumed' in str(error)
        else:
            raise AssertionError('failed invocation reopened')
    assert signal.getsignal(signal.SIGTERM) == handler
print('Unsafe paths refused; failure receipt/marker retained; retry refused; SIGTERM restored. No child/export.')
