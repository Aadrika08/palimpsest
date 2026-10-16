"""Diagnostic only: exact policy-v5 semantics on the held four imports.

PathFinder is replaced by a wrapper: the 36 declared names (32 absent + 4 hidden)
are recorded and unresolvable by every finder, so imports see stock absence and
hidden modules never execute. Registered or stdlib requests delegate to PathFinder.
Any other request is what the real guard would refuse; it is recorded, then
delegated so one pass lists every such request.
Not admission, qualification or runtime evidence.
"""
import importlib, importlib.machinery, json, sys, traceback

SITE, REGISTRATION, ABSENT, HIDDEN, OUT = sys.argv[1:6]
sys.path[:] = [SITE] + [p for p in sys.path if 'site-packages' not in p]
reg = json.load(open(REGISTRATION))
registered = {r['name'] for r in reg['modules']} | {r['name'] for r in reg['namespaces']}
absent, hidden = set(ABSENT.split(',')), set(HIDDEN.split(','))
denied, refused = set(), {}
Path = importlib.machinery.PathFinder

class V5Path:
    @staticmethod
    def find_spec(fullname, path=None, target=None):
        if fullname in absent or fullname in hidden:
            denied.add(fullname); return None
        if fullname not in registered and fullname.split('.')[0] not in sys.stdlib_module_names:
            refused.setdefault(fullname, [f'{f.filename.replace(SITE + "/", "")}:{f.lineno}'
                for f in traceback.extract_stack()[:-1] if 'importlib' not in f.filename][-3:])
        return Path.find_spec(fullname, path, target)
    invalidate_caches = staticmethod(Path.invalidate_caches)

sys.meta_path[:] = [V5Path if f is Path else f for f in sys.meta_path]
done, error = [], None
for name in ('numpy', 'torch', 'torchvision', 'mujoco'):
    try:
        m = importlib.import_module(name); done.append([name, str.__str__(m.__version__)])
    except BaseException as e:
        error = dict(name=name, error=repr(e)[:400]); break
executed_hidden = sorted(n for n in hidden if n in sys.modules)
out = dict(kind='diagnostic-v5-semantics-probe-v1', diagnostic_only=True, completed=done, error=error,
           denied=sorted(denied), refused=refused, executed_hidden=executed_hidden,
           denied_outside_declared=sorted(denied - absent - hidden))
json.dump(out, open(OUT, 'w'), indent=1)
print(json.dumps(dict(completed=done, error=error, refused=sorted(refused), denied_count=len(denied),
                      undenied_declared=sorted((absent | hidden) - denied), executed_hidden=executed_hidden)))
