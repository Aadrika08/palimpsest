"""Declared development exploration/homing supervisors; no trained-policy claims.

Geometry is confined to capture/configure. advance sees only the exact declared
packet. Encoder state, stopped dwell and all supervisor decisions are JSON.
"""

import copy
import hashlib
import math
from pathlib import Path

from . import memory_task, memory_world, task_mechanics as mechanisms
from .memory import canonical_bytes, sha256


SCENARIOS = ('exploration-landmarks', 'encoder-homing')
LANDMARKS = [{'id': 'inspect-a', 'xy': [-1.75, 0.]}, {'id': 'inspect-b', 'xy': [-1., 0.]}]
PROTOCOL = {'version': 1, 'claim': 'development-unqualified',
    'control_interval_s': .02, 'max_ticks': 600, 'max_travel_m': 20.,
    'encoder_quantum_rad': .001, 'max_increment_rad': math.tau,
    'encoder_signs': [1, 1], 'encoder_joints': ['left_hinge', 'right_hinge'],
    'stopped_rule': 'both quantized encoder increments exactly zero', 'dwell_ticks': 5,
    'visible_range_m': 4., 'visible_half_fov_rad': math.pi / 2,
    'occlusion': 'circular-cylinder line-of-sight including tangency',
    'inspection_radius_m': .25, 'landmarks': LANDMARKS,
    'outbound_radius_m': 1., 'home_arrival_radius_m': .2,
    'home_frame': 'encoder-only local origin at reset',
    'world_protocol_sha256': memory_world.PROFILE_SHA256,
    'source_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                      for name in ('task_profiles.py', 'task_mechanics.py', 'memory_task.py')}}
PROTOCOL_SHA256 = sha256(PROTOCOL)


def identity(scenario, calibration):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown declared task profile')
    mechanisms._fields(calibration, ('radius_m', 'track_m', 'quantum_rad'), 'body calibration')
    for key, value in calibration.items():
        mechanisms._number(value, key, positive=True)
    if calibration['quantum_rad'] != PROTOCOL['encoder_quantum_rad']:
        raise ValueError('Encoder quantum differs from declared emulation protocol')
    return sha256({'scenario': scenario, 'protocol': PROTOCOL, 'calibration': calibration})


def body_calibration(env):
    """Read fixed dimensions/sign convention from the loaded pinned body.

    +Y shaft axes, left at +Y, and body +X forward imply +angle means forward
    under no-slip kinematics (omega cross bottom-radius points toward -X).
    Runtime direction/odometry qualification is still required.
    """
    model = env.model
    wheels = [model.geom(name).id for name in ('left_wheel_geom', 'right_wheel_geom')]
    bodies = [model.body(name).id for name in ('left_wheel', 'right_wheel')]
    joints = [env.left_hinge_id, env.right_hinge_id]
    if any(int(model.geom_type[g]) != 5 for g in wheels) or any(int(model.jnt_type[j]) != 3 for j in joints):
        raise ValueError('Expected pinned cylinder wheels and hinge encoders')
    radii = [float(model.geom_size[g, 0]) for g in wheels]
    positions = [[float(v) for v in model.body_pos[b]] for b in bodies]
    if any(list(map(float, model.jnt_axis[j])) != [0., 1., 0.] for j in joints):
        raise ValueError('Unknown wheel encoder forward signs')
    if any(list(map(float, model.body_quat[b])) != [1., 0., 0., 0.] for b in bodies):
        raise ValueError('Unsupported rotated wheel bodies')
    if radii[0] != radii[1] or positions[0][0] != positions[1][0] or positions[0][2] != positions[1][2]:
        raise ValueError('Unsupported asymmetric body calibration')
    calibration = {'radius_m': radii[0], 'track_m': positions[0][1] - positions[1][1],
                   'quantum_rad': PROTOCOL['encoder_quantum_rad']}
    identity(SCENARIOS[0], calibration)
    return calibration


def encoder_angles(env):
    """Expose only the named hinges, never base qpos or true position."""
    angles = [float(env.data.qpos[int(env.model.jnt_qposadr[j])])
              for j in (env.left_hinge_id, env.right_hinge_id)]
    return mechanisms._pair(angles, 'measured shaft angles')


def configure_world(env):
    # Reuse the reviewed authored layout; do not run its hidden gate schedule.
    memory_world.configure(env, memory_world.initial_state(close_subject_id=None))


def initialize(scenario, episode_id, wheel_angles, calibration):
    mechanisms._identifier(episode_id)
    return validate_state({'version': 1, 'scenario': scenario,
        'profile_sha256': identity(scenario, calibration), 'episode_id': episode_id,
        'last_tick': None, 'phase': 'explore' if scenario == SCENARIOS[0] else 'outbound',
        'active': None, 'dwell_ticks': 0, 'completed_ids': [], 'outbound_reached': False,
        'selector': mechanisms.initial_exploration(max_landmarks=2, max_visits=1, max_decisions=2)
                    if scenario == SCENARIOS[0] else None,
        'odometry': mechanisms.initial_odometry(wheel_angles, **calibration,
                    max_steps=PROTOCOL['max_ticks'], max_travel_m=PROTOCOL['max_travel_m'])})


def validate_state(state):
    mechanisms._fields(state, ('version', 'scenario', 'profile_sha256', 'episode_id', 'last_tick',
        'phase', 'active', 'dwell_ticks', 'completed_ids', 'outbound_reached', 'selector', 'odometry'), 'task state')
    mechanisms._version(state['version'])
    mechanisms._identifier(state['episode_id'])
    mechanisms._odometry(state['odometry'])
    if state['profile_sha256'] != identity(state['scenario'], state['odometry']['calibration']):
        raise ValueError('Incompatible/bounded task protocol or calibration')
    tick = state['last_tick']
    if tick is not None:
        mechanisms._integer(tick, 'task tick', high=PROTOCOL['max_ticks'] - 1)
    if state['odometry']['steps'] != (0 if tick is None else tick):
        raise ValueError('Odometry cursor differs from task boundary')
    if state['odometry']['max_steps'] != PROTOCOL['max_ticks'] or state['odometry']['max_travel_m'] != PROTOCOL['max_travel_m']:
        raise ValueError('Odometry budgets differ from protocol')
    dwell = mechanisms._integer(state['dwell_ticks'], 'stopped dwell', high=PROTOCOL['dwell_ticks'])
    if type(state['outbound_reached']) is not bool:
        raise ValueError('Invalid outbound state')
    if state['scenario'] == SCENARIOS[0]:
        if state['phase'] not in ('explore', 'complete') or state['outbound_reached']:
            raise ValueError('Invalid exploration phase')
        completed = state['completed_ids']
        ids = {p['id'] for p in LANDMARKS}
        if type(completed) is not list or len(completed) > 2 or any(type(i) is not str or i not in ids for i in completed) or len(set(completed)) != len(completed):
            raise ValueError('Invalid completed inspection IDs')
        active = state['active']
        if active is not None and (type(active) is not str or active not in ids or active in completed):
            raise ValueError('Invalid retained visible target')
        selector = state['selector']
        mechanisms._fields(selector, ('version', 'visits', 'decisions', 'max_landmarks', 'max_visits', 'max_decisions'), 'inspection selector')
        mechanisms._version(selector['version'])
        for key in ('decisions', 'max_landmarks', 'max_visits', 'max_decisions'):
            mechanisms._integer(selector[key], key)
        if type(selector['visits']) is not dict or len(selector['visits']) > len(LANDMARKS):
            raise ValueError('Invalid inspection count map')
        for count in selector['visits'].values():
            mechanisms._integer(count, 'inspection count', low=1, high=1)
        expected = mechanisms.initial_exploration(max_landmarks=2, max_visits=1, max_decisions=2)
        selected = completed + ([] if active is None else [active])
        expected.update(visits={key: 1 for key in selected}, decisions=len(selected))
        if selector != expected or type(selector) is not dict:
            raise ValueError('Inspection counts disagree with selected/completed IDs')
        if (state['phase'] == 'complete') != (len(completed) == 2) or active is None and dwell and state['phase'] != 'complete':
            raise ValueError('Inconsistent exploration dwell/completion')
    else:
        if state['phase'] not in ('outbound', 'home', 'complete') or any(state[key] is not None for key in ('active', 'selector')) or state['completed_ids'] != []:
            raise ValueError('Invalid homing state')
        if state['outbound_reached'] != (state['phase'] != 'outbound') or state['phase'] == 'outbound' and dwell:
            raise ValueError('Homing cannot arrive without outbound departure')
    if (state['phase'] == 'complete') != (dwell == PROTOCOL['dwell_ticks']):
        raise ValueError('Completion requires consecutive stopped dwell')
    if tick is None and (state['active'] is not None or state['completed_ids'] or dwell
                         or state['phase'] != ('explore' if state['scenario'] == SCENARIOS[0] else 'outbound')):
        raise ValueError('Initial task state cannot contain prior progress')
    if len(canonical_bytes(state)) > 16384:
        raise ValueError('Task state exceeds byte limit')
    return copy.deepcopy(state)


def capture(env, state, tick, *, wheel_angles=None):
    """Acquisition boundary: virtual visible/proximity sensor and named encoders.

    Homing never acquires base pose, goal or obstacle geometry in this function.
    Geometry-derived virtual proximity is confined to exploration and declared.
    """
    state = validate_state(state)
    angles = encoder_angles(env) if wheel_angles is None else mechanisms._pair(wheel_angles, 'measured shaft angles')
    landmarks = []
    if state['scenario'] == SCENARIOS[0]:
        pose = [*map(float, env._base_xy()), float(env._base_yaw())]
        circles = [[float(env.data.geom_xpos[g, 0]), float(env.data.geom_xpos[g, 1]), float(env.model.geom_size[g, 0])]
                   for g in env.obstacle_ids]
        world = {'cues': [], 'landmarks': copy.deepcopy(LANDMARKS), 'passages': [], 'common_goal_id': LANDMARKS[-1]['id']}
        visible = memory_task.capture_symbolic(world, pose, circles, episode_id=state['episode_id'], tick=tick)
        positions = {p['id']: p['xy'] for p in LANDMARKS}
        landmarks = [{**item, 'near': math.dist(pose[:2], positions[item['id']]) <= PROTOCOL['inspection_radius_m']}
                     for item in visible['landmarks']]
    return {'version': 1, 'episode_id': state['episode_id'], 'tick': tick,
            'time_s': float(env.data.time), 'angles_rad': angles, 'landmarks': landmarks}


def advance(state, packet):
    """Retain a target; choose again only after stopped visible inspection.

    The returned cue is neutral [0,0] during homing arrival; hold suppresses live
    actions after inference. No true-pose speed, hidden distance or planner is read.
    """
    state = validate_state(state)
    mechanisms._fields(packet, ('version', 'episode_id', 'tick', 'time_s', 'angles_rad', 'landmarks'), 'task packet')
    mechanisms._version(packet['version'])
    tick = mechanisms._integer(packet['tick'], 'packet tick', high=PROTOCOL['max_ticks'] - 1)
    if packet['episode_id'] != state['episode_id'] or tick != (0 if state['last_tick'] is None else state['last_tick'] + 1):
        raise ValueError('Missing/stale task or encoder packet')
    time_s = mechanisms._number(packet['time_s'], 'encoder time', nonnegative=True)
    if not math.isclose(time_s, tick * PROTOCOL['control_interval_s'], rel_tol=0., abs_tol=1e-9):
        raise ValueError('Encoder stream time differs from control boundary')
    angles = mechanisms._pair(packet['angles_rad'], 'measured shaft angles')
    before = state['odometry']['encoder_counts']
    if tick:
        state['odometry'] = mechanisms.odometry_step(state['odometry'], angles,
            max_increment_rad=PROTOCOL['max_increment_rad'])
    elif angles != state['odometry']['wheel_angles_rad']:
        raise ValueError('Initial encoder stream differs from reset baseline')
    stopped = tick > 0 and before == state['odometry']['encoder_counts']
    state['last_tick'] = tick
    landmarks = packet['landmarks']
    if type(landmarks) is not list or len(landmarks) > len(LANDMARKS):
        raise ValueError('Invalid bounded visible landmark packet')
    visible = {}
    for item in landmarks:
        mechanisms._fields(item, ('id', 'bearing_rad', 'near'), 'visible proximity landmark')
        if type(item['id']) is not str or item['id'] not in {p['id'] for p in LANDMARKS} or item['id'] in visible or type(item['near']) is not bool:
            raise ValueError('Unknown/duplicate landmark or invalid proximity bit')
        angle = mechanisms._number(item['bearing_rad'], 'visible bearing')
        if abs(angle) > PROTOCOL['visible_half_fov_rad']:
            raise ValueError('Bearing outside declared visibility')
        visible[item['id']] = item
    events, hold = [], False
    if state['scenario'] == SCENARIOS[0]:
        if state['active'] is None:
            choices = [{k: item[k] for k in ('id', 'bearing_rad')} for item in landmarks
                       if item['id'] not in state['completed_ids']]
            choice = mechanisms.choose_landmark(state['selector'], {'landmarks': choices})
            state['selector'], state['active'] = choice['state'], choice['landmark']['id']
            events.append({'kind': 'target_selected', 'id': state['active']})
        if state['active'] not in visible:
            raise mechanisms.CueUnavailable('Retained inspection target is no longer visible')
        item = visible[state['active']]
        bearing, hold = item['bearing_rad'], item['near']
        state['dwell_ticks'] = state['dwell_ticks'] + 1 if hold and stopped else 0
        if state['dwell_ticks'] == PROTOCOL['dwell_ticks']:
            state['completed_ids'].append(state['active'])
            events.append({'kind': 'inspection_completed', 'id': state['active'], 'stopped_dwell_ticks': state['dwell_ticks']})
            state['active'] = None
            if len(state['completed_ids']) == len(LANDMARKS):
                state['phase'] = 'complete'
            else:
                state['dwell_ticks'] = 0
        cue = [math.cos(bearing), math.sin(bearing)]
    else:
        if landmarks:
            raise ValueError('Homing does not accept landmark/goal truth')
        odometry = state['odometry']
        if state['phase'] == 'outbound' and math.hypot(odometry['x_m'], odometry['y_m']) >= PROTOCOL['outbound_radius_m']:
            state['phase'], state['outbound_reached'] = 'home', True
            events.append({'kind': 'home_started', 'estimated_departure_m': math.hypot(odometry['x_m'], odometry['y_m'])})
        if state['phase'] == 'outbound':
            bearing = math.remainder(math.atan2(-odometry['y_m'], PROTOCOL['outbound_radius_m'] - odometry['x_m']) - odometry['yaw_rad'], math.tau)
            cue = [math.cos(bearing), math.sin(bearing)]
        else:
            home = mechanisms.home_bearing(odometry, arrival_radius_m=PROTOCOL['home_arrival_radius_m'])
            hold = home['arrived']
            bearing = home['bearing_rad']
            cue = [0., 0.] if bearing is None else [math.cos(bearing), math.sin(bearing)]
            state['dwell_ticks'] = state['dwell_ticks'] + 1 if hold and stopped else 0
            if state['dwell_ticks'] == PROTOCOL['dwell_ticks']:
                state['phase'] = 'complete'
                events.append({'kind': 'home_completed', 'estimated_distance_m': home['distance_m'], 'stopped_dwell_ticks': state['dwell_ticks']})
    return validate_state(state), cue, hold, events
