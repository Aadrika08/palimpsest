"""Small stdlib command surface; simulation dependencies load only in the worker."""

import argparse
import json
import os
from pathlib import Path
import sys
import uuid


def _bounded_int(low, high):
    def parse(value):
        number = int(value)
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(f'must be between {low} and {high}')
        return number
    return parse


def _storage_flags(parser):
    group = parser.add_argument_group('managed storage', 'Limits apply to managed run/export roots, not the whole filesystem.')
    group.add_argument('--storage-max-bytes', type=_bounded_int(1024**2, 100 * 1024**3), default=20 * 1024**3, help='aggregate bytes under managed roots')
    group.add_argument('--min-free-bytes', type=_bounded_int(0, 100 * 1024**3), default=1024**3, help='free-space floor on destination filesystem')
    for name, default in (('runs', 1024), ('snapshots', 64), ('exports', 1024)):
        group.add_argument('--max-' + name, type=_bounded_int(1, 4096), default=default, help='per-run snapshot limit' if name == 'snapshots' else 'managed ' + name + ' count limit')
    group.add_argument('--log-max-bytes', type=_bounded_int(1024, 64 * 1024**2), default=1024**2, help='maximum bytes per child stdout/stderr log')


def _limits(args):
    from .storage import StorageLimits
    return StorageLimits(max_bytes=args.storage_max_bytes, min_free_bytes=args.min_free_bytes,
                         max_runs=args.max_runs, max_snapshots=args.max_snapshots, max_exports=args.max_exports)


def _managed_root(output, asset_root):
    root = output.parent.absolute()
    if root.resolve().is_relative_to(asset_root) or asset_root.is_relative_to(root.resolve()):
        raise ValueError('Model assets must be outside managed storage roots')
    return root


def _run_count(root):
    count = 0
    for path in root.iterdir():
        if not path.is_dir():
            continue
        try:
            value = uuid.UUID(path.name)
            known = path.name in (value.hex, str(value))
        except ValueError:
            known = False
        count += bool(known or (path / 'recording/manifest.json').is_file())
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(prog='palimpsest')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--assets', type=Path, help='asset directory (default: REPO/data/assets/flynn)')
    commands = parser.add_subparsers(dest='command', required=True)
    doctor = commands.add_parser('doctor', help='inspect setup without downloads')
    doctor.add_argument('--probe-renderer', action='store_true')
    memory_fit = commands.add_parser('memory-fit', help='fit bounded revision rules from retained historical observations')
    memory_fit.add_argument('history', type=Path, help='E JSON file; emits the U artifact as JSON')
    assets = commands.add_parser('assets', help='verify, explicitly download, or extract pinned assets')
    assets.add_argument('operation', choices=('verify', 'fetch', 'prepare'))
    evaluate = commands.add_parser('evaluate', help='bounded teacher or FLYNN evaluation')
    evaluate.add_argument('--controller', choices=('teacher', 'flynn'), required=True)
    evaluate.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    evaluate.add_argument('--episodes', type=_bounded_int(1, 1000), default=1)
    evaluate.add_argument('--max-steps', type=_bounded_int(1, 600), default=600)
    evaluate.add_argument('--seed', type=_bounded_int(0, 2**31 - 1000), default=0)
    evaluate.add_argument('--timeout', type=_bounded_int(1, 86400), default=900, help='wall seconds including loading')
    evaluate.add_argument('--max-bytes', type=_bounded_int(1024**2, 100 * 1024**3), default=2 * 1024**3)
    evaluate.add_argument('--threads', type=_bounded_int(1, 16), default=2)
    evaluate.add_argument('--parity', action='store_true', help='compare every FLYNN tick with upstream preprocessing')
    evaluate.add_argument('--output', type=Path, help='new run directory; never overwritten')
    lab = commands.add_parser('lab', help='launch the local interactive lab')
    lab.add_argument('--port', type=_bounded_int(1, 65535), default=8765)
    lab.add_argument('--runs', type=Path, help='registered run root (default: REPO/runs/lab)')
    lab.add_argument('--exports', type=Path, help='export root (default: REPO/exports)')
    lab.add_argument('--headless-continue', action='store_true', help='explicitly continue when the browser disconnects')
    replay = commands.add_parser('replay', help='recorded playback or bounded action/policy replay')
    replay.add_argument('source', type=Path)
    replay.add_argument('--mode', choices=('playback', 'actions', 'policy'), required=True)
    replay.add_argument('--episode', type=_bounded_int(0, 100000), default=0)
    replay.add_argument('--tick', type=_bounded_int(0, 599), default=0)
    replay.add_argument('--timeout', type=_bounded_int(1, 86400), default=900)
    replay.add_argument('--output', type=Path, help='new UUID-named run directory; parent is managed root (actions/policy only)')
    compare = commands.add_parser('compare', help='compare completed runs and provenance')
    compare.add_argument('left', type=Path)
    compare.add_argument('right', type=Path)
    compare.add_argument('--output', type=Path, help='optional new standalone HTML comparison; default prints recorded JSON')
    export = commands.add_parser('export', help='export a completed run without inference')
    export.add_argument('source', type=Path)
    export.add_argument('--format', choices=('svg', 'png', 'bundle'), required=True)
    export.add_argument('--output', type=Path, required=True, help='new artifact path; never overwritten; parent directory is managed storage root')
    sonify = commands.add_parser('sonify', help='compose an offline WAV from recorded neural population means')
    sonify.add_argument('source', type=Path)
    sonify.add_argument('--population', choices=('visual_left', 'visual_right', 'descending'), action='append', required=True)
    sonify.add_argument('--episode', type=_bounded_int(0, 100000), default=0)
    sonify.add_argument('--output', type=Path, required=True, help='new WAV path with embedded provenance; never overwritten')
    for command in (lab, evaluate, replay, export, sonify, compare):
        _storage_flags(command)
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    asset_root = (args.assets or root / 'data/assets/flynn').resolve()
    try:
        if args.command == 'memory-fit':
            from .memory import MAX_STATE_BYTES, fit
            with args.history.open('rb') as source:
                history = source.read(MAX_STATE_BYTES + 1)
            if len(history) > MAX_STATE_BYTES:
                raise ValueError('Memory history exceeds 4 MiB')
            report, ok = fit(json.loads(history)), True
        elif args.command == 'doctor':
            from .doctor import diagnose
            report = diagnose(root, asset_root, args.probe_renderer)
            ok = report['ready']
        elif args.command == 'assets':
            from .assets import fetch_assets, prepare_graph, verify_assets
            if args.operation == 'prepare':
                report = {'ok': True, 'edge_path': str(prepare_graph(root, asset_root))}
            else:
                report = (fetch_assets if args.operation == 'fetch' else verify_assets)(root, asset_root)
            ok = report['ok']
        elif args.command == 'evaluate':
            from .evaluate import evaluate
            report = evaluate(root, asset_root, args)
            ok = report['status'] == 'completed'
        elif args.command == 'lab':
            from .lab import create_app
            import uvicorn
            if not (root / 'ui/dist/index.html').is_file():
                raise ValueError('Build the UI first: cd ui && npm ci && npm run build')
            app = create_app(root, asset_root, (args.runs or root / 'runs/lab').resolve(),
                             (args.exports or root / 'exports').resolve(), port=args.port,
                             headless_continue=args.headless_continue, storage_limits=_limits(args),
                             log_max_bytes=args.log_max_bytes)
            uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False, ws_max_size=16384)
            return 0
        elif args.command == 'compare' and args.output is None:
            from .artifacts import compare_runs
            report, ok = compare_runs(args.left, args.right), True
        elif args.command in {'export', 'sonify', 'compare'}:
            from .artifacts import export_run
            from .storage import StorageBudget
            output = args.output.absolute()
            managed = _managed_root(output, asset_root)
            budget = StorageBudget((managed,), _limits(args))
            with budget.lock():
                budget.check(0, path=output)
                count = sum(path.is_file() and path.suffix.lower() in {'.svg', '.png', '.zip', '.wav', '.html'} for path in managed.rglob('*'))
                budget.check_count('exports', count)
                if args.command == 'compare':
                    from .comparison import export_comparison
                    result = export_comparison(args.left, args.right, output, storage_budget=budget)
                elif args.command == 'sonify':
                    from .sonification import sonify
                    result = sonify(args.source, output, populations=args.population, episode=args.episode, storage_budget=budget)
                else:
                    result = export_run(args.source, output, args.format, storage_budget=budget)
                report = {'artifact': str(result)}
            ok = True
        elif args.mode == 'playback':
            from .artifacts import playback
            if args.output:
                raise ValueError('Playback emits recorded JSON; --output is for action/policy replay')
            report, ok = playback(args.source, args.episode, args.tick), True
        else:
            from .evaluate import bounded_process
            output = (args.output or root / 'runs/lab' / uuid.uuid4().hex).absolute()
            if uuid.UUID(output.name).hex != output.name:
                raise ValueError('Replay output directory must have a canonical hexadecimal UUID name')
            from dataclasses import asdict
            from .storage import StorageBudget
            managed = _managed_root(output, asset_root)
            budget = StorageBudget((managed,), _limits(args), headroom_bytes=2 * args.log_max_bytes + 8 * 1024**2)
            config = dict(source_run_path=str(args.source.resolve()), destination_run_path=str(output),
                          mode=args.mode, repo_root=str(root), asset_root=str(asset_root),
                          storage={'roots': [str(managed)], 'limits': asdict(budget.limits),
                                   'headroom_bytes': budget.headroom_bytes})
            env = os.environ.copy()
            env.setdefault('MUJOCO_GL', 'egl')
            env.update(OMP_NUM_THREADS='2', MPLBACKEND='Agg')
            with budget.lock():
                budget.check(1024**2, path=output)
                budget.check_count('runs', _run_count(managed))
                report = bounded_process([sys.executable, '-m', 'palimpsest.replay', json.dumps(config)],
                                         output, args.timeout, env, storage_budget=budget, log_max_bytes=args.log_max_bytes)
            result = output / 'replay-report.json'
            if result.is_file():
                report['replay'] = json.loads(result.read_text())
            ok = report['status'] == 'completed' and report.get('replay', {}).get('status') == 'passed'
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if ok else 1
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(json.dumps({'error': str(error), 'type': type(error).__name__}), file=sys.stderr)
        return 1
