"""One fresh eight-cell, one-profile campaign; pilot and held-out remain locked."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from scripts import memory_restore_offline_readout as o
from palimpsest import memory_decision_world as world

DERIVATION = {'job_id': 'south-prefix', 'operation': 'prefix',
              'repeat_job_ids': ['restore-1', 'restore-2']}


def validate_registration(reg):
    if (reg.get('schema') != 'memory-prerequisites-registration-v2' or
            reg.get('mode') != 'prerequisites-v2' or reg.get('seconds_caps') != [4300, 600] or
            reg.get('state_contract') != d.STATE_CONTRACT or reg.get('profile_sha256') != d.PROFILE or
            reg.get('protocol_sha256') != p.TRAVEL_PROTOCOL_SHA256 or
            reg.get('expected_specs') != p.travel_specs('travel-feasibility', d.PROFILE) or
            reg.get('source_derivation') != DERIVATION or not isinstance(reg.get('runtime'), dict) or
            not reg['runtime'] or any(type(reg.get(key)) is not int or reg[key] != value for key, value in
                {'native_invocations': 1, 'native_owners_max': 8, 'corrective_studies': 0,
                 'preparation_seconds_cap': 180}.items())):
        raise ValueError('Unknown or incomplete campaign registration')
    python_version = reg['runtime'].get('python_version')
    if (not isinstance(python_version, list) or python_version[:2] != [3,11] or
            reg['runtime'].get('versions') != {'numpy':'2.2.5','mujoco':'3.3.6','torch':'2.9.0'}):
        raise ValueError('Campaign runtime versions differ from approved Python/packages')
    repo = p.checked_path(reg['repo']); output = p.checked_path(reg['output'])
    control = p.checked_path(reg['control_root']); publication = p.checked_path(reg['publication_root'])
    if (control != repo/'.superpowers/sdd/memory-prerequisites-v2' or
            publication != repo/'docs/reports/memory-prerequisites-v2-evidence' or
            output.parent != repo/'runs' or not output.name.startswith('memory-prerequisites-v2-')):
        raise ValueError('Campaign output/control/publication path differs')
    paths = {'driver': repo/'scripts/memory_prerequisites_v2.py',
        'auditor': repo/'scripts/memory_prerequisites_v2.py',
        'comparator': repo/'scripts/memory_restore_offline_readout.py',
        'launcher': publication/'execute-campaign.py', 'registration_preparer': publication/'register.py',
        'shared_launcher': repo/'docs/reports/restore-qualification-v2-evidence/execute-restore-v2.py'}
    for name, path in paths.items():
        digest = reg.get(name+'_sha256')
        if (reg.get(name+'_path') != str(path) or type(digest) is not str or len(digest) != 64 or
                any(char not in '0123456789abcdef' for char in digest)):
            raise ValueError('Missing or invalid campaign '+name+' pin')
    expected_cases = [world.make_case(spec['seed'], spec['regime'], spec['kind'], spec['mirrored'],
        profile_sha256=d.PROFILE) for spec in reg['expected_specs']]
    if reg.get('expected_cases') != expected_cases:
        raise ValueError('Registered campaign cases differ')
    preserved = reg.get('preserved_sets'); protected = [p.checked_path(x) for x in reg.get('protected_roots', [])]
    if not isinstance(preserved, list) or not preserved:
        raise ValueError('Missing campaign preserved inventories')
    if any(path not in protected for path in [p.checked_path(reg['prior_output']),
            *(p.checked_path(row['root']) for row in preserved)]):
        raise ValueError('Campaign preserved source protection is incomplete')
    roots = (output, control, publication)
    sources = p.source_paths(repo, reg['assets'], reg['history_root'])+protected
    if (any(p.overlaps(root, source) for root in roots for source in sources) or
            any(p.overlaps(a, b) for i, a in enumerate(roots) for b in roots[i+1:])):
        raise ValueError('Campaign counted roots overlap inputs or each other')


def budget(reg):
    return d.restore_v2_budget(reg)  # Same measured bounds, new exact three-root set.


def recheck_inputs(reg, deadline=None):
    validate_registration(reg)
    if d.runtime_v2_identity() != reg['runtime'] or reg.get('python') != reg['runtime'].get('python_path'):
        raise ValueError('Registered campaign runtime differs')
    required_environment = {key:'1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                              'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}
    required_environment.update(MUJOCO_GL='egl', CUDA_VISIBLE_DEVICES='')
    if reg['runtime'].get('environment') != required_environment:
        raise ValueError('Campaign requires one CPU thread, EGL and disabled CUDA')
    for name in ('driver', 'auditor', 'comparator', 'launcher', 'shared_launcher', 'registration_preparer'):
        if p.file_hash(reg[name+'_path']) != reg[name+'_sha256']:
            raise ValueError('Registered campaign '+name+' changed')
        p.deadline_check(deadline)
    d.recheck_inputs(reg, deadline)
    for reference in reg['preserved_sets']:
        o.verify_inventory(reference, deadline)
    p.deadline_check(deadline)


def cell_pass(spec, result):
    return (result.get('status') == 'recorded' and result.get('raw_audit_pass') is True and
        p.prerequisite_pass(spec['mandatory'], result) and
        (spec['mandatory'] != 'retreat' or
            (result.get('first_commitment_blocked') is True and result.get('replans', 0) >= 1)))


def fresh_source(reg, result, deadline):
    p.deadline_check(deadline)
    path = p.checked_path(result['snapshot_path'])
    expected = Path(reg['output'])/'stage/runs'/result['run_id']/'snapshots/initial.snp'
    if (result['job_id'] != 'south-prefix' or path != expected or
            path.stat().st_size > 16*p.MiB or p.file_hash(path) != result['snapshot_sha256']):
        raise ValueError('Fresh south-prefix source path/checksum differs')
    state = d.read_snapshot(path)
    if (p.condition_digest(state) != result['invariant'] or
            state['application']['memory']['supervisor']['phase'] != 'await_decision'):
        raise ValueError('Fresh south-prefix source invariant or boundary differs')
    return {'snapshot_path': str(path), 'snapshot_sha256': result['snapshot_sha256'],
        'invariant': result['invariant'], 'bytes': path.stat().st_size, 'source_job_id': 'south-prefix',
        'run_id': result['run_id'], 'source_receipt_ids': sorted(state['application']['receipts'])}


def read_evidence(reg, receipt, deadline, evidence):
    """Re-read allocated jobs and raw evidence; never trust a provisional pass."""
    root = p.checked_path(reg['output']); stage = root/'stage'
    attempts = receipt['attempted']; specs = reg['expected_specs']
    rows = d.audit_owners(stage, {row['run_id']: row for row in attempts}, deadline)
    evidence['owners'] = rows
    jobs = p.hash_ledger(stage/'jobs', deadline)
    started = [row for row in p.hash_ledger(stage/'runs', deadline) if Path(row['path']).name == 'owner.json']
    evidence.update(allocated_jobs=jobs, started_owners=started,
        allocated_jobs_sha256=p.sha(jobs), started_owners_sha256=p.sha(started))
    if (len(attempts) != 8 or [row['job_id'] for row in attempts] != [spec['id'] for spec in specs] or
            len({row['run_id'] for row in attempts}) != 8 or len(rows) != 8 or
            {row['job_id'] for row in rows} != {spec['id'] for spec in specs} or
            {row['path'] for row in jobs} != {row['run_id']+'.json' for row in attempts} or
            {row['path'] for row in started} != {row['run_id']+'/owner.json' for row in attempts}):
        raise ValueError('Exactly eight ordered attempts, allocated jobs and started owners required')
    cleanup = receipt['cleanup']
    if len(cleanup) != 8 or len({row['owner']['run_id'] for row in cleanup}) != 8:
        raise ValueError('Exactly eight clean owner observations required')
    cleanup_by_run = {row['owner']['run_id']:row for row in cleanup}
    by_run = {row['run_id']: row for row in rows}; posts = []; ids = []; traces = []
    source = None
    for index, (spec, attempt) in enumerate(zip(specs, attempts)):
        p.deadline_check(deadline)
        row = by_run[attempt['run_id']]
        job = p.validate_job(p.read_json(stage/'jobs'/(attempt['run_id']+'.json')), read_only=True)
        run = p.checked_path(job['output'])
        if (job['spec'] != spec or job['case'] != reg['expected_cases'][index] or
                job['stage'] != 'travel-feasibility' or job['operation'] != spec['operation'] or
                job['condition'] is not None or job['stage_output'] != str(stage) or
                job['phase_root'] != str(root) or job['protocol_sha256'] != p.TRAVEL_PROTOCOL_SHA256 or
                any(job[key] != reg[key] for key in ('repo', 'assets', 'history_root', 'source_identity')) or
                run != stage/'runs'/job['run_id'] or job['run_id'] != attempt['run_id']):
            raise ValueError('Fresh campaign job binding differs')
        expected_source = (None, None, None) if spec['operation'] != 'repeat' else (
            source['snapshot_path'], source['snapshot_sha256'], source['invariant'])
        if tuple(job[key] for key in ('snapshot_path', 'snapshot_sha256', 'expected_invariant')) != expected_source:
            raise ValueError('Campaign owner does not use its prescribed fresh source')
        owner = p.read_json(run/'owner.json'); observed = cleanup_by_run.get(job['run_id'])
        if (owner.get('run_id') != job['run_id'] or observed is None or observed['owner'] != owner or
                observed['path'] != str(run/'owner.json') or observed['status'] not in
                    ('already-exited', 'pid-reused-do-not-touch') or not d.owner_exited(owner)):
            raise ValueError('Fresh owner was not cleanly terminated in its original namespace')
        supervised_path = stage/'supervision'/job['run_id']
        supervised = p.read_json(supervised_path/'supervisor.json')
        internal, outer = p.owner_allocation('travel-feasibility', spec['operation'], p.TRAVEL_PROTOCOL_SHA256)
        elapsed = supervised.get('elapsed_seconds')
        if (supervised != attempt['supervision'] or supervised.get('status') != 'completed' or
                supervised.get('returncode') != 0 or supervised.get('timeout_seconds') != outer or
                supervised.get('output') != str(supervised_path) or type(elapsed) not in (int,float) or
                not math.isfinite(elapsed) or not 0 <= elapsed <= outer or
                any(path.stat().st_size > p.MiB for path in supervised_path.glob('*.log'))):
            raise ValueError('Campaign owner supervision differs or failed')
        if row.get('raw_audit_pass') is not True or row.get('matching_owner_exited') is not True:
            raise ValueError('Campaign raw audit or owner absence failed')
        audited = row['audit']; raw = p.read_raw(run, deadline)
        wall = audited.get('wall_seconds'); initial_path = run/'snapshots/initial.snp'
        initial = d.read_snapshot(initial_path)
        if (type(wall) not in (int,float) or not math.isfinite(wall) or not 0 <= wall <= internal or
                audited.get('snapshot_path') != str(initial_path) or
                p.file_hash(initial_path) != audited.get('snapshot_sha256') or
                p.condition_digest(initial) != audited.get('invariant')):
            raise ValueError('Fresh initial snapshot integrity/invariant or internal owner cap differs')
        if any(audited.get(key) != attempt.get(key) for key in ('snapshot_sha256', 'invariant',
                'trace_digest', 'goal', 'acquired', 'continuation_ticks', 'retreat_completed',
                'first_commitment_blocked', 'replans')):
            raise ValueError('Fresh raw audit differs from recorded attempt')
        if spec['operation'] != 'repeat':
            if not cell_pass(spec, audited):
                raise ValueError('Mandatory fresh prerequisite failed: '+spec['id'])
            if spec['id'] == 'south-prefix':
                source = fresh_source(reg, audited, deadline)
                if p.read_json(root/'fresh-source.json') != source:
                    raise ValueError('Fresh source receipt differs from producing prefix')
        else:
            trace = p.trace_digest(raw['rows'])
            if (len(raw['rows']) != 5 or audited.get('continuation_ticks') != 5 or
                    audited.get('invariants_preserved') is not True or audited.get('trace_digest') != trace or
                    p.condition_digest(initial) != source['invariant'] or
                    sorted(initial['application']['receipts']) != source['source_receipt_ids']):
                raise ValueError('Restore must have five invariant-preserving fresh-source controls')
            post, initial_ids = d.audit_post_state(run, audited)
            if any(audited.get(key) != attempt.get(key) for key in
                    ('post_snapshot_sha256', 'post_state_digest', 'post_state_components')):
                raise ValueError('Retained repeat capture differs from original attempt')
            posts.append(post); ids.append(initial_ids); traces.append(trace)
    comparison = d.compare_states(*posts, *ids)
    candidate = o.compare_reproducibility_states(*posts, *ids, deadline)
    trace_equal = traces[0] == traces[1]
    evidence.update(comparison=comparison, candidate_comparison=candidate, trace_equal=trace_equal,
        restore_pair_matches=bool(comparison['equal'] and trace_equal),
        candidate_restore_pair_matches=bool(candidate['equal'] and trace_equal),
        total_new_controls=sum(row['raw_rows'] for row in rows), fresh_source=source)
    if not evidence['candidate_restore_pair_matches']:
        raise ValueError('Fresh candidate restore state or non-timing trace differs')
    p.deadline_check(deadline)


def invalidate(root, storage, error):
    path = root/'scientific-close.json'
    if path.exists():
        close = p.read_json(path)
        close.update(status='scientific-close-stop', native_prerequisites_passed=False,
                     qualification_claims=[], invalidation_error=str(error))
        try:
            d.replace_control(path, close, storage)
        except BaseException:
            if path.exists() and p.read_json(path).get('native_prerequisites_passed') is True:
                path.rename(root/'scientific-close.invalidated.json')


def launcher_origin(reg, path):
    marker = Path(reg['control_root'])/'launched.json'
    value = p.read_json(marker); started = value.get('started_monotonic')
    if (value.get('registration_sha256') != p.file_hash(path) or
            type(started) not in (int,float) or not math.isfinite(started) or
            not 0 < started <= time.monotonic()):
        raise ValueError('Original launcher clock or registration binding differs')
    return started


def run(path):
    path = p.checked_path(path); reg = p.read_json(path); validate_registration(reg)
    started = launcher_origin(reg,path); owner_deadline = started+4300; global_deadline = started+4900
    repo = p.checked_path(reg['repo'])
    if repo != Path(__file__).resolve().parents[1] or path != Path(reg['publication_root'])/'registration.json':
        raise ValueError('Campaign checkout or registration path differs')
    if subprocess.check_output(['git','status','--porcelain'], cwd=repo):
        raise ValueError('Native admission requires a clean committed checkout')
    head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=repo, text=True).strip()
    if subprocess.check_output(['git','diff',reg['implementation_commit'],head,'--name-only','--',
            'src','scripts','tests','model_manifests','uv.lock','upstream'], cwd=repo):
        raise ValueError('Registered campaign implementation differs')
    root = p.safe_output(reg['output'], p.source_paths(repo,reg['assets'],reg['history_root'])+
        reg['protected_roots']+[reg['control_root'],reg['publication_root']])
    recheck_inputs(reg, owner_deadline)
    plan = p.preflight(repo, Path(reg['assets']), Path(reg['history_root']), root/'stage', root,
                       owner_deadline, profile_sha256=d.PROFILE)
    plan.update(protocol=p.TRAVEL_PROTOCOL, protocol_sha256=p.TRAVEL_PROTOCOL_SHA256,
                selected_profile_sha256=d.PROFILE)
    storage = budget(reg)
    receipt = {'schema':'memory-prerequisites-execution-v2', 'mode':'prerequisites-v2',
        'implementation_head':head, 'registration_sha256':p.file_hash(path),
        'launcher_marker_sha256':p.file_hash(Path(reg['control_root'])/'launched.json'),
        'source_identity':reg['source_identity'], 'state_contract':reg['state_contract'],
        'process_namespace':os.readlink('/proc/self/ns/pid'), 'output':str(root),
        'started_utc':datetime.now(timezone.utc).isoformat(), 'started_monotonic':started,
        'owner_deadline_monotonic':owner_deadline, 'global_deadline_monotonic':global_deadline,
        'seconds_caps':[4300,600], 'status':'running', 'attempted':[], 'unattempted':[],
        'native_prerequisites_passed':False, 'qualification_claims':[], 'r2_complete':False,
        'paired_pilot':'unattempted-by-scope', 'held_out_used':False, 'retries':0}
    def interrupted(signum, frame):
        raise RuntimeError('Campaign interrupted: '+str(signum))
    previous = signal.signal(signal.SIGTERM, interrupted)
    root.mkdir(parents=True, exist_ok=False)
    try:
        with storage.lock():
            (root/'stage').mkdir()
            p.write_control(root/'registration.json', reg, storage)
            p.write_control(root/'stage/preflight.json', plan, storage)
            d.replace_control(root/'execution.json', receipt, storage)
            source = None
            try:
                if not plan.get('geometry_valid'):
                    raise ValueError('Frozen profile geometry invalid')
                for spec in reg['expected_specs']:
                    recheck_inputs(reg, owner_deadline)
                    if spec['operation'] == 'repeat':
                        if source is None or fresh_source(reg, receipt['attempted'][4], owner_deadline) != source:
                            raise ValueError('Fresh source changed before repeat admission')
                    storage.check(512*p.MiB+2*16*p.MiB+4*p.MiB, path=root/'stage/runs')
                    result = p.launch_owner('travel-feasibility', spec, plan, storage, owner_deadline,
                        source=source if spec['operation']=='repeat' else None,
                        retain_repeat_state=spec['operation']=='repeat')
                    receipt['attempted'].append(result)
                    d.replace_control(root/'execution.json', receipt, storage)
                    if spec['operation'] == 'repeat':
                        if (result.get('status') != 'recorded' or result.get('raw_audit_pass') is not True or
                                result.get('invariants_preserved') is not True or result.get('continuation_ticks') != 5):
                            raise ValueError('Restore owner failed; later launch prohibited')
                        d.audit_post_state(Path(result['run']), result)
                    elif not cell_pass(spec, result):
                        raise ValueError('Mandatory fresh prerequisite failed: '+spec['id'])
                    if spec['id'] == 'south-prefix':
                        source = fresh_source(reg, result, owner_deadline)
                        p.write_control(root/'fresh-source.json', source, storage)
                p.deadline_check(owner_deadline)
                receipt['status'] = 'recorded-bounded-attempt'
            except BaseException as error:
                receipt.update(status='owner-or-admission-stop', error={'type':type(error).__name__,'message':str(error)})
            finally:
                readout_started = time.monotonic(); deadline = min(global_deadline, readout_started+600)
                receipt.update(readout_started_monotonic=readout_started, readout_deadline_monotonic=deadline)
                analysis = {}
                try:
                    receipt['cleanup'] = d.cleanup_owners(root)
                    read_evidence(reg, receipt, deadline, analysis)
                    if receipt['status'] != 'recorded-bounded-attempt':
                        raise ValueError('Owner phase did not complete')
                    recheck_inputs(reg, deadline)
                    receipt['source_and_prior_evidence_unchanged'] = True
                    receipt['status'] = 'prerequisites-provisional-pass'
                except BaseException as error:
                    receipt.update(status='prerequisites-failure', readout_error={'type':type(error).__name__,'message':str(error)})
                # Attempts retain full reports; independent close keeps its own audits.
                for owner in analysis.get('owners', []):
                    owner.pop('audit', None)
                receipt.update(analysis)
                attempted_ids = {row['job_id'] for row in receipt['attempted']}
                receipt['unattempted'] = [spec['id'] for spec in reg['expected_specs'] if spec['id'] not in attempted_ids]
                receipt.update(total_seconds=time.monotonic()-started, readout_seconds=time.monotonic()-readout_started)
                try:
                    receipt['artifact_index'] = [row for row in p.hash_ledger(root, deadline) if row['path'] != 'execution.json']
                    p.deadline_check(deadline); d.replace_control(root/'execution.json', receipt, storage)
                    storage.check(0, path=root/'execution.json'); p.deadline_check(deadline)
                except BaseException as error:
                    receipt.update(status='prerequisites-failure', close_error={'type':type(error).__name__,'message':str(error)})
                    d.replace_control(root/'execution.json', receipt, storage)
    finally:
        signal.signal(signal.SIGTERM, previous)
    print(json.dumps({key:receipt.get(key) for key in ('status','native_prerequisites_passed',
        'restore_pair_matches','candidate_restore_pair_matches','total_new_controls','unattempted')}), flush=True)
    return 0 if receipt['status'] == 'prerequisites-provisional-pass' else 1


def audit(path):
    path = p.checked_path(path); reg = p.read_json(path); validate_registration(reg)
    root = p.checked_path(reg['output']); target = root/'scientific-close.json'; storage = budget(reg)
    if target.exists():
        raise FileExistsError('Scientific close exists; no repeated readout')
    close = {'schema':'memory-prerequisites-scientific-close-v2', 'status':'scientific-close-stop',
        'output':str(root), 'state_contract':reg['state_contract'], 'native_prerequisites_passed':False,
        'qualification_claims':[], 'r2_complete':False, 'paired_pilot':'unattempted-by-scope',
        'held_out_used':False, 'physics_steps':0, 'new_native_owners':0, 'owners':[]}
    try:
        receipt = p.read_json(root/'execution.json')
        digest = p.file_hash(path); execution_digest = p.file_hash(root/'execution.json')
        keys = ('started_monotonic','owner_deadline_monotonic','global_deadline_monotonic',
                'readout_started_monotonic','readout_deadline_monotonic')
        times = [receipt[key] for key in keys]
        if any(type(value) not in (int,float) or not math.isfinite(value) for value in times):
            raise ValueError('Finite original campaign deadlines required')
        start, owner_end, global_end, readout_start, deadline = times
        if (start != launcher_origin(reg,path) or owner_end != start+4300 or global_end != start+4900 or
                not start <= readout_start <= global_end or deadline != min(global_end,readout_start+600) or
                readout_start > time.monotonic()):
            raise ValueError('Original campaign readout allocation differs')
        original = p.hash_ledger(root, deadline)
        close.update(registration_sha256=digest, driver_execution_sha256=execution_digest,
            readout_deadline_monotonic=deadline, process_namespace=receipt['process_namespace'])
        close['allocated_jobs'] = p.hash_ledger(root/'stage/jobs', deadline)
        close['started_owners'] = [row for row in p.hash_ledger(root/'stage/runs', deadline)
                                  if Path(row['path']).name == 'owner.json']
        close['owners'] = [{'owner':p.read_json(root/'stage/runs'/row['path']),
            'path':str(root/'stage/runs'/row['path']), 'disposition':'started-incomplete',
            'raw_audit_pass':False} for row in close['started_owners']]
        def recheck():
            p.deadline_check(deadline)
            if (p.file_hash(path) != digest or p.file_hash(root/'execution.json') != execution_digest or
                    p.file_hash(Path(reg['control_root'])/'launched.json') != receipt['launcher_marker_sha256'] or
                    Path(reg['auditor_path']) != Path(__file__).resolve() or
                    os.readlink('/proc/self/ns/pid') != receipt['process_namespace']):
                raise ValueError('Fresh auditor, registration, driver receipt or namespace differs')
            recheck_inputs(reg, deadline)
        recheck()
        if (receipt.get('schema') != 'memory-prerequisites-execution-v2' or receipt.get('mode') != 'prerequisites-v2' or
                receipt.get('status') != 'prerequisites-provisional-pass' or receipt.get('registration_sha256') != digest or
                receipt.get('source_identity') != reg['source_identity'] or receipt.get('output') != str(root) or
                receipt.get('state_contract') != reg['state_contract'] or receipt.get('seconds_caps') != [4300,600] or
                receipt.get('native_prerequisites_passed') is not False or receipt.get('qualification_claims') != [] or
                receipt.get('r2_complete') is not False or receipt.get('paired_pilot') != 'unattempted-by-scope' or
                receipt.get('held_out_used') is not False or receipt.get('unattempted') or
                receipt.get('source_and_prior_evidence_unchanged') is not True or
                any(key in receipt for key in ('error','readout_error','close_error')) or
                p.read_json(root/'registration.json') != reg):
            raise ValueError('Driver did not provisionally close all eight cells')
        expected_ledger = [row for row in original if row['path'] != 'execution.json']
        if receipt['artifact_index'] != expected_ledger:
            raise ValueError('Driver retained artifact inventory changed')
        read_evidence(reg, receipt, deadline, close)
        for key in ('comparison','candidate_comparison','trace_equal','restore_pair_matches',
                    'candidate_restore_pair_matches','total_new_controls','fresh_source'):
            if p.canonical(close[key]) != p.canonical(receipt[key]):
                raise ValueError('Independent campaign comparison differs from driver')
        recheck()
        if p.hash_ledger(root, deadline) != original:
            raise ValueError('Fresh campaign evidence changed during independent audit')
        close.update(immutable_inputs_and_raw_evidence_unchanged=True,
            storage_before_close=storage.check(0, path=target))
        p.deadline_check(deadline)
        close.update(status='native-prerequisites-passed', native_prerequisites_passed=True,
                     closed_monotonic=time.monotonic())
        d.replace_control(target, close, storage)
        p.deadline_check(deadline); storage.check(0, path=target); p.deadline_check(deadline)
    except BaseException as error:
        close.update(status='scientific-close-stop', native_prerequisites_passed=False,
                     error={'type':type(error).__name__,'message':str(error)})
        try:
            d.replace_control(target, close, storage)
        except BaseException as publication_error:
            close['failure_publication_error'] = str(publication_error)
            invalidate(root, storage, error)
    print(json.dumps({key:close.get(key) for key in ('status','native_prerequisites_passed',
        'restore_pair_matches','candidate_restore_pair_matches','error','failure_publication_error')}), flush=True)
    return 0 if close['native_prerequisites_passed'] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args(argv)
    return audit(args.registration) if args.audit else run(args.registration)


if __name__ == '__main__':
    raise SystemExit(main())
