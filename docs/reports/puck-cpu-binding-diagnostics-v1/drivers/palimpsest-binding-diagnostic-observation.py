from pathlib import Path
import fcntl
import hashlib
import json
import os
import sys
import time

root = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
sys.path[:0] = [str(root / 'tests'), str(root / 'src')]
from test_puck_dependency_profile import fixture_profile
from test_puck_worker_dependencies import dependency_fixture

out = root / 'runs/source-validation/cpu-binding-diagnostics-v1/authored-observation-01'
out.mkdir(parents=True, exist_ok=False)
scratch = Path('/tmp/palimpsest-cpu-binding-diagnostics-observation-01')
scratch.mkdir(exist_ok=False)

def mutate(deps, package):
    profile = fixture_profile(deps, package)
    profile['exports'][1]['attributes'] = ['nested', 'unavailable']

with (root / 'runs/source-validation/qualification-amendment03-test.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    before = time.monotonic()
    result, _ = dependency_fixture(scratch,
        'import fixture_dep.producer\nraise AssertionError("AFTER_IMPORT_RAN")', mutate=mutate)
    elapsed = time.monotonic() - before
(out / 'worker.stdout').write_text(result.stdout)
(out / 'worker.stderr').write_text(result.stderr)
assert result.returncode != 0 and result.stdout == ''
for value in ["producer='fixture_dep.producer'", "phase='module_exec'",
              "export='fixture_dep.cache_name'", "attributes=['nested', 'unavailable']",
              "component 'unavailable' at index 1", 'The above exception was the direct cause']:
    assert value in result.stderr
assert 'AFTER_IMPORT_RAN' not in result.stderr and 'HOOK' not in result.stderr
publication = {
    'kind': 'authored-export-binding-failure-observation-v1',
    'scope': 'authored held Python producer only; no installed CPU stack, actual qualification or scientific allocation',
    'observer_status': 'PASS', 'worker_returncode': result.returncode,
    'worker_command': result.args, 'elapsed_seconds': elapsed,
    'stdout': {'size_bytes': len(result.stdout.encode()), 'sha256': hashlib.sha256(result.stdout.encode()).hexdigest()},
    'stderr': {'size_bytes': len(result.stderr.encode()), 'sha256': hashlib.sha256(result.stderr.encode()).hexdigest()},
    'actual03_failed_consumed': True, 'actual04_created': False,
    'qualification_claims': [], 'runtime_qualified': False,
}
(out / 'result.json').write_text(json.dumps(publication, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: publication[k] for k in ['observer_status', 'worker_returncode', 'elapsed_seconds', 'stdout', 'stderr', 'scope']}))
