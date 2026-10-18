"""Archive the authored rejected candidate; never run a worker or qualification."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,time

ROOT=Path('/home/utkarsh/.codex/worktrees/f2fa/brain')
BASE=ROOT/'docs/plans/puck-cpu-guard-equivalence-v1'
PACKET=ROOT/'docs/reports/puck-cpu-guard-equivalence-v1'
SOURCE='fb20e74362cd3cf19331a291d0a95753b19a81da'
STARTED=time.monotonic()
def read(path):
    path=Path(path);assert time.monotonic()-STARTED<30
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=2*1024**2
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(2*1024**2+1)
        fields=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        assert len(raw)==before.st_size and all(getattr(before,k)==getattr(os.fstat(fd),k)==getattr(path.lstat(),k) for k in fields)
        return raw
    finally:os.close(fd)
assert not PACKET.exists()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==SOURCE
assert subprocess.check_output(['git','diff','31d980be15921b206eb77d2455931cc44c06270e','--','scripts','src'],cwd=ROOT)==b''
comparison=json.loads(read(BASE/'comparison.json'))
assert comparison['status']=='CANDIDATE_REJECTED_SEMANTIC_MISMATCH' and comparison['production_changed'] is comparison['timing_workload_executed'] is False
review=json.loads(read('/tmp/palimpsest-guard-equivalence-outcome-review.json'))
assert review['findings']==[] and review['status']=='GO_EVIDENCE_CONSISTENT_CANDIDATE_REJECTED'
source_paths=[r['path'] for r in json.loads(read(BASE/'validation/baseline01/command.json'))['pins']]
assert len(source_paths)==13
pairs={}
def reserve(path,name):
    assert name not in pairs and not Path(name).is_absolute() and '..' not in Path(name).parts
    pairs[name]=Path(path)
for name in source_paths:
    assert read(ROOT/name)==subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT)
    reserve(ROOT/name,'source/'+name)
files=sorted(p for p in BASE.rglob('*') if p.is_file())
assert len(files)==41,len(files)
for path in files:reserve(path,'experiment/'+str(path.relative_to(BASE)))
for name in ('design-review','fixture-map','source-review','outcome-review'):
    reserve('/tmp/palimpsest-guard-equivalence-'+name+'.json','reviews/'+name+'.json')
reserve('/tmp/palimpsest-guard-equivalence-run-batch.py','tools/run-batch.py')
reserve('/tmp/palimpsest-guard-equivalence-tool-terminals.json','tools/tool-terminals.json')
reserve(Path(__file__).resolve(),'archive_evidence.py')
reserve(ROOT/'docs/reports/puck-cpu-held-qualification-09/verify_evidence.py','verify_evidence.py')
reserve(ROOT/'docs/reports/puck-cpu-held-qualification-09/.gitattributes','.gitattributes')
payloads={};rows=[];total=0
for name,path in sorted(pairs.items()):
    raw=read(path);total+=len(raw);assert total<2*1024**2
    payloads[name]=raw;rows.append(dict(archived_path=name,original_path=str(path),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
assert len(rows)<=96
PACKET.mkdir()
for name,raw in payloads.items():
    path=PACKET/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    assert read(path)==raw
index=dict(kind='puck-authored-guard-equivalence-evidence-v1',source_commit=SOURCE,source_paths=source_paths,
    unchanged_production_base='31d980be15921b206eb77d2455931cc44c06270e',decision='REJECT_INPLACE_RETAIN_PRODUCTION',
    production_changed=False,timing_workload_executed=False,runtime_qualified=False,actual10_invoked=False,
    all_seven_release_gates_open=True,artifact_count=len(rows),total_bytes=total,empty_files=sum(r['size_bytes']==0 for r in rows),artifacts=rows,
    scope='Authored dispatch counterexample and byte archive only; not installed runtime or performance acceptance.')
raw=(json.dumps(index,sort_keys=True,indent=2)+'\n').encode()
with (PACKET/'evidence-index.json').open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
assert read(PACKET/'evidence-index.json')==raw
print(json.dumps(dict(artifacts=len(rows),bytes=total,empty_files=index['empty_files'],index_sha256=hashlib.sha256(raw).hexdigest(),runtime_qualified=False)))
