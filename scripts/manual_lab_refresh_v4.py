"""Formal manual lab refresh v4: one registered, serialized real-browser session.

Modes (exactly one):
  --register            write the prospective registration (metadata only)
  --launch              consume the registered allocation once; no retry
  --worker              internal; started by --launch under a bounded supervisor
  --rehearse SECONDS CYCLE
                        bounded rehearsal: SECONDS endurance window in CYCLE-second
                        cycles; never consumes the allocation or publishes evidence

Phases: browser preflight (versions, /tmp and /dev/shm free space,
``npm run test:browser-shm``), one test-selection listing, build, the
acceptance browser suite (inspection, snapshot, branches with a goal edit,
comparison, action and policy replay, SVG and bundle export, disconnect/reload
recovery, measured cadence), then the mixed browser endurance on a fresh
server with forced-GC renderer samples. This module judges the decided cadence
tolerance and listener growth from raw recorded evidence.
"""
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import time
import urllib.request

from palimpsest.evaluate import bounded_process
from palimpsest.storage import StorageBudget, StorageLimits
from verify_afterimage import cleanup_check, process_identity, write_json
from verify_endurance import descendants, process

ROOT = Path.cwd()
SCHEMA = 'manual-lab-refresh-v4'
BASE = '5456b33'
FLY_GYM = '8d964599119b420de67ee259434d273651a1a76d'
PHASE = ROOT / '.superpowers/sdd/manual-lab-refresh-v4'
PUBLICATION = ROOT / 'docs/reports/manual-lab-refresh-v4-evidence'
REGISTRATION = ROOT / 'docs/plans/manual-lab-refresh-v4-registration.json'
NODE = Path('/home/utkarsh/.local/share/mise/installs/node/24.21.0/bin/node')
NPM = NODE.parent / 'npm'
CHROMIUM = Path('/usr/bin/chromium')
PORTS = {'acceptance': 8774, 'endurance': 8775}
GiB, MiB = 1024**3, 1024**2

# Decided cadence acceptance (mirrors CADENCE_ACCEPTANCE in ui/tests/measurement.ts).
CADENCE = {'emission_hz': 30, 'display_mean_hz_min': 29, 'interarrival_p99_ms_max': 70,
           'acknowledgement_p95_ms_below': 150}
# Listener growth: growth while streaming that a forced GC reclaims is allowed;
# idle post-GC growth from the early to the late third of cycles is not.
LISTENER_ALLOWANCE = {'absolute': 64, 'fraction': .10, 'min_cycles': 3}

ENDURANCE_SECONDS, CYCLE_SECONDS, STREAM_SECONDS = 3600, 120, 4
FLOORS = {'tmp_free_bytes': 2 * GiB, 'dev_shm_free_bytes': 1 * GiB, 'project_initial_free_bytes': 10 * GiB,
          'project_free_bytes': 4 * GiB}
SERVER_CAPS = {'acceptance': {'storage_max_bytes': 2 * GiB, 'max_runs': 32, 'max_snapshots': 4, 'max_exports': 4},
               'endurance': {'storage_max_bytes': 4 * GiB, 'max_runs': 128, 'max_snapshots': 2, 'max_exports': 1}}
CONTROL_MAX_BYTES = 7 * GiB
PROCESS_CEILING = 2048
ACCEPTANCE_TESTS = [
    ('lab.spec.ts', 'actual local manual workflow, snapshots, sequential branches, comparison and export'),
    ('lab.spec.ts', 'actual replay jobs recover without samples and expose controls, reports and authenticated bundle'),
    ('lab.spec.ts', 'actual trajectory overlay isolation and keyboard error recovery'),
    ('lab.spec.ts', 'actual memory inspector, U-only branch and evidence-linked route annotations'),
    ('lab.spec.ts', 'measured browser responsiveness and actual display cadence'),
    ('lab.spec.ts', 'actual declared task inspection and snapshot continuation: exploration-landmarks'),
    ('lab.spec.ts', 'actual declared task inspection and snapshot continuation: encoder-homing'),
    ('recorded-snapshots.spec.ts', 'closed recorded runs recover snapshots and branch from the selected source'),
]
ENDURANCE_TEST = ('lab-endurance.spec.ts', 'mixed browser endurance with forced-GC renderer samples')
OBSERVED = {}


def configure(phase=None, endurance_seconds=ENDURANCE_SECONDS, cycle_seconds=CYCLE_SECONDS):
    """Bind paths, budget and commands; rehearsals bind a separate phase."""
    global PHASE, BUDGET, ENV, COMMANDS, ENDURANCE, CYCLE
    PHASE = phase or ROOT / '.superpowers/sdd/manual-lab-refresh-v4'
    ENDURANCE, CYCLE = endurance_seconds, cycle_seconds
    BUDGET = StorageBudget((PHASE, ROOT / 'ui/dist', ROOT / 'ui/test-results', PUBLICATION),
                           StorageLimits(max_bytes=CONTROL_MAX_BYTES, min_free_bytes=FLOORS['project_free_bytes']),
                           headroom_bytes=16 * MiB)
    ENV = {**os.environ, 'PATH': str(NODE.parent) + ':' + os.environ['PATH'], 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONPATH': str(ROOT / 'src') + ':' + str(ROOT / 'scripts'), 'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '1',
           'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PALIMPSEST_BROWSER': str(CHROMIUM), 'TMPDIR': '/tmp'}
    playwright = [str(NODE), str(ROOT / 'ui/node_modules/@playwright/test/cli.js'), 'test', '--config',
                  str(ROOT / 'ui/playwright.config.ts'), '--workers', '1', '--retries', '0']
    COMMANDS = {
        'preflight': [str(NPM), '--prefix', 'ui', 'run', 'test:browser-shm'],
        'selection': [*playwright, '--list', '--reporter=json', 'tests/lab.spec.ts', 'tests/recorded-snapshots.spec.ts',
                      'tests/lab-endurance.spec.ts'],
        'build': [str(NPM), '--prefix', 'ui', 'run', 'build'],
        'acceptance': [*playwright, '--reporter=list,json', '--timeout', '180000', '--output',
                       str(PHASE / 'acceptance/test-results'), 'tests/lab.spec.ts', 'tests/recorded-snapshots.spec.ts'],
        'endurance': [sys.executable, '-I', str(ROOT / 'scripts/lab_chromium_resource_probe.py'), '--out',
                      str(PHASE / 'endurance/chromium-resources.jsonl'), '--shm-dir', '/dev/shm', '--interval', '5',
                      '--max-bytes', str(4 * MiB), '--timeout', str(endurance_seconds + 900), '--',
                      *playwright, '--reporter=list,json', '--timeout', str((endurance_seconds + 600) * 1000), '--output',
                      str(PHASE / 'endurance/test-results'), 'tests/lab-endurance.spec.ts']}
    for name in ('acceptance', 'endurance'):
        caps = SERVER_CAPS[name]
        COMMANDS[name + '_server'] = [sys.executable, '-B', '-m', 'palimpsest', 'lab', '--port', str(PORTS[name]),
            '--runs', str(PHASE / name / 'runs'), '--exports', str(PHASE / name / 'exports'),
            '--storage-max-bytes', str(caps['storage_max_bytes']), '--min-free-bytes', str(FLOORS['project_free_bytes']),
            '--max-runs', str(caps['max_runs']), '--max-snapshots', str(caps['max_snapshots']),
            '--max-exports', str(caps['max_exports']), '--log-max-bytes', str(MiB)]


configure()


def environment(name):
    """Per-phase browser environment; the measured test enforces the cadence tolerance."""
    env = {**ENV, 'PALIMPSEST_LAB_URL': f'http://127.0.0.1:{PORTS[name]}'}
    if name == 'acceptance':
        env.update(PALIMPSEST_MEASURE_UI='1', PALIMPSEST_REQUIRE_UI_TARGETS='1',
                   PLAYWRIGHT_JSON_OUTPUT_FILE=str(PHASE / 'acceptance/playwright-results.json'))
    else:
        env.update(PALIMPSEST_ENDURANCE_SECONDS=str(ENDURANCE), PALIMPSEST_ENDURANCE_CYCLE_SECONDS=str(CYCLE),
                   PALIMPSEST_ENDURANCE_STREAM_SECONDS=str(STREAM_SECONDS),
                   PLAYWRIGHT_JSON_OUTPUT_FILE=str(PHASE / 'endurance/playwright-results.json'))
    return env


def deadlines(endurance_seconds=None):
    endurance = ENDURANCE if endurance_seconds is None else endurance_seconds
    phases = {'preflight': 60, 'selection': 60, 'build': 90, 'acceptance': 900, 'endurance': endurance + 900}
    worker = sum(phases.values()) + 120
    return {'phases': phases, 'worker': worker, 'supervisor': worker + 60, 'publication': worker + 150,
            'outer': worker + 240}


def pin(path):
    raw = Path(path).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def pins():
    upstream = subprocess.check_output(['git', '-C', 'upstream/fly-gym', 'ls-files'], cwd=ROOT, text=True).splitlines()
    paths = [*sorted((ROOT / 'src/palimpsest').glob('*.py')), *sorted((ROOT / 'ui/src').glob('*')),
             *sorted((ROOT / 'ui/tests').glob('*')), *(ROOT / 'upstream/fly-gym' / name for name in upstream),
             ROOT / 'pyproject.toml', ROOT / 'uv.lock', ROOT / 'ui/package.json', ROOT / 'ui/package-lock.json',
             ROOT / 'ui/playwright.config.ts', ROOT / 'ui/index.html', ROOT / 'ui/vite.config.ts', ROOT / 'ui/tsconfig.json',
             ROOT / 'tests/test_manual_lab_refresh_v4.py', ROOT / 'docs/plans/manual-lab-refresh-v4.md',
             ROOT / 'scripts/manual_lab_refresh_v4.py', ROOT / 'scripts/lab_chromium_resource_probe.py',
             ROOT / 'scripts/verify_afterimage.py', ROOT / 'scripts/verify_endurance.py']
    result = {str(path.relative_to(ROOT)): pin(path) for path in paths if path.is_file()}
    for path in (Path(sys.executable).resolve(), NODE.resolve(), CHROMIUM, Path('/usr/lib/chromium/chromium')):
        result[str(path)] = pin(path)
    return result


def installed_dependencies():
    """Installed UI packages must equal the lock (version, resolved, integrity)."""
    lock = json.loads((ROOT / 'ui/package-lock.json').read_text())['packages']
    installed = json.loads((ROOT / 'ui/node_modules/.package-lock.json').read_text())['packages']
    for name, record in installed.items():
        assert name in lock and all(record.get(key) == lock[name].get(key) for key in ('version', 'resolved', 'integrity')), name
    package = json.loads((ROOT / 'ui/package.json').read_text())
    versions = {name: json.loads((ROOT / 'ui/node_modules' / name / 'package.json').read_text())['version']
                for name in {**package['dependencies'], **package['devDependencies']}}
    assert all(versions[name] == wanted for name, wanted in {**package['dependencies'], **package['devDependencies']}.items())
    return {'top_level_versions': dict(sorted(versions.items())), 'installed_manifest_entries': len(installed)}


def free_bytes(path):
    stats = os.statvfs(path)
    return stats.f_bavail * stats.f_frsize


def shm_floors():
    """Continuing floors on Chromium's shared-memory filesystem and the shared /tmp."""
    observed = {'tmp_free_bytes': free_bytes('/tmp'), 'dev_shm_free_bytes': free_bytes('/dev/shm')}
    for name, value in observed.items():
        if value < FLOORS[name]:
            raise RuntimeError(f'Browser filesystem floor reached: {name}={value} < {FLOORS[name]}')
    return observed


def version(command):
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT, timeout=20).strip()
    except (OSError, subprocess.SubprocessError) as error:
        return f'unavailable: {type(error).__name__}'


def preflight_facts():
    """Recorded browser preflight; refuses below the browser filesystem floors."""
    facts = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **shm_floors(),
             'project_free_bytes': shutil.disk_usage(ROOT).free, 'floors': FLOORS,
             'browsers': {'chromium': version([str(CHROMIUM), '--version']),
                          'chromium_binary_sha256': pin('/usr/lib/chromium/chromium')['sha256'],
                          'playwright': json.loads((ROOT / 'ui/node_modules/playwright-core/package.json').read_text())['version'],
                          'node': version([str(NODE), '--version'])},
             'chromium_shared_memory': 'Playwright default --disable-dev-shm-usage is ignored; regions live on /dev/shm'}
    if facts['project_free_bytes'] < FLOORS['project_initial_free_bytes']:
        raise RuntimeError('Project free space below the initial floor')
    return facts


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)] if ordered else None


def cadence_verdict(windows, acknowledgements):
    """Decided tolerance from raw delivered-display timestamps.

    windows: [(timestamps_ms, started_ms, ended_ms)], pooled; mean = events / window.
    """
    count = sum(len(stamps) for stamps, _, _ in windows)
    duration = sum(ended - started for _, started, ended in windows)
    gaps = [b - a for stamps, _, _ in windows for a, b in zip(stamps, stamps[1:])]
    mean = count * 1000 / duration if duration > 0 else None
    p50, p99, ack95 = percentile(gaps, .5), percentile(gaps, .99), percentile(acknowledgements, .95)
    passed = (mean is not None and mean >= CADENCE['display_mean_hz_min'] and p99 is not None
              and p99 <= CADENCE['interarrival_p99_ms_max'] and ack95 is not None
              and ack95 < CADENCE['acknowledgement_p95_ms_below'])
    return {'criteria': CADENCE, 'windows': len(windows), 'display_updates': count, 'window_ms': duration,
            'mean_hz': mean, 'interarrival_p50_ms': p50, 'interarrival_p99_ms': p99,
            'acknowledgement_count': len(acknowledgements), 'acknowledgement_p95_ms': ack95, 'passed': passed}


def growth_verdict(idle, streaming, absolute, fraction, min_cycles):
    if len(idle) < min_cycles:
        return {'passed': False, 'reason': f'fewer than {min_cycles} idle post-GC samples', 'idle_gc': idle}
    third = max(1, len(idle) // 3)
    early, late = statistics.median(idle[:third]), statistics.median(idle[-third:])
    allowance = max(absolute, fraction * early)
    reclaimed = [raw - after for raw, after in zip(streaming, idle)]
    return {'passed': late - early <= allowance, 'idle_gc_early_median': early, 'idle_gc_late_median': late,
            'unreclaimed_growth': late - early, 'allowance': allowance, 'idle_gc': idle, 'streaming_raw': streaming,
            'streaming_minus_idle_gc': reclaimed,
            'rule': 'idle post-GC late-third median may exceed early-third median by at most max(absolute, fraction*early)'}


def listener_verdict(cycles):
    """Gate on listeners; DOM nodes and JS heap are recorded with the same rule."""
    def series(key, metric):
        return [cycle[key][metric] for cycle in cycles]
    result = {'listeners': growth_verdict(series('idle_gc', 'listeners'), series('streaming_raw', 'listeners'),
                                          LISTENER_ALLOWANCE['absolute'], LISTENER_ALLOWANCE['fraction'],
                                          LISTENER_ALLOWANCE['min_cycles'])}
    result['recorded_only'] = {
        'dom_nodes': growth_verdict(series('idle_gc', 'nodes'), series('streaming_raw', 'nodes'), 256, .10, 3),
        'js_heap_used': growth_verdict(series('idle_gc', 'js_heap_used'), series('streaming_raw', 'js_heap_used'),
                                       8 * MiB, .25, 3)}
    result['passed'] = result['listeners']['passed']
    return result


def expected_cycles(seconds, cycle_seconds):
    return int(seconds // cycle_seconds)


def evaluate(phase):
    """Judge the recorded evidence; every listed check must pass."""
    checks = {}
    performance = sorted((phase / 'acceptance/test-results').glob('*/ui-performance.json'))
    if len(performance) == 1:
        report = json.loads(performance[0].read_text())
        checks['measured_cadence'] = cadence_verdict(
            [(report['raw_timestamps_ms']['dom_sample_commit'], report['started_ms'], report['ended_ms'])],
            [command['ack_ms'] for command in report['commands']])
    else:
        checks['measured_cadence'] = {'passed': False, 'reason': f'{len(performance)} ui-performance reports'}
    closes = [json.loads(path.read_text()) for path in sorted((phase / 'acceptance/test-results').glob('*/owner-close.json'))]
    checks['owner_closes'] = {'count': len(closes), 'passed': bool(closes) and all(
        close['http_status'] == 200 and close['response']['status'] == 'closed' for close in closes)}
    exports = {suffix: len(list((phase / 'acceptance/exports').glob('*' + suffix))) for suffix in ('.svg', '.zip')}
    checks['exports'] = {**exports, 'passed': exports['.svg'] >= 1 and exports['.zip'] >= 1}
    for name, wanted in (('acceptance', len(ACCEPTANCE_TESTS)), ('endurance', 1)):
        path = phase / name / 'playwright-results.json'
        stats = json.loads(path.read_text()).get('stats', {}) if path.is_file() else {}
        checks[name + '_tests'] = {**stats, 'passed': stats.get('expected') == wanted and not stats.get('unexpected')
                                   and not stats.get('skipped') and not stats.get('flaky')}
    endurance = sorted((phase / 'endurance/test-results').glob('*/lab-endurance.json'))
    if len(endurance) == 1:
        data = json.loads(endurance[0].read_text())
        cycles = data['cycles']
        configuration = data['configuration']
        wanted = expected_cycles(configuration['seconds'], configuration['cycle_seconds'])
        checks['endurance_cycles'] = {'count': len(cycles), 'expected': wanted, 'configuration': configuration,
            'reloads': sum(bool(cycle.get('reloaded')) for cycle in cycles),
            'replays': sorted({cycle['replay']['mode'] for cycle in cycles}),
            'passed': len(cycles) == wanted and configuration['seconds'] == ENDURANCE and configuration['cycle_seconds'] == CYCLE
                      and all(cycle['replay']['result'].get('status') == 'passed' for cycle in cycles)}
        checks['endurance_failures'] = {'network': data['network_failures'], 'page_errors': data['page_errors'],
                                        'passed': not data['network_failures'] and not data['page_errors']}
        checks['endurance_cadence'] = cadence_verdict(
            [(c['cadence']['display_commits_ms'], c['cadence']['started_ms'], c['cadence']['ended_ms']) for c in cycles],
            [value for c in cycles for value in c['cadence']['acknowledgement_raw_ms']])
        checks['listener_growth'] = listener_verdict(cycles)
    else:
        checks['endurance'] = {'passed': False, 'reason': f'{len(endurance)} endurance reports'}
    return {'passed': all(check.get('passed') for check in checks.values()), 'checks': checks,
            'recorded': {'recording_writers': writer_statistics(phase)}}


def writer_statistics(phase):
    """Per-owner recording writer statistics from supervisor.json; evidence, not a gate.

    Live owners report background statistics; replay jobs record synchronously
    (``recording_writer`` is null). Writer errors already fail their owner's close.
    """
    rows = []
    for path in sorted(phase.glob('*/runs/*/supervisor.json')):
        stats = json.loads(path.read_text()).get('recording_writer')
        rows.append({'phase': path.parts[-4], 'run_id': path.parent.name, 'recording_writer': stats})
    live = [row['recording_writer'] for row in rows if row['recording_writer']]
    return {'owners': len(rows), 'background': len(live), 'synchronous': len(rows) - len(live),
            'written_items': sum(stats['written_items'] for stats in live),
            'max_queued_items': max((stats['max_queued_items'] for stats in live), default=0),
            'backpressure_events': sum(stats['backpressure_events'] for stats in live),
            'backpressure_seconds': sum(stats['backpressure_seconds'] for stats in live),
            'errors': [row for row in rows if row['recording_writer'] and row['recording_writer'].get('error')],
            'per_owner': rows}


def observe():
    for row in descendants(os.getpid()):
        OBSERVED[f"{row['pid']}:{row['start_ticks']}"] = row
    assert len(OBSERVED) <= PROCESS_CEILING, 'Owned process inventory exceeds frozen ceiling'


def checked_wait(child, seconds, start, worker_deadline, require_success=True):
    """Wait under floors and deadlines. Browser phases record a failed exit and
    continue, so one consumed session always yields acceptance and endurance
    evidence; the evaluation then fails it."""
    until, last = time.monotonic() + seconds, 0.
    while child.poll() is None:
        if time.monotonic() - last >= 1.:
            observe()
            shm_floors()
            BUDGET.check(0, path=PHASE / 'worker.json')
            check_server_logs()
            last = time.monotonic()
        if time.monotonic() > until or time.monotonic() - start > worker_deadline:
            raise TimeoutError('Frozen child/aggregate deadline exceeded')
        time.sleep(.1)
    if child.returncode and require_success:
        raise RuntimeError(f'Child exited {child.returncode}')
    return child.returncode


def check_server_logs():
    for path in PHASE.glob('*/server.*.log'):
        if path.stat().st_size > MiB:
            raise RuntimeError('Server log limit exceeded')


def serve(name, start, worker_deadline, result):
    """One fresh lab server for one browser phase; graceful shutdown is required."""
    (PHASE / name).mkdir(parents=True, exist_ok=True)
    with (PHASE / name / 'server.stdout.log').open('xb') as stdout, (PHASE / name / 'server.stderr.log').open('xb') as stderr:
        server = subprocess.Popen(COMMANDS[name + '_server'], cwd=ROOT, env=ENV, stdout=stdout, stderr=stderr)
        try:
            until = time.monotonic() + 30
            while True:
                observe()
                if server.poll() is not None or time.monotonic() > until:
                    raise RuntimeError(f'{name} server failed readiness')
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{PORTS[name]}/api/v1/session', timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    time.sleep(.1)
            browser = subprocess.Popen(COMMANDS[name], cwd=ROOT / 'ui', env=environment(name))
            try:
                checked_wait(browser, deadlines()['phases'][name], start, worker_deadline, require_success=False)
            finally:
                if browser.poll() is None:
                    browser.terminate()
                    browser.wait(timeout=10)
            result[name + '_browser_returncode'] = browser.returncode
        finally:
            if server.poll() is None:
                server.terminate()
                server.wait(timeout=20)
    result[name + '_server_returncode'] = server.returncode
    assert server.returncode in (0, -signal.SIGTERM), f'{name} server shutdown failed'
    log = (PHASE / name / 'server.stderr.log').read_text()
    assert 'Application shutdown complete.' in log, f'{name} application shutdown did not complete'
    assert not any(text in log for text in ('ERROR:', 'Traceback', 'Application shutdown failed')), f'{name} server log failure'


def worker(registered=True):
    start = time.monotonic()
    limit = deadlines()['worker']
    result = {'status': 'failed', 'process': process_identity(), 'qualification_claims': [], 'endurance_seconds': ENDURANCE}
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    write_json(PHASE / 'worker.json', result, BUDGET)
    try:
        if registered:
            assert pins() == json.loads(REGISTRATION.read_text())['sources'], 'Source changed before preflight'
        result['preflight'] = preflight_facts()
        result['preflight']['browser_shm_check'] = bounded_process(COMMANDS['preflight'], PHASE / 'preflight',
            deadlines()['phases']['preflight'], ENV, log_max_bytes=MiB, storage_budget=BUDGET)
        assert result['preflight']['browser_shm_check']['returncode'] == 0, 'Browser shared-memory preflight failed'
        selection = bounded_process(COMMANDS['selection'], PHASE / 'selection', deadlines()['phases']['selection'],
                                    {**ENV, 'PALIMPSEST_ENDURANCE_SECONDS': '1'}, log_max_bytes=4 * MiB, storage_budget=BUDGET)
        assert selection['status'] == 'completed' and selection['returncode'] == 0, 'Selection listing failed'
        result['selected'] = selected_tests(json.loads((PHASE / 'selection/stdout.log').read_text()))
        assert sorted(result['selected']) == sorted([*ACCEPTANCE_TESTS, ENDURANCE_TEST]), 'Unexpected test selection'
        write_json(PHASE / 'worker.json', result, BUDGET)
        build = subprocess.Popen(COMMANDS['build'], cwd=ROOT, env=ENV)
        checked_wait(build, deadlines()['phases']['build'], start, limit)
        result['build'] = {str(path.relative_to(ROOT)): pin(path) for path in sorted((ROOT / 'ui/dist').rglob('*')) if path.is_file()}
        for name in ('acceptance', 'endurance'):
            result[name + '_started_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            serve(name, start, limit, result)
            result[name + '_floors'] = shm_floors()
            write_json(PHASE / 'worker.json', result, BUDGET)
        if registered:
            assert pins() == json.loads(REGISTRATION.read_text())['sources'], 'Source changed during session'
        result['evaluation'] = evaluate(PHASE)
        assert result['evaluation']['passed'], 'Acceptance evaluation failed'
        result.update(status='passed', storage=BUDGET.check(0, path=PHASE / 'worker.json'))
    except BaseException as error:
        result['status'] = 'failed'
        result['failure'] = {'type': type(error).__name__, 'message': str(error)}
        if 'evaluation' not in result:
            try:
                result['evaluation'] = evaluate(PHASE)
            except BaseException as failure:
                result['evaluation_failure'] = {'type': type(failure).__name__, 'message': str(failure)}
    finally:
        cleanup(result, start, limit)
        write_json(PHASE / 'worker.json', result, BUDGET)
    return 0 if result['status'] == 'passed' else 1


def selected_tests(report):
    selected = []
    def collect(suite):
        for spec in suite.get('specs', []):
            selected.append((spec['file'], spec['title']))
        for child in suite.get('suites', []):
            collect(child)
    assert not report.get('errors'), 'Selection reported errors'
    for suite in report['suites']:
        collect(suite)
    return selected


def cleanup(result, start, limit):
    try:
        observe()
    except BaseException as error:
        result.update(status='failed', cleanup_observation_failure={'type': type(error).__name__, 'message': str(error)})
    rows = list(OBSERVED.values())
    deadline = min(time.monotonic() + 2., start + limit)
    while time.monotonic() < deadline and any(live(row) for row in rows):
        time.sleep(.05)
    survivors = [row['pid'] for row in rows if live(row)]
    for pid in survivors:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    result['observed_processes'] = len(rows)
    result['owned_survivors_requiring_kill'] = survivors
    if survivors:
        result['status'] = 'failed'
    result['elapsed_seconds'] = time.monotonic() - start
    if result['elapsed_seconds'] > limit:
        result.update(status='failed', deadline_exceeded=True)


def live(row):
    current = process(row['pid'])
    return bool(current and current['start_ticks'] == row['start_ticks'] and current['group'] == row['group']
                and current['state'] != 'Z')


def register():
    """Metadata only: no browser, owner, socket or lease."""
    assert not REGISTRATION.exists() and not (PHASE / 'launched.json').exists()
    assert subprocess.check_output(['git', '-C', 'upstream/fly-gym', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == FLY_GYM
    registration = {'schema': SCHEMA, 'code_base': BASE, 'sources': pins(), 'commands': COMMANDS,
        'outer': outer_command(), 'deadlines_seconds': deadlines(), 'ports': PORTS, 'server_caps': SERVER_CAPS,
        'control_max_bytes': CONTROL_MAX_BYTES, 'floors': FLOORS, 'cadence_acceptance': CADENCE,
        'listener_allowance': LISTENER_ALLOWANCE, 'endurance': {'seconds': ENDURANCE_SECONDS, 'cycle_seconds': CYCLE_SECONDS,
        'stream_seconds': STREAM_SECONDS, 'expected_cycles': expected_cycles(ENDURANCE_SECONDS, CYCLE_SECONDS)},
        'tests': {'acceptance': ACCEPTANCE_TESTS, 'endurance': [ENDURANCE_TEST]},
        'invocations': {'launch_max': 1, 'corrective_attempts': 0},
        'environment': {name: ENV[name] for name in ('MUJOCO_GL', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'TMPDIR')},
        'python': {'path': sys.executable, 'version': sys.version}, 'node': pin(NODE),
        'runtime_versions': {name: importlib.metadata.version(name) for name in ('numpy', 'mujoco', 'torch', 'uvicorn')},
        'installed_dependencies': installed_dependencies(), 'qualification_claims': []}
    REGISTRATION.write_text(json.dumps(registration, indent=2, sort_keys=True) + '\n')
    return 0


def outer_command():
    return ['timeout', '--signal=TERM', '--kill-after=10s', f"{deadlines(ENDURANCE_SECONDS)['outer']}s", sys.executable, '-B',
            str(ROOT / 'scripts/manual_lab_refresh_v4.py'), '--launch']


def launch():
    start = time.monotonic()
    marker = PHASE / 'launched.json'
    assert not marker.exists(), 'Consumed allocation; do not retry'
    assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True) == '', 'Clean source required'
    assert not PHASE.exists() and not PUBLICATION.exists() and not (ROOT / 'ui/dist').exists() and not (ROOT / 'ui/test-results').exists()
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT, check=True)
    assert subprocess.check_output([str(NODE), '--version'], text=True).strip() == 'v24.21.0'
    registration = json.loads(REGISTRATION.read_text())
    assert registration['schema'] == SCHEMA and registration['code_base'] == BASE
    assert pins() == registration['sources'], 'Registered source changed'
    assert registration['commands'] == json.loads(json.dumps(COMMANDS)), 'Registered commands changed'
    assert installed_dependencies() == registration['installed_dependencies']
    assert {name: importlib.metadata.version(name) for name in registration['runtime_versions']} == registration['runtime_versions']
    for port in PORTS.values():
        with socket.socket() as admission:
            admission.bind(('127.0.0.1', port))
    assert shutil.disk_usage(ROOT).free >= FLOORS['project_initial_free_bytes']
    shm_floors()
    limits = deadlines()
    PHASE.mkdir(parents=True)
    with marker.open('x') as stream:
        json.dump({'registration_sha256': pin(REGISTRATION)['sha256'],
                   'producer_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   'started_wall_time_ns': time.time_ns(), 'deadlines_seconds': limits}, stream)
    result = {'status': 'failed', 'qualification_claims': []}
    old_handler = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        result['supervisor'] = bounded_process([sys.executable, '-B', str(ROOT / 'scripts/manual_lab_refresh_v4.py'), '--worker'],
            PHASE / 'supervision', limits['supervisor'], ENV, log_max_bytes=4 * MiB, storage_budget=BUDGET)
        result['worker'] = json.loads((PHASE / 'worker.json').read_text())
        result['cleanup'] = cleanup_check(result['worker']['process'])
        with BUDGET.lock():
            result['lease_free'] = True
        assert result['supervisor']['status'] == 'completed' and result['supervisor']['returncode'] == 0
        assert result['worker']['status'] == 'passed' and result['cleanup']['passed']
        assert not result['worker']['owned_survivors_requiring_kill']
        assert pins() == registration['sources']
        assert time.monotonic() - start < limits['publication']
        result.update(status='passed', storage=BUDGET.check(0, path=PHASE / 'result.json'))
    except BaseException as error:
        result.update(status='failed', failure={'type': type(error).__name__, 'message': str(error)})
    try:
        return publish(result, start, limits['publication'])
    finally:
        signal.signal(signal.SIGTERM, old_handler)


def publish(result, start, deadline):
    """Publish once; the canonical result stays pending until readback finishes."""
    completed = result['status']
    result['status'] = 'pending-publication' if completed == 'passed' else 'failed'
    try:
        write_json(PHASE / 'result.json', result, BUDGET)
        PUBLICATION.mkdir(exist_ok=True)
        published = {}
        for source in [REGISTRATION, *sorted(PHASE.rglob('*')), *sorted((ROOT / 'ui/test-results').rglob('*'))]:
            if (not source.is_file() or source.is_symlink() or source == PHASE / 'result.json'
                    or '/runs/' in str(source) or '/exports/' in str(source)):
                continue
            assert time.monotonic() - start < deadline, 'Publication deadline exceeded'
            relative = source.relative_to(ROOT)
            destination = PUBLICATION / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            BUDGET.check(source.stat().st_size, path=destination)
            with destination.open('xb') as stream:
                stream.write(source.read_bytes())
            assert pin(destination) == pin(source)
            published[str(relative)] = pin(destination)
        result.update(publication=published, elapsed_seconds=time.monotonic() - start)
        receipt = {**result, 'status': completed}
        write_json(PUBLICATION / 'publication.json', receipt, BUDGET)
        assert json.loads((PUBLICATION / 'publication.json').read_text()) == receipt, 'Publication readback differs'
        assert time.monotonic() - start < deadline, 'Deadline exceeded during publication'
        result['status'] = completed
        result['elapsed_seconds'] = time.monotonic() - start
        write_json(PHASE / 'result.json', result, BUDGET)
        assert json.loads((PHASE / 'result.json').read_text()) == result, 'Canonical readback differs'
        assert time.monotonic() - start < deadline, 'Deadline exceeded during canonical write'
    except BaseException as error:
        result.update(status='failed', publication_failure={'type': type(error).__name__, 'message': str(error)},
                      elapsed_seconds=time.monotonic() - start)
        for path in (PHASE / 'result.json', PUBLICATION / 'publication.json'):
            try:
                write_json(path, result, BUDGET)
            except BaseException:
                pass
    print(json.dumps({'status': result['status'], 'elapsed_seconds': result.get('elapsed_seconds')}))
    return 0 if result['status'] == 'passed' else 1


def rehearse(seconds, cycle_seconds):
    """Bounded rehearsal: same worker and evaluation, separate phase, no publication.

    The build and fixed-path screenshots are moved into the rehearsal phase so
    the real launch preconditions (absent ui/dist and ui/test-results) still hold.
    """
    assert 0 < seconds <= 900 and 30 <= cycle_seconds <= seconds, 'Rehearsal: 1..900 s window, cycles >= 30 s'
    assert not (ROOT / 'ui/dist').exists() and not (ROOT / 'ui/test-results').exists()
    phase = ROOT / '.superpowers/sdd/manual-lab-refresh-v4-rehearsal' / time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    phase.mkdir(parents=True)
    configure(phase, seconds, cycle_seconds)
    for port in PORTS.values():
        with socket.socket() as admission:
            admission.bind(('127.0.0.1', port))
    code = worker(registered=False)
    for name in ('dist', 'test-results'):
        if (ROOT / 'ui' / name).exists():
            shutil.move(ROOT / 'ui' / name, phase / ('ui-' + name))
    result = json.loads((phase / 'worker.json').read_text())
    print(json.dumps({'status': result['status'], 'phase': str(phase), 'elapsed_seconds': result['elapsed_seconds'],
                      'failure': result.get('failure'), 'evaluation_passed': result.get('evaluation', {}).get('passed')}))
    return code


if __name__ == '__main__':
    arguments = sys.argv[1:]
    if arguments[:1] == ['--rehearse'] and len(arguments) == 3:
        raise SystemExit(rehearse(int(arguments[1]), int(arguments[2])))
    assert arguments in (['--register'], ['--launch'], ['--worker']), 'Use one explicit mode'
    raise SystemExit(register() if arguments == ['--register'] else worker() if arguments == ['--worker'] else launch())
