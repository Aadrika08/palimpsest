from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/293b/brain');BASE=ROOT/'docs/plans/puck-cpu-q4-qualification-epoch10'
CASE=ROOT/'runs/q4-epoch10-regression01/test_authored10_binds_fifth_so0/authored-project'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='cbe48b339f4839ec4d2b5ef153d0dc0820be712e'
config=json.loads((CASE/'authored-qualify10-configuration.json').read_text())
base=CASE/'runs/puck-cpu-held-qualification-10'
result=json.loads((base/'result.json').read_text());worker=json.loads((base/'logs/stdout.log').read_text());reg=json.loads((base/'control/worker-registration.json').read_text())
assert (result['version'],result['allocation_id'],result['status'])==(10,10,'imports_completed')
assert reg['qualification']['version']==worker['entry_result']['qualification_version']==4
reports=[json.loads((CASE/name).read_text()) for name in ('authored-q4epoch10-api-audit.json','authored-q4epoch10-cli-audit.json','authored-q4epoch10-no-cost-api-audit.json')]
for value in (result,*reports):
 assert value['version']==10
 assert value['closure']['active_children']==value['closure']['active_non_main_threads']==[]
 assert value['closure']['fd_count_before']==value['closure']['fd_count_after']
 for key in ('runtime_qualified','native_authorized','collection_authorized','study_authorized','executable'):assert value[key] is False
 assert value['qualification_claims']==[]
assert all(value['status']=='PASS' for value in reports)
files=set(path for path in base.rglob('*') if path.is_file())
files.update(CASE.glob('authored-qualify10*'));files.update(CASE.glob('authored-q4epoch10*'))
for pin in config['preparation_acceptance'].values():files.add(CASE/pin['path'])
files.add(CASE/'runs/puck-cpu-held-preparation-01/payload/dependencies.json')
roster=[];total=0
for original in sorted(files):
 assert original.is_file() and not original.is_symlink() and original.stat().st_nlink==1
 raw=original.read_bytes();assert len(raw)<2*1024**2;total+=len(raw);assert total<8*1024**2
 name=str(original.relative_to(CASE));target=BASE/'authored'/name;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as stream:stream.write(raw)
 assert target.read_bytes()==raw
 roster.append(dict(path=str(target.relative_to(BASE)),original_path=str(original),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
source_pins=0;terminals=[]
for folder in sorted((BASE/'validation').iterdir()):
 command=json.loads((folder/'command.json').read_text());terminal=json.loads((folder/'terminal.json').read_text());assert terminal['outer_timeout'] is False
 for row in command['pins']:
  raw=(folder/'source'/row['path']).read_bytes();assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'];source_pins+=1
 terminals.append(terminal)
summary=dict(kind='puck-q4-epoch10-source-outcome-v1',status='SOURCE_AND_AUTHORED_INTEGRATION_PASS',source_commit='cbe48b339f4839ec4d2b5ef153d0dc0820be712e',
 test_first_commit='0cb3755b846753354f57c01bc4d0958957e91c86',new_cases=51,affected_regression_passing_cases=732,
 regression_seconds=122.64,terminals=terminals,source_copies_verified=source_pins,authored_files=len(roster),authored_bytes=total,
 parent_result=result['status'],worker_qualification_version=4,independent_audit_statuses=[v['status'] for v in reports],
 runtime_qualified=False,actual10_controls_created=False,actual10_invoked=False,all_seven_release_gates_open=True,
 scope='Tiny authored fixture uses18 missing names/128MiB floor. Production19 names/2GiB unchanged.51 new cases overlap732, not783.',artifacts=roster)
(BASE/'outcome.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
(BASE/'collect_evidence.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({k:v for k,v in summary.items() if k not in ('artifacts','terminals')},sort_keys=True))
