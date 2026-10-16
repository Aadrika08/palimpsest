"""CPU supervisor contracts with authored receipt data, without vendor imports."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/qualify_puck_cpu_held_runtime.py'


def api():
    assert SCRIPT.is_file(), 'Dedicated CPU supervisor missing'
    spec=importlib.util.spec_from_file_location('cpu_held_parent_test', SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_worker_descriptor_selects_exact_four_import_contract_and_frozen_source():
    m=api();files=[dict(path=p,size_bytes=(ROOT/p).stat().st_size,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in m.WORKER_SOURCES]
    raw=b'{"authored":"dependency descriptor"}'
    worker,command=m.worker_registration(files,raw,negative_imports=['org'])
    assert worker['qualification']['version']==3
    assert worker['qualification']['expected_versions']==m.VERSIONS
    assert worker['source_root']==worker['cwd']=='/puck/source'
    assert worker['dependencies']==dict(path='/puck/control/dependencies.json',size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    assert worker['argv_prefix']==command[:-1]
    assert worker['runtime']['root']==str(Path(m.PYTHON).parent)
    assert worker['qualification']['stdlib_cache_aliases']=={'__mp_main__':'__main__'}
    assert worker['executable'] is False and worker['qualification_claims']==[]
    assert {r['path'] for r in worker['modules']}==set(m.WORKER_SOURCES)-{m.BOOTSTRAP}


def result_case():
    m=api()
    cache=[dict(name='authored_cache',producer='demo.native',phase='module_exec',delegate_attributes=[])]
    dependency=dict(roots=[dict(files=[dict(size_bytes=3)]) for _ in range(4)],import_profile=dict(native_cache=cache))
    result=dict(kind='puck-worker-source-bootstrap-receipt-v1',registration_sha256='a'*64,
        interpreter_object_bound=True,python_version='3.11.15',runtime_qualified=False,
        dependencies_qualified=False,native_authorized=False,collection_authorized=False,
        executable=False,qualification_claims=[],expected_missing_imports=['org'],denied_imports=[],
        dependencies=dict(registration_sha256='b'*64,root_count=4,file_count=4,input_bytes=12,
            native_identity='tmpfs-raw-dev-inode-v1',native_cache_modules=cache),
        entry_result=dict(kind='puck-held-runtime-import-qualification-result-v2',version=2,
            qualification_version=3,status='imports_completed',held_imports_observed=True,
            imports=[dict(name=n,version=m.VERSIONS[n]) for n in ('numpy','torch','torchvision','mujoco')]))
    return m,dependency,result


def test_complete_terminal_requires_cache_bindings_and_exact_order():
    m,deps,result=result_case()
    m.validate_worker_result(result,registration_sha256='a'*64,dependency_sha256='b'*64,
        dependencies=deps,negative_imports=['org'])


@pytest.mark.parametrize('defect',['cache','cache-delegate','order','version','registration','dependency','count','authority','extra-denial','interpreter'])
def test_incomplete_or_substituted_worker_terminal_is_never_accepted(defect):
    m,deps,result=result_case()
    if defect=='cache':result['dependencies']['native_cache_modules']=[]
    elif defect=='cache-delegate':result['dependencies']['native_cache_modules']=copy.deepcopy(result['dependencies']['native_cache_modules']);result['dependencies']['native_cache_modules'][0]['delegate_attributes']=['unexpected']
    elif defect=='order':result['entry_result']['imports'].reverse()
    elif defect=='version':result['entry_result']['imports'][2]['version']='wrong'
    elif defect=='registration':result['registration_sha256']='0'*64
    elif defect=='dependency':result['dependencies']['registration_sha256']='0'*64
    elif defect=='count':result['dependencies']['file_count']=True
    elif defect=='authority':result['collection_authorized']=True
    elif defect=='extra-denial':result['denied_imports']=['undeclared']
    else:result['interpreter_object_bound']=False
    with pytest.raises(ValueError):
        m.validate_worker_result(result,registration_sha256='a'*64,dependency_sha256='b'*64,
            dependencies=deps,negative_imports=['org'])


@pytest.mark.parametrize('names',[[],['org','org'],['z','a'],['org','org.child'],['palimpsest'],['bad-name']])
def test_missing_import_roster_cannot_bypass_source_bindings(names):
    m=api();files=[dict(path=p,size_bytes=(ROOT/p).stat().st_size,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in m.WORKER_SOURCES]
    with pytest.raises(ValueError):m.worker_registration(files,b'{}',negative_imports=names)


def test_configuration_requires_exact_phase_limits_and_source_closure():
    m=api()
    config=m.configuration_template(phase='prepare',root=str(ROOT),stage_parent='/tmp/palimpsest-puck-cpu-held-authored',
        sources=[dict(path=p,size_bytes=1,sha256='a'*64) for p in m.SOURCES],
        inputs={role:dict(path='docs/authored-'+role+'.json',size_bytes=1,sha256='b'*64) for role in m.INPUT_ROLES},
        negative_imports=['org'])
    m.validate_configuration(config)
    for key in ('normal_seconds','hard_seconds','min_available_ram_bytes','max_fds'):
        changed=copy.deepcopy(config);changed['limits'][key]+=1
        with pytest.raises(ValueError):m.validate_configuration(changed)
    for mutate in ('source','unknown','bool-id','overlap'):
        changed=copy.deepcopy(config)
        if mutate=='source':changed['sources'].pop()
        elif mutate=='unknown':changed['undocumented']=True
        elif mutate=='bool-id':changed['allocation_id']=True
        else:changed['stage_parent']=str(ROOT/'runs/overlap')
        with pytest.raises(ValueError):m.validate_configuration(changed)


def test_control_read_ignores_access_time_but_closes_all_descriptors(tmp_path):
    import os
    m=api();leaf=tmp_path/'control.json';leaf.write_bytes(b'{}');os.utime(leaf,(1,2))
    before=len(os.listdir('/proc/self/fd'))
    assert m.read(leaf,1024,hashlib.sha256(b'{}').hexdigest())==b'{}'
    assert len(os.listdir('/proc/self/fd'))==before


def test_control_decode_refuses_numeric_overflow():
    with pytest.raises(ValueError):api().decode(b'{"overflow":1e9999}')


def test_worker_capsule_includes_all_three_bootstrap_scan_prefixes(tmp_path):
    m=api();source={p:(ROOT/p).read_bytes() for p in m.WORKER_SOURCES}
    m.create_capsule(tmp_path/'capsule',m.WORKER_SOURCES,source,lambda path,raw:path.write_bytes(raw))
    for name in ('src/palimpsest','scripts','upstream/fly-gym'):
        assert (tmp_path/'capsule'/name).is_dir()
    assert not list((tmp_path/'capsule/upstream/fly-gym').iterdir())


def test_preparation_binding_refuses_replaced_root_or_registration(tmp_path):
    import os
    m=api();stage=tmp_path/'stage';(stage/'inputs').mkdir(parents=True)
    roots=[];states=[]
    for i in range(4):
        path=stage/'inputs'/('root-'+str(i).zfill(4));path.mkdir(mode=0o700)
        state=path.stat();roots.append(dict(root='/puck/staged/inputs/'+path.name,kind='package',files=[]))
        states.append(dict(root_index=i,device=state.st_dev,inode=state.st_ino))
    m.verify_staged_roots(str(stage),dict(roots=roots),states)
    original=stage/'inputs/root-0000';original.rename(stage/'inputs/replaced');original.mkdir()
    with pytest.raises(ValueError):m.verify_staged_roots(str(stage),dict(roots=roots),states)


def link_case():
    m=api();roles=('inventory','layout','native','baseline','accepted_result','accepted_snapshot','accepted_audit','accepted_configuration','accepted_index')
    inputs={k:dict(path='docs/'+k+'.json',size_bytes=2,sha256=hashlib.sha256(k.encode()).hexdigest()) for k in roles}
    for key in ('observation_configuration','observation_report','observation_result','observation_audit','observation_index'):
        inputs[key]=dict(path='docs/'+key+'.json',size_bytes=2,sha256=hashlib.sha256(key.encode()).hexdigest())
    accepted_raw=b'{\n  \"authored\": true\n}\n'
    inputs['accepted_configuration']=dict(inputs['accepted_configuration'],size_bytes=len(accepted_raw),sha256=hashlib.sha256(accepted_raw).hexdigest())
    frozen=dict(kind='puck-cpu-runtime-characterization-v1',version=1,
        roles={('native_metadata' if k=='native' else k):v['path'] for k,v in inputs.items() if k in roles},
        inputs=[inputs[k] for k in roles])
    a={'inventory':'raw/inventory.json','accepted_result':'raw/result.json','accepted_snapshot':'raw/snapshot.json',
       'accepted_audit':'acceptance-audit-03.json','accepted_configuration':'raw/configuration.json'}
    b={'observation_configuration':'frozen-configuration.json','observation_report':'raw/payload/imports.json',
       'observation_result':'raw/result.json','observation_audit':'outcome-audit-02.json'}
    index=lambda kind,paths:dict(kind=kind,entries=[dict(inputs[k],path=v) for k,v in paths.items()])
    blobs=dict(accepted_configuration=accepted_raw,observation_configuration=m.canonical(frozen),
        accepted_index=m.canonical(index('retained-admission-02-evidence-index-v1',a)),
        observation_index=m.canonical(index('cpu-characterization-evidence-index-v2',b)))
    value=json.loads(blobs['accepted_index']);retained=m.canonical(json.loads(accepted_raw))
    next(r for r in value['entries'] if r['path']=='raw/configuration.json').update(size_bytes=len(retained),sha256=hashlib.sha256(retained).hexdigest())
    blobs['accepted_index']=m.canonical(value)
    return m,dict(inputs=inputs),blobs


def test_retained_metadata_must_match_frozen_observation_roles_and_archived_bytes():
    m,config,blobs=link_case();m.validate_observation_links(config,blobs)
    for defect in ('native','baseline','inventory','accepted_result','observation_report','accepted_configuration'):
        changed=copy.deepcopy(config);changed['inputs'][defect]['sha256']='0'*64
        with pytest.raises(ValueError):m.validate_observation_links(changed,blobs)


def test_archived_receipt_links_cannot_be_satisfied_by_duplicate_rows():
    m,config,blobs=link_case();value=json.loads(blobs['observation_index'])
    value['entries'].append(value['entries'][0]);blobs['observation_index']=m.canonical(value)
    with pytest.raises(ValueError):m.validate_observation_links(config,blobs)


def test_resource_admission_uses_a_regular_tmpfs_probe_and_closes_it():
    import os
    m=api();limits=dict(m.LIMITS['qualify'],min_available_ram_bytes=1,min_free_bytes=1,min_tmpfs_free_bytes=1,max_fds=1)
    before=len(os.listdir('/proc/self/fd'))
    result=m.resource_admission(dict(stage_parent='/tmp/palimpsest-puck-cpu-held-authored-resource',limits=limits))
    assert result['mem_available_bytes']>0 and result['tmpfs_available_bytes']>0
    assert len(os.listdir('/proc/self/fd'))==before


def test_qualification_session_launcher_execs_exact_original_argv():
    import subprocess
    m=api();body='import json,os,sys;print(json.dumps(dict(argv=sys.orig_argv,pid=os.getpid(),ppid=os.getppid(),pgid=os.getpgrp(),sid=os.getsid(0))))'
    worker=[m.PYTHON,'-I','-B','-S','-c',body]
    original=list(worker);command=m.qualification_command(worker)
    assert worker==original and command[-len(worker):]==worker
    process=subprocess.run(command,capture_output=True,text=True,timeout=10)
    assert process.returncode==0,process.stderr
    result=json.loads(process.stdout)
    assert result['argv']==worker and result['pid']==result['pgid']==result['sid'] and result['ppid']>0
