from pathlib import Path
import hashlib,json,os,re,stat,subprocess
ROOT=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
BASE='27a5c134613747c8c782829b8084834e92a53d66';CODE='92ef33114c535a7d039e31ba6ed34da29cc56d79';PLAN='8968023b14d4c466d75fa196ab2f3417348ff52b'
NAME='puck-cpu-held-qualification-amendment-05';OUT=ROOT/'docs/reports'/NAME;OUT.mkdir(parents=True,exist_ok=False)
SOURCE=['scripts/qualify_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py','tests/test_puck_cpu_held_amendment05.py','tests/test_puck_cpu_held_amendment05_integration.py','tests/test_puck_cpu_held_parent_integration.py','tests/test_puck_cpu_held_observer.py']
entries=[]
def canonical(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def pin(raw):return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def copy(src,rel):
 assert stat.S_ISREG(src.lstat().st_mode),src
 raw=src.read_bytes();p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 assert p.read_bytes()==raw==src.read_bytes()
 entries.append(dict(path=rel,original=str(src),**pin(raw)))
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==CODE
for f in SOURCE:
 assert subprocess.check_output(['git','show',CODE+':'+f],cwd=ROOT)==(ROOT/f).read_bytes()
 copy(ROOT/f,'source/'+f)
for f in ['docs/plans/puck-cpu-held-qualification-amendment-05.md','docs/plans/puck-cpu-autograd-publication-profile-v1.json']:
 copy(ROOT/f,'plan/'+Path(f).name)
for f in sorted((ROOT/'docs/plans/puck-cpu-autograd-publication-profile-v1').rglob('*')):
 if f.is_file():copy(f,'plan/profile-source/'+str(f.relative_to(ROOT/'docs/plans/puck-cpu-autograd-publication-profile-v1')))
for src,rel in [('/tmp/palimpsest-amendment05-source-check.py','test-driver.py'),('/tmp/palimpsest-amendment05-metadata-edit.py','implementation/metadata-edit.py'),('/tmp/palimpsest-amendment05-projection-edit.py','implementation/projection-edit.py'),('/tmp/palimpsest-build-autograd-profile.py','implementation/build-static-profile.py'),(__file__,'evidence-assembly.py')]:copy(Path(src),rel)
diff=Path('/tmp/palimpsest-amendment05-source.diff');assert not diff.exists();diff.write_bytes(subprocess.check_output(['git','diff',BASE,CODE,'--',*SOURCE],cwd=ROOT));copy(diff,'source.diff')
validation=ROOT/'runs/source-validation/cpu-amendment05';runs={}
for folder in sorted(validation.iterdir()):
 if not folder.is_dir():continue
 value=json.loads((folder/'result.json').read_bytes());output=(folder/'stdout.log').read_text()
 summary=next((s for s in reversed(output.splitlines()) if re.search(r'\b(?:passed|failed)\b.*\bin [\d.]+s',s)),None)
 runs[folder.name]=dict(value,pytest_summary=summary)
 for leaf in ['command.json','result.json','stdout.log','stderr.log']:copy(folder/leaf,'validation/'+folder.name+'/'+leaf)
for label,folder in [('red-unit-01','/tmp/palimpsest-amendment05-red-unit-source'),('isolated-persistent-red-integration-01','/tmp/palimpsest-amendment05-red-integration-source')]:
 for p in sorted(Path(folder).rglob('*')):
  if p.is_file():copy(p,'validation/'+label+'/source/'+str(p.relative_to(folder)))
for label in ['green-unit-01','isolated-persistent-green-integration-02','isolated-persistent-affected-01']:
 assert runs[label]['normal_return'] and runs[label]['returncode']==0 and 'failed' not in runs[label]['pytest_summary']
assert runs['isolated-persistent-affected-01']['pytest_summary'].startswith('395 passed')
project=validation/'isolated-persistent-affected-01/tmp/test_authored05_corrects_only_0/authored-project';assert project.is_dir()
for p in sorted(project.rglob('*')):
 assert not p.is_symlink(),p
 if p.is_file():copy(p,'authored05/'+str(p.relative_to(project)))
obs=json.loads((project/'authored-publication05-observations.json').read_bytes());cleanup=json.loads((project/'authored-publication05-stage-cleanup.json').read_bytes())
assert obs['actual_vendor_imports'] is False and cleanup['absent'] is True
actual=Path('/home/utkarsh/.codex/worktrees/0071/brain');cfgraw=(actual/'docs/plans/puck-cpu-held-qualification-04.json').read_bytes()
assert pin(cfgraw)['sha256']=='6fa33667eb5c4d5ebe94f13a8e485be8ef3b2929f29c30ad1ee479baccfe47b8'
cfg=json.loads(cfgraw);invraw=(actual/cfg['inputs']['inventory']['path']).read_bytes();assert pin(invraw)=={k:cfg['inputs']['inventory'][k] for k in ('size_bytes','sha256')}
inventory={r['path']:r for r in json.loads(invraw)['entries']}
phase_rows=[];commit='0fabc3ba44823f257e70ce397d989c8de5e362c1'
for short,name,creator,python,callline,callback,creation,method in [
 ('autograd','_distributed_autograd','torch.distributed.autograd','torch/distributed/autograd/__init__.py',16,'_dist_autograd_init',30,228),
 ('c10d','_distributed_c10d','torch.distributed','torch/distributed/__init__.py',29,'_c10d_init',466,4202),
 ('rpc','_distributed_rpc','torch.distributed.rpc','torch/distributed/rpc/__init__.py',28,'_rpc_init',47,854)]:
 cpp=Path('/tmp/palimpsest-cpu-remaining-export-review-01')/(short+'.cpp');copy(cpp,'remaining-phase-review/upstream/torch/csrc/distributed/'+short+'/init.cpp')
 src=actual/'runs/puck-cpu-install-01/site'/python;raw=src.read_bytes();assert pin(raw)=={k:inventory[python][k] for k in ('size_bytes','sha256')}
 copy(src,'remaining-phase-review/installed-source/'+python)
 phase_rows.append(dict(name='torch._C.'+name,current_producer='torch._C',current_phase='native_create',prospective_python_creator=creator,prospective_raw_attributes=['torch','_C',name],callback=callback,installed_python_call_line=callline,cpp_creation_line=creation,cpp_callback_mapping_line=method,cpp_url='https://github.com/pytorch/pytorch/blob/'+commit+'/torch/csrc/distributed/'+short+'/init.cpp',dispatch_roster_qualified=False,replacement_phase_accepted=False))
copy(ROOT/'docs/plans/puck-cpu-autograd-publication-profile-v1/upstream/LICENSE','remaining-phase-review/upstream/LICENSE')
assessment=dict(kind='puck-cpu-remaining-export-phase-preflight-v1',scope='static exact-commit/installed-source evidence only; not binary/runtime acceptance',status='three remaining source phase conflicts; actual05 freeze not ready',module_method_registration_lines=[1997,2006],rows=phase_rows,remaining_native_create_rows_not_reviewed_here=32,independent_review='all three source-level misattributions confirmed; review finite rosters/build conditions/intermediate publication before changing declarations',actual05_configuration_created=False,actual05_invoked=False)
assessment_path=Path('/tmp/palimpsest-cpu-remaining-export-review-01/assessment.json');assessment_path.write_bytes(canonical(assessment));copy(assessment_path,'remaining-phase-review/assessment.json')
absent=['docs/plans/puck-cpu-held-qualification-05.json','docs/plans/puck-cpu-held-qualification-05-freeze.json','runs/puck-cpu-held-qualification-05','docs/reports/puck-cpu-held-qualification-05.md','docs/reports/puck-cpu-held-qualification-05.json','docs/reports/puck-cpu-held-qualification-05']
assert all(not os.path.lexists(actual/p) for p in absent)
index=dict(kind='puck-cpu-held-amendment05-source-evidence-index-v1',source_code_commit=CODE,scope='AUTHORED source/prospective-profile/static preflight only',file_count=len(entries),total_bytes=sum(r['size_bytes'] for r in entries),entries=sorted(entries,key=lambda r:r['path']))
raw=canonical(index);(OUT/'evidence-index.json').write_bytes(raw)
report=dict(kind='puck-cpu-held-amendment05-source-report-v1',status='single-row source verified; real profile incomplete',source_base_commit=BASE,prospective_plan_commit=PLAN,source_code_commit=CODE,evidence_index=dict(path=NAME+'/evidence-index.json',**pin(raw)),verification=runs,authored05_observations=obs,authored_stage_cleanup=cleanup,independent_source_review='No material source findings; exact6 static source pins/one-row candidate/41-name roster verified independently',remaining_phase_preflight=assessment,actual05_configuration_created=False,actual05_invoked=False,actual01_through04_failed_consumed=True,installed_runtime_data_changed=False,runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,executable=False,all_seven_release_gates_open=True,qualification_claims=[])
(ROOT/'docs/reports'/ (NAME+'.json')).write_bytes(canonical(report))
print(json.dumps(dict(code=CODE,file_count=len(entries),bytes=index['total_bytes'],index=pin(raw),final_run=runs['isolated-persistent-affected-01'],remaining_phase_conflicts=len(phase_rows)),sort_keys=True))
