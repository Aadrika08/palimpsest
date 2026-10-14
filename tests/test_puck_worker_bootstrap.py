"""Real isolated stdlib children and authored source; no models or studies."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).absolute().parents[1]
SCRIPT = ROOT / 'scripts/puck_worker_bootstrap.py'


def api():
    assert SCRIPT.is_file(), 'Authenticated fresh-worker bootstrap missing'
    spec = importlib.util.spec_from_file_location('bootstrap_test_api', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def descriptor(path, relative):
    payload = path.read_bytes()
    return {'path': relative, 'size_bytes': len(payload), 'sha256': sha(payload)}


def fixture(tmp_path, body='return {"answer": 42}'):
    module = api()
    root = tmp_path / 'source'; root.mkdir()
    for name in ('src/palimpsest', 'scripts', 'upstream/fly-gym'):
        (root / name).mkdir(parents=True)
    bootstrap = root / 'scripts/puck_worker_bootstrap.py'
    bootstrap.write_bytes(SCRIPT.read_bytes())
    holder = root / 'src/palimpsest/puck_execution_files.py'
    holder.write_bytes((ROOT / 'src/palimpsest/puck_execution_files.py').read_bytes())
    (root / 'src/palimpsest/__init__.py').write_text('"""Authored package."""\n')
    (root / 'src/palimpsest/puck_worker_preflight.py').write_text(
        'def preflight(admission):\n    ' + body.replace('\n', '\n    ') + '\n')
    paths = ('scripts/puck_worker_bootstrap.py', 'src/palimpsest/__init__.py',
             'src/palimpsest/puck_execution_files.py', 'src/palimpsest/puck_worker_preflight.py')
    # The running Python image is held, never copied or hard-linked for fixtures.
    image = Path('/proc/self/exe').resolve()
    registration = {'kind': 'puck-worker-source-bootstrap-v1', 'version': 1,
        'source_root': str(root), 'source_files': [descriptor(root / p, p) for p in paths],
        'modules': [{'name': 'palimpsest', 'path': 'src/palimpsest/__init__.py'},
                    {'name': 'palimpsest.puck_execution_files', 'path': 'src/palimpsest/puck_execution_files.py'},
                    {'name': 'palimpsest.puck_worker_preflight', 'path': 'src/palimpsest/puck_worker_preflight.py'}],
        'namespaces': [], 'runtime': {'root': str(image.parent),
            'files': [descriptor(image, image.name)], 'python_version': '3.11.15'},
        'environment': {'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C.UTF-8', 'LANG': 'C.UTF-8'}, 'cwd': str(root),
        'argv_prefix': [], 'qualification_claims': [], 'executable': False}
    manifest = tmp_path / 'registration.json'
    bootstrap_sha = sha(bootstrap.read_bytes())
    registration['argv_prefix'] = module.command(sys.executable, str(bootstrap),
        bootstrap_sha, str(manifest), '0' * 64)[:-1]
    return module, registration, manifest, bootstrap, bootstrap_sha


def launch(tmp_path, *, body='return {"answer": 42}', change=None, command_change=None,
           environment_change=None):
    module, registration, manifest, bootstrap, bootstrap_sha = fixture(tmp_path, body)
    if change:
        change(registration)
    payload = raw(registration); manifest.write_bytes(payload)
    command = module.command(sys.executable, str(bootstrap), bootstrap_sha, str(manifest), sha(payload))
    if command_change:
        command_change(command)
    environment = dict(registration['environment'])
    if environment_change:
        environment_change(environment)
    result = subprocess.run(command, cwd=registration['cwd'], env=environment,
        capture_output=True, timeout=15, text=True, start_new_session=True)
    return result, registration


def test_real_fresh_worker_executes_authenticated_source_and_emits_no_grants(tmp_path):
    result, registration = launch(tmp_path)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['entry_result'] == {'answer': 42}
    assert receipt['python_version'] == '3.11.15'
    assert receipt['interpreter_object_bound'] is True
    assert {r['name'] for r in receipt['loaded_modules']} == {'_puck_held_file_bootstrap', 'palimpsest', 'palimpsest.puck_worker_preflight'}
    assert receipt['process']['pid'] == receipt['process']['pgid']
    assert receipt['environment_sha256'] == sha(raw(registration['environment']))
    for key in ('runtime_qualified', 'dependencies_qualified', 'native_authorized', 'collection_authorized', 'executable'):
        assert receipt[key] is False
    assert receipt['qualification_claims'] == []
    assert not list(Path(registration['source_root']).rglob('*.pyc'))


@pytest.mark.parametrize('defect', ['source-sha', 'python-version', 'argv', 'environment', 'duplicate-module', 'omit-module'])
def test_bad_admission_never_executes_local_entry(tmp_path, defect):
    def change(reg):
        if defect == 'source-sha': reg['source_files'][-1]['sha256'] = '0' * 64
        elif defect == 'python-version': reg['runtime']['python_version'] = '3.11.14'
        elif defect == 'argv': reg['argv_prefix'][3] = '-Sx'
        elif defect == 'environment': reg['environment']['EXTRA'] = 'not actually supplied'
        elif defect == 'duplicate-module': reg['modules'].append(dict(reg['modules'][0]))
        else: reg['modules'] = reg['modules'][:1]
    env_change = (lambda env: env.pop('EXTRA')) if defect == 'environment' else None
    result, _ = launch(tmp_path, body='raise AssertionError("ENTRY_RAN")', change=change,
                       environment_change=env_change)
    assert result.returncode != 0
    assert result.stdout == ''
    assert 'ENTRY_RAN' not in result.stderr
    reason = {'source-sha':'input file bytes or size differ',
        'python-version':'interpreter pin/version', 'argv':'Frozen worker command',
        'environment':'environment/cwd differs', 'duplicate-module':'source module mapping',
        'omit-module':'Complete Python module mapping'}[defect]
    assert reason in result.stderr


@pytest.mark.parametrize('body, reason', [
    ('import numpy\nreturn {}', 'Unregistered local or external dependency'),
    ('from palimpsest import unregistered\nreturn {}', 'Unregistered local or external dependency'),
    ('import sys\nsys.modules[__name__].preflight = lambda _: {}\nreturn {}', 'function code binding changed'),
    ('import sys\nsys.meta_path.clear()\nreturn {}', 'Source import dispatch changed'),
    ('import pathlib\np = pathlib.Path(__file__)\np.write_bytes(p.read_bytes() + b"# drift\\n")\nreturn {}', 'input file edge or metadata changed'),
])
def test_foreign_import_or_source_dispatch_drift_is_terminal(tmp_path, body, reason):
    result, _ = launch(tmp_path, body=body)
    assert result.returncode != 0
    assert result.stdout == ''
    assert reason in result.stderr


def test_seed_rejects_wrong_bootstrap_digest_before_code_runs(tmp_path):
    result, _ = launch(tmp_path, command_change=lambda args: args.__setitem__(-3, '0' * 64))
    assert result.returncode != 0
    assert result.stdout == ''


def test_unregistered_code_namespace_entry_refuses_before_entry(tmp_path):
    def change(reg):
        (Path(reg['source_root']) / 'src/palimpsest/foreign.py').write_text('raise AssertionError("FOREIGN_RAN")')
    result, _ = launch(tmp_path, body='raise AssertionError("ENTRY_RAN")', change=change)
    assert result.returncode != 0
    assert result.stdout == ''
    assert 'ENTRY_RAN' not in result.stderr


def test_command_elements_preserve_existing_4096_byte_limit(tmp_path):
    module, reg, manifest, bootstrap, bootstrap_sha = fixture(tmp_path)
    args = module.command(sys.executable, str(bootstrap), bootstrap_sha, str(manifest), 'f' * 64)
    assert max(len(x.encode()) for x in args) <= 4096
    assert args[1:5] == ['-I', '-B', '-S', '-c']


def test_registered_scripts_namespace_loads_from_held_bytes(tmp_path):
    def change(reg):
        path = Path(reg['source_root']) / 'scripts/probe.py'
        path.write_text('def value():\n    return 43\n')
        reg['source_files'].append(descriptor(path, 'scripts/probe.py'))
        reg['source_files'].sort(key=lambda row: row['path'])
        reg['modules'].append({'name':'scripts.probe', 'path':'scripts/probe.py'})
        reg['namespaces'] = [{'name':'scripts', 'path':'scripts'}]
    result, _ = launch(tmp_path, body='from scripts.probe import value\nreturn {"answer": value()}', change=change)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['entry_result'] == {'answer':43}
    assert {'scripts', 'scripts.probe'} <= {row['name'] for row in receipt['loaded_modules']}


@pytest.mark.parametrize('body, reason', [
    ('import sys,types\nsys.modules["palimpsest.unregistered"] = types.ModuleType("palimpsest.unregistered")\nreturn {}', 'Unregistered module cache'),
    ('import sys\nsys.modules[__name__].__spec__.name = "foreign"\nreturn {}', 'module dispatch'),
])
def test_module_cache_and_spec_replacements_cannot_bypass_source_binding(tmp_path, body, reason):
    result, _ = launch(tmp_path, body=body)
    assert result.returncode != 0
    assert reason in result.stderr


def test_byte_identical_other_interpreter_inode_is_not_running_image(tmp_path):
    def change(reg):
        root = tmp_path / 'runtime'; root.mkdir()
        (root / 'python3.11').write_bytes(Path('/proc/self/exe').read_bytes())
        reg['runtime']['root'] = str(root)
    result, _ = launch(tmp_path, body='raise AssertionError("ENTRY_RAN")', change=change)
    assert result.returncode != 0
    assert 'Running interpreter object differs' in result.stderr
    assert 'ENTRY_RAN' not in result.stderr


def test_caught_failed_operation_cannot_be_rearmed_by_restoring_environment(tmp_path):
    body = ('import os\nos.environ["DRIFT"] = "yes"\n'
            'try:\n    admission.snapshot()\nexcept RuntimeError:\n    pass\n'
            'del os.environ["DRIFT"]\nreturn {}')
    result, _ = launch(tmp_path, body=body)
    assert result.returncode != 0
    assert 'Bootstrap inactive or poisoned' in result.stderr
    assert result.stdout == ''


def test_interpreter_identity_refuses_before_source_holder_module_exec(tmp_path):
    marker = tmp_path / 'holder-ran'
    def change(reg):
        runtime = tmp_path / 'runtime'; runtime.mkdir()
        (runtime / 'python3.11').write_bytes(Path('/proc/self/exe').read_bytes())
        reg['runtime']['root'] = str(runtime)
        path = Path(reg['source_root']) / 'src/palimpsest/puck_execution_files.py'
        path.write_bytes(path.read_bytes() + ('\nPath('+repr(str(marker))+').write_text("ran")\n').encode())
        next(r for r in reg['source_files'] if r['path'].endswith('puck_execution_files.py')).update(
            descriptor(path, 'src/palimpsest/puck_execution_files.py'))
    result, _ = launch(tmp_path, change=change)
    assert result.returncode != 0
    assert 'Running interpreter object differs' in result.stderr
    assert not marker.exists()


@pytest.mark.parametrize('variant', ['class', 'imported-alias', 'method-wrapper', 'support-holder'])
def test_every_loaded_local_dispatch_slot_remains_bound(tmp_path, variant):
    def change(reg):
        root = Path(reg['source_root'])
        sources = {'scripts/helper.py': 'def value():\n    return 43\n',
            'scripts/probe.py': 'from scripts.helper import value\nclass Probe:\n    @staticmethod\n    def value():\n        return 43\n'}
        for relative, text in sources.items():
            path = root / relative; path.write_text(text)
            reg['source_files'].append(descriptor(path, relative))
            reg['modules'].append({'name':relative[:-3].replace('/', '.'), 'path':relative})
        reg['source_files'].sort(key=lambda row:row['path'])
        reg['namespaces'] = [{'name':'scripts', 'path':'scripts'}]
    body = 'from scripts import probe\n'
    if variant == 'class':
        body += ('class Replacement:\n    @staticmethod\n    def value():\n        return 99\n'
                 'probe.Probe = Replacement\nreturn {"answer": probe.Probe.value()}')
    elif variant == 'imported-alias':
        body += 'probe.value = lambda: 99\nreturn {"answer": probe.value()}'
    elif variant == 'method-wrapper':
        body += 'probe.Probe.value = classmethod(probe.Probe.value)\nreturn {}'
    else:
        body += ('import sys\nsys.modules["_puck_held_file_bootstrap"].HeldCollectionFiles.recheck = lambda _: None\n'
                 'return {}')
    result, _ = launch(tmp_path, body=body, change=change)
    assert result.returncode != 0
    assert result.stdout == ''
    assert 'binding changed' in result.stderr
