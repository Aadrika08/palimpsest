"""One bounded public FLYNN lab recording and offline Choir export; no retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from palimpsest.storage import StorageBudget, StorageLimits
from verify_afterimage import cleanup_check, process_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'docs/plans/choir-material-2026-10-22.md'
TARGET, MAX_TICKS, MAX_EPISODES = 6000, 6600, 64
SOURCE_BYTES, TOTAL_BYTES, FLOOR = 2 * 1024**3, 3 * 1024**3, 2 * 1024**3


def pins():
    paths = [*sorted((ROOT / 'src/palimpsest').glob('*.py')), Path(__file__).resolve(),
             ROOT / 'scripts/verify_afterimage.py', ROOT / PLAN, ROOT / 'uv.lock', ROOT / 'pyproject.toml',
             ROOT / 'model_manifests/flynn-full-vision.json']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def budget(root):
    return StorageBudget((root,), StorageLimits(max_bytes=TOTAL_BYTES, min_free_bytes=FLOOR),
                         headroom_bytes=8 * 1024**2, recount_seconds=5)


def drive(engine, heartbeat):
    """Keep every outcome; finish the episode crossing TARGET without a retry."""
    sequence = 0
    def command(kind, payload=None):
        nonlocal sequence
        sequence += 1
        receipt = engine.submit({'id': f'choir-{sequence}', 'kind': kind,
                                 'expected_state': engine.phase, 'expected_episode': engine.episode,
                                 'payload': payload or {}})
        if receipt['status'] != 'queued':
            raise ValueError('command was not queued')
        engine.advance()
    command('run')
    while True:
        if engine.phase == 'failed':
            raise ValueError('recording engine failed')
        if engine.total_tick > MAX_TICKS:
            raise ValueError('source interval ceiling exceeded')
        if engine.phase in ('terminated', 'truncated'):
            if engine.total_tick >= TARGET:
                break
            if engine.episode + 1 >= MAX_EPISODES:
                raise ValueError('episode allocation exhausted before 6000 intervals')
            command('reset', {'seed': engine.episode + 1})
            if engine.phase != 'paused':
                raise ValueError('reset did not pause')
            command('run')
        elif engine.phase == 'running':
            if engine.total_tick >= MAX_TICKS:
                raise ValueError('source did not terminate within interval ceiling')
            engine.advance()
        else:
            raise ValueError('unexpected engine phase')
        if engine.total_tick % 100 == 0:
            heartbeat({'intervals': engine.total_tick, 'episode': engine.episode, 'phase': engine.phase})
    heartbeat({'intervals': engine.total_tick, 'episode': engine.episode, 'phase': engine.phase})
    return {'intervals': engine.total_tick, 'episodes': engine.episode + 1}


def child(mode, config):
    root = Path(config['output'])
    store = budget(root)
    stage = root / mode
    write_json(stage / 'process.json', process_identity(), store)
    if pins() != config['sources']:
        raise ValueError('source pins changed')
    if mode == 'record':
        from palimpsest.engine import Engine
        engine = None
        try:
            engine = Engine.open(ROOT, ROOT / 'data/assets/flynn', root / config['run_id'] / 'recording',
                                 controller='flynn', device='cpu', seed=0, run_id=config['run_id'],
                                 scenario='reproduction', texture='checker', max_bytes=SOURCE_BYTES, storage_budget=store)
            result = drive(engine, lambda value: write_json(root / 'heartbeat.json', value, store))
        finally:
            if engine is not None:
                engine.close()
    else:
        from palimpsest.sonification import sonify
        output = sonify(root / config['run_id'], root / 'choir.wav', episode=None,
                       populations=['visual_left', 'visual_right', 'descending'], storage_budget=store)
        result = {'wav_bytes': output.stat().st_size, 'wav_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    if pins() != config['sources']:
        raise ValueError('source pins changed during stage')
    write_json(stage / 'result.json', {'status': 'passed', **result}, store)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--child', choices=('record', 'export'))
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    if args.child:
        child(args.child, json.loads(args.config.read_text()))
        return 0
    root = args.output.absolute()
    if root != root.resolve() or not root.is_relative_to(ROOT / 'runs') or root.exists():
        raise ValueError('fresh canonical runs/ output required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise ValueError('commit source before generation')
    from palimpsest.evaluate import bounded_process
    config = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'sources': pins(), 'output': str(root), 'run_id': uuid.uuid4().hex,
              'target_intervals': TARGET, 'max_intervals': MAX_TICKS, 'max_episodes': MAX_EPISODES,
              'record_timeout_seconds': 7200, 'export_timeout_seconds': 300,
              'qualification_claims': []}
    store = budget(root)
    with store.lock():
        store.check(SOURCE_BYTES + 32 * 1024**2, path=root)
        write_json(root / 'registration.json', config, store)
        env = os.environ.copy()
        env.update(PYTHONDONTWRITEBYTECODE='1', MUJOCO_GL='egl', MPLBACKEND='Agg', CUDA_VISIBLE_DEVICES='',
                   OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                   PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT / 'scripts'))
        stages = {}
        for mode, seconds in [('record', 7200), ('export', 300)]:
            report = bounded_process([sys.executable, '-B', __file__, '--child', mode,
                                      '--config', str(root / 'registration.json')], root / mode, seconds,
                                     env=env, storage_budget=store)
            identity = root / mode / 'process.json'
            cleanup = cleanup_check(json.loads(identity.read_text())) if identity.exists() else {'passed': False}
            stages[mode] = {'supervisor': report, 'cleanup': cleanup}
            passed = report['status'] == 'completed' and report['returncode'] == 0 and cleanup['passed']
            write_json(root / 'result.json', {'status': 'passed' if passed and mode == 'export' else 'incomplete' if passed else 'failed',
                       'stages': stages, 'qualification_claims': []}, store)
            if not passed:
                return 1
        if pins() != config['sources']:
            raise ValueError('source pins changed before finalization')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
