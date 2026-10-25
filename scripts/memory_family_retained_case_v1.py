"""Read one staged nine-condition case under custody; never publish or qualify it."""
from __future__ import annotations

import copy
import math
from pathlib import Path, PurePosixPath

from palimpsest import artifacts, memory, snapshots
from scripts import memory_family_analysis_v3 as analysis
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_condition_seal_v4 as seal
from scripts import memory_family_oracle_admission_v4 as pair
from scripts import memory_family_producer_v4 as source
from scripts import memory_family_retained_condition_v1 as retained
from scripts.memory_decision_pilot import capped_score, condition_digest
from scripts.memory_family_replay_custody_v4 import HeldReplayFiles

CONDITIONS = tuple(compact.PROTOCOL['analysis_contract']['conditions'])


def _inventory(root, case_id, marker_descriptor, condition, lifetime, deadline):
    """Derive held leaves from expected markers, not a self-authenticating scan."""
    base = f'cases/{case_id}/' + ('source' if condition is None else f'conditions/{condition}')
    fields = compact.PROTOCOL['source_finalization']['marker_keys'] if condition is None else seal.MARKER_KEYS
    if pair._descriptor(marker_descriptor, 'Case owner marker')['path'] != base + '/commit.json':
        raise ValueError('Case owner marker is outside its canonical path')
    _, payload, _ = seal._bind(lifetime, root, marker_descriptor, compact.MiB,
                               deadline, case_id=case_id)
    marker = seal._canonical(payload, fields, 'Case owner marker')
    conversion_descriptor = marker['conversion']
    if pair._descriptor(conversion_descriptor, 'Case conversion')['path'] != base + '/recording/conversion.json':
        raise ValueError('Case conversion is outside its canonical path')
    _, payload, _ = seal._bind(lifetime, root, conversion_descriptor, compact.MiB,
                               deadline, case_id=case_id)
    conversion = seal._canonical(payload, compact.PROTOCOL['schemas']['conversion']['exact_keys'],
                                  'Case conversion')
    entries = [marker_descriptor, conversion_descriptor]
    for key, maximum in (('inventory', 46 if condition is None else 36), ('support', 3)):
        values = conversion[key]
        if type(values) is not list or not 1 <= len(values) <= maximum:
            raise ValueError('Case conversion inventory count exceeds its bound')
        for value in values:
            row = copy.deepcopy(pair._descriptor(value, 'Case inventory entry'))
            if row['path'].startswith('cases/'):
                if condition is not None or row['path'] != base + '/snapshots/initial.snp':
                    raise ValueError('Case inventory names another snapshot or owner')
            else:
                row['path'] = base + '/' + row['path']
            entries.append(row)
    if condition is not None:
        descriptor = pair._descriptor(marker['pair_admission'], 'Case pair admission')
        if descriptor['path'] != base + '/pair-admission.json':
            raise ValueError('Case pair receipt is outside its canonical path')
        entries.append(descriptor)
    if len(entries) > (49 if condition is None else 41):
        raise ValueError('Case owner file count exceeds its bound')
    ceiling = compact.PROTOCOL['recordings']['source' if condition is None else 'condition']['ceiling_bytes']
    if sum(row['size_bytes'] for row in entries if row['path'].startswith(base + '/recording/')) > ceiling:
        raise ValueError('Case owner recording exceeds its byte bound')
    return [{**row, 'path': '.pending/' + row['path'][len('cases/'):]} for row in entries]


def _cell(result, case, snapshot):
    """Project validated retained semantics without asserting fresh policy replay."""
    read = result['read']
    manifest = artifacts._json(read['legacy_manifest_bytes'])
    outcome = manifest.get('last_outcome')
    if type(outcome) is not dict:
        raise ValueError('Retained case contains a nonterminal condition')
    reason = outcome.get('reason')
    goal = reason == 'goal'
    cue_failure = (reason == 'runtime_failure' and outcome.get('type') == 'CueUnavailable'
                   and type(outcome.get('message')) is str
                   and outcome['message'].startswith('selected_waypoint_unavailable: '))
    if not (goal or reason in ('stalled', 'time_limit') or cue_failure):
        raise ValueError('Retained condition has an unscored infrastructure outcome')
    rows = read['rows']
    if goal:
        try:
            radius = snapshot['identity']['environment_profile']['values']['goal_radius']
        except (KeyError, TypeError) as error:
            raise ValueError('Retained goal lacks bound snapshot geometry') from error
        if (type(radius) not in (int, float) or not math.isfinite(radius) or radius <= 0
                or math.hypot(*(float(rows[-1]['next_pose'][i]) - case['goal_xy'][i]
                                for i in range(2))) >= radius):
            raise ValueError('Retained goal differs from bound snapshot geometry')
    path = sum(math.hypot(*(float(row['next_pose'][i]) - float(row['pose'][i])
                           for i in range(2))) for row in rows)
    if not math.isfinite(path):
        raise ValueError('Retained path length is not finite')
    cell = {'family_id': case['family_id'], 'case_id': case['case_id'],
        'kind': case['kind'], 'condition': result['condition'], 'run_id': result['run_id'],
        'goal': goal, 'continuation_ticks': len(rows), 'path_length': path,
        'outcome': outcome, 'trace_digest': read['trace_digest'],
        'invariant': condition_digest(snapshot)}
    cell['capped_ticks'] = capped_score(cell)
    return cell


def read_retained_staged_case(evidence_root, registrations, *, case_slot,
                              condition_commits, deadline):
    """Require independent expected slots and commits; returned data has no custody.

    The slot comes from the registered v3 case table. Caller-supplied cells or
    execution-order assertions are not accepted. The real qualification gate is
    still closed, and this reader never grants publication or study authority.
    """
    source.audit._public_deadline(deadline)
    registrations, slot, commits = copy.deepcopy((registrations, case_slot, condition_commits))
    pair._fields(slot, {'case_id', 'case_sha256', 'source_run_id', 'condition_run_ids'}, 'Case slot')
    for mapping in (registrations, commits, slot['condition_run_ids']):
        pair._fields(mapping, set(CONDITIONS), 'Nine-condition case mapping')
    case_id = slot['case_id']
    memory._id(case_id)
    compact._digest(slot['case_sha256'])
    run_ids = [pair._run_id(value) for value in [slot['source_run_id'], *slot['condition_run_ids'].values()]]
    if len(set(run_ids)) != 10:
        raise ValueError('Case source and condition run IDs must be distinct')
    root = artifacts._safe_path(evidence_root)
    with seal._ValidatingStack() as lifetime:
        # Admit every qualification before any staged source or condition access.
        for condition in CONDITIONS:
            descriptor = pair._descriptor(registrations[condition], 'Case terminal export')
            if descriptor['path'].startswith(('cases/', '.pending/')):
                raise ValueError('Case terminal exports must be external')
            _, payload, _ = seal._bind(lifetime, root, descriptor, compact.MiB, deadline)
            contract = seal._canonical(payload, seal.REGISTRATION_KEYS, 'Case terminal export')
            seal._require_qualification_pin(contract['qualification'])

        contracts, checks = {}, []
        for condition in CONDITIONS:
            contract, bound_checks, _ = seal._registration(
                root, registrations[condition], case_id, condition, deadline, lifetime)
            if (contract['case']['case_sha256'] != slot['case_sha256']
                    or contract['case']['block'] != compact.PROTOCOL['analysis_contract']['block']
                    or contract['source_run_id'] != slot['source_run_id']
                    or contract['run_id'] != slot['condition_run_ids'][condition]):
                raise ValueError('Retained condition differs from its registered case slot')
            if contracts and any(contract[key] != contracts['own'][key]
                    for key in ('case', 'source', 'owner_source_sha256', 'history_bundles')):
                raise ValueError('Retained conditions do not share one source, case and histories')
            order = analysis.condition_order(contract['case']['row'])
            if order.index('own') > order.index('oracle'):
                raise ValueError('Registered order conflicts with the prior-own dependency')
            _, payload, check = seal._bind(lifetime, root, contract['qualification'], compact.MiB, deadline)
            retained.qualification._validate_receipt(seal._canonical(
                payload, retained.qualification.RECEIPT_KEYS, 'Case qualification'))
            contracts[condition] = contract
            checks.extend([*bound_checks, check])
        common, case = contracts['own'], contracts['own']['case']
        own_pair = f'cases/{case_id}/conditions/own/pair-admission.json'
        if contracts['oracle']['prior_own_receipt']['path'] != own_pair:
            raise ValueError('Oracle prior-own receipt is outside this case')

        # Source inputs and behavior closure stay held across all nine readers.
        values = source._inputs(root, common['source']['registration'], case_id, deadline, lifetime)
        source_contract, source_case, run_id, _, _, snapshot_fd, source_checks, _ = values
        if (source_case != case or run_id != slot['source_run_id']
                or source_contract['snapshot'] != common['source']['snapshot']
                or source_contract['owner_source_sha256'] != common['owner_source_sha256']):
            raise ValueError('Retained source differs from the registered case')
        checks.extend(source_checks)
        for descriptor in compact.PROTOCOL['behavior_sources']:
            checks.append(seal._bind(lifetime, compact.ROOT,
                {key: descriptor[key] for key in ('path', 'size_bytes', 'sha256')},
                2 * compact.MiB, deadline)[2])
        protocol_descriptor = {'path': compact.PROTOCOL_PATH.relative_to(compact.ROOT).as_posix(),
            'sha256': compact.PROTOCOL_SHA256, 'size_bytes': len(memory.canonical_bytes(compact.PROTOCOL))}
        checks.append(seal._bind(lifetime, compact.ROOT, protocol_descriptor, compact.MiB, deadline)[2])

        entries = _inventory(root, case_id, common['source']['commit'], None, lifetime, deadline)
        for condition in CONDITIONS:
            entries.extend(_inventory(root, case_id, commits[condition], condition, lifetime, deadline))
        paths = [entry['path'] for entry in entries]
        directories = {parent.as_posix() for path in paths for parent in PurePosixPath(path).parents
                       if parent.as_posix().startswith(f'.pending/{case_id}')}
        total_bytes = sum(entry['size_bytes'] for entry in entries)
        if (len(paths) != len(set(paths)) or len(paths) > 418 or len(directories) != 33
                or total_bytes > (32 + 16 + 1 + 9 * (25 + 1)) * compact.MiB):
            raise ValueError('Retained case inventory exceeds its exact namespace or byte bounds')
        held = lifetime.enter_context(HeldReplayFiles(root,
            sorted(entries, key=lambda row: row['path']), deadline,
            exact_subtrees=(f'.pending/{case_id}',)))
        lifetime.enter_context(pair._staged_namespace(root, case_id))
        source.read_retained_sealed_source(root, common['source']['registration'], case_id=case_id,
            source_commit=common['source']['commit'], deadline=deadline)
        snapshot = snapshots.read_snapshot(Path(f'/proc/self/fd/{snapshot_fd}'))
        cells = {}
        for condition in order:
            result = retained.read_retained_sealed_condition(root, registrations[condition],
                case_id=case_id, condition=condition, condition_commit=commits[condition], deadline=deadline)
            cells[condition] = _cell(result, case, snapshot)
            del result
            held.recheck()
        equality = ('trace_digest', 'goal', 'continuation_ticks', 'path_length', 'outcome')
        references = CONDITIONS if case['kind'] == 'no-event' else ('sham',)
        if any(any(cells[condition][key] != cells['own'][key] for key in equality)
               for condition in references):
            raise ValueError('Retained own/sham or no-event equality differs')
        for check in checks:
            check()
        for contract in contracts.values():
            seal._require_qualification_pin(contract['qualification'])
        result = {'schema': 'memory-family-retained-case-v1', 'protocol_sha256': compact.PROTOCOL_SHA256,
            'case_id': case_id, 'source_run_id': slot['source_run_id'],
            'condition_run_ids': slot['condition_run_ids'], 'snapshot': common['source']['snapshot'],
            'source_commit': common['source']['commit'], 'condition_commits': commits,
            'condition_order': list(order), 'execution_order_verified': False,
            'retained_cells': [cells[condition] for condition in CONDITIONS],
            'file_count': len(entries), 'directory_count': len(directories), 'total_bytes': total_bytes,
            'raw_replay_performed': False, 'model_replay_performed': False,
            'replay_evidence': 'retained-attestation', 'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
    source.audit._deadline(deadline)
    return result
