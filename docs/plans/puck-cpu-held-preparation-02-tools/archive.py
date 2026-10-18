"""Archive the preparation02 audit, CLI record and terminals byte-identically, then prove acceptance.

After a fresh enforced archive preflight, copies exclusively into
docs/reports/puck-cpu-held-preparation-02/{audit,records}/, re-reads every copy, and runs
the parent's validate_preparation_acceptance plus the auditor's historical_acceptance on
the archived pins exactly as a qualification11 configuration will bind them.
"""
from pathlib import Path
import datetime,importlib.util,json,sys

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('prep02_preflight',HERE/'preflight.py')
P=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(P)
C=P.C


def plan(root=C.ROOT):
    audit=Path(root)/C.ARCHIVE/'audit';records=Path(root)/C.ARCHIVE/'records'
    pairs=[(C.AUDIT_OUTPUT,Path(root)/C.ARCHIVED_AUDIT),(C.AUDIT_RECORD,Path(root)/C.ARCHIVED_RECORD),
        (C.AUDIT_STDOUT,audit/Path(C.AUDIT_STDOUT).name),(C.AUDIT_STDERR,audit/Path(C.AUDIT_STDERR).name)]
    for name in (C.OBSERVER_TERMINAL,C.AUDIT_TERMINAL,C.OBSERVER_STDOUT,C.OBSERVER_STDERR):
        pairs.append((name,records/Path(name).name))
    for name in sorted((Path(root)/C.RECORDS).glob('preflight-*.json')):pairs.append((str(name),records/name.name))
    return pairs


def copy(pairs):
    rows=[]
    for source,target in pairs:
        raw=C.read(source);Path(target).parent.mkdir(mode=0o755,parents=True,exist_ok=True)
        C.write_new(target,raw);C.require(C.read(target)==raw,'Archived copy differs: '+str(target))
        rows.append(dict(source=str(source),archived=str(target),size_bytes=len(raw),sha256=C.sha(raw)))
    return rows


def main():
    require=C.require;require(len(sys.argv)==1,__doc__)
    preflight=P.check('archive')
    for name in (C.OBSERVER_TERMINAL,C.AUDIT_TERMINAL):P.same_record(name)
    require(C.read(C.AUDIT_RECORD)==C.read(C.ROOT/C.RECORDS/Path(C.AUDIT_RECORD).name),'Record copies differ')
    rows=copy(plan())
    parent=C.load(C.ROOT/'scripts/qualify_puck_cpu_held_runtime.py','prep02_archive_parent')
    auditor=C.load(C.ROOT/'scripts/audit_puck_cpu_held_runtime.py','prep02_archive_auditor')
    candidate=json.loads(C.read(C.ROOT/C.CANDIDATE_D_SOURCE))['inputs']['candidate']
    paths=dict(configuration=C.CONFIG,result=C.OUTPUT+'/result.json',independent_audit=C.ARCHIVED_AUDIT,externally_observed_auditor_cli=C.ARCHIVED_RECORD)
    blobs=[C.read(C.ROOT/paths[k]) for k in ('configuration','result','independent_audit','externally_observed_auditor_cli')]
    config11,proof=C.prove_parent(parent,auditor,*blobs,paths,candidate)
    proof.update(C.prove_auditor_files(auditor,config11))
    require(C.boot_id()==preflight['boot_id'],'Boot changed during archive')
    value=dict(kind='palimpsest-prep02-archive-record-v1',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        boot_id=preflight['boot_id'],head=preflight['git']['head'],copies=rows,acceptance_pins=config11['preparation_acceptance'],
        acceptance_proof=proof,preflight=preflight,scope='byte-identical archive of preparation02 audit evidence; not runtime qualification')
    C.write_new(C.ROOT/C.ARCHIVE/'archive-record.json',C.pretty(value))
    print(json.dumps(dict(status='PASS_ARCHIVED_AND_ACCEPTED',copies=len(rows),acceptance_pins=config11['preparation_acceptance'],proof=proof),indent=2,sort_keys=True))
    return 0


if __name__=='__main__':raise SystemExit(main())
