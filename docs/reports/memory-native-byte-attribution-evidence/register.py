"""Freeze a new attribution study; hash files only, never decode snapshots."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from scripts import memory_decision_pilot as p, memory_restore_offline_readout as o

repo=Path.cwd(); workspace=repo/'.superpowers/sdd/memory-native-byte-attribution'
evidence=repo/'docs/reports/memory-native-byte-attribution-evidence'
prior=repo/'docs/reports/memory-restore-offline-readout-evidence'
old=p.read_json(prior/'registration.json'); deadline=time.monotonic()+180
if subprocess.check_output(['git','status','--porcelain']):
    raise ValueError('Commit implementation and software evidence before registration')
sets=list(old['preserved_sets'])
for reference in sets:o.verify_inventory(reference,deadline)
sets.extend({'root':str(path),'files':p.hash_ledger(path,deadline)}
    for path in (prior,Path(old['output'])))
paths=[Path(row['path']) for row in old['bound_files']]
paths.extend([evidence/'execute-readout.py',evidence/'source-review.json',
    repo/'docs/plans/memory-native-byte-attribution.md',prior/'registration.json',
    repo/'.superpowers/sdd/memory-restore-offline-readout/offline-launched.json'])
assert len(paths)==len(set(paths))
stamp=datetime.now(timezone.utc)
output=repo/'runs'/('memory-native-byte-attribution-'+stamp.strftime('%Y%m%dT%H%M%SZ'))
full=(workspace/'full-suite.log').read_text()
match=re.search(r'(\d+) passed, (\d+) skipped, (\d+) warnings in ([\d.]+)s',full)
if match is None:raise ValueError('Successful full suite required')
passed,skipped,warnings,seconds=match.groups()
reg=dict(old,study_id='memory-native-byte-attribution',readout_kind='native-byte-attribution-v1',
    parent_head='29b01b535d2e09f257f47811b7dbccbaf906b52c',created_utc=stamp.isoformat(),
    implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    output=str(output),preserved_sets=sets,runtime_identity=o.runtime_identity(),
    source_identity=p.source_identity(repo,old['assets']),
    bound_files=[{'path':str(path),'bytes':path.stat().st_size,'sha256':p.file_hash(path)} for path in paths],
    free_bytes_at_registration=shutil.disk_usage(repo).free,native_byteorder=sys.byteorder,
    source_review=p.read_json(evidence/'source-review.json'),
    qualifier='Separate timer-byte attribution and arena-eligibility readout; previous dispositions/gates unchanged',
    software_verification={'focused_passed':38,'full_passed':int(passed),'full_skipped':int(skipped),
        'warnings':int(warnings),'full_seconds':float(seconds)})
if output.exists() or (workspace/'offline-launched.json').exists():
    raise ValueError('Study invocation/output already consumed')
p.safe_output(output,[Path(row['root']) for row in sets]+p.source_paths(repo,old['assets'],old['history_root']))
if reg['free_bytes_at_registration']<10*p.GiB:raise ValueError('Insufficient free space')
with (evidence/'registration.json').open('x') as stream:
    json.dump(reg,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'implementation_commit':reg['implementation_commit'],'output':str(output),
    'preserved_set_counts':[len(row['files']) for row in sets],
    'bound_files':len(paths),'runtime_identity':reg['runtime_identity'],
    'free_bytes':reg['free_bytes_at_registration'],'software_verification':reg['software_verification']},indent=2))
