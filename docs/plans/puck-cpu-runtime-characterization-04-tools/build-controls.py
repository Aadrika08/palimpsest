"""Write the characterization-04 configuration and prospective freeze once; never invokes anything.

The configuration is the parent's own ``configuration(source_rows())`` serialized in the
pretty form the parent and the auditor both require. Both pure validators must accept it.
Preparation02/03 stages are never read here.
Usage: python3.11 -I -S -B build-controls.py
"""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
SOURCE='ea9500e309a9f72122932a62107c46af89417d77'
CONFIG='docs/plans/puck-cpu-runtime-characterization-04.json'
FREEZE='docs/plans/puck-cpu-runtime-characterization-04-freeze.json'
TOOLS='docs/plans/puck-cpu-runtime-characterization-04-tools'
OUTPUT='runs/puck-cpu-runtime-characterization-04'
AUDIT_STEM='/tmp/palimpsest-puck-cpu-characterization-04-audit-01'
ARCHIVE='docs/reports/puck-cpu-characterization-04'
RECORDS_ARCHIVE='docs/reports/puck-cpu-characterization-04-records'
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
AUDITOR_SHA='1608a3d79a2ebb10723023b25c054401bbd598b2e95508422b1e6bfaa2efac46'
UPSTREAM='8d964599119b420de67ee259434d273651a1a76d'
SCRIPTS=dict(parent='scripts/characterize_puck_cpu_episode.py',worker='scripts/characterize_puck_episode_worker.py',
    observer='scripts/observe_puck_cpu_episode_characterization.py',auditor='scripts/audit_puck_cpu_episode_characterization.py',
    archive='scripts/archive_puck_episode_characterization.py',derivation='scripts/derive_puck_episode_profile.py',
    qualifier='scripts/qualify_puck_cpu_held_runtime.py',held_auditor='scripts/audit_puck_cpu_held_runtime.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args,cwd=ROOT):return subprocess.check_output(['git','-C',str(cwd),*args])
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
def pin(name):
    raw=(ROOT/name).read_bytes();return dict(path=name,size_bytes=len(raw),sha256=sha(raw))
def committed(path):
    """HEAD bytes of one source, reading the fly-gym submodule at its own pinned HEAD."""
    if path.startswith('upstream/fly-gym/'):return git('show','HEAD:'+path[len('upstream/fly-gym/'):],cwd=ROOT/'upstream/fly-gym')
    return git('show','HEAD:'+path)
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain','--','.',':!'+TOOLS)==b''
assert git('rev-parse','HEAD',cwd=ROOT/'upstream/fly-gym').decode().strip()==UPSTREAM
assert git('ls-files','-s','upstream/fly-gym').decode().split()[1]==UPSTREAM
assert not (ROOT/CONFIG).exists() and not (ROOT/FREEZE).exists()
parent=load(ROOT/SCRIPTS['parent'],'char04_parent');auditor=load(ROOT/SCRIPTS['auditor'],'char04_auditor')
qualifier=load(ROOT/SCRIPTS['qualifier'],'char04_qualifier');held=load(ROOT/SCRIPTS['held_auditor'],'char04_held_auditor')
config=parent.configuration(parent.source_rows())
raw=(json.dumps(config,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
parent.validate_configuration(json.loads(raw));capsule=auditor.validate_configuration(json.loads(raw))
assert json.loads(raw)==config and parent.EPISODE['upstream_commit']==UPSTREAM
for row in config['sources']:assert committed(row['path'])==(ROOT/row['path']).read_bytes(),row['path']
assert [r['path'] for r in config['sources']]==list(parent.SOURCES)==list(qualifier.PREPARATION04_SOURCES)==list(held.PREPARATION04_SOURCES)
assert sha((ROOT/SCRIPTS['auditor']).read_bytes())==AUDITOR_SHA==qualifier.CHARACTERIZATION04_AUDITOR_SHA256==held.CHARACTERIZATION04_AUDITOR_SHA256
assert config['episode']['run_ids']==dict(source='a6effc7912fec337875d13ae69445e43',replay='6c04b9ed22c383fda860fa3b4f8bab13')
native=json.loads((ROOT/parent.NATIVE_METADATA_PIN['path']).read_bytes())
assert native['kind']=='puck-cpu-characterization-native-metadata-v6' and len(native['native_files'])==60
with (ROOT/CONFIG).open('xb') as out:out.write(raw)
assert (ROOT/CONFIG).read_bytes()==raw
config_sha=sha(raw);python=parent.PYTHON
transport=str(ROOT/(OUTPUT+'-external-cli-transport.json'))
freeze=dict(kind='puck-cpu-runtime-characterization04-prospective-freeze-v1',version=1,
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=SOURCE,upstream_fly_gym_commit=UPSTREAM,
    configuration_kind=config['kind'],output=OUTPUT,transport_path=transport,
    command=[python,'-I','-S','-B',str(ROOT/SCRIPTS['observer']),'--configuration',str(ROOT/CONFIG),'--sha256',config_sha],
    cwd=str(ROOT),environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'),
    clocks=dict(parent_normal_child_hard_hard=[360,375,390],observer_normal_alarm_cleanup=[420,435,5],observer_outer_bound=460,
        auditor_deadline_alarm=[300,310],audit_outer_bound=330,archive_outer_bound=120),
    audit=dict(command_prefix=[python,'-I','-S','-B',str(ROOT/SCRIPTS['auditor']),'--configuration',str(ROOT/CONFIG),
            '--sha256',config_sha,'--transport',transport],
        output=AUDIT_STEM+'.json',stdout=AUDIT_STEM+'.stdout',stderr=AUDIT_STEM+'.stderr',record=AUDIT_STEM+'.external-cli.json',
        transport_sha256_binding='Computed from the raw observer transport after its single completed invocation; never a placeholder',
        acceptance=['bare 15-element auditor argv with no timeout wrapper; normal zero exit; stderr empty',
            'published and stdout PASS bytes identical; external record elapsed below 330s',
            'kind cpu-episode-characterization-outcome-audit-v1, status PASS, auditor_source_sha256 '+AUDITOR_SHA,
            'verified configuration/result/source/replay report/transport SHA-256s equal the observed bytes',
            'every authority field false and target_code_executed_by_auditor false']),
    archive=dict(command=[python,'-I','-S','-B',str(ROOT/SCRIPTS['archive']),'--configuration',str(ROOT/CONFIG),'--audit',AUDIT_STEM+'.json'],
        destination=ARCHIVE,records=RECORDS_ARCHIVE,index_kind='cpu-episode-characterization-evidence-index-v1',
        preparation04_paths=dict(qualifier.EPISODE_OBSERVATION_PATHS),
        acceptance=['source archive tool exit 0 with its receipt equal to the written evidence-index.json',
            'qualifier validate_observation_links (version 15) accepts the archived index and frozen configuration',
            'qualifier validate_episode_observation accepts the archive with a synthetic candidate bound to these pins',
            'every characterization-04 import miss outside stdlib is declared by EPISODE_NEGATIVE_IMPORTS or EPISODE_HIDDEN_IMPORTS']),
    pins=dict(configuration=pin(CONFIG),**{k:pin(v) for k,v in SCRIPTS.items()},native_metadata=dict(parent.NATIVE_METADATA_PIN),
        observation02_configuration=dict(parent.OBSERVATION02_PIN),interpreter=dict(path=python,size_bytes=parent.INTERPRETER['size_bytes'],
        sha256=parent.INTERPRETER['sha256']),sources=config['sources'],inputs=config['inputs']),
    capsule_files=len(capsule),native_files=len(native['native_files']),native_aliases=len(native['aliases']),
    boot_guard='Every preflight requires boot_id '+BOOT+'; observer, audit and archive refuse a boot change',
    untouched=dict(stages=['/tmp/palimpsest-puck-cpu-held-02','/tmp/palimpsest-puck-cpu-held-03'],
        outputs=['runs/puck-cpu-held-preparation-02','runs/puck-cpu-held-preparation-03'],
        rule='lstat identity of these four directories only (never listed, opened or written); compared before and after each one-shot step'),
    consumer='derivation of import-profile candidate 02 (derive_puck_episode_profile.py) and preparation04 (allocation 15), which must pin exactly these sources',
    claims=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,executable=False),
    fresh_admission_required=True,
    review=dict(status='Controls not yet independently reviewed'),
    verification=dict(scope='offline fixture proofs and a dry-run preflight only; no real observer, parent, auditor, archive or derivation invoked',
        path=TOOLS+'/validation'),
    scope='One-shot characterization-04 observation evidence only; invocation still requires a fresh boot/pin/resource preflight')
freeze_raw=(json.dumps(freeze,indent=2,sort_keys=True)+'\n').encode()
with (ROOT/FREEZE).open('xb') as out:out.write(freeze_raw)
print(json.dumps(dict(configuration=dict(path=CONFIG,size_bytes=len(raw),sha256=config_sha),
    freeze=dict(path=FREEZE,size_bytes=len(freeze_raw),sha256=sha(freeze_raw)),
    serializer="json.dumps(parent.configuration(parent.source_rows()),sort_keys=True,indent=2,allow_nan=False)+'\\n'",
    validators=dict(parent_validate_configuration='PASS',auditor_validate_configuration='PASS',capsule_files=len(capsule)),
    sources=len(config['sources']),inputs=len(config['inputs']),sources_equal_head=True,sources_equal_preparation04_sources=True,
    auditor_sha256=AUDITOR_SHA,run_ids=config['episode']['run_ids'],invoked=False,stages_touched=False),indent=2,sort_keys=True))
