"""Independent post-processing only; never launch or promote a native owner."""
import json
import math
import os
from pathlib import Path
import shutil
import time

from scripts import memory_decision_pilot as p


def execution_receipt(root):
    available = []
    for name in ('execution.json', 'execution.json.pending'):
        path = root/name
        if path.exists():
            try:
                value = p.read_json(path)
                if not isinstance(value, dict):
                    raise ValueError('Receipt is not an object')
                available.append((value, path))
            except (ValueError, OSError):
                continue
    if not available:
        raise ValueError('No readable execution receipt; no native qualification')
    value, path = max(available, key=lambda row: row[0].get('elapsed_seconds', 0))
    return value, path, [{'path': str(f), 'sha256': p.file_hash(f)} for _, f in available]


def verify_index(root, entries, deadline):
    verified = []
    for entry in entries:
        p.deadline_check(deadline)
        path = p.checked_path(root/entry['path'])
        if not path.is_relative_to(root):
            raise ValueError('Indexed path escapes output')
        if path.stat().st_size != entry['bytes'] or p.file_hash(path) != entry['sha256']:
            raise ValueError('Indexed artifact differs: '+entry['path'])
        verified.append(entry['path'])
    return verified


def compare_scored(scored, audited):
    # audit_prefix_failure does not emit launcher fields; repeat_matches is
    # stage reconciliation, not an individual auditor result.
    for key, value in audited.items():
        if key not in scored or scored[key] != value:
            raise ValueError('Published audit differs: '+key)


def disposition(*, owner_started, audit, scored):
    if not owner_started:
        return 'unattempted'
    if audit is None or audit.get('raw_audit_pass') is not True:
        return 'started-incomplete-or-unqualified'
    if scored is None:
        return 'audited-but-unscored'
    return 'audited-task-failure' if audit.get('retained_task_failure') is True else 'audited-recording'


def repeat_equal(repeats):
    return (len(repeats) == 2 and all(
        r.get('raw_audit_pass') is True and r.get('invariants_preserved') is True
        and r.get('continuation_ticks') == 5 and r.get('trace_digest') is not None
        and r.get('post_state_digest') is not None for r in repeats)
        and repeats[0]['trace_digest'] == repeats[1]['trace_digest']
        and repeats[0]['post_state_digest'] == repeats[1]['post_state_digest'])


def selection_valid(specs, rows, selected):
    if selected is None:
        return False
    for spec, row in zip(specs, rows):
        audit = row.get('audit', {})
        if row['job_id'] != spec['id']:
            return False
        if spec['profile_sha256'] == selected:
            return (row['disposition'] == 'audited-recording' and audit.get('raw_audit_pass') is True
                and audit.get('acquired') is True and audit.get('goal') is True
                and audit.get('first_commitment_blocked') is True and audit.get('retreat_completed') is True
                and audit.get('replans', 0) >= 1)
        if row['disposition'] != 'audited-task-failure' or audit.get('retained_task_failure') is not True:
            return False
    return False


def verify_restore_source(job, source):
    if source is None or any(job[k] != source[v] for k, v in (
        ('snapshot_path', 'snapshot_path'), ('snapshot_sha256', 'snapshot_sha256'),
        ('expected_invariant', 'invariant'))):
        raise ValueError('Restore source differs from the new south-prefix')


def stop_status(development, prerequisites, *, selection_ok):
    if not selection_ok:
        return ('audited-task-stop' if development and all(
            r['disposition'] == 'audited-task-failure' for r in development)
            else 'infrastructure-or-evidence-stop')
    if any(r['disposition'] == 'audited-task-failure' for r in prerequisites):
        return 'audited-task-stop'
    return 'infrastructure-or-evidence-stop'


def owner_exited(owner):
    pid, start, pgid = (owner[k] for k in ('pid', 'starttime', 'pgid'))
    if any(type(v) is not int or v <= 0 for v in (pid, start, pgid)) or pid != pgid:
        raise ValueError('Invalid owner identity')
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return (int(fields[19]), os.getpgid(pid)) != (start, pgid)
    except (FileNotFoundError, ProcessLookupError):
        return True


def terminal_and_plot(root, job, audited, data, deadline):
    """Draw only independently audited trajectories, including admitted failures."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from palimpsest import memory_decision_world as w
    poses = [row['pose'].tolist() for row in data['rows']]
    if not poses:
        raise ValueError('Audited recording contains no controls')
    poses.append(data['rows'][-1]['next_pose'].tolist())
    case = job['case']; terminal = None
    outcome = audited.get('outcome') or {}
    if outcome.get('type') == 'CueUnavailable':
        target = outcome['message'].removeprefix('selected_waypoint_unavailable: ')
        xy = case['landmarks'][target]; pose = poses[-1]
        packets = [e['packet'] for e in data['events'] if e['kind'] == 'memory_sensed']
        terminal = {'tick': packets[-1]['tick'], 'target': target, 'target_xy': xy, 'pose': pose,
            'range_m': math.dist(pose[:2], xy), 'relative_bearing_degrees': math.degrees(
                math.remainder(math.atan2(xy[1]-pose[1], xy[0]-pose[0])-pose[2], 2*math.pi)),
            'terminal_packet_and_exception_replayed_by_existing_auditor': True}
    profile = w.registered_profile(case['profile_sha256'])
    fig, ax = plt.subplots(figsize=(7, 6))
    for xy in profile['obstacles']:
        ax.add_patch(Circle(xy, profile['obstacle_radius'], color='#dddddd'))
    xy = list(case['landmarks'].values())
    ax.scatter([v[0] for v in xy], [v[1] for v in xy], s=8, color='#999999', label='Registered cues')
    ax.plot([v[0] for v in poses], [v[1] for v in poses], color='#236b8e', label='Audited measured path')
    ax.scatter(*case['goal_xy'], marker='*', s=100, color='#48783f', label='Goal')
    if terminal:
        x, y, yaw = terminal['pose']
        ax.scatter(x, y, color='#b02b32', marker='x', s=65)
        ax.plot([x, terminal['target_xy'][0]], [y, terminal['target_xy'][1]], color='#b02b32')
        ax.arrow(x, y, .4*math.cos(yaw), .4*math.sin(yaw), head_width=.08, color='#b02b32')
    ax.set_title(f"{job['spec']['id']}: {len(data['rows'])} controls, goal={audited.get('goal')}")
    ax.set(xlabel='x (m)', ylabel='y (m)'); ax.set_aspect('equal'); ax.grid(alpha=.15); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(root/('measured-'+job['run_id']+'.svg')); plt.close(fig)
    p.deadline_check(deadline)
    return terminal


def run_readout(root, registration, evidence):
    from palimpsest import memory_decision_world as w
    root = p.checked_path(root); evidence = p.checked_path(evidence)
    receipt, receipt_path, available = execution_receipt(root)
    deadline = min(receipt['phase_deadline_monotonic'], receipt['readout_deadline_monotonic'])
    p.deadline_check(deadline)
    if (str(root) != registration['output'] or receipt['protocol_sha256'] != registration['protocol_sha256']
            or receipt['source_identity'] != registration['source_identity']):
        raise ValueError('Execution differs from registration')
    plan = p.read_json(root/'development/preflight.json')
    if (p.source_identity(Path(plan['repo']), Path(plan['assets'])) != registration['source_identity']
            or plan['history_inputs'] != registration['history_inputs']):
        raise ValueError('Scientific source/assets/histories differ')
    registered = registration['candidates']; ledger = p.read_json(root/'candidates.json')
    if ledger['protocol_sha256'] != registration['protocol_sha256'] or len(ledger['candidates']) != 3:
        raise ValueError('Candidate ledger differs')
    for actual, expected in zip(ledger['candidates'], registered):
        if any(actual[k] != expected[k] for k in ('spec', 'case', 'profile')):
            raise ValueError('Candidate inputs differ from prospective registration')
    index = [e for e in receipt.get('artifact_index', []) if e['path'] != 'execution.json.pending']
    result = {'schema': 'memory-travel-recovery-readout-v1', 'started_monotonic': time.monotonic(),
        'receipt_used': str(receipt_path), 'available_receipts': available,
        'original_indexed_files_verified': verify_index(root, index, deadline),
        'original_index_present': bool(index), 'source_identity_unchanged': True,
        'owners': [], 'stages': {}, 'native_prerequisites_passed': False,
        'qualification_claims': [], 'r2_complete': False, 'held_out_used': False,
        'paired_pilot': 'unattempted-by-scope', 'native_retries': 0, 'errors': []}
    all_audits = {}; selected = receipt.get('stages', {}).get('development', {}).get('selected_profile_sha256')
    for stage in ('development', 'prerequisites'):
        stage_report = receipt.get('stages', {}).get(stage, {})
        scored_rows = stage_report.get('attempted', [])
        scored_by = {r['run_id']: r for r in scored_rows}
        specs = p.travel_specs('travel-development') if stage == 'development' else (
            p.travel_specs('travel-feasibility', selected) if selected else p.feasibility_specs())
        expected_by = {s['id']: s for s in specs}; rows_by = {}
        for jobfile in sorted((root/stage/'jobs').glob('*.json')):
            p.deadline_check(deadline); job = p.read_json(jobfile); run = p.checked_path(job['output'])
            ident = job['run_id']; name = job['spec']['id']
            if (name in rows_by or job['version'] != 3 or job['protocol_sha256'] != registration['protocol_sha256']
                    or job['source_identity'] != registration['source_identity'] or job['spec'] != expected_by.get(name)
                    or job['phase_root'] != str(root) or run != root/stage/'runs'/ident
                    or jobfile.stem != ident or job['repo'] != registration['repo']
                    or job['assets'] != registration['assets'] or job['history_root'] != registration['history_root']):
                raise ValueError('Retained job differs from registered input/allocation')
            spec = job['spec']; case = w.make_case(spec['seed'], spec['regime'], spec['kind'], spec['mirrored'],
                profile_sha256=spec['profile_sha256'])
            if job['case'] != case or job['operation'] != spec['operation'] or job['condition'] is not None:
                raise ValueError('Retained case/operation differs')
            row = {'stage': stage, 'job_id': name, 'run_id': ident, 'profile_sha256': case['profile_sha256']}
            owner_path = run/'owner.json'; started = owner_path.exists(); audit = None
            if started:
                owner = p.read_json(owner_path); row.update(owner=owner, matching_owner_exited=owner_exited(owner))
                if not row['matching_owner_exited']:
                    raise ValueError('Matching native owner remains active')
            try:
                worker = p.read_json(run/'worker-report.json')
                if not started:
                    raise ValueError('Missing actual owner identity')
                if job['operation'] == 'repeat':
                    source = next((r for r in scored_rows if r['job_id'] == spec['source']), None)
                    verify_restore_source(job, source)
                supervision = root/stage/'supervision'/ident
                canonical = supervision/'supervisor.json'; draft = supervision/'supervisor.tmp'
                supervised = p.read_json(canonical)
                if supervised.get('status') == 'running' and draft.exists():
                    supervised = p.read_json(draft); row['unpublished_supervision_used'] = True
                audit = (p.audit_prefix_failure(job, supervised, deadline) if worker.get('acquired') is False
                         else p.audit_run(job, supervised, deadline))
                scored = scored_by.get(ident)
                if scored is not None and scored.get('raw_audit_pass') is True:
                    compare_scored(scored, audit)
                elif scored is not None:
                    raise ValueError('Independent audit differs from unqualified launcher result')
                data = p.read_raw(run, deadline)
                row.update(audit=audit, raw_rows=len(data['rows']),
                    terminal_failure=terminal_and_plot(root, job, audit, data, deadline))
                all_audits[ident] = audit
            except Exception as error:
                row['audit_refusal'] = {'type': type(error).__name__, 'message': str(error)}
                result['errors'].append({'run_id': ident, **row['audit_refusal']}); audit = None
            row['disposition'] = disposition(owner_started=started, audit=audit, scored=scored_by.get(ident))
            rows_by[name] = row; result['owners'].append(row)
        if set(scored_by)-{r['run_id'] for r in rows_by.values()}:
            raise ValueError('Published score has no retained job')
        result['stages'][stage] = [rows_by.get(s['id'], {'job_id': s['id'], 'disposition': 'unattempted'}) for s in specs]
    # IDs are derived from the registered specs rather than guessed from labels.
    restore_ids = {s['id'] for s in p.feasibility_specs() if s['operation'] == 'repeat'}
    repeats = [all_audits[r['run_id']] for r in result['owners'] if r['job_id'] in restore_ids and r['run_id'] in all_audits]
    result['restore_pair_matches'] = repeat_equal(repeats)
    result['selection_independently_qualified'] = selection_valid(
        [c['spec'] for c in registered], result['stages']['development'], selected)
    mandatory = receipt.get('stages', {}).get('prerequisites', {})
    result['reported_selected_profile_sha256'] = selected
    result['native_prerequisites_passed'] = bool(result['selection_independently_qualified']
        and receipt.get('status') == 'finished-bounded-attempt' and index and mandatory.get('mandatory_pass') is True
        and len(mandatory.get('attempted', [])) == 8 and result['restore_pair_matches']
        and not result['errors'] and all(r['disposition'] == 'audited-recording' for r in result['stages']['prerequisites']))
    result['status'] = ('native-prerequisites-passed' if result['native_prerequisites_passed'] else
        'infrastructure-or-evidence-stop' if result['errors'] or not index or receipt.get('status') != 'finished-bounded-attempt'
        else 'native-prerequisite-failure' if len(repeats) == 2 and not result['restore_pair_matches']
        else stop_status(result['stages']['development'], result['stages']['prerequisites'],
                         selection_ok=result['selection_independently_qualified']))
    result['historical_inventory_unchanged'] = p.hash_ledger(Path(registration['historical_output']), deadline) == registration['historical_inventory']
    if not result['historical_inventory_unchanged']:
        raise ValueError('Historical evidence changed')
    result['retained_inventory_before_readout'] = p.hash_ledger(root, deadline)
    # Small immutable inputs, receipts and logs only; payloads stay local.
    copied = []
    for path in sorted(root.rglob('*')):
        p.deadline_check(deadline)
        if not path.is_file() or path.suffix not in ('.json', '.log', '.svg') or path.stat().st_size > 2*p.MiB:
            continue
        rel = path.relative_to(root)
        destination = evidence/'owners'/rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError('Publication destination already exists')
        shutil.copyfile(path, destination)
        copied.append({'path': str(destination.relative_to(evidence)), 'bytes': destination.stat().st_size,
                       'sha256': p.file_hash(destination)})
    result['publication_inventory'] = copied
    result['completed_monotonic'] = time.monotonic()
    result['conservative_readout_seconds'] = result['completed_monotonic']-receipt['readout_started_monotonic']
    result['conservative_total_seconds'] = result['completed_monotonic']-receipt['phase_started_monotonic']
    result['readout_deadline_monotonic'] = deadline
    result['raw_bytes'] = sum(f.stat().st_size for f in root.rglob('*') if f.is_file())
    result['documentary_bytes'] = sum(f.stat().st_size for f in evidence.rglob('*') if f.is_file())
    payload = json.dumps(result, indent=2, sort_keys=True)+'\n'
    if result['raw_bytes']+result['documentary_bytes']+2*len(payload.encode()) > 8*p.GiB:
        raise ValueError('Aggregate byte budget exceeded')
    p.deadline_check(deadline)
    for path in (root/'readout-completion.json', evidence/'readout-completion.json'):
        with path.open('x') as stream:
            stream.write(payload)
    p.deadline_check(deadline)
    return result
