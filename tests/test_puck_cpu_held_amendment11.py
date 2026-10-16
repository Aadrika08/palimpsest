"""Policy v5 stock absence in epoch11 on preparation02; authored metadata/transport, no vendors."""
import copy
import json

import pytest

from test_puck_cpu_held_amendment import rebind
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
PREPARATION02='runs/puck-cpu-held-preparation-02'
STAGE02='/tmp/palimpsest-puck-cpu-held-02-authored'


def bind_preparation02(m,config,blobs,*,version=12,stage=STAGE02):
    """Re-express the authored accepted preparation as a fresh epoch over current sources.

    version=12 is the real preparation02 identity; version=1 keeps preparation01's
    identity while moving its stage/sources, isolating the identity refusal."""
    prior=json.loads(blobs['configuration'])
    prior.update(stage_parent=stage,sources=copy.deepcopy(config['sources']))
    if version==12:prior.update(kind='puck-cpu-held-runtime-allocation-v12',version=12,allocation_id=12)
    raw=m.canonical(prior);acceptance=config['preparation_acceptance']
    acceptance['configuration'].update(path='authored-prepare02-configuration.json',size_bytes=len(raw),sha256=m.digest(raw))
    acceptance['result']['path']=PREPARATION02+'/result.json';blobs['configuration']=raw
    prepared=json.loads(blobs['result'])
    prepared.update(stage_parent=stage,sources=copy.deepcopy(prior['sources']),configuration_sha256=m.digest(raw))
    audit=json.loads(blobs['independent_audit']);audit['configuration_sha256']=m.digest(raw)
    cli=json.loads(blobs['externally_observed_auditor_cli'])
    cli['command'][6]=str(m.ROOT/acceptance['configuration']['path']);cli['command'][8]=m.digest(raw)
    if version==12:
        prepared.update(kind='puck-cpu-held-runtime-outcome-v12',version=12,allocation_id=12)
        audit.update(kind='puck-cpu-held-runtime-independent-audit-v12',version=12,allocation_id=12,
                     auditor_source_sha256=m.PREPARATION02_AUDITOR_SHA256)
        cli['command'][10]=str(m.ROOT/'authored-prepare02-transport.json')
    blobs['independent_audit']=m.canonical(audit);blobs['externally_observed_auditor_cli']=m.canonical(cli)
    rebind(m,config,blobs,'result',prepared)
    config['stage_parent']=stage


def acceptance11_case():
    m,config,blobs,old,candidate_c,candidate_d=acceptance10_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,
                  negative_imports=list(ROSTER11))
    bind_preparation02(m,config,blobs)
    return m,config,blobs,old,candidate_c,candidate_d


def worker_files(m):
    return [dict(path=p,size_bytes=(m.ROOT/p).stat().st_size,sha256=m.digest((m.ROOT/p).read_bytes()))
            for p in m.WORKER_SOURCES]


def test11_fixes_exact_policy_v5_rosters_and_binds_preparation02():
    m,config,blobs,old,_,candidate_d=acceptance11_case()
    prior,prepared=validate_both(m,config,blobs)
    assert m.allocation_output(config)==auditor_api().allocation_output(config)=='runs/puck-cpu-held-qualification-11'
    assert (prior['kind'],prior['version'],prior['allocation_id'],prior['phase'])==(
        'puck-cpu-held-runtime-allocation-v12',12,12,'prepare')
    assert config['preparation_acceptance']['result']['path']==PREPARATION02+'/result.json'
    assert config['stage_parent']==prior['stage_parent']==prepared['stage_parent']==STAGE02
    assert prior['sources']==config['sources']==prepared['sources']
    assert len(config['sources'])==24 and len(config['inputs'])==16
    assert len(ROSTER11)==32 and ROSTER11==sorted(set(ROSTER06+OPTIONAL11))
    assert config['negative_imports']==m.QUALIFY11_NEGATIVE_IMPORTS==ROSTER11
    assert m.QUALIFY11_HIDDEN_IMPORTS==auditor_api().HIDDEN11_IMPORTS==HIDDEN11
    assert all(config['inputs'][key]==prior['inputs'][key] for key in OTHER_INPUTS)
    assert prepared['inputs']==prior['inputs'] and prior['inputs']['candidate']!=config['inputs']['candidate']
    assert config['limits']==m.LIMITS['qualify']
    m.validate_publication_candidate(old,candidate_d,pillow_origins=True)
    auditor_api().publication_candidate(old,candidate_d,pillow_origins=True)


@pytest.mark.parametrize('path',DIAGNOSTIC_SOURCES+['src/palimpsest/puck_native_origins.py'])
def test11_refuses_any_source_change_after_preparation02(path):
    m,config,blobs,*_=acceptance11_case();prior,_=validate_both(m,config,blobs)
    next(row for row in config['sources'] if row['path']==path)['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


def test11_refuses_preparation01_acceptance():
    m,config,blobs,*_=acceptance10_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,negative_imports=list(ROSTER11))
    prior=json.loads(blobs['configuration']);prepared=json.loads(blobs['result'])
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)
    with pytest.raises(ValueError,match='preparation02'):auditor_api().preparation_epoch(config,prior,prepared)
    # Even at preparation02's paths and stage, a preparation01 identity is refused.
    bind_preparation02(m,config,blobs,version=1);m.validate_configuration(config)
    with pytest.raises(ValueError,match='^Accepted CPU preparation02 required$'):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError,match='preparation02'):
        auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))


def test10_refuses_preparation02_acceptance():
    m,config,blobs,*_=acceptance10_case();validate_both(m,config,blobs)
    bind_preparation02(m,config,blobs)
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)
    config['preparation_acceptance']['result']['path']='runs/puck-cpu-held-preparation-01/result.json'
    m.validate_configuration(config)
    with pytest.raises(ValueError,match='^Historical CPU preparation01 required$'):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError,match='^Historical preparation01 configuration required$'):
        auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))


@pytest.mark.parametrize('defect',['outcome-kind','outcome-version','outcome-id','audit-kind','audit-version','audit-id',
    'audit-legacy-auditor','audit-foreign-auditor','cli-prep01-transport','prior-stage01','prior-stage-other'])
def test11_preparation02_acceptance_identity_is_exact(defect):
    m,config,blobs,*_=acceptance11_case();validate_both(m,config,blobs)
    prepared=json.loads(blobs['result']);audit=json.loads(blobs['independent_audit'])
    cli=json.loads(blobs['externally_observed_auditor_cli']);prior=json.loads(blobs['configuration'])
    if defect=='outcome-kind':prepared['kind']='puck-cpu-held-runtime-outcome-v1';rebind(m,config,blobs,'result',prepared)
    elif defect=='outcome-version':prepared['version']=1;rebind(m,config,blobs,'result',prepared)
    elif defect=='outcome-id':prepared['allocation_id']=1;rebind(m,config,blobs,'result',prepared)
    elif defect=='audit-kind':audit['kind']='puck-cpu-held-runtime-independent-audit-v1';rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='audit-version':audit['version']=1;rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='audit-id':audit['allocation_id']=1;rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='audit-legacy-auditor':
        audit['auditor_source_sha256']=m.LEGACY_AUDITOR_SHA256;rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='audit-foreign-auditor':
        audit['auditor_source_sha256']='0'*64;rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='cli-prep01-transport':
        cli['command'][10]=str(m.ROOT/'runs/puck-cpu-held-preparation-01-external-cli-transport.json')
        rebind(m,config,blobs,'externally_observed_auditor_cli',cli)
    else:
        stage='/tmp/palimpsest-puck-cpu-held-01' if defect=='prior-stage01' else '/tmp/palimpsest-puck-cpu-held-authored'
        bind_preparation02(m,config,blobs,stage=stage)
    with pytest.raises(ValueError):
        m.validate_configuration(config);m.validate_preparation_acceptance(config,blobs)


def test_preparation02_auditor_pin_is_the_current_independent_auditor():
    m,*_=acceptance11_case()
    assert m.PREPARATION02_AUDITOR_SHA256==m.digest((m.ROOT/'scripts/audit_puck_cpu_held_runtime.py').read_bytes())
    assert m.PREPARATION02_AUDITOR_SHA256!=m.LEGACY_AUDITOR_SHA256


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


@pytest.mark.parametrize('version',[3,4])
def test11_older_selections_refuse_a_hidden_receipt_field(version):
    m,deps,result=result_case();result['entry_result']['qualification_version']=version
    arguments=dict(registration_sha256='a'*64,dependency_sha256='b'*64,dependencies=deps,
                   negative_imports=['org'],qualification_version=version)
    m.validate_worker_result(result,**arguments)
    result['expected_hidden_imports']=[]
    with pytest.raises(ValueError):m.validate_worker_result(result,**arguments)


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
