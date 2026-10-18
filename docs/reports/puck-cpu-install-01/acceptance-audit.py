#!/usr/bin/env python3
"""Inspect the frozen CPU installation without importing or executing its code."""
import argparse
import base64
import csv
import datetime
import email
import hashlib
import io
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
LAYOUT = Path('/tmp/palimpsest-cpu-wheel-install-layout-v1.json')
LAYOUT_SHA = '82076ef08db0cb07c19d26376d6f501dd3a8d072738d0150641dd6691c9fda5b'
MAX_FILES, MAX_DIRS = 40000, 40000
MAX_BYTES, MAX_FILE, MAX_META, WALL = 3 << 30, 1 << 30, 32 << 20, 180
CLAIMS = dict(installed=True, runtime_qualified=False, numerical_imports_executed=False,
              study_authorized=False, collection_authorized=False)
EXTRA_METADATA = {'INSTALLER', 'REQUESTED', 'direct_url.json', 'uv_cache.json'}
SOURCE_PATHS = sorted((
    'scripts/install_puck_cpu.py', 'scripts/build_puck_python_louvain.py',
    'scripts/acquire_puck_cpu_payloads.py', 'src/palimpsest/__init__.py',
    'src/palimpsest/bounded_qualification.py', 'src/palimpsest/evaluate.py',
    'src/palimpsest/puck_execution_files.py', 'src/palimpsest/puck_package_payloads.py',
    'src/palimpsest/puck_build_inputs.py', 'docs/plans/puck-cpu-install-v1.md',
    'docs/plans/puck-cpu-runtime-candidate-v1.json',
    'docs/reports/puck-cpu-footprint-02/assessment.json', 'pyproject.toml', 'uv.lock'))


class AuditError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def canonical(path):
    require(isinstance(path, str) and path and not path.startswith('/') and '\\' not in path,
            'invalid relative path: ' + repr(path))
    parts = path.split('/')
    require(all(p not in ('', '.', '..') for p in parts), 'noncanonical relative path: ' + path)
    return path


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def hash_file(path, limit=MAX_FILE, *, single_link=True):
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and (not single_link or before.st_nlink == 1),
            'not an allowed regular file: ' + str(path))
    require(before.st_size <= limit, 'file exceeds read bound: ' + str(path))
    digest = hashlib.sha256()
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC), 'rb') as stream:
        require(fingerprint(os.fstat(stream.fileno())) == fingerprint(before),
                'file changed before read: ' + str(path))
        size = 0
        while chunk := stream.read(1 << 20):
            size += len(chunk)
            require(size <= limit, 'file grew beyond read bound: ' + str(path))
            digest.update(chunk)
        require(size == before.st_size and fingerprint(os.fstat(stream.fileno())) == fingerprint(before),
                'file changed while read: ' + str(path))
    require(fingerprint(path.lstat()) == fingerprint(before), 'file changed after read: ' + str(path))
    return dict(size_bytes=size, sha256=digest.hexdigest()), fingerprint(before)


def read_file(path, limit=MAX_META):
    expected, stamp = hash_file(path, limit)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC), 'rb') as stream:
        require(fingerprint(os.fstat(stream.fileno())) == stamp, 'file changed before metadata read')
        data = stream.read(limit + 1)
        require(fingerprint(os.fstat(stream.fileno())) == stamp, 'file changed during metadata read')
    require(len(data) == expected['size_bytes'] and hashlib.sha256(data).hexdigest() == expected['sha256'],
            'metadata read changed: ' + str(path))
    return data


def census(root, hashes=True, *, allow_hooks=False):
    require(stat.S_ISDIR(root.lstat().st_mode), 'tree root is not a real directory: ' + str(root))
    files, directories, stamps = {}, set(), {}
    pending, total = [root], 0
    while pending:
        directory = pending.pop()
        require(stat.S_ISDIR(directory.lstat().st_mode), 'directory changed to symlink/special: ' + str(directory))
        with os.scandir(directory) as entries:
            for item in entries:
                path = Path(item.path)
                relative = canonical(path.relative_to(root).as_posix())
                info = item.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    directories.add(relative)
                    require(len(directories) <= MAX_DIRS, 'directory count bound exceeded')
                    pending.append(path)
                else:
                    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                            'symlink, special file, or multiple hard links: ' + str(path))
                    require(info.st_size <= MAX_FILE, 'individual file byte bound exceeded')
                    total += info.st_size
                    require(total <= MAX_BYTES and len(files) < MAX_FILES, 'tree file/byte bound exceeded')
                    require(not relative.endswith('.pyc') and (allow_hooks or not relative.endswith('.pth')),
                            'forbidden pyc/pth: ' + relative)
                    if hashes:
                        files[relative], stamps[relative] = hash_file(path)
                    else:
                        files[relative] = dict(size_bytes=info.st_size)
                        stamps[relative] = fingerprint(info)
    return files, directories, stamps


def mapped(path):
    canonical(path)
    parts = path.split('/')
    if parts[0].endswith('.data'):
        require(len(parts) >= 3 and parts[1] in ('data', 'scripts', 'purelib', 'platlib'),
                'unexpected .data mapping: ' + path)
        return '/'.join((['bin'] if parts[1] == 'scripts' else []) + parts[2:])
    return path


def hash_member(archive, member):
    require(member.file_size <= MAX_FILE, 'archive member individual bound exceeded')
    digest, count = hashlib.sha256(), 0
    with archive.open(member) as stream:
        while chunk := stream.read(1 << 20):
            count += len(chunk)
            require(count <= member.file_size, 'archive member exceeds declared size')
            digest.update(chunk)
    require(count == member.file_size, 'archive member size mismatch')
    return dict(size_bytes=count, sha256=digest.hexdigest())


def inspect_launcher(data, interpreter, entry):
    module, separator, target = entry['value'].partition(':')
    require(separator and re.fullmatch(r'[A-Za-z_]\w*', target), 'unsupported entrypoint form')
    require(len(('#!' + interpreter + '\n').encode()) <= 127, 'unsupported long interpreter shebang')
    # Exact Linux template from uv 0.9.25, wheel.rs:31-50; compared as inert bytes.
    expected = f'''#!{interpreter}
# -*- coding: utf-8 -*-
import sys
from {module} import {target}
if __name__ == "__main__":
    if sys.argv[0].endswith("-script.pyw"):
        sys.argv[0] = sys.argv[0][:-11]
    elif sys.argv[0].endswith(".exe"):
        sys.argv[0] = sys.argv[0][:-4]
    sys.exit({target}())
'''.encode('utf-8')
    require(data == expected, 'launcher differs from pinned uv template: ' + entry['name'])


def check_record(data, record_path, wanted, actual):
    paths = set()
    for row in csv.reader(io.StringIO(data.decode('utf-8'))):
        require(len(row) == 3, 'malformed installed RECORD row')
        path, digest, size = row
        canonical(path)
        require(path not in paths and path in actual, 'duplicate/missing installed RECORD path: ' + path)
        paths.add(path)
        if path == record_path:
            require(digest == '' and size == '', 'RECORD self row must omit hash and size')
        else:
            require(digest.startswith('sha256=') and size.isdecimal() and int(size) == actual[path]['size_bytes'],
                    'installed RECORD size/hash algorithm mismatch: ' + path)
            encoded = digest.split('=', 1)[1]
            decoded = base64.b64decode(encoded + '=' * (-len(encoded) % 4), altchars=b'-_', validate=True)
            require(decoded.hex() == actual[path]['sha256'], 'installed RECORD digest mismatch: ' + path)
    require(paths == wanted, 'installed RECORD ownership/path set mismatch: ' + record_path)


def audit_fixture(root):
    site, dist_info = root / 'site', 'install_fixture-0.0.dist-info'
    actual, directories, _ = census(site, allow_hooks=True)
    wheel = root / 'install_fixture-0.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as archive:
        source_paths = set(archive.namelist())
        require(source_paths == {'install_fixture/__init__.py', 'install_fixture.pth',
                                dist_info + '/METADATA', dist_info + '/WHEEL', dist_info + '/RECORD'},
                'fixture source wheel membership mismatch')
        require(archive.read('install_fixture/__init__.py') == b"raise RuntimeError('fixture must never import')\n"
                and archive.read('install_fixture.pth') == b"import pathlib; pathlib.Path('fixture-hook-executed').write_text('executed')\n",
                'fixture inert import/hook probe source mismatch')
        for path in source_paths - {dist_info + '/RECORD'}:
            require(path in actual and hash_member(archive, archive.getinfo(path)) == actual[path],
                    'fixture payload changed: ' + path)
    wanted = set(actual) - {'.lock'}
    require(source_paths <= wanted and all(path in source_paths or path in {dist_info + '/' + leaf for leaf in EXTRA_METADATA}
                                           for path in wanted), 'fixture installed dependency or unexpected file')
    require('.lock' not in actual or actual['.lock']['size_bytes'] == 0, 'fixture lock is not empty')
    require(not any(path.endswith('.pth') and path != 'install_fixture.pth' for path in actual), 'unexpected fixture pth')
    check_record(read_file(site / dist_info / 'RECORD'), dist_info + '/RECORD', wanted, actual)
    inventory = json.loads(read_file(root / 'inventory.json'))
    rows = inventory['entries']
    require(inventory['kind'] == 'puck-cpu-installed-files-v1' and len(rows) == len(actual)
            and {row['path']: {k: row[k] for k in ('size_bytes', 'sha256')} for row in rows} == actual
            and inventory['file_count'] == len(actual) and inventory['directory_count'] == len(directories)
            and inventory['total_bytes'] == sum(row['size_bytes'] for row in actual.values()), 'fixture inventory mismatch')
    tree, _, _ = census(root, hashes=False, allow_hooks=True)
    require(not any(path.rsplit('/', 1)[-1] == 'fixture-hook-executed' for path in tree), 'fixture hook execution marker exists')
    return len(actual)


def audit_receipts(run_root, interpreter, configuration_sha256, layout, result):
    raw = read_file(run_root / 'configuration.json')
    require(hashlib.sha256(raw).hexdigest() == configuration_sha256
            and raw == read_file(BASE / 'docs/plans/puck-cpu-install-01.json')
            and result['configuration_sha256'] == configuration_sha256, 'configuration digest/copy mismatch')
    config = json.loads(raw)
    require(config['kind'] == 'puck-cpu-install-v1' and run_root == BASE / canonical(config['output'])
            and config['interpreter']['path'] == interpreter, 'configuration target/interpreter mismatch')
    require([row['path'] for row in config['sources']] == SOURCE_PATHS, 'source capsule membership mismatch')
    for row in config['sources']:
        actual, _ = hash_file(BASE / canonical(row['path']))
        require(actual == {key: row[key] for key in ('size_bytes', 'sha256')}, 'source pin changed: ' + row['path'])
    expected_wheels = {wheel['archive_path']: wheel for wheel in layout['wheels']}
    require(len(config['wheels']) == 71 and len({row['path'] for row in config['wheels']}) == 71,
            'configuration wheel membership mismatch')
    for row in config['wheels']:
        require(row['path'] in expected_wheels, 'unexpected configuration archive path')
        wheel = expected_wheels[row['path']]
        require(row['name'] == wheel['normalized_name'] and row['version'] == wheel['version']
                and row['filename'] == Path(row['path']).name and row['size_bytes'] == wheel['archive_bytes']
                and row['sha256'] == wheel['expected_archive_sha256']
                and row['metadata_sha256'] == wheel['metadata_sha256'], 'configuration wheel identity mismatch')
    baseline_row = config['host_baseline']
    baseline_raw = read_file(BASE / canonical(baseline_row['path']))
    require(len(baseline_raw) == baseline_row['size_bytes']
            and hashlib.sha256(baseline_raw).hexdigest() == baseline_row['sha256'], 'raw host baseline pin changed')
    baseline = json.loads(baseline_raw)
    prefix = Path(baseline['python_prefix'])
    manifest = {key: baseline[key] for key in ('files', 'symlinks')}
    require(len(baseline['files']) + len(baseline['symlinks']) <= 10000
            and sum(row[1] for row in baseline['files']) <= 256 << 20, 'baseline manifest bound exceeded')
    manifest_sha = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    require(manifest_sha == baseline['prefix_manifest_sha256'], 'baseline manifest digest mismatch')
    for relative, size, digest in baseline['files']:
        actual, _ = hash_file(prefix / canonical(relative), single_link=False)
        require(actual == dict(size_bytes=size, sha256=digest), 'named baseline file changed: ' + relative)
    for relative, target in baseline['symlinks']:
        path = prefix / canonical(relative)
        require(stat.S_ISLNK(path.lstat().st_mode) and os.readlink(path) == target, 'baseline symlink changed: ' + relative)
    external = list(baseline['external_libraries'])
    if baseline['bwrap_executable'] is not None:
        external.append(baseline['bwrap_executable'])
    for row in external:
        path = Path(row.get('realpath', row.get('path')))
        actual, _ = hash_file(path, single_link=False)
        require(actual == dict(size_bytes=row['size'], sha256=row['sha256']), 'baseline external file changed: ' + str(path))
    for key in ('uv', 'interpreter'):
        row = config[key]
        actual, _ = hash_file(Path(row['path']), single_link=False)
        require(actual == {key: row[key] for key in ('size_bytes', 'sha256')}, 'live tool/interpreter pin changed')
    summary = dict(prefix_manifest_sha256=manifest_sha, regular_file_count=len(baseline['files']),
                   symlink_count=len(baseline['symlinks']), regular_file_bytes=sum(row[1] for row in baseline['files']),
                   external_file_count=len(external))
    require(json.loads(read_file(run_root / 'baseline-before.json')) == summary
            and json.loads(read_file(run_root / 'baseline-after.json')) == summary, 'baseline receipt mismatch')
    require(0 <= result['elapsed_seconds'] < config['limits']['normal_seconds'], 'parent normal deadline not met')
    for fixture in (False, True):
        stage_root = run_root / 'fixture' if fixture else run_root
        log_root = stage_root / 'logs'
        supervisor = result['fixture_supervisor' if fixture else 'supervisor']
        require(supervisor['status'] == 'completed' and type(supervisor['returncode']) is int
                and supervisor['returncode'] == 0 and supervisor['failure'] is None
                and supervisor['matching_survivors'] == [] and supervisor['mutable_failures'] == []
                and supervisor['sampled_peak_rss_bytes'] <= config['limits']['rss_bytes']
                and supervisor['sampled_mutable_peak_bytes'] <= config['limits']['mutable_bytes'],
                'fixture/installation supervisor did not terminate normally and cleanly')
        require(json.loads(read_file(log_root / 'supervisor.json')) == supervisor, 'supervisor result/log mismatch')
        namespace = json.loads(read_file(log_root / 'namespace.json'))
        stdout = read_file(log_root / 'stdout.log', 4 << 20)
        read_file(log_root / 'stderr.log', 4 << 20)
        require(stdout.splitlines() and json.loads(stdout.splitlines()[0]) == namespace, 'namespace/stdout mismatch')
        scratch, site = stage_root / 'scratch', stage_root / 'site'
        environment = dict(HOME=str(scratch / 'home'), TMPDIR=str(scratch), PATH='/nonexistent',
                           LC_ALL='C.UTF-8', LANG='C.UTF-8', TZ='UTC', SETUPTOOLS_USE_DISTUTILS='stdlib', PWD=str(scratch))
        wheels = [stage_root / 'install_fixture-0.0-py3-none-any.whl'] if fixture else [BASE / row['path'] for row in config['wheels']]
        readonly = [str(prefix), config['uv']['path'], '/driver.py', '/', '/proc', '/dev', *map(str, wheels)]
        require(namespace['kind'] == 'puck-cpu-install-namespace-v1' and namespace['status'] == 'PASS'
                and re.fullmatch(r'net:\[\d+\]', namespace['network'])
                and namespace['parent_network'] == os.readlink('/proc/self/ns/net')
                and namespace['network'] != namespace['parent_network']
                and namespace['environment'] == environment and namespace['readonly_paths'] == readonly,
                'namespace receipt does not match admitted stage')
        expected_uv = [config['uv']['path'], 'pip', 'install', '--target', str(site), '--python', interpreter,
                       '--no-deps', '--no-index', '--offline', '--no-build', '--link-mode', 'copy', '--no-cache',
                       '--no-config', '--no-python-downloads', '--no-compile-bytecode', '--', *map(str, wheels)]
        command = json.loads(read_file(log_root / 'command.json'))
        require(command['uv_argv'] == expected_uv, 'installer argv receipt mismatch')
        argv = ['/usr/bin/bwrap', '--unshare-all', '--unshare-user', '--as-pid-1', '--disable-userns',
                '--die-with-parent', '--cap-drop', 'ALL', '--clearenv', '--hostname', 'palimpsest-install',
                '--ro-bind', str(prefix), str(prefix), '--ro-bind', config['uv']['path'], config['uv']['path'],
                '--ro-bind', str(BASE / 'scripts/install_puck_cpu.py'), '/driver.py']
        for row in baseline['external_libraries']:
            path = row.get('realpath', row.get('path'))
            argv += ['--ro-bind', path, path]
        for path, target in baseline['host_path_aliases']:
            argv += ['--symlink', target, path]
        for path in wheels:
            argv += ['--ro-bind', str(path), str(path)]
        argv += ['--bind', str(site), str(site), '--bind', str(scratch), str(scratch), '--symlink', str(scratch),
                 '/tmp', '--proc', '/proc', '--remount-ro', '/proc', '--dev', '/dev', '--remount-ro', '/dev', '--remount-ro', '/']
        for key, value in environment.items():
            if key != 'PWD':
                argv += ['--setenv', key, value]
        argv += ['--chdir', str(scratch), interpreter, '-I', '-S', '-B', '/driver.py', '--installer-worker',
                 namespace['parent_network'], str(site), str(scratch), *map(str, wheels)]
        require(command['argv'] == argv, 'namespace command receipt mismatch')
    return dict(configuration_sha256=configuration_sha256, source_pin_count=len(SOURCE_PATHS),
                baseline_named_regular_files_rehashed=len(baseline['files']), baseline_symlinks_rechecked=len(baseline['symlinks']),
                baseline_external_files_rehashed=len(external), baseline_prepost_receipts_match=True,
                full_baseline_namespace_recensused_by_auditor=False, both_supervisors_completed_normally=True,
                both_namespace_and_command_receipts_match=True, live_uv_and_interpreter_pins_match=True,
                literal_tool_prepost_byte_checks_scope='source-frozen parent checks; this auditor verifies current tool pins',
                inert_fixture_installed_files_verified=audit_fixture(run_root / 'fixture'))


def audit(run_root, interpreter, configuration_sha256):
    layout_raw = read_file(LAYOUT)
    require(hashlib.sha256(layout_raw).hexdigest() == LAYOUT_SHA, 'layout report changed')
    layout = json.loads(layout_raw)
    require(len(layout['wheels']) == 71 and layout['scope']['unique_normalized_distributions'] == 71,
            'layout distribution count mismatch')
    candidate = json.loads(read_file(BASE / 'docs/plans/puck-cpu-runtime-candidate-v1.json'))
    normalize = lambda value: re.sub(r'[-_.]+', '-', value).lower()
    pins = {normalize(pin.split('==')[0]): pin.split('==')[1] for pin in candidate['target']['candidate_pins']}
    require(len(pins) == 71 and {w['normalized_name']: w['version'] for w in layout['wheels']} == pins,
            'candidate/layout pin mismatch')
    site = run_root / 'site'
    actual, directories, stamps = census(site)
    inventory_raw, result_raw = read_file(run_root / 'inventory.json'), read_file(run_root / 'result.json')
    inventory, result = json.loads(inventory_raw), json.loads(result_raw)
    require(inventory['kind'] == 'puck-cpu-installed-files-v1', 'inventory kind mismatch')
    rows = inventory['entries']
    require(isinstance(rows, list) and len(rows) <= MAX_FILES, 'inventory entry bound exceeded')
    reported = {}
    for row in rows:
        path = canonical(row['path'])
        require(path not in reported and type(row['size_bytes']) is int and row['size_bytes'] >= 0
                and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'invalid/duplicate inventory entry')
        reported[path] = {k: row[k] for k in ('size_bytes', 'sha256')}
    require(reported == actual, 'root inventory differs from independent full installed census')
    require(inventory['file_count'] == len(actual) and inventory['directory_count'] == len(directories)
            and inventory['total_bytes'] == sum(row['size_bytes'] for row in actual.values()),
            'root inventory totals differ from independent census')
    require(result['kind'] == 'puck-cpu-install-result-v1' and result['status'] == 'PASS'
            and result['interpreter'] == interpreter and isinstance(result['supervisor'], dict),
            'root result identity/status/interpreter mismatch')
    require(all(result['claims'].get(key) is value for key, value in CLAIMS.items()), 'root claims mismatch')
    receipts = audit_receipts(run_root, interpreter, configuration_sha256, layout, result)
    owners, members, expected_directories, licenses = {}, {}, set(), set()
    mutable, community, seen_pins = set(), {}, {}
    archive_bytes, expanded_bytes = 0, 0
    for wheel in layout['wheels']:
        name, version, dist_info = wheel['normalized_name'], wheel['version'], wheel['dist_info_root']
        require(name not in seen_pins, 'duplicate expected distribution')
        seen_pins[name] = version
        members[name] = set()
        archive_path = BASE / canonical(wheel['archive_path'])
        archive_hash, archive_stamp = hash_file(archive_path)
        require(archive_hash == dict(size_bytes=wheel['archive_bytes'], sha256=wheel['expected_archive_sha256']),
                'authenticated wheel changed: ' + name)
        archive_bytes += archive_hash['size_bytes']
        with zipfile.ZipFile(archive_path) as archive:
            require(fingerprint(os.fstat(archive.fp.fileno())) == archive_stamp, 'archive changed before ZIP inspection')
            infos = archive.infolist()
            require(len({i.filename for i in infos}) == len(infos), 'duplicate archive member')
            require(len(infos) <= MAX_FILES, 'archive entry bound exceeded')
            metadata_paths = [i.filename for i in infos if not i.is_dir() and i.filename.endswith('.dist-info/METADATA')]
            require(metadata_paths == [wheel['metadata_path']], 'archive METADATA identity changed')
            metadata = email.message_from_bytes(archive.read(metadata_paths[0]))
            require(normalize(metadata['Name']) == name and metadata['Version'] == pins[name], 'archive metadata pins changed')
            for info in infos:
                source = info.filename.rstrip('/') if info.is_dir() else info.filename
                canonical(source)
                unix_type = stat.S_IFMT(info.external_attr >> 16)
                require(unix_type in (0, stat.S_IFREG, stat.S_IFDIR), 'special archive member')
                if info.is_dir():
                    parts = source.split('/')
                    if not (parts[0].endswith('.data') and len(parts) < 3):
                        expected_directories.add(mapped(source))
                    continue
                destination = mapped(source)
                require(destination not in owners, 'wheel mapping collision: ' + destination)
                owners[destination] = name
                members[name].add(destination)
                require(destination in actual, 'missing mapped archive member: ' + destination)
                expanded_bytes += info.file_size
                require(expanded_bytes <= MAX_BYTES, 'archive expanded byte bound exceeded')
                if source == dist_info + '/RECORD':
                    mutable.add(destination)
                elif source.split('/')[0].endswith('.data') and source.split('/')[1] == 'scripts':
                    require(destination == 'bin/community' and name == 'python-louvain' and info.file_size <= MAX_META,
                            'unexpected archive script rewrite')
                    original = archive.read(info)
                    first, separator, rest = original.partition(b'\n')
                    require(first == b'#!python' and separator, 'unexpected community source shebang')
                    expected = ('#!' + interpreter + '\n').encode() + rest
                    require(read_file(site / destination) == expected, 'community changed beyond selected shebang')
                    community[destination] = True
                else:
                    require(hash_member(archive, info) == actual[destination], 'archive payload changed: ' + destination)
                if source.startswith(dist_info + '/licenses/') or source.rsplit('/', 1)[-1].lower().startswith(
                        ('license', 'licence', 'copying', 'notice')):
                    licenses.add(destination)
            require(fingerprint(os.fstat(archive.fp.fileno())) == archive_stamp
                    and fingerprint(archive_path.lstat()) == archive_stamp, 'archive changed during ZIP inspection')
        installed_metadata = email.message_from_bytes(read_file(site / wheel['metadata_path']))
        require(normalize(installed_metadata['Name']) == name and installed_metadata['Version'] == version,
                'installed metadata identity mismatch')
    require(seen_pins == pins and len(mutable) == 71 and len(community) == 1, 'exact71 source mapping mismatch')
    wrappers = [entry for entry in layout['entry_points'] if entry['generates_script_on_linux']]
    require(len(wrappers) == 18, 'entrypoint count mismatch')
    for entry in wrappers:
        destination, name = entry['destination_path'], entry['distribution']
        require(destination not in owners and destination in actual, 'missing/colliding launcher: ' + destination)
        inspect_launcher(read_file(site / destination, 65536), interpreter, entry)
        owners[destination] = name
        members[name].add(destination)
    dist_infos = {wheel['dist_info_root']: wheel for wheel in layout['wheels']}
    installed_dist_infos = {path.split('/')[0] for path in directories if path.split('/')[0].endswith('.dist-info')}
    require(installed_dist_infos == set(dist_infos), 'installed distribution namespace is not exact71')
    installer_extras = []
    for path in actual:
        if path in owners:
            continue
        if path == '.lock':
            require(actual[path]['size_bytes'] == 0, 'root .lock is not inert empty data')
            continue
        parts = path.split('/')
        require(len(parts) == 2 and parts[0] in dist_infos and parts[1] in EXTRA_METADATA,
                'unexpected installed file: ' + path)
        wheel = dist_infos[parts[0]]
        name, leaf = wheel['normalized_name'], parts[1]
        data = read_file(site / path)
        if leaf == 'INSTALLER':
            require(data.strip() == b'uv', 'unexpected INSTALLER contents')
        elif leaf == 'REQUESTED':
            require(data == b'', 'REQUESTED is not empty')
        else:
            parsed = json.loads(data)
            require(isinstance(parsed, dict), 'installer metadata is not an object')
            if leaf == 'direct_url.json':
                url = urlparse(parsed['url'])
                require(url.scheme == 'file' and not url.netloc and not url.query and not url.fragment
                        and unquote(url.path) == str(BASE / wheel['archive_path']),
                        'direct_url is not exact authenticated local wheel path')
                archive_info = parsed.get('archive_info', {})
                declared = archive_info.get('hashes', {}).get('sha256')
                require(declared is None or declared == wheel['expected_archive_sha256'], 'direct_url wheel hash mismatch')
                legacy = archive_info.get('hash')
                require(legacy is None or legacy == 'sha256=' + wheel['expected_archive_sha256'], 'legacy direct_url hash mismatch')
        owners[path] = name
        members[name].add(path)
        installer_extras.append(path)
    for path in actual:
        for parent in PurePosixPath(path).parents:
            if str(parent) != '.':
                expected_directories.add(str(parent))
    require(directories <= expected_directories, 'unexpected installed directory')
    for dist_info, wheel in dist_infos.items():
        name, record_path = wheel['normalized_name'], dist_info + '/RECORD'
        check_record(read_file(site / record_path), record_path, members[name], actual)
    copied, _, _ = census(run_root / 'licences')
    require(set(copied) == licenses, 'licence-copy path set differs from frozen archive predicate')
    require(all(copied[path] == actual[path] for path in licenses), 'licence copy bytes differ from installed source')
    after, after_dirs, after_stamps = census(site, hashes=False)
    require(set(after) == set(actual) and after_dirs == directories and after_stamps == stamps,
            'installed namespace changed during independent audit')
    return dict(distributions=71, archive_count=71, archive_bytes=archive_bytes,
                expanded_archive_bytes=expanded_bytes, installed_file_count=len(actual),
                installed_directory_count_excluding_root=len(directories),
                installed_bytes=sum(row['size_bytes'] for row in actual.values()),
                generated_console_launchers=len(wrappers), rewritten_archive_scripts=len(community),
                installer_metadata_files=len(installer_extras), licence_copy_count=len(licenses),
                root_lock_present='.lock' in actual, zero_pyc_and_pth=True,
                source_payloads_verified=True, installed_RECORD_hashes_and_sizes_verified=True,
                root_inventory_sha256=hashlib.sha256(inventory_raw).hexdigest(),
                root_result_sha256=hashlib.sha256(result_raw).hexdigest(),
                layout_sha256=LAYOUT_SHA, receipts=receipts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, default=BASE / 'runs/puck-cpu-install-01')
    parser.add_argument('--interpreter', required=True)
    parser.add_argument('--configuration-sha256', required=True)
    parser.add_argument('--output', type=Path, default=Path('/tmp/palimpsest-cpu-install-audit-v1.json'))
    args = parser.parse_args()
    require(args.output.parent.resolve() == Path('/tmp') and not args.output.exists(), 'audit output must be fresh /tmp file')
    require(args.interpreter.startswith('/') and not any(c.isspace() for c in args.interpreter), 'invalid selected interpreter')
    require(re.fullmatch('[0-9a-f]{64}', args.configuration_sha256), 'invalid admitted configuration digest')
    started, before = datetime.datetime.now(datetime.timezone.utc).isoformat(), time.monotonic()
    outcome = dict(kind='puck-cpu-install-independent-audit-v1', status='FAIL', started_at_utc=started,
                   target_code_executed=False, installer_executed_by_auditor=False,
                   bounds=dict(max_files=MAX_FILES, max_directories=MAX_DIRS,
                               max_installed_bytes=MAX_BYTES, max_individual_bytes=MAX_FILE, wall_seconds=WALL))
    def alarm(_signal, _frame):
        raise AuditError('180-second independent audit wall bound exceeded')
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, WALL)
    try:
        outcome['verified'] = audit(args.run_root, args.interpreter, args.configuration_sha256)
        outcome['claims'] = CLAIMS
        outcome['status'] = 'PASS'
    except Exception as error:
        outcome['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    outcome['elapsed_seconds'] = time.monotonic() - before
    outcome['ended_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    encoded = (json.dumps(outcome, indent=2, sort_keys=True) + '\n').encode()
    with args.output.open('xb') as stream:
        stream.write(encoded)
    print(json.dumps(dict(path=str(args.output), sha256=hashlib.sha256(encoded).hexdigest(),
                          size_bytes=len(encoded), status=outcome['status'])))
    return 0 if outcome['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
