"""Post-close documentary checks and copies only; no native decode or probes."""
import json
from pathlib import Path
import shutil
import time

from scripts import memory_decision_pilot as p, memory_restore_offline_readout as o

repo=Path.cwd(); evidence=repo/'docs/reports/memory-native-byte-attribution-evidence'
workspace=repo/'.superpowers/sdd/memory-native-byte-attribution'
reg=p.read_json(evidence/'registration.json'); root=Path(reg['output'])
o.recheck_inputs(reg,time.monotonic()+180)
close=p.read_json(root/'execution.json')
assert close['status']=='offline-audit-complete' and close['offline_pair_audit_complete'] is True
assert close['new_native_owners']==close['physics_steps']==0 and close['qualification_claims']==[]
assert close['registration_sha256']==p.file_hash(evidence/'registration.json')
for row in close['artifact_index']:
    path=root/row['path']
    assert path.stat().st_size==row['bytes'] and p.file_hash(path)==row['sha256']
copies={
    'execution.json':root/'execution.json','analysis.json':root/'analysis.json',
    'offline-launched.json':workspace/'offline-launched.json','wrapper.log':workspace/'wrapper.log',
    'executed-offline-driver.py':repo/'scripts/memory_restore_offline_readout.py',
    'executed-diagnostic-driver.py':repo/'scripts/memory_restore_diagnostic.py',
    'executed-pilot-driver.py':repo/'scripts/memory_decision_pilot.py',
}
published=[]
for name,source in copies.items():
    target=evidence/name
    assert not target.exists() and source.stat().st_size<=p.MiB
    shutil.copyfile(source,target)
    assert p.file_hash(source)==p.file_hash(target)
    published.append({'path':name,'source':str(source),'bytes':target.stat().st_size,'sha256':p.file_hash(target)})
receipt={'schema':'memory-native-byte-attribution-publication-v1',
    'scope':'Post-close documentary hash/copy verification; no additional scientific readout',
    'registration_sha256':p.file_hash(evidence/'registration.json'),
    'preserved_set_counts':[len(row['files']) for row in reg['preserved_sets']],
    'all_preserved_inputs_unchanged':True,'bound_files_verified':len(reg['bound_files']),
    'offline_artifact_index_verified':True,'executed_code_matches_registration':True,
    'published':published,'new_native_owners':0,'physics_steps':0,'qualification_claims':[]}
with (evidence/'publication-integrity.json').open('x') as stream:
    json.dump(receipt,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({'preserved_files':sum(receipt['preserved_set_counts']),
    'bound_files_verified':receipt['bound_files_verified'],'exact_copies':len(copies)},indent=2))
