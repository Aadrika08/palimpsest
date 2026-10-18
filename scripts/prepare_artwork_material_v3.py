"""Prospective v3 controls; reuse the pinned v2 supervisor without retrying v2."""
from collections import Counter
import html
import json
from pathlib import Path
import re
import sys

import prepare_artwork_material_v2 as previous

PHASE = previous.h.ROOT / '.superpowers/sdd/artwork-material-v3'
REGISTRATION = previous.h.ROOT / 'docs/plans/artwork-material-v3-registration.json'
PLAN = previous.h.ROOT / 'docs/plans/artwork-material-v3.md'


def check_event_references(comparison, runs):
    """Check HTML descriptors against complete, validated relocated recordings."""
    previous.h.require(comparison['version'] == 2 and comparison['rendering']['version'] ==
                       'recorded-route-comparison-v2', 'comparison rendering version differs')
    original = previous.h.artifacts.compare_runs(*runs)
    for side, run in zip(('left', 'right'), runs):
        data = previous.h.artifacts._load(run)
        source = comparison['comparison'][side]
        previous.h.require(all(source.get(key) == value for key, value in original[side].items()
                               if key != 'events'), 'comparison source fields differ')
        previous.h.require(comparison['projection'] == previous.h.artifacts._export_metadata(data)['projection'],
                           'comparison source projection differs')
        events = [event for event in data['events'] if event['kind'] in previous.h.artifacts._VISIBLE_EVENTS]
        expected = {'path': f"runs/{data['manifest']['run_id']}/recording/events.jsonl",
                    **previous.digest(Path(run) / 'recording/events.jsonl'),
                    'total_event_count': len(data['events']), 'visible_event_count': len(events),
                    'visible_kind_counts': dict(sorted(Counter(event['kind'] for event in events).items())),
                    'payloads_embedded': False}
        previous.h.require('events' not in source and source['event_stream'] == expected,
                           'comparison raw event reference differs')


_relocate = previous.relocate
_package = previous.check_and_package


def relocate(registration, start):
    # Copy this prospective plan under the same budget and original clock.
    with previous.BUDGET.lock():
        previous.BUDGET.check(PLAN.stat().st_size, path=PHASE / PLAN.name)
        with (PHASE / PLAN.name).open('xb') as output:
            output.write(PLAN.read_bytes())
    previous.check_clock(start)
    return _relocate(registration, start)


def check_and_package(result):
    raw = (PHASE / 'artifacts/one-map-many-lives.html').read_text()
    match = re.search(r'<pre id="comparison-metadata">([^<]*)</pre>', raw)
    previous.h.require(match is not None, 'comparison metadata missing')
    comparison = json.loads(html.unescape(match[1]))
    check_event_references(comparison, [PHASE / 'inputs/runs' / run for run in previous.IDS])
    _package(result)
    # The reused packager writes its historical basename inside the new root.
    # Rename without a second pack/export; the inherited readback already checked it.
    old = PHASE / 'palimpsest-artwork-review-development-v2.zip'
    new = PHASE / 'palimpsest-artwork-review-development-v3.zip'
    previous.h.require(not new.exists(), 'review ZIP destination exists')
    old.rename(new)
    previous.h.require(previous.digest(new) == result['review_zip'], 'renamed review ZIP differs')
    result['review_zip_name'] = new.name


def configure():
    previous.PHASE, previous.REGISTRATION = PHASE, REGISTRATION
    previous.BUDGET = previous.h.StorageBudget((PHASE,), previous.h.StorageLimits(
        max_bytes=2 * 1024**3, min_free_bytes=2 * 1024**3, max_exports=3), headroom_bytes=1024**2)
    # The inherited dispatcher copies and launches this v3 entrypoint. The v2
    # implementation and its historical plan are separately pinned unchanged.
    previous.__file__ = __file__
    previous.relocate, previous.check_and_package = relocate, check_and_package


if __name__ == '__main__':
    configure()
    raise SystemExit(previous.self_check() if sys.argv[1:] == ['--self-check'] else
                     previous.export_child(int(sys.argv[2])) if len(sys.argv) == 3 and sys.argv[1] == '--export' else previous.main())
