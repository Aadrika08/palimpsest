"""Diagnostic only: split host mappings into pre-renderer (all episode imports done)
versus renderer construction and first frames. Same env and refusing hook as the
held episode probe. Not admission or runtime evidence."""
import json, os, sys
SITE, ROOT, OUT = sys.argv[1:4]
sys.path[:] = [SITE, ROOT + '/src'] + [p for p in sys.path if 'site-packages' not in p]
PREFIX = os.path.dirname(os.path.dirname(os.path.dirname(os.__file__)))
refused = []
def hook(event, args):
    if event in {'subprocess.Popen', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'os.system', 'pty.spawn', 'os.spawn'} or event.startswith('os.exec'):
        refused.append(event); raise RuntimeError('refused ' + event)
sys.addaudithook(hook)
def maps():
    with open('/proc/self/maps') as s:
        return sorted({l.split()[5] for l in s if len(l.split()) >= 6 and l.split()[5].startswith('/')
                       and not l.split()[5].startswith((SITE + '/', PREFIX + '/'))})
import numpy, torch, mujoco  # noqa
from palimpsest.flynn import import_upstream
from palimpsest.profiles import validate
from palimpsest.engine import _make_manual_environment
import_upstream(ROOT, 'environment.mujoco_two_cam_env_random_obstacles')
before = maps()
env = _make_manual_environment(ROOT, validate('reproduction', 'checker', 'manual'), 'checker')
after_construct = maps()
obs, _ = env.reset(seed=7)
for _ in range(3): obs = env.step(numpy.array([1.0, 0.0]))[0]
after_frames = maps()
env.renderer.close(); env.close()
json.dump(dict(before_renderer=before, added_by_construct=sorted(set(after_construct) - set(before)),
               added_by_frames=sorted(set(after_frames) - set(after_construct)), refused=refused,
               frame=[list(obs['cam_left'].shape), str(obs['cam_left'].dtype), int(obs['cam_left'].std() > 0)]),
          open(OUT + '/maps-split.json', 'w'), indent=1)
print(len(before), len(after_construct), len(after_frames), refused)
