#!/usr/bin/env python3
"""Independent ordinary CPU-import terminal/byte audit; no target code imports."""
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
ARCHIVE = 'docs/reports/puck-cpu-retained-admission-02'
VERSIONS = dict(numpy='2.2.5', torch='2.9.0+cpu', torchvision='0.24.0+cpu', mujoco='3.3.6')
FALSE = dict(runtime_qualified=False, native_authorized=False, study_authorized=False,
             collection_authorized=False, executable=False, qualification_claims=[])
ACCEPTED_SHA = '32605ca0d48537a6eabf98a54d605ad23bf525456760d83726381aeaf38e3e96'
HELPERS = (('/tmp/palimpsest_cpu_install_audit_v1.py', 'a8945d3dc432831522e66c7817c0f3281e278e2a930ab1e31cbb14a26e17e406'),
           ('/tmp/palimpsest_cpu_retained_admission_audit_v3.py', 'f6229e92238f260e001b6e49cf545dcddd9a371fb272118881fbec8b38961469'))
STAMPS = {}

def helpers():
    loaded = []
    for filename, digest in HELPERS:
        path = Path(filename); raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest: raise ValueError('reviewed audit helper changed')
        name = path.stem
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec); sys.modules[name] = module
        spec.loader.exec_module(module); loaded.append(module)
    return loaded

def remember(path, stamp):
    a.require(path not in STAMPS or STAMPS[path] == stamp, 'input changed between reads: ' + str(path))
    STAMPS[path] = stamp

def read(path, limit=32 << 20):
    stamp = a.fingerprint(path.lstat()); remember(path, stamp)
    raw = a.read_file(path, limit)
    a.require(a.fingerprint(path.lstat()) == stamp, 'input changed while read')
    return raw

def load(path): return json.loads(read(path))
def canonical(value): return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
def metadata(row): return {key: row[key] for key in ('size_bytes', 'sha256')}
def finite(value, maximum): return type(value) in (int, float) and math.isfinite(value) and 0 <= value < maximum

def hashed(path, expected, *, single_link=True, limit=1 << 30):
    actual, stamp = a.hash_file(path, limit, single_link=single_link); remember(path, stamp)
    a.require(actual == expected, 'pinned bytes differ: ' + str(path))

def false_claims(value):
    a.require(all(value.get(key) is False for key in FALSE if key != 'qualification_claims')
              and value.get('qualification_claims') == [], 'ordinary observation granted authority')

def audit(config_path, digest):
    config_raw = read(config_path, 1 << 20)
    config = r.validate_configuration(config_raw, read(RUN / 'configuration.json', 1 << 20), digest)
    a.require(config['kind'] == 'puck-cpu-runtime-characterization-v1' and type(config['version']) is int
              and config['version'] == 1 and config['output'] == str(RUN.relative_to(BASE))
              and config['site_root'] == 'runs/puck-cpu-install-01/site' and config['expected_versions'] == VERSIONS,
              'CPU configuration scope mismatch')
    limits = config['limits']
    a.require(limits == dict(normal_seconds=180, child_hard_seconds=190, hard_seconds=195,
        rss_bytes=1536 << 20, address_space_bytes=8192 << 20, output_bytes=64 << 20,
        scratch_bytes=64 << 20, file_bytes=8 << 20, min_free_bytes=4096 << 20,
        min_available_ram_bytes=2048 << 20, max_processes=3, max_fds=40000), 'resource contract changed')
    rows = config['sources'] + config['inputs']; pins = {}
    a.require(rows and len(rows) <= 512, 'source/input bounds')
    for row in rows:
        path = a.canonical(row['path']); a.require(path not in pins, 'duplicate input pin')
        hashed(BASE / path, metadata(row)); pins[path] = row
    roles = config['roles']
    a.require(all(path in pins for path in roles.values()), 'unpinned input role')
    get = lambda role: load(BASE / roles[role])
    accepted, old, proof, snapshot = (get(role) for role in ('accepted_configuration', 'accepted_result', 'accepted_audit', 'accepted_snapshot'))
    a.require(pins[roles['accepted_configuration']]['sha256'] == ACCEPTED_SHA
              and old['status'] == proof['status'] == 'PASS' and old['claims']['package_preparation_accepted'] is True
              and proof['package_preparation_accepted'] is True and old['configuration_sha256'] == ACCEPTED_SHA
              and proof['verified']['configuration_sha256'] == ACCEPTED_SHA
              and old['snapshot_sha256'] == pins[roles['accepted_snapshot']]['sha256'], 'accepted preparation binding changed')
    a.require(len(accepted['sources']) == 16, 'acceptance source capsule count')
    for row in accepted['sources']:
        archived = ARCHIVE + '/source/' + row['path']
        a.require(archived in pins and metadata(pins[archived]) == metadata(row), 'archived acceptance source changed')
    inventory, layout, native, baseline = (get(role) for role in ('inventory', 'layout', 'native_metadata', 'baseline'))
    expected = r.rows_to_map(inventory['entries']); wanted_dirs = set(layout['predicted_destination_directories'])
    site = BASE / config['site_root']
    actual, directories, stamps = r.census(site)
    a.require(snapshot['site_root'] == str(site) and actual == expected and directories == wanted_dirs
              and len(actual) == 27225 and len(directories) == 2074
              and sum(row['size_bytes'] for row in actual.values()) == 1304701872, 'accepted whole SITE differs')
    a.require(native['kind'] == 'puck-cpu-characterization-native-metadata-v4' and native['status'] == 'COMPLETE'
              and native['root_scope'] == 'installed_shared_objects_and_interpreter'
              and native['required_missing_names'] == [] and native['errors'] == []
              and native['oversized_native_files'] == [] and 1 <= len(native['native_files']) <= 128
              and len(native['aliases']) <= 256 and native['installed_DSO_count'] <= 512
              and native['system_ELF_count_including_prefix'] <= 128, 'required native metadata is incomplete')
    for key in ('numerical_imports_executed', 'target_execution_performed', 'runtime_qualified', 'renderer_qualified'):
        a.require(native[key] is False, 'static native metadata overclaims execution')
    for row in native['native_files']: hashed(Path(row['path']), metadata(row), single_link=False, limit=64 << 20)
    for path, target in native['aliases'] + baseline['host_path_aliases']:
        path = Path(path); info = path.lstat()
        a.require(stat.S_ISLNK(info.st_mode) and os.readlink(path) == target, 'host alias changed')
        remember(path, a.fingerprint(info))
    for row in baseline['external_libraries'] + [baseline['bwrap_executable']]:
        hashed(Path(row.get('realpath') or row['path']), dict(size_bytes=row['size'], sha256=row['sha256']), single_link=False, limit=64 << 20)
    python = Path(baseline['python_prefix']) / 'bin/python3.11'
    hashed(python, dict(size_bytes=21662864, sha256='572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a'))
    summary = dict(prefix_manifest_sha256=baseline['prefix_manifest_sha256'], regular_file_count=len(baseline['files']),
        symlink_count=len(baseline['symlinks']), regular_file_bytes=sum(row[1] for row in baseline['files']),
        external_file_count=len(baseline['external_libraries']) + (baseline['bwrap_executable'] is not None))
    a.require(load(RUN / 'baseline-before.json') == summary == load(RUN / 'baseline-after.json'), 'baseline summaries changed')
    namespace = dict(kind='cpu-characterization-namespace-v1', network_isolated=True, site_readonly=True, project_hidden=True, private_pycache_empty=True)
    a.require(load(RUN / 'namespace.json') == namespace == json.loads(read(RUN / 'probe-logs/stdout.log')), 'namespace probe mismatch')
    request_raw = read(RUN / 'request.json', 65536); request = json.loads(request_raw)
    a.require(request_raw == canonical(request) and request == dict(kind='puck-runtime-import-characterization-v2', version=2,
        site_root=str(site), output_root='/output', environment=config['environment'], expected_versions=VERSIONS,
        pycache_prefix='/scratch/pycache'), 'CPU worker request mismatch')
    for name in ('probe', 'worker'):
        supervision = load(RUN / (name + '-supervision.json'))
        a.require(supervision['status'] == 'completed' and supervision['returncode'] == 0 and supervision['failure'] is None
                  and supervision['matching_survivors'] == [] and type(supervision['sampled_peak_rss_bytes']) is int
                  and 0 <= supervision['sampled_peak_rss_bytes'] <= limits['rss_bytes'], 'child supervision failed')
        invocation = load(RUN / (name + '-invocation.json')); command = invocation['command']
        a.require(invocation['configuration_sha256'] == digest and command[0] == '/usr/bin/bwrap'
                  and all(flag in command for flag in ('--unshare-all', '--disable-userns', '--clearenv', '--remount-ro', '-I', '-S', '-B'))
                  and 'pycache_prefix=/scratch/pycache' in command, 'namespace invocation binding mismatch')
        for leaf in ('stdout.log', 'stderr.log'): read(RUN / (name + '-logs') / leaf, 8 << 20)
    report_raw = read(RUN / 'payload/imports.json', 1 << 20); report = json.loads(report_raw)
    a.require(report['kind'] == 'puck-runtime-import-characterization-result-v3' and report['version'] == 3
              and report['profile'] == 'cpu-four-imports-v1' and report['status'] == 'observed'
              and report['observation_scope'] == 'completed_imports' and report['expected_versions'] == report['versions'] == VERSIONS
              and report['request_sha256'] == hashlib.sha256(request_raw).hexdigest()
              and report['source_sha256'] == pins['scripts/characterize_puck_runtime_imports.py']['sha256']
              and report['environment_sha256'] == hashlib.sha256(canonical(config['environment'])).hexdigest()
              and report['pycache_prefix'] == '/scratch/pycache' and report['environment_delta'] is None
              and report['observation_errors'] == [] and 'error' not in report, 'ordinary import report mismatch')
    false_claims(report)
    a.require([row['name'] for row in report['imports']] == list(VERSIONS)
              and all(row['status'] == 'observed' and finite(row['seconds'], 180) and row['cache_entries'] <= 8192
                      for row in report['imports']), 'four import order/status mismatch')
    cache = report['cache']
    a.require(cache['cache_entries'] == len(cache['modules']) <= 8192 and cache['attribute_edges'] <= 262144
              and cache['export_scope'] == 'exceptional_cache_identities', 'cache observation bounds')
    for key in ('baseline_maps', 'maps'):
        maps = report[key]
        a.require(maps['map_bytes'] <= 4 << 20 and maps['map_lines'] <= 65536 and len(maps['images']) <= 65536
                  and maps['persistent_snapshot_only'] is True and maps['transient_anonymous_jit_closure_qualified'] is False, 'map scope/bounds')
    worker_receipt = json.loads(read(RUN / 'worker-logs/stdout.log'))
    a.require(worker_receipt == dict(report_sha256=hashlib.sha256(report_raw).hexdigest(), report_bytes=len(report_raw), status='observed'), 'worker publication receipt')
    result = load(RUN / 'result.json'); false_claims(result)
    a.require(result['kind'] == 'puck-cpu-characterization-outcome-v1' and result['status'] == 'observed'
              and 'error' not in result and 'error_type' not in result and result['configuration_sha256'] == digest
              and result['report_sha256'] == hashlib.sha256(report_raw).hexdigest() and result['versions'] == VERSIONS
              and result['namespace_probe_completed'] is True and result['accepted_package_preparation_preserved'] is True
              and result['worker_supervision_status'] == 'completed' and finite(result['elapsed_seconds'], 180)
              and 0 <= result['sampled_parent_peak_rss_bytes'] <= limits['rss_bytes'], 'parent terminal outcome mismatch')
    closure = result['closure']
    a.require(closure['active_children'] == closure['active_non_main_threads'] == []
              and closure['all_handles_closed'] is True and closure['all_receipts_fsynced'] is True
              and type(closure['fd_count_before']) is int and closure['fd_count_after'] == closure['fd_count_before'], 'parent closure mismatch')
    a.require(load(BASE / 'runs/puck-cpu-install-01/result.json')['status'] == 'FAIL'
              and load(BASE / 'runs/puck-cpu-retained-admission-01/result.json')['status'] == 'FAIL', 'prior failure changed')
    for old_run, names in (('puck-cpu-install-01', ('inventory.json', 'licences.json', 'baseline-after.json', 'logs/namespace.json')),
                           ('puck-cpu-retained-admission-01', ('inventory.json', 'snapshot.json', 'baseline-after.json'))):
        a.require(all(not os.path.lexists(BASE / 'runs' / old_run / name) for name in names), 'historical missing receipt replaced')
    _, after_dirs, after_stamps = r.census(site, hashes=False)
    a.require(after_dirs == directories and after_stamps == stamps, 'SITE file/directory fingerprints changed during audit')
    for path, stamp in STAMPS.items(): a.require(a.fingerprint(path.lstat()) == stamp, 'input/receipt changed during audit: ' + str(path))
    return dict(file_count=len(actual), directory_count=len(directories), regular_file_bytes=1304701872,
        source_and_input_pin_count=len(pins), archived_acceptance_source_pins=16, receipt_fingerprints=len(STAMPS),
        native_file_count=len(native['native_files']), native_alias_count=len(native['aliases']), configuration_sha256=digest,
        baseline_scope='source-frozen full-prefix checks plus independently hashed selected host files/interpreter',
        observation_scope='ordinary trusted imports and persistent snapshots only; not held/native/render qualification')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', type=Path, required=True)
    parser.add_argument('--configuration-sha256', required=True)
    parser.add_argument('--output', type=Path, default=Path('/tmp/palimpsest-cpu-characterization-audit-01.json'))
    args = parser.parse_args(); started = time.monotonic()
    if args.output.parent.resolve() != Path('/tmp') or os.path.lexists(args.output): raise ValueError('fresh /tmp output required')
    report = dict(kind='cpu-characterization-independent-audit-v1', status='FAIL', ordinary_imports_observed=False,
                  native_qualified=False, target_code_executed_by_auditor=False, **FALSE)
    global a, r
    def expired(_signal, _frame): raise TimeoutError('180-second independent CPU audit deadline')
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, 180)
    try:
        a, r = helpers(); report['verified'] = audit(args.configuration, args.configuration_sha256)
        if not finite(time.monotonic()-started, 180): raise TimeoutError('late independent CPU audit')
        report.update(status='PASS', ordinary_imports_observed=True)
    except Exception as error: report['error'] = type(error).__name__ + ': ' + str(error)
    report['elapsed_seconds'] = time.monotonic()-started
    raw = (json.dumps(report, sort_keys=True, indent=2) + '\n').encode()
    with args.output.open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(dict(path=str(args.output), status=report['status'], sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))))
    return 0 if report['status'] == 'PASS' else 1

if __name__ == '__main__': sys.dont_write_bytecode = True; raise SystemExit(main())
