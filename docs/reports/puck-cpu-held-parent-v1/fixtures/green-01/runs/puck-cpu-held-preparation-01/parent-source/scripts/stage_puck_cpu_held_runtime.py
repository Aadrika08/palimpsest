"""Private, data-only worker for the separately frozen CPU preparation phase."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def main():
    sys.path[:0]=['/puck/source/src','/puck/source/scripts']
    from qualify_puck_held_runtime import read,decode,write,canonical
    from palimpsest.puck_runtime_staging import stage_tmpfs_registration
    from palimpsest.puck_cpu_registration import attach_cpu_candidate
    from palimpsest.puck_retained_installation import HeldInstalledFiles
    if len(sys.argv)!=2:raise ValueError('Exact CPU stage request hash required')
    deadline=time.monotonic()+180
    request=decode(read('/puck/control/stage-request.json',1024**2,sys.argv[1]))
    get=lambda name:read(request[name]['path'],16*1024**2,request[name]['sha256'])
    raw=get('registration');registration=decode(raw);candidate_raw=get('candidate');layout=decode(get('layout'))
    root=registration['roots'][0]
    with HeldInstalledFiles(root['root'],root['files'],layout['predicted_destination_directories'],deadline) as held:
        staged=stage_tmpfs_registration(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),
            staging_root='/puck/staged/inputs',deadline=deadline)
        staged=attach_cpu_candidate(staged,candidate_raw,expected_sha256=request['candidate']['sha256'],deadline=deadline)
        held.recheck()
    payload=json.dumps(staged,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    write(Path('/output/dependencies.json'),payload,16*1024**2)
    roots=[]
    for index,row in enumerate(staged['roots']):
        state=os.stat(row['root'],follow_symlinks=False)
        roots.append(dict(root_index=index,device=state.st_dev,inode=state.st_ino))
    receipt=dict(kind='puck-cpu-tmpfs-preparation-receipt-v1',status='prepared',
        dependencies=dict(path='payload/dependencies.json',size_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest()),
        staged_roots=roots,runtime_qualified=False,native_authorized=False,collection_authorized=False,
        study_authorized=False,executable=False,qualification_claims=[])
    write(Path('/output/stage.json'),canonical(receipt))
    print(canonical(receipt).decode(),end='',flush=True)


if __name__=='__main__':raise SystemExit(main())
