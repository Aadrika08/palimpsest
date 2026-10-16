"""Retain this authored diagnosis; never invoke runtime or study controls."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-guard-cost-v1')
PACKET = ROOT/'docs/reports/puck-cpu-guard-cost-v1'
SOURCE = '2a9db8d35af5ede17d3a676ec55296f008fd078a'
BASE = '2159cdf1d515513abdd36bdd5999019ea27ff39c'
SOURCE_PATHS = [
    'scripts/puck_worker_bootstrap.py',
    'tests/test_puck_guard_cost.py',
    'tests/test_puck_worker_bootstrap.py',
    'tests/test_puck_worker_dependencies.py',
    *['src/palimpsest/'+name+'.py' for name in (
        'puck_execution_files', 'puck_dependency_files', 'puck_dependency_imports',
        'puck_dependency_bindings', 'puck_native_origins', 'puck_native_identity',
        'puck_runtime_qualification')],
]
assert not subprocess.check_output(['git','diff',BASE,'--','scripts','src'],cwd=ROOT)
PACKET.mkdir(exist_ok=False)
artifacts = []
def retain(original, relative):
    original = Path(original)
    assert not original.is_symlink() and original.is_file()
    raw = original.read_bytes()
    target = PACKET/relative
    assert not target.exists() and not Path(relative).is_absolute() and '..' not in Path(relative).parts
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    artifacts.append(dict(archived_path=relative, original_path=str(original),
        size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
for relative in SOURCE_PATHS:
    raw = (ROOT/relative).read_bytes()
    assert raw == subprocess.check_output(['git','show',SOURCE+':'+relative],cwd=ROOT)
    retain(ROOT/relative, 'source/'+relative)
runs = ROOT/'runs/puck-cpu-guard-cost-v1'
for label in ('baseline01', 'direct-dependency01', 'hoisted-whitelist01'):
    for name in ('command.json','stdout.txt','stderr.txt','terminal.json'):
        retain(runs/label/name, 'validation/'+label+'/'+name)
for path in sorted((runs/'experimental-sources').iterdir()):
    retain(path, 'experimental-sources/'+path.name)
retain(runs/'comparison.json','comparison.json')
retain('/tmp/palimpsest-guard-cost-tool-terminals.json','tool-terminals.json')
retain('/tmp/palimpsest-guard-cost-outcome-review.json','outcome-review.json')
retain(ROOT/'docs/reports/puck-cpu-runtime-phase-trace-v1/verify_evidence.py','verify_evidence.py')
retain(Path(__file__), 'archive_evidence.py')
assert len(artifacts) <= 64 and sum(row['size_bytes'] for row in artifacts) < 2*1024**2
index=dict(kind='puck-authored-guard-cost-evidence-v1', source_commit=SOURCE,
    unchanged_production_base=BASE, source_paths=SOURCE_PATHS,
    production_changed=False, runtime_qualified=False, actual09_controls_created=False,
    all_seven_release_gates_open=True, decision='retain-production-guard',
    artifacts=artifacts, artifact_count=len(artifacts))
(PACKET/'evidence-index.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(artifacts=len(artifacts), bytes=sum(row['size_bytes'] for row in artifacts),
    empty_files=sum(row['size_bytes']==0 for row in artifacts),
    index_sha256=hashlib.sha256((PACKET/'evidence-index.json').read_bytes()).hexdigest())))
