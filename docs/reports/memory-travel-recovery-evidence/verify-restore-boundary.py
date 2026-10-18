"""Read-only verification of retained restore evidence; never execute policy."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from scripts import memory_decision_pilot as p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    args = parser.parse_args()
    evidence = Path(__file__).resolve().parent
    root = args.root or Path(p.read_json(evidence/'registration.json')['output'])
    deadline = time.monotonic()+120  # Offline verification, no new qualification.
    original = p.read_json(root/'restore-boundary.json')
    repeats = [r for r in p.read_json(root/'prerequisites/report.json')['attempted']
               if r['job_id'] in ('restore-1', 'restore-2')]
    if len(repeats) != 2:
        raise ValueError('Missing restore pair')
    data = [p.read_raw(r['run'], deadline) for r in repeats]
    jobs = [p.read_json(root/'prerequisites/jobs'/(r['run_id']+'.json')) for r in repeats]
    workers = [p.read_json(Path(r['run'])/'worker-report.json') for r in repeats]
    if any(len(d['rows']) != 5 for d in data):
        raise ValueError('Restore must have five recorded controls')
    unequal, timing = [], []
    for one, two in zip(data[0]['rows'], data[1]['rows']):
        if one.keys() != two.keys():
            raise ValueError('Restore raw fields differ')
        for key in sorted(one):
            if not np.array_equal(one[key], two[key]):
                (timing if key in ('latency', 'step_latency') else unequal).append(
                    {'tick': int(one['tick']), 'field': key})
    differences = []
    def walk(one, two, path):
        if type(one) != type(two):
            differences.append(path)
        elif isinstance(one, dict):
            if one.keys() != two.keys():
                differences.append(path+'.keys')
            else:
                for key in one:
                    walk(one[key], two[key], path+'.'+key)
        elif isinstance(one, list):
            if len(one) != len(two):
                differences.append(path+'.length')
            else:
                for index, (a, b) in enumerate(zip(one, two)):
                    walk(a, b, path+f'[{index}]')
        elif one != two:
            differences.append(path)
    for key in ('final_memory', 'world_state'):
        walk(workers[0][key], workers[1][key], key)
    measured = {
        'five_ticks': [int(r['tick']) for r in data[0]['rows']],
        'raw_fields_compared': sorted(data[0]['rows'][0]),
        'non_timing_raw_fields_differ': unequal, 'timing_measurement_differences': timing,
        'retained_final_memory_world_differences': differences,
        'same_source_snapshot': all(all(j[k] == jobs[0][k] for k in
            ('snapshot_path', 'snapshot_sha256', 'expected_invariant')) for j in jobs),
        'initial_invariants_preserved': all(r['invariants_preserved'] is True for r in repeats),
        'trace_digest_matches': repeats[0]['trace_digest'] == repeats[1]['trace_digest'],
        'post_state_digest_matches': repeats[0]['post_state_digest'] == repeats[1]['post_state_digest'],
        'post_state_digests': [r['post_state_digest'] for r in repeats]}
    if any(original[key] != value for key, value in measured.items()):
        raise ValueError('Retained boundary receipt differs from raw/worker evidence')
    p.deadline_check(deadline)
    print(json.dumps({'retained_restore_boundary_verified': True,
        'native_owners_started': 0, 'post_state_digest_matches': measured['post_state_digest_matches'],
        'trace_digest_matches': measured['trace_digest_matches'], 'qualification_claims': []}, indent=2))


if __name__ == '__main__':
    main()
