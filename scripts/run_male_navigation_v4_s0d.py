"""MaleCNS v4 S0d controller: seeds 10, 11, 12 of the ported recovery trainer once each; plan-only by default.

Reconstructs the lost ``supervise.py`` (Amendment 1, reconstructed_controllers S0d), bound to
``docs/reports/m7-recovery-training.{md,json}`` at ``217cbee``:

* each pair is one driver invocation (``regenerate_male_navigation_v4.py --stage S0d``) of the
  T-d port ``train_male_recovery.py --data-manifest M --training-seed N --output <root>/seed-N``;
  the driver verifies the port tree, writes the locator and the per-seed pin record;
* pairs: 600 s internal (normal exit after it is a failure) / 660 s supervised (group killed);
  stage: 2,100 s internal (bounds every pair) / 2,160 s enclosing (outer supervisor);
* a 0.25 s PID/start sampler over every descendant, with subreaper containment and cleanup
  ``{sampler_stopped, sample_errors, forced_signals, survivors}``;
* a five-part before/after inventory (tracked 355, upstream 122 asserted; raw-document,
  model/production and runtime parts are caller-listed, v2 counts 181/16/7 kept descriptive);
* after the first failure the remaining pairs stay ``not_started``.

Outputs (all under the T-d worktree, which is the recovery index ``producer_root``):
``<control>/terminal.json`` (training_terminal), ``<control>/outer-supervisor/supervisor.json``
(training_supervisor) and, after a pass, ``<control>/recovery-index-values.json`` holding the
S0d fill values the ported ``male_recovery_research._gate`` reads. The controller never
accounts CPU: it must run as stage S0d under ``run_research_stage.py`` (navigation lane).
"""
import argparse
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import male_navigation_v4_controls as ctl  # noqa: E402

STAGE = 'S0d'
SEEDS = (10, 11, 12)
LIMITS = {'pair_internal_seconds': 600, 'pair_supervised_seconds': 660,
          'stage_internal_seconds': 2100, 'stage_supervised_seconds': 2160}
INVENTORY_PARTS = ('tracked', 'upstream', 'raw_documents', 'model_production', 'runtime')
V2_REFERENCE_COUNTS = {'tracked': 355, 'upstream': 122, 'raw_documents': 181, 'model_production': 16, 'runtime': 7}
# Derivable from surviving bytes: every tracked regular file at 19d275d (ports add none) and upstream 8d96459.
EXPECTED_COUNTS = {'tracked': 355, 'upstream': 122}
UNIT = {'stage': STAGE, 'runtime_max_sec': 2160, 'k': 1}
TERMINAL_SCHEMA = 'm7-navigation-v4-s0d-terminal-1'


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--go', help='GO record naming stage S0d and the protocol sha256 (absent: plan only)')
    parser.add_argument('--plan-only', action='store_true', help='Print the plan (the default without --go)')
    parser.add_argument('--worktree', help='T-d port worktree (detached at the port commit)')
    parser.add_argument('--previous-pins', help='S0c pin record')
    parser.add_argument('--data-manifest', help='S0c data-manifest.json')
    parser.add_argument('--output-root', help='Fresh aggregate root inside the worktree; pairs go to seed-N')
    parser.add_argument('--control-root', help='Fresh control root inside the worktree, disjoint from the output root')
    parser.add_argument('--raw-documents', nargs='+', default=[], help='Fixed raw/document inventory paths')
    parser.add_argument('--model-production', nargs='+', default=[], help='Original-model/production inventory paths')
    parser.add_argument('--runtime', nargs='+', default=[], help='Runtime metadata/entrypoint inventory paths')
    parser.add_argument('--inner', help=argparse.SUPPRESS)
    parser.add_argument('--invocation-sha256', help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def configure(args, *, driver_path, limits, expected_counts, protocol_sha256):
    if args.go is not None and args.plan_only: raise ctl.Refusal('--plan-only and --go are mutually exclusive')
    names = ('worktree', 'previous_pins', 'data_manifest', 'output_root', 'control_root')
    paths = {n: str(ctl.absolute('--' + n.replace('_', '-'), getattr(args, n))) for n in names}
    parts = {}
    for part in INVENTORY_PARTS[2:]:
        values = getattr(args, part)
        if not values: raise ctl.Refusal(f'--{part.replace("_", "-")} needs at least one absolute path')
        parts[part] = [str(ctl.absolute('--' + part.replace('_', '-'), v)) for v in values]
    worktree, output, control = (Path(paths[n]) for n in ('worktree', 'output_root', 'control_root'))
    for name, path in (('--output-root', output), ('--control-root', control)):
        if path == worktree or not ctl.driver.under(path, worktree):
            raise ctl.Refusal(f'{name} must be inside the port worktree (the recovery index producer_root): {path}')
    if ctl.driver.under(output, control) or ctl.driver.under(control, output):
        raise ctl.Refusal('--output-root and --control-root must be disjoint')
    return {'stage': STAGE, 'protocol_sha256': protocol_sha256, 'go': None if args.go is None else str(ctl.absolute('--go', args.go)),
            **paths, 'inventory_paths': parts, 'driver': str(driver_path), 'python': sys.executable,
            'limits': dict(limits), 'expected_counts': dict(expected_counts)}


def pair_command(cfg, seed):
    return [cfg['python'], '-B', cfg['driver'], '--stage', STAGE, '--worktree', cfg['worktree'],
            '--previous-pins', cfg['previous_pins'], '--go', cfg['go'] or '<GO>',
            '--pin-record-out', f'{cfg["control_root"]}/pairs/seed-{seed}/pin-record.json', '--',
            '--data-manifest', cfg['data_manifest'], '--training-seed', str(seed), '--output', f'{cfg["output_root"]}/seed-{seed}']


def inventory(cfg):
    worktree = Path(cfg['worktree'])
    return ctl.inventory({'tracked': ctl.git_tracked(worktree), 'upstream': [worktree/'upstream/fly-gym'],
                          **{k: [Path(p) for p in v] for k, v in cfg['inventory_paths'].items()}})


# --------------------------------------------------------------------------- inner: terminal controller

def inner(path, sha256):
    cfg = ctl.read_invocation(path, sha256)
    limits, control, started = cfg['limits'], Path(cfg['control_root']), time.monotonic()
    ctl.on_sigterm(); ctl.set_subreaper()
    sampler = ctl.Sampler().start()
    pairs = [{'training_seed': s, 'status': 'not_started', 'output': f'{cfg["output_root"]}/seed-{s}'} for s in SEEDS]
    terminal = {'schema': TERMINAL_SCHEMA, 'stage': STAGE, 'status': 'running', 'protocol_sha256': cfg['protocol_sha256'],
                'limits': limits, 'v2_reference_inventory_counts': V2_REFERENCE_COUNTS, 'qualification_claims': [],
                'pairs': pairs}
    failure, before = None, None
    try:
        terminal['head'] = ctl.git_head(cfg['worktree'])
        before = inventory(cfg)
        ctl.write_json(control/'before.json', before)
        if any(before['counts'][k] != v for k, v in cfg['expected_counts'].items()):
            raise ctl.Refusal(f'inventory counts {before["counts"]} differ from {cfg["expected_counts"]}')
        for pair in pairs:
            seed, remaining = pair['training_seed'], limits['stage_internal_seconds'] - (time.monotonic() - started)
            if remaining <= 0:
                failure = f'stage internal deadline {limits["stage_internal_seconds"]} s reached before seed {seed}'; break
            supervision = ctl.supervise(pair_command(cfg, seed), min(limits['pair_supervised_seconds'], remaining),
                                        control/'pairs'/f'seed-{seed}', env=ctl.child_env(), cwd=cfg['worktree'], sampler=sampler)
            pair['supervision'] = supervision
            if supervision['status'] != 'completed' or supervision['returncode'] != 0:
                failure = f'seed {seed} supervision {supervision["status"]} with returncode {supervision["returncode"]}'
            elif supervision['elapsed_seconds'] > limits['pair_internal_seconds']:
                failure = f'seed {seed} exceeded the pair internal deadline {limits["pair_internal_seconds"]} s'
            elif not (Path(pair['output'])/'report.json').is_file():
                failure = f'seed {seed} exited normally without report.json'
            if failure: pair['status'] = 'failed'; break
            pair['status'], pair['content_sha256'] = 'completed', ctl.tree_sha(pair['output'])
    except Exception as error:
        failure = f'{type(error).__name__}: {error}'[:1024]
    cleanup = ctl.cleanup(sampler)
    after = None
    try:
        after = inventory(cfg); ctl.write_json(control/'after.json', after)
    except Exception as error:
        failure = failure or f'after inventory: {type(error).__name__}: {error}'[:1024]
    completed = [p for p in pairs if p['status'] == 'completed']
    stage_seconds = time.monotonic() - started
    terminal.update({
        'inventories_unchanged': before is not None and after is not None and before['sha256'] == after['sha256'],
        'before_inventory_sha256': before and before['sha256'], 'after_inventory_sha256': after and after['sha256'],
        'inventory_counts': before and before['counts'],
        'completed_pair_content_unchanged': bool(completed) and all(ctl.tree_sha(p['output']) == p['content_sha256'] for p in completed),
        'cleanup': cleanup, 'stage_seconds': stage_seconds})
    checks = ((len(completed) == len(SEEDS), 'not every pair completed'),
              (terminal['inventories_unchanged'], 'before/after inventories differ'),
              (terminal['completed_pair_content_unchanged'], 'completed pair content changed'),
              (ctl.clean(cleanup), 'cleanup found survivors, forced signals or sampler errors'),
              (stage_seconds <= limits['stage_internal_seconds'], 'stage internal deadline exceeded'))
    failure = failure or next((reason for ok, reason in checks if not ok), None)
    terminal['status'] = 'failed-research-training' if failure else 'passed-research-training'
    if failure: terminal['failure'] = failure
    ctl.write_json(control/'terminal.json', terminal)
    return 1 if failure else 0


# --------------------------------------------------------------------------- outer: enclosing supervisor

def index_values(cfg, supervisor):
    """The S0d fields of the v4 recovery index (male-recovery-research-development-v1.json)."""
    worktree, control = Path(cfg['worktree']), Path(cfg['control_root'])
    rel = lambda p: Path(p).relative_to(worktree).as_posix()
    terminal = ctl.binding(control/'terminal.json'); value = ctl.read_json(terminal['path'], terminal['sha256'])
    return {'producer_root': str(worktree), 'training_source_commit': value['head'],
            'training_terminal': {'path': rel(terminal['path']), 'sha256': terminal['sha256']},
            'training_supervisor': {'path': rel(supervisor['path']), 'sha256': supervisor['sha256']},
            'before_after_inventory_sha256': value['before_inventory_sha256'],
            'pairs': [{'training_seed': p['training_seed'], 'directory': rel(p['output']),
                       'report_sha256': ctl.binding(Path(p['output'])/'report.json')['sha256']} for p in value['pairs']]}


def outer(cfg):
    control = Path(cfg['control_root'])
    control.mkdir(parents=True); Path(cfg['output_root']).mkdir(parents=True)
    invocation = ctl.write_json(control/'invocation.json', cfg)
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--inner', invocation['path'],
               '--invocation-sha256', invocation['sha256']]
    limit = cfg['limits']['stage_supervised_seconds']
    record = ctl.supervise(command, limit, control/'outer-supervisor', env=ctl.child_env())
    record['output'] = str(control/'terminal.json')
    supervisor = ctl.write_json(control/'outer-supervisor/supervisor.json', record)
    ok = record['status'] == 'completed' and record['returncode'] == 0 and record['elapsed_seconds'] <= limit
    summary = {'mode': 'go', 'stage': STAGE, 'status': 'completed' if ok else 'failed', 'supervisor': supervisor,
               'terminal': str(control/'terminal.json')}
    if ok: summary['recovery_index_values'] = ctl.write_json(control/'recovery-index-values.json', index_values(cfg, supervisor))
    ctl.emit(summary)
    return 0 if ok else 1


def main(argv=None, *, driver_path=ctl.DRIVER, limits=None, expected_head=None, expected_counts=None,
         protocol_sha256=None, require_unit=True):
    args = parse(sys.argv[1:] if argv is None else argv)
    if args.inner: return inner(args.inner, args.invocation_sha256)
    try:
        protocol_sha256 = ctl.protocol_gate(protocol_sha256)
        cfg = configure(args, driver_path=driver_path, limits=LIMITS if limits is None else limits,
                        expected_counts=EXPECTED_COUNTS if expected_counts is None else expected_counts,
                        protocol_sha256=protocol_sha256)
        if args.go is None:
            ctl.emit({'mode': 'plan-only', 'stage': STAGE, 'protocol_sha256': protocol_sha256, 'limits': cfg['limits'],
                      'pairs': [{'training_seed': s, 'command': pair_command(cfg, s)} for s in SEEDS],
                      'inventory_paths': cfg['inventory_paths'], 'expected_counts': cfg['expected_counts'],
                      'unit_command': ctl.unit_command(STAGE, UNIT['runtime_max_sec'], [sys.executable, '-B', str(Path(__file__).resolve()),
                                                                                         *(argv if argv is not None else sys.argv[1:]), '--go', '<GO>'])})
            return 0
        cfg['go_sha256'] = ctl.go_gate(cfg['go'], STAGE, protocol_sha256)
        if require_unit and not ctl.research_stage_unit():
            raise ctl.Refusal('S0d must run as stage S0d inside a run_research_stage.py unit (work leaf)')
        expected_head = ctl.port_commit('T-d') if expected_head is None else expected_head
        if (head := ctl.git_head(cfg['worktree'])) != expected_head:
            raise ctl.Refusal(f'Worktree HEAD {head} is not the T-d port commit {expected_head}')
        for name in ('output_root', 'control_root'): ctl.fresh('--' + name.replace('_', '-'), cfg[name])
    except (ctl.Refusal, OSError, ValueError, KeyError) as error:
        ctl.emit({'mode': 'go' if args.go else 'plan-only', 'stage': STAGE, 'status': 'refused',
                  'reason': str(error) if isinstance(error, ctl.Refusal) else f'{type(error).__name__}: {error}'})
        return 2
    return outer(cfg)


if __name__ == '__main__':
    raise SystemExit(main())
