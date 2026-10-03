"""Verify retained R0 bundles and emit a compact, reproducible evidence report."""

import argparse
from collections import Counter
import json
from pathlib import Path

from palimpsest.assets import sha256_file
from palimpsest.records import iter_ticks


def inspect(path, expected_controller):
    path = Path(path)
    recording = path / 'recording'
    manifest = json.loads((recording / 'manifest.json').read_text())
    supervisor = json.loads((path / 'supervisor.json').read_text())
    if supervisor.get('status') != 'completed' or supervisor.get('returncode') != 0:
        raise ValueError(f'Worker did not complete successfully: {path}')
    if manifest['status'] != 'completed':
        raise ValueError(f'Incomplete run: {path}')
    expected_profile = 'flynn-full-vision' if expected_controller == 'flynn' else 'privileged-teacher'
    if (manifest.get('profile') != expected_profile or
            manifest.get('configuration', {}).get('controller') != expected_controller or
            manifest.get('teacher_privileged') is not (expected_controller == 'teacher')):
        raise ValueError(f'Wrong controller/profile for {expected_controller}: {path}')
    events = [json.loads(line) for line in (recording / 'events.jsonl').read_text().splitlines()]
    first = {}
    for tick in iter_ticks(recording):  # Exhaust to verify hashes, every chunk and terminal counts.
        if tick['tick'] == 0:
            first[tick['episode']] = {key: tick[key] for key in ('cam_left', 'cam_right', 'sensors', 'pose')}
    starts = {event['episode']: event for event in events if event['kind'] == 'episode_started'}
    if set(first) != set(starts):
        raise ValueError('Episode start records and recorded observations disagree')
    index = {str(file.relative_to(recording)): sha256_file(file)
             for file in (recording / 'manifest.json', recording / 'events.jsonl')}
    index.update({event['path']: event['sha256'] for event in events if event['kind'] == 'chunk'})
    result = {'bundle': path.name, 'integrity_verified': True, 'files': index,
              'recorded_ticks': manifest['recorded_ticks'], 'metrics': manifest['metrics'],
              'outcomes': dict(Counter(ep['outcome'] for ep in manifest['metrics']['episodes'])),
              'bytes': sum(file.stat().st_size for file in recording.rglob('*') if file.is_file())}
    return result, events, starts, first


def report(reference, teacher, flynn):
    import numpy as np
    ref, ref_events, _, _ = inspect(reference, 'flynn')
    teacher_result, _, teacher_starts, teacher_first = inspect(teacher, 'teacher')
    flynn_result, flynn_events, flynn_starts, flynn_first = inspect(flynn, 'flynn')
    ref_provenance = [e['provenance'] for e in ref_events if e['kind'] == 'policy_loaded']
    dev_provenance = [e['provenance'] for e in flynn_events if e['kind'] == 'policy_loaded']
    if len(ref_provenance) != 1 or ref_provenance != dev_provenance:
        raise ValueError('Reference/development FLYNN provenance differs or is missing')
    parity = [event['result'] for event in ref_events if event['kind'] == 'parity']
    if len(parity) != ref['recorded_ticks'] or not all(p['checked'] and p['ok'] for p in parity):
        raise ValueError('Reference does not establish parity for every recorded tick')
    if len(teacher_starts) != 30 or set(teacher_starts) != set(flynn_starts):
        raise ValueError('Development runs must each contain the same 30 episodes')
    for episode in teacher_starts:
        for key in ('seed', 'goal', 'obstacles', 'initial_qpos', 'initial_qvel', 'reset_protocol'):
            if teacher_starts[episode][key] != flynn_starts[episode][key]:
                raise ValueError(f'Unpaired initial {key} in episode {episode}')
        for key in teacher_first[episode]:
            if not np.array_equal(teacher_first[episode][key], flynn_first[episode][key]):
                raise ValueError(f'Unpaired initial input {key} in episode {episode}')
    return {'schema_version': 1, 'profiles_and_supervisors_verified': True,
            'matching_flynn_provenance': True,
            'reference': ref, 'teacher': teacher_result, 'flynn': flynn_result,
            'initial_states_and_inputs_matched': 30, 'reference_parity_ticks': len(parity),
            'parity_max_abs_error': max(error for p in parity for error in p['max_abs_errors'].values()),
            'provenance': ref_provenance[0],
            'limitations': ['Development smoke seeds, not held-out generalization evidence.',
                            'Teacher has privileged information; information budgets differ.',
                            'Legacy checkpoint training lineage is not established.',
                            'Simulation only; no hardware, memory-learning or topology claims.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--teacher', type=Path, required=True)
    parser.add_argument('--flynn', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = report(args.reference, args.teacher, args.flynn)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(evidence, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: evidence[key] for key in ('initial_states_and_inputs_matched',
                                                   'reference_parity_ticks', 'parity_max_abs_error')}))
