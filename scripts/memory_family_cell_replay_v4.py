"""Actual FLYNN cell replay from retained inputs; never an execution grant.

The owner/producer supplies an already admitted model and keeps its input/model
custody open. This consumer checks the live policy, strict compact bytes and
decoded source snapshot. It does not authenticate a supplied snapshot ZIP path,
load model assets, execute physics, publish evidence or enable pruning.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack
import hashlib
import math
from pathlib import Path
import sys

from palimpsest import assets, memory, snapshots
from palimpsest.flynn import FlynnPolicy
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_raw_audit_v4 as audit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SHA256 = 'e319bb18e12110dbc096d62d3d6e9550c7b37434bf5e18e410c5410c21bb97e5'


def _equal(value, expected, label):
    if snapshots.state_digest(value) != snapshots.state_digest(expected):
        raise ValueError(f'Cell replay {label} differs')


def _array(value, shape, label):
    import numpy as np
    if (type(value) is not np.ndarray or value.dtype != np.float32
            or value.shape != shape or not np.isfinite(value).all()):
        raise ValueError(f'Cell replay {label} shape/dtype/value differs')
    return value.copy()


def _runtime(policy, snapshot):
    torch = policy.torch
    if (str(policy.device) != 'cpu' or policy.dtype != torch.float32
            or torch.get_num_threads() != 1
            or sys.version_info[:3] != (3, 11, 15)
            or str(torch.__version__).split('+')[0] != '2.9.0'
            or any(module.training for module in policy.agent.modules())
            or any(value.requires_grad for value in policy.agent.parameters())):
        raise ValueError('Cell replay requires eval CPU float32 one-thread immutable model')
    _equal(snapshots._torch_profile(), snapshot['identity']['torch'], 'runtime profile')


def _replay_rows(*, policy, rows, source_snapshot, operation, first_tick,
                 input_width, deadline):
    """Numerical core on the actual guarded policy; dimension-general for tests."""
    import numpy as np
    audit._public_deadline(deadline)
    if (type(policy) is not FlynnPolicy or operation not in ('source', 'condition')
            or type(first_tick) is not int or first_tick < 0
            or type(input_width) is not int or input_width < 1
            or policy.agent.cell.Nin != input_width
            or type(rows) is not list or not 1 <= len(rows) <= (1200 if operation == 'source' else 900)):
        raise ValueError('Cell replay identity, count or input width differs')
    if operation == 'source' and first_tick != 0:
        raise ValueError('Source cell replay must start at reset tick zero')
    _runtime(policy, source_snapshot)
    expected_tensors = copy.deepcopy(source_snapshot['application']['controller_tensors'])
    _equal(snapshots.controller_hashes(policy), expected_tensors, 'immutable model tensors')
    staged, _ = snapshots._stage_policy(source_snapshot['policy'], policy)
    end_hidden = _array(source_snapshot['policy']['hidden'], (1, policy.agent.cell.N), 'source hidden')
    source_before = snapshots.state_digest(source_snapshot)
    rows_before = snapshots.state_digest(rows)
    previous = policy._state()
    attributes = {name: (hasattr(policy, name), getattr(policy, name, None))
                  for name in ('failure_diagnostics', '_current_raw_output', '_encoded', '_raw')}
    cell = policy.agent.cell
    cache = {name: (hasattr(cell, name), getattr(cell, name, None))
             for name in ('_cached_alphas', '_alphas_dirty')}
    torch = policy.torch
    hidden = (torch.zeros_like(staged[0]) if operation == 'source' else staged[0].clone())
    try:
        cell._cached_alphas = None
        cell._alphas_dirty = True
        with torch.inference_mode():
            for offset, row in enumerate(rows):
                audit._deadline(deadline)
                if (type(row) is not dict or not {'encoded_input', 'raw_output', 'action'} <= set(row)
                        or type(row.get('episode')) is not int
                        or row['episode'] != 0 or type(row.get('tick')) is not int
                        or row['tick'] != first_tick + offset):
                    raise ValueError('Cell replay row cursor differs')
                encoded = _array(row['encoded_input'], (input_width,), 'encoded input')
                raw_expected = _array(row['raw_output'], (2,), 'recorded raw output')
                action_expected = _array(row['action'], (2,), 'recorded action')
                hidden, raw = cell(hidden, torch.from_numpy(encoded).reshape(1, 1, input_width),
                                   checkpoint_steps=False, store_sequence=False)
                audit._deadline(deadline)
                hidden_array = _array(hidden.detach().cpu().numpy(), (1, cell.N), 'outgoing hidden')
                raw_array = _array(raw.detach().cpu().numpy(), (1, 2), 'outgoing raw output')
                if raw.dtype != torch.float32 or hidden.dtype != torch.float32:
                    raise ValueError('Cell replay output dtype differs')
                action = raw.clone()
                action[:, 0] = torch.tanh(raw[:, 0]) * 3
                action[:, 1] = math.pi * torch.tanh(raw[:, 1])
                action_array = _array(action.detach().cpu().numpy(), (1, 2), 'mapped action')
                if (raw_array[0].tobytes() != raw_expected.tobytes()
                        or action_array[0].tobytes() != action_expected.tobytes()):
                    raise ValueError(f'Cell replay raw output or action differs at tick {row["tick"]}')
            if operation == 'source' and hidden_array.tobytes() != end_hidden.tobytes():
                raise ValueError('Cell replay acquired source endpoint differs')
        _runtime(policy, source_snapshot)
        _equal(snapshots.controller_hashes(policy), expected_tensors, 'final immutable model tensors')
        if (source_before != snapshots.state_digest(source_snapshot)
                or rows_before != snapshots.state_digest(rows)):
            raise ValueError('Cell replay supplied state/rows changed during replay')
        audit._deadline(deadline)
        return {'rows_checked': len(rows), 'raw_output_equal': True, 'action_equal': True,
                'source_endpoint_verified': operation == 'source',
                'initial_hidden_sha256': snapshots.state_digest(
                    np.zeros_like(end_hidden) if operation == 'source' else end_hidden),
                'final_hidden_sha256': snapshots.state_digest(hidden_array)}
    finally:
        policy._restore(previous)
        for target, saved in ((policy, attributes), (cell, cache)):
            for name, (present, value) in saved.items():
                if present:
                    setattr(target, name, value)
                elif hasattr(target, name):
                    delattr(target, name)


def _pinned_policy(policy):
    if (type(policy) is not FlynnPolicy
            or type(policy.agent).__module__ != 'agents.connectome_rnn_agent'
            or type(policy.agent).__name__ != 'ConnectomeAgent'
            or type(policy.agent.cell).__module__ != 'models.connectome_rnn_model'
            or type(policy.agent.cell).__name__ != 'LeakyConnectomeRNNCell'):
        raise ValueError('Cell replay requires actual pinned FLYNN agent/cell')
    raw = (ROOT / 'model_manifests/flynn-full-vision.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Cell replay pinned model manifest differs')
    manifest = assets.load_manifest(ROOT)
    checkpoint = next(row for row in manifest['files'] if row['id'] == 'checkpoint')
    provenance = policy.provenance
    if (provenance.get('upstream_commit') != assets.UPSTREAM_COMMIT
            or provenance.get('checkpoint_sha256') != checkpoint['sha256']
            or provenance.get('edge_sha256') != manifest['graph']['edge_identity']['sha256']
            or provenance.get('device') != 'cpu' or provenance.get('requested_device') != 'cpu'
            or provenance.get('dtype') != 'torch.float32' or policy.agent.cell.Nin != 4813):
        raise ValueError('Cell replay pinned full-model identity differs')
    for name in ('agents.connectome_rnn_agent', 'models.connectome_rnn_model'):
        module = sys.modules[name]
        if not Path(module.__file__).resolve().is_relative_to(ROOT / 'upstream/fly-gym'):
            raise ValueError('Cell replay pinned module was loaded from another checkout')


def replay_compact_cell(*, policy, bundle, raw_audit_receipt, source_snapshot, deadline):
    """Compare every compact row using actual admitted FLYNN, returning no grant."""
    audit._public_deadline(deadline)
    _pinned_policy(policy)
    audit._validate_receipt_shape(raw_audit_receipt)
    read = compact.read_compact(bundle, raw_audit_receipt=raw_audit_receipt)
    manifest = read['manifest']
    snapshot_before = snapshots.state_digest(source_snapshot)
    bundle_before = snapshots.state_digest(bundle)
    audit_before = snapshots.state_digest(raw_audit_receipt)
    application = source_snapshot['application']
    reference = read['snapshot_reference']
    operation = manifest['operation']
    if (application['schema_version'] != 8 or application['scenario'] != 'memory-decision-v2'
            or application['controller'] != 'flynn' or application['phase'] != 'paused'
            or type(application['episode_step']) is not int or not 0 < application['episode_step'] <= 1200
            or application['source_run_id'] != reference['source_run_id']
            or application['world_task_state']['case']['case_id'] != manifest['case_id']
            or application['seed'] != policy.provenance['seed']
            or source_snapshot['identity']['policy']['class'] != 'palimpsest.flynn.FlynnPolicy'
            or source_snapshot['identity']['policy']['device'] != 'cpu'
            or source_snapshot['identity']['policy']['dtype'] != 'torch.float32'):
        raise ValueError('Cell replay source snapshot/application identity differs')
    _equal(source_snapshot['identity']['policy']['provenance'], policy.provenance,
           'source policy provenance')
    if (operation == 'source' and (reference['kind'] != 'source'
            or manifest['run_id'] != reference['source_run_id']
            or manifest['row_count'] != application['episode_step'])
            or operation == 'condition' and reference['kind'] != 'shared-source'):
        raise ValueError('Cell replay source/condition boundary differs')
    with ExitStack() as custody:
        for row in compact.PROTOCOL['behavior_sources']:
            custody.enter_context(compact.bound_payload(ROOT,
                {key: row[key] for key in ('path', 'size_bytes', 'sha256')},
                2 * compact.MiB, deadline))
        for row in compact.PROTOCOL['cell_replay']['upstream_sources']:
            custody.enter_context(compact.bound_payload(ROOT, row, 2 * compact.MiB, deadline))
        result = _replay_rows(policy=policy, rows=read['rows'], source_snapshot=source_snapshot,
            operation=operation, first_tick=0 if operation == 'source' else application['episode_step'],
            input_width=4813, deadline=deadline)
        if (snapshot_before != snapshots.state_digest(source_snapshot)
                or bundle_before != snapshots.state_digest(bundle)
                or audit_before != snapshots.state_digest(raw_audit_receipt)):
            raise ValueError('Cell replay supplied compact evidence changed')
        _pinned_policy(policy)
        audit._deadline(deadline)
    result.update(schema='memory-family-cell-replay-v4', protocol_sha256=compact.PROTOCOL_SHA256,
        case_id=manifest['case_id'], run_id=manifest['run_id'], operation=operation,
        trace_digest=read['trace_digest'], source_snapshot_reference=copy.deepcopy(reference),
        claims=copy.deepcopy(compact.PROTOCOL['claims']))
    return result
