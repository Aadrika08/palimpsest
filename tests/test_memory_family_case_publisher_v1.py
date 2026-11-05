"""Authored prospective control fixtures; never accepted runtime qualification."""
import copy
import hashlib
import time
import uuid
from pathlib import Path
import pytest
from palimpsest import artifacts, memory
from scripts import memory_family_analysis_v3 as analysis
from scripts import memory_family_case_publication_v1 as publication
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_condition_seal_v4 as seal
from scripts import memory_family_producer_v4 as source
from scripts import memory_family_retained_case_v1 as cases
from memory_publication_authored_profiles import authored_current_profile
from test_memory_family_retained_case_v1 import build_case


def test_public_final_reader_roundtrip_requires_expected_commit(admitted):
    published=publication.publish_retained_case(**admitted)
    final=publication.read_retained_published_case(**admitted,case_commit=published['case_commit'])
    assert final==published and final is not published
    final['retained']['condition_run_ids']['own']='caller mutation'
    assert published['retained']['condition_run_ids']['own']!='caller mutation'
    with pytest.raises(TypeError):
        publication.read_retained_published_case(**admitted)


@pytest.mark.parametrize('target',['marker','close','manifest','quarantine','temporary','staged-alias'])
def test_public_final_reader_refuses_tampering_and_aliases(admitted,target):
    published=publication.publish_retained_case(**admitted)
    root=admitted['evidence_root'];case_id=admitted['case_slot']['case_id'];final=root/'cases'/case_id
    if target in ('marker','close','manifest'):
        name={'marker':'commit.json','close':'close.json','manifest':'manifest.json'}[target]
        (final/name).write_bytes((final/name).read_bytes()+b' ')
    elif target=='quarantine':(final/'quarantine.json').write_bytes(b'{}')
    elif target=='temporary':(final/'.commit.tmp').write_bytes(b'{}')
    else:(root/'.pending'/case_id).mkdir()
    with pytest.raises((ValueError,RuntimeError,OSError)):
        publication.read_retained_published_case(**admitted,case_commit=published['case_commit'])


def test_public_final_reader_revocation_precedes_protected_reads(admitted,monkeypatch):
    published=publication.publish_retained_case(**admitted)
    monkeypatch.setattr(publication.pins,'ACCEPTED_EXECUTION_AUDIT_SHA256',frozenset())
    def forbidden(*args,**kwargs):raise AssertionError('protected read after revoked execution policy')
    monkeypatch.setattr(cases,'_inventory',forbidden)
    with pytest.raises(PermissionError):
        publication.read_retained_published_case(**admitted,case_commit=published['case_commit'])


def test_public_final_reader_empty_execution_pin_precedes_protected_copy(tmp_path):
    class Protected(dict):
        def __deepcopy__(self,memo):raise AssertionError('protected mapping copied before trust')
    with pytest.raises(PermissionError):
        publication.read_retained_published_case(tmp_path/'absent',Protected(),case_slot=Protected(),
            condition_commits=Protected(),execution_audit={},case_commit=Protected(),deadline=time.monotonic()+30)
    assert not (tmp_path/'absent').exists()


@pytest.mark.parametrize('target',['cells','retained-bytes','extra-field'])
def test_public_final_reader_recomputes_rebound_candidate(admitted,target):
    published=publication.publish_retained_case(**admitted)
    root=admitted['evidence_root'];case_id=admitted['case_slot']['case_id'];base=f'cases/{case_id}/'
    final=root/'cases'/case_id
    manifest=artifacts._json((final/'manifest.json').read_bytes())
    close=artifacts._json((final/'close.json').read_bytes())
    marker=artifacts._json((final/'commit.json').read_bytes())
    if target=='cells':
        manifest['analysis_cells'][0]['path_length']+=.25
        payload=memory.canonical_bytes(manifest);(final/'manifest.json').write_bytes(payload)
        close['manifest']=marker['manifest']=source._descriptor(base+'manifest.json',payload)
    elif target=='retained-bytes':
        close['retained_bytes']+=1
    else:
        marker['unregistered']=False
    payload=memory.canonical_bytes(close);(final/'close.json').write_bytes(payload)
    marker['close']=source._descriptor(base+'close.json',payload)
    payload=memory.canonical_bytes(marker);(final/'commit.json').write_bytes(payload)
    expected=source._descriptor(base+'commit.json',payload)
    # An explicit authored candidate descriptor is no substitute for semantics.
    with pytest.raises((ValueError,RuntimeError)):
        publication.read_retained_published_case(**admitted,case_commit=expected)


@pytest.fixture(scope='module')
def prospective_case(tmp_path_factory):
    root=tmp_path_factory.mktemp('authored-prospective-order')/'evidence'
    observer=dict(source_sha256='b'*64,qualification_sha256='c'*64,
        boot_id=str(uuid.UUID(int=1)),pid_namespace='pid:[123]',clock='CLOCK_BOOTTIME',ticks_per_second=100)
    facts={}
    def control_factory(case,run_id,operation,condition,controls):
        i=0 if condition is None else 1+analysis.condition_order(case['row']).index(condition)
        start=(100+i*10)*10**9
        row=dict(case_id=case['case_id'],run_id=run_id,operation=operation,condition=condition,
            observer=observer,job=copy.deepcopy(controls['job']),pid=100+i,pgid=100+i,
            starttime=(100+i*10)*100,launch_ns=start,reaped_ns=start+10**9,
            drained_ns=start+2*10**9,returncode=0,status='completed')
        facts['source' if condition is None else condition]=row
        cleanup={k:v for k,v in row.items() if k not in ('launch_ns','reaped_ns','returncode','status')}
        return {'supervisor':dict(schema='memory-family-order-supervisor-v1',**row),
            'cleanup':dict(schema='memory-family-order-cleanup-v1',status='drained',**cleanup)}
    sample=build_case(root,control_factory=control_factory)
    return sample,observer,facts


@pytest.fixture
def admitted(tmp_path,monkeypatch,prospective_case):
    import shutil
    sample,observer,facts=copy.deepcopy(prospective_case)
    root=tmp_path/'evidence';shutil.copytree(sample['evidence_root'],root)
    sample['evidence_root']=root;(root/'cases').mkdir(exist_ok=True)
    contracts={c:artifacts._json((root/d['path']).read_bytes()) for c,d in sample['registrations'].items()}
    source_registration=contracts['own']['source']['registration']
    contracts['source']=artifacts._json((root/source_registration['path']).read_bytes())
    # Ephemeral test-owned extension. Existing profiles/real pins remain unchanged.
    path=compact.PROTOCOL_PATH.parent/'authored-publication.json'
    code_paths=['scripts/memory_family_case_publication_v1.py',
                'scripts/memory_family_case_custody_v1.py','scripts/memory_family_retained_case_v1.py']
    extension=dict(schema='memory-case-publication-v1-protocol',
        base_protocol=source._descriptor(compact.PROTOCOL_PATH.relative_to(compact.ROOT).as_posix(),compact.PROTOCOL_PATH.read_bytes()),
        condition_extension=source._descriptor(seal.EXTENSION_PATH,(compact.ROOT/seal.EXTENSION_PATH).read_bytes()),
        schemas=publication.PUBLICATION_SCHEMAS,bounds=publication.PUBLICATION_BOUNDS,
        source_pins=[source._descriptor(p,(compact.ROOT/p).read_bytes()) for p in sorted(code_paths)],
        claims=copy.deepcopy(compact.PROTOCOL['claims']))
    path.write_bytes(memory.canonical_bytes(extension))
    monkeypatch.setattr(publication,'PUBLICATION_PATH',path.relative_to(compact.ROOT).as_posix())
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    owners=[]
    for name in ['source',*analysis.condition_order(contracts['own']['case']['row'])]:
        contract=contracts[name];row=facts[name]
        owners.append(dict(operation=row['operation'],condition=row['condition'],run_id=contract['run_id'],
            registration=source_registration if name=='source' else sample['registrations'][name],
            job=contract['controls']['job'],owner=contract['owner_record'],
            supervisor=contract['controls']['supervisor'],cleanup=contract['controls']['cleanup'],
            commit=contracts['own']['source']['commit'] if name=='source' else sample['condition_commits'][name],
            **{k:row[k] for k in ('pid','starttime','pgid','launch_ns','reaped_ns','drained_ns','returncode','status')}))
    audit=dict(schema='memory-family-case-execution-audit-v1',publication_protocol_sha256=digest,
        case_slot=sample['case_slot'],source_commit=contracts['own']['source']['commit'],
        condition_commits=sample['condition_commits'],observer=observer,owners=owners,
        claims=copy.deepcopy(compact.PROTOCOL['claims']))
    policy={'ACCEPTED_EXECUTION_AUDIT_SHA256':frozenset({hashlib.sha256(memory.canonical_bytes(audit)).hexdigest()}),
        'TRUSTED_QUALIFICATION_PINS':tuple(tuple(c['qualification'][k] for k in ('path','size_bytes','sha256')) for n,c in contracts.items() if n!='source')}
    # Explicit private admission seams for authored regression only.
    monkeypatch.setattr(publication.pins,'ACCEPTED_EXECUTION_AUDIT_SHA256',policy['ACCEPTED_EXECUTION_AUDIT_SHA256'])
    monkeypatch.setattr(publication,'_read_acceptance_policy',lambda *args:copy.deepcopy(policy))
    monkeypatch.setattr(seal,'_require_qualification_pin',lambda value:None)
    return dict(**sample,execution_audit=audit,deadline=time.monotonic()+90)


def test_authored_real_writer_binding_chain_and_independent_final_semantics(admitted):
    root=admitted['evidence_root'];case_id=admitted['case_slot']['case_id']
    old_inode=(root/'.pending'/case_id).stat().st_ino
    expected=cases.read_retained_staged_case(**{k:v for k,v in admitted.items() if k!='execution_audit'})
    result=publication.publish_retained_case(**admitted)
    assert set(result)=={'case_commit','retained','order_evidence'}
    assert result['retained']==expected
    assert result['order_evidence']=='accepted-supervisor-attestation'
    final=root/'cases'/case_id
    assert final.stat().st_ino==old_inode and not (root/'.pending'/case_id).exists()
    marker=artifacts._json((final/'commit.json').read_bytes())
    close=artifacts._json((final/'close.json').read_bytes())
    files={name:source._descriptor(f'cases/{case_id}/{name}',(final/name).read_bytes())
           for name in ('manifest.json','close.json','commit.json')}
    assert marker['manifest']==close['manifest']==files['manifest.json']
    assert marker['close']==files['close.json'] and result['case_commit']==files['commit.json']
    assert close['execution_audit']==admitted['execution_audit']
    recomputed=cases._read_retained_case(**{k:v for k,v in admitted.items() if k!='execution_audit'},
                                       location='published',case_files=files)
    assert recomputed==expected


def test_all_nine_qualification_policy_pins_precede_protected_reads(admitted,monkeypatch):
    policy_reader=publication._read_acceptance_policy
    def missing(*args):
        policy=policy_reader(*args)
        policy['TRUSTED_QUALIFICATION_PINS']=policy['TRUSTED_QUALIFICATION_PINS'][:-1]
        return policy
    monkeypatch.setattr(publication,'_read_acceptance_policy',missing)
    def forbidden(*args,**kwargs):raise AssertionError('protected read before all qualification policies')
    monkeypatch.setattr(publication,'_publication_profile',forbidden)
    monkeypatch.setattr(cases,'_inventory',forbidden)
    monkeypatch.setattr(source,'_inputs',forbidden)
    with pytest.raises(PermissionError,match='qualification policy'):
        publication.publish_retained_case(**admitted)
    assert not (admitted['evidence_root']/'.pending'/admitted['case_slot']['case_id']/'manifest.json').exists()


def test_revocation_during_write_is_indeterminate_and_quarantined(admitted,monkeypatch):
    from scripts.memory_family_case_custody_v1 import _CasePublication
    original=_CasePublication._write
    def revoke(self,name,payload):
        original(self,name,payload)
        if name=='manifest.json':
            monkeypatch.setattr(publication.pins,'ACCEPTED_EXECUTION_AUDIT_SHA256',frozenset())
    monkeypatch.setattr(_CasePublication,'_write',revoke)
    with pytest.raises(publication.CasePublicationIndeterminate) as raised:
        publication.publish_retained_case(**admitted)
    assert isinstance(raised.value.__cause__,PermissionError)
    path=admitted['evidence_root']/'.pending'/admitted['case_slot']['case_id']
    assert (path/'manifest.json').exists() and (path/'quarantine.json').exists()
    assert not (path/'commit.json').exists()


def test_external_control_mutation_after_semantics_refuses_before_creation(admitted,monkeypatch):
    original=cases.read_retained_staged_case
    def mutate(*args,**kwargs):
        result=original(*args,**kwargs)
        path=admitted['evidence_root']/admitted['registrations']['own']['path']
        contract=artifacts._json(path.read_bytes())
        (admitted['evidence_root']/contract['controls']['job']['path']).write_bytes(b'changed')
        return result
    monkeypatch.setattr(cases,'read_retained_staged_case',mutate)
    with pytest.raises((ValueError,RuntimeError)):
        publication.publish_retained_case(**admitted)
    assert not (admitted['evidence_root']/'.pending'/admitted['case_slot']['case_id']/'manifest.json').exists()


def test_publication_teardown_failure_never_returns_marker_descriptor(admitted,monkeypatch):
    from scripts.memory_family_case_custody_v1 import _CasePublication
    original=_CasePublication._close
    def close_then_fail(self):
        original(self)
        raise OSError('authored final teardown fault')
    monkeypatch.setattr(_CasePublication,'_close',close_then_fail)
    with pytest.raises(publication.CasePublicationIndeterminate) as raised:
        publication.publish_retained_case(**admitted)
    assert 'authored final teardown fault' in str(raised.value.__cause__)
    final=admitted['evidence_root']/'cases'/admitted['case_slot']['case_id']
    assert (final/'commit.json').exists()  # Mere existence never records success.


def test_policy_parser_does_not_execute_expressions():
    assert publication._policy_assignment(b'"doc"\nACCEPTED = frozenset()','ACCEPTED')==frozenset()
    assert publication._policy_assignment(b'ACCEPTED = (("p", 1, "d"),)','ACCEPTED')==(('p',1,'d'),)
    with pytest.raises((ValueError,TypeError)):
        publication._policy_assignment(b'ACCEPTED = __import__("os").system("false")','ACCEPTED')
