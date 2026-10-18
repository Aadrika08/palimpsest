from pathlib import Path
import hashlib,json
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
base=root/'docs/plans/puck-cpu-held-qualification-14-control-validation'
source=Path('/tmp/palimpsest-held14-pre-admission-guard.py').read_text()
source=source.replace('before the sole data-only admission.','before the sole runtime observer.')
old="""for outputs in envelope['phase_outputs'].values():assert all(not os.path.lexists(path) for path in outputs.values())
assert all(not os.path.lexists(envelope[key]) for key in ('admission_output','auditor_output','concrete_audit_command_path'))"""
admission=Path('/tmp/palimpsest-puck-cpu-held-qualification-14-admission-01.json').read_bytes()
review_path=Path('/tmp/palimpsest-held14-independent-admission-review.json')
review_raw=review_path.read_bytes()
review=json.loads(review_raw);assert review['decision']=='GO'
new="""future=[path for phase in ('observer','audit') for path in envelope['phase_outputs'][phase].values()]
future += [envelope['auditor_output'],envelope['concrete_audit_command_path']]
prior_guard=json.loads(Path('/tmp/palimpsest-held14-pre-admission-guard01.json').read_bytes())
assert prior_guard['control_commit']==CONTROL
future += [path for path in prior_guard['absence']['new_paths'] if path not in (envelope['admission_output'],envelope['auditor_output'])]
assert len(future)==len(set(future))==12
assert all(not os.path.lexists(path) for path in future)
assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-qualification-14-admission-02.json')
admission=Path(envelope['admission_output']).read_bytes()
assert admission==Path(envelope['phase_outputs']['admission']['stdout']).read_bytes()
assert len(admission)==@ADMISSION_SIZE@ and hashlib.sha256(admission).hexdigest()=='@ADMISSION_SHA@'
a=json.loads(admission)
assert a['status']=='DATA_ONLY_ADMITTED' and a['admission_check_id']==1 and a['qualification14_invoked'] is False
assert a['runtime_qualified'] is False and a['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
review_path=Path('/tmp/palimpsest-held14-independent-admission-review.json')
assert pin(review_path)==dict(size_bytes=@REVIEW_SIZE@,sha256='@REVIEW_SHA@')
review=json.loads(review_path.read_bytes());assert review['decision']=='GO'"""
new=new.replace('@ADMISSION_SIZE@',str(len(admission))).replace('@ADMISSION_SHA@',hashlib.sha256(admission).hexdigest()).replace('@REVIEW_SIZE@',str(len(review_raw))).replace('@REVIEW_SHA@',hashlib.sha256(review_raw).hexdigest())
assert source.count(old)==1;source=source.replace(old,new)
old='absence=module.absent();resources=module.resources()'
new='absence=dict(future_output_paths=future,historical_missing_receipts=19);resources=module.resources()'
assert source.count(old)==1;source=source.replace(old,new)
source=source.replace("status='PASS_PRE_ADMISSION_GUARD_ONLY'","status='PASS_PRE_OBSERVER_GUARD_ONLY'")
source=source.replace('historical_records_unchanged=126,admission_main_invoked=False,runtime_invoked=False,','historical_records_unchanged=126,admission_main_invoked=True,admission_receipt_sha256=hashlib.sha256(admission).hexdigest(),runtime_invoked=False,')
source=source.replace("Path('/tmp/palimpsest-held14-pre-admission-guard01.json').open('x')","Path('/tmp/palimpsest-held14-pre-observer-guard01.json').open('x')")
path=Path('/tmp/palimpsest-held14-pre-observer-guard.py')
compile(source,str(path),'exec')
with path.open('x') as out:out.write(source)
print(json.dumps(dict(guard_path=str(path),admission_size_bytes=len(admission),admission_sha256=hashlib.sha256(admission).hexdigest(),review_size_bytes=len(review_raw),review_sha256=hashlib.sha256(review_raw).hexdigest())))
