#!/usr/bin/env python3
"""Bounded ordinary-import observation, never held-runtime qualification.

The outer supervisor supplies time/process/RSS/output limits. This worker trusts
CPython and imported packages; it is not an import sandbox or native-load proof.
No model, scene, inference, physics or training entry point is called here.
"""
import hashlib
import importlib
from importlib.machinery import ModuleSpec
import json
import os
from pathlib import Path
import stat
import sys
import time
import types

REQUEST_BYTES = 64 * 1024
REPORT_BYTES = 1024 ** 2
CACHE_ENTRIES = 8192
ATTRIBUTE_EDGES = 262144
MAP_BYTES = 4 * 1024 ** 2
MAP_LINES = 65536
PACKAGES = ('numpy', 'torch', 'mujoco')


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def text_value(value, maximum=4096):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > maximum or '\0' in value:
        raise ValueError('Unexpected or oversized metadata text')
    # Bypass a framework str subclass's conversion hook (e.g. TorchVersion).
    return str.__str__(value)


def module_dict(value):
    # Do not use getattr/hasattr: torch.ops/classes create objects on lookup.
    return types.ModuleType.__dict__['__dict__'].__get__(value)


def class_name(value):
    kind = type(value)
    return (text_value(type.__getattribute__(kind, '__module__'), 512) + '.'
            + text_value(type.__getattribute__(kind, '__qualname__'), 512))


def describe_cache(cache):
    if type(cache) is not dict or len(cache) > CACHE_ENTRIES:
        raise ValueError('Module cache exceeds bounded dictionary contract')
    entries = list(cache.items())
    identities = {}
    for name, value in entries:
        text_value(name, 512)
        if type(name) is not str:
            raise ValueError('Module cache key is not an exact string')
        if isinstance(value, types.ModuleType):
            identities.setdefault(id(value), []).append(name)
    exceptional = set()
    for name, value in entries:
        if not isinstance(value, types.ModuleType):
            continue
        attributes = module_dict(value)
        spec = attributes.get('__spec__')
        spec_name = (text_value(object.__getattribute__(spec, '__dict__').get('name'), 512)
                     if type(spec) is ModuleSpec else None)
        if (len(identities[id(value)]) > 1 or type(value) is not types.ModuleType
                or type(spec) is not ModuleSpec or attributes.get('__file__') is None
                or spec_name != name):
            exceptional.add(id(value))
    exports = {}
    inspected = set()
    edges = 0
    for name, producer in entries:
        if not isinstance(producer, types.ModuleType) or id(producer) in inspected:
            continue
        inspected.add(id(producer))
        attributes = module_dict(producer)
        edges += len(attributes)
        if edges > ATTRIBUTE_EDGES:
            raise ValueError('Module attribute edge budget exceeded')
        for attribute, value in list(attributes.items()):
            if isinstance(value, types.ModuleType) and id(value) in exceptional:
                if type(attribute) is not str:
                    raise ValueError('Module export attribute is not an exact string')
                text_value(attribute, 512)
                exports.setdefault(id(value), []).append(
                    {'producer': name, 'attribute': attribute})
    rows = []
    for name, value in sorted(entries):
        if not isinstance(value, types.ModuleType):
            rows.append({'name': name, 'classification': 'nonmodule',
                         'type': class_name(value)})
            continue
        attributes = module_dict(value)
        spec = attributes.get('__spec__')
        spec_dict = object.__getattribute__(spec, '__dict__') if type(spec) is ModuleSpec else {}
        spec_name = text_value(spec_dict.get('name'), 512)
        origin = text_value(spec_dict.get('origin'))
        file = text_value(attributes.get('__file__'))
        classification = ('alias' if spec_name is not None and spec_name != name
                          else 'virtual' if file is None and spec_name is None
                          else 'module')
        row = {'name': name, 'spec_name': spec_name, 'file': file,
               'classification': classification,
               'exports': sorted(exports.get(id(value), []),
                                 key=lambda item: (item['producer'], item['attribute']))}
        if origin != file:
            row['spec_origin'] = origin
        if type(value) is not types.ModuleType:
            row['type'] = class_name(value)
        if spec is not None and type(spec) is not ModuleSpec:
            row['spec_type'] = class_name(spec)
        if len(identities[id(value)]) > 1:
            row['same_object_cache_names'] = sorted(identities[id(value)])
        rows.append(row)
    return {'modules': rows, 'attribute_edges': edges,
            'module_objects': len(identities), 'cache_entries': len(entries),
            'export_scope': 'exceptional_cache_identities'}


def describe_maps(raw):
    if len(raw) > MAP_BYTES:
        raise ValueError('Mapped-image observation exceeds byte budget')
    lines = raw.splitlines()
    if len(lines) > MAP_LINES:
        raise ValueError('Mapped-image observation exceeds line budget')
    images = {}
    for line in lines:
        parts = line.decode('utf-8', errors='strict').split(None, 5)
        if len(parts) < 5:
            raise ValueError('Malformed mapped-image observation')
        if len(parts) == 6 and parts[5].startswith('/') and int(parts[4]) != 0:
            key = (parts[3], int(parts[4]), parts[5])
            row = images.setdefault(key, {'device': parts[3], 'inode': int(parts[4]),
                                          'path': text_value(parts[5]), 'segments': 0,
                                          'executable': False})
            row['segments'] += 1
            row['executable'] |= 'x' in parts[1]
    return {'images': [images[key] for key in sorted(images)],
            'map_bytes': len(raw), 'map_lines': len(lines),
            'persistent_snapshot_only': True,
            'transient_anonymous_jit_closure_qualified': False}


def mapped_images():
    with open('/proc/self/maps', 'rb') as handle:
        return describe_maps(handle.read(MAP_BYTES + 1))


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def read_bounded(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 < before.st_size <= maximum):
            raise ValueError('Input is not a bounded single-link regular file')
        raw = bytearray()
        while len(raw) <= maximum:
            block = os.read(fd, min(65536, maximum + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        if (len(raw) != before.st_size or len(raw) > maximum
                or identity(os.fstat(fd)) != identity(before)
                or identity(os.stat(path, follow_symlinks=False)) != identity(before)):
            raise ValueError('Input changed during bounded read')
        return bytes(raw)
    finally:
        os.close(fd)


def exact_directory(value):
    if type(value) is not str or len(value) > 4096:
        raise ValueError('Directory must be canonical absolute text')
    path = Path(value)
    if not path.is_absolute() or str(path) != value or path.resolve(strict=True) != path or not path.is_dir():
        raise ValueError('Directory must be canonical, present and nonsymlinked')
    return path


def request_at(path, expected_sha):
    if (type(expected_sha) is not str or len(expected_sha) != 64
            or any(c not in '0123456789abcdef' for c in expected_sha)):
        raise ValueError('Request SHA must be lowercase hexadecimal')
    raw = read_bounded(path, REQUEST_BYTES)
    if sha(raw) != expected_sha:
        raise ValueError('Request SHA mismatch')
    value = json.loads(raw)
    fields = {'kind', 'version', 'site_root', 'output_root', 'environment'}
    if (type(value) is not dict or set(value) != fields or canonical(value) != raw
            or value['kind'] != 'puck-runtime-import-characterization-v1'
            or type(value['version']) is not int or value['version'] != 1):
        raise ValueError('Request schema/canonical bytes mismatch')
    site = exact_directory(value['site_root'])
    output = exact_directory(value['output_root'])
    if site == output or site in output.parents or output in site.parents:
        raise ValueError('Output overlaps numerical site root')
    if (output / 'imports.json').exists() or (output / 'imports.json').is_symlink():
        raise ValueError('Output already contains a report')
    environment = value['environment']
    if (type(environment) is not dict or len(environment) > 128
            or any(type(k) is not str or type(v) is not str or not k or '=' in k
                   or '\0' in k + v or len(k) > 256 or len(v) > 4096
                   for k, v in environment.items())
            or dict(os.environ) != environment):
        raise ValueError('Exact environment mismatch')
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError('Worker must use -I -B -S')
    return value


def publish(output, report):
    raw = canonical(report)
    if len(raw) > REPORT_BYTES:
        raise ValueError('Characterization report exceeds one MiB')
    root = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open('imports.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=root)
        try:
            remaining = memoryview(raw)
            while remaining:
                count = os.write(fd, remaining)
                if count < 1:
                    raise OSError('Report write made no progress')
                remaining = remaining[count:]
            os.fsync(fd)
            os.fsync(root)
        finally:
            os.close(fd)
    finally:
        os.close(root)
    return {'report_sha256': sha(raw), 'report_bytes': len(raw), 'status': report['status']}


def environment_delta(before, after):
    """Bounded changed-name diagnostics; unknown values never appear as plaintext."""
    result = {'complete': False, 'before_count': len(before), 'after_count': len(after),
              'added': [], 'removed': [], 'changed': [],
              'value_encoding': sys.getfilesystemencoding() + '/' + sys.getfilesystemencodeerrors()}
    if len(before) > 256 or len(after) > 256:
        return dict(result, reason='namespace_limit')
    names = set(before) | set(after)
    if len(names) > 256:
        return dict(result, reason='namespace_limit')
    if any(type(name) is not str or len(name) > 256 for name in names):
        return dict(result, reason='key_limit')
    changed = [name for name in sorted(names)
               if name not in before or name not in after or before[name] != after[name]]
    if len(changed) > 128:
        return dict(result, reason='change_limit')
    rows = {'added': [], 'removed': [], 'changed': []}
    for name in changed:
        row = {'name': name}
        for prefix, values in (('before', before), ('after', after)):
            if name not in values:
                continue
            value = values[name]
            if type(value) is not str or len(value) > 4096:
                return dict(result, reason='value_limit')
            raw = os.fsencode(value)
            if len(raw) > 4096:
                return dict(result, reason='value_limit')
            row[prefix + '_bytes'] = len(raw)
            row[prefix + '_sha256'] = sha(raw)
        section = 'added' if name not in before else 'removed' if name not in after else 'changed'
        rows[section].append(row)
    return dict(result, complete=True, **rows)


def failure_detail(error):
    return {'type': class_name(error), 'message': str(error)[:2048]}


def observe(request, request_sha):
    report = {'kind': 'puck-runtime-import-characterization-result-v2', 'version': 2,
              'status': 'failed', 'request_sha256': request_sha,
              'source_sha256': sha(read_bounded(__file__, REPORT_BYTES)),
              'environment_sha256': sha(canonical(request['environment'])),
              'python_version': sys.version, 'executable_path': sys.executable,
              'pid': os.getpid(), 'ppid': os.getppid(),
              'runtime_qualified': False, 'collection_authorized': False,
              'executable': False, 'qualification_claims': [],
              'versions': {}, 'imports': [], 'cache': None, 'maps': None,
              'baseline_maps': None, 'environment_delta': None, 'observation_errors': []}
    started = time.monotonic()
    error = None
    imports_complete = False
    try:
        # Ordinary imports deliberately remain separate from the held finder.
        # -I -S removes ambient site initialization; one explicit site is appended.
        sys.path.append(request['site_root'])
        report['baseline_maps'] = mapped_images()
        for name in PACKAGES:
            before = time.monotonic()
            row = {'name': name, 'status': 'failed'}
            report['imports'].append(row)
            value = importlib.import_module(name)
            if dict(os.environ) != request['environment']:
                raise ValueError('Exact environment changed during ' + name + ' import')
            report['versions'][name] = text_value(module_dict(value).get('__version__'), 512)
            if report['versions'][name] is None:
                raise ValueError('Missing raw package version: ' + name)
            row.update(status='observed', seconds=time.monotonic() - before,
                       cache_entries=len(sys.modules))
        imports_complete = True
    except BaseException as failure:
        # A package SystemExit(0) must not become an empty successful observation.
        error = failure_detail(failure)
    report['observation_scope'] = 'completed_imports' if imports_complete else 'post_failure'
    actual_environment = dict(os.environ)
    if actual_environment != request['environment']:
        if error is None:
            error = failure_detail(ValueError('Exact environment changed during observation'))
        try:
            report['environment_delta'] = environment_delta(request['environment'], actual_environment)
        except Exception as failure:
            report['observation_errors'].append(dict(failure_detail(failure), stage='environment_delta'))
    # These are independent bounded observations, even after failed import admission.
    # A broken cache inspection must not erase the primary cause or a usable map snapshot.
    for stage, snapshot in (('cache', lambda: describe_cache(sys.modules)), ('maps', mapped_images)):
        try:
            report[stage] = snapshot()
        except BaseException as failure:
            report['observation_errors'].append(dict(failure_detail(failure), stage=stage))
    terminal_environment = dict(os.environ)
    if terminal_environment != request['environment']:
        if error is None:
            error = failure_detail(ValueError('Exact environment changed during observation'))
        if report['environment_delta'] is None or terminal_environment != actual_environment:
            try:
                delta = environment_delta(request['environment'], terminal_environment)
                key = ('environment_delta' if report['environment_delta'] is None
                       else 'terminal_environment_delta')
                report[key] = delta
            except Exception as failure:
                report['observation_errors'].append(dict(failure_detail(failure), stage='terminal_environment_delta'))
    report['seconds'] = time.monotonic() - started
    if error is not None:
        report['error'] = error
    elif report['observation_errors']:
        report['error'] = dict(report['observation_errors'][0])
    else:
        report['status'] = 'observed'
    # A too-large observation is retained failure. Keep the original cause and
    # bounded environment delta; never truncate oversized cache data into success.
    observed_bytes = len(canonical(report))
    if observed_bytes > REPORT_BYTES:
        report['status'] = 'failed'
        report['baseline_maps'] = report['cache'] = report['maps'] = None
        limit = {'stage': 'report', 'type': 'report_limit',
                 'message': 'Full observation exceeded one MiB', 'observed_bytes': observed_bytes}
        report['observation_errors'].append(limit)
        report.setdefault('error', dict(limit))
    return report


def main(argv):
    try:
        if len(argv) != 2:
            raise ValueError('Expected request path and external SHA')
        request = request_at(argv[0], argv[1])
        report = observe(request, argv[1])
        receipt = publish(request['output_root'], report)
        print(canonical(receipt).decode(), end='', flush=True)
        return 0 if report['status'] == 'observed' else 1
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error)[:2048], file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
