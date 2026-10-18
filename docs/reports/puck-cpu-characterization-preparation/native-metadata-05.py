#!/usr/bin/env python3
"""Prepare only the explicit host-zlib correction; never import target packages."""
from pathlib import Path
import copy, hashlib, json, os, signal, stat, sys, time

OLD = Path('/tmp/palimpsest-cpu-characterization-native-metadata-04.json')
OLD_SHA = '451e6af507c6e7d181f253430145053f9eaa9404496f8b97cb27d33ec6e88066'
HELPER = Path('/tmp/palimpsest_cpu_characterization_native_metadata_04.py')
HELPER_SHA = '6bc8c65ded4873676cb1cbd7d7ed82770813933ecc6995edcf2734f0bc588f12'
OUT = Path('/tmp/palimpsest-cpu-characterization-native-metadata-05.json')
CACHE = Path('/tmp/palimpsest-cpu-characterization-native-metadata-05-no-bytecode-cache')
ROOT = Path('/usr/lib/libz.so.1')
SITE = Path('/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-install-01/site')
AUTHORITY = ('runtime_qualified', 'renderer_qualified', 'numerical_imports_executed', 'target_execution_performed')
START = time.monotonic()


def check():
    if time.monotonic() - START >= 120: raise RuntimeError('120-second metadata bound')


def stop(*_): raise RuntimeError('120-second metadata bound')


def stamp(s):
    return s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def read_pinned(path, expected, limit):
    check(); before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit: raise RuntimeError('input type/size bound')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC), 'rb') as stream:
        if stamp(os.fstat(stream.fileno())) != stamp(before): raise RuntimeError('input replaced')
        raw = stream.read(limit + 1)
        if stamp(os.fstat(stream.fileno())) != stamp(before): raise RuntimeError('input changed')
    if len(raw) != before.st_size or stamp(path.lstat()) != stamp(before): raise RuntimeError('input changed')
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected: raise RuntimeError('input SHA256 mismatch: ' + str(path))
    return raw, dict(path=str(path), size_bytes=len(raw), sha256=digest)


def main():
    if os.path.lexists(OUT): raise RuntimeError('fresh output already exists')
    signal.signal(signal.SIGALRM, stop); signal.setitimer(signal.ITIMER_REAL, max(.01, 120 - (time.monotonic() - START)))
    report = dict(kind='puck-cpu-characterization-native-metadata-v5', status='PARTIAL', **dict.fromkeys(AUTHORITY, False))
    errors = []; missing = {}; helper = None; watched = []; before = []; additions = []; new_edges = []
    try:
        raw, old_pin = read_pinned(OLD, OLD_SHA, 16 << 20)
        _, helper_pin = read_pinned(HELPER, HELPER_SHA, 64 << 10)
        old = json.loads(raw)
        if old['kind'] != 'puck-cpu-characterization-native-metadata-v4' or old['status'] != 'COMPLETE': raise RuntimeError('metadata04 identity/status mismatch')
        if any(old[k] is not False for k in AUTHORITY) or old['required_missing_names'] or old['errors']: raise RuntimeError('metadata04 authority/closure mismatch')
        if old['installed_DSO_count'] != 424 or len(old['installed_DSO_metadata']) != 424 or old['installed_DSO_count'] > 512: raise RuntimeError('installed DSO count mismatch')
        if old['bounds'] != dict(wall_seconds=120, installed_DSOs=512, system_ELFs=128, metadata_output_bytes=16 << 20, native_leaf_bytes=64 << 20): raise RuntimeError('bounds mismatch')
        replaced = ('kind', 'status', 'helper_source', 'elapsed_seconds', 'native_files', 'native_file_reasons', 'aliases', 'system_ELF_metadata', 'system_ELF_count_including_prefix', 'dependency_edges', 'readelf_new_output_bytes', 'errors', 'required_missing_names', 'missing_consumers', 'limitations')
        report = copy.deepcopy(old)
        report['metadata04_preserved_replaced_fields'] = {k: copy.deepcopy(old[k]) for k in replaced}
        report.update(kind='puck-cpu-characterization-native-metadata-v5', status='PARTIAL')
        if os.path.lexists(CACHE): raise RuntimeError('helper source-import cache prefix must be absent')
        sys.dont_write_bytecode = True
        previous_cache = sys.pycache_prefix; sys.pycache_prefix = str(CACHE)
        sys.path.insert(0, str(HELPER.parent))
        try: import palimpsest_cpu_characterization_native_metadata_04 as helper
        finally: sys.path.pop(0); sys.pycache_prefix = previous_cache
        if Path(helper.__file__) != HELPER or helper.helper_pin != helper_pin: raise RuntimeError('low-level helper pin mismatch')
        helper.started = START; helper.deadline = START + 120
        if helper.parser != old['trusted_parser'] or old['helper_source'] != helper_pin: raise RuntimeError('source/parser pin mismatch')
        own_pin = helper.hashed(Path(__file__))
        watched = [old_pin, helper_pin, own_pin, old['trusted_parser'], old['trusted_baseline_input']] + old['admission_inputs'] + old['source_justifications'] + old['parent_only_tools_not_worker_mounts'] + old['native_files']
        watched = [{k: row[k] for k in ('path', 'size_bytes', 'sha256')} for row in watched]
        unique = {row['path']: row for row in watched}
        if any(unique[row['path']] != row for row in watched): raise RuntimeError('conflicting input pins')
        watched = list(unique.values())
        for row in watched:
            if helper.hashed(Path(row['path'])) != row: raise RuntimeError('preserved input changed: ' + row['path'])
        aliases = dict(old['aliases']); helper.aliases.update(aliases)
        for path, target in aliases.items():
            if not Path(path).is_symlink() or os.readlink(path) != target: raise RuntimeError('preserved alias changed')
        native = {row['path']: dict(row) for row in old['native_files']}
        reasons = copy.deepcopy(old['native_file_reasons'])
        systems = {row['path']: row for row in old['system_ELF_metadata']}
        if len(systems) != old['system_ELF_count_including_prefix'] or len(systems) > 128: raise RuntimeError('system ELF count mismatch')
        queue = []; visited = set()

        def host(path, reason):
            check(); resolved = helper.real(path); key = str(resolved)
            if resolved.lstat().st_size > 64 << 20: raise RuntimeError('64MiB native leaf bound')
            row = helper.hashed(resolved)
            if key in native and native[key] != row: raise RuntimeError('cached native file changed')
            native[key] = row
            if reason not in reasons.setdefault(key, []): reasons[key].append(reason)
            if key not in systems:
                if len(systems) >= 128: raise RuntimeError('128 system ELF bound')
                with resolved.open('rb') as stream:
                    if stream.read(4) != b'\x7fELF': raise RuntimeError('required native root/dependency is not ELF')
                systems[key] = helper.parse_elf(resolved, row); additions.append(systems[key])
            elif any(systems[key][k] != row[k] for k in ('size_bytes', 'sha256')): raise RuntimeError('cached ELF changed')
            queue.append(systems[key]); return key

        zlib = host(ROOT, 'explicit required host root correcting metadata04 unreachable libz.so.1 provider')
        if systems[zlib]['soname'] != 'libz.so.1': raise RuntimeError('explicit zlib SONAME mismatch')
        old_edges = [copy.deepcopy(e) for e in old['dependency_edges'] if e['needed'] == 'libz.so.1']
        bad_provider = str(SITE / 'torchvision.libs/libz.81d90590.so.1')
        if len(old_edges) != 17 or any(e['resolutions'] != [bad_provider] for e in old_edges): raise RuntimeError('known 17-edge correction shape mismatch')
        for edge in report['dependency_edges']:
            if edge['needed'] == 'libz.so.1': edge.update(resolutions=[zlib], basis='explicit reachable /usr/lib/libz.so.1 host fallback; no global packaged SONAME inference')
        while queue:
            check(); item = queue.pop(0)
            if item['path'] in visited: continue
            visited.add(item['path'])
            for original in item['needed'] + ([item['interpreter']] if item['interpreter'] else []):
                name = helper.expanded_name(item, original)
                if '/' in name and not name.startswith(('/usr/lib/', '/lib/', '/lib64/')): raise RuntimeError('unexpected new native dependency path: ' + original)
                path = Path(name) if name.startswith('/') else Path('/usr/lib') / name
                try:
                    chosen = host(path, 'explicit host-zlib transitive dependency by ' + item['path'])
                    edge = dict(consumer=item['path'], needed=original, resolutions=[chosen], basis='explicit reachable host SONAME/interpreter path for zlib correction closure')
                    if not any(e['consumer'] == edge['consumer'] and e['needed'] == original and e['resolutions'] == edge['resolutions'] for e in report['dependency_edges']): new_edges.append(edge)
                except FileNotFoundError: missing.setdefault(original, []).append(item['path'])
        aliases = helper.aliases
        for path, target in aliases.items():
            if not Path(path).is_symlink() or os.readlink(path) != target: raise RuntimeError('native alias changed')
        for row in watched + list(native.values()):
            if helper.hashed(Path(row['path'])) != row: raise RuntimeError('input/native changed at final check')
        report.update(helper_source=own_pin, native_files=[native[k] for k in sorted(native)], native_file_reasons=reasons,
                      aliases=sorted([[p, t] for p, t in aliases.items()]), system_ELF_metadata=list(systems.values()),
                      system_ELF_count_including_prefix=len(systems), dependency_edges=report['dependency_edges'] + new_edges,
                      readelf_new_output_bytes=helper.parser_bytes, required_missing_names=sorted(missing), missing_consumers=missing,
                      correction_provenance=dict(input_metadata04=old_pin, low_level_helper04=helper_pin, explicit_required_host_root=str(ROOT),
                          helper_import_policy='normal source import with absent private cache prefix and bytecode writes disabled',
                          resolved_required_host_root=zlib, old_libz_dependency_edges=old_edges, added_system_ELF_metadata=additions,
                          added_dependency_edges=new_edges, preserved_other_edge_count=len(old['dependency_edges']) - 17,
                          rationale='A packaged SONAME alone does not make its differently named file reachable through another package RPATH; add exact host fallback only.',
                          scope='Static correction of the known libz path omission; no loader execution or proof of the sole actual failure cause.'))
        report['limitations'] = old['limitations'] + ['Metadata05 reuses authenticated metadata04 installed-DSO records; it does not repeat the full installed-tree census or establish every prior packaged-provider edge reachable.',
            'Only the explicit host-zlib root, its exact symlink aliases and transitive host dependency paths are added. No SITE alias, LD_PRELOAD, LD_LIBRARY_PATH, ABI substitution or target execution.',
            'The original 17 libz edges and every overwritten metadata04 field are retained alongside the exact immutable metadata04 pin; optional libcrypt.so.1 absence remains unchanged.']
        report['status'] = 'MISSING' if missing else 'COMPLETE'
    except Exception as error: errors.append(type(error).__name__ + ': ' + str(error))
    report.update(errors=errors, elapsed_seconds=time.monotonic() - START)
    if errors: report['status'] = 'PARTIAL'
    raw = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode()
    if len(raw) > 16 << 20: raise RuntimeError('16MiB final metadata bound')
    try:
        with OUT.open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        check()
        print(json.dumps(dict(path=str(OUT), size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), status=report['status'],
            native_files=len(report.get('native_files', [])), system_ELFs=report.get('system_ELF_count_including_prefix'),
            terminal_elapsed_seconds=time.monotonic() - START, errors=errors), sort_keys=True), flush=True)
        check()
        return 0 if report['status'] == 'COMPLETE' else 1
    finally: signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__': raise SystemExit(main())
