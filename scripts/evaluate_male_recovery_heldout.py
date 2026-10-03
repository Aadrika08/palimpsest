"""Named fixed recovery held-out EVALUATION; no useful-navigation/R3 admission."""
import argparse
from pathlib import Path
import shutil
from types import SimpleNamespace

from palimpsest import artifacts, male_recovery_heldout as research


def run(args):
    if args.stage != 'recorded' and (args.collection is not None or args.collection_sha256 is not None):
        raise ValueError('Teacher report arguments belong only to the recorded stage')
    root, assets = args.repo.resolve(), args.assets.resolve()
    research.protocol(root)
    value = SimpleNamespace(**vars(args), research_stage='held_out',
        research_manifest=root / research.INDEX_PATH, research_manifest_sha256=research.INDEX_SHA256,
        protocol=root / research.PROTOCOL_PATH)
    value.repo, value.assets = root, assets
    # The exact passed development gate precedes held-out source reads or output creation.
    receipt = research.require_unlock(value)
    output = research.outside_sources(args.output, root)
    value.output = output
    if output.exists() or not output.parent.is_dir():
        raise ValueError('Fresh output in an existing separate stage parent required')
    if shutil.disk_usage(output.parent).free < research.protocol(root)['combined_disk_required_bytes']:
        raise ValueError('Combined collection/recorded/closed-loop reservations plus 1 GiB floor unavailable')
    if args.stage == 'collect':
        from collect_male_teachers import _collect
        return _collect(value, research)
    if args.stage == 'recorded':
        if args.collection is None:
            raise ValueError('Explicit completed held-out teacher report required')
        collection = artifacts._safe_path(args.collection).parent
        if output == collection or collection in output.parents or output in collection.parents:
            raise ValueError('Recorded evaluation output must be outside held-out source tree')
        value.held_out = research.heldout_paths(value, receipt)
        from male_research import _evaluate_heldout
        return _evaluate_heldout(value, research, research.disjoint_heldout, collection_report=args.collection)
    if args.stage == 'closed-loop':
        from evaluate_male_closed_loop import _evaluate
        return _evaluate(value, research)
    raise ValueError('Unknown named held-out evaluation stage')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('collect', 'recorded', 'closed-loop'))
    for key in ('repo', 'assets', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--collection', type=Path)
    parser.add_argument('--collection-sha256')
    return run(parser.parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())
