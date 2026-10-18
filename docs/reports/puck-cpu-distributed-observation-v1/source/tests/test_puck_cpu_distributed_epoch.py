"""Closed observation03 contracts, using retained data and authored projections only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/characterize_puck_cpu_runtime.py'
PROPOSAL = ROOT / 'docs/reports/puck-cpu-export-phase-preflight-v1/notes/distributed-rosters/review.json'


def api():
    spec = importlib.util.spec_from_file_location('distributed_epoch_parent', SCRIPT)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def configuration(m):
    return dict(kind='puck-cpu-runtime-characterization-v2', version=2,
                output=m.ROSTER_OUTPUT, site_root=m.SITE, roles=dict(m.ROSTER_ROLES),
                limits=dict(m.LIMITS), environment=dict(m.ENVIRONMENT), expected_versions=dict(m.VERSIONS),
                sources=[dict(path=p, size_bytes=1, sha256='0' * 64) for p in m.ROSTER_SOURCES],
                inputs=m.required_roster_input_rows(m.read_observation_configuration()))


def history(m):
    base = ROOT / m.OBSERVATION_ARCHIVE
    values = [json.loads((base / p).read_bytes()) for p in (
        'frozen-configuration.json', 'raw/result.json', 'raw/payload/imports.json',
        'outcome-audit-02.json', 'evidence-index.json', 'external-terminal-observations.json')]
    pins = {row['path']: row for row in m.required_roster_input_rows(values[0])}
    return values, pins


def report(m):
    value = json.loads((ROOT / 'docs/reports/puck-cpu-characterization-02/raw/payload/imports.json').read_bytes())
    value.update(kind='puck-runtime-import-characterization-result-v4', version=4,
                 profile='cpu-distributed-terminal-v1', request_sha256='1' * 64, source_sha256='2' * 64)
    expected = m.distributed_expected(json.loads(PROPOSAL.read_bytes()))
    modules = []
    for name, names in sorted(expected.items()):
        modules.append(dict(name=name, raw_attribute_identity=True, cache_identity=True,
            metadata=dict(name=name, module_type='builtins.module', file=None, package=None,
                          loader_type=None, spec=None, path=[]), delegate_attributes=list(names),
            comparison=dict(expected=list(names), missing=[], extra=[], matches=True)))
    value['distributed_exports'] = dict(kind='puck-cpu-distributed-exports-v1', version=1,
        capture_point='after_four_fixed_imports', stable=True, profile_accepted=False,
        runtime_qualified=False, modules=modules)
    return value, expected


def test_new_epoch_has_exact_19_sources_19_roles_and_63_inputs_without_changing02():
    m = api(); value = configuration(m); m.validate_configuration(value)
    old = m.read_observation_configuration(); m.validate_configuration(old)
    assert len(m.SOURCES) == 14 and len(m.ROLES) == 12 and m.OUTPUT.endswith('-02')
    assert len(m.ROSTER_SOURCES) == len(set(m.ROSTER_SOURCES)) == 19
    assert len(m.ROSTER_ROLES) == 19 and len(value['inputs']) == 63
    assert m.ROSTER_OUTPUT == 'runs/puck-cpu-runtime-characterization-03'
    assert 'scripts/observe_puck_cpu_runtime_characterization.py' in m.ROSTER_SOURCES
    assert 'scripts/audit_puck_cpu_runtime_characterization.py' in m.ROSTER_SOURCES
    assert 'docs/plans/puck-cpu-characterization-v2.md' not in m.ROSTER_SOURCES
    pins = {row['path']: row for row in value['inputs']}
    assert all(pins[row['path']] == row for row in old['inputs'])
    assert sum(p.startswith(m.OBSERVATION_ARCHIVE + '/source/') for p in pins) == 14
    values, pins = history(m); m.validate_observation02(*values, pins)


@pytest.mark.parametrize('defect', ['kind', 'version', 'boolean-version', 'output', 'roles', 'limit',
    'environment', 'versions', 'authority', 'source-missing', 'source-extra', 'source-fields',
    'source-bool-size', 'source-hash', 'input-missing', 'input-rebound', 'input-extra'])
def test_new_epoch_refuses_drift_or_rebound_history(defect):
    m = api(); value = configuration(m)
    if defect == 'kind': value['kind'] = 'puck-cpu-runtime-characterization-v3'
    elif defect == 'version': value['version'] = 3
    elif defect == 'boolean-version': value['version'] = True
    elif defect == 'output': value['output'] = m.OUTPUT
    elif defect == 'roles': value['roles']['observation_result'] = 'other.json'
    elif defect == 'limit': value['limits']['normal_seconds'] += 1
    elif defect == 'environment': value['environment']['OMP_NUM_THREADS'] = '2'
    elif defect == 'versions': value['expected_versions']['torch'] = 'other'
    elif defect == 'authority': value['runtime_qualified'] = True
    elif defect == 'source-missing': value['sources'].pop()
    elif defect == 'source-extra': value['sources'].append(dict(path='extra.py', size_bytes=1, sha256='0' * 64))
    elif defect == 'source-fields': value['sources'][0]['ignored'] = True
    elif defect == 'source-bool-size': value['sources'][0]['size_bytes'] = True
    elif defect == 'source-hash': value['sources'][0]['sha256'] = 'G' * 64
    elif defect == 'input-missing': value['inputs'].pop()
    elif defect == 'input-rebound': value['inputs'][0]['sha256'] = '0' * 64
    else: value['inputs'].append(dict(path='extra.json', size_bytes=1, sha256='0' * 64))
    with pytest.raises(ValueError): m.validate_configuration(value)


def test_observation_configuration_reader_authenticates_raw_bytes(monkeypatch):
    m = api(); m.read_observation_configuration()
    monkeypatch.setattr(m, 'read', lambda *_: b'{}\n')
    with pytest.raises(ValueError): m.read_observation_configuration()


@pytest.mark.parametrize('defect', ['parent-status', 'parent-authority', 'parent-report', 'parent-late',
    'parent-children', 'report-status', 'report-versions', 'audit-status', 'audit-scope',
    'audit-inputs', 'audit-report', 'terminal-return', 'terminal-retry', 'configuration', 'index'])
def test_historical02_success_is_not_weakened_or_reinterpreted(defect):
    m = api(); values, pins = history(m)
    config, result, worker, audit, index, terminal = values
    if defect == 'parent-status': result['status'] = 'FAIL'
    elif defect == 'parent-authority': result['runtime_qualified'] = True
    elif defect == 'parent-report': result['report_sha256'] = '0' * 64
    elif defect == 'parent-late': result['elapsed_seconds'] = 180
    elif defect == 'parent-children': result['closure']['active_children'] = [1]
    elif defect == 'report-status': worker['status'] = 'failed'
    elif defect == 'report-versions': worker['versions']['numpy'] = 'other'
    elif defect == 'audit-status': audit['status'] = 'FAIL'
    elif defect == 'audit-scope': audit['native_qualified'] = True
    elif defect == 'audit-inputs': audit['verified']['input_pins'] = 41
    elif defect == 'audit-report': audit['verified']['report_sha256'] = '0' * 64
    elif defect == 'terminal-return': terminal['actual']['exit_code'] = 1
    elif defect == 'terminal-retry': terminal['actual_retry_performed'] = True
    elif defect == 'configuration': config['inputs'].pop()
    else: index['actual_retry_performed'] = True
    with pytest.raises(ValueError): m.validate_observation02(*values, pins)


@pytest.mark.parametrize('defect', ['kind', 'target', 'producer', 'phase', 'raw-path', 'duplicate',
                                  'unsorted', 'boolean-name', 'authority'])
def test_expected_rosters_come_only_from_the_bounded_source_proposal(defect):
    m = api(); proposal = json.loads(PROPOSAL.read_bytes()); m.distributed_expected(proposal)
    row = proposal['proposed_rows']['autograd']
    if defect == 'kind': proposal['kind'] = 'other'
    elif defect == 'target': row['name'] = 'torch._C._other'
    elif defect == 'producer': row['producer'] = 'torch'
    elif defect == 'phase': row['phase'] = 'native_create'
    elif defect == 'raw-path': row['attributes'] = ['wrong']
    elif defect == 'duplicate': row['delegate_attributes'].append(row['delegate_attributes'][0])
    elif defect == 'unsorted': row['delegate_attributes'].reverse()
    elif defect == 'boolean-name': row['delegate_attributes'][0] = True
    else: proposal['acceptance']['runtime_qualified'] = True
    with pytest.raises(ValueError): m.distributed_expected(proposal)


def test_complete_roster_mismatch_remains_observed_data_without_profile_acceptance():
    m = api(); value, expected = report(m)
    row = value['distributed_exports']['modules'][0]
    actual = sorted(row['delegate_attributes'][1:] + ['AUTHORED_extra'])
    row['delegate_attributes'] = actual
    wanted = row['comparison']['expected']
    row['comparison'].update(missing=sorted(set(wanted)-set(actual)),
                             extra=sorted(set(actual)-set(wanted)), matches=False)
    m.validate_distributed_report(value, '1' * 64, '2' * 64, expected)
    assert value['distributed_exports']['profile_accepted'] is False


def test_projection_byte_limit_uses_the_workers_actual_ascii_escaped_encoding():
    m = api(); value, expected = report(m)
    projection = value['distributed_exports']
    for row in projection['modules']:
        row['metadata']['path'] = ['é' * 128] * 128
    assert len(json.dumps(projection, ensure_ascii=False).encode()) < 256 * 1024
    assert len(json.dumps(projection).encode()) > 256 * 1024
    with pytest.raises(ValueError):
        m.validate_distributed_report(value, '1' * 64, '2' * 64, expected)


@pytest.mark.parametrize('defect', ['kind', 'version', 'profile', 'request', 'source', 'authority',
    'error', 'imports', 'import-status', 'nan-time', 'environment', 'projection-kind', 'projection-version',
    'stable', 'profile-accepted', 'target', 'raw-identity', 'cache-identity', 'comparison', 'match-type',
    'duplicate-name', 'metadata-name', 'metadata-field', 'metadata-text', 'path-type', 'spec-field', 'extra-field'])
def test_new_parent_refuses_incomplete_or_semantically_rebound_projection(defect):
    m = api(); value, expected = report(m)
    projection = value['distributed_exports']; row = projection['modules'][0]
    if defect == 'kind': value['kind'] = 'puck-runtime-import-characterization-result-v3'
    elif defect == 'version': value['version'] = True
    elif defect == 'profile': value['profile'] = 'cpu-four-imports-v1'
    elif defect == 'request': value['request_sha256'] = '0' * 64
    elif defect == 'source': value['source_sha256'] = '0' * 64
    elif defect == 'authority': value['native_authorized'] = True
    elif defect == 'error': value['error'] = {}
    elif defect == 'imports': value['imports'].pop()
    elif defect == 'import-status': value['imports'][0]['status'] = 'failed'
    elif defect == 'nan-time': value['seconds'] = float('nan')
    elif defect == 'environment': value['environment_delta'] = {}
    elif defect == 'projection-kind': projection['kind'] = 'other'
    elif defect == 'projection-version': projection['version'] = True
    elif defect == 'stable': projection['stable'] = False
    elif defect == 'profile-accepted': projection['profile_accepted'] = True
    elif defect == 'target': row['name'] = 'torch._C._other'
    elif defect == 'raw-identity': row['raw_attribute_identity'] = 1
    elif defect == 'cache-identity': row['cache_identity'] = False
    elif defect == 'comparison': row['comparison']['missing'] = ['invented']
    elif defect == 'match-type': row['comparison']['matches'] = 1
    elif defect == 'duplicate-name': row['delegate_attributes'].append(row['delegate_attributes'][0])
    elif defect == 'metadata-name': row['metadata']['name'] = 'other'
    elif defect == 'metadata-field': row['metadata']['ignored'] = True
    elif defect == 'metadata-text': row['metadata']['file'] = 'x' * 4097
    elif defect == 'path-type': row['metadata']['path'] = [None]
    elif defect == 'spec-field': row['metadata']['spec'] = {'ignored': True}
    else: projection['ignored'] = True
    with pytest.raises(ValueError): m.validate_distributed_report(value, '1' * 64, '2' * 64, expected)
