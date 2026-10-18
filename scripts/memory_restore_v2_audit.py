"""Fresh registered restore readback and terminal close; no physics or new owners."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from scripts import memory_restore_offline_readout as o
from scripts.memory_waypoint_study import replace_control


def _keyed(rows):
    values = {row['path']: (row['bytes'], row['sha256']) for row in rows}
    if len(values) != len(rows):
        raise ValueError('Duplicate artifact inventory path')
    return values


def audit(registration_path: Path) -> int:
    """Consume the driver's original readout deadline and leave its receipt unchanged."""
    registration_path = p.checked_path(registration_path)
    registration = p.read_json(registration_path)
    d.validate_v2_registration(registration)
    root = p.checked_path(registration['output']); stage = root/'stage'
    target = root/'scientific-close.json'
    if target.exists():
        raise FileExistsError('Fresh scientific close already exists; no repeated readback')
    storage = d.restore_v2_budget(registration)
    close = {'schema': 'memory-restore-scientific-close-v2', 'status': 'scientific-close-stop',
        'started_utc': datetime.now(timezone.utc).isoformat(), 'output': str(root),
        'state_contract': registration['state_contract'], 'narrow_restore_passed': False,
        'native_prerequisites_passed': False, 'qualification_claims': [],
        'paired_pilot': 'unattempted-by-scope', 'held_out_used': False,
        'physics_steps': 0, 'new_native_owners': 0, 'owners': []}
    deadline = None
    try:
        registration_sha = p.file_hash(registration_path)
        execution_path = root/'execution.json'; receipt = p.read_json(execution_path)
        deadline = receipt['readout_deadline_monotonic']
        times = [receipt[key] for key in ('started_monotonic', 'owner_deadline_monotonic',
            'global_deadline_monotonic', 'readout_started_monotonic', 'readout_deadline_monotonic')]
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in times):
            raise ValueError('Finite original invocation deadlines required')
        start, owner_end, global_end, readout_start, readout_end = times
        if (owner_end != start+600 or global_end != start+900 or
                not start <= readout_start <= global_end or
                readout_end != min(global_end, readout_start+300) or readout_start > time.monotonic()):
            raise ValueError('Original readout allocation differs; no restarted window')
        close.update(registration_sha256=registration_sha, readout_deadline_monotonic=deadline,
            driver_execution_sha256=p.file_hash(execution_path), process_namespace=receipt['process_namespace'])

        def recheck():
            p.deadline_check(deadline)
            if (p.file_hash(registration_path) != registration_sha or
                    p.checked_path(registration['auditor_path']) != Path(__file__).resolve() or
                    p.file_hash(__file__) != registration['auditor_sha256']):
                raise ValueError('Fresh registration or auditor source changed')
            if os.readlink('/proc/self/ns/pid') != receipt['process_namespace']:
                raise ValueError('Fresh invocation process namespace differs')
            d.recheck_v2_inputs(registration, deadline)
            p.deadline_check(deadline)

        recheck()
        original_ledger = p.hash_ledger(root, deadline)
        jobs = p.hash_ledger(stage/'jobs', deadline) if (stage/'jobs').exists() else []
        started = [row for row in original_ledger if Path(row['path']).name == 'owner.json']
        close.update(allocated_jobs=jobs, started_owners=started,
            allocated_jobs_sha256=p.sha(jobs), started_owners_sha256=p.sha(started))
        for entry in started:
            p.deadline_check(deadline)
            owner = p.read_json(root/entry['path'])
            close['owners'].append({'run_id': owner.get('run_id'), 'owner': owner,
                'disposition': 'started-incomplete', 'raw_audit_pass': False})
        if (receipt.get('schema') != 'memory-restore-execution-v2' or receipt.get('mode') != 'restore-v2' or
                receipt.get('status') != 'narrow-restore-provisional-pass' or
                receipt.get('registration_sha256') != registration_sha or receipt.get('output') != str(root) or
                receipt.get('state_contract') != registration['state_contract'] or
                receipt.get('source_identity') != registration['source_identity'] or
                receipt.get('seconds_caps') != [600, 300] or receipt.get('narrow_restore_passed') is not False or
                receipt.get('native_prerequisites_passed') is not False or receipt.get('qualification_claims') != [] or
                receipt.get('paired_pilot') != 'unattempted-by-scope' or receipt.get('held_out_used') is not False or
                receipt.get('source_and_prior_evidence_unchanged') is not True or
                any(key in receipt for key in ('error', 'readout_error', 'close_error'))):
            raise ValueError('Driver did not provisionally close the fresh narrow pair')
        if p.read_json(root/'registration.json') != registration:
            raise ValueError('Invocation registration copy differs')
        if _keyed(receipt['artifact_index']) != _keyed([row for row in original_ledger if row['path'] != 'execution.json']):
            raise ValueError('Driver retained artifact inventory changed')
        attempts = receipt['attempted']; specs = registration['expected_specs']
        if (specs != p.travel_specs('travel-feasibility', d.PROFILE)[-2:] or len(attempts) != 2 or
                [row['job_id'] for row in attempts] != [spec['id'] for spec in specs] or
                len({row['run_id'] for row in attempts}) != 2):
            raise ValueError('Exactly the two ordered registered restore attempts required')
        if ({row['path'] for row in jobs} != {row['run_id']+'.json' for row in attempts} or
                {row['path'] for row in started} != {'stage/runs/'+row['run_id']+'/owner.json' for row in attempts}):
            raise ValueError('Extra or missing allocated job or started owner')
        cleanup = receipt['cleanup']
        if len(cleanup) != 2 or len({row['owner']['run_id'] for row in cleanup}) != 2:
            raise ValueError('Exactly two bound cleanup observations required')
        cleanup_by_run = {row['owner']['run_id']: row for row in cleanup}
        source = registration['source_snapshot']; copied_path = stage/'source/snapshots/initial.snp'
        copied = {'snapshot_path': str(copied_path), 'snapshot_sha256': source['sha256'],
            'invariant': source['invariant'], 'original_source': source}
        if (p.read_json(root/'source-copy.json') != copied or copied_path.stat().st_size != source['bytes'] or
                source['bytes'] > 16*p.MiB or p.file_hash(copied_path) != source['sha256'] or
                p.checked_path(source['path']).stat().st_size != source['bytes'] or
                p.file_hash(source['path']) != source['sha256']):
            raise ValueError('Fresh stage source copy differs')
        source_state = d.read_snapshot(copied_path)
        if p.condition_digest(source_state) != source['invariant']:
            raise ValueError('Fresh source invariant differs')
        source_ids = set(source_state['application']['receipts'])
        posts, ids, traces = [], [], []
        for attempt, spec in zip(attempts, specs):
            p.deadline_check(deadline)
            job = p.validate_job(p.read_json(stage/'jobs'/(attempt['run_id']+'.json')), read_only=True)
            run = p.checked_path(job['output'])
            row = next(row for row in close['owners'] if row['run_id'] == attempt['run_id'])
            row['job_id'] = spec['id']
            if (job['run_id'] != attempt['run_id'] or run != stage/'runs'/job['run_id'] or
                    job['spec'] != spec or job['operation'] != 'repeat' or job['condition'] is not None or
                    job['stage'] != 'travel-feasibility' or job['stage_output'] != str(stage) or
                    job['phase_root'] != str(root) or job['protocol_sha256'] != p.TRAVEL_PROTOCOL_SHA256 or
                    any(job[key] != registration[key] for key in ('repo', 'assets', 'history_root', 'source_identity')) or
                    (job['snapshot_path'], job['snapshot_sha256'], job['expected_invariant']) !=
                        (str(copied_path), source['sha256'], source['invariant'])):
                raise ValueError('Fresh restore job binding differs')
            owner = p.read_json(run/'owner.json'); row['owner'] = owner
            observed = cleanup_by_run.get(job['run_id'])
            if (owner.get('run_id') != job['run_id'] or observed is None or observed['owner'] != owner or
                    observed['path'] != str(run/'owner.json') or
                    observed['status'] not in ('already-exited', 'pid-reused-do-not-touch')):
                raise ValueError('Fresh cleanup identity or clean termination differs')
            row['matching_owner_exited'] = d.owner_exited(owner)
            if not row['matching_owner_exited']:
                raise ValueError('Matching fresh native owner remains active')
            supervised_path = stage/'supervision'/job['run_id']; supervised = p.read_json(supervised_path/'supervisor.json')
            elapsed = supervised.get('elapsed_seconds')
            if (supervised != attempt['supervision'] or supervised.get('status') != 'completed' or
                    supervised.get('returncode') != 0 or supervised.get('timeout_seconds') != 160 or
                    supervised.get('output') != str(supervised_path) or
                    type(elapsed) not in (int, float) or not math.isfinite(elapsed) or not 0 <= elapsed <= 160):
                raise ValueError('Fresh owner supervision differs or failed')
            if any(path.stat().st_size > p.MiB for path in supervised_path.glob('*.log')):
                raise ValueError('Fresh owner log exceeds registered stream cap')
            audited = p.audit_run(job, supervised, deadline); raw = p.read_raw(run, deadline)
            wall = audited.get('wall_seconds'); trace = p.trace_digest(raw['rows'])
            if (len(raw['rows']) != 5 or audited.get('continuation_ticks') != 5 or
                    audited.get('invariants_preserved') is not True or
                    type(wall) not in (int, float) or not math.isfinite(wall) or not 0 <= wall <= 150 or
                    audited.get('trace_digest') != trace or any(audited.get(key) != attempt.get(key) for key in
                        ('trace_digest', 'post_state_digest', 'post_snapshot_sha256', 'post_state_components'))):
                raise ValueError('Fresh restore must have five invariant-preserving audited controls')
            initial = d.read_snapshot(run/'snapshots/initial.snp')
            if (p.file_hash(run/'snapshots/initial.snp') != audited.get('snapshot_sha256') or
                    p.condition_digest(initial) != source['invariant'] or
                    set(initial['application']['receipts']) != source_ids):
                raise ValueError('Fresh initial snapshot integrity, invariant or receipt IDs differ')
            post, initial_ids = d.audit_post_state(run, audited)
            posts.append(post); ids.append(initial_ids); traces.append(trace)
            row.update(disposition='audited-recording', raw_audit_pass=True, raw_rows=5,
                retained_post_state_audited=True, trace_digest=trace,
                post_snapshot_sha256=audited['post_snapshot_sha256'], post_state_digest=audited['post_state_digest'])
        p.deadline_check(deadline)
        comparison = d.compare_states(*posts, *ids)
        candidate = o.compare_reproducibility_states(*posts, *ids, deadline)
        trace_equal = traces[0] == traces[1]
        raw_equal = comparison['equal'] and trace_equal
        candidate_equal = candidate['equal'] and trace_equal
        close.update(comparison=comparison, candidate_comparison=candidate, trace_equal=trace_equal,
            restore_pair_matches=raw_equal, candidate_restore_pair_matches=candidate_equal,
            independent_restore_attempts=2, controls_per_restore=5, total_new_controls=10)
        if (any(receipt['comparison'].get(key) != comparison[key] for key in
                ('equal', 'left_digest', 'right_digest', 'differing_components')) or
                any(receipt['candidate_comparison'].get(key) != candidate[key] for key in
                    ('equal', 'contract_id', 'left_digest', 'right_digest')) or
                receipt.get('restore_pair_matches') is not raw_equal or
                receipt.get('candidate_restore_pair_matches') is not candidate_equal or not candidate_equal):
            raise ValueError('Independent trace/state comparison failed or differs from driver')
        recheck()
        if _keyed(p.hash_ledger(root, deadline)) != _keyed(original_ledger):
            raise ValueError('Fresh allocated/started/raw evidence changed during independent readback')
        close['immutable_inputs_and_raw_evidence_unchanged'] = True
        close['storage_before_close'] = storage.check(0, path=target)
        p.deadline_check(deadline)
        close.update(status='narrow-restore-passed', narrow_restore_passed=True,
            closed_monotonic=time.monotonic())
        replace_control(target, close, storage)
        p.deadline_check(deadline)
        storage.check(0, path=target)
        p.deadline_check(deadline)
    except BaseException as error:
        close.update(status='scientific-close-stop', narrow_restore_passed=False,
            error={'type': type(error).__name__, 'message': str(error)})
        # Failure publication never extends the scientific deadline or adds physics.
        try:
            replace_control(target, close, storage)
        except BaseException as publication_error:
            close['failure_publication_error'] = {'type': type(publication_error).__name__, 'message': str(publication_error)}
            # Preserve the bytes, but remove authority if invalidation cannot publish.
            if target.exists() and p.read_json(target).get('narrow_restore_passed') is True:
                target.rename(root/'scientific-close.invalidated.json')
    print(json.dumps({key: close.get(key) for key in
        ('status', 'narrow_restore_passed', 'restore_pair_matches', 'candidate_restore_pair_matches', 'error',
         'failure_publication_error')}, indent=2), flush=True)
    return 0 if close['narrow_restore_passed'] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    return audit(parser.parse_args(argv).registration)


if __name__ == '__main__':
    raise SystemExit(main())
