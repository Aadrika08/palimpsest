"""Build native metadata v6 for the held public episode; read-only on the host.

Inputs: the accepted v5 closure document, the observed episode native maps
(census v2-held-entry h1) and one GLVND EGL vendor JSON. Every leaf is re-hashed
on the host and must equal its input pin; only SONAME aliases that the host
already links directly are added; dynamic leaves are the explicit constant below,
never inferred. The result is validated with the v6 planner contract and written
once to a new file. No subprocess is spawned and no host file is modified.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
KIND = 'puck-cpu-characterization-native-metadata-v6'
SCOPE = 'installed_shared_objects_interpreter_and_declared_dynamic_leaves'
OBSERVED_KIND = 'diagnostic-held-episode-native-maps-v1'
# Declared, not ELF-walk inferred: leaves the held episode maps through dlopen
# (GLVND/PyOpenGL, the Mesa EGL vendor, gallium/llvmpipe, LLVM and their closure)
# or through glibc data mappings (gconv, C.UTF-8 locale), as observed by census h1.
EPISODE_DYNAMIC_LEAVES = tuple(sorted((
    '/usr/lib/gconv/gconv-modules.cache', '/usr/lib/libEGL.so.1.1.0', '/usr/lib/libEGL_mesa.so.0.0.0',
    '/usr/lib/libGLdispatch.so.0.0.0', '/usr/lib/libLLVM.so.22.1', '/usr/lib/libOpenGL.so.0.0.0',
    '/usr/lib/libSPIRV-Tools.so', '/usr/lib/libX11-xcb.so.1.0.0', '/usr/lib/libdrm.so.2.134.0',
    '/usr/lib/libdrm_amdgpu.so.1.134.0', '/usr/lib/libdrm_intel.so.1.134.0', '/usr/lib/libedit.so.0.0.78',
    '/usr/lib/libelf-0.196.so', '/usr/lib/libexpat.so.1.12.4', '/usr/lib/libffi.so.8.5.0',
    '/usr/lib/libgallium-26.2.2-arch1.1.so', '/usr/lib/libgbm.so.1.0.0', '/usr/lib/libicudata.so.78.3',
    '/usr/lib/libicuuc.so.78.3', '/usr/lib/libncursesw.so.6.6', '/usr/lib/libpciaccess.so.0.11.1',
    '/usr/lib/libsensors.so.5.0.0', '/usr/lib/libwayland-client.so.0.26.0', '/usr/lib/libxcb-dri3.so.0.1.0',
    '/usr/lib/libxcb-present.so.0.0.0', '/usr/lib/libxcb-randr.so.0.1.0', '/usr/lib/libxcb-shm.so.0.0.0',
    '/usr/lib/libxcb-sync.so.1.0.0', '/usr/lib/libxcb-xfixes.so.0.0.0', '/usr/lib/libxml2.so.16.1.4',
    '/usr/lib/libxshmfence.so.1.0.0', '/usr/lib/libzstd.so.1.5.7', '/usr/lib/locale/C.utf8/LC_CTYPE',
    '/usr/lib/locale/locale-archive')))
LIMITATIONS = [
    'Dynamic leaves come from one unguarded diagnostic census observation; held characterization-04 must re-observe them.',
    'The v5 ELF dependency closure is carried forward unchanged; no ELF closure is recomputed here.',
    'Only direct host SONAME symlinks are added as aliases; other link names are not bound.',
    'This metadata grants no renderer, runtime, native or collection authority.',
]


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path, maximum):
    with open(path, 'rb') as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('Input exceeds its bound: ' + str(path))
    return raw


def _host(host_root, path):
    return Path(host_root) / path.lstrip('/')


def _hash_leaf(host_root, path):
    """Hash one regular host leaf through a nofollow descriptor; refuse links."""
    try:
        fd = os.open(_host(host_root, path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as error:
        raise ValueError('Native leaf is not an openable regular file: ' + path) from error
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Native leaf is not a regular file: ' + path)
        digest = hashlib.sha256(); size = 0
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            size += len(chunk); digest.update(chunk)
        if size != before.st_size or os.fstat(fd).st_mtime_ns != before.st_mtime_ns:
            raise ValueError('Native leaf changed while hashed: ' + path)
        return dict(path=path, size_bytes=size, sha256=digest.hexdigest())
    finally:
        os.close(fd)


def soname(host_root, path):
    """DT_SONAME of a 64-bit little-endian ELF shared object, or None for other files."""
    with open(_host(host_root, path), 'rb') as stream:
        header = stream.read(64)
        if len(header) < 64 or header[:4] != b'\x7fELF' or header[4] != 2 or header[5] != 1:
            return None
        number = lambda raw, start, size: int.from_bytes(raw[start:start + size], 'little')
        phoff, phentsize, phnum = number(header, 32, 8), number(header, 54, 2), number(header, 56, 2)
        if phentsize < 56 or phnum > 256:
            raise ValueError('ELF program headers are unbounded: ' + path)
        stream.seek(phoff); table = stream.read(phentsize * phnum)
        loads = []; dynamic = None
        for index in range(phnum):
            entry = table[index*phentsize:(index+1)*phentsize]
            kind, offset, vaddr, filesz = number(entry, 0, 4), number(entry, 8, 8), number(entry, 16, 8), number(entry, 32, 8)
            if kind == 1: loads.append((vaddr, offset, filesz))
            elif kind == 2: dynamic = (offset, filesz)
        if dynamic is None:
            return None
        if dynamic[1] > 1 << 20:
            raise ValueError('ELF dynamic section is unbounded: ' + path)
        stream.seek(dynamic[0]); entries = stream.read(dynamic[1])
        strtab = name = None
        for start in range(0, len(entries) - 15, 16):
            tag, value = int.from_bytes(entries[start:start+8], 'little', signed=True), number(entries, start + 8, 8)
            if tag == 0: break
            if tag == 5: strtab = value
            elif tag == 14: name = value
        if strtab is None or name is None:
            return None
        base = next((offset + strtab - vaddr for vaddr, offset, size in loads if vaddr <= strtab < vaddr + size), None)
        if base is None:
            raise ValueError('ELF string table is outside its loads: ' + path)
        stream.seek(base + name); raw = stream.read(256)
        if b'\0' not in raw:
            raise ValueError('ELF SONAME is unterminated: ' + path)
        return raw.split(b'\0', 1)[0].decode('ascii')


def build(*, v5, observed, vendor, output, host_root='/', dynamic_leaves=EPISODE_DYNAMIC_LEAVES):
    sys.path.insert(0, str(ROOT / 'src'))
    from palimpsest.puck_cpu_registration import _native, egl_vendor_control
    output = Path(output)
    if os.path.lexists(output):
        raise FileExistsError('Native metadata v6 output already exists: ' + str(output))
    v5_raw, observed_raw = _read(v5, 16 * 1024**2), _read(observed, 16 * 1024**2)
    old, census = json.loads(v5_raw), json.loads(observed_raw)
    if old.get('kind') != 'puck-cpu-characterization-native-metadata-v5' or old.get('status') != 'COMPLETE':
        raise ValueError('Accepted native metadata v5 required')
    if census.get('kind') != OBSERVED_KIND or type(census.get('host')) is not list:
        raise ValueError('Observed held episode native maps required')
    pins = {}
    for source, rows in (('metadata05', old['native_files']), ('observed_native_maps', census['host'])):
        for row in rows:
            pin = {key: row[key] for key in ('path', 'size_bytes', 'sha256')}
            if pin['path'] in pins and pins[pin['path']] != pin:
                raise ValueError('Inputs disagree on a native leaf: ' + pin['path'])
            if source == 'observed_native_maps' and not (pin['path'].startswith('/usr/lib/') or pin['path'] == '/etc/ld.so.cache'):
                raise ValueError('Observed native leaf is outside the selectable host paths: ' + pin['path'])
            pins[pin['path']] = pin
    files = []
    for path in sorted(pins):
        current = _hash_leaf(host_root, path)
        if current != pins[path]:
            raise ValueError('Host native leaf differs from its input pin: ' + path)
        files.append(current)
    observed_only = sorted({row['path'] for row in census['host']} - {row['path'] for row in old['native_files']})
    dynamic_leaves = list(dynamic_leaves)
    if dynamic_leaves != sorted(set(dynamic_leaves)) or not set(observed_only) <= set(dynamic_leaves) or not set(dynamic_leaves) <= set(pins):
        raise ValueError('Declared dynamic leaves must cover every observed-only leaf and name only selected leaves')
    aliases = copy.deepcopy(old['aliases']); existing = {alias[0] for alias in aliases}; added = []
    for alias in aliases:
        if alias[0].startswith('/usr/lib/') and os.readlink(_host(host_root, alias[0])) != alias[1]:
            raise ValueError('Host alias no longer matches metadata05: ' + alias[0])
    for row in files:
        path = row['path']
        if not path.startswith('/usr/lib/') or path.count('/') != 3:
            continue
        name = soname(host_root, path)
        if name is None or name == path.rsplit('/', 1)[1] or '/usr/lib/' + name in existing:
            continue
        link = _host(host_root, '/usr/lib/' + name)
        if not os.path.islink(link) or os.readlink(link) != path.rsplit('/', 1)[1]:
            raise ValueError('Host SONAME is not a direct link to its leaf: ' + name)
        aliases.append(['/usr/lib/' + name, path.rsplit('/', 1)[1]]); existing.add('/usr/lib/' + name); added.append(name)
    aliases.sort(key=lambda alias: alias[0])
    vendor_raw = _read(_host(host_root, vendor), 64 * 1024)
    vendor_value = json.loads(vendor_raw)
    library = vendor_value.get('ICD', {}).get('library_path') if type(vendor_value) is dict else None
    helper = Path(__file__).resolve().read_bytes()
    document = dict(kind=KIND, status='COMPLETE', root_scope=SCOPE, errors=[], oversized_native_files=[],
        required_missing_names=[], native_files=files, aliases=aliases, dynamic_leaves=dynamic_leaves,
        egl_vendor=dict(path=vendor, size_bytes=len(vendor_raw), sha256=_digest(vendor_raw), library_path=library),
        limitations=list(LIMITATIONS),
        provenance=dict(kind='puck-native-metadata-v6-derivation-v1',
            inputs=[dict(role='metadata05', path=str(v5), size_bytes=len(v5_raw), sha256=_digest(v5_raw)),
                    dict(role='observed_native_maps', path=str(observed), size_bytes=len(observed_raw), sha256=_digest(observed_raw)),
                    dict(role='egl_vendor', path=vendor, size_bytes=len(vendor_raw), sha256=_digest(vendor_raw))],
            helper=dict(path='scripts/build_puck_native_metadata_v6.py', size_bytes=len(helper), sha256=_digest(helper)),
            host_rehash='every native leaf equals its input pin on the host',
            observed_only_leaves=observed_only, soname_aliases_added=sorted(added)))
    _native(document, float('inf'))
    egl_vendor_control(document, vendor_raw)
    raw = (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode()
    with open(output, 'xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return dict(kind='puck-native-metadata-v6-build-summary-v1', status='VALID', output=str(output),
                output_size_bytes=len(raw), output_sha256=_digest(raw), native_file_count=len(files),
                native_bytes=sum(row['size_bytes'] for row in files), dynamic_leaf_count=len(dynamic_leaves),
                alias_count=len(aliases), soname_aliases_added=sorted(added), observed_only_leaves=observed_only,
                inputs=document['provenance']['inputs'], helper_sha256=_digest(helper))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('v5', 'observed', 'vendor', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    summary = build(v5=args.v5, observed=args.observed, vendor=args.vendor, output=args.output)
    print(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
