"""Operational supervision of authored descendants that create new sessions."""
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

MiB = 1024**2


def api():
    return importlib.import_module('palimpsest.bounded_qualification')


def identity(pid):
    try:
        row=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        return None if row[0] in ('Z','X') else int(row[19])
    except FileNotFoundError:
        return None


def cleanup(path):
    if path.exists():
        row=json.loads(path.read_text())
        if identity(row['pid'])==row['start_ticks']:
            os.kill(row['pid'],signal.SIGKILL)


def escaped_code(path, *, seconds=10, memory=0, orphan=False):
    # Publish the exact child identity before the RSS stimulus can trigger a stop.
    child=("import json,os,signal,time\n"
           "os.setsid();signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
           "ticks=int(open('/proc/self/stat').read().rsplit(')',1)[1].split()[19])\n"
           f"open({str(path)!r},'w').write(json.dumps(dict(pid=os.getpid(),start_ticks=ticks,group=os.getpgrp())))\n"
           f"payload=bytearray({memory})\n"
           f"time.sleep({seconds})\n")
    return ("import subprocess,sys,time\n"
            f"child=subprocess.Popen([sys.executable,'-c',{child!r}])\n"
            + ("time.sleep(.2)\n" if orphan else "child.wait()\n"))


def supervise(tmp_path, code, **extra):
    root=tmp_path/'attempt';root.mkdir();logs=root/'logs';logs.mkdir()
    now=time.monotonic()
    arguments=dict(cwd=tmp_path,normal_deadline=now+2,hard_deadline=now+3,
        rss_bytes=1024**3,output_bytes=MiB,min_free_bytes=0,max_processes=2,
        output_root=root,log_mode='direct',process_scope='descendants')
    arguments.update(extra)
    return api().supervised([sys.executable,'-c',code],logs,**arguments)


def test_new_session_child_is_recorded_and_normal_exit_is_closed(tmp_path):
    pidfile=tmp_path/'escaped.json';state={}
    try:
        result=supervise(tmp_path,escaped_code(pidfile,seconds=.2),guard_state=state)
        row=json.loads(pidfile.read_text())
        assert row['group']==row['pid']
        assert result['status']=='completed' and result['matching_survivors']==[]
        assert result['process_scope']=='descendants'
        assert {k:row[k] for k in ('pid','start_ticks')} in result['tracked_processes']
        assert state['tracked_processes'][row['pid']]==row['start_ticks']
    finally:cleanup(pidfile)


@pytest.mark.parametrize('limit',['processes','rss','timeout','orphan'])
def test_session_escape_is_counted_and_killed_on_stop(tmp_path,limit):
    pidfile=tmp_path/'escaped.json';now=time.monotonic();options={}
    if limit=='processes':options['max_processes']=1
    if limit=='rss':
        parent_rss=int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
        options['rss_bytes']=parent_rss+40*MiB
    if limit=='timeout':options.update(normal_deadline=now+.5,hard_deadline=now+.9)
    try:
        result=supervise(tmp_path,escaped_code(pidfile,memory=64*MiB if limit=='rss' else 0,
                                             orphan=limit=='orphan'),**options)
        assert result['status']=='failed' and result['matching_survivors']==[]
        assert result['failure']=={'processes':'unexpected child process','rss':'sampled RSS stop threshold',
            'timeout':'normal-return deadline','orphan':'matching descendant survivors'}[limit]
        if limit=='rss':assert result['sampled_peak_rss_bytes']>options['rss_bytes']
        if pidfile.exists():
            row=json.loads(pidfile.read_text());assert identity(row['pid'])!=row['start_ticks']
        else:assert limit=='processes'  # The extra process can be stopped before its first Python line.
    finally:cleanup(pidfile)


def test_monitor_exception_kills_recorded_new_session(tmp_path,monkeypatch):
    pidfile=tmp_path/'escaped.json';module=api();original=module._output_bytes
    def fail_after_escape(*args,**kwargs):
        if pidfile.exists():raise LookupError('authored monitor failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'_output_bytes',fail_after_escape)
    try:
        with pytest.raises(LookupError,match='authored monitor failure'):
            supervise(tmp_path,escaped_code(pidfile))
        row=json.loads(pidfile.read_text())
        until=time.monotonic()+1
        while identity(row['pid'])==row['start_ticks'] and time.monotonic()<until:time.sleep(.01)
        assert identity(row['pid'])!=row['start_ticks']
    finally:cleanup(pidfile)


def test_hard_guard_kills_escape_during_blocked_monitor(tmp_path):
    pidfile=tmp_path/'escaped.json';root=tmp_path/'attempt';root.mkdir();logs=root/'logs';logs.mkdir()
    code=f"""import os,sys,time
from pathlib import Path
from palimpsest import bounded_qualification as q
state={{}};original=q._output_bytes
def blocked(*args,**kwargs):
 if Path({str(pidfile)!r}).exists():time.sleep(10)
 return original(*args,**kwargs)
q._output_bytes=blocked
with q.hard_guard(time.monotonic()+.7,state):
 q.supervised([sys.executable,'-c',{escaped_code(pidfile)!r}],{str(logs)!r},cwd={str(tmp_path)!r},
  normal_deadline=time.monotonic()+20,hard_deadline=time.monotonic()+30,rss_bytes=2**30,
  output_bytes=2**20,min_free_bytes=0,max_processes=2,guard_state=state,
  process_scope='descendants',log_mode='direct')
"""
    parent=subprocess.Popen([sys.executable,'-c',code],start_new_session=True)
    try:
        assert parent.wait(timeout=3)==-signal.SIGKILL
        row=json.loads(pidfile.read_text());until=time.monotonic()+1
        while identity(row['pid'])==row['start_ticks'] and time.monotonic()<until:time.sleep(.01)
        assert identity(row['pid'])!=row['start_ticks']
    finally:
        if parent.poll() is None:os.killpg(parent.pid,signal.SIGKILL);parent.wait()
        cleanup(pidfile)


def test_reused_pid_start_tick_mismatch_is_not_signalled(tmp_path):
    pidfile=tmp_path/'escaped.json'
    # Reparent to PID1 so the independent direct-child cleanup rule cannot own it.
    parent=subprocess.Popen([sys.executable,'-c',escaped_code(pidfile,orphan=True)])
    try:
        parent.wait(timeout=2);row=json.loads(pidfile.read_text())
        api()._kill_owned_groups({'tracked_processes':{row['pid']:row['start_ticks']+1}})
        assert identity(row['pid'])==row['start_ticks']
        api()._kill_owned_groups({'tracked_processes':{row['pid']:row['start_ticks']}})
        until=time.monotonic()+1
        while identity(row['pid'])==row['start_ticks'] and time.monotonic()<until:time.sleep(.01)
        assert identity(row['pid'])!=row['start_ticks']
    finally:
        if parent.poll() is None:parent.kill();parent.wait()
        cleanup(pidfile)


def test_group_scope_receipt_schema_is_unchanged(tmp_path):
    result=supervise(tmp_path,'pass',process_scope='group')
    assert result['status']=='completed'
    assert set(result)=={'status','returncode','failure','matching_survivors','sampled_peak_rss_bytes',
        'rss_sampling_seconds','pid','finished_monotonic'}


@pytest.mark.parametrize('scope',[None,True,[], 'tree'])
def test_unknown_process_scope_refuses_before_execution(tmp_path,scope):
    with pytest.raises(ValueError,match='process scope'):
        supervise(tmp_path,"raise AssertionError('must not execute')",process_scope=scope)


@pytest.mark.parametrize('maximum',[2,3])
def test_recursive_new_session_grandchild_is_counted_under_three_process_bound(tmp_path,maximum):
    pidfile=tmp_path/'grandchild.json'
    middle="import os\nos.setsid()\n"+escaped_code(pidfile,seconds=.3)
    code=f"import subprocess,sys\nchild=subprocess.Popen([sys.executable,'-c',{middle!r}])\nchild.wait()\n"
    state={}
    try:
        result=supervise(tmp_path,code,max_processes=maximum,guard_state=state)
        assert len(result['tracked_processes'])==3
        assert result['matching_survivors']==[]
        if maximum==3:
            assert result['status']=='completed'
            row=json.loads(pidfile.read_text());assert row['group']==row['pid']
            assert {k:row[k] for k in ('pid','start_ticks')} in result['tracked_processes']
        else:
            assert result['status']=='failed' and result['failure']=='unexpected child process'
        assert all(identity(row['pid'])!=row['start_ticks'] for row in result['tracked_processes'])
    finally:
        for pid,ticks in state.get('tracked_processes',{}).items():
            if identity(pid)==ticks:os.kill(pid,signal.SIGKILL)
        cleanup(pidfile)


def test_tracked_signal_uses_stable_handle_and_closes_it(tmp_path,monkeypatch):
    pidfile=tmp_path/'escaped.json';module=api();original=os.kill
    parent=subprocess.Popen([sys.executable,'-c',escaped_code(pidfile,orphan=True)])
    try:
        parent.wait(timeout=2);row=json.loads(pidfile.read_text())
        def refuse_numeric_pid(pid,signum):
            if pid==row['pid']:raise AssertionError('tracked signal used numeric PID instead of stable handle')
            return original(pid,signum)
        monkeypatch.setattr(module.os,'kill',refuse_numeric_pid)
        before=len(os.listdir('/proc/self/fd'))
        module._signal_tracked({row['pid']:row['start_ticks']},signal.SIGKILL)
        until=time.monotonic()+1
        while identity(row['pid'])==row['start_ticks'] and time.monotonic()<until:time.sleep(.01)
        assert identity(row['pid'])!=row['start_ticks']
        assert len(os.listdir('/proc/self/fd'))==before
    finally:
        if parent.poll() is None:parent.kill();parent.wait()
        if pidfile.exists():
            row=json.loads(pidfile.read_text())
            if identity(row['pid'])==row['start_ticks']:original(row['pid'],signal.SIGKILL)
