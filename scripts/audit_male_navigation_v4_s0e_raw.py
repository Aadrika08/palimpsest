"""S0e-A raw-audit worker: the v2 root raw-audit scope over the S0e output, with T-e port readers.

Run only by ``run_male_navigation_v4_s0e.py audit`` as ``python -I -B <this> <config json>``
with PALIMPSEST_M7_V4_PINS naming the S0e locator. ``sys.path`` holds only the verified T-e
port worktree (``src`` then ``scripts``); the port modules are imported read-only by name,
so this file itself is stdlib-only for the stage P probe. Per owner it runs:

* the shared source/label/initial/contact validators: the port's unchanged ``admit_record``;
* an independent contact-incidence reconstruction from the raw recording (every stage's
  pairs classified by the port's ``pair_type``, summed here, compared with the owner result
  and the collection report);
* finite-array, row, tick and event counts over every recorded array.

No native simulator or model is imported; the worker reports any MuJoCo/Torch module and
any local module loaded from outside the port worktree. One JSON line on stdout.
"""
import importlib
import json
from pathlib import Path
import sys

FORBIDDEN = ('mujoco', 'torch')


def rebuild(nav, records, np, run, ownership):
    """Independent incidence, finite-array and count pass over one raw recording."""
    geometry = nav.ownership_map(ownership)
    types = list(nav.TYPES)
    by_type = [[0]*11 for _ in types]; intervals = [[0]*11 for _ in types]; pairs = [0]*125
    nonfinite, ticks = [], 0
    for tick, raw in enumerate(records.iter_ticks(run/'recording')):
        for name, value in raw.items():
            array = np.asarray(value)
            if array.dtype.kind in 'fc' and not np.isfinite(array).all(): nonfinite.append(f'{tick}:{name}')
        counts, ids = np.asarray(raw['body_contact_counts']), np.asarray(raw['body_contact_ids'])
        classes, distances = np.asarray(raw['body_contact_classes']), np.asarray(raw['body_contact_distances'])
        for stage in range(11):
            seen = [0]*len(types)
            for j in range(int(counts[stage])):
                kind, pair = nav.pair_type(ids[stage, j], int(classes[stage, j]), distances[stage, j], geometry)
                seen[types.index(kind)] += 1
                if pair is not None: pairs[pair] += 1
            for i, n in enumerate(seen):
                by_type[i][stage] += n; intervals[i][stage] += int(n > 0)
        ticks += 1
    events = sum(1 for _ in (run/'recording'/'events.jsonl').open('rb'))
    incidence = {'scope': 'fully admitted prefix only', 'admitted_intervals': ticks, 'pair_instances_by_type_stage': by_type,
                 'intervals_by_type_stage': intervals, 'robot_world_pair_instances': pairs}
    return incidence, nonfinite, ticks, events


def main():
    config = json.loads(sys.argv[1])
    port, collection = Path(config['port_root']).resolve(), Path(config['collection'])
    sys.path[:0] = [str(port/'src'), str(port/'scripts')]
    np = importlib.import_module('numpy')
    nav = importlib.import_module('collect_male_navigation_v2')
    records = importlib.import_module('palimpsest.records')
    report = json.loads((collection/'report.json').read_bytes())
    owners, totals = [], {kind: 0 for kind in nav.TYPES}
    for case in nav.CASES:
        item, out = report['cases'][case['id']], {'case': case['id']}
        try:
            result = json.loads((collection/case['id']/'result.json').read_bytes())
            run = Path(item['run'])
            if not run.resolve().is_relative_to(collection.resolve()): raise ValueError('Owner run outside the collection')
            out['rows'] = len(result['rows'])
            try: out['admitted'] = nav.admit_record(run, result, report['identities_before'][str(case['learner_seed'])])
            except Exception as error: out['validator_error'] = f'{type(error).__name__}: {error}'[:512]
            incidence, nonfinite, ticks, events = rebuild(nav, records, np, run, result['contact_ownership'])
            out.update(ticks=ticks, events=events, nonfinite=nonfinite[:16], nonfinite_count=len(nonfinite),
                       incidence_matches_result=incidence == result.get('contact_incidence'),
                       incidence_matches_report=incidence == item.get('contact_incidence'))
            for kind, stages in zip(nav.TYPES, incidence['pair_instances_by_type_stage']): totals[kind] += sum(stages)
        except Exception as error:
            out['error'] = f'{type(error).__name__}: {error}'[:512]
        owners.append(out)
    loaded = {name: getattr(module, '__file__', None) for name, module in list(sys.modules.items())}
    own = Path(__file__).resolve()   # this worker, also aliased as __mp_main__
    outside = sorted(n for n, p in loaded.items() if p and Path(p).resolve() != own and (n.split('.')[0] == 'palimpsest' or Path(p).parent.name == 'scripts')
                     and not Path(p).resolve().is_relative_to(port))
    local = [n for n, p in loaded.items() if p and Path(p).resolve().is_relative_to(port)]
    print(json.dumps({'owners': owners, 'pair_instances_by_type': totals, 'cases': [c['id'] for c in nav.CASES],
                      'forbidden_modules': sorted(n for n in loaded if n.split('.')[0] in FORBIDDEN),
                      'local_modules_outside_port': outside, 'local_modules': len(local),
                      'reader_origin': str(Path(nav.__file__).resolve())}, sort_keys=True))


if __name__ == '__main__':
    main()
