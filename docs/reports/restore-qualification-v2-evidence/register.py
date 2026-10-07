"""Freeze one reviewed restore-v2 registration; metadata and raw hashes only."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d


def main():
    started = time.monotonic(); deadline = started+180
    evidence = Path(__file__).resolve().parent; repo = evidence.parents[2]
    path = evidence/'registration.json'
    control = repo/'.superpowers/sdd/restore-qualification-v2'
    if path.exists() or (control/'launched.json').exists():
        raise FileExistsError('Fresh registration/allocation already exists')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo):
        raise ValueError('Registration requires committed software and protocol')
    legacy = p.read_json(repo/'docs/reports/memory-restore-study-v2-evidence/registration.json')
    attribution = p.read_json(repo/'docs/reports/memory-native-byte-attribution-evidence/registration.json')
    source = attribution['source_snapshot']
    if (source['bytes'] != 1559915 or source['sha256'] !=
            'c839fae1fe3d981cf4b7073970f7eb06d5738f009d6cb23f249408fd227cf6bf' or
            source['invariant'] != '86fa2ebcee8305a1b39c779a9a52e7c844345142fdbc4fd19175584a695a8b78'):
        raise ValueError('Source differs from the approved single-source scope')
    preserved = attribution['preserved_sets']
    # Retain original consumed allocations as well as the published/raw history.
    marker_inputs = [row for row in attribution['bound_files'] if row['path'].endswith(
        ('/diagnostic-launched.json', '/diagnose/launched.json'))]
    if len(marker_inputs) != 2:
        raise ValueError('Exactly two historical consumed markers required')
    for row in marker_inputs:
        marker = p.checked_path(row['path'])
        if marker.stat().st_size != row['bytes'] or p.file_hash(marker) != row['sha256']:
            raise ValueError('Original consumed marker changed')
        preserved.append({'root': str(marker.parent), 'files': p.hash_ledger(marker.parent, deadline)})
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    contract = repo/'docs/plans/restore-qualification-v2.md'
    registration = {key: legacy[key] for key in ('assets', 'history_root', 'history_inputs',
        'prior_output', 'prior_inventory')}
    registration.update(schema='memory-restore-registration-v2', mode='restore-v2',
        repo=str(repo), python=sys.executable, state_contract=d.STATE_CONTRACT,
        implementation_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
        contract=str(contract), contract_sha256=p.file_hash(contract),
        diagnostic_driver_sha256=p.file_hash(d.__file__),
        profile_sha256=d.PROFILE, protocol_sha256=p.TRAVEL_PROTOCOL_SHA256,
        expected_specs=p.travel_specs('travel-feasibility', d.PROFILE)[-2:], seconds_caps=[600, 300],
        output=str(repo/'runs'/('restore-v2-pair-'+stamp)), control_root=str(control),
        publication_root=str(evidence), source_snapshot=source,
        source_identity=p.source_identity(repo, attribution['assets']),
        runtime=d.runtime_v2_identity(), preserved_sets=preserved,
        prepared_utc=datetime.now(timezone.utc).isoformat(), preparation_started_monotonic=started,
        preparation_deadline_monotonic=deadline, preparation_seconds_cap=180,
        source_invariant_rechecked=False, qualification_claims=[], corrective_studies=0,
        native_invocations=1, native_owners_max=2)
    if registration['source_identity'] != attribution['source_identity']:
        raise ValueError('Native source/assets differ from the preserved baseline')
    registration['protected_roots'] = sorted({source['path'], legacy['prior_output'],
        *(row['root'] for row in preserved)})
    for name, target in {'comparator': repo/'scripts/memory_restore_offline_readout.py',
            'auditor': repo/'scripts/memory_restore_v2_audit.py',
            'launcher': evidence/'execute-restore-v2.py'}.items():
        registration[name+'_path'] = str(target)
        registration[name+'_sha256'] = p.file_hash(target)
    d.validate_v2_registration(registration)
    p.safe_output(registration['output'], registration['protected_roots'])
    d.recheck_v2_inputs(registration, deadline)
    if shutil.disk_usage(repo).free < 10*p.GiB:
        raise ValueError('Fresh phase requires 10 GiB free at admission')
    p.deadline_check(deadline)
    registration['preparation_seconds_before_write'] = time.monotonic()-started
    p.write_control(path, registration, d.restore_v2_budget(registration))
    p.deadline_check(deadline)
    print(json.dumps({'registration': str(path), 'sha256': p.file_hash(path),
        'preserved_files': sum(len(row['files']) for row in preserved),
        'elapsed_seconds': time.monotonic()-started, 'qualification_claims': []}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
