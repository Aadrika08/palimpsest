"""Write the preparation02 configuration and prospective freeze once; never invokes an allocation.

The configuration bytes come from the qualifier's own canonical serializer. Only kind,
version, allocation id, stage parent and the 24 source pins differ from preparation01.
"""
from pathlib import Path
import copy,datetime,hashlib,json,subprocess,sys,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
SOURCE='8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15'
PREP01='docs/plans/puck-cpu-held-preparation-01.json'
FREEZE01='docs/plans/puck-cpu-held-preparation-01-freeze.json'
CONFIG='docs/plans/puck-cpu-held-preparation-02.json'
FREEZE='docs/plans/puck-cpu-held-preparation-02-freeze.json'
STAGE='/tmp/palimpsest-puck-cpu-held-02'
OUTPUT='runs/puck-cpu-held-preparation-02'
AUDIT_STEM='/tmp/palimpsest-puck-cpu-held-preparation-02-audit-01'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
def pin(name):
    raw=(ROOT/name).read_bytes();return dict(path=name,size_bytes=len(raw),sha256=sha(raw))
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',SOURCE,'HEAD']).returncode==0
assert not (ROOT/CONFIG).exists() and not (ROOT/FREEZE).exists()
parent=load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','prep02_parent')
auditor=load(ROOT/'scripts/audit_puck_cpu_held_runtime.py','prep02_auditor')
raw01=(ROOT/PREP01).read_bytes();prep01=parent.decode(raw01)
assert parent.canonical(prep01)==raw01 and sha(raw01)=='38134e016eff974e06806f1ac74492dc51e0a5721d8cd13d1123a1fd950fe8a6'
config=copy.deepcopy(prep01)
config.update(kind='puck-cpu-held-runtime-allocation-v12',version=12,allocation_id=12,stage_parent=STAGE)
sources=[]
for row in prep01['sources']:
    raw=(ROOT/row['path']).read_bytes()
    assert raw==git('show','HEAD:'+row['path'])==git('show',SOURCE+':'+row['path']),row['path']
    sources.append(dict(path=row['path'],size_bytes=len(raw),sha256=sha(raw)))
config['sources']=sources
parent.validate_configuration(config);auditor.configuration(config,False)
assert parent.allocation_output(config)==auditor.allocation_output(config)==OUTPUT
assert parent.preparation_output(config)==auditor.preparation_output(config)==OUTPUT
assert config['limits']==parent.LIMITS['prepare'] and config['negative_imports']==parent.PREPARATION_NEGATIVE_IMPORTS
raw=parent.canonical(config)
with (ROOT/CONFIG).open('xb') as out:out.write(raw)
assert (ROOT/CONFIG).read_bytes()==raw
config_sha=sha(raw)
diff={key:dict(preparation01=prep01[key],preparation02=config[key]) for key in sorted(prep01) if key!='sources' and prep01[key]!=config[key]}
assert set(prep01)==set(config) and set(diff)=={'kind','version','allocation_id','stage_parent'}
changed_sources=[dict(path=a['path'],preparation01={k:a[k] for k in ('size_bytes','sha256')},preparation02={k:b[k] for k in ('size_bytes','sha256')})
    for a,b in zip(prep01['sources'],config['sources']) if a!=b]
assert [r['path'] for r in changed_sources]==['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py',
    'src/palimpsest/puck_dependency_bindings.py','src/palimpsest/puck_dependency_imports.py','src/palimpsest/puck_runtime_qualification.py']
python=parent.PYTHON
freeze=copy.deepcopy(json.loads((ROOT/FREEZE01).read_bytes()))
auditor_pin=pin('scripts/audit_puck_cpu_held_runtime.py')
assert auditor_pin['sha256']==parent.PREPARATION02_AUDITOR_SHA256=='04192a3ba3d7020a5399465aa6da4f7d7ebe3d74172e4b448ea500b09aa9a62b'
freeze['audit'].update(
    acceptance=freeze['audit']['acceptance']+[
        'bare 15-element auditor argv with no timeout wrapper',
        'stderr empty; auditor elapsed below 120s and external record elapsed below 130s',
        'record keys exactly kind, command, observed_returncode, elapsed_seconds, published, stdout, stderr',
        'audit kind v12, version 12, allocation_id 12, auditor_source_sha256 equals the auditor pin'],
    command_prefix=[python,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),'--configuration',str(ROOT/CONFIG),
        '--sha256',config_sha,'--transport',str(ROOT/(OUTPUT+'-external-cli-transport.json'))],
    output=AUDIT_STEM+'.json',stdout=AUDIT_STEM+'.stdout',stderr=AUDIT_STEM+'.stderr',record=AUDIT_STEM+'.external-cli.json')
freeze.update(kind='puck-cpu-held-preparation02-prospective-freeze-v1',version=1,allocation_id=12,
    command=[python,'-I','-S','-B',str(ROOT/'scripts/observe_puck_cpu_held_allocation.py'),'--configuration',str(ROOT/CONFIG),'--sha256',config_sha],
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=SOURCE,
    transport_path=str(ROOT/(OUTPUT+'-external-cli-transport.json')),output=OUTPUT,stage_parent=STAGE,
    pins=dict(configuration=pin(CONFIG),observer=pin('scripts/observe_puck_cpu_held_allocation.py'),auditor=auditor_pin,
        interpreter=dict(config['interpreter']),sources=config['sources']),
    previous_preparation=dict(configuration=pin(PREP01),freeze=pin(FREEZE01),status='ACCEPTED_BUT_STAGE_LOST_ON_REBOOT'),
    boot_guard='Record boot_id before the observer; audit and archive refuse any other boot_id and any staged-root dev/inode differing from result.staged_roots',
    review=dict(scope='independent source review 02 of 1126b71..8f3a138 (APPROVE); these controls still need an independent controls review',
        status='Source approved; controls not yet reviewed'),
    verification=dict(scope='offline metadata and fixture proofs only; no allocation, observer, auditor or qualifier invoked',
        path='docs/plans/puck-cpu-held-preparation-02-tools/validation'),
    scope='One data-only CPU preparation02 (allocation 12); invocation still requires a fresh boot/pin/resource preflight')
assert freeze['environment']==dict(LANG='C.UTF-8',LC_ALL='C.UTF-8',PATH='/usr/bin:/bin',PYTHONDONTWRITEBYTECODE='1')
assert freeze['cwd']==str(ROOT) and freeze['fresh_admission_required'] is True
freeze_raw=(json.dumps(freeze,indent=2,sort_keys=True)+'\n').encode()
with (ROOT/FREEZE).open('xb') as out:out.write(freeze_raw)
print(json.dumps(dict(configuration=dict(path=CONFIG,size_bytes=len(raw),sha256=config_sha),
    freeze=dict(path=FREEZE,size_bytes=len(freeze_raw),sha256=sha(freeze_raw)),
    top_level_diff=diff,changed_sources=changed_sources,unchanged_sources=24-len(changed_sources),
    validators=dict(parent_validate_configuration='PASS',auditor_configuration='PASS',allocation_output=OUTPUT),
    canonical_serializer='qualify_puck_cpu_held_runtime.canonical (reproduces preparation01 bytes exactly)',
    allocation_invoked=False),indent=2,sort_keys=True))
