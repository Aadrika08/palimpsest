"""Authored ordinary-CPU transport fixtures; never import the vendor runtime."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/observe_puck_cpu_runtime_characterization.py'
OBSERVER = 'scripts/observe_puck_cpu_runtime_characterization.py'
PARENT = 'scripts/characterize_puck_cpu_runtime.py'
WORKER = 'scripts/characterize_puck_runtime_imports.py'
OUTPUT = 'runs/puck-cpu-runtime-characterization-03'
ENVIRONMENT = dict(PATH='/usr/bin:/bin', LANG='C.UTF-8', LC_ALL='C.UTF-8',
                   PYTHONDONTWRITEBYTECODE='1')


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def pin(path, root):
    raw = (root / path).read_bytes()
    return dict(path=path, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def api():
    assert SCRIPT.is_file(), 'Ordinary CPU characterization observer is not implemented'
    spec = importlib.util.spec_from_file_location('distributed_observer_tests', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, monkeypatch, body='print("AUTHORED transport", flush=True)\n'):
    module = api()
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'runs').mkdir()
    (tmp_path / OBSERVER).write_bytes(SCRIPT.read_bytes())
    (tmp_path / PARENT).write_text(body)
    (tmp_path / WORKER).write_text('# AUTHORED inert worker; observer never imports it\n')
    config = dict(kind='puck-cpu-runtime-characterization-v2', version=2, output=OUTPUT,
                  site_root='runs/puck-cpu-install-01/site',
                  sources=[pin(path, tmp_path) for path in sorted((OBSERVER, PARENT, WORKER))],
                  inputs=[], roles={}, limits={}, environment={}, expected_versions={})
    path = tmp_path / 'configuration.json'
    return module, path, config


def save(path, config):
    raw = encoded(config)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def receipt_path(root):
    return root / (OUTPUT + '-external-cli-transport.json')


def assert_false_authority(result):
    assert all(result[name] is False for name in (
        'runtime_qualified', 'native_authorized', 'collection_authorized',
        'study_authorized', 'executable'))
    assert result['qualification_claims'] == []


@pytest.mark.parametrize('code', [0, 7])
def test_separately_executes_fixed_parent_and_preserves_transport(tmp_path, monkeypatch, code):
    body = ('import json,os,resource,sys,time\n'
            'print(json.dumps(dict(argv=sys.argv[1:],environment=dict(os.environ),'
            'isolated=sys.flags.isolated,no_site=sys.flags.no_site,bytecode=sys.dont_write_bytecode)),flush=True)\n'
            'print("AUTHORED stderr",file=sys.stderr,flush=True)\ntime.sleep(.08)\nsys.exit(' + str(code) + ')\n')
    module, path, config = fixture(tmp_path, monkeypatch, body)
    sha = save(path, config)
    # Previous observations are never consumed or overwritten by this wrapper.
    old = tmp_path / 'runs/puck-cpu-runtime-characterization-02-external-cli.stdout'
    old.write_bytes(b'preserved old observation')
    before = len(os.listdir('/proc/self/fd'))
    result = module.observe(path, sha)
    assert result['kind'] == 'puck-cpu-characterization-cli-transport-v1'
    assert result['version'] == 1 and result['allocation_id'] == 3
    assert result['root'] == str(tmp_path)
    assert result['configuration'] == dict(path='configuration.json', size_bytes=path.stat().st_size, sha256=sha)
    assert result['command'] == [module.PYTHON, '-I', '-S', '-B', str(tmp_path / PARENT),
                                 '--configuration', str(path), '--sha256', sha]
    assert result['environment'] == ENVIRONMENT
    assert result['observed_returncode'] == code and result['timed_out'] is False
    assert math.isfinite(result['elapsed_seconds']) and 0 < result['elapsed_seconds'] < 10
    identity = result['parent_identity']
    assert set(identity) == {'pid', 'start_ticks'} and identity['pid'] > 0 and identity['start_ticks'] > 0
    assert identity in result['sampled_identities'] and len(result['sampled_identities']) <= 64
    assert result['sampled_survivors'] == [] and result['sampled_cleanup_only'] is True
    assert 'not exhaustive' in result['sampling_limitation']
    assert_false_authority(result)
    saved = receipt_path(tmp_path).read_bytes()
    assert json.loads(saved) == result
    assert saved == (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    assert len(saved) <= 64 * 1024
    for name in ('stdout', 'stderr'):
        row = result[name]
        assert row['path'] == OUTPUT + '-external-cli.' + name
        raw = (tmp_path / row['path']).read_bytes()
        assert row['size_bytes'] == len(raw) and row['sha256'] == hashlib.sha256(raw).hexdigest()
        assert stat.S_IMODE((tmp_path / row['path']).stat().st_mode) == 0o600
    observed = json.loads((tmp_path / result['stdout']['path']).read_bytes())
    assert observed == dict(argv=['--configuration', str(path), '--sha256', sha],
                            environment=ENVIRONMENT, isolated=1, no_site=1, bytecode=True)
    assert old.read_bytes() == b'preserved old observation'
    assert stat.S_IMODE(receipt_path(tmp_path).stat().st_mode) == 0o600
    captured = {p: p.read_bytes() for p in (tmp_path / 'runs').iterdir() if p.is_file()}
    with pytest.raises(FileExistsError):
        module.observe(path, sha)
    assert all(p.read_bytes() == raw for p, raw in captured.items())
    assert len(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('field,value', [
    ('kind', 'puck-cpu-runtime-characterization-v1'), ('version', 1), ('version', True),
    ('output', 'runs/puck-cpu-runtime-characterization-02'), ('output', '/tmp/arbitrary'),
    ('site_root', 'runs/other/site'), ('entrypoint', PARENT), ('allocation_id', 3),
])
def test_closed_configuration_identity_refused_before_launch(tmp_path, monkeypatch, field, value):
    module, path, config = fixture(tmp_path, monkeypatch, 'raise AssertionError("must not execute")\n')
    config[field] = value
    with pytest.raises(ValueError):
        module.observe(path, save(path, config))
    assert list((tmp_path / 'runs').iterdir()) == []


@pytest.mark.parametrize('change', ['digest', 'compact', 'relative', 'dotdot', 'outside', 'symlink', 'parent-symlink',
                                   'double-slash', 'dot'])
def test_configuration_bytes_and_canonical_root_path_are_bound(tmp_path, monkeypatch, change):
    module, path, config = fixture(tmp_path, monkeypatch)
    sha = save(path, config)
    if change == 'digest':
        sha = '0' * 64
    elif change == 'compact':
        raw = json.dumps(config, sort_keys=True, separators=(',', ':')).encode() + b'\n'
        path.write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()
    elif change == 'relative':
        path = Path('configuration.json')
    elif change == 'dotdot':
        path = tmp_path / 'scripts/../configuration.json'
    elif change == 'outside':
        outside = tmp_path.parent / (tmp_path.name + '-outside.json')
        outside.write_bytes(path.read_bytes())
        path = outside
    elif change == 'symlink':
        link = tmp_path / 'linked.json'
        link.symlink_to(path)
        path = link
    elif change == 'double-slash':
        path = str(tmp_path) + '//configuration.json'
    elif change == 'dot':
        path = str(tmp_path) + '/./configuration.json'
    else:
        real = tmp_path / 'real'
        real.mkdir()
        path.rename(real / 'configuration.json')
        (tmp_path / 'linked').symlink_to(real, target_is_directory=True)
        path = tmp_path / 'linked/configuration.json'
    with pytest.raises((ValueError, OSError)):
        module.observe(path, sha)
    assert list((tmp_path / 'runs').iterdir()) == []


@pytest.mark.parametrize('change', ['missing-parent', 'missing-worker', 'missing-observer', 'duplicate',
                                   'unsorted', 'size', 'hash', 'extra-field', 'dotdot', 'absolute', 'symlink'])
def test_source_rows_are_unique_canonical_and_authenticated_before_launch(tmp_path, monkeypatch, change):
    module, path, config = fixture(tmp_path, monkeypatch, 'raise AssertionError("must not execute")\n')
    target = {'missing-parent': PARENT, 'missing-worker': WORKER, 'missing-observer': OBSERVER}.get(change)
    if target:
        config['sources'] = [row for row in config['sources'] if row['path'] != target]
    elif change == 'duplicate':
        config['sources'].append(dict(config['sources'][0]))
    elif change == 'unsorted':
        config['sources'].reverse()
    elif change == 'size':
        config['sources'][0]['size_bytes'] += 1
    elif change == 'hash':
        config['sources'][0]['sha256'] = '0' * 64
    elif change == 'extra-field':
        config['sources'][0]['ignored'] = True
    elif change == 'dotdot':
        config['sources'][0]['path'] = 'scripts/../' + config['sources'][0]['path']
    elif change == 'absolute':
        config['sources'][0]['path'] = str(tmp_path / config['sources'][0]['path'])
    else:
        original = tmp_path / config['sources'][0]['path']
        moved = tmp_path / 'source-real.py'
        original.rename(moved)
        original.symlink_to(moved)
    with pytest.raises((ValueError, OSError)):
        module.observe(path, save(path, config))
    assert list((tmp_path / 'runs').iterdir()) == []


@pytest.mark.parametrize('suffix', ['', '-external-cli.stdout', '-external-cli.stderr', '-external-cli-transport.json'])
@pytest.mark.parametrize('symlink', [False, True])
def test_all_reserved_paths_refuse_existing_files_and_symlinks(tmp_path, monkeypatch, suffix, symlink):
    module, path, config = fixture(tmp_path, monkeypatch)
    reserved = tmp_path / (OUTPUT + suffix)
    if symlink:
        reserved.symlink_to(tmp_path / 'absent-target')
    else:
        reserved.write_bytes(b'preserved')
    with pytest.raises(FileExistsError):
        module.observe(path, save(path, config))
    assert reserved.is_symlink() if symlink else reserved.read_bytes() == b'preserved'
    assert len(list((tmp_path / 'runs').iterdir())) == 1


def test_runs_directory_symlink_cannot_redirect_receipts(tmp_path, monkeypatch):
    module, path, config = fixture(tmp_path, monkeypatch)
    (tmp_path / 'runs').rmdir()
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (tmp_path / 'runs').symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        module.observe(path, save(path, config))
    assert list(elsewhere.iterdir()) == []


def test_launch_failure_still_retains_false_authority_receipt_and_empty_streams(tmp_path, monkeypatch):
    module, path, config = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(module, 'PYTHON', str(tmp_path / 'absent-interpreter'))
    result = module.observe(path, save(path, config))
    assert result['observed_returncode'] is None and result['parent_identity'] is None
    assert result['timed_out'] is False and result['error_type'] == 'FileNotFoundError'
    assert result['sampled_identities'] == result['sampled_survivors'] == []
    assert result['stdout']['size_bytes'] == result['stderr']['size_bytes'] == 0
    assert_false_authority(result)
    assert json.loads(receipt_path(tmp_path).read_bytes()) == result


def test_timeout_kills_and_reaps_only_owned_parent_and_sampled_child(tmp_path, monkeypatch):
    body = ('import os,signal,subprocess,sys,time\n'
            'child=subprocess.Popen([sys.executable,"-I","-S","-c","import time;time.sleep(30)"])\n'
            'signal.signal(signal.SIGCHLD,lambda *args: child.wait())\n'
            'print(str(os.getpid())+" "+str(child.pid),flush=True)\n'
            'try: time.sleep(30)\nfinally: child.kill();child.wait()\n')
    module, path, config = fixture(tmp_path, monkeypatch, body)
    monkeypatch.setattr(module, 'NORMAL_SECONDS', .25)
    result = module.observe(path, save(path, config))
    pids = [int(value) for value in (tmp_path / result['stdout']['path']).read_text().split()]
    assert result['timed_out'] is True and result['observed_returncode'] == -signal.SIGKILL
    assert set(pids) <= {row['pid'] for row in result['sampled_identities']}
    assert result['sampled_survivors'] == [] and result['elapsed_seconds'] < 6
    assert all(module.process_identity(pid) is None for pid in pids)
    assert_false_authority(result)


def test_stale_sampled_pid_is_never_signalled(tmp_path, monkeypatch):
    module = api()
    identity = dict(pid=os.getpid(), start_ticks=1)
    assert module.process_identity(os.getpid())['start_ticks'] != 1
    assert module.terminate_identity(identity) is False
    assert module.process_identity(os.getpid()) is not None


def test_sample_identity_limit_becomes_failed_transport_and_cleans_owned_parent(tmp_path, monkeypatch):
    module, path, config = fixture(tmp_path, monkeypatch, 'import time\ntime.sleep(30)\n')
    monkeypatch.setattr(module, 'MAX_IDENTITIES', 0)
    result = module.observe(path, save(path, config))
    assert result['error_type'] == 'ValueError' and result['observed_returncode'] == -signal.SIGKILL
    assert result['sampled_survivors'] == []
    assert_false_authority(result)


def test_sampled_cleanup_limitation_does_not_claim_atomic_pid_reuse_proof(tmp_path, monkeypatch):
    module, path, config = fixture(tmp_path, monkeypatch)
    result = module.observe(path, save(path, config))
    assert 'not atomic' in result['sampling_limitation']


def test_source_directory_token_is_not_a_file_pin(tmp_path, monkeypatch):
    module, path, config = fixture(tmp_path, monkeypatch)
    config['sources'].append(dict(path='.', size_bytes=1, sha256='0' * 64))
    config['sources'].sort(key=lambda row: row['path'])
    with pytest.raises(ValueError):
        module.observe(path, save(path, config))
    assert list((tmp_path / 'runs').iterdir()) == []


def cli(tmp_path, module, path, sha, flags=('-I', '-S', '-B'), extra_environment=None):
    environment = dict(ENVIRONMENT, **(extra_environment or {}))
    return subprocess.run([module.PYTHON, *flags, str(tmp_path / OBSERVER),
                           '--configuration', str(path), '--sha256', sha],
                          cwd=tmp_path, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)


@pytest.mark.parametrize('code', [0, 9])
def test_cli_reports_authored_exit_and_inherited_resource_limits(tmp_path, monkeypatch, code):
    body = ('import json,resource,sys\n'
            'print(json.dumps({name:resource.getrlimit(getattr(resource,"RLIMIT_"+name))'
            ' for name in ("NOFILE","AS","FSIZE")}),flush=True)\nsys.exit(' + str(code) + ')\n')
    module, path, config = fixture(tmp_path, monkeypatch, body)
    result = cli(tmp_path, module, path, save(path, config))
    assert result.returncode == (0 if code == 0 else 1), result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['observed_returncode'] == code
    observed = json.loads((tmp_path / receipt['stdout']['path']).read_bytes())
    assert observed == dict(NOFILE=[40000, 40000], AS=[8 * 1024**3] * 2, FSIZE=[16 * 1024**2] * 2)
    assert_false_authority(receipt)


@pytest.mark.parametrize('flags,extra', [(('-S', '-B'), {}), (('-I', '-B'), {}),
                                      (('-I', '-S'), {}), (('-I', '-S', '-B'), {'LD_LIBRARY_PATH': '/tmp/authored'}),
                                      (('-I', '-S', '-B'), {'LD_PRELOAD': '/tmp/authored-absent.so'})])
def test_cli_requires_original_isolated_interpreter_and_clean_loader_environment(tmp_path, monkeypatch, flags, extra):
    module, path, config = fixture(tmp_path, monkeypatch)
    result = cli(tmp_path, module, path, save(path, config), flags, extra)
    assert result.returncode != 0
    assert list((tmp_path / 'runs').iterdir()) == []


def test_cli_rejects_a_different_interpreter_before_allocating(tmp_path, monkeypatch):
    module, path, config = fixture(tmp_path, monkeypatch)
    result = subprocess.run(['/usr/bin/python', '-I', '-S', '-B', str(tmp_path / OBSERVER),
                             '--configuration', str(path), '--sha256', save(path, config)],
                            cwd=tmp_path, env=ENVIRONMENT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
    assert result.returncode != 0
    assert list((tmp_path / 'runs').iterdir()) == []


@pytest.mark.parametrize('spelling', ['/./', '//'])
def test_cli_preserves_raw_configuration_spelling_for_canonicality_check(tmp_path, monkeypatch, spelling):
    module, path, config = fixture(tmp_path, monkeypatch, 'raise AssertionError("must not execute")\n')
    sha = save(path, config)
    supplied = str(tmp_path) + spelling + 'configuration.json'
    result = cli(tmp_path, module, supplied, sha)
    assert result.returncode != 0
    assert b'Canonical absolute CPU configuration' in result.stderr
    assert list((tmp_path / 'runs').iterdir()) == []


def test_cli_file_limit_preserves_bounded_raw_stream_and_failure_receipt(tmp_path, monkeypatch):
    body = 'import os\nfor i in range(18): os.write(1,b"x"*(1024**2))\n'
    module, path, config = fixture(tmp_path, monkeypatch, body)
    result = cli(tmp_path, module, path, save(path, config))
    assert result.returncode == 1, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['observed_returncode'] != 0
    assert receipt['stdout']['size_bytes'] == 16 * 1024**2
    assert receipt['stderr']['size_bytes'] <= 16 * 1024**2
    assert len(receipt_path(tmp_path).read_bytes()) <= 64 * 1024
    assert_false_authority(receipt)


def test_api_file_limit_preserves_failure_receipt_instead_of_unbounded_read(tmp_path, monkeypatch):
    body = 'import os\nfor i in range(18): os.write(1,b"x"*(1024**2))\n'
    module, path, config = fixture(tmp_path, monkeypatch, body)
    result = module.observe(path, save(path, config))
    assert result['observed_returncode'] != 0
    assert result['stdout']['size_bytes'] <= 16 * 1024**2
    assert result['stderr']['size_bytes'] <= 16 * 1024**2
    assert json.loads(receipt_path(tmp_path).read_bytes()) == result
    assert_false_authority(result)
