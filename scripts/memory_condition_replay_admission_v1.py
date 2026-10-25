"""Prospective cell admission; no successful qualification is trusted yet.

Only a separately reviewed source change may add an independently accepted
receipt to the empty pin set. Caller-supplied status is never execution authority.
The admitted session owns all receipt/source/model/runtime files until teardown.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
import copy
import math
from pathlib import Path, PurePosixPath
import sys
import time

from palimpsest import artifacts, assets, memory
from scripts import memory_family_compact_v4 as compact
from scripts.memory_condition_qualification_pins_v1 import TRUSTED_QUALIFICATION_PINS
from scripts.memory_family_replay_custody_v4 import HeldReplayFiles, _relative

ROOT = Path(__file__).resolve().parents[1]
MiB = 1024 ** 2
TRUST_ANCHOR_PATH = 'scripts/memory_condition_qualification_pins_v1.py'
EXTENSION_PATH = 'docs/plans/memory-condition-seal-v1-retained-condition-v1-protocol.json'
EXTENSION_SOURCES = (
    'docs/plans/memory-condition-seal-v1.md',
    'scripts/memory_condition_replay_admission_v1.py',
    'scripts/memory_family_condition_seal_v4.py',
)
RECEIPT_KEYS = {'schema', 'status', 'scope', 'protocol_sha256',
                'replay_consumer_sha256', 'inputs', 'model', 'runtime_identity',
                'model_provenance', 'controller_tensors', 'audit', 'claims'}


def _fields(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(label + ' has missing or unknown fields')


def _descriptor(value, maximum=MiB):
    _fields(value, {'path', 'size_bytes', 'sha256'}, 'Qualification descriptor')
    _relative(value['path'])
    if type(value['size_bytes']) is not int or not 0 <= value['size_bytes'] <= maximum:
        raise ValueError('Qualification descriptor size exceeds its bound')
    digest = value['sha256']
    if (type(digest) is not str or len(digest) != 64
            or any(char not in '0123456789abcdef' for char in digest)):
        raise ValueError('Qualification descriptor needs exact lowercase SHA-256')
    return value


def require_qualification_pin(descriptor):
    """Refuse unreviewed identity before any file access or numerical import."""
    _descriptor(descriptor)
    identity = tuple(descriptor[key] for key in ('path', 'size_bytes', 'sha256'))
    if identity not in TRUSTED_QUALIFICATION_PINS:
        raise PermissionError('No independently accepted exact qualification pin')


def _deadline(deadline):
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError('Qualification deadline must be finite numeric monotonic time')
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Qualification admission deadline expired')
    if remaining > 300:
        raise ValueError('Qualification admission exceeds 300 seconds')


def _base_sources():
    values = [{key: row[key] for key in ('path', 'size_bytes', 'sha256')}
              for row in compact.PROTOCOL['behavior_sources']]
    values += copy.deepcopy(compact.PROTOCOL['cell_replay']['upstream_sources'])
    values.append({'path': compact.PROTOCOL_PATH.relative_to(ROOT).as_posix(),
                   'size_bytes': len(compact.PROTOCOL_BYTES), 'sha256': compact.PROTOCOL_SHA256})
    return {row['path']: row for row in values}


def _validate_receipt(value):
    """Validate prospective metadata only; passing this function grants nothing."""
    _fields(value, RECEIPT_KEYS, 'Qualification admission receipt')
    cell_source = next(row for row in compact.PROTOCOL['behavior_sources']
                       if row['id'] == 'cell_replay')
    if (value['schema'] != 'memory-condition-cell-qualification-admission-v1'
            or value['status'] != 'accepted'
            or value['scope'] != 'three-historical-traces-full-model-encoded-cell-only'
            or value['protocol_sha256'] != compact.PROTOCOL_SHA256
            or value['replay_consumer_sha256'] != cell_source['sha256']
            or memory.canonical_bytes(value['claims']) != memory.canonical_bytes(compact.PROTOCOL['claims'])):
        raise ValueError('Qualification scope, consumer, protocol or claims differs')
    _fields(value['inputs'], {'sources', 'assets', 'runtime'}, 'Qualification input roles')
    for section in value['inputs'].values():
        _fields(section, {'root', 'files'}, 'Qualification input section')
        # Constructor checks canonical roots, fixed descriptor order and all bounds without I/O.
        HeldReplayFiles(section['root'], section['files'], time.monotonic() + 1)
        for row in section['files']:
            _descriptor(row, 1024 * MiB)
    sources = value['inputs']['sources']
    if sources['root'] != str(ROOT):
        raise ValueError('Qualification sources belong to another checkout')
    source_files = {row['path']: row for row in sources['files']}
    if TRUST_ANCHOR_PATH in source_files:
        raise ValueError('Qualification trust anchor must remain outside receipt source custody')
    if (any(source_files.get(path) != row for path, row in _base_sources().items())
            or not set((*EXTENSION_SOURCES, EXTENSION_PATH)) <= set(source_files)):
        raise ValueError('Qualification source closure is incomplete or rebound')
    _fields(value['model'], {'edge', 'checkpoint', 'seed'}, 'Qualification model')
    model = value['model']
    edge, checkpoint = _relative(model['edge']), _relative(model['checkpoint'])
    if (type(model['seed']) is not int or model['seed'] != 400
            or PurePosixPath(edge).name != 'connections_princeton.csv'
            or checkpoint != 'connectome_rnn_dagger_princeton_full_vision.pt'):
        raise ValueError('Qualification full-model identity differs')
    expected_assets = {edge, checkpoint,
                       *(str(PurePosixPath(edge).parent / name) for name in assets.MAPPING_NAMES)}
    if {row['path'] for row in value['inputs']['assets']['files']} != expected_assets:
        raise ValueError('Qualification assets require edge, checkpoint and all seven mappings exactly')
    python = Path(sys.executable).resolve()
    runtime = value['inputs']['runtime']
    if (runtime['root'] != str(python.parent) or len(runtime['files']) != 1
            or runtime['files'][0]['path'] != python.name):
        raise ValueError('Qualification runtime must hold the resolved running interpreter')
    identity = value['runtime_identity']
    _fields(identity, {'python', 'numpy', 'torch', 'torch_profile'}, 'Qualification runtime identity')
    if (type(identity['python']) is not list or any(type(item) is not int for item in identity['python'])
            or identity['python'] != [3, 11, 15] or identity['numpy'] != '2.2.5'
            or type(identity['torch']) is not str or identity['torch'].split('+')[0] != '2.9.0'
            or type(identity['torch_profile']) is not dict or not identity['torch_profile']):
        raise ValueError('Qualification numerical runtime identity differs')
    if any(type(value[key]) is not dict or not value[key]
           for key in ('model_provenance', 'controller_tensors')):
        raise ValueError('Qualification model and tensor identities must be nonempty objects')
    _fields(value['audit'], {'freeze', 'terminal', 'outcome_audit'}, 'Qualification audit')
    for row in value['audit'].values():
        _descriptor(row)
    if len({row['path'] for row in value['audit'].values()}) != 3:
        raise ValueError('Qualification audit paths must be distinct')


def _validate_extension(payload, source_rows):
    value = artifacts._json(payload)
    if (payload != memory.canonical_bytes(value)
            or value.get('schema') != 'memory-condition-seal-v1-protocol'
            or value.get('base_protocol_sha256') != compact.PROTOCOL_SHA256
            or memory.canonical_bytes(value.get('claims')) != memory.canonical_bytes(compact.PROTOCOL['claims'])):
        raise ValueError('Qualification condition extension differs')
    pins = value.get('source_pins')
    if type(pins) is not list:
        raise ValueError('Qualification extension source pins are absent')
    for row in pins:
        _descriptor(row)
    if [row['path'] for row in pins] != sorted(EXTENSION_SOURCES):
        raise ValueError('Qualification extension source pin roster differs')
    sources = {row['path']: row for row in source_rows}
    if any(sources.get(row['path']) != row for row in pins):
        raise ValueError('Qualification extension source pin identity differs')


def _load_policy(receipt, holders):
    import torch
    from palimpsest.flynn import load_policy
    torch.set_num_threads(1)
    model = receipt['model']
    return load_policy(ROOT, holders['assets'].path(model['edge']),
                       holders['assets'].path(model['checkpoint']), 'cpu', model['seed'])


def _check_policy(policy, receipt):
    import numpy as np
    import torch
    from palimpsest import snapshots
    from scripts import memory_family_cell_replay_v4 as cell
    cell._pinned_policy(policy)
    actual = {'python': list(sys.version_info[:3]), 'numpy': str(np.__version__),
              'torch': str(torch.__version__), 'torch_profile': snapshots._torch_profile()}
    if (memory.canonical_bytes(actual) != memory.canonical_bytes(receipt['runtime_identity'])
            or str(policy.device) != 'cpu' or policy.dtype != torch.float32
            or torch.get_num_threads() != 1 or torch.cuda.is_initialized()
            or any(module.training for module in policy.agent.modules())
            or any(parameter.requires_grad for parameter in policy.agent.parameters())
            or 'mujoco' in sys.modules or 'palimpsest.engine' in sys.modules):
        raise ValueError('Qualification live numerical runtime differs')
    if (memory.canonical_bytes(policy.provenance) != memory.canonical_bytes(receipt['model_provenance'])
            or memory.canonical_bytes(snapshots.controller_hashes(policy))
               != memory.canonical_bytes(receipt['controller_tensors'])):
        raise ValueError('Qualification live model or tensor identity differs')


class _Session:
    def __init__(self, policy, descriptor, receipt, holders, deadline):
        self._policy = policy
        self._descriptor = copy.deepcopy(descriptor)
        self._receipt = copy.deepcopy(receipt)
        self._holders = holders
        self._deadline = deadline
        self._active = True
        self._error = None

    def _require_active(self):
        if self._error is not None:
            raise self._error
        if not self._active:
            raise RuntimeError('Qualification session is closed')

    @property
    def policy(self):
        self._require_active()
        return self._policy

    @property
    def descriptor(self):
        self._require_active()
        return copy.deepcopy(self._descriptor)

    def recheck(self):
        self._require_active()
        try:
            _deadline(self._deadline)
            for held in self._holders.values():
                held.recheck()
            _check_policy(self._policy, self._receipt)
            _deadline(self._deadline)
        except BaseException as error:
            self._error = error
            raise


def _enter_holder(stack, holder, close_errors):
    value = holder.__enter__()
    def close():
        try:
            holder.__exit__(None, None, None)
        except BaseException as error:
            close_errors.append(error)
    stack.callback(close)
    return value


@contextmanager
def qualified_replay(evidence_root, descriptor, *, deadline):
    """Hold the independently admitted model and inputs; default always refuses."""
    _deadline(deadline)
    descriptor = copy.deepcopy(descriptor)
    require_qualification_pin(descriptor)
    stack = ExitStack()
    close_errors = []
    session = None
    first = None
    try:
        receipt_holder = _enter_holder(stack, HeldReplayFiles(evidence_root, [descriptor], deadline), close_errors)
        payload = receipt_holder.read(descriptor['path'], MiB)
        receipt = artifacts._json(payload)
        if payload != memory.canonical_bytes(receipt):
            raise ValueError('Qualification admission receipt must be canonical JSON')
        _validate_receipt(receipt)
        audit_rows = sorted(receipt['audit'].values(), key=lambda row: row['path'])
        if descriptor['path'] in {row['path'] for row in audit_rows}:
            raise ValueError('Qualification receipt cannot be one of its own audit inputs')
        holders = {'receipt': receipt_holder,
                   'audit': _enter_holder(stack, HeldReplayFiles(evidence_root, audit_rows, deadline), close_errors)}
        for role in ('sources', 'assets', 'runtime'):
            section = receipt['inputs'][role]
            holders[role] = _enter_holder(stack, HeldReplayFiles(section['root'], section['files'], deadline), close_errors)
        _validate_extension(holders['sources'].read(EXTENSION_PATH, MiB),
                            receipt['inputs']['sources']['files'])
        for held in holders.values():
            held.recheck()
        policy = _load_policy(receipt, holders)
        session = _Session(policy, descriptor, receipt, holders, deadline)
        session.recheck()
        yield session
    except BaseException as error:
        first = error
    finally:
        if session is not None:
            try:
                session.recheck()
            except BaseException as error:
                if first is None:
                    first = error
            session._active = False
        try:
            stack.close()
        except BaseException as error:
            if first is None:
                first = error
        if first is None and close_errors:
            first = close_errors[0]
    if first is not None:
        raise first
