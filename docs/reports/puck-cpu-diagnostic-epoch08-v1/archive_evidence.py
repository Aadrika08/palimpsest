from pathlib import Path
import hashlib,json,shutil,subprocess

root=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-diagnostic-epoch08-v1')
packet=root/'docs/reports/puck-cpu-diagnostic-epoch08-v1'
assert not packet.exists()
review=Path('/tmp/palimpsest-diagnostic-epoch08-source-review.json')
source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
assert source_commit.startswith('1a51fb3')
metadata=['tests/test_puck_cpu_held_amendment'+suffix+'.py' for suffix in ('08','07','06','05','04','03','')]+[
    'tests/test_puck_cpu_held_parent.py','tests/test_puck_cpu_held_runtime_audit.py','tests/test_puck_cpu_held_observer.py']
integrations=['tests/test_puck_cpu_held_amendment'+suffix+'_integration.py' for suffix in ('08','07','06','05','04')]+[
    'tests/test_puck_cpu_held_amendment03.py::test_authored03_completes_after_real_failed01_02_without_changing_their_bytes',
    'tests/test_puck_cpu_held_amendment.py::test_authored02_uses_fresh_capsule_preserves01_and_refuses_reentry']
selection='not test_authored02_uses_fresh_capsule_preserves01_and_refuses_reentry and not test_authored03_completes_after_real_failed01_02_without_changing_their_bytes'
common=['env','PYTEST_DISABLE_PLUGIN_AUTOLOAD=1','PYTHONDONTWRITEBYTECODE=1','/usr/bin/timeout','--signal=TERM','--kill-after=5s']
sandbox=['/usr/bin/bwrap','--unshare-user','--uid','1000','--gid','1000','--bind','/','/','--tmpfs','/tmp','--dev','/dev','--proc','/proc','--chdir',str(root),'--',str(root.parents[0]/'r0-reproduction/.venv/bin/python'),'-m','pytest','-q','-p','no:cacheprovider']
stages=[
    ('red01',60,'/tmp/palimpsest-diagnostic-epoch08-red01',['tests/test_puck_cpu_held_amendment08.py','-k','accepts_five or observer_preserves'],1,0.80,dict(failed=3,deselected=38),'277c77'),
    ('metadata01',120,'/tmp/palimpsest-diagnostic-epoch08-metadata01',metadata,1,25.97,dict(passed=622,failed=2),'896468'),
    ('integration01',240,str(root/'runs/source-validation/diagnostic-epoch08-integration01/tmp'),integrations,0,119.48,dict(passed=8),'729587'),
    ('metadata02',120,'/tmp/palimpsest-diagnostic-epoch08-metadata02',metadata+['-k',selection],0,26.42,dict(passed=622,deselected=2),'ed879c'),
]
record=dict(kind='puck-cpu-diagnostic-epoch08-source-validation-v1',source_commit=source_commit,
    base_commit='9d4e425372c9457e363e198ddef2657190b9994b',red_test_commit='b89ef4ab2a13ff17dc4191ec0370e1c9274d18f9',
    scope='Authored metadata, transport and tiny Python/ELF packages only; no installed vendor or actual08 allocation.',
    final_disjoint_passed=630,full_repository_suite_run=False,actual08_controls_created=False,runtime_qualified=False,
    limitations=['RED reproduces missing08 parent/observer support before implementation.',
        'metadata01 ran two historical integrations under private/tmp; both failed their explicit persistent-runs fixture precondition. No production guard was changed; both passed in integration01.',
        'metadata02 excludes exactly those two already-passing persistent integrations;630 is622+8, without adding repeated successes.',
        'Independent source review binds nine source/test/plan byte pins; it did not execute tests.',
        'Authored stdout/stderr and source results do not explain07 timeout, refresh actual payload custody or grant installed-runtime/operator/renderer/episode/study/release acceptance.'],
    runs=[])
for stage,seconds,temp,tests,code,elapsed,counts,terminal in stages:
    folder=root/('runs/source-validation/diagnostic-epoch08-'+stage)
    record['runs'].append(dict(name=stage,command=common+[str(seconds)+'s']+sandbox+['--basetemp',temp]+tests,
        cwd=str(root),stdout=str(folder/'stdout.log'),stderr=str(folder/'stderr.log'),
        root_observed_terminal=dict(tool='exec_command/write_stdin',chunk_id=terminal,exit_code=code),
        pytest_reported_seconds=elapsed,pytest_counts=counts))
record_path=Path('/tmp/palimpsest-diagnostic-epoch08-validation-record.json')
with record_path.open('x') as stream:json.dump(record,stream,indent=2,sort_keys=True);stream.write('\n')
packet.mkdir()
artifacts=[]
def add(name,original):
    original=Path(original);raw=original.read_bytes();destination=packet/name
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:stream.write(raw)
    artifacts.append(dict(archived_path=name,original_path=str(original),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
source_paths=[]
for row in json.loads(review.read_bytes())['pins']:
    name=row['path'];raw=(root/name).read_bytes()
    assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    assert raw==subprocess.check_output(['git','show',source_commit+':'+name],cwd=root)
    add('source/'+name,root/name);source_paths.append(name)
for stage,*_ in stages:
    folder=root/('runs/source-validation/diagnostic-epoch08-'+stage)
    for name in ('stdout.log','stderr.log'):add('validation/'+stage+'/'+name,folder/name)
add('validation/record.json',record_path)
add('reviews/source-review.json',review)
roots={p.resolve() for p in (root/'runs/source-validation/diagnostic-epoch08-integration01/tmp').glob('test_authored08_*/authored-project')}
assert len(roots)==1
fixture=roots.pop()
for path in sorted((fixture/'runs/puck-cpu-held-qualification-08').rglob('*')):
    if path.is_file() and 'worker-source' not in path.parts:
        add('authored/qualify08/'+str(path.relative_to(fixture/'runs/puck-cpu-held-qualification-08')),path)
for name in ('authored-qualify08-configuration.json','authored-qualify08-transport.json','authored-qualify08-cli.stdout','authored-qualify08-cli.stderr',
             'authored-diagnostic08-cli-audit.json','authored-diagnostic08-cli-audit.stdout','authored-diagnostic08-cli-audit.stderr','authored-publication05-stage-cleanup.json'):
    add('authored/'+name,fixture/name)
add('archive_evidence.py',Path(__file__))
add('verify_evidence.py',root/'docs/reports/puck-cpu-runtime-phase-trace-v1/verify_evidence.py')
index=dict(kind='puck-cpu-diagnostic-epoch08-source-evidence-v1',source_commit=source_commit,
    source_paths=source_paths,artifact_count=len(artifacts),artifacts=sorted(artifacts,key=lambda row:row['archived_path']),
    final_disjoint_authored_passes=630,actual08_controls_created=False,runtime_qualified=False,all_seven_release_gates_open=True)
(packet/'evidence-index.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(artifacts=len(artifacts),bytes=sum(row['size_bytes'] for row in artifacts),empty_files=sum(row['size_bytes']==0 for row in artifacts),source_commit=source_commit)))
