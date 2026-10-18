"""Frozen memory-v2 development candidate; geometry is evaluator/sensor-only.

No native feasibility is asserted. Public routes contain IDs and fixed authored
lengths, never private coordinates, closures, or observed pose.
"""
import copy
import importlib
import math

from . import memory, memory_world
from .interventions import ROVER_RADIUS, WALL_INSET, apply_intervention

SCENARIO = 'memory-decision-v2'
POSTS = [[0., y] for y in (0., -2., 2., -2.9, 2.9, -3.8, 3.8, -4.7, 4.7, -5.6, 5.6, -6.5, 6.5)]
PARKED_GATES = [[2.5, -1.], [2.5, 1.]]
CLOSED_GATES = [[0., -1.], [0., 1.]]
OTHER_CYLINDERS = [[4.2, -4.8], [4.2, 4.8], [5.4, -4.8], [5.4, 4.8], [6.4, 0.]]
START_POSE = [-2.5, 0., 0.]
DECISION_XY = [-1.8, 0.]
GOAL_XY = [2.5, 0.]
RETREAT_XY = [[-.8, 1.4], [-1.3, 1.65], [-2., 1.25], [-2.3, .65], [-2.3, .15], [-2.1, 0.]]
PROFILE = {'version': 2, 'id': SCENARIO, 'claim': 'unvalidated-development-candidate',
    'arena': 7., 'rover_radius': ROVER_RADIUS, 'obstacle_radius': .4, 'wall_inset': WALL_INSET,
    'obstacles': POSTS + PARKED_GATES + OTHER_CYLINDERS, 'closed_gates': CLOSED_GATES,
    'start_pose': START_POSE, 'decision_xy': DECISION_XY, 'goal_xy': GOAL_XY,
    'cue_xy': [-1.1, 0.], 'inspection_xy': [[-.8, -1.], [-.8, 1.]],
    'crossing_xy': [[0., -1.], [0., 1.]], 'exit_xy': [[1.2, -1.], [1.2, 1.]],
    'nonpreferred_detour_xy': [[.6, -1.35], [.6, 1.35]], 'north_retreat_xy': RETREAT_XY,
    'sensing': {'range_m': 4., 'half_fov_rad': math.pi / 2, 'passage_radius_m': .75, 'arrival_radius_m': .35},
    'budgets': {'attempts': 2, 'inspection_ticks': 150, 'waypoint_ticks': 300,
                'prefix_ticks': 1200, 'continuation_ticks': 900, 'total_ticks': 2100},
    'arm_schedule': {'event_offset': 1, 'decision_offset': 2},
    'preferred_side': 'south-unless-mirrored', 'tie_rule': 'cost-then-lexical-route-id',
    'prefix': 'decision-south-inspection-south-retreat-north-inspection-north-retreat-decision',
    'memory_protocol_sha256': memory.PROTOCOL_SHA256}
PROFILE_SHA256 = memory.sha256(PROFILE)


def _loop_profile(radius):
    profile = copy.deepcopy(PROFILE)
    cx = -.8-math.sqrt(2*radius-1)
    theta = math.asin((radius-1)/radius)
    south = []
    for index in range(1, 8):
        angle = theta-(theta+4*math.pi/3)*index/7
        south.append([round(cx+radius*math.cos(angle), 12),
                      round(-radius+radius*math.sin(angle), 12)])
    profile.update(waypoint_amendment='fixed-loop-v1', loop_radius_m=radius,
                   north_retreat_xy=[[x, -y] for x, y in south])
    return profile


_WAYPOINT_PROFILES = [_loop_profile(radius) for radius in (1.4, 1.3, 1.2)]
WAYPOINT_PROFILE_HASHES = tuple(memory.sha256(profile) for profile in _WAYPOINT_PROFILES)
def _travel_profile(offset):
    profile = copy.deepcopy(_WAYPOINT_PROFILES[0])
    profile.update(travel_amendment='fixed-detour-v1', detour_offset_m=offset,
                   nonpreferred_detour_xy=[[.6, -(1+offset)], [.6, 1+offset]])
    return profile


_TRAVEL_PROFILES = [_travel_profile(offset) for offset in (.25, .20, .15)]
TRAVEL_PROFILE_HASHES = tuple(memory.sha256(profile) for profile in _TRAVEL_PROFILES)
_PROFILES = {PROFILE_SHA256: PROFILE, **dict(zip(WAYPOINT_PROFILE_HASHES, _WAYPOINT_PROFILES)),
             **dict(zip(TRAVEL_PROFILE_HASHES, _TRAVEL_PROFILES))}


def registered_profile(profile_sha256=PROFILE_SHA256):
    if type(profile_sha256) is not str or profile_sha256 not in _PROFILES:
        raise ValueError('Unknown frozen memory-v2 waypoint profile')
    return copy.deepcopy(_PROFILES[profile_sha256])


def make_case(seed, regime, kind, mirrored=False, *, profile_sha256=PROFILE_SHA256):
    profile = registered_profile(profile_sha256)
    if type(seed) is not int or not 0 <= seed < 2**32 or regime not in memory.RELATIONS or kind not in ('change', 'null', 'no-event') or type(mirrored) is not bool:
        raise ValueError('Invalid development memory-v2 case')
    cid = f'memory-v2-{seed:08x}-{regime}-{kind}-{int(mirrored)}'
    cue = cid + '-cue'
    preferred = int(mirrored)
    subjects = [cid + ('-subject-a' if side == preferred else '-subject-z') for side in range(2)]
    facts = [{'id': cid + ('-fact-a' if side == preferred else '-fact-z'), 'subject_id': subject,
        'kind': 'passability', 'estimate': None, 'status': 'unknown', 'evidence': None,
        'associations': [{'cue_id': cue, 'relation': regime if side == preferred else memory.RELATIONS[1-memory.RELATIONS.index(regime)]}],
        'inspection_landmark_id': subject + '-inspection', 'revision': 0, 'origin': 'initial_unknown'}
        for side, subject in enumerate(subjects)]
    markers = {cid + '-decision': DECISION_XY.copy(), cid + '-goal': GOAL_XY.copy()}
    for side, subject in enumerate(subjects):
        sign = -1 if side == 0 else 1
        markers[subject + '-inspection'] = [-.8, float(sign)]
        markers[subject + '-crossing'] = [0., float(sign)]
        markers[subject + '-exit'] = [1.2, float(sign)]
        if side != preferred:
            markers[subject + '-detour'] = profile['nonpreferred_detour_xy'][side].copy()
        for index, (x, y) in enumerate(profile['north_retreat_xy']):
            markers[subject + f'-retreat-{index}'] = [x, sign * y]
    case = {'version': 2, 'claim': 'development-runtime-configuration', 'case_id': cid,
        'seed': seed, 'regime': regime, 'kind': kind, 'mirrored': mirrored, 'acquisition': True,
        'profile_sha256': profile_sha256, 'acquisition_protocol_sha256': profile_sha256,
        'subjects_by_side': subjects, 'facts': memory.seed_m(facts, [])['facts'], 'cue_id': cue,
        'common_goal_id': cid + '-goal', 'decision_landmark_id': cid + '-decision',
        'closure_subject_id': subjects[preferred] if kind == 'change' else None,
        'event_enabled': kind != 'no-event', 'start_pose': START_POSE.copy(),
        'goal_xy': GOAL_XY.copy(), 'cue_xy': PROFILE['cue_xy'].copy(), 'landmarks': markers}
    case['graph_sha256'] = memory.sha256(_public_graph(case))
    case['case_sha256'] = memory.sha256(case)
    return case


def validate_case(case):
    if type(case) is not dict or len(memory.canonical_bytes(case)) > 64 * 1024:
        raise ValueError('Invalid bounded memory-v2 case')
    try:
        expected = make_case(case['seed'], case['regime'], case['kind'], case['mirrored'],
                             profile_sha256=case['profile_sha256'])
    except KeyError as error:
        raise ValueError('Incomplete memory-v2 case') from error
    if memory.canonical_bytes(case) != memory.canonical_bytes(expected):
        raise ValueError('Memory-v2 case differs from frozen generator/profile')
    return copy.deepcopy(case)


def _public_graph(case):
    decision, goal = case['decision_landmark_id'], case['common_goal_id']
    routes, edges = [], []
    for side, subject in enumerate(case['subjects_by_side']):
        inspection = subject + '-inspection'
        waypoints = [inspection, subject + '-crossing']
        if subject + '-detour' in case['landmarks']:
            waypoints.append(subject + '-detour')
        waypoints += [subject + '-exit', goal]
        retreat = [subject + f'-retreat-{i}' for i in range(len(registered_profile(case['profile_sha256'])['north_retreat_xy']))] + [decision]
        cost = sum(math.dist(case['landmarks'][a], case['landmarks'][b]) for a, b in zip([decision] + waypoints, waypoints))
        route_id = case['case_id'] + ('-route-a' if side == int(case['mirrored']) else '-route-z')
        fact = next(f for f in case['facts'] if f['subject_id'] == subject)
        routes.append({'route_id': route_id, 'subject_id': subject, 'fact_id': fact['id'],
            'cost': cost, 'inspection_landmark_id': inspection, 'waypoint_ids': waypoints,
            'retreat_ids': retreat})
        for role, chain in (('crossing', [decision] + waypoints), ('retreat', [inspection] + retreat)):
            for index, (a, b) in enumerate(zip(chain, chain[1:])):
                edges.append({'id': route_id + f'-{role}-{index}', 'from': a, 'to': b,
                    'direction': 'forward', 'subject_id': subject, 'role': role,
                    'length_m': math.dist(case['landmarks'][a], case['landmarks'][b])})
    acquisition = [decision]
    for subject in case['subjects_by_side']:
        route = next(r for r in routes if r['subject_id'] == subject)
        acquisition += [route['inspection_landmark_id']] + route['retreat_ids']
    return {'version': 2, 'routes': sorted(routes, key=lambda r: r['route_id']),
        'acquisition_ids': acquisition, 'decision_landmark_id': decision, 'common_goal_id': goal,
        'edges': edges, 'landmark_ids': sorted(case['landmarks']), 'profile_sha256': case['profile_sha256']}


def public_graph(case):
    return _public_graph(validate_case(case))


def _segment_distance(point, start, end):
    dx, dy = end[0]-start[0], end[1]-start[1]
    length2 = dx*dx+dy*dy
    fraction = 0. if not length2 else max(0., min(1., ((point[0]-start[0])*dx+(point[1]-start[1])*dy)/length2))
    return math.dist(point, [start[0]+fraction*dx, start[1]+fraction*dy])


def geometry_check(case):
    case = validate_case(case)
    obstacles = PROFILE['obstacles']
    inflated, boundary = .4 + ROVER_RADIUS, 7.-WALL_INSET-ROVER_RADIUS
    placements = all(max(map(abs, xy))+.4 < 7.-WALL_INSET for xy in obstacles)
    placements &= all(math.dist(a, b) > .8 for i, a in enumerate(obstacles) for b in obstacles[:i])
    placements &= all(math.dist(p, o) > size+.4 for p, size in ((START_POSE[:2], ROVER_RADIUS), (GOAL_XY, .25)) for o in obstacles)
    opened = memory_world.passage_status([[*xy, .4] for xy in obstacles])
    closed = []
    for side in range(2):
        positions = copy.deepcopy(obstacles)
        positions[len(POSTS)+side] = CLOSED_GATES[side].copy()
        closed.append(memory_world.passage_status([[*xy, .4] for xy in positions]))
    # Inflated post disks overlap continuously from each aperture end to the
    # admissible body-center boundary, so a path cannot pass around either end.
    north = sorted(y for _, y in POSTS if y >= 2.)
    south = sorted(y for _, y in POSTS if y <= -2.)
    no_end = north[-1]+inflated >= boundary and south[0]-inflated <= -boundary
    no_end &= all(b-a < 2*inflated for ys in (north, south) for a, b in zip(ys, ys[1:]))
    graph = _public_graph(case)
    paths = [[START_POSE[:2]]+[case['landmarks'][i] for i in graph['acquisition_ids']]]
    for route in graph['routes']:
        paths += [[DECISION_XY]+[case['landmarks'][i] for i in route['waypoint_ids']],
                  [DECISION_XY, case['landmarks'][route['inspection_landmark_id']]]+[case['landmarks'][i] for i in route['retreat_ids']]]
    clear, visible = True, True
    for path in paths:
        heading = 0.
        for a, b in zip(path, path[1:]):
            direction = math.atan2(b[1]-a[1], b[0]-a[0])
            visible &= math.dist(a, b) <= 4. and abs(math.remainder(direction-heading, 2*math.pi)) <= math.pi/2 + 1e-12
            visible &= all(_segment_distance(o, a, b) > .4 for o in obstacles)
            clear &= all(_segment_distance(o, a, b) > inflated for o in obstacles)
            clear &= all(max(map(abs, p)) < boundary for p in (a, b))
            heading = direction
    checks = {'placement_guards': bool(placements), 'both_open_crossings': set(opened.values()) == {'open'},
        'closed_crossings_excluded': closed[0] == {'passage-a': 'blocked', 'passage-b': 'open'} and closed[1] == {'passage-a': 'open', 'passage-b': 'blocked'},
        'no_end_bypass': bool(no_end), 'authored_chains_clear': bool(clear),
        'authored_successors_forward_visible': bool(visible)}
    return {'valid': all(checks.values()), 'checks': checks, 'failures': [k for k, v in checks.items() if not v],
        'profile_sha256': case['profile_sha256'], 'case_sha256': case['case_sha256'],
        'claim': 'analytic-candidate-geometry-only', 'native_feasibility': 'unvalidated'}


def arrival_analysis(case, *, include_routes=False):
    """Finite evaluator-only survey; headings are not controller guarantees.

    Survey a .05 m lattice and 5-degree circle boundary in each arrival disk,
    excluding body-colliding poses. For each 5-degree absolute heading retain
    only poses where the departing landmark is a legitimate visible arrival.
    Count unavailable successors and retain bounded explicit counterexamples.
    """
    case = validate_case(case)
    obstacles = registered_profile(case['profile_sha256'])['obstacles']
    offsets = {(round(x*.05, 12), round(y*.05, 12))
               for x in range(-7, 8) for y in range(-7, 8)
               if x*x+y*y <= 49}
    offsets |= {(round(.35*math.cos(math.radians(angle)), 12),
                 round(.35*math.sin(math.radians(angle)), 12))
                for angle in range(0, 360, 5)}
    graph = _public_graph(case)
    chains = [graph['acquisition_ids']]
    if type(include_routes) is not bool:
        raise ValueError('Arrival survey scope must be boolean')
    if include_routes:
        for route in graph['routes']:
            chains.extend(([graph['decision_landmark_id']]+route['waypoint_ids'],
                           [route['inspection_landmark_id']]+route['retreat_ids']))
    pairs = list(dict.fromkeys(pair for chain in chains for pair in zip(chain,chain[1:])))
    transitions = []
    boundary = 7.-WALL_INSET-ROVER_RADIUS
    for aid, bid in pairs:
        a, b = case['landmarks'][aid], case['landmarks'][bid]
        row = {'from': aid, 'to': bid, 'tested_count': 0, 'visible_count': 0,
               'unsafe_count': 0, 'unsafe_examples': [], 'min_margin_degrees': None}
        for dx, dy in sorted(offsets):
            q = [a[0]+dx, a[1]+dy]
            if max(map(abs, q)) >= boundary or any(math.dist(q, o) <= .7 for o in obstacles):
                continue
            if any(_segment_distance(o, q, a) <= .4 for o in obstacles):
                continue
            next_range = math.dist(q, b)
            next_los = all(_segment_distance(o, q, b) > .4 for o in obstacles)
            for degrees in range(0, 360, 5):
                yaw = math.radians(degrees)
                old_angle = 0. if dx == dy == 0 else math.remainder(math.atan2(-dy, -dx)-yaw, 2*math.pi)
                if abs(old_angle) > math.pi/2:
                    continue
                angle = math.degrees(math.remainder(math.atan2(b[1]-q[1], b[0]-q[0])-yaw, 2*math.pi))
                margin = 90.-abs(angle)
                row['tested_count'] += 1
                row['min_margin_degrees'] = margin if row['min_margin_degrees'] is None else min(margin,row['min_margin_degrees'])
                if next_range <= 4. and margin >= 0 and next_los:
                    row['visible_count'] += 1
                else:
                    row['unsafe_count'] += 1
                    if len(row['unsafe_examples']) < 8:
                        row['unsafe_examples'].append({'pose': [*q, yaw], 'successor_bearing_degrees': angle,
                            'successor_range_m': next_range, 'line_of_sight': next_los})
        transitions.append(row)
    return {'profile_sha256': case['profile_sha256'], 'case_sha256': case['case_sha256'],
            'position_step_m': .05, 'heading_step_degrees': 5, 'arrival_radius_m': .35,
            'continuous_guarantee': False, 'native_feasibility': 'unvalidated',
            'heading_assumption': 'all sampled headings with a legitimate departing visible arrival',
            'unsafe_examples_per_transition_cap': 8, 'transitions': transitions}


def initial_state(case):
    case = validate_case(case)
    if not geometry_check(case)['valid']:
        raise ValueError('Mandatory memory-v2 geometry failed')
    return {'version': 2, 'case': case, 'profile_sha256': case['profile_sha256'],
        'cue_state': 0, 'event_tick': None, 'decision_tick': None,
        'armed_boundary_tick': None, 'acquired_state_sha256': None,
        'applied': False, 'gate_result': 'pending' if case['event_enabled'] else 'not_requested', 'last_tick': None}


def validate_state(state):
    memory._fields(state, 'version case profile_sha256 cue_state event_tick decision_tick armed_boundary_tick acquired_state_sha256 applied gate_result last_tick')
    case = validate_case(state['case'])
    if type(state['version']) is not int or state['version'] != 2 or state['profile_sha256'] != case['profile_sha256'] or type(state['applied']) is not bool or type(state['cue_state']) is not int or state['cue_state'] != int(state['applied']):
        raise ValueError('Invalid memory-v2 world identity/cue')
    for key in ('event_tick', 'decision_tick', 'armed_boundary_tick', 'last_tick'):
        if state[key] is not None:
            memory._int(state[key])
    if state['armed_boundary_tick'] is None:
        if any(state[key] is not None for key in ('event_tick','decision_tick','acquired_state_sha256')) or state['applied']:
            raise ValueError('Unarmed world contains a scheduled event')
    else:
        memory._digest(state['acquired_state_sha256'])
        base = state['armed_boundary_tick']
        if state['decision_tick'] != base+2 or state['event_tick'] != (base+1 if case['event_enabled'] else None):
            raise ValueError('Schedule differs from frozen acquired boundary')
        if state['applied'] != (state['event_tick'] is not None and state['last_tick'] is not None and state['last_tick'] >= state['event_tick']):
            raise ValueError('World applied state differs from schedule cursor')
    if state['gate_result'] not in ('pending','not_requested','closed','rejected'):
        raise ValueError('Invalid memory-v2 gate result')
    expected_gate = ('closed','rejected') if state['applied'] and case['closure_subject_id'] is not None else ('not_requested',) if not case['event_enabled'] or state['applied'] else ('pending',)
    if state['gate_result'] not in expected_gate:
        raise ValueError('Gate result contradicts event schedule')
    return copy.deepcopy(state)


def arm(state, boundary_tick, acquired_state_sha256):
    state = validate_state(state)
    memory._int(boundary_tick)
    memory._digest(acquired_state_sha256)
    if state['armed_boundary_tick'] is not None or state['last_tick'] != boundary_tick-1:
        raise ValueError('World arm requires its unarmed acquired snapshot boundary')
    state.update(armed_boundary_tick=boundary_tick, decision_tick=boundary_tick+2,
                 event_tick=boundary_tick+1 if state['case']['event_enabled'] else None,
                 acquired_state_sha256=acquired_state_sha256)
    return validate_state(state)


def configure(env, state):
    state = validate_state(state)
    if state['last_tick'] is not None or state['armed_boundary_tick'] is not None:
        raise ValueError('Configure requires a fresh unarmed memory-v2 world')
    memory_world._validate_env(env)
    forward = importlib.import_module('mujoco').mj_forward
    joints = []
    for index, xy in enumerate(PROFILE['obstacles']):
        for joint, coordinate in zip((env.obstacle_x_joint_ids[index], env.obstacle_y_joint_ids[index]), xy):
            width = (float(env.model.jnt_range[joint][1])-float(env.model.jnt_range[joint][0]))/2
            if not math.isfinite(width) or not 0 < width <= .001:
                raise ValueError('Obstacle joints are not tightly locked')
            joints.append((joint, coordinate, width))
    env.place_robot(*START_POSE, env.data.qpos.copy(), env.data.qvel.copy())
    for joint, coordinate, width in joints:
        env.data.qpos[env.model.jnt_qposadr[joint]] = coordinate
        env.data.qvel[env.model.jnt_dofadr[joint]] = 0.
        env.model.jnt_range[joint, :] = [coordinate-width, coordinate+width]
    env._obstacle_xy[:,:] = PROFILE['obstacles']
    env._goal_xy[:] = GOAL_XY
    env.model.site_pos[env.goal_site_id,:2] = GOAL_XY
    env.max_steps = PROFILE['budgets']['total_ticks']
    forward(env.model, env.data)
    env._prev_xy = env._base_xy().copy()
    env._speed, env._stall_steps = 0., 0
    env._last_action[:] = 0.
    env.path_to_draw = env.target_to_draw = None
    for name in ('_cached_occ','_cached_obstacles_hash','_cached_clearance'):
        setattr(env.planner, name, None)
    env._reset_exploration()
    return state


def advance_world(env, state, tick):
    state = validate_state(state)
    memory._int(tick)
    previous = state['last_tick']
    if tick == previous:
        return state, []
    if tick != (0 if previous is None else previous+1):
        raise ValueError('Memory-v2 world requires consecutive ticks')
    state['last_tick'] = tick
    events = []
    if not state['applied'] and state['event_tick'] == tick:
        state.update(applied=True, cue_state=1)
        events.append({'kind':'memory_cue_changed','tick':tick,'cue_id':state['case']['cue_id'],'before':0,'after':1})
        subject = state['case']['closure_subject_id']
        if subject is None:
            state['gate_result'] = 'not_requested'
        else:
            side = state['case']['subjects_by_side'].index(subject)
            try:
                edit = apply_intervention(env, {'kind':'move_obstacle','index':len(POSTS)+side,'xy':CLOSED_GATES[side]})
            except ValueError as error:
                state['gate_result'] = 'rejected'
                events.append({'kind':'memory_gate_rejected','tick':tick,'subject_id':subject,'reason':str(error)})
            else:
                state['gate_result'] = 'closed'
                events.append({'kind':'memory_gate_applied','tick':tick,'subject_id':subject,'intervention':edit})
    return validate_state(state), events


def sensing_inputs(env, state):
    state = validate_state(state)
    case = state['case']
    circles = memory_world._occluders(env)
    world = _symbolic_world(case,state['cue_state'],circles)
    pose = [*map(float, env._base_xy()),float(env._base_yaw())]
    return world, pose, circles


def audit_inputs(state, pose):
    """Pure audit reconstruction from frozen geometry and recorded schedule.

    The caller must independently admit the actual gate intervention events;
    a schedule alone is not evidence that native placement succeeded.
    """
    state = validate_state(state)
    pose = memory_world._numbers(pose,3)
    positions = copy.deepcopy(PROFILE['obstacles'])
    case = state['case']
    if state['gate_result'] == 'closed':
        side = case['subjects_by_side'].index(case['closure_subject_id'])
        positions[len(POSTS)+side] = CLOSED_GATES[side].copy()
    circles = [[*xy,.4] for xy in positions]
    return _symbolic_world(case,state['cue_state'],circles),pose,circles


def _symbolic_world(case,cue_state,circles):
    raw = memory_world.passage_status(circles)
    labels = {subject:raw[old] for subject,old in zip(case['subjects_by_side'],memory_world.SUBJECTS)}
    return {'cues':[{'id':case['cue_id'],'xy':case['cue_xy'].copy(),'state':cue_state}],
        'landmarks':[{'id':landmark,'xy':xy.copy()} for landmark,xy in sorted(case['landmarks'].items())],
        'passages':[{'subject_id':f['subject_id'],'inspection_landmark_id':f['inspection_landmark_id'],
                     'passability':labels[f['subject_id']]} for f in case['facts']],
        'common_goal_id':case['common_goal_id']}


def reconstruct_inputs(case, pose, tick, *, event_tick=None, gate_result='closed'):
    """Independent audit input reconstruction; no simulator allocation/state."""
    case = validate_case(case)
    pose = memory_world._numbers(pose,3)
    memory._int(tick)
    if event_tick is not None:
        memory._int(event_tick)
    if gate_result not in ('closed','not_requested','rejected','pending'):
        raise ValueError('Invalid audited gate result')
    applied = case['event_enabled'] and event_tick is not None and tick >= event_tick
    positions = copy.deepcopy(PROFILE['obstacles'])
    if applied and case['closure_subject_id'] is not None and gate_result == 'closed':
        side = case['subjects_by_side'].index(case['closure_subject_id'])
        positions[len(POSTS)+side] = CLOSED_GATES[side].copy()
    circles = [[*xy,.4] for xy in positions]
    return _symbolic_world(case,int(applied),circles),pose,circles
