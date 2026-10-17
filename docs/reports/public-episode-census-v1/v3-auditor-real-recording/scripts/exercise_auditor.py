"""Diagnostic only: exercise the ae9bd81 episode auditor's internal checks and the
stdlib bundle validator against one REAL held-layout source/replay pair, and compare
the validator's npz reader with numpy. Reads only; changes nothing.

usage: exercise_auditor.py <scripts-dir> <source-output> <replay-output> <source-diag> <replay-diag> <site> <out.json>
"""
import importlib.util, json, sys, time, traceback
from pathlib import Path

SCRIPTS, SOURCE_OUT, REPLAY_OUT, SOURCE_DIAG, REPLAY_DIAG, SITE, OUT = sys.argv[1:8]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


auditor = load('_auditor', Path(SCRIPTS) / 'audit_puck_cpu_held_episode.py')
validator = auditor.validator()
results = {}


def check(label, fn):
    try:
        value = fn(); results[label] = dict(ok=True, value=value)
    except BaseException as error:
        frames = [f for f in traceback.extract_tb(error.__traceback__)
                  if f.filename.endswith(('audit_puck_cpu_held_episode.py', 'validate_palimpsest_bundle.py'))]
        where = [f'{Path(f.filename).name}:{f.lineno}' for f in frames][-2:]
        results[label] = dict(ok=False, error=repr(error)[:600], at=where)
    print(label, 'PASS' if results[label]['ok'] else 'FAIL ' + results[label]['error'][:200] + ' @ ' + str(results[label].get('at')), flush=True)


src_entry = json.load(open(Path(SOURCE_DIAG) / 'probe-source.json'))['result']
rep_entry = json.load(open(Path(REPLAY_DIAG) / 'probe-replay.json'))['result']
src_run = Path(SOURCE_OUT) / src_entry['run_id']
rep_run = Path(REPLAY_OUT) / rep_entry['run_id']
config = dict(run_ids=dict(source=src_entry['run_id'], replay=rep_entry['run_id']))
ticks = auditor.EPISODE['schedule']['ticks']

# 1. Validator CLI-equivalent on both bundles, with and without the run directory.
for phase, out, run, entry in (('source', SOURCE_OUT, src_run, src_entry), ('replay', REPLAY_OUT, rep_run, rep_entry)):
    bundle = Path(out) / entry['bundle']['path']
    check(f'validator.{phase}.bundle_only', lambda bundle=bundle: validator.validate_bundle(bundle))
    check(f'validator.{phase}.bundle_vs_run', lambda bundle=bundle, run=run: validator.validate_bundle(bundle, run))
    check(f'validator.{phase}.sha_matches_entry', lambda bundle=bundle, entry=entry: auditor.require(
        validator.validate_bundle(bundle, run)['sha256'] == entry['bundle']['sha256'], 'bundle sha differs from entry'))
    check(f'auditor.{phase}.validate_entry', lambda entry=entry, phase=phase: auditor.validate_entry(entry, config, phase))
    check(f'auditor.{phase}.payload_members', lambda out=out, entry=entry, run=run: auditor.require(
        {p.name for p in Path(out).iterdir()} == {entry['bundle']['path'], run.name}, 'payload members differ'))

# 2. recording(): manifest/events/chunks/cameras/snapshot index, then compare() and replay-report checks.
recordings = {}
for phase, run in (('source', src_run), ('replay', rep_run)):
    reader = auditor.Reader(time.monotonic() + 300)
    def rec(run=run, reader=reader, phase=phase):
        rows, record = auditor.recording(run, validator, reader, ticks); recordings[phase] = (rows, record)
        return dict(rows=len(rows), snapshot_id=record['snapshot_id'])
    check(f'auditor.{phase}.recording', rec)
check('auditor.source.snapshot_identity', lambda: auditor.require(
    src_entry['initial_snapshot_id'] == recordings['source'][1]['snapshot_id'], 'snapshot id differs'))
check('auditor.provenance_equal', lambda: auditor.require(
    src_entry['provenance_sha256'] == rep_entry['provenance_sha256'], 'provenance differs'))
check('auditor.compare', lambda: auditor.compare(recordings['source'][0], recordings['replay'][0]))


def report():
    r = json.loads((rep_run / 'replay-report.json').read_bytes())
    auditor.require(r.get('status') == 'passed' and r.get('compared_ticks') == ticks and r.get('first_divergence') is None
                    and r.get('mode') == 'actions' and r.get('source_run_id') == config['run_ids']['source']
                    and r.get('run_id') == config['run_ids']['replay']
                    and r.get('compared_events') == rep_entry['replay']['compared_events'], 'Replay report differs')
    return {k: r.get(k) for k in ('status', 'compared_ticks', 'compared_events', 'mode')}
check('auditor.replay_report', report)

# 3. Independent facts about the real recordings, and validator npz reader vs numpy.
sys.path.insert(0, SITE)
import numpy as np  # noqa: E402
facts = {}
for phase, run in (('source', src_run), ('replay', rep_run)):
    manifest = json.loads((run / 'recording/manifest.json').read_bytes())
    events = [json.loads(line) for line in (run / 'recording/events.jsonl').read_bytes().splitlines()]
    chunks = [e for e in events if e['kind'] == 'chunk']
    index = json.loads((run / 'snapshots/index.json').read_bytes())
    reg = [e for e in events if e['kind'] == 'snapshot_registered']
    mismatch, frames, eyes = [], {}, set()
    for event in chunks:
        raw = (run / 'recording' / event['path']).read_bytes()
        mine = validator.read_npz(raw)
        with np.load(run / 'recording' / event['path'], allow_pickle=False) as theirs:
            if set(mine) != set(theirs.files): mismatch.append(('names', event['path']))
            for name in theirs.files:
                a = theirs[name]
                b = mine[name]
                if a.dtype.str != b.descr or tuple(a.shape) != b.shape or a.tobytes() != b.data:
                    mismatch.append((event['path'], name, a.dtype.str, b.descr, a.shape, b.shape))
                if name in auditor.CAMERAS:
                    frames.setdefault(name, []).extend(int(f.min() == f.max()) for f in a)
                if name == 'eyes':
                    eyes.update(tuple(map(bool, row)) for row in a)
    facts[phase] = dict(
        manifest_keys=sorted(manifest), run_id_equals_dir=manifest.get('run_id') == run.name,
        recorded_ticks=manifest.get('recorded_ticks'), recorded_events=manifest.get('recorded_events'), event_count=len(events),
        recorded_chunks=manifest.get('recorded_chunks'), chunk_events=[{k: e.get(k) for k in ('path', 'start', 'count', 'episode')} for e in chunks],
        chunk_episodes=sorted({e.get('episode') for e in chunks}),
        schema={k: v for k, v in (chunks[0].get('arrays') or {}).items()} if chunks else None,
        constant_frames={k: sum(v) for k, v in frames.items()}, frames_per_camera={k: len(v) for k, v in frames.items()},
        eyes_values=sorted(eyes), npz_reader_vs_numpy_mismatches=mismatch,
        snapshot_index=index, snapshot_registered_event={k: v for k, v in reg[0].items()} if reg else None,
        event_kinds=sorted({e['kind'] for e in events}),
        top_level=sorted(p.name for p in run.iterdir()))
json.dump(dict(kind='diagnostic-episode-auditor-exercise-v1', diagnostic_only=True, checks=results, facts=facts),
          open(OUT, 'w'), indent=1, default=str)
for phase, f in facts.items():
    print(phase, {k: f[k] for k in ('run_id_equals_dir', 'recorded_ticks', 'recorded_events', 'event_count', 'recorded_chunks',
                                    'chunk_episodes', 'constant_frames', 'frames_per_camera', 'eyes_values', 'npz_reader_vs_numpy_mismatches', 'top_level')})
