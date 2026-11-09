"""MaleCNS v4 S0e controllers: launcher, S0e-D drain receipt, S0e-A root raw audit, S0e-I index; plan-only by default.

Reconstructs the lost collection-v2 ``launch.py``/``supervise.py`` and their post-run steps
(Amendment 1, reconstructed_controllers S0e/S0e-D/S0e-A/S0e-I), bound to
``docs/reports/m7-navigation-collection-v2.{md,json}`` and to the exact fields the ported
``prepare_male_navigation_v2.admit_collection`` (T-f, lines 323-345) reads. Every S0e
document lives under one stage root ``R``: the collector output in ``R/collection`` and
every controller document in ``R/control``, so the data-v2 declared paths trace to the
driver's merged S0e chain (``R`` is its output root):

``launch`` (stage S0e)
    enclosing supervisor (outer sampler, outer inventory, ``enclosing.json``) -> launcher
    (inner sampler, inventories, ``terminal.json``) -> the driver running the T-e port
    collector with the S0d seed 10/11/12 records. Normal admission requires return within
    2,210 s of the enclosing start. ``outer-launch/supervisor.json`` supervises the collector
    process and ``outer-supervisor/supervisor.json`` supervises the launcher process.
``drain`` (stage S0e-D)
    ``control/exec-drain.json`` from the S0e unit's exit status (run_research_stage ledger)
    and an empty unit cgroup (its receipt's drain plus a post-exit cgroup check).
``audit`` (stage S0e-A)
    ``control/root-raw-audit.json``: the v2 root raw-audit scope. Shared validators, raw
    contact incidence, finite arrays and row/tick/event counts come from a worker that
    imports the verified T-e port worktree's own readers read-only; hashes, owners,
    snapshots, enclosure and drain are checked here. ``status`` is ``passed`` only if every
    check passes. ``audit_passed`` is the check S0z applies: it also refuses any
    ``not_covered`` scope item unless the owner explicitly waives it (default refuse).
``index`` (stage S0e-I)
    ``control/collection-index.json`` binding the seven data-v2 S0e inputs, refused unless
    the audit passed and nothing changed since; then ``control/controller-record.json``,
    which the driver merges with the collector pin record for S0f.

Every subcommand runs as its own stage under ``run_research_stage.py``; none accounts CPU.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import male_navigation_v4_controls as ctl  # noqa: E402

COMMANDS = {'launch': 'S0e', 'drain': 'S0e-D', 'audit': 'S0e-A', 'index': 'S0e-I'}
# Kill targets from amendment_1.lane_budget (k=1; worst case k x (kill + 5)).
UNITS = {'S0e': {'runtime_max_sec': 2240}, 'S0e-D': {'runtime_max_sec': 30},
         'S0e-A': {'runtime_max_sec': 150}, 'S0e-I': {'runtime_max_sec': 30}}
NORMAL_RETURN_SECONDS = 2210
LIMITS = {'normal_return_seconds': NORMAL_RETURN_SECONDS}
CASES = ctl.driver.ADVICE_CASES
ADVICE_MAX_ROWS = ctl.driver.ADVICE_MAX_ROWS
CONTROL_DOCUMENTS = {'collection_terminal': 'terminal.json', 'collection_enclosing': 'enclosing.json',
                     'collector_supervisor': 'outer-launch/supervisor.json',
                     'launcher_supervisor': 'outer-supervisor/supervisor.json'}
DRAIN, AUDIT, INDEX = 'exec-drain.json', 'root-raw-audit.json', 'collection-index.json'
COLLECTOR_RECORD = 'collector-pin-record.json'
LOCATOR = COLLECTOR_RECORD + '.port-pins.json'   # written by the driver next to its pin record
INDEX_INPUTS = ('accepted_collection', *CONTROL_DOCUMENTS, 'exec_drain', 'root_raw_audit')
AUDIT_KIND = 'm7-navigation-v4-root-raw-audit-1'
WORKER = Path(__file__).resolve().parent/'audit_male_navigation_v4_s0e_raw.py'
WORKER_TIMEOUT = 120
V2_AUDIT_SCOPE = ('v2 root raw-audit scope: shared source/label/initial/contact validators plus independent raw contact '
                  'incidence, finite arrays, row/event/hash counts and cleanup; no inference or physics recomputation; '
                  'no useful-navigation qualification')
NOT_COVERED = []   # every v2 scope item is reproduced; S0z refuses any future entry unless waived


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    commands = {name: sub.add_parser(name) for name in COMMANDS}
    for name, command in commands.items():
        command.add_argument('--go', help=f'GO record naming stage {COMMANDS[name]} and the protocol sha256 (absent: plan only)')
        command.add_argument('--plan-only', action='store_true', help='Print the plan (the default without --go)')
        command.add_argument('--stage-root', help='S0e stage root: collection/ and control/')
    launch = commands['launch']
    for flag in ('--worktree', '--assets'): launch.add_argument(flag)
    launch.add_argument('--previous-pins', nargs='+', default=[], help='S0d seed 10, 11, 12 pin records, in order')
    launch.add_argument('--corpus', nargs='+', default=[], help='Corpus inventory paths (S0a-S0c outputs)')
    launch.add_argument('--bundle', nargs='+', default=[], help='Learner bundle inventory paths (S0d outputs)')
    launch.add_argument('--launcher', help=argparse.SUPPRESS)
    launch.add_argument('--invocation-sha256', help=argparse.SUPPRESS)
    for flag in ('--receipt-dir', '--ledger'): commands['drain'].add_argument(flag)
    commands['audit'].add_argument('--port-worktree', help='Verified T-e port worktree whose readers the audit imports')
    return parser.parse_args(argv)


def _paths(args, *names):
    return {n: str(ctl.absolute('--' + n.replace('_', '-'), getattr(args, n))) for n in names}


def _layout(cfg):
    root = Path(cfg['stage_root'])
    control = root/'control'
    return {'collection': str(root/'collection'), 'control_root': str(control), 'drain': str(control/DRAIN),
            'audit': str(control/AUDIT), 'index': str(control/INDEX), 'locator': str(control/LOCATOR),
            'collector_record': str(control/COLLECTOR_RECORD)}


# --------------------------------------------------------------------------- S0e launcher

def configure_launch(args, *, driver_path, limits, **_):
    cfg = _paths(args, 'worktree', 'assets', 'stage_root')
    for name in ('previous_pins', 'corpus', 'bundle'):
        if not getattr(args, name): raise ctl.Refusal(f'--{name.replace("_", "-")} needs at least one absolute path')
        cfg[name] = [str(ctl.absolute(f'--{name.replace("_", "-")}', v)) for v in getattr(args, name)]
    # The source part is git-tracked files only, so an untracked worktree path stays allowed.
    roots = [cfg['assets'], *cfg['corpus'], *cfg['bundle'], *cfg['previous_pins'], str(Path(cfg['worktree'])/'upstream')]
    root = cfg['stage_root']
    if ctl.driver.under(cfg['worktree'], root) or any(ctl.driver.under(root, r) or ctl.driver.under(r, root) for r in roots):
        raise ctl.Refusal('--stage-root overlaps an inventoried input')
    cfg.update(_layout(cfg), output=_layout(cfg)['collection'])
    return {**cfg, 'driver': str(driver_path), 'python': sys.executable, 'limits': dict(limits)}


def collector_command(cfg):
    return [cfg['python'], '-B', cfg['driver'], '--stage', 'S0e', '--worktree', cfg['worktree'],
            '--previous-pins', *cfg['previous_pins'], '--go', cfg.get('go') or '<GO>',
            '--pin-record-out', cfg['collector_record'], '--',
            '--repo', cfg['worktree'], '--assets', cfg['assets'], '--output', cfg['output']]


def controls(cfg):
    names = [__file__, ctl.__file__, cfg['driver'], cfg['go'], *cfg['previous_pins']]
    return {str(Path(n).resolve()): ctl.driver.sha256_file(n) for n in names}


def inventory(cfg):
    worktree = Path(cfg['worktree'])
    return ctl.inventory({'source': ctl.git_tracked(worktree), 'upstream': [worktree/'upstream/fly-gym'],
                          'assets': [Path(cfg['assets'])], 'corpus': [Path(p) for p in cfg['corpus']],
                          'bundle': [Path(p) for p in cfg['bundle']]})


def launcher(path, sha256):
    """Inner launcher: inventories, inner sampler, collector supervision, terminal.json."""
    cfg = ctl.read_invocation(path, sha256)
    control, limit = Path(cfg['control_root']), cfg['limits']['normal_return_seconds']
    ctl.on_sigterm(); ctl.set_subreaper()
    sampler = ctl.Sampler().start()
    terminal = {'schema': 'm7-navigation-v4-s0e-terminal-1', 'stage': 'S0e', 'normal_return_limit_seconds': limit}
    failure, before, controls_before = None, None, None
    try:
        terminal['head'] = ctl.git_head(cfg['worktree'])
        controls_before, before = controls(cfg), inventory(cfg)
        ctl.write_json(control/'before.json', before)
        remaining = limit - (time.monotonic() - cfg['started_monotonic'])
        record = ctl.supervise(collector_command(cfg), remaining, control/'outer-launch', env=ctl.child_env(),
                               cwd=cfg['worktree'], sampler=sampler)
        terminal['collector_supervisor'] = ctl.write_json(control/CONTROL_DOCUMENTS['collector_supervisor'], record)
        if record['status'] != 'completed' or record['returncode'] != 0:
            failure = f'collector supervision {record["status"]} with returncode {record["returncode"]}'
    except Exception as error:
        failure = f'{type(error).__name__}: {error}'[:1024]
    cleanup = ctl.cleanup(sampler)
    after, controls_after = None, None
    try:
        after, controls_after = inventory(cfg), controls(cfg)
        ctl.write_json(control/'after.json', after)
    except Exception as error:
        failure = failure or f'after inventory: {type(error).__name__}: {error}'[:1024]
    report_path = Path(cfg['output'])/'report.json'
    report = ctl.binding(report_path) if report_path.is_file() else None
    report_status = ctl.read_json(report_path).get('status') if report else None
    terminal.update({'controls_unchanged': controls_before is not None and controls_before == controls_after,
                     'cleanup': cleanup, 'inventories_unchanged': before is not None and after is not None and before['sha256'] == after['sha256'],
                     'before_inventory_sha256': before and before['sha256'], 'after_inventory_sha256': after and after['sha256'],
                     'inventory_counts': before and before['counts'], 'report_sha256': report and report['sha256'],
                     'report_status': report_status})
    checks = ((report_status == 'completed-collection', 'no completed-collection report.json'),
              (Path(cfg['collector_record']).is_file(), 'the driver published no collector pin record'),
              (terminal['inventories_unchanged'], 'before/after inventories differ'),
              (terminal['controls_unchanged'], 'control files changed'),
              (ctl.clean(cleanup), 'inner cleanup found survivors, forced signals, sampler errors or PID conflicts'))
    failure = failure or next((reason for ok, reason in checks if not ok), None)
    terminal['status'] = 'failed-collection' if failure else 'completed-collection'
    if failure: terminal['error'] = failure
    ctl.write_json(control/CONTROL_DOCUMENTS['collection_terminal'], terminal)
    return 1 if failure else 0


def run_launch(cfg):
    """Enclosing supervisor: outer inventory and sampler around the launcher process."""
    control, limit = Path(cfg['control_root']), cfg['limits']['normal_return_seconds']
    control.mkdir(parents=True)
    cfg['started_monotonic'] = started = time.monotonic()
    invocation = ctl.write_json(control/'invocation.json', cfg)
    ctl.on_sigterm(); ctl.set_subreaper()
    sampler = ctl.Sampler().start()
    enclosing = {'schema': 'm7-navigation-v4-s0e-enclosing-1', 'stage': 'S0e', 'normal_return_limit_seconds': limit}
    failure, controls_before, before, record = None, None, None, None
    try:
        controls_before, before = controls(cfg), inventory(cfg)
        ctl.write_json(control/'outer-before.json', before)
        command = [sys.executable, '-B', str(Path(__file__).resolve()), 'launch', '--launcher', invocation['path'],
                   '--invocation-sha256', invocation['sha256']]
        # The launcher owns the 2,210 s collector deadline; this grace only lets it retain its evidence.
        record = ctl.supervise(command, limit - (time.monotonic() - started) + 2*ctl.STOP_GRACE, control/'outer-supervisor',
                               env=ctl.child_env(), sampler=sampler)
        enclosing['launcher_supervisor'] = ctl.write_json(control/CONTROL_DOCUMENTS['launcher_supervisor'], record)
    except Exception as error:
        failure = f'{type(error).__name__}: {error}'[:1024]
    cleanup = ctl.cleanup(sampler)
    after, controls_after = None, None
    try:
        after, controls_after = inventory(cfg), controls(cfg)
        ctl.write_json(control/'outer-after.json', after)
    except Exception as error:
        failure = failure or f'outer after inventory: {type(error).__name__}: {error}'[:1024]
    terminal_path = control/CONTROL_DOCUMENTS['collection_terminal']
    terminal = ctl.read_json(terminal_path) if terminal_path.is_file() else {}
    enclosing.update({'controls_unchanged': controls_before is not None and controls_before == controls_after,
                      'outer_cleanup': cleanup, 'outer_inventory_unchanged': before is not None and after is not None and before['sha256'] == after['sha256'],
                      'outer_before_inventory_sha256': before and before['sha256'], 'outer_after_inventory_sha256': after and after['sha256'],
                      'terminal': ctl.binding(terminal_path) if terminal else None, 'wall_seconds': time.monotonic() - started})
    checks = ((record is not None and record['status'] == 'completed' and record['returncode'] == 0, 'launcher supervision failed'),
              (terminal.get('status') == 'completed-collection', 'terminal is not completed-collection'),
              (enclosing['outer_inventory_unchanged'], 'outer inventories differ'),
              (enclosing['controls_unchanged'], 'control files changed'),
              (ctl.clean(cleanup), 'outer cleanup found survivors, forced signals, sampler errors or PID conflicts'),
              (enclosing['wall_seconds'] <= limit, f'normal return exceeded {limit} s'))
    failure = failure or next((reason for ok, reason in checks if not ok), None)
    enclosing['status'] = 'failed-collection' if failure else 'completed-collection'
    if failure: enclosing['error'] = failure
    ctl.write_json(control/CONTROL_DOCUMENTS['collection_enclosing'], enclosing)
    ctl.emit({'mode': 'go', 'stage': 'S0e', 'status': enclosing['status'], 'stage_root': cfg['stage_root'],
              **({'error': failure} if failure else {})})
    return 1 if failure else 0


def precheck_launch(cfg, expected_head):
    expected_head = ctl.port_commit('T-e') if expected_head is None else expected_head
    if (head := ctl.git_head(cfg['worktree'])) != expected_head:
        raise ctl.Refusal(f'Worktree HEAD {head} is not the T-e port commit {expected_head}')
    ctl.fresh('--stage-root', cfg['stage_root'])


# --------------------------------------------------------------------------- S0e-D drain receipt

def configure_drain(args, **_):
    cfg = _paths(args, 'stage_root', 'receipt_dir', 'ledger')
    return {**cfg, **_layout(cfg)}


def run_drain(cfg):
    ctl.fresh('--stage-root control/' + DRAIN, cfg['drain'])
    rows = [json.loads(line) for line in ctl.driver.read_bounded(cfg['ledger']).decode().splitlines() if line.strip()]
    charged = [r for r in rows if (r.get('lane'), r.get('stage'), r.get('event'), r.get('receipt_dir')) ==
               (ctl.LANE, 'S0e', 'charged', cfg['receipt_dir'])]
    if len(charged) != 1: raise ctl.Refusal('The ledger must hold exactly one charged navigation/S0e row for this receipt dir')
    receipt_path = Path(cfg['receipt_dir'])/'receipt.json'
    receipt = ctl.read_json(receipt_path) if receipt_path.is_file() else {}
    unit, workload = charged[0].get('unit_returncode'), receipt.get('returncode')
    complete = receipt.get('complete') is True
    cgroup = receipt.get('cgroup')
    present = bool(cgroup) and Path(cgroup).exists()
    cgroup_pids = sorted(int(p) for procs in (Path(cgroup).rglob('cgroup.procs') if present else [])
                         for p in procs.read_text().split())
    killed = sorted(receipt.get('survivors_killed') or [])
    # The unit exit status, unless no complete receipt exists or it claims success over a failed exec.
    exitcode = None if not complete or type(unit) is not int or (unit == 0 and workload != 0) else unit
    doc = {'kind': 'm7-navigation-v4-exec-drain-1', 'stage': 'S0e-D', 'source_stage': 'S0e',
           'protocol_sha256': cfg['protocol_sha256'], 'receipt': ctl.binding(receipt_path) if receipt else None,
           'ledger_row': charged[0], 'unit_returncode': unit, 'workload_returncode': workload, 'receipt_complete': complete,
           'drained': receipt.get('drained'), 'cgroup': cgroup, 'cgroup_present': present, 'cgroup_pids': cgroup_pids,
           'exec_exitcode': exitcode, 'matching_survivors': sorted(set(killed) | set(cgroup_pids)),
           'forced_signals': [{'signal': 'cgroup.kill', 'pids': killed}] if killed else [],
           'basis': 'systemd unit exit status (run_research_stage ledger) and an empty unit cgroup'}
    clean = exitcode == 0 and doc['drained'] is True and not doc['matching_survivors'] and not doc['forced_signals']
    doc['status'] = 'drained' if clean else 'not-drained'
    if not clean: doc['error'] = 'S0e unit did not exit 0 with a complete, drained, empty cgroup'
    ctl.emit({'mode': 'go', 'stage': 'S0e-D', 'status': doc['status'], 'receipt': ctl.write_json(cfg['drain'], doc)})
    return 0 if clean else 1


# --------------------------------------------------------------------------- S0e-A root raw audit

def configure_audit(args, **_):
    cfg = _paths(args, 'stage_root', 'port_worktree')
    return {**cfg, **_layout(cfg)}


def precheck_audit(cfg, expected_head):
    """The readers come only from a clean, detached T-e port worktree at the recorded port commit."""
    expected_head = ctl.port_commit('T-e') if expected_head is None else expected_head
    ctl.driver.verify_worktree(cfg['port_worktree'], {}, commit=expected_head)
    ctl.fresh('--stage-root control/' + AUDIT, cfg['audit'])


def _inputs(cfg):
    control = Path(cfg['control_root'])
    return {'accepted_collection': Path(cfg['collection'])/'report.json',
            **{k: control/rel for k, rel in CONTROL_DOCUMENTS.items()}, 'exec_drain': Path(cfg['drain'])}


def _supervisor_ok(value):
    return value.get('status') == 'completed' and value.get('returncode') == 0 and type(value.get('returncode')) is int \
        and 'error' not in value and 'failure' not in value


def port_readers(cfg):
    """Run the raw worker under -I with only the T-e port on sys.path and the S0e locator."""
    env = {**ctl.child_env(), ctl.driver.PORT_LOCATOR_ENV: cfg['locator']}
    config = json.dumps({'port_root': cfg['port_worktree'], 'collection': cfg['collection']})
    done = subprocess.run([sys.executable, '-I', '-B', str(WORKER), config], env=env, cwd=cfg['port_worktree'],
                          capture_output=True, text=True, timeout=WORKER_TIMEOUT, stdin=subprocess.DEVNULL)
    lines = [line for line in done.stdout.splitlines() if line.startswith('{')]
    if done.returncode != 0 or len(lines) != 1:
        raise ctl.Refusal(f'Raw-audit worker failed ({done.returncode}): {done.stderr[-512:]}')
    return json.loads(lines[0])


def run_audit(cfg):
    started = time.monotonic()
    collection = Path(cfg['collection'])
    bindings = {k: ctl.binding(p) if p.is_file() else None for k, p in _inputs(cfg).items()}
    docs = {k: ctl.read_json(b['path'], b['sha256']) if b else {} for k, b in bindings.items()}
    report, checks, case_rows, outcomes, raw = docs['accepted_collection'], [], {}, {}, {}

    def check(name, test):
        try: ok, detail = test()
        except Exception as error: ok, detail = False, f'{type(error).__name__}: {error}'[:512]
        checks.append({'name': name, 'ok': bool(ok), 'detail': detail})

    def rows():
        for case in CASES:
            result = ctl.read_json(collection/case/'result.json')
            if (result.get('status') != 'completed-recording' or result.get('engine_closed') is not True or
                    result.get('callback_restored') is not True or
                    result.get('contact_incidence') != report['cases'][case].get('contact_incidence')):
                return False, f'{case}: owner result is not a closed, completed, incidence-bound recording'
            case_rows[case], outcomes[case] = len(result['rows']), result.get('outcome')
        bad = {c: n for c, n in case_rows.items() if not 0 < n <= ADVICE_MAX_ROWS}
        total = sum(case_rows.values())
        return not bad and total == report.get('numeric_ticks'), f'rows {total} vs numeric_ticks {report.get("numeric_ticks")}; out of bounds {bad}'

    def artifacts():
        indexed = report.get('artifacts_sha256') or {}
        wrong = [rel for rel, h in indexed.items() if not (collection/rel).is_file() or ctl.driver.sha256_file(collection/rel) != h]
        return bool(indexed) and not wrong, f'{len(indexed)} producer-indexed files; mismatched {wrong[:8]}'

    def enclosure():
        terminal, enclosing = docs['collection_terminal'], docs['collection_enclosing']
        ok = (terminal.get('status') == enclosing.get('status') == 'completed-collection' and
              terminal.get('controls_unchanged') is True and enclosing.get('controls_unchanged') is True and
              ctl.clean(terminal.get('cleanup', {})) and ctl.clean(enclosing.get('outer_cleanup', {})) and
              terminal.get('inventories_unchanged') is True and enclosing.get('outer_inventory_unchanged') is True and
              'error' not in terminal and 'error' not in enclosing and
              terminal.get('report_sha256') == (bindings['accepted_collection'] or {}).get('sha256') and
              all(_supervisor_ok(docs[k]) for k in ('collector_supervisor', 'launcher_supervisor')))
        return ok, 'terminal/enclosing/supervisor statuses, cleanups, inventories, controls and report binding'

    def drain():
        d = docs['exec_drain']
        return (type(d.get('exec_exitcode')) is int and d['exec_exitcode'] == 0 and d.get('matching_survivors') == [] and
                d.get('forced_signals') == [] and d.get('status') == 'drained'), 'exec drain receipt'

    def readers():
        raw.update(port_readers(cfg))
        return (raw['cases'] == list(CASES) and raw['forbidden_modules'] == [] and raw['local_modules_outside_port'] == [] and
                Path(raw['reader_origin']).is_relative_to(Path(cfg['port_worktree']).resolve()),
                {k: raw[k] for k in ('forbidden_modules', 'local_modules_outside_port', 'reader_origin')})

    def per_owner(test, describe):
        owners = raw.get('owners') or []
        bad = [o['case'] for o in owners if not test(o)]
        return len(owners) == len(CASES) and not bad, {o['case']: describe(o) for o in owners if o['case'] in bad} or 'all owners'

    check('inputs', lambda: (all(bindings.values()), {k: bool(v) for k, v in bindings.items()}))
    check('report', lambda: (report.get('status') == 'completed-collection' and report.get('qualification_claims') == [] and
                             report.get('source_pins') == report.get('final_source_pins') and
                             report.get('assets_before') == report.get('assets_after') and
                             report.get('assets_before', {}).get('ok') is True and
                             report.get('identities_before') == report.get('identities_after') and 'error' not in report,
                             'report status, pins, assets and learner identities'))
    check('owners', lambda: (report.get('owners_completed') == 12 and list(report.get('cases', {})) == list(CASES),
                             'twelve owners in scene x learner order'))
    check('rows', rows)
    check('snapshots', lambda: ((n := len(list(collection.rglob('*.snp')))) == 12, f'{n} initial snapshots'))
    check('artifacts', artifacts)
    check('enclosure', enclosure)
    check('drain', drain)
    check('reader_isolation', readers)
    check('shared_validators', lambda: per_owner(lambda o: 'error' not in o and 'validator_error' not in o and o.get('admitted') == o.get('rows'),
                                                 lambda o: o.get('validator_error') or o.get('error') or o.get('admitted')))
    check('contact_incidence', lambda: per_owner(lambda o: o.get('incidence_matches_result') is True and o.get('incidence_matches_report') is True,
                                                 lambda o: 'rebuilt incidence differs from the owner result/report'))
    check('finite_arrays', lambda: per_owner(lambda o: o.get('nonfinite_count') == 0, lambda o: o.get('nonfinite')))
    check('tick_counts', lambda: per_owner(lambda o: o.get('ticks') == o.get('rows') == case_rows.get(o['case']) and (o.get('events') or 0) > 0,
                                           lambda o: {k: o.get(k) for k in ('ticks', 'rows', 'events')}))
    files = [p for p in collection.rglob('*') if p.is_file()]
    failures = [c for c in checks if not c['ok']]
    doc = {'kind': AUDIT_KIND, 'stage': 'S0e-A', 'status': 'failed' if failures else 'passed', 'protocol_sha256': cfg['protocol_sha256'],
           'scope': V2_AUDIT_SCOPE, 'not_covered': list(NOT_COVERED), 'native_or_model_import': bool(raw.get('forbidden_modules')),
           'port_worktree': cfg['port_worktree'], 'port_head': ctl.git_head(cfg['port_worktree']), 'inputs': bindings,
           'checks': checks, 'failures': failures, 'case_rows': case_rows, 'outcomes': outcomes,
           'pair_instances_by_type': raw.get('pair_instances_by_type'),
           'events': {o['case']: o.get('events') for o in raw.get('owners', [])},
           'output_ledger': {'files': len(files), 'bytes': sum(p.stat().st_size for p in files)},
           'seconds': time.monotonic() - started}
    ctl.emit({'mode': 'go', 'stage': 'S0e-A', 'status': doc['status'], 'audit': ctl.write_json(cfg['audit'], doc)})
    return 1 if failures else 0


def audit_passed(path, expected_sha256=None, *, waivers=()):
    """The S0z check: a passed S0e-A document; any not-covered scope item needs an explicit owner waiver."""
    doc = ctl.read_json(path, expected_sha256)
    if doc.get('kind') != AUDIT_KIND or doc.get('status') != 'passed' or doc.get('failures') != []:
        raise ctl.Refusal(f'S0e-A root raw audit has not passed: {path}')
    covered = doc.get('not_covered')
    unwaived = [item for item in covered if item not in waivers] if isinstance(covered, list) else ['<missing not_covered list>']
    if unwaived:
        raise ctl.Refusal(f'S0e-A leaves v2 root-audit scope uncovered without an owner waiver: {unwaived}')
    return doc


# --------------------------------------------------------------------------- S0e-I index publisher

def configure_index(args, **_):
    cfg = _paths(args, 'stage_root')
    return {**cfg, **_layout(cfg)}


def run_index(cfg):
    ctl.fresh('--stage-root control/' + INDEX, cfg['index'])
    audit = audit_passed(cfg['audit'])
    inputs = {**_inputs(cfg), 'root_raw_audit': Path(cfg['audit'])}
    bindings = {k: ctl.binding(p) for k, p in inputs.items()}
    changed = [k for k, b in audit['inputs'].items() if bindings[k] != b]
    if changed: raise ctl.Refusal(f'Inputs changed since the audit: {changed}')
    docs = {k: ctl.read_json(b['path'], b['sha256']) for k, b in bindings.items()}
    terminal, enclosing, drain = docs['collection_terminal'], docs['collection_enclosing'], docs['exec_drain']
    report = docs['accepted_collection']
    cleanups = (terminal['cleanup'], enclosing['outer_cleanup'])
    index = {'kind': 'm7-navigation-v4-collection-index-1', 'stage': 'S0e-I', 'status': 'completed-collection',
             'protocol_sha256': cfg['protocol_sha256'], 'producer_commit': terminal['head'], 'qualification_claims': [],
             'immutable_inputs': {k: bindings[k] for k in INDEX_INPUTS},
             'coverage': {'owners_completed': report['owners_completed'], 'rows': report['numeric_ticks'],
                          'cases': [{'case': c, 'intervals': audit['case_rows'][c], 'outcome': audit['outcomes'][c],
                                     'events': audit['events'].get(c)} for c in CASES],
                          'pair_instances_by_type': audit['pair_instances_by_type'],
                          'output_files': audit['output_ledger']['files'], 'output_bytes': audit['output_ledger']['bytes']},
             'disposition': {'exec_exitcode': drain['exec_exitcode'], 'unit_returncode': drain['unit_returncode'],
                             'collector_supervisor_seconds': docs['collector_supervisor']['elapsed_seconds'],
                             'launcher_supervisor_seconds': docs['launcher_supervisor']['elapsed_seconds'],
                             'enclosing_wall_seconds': enclosing['wall_seconds'],
                             'normal_through_return_limit_seconds': enclosing['normal_return_limit_seconds'],
                             **{k: [x for c in cleanups for x in c[k]] for k in ctl.CLEAN_KEYS},
                             'union_sampled_identities': len({(o['pid'], o['start_ticks']) for c in cleanups
                                                              for o in c['observed_owned_processes']}),
                             'inventories_and_controls_unchanged': True},
             'audits': {'root_raw': {'status': audit['status'], 'seconds': audit['seconds'],
                                     'sha256': bindings['root_raw_audit']['sha256'], 'not_covered': audit['not_covered']}}}
    published = ctl.write_json(cfg['index'], index)
    record = ctl.write_controller_record('S0e', cfg['stage_root'], [cfg['collector_record']], cfg['protocol_sha256'])
    ctl.emit({'mode': 'go', 'stage': 'S0e-I', 'status': 'published', 'index': published, 'controller_record': record})
    return 0


# --------------------------------------------------------------------------- entry

CONFIGURE = {'launch': configure_launch, 'drain': configure_drain, 'audit': configure_audit, 'index': configure_index}
RUN = {'launch': run_launch, 'drain': run_drain, 'audit': run_audit, 'index': run_index}


def main(argv=None, *, driver_path=ctl.DRIVER, limits=None, expected_head=None, protocol_sha256=None, require_unit=True):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parse(argv)
    if args.command == 'launch' and args.launcher: return launcher(args.launcher, args.invocation_sha256)
    stage = COMMANDS[args.command]
    try:
        protocol_sha256 = ctl.protocol_gate(protocol_sha256)
        if args.go is not None and args.plan_only: raise ctl.Refusal('--plan-only and --go are mutually exclusive')
        cfg = CONFIGURE[args.command](args, driver_path=driver_path, limits=LIMITS if limits is None else limits)
        cfg.update(stage=stage, protocol_sha256=protocol_sha256, go=None if args.go is None else str(ctl.absolute('--go', args.go)))
        if args.go is None:
            plan = {'mode': 'plan-only', **cfg, 'unit_command': ctl.unit_command(
                stage, UNITS[stage]['runtime_max_sec'], [sys.executable, '-B', str(Path(__file__).resolve()), *argv, '--go', '<GO>'])}
            if args.command == 'launch': plan['collector_command'] = collector_command(cfg)
            ctl.emit(plan); return 0
        cfg['go_sha256'] = ctl.go_gate(cfg['go'], stage, protocol_sha256)
        if require_unit and not ctl.research_stage_unit():
            raise ctl.Refusal(f'{stage} must run as stage {stage} inside a run_research_stage.py unit (work leaf)')
        if args.command == 'launch': precheck_launch(cfg, expected_head)
        if args.command == 'audit': precheck_audit(cfg, expected_head)
        return RUN[args.command](cfg)
    except (ctl.Refusal, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        ctl.emit({'mode': 'go' if args.go else 'plan-only', 'stage': stage, 'status': 'refused',
                  'reason': str(error) if isinstance(error, ctl.Refusal) else f'{type(error).__name__}: {error}'})
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
