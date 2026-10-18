"""Run authored cases with an isolated experimental bootstrap copy only."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root/'tests'))
import test_puck_worker_bootstrap
import pytest
test_puck_worker_bootstrap.SCRIPT = Path(sys.argv[1]).resolve()
raise SystemExit(pytest.main(['-q', '-s', '-p', 'no:cacheprovider', '--basetemp', sys.argv[2], str(root/'tests/test_puck_guard_cost.py')]))
