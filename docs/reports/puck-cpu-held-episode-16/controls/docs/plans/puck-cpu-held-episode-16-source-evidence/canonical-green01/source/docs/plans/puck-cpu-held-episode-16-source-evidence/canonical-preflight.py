"""Re-validate the frozen allocation-16 configuration offline; never runs an allocation, observer or auditor main.

Checks the canonical bytes, run_puck_cpu_held_episode validate_configuration/validate_acceptance/
require_declared_misses and audit_puck_cpu_held_episode validate_configuration/validate_acceptance,
the 1200/1215/1230 s clocks with 600 s workers, the 42+4 rosters, fresh run ids and that the
configuration binds exactly preparation04's sources, inputs and stage. Never opens the stage.
"""
from pathlib import Path
import hashlib,json,sys,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
q=load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','canonical16_qualifier')
episode=load(ROOT/'scripts/run_puck_cpu_held_episode.py','canonical16_episode')
auditor=load(ROOT/'scripts/audit_puck_cpu_held_episode.py','canonical16_episode_auditor')
raw=(ROOT/'docs/plans/puck-cpu-held-episode-16.json').read_bytes();config=json.loads(raw)
assert episode.canonical(config)==raw==auditor.canonical(config)
blobs={role:(ROOT/row['path']).read_bytes() for role,row in config['preparation_acceptance'].items()}
episode.validate_configuration(config,q);prior,prep=episode.validate_acceptance(config,blobs,q)
episode.require_declared_misses(json.loads((ROOT/config['inputs']['candidate']['path']).read_bytes()))
auditor.validate_configuration(config,prior);auditor.validate_acceptance(config,auditor.Reader(time.monotonic()+60))
prep04=json.loads((ROOT/'docs/plans/puck-cpu-held-preparation-04.json').read_bytes())
assert prior==prep04 and config['inputs']==prep04['inputs'] and config['stage_parent']==prep04['stage_parent']=='/tmp/palimpsest-puck-cpu-held-04'
assert [r for r in config['sources'] if r['path']!=episode.PARENT]==prep04['sources']
assert (config['limits']['normal_seconds'],config['limits']['child_hard_seconds'],config['limits']['hard_seconds'])==(1200,1215,1230)
assert episode.WORKER_SECONDS==auditor.WORKER_SECONDS==600 and auditor.TRANSPORT_SECONDS==1260
assert len(config['negative_imports'])==42 and config['hidden_imports']==['networkx','pandas','sklearn','torch.utils._cxx_pytree']
assert config['run_ids']['source']!=config['run_ids']['replay'] and not set(config['run_ids'].values())&set(episode.CHARACTERIZATION_RUN_IDS)
assert prep['staged_roots']==[dict(device=55,inode=317249+i,root_index=i) for i in range(4)]
print(json.dumps(dict(status='PASS_CANONICAL_ALLOCATION16_CONFIGURATION',size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
    episode_validate_configuration=True,episode_validate_acceptance=True,require_declared_misses=True,
    episode_auditor_validate_configuration=True,episode_auditor_validate_acceptance=True,run_ids=config['run_ids'],
    clocks=[1200,1215,1230],worker_seconds=600,negative_imports=42,hidden_imports=4,stage_touched=False),sort_keys=True))
