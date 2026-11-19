"""MaleCNS v4 S0z: pin + independent compact audit, on a synthetic S0f output only (no real data)."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src'), str(ROOT/'tests')]
import audit_male_navigation_v4_s0z as audit_module  # noqa: E402
import male_navigation_v4_controls as ctl  # noqa: E402
import run_male_navigation_v4_s0z as s0z  # noqa: E402
import train_male_navigation_v4 as trainer  # noqa: E402
from test_male_navigation_v4 import manifest_value, canonical  # noqa: E402
from palimpsest import male_matched_budget_v4 as budget  # noqa: E402

PROTOCOL = ctl.driver.PROTOCOL_SHA256
ORDER = audit_module.ORDER


def sha(raw): return hashlib.sha256(raw).hexdigest()


def write_bytes(path, raw):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw); return path


def build(tmp, mutate=None, hist=None, mutate_audit=None, mutate_record=None):
    """A synthetic S0f output tree + pin record; returns a dict of paths and the expected shas."""
    out = Path(tmp)/'s0f/data'
    arrays = {}
    m = manifest_value(arrays=arrays)
    old, dev = m['arms']['old']['train'], m['arms']['old']['dev']
    m['new_sources'] = [{**s, 'ticks': a['ticks']} for s, a in zip(m['new_sources'], m['arms']['augmented']['train'][10:])]
    rows = lambda xs: [x['ticks'] for x in xs]
    adv = rows(m['arms']['augmented']['train'][10:])
    s0c = write_bytes(Path(tmp)/'s0c/data-manifest.json', canonical({'ordered_sources': {
        'train': copy.deepcopy(old), 'dev': copy.deepcopy(dev), 'held_out': []}}))
    m.update({'counts': {'old_sources': 14, 'new_sources': 12, 'combined_unique_sources': 26, 'old_train_rows': sum(rows(old)),
                         'new_advice_train_rows': sum(adv), 'augmented_train_rows': sum(rows(old)) + sum(adv),
                         'recorded_dev_rows': sum(rows(dev)), 'combined_rows': sum(rows(old)) + sum(adv) + sum(rows(dev)),
                         'held_out_sources': 0, 'held_out_rows': 0},
              'input_documents': {'old_manifest': {'path': str(s0c), 'sha256': sha(s0c.read_bytes())}},
              'old_manifest_sha256': sha(s0c.read_bytes()),
              'historical_reader': {'root': str(Path(tmp)/'t-h'), 'head': 'b'*40}})
    s0e_root = Path(tmp)/'s0e'
    audit_doc = {'kind': 'm7-navigation-v4-root-raw-audit-1', 'status': 'passed', 'failures': [], 'not_covered': []}
    if mutate_audit: mutate_audit(audit_doc)
    audit_file = write_bytes(s0e_root/'control/root-raw-audit.json', canonical(audit_doc))
    m['input_documents'].update(accepted_collection={'path': str(s0e_root/'collection/report.json')},
                                root_raw_audit={'path': str(audit_file), 'sha256': sha(audit_file.read_bytes()), 'bytes': audit_file.stat().st_size})
    if mutate: mutate(m)
    historical, mapping, npz = {}, [], {}
    for i, source in enumerate(old + dev):
        key = source['feature_target_sha256']
        f, t = arrays[key + '/features'], arrays[key + '/targets']
        if hist: f, t = hist(i, f, t)
        npz[f'source{i:03d}_features'], npz[f'source{i:03d}_targets'] = f, t
        mapping.append({'split': 'train' if i < 10 else 'dev', 'run_id': source['run_id'], 'episode': 0, 'ticks': source['ticks'], 'prefix': f'source{i:03d}'})
    import io
    stream = io.BytesIO(); np.savez(stream, **npz)
    raw = canonical(m)
    write_bytes(out/'data-manifest.json', raw)
    write_bytes(out/'historical-arrays.npz', stream.getvalue())
    write_bytes(out/'historical-result.json', canonical({'arrays': mapping}))
    write_bytes(out/'after-admission.json', b'{}')
    locator = write_bytes(Path(tmp)/'s0f/pin-record.json.port-pins.json', b'{"documents": {}}')
    outputs = {p.relative_to(out).as_posix(): {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size} for p in sorted(out.rglob('*')) if p.is_file()}
    try:
        derivation = budget.derive(raw, sha(raw))
    except ValueError:
        derivation = {'bytes': b'{}', 'sha256': sha(b'{}')}
    ports = json.loads((ROOT/'docs/plans/m7-navigation-v4-pins/ports.json').read_text())['trees']
    commits = {'S0a': 'cc1cea93d4c3333a0ee2a091dd34fff0b2986887', 'S0b': 'c382c86781a7a5d6651af721119789729cc890ae',
               'S0c': ports['T-c']['port_commit'], 'S0d': ports['T-d']['port_commit'], 'S0e': ports['T-e']['port_commit'], 'S0f': ports['T-f']['port_commit']}
    advice_ids = audit_module.ADVICE
    entry = {'producing_commit': commits['S0f'], 'worktree': str(Path(tmp)/'t-f'), 'output_root': str(out), 'outputs': outputs}
    chain = {s_: {'stage': s_, 'producing_commit': c} for s_, c in commits.items()}
    chain['S0c']['outputs'] = {'data-manifest.json': {'sha256': sha(s0c.read_bytes()), 'bytes': 1}}
    chain['S0e'].update(counts=dict(zip(advice_ids, adv)), outputs={'control/root-raw-audit.json': {'sha256': sha(audit_file.read_bytes()), 'bytes': 1}})
    s0e_record = {'stage': 'S0e', 'previous_record_sha256': 'd'*64, 'chain': {k: chain[k] for k in ORDER[:5]}}
    s0e_file = write_bytes(s0e_root/'control/collector-pin-record.json', canonical(s0e_record))
    canon = lambda v: (json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    chain['S0f'] = entry
    link = sha(canon({'chain': {k: chain[k] for k in ORDER[:-1]}, 'records': [sha(canon(s0e_record))]}))
    record = {'schema': 'm7-navigation-v4-pin-record-1', 'stage': 'S0f', 'protocol_sha256': PROTOCOL, 'producing_commit': commits['S0f'],
              'worktree': str(Path(tmp)/'t-f'), 'output_root': str(out), 'outputs': outputs, 'qualification_claims': [],
              'previous_record_sha256': link, 'chain': chain,
              'port': {'tree': 'T-f', 'head': commits['S0f'], 'locator_path': str(locator), 'locator_sha256': sha(locator.read_bytes())}}
    if mutate_record: mutate_record(record)
    path = write_bytes(Path(tmp)/'s0f/pin-record.json', canonical(record))
    return {'record': path, 'out': out, 'manifest_sha': sha(raw), 'derivation': derivation['bytes'], 'derivation_sha': derivation['sha256'],
            'manifest': m, 'arrays': arrays}


def run_audit(b, **changes):
    args = dict(expected_manifest_sha256=b['manifest_sha'], expected_derivation_sha256=b['derivation_sha'],
                derivation_bytes=b['derivation'], protocol_sha256=PROTOCOL)
    return audit_module.audit(b['record'], **{**args, **changes})


def failed(report): return {f['name'] for f in report['failures']}


def test_audit_passes_a_synthetic_s0f_output_and_states_what_it_does_not_vouch_for(tmp_path):
    report = run_audit(build(tmp_path))
    assert report['status'] == 'passed' and report['failures'] == [], report['failures']
    assert {c['name'] for c in report['checks']} == {'s0f_record', 'outputs', 'manifest_pin', 'structure', 'old_corpus', 'chain', 's0e_audit', 'historical_arrays', 'derivation'}
    assert report['advice_arrays'].startswith('not vouched')   # Torch absence is asserted in the controller subprocess test


MUTATIONS = {
    'held_out_present': (lambda m: m['arms']['old'].update(held_out=[{'run_id': 'x'}]), 'structure'),
    'advice_reordered': (lambda m: m['new_sources'].reverse(), 'structure'),
    'recovery_over_bound': (lambda m: [m['arms'][a]['train'][9].update(ticks=121) for a in ('old', 'augmented')], 'structure'),
    'advice_over_bound': (lambda m: m['arms']['augmented']['train'][12].update(ticks=601), 'structure'),
    'duplicate_hash': (lambda m: m['arms']['augmented']['train'][11].update(feature_target_sha256=m['arms']['augmented']['train'][10]['feature_target_sha256']), 'structure'),
    'count_drift': (lambda m: m['counts'].update(old_train_rows=m['counts']['old_train_rows'] + 1), 'structure'),
    'augmented_prefix_differs': (lambda m: m['arms']['augmented']['train'][0].update(run_id='f'*32), 'structure'),
    'status': (lambda m: m.update(status='prepared'), 'structure'),
}


@pytest.mark.parametrize('name', sorted(MUTATIONS))
def test_audit_refuses_structural_faults(tmp_path, name):
    mutate, check = MUTATIONS[name]
    b = build(tmp_path, mutate)
    report = run_audit(b)
    assert report['status'] == 'failed' and check in failed(report), (name, failed(report))


def test_audit_refuses_old_identities_that_differ_from_s0c_historical_drift_and_wrong_derivation(tmp_path):
    b = build(tmp_path/'a', lambda m: m['arms']['old']['train'][3].update(run_id='e'*32))
    assert 'old_corpus' in failed(run_audit(b))
    b = build(tmp_path/'b', hist=lambda i, f, t: (f + 1 if i == 2 else f, t))
    assert 'historical_arrays' in failed(run_audit(b))
    b = build(tmp_path/'c', hist=lambda i, f, t: (f.astype(np.float64) if i == 0 else f, t))
    assert 'historical_arrays' in failed(run_audit(b))
    b = build(tmp_path/'d', hist=lambda i, f, t: (np.where(np.arange(f.size).reshape(f.shape) == 0, np.nan, f).astype(np.float32) if i == 1 else f, t))
    assert 'historical_arrays' in failed(run_audit(b))
    b = build(tmp_path/'e')
    doc = json.loads(b['derivation']); doc['arms']['augmented']['q'] += 1
    bad = canonical(doc)
    assert 'derivation' in failed(run_audit(b, derivation_bytes=bad, expected_derivation_sha256=sha(bad)))
    assert 'derivation' in failed(run_audit(b, expected_derivation_sha256='0'*64))
    assert failed(run_audit(b, expected_manifest_sha256='0'*64)) >= {'manifest_pin'}


def test_audit_refuses_a_changed_output_a_broken_chain_and_a_wrong_locator(tmp_path):
    b = build(tmp_path/'a')
    (b['out']/'after-admission.json').write_bytes(b'{"x": 1}')
    assert 'outputs' in failed(run_audit(b))
    b = build(tmp_path/'b')
    record = json.loads(b['record'].read_bytes()); record['chain'].pop('S0c')
    b['record'].write_bytes(canonical(record))
    assert 's0f_record' in failed(run_audit(b))
    b = build(tmp_path/'c')
    record = json.loads(b['record'].read_bytes()); Path(record['port']['locator_path']).write_bytes(b'{}')
    assert 's0f_record' in failed(run_audit(b))


# ------------------------------------------------------------------- controller

RUNNER = ('import json, sys; sys.path.insert(0, sys.argv[1]); import run_male_navigation_v4_s0z as m; '
          'code = m.main(json.loads(sys.argv[2]), require_unit=False); print(json.dumps({"code": code, "torch": "torch" in sys.modules}))')


def go(tmp, stage='S0z', **changes):
    path = write_bytes(Path(tmp)/f'go-{stage}-{len(changes)}.json', canonical({'decision': 'GO', 'stage': stage, 'lane': 'navigation',
        'protocol_sha256': PROTOCOL, 'granted_by': 'owner', 'granted_at': '2026-11-18', **changes}))
    return path


def argv(b, tmp, go_path=None, **changes):
    values = {'--s0f-record': b['record'], '--stage-root': Path(tmp)/'s0z', '--expected-manifest-sha256': b['manifest_sha'],
              '--expected-derivation-sha256': b['derivation_sha'], **changes}
    return [str(x) for k, v in values.items() for x in (k, v)] + ([] if go_path is None else ['--go', str(go_path)])


def run_main(arguments):
    done = subprocess.run([sys.executable, '-B', '-c', RUNNER, str(ROOT/'scripts'), json.dumps(arguments)], capture_output=True, text=True,
                          timeout=120, env={**ctl.child_env(), 'PYTHONPATH': str(ROOT/'src')})
    lines = [line for line in done.stdout.splitlines() if line.startswith('{"code"')]
    return json.loads(lines[-1]), done.stdout, done.stderr


def test_plan_only_is_the_default_writes_nothing_and_budgets_305(tmp_path, capsys):
    b = build(tmp_path)
    assert s0z.main(argv(b, tmp_path)) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan['mode'] == 'plan-only' and plan['stage'] == 'S0z' and plan['outputs'] == ['derivation.json', 'audit.json', 'corpus-pin.json']
    unit = plan['unit_command']
    flag = lambda n: unit[unit.index(n) + 1]
    assert (flag('--stage'), flag('--runtime-max-sec'), flag('--worst-case-cpu'), flag('--cpu-quota-k')) == ('S0z', '300', '305', '1')
    assert not (Path(tmp_path)/'s0z').exists()
    assert s0z.main(argv(b, tmp_path) + ['--plan-only', '--go', str(go(tmp_path))]) == 2


@pytest.mark.parametrize('mutate, reason', [
    (lambda b, t: {'--s0f-record': 'relative/pin.json'}, 'absolute'),
    (lambda b, t: {'--stage-root': 'relative/s0z'}, 'absolute'),
    (lambda b, t: {'--expected-manifest-sha256': 'abc'}, '64-hex'),
    (lambda b, t: {'--stage-root': str(b['out']/'inner')}, 'overlaps'),
])
def test_refuses_relative_paths_bad_shas_and_an_overlapping_stage_root(tmp_path, capsys, mutate, reason):
    b = build(tmp_path)
    assert s0z.main(argv(b, tmp_path, go(tmp_path), **mutate(b, tmp_path)), require_unit=False) == 2
    assert reason in json.loads(capsys.readouterr().out)['reason']
    assert not (Path(tmp_path)/'s0z').exists()


def test_go_gating_unit_requirement_and_freshness(tmp_path, capsys):
    b = build(tmp_path)
    for wrong in (go(tmp_path, 'S0f'), go(tmp_path, 'S0z', protocol_sha256='0'*64), go(tmp_path, 'S0z', decision='NO-GO')):
        assert s0z.main(argv(b, tmp_path, wrong), require_unit=False) == 2
        assert 'does not name stage S0z' in json.loads(capsys.readouterr().out)['reason']
    assert s0z.main(argv(b, tmp_path, go(tmp_path))) == 2                              # not inside a research-stage unit
    assert 'run_research_stage' in json.loads(capsys.readouterr().out)['reason']
    (Path(tmp_path)/'s0z').mkdir()
    assert s0z.main(argv(b, tmp_path, go(tmp_path)), require_unit=False) == 2
    assert 'fresh' in json.loads(capsys.readouterr().out)['reason']


def test_passing_run_pins_the_corpus_for_m4_with_the_full_chain_and_writes_only_the_stage_root(tmp_path):
    b = build(tmp_path)
    before = {p for p in Path(tmp_path).rglob('*')}
    result, out, err = run_main(argv(b, tmp_path, go(tmp_path)))
    assert result == {'code': 0, 'torch': False}, (out, err)
    created = {p for p in Path(tmp_path).rglob('*')} - before
    root = Path(tmp_path)/'s0z'
    outside = {p.name for p in created if p != root and not p.is_relative_to(root)}
    assert outside == {'go-S0z-0.json'}                                           # only the test's own GO file
    assert sorted(p.name for p in root.iterdir()) == ['audit.json', 'corpus-pin.json', 'derivation.json']
    pin_path = root/'corpus-pin.json'
    record, pin_sha = trainer.read_corpus_pin(pin_path)                              # exactly what M4 consumes
    assert pin_sha == sha(pin_path.read_bytes()) and record['stage'] == 'S0z' and record['status'] == 'passed'
    assert record['data_manifest']['sha256'] == b['manifest_sha'] and record['scientific_attempt'] is True
    assert record['schedule_derivation_sha256'] == b['derivation_sha'] == trainer.derive_schedules(record)['sha256']
    assert list(record['chain']) == list(ORDER) + ['S0z'] and record['s0f_pin_record']['sha256'] == sha(b['record'].read_bytes())
    assert record['reader']['t_f'] == {'path': str(Path(tmp_path)/'t-f'), 'head': json.loads(b['record'].read_bytes())['port']['head']} and record['reader']['data_root'] == str(b['out'])
    roster = record['roster_feature_target_sha256']
    assert (len(roster['old_train']), len(roster['advice']), len(roster['dev'])) == (10, 12, 4)
    assert len(set(sum(roster.values(), []))) == 26 and 'arrays' not in record
    assert json.loads((root/'audit.json').read_bytes())['status'] == 'passed'
    assert (root/'derivation.json').exists()


def test_failing_audit_publishes_no_corpus_pin_and_wrong_pins_refuse_before_writing(tmp_path, capsys):
    b = build(tmp_path/'a', MUTATIONS['advice_reordered'][0])
    # advice_reordered makes derive() refuse (it admits rosters): nothing is written, no pin.
    assert s0z.main(argv(b, tmp_path/'a', go(tmp_path/'a')), require_unit=False) == 2
    assert not (Path(tmp_path)/'a/s0z').exists()
    capsys.readouterr()
    b = build(tmp_path/'b')
    (b['out']/'after-admission.json').write_bytes(b'{"changed": true}')                # S0f output drifted after S0f
    assert s0z.main(argv(b, tmp_path/'b', go(tmp_path/'b')), require_unit=False) == 1
    root = Path(tmp_path)/'b/s0z'
    assert sorted(p.name for p in root.iterdir()) == ['audit.json', 'derivation.json']
    assert json.loads((root/'audit.json').read_bytes())['status'] == 'failed'
    capsys.readouterr()
    b = build(tmp_path/'c')
    assert s0z.main(argv(b, tmp_path/'c', go(tmp_path/'c'), **{'--expected-derivation-sha256': '0'*64}), require_unit=False) == 2
    assert 'expected pin' in json.loads(capsys.readouterr().out)['reason'] and not (Path(tmp_path)/'c/s0z').exists()


# ------------------------------------------------------------------- manifest binding

def test_s0z_manifest_binds_the_plan_the_command_the_s0f_evidence_and_the_budget():
    import re
    import run_research_stage as launcher
    folder = ROOT/'docs/reports/male-v4-s0z'
    text = (folder/'MANIFEST.md').read_text()
    raw, derived = (folder/'plan-only.prepared-in-agent-worktree.json').read_bytes(), (folder/'plan-only.json').read_bytes()
    agent = re.search(rb'"(/[^"]+?/)scripts/run_research_stage.py"', raw).group(1)
    cur = b'/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/'
    assert raw.replace(agent, cur) == derived and sha(raw) in text and sha(derived) in text
    plan = json.loads(derived)
    s0f = ROOT/'docs/reports/male-v4-s0f'
    record_sha = sha((s0f/'pin-record.json').read_bytes())
    manifest_sha = sha((s0f/'data-manifest.json').read_bytes())
    derivation_sha = sha((s0f/'derivation.json').read_bytes())
    assert plan['expected_manifest_sha256'] == manifest_sha and plan['expected_derivation_sha256'] == derivation_sha
    assert all(v in text for v in (record_sha, manifest_sha, derivation_sha))
    assert json.loads((s0f/'pin-record.json').read_text())['outputs']['data-manifest.json']['sha256'] == manifest_sha
    block = re.search(r'<!-- s0z-command -->\n```sh\n(.*?)\n```', text, re.S).group(1)
    words = block.replace('\\\n', ' ').split()
    unit, command = words[:words.index('--')], words[words.index('--') + 1:]
    flag = lambda name, w: w[w.index(name) + 1]
    stages = json.loads((ROOT/ctl.driver.PROTOCOL_PATH).read_text())['amendment_1']['lane_budget']['stage_costs_seconds']
    rows = {r['stage']: r for r in stages}
    row = rows['S0z']
    k, kill, worst = int(flag('--cpu-quota-k', unit)), int(flag('--runtime-max-sec', unit)), int(flag('--worst-case-cpu', unit))
    assert (k, kill, worst) == (row['cpu_quota_k'], row['runtime_max_sec_kill_target'], row['worst_case_cpu']) == (1, 300, 305)
    assert worst >= k * (kill + launcher.STOP_TIMEOUT) and s0z.UNIT['runtime_max_sec'] == kill
    planned = plan['unit_command'][plan['unit_command'].index('--') + 1:]
    given = command[:command.index('--go')]
    assert given[3:] == planned[3:planned.index('--go')]
    assert command[2] == cur.decode() + 'scripts/run_male_navigation_v4_s0z.py' and flag('--go', command) == flag('--go-record', unit)
    stage_root = Path(flag('--stage-root', command))
    assert stage_root.name == 'S0z' and stage_root.parent.name == 'male-v4-data' and not ctl.driver.under(flag('--receipt-dir', unit), stage_root)
    ledger = [json.loads(line) for line in (s0f/'research-ledger-snapshot.jsonl').read_text().splitlines() if line.strip()]
    charged = sum(v for key, v in launcher.charges(ledger).items() if key[0] == 'navigation')
    ahead = sum(rows[s]['worst_case_cpu'] for s in ('S0z', 'S1', 'S2'))
    assert round(charged, 3) == 604.510 and ahead == 6905 and round(charged - 1.832 + ahead, 3) == 7507.678 <= 14398.168
    for phrase in ('scientific_attempt": true', 'current_tree_head', 'declared_fields_sha256', 'must **not exist**', 'writer.lock',
                   'Throttling risk', 'not applicable', 'Post-run gate', 'no array bundle', 'identical to v3',
                   'not a new data-producing stage and needs no amendment', 'does **not** vouch', 'ends v4', '7,507.678',
                   'old N 2,117 q = 21 r = 1,623', 'd537a96', 'Ruling needed', 'Stage P must be re-run', 'owner_waivers'):
        assert phrase in text, phrase
    assert divmod(46080, 2117) == (21, 1623) and divmod(46080, 7197) == (6, 2898)


# ------------------------------------------------------------------- S0e-A document and chain audit

@pytest.mark.parametrize('name, mutate, check', [
    ('failed_status', lambda d: d.update(status='failed'), 's0e_audit'),
    ('failures', lambda d: d.update(failures=[{'name': 'x'}]), 's0e_audit'),
    ('not_covered', lambda d: d.update(not_covered=['finite arrays']), 's0e_audit'),
    ('missing_not_covered', lambda d: d.pop('not_covered'), 's0e_audit'),
    ('kind', lambda d: d.update(kind='other'), 's0e_audit'),
])
def test_s0e_audit_document_must_have_passed_with_nothing_uncovered(tmp_path, name, mutate, check):
    b = build(tmp_path, mutate_audit=mutate)
    assert check in failed(run_audit(b))
    if name == 'not_covered':
        assert 's0e_audit' not in failed(run_audit(b, waivers=('finite arrays',)))          # only an explicit owner waiver


@pytest.mark.parametrize('name, mutate', [
    ('commit', lambda r: r['chain']['S0d'].update(producing_commit='0' * 40)),
    ('link', lambda r: r.update(previous_record_sha256='0' * 64)),
    ('s0e_counts', lambda r: r['chain']['S0e']['counts'].update({'learner-3100-seed-10': 1})),
    ('old_manifest_sha', lambda r: r['chain']['S0c']['outputs']['data-manifest.json'].update(sha256='1' * 64)),
    ('audit_not_in_chain', lambda r: r['chain']['S0e']['outputs'].clear()),
])
def test_chain_audit_refuses_commit_linkage_count_and_old_manifest_faults(tmp_path, name, mutate):
    b = build(tmp_path, mutate_record=mutate)
    got = failed(run_audit(b))
    assert got & {'chain', 's0e_audit', 's0f_record'}, (name, got)


def test_audit_document_tampered_after_s0e_changes_its_sha(tmp_path):
    b = build(tmp_path)
    audit_path = Path(json.loads((b['out']/'data-manifest.json').read_bytes())['input_documents']['root_raw_audit']['path'])
    audit_path.write_bytes(audit_path.read_bytes() + b' ')
    assert 's0e_audit' in failed(run_audit(b))


def test_controller_pins_the_s0e_audit_and_refuses_an_unwaived_not_covered_item(tmp_path, capsys):
    b = build(tmp_path/'a', mutate_audit=lambda d: d.update(not_covered=['finite arrays']))
    assert s0z.main(argv(b, tmp_path/'a', go(tmp_path/'a')), require_unit=False) == 1
    assert not (Path(tmp_path)/'a/s0z/corpus-pin.json').exists()
    b = build(tmp_path/'b')
    assert s0z.main(argv(b, tmp_path/'b', go(tmp_path/'b')), require_unit=False) == 0
    pin = json.loads((Path(tmp_path)/'b/s0z/corpus-pin.json').read_text())
    manifest = json.loads((b['out']/'data-manifest.json').read_bytes())
    assert pin['s0e_audit']['sha256'] == manifest['input_documents']['root_raw_audit']['sha256'] and pin['owner_waivers'] == []


def test_go_expected_shas_must_equal_the_arguments_when_present(tmp_path, capsys):
    b = build(tmp_path)
    bad = go(tmp_path, data_manifest_sha256='0' * 64)
    assert s0z.main(argv(b, tmp_path, bad), require_unit=False) == 2
    assert 'differs from the expected pin' in json.loads(capsys.readouterr().out)['reason']
    assert not (Path(tmp_path)/'s0z').exists()


# ------------------------------------------------------------------- S1 manifest binding

def test_s1_manifest_binds_the_plan_the_pins_the_command_the_budget_and_the_lane_math():
    import re
    import run_research_stage as launcher
    folder = ROOT/'docs/reports/male-v4-s1'
    text = (folder/'MANIFEST.md').read_text()
    plan_raw = (folder/'plan-only.json').read_bytes()
    plan = json.loads(plan_raw)
    assert sha(plan_raw) in text and plan['mode'] == 'plan-only' and plan['stage'] == 'S1' and plan['protocol_sha256'] == PROTOCOL
    s0z = ROOT/'docs/reports/male-v4-s0z'
    pin_sha, audit_sha = (sha((s0z/n).read_bytes()) for n in ('corpus-pin.json', 'audit.json'))
    derivation_sha = json.loads((s0z/'corpus-pin.json').read_text())['schedule_derivation_sha256']   # sha of derive()'s canonical bytes
    assert plan['corpus_pin_sha256'] == pin_sha and plan['schedule_derivation_sha256'] == derivation_sha
    assert all(v in text for v in (pin_sha, audit_sha, derivation_sha)) and pin_sha.startswith('f6115c1e') and audit_sha.startswith('2bef1569')
    pin = json.loads((s0z/'corpus-pin.json').read_text())
    assert pin['schedule_derivation_sha256'] == derivation_sha and pin['audit']['sha256'] == audit_sha
    manifest_raw = (ROOT/'docs/reports/male-v4-s0f/data-manifest.json').read_bytes()
    assert sha(manifest_raw) == pin['data_manifest']['sha256'] and sha(manifest_raw) in text
    derived = budget.derive(manifest_raw, sha(manifest_raw))
    assert derived['sha256'] == derivation_sha and plan['schedule_derivation'] == derived['document']
    assert plan['models'] == trainer.plan()['models'] and len(plan['models']) == 6
    assert (pin['reader']['t_f']['head'], pin['reader']['t_h']['head']) == ('88c1a0f6f53274fe663f4cdad3be5ae2743af558', '0789b2ed54117c01c40ab5818148cc0515eb4fb5')
    for head in (pin['reader']['t_f']['head'], pin['reader']['t_h']['head']): assert head in text
    for receipt in ('stage-p', 'stage-p2'):
        assert sha((ROOT/f'docs/reports/male-v4-{receipt}/launcher-receipt.json').read_bytes()) in text
    assert sha((ROOT/'docs/plans/m7-navigation-v4-pins/declared-fields.json').read_bytes()).startswith('8877390c')
    block = re.search(r'<!-- s1-command -->\n```sh\n(.*?)\n```', text, re.S).group(1)
    words = block.replace('\\\n', ' ').split()
    unit, command = words[:words.index('--')], words[words.index('--') + 1:]
    flag = lambda name, w: w[w.index(name) + 1]
    stages = json.loads((ROOT/ctl.driver.PROTOCOL_PATH).read_text())['amendment_1']['lane_budget']['stage_costs_seconds']
    rows = {r['stage']: r for r in stages}
    k, kill, worst = int(flag('--cpu-quota-k', unit)), int(flag('--runtime-max-sec', unit)), int(flag('--worst-case-cpu', unit))
    assert (flag('--lane', unit), flag('--stage', unit)) == ('navigation', 'S1')
    assert (k, kill, worst) == (rows['S1']['cpu_quota_k'], rows['S1']['runtime_max_sec_kill_target'], rows['S1']['worst_case_cpu']) == (1, 2160, 2165)
    assert worst >= k * (kill + launcher.STOP_TIMEOUT)
    assert command[0] == '/usr/bin/env' and 'CUDA_VISIBLE_DEVICES=' in command and 'OMP_NUM_THREADS=1' in command   # hooks.runtime needs CUDA hidden
    assert flag('--corpus-pin', command).endswith('male-v4-data/S0z/corpus-pin.json') and flag('--go', command) == flag('--go-record', unit)
    output = Path(flag('--output', command))
    assert output.parent.name == 'S1' and output.parent.parent.name == 'male-v4-data' and not ctl.driver.under(output, ROOT)
    ledger = [json.loads(line) for line in (ROOT/'docs/reports/male-v4-stage-p2/research-ledger-snapshot.jsonl').read_text().splitlines() if line.strip()]
    charged = sum(v for key, v in launcher.charges(ledger).items() if key[0] == 'navigation')
    ahead = rows['S1']['worst_case_cpu'] + rows['S2']['worst_case_cpu']
    v4 = charged - 1.832
    assert round(charged, 3) == 635.154 and round(v4, 3) == 633.322 and ahead == 6600 and round(v4 + ahead, 3) == 7233.322 <= 14398.168
    assert 14398.168 - rows['S3']['worst_case_cpu'] == 5643.168
    for phrase in ('scientific_attempt": true', 'current_tree_head', 'declared_fields_sha256', 'must **not\n   exist**', 'writer lock', 'Throttling / threads',
                   'honest CPU estimate', 'terminal-only', 'ends v4', '7,233.322', '5,643.168', 'one attempt', 'CUDA_VISIBLE_DEVICES'):
        assert phrase.replace('\n   ', ' ') in text.replace('\n   ', ' ') or phrase in text, phrase
