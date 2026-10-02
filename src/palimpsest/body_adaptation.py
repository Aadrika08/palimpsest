"""Bounded development session and a narrow bridge to the shared body collector.

Only measured controls, encoder increments and time enter fitting. Contact cache
coverage is supplied by the existing native probe; pure state validation cannot
prove physics or contact coverage. Inputs/outputs are copied JSON state.
"""
import copy
import hashlib
import json
import math

from . import body_profile as loaded
from .task_mechanics import (_fields, _integer, _number, _pair, fit_wheel_gains,
                             compensate_wheels)

SCENARIO = 'adaptive-wheel-calibration'
PROTOCOL = {
    'version': 1, 'scenario': SCENARIO, 'seed': 1,
    'claim': 'development measured calibration; no neural learning or physical qualification',
    'probe_actions': [[.2,0.], [.4,0.], [-.2,0.], [-.4,0.]],
    'trial_ticks': 120, 'settling_ticks': 20, 'samples_per_trial': 100, 'max_samples': 400,
    'start_pose': loaded.PROTOCOL['start_pose'], 'goal_xy': loaded.PROTOCOL['goal_xy'],
    'left_gear': loaded.PROTOCOL['left_gear'], 'right_gear': loaded.PROTOCOL['right_gear'],
    'radius_m': loaded.PROTOCOL['radius_m'], 'track_m': loaded.PROTOCOL['track_m'],
    'authoring_source_sha256': loaded.PROTOCOL['authoring_source_sha256'],
    'semantic_world_profile_sha256': loaded.PROTOCOL['semantic_world_profile_sha256'],
    'model_sha256': loaded.ARTIFACT['model_sha256'],
    'baseline_report_sha256': loaded.ARTIFACT['report_sha256'],
    'nominal_gains_rad_s_per_control': loaded.ARTIFACT['nominal_gains_rad_s_per_control'],
    'fit_bounds': loaded.ARTIFACT['fit_bounds'],
    'between_trial_gain_range_over_mean_max': .2,
    'max_compensation_ratio': 1.5, 'control_limit': 2.,
    'pipeline': loaded.PROTOCOL['pipeline'], 'max_episode_steps': 600, 'state_max_bytes':128*1024,
    'contact_scope':loaded.PROTOCOL['contact_scope'], 'contact_coverage':loaded.PROTOCOL['contact_coverage'],
    'next_command': 'calibration-next only paused after a complete trial; first three start next probe, fourth accepted trial starts one fresh fitted episode',
    'ordinary_reset': 'abort session, clear samples/fit, start first probe again',
    'application_schema_version':6, 'keyboard_nominal':{'velocity':.3,'heading':.2},
    'fitted_terminal': 'retain complete valid last interval and explicit flags; no further step, fit or calibration-next',
}
MAX_STATE_BYTES = PROTOCOL['state_max_bytes']


def _sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


IDENTITY = {'version':1, 'profile_sha256':_sha(PROTOCOL), 'model_sha256':PROTOCOL['model_sha256']}
_STATE_KEYS = ('identity','start_episode','episode','episode_step','trial_index','phase',
               'previous_angles_rad','time_s','samples','samples_sha256','fit','fit_sha256','rejection','terminal')
_SAMPLE_KEYS = ('trial','tick','control','increments_rad','dt_s','contact')


def initial_session(*, episode):
    episode = _integer(episode,'episode')
    samples = []
    return {'identity':copy.deepcopy(IDENTITY),'start_episode':episode,'episode':episode,
            'episode_step':0,'trial_index':0,'phase':'collecting','previous_angles_rad':[0.,0.],
            'time_s':0.,'samples':samples,'samples_sha256':_sha(samples),
            'fit':None,'fit_sha256':None,'rejection':None,'terminal':None}


def _fit(samples):
    def fit(part):
        return fit_wheel_gains([{k:s[k] for k in ('control','increments_rad','dt_s','contact')}
                                for s in part], **PROTOCOL['fit_bounds'])
    trials = [fit(samples[i*100:(i+1)*100]) for i in range(4)]
    pooled = fit(samples)
    agreement = []
    for wheel in range(2):
        gains = [t['gains_rad_s_per_control'][wheel] for t in trials]
        agreement.append((max(gains)-min(gains))/(sum(gains)/4))
    if any(v > PROTOCOL['between_trial_gain_range_over_mean_max'] for v in agreement):
        raise ValueError('Direction/amplitude gain agreement rejects calibration')
    # A fit is unusable if its correction cannot be represented within protocol.
    compensate_wheels([0.,0.],pooled,nominal_gains_rad_s_per_control=PROTOCOL['nominal_gains_rad_s_per_control'],
                      max_compensation_ratio=PROTOCOL['max_compensation_ratio'])
    return {'pooled':pooled,'per_trial':trials,'gain_range_over_mean':agreement}


def validate_session(state, *, episode=None, episode_step=None, angles=None, time_s=None):
    """Validate typed session/derived fit before any native destination mutation."""
    _fields(state,_STATE_KEYS,'calibration session')
    if type(state['identity']) is not dict or state['identity'] != IDENTITY or type(state['identity'].get('version')) is not int:
        raise ValueError('Calibration immutable identity differs')
    start = _integer(state['start_episode'],'session start episode')
    current = _integer(state['episode'],'episode')
    trial = _integer(state['trial_index'],'trial index',high=3)
    step = _integer(state['episode_step'],'episode step',high=PROTOCOL['max_episode_steps'])
    evaluation = current == start+4
    if (evaluation and trial!=3) or (not evaluation and current!=start+trial):
        raise ValueError('Calibration episode/trial relation differs')
    encoder = _pair(state['previous_angles_rad'],'raw encoder cursor')
    timestamp = _number(state['time_s'],'native time',nonnegative=True)
    if (not math.isclose(timestamp,step*.02,abs_tol=1e-9,rel_tol=0.) or
            any(abs(v)>step*.02*100.+1e-9 for v in encoder) or (step==0 and encoder!=[0.,0.])):
        raise ValueError('Calibration native time/cursor differs')
    if ((episode is not None and (type(episode) is not int or episode!=current)) or
        (episode_step is not None and (type(episode_step) is not int or episode_step!=step))):
        raise ValueError('Application calibration cursor differs')
    if angles is not None and _pair(angles,'native raw encoders')!=encoder:
        raise ValueError('Calibration raw encoder cursor differs from native data')
    if time_s is not None and _number(time_s,'native time',nonnegative=True)!=timestamp:
        raise ValueError('Calibration time differs from native data')
    expected_count = 400 if evaluation else trial*100+max(min(step,120)-20,0)
    samples = state['samples']
    if type(samples) is not list or len(samples)!=expected_count or len(samples)>400:
        raise ValueError('Calibration sample count/cursor differs')
    fixed_controls = [loaded.effective_control(action) for action in PROTOCOL['probe_actions']]
    for index,s in enumerate(samples):
        _fields(s,_SAMPLE_KEYS,'calibration sample')
        t = _integer(s['trial'],'sample trial',high=3)
        tick = _integer(s['tick'],'sample tick',low=20,high=119)
        if (t,tick)!=(index//100,index%100+20):
            raise ValueError('Calibration sample order differs')
        control = _pair(s['control'],'actual control')
        if control != fixed_controls[t]:
            raise ValueError('Calibration actual control differs from fixed probe')
        increments = _pair(s['increments_rad'],'raw encoder increment')
        dt = _number(s['dt_s'],'measured dt',positive=True)
        if not .02-1e-9<=dt<=.02+1e-9 or any(abs(v/dt)>100. for v in increments):
            raise ValueError('Calibration measured dt/rate outside protocol')
        if s['contact'] is not False:
            raise ValueError('Rejected contact sample in calibration state')
    if state['samples_sha256'] != _sha(samples):
        raise ValueError('Calibration sample digest differs')
    terminal = state['terminal']
    if terminal is not None:
        _fields(terminal,('terminated','truncated'),'fitted terminal outcome')
        if (not evaluation or step==0 or any(type(v) is not bool for v in terminal.values())
                or not any(terminal.values())):
            raise ValueError('Invalid fitted terminal outcome')
    if evaluation and step==600 and terminal is None:
        raise ValueError('Fitted episode limit requires explicit terminal flags')
    if evaluation:
        phase = 'fitted_terminal' if terminal is not None else 'fitted'
        fitted = _fit(samples)
    elif step < 120:
        phase = 'collecting'
    elif trial < 3:
        if step != 120:
            raise ValueError('Complete probe waits without additional physics')
        phase = 'trial_complete'
    else:
        if step != 120:
            raise ValueError('Accepted probe must await its prescribed fresh reset')
        try:
            fitted = _fit(samples)
        except ValueError as error:
            phase = 'rejected'
            if step != 120 or state['rejection'] != str(error)[:512]:
                raise ValueError('Rejected calibration reason/cursor differs')
        else:
            phase = 'fit_complete'
    if phase in ('fit_complete','fitted','fitted_terminal') and (_sha(state['fit'])!=_sha(fitted) or state['fit_sha256']!=_sha(fitted)):
        raise ValueError('Calibration fitted coefficients/digest differ from samples')
    if state['phase'] != phase:
        raise ValueError('Calibration phase differs from cursor/measurements')
    if phase not in ('fit_complete','fitted','fitted_terminal') and (state['fit'] is not None or state['fit_sha256'] is not None):
        raise ValueError('No fallback fit allowed before acceptance')
    if phase != 'rejected' and state['rejection'] is not None:
        raise ValueError('Unexpected calibration rejection')
    if len(json.dumps(state,allow_nan=False,separators=(',',':')).encode())>MAX_STATE_BYTES:
        raise ValueError('Calibration state exceeds byte bound')
    return copy.deepcopy(state)


def probe_action(state):
    state = validate_session(state)
    if state['phase']!='collecting':
        raise ValueError('Fixed probe requires collecting phase')
    return list(PROTOCOL['probe_actions'][state['trial_index']])


def plan_action(state, nominal_action):
    state = validate_session(state)
    if state['phase']!='fitted':
        raise ValueError('Compensation requires newly accepted calibration')
    nominal = _pair(nominal_action,'nominal manual action')
    control = loaded.effective_control(nominal)
    correction = compensate_wheels(control,state['fit']['pooled'],
        nominal_gains_rad_s_per_control=PROTOCOL['nominal_gains_rad_s_per_control'],
        max_compensation_ratio=PROTOCOL['max_compensation_ratio'])
    inverse = loaded.inverse_control(correction['control'])
    return {'nominal_action':nominal,'nominal_control':control,
            'applied_action':inverse['action'],'applied_control':inverse['control_float32'],
            'gain_ratio':correction['gain_ratio'],'rounding_delta':inverse['rounding_delta']}


def observe_interval(state, *, nominal_action, actual_control, before, after, dt_s, time_s,
                     contact, coverage_passed, terminated, truncated):
    """Consume one complete measured interval; rejects never mutate input state."""
    state = validate_session(state)
    if state['phase'] not in ('collecting','fitted') or state['episode_step']>=600:
        raise ValueError('Calibration interval outside active bounded phase')
    if type(terminated) is not bool or type(truncated) is not bool:
        raise ValueError('Explicit boolean outcome flags required')
    if contact is not False or coverage_passed is not True or (state['phase']=='collecting' and (terminated or truncated)):
        raise ValueError('Contact/coverage/early outcome rejects calibration interval')
    nominal = _pair(nominal_action,'nominal action')
    if state['phase']=='collecting':
        if nominal != PROTOCOL['probe_actions'][state['trial_index']]:
            raise ValueError('User action prohibited during fixed probe')
        expected_control = loaded.effective_control(nominal)
    else:
        expected_control = plan_action(state,nominal)['applied_control']
    control = _pair(actual_control,'actual control')
    if control != expected_control:
        raise ValueError('Actual controls differ from calibration plan')
    first,last = _pair(before,'raw encoders before'),_pair(after,'raw encoders after')
    if first != state['previous_angles_rad']:
        raise ValueError('Raw encoder interval is discontinuous')
    dt = _number(dt_s,'measured dt',positive=True)
    timestamp = _number(time_s,'native time',positive=True)
    increments = [b-a for a,b in zip(first,last)]
    if (not .02-1e-9<=dt<=.02+1e-9 or not math.isclose(timestamp-state['time_s'],dt,abs_tol=1e-9,rel_tol=0.) or
            any(not math.isfinite(v) or abs(v/dt)>100. for v in increments)):
        raise ValueError('Measured interval dt/time/encoder rate rejects calibration')
    step = state['episode_step']
    collecting = state['phase']=='collecting'
    if not collecting and (terminated or truncated):
        state.update(phase='fitted_terminal',terminal={'terminated':terminated,'truncated':truncated})
    if collecting and step>=20:
        state['samples'].append({'trial':state['trial_index'],'tick':step,'control':control,
                                'increments_rad':increments,'dt_s':dt,'contact':False})
        state['samples_sha256'] = _sha(state['samples'])
    state.update(episode_step=step+1,previous_angles_rad=last,time_s=timestamp)
    if collecting and step+1==120:
        if state['trial_index']<3:
            state['phase']='trial_complete'
        else:
            try:
                state['fit'] = _fit(state['samples'])
            except ValueError as error:
                state.update(phase='rejected',rejection=str(error)[:512])
            else:
                state.update(phase='fit_complete',fit_sha256=_sha(state['fit']))
    return validate_session(state)


def calibration_next(state, *, application_phase):
    """Prevalidate explicit prescribed reset; caller must verify fresh native data."""
    state = validate_session(state)
    if application_phase!='paused' or state['phase'] not in ('trial_complete','fit_complete') or state['episode_step']!=120:
        raise ValueError('calibration-next requires paused completed trial')
    accepted = state['phase']=='fit_complete'
    state.update(episode=state['episode']+1,episode_step=0,trial_index=state['trial_index']+(0 if accepted else 1),
                 phase='fitted' if accepted else 'collecting',previous_angles_rad=[0.,0.],time_s=0.)
    return validate_session(state)


def ordinary_reset(state, *, episode):
    validate_session(state)
    if type(episode) is not int or episode != state['episode']+1:
        raise ValueError('Ordinary reset requires the next episode')
    return initial_session(episode=episode)


def configure(env, *, episode, session=None):
    """Reuse the pinned physical authoring; never load historical weaker-wheel gains."""
    state = initial_session(episode=episode) if session is None else validate_session(session,episode=episode,episode_step=0)
    loaded.configure(env,f'episode-{episode}')
    env._body_profile_identity = copy.deepcopy(IDENTITY)
    validate_native(state,env.model,env.data,env)
    return state


def validate_native(state, model, data, env):
    angles = [float(data.qpos[int(model.jnt_qposadr[j])])
              for j in (env.left_hinge_id,env.right_hinge_id)]
    return validate_session(state,angles=angles,time_s=float(data.time))


def validate_snapshot_application(application, env, model, data):
    if (type(application) is not dict or type(application.get('schema_version')) is not int or
            application.get('schema_version')!=6 or application.get('phase')!='paused' or
            application.get('scenario')!=SCENARIO or application.get('controller')!='manual' or
            type(application.get('seed')) is not int or application.get('seed')!=PROTOCOL['seed'] or env._body_profile_identity!=IDENTITY):
        raise ValueError('Adaptive native snapshot requires its paused application/profile')
    state = validate_session(application.get('body_state'),episode=application.get('episode'),
                             episode_step=application.get('episode_step'))
    if state['phase']=='fitted_terminal':
        raise ValueError('Terminal fitted episode cannot restore as paused')
    validate_native(state,model,data,env)


def inspect(state):
    """Bounded display/event progress; the measurement buffer belongs only in snapshots."""
    # Engine already validates each committed transition. No fit recomputation for display.
    return copy.deepcopy({key:state[key] for key in
        ('identity','episode','episode_step','trial_index','phase','samples_sha256','fit_sha256','rejection','terminal')}) | {
        'sample_count':len(state['samples']), 'trial_ticks':120, 'total_trials':4, 'episode_limit':PROTOCOL['max_episode_steps'],
        'gains_rad_s_per_control':None if state['fit'] is None else list(state['fit']['pooled']['gains_rad_s_per_control'])}


def step(env, state, nominal_action, tick, *, action_override=None):
    """Measure a fixed probe or newly fitted command; effective replay maps only once."""
    state = validate_session(state,episode_step=tick)
    if state['phase']=='collecting':
        nominal = probe_action(state)
        control = loaded.effective_control(nominal)
        plan = {'nominal_action':nominal,'nominal_control':control,'applied_action':nominal,
                'applied_control':control,'gain_ratio':[1.,1.],'rounding_delta':[0.,0.]}
    else:
        import numpy as np
        plan = plan_action(state,np.asarray(nominal_action,dtype=np.float64).tolist())
    try:
        result,packet,arrays = loaded.measure_step(env,plan,tick,
            previous_angles_rad=state['previous_angles_rad'],time_s=state['time_s'],
            action_override=action_override,retain_outcome=True)
    except loaded.BodyFailure as error:
        error.packet.setdefault('outcome',None)  # Explicitly unknown if the native step did not return.
        raise
    _,_,terminated,truncated,_ = result
    try:
        advanced = observe_interval(state,nominal_action=plan['nominal_action'],
            actual_control=list(map(float,env.data.ctrl)),before=packet['encoder_before'],after=packet['encoder_after'],
            dt_s=packet['dt_s'],time_s=float(env.data.time),contact=packet['interval']['contact'],
            coverage_passed=packet['interval']['coverage_passed'],terminated=terminated,truncated=truncated)
    except ValueError as error:
        packet['outcome']={'terminated':terminated,'truncated':truncated}
        raise loaded.BodyFailure(str(error),packet) from error
    return result,advanced,packet,arrays
