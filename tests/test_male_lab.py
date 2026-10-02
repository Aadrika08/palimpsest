"""Pure Engine/API/state fixtures; no Torch, native simulator, owner, or build."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
from fastapi.testclient import TestClient
from palimpsest.engine import Engine
from palimpsest import male_policy, profiles, replay, snapshots, worker
from palimpsest.records import RunWriter, iter_ticks
from test_engine import SmallEnv, SmallPolicy


def identity(controller='male-original'):
    return {'controller': controller, 'variant': male_policy.CONTROLLERS[controller], 'profile': male_policy.PROFILE,
            **{key: 'a' * 64 for key in male_policy.IDENTITY_HASHES}}


class MaleIntegrationFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def engine(self, name, controller='male-original'):
        policy = SmallPolicy()
        policy.provenance = {'policy_identity': identity(controller)}
        engine = Engine(SmallEnv(), RunWriter(self.root / name, {'run_id': name}), controller=controller, policy=policy)
        self.addCleanup(engine.close)
        return engine

    def test_cpu_profile_dispatch_recording_and_reset_have_no_visual_populations(self):
        for controller in male_policy.CONTROLLERS:
            self.assertEqual(profiles.validate('reproduction', 'checker', controller)['controller'], controller)
            for scenario, texture in (('memory-passages', 'checker'), ('sparse-navigation', 'checker'), ('reproduction', 'realistic')):
                with self.assertRaises(ValueError):
                    profiles.validate(scenario, texture, controller)
            engine = self.engine(controller, controller)
            engine.submit({'id': 'step', 'kind': 'step', 'expected_state': 'paused', 'expected_episode': 0})
            engine.advance()
            self.assertEqual(engine.env.calls, 1)
            self.assertNotIn('privileged', engine.policy.seen)
            self.assertEqual(set(engine.policy.seen['sensors']), {'collision', 'collision_angle', 'wind_direction'})
            self.assertEqual(engine.last_transition['populations'], [])
            self.assertEqual(engine.writer.manifest['policy_identity'], identity(controller))
            engine.submit({'id': 'reset', 'kind': 'reset', 'expected_state': 'paused', 'expected_episode': 0})
            engine.advance()
            self.assertIsNone(engine.policy.seen)
            engine.close()
            row = next(iter_ticks(engine.writer.path))
            self.assertEqual(row['population_stats'].shape, (0, 4))
        with self.assertRaisesRegex(ValueError, 'CPU'):
            Engine.open(self.root, self.root, self.root / 'never-created', controller='male-original', device='cuda')
        self.assertFalse((self.root / 'never-created').exists())

    def test_bad_policy_output_does_not_step_world(self):
        engine = self.engine('bad')
        engine.policy.action = (float('nan'), 0.)
        engine.submit({'id': 'step', 'kind': 'step', 'expected_state': 'paused', 'expected_episode': 0})
        engine.advance()
        self.assertEqual(engine.phase, 'failed')
        self.assertEqual(engine.env.calls, 0)
        np.testing.assert_array_equal(engine.env.data.qpos, 0.)

    def test_male_snapshot_validation_is_bounded_copied_and_has_no_retina_fields(self):
        state = {'kind': 'male-reduced-v1', 'hidden': np.zeros((1, 138), np.float32), 'failure_diagnostics': {}}
        hidden, _ = snapshots._male_state(state)
        hidden[0, 0] = 1.
        self.assertEqual(state['hidden'][0, 0], 0.)
        changes = [{'hidden': np.zeros((138,), np.float32)}, {'hidden': np.zeros((1, 138), np.float64)},
                   {'hidden': np.full((1, 138), np.nan, np.float32)}, {'left': None}, {'kind': 'flynn'},
                   {'failure_diagnostics': {'type': 'Error', 'message': 'x' * 513}}]
        for change in changes:
            with self.assertRaises(ValueError):
                snapshots._male_state({**state, **change})
            np.testing.assert_array_equal(state['hidden'], 0.)

    def test_explicit_controller_replacement_and_native_failure_leave_fresh_state(self):
        source = self.engine('source')
        application = source.application_state()
        snapshot = {'application': application}
        same = self.engine('same')
        with patch.object(snapshots, 'restore', side_effect=ValueError('bad male hidden shape')):
            with self.assertRaisesRegex(ValueError, 'hidden'):
                same.restore_branch(snapshot)
        self.assertFalse(same._restored)
        self.assertIsNone(same.parent_run_id)
        np.testing.assert_array_equal(same.env.data.qpos, 0.)
        replacement = self.engine('control', 'male-control')
        with patch.object(snapshots, 'restore', return_value=(replacement.observation, None)) as restore:
            replacement.restore_branch(snapshot, replace_controller=True)
        self.assertTrue(restore.call_args.kwargs['replace_controller'])
        self.assertEqual(replacement.writer.manifest['policy_identity'], identity('male-control'))
        self.assertEqual(replacement.controller, 'male-control')
        self.assertEqual(replacement.parent_run_id, 'source')
        self.assertIsNone(replacement.policy.seen)
        events = [json.loads(line) for line in (replacement.writer.path / 'events.jsonl').read_text().splitlines()]
        self.assertTrue(any(event['kind'] == 'controller_replaced' and event['old'] == 'male-original' and event['new'] == 'male-control' for event in events))

    def test_replay_checks_male_source_identity_without_expanding_legacy_requirements(self):
        base = {'kind': 'environment', 'upstream_commit': 'pinned', 'lock_sha256': 'lock',
                'source_sha256': {key: 'a' for key in replay._RUNTIME}}
        replay._compatible([base], [base], 'manual')
        with self.assertRaisesRegex(ValueError, 'source hashes'):
            replay._compatible([base], [base], 'male-original')
        male = copy.deepcopy(base)
        male['source_sha256'].update({key: 'a' for key in replay._MALE_RUNTIME})
        replay._compatible([male], [male], 'male-original')
        changed = copy.deepcopy(male)
        changed['source_sha256'][replay._MALE_RUNTIME[0]] = 'b'
        with self.assertRaisesRegex(ValueError, 'provenance differs'):
            replay._compatible([male], [changed], 'male-original')

    def test_worker_and_replay_snapshot_registrations_retain_actual_identity(self):
        engine = SimpleNamespace(run_id='a' * 32, phase='paused', env=None, observation=None, policy=None, teacher=None,
            application_state=lambda: {}, revision=0, episode=0, episode_step=0, seed=1,
            scenario='reproduction', texture='checker', controller='male-original',
            writer=SimpleNamespace(manifest={'policy_identity': identity(), 'requested_device': 'cpu'}, event=Mock()))
        config = {'scenario': 'reproduction', 'texture': 'checker', 'controller': 'male-original', 'device': 'cpu', 'seed': 1}
        def save(value, path, **kwargs):
            Path(path).write_bytes(b'pure fixture, not a native snapshot')
        with patch.object(snapshots, 'capture', return_value={}), patch.object(snapshots, 'save_snapshot', side_effect=save):
            worker_path = self.root / 'worker'
            (worker_path / 'snapshots').mkdir(parents=True)
            registry = {}
            worker._snapshot(engine, worker_path, registry, config, initial=True)
            stored = next(iter(registry.values()))['config']['policy_identity']
            self.assertEqual(stored, identity())
            self.assertIsNot(stored, engine.writer.manifest['policy_identity'])
            destination = self.root / 'replay'
            destination.mkdir()
            replay._register_initial(engine, destination)
            replay_index = json.loads((destination / 'snapshots/index.json').read_text())
            self.assertEqual(next(iter(replay_index['snapshots'].values()))['config']['policy_identity'], identity())

    def test_api_derives_identity_and_replacement_drops_source_identity(self):
        from palimpsest.lab import create_app
        supervisor = SimpleNamespace(repo_root=self.root, asset_root=self.root / 'assets', runs_root=self.root / 'runs',
            export_root=self.root / 'exports', active_run_id=None, shutdown=Mock(), start=Mock(return_value='b' * 32),
            snapshot=Mock(return_value=(self.root / 'unused.snp', {'config': {'controller': 'male-original', 'device': 'cpu',
                'scenario': 'reproduction', 'texture': 'checker', 'seed': 1, 'policy_identity': identity()}, 'sha256': 'c' * 64})),
            path=Mock(return_value=self.root / 'source'))
        def resolve(root, assets, controller, expected=None):
            current = identity(controller)
            if expected is not None and expected != current:
                raise ValueError('recorded male policy identity differs')
            return current, {}
        choices = {'controllers': [{'id': name, 'available': True} for name in male_policy.CONTROLLERS]}
        with patch('palimpsest.lab.LabSupervisor', return_value=supervisor), patch.object(profiles, 'list_profiles', return_value=choices), \
                patch.object(male_policy, 'resolve_profile', side_effect=resolve) as resolver, \
                patch.object(snapshots, 'read_snapshot', return_value={'application': {'execution_mode': 'live'}}):
            with TestClient(create_app(self.root, supervisor.asset_root, supervisor.runs_root), base_url='http://127.0.0.1:8765') as client:
                token = client.get('/api/v1/session').json()['token']
                headers = {'X-Palimpsest-Session': token, 'Origin': 'http://127.0.0.1:8765'}
                response = client.post('/api/v1/runs', json={'controller': 'male-original'}, headers=headers)
                self.assertEqual(response.status_code, 202, response.text)
                self.assertEqual(supervisor.start.call_args.args[0]['policy_identity'], identity())
                for body in ({'controller': 'male-original', 'device': 'cuda'}, {'controller': 'male-original', 'scenario': 'memory-passages'},
                             {'controller': 'male-original', 'policy_identity': identity()}, {'controller': 'male-original', 'checkpoint': '/tmp/model'}):
                    self.assertEqual(client.post('/api/v1/runs', json=body, headers=headers).status_code, 400)
                response = client.post('/api/v1/branches', json={'source_run_id': 'a' * 32, 'snapshot_id': 'c' * 32,
                    'controller': 'male-control'}, headers=headers)
                self.assertEqual(response.status_code, 202, response.text)
                self.assertIsNone(resolver.call_args.args[3])
                config = supervisor.start.call_args.args[0]
                self.assertEqual(config['policy_identity'], identity('male-control'))
                self.assertTrue(config['replace_controller'])
                response = client.post('/api/v1/branches', json={'source_run_id': 'a' * 32, 'snapshot_id': 'c' * 32}, headers=headers)
                self.assertEqual(response.status_code, 202, response.text)
                self.assertEqual(resolver.call_args.args[3], identity())
                self.assertFalse(supervisor.start.call_args.args[0]['replace_controller'])
                supervisor.snapshot.return_value[1]['config']['policy_identity'] = {'malformed': True}
                count = supervisor.start.call_count
                response = client.post('/api/v1/branches', json={'source_run_id': 'a' * 32, 'snapshot_id': 'c' * 32}, headers=headers)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(supervisor.start.call_count, count)


if __name__ == '__main__':
    unittest.main()
