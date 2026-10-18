"""One frozen, near-planar native-contact puck profile, not Engine-integrated.

Native installation is explicit and lazy; no trained controller is implemented.
Geometry is privileged evaluator/teacher data; project() is the only eight-value
student input. ContactProbe retains its existing calibration classifications;
this module validates its raw timing/pairs and derives separate task meanings.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from .body_profile import GROUND_SUPPORT, ROBOT_GEOMS
from .task_mechanics import _fields, _identifier, _integer, _number, _pair, _version

SCENARIO = 'puck-pushing-development'
PROTOCOL_SHA256 = '77ce33fa593247715abe99ff2ba0eca399edbac44b29a580d4f92410b8013c30'
PROTOCOL_PATH = 'docs/plans/m6-puck-pushing-protocol-v5.json'
WORLD_GEOMS = {'floor', 'wall_n', 'wall_s', 'wall_e', 'wall_w',
               *[f'obstacle{i}' for i in range(20)]}
CONTACT_FIELDS = ('tick', 'time_s', 'source_start_time_s', 'contact_cache_time_s',
                  'initial_forwarded', 'rover_puck_contact', 'other_robot_contact',
                  'rover_ground_support', 'puck_floor_support', 'puck_wall_contact',
                  'rover_puck_max_penetration_m', 'failure')


def _read(path):
    with Path(path).open('rb') as stream:
        data = stream.read(128 * 1024 + 1)
    if len(data) > 128 * 1024:
        raise ValueError('Source exceeds the fixed byte bound')
    return data


def load_protocol(repo_root):
    raw = _read(Path(repo_root) / PROTOCOL_PATH)
    if hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('Frozen puck protocol hash mismatch')
    return json.loads(raw)


def layout(repo_root, seed, split):
    """Return only an exact authored row; split admission is explicit."""
    _integer(seed, 'layout seed')
    protocol = load_protocol(repo_root)
    if split == 'mechanics':
        for row in protocol['physics_cases']:
            if row['seed'] == seed:
                return {key: row[key] for key in ('seed', 'rover_pose', 'puck_xy', 'goal_xy')} | {
                    'split': 'mechanics', 'initial_qvel': 'all zeros'}
    for row in protocol['layouts']:
        if row['seed'] == seed and row['split'] == split:
            return row
    raise ValueError('Unknown puck layout or wrong declared split')


def derive_xml(repo_root):
    """Derive exact pinned XML bytes without loading any native dependency."""
    spec = load_protocol(repo_root)['xml']
    raw = _read(Path(repo_root) / spec['source_path'])
    if hashlib.sha256(raw).hexdigest() != spec['source_sha256']:
        raise ValueError('Pinned checker XML hash mismatch')
    tree = ET.fromstring(raw)
    topology = [(node.tag, node.get('name')) for node in tree.iter()]
    for edit in spec['edits']:
        matches = tree.findall(edit['selector'])
        if len(matches) != 1:
            raise ValueError('Puck XML requires exactly one selector match')
        matches[0].attrib.update(edit['attributes'])
    if [(node.tag, node.get('name')) for node in tree.iter()] != topology:
        raise ValueError('Puck derivation changed named topology')
    derived = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    if len(derived) != spec['derived_bytes'] or hashlib.sha256(derived).hexdigest() != spec['derived_sha256']:
        raise ValueError('Derived puck XML bytes/hash mismatch')
    return derived


def _vector(value, size, label):
    if type(value) is not list or len(value) != size:
        raise ValueError(f'{label}: {size} finite values required')
    return [_number(v, label) for v in value]


def _time(actual, expected):
    if not math.isclose(_number(actual, 'time', nonnegative=True), expected, rel_tol=0., abs_tol=1e-9):
        raise ValueError('Stale/misaligned puck or contact time')


def _world(world):
    _fields(world, ('time_s', 'rover_pose', 'puck_xyz', 'puck_velocity_xy', 'goal_xy'), 'puck world')
    _number(world['time_s'], 'current qpos time', nonnegative=True)
    for key, size in [('rover_pose', 3), ('puck_xyz', 3), ('puck_velocity_xy', 2), ('goal_xy', 2)]:
        _vector(world[key], size, key)
    if any(abs(v) > 5 for v in world['goal_xy']):
        raise ValueError('Goal outside fixed arena')
    return world


def _native_values(data, *, base_qpos_adr, puck_qpos_adrs, puck_dof_adrs):
    """Validate current native arrays/bindings without an authored goal domain."""
    import numpy as np
    qpos, qvel = data.qpos, data.qvel
    for value in (qpos, qvel):
        if (not isinstance(value, np.ndarray) or value.ndim != 1 or not 1 <= value.size <= 4096
                or value.dtype.kind != 'f' or not np.isfinite(value).all()):
            raise ValueError('Finite bounded native qpos/qvel arrays required')
    base = _integer(base_qpos_adr, 'base qpos address', high=qpos.size - 7)
    for addresses, size, label in [(puck_qpos_adrs, qpos.size, 'puck qpos'),
                                    (puck_dof_adrs, qvel.size, 'puck dof')]:
        if type(addresses) is not list or len(addresses) != 3:
            raise ValueError('Three named puck slide addresses required')
        for address in addresses:
            _integer(address, label, high=size - 1)
        if len(set(addresses)) != 3:
            raise ValueError('Duplicate puck slide address')
    if set(puck_qpos_adrs) & set(range(base, base + 7)):
        raise ValueError('Puck/base qpos bindings overlap')
    qw, qx, qy, qz = map(float, qpos[base + 3:base + 7])
    if not math.isclose(qw*qw + qx*qx + qy*qy + qz*qz, 1., rel_tol=0., abs_tol=1e-6):
        raise ValueError('Unit base quaternion required; no normalization substitute')
    yaw = math.atan2(2*(qw*qz + qx*qy), 1 - 2*(qy*qy + qz*qz))
    puck = [float(qpos[a]) for a in puck_qpos_adrs]
    puck[2] += .062
    return {'time_s': _number(float(data.time), 'current qpos time', nonnegative=True),
            'rover_pose': [float(qpos[base]), float(qpos[base+1]), yaw],
            'puck_xyz': puck, 'puck_velocity_xy': [float(qvel[a]) for a in puck_dof_adrs[:2]]}


def native_state(data, *, base_qpos_adr, puck_qpos_adrs, puck_dof_adrs, goal_xy):
    """Read authored task qpos/qvel only, never xpos/geom_xpos caches.

    The fixed-model constructor must verify these named bindings and the puck
    body's fixed [0,0,.062] transform. This helper does not certify a model.
    """
    return _world({**_native_values(data, base_qpos_adr=base_qpos_adr,
        puck_qpos_adrs=puck_qpos_adrs, puck_dof_adrs=puck_dof_adrs),
        'goal_xy': _pair(goal_xy, 'goal')})


def _geometry_map(ownership):
    if type(ownership) is not dict or type(ownership.get('geometries')) is not list:
        raise ValueError('ContactProbe named ownership required')
    entries = ownership['geometries']
    if len(entries) != len(WORLD_GEOMS | ROBOT_GEOMS):
        raise ValueError('Fixed puck geometry inventory required')
    result = {}
    for entry in entries:
        _fields(entry, ('geom_id', 'name', 'body_id', 'body_name', 'owner'), 'named geometry')
        gid = _integer(entry['geom_id'], 'geometry ID', high=len(entries)-1)
        name = entry['name']
        if gid in result or type(name) is not str or name not in WORLD_GEOMS | ROBOT_GEOMS:
            raise ValueError('Unknown/duplicate geometry identity')
        if entry['owner'] != ('robot' if name in ROBOT_GEOMS else 'world'):
            raise ValueError('Contact ownership disagrees with pinned geometry')
        result[gid] = name
    if len(set(result.values())) != len(entries):
        raise ValueError('Duplicate geometry name')
    return result


def _pairs(pairs, names, summary):
    if type(pairs) is not list or len(pairs) > 128:
        raise ValueError('Bounded contact pair list required')
    for pair in pairs:
        _fields(pair, ('geom_ids', 'geom_names', 'distance_m', 'allowed_ground_support',
                       'classification', 'rejects_fit'), 'ContactProbe pair')
        ids = pair['geom_ids']
        if type(ids) is not list or len(ids) != 2 or any(type(i) is not int or i not in names for i in ids) or ids[0] == ids[1]:
            raise ValueError('Two distinct known geometry IDs required')
        actual = [names[i] for i in ids]
        if pair['geom_names'] != actual:
            raise ValueError('Contact name/ID mismatch')
        distance = _number(pair['distance_m'], 'contact distance')
        incident = any(name in ROBOT_GEOMS for name in actual)
        support = 'floor' in actual and any(name in GROUND_SUPPORT for name in actual)
        classification = 'rover_ground_support' if support else 'unexpected_robot_contact' if incident else 'world_only'
        if (pair['allowed_ground_support'] is not support or pair['classification'] != classification
                or pair['rejects_fit'] is not (incident and not support)):
            raise ValueError('Raw ContactProbe classifications changed')
        if support:
            summary['rover_ground_support'] = True
        elif 'obstacle0' in actual and incident:
            summary['rover_puck_contact'] = True
            summary['rover_puck_max_penetration_m'] = max(summary['rover_puck_max_penetration_m'], -distance)
        elif incident:
            summary['other_robot_contact'] = True
        elif set(actual) == {'obstacle0', 'floor'}:
            summary['puck_floor_support'] = True
        elif 'obstacle0' in actual and any(n in {'wall_n', 'wall_s', 'wall_e', 'wall_w'} for n in actual):
            summary['puck_wall_contact'] = True


def classify_contacts(report, ownership, *, tick, time_s):
    """Validate ContactProbe coverage; retain intended push and floor separately.

    At tick n>0 the packet is interval n-1, ending at n*.02, whose last
    pre-integration contact cache is n*.02-.002. Initial forwarded contacts have
    their own explicit schema and are never relabelled as a preceding interval.
    """
    _integer(tick, 'sensor tick', high=600)
    _time(time_s, tick * .02)
    names = _geometry_map(ownership)
    summary = dict(tick=tick, time_s=float(time_s), source_start_time_s=max(0, tick-1)*.02,
                   contact_cache_time_s=0. if tick == 0 else (tick-1)*.02+.018,
                   initial_forwarded=tick == 0, rover_puck_contact=False, other_robot_contact=False,
                   rover_ground_support=False, puck_floor_support=False, puck_wall_contact=False,
                   rover_puck_max_penetration_m=0., failure=None)
    if tick == 0:
        _fields(report, ('kind', 'time_s', 'pairs'), 'initial contact cache')
        if report['kind'] != 'initial_forwarded':
            raise ValueError('Explicit initial forwarded contact cache required')
        _time(report['time_s'], 0.)
        _pairs(report['pairs'], names, summary)
    else:
        _fields(report, ('tick', 'start_time_s', 'callback_count', 'stages', 'end', 'contact',
                         'coverage_passed', 'coverage_errors'), 'ContactProbe interval')
        if (type(report['tick']) is not int or report['tick'] != tick-1 or
                type(report['callback_count']) is not int or report['callback_count'] != 10 or
                report['coverage_passed'] is not True or report['coverage_errors'] != [] or
                type(report['stages']) is not list or len(report['stages']) != 10):
            raise ValueError('Incomplete/stale ContactProbe interval')
        _time(report['start_time_s'], summary['source_start_time_s'])
        control = None
        rejects_fit = False
        for index, stage in enumerate(report['stages']):
            _fields(stage, ('stage', 'time_s', 'control', 'pairs'), 'contact stage')
            if type(stage['stage']) is not int or stage['stage'] != index:
                raise ValueError('Missing/reordered contact stage')
            _time(stage['time_s'], (tick-1)*.02 + index*.002)
            values = _pair(stage['control'], 'actual wheel control')
            if any(abs(v) > 2 for v in values) or control is not None and control != values:
                raise ValueError('Changing/out-of-range contact-stage control')
            control = values
            _pairs(stage['pairs'], names, summary)
            rejects_fit |= any(p['rejects_fit'] for p in stage['pairs'])
        end = report['end']
        _fields(end, ('data_time_s', 'contact_cache_time_s', 'pairs'), 'end contact cache')
        _time(end['data_time_s'], time_s)
        _time(end['contact_cache_time_s'], summary['contact_cache_time_s'])
        if end['pairs'] != report['stages'][-1]['pairs'] or report['contact'] is not rejects_fit:
            raise ValueError('End cache or original calibration contact flag changed')
    summary['failure'] = _contact_failure(summary)
    return summary


def _contact_failure(contact):
    if contact['other_robot_contact']:
        return 'unexpected_robot_contact'
    if contact['puck_wall_contact']:
        return 'puck_wall_contact'
    if contact['rover_puck_max_penetration_m'] > .02:
        return 'puck_penetration'
    return None


def _contact(contact, time_s):
    _fields(contact, CONTACT_FIELDS, 'puck contact summary')
    tick = _integer(contact['tick'], 'contact tick', high=600)
    _time(time_s, tick*.02)
    _time(contact['time_s'], time_s)
    _time(contact['source_start_time_s'], max(0, tick-1)*.02)
    _time(contact['contact_cache_time_s'], 0. if tick == 0 else (tick-1)*.02+.018)
    for key in CONTACT_FIELDS[4:10]:
        if type(contact[key]) is not bool:
            raise ValueError('Boolean contact classification required')
    if contact['initial_forwarded'] != (tick == 0):
        raise ValueError('Initial contact provenance mismatch')
    penetration = _number(contact['rover_puck_max_penetration_m'], 'penetration', nonnegative=True)
    if penetration and not contact['rover_puck_contact'] or contact['failure'] != _contact_failure(contact):
        raise ValueError('Inconsistent contact summary')
    return contact


def _world_failure(world):
    if any(abs(v) > 5 for v in world['rover_pose'][:2] + world['puck_xyz'][:2]):
        return 'out_of_bounds'
    if abs(world['puck_xyz'][2] - .062) > .02:
        return 'puck_height'
    if math.hypot(*world['puck_velocity_xy']) > 2:
        return 'puck_speed'
    return None


def project(world, contact):
    """Return float32[8]; geometry is virtual, not a camera/retina feature."""
    import numpy as np
    _world(world)
    _contact(contact, world['time_s'])
    if _world_failure(world) or contact['failure']:
        raise ValueError('Failed puck state cannot produce a controller input')
    x, y, yaw = world['rover_pose']
    c, s = math.cos(yaw), math.sin(yaw)
    def rotate(dx, dy):
        return [c*dx+s*dy, -s*dx+c*dy]
    values = [v/14 for point in (world['puck_xyz'], world['goal_xy'])
              for v in rotate(point[0]-x, point[1]-y)]
    values += [v/2 for v in rotate(*world['puck_velocity_xy'])]
    values += [float(contact['rover_puck_contact']), float(contact['other_robot_contact'])]
    if any(not math.isfinite(v) or abs(v) > 1 for v in values):
        raise ValueError('Feature outside declared range; no clipping')
    return np.asarray(values, dtype=np.float32)


def initialize(world, episode_id):
    _world(world)
    _identifier(episode_id)
    _time(world['time_s'], 0.)
    if _world_failure(world):
        raise ValueError('Invalid initial puck world')
    return {'version': 1, 'protocol_sha256': PROTOCOL_SHA256, 'episode_id': episode_id, 'tick': 0,
            'initial_puck_xy': world['puck_xyz'][:2], 'previous_puck_xy': world['puck_xyz'][:2],
            'previous_rover_xy': world['rover_pose'][:2], 'goal_xy': world['goal_xy'][:],
            'previous_distance': math.dist(world['puck_xyz'][:2], world['goal_xy']),
            'had_contact': False, 'dwell_ticks': 0, 'stall_ticks': 0, 'reason': None}


def advance(state, world, contact, action):
    """Pure post-interval transition; caller must record then halt terminal output.

    Malformed/nonfinite input raises before mutation. Native finite task failures
    are retained as explicit terminal reasons. No reset or automatic recovery.
    """
    _fields(state, ('version', 'protocol_sha256', 'episode_id', 'tick', 'initial_puck_xy',
                    'previous_puck_xy', 'previous_rover_xy', 'goal_xy', 'previous_distance',
                    'had_contact', 'dwell_ticks', 'stall_ticks', 'reason'), 'puck state')
    _version(state['version'])
    _identifier(state['episode_id'])
    tick = _integer(state['tick'], 'completed puck ticks', high=599)
    if state['protocol_sha256'] != PROTOCOL_SHA256 or state['reason'] is not None:
        raise ValueError('Incompatible or terminal puck state')
    for key in ('initial_puck_xy', 'previous_puck_xy', 'previous_rover_xy', 'goal_xy'):
        if any(abs(v) > 5 for v in _pair(state[key], key)):
            raise ValueError('Retained nonterminal task position outside arena')
    _number(state['previous_distance'], 'previous goal distance', nonnegative=True)
    if state['previous_distance'] != math.dist(state['previous_puck_xy'], state['goal_xy']):
        raise ValueError('Retained goal distance disagrees with previous puck state')
    if type(state['had_contact']) is not bool:
        raise ValueError('Invalid prior contact bit')
    _integer(state['dwell_ticks'], 'dwell count', high=min(tick, 9))
    _integer(state['stall_ticks'], 'stall count', high=min(tick, 99))
    if tick == 0 and (state['had_contact'] or state['initial_puck_xy'] != state['previous_puck_xy']):
        raise ValueError('Initial state cannot contain prior contact or puck motion')
    if state['dwell_ticks'] and not state['had_contact']:
        raise ValueError('Goal dwell requires prior contact')
    _world(world)
    _contact(contact, world['time_s'])
    if contact['tick'] != tick+1 or world['goal_xy'] != state['goal_xy']:
        raise ValueError('Stale step or changed fixed puck goal')
    command = _pair(action, 'applied puck action')
    if any(abs(v) > .4 for v in command):
        raise ValueError('Action exceeds fixed task output bounds')
    result = copy.deepcopy(state)
    distance = math.dist(world['puck_xyz'][:2], world['goal_xy'])
    if not math.isfinite(distance):
        raise ValueError('Nonfinite derived puck distance/reward')
    reward = state['previous_distance'] - distance
    result['had_contact'] |= contact['rover_puck_contact']
    qualifies = (distance <= .2 and math.hypot(*world['puck_velocity_xy']) <= .03 and
                 result['had_contact'] and math.dist(world['puck_xyz'][:2], state['initial_puck_xy']) >= .5)
    result['dwell_ticks'] = state['dwell_ticks']+1 if qualifies else 0
    still = (math.dist(world['puck_xyz'][:2], state['previous_puck_xy']) < .002 and
             math.dist(world['rover_pose'][:2], state['previous_rover_xy']) < .002 and abs(command[0]) > .05)
    result['stall_ticks'] = state['stall_ticks']+1 if still else 0
    result['reason'] = _world_failure(world) or contact['failure']
    if result['reason'] is None:
        result['reason'] = ('stalled' if result['stall_ticks'] >= 100 else
                            'puck_goal' if result['dwell_ticks'] >= 10 else
                            'time_limit' if tick+1 == 600 else None)
    result.update(tick=tick+1, previous_puck_xy=world['puck_xyz'][:2],
                  previous_rover_xy=world['rover_pose'][:2], previous_distance=distance)
    return result, reward


def demonstrate(world, mode):
    """One privileged teacher transition; callers own and retain explicit mode."""
    if type(mode) is not str or mode not in ('approach', 'push'):
        raise ValueError('Invalid explicit puck teacher mode')
    _world(world)
    if _world_failure(world):
        raise ValueError('Invalid puck state for demonstrator')
    px, py = world['puck_xyz'][:2]
    gx, gy = world['goal_xy']
    distance = math.hypot(gx-px, gy-py)
    if distance <= .2:
        return [0., 0.], mode
    dx, dy = (gx-px)/distance, (gy-py)/distance
    x, y, yaw = world['rover_pose']
    axial, lateral = (px-x)*dx+(py-y)*dy, abs(-(px-x)*dy+(py-y)*dx)
    ready = .35 <= axial <= .63 and lateral <= .06
    ax, ay = px-.55*dx-x, py-.55*dy-y
    if mode == 'push' and not ready:
        mode = 'approach'
    elif mode == 'approach' and ready and math.hypot(ax, ay) <= .08:
        mode = 'push'
    if mode == 'push':
        ax, ay = dx, dy
    error = math.remainder(math.atan2(ay, ax)-yaw, math.tau)
    velocity = .2 if mode == 'push' else .25
    if mode == 'approach':
        reverse_error = math.remainder(math.atan2(-ay, -ax)-yaw, math.tau)
        if abs(reverse_error) < abs(error):  # Exact ties retain forward approach.
            error, velocity = reverse_error, -.25
    heading = max(-.4, min(.4, error))
    if abs(error) > .12:
        return [0., heading], mode
    return [velocity, heading], mode


def _fixed_bindings(env, model):
    import mujoco as mj
    from .snapshots import _bindings
    bindings = _bindings(env, model)
    def joint(name):
        value = mj.mj_name2id(model, mj.mjtObj.mjOBJ_JOINT, name)
        if not 0 <= value < model.njnt:
            raise ValueError('Missing fixed joint: ' + name)
        return value
    base, puck = joint('base_free'), [joint(f'obstacle0_{axis}') for axis in 'xyz']
    if int(model.jnt_type[base]) != 0 or any(int(model.jnt_type[j]) != 2 for j in puck):
        raise ValueError('Fixed base free joint and three puck slides required')
    extra = {'base_qpos_adr': int(model.jnt_qposadr[base]), 'puck_joint_ids': puck,
             'puck_qpos_adrs': [int(model.jnt_qposadr[j]) for j in puck],
             'puck_dof_adrs': [int(model.jnt_dofadr[j]) for j in puck]}
    if extra != {'base_qpos_adr': 60, 'puck_joint_ids': [0, 1, 2],
                 'puck_qpos_adrs': [0, 1, 2], 'puck_dof_adrs': [0, 1, 2]}:
        raise ValueError('Named fixed-profile native addresses changed')
    return bindings, extra


def _admit_owner(env):
    import mujoco as mj
    import numpy as np
    settings = {'W': 128, 'H': 128, 'n_obstacles': 1, 'frame_skip': 10, 'k_nearest': 5,
                'arena': 7., 'max_steps': 600, 'texture_mode': 'checker', 'render_mode': None,
                '_action_scale': 2., '_t': 0, '_speed': 0., '_stall_steps': 0,
                'window': None, '_view_ctx': None, 'explore_binsize': .2}
    if any(type(getattr(env, key, None)) is not type(value) or getattr(env, key, object()) != value
           for key, value in settings.items()):
        raise ValueError('Fresh fixed checker owner settings required')
    if (mj.__version__ != '3.3.6' or mj.get_mjcb_control() is not None or
            env.data.time != 0. or env._view_scn.maxgeom != 10000 or
            (env.renderer.height, env.renderer.width) != (128, 128)):
        raise ValueError('Fresh owner without callback/view context/tick required')
    bindings, extra = _fixed_bindings(env, env.model)
    for key, value in bindings.items():
        if not np.array_equal(getattr(env, key, None), value):
            raise ValueError('Stale cached native binding: ' + key)
    for key, shape in [('_obstacle_xy', (1, 2)), ('_goal_xy', (2,)), ('_prev_xy', (2,)), ('_last_action', (2,))]:
        value = getattr(env, key)
        if not isinstance(value, np.ndarray) or value.dtype != np.float32 or value.shape != shape or not np.isfinite(value).all():
            raise ValueError('Invalid fixed environment array: ' + key)
    for value in (env.data.qvel, env.data.ctrl, env.data.qfrc_applied, env.data.xfrc_applied, env._last_action):
        if not np.isfinite(value).all() or np.any(value):
            raise ValueError('Fresh zero velocity/control/applied force required')
    _native_values(env.data, **{k: extra[k] for k in ('base_qpos_adr', 'puck_qpos_adrs', 'puck_dof_adrs')})
    # Pinned upstream reset samples within arena-1.5 (5.5); the authored task
    # still has its stricter ±5 goal domain, enforced only by native_state/_world.
    if np.any(np.abs(env._goal_xy) > env.arena - 1.5):
        raise ValueError('Goal outside pinned constructor reset domain')
    if (not np.array_equal(env._obstacle_xy[0], env.data.qpos[extra['puck_qpos_adrs'][:2]].astype(np.float32)) or
            not np.array_equal(env._prev_xy, env.data.qpos[extra['base_qpos_adr']:extra['base_qpos_adr']+2].astype(np.float32)) or
            not np.array_equal(env._goal_xy, env.model.site_pos[env.goal_site_id, :2].astype(np.float32))):
        raise ValueError('Current reset qpos differs from cached environment positions')
    return bindings, extra


def _validate_compiled(old, new):
    """Reviewable fixed delta, including collision bounds/inertia; no native step."""
    import mujoco as mj
    import numpy as np
    dimensions = {'nq': 71, 'nv': 70, 'nu': 2, 'nbody': 26, 'njnt': 65,
                  'ngeom': 32, 'ncam': 2, 'nsite': 1, 'na': 0}
    if any(getattr(model, key) != value for model in (old, new) for key, value in dimensions.items()):
        raise ValueError('Fixed native dimensions changed')
    for model in (old, new):
        if (model.opt.timestep != .002 or int(model.opt.integrator) != 0 or int(model.opt.disableflags) != 0
                or not np.array_equal(model.opt.gravity, [0., 0., -9.81])):
            raise ValueError('Fixed Euler/contact/actuation pipeline changed')
    for kind, count in [('BODY', 26), ('JOINT', 65), ('GEOM', 32), ('CAMERA', 2), ('SITE', 1), ('ACTUATOR', 2)]:
        enum = getattr(mj.mjtObj, 'mjOBJ_' + kind)
        if [mj.mj_id2name(old, enum, i) for i in range(count)] != [mj.mj_id2name(new, enum, i) for i in range(count)]:
            raise ValueError('Named native ordering changed: ' + kind)
    puck = mj.mj_name2id(new, mj.mjtObj.mjOBJ_GEOM, 'obstacle0')
    body = mj.mj_name2id(new, mj.mjtObj.mjOBJ_BODY, 'obstacle0_body')
    goal = mj.mj_name2id(new, mj.mjtObj.mjOBJ_SITE, 'goal_site')
    replacements = {
        'body_pos': {body: [0., 0., .062]}, 'body_mass': {body: .25},
        'body_inertia': {body: [.00420625, .00420625, .0078125]},
        'jnt_range': {0: [-5.5, 5.5], 1: [-5.5, 5.5], 2: [-.002, .002]},
        'geom_size': {puck: [.25, .06, 0.]}, 'geom_friction': {puck: [.25, .005, .0001]},
        'geom_priority': {puck: 1}, 'geom_condim': {puck: 3}, 'geom_solref': {puck: [.004, 1.]},
        'geom_solimp': {puck: [.95, .99, .001, .5, 2.]}, 'geom_rgba': {puck: [.9, .7, .1, 1.]},
        # The XML pins two cylinder dimensions; site size[2] keeps MuJoCo's
        # unused .005 default (XMLreference.html#body-site, pinned 3.3.6).
        'site_type': {goal: 5}, 'site_size': {goal: [.45, .001, .005]}, 'site_pos': {goal: [0., 0., .001]}}
    unchanged = ('body_parentid', 'body_quat', 'body_ipos', 'body_iquat', 'jnt_type', 'jnt_bodyid',
        'jnt_axis', 'jnt_pos', 'jnt_limited', 'jnt_qposadr', 'jnt_dofadr', 'geom_type', 'geom_bodyid',
        'geom_pos', 'geom_quat', 'geom_contype', 'geom_conaffinity', 'site_quat', 'cam_pos', 'cam_quat',
        'cam_fovy', 'actuator_trnid', 'actuator_trntype', 'actuator_gear', 'actuator_ctrlrange',
        'actuator_ctrllimited', 'qpos0')
    for key in (*unchanged, *replacements):
        expected, actual = getattr(old, key).copy(), getattr(new, key)
        for index, value in replacements.get(key, {}).items(): expected[index] = value
        if expected.shape != actual.shape or expected.dtype != actual.dtype or not np.isfinite(actual).all() or not np.array_equal(expected, actual):
            raise ValueError('Compiled fixed-model delta differs: ' + key)
    for actual, expected in [(new.jnt_axis[:3], np.eye(3)), (new.jnt_limited[:3], [1, 1, 1]),
                             (new.actuator_gear, [[3., 0, 0, 0, 0, 0]]*2),
                             (new.actuator_ctrlrange, [[-2., 2.]]*2), (new.actuator_ctrllimited, [1, 1]),
                             (new.geom_pos[puck], [0., 0., 0.]), (new.body_ipos[body], [0., 0., 0.]),
                             (new.geom_aabb[puck], [0., 0., 0., .25, .25, .06])]:
        if not np.array_equal(actual, expected):
            raise ValueError('Fixed transform, collision extent or actuator contract changed')
    if (int(new.geom_type[puck]) != 5 or int(new.geom_bodyid[puck]) != body or
            not math.isclose(float(new.geom_rbound[puck]), math.hypot(.25, .06), rel_tol=0., abs_tol=1e-12)):
        raise ValueError('Compiled puck cylinder ownership/bounds changed')
    if [mj.mj_id2name(new, mj.mjtObj.mjOBJ_ACTUATOR, i) for i in range(2)] != ['left_motor', 'right_motor']:
        raise ValueError('Only the original ordered wheel actuators are allowed')
    if not np.array_equal(new.actuator_trnid[:, 0], [61, 62]):
        raise ValueError('Wheel actuator joint bindings changed')


def install_fixed_model(env, repo_root):
    """Stage once before any Engine exists; commit before retiring old renderer.

    A post-commit old-renderer close error is terminal: the caller owns and must
    close the newly committed renderer. It must not continue with a partial task.
    """
    import mujoco as mj
    import numpy as np
    from .profiles import configure_world
    from .snapshots import _model_digest
    if hasattr(env, '_puck_profile_identity'):
        raise ValueError('Fixed puck model is already installed')
    _admit_owner(env)
    xml = derive_xml(repo_root)
    model = mj.MjModel.from_xml_string(xml.decode('utf-8'))
    _validate_compiled(env.model, model)
    data = mj.MjData(model)
    bindings, extra = _fixed_bindings(env, model)
    staged = copy.copy(env)
    staged.model, staged.data = model, data
    vars(staged).update(bindings)
    configure_world(staged)  # Existing inactive-obstacle parking, on staged resources only.
    raw = model.__getstate__()
    if type(raw) is not bytes or len(raw) > 8 * 1024**2:
        raise ValueError('Compiled native model exceeds 8 MiB bound')
    identity = {'version': 1, 'scenario': SCENARIO, 'protocol_sha256': PROTOCOL_SHA256,
                'derived_xml_sha256': hashlib.sha256(xml).hexdigest(),
                'model_sha256': _model_digest(model), 'compiled_native_sha256': hashlib.sha256(raw).hexdigest()}
    renderer = None
    try:
        renderer = mj.Renderer(model, height=128, width=128)
        scene = mj.MjvScene(model, maxgeom=10000)
        updates = {**bindings, 'model': model, 'data': data, 'renderer': renderer, '_view_scn': scene,
                   '_puck_profile_identity': identity, '_puck_bindings': extra,
                   '_obstacle_xy': data.qpos[extra['puck_qpos_adrs'][:2]].astype(np.float32).reshape(1, 2),
                   '_goal_xy': model.site_pos[bindings['goal_site_id'], :2].astype(np.float32),
                   '_prev_xy': data.qpos[60:62].astype(np.float32), '_last_action': np.zeros(2, np.float32),
                   'visited': set(), 'path_to_draw': None, 'target_to_draw': None}
        vars(staged).update(updates)
        _admit_owner(staged)
    except BaseException:
        if renderer is not None: renderer.close()
        raise
    old_renderer = env.renderer
    vars(env).update(updates)
    old_renderer.close()
    return copy.deepcopy(identity)


def authored_reset(env, repo_root, seed, split, episode_id):
    """Apply one explicit time-zero layout after upstream reset has relocked XY.

    Stage new data; restore old mutable model arrays if mj_forward/validation
    fails. Never call env.step, reset, render or change RNG inside this adapter.
    """
    import mujoco as mj
    import numpy as np
    from .snapshots import ASTAR_CACHE, _model_digest
    row = layout(repo_root, seed, split)
    _identifier(episode_id)
    _, extra = _admit_owner(env)
    identity = getattr(env, '_puck_profile_identity', {})
    if (identity.get('protocol_sha256') != PROTOCOL_SHA256 or identity.get('model_sha256') != _model_digest(env.model)
            or getattr(env, '_puck_bindings', None) != extra or hasattr(env, '_puck_reset_seed')):
        raise ValueError('Matching installed puck model and first reset required')
    if (not np.array_equal(env.model.jnt_range[3:60], np.tile([-1e-6, 1e-6], (57, 1))) or
            np.any(env.model.jnt_range[60:]) or not np.array_equal(env.model.jnt_range[2], [-.002, .002])):
        raise ValueError('Only upstream-reset puck XY lock ranges may differ')
    data = mj.MjData(env.model)
    x, y, yaw = row['rover_pose']
    data.qpos[60:67] = [x, y, .1, math.cos(yaw/2), 0., 0., math.sin(yaw/2)]
    data.qpos[extra['puck_qpos_adrs']] = [*row['puck_xy'], 0.]
    data.qvel[:] = data.ctrl[:] = data.qfrc_applied[:] = 0.
    data.xfrc_applied[:] = 0.
    before = {key: getattr(env.model, key).copy() for key in ('jnt_range', 'geom_rgba', 'site_pos')}
    try:
        env.model.jnt_range[extra['puck_joint_ids']] = [[-5.5, 5.5], [-5.5, 5.5], [-.002, .002]]
        env.model.geom_rgba[env.obstacle_ids[0]] = [.9, .7, .1, 1.]
        env.model.site_pos[env.goal_site_id] = [*row['goal_xy'], .001]
        mj.mj_forward(env.model, data)
        world = native_state(data, **{k: extra[k] for k in ('base_qpos_adr', 'puck_qpos_adrs', 'puck_dof_adrs')},
                             goal_xy=row['goal_xy'])
        state = initialize(world, episode_id)
        if data.time != 0. or np.any(data.ctrl) or np.any(data.qfrc_applied) or np.any(data.xfrc_applied):
            raise ValueError('Authored reset must retain zero controls/forces/time')
    except BaseException:
        for key, value in before.items(): getattr(env.model, key)[:] = value
        raise
    vars(env).update(data=data, _obstacle_xy=np.asarray([row['puck_xy']], np.float32),
                     _goal_xy=np.asarray(row['goal_xy'], np.float32), _prev_xy=np.asarray([x, y], np.float32),
                     _last_action=np.zeros(2, np.float32), _speed=0., _t=0, _stall_steps=0,
                     visited={(math.floor(x/.2), math.floor(y/.2))}, path_to_draw=None, target_to_draw=None,
                     _puck_reset_seed=seed)
    if hasattr(env, 'planner'):
        for name in ASTAR_CACHE: setattr(env.planner, name, None)
    return state
