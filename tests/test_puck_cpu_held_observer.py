"""External observer records real child transport without runtime authority."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/observe_puck_cpu_held_allocation.py'


def api():
    assert SCRIPT.is_file(), 'External CPU CLI observer is not implemented'
    spec=importlib.util.spec_from_file_location('cpu_cli_observer_tests',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def setup(tmp_path,monkeypatch,body):
    module=api();monkeypatch.setattr(module,'ROOT',tmp_path)
    (tmp_path/'scripts').mkdir();(tmp_path/'runs').mkdir()
    (tmp_path/'scripts/qualify_puck_cpu_held_runtime.py').write_text(body)
    config=dict(kind='puck-cpu-held-runtime-allocation-v1',phase='prepare',root=str(tmp_path))
    raw=(json.dumps(config,sort_keys=True,separators=(',',':'))+'\n').encode()
    path=tmp_path/'configuration.json';path.write_bytes(raw)
    return module,path,hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('code',[0,7])
def test_records_real_exit_streams_and_refuses_overwrite(tmp_path,monkeypatch,code):
    module,path,sha=setup(tmp_path,monkeypatch,
        'import sys\nsys.stdout.buffer.write(b"real stdout\\n")\nsys.stderr.buffer.write(b"real stderr\\n")\nsys.exit('+str(code)+')\n')
    before=len(os.listdir('/proc/self/fd'))
    result=module.observe(path,sha)
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['configuration_sha256']==sha and result['phase']=='prepare'
    assert result['command']==[module.PYTHON,'-I','-S','-B',str(tmp_path/'scripts/qualify_puck_cpu_held_runtime.py'),'--configuration',str(path),'--sha256',sha]
    assert 0<result['elapsed_seconds']<10
    for name,expected in (('stdout',b'real stdout\n'),('stderr',b'real stderr\n')):
        row=result[name];data=(tmp_path/row['path']).read_bytes();assert data==expected
        assert row['size_bytes']==len(data) and row['sha256']==hashlib.sha256(data).hexdigest()
    saved={p:p.read_bytes() for p in (tmp_path/'runs').iterdir()}
    with pytest.raises(FileExistsError):module.observe(path,sha)
    assert all(p.read_bytes()==raw for p,raw in saved.items())
    assert len(os.listdir('/proc/self/fd'))==before


def test_refuses_bad_configuration_hash_before_reserving_outputs(tmp_path,monkeypatch):
    module,path,sha=setup(tmp_path,monkeypatch,'raise AssertionError("must not run")\n')
    with pytest.raises(ValueError,match='SHA'):module.observe(path,'0'*64)
    assert list((tmp_path/'runs').iterdir())==[]


def test_times_out_and_reaps_owned_child(tmp_path,monkeypatch):
    module,path,sha=setup(tmp_path,monkeypatch,
        'import os,time\nprint(os.getpid(),flush=True)\ntime.sleep(60)\n')
    monkeypatch.setattr(module,'NORMAL_SECONDS',0.2)
    result=module.observe(path,sha)
    pid=int((tmp_path/result['stdout']['path']).read_text())
    assert result['timed_out'] is True and result['observed_returncode']==-signal.SIGKILL
    assert not Path('/proc/'+str(pid)).exists()
    assert result['elapsed_seconds']<5


def test_preparation_can_copy_an_authored_payload_larger_than_log_limit(tmp_path):
    # The real accepted tree contains a432MB library. A17MiB inert payload is
    # enough to reproduce the inherited16MiB ceiling without vendor execution.
    module=api();spec=importlib.util.spec_from_file_location('cpu_parent_file_limit',ROOT/'scripts/qualify_puck_cpu_held_runtime.py')
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    (tmp_path/'scripts').mkdir();(tmp_path/'runs').mkdir()
    observer=tmp_path/'scripts/observe_puck_cpu_held_allocation.py';observer.write_bytes(SCRIPT.read_bytes())
    ceiling=parent.LIMITS['prepare']['file_bytes']
    body='import resource\nfrom pathlib import Path\nresource.setrlimit(resource.RLIMIT_FSIZE,('+str(ceiling)+','+str(ceiling)+'))\nwith Path("authored-payload.bin").open("wb") as stream:\n for i in range(17):stream.write(b"x"*(1024**2))\nprint("authored copy complete",flush=True)\n'
    (tmp_path/'scripts/qualify_puck_cpu_held_runtime.py').write_text(body)
    config=dict(kind='puck-cpu-held-runtime-allocation-v1',phase='prepare',root=str(tmp_path))
    raw=(json.dumps(config,sort_keys=True,separators=(',',':'))+'\n').encode();configuration=tmp_path/'configuration.json';configuration.write_bytes(raw)
    import subprocess
    result=subprocess.run([module.PYTHON,'-I','-S','-B',str(observer),'--configuration',str(configuration),
        '--sha256',hashlib.sha256(raw).hexdigest()],cwd=tmp_path,env=module.ENVIRONMENT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
    diagnostic=(tmp_path/'runs/puck-cpu-held-preparation-01-external-cli.stderr').read_bytes()
    assert result.returncode==0,(result.returncode,result.stdout,result.stderr,diagnostic)
    assert (tmp_path/'authored-payload.bin').stat().st_size==17*1024**2
    assert parent.LIMITS['qualify']['file_bytes']==16*1024**2


@pytest.mark.parametrize('code',[0,7])
def test_qualification02_uses_exclusive_new_paths_and_preserves01(tmp_path,monkeypatch,code):
    module,path,_=setup(tmp_path,monkeypatch,'import sys\nprint("authored02")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v2',version=2,allocation_id=2,phase='qualify')
    raw=module.canonical(config);path.write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
    old=tmp_path/'runs/puck-cpu-held-qualification-01';old.mkdir();(old/'result.json').write_bytes(b'preserved consumed01')
    for suffix in ('-external-cli.stdout','-external-cli.stderr','-external-cli-transport.json'):
        (tmp_path/('runs/puck-cpu-held-qualification-01'+suffix)).write_bytes(b'preserved01'+suffix.encode())
    legacy={p:p.read_bytes() for p in (tmp_path/'runs').rglob('*') if p.is_file()}
    result=module.observe(path,sha)
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['stdout']['path']=='runs/puck-cpu-held-qualification-02-external-cli.stdout'
    assert (tmp_path/result['stdout']['path']).read_bytes()==b'authored02\n'
    assert all(p.read_bytes()==raw for p,raw in legacy.items())
    captured={p:p.read_bytes() for p in (tmp_path/'runs').rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):module.observe(path,sha)
    assert all(p.read_bytes()==raw for p,raw in captured.items())


@pytest.mark.parametrize('field,value',[('phase','prepare'),('version',True),('allocation_id',1),('allocation_id',True)])
def test_qualification02_observer_refuses_wrong_closed_identity(tmp_path,monkeypatch,field,value):
    module,path,_=setup(tmp_path,monkeypatch,'raise AssertionError("must not run")\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v2',version=2,allocation_id=2,phase='qualify');config[field]=value
    raw=module.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):module.observe(path,hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]


@pytest.mark.parametrize('code',[0,7])
def test_qualification03_uses_fresh_paths_preserving_both_consumed_epochs(tmp_path,monkeypatch,code):
    module,path,_=setup(tmp_path,monkeypatch,'import sys\nprint("authored03")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v3',version=3,allocation_id=3,phase='qualify')
    raw=module.canonical(config);path.write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
    for epoch in ('01','02'):
        stem='runs/puck-cpu-held-qualification-'+epoch;old=tmp_path/stem;old.mkdir();(old/'result.json').write_bytes(b'preserved consumed'+epoch.encode())
        for suffix in ('-external-cli.stdout','-external-cli.stderr','-external-cli-transport.json'):
            (tmp_path/(stem+suffix)).write_bytes(b'preserved'+epoch.encode()+suffix.encode())
    legacy={p:p.read_bytes() for p in (tmp_path/'runs').rglob('*') if p.is_file()}
    result=module.observe(path,sha)
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['stdout']['path']=='runs/puck-cpu-held-qualification-03-external-cli.stdout'
    assert (tmp_path/result['stdout']['path']).read_bytes()==b'authored03\n'
    assert all(p.read_bytes()==raw for p,raw in legacy.items())
    captured={p:p.read_bytes() for p in (tmp_path/'runs').rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):module.observe(path,sha)
    assert all(p.read_bytes()==raw for p,raw in captured.items())


@pytest.mark.parametrize('field,value',[('phase','prepare'),('version',2),('version',True),('allocation_id',2),('allocation_id',True)])
def test_qualification03_observer_rejects_epoch_alias_before_launch(tmp_path,monkeypatch,field,value):
    module,path,_=setup(tmp_path,monkeypatch,'raise AssertionError("must not run")\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v3',version=3,allocation_id=3,phase='qualify');config[field]=value
    raw=module.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):module.observe(path,hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]


@pytest.mark.parametrize('code',[0,7])
@pytest.mark.parametrize('version',[4,5])
def test_qualification04_05_observer_preserves_prior_epochs_and_reserves_once(tmp_path,monkeypatch,code,version):
    module,path,_=setup(tmp_path,monkeypatch,'import sys\nprint("authored04")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v'+str(version),version=version,allocation_id=version,phase='qualify')
    raw=module.canonical(config);path.write_bytes(raw);sha=hashlib.sha256(raw).hexdigest()
    for epoch in (str(i).zfill(2) for i in range(1,version)):
        stem='runs/puck-cpu-held-qualification-'+epoch;old=tmp_path/stem;old.mkdir();(old/'result.json').write_bytes(b'preserved consumed'+epoch.encode())
        for suffix in ('-external-cli.stdout','-external-cli.stderr','-external-cli-transport.json'):
            (tmp_path/(stem+suffix)).write_bytes(b'preserved'+epoch.encode()+suffix.encode())
    legacy={p:p.read_bytes() for p in (tmp_path/'runs').rglob('*') if p.is_file()}
    result=module.observe(path,sha)
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['stdout']['path']=='runs/puck-cpu-held-qualification-'+str(version).zfill(2)+'-external-cli.stdout'
    assert (tmp_path/result['stdout']['path']).read_bytes()==b'authored04\n'
    assert all(p.read_bytes()==raw for p,raw in legacy.items())
    captured={p:p.read_bytes() for p in (tmp_path/'runs').rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):module.observe(path,sha)
    assert all(p.read_bytes()==raw for p,raw in captured.items())


@pytest.mark.parametrize('field,value',[('allocation_id',3),('phase','prepare')])
@pytest.mark.parametrize('version',[4,5])
def test_qualification04_05_observer_refuses_wrong_closed_selector(tmp_path,monkeypatch,field,value,version):
    module,path,_=setup(tmp_path,monkeypatch,'raise AssertionError("must not run")\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v'+str(version),version=version,allocation_id=version,phase='qualify');config[field]=value
    raw=module.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):module.observe(path,hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]
