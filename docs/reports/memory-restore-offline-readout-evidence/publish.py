"""Documentary publication only: hash/copy receipts; never decode retained state."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path.cwd()
workspace = repo/'.superpowers/sdd/memory-restore-offline-readout'
dest = repo/'docs/reports/memory-restore-offline-readout-evidence'
reg_path = dest/'registration.json'
reg = json.loads(reg_path.read_text())
root = Path(reg['output'])
digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check(path, reference):
    path = Path(path)
    assert path.stat().st_size == reference['bytes'], path
    assert digest(path) == reference['sha256'], path

preserved = []
for reference in reg['preserved_sets']:
    directory = Path(reference['root'])
    actual = {str(path.relative_to(directory)) for path in directory.rglob('*') if path.is_file()}
    assert actual == {row['path'] for row in reference['files']}, directory
    for row in reference['files']:
        check(directory/row['path'], row)
    preserved.append({'root':str(directory),'files':len(actual),'unchanged':True})

executed = {}
for reference in reg['bound_files']:
    path = Path(reference['path'])
    if path == repo/'scripts/memory_restore_diagnostic.py':
        path = workspace/'executed-diagnostic-driver.py'
    check(path, reference)
    executed[reference['path']] = path

close = json.loads((root/'execution.json').read_text())
assert close['status'] == 'offline-audit-complete'
assert close['offline_pair_audit_complete'] is True
assert close['qualification_claims'] == []
assert close['new_native_owners'] == close['physics_steps'] == 0
assert close['registration_sha256'] == digest(reg_path)
for row in close['artifact_index']:
    check(root/row['path'], row)

copies = {
    'execution.json':root/'execution.json',
    'analysis.json':root/'analysis.json',
    'offline-launched.json':workspace/'offline-launched.json',
    'executed-offline-driver.py':executed[str(repo/'scripts/memory_restore_offline_readout.py')],
    'executed-diagnostic-driver.py':executed[str(repo/'scripts/memory_restore_diagnostic.py')],
    'executed-pilot-driver.py':executed[str(repo/'scripts/memory_decision_pilot.py')],
    'wrapper.log':workspace/'wrapper.log',
    'decoder-red.log':workspace/'decoder-red.log',
    'decoder-green.log':workspace/'decoder-green.log',
    'delivery-full-suite.log':workspace/'delivery-full-suite.log',
}
published = []
for name, source in copies.items():
    target = dest/name
    assert not target.exists(), target
    assert source.stat().st_size <= 1024*1024, source
    shutil.copyfile(source, target)
    assert digest(source) == digest(target), target
    published.append({'path':name,'source':str(source),'bytes':target.stat().st_size,'sha256':digest(target)})

receipt = {'schema':'memory-restore-offline-publication-v1',
    'checked_utc':datetime.now(timezone.utc).isoformat(),
    'scope':'Post-close documentary hash/copy checks only; no new scientific readout or native decode',
    'registration_sha256':digest(reg_path),'preserved_sets':preserved,
    'executed_bound_files_verified':len(executed),
    'executed_helper_preserved_separately':True,
    'delivery_helper_changed_after_close':True,
    'offline_output_index_verified':True,'published':published,
    'new_native_owners':0,'physics_steps':0,'qualification_claims':[]}
target = dest/'publication-integrity.json'
assert not target.exists()
target.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'preserved_files':sum(row['files'] for row in preserved),
    'executed_bound_files_verified':len(executed),'exact_copies':len(copies),
    'offline_close':close['status'],'new_native_owners':0},indent=2))
