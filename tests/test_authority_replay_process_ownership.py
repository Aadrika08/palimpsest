"""Include replay/campaign process ownership regressions in hosted checks."""
import os
from pathlib import Path
import subprocess
import sys


def test_replay_process_ownership_regressions_are_in_the_canonical_suite(tmp_path):
    root=Path(__file__).resolve().parents[1]
    command=[sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',
        'paper/studies/authority_replay_v1/tests/test_repeatability_process_ownership.py',
        'paper/studies/authority_replay_v1/tests/test_repeatability.py',
        'paper/studies/authority_replay_v1/tests/test_campaign.py',
        '--basetemp',str(tmp_path/'owned-processes')]
    env={**os.environ,'PYTHONPATH':os.pathsep.join((str(root),str(root/'src'))),
         'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(tmp_path),
         'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
    result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=120)
    (tmp_path/'replay-ownership-regressions.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
