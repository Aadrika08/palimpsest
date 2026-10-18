#!/usr/bin/env python3
"""Independent CPU characterization02 outcome/byte audit; no vendor execution."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import stat
import sys
import time
import types

BASE = Path('/home/utkarsh/.codex/worktrees/0071/brain')
RUN = BASE / 'runs/puck-cpu-runtime-characterization-02'
CONFIG = BASE / 'docs/plans/puck-cpu-runtime-characterization-02.json'
OUTPUT = Path('/tmp/palimpsest-cpu-characterization-audit-02.json')
PRIOR = 'docs/reports/puck-cpu-characterization-01'
PRIOR_PINS = {PRIOR+'/frozen-configuration.json': 'b11daf4719daf3a838ece18cf6c0604875d3fcba65b0ab0b5354b9428be6b8ca',
    PRIOR+'/raw/result.json': 'bd700625635bd47a170b70ce955097c47c0e4a27c1c3d9a04c137461d848288a',
    PRIOR+'/failure-audit-01.json': '26dd167d4d06ce4a8d45598a06dcd5c0e5a6c1b171550cfa11c0b039b655fbf9'}
NATIVE_SHA = '64a9e46f60700f12712262879547fbf26d785fb8a825098940e6494482dae2aa'
SUPPORT = (('/tmp/palimpsest_cpu_characterization_audit_v1.py', 'ba1f54b2885901cae837bb710bb725e211d5aaf5fcddb8fc6bfeb786f2daac4e'),
    ('/tmp/palimpsest_cpu_install_audit_v1.py', 'a8945d3dc432831522e66c7817c0f3281e278e2a930ab1e31cbb14a26e17e406'),
    ('/tmp/palimpsest_cpu_retained_admission_audit_v3.py', 'f6229e92238f260e001b6e49cf545dcddd9a371fb272118881fbec8b38961469'))
VERSIONS = dict(numpy='2.2.5', torch='2.9.0+cpu', torchvision='0.24.0+cpu', mujoco='3.3.6')
FALSE = dict(runtime_qualified=False, native_authorized=False, study_authorized=False,
             collection_authorized=False, executable=False, qualification_claims=[])
ENVIRONMENT = dict(PYTHONDONTWRITEBYTECODE='1', LC_ALL='C.UTF-8', LANG='C.UTF-8', HOME='/scratch/home',
    TMPDIR='/scratch/tmp', PWD='/scratch', PATH='/nonexistent', TZ='UTC', CUDA_VISIBLE_DEVICES='', MUJOCO_GL='egl',
    PYOPENGL_PLATFORM='egl', MPLBACKEND='Agg', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1', GOTOBLAS_MAIN_FREE='1', TORCH_DEVICE_BACKEND_AUTOLOAD='0')
LIMITS = dict(normal_seconds=180, child_hard_seconds=190, hard_seconds=195, rss_bytes=1536 << 20,
    address_space_bytes=8192 << 20, output_bytes=64 << 20, scratch_bytes=64 << 20, file_bytes=8 << 20,
    min_free_bytes=4096 << 20, min_available_ram_bytes=2048 << 20, max_processes=3, max_fds=40000)

def support():
    modules, stamps = [], []
    for filename, digest in SUPPORT:
        path = Path(filename); info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1 << 20:
            raise ValueError('unbounded or linked support source')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest: raise ValueError('reviewed support changed')
        module = types.ModuleType(path.stem); module.__file__ = filename; sys.modules[path.stem] = module
        # Authenticate and compile source directly; never consult inherited bytecode.
        exec(compile(raw, filename, 'exec'), module.__dict__)
        modules.append(module); stamps.append((path, info))
    p, a, r = modules; p.a, p.r = a, r
    for path, info in stamps: p.remember(path, a.fingerprint(info))
    return p, a, r

def finite(value, limit): return type(value) in (int, float) and math.isfinite(value) and 0 <= value < limit
def claims(value): p.false_claims(value)
def aliases(rows):
    for filename, target in rows:
        path = Path(filename); info = path.lstat()
        a.require(stat.S_ISLNK(info.st_mode) and os.readlink(path) == target, 'alias changed: '+filename)
        p.remember(path, a.fingerprint(info))

def missing():
    paths = [BASE/'runs/puck-cpu-runtime-characterization-01/baseline-after.json']
    for allocation, leaves in (('puck-cpu-install-01', ('inventory.json', 'licences.json', 'baseline-after.json', 'logs/namespace.json')),
                               ('puck-cpu-retained-admission-01', ('inventory.json', 'snapshot.json', 'baseline-after.json'))):
        paths.extend(BASE/'runs'/allocation/leaf for leaf in leaves)
    a.require(all(not os.path.lexists(path) for path in paths), 'old missing receipt filled')
    return len(paths)

def audit(digest, success):
    config = r.validate_configuration(p.read(CONFIG, 1 << 20), p.read(RUN/'configuration.json', 1 << 20), digest)
    a.require(config['kind'] == 'puck-cpu-runtime-characterization-v1' and type(config['version']) is int and config['version'] == 1
        and config['output'] == str(RUN.relative_to(BASE)) and config['site_root'] == 'runs/puck-cpu-install-01/site'
        and config['expected_versions'] == VERSIONS and config['environment'] == ENVIRONMENT and config['limits'] == LIMITS,
        'frozen02 configuration contract differs')
    a.require(len(config['sources']) == 14 and len(config['inputs']) == 42, '02 source/input counts differ')
    pins = {}
    for row in config['sources'] + config['inputs']:
        path = a.canonical(row['path']); a.require(path not in pins, 'duplicate pin')
        p.hashed(BASE/path, p.metadata(row)); pins[path] = row
    roles = config['roles']; a.require(len(roles) == 12 and all(path in pins for path in roles.values()), '12 pinned roles required')
    get = lambda role: p.load(BASE/roles[role])
    a.require(roles['native_metadata'] == 'docs/plans/puck-cpu-characterization-native-metadata-05.json'
        and roles['prior_configuration'] == PRIOR+'/frozen-configuration.json' and roles['prior_result'] == PRIOR+'/raw/result.json'
        and roles['prior_audit'] == PRIOR+'/failure-audit-01.json', '02 historical/native role differs')
    accepted, old, proof, snapshot = (get(k) for k in ('accepted_configuration', 'accepted_result', 'accepted_audit', 'accepted_snapshot'))
    a.require(pins[roles['accepted_configuration']]['sha256'] == p.ACCEPTED_SHA and old['status'] == proof['status'] == 'PASS'
        and old['claims']['package_preparation_accepted'] is proof['package_preparation_accepted'] is True
        and old['configuration_sha256'] == proof['verified']['configuration_sha256'] == p.ACCEPTED_SHA
        and old['snapshot_sha256'] == pins[roles['accepted_snapshot']]['sha256'], 'accepted preparation binding differs')
    for key in ('runtime_qualified', 'numerical_imports_executed', 'study_authorized', 'collection_authorized'):
        a.require(old['claims'][key] is proof[key] is False, 'package preparation overclaims qualification')
    prior_config, prior_result, prior_audit = (get(k) for k in ('prior_configuration', 'prior_result', 'prior_audit'))
    for path, expected in PRIOR_PINS.items(): a.require(pins[path]['sha256'] == expected, '01 failure identity differs')
    claims(prior_result); claims(prior_audit)
    a.require(prior_result['status'] == 'FAIL' and prior_audit['status'] == 'PRESERVED_FAILURE_VERIFIED'
        and prior_audit['ordinary_imports_observed'] is False and prior_audit['native_qualified'] is False
        and prior_result['configuration_sha256'] == PRIOR_PINS[roles['prior_configuration']], '01 failure scope differs')
    a.require(len(accepted['sources']) == 16 and len(prior_config['sources']) == 14, 'historical capsule counts differ')
    required = set(roles.values())
    for configuration, archive in ((accepted, p.ARCHIVE), (prior_config, PRIOR)):
        for row in configuration['sources']:
            path = archive+'/source/'+row['path']; required.add(path)
            a.require(path in pins and p.metadata(pins[path]) == p.metadata(row), 'historical capsule changed')
    a.require(required == {row['path'] for row in config['inputs']}, 'exact42 input boundary differs')
    inventory, layout, native, baseline = (get(k) for k in ('inventory', 'layout', 'native_metadata', 'baseline'))
    site = BASE/config['site_root']; actual, directories, stamps = r.census(site)
    a.require(actual == r.rows_to_map(inventory['entries']) and directories == set(layout['predicted_destination_directories'])
        and snapshot['site_root'] == str(site) and len(actual) == 27225 and len(directories) == 2074
        and sum(v['size_bytes'] for v in actual.values()) == 1304701872, 'complete accepted SITE differs')
    a.require(pins[roles['native_metadata']]['sha256'] == NATIVE_SHA and native['kind'] == 'puck-cpu-characterization-native-metadata-v5'
        and native['status'] == 'COMPLETE' and native['root_scope'] == 'installed_shared_objects_and_interpreter'
        and native['required_missing_names'] == native['errors'] == native['oversized_native_files'] == []
        and len(native['native_files']) == 29 and len(native['aliases']) == 23 and native['system_ELF_count_including_prefix'] == 39
        and len([row for row in native['dependency_edges'] if row.get('needed') == 'libz.so.1']) == 17
        and any(row['needed'] == 'libcrypt.so.1' for row in native['optional_prefix_missing']), 'native05 scope/closure differs')
    for key in ('numerical_imports_executed', 'target_execution_performed', 'runtime_qualified', 'renderer_qualified'):
        a.require(native[key] is False, 'static metadata overclaims execution')
    for row in native['native_files']: p.hashed(Path(row['path']), p.metadata(row), single_link=False, limit=64 << 20)
    aliases(native['aliases'] + baseline['host_path_aliases'])
    for row in baseline['external_libraries'] + [baseline['bwrap_executable']]:
        p.hashed(Path(row.get('realpath') or row['path']), dict(size_bytes=row['size'], sha256=row['sha256']), single_link=False, limit=64 << 20)
    prefix = Path(baseline['python_prefix']); a.require(len(baseline['files']) == 4233 and len(baseline['symlinks']) == 1048, 'baseline counts differ')
    for relative, size, sha in baseline['files']: p.hashed(prefix/a.canonical(relative), dict(size_bytes=size, sha256=sha))
    aliases([(str(prefix/a.canonical(relative)), target) for relative, target in baseline['symlinks']])
    summary = dict(prefix_manifest_sha256=baseline['prefix_manifest_sha256'], regular_file_count=4233, symlink_count=1048,
        regular_file_bytes=sum(row[1] for row in baseline['files']), external_file_count=len(baseline['external_libraries'])+1)
    a.require(p.load(RUN/'baseline-before.json') == summary, 'prelaunch baseline differs')
    after_present = os.path.lexists(RUN/'baseline-after.json')
    if after_present: a.require(p.load(RUN/'baseline-after.json') == summary, 'postlaunch baseline differs')
    namespace = dict(kind='cpu-characterization-namespace-v1', network_isolated=True, site_readonly=True, project_hidden=True, private_pycache_empty=True)
    a.require(p.load(RUN/'namespace.json') == namespace == json.loads(p.read(RUN/'probe-logs/stdout.log')), 'namespace probe differs')
    request_raw = p.read(RUN/'request.json', 65536); request = json.loads(request_raw)
    a.require(request_raw == p.canonical(request) and request == dict(kind='puck-runtime-import-characterization-v2', version=2,
        site_root=str(site), output_root='/output', environment=ENVIRONMENT, expected_versions=VERSIONS, pycache_prefix='/scratch/pycache'), '02 request differs')
    supervisors = {}
    for name in ('probe', 'worker'):
        observed = p.load(RUN/(name+'-supervision.json')); supervisors[name] = observed
        a.require(observed['matching_survivors'] == [] and observed['rss_sampling_seconds'] == .05
            and type(observed['sampled_peak_rss_bytes']) is int and observed['sampled_peak_rss_bytes'] >= 0, 'supervision/closure differs')
        normal = observed['returncode'] == 0 and observed['failure'] is None
        a.require(observed['status'] == ('completed' if normal else 'failed'), 'supervision status differs')
        if name == 'probe' or success: a.require(normal and observed['sampled_peak_rss_bytes'] <= LIMITS['rss_bytes'], 'normal supervision required')
        invocation = p.load(RUN/(name+'-invocation.json')); command = invocation['command']
        a.require(invocation['configuration_sha256'] == digest and command[0] == '/usr/bin/bwrap'
            and all(flag in command for flag in ('--unshare-all', '--disable-userns', '--clearenv', '--remount-ro', '-I', '-S', '-B'))
            and 'pycache_prefix=/scratch/pycache' in command, 'namespace invocation differs')
        for leaf in ('stdout.log', 'stderr.log'): p.read(RUN/(name+'-logs')/leaf, 8 << 20)
    report_raw = p.read(RUN/'payload/imports.json', 1 << 20); report = json.loads(report_raw); claims(report)
    report_sha = hashlib.sha256(report_raw).hexdigest()
    a.require(report['kind'] == 'puck-runtime-import-characterization-result-v3' and report['version'] == 3
        and report['profile'] == 'cpu-four-imports-v1' and report['expected_versions'] == VERSIONS
        and report['request_sha256'] == hashlib.sha256(request_raw).hexdigest()
        and report['source_sha256'] == pins['scripts/characterize_puck_runtime_imports.py']['sha256']
        and report['environment_sha256'] == hashlib.sha256(p.canonical(ENVIRONMENT)).hexdigest()
        and report['pycache_prefix'] == '/scratch/pycache' and finite(report['seconds'], 195), 'worker report binding differs')
    a.require(json.loads(p.read(RUN/'worker-logs/stdout.log')) == dict(report_sha256=report_sha, report_bytes=len(report_raw), status=report['status']), 'worker receipt differs')
    if success:
        a.require(report['status'] == 'observed' and report['versions'] == VERSIONS and report['observation_scope'] == 'completed_imports'
            and report['environment_delta'] is None and report['observation_errors'] == [] and 'error' not in report
            and [row['name'] for row in report['imports']] == list(VERSIONS)
            and all(row['status'] == 'observed' and finite(row['seconds'], 180) and row['cache_entries'] <= 8192 for row in report['imports']), 'four completed exact imports required')
    else:
        a.require(report['status'] in ('observed', 'failed'), 'unrecognized failure-phase worker status')
        if report['status'] == 'failed': a.require(isinstance(report.get('error'), dict), 'failed worker lacks error')
    if success or report['cache'] is not None:
        cache = report['cache']; a.require(cache['cache_entries'] == len(cache['modules']) <= 8192
            and 0 <= cache['attribute_edges'] <= 262144 and cache['export_scope'] == 'exceptional_cache_identities', 'cache scope/bounds')
    for key in ('baseline_maps', 'maps'):
        value = report[key]
        if value is None and not success: continue
        a.require(0 <= value['map_bytes'] <= 4 << 20 and 0 <= value['map_lines'] <= 65536 and len(value['images']) <= 65536
            and value['persistent_snapshot_only'] is True and value['transient_anonymous_jit_closure_qualified'] is False, 'map scope/bounds')
    if 'error_chain' in report:
        chain = report['error_chain']; a.require(len(chain['entries']) <= 8 and type(chain['complete']) is bool
            and chain['truncation'] in (None, 'cycle', 'depth', 'diagnostic_error')
            and all(type(row['message']) is str and len(row['message']) <= 2048 and row['via'] in ('raised', 'cause', 'context') for row in chain['entries']), 'error chain bounds')
    result_raw = p.read(RUN/'result.json'); result = json.loads(result_raw); claims(result)
    a.require(result['kind'] == 'puck-cpu-characterization-outcome-v1' and result['configuration_sha256'] == digest
        and finite(result['elapsed_seconds'], 180 if success else 195), 'parent outcome binding/time differs')
    closure = result['closure']; a.require(closure['active_children'] == closure['active_non_main_threads'] == []
        and closure['all_handles_closed'] is closure['all_receipts_fsynced'] is True and type(closure['fd_count_before']) is int
        and closure['fd_count_before'] == closure['fd_count_after'], 'parent closure differs')
    if success:
        a.require(result['status'] == 'observed' and not any(k in result for k in ('error', 'error_type')) and after_present
            and result['report_sha256'] == report_sha and result['versions'] == VERSIONS and result['namespace_probe_completed'] is True
            and result['accepted_package_preparation_preserved'] is True and result['worker_supervision_status'] == 'completed'
            and 0 <= result['sampled_parent_peak_rss_bytes'] <= LIMITS['rss_bytes'], 'normal parent success required')
    else: a.require(result['status'] == 'FAIL' and type(result.get('error')) is str and type(result.get('error_type')) is str, 'parent failure required')
    for path, sha in (('runs/puck-cpu-install-01/result.json', r.ORIGINAL_SHA), ('runs/puck-cpu-retained-admission-01/result.json', r.PRIOR_ADMISSION_SHA)):
        raw = p.read(BASE/path); a.require(hashlib.sha256(raw).hexdigest() == sha and json.loads(raw)['status'] == 'FAIL', 'old failure changed')
    missing(); _, after_dirs, after_stamps = r.census(site, hashes=False)
    a.require(after_dirs == directories and after_stamps == stamps, 'SITE file/directory fingerprints changed')
    for path, stamp in p.STAMPS.items(): a.require(a.fingerprint(path.lstat()) == stamp, 'input/receipt changed during audit')
    a.require(os.path.lexists(RUN/'baseline-after.json') == after_present and missing() == 8, 'receipt absence changed')
    return dict(configuration_sha256=digest, source_pins=14, input_pins=42, accepted_source_capsules=16, prior_source_capsules=14,
        site_file_count=27225, site_directory_count=2074, site_regular_file_bytes=1304701872, native_files=29, native_aliases=23,
        baseline_declared_files=4233, baseline_declared_symlinks=1048, receipt_fingerprints=len(p.STAMPS), old_missing_receipts=8,
        worker_status=report['status'], worker_returncode=supervisors['worker']['returncode'], parent_status=result['status'],
        report_sha256=report_sha, result_sha256=hashlib.sha256(result_raw).hexdigest(), baseline_after_present=after_present,
        scope='ordinary trusted imports/persistent snapshots or preserved failure; no held/native/render qualification')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration-sha256', required=True)
    parser.add_argument('--expected-outcome', choices=('success', 'failure'), required=True)
    parser.add_argument('--parent-exit-code', type=int, choices=(0, 1), required=True)
    args = parser.parse_args(); started = time.monotonic(); success = args.expected_outcome == 'success'
    if os.path.lexists(OUTPUT): raise ValueError('fresh02 audit output required')
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode): raise ValueError('auditor requires -I -S -B')
    if (args.parent_exit_code != (0 if success else 1) or len(args.configuration_sha256) != 64
            or any(c not in '0123456789abcdef' for c in args.configuration_sha256)): raise ValueError('explicit terminal/config contract differs')
    report = dict(kind='cpu-characterization-independent-outcome-audit-v2', status='FAIL', ordinary_imports_observed=False,
        native_qualified=False, target_code_executed_by_auditor=False, expected_outcome=args.expected_outcome,
        caller_supplied_observed_parent_exit_code=args.parent_exit_code, **FALSE)
    def expired(_signal, _frame): raise TimeoutError('180-second independent02 audit deadline')
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, 180)
    global p, a, r
    try:
        p, a, r = support(); report['verified'] = audit(args.configuration_sha256, success)
        if not finite(time.monotonic()-started, 180): raise TimeoutError('late independent02 audit')
        report.update(status='PASS' if success else 'PRESERVED_FAILURE_VERIFIED', ordinary_imports_observed=success)
    except Exception as error: report['error'] = type(error).__name__+': '+str(error)
    report['elapsed_seconds'] = time.monotonic()-started
    raw = (json.dumps(report, sort_keys=True, indent=2)+'\n').encode()
    with OUTPUT.open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(dict(path=str(OUTPUT), status=report['status'], sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))), flush=True)
    if not finite(time.monotonic()-started, 180): raise TimeoutError('late independent02 publication/terminal')
    signal.setitimer(signal.ITIMER_REAL, 0)
    return 0 if report['status'] in ('PASS', 'PRESERVED_FAILURE_VERIFIED') else 1

if __name__ == '__main__': raise SystemExit(main())
