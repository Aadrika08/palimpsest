"""Archive the consumed07 record; never run a control or target runtime."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat
import subprocess

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PACKET=ROOT/'docs/reports/puck-cpu-held-qualification-07'
CONTROL='1a1ffa06b325d0a0a60b26cff14f70992ca995ec'
SOURCE='f0b122db7ccc4fd0117b0f8527b48b3a5d3b1c61'
LIMIT=64*1024**2


def main():
    assert not PACKET.exists()
    config=json.loads((ROOT/'docs/plans/puck-cpu-held-qualification-07.json').read_bytes())
    freeze=json.loads((ROOT/'docs/plans/puck-cpu-held-qualification-07-freeze.json').read_bytes())
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==CONTROL
    assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)==''
    for row in freeze['pins']:
        raw=(ROOT/row['path']).read_bytes()
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']
    pairs={}
    def reserve(original,archive):
        original=Path(original)
        assert archive not in pairs,(archive,str(original))
        assert original.is_absolute() and not Path(archive).is_absolute() and '..' not in Path(archive).parts
        pairs[archive]=original
    source_paths=[row['path'] for row in config['sources']]
    source_paths+=['scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py']
    assert len(set(source_paths))==26
    for name in source_paths:
        assert subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT)==(ROOT/name).read_bytes(),name
        reserve(ROOT/name,'source/'+name)
    controls=['docs/plans/puck-cpu-held-qualification-07'+suffix for suffix in
              ('.json','-admission.py','-freeze.json','-review.md','-proof-roster-review.json',
               '-admission-source-review.json','-independent-review.json','-external.py','-execution.json')]
    for name in controls:
        assert subprocess.check_output(['git','show',CONTROL+':'+name],cwd=ROOT)==(ROOT/name).read_bytes(),name
        reserve(ROOT/name,'controls/'+name)
    raw_paths={row['path'] for row in config['inputs'].values()}
    raw_paths.update(row['path'] for row in config['preparation_acceptance'].values())
    raw_paths.add('docs/plans/puck-cpu-observed-import-profile-candidate-01.json')
    raw_paths.update('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json' for i in range(1,7))
    assert len(raw_paths)==27
    for name in sorted(raw_paths):reserve(ROOT/name,'inputs/'+name)
    allocation=ROOT/'runs/puck-cpu-held-qualification-07'
    names=subprocess.check_output(['rg','--files','--hidden','--no-ignore',str(allocation)],text=True).splitlines()
    assert 1<=len(names)<=128
    for name in sorted(names):reserve(name,'raw/'+str(Path(name).relative_to(allocation)))
    for suffix in ('.stdout','.stderr','-transport.json'):
        p=ROOT/('runs/puck-cpu-held-qualification-07-external-cli'+suffix)
        reserve(p,'transport/'+p.name)
    for phase in ('admission','observer','audit'):
        for suffix in ('.json','.stdout','.stderr'):
            p=Path('/tmp/palimpsest-held07-'+phase+'-external'+suffix)
            reserve(p,'external/'+p.name)
        p=Path('/tmp/palimpsest-held07-'+phase+'-terminal-tool.json')
        reserve(p,'tools/'+p.name)
    for name in ('palimpsest-puck-cpu-held-qualification-07-admission-01.json',
                 'palimpsest-puck-cpu-held-qualification-07-audit-01.json',
                 'palimpsest-held07-concrete-audit-command.json',
                 'palimpsest-held07-pre-admission-guard-01.json',
                 'palimpsest-held07-pre-observer-guard-01-refusal.json',
                 'palimpsest-held07-pre-observer-guard-02.json',
                 'palimpsest-held07-admission-result-review.json',
                 'palimpsest-held07-outcome-independent-review.json'):
        reserve(Path('/tmp')/name,'observations/'+name)
    reserve(Path(__file__).resolve(),'tools/archive_evidence.py')
    # Reuse the existing byte verifier unchanged; it has no runtime entry path.
    reserve(ROOT/'docs/plans/puck-cpu-held-qualification-07-source-evidence/verify_evidence.py','verify_evidence.py')
    known_missing=[allocation/'result.json',allocation/'baseline-after.json']
    assert all(not os.path.lexists(p) for p in known_missing)
    review=json.loads(Path('/tmp/palimpsest-held07-outcome-independent-review.json').read_bytes())
    assert review['review_status']=='BINDINGS_CONSISTENT_WITH_FAILED_CONSUMED07'
    assert review['qualification_status']=='FAILED_CONSUMED' and review['claims']['runtime_qualified'] is False
    assert {row['id'] for row in review['findings']}=={
        'INNER_NORMAL_RETURN_DEADLINE','NO_COMPLETION_OR_PARENT_CLOSURE_RECEIPT',
        'INDEPENDENT_REFUSAL_IS_EXPECTED_EARLY_GATE','NO_ROOT_CAUSE_OR_POST_CUSTODY_INFERENCE'}
    assert json.loads((allocation/'supervision.json').read_bytes())['failure']=='normal-return deadline'
    assert json.loads(Path('/tmp/palimpsest-puck-cpu-held-qualification-07-audit-01.json').read_bytes())['status']=='FAIL'
    payloads={};total=0;rows=[]
    for archive,original in sorted(pairs.items()):
        before=original.lstat();assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=16*1024**2,str(original)
        raw=original.read_bytes();after=original.lstat()
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        assert len(raw)==before.st_size and stamp(before)==stamp(after),str(original)
        total+=len(raw);assert total<=LIMIT
        payloads[archive]=raw
        rows.append(dict(archived_path=archive,original_path=str(original),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    PACKET.mkdir()
    for archive,raw in payloads.items():
        path=PACKET/archive;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
    index=dict(kind='puck-cpu-held-qualification07-evidence-index-v1',version=1,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        control_commit=CONTROL,source_commit=SOURCE,source_paths=sorted(source_paths),control_paths=controls,
        artifact_count=len(rows),total_bytes=total,empty_files=sum(row['size_bytes']==0 for row in rows),
        artifacts=rows,missing_original_paths=[str(p) for p in known_missing],
        frozen501_pins_match=True,independent_audit_status='FAIL',qualification_status='FAIL',
        actual07_invoked=True,observer_invocations_in_retained_record=1,qualifications01_07_consumed=True,
        runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,
        qualification_claims=[],implicit_retry=False,all_seven_release_gates_open=True,
        post_failure_full_payload_custody='NOT_CHECKED',parent_closure_receipt='ABSENT',
        observed_failure='normal-return deadline; child SIGTERM; no completed worker receipt',
        failure_phase='UNKNOWN: worker logs are empty',
        preserved_prior_evidence='Existing committed06/source/post03 packets are referenced by frozen pins; they are not recursively copied again.')
    with (PACKET/'evidence-index.json').open('x') as stream:
        json.dump(index,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps(dict(packet=str(PACKET),artifacts=len(rows),bytes=total,empty_files=index['empty_files'],status='ARCHIVED_FAILED_NOT_QUALIFIED'),sort_keys=True))


if __name__=='__main__':main()
