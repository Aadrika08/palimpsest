"""One public lab parent, registered snapshot and goal-edit branch; no retries."""
import argparse
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time

from palimpsest.storage import StorageBudget, StorageLimits
from verify_afterimage import cleanup_check, process_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'docs/plans/route-material-2026-10-22.md'
LIMITS = StorageLimits(max_bytes=2 * 1024**3, min_free_bytes=2 * 1024**3)
EDIT = {'kind': 'move_goal', 'xy': [0., 0.]}


def pins():
    paths = [*sorted((ROOT / 'src/palimpsest').glob('*.py')), Path(__file__).resolve(),
             ROOT / 'scripts/verify_afterimage.py', ROOT / PLAN, ROOT / 'uv.lock', ROOT / 'pyproject.toml']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def wait(supervisor, run, predicate):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        view = supervisor.describe(run)
        if view['status'] == 'failed' or (view.get('state') or {}).get('phase') == 'failed':
            raise ValueError('lab owner failed: ' + str(view.get('failure')))
        if predicate(view):
            return view
        time.sleep(.01)
    raise TimeoutError('lab boundary exceeded 60 seconds')


def command(supervisor, run, kind, identifier):
    state = supervisor.describe(run)['state']
    return supervisor.call(run, 'command', {'id': identifier, 'kind': kind,
        'expected_state': state['phase'], 'expected_episode': state['episode'],
        'expected_revision': state['revision']})


def finish(supervisor, run):
    command(supervisor, run, 'run', 'route-continue-' + run)
    view = wait(supervisor, run, lambda v: v['state']['phase'] in ('terminated', 'truncated'))
    if not 100 < view['state']['total_tick'] <= 600:
        raise ValueError('route did not finish within its episode allocation')
    return view['state']

def parent_sequence(supervisor, run):
    for tick in range(100):
        state = supervisor.describe(run)['state']
        if state['phase'] != 'paused' or state['total_tick'] != tick:
            raise ValueError('parent cannot reach the declared paused boundary')
        command(supervisor, run, 'step', f'route-step-{tick}')
        view = wait(supervisor, run, lambda v: v['state']['total_tick'] == tick + 1)
        if view['state']['phase'] != 'paused':
            raise ValueError('parent ended before the declared snapshot boundary')
    result = supervisor.call(run, 'snapshot', {'expected_revision': view['state']['revision']})
    finish(supervisor, run)
    return result['snapshot_id']


def child(config):
    from palimpsest.lab import LabSupervisor
    from palimpsest.artifacts import export_run, registered_snapshots
    from palimpsest.comparison import export_comparison
    root = Path(config['output'])
    if pins() != config['sources']:
        raise ValueError('registered source pins changed')
    supervisor = LabSupervisor(ROOT, ROOT / 'data/assets/flynn', root,
        export_root=root / 'exports', startup_timeout=60, step_timeout=30,
        headless_continue=True, storage_limits=LIMITS)
    identities = []
    def remember(run):
        pid = supervisor.workers[run].process.pid
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
        identity = {'pid': pid, 'start_ticks': int(fields[19]), 'process_group': pid}
        identities.append(identity)
        write_json(root / run / 'owner-process.json', identity, supervisor.control_budget)
    def interrupted(signum, frame):
        raise SystemExit('route allocation interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        store = supervisor.control_budget
        write_json(root / 'generation/process.json', process_identity(), store)
        parent = supervisor.start({'controller': 'flynn', 'device': 'cpu', 'seed': 0,
                                   'scenario': 'reproduction', 'texture': 'checker'})
        remember(parent)
        wait(supervisor, parent, lambda v: v['status'] == 'ready' and v['sample'] is not None)
        snapshot_id = parent_sequence(supervisor, parent)
        snapshot_path, snapshot_entry = supervisor.snapshot(parent, snapshot_id)
        parent_state = supervisor.describe(parent)['state']
        supervisor.close(parent)
        assert snapshot_id in {x['snapshot_id'] for x in registered_snapshots(root / parent)}
        branch = supervisor.start({**snapshot_entry['config'], 'snapshot_path': str(snapshot_path),
            'snapshot_sha256': snapshot_entry['sha256'], 'snapshot_id': snapshot_id,
            'source_run_path': str(root / parent), 'replace_controller': False, 'intervention': EDIT})
        remember(branch)
        view = wait(supervisor, branch, lambda v: v['status'] == 'ready' and v['sample'] is not None)
        if view['state']['total_tick'] != 100 or view['state']['parent_run_id'] != parent:
            raise ValueError('branch restoration differs from registered boundary')
        branch_state = finish(supervisor, branch)
        supervisor.close(branch)
        export_run(root / parent, root / 'exports/borrowed-body.svg', 'svg', storage_budget=store)
        export_comparison(root / parent, root / branch, root / 'exports/one-map-many-lives.html', storage_budget=store)
        if pins() != config['sources']:
            raise ValueError('source pins changed during generation')
        result = {'status': 'passed', 'parent_run_id': parent, 'branch_run_id': branch,
                  'snapshot': snapshot_entry, 'branch_tick': 100, 'intervention': EDIT,
                  'parent_final_state': parent_state, 'branch_final_state': branch_state,
                  'qualification_claims': []}
    finally:
        supervisor.shutdown()
    if any(not cleanup_check(identity)['passed'] for identity in identities):
        raise ValueError('lab worker remained alive after shutdown')
    store = StorageBudget((root,), LIMITS)
    with store.lock():
        result['lab_workers_exited'] = True
        write_json(root / 'generation/result.json', result, store)


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
        raise ValueError('fresh canonical output required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise ValueError('commit source before generation')
    config = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'sources': pins(), 'output': str(root), 'timeout_seconds': 300,
              'branch_tick': 100, 'intervention': EDIT, 'qualification_claims': []}
    store = StorageBudget((root,), LIMITS, headroom_bytes=10 * 1024**2)
    with store.lock():
        store.check(1024**3, path=root)
        write_json(root / 'registration.json', config, store)
    from palimpsest.evaluate import bounded_process
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE='1', MUJOCO_GL='egl', MPLBACKEND='Agg', CUDA_VISIBLE_DEVICES='',
               OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT / 'scripts'))
    # The child LabSupervisor owns the writer lease; this parent only caps its logs.
    report = bounded_process([sys.executable, '-B', __file__, '--child', str(root / 'registration.json')],
                             root / 'generation', 300, env=env, log_max_bytes=1024**2)
    owners = []
    for receipt in root.glob('*/owner-process.json'):
        owner = json.loads(receipt.read_text())
        state = cleanup_check(owner)
        if state['same_process_alive'] and os.getpgid(owner['pid']) == owner['process_group']:
            os.killpg(owner['process_group'], signal.SIGTERM)
            time.sleep(.2)
            if cleanup_check(owner)['same_process_alive']:
                os.killpg(owner['process_group'], signal.SIGKILL)
        owners.append(cleanup_check(owner))
    identity = root / 'generation/process.json'
    cleanup = cleanup_check(json.loads(identity.read_text())) if identity.exists() else {'passed': False}
    passed = (report['status'] == 'completed' and report['returncode'] == 0 and cleanup['passed']
              and len(owners) == 2 and all(item['passed'] for item in owners))
    with store.lock():
        write_json(root / 'result.json', {'status': 'passed' if passed else 'failed',
                   'supervisor': report, 'cleanup': cleanup, 'lab_owner_cleanup': owners, 'qualification_claims': []}, store)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
