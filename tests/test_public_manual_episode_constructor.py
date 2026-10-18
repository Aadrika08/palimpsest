"""Engine.open constructor contracts with authored environments and fake vendors.

Only engine.py and the ordinary data-only RunWriter execute. No upstream,
vendor, native operator, renderer, asset, diagnostic subprocess or model runs.
"""
import builtins
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest


SOURCE=Path(__file__).resolve().parents[1]/'src/palimpsest'
PUBLIC='environment.mujoco_two_cam_env_random_obstacles'
RUNNER='run_connectome_rnn_checkpoint'
EXPECTED_KWARGS=dict(width=128,height=128,max_episode_steps=600,
    n_obstacles=20,arena_half_extent=7.,render_mode=None,end_on_collision=False,
    goal_bonus=0,contact_penalty=0,time_penalty=.01,prog_scale=10.,
    ctrl_penalty=.001,texture_mode='checker')


class AuthoredVector(list):
    """Only the manual action allocation/reset; no NumPy arithmetic."""
    def __setitem__(self,key,value):
        if type(key) is slice and type(value) in (int,float):
            value=[value]*len(self[key])
        super().__setitem__(key,value)


@pytest.fixture
def route(tmp_path,monkeypatch):
    trace=[];created=[];constructed=[];imported=[]
    state=SimpleNamespace(trace=trace,created=created,constructed=constructed,
        imported=imported,construct_error=None,configure_error=None,diagnostic_error=False,
        episode_error=None,renderer_error=None)
    root=tmp_path/'project';(root/'src/palimpsest').mkdir(parents=True)
    (root/'src/palimpsest/authored.py').write_text('AUTHORED = True\n')
    (root/'uv.lock').write_text('# AUTHORED inert lock\n')
    state.root=root;state.output=tmp_path/'recording'

    class AuthoredEnvironment:
        def __init__(self,**kwargs):
            trace.append(('construct',copy.deepcopy(kwargs)))
            constructed.append(copy.deepcopy(kwargs))
            if state.construct_error:raise state.construct_error
            self.constructor_seed=kwargs.get('seed')
            self.model=SimpleNamespace(opt=SimpleNamespace(timestep=.002))
            self.data=SimpleNamespace()
            self.frame_skip=10;self.arena=7.;self.closed=False
            self.renderer=SimpleNamespace(closed=False)
            def close_renderer():
                trace.append(('renderer.close',));self.renderer.closed=True
                if state.renderer_error:raise state.renderer_error
            self.renderer.close=close_renderer
            created.append(self)
            # Upstream's constructor resets once with its default seed=None.
            self.reset(seed=self.constructor_seed)
        def reset(self,seed=None):
            trace.append(('reset',seed));return {'authored':True},{}
        def close(self):
            trace.append(('env.close',));self.closed=True

    class AuthoredPolicy:
        device='cpu'
        def __init__(self):self.provenance={'policy_identity':{'authored':True}}
        def reset(self):trace.append(('policy.reset',))

    class AuthoredTeacher:
        def __init__(self,arena_half_extent,device):
            trace.append(('teacher',arena_half_extent,device));self.device=device

    def old_environment(render_mode,n_obstacles,texture_mode='checker'):
        trace.append(('reference._make_env',render_mode,n_obstacles,texture_mode))
        return AuthoredEnvironment(**dict(EXPECTED_KWARGS,n_obstacles=n_obstacles,texture_mode=texture_mode))

    def import_upstream(repo_root,name):
        assert repo_root==root.resolve()
        imported.append(name);trace.append(('import',name))
        if name==PUBLIC:return SimpleNamespace(MuJoCoTwoCamEnv=AuthoredEnvironment)
        if name==RUNNER:
            return SimpleNamespace(_make_env=old_environment,PlannerAnalyticTeacher=AuthoredTeacher)
        raise AssertionError('Unexpected authored upstream import: '+name)

    prefix='_authored_public_manual_constructor'
    package=ModuleType(prefix);package.__path__=[str(SOURCE)]
    monkeypatch.setitem(sys.modules,prefix,package)
    def module(name,**attributes):
        value=ModuleType(prefix+'.'+name);value.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules,value.__name__,value);setattr(package,name,value)
        return value
    def load(name):
        spec=importlib.util.spec_from_file_location(prefix+'.'+name,SOURCE/(name+'.py'))
        value=importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules,spec.name,value);spec.loader.exec_module(value)
        setattr(package,name,value);return value

    def validate(scenario,texture,controller):
        if scenario not in ('reproduction','sparse-navigation','texture-variation') or texture not in ('checker','realistic'):
            raise ValueError('Unknown authored scenario or texture')
        if texture=='realistic' and scenario!='texture-variation':raise ValueError('Invalid authored texture')
        return dict(id=scenario,width=128,height=128,max_steps=600,arena=7.,
            n_obstacles=5 if scenario=='sparse-navigation' else 20,
            observation_profile='AUTHORED',texture=texture,controller=controller)
    def configure(env):
        trace.append(('configure_world',))
        if state.configure_error:raise state.configure_error
    def diagnose(repo_root,asset_root):
        trace.append(('diagnose',))
        return {'checks':[dict(name='upstream',status='error' if state.diagnostic_error else 'ok')]}
    def load_manifest(repo_root):
        return dict(upstream_commit='AUTHORED public upstream',files=[dict(id='checkpoint',path='not-read.pt')])
    def policy(*args,**kwargs):trace.append(('load_policy',));return AuthoredPolicy()
    male=module('male_policy',CONTROLLERS={'male-original':'original'},
        validate_identity=lambda identity,controller:identity,
        resolve_profile=lambda *a:({'authored':True},{}),load_pinned_policy=policy)
    module('assets',load_manifest=load_manifest,prepare_graph=lambda *a:root/'not-read.csv',
        sha256_file=lambda path:'a'*64,verify_assets=lambda *a:{'ok':True})
    module('doctor',diagnose=diagnose)
    module('profiles',validate=validate,configure_world=configure,POPULATIONS=('AUTHORED',))
    module('memory_reference',REFERENCES={},validate_source=lambda *a:None)
    module('flynn',import_upstream=import_upstream,load_policy=policy)
    records=load('records');api=load('engine')

    class NeverArray:pass
    numpy=ModuleType('numpy');numpy.generic=numpy.ndarray=NeverArray
    numpy.float64='AUTHORED float64'
    numpy.zeros=lambda count,dtype:AuthoredVector([0.]*count)
    numpy.random=SimpleNamespace(seed=lambda seed:trace.append(('numpy.seed',seed)))
    torch=ModuleType('torch');torch.manual_seed=lambda seed:trace.append(('torch.seed',seed))
    torch.set_num_threads=lambda count:trace.append(('torch.threads',count))
    random=ModuleType('random');random.seed=lambda seed:trace.append(('python.seed',seed))
    fake={'numpy':numpy,'torch':torch,'random':random}
    forbidden={'numpy','torch','torchvision','mujoco','gymnasium','glfw','scipy',
        'pandas','cv2','matplotlib','seaborn','sklearn','networkx','py7zr'}
    original_import=builtins.__import__
    def guarded_import(name,globals=None,locals=None,fromlist=(),level=0):
        if level==0 and name in fake:return fake[name]
        if level==0 and name.split('.')[0] in forbidden:
            raise AssertionError('Real vendor import is forbidden in this authored test: '+name)
        return original_import(name,globals,locals,fromlist,level)
    monkeypatch.setattr(builtins,'__import__',guarded_import)
    def no_subprocess(*a,**kw):raise AssertionError('No diagnostic subprocess is admitted')
    monkeypatch.setattr(subprocess,'run',no_subprocess)
    monkeypatch.setenv('MUJOCO_GL','AUTHORED unchanged backend')
    monkeypatch.setenv('MPLBACKEND','AUTHORED unchanged plotting')

    class AuthoredEngine(api.Engine):
        # World rendering/task sensors are outside this construction seam.
        # Real Engine.__init__, _reset_world, _event and close still execute.
        def _episode_started(self):
            if state.episode_error:raise state.episode_error
            self._event('episode_started',seed=self.seed)
    state.api=api;state.engine=AuthoredEngine;state.records=records;state.male=male
    def open(**changes):
        kwargs=dict(controller='manual',device='cpu',seed=19,scenario='reproduction',
            texture='checker',run_id='1'*32)
        kwargs.update(changes)
        return AuthoredEngine.open(root,tmp_path/'absent-assets',state.output,**kwargs)
    state.open=open
    yield state
    for env in created:
        # A failed Engine.open must already have closed these; this fixture
        # itself owns no native resource or vendor handle.
        assert env.closed and env.renderer.closed


@pytest.mark.parametrize('scenario,texture,obstacles',[
    ('reproduction','checker',20),('sparse-navigation','checker',5),
    ('texture-variation','realistic',20),
])
def test_manual_uses_public_constructor_with_exact_runner_arguments(route,scenario,texture,obstacles):
    engine=route.open(scenario=scenario,texture=texture)
    try:
        assert route.imported==[PUBLIC]
        assert route.constructed==[dict(EXPECTED_KWARGS,n_obstacles=obstacles,texture_mode=texture)]
        assert engine.env.constructor_seed is None
        assert engine.phase=='paused' and engine.seed==19
        assert engine.writer.manifest['scenario']['id']==scenario
    finally:engine.close()


def test_global_seeds_constructor_default_then_declared_reset_keep_their_order(route):
    engine=route.open()
    try:
        positions=[route.trace.index(row) for row in [
            ('diagnose',),('python.seed',19),('numpy.seed',19),('torch.seed',19),
            ('torch.threads',2),('import',PUBLIC),('construct',EXPECTED_KWARGS),
            ('reset',None),('configure_world',),('reset',19),
        ]]
        assert positions==sorted(positions)
        events=[json.loads(line) for line in (route.output/'events.jsonl').read_text().splitlines()]
        assert [event['kind'] for event in events]==['diagnostics','environment','engine_opened','episode_started']
        environment=events[1]
        assert environment['upstream_commit']=='AUTHORED public upstream'
        assert environment['lock_sha256']=='a'*64
        assert environment['source_sha256']=={'src/palimpsest/authored.py':'a'*64}
    finally:engine.close()


@pytest.mark.parametrize('controller',['teacher','flynn','male-original'])
def test_nonmanual_controllers_retain_the_existing_reference_constructor(route,controller):
    engine=route.open(controller=controller)
    try:
        assert route.imported==[RUNNER]
        assert ('reference._make_env',None,20,'checker') in route.trace
        assert engine.controller==controller
        if controller=='teacher':assert ('teacher',7.,'cpu') in route.trace
        else:assert ('load_policy',) in route.trace
    finally:engine.close()


@pytest.mark.parametrize('changes',[
    {'seed':-1},{'seed':True},{'controller':'caller-factory'},
    {'scenario':'unknown'},{'texture':'unknown'},
    {'scenario':'reproduction','texture':'realistic'},
])
def test_existing_validation_refuses_before_allocating_the_writer_or_environment(route,changes):
    with pytest.raises(ValueError):route.open(**changes)
    assert not route.output.exists()
    assert route.constructed==[] and route.imported==[]


@pytest.mark.parametrize('failure',['diagnostic','constructor','configure','engine-init'])
def test_manual_construction_failure_keeps_failed_recording_and_closes_created_environment(route,failure):
    if failure=='diagnostic':route.diagnostic_error=True
    elif failure=='constructor':route.construct_error=RuntimeError('AUTHORED constructor failure')
    elif failure=='configure':route.configure_error=RuntimeError('AUTHORED world failure')
    else:route.episode_error=RuntimeError('AUTHORED engine initialization failure')
    with pytest.raises(RuntimeError):route.open()
    manifest=json.loads((route.output/'manifest.json').read_text())
    assert manifest['status']=='failed' and manifest['recorded_ticks']==0
    assert all(env.closed and env.renderer.closed for env in route.created)
    if route.created:
        assert route.trace.index(('renderer.close',))<route.trace.index(('env.close',))
    before={p.name:p.read_bytes() for p in route.output.iterdir() if p.is_file()}
    with pytest.raises(FileExistsError):route.open()
    assert before=={p.name:p.read_bytes() for p in route.output.iterdir() if p.is_file()}


def test_normal_close_uses_existing_recording_contract_and_preserves_environment_selection(route,monkeypatch):
    engine=route.open()
    engine.close()
    manifest=json.loads((route.output/'manifest.json').read_text())
    assert manifest['status']=='completed' and manifest['final_phase']=='paused'
    assert manifest['recorded_ticks']==0  # A seam test, never an episode success claim.
    assert manifest['recording_format']=='palimpsest-npz-v1'
    assert route.trace[-2:]==[('renderer.close',),('env.close',)]
    import os
    assert os.environ['MUJOCO_GL']=='AUTHORED unchanged backend'
    assert os.environ['MPLBACKEND']=='AUTHORED unchanged plotting'


def test_renderer_close_failure_retains_failed_recording_and_closes_environment(route):
    engine=route.open();route.renderer_error=RuntimeError('AUTHORED close failure')
    with pytest.raises(RuntimeError,match='AUTHORED close failure'):engine.close()
    assert route.created[0].closed and route.created[0].renderer.closed
    assert json.loads((route.output/'manifest.json').read_text())['status']=='failed'
