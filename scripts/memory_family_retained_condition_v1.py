"""Read retained staged condition evidence; replay remains an attestation."""
from __future__ import annotations

import copy

from palimpsest import artifacts, memory
from scripts import memory_condition_replay_admission_v1 as qualification
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_condition_seal_v4 as seal
from scripts import memory_family_oracle_admission_v4 as pair
from scripts import memory_family_producer_v4 as source


def read_retained_sealed_condition(evidence_root, registration, *, case_id,
                                   condition, condition_commit, deadline):
    """Validate retained bytes without raw/model replay or publication authority.

    The expected commit must be independently registered, not self-derived from
    the marker under inspection. No returned object retains live file custody.
    """
    registration = copy.deepcopy(registration)
    condition_commit = copy.deepcopy(condition_commit)
    with seal._ValidatingStack() as lifetime:
        contract, checks, control_bytes = seal._registration(
            evidence_root, registration, case_id, condition, deadline, lifetime)
        base = f'cases/{case_id}/conditions/{condition}'
        if pair._descriptor(condition_commit, 'Retained condition commit')['path'] != base + '/commit.json':
            raise ValueError('Retained condition commit is outside its canonical path')
        _, qualification_bytes, check = seal._bind(lifetime, evidence_root,
            contract['qualification'], compact.MiB, deadline)
        receipt = seal._canonical(qualification_bytes, qualification.RECEIPT_KEYS,
                                  'Retained qualification receipt')
        qualification._validate_receipt(receipt)
        checks.append(check)
        lifetime.enter_context(pair._staged_namespace(evidence_root, case_id))
        anchor = seal._Anchor(evidence_root, case_id, condition)
        lifetime.callback(anchor.close)
        source_fd, case_fd, check = lifetime.enter_context(
            source._source_directory(evidence_root, case_id))
        checks.append(check)
        source._retained_source_namespace(lifetime, source_fd, case_fd,
                                         contract['source_run_id'], None)
        source_bundle, source_conversion, _, source_checks = seal._load_source(
            evidence_root, contract, deadline, lifetime)
        checks.extend(source_checks)
        owner, check = seal._owner(evidence_root, contract, deadline, lifetime)
        checks.append(check)
        bundle, support = seal._bundle(anchor, lifetime, deadline,
                                        {'pair-admission.json', 'commit.json'})
        marker_bytes = source._read_file(anchor.condition_fd, 'commit.json',
            compact.MiB, lifetime=lifetime, deadline=deadline)
        compact._check_descriptor(condition_commit, base + '/commit.json', marker_bytes)
        marker = seal._canonical(marker_bytes, seal.MARKER_KEYS, 'Retained condition marker')
        _, raw_bytes, check = seal._bind(lifetime, evidence_root,
            contract['raw_audit'], compact.MiB, deadline)
        checks.append(check)
        if support['recording/raw-audit.json'] != raw_bytes or support['owner.json'] != owner:
            raise ValueError('Retained condition raw audit or owner differs')
        raw_receipt = artifacts._json(raw_bytes)
        read = compact.read_compact(bundle, raw_audit_receipt=raw_receipt)
        worker = support['worker-report.json']
        if source._descriptor('worker-report.json', worker) != next(
                row for row in raw_receipt['raw_inventory']['files']
                if row['path'] == 'worker-report.json'):
            raise ValueError('Retained worker report differs from raw-auditor attestation')
        reference = {'kind': 'shared-source', 'source_run_id': contract['source_run_id'],
            'source_receipt_sha256': source_conversion['sha256'], **contract['source']['snapshot']}
        reference_bytes = memory.canonical_bytes(reference)
        if (read['snapshot_reference'] != reference
                or support['snapshot-reference.json'] != reference_bytes):
            raise ValueError('Retained condition shared snapshot differs')
        support_inventory = sorted([
            source._descriptor('worker-report.json', worker),
            source._descriptor('owner.json', owner),
            source._descriptor('snapshot-reference.json', reference_bytes)], key=lambda d: d['path'])
        conversion = {'schema': 'memory-family-compact-conversion-v1',
            'protocol_sha256': compact.PROTOCOL_SHA256, 'case_id': case_id,
            'run_id': contract['run_id'], 'operation': 'condition', 'condition': condition,
            'raw_audit': copy.deepcopy(contract['raw_audit']),
            'source_identity': source.audit.canonical_source_identity(contract['owner_source_sha256']),
            'legacy_trace_digest': read['trace_digest'], 'compact_trace_digest': read['trace_digest'],
            'compact_manifest': source._descriptor('manifest.json', bundle['manifest.json']),
            'inventory': sorted([*[source._descriptor('recording/' + p, b) for p, b in bundle.items()],
                source._descriptor('recording/raw-audit.json', raw_bytes)], key=lambda d: d['path']),
            'support': support_inventory, 'registration': registration,
            'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
        conversion_bytes = memory.canonical_bytes(conversion)
        if support['recording/conversion.json'] != conversion_bytes:
            raise ValueError('Retained condition conversion inventory differs')
        conversion_descriptor = source._descriptor(base + '/recording/conversion.json', conversion_bytes)
        pair_result = pair.admit_staged_compact_pair(source_commit=contract['source']['commit'],
            evidence_root=evidence_root, case=contract['case'], source_bundle=source_bundle,
            condition_bundle=bundle, source_run_id=contract['source_run_id'],
            condition_run_id=contract['run_id'], condition=condition,
            source_conversion_receipt=source_conversion,
            condition_conversion_receipt=conversion_descriptor,
            history_bundles=contract['history_bundles'],
            owner_source_sha256=contract['owner_source_sha256'], deadline=deadline,
            prior_own_receipt=contract['prior_own_receipt'])
        pair_bytes = memory.canonical_bytes(pair_result)
        if support['pair-admission.json'] != pair_bytes:
            raise ValueError('Retained pair receipt differs from recomputed semantics')
        seal._validate_replay(marker['cell_replay'], contract, read)
        expected_marker = {'schema': 'memory-family-compact-condition-commit-v1',
            'protocol_sha256': compact.PROTOCOL_SHA256, 'extension_sha256': contract['extension_sha256'],
            'case_id': case_id, 'run_id': contract['run_id'], 'condition': condition,
            'source_run_id': contract['source_run_id'], 'conversion': conversion_descriptor,
            'snapshot_reference': source._descriptor(base + '/snapshot-reference.json', reference_bytes),
            'pair_admission': source._descriptor(base + '/pair-admission.json', pair_bytes),
            'qualification': copy.deepcopy(contract['qualification']),
            'cell_replay': marker['cell_replay'], 'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
        if marker_bytes != memory.canonical_bytes(expected_marker):
            raise ValueError('Retained condition marker differs from bound evidence')
        seal._bounds(bundle, raw_bytes, conversion_bytes,
            sum(d['size_bytes'] for d in support_inventory) + len(pair_bytes), control_bytes, len(marker_bytes))
        for check in checks:
            check()
        seal._require_qualification_pin(contract['qualification'])
        anchor.recheck()
        result = {'case_id': case_id, 'run_id': contract['run_id'],
            'condition': condition, 'marker': marker, 'read': read,
            'conversion': conversion, 'pair_admission': pair_result,
            'raw_replay_performed': False, 'model_replay_performed': False,
            'replay_evidence': 'retained-attestation',
            'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
    source.audit._deadline(deadline)
    return result
