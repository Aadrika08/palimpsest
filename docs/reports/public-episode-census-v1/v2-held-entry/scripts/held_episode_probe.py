"""Diagnostic only: drive the real palimpsest.puck_held_episode.run() for one phase
(source or replay) in this fresh process, with a stand-in admission (no guard),
held provenance built from supplied pins, and an audit hook that records and
REFUSES every process creation exactly like the v4 bootstrap hook.

Passive recorders: head/tail meta-path finders, ctypes.dlopen log, /proc/self/maps
snapshots. Engine/replay/export helpers are wrapped only to time them.
Not admission, qualification or runtime evidence.
"""
import importlib, json, os, resource, sys, time

SITE, ROOT, INPUTS, OUT, PHASE, SOURCE_ID, REPLAY_ID, SOURCE_ROOT, TICKS = sys.argv[1:10]
TICKS = int(TICKS)
SRC = ROOT + '/src'
sys.path[:] = [SITE, SRC] + [p for p in sys.path if 'site-packages' not in p]
STDLIB = os.path.dirname(os.__file__)
PREFIX = os.path.dirname(os.path.dirname(STDLIB))
UP = ROOT + '/upstream/fly-gym'
T0, C0, ENV0 = time.monotonic(), time.process_time(), dict(os.environ)
phase = 'start'
requests, misses, refusals, dlopens, rechecks, per_tick = {}, {}, [], [], [], []
PROCESS_EVENTS = frozenset({'subprocess.Popen', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'os.system',
                            'pty.spawn', 'os.spawn'})


def _stack(skip=2, limit=10):
    frames, f = [], sys._getframe(skip)
    while f is not None and len(frames) < limit:
        name = f.f_code.co_filename
        if 'importlib._bootstrap' not in name:
            for prefix, tag in ((SITE + '/', ''), (SRC + '/', 'src:'), (UP + '/', 'upstream:'), (STDLIB + '/', 'stdlib:')):
                if name.startswith(prefix):
                    name = tag + name[len(prefix):]; break
            frames.append(f'{name}:{f.f_lineno}:{f.f_code.co_name}')
        f = f.f_back
    return frames


def _refuse(event, args):
    if event in PROCESS_EVENTS or event.startswith('os.exec'):
        try:
            shown = [a if isinstance(a, (str, int, float, type(None))) else
                     (list(map(str, a))[:12] if isinstance(a, (list, tuple)) else type(a).__name__) for a in args]
            refusals.append(dict(event=event, phase=phase, t=round(time.monotonic() - T0, 3),
                                 args=[str(x)[:300] for x in shown], stack=_stack()))
        except Exception:
            pass
        raise RuntimeError('Held episode refuses process creation: ' + event)
    if event == 'ctypes.dlopen':
        try:
            dlopens.append(dict(name=str(args[0]), phase=phase))
        except Exception:
            pass


sys.addaudithook(_refuse)


class Head:
    def find_spec(self, fullname, path=None, target=None):
        r = requests.get(fullname)
        if r is None: requests[fullname] = dict(phase=phase, n=1, stack=_stack(limit=4))
        else: r['n'] += 1
        return None
    def invalidate_caches(self): pass


class Tail:
    def find_spec(self, fullname, path=None, target=None):
        if fullname not in misses:
            misses[fullname] = dict(phase=phase, stack=_stack(limit=4),
                                    stdlib=fullname.split('.')[0] in sys.stdlib_module_names)
        return None
    def invalidate_caches(self): pass


sys.meta_path.insert(0, Head())
sys.meta_path.append(Tail())


def vm():
    out = {}
    with open('/proc/self/status') as stream:
        for line in stream:
            if line.startswith(('VmPeak:', 'VmSize:', 'VmHWM:', 'VmRSS:', 'Threads:')):
                out[line.split(':')[0]] = int(line.split()[1]) if line.startswith('Threads') else round(int(line.split()[1]) / 1024, 1)
    return out


def maps():
    files = set()
    with open('/proc/self/maps') as stream:
        for line in stream:
            parts = line.split()
            if len(parts) >= 6 and parts[5].startswith('/'):
                files.add(parts[5])
    return files


def origin(name):
    m = sys.modules.get(name)
    f = getattr(m, '__file__', None)
    if f is None:
        spec = getattr(m, '__spec__', None)
        o = getattr(spec, 'origin', None)
        return o if o in ('built-in', 'frozen') else 'nofile'
    for prefix, tag in ((SITE + '/', 'site'), (SRC + '/', 'src'), (UP + '/', 'upstream'), (STDLIB + '/', 'stdlib')):
        if str(f).startswith(prefix): return tag
    return 'other'


segments, loaded, map_points = [], {}, {}
seg = dict(name='start', t=T0, c=C0, mods=set(sys.modules))


def switch(name):
    global seg, phase
    now, cpu = time.monotonic(), time.process_time()
    new = sorted(set(sys.modules) - seg['mods'])
    counts = {}
    for n in new:
        k = origin(n); counts[k] = counts.get(k, 0) + 1
    if new: loaded.setdefault(seg['name'], []).extend(new)
    segments.append(dict(name=seg['name'], seconds=round(now - seg['t'], 4), cpu_seconds=round(cpu - seg['c'], 4),
                         new_modules=len(new), origins=counts, end_elapsed=round(now - T0, 4), **vm()))
    seg = dict(name=name, t=now, c=cpu, mods=set(sys.modules))
    phase = name


def wrap(owner, attribute, label, after=None, kind='function'):
    original = getattr(owner, attribute)
    def wrapper(*a, **k):
        switch(label)
        try:
            return original(*a, **k)
        finally:
            if after: after()
            switch('after.' + label)
    setattr(owner, attribute, classmethod(lambda cls, *a, **k: wrapper(*a, **k)) if kind == 'classmethod' else wrapper)


inputs = json.load(open(INPUTS))
result, error = None, None
switch(PHASE + '.import.palimpsest')
try:
    import palimpsest.puck_held_episode as held
    import palimpsest.held_provenance  # noqa: F401
    from palimpsest import replay, artifacts
    from palimpsest.engine import Engine
    switch(PHASE + '.setup')
    wrap(held, 'provenance', 'provenance')
    wrap(Engine, 'open', 'Engine.open', after=lambda: map_points.setdefault('after_open', maps()), kind='classmethod')
    wrap(held, 'versions', 'versions')
    wrap(held, 'renderer_identity', 'renderer_identity', after=lambda: map_points.setdefault('after_renderer_identity', maps()))
    wrap(replay, '_register_initial', 'register_initial')
    wrap(replay, 'replay_run', 'replay_run')
    wrap(artifacts, 'export_run', 'export_run')
    original_close, original_advance = Engine.close, Engine.advance
    def close(self):
        map_points.setdefault('before_close', maps())
        switch('Engine.close')
        try:
            return original_close(self)
        finally:
            switch('after.Engine.close')
    def advance(self, *a, **k):
        t = time.monotonic()
        try:
            return original_advance(self, *a, **k)
        finally:
            per_tick.append(round(time.monotonic() - t, 4))
    Engine.close, Engine.advance = close, advance

    class Source:
        def read(self, path, limit):
            data = open(os.path.join(ROOT, path), 'rb').read()
            if len(data) > limit: raise ValueError('limit')
            return data

    class Dependencies:
        distributions = inputs['distributions']

    episode = dict(phase=PHASE, upstream_commit='8d964599119b420de67ee259434d273651a1a76d',
                   expected_versions=dict(numpy='2.2.5', torch='2.9.0+cpu', mujoco='3.3.6', gymnasium='1.2.1'),
                   profile=dict(controller='manual', device='cpu', seed=7, scenario='reproduction', texture='checker'),
                   schedule=dict(ticks=TICKS, actions=[[0, 1.0, 0.0], [TICKS // 2, 1.0, 0.5]]),
                   run_ids=dict(source=SOURCE_ID, replay=REPLAY_ID),
                   paths=dict(output_root=OUT, asset_root='/tmp/assets', source_root=SOURCE_ROOT))

    class Admission:
        _reg = dict(source_root=ROOT, source_files=inputs['source_files'], runtime=inputs['runtime'],
                    environment=dict(ENV0), episode=episode)
        _source, _dependencies = Source(), Dependencies()
        def recheck(self):
            rechecks.append(dict(phase=phase, t=round(time.monotonic() - T0, 3)))

    switch(PHASE + '.run')
    result = held.run(Admission())
except BaseException as e:
    import traceback
    error = dict(repr=repr(e)[:1000], traceback=traceback.format_exc()[-6000:])
switch('end')
end_maps = maps()
host = lambda s: sorted(p for p in s if not p.startswith((SITE + '/', PREFIX + '/', OUT + '/', ROOT + '/')))
rendering = map_points.get('after_renderer_identity') or map_points.get('after_open') or set()
out = dict(kind='diagnostic-held-episode-probe-v1', diagnostic_only=True, runtime_qualified=False, phase=PHASE,
           result=result, error=error, segments=segments, per_tick_seconds=per_tick, rechecks=rechecks,
           process_refusals=refusals, dlopens=dlopens,
           env_changed={k: os.environ.get(k) for k in sorted((set(os.environ) ^ set(ENV0)) | {k for k in ENV0 if ENV0[k] != os.environ.get(k)})},
           maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
           children_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, vm_end=vm(),
           wall_seconds=round(time.monotonic() - T0, 3), cpu_seconds=round(time.process_time() - C0, 3),
           modules_total=len(sys.modules), torchvision_loaded='torchvision' in sys.modules,
           dynamo_loaded='torch._dynamo' in sys.modules,
           host_mapped_during_rendering=host(rendering), host_mapped_end=host(end_maps),
           host_mapped_points={k: host(v) for k, v in map_points.items()},
           site_mapped_end=sorted(p for p in end_maps if p.startswith(SITE + '/')),
           non_stdlib_misses={n: r for n, r in sorted(misses.items()) if not r['stdlib']},
           stdlib_misses=sorted(n for n, r in misses.items() if r['stdlib']),
           resolved_not_loaded=sorted(n for n in requests if n not in misses and n not in sys.modules),
           loaded_by_segment=loaded, sysconfigdata_requested={k: v for k, v in requests.items() if 'sysconfigdata' in k})
with open(os.path.join(OUT, f'probe-{PHASE}.json'), 'w') as stream:
    json.dump(out, stream, indent=1, default=str)
print(json.dumps(dict(phase=PHASE, error=error and error['repr'], refusals=[(r['event'], r['args'][:2]) for r in refusals],
                      wall=out['wall_seconds'], maxrss_mib=out['maxrss_mib'],
                      result={k: (result or {}).get(k) for k in ('ticks_completed', 'final_phase', 'replay', 'bundle', 'renderer')})), flush=True)
