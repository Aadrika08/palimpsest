"""Pure preparation for one frozen, near-planar native-contact puck profile.

No native compilation, Engine wiring or trained controller is implemented here.
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
PROTOCOL_SHA256 = '8a7f14ee69fe386fe1150b644e71737a5e39ab3c8c4987d7cdf61277796f3bac'
PROTOCOL_PATH = 'docs/plans/m6-puck-pushing-protocol.json'
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
    for row in load_protocol(repo_root)['layouts']:
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


def native_state(data, *, base_qpos_adr, puck_qpos_adrs, puck_dof_adrs, goal_xy):
    """Read post-integration qpos/qvel only, never xpos/geom_xpos caches.

    The later fixed-model constructor must verify these named bindings and the
    puck body's fixed [0,0,.062] transform. This helper does not certify a model.
    """
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
    return _world({'time_s': float(data.time), 'rover_pose': [float(qpos[base]), float(qpos[base+1]), yaw],
                   'puck_xyz': puck, 'puck_velocity_xy': [float(qvel[a]) for a in puck_dof_adrs[:2]],
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


def demonstrate(world):
    """Frozen, stateless privileged teacher; no learned capability claim."""
    _world(world)
    if _world_failure(world):
        raise ValueError('Invalid puck state for demonstrator')
    px, py = world['puck_xyz'][:2]
    gx, gy = world['goal_xy']
    distance = math.hypot(gx-px, gy-py)
    if distance <= .18:
        return [0., 0.]
    dx, dy = (gx-px)/distance, (gy-py)/distance
    x, y, yaw = world['rover_pose']
    ax, ay = px-.55*dx-x, py-.55*dy-y
    if math.hypot(ax, ay) <= .08:
        ax, ay = dx, dy
    error = math.remainder(math.atan2(ay, ax)-yaw, math.tau)
    heading = max(-.4, min(.4, error))
    if abs(error) > .12:
        return [0., heading]
    axial, lateral = (px-x)*dx+(py-y)*dy, abs(-(px-x)*dy+(py-y)*dx)
    return [.2 if .35 <= axial <= .63 and lateral <= .06 else .25, heading]
