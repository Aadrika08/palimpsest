"""Archive terminal10 evidence only, with bounded stable reads and exact Git origins."""
from pathlib import Path
import datetime,hashlib,json,os,stat,subprocess,sys,time
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
base='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
control='796359a099131157b5b91db38f14784628d5d7c5'
source='e723db037ed1f790c2618798d59f56913054754f'
packet=root/'docs/reports/puck-cpu-held-qualification-10'
end=time.monotonic()+60

def read(path):
    assert time.monotonic()<end
    path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    def stamp(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    try:
        before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=16*1024**2
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(16*1024**2+1)
        assert len(raw)==before.st_size and stamp(before)==stamp(os.fstat(fd))==stamp(path.lstat())
        return raw
    finally:os.close(fd)

def git(*args):return subprocess.check_output(['git',*args],cwd=root,timeout=10)
assert len(sys.argv)==2 and len(sys.argv[1])==64 and not os.path.lexists(packet)
assert git('rev-parse','HEAD').decode().strip()==control and git('status','--porcelain')==b''
review_path=Path('/tmp/palimpsest-held10-amendment02-independent-outcome-review.json')
review_raw=read(review_path);assert hashlib.sha256(review_raw).hexdigest()==sys.argv[1]
review=json.loads(review_raw)
assert review['status']=='PASS_FAILED_OUTCOME_RECORD_NO_RUNTIME_ACCEPTANCE' and review.get('material_findings',review.get('findings'))==[]
post_path=Path('/tmp/palimpsest-held10-amendment02-post-outcome-observation.json')
post_raw=read(post_path);post=json.loads(post_raw)
assert post['status']=='FAILED_CONSUMED' and post['source_commit']==source and post['control_commit']==control
assert post['observer_invocations']==post['independent_auditor_invocations']==1
assert post['parent_result']['status']==post['independent_audit']['status']=='FAIL'
assert post['completed_four_import_receipt'] is post['post_failure_full_payload_custody'] is False
assert all(not os.path.lexists(p) for p in post['missing_original_paths'])
payloads={};rows=[];total=0

def save(name,path,pin=None,revision=None):
    global total
    assert name not in payloads and not Path(name).is_absolute() and '..' not in Path(name).parts
    path=Path(path);raw=read(path);digest=hashlib.sha256(raw).hexdigest()
    if pin is not None:assert len(raw)==pin['size_bytes'] and digest==pin['sha256'],name
    if revision is not None:assert raw==git('show',revision+':'+str(path.relative_to(root))),name
    total+=len(raw);assert total<=64*1024**2
    payloads[name]=raw
    row=dict(archived_path=name,original_path=str(path),size_bytes=len(raw),sha256=digest)
    if revision is not None:row['original_git_revision']=revision
    rows.append(row)

controls=git('ls-tree','-r','--name-only',control,'--',base).decode().splitlines();assert len(controls)==74
for name in controls:save('controls/'+name,root/name,revision=control)
config=json.loads(read(root/base/'configuration.json'))
auth='docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'
sources=sorted({row['path'] for row in config['sources']}|{'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py',auth})
assert len(sources)==27
for name in sources:save('source/'+name,root/name,revision=source)
allocation=root/'runs/puck-cpu-held-qualification-10'
for row in post['pins']:
    path=Path(row['path'])
    if path.is_relative_to(allocation):name='raw/'+str(path.relative_to(allocation))
    elif path.is_relative_to(root/'runs'):name='transport/'+path.name
    else:
        assert path.parent==Path('/tmp')
        name='observations/'+path.name
    save(name,path,pin=row)
for name in ('pre-admission-guard.py','pre-observer-guard.py','run-admission-template.py','run-admission-once.py','run-observer-once.py','run-audit-once.py','bind-audit-command.py','make-observer-guard.py','collect-outcome.py','post-outcome-observation.json','independent-outcome-review.json','external.py'):
    path=Path('/tmp/palimpsest-held10-amendment02-'+name)
    save('tools/'+path.name,path)
save('verify_evidence.py',root/'docs/reports/puck-cpu-held-qualification-09/verify_evidence.py')
save('archive_evidence.py',Path(__file__))
index=dict(kind='puck-cpu-held-qualification10-terminal-evidence-v1',created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=source,source_paths=sources,control_commit=control,control_paths=controls,artifacts=rows,artifact_count=len(rows),total_bytes=total,empty_files=sum(r['size_bytes']==0 for r in rows),status='FAILED_CONSUMED',observer_invocations=1,independent_auditor_invocations=1,admission02_status='DATA_ONLY_ADMITTED',runtime_qualified=False,qualification_claims=[],all_seven_release_gates_open=True,post_failure_full_payload_custody=False,post_outcome_sha256=hashlib.sha256(post_raw).hexdigest(),independent_outcome_review_sha256=sys.argv[1],missing_original_paths=post['missing_original_paths'],limits='Terminal metadata archive, not runtime acceptance, full post-run payload custody, model/operator/renderer/study or physical proof. Prior frozen histories and inputs remain referenced by the unchanged freeze, not recursively copied.')
packet.mkdir()
for name,raw in payloads.items():
    path=packet/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    assert read(path)==raw
raw=(json.dumps(index,indent=2,sort_keys=True)+'\n').encode()
with (packet/'evidence-index.json').open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
assert read(packet/'evidence-index.json')==raw
print(json.dumps(dict(packet=str(packet),artifacts=len(rows),bytes=total,empty_files=index['empty_files'],index_sha256=hashlib.sha256(raw).hexdigest(),runtime_qualified=False)))
