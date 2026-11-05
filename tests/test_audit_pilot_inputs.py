"""Input authoring fixtures: no model/native execution or real asset reads."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

MODULE=Path(__file__).parents[1]/'paper/studies/change_audit_v1/prepare_inputs.py'
spec=importlib.util.spec_from_file_location('audit_pilot_inputs',MODULE)
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def descriptor(path):
    payload=path.read_bytes()
    return {'path':str(path),'sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload)}


@pytest.fixture
def prepared(tmp_path):
    repo=tmp_path/'repo'; repo.mkdir()
    source=repo/'worker.py'; source.write_text('# authored ordinary source\n')
    plan=repo/'docs/plans/project-completion-2026-11-05.md'; plan.parent.mkdir(parents=True)
    plan.write_text('Authored public plan fixture; no research result.')
    runtime=tmp_path/'runtime.txt'; runtime.write_text('authored runtime descriptor')
    model=tmp_path/'model.txt'; model.write_text('ordinary tiny stand-in, never a pretrained asset')
    python=tmp_path/'python-fixture'; python.write_text('authored interpreter descriptor')
    assets=tmp_path/'assets'; assets.mkdir(); graph=assets/'prepared'; graph.mkdir()
    config={'repo_root':str(repo),'asset_root':str(assets),'prepared_graph_directory':str(graph),
        'source_commit':'a'*40,'source_files':[str(source)],'runtime_files':[str(runtime)],
        'model_files':[str(model)],'python_executable':str(python)}
    runtime_identity=lambda:{'executable':str(python),'version':'3.11.0 authored',
        'scope':'injected-software-fixture'}
    source_state=lambda repo,files:{'head':'a'*40,'tracked_clean':True,'selected_sources_tracked':True}
    def run(mode='execute-preparation',name='output',**kwargs):
        return p.prepare(mode=mode,output=tmp_path/name,approved_plan=plan,
            expected_plan_sha256=descriptor(plan)['sha256'],config=config if mode=='execute-preparation' else None,
            _runtime_identity=runtime_identity,_source_state=source_state,**kwargs)
    return SimpleNamespace(repo=repo,plan=plan,source=source,runtime=runtime,model=model,python=python,
        config=config,run=run,tmp_path=tmp_path,source_state=source_state,runtime_identity=runtime_identity)


def test_namespace_pure_exact_public_ids_and_no_disjointness_claim(prepared):
    source,projection=p.namespace_documents(descriptor(prepared.plan))
    expected=set(range(6110,6114))|set(range(6120,6124))|set(range(6200,6208))|set(range(3130,3134))|set(range(3120,3128))|{10,11,12}
    assert set(source['reserved_seed_ids'])==expected
    assert source['approved_plan']==descriptor(prepared.plan)
    assert [root['seed'] for root in projection['roots']]==[91001,91002,91003,91004]
    assert all((root['scenario'],root['texture'])==('reproduction','checker') for root in projection['roots'])
    assert projection['scope']=='approved-public-cohort-ids-only'
    assert projection['protected_catalogs_read'] is False
    assert 'no geometry, pretraining, or sampling-disjointness claim' in source['limitations']


def test_plan_only_reads_no_runtime_or_model_and_writes_accepted_projection(prepared,monkeypatch):
    original=p.describe_file
    def only_public(path):
        assert Path(path) not in (prepared.runtime,prepared.model,prepared.python,prepared.source)
        return original(path)
    monkeypatch.setattr(p,'describe_file',only_public)
    result=prepared.run('plan-only')
    projection=json.loads(Path(result['namespace_projection']['path']).read_text())
    assert set(projection)=={'schema','roots','reserved_seed_ids','source','scope','protected_catalogs_read'}
    assert projection['source']==result['namespace_source']
    assert not (prepared.tmp_path/'output/input-roster.json').exists()
    assert result['research_execution_started'] is False


def test_execute_emits_exact_roster_schema_and_explicit_runtime_metadata(prepared):
    result=prepared.run()
    roster=json.loads(Path(result['input_roster']['path']).read_text())
    assert set(roster)=={'schema','repo_root','asset_root','prepared_graph_directory','source_commit','files','runtime_metadata'}
    assert roster['schema']=='change-audit-input-roster-v1'
    assert result['namespace_source'] in roster['files']
    assert descriptor(prepared.plan) in roster['files']
    assert descriptor(prepared.source) in roster['files']
    assert descriptor(prepared.runtime) in roster['files']
    assert descriptor(prepared.model) in roster['files']
    assert descriptor(prepared.python) in roster['files']
    assert roster['runtime_metadata']['dependency_completeness_claimed'] is False
    assert roster['runtime_metadata']['python']['scope']=='injected-software-fixture'
    assert result['status']=='completed'
    receipt=json.loads((prepared.tmp_path/'output/preparation-receipt.json').read_text())
    assert receipt['observed_self_and_waited_children_cpu_seconds']>=0
    assert receipt['requires_parent_final_process_accounting'] is True


@pytest.mark.parametrize('state',[
    {'head':'b'*40,'tracked_clean':True,'selected_sources_tracked':True},
    {'head':'a'*40,'tracked_clean':False,'selected_sources_tracked':True},
    {'head':'a'*40,'tracked_clean':True,'selected_sources_tracked':False},
])
def test_dirty_wrong_head_or_untracked_selected_source_fails_with_cpu_receipt(prepared,state):
    with pytest.raises(p.PreparationFailure):
        p.prepare(mode='execute-preparation',output=prepared.tmp_path/'failure',approved_plan=prepared.plan,
            expected_plan_sha256=descriptor(prepared.plan)['sha256'],config=prepared.config,
            _source_state=lambda *args:state,_runtime_identity=prepared.runtime_identity)
    receipt=json.loads((prepared.tmp_path/'failure/preparation-receipt.json').read_text())
    assert receipt['status']=='failed' and receipt['observed_self_and_waited_children_cpu_seconds']>=0
    assert receipt['errors']


def test_explicit_duplicate_resolved_inputs_rejected_and_symlink_aliases_recorded(prepared):
    alias=prepared.tmp_path/'runtime-alias'; alias.symlink_to(prepared.runtime)
    prepared.config['runtime_files']=[str(alias)]
    result=prepared.run()
    roster=json.loads(Path(result['input_roster']['path']).read_text())
    assert descriptor(prepared.runtime) in roster['files']
    assert {'requested':str(alias),'resolved':str(prepared.runtime)} in roster['runtime_metadata']['explicit_path_resolution']
    prepared.config['model_files'].append(str(prepared.runtime))
    with pytest.raises(p.PreparationFailure): prepared.run(name='duplicate')


def test_no_recursive_discovery_or_unselected_file_read(prepared,monkeypatch):
    forbidden=prepared.repo/'data/protected_catalog.json'; forbidden.parent.mkdir()
    forbidden.write_text('DO NOT READ')
    original=p.describe_file
    seen=[]
    def explicit_only(path):
        seen.append(Path(path)); assert Path(path)!=forbidden
        return original(path)
    monkeypatch.setattr(p,'describe_file',explicit_only)
    prepared.run()
    assert forbidden not in seen


def test_output_is_exclusive_and_input_mutation_after_hash_fails_retaining_receipt(prepared):
    prepared.run()
    with pytest.raises(FileExistsError): prepared.run()
    calls=[]
    def state(repo,files):
        calls.append(True)
        if len(calls)>1: prepared.model.write_text('changed after initial hash')
        return prepared.source_state(repo,files)
    with pytest.raises(p.PreparationFailure):
        p.prepare(mode='execute-preparation',output=prepared.tmp_path/'mutation',approved_plan=prepared.plan,
            expected_plan_sha256=descriptor(prepared.plan)['sha256'],config=prepared.config,
            _source_state=state,_runtime_identity=prepared.runtime_identity)
    assert json.loads((prepared.tmp_path/'mutation/preparation-receipt.json').read_text())['status']=='failed'


def test_supplied_wrong_public_plan_hash_fails_without_asset_hashing(prepared,monkeypatch):
    seen=[]; original=p.describe_file
    monkeypatch.setattr(p,'describe_file',lambda path:seen.append(Path(path)) or original(path))
    with pytest.raises(p.PreparationFailure):
        p.prepare(mode='plan-only',output=prepared.tmp_path/'bad-plan',approved_plan=prepared.plan,
            expected_plan_sha256='0'*64)
    assert prepared.model not in seen


def test_finite_exclusive_control_and_total_output_bounds(tmp_path):
    destination=tmp_path/'record.json'
    with pytest.raises(ValueError): p.write_json(destination,{'v':float('nan')})
    assert not destination.exists()
    p.write_json(destination,{'v':1})
    with pytest.raises(FileExistsError): p.write_json(destination,{'v':2})
    with pytest.raises(ValueError): p.write_json(tmp_path/'huge.json',{'v':'x'*(2*1024**2)})


def test_real_source_checker_uses_exact_clean_git_head_and_selected_tracking(tmp_path):
    repo=tmp_path/'repo'; repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    source=repo/'source.py'; source.write_text('# authored')
    subprocess.run(['git','-C',str(repo),'add','source.py'],check=True)
    subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','authored fixture'],check=True)
    state=p.source_state(repo,[source])
    assert state['tracked_clean'] is state['selected_sources_tracked'] is True
    assert len(state['head'])==40
    source.write_text('# changed')
    assert p.source_state(repo,[source])['tracked_clean'] is False
    other=repo/'untracked.py'; other.write_text('# untracked')
    assert p.source_state(repo,[other])['selected_sources_tracked'] is False


def test_execute_cli_config_hash_failure_has_durable_preparation_receipt(prepared):
    config=prepared.tmp_path/'explicit-config.json'; config.write_text(json.dumps(prepared.config))
    output=prepared.tmp_path/'bad-config-cli'
    with pytest.raises(p.PreparationFailure):
        p.main(['--mode','execute-preparation','--output',str(output),'--approved-plan',str(prepared.plan),
            '--expected-plan-sha256',descriptor(prepared.plan)['sha256'],
            '--config',str(config),'--expected-config-sha256','0'*64])
    receipt=json.loads((output/'preparation-receipt.json').read_text())
    assert receipt['status']=='failed'
    assert receipt['observed_self_and_waited_children_cpu_seconds']>=0


def test_frozen_config_refuses_float_overflow_json(prepared):
    config=prepared.tmp_path/'overflow.json'; config.write_text('{"unexpected":1e999}')
    with pytest.raises(ValueError,match='Nonfinite'):
        p._read_frozen(config,descriptor(config)['sha256'])


def test_generated_input_shapes_are_accepted_by_pilot_admission_on_authored_files(prepared):
    from paper.studies.change_audit_v1 import pilot
    result=prepared.run()
    roster,projection,configs=pilot._load_admission(result['input_roster']['path'],result['input_roster']['sha256'],
        result['namespace_projection']['path'],result['namespace_projection']['sha256'],'a'*40,
        lambda repo:{'head':'a'*40,'tracked_clean':True})
    assert len(configs)==4 and len(roster['files'])==6
    assert projection['protected_catalogs_read'] is False
