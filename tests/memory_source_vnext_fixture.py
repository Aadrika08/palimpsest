"""Fresh retained authored premises and controlled native boundary; no real physics.

Named upstream source files are copied as software fixtures. All weights/graph/
mappings/runtime-placeholder bytes are generated, never production assets.
"""
from __future__ import annotations
import contextlib
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
from types import ModuleType,SimpleNamespace
import uuid
import numpy as np
import pytest
from scripts import memory_family_source_records_vnext as wire
from palimpsest import assets,memory,memory_decision_world as world,snapshots
from palimpsest.held_provenance import SIMULATION_DISTRIBUTIONS,UPSTREAM_PIN
from test_memory_source_bootstrap_vnext import Environment

REPO=Path(__file__).resolve().parents[1]
SOURCES=('memory_source_parent_entry_vnext.py','memory_family_source_records_vnext.py',
    'memory_family_source_runtime_vnext.py','memory_family_source_raw_audit_vnext.py',
    'memory_family_source_numeric_vnext.py','memory_family_source_qualifier_vnext.py')
UPSTREAM=('core/utils.py','agents/connectome_rnn_agent.py','models/connectome_rnn_model.py','shared_config.py')


def ad(path):
    raw=path.read_bytes(); return dict(path=str(path),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def put(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw); return ad(path)


def record(path,value): return put(path,wire.encode(value))


class NativeModel(SimpleNamespace):
    def __getstate__(self):
        return json.dumps({key:value.tolist() for key,value in vars(self).items() if isinstance(value,np.ndarray)},sort_keys=True).encode()
    def __setstate__(self,raw):
        for key,value in json.loads(raw).items(): setattr(self,key,np.array(value))


class NativeData(SimpleNamespace):
    def __getstate__(self): return b'authored-native-state-only'


class AuthoredEnvironment(Environment):
    def __init__(self,case,trace):
        super().__init__(trace); self.case=case
        self.model=NativeModel(**vars(self.model)); self.model.geom_rgba=np.zeros((20,4))
        self.data=NativeData(**vars(self.data),ctrl=np.zeros(2),time=0.)
        self.renderer=SimpleNamespace(height=128,width=128,_gl_context=object(),close=lambda:trace.append(('renderer.close',)))
        for name in snapshots.ENV_PROFILE:
            if not hasattr(self,name): setattr(self,name,False if name=='end_on_collision' else 'checker' if name=='texture_mode' else None if name=='render_mode' else 1.)
        self.goal_radius=.25; self.max_steps=2100; self.W=self.H=128
        self._action_scale=1.; self._prev_xy=np.zeros(2); self._speed=0.; self._t=0
        self.visited=set(); self._stall_steps=0; self.path_to_draw=np.zeros((0,2)); self.target_to_draw=None
        self.np_random=np.random.default_rng(case['seed']); self._np_random_seed=case['seed']
        self.planner=SimpleNamespace(spec=SimpleNamespace(authored=True))
        graph=world.public_graph(case)
        self.itinerary=[case['landmarks'][name] for name in graph['acquisition_ids']]
        self.counter=0

    def _get_obs(self):
        return dict(cam_left=np.full((128,128,3),73,dtype=np.uint8),cam_right=np.full((128,128,3),127,dtype=np.uint8),
            sensors=dict(collision=False,collision_angle=None,wind_direction=[1.,0.]))

    def step(self,action):
        # Controlled authored native acquisition boundary: scripted geometry,
        # while real symbolic capture/memory/Engine/policy processing still runs.
        if self.counter<len(self.itinerary):
            xy=np.array(self.itinerary[self.counter]); old=self.pose[:2].copy()
            self.pose[:2]=xy; self.pose[2]=math.atan2(xy[1]-old[1],xy[0]-old[0])
        self.counter+=1; self.data.time+=.02; self.data.ctrl[:]=np.asarray(action,dtype=np.float64)
        return self._get_obs(),0.,False,False,dict(dist_to_goal=10.,stalled=False)


def install_native(monkeypatch,case,trace):
    native=ModuleType('mujoco'); native.__version__='authored-native-boundary'
    native.MjModel=NativeModel; native.mjtState=SimpleNamespace(mjSTATE_INTEGRATION=1)
    native.mj_stateSize=lambda model,kind:4
    native.mj_getState=lambda model,data,array,kind:array.fill(0.)
    native.mj_forward=lambda model,data:data.geom_xpos.__setitem__((slice(None),slice(0,2)),data.qpos.reshape(20,2))
    monkeypatch.setitem(sys.modules,'mujoco',native)
    from palimpsest import flynn
    real_import=flynn.import_upstream
    def upstream(repo,name):
        if name=='run_connectome_rnn_checkpoint': return SimpleNamespace(_make_env=lambda *a,**k:AuthoredEnvironment(case,trace))
        return real_import(repo,name)
    monkeypatch.setattr(flynn,'import_upstream',upstream)


def fixture_model(root,monkeypatch,case):
    import torch
    from palimpsest.flynn import import_upstream,load_policy
    repo=root/'freeze/repo'; assets_root=root/'freeze/assets'; graph=assets_root/'graph'
    repo.mkdir(parents=True); graph.mkdir(parents=True)
    for name in UPSTREAM: put(repo/'upstream/fly-gym'/name,(REPO/'upstream/fly-gym'/name).read_bytes())
    for package in ('core','agents','models'): put(repo/'upstream/fly-gym'/package/'__init__.py',b'')
    # Import genuine copied upstream classes; restore previous registrations at test end.
    for name in ('core','core.utils','agents','agents.connectome_rnn_agent',
                 'models','models.connectome_rnn_model','shared_config'):
        # Record an original ABSENT entry too: otherwise a fresh fixture import
        # leaks into a later unit whose real origin guard must keep refusing it.
        monkeypatch.setitem(sys.modules,name,sys.modules.get(name))
        sys.modules.pop(name,None)
    monkeypatch.syspath_prepend(str(repo/'upstream/fly-gym'))
    edge=put(graph/'connections_princeton.csv',('pre,post,weight\n'+''.join(f'{100+i},{100+(i+1)%12},1\n' for i in range(12))).encode())
    names=assets.MAPPING_NAMES
    for name in names:
        if name.startswith('visual_column'):
            offset=0 if 'left' in name else 3
            raw='root_id,type,x,y\n'+''.join(f'{100+offset+layer},L{layer+1},{i%30},{i//30}\n' for layer in range(3) for i in range(801))
        elif name=='head_bristles_left.csv': raw='root_id\n106\n'
        elif name=='head_bristles_right.csv': raw='root_id\n107\n'
        elif name=='descending_neurons.csv': raw='root_id\n108\n109\n'
        elif name=='JO-C_and_JO-E.csv': raw='root_id\n110\n111\n110\n111\n110\n'
        else: raw='root_id,primary_type\n'+''.join(f'{100+i},A\n' for i in range(12))
        put(graph/name,raw.encode())
    torch.manual_seed(7); torch.set_num_threads(1)
    utils=import_upstream(repo,'core.utils'); agent_class=import_upstream(repo,'agents.connectome_rnn_agent').ConnectomeAgent
    options=dict(zip(('photoreceptor_left_csv','photoreceptor_right_csv','tactile_left_csv','tactile_right_csv','descending_neurons_csv','cell_types_csv','wind_sensing_csv'),[str(graph/name) for name in names]))
    with contextlib.redirect_stdout(io.StringIO()): cell,positions,splits,_=utils.build_connectome_cell(edge['path'],torch.device('cpu'),torch.float32,**options)
    assert cell.Nin==4813 and cell.N==12
    agent=agent_class(cell,positions,splits); checkpoint=graph/'fixture.pt'; torch.save(agent.state_dict(),checkpoint)
    # Original static actual manifest is permitted as a layout template only;
    # every fixture asset descriptor is newly authored and independently held.
    manifest=json.loads((REPO/'model_manifests/flynn-full-vision.json').read_bytes())
    archive=put(assets_root/manifest['files'][0]['path'],b'authored-unused-archive')
    for item,desc in zip(manifest['files'],(archive,ad(checkpoint))):
        item['path']=str(Path(desc['path']).relative_to(assets_root)); item.update({key:desc[key] for key in ('size_bytes','sha256')})
    target=assets_root/('graph-'+archive['sha256']); target.mkdir()
    # No graph copying after leases: prepare independent fixture bytes now.
    for name in [Path(edge['path']).name,*names]: put(target/name,(graph/name).read_bytes())
    graph_manifest=manifest['graph']; graph_manifest['edge_identity'].update(size_bytes=edge['size_bytes'],sha256=edge['sha256'],archive_member='connections_princeton.csv',derived_from_archive_sha256=archive['sha256'])
    for row,name in zip(graph_manifest['mapping_files'],names):
        desc=ad(target/name); row['path']=name; row['archive_identity']={key:desc[key] for key in ('size_bytes','sha256')}
        row['source_path']='upstream/fly-gym/connectomes/drosophila adult connectome/'+name; source=put(repo/row['source_path'],(target/name).read_bytes()); row.update({key:source[key] for key in ('size_bytes','sha256')})
    record(repo/'model_manifests/flynn-full-vision.json',manifest)
    record(target/'palimpsest-prepared.json',dict(archive_sha256=archive['sha256'],edge_path='connections_princeton.csv',edge_sha256=edge['sha256'],upstream_commit=assets.UPSTREAM_COMMIT,mapping_files=copy.deepcopy(graph_manifest['mapping_files']),provenance_limit=manifest['provenance_limit']))
    put(repo/'uv.lock',b'# authored lock\n'); put(repo/'src/palimpsest/authored.py',b'# authored source fixture\n')
    (root/'freeze/runtime').mkdir()
    # Warm ordinary numeric/import paths before full-stat leases; any generated
    # ML/Python temporary bytes stay in the retained precreated harness scratch.
    with contextlib.redirect_stdout(io.StringIO()):
        warm=load_policy(repo,target/'connections_princeton.csv',checkpoint,'cpu',case['seed'])
    warm.act(dict(cam_left=np.zeros((128,128,3),dtype=np.uint8),cam_right=np.zeros((128,128,3),dtype=np.uint8),sensors=dict(collision=False,collision_angle=None,wind_direction=[1.,0.])))
    snapshots._torch_profile(); warm=None
    # Fixed Model.graph first descriptor is the actual prepared edge consumed by load_policy.
    return repo,assets_root,dict(manifest=None,checkpoint=ad(checkpoint),graph=[ad(target/'connections_princeton.csv')],mapping=sorted([ad(target/name) for name in names],key=lambda d:d['path']),upstream_sources=sorted([ad(repo/'upstream/fly-gym'/name) for name in UPSTREAM],key=lambda d:d['path']),upstream_commit=UPSTREAM_PIN,controller='flynn',device='cpu',dtype='torch.float32',input_width=4813,threads=1,training=False,requires_grad=False)


def tree(root):
    # Inventory only newly authored fixture roots, never a production catalog.
    dirs=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())
    files=sorted([ad(p) for p in root.rglob('*') if p.is_file()],key=lambda d:d['path'])
    return dict(root=str(root),directories=dirs,files=files)


def build(root,monkeypatch):
    import tempfile
    scratch=root.parent/'harness-scratch'; scratch.mkdir()
    monkeypatch.setattr(tempfile,'tempdir',str(scratch))
    monkeypatch.setenv('TMPDIR',str(scratch))
    import torch
    from scripts import memory_source_runtime_closure_v1 as runtime
    fixture_id='source-vertical-authored-4813'; case=world.make_family_case('development',0,0,'change')
    root.mkdir(); (root/'freeze/metadata').mkdir(parents=True)
    repo,assets_root,model=fixture_model(root,monkeypatch,case); trace=[]; install_native(monkeypatch,case,trace)
    metadata=root/'freeze/metadata'; rt=root/'freeze/runtime'
    interpreter=put(rt/'python',b'authored executable identity premise only')
    put(rt/'venv/pyvenv.cfg',b'authored runtime fixture\n'); (rt/'venv/bin').mkdir(parents=True)
    alias=rt/'venv/bin/python'; alias.symlink_to(rt/'python')
    sources=sorted([ad(REPO/name) for name in wire.HARNESS_SOURCES],key=lambda d:d['path'])
    provenance_files=[ad(repo/'src/palimpsest/authored.py')]
    pins=dict(python_alias=str(alias),python_elf=interpreter,owner_source=ad(REPO/'scripts/memory_family_source_runtime_vnext.py'),pyvenv_config=ad(rt/'venv/pyvenv.cfg'),required_sources=sources)
    # Complete runtime root excludes its explicitly pinned interpreter alias (the
    # unchanged runtime adapter permits the alias outside complete selected trees).
    runtime_root=rt/'complete'; runtime_root.mkdir()
    for name in SIMULATION_DISTRIBUTIONS:
        put(runtime_root/(name+'.dist-info/METADATA'),f'Name: {name}\nVersion: 0.0.1\n\nAuthored metadata premise only.\n'.encode())
    runtime_tree=tree(runtime_root)
    # Semantic pin records can be genuine standalones in unchanged RuntimeHandle.
    standalone=sorted([interpreter,pins['pyvenv_config'],*sources],key=lambda d:d['path'])
    profile=dict(profile_id=runtime.PROFILE['profile_id'] if 'profile_id' in runtime.PROFILE else 'memory-source-runtime-profile-v1-proposed',profile_sha256=runtime.PROFILE_SHA256,load_policy='retained-unqualified-v1')
    recipe=dict(schema='memory-source-runtime-recipe-v1',preparation_id='1'*32,**profile,intended_roots=[str(runtime_root)],intended_standalones=[d['path'] for d in standalone],method='externally-prepared-complete-runtime-input')
    recipe_d=record(metadata/'runtime-recipe.json',recipe)
    manifest=dict(schema='memory-source-runtime-manifest-v1',preparation_id='1'*32,**profile,recipe=recipe_d,roots=[dict(root=str(runtime_root),kind='complete',directories=runtime_tree['directories'],files=[dict(d,path=str(Path(d['path']).relative_to(runtime_root))) for d in runtime_tree['files']])],standalones=standalone,pins=pins)
    manifest_d=record(metadata/'runtime-manifest.json',manifest)
    evidence=put(metadata/'runtime-evidence',b'authored runtime ledger premise'); operation=put(metadata/'runtime-operation',b'authored operation premise')
    ledger=dict(schema='memory-source-runtime-preparation-ledger-v1',preparation_id='1'*32,state='completed',recipe=recipe_d,manifest=manifest_d,baseline=dict(accounting_id='2'*32,project_cpu_ns=0,memory_cpu_ns=0,evidence=evidence),operations=[dict(operation_id='3'*32,outcome='failed',memory_cpu_ns=0,evidence=operation)],retained_files=sorted([evidence,operation],key=lambda d:d['path']),runtime_input_bytes=sum(d['size_bytes'] for d in standalone+runtime_tree['files']),external_record_bytes=recipe_d['size_bytes']+manifest_d['size_bytes']+evidence['size_bytes']+operation['size_bytes'],totals=dict(project_cpu_ns=0,memory_cpu_ns=0),cumulative_charge_reference=dict(evidence=evidence,project_cpu_ns=0,memory_cpu_ns=0))
    ledger_d=record(metadata/'runtime-ledger.json',ledger)
    reference=dict(schema='memory-source-runtime-reference-v1',**profile,recipe=recipe_d,manifest=manifest_d,ledger=ledger_d)
    identity=dict(schema=wire.record_schema('model-identity',True),fixture_id=fixture_id,input_width=4813,hidden_width=12,runtime_sources=sources,model_sources=model['upstream_sources'],weights=[model['checkpoint']],graph=model['graph'],python_version='.'.join(map(str,sys.version_info[:3])),torch_version=str(torch.__version__),dtype='torch.float32',device='cpu',threads=1,training=False,requires_grad=False,scope='software-unit-only',claims=wire.CLAIMS.copy())
    model['manifest']=record(metadata/'authored-model-identity.json',identity)
    wrappers=[]; expected=[]
    for index,(purpose,kind) in enumerate([('pre-heldout-development-history','historical'),('training-namespace','training')]):
        namespace=root/'freeze/namespaces'/purpose
        export=dict(schema='memory-family-namespace-export-v3',source_id=purpose,kind=kind,known_sources=['authored-'+kind],historical_run_ids=[],historical_authored_ids=[],training_seeds=[])
        export_d=record(namespace/'namespace-export.json',export)
        one=dict(entries=1,files=1,bytes=export_d['size_bytes'],inventory_sha256=memory.sha256([dict(path='namespace-export.json',kind='file',executable=False,bytes=export_d['size_bytes'],sha256=export_d['sha256'])]),export_bytes=export_d['size_bytes'],export_sha256=export_d['sha256'])
        for name in ('known_sources','historical_run_ids','historical_authored_ids','training_seeds'): one[name+'_count']=len(export[name]); one[name+'_sha256']=memory.sha256(export[name])
        expected.append(dict(source_id=purpose,kind=kind,expected=one)); wrappers.append(dict(schema=wire.record_schema('namespace-export-binding',True),purpose=purpose,fixture_id=fixture_id,coverage_contract=None,root=str(namespace),export=export_d,scope='software-unit-only',claims=wire.CLAIMS.copy()))
    coverage=record(metadata/'authored-namespace-coverage.json',dict(schema=wire.record_schema('namespace-coverage',True),fixture_id=fixture_id,scope='software-unit-only',sources=expected,file_allowlist=['namespace-export.json'],max_identity_characters=128,max_metadata_bytes=32*wire.MiB,max_values=100000,claims=wire.CLAIMS.copy()))
    for wrapper in wrappers: wrapper['coverage_contract']=coverage
    ds={}
    def freeze(key,filename,value):
        desc=record(metadata/(filename+'.json'),value); ds[key]=dict(desc,path='freeze/metadata/'+filename+'.json'); return ds[key]
    freeze('history_namespace','history',wrappers[0]); freeze('training_namespace','training',wrappers[1])
    provenance=dict(interpreter=dict(interpreter,python_version='.'.join(map(str,sys.version_info[:3]))),upstream=dict(path=str(repo/'upstream/fly-gym'),commit=UPSTREAM_PIN,files=[dict(d,path=str(Path(d['path']).relative_to(repo/'upstream/fly-gym'))) for d in model['upstream_sources']]),distributions=[dict(name=name,version='0.0.1',root_index=0,metadata_path=name+'.dist-info/METADATA') for name in SIMULATION_DISTRIBUTIONS],palimpsest_version='0.1.0',lock_sha256=ad(repo/'uv.lock')['sha256'],environment={'MUJOCO_GL':'egl'})
    load=dict(schema=wire.record_schema('load-environment',True),runtime_reference=reference,runtime_requirements=dict(roots=[str(runtime_root)],pins=pins),model=model,provenance=provenance,roots=[dict(role=role,path=str(p)) for role,p in [('repo',repo),('assets',assets_root),('runtime',runtime_root),('history',Path(wrappers[0]['root'])),('training',Path(wrappers[1]['root']))]],environment=provenance['environment'],working_directory=str(repo),python_path=[str(repo)],native_libraries=[],claims=wire.CLAIMS.copy())
    freeze('load_environment','load',load)
    closure=dict(schema=wire.record_schema('software-closure',True),roots=[tree(repo),tree(assets_root),runtime_tree],standalones=sources,entry_sources=sources,claims=wire.CLAIMS.copy())
    freeze('source_closure','source-closure',closure)
    entrypoints=dict(parent='scripts/memory_source_parent_entry_vnext.py:run_attempt',producer='scripts/memory_family_source_runtime_vnext.py:produce_source',raw_auditor='scripts/memory_family_source_raw_audit_vnext.py:audit_source',converter='scripts/memory_family_source_numeric_vnext.py:convert_source',qualifier='scripts/memory_family_source_qualifier_vnext.py:qualify_source')
    freeze('profile','profile',dict(schema=wire.record_schema('software-profile',True),source_closure=ds['source_closure'],entrypoints=entrypoints,load_environment=ds['load_environment'],codec=dict(chunk_rows=32,base_arrays=16,companion_arrays=3,input_width=4813,source_rows_max=1200,numeric_format='palimpsest-source-numeric-vnext-v1'),claims=wire.CLAIMS.copy()))
    run=str(uuid.uuid4()); attempt=str(uuid.uuid4())
    job=dict(schema=wire.record_schema('job',True),operation='source',condition=None,split='development',block=0,row=0,kind='change',case=case,source_run_id=run,attempt_id=attempt,readset=ds,workspace_root=str(root),output_root='output',limits=wire.LIMITS.copy())
    capacity=dict(frozen_input_bytes=0,frozen_input_files=0,frozen_input_directories=0,reserved_output_directories=len(wire.reserved_directories(job)),required_free_bytes=0)
    freeze('resources','resources',dict(schema=wire.record_schema('resource-contract',True),limits=wire.LIMITS.copy(),fixture=dict(fixture_id=fixture_id,scope='software-unit-only'),capacity=capacity,claims=wire.CLAIMS.copy()))
    caps=dict(profile=262144,source_closure=wire.MiB,load_environment=262144,resources=65536,history_namespace=524288,training_namespace=524288)
    inputs=sorted([dict(role=name,path=ds[name]['path'],max_bytes=cap) for name,cap in caps.items()]+[dict(role='source-job',path='freeze/metadata/job.json',max_bytes=262144),dict(role='authorization',path='freeze/metadata/authorization.json',max_bytes=262144),dict(role='authored-model-identity',path='freeze/metadata/authored-model-identity.json',max_bytes=262144)],key=lambda d:(d['role'],d['path']))
    freeze('producer_plan','plan',dict(schema=wire.record_schema('producer-plan',True),profile=ds['profile'],source_closure=ds['source_closure'],case=case,source_run_id=run,source_job=dict(role='source-job',path='freeze/metadata/job.json',max_bytes=262144),inputs=inputs,output_roster=wire.output_roster(case['case_id'],run),namespace=dict(history=ds['history_namespace'],training=ds['training_namespace']),resource_envelope=ds['resources'],claims=wire.CLAIMS.copy()))
    job_bytes=wire.encode(job,262144); put(metadata/'job.json',job_bytes)
    now=time.monotonic_ns()
    auth=dict(schema=wire.record_schema('attempt-authorization',True),attempt_id=attempt,source_run_id=run,job=wire.describe('freeze/metadata/job.json',job_bytes),readset=ds,workspace_root=str(root),resource_contract=ds['resources'],phases=list(wire.PHASES),issued_monotonic_ns=now,deadline_monotonic_ns=now+120_000_000_000,fixture_id=fixture_id,scope='software-unit-only',claims=wire.CLAIMS.copy())
    authorization_bytes=wire.encode(auth,262144); put(metadata/'authorization.json',authorization_bytes)
    # Finish the acyclic descriptors and exact unique input census before the
    # fixture is frozen. Byte totals include the metadata records themselves.
    resources=wire.decode((metadata/'resources.json').read_bytes())
    plan=wire.decode((metadata/'plan.json').read_bytes())
    for _ in range(8):
        values={name:wire.decode((root/desc['path']).read_bytes()) for name,desc in ds.items()}
        values['coverage']=wire.decode((metadata/'authored-namespace-coverage.json').read_bytes())
        values['authored_identity']=identity
        descriptors,trees=wire.input_closure(job,auth,values,True)
        unique={d['path']:d for d in [*descriptors,evidence,operation]}
        directories={'/',str(alias.parent)}
        directories.update(str(p) for p in alias.parent.parents)
        for desc in unique.values():
            parent=Path(desc['path']).parent
            directories.update(str(p) for p in (parent,*parent.parents))
        for t in trees:
            directory=Path(t['root']); directories.update(str(p) for p in (directory,*directory.parents))
            for relative in t['directories']: directories.add(str(directory/relative))
        measured=dict(frozen_input_bytes=sum(d['size_bytes'] for d in unique.values()),frozen_input_files=len(unique),frozen_input_directories=len(directories))
        if all(resources['capacity'][name]==value for name,value in measured.items()): break
        resources['capacity'].update(measured); freeze('resources','resources',resources)
        plan['resource_envelope']=ds['resources']; freeze('producer_plan','plan',plan)
        job_bytes=wire.encode(job,262144); put(metadata/'job.json',job_bytes)
        auth.update(job=wire.describe('freeze/metadata/job.json',job_bytes),readset=ds,resource_contract=ds['resources'])
        authorization_bytes=wire.encode(auth,262144); put(metadata/'authorization.json',authorization_bytes)
    else: raise AssertionError('Authored input census failed to stabilize')
    for directory in wire.reserved_directories(job): (root/directory).mkdir(exist_ok=True)
    return SimpleNamespace(root=root,job=job,auth=auth,job_bytes=job_bytes,authorization_bytes=authorization_bytes,trace=trace,load=load)


def observer(fixture):
    """Test observer of fixed sightings only; no accounting/independence assertion."""
    from scripts.memory_source_parent_entry_vnext import _initial_bytes,_publish_bytes
    job=fixture.job; root=fixture.root; run=job['source_run_id']; case=job['case']['case_id']
    owner=f'output/.pending/{case}/source/owner.json'; report=f'output/.pending/{case}/.raw/{run}/worker-report.json'; k=f'output/controls/{run}/producer/'
    roster={row['path']:row for row in wire.output_roster(case,run)}; errors=[]
    def wait():
        try:
            deadline=time.monotonic()+10
            while not (root/owner).exists():
                if time.monotonic()>deadline: raise TimeoutError('Authored observer owner wait')
                time.sleep(.002)
            owner_d=wire.describe(owner,_initial_bytes(str(root/owner),16384)); started=time.monotonic_ns()
            while not (root/(k+'cleanup.json')).exists():
                if time.monotonic()>deadline: raise TimeoutError('Authored observer report wait')
                if list((root/f'output/controls/{run}/failures').glob('*/failure.json')): return
                time.sleep(.002)
            report_d=wire.describe(report,_initial_bytes(str(root/report),32768)); cleanup_d=wire.describe(k+'cleanup.json',_initial_bytes(str(root/(k+'cleanup.json')),65536))
            stdout=_publish_bytes(job,k+'stdout',b'',roster); stderr=_publish_bytes(job,k+'stderr',b'',roster)
            supervisor=dict(schema=wire.record_schema('producer-supervision',True),attempt_id=job['attempt_id'],job=wire.describe('freeze/metadata/job.json',fixture.job_bytes),authorization_sha256=hashlib.sha256(fixture.authorization_bytes).hexdigest(),resource_contract=job['readset']['resources'],process_role='workload',segment='producer-only',scope='observed-owner-intent-to-closed-worker-report',owner_intent=owner_d,worker_report=report_d,cleanup=cleanup_d,stdout=stdout,stderr=stderr,started_monotonic_ns=started,ended_monotonic_ns=time.monotonic_ns(),status='closed',claims=wire.CLAIMS.copy())
            _publish_bytes(job,k+'supervisor.json',wire.encode(supervisor,65536),roster)
        except BaseException as error: errors.append(error)
    thread=threading.Thread(target=wait); thread.start(); return thread,errors
