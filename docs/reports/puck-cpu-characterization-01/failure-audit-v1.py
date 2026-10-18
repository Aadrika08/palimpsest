#!/usr/bin/env python3
"""Preserve CPU characterization01 failure; inspect inert files, never target code."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import stat
import sys
import time

BASE = Path('/home/utkarsh/.codex/worktrees/0071/brain')
RUN = BASE / 'runs/puck-cpu-runtime-characterization-01'
CONFIG = BASE / 'docs/plans/puck-cpu-runtime-characterization-01.json'
CONFIG_SHA = 'b11daf4719daf3a838ece18cf6c0604875d3fcba65b0ab0b5354b9428be6b8ca'
PARKED = Path('/tmp/palimpsest_cpu_characterization_audit_v1.py')
PARKED_SHA = 'ba1f54b2885901cae837bb710bb725e211d5aaf5fcddb8fc6bfeb786f2daac4e'
OUTPUT = Path('/tmp/palimpsest-cpu-characterization-failure-audit-01.json')
REPORT_SHA = '726ae7250a2d5b89dfabb5663847b4360f7fa2784a2864004bf971945b8c111d'
RESULT_SHA = 'bd700625635bd47a170b70ce955097c47c0e4a27c1c3d9a04c137461d848288a'
VERSIONS = dict(numpy='2.2.5', torch='2.9.0+cpu', torchvision='0.24.0+cpu', mujoco='3.3.6')
FALSE = dict(runtime_qualified=False, native_authorized=False, study_authorized=False,
             collection_authorized=False, executable=False, qualification_claims=[])

def support():
    raw = PARKED.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PARKED_SHA: raise ValueError('parked auditor changed')
    spec = importlib.util.spec_from_file_location('cpu_characterization_support', PARKED)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    # Definitions and reviewed low-level helpers only: never call any old audit/main.
    module.a, module.r = module.helpers()
    return module, module.a, module.r

def finite(value, maximum):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value < maximum

def aliases(rows):
    for filename, target in rows:
        path = Path(filename); info = path.lstat()
        a.require(stat.S_ISLNK(info.st_mode) and os.readlink(path) == target, 'alias changed: ' + filename)
        p.remember(path, a.fingerprint(info))

def claims(value):
    a.require(all(value.get(key) is False for key in FALSE if key != 'qualification_claims')
              and value.get('qualification_claims') == [], 'failure granted authority')

def absences():
    absent = [RUN / 'baseline-after.json']
    for allocation, leaves in (('puck-cpu-install-01', ('inventory.json', 'licences.json', 'baseline-after.json', 'logs/namespace.json')),
                               ('puck-cpu-retained-admission-01', ('inventory.json', 'snapshot.json', 'baseline-after.json'))):
        absent.extend(BASE / 'runs' / allocation / leaf for leaf in leaves)
    a.require(all(not os.path.lexists(path) for path in absent), 'missing historical/postfailure receipt filled')
    return len(absent)

def audit():
    raw = p.read(CONFIG, 1 << 20)
    config = r.validate_configuration(raw, p.read(RUN / 'configuration.json', 1 << 20), CONFIG_SHA)
    a.require(len(raw) == 9898 and config['kind'] == 'puck-cpu-runtime-characterization-v1'
              and type(config['version']) is int and config['version'] == 1
              and config['output'] == str(RUN.relative_to(BASE)) and config['site_root'] == 'runs/puck-cpu-install-01/site'
              and config['expected_versions'] == VERSIONS, 'frozen configuration mismatch')
    a.require(config['limits'] == dict(normal_seconds=180, child_hard_seconds=190, hard_seconds=195,
        rss_bytes=1536 << 20, address_space_bytes=8192 << 20, output_bytes=64 << 20, scratch_bytes=64 << 20,
        file_bytes=8 << 20, min_free_bytes=4096 << 20, min_available_ram_bytes=2048 << 20,
        max_processes=3, max_fds=40000), 'resource limits changed')
    a.require(len(config['sources']) == 14 and len(config['inputs']) == 25, 'frozen pin counts changed')
    pins = {}
    for row in config['sources'] + config['inputs']:
        path = a.canonical(row['path']); a.require(path not in pins, 'duplicate pin')
        p.hashed(BASE / path, p.metadata(row)); pins[path] = row
    roles = config['roles']; a.require(len(roles) == 9 and all(v in pins for v in roles.values()), 'role pins missing')
    get = lambda role: p.load(BASE / roles[role])
    accepted, old, proof, snapshot = (get(role) for role in ('accepted_configuration', 'accepted_result', 'accepted_audit', 'accepted_snapshot'))
    a.require(pins[roles['accepted_configuration']]['sha256'] == p.ACCEPTED_SHA
              and old['status'] == proof['status'] == 'PASS' and old['claims']['package_preparation_accepted'] is True
              and proof['package_preparation_accepted'] is True and old['configuration_sha256'] == p.ACCEPTED_SHA
              and proof['verified']['configuration_sha256'] == p.ACCEPTED_SHA
              and old['snapshot_sha256'] == pins[roles['accepted_snapshot']]['sha256'], 'accepted preparation chain differs')
    for key in ('runtime_qualified', 'numerical_imports_executed', 'study_authorized', 'collection_authorized'):
        a.require(old['claims'][key] is proof[key] is False, 'prior package preparation overclaims qualification')
    a.require(len(accepted['sources']) == 16, 'historical source capsule count')
    for row in accepted['sources']:
        archived = p.ARCHIVE + '/source/' + row['path']
        a.require(archived in pins and p.metadata(pins[archived]) == p.metadata(row), 'historical source capsule changed')
    inventory, layout, native, baseline = (get(role) for role in ('inventory', 'layout', 'native_metadata', 'baseline'))
    site = BASE / config['site_root']; actual, directories, stamps = r.census(site)
    a.require(actual == r.rows_to_map(inventory['entries']) and directories == set(layout['predicted_destination_directories'])
              and snapshot['site_root'] == str(site) and len(actual) == 27225 and len(directories) == 2074
              and sum(v['size_bytes'] for v in actual.values()) == 1304701872, 'accepted complete SITE differs')
    a.require(pins[roles['native_metadata']]['sha256'] == '451e6af507c6e7d181f253430145053f9eaa9404496f8b97cb27d33ec6e88066'
              and native['kind'] == 'puck-cpu-characterization-native-metadata-v4' and native['status'] == 'COMPLETE'
              and native['root_scope'] == 'installed_shared_objects_and_interpreter'
              and native['required_missing_names'] == native['errors'] == native['oversized_native_files'] == []
              and len(native['native_files']) == 28 and len(native['aliases']) == 22
              and native['installed_DSO_count'] <= 512 and native['system_ELF_count_including_prefix'] <= 128, 'native metadata differs')
    for key in ('numerical_imports_executed', 'target_execution_performed', 'runtime_qualified', 'renderer_qualified'):
        a.require(native[key] is False, 'static native metadata overclaims execution')
    for row in native['native_files']: p.hashed(Path(row['path']), p.metadata(row), single_link=False, limit=64 << 20)
    aliases(native['aliases'] + baseline['host_path_aliases'])
    for row in baseline['external_libraries'] + [baseline['bwrap_executable']]:
        p.hashed(Path(row.get('realpath') or row['path']), dict(size_bytes=row['size'], sha256=row['sha256']), single_link=False, limit=64 << 20)
    prefix = Path(baseline['python_prefix'])
    for relative, size, digest in baseline['files']:
        p.hashed(prefix / a.canonical(relative), dict(size_bytes=size, sha256=digest))
    aliases([(str(prefix / a.canonical(relative)), target) for relative, target in baseline['symlinks']])
    summary = dict(prefix_manifest_sha256=baseline['prefix_manifest_sha256'], regular_file_count=len(baseline['files']),
        symlink_count=len(baseline['symlinks']), regular_file_bytes=sum(row[1] for row in baseline['files']),
        external_file_count=len(baseline['external_libraries']) + (baseline['bwrap_executable'] is not None))
    a.require(p.load(RUN / 'baseline-before.json') == summary, 'prelaunch baseline receipt differs')
    namespace = dict(kind='cpu-characterization-namespace-v1', network_isolated=True, site_readonly=True, project_hidden=True, private_pycache_empty=True)
    a.require(p.load(RUN / 'namespace.json') == namespace == json.loads(p.read(RUN / 'probe-logs/stdout.log')), 'namespace probe differs')
    request_raw = p.read(RUN / 'request.json', 65536); request = json.loads(request_raw)
    a.require(request_raw == p.canonical(request) and request == dict(kind='puck-runtime-import-characterization-v2', version=2,
        site_root=str(site), output_root='/output', environment=config['environment'], expected_versions=VERSIONS,
        pycache_prefix='/scratch/pycache'), 'worker request differs')
    for name, status, returncode in (('probe', 'completed', 0), ('worker', 'failed', 1)):
        observed = p.load(RUN / (name + '-supervision.json'))
        a.require(observed['status'] == status and observed['returncode'] == returncode and observed['failure'] is None
                  and observed['matching_survivors'] == [] and observed['rss_sampling_seconds'] == .05
                  and type(observed['pid']) is int and observed['pid'] > 0
                  and type(observed['sampled_peak_rss_bytes']) is int
                  and 0 <= observed['sampled_peak_rss_bytes'] <= config['limits']['rss_bytes'], 'supervised terminal differs')
        invocation = p.load(RUN / (name + '-invocation.json')); command = invocation['command']
        a.require(invocation['configuration_sha256'] == CONFIG_SHA and command[0] == '/usr/bin/bwrap'
                  and all(flag in command for flag in ('--unshare-all', '--disable-userns', '--clearenv', '--remount-ro', '-I', '-S', '-B'))
                  and 'pycache_prefix=/scratch/pycache' in command, 'frozen invocation differs')
        for leaf in ('stdout.log', 'stderr.log'): p.read(RUN / (name + '-logs') / leaf, 8 << 20)
    report_raw = p.read(RUN / 'payload/imports.json', 1 << 20); report = json.loads(report_raw)
    a.require(len(report_raw) == 19975 and hashlib.sha256(report_raw).hexdigest() == REPORT_SHA
              and report['kind'] == 'puck-runtime-import-characterization-result-v3' and report['version'] == 3
              and report['profile'] == 'cpu-four-imports-v1' and report['status'] == 'failed'
              and report['observation_scope'] == 'post_failure' and report['expected_versions'] == VERSIONS
              and report['versions'] == {} and report['imports'] == [dict(name='numpy', status='failed')]
              and report['request_sha256'] == hashlib.sha256(request_raw).hexdigest()
              and report['source_sha256'] == pins['scripts/characterize_puck_runtime_imports.py']['sha256']
              and report['environment_sha256'] == hashlib.sha256(p.canonical(config['environment'])).hexdigest()
              and report['pycache_prefix'] == '/scratch/pycache' and report['environment_delta'] is None
              and report['observation_errors'] == [] and report['error']['type'] == 'builtins.ImportError'
              and finite(report['seconds'], 180), 'preserved first-import failure differs')
    claims(report)
    cache = report['cache']
    a.require(cache['cache_entries'] == len(cache['modules']) <= 8192 and 0 <= cache['attribute_edges'] <= 262144
              and cache['export_scope'] == 'exceptional_cache_identities', 'postfailure cache bounds')
    for key in ('baseline_maps', 'maps'):
        value = report[key]
        a.require(0 <= value['map_bytes'] <= 4 << 20 and 0 <= value['map_lines'] <= 65536 and len(value['images']) <= 65536
                  and value['persistent_snapshot_only'] is True and value['transient_anonymous_jit_closure_qualified'] is False, 'map snapshot scope/bounds')
    a.require(json.loads(p.read(RUN / 'worker-logs/stdout.log')) == dict(report_sha256=REPORT_SHA, report_bytes=len(report_raw), status='failed'), 'worker publication receipt differs')
    result_raw = p.read(RUN / 'result.json'); result = json.loads(result_raw); claims(result)
    a.require(hashlib.sha256(result_raw).hexdigest() == RESULT_SHA and result['kind'] == 'puck-cpu-characterization-outcome-v1'
              and result['status'] == 'FAIL' and result['configuration_sha256'] == CONFIG_SHA
              and result['error_type'] == 'RuntimeError' and result['error'] == 'CPU worker did not complete normally'
              and result['elapsed_seconds'] == 8.909677214978728 and finite(result['elapsed_seconds'], 180)
              and 0 <= result['sampled_parent_peak_rss_bytes'] <= config['limits']['rss_bytes']
              and all(key not in result for key in ('versions', 'report_sha256', 'accepted_package_preparation_preserved', 'namespace_probe_completed')), 'parent retained failure differs')
    a.require(result['closure'] == dict(active_children=[], active_non_main_threads=[], all_handles_closed=True,
        all_receipts_fsynced=True, fd_count_before=5, fd_count_after=5), 'parent closure differs')
    for path, digest in (('runs/puck-cpu-install-01/result.json', r.ORIGINAL_SHA), ('runs/puck-cpu-retained-admission-01/result.json', r.PRIOR_ADMISSION_SHA)):
        raw = p.read(BASE / path)
        a.require(hashlib.sha256(raw).hexdigest() == digest and json.loads(raw)['status'] == 'FAIL', 'prior failure changed')
    absent_count = absences()
    _, after_dirs, after_stamps = r.census(site, hashes=False)
    a.require(after_dirs == directories and after_stamps == stamps, 'SITE file/directory fingerprints changed during audit')
    for path, stamp in p.STAMPS.items(): a.require(a.fingerprint(path.lstat()) == stamp, 'input changed during audit: ' + str(path))
    a.require(absences() == absent_count, 'receipt absence changed')
    return dict(configuration_sha256=CONFIG_SHA, source_pins=14, input_pins=25, archived_acceptance_source_pins=16,
        site_file_count=len(actual), site_directory_count=len(directories), site_regular_file_bytes=1304701872,
        native_files=len(native['native_files']), native_aliases=len(native['aliases']), baseline_declared_file_pins=len(baseline['files']),
        baseline_declared_symlinks=len(baseline['symlinks']), receipt_fingerprints=len(p.STAMPS), absent_receipts=absent_count,
        worker_returncode=1, worker_failure=None, first_import='numpy', reported_error_type=report['error']['type'],
        worker_report_sha256=REPORT_SHA, parent_result_sha256=RESULT_SHA,
        limitation='reported outer ImportError only; no causal diagnosis or held/native/render qualification',
        baseline_scope='prelaunch full-prefix summary; current declared baseline files/aliases verified; no fabricated after receipt')

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.parse_args()
    if os.path.lexists(OUTPUT): raise ValueError('fresh failure-audit output required')
    started = time.monotonic()
    report = dict(kind='cpu-characterization-independent-failure-audit-v1', status='FAIL',
        ordinary_imports_observed=False, native_qualified=False, target_code_executed_by_auditor=False, **FALSE)
    def expired(_signal, _frame): raise TimeoutError('180-second independent failure audit deadline')
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, 180)
    global p, a, r
    try:
        p, a, r = support(); report['verified'] = audit()
        if not finite(time.monotonic() - started, 180): raise TimeoutError('late independent failure audit')
        report['status'] = 'PRESERVED_FAILURE_VERIFIED'
    except Exception as error: report['error'] = type(error).__name__ + ': ' + str(error)
    report['elapsed_seconds'] = time.monotonic() - started
    raw = (json.dumps(report, sort_keys=True, indent=2) + '\n').encode()
    with OUTPUT.open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(dict(path=str(OUTPUT), status=report['status'], sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))))
    return 0 if report['status'] == 'PRESERVED_FAILURE_VERIFIED' else 1

if __name__ == '__main__': sys.dont_write_bytecode = True; raise SystemExit(main())
