"""Exactly one registered diagnostic invocation; original outputs are never reused."""
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
    if repo != Path(registration['repo']) or Path(registration['output']).exists():
        raise ValueError('Registered output must be absent and checkout exact')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo):
        raise ValueError('Native invocation requires clean committed implementation')
    command = ['timeout', '--signal=TERM', '--kill-after=5', '890s', registration['python'],
        '-m', 'scripts.memory_restore_diagnostic', '--registration', str(evidence/'registration.json')]
    marker = repo/'.superpowers/sdd/memory-restore-diagnostic/diagnostic-launched.json'
    with marker.open('x') as stream:
        json.dump({'command': command, 'started_monotonic': time.monotonic(),
            'registration_sha256': p.file_hash(evidence/'registration.json'),
            'implementation_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()}, stream, indent=2)
    env = dict(os.environ, PYTHONPATH='.:src:scripts', PYTHONDONTWRITEBYTECODE='1',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1', MUJOCO_GL='egl', CUDA_VISIBLE_DEVICES='')
    print(json.dumps({'diagnostic_invocation': 'starting', 'output': registration['output']}), flush=True)
    with (evidence/'native-invocation.log').open('x') as log:
        completed = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    result = {'native_exit_code': completed.returncode, 'registration_sha256': p.file_hash(evidence/'registration.json')}
    with (evidence/'invocation-result.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result), flush=True)
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
