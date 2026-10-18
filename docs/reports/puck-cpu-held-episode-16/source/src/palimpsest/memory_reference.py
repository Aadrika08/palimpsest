"""Three fixed headless development references; no memory guidance or training.

The original checkpoint reference has an always-available upstream bearing.
That input is derived from true pose/goal and is not equal information to the
visibility-limited sensor-only reference. Frozen memory is audit state only.
"""

import copy
import math

from . import memory, memory_task


REFERENCES = {
    'memory-reference-original-flynn': ('flynn', 'rgb-contact-upstream-goal-bearing'),
    'memory-reference-sensor-only': ('manual', 'visible-common-goal-bearing-contact'),
    'memory-reference-teacher': ('teacher', 'privileged-pose-goal-obstacle-map'),
}
PROTOCOL = {'version': 1, 'claim': 'fixed-headless-controller-references-development',
    'source': 'paused-empty-u-cpu-flynn-acquisition-boundary-300',
    'references': {name: {'controller': spec[0], 'inputs': spec[1]} for name, spec in REFERENCES.items()},
    'source_cursor': 299, 'memory': 'frozen-unused-audit-state',
    'maximum_continuation_intervals': 300,
    'sensor_only_velocity': .65, 'sensor_only_collision_velocity': 0.,
    'sensor_only_heading_bound': math.pi, 'teacher_geometry_edit': 'clear-existing-cache-and-path-only',
    'teacher_retained': ['PID', 'reverse-recovery', 'VFH-hysteresis'],
    'input_dimensions_action_conversion_checkpoint': 'unchanged',
    'held_out': False}
PROTOCOL_SHA256 = memory.sha256(PROTOCOL)


def validate_mode(scenario, controller, device='cpu'):
    if type(scenario) is not str or scenario not in REFERENCES or controller != REFERENCES[scenario][0] or device != 'cpu':
        raise ValueError('Reference requires its fixed controller and CPU mode')
    return REFERENCES[scenario]


def validate_memory(state):
    state = memory_task.validate_state(state)
    if (state['episode_id'] != 'episode-0' or state['cursor'] is None or state['cursor']['tick'] != 299
            or state['u'] != memory.artifact(method='empty-v1') or state['e'] != {'version': 1, 'episodes': []}
            or state['requests'] or state['active'] is not None):
        raise ValueError('Reference requires the frozen empty-guidance source memory')
    facts = state['m']['facts']
    if len(facts) != 2 or any(f['status'] != 'observed' or f['evidence'] is None
            or f['evidence']['episode_id'] != 'episode-0' or f['evidence']['tick'] > 299 for f in facts):
        raise ValueError('Reference requires both source facts backed by before observations')
    return state


def validate_source(snapshot, scenario, controller, device, replace_controller, u):
    validate_mode(scenario, controller, device)
    if u is not None:
        raise ValueError('Reference cannot replace U')
    state = snapshot['application']
    replay = state.get('scenario') == scenario
    if (type(state.get('episode')) is not int or state['episode'] != 0
            or type(state.get('total_tick')) is not int or type(state.get('episode_step')) is not int
            or state['episode_step'] != 300 or state.get('total_tick') != 300
            or state.get('phase') != 'paused' or state.get('episode_finished') is not False
            or state.get('session_exhausted') is not False or state.get('recording_failed') is not False
            or state.get('execution_mode') not in ('live', 'policy', 'actions')
            or not replay and state['execution_mode'] == 'actions'):
        raise ValueError('Reference requires its exact paused source boundary 300')
    if replay:
        if state.get('controller') != controller or replace_controller:
            raise ValueError('Reference replay must retain the same controller')
    elif (state.get('scenario') != 'memory-passages' or state.get('controller') != 'flynn'
            or replace_controller != (controller != 'flynn')
            or snapshot.get('identity', {}).get('policy', {}).get('device') != 'cpu'):
        raise ValueError('Reference requires the declared CPU FLYNN profile transaction')
    validate_memory(state.get('memory'))


def teacher_control_hash(teacher):
    """The existing captured control fields, excluding only the cleared path."""
    from .snapshots import _fields, state_digest, TEACHER_STATE, VFH_STATE
    return state_digest({'state': _fields(teacher, tuple(k for k in TEACHER_STATE if k != '_path')),
        'pid': _fields(teacher.pid_state, ('integral', 'last_error')),
        'planner': _fields(teacher.planner, VFH_STATE)})


def sensor_input(packet, collision):
    """Project just the visible common-goal bearing and contact; never a map."""
    if type(collision) is not bool:
        raise ValueError('Reference contact must be a boolean')
    goals = [p for p in packet['landmarks'] if p['id'] == packet['common_goal_id']]
    if len(goals) != 1:
        raise memory_task.CueUnavailable('Sensor-only reference common goal is not visible')
    angle = goals[0]['bearing_rad']
    if type(angle) not in (int, float) or not math.isfinite(angle) or abs(angle) > math.pi / 2:
        raise ValueError('Invalid visible common-goal bearing')
    bearing = [math.cos(angle), math.sin(angle)]
    return {'bearing': bearing, 'collision': collision}


def sensor_action(inputs):
    memory._fields(inputs, 'bearing collision')
    bearing = inputs['bearing']
    if (type(inputs['collision']) is not bool or type(bearing) is not list or len(bearing) != 2
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in bearing)
            or not math.isclose(sum(v*v for v in bearing), 1., rel_tol=0., abs_tol=1e-6)):
        raise ValueError('Invalid sensor-only reference input')
    return [0. if inputs['collision'] else .65,
            max(-math.pi, min(math.pi, math.atan2(bearing[1], bearing[0])))]


def preservation_hash(snapshot, replacement):
    """Exact profile transaction guard, with explicit controller-only exceptions."""
    from .snapshots import state_digest
    result = copy.deepcopy(snapshot)
    state = result['application']
    if state['schema_version'] == 3 and 'task_state' not in state:
        state.update(schema_version=4, task_state=None)
    for field in ('source_run_id', 'event_prefix', 'scenario', 'revision'):
        state.pop(field)
    if replacement:
        result.pop('policy')
        result.pop('teacher')
        for field in ('policy', 'teacher', 'torch'):
            result['identity'].pop(field, None)
        for field in ('torch_cpu', 'torch_cuda'):
            result['rng'].pop(field, None)
        for field in ('controller', 'controller_tensors', 'teacher_reset_identity', 'manual_action',
                      'pending_commands', 'receipts', 'original_commands'):
            state.pop(field)
    return state_digest(result)
