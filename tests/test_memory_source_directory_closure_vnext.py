import hashlib
import os
import time
import pytest
from scripts.memory_source_parent_entry_vnext import _HeldDirectoryClosure, _SourcePathRegistry, _DIRECTORY_TOKEN, _REGISTRY_TOKEN


def registry(): return _SourcePathRegistry(_REGISTRY_TOKEN,time.monotonic_ns()+30_000_000_000)


def test_exact_tree_including_empty_and_registered_children(tmp_path):
    tree=tmp_path/'tree'; tree.mkdir(); (tree/'empty').mkdir(); (tree/'leaf').write_bytes(b'x')
    reg=registry(); desc=dict(path=str(tree/'leaf'),size_bytes=1,sha256=hashlib.sha256(b'x').hexdigest())
    with _HeldDirectoryClosure(_DIRECTORY_TOKEN,trees=(dict(root=str(tree),directories=['empty'],files=[desc]),),
            ancestor_targets=(str(tree),),deadline_ns=time.monotonic_ns()+30_000_000_000,registry=reg) as held:
        assert held.require_children(str(tree)) == (('empty','directory'),('leaf','file'))
        held.recheck()
        (tree/'empty'/'extra').write_bytes(b'extra')
        with pytest.raises((ValueError,RuntimeError)): held.recheck()
    assert held._fds==[]


def test_registry_real_batches_and_descriptor_reuse(tmp_path):
    from scripts.memory_family_replay_custody_v4 import HeldReplayFiles
    leaf=tmp_path/'leaf'; leaf.write_bytes(b'x'); desc=dict(path=str(leaf),size_bytes=1,sha256=hashlib.sha256(b'x').hexdigest())
    reg=registry()
    assert reg.claim(desc,'fixture')=='new'
    assert reg.claim(desc,'repeat')=='reuse'
    with pytest.raises(ValueError): reg.claim(dict(desc,sha256='0'*64),'conflict')
    with HeldReplayFiles('/',[dict(desc,path=desc['path'][1:])],time.monotonic()+30,structured_teardown=True) as holder:
        reg.register_batch(holder); reg.recheck(); assert reg.binding(str(leaf)).descriptor==desc
        reg.invalidate()
    with pytest.raises(RuntimeError): reg.recheck()


@pytest.mark.parametrize('defect',['symlink','extra','missing-empty','hardlink','directory-alias'])
def test_directory_refuses_unclosed_or_alias_inputs(tmp_path,defect):
    tree=tmp_path/'tree'; tree.mkdir(); (tree/'empty').mkdir(); leaf=tree/'leaf'; leaf.write_bytes(b'x')
    desc=dict(path=str(leaf),size_bytes=1,sha256=hashlib.sha256(b'x').hexdigest())
    if defect=='symlink': (tree/'link').symlink_to(leaf)
    elif defect=='extra': (tree/'extra').write_bytes(b'x')
    elif defect=='missing-empty': (tree/'empty').rename(tree/'renamed')
    elif defect=='hardlink': os.link(leaf,tree/'alias')
    else: (tree/'alias').symlink_to(tree/'empty',target_is_directory=True)
    held=_HeldDirectoryClosure(_DIRECTORY_TOKEN,trees=(dict(root=str(tree),directories=['empty'],files=[desc]),),ancestor_targets=(),deadline_ns=time.monotonic_ns()+10_000_000_000,registry=registry())
    with pytest.raises((ValueError,RuntimeError,OSError)): held.__enter__()
    assert held._fds==[]


def test_directory_cross_thread_and_second_enter_refuse(tmp_path):
    import threading
    tree=tmp_path/'tree'; tree.mkdir(); held=_HeldDirectoryClosure(_DIRECTORY_TOKEN,trees=(dict(root=str(tree),directories=[],files=[]),),ancestor_targets=(),deadline_ns=time.monotonic_ns()+10_000_000_000,registry=registry())
    caught=[]
    with held:
        def read():
            try: held.require_children(str(tree))
            except BaseException as error: caught.append(error)
        thread=threading.Thread(target=read); thread.start(); thread.join()
        assert len(caught)==1 and isinstance(caught[0],RuntimeError)
        with pytest.raises(RuntimeError): held.__enter__()
    with pytest.raises(RuntimeError): held.recheck()


def test_real_batch_bounds_are_deterministic_without_payload_allocation():
    from scripts.memory_source_parent_entry_vnext import _batches
    mib=1024**2
    descriptor=lambda index,size:dict(path=f'/authored/{index:06}',size_bytes=size,sha256='1'*64)
    batches=list(_batches([descriptor(index,1024*mib) for index in range(3)]))
    assert [len(batch) for batch in batches]==[2,1]
    batches=list(_batches([descriptor(index,0) for index in range(513)]))
    assert [len(batch) for batch in batches]==[512,1]
    with pytest.raises(ValueError): list(_batches([descriptor(0,1024*mib+1)]))
