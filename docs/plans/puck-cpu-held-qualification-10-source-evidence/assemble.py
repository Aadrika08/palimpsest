from pathlib import Path
import copy
import hashlib
import json

root = Path('/home/utkarsh/.codex/worktrees/0071/brain')
base = root / 'docs/plans/puck-cpu-held-qualification-10'
proof = Path(str(base) + '-source-evidence')
proof.mkdir(exist_ok=False)
before = Path('/tmp/palimpsest-actual10-before-source-rollout.json')
(proof / 'before-source-rollout.json').write_bytes(before.read_bytes())
old = json.loads((root / 'docs/plans/puck-cpu-held-qualification-09.json').read_text())
config = copy.deepcopy(old)
config.update(kind='puck-cpu-held-runtime-allocation-v10', version=10, allocation_id=10)
for row in config['sources']:
    raw = (root / row['path']).read_bytes()
    row.update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
assert [a['path'] for a,b in zip(old['sources'], config['sources']) if a != b] == [
    'scripts/puck_worker_bootstrap.py', 'scripts/qualify_puck_cpu_held_runtime.py',
    'src/palimpsest/puck_runtime_qualification.py']
config_raw = (json.dumps(config, indent=2, sort_keys=True) + '\n').encode()
with Path(str(base) + '.json').open('xb') as f:
    f.write(config_raw)
admission = (root / 'docs/plans/puck-cpu-held-qualification-09-admission.py').read_text()
admission = admission.replace('puck-cpu-held-qualification-09', 'puck-cpu-held-qualification-10').replace('held09', 'held10')
admission = admission.replace('pre09', 'pre10').replace('current09/D', 'current10/D').replace('check_id=9', 'check_id=10')
admission = admission.replace('2c441b2465c86baf2982a5c023ce5923c1c144bd5789576807ffee6f19beb6c0', hashlib.sha256(config_raw).hexdigest())
admission = admission.replace('dffcec25696948da18b18abda32dae764fa933a1175c622f45d33a3bca27d234', '7d87485b1bfcbeeb625a2fc71a59f697cdde5850dabec5a5d29bd7b7f7ac16fa')
admission = admission.replace('96ace37062fd14e20ae1ebd2371b90fa88f8d7ab', 'e723db037ed1f790c2618798d59f56913054754f')
with Path(str(base) + '-admission.py').open('x') as f:
    f.write(admission)
history = (root / 'docs/plans/puck-cpu-held-qualification-09-source-evidence/history-check.py').read_text()
history = history.replace('Prospective09', 'Prospective10').replace('qualification-09-admission', 'qualification-10-admission').replace('held09', 'held10')
history = history.replace('Nine unittest cases:', 'Thirteen unittest cases:').replace('Only existing small07/08', 'Only existing small07/08/09')
history = history.replace("('07','08')", "('07','08','09')")
history = history.replace('set(control.HISTORICAL08_JSON)', 'set(control.HISTORICAL08_JSON)|set(control.HISTORICAL09_JSON)')
history = history.replace('len(pins),19', 'len(pins),29').replace("['historical_missing_receipts'],14", "['historical_missing_receipts'],16")
history = history.replace("self.assertEqual(control.check_consumed08(held)['status'],'FAILED_CONSUMED')", "self.assertEqual(control.check_consumed08(held)['status'],'FAILED_CONSUMED')\n            self.assertEqual(control.check_consumed09(held)['status'],'FAILED_CONSUMED')")
extra = '''
    def test_genuine09_failure_has_no_success_or_closure_receipt(self):
        self.genuine('09')

    def test_changed09_transport_is_refused(self):self.changed_transport('09')
    def test_fabricated09_result_is_refused(self):self.check_missing('09','result.json')
    def test_fabricated09_baseline_after_is_refused(self):self.check_missing('09','baseline-after.json')

'''
history = history.replace("\n\nif __name__=='__main__':", '\n' + extra + "\nif __name__=='__main__':")
(proof / 'history-check.py').write_text(history)
review = '''# Qualification 10: exact CPU runtime import route

Goal: one separately admitted, observed and independently audited normal
four-import completion under the reviewed q4 contract. Then separately qualify
operator/renderer before the recorded/snapshotted/replayed/exported public episode.
All seven full simulation-release gates stay open.

Use source publication e723db0 (implementation cbe48b3), original preparation 01,
candidate D, nineteen missing names, unchanged environment and 180s/2GiB limits.
Retain consumed 01–09 and every genuine failure/absence. No silent retry.

Ruling: reuse the existing runtime worktree because original preparation and
custody paths bind it. Branch from published e723db0; its 24 qualification-source
bytes equal cbe48b3. Preserve old live bytes through the existing 09 source archive.

1. Prove small 09-history additions RED, then GREEN with existing stdlib checks.
   Pin current controls and full historical source/evidence metadata. No vendor
   imports, SITE/staged-payload reads, qualification or admission during assembly.
2. Freeze distinct10 metadata and fixed external admission/observer/audit commands;
   run metadata-only self-check, independent exact-controls/roster review, commit
   and push before any admission or actual invocation.
3. Run fresh full data-only admission once under the fixed envelope. Independently
   check bytes, resources, historical absences and normal closure. Only then use a
   fresh pre-observer guard and invoke actual10 once. Preserve the terminal result.
4. Bind the concrete audit command to the real transport digest and run the
   independent auditor once. Preserve its verdict, exact bytes, source/controls,
   logs, process/descriptor observations and any missing receipts. Publish the
   bounded outcome; do not convert failure into acceptance or retry implicitly.

Scope: import-route evidence only. No operator, renderer, physics, inference,
collection, protected inputs, scientific studies, CI, cloud or rover execution.
'''
with Path(str(base) + '-review.md').open('x') as f:
    f.write(review)
print(json.dumps(dict(configuration_sha256=hashlib.sha256(config_raw).hexdigest(),
    configuration_bytes=len(config_raw), baseline_control_created=True,
    actual10_invoked=False, admission_invoked=False)))
