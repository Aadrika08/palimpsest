"""AUTHORED ordinary observation03 route; no installed vendor payloads are read.

Only literal source pins/counts/RAM floors are relocated in authenticated test
clones. Historical records here are authored schema fixtures, not actual audits.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PARENT = 'scripts/characterize_puck_cpu_runtime.py'
OBSERVER = 'scripts/observe_puck_cpu_runtime_characterization.py'
AUDITOR = 'scripts/audit_puck_cpu_runtime_characterization.py'
PYTHON = '/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
SCOPE = 'AUTHORED stand-ins and history only; no actual CPU runtime evidence'


def canonical(value, *, ascii=True, pretty=False):
    kwargs = dict(sort_keys=True, ensure_ascii=ascii, allow_nan=False)
    kwargs.update(dict(indent=2) if pretty else dict(separators=(',', ':')))
    return (json.dumps(value, **kwargs)+'\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def put(root, name, value):
    raw = value if type(value) is bytes else canonical(value)
    path = root/name
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(raw)
    return dict(path=name, size_bytes=len(raw), sha256=sha(raw))


def clone_constants(raw, values):
    """Replace only named module literal bindings; prove exact reversibility."""
    text = raw.decode(); changes = []
    for key, value in values.items():
        tree = ast.parse(text)
        nodes = [n for n in tree.body if isinstance(n, ast.Assign)
                 and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id == key]
        assert len(nodes) == 1, key
        node = nodes[0]
        lines = text.splitlines(keepends=True)
        old = ''.join(lines[node.lineno-1:node.end_lineno])
        new = key+' = '+repr(value)+'\n'
        assert text.count(old) == 1
        text = text.replace(old, new, 1); changes.append((old, new))
    reverse = text
    for old, new in reversed(changes):
        assert reverse.count(new) == 1
        reverse = reverse.replace(new, old, 1)
    assert reverse.encode() == raw
    return text.encode(), changes


def command_capture(root, label, command, *, timeout=90):
    env = dict(PATH='/usr/bin:/bin', LANG='C.UTF-8', LC_ALL='C.UTF-8', PYTHONDONTWRITEBYTECODE='1')
    start = time.monotonic()
    child = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = child.communicate(timeout=timeout)
    except BaseException:
        os.killpg(child.pid, signal.SIGKILL); child.communicate(); raise
    rows = {name: put(root, 'authored-evidence/'+label+'.'+name, raw)
            for name, raw in (('stdout', out), ('stderr', err))}
    put(root, 'authored-evidence/'+label+'-transport.json', dict(
        authored_scope=SCOPE, command=command, observed_returncode=child.returncode,
        elapsed_seconds=time.monotonic()-start, **rows))
    return child.returncode, out, err


def make_project(tmp_path):
    from test_puck_cpu_held_parent_integration import project
    root, _, held_inputs, _ = project(tmp_path)
    original = load(ROOT/PARENT, 'distributed_original_parent')
    proposal_raw = (ROOT/original.DISTRIBUTED_PROPOSAL_PIN['path']).read_bytes()
    expected = original.distributed_expected(json.loads(proposal_raw))
    site = root/original.SITE
    # The immutable admission helper admits one exact production pyc only.
    # This unrelated authored inert leaf is ordinary data instead.
    (site/'inert.pyc').rename(site/'inert.data')
    # Plain stand-ins publish three raw children; no native extension or payload.
    source = ("__version__ = "+repr(original.VERSIONS['torch'])+"\nimport sys, types\n"
              "def authored_delegate():\n    return 47\n"
              "_C = types.ModuleType('torch._C')\n"
              "sys.modules['torch._C'] = _C\n")
    for name, names in expected.items():
        delegates = list(names) + (['AUTHORED_é'] if name.endswith('_autograd') else [])
        source += ("child = types.ModuleType("+repr(name)+")\n"
                   "setattr(_C, "+repr(name.rsplit('.', 1)[1])+", child)\n"
                   "sys.modules["+repr(name)+"] = child\n"
                   "for key in "+repr(delegates)+":\n    setattr(child, key, authored_delegate)\n")
    put(site, 'torch.py', source.encode())
    entries = []
    directories = []
    for folder, dirs, names in os.walk(site):
        dirs.sort(); names.sort()
        directories.extend((Path(folder)/d).relative_to(site).as_posix() for d in dirs)
        for name in names:
            p = Path(folder)/name; raw = p.read_bytes()
            entries.append(dict(path=p.relative_to(site).as_posix(), size_bytes=len(raw), sha256=sha(raw)))
    entries.sort(key=lambda row: row['path']); directories.sort()
    counts = (len(entries), len(directories), sum(row['size_bytes'] for row in entries))
    limits = dict(original.LIMITS, min_available_ram_bytes=128*1024**2)
    role_rows = {}
    def document(role, value, *, path=None):
        role_rows[role] = put(root, path or original.ROLES[role], value)
        return role_rows[role]
    inventory = dict(kind='puck-cpu-installed-files-v1', entries=entries,
                     file_count=counts[0], directory_count=counts[1], total_bytes=counts[2])
    document('inventory', inventory)
    layout = json.loads((root/held_inputs['layout']['path']).read_bytes())
    layout.pop('authored_scope', None)
    document('layout', layout)
    document('baseline', (ROOT/original.ROLES['baseline']).read_bytes())
    native = json.loads((root/held_inputs['native']['path']).read_bytes())
    native.pop('authored_scope', None)
    native.update(system_ELF_count_including_prefix=7, dependency_edges=[],
        optional_prefix_missing=[dict(needed='libcrypt.so.1')], numerical_imports_executed=False,
        target_execution_performed=False, runtime_qualified=False, renderer_qualified=False)
    document('native_metadata', native)
    accepted_original = json.loads((ROOT/original.ROLES['accepted_configuration']).read_bytes())
    accepted_sources = []
    accepted_caps = []
    for row in accepted_original['sources']:
        path = original.ARCHIVE+'/source/'+row['path']
        raw = (ROOT/path).read_bytes()
        assert len(raw) == row['size_bytes'] and sha(raw) == row['sha256']
        accepted_caps.append(put(root, path, raw)); accepted_sources.append(dict(row))
    assert len(accepted_sources) == 16
    document('accepted_configuration', dict(sources=accepted_sources, authored_scope=SCOPE))
    accepted_sha = role_rows['accepted_configuration']['sha256']
    document('accepted_snapshot', dict(site_root=str(site), configuration_sha256=accepted_sha))
    claims = dict(package_preparation_accepted=True, runtime_qualified=False,
                  numerical_imports_executed=False, study_authorized=False, collection_authorized=False)
    document('accepted_result', dict(status='PASS', configuration_sha256=accepted_sha,
        snapshot_sha256=role_rows['accepted_snapshot']['sha256'], claims=claims))
    document('accepted_audit', dict(status='PASS', **claims, verified=dict(configuration_sha256=accepted_sha)))
    document('accepted_index', dict(authored_scope=SCOPE, entries=[]))
    # Source capsules are data. Their raw historical bytes are kept independent
    # of the current authenticated clone and the new19-source closure.
    def capsules(names, archive):
        source_rows = []; archived_rows = []
        for name in names:
            raw = (ROOT/name).read_bytes()
            row = dict(path=name, size_bytes=len(raw), sha256=sha(raw))
            source_rows.append(row); archived_rows.append(put(root, archive+'/source/'+name, raw))
        return source_rows, archived_rows
    prior_sources, prior_caps = capsules(original.PRIOR_SOURCES, original.PRIOR_ARCHIVE)
    old_roles = {k:v for k,v in original.ROLES.items() if k not in original.PRIOR_PINS}
    old_roles['native_metadata'] = 'docs/plans/puck-cpu-characterization-native-metadata-04.json'
    native04 = put(root, old_roles['native_metadata'], native)
    old_inputs = sorted([*(row for role,row in role_rows.items() if role!='native_metadata'),
                         native04, *accepted_caps], key=lambda row: row['path'])
    assert len(old_inputs) == 25
    old_config = dict(kind='puck-cpu-runtime-characterization-v1', version=1,
        output='runs/puck-cpu-runtime-characterization-01', site_root=original.SITE,
        roles=old_roles, sources=prior_sources, inputs=old_inputs, limits=limits,
        environment=dict(original.ENVIRONMENT), expected_versions=dict(original.VERSIONS))
    prior_pins = {}
    def prior(role, value):
        prior_pins[role] = put(root, original.PRIOR_PINS[role]['path'], value)
        return prior_pins[role]
    prior('prior_configuration', old_config)
    closed = dict(active_children=[], active_non_main_threads=[], all_handles_closed=True,
                  all_receipts_fsynced=True, fd_count_before=5, fd_count_after=5)
    prior('prior_result', dict(original.CLAIMS, kind='puck-cpu-characterization-outcome-v1', status='FAIL',
        configuration_sha256=prior_pins['prior_configuration']['sha256'], elapsed_seconds=1., closure=closed,
        error_type='RuntimeError', error='CPU worker did not complete normally'))
    prior('prior_audit', dict(original.CLAIMS, kind='cpu-characterization-independent-failure-audit-v1',
        status='PRESERVED_FAILURE_VERIFIED', native_qualified=False, ordinary_imports_observed=False,
        target_code_executed_by_auditor=False, verified=dict(
            configuration_sha256=prior_pins['prior_configuration']['sha256'],
            parent_result_sha256=prior_pins['prior_result']['sha256'], worker_returncode=1,
            worker_failure=None, first_import='numpy', reported_error_type='builtins.ImportError',
            source_pins=14, input_pins=25, archived_acceptance_source_pins=16)))
    role_rows.update(prior_pins)
    observation_sources, observation_caps = capsules(original.SOURCES, original.OBSERVATION_ARCHIVE)
    inputs42 = {r['path']:r for r in old_inputs if r['path']!=old_roles['native_metadata']}
    for row in [role_rows['native_metadata'], *prior_pins.values(), *prior_caps]: inputs42[row['path']] = row
    assert len(inputs42) == 42
    observation = dict(kind='puck-cpu-runtime-characterization-v1', version=1, output=original.OUTPUT,
        site_root=original.SITE, sources=observation_sources, inputs=[inputs42[p] for p in sorted(inputs42)],
        roles=dict(original.ROLES), limits=limits, environment=dict(original.ENVIRONMENT),
        expected_versions=dict(original.VERSIONS))
    observation_pins = {}
    def observed(role, value):
        observation_pins[role] = put(root, original.OBSERVATION_PINS[role]['path'], value)
        return observation_pins[role]
    observed('observation_configuration', observation)
    observed('observation_report', dict(original.CLAIMS, kind='puck-runtime-import-characterization-result-v3',
        version=3, profile='cpu-four-imports-v1', status='observed', versions=dict(original.VERSIONS),
        expected_versions=dict(original.VERSIONS), observation_errors=[], environment_delta=None,
        observation_scope='completed_imports'))
    observed('observation_result', dict(original.CLAIMS, kind='puck-cpu-characterization-outcome-v1',
        status='observed', configuration_sha256=observation_pins['observation_configuration']['sha256'],
        report_sha256=observation_pins['observation_report']['sha256'], versions=dict(original.VERSIONS),
        namespace_probe_completed=True, accepted_package_preparation_preserved=True,
        worker_supervision_status='completed', elapsed_seconds=1., sampled_parent_peak_rss_bytes=4096, closure=closed))
    observed('observation_audit', dict(original.CLAIMS, kind='cpu-characterization-independent-outcome-audit-v2',
        status='PASS', expected_outcome='success', caller_supplied_observed_parent_exit_code=0,
        ordinary_imports_observed=True, native_qualified=False, target_code_executed_by_auditor=False,
        verified=dict(configuration_sha256=observation_pins['observation_configuration']['sha256'],
            report_sha256=observation_pins['observation_report']['sha256'],
            result_sha256=observation_pins['observation_result']['sha256'], source_pins=14, input_pins=42,
            accepted_source_capsules=16, prior_source_capsules=14, parent_status='observed',
            worker_status='observed', worker_returncode=0, baseline_after_present=True)))
    config_entry = dict(observation_pins['observation_configuration'], path='frozen-configuration.json')
    observed('observation_index', dict(kind='cpu-characterization-evidence-index-v2', actual_retry_performed=False,
        original_output=original.OUTPUT, entries=[config_entry], file_count=1, total_bytes=config_entry['size_bytes']))
    observed('observation_terminal', dict(kind='cpu-characterization-external-terminal-observations-v2',
        configuration_sha256=observation_pins['observation_configuration']['sha256'], actual_retry_performed=False,
        actual=dict(exit_code=0), outcome_audit=dict(status='PASS', exit_code=0)))
    put(root, original.DISTRIBUTED_PROPOSAL_PIN['path'], proposal_raw)
    for allocation in ('puck-cpu-install-01', 'puck-cpu-retained-admission-01'):
        put(root, 'runs/'+allocation+'/result.json', (ROOT/('docs/reports/'+allocation+'/raw/result.json')).read_bytes())
    # Copy precisely current19 source leaves, keeping archived helper bytes exact.
    for name in original.ROSTER_SOURCES:
        put(root, name, (ROOT/name).read_bytes())
    parent_values = dict(ACCEPTED_SHA=accepted_sha, PRIOR_PINS=prior_pins,
        NATIVE_METADATA_PIN=role_rows['native_metadata'], OBSERVATION_PINS=observation_pins, LIMITS=limits)
    changed, parent_ledger = clone_constants((ROOT/PARENT).read_bytes(), parent_values)
    marker = b"if len(files)!=27225 or len(directories)!=2074 or sum(r['size_bytes'] for r in files)!=1304701872:"
    replacement = ("if len(files)!="+str(counts[0])+" or len(directories)!="+str(counts[1])+
                   " or sum(r['size_bytes'] for r in files)!="+str(counts[2])+":").encode()
    assert changed.count(marker) == 1
    changed = changed.replace(marker, replacement)
    assert changed.replace(replacement, marker) == clone_constants((ROOT/PARENT).read_bytes(), parent_values)[0]
    put(root, PARENT, changed)
    auditor_values = dict(ACCEPTED_SHA=accepted_sha,
        PRIOR_SHAS=tuple(prior_pins[k]['sha256'] for k in ('prior_configuration','prior_result','prior_audit')),
        OBSERVATION_PINS=observation_pins, NATIVE_SHA=role_rows['native_metadata']['sha256'],
        SITE_COUNTS=counts, NATIVE_COUNTS=(8,3,7,0), LIMITS=limits)
    changed, auditor_ledger = clone_constants((ROOT/AUDITOR).read_bytes(), auditor_values)
    put(root, AUDITOR, changed)
    put(root, 'authored-evidence/clone-relocations.json', dict(authored_scope=SCOPE,
        parent_constants=list(parent_values), parent_count_line=[marker.decode(), replacement.decode()],
        auditor_constants=list(auditor_values), parent_changes=parent_ledger, auditor_changes=auditor_ledger))
    api = load(root/PARENT, 'distributed_authored_parent')
    inputs63 = dict(inputs42)
    for row in [*observation_pins.values(), original.DISTRIBUTED_PROPOSAL_PIN, *observation_caps]:
        inputs63[row['path']] = row
    assert len(inputs63) == 63
    sources = [dict(path=p, size_bytes=len((root/p).read_bytes()), sha256=sha((root/p).read_bytes())) for p in api.ROSTER_SOURCES]
    config = dict(kind='puck-cpu-runtime-characterization-v2', version=2, output=api.ROSTER_OUTPUT,
        site_root=api.SITE, sources=sources, inputs=[inputs63[p] for p in sorted(inputs63)],
        roles=dict(api.ROSTER_ROLES), limits=dict(api.LIMITS), environment=dict(api.ENVIRONMENT),
        expected_versions=dict(api.VERSIONS))
    api.validate_configuration(config)
    configuration = root/'authored-observation03-configuration.json'
    configuration.write_bytes(canonical(config, pretty=True))
    legacy = {p: (root/p).read_bytes() for p in inputs63}
    return root, api, config, configuration, legacy


def inside(tmp_path):
    root, api, config, configuration, legacy = make_project(tmp_path)
    config_sha = sha(configuration.read_bytes())
    observer_command = [PYTHON, '-I', '-S', '-B', str(root/OBSERVER), '--configuration', str(configuration), '--sha256', config_sha]
    code, out, err = command_capture(root, 'observer', observer_command)
    assert code == 0, (code, out, err)
    run = root/api.ROSTER_OUTPUT
    result = json.loads((run/'result.json').read_bytes())
    assert result['status'] == 'observed', result
    assert all(result[k] == v for k,v in api.CLAIMS.items())
    worker_raw = (run/'payload/imports.json').read_bytes()
    report = json.loads(worker_raw)
    assert report['kind'] == 'puck-runtime-import-characterization-result-v4'
    assert b'AUTHORED_\\u00e9' in worker_raw and 'AUTHORED_é'.encode() not in worker_raw
    rows = report['distributed_exports']['modules']
    assert [len(r['comparison']['expected']) for r in rows] == [11,69,29]
    assert rows[0]['comparison'] == dict(expected=rows[0]['comparison']['expected'], missing=[], extra=['AUTHORED_é'], matches=False)
    assert all(r['comparison']['matches'] for r in rows[1:])
    assert report['distributed_exports']['profile_accepted'] is False
    transport = root/(api.ROSTER_OUTPUT+'-external-cli-transport.json')
    auditor = load(root/AUDITOR, 'distributed_authored_auditor')
    before = len(os.listdir('/proc/self/fd'))
    verified = auditor.audit(str(configuration), config_sha, str(transport), sha(transport.read_bytes()))
    assert len(os.listdir('/proc/self/fd')) == before
    assert verified['source_pins'] == 19 and verified['input_pins'] == 63
    assert verified['site_file_count'] == 9 and verified['profile_accepted'] is False
    put(root, 'authored-evidence/api-audit.json', dict(authored_scope=SCOPE, verified=verified,
        fd_count_before=before, fd_count_after=len(os.listdir('/proc/self/fd'))))
    audit_command = [PYTHON, '-I', '-S', '-B', str(root/AUDITOR), '--configuration', str(configuration),
        '--sha256', config_sha, '--transport', str(transport), '--transport-sha256', sha(transport.read_bytes())]
    code, out, err = command_capture(root, 'audit-cli', audit_command)
    assert code == 0, (code, out, err)
    audit_report = json.loads(out)
    assert audit_report['status'] == 'PASS' and audit_report['ordinary_imports_observed'] is True
    assert all(audit_report[k] == v for k,v in api.CLAIMS.items())
    current_pin = next(r for r in config['sources'] if r['path'] == AUDITOR)
    assert current_pin['sha256'] == sha((root/AUDITOR).read_bytes())
    first = {p.relative_to(root).as_posix(): p.read_bytes() for p in run.rglob('*') if p.is_file()}
    first.update({p: (root/p).read_bytes() for p in (
        api.ROSTER_OUTPUT+'-external-cli.stdout', api.ROSTER_OUTPUT+'-external-cli.stderr',
        api.ROSTER_OUTPUT+'-external-cli-transport.json')})
    code, out, err = command_capture(root, 'observer-reentry-refused', observer_command)
    assert code != 0
    assert all((root/p).read_bytes() == raw for p,raw in first.items())
    # Rebind every public byte digest touched by a report mutation. The
    # independent semantic projection guard must still reject a false match.
    names = ('payload/imports.json', 'worker-logs/stdout.log', 'result.json')
    originals = {run/name: (run/name).read_bytes() for name in names}
    observed = json.loads(transport.read_bytes())
    external_stdout = root/observed['stdout']['path']
    originals.update({external_stdout: external_stdout.read_bytes(), transport: transport.read_bytes()})
    bad = copy.deepcopy(report); bad['distributed_exports']['modules'][0]['comparison']['matches'] = True
    bad_raw = canonical(bad); (run/'payload/imports.json').write_bytes(bad_raw)
    (run/'worker-logs/stdout.log').write_bytes(canonical(dict(report_sha256=sha(bad_raw), report_bytes=len(bad_raw), status='observed')))
    bad_result = dict(result, report_sha256=sha(bad_raw)); (run/'result.json').write_bytes(canonical(bad_result))
    external_stdout.write_bytes((json.dumps(bad_result, sort_keys=True)+'\n').encode())
    observed['stdout'].update(size_bytes=external_stdout.stat().st_size, sha256=sha(external_stdout.read_bytes()))
    transport.write_bytes(canonical(observed, ascii=False))
    refused = None
    try:
        auditor.audit(str(configuration), config_sha, str(transport), sha(transport.read_bytes()))
    except (ValueError, RuntimeError) as error:
        refused = str(error)
    finally:
        for path, raw in originals.items(): path.write_bytes(raw)
    assert refused and 'comparison' in refused.lower(), refused
    put(root, 'authored-evidence/rebound-semantic-refusal.json', dict(authored_scope=SCOPE, error=refused,
        report_sha256=sha(bad_raw), all_public_hashes_rebound=True))
    assert all((root/p).read_bytes() == raw for p,raw in legacy.items())
    assert all((root/p).read_bytes() == raw for p,raw in first.items())
    assert len(os.listdir('/proc/self/fd')) == before
    put(root, 'authored-evidence/complete.json', dict(authored_scope=SCOPE, status='PASS',
        sources=19, inputs=63, authored_site_files=9, comparisons=[r['comparison'] for r in rows],
        observer_exit=0, auditor_cli_exit=0, reentry_refused=True, rebound_semantics_refused=True,
        historical_bytes_preserved=True, fd_count_before=before, fd_count_after=before,
        private_tmpfs_lifetime='outer namespace', actual_vendor_imports=False, actual_allocation=False))


def test_authored_distributed_observation_observer_and_independent_auditor(tmp_path):
    assert tmp_path.is_relative_to(ROOT/'runs'), 'Use persistent runs/ --basetemp for the authored project'
    seed = ("import importlib.util,sys;sys.path[:0]=[sys.argv[1]+'/tests',sys.argv[1]+'/src'];"
            "s=importlib.util.spec_from_file_location('authored_distributed_integration',sys.argv[2]);"
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
            "m.inside(m.Path(sys.argv[3]))")
    command = ['/usr/bin/bwrap', '--unshare-user', '--die-with-parent', '--ro-bind', '/', '/',
        '--bind', str(tmp_path), str(tmp_path), '--tmpfs', '/tmp', '--dev', '/dev', '--proc', '/proc',
        '--chdir', str(ROOT), sys.executable, '-I', '-S', '-B', '-c', seed,
        str(ROOT), str(Path(__file__).resolve()), str(tmp_path)]
    start = time.monotonic()
    process = subprocess.run(command, capture_output=True, timeout=120,
        env=dict(PATH='/usr/bin:/bin', LANG='C.UTF-8', LC_ALL='C.UTF-8', PYTHONDONTWRITEBYTECODE='1'))
    put(tmp_path, 'outer.stdout', process.stdout); put(tmp_path, 'outer.stderr', process.stderr)
    put(tmp_path, 'outer-result.json', dict(authored_scope=SCOPE, command=command,
        observed_returncode=process.returncode, elapsed_seconds=time.monotonic()-start,
        stdout_sha256=sha(process.stdout), stderr_sha256=sha(process.stderr)))
    assert process.returncode == 0, (process.returncode, process.stdout, process.stderr)
    complete = json.loads((tmp_path/'authored-project/authored-evidence/complete.json').read_bytes())
    assert complete['status'] == 'PASS' and complete['actual_vendor_imports'] is False
