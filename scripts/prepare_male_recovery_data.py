"""Research-only executed-target/right-censored data admission; never trains."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from palimpsest import artifacts, male_model, male_research
from palimpsest.records import iter_ticks
import collect_male_recovery as recovery

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = 'docs/plans/m7-recovery-learning-protocol.json'
PROTOCOL_SHA256 = '091c4e98bf8bc4124383673783a21f5687112946ffeaa54c8a70c41e968f2b28'
MAX_JSON = 4*1024**2


def protocol():
    return frozen_json(ROOT/PROTOCOL_PATH, PROTOCOL_SHA256)


def frozen_json(path, expected):
    payload = artifacts._read(path, MAX_JSON)
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError('Frozen JSON source hash differs: ' + str(path))
    return artifacts._json(payload)


def reader_identity():
    p = protocol()
    code = {name: hashlib.sha256(artifacts._read(ROOT/name, MAX_JSON)).hexdigest()
            for name in p['source_code_sha256']}
    if code != p['source_code_sha256']:
        raise ValueError('Pinned current reader source differs')
    return {'current_reader_sources': code,
            'adapter_sha256': hashlib.sha256(artifacts._read(Path(__file__), MAX_JSON)).hexdigest()}


def output_path(output, baseline_collection, recovery_report):
    output = artifacts._safe_path(output)
    for document in (baseline_collection, recovery_report):
        corpus = artifacts._safe_path(document).parent
        if output == corpus or corpus in output.parents or output in corpus.parents:
            raise ValueError('Output must be outside both immutable source corpus trees')
    return output


def inventory(root, entries, deadline=math.inf):
    """Fresh exact recording/snapshot inventory, including hashes and extra files."""
    root = artifacts._safe_path(root)
    names = []
    for directory in ('recording', 'snapshots'):
        path = artifacts._safe_path(root/directory)
        if path.exists():
            for file in path.rglob('*'):
                file = artifacts._safe_path(file)
                if file.is_dir(): continue
                if not file.is_file(): raise ValueError('Nonregular source file')
                names.append(file.relative_to(root).as_posix())
                if len(names) > 128: raise ValueError('Source file count exceeds fixed inventory')
    if sorted(names) != sorted(entry['path'] for entry in entries):
        raise ValueError('Frozen source file inventory differs')
    result, total = [], 0
    for entry in entries:
        name = entry['path']
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Relative frozen source path required')
        file = artifacts._safe_path(root/name)
        size = file.stat().st_size
        if size != entry['bytes'] or size < 0:
            raise ValueError('Frozen source file size differs')
        total += size
        if total > 160*1024**2: raise ValueError('Source exceeds combined recording/snapshot limit')
        sha = hashlib.sha256()
        with file.open('rb') as stream:
            while payload := stream.read(1024**2):
                if time.monotonic() > deadline: raise TimeoutError('Research data preparation deadline exceeded')
                sha.update(payload)
        if sha.hexdigest() != entry['sha256']:
            raise ValueError('Frozen source file bytes differ')
        result.append({'path': name, 'bytes': size, 'sha256': sha.hexdigest()})
    return result


def admit_rows(raw_rows, result, run_id):
    """Reuse v3 raw validators; feature inputs never include expert/private fields."""
    import numpy as np
    if len(raw_rows) != 67 or len(result['rows']) != 67:
        raise ValueError('Exact full 67-row fresh recovery sequence required')
    inputs, targets, bound, prefix = [], [], [], True
    for tick, (raw, row) in enumerate(zip(raw_rows, result['rows'])):
        if (int(raw['episode']) != 0 or int(raw['tick']) != tick or row['tick'] != tick or
                raw['action'].dtype != np.float32 or raw['action'].shape != (2,) or
                not np.isfinite(raw['action']).all() or
                not math.isclose(float(raw['simulation_time']), (tick+1)*.02, rel_tol=0., abs_tol=1e-8) or
                raw['eyes'].dtype.kind != 'b' or raw['eyes'].shape != (2,) or not raw['eyes'].all()):
            raise ValueError('Recovery fresh cursor/actual target/time/eyes differs')
        prefix = recovery.bind_action(tick, raw, prefix)
        if (raw['action'].tolist() != row['action'] or raw['recovery_expert_action'].tolist() != row['expert_action'] or
                bool(raw['recovery_prefix']) != row['prefix'] or row['callback_count'] != 10 or
                raw['body_contact_counts'].tolist() != row['contact_counts'] or
                raw['recovery_teacher_before'].tolist() != [row['before'][key] for key in ('count', 'direction', 'previous_bad_contact')] or
                raw['recovery_teacher_after'].tolist() != [row['after'][key] for key in ('count', 'direction', 'previous_bad_contact')] or
                raw['recovery_transitions'].tolist() != [row['transition'][key] for key in ('started', 'completed', 'old_label_replaced')]):
            raise ValueError('Recovery actual/expert/counter binding differs')
        bound.append(recovery.bind_clearance(raw, row, result['contact_ownership']))
        inputs.append(male_model.features(raw)); targets.append(raw['action'].copy())
    coverage = recovery.validate_collection(bound, result['collection_boundary'], result['final_state'])
    if (coverage != result['coverage'] or not coverage['passed'] or
            result['final_state']['phase'] != 'paused' or result['final_state']['last_outcome'] is not None):
        raise ValueError('Only the pinned paused first-cycle coverage ending is admitted')
    episode = {'run_id': run_id, 'episode': 0, 'features': np.stack(inputs), 'targets': np.stack(targets)}
    return episode, {'ending': 'right_censored_coverage_complete', 'final_phase': 'paused',
        'last_outcome': None, 'windows': [32, 32, 3], 'coverage': coverage,
        'feature_target_sha256': hashlib.sha256(episode['features'].tobytes()+episode['targets'].tobytes()).hexdigest()}


def validate_splits(data, *, check_counts=True):
    import numpy as np
    if set(data) != {'train', 'dev', 'held_out'} or data['held_out']:
        raise ValueError('Held-out boundary must remain unopened')
    seen, payload_splits, counts = set(), {}, {}
    for split, episodes in data.items():
        counts[split] = 0
        for episode in episodes:
            key = (episode['run_id'], episode['episode'])
            if key in seen: raise ValueError('Duplicate source episode or split overlap')
            seen.add(key)
            features, targets = episode['features'], episode['targets']
            if (features.dtype != np.float32 or targets.dtype != np.float32 or
                    features.shape != (len(targets), 388) or targets.shape != (len(targets), 2) or
                    not len(targets) or not np.isfinite(features).all() or not np.isfinite(targets).all()):
                raise ValueError('Invalid research features/actual targets')
            sha = hashlib.sha256(features.tobytes()+targets.tobytes()).hexdigest()
            if sha in payload_splits: raise ValueError('Duplicate feature/target payload')
            payload_splits[sha] = split
            counts[split] += len(targets)
    if check_counts and counts != {'train': 2117, 'dev': 1228, 'held_out': 0}:
        raise ValueError('Fixed research train/dev row counts differ')
    return counts


def prepare(baseline_collection, recovery_report, *, deadline=None):
    """Explicit two input documents; no directory search or held-out path argument."""
    p = protocol()
    deadline = time.monotonic()+p['preparation_limits']['seconds'] if deadline is None else deadline
    initial_reader = reader_identity()
    if recovery.PROTOCOL_SHA256 != p['recovery_protocol_sha256']:
        raise ValueError('Pinned admission/feature/collector code differs')
    baseline_collection = artifacts._safe_path(baseline_collection)
    recovery_report = artifacts._safe_path(recovery_report)
    baseline = frozen_json(baseline_collection, p['baseline_collection_sha256'])
    observed = frozen_json(recovery_report, p['recovery_report_sha256'])
    if baseline['status'] != 'completed' or baseline['stage'] != 'development' or baseline['research_protocol_sha256'] != p['baseline_protocol_sha256']:
        raise ValueError('Frozen baseline development collection differs')
    if (observed['status'] != 'passed' or observed['protocol_status'] != 'completed' or
            observed['protocol_sha256'] != p['recovery_protocol_sha256'] or
            observed['numeric_ticks'] != 134 or observed['owners_completed'] != 2 or
            observed['runtime_source']['commit'] != p['recovery_source_commit']):
        raise ValueError('Only the successful exact v3 collection is admitted')
    # Fourteen combined160 MiB ceilings are below the unchanged3 GiB source cap.
    if (len(baseline['runs']) != 12 or
            14*160*1024**2 > p['source_limits']['max_bytes']):
        raise ValueError('Fixed prospective source admission exceeds count/byte budget')
    checks, paths, total_bytes = [], {'train': [], 'dev': [], 'held_out': []}, 0
    for entry in baseline['runs']:
        if entry['split'] not in ('train', 'dev') or entry['status'] != 'completed':
            raise ValueError('Unopened held-out and completed baseline only')
        run = baseline_collection.parent/'runs'/entry['run_id']
        files = inventory(run, entry['files'], deadline)
        total_bytes += sum(file['bytes'] for file in files)
        checks.append((run, files)); paths[entry['split']].append(run)
    # Preserve the existing reader's complete v2 admission, seeds and natural endings.
    data, baseline_admission = male_model.prepare_splits(paths, research_stage='development')
    if sum(len(ep['targets']) for ep in data['train']) != 1983 or sum(len(ep['targets']) for ep in data['dev']) != 1228:
        raise ValueError('Baseline row counts differ')
    recovery_admission = []
    for expected in p['recovery_sources']:
        case = observed['cases'][expected['case_id']]
        result = frozen_json(recovery_report.parent/expected['case_id']/'result.json', expected['result_sha256'])
        if (case['status'] != 'completed-recording' or result['status'] != 'completed-recording' or
                result['case']['seed'] != expected['seed'] or Path(result['run']).name != expected['run_id'] or
                not result['engine_closed'] or not result['callback_restored']):
            raise ValueError('Pinned v3 source/result/cleanup identity differs')
        run = recovery_report.parent/expected['case_id']/expected['run_id']
        prefix = run.relative_to(recovery_report.parent).as_posix()+'/'
        files = [{'path': name[len(prefix):], 'bytes': artifacts._safe_path(recovery_report.parent/name).stat().st_size, 'sha256': sha}
                 for name, sha in observed['artifacts_sha256'].items() if name.startswith(prefix)]
        if not files: raise ValueError('Missing pinned recovery file inventory')
        files = inventory(run, files, deadline); checks.append((run, files))
        total_bytes += sum(file['bytes'] for file in files)
        manifest = artifacts._manifest(run)
        if (manifest['run_id'] != expected['run_id'] or manifest['profile'] != recovery.PROFILE or
                manifest['controller'] != 'teacher' or manifest['teacher_privileged'] is not True or
                manifest.get('parent_run_id') is not None or manifest.get('replay_source_run_id') is not None or
                manifest.get('initial_memory') is not None or manifest['recorded_ticks'] != 67 or
                manifest['recovery_protocol_sha256'] != p['recovery_protocol_sha256'] or
                manifest['recovery_collection_boundary'] != 'coverage_complete' or
                manifest['recovery_contact_ownership'] != result['contact_ownership']):
            raise ValueError('Research-only recovery manifest differs')
        artifacts._load(run)  # Reuse published chunk/event integrity admission, without native decoding.
        episode, admission = admit_rows(list(iter_ticks(run/'recording')), result, expected['run_id'])
        data['train'].append(episode)
        recovery_admission.append({**expected, **admission, 'path': str(run), 'files': files})
    if total_bytes > p['source_limits']['max_bytes'] or len(checks) != 14:
        raise ValueError('Research source byte/count budget differs')
    counts = validate_splits(data)
    male_model.check_sources(baseline_admission)
    for run, files in checks: inventory(run, files, deadline)
    frozen_json(baseline_collection, p['baseline_collection_sha256'])
    frozen_json(recovery_report, p['recovery_report_sha256'])
    for expected in p['recovery_sources']:
        frozen_json(recovery_report.parent/expected['case_id']/'result.json', expected['result_sha256'])
    if reader_identity() != initial_reader:
        raise ValueError('Reader/adapter source changed during admission')
    if time.monotonic() > deadline: raise TimeoutError('Research data preparation deadline exceeded')
    manifest = {'schema_version': 1, 'status': 'prepared-research-only', 'protocol_sha256': PROTOCOL_SHA256,
        'protocol': p, **initial_reader,
        'baseline_collection': {'path': str(baseline_collection), 'sha256': p['baseline_collection_sha256']},
        'recovery_report': {'path': str(recovery_report), 'sha256': p['recovery_report_sha256']},
        'historical_recovery_producer': {'runtime_source': observed['runtime_source'],
                                        'harness_sha256': observed['harness_sha256']},
        'baseline_admission': baseline_admission, 'recovery_admission': recovery_admission,
        'ordered_sources': {split: [{'run_id': ep['run_id'], 'episode': ep['episode'], 'ticks': len(ep['targets']),
            'feature_target_sha256': hashlib.sha256(ep['features'].tobytes()+ep['targets'].tobytes()).hexdigest()}
            for ep in episodes] for split, episodes in data.items()},
        'feature_protocol': male_model.FEATURE_PROTOCOL, 'feature_protocol_sha256': male_model.digest(male_model.FEATURE_PROTOCOL),
        'counts': counts, 'total_source_bytes': total_bytes, 'qualification_claims': []}
    return data, manifest


def publish_manifest(output, manifest, deadline):
    """Fresh single-writer directory; no admissible report before final fsync."""
    import shutil
    payload = (json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    if len(payload) > MAX_JSON: raise ValueError('Data manifest exceeds 4 MiB')
    if shutil.disk_usage(output).free < len(payload)+1024**3:
        raise ValueError('Data manifest free-disk floor exceeded')
    destination = output/'data-manifest.json'
    if destination.exists(): raise FileExistsError('Data manifest is immutable; fresh output required')
    expected_reader = {key: manifest[key] for key in ('current_reader_sources', 'adapter_sha256')}
    if reader_identity() != expected_reader: raise ValueError('Reader/adapter drift before publication')
    pending = output/'data-manifest.pending'
    with pending.open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    if time.monotonic() > deadline: raise TimeoutError('Data manifest completion deadline exceeded')
    if reader_identity() != expected_reader: raise ValueError('Reader/adapter drift during final sync')
    # Exclusive output is owned by this one preparation process. Publication last.
    pending.replace(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-collection', type=Path, required=True)
    parser.add_argument('--recovery-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Fresh exclusive directory; research manifest only')
    args = parser.parse_args()
    output = output_path(args.output, args.baseline_collection, args.recovery_report)
    output.mkdir(parents=True, exist_ok=False)
    try:
        deadline = time.monotonic()+protocol()['preparation_limits']['seconds']
        _, manifest = prepare(args.baseline_collection, args.recovery_report, deadline=deadline)
        publish_manifest(output, manifest, deadline)
    except Exception as error:
        try:
            male_research.write_json(output/'failure.json', {'status': 'failed-preparation',
                'type': type(error).__name__, 'message': str(error)[:1024], 'qualification_claims': []})
        except Exception as reporting_error:
            error.add_note('Failure evidence write also failed: '+str(reporting_error)[:256])
        raise


if __name__ == '__main__': main()
