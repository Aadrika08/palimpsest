"""Exactly one registered offline readout; no new native study owners."""
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
    if registration.get('schema') != 'memory-restore-offline-registration-v1':
        raise ValueError('This launcher accepts only the offline registration')
    if repo != Path(registration['repo']) or Path(registration['output']).exists():
        raise ValueError('Registered output must be absent and checkout exact')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo):
        raise ValueError('Offline invocation requires clean committed implementation')
    command = ['timeout', '--signal=TERM', '--kill-after=5', '290s', registration['python'],
        '-m', 'scripts.memory_restore_offline_readout', '--registration', str(evidence/'registration.json')]
    marker = repo/'.superpowers/sdd/memory-native-byte-attribution/offline-launched.json'
    with marker.open('x') as stream:
        json.dump({'command': command, 'started_monotonic': time.monotonic(),
            'registration_sha256': p.file_hash(evidence/'registration.json'),
            'implementation_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()}, stream, indent=2)
    env = dict(os.environ, PYTHONPATH='.:src:scripts', PYTHONDONTWRITEBYTECODE='1',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1', MUJOCO_GL='egl', CUDA_VISIBLE_DEVICES='')
    print(json.dumps({'offline_invocation': 'starting', 'output': registration['output']}), flush=True)
    # The child repeats clean-checkout admission. Keep its live log ignored until
    # it has exited; publication files created beforehand would dirty the repo.
    readout_log = marker.parent/'readout.log'
    with readout_log.open('x') as log:
        completed = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    if readout_log.stat().st_size > p.MiB:
        raise ValueError('Offline live log exceeds registered bound')
    with (evidence/'readout.log').open('xb') as published:
        published.write(readout_log.read_bytes())
    result = {'offline_exit_code': completed.returncode, 'new_native_owners': 0,
        'registration_sha256': p.file_hash(evidence/'registration.json')}
    with (evidence/'invocation-result.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result), flush=True)
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
