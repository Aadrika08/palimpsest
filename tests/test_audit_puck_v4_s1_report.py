"""D8 audit of a published S1 report, on synthetic admissions only."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_puck_v4_scene_admission as t  # noqa: E402  (reuse its synthetic fixtures)
import audit_puck_v4_s1_report as a  # noqa: E402


@pytest.fixture(autouse=True)
def _synthetic_ledgers(monkeypatch):
    monkeypatch.setattr(t.s1, 'ENFORCE_ATTEMPT_LEDGERS', False)


def _receipt(tmp_path, returncode):
    path = tmp_path / 'receipt.json'
    path.write_text(json.dumps({'complete': True, 'drained': True, 'survivors_killed': [],
                                'returncode': returncode}))
    return path


def _admitted(tmp_path):
    tree = tmp_path / 'tree'
    t._touch(tree / 'docs/a.md', 'nothing here\n') if hasattr(t, '_touch') else \
        (tree / 'docs').mkdir(parents=True) or (tree / 'docs/a.md').write_text('nothing here\n')
    result, output = t._admit(tmp_path, [t._dir_root(tree)])
    assert result['verdict'] == 'admitted', result
    return output


def test_audit_passes_on_a_clean_admitted_report(tmp_path):
    report = _admitted(tmp_path)
    out = a.audit(report, _receipt(tmp_path, 0))
    assert out['passed'], [c for c in out['checks'] if not c['ok']]


def test_audit_fails_on_tampered_report_or_mismatched_receipt(tmp_path):
    report = _admitted(tmp_path)
    assert not a.audit(report, _receipt(tmp_path, 1))['passed']
    data = json.loads(Path(report).read_bytes())
    data['reservation']['scene_ids'] = data['reservation']['scene_ids'][:-1]
    tampered = tmp_path / 'tampered.json'
    tampered.write_bytes(json.dumps(data).encode())
    failed = {c['check'] for c in a.audit(tampered, _receipt(tmp_path, 0))['checks'] if not c['ok']}
    assert {'canonical bytes', 'reservation covers exactly the new IDs'} <= failed


def test_cli_refuses_existing_output(tmp_path):
    report = _admitted(tmp_path)
    out = tmp_path / 'audit.json'
    out.write_text('x')
    with pytest.raises(SystemExit):
        a.main(['--report', str(report), '--receipt', str(_receipt(tmp_path, 0)),
                '--output', str(out)])
