"""Run the trusted-process regressions in a fresh, unthreaded interpreter."""
import os
from pathlib import Path
import subprocess
import sys


def test_accounting_ownership_regressions_are_in_the_canonical_suite(tmp_path):
    root=Path(__file__).resolve().parents[1]
    command=[sys.executable,'-B','-m','unittest','discover','-s',
        'paper/studies/change_audit_v1/tests','-p','test_process.py']
    env={**os.environ,'PYTHONPATH':str(root),'PYTHONDONTWRITEBYTECODE':'1',
         'TMPDIR':str(tmp_path),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
    result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=120)
    (tmp_path/'accounting-regressions.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
