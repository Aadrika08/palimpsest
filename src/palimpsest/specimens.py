"""Offline, unregistered anatomical pairs with explicit curatorial provenance."""
import hashlib
import html
import json
import math
from pathlib import Path
import re
import textwrap

from . import artifacts

MAX_SWC_BYTES = 4 * 1024**2
MAX_NODES = 50_000
MAX_OUTPUT_BYTES = 16 * 1024**2
UNITS = {'nm': .001, '8nm': .008, 'um': 1.}
FIELDS = {'dataset', 'version', 'specimen', 'sex', 'cell_id', 'cell_type', 'side',
          'file', 'sha256', 'units', 'coordinate_space', 'coverage', 'license',
          'attribution', 'source_url'}


def parse_swc(raw, units):
    """Keep every node and edge; convert spatial values to micrometres only."""
    if units not in UNITS or len(raw) > MAX_SWC_BYTES:
        raise ValueError('Unsupported units or oversized SWC')
    nodes = {}
    try:
        for line in raw.decode('utf-8').splitlines():
            row = line.split('#', 1)[0].split()
            if not row:
                continue
            if len(row) != 7 or len(nodes) >= MAX_NODES:
                raise ValueError('SWC requires seven columns and at most 50000 nodes')
            node, kind, parent = int(row[0]), int(row[1]), int(row[6])
            values = [float(x) * UNITS[units] for x in row[2:6]]
            if (not 0 <= node < 2**63 or not -1 <= parent < 2**63 or kind < 0 or kind > 7
                    or node in nodes or parent == node
                    or any(not math.isfinite(x) or abs(x) > 1e9 for x in values) or values[3] < 0):
                raise ValueError('Invalid SWC identity or spatial value')
            nodes[node] = {'parent': parent, 'xyzr': values}
    except (UnicodeError, OverflowError) as error:
        raise ValueError('Invalid SWC encoding or number') from error
    if not nodes or any(n['parent'] != -1 and n['parent'] not in nodes for n in nodes.values()):
        raise ValueError('Empty SWC or missing parent')
    done = set()
    for node in nodes:
        path = set()
        cursor = node
        while cursor != -1 and cursor not in done:
            if cursor in path:
                raise ValueError('SWC parent cycle')
            path.add(cursor)
            cursor = nodes[cursor]['parent']
        done.update(path)
    return nodes


def _strings(value, keys):
    if (type(value) is not dict or set(value) != keys
            or any(type(x) is not str or not x.strip() or len(x) > 1000
                   or any(ord(c) < 32 for c in x) for x in value.values())):
        raise ValueError('Missing, unknown or invalid specimen provenance fields')


def load_pair(path):
    path = artifacts._safe_path(path)
    manifest_raw = artifacts._read(path, 64 * 1024)
    manifest = artifacts._json(manifest_raw)
    if (type(manifest) is not dict or set(manifest) != {'version', 'correspondence', 'specimens'}
            or type(manifest['version']) is not int or manifest['version'] != 1
            or type(manifest['specimens']) is not list or len(manifest['specimens']) != 2):
        raise ValueError('Require a version1 manifest with exactly two specimens')
    _strings(manifest['correspondence'], {'curator', 'evidence', 'uncertainty', 'source_url'})
    if any(len(manifest['correspondence'][key]) > 200 for key in ('evidence', 'uncertainty')):
        raise ValueError('Visible correspondence labels exceed 200 characters')
    paths, skeletons = [path], []
    for item in manifest['specimens']:
        _strings(item, FIELDS)
        if (any(len(item[key]) > 32 for key in ('dataset', 'version', 'cell_id', 'cell_type'))
                or len(item['coverage']) > 160):
            raise ValueError('Visible specimen labels exceed the fixed panel bounds')
        if (not re.fullmatch(r'[A-Za-z0-9_-]+\.swc', item['file'])
                or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])
                or item['sex'] not in ('male', 'female', 'unknown')
                or item['side'] not in ('left', 'right', 'midline', 'unknown')):
            raise ValueError('Invalid local SWC name, hash, sex or side')
        source = artifacts._safe_path(path.parent/item['file'])
        raw = artifacts._read(source, MAX_SWC_BYTES)
        if hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('SWC SHA256 differs from the curated manifest')
        skeletons.append(parse_swc(raw, item['units']))
        paths.append(source)
    if len(set(paths)) != 3:
        raise ValueError('Pair requires two distinct source files')
    artifacts._no_secrets(manifest)
    return manifest, skeletons, paths, hashlib.sha256(manifest_raw).hexdigest()


def _structure(nodes):
    bounds = [[min(n['xyzr'][i] for n in nodes.values()), max(n['xyzr'][i] for n in nodes.values())]
              for i in range(3)]
    return {'nodes': len(nodes), 'edges': sum(n['parent'] != -1 for n in nodes.values()),
            'roots': [i for i, n in nodes.items() if n['parent'] == -1], 'bounds_um': bounds}


def render_pair(manifest, skeletons, manifest_hash):
    structures = [_structure(n) for n in skeletons]
    span = max(1., *(b[1]-b[0] for s in structures for i, b in enumerate(s['bounds_um']) if i in (0, 2)))
    scale = 460 / span
    report = {'version': 1, 'artwork': 'the space between two flies', 'mode': 'offline anatomy',
        'manifest': manifest, 'manifest_sha256': manifest_hash, 'structures': structures,
        'projection': {'axes': ['native x', 'native z'], 'units': 'um', 'shared_pixels_per_um': scale,
            'centering': 'each native x/z bounding-box center; minimum viewport span 1um',
            'registration': 'none', 'smoothing': False, 'radii_rendered': False},
        'renderer_sha256': hashlib.sha256(artifacts._read(__file__, 1024**2)).hexdigest(),
        'qualification_claims': []}
    esc = html.escape
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1000" role="img" aria-labelledby="title desc">',
        '<title id="title">The space between two flies</title>',
        '<desc id="desc">Two curated skeletons, separate native coordinate spaces, one shared micrometre scale. No anatomical registration or population-level inference. Root circles preserve disconnected components.</desc>',
        '<metadata id="palimpsest-provenance">'+esc(json.dumps(report, sort_keys=True, allow_nan=False))+'</metadata>',
        '<rect width="1200" height="1000" fill="#f5f8fc"/>',
        '<g fill="#203444" font-family="sans-serif">',
        '<text x="40" y="55" font-family="Georgia,serif" font-size="32">The space between two flies</text>',
        '<text x="40" y="86" font-size="16">Offline anatomy · curated cell correspondence · separate coordinate spaces</text>']
    def text(x, y, value, width=60, size=14):
        lines = textwrap.wrap(value, width=width)
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}">')
        for i, line in enumerate(lines):
            parts.append(f'<tspan x="{x}" dy="{0 if i == 0 else 19}">{esc(line)}</tspan>')
        parts.append('</text>')
    for index, (item, nodes, structure) in enumerate(zip(manifest['specimens'], skeletons, structures)):
        x = 40 + 600*index
        text(x, 125, f"{item['dataset']} {item['version']} · {item['sex']} · {item['side']}", width=58)
        text(x, 170, f"{item['cell_type']} · {item['cell_id']}", width=58, size=17)
        cx, cz = (sum(structure['bounds_um'][i])/2 for i in (0, 2))
        color = ('#245b84', '#81562b')[index]
        parts.append(f'<g data-specimen="{index}" transform="translate({x+230} 450) scale({scale} {-scale}) translate({-cx} {-cz})" stroke="{color}" fill="none">')
        segments = []
        for node, value in nodes.items():
            px, _, pz, _ = value['xyzr']
            if value['parent'] == -1:
                parts.append(f'<circle data-root="{node}" cx="{px}" cy="{pz}" r="{3/scale}" stroke-width="{1/scale}"/>')
            else:
                qx, _, qz, _ = nodes[value['parent']]['xyzr']
                segments.append(f'M{px},{pz} L{qx},{qz}')
        # One independent move/line pair per edge avoids tens of thousands of DOM elements.
        parts.append(f'<path data-segments="{len(segments)}" d="{" ".join(segments)}" stroke-width="{.75/scale}"/>')
        parts.append('</g>')
        bar = 10**math.floor(math.log10(150/scale))
        parts.append(f'<path d="M{x},710 h{bar*scale}" stroke="#203444" stroke-width="2"/>')
        text(x, 735, f'{bar:g} µm · native x / z projection · root circles', width=58)
        text(x, 767, f"{structure['nodes']} skeleton nodes · {structure['edges']} segments · {len(structure['roots'])} roots", width=58)
        text(x, 805, item['coverage'], width=62)
    text(40, 870, manifest['correspondence']['evidence'], width=135)
    text(40, 924, 'Curatorial uncertainty: '+manifest['correspondence']['uncertainty'], width=135)
    text(40, 978, 'Unregistered reconstructions with unequal coverage and sampling. Size differences do not establish population-wide sex effects.', width=150)
    parts.append('</g></svg>')
    return ''.join(parts).encode('utf-8')


def export_specimens(manifest_path, output_path, *, storage_budget=None):
    manifest, skeletons, paths, digest = load_pair(manifest_path)
    before = artifacts._fingerprint(paths)
    # Revalidate bytes after the initial read so publication binds the parsed source.
    if any(hashlib.sha256(artifacts._read(p, MAX_SWC_BYTES)).hexdigest() != wanted
           for p, wanted in zip(paths, [digest, *[s['sha256'] for s in manifest['specimens']]])):
        raise ValueError('Specimen source changed during loading')
    payload = render_pair(manifest, skeletons, digest)
    output = artifacts._safe_path(output_path)
    if output in paths or output.suffix.lower() != '.svg' or len(payload) > MAX_OUTPUT_BYTES:
        raise ValueError('Require a new SVG distinct from sources and within 16MiB')
    if artifacts._fingerprint(paths) != before:
        raise ValueError('Specimen source changed during rendering')
    if storage_budget is not None:
        storage_budget.check(len(payload), path=output)
    stream = output.open('xb')
    try:
        with stream:
            stream.write(payload)
            if artifacts._fingerprint(paths) != before:
                raise ValueError('Specimen source changed during publication')
    except BaseException:
        output.unlink()
        raise
    return output
