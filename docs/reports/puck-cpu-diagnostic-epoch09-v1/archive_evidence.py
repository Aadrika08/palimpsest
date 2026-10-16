"""Preserve authored09 source evidence; never invoke an installed allocation."""
import ast,hashlib,json,subprocess
from pathlib import Path
ROOT=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-diagnostic-epoch09-v1')
PACKET=ROOT/'docs/reports/puck-cpu-diagnostic-epoch09-v1'
record=Path('/tmp/palimpsest-epoch09-validation-record.json')
validation=json.loads(record.read_bytes());SOURCE=validation['source_commit']
assert validation['final_disjoint_cases']==673
pairs={}
def retain(original,name):
    original=Path(original)
    assert name not in pairs and not Path(name).is_absolute() and '..' not in Path(name).parts
    assert original.is_file() and not original.is_symlink() and original.stat().st_size<2*1024**2
    pairs[name]=original
fixture=ROOT/'runs/source-validation/epoch09-persistent01/tmp/test_authored09_binds_fifth_so0/authored-project'
base=fixture/'runs/puck-cpu-held-qualification-09'
config=json.loads((fixture/'authored-qualify09-configuration.json').read_bytes())
paths={r['path'] for r in config['sources']}
paths.update(('scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py'))
for label in ('private01','persistent01'):
    directory=ROOT/'runs/source-validation'/('epoch09-'+label)
    command=json.loads((directory/'command.json').read_bytes())['command']
    paths.update(x.split('::')[0] for x in command if x.startswith('tests/'))
seen=set()
while True:
    todo=sorted(p for p in paths if p.startswith('tests/') and p not in seen)
    if not todo:break
    for name in todo:
        seen.add(name)
        for node in ast.walk(ast.parse((ROOT/name).read_bytes())):
            if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith('test_'):
                relative='tests/'+node.module.replace('.','/')+'.py'
                assert (ROOT/relative).is_file(),relative
                paths.add(relative)
for name in sorted(paths):
    assert (ROOT/name).read_bytes()==subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT),name
    retain(ROOT/name,'source/'+name)
for row in validation['batches']:
    directory=Path(row['directory'])
    for name in ('command.json','stdout.txt','stderr.txt','terminal.json'):
        retain(directory/name,'validation/'+row['label']+'/'+name)
    for path in sorted((directory/'source').rglob('*')):
        if path.is_file():retain(path,'validation/'+row['label']+'/source/'+str(path.relative_to(directory/'source')))
retain(record,'validation-record.json')
for name in ('palimpsest-epoch09-design-review.json','palimpsest-epoch09-source-review.json','palimpsest-epoch09-validation-review.json'):
    retain(Path('/tmp')/name,'reviews/'+name)
retain('/tmp/palimpsest-epoch09-reviewed-plan.md','reviews/reviewed-plan.md')
for name in ('result.json','baseline-before.json','baseline-after.json','supervision.json','invocation.json',
             'configuration.json','resource-admission.json','control/worker-registration.json',
             'control/dependencies.json','logs/stdout.log','logs/stderr.log'):
    retain(base/name,'authored09/'+name)
for name in ('authored-qualify09-configuration.json','authored-qualify09-transport.json',
             'authored-qualify09-cli.stdout','authored-qualify09-cli.stderr',
             'authored-accounting09-api-audit.json','authored-diagnostic09-cli-audit.json',
             'authored-diagnostic09-cli-audit.stdout','authored-diagnostic09-cli-audit.stderr',
             'authored-accounting09-cli-audit-transport.json','authored-accounting09-no-cost-api-audit.json',
             'authored-qualify09-rerun-transport.json','authored-publication05-stage-cleanup.json'):
    retain(fixture/name,'authored09/'+name)
retain('/tmp/palimpsest-epoch09-run.py','validation/runner.py')
retain(ROOT/'docs/reports/puck-cpu-guard-accounting-v1/verify_evidence.py','verify_evidence.py')
retain(Path(__file__),'archive_evidence.py')
assert not PACKET.exists() and len(pairs)<200 and sum(p.stat().st_size for p in pairs.values())<8*1024**2
PACKET.mkdir();rows=[]
for name,original in sorted(pairs.items()):
    raw=original.read_bytes();target=PACKET/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw)
    rows.append(dict(archived_path=name,original_path=str(original),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
index=dict(kind='puck-diagnostic-epoch09-authored-evidence-v1',source_commit=SOURCE,
    source_paths=sorted(paths),artifacts=rows,artifact_count=len(rows),final_disjoint_authored_passes=673,
    production_changes=['scripts/qualify_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py'],
    runtime_qualified=False,actual09_controls_created=False,all_seven_release_gates_open=True)
with (PACKET/'evidence-index.json').open('x') as stream:json.dump(index,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps(dict(artifacts=len(rows),bytes=sum(r['size_bytes'] for r in rows),
    empty_files=sum(r['size_bytes']==0 for r in rows),source_paths=len(paths),source_commit=SOURCE,
    index_sha256=hashlib.sha256((PACKET/'evidence-index.json').read_bytes()).hexdigest()),sort_keys=True))
