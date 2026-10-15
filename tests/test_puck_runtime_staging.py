"""Data-only tmpfs copies of tiny authored dependency forests."""
from contextlib import contextmanager
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import time

import pytest

NAME='palimpsest.puck_runtime_staging'


def api():
    assert importlib.util.find_spec(NAME) is not None,'Tmpfs runtime staging helper missing'
    return importlib.import_module(NAME)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def descriptor(path,relative):
    raw=path.read_bytes()
    return dict(path=relative,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def forest(base,version=2):
    root=base/'source';root.mkdir()
    payloads={'demo/__init__.py':b'raise AssertionError("must stay inert")\n',
              'demo/__pycache__/inert.pyc':b'not executable bytecode',
              'demo-1.dist-info/METADATA':b'Metadata-Version: 2.1\nName: demo\nVersion: 1\n\n'}
    for relative,raw in payloads.items():
        path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    (root/'empty/nested').mkdir(parents=True)
    reg=dict(kind='puck-worker-dependencies-v'+str(version),version=version,
        roots=[dict(root=str(root),kind='package',files=[descriptor(root/p,p) for p in sorted(payloads)])],
        modules=[dict(name='demo',root_index=0,path='demo/__init__.py',kind='python',is_package=True)],
        namespaces=[],distributions=[dict(name='demo',version='1',root_index=0,metadata_path='demo-1.dist-info/METADATA')],
        import_profile=dict(exports=[],module_changes=[],native_origins=[]))
    if version==3:reg['native_identity']='tmpfs-raw-dev-inode-v1'
    return root,reg


@contextmanager
def tmpfs_base():
    with tempfile.TemporaryDirectory(prefix='palimpsest-runtime-stage-',dir='/tmp') as value:
        yield Path(value)


def stage(reg,target,**kwargs):
    raw=canonical(reg)
    return api().stage_tmpfs_registration(raw,expected_sha256=kwargs.pop('expected_sha256',hashlib.sha256(raw).hexdigest()),
        staging_root=str(target),deadline=kwargs.pop('deadline',time.monotonic()+30),**kwargs)


@pytest.mark.parametrize('version',[2,3])
def test_exact_tmpfs_copy_is_closed_and_accepted_by_held_consumer(tmp_path,version):
    source,reg=forest(tmp_path,version);original=copy.deepcopy(reg)
    before=len(os.listdir('/proc/self/fd'))
    with tmpfs_base() as base:
        target=base/'stage';result=stage(reg,target)
        assert reg==original and len(os.listdir('/proc/self/fd'))==before
        assert result['kind']=='puck-worker-dependencies-v3' and result['version']==3
        assert result['native_identity']=='tmpfs-raw-dev-inode-v1'
        for key in ('modules','namespaces','distributions','import_profile'):assert result[key]==reg[key]
        root=Path(result['roots'][0]['root'])
        assert result['roots'][0]['kind']=='package' and (root/'empty/nested').is_dir()
        assert stat.S_IMODE(target.stat().st_mode)==stat.S_IMODE(root.stat().st_mode)==0o700
        for row in reg['roots'][0]['files']:
            assert (root/row['path']).read_bytes()==(source/row['path']).read_bytes()
            assert stat.S_IMODE((root/row['path']).stat().st_mode)==0o600
        registration=base/'registration.json';raw=canonical(result);registration.write_bytes(raw)
        from palimpsest.puck_dependency_files import HeldDependencyNamespace
        with HeldDependencyNamespace(raw,expected_sha256=hashlib.sha256(raw).hexdigest(),
                deadline=time.monotonic()+30,registration_path=str(registration)) as held:
            assert held.read(0,'demo/__pycache__/inert.pyc')==b'not executable bytecode'
            assert held.snapshot()['runtime_qualified'] is False
        assert len(os.listdir('/proc/self/fd'))==before


def test_system_image_root_copies_only_selected_leaves_and_preserves_indices(tmp_path):
    _,reg=forest(tmp_path);system=tmp_path/'system';system.mkdir()
    (system/'selected.so').write_bytes(b'authored image data');os.mkfifo(system/'unselected-fifo')
    reg['roots'].append(dict(root=str(system),kind='system_images',files=[descriptor(system/'selected.so','selected.so')]))
    with tmpfs_base() as base:
        result=stage(reg,base/'stage');root=Path(result['roots'][1]['root'])
        assert list(p.name for p in root.iterdir())==['selected.so']
        assert result['modules']==reg['modules'] and all(r['kind']=='package' for r in result['roots'])


def test_large_leaf_is_streamed_without_metadata_copy_limit(tmp_path,monkeypatch):
    source,reg=forest(tmp_path);path=source/'large.bin';path.write_bytes(b'x'*(5*1024**2+17))
    reg['roots'][0]['files'].append(descriptor(path,'large.bin'));reg['roots'][0]['files'].sort(key=lambda r:r['path'])
    m=api();original=m.os.read;sizes=[]
    def bounded(fd,size):
        sizes.append(size);assert size<=1024**2
        return original(fd,size)
    monkeypatch.setattr(m.os,'read',bounded)
    with tmpfs_base() as base:
        result=stage(reg,base/'stage')
        assert hashlib.sha256((Path(result['roots'][0]['root'])/'large.bin').read_bytes()).hexdigest()==reg['roots'][0]['files'][-1]['sha256']
    assert sizes


@pytest.mark.parametrize('defect',['extra','missing','symlink','fifo','alias'])
def test_source_namespace_defects_return_no_descriptor_and_close_fds(tmp_path,defect):
    source,reg=forest(tmp_path);leaf=source/'demo/__init__.py'
    if defect=='extra':(source/'extra').write_bytes(b'undeclared')
    elif defect=='missing':leaf.unlink()
    elif defect=='symlink':leaf.unlink();leaf.symlink_to(source/'demo-1.dist-info/METADATA')
    elif defect=='fifo':leaf.unlink();os.mkfifo(leaf)
    else:
        os.link(leaf,source/'alias');reg['roots'][0]['files'].insert(0,descriptor(source/'alias','alias'))
    before=len(os.listdir('/proc/self/fd'))
    with tmpfs_base() as base,pytest.raises((ValueError,RuntimeError,OSError)):
        stage(reg,base/'stage')
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('defect',['registration-hash','leaf-hash','persistent','preexisting','overlap','ancestor-symlink'])
def test_invalid_source_or_destination_refuses_without_replacing_existing_bytes(tmp_path,defect):
    source,reg=forest(tmp_path);before=len(os.listdir('/proc/self/fd'))
    with tmpfs_base() as base:
        target=base/'stage';kwargs={}
        if defect=='registration-hash':kwargs['expected_sha256']='0'*64
        elif defect=='leaf-hash':reg['roots'][0]['files'][0]['sha256']='0'*64
        elif defect=='persistent':target=tmp_path/'persistent-stage'
        elif defect=='preexisting':target.mkdir();(target/'preserved').write_bytes(b'preserved')
        elif defect=='overlap':target=source/'stage'
        else:
            actual=base/'actual';actual.mkdir();alias=base/'alias';alias.symlink_to(actual,target_is_directory=True);target=alias/'stage'
        with pytest.raises((ValueError,RuntimeError,OSError)):stage(reg,target,**kwargs)
        if defect=='preexisting':assert (target/'preserved').read_bytes()==b'preserved'
        if defect=='registration-hash':assert not target.exists()
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('defect',['source','destination','extra-destination','late-write'])
def test_drift_during_copy_is_not_published_and_keeps_partial_tree(tmp_path,monkeypatch,defect):
    source,reg=forest(tmp_path);m=api();original=m.os.write;changed=False
    before=len(os.listdir('/proc/self/fd'))
    with tmpfs_base() as base:
        target=base/'stage'
        def write(fd,raw):
            nonlocal changed
            count=original(fd,raw)
            if not changed:
                changed=True;path=Path(os.readlink('/proc/self/fd/'+str(fd)))
                if defect=='source':(source/'demo/__init__.py').write_bytes(b'mutated source')
                elif defect=='destination':path.write_bytes(b'z'*path.stat().st_size)
                elif defect=='extra-destination':(path.parent/'extra').write_bytes(b'undeclared')
                else:time.sleep(.2)
            return count
        monkeypatch.setattr(m.os,'write',write)
        with pytest.raises((ValueError,RuntimeError,OSError,TimeoutError)):
            stage(reg,target,**({'deadline':time.monotonic()+.1} if defect=='late-write' else {}))
        assert changed and target.exists()
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('deadline',[True,float('nan'),float('inf'),-1])
def test_invalid_deadline_rejects_before_allocation(tmp_path,deadline):
    _,reg=forest(tmp_path)
    with tmpfs_base() as base,pytest.raises(ValueError):stage(reg,base/'stage',deadline=deadline)


def test_overlong_deadline_and_schema_size_limits_refuse_before_allocation(tmp_path,monkeypatch):
    _,reg=forest(tmp_path)
    with tmpfs_base() as base:
        with pytest.raises(ValueError):stage(reg,base/'stage',deadline=time.monotonic()+181)
        from palimpsest import puck_dependency_files
        monkeypatch.setattr(puck_dependency_files,'MAX_TOTAL_BYTES',1)
        with pytest.raises(ValueError):stage(reg,base/'stage')
        assert not (base/'stage').exists()


def test_metadata_ceiling_closes_planning_handles(tmp_path,monkeypatch):
    _,reg=forest(tmp_path);m=api();monkeypatch.setattr(m,'MAX_METADATA_BYTES',1)
    before=len(os.listdir('/proc/self/fd'))
    with tmpfs_base() as base,pytest.raises(ValueError):stage(reg,base/'stage')
    assert len(os.listdir('/proc/self/fd'))==before


def test_registered_relative_depth_32_survives_root_relocation(tmp_path):
    source,reg=forest(tmp_path);relative='/'.join(['nested']*31+['leaf.bin'])
    leaf=source/relative;leaf.parent.mkdir(parents=True);leaf.write_bytes(b'depth boundary')
    reg['roots'][0]['files'].append(descriptor(leaf,relative));reg['roots'][0]['files'].sort(key=lambda r:r['path'])
    with tmpfs_base() as base:
        result=stage(reg,base/'stage')
        assert (Path(result['roots'][0]['root'])/relative).read_bytes()==b'depth boundary'


def test_explicit_native_cache_profile_survives_data_only_staging(tmp_path):
    import importlib.machinery
    source,reg=forest(tmp_path,version=3)
    relative='demo/native'+importlib.machinery.EXTENSION_SUFFIXES[0]
    leaf=source/relative;leaf.write_bytes(b'authored native data, never executed')
    reg['roots'][0]['files'].append(descriptor(leaf,relative));reg['roots'][0]['files'].sort(key=lambda r:r['path'])
    reg['modules'].append(dict(name='demo.native',root_index=0,path=relative,kind='extension',is_package=False))
    reg['import_profile'].update(kind='puck-producer-import-profile-v2',version=2,native_cache=[
        dict(name='cache_only_demo',producer='demo.native',phase='module_exec',delegate_attributes=[])])
    with tmpfs_base() as base:
        result=stage(reg,base/'stage')
        assert result['import_profile']==reg['import_profile']
        assert (Path(result['roots'][0]['root'])/relative).read_bytes()==b'authored native data, never executed'
