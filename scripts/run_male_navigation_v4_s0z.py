"""MaleCNS v4 S0z: pin the v4 corpus and audit it independently; plan-only by default.

Protocol (stage table + execution stops): "S0z freezes the v4 data-manifest SHA and the source
rosters before any training reads them", with an independent compact audit; S1 cannot start
before S0z passes review. There is NO producer and NO array bundle: v3 never used one, and S1
(``train_male_navigation_v4.py``) loads the old arrays from S0f's historical transfer and derives
the 12 advice arrays in a T-f-reader child, hash-gated to the manifest's feature_target_sha256.

This controller (one unit under ``run_research_stage.py``; it keeps no CPU accounting):

1. checks the GO (stage S0z, protocol sha), absolute paths, the unit ``work`` leaf and a fresh
   stage root, and requires the S0f data-manifest sha256 and the schedule-derivation sha256 it
   was told to expect;
2. runs the separate-code-path audit (``audit_male_navigation_v4_s0z.py``: stdlib + NumPy only);
3. reproduces M4's pure ``derive()`` twice (byte-identical, sha256 equal to the expected pin);
4. only if both pass, writes ``corpus-pin.json`` in M4's ``m7-navigation-v4-corpus-pin-1`` schema
   (stage S0z, status passed, data manifest, the T-f/T-h reader context S1 needs, the 26 ordered
   roster hashes, derivation sha, the S0f record, the chain S0a..S0z and the audit).

Writes only under the stage root: ``derivation.json``, ``audit.json`` and ``corpus-pin.json``.
Torch is never imported. ``driver.check_pin_record``/``previous_chain`` cannot be used (S0z is not
in the driver's stage map), so the S0f record is validated by the audit's explicit chain check.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import male_navigation_v4_controls as ctl  # noqa: E402
import audit_male_navigation_v4_s0z as audit_module  # noqa: E402

STAGE = 'S0z'
UNIT = {'stage': STAGE, 'runtime_max_sec': 300, 'k': 1}          # worst case k x (300 + 5) = 305
CORPUS_PIN_SCHEMA = 'm7-navigation-v4-corpus-pin-1'
FILES = ('derivation.json', 'audit.json', 'corpus-pin.json')


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--go', help='GO record naming stage S0z and the protocol sha256 (absent: plan only)')
    parser.add_argument('--plan-only', action='store_true', help='Print the plan (the default without --go)')
    parser.add_argument('--s0f-record', help='S0f pin record (absolute)')
    parser.add_argument('--stage-root', help='Fresh S0z stage root (absolute); the controller creates it')
    parser.add_argument('--expected-manifest-sha256', help='S0f data manifest sha256 the GO binds')
    parser.add_argument('--expected-derivation-sha256', help='Schedule derivation sha256 the GO binds')
    return parser.parse_args(argv)


def configure(args, protocol_sha256):
    if args.go is not None and args.plan_only: raise ctl.Refusal('--plan-only and --go are mutually exclusive')
    cfg = {n: str(ctl.absolute('--' + n.replace('_', '-'), getattr(args, n))) for n in ('s0f_record', 'stage_root')}
    for name in ('expected_manifest_sha256', 'expected_derivation_sha256'):
        value = getattr(args, name)
        if not audit_module._hex(value): raise ctl.Refusal(f'--{name.replace("_", "-")} needs a 64-hex sha256')
        cfg[name] = value
    record = ctl.read_json(cfg['s0f_record'])
    if ctl.driver.under(cfg['stage_root'], record.get('output_root', '/')) or ctl.driver.under(record.get('output_root', '/'), cfg['stage_root']):
        raise ctl.Refusal('--stage-root overlaps the S0f output tree')
    if record.get('protocol_sha256') != protocol_sha256: raise ctl.Refusal('S0f record binds another protocol')
    return {'stage': STAGE, 'protocol_sha256': protocol_sha256, **cfg,
            'go': None if args.go is None else str(ctl.absolute('--go', args.go)), 'outputs': list(FILES)}


def derive_twice(manifest_raw, manifest_sha256, expected):
    """M4's pure derive(), run twice; byte-identical and equal to the expected pin."""
    sys.path.insert(0, str(ctl.ROOT/'src'))
    from palimpsest import male_matched_budget_v4 as budget
    first, second = budget.derive(manifest_raw, manifest_sha256), budget.derive(manifest_raw, manifest_sha256)
    if first['bytes'] != second['bytes'] or first['sha256'] != expected:
        raise ctl.Refusal(f'derive() is not reproducible or differs from the expected pin: {first["sha256"]}')
    return first['bytes']


def run(cfg):
    root = Path(cfg['stage_root'])
    record = ctl.read_json(cfg['s0f_record'])
    manifest_item = record['outputs']['data-manifest.json']
    manifest_path = Path(record['output_root'])/'data-manifest.json'
    manifest_raw = ctl.driver.read_bounded(manifest_path)
    derivation = derive_twice(manifest_raw, ctl.sha256_bytes(manifest_raw), cfg['expected_derivation_sha256'])
    root.mkdir(parents=True)
    written = {'derivation.json': ctl.write_json(root/'derivation.json', json.loads(derivation))}
    report = audit_module.audit(cfg['s0f_record'], expected_manifest_sha256=cfg['expected_manifest_sha256'],
                                expected_derivation_sha256=cfg['expected_derivation_sha256'], derivation_bytes=derivation,
                                protocol_sha256=cfg['protocol_sha256'])
    written['audit.json'] = ctl.write_json(root/'audit.json', report)
    if report['status'] != 'passed':
        ctl.emit({'mode': 'go', 'stage': STAGE, 'status': 'failed-audit', 'failures': [f['name'] for f in report['failures']]})
        return 1
    manifest = json.loads(manifest_raw)
    s0f_raw = ctl.driver.read_bounded(cfg['s0f_record'])
    pin = {'schema': CORPUS_PIN_SCHEMA, 'protocol_sha256': cfg['protocol_sha256'], 'stage': STAGE, 'status': 'passed',
           'qualification_claims': [], 'scientific_attempt': True,
           'data_manifest': {'path': str(manifest_path), 'sha256': ctl.sha256_bytes(manifest_raw), 'bytes': len(manifest_raw)},
           'reader': {'t_f': {'path': record['worktree'], 'head': record['port']['head']},
                      't_h': {'path': manifest['historical_reader']['root'], 'head': manifest['historical_reader']['head']},
                      'locator': {'path': record['port']['locator_path'], 'sha256': record['port']['locator_sha256'],
                                  'bytes': Path(record['port']['locator_path']).stat().st_size},
                      'data_root': record['output_root']},
           'roster_feature_target_sha256': {'old_train': [s['feature_target_sha256'] for s in manifest['arms']['old']['train']],
                                            'advice': [s['feature_target_sha256'] for s in manifest['arms']['augmented']['train'][10:]],
                                            'dev': [s['feature_target_sha256'] for s in manifest['arms']['old']['dev']]},
           'schedule_derivation_sha256': cfg['expected_derivation_sha256'],
           's0f_pin_record': {'path': cfg['s0f_record'], 'sha256': ctl.sha256_bytes(s0f_raw), 'bytes': len(s0f_raw)},
           'audit': {'path': written['audit.json']['path'], 'sha256': written['audit.json']['sha256']},
           'go_sha256': cfg['go_sha256'], 'chain': {**record['chain'], STAGE: {'stage_root': cfg['stage_root'], 'outputs': {
               name: {'sha256': written[name]['sha256'], 'bytes': written[name]['bytes']} for name in ('derivation.json', 'audit.json')}}},
           'advice_arrays': 'derived at S1 by the T-f reader child; enforced by the feature_target_sha256 gate, not published here'}
    written['corpus-pin.json'] = ctl.write_json(root/'corpus-pin.json', pin)
    ctl.emit({'mode': 'go', 'stage': STAGE, 'status': 'passed', 'corpus_pin': written['corpus-pin.json']})
    return 0


def main(argv=None, *, protocol_sha256=None, require_unit=True):
    args = parse(sys.argv[1:] if argv is None else argv)
    try:
        protocol_sha256 = ctl.protocol_gate(protocol_sha256)
        cfg = configure(args, protocol_sha256)
        if args.go is None:
            ctl.emit({'mode': 'plan-only', **cfg, 'unit_command': ctl.unit_command(
                STAGE, UNIT['runtime_max_sec'], [sys.executable, '-B', str(Path(__file__).resolve()),
                                                 *(sys.argv[1:] if argv is None else argv), '--go', '<GO>'])})
            return 0
        cfg['go_sha256'] = ctl.go_gate(cfg['go'], STAGE, protocol_sha256)
        if require_unit and not ctl.research_stage_unit():
            raise ctl.Refusal('S0z must run as stage S0z inside a run_research_stage.py unit (work leaf)')
        ctl.fresh('--stage-root', cfg['stage_root'])
        if not Path(cfg['stage_root']).parent.is_dir(): raise ctl.Refusal('--stage-root parent directory must exist')
        return run(cfg)
    except (ctl.Refusal, OSError, ValueError, KeyError) as error:
        ctl.emit({'mode': 'go' if args.go else 'plan-only', 'stage': STAGE, 'status': 'refused',
                  'reason': str(error) if isinstance(error, ctl.Refusal) else f'{type(error).__name__}: {error}'})
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
