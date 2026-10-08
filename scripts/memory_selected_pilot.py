"""Explicit admission and bounded publication for the approved selected pilot."""
import math
from pathlib import Path

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from scripts import memory_prerequisites_v2 as m, memory_restore_offline_readout as o

PREREQUISITE_REGISTRATION_SHA256 = '8567bc446b265c36a3063dc5d3fcb2cf354bcd2a3684ec4a068e6c98007f12f9'
PREREQUISITE_CLOSE_SHA256 = '6e33c0c5fd0ec6a407588e6d7f7240f79964706e5cdd638a351bbe5a0b433b76'
PREREQUISITE_INDEX_SHA256 = 'b9e571a8fff0d9c1bc0a2d10b47355ad9cff96fc0e056d5f994789a95748e3a3'


def check_file(path, digest, size=None, deadline=None):
    p.deadline_check(deadline)
    path = p.checked_path(path)
    if (not path.is_file() or (size is not None and path.stat().st_size != size)
            or p.file_hash(path) != digest):
        raise ValueError('Immutable input bytes differ: '+str(path))
    p.deadline_check(deadline)


def admit_prerequisites(path, repo, deadline=None):
    """Consume the pinned old close as bytes/metadata, never regrade old physics."""
    path, repo = p.checked_path(path), p.checked_path(repo)
    check_file(path, PREREQUISITE_REGISTRATION_SHA256, deadline=deadline)
    reg = p.read_json(path); m.validate_registration(reg)
    root, pub, control = (p.checked_path(reg[k]) for k in ('output','publication_root','control_root'))
    if reg['mode'] != 'prerequisites-v3' or path != pub/'registration.json':
        raise ValueError('Only the pinned original v3 prerequisite is admitted')
    close_path = root/'scientific-close.json'
    check_file(close_path, PREREQUISITE_CLOSE_SHA256, deadline=deadline)
    close, execution = p.read_json(close_path), p.read_json(root/'execution.json')
    check_file(root/'execution.json', close['driver_execution_sha256'], deadline=deadline)
    required = {'native_prerequisites_passed':True,'candidate_restore_pair_matches':True,
                'trace_equal':True,'immutable_inputs_and_raw_evidence_unchanged':True,
                'restore_pair_matches':False,'r2_complete':False,'held_out_used':False}
    if (close.get('schema') != 'memory-prerequisites-scientific-close-v3'
            or close.get('status') != 'native-prerequisites-passed'
            or any(close.get(k) is not v for k,v in required.items())
            or close.get('qualification_claims') != []
            or close.get('paired_pilot') != 'unattempted-by-scope'
            or close.get('registration_sha256') != PREREQUISITE_REGISTRATION_SHA256
            or close.get('state_contract') != d.STATE_CONTRACT
            or execution.get('status') != 'prerequisites-provisional-pass'
            or execution.get('native_prerequisites_passed') is not False
            or execution.get('unattempted')):
        raise ValueError('Pinned prerequisite authority or scope differs')
    candidate = close['candidate_comparison']; intervals = candidate['timer_duration_intervals']
    if (candidate.get('equal') is not True or candidate.get('contract_id') != d.STATE_CONTRACT
            or candidate.get('excluded_native_bytes_per_side') != 120 or len(intervals) != 15
            or any(type(a) is not int or type(b) is not int or b-a != 8 for a,b in intervals)
            or any(b > c for (_,b),(c,_) in zip(intervals,intervals[1:]))
            or candidate.get('differences') != [] or close['comparison'].get('equal') is not False):
        raise ValueError('Frozen candidate/legacy comparison differs')
    attempts = execution['attempted']; owners = close['owners']; cleanup = execution['cleanup']
    ids = [a['run_id'] for a in attempts]
    if (len(attempts) != 8 or len(set(ids)) != 8 or
            [a['job_id'] for a in attempts] != [s['id'] for s in reg['expected_specs']]
            or len(owners) != 8 or {r['run_id'] for r in owners} != set(ids)
            or len(cleanup) != 8 or {r['owner']['run_id'] for r in cleanup} != set(ids)
            or any(r.get('raw_audit_pass') is not True or r.get('matching_owner_exited') is not True
                   or r.get('disposition') != 'audited-recording' for r in owners)
            or any(not m.cell_pass(spec,a) for spec,a in zip(reg['expected_specs'][:6],attempts[:6]))
            or any(a.get('raw_audit_pass') is not True or a.get('invariants_preserved') is not True
                   or a.get('continuation_ticks') != 5 for a in attempts[-2:])):
        raise ValueError('Complete eight-cell prerequisite binding is required')
    by_run = {r['run_id']:r for r in owners}
    for item in cleanup:
        if (item['owner'] != by_run[item['owner']['run_id']]['owner']
                or item['status'] not in ('already-exited','pid-reused-do-not-touch')
                or not d.owner_exited(item['owner'])):
            raise ValueError('Original prerequisite owner exit proof differs')
    marker = p.read_json(control/'launched.json'); origin = marker['started_monotonic']
    readout = execution['readout_started_monotonic']
    end = min(origin+4900,readout+600)
    times = (origin,readout,close['closed_monotonic'],close['readout_deadline_monotonic'])
    if (any(type(x) not in (int,float) or not math.isfinite(x) for x in times)
            or execution['started_monotonic'] != origin
            or execution['owner_deadline_monotonic'] != origin+4300
            or execution['global_deadline_monotonic'] != origin+4900
            or close['readout_deadline_monotonic'] != end
            or not origin <= readout <= close['closed_monotonic'] <= end
            or marker['registration_sha256'] != PREREQUISITE_REGISTRATION_SHA256):
        raise ValueError('Original prerequisite clock differs')
    check_file(control/'launched.json', execution['launcher_marker_sha256'], deadline=deadline)
    for name in ('driver','auditor','comparator','launcher','shared_launcher',
                 'registration_preparer','campaign_launcher','shared_preparer'):
        check_file(reg[name+'_path'], reg[name+'_sha256'], deadline=deadline)
    check_file(reg['contract'], reg['contract_sha256'], deadline=deadline)
    check_file(Path(reg['repo'])/'scripts/memory_restore_diagnostic.py',
               reg['diagnostic_driver_sha256'],deadline=deadline)
    check_file(Path(reg['repo'])/'scripts/memory_decision_pilot.py',
               reg['source_identity']['pilot_driver_sha256'],deadline=deadline)
    inventory = execution['artifact_index']+[
        {'path':'execution.json','bytes':(root/'execution.json').stat().st_size,
         'sha256':close['driver_execution_sha256']},
        {'path':'scientific-close.json','bytes':close_path.stat().st_size,
         'sha256':PREREQUISITE_CLOSE_SHA256}]
    o.verify_inventory({'root':str(root),'files':inventory},deadline)
    for reference in reg['preserved_sets']: o.verify_inventory(reference,deadline)
    index_path = pub/'publication-index.json'
    check_file(index_path,PREREQUISITE_INDEX_SHA256,deadline=deadline)
    for row in p.read_json(index_path)['files']:
        source = p.checked_path(row['source'])
        if not any(source.is_relative_to(r) for r in (root,pub,control)):
            raise ValueError('Prerequisite byte index escapes its frozen roots')
        check_file(source,row['sha256'],row['bytes'],deadline)
    source = close['fresh_source']
    if (source != p.read_json(root/'fresh-source.json') or source['source_job_id'] != 'south-prefix'
            or source['run_id'] != attempts[4]['run_id'] or
            len(source['source_receipt_ids']) != 727 or len(set(source['source_receipt_ids'])) != 727
            or any(by_run[a['run_id']]['audit'].get('repeat_source_receipt_ids') != source['source_receipt_ids']
                   for a in attempts[-2:])):
        raise ValueError('Fresh prerequisite source binding differs')
    check_file(source['snapshot_path'],source['snapshot_sha256'],source['bytes'],deadline)
    current = p.source_identity(repo,reg['assets']); previous = reg['source_identity']
    if ({k:v for k,v in current.items() if k != 'pilot_driver_sha256'} !=
            {k:v for k,v in previous.items() if k != 'pilot_driver_sha256'}):
        raise ValueError('Scientific source/assets differ; only explicit pilot worker derivation is allowed')
    return {'registration_path':str(path),'registration_sha256':PREREQUISITE_REGISTRATION_SHA256,
            'close_path':str(close_path),'close_sha256':PREREQUISITE_CLOSE_SHA256,
            'index_path':str(index_path),'index_sha256':PREREQUISITE_INDEX_SHA256,
            'old_worker_sha256':previous['pilot_driver_sha256'],
            'new_worker_sha256':current['pilot_driver_sha256']}


def retain_report(root, report, storage):
    """Full audit stays bounded in its own file; all thirty summaries fit the close."""
    path = p.checked_path(root)/'inline-audits'/(report['run_id']+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    p.write_control(path,report,storage)
    compact = {k:v for k,v in report.items() if k not in
               ('final_memory','world_state','commitment_inputs','failed_worker_report')}
    return {**compact,'audit_path':str(path),'audit_sha256':p.file_hash(path)}
