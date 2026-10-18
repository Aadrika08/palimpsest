"""Write the allocation-16 episode configuration once; never invokes an allocation, observer or auditor.

The configuration is exactly the shape run_puck_cpu_held_episode.py and audit_puck_cpu_held_episode.py
validate: preparation04's sources plus this parent, preparation04's inputs and stage, the parent's
environment, versions, 1200/1215/1230 s limits, 42 absent and 4 hidden names and claims,
preparation04's four archived acceptance pins and two fresh run ids distinct from characterization-04's.
Bytes come from the episode parent's own canonical(). Both parent validators and both episode-auditor
validators must accept it before it is written.
"""
from pathlib import Path
import hashlib,json,secrets,subprocess,sys,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONFIG='docs/plans/puck-cpu-held-episode-16.json'
PREP04='docs/plans/puck-cpu-held-preparation-04.json'
PREP04_ARCHIVE='docs/reports/puck-cpu-held-preparation-04/archive-record.json'
MERGE='75df4dba55e435eee84d8a0f34b33967b0ac86bf'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
def pin(name):raw=(ROOT/name).read_bytes();return dict(path=name,size_bytes=len(raw),sha256=sha(raw))
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert git('rev-parse','HEAD').decode().strip()==MERGE and not (ROOT/CONFIG).exists()
q=load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','port16_qualifier')
episode=load(ROOT/'scripts/run_puck_cpu_held_episode.py','port16_episode')
auditor=load(ROOT/'scripts/audit_puck_cpu_held_episode.py','port16_episode_auditor')
prep04=json.loads((ROOT/PREP04).read_bytes());acceptance=json.loads((ROOT/PREP04_ARCHIVE).read_bytes())['acceptance_pins']
assert all(pin(r['path'])==r for r in acceptance.values()) and acceptance['configuration']==pin(PREP04)
run_ids=dict(source=secrets.token_hex(16),replay=secrets.token_hex(16))
assert run_ids['source']!=run_ids['replay'] and not set(run_ids.values())&set(episode.CHARACTERIZATION_RUN_IDS)
config=dict(kind=episode.KIND,version=16,allocation_id=16,root=str(ROOT),stage_parent=prep04['stage_parent'],
    sources=sorted(prep04['sources']+[pin(episode.PARENT)],key=lambda r:r['path']),inputs=prep04['inputs'],
    interpreter=dict(q.INTERPRETER),environment=dict(episode.ENVIRONMENT),expected_versions=dict(episode.VERSIONS),
    limits=dict(episode.LIMITS),negative_imports=list(episode.NEGATIVE_IMPORTS),hidden_imports=list(episode.HIDDEN_IMPORTS),
    claims=dict(episode.CLAIMS),preparation_acceptance=acceptance,run_ids=run_ids)
raw=episode.canonical(config);config=json.loads(raw)
for row in config['sources']:
    assert pin(row['path'])==row,row['path']
    if not row['path'].startswith('upstream/'):assert (ROOT/row['path']).read_bytes()==git('show','HEAD:'+row['path']),row['path']
blobs={role:(ROOT/row['path']).read_bytes() for role,row in acceptance.items()}
episode.validate_configuration(config,q);prior,prep=episode.validate_acceptance(config,blobs,q)
episode.require_declared_misses(json.loads((ROOT/config['inputs']['candidate']['path']).read_bytes()))
auditor.validate_configuration(config,prior);auditor.validate_acceptance(config,auditor.Reader(time.monotonic()+60))
assert auditor.canonical(config)==raw and prior==prep04 and prep['staged_roots']==[dict(device=55,inode=317249+i,root_index=i) for i in range(4)]
assert (config['limits']['normal_seconds'],config['limits']['child_hard_seconds'],config['limits']['hard_seconds'])==(1200,1215,1230)
assert episode.WORKER_SECONDS==auditor.WORKER_SECONDS==600 and len(config['negative_imports'])==42 and len(config['hidden_imports'])==4
assert episode.EPISODE['schedule']==dict(ticks=48,actions=[[0,1.0,0.0],[24,1.0,0.5]]) and episode.EPISODE['profile']['seed']==7
with (ROOT/CONFIG).open('xb') as out:out.write(raw)
print(json.dumps(dict(configuration=dict(path=CONFIG,size_bytes=len(raw),sha256=sha(raw)),run_ids=run_ids,
    sources=len(config['sources']),inputs=len(config['inputs']),stage_parent=config['stage_parent'],
    preparation_acceptance={k:v['sha256'] for k,v in acceptance.items()},
    validators=dict(episode_validate_configuration='PASS',episode_validate_acceptance='PASS',require_declared_misses='PASS',
        episode_auditor_validate_configuration='PASS',episode_auditor_validate_acceptance='PASS'),
    serializer='run_puck_cpu_held_episode.canonical (compact, ensure_ascii=False, LF)',allocation_invoked=False,stage_touched=False),
    indent=2,sort_keys=True))
