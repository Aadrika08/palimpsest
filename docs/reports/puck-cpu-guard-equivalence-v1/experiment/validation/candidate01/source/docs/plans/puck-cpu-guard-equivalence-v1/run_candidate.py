"""Select one experimental bootstrap for authored semantic tests only."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'tests'))
import test_puck_worker_bootstrap
import pytest
test_puck_worker_bootstrap.SCRIPT=Path(sys.argv[1]).resolve()
raise SystemExit(pytest.main(sys.argv[2:]))
