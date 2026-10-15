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
