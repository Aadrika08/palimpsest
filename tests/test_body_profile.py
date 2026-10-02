"""Fixture-only guards for loaded compensation; no simulator qualification."""
import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
try:
    import numpy as np
except ModuleNotFoundError:
    np = None

from palimpsest import body_profile as body
from palimpsest.engine import Engine
from palimpsest.records import RunWriter, iter_ticks
from palimpsest.replay import _same_tick, Divergence
from test_engine import SmallEnv
import test_verify_body_gains as diagnostic


class BodyFixtureEnv(SmallEnv):
    """Small deterministic body, for Engine/IPC boundaries only, not physics proof."""
    def __init__(self):
        super().__init__()
        self.mj, fixture = diagnostic.GainChecks().probe()
        for key, value in vars(fixture.model).items():
            if key != 'opt':
                setattr(self.model, key, value)
        self.model.opt.integrator, self.model.opt.disableflags = 0, 0
        self.model.jnt_qposadr = np.array([3, 4])
        self.model.actuator_gear = np.array([[3.*.8,0,0,0,0,0],[3.,0,0,0,0,0]])
        self.left_hinge_id, self.right_hinge_id = 0, 1
        self.data.qpos = np.zeros(5)
        self.data._address = 20
        self.data.ncon, self.data.contact = fixture.data.ncon, fixture.data.contact
        self._action_scale = 2.

    def step(self, action):
        self.calls += 1
        self.data.ctrl[:] = body.effective_control(action.tolist())
        start = self.data.time
        for index in range(10):
            self.data.time = start + index*.002
            self.mj.callback(self.model, self.data)
        self.data.time = start + .02
        self.data.qpos[3:] += self.data.ctrl*.02
        self.data.qpos[:2] += action*.02
        return self._get_obs(), 1., False, False, {'dist_to_goal':5., 'stalled':False}


def fixture_configure(env, episode):
    env._body_profile_identity = body.profile_identity()
    env._body_contact_ownership = body.contact_ownership(env.mj, env.model)
    env._body_runtime_world_profile = {'fixture':True}
    return body.initialize_state(episode, [0.,0.], env.data.time)


@unittest.skipIf(np is None, 'NumPy is provided by the simulation extra')
class BodyChecks(unittest.TestCase):
    def test_world_metadata_does_not_relax_geometry_or_authoring_source_pins(self):
        from palimpsest import memory_world
        current = copy.deepcopy(memory_world.PROFILE)
        accepted = body.world_identity(current, memory_world.PROFILE_SHA256)
        changed = copy.deepcopy(current)
        changed['memory_source_sha256'] = '1'*64
        changed['sensor_bridge_source_sha256'] = '2'*64
        newer = body.world_identity(changed, body._sha(changed))
        self.assertNotEqual(accepted['profile_sha256'], newer['profile_sha256'])
        self.assertEqual(accepted['semantic_profile_sha256'], newer['semantic_profile_sha256'])
        self.assertEqual(newer['profile'], changed)
        with self.assertRaisesRegex(ValueError, 'full world PROFILE'):
            body.world_identity(current, 'f'*64)
        changed['posts'][0][0] += .01
        with self.assertRaisesRegex(ValueError, 'geometry'):
            body.world_identity(changed, body._sha(changed))
        changed = copy.deepcopy(current); changed['world_source_sha256'] = '3'*64
        with self.assertRaisesRegex(ValueError, 'authoring'):
            body.world_identity(changed, body._sha(changed))
        changed = copy.deepcopy(current); changed['other_source_sha256'] = '4'*64
        with self.assertRaisesRegex(ValueError, 'geometry'):
            body.world_identity(changed, body._sha(changed))

    def test_shared_helpers_preserve_frozen_diagnostic_protocol(self):
        self.assertIs(diagnostic.verify.ContactProbe, body.ContactProbe)
        self.assertIs(diagnostic.verify.contact_ownership, body.contact_ownership)
        self.assertEqual(diagnostic.verify.PROTOCOL_SHA256,
                         'bf883b89156201ccd35659fa7971fda507876e357c733356ed3eec59bac760f0')
        for controller in ('teacher', 'flynn', 'male-original'):
            from palimpsest.profiles import validate
            with self.assertRaises(ValueError):
                validate(body.SCENARIO, 'checker', controller)
        from palimpsest.profiles import validate
        self.assertEqual(validate(body.SCENARIO, 'checker', 'manual')['devices'], ['cpu'])
        with self.assertRaisesRegex(ValueError, 'CPU'):
            Engine.open(Path('.'), Path('.'), Path('must-not-be-created'),
                        scenario=body.SCENARIO, controller='manual', device='cuda')
        self.assertFalse(Path('must-not-be-created').exists())

    def test_nominal_mapping_zero_reverse_saturation_and_keyboard_combinations(self):
        forward = body.plan_action([.3, 0.])
        self.assertEqual(forward['applied_action'], [.3435766398906708, -.06609576940536499])
        self.assertEqual(forward['applied_control'], [.7532490491867065, .6210575103759766])
        self.assertEqual(body.plan_action([-.3, 0.])['applied_control'], [-x for x in forward['applied_control']])
        self.assertEqual(body.plan_action([0., 0.])['applied_action'], [0., 0.])
        for v in (-.3, 0., .3):
            for h in (-.2, 0., .2):
                plan = body.plan_action([v, h])
                self.assertEqual(body.effective_control(plan['applied_action']), plan['applied_control'])
        for action in ([1., 0.], [2., 1.], [float('nan'), 0.]):
            with self.assertRaises(ValueError):
                body.plan_action(action)

    def test_state_identity_cursor_and_native_encoder_validation(self):
        identity = body.profile_identity()
        state = body.initialize_state('episode-0', [0., 0.], 0.)
        self.assertEqual(body.validate_state(state, identity, episode=0, episode_step=0), state)
        for field, value in [('profile_sha256', '0'*64), ('previous_angles_rad', [True, 0.]),
                             ('time_s', -.1), ('last_tick', 0), ('phase', 'learning')]:
            invalid = {**state, field: value}
            with self.assertRaises(ValueError):
                body.validate_state(invalid, identity, episode=0, episode_step=0)
        mj, env = diagnostic.GainChecks().probe()
        env.model.jnt_qposadr = [0, 1]
        env.left_hinge_id, env.right_hinge_id = 0, 1
        env.data.qpos = np.zeros(2)
        body.validate_native(state, env.model, env.data, env)
        env.data.qpos[0] = .1
        with self.assertRaisesRegex(ValueError, 'encoder'):
            body.validate_native(state, env.model, env.data, env)

    def test_snapshot_application_rejects_malformed_state_without_touching_destination(self):
        env = BodyFixtureEnv()
        fixture_configure(env, 'episode-0')
        state = body.initialize_state('episode-0', [0.,0.], 0.)
        application = {'schema_version':5, 'phase':'paused', 'scenario':body.SCENARIO,
                       'controller':'manual', 'episode':0, 'episode_step':0, 'body_state':state}
        body.validate_snapshot_application(application, env, env.model, env.data)
        original = env.data.qpos.copy()
        for key, value in [('schema_version',4), ('phase','running'), ('controller','teacher'),
                           ('episode_step',1)]:
            with self.assertRaises(ValueError):
                body.validate_snapshot_application({**application,key:value}, env, env.model, env.data)
        invalid = copy.deepcopy(application)
        invalid['body_state']['previous_angles_rad'][0] = .1
        with self.assertRaisesRegex(ValueError, 'encoder'):
            body.validate_snapshot_application(invalid, env, env.model, env.data)
        np.testing.assert_array_equal(env.data.qpos, original)

    def test_contact_overflow_is_retained_and_numeric_converter_never_truncates(self):
        mj, env = diagnostic.GainChecks().probe()
        env.data.ncon = 129
        probe = body.ContactProbe(mj, env)
        probe.install(); probe.begin(0)
        try:
            for index in range(10):
                env.data.time = index*.002
                mj.callback(env.model, env.data)
            env.data.time = .02
            interval = probe.end()
            self.assertFalse(interval['coverage_passed'])
            self.assertEqual(interval['callback_count'], 10)
            self.assertIn('Contact count', interval['coverage_errors'][0])
            with self.assertRaises(ValueError):
                body.contact_arrays(interval)
        finally:
            probe.close()
        mj, env = diagnostic.GainChecks().probe()
        probe = body.ContactProbe(mj, env)
        pair = probe._pairs(env.model, env.data)[0]
        interval = {'coverage_passed':True, 'callback_count':10,
                    'stages':[{'pairs':[pair]*129, 'time_s':i*.002, 'control':[0.,0.]} for i in range(10)],
                    'end':{'pairs':[], 'contact_cache_time_s':.018, 'data_time_s':.02}}
        with self.assertRaisesRegex(ValueError, 'overflow'):
            body.contact_arrays(interval)

    def test_interval_cleanup_rejection_and_once_only_override(self):
        mj, env = diagnostic.GainChecks().probe()
        env._action_scale = 2.
        env.model.jnt_qposadr = [0, 1]
        env.left_hinge_id, env.right_hinge_id = 0, 1
        env.data.qpos = np.zeros(2)
        def step(action):
            env.data.ctrl = body.effective_control(action.tolist())
            for i in range(10):
                env.data.time = i * .002
                mj.callback(env.model, env.data)
            env.data.time = .02
            env.data.qpos += np.asarray(env.data.ctrl)*.02
            return {}, 0., False, False, {}
        env.step = step
        state = body.initialize_state('episode-0', [0., 0.], 0.)
        plan = body.plan_action([.3, 0.])
        with patch.dict('sys.modules', mujoco=mj):
            result, advanced, packet, arrays = body.step(env, state, [.3, 0.], 0,
                                                      action_override=plan['applied_action'])
        self.assertIsNone(mj.callback)
        self.assertEqual(packet['command'], plan)
        self.assertEqual(advanced['last_tick'], 0)
        self.assertEqual(arrays['body_nominal_action'].tolist(), [.3, 0.])
        self.assertEqual(arrays['body_contact_counts'].tolist(), [1]*11)
        self.assertEqual(arrays['body_contact_classes'][:,0].tolist(), [2]*11)
        self.assertTrue(np.all(arrays['body_contact_ids'][:,1:]==0))
        self.assertTrue(np.all(arrays['body_contact_distances'][:,1:]==0))
        self.assertTrue(np.all(arrays['body_contact_classes'][:,1:]==0))
        self.assertLess(sum(a.nbytes for a in arrays.values()), body.MAX_TICK_BYTES)
        self.assertEqual(list(env.data.ctrl), plan['applied_control'])
        env.data.time = 0.; env.data.qpos[:] = 0.
        with patch.dict('sys.modules', mujoco=mj):
            with self.assertRaisesRegex(ValueError, 'override'):
                body.step(env, state, [.3, 0.], 0, action_override=[.3, 0.])
        self.assertIsNone(mj.callback)
        env.data.contact[0].geom1, env.data.contact[0].geom2 = 1, 4
        with patch.dict('sys.modules', mujoco=mj):
            with self.assertRaises(body.BodyFailure) as caught:
                body.step(env, state, [.3, 0.], 0)
        self.assertEqual(caught.exception.packet['interval']['callback_count'], 10)
        self.assertTrue(caught.exception.packet['interval']['contact'])
        self.assertIsNone(mj.callback)

    def test_action_replay_compares_optional_body_fields_without_breaking_legacy(self):
        from palimpsest.replay import _PHYSICAL
        left = {key: np.array(0.) for key in _PHYSICAL}
        left.update(episode=0, tick=0)
        _same_tick(left, copy.deepcopy(left), 'actions', 0)
        left.update({key: np.zeros(2) for key in body.TICK_FIELDS})
        right = copy.deepcopy(left)
        right['body_nominal_action'][0] = .1
        with self.assertRaises(Divergence):
            _same_tick(left, right, 'actions', 0)

    def test_engine_conditional_schema_and_rejection_before_mutating_manual_intent(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = [Path(temp)/str(i) for i in range(3)]
            def configure(env, episode):
                env._body_profile_identity = body.profile_identity()
                env.model.actuator_gear = np.array([[3.*.8,0,0,0,0,0],[3.,0,0,0,0,0]])
                env._body_contact_ownership = {'fixture': True}
                env._body_runtime_world_profile = {'fixture':True}
                return body.initialize_state(episode, [0., 0.], env.data.time)
            with patch.object(body, 'configure', side_effect=configure):
                source = Engine(SmallEnv(), RunWriter(paths[0], {}), scenario=body.SCENARIO)
                dest = Engine(SmallEnv(), RunWriter(paths[1], {}), scenario=body.SCENARIO)
            legacy = Engine(SmallEnv(), RunWriter(paths[2], {}))
            try:
                self.assertEqual(legacy.application_state()['schema_version'], 4)
                self.assertNotIn('body_state', legacy.application_state())
                state = source.application_state()
                self.assertEqual(state['schema_version'], 5)
                self.assertEqual(dest.validate_application(state), state)
                invalid = copy.deepcopy(state); invalid['body_state']['previous_angles_rad'][0] = True
                with self.assertRaises(ValueError):
                    dest.validate_application(invalid)
                command = {'id':'bad', 'kind':'set_action', 'expected_state':'paused',
                           'expected_episode':0, 'payload':{'action':[1.,0.]}}
                with self.assertRaises(ValueError):
                    source.submit(command)
                self.assertEqual(source.manual_action.tolist(), [0.,0.])
            finally:
                for engine in (source, dest, legacy):
                    engine.close()


    def test_engine_source_action_replay_reset_and_restored_application(self):
        with tempfile.TemporaryDirectory() as temp:
            engines = []
            with patch.object(body, 'configure', side_effect=fixture_configure):
                for i in range(3):
                    engines.append(Engine(BodyFixtureEnv(), RunWriter(Path(temp)/str(i), {}), scenario=body.SCENARIO))
            source, actions, destination = engines
            def command(engine, identifier, kind, payload=None, override=None):
                message = {'id':identifier, 'kind':kind, 'expected_state':engine.phase,
                           'expected_episode':engine.episode, 'payload':payload or {}}
                engine.submit(message)
                with patch.dict('sys.modules', mujoco=engine.env.mj):
                    engine.advance(action_override=override)
                self.assertEqual(engine.submit(message)['status'], 'applied')
                self.assertNotEqual(engine.phase, 'failed')
            try:
                for engine in (source, actions):
                    command(engine, 'action', 'set_action', {'action':[.3,.2]})
                command(source, 'one', 'step')
                effective = source.last_transition['action'].copy()
                command(actions, 'one', 'step', override=effective)
                self.assertEqual(source.body_state, actions.body_state)
                np.testing.assert_array_equal(source.last_transition['action'], actions.last_transition['action'])
                state = source.application_state()
                destination.restore_application(state)
                destination.env.data.qpos[:] = source.env.data.qpos
                destination.env.data.time = source.env.data.time
                destination.env.calls = source.env.calls
                self.assertEqual(destination.body_state, source.body_state)
                for engine in (source, destination):
                    command(engine, 'two', 'step')
                self.assertEqual(source.body_state, destination.body_state)
                command(source, 'run', 'run')
                command(source, 'pause', 'pause')
                self.assertEqual(source.body_state['last_tick'], 2)
                with patch.object(body, 'configure', side_effect=fixture_configure):
                    command(source, 'reset', 'reset', {'seed':1})
                self.assertEqual(source.body_state['episode_id'], 'episode-1')
                self.assertIsNone(source.body_state['last_tick'])
                self.assertEqual(source.manual_action.tolist(), [0.,0.])
                self.assertIsNone(source.env.mj.callback)
                for engine in engines:
                    engine.writer.flush()
                source_ticks = list(iter_ticks(source.writer.path))
                action_ticks = list(iter_ticks(actions.writer.path))
                _same_tick(source_ticks[0], action_ticks[0], 'actions', 0)
            finally:
                for engine in engines:
                    engine.close()

    def test_rejected_contact_retains_packet_and_failed_engine_cannot_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(body, 'configure', side_effect=fixture_configure):
                engine = Engine(BodyFixtureEnv(), RunWriter(Path(temp)/'record', {}), scenario=body.SCENARIO)
            try:
                engine.env.data.contact[0].geom1, engine.env.data.contact[0].geom2 = 1,4
                engine.submit({'id':'step', 'kind':'step', 'expected_state':'paused', 'expected_episode':0})
                with patch.dict('sys.modules', mujoco=engine.env.mj):
                    engine.advance()
                self.assertEqual(engine.phase, 'failed')
                with self.assertRaises(ValueError):
                    engine.application_state()
                import json
                events = [json.loads(line) for line in (engine.writer.path/'events.jsonl').read_text().splitlines()]
                failed = next(event for event in events if event['kind']=='body_failed')
                self.assertEqual(failed['detail']['interval']['callback_count'], 10)
                self.assertTrue(failed['detail']['interval']['contact'])
                self.assertIsNone(engine.env.mj.callback)
            finally:
                engine.close()


if __name__ == '__main__':
    unittest.main()
