"""Diagnostic only: record every import request no finder resolves during the
fixed CPU four-import sequence. Not admission, qualification or runtime evidence.

Run under a read-only sandbox with the held site as the only sys.path entry.
A tail meta-path finder sees exactly the names PathFinder could not resolve.
"""
import importlib, json, sys, time, traceback

SITE, OUT = sys.argv[1], sys.argv[2]
sys.path[:] = [SITE] + [p for p in sys.path if 'site-packages' not in p]
misses = []

class Tail:
    def find_spec(self, fullname, path=None, target=None):
        stack = [f'{f.filename}:{f.lineno}' for f in traceback.extract_stack()[:-1]
                 if 'importlib._bootstrap' not in f.filename][-4:]
        misses.append(dict(name=fullname, top=fullname.split('.')[0],
                           stdlib=fullname.split('.')[0] in sys.stdlib_module_names,
                           phase=phase, stack=stack, nmods=len(sys.modules)))
        return None

sys.meta_path.append(Tail())
phase = 'start'
rows = []
for phase in ('numpy', 'torch', 'torchvision', 'mujoco'):
    t = time.monotonic()
    try:
        m = importlib.import_module(phase)
        rows.append(dict(name=phase, version=str.__str__(m.__version__), seconds=time.monotonic() - t, nmods=len(sys.modules)))
    except BaseException as e:
        rows.append(dict(name=phase, error=repr(e)[:500]))
        break

non_stdlib = sorted({m['name'] for m in misses if not m['stdlib']})
json.dump(dict(kind='diagnostic-missing-import-census-v1', diagnostic_only=True,
               runtime_qualified=False, python=sys.version, imports=rows,
               non_stdlib_missing=non_stdlib, misses=misses), open(OUT, 'w'), indent=1)
print(json.dumps(dict(imports=rows, non_stdlib_missing=non_stdlib,
                      stdlib_missing=sorted({m['name'] for m in misses if m['stdlib']}))))
