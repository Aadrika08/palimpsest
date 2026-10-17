"""Held public episode entry phases with authored seams; no mujoco, EGL or upstream.

Engine.open, snapshot registration, replay and export are replaced by authored
recorders so the cases specify only the entry's own contract: provenance from
the authenticated registration, the frozen schedule, rechecks, the renderer
query on already-loaded libraries, bundles and a closed claim-free receipt.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest

import palimpsest.artifacts  # noqa: F401 - bind real modules before authored version stand-ins
import palimpsest.engine  # noqa: F401
import palimpsest.replay  # noqa: F401
from palimpsest import puck_held_episode as entry
from palimpsest.held_provenance import HeldProvenance, UPSTREAM_PIN


EXPECTED=dict(numpy='authored-numpy',torch='authored-torch',mujoco='authored-mujoco',gymnasium='authored-gymnasium')
PYPROJECT=b'[project]\nname = "palimpsest"\nversion = "0.1.0.dev0"\n'
LOCK=b'# authored lock\n'
DISTRIBUTIONS=[dict(name=name,version='9.'+str(index),root_index=0,metadata_path=name+'-9.dist-info/METADATA')
               for index,name in enumerate(('torch','torchvision','numpy','scipy','pandas','scikit-learn','mujoco',
                   'gymnasium','glfw','opencv-python','matplotlib','seaborn','networkx','python-louvain','py7zr'))]


def row(path,raw):
    return dict(path=path,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def admission(tmp_path,phase='source',ticks=48):
    output=tmp_path/'output';output.mkdir()
    source_root=output if phase=='source' else tmp_path/'source-run'
    files={'pyproject.toml':PYPROJECT,'uv.lock':LOCK,'upstream/fly-gym/environment/__init__.py':b'',
           'upstream/fly-gym/environment/mujoco_two_cam_env_random_obstacles.py':b'AUTHORED = True\n'}
    reg=dict(version=4,source_root='/puck/source',environment=dict(MUJOCO_GL='egl',PATH='/nonexistent'),
        runtime=dict(root='/opt/python/bin',files=[dict(path='python3.11',size_bytes=21662864,sha256='57'*32)],
                     python_version='3.11.15'),
        source_files=sorted([row(path,raw) for path,raw in files.items()],key=lambda r:r['path']),
        episode=dict(kind='puck-held-public-episode-v1',version=1,phase=phase,expected_versions=dict(EXPECTED),
            profile=dict(scenario='reproduction',texture='checker',controller='manual',device='cpu',seed=7),
            schedule=dict(ticks=ticks,actions=[[0,.5,0.],[ticks//2,.5,.25]]),
            run_ids=dict(source='a'*32,replay='b'*32),
            paths=dict(output_root=str(output),source_root=str(source_root),asset_root=str(tmp_path/'assets')),
            upstream_commit=UPSTREAM_PIN))
    calls=[]
    value=SimpleNamespace(_reg=reg,_source=SimpleNamespace(read=lambda path,maximum:files[path]),
        _dependencies=SimpleNamespace(distributions=copy.deepcopy(DISTRIBUTIONS)),recheck=lambda:calls.append('recheck'))
    value.calls=calls;value.output=output;value.source_root=source_root
    return value


class AuthoredEngine:
    def __init__(self,calls,stop_after=None):
        self.calls=calls;self.phase='paused';self.episode=0;self.total_tick=0;self.commands=[];self.pending=[]
        self.stop_after=stop_after;self.closed=False
        self.env=SimpleNamespace(renderer=SimpleNamespace())
    def submit(self,command):
        self.commands.append(copy.deepcopy(command));self.pending.append(command['kind'])
        return {'id':command['id'],'status':'queued'}
    def advance(self):
        self.calls.append(('advance',self.total_tick))
        if 'step' in self.pending:
            if self.stop_after is not None and self.total_tick>=self.stop_after:self.phase='terminated'
            else:self.total_tick+=1
        self.pending=[]
        return self.public_state()
    def public_state(self):
        return {'phase':self.phase,'episode':self.episode,'total_tick':self.total_tick}
    def close(self):
        self.calls.append('close');self.closed=True


def versions(monkeypatch,**changes):
    for name,version in dict(EXPECTED,**changes).items():
        module=ModuleType(name);module.__version__=version;monkeypatch.setitem(sys.modules,name,module)


def run_source(tmp_path,monkeypatch,*,stop_after=None,engine_error=None):
    value=admission(tmp_path);versions(monkeypatch)
    engines=[];opened=[];registered=[];exported=[]
    def open_engine(repo_root,asset_root,output,**kwargs):
        opened.append(dict(repo_root=repo_root,asset_root=asset_root,output=output,**kwargs))
        value.calls.append('open');engine=AuthoredEngine(value.calls,stop_after);engines.append(engine)
        if engine_error:engine.advance=lambda:(_ for _ in ()).throw(engine_error)
        return engine
    def register(engine,destination,*args):
        value.calls.append('snapshot');registered.append(destination);return 'snapshot-fixture'
    def export(run,target,format):
        value.calls.append('export');exported.append((run,target,format));Path(target).write_bytes(b'AUTHORED bundle')
        return Path(target)
    with patch('palimpsest.engine.Engine.open',side_effect=open_engine), \
         patch('palimpsest.replay._register_initial',side_effect=register), \
         patch('palimpsest.artifacts.export_run',side_effect=export), \
         patch.object(entry,'renderer_identity',return_value=dict(vendor='AUTHORED',renderer='AUTHORED llvmpipe',
             version='4.6 (Compatibility Profile) Mesa 26.2.2',egl_vendor='Mesa Project',egl_version='1.5',backend='egl')):
        receipt=entry.run(value)
    return value,receipt,engines,opened,registered,exported


def test_source_runs_the_frozen_schedule_on_held_provenance(tmp_path,monkeypatch):
    value,receipt,engines,opened,registered,exported=run_source(tmp_path,monkeypatch)
    engine=engines[0];run=value.output/('a'*32)
    assert len(opened)==1
    call=opened[0];record=call.pop('diagnostics')
    assert type(record) is HeldProvenance
    assert call==dict(repo_root=Path('/puck/source'),asset_root=tmp_path/'assets',output=run/'recording',
        controller='manual',device='cpu',seed=7,scenario='reproduction',texture='checker',run_id='a'*32)
    report=record.report();pins=next(c for c in report['checks'] if c['name']=='held-provenance')['detail']
    assert pins['interpreter']==dict(path='/opt/python/bin/python3.11',size_bytes=21662864,sha256='57'*32,python_version='3.11.15')
    assert pins['lock_sha256']==hashlib.sha256(LOCK).hexdigest() and pins['upstream']['file_count']==2
    assert next(c for c in report['checks'] if c['name']=='dependency:palimpsest')['detail']=='0.1.0.dev0'
    assert report['ready'] is True
    assert registered==[run]
    kinds=[(c['kind'],c.get('payload')) for c in engine.commands]
    assert kinds[:2]==[('set_action',{'action':[.5,0.]}),('step',None)]
    assert kinds.count(('step',None))==48 and kinds.index(('set_action',{'action':[.5,.25]}))==25
    assert [c['id'] for c in engine.commands]==['held-%04d'%i for i in range(1,len(engine.commands)+1)]
    assert all(c['expected_state']=='paused' and c['expected_episode']==0 for c in engine.commands)
    assert engine.closed and exported==[(run,value.output/'source-bundle.zip','bundle')]
    calls=value.calls
    assert calls.index('open')<calls.index('snapshot')<calls.index(('advance',0))<calls.index('close')<calls.index('export')
    assert calls.count('recheck')>=3+48//16+2 and calls[-1]=='recheck'
    assert receipt==dict(kind='puck-held-public-episode-result-v1',version=1,phase='source',
        run_id='a'*32,source_run_id='a'*32,ticks_requested=48,ticks_completed=48,final_phase='paused',
        initial_snapshot_id='snapshot-fixture',provenance_sha256=record.sha256,versions=EXPECTED,
        renderer=dict(vendor='AUTHORED',renderer='AUTHORED llvmpipe',version='4.6 (Compatibility Profile) Mesa 26.2.2',
                      egl_vendor='Mesa Project',egl_version='1.5',backend='egl'),
        bundle=dict(path='source-bundle.zip',size_bytes=15,sha256=hashlib.sha256(b'AUTHORED bundle').hexdigest()),
        runtime_qualified=False,native_authorized=False,collection_authorized=False,executable=False,qualification_claims=[])
    assert len(json.dumps(receipt))<64*1024


def test_source_reports_a_natural_early_stop_without_inventing_ticks(tmp_path,monkeypatch):
    value,receipt,engines,*_=run_source(tmp_path,monkeypatch,stop_after=30)
    assert receipt['ticks_completed']==30 and receipt['final_phase']=='terminated' and engines[0].closed


def test_source_failure_closes_the_engine_and_publishes_nothing(tmp_path,monkeypatch):
    with pytest.raises(RuntimeError,match='AUTHORED engine failure'):
        run_source(tmp_path,monkeypatch,engine_error=RuntimeError('AUTHORED engine failure'))
    assert not (tmp_path/'output/source-bundle.zip').exists()


def run_replay(tmp_path,monkeypatch,status='passed'):
    value=admission(tmp_path,'replay');versions(monkeypatch)
    replayed=[];exported=[]
    def replay(source,destination,**kwargs):
        replayed.append(dict(source=source,destination=destination,**kwargs))
        assert destination.is_dir() and not any(destination.iterdir())
        progress=kwargs['progress'];progress('loading');progress('loading');progress('ready',state={'total_tick':0})
        for tick in range(1,49):
            progress('step',state={'total_tick':tick-1});progress('step',state={'total_tick':tick})
        return {'status':status,'compared_ticks':48,'compared_events':12,'first_divergence':None,'errors':[]}
    def export(run,target,format):
        exported.append((run,target,format));Path(target).write_bytes(b'AUTHORED replay bundle');return Path(target)
    with patch('palimpsest.replay.replay_run',side_effect=replay),patch('palimpsest.artifacts.export_run',side_effect=export):
        receipt=entry.run(value)
    return value,receipt,replayed,exported


def test_replay_hands_the_same_held_provenance_to_a_fresh_owner(tmp_path,monkeypatch):
    value,receipt,replayed,exported=run_replay(tmp_path,monkeypatch)
    call=replayed[0];record=call.pop('diagnostics');call.pop('progress')
    destination=value.output/('b'*32)
    assert type(record) is HeldProvenance and receipt['provenance_sha256']==record.sha256
    assert call==dict(source=value.source_root/('a'*32),destination=destination,mode='actions',
                      repo_root=Path('/puck/source'),asset_root=tmp_path/'assets')
    assert exported==[(destination,value.output/'replay-bundle.zip','bundle')]
    assert value.calls.count('recheck')>=2+48//16+2
    assert receipt==dict(kind='puck-held-public-episode-result-v1',version=1,phase='replay',
        run_id='b'*32,source_run_id='a'*32,ticks_requested=48,provenance_sha256=record.sha256,versions=EXPECTED,
        replay=dict(status='passed',compared_ticks=48,compared_events=12,first_divergence=None),
        bundle=dict(path='replay-bundle.zip',size_bytes=22,sha256=hashlib.sha256(b'AUTHORED replay bundle').hexdigest()),
        runtime_qualified=False,native_authorized=False,collection_authorized=False,executable=False,qualification_claims=[])


@pytest.mark.parametrize('status',['diverged','failed','cancelled'])
def test_replay_that_does_not_pass_publishes_no_bundle(tmp_path,monkeypatch,status):
    with pytest.raises(RuntimeError,match='Held replay did not pass: '+status):run_replay(tmp_path,monkeypatch,status)
    assert not (tmp_path/'output/replay-bundle.zip').exists()


def test_provenance_is_built_only_from_the_authenticated_registration(tmp_path):
    value=admission(tmp_path);first=entry.provenance(value);second=entry.provenance(value)
    assert first.report()==second.report()
    value._source=SimpleNamespace(read=lambda path,maximum:PYPROJECT.replace(b'0.1.0.dev0',b'9.9.9'))
    with pytest.raises(ValueError,match='pyproject'):entry.provenance(value)
    other=tmp_path/'other';other.mkdir()
    value=admission(other)
    value._reg['source_files']=[r for r in value._reg['source_files'] if r['path']!='uv.lock']
    with pytest.raises(ValueError,match='uv.lock'):entry.provenance(value)


@pytest.mark.parametrize('name,version',[('numpy','wrong'),('gymnasium',None)])
def test_expected_versions_are_exact(monkeypatch,name,version):
    versions(monkeypatch)
    if version is None:monkeypatch.delitem(sys.modules,name)
    else:sys.modules[name].__version__=version
    with pytest.raises(ValueError,match=name):entry.versions(EXPECTED)


class Function:
    def __init__(self,result,log,name):self.result=result;self.log=log;self.name=name;self.restype=None;self.argtypes=None
    def __call__(self,*args):self.log.append((self.name,args));return self.result(*args)


def test_renderer_identity_queries_only_already_loaded_libraries_on_the_current_context():
    log=[];loaded=[]
    strings={0x1F00:b'Mesa',0x1F01:b'llvmpipe (LLVM 21.1.0, 256 bits)',0x1F02:b'4.6 (Compatibility Profile) Mesa 26.2.2',
             0x3053:b'Mesa Project',0x3054:b'1.5'}
    class Library:
        def __init__(self,name,mode=0):
            import os
            assert mode&os.RTLD_NOLOAD,'renderer query may not map a new library'
            loaded.append(name)
            if name not in ('libOpenGL.so.0','libEGL.so.1'):raise OSError(name+': not loaded')
            self.glGetString=Function(lambda code:strings[code],log,'glGetString')
            self.eglGetCurrentDisplay=Function(lambda:1234,log,'eglGetCurrentDisplay')
            self.eglQueryString=Function(lambda display,code:strings[code],log,'eglQueryString')
    context=type('GLContext',(),{'__module__':'mujoco.egl','make_current':lambda self:log.append('make_current')})()
    engine=SimpleNamespace(env=SimpleNamespace(renderer=SimpleNamespace(_gl_context=context)))
    with patch('ctypes.CDLL',Library):
        result=entry.renderer_identity(engine)
    assert log[0]=='make_current' and loaded==['libOpenGL.so.0','libEGL.so.1']
    assert result==dict(vendor='Mesa',renderer='llvmpipe (LLVM 21.1.0, 256 bits)',
        version='4.6 (Compatibility Profile) Mesa 26.2.2',egl_vendor='Mesa Project',egl_version='1.5',backend='egl')
    assert ('eglQueryString',(1234,0x3053)) in log


def test_entry_refuses_any_other_phase(tmp_path):
    value=admission(tmp_path);value._reg['episode']['phase']='export'
    with pytest.raises(ValueError,match='phase'):entry.run(value)
