#!/usr/bin/env python3
"""Preserve derivative byte evidence from failed allocation01; accept no installation."""
import datetime
import email
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import sys
import time
from urllib.parse import unquote, urlparse
import zipfile

BASE = Path('/home/utkarsh/.codex/worktrees/0071/brain')
RUN = BASE / 'runs/puck-cpu-install-01'
OUTPUT = Path('/tmp/palimpsest-cpu-install-01-failure-audit')
HELPER = Path('/tmp/palimpsest_cpu_install_audit_v1.py')
HELPER_SHA = 'a8945d3dc432831522e66c7817c0f3281e278e2a930ab1e31cbb14a26e17e406'
CONFIG_SHA = 'edc9f98bb546212f9f8e07722f04ca4be0a3cbf63d68a38033b50ae3d44709b4'
RESULT_SHA = 'd6d33b99dfe0300fc57b018e9cbadce0fb570debfe359974b55984a9ed687ea1'
ACCEPTANCE = Path('/tmp/palimpsest-cpu-install-acceptance-audit-01.json')
ACCEPTANCE_SHA = '7015fbe7dd968b1271d22eccd6c3333e73ce3408518531e7668a3c1cc3fb5470'
PYCS = {'numpy/distutils/__pycache__/conv_template.cpython-311.pyc'}
FAILURE = 'native log drain/final sync timed out'

# Normal import of the reviewed helper module; no target module enters sys.path.
sys.dont_write_bytecode = True
helper_raw = HELPER.read_bytes()
if hashlib.sha256(helper_raw).hexdigest() != HELPER_SHA:
    raise SystemExit('reviewed audit helper changed')
sys.path.insert(0, str(HELPER.parent))
import palimpsest_cpu_install_audit_v1 as a
sys.path.pop(0)
if Path(a.__file__) != HELPER or hashlib.sha256(HELPER.read_bytes()).hexdigest() != HELPER_SHA:
    raise SystemExit('reviewed helper import path/bytes differ')


def census(root, hashes=True):
    a.require(stat.S_ISDIR(root.lstat().st_mode), 'site root is not a real directory')
    files, directories, stamps, pending, total = {}, set(), {}, [root], 0
    while pending:
        directory = pending.pop()
        a.require(stat.S_ISDIR(directory.lstat().st_mode), 'directory changed to symlink/special')
        with os.scandir(directory) as entries:
            for item in entries:
                path = Path(item.path)
                relative = a.canonical(path.relative_to(root).as_posix())
                info = item.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    directories.add(relative)
                    a.require(len(directories) <= a.MAX_DIRS, 'directory bound exceeded')
                    pending.append(path)
                    continue
                a.require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'nonregular/symlink/hardlinked site leaf')
                a.require(not relative.endswith('.pth') and (not relative.endswith('.pyc') or relative in PYCS),
                          'unexpected pth or non-source-authenticated pyc: ' + relative)
                total += info.st_size
                a.require(info.st_size <= a.MAX_FILE and total <= a.MAX_BYTES and len(files) < a.MAX_FILES,
                          'site census byte/file bound exceeded')
                if hashes:
                    files[relative], stamps[relative] = a.hash_file(path)
                else:
                    files[relative], stamps[relative] = dict(size_bytes=info.st_size), a.fingerprint(info)
    return files, directories, stamps


def read_json(path, *, digest=None):
    raw = a.read_file(path)
    if digest:
        a.require(hashlib.sha256(raw).hexdigest() == digest, 'pinned receipt changed: ' + str(path))
    return json.loads(raw), dict(path=str(path), size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def verify_receipts(layout):
    result, result_receipt = read_json(RUN / 'result.json', digest=RESULT_SHA)
    config, config_receipt = read_json(RUN / 'configuration.json', digest=CONFIG_SHA)
    a.require(a.read_file(RUN / 'configuration.json') == a.read_file(BASE / 'docs/plans/puck-cpu-install-01.json'),
              'configuration copy differs from admitted original')
    a.require(result['kind'] == 'puck-cpu-install-result-v1' and result['status'] == 'FAIL'
              and result['configuration_sha256'] == CONFIG_SHA and result['error_type'] == 'ValueError'
              and FAILURE in result['error'], 'original allocation failure differs')
    a.require(all(result['claims'].get(key) is False for key in a.CLAIMS), 'original false claims changed')
    a.require(config['kind'] == 'puck-cpu-install-v1' and config['output'] == 'runs/puck-cpu-install-01'
              and config['interpreter']['path'] == result['interpreter'], 'configuration identity mismatch')
    a.require([row['path'] for row in config['sources']] == a.SOURCE_PATHS, 'source capsule membership mismatch')
    for row in config['sources']:
        observed, _ = a.hash_file(BASE / a.canonical(row['path']))
        a.require(observed == {key: row[key] for key in ('size_bytes', 'sha256')}, 'source pin changed: ' + row['path'])
    expected = {wheel['archive_path']: wheel for wheel in layout['wheels']}
    a.require(len(config['wheels']) == 71 and len({row['path'] for row in config['wheels']}) == 71, 'wheel pin count mismatch')
    for row in config['wheels']:
        wheel = expected[row['path']]
        a.require(row['name'] == wheel['normalized_name'] and row['version'] == wheel['version']
                  and row['sha256'] == wheel['expected_archive_sha256'] and row['size_bytes'] == wheel['archive_bytes']
                  and row['metadata_sha256'] == wheel['metadata_sha256'], 'configuration wheel pin mismatch')
    baseline_row = config['host_baseline']
    baseline, _ = read_json(BASE / baseline_row['path'], digest=baseline_row['sha256'])
    summary = dict(prefix_manifest_sha256=baseline['prefix_manifest_sha256'], regular_file_count=len(baseline['files']),
                   symlink_count=len(baseline['symlinks']), regular_file_bytes=sum(row[1] for row in baseline['files']),
                   external_file_count=len(baseline['external_libraries']) + (baseline['bwrap_executable'] is not None))
    before, before_receipt = read_json(RUN / 'baseline-before.json')
    a.require(before == summary, 'original baseline-before receipt mismatch')
    supervisors = {}
    receipts = [result_receipt, config_receipt, before_receipt]
    for fixture in (False, True):
        stage = RUN / 'fixture' if fixture else RUN
        supervisor, receipt = read_json(stage / 'logs/supervisor.json')
        receipts.append(receipt)
        a.require(type(supervisor['returncode']) is int and supervisor['returncode'] == 0
                  and supervisor['matching_survivors'] == [] and supervisor['mutable_failures'] == [], 'unexpected process outcome')
        if fixture:
            a.require(supervisor == result['fixture_supervisor'] and supervisor['status'] == 'completed'
                      and supervisor['failure'] is None, 'original fixture did not pass')
        else:
            a.require(supervisor['status'] == 'failed' and supervisor['failure'] == FAILURE, 'target supervisor failure differs')
        supervisors['fixture' if fixture else 'target'] = supervisor
        stdout = a.read_file(stage / 'logs/stdout.log', 4 << 20)
        stderr = a.read_file(stage / 'logs/stderr.log', 4 << 20)
        namespace = json.loads(stdout.splitlines()[0])
        command, command_receipt = read_json(stage / 'logs/command.json')
        receipts.extend([command_receipt, dict(path=str(stage / 'logs/stdout.log'), size_bytes=len(stdout), sha256=hashlib.sha256(stdout).hexdigest()),
                         dict(path=str(stage / 'logs/stderr.log'), size_bytes=len(stderr), sha256=hashlib.sha256(stderr).hexdigest())])
        scratch, site = stage / 'scratch', stage / 'site'
        environment = dict(HOME=str(scratch / 'home'), TMPDIR=str(scratch), PATH='/nonexistent', LC_ALL='C.UTF-8', LANG='C.UTF-8',
                           TZ='UTC', SETUPTOOLS_USE_DISTUTILS='stdlib', PWD=str(scratch))
        wheels = [stage / 'install_fixture-0.0-py3-none-any.whl'] if fixture else [BASE / row['path'] for row in config['wheels']]
        readonly = [baseline['python_prefix'], config['uv']['path'], '/driver.py', '/', '/proc', '/dev', *map(str, wheels)]
        a.require(namespace['kind'] == 'puck-cpu-install-namespace-v1' and namespace['status'] == 'PASS'
                  and namespace['network'] != namespace['parent_network'] and namespace['environment'] == environment
                  and namespace['readonly_paths'] == readonly, 'raw namespace receipt mismatch')
        expected_uv = [config['uv']['path'], 'pip', 'install', '--target', str(site), '--python', result['interpreter'],
                       '--no-deps', '--no-index', '--offline', '--no-build', '--link-mode', 'copy', '--no-cache',
                       '--no-config', '--no-python-downloads', '--no-compile-bytecode', '--', *map(str, wheels)]
        a.require(command['uv_argv'] == expected_uv, 'original uv command differs')
        if fixture:
            a.require(read_json(stage / 'logs/namespace.json')[0] == namespace, 'fixture normalized namespace receipt differs')
    acceptance, acceptance_receipt = read_json(ACCEPTANCE, digest=ACCEPTANCE_SHA)
    a.require(acceptance['status'] == 'FAIL' and 'forbidden pyc' in acceptance['error'], 'original acceptance audit failure differs')
    receipts.append(acceptance_receipt)
    missing = ['inventory.json', 'licences.json', 'baseline-after.json', 'logs/namespace.json']
    a.require(all(not (RUN / relative).exists() for relative in missing), 'missing original receipt was subsequently created')
    original_copies, original_copy_dirs, _ = a.census(RUN / 'licences')
    a.require(not original_copies and not original_copy_dirs, 'original licence directory is no longer empty')
    return result, receipts, supervisors, missing, a.audit_fixture(RUN / 'fixture')


def inspect_site(layout, interpreter):
    actual, directories, stamps = census(RUN / 'site')
    owners, members, licences, explicit_dirs, pycs, expanded = {}, {}, set(), set(), set(), 0
    for wheel in layout['wheels']:
        name, dist_info = wheel['normalized_name'], wheel['dist_info_root']
        a.require(name not in members, 'duplicate distribution identity')
        members[name] = set()
        path = BASE / wheel['archive_path']
        observed, stamp = a.hash_file(path)
        a.require(observed == dict(size_bytes=wheel['archive_bytes'], sha256=wheel['expected_archive_sha256']), 'wheel bytes changed: ' + name)
        with zipfile.ZipFile(path) as archive:
            a.require(a.fingerprint(os.fstat(archive.fp.fileno())) == stamp, 'archive changed before inspection')
            infos = archive.infolist()
            a.require(len(infos) <= a.MAX_FILES and len({i.filename for i in infos}) == len(infos), 'archive member count/duplicates')
            for info in infos:
                source = info.filename.rstrip('/') if info.is_dir() else info.filename
                a.canonical(source)
                a.require(stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG, stat.S_IFDIR), 'special archive member')
                if info.is_dir():
                    if not (source.split('/')[0].endswith('.data') and len(source.split('/')) < 3):
                        explicit_dirs.add(a.mapped(source))
                    continue
                destination = a.mapped(source)
                a.require(destination not in owners and destination in actual, 'missing/colliding archive destination: ' + destination)
                owners[destination] = name
                members[name].add(destination)
                expanded += info.file_size
                a.require(expanded <= a.MAX_BYTES, 'archive expanded bytes exceeded bound')
                if source == dist_info + '/RECORD':
                    pass
                elif '.data/scripts/' in source:
                    a.require(name == 'python-louvain' and destination == 'bin/community', 'unexpected rewritten script')
                    original = archive.read(info)
                    first, separator, rest = original.partition(b'\n')
                    a.require(first == b'#!python' and separator
                              and a.read_file(RUN / 'site' / destination) == ('#!' + interpreter + '\n').encode() + rest,
                              'community changed beyond interpreter shebang')
                else:
                    a.require(a.hash_member(archive, info) == actual[destination], 'immutable wheel member changed: ' + destination)
                if destination.endswith('.pyc'):
                    pycs.add(destination)
                if source.startswith(dist_info + '/licenses/') or source.rsplit('/', 1)[-1].lower().startswith(('license', 'licence', 'copying', 'notice')):
                    licences.add(destination)
            a.require(a.fingerprint(os.fstat(archive.fp.fileno())) == stamp and a.fingerprint(path.lstat()) == stamp,
                      'archive changed during inspection')
        metadata = email.message_from_bytes(a.read_file(RUN / 'site' / wheel['metadata_path']))
        a.require(re.sub(r'[-_.]+', '-', metadata['Name']).lower() == name and metadata['Version'] == wheel['version'], 'installed pin mismatch')
    a.require(len(members) == 71 and pycs == PYCS, 'exact71/source-authentic pyc set mismatch')
    wrappers = [entry for entry in layout['entry_points'] if entry['generates_script_on_linux']]
    a.require(len(wrappers) == 18, 'launcher count changed')
    for entry in wrappers:
        path = entry['destination_path']
        a.require(path in actual and path not in owners, 'launcher missing/collision')
        a.inspect_launcher(a.read_file(RUN / 'site' / path, 65536), interpreter, entry)
        owners[path] = entry['distribution']
        members[entry['distribution']].add(path)
    by_dist_info = {wheel['dist_info_root']: wheel for wheel in layout['wheels']}
    for path in actual:
        if path in owners:
            continue
        if path == '.lock':
            a.require(actual[path]['size_bytes'] == 0, 'nonempty root lock')
            continue
        parts = path.split('/')
        a.require(len(parts) == 2 and parts[0] in by_dist_info and parts[1] in a.EXTRA_METADATA, 'unexpected installed file: ' + path)
        wheel, leaf = by_dist_info[parts[0]], parts[1]
        data = a.read_file(RUN / 'site' / path)
        if leaf == 'INSTALLER':
            a.require(data.strip() == b'uv', 'unexpected INSTALLER')
        elif leaf == 'REQUESTED':
            a.require(data == b'', 'nonempty REQUESTED')
        else:
            parsed = json.loads(data)
            a.require(isinstance(parsed, dict), 'nonobject installer metadata')
            if leaf == 'direct_url.json':
                url = urlparse(parsed['url'])
                a.require(url.scheme == 'file' and not url.netloc and not url.query and not url.fragment
                          and unquote(url.path) == str(BASE / wheel['archive_path']), 'direct URL not exact archive')
                hashes = parsed.get('archive_info', {})
                a.require(hashes.get('hashes', {}).get('sha256', wheel['expected_archive_sha256']) == wheel['expected_archive_sha256']
                          and hashes.get('hash', 'sha256=' + wheel['expected_archive_sha256']) == 'sha256=' + wheel['expected_archive_sha256'],
                          'direct URL archive digest mismatch')
        name = wheel['normalized_name']
        owners[path] = name
        members[name].add(path)
    for path in actual:
        explicit_dirs.update(str(parent) for parent in PurePosixPath(path).parents if str(parent) != '.')
    a.require(directories <= explicit_dirs, 'unexpected installed directory')
    a.require({p.split('/')[0] for p in directories if p.split('/')[0].endswith('.dist-info')} == set(by_dist_info), 'extra/missing dist-info directory')
    for dist_info, wheel in by_dist_info.items():
        path = dist_info + '/RECORD'
        a.check_record(a.read_file(RUN / 'site' / path), path, members[wheel['normalized_name']], actual)
    a.require(expanded == layout['totals']['expanded_regular_bytes'], 'expanded archive total differs from frozen layout')
    return actual, directories, stamps, licences, expanded


def write_new(path, data):
    with path.open('xb') as stream:
        stream.write(data)
    return dict(path=path.relative_to(OUTPUT).as_posix(), size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    OUTPUT.mkdir(mode=0o700)
    started = time.monotonic()
    report = dict(kind='puck-cpu-install-preserved-failure-audit-v1', status='AUDIT_FAILED', accepted_installation=False,
                  runtime_qualified=False, numerical_imports_executed=False, study_authorized=False, collection_authorized=False,
                  original_allocation_status='FAIL', no_gate_closed=True, installer_retry_performed=False,
                  target_packages_imported_by_auditor=False, target_code_executed_by_auditor=False,
                  helper_sha256=HELPER_SHA, bounds=dict(wall_seconds=180, max_site_bytes=a.MAX_BYTES, max_files=a.MAX_FILES, max_individual_bytes=a.MAX_FILE))
    def deadline(_signal, _frame):
        raise a.AuditError('180-second preserved-failure audit bound exceeded')
    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, 180)
    try:
        layout, _ = read_json(a.LAYOUT, digest=a.LAYOUT_SHA)
        result, receipts, supervisors, missing, fixture_files = verify_receipts(layout)
        actual, directories, stamps, licences, expanded = inspect_site(layout, result['interpreter'])
        inventory = dict(kind='puck-cpu-install-failure-files-v1', entries=[dict(path=path, **actual[path]) for path in sorted(actual)],
                         file_count=len(actual), directory_count=len(directories), total_bytes=sum(row['size_bytes'] for row in actual.values()))
        report['derivative_inventory'] = write_new(OUTPUT / 'inventory.json', (json.dumps(inventory, indent=2, sort_keys=True) + '\n').encode())
        copies = []
        for path in sorted(licences):
            data = a.read_file(RUN / 'site' / path)
            a.require(dict(size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest()) == actual[path], 'licence source changed')
            target = OUTPUT / 'licences' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            copies.append(write_new(target, data))
        report['derivative_licences_manifest'] = write_new(OUTPUT / 'licences.json', (json.dumps(dict(entries=copies), indent=2, sort_keys=True) + '\n').encode())
        _, after_dirs, after_stamps = census(RUN / 'site', hashes=False)
        a.require(after_dirs == directories and after_stamps == stamps, 'failed installed namespace changed during audit')
        for receipt in receipts:
            current, _ = a.hash_file(Path(receipt['path']))
            a.require(current == {k: receipt[k] for k in ('size_bytes', 'sha256')}, 'original receipt changed during audit')
        report.update(status='PRESERVED_FAILURE_VERIFIED', original_receipts=receipts, original_supervisors=supervisors,
                      missing_original_receipts=missing, original_licence_copy_directory_empty=True,
                      measured_installed_files=len(actual), measured_installed_directories=len(directories), measured_installed_bytes=inventory['total_bytes'],
                      verified_distributions=71, verified_expanded_archive_bytes=expanded, retained_licence_files=len(copies),
                      retained_licence_bytes=sum(row['size_bytes'] for row in copies), inert_fixture_files_verified=fixture_files,
                      inherited_authenticated_pyc_paths=sorted(PYCS), inherited_pyc_count=1, target_pth_count=0,
                      blanket_pyc_policy_nonconformance=True, pyc_origin='unchanged authenticated numpy wheel member; no inference of installer compilation',
                      scope='Derivative failed-namespace byte evidence only; missing parent outputs remain missing; no installed acceptance or runtime qualification')
    except Exception as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    report['elapsed_seconds'] = time.monotonic() - started
    report['ended_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt = write_new(OUTPUT / 'report.json', (json.dumps(report, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps(dict(status=report['status'], **receipt), sort_keys=True))
    return 0 if report['status'] == 'PRESERVED_FAILURE_VERIFIED' else 1


if __name__ == '__main__':
    sys.exit(main())
