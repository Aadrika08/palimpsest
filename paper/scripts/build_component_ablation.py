#!/usr/bin/env python3
"""Generate the component-wise restore ablation numbers quoted in the paper.

Reads only the retained evidence (paper/evidence/authority-component-v1). Never launches
experiments. Re-derives each seed's analysis from the retained rows with the study's own
classify() and refuses if it disagrees with the analysis.json retained by the run.
"""
from __future__ import annotations

import argparse
import json
import sys
import hashlib
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
REPO = PAPER.parent
sys.path.insert(0, str(REPO))
from paper.studies.authority_component_v1 import runner  # noqa: E402

EVIDENCE = PAPER / 'evidence/authority-component-v1'
PROTOCOL = PAPER / 'studies/authority_component_v1/protocol.json'
OUTPUT = PAPER / 'generated/component-ablation.tex'


def _ticks(values):
    lo, hi = min(values), max(values)
    return str(lo) if lo == hi else f'{lo}--{hi}'


def compute() -> dict:
    protocol = json.loads(PROTOCOL.read_text())
    rows = [json.loads(line) for line in (EVIDENCE / 'rows.jsonl').read_text().splitlines()]
    seeds = protocol['seeds']
    if len(rows) != len(seeds) * protocol['arms_per_seed'] or any(r['status'] != 'completed' for r in rows):
        raise ValueError('ablation evidence is not 96 completed rows')
    identity = json.loads((EVIDENCE / 'identity.json').read_text())
    if identity['protocol_sha256'] != identity['go']['protocol_sha256'] or identity['go']['go'] is not True:
        raise ValueError('run identity does not carry the owner GO for its protocol')
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != identity['protocol_sha256']:
        raise ValueError('protocol.json differs from the protocol the run executed')
    if any(r['restore_refused'] or r['ticks'] != protocol['horizon_ticks'] or not isinstance(r['first_action_changed'], bool)
           for r in rows):
        raise ValueError('a row was refused, short or has no boolean first-action verdict')
    arm = {(r['seed'], r['arm']): r for r in rows}
    analyses = []
    for seed in seeds:
        derived = runner.classify({name: arm[(seed, name)] for name, _, _ in runner.arms()})
        if derived != json.loads((EVIDENCE / f'seed-{seed}/analysis.json').read_text()):
            raise ValueError(f'seed {seed}: recomputed analysis disagrees with the retained analysis')
        analyses.append(derived)
    count = lambda key, comp, want=True: sum(a[key][comp] is want for a in analyses)
    # 'clean' means every recorded tick field agreed, including the revision counter.
    clean = lambda name: sum(arm[(s, name)]['scientific_first_divergence'] is None
                             and arm[(s, name)]['application_first_divergence'] is None for s in seeds)
    revision_only = lambda name: sum(arm[(s, name)]['scientific_first_divergence'] is None
                                     and (arm[(s, name)]['application_first_divergence'] or {}).get('field') == 'revision'
                                     for s in seeds)
    # Text claim 'the first action changed only when hidden state was stale', checked over every arm.
    for r in rows:
        if r['arm'] != 'full' and r['first_action_changed'] != ('controller_hidden' not in r['from_source']):
            raise ValueError(f"{r['unit_id']}: first-action change does not track stale hidden state")
    tick = lambda name: [arm[(s, name)]['first_action_divergence_tick'] for s in seeds]
    for name in ('loo:observation', 'loo:physics', 'loo:controller_retina'):
        if None in tick(name):
            raise ValueError(f'{name}: action never diverged on some seed; macros assume it did')
    others = [c for c in runner.COMPONENTS if c not in ('controller_hidden', 'rng')]
    prechecks = [json.loads((EVIDENCE / f'seed-{s}/precheck.json').read_text()) for s in seeds]
    if any(p['differs']['rng'] for p in prechecks):
        raise ValueError('rng differs between source and donor on some seed; the text says the snapshot-to-post-step step consumed no RNG state')
    cpu = json.loads((EVIDENCE / 'cpu.json').read_text())
    return {
        'seeds': len(seeds), 'arms': protocol['arms_per_seed'], 'horizon': protocol['horizon_ticks'],
        'valid': sum(a['h1_full_agrees'] for a in analyses),
        'hidden_necessary': count('necessary_first_action', 'controller_hidden'),
        'hidden_repairs': count('repairs_first_action', 'controller_hidden'),
        'other_first_action': sum(a['necessary_first_action'][c] is True for a in analyses for c in others),
        'other_first_action_arms': len(others) * len(seeds),
        'inputs_revision_only': revision_only('add:controller_inputs'),
        'observation_tick': _ticks(tick('loo:observation')),
        'physics_tick': _ticks(tick('loo:physics')),
        'retina_tick': _ticks(tick('loo:controller_retina')),
        'wrapper_clean': clean('loo:environment'), 'application_revision_only': revision_only('loo:application'),
        'cpu': round(cpu['total_cpu_seconds_including_parent']),
    }


def render(v: dict) -> str:
    names = {'seeds': 'CompSeeds', 'arms': 'CompArms', 'horizon': 'CompHorizon',
             'valid': 'CompValidSeeds', 'hidden_necessary': 'CompHiddenNecessary',
             'hidden_repairs': 'CompHiddenRepairs', 'other_first_action': 'CompOtherFirstAction',
             'other_first_action_arms': 'CompOtherFirstActionArms',
             'inputs_revision_only': 'CompInputsRevisionOnly', 'observation_tick': 'CompObservationTick',
             'physics_tick': 'CompPhysicsTick', 'retina_tick': 'CompRetinaTick', 'wrapper_clean': 'CompWrapperClean',
             'application_revision_only': 'CompApplicationRevisionOnly', 'cpu': 'CompCPU'}
    lines = ['% Generated by scripts/build_component_ablation.py from paper/evidence/authority-component-v1; do not edit.']
    for key, name in names.items():
        value = f'{v[key]:,}' if key == 'cpu' else v[key]
        lines.append(f'\\newcommand{{\\{name}}}{{{value}}}')
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = render(compute())
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != text:
            raise SystemExit('component-ablation.tex is missing or stale')
        return 0
    OUTPUT.write_text(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
