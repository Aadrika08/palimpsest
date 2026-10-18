"""Install only the 71 retained CPU wheels; never execute target package code."""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import sys
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1] if sys.argv[1:2] != ['--installer-worker'] else Path('/')
PYTHON = '/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
UV = '/home/utkarsh/.local/bin/uv'
UV_SHA = '6db762293e2843c7cd7420dd35db124480eebe6b15df1f3ed05407bd905bf55f'
OUTPUT = 'runs/puck-cpu-install-01'
CODE_PATHS = tuple(sorted((
    'scripts/install_puck_cpu.py', 'scripts/build_puck_python_louvain.py',
    'scripts/acquire_puck_cpu_payloads.py', 'src/palimpsest/__init__.py',
    'src/palimpsest/bounded_qualification.py', 'src/palimpsest/evaluate.py',
    'src/palimpsest/puck_execution_files.py', 'src/palimpsest/puck_package_payloads.py',
    'src/palimpsest/puck_build_inputs.py', 'docs/plans/puck-cpu-install-v1.md',
    'docs/plans/puck-cpu-runtime-candidate-v1.json',
    'docs/reports/puck-cpu-footprint-02/assessment.json', 'pyproject.toml', 'uv.lock')))
MiB = 1024 ** 2
LIMITS = dict(normal_seconds=300, hard_seconds=315, rss_bytes=1536*MiB,
              min_free_bytes=4096*MiB, min_available_ram_bytes=2048*MiB,
              mutable_bytes=6144*MiB, max_mutable_entries=100000,
              installed_bytes=3072*MiB, max_files=40000, max_directories=5000,
              max_file_bytes=1024*MiB, report_bytes=16*MiB)
CLAIMS = dict(installed=False, runtime_qualified=False, numerical_imports_executed=False,
              study_authorized=False, collection_authorized=False, qualification_claims=[])


def clock(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('CPU installation deadline exhausted')


def file_hash(path, deadline, maximum=1024*MiB):
    clock(deadline)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ValueError('Expected bounded single-link regular file')
        digest, count = hashlib.sha256(), 0
        while True:
            clock(deadline)
            block = os.read(fd, min(MiB, maximum+1-count))
            if not block:
                break
            count += len(block)
            if count > maximum:
                raise ValueError('File grew beyond its cap')
            digest.update(block)
        def identity(s):
            return s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns
        if count != before.st_size or identity(before) != identity(os.fstat(fd)) or identity(before) != identity(path.lstat()):
            raise ValueError('File changed during hashing')
        return dict(size_bytes=count, sha256=digest.hexdigest())
    finally:
        os.close(fd)


def installer_argv(site, wheels):
    return [UV, 'pip', 'install', '--target', str(site), '--python', PYTHON,
            '--no-deps', '--no-index', '--offline', '--no-build', '--link-mode', 'copy',
            '--no-cache', '--no-config', '--no-python-downloads', '--no-compile-bytecode',
            '--', *map(str, wheels)]


def destination(path, name):
    parts = path.split('/')
    if any(p in ('', '.', '..') for p in parts) or path.startswith('/'):
        raise ValueError('Unsafe wheel path')
    if not parts[0].endswith('.data'):
        return path
    if len(parts) < 3:
        raise ValueError('Incomplete wheel data path')
    prefixes = dict(purelib='', platlib='', data='', scripts='bin/', headers='include/'+name+'/')
    if parts[1] not in prefixes:
        raise ValueError('Unknown wheel data scheme')
    return prefixes[parts[1]] + '/'.join(parts[2:])


def census(root, deadline, *, allow_hooks=False):
    entries, directories, total = [], 0, 0
    for directory, names, files in os.walk(root, followlinks=False, onerror=lambda error: (_ for _ in ()).throw(error)):
        clock(deadline)
        for name in names:
            state = (Path(directory)/name).lstat()
            if not stat.S_ISDIR(state.st_mode):
                raise ValueError('Installed directory is a symlink or special file')
            if name == '__pycache__':
                raise ValueError('Unexpected installed bytecode directory')
            directories += 1
        for name in sorted(files):
            path = Path(directory)/name
            if not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError('Installed leaf is a symlink or non-regular file')
            if path.suffix == '.pyc' or (not allow_hooks and path.suffix == '.pth'):
                raise ValueError('Unexpected installed hook or bytecode')
            row = dict(path=path.relative_to(root).as_posix(), **file_hash(path, deadline))
            entries.append(row)
            total += row['size_bytes']
            if len(entries) > LIMITS['max_files'] or total > LIMITS['installed_bytes']:
                raise ValueError('Installed file/byte census cap exceeded')
        if directories > LIMITS['max_directories']:
            raise ValueError('Installed directory census cap exceeded')
    return dict(kind='puck-cpu-installed-files-v1', entries=sorted(entries, key=lambda r:r['path']),
                file_count=len(entries), directory_count=directories, total_bytes=total)


def make_fixture(root):
    files = {
        'install_fixture/__init__.py': b"raise RuntimeError('fixture must never import')\n",
        'install_fixture.pth': b"import pathlib; pathlib.Path('fixture-hook-executed').write_text('executed')\n",
        'install_fixture-0.0.dist-info/METADATA': b'Metadata-Version: 2.4\nName: install-fixture\nVersion: 0.0\nRequires-Dist: not-installed-for-fixture>=1\n\n',
        'install_fixture-0.0.dist-info/WHEEL': b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n',
    }
    stream = io.StringIO(newline='')
    rows = [[name, 'sha256='+base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode(), str(len(raw))] for name, raw in sorted(files.items())]
    rows.append(['install_fixture-0.0.dist-info/RECORD', '', ''])
    csv.writer(stream).writerows(rows)
    files['install_fixture-0.0.dist-info/RECORD'] = stream.getvalue().encode()
    wheel = root/'install_fixture-0.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2024, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    return wheel


def sandbox_command(baseline, site, scratch, wheels):
    cmd = ['/usr/bin/bwrap', '--unshare-all', '--unshare-user', '--as-pid-1',
           '--disable-userns', '--die-with-parent', '--cap-drop', 'ALL', '--clearenv',
           '--hostname', 'palimpsest-install', '--ro-bind', baseline['python_prefix'], baseline['python_prefix'],
           '--ro-bind', UV, UV, '--ro-bind', str(Path(__file__).resolve()), '/driver.py']
    for row in baseline['external_libraries']:
        path = row.get('realpath', row.get('path'))
        cmd += ['--ro-bind', path, path]
    for path, target in baseline['host_path_aliases']:
        cmd += ['--symlink', target, path]
    for path in wheels:
        cmd += ['--ro-bind', str(path), str(path)]
    cmd += ['--bind', str(site), str(site), '--bind', str(scratch), str(scratch),
            '--symlink', str(scratch), '/tmp', '--proc', '/proc', '--remount-ro', '/proc',
            '--dev', '/dev', '--remount-ro', '/dev', '--remount-ro', '/']
    env = dict(HOME=str(scratch/'home'), TMPDIR=str(scratch), PATH='/nonexistent',
               LC_ALL='C.UTF-8', LANG='C.UTF-8', TZ='UTC', SETUPTOOLS_USE_DISTUTILS='stdlib')
    for key, value in env.items():
        cmd += ['--setenv', key, value]
    cmd += ['--chdir', str(scratch), PYTHON, '-I', '-S', '-B', '/driver.py',
            '--installer-worker', os.readlink('/proc/self/ns/net'), str(site), str(scratch), *map(str,wheels)]
    return cmd


def installer_worker(arguments):
    parent_net, site_raw, scratch_raw, *raw_wheels = arguments
    site, scratch = Path(site_raw), Path(scratch_raw)
    expected = dict(HOME=str(scratch/'home'), TMPDIR=str(scratch), PATH='/nonexistent', LC_ALL='C.UTF-8',
                    LANG='C.UTF-8', TZ='UTC', SETUPTOOLS_USE_DISTUTILS='stdlib', PWD=str(scratch))
    if dict(os.environ) != expected or Path.cwd() != scratch:
        raise ValueError('Installer environment differs')
    network = os.readlink('/proc/self/ns/net')
    if network == parent_net or len(Path('/proc/net/route').read_text().splitlines()) != 1:
        raise ValueError('Installer private network check failed')
    readonly = [Path(PYTHON).parents[1], Path(UV), Path('/driver.py'), Path('/'), Path('/proc'), Path('/dev'), *map(Path,raw_wheels)]
    if not all(os.statvfs(p).f_flag & os.ST_RDONLY for p in readonly):
        raise ValueError('Installer input mount is writable')
    if any(os.statvfs(p).f_flag & os.ST_RDONLY for p in (site,scratch)):
        raise ValueError('Installer output mount is read-only')
    for name, value in ((resource.RLIMIT_AS,2048*MiB), (resource.RLIMIT_CPU,120),
                        (resource.RLIMIT_FSIZE,1024*MiB), (resource.RLIMIT_NOFILE,256)):
        resource.setrlimit(name,(value,value))
    print(json.dumps(dict(kind='puck-cpu-install-namespace-v1',status='PASS',network=network,
                         parent_network=parent_net,readonly_paths=list(map(str,readonly)),environment=expected)),flush=True)
    os.execve(UV, installer_argv(site,raw_wheels), expected)


def mutable_usage(roots):
    total, count = 0, 0
    pending = list(roots)
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    try:
                        state = entry.stat(follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    count += 1
                    if count > LIMITS['max_mutable_entries']:
                        raise ValueError('Mutable installer namespace entry cap')
                    if stat.S_ISDIR(state.st_mode):
                        pending.append(Path(entry.path))
                    elif stat.S_ISREG(state.st_mode):
                        total += state.st_size
                    elif stat.S_ISLNK(state.st_mode) and Path(entry.path).is_relative_to(roots[1]):
                        total += state.st_size  # UV temporary-cache links: count the inode, never follow.
                    else:
                        raise ValueError('Mutable installer namespace contains special file')
        except FileNotFoundError:
            continue  # UV removes temporary cache/extraction directories during normal operation.
    return total


def run_stage(baseline, site, scratch, wheels, logs, normal, hard, state):
    from palimpsest.bounded_qualification import supervised, write_new
    stop, failures, peak = threading.Event(), [], [0]
    def watch():
        while not stop.is_set():
            try:
                peak[0] = max(peak[0],mutable_usage((site,scratch)))
                if peak[0] > LIMITS['mutable_bytes']:
                    raise ValueError('Sampled mutable installer byte threshold')
            except Exception as error:
                failures.append(str(error))
                group = state.get('group')
                if group:
                    try: os.killpg(group,signal.SIGTERM)
                    except ProcessLookupError: pass
                return
            stop.wait(.1)
    watcher = threading.Thread(target=watch,daemon=True)
    watcher.start()
    command = sandbox_command(baseline,site,scratch,wheels)
    write_new(logs/'command.json',dict(argv=command,uv_argv=installer_argv(site,wheels)))
    try:
        result = supervised(command,logs,cwd=ROOT,normal_deadline=normal,hard_deadline=hard,
                            rss_bytes=LIMITS['rss_bytes'],output_bytes=4*MiB,
                            min_free_bytes=LIMITS['min_free_bytes'],max_processes=3,
                            output_root=logs,guard_state=state,output_namespace_limits=(8,1))
    finally:
        stop.set()
        watcher.join(timeout=1)
    result.update(sampled_mutable_peak_bytes=peak[0],mutable_sampling_seconds=.1,mutable_failures=failures)
    write_new(logs/'supervisor.json',result)
    if result['status'] != 'completed' or failures or watcher.is_alive():
        raise ValueError('Installer stage failed: '+str(result))
    raw = (logs/'stdout.log').read_bytes()
    probe = json.loads(raw.splitlines()[0])
    if probe.get('kind') != 'puck-cpu-install-namespace-v1' or probe.get('status') != 'PASS':
        raise ValueError('Installer namespace probe missing')
    write_new(logs/'namespace.json',probe)
    return result


def parent(config_path, digest):
    sys.path[:0] = [str(ROOT/'src'),str(ROOT/'scripts')]
    import acquire_puck_cpu_payloads as acquisition
    import build_puck_python_louvain as build
    from palimpsest.bounded_qualification import hard_guard, reserve_output, write_new
    from palimpsest.puck_execution_files import _HeldFileCore
    from palimpsest.puck_package_payloads import verify_wheel
    if os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH'):
        raise ValueError('Undeclared parent loader environment')
    started = time.monotonic()
    normal, hard = started+LIMITS['normal_seconds'],started+LIMITS['hard_seconds']
    if Path(sys.executable).resolve() != Path(PYTHON) or file_hash(config_path,normal,MiB)['sha256'] != digest:
        raise ValueError('Installer configuration/interpreter differs')
    config = json.loads(config_path.read_bytes())
    if config['kind'] != 'puck-cpu-install-v1' or config['output'] != OUTPUT or config['limits'] != LIMITS:
        raise ValueError('Unsupported installation configuration')
    if tuple(row['path'] for row in config['sources']) != CODE_PATHS:
        raise ValueError('Source capsule membership differs')
    if len(config['wheels']) != 71 or config['uv']['path'] != UV or config['uv']['sha256'] != UV_SHA:
        raise ValueError('Installer/wheel selection differs')
    if file_hash(Path(UV),normal) != {k:config['uv'][k] for k in ('size_bytes','sha256')}:
        raise ValueError('Pinned UV changed')
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    if available < LIMITS['min_available_ram_bytes'] or shutil.disk_usage(ROOT).free < LIMITS['min_free_bytes']:
        raise ValueError('Installation resource admission failed')
    output = ROOT/OUTPUT
    entries = [{k:row[k] for k in ('path','size_bytes','sha256')} for row in [*config['sources'],*config['wheels'],config['host_baseline']]]
    entries.append(dict(path=config_path.relative_to(ROOT).as_posix(),**file_hash(config_path,normal,MiB)))
    entries.sort(key=lambda r:r['path'])
    with _HeldFileCore(ROOT,entries,normal,limits=(100,256*MiB,512*MiB)) as held:
        held.recheck()
    reserve_output(output,{'sources':{'root':str(ROOT),'files':entries}})
    for path in ('site','scratch','scratch/home','fixture','fixture/site','fixture/scratch','fixture/scratch/home','logs','fixture/logs','licences'):
        (output/path).mkdir(mode=0o700)
    write_new(output/'configuration.json',config)
    result = dict(kind='puck-cpu-install-result-v1',status='FAIL',claims=dict(CLAIMS),interpreter=PYTHON,
                  configuration_sha256=digest,started_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                  resource_admission=dict(mem_available_bytes=available,disk_free_bytes=shutil.disk_usage(ROOT).free))
    state = {}
    with hard_guard(hard,state):
        try:
            with _HeldFileCore(ROOT,entries,normal,limits=(100,256*MiB,512*MiB)) as held:
                candidate = json.loads(held.read('docs/plans/puck-cpu-runtime-candidate-v1.json',MiB))
                if sorted(row['name']+'=='+row['version'] for row in config['wheels']) != candidate['target']['candidate_pins']:
                    raise ValueError('Exact candidate wheel pins differ')
                baseline = json.loads(held.read(config['host_baseline']['path'],MiB))
                before = build.verify_baseline(baseline,normal)
                write_new(output/'baseline-before.json',before)
                checked = []
                for row in config['wheels']:
                    fd = os.open(ROOT/row['path'],os.O_RDONLY|os.O_NOFOLLOW)
                    try:
                        checked.append(verify_wheel(fd,expected={k:row[k] for k in ('name','version','filename','size_bytes','sha256','metadata_sha256')},
                            limits=dict(max_members=32768,max_uncompressed_bytes=2048*MiB,max_member_bytes=1024*MiB,max_metadata_bytes=4*MiB),deadline=normal))
                    finally: os.close(fd)
                acquisition.write_report(output/'wheel-verification.json',dict(wheels=checked),LIMITS['report_bytes'])
                fixture = make_fixture(output/'fixture')
                result['fixture_supervisor'] = run_stage(baseline,output/'fixture/site',output/'fixture/scratch',[fixture],output/'fixture/logs',normal,hard,state)
                with zipfile.ZipFile(fixture) as archive:
                    for name in ('install_fixture/__init__.py','install_fixture.pth'):
                        if (output/'fixture/site'/name).read_bytes() != archive.read(name):
                            raise ValueError('Fixture inert code changed')
                if list((output/'fixture').rglob('fixture-hook-executed')):
                    raise ValueError('Fixture hook executed')
                write_new(output/'fixture/inventory.json',census(output/'fixture/site',normal,allow_hooks=True))
                held.recheck()
                result['supervisor'] = run_stage(baseline,output/'site',output/'scratch',[ROOT/row['path'] for row in config['wheels']],output/'logs',normal,hard,state)
                inventory = census(output/'site',normal)
                actual = {row['path']:row for row in inventory['entries']}
                licences = []
                for wheel in checked:
                    for member in wheel['members']:
                        if member['path'].endswith('/'):
                            continue
                        target = destination(member['path'],wheel['name'])
                        if target.endswith('.dist-info/RECORD') or '.data/scripts/' in member['path']:
                            continue
                        if target not in actual or any(actual[target][k] != member[k] for k in ('size_bytes','sha256')):
                            raise ValueError('Installed immutable payload changed: '+target)
                    for member in wheel['licence_candidates']:
                        target = destination(member['path'],wheel['name'])
                        copied = output/'licences'/target
                        copied.parent.mkdir(parents=True,exist_ok=True)
                        with copied.open('xb') as sink:
                            sink.write((output/'site'/target).read_bytes())
                            sink.flush();os.fsync(sink.fileno())
                        if file_hash(copied,normal) != {k:member[k] for k in ('size_bytes','sha256')}:
                            raise ValueError('Copied licence bytes differ')
                        licences.append(dict(path=target,**file_hash(copied,normal)))
                acquisition.write_report(output/'inventory.json',inventory,LIMITS['report_bytes'])
                write_new(output/'licences.json',dict(entries=licences))
                after = build.verify_baseline(baseline,normal)
                if before != after or file_hash(Path(UV),normal) != {k:config['uv'][k] for k in ('size_bytes','sha256')}:
                    raise ValueError('Trusted host/tool changed')
                write_new(output/'baseline-after.json',after)
                held.recheck()
                result.update(status='PASS',file_count=inventory['file_count'],directory_count=inventory['directory_count'],
                              installed_bytes=inventory['total_bytes'],licence_file_count=len(licences))
                result['claims']['installed'] = True
        except Exception as error:
            result.update(error_type=type(error).__name__,error=str(error))
        result['elapsed_seconds'] = time.monotonic()-started
        write_new(output/'result.json',result)
        clock(normal)
    return result


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--installer-worker':
        installer_worker(sys.argv[2:])
        return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',required=True,type=Path)
    parser.add_argument('--sha256',required=True)
    args = parser.parse_args()
    if os.getpgrp()!=os.getpid(): os.setsid()
    result = parent(args.configuration,args.sha256)
    print(json.dumps(result,sort_keys=True),flush=True)
    return 0 if result['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
