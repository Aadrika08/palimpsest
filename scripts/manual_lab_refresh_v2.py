"""One registered manual lab QA invocation; no corrective attempt."""
import hashlib
import json
import importlib.metadata
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

from palimpsest.evaluate import bounded_process
from palimpsest.storage import StorageBudget, StorageLimits
from verify_afterimage import cleanup_check, process_identity, write_json
from verify_endurance import descendants, process

ROOT = Path.cwd()
PHASE = ROOT / '.superpowers/sdd/manual-lab-refresh-v2'
NODE = Path('/home/utkarsh/.local/share/mise/installs/node/24.21.0/bin/node')
NPM = NODE.parent / 'npm'
CACHE_UI = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/ui')
PORT = 8772
BASE = '40f4597'
REGISTRATION = ROOT / 'docs/plans/manual-lab-refresh-v2-registration.json'
PUBLICATION = ROOT / 'docs/reports/manual-lab-refresh-v2-evidence'
TITLE = 'actual local manual workflow, snapshots, sequential branches, comparison and export'
TEST = TITLE + '$'
ENV = {**os.environ, 'PATH': str(NODE.parent) + ':' + os.environ['PATH'],
       'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(ROOT / 'src') + ':' + str(ROOT / 'scripts'),
       'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
       'MKL_NUM_THREADS': '1', 'PALIMPSEST_LAB_URL': f'http://127.0.0.1:{PORT}',
       'PALIMPSEST_BROWSER': '/usr/bin/chromium'}
BUDGET = StorageBudget((PHASE, ROOT / 'ui/dist', ROOT / 'ui/test-results', PUBLICATION),
    StorageLimits(max_bytes=1024**3, min_free_bytes=2 * 1024**3), headroom_bytes=4 * 1024**2)
BUILD = [str(NPM), '--prefix', 'ui', 'run', 'build']
SERVER = [sys.executable, '-B', '-m', 'palimpsest', 'lab', '--port', str(PORT),
    '--runs', str(PHASE / 'runs'), '--exports', str(PHASE / 'exports'),
    '--storage-max-bytes', str(128 * 1024**2), '--min-free-bytes', str(2 * 1024**3),
    '--max-runs', '3', '--max-snapshots', '2', '--max-exports', '1', '--log-max-bytes', str(1024**2)]
BROWSER = [str(NODE), str(ROOT / 'ui/node_modules/@playwright/test/cli.js'), 'test', str(ROOT / 'ui/tests/lab.spec.ts'),
           '--config', str(ROOT / 'ui/playwright.config.ts'),
           '--grep', TEST, '--workers', '1', '--retries', '0', '--timeout', '180000']
SELECTION = [*BROWSER, '--list', '--reporter=json']
OBSERVED = {}


def pin(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def pins():
    upstream = subprocess.check_output(['git', '-C', 'upstream/fly-gym', 'ls-files'], text=True).splitlines()
    paths = [*sorted((ROOT / 'src/palimpsest').glob('*.py')), *sorted((ROOT / 'ui/src').glob('*')),
        *(ROOT / 'upstream/fly-gym' / name for name in upstream), ROOT / 'pyproject.toml', ROOT / 'uv.lock',
        ROOT / 'ui/package.json', ROOT / 'ui/package-lock.json', ROOT / 'ui/playwright.config.ts',
        ROOT / 'ui/tests/lab.spec.ts', ROOT / 'tests/test_manual_lab_refresh_v2.py', ROOT / 'docs/plans/manual-lab-refresh-v2.md', Path(__file__),
        ROOT / 'scripts/verify_afterimage.py', ROOT / 'scripts/verify_endurance.py']
    result = {str(path.relative_to(ROOT)): pin(path) for path in paths if path.is_file()}
    for path in (Path(sys.executable).resolve(), NODE.resolve(), Path(ENV['PALIMPSEST_BROWSER']),
                 Path('/usr/lib/chromium/chromium'), CACHE_UI / 'package-lock.json',
                 CACHE_UI / 'node_modules/.package-lock.json'):
        result[str(path)] = pin(path)
    package = json.loads((ROOT / 'ui/package.json').read_text())
    for name in {**package['dependencies'], **package['devDependencies']}:
        path = CACHE_UI / 'node_modules' / name / 'package.json'
        result[str(path)] = pin(path)
    for relative in ('playwright-core/lib/coreBundle.js', 'playwright/lib/runner/index.js', 'playwright/lib/common/index.js'):
        result[str(CACHE_UI / 'node_modules' / relative)] = pin(CACHE_UI / 'node_modules' / relative)
    return result


def cached_dependencies():
    assert pin(ROOT / 'ui/package-lock.json') == pin(CACHE_UI / 'package-lock.json'), 'Cached lock differs'
    package = json.loads((ROOT / 'ui/package.json').read_text())
    versions = {}
    for name, wanted in {**package['dependencies'], **package['devDependencies']}.items():
        actual = json.loads((CACHE_UI / 'node_modules' / name / 'package.json').read_text())['version']
        assert actual == wanted, f'Installed dependency version differs: {name}'
        versions[name] = actual
    lock = json.loads((ROOT / 'ui/package-lock.json').read_text())['packages']
    installed = json.loads((CACHE_UI / 'node_modules/.package-lock.json').read_text())['packages']
    for name, record in installed.items():
        assert name in lock and all(record.get(key) == lock[name].get(key) for key in ('version', 'resolved', 'integrity')), name
    return {'top_level_versions': versions, 'installed_manifest_entries': len(installed),
            'scope': 'Declared installed dependency metadata and lock equality; not a rehash of every cached package file.'}


def check_server_logs():
    for name in ('server.stdout.log', 'server.stderr.log'):
        path = PHASE / name
        if path.exists() and path.stat().st_size > 1024**2:
            raise RuntimeError('Server log limit exceeded')


def observe():
    for row in descendants(os.getpid()):
        OBSERVED[f"{row['pid']}:{row['start_ticks']}"] = row
    assert len(OBSERVED) <= 128, 'Owned process inventory exceeds frozen ceiling'
    write_json(PHASE / 'processes.json', list(OBSERVED.values()), BUDGET)


def checked_wait(child, seconds, start):
    until = time.monotonic() + seconds
    while child.poll() is None:
        observe()
        BUDGET.check(0, path=PHASE / 'result.json')
        if time.monotonic() > until or time.monotonic() - start > 320:
            raise TimeoutError('Frozen child/aggregate deadline exceeded')
        check_server_logs()
        time.sleep(.1)
    if child.returncode:
        raise RuntimeError(f'Child exited {child.returncode}')


def worker():
    start = time.monotonic()
    result = {'status': 'failed', 'process': process_identity(), 'qualification_claims': []}
    build = server = browser = None
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    write_json(PHASE / 'worker.json', result, BUDGET)
    try:
        registered = json.loads(REGISTRATION.read_text())
        assert pins() == registered['sources'], 'Source changed before selection'
        result['selection'] = bounded_process(SELECTION, PHASE / 'selection', 30, ENV, log_max_bytes=1024**2, storage_budget=BUDGET)
        assert result['selection']['status'] == 'completed' and result['selection']['returncode'] == 0, 'Selection preflight failed'
        report = json.loads((PHASE / 'selection/stdout.log').read_text())
        selected = []
        def collect(suite):
            selected.extend(suite.get('specs', []))
            for child in suite.get('suites', []):
                collect(child)
        for suite in report['suites']:
            collect(suite)
        assert not report.get('errors') and len(selected) == 1, 'Preflight must select exactly one test'
        spec = selected[0]
        assert spec['title'] == TITLE and spec['file'] == 'lab.spec.ts' and spec['line'] == 21 and len(spec['tests']) == 1, 'Unexpected selected test'
        result['selected_test'] = {key: spec[key] for key in ('title', 'file', 'line')}
        write_json(PHASE / 'worker.json', result, BUDGET)
        build = subprocess.Popen(BUILD, cwd=ROOT, env=ENV)
        checked_wait(build, 60, start)
        result['build_returncode'] = build.returncode
        result['build'] = {str(path.relative_to(ROOT)): pin(path) for path in sorted((ROOT / 'ui/dist').rglob('*')) if path.is_file()}
        with (PHASE / 'server.stdout.log').open('xb') as stdout, (PHASE / 'server.stderr.log').open('xb') as stderr:
            server = subprocess.Popen(SERVER, cwd=ROOT, env=ENV, stdout=stdout, stderr=stderr)
            result['server_pid'] = server.pid
            until = time.monotonic() + 30
            while True:
                observe()
                check_server_logs()
                if server.poll() is not None or time.monotonic() > until:
                    raise RuntimeError('Server failed readiness')
                try:
                    with urllib.request.urlopen(ENV['PALIMPSEST_LAB_URL'] + '/api/v1/session', timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    time.sleep(.1)
            browser = subprocess.Popen(BROWSER, cwd=ROOT / 'ui', env=ENV)
            checked_wait(browser, 180, start)
            result['browser_returncode'] = browser.returncode
        server.terminate()
        server.wait(timeout=20)
        check_server_logs()
        result['server_returncode'] = server.returncode
        # Uvicorn re-raises its handled SIGTERM after graceful application shutdown.
        assert server.returncode in (0, -signal.SIGTERM), 'Server shutdown failed'
        shutdown = (PHASE / 'server.stderr.log').read_text()
        assert 'Application shutdown complete.' in shutdown, 'Application shutdown did not complete'
        assert not any(message in shutdown for message in ('ERROR:', 'Traceback', 'Application shutdown failed')), 'Application shutdown/log failure'
        assert pins() == registered['sources'], 'Source changed during QA'
        from palimpsest.artifacts import _load
        runs = sorted((PHASE / 'runs').glob('*/recording/manifest.json'))
        assert len(runs) == 3, 'Expected exactly three admitted owners'
        result['runs'] = []
        for manifest_path in runs:
            data = _load(manifest_path.parent.parent)
            assert data['manifest']['controller'] == 'manual'
            result['runs'].append({'run_id': data['manifest']['run_id'], 'recorded_ticks': data['manifest']['recorded_ticks'],
                'files': {str(path.relative_to(data['run'])): pin(path) for path in sorted(data['run'].rglob('*')) if path.is_file()}})
        exports = sorted((PHASE / 'exports').glob('*.svg'))
        assert len(exports) == 1, 'Expected exactly one SVG'
        metadata = json.loads(ET.fromstring(exports[0].read_bytes()).find('{http://www.w3.org/2000/svg}metadata').text)
        assert metadata['run_id'] in {row['run_id'] for row in result['runs']}
        trace = _load(PHASE / 'runs' / metadata['run_id'])['episodes'][0]['trace']
        assert metadata['traces'][0]['points'] == trace
        line = ET.fromstring(exports[0].read_bytes()).find('.//{http://www.w3.org/2000/svg}polyline')
        assert [[float(value) for value in point.split(',')] for point in line.attrib['points'].split()] == trace
        for name in ('actual-lab-desktop.png', 'actual-lab-mobile.png'):
            assert (ROOT / 'ui/test-results' / name).is_file(), name
        closes = list((ROOT / 'ui/test-results').glob('*/owner-close.json'))
        assert len(closes) == 1
        close = json.loads(closes[0].read_text())
        assert close['http_status'] == 200 and close['response']['status'] == 'closed'
        result['artifacts'] = {str(path.relative_to(ROOT)): pin(path) for path in [*exports, *sorted((ROOT / 'ui/test-results').rglob('*'))] if path.is_file()}
        result.update(status='passed', storage=BUDGET.check(0, path=PHASE / 'worker.json'))
    except BaseException as error:
        result['status'] = 'failed'
        result['failure'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        try:
            observe()
        except BaseException as error:
            result.update(status='failed', cleanup_observation_failure={'type': type(error).__name__, 'message': str(error)})
        for child in (browser, server, build):
            try:
                if child is not None and child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=3)
            except BaseException as error:
                result['status'] = 'failed'
                result.setdefault('child_cleanup_failures', []).append({'pid': child.pid, 'type': type(error).__name__, 'message': str(error)})
        survivors = []
        for row in OBSERVED.values():
            current = process(row['pid'])
            if current and current['start_ticks'] == row['start_ticks'] and current['state'] != 'Z':
                survivors.append(row['pid'])
                try:
                    os.kill(row['pid'], signal.SIGKILL)
                except ProcessLookupError:
                    pass
        result['owned_survivors_requiring_kill'] = survivors
        if survivors:
            result['status'] = 'failed'
        result['elapsed_seconds'] = time.monotonic() - start
        if result['elapsed_seconds'] > 320:
            result.update(status='failed', deadline_exceeded=True)
        write_json(PHASE / 'worker.json', result, BUDGET)
    return 0 if result['status'] == 'passed' else 1


def register():
    # Pure metadata preparation: no Playwright, browser, owner, socket or lease.
    assert not REGISTRATION.exists() and not (PHASE / 'launched.json').exists()
    assert subprocess.check_output(['git', '-C', 'upstream/fly-gym', 'rev-parse', 'HEAD'], text=True).strip() == '8d964599119b420de67ee259434d273651a1a76d'
    registration = {'schema': 'manual-lab-refresh-v2', 'code_base': BASE,
        'sources': pins(), 'commands': {'selection': SELECTION, 'build': BUILD, 'server': SERVER, 'browser': BROWSER,
            'outer': ['timeout', '--signal=TERM', '--kill-after=5s', '350s', sys.executable, '-B', str(Path(__file__).resolve()), '--launch']},
        'native_owners_max': 3, 'exports_max': 1, 'selection_invocations_max': 1,
        'workflow_invocations_max': 1, 'corrective_attempts': 0, 'aggregate_seconds': 360,
        'supervisor_seconds': 330, 'worker_seconds': 320, 'publication_deadline_seconds': 345,
        'environment': {name: ENV[name] for name in ('MUJOCO_GL', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
        'python': {'path': sys.executable, 'version': sys.version}, 'node': pin(NODE),
        'runtime_versions': {name: importlib.metadata.version(name) for name in ('numpy', 'mujoco', 'torch', 'uvicorn')},
        'cached_dependencies': cached_dependencies(), 'qualification_claims': []}
    REGISTRATION.write_text(json.dumps(registration, indent=2, sort_keys=True) + '\n')
    return 0


def launch():
    start = time.monotonic()
    marker = PHASE / 'launched.json'
    assert not marker.exists(), 'Consumed allocation; do not retry'
    assert subprocess.check_output(['git', 'status', '--porcelain'], text=True) == '', 'Clean source required'
    assert not PHASE.exists() and not PUBLICATION.exists() and not (ROOT / 'ui/dist').exists() and not (ROOT / 'ui/test-results').exists()
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], check=True)
    assert subprocess.check_output([str(NODE), '--version'], text=True).strip() == 'v24.21.0'
    assert subprocess.check_output(['git', '-C', 'upstream/fly-gym', 'status', '--porcelain'], text=True) == ''
    registration = json.loads(REGISTRATION.read_text())
    assert registration['schema'] == 'manual-lab-refresh-v2' and registration['code_base'] == BASE
    assert pins() == registration['sources'], 'Registered source changed'
    assert all(registration['commands'][name] == command for name, command in (('selection', SELECTION), ('build', BUILD), ('server', SERVER), ('browser', BROWSER)))
    assert cached_dependencies() == registration['cached_dependencies']
    assert {name: importlib.metadata.version(name) for name in registration['runtime_versions']} == registration['runtime_versions']
    with socket.socket() as admission:
        admission.bind(('127.0.0.1', PORT))
    import shutil
    assert shutil.disk_usage(ROOT).free >= 4 * 1024**3
    PHASE.mkdir(parents=True)
    with marker.open('x') as stream:
        json.dump({'registration_sha256': pin(REGISTRATION)['sha256'],
                   'producer_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                   'started_wall_time_ns': time.time_ns(), 'aggregate_seconds': 360}, stream)
    result = {'status': 'failed', 'qualification_claims': []}
    old_handler = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        result['supervisor'] = bounded_process([sys.executable, '-B', str(Path(__file__)), '--worker'],
            PHASE / 'supervision', 330, ENV, log_max_bytes=1024**2, storage_budget=BUDGET)
        result['worker'] = json.loads((PHASE / 'worker.json').read_text())
        result['cleanup'] = cleanup_check(result['worker']['process'])
        result['observed_processes'] = json.loads((PHASE / 'processes.json').read_text())
        result['observed_live_survivors'] = []
        for row in result['observed_processes']:
            current = process(row['pid'])
            if current and current['start_ticks'] == row['start_ticks'] and current['state'] != 'Z':
                result['observed_live_survivors'].append(row['pid'])
                try:
                    os.kill(row['pid'], signal.SIGKILL)
                except ProcessLookupError:
                    pass
        with BUDGET.lock():
            result['lease_free'] = True
        assert result['supervisor']['status'] == 'completed' and result['supervisor']['returncode'] == 0 and result['worker']['status'] == 'passed' and result['cleanup']['passed']
        assert not result['observed_live_survivors'] and not result['worker']['owned_survivors_requiring_kill']
        assert pins() == registration['sources']
        assert time.monotonic() - start < 345
        result.update(status='passed', storage=BUDGET.check(0, path=PHASE / 'result.json'))
    except BaseException as error:
        result.update(status='failed', failure={'type': type(error).__name__, 'message': str(error)})
    try:
        return publish(result, start)
    finally:
        signal.signal(signal.SIGTERM, old_handler)


def publish(result, start):
    """Publish once; the canonical result stays pending until readback finishes."""
    completed_status = result['status']
    result['status'] = 'pending-publication' if completed_status == 'passed' else 'failed'
    try:
        write_json(PHASE / 'result.json', result, BUDGET)
        PUBLICATION.mkdir(exist_ok=True)  # StorageBudget.lock reserves this root.
        published = {}
        for source in [REGISTRATION, *sorted(PHASE.rglob('*')), *sorted((ROOT / 'ui/test-results').rglob('*'))]:
            if not source.is_file() or source.is_symlink() or source == PHASE / 'result.json' or '/runs/' in str(source) or '/exports/' in str(source):
                continue
            assert time.monotonic() - start < 345, 'Publication deadline exceeded'
            relative = source.relative_to(ROOT)
            destination = PUBLICATION / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            BUDGET.check(source.stat().st_size, path=destination)
            with destination.open('xb') as stream:
                stream.write(source.read_bytes())
            assert pin(destination) == pin(source)
            published[str(relative)] = pin(destination)
        result.update(publication=published, elapsed_seconds=time.monotonic() - start)
        assert result['elapsed_seconds'] < 345, 'Publication deadline exceeded'
        receipt = {**result, 'status': completed_status}
        write_json(PUBLICATION / 'publication.json', receipt, BUDGET)
        assert json.loads((PUBLICATION / 'publication.json').read_text()) == receipt, 'Publication readback differs'
        assert time.monotonic() - start < 345, 'Deadline exceeded during publication write/readback'
        result['status'] = completed_status
        result['elapsed_seconds'] = time.monotonic() - start
        write_json(PHASE / 'result.json', result, BUDGET)
        assert json.loads((PHASE / 'result.json').read_text()) == result, 'Canonical readback differs'
        assert time.monotonic() - start < 345, 'Deadline exceeded during canonical write/readback'
    except BaseException as error:
        result.update(status='failed', publication_failure={'type': type(error).__name__, 'message': str(error)},
                      elapsed_seconds=time.monotonic() - start)
        # Preserve failure where writing is still possible; never turn refusal into success.
        for path in (PHASE / 'result.json', PUBLICATION / 'publication.json'):
            try:
                write_json(path, result, BUDGET)
            except BaseException:
                pass
    print(json.dumps({'status': result['status'], 'elapsed_seconds': result.get('elapsed_seconds')}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    assert sys.argv[1:] in (['--register'], ['--launch'], ['--worker']), 'Use one explicit mode'
    raise SystemExit(register() if sys.argv[1:] == ['--register'] else worker() if sys.argv[1:] == ['--worker'] else launch())
