"""Held public manual episode entry; the v4 bootstrap dispatches only ``run``.

Phase ``source`` records one bounded manual CPU episode with a registered
tick-0 snapshot and exports its bundle. Phase ``replay`` replays that source
by actions in a fresh owner and exports the replay bundle. Both use held
provenance built from the authenticated registration, never the ambient doctor.
The receipt claims nothing: independent outcome audits decide acceptance.
"""
import copy
import hashlib
import os
from pathlib import Path, PurePosixPath
import sys
import types

MiB = 1024**2
RECHECK_TICKS = 16
RESULT_KIND = 'puck-held-public-episode-result-v1'
CLAIMS = dict(runtime_qualified=False, native_authorized=False, collection_authorized=False,
              executable=False, qualification_claims=[])
UPSTREAM = 'upstream/fly-gym/'
GL_LIBRARIES = ('libOpenGL.so.0', 'libGL.so.1')
EGL_LIBRARY = 'libEGL.so.1'


def provenance(admission):
    """HeldProvenance from registration pins, held source bytes and held distributions."""
    import tomllib
    from .held_provenance import held_provenance
    reg = admission._reg; episode = reg['episode']
    rows = {row['path']: row for row in reg['source_files']}
    for name in ('pyproject.toml', 'uv.lock'):
        if name not in rows:
            raise ValueError('Held episode provenance requires a registered ' + name)
    raw = admission._source.read('pyproject.toml', MiB)
    if hashlib.sha256(raw).hexdigest() != rows['pyproject.toml']['sha256']:
        raise ValueError('Held episode pyproject bytes differ from their registration')
    version = tomllib.loads(raw.decode('utf-8'))['project']['version']
    runtime = reg['runtime']; pin = runtime['files'][0]
    interpreter = dict(path=str(PurePosixPath(runtime['root'])/pin['path']), size_bytes=pin['size_bytes'],
                       sha256=pin['sha256'], python_version=runtime['python_version'])
    upstream = dict(path=str(PurePosixPath(reg['source_root'])/UPSTREAM.rstrip('/')), commit=episode['upstream_commit'],
                    files=[dict(row, path=row['path'][len(UPSTREAM):]) for row in reg['source_files']
                           if row['path'].startswith(UPSTREAM)])
    return held_provenance(interpreter=interpreter, upstream=upstream,
        distributions=copy.deepcopy(admission._dependencies.distributions), palimpsest_version=version,
        lock_sha256=rows['uv.lock']['sha256'], environment=dict(reg['environment']))


def versions(expected, modules=None):
    """Exact ``__version__`` of already-imported modules, read without import hooks."""
    modules = sys.modules if modules is None else modules
    observed = {}
    for name, version in sorted(expected.items()):
        module = modules.get(name)
        if module is None:
            raise ValueError('Held episode module was not imported: ' + name)
        value = types.ModuleType.__dict__['__dict__'].__get__(module).get('__version__')
        if not isinstance(value, str) or len(value) > 128 or str.__str__(value) != version:
            raise ValueError('Held episode version differs: ' + name)
        observed[name] = str.__str__(value)
    return observed


def renderer_identity(engine):
    """GL/EGL strings on the renderer's own current context; maps no new library."""
    import ctypes
    context = engine.env.renderer._gl_context
    context.make_current()
    def loaded(names):
        for name in names:
            try:
                return ctypes.CDLL(name, mode=os.RTLD_NOLOAD | os.RTLD_LOCAL)
            except OSError:
                continue
        raise RuntimeError('Held renderer library is not already loaded: ' + names[0])
    gl, egl = loaded(GL_LIBRARIES), loaded((EGL_LIBRARY,))
    get = gl.glGetString; get.restype = ctypes.c_char_p; get.argtypes = [ctypes.c_uint]
    current = egl.eglGetCurrentDisplay; current.restype = ctypes.c_void_p; current.argtypes = []
    query = egl.eglQueryString; query.restype = ctypes.c_char_p; query.argtypes = [ctypes.c_void_p, ctypes.c_int]
    display = current()
    if not display:
        raise RuntimeError('Held renderer has no current EGL display')
    values = dict(vendor=get(0x1F00), renderer=get(0x1F01), version=get(0x1F02),
                  egl_vendor=query(display, 0x3053), egl_version=query(display, 0x3054))
    if any(type(value) is not bytes or not value for value in values.values()):
        raise RuntimeError('Held renderer string query returned no result')
    result = {key: value.decode('ascii', 'replace')[:256] for key, value in values.items()}
    result['backend'] = type(context).__module__.rsplit('.', 1)[-1]
    return result


def _bundle(export_run, run, target):
    export_run(run, target, 'bundle')
    with open(target, 'rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=target.name, size_bytes=target.stat().st_size, sha256=digest)


def _source(admission, episode, record):
    from . import replay
    from .artifacts import export_run
    from .engine import Engine
    output = Path(episode['paths']['output_root']); run = output/episode['run_ids']['source']
    profile = episode['profile']; schedule = episode['schedule']
    run.mkdir(mode=0o700)
    engine = Engine.open(Path(admission._reg['source_root']), Path(episode['paths']['asset_root']), run/'recording',
        controller=profile['controller'], device=profile['device'], seed=profile['seed'],
        scenario=profile['scenario'], texture=profile['texture'], run_id=episode['run_ids']['source'],
        diagnostics=record)
    try:
        admission.recheck()
        observed = versions(episode['expected_versions'])
        renderer = renderer_identity(engine)
        snapshot = replay._register_initial(engine, run)
        admission.recheck()
        actions = {tick: [velocity, heading] for tick, velocity, heading in schedule['actions']}
        counter = 0; completed = 0
        def command(kind, payload=None):
            nonlocal counter
            counter += 1
            engine.submit({'id': 'held-%04d' % counter, 'kind': kind, 'expected_state': engine.phase,
                           'expected_episode': engine.episode, **({} if payload is None else {'payload': payload})})
        for tick in range(schedule['ticks']):
            if engine.phase not in ('paused', 'running'):
                break
            if tick in actions:
                command('set_action', {'action': actions[tick]})
            command('step')
            engine.advance()
            if engine.total_tick != tick+1:
                break
            completed = tick+1
            if completed % RECHECK_TICKS == 0:
                admission.recheck()
        final = engine.public_state()['phase']
    except BaseException as error:
        try:
            engine.close()
        except BaseException as close_error:
            error.add_note('Held episode close after failure: ' + str(close_error))
        raise
    engine.close()
    admission.recheck()
    bundle = _bundle(export_run, run, output/'source-bundle.zip')
    admission.recheck()
    return dict(kind=RESULT_KIND, version=1, phase='source', run_id=episode['run_ids']['source'],
        source_run_id=episode['run_ids']['source'], ticks_requested=schedule['ticks'], ticks_completed=completed,
        final_phase=final, initial_snapshot_id=snapshot, provenance_sha256=record.sha256, versions=observed,
        renderer=renderer, bundle=bundle, **copy.deepcopy(CLAIMS))


def _replay(admission, episode, record):
    from .artifacts import export_run
    from .replay import replay_run
    output = Path(episode['paths']['output_root']); destination = output/episode['run_ids']['replay']
    destination.mkdir(mode=0o700)
    checked = [0]
    def progress(stage, state=None):
        if stage == 'ready':
            admission.recheck()
        elif stage == 'step' and state is not None and state['total_tick'] >= checked[0]+RECHECK_TICKS:
            checked[0] = state['total_tick'] - state['total_tick'] % RECHECK_TICKS
            admission.recheck()
    report = replay_run(Path(episode['paths']['source_root'])/episode['run_ids']['source'], destination,
        mode='actions', repo_root=Path(admission._reg['source_root']), asset_root=Path(episode['paths']['asset_root']),
        progress=progress, diagnostics=record)
    admission.recheck()
    if report.get('status') != 'passed':
        raise RuntimeError('Held replay did not pass: ' + str(report.get('status')))
    observed = versions(episode['expected_versions'])
    bundle = _bundle(export_run, destination, output/'replay-bundle.zip')
    admission.recheck()
    return dict(kind=RESULT_KIND, version=1, phase='replay', run_id=episode['run_ids']['replay'],
        source_run_id=episode['run_ids']['source'], ticks_requested=episode['schedule']['ticks'],
        provenance_sha256=record.sha256, versions=observed,
        replay={key: copy.deepcopy(report.get(key)) for key in ('status', 'compared_ticks', 'compared_events', 'first_divergence')},
        bundle=bundle, **copy.deepcopy(CLAIMS))


def run(admission):
    admission.recheck()
    episode = copy.deepcopy(admission._reg['episode'])
    if episode.get('phase') not in ('source', 'replay'):
        raise ValueError('Held episode phase must be source or replay')
    record = provenance(admission)
    admission.recheck()
    return (_source if episode['phase'] == 'source' else _replay)(admission, episode, record)
