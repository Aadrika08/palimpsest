"""A fresh offline encounter from pinned derivatives; no scientific runtime."""
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import struct
import subprocess
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'docs/reports/artwork-material-v3-evidence/palimpsest-artwork-review-development-v3.zip'
ARCHIVE_PIN = {'size_bytes': 13529793,
               'sha256': 'e4994c965d3b2ff18623e39b745dbb4d7f4f36ed2ddecd7f2d6f5fddb7a132de'}
ARTIFACTS = ('afterimage.svg', 'borrowed-body.svg', 'one-map-many-lives.html',
             'counterfactual-choir.wav', 'atlas.svg', 'space-between-two-flies.svg')
MEMBERS = (*ARTIFACTS, 'README.md', 'THIRD_PARTY_NOTICES.md', 'checksums.json')
SOURCES = ('scripts/prepare_artwork_encounter.py', 'tests/test_artwork_encounter.py',
           'docs/plans/artwork-encounter-v1.md')
OUTPUT_LIMIT, FREE_FLOOR, HEADROOM = 64 * 1024**2, 2 * 1024**3, 64 * 1024**2
MAX_HEADING = struct.unpack('!f', struct.pack('!f', math.pi))[0]  # Producer stores float32 actions.


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe(path):
    path = Path(path).absolute()
    require(path == path.resolve() and not any(p.is_symlink() for p in (path, *path.parents)),
            'canonical non-symlink path required')
    return path


def pin(path):
    path = safe(path)
    require(path.is_file(), 'regular source file required')
    with path.open('rb') as stream:
        return {'size_bytes': path.stat().st_size,
                'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def destination(path):
    path = safe(path)
    require(path.is_relative_to(ROOT) and path != ROOT, 'output must be inside this worktree')
    require(not path.exists(), 'fresh absent output directory required')
    require(path.parent.is_dir(), 'output parent must already exist')
    return path


class Guard:
    def __init__(self, output):
        self.output, self.start, self.written = output, time.monotonic(), 0

    def check(self, additional=0):
        require(time.monotonic() - self.start < 120, 'preparation deadline exceeded')
        require(self.written + additional <= OUTPUT_LIMIT - 1024**2, 'output byte cap exceeded')
        require(shutil.disk_usage(self.output if self.output.exists() else self.output.parent).free
                >= FREE_FLOOR + HEADROOM + additional, 'free space floor/headroom exceeded')

    def write(self, name, raw):
        self.check(len(raw))
        with (self.output / name).open('xb') as stream:
            self.written += len(raw)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        self.check()


def read_archive(path, expected, check):
    check()
    require(safe(path).stat().st_size == expected['size_bytes'], 'input ZIP pin size differs')
    require(pin(path) == expected, 'input ZIP pin differs')
    with zipfile.ZipFile(path) as bundle:
        members = bundle.infolist()
        require(len(members) == len(MEMBERS) and {m.filename for m in members} == set(MEMBERS),
                'ZIP member allowlist or uniqueness differs')
        require(sum(m.file_size for m in members) < OUTPUT_LIMIT - 1024**2, 'ZIP member byte cap exceeded')
        for member in members:
            require(member.create_system == 3 and stat.S_ISREG(member.external_attr >> 16)
                    and member.compress_type == zipfile.ZIP_STORED and not member.flag_bits & 1
                    and member.file_size == member.compress_size,
                    'regular stored unencrypted ZIP members required')
        files = {}
        for member in members:
            check()
            files[member.filename] = bundle.read(member)  # zipfile validates each CRC.
            require(len(files[member.filename]) == member.file_size, 'ZIP member size differs')
    checks = json.loads(files['checksums.json'])
    require(isinstance(checks, dict) and checks.get('qualification_claims') == []
            and isinstance(checks.get('files'), dict)
            and set(checks['files']) == set(MEMBERS) - {'checksums.json'}, 'checksum member allowlist differs')
    for name, expected_member in checks['files'].items():
        raw = files[name]
        require(expected_member == {'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                'member checksum differs: ' + name)
    check()
    require(pin(path) == expected, 'input ZIP pin changed during read')
    return files


def alignment(raw):
    root = ET.fromstring(raw)
    require(root.tag == '{http://www.w3.org/2000/svg}svg', 'Afterimage SVG required')
    nodes = root.findall('{http://www.w3.org/2000/svg}metadata')
    require(len(nodes) == 1, 'one Afterimage metadata node required')
    meta = json.loads(nodes[0].text)
    require(meta['kind'] == 'afterimage-v1' and meta['model_dt_seconds'] == .02
            and meta['mapping']['id'] == 'response-plane-v1'
            and meta['mapping']['axis_limits'] == [-360, 360], 'fixed Afterimage mapping required')
    rows, times = meta['alignment'], meta['stimulus']['manifest']['source_times_seconds']
    number = lambda x: type(x) in (int, float) and math.isfinite(x)
    require(isinstance(rows, list) and 1 <= len(rows) <= 600 and isinstance(times, list)
            and len(times) == len(rows) and all(number(t) and 0 <= t <= 1e12 for t in times)
            and all(b > a for a, b in zip(times, times[1:])) and times[-1] - times[0] <= 120,
            'bounded source times/alignment required')
    for i, row in enumerate(rows):
        require(type(row['frame']) is int and row['frame'] == i
                and number(row['source_timestamp_seconds']) and row['source_timestamp_seconds'] == times[i]
                and number(row['model_time_seconds']) and row['model_time_seconds'] == (i + 1) * .02,
                'frame/source/model time alignment differs')
        action, point = row['action'], row['point']
        require(isinstance(action, list) and isinstance(point, list) and len(action) == len(point) == 2
                and all(number(v) for v in (*action, *point)) and abs(action[0]) <= 3 and abs(action[1]) <= MAX_HEADING
                and point == [360 * action[0] / 3, -360 * action[1] / math.pi], 'exact response-plane alignment differs')
    return rows


def script_json(value):
    raw = json.dumps(value, allow_nan=False, separators=(',', ':'))
    for value, escaped in (('&', '\\u0026'), ('<', '\\u003c'), ('>', '\\u003e'),
                           ('\u2028', '\\u2028'), ('\u2029', '\\u2029')):
        raw = raw.replace(value, escaped)
    return raw


def choir_details(raw):
    """Validate bounded Choir PCM/provenance before using it as presentation text."""
    require(12 <= len(raw) <= 16 * 1024**2 and raw[:4] == b'RIFF'
            and raw[8:12] == b'WAVE' and struct.unpack_from('<I', raw, 4)[0] == len(raw) - 8,
            'bounded complete Choir WAV required')
    chunks, position = {}, 12
    while position < len(raw):
        require(position + 8 <= len(raw), 'truncated WAV chunk')
        kind, size = struct.unpack_from('<4sI', raw, position)
        end = position + 8 + size
        require(end + size % 2 <= len(raw) and kind not in chunks, 'invalid or duplicate WAV chunk')
        chunks[kind] = raw[position + 8:end]
        position = end + size % 2
    require(chunks.get(b'fmt ') == struct.pack('<HHIIHH', 1, 1, 48000, 96000, 2, 16)
            and b'data' in chunks and b'plmp' in chunks and len(chunks[b'plmp']) <= 256 * 1024,
            '48 kHz mono PCM and bounded Choir metadata required')
    pcm = chunks[b'data']
    require(len(pcm) > 0 and len(pcm) % 2 == 0, 'complete PCM samples required')
    meta = json.loads(chunks[b'plmp'])
    require(isinstance(meta, dict) and type(meta.get('version')) is int and meta['version'] in (1, 2)
            and meta.get('artwork') == 'counterfactual choir'
            and meta.get('pcm_sha256') == hashlib.sha256(pcm).hexdigest(), 'Choir identity or PCM hash differs')
    timing, mapping = meta.get('timing'), meta.get('mapping')
    require(isinstance(timing, dict) and isinstance(mapping, dict), 'Choir timing/mapping required')
    require(mapping.get('sample_rate_hz') == 48000 and mapping.get('channels') == 1
            and mapping.get('sample_width_bytes') == 2, 'Choir mapping disagrees with PCM')
    voices = mapping.get('voices')
    require(isinstance(voices, list) and 1 <= len(voices) <= 3
            and all(isinstance(v, dict) and v.get('population') in ('visual_left', 'visual_right', 'descending') for v in voices),
            'declared Choir voices required')
    names = [v['population'] for v in voices]
    require(len(set(names)) == len(names), 'duplicate Choir voice')
    frames = len(pcm) // 2
    boundaries = timing.get('sample_boundaries')
    require(isinstance(boundaries, list) and 2 <= len(boundaries) <= 100001
            and all(type(v) is int for v in boundaries) and boundaries[0] == 0
            and boundaries[-1] == frames and all(b > a for a, b in zip(boundaries, boundaries[1:])),
            'Choir sample boundaries disagree with PCM')
    dt = timing.get('control_interval_seconds')
    require(type(dt) in (int, float) and math.isfinite(dt) and dt > 0
            and abs((len(boundaries) - 1) * dt * 48000 - frames) <= .500001,
            'Choir interval duration disagrees with PCM')
    segments = []
    prefix = False
    if meta['version'] == 2:
        require(timing.get('clock') == 'concatenated simulation time' and frames == 5760000
                and dt == .02 and timing.get('duration_seconds') == 120
                and timing.get('selected_intervals') == 6000 and len(boundaries) == 6001
                and boundaries == list(range(0, 5760001, 960)), '120-second composition timing required')
        segments = timing.get('segments')
        prefix = timing.get('final_episode_prefix')
        require(isinstance(segments, list) and 1 <= len(segments) <= 6000 and type(prefix) is bool,
                'composition segments and prefix declaration required')
        previous_end, previous_episode = 0, None
        for segment in segments:
            require(isinstance(segment, dict) and all(type(segment.get(k)) is int for k in
                    ('episode', 'start_tick', 'end_tick_inclusive', 'output_start_sample', 'output_end_sample_exclusive')),
                    'integer composition ranges required')
            episode, start, end = segment['episode'], segment['output_start_sample'], segment['output_end_sample_exclusive']
            ticks = segment['end_tick_inclusive'] + 1
            require(episode >= 0 and (previous_episode is None or episode == previous_episode + 1)
                    and segment['start_tick'] == 0 and ticks > 0 and start == previous_end
                    and end - start == ticks * 960 and end <= frames,
                    'composition ranges must cover consecutive episodes and samples')
            native_start, native_end = segment.get('simulation_start_seconds'), segment.get('simulation_end_seconds')
            require(all(type(v) in (int, float) and math.isfinite(v) for v in (native_start, native_end))
                    and abs(native_start) <= 1e-8 and abs(native_end - ticks * .02) <= 1e-7,
                    'composition native time differs from ticks')
            previous_end, previous_episode = end, episode
        require(previous_end == frames, 'composition does not cover full audio')
    else:
        require(all(type(timing.get(k)) is int for k in ('episode', 'start_tick', 'end_tick_inclusive'))
                and timing['episode'] >= 0 and timing['start_tick'] >= 0
                and timing['end_tick_inclusive'] - timing['start_tick'] + 1 == len(boundaries) - 1,
                'single-episode timing disagrees with PCM')
    return frames / 48000, names, segments, prefix


def camera_provenance(files, rows):
    raw = files.get('afterimage-source.json')
    if raw is None:
        return None
    require(len(raw) <= 1024**2, 'Afterimage source index too large')
    source = json.loads(raw)
    meta = json.loads(ET.fromstring(files['afterimage.svg']).find('{http://www.w3.org/2000/svg}metadata').text)
    require(source.get('schema_version') == 1 and source.get('camera') == 'cam_left'
            and source.get('source_controller') == 'manual' and source.get('selected_intervals') == 3000
            and type(source.get('source_intervals')) is int and 3000 <= source['source_intervals'] <= 3600
            and source.get('presentation_seconds') == 60 and source.get('clock') == 'concatenated source time'
            and meta.get('policy_identity', {}).get('controller') == 'male-original'
            and isinstance(source.get('frame_file_sha256'), str)
            and re.fullmatch('[0-9a-f]{64}', source['frame_file_sha256'])
            and source.get('frame_file_sha256') == meta['stimulus']['manifest'].get('frame_file_sha256')
            and isinstance(source.get('frames'), list) and len(source['frames']) == len(rows) == 600,
            'Afterimage camera source contract differs')
    for i, (entry, row) in enumerate(zip(source['frames'], rows)):
        require(entry.get('frame') == i and entry.get('source_interval') == i * 5
                and entry.get('presentation_seconds') == row['source_timestamp_seconds'] == i / 10
                and entry.get('frame_sha256') == row.get('frame_sha256')
                and isinstance(entry.get('frame_sha256'), str) and re.fullmatch('[0-9a-f]{64}', entry['frame_sha256'])
                and type(entry.get('episode')) is int and entry['episode'] >= 0
                and type(entry.get('tick')) is int and entry['tick'] >= 0
                and isinstance(entry.get('eyes'), list) and len(entry['eyes']) == 2
                and all(type(eye) is bool for eye in entry['eyes'])
                and type(entry.get('simulation_time_seconds')) in (int, float)
                and abs(entry['simulation_time_seconds'] - (entry['tick'] + 1) * .02) < 1e-7,
                'Afterimage frame/source provenance differs')
    return source


def route_captions(files):
    if 'routes-source.json' not in files:
        return None
    raw = files['routes-source.json']
    require(len(raw) <= 1024**2, 'route provenance exceeds limit')
    source = json.loads(raw)
    for name in ('borrowed-body.svg', 'one-map-many-lives.html'):
        require(len(files[name]) <= 16 * 1024**2
                and hashlib.sha256(files[name]).hexdigest() == source['files_sha256'][name],
                'route derivative hash differs')
    for key in ('parent_run_id', 'branch_run_id', 'snapshot_id'):
        require(isinstance(source.get(key), str) and re.fullmatch('[0-9a-f]{32}', source[key]), 'route identity differs')
    require(source['parent_run_id'] != source['branch_run_id'] and source.get('branch_tick') == 100
            and source.get('intervention') in ({'kind': 'move_goal', 'xy': [0., 0.]},
                {'kind': 'move_obstacle', 'index': 0, 'xy': [.75, -.75]}), 'route allocation differs')
    edit = source['intervention']
    edit_label = ('Goal moved to [0, 0]' if edit['kind'] == 'move_goal' else
                  'Obstacle 0 moved to [0.75, -0.75]; goal unchanged')
    nodes = ET.fromstring(files['borrowed-body.svg']).findall('{http://www.w3.org/2000/svg}metadata')
    require(len(nodes) == 1, 'one route metadata node required')
    body = json.loads(nodes[0].text)
    matches = re.findall(r'<pre id="comparison-metadata">(.*?)</pre>', files['one-map-many-lives.html'].decode(), re.S)
    require(len(matches) == 1, 'one comparison metadata node required')
    comparison = json.loads(html.unescape(matches[0]))['comparison']
    left, right = comparison['left'], comparison['right']
    require(body['run_id'] == left['run_id'] == source['parent_run_id']
            and right['run_id'] == source['branch_run_id'] and body['traces'] == left['traces']
            and right['provenance'].get('parent_run_id') == left['run_id']
            and right['provenance'].get('source_snapshot_id') == source['snapshot_id'], 'route lineage differs')
    counts = []
    for side, start in ((left, 0), (right, 100)):
        require(side['provenance'].get('controller') == 'flynn'
                and side['provenance'].get('control_interval_seconds') == .02
                and len(side['traces']) == 1, 'single-episode 50 Hz FLYNN routes required')
        trace = side['traces'][0]
        require(trace['episode'] == 0 and trace['start_tick'] == start
                and 2 <= len(trace['points']) <= 601 - start
                and all(isinstance(p, list) and len(p) == 2
                        and all(type(v) in (int, float) and math.isfinite(v) for v in p) for p in trace['points']),
                'route points or tick range differs')
        counts.append(len(trace['points']) - 1)
    edits = right['provenance'].get('interventions', [])
    require(len(edits) == 1 and edits[0].get('kind') == 'intervention'
            and edits[0].get('episode') == 0 and edits[0].get('episode_step') == 100
            and edits[0].get('change', {}).get('kind') == edit['kind']
            and edits[0]['change'].get('index') == edit.get('index')
            and edits[0]['change'].get('new', {}).get('xy') == edit['xy'], 'route intervention differs')
    a, b = counts
    require(a > 100, 'parent lacks its branch boundary')
    delta = [right['traces'][0]['points'][0][i] - left['traces'][0]['points'][100][i] for i in (0, 1)]
    return (f'Recorded FLYNN parent route: {a} intervals, {a + 1} points, {a * .02:g} simulation seconds. No physical pen marks.',
            f'Public FLYNN parent and labelled branch at tick 100. Parent: {a} intervals / {a * .02:g} simulation seconds; branch continuation: {b} intervals / {b * .02:g} simulation seconds. {edit_label}; controller unchanged. Shared post-snapshot window: tick boundaries 100–{100 + min(a - 100, b)} ({min(a - 100, b) * .02:g} simulation seconds), ending at the earlier outcome. Full routes retain their unequal ranges. No causal memory-effect claim.',
            f'Parent {source["parent_run_id"]}; branch {source["branch_run_id"]}; snapshot {source["snapshot_id"]}. Parent includes ticks before the branch; the branch starts at tick 100. Recorded branch-start XY offset from parent tick 100: [{delta[0]:.9g}, {delta[1]:.9g}] world units. Coordinates are shown unchanged. Source identities and the declared edit are retained in the original comparison and routes-source.json.')


def encounter_html(files):
    rows = alignment(files['afterimage.svg'])
    source = camera_provenance(files, rows)
    routes = route_captions(files)
    choir_duration, voices, segments, prefix = choir_details(files['counterfactual-choir.wav'])
    durations = (len(rows), rows[-1]['source_timestamp_seconds'] - rows[0]['source_timestamp_seconds'], rows[-1]['model_time_seconds'])
    captions = (
        ('afterimage', 'Afterimage', ('Authored model responses to scripted manual-controller left-camera footage. Source controller: manual; portrait controller: male-original. ' if source else 'Authored model responses to geometric frames. ') + 'Offline inference / recorded playback; not fly perception or biological activity.'),
        ('borrowed-body', 'Borrowed body', routes[0] if routes else 'Recorded south-change simulator route: 1,267 intervals, 1,268 points, 25.34 simulation seconds. No physical pen marks.'),
        ('one-map', 'One map, many possible lives', routes[1] if routes else 'Separate mirrored no-U cases: south 25.34 seconds; north 25.84 seconds. No paired intervention or causal memory-effect claim.'),
        ('choir', 'Counterfactual choir', f'{choir_duration:g}-second composed mapping of {html.escape(", ".join(voices))} model populations. Not biological audio or a counterfactual experiment.'),
        ('atlas', 'Atlas of what disappears', 'Reduced graph before/after isolating node 12781: 135 removed edges, 137 lost reachable input/output pairs. Structural analysis, not measured impairment.'),
        ('specimens', 'The space between two flies', 'One curated, unregistered DNge104 anatomical pair, shared micrometre scale, unequal coverage. No population sex inference.'))
    nav = ''.join(f'<a href="#{key}">{html.escape(title)}</a>' for key, title, _ in captions)
    sections = []
    for (key, title, caption), name in zip(captions, ARTIFACTS):
        if name.endswith('.svg'):
            media = f'<img src="{name}" alt="{html.escape(caption, quote=True)}" loading="lazy">'
        elif name.endswith('.html'):
            media = f'<iframe src="{name}" title="Recorded route comparison and provenance" sandbox="" loading="lazy"></iframe>'
        else:
            media = f'<p>Start at low volume. Playback ends after {choir_duration:g} seconds; repeats must be declared and recorded.</p><audio controls preload="none" src="{name}"></audio><button id="stop-audio" hidden>Stop audio and return to start</button>'
        inspector = ''
        if key == 'one-map' and routes:
            inspector = '<p>' + html.escape(routes[2]) + '</p><p><a href="routes-source.json">Route source and branch provenance</a></p>'
        if key == 'choir' and segments:
            table = ''.join(f"<tr><td>{s['episode']}</td><td>{s['output_start_sample'] / 48000:g}–{s['output_end_sample_exclusive'] / 48000:g}</td><td>{s['start_tick']}–{s['end_tick_inclusive']}</td></tr>" for s in segments)
            ending = 'Final episode uses a recorded prefix.' if prefix else 'Final selected episode is included in full.'
            inspector = f'<p>Composition of {len(segments)} recorded episodes. Episode resets are retained; loading and paused wall time are omitted. {ending}</p><details><summary>Episode boundaries</summary><div class="table-scroll"><table><caption>Source episodes in playback order</caption><thead><tr><th scope="col">Episode</th><th scope="col">Playback seconds</th><th scope="col">Source ticks (inclusive)</th></tr></thead><tbody>{table}</tbody></table></div></details>'
        if key == 'afterimage':
            note = ('60-second sample-and-hold presentation at 10 fps, on concatenated source time. '
                    'Source episode resets are retained; the portrait model carries hidden state across them. '
                    '<a href="afterimage-source.json">Source episodes, eye masks and frame hashes</a>. '
                    'Human artistic acceptance remains open.' if source else
                    'Insufficient for assessing sustained material. Manual inspection adds no frames or elapsed source time.')
            playback = ('<button id="play-portrait">Play 60-second portrait</button>'
                        '<button id="stop-portrait">Stop portrait and return to start</button>'
                        '<p id="portrait-status" role="status">Ready; playback has not started.</p>' if source else '')
            table = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in
                (r['frame'] + 1, r['source_timestamp_seconds'], r['model_time_seconds'], *r['action'], *r['point'])) + '</tr>' for r in rows)
            inspector = f'''<p>{durations[0]} frames / {durations[1]:.9g} source seconds / {durations[2]:.9g} model seconds.
{note}</p>
<details><summary>Inspect recorded responses one at a time</summary>
<div id="controls" hidden>{playback}<button id="previous">Previous frame</button><button id="next">Next frame</button>
<p id="frame-status" aria-live="polite"></p>
<svg viewBox="-400 -400 800 800" role="img" aria-labelledby="inspect-title inspect-description">
<title id="inspect-title">Recorded response-plane inspection</title><desc id="inspect-description">Exact chronological prefix on fixed axes ±360. The red marker is the sequence start; blue marks the selected response. Coincident responses remain coincident.</desc>
<rect x="-360" y="-360" width="720" height="720" fill="none" stroke="#8c8a83"/>
<path d="M -360 0 H 360 M 0 -360 V 360" fill="none" stroke="#8c8a83"/>
<polyline id="prefix" fill="none" stroke="#244c5a" stroke-width="2"/>
<circle cx="{rows[0]['point'][0]}" cy="{rows[0]['point'][1]}" r="4" fill="#aa392b"/>
<circle id="selected" r="4" fill="#244c5a"/></svg></div>
<div class="table-scroll"><table><caption>Exact recorded alignment; all frames, including coincident responses</caption>
<thead><tr><th>Frame</th><th>Source time (s)</th><th>Model time (s)</th><th>Velocity</th><th>Heading</th><th>x</th><th>y</th></tr></thead><tbody>{table}</tbody></table></div></details>'''
        sections.append(f'<section id="{key}" aria-labelledby="{key}-title"><h2 id="{key}-title">{title}</h2><p>{caption}</p><p><a href="{name}">Open original artifact and embedded provenance</a></p>{media}{inspector}<a href="#modes">Return to modes</a></section>')
    return ('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' file:; media-src 'self' file:; frame-src 'self' file:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>Palimpsest: six recorded encounters</title><style>
body{margin:0;background:#fff;color:#253746;font:1rem/1.6 system-ui,sans-serif}main{max-width:72rem;margin:auto;padding:clamp(1rem,4vw,3rem)}
h1,h2{font-family:Georgia,serif;line-height:1.2}h1{font-size:clamp(2rem,5vw,3.5rem)}h2{font-size:2rem}p{max-width:72ch}
a{color:#244c5a}a:focus-visible,button:focus-visible,summary:focus-visible,audio:focus-visible{outline:3px solid #005fcc;outline-offset:4px}
nav{display:flex;flex-wrap:wrap;gap:.6rem 1.6rem;background:#edf4f8;padding:1rem}section{margin:4rem 0;scroll-margin-top:1rem}
img,svg{display:block;max-width:100%;height:auto;margin:1rem auto}img{max-height:75vh;object-fit:contain}iframe{width:100%;height:38rem;border:1px solid #253746;box-sizing:border-box}
audio{display:block;max-width:100%;margin:1rem 0}button,summary{font:inherit;cursor:pointer}button{padding:.5rem .8rem;margin:.25rem}button:disabled{cursor:default}
details{margin:1rem 0;padding:1rem;background:#edf4f8}#controls svg{max-width:38rem}.table-scroll{overflow:auto}table{border-collapse:collapse}th,td{padding:.5rem;text-align:left;border-bottom:1px solid #b6c8d4;white-space:nowrap}
pre{white-space:pre-wrap;overflow-wrap:anywhere}footer{padding:1rem 0} [hidden]{display:none!important}
</style><main><h1>Palimpsest</h1><p>Six recorded encounters. Open this page locally; each original artifact retains its source identities and mapping.
No live model, simulator or rover runs here. Human artistic and independent operator acceptance remain open.</p>
<p>Declare your finite session, repeat policy, audience/use, custodian and retention before review. Record actual start/end, interruptions and any assistance. Stop audio before closing.</p>
<nav id="modes" aria-label="Artwork modes">''' + nav + '</nav>' + ''.join(sections) + '''
<footer><h2>Sources and review boundaries</h2><p>Source seconds describe the retained material, not live model performance.
''' + ('The route sources retain their registered parent and snapshot relationship.' if routes else 'The two route sources have no parent relationship.') + ''' Inspection and repeats do not extend the original recording.</p>
<p><a href="README.md">Original review guide</a> · <a href="THIRD_PARTY_NOTICES.md">Distinct source notices</a> · <a href="checksums.json">Original artifact checksums</a></p>
<details><summary>Original review guide as plain text</summary><pre>''' + html.escape(files['README.md'].decode('utf-8')) + '''</pre></details>
<p>Record keep, revise presentation or insufficient sample for each mode, with one reason. Missing judgment is not acceptance.
This encounter adds no scientific, biological, exhibition-duration or physical qualification.</p></footer>
<script id="source-index" type="application/json">''' + script_json(source) + '''</script>
<script id="alignment" type="application/json">''' + script_json(rows) + '''</script><script>
const rows=JSON.parse(document.getElementById('alignment').textContent);let frame=0;
const source=JSON.parse(document.getElementById('source-index').textContent);
const previous=document.getElementById('previous'),next=document.getElementById('next');
function inspect(){const row=rows[frame];document.getElementById('prefix').setAttribute('points',rows.slice(0,frame+1).map(r=>r.point.join(',')).join(' '));const marker=document.getElementById('selected');marker.setAttribute('cx',row.point[0]);marker.setAttribute('cy',row.point[1]);document.getElementById('frame-status').textContent=`Frame ${frame+1} of ${rows.length}; source time ${row.source_timestamp_seconds} s; model time ${row.model_time_seconds} s. Fixed axes ±360.`+(source?` Source episode ${source.frames[frame].episode}, tick ${source.frames[frame].tick}; eyes ${source.frames[frame].eyes.join(', ')}.`:'');previous.disabled=frame===0;next.disabled=frame===rows.length-1;}
previous.addEventListener('click',()=>{if(frame>0){frame--;inspect();}});next.addEventListener('click',()=>{if(frame<rows.length-1){frame++;inspect();}});inspect();document.getElementById('controls').hidden=false;
if(source){
 const play=document.getElementById('play-portrait'),stopPortrait=document.getElementById('stop-portrait'),status=document.getElementById('portrait-status');let timer=null,start=0;
 function stopPortraitPlayback(){if(timer!==null)cancelAnimationFrame(timer);timer=null;play.disabled=false;frame=0;inspect();status.textContent='Stopped; returned to start.';}
 function step(now){const elapsed=(now-start)/1000;const selected=Math.min(599,Math.floor(elapsed*10));if(frame!==selected){frame=selected;inspect();}previous.disabled=true;next.disabled=true;if(elapsed>=60){timer=null;play.disabled=false;inspect();status.textContent='Completed 60-second presentation; no repeat.';return;}timer=requestAnimationFrame(step);}
 play.addEventListener('click',()=>{frame=0;inspect();start=performance.now();play.disabled=true;previous.disabled=true;next.disabled=true;status.textContent='Playing 60 seconds at 10 fps; no repeat.';timer=requestAnimationFrame(step);});
 stopPortrait.addEventListener('click',stopPortraitPlayback);
 document.addEventListener('visibilitychange',()=>{if(document.hidden&&timer!==null)stopPortraitPlayback();});
 play.closest('details').addEventListener('toggle',event=>{if(!event.target.open&&timer!==null)stopPortraitPlayback();});
}
const audio=document.querySelector('audio'),stop=document.getElementById('stop-audio');stop.addEventListener('click',()=>{audio.pause();audio.currentTime=0;});stop.hidden=false;
</script></main></html>''').encode('utf-8')


def head():
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def registration(output):
    output = destination(output)
    clean = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT, check=True, capture_output=True, text=True)
    require(not clean.stdout, 'committed clean worktree required for registration')
    require(pin(ARCHIVE) == ARCHIVE_PIN, 'input ZIP pin differs')
    return {'schema_version': 1, 'head': head(), 'sources': {name: pin(ROOT / name) for name in SOURCES},
            'archive': ARCHIVE_PIN, 'output': str(output), 'limits': {'seconds': 120, 'output_bytes': OUTPUT_LIMIT,
            'free_bytes': FREE_FLOOR, 'headroom_bytes': HEADROOM}, 'qualification_claims': []}


def prepare(registered):
    output = destination(registered['output'])
    guard = Guard(output)
    guard.check()
    require(registration(output) == registered, 'registration/source/HEAD changed')
    guard.check()
    output.mkdir()
    receipt = {'status': 'failed', 'registration': registered, 'qualification_claims': []}
    try:
        guard.write('launched.json', (script_json(registered) + '\n').encode())
        files = read_archive(ARCHIVE, ARCHIVE_PIN, guard.check)
        page = encounter_html(files)
        for name, raw in files.items():
            guard.write(name, raw)
            require(pin(output / name) == {'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
                    'copied member differs')
        guard.write('index.html', page)
        guard.check()
        require(head() == registered['head'] and pin(ARCHIVE) == ARCHIVE_PIN
                and all(pin(ROOT / name) == value for name, value in registered['sources'].items()),
                'input/source pin changed before close')
        receipt.update(status='passed', files={name: pin(output / name) for name in (*MEMBERS, 'index.html')})
    except BaseException as error:
        receipt['error'] = type(error).__name__ + ': ' + str(error)
    receipt.update(elapsed_seconds_before_receipt=time.monotonic() - guard.start, output_bytes_before_receipt=guard.written)
    # Keep a failed receipt even after a breached limit; reserve 1 MiB for it.
    raw = (script_json(receipt) + '\n').encode()
    require(len(raw) <= 1024**2 and guard.written + len(raw) <= OUTPUT_LIMIT, 'receipt byte reserve exceeded')
    if receipt['status'] == 'passed':
        try:
            guard.check(len(raw))
        except ValueError as error:
            receipt.update(status='failed', error=str(error))
            raw = (script_json(receipt) + '\n').encode()
    with (output / 'result.json').open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return 0 if receipt['status'] == 'passed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--register', action='store_true', help='print source registration; does not prepare derivatives')
    parser.add_argument('--registration', type=Path)
    args = parser.parse_args()
    if args.register:
        require(args.registration is None, 'choose registration or preparation')
        print(script_json(registration(args.output)))
        return 0
    require(args.registration is not None, 'reviewed registration file required')
    with safe(args.registration).open('rb') as stream:
        raw = stream.read(1024**2 + 1)
    require(len(raw) <= 1024**2, 'registration exceeds byte cap')
    registered = json.loads(raw)
    require(registered['output'] == str(args.output.absolute()), 'registered output differs')
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt('outer deadline')))
    return prepare(registered)


if __name__ == '__main__':
    raise SystemExit(main())
