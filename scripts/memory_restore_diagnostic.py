"""Registered restore diagnosis or fixed-profile fresh prerequisites; never pilot.

Decision rule: one diagnostic pair. Repair only a proven violation of the existing
state contract; unlocalized/non-reproduced differences or required normalization
changes stop. Diagnostic recordings never count as prerequisite qualification.
"""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import time

from scripts import memory_decision_pilot as p
from scripts.memory_waypoint_study import cleanup_owners, replace_control
from palimpsest.snapshots import read_snapshot, state_digest

PROFILE = '7faba0a56d129ea051d5c28a019964034b546923dbe49cedb3a605af84437ec3'
CAPS = {'diagnose': (600, 300), 'qualify': (4300, 600), 'restore-v2': (600, 300)}
STATE_CONTRACT = 'restore-reproducibility-v2-candidate'


def runtime_v2_identity():
    import importlib.metadata
    environment = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                   'NUMEXPR_NUM_THREADS', 'MUJOCO_GL', 'CUDA_VISIBLE_DEVICES')
    return {'python_path': sys.executable, 'python_resolved_path': str(Path(sys.executable).resolve()),
        'python_sha256': p.file_hash(Path(sys.executable).resolve()),
        'python_version': list(sys.version_info[:3]), 'platform': platform.platform(),
        'host': socket.gethostname(),
        'versions': {name: importlib.metadata.version(name) for name in ('numpy', 'mujoco', 'torch')},
        'environment': {name: os.environ.get(name) for name in environment}}


def validate_v2_registration(registration):
    """The new scope never broadens a legacy registration or preserved root."""
    if (registration.get('schema') != 'memory-restore-registration-v2'
            or registration.get('mode') != 'restore-v2'
            or registration.get('state_contract') != STATE_CONTRACT
            or registration.get('seconds_caps') != [600, 300]
            or registration.get('expected_specs') != p.travel_specs('travel-feasibility', PROFILE)[-2:]
            or not isinstance(registration.get('runtime'), dict) or not registration['runtime']):
        raise ValueError('Unknown or incomplete v2 registration')
    repo = p.checked_path(registration['repo'])
    control = p.checked_path(registration['control_root'])
    publication = p.checked_path(registration['publication_root'])
    output = p.checked_path(registration['output'])
    if (control != repo/'.superpowers/sdd/restore-qualification-v2'
            or publication != repo/'docs/reports/restore-qualification-v2-evidence'
            or output.parent != repo/'runs' or not output.name.startswith('restore-v2-pair-')):
        raise ValueError('Registered v2 output/control/publication path differs')
    paths = {'comparator': repo/'scripts/memory_restore_offline_readout.py',
             'auditor': repo/'scripts/memory_restore_v2_audit.py',
             'launcher': publication/'execute-restore-v2.py'}
    for name, expected in paths.items():
        digest = registration.get(name+'_sha256')
        if (registration.get(name+'_path') != str(expected) or type(digest) is not str
                or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('Missing or invalid v2 '+name+' binding')
    preserved = registration.get('preserved_sets')
    protected = [p.checked_path(path) for path in registration.get('protected_roots', [])]
    if not isinstance(preserved, list) or not preserved:
        raise ValueError('Missing preserved v2 evidence inventory')
    required = [p.checked_path(registration['prior_output']),
                p.checked_path(registration['source_snapshot']['path']),
                *(p.checked_path(item['root']) for item in preserved)]
    if any(path not in protected for path in required):
        raise ValueError('Preserved v2 source protection is incomplete')
    sources = p.source_paths(repo, registration['assets'], registration['history_root'])+protected
    if any(p.overlaps(root, source) for root in (output, control, publication) for source in sources):
        raise ValueError('Registered v2 output overlaps preserved source')
    if any(p.overlaps(a, b) for a, b in ((output, control), (output, publication), (control, publication))):
        raise ValueError('Registered v2 counted roots overlap')


def restore_v2_budget(registration):
    from palimpsest.storage import StorageBudget, StorageLimits
    return StorageBudget(tuple(p.checked_path(registration[key]) for key in
        ('output', 'control_root', 'publication_root')), StorageLimits(max_bytes=8*p.GiB,
        min_free_bytes=2*p.GiB, max_runs=38, max_snapshots=1), headroom_bytes=64*p.MiB)


def recheck_v2_inputs(registration, deadline=None):
    validate_v2_registration(registration)
    if runtime_v2_identity() != registration['runtime']:
        raise ValueError('Registered v2 runtime differs')
    for name in ('comparator', 'auditor', 'launcher'):
        if p.file_hash(registration[name+'_path']) != registration[name+'_sha256']:
            raise ValueError('Registered v2 '+name+' changed')
        p.deadline_check(deadline)
    recheck_inputs(registration, deadline)
    reference = registration['source_snapshot']; source = p.checked_path(reference['path'])
    if source.stat().st_size != reference['bytes'] or p.file_hash(source) != reference['sha256']:
        raise ValueError('Registered v2 raw source changed')
    from scripts.memory_restore_offline_readout import verify_inventory
    for reference in registration['preserved_sets']:
        verify_inventory(reference, deadline)
    p.deadline_check(deadline)


def compare_states(left, right, left_ids, right_ids):
    """Exact existing normalized state comparison; bounded details, complete hashes."""
    result = compare_values(p.repeat_post_state(left, left_ids), p.repeat_post_state(right, right_ids))
    result['normalization'] = 'unchanged condition_state and new-destination-receipt IDs only'
    return result


def compare_values(a, b):
    """Compare complete typed dictionaries without applying any normalization."""
    import numpy as np
    hashes = [{key: state_digest(value) for key, value in state.items()} for state in (a, b)]
    differing = [key for key in sorted(set(a)|set(b)) if hashes[0].get(key) != hashes[1].get(key)]
    differences = []

    def walk(one, two, path):
        if state_digest(one) == state_digest(two) or len(differences) >= 64:
            return
        row = {'path': path, 'left_type': type(one).__name__, 'right_type': type(two).__name__}
        if type(one) is type(two) is dict:
            for key in sorted(set(one)|set(two)):
                if len(differences) >= 64:
                    break
                child = path+'/'+key.replace('~', '~0').replace('/', '~1')
                if key not in one or key not in two:
                    differences.append({'path': child, 'reason': 'missing-key',
                        'left_present': key in one, 'right_present': key in two})
                else:
                    walk(one[key], two[key], child)
            return
        if type(one) is type(two) and type(one) in (list, tuple):
            if len(one) == len(two):
                for index, (x, y) in enumerate(zip(one, two)):
                    walk(x, y, path+'/'+str(index))
                return
            row.update(reason='length', left_length=len(one), right_length=len(two))
        elif isinstance(one, np.ndarray) and isinstance(two, np.ndarray):
            row.update(left_dtype=one.dtype.str, right_dtype=two.dtype.str,
                       left_shape=list(one.shape), right_shape=list(two.shape))
            if one.dtype == two.dtype and one.shape == two.shape:
                x = np.frombuffer(one.tobytes(), dtype=np.dtype(('V', one.dtype.itemsize)))
                y = np.frombuffer(two.tobytes(), dtype=np.dtype(('V', two.dtype.itemsize)))
                row['different_elements'] = int(np.count_nonzero(x != y))
                row['first_flat_indices'] = np.flatnonzero(x != y)[:16].tolist()
                if one.dtype.kind in 'if' and one.size:
                    delta = np.abs(one.astype(np.float64)-two.astype(np.float64))
                    if np.isfinite(delta).all():
                        row['max_abs_difference'] = float(delta.max())
        elif type(one) is type(two) is bytes:
            different, offsets = 0, []
            for index, (x, y) in enumerate(zip(one, two)):
                if x != y:
                    different += 1
                    if len(offsets) < 16:
                        offsets.append(index)
            row.update(left_bytes=len(one), right_bytes=len(two),
                       different_bytes=different+abs(len(one)-len(two)),
                       first_offsets=offsets, reason='opaque-bytes')
        else:
            row.update(left_preview=repr(one)[:256], right_preview=repr(two)[:256])
        differences.append(row)

    walk(a, b, '')
    return {'equal': state_digest(a) == state_digest(b), 'left_digest': state_digest(a),
        'right_digest': state_digest(b), 'component_hashes': hashes,
        'differing_components': differing, 'differences': differences,
        'detail_limit': 64, 'details_may_be_truncated': len(differences) == 64}


def native_fields(snapshot):
    """Decode trusted same-version native bytes offline; never forward/reset/step."""
    import mujoco
    import numpy as np
    data = mujoco.MjData.__new__(mujoco.MjData)
    data.__setstate__(snapshot['native_data'])
    fields = {'model_native_sha256': p.hashlib.sha256(data.model.__getstate__()).hexdigest()}
    omitted = []
    def retain(value, path):
        if isinstance(value, np.ndarray) and value.dtype.kind in 'buif' and value.dtype.fields is None:
            if value.flags.owndata:
                # A null MjData arena pointer can produce a fresh NumPy-owned
                # array. Its contents are not evidence from the native payload.
                omitted.append({'field':path,'reason':'owned NumPy array is not a view of native storage',
                                'shape':list(value.shape),'dtype':value.dtype.str})
            else:
                fields[path] = value.copy()
        elif type(value) in (int, float, bool):
            fields[path] = value
    for name in dir(data):
        if name.startswith('_') or name == 'model':
            continue
        try:
            value = getattr(data, name)
            retain(value, name)
            if name in ('timer', 'warning', 'solver', 'contact'):
                for child in dir(value):
                    if not child.startswith('_'):
                        retain(getattr(value, child), name+'.'+child)
        except (ValueError, AttributeError) as error:
            omitted.append({'field': name, 'error': str(error)[:256]})
    return fields, omitted


def compare_native_states(left, right):
    one, omitted_one = native_fields(left); two, omitted_two = native_fields(right)
    result = compare_values(one, two)
    result.update(decoded_field_count=[len(one), len(two)], omitted_fields=[omitted_one, omitted_two],
        physics_steps=0, scope='Exposed plain numeric MjData scalars and native-storage views plus timer/warning/solver/contact arrays and serialized model hash; owned NumPy arrays are omitted as unbacked views; opaque residual native bytes remain outside this named-field inventory')
    return result


def copy_source(reference, destination, storage):
    source, destination = p.checked_path(reference['path']), p.checked_path(destination)
    if source.stat().st_size != reference['bytes'] or p.file_hash(source) != reference['sha256']:
        raise ValueError('Prior source checksum differs')
    snapshot = read_snapshot(source)
    if p.condition_digest(snapshot) != reference['invariant']:
        raise ValueError('Prior source invariant differs')
    if source.stat().st_size > 16*p.MiB:
        raise ValueError('Source exceeds snapshot publication bound')
    storage.check(source.stat().st_size, path=destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as target, source.open('rb') as stream:
        target.write(stream.read(16*p.MiB+1)); target.flush(); os.fsync(target.fileno())
    if p.file_hash(destination) != reference['sha256']:
        raise ValueError('Copied source checksum differs')
    return {'snapshot_path': str(destination), 'snapshot_sha256': reference['sha256'],
            'invariant': reference['invariant'], 'original_source': reference}


def audit_post_state(run, report):
    run = p.checked_path(run)
    path = p.checked_path(report.get('post_snapshot_path', run/'snapshots/post-repeat.snp'))
    if path != run/'snapshots/post-repeat.snp' or not path.is_file():
        raise ValueError('Retained post-state missing or outside its fixed path')
    if p.file_hash(path) != report.get('post_snapshot_sha256'):
        raise ValueError('Retained post-state checksum differs')
    initial_path = p.checked_path(report['snapshot_path'])
    if initial_path != run/'snapshots/initial.snp':
        raise ValueError('Initial snapshot path differs')
    initial = read_snapshot(initial_path)
    ids = set(initial['application']['receipts'])
    if report.get('repeat_source_receipt_ids') != sorted(ids):
        raise ValueError('Post-state source receipt binding differs')
    snapshot = read_snapshot(path)
    normalized = p.repeat_post_state(snapshot, ids)
    if state_digest(normalized) != report.get('post_state_digest'):
        raise ValueError('Retained post-state digest differs from worker')
    components = {key: state_digest(value) for key, value in normalized.items()}
    if components != report.get('post_state_components'):
        raise ValueError('Retained post-state component digest differs')
    return snapshot, ids


def owner_exited(owner):
    pid, start, pgid = (owner[k] for k in ('pid', 'starttime', 'pgid'))
    if any(type(v) is not int or v <= 0 for v in (pid, start, pgid)) or pid != pgid:
        raise ValueError('Invalid native owner identity')
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return (int(fields[19]), os.getpgid(pid)) != (start, pgid)
    except (FileNotFoundError, ProcessLookupError):
        return True


def audit_owners(stage, attempted, deadline):
    """Discover allocated jobs, including started owners absent from score receipts."""
    stage = p.checked_path(stage); rows = []
    for path in sorted((stage/'jobs').glob('*.json')):
        p.deadline_check(deadline)
        job = p.validate_job(p.read_json(path), read_only=True); run = p.checked_path(job['output'])
        if run != stage/'runs'/job['run_id'] or path.name != job['run_id']+'.json':
            raise ValueError('Allocated owner path differs')
        row = {'run_id': job['run_id'], 'job_id': job['spec']['id'], 'operation': job['operation'],
               'raw_audit_pass': False, 'disposition': 'allocated-unstarted'}
        owner_path = run/'owner.json'
        if owner_path.exists():
            row.update(owner=p.read_json(owner_path), disposition='started-incomplete')
            if row['owner'].get('run_id') != job['run_id']:
                raise ValueError('Started owner run identity differs')
            row['matching_owner_exited'] = owner_exited(row['owner'])
            if not row['matching_owner_exited']:
                raise ValueError('Matching native owner remains active')
            try:
                supervision = attempted.get(job['run_id'], {}).get('supervision', {})
                audit = p.audit_run(job, supervision, deadline)
                row.update(disposition='audited-recording', raw_audit_pass=True, audit=audit,
                           raw_rows=len(p.read_raw(run, deadline)['rows']))
                if job['operation'] == 'repeat':
                    audit_post_state(run, audit)
                    row['retained_post_state_audited'] = True
            except Exception as error:
                row.update(raw_audit_pass=False, disposition='started-incomplete',
                           audit_error={'type': type(error).__name__, 'message': str(error)})
        rows.append(row)
    known = {row['run_id'] for row in rows}
    for path in stage.rglob('owner.json'):
        p.deadline_check(deadline)
        if p.read_json(path).get('run_id') not in known:
            raise ValueError('Started owner has no allocated job')
    return rows


def run_pair(plan, storage, deadline, source, checkpoint=None):
    results = []
    for spec in p.travel_specs('travel-feasibility', plan['selected_profile_sha256'])[-2:]:
        p.deadline_check(deadline)
        if plan.get('restore_v2_budget_reservation') is True:
            # The unchanged child budgets its run root only. Reserve its complete
            # recording, two SNPs and bounded control/log allowance across all
            # three roots; concurrent parent logs fit the existing 64 MiB reserve.
            storage.check(512*p.MiB+2*16*p.MiB+4*p.MiB, path=Path(plan['output'])/'runs')
        result = p.launch_owner('travel-feasibility', spec, plan, storage, deadline,
                                source=source, retain_repeat_state=True)
        results.append(result)
        if checkpoint is not None:
            checkpoint(results)
        if result.get('status') != 'recorded' or not result.get('raw_audit_pass'):
            raise ValueError('Diagnostic owner did not complete independently audited five ticks')
    return results


def recheck_inputs(registration, deadline):
    p.deadline_check(deadline)
    repo = Path(registration['repo']); assets = Path(registration['assets'])
    if p.source_identity(repo, assets) != registration['source_identity']:
        raise ValueError('Registered source or assets changed')
    if p.file_hash(__file__) != registration['diagnostic_driver_sha256']:
        raise ValueError('Diagnostic driver changed')
    if p.file_hash(registration['contract']) != registration['contract_sha256']:
        raise ValueError('Diagnostic contract changed')
    for reference in registration['history_inputs'].values():
        if p.file_hash(reference['path']) != reference['sha256']:
            raise ValueError('Registered historical input changed')
    for entry in registration['prior_inventory']:
        p.deadline_check(deadline)
        path = p.checked_path(Path(registration['prior_output'])/entry['path'])
        if not path.is_relative_to(Path(registration['prior_output'])) or path.stat().st_size != entry['bytes'] or p.file_hash(path) != entry['sha256']:
            raise ValueError('Prior immutable recording changed')
    p.deadline_check(deadline)


def main(argv=None):
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    args = parser.parse_args(argv)
    registration = p.read_json(args.registration)
    v2 = registration.get('mode') == 'restore-v2'
    if v2:
        validate_v2_registration(registration)
    elif registration.get('schema') != 'memory-restore-registration-v1' or registration.get('mode') not in ('diagnose', 'qualify'):
        raise ValueError('Unknown diagnostic registration')
    mode = registration['mode']; owner_cap, readout_cap = CAPS[mode]
    global_deadline = started+owner_cap+readout_cap; owner_deadline = started+owner_cap
    repo = p.checked_path(registration['repo'])
    if repo != Path(__file__).resolve().parents[1] or registration['profile_sha256'] != PROFILE:
        raise ValueError('Registered checkout or fixed profile differs')
    if registration.get('protocol_sha256') != p.TRAVEL_PROTOCOL_SHA256:
        raise ValueError('Existing travel protocol differs')
    if list(registration.get('seconds_caps', [])) != [owner_cap, readout_cap]:
        raise ValueError('Registered diagnostic allocation differs')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo):
        raise ValueError('Native admission requires a clean implementation checkout')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    if subprocess.check_output(['git', 'diff', registration['implementation_commit'], head, '--name-only',
        '--', 'src', 'scripts', 'tests', 'model_manifests', 'uv.lock', 'upstream'], cwd=repo):
        raise ValueError('Registered implementation differs')
    sources = p.source_paths(repo, registration['assets'], registration['history_root'])
    if v2:
        sources += registration['protected_roots']+[registration['control_root'], registration['publication_root']]
    root = p.safe_output(registration['output'], sources)
    if root.exists():
        raise ValueError('Registered invocation output already exists; no retry')
    recheck = recheck_v2_inputs if v2 else recheck_inputs
    recheck(registration, owner_deadline)
    plan = p.preflight(repo, Path(registration['assets']), Path(registration['history_root']),
        root/'stage', root, owner_deadline, profile_sha256=PROFILE)
    plan.update(protocol=p.TRAVEL_PROTOCOL, protocol_sha256=p.TRAVEL_PROTOCOL_SHA256,
                selected_profile_sha256=PROFILE)
    if v2:
        plan['restore_v2_budget_reservation'] = True
    storage = restore_v2_budget(registration) if v2 else p.phase_budget(root)
    receipt = {'schema': 'memory-restore-execution-v2' if v2 else 'memory-restore-execution-v1', 'mode': mode, 'implementation_head': head,
        'registration_sha256': p.file_hash(args.registration), 'source_identity': registration['source_identity'],
        'started_utc': datetime.now(timezone.utc).isoformat(), 'started_monotonic': started,
        'global_deadline_monotonic': global_deadline, 'owner_deadline_monotonic': owner_deadline,
        'seconds_caps': [owner_cap, readout_cap], 'output': str(root), 'status': 'running',
        'attempted': [], 'qualification_claims': [], 'paired_pilot': 'unattempted-by-scope',
        'held_out_used': False, 'retries': 0, 'native_prerequisites_passed': False}
    if v2:
        receipt.update(state_contract=STATE_CONTRACT, candidate_restore_pair_matches=False,
                       narrow_restore_passed=False, process_namespace=os.readlink('/proc/self/ns/pid'))
    def interrupted(signum, frame):
        raise RuntimeError('External invocation interruption: '+str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    root.mkdir(parents=True, exist_ok=False)
    with storage.lock():
        stage = root/'stage'; stage.mkdir()
        p.write_control(root/'registration.json', registration, storage)
        p.write_control(stage/'preflight.json', plan, storage)
        replace_control(root/'execution.json', receipt, storage)
        try:
            if mode in ('diagnose', 'restore-v2'):
                source = copy_source(registration['source_snapshot'], stage/'source/snapshots/initial.snp', storage)
                p.write_control(root/'source-copy.json', source, storage)
                def checkpoint(results):
                    receipt['attempted'] = results
                    replace_control(root/'execution.json', receipt, storage)
                receipt['attempted'] = run_pair(plan, storage, owner_deadline, source, checkpoint)
            else:
                qualification = p.execute_stage('travel-feasibility', plan, storage, owner_deadline,
                                                retain_repeat_state=True)
                receipt['attempted'] = qualification['attempted']
                receipt['qualification'] = qualification
            p.deadline_check(owner_deadline)
            receipt['status'] = 'recorded-bounded-attempt'
        except BaseException as error:
            receipt.update(status='owner-or-admission-stop', error={'type': type(error).__name__, 'message': str(error)})
        finally:
            readout_started = time.monotonic()
            readout_deadline = min(global_deadline, readout_started+readout_cap)
            receipt.update(readout_started_monotonic=readout_started, readout_deadline_monotonic=readout_deadline)
            gates = False  # Provisional until all integrity/storage/deadline checks finish.
            try:
                receipt['cleanup'] = cleanup_owners(root)
                p.deadline_check(readout_deadline)
                attempted = {row['run_id']: row for row in receipt['attempted']}
                rows = audit_owners(stage, attempted, readout_deadline)
                receipt['owners'] = rows
                expected = (p.travel_specs('travel-feasibility', PROFILE)[-2:] if mode in ('diagnose', 'restore-v2')
                            else p.travel_specs('travel-feasibility', PROFILE))
                by_id = {row['job_id']: row for row in rows}
                receipt['unattempted'] = [spec['id'] for spec in expected if spec['id'] not in by_id]
                complete = (receipt['status'] == 'recorded-bounded-attempt'
                    and len(rows) == len(expected) and not receipt['unattempted']
                    and all(row['raw_audit_pass'] and row.get('matching_owner_exited') for row in rows))
                repeats = [by_id[name] for name in ('restore-1', 'restore-2') if name in by_id]
                if len(repeats) == 2 and all(row.get('retained_post_state_audited') for row in repeats):
                    posts = [audit_post_state(stage/'runs'/row['run_id'], row['audit']) for row in repeats]
                    comparison = compare_states(posts[0][0], posts[1][0], posts[0][1], posts[1][1])
                    p.write_control(root/'state-comparison.json', comparison, storage)
                    if 'native_data' in comparison['differing_components']:
                        p.deadline_check(readout_deadline)
                        p.write_control(root/'native-field-comparison.json',
                            compare_native_states(posts[0][0], posts[1][0]), storage)
                    receipt['comparison'] = {k: comparison[k] for k in ('equal','left_digest','right_digest','differing_components')}
                    trace_equal = repeats[0]['audit']['trace_digest'] == repeats[1]['audit']['trace_digest']
                    receipt['restore_pair_matches'] = (comparison['equal'] and trace_equal and
                        all(row['audit'].get('invariants_preserved') is True for row in repeats))
                    if v2:
                        from scripts.memory_restore_offline_readout import compare_reproducibility_states
                        candidate = compare_reproducibility_states(posts[0][0], posts[1][0],
                            posts[0][1], posts[1][1], readout_deadline)
                        p.write_control(root/'candidate-state-comparison.json', candidate, storage)
                        receipt['candidate_comparison'] = {k: candidate[k] for k in
                            ('equal', 'left_digest', 'right_digest', 'differing_components', 'contract_id')}
                        receipt['candidate_restore_pair_matches'] = (candidate['equal'] and trace_equal
                            and all(row['audit'].get('invariants_preserved') is True for row in repeats))
                else:
                    receipt['restore_pair_matches'] = False
                if v2:
                    receipt['status'] = ('narrow-restore-provisional-pass' if complete
                        and receipt['candidate_restore_pair_matches'] else 'narrow-restore-failure')
                elif mode=='diagnose':
                    receipt['status'] = ('diagnostic-pair-audited' if complete else 'diagnostic-evidence-stop')
                else:
                    gates = complete and receipt['restore_pair_matches'] and all(
                        p.prerequisite_pass(spec['mandatory'], {**by_id[spec['id']]['audit'],
                            'repeat_matches': receipt['restore_pair_matches']}) for spec in expected)
                    receipt['status'] = 'native-prerequisite-failure'
                recheck(registration, readout_deadline)
                receipt['source_and_prior_evidence_unchanged'] = True
                receipt['artifact_index'] = [item for item in p.hash_ledger(root, readout_deadline)
                                             if item['path'] != 'execution.json']
                receipt['storage_before_close'] = storage.usage()
                receipt['total_new_controls'] = sum(row.get('raw_rows', 0) for row in rows)
                p.deadline_check(readout_deadline)
                if mode == 'qualify' and gates:
                    receipt.update(status='native-prerequisites-passed', native_prerequisites_passed=True)
            except BaseException as error:
                receipt.update(status='independent-readout-stop', native_prerequisites_passed=False,
                    qualification_claims=[], readout_error={'type': type(error).__name__, 'message': str(error)})
            receipt.update(readout_seconds=time.monotonic()-readout_started, total_seconds=time.monotonic()-started)
            try:
                p.deadline_check(readout_deadline)
                replace_control(root/'execution.json', receipt, storage)
                p.deadline_check(readout_deadline)
            except BaseException as error:
                receipt.update(status='independent-readout-stop', native_prerequisites_passed=False,
                    qualification_claims=[], close_error={'type': type(error).__name__, 'message': str(error)})
                # Invalidate any success written just before crossing the deadline.
                # This best-effort failure receipt adds no measurement or qualification.
                replace_control(root/'execution.json', receipt, storage)
    print(json.dumps({key: receipt.get(key) for key in ('status','mode','total_seconds','readout_seconds',
        'total_new_controls','restore_pair_matches','comparison','native_prerequisites_passed')}, indent=2), flush=True)
    return 0 if receipt['status'] in ('diagnostic-pair-audited','native-prerequisites-passed',
        'native-prerequisite-failure','narrow-restore-provisional-pass') else 1


if __name__ == '__main__':
    raise SystemExit(main())
