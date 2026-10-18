"""Isolate the upstream runtime and retain bounded, explicitly labelled evidence."""

from dataclasses import asdict
from datetime import datetime, timezone
import contextlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time


def _json(path, value, budget=None):
    payload = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if budget is not None:
        budget.check(len(payload), path=path)
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(payload)
    temporary.replace(path)


@contextlib.contextmanager
def bounded_logs(output, max_bytes, on_failure):
    """Drain native/Python output through pipes; retain only each bounded prefix."""
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError('log limit must be a positive byte count')
    writers, readers, threads = [], [], []
    def drain(fd, path):
        used, failed = 0, False
        try:
            with path.open('xb') as target:
                while block := os.read(fd, 65536):
                    kept = block[:max(0, max_bytes - used)]
                    target.write(kept)
                    used += len(kept)
                    if len(kept) != len(block) and not failed:
                        target.flush()
                        os.fsync(target.fileno())
                        failed = True
                        on_failure(f'{path.name} exceeded {max_bytes} bytes; retained prefix')
                target.flush()
                os.fsync(target.fileno())
        except OSError as error:
            on_failure(f'{path.name}: {error}')
        finally:
            with contextlib.suppress(OSError):
                os.close(fd)
    try:
        for name in ('stdout.log', 'stderr.log'):
            reader, writer = os.pipe()
            readers.append(reader)
            writers.append(os.fdopen(writer, 'wb', buffering=0))
            thread = threading.Thread(target=drain, args=(reader, Path(output) / name), daemon=True)
            thread.start()
            readers.remove(reader)  # Started drains own their reader descriptor.
            threads.append(thread)
        yield writers
    finally:
        for writer in writers:
            try:
                writer.close()
            except OSError as error:
                on_failure(f'native log pipe cleanup failed: {error}')
        for thread in threads:
            thread.join(timeout=2.)
            if thread.is_alive():
                on_failure('native log drain/final sync timed out')
        for reader in readers:
            with contextlib.suppress(OSError):
                os.close(reader)


def bounded_process(command, output, timeout, env=None, *, log_max_bytes=1024**2, storage_budget=None):
    """One isolated process group; timeout includes model loading and renderer stalls."""
    output = Path(output)
    control_budget = None
    if storage_budget is not None:
        from .storage import StorageBudget
        storage_budget.check(1024**2, path=output)
        control_budget = StorageBudget(storage_budget.roots, storage_budget.limits)
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'status': 'running', 'timeout_seconds': timeout,
              'started_utc': datetime.now(timezone.utc).isoformat(), 'output': str(output)}
    _json(output / 'supervisor.json', report, control_budget)
    started, process = time.perf_counter(), None
    log_failure = []
    def fail_log(reason):
        log_failure.append(reason)
        if process is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
    try:
        with bounded_logs(output, log_max_bytes, fail_log) as (stdout, stderr):
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=env,
                                       start_new_session=True)
            if log_failure:
                fail_log(log_failure[0])
            try:
                code = process.wait(timeout=timeout)
                report['status'] = 'completed' if code == 0 else 'failed'
            except subprocess.TimeoutExpired:
                report['status'] = 'timeout'
            except KeyboardInterrupt:
                report['status'] = 'interrupted'
            finally:
                # Descendants can outlive their leader while retaining a log pipe.
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGTERM)
                if process.poll() is None:
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        with contextlib.suppress(ProcessLookupError):
                            os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=3)
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
    except OSError as error:
        report.update(status='failed', error=str(error))
    finally:
        report.update(returncode=process.returncode if process else None,
                      elapsed_seconds=time.perf_counter() - started)
        if log_failure:
            report.update(status='failed', failure={'type': 'LogLimit', 'message': log_failure[0]})
        _json(output / 'supervisor.json', report, control_budget)
    return report


def outcome(terminated, truncated, info, goal_radius):
    if terminated:
        if info['dist_to_goal'] < goal_radius:
            return 'goal'
        if info['stalled']:
            return 'stalled'
        return 'collision'
    return 'time_limit' if truncated else None


def evaluate(repo_root, asset_root, args):
    from .storage import StorageBudget, StorageLimits
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = (args.output or repo_root / 'runs' / f'{stamp}-{args.controller}').resolve()
    assets = Path(asset_root).resolve()
    managed_root = output.parent
    if managed_root == assets or managed_root in assets.parents or assets in managed_root.parents:
        raise ValueError('Model assets must be outside managed storage roots')
    log_max_bytes = getattr(args, 'log_max_bytes', 1024**2)
    if type(log_max_bytes) is not int or not 1024 <= log_max_bytes <= 64 * 1024**2:
        raise ValueError('Per-stream log limit must be 1 KiB to 64 MiB')
    limits = StorageLimits(max_bytes=getattr(args, 'storage_max_bytes', 20 * 1024**3),
        min_free_bytes=getattr(args, 'min_free_bytes', 1024**3), max_runs=getattr(args, 'max_runs', 1024),
        max_snapshots=getattr(args, 'max_snapshots', 64), max_exports=getattr(args, 'max_exports', 1024))
    budget = StorageBudget((managed_root,), limits, headroom_bytes=2 * log_max_bytes + 8 * 1024**2)
    control_budget = StorageBudget(budget.roots, limits)
    config = {key: getattr(args, key) for key in
              ('controller', 'device', 'episodes', 'max_steps', 'seed', 'parity', 'max_bytes', 'threads')}
    config.update(repo_root=str(repo_root), asset_root=str(asset_root), output=str(output))
    config['storage'] = {'roots': [str(path) for path in budget.roots], 'limits': asdict(limits),
                         'headroom_bytes': budget.headroom_bytes}
    env = os.environ.copy()
    env.setdefault('MUJOCO_GL', 'egl')
    env['OMP_NUM_THREADS'] = str(args.threads)
    env['MPLBACKEND'] = 'Agg'
    with budget.lock():
        budget.check_count('runs', sum(path.is_dir() for path in managed_root.iterdir()))
        budget.check(1024**2, path=output)
        report = bounded_process([sys.executable, '-m', 'palimpsest.evaluate', json.dumps(config)],
                                 output, args.timeout, env, log_max_bytes=log_max_bytes, storage_budget=budget)
        manifest = output / 'recording/manifest.json'
        if manifest.exists():
            try:
                report['recording'] = json.loads(manifest.read_text())
            except (OSError, ValueError) as error:
                report.update(status='failed', error=f'Invalid recording manifest: {error}')
            if report['status'] == 'completed' and report.get('recording', {}).get('status') != 'completed':
                report['status'] = 'failed'
        elif report['status'] == 'completed':
            report.update(status='failed', error='Worker exited without a recording manifest')
        _json(output / 'supervisor.json', report, control_budget)
        return report


def _evaluation_preflight(observation, policy, config, budget):
    cameras = sum(observation[name].nbytes for name in ('cam_left', 'cam_right'))
    neural = (policy.agent.cell.Nin + 2) * policy.hidden.element_size() if policy is not None else 0
    ticks = config['episodes'] * config['max_steps']
    estimate = ticks * (cameras + neural + 4096) + 1024**2
    if estimate > config['max_bytes']:
        raise RuntimeError('Estimated batch recording exceeds per-recording quota before first step')
    return {'planned_ticks': ticks, 'raw_camera_bytes_per_tick': cameras, 'neural_bytes_per_tick': neural,
            'recording_bytes_estimate': estimate,
            'scope': 'uncompressed planned batch and scalar/NPZ/event allowance; actual writes remain bounded',
            'admission': budget.check(estimate, path=Path(config['output']) / 'recording')}


def worker(config):
    # Imports stay inside the bounded child, after renderer/thread environment setup.
    from .records import RunWriter
    from .assets import load_manifest, prepare_graph, sha256_file, verify_assets
    from .doctor import diagnose

    root, assets, output = (Path(config[key]) for key in ('repo_root', 'asset_root', 'output'))
    from .storage import StorageBudget, StorageLimits
    storage = config.get('storage')
    budget = StorageBudget(tuple(Path(path) for path in storage['roots']), StorageLimits(**storage['limits']),
                           headroom_bytes=storage['headroom_bytes']) if storage else None
    writer = RunWriter(output / 'recording', {
        'schema_version': 1,
        'configuration': config, 'profile': 'flynn-full-vision' if config['controller'] == 'flynn' else 'privileged-teacher',
        'observation_profile': 'two-rgb-eyes-contact-relative-goal-bearing-v1',
        'teacher_privileged': config['controller'] == 'teacher',
        'replay_capabilities': ['playback', 'recorded-inputs'],
        'snapshot_capability': False,
        'tick_contract': 'input and pose before step; control, next_pose, reward and time after step',
        'sensor_order': ['collision', 'collision_angle', 'wind_cos', 'wind_sin'],
        'parity_tolerance': {'atol': 1e-6, 'rtol': 1e-6},
        'recording_budget_bytes': config['max_bytes'],
        'budget_scope': 'recording files including atomic manifest staging; supervisor logs excluded',
    }, max_bytes=config['max_bytes'], storage_budget=budget)
    env = policy = None
    started = time.perf_counter()
    try:
        diagnosis = diagnose(root, assets)
        writer.event('diagnostics', report=diagnosis)
        # Teacher needs the same frozen runtime but not the graph/checkpoint.
        required = [check for check in diagnosis['checks']
                    if check['name'] in ('python', 'upstream') or check['name'].startswith('dependency:')]
        if any(check['status'] != 'ok' for check in required):
            raise RuntimeError('Runtime diagnostics failed; see diagnostics event')
        import numpy as np
        import torch
        import random
        import resource
        import mujoco
        from .flynn import import_upstream, load_policy

        torch.set_num_threads(config['threads'])
        random.seed(config['seed'])
        np.random.seed(config['seed'])
        torch.manual_seed(config['seed'])
        reference = import_upstream(root, 'run_connectome_rnn_checkpoint')
        env = reference._make_env(None, reference.N_OBSTACLES)
        from OpenGL import GL
        renderer = GL.glGetString(GL.GL_RENDERER)
        dt = float(env.model.opt.timestep * env.frame_skip)
        writer.event('environment', control_interval_seconds=dt, width=env.W, height=env.H,
                     upstream_commit=load_manifest(root)['upstream_commit'],
                     lock_sha256=sha256_file(root / 'uv.lock'),
                     renderer=renderer.decode() if renderer else 'unknown',
                     renderer_backend=os.environ.get('MUJOCO_GL', 'default'),
                     source_sha256={str(path.relative_to(root)): sha256_file(path)
                                    for path in sorted((root / 'src/palimpsest').glob('*.py'))})
        if config['controller'] == 'flynn':
            if not verify_assets(root, assets)['ok']:
                raise ValueError('Missing/corrupt pinned model assets')
            edge = prepare_graph(root, assets)
            checkpoint = next(item for item in load_manifest(root)['files'] if item['id'] == 'checkpoint')
            policy = load_policy(root, edge, assets / checkpoint['path'], config['device'], config['seed'])
            writer.event('policy_loaded', provenance=policy.provenance)
        load_seconds = time.perf_counter() - started
        summaries, all_latency, all_step_latency, parity_ticks = [], [], [], 0
        rollout_started = time.perf_counter()
        for episode in range(config['episodes']):
            seed = config['seed'] + episode
            # Upstream reset leaves wheel phase, time and solver state from the prior episode.
            # Start each development layout from fresh physics for cross-controller pairing.
            mujoco.mj_resetData(env.model, env.data)
            obs, _ = env.reset(seed=seed)
            if policy:
                policy.reset()
            else:
                # Upstream teacher.reset leaves the planner's previous path direction.
                teacher = reference.PlannerAnalyticTeacher(arena_half_extent=env.arena, device='cpu')
            if episode == 0 and budget is not None:
                writer.event('storage_preflight', **_evaluation_preflight(obs, policy, config, budget))
            writer.event('episode_started', episode=episode, seed=seed,
                         reset_protocol='fresh physics and controller episode state; upstream seeded layout',
                         goal=env._goal_xy.tolist(), obstacles=env._obstacle_xy.tolist(),
                         initial_qpos=env.data.qpos.tolist(), initial_qvel=env.data.qvel.tolist())
            reward_total, contacts, path_length = 0., 0, 0.
            reason = 'step_budget'
            for tick in range(config['max_steps']):
                pose = np.array([*env._base_xy(), env._base_yaw()], dtype=np.float64)
                before = time.perf_counter()
                if policy:
                    result = policy.act(obs, check_parity=config['parity'])
                    action = result['action']
                    if config['parity']:
                        parity_ticks += 1
                        writer.event('parity', episode=episode, tick=tick, result=result['parity'])
                    neural = {key: result[key] for key in ('encoded_input', 'raw_output')}
                else:
                    action = teacher.act(env)
                    if hasattr(action, 'detach'):
                        action = action.detach().cpu().numpy()
                    action = np.asarray(action).reshape(-1)
                    neural = {}
                latency = time.perf_counter() - before
                action = np.asarray(action, dtype=np.float32)
                if action.shape != (2,) or not np.isfinite(action).all():
                    raise ValueError('Controller returned invalid action; world not stepped')
                sensors = obs['sensors']
                angle = sensors['collision_angle']
                sensor_vector = np.array([float(sensors['collision']), 0. if angle is None else float(angle),
                                          *sensors['wind_direction']], dtype=np.float32)
                before_step = time.perf_counter()
                next_obs, reward, terminated, truncated, info = env.step(action)
                step_latency = time.perf_counter() - before_step
                next_pose = np.array([*env._base_xy(), env._base_yaw()], dtype=np.float64)
                contacts += int(bool(sensors['collision']))
                path_length += float(np.linalg.norm(next_pose[:2] - pose[:2]))
                reward_total += reward
                writer.tick(episode, tick, cam_left=obs['cam_left'], cam_right=obs['cam_right'],
                            sensors=sensor_vector, action=action, control=env.data.ctrl.copy(),
                            pose=pose, next_pose=next_pose, reward=np.array(reward),
                            simulation_time=np.array(env.data.time), latency=np.array(latency),
                            step_latency=np.array(step_latency), **neural)
                all_latency.append(latency)
                all_step_latency.append(step_latency)
                obs = next_obs
                ending = outcome(terminated, truncated, info, env.goal_radius)
                if ending:
                    reason = ending
                    break
            summary = {'episode': episode, 'seed': seed, 'steps': tick + 1, 'outcome': reason,
                       'reward': reward_total, 'contact_ticks': contacts, 'path_length': path_length,
                       'final_distance': float(info['dist_to_goal'])}
            summaries.append(summary)
            writer.event('episode_finished', **summary)
        writer.flush()
        elapsed = time.perf_counter() - rollout_started
        metrics = {'load_seconds': load_seconds, 'rollout_seconds': elapsed,
                   'control_interval_seconds': dt, 'real_time_factor': len(all_latency) * dt / elapsed,
                   'timing_scope': 'rollout includes numeric chunk publication; excludes final summary manifest and teardown',
                   'controller_latency_ms': {name: float(np.percentile(all_latency, q) * 1000)
                                             for name, q in [('p50', 50), ('p95', 95), ('p99', 99)]},
                   'step_with_cameras_ms_p95': float(np.percentile(all_step_latency, 95) * 1000),
                   'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                   'cuda_peak_allocated_bytes': torch.cuda.max_memory_allocated() if torch.cuda.is_initialized() else 0,
                   'parity_ticks': parity_ticks, 'episodes': summaries}
        writer.finish({'metrics': metrics})
        return 0
    except Exception as error:
        import traceback
        traceback.print_exc()
        failure = {'type': type(error).__name__, 'message': str(error),
                   'policy_diagnostics': getattr(policy, 'failure_diagnostics', None)}
        try:
            writer.event('runtime_failure', **failure)
            writer.finish({'error': failure}, status='failed')
        except (OSError, ValueError, RuntimeError):
            # The supervisor's failure and stderr remain authoritative if the recorder cannot write.
            traceback.print_exc()
        return 1
    finally:
        if env is not None:
            env.renderer.close()
            env.close()
        writer.close()


if __name__ == '__main__':
    raise SystemExit(worker(json.loads(sys.argv[1])))
