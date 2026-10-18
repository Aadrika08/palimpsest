"""Launcher/preparation checks use completed doubles, never native models."""
import contextlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from palimpsest.storage import StorageBudget, StorageLimits


def load(name):
    source = Path(__file__).resolve().parents[1]/'docs/reports/memory-decision-pilot-v2-evidence'/name
    assert source.exists(), 'Selected pilot wrapper is not implemented'
    spec = importlib.util.spec_from_file_location('selected_pilot_wrapper_fixture',source)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('driver,auditor,passed',[(0,0,True),(1,0,True),(0,1,True),(0,0,False)])
def test_pipeline_requires_driver_independent_audit_and_close(tmp_path,monkeypatch,driver,auditor,passed):
    module=load('execute-pilot.py');root=tmp_path/'output';path=tmp_path/'registration.json'
    monkeypatch.setattr(module.runner,'admission',lambda value:{'output':str(root)})
    calls=[]
    def run(value):
        assert value==path;calls.append('run');root.mkdir();return driver
    def audit(value):
        assert value==path;calls.append('audit')
        (root/'scientific-close.json').write_text(json.dumps({'pilot_complete':passed}))
        return auditor
    monkeypatch.setattr(module.m,'run',run,raising=False)
    monkeypatch.setattr(module.m,'audit',audit,raising=False)
    assert module.pipeline(path)==(0 if driver==auditor==0 and passed else 1)
    assert calls==['run','audit']


@pytest.mark.parametrize('code',[0,124])
def test_pilot_watchdogs_preserve_ancestor_containment_and_invalidate(tmp_path,monkeypatch,code):
    module=load('execute-pilot.py');runner=module.runner
    evidence=tmp_path/'docs/reports/memory-decision-pilot-v2-evidence';evidence.mkdir(parents=True)
    root=tmp_path/'runs/fixture';root.mkdir(parents=True)
    source=evidence/'execute-pilot.py'
    (root/'scientific-close.json').write_text(json.dumps({'pilot_complete':True}))
    reg={'repo':str(tmp_path),'output':str(root),'python':sys.executable,
         'control_root':str(tmp_path/'control'),'publication_root':str(evidence)}
    (evidence/'registration.json').write_text(json.dumps(reg))
    monkeypatch.setattr(runner,'__file__',str(source))
    monkeypatch.setattr(runner,'admission',lambda *a,**k:reg)
    monkeypatch.setattr(runner.d,'restore_v2_budget',lambda value:StorageBudget(
        (root,evidence,tmp_path/'control'),StorageLimits(max_bytes=1024**2,min_free_bytes=0)))
    calls=[]
    def child(command,**kw):
        calls.append(command)
        assert command[:5]==['timeout','--foreground','--signal=TERM','--kill-after=5','6590s']
        assert command[-3:]==[sys.executable,str(source),'--supervised']
        assert kw['start_new_session'] is False
        return SimpleNamespace(pid=999999999,wait=lambda **kw:code,poll=lambda:code)
    monkeypatch.setattr(runner.subprocess,'Popen',child)
    assert module.main(['--bounded'])==(0 if code==0 else 1)
    assert len(calls)==1
    assert json.loads((root/'scientific-close.json').read_text())['pilot_complete'] is (code==0)
    if code:
        receipt=json.loads((evidence/'invocation-result.json').read_text())
        assert receipt['watchdog_exit_code']==code and receipt['qualification_claims']==[]
    calls.clear()
    def ancestor(command,**kw):
        calls.append(command)
        assert command[:3]==['timeout','--signal=KILL','6600s']
        assert command[-3:]==[sys.executable,str(Path(module.__file__).resolve()),'--bounded']
        return SimpleNamespace(returncode=code)
    monkeypatch.setattr(module.subprocess,'run',ancestor)
    assert module.main([])==(0 if code==0 else 1)
    assert len(calls)==1


def preparer_fixture(tmp_path,monkeypatch):
    module=load('register.py');evidence=tmp_path/'docs/reports/memory-decision-pilot-v2-evidence'
    evidence.mkdir(parents=True);monkeypatch.setattr(module,'__file__',str(evidence/'register.py'))
    reg={'repo':str(tmp_path),'output':str(tmp_path/'runs/memory-decision-pilot-v2-fixture'),
         'control_root':str(tmp_path/'.superpowers/sdd/memory-decision-pilot-v2-runtime'),
         'publication_root':str(evidence),'protected_roots':[str(tmp_path/'old')],
         'preserved_sets':[{'files':[{'path':'old','sha256':'a'*64}]}]}
    calls=[]
    def build(repo,prerequisite,*,stamp,deadline):
        calls.append('build');assert repo==tmp_path and deadline==280
        return dict(reg)
    monkeypatch.setattr(module.m,'build_registration',build)
    monkeypatch.setattr(module.m,'recheck_inputs',lambda value,deadline:calls.append('recheck'))
    monkeypatch.setattr(module.m,'budget',lambda value:StorageBudget(
        [value[k] for k in ('output','control_root','publication_root')],
        StorageLimits(max_bytes=8*module.p.GiB,min_free_bytes=2*module.p.GiB),headroom_bytes=64*module.p.MiB))
    monkeypatch.setattr(module,'preparation_lease',contextlib.nullcontext)
    monkeypatch.setattr(module.time,'monotonic',lambda:100)
    monkeypatch.setattr(module.shutil,'disk_usage',lambda value:SimpleNamespace(free=16*module.p.GiB))
    monkeypatch.setattr(module.subprocess,'check_output',lambda *a,**k:b'')
    def command(argv,**kw):
        calls.append(argv)
        assert kw['check'] is True and 0<kw['timeout']<=180
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess,'run',command)
    return module,evidence,reg,calls


def test_preparation_rechecks_reserves_and_commits_only_registration(tmp_path,monkeypatch):
    module,evidence,reg,calls=preparer_fixture(tmp_path,monkeypatch)
    assert module.main(['--bounded'])==0
    path=evidence/'registration.json';written=json.loads(path.read_text())
    assert written['preparation_started_monotonic']==100
    assert written['preparation_deadline_monotonic']==280
    assert written['preparation_seconds_cap']==180
    assert calls[:2]==['build','recheck']
    assert calls[2]==['git','add',str(path)]
    assert calls[3][:3]==['git','commit','-m']
    assert not Path(reg['output']).exists() and not Path(reg['control_root']).exists()


@pytest.mark.parametrize('reason',['registration','control','output','dirty','reservation','deadline'])
def test_preparation_refusal_never_writes_or_commits(tmp_path,monkeypatch,reason):
    module,evidence,reg,calls=preparer_fixture(tmp_path,monkeypatch)
    if reason=='registration':(evidence/'registration.json').write_text('{}')
    elif reason in ('control','output'):Path(reg['control_root' if reason=='control' else 'output']).mkdir(parents=True)
    elif reason=='dirty':monkeypatch.setattr(module.subprocess,'check_output',lambda *a,**k:b' M source.py')
    elif reason=='reservation':
        monkeypatch.setattr(module.shutil,'disk_usage',lambda value:SimpleNamespace(
            free=10*module.p.GiB+64*module.p.MiB-1))
    elif reason=='deadline':
        def recheck(value,deadline):monkeypatch.setattr(module.time,'monotonic',lambda:281)
        monkeypatch.setattr(module.m,'recheck_inputs',recheck)
    with pytest.raises((ValueError,FileExistsError,RuntimeError,TimeoutError)):module.main(['--bounded'])
    assert not any(isinstance(row,list) for row in calls)
    if reason!='registration':assert not (evidence/'registration.json').exists()


def test_preparation_absolute_cap_includes_registration_commit(monkeypatch):
    module=load('register.py');calls=[]
    def command(argv,**kw):
        calls.append(argv)
        assert argv==['timeout','--signal=KILL','180s',sys.executable,
                      str(Path(module.__file__).resolve()),'--bounded']
        return SimpleNamespace(returncode=124)
    monkeypatch.setattr(module.subprocess,'run',command)
    assert module.main([])==1 and len(calls)==1


@pytest.mark.parametrize('failure',['add','commit'])
def test_failed_preparation_commit_preserves_registration_and_prevents_retry(tmp_path,monkeypatch,failure):
    module,evidence,reg,calls=preparer_fixture(tmp_path,monkeypatch)
    def command(argv,**kw):
        calls.append(argv)
        if argv[1]==failure:raise module.subprocess.CalledProcessError(1,argv)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess,'run',command)
    with pytest.raises(module.subprocess.CalledProcessError):module.main(['--bounded'])
    assert (evidence/'registration.json').exists()
    assert not Path(reg['output']).exists() and not Path(reg['control_root']).exists()
    before=list(calls)
    with pytest.raises(FileExistsError):module.main(['--bounded'])
    assert calls==before


def test_selected_origin_precedes_full_admission_and_pipeline_keeps_ancestor_group(tmp_path,monkeypatch):
    module=load('execute-pilot.py');runner=module.runner
    evidence=tmp_path/'docs/reports/memory-decision-pilot-v2-evidence';evidence.mkdir(parents=True)
    monkeypatch.setattr(runner,'__file__',str(evidence/'execute-pilot.py'))
    root=tmp_path/'runs/fixture';control=tmp_path/'control'
    reg={'repo':str(tmp_path),'output':str(root),'python':sys.executable,
         'control_root':str(control),'publication_root':str(evidence)}
    (evidence/'registration.json').write_text(json.dumps(reg))
    now=[100.]
    monkeypatch.setattr(runner.time,'monotonic',lambda:now[0])
    def admission(path):now[0]=110.;return reg
    monkeypatch.setattr(runner,'admission',admission)
    monkeypatch.setattr(runner.d,'restore_v2_budget',lambda reg:StorageBudget(
        [root,control,evidence],StorageLimits(max_bytes=8*runner.p.MiB,min_free_bytes=0)))
    monkeypatch.setattr(runner.shutil,'disk_usage',lambda value:SimpleNamespace(free=16*runner.p.GiB))
    monkeypatch.setattr(runner.subprocess,'check_output',lambda *a,**k:'a'*40)
    monkeypatch.setattr(runner.d,'recheck_v2_inputs',lambda *a:None)
    monkeypatch.setattr(runner.d,'cleanup_owners',lambda root:[])
    def child(command,**kw):
        assert kw['start_new_session'] is False
        root.mkdir(parents=True)
        (root/'execution.json').write_text(json.dumps({'readout_deadline_monotonic':6700.}))
        (root/'scientific-close.json').write_text(json.dumps({'pilot_complete':True}))
        return SimpleNamespace(pid=999999999,returncode=0,wait=lambda **k:0,poll=lambda:0)
    monkeypatch.setattr(runner.subprocess,'Popen',child)
    assert runner.execute()==0
    marker=json.loads((control/'launched.json').read_text())
    assert marker['started_monotonic']==100.
    assert marker['watchdog_command'][:5]==[
        'timeout','--foreground','--signal=TERM','--kill-after=5','6590s']


def test_preparation_lease_reuses_existing_file_read_only(tmp_path,monkeypatch):
    module=load('register.py');path=tmp_path/'.cache/palimpsest/writer.lock'
    path.parent.mkdir(parents=True);path.write_bytes(b'preserve existing lease')
    monkeypatch.setattr(module.Path,'home',lambda:tmp_path)
    observed=[];original=module.os.open
    def opened(value,flags,*args,**kw):
        observed.append(flags);return original(value,flags,*args,**kw)
    monkeypatch.setattr(module.os,'open',opened)
    with module.preparation_lease():
        with path.open('rb') as other:
            with pytest.raises(BlockingIOError):
                module.fcntl.flock(other,module.fcntl.LOCK_EX|module.fcntl.LOCK_NB)
    assert observed==[module.os.O_RDONLY|module.os.O_NOFOLLOW]
    assert path.read_bytes()==b'preserve existing lease'
    path.unlink()
    with pytest.raises(FileNotFoundError):
        with module.preparation_lease():pytest.fail('Missing lease was created')
    assert not path.exists()


def test_pilot_control_refuses_reentry_before_supervised_launch(tmp_path,monkeypatch):
    module=load('execute-pilot.py');control=tmp_path/'control';control.mkdir()
    monkeypatch.setattr(module.runner,'admission',lambda *a,**k:{'control_root':str(control)})
    calls=[];monkeypatch.setattr(module.runner,'main',lambda args:calls.append(args))
    for args in (['--bounded'],['--supervised']):
        with pytest.raises(FileExistsError):module.main(args)
    assert calls==[]


def test_ancestor_hard_timeout_leaves_no_selected_pipeline_process(tmp_path):
    """Real supervisor lifecycle; its only worker is a harmless exact-ID sleeper."""
    import os
    import signal
    import subprocess

    repo=tmp_path/'repo';evidence=repo/'docs/reports/memory-decision-pilot-v2-evidence'
    evidence.mkdir(parents=True);script=evidence/'execute.py'
    source=Path(__file__).resolve().parents[1]/'docs/reports/memory-decision-pilot-v2-evidence/execute-pilot.py'
    reg={'repo':str(repo),'output':str(repo/'runs/fixture'),'python':sys.executable,
         'control_root':str(repo/'control'),'publication_root':str(evidence)}
    (evidence/'registration.json').write_text(json.dumps(reg))
    script.write_text(f'''import importlib.util,json,os,signal,sys,time
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parents[3]
def identity(role):
    fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
    (HERE/(role+'.json')).write_text(json.dumps({{'pid':os.getpid(),
        'starttime':int(fields[19]),'pgid':os.getpgrp()}}))
identity('pipeline' if '--pipeline' in sys.argv else 'supervised' if '--supervised' in sys.argv else 'controller')
SOURCE=Path({str(source)!r})
sys.path[:0]=[str(SOURCE.parents[3]),str(SOURCE.parents[3]/'src')]
spec=importlib.util.spec_from_file_location('actual_pilot',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
runner=module.runner;runner.__file__=__file__;runner.WATCHDOG_SECONDS=1.5
reg=json.loads((Path(__file__).parent/'registration.json').read_text())
runner.admission=lambda *args,**kw:reg
runner.shutil.disk_usage=lambda path:SimpleNamespace(free=16*runner.p.GiB)
runner.subprocess.check_output=lambda *args,**kw:'0'*40
from palimpsest.storage import StorageBudget,StorageLimits
runner.d.restore_v2_budget=lambda reg:StorageBudget(
    [reg[key] for key in ('output','control_root','publication_root')],
    StorageLimits(max_bytes=64*runner.p.MiB,min_free_bytes=0),headroom_bytes=0)
runner.d.recheck_v2_inputs=lambda *args:None
runner.d.cleanup_owners=lambda root:[]
def harmless_run(path):
    signal.signal(signal.SIGTERM,signal.SIG_IGN);identity('pipeline-ready')
    while True:time.sleep(60)
module.m.run=harmless_run
raise SystemExit(runner.main(sys.argv[1:]))
''')
    def matching_live(record):
        try:
            fields=Path(f"/proc/{record['pid']}/stat").read_text().rsplit(')',1)[1].split()
            return (int(fields[19]),os.getpgid(record['pid']))==(record['starttime'],record['pgid']) and fields[0]!='Z'
        except (FileNotFoundError,ProcessLookupError):return False
    try:
        with (repo/'harness.log').open('wb') as log:
            result=subprocess.run(['timeout','--signal=KILL','5s',sys.executable,str(script)],
                cwd=repo,stdout=log,stderr=log,start_new_session=True,timeout=12)
        assert result.returncode!=0
        assert (repo/'pipeline-ready.json').exists(),(repo/'harness.log').read_text()
        records={role:json.loads((repo/(role+'.json')).read_text())
                 for role in ('controller','supervised','pipeline')}
        assert not {role:row for role,row in records.items() if matching_live(row)}
    finally:
        for role in ('pipeline-ready','pipeline','supervised','controller'):
            path=repo/(role+'.json')
            if path.exists():
                row=json.loads(path.read_text())
                if matching_live(row):
                    try:os.kill(row['pid'],signal.SIGKILL)
                    except ProcessLookupError:pass
