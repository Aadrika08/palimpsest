"""Policy v5 stock absence in epoch11; authored metadata/transport, no vendors."""
import copy
import json

import pytest

from test_puck_cpu_held_amendment05 import validate_both
from test_puck_cpu_held_amendment06 import OTHER_INPUTS, ROSTER06
from test_puck_cpu_held_amendment08 import DIAGNOSTIC_SOURCES
from test_puck_cpu_held_amendment10 import acceptance10_case
from test_puck_cpu_held_observer import setup as observer_setup
from test_puck_cpu_held_parent import result_case
from test_puck_cpu_held_runtime_audit import api as auditor_api


# Independently authored contract; do not derive these from producer constants.
OPTIONAL11=['backports_abc','fx2trt_oss','hypothesis','onnx','onnx_tf','onnxruntime',
            'tabulate','tensorflow','tensorrt','torch2trt','tree','tvm','xarray']
ROSTER11=[
    'OpenGL_accelerate','accimage','av','backports_abc','colorama','defusedxml','dill','flint',
    'fx2trt_oss','gmpy','gmpy2','hypothesis','monkeytype','numpy._distributor_init_local','onnx',
    'onnx_tf','onnxruntime','opt_einsum','org','pydot','pynvml','tabulate','tensorflow','tensorrt',
    'torch._rocm_init','torch2trt','torchdistx','tqdm','tree','triton','tvm','xarray',
]
HIDDEN11=['networkx','pandas','sklearn','torch.utils._cxx_pytree']


def acceptance11_case():
    m,config,blobs,old,candidate_c,candidate_d=acceptance10_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,
                  negative_imports=list(ROSTER11))
    return m,config,blobs,old,candidate_c,candidate_d


def worker_files(m):
    return [dict(path=p,size_bytes=(m.ROOT/p).stat().st_size,sha256=m.digest((m.ROOT/p).read_bytes()))
            for p in m.WORKER_SOURCES]


def test11_fixes_exact_policy_v5_rosters_and_preserves_preparation_projection():
    m,config,blobs,old,_,candidate_d=acceptance11_case()
    prior,prepared=validate_both(m,config,blobs)
    assert m.allocation_output(config)==auditor_api().allocation_output(config)=='runs/puck-cpu-held-qualification-11'
    assert {r['path'] for r in config['sources'] if r!=next(p for p in prior['sources'] if p['path']==r['path'])}==set(DIAGNOSTIC_SOURCES)
    assert len(config['sources'])==24 and len(config['inputs'])==16
    assert len(ROSTER11)==32 and ROSTER11==sorted(set(ROSTER06+OPTIONAL11))
    assert config['negative_imports']==m.QUALIFY11_NEGATIVE_IMPORTS==ROSTER11
    assert m.QUALIFY11_HIDDEN_IMPORTS==auditor_api().HIDDEN11_IMPORTS==HIDDEN11
    assert all(config['inputs'][key]==prior['inputs'][key] for key in OTHER_INPUTS)
    assert prepared['sources']==prior['sources'] and prepared['inputs']==prior['inputs']
    assert config['limits']==m.LIMITS['qualify']
    m.validate_publication_candidate(old,candidate_d,pillow_origins=True)
    auditor_api().publication_candidate(old,candidate_d,pillow_origins=True)


@pytest.mark.parametrize('path',DIAGNOSTIC_SOURCES)
def test11_refuses_missing_preparation_relative_source_changes(path):
    m,config,blobs,*_=acceptance11_case();prior,_=validate_both(m,config,blobs)
    original=next(row for row in prior['sources'] if row['path']==path)
    config['sources']=[copy.deepcopy(original) if row['path']==path else row for row in config['sources']]
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


def test11_refuses_an_additional_source_change():
    m,config,blobs,*_=acceptance11_case();prior,_=validate_both(m,config,blobs)
    next(row for row in config['sources'] if row['path']=='src/palimpsest/puck_native_origins.py')['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('defect',['old-kind','old-version','old-id','bool-version','bool-id','prepare','limits',
    'roster06','roster-extra','roster-missing','roster-hidden','environment','hidden-field','policy-field'])
def test11_refuses_identity_aliases_and_policy_expansion(defect):
    m,config,blobs,*_=acceptance11_case();validate_both(m,config,blobs)
    if defect=='old-kind':config['kind']='puck-cpu-held-runtime-allocation-v10'
    elif defect=='old-version':config['version']=10
    elif defect=='old-id':config['allocation_id']=10
    elif defect=='bool-version':config['version']=True
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='prepare':config.update(phase='prepare',limits=copy.deepcopy(m.LIMITS['prepare']))
    elif defect=='limits':config['limits']['normal_seconds']+=1
    elif defect=='roster06':config['negative_imports']=list(ROSTER06)
    elif defect=='roster-extra':config['negative_imports']=sorted(ROSTER11+['unreviewed'])
    elif defect=='roster-missing':config['negative_imports']=[n for n in ROSTER11 if n!='backports_abc']
    elif defect=='roster-hidden':config['negative_imports']=sorted(ROSTER11+['networkx'])
    elif defect=='environment':config['environment']['UNREVIEWED']='1'
    elif defect=='hidden-field':config['hidden_imports']=list(HIDDEN11)
    else:config['qualification_version']=5
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('role',OTHER_INPUTS)
def test11_preserves_every_noncandidate_input(role):
    m,config,blobs,*_=acceptance11_case();prior,_=validate_both(m,config,blobs)
    config['inputs'][role]['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


def test11_consumed_epoch10_keeps_its_exact_roster():
    m,config,blobs,*_=acceptance10_case();validate_both(m,config,blobs)
    assert config['negative_imports']==ROSTER06
    config['negative_imports']=list(ROSTER11)
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


def test11_worker_registration_requires_explicit_v5_hidden_roster_and_keeps_defaults():
    m,_,_=result_case();files=worker_files(m)
    old,_=m.worker_registration(files,b'{}',negative_imports=['org'])
    q4,_=m.worker_registration(files,b'{}',negative_imports=['org'],qualification_version=4)
    selected,_=m.worker_registration(files,b'{}',negative_imports=['org'],qualification_version=5,
                                     hidden_imports=list(HIDDEN11))
    assert old['qualification']['version']==3 and 'hidden_imports' not in old['qualification']
    assert q4['qualification']['version']==4 and 'hidden_imports' not in q4['qualification']
    assert selected['qualification']['kind']=='puck-held-runtime-import-qualification-v5'
    assert selected['qualification']['version']==5
    assert selected['qualification']['hidden_imports']==HIDDEN11
    for key in selected:
        if key!='qualification':assert selected[key]==old[key]
    assert set(selected['qualification'])==set(old['qualification'])|{'hidden_imports'}
    for key in old['qualification']:
        if key not in ('kind','version'):assert selected['qualification'][key]==old['qualification'][key]


@pytest.mark.parametrize('version,hidden',[(5,None),(5,[]),(5,['pandas','networkx']),(5,['networkx','networkx']),
    (5,['org']),(5,['org.child']),(5,['palimpsest.optional']),(5,'networkx'),(4,['networkx']),(3,['networkx'])])
def test11_worker_helpers_refuse_malformed_or_misplaced_hidden_rosters(version,hidden):
    m,deps,result=result_case();files=worker_files(m)
    result['entry_result']['qualification_version']=version
    if version==5:result['expected_hidden_imports']=hidden
    with pytest.raises(ValueError):
        m.worker_registration(files,b'{}',negative_imports=['org'],qualification_version=version,hidden_imports=hidden)
    with pytest.raises(ValueError):
        m.validate_worker_result(result,registration_sha256='a'*64,dependency_sha256='b'*64,
            dependencies=deps,negative_imports=['org'],qualification_version=version,hidden_imports=hidden)


@pytest.mark.parametrize('defect',[None,'denied-hidden','denied-both','missing-receipt','receipt-differs',
    'denied-undeclared','qualification4','qualification-bool'])
def test11_parent_binds_v5_receipt_rosters_and_denials(defect):
    m,deps,result=result_case()
    result['entry_result']['qualification_version']=5;result['expected_hidden_imports']=list(HIDDEN11)
    if defect=='denied-hidden':result['denied_imports']=['networkx','torch.utils._cxx_pytree']
    elif defect=='denied-both':result['denied_imports']=['networkx','org','sklearn']
    elif defect=='missing-receipt':del result['expected_hidden_imports']
    elif defect=='receipt-differs':result['expected_hidden_imports']=HIDDEN11[:-1]
    elif defect=='denied-undeclared':result['denied_imports']=['networkx','unreviewed']
    elif defect=='qualification4':result['entry_result']['qualification_version']=4
    elif defect=='qualification-bool':result['entry_result']['qualification_version']=True
    def check():
        m.validate_worker_result(result,registration_sha256='a'*64,dependency_sha256='b'*64,
            dependencies=deps,negative_imports=['org'],qualification_version=5,hidden_imports=list(HIDDEN11))
    if defect in (None,'denied-hidden','denied-both'):check()
    else:
        with pytest.raises(ValueError):check()


def test11_older_selections_do_not_accept_hidden_denials():
    m,deps,result=result_case()
    result['denied_imports']=['networkx']
    for version in (3,4):
        result['entry_result']['qualification_version']=version
        with pytest.raises(ValueError):
            m.validate_worker_result(result,registration_sha256='a'*64,dependency_sha256='b'*64,
                dependencies=deps,negative_imports=['org'],qualification_version=version)


@pytest.mark.parametrize('code',[0,7])
def test11_observer_reserves_once_without_modifying_consumed10(tmp_path,monkeypatch,code):
    m,path,_=observer_setup(tmp_path,monkeypatch,'import sys\nprint("AUTHORED11 transport")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,phase='qualify')
    raw=m.canonical(config);path.write_bytes(raw)
    old=tmp_path/'runs/puck-cpu-held-qualification-10';(old/'logs').mkdir(parents=True)
    (old/'logs/stdout.log').write_bytes(b'');(old/'logs/stderr.log').write_bytes(b'AUTHORED consumed10\n')
    previous={p:p.read_bytes() for p in old.rglob('*') if p.is_file()}
    result=m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['stdout']['path']=='runs/puck-cpu-held-qualification-11-external-cli.stdout'
    assert (tmp_path/result['stdout']['path']).read_bytes()==b'AUTHORED11 transport\n'
    assert all(p.read_bytes()==data for p,data in previous.items())
    assert not (old/'result.json').exists() and not (old/'baseline-after.json').exists()
    with pytest.raises(FileExistsError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert all(p.read_bytes()==data for p,data in previous.items())


@pytest.mark.parametrize('field,value',[('phase','prepare'),('version',10),('version',True),('allocation_id',10),('allocation_id',True)])
def test11_observer_rejects_mixed_identity_before_launch(tmp_path,monkeypatch,field,value):
    m,path,_=observer_setup(tmp_path,monkeypatch,'raise AssertionError("must not launch")\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,phase='qualify')
    config[field]=value;raw=m.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]
