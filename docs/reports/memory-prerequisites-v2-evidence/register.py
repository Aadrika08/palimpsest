"""Freeze the approved fresh campaign using raw inventories, never snapshot decode."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from scripts import memory_prerequisites_v2 as m
from palimpsest import memory_decision_world as world


def main(version='v2', *, evidence=None, baseline_path=None, registration_preparer_path=None):
    started = time.monotonic(); deadline = started+180
    if version not in ('v2','v3'): raise ValueError('Unknown campaign version')
    evidence = Path(evidence).resolve() if evidence is not None else Path(__file__).resolve().parent
    repo = evidence.parents[2]
    path = evidence/'registration.json'
    control = repo/f'.superpowers/sdd/memory-prerequisites-{version}'
    if path.exists() or control.exists():
        raise FileExistsError('Fresh campaign registration or control already exists')
    if subprocess.check_output(['git','status','--porcelain'], cwd=repo):
        raise ValueError('Registration requires committed software and protocol')
    baseline = p.read_json(baseline_path if baseline_path is not None else
                           repo/'docs/reports/restore-qualification-v2-evidence/registration.json')
    preserved = baseline['preserved_sets']
    for name in ('output','control_root','publication_root'):
        root = p.checked_path(baseline[name])
        preserved.append({'root':str(root), 'files':p.hash_ledger(root, deadline)})
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    contract = repo/f'docs/plans/memory-prerequisites-{version}.md'
    specs = p.travel_specs('travel-feasibility', d.PROFILE)
    reg = {key:baseline[key] for key in ('assets','history_root','history_inputs',
                                        'prior_output','prior_inventory')}
    reg.update(schema=f'memory-prerequisites-registration-{version}', mode=f'prerequisites-{version}',
        repo=str(repo), python=sys.executable, state_contract=d.STATE_CONTRACT,
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
        contract=str(contract), contract_sha256=p.file_hash(contract),
        diagnostic_driver_sha256=p.file_hash(d.__file__), profile_sha256=d.PROFILE,
        protocol_sha256=p.TRAVEL_PROTOCOL_SHA256, expected_specs=specs,
        expected_cases=[world.make_case(spec['seed'],spec['regime'],spec['kind'],spec['mirrored'],
                        profile_sha256=d.PROFILE) for spec in specs],
        source_derivation=m.DERIVATION, seconds_caps=[4300,600],
        output=str(repo/'runs'/(f'memory-prerequisites-{version}-'+stamp)), control_root=str(control),
        publication_root=str(evidence), source_identity=p.source_identity(repo,reg['assets']),
        runtime=d.runtime_v2_identity(), preserved_sets=preserved,
        prepared_utc=datetime.now(timezone.utc).isoformat(), preparation_started_monotonic=started,
        preparation_deadline_monotonic=deadline, preparation_seconds_cap=180,
        source_invariant_rechecked=False, qualification_claims=[], corrective_studies=0,
        native_invocations=1, native_owners_max=8)
    if reg['source_identity'] != baseline['source_identity']:
        raise ValueError('Native source/assets differ from the preserved baseline')
    reg['protected_roots'] = sorted({reg['prior_output'], *(row['root'] for row in preserved)})
    paths = {'driver':repo/'scripts/memory_prerequisites_v2.py',
            'auditor':repo/'scripts/memory_prerequisites_v2.py',
            'comparator':repo/'scripts/memory_restore_offline_readout.py',
            'launcher':evidence/'execute-campaign.py', 'registration_preparer':Path(registration_preparer_path).resolve() if registration_preparer_path is not None else Path(__file__).resolve(),
            'shared_launcher':repo/'docs/reports/restore-qualification-v2-evidence/execute-restore-v2.py'}
    if version == 'v3':
        paths.update(campaign_launcher=repo/'docs/reports/memory-prerequisites-v2-evidence/execute-campaign.py',
                     shared_preparer=repo/'docs/reports/memory-prerequisites-v2-evidence/register.py')
    for name,target in paths.items():
        reg[name+'_path'] = str(target); reg[name+'_sha256'] = p.file_hash(target)
    m.validate_registration(reg)
    p.safe_output(reg['output'],reg['protected_roots'])
    m.recheck_inputs(reg,deadline)
    if shutil.disk_usage(repo).free < 10*p.GiB:
        raise ValueError('Fresh campaign requires 10 GiB free at admission')
    p.deadline_check(deadline)
    reg['preparation_seconds_before_write'] = time.monotonic()-started
    p.write_control(path,reg,m.budget(reg))
    p.deadline_check(deadline)
    # The committed registration must exist before native admission. Commit only
    # this file; a Git failure consumes preparation without authorizing a retry.
    subprocess.run(['git','add',str(path)],cwd=repo,check=True,
                   timeout=max(.01,deadline-time.monotonic()))
    subprocess.run(['git','commit','-m','docs(memory): freeze one eight-cell prerequisite allocation'],
                   cwd=repo,check=True,timeout=max(.01,deadline-time.monotonic()))
    p.deadline_check(deadline)
    print(json.dumps({'registration':str(path),'sha256':p.file_hash(path),
        'preserved_files':sum(len(row['files']) for row in preserved),
        'elapsed_seconds':time.monotonic()-started,'qualification_claims':[]}),flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
