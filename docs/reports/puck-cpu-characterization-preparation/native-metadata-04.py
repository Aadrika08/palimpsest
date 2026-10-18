#!/usr/bin/env python3
"""Static shared-library closure; no target import or execution."""
from pathlib import Path
import collections, datetime, hashlib, json, os, posixpath, re, signal, stat, subprocess, time

B = Path('/home/utkarsh/.codex/worktrees/0071/brain')
SITE = B / 'runs/puck-cpu-install-01/site'
OLD = Path('/tmp/palimpsest-cpu-characterization-native-metadata-03.json')
OLD_SHA = '79f100aa7622cd4ce53f3463d4ed5fe5e006f01d332a12b825a609e87eb1ef96'
FIRST = Path('/tmp/palimpsest-cpu-characterization-native-metadata-01.json')
FIRST_SHA = '83f871f64a2fdb6d9419000b434d00fa0b9487a22c1dccd5f7bb791a302d261c'
OUT = Path('/tmp/palimpsest-cpu-characterization-native-metadata-04.json')
started = time.monotonic(); deadline = started + 120
aliases = {}; native = {}; systems = {}; edges = []; errors = []; missing = collections.defaultdict(set)
optional_missing = []; optional_edges = []; ambiguities = []; queue = collections.deque(); visited = set(); parser_bytes = 0


def check():
    if time.monotonic() >= deadline: raise RuntimeError('120-second metadata bound')


def fingerprint(s):
    return s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def hashed(path):
    check(); before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > 1 << 30: raise RuntimeError('nonregular/oversize input ' + str(path))
    digest = hashlib.sha256(); count = 0
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC), 'rb') as stream:
        if fingerprint(os.fstat(stream.fileno())) != fingerprint(before): raise RuntimeError('input replaced')
        while block := stream.read(1 << 20): check(); digest.update(block); count += len(block)
        if count != before.st_size or fingerprint(os.fstat(stream.fileno())) != fingerprint(before): raise RuntimeError('input changed')
    if fingerprint(path.lstat()) != fingerprint(before): raise RuntimeError('input changed')
    return dict(path=str(path), size_bytes=count, sha256=digest.hexdigest())


def real(path):
    path = posixpath.normpath(str(path)); hops = 0
    while True:
        parts = Path(path).parts; current = Path('/'); changed = False
        for n, part in enumerate(parts[1:], 1):
            current /= part
            if stat.S_ISLNK(current.lstat().st_mode):
                hops += 1
                if hops > 32: raise RuntimeError('symlink bound')
                target = os.readlink(current); aliases[str(current)] = target
                target = target if target.startswith('/') else str(current.parent / target)
                path = posixpath.normpath(str(Path(target).joinpath(*parts[n + 1:]))); changed = True; break
        if not changed:
            if not stat.S_ISREG(current.lstat().st_mode): raise RuntimeError('host leaf not regular')
            return current


parser = hashed(Path('/usr/bin/readelf'))
helper_pin = hashed(Path(__file__))


def parse_elf(path, row):
    global parser_bytes
    check()
    proc = subprocess.run(['/usr/bin/readelf', '--wide', '--file-header', '--program-headers', '--dynamic', '--', str(path)],
                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env={'LC_ALL': 'C', 'LANG': 'C', 'PATH': '/nonexistent'}, timeout=max(.05, min(8, deadline - time.monotonic())))
    parser_bytes += len(proc.stdout) + len(proc.stderr)
    if parser_bytes > 16 << 20 or proc.returncode: raise RuntimeError('readelf output bound/failure ' + str(path))
    text = proc.stdout.decode(); values = lambda tag: re.findall(r'\(' + tag + r'\).*?\[(.*?)\]', text)
    field = lambda key: next((line.split(':', 1)[1].strip() for line in text.splitlines() if line.lstrip().startswith(key + ':')), None)
    names = values('SONAME'); interp = re.findall(r'Requesting program interpreter:\s*(.*?)\]', text)
    return dict(row, scope='host', elf_class=field('Class'), elf_type=field('Type'), machine=field('Machine'),
                needed=values('NEEDED'), rpath=values('RPATH'), runpath=values('RUNPATH'),
                soname=names[0] if names else None, interpreter=interp[0] if interp else None)


def host(path, reason):
    path = real(path); key = str(path)
    if key not in native:
        row = hashed(path); native[key] = dict(row, reasons=[reason])
        if row['size_bytes'] > 64 << 20: raise RuntimeError('native leaf exceeds parent64MiB bound: ' + key)
        with path.open('rb') as stream: magic = stream.read(4)
        if magic == b'\x7fELF':
            if key not in systems:
                if len(systems) >= 128: raise RuntimeError('128 system ELF bound')
                systems[key] = parse_elf(path, row)
            queue.append(systems[key])
    elif reason not in native[key]['reasons']: native[key]['reasons'].append(reason)
    return key


def expanded_name(item, name):
    origin = str(Path(item['path']).parent)
    return posixpath.normpath(name.replace('${ORIGIN}', origin).replace('$ORIGIN', origin)) if '$ORIGIN' in name or '${ORIGIN}' in name else name


def stop(*_): raise RuntimeError('120-second metadata bound')


def main():
    if OUT.exists(): raise RuntimeError('fresh output exists')
    signal.signal(signal.SIGALRM, stop); signal.setitimer(signal.ITIMER_REAL, 120)
    report = dict(kind='puck-cpu-characterization-native-metadata-v4', status='PARTIAL', root_scope='installed_shared_objects_and_interpreter',
                  runtime_qualified=False, renderer_qualified=False, numerical_imports_executed=False, target_execution_performed=False)
    installed = []
    try:
        old_pin, first_pin = hashed(OLD), hashed(FIRST)
        if old_pin['sha256'] != OLD_SHA or first_pin['sha256'] != FIRST_SHA: raise RuntimeError('preserved metadata pin mismatch')
        old, first = json.loads(OLD.read_bytes()), json.loads(FIRST.read_bytes())
        inventory_path = B / 'runs/puck-cpu-retained-admission-02/inventory.json'; inventory_pin = hashed(inventory_path)
        if inventory_pin['sha256'] != 'd1dac91f2b69e193d6eafc8b6c47a37204bb2cb51925faad5b895dea83701b35': raise RuntimeError('accepted census pin mismatch')
        inventory = json.loads(inventory_path.read_bytes()); rows = {row['path']: row for row in inventory['entries']}
        result_path = B / 'runs/puck-cpu-retained-admission-02/result.json'; result = json.loads(result_path.read_bytes())
        snapshot_pin = hashed(B / 'runs/puck-cpu-retained-admission-02/snapshot.json')
        if result['status'] != 'PASS' or result['claims']['package_preparation_accepted'] is not True or result['snapshot_sha256'] != snapshot_pin['sha256']: raise RuntimeError('accepted receipt chain mismatch')
        report.update(prior_partial_metadata=[old_pin, first_pin], admission_inputs=[inventory_pin, hashed(result_path), snapshot_pin],
                      selection=old['selection'], preparation_correction='ET_DYN named shared library with SONAME remains selected despite PT_INTERP; standalone EXEC remains excluded')
        index = {item['path']: item for item in old['installed_DSO_metadata']}
        for item in first['installed_elf_metadata']:
            if item['soname'] == 'libQt5Core-e7f476e2.so.5.15.16': index[item['path']] = item
        if len(index) != 424 or len(index) > 512: raise RuntimeError('424 DSO selection/count mismatch')
        installed = list(index.values()); package = collections.defaultdict(list)
        for item in installed:
            path = Path(item['path']); relative = path.relative_to(SITE).as_posix(); row = hashed(path)
            if not item['elf_type'].startswith('DYN') or path.lstat().st_nlink != 1 or any(row[k] != item[k] or row[k] != rows[relative][k] for k in ('size_bytes', 'sha256')): raise RuntimeError('DSO binding/type mismatch')
            if item['interpreter'] and not item['soname']: raise RuntimeError('unsupported interpreter-bearing anonymous DYN')
            for name in {path.name, item['soname']} - {None}: package[name].append(item)
        report['selection'] = dict(old['selection'], filename_rule='basename .so/.so.* and ELF ET_DYN; named SONAME permits PT_INTERP',
                                   non_DSO_candidates=[], corrected_shared_DSO='libQt5Core-e7f476e2.so.5.15.16')
        baseline_path = B / 'docs/plans/puck-python-louvain-host-baseline-v1.json'; baseline = json.loads(baseline_path.read_bytes())
        prefix = Path(baseline['python_prefix']); prefix_rows = {row[0]: row for row in baseline['files']}; prefix_index = collections.defaultdict(list)
        for item in old['system_ELF_metadata']:
            path = Path(item['path']); current = hashed(path)
            if any(current[k] != item[k] for k in ('size_bytes', 'sha256')): raise RuntimeError('cached system metadata changed')
            systems[str(path)] = item
            if path.is_relative_to(prefix):
                expected = prefix_rows[path.relative_to(prefix).as_posix()]
                if current['size_bytes'] != expected[1] or current['sha256'] != expected[2]: raise RuntimeError('prefix baseline changed')
                for name in {path.name, item['soname']} - {None}: prefix_index[name].append(item)
                if path == prefix / 'bin/python3.11': queue.append(item)
        registered = {item['path']: item for item in installed + list(systems.values())}
        for row in old['native_files']: host(Path(row['path']), 'preserved03 required host native closure')
        aliases.update(dict(old['aliases']))
        for alias, target in aliases.items():
            if not Path(alias).is_symlink() or os.readlink(alias) != target: raise RuntimeError('preserved host alias changed')
        queue.extend(installed)
        while queue:
            check(); item = queue.popleft()
            if item['path'] in visited: continue
            visited.add(item['path'])
            for original in item['needed'] + ([item['interpreter']] if item['interpreter'] else []):
                name = expanded_name(item, original); found = [registered[name]] if name in registered else package.get(name, []) or prefix_index.get(name, [])
                if found:
                    if len(found) > 1: ambiguities.append(dict(consumer=item['path'], needed=original, candidates=[x['path'] for x in found]))
                    queue.extend(found); edges.append(dict(consumer=item['path'], needed=original, resolutions=[x['path'] for x in found], basis='registered prefix/package provider or conservative union')); continue
                if '/' in name and (not name.startswith('/') or not name.startswith(('/usr/lib/', '/lib64/', '/lib/'))): missing[original].add(item['path']); continue
                try: chosen = host(Path(name) if name.startswith('/') else Path('/usr/lib') / name, 'DT_NEEDED/interpreter by ' + item['path']); edges.append(dict(consumer=item['path'], needed=original, resolutions=[chosen], basis='exact explicit native SONAME/interpreter'))
                except FileNotFoundError: missing[original].add(item['path'])
        prefix_metadata = [item for item in systems.values() if Path(item['path']).is_relative_to(prefix)]
        for item in prefix_metadata:
            for original in item['needed']:
                name = expanded_name(item, original); found = [registered[name]] if name in registered else package.get(name, []) or prefix_index.get(name, [])
                if found: optional_edges.append(dict(consumer=item['path'], needed=original, resolutions=[x['path'] for x in found])); continue
                path = Path(name) if name.startswith('/') else Path('/usr/lib') / name
                try: resolved = real(path); optional_edges.append(dict(consumer=item['path'], needed=original, resolutions=[str(resolved)]))
                except FileNotFoundError: optional_missing.append(dict(consumer=item['path'], needed=original, attempted_path=str(path), scope='optional prefix root, not required four-import closure'))
        report.update(trusted_baseline_input=hashed(baseline_path), prefix_ELF_diagnostic_count=len(prefix_metadata),
                      parent_only_tools_not_worker_mounts=old['parent_only_tools_not_worker_mounts'], source_justifications=old['source_justifications'])
        for row in report['source_justifications'] + report['parent_only_tools_not_worker_mounts']:
            if hashed(Path(row['path'])) != {k: row[k] for k in ('path', 'size_bytes', 'sha256')}: raise RuntimeError('preserved source/tool pin changed')
        if hashed(OLD) != old_pin or hashed(FIRST) != first_pin or hashed(Path('/usr/bin/readelf')) != parser: raise RuntimeError('preserved metadata/parser changed')
        report['status'] = 'COMPLETE' if not missing else 'MISSING'
    except Exception as error: errors.append(type(error).__name__ + ': ' + str(error))
    finally: signal.setitimer(signal.ITIMER_REAL, 0)
    report.update(elapsed_seconds=time.monotonic() - started, bounds=dict(wall_seconds=120, installed_DSOs=512, system_ELFs=128, metadata_output_bytes=16 << 20, native_leaf_bytes=64 << 20),
                  helper_source=helper_pin, trusted_parser=parser, installed_DSO_count=len(installed), system_ELF_count_including_prefix=len(systems), readelf_new_output_bytes=parser_bytes,
                  native_files=[{k: row[k] for k in ('path', 'size_bytes', 'sha256')} for _, row in sorted(native.items())], native_file_reasons={p: r['reasons'] for p, r in sorted(native.items())},
                  aliases=sorted([[p, t] for p, t in aliases.items()]), installed_DSO_metadata=installed, system_ELF_metadata=list(systems.values()), dependency_edges=edges,
                  required_missing_names=sorted(missing), missing_consumers={n: sorted(v) for n, v in missing.items()}, ambiguous_packaged_sonames=ambiguities,
                  optional_prefix_missing=optional_missing, optional_prefix_dependency_edges=optional_edges, oversized_native_files=[r for r in native.values() if r['size_bytes'] > 64 << 20], errors=errors,
                  limitations=['Static conservative installed-DSO+interpreter closure; not measured four-import reachability, dynamic loader success, runtime qualification or renderer evidence.',
                               'All11 frozen prefix ELF metadata are examined diagnostically; optional _crypt requires absent libcrypt.so.1. Prefix bytes remain hashed/readonly bound by parent; every optional extension is not claimed loadable.',
                               'A real crypt import will fail without its ABI dependency; optional diagnostic absence is never substituted, installed, or hidden. Required dependency on it would remain MISSING.',
                               'Packaged SONAME ambiguity uses conservative provider union; RPATH/RTLD/symbol compatibility and dlopen are not executed.',
                               'ldconfig/cache remain conditional source-derived capabilities; EGL/OpenGL dispatchers do not establish vendor/driver/context/device/renderer operation.',
                               'Only trusted readelf parses bytes; no target import/initializer/ELF execution/ldd/model/scene/catalog/scientific operation or CPU writes. Earlier01-03 artifacts remain unchanged.'])
    raw = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode()
    if len(raw) > 16 << 20: raise RuntimeError('16MiB final report bound')
    with OUT.open('xb') as stream: stream.write(raw)
    print(json.dumps(dict(path=str(OUT), size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), status=report['status'],
                          elapsed_seconds=report['elapsed_seconds'], installed_DSOs=len(installed), system_ELFs=len(systems), native_files=len(native), aliases=len(aliases),
                          required_missing_names=sorted(missing), optional_prefix_missing=optional_missing, errors=errors), indent=2))


if __name__ == '__main__': main()
