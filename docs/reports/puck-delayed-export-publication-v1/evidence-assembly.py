from pathlib import Path
import hashlib,json,re,stat,subprocess,sys

ROOT=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
BASE='c9adf32ba54854d2edaec792abf8c0c375686814'
NAME='puck-delayed-export-publication-v1'
SOURCE=['src/palimpsest/puck_dependency_bindings.py','src/palimpsest/puck_dependency_imports.py',
'scripts/qualify_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_held_runtime.py',
'tests/test_puck_published_exports.py','tests/test_puck_published_export_receipts.py',
'tests/test_puck_cpu_held_parent_integration.py','tests/test_puck_published_export_integration.py']
CODE=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert CODE!=BASE
OUT=ROOT/'docs/reports'/NAME
OUT.mkdir(parents=True,exist_ok=False)
entries=[]
def canonical(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def pin(raw):return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def copy(src,rel):
    assert stat.S_ISREG(src.lstat().st_mode),src
    raw=src.read_bytes();target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(raw);assert target.read_bytes()==raw==src.read_bytes()
    entries.append(dict(path=rel,original=str(src),**pin(raw)))
for f in SOURCE:
    raw=(ROOT/f).read_bytes()
    assert subprocess.check_output(['git','show',CODE+':'+f],cwd=ROOT)==raw
    copy(ROOT/f,'source/'+f)
copy(Path('/tmp/palimpsest-delayed-export-check.py'),'test-driver.py')
copy(Path(__file__),'evidence-assembly.py')
diff=Path('/tmp/palimpsest-delayed-export-publication-source.diff')
assert not diff.exists()
diff.write_bytes(subprocess.check_output(['git','diff',BASE,CODE,'--',*SOURCE],cwd=ROOT))
copy(diff,'source.diff')
validation=ROOT/'runs/source-validation/delayed-exports-v1'
runs={}
for folder in sorted(validation.iterdir()):
    if not folder.is_dir():continue
    assert (folder/'result.json').is_file(),folder
    value=json.loads((folder/'result.json').read_bytes())
    output=(folder/'stdout.log').read_text()
    lines=output.splitlines()
    summary=next((s for s in reversed(lines) if re.search(r'\b(?:passed|failed|deselected)\b.*\bin [\d.]+s',s)),None)
    runs[folder.name]=dict(value,pytest_summary=summary)
    for leaf in ['command.json','result.json','stdout.log','stderr.log']:
        copy(folder/leaf,'validation/'+folder.name+'/'+leaf)
    for p in sorted(folder.rglob('*')):
        if not p.is_file() or p.is_symlink():continue
        rel=p.relative_to(folder)
        if rel.parts[0]=='source' or str(rel)=='original-test-source.py':
            copy(p,'validation/'+folder.name+'/'+str(rel))
for name,count in [('isolated-bindings-03',263),('isolated-persistent-parent-01',None)]:
    assert runs[name]['normal_return'] is True and runs[name]['returncode']==0,runs[name]
    assert runs[name]['pytest_summary'] and 'failed' not in runs[name]['pytest_summary']
    if count is not None:assert re.search(r'\b'+str(count)+r' passed\b',runs[name]['pytest_summary'])
projects=[p for p in (validation/'isolated-persistent-parent-01/tmp').glob('test_authored_publication_surv*/authored-project') if not p.parent.is_symlink()]
assert len(projects)==1,projects
project=projects[0]
for p in sorted(project.rglob('*')):
    if p.is_symlink():raise AssertionError('Unexpected authored symlink: '+str(p))
    if p.is_file():copy(p,'authored-publication/'+str(p.relative_to(project)))
observations=json.loads((project/'authored-publication-test-observations.json').read_bytes())
cleanup=json.loads((project/'authored-published-stage-cleanup.json').read_bytes())
assert observations['actual_vendor_imports'] is False and cleanup['absent'] is True
assert observations['prepare_audit']==observations['qualify_audit']=='PASS'
index=dict(kind='puck-delayed-export-publication-evidence-index-v1',source_code_commit=CODE,
           scope='AUTHORED source/fixture evidence only; no installed vendor or actual allocation acceptance',
           file_count=len(entries),total_bytes=sum(r['size_bytes'] for r in entries),
           entries=sorted(entries,key=lambda r:r['path']))
index_raw=canonical(index);(OUT/'evidence-index.json').write_bytes(index_raw)
report=dict(kind='puck-delayed-export-publication-source-report-v1',status='source verified',
 source_base_commit=BASE,source_code_commit=CODE,
 source_files=[dict(path=f,**pin((ROOT/f).read_bytes())) for f in SOURCE],
 evidence_index=dict(path=NAME+'/evidence-index.json',**pin(index_raw)),verification=runs,
 authored_publication_observations=observations,authored_stage_cleanup=cleanup,
 independent_source_review='No material findings after exact-innermost-phase delegate-growth correction; source-only review',
 actual05_configuration_created=False,actual05_invoked=False,actual04_failed_consumed=True,
 real_profile_changed=False,installed_runtime_data_changed=False,runtime_qualified=False,
 collection_authorized=False,study_authorized=False,native_authorized=False,executable=False,
 all_seven_release_gates_open=True,qualification_claims=[])
(ROOT/'docs/reports'/ (NAME+'.json')).write_bytes(canonical(report))
print(json.dumps(dict(source_code_commit=CODE,file_count=index['file_count'],total_bytes=index['total_bytes'],evidence_index=pin(index_raw),final_runs={k:runs[k] for k in ('isolated-bindings-03','isolated-persistent-parent-01')}),sort_keys=True))
