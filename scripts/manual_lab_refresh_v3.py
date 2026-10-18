"""Bind the approved v3 allocation to the existing finite manual QA controls."""
import json
from pathlib import Path
import sys
import time

import manual_lab_refresh_v2 as v2

HELPER = Path(v2.__file__).resolve()
WRAPPER = Path(__file__).resolve()
IDENTITIES = {}
READ_PROCESS = v2.process
WRITE_JSON = v2.write_json
READ_PINS = v2.pins


def exit_grace(rows, deadline):
    """Observe one shared two-second window; never signal here or forgive a survivor."""
    start = time.monotonic()
    until = min(start + 2., deadline)
    IDENTITIES.update({row['pid']: row for row in rows})
    outcomes = []
    while True:
        outcomes = []
        for row in rows:
            current = READ_PROCESS(row['pid'])
            if current is None or current['state'] == 'Z':
                outcome = 'exited'
            elif (current['start_ticks'], current['group']) != (row['start_ticks'], row['group']):
                outcome = 'identity-changed'
            else:
                outcome = 'live'
            outcomes.append({'pid': row['pid'], 'start_ticks': row['start_ticks'],
                             'group': row['group'], 'outcome': outcome})
        remaining = until - time.monotonic()
        if not any(row['outcome'] == 'live' for row in outcomes) or remaining <= 0:
            break
        v2.check_server_logs()
        v2.BUDGET.check(0, path=v2.PHASE / 'worker.json')
        time.sleep(min(.05, remaining))
    return {'elapsed_seconds': time.monotonic() - start, 'seconds_max': 2,
            'worker_deadline_monotonic': deadline, 'outcomes': outcomes}


def matched_process(pid):
    current = READ_PROCESS(pid)
    expected = IDENTITIES.get(pid)
    if current and expected and (current['start_ticks'], current['group']) != (expected['start_ticks'], expected['group']):
        return None
    return current


def write_json(path, value, budget):
    if path.name == 'worker.json' and 'descendant_exit_grace' in value:
        value['descendant_exit_grace']['seconds_max'] = 2
    return WRITE_JSON(path, value, budget)


def pins():
    result = READ_PINS()
    for path in (HELPER, WRAPPER, v2.ROOT / 'tests/test_manual_lab_refresh_v3.py',
                 v2.ROOT / 'docs/plans/manual-lab-refresh-v3.md'):
        result[str(path.relative_to(v2.ROOT))] = v2.pin(path)
    return result


def bind():
    v2.PHASE = v2.ROOT / '.superpowers/sdd/manual-lab-refresh-v3'
    v2.PUBLICATION = v2.ROOT / 'docs/reports/manual-lab-refresh-v3-evidence'
    v2.REGISTRATION = v2.ROOT / 'docs/plans/manual-lab-refresh-v3-registration.json'
    v2.BASE = '4364b72'
    v2.SCHEMA = 'manual-lab-refresh-v3'
    v2.__file__ = str(WRAPPER)
    v2.BUDGET = v2.StorageBudget((v2.PHASE, v2.ROOT / 'ui/dist', v2.ROOT / 'ui/test-results', v2.PUBLICATION),
        v2.StorageLimits(max_bytes=1024**3, min_free_bytes=2 * 1024**3), headroom_bytes=4 * 1024**2)
    v2.SERVER = [sys.executable, '-B', '-m', 'palimpsest', 'lab', '--port', str(v2.PORT),
        '--runs', str(v2.PHASE / 'runs'), '--exports', str(v2.PHASE / 'exports'),
        '--storage-max-bytes', str(256 * 1024**2), '--min-free-bytes', str(2 * 1024**3),
        '--max-runs', '3', '--max-snapshots', '2', '--max-exports', '1', '--log-max-bytes', str(1024**2)]
    v2.pins, v2.process, v2.write_json = pins, matched_process, write_json
    v2.EXIT_GRACE = exit_grace
    v2.PROCESS_MATCH = lambda current, row: current['group'] == row['group']


def launch():
    registration = json.loads(v2.REGISTRATION.read_text())
    assert registration['managed_storage_bytes'] == 256 * 1024**2
    assert registration['natural_exit_grace_seconds'] == 2
    assert registration['commands']['worker'] == [sys.executable, '-B', str(WRAPPER), '--worker']
    return v2.launch()


def register():
    v2.register()
    registration = json.loads(v2.REGISTRATION.read_text())
    registration.update(managed_storage_bytes=256 * 1024**2, natural_exit_grace_seconds=2)
    registration['commands']['worker'] = [sys.executable, '-B', str(WRAPPER), '--worker']
    v2.REGISTRATION.write_text(json.dumps(registration, indent=2, sort_keys=True) + '\n')
    return 0


bind()

if __name__ == '__main__':
    assert sys.argv[1:] in (['--register'], ['--launch'], ['--worker']), 'Use one explicit mode'
    raise SystemExit(register() if sys.argv[1:] == ['--register'] else v2.worker() if sys.argv[1:] == ['--worker'] else launch())
