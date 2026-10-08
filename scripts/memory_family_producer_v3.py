"""Validate a family-v3 producer contract; never allocate or launch owners."""
from __future__ import annotations

import copy
import hashlib
import math
import os
from pathlib import Path
import tempfile
import time
import uuid

from palimpsest import (
    artifacts, interventions, male_model, male_policy, memory, memory_decision,
    memory_decision_world as world, memory_experiment, memory_task, memory_world,
    profiles, records, replay, snapshots,
)
from palimpsest.memory_experiment import CONDITIONS
from scripts import memory_family_analysis_v3 as analysis
from scripts import memory_family_oracle_admission_v3 as admission
from scripts import memory_family_oracle_v3 as oracle
from scripts import memory_family_v3 as family
from scripts import memory_confirmatory_v3 as confirmatory
from scripts import memory_restore_diagnostic as diagnostic


MiB = 1024 * 1024
MAX_JSON = 4 * MiB
MAX_NAMESPACE = 16 * MiB
MAX_CLOSE = 32 * MiB
REGISTRATION_FIELDS = {
    'schema', 'mode', 'split', 'block', 'conditions', 'plan', 'protocol',
    'analysis_design',
    'source_identity', 'source_identity_sha256', 'histories',
    'namespace_inventory', 'roots', 'dependencies', 'resource_projection',
    'case_slots', 'authored_ids', 'retries', 'corrective_studies',
    'native_allocation', 'held_out_used', 'study_complete',
    'qualification_claims',
}
JOB_FIELDS = {
    'schema', 'scope', 'registration_path', 'registration_sha256', 'run_id',
    'output', 'case_id', 'case', 'operation', 'condition', 'source', 'history',
}
RESOURCE_PROJECTION = {
    'scope': 'projection-not-allocation',
    'source_owners': 144,
    'condition_owners': 1296,
    'total_owners': 1440,
    'source_recording_max_bytes': admission.SOURCE_RECORDING_MAX_BYTES,
    'condition_recording_max_bytes': admission.POST_RECORDING_MAX_BYTES,
    'snapshot_max_bytes': 16 * MiB,
    'log_stream_max_bytes': MiB,
    'control_max_bytes': MiB,
    'raw_bytes': 599_147_937_792,
    'snapshot_bytes': 24_159_191_040,
    'log_control_bytes': 4_529_848_320,
    'known_bytes': 627_836_977_152,
    'source_outer_seconds': 370,
    'condition_outer_seconds': 130,
    'cleanup_seconds_per_owner': 10,
    'outer_seconds': 221_760,
    'outer_plus_cleanup_seconds': 236_160,
    'excluded': ['reports', 'audits', 'prerequisites', 'close-headroom'],
}


def _deadline(deadline):
    if deadline is None:
        return
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError('Producer deadline must be finite')
    if time.monotonic() >= deadline:
        raise TimeoutError('Producer contract deadline exhausted')


def _fields(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError(f'{label} has missing or unknown fields')


def _digest(value, label):
    try:
        memory._digest(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'Invalid {label} SHA-256') from error
    return value


def _run_id(value):
    try:
        valid = type(value) is str and uuid.UUID(value).hex == value
    except (AttributeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Run ID must be canonical UUID hex')
    return value


def _file_sha(path, deadline=None):
    path = artifacts._safe_path(path)
    if not path.is_file():
        raise ValueError(f'Missing producer input: {path.name}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(MiB):
            _deadline(deadline)
            digest.update(block)
    return digest.hexdigest()


def _read_json(path, limit=MAX_JSON, deadline=None, *, canonical=False):
    _deadline(deadline)
    path = artifacts._safe_path(path)
    payload = artifacts._read(path, limit)
    value = artifacts._json(payload)
    try:
        encoded = memory.canonical_bytes(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'Invalid canonical JSON input: {path.name}') from error
    if canonical and payload != encoded:
        raise ValueError(f'JSON input is not canonical: {path.name}')
    return path, value, hashlib.sha256(payload).hexdigest()


def _history_descriptor(path, relation, deadline=None):
    path, bundle, digest = _read_json(path, admission.MAX_HISTORY_BYTES, deadline)
    if (type(bundle) is not dict
            or not {'version', 'e', 'u', 'history_sha256'}.issubset(bundle)
            or bundle['version'] != 1):
        raise ValueError('Unknown history bundle version')
    try:
        history = memory.validate_e(bundle['e'])
        fitted = memory.validate_u(bundle['u'])
        expected = memory.fit(history)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('History bundle identity/U is invalid') from error
    if (bundle['history_sha256'] != memory.sha256(history)
            or memory.canonical_bytes(fitted) != memory.canonical_bytes(expected)
            or fitted['payload']['rules'] != [
                {'trigger': 'cue_changed', 'relation': relation}]):
        raise ValueError('History bundle differs from its registered relation')
    return {'path': str(path), 'sha256': digest}, memory_experiment._ids(history)


def _overlaps(left, right):
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _dependency_descriptors(deadline=None):
    paths = {
        'producer': Path(__file__),
        'artifacts': Path(artifacts.__file__),
        'memory_core': Path(memory.__file__),
        'family_world': Path(world.__file__),
        'synthetic_history': Path(memory_experiment.__file__),
        'family_generator': Path(family.__file__),
        'family_plan_validator': Path(confirmatory.__file__),
        'family_analysis': Path(analysis.__file__),
        'raw_admission': Path(admission.__file__),
        'pure_oracle': Path(oracle.__file__),
        'owner_diagnostic': Path(diagnostic.__file__),
        'profiles': Path(profiles.__file__),
        'records': Path(records.__file__),
        'replay': Path(replay.__file__),
        'snapshots': Path(snapshots.__file__),
        'memory_decision': Path(memory_decision.__file__),
        'memory_task': Path(memory_task.__file__),
        'memory_world': Path(memory_world.__file__),
        'interventions': Path(interventions.__file__),
        'male_policy': Path(male_policy.__file__),
        'male_model': Path(male_model.__file__),
        'flynn_policy_binding': Path(admission.__file__).with_name(
            'verify_flynn_memory_transfer.py'),
        'manual_transfer_helpers': Path(admission.__file__).with_name(
            'verify_memory_transfer.py'),
    }
    return {name: {'path': str(artifacts._safe_path(path)),
                   'sha256': _file_sha(path, deadline)}
            for name, path in paths.items()}


def _case_ids(case):
    graph = world.public_graph(case)
    result = {
        case['family_id'], case['case_id'], case['cue_id'],
        case['common_goal_id'], case['decision_landmark_id'],
        *case['subjects_by_side'], *case['route_ids_by_side'],
        *case['landmarks'], *graph['landmark_ids'], *graph['acquisition_ids'],
    }
    for fact in case['facts']:
        result.update((fact['id'], fact['subject_id'],
                       fact['inspection_landmark_id']))
        result.update(row['cue_id'] for row in fact['associations'])
    for route in graph['routes']:
        result.update((route['route_id'], route['subject_id'], route['fact_id'],
                       route['inspection_landmark_id']))
        result.update(route['waypoint_ids'])
        result.update(route['retreat_ids'])
    for edge in graph['edges']:
        result.update((edge['id'], edge['from'], edge['to'], edge['subject_id']))
    for identifier in result:
        memory._id(identifier)
    return result


def _authored_ids(cases):
    result, families = set(), set()
    for case in cases:
        identifiers = _case_ids(case)
        family_id = case['family_id']
        expected = {family_id} if family_id in families else set()
        if result.intersection(identifiers) != expected:
            raise ValueError('Selected family block has an unintended authored ID collision')
        result.update(identifiers)
        families.add(family_id)
    return result


def _namespace(path, deadline=None):
    path, value, digest = _read_json(path, MAX_NAMESPACE, deadline)
    _fields(value, {'schema', 'historical_run_ids', 'historical_authored_ids'},
            'Namespace inventory')
    if value['schema'] != 'memory-family-namespace-inventory-v3':
        raise ValueError('Unknown namespace inventory')
    memory._list(value['historical_run_ids'], 100_000)
    memory._list(value['historical_authored_ids'], 100_000)
    run_ids = [_run_id(item) for item in value['historical_run_ids']]
    authored = []
    for item in value['historical_authored_ids']:
        memory._id(item)
        authored.append(item)
    if len(run_ids) != len(set(run_ids)) or len(authored) != len(set(authored)):
        raise ValueError('Namespace inventory contains duplicate identities')
    descriptor = {'path': str(path), 'sha256': digest,
                  'historical_run_ids': len(run_ids),
                  'historical_authored_ids': len(authored)}
    return descriptor, set(run_ids), set(authored)


def _plan(path, block, deadline=None):
    path, plan, digest = _read_json(path, MAX_JSON, deadline)
    if type(plan) is not dict or type(plan.get('prerequisites')) is not list:
        raise ValueError('Invalid family matrix plan')
    generated = family.build_slots('development', [block], plan['prerequisites'])
    if memory.canonical_bytes(plan) != memory.canonical_bytes(generated['plan']):
        raise ValueError('Matrix plan differs from the selected complete development block')
    return {'path': str(path), 'sha256': digest}, generated


def _roots(value, inputs):
    _fields(value, {'output', 'control', 'publication'}, 'Producer roots')
    roots = {name: artifacts._safe_path(path) for name, path in value.items()}
    if any(not path.is_absolute() for path in roots.values()):
        raise ValueError('Producer roots must be absolute')
    ordered = list(roots.values())
    if any(_overlaps(left, right) for index, left in enumerate(ordered)
           for right in ordered[index + 1:]):
        raise ValueError('Producer roots overlap')
    if any(_overlaps(root, source) for root in ordered for source in inputs):
        raise ValueError('Producer root overlaps a bound input')
    return {name: str(path) for name, path in roots.items()}


def _case_slots(cases, run_ids):
    if type(run_ids) is not list or len(run_ids) != 1440:
        raise ValueError('Exactly 1,440 caller-allocated run IDs are required')
    run_ids = [_run_id(value) for value in run_ids]
    if len(set(run_ids)) != len(run_ids):
        raise ValueError('Registered run IDs must be globally distinct')
    result = []
    cursor = 0
    for case in cases:
        source = run_ids[cursor]
        cursor += 1
        conditions = dict(zip(CONDITIONS, run_ids[cursor:cursor + len(CONDITIONS)]))
        cursor += len(CONDITIONS)
        result.append({'case_id': case['case_id'],
                       'case_sha256': case['case_sha256'],
                       'source_run_id': source,
                       'condition_run_ids': conditions})
    if cursor != len(run_ids):
        raise ValueError('Run-ID accounting differs from the complete matrix')
    return result


def build_registration(block, *, plan_path, protocol_path, source_identity,
                       history_bundles, namespace_inventory_path, output_root,
                       control_root, publication_root, run_ids):
    """Return one validated, non-executable development contract; never write."""
    if type(block) is not int or not 0 <= block < world.FAMILY_DESIGN['block_limit']:
        raise ValueError('Invalid family block')
    plan, generated = _plan(plan_path, block)
    protocol_path, protocol, protocol_sha256 = _read_json(
        protocol_path, canonical=True)
    if type(protocol) is not dict:
        raise ValueError('Protocol must be a JSON object')
    analysis.validate_protocol(protocol)
    analysis_design = analysis.build_design('development', block, protocol)
    if type(source_identity) is not dict:
        raise ValueError('Source identity must be a JSON object')
    try:
        memory._bounded(source_identity, MiB)
    except (TypeError, ValueError) as error:
        raise ValueError('Invalid bounded source identity') from error
    source_identity = copy.deepcopy(source_identity)
    source_identity_sha256 = memory.sha256(source_identity)
    if type(history_bundles) is not dict or set(history_bundles) != set(memory.RELATIONS):
        raise ValueError('Both exact relation history bundles are required')
    histories, history_ids = {}, set()
    for relation in memory.RELATIONS:
        descriptor, identifiers = _history_descriptor(history_bundles[relation], relation)
        if history_ids.intersection(identifiers):
            raise ValueError('History namespaces overlap')
        histories[relation] = descriptor
        history_ids.update(identifiers)
    namespace, historical_runs, historical_authored = _namespace(namespace_inventory_path)
    slots = _case_slots(generated['cases'], run_ids)
    registered_runs = {slot['source_run_id'] for slot in slots}
    registered_runs.update(run_id for slot in slots
                           for run_id in slot['condition_run_ids'].values())
    if registered_runs.intersection(historical_runs):
        raise ValueError('Registered run ID collides with retained history')
    authored = _authored_ids(generated['cases'])
    if authored.intersection(historical_authored | history_ids):
        raise ValueError('Selected authored ID collides with retained history')
    dependencies = _dependency_descriptors()
    inputs = [Path(plan['path']), protocol_path, Path(namespace['path']),
              *(Path(row['path']) for row in histories.values()),
              *(Path(row['path']) for row in dependencies.values())]
    roots = _roots({'output': output_root, 'control': control_root,
                    'publication': publication_root}, inputs)
    registration = {
        'schema': 'memory-family-producer-registration-v3',
        'mode': 'software-contract-only', 'split': 'development', 'block': block,
        'conditions': list(CONDITIONS), 'plan': plan,
        'protocol': {'path': str(protocol_path), 'sha256': protocol_sha256},
        'analysis_design': analysis_design,
        'source_identity': source_identity,
        'source_identity_sha256': source_identity_sha256,
        'histories': histories, 'namespace_inventory': namespace, 'roots': roots,
        'dependencies': dependencies,
        'resource_projection': copy.deepcopy(RESOURCE_PROJECTION),
        'case_slots': slots,
        'authored_ids': {'count': len(authored),
                         'sha256': memory.sha256(sorted(authored))},
        'retries': 0, 'corrective_studies': 0, 'native_allocation': False,
        'held_out_used': False, 'study_complete': False,
        'qualification_claims': [],
    }
    return validate_registration(registration)


def validate_registration(registration, deadline=None):
    """Validate all current inputs and return a defensive registration copy."""
    _deadline(deadline)
    _fields(registration, REGISTRATION_FIELDS, 'Producer registration')
    if (registration['schema'] != 'memory-family-producer-registration-v3'
            or registration['mode'] != 'software-contract-only'
            or registration['split'] != 'development'
            or registration['conditions'] != list(CONDITIONS)
            or registration['resource_projection'] != RESOURCE_PROJECTION
            or registration['retries'] != 0
            or registration['corrective_studies'] != 0
            or registration['native_allocation'] is not False
            or registration['held_out_used'] is not False
            or registration['study_complete'] is not False
            or registration['qualification_claims'] != []):
        raise ValueError('Unknown or executable producer registration')
    block = registration['block']
    if type(block) is not int or not 0 <= block < world.FAMILY_DESIGN['block_limit']:
        raise ValueError('Invalid registered family block')
    _fields(registration['plan'], {'path', 'sha256'}, 'Plan descriptor')
    plan, generated = _plan(registration['plan']['path'], block, deadline)
    if registration['plan'] != plan:
        raise ValueError('Registered plan binding differs')
    _fields(registration['protocol'], {'path', 'sha256'}, 'Protocol descriptor')
    protocol_path, protocol, protocol_sha256 = _read_json(
        registration['protocol']['path'], MAX_JSON, deadline, canonical=True)
    if type(protocol) is not dict or registration['protocol'] != {
            'path': str(protocol_path), 'sha256': protocol_sha256}:
        raise ValueError('Registered protocol binding differs')
    analysis.validate_protocol(protocol)
    analysis_design = analysis.build_design(registration['split'], block, protocol)
    if memory.canonical_bytes(registration['analysis_design']) != memory.canonical_bytes(analysis_design):
        raise ValueError('Registered analysis design differs')
    if type(registration['source_identity']) is not dict:
        raise ValueError('Registered source identity must be an object')
    try:
        memory._bounded(registration['source_identity'], MiB)
    except (TypeError, ValueError) as error:
        raise ValueError('Invalid registered source identity') from error
    if registration['source_identity_sha256'] != memory.sha256(registration['source_identity']):
        raise ValueError('Source identity digest differs')
    if type(registration['histories']) is not dict or set(registration['histories']) != set(memory.RELATIONS):
        raise ValueError('Registered history map differs')
    histories, history_ids = {}, set()
    for relation in memory.RELATIONS:
        descriptor = registration['histories'][relation]
        _fields(descriptor, {'path', 'sha256'}, 'History descriptor')
        expected, identifiers = _history_descriptor(
            descriptor['path'], relation, deadline)
        if descriptor != expected:
            raise ValueError('Registered history binding differs')
        if history_ids.intersection(identifiers):
            raise ValueError('History namespaces overlap')
        histories[relation] = descriptor
        history_ids.update(identifiers)
    _fields(registration['namespace_inventory'], {
        'path', 'sha256', 'historical_run_ids', 'historical_authored_ids'},
        'Namespace descriptor')
    namespace, historical_runs, historical_authored = _namespace(
        registration['namespace_inventory']['path'], deadline)
    if registration['namespace_inventory'] != namespace:
        raise ValueError('Registered namespace binding differs')
    dependencies = _dependency_descriptors(deadline)
    if registration['dependencies'] != dependencies:
        raise ValueError('Producer dependency binding differs')
    inputs = [Path(plan['path']), protocol_path, Path(namespace['path']),
              *(Path(row['path']) for row in histories.values()),
              *(Path(row['path']) for row in dependencies.values())]
    if registration['roots'] != _roots(registration['roots'], inputs):
        raise ValueError('Registered root binding differs')
    slots = registration['case_slots']
    if type(slots) is not list or len(slots) != len(generated['cases']):
        raise ValueError('Registration requires all 144 case slots')
    run_ids = []
    for slot, case in zip(slots, generated['cases']):
        _fields(slot, {'case_id', 'case_sha256', 'source_run_id',
                       'condition_run_ids'}, 'Case slot')
        if (slot['case_id'] != case['case_id']
                or slot['case_sha256'] != case['case_sha256']
                or type(slot['condition_run_ids']) is not dict
                or set(slot['condition_run_ids']) != set(CONDITIONS)):
            raise ValueError('Registered case slot differs from the family generator')
        run_ids.append(_run_id(slot['source_run_id']))
        run_ids.extend(_run_id(slot['condition_run_ids'][condition])
                       for condition in CONDITIONS)
    if len(run_ids) != 1440 or len(set(run_ids)) != len(run_ids):
        raise ValueError('Registration requires 1,440 distinct run IDs')
    if set(run_ids).intersection(historical_runs):
        raise ValueError('Registered run ID collides with retained history')
    authored = _authored_ids(generated['cases'])
    _fields(registration['authored_ids'], {'count', 'sha256'}, 'Authored ID digest')
    expected_authored = {'count': len(authored),
                         'sha256': memory.sha256(sorted(authored))}
    if registration['authored_ids'] != expected_authored:
        raise ValueError('Registered authored-ID inventory differs')
    if authored.intersection(historical_authored | history_ids):
        raise ValueError('Selected authored ID collides with retained history')
    try:
        memory._bounded(registration, MAX_JSON)
    except (TypeError, ValueError) as error:
        raise ValueError('Producer registration exceeds its bound') from error
    return copy.deepcopy(registration)


def _registration(path, deadline=None):
    path, registration, digest = _read_json(path, MAX_JSON, deadline)
    registration = validate_registration(registration, deadline)
    expected = Path(registration['roots']['publication']) / 'registration.json'
    if path != expected:
        raise ValueError('Producer registration path differs')
    return path, registration, digest


def _case_slot(registration, case_id, deadline=None):
    _, plan, _ = _read_json(registration['plan']['path'], deadline=deadline)
    cases = family.build_slots(registration['split'], [registration['block']],
                               plan['prerequisites'])['cases']
    for slot, case in zip(registration['case_slots'], cases):
        if slot['case_id'] == case_id:
            return slot, case
    raise ValueError('Case is not registered')


def _source(value, registration, slot, deadline=None):
    _fields(value, {'run_id', 'run_path', 'snapshot_path', 'snapshot_sha256'},
            'Source descriptor')
    run_id = _run_id(value['run_id'])
    run = artifacts._safe_path(value['run_path'])
    snapshot = artifacts._safe_path(value['snapshot_path'])
    expected_run = Path(registration['roots']['output']) / 'runs' / slot['source_run_id']
    if (not snapshot.is_file() or not 0 < snapshot.stat().st_size
            <= RESOURCE_PROJECTION['snapshot_max_bytes']):
        raise ValueError('Source snapshot is missing, empty or exceeds its bound')
    if (run_id != slot['source_run_id'] or run != expected_run
            or snapshot != run / 'snapshots/initial.snp'
            or _file_sha(snapshot, deadline) != _digest(
                value['snapshot_sha256'], 'source snapshot')):
        raise ValueError('Source descriptor differs from the registered source snapshot')
    return {'run_id': run_id, 'run_path': str(run), 'snapshot_path': str(snapshot),
            'snapshot_sha256': value['snapshot_sha256']}


def make_job(registration_path, case_id, condition, source=None):
    """Build a non-executable source or own descriptor from one registration."""
    path, registration, digest = _registration(registration_path)
    slot, case = _case_slot(registration, case_id)
    if condition is None:
        if source is not None:
            raise ValueError('Source descriptor cannot restore another source')
        operation, run_id, source, history = 'source', slot['source_run_id'], None, None
    elif condition == 'own':
        operation, run_id = 'condition', slot['condition_run_ids']['own']
        source = _source(source, registration, slot)
        history = copy.deepcopy(registration['histories'][case['regime']])
    else:
        raise ValueError('This zero-allocation contract materializes source/own only')
    job = {
        'schema': 'memory-family-producer-job-v3',
        'scope': 'non-executable-contract', 'registration_path': str(path),
        'registration_sha256': digest, 'run_id': run_id,
        'output': str(Path(registration['roots']['output']) / 'runs' / run_id),
        'case_id': case_id, 'case': case, 'operation': operation,
        'condition': condition, 'source': source, 'history': history,
    }
    return validate_job(job)


def validate_job(job, deadline=None):
    """Validate a descriptor; this function never grants native allocation."""
    _deadline(deadline)
    _fields(job, JOB_FIELDS, 'Producer job')
    if (job['schema'] != 'memory-family-producer-job-v3'
            or job['scope'] != 'non-executable-contract'):
        raise ValueError('Unknown or executable producer job')
    registration_path, registration, registration_sha256 = _registration(
        job['registration_path'], deadline)
    if job['registration_sha256'] != registration_sha256:
        raise ValueError('Job registration digest differs')
    slot, case = _case_slot(registration, job['case_id'], deadline)
    if job['case'] != case:
        raise ValueError('Job case differs from the family generator')
    if job['operation'] == 'source' and job['condition'] is None:
        expected_run, expected_source, expected_history = slot['source_run_id'], None, None
    elif job['operation'] == 'condition' and job['condition'] == 'own':
        expected_run = slot['condition_run_ids']['own']
        expected_source = _source(job['source'], registration, slot, deadline)
        expected_history = registration['histories'][case['regime']]
    else:
        raise ValueError('Job is not the registered source/own contract')
    expected_output = Path(registration['roots']['output']) / 'runs' / expected_run
    if (_run_id(job['run_id']) != expected_run
            or artifacts._safe_path(job['output']) != expected_output
            or job['source'] != expected_source or job['history'] != expected_history
            or job['registration_path'] != str(registration_path)):
        raise ValueError('Job identity or input binding differs')
    return copy.deepcopy(job)


def _admission_envelope(job):
    job = validate_job(job)
    _, registration, _ = _registration(job['registration_path'])
    return {
        'schema': admission.ENVELOPE_SCHEMA,
        'protocol_sha256': registration['protocol']['sha256'],
        'source_identity_sha256': registration['source_identity_sha256'],
        'case': copy.deepcopy(job['case']), 'operation': job['operation'],
        'condition': job['condition'],
        'source_snapshot_sha256': (None if job['source'] is None
                                   else job['source']['snapshot_sha256']),
    }


def _supervision(path, timeout, deadline=None):
    path, report, digest = _read_json(
        path, RESOURCE_PROJECTION['control_max_bytes'], deadline)
    _fields(report, {'schema_version', 'status', 'timeout_seconds', 'started_utc',
                     'output', 'returncode', 'elapsed_seconds'}, 'Supervisor report')
    elapsed = report['elapsed_seconds']
    if (type(report['schema_version']) is not int or report['schema_version'] != 1
            or report['status'] != 'completed'
            or type(report['returncode']) is not int or report['returncode'] != 0
            or type(report['timeout_seconds']) is not int
            or report['timeout_seconds'] != timeout
            or type(report['started_utc']) is not str or not report['started_utc']
            or artifacts._safe_path(report['output']) != path.parent
            or type(elapsed) not in (int, float) or not math.isfinite(elapsed)
            or not 0 <= elapsed <= timeout):
        raise ValueError('Supervisor did not prove a normal bounded owner exit')
    for name in ('stdout.log', 'stderr.log'):
        log = artifacts._safe_path(path.parent / name)
        if not log.is_file() or log.stat().st_size > MiB:
            raise ValueError('Owner log is missing or exceeds its bound')
    children = list(path.parent.iterdir())
    if ({child.name for child in children} != {
            'supervisor.json', 'stdout.log', 'stderr.log'}
            or any(child.is_symlink() or not child.is_file() for child in children)):
        raise ValueError('Supervisor directory contains unregistered evidence')
    return {'path': str(path), 'sha256': digest}


def _owner_cleanup(registration, registration_sha256, job, job_sha256, row,
                   process_namespace, deadline=None):
    _fields(row, {'run_id', 'owner_path', 'owner_sha256', 'status',
                  'supervisor_path', 'supervisor_sha256'}, 'Cleanup row')
    owner_path, owner, owner_sha256 = _read_json(
        row['owner_path'], RESOURCE_PROJECTION['control_max_bytes'], deadline)
    _fields(owner, {'schema', 'run_id', 'pid', 'starttime', 'pgid',
                    'process_namespace', 'registration_sha256', 'job_sha256'},
            'Owner marker')
    expected_owner_path = Path(job['output']) / 'owner.json'
    values = (owner['pid'], owner['starttime'], owner['pgid'])
    if (owner['schema'] != 'memory-family-owner-v3'
            or owner['run_id'] != job['run_id'] or row['run_id'] != job['run_id']
            or owner_path != expected_owner_path
            or row['owner_sha256'] != owner_sha256
            or owner['process_namespace'] != process_namespace
            or owner['registration_sha256'] != registration_sha256
            or owner['job_sha256'] != job_sha256
            or any(type(value) is not int or value <= 0 for value in values)
            or owner['pid'] != owner['pgid']
            or row['status'] not in ('already-exited', 'pid-reused-do-not-touch')):
        raise ValueError('Owner cleanup identity differs')
    timeout = (RESOURCE_PROJECTION['source_outer_seconds']
               if job['operation'] == 'source'
               else RESOURCE_PROJECTION['condition_outer_seconds'])
    expected_supervisor = (Path(registration['roots']['control']) / 'supervision' /
                           job['run_id'] / 'supervisor.json')
    if artifacts._safe_path(row['supervisor_path']) != expected_supervisor:
        raise ValueError('Cleanup supervisor path differs from its registered owner')
    supervisor = _supervision(row['supervisor_path'], timeout, deadline)
    if row['supervisor_sha256'] != supervisor['sha256']:
        raise ValueError('Cleanup supervisor digest differs')
    if not diagnostic.owner_exited(owner):
        raise ValueError('Matching native owner remains active')
    return {'owner': owner, 'owner_path': str(owner_path),
            'owner_sha256': owner_sha256, 'cleanup_status': row['status'],
            'supervisor': supervisor}


def _manifest_binding(job, registration_sha256, job_sha256, owner_sha256,
                      deadline=None):
    path, manifest, _ = _read_json(Path(job['output']) / 'recording/manifest.json',
                                   MAX_JSON, deadline)
    expected = {'schema': 'memory-family-producer-binding-v3',
                'registration_sha256': registration_sha256,
                'job_sha256': job_sha256, 'owner_sha256': owner_sha256}
    if type(manifest) is not dict or manifest.get('memory_family_producer_v3') != expected:
        raise ValueError('Raw manifest lacks the exact producer binding')
    return str(path)


def _file_ledger(paths, deadline=None):
    result = []
    for path in sorted({artifacts._safe_path(path) for path in paths}, key=str):
        _deadline(deadline)
        if not path.is_file():
            raise ValueError('Producer ledger input is missing')
        result.append({'path': str(path), 'bytes': path.stat().st_size,
                       'sha256': _file_sha(path, deadline)})
    return result


def _run_ledger(root, recording_max_bytes, deadline=None):
    root = artifacts._safe_path(root)
    if not root.is_dir():
        raise ValueError('Producer run ledger root is missing')
    allowed_directories = {
        Path('.'), Path('recording'), Path('recording/chunks'), Path('snapshots')}
    result, recording_bytes = [], 0
    for directory, directories, names in os.walk(root, followlinks=False):
        _deadline(deadline)
        if Path(directory).relative_to(root) not in allowed_directories:
            raise ValueError('Run contains an unregistered directory')
        directories.sort()
        children = [Path(directory) / name for name in directories + names]
        if any(path.is_symlink() for path in children):
            raise ValueError('Output ledger contains symlink')
        for name in sorted(names):
            path = Path(directory) / name
            if len(result) >= 100_000 or not path.is_file():
                raise ValueError('Output ledger exceeds regular-file inventory bound')
            relative, size = path.relative_to(root), path.stat().st_size
            if relative.parts[0] == 'recording':
                recording_bytes += size
                if recording_bytes > recording_max_bytes:
                    raise ValueError('Run recording exceeds its registered bound')
            elif relative == Path('snapshots/initial.snp'):
                if not 0 < size <= RESOURCE_PROJECTION['snapshot_max_bytes']:
                    raise ValueError('Run snapshot exceeds its registered bound')
            elif relative in (Path('worker-report.json'), Path('snapshots/index.json')):
                if size > admission.MAX_REPORT_BYTES:
                    raise ValueError('Run report evidence exceeds its bound')
            elif relative == Path('owner.json'):
                if size > RESOURCE_PROJECTION['control_max_bytes']:
                    raise ValueError('Run owner evidence exceeds its bound')
            else:
                raise ValueError('Run contains an unregistered file')
            result.append({'path': str(relative), 'bytes': size,
                           'sha256': _file_sha(path, deadline)})
    return result


def _ledger(registration_path, registration, source_job_path, source_job,
            post_job_path, post_job, cleanup_path, owner_rows, deadline=None):
    files = [registration_path, source_job_path, post_job_path, cleanup_path,
             registration['plan']['path'], registration['protocol']['path'],
             registration['namespace_inventory']['path'],
             *(row['path'] for row in registration['histories'].values()),
             *(row['path'] for row in registration['dependencies'].values())]
    for row in owner_rows:
        files.extend((row['owner_path'], row['supervisor']['path'],
                      Path(row['supervisor']['path']).parent / 'stdout.log',
                      Path(row['supervisor']['path']).parent / 'stderr.log'))
    return {
        'files': _file_ledger(files, deadline),
        'source_run': _run_ledger(
            source_job['output'], admission.SOURCE_RECORDING_MAX_BYTES, deadline),
        'post_run': _run_ledger(
            post_job['output'], admission.POST_RECORDING_MAX_BYTES, deadline),
    }


def _pair_controls(registration_path, source_job_path, post_job_path,
                   cleanup_path, deadline=None):
    registration_path, registration, registration_sha256 = _registration(
        registration_path, deadline)
    source_job_path, source_job, source_job_sha256 = _read_json(
        source_job_path, RESOURCE_PROJECTION['control_max_bytes'], deadline)
    post_job_path, post_job, post_job_sha256 = _read_json(
        post_job_path, RESOURCE_PROJECTION['control_max_bytes'], deadline)
    source_job = validate_job(source_job, deadline)
    post_job = validate_job(post_job, deadline)
    expected_job_root = Path(registration['roots']['control']) / 'jobs'
    if (source_job_path != expected_job_root / f"{source_job['run_id']}.json"
            or post_job_path != expected_job_root / f"{post_job['run_id']}.json"
            or any(job['registration_path'] != str(registration_path)
                   or job['registration_sha256'] != registration_sha256
                   for job in (source_job, post_job))
            or source_job['operation'] != 'source'
            or post_job['operation'] != 'condition'
            or post_job['condition'] != 'own'
            or source_job['case_id'] != post_job['case_id']
            or post_job['source']['run_id'] != source_job['run_id']):
        raise ValueError('Close requires one exact registered source/own pair')
    cleanup_path, cleanup, cleanup_sha256 = _read_json(
        cleanup_path, RESOURCE_PROJECTION['control_max_bytes'], deadline)
    expected_cleanup = (Path(registration['roots']['control']) / 'cleanup' /
                        f"{source_job['run_id']}-{post_job['run_id']}.json")
    _fields(cleanup, {'schema', 'registration_sha256', 'process_namespace', 'rows'},
            'Pair cleanup')
    current_namespace = os.readlink('/proc/self/ns/pid')
    if (cleanup_path != expected_cleanup
            or cleanup['schema'] != 'memory-family-pair-cleanup-v3'
            or cleanup['registration_sha256'] != registration_sha256
            or cleanup['process_namespace'] != current_namespace
            or type(cleanup['rows']) is not list or len(cleanup['rows']) != 2):
        raise ValueError('Pair cleanup envelope or PID namespace differs')
    jobs = ((source_job, source_job_sha256), (post_job, post_job_sha256))
    owners = [_owner_cleanup(registration, registration_sha256, job, job_sha256,
                              row, current_namespace, deadline)
              for (job, job_sha256), row in zip(jobs, cleanup['rows'])]
    control_paths = [source_job_path, post_job_path, cleanup_path]
    for owner in owners:
        control_paths.extend((Path(owner['owner_path']),
                              Path(owner['supervisor']['path'])))
    if sum(path.stat().st_size for path in control_paths) > (
            2 * RESOURCE_PROJECTION['control_max_bytes']):
        raise ValueError('Pair control evidence exceeds its aggregate bound')
    for job, job_sha256, owner in zip(
            (source_job, post_job), (source_job_sha256, post_job_sha256), owners):
        _manifest_binding(job, registration_sha256, job_sha256,
                          owner['owner_sha256'], deadline)
    return {
        'registration_path': registration_path, 'registration': registration,
        'registration_sha256': registration_sha256,
        'source_job_path': source_job_path, 'source_job': source_job,
        'source_job_sha256': source_job_sha256,
        'post_job_path': post_job_path, 'post_job': post_job,
        'post_job_sha256': post_job_sha256,
        'cleanup_path': cleanup_path, 'cleanup_sha256': cleanup_sha256,
        'owners': owners,
    }


def close_oracle_pair(registration_path, source_job_path, post_job_path,
                      cleanup_path, *, deadline=None):
    """Admit and hash-seal one retained contract pair without launching work."""
    _deadline(deadline)
    controls = _pair_controls(registration_path, source_job_path, post_job_path,
                              cleanup_path, deadline)
    registration = controls['registration']
    source_job, post_job = controls['source_job'], controls['post_job']
    target = (Path(registration['roots']['publication']) / 'pair-closes' /
              f"{source_job['run_id']}-{post_job['run_id']}.json")
    target = artifacts._safe_path(target)
    if target.exists() or target.is_symlink():
        raise FileExistsError('Oracle pair close already exists')
    if not target.parent.is_dir():
        raise ValueError('Pair-close directory must be prepared before readout')
    before = _ledger(
        controls['registration_path'], registration,
        controls['source_job_path'], source_job, controls['post_job_path'],
        post_job, controls['cleanup_path'], controls['owners'], deadline)
    oracle_result = admission.admit_oracle_pair(
        source_job['case'],
        {'run_id': source_job['run_id'], 'run_path': source_job['output']},
        {'run_id': post_job['run_id'], 'run_path': post_job['output'],
         'condition': 'own',
         'source_snapshot_sha256': post_job['source']['snapshot_sha256']},
        plan_path=registration['plan']['path'],
        plan_sha256=registration['plan']['sha256'],
        protocol_sha256=registration['protocol']['sha256'],
        source_identity_sha256=registration['source_identity_sha256'],
        history_bundle_path=post_job['history']['path'],
        history_bundle_sha256=post_job['history']['sha256'], deadline=deadline)
    after_controls = _pair_controls(
        registration_path, source_job_path, post_job_path, cleanup_path, deadline)
    after = _ledger(
        after_controls['registration_path'], after_controls['registration'],
        after_controls['source_job_path'], after_controls['source_job'],
        after_controls['post_job_path'], after_controls['post_job'],
        after_controls['cleanup_path'], after_controls['owners'], deadline)
    if (memory.canonical_bytes(after) != memory.canonical_bytes(before)
            or after_controls['registration_sha256'] != controls['registration_sha256']
            or after_controls['source_job_sha256'] != controls['source_job_sha256']
            or after_controls['post_job_sha256'] != controls['post_job_sha256']
            or after_controls['cleanup_sha256'] != controls['cleanup_sha256']):
        raise RuntimeError('Producer inputs changed during oracle pair close')
    close = {
        'schema': 'memory-family-oracle-pair-close-v3',
        'status': 'contract-pair-validated',
        'case_id': source_job['case_id'],
        'case_sha256': source_job['case']['case_sha256'],
        'registration_sha256': controls['registration_sha256'],
        'source_job_sha256': controls['source_job_sha256'],
        'post_job_sha256': controls['post_job_sha256'],
        'cleanup_sha256': controls['cleanup_sha256'],
        'process_namespace': os.readlink('/proc/self/ns/pid'),
        'owners': controls['owners'], 'input_ledger': before,
        'input_ledger_sha256': memory.sha256(before),
        'oracle': oracle_result, 'study_complete': False,
        'native_allocation': False, 'held_out_used': False,
        'qualification_claims': [],
        'scope': ('Synthetic contract/readout proof only; no native allocation, '
                  'matrix completion, scientific result or hostile-process immutability.'),
    }
    payload = memory.canonical_bytes(close)
    if len(payload) > MAX_CLOSE:
        raise ValueError('Oracle pair close exceeds its publication bound')
    _deadline(deadline)
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    temporary, linked = None, False
    try:
        with tempfile.NamedTemporaryFile(
                mode='wb', dir=target.parent, prefix=f'.{target.name}.',
                suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _deadline(deadline)
        os.link(temporary, target)
        linked = True
        _deadline(deadline)
        directory = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        _deadline(deadline)
    except BaseException:
        if linked:
            target.unlink(missing_ok=True)
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'path': str(target), 'sha256': payload_sha256,
            'close': copy.deepcopy(close)}
