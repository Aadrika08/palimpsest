"""Diagnostic only: host mappings after interpreter start, numpy+torch, mujoco, upstream env import."""
import json, os, sys
SITE, ROOT, OUT = sys.argv[1:4]
sys.path[:] = [SITE, ROOT + '/src'] + [p for p in sys.path if 'site-packages' not in p]
PREFIX = os.path.dirname(os.path.dirname(os.path.dirname(os.__file__)))
def hook(event, args):
    if event in {'subprocess.Popen', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'os.system', 'pty.spawn', 'os.spawn'} or event.startswith('os.exec'):
        raise RuntimeError('refused ' + event)
sys.addaudithook(hook)
def maps():
    with open('/proc/self/maps') as s:
        return {l.split()[5] for l in s if len(l.split()) >= 6 and l.split()[5].startswith('/')
                and not l.split()[5].startswith((SITE + '/', PREFIX + '/'))}
points = [('interpreter', maps())]
import numpy, torch  # noqa
points.append(('numpy+torch', maps()))
import mujoco  # noqa
points.append(('mujoco', maps()))
from palimpsest.flynn import import_upstream
import_upstream(ROOT, 'environment.mujoco_two_cam_env_random_obstacles')
points.append(('upstream-env-import', maps()))
seen, out = set(), {}
for name, files in points:
    out[name] = sorted(files - seen); seen |= files
json.dump(out, open(OUT + '/maps-import-split.json', 'w'), indent=1)
print({k: len(v) for k, v in out.items()})
