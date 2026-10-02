"""Loaded, fixed calibration for one development body; no online fitting.

The contact probe is shared with the standalone diagnostic. Only derived contact
caches and shaft angles are read. No true pose enters compensation.
"""
import copy
import hashlib
import json
import math

SCENARIO = 'calibrated-wheel-compensation'
GROUND_SUPPORT = ['left_wheel_geom', 'right_wheel_geom', 'caster_wheel_geom']
ROBOT_BODIES = {'base', 'left_wheel', 'right_wheel', 'front_caster_mount', 'caster_wheel'}
ROBOT_GEOMS = {'base_geom', 'left_wheel_geom', 'right_wheel_geom', 'caster_fork',
               'caster_wheel_geom', 'cam_left_marker', 'cam_right_marker'}
ARTIFACT = {'report_sha256': '9d2cd4729d32f84b490db3a6726764111989fcc80be74c7a2ba44a97cb419331',
 'protocol_sha256': 'bf883b89156201ccd35659fa7971fda507876e357c733356ed3eec59bac760f0',
 'baseline_model_sha256': 'c4d30fef8fbe05739e72e762d10d2dc435c1c831993a32d0662560d494b158e5',
 'model_sha256': 'bf3ca4b0d32600444e0f23e658c790da50a7675fb3c26fee8f9b0a16e0839d67',
 'nominal_gains_rad_s_per_control': [14.878897911022118, 14.878897948225164],
 'fit': {'version': 1,
         'gains_rad_s_per_control': [11.851776561760323, 14.374415787256368],
         'excitation': [160.0000047683716, 160.0000047683716],
         'rmse_rad_s': [0.435802065001471, 0.3676085033176917],
         'relative_rmse': [0.05804209068994394, 0.04040271846909737],
         'sample_count': 400,
         'gain_bounds': [1.0, 100.0],
         'control_limit': 2.0},
 'fit_bounds': {'max_samples': 400,
                'min_samples': 100,
                'min_excitation': 1.0,
                'gain_bounds': [1.0, 100.0],
                'control_limit': 2.0,
                'dt_bounds_s': [0.019999999, 0.020000001],
                'max_rate_rad_s': 100.0,
                'max_residual_rad_s': 2.0,
                'max_relative_rmse': 0.2},
 'between_trial_gain_range_over_mean_max': 0.2,
 'observed_gain_range_over_mean': [0.1195000151912334, 0.03133850076547491]}
PROTOCOL = {
    'version': 1, 'scenario': SCENARIO, 'claim': 'loaded fixed calibration; no online learning or physical qualification',
    'artifact': ARTIFACT, 'world_protocol_sha256': 'ed6d7996b1c5dd412621533ebc87c0712ef3ed618031167774f27e313371379c',
    'start_pose': [-3.5, 0., 0.], 'goal_xy': [-3.5, 3.],
    'left_gear': 3.*.8, 'right_gear': 3., 'radius_m': .06, 'track_m': .36,
    'max_compensation_ratio': 1.5, 'control_limit': 2., 'max_steps': 600,
    'pipeline': {'mujoco_version': '3.3.6', 'integrator': 'Euler', 'physics_dt_s': .002,
                 'frame_skip': 10, 'control_dt_s': .02, 'max_contacts_per_stage': 128},
    'contact_scope': 'all timed pairs retained; reject unexpected robot-incident contacts; world-only pairs may move',
    'contact_coverage': 'ten pre-control caches plus unchanged final cache; no continuous collision or endpoint claim',
    'contact_records': {'slots': [11, 128], 'unused': 'zero; counts delimit valid slots',
                        'classes': {'padding':0, 'world_only':1, 'rover_ground_support':2, 'unexpected_robot_contact':3}},
    'action_replay': 'recorded effective action once, checked against nominal manual intent',
    'keyboard_nominal': {'velocity': .3, 'heading': .2},
    'limits': 'straight steady-state fit; combined/transient motion and task performance unqualified',
}
def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

PROFILE_SHA256 = _sha(PROTOCOL)
MAX_PACKET_BYTES = 512 * 1024
MAX_TICK_BYTES = 32 * 1024
TICK_FIELDS = {'body_nominal_action', 'body_nominal_control', 'body_encoder_before',
               'body_encoder_after', 'body_encoder_increment', 'body_dt', 'body_contact_ids',
               'body_contact_distances', 'body_contact_classes', 'body_contact_counts',
               'body_contact_times', 'body_stage_controls', 'body_end_data_time'}


def profile_identity():
    return {'version': 1, 'profile_sha256': PROFILE_SHA256,
            'artifact_sha256': ARTIFACT['report_sha256'],
            'model_sha256': ARTIFACT['model_sha256']}


def contact_ownership(mj, model):
    """Partition every known geometry by the actual pinned base-body ancestry."""
    if not 1 < model.nbody <= 128 or not 1 <= model.ngeom <= 128:
        raise ValueError('Body/geometry count outside bounded ownership protocol')
    root = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, 'base')
    if not 0 < root < model.nbody:
        raise ValueError('Missing pinned robot base body')
    owned = set()
    for body in range(model.nbody):
        current, seen = body, set()
        while current != 0:
            if not 0 <= current < model.nbody or current in seen:
                raise ValueError('Invalid body ownership tree')
            seen.add(current)
            if current == root:
                owned.add(body)
            current = int(model.body_parentid[current])
    bodies = [{'body_id': body, 'name': mj.mj_id2name(model, mj.mjtObj.mjOBJ_BODY, body),
               'parent_id': int(model.body_parentid[body])} for body in sorted(owned)]
    if {entry['name'] for entry in bodies} != ROBOT_BODIES or len(bodies) != len(ROBOT_BODIES):
        raise ValueError('Pinned robot descendant body set changed')
    geometries = []
    for geom in range(model.ngeom):
        body = int(model.geom_bodyid[geom])
        if not 0 <= body < model.nbody:
            raise ValueError('Geometry references unknown body')
        geometries.append({'geom_id': geom, 'name': mj.mj_id2name(model, mj.mjtObj.mjOBJ_GEOM, geom),
                           'body_id': body, 'body_name': mj.mj_id2name(model, mj.mjtObj.mjOBJ_BODY, body),
                           'owner': 'robot' if body in owned else 'world'})
    robot = [entry for entry in geometries if entry['owner'] == 'robot']
    if {entry['name'] for entry in robot} != ROBOT_GEOMS or len(robot) != len(ROBOT_GEOMS):
        raise ValueError('Pinned robot descendant geometry set changed')
    if any(entry['name'] in ROBOT_GEOMS for entry in geometries if entry['owner'] == 'world'):
        raise ValueError('Robot geometry cannot be excluded as world-only')
    return {'base_body_id': root, 'robot_bodies': bodies, 'geometries': geometries}


class ContactProbe:
    """Read only the derived contact pairs; never contact forces or controls.

    mj_step/Euler computes contact at t before integration to t+dt. End data.contact
    still caches the last such stage. No mj_forward is added to refresh it.
    """
    def __init__(self, mujoco, env):
        self.mj, self.env = mujoco, env
        self.callback = self._capture
        self.installed, self.active = False, False
        self.violations = []
        self.count = 0
        self.stages = []
        self.model_address, self.data_address = env.model._address, env.data._address
        self._check_pipeline()
        self.ownership = contact_ownership(mujoco, env.model)
        self.robot_geom_ids = {entry['geom_id'] for entry in self.ownership['geometries'] if entry['owner'] == 'robot'}
        names = ['floor', *GROUND_SUPPORT]
        identifiers = [self.mj.mj_name2id(env.model, self.mj.mjtObj.mjOBJ_GEOM, name) for name in names]
        if len(set(identifiers)) != len(names) or any(not 0 <= gid < env.model.ngeom for gid in identifiers):
            raise ValueError('Pinned named ground/support geometries required')
        self.support_pairs = {frozenset((identifiers[0], gid)) for gid in identifiers[1:]}
        if identifiers[0] in self.robot_geom_ids or any(gid not in self.robot_geom_ids for gid in identifiers[1:]):
            raise ValueError('Ground support ownership mismatch')

    def _check_pipeline(self):
        option = self.env.model.opt
        enums = self.mj.mjtDisableBit
        disabled_contact, disabled_actuation = int(enums.mjDSBL_CONTACT), int(enums.mjDSBL_ACTUATION)
        euler = int(self.mj.mjtIntegrator.mjINT_EULER)
        if (euler != 0 or disabled_contact != 1 << 4 or disabled_actuation != 1 << 11 or
                self.mj.__version__ != '3.3.6' or int(option.integrator) != euler or
                not math.isclose(float(option.timestep), .002, abs_tol=1e-12, rel_tol=0.) or
                self.env.frame_skip != 10 or int(option.disableflags) & (disabled_contact | disabled_actuation)):
            raise ValueError('Pinned Euler/contact/actuation pipeline required')

    def install(self):
        if self.mj.get_mjcb_control() is not None:
            raise ValueError('Refusing existing global control callback')
        self.mj.set_mjcb_control(self.callback)
        self.installed = True

    def close(self):
        if self.installed:
            unexpected = self.mj.get_mjcb_control() is not self.callback
            self.installed = False
            if unexpected:
                raise ValueError('Global callback changed during diagnostic')
            # We accepted only None before installation; restore that state.
            self.mj.set_mjcb_control(None)

    def begin(self, tick):
        if not self.installed or self.active or self.violations:
            raise ValueError('Invalid callback interval lifecycle')
        self._check_pipeline()
        self.tick, self.start = tick, float(self.env.data.time)
        self.count, self.stages = 0, []
        self.active = True

    def _pairs(self, model, data):
        count = int(data.ncon)
        if not 0 <= count <= PROTOCOL['pipeline']['max_contacts_per_stage']:
            raise ValueError('Contact count outside bounded protocol')
        pairs = []
        for index in range(count):
            contact = data.contact[index]
            ids = [int(contact.geom1), int(contact.geom2)]
            if any(not 0 <= gid < model.ngeom for gid in ids):
                raise ValueError('Contact references unknown geometry')
            names = [self.mj.mj_id2name(model, self.mj.mjtObj.mjOBJ_GEOM, gid) for gid in ids]
            if any(type(name) is not str or not name for name in names):
                raise ValueError('Contact references unnamed/unknown geometry')
            allowed = (frozenset(ids) in self.support_pairs and
                       (names[0] == 'floor' and names[1] in GROUND_SUPPORT or
                        names[1] == 'floor' and names[0] in GROUND_SUPPORT))
            distance = float(contact.dist)
            if not math.isfinite(distance):
                raise ValueError('Nonfinite contact distance')
            incident = any(gid in self.robot_geom_ids for gid in ids)
            classification = ('rover_ground_support' if allowed else
                              'unexpected_robot_contact' if incident else 'world_only')
            pairs.append({'geom_ids': ids, 'geom_names': names, 'distance_m': distance,
                          'allowed_ground_support': allowed, 'classification': classification,
                          'rejects_fit': incident and not allowed})
        return pairs

    def _capture(self, model, data):
        # Retain failures and defer rejection until end so the entire interval is observed.
        self.count += 1
        try:
            if not self.active or model._address != self.model_address or data._address != self.data_address:
                raise ValueError('Callback outside interval or unexpected model/data')
            if self.count > 10:
                raise ValueError('Extra callback stage')
            packet = {'stage': self.count - 1, 'time_s': float(data.time),
                      'control': list(map(float, data.ctrl)), 'pairs': []}
            self.stages.append(packet)
            packet['pairs'] = self._pairs(model, data)
        except Exception as error:
            if len(self.violations) < 8:
                self.violations.append(str(error)[:256])

    def end(self):
        if not self.active:
            raise ValueError('No active callback interval')
        self.active = False
        data = self.env.data
        errors = list(self.violations)
        if self.count != 10 or len(self.stages) != 10:
            errors.append('Expected exactly ten complete callback packets')
        control = list(map(float, data.ctrl))
        if len(control) != 2 or not all(math.isfinite(u) for u in control):
            errors.append('Expected two finite actual controls')
        for index, stage in enumerate(self.stages):
            if not math.isclose(stage['time_s'], self.start + index * .002, abs_tol=1e-9, rel_tol=0.):
                errors.append('Callback stage time mismatch')
            if stage['control'] != control or not all(math.isfinite(u) for u in stage['control']):
                errors.append('Nonfinite/changing stage controls')
        if not math.isclose(float(data.time), self.start + .02, abs_tol=1e-9, rel_tol=0.):
            errors.append('Control interval time mismatch')
        end = {'data_time_s': float(data.time), 'contact_cache_time_s': self.start + .018, 'pairs': []}
        try:
            end['pairs'] = self._pairs(self.env.model, data)
        except ValueError as error:
            errors.append(str(error))
        if self.stages and end['pairs'] != self.stages[-1]['pairs']:
            errors.append('End contacts differ from last pre-integration cache')
        contact = any(pair['rejects_fit']
                      for packet in [*self.stages, end] for pair in packet['pairs'])
        return {'tick': self.tick, 'start_time_s': self.start, 'callback_count': self.count,
                'stages': self.stages, 'end': end, 'contact': contact,
                'coverage_passed': not errors, 'coverage_errors': errors}


def effective_control(action):
    """Pinned converter restricted to its unnormalized branch; validation only."""
    import numpy as np
    if type(action) is not list or len(action) != 2 or any(type(x) not in (int, float) or not math.isfinite(x) for x in action):
        raise ValueError('Two finite numeric action values required')
    wheels = [action[0] - .5 * action[1], action[0] + .5 * action[1]]
    if any(abs(wheel) > 1 for wheel in wheels):
        raise ValueError('Inverse would invoke upstream normalization/clipping')
    return (np.asarray(wheels, dtype=np.float32) * 2).tolist()


def inverse_control(control):
    import numpy as np
    if type(control) is not list or len(control) != 2 or any(type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 2 for x in control):
        raise ValueError('Two finite controls within +/-2 required')
    target = np.asarray(control, dtype=np.float32).tolist()
    action = [(target[0] + target[1]) / 4, (target[1] - target[0]) / 2]
    if effective_control(action) != target:
        raise ValueError('Exact float32 control inverse roundtrip failed')
    return {'action': action, 'control_float32': target,
            'rounding_delta': [b - a for a, b in zip(control, target)]}


def plan_action(action):
    from .task_mechanics import _pair, compensate_wheels
    import numpy as np
    array = np.asarray(action)
    if array.shape != (2,) or array.dtype.kind not in 'fiu' or not np.isfinite(array).all():
        raise ValueError('Two finite nominal manual action values required')
    nominal = _pair(array.astype(np.float64).tolist(), 'nominal manual action')
    control = effective_control(nominal)
    compensation = compensate_wheels(control, ARTIFACT['fit'],
        nominal_gains_rad_s_per_control=ARTIFACT['nominal_gains_rad_s_per_control'],
        max_compensation_ratio=PROTOCOL['max_compensation_ratio'])
    inverse = inverse_control(compensation['control'])
    return {'nominal_action': nominal, 'nominal_control': control,
            'applied_action': inverse['action'], 'applied_control': inverse['control_float32'],
            'gain_ratio': compensation['gain_ratio'], 'rounding_delta': inverse['rounding_delta']}


def initialize_state(episode_id, angles, time_s):
    from .task_mechanics import _pair, _number
    return {**profile_identity(), 'episode_id': episode_id, 'last_tick': None,
            'phase': 'loaded', 'previous_angles_rad': _pair(list(angles), 'raw encoders'),
            'time_s': _number(time_s, 'body time', nonnegative=True)}


def validate_state(state, identity, *, episode, episode_step):
    from .task_mechanics import _fields, _pair, _number
    _fields(state, ('version', 'profile_sha256', 'artifact_sha256', 'model_sha256',
                   'episode_id', 'last_tick', 'phase', 'previous_angles_rad', 'time_s'), 'body state')
    if identity != profile_identity() or any(type(state[k]) is not type(v) or state[k] != v
                                           for k, v in identity.items()):
        raise ValueError('Loaded body calibration identity differs')
    expected = episode_step - 1 if episode_step else None
    if (type(episode) is not int or episode < 0 or type(episode_step) is not int or not 0 <= episode_step <= 600 or
            state['episode_id'] != f'episode-{episode}' or
            type(state['last_tick']) is not type(expected) or state['last_tick'] != expected or
            state['phase'] != ('compensating' if episode_step else 'loaded')):
        raise ValueError('Body cursor/phase differs from paused application boundary')
    _pair(state['previous_angles_rad'], 'body raw encoders')
    timestamp = _number(state['time_s'], 'body time', nonnegative=True)
    if not math.isclose(timestamp, episode_step*.02, abs_tol=1e-9, rel_tol=0.):
        raise ValueError('Body time differs from episode cursor')
    return copy.deepcopy(state)


def validate_native(state, model, data, env):
    angles = [float(data.qpos[int(model.jnt_qposadr[j])])
              for j in (env.left_hinge_id, env.right_hinge_id)]
    if angles != state['previous_angles_rad'] or float(data.time) != state['time_s']:
        raise ValueError('Body raw encoder/time state differs from native data')



def validate_snapshot_application(application, env, model, data):
    if (type(application) is not dict or type(application.get('schema_version')) is not int or
            application.get('schema_version') != 5 or
            application.get('phase') != 'paused' or application.get('scenario') != SCENARIO or
            application.get('controller') != 'manual'):
        raise ValueError('Body native snapshot requires its paused application/profile')
    state = validate_state(application.get('body_state'), env._body_profile_identity,
                           episode=application.get('episode'), episode_step=application.get('episode_step'))
    validate_native(state, model, data, env)

def configure(env, episode_id):
    import mujoco
    from . import memory_world, task_profiles
    from .snapshots import _model_digest
    if memory_world.PROFILE_SHA256 != PROTOCOL['world_protocol_sha256']:
        raise ValueError('Pinned calibration authored world protocol differs')
    if mujoco.get_mjcb_control() is not None:
        raise ValueError('Body setup refuses existing global control callback')
    left = mujoco.mj_name2id(env.model, mujoco.mjtObj.mjOBJ_ACTUATOR, 'left_motor')
    right = mujoco.mj_name2id(env.model, mujoco.mjtObj.mjOBJ_ACTUATOR, 'right_motor')
    gear = env.model.actuator_gear.tolist()
    nominal = [[3., 0., 0., 0., 0., 0.], [3., 0., 0., 0., 0., 0.]]
    perturbed = [[2.4, 0., 0., 0., 0., 0.], [3., 0., 0., 0., 0., 0.]]
    # The accepted diagnostic performed 3*.8: retain the exact binary value.
    perturbed[0][0] = 3.*.8
    if (left, right) != (0, 1) or env.model.nu != 2 or gear not in (nominal, perturbed):
        raise ValueError('Pinned scalar two-motor gear/order required')
    expected = ARTIFACT['baseline_model_sha256'] if gear == nominal else ARTIFACT['model_sha256']
    if _model_digest(env.model) != expected or float(env._action_scale) != 2.:
        raise ValueError('Pinned body model/control scale differs')
    memory_world.configure(env, memory_world.initial_state(close_subject_id=None))
    env._goal_xy[:] = PROTOCOL['goal_xy']
    env.model.site_pos[env.goal_site_id, :2] = PROTOCOL['goal_xy']
    env.place_robot(*PROTOCOL['start_pose'], env.data.qpos.copy(), env.data.qvel.copy())
    env.model.actuator_gear[0, 0] = 3.*.8
    mujoco.mj_forward(env.model, env.data)
    env._prev_xy = env._base_xy().copy()
    calibration = task_profiles.body_calibration(env)
    if calibration['radius_m'] != .06 or not math.isclose(calibration['track_m'], .36, abs_tol=1e-12, rel_tol=0.):
        raise ValueError('Pinned body physical dimensions differ')
    if _model_digest(env.model) != ARTIFACT['model_sha256']:
        raise ValueError('Constructed body model differs from fitted artifact')
    # Probe construction validates the exact named descendant geometry partition.
    env._body_contact_ownership = ContactProbe(mujoco, env).ownership
    env._body_profile_identity = profile_identity()
    return initialize_state(episode_id, task_profiles.encoder_angles(env), float(env.data.time))


class BodyFailure(ValueError):
    def __init__(self, message, packet):
        self.packet = packet
        super().__init__(message)


def step(env, state, nominal_action, tick, *, action_override=None):
    """Apply one mapped action and retain every observed contact cache.

    Override is already effective; reject mismatch and never compensate it again.
    The outgoing state advances once in either replay mode.
    """
    import mujoco
    import numpy as np
    from .task_profiles import encoder_angles
    plan = plan_action(nominal_action)
    action = plan['applied_action'] if action_override is None else list(map(float, action_override))
    if action != plan['applied_action']:
        raise ValueError('Recorded body effective override differs from nominal plan')
    if state['last_tick'] != (tick - 1 if tick else None):
        raise ValueError('Body tick cursor differs')
    validate_native(state, env.model, env.data, env)
    probe = ContactProbe(mujoco, env)
    before = encoder_angles(env)
    packet = {'command': plan, 'interval': None, 'encoder_before': before}
    try:
        probe.install()
        probe.begin(tick)
        result = env.step(np.asarray(action, dtype=np.float64))
        interval = packet['interval'] = probe.end()
        after = packet['encoder_after'] = encoder_angles(env)
        dt = packet['dt_s'] = float(env.data.time) - state['time_s']
        increments = packet['increments_rad'] = [b-a for a,b in zip(before, after)]
        if len(json.dumps(packet, allow_nan=False, separators=(',', ':')).encode()) > MAX_PACKET_BYTES:
            raise BodyFailure('Body contact packet exceeds bounded size', packet)
        if not interval['coverage_passed'] or interval['contact']:
            raise BodyFailure('Body contact/callback interval rejected', packet)
        if list(map(float, env.data.ctrl)) != plan['applied_control']:
            raise BodyFailure('Actual body controls differ from mapped float32 target', packet)
        if (not math.isclose(dt, .02, abs_tol=1e-9, rel_tol=0.) or
                any(not math.isfinite(v) or abs(v/dt) > 100. for v in increments)):
            raise BodyFailure('Body encoder rate/interval rejected', packet)
    except BodyFailure:
        raise
    except Exception as error:
        if probe.active:
            packet['interval'] = probe.end()
        raise BodyFailure(str(error), packet) from error
    finally:
        probe.close()
    advanced = {**state, 'last_tick': tick, 'phase': 'compensating',
                'previous_angles_rad': after, 'time_s': float(env.data.time)}
    arrays = {'body_nominal_action': np.asarray(plan['nominal_action'], np.float64),
              'body_nominal_control': np.asarray(plan['nominal_control'], np.float32),
              'body_encoder_before': np.asarray(before, np.float64),
              'body_encoder_after': np.asarray(after, np.float64),
              'body_encoder_increment': np.asarray(increments, np.float64), 'body_dt': np.array(dt, np.float64)}
    arrays.update(contact_arrays(packet['interval']))
    return result, advanced, packet, arrays


def contact_arrays(interval):
    """Counts delimit 11x128 zero-padded slots; the last row is the cached end.

    Classes: 0 padding, 1 world-only, 2 allowed rover/floor, 3 unexpected robot.
    Geometry names/body ownership are recorded once and bound to the model digest.
    """
    import numpy as np
    if not interval['coverage_passed'] or interval['callback_count'] != 10 or len(interval['stages']) != 10:
        raise ValueError('Complete contact stages required for numeric records')
    packets = [*interval['stages'], interval['end']]
    ids = np.zeros((11, 128, 2), np.int16)
    distances = np.zeros((11, 128), np.float64)
    classes = np.zeros((11, 128), np.uint8)
    counts = np.zeros(11, np.int16)
    codes = {'world_only':1, 'rover_ground_support':2, 'unexpected_robot_contact':3}
    for row, packet in enumerate(packets):
        pairs = packet['pairs']
        if len(pairs) > 128:
            raise ValueError('Contact record overflow; no truncation permitted')
        counts[row] = len(pairs)
        for column, pair in enumerate(pairs):
            identifiers = pair['geom_ids']
            if len(identifiers) != 2 or any(type(gid) is not int or not 0 <= gid < 128 for gid in identifiers):
                raise ValueError('Invalid bounded contact geometry IDs')
            if not math.isfinite(pair['distance_m']):
                raise ValueError('Nonfinite contact record distance')
            ids[row, column] = identifiers
            distances[row, column] = pair['distance_m']
            classes[row, column] = codes[pair['classification']]
    return {'body_contact_ids': ids, 'body_contact_distances': distances,
            'body_contact_classes': classes, 'body_contact_counts': counts,
            'body_contact_times': np.array([p['time_s'] for p in interval['stages']] +
                                           [interval['end']['contact_cache_time_s']], np.float64),
            'body_stage_controls': np.array([p['control'] for p in interval['stages']], np.float64),
            'body_end_data_time': np.array(interval['end']['data_time_s'], np.float64)}


def measurement_event(packet):
    interval = packet['interval']
    return {key: copy.deepcopy(packet[key]) for key in
            ('command', 'encoder_before', 'encoder_after', 'dt_s', 'increments_rad')} | {
            'callback_count': interval['callback_count'], 'contact': interval['contact'],
            'coverage_passed': interval['coverage_passed'], 'coverage_errors': interval['coverage_errors'],
            'contact_counts': [len(p['pairs']) for p in [*interval['stages'], interval['end']]]}
