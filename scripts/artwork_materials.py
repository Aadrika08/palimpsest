"""Artwork materials v1: rebuildable public inputs for the six-mode encounter.

Stages (each is launchable detached; see ``detached``):
  manual    public manual lab run (Afterimage source) and a labelled branch (One map,
            Borrowed body), stepped deterministically through the real lab owner
  flynn     one public FLYNN lab run of consecutive episodes (Choir source)
  materials Afterimage pair stimulus + bounded record/render, multi-episode Choir,
            and the rebuilt six-mode encounter pack (index.html, checksums, recipe)
  detached  print the exact systemd-run commands for an output root

Every stage writes an atomic ``progress.json`` heartbeat (at least every 5 s) and a
``receipt.json`` recipe with source commit, arguments, run ids and output hashes.
Inputs are public: the lab's own simulator recordings, pinned FLYNN/male assets and
the committed portable archive (graph and specimens). No protected catalog is used.
"""
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INPUT_ARCHIVE = ROOT / 'docs/reports/artwork-portability-preparation-evidence/palimpsest-artwork-inputs-v1.zip'
LOCK = '/tmp/palimpsest-software-tests.lock'
NODE_BIN = '/home/utkarsh/.local/share/mise/installs/node/24.21.0/bin'
PYTHON = '/home/utkarsh/Work/shraddha/brain/.venv/bin/python'
# Hash-verified public FLYNN and male assets (palimpsest assets verify: ok); outside every output root.
ASSETS = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn')
GiB = 1024**3
DT = .02
FREE_FLOOR = 10 * GiB  # default: stop rather than eat into the operator's 10 GiB margin
OPERATOR_FLOOR = 4 * GiB  # the detached commands keep at least 4 GiB free (coordinator, 19 Oct 2026)
SEGMENT_TICKS = 25  # the manual action changes every 0.5 s, so one run stays inside the owner's command cap
SCHEDULE = ('action = [0.8, 0.6 * sin(2 * pi * t0 * 0.02 / 5)], t0 = global tick rounded down to a multiple of 25 '
            '(piecewise constant every 0.5 s; fixed, public)')
GOAL_CANDIDATES = ([5., 5.], [-5., 5.], [5., -5.], [-5., -5.], [0., 5.], [5., 0.], [0., -5.], [-5., 0.])


def manual_action(tick):
    """The fixed public manual drive: steady forward speed with a slow weave, held for 25 ticks."""
    start = tick - tick % SEGMENT_TICKS
    return [.8, round(.6 * math.sin(2 * math.pi * start * DT / 5), 9)]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=str) + '\n')
    temporary.replace(path)


def commit():
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip() or None


class Progress:
    """Atomic heartbeat an operator can poll; refreshed by a daemon thread."""

    def __init__(self, output, stage):
        self.path, self.stage, self.started = Path(output) / 'progress.json', stage, time.monotonic()
        self.fields, self.lock, self.stop = {'status': 'running', 'step': 'starting'}, threading.Lock(), threading.Event()
        self.beat()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def update(self, **fields):
        with self.lock:
            self.fields.update(fields)
        self.beat()

    def beat(self):
        with self.lock:
            fields = dict(self.fields)
        free = shutil.disk_usage(self.path.parent).free
        write_json(self.path, {'schema': 'artwork-materials-v1-progress', 'stage': self.stage, 'pid': os.getpid(),
                               'updated_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                               'elapsed_seconds': round(time.monotonic() - self.started, 1), 'free_bytes': free, **fields})

    def _run(self):
        while not self.stop.wait(5.):
            self.beat()

    def close(self, status):
        self.stop.set()
        self.update(status=status)


def floor_check(path):
    free = shutil.disk_usage(path).free
    if free < FREE_FLOOR:
        raise RuntimeError(f'free space {free} below the {FREE_FLOOR}-byte floor')


# Measured in the rehearsal: manual 199,219 B/tick (3,300 ticks), FLYNN 217,560 B/tick (6,000 ticks),
# materials about 192 MB (stimulus 59 MB, Afterimage record 60 MB, exports, pack and its ZIP).
ESTIMATED_BYTES = {'manual': 700 * 1024**2, 'flynn': 1550 * 1024**2, 'materials': 250 * 1024**2}  # FLYNN may run to 6,600 ticks


def admit(path, stages):
    """Refuse up front when the declared floor cannot survive the estimated outputs."""
    free, need = shutil.disk_usage(path).free, sum(ESTIMATED_BYTES[s] for s in stages)
    if free - need < FREE_FLOOR:
        raise RuntimeError(f'free space {free} minus estimated outputs {need} would cross the {FREE_FLOOR}-byte floor')


# --------------------------------------------------------------------------- lab sessions

class Session:
    """Drive one real lab owner deterministically: every tick is an explicit step."""

    def __init__(self, supervisor, run, progress):
        self.supervisor, self.run, self.progress = supervisor, run, progress

    def view(self):
        return self.supervisor.describe(self.run)

    def wait(self, predicate, timeout=180.):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            view = self.view()
            if view['status'] == 'failed':
                raise RuntimeError(f'owner failed: {view.get("failure")}')
            if predicate(view):
                return view
            time.sleep(.005)
        raise TimeoutError('lab owner did not reach the expected boundary')

    def command(self, kind, payload=None, *, expect_tick=None):
        state = self.view()['state']
        body = {'id': uuid.uuid4().hex, 'kind': kind, 'expected_state': state['phase'],
                'expected_episode': state['episode'], 'expected_revision': state['revision']}
        if payload is not None:
            body['payload'] = payload
        receipt = self.supervisor.call(self.run, 'command', body)
        if receipt.get('status') == 'rejected':
            raise RuntimeError(f'{kind} rejected: {receipt}')
        return self.wait(lambda v: any(r['id'] == body['id'] and r['status'] in ('applied', 'rejected', 'failed')
                                       for r in v.get('receipts', [])) and
                         (expect_tick is None or v['state']['total_tick'] >= expect_tick))

    def step(self, action=None):
        """One tick. A manual action is sent only when it differs from the held one: the
        owner keeps a bounded per-run idempotency store (Engine.MAX_IDS = 4096 commands)."""
        state = self.view()['state']
        if action is not None and action != getattr(self, 'held', None):
            self.command('set_action', {'action': action})
            self.held = action
        return self.command('step', expect_tick=state['total_tick'] + 1)['state']

    def run_episode(self, progress, label):
        """Free-run to the episode's own end (no manual input: deterministic per tick)."""
        self.command('run')
        deadline = time.monotonic() + 3600
        while time.monotonic() < deadline:
            view = self.view()
            if view['status'] == 'failed':
                raise RuntimeError(f'owner failed: {view.get("failure")}')
            state = view['state']
            if state['phase'] in ('terminated', 'truncated'):
                return state
            progress.update(step=label, total_ticks=state['total_tick'])
            time.sleep(.2)
        raise TimeoutError('episode did not end')


def start_owner(supervisor, config):
    run = supervisor.start(config)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        view = supervisor.describe(run)
        if view['status'] == 'failed':
            raise RuntimeError(f'owner failed to load: {view.get("failure")}')
        if view['status'] == 'ready' and view.get('sample') is not None:
            return run
        time.sleep(.05)
    raise TimeoutError('owner did not become ready')


def drive(session, *, controller, episodes, episode_ticks, total_ticks, seed, branch_at, progress):
    """Step consecutive episodes; returns per-episode summaries and an optional snapshot."""
    summaries, snapshot, tick = [], None, 0
    free_run = controller != 'manual' and episode_ticks >= 600 and branch_at is None
    for episode in range(episodes):
        steps = 0
        session.held = None  # the engine zeroes manual intent at each new episode
        if free_run:
            state = session.run_episode(progress, f'{controller} episode {episode + 1}/{episodes}')
            steps = state['total_tick'] - tick
            tick = state['total_tick']
            summaries.append({'episode': state['episode'], 'ticks': steps, 'ending': state['phase'],
                              'last_outcome': state.get('last_outcome')})
            if total_ticks and tick >= total_ticks:
                break
            if episode + 1 < episodes:
                session.command('reset', {'seed': seed + episode + 1})
            continue
        while True:
            state = session.step(manual_action(tick) if controller == 'manual' else None)
            tick, steps = tick + 1, steps + 1
            if episode == 0 and branch_at is not None and steps == branch_at and snapshot is None:
                snapshot = session.supervisor.call(session.run, 'snapshot', {'expected_revision': state['revision']})['snapshot_id']
            if tick % 50 == 0:
                progress.update(step=f'{controller} episode {episode + 1}/{episodes}', total_ticks=tick, episode_ticks=steps)
            ended = state['phase'] in ('terminated', 'truncated')
            if ended or steps >= episode_ticks or (total_ticks and tick >= total_ticks):
                ending = state['phase'] if ended else ('declared total reached' if total_ticks and tick >= total_ticks
                                                       else 'declared-length reset')
                summaries.append({'episode': state['episode'], 'ticks': steps, 'ending': ending,
                                  'last_outcome': state.get('last_outcome')})
                break
        if total_ticks and tick >= total_ticks:
            break
        if episode + 1 < episodes:
            session.command('reset', {'seed': seed + episode + 1})
    return summaries, snapshot, tick


def lab_stage(args, controller):
    from palimpsest.lab import LabSupervisor
    from palimpsest.storage import StorageLimits
    output = Path(args.output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    floor_check(output)
    progress = Progress(output, controller)
    receipt = {'schema': 'artwork-materials-v1-session', 'stage': controller, 'commit': commit(), 'arguments': vars(args),
               'schedule': SCHEDULE if controller == 'manual' else 'FLYNN policy; no manual input', 'status': 'failed'}
    supervisor = LabSupervisor(ROOT, Path(args.assets).resolve(), output / 'runs', export_root=output / 'exports',
                               storage_limits=StorageLimits(max_bytes=args.max_bytes, min_free_bytes=FREE_FLOOR),
                               startup_timeout=180.)
    try:
        config = {'scenario': args.scenario, 'texture': 'checker', 'controller': controller, 'device': 'cpu', 'seed': args.seed}
        run = start_owner(supervisor, config)
        session = Session(supervisor, run, progress)
        summaries, snapshot, ticks = drive(session, controller=controller, episodes=args.episodes,
                                           episode_ticks=args.episode_ticks, total_ticks=args.total_ticks, seed=args.seed,
                                           branch_at=getattr(args, 'branch_at', None), progress=progress)
        receipt.update(source_run_id=run, episodes=summaries, recorded_ticks=ticks)
        goal = None
        if snapshot is not None:
            path, item = supervisor.snapshot(run, snapshot)
            closed = supervisor.close(run)
            if closed['status'] != 'closed':
                raise RuntimeError(f'source did not close: {closed}')
            progress.update(step='branch')
            for candidate in GOAL_CANDIDATES:
                branch_config = {**item['config'], 'snapshot_path': str(path), 'snapshot_sha256': item['sha256'],
                                 'snapshot_id': snapshot, 'source_run_path': str(supervisor.path(run)),
                                 'replace_controller': False, 'intervention': {'kind': 'move_goal', 'xy': candidate}}
                try:
                    branch = start_owner(supervisor, branch_config)
                except RuntimeError:
                    continue  # rejected placement; the next fixed candidate is tried
                goal = candidate
                break
            if goal is None:
                raise RuntimeError('no fixed goal candidate was valid for the branch')
            branch_session = Session(supervisor, branch, progress)  # a new owner: its own command store
            start_tick, steps = branch_session.view()['state']['total_tick'], 0
            while True:
                state = branch_session.step(manual_action(start_tick + steps))
                steps += 1
                if state['phase'] in ('terminated', 'truncated') or steps >= args.episode_ticks - args.branch_at:
                    break
            closed = supervisor.close(branch)
            if closed['status'] != 'closed':
                raise RuntimeError(f'branch did not close: {closed}')
            receipt.update(branch_run_id=branch, branch_snapshot_id=snapshot, branch_tick=args.branch_at,
                           branch_edit={'kind': 'move_goal', 'xy': goal, 'label': 'goal moved at the branch snapshot'},
                           branch_ticks=steps, branch_ending=state['phase'])
        else:
            closed = supervisor.close(run)
            if closed['status'] != 'closed':
                raise RuntimeError(f'source did not close: {closed}')
        receipt['status'] = 'completed'
    except BaseException as error:
        receipt['error'] = f'{type(error).__name__}: {error}'
    finally:
        supervisor.shutdown()
    receipt['files'] = {str(p.relative_to(output)): {'sha256': sha(p), 'size_bytes': p.stat().st_size}
                        for p in sorted((output / 'runs').rglob('*')) if p.is_file() and 'recording' in p.parts}
    write_json(output / 'receipt.json', receipt)
    progress.close(receipt['status'])
    return 0 if receipt['status'] == 'completed' else 1


# --------------------------------------------------------------------------- materials

def afterimage_stimulus(recording, output, *, frames, stride, run_id):
    """Every ``stride``-th recorded tick across consecutive episodes; both eyes as recorded."""
    import numpy as np
    from palimpsest.records import iter_ticks
    pairs, ticks, index = [], [], 0
    for row in iter_ticks(recording):
        if index % stride == 0:
            pairs.append(np.stack([row['cam_left'], row['cam_right']]))
            ticks.append([int(row['episode']), int(row['tick'])])
            if len(pairs) == frames:
                break
        index += 1
    if len(pairs) != frames:
        raise ValueError(f'recording supplies {len(pairs)} of {frames} frames')
    output.mkdir(parents=True, exist_ok=False)
    array = np.ascontiguousarray(np.stack(pairs), dtype=np.uint8)
    np.save(output / 'frames.npy', array)
    files = {str(p.relative_to(recording.parent)): sha(p) for p in sorted(recording.rglob('*')) if p.is_file()}
    spec = {'schema_version': 2, 'title': 'Recorded eyes from a public manual lab run', 'creator': 'Palimpsest public lab recording',
            'frame_file': 'frames.npy', 'frame_file_sha256': sha(output / 'frames.npy'),
            'source_times_seconds': [round(i * stride * DT, 9) for i in range(frames)], 'eyes': 'recorded-pair',
            'source': {'kind': 'public manual lab recording', 'run_id': run_id, 'tick_stride': stride,
                       'frames_per_second': round(1 / (stride * DT), 9), 'ticks': ticks, 'recording_files_sha256': files},
            'rights': {'basis': 'self_created', 'statement': 'Simulator camera frames rendered from a public Palimpsest lab recording; no people.',
                       'attribution': 'Palimpsest', 'authorized_processing_and_retention': True,
                       'subject_consent': 'no_identifiable_people'}}
    write_json(output / 'stimulus.json', spec)
    return output / 'stimulus.json'


def cli(args, *command, timeout=900):
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '1'}
    result = subprocess.run([sys.executable, '-B', '-m', 'palimpsest', '--assets', str(Path(args.assets).resolve()), *command],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed: {result.stdout[-2000:]} {result.stderr[-2000:]}')
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except ValueError:
        return {'stdout': result.stdout[-2000:]}


def eye_png(frame):
    """Lossless PNG of one recorded eye, exactly as stored (no resize or colour change)."""
    import base64
    from palimpsest.artifacts import image_data_url
    return base64.b64decode(image_data_url(frame).split(',', 1)[1])


def materials_stage(args):
    import numpy as np
    from palimpsest import afterimage
    from palimpsest.records import iter_ticks
    output = Path(args.output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    floor_check(output)
    progress = Progress(output, 'materials')
    receipt = {'schema': 'artwork-materials-v1-materials', 'commit': commit(), 'arguments': vars(args), 'status': 'failed'}
    try:
        manual = json.loads((Path(args.manual) / 'receipt.json').read_text())
        flynn = json.loads((Path(args.flynn) / 'receipt.json').read_text())
        if manual['status'] != 'completed' or flynn['status'] != 'completed':
            raise RuntimeError('both lab sessions must have completed')
        source = Path(args.manual) / 'runs' / manual['source_run_id']
        branch = Path(args.manual) / 'runs' / manual['branch_run_id']
        choir_run = Path(args.flynn) / 'runs' / flynn['source_run_id']
        exports = output / 'exports'
        exports.mkdir()
        progress.update(step='afterimage stimulus')
        stimulus = afterimage_stimulus(source / 'recording', output / 'stimulus', frames=args.frames, stride=args.stride,
                                       run_id=manual['source_run_id'])
        progress.update(step='afterimage record (fixed male-original, CPU, seed 0)')
        record = output / 'afterimage' / uuid.uuid4().hex
        record.parent.mkdir()
        cli(args, 'afterimage', 'record', str(stimulus), '--controller', 'male-original', '--output', str(record),
            '--min-free-bytes', str(FREE_FLOOR))
        cli(args, 'afterimage', 'render', str(record), '--output', str(exports / 'afterimage.svg'), '--min-free-bytes', str(FREE_FLOOR))
        progress.update(step='borrowed body and one map')
        cli(args, 'export', str(source), '--format', 'svg', '--output', str(exports / 'borrowed-body.svg'), '--min-free-bytes', str(FREE_FLOOR))
        cli(args, 'compare', str(source), str(branch), '--output', str(exports / 'one-map-many-lives.html'), '--min-free-bytes', str(FREE_FLOOR))
        progress.update(step='choir')
        last = max(e['episode'] for e in flynn['episodes'])
        first = min(e['episode'] for e in flynn['episodes'])
        cli(args, 'sonify', str(choir_run), '--population', 'visual_left', '--population', 'visual_right',
            '--population', 'descending', '--episodes', f'{first}-{last}', '--max-seconds', str(args.choir_seconds),
            '--boundary-fade-seconds', '0.02', '--declared-gain', str(args.declared_gain),
            '--output', str(exports / 'counterfactual-choir.wav'), '--min-free-bytes', str(FREE_FLOOR))
        progress.update(step='atlas and specimens (committed portable inputs)')
        inputs = output / 'portable-inputs'
        with zipfile.ZipFile(INPUT_ARCHIVE) as archive:
            archive.extractall(inputs)
        cli(args, 'atlas', '--graph', str(inputs / 'graph/source-graph.json'), '--graph-manifest', str(inputs / 'graph/extraction.json'),
            '--cut-node', '12781', '--output', str(exports / 'atlas.svg'), '--min-free-bytes', str(FREE_FLOOR))
        cli(args, 'specimens', str(inputs / 'specimens/pair.json'), '--output', str(exports / 'space-between-two-flies.svg'),
            '--min-free-bytes', str(FREE_FLOOR))
        progress.update(step='encounter pack')
        eyes = [[row['cam_left'], row['cam_right']] for row in iter_ticks(record / 'recording')]
        pack = build_pack(output / 'pack', exports, eyes=eyes, inputs=inputs, sources={
            'manual': (Path(args.manual), manual), 'flynn': (Path(args.flynn), flynn), 'afterimage': record,
            'stimulus': stimulus.parent}, declared={'afterimage_frames': args.frames,
            'afterimage_source_seconds': round(args.frames * args.stride * DT, 9), 'choir_seconds': args.choir_seconds,
            'static_viewing_seconds': 600, 'choir_declared_gain': args.declared_gain})
        receipt.update(status='completed', pack=str(pack), pack_sha256=sha(pack))
    except BaseException as error:
        import traceback
        receipt['error'] = f'{type(error).__name__}: {error}'
        receipt['traceback'] = traceback.format_exc()[-4000:]
    write_json(output / 'receipt.json', receipt)
    progress.close(receipt['status'])
    return 0 if receipt['status'] == 'completed' else 1


ARTIFACTS = ('afterimage.svg', 'borrowed-body.svg', 'one-map-many-lives.html', 'counterfactual-choir.wav', 'atlas.svg',
             'space-between-two-flies.svg')


def svg_metadata(raw):
    import re
    text = re.search(rb'<metadata[^>]*>(.*?)</metadata>', raw, re.S).group(1).decode()
    for entity, value in (('&quot;', '"'), ('&lt;', '<'), ('&gt;', '>'), ('&amp;', '&')):
        text = text.replace(entity, value)
    return json.loads(text)


def plmp(raw):
    import struct
    position = 12
    while position < len(raw):
        kind, size = struct.unpack_from('<4sI', raw, position)
        if kind == b'plmp':
            return json.loads(raw[position + 8:position + 8 + size])
        position += 8 + size + (size & 1)
    raise ValueError('WAV lacks plmp metadata')


def input_manifest(sources, inputs):
    rows = []
    for name in ('manual', 'flynn'):
        root, receipt = sources[name]
        for relative, value in sorted(receipt['files'].items()):
            rows.append({'path': relative, **value})
    record = sources['afterimage']
    for path in sorted(record.rglob('*')):
        if path.is_file():
            rows.append({'path': f'runs/{record.name}/{path.relative_to(record)}', 'sha256': sha(path), 'size_bytes': path.stat().st_size})
    for path in sorted(sources['stimulus'].rglob('*')):
        rows.append({'path': f'stimulus/afterimage/{path.name}', 'sha256': sha(path), 'size_bytes': path.stat().st_size})
    for path in sorted(inputs.rglob('*')):
        if path.is_file() and path.parts[len(inputs.parts)] in ('graph', 'specimens'):
            rows.append({'path': str(path.relative_to(inputs)), 'sha256': sha(path), 'size_bytes': path.stat().st_size})
    return rows


def build_pack(pack, exports, *, eyes, inputs, sources, declared):
    """Six-mode offline encounter rebuilt from the generated, rebuildable materials."""
    pack.mkdir()
    files = {name: (exports / name).read_bytes() for name in ARTIFACTS}
    after = svg_metadata(files['afterimage.svg'])
    rows = after['alignment']
    choir = plmp(files['counterfactual-choir.wav'])
    body = svg_metadata(files['borrowed-body.svg'])
    atlas = svg_metadata(files['atlas.svg'])
    pair = svg_metadata(files['space-between-two-flies.svg'])
    manual, flynn = sources['manual'][1], sources['flynn'][1]
    eye_dir = pack / 'afterimage-eyes'
    eye_dir.mkdir()
    for index, (left, right) in enumerate(eyes):
        for side, frame in (('left', left), ('right', right)):
            (eye_dir / f'{index + 1:04d}-{side}.png').write_bytes(eye_png(frame))
    seconds = len(choir['timing']['ticks']) * choir['timing']['control_interval_seconds']
    points = len(body['traces'][0]['points']) if body.get('traces') else 0
    captions = (
        ('afterimage', 'Afterimage', f'The fly\'s own recorded eyes from a public manual lab run, both eyes shown side by side and replayed to the fixed male model: {len(rows)} frames at 10 per second ({declared["afterimage_source_seconds"]:g} source seconds). Offline inference; not fly perception.'),
        ('borrowed-body', 'Borrowed body', f'Recorded public manual simulator route: run {manual["source_run_id"]}, {len(manual["episodes"])} episodes, first route {points} points. Actual recorded actions; no physical pen marks.'),
        ('one-map', 'One map, many possible lives', f'Source run {manual["source_run_id"]} and its labelled branch {manual.get("branch_run_id")}, which moved the goal to {manual.get("branch_edit", {}).get("xy")} at tick {manual.get("branch_tick")}. A single declared edit; no causal memory-effect claim.'),
        ('choir', 'Counterfactual choir', f'{seconds:g}-second composed mapping of one public FLYNN run ({len(choir["timing"]["episodes"])} consecutive episodes, boundaries marked by short fades). Declared gain {choir["gain"]["declared_linear"]:g}; peak {choir["levels"]["peak_dbfs"]:.1f} dBFS. Not biological audio.'),
        ('atlas', 'Atlas of what disappears', f'Reduced MaleCNS graph before and after isolating node 12781: {atlas["removed_edges"] if isinstance(atlas["removed_edges"], int) else len(atlas["removed_edges"])} removed edges. Structural analysis, not measured impairment.'),
        ('specimens', 'The space between two flies', 'One curated, unregistered DNge104 anatomical pair on a shared micrometre scale with unequal coverage. No population sex inference.'))
    nav = ''.join(f'<a href="#{key}">{html.escape(title)}</a>' for key, title, _ in captions)
    sections = []
    for (key, title, caption), name in zip(captions, ARTIFACTS):
        if name.endswith('.svg'):
            media = f'<img src="{name}" alt="{html.escape(caption, quote=True)}" loading="lazy">'
        elif name.endswith('.html'):
            media = f'<iframe src="{name}" title="Recorded route comparison and provenance" sandbox="" loading="lazy"></iframe>'
        else:
            media = (f'<p>Start at low volume. Playback ends after {seconds:g} seconds; repeats must be declared and recorded.</p>'
                     f'<audio controls preload="none" src="{name}"></audio><button id="stop-audio" hidden>Stop audio and return to start</button>')
        inspector = ''
        if key == 'afterimage':
            inspector = '''<details><summary>Inspect recorded responses one at a time</summary>
<div id="controls" hidden><button id="previous">Previous frame</button><button id="next">Next frame</button>
<p id="frame-status" aria-live="polite"></p><div class="eyes"><figure><img id="eye-left" alt="Recorded left eye" width="256" height="256"><figcaption>Left eye</figcaption></figure>
<figure><img id="eye-right" alt="Recorded right eye" width="256" height="256"><figcaption>Right eye</figcaption></figure></div>
<svg viewBox="-400 -400 800 800" role="img" aria-labelledby="inspect-title inspect-description">
<title id="inspect-title">Manual response-plane inspection</title><desc id="inspect-description">Exact chronological prefix on fixed axes ±360. The red marker is the sequence start; blue marks the selected response.</desc>
<rect x="-360" y="-360" width="720" height="720" fill="none" stroke="#8c8a83"/><path d="M -360 0 H 360 M 0 -360 V 360" fill="none" stroke="#8c8a83"/>
<polyline id="prefix" fill="none" stroke="#244c5a" stroke-width="2"/>''' + f'<circle cx="{rows[0]["point"][0]}" cy="{rows[0]["point"][1]}" r="4" fill="#aa392b"/>' + '''
<circle id="selected" r="4" fill="#244c5a"/></svg></div></details>'''
        sections.append(f'<section id="{key}" aria-labelledby="{key}-title"><h2 id="{key}-title">{html.escape(title)}</h2><p>{html.escape(caption)}</p>'
                        f'<p><a href="{name}">Open original artifact and embedded provenance</a></p>{media}{inspector}<a href="#modes">Return to modes</a></section>')
    alignment = json.dumps([{'frame': r['frame'], 'point': r['point'], 'source_timestamp_seconds': r['source_timestamp_seconds'],
                             'model_time_seconds': r['model_time_seconds']} for r in rows], separators=(',', ':')).replace('<', '\\u003c')
    page = ('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' file:; media-src 'self' file:; frame-src 'self' file:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>Palimpsest: six recorded encounters</title><style>
body{margin:0;background:#fff;color:#253746;font:1rem/1.6 system-ui,sans-serif}main{max-width:72rem;margin:auto;padding:clamp(1rem,4vw,3rem)}
h1,h2{font-family:Georgia,serif;line-height:1.2}h1{font-size:clamp(2rem,5vw,3.5rem)}h2{font-size:2rem}p{max-width:72ch}
a{color:#244c5a}a:focus-visible,button:focus-visible,summary:focus-visible,audio:focus-visible{outline:3px solid #005fcc;outline-offset:4px}
nav{display:flex;flex-wrap:wrap;gap:.6rem 1.6rem;background:#edf4f8;padding:1rem}section{margin:4rem 0;scroll-margin-top:1rem}
img,svg{display:block;max-width:100%;height:auto;margin:1rem auto}img{max-height:75vh;object-fit:contain}iframe{width:100%;height:38rem;border:1px solid #253746;box-sizing:border-box}
.eyes{display:flex;flex-wrap:wrap;gap:1rem;justify-content:center}.eyes figure{margin:0}.eyes img{image-rendering:pixelated;width:min(256px,40vw);height:auto}
audio{display:block;max-width:100%;margin:1rem 0}button,summary{font:inherit;cursor:pointer}button{padding:.5rem .8rem;margin:.25rem}button:disabled{cursor:default}
details{margin:1rem 0;padding:1rem;background:#edf4f8}#controls svg{max-width:38rem}footer{padding:1rem 0} [hidden]{display:none!important}
</style><main><h1>Palimpsest</h1><p>Six recorded encounters, rebuilt from public, rebuildable materials. Open this page locally; each original artifact retains its source identities and mapping.
No live model, simulator or rover runs here. Human artistic and independent operator acceptance remain open.</p>
<p>Declared durations: Afterimage ''' + f'{declared["afterimage_source_seconds"]:g}' + ''' source seconds; Choir ''' + f'{declared["choir_seconds"]:g}' + ''' seconds; static modes ten-minute viewing sessions. Declare your session, repeat policy, audience/use, custodian and retention before review.</p>
<nav id="modes" aria-label="Artwork modes">''' + nav + '</nav>' + ''.join(sections) + '''
<footer><h2>Sources and review boundaries</h2><p>Inputs are listed with their hashes in <a href="inputs-manifest.json">the input manifest</a>; <a href="recipe.json">the rebuild recipe</a> gives the exact commands. <a href="THIRD_PARTY_NOTICES.md">Distinct source notices</a> · <a href="checksums.json">Artifact checksums</a></p>
<p>This encounter adds no scientific, biological, exhibition-duration or physical qualification.</p></footer>
<script id="alignment" type="application/json">''' + alignment + '''</script><script>
const rows=JSON.parse(document.getElementById('alignment').textContent);let frame=0;
const previous=document.getElementById('previous'),next=document.getElementById('next');
const pad=n=>String(n).padStart(4,'0');
function inspect(){const row=rows[frame];document.getElementById('prefix').setAttribute('points',rows.slice(0,frame+1).map(r=>r.point.join(',')).join(' '));const marker=document.getElementById('selected');marker.setAttribute('cx',row.point[0]);marker.setAttribute('cy',row.point[1]);
document.getElementById('eye-left').src=`afterimage-eyes/${pad(frame+1)}-left.png`;document.getElementById('eye-right').src=`afterimage-eyes/${pad(frame+1)}-right.png`;
document.getElementById('frame-status').textContent=`Frame ${frame+1} of ${rows.length}; source time ${row.source_timestamp_seconds} s; model time ${row.model_time_seconds} s. Fixed axes ±360.`;previous.disabled=frame===0;next.disabled=frame===rows.length-1;}
previous.addEventListener('click',()=>{if(frame>0){frame--;inspect();}});next.addEventListener('click',()=>{if(frame<rows.length-1){frame++;inspect();}});inspect();document.getElementById('controls').hidden=false;
const audio=document.querySelector('audio'),stop=document.getElementById('stop-audio');stop.addEventListener('click',()=>{audio.pause();audio.currentTime=0;});stop.hidden=false;
</script></main></html>''')
    for name, raw in files.items():
        (pack / name).write_bytes(raw)
    (pack / 'index.html').write_text(page)
    shutil.copyfile(inputs / 'THIRD_PARTY_NOTICES.md', pack / 'THIRD_PARTY_NOTICES.md')
    write_json(pack / 'inputs-manifest.json', {'schema': 'artwork-materials-v1-inputs', 'run_ids': {
        'afterimage': sources['afterimage'].name, 'left': manual['source_run_id'], 'right': manual['branch_run_id'],
        'choir': flynn['source_run_id']}, 'files': input_manifest(sources, inputs)})
    route = [episode['ticks'] + 1 for episode in manual['episodes']]
    # Declared Choir length is what was recorded (episodes may end early); the request is kept beside it.
    declared = {**declared, 'choir_requested_seconds': declared['choir_seconds'], 'choir_seconds': round(seconds, 9)}
    write_json(pack / 'declaration.json', {'schema': 'artwork-materials-v1-declaration', **declared,
                                           'borrowed_body_route_points': route,
                                           'one_map_route_points': sorted(set(route + [manual['branch_ticks'] + 1])),
                                           'afterimage_eyes': 'recorded-pair'})
    write_json(pack / 'recipe.json', {'schema': 'artwork-materials-v1-recipe', 'commit': commit(), 'schedule': SCHEDULE,
                                      'manual_receipt': sources['manual'][1], 'flynn_receipt': sources['flynn'][1]})
    members = sorted(p for p in pack.rglob('*') if p.is_file())
    write_json(pack / 'checksums.json', {'files': {str(p.relative_to(pack)): {'sha256': sha(p), 'size_bytes': p.stat().st_size} for p in members}})
    archive = pack.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_STORED) as stream:
        for path in sorted(p for p in pack.rglob('*') if p.is_file()):
            info = zipfile.ZipInfo(str(path.relative_to(pack)), (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            stream.writestr(info, path.read_bytes())
    return archive


# --------------------------------------------------------------------------- detached launch

def detached(stage, unit, output_root, extra, timeout):
    """The operator's detached start: transient user unit, no TTY, explicit environment."""
    return ['systemd-run', '--user', f'--unit={unit}', '--collect', f'--working-directory={ROOT}',
            '--property=StandardInput=null', f'--setenv=PATH={NODE_BIN}:/usr/bin:/bin',
            '--setenv=PYTHONPATH=src:scripts', '--setenv=TMPDIR=/tmp', '--setenv=PYTHONDONTWRITEBYTECODE=1',
            '--setenv=MUJOCO_GL=egl', '--setenv=OMP_NUM_THREADS=1',
            '/usr/bin/flock', LOCK, 'timeout', '--signal=TERM', '--kill-after=30s', f'{timeout}s',
            PYTHON, '-B', str(ROOT / 'scripts/artwork_materials.py'), stage, '--output', str(Path(output_root) / stage),
            '--assets', str(ASSETS), *extra]


def commands(output_root, *, scale='full'):
    suffix = {'rehearsal': '-rehearsal', 'cap': '-cap-rehearsal'}.get(scale, '')
    timeouts = {'manual': 3600, 'flynn': 6 * 3600, 'materials': 3600, 'all': 8 * 3600}
    extra = stage_arguments(scale, output_root)
    floor = ['--min-free-bytes', str(OPERATOR_FLOOR)]  # coordinator: keep at least 4 GiB free
    result = {'all': detached('all', f'palimpsest-art-all{suffix}', output_root, ['--scale', scale, *floor], timeouts['all'])}
    for stage in ('manual', 'flynn', 'materials'):
        result[stage] = detached(stage, f'palimpsest-art-{stage}{suffix}', output_root, [*extra[stage], *floor], timeouts[stage])
    return result


def stage_arguments(scale, output_root):
    root = Path(output_root)
    if scale == 'cap':
        # Short, but beyond one owner's 4,096-command store under the 8faab2b client path.
        return {'manual': ['--episodes', '20', '--episode-ticks', '600', '--total-ticks', '2400', '--branch-at', '300'],
                'flynn': ['--episodes', '30', '--episode-ticks', '600', '--total-ticks', '4200'],
                'materials': ['--manual', str(root / 'manual'), '--flynn', str(root / 'flynn'), '--frames', '480',
                              '--stride', '5', '--choir-seconds', '84', '--declared-gain', '1']}
    rehearsal = scale == 'rehearsal'
    # Episodes can end early (the 8faab2b launch saw 'stalled' at 255 and 526 ticks), so the stages
    # run consecutive episodes until the declared total; --episodes is only an upper bound.
    return {'manual': ['--episodes', '2' if rehearsal else '20', '--episode-ticks', '50' if rehearsal else '600',
                       '--total-ticks', '100' if rehearsal else '3000', '--branch-at', '20' if rehearsal else '300'],
            'flynn': ['--episodes', '2' if rehearsal else '30', '--episode-ticks', '50' if rehearsal else '600',
                      '--total-ticks', '100' if rehearsal else '6000'],
            'materials': ['--manual', str(root / 'manual'), '--flynn', str(root / 'flynn'), '--frames', '20' if rehearsal else '600',
                          '--stride', '5', '--choir-seconds', '2' if rehearsal else '120', '--declared-gain', '1']}


def run_all(args):
    """One process, one lock: stages run strictly in order and stop at the first failure."""
    root = Path(args.output).absolute()
    root.mkdir(parents=True, exist_ok=False)
    admit(root, ('manual', 'flynn', 'materials') if args.scale in ('full', 'cap') else ())
    progress = Progress(root, 'all')
    status = 'completed'
    for stage, extra in stage_arguments(args.scale, root).items():
        progress.update(step=stage)
        code = main([stage, '--output', str(root / stage), '--assets', str(args.assets),
                     '--min-free-bytes', str(FREE_FLOOR), *extra])
        if code:
            status = f'failed at {stage}'
            break
    progress.close(status)
    return 0 if status == 'completed' else 1


def main(argv=None):
    global FREE_FLOOR
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    stages = parser.add_subparsers(dest='stage', required=True)
    for name in ('manual', 'flynn'):
        stage = stages.add_parser(name)
        stage.add_argument('--output', type=Path, required=True)
        stage.add_argument('--assets', type=Path, default=ASSETS)
        stage.add_argument('--scenario', default='sparse-navigation')
        stage.add_argument('--seed', type=int, default=0)
        stage.add_argument('--episodes', type=int, required=True)
        stage.add_argument('--episode-ticks', type=int, default=600)
        stage.add_argument('--total-ticks', type=int, default=0)
        stage.add_argument('--max-bytes', type=int, default=4 * GiB)
        if name == 'manual':
            stage.add_argument('--branch-at', type=int, default=300)
    materials = stages.add_parser('materials')
    materials.add_argument('--output', type=Path, required=True)
    materials.add_argument('--assets', type=Path, default=ASSETS)
    materials.add_argument('--manual', type=Path, required=True)
    materials.add_argument('--flynn', type=Path, required=True)
    materials.add_argument('--frames', type=int, default=600)
    materials.add_argument('--stride', type=int, default=5)
    materials.add_argument('--choir-seconds', type=float, default=120.)
    materials.add_argument('--declared-gain', type=float, default=1.)
    every = stages.add_parser('all', help='manual, flynn and materials in order, under one lock')
    every.add_argument('--output', type=Path, required=True)
    every.add_argument('--assets', type=Path, default=ASSETS)
    every.add_argument('--scale', choices=('full', 'rehearsal', 'cap'), default='full')
    for stage in (every, materials, *[stages.choices[name] for name in ('manual', 'flynn')]):
        stage.add_argument('--min-free-bytes', type=int, default=FREE_FLOOR)
    show = stages.add_parser('detached')
    show.add_argument('--output-root', type=Path, required=True)
    show.add_argument('--scale', choices=('full', 'rehearsal', 'cap'), default='full')
    args = parser.parse_args(argv)
    FREE_FLOOR = getattr(args, 'min_free_bytes', FREE_FLOOR)
    if args.stage == 'all':
        return run_all(args)
    if args.stage == 'detached':
        import shlex
        for name, command in commands(args.output_root, scale=args.scale).items():
            print(f'# {name}\n{shlex.join(command)}')
        return 0
    if args.stage == 'materials':
        return materials_stage(args)
    return lab_stage(args, args.stage)


if __name__ == '__main__':
    raise SystemExit(main())
