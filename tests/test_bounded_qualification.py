"""Qualification guards on authored files and plain Python child processes."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

NAME = 'palimpsest.bounded_qualification'
MiB = 1024 ** 2


def helper():
    assert importlib.util.find_spec(NAME) is not None, 'Bounded qualification helper is missing'
    return importlib.import_module(NAME)


def command(code): return [sys.executable, '-c', code]


def supervise(tmp_path, code, **extra):
    root = tmp_path / 'attempt'; root.mkdir(); output = root / 'outer'; output.mkdir()
    now = time.monotonic()
    arguments = dict(cwd=tmp_path, normal_deadline=now+2, hard_deadline=now+3,
                     rss_bytes=1024**3, output_bytes=16*MiB, min_free_bytes=0,
                     output_root=root)
    arguments.update(extra)
    return helper().supervised(command(code), output, **arguments), output


def test_missing_api_red_then_exclusive_canonical_control(tmp_path):
    module = helper(); target = tmp_path / 'control.json'
    module.write_new(target, {'z':1,'a':2})
    assert target.read_bytes() == b'{"a":2,"z":1}\n'
    assert module.read_control(target) == {'a':2,'z':1}
    with pytest.raises(FileExistsError): module.write_new(target, {'new':True})
    assert target.read_bytes() == b'{"a":2,"z":1}\n'


@pytest.mark.parametrize('kind', ['symlink','fifo','hardlink','oversize','duplicate-json','nonfinite-json'])
def test_read_control_refuses_unsafe_files(tmp_path, kind):
    module = helper(); target = tmp_path / 'control.json'; target.write_bytes(b'{"a":1}\n')
    if kind == 'symlink':
        actual = tmp_path / 'actual'; target.rename(actual); target.symlink_to(actual)
    elif kind == 'fifo': target.unlink(); os.mkfifo(target)
    elif kind == 'hardlink': os.link(target, tmp_path / 'alias')
    elif kind == 'oversize': target.write_bytes(b'x' * (MiB+1))
    elif kind == 'duplicate-json': target.write_bytes(b'{"a":1,"a":2}')
    elif kind == 'nonfinite-json': target.write_bytes(b'{"a":NaN}')
    with pytest.raises((ValueError,OSError)): module.read_control(target)


def test_publication_directory_detects_same_contents_swap_even_failed_body(tmp_path):
    module = helper(); output = tmp_path / 'out'; output.mkdir()
    with pytest.raises(RuntimeError,match='directory'):
        with module.publication_directory(output):
            output.rename(tmp_path / 'saved'); output.mkdir(); raise LookupError('body')


def test_publication_directory_rejects_symlink_ancestor(tmp_path):
    module = helper(); actual = tmp_path / 'actual'; actual.mkdir(); alias = tmp_path / 'alias'
    alias.symlink_to(actual,target_is_directory=True)
    with pytest.raises(OSError):
        with module.publication_directory(alias): pass


def test_reserve_output_exclusive_disjoint_and_exact_runs_parent(tmp_path):
    module = helper(); repo = tmp_path / 'repo'; repo.mkdir()
    inputs = {'sources':{'root':str(repo),'files':[{'path':'src/model.py'}]},
              'bundles':{'root':str(tmp_path/'bundle'),'files':[]}}
    output = repo / 'runs/attempt'
    module.reserve_output(output,inputs)
    assert (output/'outer').is_dir()
    with pytest.raises(FileExistsError): module.reserve_output(output,inputs)
    with pytest.raises(ValueError): module.reserve_output(repo/'other/attempt',inputs)
    protected = dict(inputs,bundles={'root':str(repo/'runs'),'files':[]})
    with pytest.raises(ValueError): module.reserve_output(repo/'runs/second',protected)


def test_normal_exit_and_parent_rss_are_recorded(tmp_path):
    result, output = supervise(tmp_path,"print('plain child')")
    assert result['status'] == 'completed'
    assert result['returncode'] == 0 and result['matching_survivors'] == []
    assert result['sampled_peak_rss_bytes'] > 0
    assert (output/'stdout.log').read_text() == 'plain child\n'


def test_parent_rss_limit_stops_before_work(tmp_path):
    result, output = supervise(tmp_path,"print('must not run')",rss_bytes=1)
    assert result['status'] == 'failed' and result['failure'] == 'sampled RSS stop threshold'
    assert (output/'stdout.log').read_bytes() == b''


def test_log_prefix_is_bounded_and_failed(tmp_path):
    result, output = supervise(tmp_path,"import sys;sys.stdout.write('x'*2200000)")
    assert result['status'] == 'failed'
    assert (output/'stdout.log').stat().st_size <= MiB


def test_normal_deadline_terminates_ignored_term(tmp_path):
    now=time.monotonic()
    result,output=supervise(tmp_path,"import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(10)",normal_deadline=now+.10,hard_deadline=now+.35)
    assert result['status']=='failed' and result['matching_survivors']==[]
    assert result['finished_monotonic'] >= now+.10


def test_term_ignoring_child_after_leader_exit_is_killed(tmp_path):
    code="import subprocess,sys;subprocess.Popen([sys.executable,'-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(10)'])"
    result,output=supervise(tmp_path,code)
    assert result['status']=='failed' and 'survivors' in result['failure']
    assert result['matching_survivors']==[]


def test_final_deadline_even_if_leader_already_exited(tmp_path,monkeypatch):
    module=helper();original=module.subprocess.Popen
    def delayed(*args,**kwargs):
        child=original(*args,**kwargs);child.wait();time.sleep(.05);return child
    monkeypatch.setattr(module.subprocess,'Popen',delayed)
    now=time.monotonic()
    result,_=supervise(tmp_path,'pass',normal_deadline=now+.005,hard_deadline=now+.01)
    assert result['status']=='failed' and result['failure'] in ('hard deadline','normal-return deadline')


def test_final_log_drain_is_part_of_deadline(tmp_path,monkeypatch):
    from contextlib import contextmanager
    module=helper(); original=module._owned_logs
    @contextmanager
    def delayed(*args,**kwargs):
        with original(*args,**kwargs) as streams: yield streams
        time.sleep(.15)
    monkeypatch.setattr(module,'_owned_logs',delayed)
    now=time.monotonic()
    result,_=supervise(tmp_path,'pass',normal_deadline=now+.1,hard_deadline=now+.12)
    assert result['status']=='failed' and result['failure']=='hard deadline'


def test_aggregate_output_and_free_floor_checked(tmp_path):
    result,_=supervise(tmp_path,"open('attempt/extra','wb').write(b'x'*2000)",output_bytes=1000)
    assert result['status']=='failed' and result['failure']=='aggregate output cap'


def test_hard_guard_requires_dedicated_outer_group(monkeypatch):
    module=helper()
    monkeypatch.setattr(module.os, 'getpgrp', lambda: module.os.getpid() + 1)
    with pytest.raises(ValueError):
        with module.hard_guard(time.monotonic()+1,{}): pass


@pytest.mark.parametrize('registered', [True, False])
def test_real_hard_guard_kills_outer_and_its_own_group(tmp_path, registered):
    helper()
    pidfile=tmp_path/'child.pid'
    code=f"""import os,sys,time,subprocess
from palimpsest.bounded_qualification import hard_guard
state={{}}
with hard_guard(time.monotonic()+.35,state):
 child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'],start_new_session=True)
 if {registered!r}:state['group']=child.pid
 open({str(pidfile)!r},'w').write(str(child.pid))
 time.sleep(10)
"""
    parent=subprocess.Popen(command(code),start_new_session=True)
    try:
        assert parent.wait(timeout=3) == -signal.SIGKILL
        pid=int(pidfile.read_text());time.sleep(.05)
        state=Path(f'/proc/{pid}/stat')
        assert not state.exists() or state.read_text().rsplit(')',1)[1].split()[0] in ('Z','X')
    finally:
        if parent.poll() is None: os.killpg(parent.pid,signal.SIGKILL);parent.wait()


def test_import_does_not_load_model_or_native_modules():
    helper()
    result=subprocess.run(command(f'import sys;import {NAME};assert not {{"torch","mujoco","numpy","palimpsest.engine"}} & set(sys.modules)'),capture_output=True,text=True)
    assert result.returncode==0,result.stderr


def test_hard_guard_exit_clock_denies_stopped_timer_thread(tmp_path):
    helper()
    code="""import time
from palimpsest import bounded_qualification as q
class DelayedThread:
 def __init__(self,*args,**kwargs):pass
 def start(self):pass
 def join(self,*args,**kwargs):pass
q.threading.Thread=DelayedThread
with q.hard_guard(time.monotonic()+.02,{}):
 time.sleep(.05)
raise AssertionError('Expired hard guard returned successfully')
"""
    parent=subprocess.Popen(command(code),start_new_session=True)
    try: assert parent.wait(timeout=3)==-signal.SIGKILL
    finally:
        if parent.poll() is None:os.killpg(parent.pid,signal.SIGKILL);parent.wait()


@pytest.mark.parametrize('deadline',[True,None,float('inf'),float('nan')])
def test_invalid_hard_guard_deadline_refuses_before_thread(deadline):
    with pytest.raises(ValueError):
        with helper().hard_guard(deadline,{}):pass


def test_control_edit_restore_detected_during_read(tmp_path,monkeypatch):
    module=helper();target=tmp_path/'control.json';target.write_bytes(b'{"a":1}\n')
    original=module.os.read;changed=False
    def altering(fd,count):
        nonlocal changed
        block=original(fd,count)
        if not changed:
            changed=True;raw=target.read_bytes();target.write_bytes(b'{}');target.write_bytes(raw)
        return block
    monkeypatch.setattr(module.os,'read',altering)
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(RuntimeError):module.read_control(target)
    assert len(os.listdir('/proc/self/fd'))==before


@pytest.mark.parametrize('cap',[True,0,1.0,MiB+1])
def test_control_cap_exact_integer(cap,tmp_path):
    module=helper();target=tmp_path/'control.json'
    with pytest.raises(ValueError):module.write_new(target,{},max_bytes=cap)
    with pytest.raises(ValueError):module.read_control(target,max_bytes=cap)


def test_final_publication_custody_exit_is_in_clock(tmp_path,monkeypatch):
    from contextlib import contextmanager
    module=helper(); original=module.publication_directory
    @contextmanager
    def delayed(path):
        with original(path) as fd:yield fd
        if Path(path).name=='attempt':time.sleep(.07)
    monkeypatch.setattr(module,'publication_directory',delayed)
    now=time.monotonic()
    result,_=supervise(tmp_path,'pass',normal_deadline=now+.12,hard_deadline=now+.15)
    assert result['status']=='failed'


def test_control_same_bytes_leaf_swap_during_fsync_refuses(tmp_path,monkeypatch):
    module=helper();target=tmp_path/'control.json';original=module.os.fsync;calls=0
    def swap(fd):
        nonlocal calls
        original(fd);calls+=1
        if calls==2:
            raw=target.read_bytes();target.unlink();target.write_bytes(raw)
    monkeypatch.setattr(module.os,'fsync',swap)
    with pytest.raises(RuntimeError,match='publication'):
        module.write_new(target,{'value':1})


def test_explicit_package_namespace_allows_more_than_legacy32_files(tmp_path):
    code = ("from pathlib import Path\n"
            "p=Path('attempt/archives');p.mkdir()\n"
            "for n in range(40):(p/str(n)).write_bytes(b'archive')\n")
    result, output = supervise(tmp_path, code, output_namespace_limits=(50, 2))
    assert result["status"] == "completed"
    assert result["returncode"] == 0 and result["matching_survivors"] == []
    assert len(list((output.parent / "archives").iterdir())) == 40


@pytest.mark.parametrize("limits", [(True,2), (0,2), (513,2), (50,True), (50,0), (50,17), [50,2]])
def test_package_namespace_requires_exact_bounded_count_pair(tmp_path, limits):
    with pytest.raises(ValueError):
        supervise(tmp_path, "raise RuntimeError('must not execute')",
                  output_namespace_limits=limits)


def test_explicit_package_namespace_still_refuses_excess_files(tmp_path):
    code = ("from pathlib import Path\n"
            "p=Path('attempt/archives');p.mkdir()\n"
            "for n in range(40):(p/str(n)).write_bytes(b'archive')\n")
    with pytest.raises(ValueError):
        supervise(tmp_path, code, output_namespace_limits=(41, 2))


def test_legacy_default_namespace_still_refuses_more_than32_files(tmp_path):
    code = ("from pathlib import Path\n"
            "p=Path('attempt/archives');p.mkdir()\n"
            "for n in range(40):(p/str(n)).write_bytes(b'archive')\n")
    with pytest.raises(ValueError):
        supervise(tmp_path, code)
