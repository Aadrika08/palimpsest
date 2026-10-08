"""Synthetic visibility/record-boundary evidence; no native execution."""
import copy
import hashlib
import importlib.util
import math
from pathlib import Path
import time

import pytest

from palimpsest import memory_decision as decision, memory_decision_world as world


def diagnostic():
    name = 'scripts.memory_terminal_attribution'
    assert importlib.util.find_spec(name) is not None, 'bounded attribution script is required'
    return importlib.import_module(name)


@pytest.mark.parametrize('xy,circles,visible,failures', [
    ([4., 0.], [], True, []),
    ([4.000001, 0.], [], False, ['range']),
    ([0., 1.], [], True, []),
    ([0., -1.], [], True, []),
    ([-.000001, 1.], [], False, ['fov']),
    ([2., 0.], [[1., .4, .4]], False, ['occlusion']),
    ([-5., 0.], [], False, ['range', 'fov']),
    ([0., 0.], [], True, []),
])
def test_visibility_inclusive_edges_and_separate_reasons(xy, circles, visible, failures):
    result = diagnostic().visibility([0., 0., 0.], xy, circles)
    assert result['visible'] is visible
    assert result['failed_predicates'] == failures


@pytest.mark.parametrize('pose', [[0., 0., math.nan], [math.inf, 0., 0.], [0., 0.]])
def test_nonfinite_or_malformed_pose_refused(pose):
    with pytest.raises(ValueError):
        diagnostic().visibility(pose, [1., 0.], [])


def terminal_fixture():
    case = world.make_case(402, 'local_cue', 'null', profile_sha256=world.TRAVEL_PROFILE_HASHES[0])
    route = next(r for r in world.public_graph(case)['routes'] if r['route_id'].endswith('-z'))
    target = route['subject_id'] + '-exit'
    predecessor = route['subject_id'] + '-detour'
    row = {'tick': 9, 'episode': 0, 'pose': [.5, 1.25, 0.], 'next_pose': [.6, 1.25, math.pi/2]}
    events = []
    for tick, pose in [(9, row['pose']), (10, row['next_pose'])]:
        inputs = world.reconstruct_inputs(case, pose, tick, event_tick=3, gate_result='not_requested')
        packet = decision.capture_symbolic(*inputs, episode_id='episode-0', tick=tick)
        events.append({'kind': 'memory_sensed', 'episode_step': tick, 'packet': packet})
    events.insert(1, {'kind': 'memory_decision', 'episode_step': 9,
                     'detail': {'kind': 'memory_bridge', 'tick': 9, 'landmark_id': predecessor}})
    return case, [row], events, target


def test_sensor_only_terminal_uses_next_pose_and_keeps_unknown_selection_unknown():
    case, rows, events, target = terminal_fixture()
    result = diagnostic().attribute(case, rows, events, target, 10, 3)
    assert result['terminal']['tick'] == 10
    assert result['terminal']['pose'] == [.6, 1.25, math.pi/2]
    assert result['terminal']['failed_predicates'] == ['fov']
    assert result['terminal']['predecessor_arrived'] is True
    assert result['first_target_selection_in_window'] is None
    assert result['selection_scope'] == 'not-recorded-in-window'
    assert result['status'] == 'attributed'


def test_duplicate_packet_or_pose_mismatch_or_expanded_window_refused():
    case, rows, events, target = terminal_fixture()
    bad = copy.deepcopy(events)
    bad.append(copy.deepcopy(events[-1]))
    with pytest.raises(ValueError, match='Duplicate'):
        diagnostic().attribute(case, rows, bad, target, 10, 3)
    bad = copy.deepcopy(events)
    bad[-1]['packet']['arrivals'] = []
    with pytest.raises(ValueError, match='packet'):
        diagnostic().attribute(case, rows, bad, target, 10, 3)
    with pytest.raises(ValueError, match='64'):
        diagnostic().attribute(case, rows*65, events, target, 10, 3)


def test_integrity_rejects_changed_bytes_symlinks_and_expired_clock(tmp_path):
    path = tmp_path/'source'; path.write_bytes(b'preserved')
    rows = [{'path': str(path), 'bytes': 9, 'sha256': hashlib.sha256(b'preserved').hexdigest()}]
    assert diagnostic().verify_files(rows, time.monotonic()+30) == 1
    path.write_bytes(b'changed!!')
    with pytest.raises(ValueError, match='identity'):
        diagnostic().verify_files(rows, time.monotonic()+30)
    link = tmp_path/'link'; link.symlink_to(path)
    with pytest.raises(ValueError, match='symlink'):
        diagnostic().verify_files([{**rows[0], 'path': str(link)}], time.monotonic()+30)
    with pytest.raises(TimeoutError):
        diagnostic().verify_files(rows, time.monotonic()-1)


def test_consumed_output_refuses_before_inputs_are_read(tmp_path):
    output = tmp_path/'output'; output.mkdir()
    with pytest.raises(FileExistsError):
        diagnostic().run({'output': str(output)})


def test_unregistered_or_rewritten_consumed_identity_refused(tmp_path):
    path = tmp_path/'record'; path.write_bytes(b'a')
    row = {'path': str(path), 'bytes': 1, 'sha256': hashlib.sha256(b'a').hexdigest()}
    module = diagnostic()
    assert hasattr(module, 'require_registered'), 'consumed files must bind to registration and original inventory'
    module.require_registered([row], [row])
    with pytest.raises(ValueError, match='Unregistered'):
        module.require_registered([row], [])
    with pytest.raises(ValueError, match='identity'):
        module.require_registered([row], [{**row, 'sha256': '0'*64}])


def test_registration_identity_covers_exact_parsed_bytes_and_later_change(tmp_path):
    module = diagnostic()
    assert hasattr(module, 'verify_registration'), 'registration needs a separate immutable identity'
    path = tmp_path/'registration.json'; path.write_bytes(b'{"schema":"fixture"}\n')
    reg = module.read_json(path, registration=True)
    assert reg['registration_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    module.verify_registration(reg)
    path.write_bytes(b'{ "schema": "fixture" }\n')
    with pytest.raises(ValueError, match='Registration'):
        module.verify_registration(reg)


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'terminal', 'invisible'])
def test_completed_controls_require_one_visible_bridge_and_terminal_requires_none(problem):
    case, rows, events, target = terminal_fixture()
    if problem == 'missing':
        events.pop(1)
    elif problem == 'duplicate':
        events.insert(1, copy.deepcopy(events[1]))
    elif problem == 'terminal':
        events.append({'kind': 'memory_decision', 'episode_step': 10,
                       'detail': {'kind': 'memory_bridge', 'tick': 10, 'landmark_id': target}})
    else:
        events[1]['detail']['landmark_id'] = 'missing-landmark'
    with pytest.raises(ValueError, match='bridge'):
        diagnostic().attribute(case, rows, events, target, 10, 3)


def test_loaded_project_code_must_be_from_the_hashed_checkout(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    module = diagnostic()
    assert hasattr(module, 'verify_loaded_sources'), 'actual imported source location must be bound'
    monkeypatch.setitem(sys.modules, 'palimpsest.wrong_checkout', SimpleNamespace(__file__=str(tmp_path/'wrong.py')))
    with pytest.raises(ValueError, match='Imported'):
        module.verify_loaded_sources(Path(__file__).resolve().parents[1])
