import json
import os
from pathlib import Path
import sys
import uuid

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'src'))
from paper.studies.authority_component_v1 import runner  # noqa: E402
from paper.studies.authority_replay_v1 import fault_matrix  # noqa: E402

PROTOCOL = json.loads(runner.PROTOCOL.read_text())
ARMS = {name: (src, tested) for name, src, tested in runner.arms()}


def snap(tag):
    """Minimal snapshot shape with every top-level key; values tagged by origin."""
    return {'schema_version': 1, 'identity': {'model': 'm'}, 'integration_enum': 1, 'teacher': None,
            'native_data': f'{tag}-native'.encode(), 'native_sha256': f'{tag}-sha', 'integration': np.array([1.0 if tag == 's' else 2.0]),
            'environment': {'_t': tag}, 'observation': {'cam': tag},
            'policy': {'hidden': f'{tag}-h', 'failure_diagnostics': {}, 'left': f'{tag}-l', 'right': f'{tag}-r'},
            'rng': {'python': tag}, 'application': {'revision': tag, 'pending_commands': []}}


def origin(snapshot):
    p = snapshot['policy']
    return {'physics': snapshot['native_sha256'][0], 'environment': snapshot['environment']['_t'],
            'observation': snapshot['observation']['cam'], 'controller_hidden': p['hidden'][0],
            'controller_retina': p['left'][0] + p['right'][0], 'rng': snapshot['rng']['python'],
            'application': snapshot['application']['revision']}


def test_arms_match_protocol_and_are_fixed():
    assert len(ARMS) == PROTOCOL['arms_per_seed'] == 16 == len(runner.arms())
    assert set(runner.COMPONENTS) == set(PROTOCOL['components'])
    every = frozenset(runner.COMPONENTS)
    assert ARMS['full'] == (every, frozenset()) and ARMS['pose_only'] == ({'physics'}, every - {'physics'})
    assert all(ARMS[f'loo:{c}'] == (every - {c}, {c}) for c in runner.COMPONENTS)
    assert all(ARMS[f'add:{c}'] == ({'physics', c}, {c}) for c in runner.COMPONENTS[1:])
    assert ARMS['add:controller_inputs'][0] == {'physics', 'observation', 'controller_hidden', 'controller_retina'}
    assert 'add:physics' not in ARMS


@pytest.mark.parametrize('name', list(ARMS))
def test_hybrid_takes_exactly_named_components_from_source(name):
    source, donor = snap('s'), snap('d')
    out = runner.hybrid(source, donor, ARMS[name][0])
    for component, value in origin(out).items():
        want = 's' if component in ARMS[name][0] else 'd'
        assert value == (want * 2 if component == 'controller_retina' else want), (name, component)
    assert set(out) == set(source) and out['policy'].keys() == source['policy'].keys()
    # Physics moves as one unit, so restore's native/integration audit stays consistent.
    assert {out['native_sha256'][0], str(int(out['integration'][0]))} in ({'s', '1'}, {'d', '2'})
    assert origin(source) == origin(snap('s')) and origin(donor) == origin(snap('d'))  # inputs unmutated


def test_hybrid_rejects_unknown_component():
    with pytest.raises(ValueError):
        runner.hybrid(snap('s'), snap('d'), {'teacher'})


def test_exercised_asks_only_about_tested_components():
    src = dict.fromkeys(runner.COMPONENTS, 'a')
    don = {**src, 'observation': 'b'}
    assert runner.exercised(src, don, frozenset()) is None
    assert runner.exercised(src, don, {'observation'}) is True
    assert runner.exercised(src, don, {'rng'}) is False  # add:rng with equal rng digests is not a finding
    assert runner.exercised(src, don, ARMS['pose_only'][1]) is True


def test_stop_rule_uses_timeout_first_then_worst_seed():
    res = {'seed_timeout_seconds': 900, 'study_ceiling_cpu_seconds': 4500}
    assert runner.should_start(0, None, res) and runner.should_start(3600, None, res)
    assert not runner.should_start(3601, None, res)
    assert runner.should_start(4000, 500, res) and not runner.should_start(4001, 500, res)
    used, worst, started = 0.0, None, 0
    for cpu in [800, 800, 800, 800, 800, 800]:
        if not runner.should_start(used, worst, res):
            break
        used, worst, started = used + cpu, max(worst or 0, cpu), started + 1
    assert started == 5 and used <= res['study_ceiling_cpu_seconds']


def row(name, **kw):
    base = {'status': 'completed', 'restore_refused': False, 'exercised': True, 'first_action_changed': False,
            'scientific_first_divergence': None, 'application_first_divergence': None}
    return {**base, **kw}


def rows(full_ok=True, pose_changed=True, loo=(), loo_horizon=(), add_fix=(), refused=(), unexercised=(), failed=()):
    out = {}
    for name in ARMS:
        c = name.split(':')[-1]
        changed = (name == 'pose_only' and pose_changed) or (name.startswith('loo:') and c in loo) or (
            name.startswith('add:') and pose_changed and c not in add_fix)
        horizon = {'tick': 3} if (name.startswith('loo:') and c in (*loo, *loo_horizon)) else None
        out[name] = row(name, first_action_changed=changed, restore_refused=name in refused,
                        exercised=None if name == 'full' else name not in unexercised,
                        status='runtime_failure' if name in failed else 'completed',
                        scientific_first_divergence={'tick': 0} if (name == 'full' and not full_ok) else horizon)
    return out


def test_classify_attributes_necessary_and_repairing_components():
    result = runner.classify(rows(loo={'observation', 'controller_hidden'}, loo_horizon={'physics'},
                                  add_fix={'controller_inputs'}, refused={'loo:application'},
                                  unexercised={'loo:rng'}, failed={'loo:environment'}))
    assert result['h1_full_agrees'] and result['h2_pose_only_changes_first_action']
    first, horizon = result['necessary_first_action'], result['necessary_horizon']
    assert first['observation'] is True and first['physics'] is False and horizon['physics'] is True
    assert first['rng'] == 'not_exercised' and first['application'] == 'refused' and first['environment'] == 'runtime_failure'
    assert horizon['controller_retina'] is False
    repairs = result['repairs_first_action']
    assert repairs['controller_inputs'] is True and repairs['observation'] is False and len(repairs) == 7


def test_classify_withholds_attribution_when_full_arm_diverges():
    result = runner.classify(rows(full_ok=False, loo={'observation'}))
    assert not result['h1_full_agrees']
    for key in ('necessary_first_action', 'necessary_horizon', 'repairs_first_action'):
        assert set(result[key].values()) == {None}


def test_classify_requires_full_arm_application_agreement():
    data = rows()
    data['full']['application_first_divergence'] = {'tick': 0}
    assert not runner.classify(data)['h1_full_agrees']


def test_classify_withholds_repair_when_pose_only_does_not_diverge():
    assert set(runner.classify(rows(pose_changed=False))['repairs_first_action'].values()) == {None}


class FakeEngine:
    """Tick-0 action reads observation+hidden+retina before stepping; every component then advances.
    rng never changes, so its arms must come out not_exercised."""
    fail_arm_restores = set()
    terminate_after = None
    opened = []

    def __init__(self, run):
        FakeEngine.opened.append(run)
        uuid.UUID(run.name)  # Engine.open parses run_id as a UUID
        self.s = dict.fromkeys(runner.COMPONENTS, 0)
        self.total_tick, self.phase, self.last = 0, 'paused', None

    def restore_branch(self, snapshot):
        if len(FakeEngine.opened) - 2 in FakeEngine.fail_arm_restores:
            raise RuntimeError('injected')
        p = snapshot['policy']
        self.s = {'physics': int(snapshot['integration'][0]), 'environment': snapshot['environment'],
                  'observation': snapshot['observation'], 'controller_hidden': p['hidden'],
                  'controller_retina': p['left'], 'rng': snapshot['rng'], 'application': snapshot['application']['v']}
        self.total_tick = snapshot['application']['tick']

    def step(self):
        if FakeEngine.terminate_after is not None and self.total_tick >= FakeEngine.terminate_after:
            self.phase = 'terminated'
            return
        s = self.s
        self.last = {'action': np.array([s['observation'] * 100 + s['controller_hidden'] * 10 + s['controller_retina']], np.float32),
                     'qpos': np.array([s['physics'] + s['environment']], np.float64), 'revision': np.array(s['application'], np.int64)}
        for c in runner.COMPONENTS:
            if c != 'rng':
                s[c] += 1
        self.total_tick += 1

    def close(self):
        pass


def fake_capture(engine):
    s = engine.s
    return {'schema_version': 1, 'identity': {'m': 1}, 'integration_enum': 1, 'teacher': None,
            'native_data': bytes([s['physics']]), 'native_sha256': str(s['physics']), 'integration': np.array([float(s['physics'])]),
            'environment': s['environment'], 'observation': s['observation'],
            'policy': {'hidden': s['controller_hidden'], 'failure_diagnostics': {}, 'left': s['controller_retina'], 'right': 0},
            'rng': s['rng'], 'application': {'v': s['application'], 'tick': engine.total_tick, 'pending_commands': []}}


@pytest.fixture
def fake(monkeypatch):
    FakeEngine.opened, FakeEngine.fail_arm_restores, FakeEngine.terminate_after = [], set(), None
    monkeypatch.setattr(fault_matrix, '_open', lambda repo, assets, run, seed: FakeEngine(run))
    monkeypatch.setattr(fault_matrix, '_capture', fake_capture)
    monkeypatch.setattr(fault_matrix, '_command', lambda engine, kind: engine.step())
    monkeypatch.setattr(fault_matrix, '_tick_state', lambda engine: dict(engine.last))
    return FakeEngine


def test_run_seed_end_to_end_with_fake_engine(tmp_path, fake):
    result = {r['arm']: r for r in runner.run_seed(7, tmp_path / 'seed', None, None, horizon=4, prefix=3)}
    assert len(result) == 16 and len(fake.opened) == 17 and len({p.name for p in fake.opened}) == 17
    assert all(r['status'] == 'completed' and r['ticks'] == 4 for r in result.values())
    assert result['full']['scientific_first_divergence'] is None and result['full']['first_action_changed'] is False
    assert result['pose_only']['first_action_changed'] is True
    assert result['loo:physics']['first_action_changed'] is False and result['loo:physics']['scientific_first_divergence']['field'] == 'qpos'
    assert result['add:controller_inputs']['first_action_changed'] is False
    assert result['add:rng']['exercised'] is False and result['loo:rng']['exercised'] is False
    analysis = json.loads((tmp_path / 'seed/analysis.json').read_text())
    assert analysis['h1_full_agrees'] and analysis['repairs_first_action']['controller_inputs'] is True
    assert analysis['necessary_first_action']['rng'] == 'not_exercised'
    precheck = json.loads((tmp_path / 'seed/precheck.json').read_text())
    assert set(precheck['runs']) == {'source', *ARMS} and precheck['differs']['rng'] is False


def test_run_seed_isolates_one_failing_arm(tmp_path, fake):
    fake.fail_arm_restores = {3}
    result = {r['arm']: r for r in runner.run_seed(7, tmp_path / 'seed', None, None, horizon=2, prefix=1)}
    failed = runner.arms()[3][0]
    assert result[failed]['restore_refused'] and 'injected' in result[failed]['refusal']
    assert all(r['status'] == 'completed' for r in result.values()) and len(result) == 16


def test_run_seed_refuses_ticks_that_do_not_advance(tmp_path, fake):
    # Source reaches tick 3 (prefix 1 + horizon 2). Arms taking donor application restart at tick 2,
    # so their second step would not advance: retained as runtime_failure, other arms unaffected.
    fake.terminate_after = 3
    result = {r['arm']: r for r in runner.run_seed(7, tmp_path / 'seed', None, None, horizon=2, prefix=1)}
    donor_app = {name for name, (src, _) in ARMS.items() if 'application' not in src}
    assert donor_app and len(result) == 16
    for name, r in result.items():
        if name in donor_app:
            assert r['status'] == 'runtime_failure' and 'did not advance' in r['reason'] and r['ticks'] == 1
        else:
            assert r['status'] == 'completed' and r['ticks'] == 2
    fake.terminate_after = 2  # the source itself cannot finish its horizon: the seed fails loudly
    with pytest.raises(ValueError, match='did not advance'):
        runner.run_seed(7, tmp_path / 'seed2', None, None, horizon=2, prefix=1)


def test_collect_seed_pads_to_fixed_denominator(tmp_path):
    seed_dir = tmp_path / 'seed-3'
    assert len(runner.collect_seed(3, seed_dir, 'not_started', 'ceiling')) == 16
    seed_dir.mkdir()
    runner.append_row(seed_dir / 'rows.jsonl', {**runner.placeholder(3, 'full', set(), 'completed', None)})
    padded = runner.collect_seed(3, seed_dir, 'failed', 'child exit 1')
    assert len(padded) == 16 and len({r['unit_id'] for r in padded}) == 16
    assert sum(r['status'] == 'failed' for r in padded) == 15


def test_real_run_refuses_without_matching_owner_go(tmp_path, monkeypatch):
    go = tmp_path / 'go.json'
    monkeypatch.setattr(runner, '__file__', str(tmp_path / 'runner.py'))
    with pytest.raises(ValueError, match='go.json missing'):
        runner._go('abc')
    go.write_text(json.dumps({'go': True, 'protocol_sha256': 'other', 'by': 'x', 'date': 'd', 'words': 'w'}))
    with pytest.raises(ValueError, match='does not approve'):
        runner._go('abc')
    go.write_text(json.dumps({'go': True, 'protocol_sha256': 'abc'}))
    with pytest.raises(ValueError, match='by, date and words'):
        runner._go('abc')
    go.write_text(json.dumps({'go': True, 'protocol_sha256': 'abc', 'by': 'x', 'date': 'd', 'words': 'w'}))
    assert runner._go('abc')['go'] is True


def test_protocol_budget_and_any_committed_go_is_well_formed():
    assert PROTOCOL['seeds'] == [0, 1, 2, 3, 4, 5]
    res = PROTOCOL['resources']
    assert res['lane'] == 'final' and res['study_ceiling_cpu_seconds'] <= res['lane_cap_cpu_seconds'] - res['lane_used_before_cpu_seconds']
    go = runner.PROTOCOL.with_name('go.json')
    if go.exists():
        runner._go(runner.sha256_file(runner.PROTOCOL))


@pytest.mark.skipif(os.environ.get('PALIMPSEST_COMPONENT_SMOKE') != '1', reason='real FLYNN smoke is opt in (needs owner OK)')
def test_real_flynn_smoke_on_non_study_seed(tmp_path):
    import resource
    seed = 1000  # never a study seed
    assert seed not in PROTOCOL['seeds']
    base = tmp_path / 'base'
    base.mkdir()
    repo, assets = fault_matrix._copy_runtime(base)
    result = {r['arm']: r for r in runner.run_seed(seed, tmp_path / 'seed', repo, assets, horizon=2, prefix=2)}
    usage = resource.getrusage(resource.RUSAGE_SELF)
    print(json.dumps({'cpu_seconds': usage.ru_utime + usage.ru_stime, 'peak_rss_kib': usage.ru_maxrss}))
    assert len(result) == 16 and all(r['status'] == 'completed' for r in result.values())
    assert not result['full']['restore_refused'] and result['full']['scientific_first_divergence'] is None
