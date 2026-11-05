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
