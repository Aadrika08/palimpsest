"""One bounded manual lab source and left-eye extraction; no retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from afterimage_material import SOURCE_BYTES, drive, extract
from palimpsest.storage import StorageBudget, StorageLimits
from verify_afterimage import cleanup_check, process_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'docs/plans/afterimage-material-2026-10-22.md'


def pins():
    paths = [*sorted((ROOT / 'src/palimpsest').glob('*.py')),
             ROOT / 'scripts/afterimage_material.py', Path(__file__).resolve(),
             ROOT / 'scripts/verify_afterimage.py', ROOT / PLAN, ROOT / 'uv.lock', ROOT / 'pyproject.toml']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def budget(root):
    return StorageBudget((root,), StorageLimits(max_bytes=2 * 1024**3, min_free_bytes=2 * 1024**3),
                         headroom_bytes=8 * 1024**2, recount_seconds=5)


def child(config):
    from palimpsest.engine import Engine
    root = Path(config['output'])
    store = budget(root)
    write_json(root / 'source/process.json', process_identity(), store)
    if pins() != config['sources']:
        raise ValueError('source pins changed')
    engine = None
    try:
        engine = Engine.open(ROOT, ROOT / 'data/assets/flynn', root / config['run_id'] / 'recording',
                             controller='manual', device='cpu', seed=0, run_id=config['run_id'],
                             scenario='reproduction', texture='checker', max_bytes=SOURCE_BYTES, storage_budget=store)
        result = drive(engine)
    finally:
        if engine is not None:
            engine.close()
    provenance = extract(root / config['run_id'], root / 'stimulus', store)
    if pins() != config['sources']:
        raise ValueError('source pins changed during recording')
    write_json(root / 'source/result.json', {'status': 'passed', **result, 'frames': len(provenance['frames'])}, store)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--child', type=Path)
    args = parser.parse_args()
    if args.child:
        child(json.loads(args.child.read_text()))
        return 0
    root = args.output.absolute()
    if root != root.resolve() or not root.is_relative_to(ROOT / 'runs') or root.exists():
        raise ValueError('fresh canonical runs/ output required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise ValueError('commit source before generation')
    from palimpsest.evaluate import bounded_process
    config = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'sources': pins(), 'output': str(root), 'run_id': uuid.uuid4().hex,
              'portrait_run_id': uuid.uuid4().hex, 'source_timeout_seconds': 300,
              'portrait_timeout_seconds': 120, 'qualification_claims': []}
    store = budget(root)
    with store.lock():
        store.check(SOURCE_BYTES + 128 * 1024**2, path=root)
        write_json(root / 'registration.json', config, store)
        env = os.environ.copy()
        env.update(PYTHONDONTWRITEBYTECODE='1', MUJOCO_GL='egl', MPLBACKEND='Agg', CUDA_VISIBLE_DEVICES='',
                   OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                   PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT / 'scripts'))
        report = bounded_process([sys.executable, '-B', __file__, '--child', str(root / 'registration.json')],
                                 root / 'source', 300, env=env, storage_budget=store)
        identity = root / 'source/process.json'
        cleanup = cleanup_check(json.loads(identity.read_text())) if identity.exists() else {'passed': False}
        passed = report['status'] == 'completed' and report['returncode'] == 0 and cleanup['passed']
        write_json(root / 'result.json', {'status': 'passed' if passed else 'failed',
                   'supervisor': report, 'cleanup': cleanup, 'qualification_claims': []}, store)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
