"""MaleCNS v4 Amendment 1 reconstructed controllers: S0d, S0e launcher, S0e-D, S0e-A, S0e-I.

No producer, simulator or training runs and no real data is opened. Every child is a tiny
synthetic fake driver that mimics producer outputs and publishes real driver pin records;
the ported ``_gate`` (T-e) and ``admit_collection`` (T-f) are compiled out of the port blobs
and fed the controllers' documents. The S0e-A audit runs the unchanged T-e readers from a
read-only extract of the port branch over a synthetic collection in the real recording
format (``male_navigation_v4_s0e_fixture.py``), and the driver's merged chains trace every
declared S0d/S0e field with the driver's own tracing code.
"""
import ast
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import male_navigation_v4_controls as ctl  # noqa: E402
import probe_male_navigation_v4_imports as probe  # noqa: E402
import run_male_navigation_v4_s0d as s0d  # noqa: E402
import run_male_navigation_v4_s0e as s0e  # noqa: E402

driver = ctl.driver
pytestmark = pytest.mark.process_isolated
PROTOCOL_SHA = driver.PROTOCOL_SHA256
PORTS = driver.load_ports()
STAGES = driver.port_stages(driver.STAGES, PORTS)
ADVICE_CASES = driver.ADVICE_CASES
PINS = ROOT/'docs/plans/m7-navigation-v4-pins'
BUILDER = Path(__file__).resolve().parent/'male_navigation_v4_s0e_fixture.py'
V2_BASELINE, V2_DEV, V2_RECOVERY = [248]*7 + [247], [307]*4, [67, 67]
V2_ADVICE = [424]*4 + [423]*8


def sha(payload): return hashlib.sha256(payload).hexdigest()


def git(cwd, *args):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


def port_rev(tree_id):
    """The port branch's commit (local ref, else origin as in CI checkouts); always the recorded commit."""
    import build_male_navigation_v4_ports as port_builder
    tree = PORTS['trees'][tree_id]
    commit = port_builder.branch_commit(ROOT, tree['branch'])
    assert commit and commit == tree['port_commit'], (tree_id, tree['branch'], commit, tree['port_commit'])
    return commit


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


def port_locator(path):
    """A T-e locator naming the real (tracked) v4 pin-document copies."""
    documents = {n: {'path': str(PINS/n), 'sha256': sha((PINS/n).read_bytes())}
                 for n in ('m7-navigation-contact-v2-protocol.json', 'm7-navigation-study-protocol.json',
                           'male-recovery-research-development-v1.json', 'm7-recovery-learning-protocol.json')}
    return write(path, {'schema': PORTS['locator']['schema'], 'documents': documents})['path']


FAKE_DRIVER = r'''
import hashlib, json, os, subprocess, sys, time
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
out = Path(opts['--output'])
pin_out = Path(argv[argv.index('--pin-record-out') + 1])
if key != 'collect':
    out.mkdir(); (out/'report.json').write_text(json.dumps({'status': 'completed-research-training', 'seed': key}))
elif b.get('builder'):
    Path(str(pin_out) + '.port-pins.json').write_text(Path(behaviour['locator']).read_text())
    config = {'port_root': behaviour['port_root'], 'output': str(out), 'ticks': b['builder']['ticks'],
              'tamper': b['builder'].get('tamper'), 'tamper_case': b['builder'].get('tamper_case')}
    subprocess.run([sys.executable, '-I', '-B', behaviour['builder_path'], json.dumps(config)], check=True,
                   env={'PATH': '/usr/bin:/bin', 'PALIMPSEST_M7_V4_PINS': str(pin_out) + '.port-pins.json'})
else:
    out.mkdir(); ticks = b.get('ticks', [5] * 12); cases = {}
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
# Publish the producer pin record exactly as the driver would (driver.make_pin_record / write_pin_record).
sys.path.insert(0, behaviour['scripts']); import regenerate_male_navigation_v4 as d
stages = d.port_stages(d.STAGES, d.load_ports())
worktree = argv[argv.index('--worktree') + 1]
if key != 'collect':
    previous = json.loads(Path(argv[argv.index('--previous-pins') + 1]).read_text())
    record = d.make_pin_record(stages['S0d'], 'S0d', worktree, out, previous, protocol_sha256=d.PROTOCOL_SHA256, training_seed=int(key))
else:
    previous = {'chain': json.loads(Path(behaviour['s0e_previous_chain']).read_text())}
    record = d.make_pin_record(stages['S0e'], 'S0e', worktree, out, previous, protocol_sha256=d.PROTOCOL_SHA256,
                               counts=d.stage_counts('advice-cases', out))
if not b.get('no_record'): d.write_pin_record(pin_out, record)
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


def chain_until_s0c(tmp_path):
    """Real driver pin records for S0a -> S0b -> S0c (tiny outputs); returns the S0c record path."""
    previous = None
    for stage in ('S0a', 'S0b', 'S0c'):
        out = tmp_path/'chain'/stage; out.mkdir(parents=True); (out/'out.json').write_text(stage)
        previous = driver.make_pin_record(STAGES[stage], stage, tmp_path, out, previous, protocol_sha256=PROTOCOL_SHA)
    path = tmp_path/'chain'/'s0c.pin-record.json'
    driver.write_pin_record(path, previous)
    return path


@pytest.fixture
def fake(tmp_path):
    """A fake driver whose per-seed behaviour the test sets; returns (folder, set_behaviour)."""
    folder = tmp_path/'fake'; folder.mkdir()
    (folder/'driver.py').write_text(FAKE_DRIVER)
    s0c = chain_until_s0c(tmp_path)
    chain = {**json.loads(s0c.read_text())['chain'], 'S0d': {'synthetic': 'merged S0d entry'}}
    write(folder/'s0e-previous-chain.json', chain)
    base = {'cases': list(ADVICE_CASES), 'scripts': str(ROOT/'scripts'), 's0e_previous_chain': str(folder/'s0e-previous-chain.json'),
            'builder_path': str(BUILDER), 'locator': port_locator(folder/'locator.json')}

    def behave(**behaviour):
        (folder/'behaviour.json').write_text(json.dumps({**base, **behaviour}))
    behave()
    return folder, behave


@pytest.fixture(scope='module')
def port_tree(tmp_path_factory):
    """Read-only extract of the T-e port branch (src, scripts) as a clean detached worktree."""
    root = tmp_path_factory.mktemp('t-e')/'worktree'; root.mkdir()
    archive = subprocess.run(['git', 'archive', port_rev('T-e'), 'src', 'scripts'], cwd=ROOT,
                             capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar: tar.extractall(root, filter='data')
    git(root, 'init', '-q'); git(root, 'add', '-A'); git(root, 'commit', '-qm', 'T-e port extract')
    git(root, 'checkout', '-q', '--detach')
    return root


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
    write(tmp_path/'data-manifest.json', {'status': 'prepared-research-only'})
    return repo


# =================================================================== S0d

COUNTS = {'tracked': len(TRACKED), 'upstream': 1}


def s0d_argv(tmp_path, worktree, go_path=None):
    argv = ['--worktree', worktree, '--previous-pins', tmp_path/'chain/s0c.pin-record.json',
            '--data-manifest', tmp_path/'data-manifest.json', '--stage-root', worktree/'runs/s0d',
            '--raw-documents', tmp_path/'raw', '--model-production', tmp_path/'model', '--runtime', tmp_path/'runtime']
    return [str(a) for a in ([] if go_path is None else ['--go', go_path]) + argv]


def s0d_run(tmp_path, worktree, fake, **overrides):
    code, out = run_cli('run_male_navigation_v4_s0d', s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d')),
                        driver_path=str(fake[0]/'driver.py'), expected_head=git(worktree, 'rev-parse', 'HEAD'),
                        expected_counts=COUNTS, require_unit=False, **overrides)
    control = worktree/'runs/s0d/control'
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


def test_s0d_raw_model_runtime_inventory_membership_is_a_documented_caller_listed_limitation(tmp_path, worktree, fake):
    # The 181/16/7 membership did not survive: those parts are never asserted, only listed and recorded.
    assert set(s0d.EXPECTED_COUNTS) == {'tracked', 'upstream'}
    assert 'Documented limitation' in s0d.__doc__ and '181/16/7' in s0d.__doc__ and 'caller-listed' in s0d.__doc__
    code, out, terminal, _ = s0d_run(tmp_path, worktree, fake)
    assert code == 0 and terminal['inventory_counts'] == {**COUNTS, 'raw_documents': 1, 'model_production': 1, 'runtime': 1}
    assert terminal['v2_reference_inventory_counts'] == s0d.V2_REFERENCE_COUNTS
    before = json.loads((worktree/'runs/s0d/control/before.json').read_text())
    assert list(before['parts']['raw_documents']['files']) == [str(tmp_path/'raw/raw.bin')]


def test_s0d_default_is_plan_only_and_lists_three_seed_runs_in_order(tmp_path, worktree, fake, capsys):
    code = s0d.main(s0d_argv(tmp_path, worktree), driver_path=str(fake[0]/'driver.py'))
    plan = json.loads(capsys.readouterr().out)
    assert code == 0 and plan['mode'] == 'plan-only' and plan['stage'] == 'S0d'
    assert [p['training_seed'] for p in plan['pairs']] == [10, 11, 12]
    for seed, pair in zip((10, 11, 12), plan['pairs']):
        tail = pair['command'][pair['command'].index('--') + 1:]
        assert tail == ['--data-manifest', str(tmp_path/'data-manifest.json'), '--training-seed', str(seed),
                        '--output', str(worktree/f'runs/s0d/seed-{seed}')]
        assert pair['command'][pair['command'].index('--pin-record-out') + 1] == \
            str(worktree/f'runs/s0d/control/pairs/seed-{seed}/pin-record.json')
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


def test_s0d_stage_root_must_be_fresh_inside_the_port_worktree_and_disjoint_from_inputs(tmp_path, worktree, fake, capsys):
    head = git(worktree, 'rev-parse', 'HEAD')
    kwargs = {'driver_path': str(fake[0]/'driver.py'), 'expected_head': head, 'require_unit': False}
    outside = [a.replace(str(worktree/'runs/s0d'), str(tmp_path/'elsewhere')) for a in s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d'))]
    assert s0d.main(outside, **kwargs) == 2 and 'inside the port worktree' in json.loads(capsys.readouterr().out)['reason']
    write(worktree/'runs/s0d/data.json', {})
    overlapping = [a.replace(str(tmp_path/'data-manifest.json'), str(worktree/'runs/s0d/data.json'))
                   for a in s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d'))]
    assert s0d.main(overlapping, **kwargs) == 2 and 'disjoint' in json.loads(capsys.readouterr().out)['reason']
    assert s0d.main(s0d_argv(tmp_path, worktree, go(tmp_path, 'S0d')), **kwargs) == 2
    assert 'fresh' in json.loads(capsys.readouterr().out)['reason']


def gate_namespace():
    ns = {'Path': Path, 'math': math, 'MAX_JSON': 4*1024**2, 'PAIR_SEEDS': (10, 11, 12),
          'artifacts': types.SimpleNamespace(_read=lambda p, cap=None: Path(p).read_bytes(), _json=json.loads,
                                             _safe_path=lambda p: Path(p).absolute()),
          'male_policy': types.SimpleNamespace(_sha=sha)}
    return extract(blob(port_rev('T-e'), 'src/palimpsest/male_recovery_research.py'), ('read_pin', '_gate'), ns)


def gate_index(tmp_path, worktree, monkeypatch):
    """The S0d recovery-index values plus synthetic data/learning documents the ported _gate also reads."""
    values = json.loads((worktree/'runs/s0d/control/recovery-index-values.json').read_text())
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
    control = worktree/'runs/s0d/control'
    assert supervisor['returncode'] == 1 and not (control/'recovery-index-values.json').exists()
    assert not (control/'controller-record.json').exists()


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


def _alive(pid):
    """Running, not a zombie: in CI containers a killed orphan can linger unreaped as Z."""
    try:
        stat = Path(f'/proc/{pid}/stat').read_text()
    except OSError:
        return False
    return stat.rsplit(')', 1)[1].split()[0] != 'Z'


def test_s0d_orphaned_descendant_is_a_survivor_and_is_force_killed(tmp_path, worktree, fake):
    fake[1](**{'12': {'orphan': True}})
    code, out, terminal, _ = s0d_run(tmp_path, worktree, fake)
    orphan = int((fake[0]/'orphan.pid').read_text())
    assert code == 1 and terminal['status'] == 'failed-research-training'
    assert [s['pid'] for s in terminal['cleanup']['survivors']] == [orphan]
    assert [f['pid'] for f in terminal['cleanup']['forced_signals']] == [orphan]
    assert terminal['cleanup']['remaining_after_forced'] == [] and not _alive(orphan)


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
    terminal = json.loads((worktree/'runs/s0d/control/terminal.json').read_text())
    assert code == 1 and 'inventory counts' in terminal['failure'] and not (fake[0]/'calls.jsonl').exists()
    assert [p['status'] for p in terminal['pairs']] == ['not_started']*3


def test_s0d_missing_driver_seed_record_fails_the_stage(tmp_path, worktree, fake):
    fake[1](**{'12': {'no_record': True}})
    code, out, terminal, supervisor = s0d_run(tmp_path, worktree, fake)
    assert code == 1 and terminal['status'] == 'passed-research-training' and out['status'] == 'failed'
    assert not (worktree/'runs/s0d/control/controller-record.json').exists()


# =================================================================== driver: merged S0d chain

def seed_records(worktree):
    return [worktree/f'runs/s0d/control/pairs/seed-{s}/pin-record.json' for s in (10, 11, 12)]


def load(paths): return [json.loads(Path(p).read_text()) for p in paths]


def declared(name, stage, skip=()):
    item = json.loads((PINS/'declared-fields.json').read_text())['documents'][name]
    return {**item, 'fields': [f for f in item['fields'] if f['stage'] == stage and f['class'] not in skip]}


def test_driver_merges_the_three_seed_records_and_traces_every_s0d_recovery_index_field(tmp_path, worktree, fake):
    assert s0d_run(tmp_path, worktree, fake)[0] == 0
    chain = driver.previous_chain(load(seed_records(worktree)), 'S0e', STAGES, protocol_sha256=PROTOCOL_SHA)
    entry = chain['S0d']
    assert list(chain) == ['S0a', 'S0b', 'S0c', 'S0d'] and entry['output_root'] == str(worktree/'runs/s0d')
    assert {'seed-10/report.json', 'seed-12/report.json', 'control/terminal.json',
            'control/outer-supervisor/supervisor.json'} <= set(entry['outputs'])
    values = json.loads((worktree/'runs/s0d/control/recovery-index-values.json').read_text())
    doc = json.loads((PINS/'male-recovery-research-development-v1.json').read_text())
    doc.update({k: values[k] for k in ('producer_root', 'training_terminal', 'training_supervisor', 'before_after_inventory_sha256')})
    for pair, value in zip(doc['pairs'], values['pairs']): pair.update(directory=value['directory'], report_sha256=value['report_sha256'])
    # path-keys, source-map and commit are read from seed protocol.json / the producing commit (ports tests cover them).
    item = declared('male-recovery-research-development-v1.json', 'S0d', skip=('path-keys', 'source-map', 'commit'))
    assert len(item['fields']) == 12
    driver.check_document_values('index', doc, doc, item, chain, None, PINS)    # every S0d path and sha traces
    for pointer, value in (('/training_terminal/sha256', 'f'*64), ('/pairs/1/directory', '/elsewhere/seed-11'),
                           ('/before_after_inventory_sha256', 'e'*64)):
        changed = copy.deepcopy(doc); driver.pointer_set(changed, pointer, value)
        with pytest.raises(driver.Refusal): driver.check_document_values('index', changed, doc, item, chain, None, PINS)


@pytest.mark.parametrize('select, reason', [
    (lambda r: r[:2], 'exactly 3 S0d pin record'),
    (lambda r: r + r[2:], 'exactly 3 S0d pin record'),
    (lambda r: [r[1], r[0], r[2]], 'seeds [10, 11, 12] in order'),
    (lambda r: [r[0], r[0], r[2]], 'seeds [10, 11, 12] in order'),
    (lambda r: [], 'exactly 3 S0d pin record'),
])
def test_driver_refuses_missing_extra_reordered_or_duplicate_seed_records(tmp_path, worktree, fake, select, reason):
    assert s0d_run(tmp_path, worktree, fake)[0] == 0
    with pytest.raises(driver.Refusal, match=reason.replace('[', r'\[').replace(']', r'\]')):
        driver.previous_chain(select(load(seed_records(worktree))), 'S0e', STAGES, protocol_sha256=PROTOCOL_SHA)


def test_driver_refuses_a_changed_or_missing_s0d_controller_record(tmp_path, worktree, fake):
    assert s0d_run(tmp_path, worktree, fake)[0] == 0
    records = load(seed_records(worktree))
    terminal = worktree/'runs/s0d/control/terminal.json'
    terminal.write_text(terminal.read_text() + ' ')
    with pytest.raises(driver.Refusal, match='controller document differs'):
        driver.previous_chain(records, 'S0e', STAGES, protocol_sha256=PROTOCOL_SHA)
    (worktree/'runs/s0d/control/controller-record.json').unlink()
    with pytest.raises(driver.Refusal):
        driver.previous_chain(records, 'S0e', STAGES, protocol_sha256=PROTOCOL_SHA)
    with pytest.raises(driver.Refusal, match='exactly one previous pin record'):   # uncontrolled stages keep one record
        driver.previous_chain(records[:2], 'S0c', STAGES, protocol_sha256=PROTOCOL_SHA)


# =================================================================== S0e launcher

def s0e_argv(tmp_path, worktree, go_path=None, previous=None):
    for name in ('assets', 'corpus', 'bundle'):
        (tmp_path/name).mkdir(exist_ok=True); (tmp_path/name/'x').write_text(name)
    previous = previous or [write(tmp_path/f'prev/s0d-{s}.json', {'stage': 'S0d', 'training_seed': s})['path'] for s in (10, 11, 12)]
    argv = ['launch', '--worktree', worktree, '--previous-pins', *previous, '--assets', tmp_path/'assets',
            '--stage-root', tmp_path/'s0e', '--corpus', tmp_path/'corpus', '--bundle', tmp_path/'bundle']
    return [str(a) for a in argv + ([] if go_path is None else ['--go', go_path])]


def launch(tmp_path, worktree, fake, **overrides):
    code, out = run_cli('run_male_navigation_v4_s0e', s0e_argv(tmp_path, worktree, go(tmp_path, 'S0e')),
                        driver_path=str(fake[0]/'driver.py'), expected_head=git(worktree, 'rev-parse', 'HEAD'),
                        require_unit=False, **overrides)
    docs = {name: json.loads((tmp_path/'s0e/control'/rel).read_text()) for name, rel in s0e.CONTROL_DOCUMENTS.items()
            if (tmp_path/'s0e/control'/rel).exists()}
    return code, out, docs


def admit_namespace():
    nav = types.SimpleNamespace(PROFILE='P', PLAN_SHA='S', PROFILE_SHA='C', CASES=[{'id': c} for c in ADVICE_CASES])
    ns = {'helpers': lambda: (None, nav)}
    return extract(blob(port_rev('T-f'), 'scripts/prepare_male_navigation_v2.py'), ('admit_collection',), ns)


def drain_fixture(tmp_path, *, returncode=0, unit_returncode=0, survivors=(), complete=True, cgroup_pids=None):
    receipt_dir = tmp_path/'s0e-receipt'
    cgroup = tmp_path/'cgroup/run-u1.service'
    if cgroup_pids is not None:
        (cgroup/'work').mkdir(parents=True); (cgroup/'work/cgroup.procs').write_text(''.join(f'{p}\n' for p in cgroup_pids))
    (tmp_path/'s0e/control').mkdir(parents=True, exist_ok=True)
    write(receipt_dir/'receipt.json', {'kind': 'research-stage-receipt-v1', 'complete': complete, 'returncode': returncode,
                                       'survivors_killed': list(survivors), 'drained': not survivors, 'cgroup': str(cgroup),
                                       'cpu_seconds': 1.0})
    base = {'lane': 'navigation', 'stage': 'S0e', 'receipt_dir': str(receipt_dir), 'protocol_sha256': PROTOCOL_SHA}
    (tmp_path/'ledger.jsonl').write_text(json.dumps({**base, 'event': 'reserved', 'cpu_seconds': 2245.0}) + '\n' +
                                         json.dumps({**base, 'event': 'charged', 'cpu_seconds': 1.0,
                                                     'unit_returncode': unit_returncode}) + '\n')
    return ['drain', '--go', str(go(tmp_path, 'S0e-D')), '--stage-root', str(tmp_path/'s0e'), '--receipt-dir', str(receipt_dir),
            '--ledger', str(tmp_path/'ledger.jsonl')]


def test_s0e_constants_are_bound_to_collection_v2_and_the_amendment_budget():
    evidence = json.loads((ROOT/'docs/reports/m7-navigation-collection-v2.json').read_text())
    assert s0e.NORMAL_RETURN_SECONDS == evidence['disposition']['normal_through_return_limit_seconds'] == 2210
    budget = {row['stage']: row for row in json.loads((ROOT/driver.PROTOCOL_PATH).read_text())
              ['amendment_1']['lane_budget']['stage_costs_seconds']}
    assert {s: u['runtime_max_sec'] for s, u in s0e.UNITS.items()} == \
        {s: budget[s]['runtime_max_sec_kill_target'] for s in ('S0e', 'S0e-D', 'S0e-A', 'S0e-I')}
    data_v2 = json.loads(blob('4ecb354', 'docs/plans/m7-navigation-data-v2-protocol.json'))['immutable_inputs']
    assert set(s0e.INDEX_INPUTS) == set(data_v2) - {'old_manifest', 'published_collection_index'}
    assert s0e.NOT_COVERED == [] and 'finite arrays' in s0e.V2_AUDIT_SCOPE and 'contact' in s0e.V2_AUDIT_SCOPE


@pytest.mark.parametrize('command', ['launch', 'drain', 'audit', 'index'])
def test_s0e_every_subcommand_defaults_to_plan_only_and_gates_its_own_stage(tmp_path, worktree, fake, capsys, command):
    head = git(worktree, 'rev-parse', 'HEAD')
    argv = {'launch': s0e_argv(tmp_path, worktree), 'drain': [a for i, a in enumerate(drain_fixture(tmp_path)) if i not in (1, 2)],
            'audit': ['audit', '--stage-root', str(tmp_path/'s0e'), '--port-worktree', str(tmp_path/'port')],
            'index': ['index', '--stage-root', str(tmp_path/'s0e')]}[command]
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
    assert not (tmp_path/'s0e/control/terminal.json').exists() and not (tmp_path/'s0e/control/exec-drain.json').exists()
    assert not (tmp_path/'s0e/control/root-raw-audit.json').exists() and not (tmp_path/'s0e/control/collection-index.json').exists()


def test_s0e_launcher_emits_every_admit_collection_document_and_the_ported_admission_accepts_them(tmp_path, worktree, fake):
    fake[1](collect={'sleep': 0.6, 'ticks': V2_ADVICE})
    code, out, docs = launch(tmp_path, worktree, fake)
    assert code == 0 and out['status'] == 'completed-collection', out
    calls = [json.loads(line) for line in (fake[0]/'calls.jsonl').read_text().splitlines()]
    previous = [str(tmp_path/f'prev/s0d-{s}.json') for s in (10, 11, 12)]
    argv = calls[0]['argv']
    assert len(calls) == 1 and argv[:2] == ['--stage', 'S0e']
    assert argv[argv.index('--previous-pins') + 1:argv.index('--previous-pins') + 4] == previous   # seed records, in order
    assert argv[argv.index('--pin-record-out') + 1] == str(tmp_path/'s0e/control/collector-pin-record.json')
    assert argv[argv.index('--') + 1:] == ['--repo', str(worktree), '--assets', str(tmp_path/'assets'),
                                           '--output', str(tmp_path/'s0e/collection')]
    terminal, enclosing = docs['collection_terminal'], docs['collection_enclosing']
    assert terminal['cleanup']['samples'] >= 2 and enclosing['outer_cleanup']['samples'] >= 2   # inner and outer samplers
    assert terminal['cleanup']['sample_seconds'] == enclosing['outer_cleanup']['sample_seconds'] == 0.25
    assert enclosing['wall_seconds'] <= 2210 and enclosing['normal_return_limit_seconds'] == 2210
    assert set(terminal['inventory_counts']) == {'source', 'upstream', 'assets', 'corpus', 'bundle'}
    drain_code = s0e.main(drain_fixture(tmp_path), require_unit=False)
    documents = {**docs, 'exec_drain': json.loads((tmp_path/'s0e/control/exec-drain.json').read_text()),
                 'accepted_collection': json.loads((tmp_path/'s0e/collection/report.json').read_text())}
    p = {'counts': {'per_source': {'advice': V2_ADVICE}}, 'source_binding': {'navigation_producer_commit': terminal['head']},
         'immutable_inputs': {'accepted_collection': {'sha256': sha((tmp_path/'s0e/collection/report.json').read_bytes())}}}
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
    fake[1](collect={'orphan': True, 'touch': [str(tmp_path/'prev/s0d-11.json')]})
    code, out, docs = launch(tmp_path, worktree, fake)
    orphan = int((fake[0]/'orphan.pid').read_text())
    terminal = docs['collection_terminal']
    assert code == 1 and terminal['status'] == 'failed-collection' and terminal['controls_unchanged'] is False
    assert [s['pid'] for s in terminal['cleanup']['survivors']] == [orphan] and not Path(f'/proc/{orphan}').exists()
    assert docs['collection_enclosing']['controls_unchanged'] is False


# =================================================================== S0e-D

@pytest.mark.parametrize('kwargs, clean', [
    ({}, True), ({'returncode': 1}, False), ({'unit_returncode': 1}, False), ({'survivors': [4242]}, False),
    ({'complete': False}, False), ({'cgroup_pids': []}, True), ({'cgroup_pids': [4243]}, False)])
def test_s0e_drain_receipt_comes_from_the_unit_exit_status_and_an_empty_cgroup(tmp_path, kwargs, clean):
    code = s0e.main(drain_fixture(tmp_path, **kwargs), require_unit=False)
    receipt = json.loads((tmp_path/'s0e/control/exec-drain.json').read_text())
    assert (code == 0) is clean and (receipt['status'] == 'drained') is clean
    assert (receipt['exec_exitcode'] == 0 and receipt['matching_survivors'] == [] and receipt['forced_signals'] == []) is clean
    unknown = kwargs.get('complete') is False or kwargs.get('returncode')   # no complete receipt / unit 0 over a failed exec
    assert receipt['exec_exitcode'] == (None if unknown else kwargs.get('unit_returncode', 0))
    if 'survivors' in kwargs: assert receipt['forced_signals'] == [{'signal': 'cgroup.kill', 'pids': [4242]}]


def test_s0e_drain_refuses_a_ledger_without_the_charged_unit_row(tmp_path, capsys):
    argv = drain_fixture(tmp_path)
    (tmp_path/'ledger.jsonl').write_text((tmp_path/'ledger.jsonl').read_text().splitlines()[0] + '\n')
    assert s0e.main(argv, require_unit=False) == 2 and 'charged' in json.loads(capsys.readouterr().out)['reason']
    assert not (tmp_path/'s0e/control/exec-drain.json').exists()


# =================================================================== S0e-A / S0e-I (T-e port readers, real format)

def collected(tmp_path, worktree, fake, port_tree, ticks=(2,)*12, **tamper):
    fake[1](port_root=str(port_tree), collect={'builder': {'ticks': list(ticks), **tamper}})
    code, out, docs = launch(tmp_path, worktree, fake)
    assert code == 0, (out, docs.get('collection_terminal'))
    assert s0e.main(drain_fixture(tmp_path), require_unit=False) == 0
    return ['--stage-root', str(tmp_path/'s0e')]


def audit(tmp_path, common, port_tree, **kwargs):
    code = s0e.main(['audit', '--go', str(go(tmp_path, 'S0e-A')), *common, '--port-worktree', str(port_tree)],
                    require_unit=False, expected_head=git(port_tree, 'rev-parse', 'HEAD'), **kwargs)
    path = tmp_path/'s0e/control/root-raw-audit.json'
    return code, json.loads(path.read_text()) if path.exists() else None


def failed(report): return {f['name'] for f in report['failures']}


def test_s0e_audit_reproduces_the_v2_root_scope_with_the_port_readers_and_passes(tmp_path, worktree, fake, port_tree):
    common = collected(tmp_path, worktree, fake, port_tree)
    code, report = audit(tmp_path, common, port_tree)
    assert code == 0 and report['status'] == 'passed' and report['failures'] == [], report['failures']
    names = {c['name'] for c in report['checks']}
    assert names >= {'report', 'owners', 'rows', 'snapshots', 'artifacts', 'enclosure', 'drain', 'reader_isolation',
                     'shared_validators', 'contact_incidence', 'finite_arrays', 'tick_counts'}
    assert report['not_covered'] == [] and report['native_or_model_import'] is False
    assert report['port_head'] == git(port_tree, 'rev-parse', 'HEAD')
    isolation = next(c for c in report['checks'] if c['name'] == 'reader_isolation')['detail']
    assert isolation['forbidden_modules'] == [] and isolation['local_modules_outside_port'] == []
    assert isolation['reader_origin'] == str(port_tree.resolve()/'scripts/collect_male_navigation_v2.py')
    # Rebuilt from recordings: per tick n = 1 + tick % 3 pairs (support, obstacle, world-only) x 11 stages.
    assert report['pair_instances_by_type'] == {'wheel_floor_support': 12*2*11, 'non_wheel_floor': 0,
                                                'robot_obstacle': 12*1*11, 'robot_wall': 0, 'world_only': 0}
    assert set(report['events'].values()) == {1} and report['case_rows']   # one chunk event per 2-tick recording == {c: 2 for c in ADVICE_CASES}


@pytest.mark.parametrize('tamper, check', [
    ('label', 'shared_validators'), ('incidence', 'contact_incidence'), ('nonfinite', 'finite_arrays')])
def test_s0e_audit_port_readers_catch_label_incidence_and_nonfinite_faults(tmp_path, worktree, fake, port_tree, tamper, check):
    common = collected(tmp_path, worktree, fake, port_tree, tamper=tamper, tamper_case=ADVICE_CASES[4])
    code, report = audit(tmp_path, common, port_tree)
    assert code == 1 and report['status'] == 'failed' and check in failed(report)
    detail = next(c for c in report['checks'] if c['name'] == check)['detail']
    assert list(detail) == [ADVICE_CASES[4]]
    if tamper == 'label': assert 'ValueError' in detail[ADVICE_CASES[4]]


def test_s0e_audit_refuses_a_port_worktree_other_than_the_t_e_commit(tmp_path, worktree, fake, port_tree, capsys):
    common = collected(tmp_path, worktree, fake, port_tree)
    capsys.readouterr()
    assert s0e.main(['audit', '--go', str(go(tmp_path, 'S0e-A')), *common, '--port-worktree', str(port_tree)],
                    require_unit=False) == 2                                   # default: ports.json T-e commit
    assert PORTS['trees']['T-e']['port_commit'] in json.loads(capsys.readouterr().out)['reason']
    assert not (tmp_path/'s0e/control/root-raw-audit.json').exists()


def test_s0z_check_refuses_uncovered_scope_unless_the_owner_waives_it(tmp_path):
    doc = {'kind': s0e.AUDIT_KIND, 'status': 'passed', 'failures': [], 'not_covered': ['finite arrays']}
    path = Path(write(tmp_path/'audit.json', doc)['path'])
    with pytest.raises(ctl.Refusal, match='without an owner waiver'): s0e.audit_passed(path)
    assert s0e.audit_passed(path, waivers=('finite arrays',)) == doc
    write(path, {**doc, 'not_covered': []})
    assert s0e.audit_passed(path)['not_covered'] == []
    write(path, {**doc, 'not_covered': None})
    with pytest.raises(ctl.Refusal): s0e.audit_passed(path)


def test_s0e_index_publishes_and_the_driver_traces_every_data_v2_s0e_field(tmp_path, worktree, fake, port_tree):
    common = collected(tmp_path, worktree, fake, port_tree)
    assert audit(tmp_path, common, port_tree)[0] == 0
    assert s0e.audit_passed(tmp_path/'s0e/control/root-raw-audit.json')['status'] == 'passed'   # the S0z check
    assert s0e.main(['index', '--go', str(go(tmp_path, 'S0e-I')), *common], require_unit=False) == 0
    control = tmp_path/'s0e/control'
    index = json.loads((control/'collection-index.json').read_text())
    assert index['status'] == 'completed-collection' and index['stage'] == 'S0e-I' and index['qualification_claims'] == []
    assert set(index['immutable_inputs']) == set(s0e.INDEX_INPUTS)
    for item in index['immutable_inputs'].values():
        raw = Path(item['path']).read_bytes()
        assert Path(item['path']).is_relative_to(tmp_path/'s0e') and item['sha256'] == sha(raw) and item['bytes'] == len(raw)
    assert index['coverage']['rows'] == 24 and [c['case'] for c in index['coverage']['cases']] == list(ADVICE_CASES)
    assert index['audits']['root_raw']['status'] == 'passed' and index['producer_commit'] == git(worktree, 'rev-parse', 'HEAD')
    # S0f: the driver merges the collector record with the controller record; every declared S0e field traces.
    chain = driver.previous_chain(load([control/'collector-pin-record.json']), 'S0f', STAGES, protocol_sha256=PROTOCOL_SHA)
    assert chain['S0e']['output_root'] == str(tmp_path/'s0e') and chain['S0e']['counts'] == {c: 2 for c in ADVICE_CASES}
    doc = json.loads((PINS/'m7-navigation-data-v2-protocol.json').read_text())
    for name, item in {**index['immutable_inputs'], 'published_collection_index': ctl.binding(control/'collection-index.json')}.items():
        doc['immutable_inputs'][name] = item
    item = declared('m7-navigation-data-v2-protocol.json', 'S0e')
    item = {**item, 'fields': [f for f in item['fields'] if f['pointer'].startswith('/immutable_inputs/')]}  # counts/commit: ports tests
    assert len(item['fields']) == 24
    driver.check_document_values('data-v2', doc, doc, item, chain, None, PINS)
    changed = copy.deepcopy(doc); changed['immutable_inputs']['exec_drain']['bytes'] += 1
    with pytest.raises(driver.Refusal): driver.check_document_values('data-v2', changed, doc, item, chain, None, PINS)


@pytest.mark.parametrize('tamper, failed_check', [
    (lambda tmp: (tmp/'s0e/collection'/ADVICE_CASES[3]/f'run-{ADVICE_CASES[3]}/snapshots/initial.snp').write_bytes(b'x'), 'artifacts'),
    (lambda tmp: (tmp/'s0e/collection'/ADVICE_CASES[0]/f'run-{ADVICE_CASES[0]}/snapshots/initial.snp').unlink(), 'snapshots'),
    (lambda tmp: write(tmp/'s0e/control/exec-drain.json',
                       {**json.loads((tmp/'s0e/control/exec-drain.json').read_text()), 'matching_survivors': [9]}), 'drain'),
])
def test_s0e_audit_fails_on_tampered_or_unclean_inputs_and_the_index_refuses_it(tmp_path, worktree, fake, port_tree, capsys,
                                                                                 tamper, failed_check):
    common = collected(tmp_path, worktree, fake, port_tree)
    tamper(tmp_path)
    code, report = audit(tmp_path, common, port_tree)
    assert code == 1 and report['status'] == 'failed' and failed_check in failed(report)
    with pytest.raises(ctl.Refusal): s0e.audit_passed(tmp_path/'s0e/control/root-raw-audit.json')
    capsys.readouterr()
    assert s0e.main(['index', '--go', str(go(tmp_path, 'S0e-I')), *common], require_unit=False) == 2
    assert 'passed' in json.loads(capsys.readouterr().out)['reason']
    assert not (tmp_path/'s0e/control/collection-index.json').exists()


def test_s0e_audit_refuses_row_counts_outside_the_structural_invariants(tmp_path, worktree, fake, port_tree):
    fake[1](collect={'ticks': [601] + [5]*11})            # simple (non-recording) fake: readers fail too
    assert launch(tmp_path, worktree, fake)[0] == 0
    assert s0e.main(drain_fixture(tmp_path), require_unit=False) == 0
    code, report = audit(tmp_path, ['--stage-root', str(tmp_path/'s0e')], port_tree)
    assert code == 1 and {'rows', 'reader_isolation', 'shared_validators'} <= failed(report)


def test_s0e_index_refuses_documents_changed_after_the_audit(tmp_path, worktree, fake, port_tree, capsys):
    common = collected(tmp_path, worktree, fake, port_tree)
    assert audit(tmp_path, common, port_tree)[0] == 0
    supervisor = tmp_path/'s0e/control'/s0e.CONTROL_DOCUMENTS['collector_supervisor']
    supervisor.write_text(supervisor.read_text().replace('"completed"', '"completed" '))
    capsys.readouterr()
    assert s0e.main(['index', '--go', str(go(tmp_path, 'S0e-I')), *common], require_unit=False) == 2
    assert 'changed since the audit' in json.loads(capsys.readouterr().out)['reason']


# =================================================================== stage P

CONTROLLER_ENTRIES = {'S0d-controller': 'run_male_navigation_v4_s0d', 'S0e-launch': 'run_male_navigation_v4_s0e',
                      'S0e-D': 'run_male_navigation_v4_s0e', 'S0e-A': 'run_male_navigation_v4_s0e',
                      'S0e-A-worker': 'audit_male_navigation_v4_s0e_raw', 'S0e-I': 'run_male_navigation_v4_s0e',
                      'controls': 'male_navigation_v4_controls'}


def test_stage_p_declares_every_controller_entry_point_and_the_probe_resolves_them():
    assert {k: probe.ENTRYPOINTS[k]['module'] for k in CONTROLLER_ENTRIES} == CONTROLLER_ENTRIES
    assert all(probe.ENTRYPOINTS[k]['commit'] is None for k in CONTROLLER_ENTRIES)
    for stage in CONTROLLER_ENTRIES:
        result = probe.probe_stage(sys.executable, stage, ROOT)
        assert result['status'] == 'passed', (stage, result.get('reasons'))


# =================================================================== S1 data child (v3's data path on the T-f reader)

S1_WORKER = ROOT/'scripts/derive_male_navigation_v4_s1_data.py'


@pytest.fixture(scope='module')
def port_tf(tmp_path_factory):
    """Read-only extract of the T-f port branch as a clean tree."""
    root = tmp_path_factory.mktemp('t-f')/'worktree'; root.mkdir()
    archive = subprocess.run(['git', 'archive', port_rev('T-f'), 'src', 'scripts'], cwd=ROOT,
                             capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar: tar.extractall(root, filter='data')
    git(root, 'init', '-q'); git(root, 'add', '-A'); git(root, 'commit', '-qm', 'T-f port extract')
    return root


def reader_identity(root):
    """T-f's reader_identity: sha256 of every tracked .py under src/ and scripts/ (the adapter included)."""
    names = sorted(p.relative_to(root).as_posix() for base in ('src', 'scripts') for p in (root/base).rglob('*.py'))
    return {n: sha((root/n).read_bytes()) for n in names}


def run_s1_worker(tmp_path, tree, value, **config):  # config overrides body keys
    tmp_path.mkdir(parents=True, exist_ok=True)
    raw = tmp_path/'data-manifest.json'; raw.write_bytes(json.dumps(value, sort_keys=True).encode())
    body = {'port_root': str(tree), 'data_root': str(tmp_path/'s0f'), 'output': str(tmp_path/'arrays.npz'), 'seconds': 120,
            'manifest': {'path': str(raw), 'sha256': sha(raw.read_bytes())}, **config}
    documents = {n: {'path': str(PINS/n), 'sha256': sha((PINS/n).read_bytes())} for n in PORTS['trees']['T-f']['documents']}
    locator = write(tmp_path/'locator.json', {'schema': PORTS['locator']['schema'], 'documents': documents})['path']
    env = {**ctl.child_env(), ctl.driver.PORT_LOCATOR_ENV: locator}
    done = subprocess.run([sys.executable, '-I', '-B', str(S1_WORKER), json.dumps(body)], env=env, cwd=tree, capture_output=True,
                          text=True, timeout=180)
    lines = [line for line in done.stdout.splitlines() if line.startswith('{')]
    return done.returncode, json.loads(lines[-1]) if lines else {'reason': 'NO RESULT: ' + done.stderr[-900:], 'status': 'crashed'}


def test_s1_data_child_refuses_tampered_reader_code_before_reading_anything(tmp_path, port_tf):
    tampered = tmp_path/'tampered'
    __import__('shutil').copytree(port_tf, tampered)
    target = tampered/'src/palimpsest/male_model.py'
    target.write_bytes(target.read_bytes() + b'\n# drift\n')
    manifest = {'current_reader_sources': reader_identity(port_tf), 'adapter_sha256': 'a'*64, 'feature_protocol_sha256': 'b'*64}
    code, result = run_s1_worker(tmp_path/'w', tampered, manifest)
    assert code == 1 and result['status'] == 'refused' and 'current_reader_sources' in result['reason'], result
    assert not (tmp_path/'w/arrays.npz').exists()


def test_s1_data_child_checks_identity_then_adapter_then_the_feature_protocol_in_that_order(tmp_path, port_tf):
    identity = reader_identity(port_tf)
    code, result = run_s1_worker(tmp_path/'a', port_tf, {'current_reader_sources': identity, 'adapter_sha256': 'a'*64,
                                                         'feature_protocol_sha256': 'b'*64})
    assert code == 1 and 'adapter_sha256' in result['reason'], result          # code identity passed; the adapter gate is next
    adapter = identity['scripts/prepare_male_navigation_v2.py']
    code, result = run_s1_worker(tmp_path/'b', port_tf, {'current_reader_sources': identity, 'adapter_sha256': adapter,
                                                         'feature_protocol_sha256': 'b'*64})
    assert code == 1 and 'Feature protocol' in result['reason'], result


def test_s1_data_child_refuses_a_manifest_that_differs_from_the_pinned_bytes(tmp_path, port_tf):
    code, result = run_s1_worker(tmp_path, port_tf, {'x': 1}, **{'manifest': {'path': str(tmp_path/'data-manifest.json'), 'sha256': '0'*64}})
    assert code == 1 and 'S0z pin' in result['reason'], result


def test_s1_hooks_derive_data_binds_heads_locator_and_the_child_result(tmp_path):
    import train_male_navigation_v4 as s1
    from unittest import mock
    repos = {}
    for name in ('t-f', 't-h'):
        repo = tmp_path/name; repo.mkdir(); git(repo, 'init', '-q'); (repo/'x').write_text(name)
        git(repo, 'add', '-A'); git(repo, 'commit', '-qm', name)
        repos[name] = (repo, git(repo, 'rev-parse', 'HEAD'))
    locator = write(tmp_path/'locator.json', {'v': 1})
    record = {'data_manifest': {'path': str(tmp_path/'m.json'), 'sha256': '1'*64, 'bytes': 1},
              'reader': {'t_f': {'path': str(repos['t-f'][0]), 'head': repos['t-f'][1]},
                         't_h': {'path': str(repos['t-h'][0]), 'head': repos['t-h'][1]},
                         'locator': {'path': locator['path'], 'sha256': locator['sha256'], 'bytes': Path(locator['path']).stat().st_size},
                         'data_root': str(tmp_path/'s0f')}}
    out = tmp_path/'out'; out.mkdir()
    real = subprocess.run
    seen = []

    def worker(payload, returncode=0):
        def fake(cmd, *args, **kwargs):
            if cmd[0] == 'git': return real(cmd, *args, **kwargs)
            seen.append((cmd, kwargs['env']))
            return types.SimpleNamespace(returncode=returncode, stderr='', stdout=json.dumps(payload) + '\n')
        return fake
    ok = {'status': 'derived', 'sources': 26, 'forbidden_modules': [], 'output_sha256': '0'*64}
    hooks = s1.Hooks()
    with mock.patch.object(s1.subprocess, 'run', worker(ok)):
        assert hooks.derive_data(record, {}, out) == out/'transient-arrays.npz'
    cmd, env = seen[0]
    assert cmd[:3] == [sys.executable, '-I', '-B'] and cmd[3].endswith('derive_male_navigation_v4_s1_data.py')
    assert env['PALIMPSEST_M7_V4_PINS'] == locator['path'] and env['CUDA_VISIBLE_DEVICES'] == ''
    assert json.loads(cmd[4])['port_root'] == str(repos['t-f'][0])
    for bad, code, message in (({**ok, 'forbidden_modules': ['torch']}, 0, 'forbidden'), ({**ok, 'sources': 25}, 0, 'forbidden'),
                               ({'status': 'refused', 'reason': 'Byte drift: x'}, 1, 'Byte drift')):
        with mock.patch.object(s1.subprocess, 'run', worker(bad, code)), pytest.raises(s1.Refusal, match=message):
            hooks.derive_data(record, {}, out)
    wrong = copy.deepcopy(record); wrong['reader']['t_f']['head'] = '0'*40
    with mock.patch.object(s1.subprocess, 'run', worker(ok)), pytest.raises(s1.Refusal, match='port head'):
        hooks.derive_data(wrong, {}, out)
    changed = copy.deepcopy(record); changed['reader']['locator']['sha256'] = '0'*64
    with mock.patch.object(s1.subprocess, 'run', worker(ok)), pytest.raises(s1.Refusal, match='differ'):
        hooks.derive_data(changed, {}, out)


def test_s1_hooks_refuse_a_dirty_or_untracked_reader_worktree_before_the_child_starts(tmp_path):
    import train_male_navigation_v4 as s1
    from unittest import mock
    record = {'data_manifest': {'path': str(tmp_path/'m.json'), 'sha256': '1'*64, 'bytes': 1}, 'reader': {}}
    for name in ('t-f', 't-h'):
        repo = tmp_path/name; (repo/'src').mkdir(parents=True); (repo/'src/a.py').write_text('a=1\n'); git(repo, 'init', '-q')
        git(repo, 'add', '-A'); git(repo, 'commit', '-qm', name)
        record['reader'][name.replace('-', '_')] = {'path': str(repo), 'head': git(repo, 'rev-parse', 'HEAD')}
    locator = write(tmp_path/'locator.json', {'v': 1})
    record['reader'].update(locator={'path': locator['path'], 'sha256': locator['sha256'], 'bytes': Path(locator['path']).stat().st_size}, data_root='/x')
    started = []
    with mock.patch.object(s1.subprocess, 'run', wraps=subprocess.run) as run:
        for edit in (lambda r: (r/'src/a.py').write_text('a=2\n'), lambda r: (r/'src/new.py').write_text('x=1\n')):
            edit(tmp_path/'t-h')
            with pytest.raises(s1.Refusal, match='modified or untracked'):
                s1.Hooks().derive_data(record, {}, tmp_path)
            git(tmp_path/'t-h', 'checkout', '-q', '--', 'src'); (tmp_path/'t-h/src/new.py').unlink(missing_ok=True)
        assert not any(call.args[0][1:3] == ['-I', '-B'] for call in run.call_args_list)   # the child never started
