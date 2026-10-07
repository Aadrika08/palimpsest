"""Launcher admission/orchestration checks; no native owner or retained decoding."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from test_restore_v2_driver import registration


def launcher():
    source = Path(__file__).resolve().parents[1]/'docs/reports/restore-qualification-v2-evidence/execute-restore-v2.py'
    spec = importlib.util.spec_from_file_location('restore_v2_launcher', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('driver_code,audit_code,passed', [(0,0,True),(0,0,False),(1,0,True),(0,1,True)])
def test_pipeline_needs_driver_independent_audit_and_terminal_close(tmp_path, monkeypatch,
        driver_code, audit_code, passed):
    module = launcher(); reg = registration(tmp_path); path = tmp_path/'registration.json'
    root = Path(reg['output'])
    monkeypatch.setattr(module, 'admission', lambda path: reg)
    calls = []
    def driver(argv):
        calls.append(('driver', argv, os.getpid()))
        root.mkdir(parents=True)
        return driver_code
    from scripts import memory_restore_v2_audit as a
    def audit(value):
        calls.append(('audit', value, os.getpid()))
        (root/'scientific-close.json').write_text(json.dumps({'narrow_restore_passed':passed}))
        return audit_code
    monkeypatch.setattr(d, 'main', driver)
    monkeypatch.setattr(a, 'audit', audit)
    assert module.pipeline(path) == (0 if driver_code == audit_code == 0 and passed else 1)
    assert calls == [('driver',['--registration',str(path)],os.getpid()),('audit',path,os.getpid())]


@pytest.mark.parametrize('dirty', ['none', 'parent', 'child', 'pass', 'overflow', 'late', 'publication',
                                  'owned-stop', 'owned-survivor', 'owned-reused', 'invalidate'])
def test_real_git_and_child_admission_exclusive_marker(tmp_path, monkeypatch, dirty):
    module = launcher(); actual_repo = Path(__file__).resolve().parents[1]
    evidence = tmp_path/'docs/reports/restore-qualification-v2-evidence'; evidence.mkdir(parents=True)
    source = evidence/'execute-restore-v2.py'
    shutil.copyfile(module.__file__, source)
    (tmp_path/'.gitignore').write_text('.superpowers/\nruns/\n')
    (tmp_path/'README').write_text('committed\n')
    old = tmp_path/'.superpowers/sdd/memory-restore-study-v2/diagnose/launched.json'
    old.parent.mkdir(parents=True); old.write_text('consumed original; immutable\n')
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    def commit():
        subprocess.run(['git','-C',str(tmp_path),'add','.'],check=True)
        subprocess.run(['git','-C',str(tmp_path),'-c','user.name=Fixture',
                        '-c','user.email=fixture@example.test','commit','-qm','fixture'],check=True)
    commit()
    reg = registration(tmp_path); reg['python'] = sys.executable
    reg['implementation_commit'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=tmp_path,text=True).strip()
    path = evidence/'registration.json'; path.write_text(json.dumps(reg)); commit()
    monkeypatch.setattr(module, '__file__', str(source))
    monkeypatch.setattr(d, '__file__', str(tmp_path/'scripts/memory_restore_diagnostic.py'))
    # Source/native preflight is doubled; both production Git admission checks run.
    monkeypatch.setattr(d, 'recheck_v2_inputs', lambda *a: None)
    disk_usage = shutil.disk_usage
    monkeypatch.setattr(shutil, 'disk_usage', lambda path: disk_usage(path)._replace(free=20*p.GiB))
    kills = []; alive = [True]
    if dirty in ('owned-stop', 'owned-survivor', 'owned-reused'):
        from scripts import memory_waypoint_study as w
        monkeypatch.setattr(w, 'proc_identity', lambda pid: (2 if dirty == 'owned-reused' else 1,999))
        def kill(pgid, signum):
            kills.append((pgid, signum))
            if signum == module.signal.SIGKILL and dirty == 'owned-stop':
                alive[0] = False
        monkeypatch.setattr(w, 'os', SimpleNamespace(killpg=kill))
        monkeypatch.setattr(w, 'time', SimpleNamespace(sleep=lambda seconds: None))
        monkeypatch.setattr(d, 'owner_exited', lambda owner: dirty == 'owned-reused' or not alive[0])
    if dirty == 'invalidate':
        replace = d.replace_control
        def refuse_false_close(path, value, storage):
            if Path(path).name == 'scientific-close.json':
                raise ValueError('false close publication failure fixture')
            return replace(path, value, storage)
        monkeypatch.setattr(d, 'replace_control', refuse_false_close)
    if dirty == 'publication':
        storage = d.restore_v2_budget(reg); check = storage.check
        def fail_publication(size, *, path):
            if Path(path).name == 'native-stdout.log':
                raise ValueError('publication storage failure fixture')
            return check(size, path=path)
        monkeypatch.setattr(storage, 'check', fail_publication)
        monkeypatch.setattr(d, 'restore_v2_budget', lambda reg: storage)
    actual_popen = module.subprocess.Popen; calls = []
    def child(command, **kwargs):
        if command[0] != 'timeout':
            return actual_popen(command, **kwargs)
        calls.append(command)
        assert command[:4] == ['timeout','--signal=TERM','--kill-after=5','890s']
        assert command[-2:] == ['--pipeline',str(path)]
        for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
            assert kwargs['env'][name] == '1'
        assert kwargs['env']['MUJOCO_GL'] == 'egl'
        if dirty == 'child':
            (tmp_path/'README').write_text('changed after parent admission\n')
        bootstrap = (
            'import importlib.util,sys;sys.path.insert(0,'+repr(str(actual_repo))+');'
            'from scripts import memory_restore_diagnostic as d;'
            'd.__file__='+repr(str(tmp_path/'scripts/memory_restore_diagnostic.py'))+';'
            'd.recheck_v2_inputs=lambda *a:None\n'
            'def stop(*a,**kw):\n'
            ' print("production clean admission reached; no native allocation",flush=True)\n'
            ' raise SystemExit(0)\n'
            'd.p.preflight=stop\n'
            'spec=importlib.util.spec_from_file_location("fixture_launcher",'+repr(str(source))+')\n'
            'm=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\n'
            'raise SystemExit(m.main(["--pipeline",'+repr(str(path))+']))\n')
        if dirty in ('pass', 'overflow', 'late', 'publication', 'owned-stop', 'owned-survivor', 'owned-reused', 'invalidate'):
            # Separate launcher-failure fixtures, rather than native/driver proof.
            bootstrap = (
                'import json,os,time;from pathlib import Path;'
                'root=Path('+repr(reg['output'])+');root.mkdir(parents=True);'
                '(root/"execution.json").write_text(json.dumps({"readout_deadline_monotonic":'
                'time.monotonic()'+('-1' if dirty in ('late','invalidate') else '+100')+'}));'
                '(root/"scientific-close.json").write_text(json.dumps({"narrow_restore_passed":True}));'
                'os.write(1,b"x"*'+str(2*p.MiB if dirty == 'overflow' else 1)+')')
            if dirty in ('owned-stop', 'owned-survivor', 'owned-reused'):
                bootstrap += (';run=root/"stage/runs/fake";run.mkdir(parents=True);'
                    '(run/"owner.json").write_text(json.dumps({"pid":999,"starttime":1,"pgid":999,"run_id":"fake"}));'
                    'raise SystemExit('+('1' if dirty == 'owned-stop' else '0')+')')
        env = dict(kwargs['env'], PYTHONPATH=str(actual_repo/'src')+':'+str(actual_repo))
        return actual_popen(command[:4]+[sys.executable,'-c',bootstrap], **{**kwargs,'env':env})
    monkeypatch.setattr(module.subprocess, 'Popen', child)
    if dirty == 'parent':
        (tmp_path/'README').write_text('dirty before parent admission\n')
        with pytest.raises(ValueError, match='clean'):
            module.main([])
        assert not calls and not (Path(reg['control_root'])/'launched.json').exists()
    else:
        # The pass case doubles scientific data; admission alone never passes.
        passed = dirty in ('pass', 'owned-reused')
        assert module.main([]) == (0 if passed else 1)
        assert len(calls) == 1
        stdout = (evidence/'native-stdout.log').read_text() if dirty != 'publication' else ''
        stderr = (evidence/'native-stderr.log').read_text() if dirty != 'publication' else ''
        if dirty == 'none':
            assert 'production clean admission reached' in stdout
        elif dirty == 'child':
            assert 'clean committed checkout' in stderr
            assert 'production clean admission reached' not in stdout
        result = p.read_json(evidence/'invocation-result.json')
        assert (result['native_exit_code'] == 0) is passed
        if dirty == 'invalidate':
            assert not (Path(reg['output'])/'scientific-close.json').exists()
            assert p.read_json(Path(reg['output'])/'scientific-close.invalidated.json')['narrow_restore_passed'] is True
        elif dirty in ('pass', 'overflow', 'late', 'publication', 'owned-stop', 'owned-survivor', 'owned-reused'):
            assert p.read_json(Path(reg['output'])/'scientific-close.json')['narrow_restore_passed'] is passed
            assert (Path(reg['control_root'])/'stdout.log').stat().st_size <= p.MiB
        else:
            assert result['pipeline_exit_code'] != 0
            assert not Path(reg['output']).exists()
        if dirty in ('owned-stop', 'owned-survivor'):
            assert kills == [(999,module.signal.SIGTERM),(999,module.signal.SIGKILL)]
            assert result['cleanup'][0]['matching_owner_exited'] is (dirty == 'owned-stop')
        elif dirty == 'owned-reused':
            assert kills == []
            assert result['cleanup'][0]['status'] == 'pid-reused-do-not-touch'
            assert result['cleanup'][0]['matching_owner_exited'] is True
        assert (Path(reg['control_root'])/'launched.json').exists()
        commit()
        assert subprocess.check_output(['git','status','--porcelain'],cwd=tmp_path) == b''
        with pytest.raises(ValueError if dirty in ('pass', 'overflow', 'late', 'publication',
                           'owned-stop', 'owned-survivor', 'owned-reused', 'invalidate') else FileExistsError):
            module.main([])
        assert len(calls) == 1
    assert old.read_text() == 'consumed original; immutable\n'
