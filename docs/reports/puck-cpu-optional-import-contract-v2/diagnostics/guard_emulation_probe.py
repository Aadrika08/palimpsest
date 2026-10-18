"""Diagnostic only: emulate the held guard's finder decision on the held four imports.

For each request: declared negative -> stock absence (None); registered module or
stdlib top -> defer to PathFinder; anything else -> what the real guard refuses as
'Unregistered'. Refusals are recorded and then deferred so one pass lists them all.
Not admission, qualification or runtime evidence.
"""
import importlib, json, sys, traceback

SITE, REGISTRATION, NEGATIVES, OUT = sys.argv[1:5]
sys.path[:] = [SITE] + [p for p in sys.path if 'site-packages' not in p]
reg = json.load(open(REGISTRATION))
registered = {r['name'] for r in reg['modules']} | {r['name'] for r in reg['namespaces']}
negatives = set(NEGATIVES.split(','))
refused, denied = {}, set()

class Guard:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in negatives: denied.add(fullname); return None
        if fullname in registered or fullname.split('.')[0] in sys.stdlib_module_names: return None
        if fullname not in refused:
            refused[fullname] = [f'{f.filename.replace(SITE + "/", "")}:{f.lineno}'
                                 for f in traceback.extract_stack()[:-1] if 'importlib' not in f.filename][-3:]
        return None

sys.meta_path.insert(0, Guard())
done = []
for name in ('numpy', 'torch', 'torchvision', 'mujoco'):
    m = importlib.import_module(name); done.append([name, str.__str__(m.__version__)])
loaded_unregistered = sorted(n for n, m in sys.modules.items()
                             if getattr(m, '__file__', None) and str(m.__file__).startswith(SITE)
                             and n not in registered)
out = dict(kind='diagnostic-guard-emulation-probe-v1', diagnostic_only=True, completed=done,
           refused=refused, denied=sorted(denied), loaded_unregistered=loaded_unregistered)
json.dump(out, open(OUT, 'w'), indent=1)
print(json.dumps(dict(completed=done, refused=sorted(refused), loaded_unregistered=loaded_unregistered[:40],
                      n_loaded_unregistered=len(loaded_unregistered), denied_count=len(denied))))
