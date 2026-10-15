"""Finite puck-v3 layout minting and data-supplied scene admission.

Inventory discovery remains outside this module.  Admission consumes typed
snapshots and publishes only to an explicitly supplied fresh directory.
"""

import hashlib
import copy
import json
import math
import os
from pathlib import Path
import stat

from .task_mechanics import MAX_COUNTER, MAX_ITEMS


SCHEMA = 'puck-on-policy-layout-v1'
COLLECTION_SPLIT = 'on_policy_collection'
DEVELOPMENT_SPLIT = 'on_policy_development'
RESERVED_SCENE_IDS = (6110, 6111, 6112, 6113, 6120, 6121, 6122, 6123)
HELD_OUT_SCENE_IDS = (6200, 6201, 6202, 6203, 6204, 6205, 6206, 6207)
PROTOCOL_SHA256 = 'fe8b2615f965a114274a13aeb2d49c26d3f79e0920eee72bce4eb671adff3d13'
_ROW_FIELDS = {'version', 'kind', 'seed', 'split', 'slot', 'rover_pose',
               'puck_xy', 'goal_xy', 'initial_qvel'}
_INVENTORY_KINDS = {'ref', 'worktree', 'raw_registry', 'manifest'}
_ROOT_FIELDS = {'kind', 'path', 'resolved_path', 'exists', 'readable',
                'is_directory', 'is_symlink', 'identity_sha256'}
_RECORD_FIELDS = {'kind', 'name', 'root', 'identity_sha256', 'role',
                  'lineage_sha256', 'scenes', 'metadata'}
_SCENE_FIELDS = {'scene_id', 'canonical_scene_sha256',
                 'scientific_initial_sha256', 'payload_sha256'}
_INVENTORY_FIELDS = {'version', 'complete', 'remote_refs_fresh',
                     'held_out_accessed', 'roots', 'records'}
_RESERVATION_FIELDS = {
    'version', 'kind', 'lineage_sha256', 'scene_ids', 'inventory_before_sha256',
    'inventory_after_sha256', 'inventory', 'occupied_scene_ids',
    'occupied_canonical_scene_sha256', 'occupied_scientific_initial_sha256',
    'occupied_payload_sha256',
}
_SCENE_MANIFEST_FIELDS = {
    'version', 'kind', 'lineage_sha256', 'reservation_sha256', 'scene_ids', 'scenes',
}
_SCENE_ENTRY_FIELDS = {
    'scene_id', 'slot', 'split', 'canonical_scene_sha256',
    'scientific_initial_sha256', 'payload_sha256', 'layout',
}
_COMMIT_RECEIPT_FIELDS = {
    'version', 'kind', 'target', 'manifest_sha256', 'manifest_bytes',
    'reservation_sha256', 'protocol_sha256',
}
_ADMISSION_RECEIPT_FIELDS = {
    'version', 'kind', 'target', 'receipt',
    'manifest_sha256', 'manifest_bytes', 'manifest_identity',
    'receipt_sha256', 'receipt_bytes', 'receipt_identity',
    'reservation_sha256', 'protocol_sha256',
}
_MAX_JSON_BYTES = 64 * 1024 * 1024
_MAX_COMMIT_BYTES = 4096

_QUERY_STATE_FIELDS = {'native_state', 'observation', 'python_rng', 'numpy_rng',
                       'torch_rng', 'environment_rng', 'space_rng'}
_INTERVAL_ROW_FIELDS = {'episode', 'tick', 'inputs', 'student_inputs', 'teacher_action',
                        'predicted_action', 'action', 'teacher_query_mode_before', 'teacher_query_mode_after',
                        'supervisor_mode_before', 'supervisor_mode_after'}
_STAGED_INTERVAL_FIELDS = {'version', 'kind', 'protocol_sha256', 'row', 'own_pending',
                           'teacher_mode_before', 'teacher_mode_after',
                           'query_before_sha256', 'query_after_sha256'}


def stage_interval(sensors, world, teacher_mode, own, model, *, terminal_reason,
                   capture_query_state):
    """Stage label/action/cursors without stepping or publishing a live interval.

    The capture seam must be independently qualified before native use; matching
    supplied snapshots alone cannot prove that the seam covers all native state.
    """
    import numpy as np
    from . import puck_learning as learning, puck_teacher as teacher, puck_student as student
    from .snapshots import state_digest

    if terminal_reason is not None:
        raise ValueError('No on-policy decision after a terminal outcome')
    pending = learning.prepare(sensors, own)
    if teacher_mode != pending['before']['mode']:
        raise ValueError('Teacher and own BEFORE modes differ')

    def capture():
        state = capture_query_state()
        if type(state) is not dict or set(state) != _QUERY_STATE_FIELDS:
            raise ValueError('Complete explicit query state capture required')
        try:
            return state_digest({'captured': state, 'sensors': sensors,
                                 'inputs': pending['inputs'], 'own': own, 'world': world})
        except TypeError as error:
            raise ValueError('Query state capture contains unsupported state') from error

    before = capture()
    label, next_mode, teacher_pending = teacher.decide(sensors, world, teacher_mode, own)
    after = capture()
    if before != after or state_digest(teacher_pending) != state_digest(pending):
        raise ValueError('Teacher query changed protected state or effective inputs')
    if next_mode != pending['after']['mode']:
        raise ValueError('Teacher and own AFTER modes differ')
    label = student.action(np.asarray(label, np.float64))
    live_before = state_digest({'sensors': sensors, 'world': world, 'own': own})
    predicted, student_pending = student.decide(sensors, own, model)
    if (state_digest(student_pending) != state_digest(pending) or
            state_digest({'sensors': sensors, 'world': world, 'own': own}) != live_before):
        raise ValueError('Student inference changed staged inputs or own cursor')
    predicted = student.action(predicted)
    row = {'episode': 0, 'tick': own['tick'], 'inputs': sensors.copy(),
           'student_inputs': pending['inputs'].copy(), 'teacher_action': label,
           'predicted_action': predicted.copy(), 'action': predicted.copy(),
           'teacher_query_mode_before': np.uint8(learning.MODES[teacher_mode]+1),
           'teacher_query_mode_after': np.uint8(learning.MODES[next_mode]+1),
           'supervisor_mode_before': np.uint8(learning.MODES[own['mode']]),
           'supervisor_mode_after': np.uint8(learning.MODES[pending['after']['mode']])}
    return {'version': 1, 'kind': 'puck-on-policy-staged-interval-v1',
            'protocol_sha256': PROTOCOL_SHA256, 'row': row, 'own_pending': copy.deepcopy(pending),
            'teacher_mode_before': teacher_mode, 'teacher_mode_after': next_mode,
            'query_before_sha256': before, 'query_after_sha256': after}


def admit_completed_interval(staged, own, teacher_mode, *, completed_tick, publication_receipt):
    """Return both cursors after a supplied exact successful row receipt.

    This pure admission function does not perform or attest a native step or a
    durable writer commit. The later owner must qualify those receipt semantics.
    """
    from . import puck_learning as learning, puck_student as student
    from .snapshots import state_digest

    before = learning.validate_cursor(own)
    if (type(staged) is not dict or set(staged) != _STAGED_INTERVAL_FIELDS or
            type(staged['version']) is not int or staged['version'] != 1 or
            staged['kind'] != 'puck-on-policy-staged-interval-v1' or
            staged['protocol_sha256'] != PROTOCOL_SHA256 or
            type(completed_tick) is not int or completed_tick != before['tick']+1 or
            teacher_mode != before['mode'] or staged['teacher_mode_before'] != teacher_mode):
        raise ValueError('Staged interval predecessor or completed tick differs')
    query_digest = _digest(staged['query_before_sha256'], 'Query state digest')
    if staged['query_after_sha256'] != query_digest:
        raise ValueError('Teacher query isolation receipt differs')
    row = staged['row']
    if (type(row) is not dict or set(row) != _INTERVAL_ROW_FIELDS or
            type(row['episode']) is not int or row['episode'] != 0 or
            type(row['tick']) is not int or row['tick'] != before['tick']):
        raise ValueError('Exact contiguous v3 interval row required')
    expected = learning.prepare(row['inputs'], before)
    if state_digest(staged['own_pending']) != state_digest(expected):
        raise ValueError('Staged supervisor transition differs from sensors')
    next_own = learning.commit(own, staged['own_pending'], completed_tick)
    if staged['teacher_mode_after'] != next_own['mode']:
        raise ValueError('Teacher and own AFTER modes differ')
    if state_digest(row['student_inputs']) != state_digest(expected['inputs']):
        raise ValueError('Exact BEFORE-mode features differ')
    for name, code in (('teacher_query_mode_before', learning.MODES[before['mode']]+1),
                       ('teacher_query_mode_after', learning.MODES[next_own['mode']]+1),
                       ('supervisor_mode_before', learning.MODES[before['mode']]),
                       ('supervisor_mode_after', learning.MODES[next_own['mode']])):
        learning._mode(row[name], code)
    student.action(row['teacher_action'])
    predicted, executed = student.action(row['predicted_action']), student.action(row['action'])
    if predicted.tobytes() != executed.tobytes():
        raise ValueError('Only the predicted student action may execute')
    expected_receipt = {'version': 1, 'kind': 'puck-on-policy-row-publication-v1',
                        'protocol_sha256': PROTOCOL_SHA256, 'status': 'published',
                        'completed_tick': completed_tick, 'row_sha256': state_digest(row),
                        'staged_sha256': state_digest(staged)}
    if state_digest(publication_receipt) != state_digest(expected_receipt):
        raise ValueError('Exact successful v3 row publication receipt required')
    return next_own, staged['teacher_mode_after']


_INTERVAL_EVENT_FIELDS = {'completed_tick', 'state_before', 'world_before', 'contact_before',
                          'state', 'world', 'contact', 'reward',
                          'supervisor_mode_before', 'supervisor_mode_after',
                          'teacher_query_mode_before', 'teacher_query_mode_after'}
_INTERVAL_COMMIT_FIELDS = {'version', 'kind', 'protocol_sha256', 'completed_tick',
                           'previous_commit_sha256', 'row_sha256', 'staged_sha256',
                           'arrays_sha256', 'event_sha256', 'query_sha256', 'files'}
_INTERVAL_FILES = ('recording/manifest.json', 'recording/events.jsonl',
                   'recording/chunks/000000.npz')
_PUCK_CAPTURE_FIELDS = ('_puck_bindings', '_puck_profile_identity', '_puck_reset_seed',
                        'base_body_id', 'goal_site_id', 'left_hinge_id', 'right_hinge_id',
                        'cam_left_id', 'cam_right_id', 'obstacle_ids', 'obstacle_body_ids',
                        'obstacle_x_joint_ids', 'obstacle_y_joint_ids',
                        '_obstacle_x_qposadr', '_obstacle_y_qposadr')


def capture_query_state(env, observation, *, application):
    """Observe a paused native owner; numerical coverage remains unqualified."""
    from . import snapshots
    import mujoco
    if (mujoco.get_mjcb_control() is not None or
            vars(env).get('_np_random', vars(env).get('np_random')) is None):
        raise ValueError('Paused callback-free owner with initialized RNG required')
    initial_native, full_model = env.data.__getstate__(), env.model.__getstate__()
    if (type(initial_native) is not bytes or type(full_model) is not bytes or
            len(initial_native)+len(full_model) > 8*1024**2):
        raise ValueError('Native query bytes exceed 8 MiB')
    snapshot = snapshots.capture(env, observation, application=application)
    if snapshot['native_data'] != initial_native or env.model.__getstate__() != full_model:
        raise ValueError('Native/model state changed during query capture')
    rng = snapshot.pop('rng')
    observed = snapshot.pop('observation')
    native = {'snapshot': snapshot, 'full_model': full_model,
              'puck_wrapper': snapshots._fields(env, _PUCK_CAPTURE_FIELDS),
              'planner_cache': None if not hasattr(env, 'planner') else
                  snapshots._fields(env.planner, snapshots.ASTAR_CACHE)}
    if type(native['full_model']) is not bytes or len(native['full_model']) > 8*1024**2:
        raise ValueError('Bounded exact native model bytes required')
    result = snapshots._copy({'native_state': native, 'observation': observed,
        'python_rng': rng['python'], 'numpy_rng': rng['numpy'],
        'torch_rng': {'cpu': rng['torch_cpu'], 'cuda': rng['torch_cuda']},
        'environment_rng': {'state': rng['environment'], 'seed': rng['environment_seed']},
        'space_rng': rng['spaces']})
    def payload_bytes(value):
        if type(value) is bytes: return len(value)
        if hasattr(value, 'nbytes'): return value.nbytes
        if type(value) is dict: return sum(len(k.encode())+payload_bytes(v) for k,v in value.items())
        if type(value) in (list,tuple,set): return sum(payload_bytes(v) for v in value)
        return len(json.dumps(value,allow_nan=False).encode())
    if payload_bytes(result) > 8*1024**2:
        raise ValueError('Query capture payload exceeds 8 MiB')
    return result


def _interval_receipt(staged, completed_tick):
    from .snapshots import state_digest
    return {'version': 1, 'kind': 'puck-on-policy-row-publication-v1',
            'protocol_sha256': PROTOCOL_SHA256, 'status': 'published',
            'completed_tick': completed_tick, 'row_sha256': state_digest(staged['row']),
            'staged_sha256': state_digest(staged)}


def _interval_payload(staged, arrays, event, completed_tick):
    import numpy as np
    from .snapshots import state_digest
    receipt = _interval_receipt(staged, completed_tick)
    admit_completed_interval(staged, staged['own_pending']['before'],
                             staged['teacher_mode_before'], completed_tick=completed_tick,
                             publication_receipt=receipt)
    if (type(arrays) is not dict or type(event) is not dict or
            set(event) != _INTERVAL_EVENT_FIELDS or
            {'teacher_mode_before', 'teacher_mode_after'} & set(arrays) or
            not (_INTERVAL_ROW_FIELDS-{'episode', 'tick'}) <= set(arrays) or
            any(state_digest(arrays[k]) != state_digest(v) for k,v in staged['row'].items()
                if k not in ('episode', 'tick')) or
            any(not isinstance(a, (np.ndarray, np.generic)) or a.dtype.kind not in 'biufc' or
                not np.isfinite(a).all() for a in arrays.values()) or
            sum(a.nbytes for a in arrays.values()) > 128*1024 or
            type(event['completed_tick']) is not int or event['completed_tick'] != completed_tick or
            type(event['state']) is not dict or type(event['state'].get('tick')) is not int or
            event['state']['tick'] != completed_tick or
            any(event[k] != v for k,v in {
                'supervisor_mode_before': staged['own_pending']['before']['mode'],
                'supervisor_mode_after': staged['own_pending']['after']['mode'],
                'teacher_query_mode_before': staged['teacher_mode_before'],
                'teacher_query_mode_after': staged['teacher_mode_after']}.items())):
        raise ValueError('Exact bounded v3 numeric row and completed event required')
    if len(_canonical_bytes(event, 'v3 interval event')) > 16*1024:
        raise ValueError('V3 interval event exceeds bound')
    from . import puck_profile as puck
    from .body_profile import effective_control
    normalized = json.loads(_canonical_bytes(event, 'V3 event'))
    before,after = normalized['world_before'],normalized['world']
    row_action = staged['row']['action'].tolist()
    expected_state,expected_reward = puck.advance(normalized['state_before'],after,normalized['contact'],row_action)
    expected_task = {'state':normalized['state'],'world':after,'contact':normalized['contact'],
                     'own_supervisor_cursor': {**staged['own_pending']['after'],'tick':completed_tick}}
    def world_array(world):
        return np.array([world['time_s'],*world['rover_pose'],*world['puck_xyz'],
                         *world['puck_velocity_xy'],*world['goal_xy']],np.float64)
    required_native = {'native_completed_tick':np.asarray(completed_tick,np.int64),
        'native_data_time_s':np.asarray(after['time_s'],np.float64),
        'world_before':world_array(before),'world_after':world_array(after),
        'reward':np.asarray(expected_reward,np.float64),
        'ctrl':np.asarray(effective_control(row_action),np.float64),
        'task_sha256':np.frombuffer(bytes.fromhex(state_digest(expected_task)),np.uint8)}
    if (state_digest(expected_state) != state_digest(normalized['state']) or
            type(normalized['reward']) not in (int,float) or normalized['reward'] != expected_reward or
            state_digest(puck.project(before,normalized['contact_before'])) != state_digest(staged['row']['inputs']) or
            normalized['contact_before']['tick'] != completed_tick-1 or
            any(k not in arrays or state_digest(np.asarray(arrays[k])) != state_digest(v)
                for k,v in required_native.items())):
        raise ValueError('V3 native packet differs from exact task/contact transition')
    return receipt


def _verify_interval_directory(path, descriptor, identity):
    _publication_root(path)
    _verify_publication_root(path, descriptor, identity, 'V3 transaction directory')


def _interval_file_inventory(row_root, directories):
    result = {}
    for name in _INTERVAL_FILES:
        path = row_root/name
        directory, identity = directories[path.parent]
        raw, info = _read_exact_file(path.parent, path, 2*1024**2, 'v3 interval file',
            directory=directory, root_identity=identity, return_identity=True)
        result[name] = {'sha256': _sha256(raw), 'bytes': len(raw), 'identity': list(info)}
    return result


def _decode_interval_recording(row_root, directories, completed_tick, *, maximum=None):
    """Exhaust a finished candidate and bind its decoded content to stable files."""
    from .records import FORMAT, _json, iter_ticks
    for path,(descriptor,identity) in directories.items():
        _verify_interval_directory(path,descriptor,identity)
    files = _interval_file_inventory(row_root,directories)
    record = row_root/'recording'
    descriptor,identity = directories[record]
    manifest_raw = _read_exact_file(record,record/'manifest.json',2*1024**2,
        'V3 recording manifest',directory=descriptor,root_identity=identity)
    manifest = json.loads(manifest_raw)
    if maximum is None:
        maximum = manifest.get('recording_max_bytes') if type(manifest) is dict else None
    if type(maximum) is not int or not 0 < maximum <= 160*1024**2:
        raise ValueError('Exact bounded candidate recording allowance required')
    expected_manifest = {'schema':'puck-on-policy-interval-record-v1',
        'protocol_sha256':PROTOCOL_SHA256,'completed_tick':completed_tick,
        'status':'completed','recording_format':FORMAT,'recording_max_bytes':maximum,
        'ticks':1,'recorded_ticks':1,'recorded_chunks':1,'recorded_events':2}
    if manifest_raw != (_json(expected_manifest)+'\n').encode():
        raise ValueError('Exact completed v3 candidate manifest required')
    event_raw = _read_exact_file(record,record/'events.jsonl',2*1024**2,
        'V3 recording events',directory=descriptor,root_identity=identity)
    rows = list(iter_ticks(record))
    events = [json.loads(line) for line in event_raw.splitlines()]
    if (len(rows) != 1 or type(rows[0]['episode']) is not int or rows[0]['episode'] != 0 or
            type(rows[0]['tick']) is not int or rows[0]['tick'] != completed_tick-1 or
            len(events) != 2 or any(type(event) is not dict for event in events)):
        raise ValueError('Exactly one complete candidate row and interval event required')
    arrays = {k:v for k,v in rows[0].items() if k not in ('episode','tick')}
    event = {k:v for k,v in events[1].items() if k not in ('sequence','kind')}
    expected_chunk = {'path':'chunks/000000.npz','sha256':files['recording/chunks/000000.npz']['sha256'],
        'episode':0,'start':completed_tick-1,'count':1,'sequence':0,'kind':'chunk',
        'arrays':{k:{'dtype':v.dtype.str,'shape':list(v.shape)} for k,v in arrays.items()}}
    expected_event = {**event,'sequence':1,'kind':'puck_on_policy_interval'}
    if event_raw != ((_json(expected_chunk)+'\n')+(_json(expected_event)+'\n')).encode():
        raise ValueError('Exact candidate event/chunk schema required')
    for path,(descriptor,identity) in directories.items():
        _verify_interval_directory(path,descriptor,identity)
    if _interval_file_inventory(row_root,directories) != files:
        raise ValueError('V3 candidate changed during exhaustive decoding')
    return rows[0],arrays,event,files


class PuckIntervalWriter:
    """One fresh v3 owner; every failure permanently stops further publication."""
    def __init__(self, path, *, max_bytes, storage_budget=None):
        if type(max_bytes) is not int or not 0 < max_bytes <= 160*1024**2:
            raise ValueError('V3 owner recording allowance must fit 160 MiB')
        self.path = Path(path)
        if not self.path.is_absolute() or self.path.parent.resolve() != self.path.parent:
            raise ValueError('Exact absolute v3 recording parent required')
        self.path.mkdir(exist_ok=False)
        self._root_identity = _directory_identity(os.lstat(self.path))
        self.max_bytes, self.storage_budget = max_bytes, storage_budget
        self._tick, self._bytes, self._previous, self._schema = 0, 0, None, None
        from .puck_learning import initial_cursor
        self._own = initial_cursor()
        self._broken = False

    def stop(self):
        self._broken = True

    def publish(self, staged, arrays, event, *, completed_tick):
        from .records import RunWriter
        from .snapshots import state_digest
        directories = {}
        writer = None
        committing = False
        try:
            if (self._broken or type(completed_tick) is not int or
                    completed_tick != self._tick+1 or completed_tick > 600):
                raise ValueError('V3 writer stopped or interval is noncontiguous')
            receipt = _interval_payload(staged, arrays, event, completed_tick)
            if state_digest(staged['own_pending']['before']) != state_digest(self._own):
                raise ValueError('V3 staged predecessor differs from committed cursor')
            schema = {k: (v.dtype.str, list(v.shape)) for k,v in arrays.items()}
            if self._schema is not None and schema != self._schema:
                raise ValueError('V3 interval schema changed')
            expected_arrays_digest = _interval_arrays_digest(arrays)
            expected_event_raw = _canonical_bytes(event,'Staged event')
            expected_query_digest = staged['query_before_sha256']
            next_own = {**staged['own_pending']['after'], 'tick':completed_tick}
            root, descriptor, identity = _open_publication_root(self.path)
            directories[root] = (descriptor, identity)
            if identity != self._root_identity:
                raise ValueError('V3 output root rebound')
            row_root = root/f'{completed_tick:06d}'
            os.mkdir(row_root.name, dir_fd=descriptor)
            _, row_descriptor, row_identity = _open_publication_root(row_root)
            directories[row_root] = (row_descriptor, row_identity)
            allowance = self.max_bytes-self._bytes-2*8192
            if allowance <= 0:
                raise RuntimeError('V3 owner byte allowance exhausted')
            writer = RunWriter(row_root/'recording', {
                'schema': 'puck-on-policy-interval-record-v1',
                'protocol_sha256': PROTOCOL_SHA256, 'completed_tick': completed_tick},
                max_bytes=allowance, storage_budget=self.storage_budget)
            for path in (row_root/'recording', row_root/'recording/chunks'):
                _, fd, ident = _open_publication_root(path)
                directories[path] = (fd, ident)
            writer.tick(0, completed_tick-1, **arrays)
            writer.flush()
            writer.event('puck_on_policy_interval', **event)
            writer.finish({'ticks': 1})
            for path,(fd,ident) in reversed(list(directories.items())):
                _fsync_directory(path, fd, ident)
            candidate,candidate_arrays,candidate_event,files = _decode_interval_recording(
                row_root,directories,completed_tick,maximum=allowance)
            candidate_row = {k:v for k,v in candidate.items() if k in _INTERVAL_ROW_FIELDS}
            if (state_digest(candidate_row) != receipt['row_sha256'] or
                    _interval_arrays_digest(candidate_arrays) != expected_arrays_digest or
                    _canonical_bytes(candidate_event,'Candidate event') != expected_event_raw):
                raise ValueError('Decoded v3 candidate differs from exact staged row/event')
            commitment = {'version': 1, 'kind': 'puck-on-policy-interval-commit-v1',
                'protocol_sha256': PROTOCOL_SHA256, 'completed_tick': completed_tick,
                'previous_commit_sha256': self._previous, 'row_sha256': receipt['row_sha256'],
                'staged_sha256': receipt['staged_sha256'], 'arrays_sha256': expected_arrays_digest,
                'event_sha256': _sha256(expected_event_raw), 'query_sha256': expected_query_digest,
                'files': files}
            raw = _canonical_bytes(commitment, 'v3 interval commitment')
            if len(raw) > 8192 or self._bytes+sum(f['bytes'] for f in files.values())+2*len(raw) > self.max_bytes:
                raise RuntimeError('V3 exact retained byte allowance exceeded')
            if self.storage_budget is not None:
                self.storage_budget.check(2*len(raw), path=row_root)
            anchor = row_root/'commit.anchor.json'
            _write_bytes_new(anchor, raw, 8192, directory=row_descriptor, root_identity=row_identity)
            _fsync_directory(row_root, row_descriptor, row_identity)
            for path,(fd,ident) in directories.items():
                _verify_interval_directory(path, fd, ident)
            if sorted(os.listdir(descriptor)) != [f'{n:06d}' for n in range(1,completed_tick+1)]:
                raise ValueError('V3 owner transaction namespace changed')
            if _interval_file_inventory(row_root, directories) != files:
                raise ValueError('V3 recording changed before commitment')
            if _read_exact_file(row_root, anchor, 8192, 'V3 commitment anchor',
                    directory=row_descriptor, root_identity=row_identity) != raw:
                raise ValueError('V3 commitment anchor changed')
            # The final link is the sole admission point; no fallible work follows.
            next_bytes = self._bytes+sum(f['bytes'] for f in files.values())+2*len(raw)
            next_digest = _sha256(raw)
            for path,(fd,ident) in directories.items():
                _verify_interval_directory(path, fd, ident)
            committing = True
            _exclusive_publish(anchor, row_root/'commit.json', directory=row_descriptor,
                               root_identity=row_identity, verify_after=False)
            self._tick, self._bytes, self._previous, self._schema = completed_tick, next_bytes, next_digest, schema
            self._own = next_own
            return receipt
        except BaseException:
            self.stop()
            raise
        finally:
            if writer is not None and not writer._events.closed:
                # A failed transaction's buffered row is never promoted by cleanup.
                writer._broken = True
                writer._events.close()
            for fd,_ in directories.values():
                try: os.close(fd)
                except OSError:
                    if not committing: raise


def read_committed_intervals(path):
    """Yield the strict committed v3 prefix; raw uncommitted bytes are not rows."""
    from . import puck_learning as learning
    from .snapshots import state_digest
    root, root_fd, root_identity = _open_publication_root(path)
    previous, own, schema = None, learning.initial_cursor(), None
    gap = False
    try:
        names = sorted(os.listdir(root_fd))
        if len(names) > 600 or any(n not in {f'{t:06d}' for t in range(1,601)} for n in names):
            raise ValueError('Bounded exact v3 interval namespace required')
        for number,name in enumerate(names,1):
            directories = {root: (root_fd,root_identity)}
            row_root = root/name
            try:
                _,fd,ident = _open_publication_root(row_root)
                directories[row_root] = (fd,ident)
                if not _path_present(row_root/'commit.json',fd,ident):
                    gap = True
                    continue
                if gap or int(name) != number:
                    raise ValueError('Committed v3 interval after a prefix gap')
                raw,marker_identity = _read_exact_file(row_root,row_root/'commit.json',8192,'V3 commitment',
                    directory=fd,root_identity=ident,return_identity=True,expected_links=2)
                anchor,anchor_identity = _read_exact_file(row_root,row_root/'commit.anchor.json',8192,'V3 commitment anchor',
                    directory=fd,root_identity=ident,return_identity=True,expected_links=2)
                commitment = json.loads(raw)
                if (raw != anchor or marker_identity != anchor_identity or
                        type(commitment) is not dict or set(commitment) != _INTERVAL_COMMIT_FIELDS or
                        raw != _canonical_bytes(commitment,'V3 commitment') or
                        type(commitment['version']) is not int or commitment['version'] != 1 or
                        commitment['kind'] != 'puck-on-policy-interval-commit-v1' or
                        commitment['protocol_sha256'] != PROTOCOL_SHA256 or
                        type(commitment['completed_tick']) is not int or commitment['completed_tick'] != number or
                        commitment['previous_commit_sha256'] != previous):
                    raise ValueError('V3 commitment identity or predecessor differs')
                for directory in (row_root/'recording',row_root/'recording/chunks'):
                    _,child_fd,child_identity = _open_publication_root(directory)
                    directories[directory] = (child_fd,child_identity)
                candidate,arrays,event,files = _decode_interval_recording(row_root,directories,number)
                if state_digest(files) != state_digest(commitment['files']):
                    raise ValueError('V3 recording file identity or bytes changed')
                row = {k:v for k,v in candidate.items() if k in _INTERVAL_ROW_FIELDS}
                pending = learning.prepare(row['inputs'],own)
                staged = {'version':1,'kind':'puck-on-policy-staged-interval-v1',
                    'protocol_sha256':PROTOCOL_SHA256,'row':row,'own_pending':pending,
                    'teacher_mode_before':own['mode'],'teacher_mode_after':pending['after']['mode'],
                    'query_before_sha256':commitment['query_sha256'],'query_after_sha256':commitment['query_sha256']}
                receipt = _interval_payload(staged,arrays,event,number)
                current_schema = {k:(v.dtype.str,list(v.shape)) for k,v in arrays.items()}
                if (_interval_arrays_digest(arrays) != commitment['arrays_sha256'] or
                        _sha256(_canonical_bytes(event,'V3 event')) != commitment['event_sha256'] or
                        receipt['row_sha256'] != commitment['row_sha256'] or
                        receipt['staged_sha256'] != commitment['staged_sha256'] or
                        schema is not None and schema != current_schema):
                    raise ValueError('V3 committed row/event/staged schema or digest differs')
                for directory,(child_fd,child_identity) in directories.items():
                    _verify_interval_directory(directory,child_fd,child_identity)
                if _interval_file_inventory(row_root,directories) != files:
                    raise ValueError('V3 recording changed during read')
                final_raw,final_identity = _read_exact_file(row_root,row_root/'commit.json',8192,'V3 commitment',
                    directory=fd,root_identity=ident,return_identity=True,expected_links=2)
                final_anchor,final_anchor_identity = _read_exact_file(row_root,row_root/'commit.anchor.json',8192,'V3 commitment anchor',
                    directory=fd,root_identity=ident,return_identity=True,expected_links=2)
                if final_raw != raw or final_anchor != raw or final_identity != marker_identity or final_anchor_identity != anchor_identity:
                    raise ValueError('V3 commitment changed during read')
                previous, schema = _sha256(raw), current_schema
                own = learning.commit(pending['before'],pending,number)
                yield {'completed_tick':number,'row':candidate,'event':event,'publication_receipt':receipt}
            finally:
                for directory,(child_fd,_) in directories.items():
                    if directory != root: os.close(child_fd)
    finally:
        os.close(root_fd)


def _interval_arrays_digest(arrays):
    import numpy as np
    from .snapshots import state_digest
    # NPZ decodes scalar columns as NumPy scalars; stored dtype/shape/bytes prevail.
    return state_digest({k:np.asarray(v) for k,v in arrays.items()})

# Integer eighth-metre/radian coefficients.  Fixed slots 0..7 are the complete
# parameter domain; binary-fraction conversion makes the arithmetic exact.
# Fields: puck x/y, goal dx/dy, rover dx/dy, rover yaw.
_PARAMETER_DOMAIN = (
    (-4, -4, 8, 0, -6, -2, 2),
    (-4, -2, 10, 2, -7, 2, -2),
    (-4, 2, 12, -2, -8, -2, 3),
    (-4, 4, 14, 0, -6, 2, -3),
    (-2, -4, 9, 1, -7, -2, 4),
    (-2, -2, 11, -1, -8, 2, -4),
    (-2, 2, 13, 1, -6, -2, 1),
    (-2, 4, 15, -1, -7, 2, -1),
)


def _ids(values, label, *, exact_length=None):
    if type(values) not in (list, tuple) or len(values) > MAX_ITEMS:
        raise ValueError(f'{label}: bounded list/tuple required')
    if exact_length is not None and len(values) != exact_length:
        raise ValueError(f'{label}: exactly {exact_length} IDs required')
    if any(type(value) is not int or not 0 <= value <= MAX_COUNTER for value in values):
        raise ValueError(f'{label}: bounded integer IDs required')
    if list(values) != sorted(values) or len(set(values)) != len(values):
        raise ValueError(f'{label}: unique increasing IDs required')
    return tuple(values)


def _row(seed, slot):
    px, py, gx, gy, rx, ry, yaw = _PARAMETER_DOMAIN[slot]
    puck = [px / 8, py / 8]
    return {
        'version': 1,
        'kind': SCHEMA,
        'seed': seed,
        'split': COLLECTION_SPLIT if slot < 4 else DEVELOPMENT_SPLIT,
        'slot': slot,
        'rover_pose': [(px + rx) / 8, (py + ry) / 8, yaw / 8],
        'puck_xy': puck,
        'goal_xy': [(px + gx) / 8, (py + gy) / 8],
        'initial_qvel': 'all zeros',
    }


def mint_layouts(scene_ids, *, occupied_scene_ids=()):
    """Return the eight fixed layouts for nonreserved synthetic IDs only."""
    scene_ids = _ids(scene_ids, 'scene domain', exact_length=len(_PARAMETER_DOMAIN))
    occupied = _ids(occupied_scene_ids, 'occupied scene IDs')
    if set(scene_ids) & set(RESERVED_SCENE_IDS):
        raise ValueError('Reserved puck scene IDs remain locked')
    if set(scene_ids) & set(occupied):
        raise ValueError('Puck scene ID collision')
    return [_row(seed, slot) for slot, seed in enumerate(scene_ids)]


def admit_layout(row, *, seed, split):
    """Validate one exact minter row for the explicit-layout reset seam."""
    (seed,) = _ids([seed], 'explicit layout seed', exact_length=1)
    if seed in RESERVED_SCENE_IDS:
        raise ValueError('Reserved puck scene IDs remain locked')
    if split not in (COLLECTION_SPLIT, DEVELOPMENT_SPLIT):
        raise ValueError('Explicit puck layout split differs')
    if type(row) is not dict or set(row) != _ROW_FIELDS:
        raise ValueError('Explicit puck layout requires exact fields')
    if (type(row['version']) is not int or type(row['seed']) is not int or
            type(row['slot']) is not int or type(row['kind']) is not str or
            type(row['split']) is not str or type(row['initial_qvel']) is not str or
            any(type(row[key]) is not list for key in ('rover_pose', 'puck_xy', 'goal_xy')) or
            any(type(value) is not float for key in ('rover_pose', 'puck_xy', 'goal_xy')
                for value in row[key])):
        raise ValueError('Explicit puck layout JSON types differ')
    slot = row['slot']
    expected = _row(seed, slot) if 0 <= slot < len(_PARAMETER_DOMAIN) else None
    exact_floats = expected is not None and all(
        [value.hex() for value in row[key]] == [value.hex() for value in expected[key]]
        for key in ('rover_pose', 'puck_xy', 'goal_xy'))
    if expected is None or row != expected or not exact_floats or row['split'] != split:
        raise ValueError('Explicit puck layout differs from fixed mapping')
    return expected


def _canonical_bytes(value, label):
    try:
        raw = json.dumps(value, allow_nan=False, sort_keys=True,
                         separators=(',', ':')).encode('utf-8') + b'\n'
    except (TypeError, ValueError) as error:
        raise ValueError(f'{label}: canonical JSON required') from error
    if len(raw) > _MAX_JSON_BYTES:
        raise ValueError(f'{label}: JSON exceeds bound')
    return raw


def _sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value, label):
    if (type(value) is not str or len(value) != 64 or
            any(character not in '0123456789abcdef' for character in value)):
        raise ValueError(f'{label}: lowercase SHA-256 required')
    return value


def _publication_root(value):
    if not isinstance(value, (str, os.PathLike)):
        raise ValueError('Publication root path required')
    root = Path(value)
    if (not root.is_absolute() or not root.exists() or not root.is_dir() or
            root.is_symlink() or root.resolve(strict=True) != root):
        raise ValueError('Publication root must be an exact existing directory')
    return root


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _directory_identity(value):
    return value.st_dev, value.st_ino, value.st_mode


def _object_identity(value):
    return value.st_dev, value.st_ino, value.st_mode, value.st_nlink


def _open_publication_root(value):
    root = _publication_root(value)
    before = os.lstat(root)
    flags = (os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) |
             getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0))
    directory = os.open(root, flags)
    try:
        opened = os.fstat(directory)
        rebound = os.lstat(root)
        if (not stat.S_ISDIR(opened.st_mode) or
                _directory_identity(opened) != _directory_identity(before) or
                _directory_identity(opened) != _directory_identity(rebound)):
            raise ValueError('Publication parent directory rebound')
        return root, directory, _directory_identity(opened)
    except BaseException:
        os.close(directory)
        raise


def _verify_publication_root(root, directory, root_identity, label='Publication parent'):
    opened = os.fstat(directory)
    rebound = os.lstat(root)
    if (not stat.S_ISDIR(opened.st_mode) or
            _directory_identity(opened) != root_identity or
            _directory_identity(rebound) != root_identity):
        raise ValueError(f'{label} directory changed or rebound')


def _fsync_directory(root, directory=None, root_identity=None):
    owned = directory is None
    if owned:
        root, directory, root_identity = _open_publication_root(root)
    try:
        _verify_publication_root(root, directory, root_identity)
        os.fsync(directory)
        _verify_publication_root(root, directory, root_identity)
    finally:
        if owned:
            os.close(directory)


def _path_present(path, directory=None, root_identity=None):
    path = Path(path)
    if directory is None:
        return os.path.lexists(os.fspath(path))
    root = path.parent
    _verify_publication_root(root, directory, root_identity)
    try:
        os.stat(path.name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        present = False
    else:
        present = True
    _verify_publication_root(root, directory, root_identity)
    return present


def _write_bytes_new(path, raw, maximum, *, directory=None, root_identity=None):
    if type(raw) is not bytes or len(raw) > maximum:
        raise ValueError('Bounded publication bytes required')
    path = Path(path)
    if not path.name:
        raise ValueError('Publication file parent differs')
    owned = directory is None
    if owned:
        root, directory, root_identity = _open_publication_root(path.parent)
    else:
        root = path.parent
        _verify_publication_root(root, directory, root_identity)
    if path.parent != root:
        raise ValueError('Publication file parent differs')
    descriptor = None
    try:
        _verify_publication_root(root, directory, root_identity)
        flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0))
        descriptor = os.open(path.name, flags, 0o600, dir_fd=directory)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise ValueError('New publication file is linked or nonregular')
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError('Short publication write')
            view = view[written:]
        os.fsync(descriptor)
        after = os.fstat(descriptor)
        rebound = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        if (_object_identity(after) != _object_identity(opened) or
                _identity(rebound) != _identity(after) or
                after.st_nlink != 1 or after.st_size != len(raw)):
            raise ValueError('Publication file rebound during write')
        _verify_publication_root(root, directory, root_identity,
                                 'Publication parent during write')
        return _identity(after)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if owned:
            os.close(directory)


def _read_exact_file(root, path, maximum, label, *, directory=None,
                     root_identity=None, return_identity=False, expected_links=1):
    root = Path(root)
    path = Path(path)
    if path.parent != root or not path.name:
        raise ValueError(f'{label}: exact parent required')
    owned = directory is None
    if owned:
        root, directory, root_identity = _open_publication_root(root)
    else:
        _verify_publication_root(root, directory, root_identity, f'{label}: parent')
    descriptor = None
    try:
        _verify_publication_root(root, directory, root_identity, f'{label}: parent')
        before = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        if (type(expected_links) is not int or expected_links < 1 or
                not stat.S_ISREG(before.st_mode) or
                before.st_nlink != expected_links or
                before.st_size > maximum):
            raise ValueError(f'{label}: missing, linked, or oversized file')
        flags = (os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) |
                 getattr(os, 'O_CLOEXEC', 0))
        descriptor = os.open(path.name, flags, dir_fd=directory)
        opened = os.fstat(descriptor)
        rebound = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        if (_identity(opened) != _identity(before) or
                _identity(rebound) != _identity(opened)):
            raise ValueError(f'{label}: file rebound while opening')
        chunks = []
        remaining = maximum + 1
        while remaining:
            block = os.read(descriptor, min(65536, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        raw = b''.join(chunks)
        after = os.fstat(descriptor)
        rebound = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        if (len(raw) > maximum or _identity(after) != _identity(opened) or
                _identity(rebound) != _identity(opened)):
            raise ValueError(f'{label}: file changed during read')
        _verify_publication_root(root, directory, root_identity, f'{label}: parent')
        result = (raw, _identity(opened)) if return_identity else raw
        return result
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if owned:
            os.close(directory)


def _quarantine_path(root, name):
    return root / f'.{name}.quarantine'


def _commit_path(root, name):
    return root / f'{name}.commit.json'


def _commit_pending_path(root, name):
    return root / f'.{name}.commit.pending'


def _admission_anchor_path(root, name):
    return root / f'.{name}.admission.anchor'


def _admission_path(root, name):
    return root / f'{name}.admission.json'


def _publication_paths(root, name):
    return {
        'target': root / name,
        'pending': root / f'.{name}.pending',
        'quarantine': _quarantine_path(root, name),
        'commit': _commit_path(root, name),
        'commit_pending': _commit_pending_path(root, name),
        'admission_anchor': _admission_anchor_path(root, name),
        'admission': _admission_path(root, name),
    }


def _fresh_publication_root(value, name):
    root = _publication_root(value)
    paths = _publication_paths(root, name)
    if any(_path_present(path) for path in paths.values()):
        raise ValueError(f'{name}: fresh publication paths required')
    return root


def _write_quarantine(root, name, *, directory=None, root_identity=None):
    quarantine = _quarantine_path(root, name)
    marker = _canonical_bytes({
        'version': 1, 'kind': 'puck-on-policy-publication-quarantine-v1',
        'target': name,
    }, 'publication quarantine')
    _write_bytes_new(quarantine, marker, _MAX_COMMIT_BYTES,
                     directory=directory, root_identity=root_identity)
    _fsync_directory(root, directory, root_identity)
    return quarantine


def _commit_receipt(name, manifest, raw):
    if type(manifest) is not dict:
        raise ValueError('Publication manifest must be an object')
    lineage_sha256 = _digest(manifest.get('lineage_sha256'),
                             'publication protocol')
    if lineage_sha256 != PROTOCOL_SHA256:
        raise ValueError('Publication protocol lineage differs')
    if name == 'reservation.json':
        if manifest.get('kind') != 'puck-on-policy-reservation-v1':
            raise ValueError('Reservation publication kind differs')
        reservation_sha256 = _sha256(raw)
    elif name == 'scene-manifest.json':
        if manifest.get('kind') != 'puck-on-policy-scene-manifest-v1':
            raise ValueError('Scene publication kind differs')
        reservation_sha256 = _digest(
            manifest.get('reservation_sha256'), 'publication reservation')
    elif name in ('owner-terminal.json','collection-terminal.json'):
        expected = ('puck-on-policy-owner-recording-close-v1' if name == 'owner-terminal.json'
                    else 'puck-on-policy-collection-recording-close-v1')
        if manifest.get('kind') != expected:
            raise ValueError('Recording close publication kind differs')
        reservation_sha256 = _digest(manifest.get('reservation_sha256'), 'Recording close reservation')
    else:
        raise ValueError('Unsupported publication target')
    return {
        'version': 1,
        'kind': 'puck-on-policy-publication-commit-v1',
        'target': name,
        'manifest_sha256': _sha256(raw),
        'manifest_bytes': len(raw),
        'reservation_sha256': reservation_sha256,
        'protocol_sha256': PROTOCOL_SHA256,
    }


def _write_commit_receipt(path, raw, *, directory=None, root_identity=None):
    return _write_bytes_new(path, raw, _MAX_COMMIT_BYTES,
                            directory=directory, root_identity=root_identity)


def _admission_receipt(name, raw, manifest_identity, commit_raw,
                       receipt_identity, receipt):
    identities = (manifest_identity, receipt_identity)
    if any(type(identity) not in (list, tuple) or len(identity) != 7 or
           any(type(value) is not int for value in identity) or
           not stat.S_ISREG(identity[2]) or identity[3] != 1
           for identity in identities):
        raise ValueError('Publication admission identities differ')
    if (manifest_identity[4] != len(raw) or
            receipt_identity[4] != len(commit_raw) or
            type(receipt) is not dict or set(receipt) != _COMMIT_RECEIPT_FIELDS):
        raise ValueError('Publication admission bytes differ')
    return {
        'version': 1,
        'kind': 'puck-on-policy-publication-admission-v1',
        'target': name,
        'receipt': f'{name}.commit.json',
        'manifest_sha256': _sha256(raw),
        'manifest_bytes': len(raw),
        'manifest_identity': list(manifest_identity),
        'receipt_sha256': _sha256(commit_raw),
        'receipt_bytes': len(commit_raw),
        'receipt_identity': list(receipt_identity),
        'reservation_sha256': receipt['reservation_sha256'],
        'protocol_sha256': receipt['protocol_sha256'],
    }


def _exclusive_publish(pending, final, *, directory=None, root_identity=None,
                       verify_after=True):
    pending, final = Path(pending), Path(final)
    if pending.parent != final.parent:
        raise ValueError('Publication names must share one exact parent')
    owned = directory is None
    if owned:
        root, directory, root_identity = _open_publication_root(pending.parent)
    else:
        root = pending.parent
    try:
        _verify_publication_root(root, directory, root_identity)
        if _path_present(final, directory, root_identity):
            raise FileExistsError(f'Publication destination exists: {final.name}')
        os.link(pending.name, final.name, src_dir_fd=directory,
                dst_dir_fd=directory, follow_symlinks=False)
        if not verify_after:
            return
        source = os.stat(pending.name, dir_fd=directory, follow_symlinks=False)
        destination = os.stat(final.name, dir_fd=directory, follow_symlinks=False)
        if (not stat.S_ISREG(source.st_mode) or
                (source.st_dev, source.st_ino) !=
                (destination.st_dev, destination.st_ino) or
                source.st_nlink != 2 or destination.st_nlink != 2):
            raise ValueError('Exclusive publication link identity differs')
        _verify_publication_root(root, directory, root_identity)
    finally:
        if owned:
            os.close(directory)


def _commit_admission(root, paths, raw, manifest_identity, commit_raw,
                      receipt_identity, admission_raw, *, directory,
                      root_identity, before_admission=None):
    blockers = (paths['pending'], paths['quarantine'], paths['commit_pending'])
    if any(_path_present(path, directory, root_identity) for path in blockers):
        raise ValueError('Publication remains quarantined or indeterminate')
    if _path_present(paths['admission'], directory, root_identity):
        raise FileExistsError(
            f'Publication destination exists: {paths["admission"].name}')
    final_raw, final_manifest_identity = _read_exact_file(
        root, paths['target'], _MAX_JSON_BYTES, paths['target'].name,
        directory=directory, root_identity=root_identity, return_identity=True)
    final_commit_raw, final_receipt_identity = _read_exact_file(
        root, paths['commit'], _MAX_COMMIT_BYTES, 'publication commit receipt',
        directory=directory, root_identity=root_identity, return_identity=True)
    final_admission_raw = _read_exact_file(
        root, paths['admission_anchor'], _MAX_COMMIT_BYTES,
        'publication admission anchor', directory=directory,
        root_identity=root_identity)
    if final_raw != raw or final_manifest_identity != manifest_identity:
        raise ValueError('Published manifest identity changed before commit')
    if final_commit_raw != commit_raw or final_receipt_identity != receipt_identity:
        raise ValueError('Published receipt identity changed before commit')
    if final_admission_raw != admission_raw:
        raise ValueError('Publication admission anchor changed before commit')
    _verify_publication_root(root, directory, root_identity)
    if before_admission is not None:
        before_admission()
        _verify_publication_root(root, directory, root_identity)
    # The no-replace hard link is the sole linearization point.  Its source is
    # already durable and binds both admitted file identities.  No namespace
    # mutation or fallible reread follows it.
    _exclusive_publish(
        paths['admission_anchor'], paths['admission'], directory=directory,
        root_identity=root_identity, verify_after=False)


def _atomic_manifest(root, name, manifest, *, before_admission=None):
    if before_admission is not None and not callable(before_admission):
        raise ValueError('Publication admission guard must be callable')
    raw = _canonical_bytes(manifest, name)
    receipt = _commit_receipt(name, manifest, raw)
    commit_raw = _canonical_bytes(receipt, 'publication commit receipt')
    root, directory, root_identity = _open_publication_root(root)
    committing = False
    try:
        paths = _publication_paths(root, name)
        target, pending = paths['target'], paths['pending']
        quarantine = paths['quarantine']
        commit, commit_pending = paths['commit'], paths['commit_pending']
        admission_anchor = paths['admission_anchor']
        if any(_path_present(path, directory, root_identity)
               for path in paths.values()):
            raise ValueError(f'{name}: fresh publication paths required')
        pending_identity = _write_bytes_new(
            pending, raw, _MAX_JSON_BYTES, directory=directory,
            root_identity=root_identity)
        _write_quarantine(root, name, directory=directory,
                          root_identity=root_identity)
        _exclusive_publish(pending, target, directory=directory,
                           root_identity=root_identity)
        _fsync_directory(root, directory, root_identity)
        _verify_publication_root(root, directory, root_identity)
        os.unlink(pending.name, dir_fd=directory)
        _verify_publication_root(root, directory, root_identity)
        _fsync_directory(root, directory, root_identity)
        target_raw, target_identity = _read_exact_file(
            root, target, _MAX_JSON_BYTES, name, directory=directory,
            root_identity=root_identity, return_identity=True)
        if (target_raw != raw or
                target_identity[:3] != pending_identity[:3]):
            raise ValueError('Published manifest identity changed before admission')
        commit_pending_identity = _write_commit_receipt(
            commit_pending, commit_raw, directory=directory,
            root_identity=root_identity)
        _exclusive_publish(commit_pending, commit, directory=directory,
                           root_identity=root_identity)
        _fsync_directory(root, directory, root_identity)
        _verify_publication_root(root, directory, root_identity)
        os.unlink(commit_pending.name, dir_fd=directory)
        _verify_publication_root(root, directory, root_identity)
        _fsync_directory(root, directory, root_identity)
        receipt_raw, receipt_identity = _read_exact_file(
            root, commit, _MAX_COMMIT_BYTES, 'publication commit receipt',
            directory=directory, root_identity=root_identity, return_identity=True)
        if (receipt_raw != commit_raw or
                receipt_identity[:3] != commit_pending_identity[:3]):
            raise ValueError('Published receipt identity changed before admission')
        final_target_raw, final_target_identity = _read_exact_file(
            root, target, _MAX_JSON_BYTES, name, directory=directory,
            root_identity=root_identity, return_identity=True)
        final_receipt_raw, final_receipt_identity = _read_exact_file(
            root, commit, _MAX_COMMIT_BYTES, 'publication commit receipt',
            directory=directory, root_identity=root_identity, return_identity=True)
        if (final_target_raw != target_raw or
                final_target_identity != target_identity):
            raise ValueError('Published manifest identity changed during admission')
        if (final_receipt_raw != receipt_raw or
                final_receipt_identity != receipt_identity):
            raise ValueError('Published receipt identity changed during admission')
        admission_raw = _canonical_bytes(
            _admission_receipt(name, final_target_raw, final_target_identity,
                               final_receipt_raw, final_receipt_identity, receipt),
            'publication admission receipt')
        _write_bytes_new(admission_anchor, admission_raw, _MAX_COMMIT_BYTES,
                         directory=directory, root_identity=root_identity)
        _fsync_directory(root, directory, root_identity)
        _verify_publication_root(root, directory, root_identity)
        os.unlink(quarantine.name, dir_fd=directory)
        _verify_publication_root(root, directory, root_identity)
        _fsync_directory(root, directory, root_identity)
        result = {
            'manifest_path': str(target), 'manifest_bytes': raw,
            'manifest_sha256': _sha256(raw),
            'commit_path': str(commit), 'commit_bytes': commit_raw,
            'commit_sha256': _sha256(commit_raw),
        }
        committing = True
        guard_args = {'before_admission':before_admission} if before_admission is not None else {}
        _commit_admission(
            root, paths, final_target_raw, final_target_identity,
            final_receipt_raw, final_receipt_identity, admission_raw,
            directory=directory, root_identity=root_identity, **guard_args)
        return result
    finally:
        try:
            os.close(directory)
        except OSError:
            if not committing:
                raise


def _read_publication(value, name, *, max_manifest_bytes=_MAX_JSON_BYTES):
    if type(max_manifest_bytes) is not int or not 0<max_manifest_bytes<=_MAX_JSON_BYTES:
        raise ValueError('Bounded publication manifest cap required')
    if not isinstance(value, (str, os.PathLike)):
        raise ValueError(f'{name}: publication path required')
    target = Path(value)
    if not target.is_absolute() or target.name != name:
        raise ValueError(f'{name}: exact publication path required')
    root, directory, root_identity = _open_publication_root(target.parent)
    try:
        paths = _publication_paths(root, name)
        pending, quarantine = paths['pending'], paths['quarantine']
        commit, commit_pending = paths['commit'], paths['commit_pending']
        blockers = (quarantine, pending, commit_pending)
        if any(_path_present(path, directory, root_identity) for path in blockers):
            raise ValueError(f'{name}: publication is quarantined or indeterminate')
        try:
            raw, target_identity = _read_exact_file(
                root, target, max_manifest_bytes, name, directory=directory,
                root_identity=root_identity, return_identity=True)
            commit_raw, commit_identity = _read_exact_file(
                root, commit, _MAX_COMMIT_BYTES, 'publication commit receipt',
                directory=directory, root_identity=root_identity, return_identity=True)
            admission_anchor_raw, admission_anchor_identity = _read_exact_file(
                root, paths['admission_anchor'], _MAX_COMMIT_BYTES,
                'publication admission anchor', directory=directory,
                root_identity=root_identity, return_identity=True, expected_links=2)
            admission_raw, admission_identity = _read_exact_file(
                root, paths['admission'], _MAX_COMMIT_BYTES,
                'publication admission receipt', directory=directory,
                root_identity=root_identity, return_identity=True, expected_links=2)
        except OSError as error:
            raise ValueError(
                f'{name}: exact target, receipt, and admission required') from error
        if (admission_anchor_raw != admission_raw or
                admission_anchor_identity != admission_identity):
            raise ValueError(f'{name}: admission link identity differs')
        if any(_path_present(path, directory, root_identity) for path in blockers):
            raise ValueError(f'{name}: publication changed while read')
        try:
            manifest = json.loads(raw)
            receipt = json.loads(commit_raw)
            admission = json.loads(admission_raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                f'{name}: publication, commit, or admission JSON differs') from error
        expected = _commit_receipt(name, manifest, raw)
        if (type(receipt) is not dict or set(receipt) != _COMMIT_RECEIPT_FIELDS or
                _canonical_bytes(receipt, 'publication commit receipt') != commit_raw or
                type(receipt['version']) is not int or
                type(receipt['manifest_bytes']) is not int or
                receipt != expected):
            raise ValueError(f'{name}: positive commit receipt differs')
        expected_admission = _admission_receipt(
            name, raw, target_identity, commit_raw, commit_identity, receipt)
        if (type(admission) is not dict or
                set(admission) != _ADMISSION_RECEIPT_FIELDS or
                _canonical_bytes(admission, 'publication admission receipt') !=
                admission_raw or type(admission['version']) is not int or
                type(admission['manifest_bytes']) is not int or
                type(admission['receipt_bytes']) is not int or
                admission_raw != _canonical_bytes(
                    expected_admission, 'expected publication admission receipt')):
            raise ValueError(f'{name}: identity-bound admission receipt differs')
        try:
            final_raw, final_target_identity = _read_exact_file(
                root, target, max_manifest_bytes, name, directory=directory,
                root_identity=root_identity, return_identity=True)
            final_commit_raw, final_commit_identity = _read_exact_file(
                root, commit, _MAX_COMMIT_BYTES, 'publication commit receipt',
                directory=directory, root_identity=root_identity, return_identity=True)
            final_admission_anchor_raw, final_admission_anchor_identity = \
                _read_exact_file(
                    root, paths['admission_anchor'], _MAX_COMMIT_BYTES,
                    'publication admission anchor', directory=directory,
                    root_identity=root_identity, return_identity=True,
                    expected_links=2)
            final_admission_raw, final_admission_identity = _read_exact_file(
                root, paths['admission'], _MAX_COMMIT_BYTES,
                'publication admission receipt', directory=directory,
                root_identity=root_identity, return_identity=True,
                expected_links=2)
        except OSError as error:
            raise ValueError(f'{name}: publication disappeared during admission') from error
        if final_raw != raw or final_target_identity != target_identity:
            raise ValueError(f'{name}: publication identity changed after admission')
        if final_commit_raw != commit_raw or final_commit_identity != commit_identity:
            raise ValueError(f'{name}: commit receipt identity changed during admission')
        if (final_admission_anchor_raw != admission_anchor_raw or
                final_admission_anchor_identity != admission_anchor_identity or
                final_admission_raw != admission_raw or
                final_admission_identity != admission_identity or
                final_admission_anchor_identity != final_admission_identity):
            raise ValueError(f'{name}: admission identity changed during admission')
        if any(_path_present(path, directory, root_identity) for path in blockers):
            raise ValueError(f'{name}: publication changed during final admission')
        return raw
    finally:
        os.close(directory)


def _inventory_roster():
    roster = _ids(RESERVED_SCENE_IDS, 'reserved scene roster', exact_length=8)
    if set(roster) & set(HELD_OUT_SCENE_IDS):
        raise ValueError('Held-out scene IDs remain locked')
    return roster


def _validate_inventory(snapshot, lineage_sha256):
    lineage_sha256 = _digest(lineage_sha256, 'reservation lineage')
    if lineage_sha256 != PROTOCOL_SHA256:
        raise ValueError('Reservation lineage differs from frozen protocol')
    if type(snapshot) is not dict or set(snapshot) != _INVENTORY_FIELDS:
        raise ValueError('Inventory snapshot requires exact fields')
    if (type(snapshot['version']) is not int or snapshot['version'] != 1 or
            type(snapshot['complete']) is not bool or not snapshot['complete'] or
            type(snapshot['remote_refs_fresh']) is not bool or
            not snapshot['remote_refs_fresh'] or
            type(snapshot['held_out_accessed']) is not bool or
            snapshot['held_out_accessed']):
        raise ValueError('Inventory snapshot is incomplete, stale, or accessed held-out')
    roots, records = snapshot['roots'], snapshot['records']
    if (type(roots) is not list or not roots or len(roots) > MAX_ITEMS or
            type(records) is not list or not records or len(records) > MAX_ITEMS):
        raise ValueError('Inventory roots and records must be bounded lists')

    root_kinds = set()
    root_paths = {}
    resolved_paths = set()
    for root in roots:
        if type(root) is not dict or set(root) != _ROOT_FIELDS:
            raise ValueError('Inventory root requires exact fields')
        kind, path, resolved = root['kind'], root['path'], root['resolved_path']
        if kind not in _INVENTORY_KINDS:
            raise ValueError('Inventory root kind differs')
        if (type(path) is not str or type(resolved) is not str or
                not Path(path).is_absolute() or path != os.path.normpath(path) or
                path != resolved or resolved in resolved_paths):
            raise ValueError('Inventory root path is aliased')
        for field in ('exists', 'readable', 'is_directory', 'is_symlink'):
            if type(root[field]) is not bool:
                raise ValueError('Inventory root flags must be booleans')
        if (not root['exists'] or not root['readable'] or not root['is_directory'] or
                root['is_symlink']):
            raise ValueError('Inventory root is missing, unreadable, or symlinked')
        _digest(root['identity_sha256'], 'inventory root identity')
        root_kinds.add(kind)
        root_paths[path] = kind
        resolved_paths.add(resolved)
    if root_kinds != _INVENTORY_KINDS:
        raise ValueError('Inventory root roster is incomplete')

    roster = _inventory_roster()
    self_reservations = []
    occupied_ids = set()
    occupied = {field: set() for field in (
        'canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')}
    record_names = set()
    record_kinds = set()
    for record in records:
        if type(record) is not dict or set(record) != _RECORD_FIELDS:
            raise ValueError('Inventory record requires exact fields')
        kind, name, root = record['kind'], record['name'], record['root']
        if (kind not in _INVENTORY_KINDS or type(name) is not str or not name or
                len(name) > 256 or (kind, name) in record_names or
                root_paths.get(root) != kind):
            raise ValueError('Inventory record identity or root differs')
        _digest(record['identity_sha256'], 'inventory record identity')
        if len(_canonical_bytes(record['metadata'], 'inventory metadata')) > 65536:
            raise ValueError('Inventory metadata exceeds bound')
        scenes = record['scenes']
        if type(scenes) is not list or len(scenes) > MAX_ITEMS:
            raise ValueError('Inventory record scenes must be a bounded list')
        role = record['role']
        if role == 'prior':
            if record['lineage_sha256'] is not None:
                raise ValueError('Prior record cannot share reservation lineage')
        elif role == 'self_reservation':
            if record['lineage_sha256'] != lineage_sha256:
                raise ValueError('Self reservation lineage differs')
            self_reservations.append(record)
        else:
            raise ValueError('Inventory record role differs')
        scene_ids = []
        for scene in scenes:
            if type(scene) is not dict or set(scene) != _SCENE_FIELDS:
                raise ValueError('Inventory scene requires exact typed fields')
            (scene_id,) = _ids([scene['scene_id']], 'inventory scene ID', exact_length=1)
            scene_ids.append(scene_id)
            if role == 'self_reservation':
                if any(scene[field] is not None for field in occupied):
                    raise ValueError('Unminted self reservation carries identities')
            else:
                if scene_id in roster:
                    raise ValueError('Reserved puck scene ID collision')
                identities = {
                    field: _digest(scene[field], f'inventory {field}')
                    for field in occupied}
                if (scene_id in occupied_ids or
                        any(value in occupied[field]
                            for field, value in identities.items())):
                    raise ValueError('Prior puck scene or identity collision')
                occupied_ids.add(scene_id)
                for field in occupied:
                    occupied[field].add(identities[field])
        if role == 'self_reservation' and tuple(scene_ids) != roster:
            raise ValueError('Self reservation roster is partial or reordered')
        record_names.add((kind, name))
        record_kinds.add(kind)
    if record_kinds != _INVENTORY_KINDS or len(self_reservations) != 1:
        raise ValueError('Inventory records or self reservation lineage are incomplete')
    return {
        'occupied_scene_ids': sorted(occupied_ids),
        'occupied_canonical_scene_sha256': sorted(occupied['canonical_scene_sha256']),
        'occupied_scientific_initial_sha256': sorted(occupied['scientific_initial_sha256']),
        'occupied_payload_sha256': sorted(occupied['payload_sha256']),
    }


def reserve_scene_roster(output_root, inventory_before, inventory_after, *, lineage_sha256):
    """Admit supplied inventory snapshots and atomically reserve all eight IDs."""
    output_root = _fresh_publication_root(output_root, 'reservation.json')
    before = _validate_inventory(inventory_before, lineage_sha256)
    after = _validate_inventory(inventory_after, lineage_sha256)
    before_bytes = _canonical_bytes(inventory_before, 'inventory before')
    after_bytes = _canonical_bytes(inventory_after, 'inventory after')
    if before_bytes != after_bytes or before != after:
        raise ValueError('Inventory changed during reservation')
    roster = _inventory_roster()
    manifest = {
        'version': 1, 'kind': 'puck-on-policy-reservation-v1',
        'lineage_sha256': PROTOCOL_SHA256, 'scene_ids': list(roster),
        'inventory_before_sha256': _sha256(before_bytes),
        'inventory_after_sha256': _sha256(after_bytes),
        'inventory': json.loads(before_bytes),
        **before,
    }
    return _atomic_manifest(output_root, 'reservation.json', manifest)


def _read_reservation(raw):
    if type(raw) is not bytes or len(raw) > _MAX_JSON_BYTES:
        raise ValueError('Canonical reservation bytes required')
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Canonical reservation JSON required') from error
    if _canonical_bytes(manifest, 'reservation') != raw:
        raise ValueError('Reservation bytes are not canonical')
    if type(manifest) is not dict or set(manifest) != _RESERVATION_FIELDS:
        raise ValueError('Reservation manifest requires exact fields')
    if (type(manifest['version']) is not int or manifest['version'] != 1 or
            manifest['kind'] != 'puck-on-policy-reservation-v1'):
        raise ValueError('Reservation schema differs')
    lineage = _digest(manifest['lineage_sha256'], 'reservation lineage')
    if lineage != PROTOCOL_SHA256:
        raise ValueError('Reservation lineage differs from frozen protocol')
    if tuple(manifest['scene_ids']) != _inventory_roster():
        raise ValueError('Reservation scene roster differs')
    admitted = _validate_inventory(manifest['inventory'], lineage)
    inventory_bytes = _canonical_bytes(manifest['inventory'], 'reserved inventory')
    if (manifest['inventory_before_sha256'] != _sha256(inventory_bytes) or
            manifest['inventory_after_sha256'] != _sha256(inventory_bytes) or
            any(manifest[field] != admitted[field] for field in admitted)):
        raise ValueError('Reservation inventory binding differs')
    return manifest


def _read_published_reservation(path):
    raw = _read_publication(path, 'reservation.json')
    return raw, _read_reservation(raw)


def _admit_staged_layout(row, scene_id, slot, split):
    if type(row) is not dict or set(row) != _ROW_FIELDS:
        raise ValueError('Staged puck layout requires exact fields')
    if (type(scene_id) is not int or type(slot) is not int or
            not 0 <= slot < 8 or
            split != (COLLECTION_SPLIT if slot < 4 else DEVELOPMENT_SPLIT) or
            type(row['version']) is not int or row['version'] != 1 or row['kind'] != SCHEMA or
            type(row['seed']) is not int or row['seed'] != scene_id or
            type(row['slot']) is not int or row['slot'] != slot or row['split'] != split or
            row['initial_qvel'] != 'all zeros'):
        raise ValueError('Staged puck layout identity differs')
    sizes = {'rover_pose': 3, 'puck_xy': 2, 'goal_xy': 2}
    for field, size in sizes.items():
        values = row[field]
        if (type(values) is not list or len(values) != size or
                any(type(value) is not float or not math.isfinite(value) or
                    (value == 0 and math.copysign(1, value) < 0) for value in values)):
            raise ValueError('Staged puck layout JSON numbers differ')
    coordinates = row['rover_pose'][:2] + row['puck_xy'] + row['goal_xy']
    if (max(map(abs, coordinates)) > 5 or abs(row['rover_pose'][2]) > math.pi or
            math.dist(row['rover_pose'][:2], row['puck_xy']) <= .55 or
            math.dist(row['puck_xy'], row['goal_xy']) <= .99):
        raise ValueError('Staged puck layout violates task-v5 bounds or clearance')


def scene_candidate_identities(layout):
    """Derive all collision identities from one admitted exact layout."""
    if type(layout) is not dict or set(layout) != _ROW_FIELDS:
        raise ValueError('Scene layout requires exact fields')
    scene_id, slot, split = layout['seed'], layout['slot'], layout['split']
    _admit_staged_layout(layout, scene_id, slot, split)
    canonical_scene = {
        'version': 1, 'kind': 'puck-on-policy-canonical-scene-v1',
        'rover_pose': layout['rover_pose'], 'puck_xy': layout['puck_xy'],
        'goal_xy': layout['goal_xy'],
    }
    scientific_initial = canonical_scene | {
        'kind': 'puck-on-policy-scientific-initial-v1',
        'initial_qvel': layout['initial_qvel'],
    }
    return {
        'canonical_scene_sha256': _sha256(
            _canonical_bytes(canonical_scene, 'canonical scene')),
        'scientific_initial_sha256': _sha256(
            _canonical_bytes(scientific_initial, 'scientific initial')),
        'payload_sha256': _sha256(_canonical_bytes(layout, 'complete scene payload')),
    }


def _validate_scene_entry(entry, scene_id, slot, split):
    if type(entry) is not dict or set(entry) != _SCENE_ENTRY_FIELDS:
        raise ValueError('Scene-manifest entry requires exact fields')
    if (type(entry['scene_id']) is not int or entry['scene_id'] != scene_id or
            type(entry['slot']) is not int or entry['slot'] != slot or
            entry['split'] != split):
        raise ValueError('Scene-manifest entry order or identity differs')
    _admit_staged_layout(entry['layout'], scene_id, slot, split)
    identities = scene_candidate_identities(entry['layout'])
    for field, expected in identities.items():
        if _digest(entry[field], f'scene manifest {field}') != expected:
            raise ValueError(f'Scene-manifest {field} is unbound')
    return identities


def _read_scene_manifest(raw, reservation_raw):
    if type(raw) is not bytes or len(raw) > _MAX_JSON_BYTES:
        raise ValueError('Canonical scene-manifest bytes required')
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('Canonical scene-manifest JSON required') from error
    if (type(manifest) is not dict or
            _canonical_bytes(manifest, 'scene manifest') != raw or
            set(manifest) != _SCENE_MANIFEST_FIELDS or
            type(manifest['version']) is not int or manifest['version'] != 1 or
            manifest['kind'] != 'puck-on-policy-scene-manifest-v1'):
        raise ValueError('Scene manifest schema or canonical bytes differ')
    reservation = _read_reservation(reservation_raw)
    if (_digest(manifest['lineage_sha256'], 'scene-manifest lineage') !=
            reservation['lineage_sha256'] or
            _digest(manifest['reservation_sha256'], 'scene-manifest reservation') !=
            _sha256(reservation_raw)):
        raise ValueError('Scene manifest reservation lineage is unbound')
    roster = _inventory_roster()
    if tuple(manifest['scene_ids']) != roster:
        raise ValueError('Scene manifest roster differs')
    scenes = manifest['scenes']
    if type(scenes) is not list or len(scenes) != len(roster):
        raise ValueError('Scene manifest requires exactly eight entries')
    occupied_ids = set(reservation['occupied_scene_ids'])
    seen_ids = set()
    seen = {
        field: set(reservation[f'occupied_{field}']) for field in (
            'canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')
    }
    for slot, (scene_id, entry) in enumerate(zip(roster, scenes)):
        split = COLLECTION_SPLIT if slot < 4 else DEVELOPMENT_SPLIT
        if scene_id in occupied_ids or scene_id in seen_ids:
            raise ValueError('Scene-manifest scene ID collision')
        identities = _validate_scene_entry(entry, scene_id, slot, split)
        if any(value in seen[field] for field, value in identities.items()):
            raise ValueError('Scene-manifest identity collision')
        seen_ids.add(scene_id)
        for field, value in identities.items():
            seen[field].add(value)
    return manifest


def _collection_projection_bytes(manifest):
    collection_ids = _inventory_roster()[:4]
    scenes = [{field: entry[field] for field in _SCENE_ENTRY_FIELDS}
              for entry in manifest['scenes'][:4]]
    return _canonical_bytes({
        'version': 1, 'kind': 'puck-on-policy-collection-projection-v1',
        'scene_ids': list(collection_ids), 'scenes': scenes,
    }, 'collection projection')


def collection_scene_projection(scene_manifest_path, *, reservation_path, audience):
    """Read durable publications and derive the only collection-visible view."""
    if audience != 'collection':
        raise ValueError('Only the collection scene projection is available')
    reservation_raw, _ = _read_published_reservation(reservation_path)
    scene_raw = _read_publication(scene_manifest_path, 'scene-manifest.json')
    manifest = _read_scene_manifest(scene_raw, reservation_raw)
    if _read_publication(reservation_path, 'reservation.json') != reservation_raw:
        raise ValueError('Reservation changed while deriving collection projection')
    return _collection_projection_bytes(manifest)


def stage_scene_manifest(output_root, reservation_path, minter, *, inventory_after):
    """Stage all eight candidates through a caller-supplied minter and publish once."""
    output_root = _fresh_publication_root(output_root, 'scene-manifest.json')
    if not callable(minter):
        raise ValueError('Scene minter must be callable')
    reservation_raw, reservation = _read_published_reservation(reservation_path)
    roster = _inventory_roster()
    occupied_ids = set(reservation['occupied_scene_ids'])
    seen_ids = set()
    occupied = {
        field: set(reservation[f'occupied_{field}']) for field in (
            'canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')
    }
    scenes = []
    for slot, scene_id in enumerate(roster):
        split = COLLECTION_SPLIT if slot < 4 else DEVELOPMENT_SPLIT
        if scene_id in occupied_ids or scene_id in seen_ids:
            raise ValueError('Puck scene ID collision')
        layout = minter(scene_id, slot, split)
        _admit_staged_layout(layout, scene_id, slot, split)
        identities = scene_candidate_identities(layout)
        for field, value in identities.items():
            if value in occupied[field]:
                raise ValueError(f'{field} collision')
        normalized = json.loads(_canonical_bytes(layout, 'scene layout'))
        scenes.append({
            'scene_id': scene_id, 'slot': slot, 'split': split,
            **identities, 'layout': normalized,
        })
        seen_ids.add(scene_id)
        for field, value in identities.items():
            occupied[field].add(value)

    final = _validate_inventory(inventory_after, reservation['lineage_sha256'])
    final_bytes = _canonical_bytes(inventory_after, 'final inventory')
    if (final_bytes != _canonical_bytes(reservation['inventory'], 'reserved inventory') or
            _sha256(final_bytes) != reservation['inventory_after_sha256'] or
            any(final[field] != reservation[field] for field in final)):
        raise ValueError('Inventory changed before scene publication')
    if _read_publication(reservation_path, 'reservation.json') != reservation_raw:
        raise ValueError('Reservation changed before scene publication')
    manifest = {
        'version': 1, 'kind': 'puck-on-policy-scene-manifest-v1',
        'lineage_sha256': reservation['lineage_sha256'],
        'reservation_sha256': _sha256(reservation_raw),
        'scene_ids': list(roster), 'scenes': scenes,
    }
    manifest_bytes = _canonical_bytes(manifest, 'scene manifest')
    _read_scene_manifest(manifest_bytes, reservation_raw)
    projection = _collection_projection_bytes(manifest)
    result = _atomic_manifest(output_root, 'scene-manifest.json', manifest)
    result['collection_projection_bytes'] = projection
    return result
