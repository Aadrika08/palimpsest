"""Write the preparation04 (allocation 15) configuration and prospective freeze once; never invokes an allocation.

The configuration is the qualifier's configuration_template for phase prepare, updated to
kind v15 / version 15 / allocation 15 / EPISODE_VERSIONS exactly as the authored preparation04
tests do, over PREPARATION04_SOURCES and the characterization-04 archive inputs plus candidate 02,
serialized with the qualifier's canonical(). It must pass the qualifier's validate_configuration
and validate_inputs, the held auditor's configuration and inputs_binding, and the pure
build_cpu_source_registration plan. Preparation02/03 stages are never read here.
Usage: python3.11 -I -S -B build-controls.py
"""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
SOURCE='5dc2010d9c429d860d80f505585a012d8cf92493'
TOOLS='docs/plans/puck-cpu-held-preparation-04-tools'
CONFIG='docs/plans/puck-cpu-held-preparation-04.json'
FREEZE='docs/plans/puck-cpu-held-preparation-04-freeze.json'
CANDIDATE='docs/plans/puck-cpu-episode-import-profile-candidate-02.json'
CHAR04='docs/reports/puck-cpu-characterization-04'
STAGE='/tmp/palimpsest-puck-cpu-held-04'
OUTPUT='runs/puck-cpu-held-preparation-04'
AUDIT_STEM='/tmp/palimpsest-puck-cpu-held-preparation-04-audit-01'
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
AUDITOR_SHA='4ef23799994785c2154aeedd83a03e0457cdfd7f9e4573d12d44e462fb782f7c'
UPSTREAM='8d964599119b420de67ee259434d273651a1a76d'
SCRIPTS=dict(qualifier='scripts/qualify_puck_cpu_held_runtime.py',observer='scripts/observe_puck_cpu_held_allocation.py',
    auditor='scripts/audit_puck_cpu_held_runtime.py',episode_parent='scripts/run_puck_cpu_held_episode.py',
    episode_auditor='scripts/audit_puck_cpu_held_episode.py',characterization_parent='scripts/characterize_puck_cpu_episode.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args,cwd=ROOT):return subprocess.check_output(['git','-C',str(cwd),*args])
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
def pin(name):
    raw=(ROOT/name).read_bytes();return dict(path=name,size_bytes=len(raw),sha256=sha(raw))
def committed(path):
    if path.startswith('upstream/fly-gym/'):return git('show','HEAD:'+path[len('upstream/fly-gym/'):],cwd=ROOT/'upstream/fly-gym')
    return git('show','HEAD:'+path)
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain','--','.',':!'+TOOLS,':!'+CANDIDATE)==b''
assert git('rev-parse','HEAD',cwd=ROOT/'upstream/fly-gym').decode().strip()==UPSTREAM
assert not (ROOT/CONFIG).exists() and not (ROOT/FREEZE).exists()
q=load(ROOT/SCRIPTS['qualifier'],'prep04_qualifier');auditor=load(ROOT/SCRIPTS['auditor'],'prep04_auditor')
char=load(ROOT/SCRIPTS['characterization_parent'],'prep04_char_parent')
assert sha((ROOT/SCRIPTS['auditor']).read_bytes())==AUDITOR_SHA==q.PREPARATION04_AUDITOR_SHA256
frozen_raw=(ROOT/CHAR04/'frozen-configuration.json').read_bytes();frozen=json.loads(frozen_raw)
rows={r['path']:r for r in frozen['inputs']}
inputs={role:dict(rows[char.ROLES['native_metadata' if role=='native' else role]]) for role in
        ('inventory','layout','native','baseline','accepted_result','accepted_snapshot','accepted_audit','accepted_configuration','accepted_index')}
inputs.update({role:pin(CHAR04+'/'+path) for role,path in q.EPISODE_OBSERVATION_PATHS.items()},observation_index=pin(CHAR04+'/evidence-index.json'),
    candidate=pin(CANDIDATE))
candidate=json.loads((ROOT/CANDIDATE).read_bytes());extra=candidate['additional_package_inputs'][0]
inputs['generated']=pin(extra['root']+'/'+extra['files'][0]['path'])
assert set(inputs)==set(q.PREPARATION04_INPUT_ROLES)
sources=[]
for path in q.PREPARATION04_SOURCES:
    raw=(ROOT/path).read_bytes();assert raw==committed(path),path
    sources.append(dict(path=path,size_bytes=len(raw),sha256=sha(raw)))
assert sources==frozen['sources'],'Characterization-04 pinned other source bytes'
config=q.configuration_template(phase='prepare',root=str(ROOT),stage_parent=STAGE,sources=sources,inputs=inputs,
    negative_imports=list(q.PREPARATION_NEGATIVE_IMPORTS))
config.update(kind='puck-cpu-held-runtime-allocation-v15',version=15,allocation_id=15,expected_versions=dict(q.EPISODE_VERSIONS))
raw=q.canonical(config);config=q.decode(raw)
q.validate_configuration(config);auditor.configuration(config,False)
assert q.allocation_output(config)==auditor.allocation_output(config)==q.preparation_output(config)==OUTPUT
blobs={role:(ROOT/row['path']).read_bytes() for role,row in config['inputs'].items()}
q.validate_inputs(config,blobs)
auditor.inputs_binding(config,{role:auditor.decode(b) for role,b in blobs.items() if role!='generated'},blobs)
sys.path[:0]=[str(ROOT/'src')]
from palimpsest.puck_cpu_registration import build_cpu_source_registration  # noqa: E402
plan=build_cpu_source_registration(blobs['inventory'],blobs['layout'],blobs['candidate'],blobs['native'],
    expected_pins={k:{x:config['inputs'][k][x] for x in ('size_bytes','sha256')} for k in ('inventory','layout','candidate','native')},
    site_root=str(ROOT/q.SITE),generated_root=str((ROOT/config['inputs']['generated']['path']).parent),deadline=time.monotonic()+170)
stage_bytes=sum(f['size_bytes'] for r in plan['roots'] for f in r['files']);stage_files=sum(len(r['files']) for r in plan['roots'])
with (ROOT/CONFIG).open('xb') as out:out.write(raw)
assert (ROOT/CONFIG).read_bytes()==raw
config_sha=sha(raw);python=q.PYTHON;transport=str(ROOT/(OUTPUT+'-external-cli-transport.json'))
freeze=dict(kind='puck-cpu-held-preparation04-prospective-freeze-v1',version=1,allocation_id=15,
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=SOURCE,upstream_fly_gym_commit=UPSTREAM,
    command=[python,'-I','-S','-B',str(ROOT/SCRIPTS['observer']),'--configuration',str(ROOT/CONFIG),'--sha256',config_sha],
    cwd=str(ROOT),environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'),
    output=OUTPUT,stage_parent=STAGE,transport_path=transport,fresh_admission_required=True,
    clocks=dict(parent_normal_child_hard_hard=[180,190,200],observer_normal_alarm_cleanup=[210,225,5],observer_outer_bound=260,
        auditor_deadline_alarm=[120,130],audit_outer_bound=150,record_elapsed_below=130),
    stage_plan=dict(files=stage_files,bytes=stage_bytes,roots=len(plan['roots']),
        tmpfs_floor_bytes=config['limits']['min_tmpfs_free_bytes'],required_tmpfs_free_bytes=config['limits']['min_tmpfs_free_bytes']+stage_bytes),
    audit=dict(command_prefix=[python,'-I','-S','-B',str(ROOT/SCRIPTS['auditor']),'--configuration',str(ROOT/CONFIG),'--sha256',config_sha,
            '--transport',transport],
        output=AUDIT_STEM+'.json',stdout=AUDIT_STEM+'.stdout',stderr=AUDIT_STEM+'.stderr',record=AUDIT_STEM+'.external-cli.json',
        transport_sha256_binding='Computed from the raw observer transport after its single completed invocation; never a placeholder',
        acceptance=['bare 15-element auditor argv with no timeout wrapper; normal zero exit; stderr empty',
            'published and stdout PASS bytes identical; external record elapsed below 130s; record keys exactly preparation01',
            'audit kind v15, version 15, allocation_id 15, auditor_source_sha256 '+AUDITOR_SHA,
            'run_puck_cpu_held_episode validate_configuration and validate_acceptance, and audit_puck_cpu_held_episode validate_configuration '
            'and validate_acceptance, accept the archived pins for a synthetic allocation-16 configuration']),
    pins=dict(configuration=pin(CONFIG),**{k:pin(v) for k,v in SCRIPTS.items()},interpreter=dict(config['interpreter']),
        sources=config['sources'],inputs=config['inputs']),
    candidate02=dict(pin=config['inputs']['candidate'],template=pin('docs/plans/puck-cpu-pillow-origin-profile-v1.json'),
        derivation_record=TOOLS+'/validation/candidate-02-derivation.json',import_misses=len(candidate['import_misses'])),
    characterization04=dict(source_commit=SOURCE,archive=CHAR04,auditor_sha256=q.CHARACTERIZATION04_AUDITOR_SHA256),
    consumed_stages=dict(paths=['/tmp/palimpsest-puck-cpu-held-02','/tmp/palimpsest-puck-cpu-held-03'],
        rule='Retired only by retire-consumed-stages.py (lstat identity and content census recorded before rm -rf); every preflight '
             'accepts each either present with an unchanged lstat identity or absent with its PASS retirement record',
        outputs_untouched=['runs/puck-cpu-held-preparation-02','runs/puck-cpu-held-preparation-03']),
    boot_guard='Every preflight requires boot_id '+BOOT+'; audit and archive refuse any staged-root dev/inode differing from result.staged_roots',
    consumer='episode allocation 16 (puck-cpu-held-episode-allocation-v16) only, which reuses these sources plus its parent and these inputs',
    claims=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,executable=False),
    review=dict(status='Controls not yet independently reviewed'),
    verification=dict(scope='offline metadata and fixture proofs only; no allocation, observer, qualifier main or auditor invoked',path=TOOLS+'/validation'),
    scope='One data-only CPU preparation04 (allocation 15); invocation still requires a fresh boot/pin/resource preflight')
freeze_raw=(json.dumps(freeze,indent=2,sort_keys=True)+'\n').encode()
with (ROOT/FREEZE).open('xb') as out:out.write(freeze_raw)
print(json.dumps(dict(configuration=dict(path=CONFIG,size_bytes=len(raw),sha256=config_sha),
    freeze=dict(path=FREEZE,size_bytes=len(freeze_raw),sha256=sha(freeze_raw)),
    serializer='qualify_puck_cpu_held_runtime.canonical(configuration_template(phase=prepare,...) + v15 identity)',
    validators=dict(qualifier_validate_configuration='PASS',qualifier_validate_inputs='PASS',auditor_configuration='PASS',
        auditor_inputs_binding='PASS',build_cpu_source_registration='PASS'),
    sources=len(sources),sources_equal_characterization04=True,inputs=sorted(inputs),stage_plan=freeze['stage_plan'],
    auditor_sha256=AUDITOR_SHA,invoked=False,stages_touched=False),indent=2,sort_keys=True))
