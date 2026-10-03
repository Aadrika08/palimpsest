"""Bounded public extraction of a reduced candidate neighborhood, not a model.

Neuron-only, total connection weights; never sum overlapping ROI rows. This
engineering reduction makes no biological sensory or behavioural assignment.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request


PROTOCOL = {'version': 1, 'dataset': 'male-cns:v1.0',
    'id': 'dnge104-strong-input-neighborhood-v1', 'endpoint_ids': [12781, 556329],
    'node_rule': 'endpoints plus direct Neuron inputs with total connection weight >= 20',
    'edge_rule': 'induced directed Neuron connections with total weight >= 1',
    'minimum_input_weight': 20, 'max_nodes': 256, 'max_edges': 4096,
    'max_response_bytes': 4 * 1024**2, 'timeout_seconds': 30,
    'boundary_scope': 'Neuron nodes only; non-Neuron segments remain unmeasured',
    'selection_basis': 'lowest threshold in feasibility grid [1,2,5,10,20,50] fitting 256-node cap',
    'biological_sensor_mapping': None, 'training_performed': False}
URL = 'https://neuprint.janelia.org/api/custom/custom'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def extract(output):
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'protocol': PROTOCOL, 'protocol_sha256': digest(PROTOCOL),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'queries': []}

    def query(name, cypher, columns, maximum):
        request = {'dataset': PROTOCOL['dataset'], 'cypher': cypher}
        req = urllib.request.Request(URL, data=json.dumps(request).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=PROTOCOL['timeout_seconds']) as response:
            payload = response.read(PROTOCOL['max_response_bytes'] + 1)
            if response.status != 200 or len(payload) > PROTOCOL['max_response_bytes']:
                raise ValueError('Public query failed or exceeded response cap')
        record = {'request': request, 'authorization_sent': False,
                  'response_sha256': hashlib.sha256(payload).hexdigest(),
                  'response_bytes': len(payload), 'response': json.loads(payload)}
        (output / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        report['queries'].append({'name': name, 'record_sha256': digest(record)})
        result = record['response']
        if result.get('columns') != columns or type(result.get('data')) is not list or len(result['data']) > maximum:
            raise ValueError('Unexpected query schema or excessive result count')
        if any(type(row) is not list or len(row) != len(columns) for row in result['data']):
            raise ValueError('Malformed query row')
        return result['data']

    try:
        endpoints = json.dumps(PROTOCOL['endpoint_ids'])
        selection = f'MATCH (n:Neuron)-[e:ConnectsTo]->(m:Neuron) WHERE m.bodyId IN {endpoints} AND e.weight >= 20 '
        count = query('count', selection + 'RETURN count(DISTINCT n) AS input_nodes, count(e) AS edges', ['input_nodes', 'edges'], 1)
        if len(count) != 1 or any(type(n) is not int or n < 0 for n in count[0]):
            raise ValueError('Invalid count response')
        if count[0][0] + 2 > PROTOCOL['max_nodes'] or count[0][1] > PROTOCOL['max_edges']:
            raise ValueError('Candidate neighborhood exceeds frozen caps')
        inputs = query('inputs', selection + 'RETURN DISTINCT n.bodyId AS bodyId ORDER BY bodyId LIMIT 257', ['bodyId'], PROTOCOL['max_nodes'])
        ids = sorted(set(PROTOCOL['endpoint_ids']) | {row[0] for row in inputs})
        if len(inputs) != count[0][0] or len(ids) > PROTOCOL['max_nodes'] or any(type(n) is not int or n <= 0 for n in ids):
            raise ValueError('Input identity/count differs')
        ids_json = json.dumps(ids)
        induced = f'MATCH (n:Neuron)-[e:ConnectsTo]->(m:Neuron) WHERE n.bodyId IN {ids_json} AND m.bodyId IN {ids_json} AND e.weight >= 1 '
        edge_count = query('edge-count', induced + 'RETURN count(e) AS edges', ['edges'], 1)
        if len(edge_count) != 1 or type(edge_count[0][0]) is not int or not 0 <= edge_count[0][0] <= PROTOCOL['max_edges']:
            raise ValueError('Induced edge count exceeds frozen cap')
        edges = query('edges', induced + 'RETURN n.bodyId AS pre, m.bodyId AS post, e.weight AS weight ORDER BY pre,post LIMIT 4097', ['pre', 'post', 'weight'], PROTOCOL['max_edges'])
        if len(edges) != edge_count[0][0] or len({tuple(row[:2]) for row in edges}) != len(edges):
            raise ValueError('Duplicate edges or changed count')
        if any(type(v) is not int or v <= 0 for row in edges for v in row) or any(a not in ids or b not in ids for a,b,_ in edges):
            raise ValueError('Invalid directed edge identity/weight')
        strong = [(a,b,w) for a,b,w in edges if b in PROTOCOL['endpoint_ids'] and w >= 20]
        if {a for a,_,_ in strong} != {row[0] for row in inputs} or len(strong) != count[0][1]:
            raise ValueError('Induced graph contradicts the input-selection query')
        if {b for _,b,_ in strong} != set(PROTOCOL['endpoint_ids']):
            raise ValueError('An endpoint has no retained strong input')
        nodes = query('nodes', f'MATCH (n:Neuron) WHERE n.bodyId IN {ids_json} RETURN n.bodyId AS bodyId,n.type AS type,n.instance AS instance,n.somaSide AS somaSide,n.status AS status ORDER BY bodyId LIMIT 257', ['bodyId','type','instance','somaSide','status'], PROTOCOL['max_nodes'])
        if [row[0] for row in nodes] != ids or any(v is not None and type(v) is not str for row in nodes for v in row[1:]):
            raise ValueError('Node annotations/identity differ')
        boundaries = {}
        for direction, condition in [('incoming',f'm.bodyId IN {ids_json} AND NOT n.bodyId IN {ids_json}'),
                                     ('outgoing',f'n.bodyId IN {ids_json} AND NOT m.bodyId IN {ids_json}')]:
            rows = query(direction + '-boundary', 'MATCH (n:Neuron)-[e:ConnectsTo]->(m:Neuron) WHERE ' + condition + ' AND e.weight >= 1 RETURN count(e) AS edges,sum(e.weight) AS weight', ['edges','weight'], 1)
            if len(rows) != 1 or any(type(v) is not int or v < 0 for v in rows[0]):
                raise ValueError('Invalid boundary counts')
            boundaries[direction] = dict(zip(['edges','weight'],rows[0]))
        graph = {'dataset': PROTOCOL['dataset'], 'protocol_sha256': report['protocol_sha256'],
                 'nodes': [dict(zip(['bodyId','type','instance','somaSide','status'],row)) for row in nodes],
                 'edges': edges, 'endpoints': PROTOCOL['endpoint_ids'], 'boundary': boundaries,
                 'input_candidates': [row[0] for row in inputs],
                 'claim': 'reduced anatomical topology; no biological sensory assignment or trained model'}
        (output / 'graph.json').write_text(json.dumps(graph, indent=2) + '\n')
        report.update(status='extracted', nodes=len(ids), edges=len(edges), retained_weight=sum(row[2] for row in edges),
                      graph_sha256=hashlib.sha256((output/'graph.json').read_bytes()).hexdigest(), boundary=boundaries,
                      biological_sensor_mapping_verified=False, r3_complete=False)
    except Exception as error:
        report.update(status='failed', error={'type':type(error).__name__,'message':str(error)[:2048]})
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = extract(args.output)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['status'] == 'extracted' else 1)
