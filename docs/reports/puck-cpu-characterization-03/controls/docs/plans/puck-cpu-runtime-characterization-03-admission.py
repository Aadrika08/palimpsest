"""Fixed data-only observation03 preflight; creates no allocation or target process."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import sys
import time
import types

ROOT = Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONFIGURATION = ROOT/'docs/plans/puck-cpu-runtime-characterization-03.json'
CONFIG_SHA = '69cc87fb68e3c745196b3435c4caaa547ad3bb120ceac6d4834d6b24eecb4e49'
AUDITOR = ROOT/'scripts/audit_puck_cpu_runtime_characterization.py'
AUDITOR_SHA = 'be7e1321356c554750baa6e0982dc939a23546eca1574b8f5f68b2bbdec3afa4'
PYTHON = '/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
FALSE = dict(runtime_qualified=False, native_authorized=False, collection_authorized=False,
             study_authorized=False, executable=False, qualification_claims=[])


def require(value, message):
    if not value: raise ValueError(message)


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def trusted_read(path, maximum):
    require(path.resolve(strict=True) == path, 'Real fixed control path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= maximum, 'Bounded single-link control required')
        with os.fdopen(os.dup(fd), 'rb') as stream: raw = stream.read(maximum+1)
        require(len(raw) == before.st_size and stamp(os.fstat(fd)) == stamp(path.lstat()) == stamp(before), 'Control changed while read')
        return raw, stamp(before)
    finally: os.close(fd)


def resources():
    path = Path('/proc/meminfo'); fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd); raw = os.read(fd, 65537)
        require(len(raw) <= 65536 and stamp(before) == stamp(os.fstat(fd)) == stamp(path.lstat()), 'Bounded memory snapshot changed identity')
    finally: os.close(fd)
    available = int(next(line.split()[1] for line in raw.decode().splitlines() if line.startswith('MemAvailable:')))*1024
    limits = resource.getrlimit(resource.RLIMIT_NOFILE); free = shutil.disk_usage(ROOT).free
    return dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), mem_available_bytes=available,
                project_free_bytes=free, nofile_soft=limits[0], nofile_hard=limits[1])


def resource_check(value):
    require(value['mem_available_bytes'] >= 2 << 30 and value['project_free_bytes'] >= 4 << 30 and min(value['nofile_soft'], value['nofile_hard']) >= 40000, 'Fresh RAM/disk/descriptor admission failed')


def preflight(started, report):
    require(len(sys.argv) == 1 and Path(sys.executable).resolve() == Path(PYTHON)
            and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
            and 'LD_PRELOAD' not in os.environ and 'LD_LIBRARY_PATH' not in os.environ, 'Original isolated no-argument interpreter and loader environment required')
    before = resources(); report['resources_before'] = before; resource_check(before)
    own_raw, own_stamp = trusted_read(Path(__file__), 65536)
    report['control_sha256'] = hashlib.sha256(own_raw).hexdigest()
    auditor_raw, auditor_stamp = trusted_read(AUDITOR, 1 << 20)
    require(hashlib.sha256(auditor_raw).hexdigest() == AUDITOR_SHA, 'Frozen independent auditor changed')
    module = types.ModuleType('_frozen_observation03_auditor'); module.__file__ = str(AUDITOR)
    exec(compile(auditor_raw, str(AUDITOR), 'exec'), module.__dict__)
    u = module; initial = {AUDITOR: auditor_stamp}; before_fds = len(os.listdir('/proc/self/fd'))
    def checked(path, expected=None, maximum=32 << 20):
        raw, identity = u.initial_read(path, maximum)
        require(path not in initial or initial[path] == identity, 'Input changed between preliminary reads')
        initial[path] = identity
        if expected is not None: require(len(raw) == expected['size_bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'], 'Frozen input byte pin differs')
        return raw
    raw = checked(CONFIGURATION, dict(size_bytes=20311, sha256=CONFIG_SHA), 1 << 20); config = u.decode(raw)
    require(raw == (json.dumps(config, sort_keys=True, indent=2, allow_nan=False)+'\n').encode(), 'Frozen configuration encoding differs')
    observation = u.decode(checked(ROOT/u.OBSERVATION_PINS['observation_configuration']['path'], u.OBSERVATION_PINS['observation_configuration']))
    proposal = u.decode(checked(ROOT/u.PROPOSAL_PIN['path'], u.PROPOSAL_PIN)); u.validate_configuration(config, observation, proposal)
    pins = {row['path']: row for row in config['sources']+config['inputs']}
    require(len(pins) == 82, 'Exact19 source plus63 input closure required')
    for row in pins.values(): checked(ROOT/row['path'], row)
    p, a, r, helpers = u.support()
    for path, identity in initial.items(): p.remember(path, identity)
    get = lambda role: u.decode(p.read(ROOT/config['roles'][role]))
    new_paths = [ROOT/u.OUTPUT]+[ROOT/(u.OUTPUT+'-external-cli'+suffix) for suffix in ('.stdout', '.stderr', '-transport.json')]
    missing = [ROOT/'runs/puck-cpu-runtime-characterization-01/baseline-after.json']
    for allocation, leaves in (('puck-cpu-install-01', ('inventory.json', 'licences.json', 'baseline-after.json', 'logs/namespace.json')),
                               ('puck-cpu-retained-admission-01', ('inventory.json', 'snapshot.json', 'baseline-after.json'))):
        missing.extend(ROOT/'runs'/allocation/leaf for leaf in leaves)
    def absent(): require(all(not os.path.lexists(path) for path in new_paths+missing), 'New output exists or historical missing receipt was filled')
    def history():
        values = [get(role) for role in ('observation_result', 'observation_report', 'observation_audit', 'observation_index', 'observation_terminal')]
        u.validate_observation02(observation, *values, pins); index = values[3]; entries = index.get('entries')
        require(type(entries) is list and 1 <= len(entries) <= 512 and type(index.get('file_count')) is int and index['file_count'] == len(entries), 'Historical evidence index count differs')
        u.pin_rows(entries, len(entries)); require(index['total_bytes'] == sum(row['size_bytes'] for row in entries), 'Historical index byte total differs')
        for row in entries: p.hashed(ROOT/u.ARCHIVE/row['path'], {key: row[key] for key in ('size_bytes', 'sha256')})
        accepted, old, proof, snapshot = (get(role) for role in ('accepted_configuration', 'accepted_result', 'accepted_audit', 'accepted_snapshot'))
        require(pins[u.ROLES['accepted_configuration']]['sha256'] == u.ACCEPTED_SHA and old['status'] == proof['status'] == 'PASS'
                and old['claims']['package_preparation_accepted'] is proof['package_preparation_accepted'] is True
                and old['configuration_sha256'] == proof['verified']['configuration_sha256'] == u.ACCEPTED_SHA
                and old['snapshot_sha256'] == pins[u.ROLES['accepted_snapshot']]['sha256'], 'Accepted data preparation binding differs')
        for key in ('runtime_qualified', 'numerical_imports_executed', 'study_authorized', 'collection_authorized'): require(old['claims'][key] is proof[key] is False, 'Preparation authority changed')
        prior, result, audit = (get(role) for role in ('prior_configuration', 'prior_result', 'prior_audit'))
        for role, digest in zip(('prior_configuration', 'prior_result', 'prior_audit'), u.PRIOR_SHAS, strict=True): require(pins[u.ROLES[role]]['sha256'] == digest, 'Historical01 byte identity differs')
        u.claims(result); u.claims(audit)
        require(result['status'] == 'FAIL' and audit['status'] == 'PRESERVED_FAILURE_VERIFIED' and audit['ordinary_imports_observed'] is False
                and audit['native_qualified'] is False and result['configuration_sha256'] == u.PRIOR_SHAS[0], 'Historical01 failure differs')
        require(len(accepted['sources']) == 16 and len(prior['sources']) == 14, 'Historical source counts differ')
        required = set(u.OLD_ROLES.values())
        for value, archive in ((accepted, u.ACCEPTANCE), (prior, u.PRIOR)):
            for row in value['sources']:
                name = archive+'/source/'+u.relative(row['path']); required.add(name)
                require(name in pins and all(pins[name][key] == row[key] for key in ('size_bytes', 'sha256')), 'Historical source capsule differs')
        require(required == {row['path'] for row in observation['inputs']}, 'Historical42 input closure differs')
        for path, digest in (('runs/puck-cpu-install-01/result.json', r.ORIGINAL_SHA), ('runs/puck-cpu-retained-admission-01/result.json', r.PRIOR_ADMISSION_SHA)):
            payload = p.read(ROOT/path); require(hashlib.sha256(payload).hexdigest() == digest and u.decode(payload)['status'] == 'FAIL', 'Original failed result differs')
        return snapshot
    absent(); snapshot = history()
    inventory, layout, native, baseline = (get(role) for role in ('inventory', 'layout', 'native_metadata', 'baseline'))
    site = ROOT/u.SITE; files, directories, site_stamps = r.census(site)
    require(files == r.rows_to_map(inventory['entries']) and directories == set(layout['predicted_destination_directories']) and snapshot['site_root'] == str(site)
            and (len(files), len(directories), sum(row['size_bytes'] for row in files.values())) == u.SITE_COUNTS, 'Complete accepted SITE differs')
    require(pins[u.ROLES['native_metadata']]['sha256'] == u.NATIVE_SHA and native['kind'] == 'puck-cpu-characterization-native-metadata-v5'
            and native['status'] == 'COMPLETE' and native['root_scope'] == 'installed_shared_objects_and_interpreter'
            and native['required_missing_names'] == native['errors'] == native['oversized_native_files'] == []
            and (len(native['native_files']), len(native['aliases']), native['system_ELF_count_including_prefix'], len([row for row in native['dependency_edges'] if row.get('needed') == 'libz.so.1'])) == u.NATIVE_COUNTS
            and any(row['needed'] == 'libcrypt.so.1' for row in native['optional_prefix_missing']), 'Native05 closure differs')
    for key in ('numerical_imports_executed', 'target_execution_performed', 'runtime_qualified', 'renderer_qualified'): require(native[key] is False, 'Static native metadata overclaims')
    def host_bytes():
        for row in native['native_files']:
            require(type(row['path']) is str and (row['path'].startswith('/usr/lib/') or row['path'] in ('/usr/bin/ldconfig', '/etc/ld.so.cache')) and str(Path(row['path'])) == row['path'] and '..' not in Path(row['path']).parts, 'Selected native path differs')
            p.hashed(Path(row['path']), {key: row[key] for key in ('size_bytes', 'sha256')}, single_link=False, limit=64 << 20)
        for filename, target in native['aliases']+baseline['host_path_aliases']:
            path = Path(filename); info = path.lstat(); require(stat.S_ISLNK(info.st_mode) and os.readlink(path) == target, 'Native alias changed'); p.remember(path, a.fingerprint(info))
        for row in baseline['external_libraries']+[baseline['bwrap_executable']]: p.hashed(Path(row.get('realpath') or row['path']), dict(size_bytes=row['size'], sha256=row['sha256']), single_link=False, limit=64 << 20)
    host_bytes(); prefix = u.prefix_inventory(Path(baseline['python_prefix']), p, a)
    require(all(prefix[key] == baseline[key] for key in prefix) and (len(prefix['files']), len(prefix['symlinks'])) == u.BASELINE_COUNTS, 'Complete trusted Python prefix differs')
    history(); host_bytes()
    for row in pins.values(): p.hashed(ROOT/row['path'], {key: row[key] for key in ('size_bytes', 'sha256')}, limit=32 << 20)
    _, final_directories, final_stamps = r.census(site, hashes=False)
    require(final_directories == directories and final_stamps == site_stamps, 'SITE changed during preflight')
    for path, identity in p.STAMPS.items(): require(a.fingerprint(path.lstat()) == identity, 'Pinned input or baseline changed during preflight')
    require(trusted_read(Path(__file__), 65536) == (own_raw, own_stamp), 'Admission control source changed')
    absent(); after = resources(); report['resources_after'] = after; resource_check(after); require(len(os.listdir('/proc/self/fd')) == before_fds and len(os.listdir('/proc/self/task')) == 1, 'Control descriptor/thread closure failed')
    require(time.monotonic()-started < 180, 'Late admission')
    return dict(resources_before=before, resources_after=after, source_pins=19, input_pins=63, roles=19,
        site_files=len(files), site_directories=len(directories), site_bytes=u.SITE_COUNTS[2], native_files=29, native_aliases=23,
        python_prefix_files=4233, python_prefix_symlinks=1048, prefix_manifest_sha256=prefix['prefix_manifest_sha256'],
        source_epoch='32d1dc690d93ffdfa820bcbe871515266acde5b0', configuration_sha256=CONFIG_SHA, auditor_sha256=AUDITOR_SHA,
        control_sha256=hashlib.sha256(own_raw).hexdigest(), helper_sources=helpers, historical_missing_receipts=8,
        new_paths_absent=[str(path.relative_to(ROOT)) for path in new_paths], fingerprints=len(p.STAMPS), fd_count_before=before_fds, fd_count_after=before_fds)


def main():
    started = time.monotonic(); report = dict(FALSE, kind='puck-cpu-observation03-data-admission-v1', status='NOT_ADMITTED', target_code_executed=False, allocation_reserved=False, configuration_sha256=CONFIG_SHA, auditor_sha256=AUDITOR_SHA, normal_seconds=180, min_ram_bytes=2 << 30, min_disk_bytes=4 << 30, min_nofile=40000)
    def expired(signum, frame): raise TimeoutError('180-second data admission deadline')
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, 180)
    try:
        try: report.update(verified=preflight(started, report), status='DATA_ONLY_ADMITTED')
        except Exception as error: report['error'] = type(error).__name__+': '+str(error)[:2048]
        report['elapsed_seconds'] = time.monotonic()-started
        require(report['elapsed_seconds'] < 180, 'Late admission publication')
        payload = (json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
        require(len(payload) <= 65536 and time.monotonic()-started < 180, 'Late or oversized admission serialization')
        print(payload.decode(), end='', flush=True)
        return 0 if report['status'] == 'DATA_ONLY_ADMITTED' and time.monotonic()-started < 180 else 1
    except Exception: return 1
    finally: signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__': raise SystemExit(main())
