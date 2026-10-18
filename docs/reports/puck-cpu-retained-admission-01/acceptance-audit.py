#!/usr/bin/env python3
"""Audit a distinct retained-tree admission; preserve allocation01's failed outcome."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import signal
import stat
import sys
import time

HELPER = Path('/tmp/palimpsest_cpu_install_audit_v1.py')
HELPER_SHA = 'a8945d3dc432831522e66c7817c0f3281e278e2a930ab1e31cbb14a26e17e406'
BASE = Path('/home/utkarsh/.codex/worktrees/0071/brain')
PRIOR = BASE / 'docs/reports/puck-cpu-install-01/failure-audit'
RUN = BASE / 'runs/puck-cpu-retained-admission-01'
CENSUS_SHA = 'b9c54829b43ca84d2208eb685598523531eb74d14aff7c9475f2ee4a7c708c3e'
ORIGINAL_SHA = 'd6d33b99dfe0300fc57b018e9cbadce0fb570debfe359974b55984a9ed687ea1'
PYC = 'numpy/distutils/__pycache__/conv_template.cpython-311.pyc'
CLAIMS = dict(package_preparation_accepted=True, runtime_qualified=False,
              numerical_imports_executed=False, study_authorized=False, collection_authorized=False)
sys.dont_write_bytecode = True
if hashlib.sha256(HELPER.read_bytes()).hexdigest() != HELPER_SHA:
    raise SystemExit('reviewed helper bytes changed')
sys.path.insert(0, str(HELPER.parent))
import palimpsest_cpu_install_audit_v1 as a
sys.path.pop(0)
if Path(a.__file__) != HELPER:
    raise SystemExit('unexpected helper import path')


def load(path):
    return json.loads(a.read_file(path))


def rows_to_map(rows):
    result = {}
    a.require(isinstance(rows, list) and len(rows) <= 40000, 'invalid census rows')
    for row in rows:
        path = a.canonical(row['path'])
        a.require(path not in result, 'duplicate census path')
        result[path] = {key: row[key] for key in ('size_bytes', 'sha256')}
    return result


def census(root, *, hashes=True):
    files, directories, stamps, pending, total = {}, set(), {}, [root], 0
    while pending:
        directory = pending.pop()
        a.require(stat.S_ISDIR(directory.lstat().st_mode), 'directory is linked/special')
        with os.scandir(directory) as entries:
            for item in entries:
                path = Path(item.path)
                relative = a.canonical(path.relative_to(root).as_posix())
                info = item.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    directories.add(relative)
                    a.require(len(directories) <= 5000, 'directory bound exceeded')
                    pending.append(path)
                    continue
                a.require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'linked/special file')
                a.require(not relative.endswith('.pth') and (not relative.endswith('.pyc') or relative == PYC), 'unregistered pyc/pth')
                total += info.st_size
                a.require(len(files) < 40000 and total <= 3 << 30 and info.st_size <= 1 << 30, 'site bounds exceeded')
                if hashes:
                    files[relative], stamps[relative] = a.hash_file(path)
                else:
                    files[relative], stamps[relative] = dict(size_bytes=info.st_size), a.fingerprint(info)
    return files, directories, stamps


def audit(config_sha):
    config_raw = a.read_file(RUN / 'configuration.json')
    a.require(hashlib.sha256(config_raw).hexdigest() == config_sha
              and config_raw == a.read_file(BASE / 'docs/plans/puck-cpu-retained-admission-01.json'), 'configuration pin/copy mismatch')
    config = json.loads(config_raw)
    a.require(config['kind'] == 'cpu-retained-installation-admission-v1'
              and config['site_root'] == 'runs/puck-cpu-install-01/site'
              and config['output'] == 'runs/puck-cpu-retained-admission-01', 'configuration scope mismatch')
    pins = {}
    a.require(config['sources'] and config['inputs'] and len(config['sources']) + len(config['inputs']) <= 512, 'input pin bounds')
    for row in config['sources'] + config['inputs']:
        path = a.canonical(row['path'])
        expected = {key: row[key] for key in ('size_bytes', 'sha256')}
        actual, _ = a.hash_file(BASE / path)
        a.require(actual == expected and (path not in pins or pins[path] == expected), 'source/input pin mismatch: ' + path)
        pins[path] = expected
    original_path = BASE / 'runs/puck-cpu-install-01/result.json'
    original_raw = a.read_file(original_path)
    original = json.loads(original_raw)
    a.require(hashlib.sha256(original_raw).hexdigest() == ORIGINAL_SHA and original['status'] == 'FAIL'
              and original['claims']['installed'] is False, 'original failure changed')
    prior_raw = a.read_file(PRIOR / 'inventory.json')
    a.require(hashlib.sha256(prior_raw).hexdigest() == CENSUS_SHA, 'prior complete census changed')
    prior, proof = json.loads(prior_raw), load(PRIOR / 'report.json')
    expected = rows_to_map(prior['entries'])
    a.require(proof['status'] == 'PRESERVED_FAILURE_VERIFIED' and proof['accepted_installation'] is False
              and proof['derivative_inventory']['sha256'] == CENSUS_SHA and proof['verified_distributions'] == 71,
              'prior namespace proof mismatch')
    a.require(config['empty_directories'] == ['mujoco.libs', 'pandas.libs'], 'empty directory descriptor mismatch')
    wanted_dirs = set(config['empty_directories'])
    for path in expected:
        wanted_dirs.update(str(parent) for parent in PurePosixPath(path).parents if str(parent) != '.')
    site = BASE / config['site_root']
    actual, directories, stamps = census(site)
    a.require(actual == expected and directories == wanted_dirs and len(directories) == prior['directory_count'], 'retained namespace differs from prior audited whole tree')
    pyc = dict(path=PYC, **expected[PYC])
    a.require(config['data_only_pyc'] == pyc and proof['inherited_authenticated_pyc_paths'] == [PYC], 'data-only pyc descriptor mismatch')
    inventory = load(RUN / 'inventory.json')
    a.require(inventory['kind'] == 'puck-cpu-installed-files-v1' and rows_to_map(inventory['entries']) == actual
              and inventory['file_count'] == len(actual) and inventory['directory_count'] == len(directories)
              and inventory['total_bytes'] == sum(row['size_bytes'] for row in actual.values()), 'new inventory mismatch')
    licence_raw = a.read_file(PRIOR / 'licences.json')
    a.require(hashlib.sha256(licence_raw).hexdigest() == proof['derivative_licences_manifest']['sha256'], 'prior licence manifest binding changed')
    copies = json.loads(licence_raw)['entries']
    required_inputs = {original_path.relative_to(BASE).as_posix(), *(str((PRIOR / name).relative_to(BASE)) for name in ('inventory.json', 'report.json', 'licences.json'))}
    for row in copies:
        a.require(row['path'].startswith('licences/'), 'invalid licence copy prefix')
        relative = a.canonical(row['path'][len('licences/'):])
        copy = PRIOR / row['path']
        observed, _ = a.hash_file(copy)
        a.require(observed == {key: row[key] for key in ('size_bytes', 'sha256')} == actual[relative], 'licence identity mismatch')
        required_inputs.add(copy.relative_to(BASE).as_posix())
    a.require(required_inputs <= set(pins) and len(copies) == proof['retained_licence_files']
              and sum(row['size_bytes'] for row in copies) == proof['retained_licence_bytes'], 'prior namespace/licence input binding incomplete')
    baseline_path = 'docs/plans/puck-python-louvain-host-baseline-v1.json'
    a.require(baseline_path in pins, 'raw host baseline not pinned')
    baseline = load(BASE / baseline_path)
    summary = dict(prefix_manifest_sha256=baseline['prefix_manifest_sha256'], regular_file_count=len(baseline['files']),
                   symlink_count=len(baseline['symlinks']), regular_file_bytes=sum(row[1] for row in baseline['files']),
                   external_file_count=len(baseline['external_libraries']) + (baseline['bwrap_executable'] is not None))
    a.require(load(RUN / 'baseline-before.json') == summary == load(RUN / 'baseline-after.json'), 'new baseline pre/post summaries mismatch')
    snapshot_raw = a.read_file(RUN / 'snapshot.json')
    snapshot, result = json.loads(snapshot_raw), load(RUN / 'result.json')
    a.require(snapshot['kind'] == 'cpu-retained-installation-snapshot-v1' and snapshot['site_root'] == str(site)
              and snapshot['configuration_sha256'] == config_sha and snapshot['data_only_pyc'] == pyc
              and snapshot['original_allocation_status'] == 'FAIL', 'snapshot binding mismatch')
    a.require(snapshot['custody'] == dict(file_count=len(actual), directory_count=len(directories),
              regular_file_bytes=inventory['total_bytes'], exact_namespace=True), 'whole-tree custody receipt mismatch')
    a.require(result['kind'] == 'cpu-retained-installation-admission-result-v1' and result['status'] == 'PASS'
              and result['configuration_sha256'] == config_sha and result['original_allocation_status'] == 'FAIL'
              and result['snapshot_sha256'] == hashlib.sha256(snapshot_raw).hexdigest()
              and all(result['claims'].get(key) is value for key, value in CLAIMS.items()), 'distinct terminal result mismatch')
    closure = result['closure']
    a.require(closure['active_children'] == [] and closure['active_non_main_threads'] == []
              and closure['all_receipts_fsynced'] is True and closure['all_handles_closed'] is True
              and type(closure['fd_count_before']) is int and closure['fd_count_before'] >= 0
              and closure['fd_count_after'] == closure['fd_count_before'], 'normal-close receipt mismatch')
    for path in proof['missing_original_receipts']:
        a.require(not (BASE / 'runs/puck-cpu-install-01' / a.canonical(path)).exists(), 'historical missing receipt was replaced')
    _, after_dirs, after_stamps = census(site, hashes=False)
    a.require(after_dirs == directories and after_stamps == stamps, 'site changed during independent audit')
    return dict(file_count=len(actual), directory_count=len(directories), total_bytes=inventory['total_bytes'],
                licence_count=len(copies), data_only_pyc=pyc, configuration_sha256=config_sha,
                source_and_input_pin_count=len(pins), original_allocation_status='FAIL', original_closure_completed=False,
                baseline_summary_scope='source-frozen parent pre/post checks; auditor checks summary identity',
                durability_scope='source-frozen parent fsync/closure receipt and referenced snapshot bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration-sha256', required=True)
    parser.add_argument('--output', type=Path, default=Path('/tmp/palimpsest-cpu-retained-admission-audit-01.json'))
    args = parser.parse_args()
    a.require(args.output.parent.resolve() == Path('/tmp') and not args.output.exists(), 'output must be fresh /tmp JSON')
    started = time.monotonic()
    report = dict(kind='cpu-retained-installation-independent-audit-v1', status='FAIL',
                  package_preparation_accepted=False, runtime_qualified=False, numerical_imports_executed=False,
                  study_authorized=False, collection_authorized=False, target_code_executed_by_auditor=False)
    def deadline(_signal, _frame):
        raise a.AuditError('180-second independent audit bound exceeded')
    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, 180)
    try:
        report['verified'] = audit(args.configuration_sha256)
        report.update(status='PASS', package_preparation_accepted=True)
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    report['elapsed_seconds'] = time.monotonic() - started
    raw = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode()
    with args.output.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(dict(path=str(args.output), status=report['status'], sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
