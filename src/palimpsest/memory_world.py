"""Two-passage DEVELOPMENT geometry for the pinned cylinder navigation body.

Passability means an unobstructed straight horizontal body-center crossing of
x=[-1,1] in the specified aperture, not global reachability. Cue and inspection
markers are declared virtual symbolic sensors, not added camera-visible geoms.
No authored known beliefs/history are supplied; M starts unknown. Actual
MuJoCo acquisition and embodied outcomes require the separate runtime gate.
"""

import copy
import hashlib
import importlib
import math
from numbers import Real
from pathlib import Path

from .interventions import ROVER_RADIUS, WALL_INSET, apply_intervention
from .memory import canonical_bytes, sha256, validate_m, PRODUCER_SHA256


SUBJECTS = ('passage-a', 'passage-b')
OBSTACLE_RADIUS = .4
START_POSE = [-2.5, 0., 0.]
GOAL_XY = [-1., 0.]
POSTS = [[0., -2.], [0., 0.], [0., 2.]]
PARKED_GATES = [[2.5, -1.], [2.5, 1.]]
CLOSED_GATES = [[0., -1.], [0., 1.]]
PARKED_OTHERS = [[x, y] for x in (3.7, 4.9, 6.1) for y in (-5.6, -4.4, -3.2, 3.2, 4.4)]
APERTURES = [[-2., 0.], [0., 2.]]
PROFILE = {'version': 1, 'id': 'memory-passages-development-v1',
    'memory_source_sha256': PRODUCER_SHA256,
    'sensor_bridge_source_sha256': hashlib.sha256(Path(__file__).with_name('memory_task.py').read_bytes()).hexdigest(),
    'world_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'claim': 'development-fixture', 'arena': 7., 'obstacle_radius': OBSTACLE_RADIUS,
    'rover_radius': ROVER_RADIUS, 'start_pose': START_POSE, 'goal_xy': GOAL_XY,
    'posts': POSTS, 'parked_gates': PARKED_GATES, 'closed_gates': CLOSED_GATES,
    'parked_others': PARKED_OTHERS, 'crossing_x': [-1., 1.], 'apertures': APERTURES,
    'cue_xy': [-1.2, 0.], 'inspection_xy': [[-.8, -1.], [-.8, 1.]],
    'default_change_tick': 10}
PROFILE_SHA256 = sha256(PROFILE)


def _tick(value):
    if type(value) is not int or value < 0:
        raise ValueError('World tick must be a nonnegative integer')


def _numbers(value, width):
    if type(value) not in (list, tuple) or len(value) != width or any(
            isinstance(v, bool) or not isinstance(v, Real) for v in value):
        raise ValueError('Invalid finite world coordinates')
    try:
        result = list(map(float, value))
    except OverflowError as error:
        raise ValueError('Invalid finite world coordinates') from error
    if not all(math.isfinite(v) for v in result):
        raise ValueError('Invalid finite world coordinates')
    return result


def initial_state(*, close_subject_id='passage-a', change_tick=10):
    return validate_state({'version': 1, 'profile_sha256': PROFILE_SHA256,
        'cue_state': 0, 'change_tick': change_tick, 'close_subject_id': close_subject_id,
        'applied': False, 'gate_result': 'pending', 'last_tick': None})


def validate_state(state):
    if type(state) is not dict or set(state) != {'version', 'profile_sha256', 'cue_state',
            'change_tick', 'close_subject_id', 'applied', 'gate_result', 'last_tick'}:
        raise ValueError('Missing or unknown memory world state fields')
    if len(canonical_bytes(state)) > 8192:
        raise ValueError('Memory world state exceeds byte limit')
    if type(state['version']) is not int or state['version'] != 1 or state['profile_sha256'] != PROFILE_SHA256:
        raise ValueError('Incompatible development world profile')
    _tick(state['change_tick'])
    if state['last_tick'] is not None:
        _tick(state['last_tick'])
    if state['close_subject_id'] is not None and state['close_subject_id'] not in SUBJECTS:
        raise ValueError('Unknown gate subject')
    if type(state['applied']) is not bool or type(state['cue_state']) is not int or state['cue_state'] != int(state['applied']):
        raise ValueError('Inconsistent cue schedule state')
    if state['gate_result'] not in ('pending', 'closed', 'not_requested', 'rejected'):
        raise ValueError('Unknown gate result')
    if state['applied']:
        if state['last_tick'] is None or state['last_tick'] < state['change_tick'] or state['gate_result'] == 'pending':
            raise ValueError('Applied schedule needs its recorded boundary/result')
        if (state['close_subject_id'] is None) != (state['gate_result'] == 'not_requested'):
            raise ValueError('Gate result disagrees with scheduled mechanism')
    elif state['gate_result'] != 'pending' or state['last_tick'] is not None and state['last_tick'] >= state['change_tick']:
        raise ValueError('Unapplied schedule is past its boundary')
    return copy.deepcopy(state)


def initial_facts():
    facts = []
    for subject, relation in zip(SUBJECTS, ('local_cue', 'paired_cue')):
        facts.append({'id': f'fact-{subject}', 'subject_id': subject, 'kind': 'passability',
            'estimate': None, 'status': 'unknown', 'associations': [{'cue_id': 'warning-cue', 'relation': relation}],
            'inspection_landmark_id': f'inspect-{subject}', 'evidence': None,
            'revision': 0, 'origin': 'initial_unknown'})
    return validate_m({'version': 1, 'facts': facts})['facts']


def validate_layout(positions=None):
    """Pure clearance check for authored initialization (not a runtime claim)."""
    positions = copy.deepcopy(POSTS + PARKED_GATES + PARKED_OTHERS) if positions is None else positions
    if type(positions) is not list or len(positions) != 20:
        raise ValueError('Development world requires exactly twenty cylinders')
    positions = [_numbers(point, 2) for point in positions]
    centers, radii = positions + [START_POSE[:2], GOAL_XY], [OBSTACLE_RADIUS] * 20 + [ROVER_RADIUS, .25]
    for index, (center, radius) in enumerate(zip(centers, radii)):
        if max(map(abs, center)) + radius >= 7. - WALL_INSET:
            raise ValueError('Development placement crosses arena clearance')
        if any(math.dist(center, previous) <= radius + radii[j] for j, previous in enumerate(centers[:index])):
            raise ValueError('Development placements overlap')
    return positions


def passage_status(occluders):
    """Independent geometry labels: existence of a clear horizontal crossing."""
    if type(occluders) not in (list, tuple) or len(occluders) > 20:
        raise ValueError('Expected at most twenty cylinder occluders')
    forbidden = []
    for circle in occluders:
        x, y, radius = _numbers(circle, 3)
        if radius <= 0:
            raise ValueError('Cylinder radius must be positive')
        inflated = radius + ROVER_RADIUS
        dx = max(-1. - x, x - 1., 0.)
        if dx < inflated:
            half = math.sqrt(inflated * inflated - dx * dx)
            forbidden.append((y - half, y + half))
    labels = {}
    for subject, (low, high) in zip(SUBJECTS, APERTURES):
        cursor = low
        for start, end in sorted(forbidden):
            if end <= cursor:
                continue
            if start > cursor:
                break
            cursor = max(cursor, end)
            if cursor >= high:
                break
        labels[subject] = 'blocked' if cursor >= high else 'open'
    return labels


def _validate_env(env):
    if env.n_obstacles != 20 or len(env.obstacle_ids) != 20 or not math.isclose(float(env.arena), 7., abs_tol=1e-9, rel_tol=0.):
        raise ValueError('Memory world requires the pinned twenty-cylinder arena')
    if not math.isclose(float(env.model.site_size[env.goal_site_id][0]), .25, abs_tol=1e-9, rel_tol=0.):
        raise ValueError('Unexpected pinned goal site radius')
    for gid in env.obstacle_ids:
        if int(env.model.geom_type[gid]) != 5 or not math.isclose(float(env.model.geom_size[gid][0]), OBSTACLE_RADIUS, abs_tol=1e-9, rel_tol=0.):
            raise ValueError('Unexpected pinned cylinder type/radius')


def _occluders(env):
    _validate_env(env)
    return [[float(env.data.geom_xpos[gid][0]), float(env.data.geom_xpos[gid][1]),
             float(env.model.geom_size[gid][0])] for gid in env.obstacle_ids]


def configure(env, state):
    """Author the initial development scene after env.reset, without stepping."""
    state = validate_state(state)
    if state['applied'] or state['last_tick'] is not None:
        raise ValueError('configure requires initial schedule state; restore uses snapshots')
    _validate_env(env)
    positions = validate_layout()
    joints = []
    for index, xy in enumerate(positions):
        for joint, coordinate in zip((env.obstacle_x_joint_ids[index], env.obstacle_y_joint_ids[index]), xy):
            width = (float(env.model.jnt_range[joint][1]) - float(env.model.jnt_range[joint][0])) / 2
            if not math.isfinite(width) or not 0 < width <= .001:
                raise ValueError('Obstacle joints are not tightly locked')
            joints.append((joint, coordinate, width))
    # Resolve the dependency before mutation; this function is not a pure fixture.
    forward = importlib.import_module('mujoco').mj_forward
    env.place_robot(*START_POSE, env.data.qpos.copy(), env.data.qvel.copy())
    for joint, coordinate, width in joints:
        env.data.qpos[env.model.jnt_qposadr[joint]] = coordinate
        env.data.qvel[env.model.jnt_dofadr[joint]] = 0.
        env.model.jnt_range[joint, :] = [coordinate - width, coordinate + width]
    env._obstacle_xy[:, :] = positions
    env._goal_xy[:] = GOAL_XY
    env.model.site_pos[env.goal_site_id, :2] = GOAL_XY
    forward(env.model, env.data)
    env._prev_xy = env._base_xy().copy()
    env._speed, env._stall_steps = 0., 0
    env._last_action[:] = 0.
    env.path_to_draw = env.target_to_draw = None
    for name in ('_cached_occ', '_cached_obstacles_hash', '_cached_clearance'):
        setattr(env.planner, name, None)
    env._reset_exploration()
    return state


def advance_world(env, state, tick):
    """Apply the hidden schedule once; log failed gate edits without inventing truth."""
    state = validate_state(state)
    _tick(tick)
    if state['last_tick'] is not None and tick < state['last_tick']:
        raise ValueError('Stale memory world tick')
    if tick == state['last_tick']:
        return state, []
    if state['last_tick'] is None and tick != 0 or state['last_tick'] is not None and tick != state['last_tick'] + 1:
        raise ValueError('Memory world requires consecutive control ticks')
    state['last_tick'] = tick
    events = []
    if not state['applied'] and tick == state['change_tick']:
        before = passage_status(_occluders(env))
        state['applied'], state['cue_state'] = True, 1
        events.append({'kind': 'memory_cue_changed', 'tick': tick, 'cue_id': 'warning-cue', 'before': 0, 'after': 1})
        subject = state['close_subject_id']
        if subject is None:
            state['gate_result'] = 'not_requested'
        else:
            index = SUBJECTS.index(subject)
            try:
                edit = apply_intervention(env, {'kind': 'move_obstacle', 'index': index + 3, 'xy': CLOSED_GATES[index]})
            except ValueError as error:
                state['gate_result'] = 'rejected'
                events.append({'kind': 'memory_gate_rejected', 'tick': tick, 'subject_id': subject, 'reason': str(error)})
            else:
                state['gate_result'] = 'closed'
                events.append({'kind': 'memory_gate_applied', 'tick': tick, 'subject_id': subject, 'intervention': edit})
        after = passage_status(_occluders(env))
        events.append({'kind': 'memory_passage_geometry', 'tick': tick, 'before': before, 'after': after})
    return validate_state(state), events


def sensing_inputs(env, state):
    """Return geometry only to capture_symbolic, never to selectors/the bridge."""
    state = validate_state(state)
    circles = _occluders(env)
    labels = passage_status(circles)
    world = {'cues': [{'id': 'warning-cue', 'xy': [-1.2, 0.], 'state': state['cue_state']}],
        'landmarks': [{'id': 'common-goal', 'xy': list(map(float, env._goal_xy))},
                      *[{'id': f'inspect-{subject}', 'xy': copy.deepcopy(xy)} for subject, xy in zip(SUBJECTS, PROFILE['inspection_xy'])]],
        'passages': [{'subject_id': subject, 'inspection_landmark_id': f'inspect-{subject}', 'passability': labels[subject]} for subject in SUBJECTS],
        'common_goal_id': 'common-goal'}
    pose = [*map(float, env._base_xy()), float(env._base_yaw())]
    _numbers(pose, 3)
    return world, pose, circles
