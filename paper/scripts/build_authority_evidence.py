#!/usr/bin/env python3
"""Build paper evidence from a complete frozen campaign; never execute experiments."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from paper.studies.authority_replay_v1.analyze import summarize
from paper.studies.authority_replay_v1.common import load_protocol, parse_json, require, validate_finite
from paper.studies.authority_replay_v1.repeatability import _paired

EXECUTION_COMMITS_BY_PROTOCOL = {
    '7a985038bffa2f55ea2eeb6f75815c96ce179e0e5a74ee9e45db0aa1b1c03b35':
        'd8658dda3fca37bb43b6dafc909114279f706f11',
    '570a4afe8179425bb2b25b86364470af34052ecc4929b74f207c279076728860':
        'cc57edf9f70323926237d887d766627d8c9cdd42',
}
CONDITIONS = ('null', 'synchronous', 'background', 'background_storage')
FLAGS = ('silent_acceptance', 'explicit_detection', 'correct_recovery', 'benign_false_rejection')


def stats(values):
    if not values:
        return None
    q1, q3 = (values[0], values[0]) if len(values) == 1 else statistics.quantiles(values, n=4, method='inclusive')[::2]
    return dict(n=len(values), median=statistics.median(values), minimum=min(values), maximum=max(values), q1=q1, q3=q3, iqr=q3-q1)


def _truth(value):
    return type(value) is bool or (type(value) is str and value == 'unknown')


def _faults(rows):
    for row in rows:
        baseline = row.get('baseline_outcome')
        if baseline is not None:
            require(isinstance(baseline, dict) and type(baseline.get('accepted')) is bool, 'baseline accepted must be boolean')
            require(_truth(baseline.get('claim_truth')), 'baseline claim truth must be boolean or unknown')
            require('baseline_claim_truth' not in row or type(row['baseline_claim_truth']) is type(baseline['claim_truth'])
                    and row['baseline_claim_truth'] == baseline['claim_truth'], 'baseline claim truth drift')
            require('silent_acceptance' not in baseline or baseline['silent_acceptance'] is
                    (baseline['accepted'] and baseline['claim_truth'] is False), 'baseline silent acceptance drift')
        elif 'baseline_claim_truth' in row:
            require(_truth(row['baseline_claim_truth']), 'invalid orphan baseline truth')
    return dict(declared=len(rows), completed=sum(r['status'] == 'completed' for r in rows),
                baseline_reported=sum('baseline_outcome' in r for r in rows),
                baseline_known=sum(type(r.get('baseline_outcome', {}).get('claim_truth')) is bool for r in rows),
                baseline_unknown=sum(r.get('baseline_outcome', {}).get('claim_truth') == 'unknown' for r in rows),
                baseline_missing=sum('baseline_outcome' not in r for r in rows),
                baseline_true=sum(r.get('baseline_outcome', {}).get('claim_truth') is True for r in rows),
                baseline_false=sum(r.get('baseline_outcome', {}).get('claim_truth') is False for r in rows),
                baseline_accepted=sum(r.get('baseline_outcome', {}).get('accepted') is True for r in rows),
                baseline_false_accepts=sum(r.get('baseline_outcome', {}).get('accepted') is True and
                                          r['baseline_outcome']['claim_truth'] is False for r in rows),
                **{flag: sum(r.get(flag) is True for r in rows) for flag in FLAGS},
                reported={flag: sum(flag in r for r in rows) for flag in FLAGS},
                # Frozen outcome_scope defaults to production even for comparison diagnostics.
                production_detection=sum(r.get('explicit_detection') is True and r['case_id'] not in ('S1','B2','R1','R2') for r in rows),
                diagnostic_detection=sum(r.get('explicit_detection') is True and r['case_id'] in ('S1','B2') for r in rows),
                study_guard_detection=sum(r.get('explicit_detection') is True and r['case_id'] in ('R1','R2') for r in rows))


def _digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _replay_mode(raw, mode, source, ticks):
    require(isinstance(raw, dict) and raw.get('status') == 'passed'
            and raw.get('mode') == mode and raw.get('source_run_id') == source
            and type(raw.get('compared_ticks')) is int and raw['compared_ticks'] == ticks
            and raw.get('first_divergence') is None and raw.get('errors') == []
            and bool(raw.get('comparison'))
            and all(raw.get(k) is (mode == 'policy') for k in ('controller_reexecuted', 'inference_executed')),
            'replay raw source/mode/ticks/computation differs')


def _replay_source(row, protocol):
    report, meta = row.get('verifier_report', {}), row.get('source', {})
    source = report.get('source_run_id')
    require(isinstance(source, str) and bool(source) and meta == report.get('source')
            and type(meta.get('seed')) is int and meta['seed'] == row['seed']
            and meta.get('condition') == 'background_storage' and meta.get('recording_writer') == 'background'
            and meta.get('storage_accounting') is True
            and meta.get('prefix_ticks') == protocol.replay['prefix_ticks']
            and meta.get('source_ticks') == protocol.replay['source_ticks']
            and isinstance(meta.get('run_path'), str) and Path(meta['run_path']).name == source,
            'retained replay source metadata differs')
    snapshot = meta.get('snapshot_path')
    require(isinstance(snapshot, str) and snapshot == report.get('snapshot_path')
            and Path(snapshot).is_relative_to(Path(meta['run_path']) / 'snapshots')
            and _digest(row.get('source_manifest_sha256'))
            and _digest(report.get('snapshot_sha256'))
            and report['snapshot_sha256'] == row['metrics'].get('snapshot_sha256')
            and type(report.get('snapshot_bytes')) is int and report['snapshot_bytes'] > 0
            and report['snapshot_bytes'] == row['metrics'].get('snapshot_bytes'),
            'retained replay snapshot/manifest identity differs')
    return source


def _normalized_pairs(pairs):
    normalized = {}
    for mode, pair in pairs.items():
        fields = pair.get('validated_fields')
        if isinstance(fields, list):
            require(all(isinstance(name, str) and name for name in fields)
                    and len(fields) == len(set(fields)), 'duplicate or malformed validated field names')
            # The producer builds this list from a dict before sorted JSON publication.
            pair = dict(pair, validated_fields=sorted(fields))
        normalized[mode] = pair
    return normalized


def _repeat(rows, protocol, kind):
    passed = 0
    section = getattr(protocol, kind)
    for row in rows:
        agreement = row['metrics'].get('agreement')
        require(agreement is None or type(agreement) is bool, 'agreement must be boolean or null')
        if agreement is not True:
            continue
        report = row.get('verifier_report', {})
        require(row['status'] == 'completed' and row.get('first_divergence') is None
                and report.get('status') == 'passed' and report.get('finite_scientific_arrays') is True,
                'passing comparison lacks completed finite report')
        count = section['continuation_ticks'] if kind == 'continuation' else section['source_ticks'] - section['prefix_ticks']
        require(report.get('prefix_ticks') == section['prefix_ticks'] and report.get('continuation_ticks') == count,
                'comparison tick bounds differ')
        if kind == 'continuation':
            require(report.get('first_divergence') is None and bool(report.get('max_abs_errors'))
                    and all(report.get(k) is True for k in ('random_draws_match', 'source_event_prefix_unchanged',
                                                          'branch_identity_distinct', 'queued_command_idempotency')),
                    'continuation passing evidence incomplete')
        else:
            pairs = row.get('paired_raw_values', {})
            require(set(pairs) == set(section['conditions']), 'replay requires all four paired modes')
            source = _replay_source(row, protocol)
            continuation = report.get('continuation', {})
            require(continuation.get('status') == 'passed' and continuation.get('divergences') == []
                    and bool(continuation.get('max_abs_errors')), 'replay branch comparison diverged or missing')
            playback = report.get('playback', {})
            require(playback.get('mode') == 'playback' and type(playback.get('first_tick')) is int
                    and playback['first_tick'] == section['prefix_ticks'], 'replay playback scope differs')
            require(_normalized_pairs(pairs) == _normalized_pairs(_paired(report, section['source_ticks'])),
                    'asserted replay pairs differ from verifier evidence')
            for name, pair in pairs.items():
                require(pair.get('agreement') is True and pair.get('first_divergence') is None
                        and bool(pair.get('validated_fields')), 'passing replay mode inconsistent')
                computation = pair.get('executed_computation', {})
                expected = name in ('branch', 'policy_replay')
                require(all(computation.get(k) is expected for k in ('controller_reexecuted', 'inference_executed')),
                        'replay computation scope differs')
                if name in ('action_replay', 'policy_replay'):
                    mode = 'actions' if name == 'action_replay' else 'policy'
                    _replay_mode(pair.get('raw', {}), mode, source, section['source_ticks'])
                    _replay_mode(report.get('replays', {}).get(mode, {}).get('report', {}), mode, source, section['source_ticks'])
        passed += 1
    return dict(passed=passed, declared=len(rows), completed=sum(r['status'] == 'completed' for r in rows), rows=rows)


def _operation_source(row, replays, protocol):
    replay = replays[row['seed']]
    require(replay['status'] == 'completed' and replay['metrics'].get('agreement') is True,
            'completed operation lacks passing retained replay unit')
    _repeat([replay], protocol, 'replay')
    require(row.get('source') == replay.get('source'), 'operation source differs from retained replay source')
    expected_row = (json.dumps(replay, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    require(row.get('source_row_sha256') == hashlib.sha256(expected_row).hexdigest(), 'operation source row digest differs')
    before, after = row.get('source_hashes_before'), row.get('source_hashes_after')
    require(isinstance(before, dict) and bool(before) and before == after
            and all(isinstance(k,str) and _digest(v) for k,v in before.items()), 'operation source custody differs')
    meta = replay['source']
    snapshot_key = str(Path(meta['snapshot_path']).relative_to(meta['run_path']))
    require(before.get('recording/manifest.json') == replay['source_manifest_sha256']
            and before.get(snapshot_key) == replay['metrics']['snapshot_sha256'],
            'operation retained manifest/snapshot hash differs')
    require(type(row.get('playback_tick_count')) is int and row['playback_tick_count'] == protocol.replay['source_ticks'],
            'operation playback count differs')
    reports = row.get('replay_reports', {})
    require(set(reports) == {'actions', 'policy'}, 'operation replay reports incomplete')
    for mode, raw in reports.items():
        _replay_mode(raw, mode, replay['verifier_report']['source_run_id'], protocol.replay['source_ticks'])


def analyze(summary, manifest, protocol):
    """Validate retained rows then derive counts and whole-set paired estimates."""
    validate_finite(summary)
    validate_finite(manifest)
    require(manifest.get('analysis_status') == 'passed', 'campaign analysis did not pass')
    require(protocol._content_sha256 in EXECUTION_COMMITS_BY_PROTOCOL, 'protocol differs from frozen execution bytes')
    require(summary.get('identity') == manifest.get('identity'), 'manifest identity differs')
    require(summary['identity']['commit'] == EXECUTION_COMMITS_BY_PROTOCOL[protocol._content_sha256],
            'execution commit does not match its frozen protocol')
    recomputed = summarize(protocol, summary.get('rows', []))
    require(recomputed == summary, 'summary aggregates differ from retained rows')
    require(recomputed['declared_units'] == 111, 'expected exactly 111 declared descriptors')
    rows = recomputed['rows']
    faults = [r for r in rows if r['kind'] == 'fault']
    families = {case.id: case.family for case in protocol.fault_cases}
    fault_summary = dict(total=_faults(faults), paths={case.id: case.path for case in protocol.fault_cases},
                         cases={case.id: _faults([r for r in faults if r['case_id'] == case.id]) for case in protocol.fault_cases},
                         families={family: _faults([r for r in faults if families[r['case_id']] == family]) for family in dict.fromkeys(families.values())}, rows=faults)
    raw, eligible = [], []
    for seed in protocol.execution_overhead['seeds']:
        group = [r for r in rows if r['kind'] == 'execution_overhead' and r['seed'] == seed]
        matched = all(r['status'] == 'completed' for r in group)
        for key in protocol.execution_overhead['matched_fields']:
            matched = matched and group[0].get(key) is not None and all(r.get(key) == group[0][key] for r in group)
        matched = bool(matched and group[0].get('tick_count') == 220)
        for row in group:
            for flag in ('matched_seed', 'timing_eligible'):
                if flag in row:
                    require(type(row[flag]) is bool and row[flag] is matched, 'falsified matched seed gate')
                elif matched:
                    raise ValueError('matched seed gate not reported')
        values = {r['condition']: r['metrics'].get('wall_seconds_per_tick') for r in group}
        if matched:
            require(all(type(v) in (int, float) and v > 0 for v in values.values()), 'matched timing must be positive finite scalar')
            eligible.append(values)
        raw.append(dict(seed=seed, matched=matched, rows=group,
                        wall_ms={k: v*1000 if type(v) in (int, float) else None for k, v in values.items()},
                        relative_percent={k: (values[k]/values['null']-1)*100 for k in CONDITIONS[1:]} if matched else None))
    overhead = dict(matched=len(eligible), declared=len(raw), raw=raw,
                    wall_ms={c: stats([g[c]*1000 for g in eligible]) for c in CONDITIONS},
                    relative={c: stats([(g[c]/g['null']-1)*100 for g in eligible]) for c in CONDITIONS[1:]})
    operations = [r for r in rows if r['kind'] == 'operation_cost']
    replays = {r['seed']: r for r in rows if r['kind'] == 'replay'}
    for row in operations:
        if row['status'] == 'completed':
            _operation_source(row, replays, protocol)
    operation_stats = {}
    for metric in protocol.operation_cost['metrics']:
        values = [r['metrics'][metric] for r in operations if r['status'] == 'completed'
                  and r.get('timing_eligible', True) is True and type(r['metrics'].get(metric)) in (int, float)]
        require(all(v >= 0 for v in values), 'operation timing must be nonnegative')
        operation_stats[metric] = stats(values)
    offline = next(r for r in rows if r['kind'] == 'offline_reproduction')
    return dict(identity=recomputed['identity'], declared=len(rows), completed=sum(r['status'] == 'completed' for r in rows),
                status_counts=recomputed['status_counts'], faults=fault_summary,
                continuation=_repeat([r for r in rows if r['kind'] == 'continuation'], protocol, 'continuation'),
                replay=_repeat([r for r in rows if r['kind'] == 'replay'], protocol, 'replay'), overhead=overhead,
                operations=operation_stats, operation_rows=operations,
                scope=dict(overhead_cache_policy=protocol.execution_overhead['cache_policy'],
                           offline=protocol.offline_reproduction['scope'],
                           independent_machine_reproduction=False,
                           limitations=manifest.get('limitations', [])),
                offline=dict(status=offline['status'], scope=protocol.offline_reproduction['scope'],
                             independent_machine=False, row=offline))


def escape_latex(value):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
                    '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(c, c) for c in str(value))


def number(value):
    return 'not reported' if value is None else f'{value:.3g}' if type(value) is float else str(value)


def estimate(value, scale=1):
    return 'not estimable' if value is None else number(value['median']*scale)


def _table(headers, rows):
    return ('{\\small\\setlength{\\tabcolsep}{3pt}\n\\begin{tabular}{' + 'l' + 'r'*(len(headers)-1) + '}\n\\toprule\n' +
            ' & '.join(escape_latex(x) for x in headers) + r' \\' + '\n\\midrule\n' +
            '\n'.join(' & '.join(escape_latex(number(x)) for x in row) + r' \\' for row in rows) + '\n\\bottomrule\n\\end{tabular}}\n')


def analyze_snapshot_ablation(result, trace_root):
    """Read hashed, bounded S1 comparisons; no model execution or new measurements."""
    import numpy as np
    from paper.studies.authority_replay_v1.fault_matrix import _continuation_comparisons

    root = Path(trace_root).resolve(strict=True)
    require(root.is_dir(), 'snapshot trace root must be a directory')
    values = []
    for seed in (0,1,2):
        unit_id = f'fault/S1/default/fault/seed-{seed}'
        matches = [r for r in result['faults']['rows'] if r['unit_id'] == unit_id]
        require(len(matches) == 1, 'snapshot ablation requires exactly one declared S1 row per seed')
        row = matches[0]
        value = dict(seed=seed, unit_id=unit_id, status=row['status'], pose_action_error=None, full_action_error=None)
        values.append(value)
        if row['status'] != 'completed':
            continue
        trace = row.get('trace', {})
        require(trace.get('arrays_path') == 'continuation-pairs.npz' and _digest(trace.get('arrays_sha256')),
                'completed S1 requires declared arrays filename and SHA256')
        folder = root / f'fault__S1__default__fault__seed-{seed}'
        path = folder / trace['arrays_path']
        require(folder.resolve().is_relative_to(root) and path.resolve().is_relative_to(folder.resolve())
                and path.is_file(), 'completed S1 arrays missing or outside trace root')
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == trace['arrays_sha256'], 'snapshot arrays SHA256 differs from retained row')
        expected_divergence = dict(field='action', tick=0, reason='value')
        require(type(trace.get('comparison_origin_tick')) is int and trace['comparison_origin_tick'] == 8
                and trace.get('scientific_first_divergence') == expected_divergence
                and 'full_scientific_first_divergence' in trace and trace['full_scientific_first_divergence'] is None,
                'retained S1 scientific comparison scope differs')
        states = {}
        with np.load(io.BytesIO(raw), allow_pickle=False) as arrays:
            require(len(arrays.files) == len(set(arrays.files)), 'duplicate snapshot array names')
            for key in arrays.files:
                array = arrays[key]
                require(array.dtype.kind in 'biufc' and np.isfinite(array).all(), 'snapshot arrays must be finite numeric values')
                require(any(key == label+'__ticks' or key.startswith(label+'__0__') for label in ('expected','pose','full')),
                        'unexpected snapshot array field or tick')
            for label in ('expected','pose','full'):
                ticks = arrays[label+'__ticks']
                require(ticks.shape == () and ticks.dtype.kind in 'iu' and int(ticks) == 1,
                        'snapshot ablation requires exactly one comparison tick per condition')
                prefix = label+'__0__'
                states[label] = {key[len(prefix):]: arrays[key].copy() for key in arrays.files if key.startswith(prefix)}
        actions = [states[label].get('action') for label in ('expected','pose','full')]
        require(all(action is not None and action.dtype.kind == 'f' and action.ndim == 1 and action.size > 0 for action in actions)
                and all(action.shape == actions[0].shape and action.dtype == actions[0].dtype for action in actions),
                'snapshot action shapes/dtypes differ or are empty')
        comparisons = _continuation_comparisons(*[[states[label]] for label in ('expected','pose','full')])
        require(comparisons['scientific_first_divergence'] == expected_divergence
                and comparisons['full_scientific_first_divergence'] is None,
                'snapshot arrays contradict retained scientific comparison')
        for key, comparison in comparisons.items():
            if key in trace:
                require(trace[key] == comparison, 'snapshot arrays contradict retained trace comparison')
            if key in trace.get('comparisons', {}):
                require(trace['comparisons'][key] == comparison, 'snapshot arrays contradict retained comparison ledger')
        expected, pose, full = [action.astype(np.float64) for action in actions]
        value.update(pose_action_error=float(np.max(np.abs(pose-expected))),
                     full_action_error=float(np.max(np.abs(full-expected))),
                     comparison_origin_tick=8, first_offset=0, arrays_sha256=digest,
                     arrays_path=str(path.relative_to(root)))
    validate_finite(values)
    return values


def generate_snapshot_ablation(result, hashes, trace_root):
    values = analyze_snapshot_ablation(result, trace_root)
    metadata = dict(inputs=hashes, identity=result['identity'], rows=values,
                    scope='S1 retained single-offset action comparison; origin control tick 8, offset 0; no means or significance estimates')
    comments = '% Generated retained snapshot ablation; do not edit.\n'
    comments += '\n'.join('% '+line for line in json.dumps(metadata, sort_keys=True, indent=2, allow_nan=False).splitlines())+'\n'
    return comments+_table(['Seed','action error: pose','action error: full'],
                          [[r['seed'], 'not estimable' if r['pose_action_error'] is None else r['pose_action_error'],
                            'not estimable' if r['full_action_error'] is None else r['full_action_error']] for r in values])


def generate_outputs(result, hashes, trace_root=None):
    """Return six deterministic files, plus the optional retained S1 table."""
    f, o = result['faults']['total'], result['overhead']
    macros = dict(StudyCommit=result['identity']['commit'], ProtocolHash=result['identity']['protocol_sha256'],
                  StudyDeclaredUnits=result['declared'], StudyCompletedUnits=result['completed'],
                  FaultDeclaredUnits=f['declared'], FaultCompletedUnits=f['completed'],
                  FaultBaselineFalseAccepts=f['baseline_false_accepts'], FaultBaselineKnownClaims=f['baseline_known'],
                  FaultBaselineUnknownClaims=f['baseline_unknown'], FaultSystemSilentAccepts=f['silent_acceptance'] if f['reported']['silent_acceptance'] else 'not reported',
                  FaultBenignFalseRejects=f['benign_false_rejection'] if f['reported']['benign_false_rejection'] else 'not reported',
                  ContinuationPassed=result['continuation']['passed'], ContinuationDeclared=result['continuation']['declared'],
                  ReplayPassed=result['replay']['passed'], ReplayDeclared=result['replay']['declared'],
                  OverheadMatchedSeeds=o['matched'], OverheadDeclaredSeeds=o['declared'],
                  SynchronousOverheadMedian=estimate(o['relative']['synchronous']), BackgroundOverheadMedian=estimate(o['relative']['background']),
                  StorageOverheadMedian=estimate(o['relative']['background_storage']), NullWallMedianMs=estimate(o['wall_ms']['null']),
                  StorageWallMedianMs=estimate(o['wall_ms']['background_storage']), OfflineStatus=result['offline']['status'])
    header = '% Generated from retained evidence; do not edit.\n% Input SHA256: ' + json.dumps(hashes, sort_keys=True) + '\n'
    outputs = {'authority-claims.tex': '\n'.join('\\newcommand{\\'+k+'}{'+escape_latex(number(v))+'}' for k,v in macros.items())+'\n'}
    fault_rows = []
    for name, c in result['faults']['cases'].items():
        path_label = {'runtime': 'R', 'fixture': 'F', 'fixture_subprocess': 'F+'}[result['faults']['paths'][name]]
        fault_rows.append([f'{name} ({path_label})', f"{c['completed']}/{c['declared']}", c['baseline_accepted'], c['baseline_false_accepts'],
                           f"{c['baseline_true']}/{c['baseline_false']}/{c['baseline_unknown']}/{c['baseline_missing']}",
                           f"{c['production_detection']}/{c['diagnostic_detection']}/{c['study_guard_detection']}",
                           f"{c['correct_recovery']}/{c['reported']['correct_recovery']}",
                           f"{c['benign_false_rejection']}/{c['reported']['benign_false_rejection']}"])
    outputs['fault-matrix.tex'] = '% Interface/diag./label: interface outcomes; S1/B2 comparison diagnostics; R1/R2 study label guards.\n'
    outputs['fault-matrix.tex'] += '% Diagnostic counts do not establish automatic production refusal; raw outcome_scope is retained in metadata.\n'
    outputs['fault-matrix.tex'] += _table(['Case', 'Done/N', 'Accept', 'False', 'T/F/U/M', 'I/D/L', 'Rec./rep.', 'FR/rep.'], fault_rows)
    outputs['fault-matrix.tex'] += '\n\\par\\smallskip\n'
    outputs['fault-matrix.tex'] += _table(['Family', 'Done/N', 'False accept', 'Known/U/M'],
        [[name, f"{c['completed']}/{c['declared']}", c['baseline_false_accepts'],
          f"{c['baseline_known']}/{c['baseline_unknown']}/{c['baseline_missing']}"]
         for name,c in [*result['faults']['families'].items(), ('Total', f)]])
    outputs['replay-table.tex'] = _table(['Comparison', 'Pass/declared', 'Completed'],
        [[label, f"{result[k]['passed']}/{result[k]['declared']}", result[k]['completed']] for label,k in [('Continuation (100 ticks)', 'continuation'), ('All four replay modes (100 source ticks)', 'replay')]])
    overhead_rows = []
    for c in CONDITIONS:
        wall, relative = o['wall_ms'][c], o['relative'].get(c)
        overhead_rows.append([c.replace('background_storage', 'storage'), f"{o['matched']}/10", estimate(wall), 'not estimable' if wall is None else f"{number(wall['minimum'])}--{number(wall['maximum'])}",
                              'not estimable' if wall is None else number(wall['iqr']), 'reference' if c == 'null' else estimate(relative),
                              'reference' if c == 'null' else 'not estimable' if relative is None else number(relative['iqr'])])
    outputs['overhead-table.tex'] = _table(['Condition', 'n/N', 'ms/tick', 'range', 'IQR', 'delta (%)', 'delta IQR'], overhead_rows)
    outputs['overhead-table.tex'] += '\n\\par\\smallskip Raw per-seed ms/tick and paired differences (\\%).\\par\n'
    paired_rows = []
    for raw in o['raw']:
        delta = raw['relative_percent'] or {}
        paired_rows.append([raw['seed'], 'matched' if raw['matched'] else 'excluded',
                            *[number(raw['wall_ms'][c]) for c in CONDITIONS],
                            '/'.join(number(delta.get(c)) for c in CONDITIONS[1:])])
    outputs['overhead-table.tex'] += _table(['Seed', 'Gate', 'Null', 'Sync', 'Bg', 'Storage', 'delta S/B/T'], paired_rows)
    outputs['overhead-table.tex'] += '% Raw paired wall milliseconds and relative percentages (all declared seeds):\n'
    outputs['overhead-table.tex'] += '\n'.join('% '+json.dumps({k:v for k,v in raw.items() if k != 'rows'}, sort_keys=True) for raw in o['raw'])+'\n'
    operation_rows = []
    for key, value in result['operations'].items():
        operation_rows.append([key.removesuffix('_seconds'), 0 if value is None else value['n'], estimate(value,1000),
                               'not estimable' if value is None else number(value['iqr']*1000)])
    outputs['operation-table.tex'] = _table(['Operation', 'n/5 sources', 'median ms', 'IQR ms'], operation_rows)
    # Numeric paired points, no categorical bars; plot extent includes every negative value.
    points = [(raw['seed'], c, raw['relative_percent'][c]) for raw in o['raw'] if raw['matched'] for c in CONDITIONS[1:]]
    if points:
        low = min(0, *(p[2] for p in points)); high = max(0, *(p[2] for p in points))
        span = max(high-low, 1)
        y = lambda value: 0.25+3*(value-low)/span
        plot = [r'\begin{tikzpicture}[x=0.48cm,y=1cm]', rf'\draw[->] (-0.5,0) -- (10,0) node[right] {{seed}};',
                rf'\draw[->] (-0.5,0) -- (-0.5,3.7) node[above] {{paired delta (\%)}};',
                rf'\draw[dashed] (-0.5,{y(0):.6f}) -- (9.5,{y(0):.6f});']
        for value in dict.fromkeys((low,0,high)):
            plot.append(rf'\node[left] at (-0.5,{y(value):.6f}) {{{number(value)}}};')
        for seed in range(10): plot.append(rf'\node[below] at ({seed},0) {{{seed}}};')
        for raw in o['raw']:
            if raw['matched']:
                values = [0, *raw['relative_percent'].values()]
                plot.append(rf'\draw[gray!40] ({raw["seed"]},{y(min(values)):.6f}) -- ({raw["seed"]},{y(max(values)):.6f});')
        for c, color, mark, label in zip(CONDITIONS[1:], ('blue','red','black'), ('+','x','o'),
                                         (r'$+$ sync', r'$\times$ background', r'$\circ$ storage')):
            coords = ' '.join(f'({seed},{y(value):.6f})' for seed,condition,value in points if condition == c)
            plot.append(rf'\draw[{color}] plot[only marks,mark={mark}] coordinates {{{coords}}};')
            plot.append(rf'\node[{color},anchor=west] at (0,{4.1+CONDITIONS.index(c)*0.25:.2f}) {{{label}}};')
        plot.append(r'\end{tikzpicture}')
        outputs['overhead-plot.tex'] = '\n'.join(plot)+'\n'
    else:
        outputs['overhead-plot.tex'] = 'Paired timing overhead is not estimable.\n'
    metadata = '% Analysis retains failures, exact compared ticks/source identities, and scope:\n'
    metadata += '\n'.join('% '+line for line in json.dumps(result, sort_keys=True, indent=2, allow_nan=False).splitlines())+'\n'
    outputs = {name: header+metadata+content for name,content in outputs.items()}
    if trace_root is not None:
        outputs['snapshot-ablation.tex'] = generate_snapshot_ablation(result, hashes, trace_root)
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('summary','manifest','protocol','output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--trace-root', type=Path, help='Optional retained fault-matrix root containing the three hashed S1 NPZ files')
    args = parser.parse_args(argv)
    try:
        paths = {name: getattr(args,name) for name in ('summary','manifest','protocol')}
        hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()}
        result = analyze(parse_json(args.summary.read_text()), parse_json(args.manifest.read_text()), load_protocol(args.protocol))
        outputs = generate_outputs(result, hashes, trace_root=args.trace_root)
        if args.check:
            stale = [name for name,content in outputs.items() if not (args.output/name).is_file() or (args.output/name).read_text() != content]
            if stale:
                print('FAIL: stale evidence: '+', '.join(stale), file=sys.stderr)
                return 1
        else:
            args.output.mkdir(parents=True, exist_ok=True)
            for name, content in outputs.items(): (args.output/name).write_text(content)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
