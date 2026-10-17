"""AUTHORED stand-in for palimpsest.puck_held_episode: stdlib recordings and bundles only.

Tests copy these bytes over the authored project's ``src/palimpsest/puck_held_episode.py``.
It never renders or simulates. It writes the real recording layout (manifest,
events, ``palimpsest-npz-v1`` chunks, a registered tick-0 snapshot) and the real
``palimpsest-bundle-v1`` ZIP_STORED bundle, so the parents, observers and
independent auditors run over faithful bytes. The harness may rewrite the one
``AUTHORED_DEFECT`` line to select an authored defect; the default is a normal episode.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import types
import zipfile

RESULT_KIND = 'puck-held-public-episode-result-v1'
CLAIMS = dict(runtime_qualified=False, native_authorized=False, collection_authorized=False,
              executable=False, qualification_claims=[])
RENDERER = dict(vendor='Mesa', renderer='llvmpipe (LLVM 22.1.8, 256 bits)',
                version='4.6 (Compatibility Profile) Mesa 26.2.2-arch1.1', egl_vendor='Mesa Project',
                egl_version='1.5', backend='egl')
CHUNK_TICKS = 32
SIDE = 128
AUTHORED_DEFECT = None


def _json(value):
    return json.dumps(value, allow_nan=False, sort_keys=True)


def npy(descr, shape, payload):
    header = "{'descr': '%s', 'fortran_order': False, 'shape': %s, }" % (descr, repr(tuple(shape)))
    header += ' ' * ((64 - (10 + len(header) + 1) % 64) % 64) + '\n'
    return b'\x93NUMPY\x01\x00' + struct.pack('<H', len(header)) + header.encode('latin1') + payload


def npz(arrays):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, (descr, shape, payload) in arrays.items():
            archive.writestr(name + '.npy', npy(descr, shape, payload))
    return stream.getvalue()


_BASE = bytes((i * 7 + i // 384) % 251 for i in range(SIDE * SIDE * 3))


def frame(tick, side, constant=False):
    if constant:
        return bytes([7]) * len(_BASE)
    shift = (tick * 1153 + side * 4099) % len(_BASE)
    return _BASE[shift:] + _BASE[:shift]


def tick_arrays(ticks, actions, latency_offset=0.0, defect=None):
    rows = []
    for tick in ticks:
        heading = [a for t, *a in actions if t <= tick][-1]
        if defect == 'schedule' and tick == 30:
            heading = [1.0, 0.25]
        rows.append(dict(
            cam_left=frame(tick, 0, defect == 'constant-frame' and tick == 3), cam_right=frame(tick, 1),
            raw_cam_left=frame(tick, 2), raw_cam_right=frame(tick, 3),
            sensors=struct.pack('<4d', 0.0, 0.0, 1.0, 0.0), action=struct.pack('<2d', *heading),
            control=struct.pack('<2d', heading[0] * .5, heading[1] * .25),
            pose=struct.pack('<3d', tick * .01, 0.0, 0.0), next_pose=struct.pack('<3d', (tick + 1) * .01, 0.0, 0.0),
            reward=struct.pack('<d', 0.0), simulation_time=struct.pack('<d', (tick + 1) * .02),
            latency=struct.pack('<d', .001 + latency_offset), step_latency=struct.pack('<d', .002 + latency_offset),
            eyes=bytes([1, 1]), revision=struct.pack('<q', 0)))
    return rows


SCHEMA = dict(cam_left=('|u1', [SIDE, SIDE, 3]), cam_right=('|u1', [SIDE, SIDE, 3]),
              raw_cam_left=('|u1', [SIDE, SIDE, 3]), raw_cam_right=('|u1', [SIDE, SIDE, 3]),
              sensors=('<f8', [4]), action=('<f8', [2]), control=('<f8', [2]), pose=('<f8', [3]),
              next_pose=('<f8', [3]), reward=('<f8', []), simulation_time=('<f8', []), latency=('<f8', []),
              step_latency=('<f8', []), eyes=('|b1', [2]), revision=('<i8', []))


def write_recording(run, run_id, rows, *, seed, events_extra=(), diagnostics=None):
    recording = run / 'recording'
    (recording / 'chunks').mkdir(parents=True)
    events = [] if diagnostics is None else [dict(kind='diagnostics', run_id=run_id, report=diagnostics)]
    events.append(dict(kind='episode_started', episode=0, world=dict(goal=[1.0, 0.0, 0.0], obstacles=[]), run_id=run_id))
    events.extend(events_extra)
    for index in range(0, len(rows), CHUNK_TICKS):
        part = rows[index:index + CHUNK_TICKS]
        arrays = {name: (descr, [len(part), *shape], b''.join(row[name] for row in part))
                  for name, (descr, shape) in SCHEMA.items()}
        payload = npz(arrays)
        relative = 'chunks/%06d.npz' % (index // CHUNK_TICKS)
        (recording / relative).write_bytes(payload)
        events.append(dict(kind='chunk', path=relative, sha256=hashlib.sha256(payload).hexdigest(), episode=0,
                           start=index, count=len(part),
                           arrays={name: dict(dtype=descr, shape=shape) for name, (descr, shape) in SCHEMA.items()}))
    with (recording / 'events.jsonl').open('x') as stream:
        for sequence, event in enumerate(events):
            stream.write(_json(dict(event, sequence=sequence)) + '\n')
    manifest = dict(schema_version=1, run_id=run_id, profile='manual', controller='manual', seed=seed,
                    status='completed', recording_format='palimpsest-npz-v1', recording_max_bytes=None,
                    recorded_ticks=len(rows), recorded_chunks=(len(rows) + CHUNK_TICKS - 1) // CHUNK_TICKS,
                    recorded_events=len(events))
    (recording / 'manifest.json').write_text(_json(manifest) + '\n')
    return len(events)


def register_snapshot(run, run_id):
    directory = run / 'snapshots'
    directory.mkdir()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('metadata.json', _json(dict(run_id=run_id, tick=0, authored=True)))
    raw = stream.getvalue(); digest = hashlib.sha256(raw).hexdigest(); identifier = digest[:32]
    (directory / 'initial.snp').write_bytes(raw)
    record = dict(filename='initial.snp', snapshot_id=identifier, sha256=digest, initial=True)
    (directory / 'index.json').write_text(_json(dict(version=1, snapshots={identifier: record})) + '\n')
    return identifier, dict(kind='snapshot_registered', snapshot_id=identifier, initial=True, sha256=digest,
                            filename='initial.snp', run_id=run_id)


def bundle(run, target, defect=None):
    members = []
    for path in sorted((run / 'recording').rglob('*')):
        if path.is_file():
            members.append(('recording/' + path.relative_to(run / 'recording').as_posix(), path))
    members.append(('snapshots/initial.snp', run / 'snapshots' / 'initial.snp'))
    if (run / 'replay-report.json').exists():
        members.append(('replay-report.json', run / 'replay-report.json'))
    files = []
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_STORED) as archive:
        for relative, path in members:
            raw = path.read_bytes()
            archive.writestr(relative, raw)
            files.append(dict(path=relative, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        if defect == 'unlisted-member':
            archive.writestr('recording/extra.txt', b'unlisted')
        archive.writestr('bundle-manifest.json', json.dumps(dict(format='palimpsest-bundle-v1', files=files,
                                                                 derived=dict(authored=True)), allow_nan=False))
    raw = target.read_bytes()
    return dict(path=target.name, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def versions(expected, modules=None):
    modules = sys.modules if modules is None else modules
    result = {}
    for name, version in sorted(expected.items()):
        value = types.ModuleType.__dict__['__dict__'].__get__(modules[name]).get('__version__')
        if value != version:
            raise ValueError('Held episode version differs: ' + name)
        result[name] = value
    return result


def provenance(admission):
    """The real held provenance record, built as palimpsest.puck_held_episode.provenance builds it."""
    import tomllib
    from pathlib import PurePosixPath
    from palimpsest.held_provenance import held_provenance
    reg = admission._reg; episode = reg['episode']
    rows = {row['path']: row for row in reg['source_files']}
    raw = admission._source.read('pyproject.toml', 1024 ** 2)
    version = tomllib.loads(raw.decode('utf-8'))['project']['version']
    runtime = reg['runtime']; pin = runtime['files'][0]
    interpreter = dict(path=str(PurePosixPath(runtime['root']) / pin['path']), size_bytes=pin['size_bytes'],
                       sha256=pin['sha256'], python_version=runtime['python_version'])
    upstream = dict(path=str(PurePosixPath(reg['source_root']) / 'upstream/fly-gym'), commit=episode['upstream_commit'],
                    files=[dict(row, path=row['path'][len('upstream/fly-gym/'):]) for row in reg['source_files']
                           if row['path'].startswith('upstream/fly-gym/')])
    return held_provenance(interpreter=interpreter, upstream=upstream,
        distributions=copy.deepcopy(admission._dependencies.distributions), palimpsest_version=version,
        lock_sha256=rows['uv.lock']['sha256'], environment=dict(reg['environment']))


def run(admission):
    import numpy, torch, torch.utils, mujoco, gymnasium, scipy.linalg  # noqa: F401  (observed packages and roster parents)
    admission.recheck()
    episode = copy.deepcopy(admission._reg['episode'])
    defect = AUTHORED_DEFECT
    if defect == 'spawn':
        import subprocess
        try:
            subprocess.run(['/bin/true'])
        except RuntimeError:
            pass
    held = type(admission).__name__ != '_Admission'
    if defect == 'undeclared-import' or (defect == 'held-undeclared-import' and held):
        # Caught as a plain miss when unguarded; the held bootstrap refuses undeclared names.
        try:
            import authored_undeclared_optional  # noqa: F401
        except ImportError:
            pass
    record = provenance(admission)
    report = record.report(); digest = record.sha256
    if defect == 'diagnostics':
        report['ready'] = not report['ready']
    if defect == 'provenance-sha':
        digest = hashlib.sha256(b'AUTHORED other provenance').hexdigest()
    output = Path(episode['paths']['output_root']); schedule = episode['schedule']
    ids = episode['run_ids']; ticks = list(range(schedule['ticks']))
    observed = versions(episode['expected_versions'])
    if episode['phase'] == 'source':
        run = output / ids['source']; run.mkdir(mode=0o700)
        identifier, registered = register_snapshot(run, ids['source'])
        completed = ticks[:-1] if defect == 'short' else ticks
        rows = tick_arrays(completed, schedule['actions'], defect=defect)
        write_recording(run, ids['source'], rows, seed=episode['profile']['seed'], events_extra=[registered], diagnostics=report)
        admission.recheck()
        receipt = bundle(run, output / 'source-bundle.zip', defect)
        return dict(kind=RESULT_KIND, version=1, phase='source', run_id=ids['source'], source_run_id=ids['source'],
                    ticks_requested=schedule['ticks'], ticks_completed=len(completed), final_phase='paused',
                    initial_snapshot_id=identifier, provenance_sha256=digest, versions=observed,
                    renderer=dict(RENDERER), bundle=receipt, **copy.deepcopy(CLAIMS))
    source = Path(episode['paths']['source_root']) / ids['source']
    if not (source / 'recording' / 'manifest.json').is_file():
        raise RuntimeError('Authored replay requires the read-only source run')
    run = output / ids['replay']; run.mkdir(mode=0o700)
    identifier, registered = register_snapshot(run, ids['replay'])
    rows = tick_arrays(ticks, schedule['actions'], latency_offset=.0005, defect=defect)
    if defect == 'diverge':
        rows[5]['pose'] = struct.pack('<3d', 9.0, 0.0, 0.0)
    events = write_recording(run, ids['replay'], rows, seed=episode['profile']['seed'], events_extra=[registered],
                             diagnostics=report)
    report = dict(schema_version=1, source_run_id=ids['source'], run_id=ids['replay'], mode='actions', status='passed',
                  compared_ticks=len(ticks), compared_events=events, first_divergence=None,
                  comparison=dict(float_atol=1e-6, float_rtol=1e-6, integer_and_camera_exact=True), errors=[])
    (run / 'replay-report.json').write_text(_json(report) + '\n')
    admission.recheck()
    receipt = bundle(run, output / 'replay-bundle.zip', defect)
    return dict(kind=RESULT_KIND, version=1, phase='replay', run_id=ids['replay'], source_run_id=ids['source'],
                ticks_requested=schedule['ticks'], provenance_sha256=digest, versions=observed,
                replay={key: report[key] for key in ('status', 'compared_ticks', 'compared_events', 'first_divergence')},
                bundle=receipt, **copy.deepcopy(CLAIMS))
