"""Repin uninvoked08 controls after the reviewed raw-stream fix."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain');BASE='docs/plans/puck-cpu-held-qualification-08';PROOF=BASE+'-source-evidence'
proof=ROOT/PROOF
for name,original in [('history-warm-check.py','/tmp/palimpsest-held08-history-check.py'),
    ('history-red02.stdout','/tmp/palimpsest-held08-history-unit-red02/stdout.log'),('history-red02.stderr','/tmp/palimpsest-held08-history-unit-red02/stderr.log'),
    ('history-green02.stdout','/tmp/palimpsest-held08-history-unit-green02/stdout.log'),('history-green02.stderr','/tmp/palimpsest-held08-history-unit-green02/stderr.log'),
    ('control-selfcheck01.py','/tmp/palimpsest-held08-control-selfcheck.py'),('control-selfcheck01.json','/tmp/palimpsest-held08-control-selfcheck.json')]:
    assert not (proof/name).exists();shutil.copyfile(original,proof/name)
shutil.copyfile(__file__,proof/'control-revision02.py')
(proof/'history-warm-check-record.json').write_text(json.dumps(dict(scope='five small control checks, no admission main/payload census/runtime',
    command=['/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11','-I','-S','-B','/tmp/palimpsest-held08-history-check.py'],outer_timeout_seconds=30,
    red=dict(exit_code=1,tests=5,errors=1,tool_chunk='92bfd4',failure='Repeated metadata/data role differs'),
    green=dict(exit_code=0,tests=5,errors=0,failures=0,tool_chunk='6b2989'),
    limitations='Initial4 are included in final5. Warm regression executes the real manifest-read helper and historical checker with the authenticated byte holder; no admission main or installed imports.'),indent=2,sort_keys=True)+'\n')
review=ROOT/(BASE+'-review.md');s=review.read_text()
s=s.replace('Four small history-control checks pass: genuine07 and balanced descriptors,\nchanged transport refusal, and refusal of either fabricated07 receipt. Initial\nREDs remain preserved. These checks do not invoke admission main or any vendor.',
'''Five small history-control checks pass: genuine07 and balanced descriptors,
changed transport refusal, refusal of either fabricated07 receipt, and manifest
first-read ordering with the real byte holder. Review found four07 streams were
first held as metadata; the warm regression reproduced that refusal, then passed
after assigning their byte roles at the shared manifest read. The initial four
checks are included in the final five. Initial controls and both REDs remain
preserved. No admission main or vendor was invoked.''')
review.write_text(s)
def pin(name):
    raw=(ROOT/name).read_bytes();return dict(path=name,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
p=ROOT/(BASE+'-freeze.json');value=json.loads(p.read_bytes());pins={r['path']:r for r in value['pins']}
changed=[]
for name,row in list(pins.items()):
    now=pin(name)
    if now!=row:changed.append(name);pins[name]=now
assert set(changed)=={BASE+'-admission.py',BASE+'-review.md'},changed
for path in sorted(proof.rglob('*')):
    if path.is_file():pins[str(path.relative_to(ROOT))]=pin(str(path.relative_to(ROOT)))
value.update(control_revision=2,previous_uninvoked_control_freeze=pin(PROOF+'/pre-review01/puck-cpu-held-qualification-08-freeze.json'),
    control_revision_reason='Correct four historical07 stream byte roles before manifest reads; no admission or allocation invoked.',pins=[pins[name] for name in sorted(pins)])
raw=(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode();p.write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest();old=(ROOT/'docs/plans/puck-cpu-held-qualification-07-external.py').read_bytes()
wrapper=old.replace(b'qualification-07',b'qualification-08').replace(b'qualification07',b'qualification08').replace(b'held07',b'held08')
wrapper=wrapper.replace(b'6230a4072b3606efd41efc694f0da15671d248f2cd39203f4eb2ca39ead22d17',sha.encode()).replace(b'len(raw)==124995',('len(raw)=='+str(len(raw))).encode())
(ROOT/(BASE+'-external.py')).write_bytes(wrapper);Path('/tmp/palimpsest-held08-external.py').write_bytes(wrapper)
envelope=ROOT/(BASE+'-execution.json');execution=json.loads(envelope.read_bytes())
execution['freeze'].update(size_bytes=len(raw),sha256=sha)
execution['wrapper'].update(size_bytes=len(wrapper),sha256=hashlib.sha256(wrapper).hexdigest())
envelope.write_text(json.dumps(execution,indent=2,sort_keys=True)+'\n')
result=dict(control_revision=2,freeze_sha256=sha,freeze_size_bytes=len(raw),pins=len(pins),pinned_bytes=sum(r['size_bytes'] for r in pins.values()),wrapper_sha256=hashlib.sha256(wrapper).hexdigest(),wrapper_size_bytes=len(wrapper),admission_invoked=False,runtime_invoked=False)
Path('/tmp/palimpsest-held08-control-revision02.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result))
