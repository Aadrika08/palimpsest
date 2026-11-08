"""Stage P of M7 navigation v4: dependency-closure import probe; opens no data input.

For each declared entry point, one fresh ``<python> -I`` child prepends the entry's
worktree ``scripts`` and ``src`` to ``sys.path``, imports the entry module WITHOUT
calling ``main`` and then resolves every non-optional import statement found in the
local closure, including function-level (lazy) imports. An audit hook blocks and
records any open of a worktree path outside source/plan trees or of a forbidden root.
The child records module origins, distribution versions, thread environment, the
CUDA-uninitialized state and any interpreter-path assertion. Any unresolved import,
blocked open, local module resolving outside the worktree or initialized CUDA is a
refusal. P is not a scientific attempt; it reserves nothing.

This parent module is stdlib-only, so the child can run this same file under ``-I``.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PROTOCOL_SHA256 = '238bc160d26c70273765eb1d51f8280383f99a88bc8f26ec4a829048552594f8'
MARKER = '@@M7-NAV-V4-PROBE-RESULT@@ '
DEFAULT_TIMEOUT = 120.0

ENTRYPOINTS = {
    'S0a': {'module': 'collect_male_teachers', 'commit': 'cc1cea93d4c3333a0ee2a091dd34fff0b2986887', 'thread_env': {}},
    'S0b': {'module': 'collect_male_recovery', 'commit': 'c382c86781a7a5d6651af721119789729cc890ae',
            'thread_env': {'OMP_NUM_THREADS': '2'}},
    'S0c': {'module': 'prepare_male_recovery_data', 'commit': '7d5fc1f4ecd1bbd6a5a139bde3585fb2255ce2fe', 'thread_env': {}},
    'S0d': {'module': 'train_male_recovery', 'commit': '19d275d7ba3d8c7da642a4b41d3a6a8f2d5c720f',
            'thread_env': {'OMP_NUM_THREADS': '1'}},
    'S0e': {'module': 'collect_male_navigation_v2', 'commit': '736e0cf0a71f6d700bd67836ee5f83911ceff90a',
            'thread_env': {'OMP_NUM_THREADS': '1'}},
    'S0f': {'module': 'prepare_male_navigation_v2', 'commit': '4ecb354efa4223abdbe3d09be118fe5402fec1a1', 'thread_env': {}},
    # The S0f historical child imports the old reader from the 217cbee root.
    'S0f-historical': {'module': 'prepare_male_recovery_data', 'commit': '217cbee8399dcb25045a079af012beecbbdae29e',
                       'thread_env': {}},
    # Planned v4 entry points live on the v4 branch; absent files are refused.
    'S1': {'module': 'train_male_navigation_v4', 'commit': None, 'thread_env': {'OMP_NUM_THREADS': '1'}},
    'S2': {'module': 'evaluate_male_navigation_v4', 'commit': None, 'thread_env': {'OMP_NUM_THREADS': '1'}},
}

# Worktree subtrees an import may read: source, plans/manifests (pin documents) and the
# pinned upstream cell. Everything else under the worktree (runs/, data/assets, ...) is data.
READABLE = ('src', 'scripts', 'docs', 'upstream', 'data/manifests', 'pyproject.toml', 'uv.lock')
RECORDED_ENV = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
                'MUJOCO_GL', 'CUDA_VISIBLE_DEVICES', 'PYOPENGL_PLATFORM')
INTERPRETER_ASSERTION = re.compile(r'lab-hardening|\.venv/bin/python|sys\.(executable|prefix|base_prefix)\s*(==|!=)')
OPTIONAL_HANDLERS = {'ImportError', 'ModuleNotFoundError', 'Exception', 'BaseException'}


# --------------------------------------------------------------------------- static helpers

def _optional(handlers):
    for handler in handlers:
        if handler.type is None: return True
        names = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        if any(isinstance(n, ast.Name) and n.id in OPTIONAL_HANDLERS for n in names): return True
    return False


def static_imports(source, module_name, is_package=False):
    """Every import statement: (absolute name, from-names, optional, line, module_level)."""
    tree = ast.parse(source)
    package = module_name if is_package else module_name.rpartition('.')[0]
    found = []

    def visit(nodes, optional, top):
        for node in nodes:
            if isinstance(node, ast.Import):
                found.extend((alias.name, (), optional, node.lineno, top) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = package.split('.') if package else []
                    base = base[:len(base)-(node.level-1)] if node.level > 1 else base
                    name = '.'.join(base + ([node.module] if node.module else []))
                else:
                    name = node.module
                found.append((name, tuple(a.name for a in node.names if a.name != '*'), optional, node.lineno, top))
            elif isinstance(node, ast.Try):
                visit(node.body, optional or _optional(node.handlers), top)
                for handler in node.handlers: visit(handler.body, optional, top)
                visit(node.orelse + node.finalbody, optional, top)
            elif isinstance(node, ast.If) and 'TYPE_CHECKING' in ast.unparse(node.test):
                visit(node.orelse, optional, top)
            else:
                nested = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
                visit(list(ast.iter_child_nodes(node)), optional, top and not nested)
    visit(tree.body, False, True)
    return found


def local_namespace(root):
    """Top-level module/package names that a worktree itself provides."""
    names = set()
    for base in (Path(root)/'scripts', Path(root)/'src'):
        if base.is_dir():
            for item in base.iterdir():
                if item.suffix == '.py': names.add(item.stem)
                elif item.is_dir() and not item.name.startswith(('.', '_')) and '.' not in item.name: names.add(item.name)
    return names


def interpreter_assertions(root, files):
    rows = []
    for path in files:
        try: lines = Path(path).read_text().splitlines()
        except (OSError, UnicodeDecodeError): continue
        for number, line in enumerate(lines, 1):
            if INTERPRETER_ASSERTION.search(line):
                rows.append({'file': Path(path).relative_to(root).as_posix(), 'line': number, 'text': line.strip()[:200]})
    return rows


# --------------------------------------------------------------------------- child

def _import_chain(error, missing=None):
    chain, tb = [], error.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        name = frame.f_globals.get('__name__', '')
        if frame.f_code.co_name == '<module>' and name not in ('__main__',) and not name.startswith('importlib'):
            if not chain or chain[-1] != name: chain.append(name)
        tb = tb.tb_next
    if missing and (not chain or chain[-1] != missing): chain.append(missing)
    return chain


def _child(config):
    import importlib
    import importlib.metadata
    root = Path(config['root']).resolve()
    readable = [root/p for p in READABLE]
    forbidden = [Path(p).resolve() for p in config['forbid']]
    denied = []

    def hook(event, args):
        if event != 'open' or not args or isinstance(args[0], int): return
        try: path = Path(os.path.abspath(os.fsdecode(args[0])))
        except (TypeError, ValueError): return
        inside = path == root or root in path.parents
        if (inside and not any(path == r or r in path.parents for r in readable)) or \
                any(path == f or f in path.parents for f in forbidden):
            denied.append(str(path))
            raise PermissionError('Stage P opens no data input: ' + str(path))
    sys.addaudithook(hook)
    sys.path[:0] = [str(root/'scripts'), str(root/'src')]
    unresolved, optional_unresolved, reasons = [], [], []
    entry = config['module']
    try:
        importlib.import_module(entry)
    except BaseException as error:  # noqa: BLE001 - every failure is a recorded refusal
        missing = getattr(error, 'name', None) if isinstance(error, ImportError) else None
        unresolved.append({'name': missing or entry, 'importer': None, 'line': None,
                           'chain': _import_chain(error, missing), 'error': f'{type(error).__name__}: {error}'[:512]})
    local_names = set(config['local_names']) | local_namespace(root)

    def is_local(module):
        origin = getattr(module, '__file__', None)
        return origin is not None and module is not sys.modules['__main__'] and (root/'src' in Path(origin).resolve().parents or
                                       root/'scripts' in Path(origin).resolve().parents)
    scanned, chains = set(), {entry: [entry]}
    while not unresolved:
        pending = [n for n, m in list(sys.modules.items()) if n not in scanned and m is not None and is_local(m)]
        if not pending: break
        for name in pending:
            scanned.add(name); module = sys.modules[name]
            chain = chains.get(name, [name])
            source = Path(module.__file__).read_text()
            is_package = Path(module.__file__).name == '__init__.py'
            for target, names, optional, line, _top in static_imports(source, name, is_package):
                attempts = [target] + [f'{target}.{n}' for n in names]
                for index, attempt in enumerate(attempts):
                    if index and hasattr(sys.modules.get(target), attempt.rpartition('.')[2]): continue
                    if attempt in sys.modules: continue
                    try:
                        importlib.import_module(attempt)
                        chains.setdefault(attempt, chain + [attempt])
                    except BaseException as error:  # noqa: BLE001
                        if index and isinstance(error, ImportError) and getattr(error, 'name', None) == attempt:
                            continue  # ``from package import attribute`` that is not a submodule
                        missing = getattr(error, 'name', None) if isinstance(error, ImportError) else None
                        inner = _import_chain(error, missing)
                        row = {'name': missing or attempt, 'importer': name, 'line': line,
                               'chain': chain + [c for c in inner if c not in chain] if inner else chain + [attempt],
                               'error': f'{type(error).__name__}: {error}'[:512]}
                        (optional_unresolved if optional else unresolved).append(row)
    modules, outside = {}, []
    for name, module in sorted(sys.modules.items()):
        if module is None or name == '__main__': continue
        origin = getattr(module, '__file__', None)
        modules[name] = str(Path(origin).resolve()) if origin else 'built-in'
        top = name.partition('.')[0]
        if top in local_names or name == entry:
            paths = [origin] if origin else list(getattr(module, '__path__', []))
            if any(p is not None and root not in Path(p).resolve().parents for p in paths):
                outside.append(name)
    if outside: reasons.append('Local modules resolve outside the worktree: ' + ', '.join(sorted(outside)))
    local_files = sorted({modules[n] for n, m in sys.modules.items() if m is not None and is_local(m)})
    distributions = importlib.metadata.packages_distributions()
    versions = {}
    for top in sorted({n.partition('.')[0] for n in modules}):
        if top in sys.stdlib_module_names or top in local_names: continue
        for dist in distributions.get(top, []):
            try: versions[top] = importlib.metadata.version(dist)
            except importlib.metadata.PackageNotFoundError: pass
    runtime = {'python': sys.version.split()[0], 'executable': sys.executable, 'prefix': sys.prefix,
               'base_prefix': sys.base_prefix, 'isolated': bool(sys.flags.isolated),
               'environment': {k: os.environ.get(k) for k in RECORDED_ENV},
               'torch_cuda_initialized': None, 'torch_threads': None}
    for name in ('numpy', 'torch', 'mujoco'):
        if name in sys.modules: runtime[name] = getattr(sys.modules[name], '__version__', None)
    if 'torch' in sys.modules:
        torch = sys.modules['torch']
        runtime['torch_cuda_initialized'] = bool(torch.cuda.is_initialized())
        runtime['torch_threads'] = torch.get_num_threads()
        if runtime['torch_cuda_initialized']: reasons.append('CUDA was initialized during import')
    if config.get('egl'):
        runtime['egl'] = _egl_identity(reasons)
    if unresolved: reasons.append('Unresolved imports: ' + ', '.join(r['name'] for r in unresolved))
    if denied: reasons.append('Blocked data opens: ' + ', '.join(denied))
    return {'status': 'refused' if reasons else 'passed', 'reasons': reasons, 'entry': entry, 'root': str(root),
            'unresolved': unresolved, 'optional_unresolved': optional_unresolved, 'modules': modules,
            'local_modules': local_files, 'versions': versions, 'runtime': runtime, 'denied_opens': denied,
            'interpreter_path_assertions': interpreter_assertions(root, local_files)}


def _egl_identity(reasons):
    """One offscreen context, no model loaded; failure is a refusal (S0 producers render)."""
    try:
        import mujoco
        context = mujoco.GLContext(16, 16); context.make_current()
        try:
            from OpenGL import GL
            value = {k: GL.glGetString(getattr(GL, 'GL_' + k.upper())).decode()
                     for k in ('vendor', 'renderer', 'version')}
        finally:
            context.free()
        return value
    except Exception as error:  # noqa: BLE001
        reasons.append(f'EGL identity unavailable: {type(error).__name__}: {error}'[:512])
        return None


# --------------------------------------------------------------------------- parent

def probe_entry(python, root, module, *, thread_env=None, forbid=(), egl=False, local_names=(),
                timeout=DEFAULT_TIMEOUT):
    """One fresh ``python -I`` child for one entry module; never calls ``main``."""
    python, root = Path(python), Path(root).resolve()
    base = {'entry': module, 'root': str(root), 'python': str(python)}
    if not python.is_absolute() or not python.exists():
        return {**base, 'status': 'refused', 'reasons': ['Explicit absolute interpreter path required']}
    config = {'root': str(root), 'module': module, 'forbid': [str(p) for p in forbid], 'egl': bool(egl),
              'local_names': list(local_names)}
    env = {'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', '/nonexistent'), 'LANG': 'C.UTF-8',
           'MUJOCO_GL': 'egl', 'CUDA_VISIBLE_DEVICES': '', 'PYTHONDONTWRITEBYTECODE': '1', **(thread_env or {})}
    try:
        done = subprocess.run([str(python), '-I', str(Path(__file__).resolve()), '--child', json.dumps(config)],
                              cwd=root, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {**base, 'status': 'refused', 'reasons': [f'Probe child exceeded {timeout} s']}
    lines = [line for line in done.stdout.splitlines() if line.startswith(MARKER)]
    if done.returncode != 0 or len(lines) != 1:
        return {**base, 'status': 'refused', 'returncode': done.returncode, 'stderr': done.stderr[-4096:],
                'reasons': ['Probe child did not return exactly one result']}
    result = json.loads(lines[0][len(MARKER):])
    return {**base, **result, 'python': str(python)}


def git_head(worktree):
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=worktree, capture_output=True,
                              text=True, timeout=10, check=True).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None


def probe_stage(python, stage, worktree, *, forbid=(), egl=False, timeout=DEFAULT_TIMEOUT):
    """A declared entry point in the stage's own worktree (producing commit for S0)."""
    entry = ENTRYPOINTS[stage]; worktree = Path(worktree).resolve()
    base = {'stage': stage, 'entry': entry['module'], 'root': str(worktree), 'python': str(python)}
    if entry['commit'] is not None and git_head(worktree) != entry['commit']:
        return {**base, 'status': 'refused', 'reasons': [f'{stage} worktree is not at {entry["commit"]}']}
    if not (worktree/'scripts'/(entry['module'] + '.py')).is_file():
        return {**base, 'status': 'refused', 'reasons': [f'{stage} entry point {entry["module"]} is not present']}
    result = probe_entry(python, worktree, entry['module'], thread_env=entry['thread_env'], forbid=forbid,
                         egl=egl, timeout=timeout)
    return {'stage': stage, 'commit': entry['commit'], **result}


def main(argv=None):
    if argv is None and len(sys.argv) == 3 and sys.argv[1] == '--child':
        try: result = _child(json.loads(sys.argv[2]))
        except BaseException as error:  # noqa: BLE001
            result = {'status': 'refused', 'reasons': [f'Probe child failure: {type(error).__name__}: {error}'[:512]]}
        sys.stdout.flush(); print(MARKER + json.dumps(result, sort_keys=True), flush=True)
        os._exit(0)  # no atexit/thread teardown from imported modules
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--python', required=True, help='Explicit absolute interpreter path')
    parser.add_argument('--stage', action='append', default=[], metavar='STAGE=WORKTREE',
                        help='Declared entry point and its worktree; repeatable')
    parser.add_argument('--root', help='Ad-hoc worktree root (with --module)')
    parser.add_argument('--module', help='Ad-hoc entry module (with --root)')
    parser.add_argument('--forbid', action='append', default=[], help='Data root that must never be opened')
    parser.add_argument('--egl', action='store_true', help='Record EGL identity from one offscreen context')
    parser.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)
    python = Path(args.python)
    if not python.is_absolute() or not python.exists():
        print(json.dumps({'status': 'refused', 'reasons': ['Explicit absolute interpreter path required']}))
        return 2
    results = []
    for item in args.stage:
        stage, _, worktree = item.partition('=')
        if stage not in ENTRYPOINTS or not worktree:
            print(json.dumps({'status': 'refused', 'reasons': [f'Undeclared stage entry {item}']})); return 2
        results.append(probe_stage(python, stage, worktree, forbid=args.forbid, egl=args.egl, timeout=args.timeout))
    if args.root or args.module:
        if not (args.root and args.module):
            print(json.dumps({'status': 'refused', 'reasons': ['--root and --module go together']})); return 2
        results.append(probe_entry(python, args.root, args.module, forbid=args.forbid, egl=args.egl, timeout=args.timeout))
    if not results:
        print(json.dumps({'status': 'refused', 'reasons': ['No entry point requested']})); return 2
    status = 'passed' if all(r['status'] == 'passed' for r in results) else 'refused'
    print(json.dumps({'status': status, 'protocol_sha256': PROTOCOL_SHA256, 'probes': results}, sort_keys=True))
    return 0 if status == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
