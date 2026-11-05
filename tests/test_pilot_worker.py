"""Authored tiny fixtures only: these checks never qualify the real runtime."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from palimpsest import snapshots
from palimpsest.storage import StorageBudget, StorageLimits
from palimpsest.velocity_gain_snapshot import derive_gain_snapshot

MODULE = Path(__file__).parents[1] / 'paper/studies/change_audit_v1/pilot_worker.py'
spec = importlib.util.spec_from_file_location('audit_pilot_worker', MODULE)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def authored_snapshot(config):
    value = {key: None for key in snapshots.SNAPSHOT_KEYS}
    value.update(native_data=b'ordinary authored placeholder', native_sha256='a'*64,
        policy={'hidden': np.array([[1, 2]], dtype=np.float32)},
        rng={'torch': b'authored rng'}, observation={'pixels': np.zeros((1,1), dtype=np.uint8)},
        application={'source_run_id': 'anchor-run', 'event_prefix': {'sha256':'b'*64},
            'phase': 'paused', 'episode': 0, 'total_tick': 0, 'seed': config['seed'],
            'scenario': config['scenario'], 'texture': config['texture'], 'controller': 'flynn'},
        identity={'policy': {'class': 'palimpsest.velocity_gain.VelocityGainPolicy',
            'device': 'cpu', 'dtype': 'torch.float32', 'provenance': {
                'schema': 'flynn-velocity-gain-v1',
                'base_policy_class': 'palimpsest.flynn.FlynnPolicy',
                'base_policy_provenance': {'checkpoint_sha256':'a'*64},
                'velocity_gain': {'numerator':1, 'denominator':1}}}})
    return value


class Cell:
    def __init__(self): self.hooks = []
    def register_forward_pre_hook(self, hook, *, prepend=False):
        self.hooks.append(hook)
        return SimpleNamespace(remove=lambda: self.hooks.remove(hook))
    def forward(self):
        for hook in self.hooks: hook(self, ())


class FixtureEngine:
    def __init__(self, config, *, stop_after=None, fail=None, mutate=None):
        self.snapshot = authored_snapshot(config)
        self.policy = SimpleNamespace(agent=SimpleNamespace(cell=Cell()))
        self.phase = 'paused'; self.episode = self.revision = self.total_tick = 0
        self.closed = False; self.commands = []; self.stop_after = stop_after; self.fail = fail; self.mutate = mutate
        self.metrics = {'contact_ticks':0}; self.last_outcome = None
    def restore_branch(self, value, *, replace_controller):
        assert replace_controller is False
        self.snapshot = copy.deepcopy(value)
        self.snapshot['application'].update(source_run_id='destination', event_prefix={'sha256':'c'*64})
        if self.mutate: self.mutate(self.snapshot)
    def submit(self, command): self.commands.append(command)
    def advance(self):
        self.policy.agent.cell.forward()
        if self.fail == 'forward': raise RuntimeError('fixture inference failed')
        if self.fail == 'double': self.policy.agent.cell.forward()
        self.total_tick += 1; self.revision += 1
        if self.stop_after == self.total_tick:
            self.phase = 'terminated'; self.last_outcome = {'reason':'authored_terminal'}
        if self.fail == 'engine': self.phase = 'failed'
    def close(self):
        self.closed = True
        if self.fail == 'close': raise RuntimeError('fixture close failed')


@pytest.fixture
def setup(tmp_path):
    pin = tmp_path/'ordinary-input.txt'; pin.write_text('software fixture')
    config = {'root_id':'fixture-root', 'repo_root':str(tmp_path), 'asset_root':str(tmp_path/'assets'),
        'scenario':'reproduction', 'texture':'checker', 'seed':3, 'ticks':64,
        'check_parity':False, 'device':'cpu', 'controller':'flynn',
        'prepared_graph_directory':str(tmp_path/'prepared'),
        'input_files':[{'path':str(pin), 'sha256':w.file_sha256(pin), 'size_bytes':pin.stat().st_size}]}
    root = tmp_path/'pilot'; root.mkdir()
    budget = StorageBudget([root], StorageLimits(max_bytes=512*1024**2, min_free_bytes=0))
    engines = []
    def bindings(**engine_options):
        def create(config, recording, budget):
            recording.mkdir(); budget.check(0,path=recording)
            engine = FixtureEngine(config, **engine_options); engines.append(engine); return engine
        return w._Bindings(create_engine=create, wrap=lambda policy,gain:policy,
            capture=lambda engine:copy.deepcopy(engine.snapshot),
            read=snapshots.read_snapshot, save=snapshots.save_snapshot,
            derive=derive_gain_snapshot, digest=snapshots.state_digest,
            scope='injected-software-fixture')
    def run(mode, output, anchor=None, gain=1, **options):
        return w._run(mode, config, root/output, storage_budget=budget,
            anchor_descriptor=anchor, gain=gain, bindings=bindings(**options))
    return SimpleNamespace(config=config, root=root, budget=budget, engines=engines, run=run, pin=pin)


def test_prepare_has_zero_ticks_forwards_and_one_exclusive_anchor(setup):
    result = setup.run('prepare-anchor','anchor')
    assert result['ticks'] == result['forward_attempts'] == 0
    assert setup.engines[-1].closed
    assert len(list(setup.root.rglob('*.snp'))) == 1
    assert result['actual_scope'] == 'injected-software-fixture'
    assert result['sampling_eligibility_verified'] is result['certified_improvement'] is False
    assert result['anchor']['state_sha256'] == snapshots.state_digest(snapshots.read_snapshot(result['anchor']['path']))
    with pytest.raises(FileExistsError): setup.run('prepare-anchor','anchor')


@pytest.mark.parametrize('gain',[1,.5,.75,1.25])
def test_condition_owns_one_forward_per_tick_strict_restore_and_bounded_snapshots(setup,gain):
    anchor = setup.run('prepare-anchor','anchor')['anchor']
    result = setup.run('execute-condition','condition',anchor,gain)
    assert result['ticks'] == result['forward_attempts'] == 64
    assert result['before_first_tick_equal'] is True
    assert result['stop_reason'] == 'tick_limit'
    assert result['completed_requested_ticks'] is True
    assert result['snapshot']['path'] == anchor['path'] if gain == 1 else result['snapshot']['path'] != anchor['path']
    assert len(list(setup.root.rglob('*.snp'))) == (1 if gain == 1 else 2)
    engine = setup.engines[-1]
    assert engine.closed and len(engine.commands) == 64
    assert all(c['kind']=='step' and c['payload']=={} for c in engine.commands)
    assert result['sampling_eligibility_verified'] is result['certified_improvement'] is False


def test_natural_terminal_is_retained_prefix_not_padded(setup):
    anchor = setup.run('prepare-anchor','anchor')['anchor']
    result = setup.run('execute-condition','condition',anchor,.5,stop_after=2)
    assert result['ticks'] == result['forward_attempts'] == 2
    assert result['stop_reason'] == 'natural_terminal'
    assert result['completed_requested_ticks'] is False
    assert setup.engines[-1].closed


@pytest.mark.parametrize('mutate',[
    lambda s:s['rng'].update(torch=b'changed'),
    lambda s:s['policy']['hidden'].__setitem__((0,0),8),
    lambda s:s['identity']['policy'].update(dtype='other'),
    lambda s:s['application'].update(seed=99),
    lambda s:s['observation']['pixels'].__setitem__((0,0),1),
])
def test_equality_retains_every_scientific_field_and_stops_before_first_tick(setup,mutate):
    anchor = setup.run('prepare-anchor','anchor')['anchor']
    with pytest.raises(w.WorkerFailure): setup.run('execute-condition','condition',anchor,.5,mutate=mutate)
    engine = setup.engines[-1]
    assert engine.closed and not engine.commands
    assert json.loads((setup.root/'condition/stage-report.json').read_text())['status']=='failed'


def test_comparison_exempts_only_two_recorder_fields(setup):
    a = authored_snapshot(setup.config); b = copy.deepcopy(a)
    b['application'].update(source_run_id='different',event_prefix={'new':'recording'})
    assert w.scientific_state_digest(a) == w.scientific_state_digest(b)
    b['application']['unexpected']=None
    assert w.scientific_state_digest(a) != w.scientific_state_digest(b)


@pytest.mark.parametrize('fail',['forward','double','engine','close'])
def test_any_inference_engine_or_close_failure_is_failed_and_closed(setup,fail):
    anchor = setup.run('prepare-anchor','anchor')['anchor']
    with pytest.raises(w.WorkerFailure): setup.run('execute-condition','condition',anchor,.5,fail=fail)
    assert setup.engines[-1].closed
    report=json.loads((setup.root/'condition/stage-report.json').read_text())
    assert report['status']=='failed'
    assert report['certified_improvement'] is False


def test_externally_expected_zip_and_typed_hashes_both_required_before_engine_load(setup):
    anchor = setup.run('prepare-anchor','anchor')['anchor']
    for key in ('file_sha256','state_sha256'):
        bad={**anchor,key:'0'*64}
        with pytest.raises(w.WorkerFailure): setup.run('execute-condition',key,bad,.5)
    assert len(setup.engines)==1


def test_input_changes_during_execution_refuse_after_close(setup):
    anchor = setup.run('prepare-anchor','anchor')['anchor']
    def changed(snapshot): setup.pin.write_text('mutated input')
    with pytest.raises(w.WorkerFailure): setup.run('execute-condition','condition',anchor,.5,mutate=changed)
    assert setup.engines[-1].closed


@pytest.mark.parametrize('key,value',[('check_parity',True),('device','cuda'),('scenario','memory-passages'),
    ('scenario','puck'),('ticks',65),('ticks',True),('seed',True),('controller','manual'),('texture','realistic')])
def test_bad_configuration_refuses_before_output_or_model_load(setup,key,value):
    setup.config[key]=value
    with pytest.raises(ValueError): setup.run('prepare-anchor','invalid')
    assert not setup.engines and not (setup.root/'invalid').exists()


def test_snapshot_quota_checks_serialized_bytes_before_file_write(setup):
    proxy=w._SnapshotBudget(setup.budget, maximum=10)
    destination=setup.root/'too-large.snp'
    with pytest.raises(Exception): snapshots.save_snapshot(authored_snapshot(setup.config),destination,storage_budget=proxy)
    assert not destination.exists()


def mock_production_module_locations(config,monkeypatch):
    """Explicit authored file-location doubles; no production files are opened."""
    import importlib
    for name in ('assets','engine','flynn','snapshots','velocity_gain','velocity_gain_snapshot'):
        module=importlib.import_module('palimpsest.'+name)
        monkeypatch.setattr(module,'__file__',str(Path(config['repo_root'])/'src/palimpsest'/(name+'.py')))


def test_production_factory_binds_readonly_resolver_and_restores_it_on_failure(setup,monkeypatch):
    mock_production_module_locations(setup.config,monkeypatch)
    """No model, cache, native environment or asset file is read in this test."""
    from palimpsest import assets
    from palimpsest.engine import Engine
    original=assets.prepare_graph
    captured=[]
    def opening(*args,**kwargs):
        captured.append((args,kwargs))
        assert assets.prepare_graph is not original
        # Missing frozen directory must fail without invoking the original resolver.
        with pytest.raises(ValueError,match='pre-existing'):
            assets.prepare_graph(setup.config['repo_root'],setup.config['asset_root'])
        raise RuntimeError('authored setup failure')
    monkeypatch.setattr(assets,'load_manifest',lambda root:{'files':[{'id':'graph_archive','path':'archive','sha256':'a'*64}],
        'graph':{}})
    monkeypatch.setattr(assets,'_verified',lambda path,row:True)
    monkeypatch.setattr(Engine,'open',opening)
    with pytest.raises(RuntimeError,match='authored setup'):
        w._production_engine(setup.config,setup.root/'recording',setup.budget)
    assert assets.prepare_graph is original
    assert captured[0][1]['max_bytes']==15*1024**2
    assert captured[0][1]['controller']=='flynn'
    assert captured[0][1]['device']=='cpu'
    assert 'restore_snapshot' not in captured[0][1]


def test_preflight_input_mismatch_creates_failure_record_without_loading_engine(setup):
    setup.pin.write_text('mutated')
    with pytest.raises(w.WorkerFailure): setup.run('prepare-anchor','anchor')
    assert not setup.engines
    report=json.loads((setup.root/'anchor/stage-report.json').read_text())
    assert report['status']=='failed' and report['forward_attempts']==0


def test_prepare_must_not_forward_while_capturing(setup):
    engine=FixtureEngine(setup.config)
    def capture(value):
        value.policy.agent.cell.forward()
        return copy.deepcopy(value.snapshot)
    bindings=w._Bindings(create_engine=lambda *args:engine,wrap=lambda policy,gain:policy,
        capture=capture,read=snapshots.read_snapshot,save=snapshots.save_snapshot,
        derive=derive_gain_snapshot,digest=snapshots.state_digest,scope='injected-software-fixture')
    with pytest.raises(w.WorkerFailure):
        w._run('prepare-anchor',setup.config,setup.root/'forwarding-capture',
            storage_budget=setup.budget,bindings=bindings)
    assert engine.closed and not engine.commands
    report=json.loads((setup.root/'forwarding-capture/stage-report.json').read_text())
    assert report['forward_attempts']==1 and report['ticks']==0
    assert not list((setup.root/'forwarding-capture').glob('*.snp'))


def test_input_hash_recheck_rejects_changed_anchor_after_execution(setup):
    anchor=setup.run('prepare-anchor','anchor')['anchor']
    def mutation(snapshot):
        with Path(anchor['path']).open('ab') as stream: stream.write(b'authored mutation')
    with pytest.raises(w.WorkerFailure): setup.run('execute-condition','condition',anchor,.5,mutate=mutation)
    assert setup.engines[-1].closed
    report=json.loads((setup.root/'condition/stage-report.json').read_text())
    assert report['errors'][-1]['stage']=='input_recheck'


def test_nonfinite_control_json_is_rejected_before_publication(setup):
    destination=setup.root/'nonfinite.json'
    with pytest.raises(ValueError): w._write_json(destination,{'v':float('nan')},setup.budget)
    assert not destination.exists()


def test_frozen_config_digest_binds_exact_bytes_decoded(tmp_path):
    path=tmp_path/'config.json'; path.write_text('{"v":1}')
    expected=w.file_sha256(path)
    assert w._finite_json(path,expected_sha256=expected)=={'v':1}
    path.write_text('{"v":2}')
    with pytest.raises(ValueError,match='checksum'):
        w._finite_json(path,expected_sha256=expected)


@pytest.mark.parametrize('payload',['{"v":NaN}','{"v":Infinity}','{"v":1,"v":2}'])
def test_frozen_control_json_refuses_nonfinite_or_duplicate_keys(tmp_path,payload):
    path=tmp_path/'input.json'; path.write_text(payload)
    with pytest.raises(ValueError): w._finite_json(path)


def test_production_cache_success_uses_validation_only_and_restores_binding(setup,monkeypatch):
    mock_production_module_locations(setup.config,monkeypatch)
    from palimpsest import assets
    from palimpsest.engine import Engine
    directory=Path(setup.config['asset_root'])/('graph-'+'a'*64)
    directory.mkdir(parents=True)
    setup.config['prepared_graph_directory']=str(directory)
    (directory/'palimpsest-prepared.json').write_text(json.dumps({'edge_path':'edge.csv','archive_sha256':'a'*64}))
    manifest={'files':[{'id':'graph_archive','path':'archive','sha256':'a'*64}],
        'graph':{'edge_identity':{'sha256':'b'*64},'mapping_files':[]}}
    monkeypatch.setattr(assets,'load_manifest',lambda root:manifest)
    monkeypatch.setattr(assets,'_verified',lambda path,row:True)
    calls=[]
    monkeypatch.setattr(assets,'_check_mappings',lambda *args,**kwargs:calls.append(kwargs))
    def forbidden(*args): raise AssertionError('Extraction resolver must never be called')
    monkeypatch.setattr(assets,'prepare_graph',forbidden)
    returned=object()
    def opening(*args,**kwargs):
        assert assets.prepare_graph(setup.config['repo_root'],setup.config['asset_root'])==directory/'edge.csv'
        return returned
    monkeypatch.setattr(Engine,'open',opening)
    assert w._production_engine(setup.config,setup.root/'recording',setup.budget) is returned
    assert calls==[{'copy_missing':False}]
    assert assets.prepare_graph is forbidden


def cli_inputs(setup):
    config=setup.root/'config.json'; config.write_text(json.dumps(setup.config))
    descriptor=setup.root/'descriptor.json'; descriptor.write_text('{"path":"/authored.snp","file_sha256":"'+'a'*64+'","state_sha256":"'+'b'*64+'"}')
    argv=['--mode','execute-condition','--config',str(config),'--expected-config-sha256',w.file_sha256(config),
        '--output',str(setup.root/'condition'),'--pilot-root',str(setup.root),'--anchor',str(descriptor),'--gain','.5']
    return argv,descriptor


def test_cli_requires_external_anchor_descriptor_hash_before_production_entry(setup,monkeypatch):
    argv,descriptor=cli_inputs(setup)
    called=[]
    monkeypatch.setattr(w,'execute_condition',lambda *args,**kwargs:called.append(True) or {})
    with pytest.raises(ValueError,match='anchor.*SHA256'):
        w.main(argv)
    assert not called


def test_cli_anchor_hash_binds_exact_decoded_bytes_and_rechecks_after_execution(setup,monkeypatch):
    argv,descriptor=cli_inputs(setup)
    expected=w.file_sha256(descriptor)
    argv += ['--expected-anchor-sha256',expected]
    called=[]
    def executing(config,output,anchor,gain,*,storage_budget):
        called.append(anchor)
        descriptor.write_text('{"changed":"after decode"}')
        return {'actual_scope':'injected-software-fixture'}
    monkeypatch.setattr(w,'execute_condition',executing)
    with pytest.raises(w.WorkerFailure,match='descriptor changed'):
        w.main(argv)
    assert called[0]['file_sha256']=='a'*64


def test_cli_changed_descriptor_bytes_refuse_before_production_entry(setup,monkeypatch):
    argv,descriptor=cli_inputs(setup)
    expected=w.file_sha256(descriptor)
    argv += ['--expected-anchor-sha256',expected]
    descriptor.write_text('{"changed":"before decode"}')
    called=[]
    monkeypatch.setattr(w,'execute_condition',lambda *args,**kwargs:called.append(True) or {})
    with pytest.raises(ValueError,match='checksum'):
        w.main(argv)
    assert not called


def test_production_wrong_loaded_source_clone_refuses_before_engine_open(setup,monkeypatch):
    from palimpsest.engine import Engine
    called=[]
    monkeypatch.setattr(Engine,'open',lambda *args,**kwargs:called.append(True))
    with pytest.raises(ValueError,match='Loaded project module'):
        w._production_engine(setup.config,setup.root/'recording',setup.budget)
    assert not called


def test_cli_descriptor_mutation_during_decode_keeps_hashed_value_and_fails_final_recheck(setup,monkeypatch):
    argv,descriptor=cli_inputs(setup)
    frozen_bytes=descriptor.read_bytes(); expected=w.file_sha256(descriptor)
    argv += ['--expected-anchor-sha256',expected]
    original_loads=w.json.loads
    def decoding(payload,**kwargs):
        if payload==frozen_bytes:
            descriptor.write_text('{"changed":"during decode"}')
        return original_loads(payload,**kwargs)
    monkeypatch.setattr(w.json,'loads',decoding)
    seen=[]
    monkeypatch.setattr(w,'execute_condition',lambda config,output,anchor,gain,**kwargs:seen.append(anchor) or {})
    with pytest.raises(w.WorkerFailure,match='descriptor changed'):
        w.main(argv)
    assert seen==[original_loads(frozen_bytes)]


@pytest.mark.parametrize('name',['assets','engine','flynn','snapshots','velocity_gain','velocity_gain_snapshot'])
def test_each_guarded_production_module_must_match_frozen_clone(setup,monkeypatch,name):
    import importlib
    mock_production_module_locations(setup.config,monkeypatch)
    module=importlib.import_module('palimpsest.'+name)
    monkeypatch.setattr(module,'__file__','/authored-other-clone/src/palimpsest/'+name+'.py')
    with pytest.raises(ValueError,match='Loaded project module.*'+name):
        w._production_bindings(setup.config)
