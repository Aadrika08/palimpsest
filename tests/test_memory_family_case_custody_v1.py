"""Private publication capability on tiny authored trees; no execution authority."""
import hashlib
import importlib
import os
from pathlib import Path
import time
import errno
import tempfile
import pytest
from palimpsest import memory

NAME='scripts.memory_family_case_custody_v1'


def module(): return importlib.import_module(NAME)


def fixture(root):
    case='authored-case';base=root/'.pending'/case
    (root/'cases').mkdir(parents=True)
    files=['source/snapshots/initial.snp','source/recording/chunks/000000.npz']
    for condition in ('own','swapped','sham','no-U','hand-authored','history-independent','traversal','retrieval','oracle'):
        files.append(f'conditions/{condition}/recording/chunks/000000.npz')
    entries=[]
    for i,name in enumerate(files):
        p=base/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(bytes([i]))
        entries.append({'path':p.relative_to(root).as_posix(),'size_bytes':1,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    payloads={name:memory.canonical_bytes({'authored':True,'name':name}) for name in ('manifest.json','close.json','commit.json')}
    return case,sorted(entries,key=lambda d:d['path']),payloads


def test_real_move_retains_inodes_and_exact_three_new_files(tmp_path):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root)
    before={d['path']:((root/d['path']).stat().st_ino,(root/d['path']).read_bytes()) for d in entries}
    case_inode=(root/'.pending'/case).stat().st_ino
    handles=len(os.listdir('/proc/self/fd'))
    with module()._CasePublication(root,case,entries,time.monotonic()+30) as held:
        held.write_case_files(payloads)
        held.publish()
        held.recheck()
    assert len(os.listdir('/proc/self/fd'))==handles
    assert not (root/'.pending'/case).exists()
    final=root/'cases'/case
    assert final.stat().st_ino==case_inode
    assert set(os.listdir(final))=={'source','conditions',*payloads}
    for path,(inode,payload) in before.items():
        p=root/('cases/'+path[len('.pending/'):]);assert p.stat().st_ino==inode and p.read_bytes()==payload
    for name,payload in payloads.items():assert (final/name).read_bytes()==payload


def test_collision_is_not_replaced(tmp_path):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root)
    destination=root/'cases'/case;destination.mkdir();(destination/'competitor').write_bytes(b'keep')
    with pytest.raises((ValueError,FileExistsError)):
        with module()._CasePublication(root,case,entries,time.monotonic()+30):pass
    assert (destination/'competitor').read_bytes()==b'keep'
    assert not (root/'.pending'/case/'manifest.json').exists()


def test_retained_mutation_refuses_before_output_creation(tmp_path):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root)
    with pytest.raises((ValueError,RuntimeError)):
        with module()._CasePublication(root,case,entries,time.monotonic()+30) as held:
            (root/entries[0]['path']).write_bytes(b'x')
            held.write_case_files(payloads)
    assert not (root/'.pending'/case/'manifest.json').exists()


@pytest.mark.parametrize('fault',['write','short-write','file-fsync','marker-rename','case-rename','source-parent-fsync','destination-parent-fsync'])
def test_mutating_failures_are_indeterminate_and_close_descriptors(tmp_path,monkeypatch,fault):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    handles=len(os.listdir('/proc/self/fd'))
    def fail(*args,**kwargs):raise OSError('authored publication fault')
    if fault in ('write','short-write','file-fsync'):
        name='fsync' if fault=='file-fsync' else 'write';original=getattr(m.os,name);calls=[]
        def once(*args,**kwargs):
            if not calls:
                calls.append(True)
                if fault=='short-write':return 0
                fail()
            return original(*args,**kwargs)
        monkeypatch.setattr(m.os,name,once)
    elif fault=='marker-rename':monkeypatch.setattr(m.source,'_rename_noreplace',fail)
    elif fault=='case-rename':monkeypatch.setattr(m,'_rename_case_noreplace',fail)
    else:
        which='source' if fault=='source-parent-fsync' else 'destination';original=m._CasePublication._fsync_parent
        def fsync_parent(self,name):
            if name==which:fail()
            return original(self,name)
        monkeypatch.setattr(m._CasePublication,'_fsync_parent',fsync_parent)
    with pytest.raises(m.CasePublicationIndeterminate) as caught:
        with m._CasePublication(root,case,entries,time.monotonic()+30) as held:
            held.write_case_files(payloads);held.publish()
    assert caught.value.__cause__ is not None
    assert len(os.listdir('/proc/self/fd'))==handles
    path=(root/'cases'/case) if (root/'cases'/case).exists() else root/'.pending'/case
    assert (path/'quarantine.json').exists()


def test_both_parent_fsyncs_precede_success_and_real_collision_race_survives(tmp_path,monkeypatch):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module();calls=[]
    original=m._CasePublication._fsync_parent
    def fsync_parent(self,name):calls.append(name);return original(self,name)
    monkeypatch.setattr(m._CasePublication,'_fsync_parent',fsync_parent)
    with m._CasePublication(root,case,entries,time.monotonic()+30) as held:
        held.write_case_files(payloads);held.publish()
        assert calls==['source','destination']
    other=tmp_path/'race';case,entries,payloads=fixture(other);rename=m._rename_case_noreplace
    def collide(old,name,new):
        target=other/'cases'/case;target.mkdir();(target/'competitor').write_bytes(b'keep')
        return rename(old,name,new)
    monkeypatch.setattr(m,'_rename_case_noreplace',collide)
    with pytest.raises(m.CasePublicationIndeterminate):
        with m._CasePublication(other,case,entries,time.monotonic()+30) as held:
            held.write_case_files(payloads);held.publish()
    assert (other/'cases'/case/'competitor').read_bytes()==b'keep'
    assert (other/'.pending'/case/'quarantine.json').exists()


@pytest.mark.parametrize('fault',['retained-file','retained-directory','ancestor','deadline'])
def test_hostile_changes_between_transitions_never_publish(tmp_path,fault):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    with pytest.raises(m.CasePublicationIndeterminate):
        with m._CasePublication(root,case,entries,time.monotonic()+30) as held:
            held.write_case_files(payloads)
            if fault=='retained-file':(root/entries[0]['path']).write_bytes(b'wrong')
            elif fault=='retained-directory':
                p=root/'.pending'/case/'source/recording';p.rename(p.with_name('replaced'));p.mkdir()
            elif fault=='ancestor':(root/'.pending'/'unexpected-sibling').mkdir()
            else:held._held._deadline_value=time.monotonic()-1
            held.publish()
    assert not (root/'cases'/case).exists()


def test_short_writes_are_completed_and_payloads_rejected_before_creation(tmp_path,monkeypatch):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module();write=m.os.write
    monkeypatch.setattr(m.os,'write',lambda fd,data:write(fd,data[:1]))
    with m._CasePublication(root,case,entries,time.monotonic()+30) as held:
        held.write_case_files(payloads);held.publish()
    assert (root/'cases'/case/'commit.json').read_bytes()==payloads['commit.json']
    other=tmp_path/'invalid';case,entries,payloads=fixture(other)
    payloads['manifest.json']=b'{"not canonical": 1}'
    with pytest.raises(ValueError):
        with m._CasePublication(other,case,entries,time.monotonic()+30) as held:held.write_case_files(payloads)
    assert not (other/'.pending'/case/'manifest.json').exists()


def test_one_shot_capability_and_readonly_custody_still_rejects_mutation(tmp_path):
    from scripts.memory_family_replay_custody_v4 import HeldReplayFiles
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    held=m._CasePublication(root,case,entries,time.monotonic()+30)
    with held:held.write_case_files(payloads);held.publish()
    with pytest.raises(RuntimeError):held.publish()
    with pytest.raises(RuntimeError):held.__enter__()
    other=tmp_path/'readonly';case,entries,payloads=fixture(other)
    with pytest.raises((RuntimeError,ValueError)):
        with HeldReplayFiles(other,entries,time.monotonic()+30,exact_subtrees=(f'.pending/{case}',)):
            (other/'.pending'/case/'manifest.json').write_bytes(b'forbidden')


@pytest.mark.parametrize('fault',['dependency','quarantine','close'])
def test_dependency_and_cleanup_failures_preserve_primary_and_no_success(tmp_path,monkeypatch,fault):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    dep=tmp_path/'external';dep.mkdir();leaf=dep/'receipt';leaf.write_bytes(b'old')
    row={'path':'receipt','size_bytes':3,'sha256':hashlib.sha256(b'old').hexdigest()}
    before=len(os.listdir('/proc/self/fd'))
    capability=m._CasePublication(root,case,entries,time.monotonic()+30,
        dependencies=[{'root':str(dep),'entries':[row]}])
    if fault=='close':
        original=capability._close
        def close_then_fail():
            original();raise OSError('authored descriptor teardown')
        monkeypatch.setattr(capability,'_close',close_then_fail)
    elif fault=='quarantine':
        def fail(*args):raise OSError('authored quarantine failure')
        monkeypatch.setattr(capability,'_quarantine',fail)
    with pytest.raises(m.CasePublicationIndeterminate) as raised:
        with capability:
            capability.write_case_files(payloads)
            if fault=='dependency':leaf.write_bytes(b'new')
            if fault=='quarantine':raise RuntimeError('authored primary failure')
            capability.publish()
    if fault=='quarantine':
        assert str(raised.value.__cause__)=='authored primary failure'
        assert any('Quarantine durability indeterminate' in n for n in raised.value.__cause__.__notes__)
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('extra',[0,1])
def test_exact_32mib_payload_boundary(tmp_path,extra):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    other=sum(len(v) for k,v in payloads.items() if k!='manifest.json')
    # Canonical JSON string adds exactly two quote bytes.
    payloads['manifest.json']=memory.canonical_bytes('x'*(32*m.MiB-other-2+extra))
    assert sum(map(len,payloads.values()))==32*m.MiB+extra
    if extra:
        with pytest.raises(ValueError,match='allowance'):
            with m._CasePublication(root,case,entries,time.monotonic()+30) as held:
                held.write_case_files(payloads)
        assert not (root/'.pending'/case/'manifest.json').exists()
    else:
        with m._CasePublication(root,case,entries,time.monotonic()+30) as held:
            held.write_case_files(payloads);held.publish()
        assert (root/'cases'/case/'manifest.json').stat().st_size==len(payloads['manifest.json'])


def test_dependency_teardown_failure_quarantines_while_case_fd_is_held(tmp_path,monkeypatch):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    dep=tmp_path/'external';dep.mkdir();(dep/'receipt').write_bytes(b'x')
    row={'path':'receipt','size_bytes':1,'sha256':hashlib.sha256(b'x').hexdigest()}
    original=m.custody.HeldReplayFiles.__exit__
    def exit_then_fail(self,*args):
        result=original(self,*args)
        if self.root==dep:raise OSError('authored dependency teardown fault')
        return result
    monkeypatch.setattr(m.custody.HeldReplayFiles,'__exit__',exit_then_fail)
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(m.CasePublicationIndeterminate):
        with m._CasePublication(root,case,entries,time.monotonic()+30,
            dependencies=[{'root':str(dep),'entries':[row]}]) as held:
            held.write_case_files(payloads);held.publish()
    assert (root/'cases'/case/'quarantine.json').exists()
    assert len(os.listdir('/proc/self/fd'))==before


def test_retained_mutation_during_dependency_teardown_never_returns_success(tmp_path,monkeypatch):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    dep=tmp_path/'external';dep.mkdir();(dep/'receipt').write_bytes(b'x')
    row={'path':'receipt','size_bytes':1,'sha256':hashlib.sha256(b'x').hexdigest()}
    original=m.custody.HeldReplayFiles.__exit__
    def exit_and_mutate_case(self,*args):
        result=original(self,*args)
        if self.root==dep:
            relative=entries[0]['path'][len(f'.pending/{case}/'):]
            (root/'cases'/case/relative).write_bytes(b'mutated during teardown')
        return result
    monkeypatch.setattr(m.custody.HeldReplayFiles,'__exit__',exit_and_mutate_case)
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(m.CasePublicationIndeterminate):
        with m._CasePublication(root,case,entries,time.monotonic()+30,
            dependencies=[{'root':str(dep),'entries':[row]}]) as held:
            held.write_case_files(payloads);held.publish()
    assert (root/'cases'/case/'quarantine.json').exists()
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('count',[418,419])
def test_exact_retained_entry_boundary_including_short_cases(tmp_path,count):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    for i in range(count-len(entries)):
        path=f'.pending/{case}/source/recording/chunks/extra-{i:04d}'
        (root/path).write_bytes(b'x')
        entries.append({'path':path,'size_bytes':1,'sha256':hashlib.sha256(b'x').hexdigest()})
    entries.sort(key=lambda row:row['path'])
    if count==419:
        with pytest.raises(ValueError,match='retained-file bound'):
            m._CasePublication(root,case,entries,time.monotonic()+30)
        assert not (root/'.pending'/case/'manifest.json').exists()
    else:
        with m._CasePublication(root,case,entries,time.monotonic()+30) as held:
            held.write_case_files(payloads);held.publish()
        final=root/'cases'/case
        assert len(list(final.rglob('*')))+1==454


@pytest.mark.parametrize('parent',['.pending','cases'])
def test_missing_parent_is_not_created_and_descriptors_do_not_leak(tmp_path,parent):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    (root/parent).rename(root/(parent+'-saved'))
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError,OSError)):
        with m._CasePublication(root,case,entries,time.monotonic()+30):
            pytest.fail('A missing durable parent cannot be admitted')
    assert not (root/parent).exists()
    assert len(os.listdir('/proc/self/fd'))==before


def test_real_cross_device_rename_has_no_copy_or_replace_fallback(tmp_path):
    m=module();repo=Path(__file__).resolve().parents[1]
    if os.stat(tmp_path).st_dev==os.stat('/dev/shm').st_dev:
        peer=Path(tempfile.mkdtemp(prefix='case-cross-device-',dir=repo/'.pytest_cache'))
    else:
        peer=Path(tempfile.mkdtemp(prefix='palimpsest-case-cross-device-',dir='/dev/shm'))
    assert os.stat(tmp_path).st_dev!=os.stat(peer).st_dev
    source=tmp_path/'from';destination=peer/'to';source.mkdir();destination.mkdir()
    (source/'case').mkdir();(source/'case'/'original').write_bytes(b'keep')
    old=os.open(source,os.O_RDONLY|os.O_DIRECTORY)
    new=os.open(destination,os.O_RDONLY|os.O_DIRECTORY)
    try:
        with pytest.raises(OSError) as raised:m._rename_case_noreplace(old,'case',new)
        assert raised.value.errno==errno.EXDEV
        assert (source/'case'/'original').read_bytes()==b'keep'
        assert not (destination/'case').exists()
    finally:
        os.close(old);os.close(new)


def test_observed_cross_device_parents_refuse_before_creation(tmp_path,monkeypatch):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    capability=m._CasePublication(root,case,entries,time.monotonic()+30)
    observed={};directory=m.custody.HeldReplayFiles._directory;fstat=m.os.fstat
    def capture(self,parts):
        fd=directory(self,parts)
        if parts==capability._cases_key:observed['fd']=fd
        return fd
    class OtherDevice:
        def __init__(self,actual):self.actual=actual;self.st_dev=actual.st_dev+1
        def __getattr__(self,name):return getattr(self.actual,name)
    def device(fd):
        actual=fstat(fd)
        return OtherDevice(actual) if fd==observed.get('fd') else actual
    monkeypatch.setattr(m.custody.HeldReplayFiles,'_directory',capture)
    monkeypatch.setattr(m.os,'fstat',device)
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(ValueError,match='one filesystem'):
        with capability:pytest.fail('Cross-device parents cannot be admitted')
    assert not (root/'.pending'/case/'manifest.json').exists()
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('phase',['manifest.json','close.json','.commit.tmp','marker-rename',
    'case-rename','source-fsync','destination-fsync'])
@pytest.mark.parametrize('defect',['retained-file','retained-directory'])
def test_hostile_retained_mutation_at_each_publication_transition(tmp_path,monkeypatch,phase,defect):
    root=tmp_path/'evidence';case,entries,payloads=fixture(root);m=module()
    def mutate():
        base=(root/'.pending'/case) if (root/'.pending'/case).exists() else root/'cases'/case
        relative=entries[0]['path'][len(f'.pending/{case}/'):]
        target=base/relative
        if defect=='retained-file':target.write_bytes(b'hostile bytes')
        else:
            parent=target.parent;parent.rename(parent.with_name(parent.name+'-replaced'));parent.mkdir()
    if phase in ('manifest.json','close.json','.commit.tmp'):
        original=m._CasePublication._write
        def after_write(self,name,payload):
            result=original(self,name,payload)
            if name==phase:mutate()
            return result
        monkeypatch.setattr(m._CasePublication,'_write',after_write)
    elif phase in ('marker-rename','case-rename'):
        target=m.source if phase=='marker-rename' else m
        name='_rename_noreplace' if phase=='marker-rename' else '_rename_case_noreplace'
        original=getattr(target,name)
        def after_rename(*args):
            result=original(*args);mutate();return result
        monkeypatch.setattr(target,name,after_rename)
    else:
        original=m._CasePublication._fsync_parent
        def after_fsync(self,name):
            result=original(self,name)
            if phase==name+'-fsync':mutate()
            return result
        monkeypatch.setattr(m._CasePublication,'_fsync_parent',after_fsync)
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(m.CasePublicationIndeterminate):
        with m._CasePublication(root,case,entries,time.monotonic()+30) as held:
            held.write_case_files(payloads);held.publish()
    final=(root/'cases'/case) if (root/'cases'/case).exists() else root/'.pending'/case
    assert (final/'quarantine.json').exists()
    assert len(os.listdir('/proc/self/fd'))==before
