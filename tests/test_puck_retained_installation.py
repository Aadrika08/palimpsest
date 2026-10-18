"""Authored bytes only: exact custody of an installed tree, including empty dirs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import pytest


def module():
    name = 'palimpsest.puck_retained_installation'
    assert importlib.util.find_spec(name), 'retained installation custody is missing'
    return __import__(name,fromlist=['HeldInstalledFiles'])


def row(path,data):
    return dict(path=path,size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def authored(tmp_path):
    root=tmp_path/'site';root.mkdir();(root/'pkg').mkdir();(root/'empty').mkdir()
    data=b"raise RuntimeError('must never import')\n";(root/'pkg/__init__.py').write_bytes(data)
    return root,[row('pkg/__init__.py',data)],['empty','pkg']


def test_exact_empty_directory_custody_rechecks_without_execution(tmp_path):
    root,rows,dirs=authored(tmp_path);m=module();before=len(os.listdir('/proc/self/fd'))
    with m.HeldInstalledFiles(root,rows,dirs,time.monotonic()+10) as held:
        held.recheck();held.recheck()
        assert not hasattr(held,'fd_path')
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('change',['bytes','extra','missing','rename-empty','symlink','hardlink'])
def test_current_namespace_changes_refuse_and_close(tmp_path,change):
    root,rows,dirs=authored(tmp_path);m=module();before=len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError,RuntimeError,OSError)):
        with m.HeldInstalledFiles(root,rows,dirs,time.monotonic()+10) as held:
            if change=='bytes':(root/'pkg/__init__.py').write_bytes(b'changed')
            elif change=='extra':(root/'empty/new').write_bytes(b'extra')
            elif change=='missing':(root/'pkg/__init__.py').unlink()
            elif change=='rename-empty':(root/'empty').rename(root/'renamed')
            elif change=='symlink':(root/'empty/link').symlink_to(root/'pkg/__init__.py')
            else:os.link(root/'pkg/__init__.py',root/'empty/alias')
            held.recheck()
    assert len(os.listdir('/proc/self/fd'))==before


def test_large_json_is_pinned_and_small_global_read_limit_stays(tmp_path):
    m=module();data=json.dumps({'payload':'x'*(4*1024**2)}).encode();p=tmp_path/'large.json';p.write_bytes(data)
    with m.AdmissionInputs(tmp_path,[row('large.json',data)],time.monotonic()+10) as held:
        assert len(held.read_json('large.json')['payload'])==4*1024**2
        with pytest.raises(ValueError,match='four MiB'):held.read('large.json',8*1024**2)


@pytest.mark.parametrize('data',[b'{"x":1,"x":2}',b'{"x":NaN}',b'['*33+b'0'+b']'*33])
def test_control_json_rejects_duplicate_nonfinite_or_deep(data,tmp_path):
    m=module();(tmp_path/'bad.json').write_bytes(data)
    with m.AdmissionInputs(tmp_path,[row('bad.json',data)],time.monotonic()+10) as held:
        with pytest.raises(ValueError):held.read_json('bad.json')


def test_data_only_pyc_is_exact_and_cannot_become_an_extra_module(tmp_path):
    m=module();good=row(m.INERT_PYC_PATH,b'authored-bytecode-data')
    assert m.validate_inert_files([good],good)==good
    with pytest.raises(ValueError):m.validate_inert_files([dict(good,sha256='0'*64)],good)
    with pytest.raises(ValueError):m.validate_inert_files([good,row('other.pyc',b'x')],good)
    with pytest.raises(ValueError):m.validate_inert_files([good,row('hook.pth',b'x')],good)


def test_file_and_time_limits_fail_without_leaking(tmp_path):
    root,rows,dirs=authored(tmp_path);m=module();before=len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError,TimeoutError)):
        with m.HeldInstalledFiles(root,rows,dirs,time.monotonic()-1):pass
    with pytest.raises(ValueError):m.HeldInstalledFiles(root,[dict(rows[0],size_bytes=1024**3+1)],dirs,time.monotonic()+10)
    assert len(os.listdir('/proc/self/fd'))==before


def driver():
    p=Path(__file__).resolve().parents[1]/'scripts/admit_puck_retained_installation.py'
    assert p.exists(),'retained admission entry is missing'
    spec=importlib.util.spec_from_file_location('retained_driver',p)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def test_completion_refuses_live_thread_or_leaked_descriptor(tmp_path):
    import threading
    m=driver();before=len(os.listdir('/proc/self/fd'))
    stop=threading.Event();worker=threading.Thread(target=stop.wait);worker.start()
    try:
        with pytest.raises(ValueError,match='thread'):m.completion_state(before)
    finally:stop.set();worker.join()
    fd=os.open(tmp_path,os.O_RDONLY|os.O_DIRECTORY)
    try:
        with pytest.raises(ValueError,match='descriptor'):m.completion_state(before)
    finally:os.close(fd)
    assert m.completion_state(before)['all_handles_closed'] is True


def test_fd_headroom_rejects_real_small_process_limit(tmp_path):
    import subprocess
    m=driver()
    code=f"""import importlib.util,resource
s=importlib.util.spec_from_file_location('m',{str(Path(m.__file__))!r})
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
try:m.require_fd_budget(100)
except ValueError:pass
else:raise AssertionError('insufficient descriptor budget accepted')
assert resource.getrlimit(resource.RLIMIT_NOFILE)==(32,32)
"""
    p=subprocess.run([m.PYTHON,'-I','-S','-B','-c',code],capture_output=True,text=True)
    assert p.returncode==0,p.stderr


def test_unrelated_sibling_membership_does_not_change_admitted_tree(tmp_path):
    root,rows,dirs=authored(tmp_path);m=module()
    with m.HeldInstalledFiles(root,rows,dirs,time.monotonic()+10) as held:
        (tmp_path/'unrelated-sibling').write_bytes(b'outside admitted tree')
        held.recheck()
    with m.AdmissionInputs(root,rows,time.monotonic()+10) as held:
        (tmp_path/'another-unrelated-sibling').write_bytes(b'outside declared metadata files')
        held.recheck()


def test_redirected_ancestor_is_rejected_despite_same_leaf_bytes(tmp_path):
    m=module();outer=tmp_path/'outer';outer.mkdir();root=outer/'site';root.mkdir()
    (root/'value').write_bytes(b'unchanged');rows=[row('value',b'unchanged')]
    with pytest.raises((ValueError,RuntimeError,OSError)):
        with m.HeldInstalledFiles(root,rows,[],time.monotonic()+10) as held:
            outer.rename(tmp_path/'saved');root.mkdir(parents=True);(root/'value').write_bytes(b'unchanged')
            held.recheck()


def test_public_collection_ancestor_policy_is_unchanged(tmp_path):
    from palimpsest.puck_execution_files import HeldCollectionFiles
    root,rows,dirs=authored(tmp_path)
    with pytest.raises(RuntimeError):
        with HeldCollectionFiles(root,rows,time.monotonic()+10) as held:
            (tmp_path/'outside-sibling').write_bytes(b'still rejected by public profile')
            held.recheck()


@pytest.mark.parametrize('change',['pass','accepted','missing-authority'])
def test_prior_admission_failure_cannot_be_promoted(change):
    m=driver();prior=dict(kind='cpu-retained-installation-admission-result-v1',status='FAIL',claims=dict(m.CLAIMS))
    m.require_prior_failure(prior)
    if change=='pass':prior['status']='PASS'
    elif change=='accepted':prior['claims']['package_preparation_accepted']=True
    else:del prior['claims']['study_authorized']
    with pytest.raises(ValueError,match='Prior admission'):m.require_prior_failure(prior)
