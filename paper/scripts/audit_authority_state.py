#!/usr/bin/env python3
"""Read-only post-run audit of trusted, pinned MuJoCo cost snapshots.

This is retained-artifact evidence, not a runtime finite-value guarantee. Native
decoding is unsafe for hostile bytes; no Engine, inference or physics is run.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from palimpsest.snapshots import read_snapshot, state_digest
from paper.studies.authority_replay_v1.common import parse_json, require, STATUSES
from paper.studies.authority_replay_v1.analyze import _validate_identity
from paper.scripts.build_authority_evidence import EXECUTION_COMMITS_BY_PROTOCOL

CONDITIONS = ('null', 'synchronous', 'background', 'background_storage')


def finite_counts(value, *, native=False):
    """Scan container numbers and public native/model struct numeric views."""
    import numpy as np
    counts = dict(arrays=0, array_elements=0, scalars=0)
    # Retain wrappers: pybind may create temporary objects whose IDs get reused.
    seen = {}

    def visit(item, path, depth=0):
        require(depth <= 64, 'numeric state nesting exceeds limit')
        if isinstance(item, (np.ndarray, np.generic)):
            array = np.asarray(item)
            require(array.dtype.kind in 'buifc', 'unsupported numeric array: '+path)
            require(bool(np.isfinite(array).all()), 'nonfinite numeric array: '+path)
            counts['arrays'] += 1
            counts['array_elements'] += array.size
        elif type(item) in (int, float, complex):
            require(type(item) is int or bool(np.isfinite(item)), 'nonfinite numeric scalar: '+path)
            counts['scalars'] += 1
        elif type(item) is dict:
            for key, child in item.items(): visit(child, path+'.'+str(key), depth+1)
        elif type(item) in (list, tuple, set):
            for index, child in enumerate(item): visit(child, path+f'[{index}]', depth+1)
        elif native and type(item).__module__.startswith('mujoco.'):
            if id(item) in seen: return
            seen[id(item)] = item
            for name in dir(item):
                if not name.startswith('_'):
                    child = getattr(item,name)
                    if not callable(child): visit(child,path+'.'+name,depth+1)
        else:
            require(item is None or type(item) in (bool, str, bytes), 'unsupported state: '+path)
    visit(value,'state')
    return counts


def decode_native(snapshot):
    import mujoco
    native = mujoco.MjData.__new__(mujoco.MjData)
    native.__setstate__(snapshot['native_data'])
    return native


def audit_unit(row, raw_root, inventory=None):
    report = dict(unit_id=row['unit_id'], source_status=row['status'], status='not audited')
    if row['status'] != 'completed': return report
    try:
        root = Path(raw_root).resolve(strict=True)
        folder = root/'execution_overhead'/row['unit_id'].replace('/','__')
        states = {}
        for label, filename, field in (('raw','final-raw.snp','raw_snapshot_path'),
                                       ('normalized','final-normalized.snp','matched_snapshot_path')):
            path = folder/filename
            require(Path(row[field]) == path, 'retained unit snapshot path differs')
            require(path.is_file() and path.resolve().is_relative_to(root)
                    and path.resolve() == path, 'snapshot missing, symlinked or outside unit path')
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            report[label+'_file_sha256'] = digest
            if inventory is not None:
                entry = inventory.get(str(path.relative_to(root)))
                require(entry is not None and entry.get('sha256') == digest
                        and entry.get('size_bytes') == len(payload), 'snapshot file differs from retained inventory')
            states[label] = read_snapshot(path)
        report['finite'] = {key:finite_counts(value) for key,value in states.items()}
        import mujoco
        normalization = row['final_state_normalization']
        require(normalization['recorder_fields'] == ['application.source_run_id','application.event_prefix']
                and normalization['native_fields'] == ['timer.duration']
                and normalization['mujoco_version'] == mujoco.__version__, 'normalization declaration differs')
        natives = {key:decode_native(value) for key,value in states.items()}
        report['finite'].update({key+'_native':finite_counts(value,native=True) for key,value in natives.items()})
        report['finite_scope'] = 'all numeric container arrays/scalars; decoded MjData and public nested MuJoCo/model numeric views'
        for label in states:
            digest = hashlib.sha256(states[label]['native_data']).hexdigest()
            require(states[label]['native_sha256'] == digest, 'snapshot native SHA differs')
            require(row['raw_native_sha256' if label=='raw' else 'matched_native_sha256'] == digest,
                    'row native SHA differs')
        raw_digest = state_digest(states['raw'])
        report['raw_state_sha256'] = raw_digest
        require(raw_digest == row['raw_snapshot_state_sha256'], 'raw snapshot state digest differs')
        canonical = copy.deepcopy(states['raw'])
        for field in ('source_run_id','event_prefix'): canonical['application'].pop(field)
        require(state_digest(canonical) == row['raw_final_state_sha256'], 'recorder-excluded raw state differs')
        native = natives['raw']
        native.timer.duration[:] = 0.
        canonical['native_data'] = native.__getstate__()
        canonical['native_sha256'] = hashlib.sha256(canonical['native_data']).hexdigest()
        canonical_digest = state_digest(canonical)
        normalized_digest = state_digest(states['normalized'])
        report.update(canonical_state_sha256=canonical_digest, normalized_state_sha256=normalized_digest,
                      canonical_state_matches=canonical_digest == normalized_digest == row['final_state_sha256'])
        require(report['canonical_state_matches'], 'canonical state differs from retained normalized snapshot or row')
        report['status'] = 'passed'
    except Exception as exc:
        report.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    return report


def audit_summary(summary, raw_root):
    _validate_identity(summary['identity'])
    identity = summary['identity']
    require(EXECUTION_COMMITS_BY_PROTOCOL.get(identity['protocol_sha256']) == identity['commit'],
            'audit requires an exact pinned execution commit/protocol pair')
    root = Path(raw_root).resolve(strict=True)
    inventory_path = root/'analysis/raw-inventory.json'
    inventory_bytes = inventory_path.read_bytes()
    entries = parse_json(inventory_bytes.decode())
    require(isinstance(entries,list), 'raw inventory must be a list')
    inventory = {entry['path']:entry for entry in entries if entry.get('type')=='file'}
    require(len(inventory) == sum(entry.get('type')=='file' for entry in entries), 'duplicate raw inventory paths')
    rows = [row for row in summary['rows'] if row['kind']=='execution_overhead']
    expected = {f'overhead/{seed}/{condition}':(seed,condition) for seed in range(10) for condition in CONDITIONS}
    require(len(rows)==40 and {row['unit_id'] for row in rows}==set(expected), 'audit requires exactly forty declared cost rows')
    for row in rows:
        seed,condition = expected[row['unit_id']]
        require(type(row['seed']) is int and row['seed']==seed and row['condition']==condition
                and row['status'] in STATUSES and row['identity']==summary['identity'], 'cost row descriptor or identity differs')
    reports = [audit_unit(row,root,inventory) for row in rows]
    counts = {status:sum(row['status']==status for row in reports) for status in ('passed','failed','not audited')}
    return dict(schema_version=1, identity=summary['identity'], raw_root=str(root),
                raw_inventory_sha256=hashlib.sha256(inventory_bytes).hexdigest(), declared=40, counts=counts,
                status='failed' if counts['failed'] else 'passed' if counts['passed']==40 else 'incomplete', rows=reports,
                limitations=['Post-run retained snapshots only; no benchmark-time finite guard is established.',
                             'Trusted same-version MuJoCo native decoder; not safe for hostile snapshots.',
                             'Numeric native scope is exposed public MjData/model struct views, not opaque byte reinterpretation.'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('summary','raw-root','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        source=args.summary.read_bytes()
        result=audit_summary(parse_json(source.decode()),args.raw_root)
        result['summary_sha256']=hashlib.sha256(source).hexdigest()
        # Exclusive output prevents replacing source evidence or an earlier audit.
        with args.output.open('x') as stream: json.dump(result,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
        print(f"{result['status']}: {result['counts']}")
        return 0 if result['status']=='passed' else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'FAIL: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
