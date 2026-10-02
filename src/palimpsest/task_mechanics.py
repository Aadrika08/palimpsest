"""Bounded, stdlib-only M6 mechanisms, with no simulator or engine access.

All calibration and experiment limits come from the caller. Returned values are
plain JSON data; failures raise ValueError subclasses before producing an action.
The structural caps below limit storage, not physical motion or safety.
"""

import math


MAX_ITEMS = 4096
MAX_SAMPLES = 8192
MAX_COUNTER = 2**31 - 1
MAX_ENCODER_COUNT = 2**53 - 1


class MechanismError(ValueError):
    """Malformed input, exhausted protocol, or rejected measurement."""


class CueUnavailable(MechanismError):
    """No declared visible cue; the caller must handle this without scanning."""


class SaturationError(MechanismError):
    """Requested compensation exceeds the declared control limit."""


def _fields(value, names, label):
    if type(value) is not dict or set(value) != set(names):
        raise MechanismError(f'{label}: exact JSON fields required')


def _number(value, label, *, positive=False, nonnegative=False):
    if type(value) not in (int, float):
        raise MechanismError(f'{label}: finite number required')
    try:
        result = float(value)
    except OverflowError as exc:
        raise MechanismError(f'{label}: finite number required') from exc
    if not math.isfinite(result) or (positive and result <= 0) or (nonnegative and result < 0):
        raise MechanismError(f'{label}: invalid finite number')
    return result


def _integer(value, label, *, low=0, high=MAX_COUNTER):
    if type(value) is not int or not low <= value <= high:
        raise MechanismError(f'{label}: bounded integer required')
    return value


def _pair(value, label, **constraints):
    if type(value) is not list or len(value) != 2:
        raise MechanismError(f'{label}: two-element JSON list required')
    return [_number(v, label, **constraints) for v in value]


def _bounds(value, label, *, positive=True):
    lower, upper = _pair(value, label, positive=positive, nonnegative=not positive)
    if lower > upper:
        raise MechanismError(f'{label}: reversed bounds')
    return [lower, upper]


def _identifier(value):
    if type(value) is not str or not 1 <= len(value) <= 128 or any(ord(c) < 32 for c in value):
        raise MechanismError('landmark ID: bounded printable string required')
    return value


def _version(value):
    if type(value) is not int or value != 1:
        raise MechanismError('unsupported state version')


def initial_exploration(*, max_landmarks, max_visits, max_decisions):
    """Initialize visible-inspection counts, not proof of reaching landmarks."""
    return {'version': 1, 'visits': {}, 'decisions': 0,
            'max_landmarks': _integer(max_landmarks, 'max_landmarks', low=1, high=MAX_ITEMS),
            'max_visits': _integer(max_visits, 'max_visits', low=1),
            'max_decisions': _integer(max_decisions, 'max_decisions', low=1)}


def choose_landmark(state, packet):
    """Choose least inspected visible ID; zero counts and ID ties are deterministic.

    A visit is one selection/inspection of a declared visible cue, not arrival.
    Packet producers must ensure visibility. No geometry or hidden IDs are accepted.
    """
    _fields(state, ('version', 'visits', 'decisions', 'max_landmarks', 'max_visits', 'max_decisions'), 'exploration')
    _version(state['version'])
    limits = initial_exploration(max_landmarks=state['max_landmarks'], max_visits=state['max_visits'],
                                 max_decisions=state['max_decisions'])
    visits = state['visits']
    if type(visits) is not dict or len(visits) > limits['max_landmarks']:
        raise MechanismError('visits: bounded JSON object required')
    for key, count in visits.items():
        _identifier(key)
        _integer(count, 'visit count', low=1, high=limits['max_visits'])
    decisions = _integer(state['decisions'], 'decisions', high=limits['max_decisions'])
    if sum(visits.values()) != decisions:
        raise MechanismError('visit counts do not match decisions')
    _fields(packet, ('landmarks',), 'visible packet')
    landmarks = packet['landmarks']
    if type(landmarks) is not list or len(landmarks) > MAX_ITEMS:
        raise MechanismError('landmarks: bounded JSON list required')
    candidates = {}
    for landmark in landmarks:
        _fields(landmark, ('id', 'bearing_rad'), 'visible landmark')
        key = _identifier(landmark['id'])
        bearing = _number(landmark['bearing_rad'], 'bearing_rad')
        if not -math.pi <= bearing <= math.pi or key in candidates:
            raise MechanismError('invalid bearing or duplicate visible ID')
        candidates[key] = bearing
    if not candidates:
        raise CueUnavailable('no declared visible landmark')
    key = min(candidates, key=lambda k: (visits.get(k, 0), k))
    if decisions == limits['max_decisions'] or visits.get(key, 0) == limits['max_visits']:
        raise MechanismError('exploration decision/visit budget exhausted')
    if key not in visits and len(visits) == limits['max_landmarks']:
        raise MechanismError('exploration landmark budget exhausted')
    return {'state': {**limits, 'visits': {**visits, key: visits.get(key, 0) + 1}, 'decisions': decisions + 1},
            'landmark': {'id': key, 'bearing_rad': candidates[key]}}


def _counts(angles, quantum_rad):
    angles = _pair(angles, 'unwrapped wheel angles')
    counts = []
    for angle in angles:
        scaled = _number(angle / quantum_rad, 'encoder count')
        # Explicit half-away-from-zero quantization of cumulative angles.
        count = math.floor(abs(scaled) + .5) * (-1 if scaled < 0 else 1)
        counts.append(_integer(count, 'encoder count', low=-MAX_ENCODER_COUNT, high=MAX_ENCODER_COUNT))
    return counts


def quantized_encoder_increments(previous_angles, current_angles, *, quantum_rad, max_increment_rad):
    """Difference quantized cumulative, unwrapped angles; retain sub-tick motion.

    Reject excessive raw or quantized jumps. Plausible false readings cannot be
    detected by this mechanism. Angles must be shaft angles for these two wheels.
    """
    quantum = _number(quantum_rad, 'quantum_rad', positive=True)
    limit = _number(max_increment_rad, 'max_increment_rad', positive=True)
    previous = _pair(previous_angles, 'previous angles')
    current = _pair(current_angles, 'current angles')
    if any(abs(b - a) > limit for a, b in zip(previous, current)):
        raise MechanismError('raw encoder increment exceeds protocol')
    return _increments(_counts(previous, quantum), _counts(current, quantum), quantum, limit)


def _increments(previous, current, quantum, limit):
    increments = [_number((b - a) * quantum, 'encoder increment') for a, b in zip(previous, current)]
    if any(abs(v) > limit for v in increments):
        raise MechanismError('quantized encoder increment exceeds protocol')
    return increments


def initial_odometry(wheel_angles, *, radius_m, track_m, quantum_rad, max_steps, max_travel_m):
    """Set estimated local origin regardless of the initial encoder readings."""
    calibration = {'radius_m': _number(radius_m, 'radius_m', positive=True),
                   'track_m': _number(track_m, 'track_m', positive=True),
                   'quantum_rad': _number(quantum_rad, 'quantum_rad', positive=True)}
    return {'version': 1, 'x_m': 0., 'y_m': 0., 'yaw_rad': 0.,
            'wheel_angles_rad': _pair(wheel_angles, 'unwrapped wheel angles'),
            'encoder_counts': _counts(wheel_angles, calibration['quantum_rad']),
            'steps': 0, 'travel_m': 0., 'calibration': calibration,
            'max_steps': _integer(max_steps, 'max_steps', low=1),
            'max_travel_m': _number(max_travel_m, 'max_travel_m', positive=True)}


def _odometry(state):
    _fields(state, ('version', 'x_m', 'y_m', 'yaw_rad', 'wheel_angles_rad', 'encoder_counts', 'steps', 'travel_m',
                    'calibration', 'max_steps', 'max_travel_m'), 'odometry')
    _version(state['version'])
    calibration = state['calibration']
    _fields(calibration, ('radius_m', 'track_m', 'quantum_rad'), 'calibration')
    for key, value in calibration.items():
        _number(value, key, positive=True)
    for key in ('x_m', 'y_m', 'yaw_rad'):
        _number(state[key], key)
    if abs(state['yaw_rad']) > math.pi:
        raise MechanismError('yaw outside normalized range')
    if type(state['encoder_counts']) is not list or len(state['encoder_counts']) != 2:
        raise MechanismError('two encoder counts required')
    for count in state['encoder_counts']:
        _integer(count, 'encoder count', low=-MAX_ENCODER_COUNT, high=MAX_ENCODER_COUNT)
    if _counts(state['wheel_angles_rad'], calibration['quantum_rad']) != state['encoder_counts']:
        raise MechanismError('encoder angles/counts do not match')
    maximum = _integer(state['max_steps'], 'max_steps', low=1)
    _integer(state['steps'], 'steps', high=maximum)
    travel = _number(state['travel_m'], 'travel_m', nonnegative=True)
    budget = _number(state['max_travel_m'], 'max_travel_m', positive=True)
    if travel > budget or math.hypot(state['x_m'], state['y_m']) > travel + 1e-12 * max(1., travel):
        raise MechanismError('odometry travel budget/invariant violated')
    return calibration


def odometry_step(state, wheel_angles, *, max_increment_rad):
    """Integrate the exact differential-drive arc from quantized shaft angles.

    This is a no-slip estimate, with fixed caller calibration. It neither reads
    true pose nor estimates slip, encoder truth, or calibration drift.
    """
    calibration = _odometry(state)
    limit = _number(max_increment_rad, 'max_increment_rad', positive=True)
    if state['steps'] == state['max_steps']:
        raise MechanismError('odometry step budget exhausted')
    increments = quantized_encoder_increments(state['wheel_angles_rad'], wheel_angles,
        quantum_rad=calibration['quantum_rad'], max_increment_rad=limit)
    counts = _counts(wheel_angles, calibration['quantum_rad'])
    left, right = [_number(v * calibration['radius_m'], 'wheel distance') for v in increments]
    distance = _number(left / 2 + right / 2, 'centre distance')
    turn = _number((right - left) / calibration['track_m'], 'heading increment')
    half = turn / 2
    arc = distance * (math.sin(half) / half if half else 1.)
    midpoint = _number(state['yaw_rad'] + half, 'midpoint heading')
    result = {**state, 'calibration': dict(calibration), 'encoder_counts': counts,
              'wheel_angles_rad': _pair(wheel_angles, 'unwrapped wheel angles'),
              'x_m': _number(state['x_m'] + arc * math.cos(midpoint), 'x_m'),
              'y_m': _number(state['y_m'] + arc * math.sin(midpoint), 'y_m'),
              'yaw_rad': math.remainder(_number(state['yaw_rad'] + turn, 'yaw_rad'), math.tau),
              'steps': state['steps'] + 1,
              'travel_m': _number(state['travel_m'] + abs(left) / 2 + abs(right) / 2, 'travel_m')}
    _odometry(result)
    return result


def home_bearing(state, *, arrival_radius_m):
    """Bearing to estimated local (0,0), absent within caller arrival tolerance."""
    _odometry(state)
    tolerance = _number(arrival_radius_m, 'arrival_radius_m', nonnegative=True)
    distance = _number(math.hypot(state['x_m'], state['y_m']), 'home distance')
    arrived = distance <= tolerance
    bearing = None if arrived else math.remainder(
        math.atan2(-state['y_m'], -state['x_m']) - state['yaw_rad'], math.tau)
    return {'distance_m': distance, 'bearing_rad': bearing, 'arrived': arrived}


def _sum(values, label):
    try:
        return _number(math.fsum(values), label)
    except (OverflowError, ValueError) as exc:
        raise MechanismError(f'{label}: nonfinite calculation') from exc


def fit_wheel_gains(samples, *, max_samples, min_samples, min_excitation, gain_bounds,
                    control_limit, dt_bounds_s, max_rate_rad_s, max_residual_rad_s,
                    max_relative_rmse):
    """Fit rate = gain * control separately for two wheels, with zero intercept.

    Inputs are measured encoder increments over measured dt, not intended motion.
    The empirical gain is protocol-specific; torque controls do not imply a
    universal velocity model. Contact samples reject the entire fit.
    """
    maximum = _integer(max_samples, 'max_samples', low=1, high=MAX_SAMPLES)
    minimum = _integer(min_samples, 'min_samples', low=1, high=maximum)
    excitation_limit = _number(min_excitation, 'min_excitation', positive=True)
    bounds = _bounds(gain_bounds, 'gain_bounds')
    control_max = _number(control_limit, 'control_limit', positive=True)
    dt_min, dt_max = _bounds(dt_bounds_s, 'dt_bounds_s')
    rate_max = _number(max_rate_rad_s, 'max_rate_rad_s', positive=True)
    residual_max = _number(max_residual_rad_s, 'max_residual_rad_s', nonnegative=True)
    relative_max = _number(max_relative_rmse, 'max_relative_rmse', nonnegative=True)
    if relative_max > 1:
        raise MechanismError('max_relative_rmse must be at most one')
    if type(samples) is not list or not minimum <= len(samples) <= maximum:
        raise MechanismError('sample count outside bounded protocol')
    controls, rates = [], []
    for sample in samples:
        _fields(sample, ('control', 'increments_rad', 'dt_s', 'contact'), 'gain sample')
        if type(sample['contact']) is not bool or sample['contact']:
            raise MechanismError('contact sample rejects gain fit')
        control = _pair(sample['control'], 'control')
        increments = _pair(sample['increments_rad'], 'measured increments')
        dt = _number(sample['dt_s'], 'dt_s', positive=True)
        if not dt_min <= dt <= dt_max or any(abs(u) > control_max for u in control):
            raise MechanismError('sample outside dt/control protocol')
        rate = [_number(v / dt, 'measured rate') for v in increments]
        if any(abs(v) > rate_max for v in rate):
            raise MechanismError('measured rate exceeds protocol')
        controls.append(control)
        rates.append(rate)
    gains, excitation, rmse, relative = [], [], [], []
    for wheel in range(2):
        energy = _sum((u[wheel] * u[wheel] for u in controls), 'excitation')
        if energy < excitation_limit:
            raise MechanismError('weak wheel excitation rejects gain fit')
        gain = _number(_sum((u[wheel] * y[wheel] for u, y in zip(controls, rates)), 'cross product')
                       / energy, 'gain')
        if not bounds[0] <= gain <= bounds[1]:
            raise MechanismError('fitted gain outside calibrated bounds')
        residuals = [_number(y[wheel] - gain * u[wheel], 'residual') for u, y in zip(controls, rates)]
        if any(abs(r) > residual_max for r in residuals):
            raise MechanismError('sample residual rejects gain fit')
        squared_error = _sum((r * r for r in residuals), 'squared residuals')
        squared_rate = _sum((y[wheel] * y[wheel] for y in rates), 'squared rates')
        if squared_rate <= 0:
            raise MechanismError('no measured response rejects gain fit')
        relative_error = math.sqrt(squared_error / squared_rate)
        if relative_error > relative_max:
            raise MechanismError('poor relative fit rejects gain fit')
        gains.append(gain)
        excitation.append(energy)
        rmse.append(math.sqrt(squared_error / len(samples)))
        relative.append(relative_error)
    return {'version': 1, 'gains_rad_s_per_control': gains, 'excitation': excitation,
            'rmse_rad_s': rmse, 'relative_rmse': relative, 'sample_count': len(samples),
            'gain_bounds': bounds, 'control_limit': control_max}


def compensate_wheels(nominal_control, fit, *, nominal_gains_rad_s_per_control, max_compensation_ratio):
    """Scale requested controls by nominal/measured gain; never silently clip."""
    _fields(fit, ('version', 'gains_rad_s_per_control', 'excitation', 'rmse_rad_s',
                  'relative_rmse', 'sample_count', 'gain_bounds', 'control_limit'), 'gain fit')
    _version(fit['version'])
    bounds = _bounds(fit['gain_bounds'], 'gain_bounds')
    gains = _pair(fit['gains_rad_s_per_control'], 'measured gains', positive=True)
    if any(not bounds[0] <= k <= bounds[1] for k in gains):
        raise MechanismError('measured gain outside calibrated bounds')
    _pair(fit['excitation'], 'excitation', positive=True)
    _pair(fit['rmse_rad_s'], 'rmse_rad_s', nonnegative=True)
    if any(v > 1 for v in _pair(fit['relative_rmse'], 'relative_rmse', nonnegative=True)):
        raise MechanismError('invalid relative fit')
    _integer(fit['sample_count'], 'sample_count', low=1, high=MAX_SAMPLES)
    limit = _number(fit['control_limit'], 'control_limit', positive=True)
    nominal = _pair(nominal_control, 'nominal control')
    nominal_gains = _pair(nominal_gains_rad_s_per_control, 'nominal gains', positive=True)
    bound = _number(max_compensation_ratio, 'max_compensation_ratio', positive=True)
    if bound < 1:
        raise MechanismError('compensation ratio bound must be at least one')
    ratios = [_number(a / b, 'compensation ratio', positive=True) for a, b in zip(nominal_gains, gains)]
    if any(not 1 / bound <= r <= bound for r in ratios):
        raise MechanismError('compensation ratio outside protocol')
    control = [_number(u * r, 'compensated control') for u, r in zip(nominal, ratios)]
    if any(abs(u) > limit for u in nominal + control):
        raise SaturationError('control saturation rejects compensation')
    return {'control': control, 'gain_ratio': ratios, 'saturated': False}
