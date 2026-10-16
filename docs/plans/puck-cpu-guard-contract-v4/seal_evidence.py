"""Seal the authored source unit in place; never run an installed allocation."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/293b/brain');BASE=ROOT/'docs/plans/puck-cpu-guard-contract-v4'
SOURCE='23663cfb884d3e5033daeb4a8a0aafc8ce558ad8'
assert not (BASE/'evidence-index.json').exists()
assert subprocess.check_output(['git','diff',SOURCE,'--','scripts','src','tests'],cwd=ROOT)==b''
review=json.loads(Path('/tmp/palimpsest-q4-outcome-review.json').read_text())
assert review['findings']==[],review
assert review['status'].startswith('GO'),review['status']
(BASE/'outcome-review.json').write_bytes(Path('/tmp/palimpsest-q4-outcome-review.json').read_bytes())
paths=set()
for label in ('guard-entry03','entry-final01','cost01'):
 command=json.loads((BASE/'validation'/label/'command.json').read_text())
 paths.update(row['path'] for row in command['pins'])
comparison=json.loads((BASE/'cost-comparison.json').read_text())
paths.update(comparison[key]['path'] for key in ('baseline','baseline_source'))
for name in sorted(paths):
 raw=(ROOT/name).read_bytes()
 assert raw==subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT),name
 target=BASE/'source'/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as stream:stream.write(raw)
(BASE/'verify_evidence.py').write_bytes((ROOT/'docs/reports/puck-cpu-held-qualification-09/verify_evidence.py').read_bytes())
(BASE/'seal_evidence.py').write_bytes(Path(__file__).read_bytes())
rows=[];total=0
for path in sorted(BASE.rglob('*')):
 if not path.is_file():continue
 assert not path.is_symlink() and path.stat().st_nlink==1
 raw=path.read_bytes();assert len(raw)<2*1024**2;total+=len(raw);assert total<8*1024**2
 name=str(path.relative_to(BASE))
 original=ROOT/str(Path(name).relative_to('source')) if name.startswith('source/') else path
 rows.append(dict(archived_path=name,original_path=str(original),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
index=dict(kind='puck-authored-q4-guard-evidence-v1',source_commit=SOURCE,source_paths=sorted(paths),
 artifact_count=len(rows),total_bytes=total,empty_files=sum(row['size_bytes']==0 for row in rows),artifacts=rows,
 runtime_qualified=False,actual10_controls_created=False,actual10_invoked=False,all_seven_release_gates_open=True,
 scope='In-place sealed authored source/evidence packet, not a copy of an installed allocation. Historical failure records remain unchanged.')
raw=(json.dumps(index,sort_keys=True,indent=2)+'\n').encode()
with (BASE/'evidence-index.json').open('xb') as stream:stream.write(raw)
print(json.dumps(dict(artifacts=len(rows),bytes=total,empty_files=index['empty_files'],index_sha256=hashlib.sha256(raw).hexdigest(),source_paths=len(paths)),sort_keys=True))
