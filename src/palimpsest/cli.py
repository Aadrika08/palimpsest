"""Small stdlib command surface; simulation dependencies load only in the worker."""

import argparse
import json
from pathlib import Path
import sys


def _bounded_int(low, high):
    def parse(value):
        number = int(value)
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(f'must be between {low} and {high}')
        return number
    return parse


def main(argv=None):
    parser = argparse.ArgumentParser(prog='palimpsest')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--assets', type=Path, help='asset directory (default: REPO/data/assets/flynn)')
    commands = parser.add_subparsers(dest='command', required=True)
    doctor = commands.add_parser('doctor', help='inspect setup without downloads')
    doctor.add_argument('--probe-renderer', action='store_true')
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
    args = parser.parse_args(argv)
    root = args.repo.resolve()
    asset_root = (args.assets or root / 'data/assets/flynn').resolve()
    try:
        if args.command == 'doctor':
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
        else:
            from .evaluate import evaluate
            report = evaluate(root, asset_root, args)
            ok = report['status'] == 'completed'
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if ok else 1
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(json.dumps({'error': str(error), 'type': type(error).__name__}), file=sys.stderr)
        return 1
