"""Scientific-state comparison checks; actual branch execution is tested separately."""

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

from palimpsest.snapshots import SNAPSHOT_KEYS, invariant_hashes, state_digest


class MemoryInvariantTests(unittest.TestCase):
    def test_only_u_and_recording_identity_are_excluded(self):
        import numpy as np

        source = dict.fromkeys(SNAPSHOT_KEYS)
        source.update(native_data=b"physics", integration=np.array([1., 2.]),
                      observation={"camera": np.zeros((2, 2, 3), dtype=np.uint8)},
                      policy={"h": np.array([.25], dtype=np.float32)}, rng={"seed": 4},
                      application={"source_run_id": "source", "event_prefix": {"sha256": "source"},
                          "pending_commands": [], "parameters": {"weights": "original"},
                          "memory": {"m": {"value": "open"}, "e": ["prior observation"],
                                     "u": {"rule": "local_cue"}, "deadline": 200}})
        branch = copy.deepcopy(source)
        branch["application"].update(source_run_id="branch", event_prefix={"sha256": "branch"})
        branch["application"]["memory"]["u"] = {"rule": "paired_cue"}
        self.assertEqual(invariant_hashes(source), invariant_hashes(branch))
        for path, changed in ((('native_data',), b'changed'), (('rng', 'seed'), 5),
                (('application', 'pending_commands'), ['step']),
                (('application', 'parameters', 'weights'), 'changed'),
                (('application', 'memory', 'm'), {'value': 'blocked'}),
                (('application', 'memory', 'e'), []),
                (('application', 'memory', 'deadline'), 201),
                (('policy', 'h'), np.array([.5], dtype=np.float32)),
                (('observation', 'camera'), np.ones((2, 2, 3), dtype=np.uint8))):
            with self.subTest(path=path):
                altered = copy.deepcopy(branch)
                target = altered
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = changed
                self.assertNotEqual(invariant_hashes(source), invariant_hashes(altered))
        self.assertEqual(source['application']['memory']['u'], {'rule': 'local_cue'})
        self.assertEqual(state_digest({'a': {1, 2}, 'b': (1,)}), state_digest({'b': (1,), 'a': {2, 1}}))
        self.assertNotEqual(state_digest([1]), state_digest((1,)))
        self.assertNotEqual(state_digest(np.array([1], dtype='int32')), state_digest(np.array([1], dtype='int64')))
        for invalid in (float('nan'), object(), {1: 'non-string key'}):
            with self.assertRaises((ValueError, TypeError)):
                state_digest(invalid)


class MemoryBranchAdmission(unittest.TestCase):
    def test_validation_precedes_allocation_and_never_closes_source(self):
        from fastapi.testclient import TestClient
        from palimpsest.lab import create_app
        from palimpsest import memory, memory_task, memory_world

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'registered.snp'
            path.write_bytes(b'registered snapshot fixture')
            source, snapshot_id = 'a' * 32, 'b' * 32
            state = memory_task.initialize(memory.seed_m(memory_world.initial_facts(), []),
                {'version': 1, 'episodes': []}, memory.artifact(), 'episode-0')
            snapshot = {'application': {'schema_version': 3, 'scenario': 'memory-passages',
                'source_run_id': source, 'phase': 'paused', 'execution_mode': 'live', 'memory': state,
                'world_task_state': memory_world.initial_state()}}
            config = {'scenario': 'memory-passages', 'controller': 'manual', 'device': 'cpu',
                      'texture': 'checker', 'seed': 0}
            item = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'config': config}
            supervisor = SimpleNamespace(repo_root=root, asset_root=root, export_root=root / 'exports',
                active_run_id=None, workers={}, lock=threading.RLock(), shutdown=Mock(),
                describe=Mock(return_value={'status': 'closed'}), snapshot=Mock(return_value=(path, item)),
                path=Mock(return_value=root / source), start=Mock(return_value='c' * 32), close=Mock())
            profiles = {'controllers': [{'id': 'manual', 'available': True}]}
            with patch('palimpsest.lab.LabSupervisor', return_value=supervisor), \
                    patch('palimpsest.snapshots.read_snapshot', return_value=snapshot), \
                    patch('palimpsest.profiles.list_profiles', return_value=profiles):
                app = create_app(root, root, root)
                with TestClient(app, base_url='http://127.0.0.1:8765') as client:
                    headers = {'X-Palimpsest-Session': client.get('/api/v1/session').json()['token'],
                               'Origin': 'http://127.0.0.1:8765'}
                    body = {'source_run_id': source, 'snapshot_id': snapshot_id, 'u': memory.artifact('local_cue')}
                    def post(value=body):
                        return client.post('/api/v1/memory/branches', json=value, headers=headers)
                    self.assertEqual(post({**body, 'controller': 'teacher'}).status_code, 400)
                    self.assertEqual(post({**body, 'u': {}}).status_code, 400)
                    supervisor.active_run_id = source
                    self.assertEqual(post().status_code, 409)
                    supervisor.active_run_id = None
                    supervisor.describe.return_value = {'status': 'failed'}
                    self.assertEqual(post().status_code, 400)
                    supervisor.describe.return_value = {'status': 'closed'}
                    item['sha256'] = '0' * 64
                    self.assertEqual(post().status_code, 400)
                    item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                    snapshot['application']['execution_mode'] = 'actions'
                    self.assertEqual(post().status_code, 400)
                    self.assertEqual(client.post('/api/v1/branches',
                        json={'source_run_id': source, 'snapshot_id': snapshot_id}, headers=headers).status_code, 400)
                    snapshot['application']['execution_mode'] = 'live'
                    supervisor.start.assert_not_called()
                    self.assertEqual(post().status_code, 202)
                    actual = supervisor.start.call_args.args[0]
                    self.assertEqual(actual['memory_u'], body['u'])
                    self.assertEqual({key: actual[key] for key in config}, config)
                    self.assertNotIn('replace_controller', actual)
                    supervisor.close.assert_not_called()
                    self.assertEqual(path.read_bytes(), b'registered snapshot fixture')


@unittest.skipUnless(os.environ.get('PALIMPSEST_SIMULATION_TESTS') == '1',
                     'opt-in actual upstream EGL memory continuation')
class ActualMemoryBranch(unittest.TestCase):
    def test_u_only_restore_sensor_events_continuation_and_replays(self):
        import numpy as np
        from palimpsest.artifacts import playback
        from palimpsest.engine import Engine
        from palimpsest.memory import artifact
        from palimpsest.records import iter_ticks
        from palimpsest.replay import _register_initial, replay_run
        from palimpsest.snapshots import capture

        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def destination():
                path = root / uuid.uuid4().hex
                path.mkdir()
                return path
            def open_engine(path):
                return Engine.open(repo, root / 'assets', path / 'recording',
                    controller='manual', scenario='memory-passages', seed=19, run_id=path.name)
            def step(engine, identifier):
                engine.submit({'id': identifier, 'kind': 'step', 'expected_state': 'paused',
                               'expected_episode': engine.episode})
                result = engine.advance()
                self.assertEqual(result['phase'], 'paused', engine.last_outcome)
            source = destination()
            engine = open_engine(source)
            try:
                _register_initial(engine, source)
                for tick in range(8):
                    step(engine, f'source-{tick}')
                snapshot = capture(engine.env, engine.observation, application=engine.application_state())
            finally:
                engine.close()
            source_digest = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in source.rglob('*') if p.is_file()}
            original_memory = copy.deepcopy(snapshot['application']['memory'])
            results = []
            for relation in ('local_cue', 'local_cue', 'paired_cue'):
                branch = destination()
                engine = open_engine(branch)
                try:
                    invalid = artifact(relation)
                    invalid['payload']['replacement_value'] = 'blocked'
                    before = engine.application_state()
                    with self.assertRaises(ValueError):
                        engine.restore_memory_branch(snapshot, invalid)
                    action_source = copy.deepcopy(snapshot)
                    action_source['application']['execution_mode'] = 'actions'
                    with self.assertRaisesRegex(ValueError, 'action-replay'):
                        engine.restore_memory_branch(action_source, artifact(relation))
                    self.assertEqual(engine.application_state(), before)
                    engine.restore_memory_branch(snapshot, artifact(relation))
                    current = capture(engine.env, engine.observation, application=engine.application_state())
                    self.assertEqual(invariant_hashes(current), invariant_hashes(snapshot))
                    self.assertEqual(engine.memory['m'], original_memory['m'])
                    self.assertEqual(engine.memory['e'], original_memory['e'])
                    _register_initial(engine, branch)
                    for tick in range(8, 12):
                        step(engine, f'continue-{tick}')
                    self.assertEqual(engine.memory['active']['fact_id'],
                                     'fact-passage-a' if relation == 'local_cue' else 'fact-passage-b')
                    self.assertEqual(engine.world_task_state['gate_result'], 'closed')
                    self.assertTrue(all(fact['estimate'] is None for fact in engine.memory['m']['facts']))
                    results.append((branch, copy.deepcopy(engine.memory)))
                finally:
                    engine.close()
            self.assertEqual(results[0][1], results[1][1])
            for left, right in zip(iter_ticks(results[0][0] / 'recording'), iter_ticks(results[1][0] / 'recording')):
                for field in ('pose', 'next_pose', 'sensors', 'action', 'cam_left', 'cam_right'):
                    np.testing.assert_array_equal(left[field], right[field])
            for branch, memory in results:
                viewed = playback(branch, 0, 10)
                self.assertEqual(viewed['memory']['active']['fact_id'], memory['active']['fact_id'])
                for mode in ('actions', 'policy'):
                    report = replay_run(branch, destination(), mode=mode, repo_root=repo, asset_root=root / 'assets')
                    self.assertEqual(report['status'], 'passed', report)
                    self.assertEqual(report['compared_ticks'], 4)
            self.assertEqual(snapshot['application']['memory'], original_memory)
            self.assertEqual(source_digest, {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in source.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
