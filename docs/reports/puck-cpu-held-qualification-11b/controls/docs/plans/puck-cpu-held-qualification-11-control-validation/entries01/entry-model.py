"""Read-only model of the admission's Held entries (files + directories + links, ceiling 40,000).

Reproduces admission10-02's measured peak of 33,719 held files, then projects attempt 11b.
Reads pins, plans and metadata only. Staged-forest paths are taken from the plan, never from
the preparation02 stage; the interpreter prefix is walked for directories only.
"""
from pathlib import Path,PurePosixPath
import json,os,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
AUDITOR=ROOT/'docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
m=load(AUDITOR,'entry_auditor');observation=load(ROOT/'scripts/audit_puck_cpu_runtime_characterization.py','entry_observation')
def js(name):return json.loads((ROOT/name).read_bytes())


def model(runner,manifest,configuration,prep_configuration,prep_output,history_files=()):
    frozen=js(configuration);prep=js(prep_configuration);result=js(prep_output+'/result.json')
    files={str(AUDITOR),str(ROOT/runner),str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),
        str(ROOT/'scripts/audit_puck_cpu_runtime_characterization.py'),str(ROOT/configuration),str(ROOT/manifest),str(ROOT/prep_configuration)}
    files.update(str(ROOT/r['path']) for r in observation.SUPPORT)
    rows=frozen['sources']+list(frozen['preparation_acceptance'].values())+js(manifest)['pins']+list(prep['inputs'].values())+[frozen['inputs']['candidate']]
    files.update(str(ROOT/r['path']) for r in rows)
    base=ROOT/prep_output
    for leaf in ('result.json','configuration.json','control/copy-registration.json','control/candidate.json','control/layout.json',
            'control/stage-request.json','payload/dependencies.json','payload/stage.json','logs/stdout.log','logs/stderr.log',
            'baseline-before.json','baseline-after.json','supervision.json','invocation.json'):files.add(str(base/leaf))
    for folder,names in (('parent-source',m.SOURCES),('worker-source',m.WORKER)):
        files.update(str(base/folder/r['path']) for r in prep['sources'] if r['path'] in names)
    files.update(str(ROOT/name) for name in history_files)
    data={role:json.loads((ROOT/r['path']).read_bytes()) for role,r in prep['inputs'].items() if role!='generated'}
    native=data['native']['native_files'];files.update(r['path'] for r in native)
    baseline=data['baseline'];prefix=baseline['python_prefix']
    files.update(prefix+'/'+p for p,_,_ in baseline['files'])
    external=list(baseline['external_libraries'])+([baseline['bwrap_executable']] if baseline.get('bwrap_executable') else [])
    files.update(r.get('realpath',r.get('path')) for r in external)
    _,dependency,directories=m.plan(prep,data)
    stage=prep['stage_parent']
    for i,root in enumerate(dependency['roots']):
        files.update(stage+'/inputs/root-'+str(i).zfill(4)+'/'+f['path'] for f in root['files'])
    links={prefix+'/'+p for p,_ in baseline['symlinks']}|{p for p,_ in data['native']['aliases']}|{p for p,_ in baseline.get('host_path_aliases',[])}
    dirs=set()
    for path in list(files)+list(links):dirs.update(str(a) for a in PurePosixPath(path).parents)
    for i,names in enumerate(directories):dirs.update(stage+'/inputs/root-'+str(i).zfill(4)+'/'+d for d in names)
    dirs.update([stage,stage+'/inputs']+[stage+'/inputs/root-'+str(i).zfill(4) for i in range(4)])
    for directory,subdirs,_ in os.walk(prefix,followlinks=False):
        dirs.add(directory);dirs.update(os.path.join(directory,d) for d in subdirs if not os.path.islink(os.path.join(directory,d)))
    return dict(files=len(files),directories=len(dirs),links=len(links),entries=len(files)+len(dirs)+len(links),
        limit=40000,margin=40000-(len(files)+len(dirs)+len(links)),manifest_pins=len(js(manifest)['pins']),
        staged_files=sum(len(r['files']) for r in dependency['roots']),staged_directories=sum(len(d) for d in directories))


admission02=model('docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/admission.py',
    'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/freeze.json',
    'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json',
    'docs/plans/puck-cpu-held-preparation-01.json','runs/puck-cpu-held-preparation-01')
attempt11b=model('docs/plans/puck-cpu-held-qualification-11-admission.py','docs/plans/puck-cpu-held-qualification-11-freeze.json',
    'docs/plans/puck-cpu-held-qualification-11.json','docs/plans/puck-cpu-held-preparation-02.json','runs/puck-cpu-held-preparation-02')
assert admission02['files']==33719,admission02
print(json.dumps(dict(kind='held11b-entry-ceiling-model-v1',calibration=dict(measured_admission10_02_peak_files=33719,
    model=admission02,reviewer_reported_entries10=37903,reviewer_projected_entries_d83dab3=38243),attempt11b=attempt11b,
    scope='read-only model from pins, the plan and metadata; staged paths from the plan; preparation02 stage untouched'),indent=2,sort_keys=True))
