"""Verify the pinned annotation asset and compare candidate rows with the API.

Run in an isolated Python 3.11 environment with pyarrow==25.0.1. This reads
annotations only; it neither extracts connectivity nor establishes eligibility.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform


def inspect(manifest_path):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.ipc as ipc

    if pa.__version__ != '25.0.1':
        raise ValueError('This recorded reader requires pyarrow==25.0.1')
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    manifest = json.loads(manifest_path.read_text())
    asset = manifest['annotation_asset']
    path = manifest_path.parent.parent.parent / asset['path']
    size = path.stat().st_size
    if size != asset['size_bytes'] or size > 20 * 1024**2:
        raise ValueError('Annotation size differs or exceeds the pilot cap')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != asset['sha256']:
        raise ValueError('Annotation SHA256 differs')
    with pa.memory_map(str(path), 'r') as source:
        table = ipc.open_file(source).read_all()
    if table.num_rows > 1_000_000 or table.num_columns > 128:
        raise ValueError('Annotation dimensions exceed the pilot cap')
    required = ['bodyId', 'type', 'instance', 'status', 'somaSide']
    if not set(required) <= set(table.column_names):
        raise ValueError('Missing required candidate annotation columns')
    candidates = manifest['candidates']
    if len(candidates) != 2 or len({c['bodyId'] for c in candidates}) != 2:
        raise ValueError('This pilot requires its two distinct declared candidates')
    rows = []
    for candidate in candidates:
        selected = table.select(required).filter(pc.equal(table['bodyId'], candidate['bodyId'])).to_pylist()
        if len(selected) != 1 or any(selected[0][key] != candidate[key] for key in required):
            raise ValueError('Raw/API candidate annotations disagree')
        rows.append(selected[0])
    return {'status': 'verified', 'reader': 'pyarrow.ipc.open_file/read_all',
            'python_version': platform.python_version(), 'pyarrow_version': pa.__version__,
            'asset_sha256': digest, 'asset_size_bytes': size,
            'row_count': table.num_rows, 'column_count': table.num_columns,
            'columns': [{'name': field.name, 'type': str(field.type),
                         'null_count': table[field.name].null_count} for field in table.schema],
            'candidate_rows': rows, 'candidate_fields_compared': required,
            'candidate_rows_match_api': True,
            'cropped_column_present': 'cropped' in table.column_names,
            'circuit_eligibility_verified': False,
            'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('data/manifests/malecns-pilot.json'))
    args = parser.parse_args()
    print(json.dumps(inspect(args.manifest.resolve()), indent=2, allow_nan=False))
