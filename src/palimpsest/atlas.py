"""Offline structural atlas of the pinned, bounded MaleCNS neighborhood."""
import copy
import hashlib
import html
import math

from . import artifacts, male_model

MAX_OUTPUT_BYTES = 2 * 1024**2
LABEL = 'Directed connectivity only; lost paths do not establish lost memories or behavioural deficits.'


def analyze(graph, cut_nodes):
    """Isolate selected nodes without relabeling the original boundary sets."""
    if (type(cut_nodes) not in (list, tuple) or len(cut_nodes) > 32 or
            any(type(node) is not int or node not in graph['ids'] for node in cut_nodes) or
            len(set(cut_nodes)) != len(cut_nodes)):
        raise ValueError('Select at most 32 distinct existing node IDs')
    cuts = set(cut_nodes)
    changed = {**graph, 'edges': [edge for edge in graph['edges'] if not cuts.intersection(edge[:2])]}
    before, after = male_model.reachability(graph), male_model.reachability(changed)
    lost = {output: sorted(set(inputs) - set(after['by_output'][output]))
            for output, inputs in before['by_output'].items()}
    return {'version': 1, 'artwork': 'atlas of what disappears', 'label': LABEL,
            'intervention': {'kind': 'node-isolation', 'node_ids': sorted(cuts),
                'rule': 'Remove every incoming/outgoing edge incident to a selected node; retain IDs and query sets.'},
            'nodes': len(graph['ids']), 'edges_before': len(graph['edges']),
            'edges_after': len(changed['edges']), 'removed_edges': len(graph['edges']) - len(changed['edges']),
            'before': before, 'after': after, 'lost_input_ids_by_output': lost,
            'lost_input_output_pairs': sum(map(len, lost.values())),
            'before_topology_sha256': male_model.digest(graph['edges']),
            'after_topology_sha256': male_model.digest(changed['edges'])}


def render(graph, report):
    """Fixed circular coordinates convey identity, not anatomical position."""
    esc = html.escape
    metadata = esc(male_model.canonical(report).decode())
    ids, cuts = graph['ids'], set(report['intervention']['node_ids'])
    lost = set().union(*map(set, report['lost_input_ids_by_output'].values()))
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" role="img" aria-labelledby="title desc">',
        '<title id="title">Atlas of what disappears</title>',
        f'<desc id="desc">{esc(LABEL)} Two circular graph panels show original connectivity and selected node isolation. Orange dashed edges are removed; orange filled nodes lose a path to at least one endpoint. Crossed nodes are isolated. Node identities are in tooltips; full directed metrics and source hashes are embedded.</desc>',
        f'<metadata id="palimpsest-provenance">{metadata}</metadata>',
        '<rect width="1200" height="800" fill="#f4f0e7"/>',
        '<g font-family="sans-serif" fill="#202b2a">',
        '<text x="40" y="48" font-size="28">Atlas of what disappears</text>',
        '<text x="40" y="78" font-size="15">MaleCNS v1.0 · extracted neighborhood · offline structural analysis</text>',
        f'<text x="40" y="112" font-size="16">{len(ids)} nodes / {report["edges_before"]} directed edges · {report["removed_edges"]} removed · {report["lost_input_output_pairs"]} lost input–endpoint pairs</text>']
    for side, center in enumerate((300, 900)):
        coords = {node: (center + 225 * math.cos(2 * math.pi * i / len(ids) - math.pi / 2),
                         405 + 225 * math.sin(2 * math.pi * i / len(ids) - math.pi / 2))
                  for i, node in enumerate(ids)}
        pieces.append(f'<text x="{center}" y="155" text-anchor="middle" font-size="18">{"Original" if side == 0 else "Node isolation"}</text>')
        for pre, post, weight in graph['edges']:
            removed = side == 1 and bool(cuts.intersection((pre, post)))
            x1, y1 = coords[pre]; x2, y2 = coords[post]
            dash = ' stroke-dasharray="3 3"' if removed else ''
            pieces.append(f'<path d="M{x1:.3f},{y1:.3f} L{x2:.3f},{y2:.3f}" fill="none" stroke="{"#b44f29" if removed else "#456d69"}" stroke-width=".6" opacity="{.65 if removed else .10}"{dash}><title>{pre} → {post}; count {weight}{"; removed" if removed else ""}</title></path>')
        for node in ids:
            x, y = coords[node]
            endpoint = node in graph['outputs']
            color = '#b44f29' if side == 1 and node in lost else '#153f3a' if endpoint else '#f4f0e7'
            pieces.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{6 if endpoint else 3}" fill="{color}" stroke="#153f3a" stroke-width="1"><title>bodyId {node}{"; endpoint" if endpoint else "; artificial boundary input"}</title></circle>')
            if side == 1 and node in cuts:
                pieces.append(f'<path d="M{x-5:.3f},{y-5:.3f} l10,10 m-10,0 l10,-10" stroke="#b44f29" stroke-width="2"/>')
    pieces += ['<text x="40" y="675" font-size="14">Filled dark nodes: endpoints · orange fill: lost reachability · orange dashed edges: removed · crosses: isolated</text>',
        '<text x="40" y="702" font-size="14">Circular placement is not anatomy. Edge direction and positive counts are in tooltips and embedded metadata.</text>',
        f'<text x="40" y="730" font-size="14">{esc(LABEL)}</text>',
        f'<text x="40" y="757" font-size="12">Source graph SHA256: {esc(report["source"]["graph_sha256"])}</text>',
        '</g></svg>']
    return ''.join(pieces).encode('utf-8')


def export_atlas(graph_path, manifest_path, output_path, *, cut_nodes, storage_budget=None):
    paths = [artifacts._safe_path(graph_path), artifacts._safe_path(manifest_path)]
    before = artifacts._fingerprint(paths)
    graph = male_model.load_graph(*paths)
    report = analyze(graph, cut_nodes)
    report['source'] = {key: copy.deepcopy(graph[key]) for key in
        ('source_graph_sha256', 'graph_manifest_sha256', 'extraction_protocol_sha256', 'license', 'attribution', 'boundary')}
    report['source']['graph_sha256'] = report['source'].pop('source_graph_sha256')
    report['source']['dataset'] = 'male-cns:v1.0'
    report['source']['query_input_mapping'] = 'artificial boundary inputs; not biological sensors'
    report['graph'] = {key: graph[key] for key in ('ids', 'edges', 'inputs', 'outputs', 'type_labels', 'type_ids')}
    report['renderer'] = {'version': 1, 'layout': 'sorted node IDs around fixed equal-radius circles; no anatomical coordinates',
                          'source_sha256': hashlib.sha256(artifacts._read(__file__, 1024**2)).hexdigest()}
    artifacts._no_secrets(report)
    payload = render(graph, report)
    output = artifacts._safe_path(output_path)
    if output in paths or output.suffix.lower() != '.svg':
        raise ValueError('Atlas output must be a new SVG distinct from source files')
    if len(payload) > MAX_OUTPUT_BYTES:
        raise ValueError('Atlas output exceeds byte limit')
    if artifacts._fingerprint(paths) != before:
        raise ValueError('Atlas source changed during analysis')
    if storage_budget is not None:
        storage_budget.check(len(payload), path=output)
    stream = output.open('xb')
    try:
        with stream:
            stream.write(payload)
            if artifacts._fingerprint(paths) != before:
                raise ValueError('Atlas source changed during export')
    except BaseException:
        output.unlink()
        raise
    return output
