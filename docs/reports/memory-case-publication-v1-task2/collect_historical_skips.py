"""Read-only collection audit; adds no marks, fixtures, acceptance or bypass."""
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'src'), str(ROOT)]
MODULES = ['tests/test_memory_family_case_publication_v1.py',
           'tests/test_memory_family_retained_case_v1.py',
           'tests/test_memory_family_retained_condition_v1.py',
           'tests/test_memory_family_retained_source_v4.py',
           'tests/test_memory_family_producer_v4.py',
           'tests/test_memory_family_condition_close_v4.py',
           'tests/test_memory_family_oracle_admission_v4.py',
           'tests/test_memory_family_replay_custody_v4.py']

class Recorder:
    def pytest_collection_finish(self, session):
        rows = [{'nodeid':item.nodeid,'reasons':[m.kwargs.get('reason','') for m in item.iter_markers('skip')]}
                for item in session.items if any(item.iter_markers('skip'))]
        payload = {'scope':'Collection-only audit of existing skip marks; no fixture execution or mark changes.',
                   'collected':len(session.items),'skipped_count':len(rows),'skipped':rows}
        (Path(__file__).parent/'historical-skip-nodeids.json').write_text(json.dumps(payload,indent=2)+'\n')
        assert len(rows)==186, 'Selected skip set differs from captured canonical run'

if __name__=='__main__':
    raise SystemExit(pytest.main(['--collect-only','-q','-p','no:cacheprovider',*MODULES],plugins=[Recorder()]))
