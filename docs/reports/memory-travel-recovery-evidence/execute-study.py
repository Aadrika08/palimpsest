"""One registered CLI invocation, immediately followed by independent readout."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

from scripts import memory_decision_pilot as p


def main():
    evidence = Path(__file__).resolve().parent
    repo = evidence.parents[2]
    registration = p.read_json(evidence/'registration.json')
    root = Path(registration['output'])
    assert repo == Path(registration['repo']) and not root.exists()
    assert p.file_hash(repo/'docs/plans/memory-travel-recovery-study.md') == registration['contract_sha256']
    assert p.source_identity(repo, Path(registration['assets'])) == registration['source_identity']
    assert p.hash_ledger(Path(registration['historical_output'])) == registration['historical_inventory']
    assert p.file_hash(registration['storage_qualification']['path']) == registration['storage_qualification']['sha256']
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo)
    assert not subprocess.check_output(['git', 'diff', registration['scientific_freeze'], 'HEAD',
        '--name-only', '--', 'src', 'scripts', 'tests', 'model_manifests', 'uv.lock', 'upstream',
        'docs/plans/memory-travel-handoff.md'], cwd=repo)
    env = dict(os.environ, PYTHONPATH='.:src:scripts', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1')
    command = ['timeout', '--signal=TERM', '--kill-after=5', '7190s', registration['python'],
        '-m', 'scripts.memory_waypoint_study', '--amendment', 'travel-handoff',
        '--repo', str(repo), '--assets', registration['assets'], '--history-root',
        registration['history_root'], '--output', str(root)]
    marker = repo/'.superpowers/sdd/memory-travel-recovery-study/native-launched.json'
    with marker.open('x') as stream:
        json.dump({'started_monotonic': time.monotonic(), 'command': command,
            'implementation_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
            'registration_sha256': p.file_hash(evidence/'registration.json')}, stream, indent=2)
    print(json.dumps({'native_invocation': 'starting', 'output': str(root)}), flush=True)
    with (evidence/'native-invocation.log').open('x') as log:
        completed = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    print(json.dumps({'native_exit_code': completed.returncode, 'readout': 'starting'}), flush=True)
    spec = importlib.util.spec_from_file_location('recovery_readout', evidence/'retained-readout.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    try:
        result = module.run_readout(root, registration, evidence)
        summary = {k: result[k] for k in ('status', 'native_prerequisites_passed',
            'selection_independently_qualified', 'restore_pair_matches', 'conservative_total_seconds',
            'conservative_readout_seconds', 'historical_inventory_unchanged', 'raw_bytes', 'documentary_bytes')}
    except Exception as error:
        summary = {'status': 'independent-readout-refused', 'error': {'type': type(error).__name__, 'message': str(error)},
                   'native_prerequisites_passed': False, 'qualification_claims': []}
    summary['native_exit_code'] = completed.returncode
    with (evidence/'invocation-result.json').open('x') as stream:
        json.dump(summary, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if summary['status'] in ('native-prerequisites-passed', 'audited-task-stop', 'native-prerequisite-failure') else 1


if __name__ == '__main__':
    raise SystemExit(main())
