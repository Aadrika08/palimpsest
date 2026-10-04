"""Study wrapper rehearsals: real Git/child admission, no native preparation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import memory_decision_pilot as p
from scripts import memory_restore_diagnostic as d


@pytest.mark.parametrize('mode,filename,seconds', [
    ('diagnose', 'execute-diagnostic.py', '890s'),
    ('qualify', 'execute-qualification.py', '4890s'),
])
def test_new_study_rehearses_production_admission_and_exclusive_marker(
        tmp_path, monkeypatch, mode, filename, seconds):
    actual_repo = Path(__file__).resolve().parents[1]
    source = actual_repo/'docs/reports/memory-restore-study-v2-evidence'/filename
    spec = importlib.util.spec_from_file_location('study_wrapper_'+mode, source)
    launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
    evidence = tmp_path/'docs/reports/memory-restore-study-v2-evidence'
    evidence.mkdir(parents=True)
    workspace = tmp_path/'.superpowers/sdd/memory-restore-study-v2'/mode
    workspace.mkdir(parents=True)
    old = tmp_path/'.superpowers/sdd/memory-restore-diagnostic'
    old.mkdir(parents=True)
    old_marker = old/'diagnostic-launched.json'
    old_marker.write_text('consumed original invocation; immutable\n')
    (tmp_path/'.gitignore').write_text('.superpowers/\nruns/\n')
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    def commit():
        subprocess.run(['git','-C',str(tmp_path),'add','.'],check=True)
        subprocess.run(['git','-C',str(tmp_path),'-c','user.name=Fixture',
            '-c','user.email=fixture@example.test','commit','-qm','fixture'],check=True)
    commit()
    registered_head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=tmp_path,text=True).strip()
    registration_path = evidence/('registration.json' if mode=='diagnose' else 'qualification-registration.json')
    registration_path.write_text(json.dumps({
        'schema':'memory-restore-registration-v1', 'mode':mode,
        'repo':str(tmp_path), 'assets':str(tmp_path/'assets'),
        'history_root':str(tmp_path/'histories'), 'output':str(tmp_path/'runs'/mode),
        'python':sys.executable, 'implementation_commit':registered_head,
        'profile_sha256':d.PROFILE, 'protocol_sha256':p.TRAVEL_PROTOCOL_SHA256,
        'seconds_caps':list(d.CAPS[mode]),
    }))
    commit()
    monkeypatch.setattr(launcher, '__file__', str(evidence/filename))
    actual_run = subprocess.run
    calls = []
    def child(command, **kwargs):
        if command[0] != 'timeout':
            return actual_run(command, **kwargs)
        calls.append(command)
        assert command[3] == seconds
        assert command[-1] == str(registration_path)
        # Real subprocess runs the production main's early admission checks.
        # Only source/preparation are doubled; stop before root/job allocation.
        bootstrap = (
            'import sys; sys.path.insert(0,'+repr(str(actual_repo))+'); '
            'from scripts import memory_restore_diagnostic as d; '
            'd.__file__='+repr(str(tmp_path/'scripts/memory_restore_diagnostic.py'))+'; '
            'd.recheck_inputs=lambda *a: None\n'
            'def stop_before_native(*args, **kwargs):\n'
            '    print("production clean admission reached; no native allocation", flush=True)\n'
            '    raise SystemExit(0)\n'
            'd.p.preflight=stop_before_native\n'
            'raise SystemExit(d.main(["--registration",'+repr(str(registration_path))+']))\n'
        )
        # The source import uses actual source; fixture paths exercise admission.
        env = dict(kwargs['env'], PYTHONPATH=str(actual_repo/'src')+':'+str(actual_repo))
        return actual_run(command[:4]+[sys.executable,'-c',bootstrap],
                          **{**kwargs, 'env':env})
    monkeypatch.setattr(launcher.subprocess, 'run', child)
    assert launcher.main() == 0
    assert len(calls) == 1
    assert not (tmp_path/'runs'/mode).exists()
    assert (workspace/'launched.json').is_file()
    assert 'production clean admission reached' in (evidence/('native-invocation.log'
        if mode=='diagnose' else 'qualification-invocation.log')).read_text()
    assert old_marker.read_text() == 'consumed original invocation; immutable\n'
    # Published logs are committed so it is the exclusive marker, rather than
    # a dirty checkout or existing output, that prevents another invocation.
    commit()
    assert subprocess.check_output(['git','status','--porcelain'],cwd=tmp_path) == b''
    with pytest.raises(FileExistsError):
        launcher.main()
    assert len(calls) == 1
