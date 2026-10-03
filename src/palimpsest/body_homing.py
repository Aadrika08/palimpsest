"""One fitted development body with the unchanged encoder-only homing component."""
import copy
import math
from . import body_adaptation as adaptive, body_profile as body, task_profiles as task
from .snapshots import state_digest

SCENARIO = 'adaptive-encoder-homing'
REFERENCE = {
    'decoded_snapshot_sha256': '4165b908939a33822e5c3524de868da01614a17707210d70a7422cb2265d043d',
    'report_sha256': '231956442698655fc8f511018067a9515797b2baa7dd5e9f7d1a174374546121',
    'snapshot_sha256': 'af42213e0bc0440906371a53fe23902b02c692e806c64b609621fed2feb63ca4',
    'samples_sha256': '8dcc254855a32bf41870fa4fb8660f6e96e4fbb3411077f816802985b4d4284c',
    'fit_sha256': '4d738e670b89cad1ca5db18dbb64d4465cc8f22663503d3c663fc6a6000a4428',
    'session_sha256': '2086d435f0bd40a5b85997ede4f7b8666ac042ecda8e135e34fba5ee239ba77b',
}
PROTOCOL = {'version': 1, 'scenario': SCENARIO, 'seed': 1, 'application_schema': 7,
    'body_identity': adaptive.IDENTITY, 'body_protocol': adaptive.PROTOCOL,
    'encoder_component_protocol_sha256': task.PROTOCOL_SHA256,
    'encoder_associated_world_sha256': task.PROTOCOL['world_protocol_sha256'],
    'component_role': 'encoder-component-only; memory-world configuration not invoked',
    'actual_world': 'pinned body lane with explicit start/goal/gear overrides',
    'actual_home_evaluator_limit_m': .25, 'task_activation': 'accepted fresh fitted boundary only',
    'reset': 'clear fit, task and derivation; collect first fixed probe',
    'claim': 'one-body simulator development composition; no efficacy/generalization/hardware claim'}
IDENTITY = {'version': 1, 'profile_sha256': adaptive._sha(PROTOCOL)}


def initial_task(session):
    state = adaptive.validate_session(session)
    if state['phase'] != 'fitted':
        return None
    if state['episode_step'] or state['time_s'] or state['previous_angles_rad'] != [0., 0.]:
        raise ValueError('Homing requires a fresh accepted fitted boundary')
    return task.initialize('encoder-homing', f"episode-{state['episode']}", [0., 0.],
        {'radius_m': body.PROTOCOL['radius_m'], 'track_m': body.PROTOCOL['track_m'],
         'quantum_rad': task.PROTOCOL['encoder_quantum_rad']})


def context(*, derivation=None, packet=None):
    return {'identity': copy.deepcopy(IDENTITY), 'derivation': copy.deepcopy(derivation),
            'encoder_packet': copy.deepcopy(packet)}


def validate_components(application, *, model=None, data=None, env=None):
    """Pure component admission first; optional native cursor binding before mutation."""
    if (application.get('schema_version') != 7 or type(application.get('schema_version')) is not int or
            application.get('scenario') != SCENARIO or application.get('controller') != 'manual' or
            type(application.get('seed')) is not int or application.get('seed') != 1 or application.get('texture') != 'checker'):
        raise ValueError('Homing composition profile/schema differs')
    info = application.get('composition')
    if type(info) is not dict or set(info) != {'identity', 'derivation', 'encoder_packet'} or type(info['identity']) is not dict or type(info['identity'].get('version')) is not int or info['identity'] != IDENTITY:
        raise ValueError('Homing composition identity differs')
    if info['derivation'] is not None and info['derivation'] != derivation_provenance():
        raise ValueError('Historical homing derivation provenance differs')
    state = adaptive.validate_session(application['body_state'], episode=application['episode'],
                                      episode_step=application['episode_step'])
    active = state['phase'] in ('fitted', 'fitted_terminal')
    current = application.get('task_state')
    packet = info['encoder_packet']
    if not active:
        if current is not None or packet is not None:
            raise ValueError('Homing must remain inactive during probes')
    else:
        current = task.validate_state(current)
        step = application['episode_step']
        if (current['scenario'] != 'encoder-homing' or current['episode_id'] != f"episode-{state['episode']}" or
                current['last_tick'] != (step-1 if step else None)):
            raise ValueError('Homing task cursor differs from body application')
        if not step:
            if current != initial_task(state) or packet is not None:
                raise ValueError('Homing initial local origin differs')
        else:
            if (type(packet) is not dict or set(packet) != {'angles_rad', 'time_s', 'tick'} or
                    type(packet['tick']) is not int or packet['tick'] != step-1 or packet['angles_rad'] != current['odometry']['wheel_angles_rad'] or
                    type(packet['time_s']) not in (int, float) or not math.isclose(packet['time_s'],(step-1)*.02,abs_tol=1e-9,rel_tol=0.)):
                raise ValueError('Homing pre-control encoder packet differs')
            if any(abs(a-b) > 2. + 1e-9 for a,b in zip(state['previous_angles_rad'],packet['angles_rad'])):
                raise ValueError('Homing last encoder interval exceeds measured rate bound')
    if data is not None:
        if env._body_profile_identity != adaptive.IDENTITY:
            raise ValueError('Homing native body identity differs')
        adaptive.validate_native(state, model, data, env)
    return copy.deepcopy(application)


def validate_snapshot_application(application, env, model, data):
    if application.get('phase') != 'paused':
        raise ValueError('Homing native snapshot requires paused application')
    validate_components(application, model=model, data=data, env=env)
    if application['body_state']['phase'] == 'fitted_terminal' or (application['task_state'] or {}).get('phase') == 'complete':
        raise ValueError('Terminal homing cannot restore as paused')


def derivation_provenance():
    return {'kind': 'trusted-historical-fitted-boundary', 'reference': copy.deepcopy(REFERENCE),
            'composition_identity': copy.deepcopy(IDENTITY)}


def derive_snapshot(snapshot, *, snapshot_sha256, report, report_sha256):
    """Explicit pinned conversion; not a permissive snapshot compatibility path."""
    if snapshot_sha256 != REFERENCE['snapshot_sha256'] or report_sha256 != REFERENCE['report_sha256']:
        raise ValueError('Historical fitted input file pin differs')
    if state_digest(snapshot) != REFERENCE['decoded_snapshot_sha256']:
        raise ValueError('Historical fitted decoded state pin differs')
    source = snapshot['application']
    state = adaptive.validate_session(source['body_state'])
    if (report.get('status') != 'passed' or source['scenario'] != adaptive.SCENARIO or source['schema_version'] != 6 or
            source['controller'] != 'manual' or source['seed'] != 1 or source['phase'] != 'paused' or
            source['episode'] != 4 or source['total_tick'] != 480 or source['episode_step'] != 0 or
            source['pending_commands'] or source['manual_action'] != [0.,0.] or source['task_state'] is not None or
            state['phase'] != 'fitted' or adaptive._sha(state) != REFERENCE['session_sha256'] or
            state['samples_sha256'] != REFERENCE['samples_sha256'] or state['fit_sha256'] != REFERENCE['fit_sha256'] or
            snapshot['identity']['model_sha256'] != adaptive.IDENTITY['model_sha256'] or
            snapshot['identity'].get('body_profile') != adaptive.IDENTITY or
            report['snapshots']['fitted']['sha256'] != snapshot_sha256 or
            report['accepted_fit']['fit'] != state['fit']):
        raise ValueError('Historical fitted state/report admission differs')
    result = copy.deepcopy(snapshot)
    result['application'].update(scenario=SCENARIO, schema_version=7,
        composition=context(derivation=derivation_provenance()), task_state=initial_task(state))
    validate_components(result['application'])
    return result


def normalized_reference(snapshot):
    result = copy.deepcopy(snapshot)
    app = result['application']
    for key in ('source_run_id', 'event_prefix', 'execution_mode'):
        app.pop(key, None)
    return state_digest(result)


def provenance(env, world):
    return {'identity': copy.deepcopy(IDENTITY), 'protocol': copy.deepcopy(PROTOCOL),
            'parent_authoring_profile': copy.deepcopy(env._body_runtime_world_profile),
            'actual_body_world': copy.deepcopy(world), 'actual_model_sha256': adaptive.IDENTITY['model_sha256']}
