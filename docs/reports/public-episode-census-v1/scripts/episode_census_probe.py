"""Diagnostic only: import closure, timing and process census of one bounded public
manual `reproduction` episode: the four held imports, Engine.open(manual, cpu,
fixed seed), an initial snapshot, N manual ticks, close, then actions replay and
export. Not admission, qualification or runtime evidence.

Run offline under a read-only bwrap sandbox. Recorders are passive: a head
meta-path finder sees every finder request, a tail finder sees requests no finder
resolved, an audit hook logs process/dlopen/open events, and subprocess.run and a
few engine helpers are wrapped only to time them (they always call the original).

MODE=census: stock resolution. MODE=v5: PathFinder is replaced so declared names
(absent + hidden) are unresolvable by every finder; anything else unregistered,
non-stdlib and non-local is recorded as a would-be guard refusal, then delegated.
"""
import importlib, importlib.machinery, json, os, resource, sys, time, traceback, uuid

(SITE, SRC, ROOT, ASSETS, OUT, MODE, REG, ABSENT, HIDDEN, EXTRA_REG,
 EXTRA_PATH, TICKS, SEED) = sys.argv[1:14]
FOUR = (sys.argv[14] if len(sys.argv) > 14 else '1') == '1'
TICKS, SEED = int(TICKS), int(SEED)
sys.path[:] = [SITE, SRC] + [p for p in sys.path if 'site-packages' not in p] + ([EXTRA_PATH] if EXTRA_PATH else [])
STDLIB = os.path.dirname(os.__file__)
UP = os.path.join(ROOT, 'upstream', 'fly-gym')
T0 = time.monotonic()
ENV0 = dict(os.environ)
phase = 'start'
requests, misses = {}, {}
proc_events, dlopens, opens, runs, subphases, sockets = [], [], {}, [], [], []
OPEN_ALLOW = tuple(p + '/' for p in (SITE, SRC, ROOT, STDLIB, OUT))


def _stack(limit=4):
    frames, f = [], sys._getframe(2)
    while f is not None and len(frames) < limit:
        name = f.f_code.co_filename
        if 'importlib' not in name and not name.endswith('episode_census_probe.py'):
            for prefix, tag in ((SITE + '/', ''), (SRC + '/', 'src:'), (UP + '/', 'upstream:'), (STDLIB + '/', 'stdlib:')):
                if name.startswith(prefix):
                    name = tag + name[len(prefix):]; break
            frames.append(f'{name}:{f.f_lineno}')
        f = f.f_back
    return frames


class Head:
    def find_spec(self, fullname, path=None, target=None):
        r = requests.get(fullname)
        if r is None:
            requests[fullname] = dict(phase=phase, n=1, stack=_stack())
        else:
            r['n'] += 1
        return None
    def invalidate_caches(self): pass


class Tail:
    def find_spec(self, fullname, path=None, target=None):
        r = misses.get(fullname)
        if r is None:
            misses[fullname] = dict(phase=phase, n=1, stack=_stack(),
                                    stdlib=fullname.split('.')[0] in sys.stdlib_module_names)
        else:
            r['n'] += 1
        return None
    def invalidate_caches(self): pass


reg = json.load(open(REG))
registered = {r['name'] for r in reg['modules']} | {r['name'] for r in reg['namespaces']}
registered |= set(filter(None, EXTRA_REG.split(',')))
absent, hidden = set(filter(None, ABSENT.split(','))), set(filter(None, HIDDEN.split(',')))
denied, refused = {}, {}
PathFinder = importlib.machinery.PathFinder


def _local(spec):
    origin = getattr(spec, 'origin', None) or ''
    locs = list(getattr(spec, 'submodule_search_locations', None) or ())
    return any(str(p).startswith((SRC + '/', UP + '/')) for p in [origin] + locs)


class V5Path:
    @staticmethod
    def find_spec(fullname, path=None, target=None):
        if fullname in absent or fullname in hidden:
            denied.setdefault(fullname, dict(phase=phase, stack=_stack()))
            return None
        spec = PathFinder.find_spec(fullname, path, target)
        if (fullname not in registered and fullname.split('.')[0] not in sys.stdlib_module_names
                and not (spec is not None and _local(spec))):
            refused.setdefault(fullname, dict(phase=phase, resolved=spec is not None, stack=_stack()))
        return spec
    invalidate_caches = staticmethod(PathFinder.invalidate_caches)
    find_distributions = staticmethod(PathFinder.find_distributions)


if MODE == 'v5':
    sys.meta_path[:] = [V5Path if f is PathFinder else f for f in sys.meta_path]
sys.meta_path.insert(0, Head())
sys.meta_path.append(Tail())


def _hook(event, args):
    try:
        if event in ('subprocess.Popen', 'os.posix_spawn', 'os.exec', 'os.fork', 'os.forkpty',
                     'os.system', 'os.spawn', 'pty.spawn', 'os.kill', 'os.killpg'):
            shown = [a if isinstance(a, (str, int, float, type(None))) else
                     (list(map(str, a))[:20] if isinstance(a, (list, tuple)) else
                      (sorted(a)[:40] if isinstance(a, dict) else type(a).__name__)) for a in args]
            proc_events.append(dict(event=event, phase=phase, t=round(time.monotonic() - T0, 3), args=shown))
        elif event == 'ctypes.dlopen':
            dlopens.append(dict(name=str(args[0]), phase=phase))
        elif event == 'open':
            p = args[0]
            if isinstance(p, bytes): p = p.decode('utf-8', 'replace')
            if isinstance(p, str) and not p.startswith(OPEN_ALLOW) and len(opens) < 400:
                opens.setdefault(p, dict(phase=phase, mode=str(args[1]) if len(args) > 1 else None))
        elif event.startswith('socket.'):
            if len(sockets) < 50: sockets.append(dict(event=event, phase=phase, args=repr(args)[:200]))
    except Exception:
        pass


sys.addaudithook(_hook)

import subprocess  # noqa: E402  (stdlib; wrapped only to time and log)
_run = subprocess.run


def _timed_run(*a, **k):
    argv = a[0] if a else k.get('args')
    rec = dict(argv=list(map(str, argv)) if isinstance(argv, (list, tuple)) else str(argv)[:200],
               phase=phase, timeout=k.get('timeout'))
    t = time.monotonic()
    try:
        r = _run(*a, **k)
        rec.update(returncode=r.returncode, stdout=str(r.stdout)[:300], stderr=str(r.stderr)[:300])
        return r
    except BaseException as e:
        rec['error'] = repr(e)[:300]
        raise
    finally:
        rec['seconds'] = round(time.monotonic() - t, 4)
        runs.append(rec)


subprocess.run = _timed_run


def origin(name):
    m = sys.modules.get(name)
    f = getattr(m, '__file__', None)
    if f is None:
        spec = getattr(m, '__spec__', None)
        o = getattr(spec, 'origin', None)
        locs = list(getattr(spec, 'submodule_search_locations', None) or ())
        if o in ('built-in', 'frozen'): return o
        if locs: f = str(locs[0]) + '/__init__'
        else: return 'nofile'
    f = str(f)
    for prefix, tag in ((SITE + '/', 'site'), (SRC + '/', 'src'), (UP + '/', 'upstream'), (STDLIB + '/', 'stdlib')):
        if f.startswith(prefix): return tag
    return 'other:' + f


seen, results, loaded = set(sys.modules), [], {}
FILE_OF = {}


def _account(name, before):
    new = sorted(set(sys.modules) - before)
    loaded[name] = [[n, origin(n)] for n in new]
    for n in new:
        f = getattr(sys.modules.get(n), '__file__', None)
        if f: FILE_OF[n] = str(f)
    seen.update(sys.modules)
    counts = {}
    for _, o in loaded[name]:
        k = o.split(':')[0]
        counts[k] = counts.get(k, 0) + 1
    return len(new), counts


class Sub:
    def __init__(self, name): self.name = name
    def __enter__(self):
        global phase
        self.outer, phase = phase, self.name
        self.before, self.t, self.c = set(sys.modules), time.monotonic(), time.process_time()
    def __exit__(self, *exc):
        global phase
        n, counts = _account(self.name, self.before)
        subphases.append(dict(phase=self.name, seconds=round(time.monotonic() - self.t, 4),
                              cpu_seconds=round(time.process_time() - self.c, 4), new_modules=n, origins=counts,
                              error=None if exc[0] is None else repr(exc[1])[:300]))
        phase = self.outer
        return False


def step(name, fn):
    global phase
    phase = name
    before, t, c = set(sys.modules), time.monotonic(), time.process_time()
    rec = dict(phase=name)
    try:
        rec['result'] = fn()
    except BaseException as e:
        rec['error'] = repr(e)[:1000]
        rec['traceback'] = traceback.format_exc()[-6000:]
    rec['seconds'] = round(time.monotonic() - t, 4)
    rec['cpu_seconds'] = round(time.process_time() - c, 4)
    rec['elapsed_total'] = round(time.monotonic() - T0, 4)
    rec['maxrss_mib'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    rec['threads'] = len(os.listdir('/proc/self/task'))
    rec['fds'] = len(os.listdir('/proc/self/fd'))
    rec['vm'] = vm_status()
    rec['new_modules'], rec['origins'] = _account(name, before)
    rec['nmods'] = len(sys.modules)
    results.append(rec)
    print(json.dumps({k: rec[k] for k in ('phase', 'seconds', 'new_modules') if k in rec} |
                     ({'error': rec['error'][:200]} if 'error' in rec else {})), file=sys.stderr, flush=True)
    return 'error' not in rec


def vm_status():
    out = {}
    with open('/proc/self/status') as stream:
        for line in stream:
            if line.startswith(('VmPeak:', 'VmSize:', 'VmHWM:', 'VmRSS:')):
                out[line.split(':')[0]] = round(int(line.split()[1]) / 1024, 1)
    return out


def mapped_native():
    prefix = os.path.dirname(os.path.dirname(STDLIB))
    files = set()
    with open('/proc/self/maps') as stream:
        for line in stream:
            parts = line.split()
            if len(parts) >= 6 and parts[5].startswith('/') and not parts[5].startswith((SITE + '/', prefix + '/')):
                files.add(parts[5])
    return sorted(files)


def gl_strings():
    import ctypes
    lib = ctypes.CDLL('libOpenGL.so.0')
    lib.glGetString.restype = ctypes.c_char_p
    return {name: (lib.glGetString(code) or b'').decode() for name, code in
            (('vendor', 0x1F00), ('renderer', 0x1F01), ('version', 0x1F02))}


def gl_libraries():
    keep = ('egl', 'gl', 'dri', 'nvidia', 'gallium', 'llvm', 'mesa', 'glfw', 'vulkan', 'drm', 'gbm', 'wayland', 'x11', 'xcb')
    libs = set()
    with open('/proc/self/maps') as stream:
        for line in stream:
            p = line.split()[-1] if len(line.split()) >= 6 else ''
            base = os.path.basename(p).lower()
            if '.so' in base and any(k in base for k in keep) and not p.startswith(SITE + '/torch'):
                libs.add(p)
    return sorted(libs)


state = {}
run_id = uuid.uuid4().hex
run_dir = os.path.join(OUT, run_id)
os.makedirs(run_dir)

ok = True
for name in ('numpy', 'torch', 'torchvision', 'mujoco') if FOUR else ():
    ok = ok and step('import.' + name, lambda name=name: str.__str__(importlib.import_module(name).__version__))


def import_palimpsest():
    from palimpsest.engine import Engine  # noqa: F401
    import palimpsest.doctor as doctor
    import palimpsest.engine as engine
    original_diagnose, original_make = doctor.diagnose, engine._make_manual_environment

    def diagnose(*a, **k):
        with Sub('open.diagnose'):
            report = original_diagnose(*a, **k)
        state['diagnose'] = report
        return report

    def make(*a, **k):
        flynn = sys.modules['palimpsest.flynn']
        original_import = flynn.import_upstream
        def import_upstream(*ia, **ik):
            with Sub('open.import_upstream'):
                return original_import(*ia, **ik)
        flynn.import_upstream = import_upstream
        try:
            with Sub('open.make_manual_environment'):
                env = original_make(*a, **k)
        finally:
            flynn.import_upstream = original_import
        if 'gl_libraries' not in state:
            global phase
            outer, phase = phase, 'diag.gl'
            try:
                state['gl_libraries'] = gl_libraries()
                state['mapped_native_after_env'] = mapped_native()
                try:
                    env.renderer._gl_context.make_current()
                    state['gl_strings'] = gl_strings()
                except Exception as error:
                    state['gl_strings'] = repr(error)[:300]
            finally:
                phase = outer
        return env

    doctor.diagnose, engine._make_manual_environment = diagnose, make
    return dict(engine_file=engine.__file__, seam=hasattr(engine, '_make_manual_environment'))


ok = ok and step('import.palimpsest', import_palimpsest)


def open_engine():
    from palimpsest.engine import Engine
    state['engine'] = Engine.open(ROOT, ASSETS, os.path.join(run_dir, 'recording'), controller='manual',
                                  device='cpu', seed=SEED, scenario='reproduction', texture='checker', run_id=run_id)
    e = state['engine']
    return dict(public=e.public_state(), env=type(e.env).__module__ + '.' + type(e.env).__qualname__,
                width=e.env.W, height=e.env.H, frame_skip=e.env.frame_skip, n_obstacles=len(e.env._obstacle_xy))


ok = ok and step('open', open_engine)


def snapshot():
    from palimpsest.replay import _register_initial
    return dict(snapshot_id=_register_initial(state['engine'], __import__('pathlib').Path(run_dir)),
                bytes=os.path.getsize(os.path.join(run_dir, 'snapshots', 'initial.snp')))


ok = ok and step('snapshot', snapshot)


def ticks():
    e, per, receipts = state['engine'], [], []
    for i in range(TICKS):
        t = time.monotonic()
        action = [1.0, 0.0] if i < TICKS // 2 else [1.0, 0.5]
        if i in (0, TICKS // 2):
            receipts.append(e.submit(dict(id=f'a{i}', kind='set_action', expected_state='paused',
                                          expected_episode=0, payload=dict(action=action)))['status'])
        receipts.append(e.submit(dict(id=f's{i}', kind='step', expected_state='paused', expected_episode=0))['status'])
        s = e.advance()
        per.append(round(time.monotonic() - t, 4))
        if s['phase'] != 'paused':
            break
    s = e.public_state()
    return dict(per_tick_seconds=per, final=dict(phase=s['phase'], total_tick=s['total_tick'],
                episode_step=s['episode_step'], metrics=s['metrics'], last_outcome=s['last_outcome']),
                receipt_status=sorted(set(receipts)),
                applied=sorted({r['status'] for r in e.receipts.values()}))


ok = ok and step('ticks', ticks)


def close():
    state['engine'].close()
    manifest = json.load(open(os.path.join(run_dir, 'recording', 'manifest.json')))
    return dict(status=manifest.get('status'), files=sorted(os.listdir(os.path.join(run_dir, 'recording'))))


ok = ok and step('close', close)
if ok:
    def replay():
        from palimpsest.replay import replay_run
        dest = os.path.join(OUT, uuid.uuid4().hex)
        os.makedirs(dest)
        report = replay_run(run_dir, dest, mode='actions', repo_root=ROOT, asset_root=ASSETS)
        return {k: report.get(k) for k in ('status', 'compared_ticks', 'compared_events', 'first_divergence', 'errors')}
    step('replay.actions', replay)

    def export(fmt):
        from palimpsest.artifacts import export_run
        path = export_run(run_dir, os.path.join(OUT, f'export.{fmt}' if fmt != 'bundle' else 'export.zip'), fmt)
        return dict(path=str(path), bytes=os.path.getsize(path))
    step('export.svg', lambda: export('svg'))
    step('export.bundle', lambda: export('bundle'))

phase = 'end'
diag = state.get('diagnose')
if diag:
    diag = dict(ready=diag.get('ready'), checks=[dict(name=c['name'], status=c['status'],
                detail=c['detail'] if c['name'] in ('upstream', 'gpu', 'python', 'renderer') or c['status'] != 'ok' else None)
                for c in diag['checks']])
non_stdlib_misses = {n: r for n, r in misses.items() if not r['stdlib']}
resolved_not_loaded = sorted(n for n in requests if n not in misses and n not in seen)
out = dict(kind='diagnostic-episode-census-v1', diagnostic_only=True, runtime_qualified=False, mode=MODE,
           python=sys.version, argv=sys.argv[1:], sys_path=sys.path, env={k: os.environ.get(k) for k in sorted(os.environ)},
           phases=results, subphases=subphases, diagnose=diag, gl_libraries=state.get('gl_libraries'), gl_strings=state.get('gl_strings'),
           mapped_native_after_env=state.get('mapped_native_after_env'), mapped_native_end=mapped_native(),
           subprocess_runs=runs, process_events=proc_events, dlopens=dlopens, sockets=sockets,
           opens_outside_allowed=opens, non_stdlib_misses=non_stdlib_misses,
           stdlib_misses=sorted(n for n, r in misses.items() if r['stdlib']),
           requests=requests, resolved_not_loaded=resolved_not_loaded,
           loaded_by_phase=loaded, module_files=FILE_OF,
           v5=dict(denied=denied, refused=refused, executed_hidden=sorted(n for n in hidden if n in seen),
                   undenied_declared=sorted((absent | hidden) - set(denied))) if MODE == 'v5' else None,
           four_imports=FOUR, four_loaded_at_end={n: n in sys.modules for n in ('numpy', 'torch', 'torchvision', 'mujoco', 'torch._dynamo')},
           env_changed={k: os.environ.get(k) for k in sorted((set(os.environ) ^ set(ENV0)) | {k for k in ENV0 if ENV0[k] != os.environ.get(k)})})
with open(os.path.join(OUT, f'census-{MODE}.json'), 'w') as stream:
    json.dump(out, stream, indent=1, default=str)
print(json.dumps(dict(mode=MODE, phases=[{k: r.get(k) for k in ('phase', 'seconds', 'new_modules', 'error')} for r in results],
                      non_stdlib_misses=sorted(non_stdlib_misses), subprocess=[r['argv'][:3] for r in runs],
                      refused=sorted(refused), denied=len(denied))), flush=True)
print(json.dumps(dict(phase='teardown-start', elapsed_total=round(time.monotonic() - T0, 3))), file=sys.stderr, flush=True)
