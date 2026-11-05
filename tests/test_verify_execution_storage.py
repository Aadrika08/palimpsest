"""Optional study quota covers both workers and auxiliary outputs."""
from pathlib import Path
import pytest
import verify_execution
from palimpsest.storage import StorageLimitError


def test_optional_budget_preserves_default_and_counts_shared_worker_root(tmp_path):
    assert hasattr(verify_execution, 'worker_budget'), 'optional worker budget missing'
    assert verify_execution.worker_budget({'output': str(tmp_path)}) is None
    root = tmp_path / 'unit'
    source, restored = root / 'source', root / 'restored'
    source.mkdir(parents=True)
    restored.mkdir()
    (source / 'held').write_bytes(b'x' * 11)
    config = {'storage_root': str(root), 'storage_max_bytes': 20, 'minimum_free_bytes': 0}
    budget = verify_execution.worker_budget(config)
    verify_execution.write_payload(restored / 'ok', b'y' * 9, budget)
    assert (restored / 'ok').read_bytes() == b'y' * 9
    with pytest.raises(StorageLimitError):
        verify_execution.write_payload(restored / 'refused', b'z', budget)
    assert not (restored / 'refused').exists()


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_scientific_comparator_rejects_nonfinite_without_poisoning_json(value):
    import json
    import numpy as np
    errors, divergences = {}, []
    with pytest.raises(ValueError, match='[Nn]onfinite'):
        verify_execution.compare_array(np.asarray([value], np.float32), np.asarray([value], np.float32),
                                       'camera', 8, errors, divergences)
    json.dumps({'errors': errors, 'divergences': divergences}, allow_nan=False)


def test_verifier_retains_structured_storage_failure(tmp_path, monkeypatch):
    import json
    def denied(*args, **kwargs):
        raise StorageLimitError('unit quota')
    monkeypatch.setattr(verify_execution, 'bounded_process', denied)
    report = verify_execution.verify({'output': str(tmp_path / 'unit'), 'timeout': 10,
                                      'controller': 'flynn', 'device': 'cpu', 'prefix': 8, 'continuation': 100})
    assert report['status'] == 'failed'
    assert report['resource_boundary']['type'] == 'StorageLimitError'
    assert json.loads((tmp_path / 'unit/verification.json').read_text()) == report


def test_worker_error_preserves_inner_storage_failure(tmp_path, monkeypatch):
    import json
    def failed_worker(command, output, *args, **kwargs):
        output.mkdir()
        (output / 'worker-error.json').write_text(json.dumps({'type': 'StorageLimitError', 'message': 'inner quota'}))
        return {'status': 'failed', 'returncode': 1}
    monkeypatch.setattr(verify_execution, 'bounded_process', failed_worker)
    report = verify_execution.verify({'output': str(tmp_path / 'unit'), 'timeout': 10,
                                      'controller': 'flynn', 'device': 'cpu', 'prefix': 8, 'continuation': 100})
    assert report['status'] == 'failed'
    assert report['resource_boundary'] == {'type': 'StorageLimitError', 'message': 'inner quota'}


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_continuation_rejects_nonfinite_source_prefix_before_filter(tmp_path, monkeypatch, value):
    import numpy as np
    from palimpsest import records
    monkeypatch.setattr(records, 'iter_ticks', lambda path: iter([{'tick': np.asarray(0), 'camera': np.asarray([value], np.float32)}]))
    with pytest.raises(ValueError, match='Nonfinite'):
        verify_execution.compare(tmp_path, {'prefix': 8, 'continuation': 100, 'controller': 'flynn', 'device': 'cpu'})


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_scientific_row_validation_rejects_nonfinite(value):
    import numpy as np
    assert hasattr(verify_execution, 'validate_scientific_rows')
    with pytest.raises(ValueError, match='Nonfinite'):
        verify_execution.validate_scientific_rows([{'tick': np.asarray(0), 'camera': np.asarray([value], np.float32)}])
