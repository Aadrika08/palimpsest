"""Describe pinned development readouts; raw audits and held-out qualification stay separate."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_memory_counterbalance_comparison as verifier


def require(ok, message):
    if not ok:
        raise ValueError(message)


def boundary(value):
    require(value is None or type(value) is int and 300 <= value <= 600,
            'Timing must be a recorded boundary or null')
    return value


def difference(own, reference, *, applicable=True):
    """No substituted deadline and no unpaired timing average."""
    own, reference = boundary(own), boundary(reference)
    missing = ('both' if own is None and reference is None else
               'own' if own is None else 'reference' if reference is None else None)
    return {'own': own, 'reference': reference,
            'own_minus_reference': own-reference if applicable and missing is None else None,
            'missing': missing if applicable else 'not-applicable'}


def conditions(rows):
    require(type(rows) is list and len(rows) == 9, 'Exactly nine condition readouts required')
    require([r['condition'] for r in rows] == list(verifier.common.CONDITIONS),
            'Condition order/identity differs')
    return {r['condition']: r for r in rows}


def summarize(reports):
    require(1 <= len(reports) <= 12, 'Supply one to twelve fixed development reports')
    seen, profiles, cells, pairs = set(), set(), [], []
    for report in reports:
        digest = report.get('protocol_sha256')
        fixed, protocol = verifier.fixed_profile(digest)
        require(digest is not None and digest not in profiles, 'Missing or duplicate profile')
        profiles.add(digest)
        require(report.get('status') == 'comparison_checked' and
                report.get('claim') == protocol['claim'] and
                report.get('source_unchanged') is True and report.get('retained_unchanged') is True and
                type(report.get('source_identity')) is dict and bool(report['source_identity']) and
                report.get('source_identity') == report.get('final_source_identity') and
                report.get('unattempted_stages') == [] and 'first_failure' not in report and
                report.get('held_out_executed') is False and report.get('r2_complete') is False,
                'Only completed, unchanged development reports are admitted')
        expected = [verifier.admission.cell_key(c) for c in fixed]
        require([c['cell'] for c in report['comparisons']] == expected, 'Fixed cells/order differ')
        require(len(report['runs']) == 40 and all(r['mechanism_pass'] is True for r in report['runs']) and
                {(r['cell'], r['stage']) for r in report['runs']} ==
                {(cell, stage) for cell in expected for stage in verifier.STAGES} and
                len({r['run_id'] for r in report['runs']}) == 40,
                'All forty owners must pass their mechanism checks')
        strict = verifier.strict_profile(digest)
        contract = 'strict-core' if strict else 'historical-broader-core'
        for parameters, cell in zip(fixed, report['comparisons'], strict=True):
            key = cell['cell']
            require(key not in seen, 'Duplicate development cell')
            seen.add(key)
            seed, regime, kind = parameters
            case = verifier.admission.experiment.validate_world_case(report['bindings'][key]['case'])
            require(case == verifier.admission.make_case(parameters), 'Case differs from fixed profile')
            gold = cell['gold_target_ids']
            fact_ids = {f['id'] for f in case['facts']}
            expected_gold = [f['id'] for f in case['facts']
                             if kind == 'change' and f['subject_id'] == case['closure_subject_id']]
            require(type(gold) is list and gold == expected_gold,
                    'Change/null gold differs')
            side = ('lower' if case['closure_subject_id'] == case['subjects_by_side'][0] else 'upper') if gold else None
            runtime, targeting = conditions(cell['runtime']), conditions(cell['targeting'])
            description = {'cell': key, 'seed_block': seed, 'regime': regime, 'kind': kind,
                           'closure_side': side, 'core_contract': contract, 'conditions': []}
            for condition, row in runtime.items():
                require(type(row['task_pass']) is bool and type(row['navigation_pass']) is bool,
                        'Evaluator task/navigation flags must be Boolean')
                goal = boundary(row['goal_tick'])
                require((goal is not None) == row['navigation_pass'] == ((row['outcome'] or {}).get('reason') == 'goal'),
                        'Goal timing and outcome disagree')
                timing = row['timing']
                require(len(timing) == 2 and {t['fact_id'] for t in timing} == fact_ids,
                        'Both fact timings required')
                for value in timing:
                    changed = value['fact_id'] in gold
                    require(value['stale_value_changed'] is changed, 'Stale correction identity differs')
                    correction = boundary(value['first_stale_value_correction_tick'])
                    confirmation = boundary(value['first_confirmation_tick'])
                    require((correction is None if not changed else confirmation is None),
                            'A confirmation cannot be counted as a stale correction')
                targets = row['target_ids']
                require(type(targets) is list and len(targets) <= 1 and set(targets) <= fact_ids,
                        'Target identities/budget differ')
                target = targeting[condition]
                hits = len(set(targets) & set(gold))
                require(target['exact_set'] is (set(targets) == set(gold)) and
                        target['false_targets'] == len(set(targets)-set(gold)) and
                        target['missed_targets'] == len(set(gold)-set(targets)) and
                        target['selection']['target_ids'] == targets and
                        target['precision'] == (hits/len(targets) if targets else None) and
                        target['recall'] == (hits/len(gold) if gold else None),
                        'Targeting readout disagrees with actual targets/gold')
                if kind == 'no-event':
                    require(row['selector_invocations'] == row['selector_behavior_bytes'] == 0 and
                            not targets and all(row[k] == 0 for k in ('requested', 'started', 'resolved', 'timeouts')),
                            'No-event must retain absence of selector/inspection')
                description['conditions'].append({k: row[k] for k in
                    ('condition', 'task_pass', 'navigation_pass', 'goal_tick', 'outcome',
                     'selector_invocations', 'selector_behavior_bytes', 'target_ids', 'timing')})
                description['conditions'][-1].update({k: target[k] for k in
                    ('exact_set', 'false_targets', 'missed_targets', 'precision', 'recall')})
                if condition == 'own':
                    continue
                own = runtime['own']
                own_changed = next((t['first_stale_value_correction_tick'] for t in own['timing'] if t['fact_id'] in gold), None)
                other_changed = next((t['first_stale_value_correction_tick'] for t in timing if t['fact_id'] in gold), None)
                pairs.append({'cell': key, 'seed_block': seed, 'regime': regime, 'kind': kind,
                    'closure_side': side, 'core_contract': contract, 'reference': condition,
                    'pair_contract': 'strict-u-only' if strict and condition in verifier.CORE_CONDITIONS else 'declared-configuration-and-resources',
                    'task_pass_difference': int(own['task_pass'])-int(row['task_pass']),
                    'exact_target_difference': int(targeting['own']['exact_set'])-int(target['exact_set']),
                    'goal_boundary': difference(own['goal_tick'], goal),
                    'stale_correction_boundary': difference(own_changed, other_changed, applicable=bool(gold))})
            cells.append(description)
    matrix = {verifier.admission.cell_key((seed, regime, kind)) for seed in range(24, 32)
              for regime in verifier.memory.RELATIONS for kind in verifier.admission.experiment.KINDS}
    require(seen <= matrix, 'Only fixed development cells may be summarized')
    groups = defaultdict(list)
    for pair in pairs:
        groups[tuple(pair[k] for k in ('core_contract', 'regime', 'kind', 'closure_side', 'reference'))].append(pair)
    strata = []
    for key, values in groups.items():
        item = dict(zip(('core_contract', 'regime', 'kind', 'closure_side', 'reference'), key))
        item.update(cells=len(values), seed_blocks=sorted({r['seed_block'] for r in values}),
                    task_pass_difference_sum=sum(r['task_pass_difference'] for r in values),
                    exact_target_difference_sum=sum(r['exact_target_difference'] for r in values))
        for metric in ('goal_boundary', 'stale_correction_boundary'):
            measured = [r[metric]['own_minus_reference'] for r in values if r[metric]['own_minus_reference'] is not None]
            item[metric] = {'paired_observations': len(measured),
                'mean_own_minus_reference': sum(measured)/len(measured) if measured else None,
                'missing': dict(Counter(r[metric]['missing'] for r in values if r[metric]['missing'] is not None))}
        strata.append(item)
    return {'status': 'complete-development-readout' if seen == matrix else 'partial-development-readout',
        'completed_cells': len(cells), 'expected_cells': 48, 'missing_cells': sorted(matrix-seen),
        'seed_blocks': dict(sorted(Counter(c['seed_block'] for c in cells).items())),
        'profiles': sorted(profiles), 'cells': cells, 'paired_readouts': pairs, 'strata': strata,
        'held_out_executed': False, 'r2_complete': False, 'qualification_claims': [],
        'scope': 'Descriptive paired readouts from explicitly pinned reports; not a new raw audit or independent samples. '
                 'Eight shared seed namespaces; fixed lower-goal geometry. Historical C3 stays separate from strict-core forks. '
                 'Negative timing differences mean own is earlier, conditional on both observed. Null confirmations are not corrections. '
                 'No imputed deadlines, inferential confidence intervals, significance test, causal benefit or route-independent claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='append', nargs=2, metavar=('SHA256', 'PATH'), required=True)
    args = parser.parse_args()
    require(len(args.report) <= 12, 'At most twelve report inputs')
    reports = [verifier.pinned_json(Path(path), digest) for digest, path in args.report]
    result = summarize(reports)
    for digest, path in args.report:
        require(verifier.common._hash(Path(path)) == digest, 'Input changed during analysis')
    result['inputs'] = [{'path': str(Path(path).absolute()), 'sha256': digest} for digest, path in args.report]
    result['analyzer_sha256'] = verifier.common._hash(Path(__file__))
    require(not {'torch', 'mujoco'} & set(sys.modules), 'Analysis imported native/model runtime')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
