"""Derive the attempt-11b guard and run-once tools from the unexecuted d83dab3 copies; never invoke them.

Counted renames to held11b names, the preparation02-based control count base and freeze size,
plus the review-01 C1 stage/boot guard before every one-shot step. collect-outcome is rewritten
separately for I1/M1 and is not derived here.
"""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
OLD11='d83dab3c92387c80e81af528fea25dd3f8931598'
REL='docs/plans/puck-cpu-held-qualification-11-control-validation'
NEW=ROOT/REL
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
EVIDENCE=git('rev-parse','facc2a7').decode().strip()
GUARD_REL=REL+'/tools/stage_guard.py'
LOADER='''stage_rel='{rel}'
stage_raw=({root}/stage_rel).read_bytes()
assert stage_raw==subprocess.check_output(['git','show',{control}+':'+stage_rel],cwd={root})
stage_namespace={{'__name__':'held11b_stage_guard'}};exec(compile(stage_raw,str({root}/stage_rel),'exec'),stage_namespace)
stage=stage_namespace['check']({root})
'''
STEM=('palimpsest-held11-','palimpsest-held11b-')
PLAN={
    'pre-admission-guard.py.in':[STEM+(1,),
        ("'_held11_pre_admission_guard'","'_held11b_pre_admission_guard'",1),
        ("git('rev-parse','origin/research/puck-cpu-held-qualification-11')","git('rev-parse','origin/research/puck-cpu-held-qualification-11b')",1),
        ("git('diff','--name-only','1126b710a372a82e932d08073cfc6c13308db437',CONTROL)","git('diff','--name-only','"+EVIDENCE+"',CONTROL)",1),
        ("assert len(freeze['pins'])==2427","assert len(freeze['pins'])==2463",1),
        ("historical_records_unchanged=102,","historical_records_unchanged=103,",1),
        ("for path in controls:assert (ROOT/path).read_bytes()==git('show',CONTROL+':'+path),path\n",
         "for path in controls:assert (ROOT/path).read_bytes()==git('show',CONTROL+':'+path),path\n"+LOADER.format(rel=GUARD_REL,root='ROOT',control='CONTROL'),1),
        ("assert all(not os.path.lexists(ROOT/path) for path in before['historical_absent_paths'])\n",
         "assert all(not os.path.lexists(ROOT/path) for path in before['historical_absent_paths'])\n"
         "for row in before['preparation02_run_files']:assert pin(ROOT/row['path'])=={k:row[k] for k in ('size_bytes','sha256')},row['path']\n"
         "for name in before['historical_empty_directories']:\n"
         "    path=ROOT/name;assert path.is_dir() and not path.is_symlink() and not any(path.iterdir()),name\n"
         "assert all(not os.path.lexists(path) for path in before['attempt11_d83dab3_absent_outputs'])\n"
         "for row in freeze['attempt11_d83dab3']['git_files']:\n"
         "    raw=git('show',freeze['attempt11_d83dab3']['control_commit']+':'+row['path'])\n"
         "    assert dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())=={k:row[k] for k in ('size_bytes','sha256')},row['path']\n",1),
        ("    payload_census_or_rehash=False)\n",
         "    payload_census_or_rehash=False,stage_guard=stage,preparation02_run_files=len(before['preparation02_run_files']),\n"
         "    historical_empty_directories=len(before['historical_empty_directories']),attempt11_d83dab3='NEVER_INVOKED')\n",1)],
    'guard-path-check.py':[("prefix='held11-guard-path-'","prefix='palimpsest-held11b-guard-path-'",1)],
    'tools/run-admission-once.py.in':[STEM+(3,),
        ("stem=Path('/tmp/palimpsest-held11b-admission-tool')\n",LOADER.format(rel=GUARD_REL,root='root',control='control')+"stem=Path('/tmp/palimpsest-held11b-admission-tool')\n",1),
        ("control_commit=control,\n    runner_sha256","control_commit=control,stage_guard=stage,\n    runner_sha256",1)],
    'tools/run-observer-once.py.in':[STEM+(3,),
        ("stem=Path('/tmp/palimpsest-held11b-observer-tool')\n",LOADER.format(rel=GUARD_REL,root='root',control='control')+"stem=Path('/tmp/palimpsest-held11b-observer-tool')\n",1),
        ("control_commit=control,\n    runner_sha256","control_commit=control,stage_guard=stage,\n    runner_sha256",1)],
    'tools/run-audit-once.py.in':[STEM+(2,),
        ("stem=Path('/tmp/palimpsest-held11b-audit-tool')\n",LOADER.format(rel=GUARD_REL,root='root',control='control')+"stem=Path('/tmp/palimpsest-held11b-audit-tool')\n",1),
        ("control_commit=control,\n    runner_sha256","control_commit=control,stage_guard=stage,\n    runner_sha256",1)],
    'tools/bind-audit-command.py':[("puck-cpu-held11-external-transport-v1","puck-cpu-held11b-external-transport-v1",1),
        ("6e28bef8bebd6daecfdf34e762584312f984e0d77c7a822a119e0c89e136b212","4ab0ef1b3eab7a74d2f6dc03ab56293a65dea2d7363680b7e687aeb399d1afb5",1)],
    'tools/make-observer-guard.py':[STEM+(7,),
        ("'/tmp/palimpsest-puck-cpu-held-qualification-11-admission-01.json'","'/tmp/palimpsest-puck-cpu-held-qualification-11b-admission-01.json'",1),
        ("'/tmp/palimpsest-puck-cpu-held-qualification-11-admission-02.json'","'/tmp/palimpsest-puck-cpu-held-qualification-11b-admission-02.json'",1),
        ('historical_records_unchanged=102','historical_records_unchanged=103',2)],
    'tools/instantiate.py':[STEM+(1,),("'origin/research/puck-cpu-held-qualification-11'","'origin/research/puck-cpu-held-qualification-11b'",1)],
    'tools/archive-evidence.py.in':[STEM+(3,),
        ("source='1126b710a372a82e932d08073cfc6c13308db437'","source='8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15'",1),
        ("controls=git('diff','--name-only',source,control).decode().splitlines()","controls=git('diff','--name-only','"+EVIDENCE+"',control).decode().splitlines()",1),
        ("kind='puck-cpu-held-qualification11-terminal-evidence-v1'","kind='puck-cpu-held-qualification11b-terminal-evidence-v1'",1),
        ("admission11_status='DATA_ONLY_ADMITTED'","admission11b_status='DATA_ONLY_ADMITTED',preparation02_evidence_commit='"+EVIDENCE+"'",1),
        ('"""Archive terminal11 evidence only,','"""Archive terminal11 (packet 11b) evidence only,',1)],
}
rows=[]
for target,pairs in PLAN.items():
    old=git('show',OLD11+':'+REL+'/'+target).decode();text=old
    for a,b,count in pairs:
        assert text.count(a)==count,(target,a[:70],text.count(a))
        text=text.replace(a,b)
    for stale in ('palimpsest-held11-','1126b710a372a82e932d08073cfc6c13308db437','6e28bef8','qualification-11-admission-0','qualification-11-audit-01'):
        assert stale not in text,(target,stale)
    compile(text.replace('@CONTROL@','0'*40).replace('@COUNT@','1'),target,'exec')
    path=NEW/target;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as out:out.write(text)
    rows.append(dict(target=target,source='git '+OLD11+':'+REL+'/'+target,old_sha256=hashlib.sha256(old.encode()).hexdigest(),
        new_sha256=hashlib.sha256(text.encode()).hexdigest(),replacements=len([p for p in pairs if p[2]])))
print(json.dumps(dict(derived=rows,tools_invoked=False,admission_invoked=False,runtime_invoked=False,stage_touched=False),indent=2,sort_keys=True))
