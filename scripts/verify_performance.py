"""Measure sustained actual owner execution; browser paint performance is separate."""

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import signal
import time
import uuid

from palimpsest.lab import LabSupervisor
from palimpsest.records import iter_ticks
from verify_endurance import source_identity, summary, write_json


def host_observation():
    value = {'thread_environment': {key: os.environ.get(key) for key in
                                   ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
             'scope': 'verifier process environment, affinity and host load at sample time',
             'cpu_affinity': None, 'load_average_1_5_15_minutes': None}
    try:
        value['cpu_affinity'] = sorted(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        pass
    try:
        value['load_average_1_5_15_minutes'] = list(os.getloadavg())
    except (AttributeError, OSError):
        pass
    return value


def measure(args):
    output, root = args.output.resolve(), args.repo.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'version': 1, 'status': 'running', 'requested_ticks_per_controller': args.ticks,
              'minimum_ticks_per_controller': args.ticks,
              'completion_protocol': 'natural-episode-completion-after-minimum-ticks' if getattr(args, 'finish_episode', False)
                                     else 'operator-pause-at-minimum-ticks-unless-current-episode-already-terminal',
              'scope': 'actual spawned owner, CPU manual/teacher, sparse-navigation/checker, EGL',
              'limitations': ['No browser paint/FPS claim', 'Only this measured host and software regime'],
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'controllers': {},
              'pre_close_observations': {}, 'host_at_start': host_observation()}
    write_json(output / 'report.json', report)
    supervisor = None
    interrupted = []
    previous = {sig: signal.signal(sig, lambda value, frame: interrupted.append(value)) for sig in (signal.SIGINT, signal.SIGTERM)}
    started, deadline = time.monotonic(), time.monotonic() + args.timeout

    def view(identifier):
        if interrupted:
            raise InterruptedError(f'Interrupted by signal {interrupted[0]}')
        if time.monotonic() >= deadline:
            raise TimeoutError('Performance gate deadline exceeded')
        value = supervisor.describe(identifier)
        if value['status'] == 'failed':
            raise RuntimeError(str(value.get('failure')))
        return value

    def wait(identifier, predicate):
        while True:
            value = view(identifier)
            if predicate(value):
                return value
            time.sleep(.01)

    def command(identifier, kind, payload=None, allow_terminal_rejection=False):
        state = view(identifier)['state']
        identifier_command = uuid.uuid4().hex
        supervisor.call(identifier, 'command', {'id': identifier_command, 'kind': kind, 'payload': payload or {},
            'expected_state': state['phase'], 'expected_episode': state['episode'], 'expected_revision': state['revision']})
        value = wait(identifier, lambda v: any(r['id'] == identifier_command and r['status'] != 'queued' for r in v['receipts']))
        receipt = next(r for r in value['receipts'] if r['id'] == identifier_command)
        if receipt['status'] != 'applied' and not (allow_terminal_rejection and receipt['status'] == 'rejected'
                                                   and value['state']['phase'] in {'terminated', 'truncated'}):
            raise RuntimeError(str(receipt))
        return value

    try:
        report['runtime_source'] = source_identity(root)
        supervisor = LabSupervisor(root, args.assets.resolve(), output / 'runs')
        for controller in args.controllers:
            identifier = supervisor.start({'controller': controller, 'device': 'cpu', 'seed': args.seed,
                                          'scenario': 'sparse-navigation', 'texture': 'checker'})
            initial = wait(identifier, lambda v: v['status'] == 'ready' and v['sample'] is not None)
            if initial['state']['total_tick'] != 0:
                raise RuntimeError('Owner advanced before the initial paused boundary')
            load_wall = time.monotonic() - started if not report['controllers'] else time.monotonic() - load_started
            active_started = time.monotonic()
            command(identifier, 'run')
            outcomes, samples, last_sample = [], 0, None
            while True:
                current = view(identifier)
                state, sample = current['state'], current['sample']
                marker = sample['wall_elapsed'] if sample else None
                if marker is not None and marker != last_sample:
                    last_sample, samples = marker, samples + 1
                if state['phase'] in {'terminated', 'truncated'}:
                    outcomes.append({'episode': state['episode'], 'episode_ticks': state['episode_step'],
                                     'phase': state['phase'], 'outcome': state['last_outcome']})
                    if state['total_tick'] >= args.ticks:
                        break
                    command(identifier, 'reset', {'seed': args.seed + state['episode'] + 1})
                    command(identifier, 'run')
                elif state['total_tick'] >= args.ticks and not getattr(args, 'finish_episode', False):
                    command(identifier, 'pause', allow_terminal_rejection=True)
                    break
                time.sleep(.01)
            active_outer_wall = time.monotonic() - active_started
            final = view(identifier)
            final_ticks = final['state']['total_tick']
            final = wait(identifier, lambda v: v['sample']['state']['total_tick'] == final_ticks
                         and abs(v['sample']['performance']['advanced_simulation_seconds'] - final_ticks * .02) < 1e-8)
            performance = final['sample']['performance']
            report['pre_close_observations'][controller] = {'run_id': identifier, 'final_ticks': final_ticks,
                'final_phase': final['state']['phase'], 'worker_active': dict(performance),
                'outer_running_wall_seconds': active_outer_wall, 'qualification': 'unqualified',
                'scope': 'copied telemetry before teardown and recorded-tick integrity validation'}
            write_json(output / 'report.json', report)
            paused_tick = final['state']['total_tick']
            time.sleep(.1)
            if view(identifier)['state']['total_tick'] != paused_tick:
                raise RuntimeError('Paused or terminal owner continued advancing')
            closed = supervisor.close(identifier)
            if closed['status'] != 'closed':
                raise RuntimeError({'run_id': identifier, 'operation': 'close',
                                    'status': closed['status'], 'failure': closed.get('failure')})
            policy, step, episode_ticks = [], [], collections.defaultdict(list)
            for row in iter_ticks(supervisor.path(identifier) / 'recording'):
                episode, tick = int(row['episode']), int(row['tick'])
                if tick != len(episode_ticks[episode]):
                    raise RuntimeError('Recorded policy ticks are not contiguous')
                if abs(float(row['simulation_time']) - (tick + 1) * .02) > 1e-8:
                    raise RuntimeError('Configured control interval changed')
                episode_ticks[episode].append(tick)
                policy.append(float(row['latency']))
                step.append(float(row['step_latency']))
            if len(policy) != final_ticks or final_ticks < args.ticks:
                raise RuntimeError('Recorded ticks do not match authoritative advancement')
            simulated = final_ticks * .02
            report['controllers'][controller] = {'run_id': identifier, 'recorded_ticks': final_ticks,
                'loading_wall_seconds': load_wall, 'episodes': {str(key): len(value) for key, value in episode_ticks.items()},
                'episode_outcomes': outcomes, 'policy_seconds': summary(policy), 'step_with_cameras_seconds': summary(step),
                'worker_active': performance, 'active_rtf_at_least_one': performance['rtf'] >= 1.,
                'outer_running_wall_seconds': active_outer_wall, 'outer_rtf': simulated / active_outer_wall,
                'outer_scope': 'first run request to observed final pause/termination, includes inter-episode reset and polling',
                'kernel_rtf': simulated / (sum(policy) + sum(step)),
                'kernel_scope': 'recorded controller and physics/camera time; excludes IPC, logging and display',
                'unique_display_samples_observed': samples,
                'display_scope': 'copied transport samples observed by headless monitor; not browser frames'}
            write_json(output / 'report.json', report)
            load_started = time.monotonic()
        report['status'] = 'passed' if all(value['active_rtf_at_least_one'] for value in report['controllers'].values()) else 'failed'
    except Exception as error:
        report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)})
    finally:
        if supervisor is not None:
            try:
                supervisor.shutdown()
            except Exception as error:
                report.update(status='failed', cleanup_error={'type': type(error).__name__, 'message': str(error)})
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        report['wall_seconds'] = time.monotonic() - started
        report['host_at_end'] = host_observation()
        if 'runtime_source' in report:
            report['runtime_source_at_end'] = source_identity(root)
            report['runtime_source_unchanged'] = report['runtime_source_at_end'] == report['runtime_source']
            if not report['runtime_source_unchanged']:
                report['status'] = 'failed'
        write_json(output / 'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='exclusive new directory')
    parser.add_argument('--ticks', type=int, default=600)
    parser.add_argument('--finish-episode', action='store_true',
                        help='After the minimum ticks, finish the current episode naturally instead of requesting pause')
    parser.add_argument('--timeout', type=float, default=300.)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--controllers', nargs='+', choices=('manual', 'teacher'), default=['manual', 'teacher'])
    args = parser.parse_args()
    if not 600 <= args.ticks <= 6000 or not 30 <= args.timeout <= 3600 or not 0 <= args.seed < 2**31 - 1000:
        parser.error('Require600–6000ticks,30–3600s timeout and a bounded seed')
    args.assets = args.assets or args.repo / 'data/assets/flynn'
    os.environ['MUJOCO_GL'] = 'egl'
    result = measure(args)
    print(json.dumps({'status': result['status'], 'controllers': result['controllers'], 'error': result.get('error')}, indent=2))
    raise SystemExit(0 if result['status'] == 'passed' else 1)
