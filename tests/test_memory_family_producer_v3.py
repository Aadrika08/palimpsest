"""Zero-allocation family-v3 producer contract checks; no native owners run."""
import copy
import hashlib
import json
from pathlib import Path
import uuid
from unittest.mock import patch

import pytest

from palimpsest import artifacts, memory, memory_experiment
from palimpsest.memory_experiment import CONDITIONS
from scripts import memory_family_producer_v3 as producer
from scripts.memory_family_v3 import build_slots
from test_memory_family_oracle_admission_v3 import _pair, _tree_hashes


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(memory.canonical_bytes(value))
    return path


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _case_offset(case_id, plan):
    cases = [case for family in plan['families']
             for case in family['cases'].values()]
    return cases.index(case_id) * (1 + len(CONDITIONS))


def _contract_inputs(tmp_path, *, pair=None):
    inputs = tmp_path / 'inputs'
    prerequisites = [{'id': 'fixture-prefix', 'kind': 'prefix'}]
    slots = build_slots('development', [0], prerequisites)
    plan_path = _write(inputs / 'plan.json', slots['plan'])
    protocol_path = _write(inputs / 'protocol.json', {
        'schema': 'memory-family-native-protocol-v3',
        'scope': 'synthetic-contract-only',
    })
    source_identity = {'schema': 'source-identity-v1', 'commit': 'fixture'}
    histories = {}
    if pair is None:
        for index, relation in enumerate(memory.RELATIONS):
            history = memory_experiment.make_history(200 + 100 * index, relation)
            value = {'version': 1,
                     'acquisition': 'recorded_declared_sensor_history',
                     'e': history, 'u': memory.fit(history),
                     'history_sha256': memory.sha256(history)}
            histories[relation] = str(_write(inputs / f'{relation}.json', value))
    else:
        payload = Path(pair['history_bundle_path']).read_bytes()
        for relation in memory.RELATIONS:
            path = inputs / f'{relation}.json'
            if relation == pair['case']['regime']:
                path.write_bytes(payload)
            else:
                history = memory_experiment.make_history(400, relation)
                _write(path, {'version': 1, 'e': history, 'u': memory.fit(history),
                              'history_sha256': memory.sha256(history)})
            histories[relation] = str(path)
    inventory_path = _write(inputs / 'namespace.json', {
        'schema': 'memory-family-namespace-inventory-v3',
        'historical_run_ids': [], 'historical_authored_ids': [],
    })
    run_ids = [uuid.UUID(int=1000 + index).hex for index in range(1440)]
    if pair is not None:
        offset = _case_offset(pair['case']['case_id'], slots['plan'])
        run_ids[offset] = pair['source']['run_id']
        run_ids[offset + 1 + list(CONDITIONS).index('own')] = pair['post']['run_id']
    roots = {name: tmp_path / name for name in ('output', 'control', 'publication')}
    return {
        'slots': slots, 'plan_path': plan_path, 'protocol_path': protocol_path,
        'source_identity': source_identity, 'histories': histories,
        'inventory_path': inventory_path, 'run_ids': run_ids, 'roots': roots,
    }


def _build(values):
    roots = values['roots']
    return producer.build_registration(
        0, plan_path=values['plan_path'], protocol_path=values['protocol_path'],
        source_identity=values['source_identity'],
        history_bundles=values['histories'],
        namespace_inventory_path=values['inventory_path'],
        output_root=roots['output'], control_root=roots['control'],
        publication_root=roots['publication'], run_ids=values['run_ids'])


def test_registration_freezes_one_complete_block_without_writing(tmp_path):
    values = _contract_inputs(tmp_path)
    registration = _build(values)

    assert set(registration) == {
        'schema', 'mode', 'split', 'block', 'conditions', 'plan', 'protocol',
        'source_identity', 'source_identity_sha256', 'histories',
        'namespace_inventory', 'roots', 'dependencies', 'resource_projection',
        'case_slots', 'authored_ids', 'retries', 'corrective_studies',
        'native_allocation', 'held_out_used', 'study_complete',
        'qualification_claims',
    }
    assert registration['schema'] == 'memory-family-producer-registration-v3'
    assert registration['mode'] == 'software-contract-only'
    assert registration['split'] == 'development' and registration['block'] == 0
    assert registration['conditions'] == list(CONDITIONS)
    assert len(registration['case_slots']) == 144
    assert len({slot['source_run_id'] for slot in registration['case_slots']}) == 144
    condition_ids = [run_id for slot in registration['case_slots']
                     for run_id in slot['condition_run_ids'].values()]
    assert len(condition_ids) == len(set(condition_ids)) == 1296
    assert len(set(condition_ids) |
               {slot['source_run_id'] for slot in registration['case_slots']}) == 1440
    assert registration['resource_projection'] == producer.RESOURCE_PROJECTION
    assert registration['native_allocation'] is False
    assert registration['held_out_used'] is False
    assert registration['study_complete'] is False
    assert registration['qualification_claims'] == []
    assert registration['retries'] == registration['corrective_studies'] == 0
    assert registration['authored_ids']['count'] > 144
    memory._digest(registration['authored_ids']['sha256'])
    assert set(registration['dependencies']) == {
        'producer', 'family_generator', 'raw_admission', 'pure_oracle',
        'owner_diagnostic'}
    assert producer.validate_registration(registration) == registration
    assert not any(path.exists() for path in values['roots'].values())


@pytest.mark.parametrize('defect', [
    'duplicate-run', 'historical-run', 'case', 'resource', 'input-byte',
    'overlap-root', 'namespace-shape', 'source-identity', 'history-map',
    'protocol-format', 'dependency', 'nested-shape',
])
def test_registration_rejects_identity_input_and_resource_tampering(tmp_path, defect):
    values = _contract_inputs(tmp_path)
    registration = _build(values)
    changed = copy.deepcopy(registration)
    if defect == 'duplicate-run':
        changed['case_slots'][1]['source_run_id'] = changed['case_slots'][0]['source_run_id']
    elif defect == 'historical-run':
        inventory = artifacts._json(Path(values['inventory_path']).read_bytes())
        inventory['historical_run_ids'] = [changed['case_slots'][0]['source_run_id']]
        _write(values['inventory_path'], inventory)
        changed['namespace_inventory']['sha256'] = _sha(values['inventory_path'])
    elif defect == 'case':
        changed['case_slots'][0]['case_sha256'] = 'f' * 64
    elif defect == 'resource':
        changed['resource_projection']['known_bytes'] -= 1
    elif defect == 'input-byte':
        Path(values['protocol_path']).write_bytes(b'{}')
    elif defect == 'overlap-root':
        changed['roots']['control'] = changed['roots']['output'] + '/child'
    elif defect == 'source-identity':
        changed['source_identity'] = 'not-an-object'
        changed['source_identity_sha256'] = memory.sha256(changed['source_identity'])
    elif defect == 'history-map':
        changed['histories'] = {
            memory.RELATIONS[0]: changed['histories'][memory.RELATIONS[1]],
            memory.RELATIONS[1]: changed['histories'][memory.RELATIONS[0]],
        }
    elif defect == 'protocol-format':
        protocol = artifacts._json(Path(values['protocol_path']).read_bytes())
        Path(values['protocol_path']).write_text(
            json.dumps(protocol, indent=2, allow_nan=False) + '\n')
        changed['protocol']['sha256'] = _sha(values['protocol_path'])
    elif defect == 'dependency':
        changed['dependencies']['owner_diagnostic']['sha256'] = 'f' * 64
    elif defect == 'nested-shape':
        changed['plan'] = []
    else:
        _write(values['inventory_path'], {'schema': 'wrong',
            'historical_run_ids': [], 'historical_authored_ids': []})
        changed['namespace_inventory']['sha256'] = _sha(values['inventory_path'])
    with pytest.raises(ValueError):
        producer.validate_registration(changed)
    assert not any(path.exists() for path in values['roots'].values())


def test_registration_rejects_history_namespace_reuse(tmp_path):
    values = _contract_inputs(tmp_path)
    for relation in memory.RELATIONS:
        history = memory_experiment.make_history(777, relation)
        _write(values['histories'][relation], {
            'version': 1, 'e': history, 'u': memory.fit(history),
            'history_sha256': memory.sha256(history),
        })
    with pytest.raises(ValueError, match='History namespaces overlap'):
        _build(values)

    values = _contract_inputs(tmp_path / 'authored')
    path = Path(values['histories'][memory.RELATIONS[0]])
    bundle = artifacts._json(path.read_bytes())
    authored_id = values['slots']['cases'][0]['case_id']
    check = bundle['e']['episodes'][0]['checks'][0]
    check['subject_id'] = authored_id
    check['before']['subject_id'] = authored_id
    check['after']['subject_id'] = authored_id
    bundle['history_sha256'] = memory.sha256(bundle['e'])
    bundle['u'] = memory.fit(bundle['e'])
    _write(path, bundle)
    with pytest.raises(ValueError, match='authored ID collides'):
        _build(values)


def _registration_file(values, registration):
    path = values['roots']['publication'] / 'registration.json'
    return _write(path, registration)


def test_source_and_own_descriptors_are_exact_and_non_executable(tmp_path):
    values = _contract_inputs(tmp_path)
    registration = _build(values)
    registration_path = _registration_file(values, registration)
    slot = registration['case_slots'][0]
    source_job = producer.make_job(registration_path, slot['case_id'], None)
    snapshot_path = (values['roots']['output'] / 'runs' /
                     slot['source_run_id'] / 'snapshots/initial.snp')
    snapshot_path.parent.mkdir(parents=True)
    snapshot_path.write_bytes(b'snapshot')
    source = {'run_id': slot['source_run_id'],
              'run_path': str(snapshot_path.parents[1]),
              'snapshot_path': str(snapshot_path),
              'snapshot_sha256': _sha(snapshot_path)}
    post_job = producer.make_job(registration_path, slot['case_id'], 'own', source)

    assert source_job['scope'] == post_job['scope'] == 'non-executable-contract'
    assert source_job['operation'] == 'source' and source_job['condition'] is None
    assert source_job['source'] is None and source_job['history'] is None
    assert post_job['operation'] == 'condition' and post_job['condition'] == 'own'
    assert post_job['source'] == source
    assert post_job['history'] == registration['histories'][post_job['case']['regime']]
    assert producer.validate_job(source_job) == source_job
    assert producer.validate_job(post_job) == post_job
    assert producer._admission_envelope(source_job) == {
        'schema': 'memory-family-oracle-admission-v3',
        'protocol_sha256': registration['protocol']['sha256'],
        'source_identity_sha256': registration['source_identity_sha256'],
        'case': source_job['case'], 'operation': 'source', 'condition': None,
        'source_snapshot_sha256': None,
    }
    assert producer._admission_envelope(post_job)['source_snapshot_sha256'] == _sha(snapshot_path)

    for defect in ('condition', 'source', 'snapshot', 'scope', 'registration'):
        changed = copy.deepcopy(post_job)
        if defect == 'condition':
            changed['condition'] = 'swapped'
        elif defect == 'source':
            changed['source']['run_id'] = uuid.uuid4().hex
        elif defect == 'snapshot':
            changed['source']['snapshot_sha256'] = 'f' * 64
        elif defect == 'scope':
            changed['scope'] = 'native-allocation'
        else:
            changed['registration_sha256'] = 'f' * 64
        with pytest.raises(ValueError):
            producer.validate_job(changed)

    with snapshot_path.open('wb') as stream:
        stream.truncate(producer.RESOURCE_PROJECTION['snapshot_max_bytes'])
    bounded = {**source, 'snapshot_sha256': _sha(snapshot_path)}
    assert producer.make_job(
        registration_path, slot['case_id'], 'own', bounded)['source'] == bounded
    with snapshot_path.open('ab') as stream:
        stream.write(b'x')
    oversized = {**bounded, 'snapshot_sha256': _sha(snapshot_path)}
    with pytest.raises(ValueError):
        producer.make_job(registration_path, slot['case_id'], 'own', oversized)


def _patch_manifest(run, binding):
    path = Path(run) / 'recording/manifest.json'
    value = artifacts._json(path.read_bytes())
    value['memory_family_producer_v3'] = binding
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _supervision(values, job, timeout):
    root = values['roots']['control'] / 'supervision' / job['run_id']
    root.mkdir(parents=True)
    (root / 'stdout.log').write_bytes(b'')
    (root / 'stderr.log').write_bytes(b'')
    report = {
        'schema_version': 1, 'status': 'completed',
        'timeout_seconds': timeout, 'started_utc': '2026-10-08T00:00:00+00:00',
        'output': str(root), 'returncode': 0,
        'elapsed_seconds': 1.0,
    }
    path = root / 'supervisor.json'
    path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return {'path': str(path), 'sha256': _sha(path)}


def _closed_pair(tmp_path):
    protocol = {'schema': 'memory-family-native-protocol-v3',
                'scope': 'synthetic-contract-only'}
    source_identity = {'schema': 'source-identity-v1', 'commit': 'fixture'}
    output = tmp_path / 'output'
    pair = _pair(output / 'runs', protocol_sha256=memory.sha256(protocol),
                 source_identity_sha256=memory.sha256(source_identity))
    values = _contract_inputs(tmp_path, pair=pair)
    assert artifacts._json(values['protocol_path'].read_bytes()) == protocol
    assert values['source_identity'] == source_identity
    registration = _build(values)
    registration_path = _registration_file(values, registration)
    registration_sha = _sha(registration_path)
    source_job = producer.make_job(registration_path, pair['case']['case_id'], None)
    own_job = producer.make_job(registration_path, pair['case']['case_id'], 'own', {
        'run_id': pair['source']['run_id'],
        'run_path': pair['source']['run_path'],
        'snapshot_path': str(Path(pair['source']['run_path']) / 'snapshots/initial.snp'),
        'snapshot_sha256': pair['post']['source_snapshot_sha256'],
    })
    job_root = values['roots']['control'] / 'jobs'
    source_job_path = _write(job_root / f"{source_job['run_id']}.json", source_job)
    own_job_path = _write(job_root / f"{own_job['run_id']}.json", own_job)
    namespace = 'pid:[fixture]'
    rows = []
    for index, (job, path, timeout) in enumerate((
            (source_job, source_job_path, 370), (own_job, own_job_path, 130)), 1):
        owner = {
            'schema': 'memory-family-owner-v3', 'run_id': job['run_id'],
            'pid': 9000 + index, 'starttime': 1, 'pgid': 9000 + index,
            'process_namespace': namespace,
            'registration_sha256': registration_sha, 'job_sha256': _sha(path),
        }
        owner_path = _write(Path(job['output']) / 'owner.json', owner)
        supervisor = _supervision(values, job, timeout)
        rows.append({'run_id': job['run_id'], 'owner_path': str(owner_path),
                     'owner_sha256': _sha(owner_path), 'status': 'already-exited',
                     'supervisor_path': supervisor['path'],
                     'supervisor_sha256': supervisor['sha256']})
        _patch_manifest(job['output'], {
            'schema': 'memory-family-producer-binding-v3',
            'registration_sha256': registration_sha,
            'job_sha256': _sha(path), 'owner_sha256': _sha(owner_path),
        })
    cleanup_path = _write(values['roots']['control'] / 'cleanup' /
                          f"{source_job['run_id']}-{own_job['run_id']}.json", {
        'schema': 'memory-family-pair-cleanup-v3',
        'registration_sha256': registration_sha,
        'process_namespace': namespace, 'rows': rows,
    })
    (values['roots']['publication'] / 'pair-closes').mkdir()
    return values, pair, registration_path, source_job_path, own_job_path, cleanup_path


def test_close_admits_real_synthetic_pair_and_writes_once(tmp_path):
    values, pair, registration, source_job, own_job, cleanup = _closed_pair(tmp_path)
    raw_before = _tree_hashes(values['roots']['output'])
    with patch.object(producer.os, 'readlink', return_value='pid:[fixture]'), \
            patch.object(producer.diagnostic, 'owner_exited', return_value=True):
        result = producer.close_oracle_pair(
            registration, source_job, own_job, cleanup)
        with pytest.raises(FileExistsError):
            producer.close_oracle_pair(registration, source_job, own_job, cleanup)

    close = artifacts._json(Path(result['path']).read_bytes())
    assert result['sha256'] == _sha(result['path'])
    assert close['status'] == 'contract-pair-validated'
    assert close['case_id'] == pair['case']['case_id']
    assert close['oracle']['proof_sha256'] == close['oracle']['selector_resource']['provenance_sha256']
    assert close['study_complete'] is close['native_allocation'] is False
    assert close['held_out_used'] is False and close['qualification_claims'] == []
    assert _tree_hashes(values['roots']['output']) == raw_before


@pytest.mark.parametrize('defect', [
    'namespace', 'owner-active', 'supervisor', 'supervisor-path',
    'supervisor-extra', 'supervisor-overrun', 'supervisor-control', 'manifest',
    'job-registration', 'drift',
])
def test_close_rejects_unproved_or_changed_inputs_without_publication(tmp_path, defect):
    values, _, registration, source_job, own_job, cleanup = _closed_pair(tmp_path)
    cleanup_value = artifacts._json(Path(cleanup).read_bytes())
    if defect == 'namespace':
        namespace = 'pid:[other]'
    else:
        namespace = 'pid:[fixture]'
    if defect == 'supervisor':
        path = Path(cleanup_value['rows'][0]['supervisor_path'])
        report = artifacts._json(path.read_bytes())
        report['returncode'] = 1
        _write(path, report)
        cleanup_value['rows'][0]['supervisor_sha256'] = _sha(path)
        _write(cleanup, cleanup_value)
    elif defect == 'supervisor-path':
        original_path = Path(cleanup_value['rows'][0]['supervisor_path'])
        other = original_path.parents[1] / 'substitute' / 'supervisor.json'
        other.parent.mkdir()
        for name in ('stdout.log', 'stderr.log'):
            (other.parent / name).write_bytes((original_path.parent / name).read_bytes())
        report = artifacts._json(original_path.read_bytes())
        report['output'] = str(other.parent)
        other.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        cleanup_value['rows'][0]['supervisor_path'] = str(other)
        cleanup_value['rows'][0]['supervisor_sha256'] = _sha(other)
        _write(cleanup, cleanup_value)
    elif defect == 'supervisor-extra':
        path = Path(cleanup_value['rows'][0]['supervisor_path'])
        (path.parent / 'unregistered.log').write_bytes(b'extra')
    elif defect == 'supervisor-overrun':
        path = Path(cleanup_value['rows'][0]['supervisor_path'])
        report = artifacts._json(path.read_bytes())
        report['elapsed_seconds'] = report['timeout_seconds'] + 11
        path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        cleanup_value['rows'][0]['supervisor_sha256'] = _sha(path)
        _write(cleanup, cleanup_value)
    elif defect == 'supervisor-control':
        path = Path(cleanup_value['rows'][0]['supervisor_path'])
        report = artifacts._json(path.read_bytes())
        report['started_utc'] = 'x' * producer.RESOURCE_PROJECTION['control_max_bytes']
        path.write_text(json.dumps(report, allow_nan=False))
        cleanup_value['rows'][0]['supervisor_sha256'] = _sha(path)
        _write(cleanup, cleanup_value)
    elif defect == 'manifest':
        path = Path(artifacts._json(Path(source_job).read_bytes())['output']) / 'recording/manifest.json'
        manifest = artifacts._json(path.read_bytes())
        manifest.pop('memory_family_producer_v3')
        _write(path, manifest)
    elif defect == 'job-registration':
        outer_sha = _sha(registration)
        alternate = artifacts._json(Path(registration).read_bytes())
        alternate_publication = tmp_path / 'publication-alternate'
        alternate['roots']['publication'] = str(alternate_publication)
        alternate_path = _write(alternate_publication / 'registration.json', alternate)
        original_post = artifacts._json(Path(own_job).read_bytes())
        jobs = [
            producer.make_job(alternate_path, original_post['case_id'], None),
            producer.make_job(alternate_path, original_post['case_id'], 'own',
                              original_post['source']),
        ]
        for job_path, job, row in zip((source_job, own_job), jobs,
                                      cleanup_value['rows']):
            _write(job_path, job)
            owner_path = Path(row['owner_path'])
            owner = artifacts._json(owner_path.read_bytes())
            owner['job_sha256'] = _sha(job_path)
            _write(owner_path, owner)
            row['owner_sha256'] = _sha(owner_path)
            _patch_manifest(job['output'], {
                'schema': 'memory-family-producer-binding-v3',
                'registration_sha256': outer_sha,
                'job_sha256': _sha(job_path),
                'owner_sha256': row['owner_sha256'],
            })
        _write(cleanup, cleanup_value)

    original = producer.admission.admit_oracle_pair
    if defect == 'drift':
        def admit_then_change(*args, **kwargs):
            result = original(*args, **kwargs)
            Path(cleanup).write_bytes(Path(cleanup).read_bytes() + b' ')
            return result
        admission = admit_then_change
    else:
        admission = original
    owner_exit = False if defect == 'owner-active' else True
    with patch.object(producer.os, 'readlink', return_value=namespace), \
            patch.object(producer.diagnostic, 'owner_exited', return_value=owner_exit), \
            patch.object(producer.admission, 'admit_oracle_pair', side_effect=admission):
        with pytest.raises((ValueError, RuntimeError)):
            producer.close_oracle_pair(registration, source_job, own_job, cleanup)
    assert not any((values['roots']['publication'] / 'pair-closes').iterdir())


def test_close_publication_failure_leaves_no_partial_final_or_temporary(tmp_path):
    values, _, registration, source_job, own_job, cleanup = _closed_pair(tmp_path)
    close_root = values['roots']['publication'] / 'pair-closes'
    with patch.object(producer.os, 'readlink', return_value='pid:[fixture]'), \
            patch.object(producer.diagnostic, 'owner_exited', return_value=True), \
            patch.object(producer.os, 'link', side_effect=OSError('fixture publish failure')):
        with pytest.raises(OSError, match='fixture publish failure'):
            producer.close_oracle_pair(registration, source_job, own_job, cleanup)
    assert not any(close_root.iterdir())


def test_contract_flow_has_no_native_launch_path(tmp_path):
    forbidden = AssertionError('contract attempted native execution')
    with patch('palimpsest.evaluate.bounded_process', side_effect=forbidden), \
            patch('subprocess.Popen', side_effect=forbidden), \
            patch('palimpsest.engine.Engine.open', side_effect=forbidden), \
            patch('os.killpg', side_effect=forbidden):
        values, _, registration, source_job, own_job, cleanup = _closed_pair(tmp_path)
        with patch.object(producer.os, 'readlink', return_value='pid:[fixture]'), \
                patch.object(producer.diagnostic, 'owner_exited', return_value=True):
            result = producer.close_oracle_pair(
                registration, source_job, own_job, cleanup)
    assert Path(result['path']).is_file()
