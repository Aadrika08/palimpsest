"""Build distinct08 metadata once; do not invoke admission or runtime."""
from pathlib import Path
import copy,datetime,hashlib,json,shutil,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
SOURCE='f5523dc69c8d05ee2f3ff1118c633512c4b6a2e0'
OLD='docs/plans/puck-cpu-held-qualification-07-freeze.json'
NEW='docs/plans/puck-cpu-held-qualification-08-freeze.json'
PROOF='docs/plans/puck-cpu-held-qualification-08-source-evidence'
proof=ROOT/PROOF;assert not proof.exists();proof.mkdir()
for name,original in [('history-check.py','/tmp/palimpsest-held08-history-check.py'),
                      ('history-red01.stdout','/tmp/palimpsest-held08-history-unit-red01/stdout.log'),
                      ('history-red01.stderr','/tmp/palimpsest-held08-history-unit-red01/stderr.log'),
                      ('history-admission-before.py','/tmp/palimpsest-held08-history-unit-red01/admission-before.py'),
                      ('history-green01.stdout','/tmp/palimpsest-held08-history-unit-green01/stdout.log'),
                      ('history-green01.stderr','/tmp/palimpsest-held08-history-unit-green01/stderr.log')]:
    shutil.copyfile(original,proof/name)
shutil.copyfile(__file__,proof/'freeze-builder.py')
(proof/'history-check-record.json').write_text(json.dumps(dict(scope='four small control checks, no admission main/payload census/runtime',
    command=['/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11','-I','-S','-B','/tmp/palimpsest-held08-history-check.py'],
    outer_timeout_seconds=30,red=dict(exit_code=1,tests=4,failures=2,errors=2,tool_chunk='a6d29b'),
    green=dict(exit_code=0,tests=4,failures=0,errors=0,tool_chunk='26dc9f'),
    limitations='Two RED errors are missing new helper; two failures are fabricated07 receipts accepted before the guards. No installed numerical import, live payload pass or actual08 invocation.'),indent=2,sort_keys=True)+'\n')
review='''# Prospective held CPU qualification 08

The product checkpoint is one real CPU episode recorded, replayed and exported.
This distinct diagnostic run is its runtime prerequisite; attempts 01–07 remain
consumed. Source support is reviewed at f5523dc (PR167), with 630 authored checks.

Configuration 08 changes only its identity and three current source pins versus
07: parent, bootstrap and qualifier. Relative to original preparation01, require
exactly five changed sources, retaining the old 05–07 exact-four predicates.
Candidate D, all fifteen noncandidate inputs, four preparation acceptance anchors,
twenty-four source paths, ten worker paths, environment and limits remain fixed.

The data-only admission retains full current source/input/SITE/staged/native/
interpreter bytes, directory custody, declarations, nineteen absences, resources
and normal closure checks. Keep the genuine 01–06 FAIL-result loop. A separate
07 check binds its exact failed transport/supervision, empty logs and independent
refusal, retaining absent result/baseline-after. Five changed live-source pins
are accompanied by immutable07 source archives. Sample the six recorded06/07
PID/start pairs only, with no exhaustive lifetime claim. Reserve raw bytes for
all five newly decoded historical07 JSON files before manifest reads.

Four small history-control checks pass: genuine07 and balanced descriptors,
changed transport refusal, and refusal of either fabricated07 receipt. Initial
REDs remain preserved. These checks do not invoke admission main or any vendor.

Keep admission120/130s, 512MiB AS, 40000FD and 2GiB initial/final RAM; keep runtime
180s normal return, 190s child hard, 200s parent hard and all other existing bounds.
The external wrapper changes only08 names and frozen size/SHA:145s admission/audit,
240s observer, outer155/250s and5s kill grace. Existing07 wrapper proof is retained;
there is no new wrapper behavior or retry route.

After independent exact-control review and a pushed control commit, run one fresh
full admission and inspect its normal zero transport, published/stdout equality,
closure and receipt review. Refresh pins, resources and all future-output absences
immediately before the sole observer. Construct the exact audit command only
from the complete measured observer transport. Both external normal zero and an
independent PASS are required for runtime acceptance. A failure consumes08;
retain diagnostics and missing receipts without inventing cause or closure.

No operator, renderer, physics, inference, collection, scientific study, protected
catalog, release or physical rover authority follows. All seven release gates
remain open. No automatic merge or CI is included.
'''
(ROOT/'docs/plans/puck-cpu-held-qualification-08-review.md').open('x').write(review)
def load(name):return json.loads((ROOT/name).read_bytes())
def pin(name):
    raw=(ROOT/name).read_bytes();assert len(raw)<=16*1024**2,name
    return dict(path=name,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
old=load(OLD);config=load('docs/plans/puck-cpu-held-qualification-08.json');pins={};changed=[]
def add(row):
    if isinstance(row,str):row=pin(row)
    assert pin(row['path'])==row,row['path']
    assert row['path'] not in pins or pins[row['path']]==row,row['path']
    pins[row['path']]=row
allowed={'scripts/qualify_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py','scripts/puck_worker_bootstrap.py','src/palimpsest/puck_runtime_qualification.py'}
for row in old['pins']:
    current=pin(row['path'])
    if current!=row:
        assert row['path'] in allowed,row['path']
        archive=dict(row,path='docs/reports/puck-cpu-held-qualification-07/source/'+row['path']);add(archive)
        changed.append(dict(historical_live_path=row['path'],historical_pin=row,archived_pin=archive,current_pin=current))
    add(current)
assert {row['historical_live_path'] for row in changed}==allowed
for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):add(row)
for path in [OLD,'docs/plans/puck-cpu-held-qualification-08.json','docs/plans/puck-cpu-held-qualification-08-admission.py','docs/plans/puck-cpu-held-qualification-08-review.md',
             'docs/reports/puck-cpu-held-qualification-07.md','docs/reports/puck-cpu-runtime-phase-trace-v1.md','docs/reports/puck-cpu-diagnostic-epoch08-v1.md']:
    add(path)
for stem in ('puck-cpu-held-qualification-07','puck-cpu-runtime-phase-trace-v1','puck-cpu-diagnostic-epoch08-v1'):
    parent='docs/reports/'+stem;index=load(parent+'/evidence-index.json');add(parent+'/evidence-index.json')
    for row in index['artifacts']:add(dict(path=parent+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256']))
    if stem=='puck-cpu-held-qualification-07':
        for row in index['artifacts']:
            origin=Path(row['original_path'])
            if origin.is_relative_to(ROOT) and origin.parts[len(ROOT.parts)]=='runs':
                add(dict(path=str(origin.relative_to(ROOT)),size_bytes=row['size_bytes'],sha256=row['sha256']))
for path in sorted(proof.iterdir()):add(str(path.relative_to(ROOT)))
for path in subprocess.check_output(['git','ls-files','docs/plans/puck-cpu-held-qualification-07-source-evidence'],cwd=ROOT,text=True).splitlines():add(path)
new=copy.deepcopy(old)
for key in ('actual06_non_candidate_inputs_unchanged','actual07_admission_invoked_at_freeze','actual07_invoked_at_freeze','qualifications01_02_03_04_05_06_failed_consumed','historical06_replaced_live_sources','previous06_freeze'):new.pop(key)
new.update(kind='puck-cpu-held-qualification08-frozen-controls-v1',branch='research/puck-cpu-held-qualification-08',
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=SOURCE,
    actual08_invoked_at_freeze=False,actual08_admission_invoked_at_freeze=False,
    actual07_inputs_unchanged=True,qualifications01_02_03_04_05_06_07_failed_consumed=True,
    historical07_replaced_live_sources=changed,previous07_freeze=pin(OLD),
    changed_preparation_source_paths=sorted(old['changed_preparation_source_paths']+['src/palimpsest/puck_runtime_qualification.py']),
    scope='one separately admitted held four-import diagnostic qualification08; no episode, renderer, operator or scientific study',
    post03_scope='Dated DATA06/C retention only; does not replace fresh08/D full admission',
    historical07_missing_receipts=['runs/puck-cpu-held-qualification-07/'+leaf for leaf in ('result.json','baseline-after.json')],
    process_identity_samples=[dict(pid=pid,start_ticks=ticks) for pid,ticks in [(3569912,53431366),(3569913,53431366),(3569914,53431367),(3798021,53913806),(3798022,53913806),(3798023,53913807)]],
    process_scope='six recorded identities only; nonexhaustive non-atomic lifetime observation',
    pins=[pins[name] for name in sorted(pins)])
old_config=load('docs/plans/puck-cpu-held-qualification-07.json')
assert config['inputs']==old_config['inputs'] and config['preparation_acceptance']==old_config['preparation_acceptance']
assert new['limits']==config['limits']==old['limits'] and new['negative_imports']==config['negative_imports']==old['negative_imports']
new['commands']=json.loads(json.dumps(old['commands']).replace('puck-cpu-held-qualification-07','puck-cpu-held-qualification-08').replace(pin('docs/plans/puck-cpu-held-qualification-07.json')['sha256'],pin('docs/plans/puck-cpu-held-qualification-08.json')['sha256']))
raw=(json.dumps(new,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();(ROOT/NEW).open('xb').write(raw)
print(json.dumps(dict(path=NEW,sha256=hashlib.sha256(raw).hexdigest(),size_bytes=len(raw),pin_count=len(pins),pinned_bytes=sum(r['size_bytes'] for r in pins.values()),runtime_invoked=False,admission_invoked=False)))
