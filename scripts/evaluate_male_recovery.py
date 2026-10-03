"""Named fixed recovery-research development evaluation; held-out remains locked.

Reuses the original 24-owner v2 evaluator with an explicit trusted binding. This
entrypoint cannot change checkpoints, scene seeds, profiles, or fit parameters.
"""
import argparse
from pathlib import Path
import time
from types import SimpleNamespace

from evaluate_male_closed_loop import evaluate_recovery
from palimpsest import artifacts, male_recovery_research as research, male_research
from palimpsest.storage import StorageBudget, StorageLimits


def run(args):
    root, assets, output = args.repo.resolve(), args.assets.resolve(), artifacts._safe_path(args.output)
    index = research._index(root, root / research.INDEX_PATH, research.INDEX_SHA256)
    producer, _, _ = research._gate(root, index)
    if output == producer or producer in output.parents or output in producer.parents:
        raise ValueError('Development output must be outside the frozen training/data producer tree')
    # The evaluator owns the only lifetime lease and preserves every natural outcome.
    started = time.monotonic()
    value = SimpleNamespace(repo=root, assets=assets, output=output, research_stage='dev',
        research_manifest=root / research.INDEX_PATH, research_manifest_sha256=research.INDEX_SHA256)
    result = evaluate_recovery(value)
    report = artifacts._json(artifacts._read(output / 'evaluation.json', research.MAX_JSON))
    receipt = {'status': 'failed-development', 'research_protocol_sha256': research.PROTOCOL_SHA256,
        'research_manifest_sha256': research.INDEX_SHA256, 'evaluation_sha256': male_research.sha(
            artifacts._read(output / 'evaluation.json', research.MAX_JSON)), 'qualification_claims': [],
        'scope': 'fixed six executed-target candidates on four development scenes; no held-out admission or promotion'}
    try:
        if result != 0:
            raise ValueError('Development owner/infrastructure evaluation failed')
        identities = {f'{seed}:{controller}': research.resolve(root, assets, root / research.INDEX_PATH,
            research.INDEX_SHA256, seed, controller)[0] for seed in research.PAIR_SEEDS for controller in research.CONTROLLERS}
        receipt['goals_per_original_seed'] = research.passed_development(report, research.INDEX_SHA256, identities)
        receipt['status'] = 'passed-development'
    except Exception as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)[:1024]}
    frozen = research.protocol(root)
    budget = StorageBudget((output,), StorageLimits(max_bytes=frozen['evaluation_limits']['dev_bytes'], min_free_bytes=1024**3))
    with budget.lock():
        if time.monotonic() - started > frozen['evaluation_limits']['dev_seconds']:
            receipt.update(status='failed-development', error={'type': 'TimeoutError', 'message': 'Development publication deadline exceeded'})
        male_research.write_json(output / 'development.json', receipt, budget)
    # Final sync/lease release cannot produce a late successful process exit.
    return 0 if receipt['status'] == 'passed-development' and time.monotonic() - started <= frozen['evaluation_limits']['dev_seconds'] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    return run(parser.parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())
