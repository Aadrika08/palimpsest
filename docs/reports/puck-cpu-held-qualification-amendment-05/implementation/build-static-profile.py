from pathlib import Path
import copy,hashlib,json
root=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
out=root/'docs/plans/puck-cpu-autograd-publication-profile-v1';out.mkdir(parents=True,exist_ok=False)
commit='0fabc3ba44823f257e70ce397d989c8de5e362c1'
old_path=root/'docs/reports/puck-cpu-held-qualification-04/inspection/profile-candidate.json'
old_raw=old_path.read_bytes();assert hashlib.sha256(old_raw).hexdigest()=='d20076cd2e1961d1514bb135746b1701a14567136b80ee073fecedb389f929df'
old=json.loads(old_raw);new=copy.deepcopy(old)
old_row=dict(name='torch._C._autograd',producer='torch._C',phase='native_create',attributes=['_autograd'],class_binding=None)
exports=new['import_profile']['exports'];indexes=[i for i,r in enumerate(exports) if r['name']==old_row['name']]
assert len(indexes)==1 and exports[indexes[0]]==old_row
roster=json.loads(Path('/tmp/palimpsest-autograd-publication-profile-01/roster.json').read_bytes())
assert roster==sorted(set(roster)) and len(roster)==41
new_row=dict(name=old_row['name'],producer='torch.autograd',phase='module_exec_publish',attributes=['torch','_C','_autograd'],class_binding=None,delegate_attributes=roster)
exports[indexes[0]]=new_row
assert next(r for r in new['module_paths'] if r['name']=='torch.autograd')['kind']=='python'
canonical=lambda v:(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
pin=lambda raw:dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
new_path=root/'docs/plans/puck-cpu-autograd-publication-profile-v1.json';assert not new_path.exists();new_path.write_bytes(canonical(new))
entries=[]
oldsource=root/'docs/reports/puck-cpu-held-qualification-04/upstream'
fresh=Path('/tmp/palimpsest-autograd-publication-profile-01/upstream')
for rel in ['LICENSE','torch/csrc/autograd/init.cpp','torch/csrc/Module.cpp','torch/autograd/__init__.py','torch/csrc/autograd/profiler_python.cpp','torch/csrc/profiler/orchestration/python_tracer.cpp']:
 src=(fresh if (fresh/rel).exists() else oldsource)/rel;raw=src.read_bytes();target=out/'upstream'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 assert target.read_bytes()==src.read_bytes()
 entries.append(dict(path='upstream/'+rel,original=str(src),url='https://github.com/pytorch/pytorch/blob/'+commit+'/'+rel,**pin(raw)))
profile=dict(kind='puck-cpu-autograd-publication-profile-source-proof-v1',status='prospective static candidate; not binary or runtime qualification',upstream_package_declared_commit=commit,
 previous_candidate=dict(path=str(old_path.relative_to(root)),**pin(old_raw)),candidate=dict(path=str(new_path.relative_to(root)),**pin(new_path.read_bytes())),
 replaced_export=old_row,proposed_export=new_row,unchanged_other_exports=len(exports)-1,
 creator_evidence=dict(python_call_line=558,cpp_creation_line=135,cpp_intermediate_import_line=138,cpp_first_delegate_line=147,cpp_final_tracer_line=599,tracer_init_lines=[1591,1598],factory_register_lines=[33,45]),
 roster_evidence=dict(literal_functions=32,literal_classes_enums=9,source_initialization_only=True,build_conditionals_do_not_change_top_level_names=True),
 source_files=entries,limitations=['Exact package-declared source is not linked-binary build provenance.','Guarded snapshots and direct dispatch references only; runtime mismatches still refuse.','Other35 native-create declarations remain unchanged and unqualified.','No real configuration or actual attempt is created by this source candidate.'],
 actual05_configuration_created=False,actual05_invoked=False,runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,executable=False,qualification_claims=[])
(out/'source-proof.json').write_bytes(canonical(profile))
Path('/tmp/palimpsest-autograd-publication-profile-01/source-proof-result.json').write_bytes(canonical(profile))
print(json.dumps(dict(candidate=profile['candidate'],other_exports_unchanged=37,delegates=len(roster),source_files=len(entries))))
