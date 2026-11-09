"""MaleCNS v4 Amendment 1 reconstructed controllers: S0d, S0e launcher, S0e-D, S0e-A, S0e-I.

No producer, simulator or training runs and no real data is opened. Every child is a tiny
synthetic fake driver that mimics producer outputs; the ported ``_gate`` (T-e) and
``admit_collection`` (T-f) are compiled out of the port blobs and fed the controllers'
documents, so the field sets are checked by the consumers themselves.
"""
import ast
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import male_navigation_v4_controls as ctl  # noqa: E402
import run_male_navigation_v4_s0d as s0d  # noqa: E402
import run_male_navigation_v4_s0e as s0e  # noqa: E402

pytestmark = pytest.mark.process_isolated
PROTOCOL_SHA = ctl.driver.PROTOCOL_SHA256
PORTS = ctl.driver.load_ports()
ADVICE_CASES = ctl.driver.ADVICE_CASES
V2_BASELINE, V2_DEV, V2_RECOVERY = [248]*7 + [247], [307]*4, [67, 67]
V2_ADVICE = [424]*4 + [423]*8


def sha(payload): return hashlib.sha256(payload).hexdigest()


def git(cwd, *args):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


def blob(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:{path}'], cwd=ROOT, capture_output=True, check=True).stdout


def extract(source, names, namespace):
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<extracted>', 'exec'), namespace)
    return namespace


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=1) + '\n').encode(); path.write_bytes(raw)
    return {'path': str(path), 'sha256': sha(raw)}


def go(tmp_path, stage, **changes):
    record = {'decision': 'GO', 'stage': stage, 'lane': 'navigation', 'protocol_sha256': PROTOCOL_SHA,
              'granted_by': 'owner', 'granted_at': '2026-11-09T00:00:00Z', **changes}
    return Path(write(tmp_path/f'go-{stage}-{len(changes)}.json', record)['path'])


FAKE_DRIVER = r'''
import hashlib, json, subprocess, sys, time
from pathlib import Path
here = Path(__file__).parent
behaviour = json.loads((here/'behaviour.json').read_text())
argv = sys.argv[1:]; producer = argv[argv.index('--') + 1:]
opts = dict(zip(producer[::2], producer[1::2]))
key = opts.get('--training-seed', 'collect')
b = behaviour.get(key, behaviour.get('default', {}))
with (here/'calls.jsonl').open('a') as log: log.write(json.dumps({'key': key, 'argv': argv}) + '\n')
time.sleep(b.get('sleep', 0))
for path in b.get('touch', []): Path(path).write_text('changed')
if b.get('orphan'):
    orphan = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'], start_new_session=True)
    (here/'orphan.pid').write_text(str(orphan.pid))
out = Path(opts['--output']); out.mkdir()
if key != 'collect':
    (out/'report.json').write_text(json.dumps({'status': 'completed-research-training', 'seed': key}))
else:
    ticks = b.get('ticks', [5] * 12)
    cases = {}
    for (case, n) in zip(behaviour['cases'], ticks):
        stage = out/case; run = stage/('run-' + case); (run/'snapshots').mkdir(parents=True)
        (run/'snapshots'/'initial.snp').write_bytes(case.encode())
        (stage/'result.json').write_text(json.dumps({'status': 'completed-recording', 'rows': [{'t': i} for i in range(n)],
            'engine_closed': True, 'callback_restored': True, 'outcome': 'time_limit', 'contact_incidence': {'n': n}}))
        cases[case] = {'status': 'completed-recording', 'outcome': 'time_limit', 'contact_incidence': {'n': n}, 'run': str(run)}
    files = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    report = {'status': 'completed-collection', 'profile': 'P', 'study_sha256': 'S', 'contact_profile_sha256': 'C',
              'qualification_claims': [], 'owners_completed': 12, 'numeric_ticks': b.get('numeric_ticks', sum(ticks)),
              'cases': cases, 'source_pins': {'a': 1}, 'final_source_pins': {'a': 1}, 'assets_before': {'ok': True},
              'assets_after': {'ok': True}, 'identities_before': {'10': 'i'}, 'identities_after': {'10': 'i'}, 'artifacts_sha256': files}
    (out/'report.json').write_text(json.dumps(report))
sys.exit(b.get('exit', 0))
'''

RUNNER = ('import json, sys; sys.path.insert(0, sys.argv[1]); m = __import__(sys.argv[2]); '
          'sys.exit(m.main(json.loads(sys.argv[3]), **json.loads(sys.argv[4])))')


def run_cli(module, argv, **overrides):
    """main(argv, **overrides) in a fresh child: subreaper, samplers and reaping never touch pytest."""
    done = subprocess.run([sys.executable, '-B', '-c', RUNNER, str(ROOT/'scripts'), module, json.dumps([str(a) for a in argv]),
                           json.dumps(overrides)], capture_output=True, text=True, timeout=180, env=ctl.child_env())
    try: return done.returncode, json.loads(done.stdout)
    except json.JSONDecodeError: raise AssertionError(done.stdout + done.stderr) from None


@pytest.fixture
def fake(tmp_path):
    """A fake driver whose per-seed behaviour the test sets; returns (driver path, set_behaviour)."""
    folder = tmp_path/'fake'; folder.mkdir()
    (folder/'driver.py').write_text(FAKE_DRIVER)

    def behave(**behaviour):
        (folder/'behaviour.json').write_text(json.dumps({'cases': list(ADVICE_CASES), **behaviour}))
    behave()
    return folder, behave


TRACKED = {'src/palimpsest/male_model.py': b'model', 'scripts/collect_male_recovery.py': b'collector',
           'scripts/prepare_male_recovery_data.py': b'adapter', 'scripts/train_male_reduced.py': b'fitter',
           'scripts/train_male_recovery.py': b'trainer', 'uv.lock': b'lock'}


@pytest.fixture
def worktree(tmp_path):
    repo = tmp_path/'worktree'; repo.mkdir()
    git(repo, 'init', '-q')
    for rel, payload in TRACKED.items():
        (repo/rel).parent.mkdir(parents=True, exist_ok=True); (repo/rel).write_bytes(payload)
    (repo/'.git/info/exclude').write_text('upstream/\nruns/\n')
    git(repo, 'add', '-A'); git(repo, 'commit', '-qm', 'fake port tree')
    (repo/'upstream/fly-gym').mkdir(parents=True); (repo/'upstream/fly-gym/cell.py').write_text('cell')
    for name in ('raw', 'model', 'runtime'):
        (tmp_path/name).mkdir(); (tmp_path/name/f'{name}.bin').write_text(name)
    write(tmp_path/'s0c.pin-record.json', {'stage': 'S0c'})
    write(tmp_path/'data-manifest.json', {'status': 'prepared-research-only'})
    return repo


# =================================================================== S0d

COUNTS = {'tracked': len(TRACKED), 'upstream': 1}


def s0d_argv(tmp_path, worktree, go_path=None):
    argv = ['--worktree', worktree, '--previous-pins', tmp_path/'s0c.pin-record.json',
            '--data-manifest', tmp_path/'data-manifest.json', '--output-root', worktree/'runs/s0d',
            '--control-root', worktree/'runs/s0d-control', '--raw-documents', tmp_path/'raw',
            '--model-production', tmp_path/'model', '--runtime', tmp_path/'runtime']
    return [str(a) for a in ([] if go_path is None else ['--go', go_path]) + argv]


def s0d_run(tmp_path, worktree, fake, **overrides):
    code, out = run_cli('run_male_navigation_v4_s0d', s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d')),
                        driver_path=str(fake[0]/'driver.py'), expected_head=git(worktree, 'rev-parse', 'HEAD'),
                        expected_counts=COUNTS, require_unit=False, **overrides)
    control = worktree/'runs/s0d-control'
    terminal = json.loads((control/'terminal.json').read_text()) if (control/'terminal.json').exists() else None
    supervisor = json.loads((control/'outer-supervisor/supervisor.json').read_text())
    return code, out, terminal, supervisor


def test_s0d_constants_are_bound_to_the_surviving_recovery_training_evidence():
    evidence = json.loads(blob('217cbee', 'docs/reports/m7-recovery-training.json'))
    assert s0d.LIMITS == {k: evidence['limits'][k] for k in ('pair_internal_seconds', 'pair_supervised_seconds',
                                                             'stage_internal_seconds', 'stage_supervised_seconds')}
    assert s0d.V2_REFERENCE_COUNTS == {'tracked': 355, 'upstream': 122, 'raw_documents': 181,
                                       'model_production': 16, 'runtime': 7}
    assert evidence['scoped_identity_counts'] == {'tracked': 355, 'upstream': 122, 'raw_documents_and_files': 181,
                                                  'model_and_production': 16, 'runtime_files': 7}
    assert s0d.SEEDS == (10, 11, 12) and ctl.SAMPLE_SECONDS == 0.25
    # 355 = every tracked regular file at 19d275d (the T-d port adds no file); asserted at run time.
    tracked = subprocess.run(['git', 'ls-tree', '-r', '19d275d'], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    assert sum(not line.startswith('160000') for line in tracked) == s0d.EXPECTED_COUNTS['tracked'] == 355
    assert s0d.EXPECTED_COUNTS['upstream'] == 122
    assert set(evidence['cleanup']) >= {'sampler_stopped', 'sample_errors', 'forced_signals', 'survivors'}
    assert s0d.UNIT == {'stage': 'S0d', 'runtime_max_sec': 2160, 'k': 1}


def test_s0d_default_is_plan_only_and_lists_three_seed_runs_in_order(tmp_path, worktree, fake, capsys):
    code = s0d.main(s0d_argv(tmp_path, worktree), driver_path=str(fake[0]/'driver.py'))
    plan = json.loads(capsys.readouterr().out)
    assert code == 0 and plan['mode'] == 'plan-only' and plan['stage'] == 'S0d'
    assert [p['training_seed'] for p in plan['pairs']] == [10, 11, 12]
    for seed, pair in zip((10, 11, 12), plan['pairs']):
        tail = pair['command'][pair['command'].index('--') + 1:]
        assert tail == ['--data-manifest', str(tmp_path/'data-manifest.json'), '--training-seed', str(seed),
                        '--output', str(worktree/f'runs/s0d/seed-{seed}')]
    assert plan['unit_command'][plan['unit_command'].index('--runtime-max-sec') + 1] == '2160'
    assert plan['unit_command'][plan['unit_command'].index('--worst-case-cpu') + 1] == '2165'
    assert not (worktree/'runs').exists() and not (fake[0]/'calls.jsonl').exists()


@pytest.mark.parametrize('mutate, reason', [
    (lambda tmp, argv: argv + ['--plan-only'], 'mutually exclusive'),
    (lambda tmp, argv: [a.replace(str(tmp/'go-S0d-0.json'), str(go(tmp, 'S0e'))) for a in argv], 'does not name stage S0d'),
    (lambda tmp, argv: [a.replace(str(tmp/'go-S0d-0.json'), str(go(tmp, 'S0d', protocol_sha256='0'*64))) for a in argv],
     'does not name stage S0d'),
    (lambda tmp, argv: [a.replace(str(tmp/'go-S0d-0.json'), str(go(tmp, 'S0d', decision='NO-GO'))) for a in argv],
     'does not name stage S0d'),
    (lambda tmp, argv: [os.path.relpath(a) if a == str(tmp/'runtime') else a for a in argv], 'absolute'),
])
def test_s0d_go_gating_and_absolute_paths_refuse_before_any_child(tmp_path, worktree, fake, capsys, mutate, reason):
    argv = mutate(tmp_path, s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d')))
    code = s0d.main(argv, driver_path=str(fake[0]/'driver.py'), expected_head=git(worktree, 'rev-parse', 'HEAD'),
                    require_unit=False)
    out = json.loads(capsys.readouterr().out)
    assert code == 2 and out['status'] == 'refused' and reason in out['reason']
    assert not (worktree/'runs').exists() and not (fake[0]/'calls.jsonl').exists()


def test_s0d_refuses_outside_a_research_stage_unit_and_a_head_other_than_the_t_d_port(tmp_path, worktree, fake, capsys):
    argv = s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d'))
    assert s0d.main(argv, driver_path=str(fake[0]/'driver.py'), expected_head=git(worktree, 'rev-parse', 'HEAD')) == 2
    assert 'run_research_stage' in json.loads(capsys.readouterr().out)['reason']
    assert s0d.main(argv, driver_path=str(fake[0]/'driver.py'), require_unit=False) == 2   # default: ports.json T-d
    assert PORTS['trees']['T-d']['port_commit'] in json.loads(capsys.readouterr().out)['reason']
    assert not (worktree/'runs').exists()


def test_s0d_outputs_and_control_must_be_fresh_disjoint_and_inside_the_port_worktree(tmp_path, worktree, fake, capsys):
    head = git(worktree, 'rev-parse', 'HEAD')
    for old, new, reason in ((str(worktree/'runs/s0d-control'), str(tmp_path/'elsewhere'), 'inside the port worktree'),
                             (str(worktree/'runs/s0d-control'), str(worktree/'runs/s0d/control'), 'disjoint')):
        argv = [a.replace(old, new) for a in s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d'))]
        assert s0d.main(argv, driver_path=str(fake[0]/'driver.py'), expected_head=head, require_unit=False) == 2
        assert reason in json.loads(capsys.readouterr().out)['reason']
    (worktree/'runs/s0d').mkdir(parents=True)
    assert s0d.main(s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d')), driver_path=str(fake[0]/'driver.py'),
                    expected_head=head, require_unit=False) == 2
    assert 'fresh' in json.loads(capsys.readouterr().out)['reason']


def gate_namespace():
    ns = {'Path': Path, 'math': math, 'MAX_JSON': 4*1024**2, 'PAIR_SEEDS': (10, 11, 12),
          'artifacts': types.SimpleNamespace(_read=lambda p, cap=None: Path(p).read_bytes(), _json=json.loads,
                                             _safe_path=lambda p: Path(p).absolute()),
          'male_policy': types.SimpleNamespace(_sha=sha)}
    return extract(blob(PORTS['trees']['T-e']['branch'], 'src/palimpsest/male_recovery_research.py'), ('read_pin', '_gate'), ns)


def gate_index(tmp_path, worktree, monkeypatch):
    """The S0d recovery-index values plus synthetic data/learning documents the ported _gate also reads."""
    values = json.loads((worktree/'runs/s0d-control/recovery-index-values.json').read_text())
    data = write(tmp_path/'s0c/data-manifest.json', {
        'status': 'prepared-research-only', 'counts': {'train': 2117, 'dev': 1228, 'held_out': 0},
        'ordered_sources': {'train': [{'ticks': n} for n in V2_BASELINE + V2_RECOVERY],
                            'dev': [{'ticks': n} for n in V2_DEV], 'held_out': []},
        'recovery_admission': [{'windows': [32, 32, 3]}]*2})
    learning = write(tmp_path/'v4/m7-recovery-learning-protocol.json', {
        'counts': {'train': 2117, 'dev': 1228, 'per_source': {'baseline_train': V2_BASELINE, 'dev': V2_DEV}},
        'recovery_ticks_each': V2_RECOVERY})
    locator = write(tmp_path/'v4/port-pins.json', {'documents': {'m7-recovery-learning-protocol.json': learning}})
    monkeypatch.setenv(PORTS['locator']['env'], locator['path'])
    shas = {rel: sha(payload) for rel, payload in TRACKED.items()}
    code = {'reader': {'current_reader_sources': {k: shas[k] for k in ('src/palimpsest/male_model.py',
                                                                      'scripts/collect_male_recovery.py')},
                       'adapter_sha256': shas['scripts/prepare_male_recovery_data.py']},
            'trainer': {k: shas[k] for k in ('scripts/train_male_recovery.py', 'scripts/train_male_reduced.py', 'uv.lock')}}
    return {**values, 'training_source_code': code, 'data_manifest': data}


def test_s0d_normal_run_emits_the_full_gate_field_set_and_passes_the_ported_gate(tmp_path, worktree, fake, monkeypatch):
    fake[1](default={'sleep': 0.6})
    code, out, terminal, supervisor = s0d_run(tmp_path, worktree, fake)
    assert code == 0 and out['status'] == 'completed', out
    calls = [json.loads(line) for line in (fake[0]/'calls.jsonl').read_text().splitlines()]
    assert [c['key'] for c in calls] == ['10', '11', '12']                       # each seed once, in order
    assert all(c['argv'][:2] == ['--stage', 'S0d'] and '--go' in c['argv'] for c in calls)
    assert terminal['status'] == 'passed-research-training' and terminal['head'] == git(worktree, 'rev-parse', 'HEAD')
    assert terminal['inventories_unchanged'] is True and terminal['completed_pair_content_unchanged'] is True
    assert terminal['before_inventory_sha256'] == terminal['after_inventory_sha256']
    assert set(terminal['inventory_counts']) == set(s0d.INVENTORY_PARTS)
    assert {k: terminal['cleanup'][k] for k in ('sampler_stopped', 'sample_errors', 'forced_signals', 'survivors')} == \
        {'sampler_stopped': True, 'sample_errors': [], 'forced_signals': [], 'survivors': []}
    assert [(p['training_seed'], p['status'], p['supervision']['status'], p['supervision']['returncode'])
            for p in terminal['pairs']] == [(s, 'completed', 'completed', 0) for s in (10, 11, 12)]
    assert all('error' not in p['supervision'] and 'failure' not in p['supervision'] for p in terminal['pairs'])
    assert terminal['limits'] == s0d.LIMITS and 'failure' not in terminal
    assert supervisor['status'] == 'completed' and supervisor['returncode'] == 0
    assert supervisor['elapsed_seconds'] <= 2160 and supervisor['timeout_seconds'] == 2160
    assert {'error', 'failure'}.isdisjoint(supervisor)
    # Sampler cadence: 0.25 s, sampled throughout ~1.8 s of pairs, three child PID/start identities seen.
    cleanup = terminal['cleanup']
    assert cleanup['sample_seconds'] == 0.25 and cleanup['samples'] >= 5 and cleanup['max_sample_gap_seconds'] < 0.75
    pids = {p['supervision']['pid'] for p in terminal['pairs']}
    assert pids <= {o['pid'] for o in cleanup['observed_owned_processes']} and len(pids) == 3
    index = gate_index(tmp_path, worktree, monkeypatch)
    producer, data, gated = gate_namespace()['_gate'](worktree, index)
    assert gated == terminal and index['pairs'][0]['directory'] == 'runs/s0d/seed-10'
    assert index['pairs'][2]['report_sha256'] == sha((worktree/'runs/s0d/seed-12/report.json').read_bytes())


def test_s0d_pair_supervised_deadline_kills_the_pair_and_leaves_later_seeds_not_started(tmp_path, worktree, fake):
    fake[1](**{'11': {'sleep': 30}})
    limits = {**s0d.LIMITS, 'pair_supervised_seconds': 1.5, 'pair_internal_seconds': 1}
    started = time.monotonic()
    code, out, terminal, supervisor = s0d_run(tmp_path, worktree, fake, limits=limits)
    assert time.monotonic() - started < 20 and code == 1
    assert [(p['training_seed'], p['status']) for p in terminal['pairs']] == [(10, 'completed'), (11, 'failed'), (12, 'not_started')]
    assert terminal['pairs'][1]['supervision']['status'] == 'timeout' and 'failure' in terminal['pairs'][1]['supervision']
    assert terminal['status'] == 'failed-research-training' and 'seed 11' in terminal['failure']
    assert supervisor['returncode'] == 1 and not (worktree/'runs/s0d-control/recovery-index-values.json').exists()


def test_s0d_pair_internal_deadline_is_a_failure_even_after_a_normal_exit(tmp_path, worktree, fake):
    fake[1](**{'10': {'sleep': 1.2}})
    code, out, terminal, _ = s0d_run(tmp_path, worktree, fake, limits={**s0d.LIMITS, 'pair_internal_seconds': 1})
    assert code == 1 and terminal['pairs'][0]['status'] == 'failed'
    assert terminal['pairs'][0]['supervision'] == {**terminal['pairs'][0]['supervision'], 'status': 'completed', 'returncode': 0}
    assert '600' not in terminal['failure'] and 'internal' in terminal['failure']


def test_s0d_stage_internal_deadline_stops_before_the_next_seed(tmp_path, worktree, fake):
    fake[1](default={'sleep': 1.2})
    code, out, terminal, _ = s0d_run(tmp_path, worktree, fake, limits={**s0d.LIMITS, 'stage_internal_seconds': 1.0})
    assert code == 1 and [p['status'] for p in terminal['pairs']] == ['failed', 'not_started', 'not_started']
    assert terminal['pairs'][0]['supervision']['status'] == 'timeout'


def test_s0d_enclosing_deadline_reports_a_timeout_supervisor(tmp_path, worktree, fake):
    fake[1](default={'sleep': 30})
    code, out, terminal, supervisor = s0d_run(tmp_path, worktree, fake, limits={**s0d.LIMITS, 'stage_supervised_seconds': 2})
    assert code == 1 and supervisor['status'] == 'timeout' and supervisor['returncode'] != 0 and 'failure' in supervisor


def test_s0d_orphaned_descendant_is_a_survivor_and_is_force_killed(tmp_path, worktree, fake):
    fake[1](**{'12': {'orphan': True}})
    code, out, terminal, _ = s0d_run(tmp_path, worktree, fake)
    orphan = int((fake[0]/'orphan.pid').read_text())
    assert code == 1 and terminal['status'] == 'failed-research-training'
    assert [s['pid'] for s in terminal['cleanup']['survivors']] == [orphan]
    assert [f['pid'] for f in terminal['cleanup']['forced_signals']] == [orphan]
    assert terminal['cleanup']['remaining_after_forced'] == [] and not Path(f'/proc/{orphan}').exists()


def test_s0d_inventory_and_completed_pair_changes_are_detected(tmp_path, worktree, fake):
    fake[1](**{'11': {'touch': [str(worktree/'scripts/train_male_recovery.py'), str(worktree/'runs/s0d/seed-10/report.json')]}})
    code, out, terminal, _ = s0d_run(tmp_path, worktree, fake)
    assert code == 1 and terminal['inventories_unchanged'] is False
    assert terminal['completed_pair_content_unchanged'] is False
    assert terminal['before_inventory_sha256'] != terminal['after_inventory_sha256']


def test_s0d_inventory_counts_must_match_before_any_pair(tmp_path, worktree, fake):
    code, payload = run_cli('run_male_navigation_v4_s0d', s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d')),
                            driver_path=str(fake[0]/'driver.py'), expected_head=git(worktree, 'rev-parse', 'HEAD'),
                            require_unit=False)                                    # real 355/122 expectation
    terminal = json.loads((worktree/'runs/s0d-control/terminal.json').read_text())
    assert code == 1 and 'inventory counts' in terminal['failure'] and not (fake[0]/'calls.jsonl').exists()
    assert [p['status'] for p in terminal['pairs']] == ['not_started']*3


# =================================================================== S0e launcher

def s0e_argv(tmp_path, worktree, go_path=None):
    for name in ('assets', 'corpus', 'bundle'):
        (tmp_path/name).mkdir(exist_ok=True); (tmp_path/name/'x').write_text(name)
    write(tmp_path/'s0d.pin-record.json', {'stage': 'S0d'})
    argv = ['launch', '--worktree', worktree, '--previous-pins', tmp_path/'s0d.pin-record.json', '--assets', tmp_path/'assets',
            '--output', tmp_path/'collection', '--control-root', tmp_path/'control', '--corpus', tmp_path/'corpus',
            '--bundle', tmp_path/'bundle']
    return [str(a) for a in argv + ([] if go_path is None else ['--go', go_path])]


def launch(tmp_path, worktree, fake, **overrides):
    code, out = run_cli('run_male_navigation_v4_s0e', s0e_argv(tmp_path, worktree, go(tmp_path, 'S0e')),
                        driver_path=str(fake[0]/'driver.py'), expected_head=git(worktree, 'rev-parse', 'HEAD'),
                        require_unit=False, **overrides)
    docs = {name: json.loads((tmp_path/'control'/rel).read_text()) for name, rel in s0e.CONTROL_DOCUMENTS.items()
            if (tmp_path/'control'/rel).exists()}
    return code, out, docs


def admit_namespace():
    nav = types.SimpleNamespace(PROFILE='P', PLAN_SHA='S', PROFILE_SHA='C', CASES=[{'id': c} for c in ADVICE_CASES])
    ns = {'helpers': lambda: (None, nav)}
    return extract(blob(PORTS['trees']['T-f']['branch'], 'scripts/prepare_male_navigation_v2.py'), ('admit_collection',), ns)


def drain_fixture(tmp_path, *, returncode=0, unit_returncode=0, survivors=(), complete=True, cgroup_pids=None):
    receipt_dir = tmp_path/'s0e-receipt'
    cgroup = tmp_path/'cgroup/run-u1.service'
    if cgroup_pids is not None:
        (cgroup/'work').mkdir(parents=True); (cgroup/'work/cgroup.procs').write_text(''.join(f'{p}\n' for p in cgroup_pids))
    write(receipt_dir/'receipt.json', {'kind': 'research-stage-receipt-v1', 'complete': complete, 'returncode': returncode,
                                       'survivors_killed': list(survivors), 'drained': not survivors, 'cgroup': str(cgroup),
                                       'cpu_seconds': 1.0})
    base = {'lane': 'navigation', 'stage': 'S0e', 'receipt_dir': str(receipt_dir), 'protocol_sha256': PROTOCOL_SHA}
    (tmp_path/'ledger.jsonl').write_text(json.dumps({**base, 'event': 'reserved', 'cpu_seconds': 2245.0}) + '\n' +
                                         json.dumps({**base, 'event': 'charged', 'cpu_seconds': 1.0,
                                                     'unit_returncode': unit_returncode}) + '\n')
    return ['drain', '--go', str(go(tmp_path, 'S0e-D')), '--receipt-dir', str(receipt_dir),
            '--ledger', str(tmp_path/'ledger.jsonl'), '--out', str(tmp_path/'exec-drain.json')]


def test_s0e_constants_are_bound_to_collection_v2_and_the_amendment_budget():
    evidence = json.loads((ROOT/'docs/reports/m7-navigation-collection-v2.json').read_text())
    assert s0e.NORMAL_RETURN_SECONDS == evidence['disposition']['normal_through_return_limit_seconds'] == 2210
    budget = {row['stage']: row for row in json.loads((ROOT/ctl.driver.PROTOCOL_PATH).read_text())
              ['amendment_1']['lane_budget']['stage_costs_seconds']}
    assert {s: u['runtime_max_sec'] for s, u in s0e.UNITS.items()} == \
        {s: budget[s]['runtime_max_sec_kill_target'] for s in ('S0e', 'S0e-D', 'S0e-A', 'S0e-I')}
    data_v2 = json.loads(blob('4ecb354', 'docs/plans/m7-navigation-data-v2-protocol.json'))['immutable_inputs']
    assert set(s0e.INDEX_INPUTS) == set(data_v2) - {'old_manifest', 'published_collection_index'}


@pytest.mark.parametrize('command', ['launch', 'drain', 'audit', 'index'])
def test_s0e_every_subcommand_defaults_to_plan_only_and_gates_its_own_stage(tmp_path, worktree, fake, capsys, command):
    head = git(worktree, 'rev-parse', 'HEAD')
    argv = {'launch': s0e_argv(tmp_path, worktree), 'drain': drain_fixture(tmp_path)[:1] + drain_fixture(tmp_path)[3:],
            'audit': ['audit', '--collection', str(tmp_path/'collection'), '--control-root', str(tmp_path/'control'),
                      '--drain', str(tmp_path/'exec-drain.json'), '--out', str(tmp_path/'audit.json')],
            'index': ['index', '--collection', str(tmp_path/'collection'), '--control-root', str(tmp_path/'control'),
                      '--drain', str(tmp_path/'exec-drain.json'), '--audit', str(tmp_path/'audit.json'),
                      '--out', str(tmp_path/'index.json')]}[command]
    kwargs = {'driver_path': str(fake[0]/'driver.py'), 'expected_head': head, 'require_unit': False}
    assert s0e.main(argv, **kwargs) == 0
    plan = json.loads(capsys.readouterr().out)
    stage = s0e.COMMANDS[command]
    assert plan['mode'] == 'plan-only' and plan['stage'] == stage
    assert plan['unit_command'][plan['unit_command'].index('--stage') + 1] == stage
    for wrong in ('S0d', *(s for s in s0e.UNITS if s != stage)):
        assert s0e.main(argv + ['--go', str(go(tmp_path, wrong))], **kwargs) == 2
        assert f'does not name stage {stage}' in json.loads(capsys.readouterr().out)['reason']
    relative = [os.path.relpath(a) if a.startswith(str(tmp_path)) else a for a in argv]
    assert s0e.main(relative + ['--go', str(go(tmp_path, stage))], **kwargs) == 2
    assert 'absolute' in json.loads(capsys.readouterr().out)['reason']
    assert not (tmp_path/'control').exists() and not (tmp_path/'exec-drain.json').exists()
    assert not (tmp_path/'audit.json').exists() and not (tmp_path/'index.json').exists()


def test_s0e_launcher_emits_every_admit_collection_document_and_the_ported_admission_accepts_them(tmp_path, worktree, fake):
    fake[1](collect={'sleep': 0.6, 'ticks': V2_ADVICE})
    code, out, docs = launch(tmp_path, worktree, fake)
    assert code == 0 and out['status'] == 'completed-collection', out
    calls = [json.loads(line) for line in (fake[0]/'calls.jsonl').read_text().splitlines()]
    assert len(calls) == 1 and calls[0]['argv'][:2] == ['--stage', 'S0e']
    assert calls[0]['argv'][calls[0]['argv'].index('--') + 1:] == ['--repo', str(worktree), '--assets', str(tmp_path/'assets'),
                                                                   '--output', str(tmp_path/'collection')]
    terminal, enclosing = docs['collection_terminal'], docs['collection_enclosing']
    assert terminal['cleanup']['samples'] >= 2 and enclosing['outer_cleanup']['samples'] >= 2   # inner and outer samplers
    assert terminal['cleanup']['sample_seconds'] == enclosing['outer_cleanup']['sample_seconds'] == 0.25
    assert enclosing['wall_seconds'] <= 2210 and enclosing['normal_return_limit_seconds'] == 2210
    assert set(terminal['inventory_counts']) == {'source', 'upstream', 'assets', 'corpus', 'bundle'}
    drain_code = s0e.main(drain_fixture(tmp_path), require_unit=False)
    documents = {**docs, 'exec_drain': json.loads((tmp_path/'exec-drain.json').read_text()),
                 'accepted_collection': json.loads((tmp_path/'collection/report.json').read_text())}
    p = {'counts': {'per_source': {'advice': V2_ADVICE}}, 'source_binding': {'navigation_producer_commit': terminal['head']},
         'immutable_inputs': {'accepted_collection': {'sha256': sha((tmp_path/'collection/report.json').read_bytes())}}}
    admit = admit_namespace()['admit_collection']
    assert drain_code == 0 and admit(p, documents) == documents['accepted_collection']
    for name, key, value in (('collection_terminal', 'head', 'f'*40), ('collection_enclosing', 'outer_inventory_unchanged', False),
                             ('launcher_supervisor', 'returncode', 1), ('exec_drain', 'matching_survivors', [1])):
        changed = copy.deepcopy(documents); changed[name][key] = value
        with pytest.raises(ValueError): admit(p, changed)


def test_s0e_normal_return_bound_turns_a_slow_collection_into_a_refused_failure(tmp_path, worktree, fake):
    fake[1](collect={'sleep': 30})
    started = time.monotonic()
    code, out, docs = launch(tmp_path, worktree, fake, limits={'normal_return_seconds': 2})
    assert time.monotonic() - started < 25 and code == 1
    assert docs['collector_supervisor']['status'] == 'timeout' or docs['launcher_supervisor']['status'] == 'timeout'
    assert docs['collection_enclosing']['status'] != 'completed-collection' and 'error' in docs['collection_enclosing']


def test_s0e_orphan_and_control_change_are_unclean_enclosures(tmp_path, worktree, fake):
    fake[1](collect={'orphan': True, 'touch': [str(tmp_path/'s0d.pin-record.json')]})
    code, out, docs = launch(tmp_path, worktree, fake)
    orphan = int((fake[0]/'orphan.pid').read_text())
    terminal = docs['collection_terminal']
    assert code == 1 and terminal['status'] == 'failed-collection' and terminal['controls_unchanged'] is False
    assert [s['pid'] for s in terminal['cleanup']['survivors']] == [orphan] and not Path(f'/proc/{orphan}').exists()
    assert docs['collection_enclosing']['controls_unchanged'] is False


# =================================================================== S0e-D / S0e-A / S0e-I

@pytest.mark.parametrize('kwargs, clean', [
    ({}, True), ({'returncode': 1}, False), ({'unit_returncode': 1}, False), ({'survivors': [4242]}, False),
    ({'complete': False}, False), ({'cgroup_pids': []}, True), ({'cgroup_pids': [4243]}, False)])
def test_s0e_drain_receipt_comes_from_the_unit_exit_status_and_an_empty_cgroup(tmp_path, kwargs, clean):
    code = s0e.main(drain_fixture(tmp_path, **kwargs), require_unit=False)
    receipt = json.loads((tmp_path/'exec-drain.json').read_text())
    assert (code == 0) is clean and (receipt['status'] == 'drained') is clean
    assert (receipt['exec_exitcode'] == 0 and receipt['matching_survivors'] == [] and receipt['forced_signals'] == []) is clean
    unknown = kwargs.get('complete') is False or kwargs.get('returncode')   # no complete receipt / unit 0 over a failed exec
    assert receipt['exec_exitcode'] == (None if unknown else kwargs.get('unit_returncode', 0))
    if 'survivors' in kwargs: assert receipt['forced_signals'] == [{'signal': 'cgroup.kill', 'pids': [4242]}]


def test_s0e_drain_refuses_a_ledger_without_the_charged_unit_row(tmp_path, capsys):
    argv = drain_fixture(tmp_path)
    (tmp_path/'ledger.jsonl').write_text((tmp_path/'ledger.jsonl').read_text().splitlines()[0] + '\n')
    assert s0e.main(argv, require_unit=False) == 2 and 'charged' in json.loads(capsys.readouterr().out)['reason']
    assert not (tmp_path/'exec-drain.json').exists()


def collected(tmp_path, worktree, fake, ticks=V2_ADVICE):
    fake[1](collect={'ticks': ticks})
    assert launch(tmp_path, worktree, fake)[0] == 0
    assert s0e.main(drain_fixture(tmp_path), require_unit=False) == 0
    return ['--collection', str(tmp_path/'collection'), '--control-root', str(tmp_path/'control'),
            '--drain', str(tmp_path/'exec-drain.json')]


def audit(tmp_path, common):
    code = s0e.main(['audit', '--go', str(go(tmp_path, 'S0e-A')), *common, '--out', str(tmp_path/'audit.json')], require_unit=False)
    return code, json.loads((tmp_path/'audit.json').read_text())


def test_s0e_audit_passes_and_s0e_index_publishes_the_bound_collection(tmp_path, worktree, fake):
    common = collected(tmp_path, worktree, fake)
    code, report = audit(tmp_path, common)
    assert code == 0 and report['status'] == 'passed' and report['failures'] == [] and report['stage'] == 'S0e-A'
    assert s0e.audit_passed(tmp_path/'audit.json') == report                      # the S0z check
    assert {c['name'] for c in report['checks']} >= {'report', 'owners', 'rows', 'snapshots', 'artifacts', 'enclosure', 'drain'}
    out = tmp_path/'index.json'
    assert s0e.main(['index', '--go', str(go(tmp_path, 'S0e-I')), *common, '--audit', str(tmp_path/'audit.json'),
                     '--out', str(out)], require_unit=False) == 0
    index = json.loads(out.read_text())
    assert index['status'] == 'completed-collection' and index['stage'] == 'S0e-I' and index['qualification_claims'] == []
    assert set(index['immutable_inputs']) == set(s0e.INDEX_INPUTS)
    for name, item in index['immutable_inputs'].items():
        raw = Path(item['path']).read_bytes()
        assert Path(item['path']).is_absolute() and item == {'path': item['path'], 'sha256': sha(raw), 'bytes': len(raw)}
    assert index['coverage']['rows'] == sum(V2_ADVICE) and [c['case'] for c in index['coverage']['cases']] == list(ADVICE_CASES)
    assert index['audits']['root_raw']['status'] == 'passed'
    assert index['producer_commit'] == git(worktree, 'rev-parse', 'HEAD')


@pytest.mark.parametrize('tamper, failed', [
    (lambda tmp: (tmp/'collection'/ADVICE_CASES[3]/f'run-{ADVICE_CASES[3]}/snapshots/initial.snp').write_bytes(b'x'), 'artifacts'),
    (lambda tmp: (tmp/'collection'/ADVICE_CASES[0]/f'run-{ADVICE_CASES[0]}/snapshots/initial.snp').unlink(), 'snapshots'),
    (lambda tmp: write(tmp/'exec-drain.json', {**json.loads((tmp/'exec-drain.json').read_text()), 'matching_survivors': [9]}), 'drain'),
])
def test_s0e_audit_fails_on_tampered_or_unclean_inputs_and_the_index_refuses_it(tmp_path, worktree, fake, capsys, tamper, failed):
    common = collected(tmp_path, worktree, fake)
    tamper(tmp_path)
    code, report = audit(tmp_path, common)
    assert code == 1 and report['status'] == 'failed' and failed in {f['name'] for f in report['failures']}
    with pytest.raises(ctl.Refusal): s0e.audit_passed(tmp_path/'audit.json')
    capsys.readouterr()
    assert s0e.main(['index', '--go', str(go(tmp_path, 'S0e-I')), *common, '--audit', str(tmp_path/'audit.json'),
                     '--out', str(tmp_path/'index.json')], require_unit=False) == 2
    assert 'passed' in json.loads(capsys.readouterr().out)['reason']
    assert not (tmp_path/'index.json').exists()


def test_s0e_audit_refuses_row_counts_outside_the_structural_invariants(tmp_path, worktree, fake):
    code, report = audit(tmp_path, collected(tmp_path, worktree, fake, ticks=[601] + V2_ADVICE[1:]))
    assert code == 1 and 'rows' in {f['name'] for f in report['failures']}


def test_s0e_index_refuses_documents_changed_after_the_audit(tmp_path, worktree, fake, capsys):
    common = collected(tmp_path, worktree, fake)
    assert audit(tmp_path, common)[0] == 0
    supervisor = tmp_path/'control'/s0e.CONTROL_DOCUMENTS['collector_supervisor']
    supervisor.write_text(supervisor.read_text().replace('"completed"', '"completed" '))
    capsys.readouterr()
    assert s0e.main(['index', '--go', str(go(tmp_path, 'S0e-I')), *common, '--audit', str(tmp_path/'audit.json'),
                     '--out', str(tmp_path/'index.json')], require_unit=False) == 2
    assert 'changed since the audit' in json.loads(capsys.readouterr().out)['reason']
