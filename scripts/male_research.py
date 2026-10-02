"""Frozen M7 v2 manifest publication and locked recorded-held-out evaluation.

This CLI is research-only. It cannot replace production model pins or select a
winning seed. Execute actual inference only in an assigned bounded runtime slot.
"""
import argparse
from pathlib import Path
import time

from palimpsest import artifacts, male_research as research
from palimpsest.male_model import check_sources, prepare_splits
from palimpsest.male_policy import load_policy
from palimpsest.storage import StorageBudget, StorageLimits


def disjoint_heldout(collection, manifest):
    """Check retained train/dev arrays' hashes without opening their recordings."""
    ids, payloads = set(), set()
    for pair in manifest['pairs']:
        directory = manifest['_directory'] / pair['directory']
        protocol = artifacts._json(artifacts._read(directory / 'protocol.json', 8 * 1024**2))
        for rows in protocol['collection']['splits'].values():
            for row in rows:
                ids.add(row['run_id'])
                payloads.add(row['feature_target_sha256'])
    for row in collection['splits']['held_out']:
        if row['run_id'] in ids or row['feature_target_sha256'] in payloads:
            raise ValueError('held-out source duplicates a train/dev run or feature/target payload')


def evaluate_heldout(args):
    # Gate before reading held-out paths, making output, or importing Torch.
    receipt = research.require_unlock(args)
    root, assets = args.repo.resolve(), args.assets.resolve()
    output = artifacts._safe_path(args.output)
    frozen = research.protocol(root)
    budget = StorageBudget((output.parent,), StorageLimits(max_bytes=64 * 1024**2, min_free_bytes=frozen['min_free_bytes']))
    started = time.monotonic()
    deadline = started + frozen['evaluation_limits']['held_out_recorded_seconds']
    before = research.research_sources(root)
    rows = [{'training_seed': seed, 'controller': controller, 'status': 'not_started'}
            for seed in research.PAIR_SEEDS for controller in research.CONTROLLERS]
    report = {'status': 'running', 'research_protocol_sha256': research.PROTOCOL_SHA256, 'unlock': receipt,
              'models': rows, 'source_hashes': before, 'qualification_claims': [],
              'scope': 'one recorded-input evaluation of all six frozen checkpoints; no refitting or selection'}
    collection, active = None, None
    with budget.lock():
        budget.check(4 * 1024**2, path=output)
        output.mkdir(parents=True, exist_ok=False)
        try:
            data, collection = prepare_splits({'train': [], 'dev': [], 'held_out': args.held_out}, research_stage='held_out')
            report['collection'] = collection
            path, manifest = research._manifest(args.research_manifest, args.research_manifest_sha256)
            disjoint_heldout(collection, manifest | {'_directory': path.parent})
            from train_male_reduced import evaluate
            for row in rows:
                active = row
                row['status'] = 'running'
                if time.monotonic() > deadline:
                    raise TimeoutError('recorded held-out deadline exceeded')
                key = f"{row['training_seed']}:{row['controller']}"
                identity, arguments = research.resolve(root, assets, args.research_manifest, args.research_manifest_sha256,
                    row['training_seed'], row['controller'], receipt['identities'][key])
                policy = load_policy(**arguments, seed=row['training_seed'])
                row.update(identity=identity, metrics=evaluate(policy.agent, data['held_out'], deadline, research.training(row['training_seed'])),
                           status='completed')
                del policy
                active = None
            report['status'] = 'completed'
        except BaseException as error:
            report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:2048]})
            if active is not None:
                active.update(status='failed', error=report['error'])
        finally:
            report['finalization_errors'] = []
            def check(name, function):
                report[name] = False
                try:
                    if function() is False:
                        raise ValueError(name + ' failed')
                    report[name] = True
                except BaseException as error:
                    report['status'] = 'failed'
                    report['finalization_errors'].append({'check': name, 'type': type(error).__name__, 'message': str(error)[:2048]})
            check('sources_unchanged', lambda: research.research_sources(root) == before)
            check('recordings_unchanged', lambda: check_sources(collection) if collection is not None else False)
            check('models_unchanged', lambda: all(research.resolve(root, assets, args.research_manifest, args.research_manifest_sha256,
                int(key.split(':')[0]), key.split(':')[1])[0] == identity for key, identity in receipt['identities'].items()))
            check('within_deadline', lambda: time.monotonic() <= deadline)
            report['wall_seconds'] = time.monotonic() - started
            research.write_json(output / 'evaluation.json', report, budget)
    return 0 if report['status'] == 'completed' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('publish', 'held-out-recorded'))
    for name in ('repo', 'assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    research.add_arguments(parser, stages=('held_out',))
    parser.add_argument('--held-out', type=Path, action='append', default=[])
    args = parser.parse_args(argv)
    if args.stage == 'publish':
        budget = StorageBudget((args.output.parent,), StorageLimits(max_bytes=256 * 1024**2, min_free_bytes=1024**3))
        with budget.lock():
            budget.check(research.MAX_JSON, path=args.output)
            print(research.publish_manifest(args.repo, args.assets, args.output))
        return 0
    return evaluate_heldout(args)


if __name__ == '__main__':
    raise SystemExit(main())
