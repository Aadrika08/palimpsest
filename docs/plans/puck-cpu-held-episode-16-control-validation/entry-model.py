"""Read-only model of the allocation-16 admission's Held entries (files + directories + links, ceiling 40,000) and bytes (ceiling 2 GiB).

Calibrates on admission14's measured peak (34,337 held files, 1,566,986,344 held bytes) with the attempt-14
file set and pinned sizes, then projects allocation 16 twice: with every attempt-14 history file pinned
(full) and with consumed docs/reports packets bound through their evidence indexes (the freeze).
Reads pins, plans and metadata only. Staged-forest paths and sizes come from the preparation04 plan, never
from the stage; the interpreter prefix is walked for directories only.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,os,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
def load(path,name):
    value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
AMENDMENT03=ROOT/'docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'
m14=load(AMENDMENT03,'entry_auditor14');m16=load(ROOT/'scripts/audit_puck_cpu_held_runtime.py','entry_auditor16')
observation=load(ROOT/'scripts/audit_puck_cpu_runtime_characterization.py','entry_observation')
admission16=load(ROOT/'docs/plans/puck-cpu-held-episode-16-admission.py','entry_admission16')
def js(name):return json.loads((ROOT/name).read_bytes())


def project(m,files,sizes,prep,stage_files):
    """Count files, links and directories for one admission; sizes: known byte sizes (pins), else lstat."""
    data={role:json.loads((ROOT/r['path']).read_bytes()) for role,r in prep['inputs'].items() if role!='generated'}
    native=data['native'];files.update(r['path'] for r in native['native_files'])
    for r in native['native_files']:sizes[r['path']]=r['size_bytes']
    baseline=data['baseline'];prefix=baseline['python_prefix']
    for p,s,_ in baseline['files']:files.add(prefix+'/'+p);sizes[prefix+'/'+p]=s
    external=list(baseline['external_libraries'])+([baseline['bwrap_executable']] if baseline.get('bwrap_executable') else [])
    for r in external:path=r.get('realpath',r.get('path'));files.add(path);sizes[path]=r['size']
    _,dependency,directories=m.plan(prep,data)
    stage=prep['stage_parent']
    for i,root in enumerate(dependency['roots']):
        for f in root['files']:path=stage+'/inputs/root-'+str(i).zfill(4)+'/'+f['path'];files.add(path);sizes[path]=f['size_bytes']
    links={prefix+'/'+p for p,_ in baseline['symlinks']}|{p for p,_ in native['aliases']}|{p for p,_ in baseline.get('host_path_aliases',[])}
    dirs=set()
    for path in list(files)+list(links):dirs.update(str(a) for a in PurePosixPath(path).parents)
    for i,names in enumerate(directories):dirs.update(stage+'/inputs/root-'+str(i).zfill(4)+'/'+d for d in names)
    dirs.update([stage,stage+'/inputs']+[stage+'/inputs/root-'+str(i).zfill(4) for i in range(4)])
    for directory,subdirs,_ in os.walk(prefix,followlinks=False):
        dirs.add(directory);dirs.update(os.path.join(directory,d) for d in subdirs if not os.path.islink(os.path.join(directory,d)))
    total=sum(sizes[p] if p in sizes else os.lstat(p).st_size for p in files)
    entries=len(files)+len(dirs)+len(links)
    return dict(files=len(files),directories=len(dirs),links=len(links),entries=entries,entry_margin=40000-entries,
        bytes=total,byte_ceiling=2048*1024**2,byte_margin=2048*1024**2-total,
        staged_files=sum(len(r['files']) for r in dependency['roots']),staged_directories=sum(len(d) for d in directories),
        staged_bytes=sum(f['size_bytes'] for r in dependency['roots'] for f in r['files']))


def attempt14():
    frozen=js('docs/plans/puck-cpu-held-qualification-14.json');prep=js('docs/plans/puck-cpu-held-preparation-03.json');manifest=js('docs/plans/puck-cpu-held-qualification-14-freeze.json')
    files={str(AMENDMENT03),str(ROOT/'docs/plans/puck-cpu-held-qualification-14-admission.py'),str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),
        str(ROOT/'scripts/audit_puck_cpu_runtime_characterization.py'),str(ROOT/'docs/plans/puck-cpu-held-qualification-14.json'),
        str(ROOT/'docs/plans/puck-cpu-held-qualification-14-freeze.json'),str(ROOT/'docs/plans/puck-cpu-held-preparation-03.json')}
    files.update(str(ROOT/r['path']) for r in observation.SUPPORT)
    rows=frozen['sources']+list(frozen['preparation_acceptance'].values())+manifest['pins']+list(prep['inputs'].values())+[frozen['inputs']['candidate']]
    sizes={str(ROOT/r['path']):r['size_bytes'] for r in rows}
    # Files the attempt-14 admission held at the f05bd69 bytes (the archived runtime14 packet source/ copies).
    for name in ('scripts/audit_puck_cpu_held_runtime.py','docs/plans/puck-cpu-held-qualification-14-admission.py'):
        archived=ROOT/'docs/reports/puck-cpu-held-qualification-14/source'/name
        if archived.exists():sizes[str(ROOT/name)]=archived.stat().st_size
    files.update(str(ROOT/r['path']) for r in rows)
    base=ROOT/'runs/puck-cpu-held-preparation-03'
    for leaf in ('result.json','configuration.json','control/copy-registration.json','control/candidate.json','control/layout.json',
            'control/stage-request.json','payload/dependencies.json','payload/stage.json','logs/stdout.log','logs/stderr.log',
            'baseline-before.json','baseline-after.json','supervision.json','invocation.json'):files.add(str(base/leaf))
    for folder,names in (('parent-source',m14.SOURCES),('worker-source',m14.WORKER)):
        files.update(str(base/folder/r['path']) for r in prep['sources'] if r['path'] in names)
    return project(m14,files,sizes,prep,None)


def episode16(pins):
    frozen=js('docs/plans/puck-cpu-held-episode-16.json');prep=js(admission16.PREP_CONFIGURATION)
    files={str(ROOT/n) for n in ('scripts/audit_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_held_episode.py','scripts/run_puck_cpu_held_episode.py',
        'scripts/qualify_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_runtime_characterization.py','docs/plans/puck-cpu-held-episode-16.json',
        'docs/plans/puck-cpu-held-episode-16-admission.py','docs/plans/puck-cpu-held-episode-16-freeze.json',admission16.PREP_CONFIGURATION,admission16.RETIREMENT)}
    files.update(str(ROOT/r['path']) for r in observation.SUPPORT)
    rows=frozen['sources']+list(frozen['preparation_acceptance'].values())+list(frozen['inputs'].values())+pins
    sizes={str(ROOT/r['path']):r['size_bytes'] for r in rows}
    files.update(str(ROOT/r['path']) for r in rows)
    history=[*admission16.HISTORICAL07_JSON,*admission16.HISTORICAL08_JSON,*admission16.HISTORICAL09_JSON,*admission16.HISTORICAL10_JSON,
        *admission16.HISTORICAL11_JSON,*admission16.HISTORICAL14_JSON,*admission16.ADMISSION01_PINS,*admission16.ADMISSION02_PINS,
        *admission16.ADMISSION11B_PINS,*admission16.ADMISSION14_PINS,*admission16.CHARACTERIZATION04_JSON,
        *(r['path'] for r in admission16.PREP02_ACCEPTANCE.values()),*(r['path'] for r in admission16.PREP03_ACCEPTANCE.values()),
        *('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json' for i in range(1,7)),
        *('runs/puck-cpu-held-qualification-'+e+'/logs/'+n+'.log' for e in ('07','08','09','10','11') for n in ('stdout','stderr')),
        *('runs/puck-cpu-held-qualification-'+e+'-external-cli.'+n for e in ('07','08','09','10','11') for n in ('stdout','stderr')),
        *('runs/puck-cpu-held-qualification-'+e+'/configuration.json' for e in ('08','09','10','11','14')),
        'runs/puck-cpu-held-qualification-14/logs/stdout.log','runs/puck-cpu-held-qualification-14/baseline-before.json',
        'runs/puck-cpu-held-qualification-14/baseline-after.json','runs/puck-cpu-held-qualification-14-external-cli.stdout',
        'runs/puck-cpu-held-qualification-14-external-cli.stderr',admission16.UNEXECUTED11['review']['path'],admission16.ADMITTED10_CONFIGURATION,
        'docs/plans/puck-cpu-held-qualification-11.json']
    files.update(str(ROOT/n) for n in history)
    base=ROOT/admission16.PREP_OUTPUT
    for leaf in ('result.json','configuration.json','control/copy-registration.json','control/candidate.json','control/layout.json',
            'control/stage-request.json','payload/dependencies.json','payload/stage.json','logs/stdout.log','logs/stderr.log',
            'baseline-before.json','baseline-after.json','supervision.json','invocation.json'):files.add(str(base/leaf))
    files.update(str(base/'parent-source'/r['path']) for r in prep['sources'])
    native=json.loads((ROOT/prep['inputs']['native']['path']).read_bytes());files.add(native['egl_vendor']['path'])
    return project(m16,files,sizes,prep,None)


def full16(freeze):
    """The same projection if every attempt-14 history file had stayed individually pinned."""
    old=js('docs/plans/puck-cpu-held-qualification-14-freeze.json')
    pins={r['path']:r for r in freeze['pins']}
    for packet,value in freeze['evidence_index_binding']['packets'].items():
        index=js(packet+'/evidence-index.json')
        for row in index['artifacts']:pins.setdefault(packet+'/'+row['archived_path'],dict(path=packet+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256']))
    for row in old['pins']:
        if row['path'] not in pins:pins[row['path']]=row
    return episode16(list(pins.values()))


freeze=js('docs/plans/puck-cpu-held-episode-16-freeze.json')
calibration=attempt14()
assert calibration['files']==34337 and calibration['bytes']==1566986344,calibration
result=dict(kind='held16-entry-and-byte-ceiling-model-v1',
    calibration=dict(attempt14=calibration,measured_admission14_peak_files=34337,measured_admission14_held_bytes=1566986344,reproduced=True),
    episode16_full_history=full16(freeze),episode16_frozen=episode16(freeze['pins']),stop_threshold_entries=39500,
    freeze=dict(pins=len(freeze['pins']),pinned_bytes=sum(r['size_bytes'] for r in freeze['pins'])),
    scope='read-only model from pins, the preparation04 plan and metadata; staged paths and sizes from the plan; no stage opened')
print(json.dumps(result,indent=2,sort_keys=True))
