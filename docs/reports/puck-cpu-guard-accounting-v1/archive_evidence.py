"""Archive finite authored diagnostics evidence; do not invoke an allocation."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-guard-accounting-v1')
PACKET=ROOT/'docs/reports/puck-cpu-guard-accounting-v1'
SOURCE='57e2e793edddc8fddc20b4af77e8a8a0035463a0'
record=Path('/tmp/palimpsest-guard-accounting-validation-record.json')
validation=json.loads(record.read_bytes())
assert validation['final_disjoint_cases']==304
pairs={}
def retain(original, relative):
    assert relative not in pairs and not Path(relative).is_absolute() and '..' not in Path(relative).parts
    original=Path(original)
    assert original.is_file() and not original.is_symlink()
    assert original.stat().st_size<2*1024**2
    pairs[relative]=original

source_paths={
    'scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py',
    'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py',
    *['src/palimpsest/'+name+'.py' for name in (
        '__init__','puck_worker_preflight','puck_runtime_qualification','puck_execution_files',
        'puck_dependency_files','puck_dependency_imports','puck_dependency_bindings',
        'puck_native_origins','puck_native_identity')],
}
for label in ('private01','persistent01'):
    command=json.loads((ROOT/'runs/source-validation'/('guard-accounting-'+label)/'command.json').read_bytes())
    source_paths.update(name for name in command['command'] if name.startswith('tests/') and name.endswith('.py'))
# Retain the finite transitive test fixture imports without importing them.
seen=set()
while True:
    todo=sorted(name for name in source_paths if name.startswith('tests/') and name not in seen)
    if not todo: break
    for name in todo:
        seen.add(name)
        tree=ast.parse((ROOT/name).read_bytes())
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith('test_'):
                relative='tests/'+node.module.replace('.','/')+'.py'
                assert (ROOT/relative).is_file(),relative
                source_paths.add(relative)
assert len(source_paths)<80
for name in sorted(source_paths):
    assert (ROOT/name).read_bytes()==subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT)
    retain(ROOT/name,'source/'+name)
for row in validation['batches']:
    directory=Path(row['directory'])
    for name in ('command.json','stdout.txt','stderr.txt','terminal.json'):
        retain(directory/name,'validation/'+row['label']+'/'+name)
    for path in sorted((directory/'source').rglob('*')):
        if path.is_file(): retain(path,'validation/'+row['label']+'/source/'+str(path.relative_to(directory/'source')))
retain(record,'validation-record.json')
for name in ('palimpsest-guard-accounting-source-review.json',
             'palimpsest-guard-accounting-source-review02.json',
             'palimpsest-guard-accounting-validation-review.json'):
    retain(Path('/tmp')/name,'reviews/'+name)
retain('/tmp/palimpsest-guard-accounting-reviewed-plan.md','reviews/reviewed-plan.md')
fixture=ROOT/'runs/source-validation/guard-accounting-persistent01/tmp/test_authored08_binds_fifth_so0/authored-project'
base=fixture/'runs/puck-cpu-held-qualification-08'
for name in ('result.json','baseline-before.json','baseline-after.json','supervision.json',
             'invocation.json','configuration.json','resource-admission.json',
             'control/worker-registration.json','control/dependencies.json','logs/stdout.log','logs/stderr.log'):
    retain(base/name,'authored08/'+name)
for name in ('authored-diagnostic08-cli-audit.json','authored-diagnostic08-cli-audit.stdout',
             'authored-diagnostic08-cli-audit.stderr','authored-qualify08-transport.json',
             'authored-qualify08-configuration.json'):
    retain(fixture/name,'authored08/'+name)
retain(ROOT/'docs/reports/puck-cpu-runtime-phase-trace-v1/verify_evidence.py','verify_evidence.py')
retain(Path(__file__),'archive_evidence.py')
assert not PACKET.exists()
assert len(pairs)<200 and sum(path.stat().st_size for path in pairs.values())<6*1024**2
PACKET.mkdir()
rows=[]
for name,original in sorted(pairs.items()):
    raw=original.read_bytes();target=PACKET/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw)
    rows.append(dict(archived_path=name,original_path=str(original),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
index=dict(kind='puck-guard-accounting-authored-evidence-v1',source_commit=SOURCE,
    source_paths=sorted(source_paths),artifact_count=len(rows),artifacts=rows,
    final_disjoint_authored_passes=304,source_review='GO_SCOPED',runtime_qualified=False,
    actual09_controls_created=False,all_seven_release_gates_open=True,
    preserved_consumed_attempts=list(range(1,9)))
with (PACKET/'evidence-index.json').open('x') as stream:json.dump(index,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps(dict(artifacts=len(rows),bytes=sum(r['size_bytes'] for r in rows),
    empty_files=sum(r['size_bytes']==0 for r in rows),source_paths=len(source_paths),source_commit=SOURCE,
    index_sha256=hashlib.sha256((PACKET/'evidence-index.json').read_bytes()).hexdigest()),sort_keys=True))
