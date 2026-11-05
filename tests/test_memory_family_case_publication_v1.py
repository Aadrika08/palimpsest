"""Authored order attestations only; no real observer qualification."""
import copy
import hashlib
import importlib
import uuid
import pytest
from palimpsest import memory
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_analysis_v3 as analysis

NAME = 'scripts.memory_family_case_publication_v1'

def module():
    return importlib.import_module(NAME)

def descriptor(path, payload):
    return dict(path=path, size_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())

def fixture(row=0):
    conditions = list(compact.PROTOCOL['analysis_contract']['conditions'])
    slot = dict(case_id='authored-case',case_sha256='a'*64,source_run_id=uuid.UUID(int=1).hex,
                condition_run_ids={c:uuid.UUID(int=i+2).hex for i,c in enumerate(conditions)})
    observer=dict(source_sha256='b'*64,qualification_sha256='c'*64,
        boot_id=str(uuid.UUID(int=1)),pid_namespace='pid:[123]',clock='CLOCK_BOOTTIME',ticks_per_second=100)
    payloads={}; contracts={}; commits={}; owners=[]
    for i,c in enumerate(['source']+analysis.condition_order(row)):
        condition=None if c=='source' else c
        run=slot['source_run_id'] if c=='source' else slot['condition_run_ids'][c]
        operation='source' if c=='source' else 'condition'
        launch=(100+i*10)*10**9
        facts=dict(case_id=slot['case_id'],run_id=run,operation=operation,condition=condition,
            observer=copy.deepcopy(observer),pid=100+i,starttime=(100+i*10)*100,pgid=100+i,
            launch_ns=launch,reaped_ns=launch+10**9,drained_ns=launch+2*10**9,returncode=0,status='completed')
        job=descriptor(f'controls/{c}/job.json',b'{}\n'); payloads[job['path']]=b'{}\n'
        facts['job']=job
        supervisor={'schema':'memory-family-order-supervisor-v1',**facts}
        cleanup={k:v for k,v in facts.items() if k not in ('launch_ns','reaped_ns','returncode','status')}
        cleanup.update(schema='memory-family-order-cleanup-v1',status='drained')
        owner=dict(schema='memory-family-source-owner-v4' if c=='source' else 'memory-family-condition-owner-v1',
            case_id=slot['case_id'],run_id=run,owner_source_sha256='d'*64,claims=copy.deepcopy(compact.PROTOCOL['claims']))
        if c!='source': owner.update(condition=c,source_run_id=slot['source_run_id'])
        desc={}
        for role,obj in (('supervisor',supervisor),('cleanup',cleanup),('owner',owner)):
            data=memory.canonical_bytes(obj); desc[role]=descriptor(f'controls/{c}/{role}.json',data);payloads[desc[role]['path']]=data
        contract=dict(case=dict(case_id=slot['case_id'],case_sha256=slot['case_sha256'],row=row),run_id=run,
            owner_source_sha256='d'*64,owner_record=desc['owner'],controls=dict(job=job,supervisor=desc['supervisor'],cleanup=desc['cleanup']))
        data=memory.canonical_bytes(contract); registration=descriptor(f'controls/{c}/registration.json',data)
        payloads[registration['path']]=data;contracts[c]=contract
        commit=descriptor(f'cases/authored-case/{c}/commit.json',b'{}\n')
        if c!='source': commits[c]=commit
        owners.append(dict(operation=operation,condition=condition,run_id=run,registration=registration,
            job=job,owner=desc['owner'],supervisor=desc['supervisor'],cleanup=desc['cleanup'],commit=commit,
            **{k:facts[k] for k in ('pid','starttime','pgid','launch_ns','reaped_ns','drained_ns','returncode','status')}))
    audit=dict(schema='memory-family-case-execution-audit-v1',publication_protocol_sha256='e'*64,
        case_slot=slot,source_commit=owners[0]['commit'],condition_commits=commits,observer=observer,
        owners=owners,claims=copy.deepcopy(compact.PROTOCOL['claims']))
    return dict(audit=copy.deepcopy(audit),case_slot=copy.deepcopy(slot),source_commit=copy.deepcopy(owners[0]['commit']),condition_commits=copy.deepcopy(commits),
        contracts=contracts,control_payloads=payloads,publication_protocol_sha256='e'*64)

def accept(monkeypatch, request):
    monkeypatch.setattr(module().pins,'ACCEPTED_EXECUTION_AUDIT_SHA256',frozenset({hashlib.sha256(memory.canonical_bytes(request['audit'])).hexdigest()}))

class Forbidden(dict):
    def __deepcopy__(self,memo): raise AssertionError('protected controls copied before trust')
    def __getitem__(self,key): raise AssertionError('protected controls read before trust')

def test_empty_execution_trust_refuses_before_control_access():
    request=fixture(); request['control_payloads']=Forbidden()
    with pytest.raises(PermissionError): module().validate_execution_audit(**request)

def test_authored_attestation_copies_and_preserves_false_claims(monkeypatch):
    request=fixture();accept(monkeypatch,request)
    result=module().validate_execution_audit(**request)
    assert result==request['audit'] and result is not request['audit']
    result['observer']['clock']='mutated'
    assert request['audit']['observer']['clock']=='CLOCK_BOOTTIME'
    assert result['claims']==compact.PROTOCOL['claims']

@pytest.mark.parametrize('defect',['missing','extra','duplicate','wrong-run','bool-pid','pid-pgid','overlap','reused-identity','clock','tick-rate','own-after-oracle','nonzero','incomplete-drain','old-supervisor','old-cleanup','job','commit','registration','observer','owner','bytes'])
def test_invalid_accepted_fixture_refused(monkeypatch,defect):
    request=fixture(row=1 if defect=='own-after-oracle' else 0); a=request['audit']; o=a['owners'][1]
    if defect=='missing':a['owners'].pop()
    elif defect=='extra':a['owners'].append(copy.deepcopy(o))
    elif defect=='duplicate':a['owners'][2]=copy.deepcopy(o)
    elif defect=='wrong-run':o['run_id']=uuid.UUID(int=88).hex
    elif defect=='bool-pid':o['pid']=True
    elif defect=='pid-pgid':o['pgid']+=1
    elif defect=='overlap':o['launch_ns']=0
    elif defect=='reused-identity':o.update(pid=a['owners'][0]['pid'],pgid=a['owners'][0]['pgid'],starttime=a['owners'][0]['starttime'])
    elif defect=='clock':a['observer']['clock']='CLOCK_MONOTONIC'
    elif defect=='tick-rate':a['observer']['ticks_per_second']=0
    elif defect=='nonzero':o['returncode']=1
    elif defect=='incomplete-drain':o['drained_ns']=o['reaped_ns']-1
    elif defect in ('job','commit','registration','owner'):o[defect]['sha256']='f'*64
    elif defect=='observer':a['observer']['boot_id']=str(uuid.UUID(int=9))
    elif defect in ('old-supervisor','old-cleanup','bytes'):
        role='supervisor' if defect!='old-cleanup' else 'cleanup'; d=o[role]
        value=__import__('json').loads(request['control_payloads'][d['path']]); value['schema']='old'
        payload=memory.canonical_bytes(value) if defect!='bytes' else request['control_payloads'][d['path']]+b' '
        request['control_payloads'][d['path']]=payload
        updated=descriptor(d['path'],payload); o[role]=updated
        name=o['condition']; request['contracts'][name]['controls'][role]=copy.deepcopy(updated)
        reg=o['registration']; data=memory.canonical_bytes(request['contracts'][name]); o['registration']=descriptor(reg['path'],data); request['control_payloads'][reg['path']]=data
    accept(monkeypatch,request)
    with pytest.raises((ValueError,PermissionError)): module().validate_execution_audit(**request)


def refresh_controls(request):
    """Authored prospective controls, never real accepted execution."""
    for o in request['audit']['owners']:
        c='source' if o['condition'] is None else o['condition']
        for role in ('supervisor','cleanup'):
            old=o[role]; value=__import__('json').loads(request['control_payloads'][old['path']])
            for key in ('pid','starttime','pgid','launch_ns','reaped_ns','drained_ns'):
                if key in value:value[key]=o[key]
            payload=memory.canonical_bytes(value)
            new=descriptor(old['path'],payload);o[role]=new
            request['contracts'][c]['controls'][role]=copy.deepcopy(new)
            request['control_payloads'][new['path']]=payload
        reg=o['registration'];payload=memory.canonical_bytes(request['contracts'][c])
        o['registration']=descriptor(reg['path'],payload);request['control_payloads'][reg['path']]=payload


def test_pid_reuse_new_start_and_adjacent_intervals_are_representable(monkeypatch):
    request=fixture();first,second=request['audit']['owners'][:2]
    first['drained_ns']=second['launch_ns']
    second['pid']=second['pgid']=first['pid']
    refresh_controls(request);accept(monkeypatch,request)
    module().validate_execution_audit(**request)


def test_wrong_tick_conversion_is_rejected_even_when_controls_match(monkeypatch):
    request=fixture();request['audit']['owners'][0]['starttime']=1
    refresh_controls(request);accept(monkeypatch,request)
    with pytest.raises(ValueError,match='Starttime'):
        module().validate_execution_audit(**request)


def test_pin_revocation_during_admission_refuses(monkeypatch):
    request=fixture();accept(monkeypatch,request)
    class Revoke(dict):
        def __deepcopy__(self,memo):
            monkeypatch.setattr(module().pins,'ACCEPTED_EXECUTION_AUDIT_SHA256',frozenset())
            return copy.deepcopy(dict(self),memo)
    request['control_payloads']=Revoke(request['control_payloads'])
    with pytest.raises(PermissionError):module().validate_execution_audit(**request)


def test_import_is_pure_and_real_acceptance_remains_empty():
    import os,subprocess,sys
    result=subprocess.run([sys.executable,'-B','-c',
        'import sys;import '+NAME+' as m;assert not m.pins.ACCEPTED_EXECUTION_AUDIT_SHA256;assert not set(sys.modules)&{"torch","mujoco","palimpsest.engine"}'],
        env={**os.environ,'PYTHONPATH':'src:.'},capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('field,value',[('size_bytes',True),('size_bytes',-1),('path','../escape'),('path','/absolute'),('path','a//b'),('path','a/./b'),('sha256','A'*64)])
def test_bad_descriptors_rejected(monkeypatch,field,value):
    request=fixture();request['audit']['owners'][1]['registration'][field]=value
    accept(monkeypatch,request)
    with pytest.raises(ValueError):module().validate_execution_audit(**request)


@pytest.mark.parametrize('field,value',[('pid',True),('starttime',False),('launch_ns',True),('returncode',False),('drained_ns',-1)])
def test_noninteger_or_negative_identity_clock_values_rejected(monkeypatch,field,value):
    request=fixture();request['audit']['owners'][1][field]=value
    accept(monkeypatch,request)
    with pytest.raises(ValueError):module().validate_execution_audit(**request)


def test_observer_tick_frequency_boolean_is_rejected(monkeypatch):
    request=fixture();request['audit']['observer']['ticks_per_second']=True
    accept(monkeypatch,request)
    with pytest.raises(ValueError):module().validate_execution_audit(**request)
