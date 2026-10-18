"""Derive episode import-profile candidate 02 once from the archived characterization-04 evidence.

Runs scripts/derive_puck_episode_profile.py as one exact argv on the pinned interpreter
(-I -S -B, fixed env, cwd ROOT). Inputs are the git-tracked characterization-04 archive,
the retained inventory, native metadata 06, the accepted site root and, as --template,
the epoch-14 accepted candidate D (docs/plans/puck-cpu-pillow-origin-profile-v1.json).
Every input is pinned before the run and re-read after it; the derivation writes the
candidate exclusively, and this tool writes one exclusive record of the run.
Usage: python3.11 -I -S -B derive-candidate-02.py
"""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
ARCHIVE='docs/reports/puck-cpu-characterization-04'
OUTPUT='docs/plans/puck-cpu-episode-import-profile-candidate-02.json'
RECORD='docs/plans/puck-cpu-held-preparation-04-tools/validation/candidate-02-derivation.json'
SITE=str(ROOT/'runs/puck-cpu-install-01/site')
ENVIRONMENT=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
INPUTS=dict(configuration=ARCHIVE+'/frozen-configuration.json',result=ARCHIVE+'/raw/result.json',
    source=ARCHIVE+'/raw/payload/source/characterization.json',replay=ARCHIVE+'/raw/payload/replay/characterization.json',
    audit=ARCHIVE+'/outcome-audit-04.json',template='docs/plans/puck-cpu-pillow-origin-profile-v1.json',
    inventory='runs/puck-cpu-retained-admission-02/inventory.json',native='docs/plans/puck-cpu-characterization-native-metadata-06.json',
    deriver='scripts/derive_puck_episode_profile.py')
# Candidate D: the epoch-14 accepted candidate (qualification-10 admission amendment 02 inputs.candidate).
TEMPLATE_SHA='6eba35557f64b8f7108558b1334d488da20b2381d0e69ffece090645f8fb8d3d'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def pins():
    return {k:dict(path=v,size_bytes=len(raw),sha256=sha(raw)) for k,v in INPUTS.items() for raw in ((ROOT/v).read_bytes(),)}


def main():
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and str(Path(sys.executable).resolve())==PYTHON
    assert len(sys.argv)==1,__doc__
    assert not os.path.lexists(ROOT/OUTPUT) and not os.path.lexists(ROOT/RECORD)
    before=pins();assert before['template']['sha256']==TEMPLATE_SHA
    candidate_d=json.loads((ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json').read_bytes())['inputs']['candidate']
    assert candidate_d==dict(path=INPUTS['template'],size_bytes=before['template']['size_bytes'],sha256=TEMPLATE_SHA)
    command=[PYTHON,'-I','-S','-B',str(ROOT/INPUTS['deriver'])]
    for name in ('configuration','result','source','replay','audit','template','inventory','native'):command+=['--'+name,str(ROOT/INPUTS[name])]
    command+=['--site-root',SITE,'--output',str(ROOT/OUTPUT)]
    started=time.monotonic()
    process=subprocess.run(command,cwd=ROOT,env=ENVIRONMENT,stdin=subprocess.DEVNULL,capture_output=True,timeout=300)
    elapsed=time.monotonic()-started;after=pins()
    record=dict(kind='palimpsest-prep04-candidate02-derivation-v1',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        command=command,cwd=str(ROOT),environment=ENVIRONMENT,returncode=process.returncode,elapsed_seconds=elapsed,
        stdout=process.stdout.decode('utf-8','replace'),stderr=process.stderr.decode('utf-8','replace'),
        stdout_sha256=sha(process.stdout),stderr_sha256=sha(process.stderr),inputs=before,inputs_unchanged=before==after,
        template_role='epoch-14 accepted candidate D (qualification-10 admission amendment 02 inputs.candidate)',output=None)
    if os.path.lexists(ROOT/OUTPUT):
        raw=(ROOT/OUTPUT).read_bytes();record['output']=dict(path=OUTPUT,size_bytes=len(raw),sha256=sha(raw))
    with open(ROOT/RECORD,'x') as stream:stream.write(json.dumps(record,indent=2,sort_keys=True)+'\n')
    ok=(process.returncode==0 and record['inputs_unchanged'] and record['output'] is not None and process.stderr==b''
        and json.loads(process.stdout)['sha256']==record['output']['sha256'])
    print(json.dumps(dict(ok=ok,returncode=process.returncode,output=record['output'],elapsed_seconds=elapsed),sort_keys=True))
    return 0 if ok else 1


if __name__=='__main__':raise SystemExit(main())
