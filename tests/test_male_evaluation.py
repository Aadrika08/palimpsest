"""Pure evaluation-contract fixtures; no owner process, Torch or simulator."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

import numpy as np
from palimpsest import artifacts
from palimpsest.male_policy import CONTROLLERS, IDENTITY_HASHES, PROFILE
from palimpsest.records import RunWriter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('male_evaluation', ROOT / 'scripts/evaluate_male_closed_loop.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def identity(controller='male-original'):
    return {'controller': controller, 'variant': CONTROLLERS[controller], 'profile': PROFILE,
            **{key: ('a' if controller == 'male-original' else 'b') * 64 for key in IDENTITY_HASHES}}


WORLD = {'arena': 7., 'pose': [0., 0., 0.], 'obstacles': [[3., 3., .3]], 'goal': [5., 5., .5]}


def initial(controller='male-original'):
    return {'application': {'seed': 120, 'controller': controller, 'episode': 0, 'total_tick': 0,
                'episode_step': 0, 'phase': 'paused', 'eyes': {'left': True, 'right': True}},
        'policy': {'kind': 'male-reduced-v1', 'hidden': np.zeros((1, 138), np.float32), 'failure_diagnostics': {}},
        'identity': {'policy': {'provenance': {'policy_identity': identity(controller)}},
                     'environment_class': 'authored.fixture', 'model_sha256': 'c' * 64},
        'integration': np.zeros(4, np.float64), 'environment': {'values': {'_t': 0}},
        'observation': {'cam_left': np.zeros((128, 128, 3), np.uint8), 'cam_right': np.zeros((128, 128, 3), np.uint8),
                        'sensors': {'collision': 0., 'collision_angle': None, 'wind_direction': np.array([1., 0.])}},
        'rng': {'environment': {'state': 123}, 'environment_seed': 120, 'spaces': {}}}


class FakeSteps:
    def __init__(self, terminal=None, reject=False):
        self.calls, self.terminal, self.reject = [], terminal, reject
        self.view = {'state': {'total_tick': 0, 'episode': 0, 'phase': 'paused', 'revision': 0}, 'receipts': []}

    def call(self, identifier, operation, command):
        self.calls.append((operation, command))
        tick = len(self.calls)
        self.view = {'state': {'total_tick': tick, 'episode': 0,
            'phase': 'terminated' if tick == self.terminal else 'paused', 'revision': tick},
            'receipts': [{'id': command['id'], 'status': 'rejected' if self.reject else 'applied'}]}

    def wait(self, identifier, predicate):
        if not predicate(self.view):
            raise AssertionError('Fixture failed to reach the requested boundary')
        return self.view


class MaleEvaluationFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        artifacts._CACHE.clear()

    def fixture(self, *, phase='terminated', reason='stalled', edit=False, changed_input=False):
        run = self.root / uuid.uuid4().hex
        model = identity()
        writer = RunWriter(run / 'recording', {'run_id': run.name, 'controller': 'male-original',
            'policy_identity': model, 'seed': 120, 'requested_device': 'cpu', 'scenario': {'id': 'reproduction'},
            'texture': 'checker', 'control_interval_seconds': .02,
            'observation_profile': 'two-rgb-eyes-contact-relative-goal-bearing-v1',
            'sensor_order': ['collision', 'collision_angle', 'wind_cos', 'wind_sin']})
        writer.event('episode_started', episode=0, episode_step=0, tick=0, seed=120, world=WORLD)
        writer.event('policy_loaded', provenance={'policy_identity': model})
        if edit:
            writer.event('eyes_changed', episode=0, episode_step=0, eyes={'left': True, 'right': True})
        camera = np.zeros((128, 128, 3), np.uint8)
        if changed_input:
            camera[0, 0, 0] = 1
        for tick in range(2):
            writer.tick(0, tick, cam_left=camera, cam_right=camera, raw_cam_left=camera, raw_cam_right=camera,
                sensors=np.array([0., 0., 1., 0.], np.float32), action=np.array([1., 0.], np.float32), control=np.zeros(2),
                pose=np.array([tick * .1, 0., 0.]), next_pose=np.array([(tick + 1) * .1, 0., 0.]),
                reward=np.array(.5), simulation_time=np.array((tick + 1) * .02),
                latency=np.array(.001 * (tick + 1)), step_latency=np.array(.002),
                raw_output=np.zeros(2, np.float32), encoded_input=np.zeros(136, np.float32),
                population_stats=np.empty((0, 4)), eyes=np.ones(2, np.bool_))
        outcome = None if reason is None else {'reason': reason, 'episode': 0, 'steps': 2, 'final_distance': 7.}
        metrics = {'reward': 1., 'contact_ticks': 0, 'path_length': .2}
        if outcome:
            writer.event('episode_finished', outcome=outcome, metrics=metrics)
        writer.finish({'total_tick': 2, 'final_phase': phase, 'last_outcome': outcome, 'metrics': metrics})
        writer.close()
        state = {'total_tick': 2, 'phase': phase, 'last_outcome': outcome, 'metrics': metrics}
        start = evaluation.initial_fingerprint(initial(), WORLD, 120, model)
        return run, model, state, start

    def test_frozen_plan_and_bounds(self):
        plan = evaluation.planned_runs()
        self.assertEqual([(row['seed'], row['controller']) for row in plan],
                         [(seed, controller) for seed in range(128, 136) for controller in CONTROLLERS])
        self.assertTrue(all(row['status'] == 'not_started' for row in plan))
        self.assertTrue(set(evaluation.PROTOCOL['scene_seeds']).isdisjoint(range(100, 128)))
        self.assertEqual(evaluation.PROTOCOL['version'], 2)
        self.assertEqual(evaluation.PROTOCOL['max_ticks_per_run'], 600)
        self.assertEqual(evaluation.PROTOCOL['max_runs'], 16)
        self.assertEqual(evaluation.PROTOCOL['retry_count'], 0)

    def test_initial_match_excludes_policy_but_checks_physics_camera_and_rng(self):
        left = evaluation.initial_fingerprint(initial(), WORLD, 120, identity())
        control = initial('male-control')
        right = evaluation.initial_fingerprint(control, WORLD, 120, identity('male-control'))
        evaluation.require_matched_initial(left, right)
        for component in ('integration', 'camera', 'rng'):
            changed = copy.deepcopy(control)
            if component == 'integration':
                changed['integration'][0] = .1
            elif component == 'camera':
                changed['observation']['cam_left'][0, 0, 0] = 1
            else:
                changed['rng']['environment']['state'] += 1
            with self.assertRaisesRegex(ValueError, 'Paired initial states differ'):
                evaluation.require_matched_initial(left, evaluation.initial_fingerprint(changed, WORLD, 120, identity('male-control')))

    def test_initial_rejects_nonfresh_hidden_or_bad_declared_sensors(self):
        for change in ('hidden', 'seed', 'bearing'):
            value = initial()
            if change == 'hidden':
                value['policy']['hidden'][0, 0] = np.nan
            elif change == 'seed':
                value['application']['seed'] = 116
            else:
                value['observation']['sensors']['wind_direction'] = np.array([2., 0.])
            with self.assertRaises(ValueError):
                evaluation.initial_fingerprint(value, WORLD, 120, identity())

    def test_initial_input_hash_matches_exact_engine_float32_projection(self):
        value = initial()
        value['observation']['sensors'] = {'collision': 0., 'collision_angle': .123456789,
                                          'wind_direction': np.array([.6, .8], np.float64)}
        projected = {'cam_left': value['observation']['cam_left'], 'cam_right': value['observation']['cam_right'],
                     'sensors': np.array([0., .123456789, .6, .8], np.float32)}
        result = evaluation.initial_fingerprint(value, WORLD, 120, identity())
        self.assertEqual(result['inputs'], evaluation.state_digest(projected))
        self.assertEqual(result['features'], evaluation.state_digest(evaluation.features(projected)))

    def test_serial_steps_stop_naturally_without_reset_and_cap_at_600(self):
        for terminal, count in ((1, 1), (None, 600)):
            supervisor = FakeSteps(terminal=terminal)
            final = evaluation.step_episode(supervisor, 'fixture', supervisor.view, supervisor.wait)
            self.assertEqual(final['total_tick'], count)
            self.assertEqual(len(supervisor.calls), count)
            self.assertTrue(all(operation == 'command' and command['kind'] == 'step' and command['expected_episode'] == 0
                                for operation, command in supervisor.calls))
            self.assertEqual(len({command['id'] for _, command in supervisor.calls}), count)

    def test_rejection_and_deadline_do_not_retry(self):
        supervisor = FakeSteps(reject=True)
        with self.assertRaisesRegex(ValueError, 'not applied'):
            evaluation.step_episode(supervisor, 'fixture', supervisor.view, supervisor.wait)
        self.assertEqual(len(supervisor.calls), 1)
        supervisor = FakeSteps()
        def expired(*args):
            raise TimeoutError('fixture deadline')
        with self.assertRaises(TimeoutError):
            evaluation.step_episode(supervisor, 'fixture', supervisor.view, expired)
        self.assertEqual(len(supervisor.calls), 1)

    def test_actual_record_reader_fixture_reports_outcome_separately_from_timing(self):
        run, model, state, start = self.fixture()
        result = evaluation.validate_recording(run, 120, model, state, start)
        self.assertEqual(result['outcome'], 'stalled')
        self.assertFalse(result['goal_reached'])
        self.assertEqual(result['simulation_seconds'], .04)
        self.assertEqual(result['policy_timing']['p95_seconds'], .002)
        self.assertEqual(result['metrics']['path_length'], .2)
        files, _, size = evaluation.inventory(run)
        self.assertEqual(size, sum(item['size_bytes'] for item in files))

    def test_record_rejects_incomplete_episode_changed_first_input_or_intervention(self):
        for kwargs in ({'phase': 'paused', 'reason': None}, {'changed_input': True}, {'edit': True},
                       {'phase': 'truncated', 'reason': 'stalled'}):
            run, model, state, start = self.fixture(**kwargs)
            with self.assertRaises(ValueError):
                evaluation.validate_recording(run, 120, model, state, start)

    def test_tick_cap_is_distinct_from_natural_termination(self):
        run, model, state, start = self.fixture(phase='paused', reason=None)
        # A small fixture cap exercises the classification without a 113 MiB fixture.
        with patch.dict(evaluation.PROTOCOL, max_ticks_per_run=2):
            result = evaluation.validate_recording(run, 120, model, state, start)
        self.assertEqual(result['outcome'], 'evaluation_tick_cap')
        self.assertIsNone(result['last_outcome'])

    def test_exclusive_output_precedes_runtime_construction(self):
        with patch.object(evaluation, 'LabSupervisor') as owner:
            with self.assertRaises(FileExistsError):
                evaluation.evaluate(SimpleNamespace(repo=self.root, assets=self.root / 'assets', output=self.root))
            owner.assert_not_called()

    def test_first_owner_failure_retains_all_frozen_plan_rows_without_retry(self):
        supervisor = SimpleNamespace(budget=SimpleNamespace(check=Mock(return_value={})),
            control_budget=SimpleNamespace(check=Mock()), workers={}, shutdown=Mock(),
            start=Mock(side_effect=RuntimeError('fixture startup failure')))
        output = self.root / 'failure'
        with patch.object(evaluation, 'LabSupervisor', return_value=supervisor), \
                patch.object(evaluation, 'sources', return_value={'fixture.py': 'a' * 64}), \
                patch.object(evaluation, 'resolve_profile', side_effect=lambda root, assets, name: (identity(name), {})):
            result = evaluation.evaluate(SimpleNamespace(repo=self.root, assets=self.root / 'assets', output=output))
        self.assertEqual(result, 1)
        report = json.loads((output / 'evaluation.json').read_text())
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['runs'][0]['status'], 'failed')
        self.assertEqual([row['status'] for row in report['runs'][1:]], ['not_started'] * 15)
        self.assertNotIn('summary', report)
        supervisor.start.assert_called_once()
        supervisor.shutdown.assert_called_once()

    def test_disposed_handle_is_not_queried_and_shutdown_failure_cannot_skip_identity_checks(self):
        class ProcessHandle:
            closed = False
            @property
            def exitcode(self):
                if self.closed:
                    raise ValueError('process object is closed')
                return 0
            def is_alive(self):
                if self.closed:
                    raise ValueError('process object is closed')
                return False

        for shutdown_fails in (False, True):
            with self.subTest(shutdown_fails=shutdown_fails):
                process = ProcessHandle()
                def shutdown():
                    process.closed = True
                    if shutdown_fails:
                        raise RuntimeError('fixture shutdown failure')
                owner = SimpleNamespace(view={'status': 'closed'}, process=process)
                supervisor = SimpleNamespace(budget=SimpleNamespace(check=Mock(return_value={})),
                    control_budget=SimpleNamespace(check=Mock()), workers={'a' * 32: owner},
                    shutdown=Mock(side_effect=shutdown), close=Mock(return_value={'status': 'closed'}),
                    start=Mock(side_effect=RuntimeError('fixture initial failure')))
                output = self.root / ('shutdown-fails' if shutdown_fails else 'disposed')
                with patch.object(evaluation, 'LabSupervisor', return_value=supervisor), \
                        patch.object(evaluation, 'sources', return_value={'fixture.py': 'a' * 64}) as source_check, \
                        patch.object(evaluation, 'resolve_profile', side_effect=lambda root, assets, name: (identity(name), {})) as models:
                    evaluation.evaluate(SimpleNamespace(repo=self.root, assets=self.root / 'assets', output=output))
                report = json.loads((output / 'evaluation.json').read_text())
                self.assertTrue(report['sources_unchanged'])
                self.assertTrue(report['model_identities_unchanged'])
                self.assertTrue(report['recording_fingerprints_unchanged'])
                self.assertEqual(source_check.call_count, 2)
                self.assertEqual(models.call_count, 4)
                self.assertEqual(report['cleanup'][0]['owner_exitcode'], 0)
                self.assertFalse(report['cleanup'][0]['owner_alive'])
                self.assertEqual(report['supervisor_shutdown'], 'failed' if shutdown_fails else 'completed')
                self.assertNotIn('process object is closed', json.dumps(report))
                if shutdown_fails:
                    self.assertEqual(report['finalization_errors'][0]['stage'], 'supervisor_shutdown')


if __name__ == '__main__':
    unittest.main()
