"""Archive one PASS-audited characterization-04 outcome with its evidence index.

Copies the frozen configuration, the retained parent receipts, both worker
reports, the external transport and the independent outcome audit into a new
report directory, then writes ``evidence-index.json`` (kind
``cpu-episode-characterization-evidence-index-v1``) over every archived file.
Run directories and bundles stay under ``runs/``; their receipts remain bound
through the archived reports. Nothing is executed and nothing is overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT=Path(__file__).resolve().parents[1]
OUTPUT='runs/puck-cpu-runtime-characterization-04'
ARCHIVE='docs/reports/puck-cpu-characterization-04'
INDEX_KIND='cpu-episode-characterization-evidence-index-v1'
AUDIT_KIND='cpu-episode-characterization-outcome-audit-v1'
RETAINED=('configuration.json','egl-vendor.json','baseline-before.json','baseline-after.json','request-source.json',
    'request-replay.json','namespace.json','result.json',
    *(name+leaf for name in ('probe','source','replay') for leaf in ('-invocation.json','-supervision.json',
                                                                    '-logs/stdout.log','-logs/stderr.log')))


def sha(raw):return hashlib.sha256(raw).hexdigest()


def read(path,maximum=16*1024**2):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        state=os.fstat(fd)
        if not stat.S_ISREG(state.st_mode) or state.st_size>maximum:raise ValueError('Bounded regular archive input required: '+str(path))
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(maximum+1)
        if len(raw)!=state.st_size:raise ValueError('Archive input changed while read: '+str(path))
        return raw
    finally:os.close(fd)


def archive(configuration,audit,destination=None):
    destination=ROOT/(destination or ARCHIVE);run=ROOT/OUTPUT
    if os.path.lexists(destination):raise FileExistsError('Characterization-04 archive already exists')
    config_raw=read(Path(configuration),1024**2);audit_raw=read(Path(audit),1024**2);verdict=json.loads(audit_raw)
    result_raw=read(run/'result.json');reports={phase:read(run/('payload-'+phase)/'characterization.json',4*1024**2)
                                                for phase in ('source','replay')}
    verified=verdict.get('verified',{})
    if (verdict.get('kind')!=AUDIT_KIND or verdict.get('status')!='PASS' or verified.get('configuration_sha256')!=sha(config_raw)
            or verified.get('result_sha256')!=sha(result_raw) or verified.get('source_report_sha256')!=sha(reports['source'])
            or verified.get('replay_report_sha256')!=sha(reports['replay'])):
        raise ValueError('Only a PASS outcome audit of these exact bytes can be archived')
    transport=OUTPUT+'-external-cli-transport.json'
    files={'frozen-configuration.json':config_raw,'outcome-audit-04.json':audit_raw,
           'raw/payload/source/characterization.json':reports['source'],'raw/payload/replay/characterization.json':reports['replay']}
    for name in RETAINED:files['raw/'+name]=read(run/name)
    for name in ('-external-cli-transport.json','-external-cli.stdout','-external-cli.stderr'):
        files['external/'+Path(OUTPUT+name).name]=read(ROOT/(OUTPUT+name))
    if sha(files['external/'+Path(transport).name])!=verified.get('transport_sha256'):
        raise ValueError('Archived transport differs from the audited transport')
    destination.mkdir(parents=True)
    entries=[]
    for path,raw in sorted(files.items()):
        target=destination/path;target.parent.mkdir(parents=True,exist_ok=True)
        with open(target,'xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        entries.append(dict(path=path,size_bytes=len(raw),sha256=sha(raw)))
    receipts={phase:json.loads(raw)['episode_result']['bundle'] for phase,raw in reports.items()}
    index=dict(kind=INDEX_KIND,version=1,original_output=OUTPUT,entries=entries,file_count=len(entries),
               total_bytes=sum(row['size_bytes'] for row in entries),retained_bundles=receipts,
               scope='retained characterization-04 receipts; run directories and bundles stay under runs/')
    raw=(json.dumps(index,sort_keys=True,indent=2)+'\n').encode()
    with open(destination/'evidence-index.json','xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return dict(path=str(destination/'evidence-index.json'),size_bytes=len(raw),sha256=sha(raw),file_count=len(entries))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',required=True);parser.add_argument('--audit',required=True)
    parser.add_argument('--destination',default=ARCHIVE)
    args=parser.parse_args()
    print(json.dumps(archive(args.configuration,args.audit,args.destination),sort_keys=True))


if __name__=='__main__':main()
