"""Validated boundary edits for the pinned upstream world; never advance physics."""

import importlib
import math
from numbers import Real


# ponytail: fixed bounds for the pinned chassis/wheels/caster and 0.05 m walls;
# derive validated bounds before supporting a different body or world model.
ROVER_RADIUS = .3
WALL_INSET = .05


def _xy(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError('xy must contain exactly two finite numbers')
    if any(isinstance(v, bool) or not isinstance(v, Real) for v in value):
        raise ValueError('xy must contain exactly two finite numbers')
    try:
        result = [float(v) for v in value]
    except OverflowError as error:
        raise ValueError('xy must contain exactly two finite numbers') from error
    if not all(math.isfinite(v) for v in result):
        raise ValueError('xy must contain exactly two finite numbers')
    return result


def apply_intervention(env, intervention: dict, teacher=None, *, dry_run=False) -> dict:
    """Return JSON old/new details, or raise ValueError before changing any state."""
    if not isinstance(intervention, dict):
        raise ValueError('Intervention must be an object')
    kind = intervention.get('kind')
    if kind not in ('move_obstacle', 'move_goal'):
        raise ValueError('Unsupported intervention kind')
    keys = {'kind', 'xy', 'index'} if kind == 'move_obstacle' else {'kind', 'xy'}
    if set(intervention) != keys:
        raise ValueError(f'{kind} requires exactly {sorted(keys)}')
    requested = _xy(intervention['xy'])
    index = intervention.get('index')
    if kind == 'move_obstacle' and (type(index) is not int or not 0 <= index < env.n_obstacles):
        raise ValueError('Obstacle index is out of range or is not an integer')

    model, data = env.model, env.data
    arena = float(env.arena)
    goal_radius = float(model.site_size[env.goal_site_id, 0])
    radii = [float(model.geom_size[gid, 0]) for gid in env.obstacle_ids]
    if not all(math.isfinite(v) and v > 0 for v in [arena, goal_radius, *radii]):
        raise ValueError('World geometry has invalid bounds')
    if any(int(model.geom_type[gid]) != 5 for gid in env.obstacle_ids):
        raise ValueError('Only the pinned cylinder obstacles are supported')
    radius = radii[index] if kind == 'move_obstacle' else goal_radius
    if max(map(abs, requested)) + radius >= arena - WALL_INSET:
        raise ValueError('Placement is outside the arena clearance')
    # Match the upstream float32 map/cue exactly to the physical coordinates.
    target = env._obstacle_xy[index].copy() if kind == 'move_obstacle' else env._goal_xy.copy()
    target[:] = requested
    xy = _xy(list(map(float, target)))
    if max(map(abs, xy)) + radius >= arena - WALL_INSET:
        raise ValueError('Placement is outside the arena clearance')
    base_address = int(model.jnt_qposadr[model.joint('base_free').id])
    rover = _xy(list(map(float, data.qpos[base_address:base_address + 2])))
    obstacles = [_xy([float(data.qpos[x]), float(data.qpos[y])])
                 for x, y in zip(env._obstacle_x_qposadr, env._obstacle_y_qposadr)]
    goal = _xy(list(map(float, env._goal_xy)))
    if math.dist(xy, rover) <= radius + ROVER_RADIUS:
        raise ValueError('Placement intersects the rover clearance')
    for other, center in enumerate(obstacles):
        if kind == 'move_obstacle' and other == index:
            continue
        if math.dist(xy, center) <= radius + radii[other]:
            raise ValueError(f'Placement intersects obstacle {other}')
    if kind == 'move_obstacle' and math.dist(xy, goal) <= radius + goal_radius:
        raise ValueError('Placement intersects the goal marker')

    time = float(data.time)
    if not math.isfinite(time):
        raise ValueError('Simulation time is not finite')
    if kind == 'move_obstacle':
        joints = [env.obstacle_x_joint_ids[index], env.obstacle_y_joint_ids[index]]
        half_widths = [(float(model.jnt_range[j, 1]) - float(model.jnt_range[j, 0])) / 2 for j in joints]
        if not all(math.isfinite(w) and 0 < w <= .001 for w in half_widths):
            raise ValueError('Obstacle slide joints are not tightly locked')
    old = obstacles[index] if kind == 'move_obstacle' else goal
    event = {'kind': kind, 'old': {'xy': old}, 'new': {'xy': xy}, 'simulation_time': time}
    if kind == 'move_obstacle':
        event['index'] = index
    if dry_run:
        return event
    # Resolve the runtime dependency before mutation; missing MuJoCo cannot leave a partial edit.
    forward = importlib.import_module('mujoco').mj_forward
    if kind == 'move_obstacle':
        for joint, position, half_width in zip(joints, xy, half_widths):
            data.qpos[model.jnt_qposadr[joint]] = position
            data.qvel[model.jnt_dofadr[joint]] = 0
            model.jnt_range[joint, :] = [position - half_width, position + half_width]
        env._obstacle_xy[index, :] = xy
    else:
        env._goal_xy[:] = xy
        model.site_pos[env.goal_site_id, :2] = xy
    forward(model, data)
    invalidate_geometry(env, teacher)
    return event


def invalidate_geometry(env, teacher=None):
    """Existing edit semantics: invalidate caches/drawing, retaining control state."""
    for name in ('_cached_occ', '_cached_obstacles_hash', '_cached_clearance'):
        setattr(env.planner, name, None)
    env.path_to_draw = env.target_to_draw = None
    if teacher is not None:
        teacher._path = None
