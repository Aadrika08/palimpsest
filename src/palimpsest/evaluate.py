"""Isolate the upstream runtime and retain bounded, explicitly labelled evidence."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def _json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def bounded_process(command, output, timeout, env=None):
    """One isolated process group; timeout includes model loading and renderer stalls."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'status': 'running', 'timeout_seconds': timeout,
              'started_utc': datetime.now(timezone.utc).isoformat(), 'output': str(output)}
    _json(output / 'supervisor.json', report)
    started, process = time.perf_counter(), None
    try:
        with (output / 'stdout.log').open('w') as stdout, (output / 'stderr.log').open('w') as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=env,
                                       start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
                report['status'] = 'completed' if code == 0 else 'failed'
            except subprocess.TimeoutExpired:
                report['status'] = 'timeout'
            except KeyboardInterrupt:
                report['status'] = 'interrupted'
    except OSError as error:
        report.update(status='failed', error=str(error))
    finally:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=3)
        report.update(returncode=process.returncode if process else None,
                      elapsed_seconds=time.perf_counter() - started)
        _json(output / 'supervisor.json', report)
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
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = (args.output or repo_root / 'runs' / f'{stamp}-{args.controller}').resolve()
    config = {key: getattr(args, key) for key in
              ('controller', 'device', 'episodes', 'max_steps', 'seed', 'parity', 'max_bytes', 'threads')}
    config.update(repo_root=str(repo_root), asset_root=str(asset_root), output=str(output))
    env = os.environ.copy()
    env.setdefault('MUJOCO_GL', 'egl')
    env['OMP_NUM_THREADS'] = str(args.threads)
    env['MPLBACKEND'] = 'Agg'
    report = bounded_process([sys.executable, '-m', 'palimpsest.evaluate', json.dumps(config)],
                             output, args.timeout, env)
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
    _json(output / 'supervisor.json', report)
    return report


def worker(config):
    # Imports stay inside the bounded child, after renderer/thread environment setup.
    from .records import RunWriter
    from .assets import load_manifest, prepare_graph, sha256_file, verify_assets
    from .doctor import diagnose

    root, assets, output = (Path(config[key]) for key in ('repo_root', 'asset_root', 'output'))
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
    }, max_bytes=config['max_bytes'])
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
