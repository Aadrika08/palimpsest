"""One conditional fresh v2 qualification; never reuse a diagnostic invocation."""
import json
import os
from pathlib import Path
import subprocess
import time

from scripts import memory_decision_pilot as p


def main():
    evidence = Path(__file__).resolve().parent
    repo = evidence.parents[2]
    registration_path = evidence/'qualification-registration.json'
    registration = p.read_json(registration_path)
    if registration.get('mode') != 'qualify':
        raise ValueError('This launcher accepts only the qualification registration')
    if repo != Path(registration['repo']) or Path(registration['output']).exists():
        raise ValueError('Registered output must be absent and checkout exact')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo):
        raise ValueError('Native invocation requires clean committed implementation')
    command = ['timeout', '--signal=TERM', '--kill-after=5', '4890s', registration['python'],
        '-m', 'scripts.memory_restore_diagnostic', '--registration', str(registration_path)]
    marker = repo/'.superpowers/sdd/memory-restore-study-v2/qualify/launched.json'
    with marker.open('x') as stream:
        json.dump({'command': command, 'started_monotonic': time.monotonic(),
            'registration_sha256': p.file_hash(registration_path),
            'implementation_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()}, stream, indent=2)
    env = dict(os.environ, PYTHONPATH='.:src:scripts', PYTHONDONTWRITEBYTECODE='1',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1', MUJOCO_GL='egl', CUDA_VISIBLE_DEVICES='')
    print(json.dumps({'qualification_invocation': 'starting', 'output': registration['output']}), flush=True)
    # The child repeats clean-checkout admission. Keep its live log ignored until
    # it has exited; publication files created beforehand would dirty the repo.
    native_log = marker.parent/'qualification-invocation.log'
    with native_log.open('x') as log:
        completed = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    with (evidence/'qualification-invocation.log').open('xb') as published:
        published.write(native_log.read_bytes())
    result = {'native_exit_code': completed.returncode, 'registration_sha256': p.file_hash(registration_path)}
    with (evidence/'qualification-invocation-result.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result), flush=True)
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
