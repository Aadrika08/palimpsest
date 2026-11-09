#!/usr/bin/env python3
"""Independent read-only audit of a published puck v4 S1 admission report (protocol D8).

Re-reads the report and its declared inputs; never rescans roots. Checks canonical
bytes, input hashes, the frozen protocol, verdict/reservation consistency against the
protocol roster, all-false claims, and the stage launcher receipt. Writes one audit
JSON to a fresh path. Exit 0 only when every check passes.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from palimpsest import puck_v4_scene_admission as s1


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(report_path, receipt_path):
    checks = []

    def check(name, ok, detail=''):
        checks.append({'check': name, 'ok': bool(ok), 'detail': detail})

    raw = Path(report_path).read_bytes()
    report = json.loads(raw)
    check('canonical bytes', s1.canonical_bytes(report) == raw)
    check('kind/version/stage', (report.get('kind'), report.get('version'), report.get('stage'))
          == (s1.REPORT_KIND, 1, s1.S1_GO_STAGE))
    inputs = report.get('inputs', {})
    for name in ('protocol', 'comparison_set', 'go_record', 'held_out_go_record',
                 'calibration_record'):
        item = inputs.get(name)
        if item is None:
            needs = (name == 'held_out_go_record' and any(
                row.get('held_out_payloads') for row in report.get('roots', [])))
            check(f'input {name} present', name in ('calibration_record', 'held_out_go_record')
                  and not needs, 'absent')
            continue
        path = item.get('path')
        ok = bool(path) and os.path.isfile(path) and _sha(Path(path).read_bytes()) == item['sha256']
        check(f'input {name} hash', ok, path or '')
    protocol_sha = inputs.get('protocol', {}).get('sha256')
    check('protocol is a frozen v4 version',
          protocol_sha in (s1.PROTOCOL_SHA256, s1.ATTEMPT_1_PROTOCOL_SHA256))
    protocol = json.loads(Path(inputs['protocol']['path']).read_bytes())
    roster = s1.derive_roster(protocol)
    check('roster matches protocol', report.get('roster') == roster)
    verdict, reasons = report.get('verdict'), report.get('refusal_reasons')
    if verdict == 'admitted':
        reservation = report.get('reservation') or {}
        check('admitted has no refusal reasons', reasons == [])
        check('admitted has no collisions', report.get('collisions') == [])
        check('admitted has no ambiguous findings', report.get('ambiguous') == [])
        check('reservation covers exactly the new IDs',
              reservation.get('scene_ids') == roster['new_scene_ids']
              and reservation.get('collection') == roster['collection']
              and reservation.get('development') == roster['development'])
        check('reservation lineage is the frozen protocol',
              reservation.get('lineage_protocol_sha256') == s1.PROTOCOL_SHA256)
    else:
        check('refused verdict is explicit', verdict == 'refused' and bool(reasons))
        check('refused report reserves nothing', report.get('reservation') is None)
    claims = report.get('claims', {})
    check('no held-out comparison, read, minting, simulator or model claims',
          not any(claims.get(k) for k in ('held_out_payloads_compared', 'held_out_read',
                                            'scenes_minted', 'simulator_executed', 'models_loaded'))
          and claims.get('qualification_claims') == [])
    allow = {row['sha256'] for row in protocol.get('amendment_1', {}).get('change', {}).get(
        'non_scene_content_allowlist', [])}
    amended = protocol_sha == s1.PROTOCOL_SHA256
    check('non-scene mentions only for protocol-allowlisted contents',
          ('non_scene_asset_mentions' in report) == amended
          and all(row.get('sha256') in allow
                  for row in report.get('non_scene_asset_mentions', [])))
    check('lost root never treated as clean',
          report.get('lost_root', {}).get('treated_as_clean') is False)
    receipt = json.loads(Path(receipt_path).read_bytes())
    check('launcher receipt complete and drained',
          receipt.get('complete') is True and receipt.get('drained') is True
          and not receipt.get('survivors_killed'))
    check('launcher exit matches verdict',
          receipt.get('returncode') == (0 if verdict == 'admitted' else 1))
    return {'kind': 'puck-v4-s1-audit-v1', 'report': {'path': str(report_path), 'sha256': _sha(raw)},
            'receipt': {'path': str(receipt_path), 'sha256': _sha(Path(receipt_path).read_bytes())},
            'verdict_audited': verdict, 'checks': checks,
            'passed': all(row['ok'] for row in checks)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--report', required=True)
    parser.add_argument('--receipt', required=True, help='run_research_stage receipt.json of S1')
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    if os.path.lexists(args.output):
        parser.error(f'output must be a fresh path: {args.output}')
    result = audit(args.report, args.receipt)
    with open(args.output, 'x', encoding='utf-8') as stream:
        json.dump(result, stream, sort_keys=True, indent=1)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'passed': result['passed'], 'failed': [r['check'] for r in result['checks']
                                                             if not r['ok']]}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
