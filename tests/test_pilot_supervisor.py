"""Parent contract tests using authored JSON/bytes and an injected runner only.

No real worker, model, graph, snapshot decoder, or native runtime is executed.
Authored production-shaped reports exercise validation and are not runtime proof.
"""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from palimpsest.storage import StorageBudget, StorageLimits, StorageLimitError

MODULE = Path(__file__).parents[1]/'paper/studies/change_audit_v1/pilot.py'
spec = importlib.util.spec_from_file_location('audit_pilot_parent_test',MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def save(path, value):
    path.write_bytes(p._json(value))
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Budget(StorageBudget):
    def __init__(self, root, *, ceiling=p.MAX_BYTES, fail_full=False, floor_fail=False):
        super().__init__([root],StorageLimits(max_bytes=ceiling,min_free_bytes=0))
        self.held = False; self.fail_full = fail_full; self.floor_fail = floor_fail
        self.checks = []
        self.after_release = lambda:None
    @contextmanager
    def lock(self):
        assert not self.held
        self.held = True
        try: yield self
        finally:
            self.held = False
            self.after_release()
    def check(self, additional_bytes, *, path):
        assert self.held
        self.checks.append(additional_bytes)
        if self.floor_fail: raise StorageLimitError('authored 6GiB free-space-floor failure')
        if self.fail_full and additional_bytes > 400*p.MiB:
            raise StorageLimitError('full condition block cannot fit')
        return super().check(additional_bytes,path=path)


@pytest.fixture
def harness(tmp_path):
    public = tmp_path/'public-scenario-source.json'; public.write_text('{"public":true}\n')
    row = {'path':str(public),'sha256':p.worker.file_sha256(public),'size_bytes':public.stat().st_size}
    roster = {'schema':'change-audit-input-roster-v1','repo_root':str(tmp_path),
        'asset_root':str(tmp_path/'assets'),'prepared_graph_directory':str(tmp_path/'prepared'),
        'source_commit':'a'*40,'files':[row],
        'runtime_metadata':{'model_sha256':'b'*64,'dependency_lock_sha256':'c'*64}}
    projection = {'schema':'change-audit-pilot-namespace-projection-v1',
        'roots':[{'root_id':f'root{i}','scenario':'reproduction','texture':'checker','seed':91001+i} for i in range(4)],
        'reserved_seed_ids':[42,43],'source':row,'scope':'approved-public-cohort-ids-only','protected_catalogs_read':False}
    roster_path = tmp_path/'roster.json'; projection_path = tmp_path/'projection.json'
    roster_sha = save(roster_path,roster); projection_sha = save(projection_path,projection)
    state = SimpleNamespace(cpu=0.,wall=0.,calls=[],budgets=[],mutate_stage=None,mutate_accounting=None,
                            after_job=None,fail_job=None,runner_raise=None,prepare_size=3,
                            release_cpu=0.,release_wall=0.,ceiling=p.MAX_BYTES,fail_full=False,floor_fail=False,natural=False)
    def factory(root):
        budget = Budget(root,ceiling=state.ceiling,fail_full=state.fail_full,floor_fail=state.floor_fail)
        def after_release():
            state.cpu += state.release_cpu; state.wall += state.release_wall
        budget.after_release=after_release
        state.budgets.append(budget)
        return budget
    def runner(command, **kwargs):
        assert state.budgets[-1].held
        assert command[:2] == [str(Path(p.sys.executable).absolute()),'-B']
        assert Path(command[2]).is_absolute()
        assert kwargs['max_log_bytes'] == 256*1024
        assert kwargs['wall_seconds'] <= 120 and kwargs['cpu_seconds'] <= 120
        assert kwargs['env']['PYTHONDONTWRITEBYTECODE']=='1'
        assert kwargs['env']['MPLBACKEND']=='Agg'
        assert Path(kwargs['env']['MPLCONFIGDIR']).parent==Path(kwargs['stdout_path']).parent
        unused=Path(kwargs['env']['PYTHONPYCACHEPREFIX'])
        assert unused.parent==Path(kwargs['stdout_path']).parent and not unused.exists()
        def arg(key): return command[command.index(key)+1]
        mode = arg('--mode'); artifact = Path(arg('--output')); pilotroot = Path(arg('--pilot-root'))
        index = len(state.calls)
        state.calls.append(mode)
        if mode == 'execute-condition':
            assert state.calls[:4] == ['prepare-anchor']*4
            frozen = json.loads((pilotroot/'condition-manifest.json').read_text())
            assert len(frozen['anchors']) == 4 and len(frozen['conditions']) == 16
            assert len(list((pilotroot/'anchors').glob('*.json'))) == 4
            assert p.worker.file_sha256(arg('--anchor')) == arg('--expected-anchor-sha256')
        assert not artifact.exists()
        configpath = Path(arg('--config'))
        assert p.worker.file_sha256(configpath) == arg('--expected-config-sha256')
        config = json.loads(configpath.read_text()); gain = float(arg('--gain')) if '--gain' in command else 1.
        artifact.mkdir()
        Path(kwargs['stdout_path']).write_bytes(b'authored bounded stdout\n')
        Path(kwargs['stderr_path']).write_bytes(b'')
        report = {'schema':'change-audit-pilot-worker-v1','mode':mode,'root_id':config['root_id'],'gain':gain,
            'actual_scope':p.SCOPE,'status':'completed','ticks':0,'forward_attempts':0,
            'before_first_tick_equal':False,'completed_requested_ticks':False,'check_parity':False,
            'sampling_eligibility_verified':False,'certified_improvement':False,'runtime_qualification':False,'errors':[]}
        def descriptor(path):
            return {'path':str(path),'file_sha256':p.worker.file_sha256(path),'state_sha256':'d'*64}
        if mode == 'prepare-anchor':
            anchor = artifact/'anchor.snp'
            with anchor.open('wb') as stream: stream.truncate(state.prepare_size)
            report.update(anchor=descriptor(anchor),stop_reason='paused_anchor_prepared')
        else:
            anchor = json.loads(Path(arg('--anchor')).read_text())
            report.update(anchor=anchor,before_first_tick_equal=True,before_first_tick_expected_sha256='e'*64,
                before_first_tick_observed_sha256='e'*64,ticks=64,forward_attempts=64,
                completed_requested_ticks=True,stop_reason='tick_limit')
            if state.natural:
                report.update(ticks=7,forward_attempts=7,completed_requested_ticks=False,
                    stop_reason='natural_terminal',terminal_outcome={'reason':'authored termination'})
            if gain == 1: report['snapshot'] = anchor
            else:
                derived = artifact/'derived.snp'; derived.write_bytes(b'authored, no SNP decoder')
                report['snapshot'] = descriptor(derived)
            save(artifact/'derivation-receipt.json',{'authored':True})
        if state.mutate_stage: state.mutate_stage(report,index)
        save(artifact/'stage-report.json',report)
        state.cpu += 7; state.wall += 10
        if state.after_job: state.after_job(index,artifact)
        if state.runner_raise == index: raise RuntimeError('authored runner transport failure')
        accounting = {'status':'completed','returncode':0,'accounting_complete':True,'tree_drained':True,
            'subtree_cpu_seconds':6.,'parent_cpu_seconds':1.,'worker_cpu_seconds':5.}
        if state.fail_job == index: accounting.update(status='failed',returncode=1)
        if state.mutate_accounting: state.mutate_accounting(accounting,index)
        return accounting
    options = dict(mode='execute',roster_path=str(roster_path),roster_sha=roster_sha,
        projection_path=str(projection_path),projection_sha=projection_sha,source_commit='a'*40,
        output=tmp_path/'output',project_cpu_used=0.,audit_cpu_used=0.,_runner=runner,
        _source_state_getter=lambda repo:{'head':'a'*40,'tracked_clean':True},
        _clock=lambda:state.wall,_cpu=lambda:state.cpu,_budget_factory=factory)
    def run(**changes): return p._run(**{**options,**changes})
    return SimpleNamespace(state=state,run=run,options=options,roster=roster,projection=projection,
        roster_path=roster_path,projection_path=projection_path,public=public,
        repin_roster=lambda:save(roster_path,roster),repin_projection=lambda:save(projection_path,projection))


def test_all_preparations_then_frozen_sixteen_conditions_and_single_lease(harness):
    h = harness; result = h.run()
    assert result['status'] == 'completed'
    assert h.state.calls == ['prepare-anchor']*4+['execute-condition']*16
    assert len(result['jobs']) == 20 and all(j['status']=='accepted' for j in result['jobs'])
    assert result['phase_cpu_seconds'] == 140  # Whole-phase meter, no worker/subtree double addition.
    assert not h.state.budgets[0].held
    assert result['sampling_eligibility_verified'] is False and result['certified_improvement'] is False
    assert all(j['attempt']==1 for j in result['jobs'])
    frozen = json.loads((h.options['output']/'condition-manifest.json').read_text())
    assert frozen['gains']==[1,.5,.75,1.25] and len(frozen['anchor_descriptor_sha256'])==4
    assert 400*p.MiB < frozen['condition_block_reserved_bytes'] < 512*p.MiB


def test_plan_only_is_readonly_and_never_calls_runner(harness):
    result = harness.run(mode='plan-only',project_cpu_used=None,audit_cpu_used=None)
    assert result['status']=='plan-only' and result['worker_invocations']==0
    assert not harness.options['output'].exists() and not harness.state.budgets
    assert not harness.state.calls


def test_failed_third_job_stops_without_retry_or_manifest(harness):
    harness.state.fail_job = 2
    result = harness.run()
    assert result['status']=='stopped' and len(harness.state.calls)==3
    assert result['phase_cpu_seconds']==21
    assert not (harness.options['output']/'condition-manifest.json').exists()
    assert len(list((harness.options['output']/'jobs').iterdir()))==3


@pytest.mark.parametrize('mutation',[
    lambda a:a.update(accounting_complete=False,subtree_cpu_seconds=None),
    lambda a:a.update(tree_drained=False),lambda a:a.update(subtree_cpu_seconds=None),
    lambda a:a.update(subtree_cpu_seconds=float('nan')),lambda a:a.update(parent_cpu_seconds=None),
])
def test_unknown_accounting_stops_and_never_invents_zero(harness,mutation):
    def change(accounting,index):
        if index==1: mutation(accounting)
    harness.state.mutate_accounting=change
    result=harness.run()
    assert result['status']=='stopped' and result['accounting_complete'] is False
    assert result['phase_cpu_seconds'] is None and len(harness.state.calls)==2
    assert result['phase_cpu_seconds_observed']==14


def test_runner_exception_persists_incomplete_running_record(harness):
    harness.state.runner_raise=0
    result=harness.run()
    assert result['status']=='stopped' and result['phase_cpu_seconds'] is None
    assert len(harness.state.calls)==1 and result['jobs'][0]['status']=='accounting-unknown'
    assert list(harness.options['output'].glob('ledger-*.json'))


@pytest.mark.parametrize('updates',[
    {'actual_scope':'software-double'}, {'root_id':'replacement'}, {'gain':.6}, {'status':'failed'},
    {'ticks':1,'forward_attempts':1}, {'errors':[{'stage':'close','message':'failure'}]},
    {'certified_improvement':True}, {'sampling_eligibility_verified':True},
])
def test_bad_preparation_report_stops_all_future_admission(harness,updates):
    harness.state.mutate_stage=lambda stage,index:stage.update(updates) if index==0 else None
    result=harness.run()
    assert result['status']=='stopped' and len(harness.state.calls)==1


@pytest.mark.parametrize('updates',[
    {'before_first_tick_equal':False},{'before_first_tick_observed_sha256':'f'*64},
    {'ticks':63,'forward_attempts':64}, {'ticks':63,'forward_attempts':63},
    {'completed_requested_ticks':False}, {'anchor':{}}, {'runtime_qualification':True},
])
def test_bad_condition_report_stops_without_replacement(harness,updates):
    harness.state.mutate_stage=lambda stage,index:stage.update(updates) if index==4 else None
    result=harness.run()
    assert result['status']=='stopped' and len(harness.state.calls)==5
    assert (harness.options['output']/'condition-manifest.json').is_file()


def test_natural_terminal_prefix_is_retained_and_accepted(harness):
    harness.state.natural=True
    assert harness.run()['status']=='completed'
    reports=[json.loads(path.read_text()) for path in (harness.options['output']/'jobs').glob('*/artifacts/stage-report.json')]
    assert sum(r['ticks']==7 for r in reports)==16


@pytest.mark.parametrize('gate',['audit','project','wall'])
def test_remaining_admission_stops_next_job_instead_of_borrowing(harness,gate):
    kwargs={}
    if gate=='audit': kwargs.update(audit_cpu_used=3460,project_cpu_used=3460)
    if gate=='project': kwargs.update(project_cpu_used=86260)
    if gate=='wall':
        harness.state.after_job=lambda index,artifact:setattr(harness.state,'wall',1680.)
    result=harness.run(**kwargs)
    assert result['status']=='stopped' and len(harness.state.calls)==1


def test_unknown_prior_usage_refuses_before_output_or_workers(harness):
    with pytest.raises(ValueError,match='known finite'): harness.run(project_cpu_used=None)
    assert not harness.options['output'].exists() and not harness.state.calls


@pytest.mark.parametrize('floor',[False,True])
def test_storage_admission_failure_precedes_any_worker(harness,floor):
    harness.state.ceiling=20*p.MiB
    harness.state.floor_fail=floor
    # Final report still retains the refusal when the authored free-space gate
    # rejects only phase admission, not the terminal control publication.
    if floor:
        with pytest.raises(StorageLimitError): harness.run()
    else:
        result=harness.run(); assert result['status']=='stopped'
    assert not harness.state.calls


def test_whole_condition_block_refused_after_four_preparations(harness):
    harness.state.fail_full=True
    result=harness.run()
    assert result['status']=='stopped' and harness.state.calls==['prepare-anchor']*4
    assert not (harness.options['output']/'condition-manifest.json').exists()


def test_large_anchors_cannot_relax_full_fixed_allocation(harness):
    harness.state.prepare_size=16*p.MiB
    result=harness.run()
    assert result['status']=='stopped' and harness.state.calls==['prepare-anchor']*4
    assert not (harness.options['output']/'condition-manifest.json').exists()


def test_existing_output_never_reused(harness):
    harness.options['output'].mkdir()
    with pytest.raises(p.PilotFailure,match='Existing'): harness.run()
    assert not harness.state.calls


@pytest.mark.parametrize('bad',['missing-projection','dirty-source','wrong-head','source-mutation','duplicate-roots','reserved','protected'])
def test_pinned_admission_failure_before_any_worker(harness,bad):
    changes={}
    if bad=='missing-projection': harness.projection_path.unlink()
    elif bad=='dirty-source': changes['_source_state_getter']=lambda repo:{'head':'a'*40,'tracked_clean':False}
    elif bad=='wrong-head': changes['_source_state_getter']=lambda repo:{'head':'b'*40,'tracked_clean':True}
    elif bad=='source-mutation': harness.public.write_text('mutated')
    elif bad=='duplicate-roots':
        harness.projection['roots'][1]['root_id']='root0'; changes['projection_sha']=harness.repin_projection()
    elif bad=='reserved':
        harness.projection['reserved_seed_ids']=[91001]; changes['projection_sha']=harness.repin_projection()
    else:
        harness.projection['protected_catalogs_read']=True; changes['projection_sha']=harness.repin_projection()
    with pytest.raises((ValueError,FileNotFoundError)): harness.run(**changes)
    assert not harness.state.calls
    retained=json.loads((harness.options['output']/'admission-failure.json').read_text())
    assert retained['accounting_complete'] is True and retained['worker_invocations']==0


def test_input_mutation_after_job_stops_all_remaining_jobs(harness):
    harness.state.after_job=lambda index,artifact:harness.public.write_text('mutated')
    result=harness.run()
    assert result['status']=='stopped' and len(harness.state.calls)==1


def test_original_anchor_mutation_stops_before_first_condition(harness):
    def mutate(index,artifact):
        if index==3:
            original=next((harness.options['output']/'jobs').glob('00-*/artifacts/anchor.snp'))
            original.write_bytes(b'mutated original')
    harness.state.after_job=mutate
    result=harness.run()
    assert result['status']=='stopped' and len(harness.state.calls)==4


@pytest.mark.parametrize('payload',[b'{"same":1,"same":2}',b'{"n":NaN}',b'{"n":1e999}',b' '* (2*p.MiB+1)])
def test_strict_bounded_json_rejects_duplicate_nonfinite_and_oversize(tmp_path,payload):
    path=tmp_path/'bad.json'; path.write_bytes(payload)
    with pytest.raises(ValueError): p._read(path)


def test_all_four_preparation_worst_cases_reserved_before_first_worker(harness):
    result=harness.run()
    expected=4*(p.worker.RECORDING_BYTES+p.worker.SNAPSHOT_BYTES)+8*p.LOG_BYTES+p.CONTROL_BYTES+p.WORKER_HEADROOM
    assert harness.state.budgets[0].checks[0] == expected
    assert result['limits']['four_preparations_worst_case_bytes'] == expected


def test_terminal_receipt_is_published_under_lease_and_names_external_tail(harness,monkeypatch):
    harness.state.release_cpu=3.
    original=p._terminal_accounting
    def under_lease(output,**kwargs):
        assert harness.state.budgets[0].held
        return original(output,**kwargs)
    monkeypatch.setattr(p,'_terminal_accounting',under_lease)
    result=harness.run()
    assert result['phase_cpu_seconds']==140
    terminal=json.loads((harness.options['output']/'terminal-accounting.json').read_text())
    assert terminal['phase_cpu_seconds']==140 and result['terminal_accounting']==terminal
    assert harness.state.cpu==143  # External lifetime accountant captures release overhead.
    assert 'lease release' in terminal['measurement_scope'] and 'unmetered_tail' in terminal
    assert not harness.state.budgets[0].held


def test_terminal_names_lease_release_as_external_lifetime_accounting(harness):
    harness.state.release_wall=1700.
    result=harness.run()
    assert result['terminal_accounting']['wall_seconds']==200
    assert 'lease release' in result['terminal_accounting']['unmetered_tail']
    assert harness.state.wall==1900


def test_plan_construction_failure_retains_hashing_charge(harness,monkeypatch):
    def fail(*args):
        harness.state.cpu=12.
        raise ValueError('authored post-roster plan failure')
    monkeypatch.setattr(p,'_plan',fail)
    with pytest.raises(ValueError,match='post-roster'): harness.run()
    receipt=json.loads((harness.options['output']/'terminal-accounting.json').read_text())
    assert receipt['phase_cpu_seconds']==12 and receipt['status']=='stopped'
    assert not harness.state.calls


def test_executing_source_mismatch_retains_preflight_charge(harness,monkeypatch):
    # Make the private source getter the production identity check's binding,
    # while preserving an authored clean HEAD and avoiding any git subprocess.
    monkeypatch.setattr(p,'_source_state',harness.options['_source_state_getter'])
    with pytest.raises(ValueError,match='executing supervisor source'): harness.run()
    receipt=json.loads((harness.options['output']/'admission-failure.json').read_text())
    assert receipt['accounting_complete'] is True and receipt['worker_invocations']==0
    assert (harness.options['output']/'terminal-accounting.json').is_file()
    assert not harness.state.calls


def test_worker_command_preserves_virtualenv_prefix_and_dependency_metadata(harness,tmp_path,monkeypatch):
    """Execute only stdlib Python plus authored package metadata, no real worker."""
    import subprocess
    import sys
    import venv

    virtualenv=tmp_path/'software-venv'
    venv.EnvBuilder(with_pip=False,symlinks=True).create(virtualenv)
    alias=virtualenv/'bin'/'python'
    assert alias.is_symlink() and alias.resolve()!=alias
    site=virtualenv/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages'
    metadata=site/'audit_supervisor_software_fixture-1.0.dist-info'
    metadata.mkdir(parents=True)
    (metadata/'METADATA').write_text('Metadata-Version: 2.1\nName: audit-supervisor-software-fixture\nVersion: 1.0\n')
    monkeypatch.setattr(p.sys,'executable',str(alias))
    original=harness.options['_runner']; probes=[]
    def runner(command,**kwargs):
        if not probes:
            program=('import sys,json; from importlib.metadata import version; '
                'print(json.dumps({"prefix":sys.prefix,"dependency":version("audit-supervisor-software-fixture")}))')
            probes.append(subprocess.run(command[:2]+['-c',program],cwd=tmp_path,env=kwargs['env'],
                capture_output=True,text=True,check=False))
        return original(command,**kwargs)
    result=harness.run(_runner=runner)
    assert result['status']=='completed'
    assert len(probes)==1 and probes[0].returncode==0,probes[0].stderr
    assert json.loads(probes[0].stdout)=={'prefix':str(virtualenv),'dependency':'1.0'}
