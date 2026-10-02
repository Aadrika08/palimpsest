"""Standalone, static presentations of validated recorded comparisons."""
import hashlib
import html
import json
import math
import xml.etree.ElementTree as ET

from . import artifacts
from .records import iter_ticks

MAX_HTML_BYTES = 16 * 1024**2
MAX_METADATA_BYTES = 4 * 1024**2
NS = 'http://www.w3.org/2000/svg'
COLORS = ('#245b84', '#8b5b12')


def _json(value):
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(',', ':'))


def _pre(value):
    return '<pre>' + html.escape(json.dumps(value, indent=2, allow_nan=False)) + '</pre>'


def _masks(data):
    """Summarize the eye flags actually recorded with each transition."""
    import numpy as np
    result = []
    for row in iter_ticks(data['run'] / 'recording'):
        eyes = None
        if 'eyes' in row:
            value = np.asarray(row['eyes'])
            if value.shape != (2,) or value.dtype.kind != 'b':
                raise ValueError('invalid recorded eye enable state')
            eyes = {'left': bool(value[0]), 'right': bool(value[1])}
        if result and result[-1]['episode'] == row['episode'] and result[-1]['eyes'] == eyes:
            result[-1]['end_tick_inclusive'] = row['tick']
        else:
            result.append({'episode': row['episode'], 'start_tick': row['tick'],
                           'end_tick_inclusive': row['tick'], 'eyes': eyes})
    return result


def _sources(data):
    files = [{'path': path.relative_to(data['run']).as_posix(), 'size_bytes': data['fingerprint'][index][2],
              'sha256': (hashlib.sha256(artifacts._read(path, artifacts.MAX_EVENTS)).hexdigest()
                         if index < 2 else data['chunks'][index - 2]['sha256'])}
             for index, path in enumerate(data['paths'])]
    return {'run_id': data['manifest']['run_id'], 'files': files,
            'recording_sha256': hashlib.sha256(_json(files).encode()).hexdigest(),
            'evidence_class': data['manifest'].get('evidence_class', 'recorded trial; no new execution')}


def _overlay(report, projection):
    arena = projection['arena']
    scale = 360 / arena
    if not math.isfinite(scale) or not math.isfinite(2 * arena):
        raise ValueError('invalid arena projection scale')
    root = ET.Element(f'{{{NS}}}svg', {'viewBox': '0 0 800 800', 'role': 'img', 'aria-labelledby': 'overlay-title overlay-description'})
    ET.SubElement(root, f'{{{NS}}}title', {'id': 'overlay-title'}).text = 'A solid route and B dashed route on the same coordinate scale'
    ET.SubElement(root, f'{{{NS}}}desc', {'id': 'overlay-description'}).text = 'Recorded coordinates only. Coincident routes remain separate; a circle and square mark recorded starts. World geometry is shown separately below.'
    group = ET.SubElement(root, f'{{{NS}}}g', {'transform': f'translate(400 400) scale({scale} {-scale})'})
    ET.SubElement(group, f'{{{NS}}}rect', {'x': str(-arena), 'y': str(-arena), 'width': str(2 * arena), 'height': str(2 * arena), 'fill': 'white', 'stroke': '#203444', 'stroke-width': str(1 / scale)})
    for index, key in enumerate(('left', 'right')):
        for trace in report[key]['traces']:
            if any(abs(value) > arena for point in trace['points'] for value in point):
                raise ValueError('recorded route exceeds the fixed arena projection; refusing to clip it')
            attributes = {'data-run-id': report[key]['run_id'], 'data-episode': str(trace['episode']),
                'points': ' '.join(f'{x},{y}' for x, y in trace['points']), 'fill': 'none',
                'stroke': COLORS[index], 'stroke-width': str((5 if index == 0 else 3) / scale)}
            if index:
                attributes['stroke-dasharray'] = f'{8 / scale} {6 / scale}'
            ET.SubElement(group, f'{{{NS}}}polyline', attributes)
            x, y = trace['points'][0]
            marker = {'data-start-marker': 'AB'[index], 'stroke': COLORS[index], 'stroke-width': str(2 / scale)}
            if index == 0:
                ET.SubElement(group, f'{{{NS}}}circle', {**marker, 'cx': str(x), 'cy': str(y), 'r': str(4 / scale), 'fill': COLORS[index]})
            else:
                ET.SubElement(group, f'{{{NS}}}rect', {**marker, 'x': str(x - 6 / scale), 'y': str(y - 6 / scale), 'width': str(12 / scale), 'height': str(12 / scale), 'fill': 'none'})
    return ET.tostring(root, encoding='unicode')


def _world_view(metadata, label):
    root = ET.fromstring(artifacts._svg(metadata))
    root.remove(root.find(f'{{{NS}}}metadata'))  # Full provenance appears once in the HTML.
    root.set('role', 'img')
    root.set('aria-labelledby', f'world-{label}')
    ET.SubElement(root, f'{{{NS}}}title', {'id': f'world-{label}'}).text = f'{label}: last recorded world per episode and recorded routes'
    if label == 'B':
        scale = 360 / metadata['projection']['arena']
        for line in root.iter(f'{{{NS}}}polyline'):
            line.set('stroke', COLORS[1])
            line.set('stroke-dasharray', f'{8 / scale} {6 / scale}')
    return ET.tostring(root, encoding='unicode')


def _render(metadata, views):
    report = metadata['comparison']
    def cell(value):
        return 'Not recorded' if value is None else _pre(value)
    rows = [('Run ID', [report[key]['run_id'] for key in ('left', 'right')])]
    for label, key in (('Controller', 'controller'), ('Profile', 'profile'), ('Scenario', 'scenario'),
                       ('Parent run', 'parent_run_id'),
                       ('Initial memory hashes', 'initial_memory'), ('U-swap records', 'memory_swaps')):
        rows.append((label, [report[side]['provenance'].get(key) for side in ('left', 'right')]))
    rows += [('Source snapshot', [report[side]['provenance'].get('source_snapshot_id') or report[side]['provenance'].get('snapshot_id') for side in ('left', 'right')]),
             ('Recorded eye masks', [report[side]['recorded_eye_masks'] for side in ('left', 'right')]),
             ('Final phase', [report[side]['final_phase'] for side in ('left', 'right')]),
             ('Source evidence', [source['evidence_class'] for source in metadata['sources']])]
    table = '<table><caption>Recorded source identities and conditions</caption><thead><tr><th scope="col">Condition</th><th scope="col">A · solid line, circle start</th><th scope="col">B · dashed line, square start</th></tr></thead><tbody>'
    table += ''.join(f'<tr><th scope="row">{label}</th><td>{cell(values[0])}</td><td>{cell(values[1])}</td></tr>' for label, values in rows) + '</tbody></table>'
    differences = ''.join('<details><summary>' + html.escape(change['field']) + '</summary><h3>A</h3>' + _pre(change['left']) + '<h3>B</h3>' + _pre(change['right']) + '</details>' for change in report['differences'])
    if not differences:
        differences = '<p>No differences in the compared recorded provenance fields.</p>'
    route_status = ('Recorded route arrays match exactly, including episode and start tick. This is not a statistical null-effect test.' if metadata['route_arrays_equal'] else
                    'Recorded route arrays differ. Starts, durations, inputs, controller state, and other conditions can contribute.')
    worlds = ''.join(f'<figure><h3>{label}: last recorded world</h3>{_world_view(view, label)}<figcaption>Final world geometry per episode; not a reconstruction of earlier geometry.</figcaption></figure>' for label, view in zip('AB', views))
    return ('''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>One map, many possible lives | Palimpsest</title>
<style>
body{margin:0;background:#edf2f4;color:#203444;font:15px/1.6 Verdana,sans-serif}main{max-width:72rem;margin:auto;padding:2rem}
h1{font:normal 2.6rem/1.2 Georgia,serif;max-width:22ch}h2{margin-top:2rem;font-size:1.3rem}h3{font-size:1rem}p{max-width:76ch}
table{width:100%;border-collapse:collapse;background:white}caption{text-align:left;font-weight:bold;padding:.6rem 0}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #b7c8d0;padding:.7rem;overflow-wrap:anywhere}thead th{background:#dce6ea}tbody th{width:20%}td{width:40%}
pre{margin:.2rem 0;white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 monospace}details{padding:.6rem 0;border-bottom:1px solid #b7c8d0}summary{cursor:pointer}summary:focus-visible,.table-scroll:focus-visible{outline:3px solid #245b84;outline-offset:3px}
figure{margin:0}svg{display:block;width:100%;height:auto}figcaption{font-size:.9rem}.overlay{max-width:48rem}.worlds{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2rem}.table-scroll{overflow-x:auto}
@media(max-width:700px){main{padding:1rem}h1{font-size:2rem}.worlds{grid-template-columns:1fr}table{min-width:36rem}}@media print{body{background:white}details{break-inside:avoid}}
</style></head><body><main>
<h1>One map, many possible lives</h1>
<p>Offline recorded comparison · static playback view. No live inference, new simulation, or policy rerun occurs in this document.</p>
<p>These recorded differences are descriptive; they do not establish causality. This presentation is not a controlled U-only experiment and does not independently verify parent snapshots or memory-effect claims.</p>
<h2>Source conditions</h2><div class="table-scroll" tabindex="0" aria-label="Source conditions table">''' + table + '</div>'
        + '<p>Eye flags describe recorded input channels: true means enabled, false means masked, and null means not recorded. Other goal/contact cues may still be available; inspect the observation profile.</p>'
        + '<h2>Recorded differences</h2><p>' + str(len(report['differences'])) + ' differing recorded fields. Expand a field to inspect both values.</p>' + differences
        + '<h2>Route overlay</h2><p>' + route_status + '</p><figure class="overlay">' + _overlay(report, metadata['projection'])
        + f'<figcaption>A: solid blue with circle start. B: dashed amber with square start. One shared projection: ±{metadata["projection"]["arena"]} recorded world units on each axis; y increases upward. No rescaling, offsets, or route smoothing between conditions. Separate episodes are not joined.</figcaption></figure>'
        + '<p>The overlay shows routes only. World conditions can differ; the final recorded worlds below and the provenance retain those differences. Equal route arrays do not establish equal internal activity or the absence of a memory effect.</p>'
        + '<div class="worlds">' + worlds + '</div><h2>Recorded lineage</h2>' + _pre(report['lineage'])
        + '<details><summary>Full recorded comparison and export provenance</summary><pre id="comparison-metadata">' + html.escape(_json(metadata))
        + '</pre></details></main></body></html>').encode('utf-8')


def export_comparison(left_path, right_path, output_path, *, storage_budget=None):
    """Export validated comparisons without changing the JSON comparison interface."""
    data = [artifacts._load(left_path), artifacts._load(right_path)]
    views = [artifacts._export_metadata(item) for item in data]
    if views[0]['projection'] != views[1]['projection']:
        raise ValueError('comparison requires matching fixed arena projections')
    report = artifacts.compare_runs(left_path, right_path)
    for key, item in zip(('left', 'right'), data):
        for event in item['events']:
            if 'run_id' in event and artifacts._id(event['run_id']) != artifacts._id(item['manifest']['run_id']):
                raise ValueError('recorded event run identity differs')
        report[key]['recorded_eye_masks'] = _masks(item)
    if report['left']['recorded_eye_masks'] != report['right']['recorded_eye_masks']:
        report['differences'].append({'field': 'recorded_eye_masks', 'left': report['left']['recorded_eye_masks'], 'right': report['right']['recorded_eye_masks']})
    metadata = {'version': 1, 'mode': 'offline recorded comparison', 'comparison': report,
        'sources': [_sources(item) for item in data], 'projection': views[0]['projection'],
        'route_arrays_equal': report['left']['traces'] == report['right']['traces'],
        'rendering': {'version': 'recorded-route-comparison-v1', 'A': 'solid blue, circle start', 'B': 'dashed amber, square start',
            'trace_coordinates': 'recorded world coordinates, unmodified', 'geometry_stage': 'last recorded transition per episode'}}
    artifacts._no_secrets(metadata)
    if len(_json(metadata).encode()) > MAX_METADATA_BYTES:
        raise ValueError('comparison metadata exceeds export limit')
    payload = _render(metadata, views)
    if len(payload) > MAX_HTML_BYTES:
        raise ValueError('comparison HTML exceeds export byte limit')
    output = artifacts._safe_path(output_path)
    if output.suffix.lower() != '.html' or any(output.is_relative_to(item['run'] / 'recording') for item in data):
        raise ValueError('comparison output must be HTML outside authoritative recordings')
    if any(artifacts._fingerprint(item['paths']) != item['fingerprint'] for item in data):
        raise ValueError('recording changed before comparison export')
    if storage_budget is not None:
        storage_budget.check(len(payload), path=output)
    with output.open('xb') as stream:
        try:
            stream.write(payload)
            stream.flush()
            if any(artifacts._fingerprint(item['paths']) != item['fingerprint'] for item in data):
                raise ValueError('recording changed during comparison export')
        except BaseException:
            try:
                stream.close()
            finally:
                output.unlink()
            raise
    return output
