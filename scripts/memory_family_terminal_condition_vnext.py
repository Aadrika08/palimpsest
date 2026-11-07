"""Conditional nine-way history mapping and fresh terminal replay, Task5a only.

Supplied history/source bodies are premises. This value-only proof neither
acquires nor registers them, grants actual authority, nor compares a family.
"""
import copy

from palimpsest import memory, memory_experiment
from palimpsest import memory_transition_vnext as transition
from scripts import memory_family_oracle_v3 as oracle
from scripts import memory_family_terminal_audit_vnext as audit


def prove_pair_vnext(source: dict, condition: dict, *, context: dict,
        terminal_proof: dict, deadline: float) -> dict:
    """Check E-only refits and exact configured bodies, then rederive all3a."""
    audit._deadline(deadline)
    c = transition.validate_context_vnext(context)
    audit._fields(source, ('application', 'events', 'rows', 'histories'))
    audit._fields(source['application'], oracle.APPLICATION_FIELDS)
    audit._fields(source['histories'], ('own', 'swapped'))
    audit._fields(condition, audit._RAW_KEYS)
    audit._fields(condition['descriptors'], audit._DESCRIPTORS)
    for value in (source, condition):
        audit._require(type(value['events']) is list and all(type(e) is dict for e in value['events'])
            and type(value['rows']) is list, 'Invalid decoded pair evidence')
    audit._fields(terminal_proof, audit.PROOF_KEYS)
    audit._require(terminal_proof['schema'] == 'memory-terminal-proof-vnext-v1', 'Invalid terminal proof schema')
    supplied_proof = memory.canonical_bytes(terminal_proof)
    histories = source['histories']
    for item in histories.values():
        audit._fields(item, ('descriptor', 'bundle'))
        bundle = item['bundle']
        audit._fields(bundle, ('e', 'u', 'history_sha256'))
        e, u = memory.validate_e(bundle['e']), memory.validate_u(bundle['u'])
        audit._same(bundle['history_sha256'], memory.sha256(e))
        audit._same(u, memory.fit(e))
        payload = memory.canonical_bytes(bundle)
        audit._descriptor(item['descriptor'], payload, 16 * 1024**2)
        audit._require(item['descriptor']['size_bytes'] > 0, 'Empty history bundle')
    audit._require(histories['own']['descriptor']['path'] != histories['swapped']['descriptor']['path'],
        'History descriptor paths alias')
    audit._require(not (memory_experiment._ids(histories['own']['bundle']['e'])
        & memory_experiment._ids(histories['swapped']['bundle']['e'])), 'History IDs overlap')
    audit._deadline(deadline)
    _, configured = oracle._single(condition['events'], 'memory_selector_configured', 'condition')
    q = c['condition']
    u, resource, provenance = memory.artifact(method='empty-v1'), None, memory_experiment.PROTOCOL_SHA256
    if q in ('own', 'sham', 'swapped'):
        history = histories['swapped' if q == 'swapped' else 'own']
        u, provenance = history['bundle']['u'], history['descriptor']['sha256']
    elif q == 'hand-authored':
        u = memory.artifact('local_cue')
    elif q == 'retrieval':
        resource = histories['own']['bundle']['e']
        provenance = histories['own']['descriptor']['sha256']
    elif q == 'oracle':
        resource, provenance = [], transition.pending_provenance_vnext(c)
    expected = {'version': 1, 'condition': q, 'limit': 1, 'resource': resource,
        'resource_sha256': memory.sha256(resource), 'provenance_sha256': provenance}
    audit._require(memory.canonical_bytes(configured.get('selector')) == memory.canonical_bytes(expected)
        and memory.canonical_bytes(configured.get('u')) == memory.canonical_bytes(u),
        'Registered condition selector/U mapping differs')
    fresh = audit.prove_terminal_vnext(condition, context=c, source_application=source['application'],
        source_events=source['events'], source_rows=source['rows'], deadline=deadline)
    audit._require(memory.canonical_bytes(fresh) == supplied_proof, 'Fresh complete terminal proof differs')
    endpoint = {name: fresh['row_count' if name == 'continuation_ticks' else name] for name in
        ('terminal_sensor_tick', 'goal', 'continuation_ticks', 'capped_ticks', 'path_length', 'outcome',
         'trace_digest', 'invariant')}
    result = {'schema': 'memory-terminal-pair-pure-vnext-v1', 'context_sha256': memory.sha256(c),
        'terminal_proof_sha256': memory.sha256(fresh),
        'history_bundles': {role: histories[role]['descriptor'] for role in ('own', 'swapped')},
        'endpoint': endpoint}
    memory._bounded(result, 1024**2)
    audit._deadline(deadline)
    return copy.deepcopy(result)
