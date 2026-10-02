"""Fixed R1 scenarios; editor metadata never becomes a student sensor."""

import importlib.util
from pathlib import Path


SCENARIOS = {
    'reproduction': ('Upstream reproduction', 'Pinned 20-obstacle paper configuration.', 20),
    'sparse-navigation': ('Sparse navigation', 'Five seeded obstacles and a validated free route; pretrained success is not guaranteed.', 5),
    'blocked-route': ('Blocked route', 'Move an existing obstacle during travel and measure the response.', 20),
    'target-relocation': ('Target relocation', 'Move the target while preserving its declared bearing cue.', 20),
    'vision-ablation': ('Vision ablation', 'Disable either eye or both; goal and contact cues remain available.', 20),
    'texture-variation': ('Texture variation', 'Compare upstream checker and realistic textures; an out-of-distribution test.', 20),
    'memory-passages': ('Memory passages (development)', 'Authored two-passage scene with declared symbolic sensing and evidence-based reinspection; transfer is not yet qualified.', 20),
}
TEXTURES = ('checker', 'realistic')
CONTROLLERS = ('manual', 'teacher', 'flynn')
POPULATIONS = ('visual_left', 'visual_right', 'descending')


def validate(scenario, texture, controller):
    if any(type(value) is not str for value in (scenario, texture, controller)) or scenario not in SCENARIOS or controller not in CONTROLLERS or texture not in TEXTURES:
        raise ValueError('Unknown scenario, controller or texture')
    if scenario != 'texture-variation' and texture != 'checker':
        raise ValueError('Realistic textures require the texture-variation scenario')
    if scenario == 'memory-passages' and controller == 'teacher':
        raise ValueError('Memory passages requires manual or FLYNN control through the declared task cue')
    label, description, count = SCENARIOS[scenario]
    profile = {'id': scenario, 'version': 1, 'label': label, 'description': description,
            'texture': texture, 'n_obstacles': count, 'width': 128, 'height': 128,
            'arena': 7., 'max_steps': 600, 'control_interval_seconds': .02,
            'observation_profile': 'two-rgb-eyes-contact-relative-goal-bearing-v1',
            'controller': controller, 'teacher_privileged': controller == 'teacher',
            'task': 'navigation', 'logging': 'lossless-inputs-actions-world-v1'}
    if scenario == 'memory-passages':
        from .memory_world import PROFILE_SHA256
        profile.update(task='memory-reinspection-development', world_protocol_sha256=PROFILE_SHA256,
                       observation_profile='two-rgb-eyes-contact-visible-landmark-bearing-v1')
    return profile


def list_profiles(root, assets):
    from .assets import verify_assets
    runtime = all(importlib.util.find_spec(name) is not None for name in ('numpy', 'mujoco', 'torch', 'gymnasium'))
    try:
        assets_ok = verify_assets(Path(root), Path(assets))['ok']
    except (OSError, ValueError):
        assets_ok = False
    controllers = []
    for name, label, description in (
        ('manual', 'Manual', 'Keyboard velocity and heading; no neural inference.'),
        ('teacher', 'Analytical teacher', 'Privileged geometry reference, not an equal-information policy.'),
        ('flynn', 'FLYNN', 'Pinned pretrained connectome; CPU continuation verified on the measured host. CUDA may diverge.')):
        available = runtime and (name != 'flynn' or assets_ok)
        controllers.append({'id': name, 'label': label, 'description': description,
                            'available': available, 'privileged': name == 'teacher',
                            'reason': None if available else 'Install simulation dependencies and verify required model assets.',
                            'license': 'CC BY-NC 4.0 graph/checkpoint' if name == 'flynn' else 'Upstream MIT code'})
    return {'scenarios': [{'id': key, 'label': value[0], 'description': value[1]} for key, value in SCENARIOS.items()],
            'controllers': controllers, 'textures': [{'id': name, 'label': name.title(),
                'description': 'Upstream texture variant'} for name in TEXTURES]}


def configure_world(env):
    """Upstream n_obstacles limits lists; unused XML placeholders still exist."""
    if env.n_obstacles == 20:
        return
    import mujoco
    for index in range(env.n_obstacles, 20):
        geom = env.model.geom(f'obstacle{index}').id
        env.model.geom_contype[geom] = env.model.geom_conaffinity[geom] = 0
        env.model.geom_rgba[geom, 3] = 0
        # qpos0 is the joint reference, so changing it alone does not translate a body.
        body = env.model.body(f'obstacle{index}_body').id
        env.model.body_pos[body, :2] = env.arena + 20 + index
    mujoco.mj_setConst(env.model, env.data)
    mujoco.mj_resetData(env.model, env.data)


def validate_world(env, require_route=False):
    """Validate evaluator geometry without changing the scene or policy input."""
    import math
    import numpy as np
    from .interventions import ROVER_RADIUS, WALL_INSET

    obstacles = env._obstacle_xy
    radii = np.array([env.model.geom_size[index, 0] for index in env.obstacle_ids])
    goal_radius = float(env.model.site_size[env.goal_site_id, 0])
    rover, goal = env._base_xy(), env._goal_xy
    if not all(np.isfinite(value).all() for value in (obstacles, radii, rover, goal)) or np.any(radii <= 0):
        raise ValueError('Invalid finite world geometry')
    centers = [*obstacles, rover, goal]
    sizes = [*radii, ROVER_RADIUS, goal_radius]
    for index, (center, radius) in enumerate(zip(centers, sizes)):
        if max(abs(center)) + radius >= env.arena - WALL_INSET:
            raise ValueError('Scenario geometry crosses arena boundary')
        if any(math.dist(center, previous) <= radius + sizes[j] for j, previous in enumerate(centers[:index])):
            raise ValueError('Scenario contains overlapping spawn geometry')
    if require_route:
        # Validation only: do not expose this evaluator route as a policy cue.
        planner = type(env.planner)(type(env.planner.spec)(env.arena, .2, ROVER_RADIUS + .2))
        path = planner.plan(rover, goal, obstacles, float(max(radii, default=0)), smooth_path=False)
        if not path:
            raise ValueError('Sparse scenario has no validated free route')
        points = [rover, *path, goal]
        for start, end in zip(points, points[1:]):
            vector = end - start
            length = float(vector @ vector)
            fractions = np.clip((obstacles - start) @ vector / length, 0, 1) if length else np.zeros(len(obstacles))
            distances = np.linalg.norm(obstacles - (start + fractions[:, None] * vector), axis=1)
            if np.any(distances <= radii + ROVER_RADIUS):
                raise ValueError('Sparse scenario route lacks body clearance')
    return {'geometry_valid': True, 'free_route_validated': bool(require_route)}
