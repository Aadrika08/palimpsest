"""Independent, authored metadata checks; no vendor packages or real allocation."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/audit_puck_cpu_runtime_characterization.py'
ARCHIVE = ROOT / 'docs/reports/puck-cpu-characterization-02'
NAMES = ('torch._C._distributed_autograd', 'torch._C._distributed_c10d', 'torch._C._distributed_rpc')
FALSE = dict(runtime_qualified=False, native_authorized=False, collection_authorized=False,
             study_authorized=False, executable=False, qualification_claims=[])


def api():
    assert SCRIPT.is_file(), 'Independent characterization03 auditor is not implemented'
    spec = importlib.util.spec_from_file_location('distributed_auditor_tests', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path):
    return json.loads(path.read_bytes())


def proposal():
    return load(ROOT / 'docs/reports/puck-cpu-export-phase-preflight-v1/notes/distributed-rosters/review.json')


def expected():
    return {name: ['Expected'] for name in NAMES}


def projection(mismatch=False):
    rows = []
    for name in NAMES:
        actual = ['Extra'] if mismatch else ['Expected']
        rows.append(dict(name=name, raw_attribute_identity=True, cache_identity=True,
                         metadata=dict(name=name, module_type='builtins.module', file=None,
                                       package=None, loader_type=None, spec=None, path=[]),
                         delegate_attributes=actual,
                         comparison=dict(expected=['Expected'], missing=['Expected'] if mismatch else [],
                                         extra=['Extra'] if mismatch else [], matches=not mismatch)))
    return dict(kind='puck-cpu-distributed-exports-v1', version=1,
                capture_point='after_four_fixed_imports', stable=True, profile_accepted=False,
                runtime_qualified=False, modules=rows)


@pytest.mark.parametrize('mismatch', [False, True])
def test_complete_projection_including_disagreement_is_data_not_authority(mismatch):
    module = api()
    module.validate_distributed_projection(projection(mismatch), expected())


@pytest.mark.parametrize('change', ['stable', 'version-bool', 'profile', 'runtime', 'missing-row', 'duplicate',
                                   'order', 'name', 'identity', 'cache', 'plain-type', 'metadata-name',
                                   'metadata-extra', 'bad-spec', 'bad-path', 'unsorted', 'duplicate-delegate',
                                   'long-name', 'too-many', 'wrong-expected', 'missing', 'extra', 'matches', 'field'])
def test_projection_rejects_semantic_tamper_even_after_json_rebinding(change):
    module = api()
    value = projection()
    row = value['modules'][0]
    if change in ('stable', 'profile', 'runtime'):
        value[{'stable': 'stable', 'profile': 'profile_accepted', 'runtime': 'runtime_qualified'}[change]] = change != 'stable'
    elif change == 'version-bool': value['version'] = True
    elif change == 'missing-row': value['modules'].pop()
    elif change == 'duplicate': value['modules'][1] = copy.deepcopy(row)
    elif change == 'order': value['modules'].reverse()
    elif change == 'name': row['name'] = 'torch._C._other'
    elif change == 'identity': row['raw_attribute_identity'] = False
    elif change == 'cache': row['cache_identity'] = 1
    elif change == 'plain-type': row['metadata']['module_type'] = 'vendor.HookedModule'
    elif change == 'metadata-name': row['metadata']['name'] = 'other'
    elif change == 'metadata-extra': row['metadata']['extra'] = True
    elif change == 'bad-spec': row['metadata']['spec'] = {'name': 'missing-fields'}
    elif change == 'bad-path': row['metadata']['path'] = [0]
    elif change == 'unsorted': row['delegate_attributes'] = ['z', 'a']
    elif change == 'duplicate-delegate': row['delegate_attributes'] = ['Expected', 'Expected']
    elif change == 'long-name': row['delegate_attributes'] = ['x' * 513]
    elif change == 'too-many': row['delegate_attributes'] = [str(i).zfill(5) for i in range(4097)]
    elif change == 'wrong-expected': row['comparison']['expected'] = ['Rebound']
    elif change == 'missing': row['comparison']['missing'] = ['Invented']
    elif change == 'extra': row['comparison']['extra'] = ['Invented']
    elif change == 'matches': row['comparison']['matches'] = 1
    else: value['extra'] = False
    rebound = json.loads(json.dumps(value, sort_keys=True))
    with pytest.raises(ValueError):
        module.validate_distributed_projection(rebound, expected())


def configuration(module):
    prior = load(ARCHIVE / 'frozen-configuration.json')
    sources = [dict(path=name, size_bytes=1, sha256='a' * 64) for name in module.SOURCES]
    return dict(kind='puck-cpu-runtime-characterization-v2', version=2,
                output='runs/puck-cpu-runtime-characterization-03', site_root='runs/puck-cpu-install-01/site',
                sources=sources, inputs=module.required_inputs(prior), roles=dict(module.ROLES),
                environment=dict(module.ENVIRONMENT), limits=dict(module.LIMITS),
                expected_versions=dict(numpy='2.2.5', torch='2.9.0+cpu', torchvision='0.24.0+cpu', mujoco='3.3.6'))


def test_closed_19_source_63_input_19_role_epoch_preserves_every_old_pin():
    module = api()
    prior = load(ARCHIVE / 'frozen-configuration.json')
    config = configuration(module)
    module.validate_configuration(config, prior, proposal())
    assert len(config['sources']) == 19 and len(config['inputs']) == 63 and len(config['roles']) == 19
    new = {row['path']: row for row in config['inputs']}
    assert all(new[row['path']] == row for row in prior['inputs'])
    assert all(new['docs/reports/puck-cpu-characterization-02/source/' + row['path']]
               == dict(row, path='docs/reports/puck-cpu-characterization-02/source/' + row['path'])
               for row in prior['sources'])


@pytest.mark.parametrize('change', ['legacy', 'bool', 'output', 'role', 'extra-role', 'source', 'input', 'duplicate',
                                   'input-hash', 'historical-hash', 'environment', 'limits', 'extra'])
def test_configuration_refuses_rebound_boundary_changes(change):
    module = api()
    prior = load(ARCHIVE / 'frozen-configuration.json')
    value = configuration(module)
    if change == 'legacy': value['kind'] = 'puck-cpu-runtime-characterization-v1'
    elif change == 'bool': value['version'] = True
    elif change == 'output': value['output'] = 'runs/puck-cpu-runtime-characterization-02'
    elif change == 'role': value['roles']['observation_report'] = 'another.json'
    elif change == 'extra-role': value['roles']['extra'] = 'another.json'
    elif change == 'source': value['sources'].pop()
    elif change == 'input': value['inputs'].pop()
    elif change == 'duplicate': value['sources'].append(dict(value['sources'][0]))
    elif change == 'input-hash': value['inputs'][0]['sha256'] = '0' * 64
    elif change == 'historical-hash':
        next(row for row in value['inputs'] if row['path'].endswith('02/raw/result.json'))['sha256'] = '0' * 64
    elif change == 'environment': value['environment']['PATH'] = '/usr/bin'
    elif change == 'limits': value['limits']['normal_seconds'] = 181
    else: value['extra'] = True
    with pytest.raises(ValueError): module.validate_configuration(value, prior, proposal())


def report(module):
    maps = dict(images=[], map_bytes=0, map_lines=0, persistent_snapshot_only=True,
                transient_anonymous_jit_closure_qualified=False)
    cache_rows = [dict(name=name, classification='virtual', spec_name=None, file=None,
                      exports=[dict(producer='torch._C', attribute=name.rsplit('.', 1)[1])] if name in NAMES else [])
                  for name in ('torch', 'torch._C', *NAMES)]
    return dict(FALSE, kind='puck-runtime-import-characterization-result-v4', version=4, status='observed',
                profile='cpu-distributed-terminal-v1', request_sha256='a' * 64, source_sha256='b' * 64,
                environment_sha256=hashlib.sha256(module.canonical(module.ENVIRONMENT)).hexdigest(),
                python_version='3.11.15 AUTHORED', executable_path=module.PYTHON, pid=2, ppid=1,
                expected_versions=dict(module.VERSIONS), versions=dict(module.VERSIONS),
                imports=[dict(name=name, status='observed', seconds=.01, cache_entries=0)
                         for name in ('numpy', 'torch', 'torchvision', 'mujoco')],
                cache=dict(modules=cache_rows, attribute_edges=0, module_objects=5, cache_entries=5,
                           export_scope='exceptional_cache_identities'), baseline_maps=maps, maps=copy.deepcopy(maps),
                environment_delta=None, observation_errors=[], pycache_prefix='/scratch/pycache',
                distributed_exports=projection(True), observation_scope='completed_imports', seconds=.1)


def test_full_report_accepts_scoped_complete_mismatch():
    module = api()
    module.validate_report(report(module), expected(), 'a' * 64, 'b' * 64)


def test_pid_namespace_init_report_has_zero_parent_pid():
    module = api(); value = report(module); value.update(pid=1, ppid=0)
    module.validate_report(value, expected(), 'a' * 64, 'b' * 64)


def test_report_must_finish_before_normal_parent_deadline():
    module = api(); value = report(module); value['seconds'] = 180
    with pytest.raises(ValueError): module.validate_report(value, expected(), 'a' * 64, 'b' * 64)


@pytest.mark.parametrize('name', ['torch', 'torch._C', *NAMES])
@pytest.mark.parametrize('change', ['missing', 'nonmodule', 'subclass'])
def test_projection_fixed_roots_must_also_be_plain_modules_in_cache(name, change):
    module = api(); value = report(module)
    rows = value['cache']['modules']; row = next(row for row in rows if row['name'] == name)
    if change == 'missing':
        rows.remove(row); value['cache'].update(cache_entries=4, module_objects=4)
    elif change == 'nonmodule':
        row.clear(); row.update(name=name, classification='nonmodule', type='builtins.int')
        value['cache']['module_objects'] = 4
    else:
        row['type'] = 'authored.ModuleSubclass'
    with pytest.raises(ValueError): module.validate_report(value, expected(), 'a' * 64, 'b' * 64)


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('change', ['file', 'spec-name', 'spec-origin', 'spec-type', 'missing-edge', 'attribute', 'producer'])
def test_child_cache_metadata_and_exceptional_edges_cannot_contradict_projection(name, change):
    module = api(); value = report(module)
    child = next(row for row in value['distributed_exports']['modules'] if row['name'] == name)
    cached = next(row for row in value['cache']['modules'] if row['name'] == name)
    if change == 'file': child['metadata']['file'] = '/AUTHORED/different.so'
    elif change in ('spec-name', 'spec-origin'):
        child['metadata']['spec'] = dict(name='different' if change == 'spec-name' else None,
            origin='/different' if change == 'spec-origin' else None, loader_type=None, submodule_search_locations=None)
    elif change == 'spec-type': cached['spec_type'] = 'authored.SpecSubclass'
    elif change == 'missing-edge': cached['exports'] = []
    elif change == 'attribute': cached['exports'][0]['attribute'] = 'different'
    else: cached['exports'][0]['producer'] = 'different'
    with pytest.raises(ValueError): module.validate_report(value, expected(), 'a' * 64, 'b' * 64)


def test_ordinary_exact_spec_file_single_cache_children_need_no_exceptional_edge():
    module = api(); value = report(module)
    for child in value['distributed_exports']['modules']:
        name = child['name']; filename = '/AUTHORED/torch/_C.so'
        child['metadata'].update(file=filename, spec=dict(name=name, origin=filename, loader_type=None,
                                                        submodule_search_locations=None))
        cached = next(row for row in value['cache']['modules'] if row['name'] == name)
        cached.update(file=filename, spec_name=name, classification='module', exports=[])
    module.validate_report(value, expected(), 'a' * 64, 'b' * 64)


def test_exceptional_native_child_edge_can_use_first_inspected_native_cache_alias():
    module = api(); value = report(module)
    rows = value['cache']['modules']; native = next(row for row in rows if row['name'] == 'torch._C')
    native['same_object_cache_names'] = ['_AUTHORED_native_alias', 'torch._C']
    alias = copy.deepcopy(native); alias['name'] = '_AUTHORED_native_alias'; rows.append(alias)
    rows.sort(key=lambda row: row['name']); value['cache']['cache_entries'] = len(rows)
    for row in rows:
        if row['name'] in NAMES: row['exports'][0]['producer'] = '_AUTHORED_native_alias'
    module.validate_report(value, expected(), 'a' * 64, 'b' * 64)


@pytest.mark.parametrize('change', ['legacy', 'extra', 'error', 'nan', 'bool-pid', 'version', 'order', 'import-time',
                                   'request', 'worker', 'environment', 'delta', 'maps', 'map-entry', 'cache',
                                   'cache-row', 'runtime'])
def test_report_refuses_boundaries_after_json_hash_rebinding(change):
    module = api(); value = report(module)
    if change == 'legacy': value['kind'] = 'puck-runtime-import-characterization-result-v3'
    elif change == 'extra': value['extra'] = False
    elif change == 'error': value['error'] = {}
    elif change == 'nan': value['seconds'] = float('nan')
    elif change == 'bool-pid': value['pid'] = True
    elif change == 'version': value['versions']['torch'] = 'other'
    elif change == 'order': value['imports'].reverse()
    elif change == 'import-time': value['imports'][0]['seconds'] = -1
    elif change == 'request': value['request_sha256'] = 'c' * 64
    elif change == 'worker': value['source_sha256'] = 'c' * 64
    elif change == 'environment': value['environment_sha256'] = 'c' * 64
    elif change == 'delta': value['environment_delta'] = {}
    elif change == 'maps': value['maps']['transient_anonymous_jit_closure_qualified'] = True
    elif change == 'map-entry': value['maps']['images'] = [dict(device='00:01', inode=True, path='/x', segments=1, executable=True)]
    elif change == 'cache': value['cache']['cache_entries'] = 1
    elif change == 'cache-row': value['cache']['modules'] = [dict(name='x', classification='nonmodule', type='builtins.int', extra=True)]; value['cache']['cache_entries'] = 1
    else: value['runtime_qualified'] = True
    with pytest.raises(ValueError): module.validate_report(value, expected(), 'a' * 64, 'b' * 64)


def transport(module, root):
    configuration = dict(path='configuration.json', size_bytes=2, sha256='a' * 64)
    return dict(FALSE, kind='puck-cpu-characterization-cli-transport-v1', version=1, root=str(root), allocation_id=3,
                configuration=configuration, command=[module.PYTHON, '-I', '-S', '-B', str(root / 'scripts/characterize_puck_cpu_runtime.py'),
                    '--configuration', str(root / 'configuration.json'), '--sha256', 'a' * 64], environment=dict(module.TRANSPORT_ENVIRONMENT),
                observed_returncode=0, elapsed_seconds=.1, timed_out=False, parent_identity=dict(pid=101, start_ticks=1),
                sampled_identities=[dict(pid=101, start_ticks=1)], sampled_survivors=[], sampled_cleanup_only=True,
                sampling_limitation=module.SAMPLING_LIMITATION,
                stdout=dict(path='runs/puck-cpu-runtime-characterization-03-external-cli.stdout', size_bytes=0, sha256=hashlib.sha256(b'').hexdigest()),
                stderr=dict(path='runs/puck-cpu-runtime-characterization-03-external-cli.stderr', size_bytes=0, sha256=hashlib.sha256(b'').hexdigest()))


@pytest.mark.parametrize('change', [None, 'code-bool', 'code', 'timeout', 'late', 'missing-parent', 'parent-bool',
                                   'survivor', 'duplicate', 'too-many', 'environment', 'argv', 'claim', 'stream-path', 'extra'])
def test_transport_acceptance_uses_observed_exact_command_and_sampled_scope(tmp_path, monkeypatch, change):
    module = api(); monkeypatch.setattr(module, 'ROOT', tmp_path)
    value = transport(module, tmp_path)
    if change == 'code-bool': value['observed_returncode'] = False
    elif change == 'code': value['observed_returncode'] = 7
    elif change == 'timeout': value['timed_out'] = True
    elif change == 'late': value['elapsed_seconds'] = 210
    elif change == 'missing-parent': value['parent_identity'] = None
    elif change == 'parent-bool': value['parent_identity']['pid'] = True
    elif change == 'survivor': value['sampled_survivors'] = [dict(pid=101, start_ticks=1)]
    elif change == 'duplicate': value['sampled_identities'] *= 2
    elif change == 'too-many': value['sampled_identities'] = [dict(pid=i + 1, start_ticks=1) for i in range(65)]
    elif change == 'environment': value['environment']['PATH'] += ':/tmp'
    elif change == 'argv': value['command'].insert(1, '-c')
    elif change == 'claim': value['runtime_qualified'] = True
    elif change == 'stream-path': value['stdout']['path'] = 'elsewhere.log'
    elif change == 'extra': value['error'] = 'rebound ignored failure'
    if change is None: module.validate_transport(value, tmp_path / 'configuration.json', value['configuration'])
    else:
        with pytest.raises(ValueError): module.validate_transport(value, tmp_path / 'configuration.json', dict(path='configuration.json', size_bytes=2, sha256='a' * 64))


def test_helpers_authenticate_all_raw_bytes_and_relocate_only_fixed_literal(tmp_path, monkeypatch):
    module = api(); monkeypatch.setattr(module, 'ROOT', tmp_path)
    for filename in ('audit-support-characterization-v1.py', 'audit-helper-install-v1.py', 'audit-helper-admission-v3.py'):
        path = tmp_path / 'docs/reports/puck-cpu-characterization-02' / filename
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes((ARCHIVE / filename).read_bytes())
    previous = sys.modules.get('palimpsest_cpu_install_audit_v1')
    p, a, r, rows = module.support()
    assert r.a is a and p.a is a and p.r is r
    assert Path(r.HELPER) == tmp_path / 'docs/reports/puck-cpu-characterization-02/audit-helper-install-v1.py'
    assert sys.modules.get('palimpsest_cpu_install_audit_v1') is previous
    assert len(rows) == 3 and rows[2]['raw_sha256'] != rows[2]['adapted_sha256']
    assert rows[0]['raw_sha256'] == rows[0]['adapted_sha256']
    assert rows[1]['raw_sha256'] == rows[1]['adapted_sha256']
    path.write_bytes(path.read_bytes() + b'\nraise AssertionError("must not execute")\n')
    def unexpected_compile(*args, **kwargs): raise AssertionError('No helper may compile before all three authenticate')
    monkeypatch.setattr(module, 'compile', unexpected_compile, raising=False)
    with pytest.raises(ValueError): module.support()


def test_retained_index_zero_byte_raw_stream_is_a_valid_byte_pin():
    module = api(); value = load(ARCHIVE / 'evidence-index.json')
    rows = module.pin_rows(value['entries'], value['file_count'])
    assert rows['raw/probe-logs/stderr.log']['size_bytes'] == 0


@pytest.mark.parametrize('change', [None, 'result', 'closure', 'report', 'report-claim', 'audit', 'exit-bool',
                                   'verified', 'index', 'retry', 'terminal', 'pin'])
def test_historical02_semantics_remain_scoped_and_immutable_after_rebinding(change):
    module = api(); prior = load(ARCHIVE / 'frozen-configuration.json')
    values = [load(ARCHIVE / path) for path in ('raw/result.json', 'raw/payload/imports.json',
                                               'outcome-audit-02.json', 'evidence-index.json', 'external-terminal-observations.json')]
    result, old_report, audit, index, terminal = values
    pins = {row['path']: row for row in module.required_inputs(prior)}
    if change == 'result': result['status'] = 'FAIL'
    elif change == 'closure': result['closure']['all_handles_closed'] = False
    elif change == 'report': old_report['status'] = 'failed'
    elif change == 'report-claim': old_report['runtime_qualified'] = True
    elif change == 'audit': audit['ordinary_imports_observed'] = False
    elif change == 'exit-bool': audit['caller_supplied_observed_parent_exit_code'] = False
    elif change == 'verified': audit['verified']['source_pins'] = 19
    elif change == 'index': index['original_output'] = 'runs/observation-03'
    elif change == 'retry': terminal['actual_retry_performed'] = True
    elif change == 'terminal': terminal['actual']['exit_code'] = False
    elif change == 'pin': pins[next(iter(pins))] = dict(pins[next(iter(pins))], sha256='0' * 64)
    if change is None: module.validate_observation02(prior, *values, pins)
    else:
        with pytest.raises(ValueError): module.validate_observation02(prior, *values, pins)


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1} {"x":2}'])
def test_json_rejects_duplicate_nonfinite_or_extra_document(raw):
    with pytest.raises(ValueError): api().decode(raw)


def test_full_trusted_prefix_census_hashes_bytes_and_rejects_escaping_symlink(tmp_path):
    module = api(); p, a, _, _ = module.support()
    prefix = tmp_path / 'prefix'; prefix.mkdir(); (prefix / 'bin').mkdir()
    (prefix / 'bin/authored').write_bytes(b'AUTHORED bytes')
    (prefix / 'bin/alias').symlink_to('authored')
    value = module.prefix_inventory(prefix, p, a)
    assert value['files'] == [['bin/authored', 14, hashlib.sha256(b'AUTHORED bytes').hexdigest()]]
    assert value['symlinks'] == [['bin/alias', 'authored']]
    (prefix / 'escape').symlink_to(tmp_path)
    p, a, _, _ = module.support()
    with pytest.raises(ValueError): module.prefix_inventory(prefix, p, a)


@pytest.mark.parametrize('case', ['live', 'absent', 'reused'])
def test_independent_final_close_checks_only_recorded_pid_start_lifetimes(case):
    module = api()
    raw = Path('/proc/self/stat').read_bytes(); start = int(raw.rsplit(b') ', 1)[1].split()[19])
    identity = dict(pid=os.getpid(), start_ticks=start)
    if case == 'live':
        with pytest.raises(ValueError, match='still exists'): module.verify_sampled_absence([identity])
    elif case == 'absent':
        module.verify_sampled_absence([dict(pid=2**31-1, start_ticks=1)])
    else:
        module.verify_sampled_absence([dict(identity, start_ticks=start+1)])


def test_namespace_reconstruction_contains_exact_fixed_mounts_and_worker_binding(tmp_path, monkeypatch):
    module = api(); monkeypatch.setattr(module, 'ROOT', tmp_path)
    baseline = dict(python_prefix='/trusted/python', external_libraries=[], host_path_aliases=[])
    native = dict(native_files=[dict(path='/usr/lib/authored.so')], aliases=[])
    command = module.namespace_command(baseline, native, 'd' * 64)
    assert command[:14] == ['/usr/bin/bwrap', '--unshare-all', '--unshare-user', '--as-pid-1', '--disable-userns',
                            '--die-with-parent', '--cap-drop', 'ALL', '--clearenv', '--hostname',
                            'palimpsest-cpu-observation', '--ro-bind', '/trusted/python', '/trusted/python']
    assert command[14:17] == ['--ro-bind', '/usr/lib/authored.so', '/usr/lib/authored.so']
    assert command[-9:] == [module.PYTHON, '-I', '-S', '-B', '-X', 'pycache_prefix=/scratch/pycache', '/driver.py', '/request.json', 'd' * 64]
    probe = module.namespace_command(baseline, native, 'd' * 64, probe=True, parent_net='net:[AUTHORED]')
    assert probe[-4:] == [module.PROBE, 'net:[AUTHORED]', str(tmp_path / 'runs/puck-cpu-install-01/site'), str(tmp_path / 'docs')]


def test_cli_failure_is_false_authority_json_without_caller_exit_argument(tmp_path):
    module = api()
    result = subprocess.run([module.PYTHON, '-I', '-S', '-B', str(SCRIPT), '--configuration', str(tmp_path / 'absent.json'),
                             '--sha256', '0' * 64, '--transport', str(tmp_path / 'absent-transport.json'),
                             '--transport-sha256', '0' * 64], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    assert result.returncode == 1
    value = json.loads(result.stdout)
    assert value['status'] == 'FAIL' and value['target_code_executed_by_auditor'] is False
    assert all(value[key] == wanted for key, wanted in FALSE.items())


@pytest.mark.parametrize('stage', ['serialization', 'flush', 'post-flush'])
def test_cli_publication_deadline_covers_serialization_flush_and_timely_return(monkeypatch, stage):
    module = api(); saved = []; timer_active = []
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), '--configuration', '/AUTHORED/config.json', '--sha256', 'a'*64,
                                    '--transport', '/AUTHORED/transport.json', '--transport-sha256', 'b'*64])
    monkeypatch.setattr(module, 'sys', types.SimpleNamespace(executable=module.PYTHON,
        flags=types.SimpleNamespace(isolated=True, no_site=True), dont_write_bytecode=True))
    monkeypatch.setattr(module, 'audit', lambda *args: dict(scope='AUTHORED no execution'))
    original_handler = module.signal.getsignal(module.signal.SIGALRM)
    original_timer = module.signal.setitimer; canonical = module.canonical
    if stage != 'post-flush':
        monkeypatch.setattr(module.signal, 'setitimer', lambda which, seconds: original_timer(which, .03 if seconds else 0))
    clock = [0.]
    if stage == 'post-flush': monkeypatch.setattr(module, 'time', types.SimpleNamespace(monotonic=lambda: clock[0]))
    if stage == 'serialization':
        def slow_canonical(value):
            time.sleep(.06)
            return canonical(value)
        monkeypatch.setattr(module, 'canonical', slow_canonical)
    class Writer(io.StringIO):
        def flush(self):
            timer_active.append(module.signal.getitimer(module.signal.ITIMER_REAL)[0] > 0)
            if stage == 'flush': time.sleep(.06)
            if stage == 'post-flush': clock[0] = 181.
    writer = Writer()
    def publish(value, **kwargs):
        saved.append(json.loads(value))
        print(value, file=writer, **kwargs)
    monkeypatch.setattr(module, 'print', publish, raising=False)
    try:
        code = module.main()
    finally:
        original_timer(module.signal.ITIMER_REAL, 0)
        module.signal.signal(module.signal.SIGALRM, original_handler)
    assert code == 1
    if stage != 'serialization': assert timer_active == [True]
    assert all(all(value[key] == wanted for key, wanted in FALSE.items()) for value in saved)
