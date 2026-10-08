"""Pure finite-domain layout minting for the prospective puck v3 study.

This source slice has no filesystem or runtime access.  The real reserved IDs
remain locked until a separately reviewed reservation/admission layer exists.
"""

from .task_mechanics import MAX_COUNTER, MAX_ITEMS


SCHEMA = 'puck-on-policy-layout-v1'
COLLECTION_SPLIT = 'on_policy_collection'
DEVELOPMENT_SPLIT = 'on_policy_development'
RESERVED_SCENE_IDS = (6110, 6111, 6112, 6113, 6120, 6121, 6122, 6123)
_ROW_FIELDS = {'version', 'kind', 'seed', 'split', 'slot', 'rover_pose',
               'puck_xy', 'goal_xy', 'initial_qvel'}

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
