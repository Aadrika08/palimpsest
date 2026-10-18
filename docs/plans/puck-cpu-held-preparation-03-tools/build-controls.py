"""Write the preparation03 configuration and prospective freeze once; never invokes an allocation.

The configuration bytes come from the qualifier's own canonical serializer. Only kind,
version, allocation id, stage parent and the 24 source pins differ from preparation01.
Preparation02 stays accepted with its stage untouched; it is recorded, never read here.
"""
from pathlib import Path
import copy,datetime,hashlib,json,subprocess,sys,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
SOURCE='f05bd699af337e44de54584bb334690ec405f994'
PREP02_EVIDENCE='facc2a741315867ce98e745edd5d6692abf77603'
PREP01='docs/plans/puck-cpu-held-preparation-01.json'
FREEZE01='docs/plans/puck-cpu-held-preparation-01-freeze.json'
PREP02='docs/plans/puck-cpu-held-preparation-02.json'
CONFIG='docs/plans/puck-cpu-held-preparation-03.json'
FREEZE='docs/plans/puck-cpu-held-preparation-03-freeze.json'
STAGE='/tmp/palimpsest-puck-cpu-held-03'
OUTPUT='runs/puck-cpu-held-preparation-03'
AUDIT_STEM='/tmp/palimpsest-puck-cpu-held-preparation-03-audit-01'
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
def pin(name):
    raw=(ROOT/name).read_bytes();return dict(path=name,size_bytes=len(raw),sha256=sha(raw))
def gitpin(name):
    raw=git('show',PREP02_EVIDENCE+':'+name);return dict(path=name,size_bytes=len(raw),sha256=sha(raw),git_commit=PREP02_EVIDENCE)
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',SOURCE,'HEAD']).returncode==0
assert not (ROOT/CONFIG).exists() and not (ROOT/FREEZE).exists()
parent=load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','prep03_parent')
auditor=load(ROOT/'scripts/audit_puck_cpu_held_runtime.py','prep03_auditor')
raw01=(ROOT/PREP01).read_bytes();prep01=parent.decode(raw01)
assert parent.canonical(prep01)==raw01 and sha(raw01)=='38134e016eff974e06806f1ac74492dc51e0a5721d8cd13d1123a1fd950fe8a6'
raw02=git('show',PREP02_EVIDENCE+':'+PREP02);prep02=parent.decode(raw02)
assert parent.canonical(prep02)==raw02 and sha(raw02)=='1acfb10b40d561b8e56c96f4cd0d59ee1f00b4d0a14f62c80ffe64e22e1de3ed'
config=copy.deepcopy(prep01)
config.update(kind='puck-cpu-held-runtime-allocation-v13',version=13,allocation_id=13,stage_parent=STAGE)
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
def delta(before,label):
    keys={key:{label:before[key],'preparation03':config[key]} for key in sorted(before) if key!='sources' and before[key]!=config[key]}
    rows=[dict(path=a['path'],**{label:{k:a[k] for k in ('size_bytes','sha256')}},preparation03={k:b[k] for k in ('size_bytes','sha256')})
        for a,b in zip(before['sources'],config['sources']) if a!=b]
    assert set(before)==set(config) and [a['path'] for a in before['sources']]==[b['path'] for b in config['sources']]
    return keys,rows
diff01,sources01=delta(prep01,'preparation01');diff02,sources02=delta(prep02,'preparation02')
assert set(diff01)==set(diff02)=={'kind','version','allocation_id','stage_parent'}
assert [r['path'] for r in sources01]==['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py',
    'src/palimpsest/puck_dependency_bindings.py','src/palimpsest/puck_dependency_files.py','src/palimpsest/puck_dependency_imports.py',
    'src/palimpsest/puck_runtime_qualification.py']
assert [r['path'] for r in sources02]==['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py','src/palimpsest/puck_dependency_files.py']
python=parent.PYTHON
freeze=copy.deepcopy(json.loads((ROOT/FREEZE01).read_bytes()))
auditor_pin=pin('scripts/audit_puck_cpu_held_runtime.py')
assert auditor_pin['sha256']==parent.PREPARATION03_AUDITOR_SHA256=='6292b55088a8b4bfb60b2d65688970cd47e6a76e207f771c3d695dd463bae3cd'
freeze['audit'].update(
    acceptance=freeze['audit']['acceptance']+[
        'bare 15-element auditor argv with no timeout wrapper',
        'stderr empty; auditor elapsed below 120s and external record elapsed below 130s',
        'record keys exactly kind, command, observed_returncode, elapsed_seconds, published, stdout, stderr',
        'audit kind v13, version 13, allocation_id 13, auditor_source_sha256 equals the auditor pin',
        'synthetic extended-clock epoch-14 acceptance (QUALIFY14_LIMITS, 32 absent names, hidden roster, candidate D, 360s v5 worker) passes'],
    command_prefix=[python,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),'--configuration',str(ROOT/CONFIG),
        '--sha256',config_sha,'--transport',str(ROOT/(OUTPUT+'-external-cli-transport.json'))],
    output=AUDIT_STEM+'.json',stdout=AUDIT_STEM+'.stdout',stderr=AUDIT_STEM+'.stderr',record=AUDIT_STEM+'.external-cli.json')
freeze.update(kind='puck-cpu-held-preparation03-prospective-freeze-v1',version=1,allocation_id=13,
    command=[python,'-I','-S','-B',str(ROOT/'scripts/observe_puck_cpu_held_allocation.py'),'--configuration',str(ROOT/CONFIG),'--sha256',config_sha],
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=SOURCE,
    transport_path=str(ROOT/(OUTPUT+'-external-cli-transport.json')),output=OUTPUT,stage_parent=STAGE,
    pins=dict(configuration=pin(CONFIG),observer=pin('scripts/observe_puck_cpu_held_allocation.py'),auditor=auditor_pin,
        interpreter=dict(config['interpreter']),sources=config['sources']),
    previous_preparation=dict(configuration=pin(PREP01),freeze=pin(FREEZE01),status='ACCEPTED_BUT_STAGE_LOST_ON_REBOOT'),
    preparation02=dict(configuration=gitpin(PREP02),freeze=gitpin('docs/plans/puck-cpu-held-preparation-02-freeze.json'),
        archive_record=gitpin('docs/reports/puck-cpu-held-preparation-02/archive-record.json'),result_sha256='4ef13965e6f312a0bcdef9c49e57190f6a9526988f20f1959357bcc31400e0d4',
        stage_parent='/tmp/palimpsest-puck-cpu-held-02',status='ACCEPTED_STAGE_RETAINED_UNTOUCHED',
        consumed_by='runtime11 (packet 11b) failed on the 180s deadline during import mujoco; never read or touched by these controls'),
    boot_guard='Every preflight requires boot_id '+BOOT+'; audit and archive refuse any staged-root dev/inode differing from result.staged_roots',
    consumer='qualification epoch 14 only (360/375/390s clocks, 360s v5 worker); epochs 10/11 refuse preparation03',
    review=dict(scope='independent source review 04 of 8f3a138..f05bd69 (APPROVE); these controls still need an independent controls review',
        status='Source approved; controls not yet reviewed'),
    verification=dict(scope='offline metadata and fixture proofs only; no allocation, observer, auditor or qualifier invoked',
        path='docs/plans/puck-cpu-held-preparation-03-tools/validation'),
    scope='One data-only CPU preparation03 (allocation 13); invocation still requires a fresh boot/pin/resource preflight')
assert freeze['environment']==dict(LANG='C.UTF-8',LC_ALL='C.UTF-8',PATH='/usr/bin:/bin',PYTHONDONTWRITEBYTECODE='1')
assert freeze['cwd']==str(ROOT) and freeze['fresh_admission_required'] is True
freeze_raw=(json.dumps(freeze,indent=2,sort_keys=True)+'\n').encode()
with (ROOT/FREEZE).open('xb') as out:out.write(freeze_raw)
print(json.dumps(dict(configuration=dict(path=CONFIG,size_bytes=len(raw),sha256=config_sha),
    freeze=dict(path=FREEZE,size_bytes=len(freeze_raw),sha256=sha(freeze_raw)),
    diff_vs_preparation01=dict(top_level=diff01,changed_sources=sources01,unchanged_sources=24-len(sources01)),
    diff_vs_preparation02=dict(top_level=diff02,changed_sources=sources02,unchanged_sources=24-len(sources02)),
    validators=dict(parent_validate_configuration='PASS',auditor_configuration='PASS',allocation_output=OUTPUT),
    canonical_serializer='qualify_puck_cpu_held_runtime.canonical (reproduces preparation01 and preparation02 bytes exactly)',
    allocation_invoked=False,stages_touched=False),indent=2,sort_keys=True))
