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




def test_unpatched_historical_profile_rejects_changed_behavior():
    import os,subprocess,sys
    code=('from scripts import memory_family_compact_v4 as c;'
          'from palimpsest import artifacts;'
          'c.PROTOCOL=artifacts._json((c.ROOT/"docs/plans/memory-family-compact-evidence-v4-retained-condition-v1-protocol.json").read_bytes());'
          'c.behavior_source_identities(c.ROOT)')
    result=subprocess.run([sys.executable,'-B','-c',code],env={**os.environ,'PYTHONPATH':'src:.'},
                          capture_output=True,text=True,timeout=30)
    assert result.returncode!=0
    assert 'Behavior source differs:' in result.stderr

from memory_publication_authored_profiles import _install_authored_profile, _authored_current_profile


@pytest.fixture(scope='module')
def published_template(tmp_path_factory, request):
    import os,time
    from scripts import memory_family_retained_case_v1 as cases
    from scripts import memory_family_condition_seal_v4 as seal
    from test_memory_family_retained_case_v1 import build_case
    patch=pytest.MonkeyPatch();request.addfinalizer(patch.undo)
    tmp_path=tmp_path_factory.mktemp('published-case-template')
    _authored_current_profile(tmp_path,patch,request)
    root=tmp_path/'evidence'; sample=build_case(root)
    patch.setattr(seal,'_require_qualification_pin',lambda value:None)
    expected=cases.read_retained_staged_case(**sample,deadline=time.monotonic()+90)
    staged=root/'.pending'/sample['case_slot']['case_id']
    final=root/'cases'/sample['case_slot']['case_id']; final.parent.mkdir(exist_ok=True)
    staged.rename(final)
    files={}
    for name in ('manifest.json','close.json','commit.json'):
        payload=memory.canonical_bytes({'authored':'semantic-core-only','name':name})
        (final/name).write_bytes(payload)
        files[name]=descriptor(f'cases/{sample["case_slot"]["case_id"]}/{name}',payload)
    return sample,files,expected


@pytest.fixture
def published_case(published_template,tmp_path):
    import shutil
    sample,files,expected=copy.deepcopy(published_template)
    root=tmp_path/'evidence'
    shutil.copytree(sample['evidence_root'],root)
    sample['evidence_root']=root
    return sample,files,expected


def test_private_published_case_core_matches_staged_and_old_route_rejects(published_case,monkeypatch):
    import os,time
    from scripts import memory_family_retained_case_v1 as cases
    sample,files,expected=published_case
    from test_memory_family_retained_case_v1 import forbid_replay
    forbid_replay(monkeypatch)
    before=len(os.listdir('/proc/self/fd'))
    actual=cases._read_retained_case(**sample,location='published',case_files=files,deadline=time.monotonic()+90)
    assert actual==expected
    assert len(os.listdir('/proc/self/fd'))==before
    with pytest.raises((ValueError,FileNotFoundError)):
        cases.read_retained_staged_case(**sample,deadline=time.monotonic()+90)


@pytest.mark.parametrize('defect',['empty-raw','raw','extra-file','staged-alias','symlink','hardlink','history','source-substitution','condition-substitution','deadline','wrong-case-files'])
def test_published_core_rejects_invalid_namespace_or_binding(published_case,defect):
    import os,time
    from scripts import memory_family_retained_case_v1 as cases
    sample,files,_=published_case
    root=sample['evidence_root']; case_id=sample['case_slot']['case_id']; final=root/'cases'/case_id
    if defect in ('empty-raw','raw'):
        (final/'.raw').mkdir()
        if defect=='raw':(final/'.raw'/'unadmitted').write_bytes(b'bad')
    elif defect=='extra-file':(final/'unexpected').write_bytes(b'bad')
    elif defect=='staged-alias':(root/'.pending'/case_id).symlink_to(final,target_is_directory=True)
    elif defect=='symlink':
        leaf=final/'source/owner.json'; payload=leaf.read_bytes();leaf.unlink();target=root/'wrong-owner';target.write_bytes(payload);leaf.symlink_to(target)
    elif defect=='hardlink':os.link(final/'source/owner.json',root/'owner-alias')
    elif defect=='history':
        import json
        c=json.loads((root/sample['registrations']['own']['path']).read_bytes())
        (root/c['history_bundles']['own']['path']).write_bytes(b'changed')
    elif defect=='source-substitution':sample['case_slot']['source_run_id']='0'*32
    elif defect=='condition-substitution':sample['condition_commits']['own']['sha256']='0'*64
    elif defect=='wrong-case-files':files['close.json']['path']='cases/different/close.json'
    deadline=time.monotonic()-1 if defect=='deadline' else time.monotonic()+90
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError,RuntimeError,OSError,TimeoutError)):
        cases._read_retained_case(**sample,location='published',case_files=files,deadline=deadline)
    assert len(os.listdir('/proc/self/fd'))==before


def test_published_core_empty_qualification_refuses_before_protected_case_reads(published_case,monkeypatch):
    import time
    from scripts import memory_family_retained_case_v1 as cases
    from scripts import memory_family_condition_seal_v4 as seal
    from scripts.memory_condition_replay_admission_v1 import require_qualification_pin
    sample,files,_=published_case
    monkeypatch.setattr(seal,'_require_qualification_pin',require_qualification_pin)
    def forbidden(*args,**kwargs):raise AssertionError('protected case read before qualification')
    monkeypatch.setattr(cases,'_inventory',forbidden)
    with pytest.raises(PermissionError):
        cases._read_retained_case(**sample,location='published',case_files=files,deadline=time.monotonic()+90)


def test_published_core_preserves_late_primary_error_and_closes_fds(published_case,monkeypatch):
    import os,time
    from scripts import memory_family_retained_case_v1 as cases
    sample,files,_=published_case
    original=cases._cell
    def failed(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('authored late primary failure')
    monkeypatch.setattr(cases,'_cell',failed)
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(RuntimeError,match='authored late primary failure'):
        cases._read_retained_case(**sample,location='published',case_files=files,deadline=time.monotonic()+90)
    assert len(os.listdir('/proc/self/fd'))==before


def test_historical_profile_bytes_remain_unchanged():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    payload=(root/'docs/plans/memory-family-compact-evidence-v4-retained-condition-v1-protocol.json').read_bytes()
    assert hashlib.sha256(payload).hexdigest()=='e71fc7ea6185f7de769b9879d4b581458074b925255b4712f0f6578fb0556261'
