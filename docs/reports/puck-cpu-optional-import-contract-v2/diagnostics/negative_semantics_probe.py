"""Diagnostic only: compare declared-absence semantics on the held four imports.

mode=raise  -> head finder raises ModuleNotFoundError for declared names (current guard)
mode=none   -> head finder returns None for declared names (stock absence)
Not admission, qualification or runtime evidence.
"""
import importlib, json, sys, traceback

SITE, MODE, OUT, ROSTER = sys.argv[1], sys.argv[2], sys.argv[3], set(sys.argv[4].split(','))
sys.path[:] = [SITE] + [p for p in sys.path if 'site-packages' not in p]
denied = []

class Head:
    def find_spec(self, fullname, path=None, target=None):
        if fullname not in ROSTER: return None
        denied.append(fullname)
        if MODE == 'raise':
            raise ModuleNotFoundError('Explicit qualification import denial: ' + fullname, name=fullname)
        return None

sys.meta_path.insert(0, Head())
rows, error = [], None
for name in ('numpy', 'torch', 'torchvision', 'mujoco'):
    try:
        m = importlib.import_module(name)
        rows.append(dict(name=name, version=str.__str__(m.__version__)))
    except BaseException as e:
        tb = traceback.extract_tb(e.__traceback__)
        error = dict(name=name, error=repr(e)[:300],
                     frames=[f'{f.filename.replace(SITE + "/", "")}:{f.lineno}' for f in tb if 'importlib' not in f.filename][-4:])
        break
out = dict(kind='diagnostic-negative-semantics-probe-v1', diagnostic_only=True, mode=MODE,
           completed=[r['name'] for r in rows], error=error, denied=sorted(set(denied)))
json.dump(out, open(OUT, 'w'), indent=1)
print(json.dumps(out))
