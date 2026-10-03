"""Explicitly gated actual CPU/EGL continuation and replay; retains all runs."""
import copy
import hashlib
import json
import os
from pathlib import Path
import time
import unittest
import uuid


@unittest.skipUnless(os.environ.get('PALIMPSEST_MALE_RUNTIME_TESTS') == '1', 'actual male CPU/EGL gate requires a released runtime window')
class ActualMaleRuntime(unittest.TestCase):
    def test_paired_native_continuation_replay_and_explicit_replacement(self):
        import numpy as np
        from palimpsest.engine import Engine
        from palimpsest.male_policy import CONTROLLERS
        from palimpsest.records import iter_ticks
        from palimpsest.replay import _register_initial, replay_run
        from palimpsest.snapshots import capture
        root = Path(__file__).resolve().parents[1]
        if not os.environ.get('PALIMPSEST_MALE_RUNTIME_OUTPUT'):
            self.fail('Set a new PALIMPSEST_MALE_RUNTIME_OUTPUT directory to retain actual evidence')
        output = Path(os.environ['PALIMPSEST_MALE_RUNTIME_OUTPUT']).absolute()
        output.mkdir(parents=True, exist_ok=False)
        assets = Path(os.environ.get('PALIMPSEST_TEST_ASSETS', root / 'data/assets/flynn'))
        paths = [*sorted((root / 'src/palimpsest').glob('*.py')), root / 'data/manifests/male-reduced-policy-v1.json',
                 root / 'data/manifests/malecns-reduced-neighborhood-v1.json', root / 'uv.lock', Path(__file__)]
        def hashes():
            return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        report = {'status': 'running', 'scope': 'bounded CPU/EGL mechanism continuation, no navigation/topology-benefit claim',
                  'qualification_claims': [], 'sources_before': hashes(), 'variants': {}, 'asset_root': str(assets)}
        started = time.monotonic()
        def destination():
            path = output / uuid.uuid4().hex
            path.mkdir()
            return path
        def open_engine(path, controller, expected=None):
            return Engine.open(root, assets, path / 'recording', controller=controller, seed=116, device='cpu',
                               run_id=path.name, expected_policy_identity=expected, max_bytes=32 * 1024**2)
        def step(engine, name):
            engine.submit({'id': name, 'kind': 'step', 'expected_state': 'paused',
                           'expected_episode': engine.episode, 'expected_revision': engine.revision})
            engine.advance()
            self.assertEqual(engine.phase, 'paused', engine.last_outcome)
        original_snapshot = None
        try:
            for controller in CONTROLLERS:
                source_path = destination()
                source = open_engine(source_path, controller)
                detail = {'source_run': source_path.name, 'identity': source.writer.manifest['policy_identity']}
                report['variants'][controller] = detail
                try:
                    _register_initial(source, source_path)
                    step(source, 'before-snapshot')
                    snapshot = capture(source.env, source.observation, policy=source.policy, application=source.application_state())
                    self.assertEqual(set(snapshot['policy']), {'kind', 'hidden', 'failure_diagnostics'})
                    self.assertEqual(snapshot['policy']['hidden'].shape, (1, 138))
                    if controller == 'male-original':
                        original_snapshot = copy.deepcopy(snapshot)
                    step(source, 'after-snapshot-1')
                    step(source, 'after-snapshot-2')
                    expected_hidden = source.policy.hidden.numpy().copy()
                finally:
                    source.close()
                continuation_path = destination()
                continuation = open_engine(continuation_path, controller, detail['identity'])
                try:
                    initial_world = continuation.env.data.qpos.copy()
                    data_identity = id(continuation.env.data)
                    for changed in ('hidden', 'identity'):
                        broken = copy.deepcopy(snapshot)
                        if changed == 'hidden':
                            broken['policy']['hidden'] = broken['policy']['hidden'].astype(np.float64)
                        else:
                            broken['identity']['policy']['provenance']['checkpoint_sha256'] = '0' * 64
                        with self.assertRaises(ValueError):
                            continuation.restore_branch(broken)
                        np.testing.assert_array_equal(continuation.env.data.qpos, initial_world)
                        self.assertEqual(id(continuation.env.data), data_identity)
                        self.assertFalse(continuation._restored)
                        np.testing.assert_array_equal(continuation.policy.hidden.numpy(), 0.)
                    continuation.restore_branch(snapshot)
                    step(continuation, 'continued-1')
                    step(continuation, 'continued-2')
                    np.testing.assert_allclose(continuation.policy.hidden.numpy(), expected_hidden, atol=1e-6, rtol=1e-6)
                finally:
                    continuation.close()
                expected = list(iter_ticks(source_path / 'recording'))[1:]
                actual = list(iter_ticks(continuation_path / 'recording'))
                self.assertEqual(len(actual), 2)
                for left, right in zip(expected, actual):
                    self.assertEqual(set(left), set(right))
                    for field in set(left) - {'latency', 'step_latency'}:
                        if np.asarray(left[field]).dtype.kind == 'f':
                            np.testing.assert_allclose(left[field], right[field], atol=1e-6, rtol=1e-6, err_msg=field)
                        else:
                            np.testing.assert_array_equal(left[field], right[field], err_msg=field)
                detail.update(continuation_run=continuation_path.name, continuation_ticks=2, malformed_state_and_identity_rejected_before_mutation=True)
                for mode in ('actions', 'policy'):
                    replay_path = destination()
                    replay_report = replay_run(source_path, replay_path, mode=mode, repo_root=root, asset_root=assets)
                    self.assertEqual(replay_report['status'], 'passed', replay_report)
                    self.assertEqual(replay_report['inference_executed'], mode == 'policy')
                    self.assertEqual(replay_report['compared_ticks'], 3)
                    detail[mode + '_replay'] = {'run_id': replay_path.name, 'ticks': replay_report['compared_ticks'], 'status': replay_report['status']}
            replacement_path = destination()
            replacement = open_engine(replacement_path, 'male-control')
            try:
                replacement.restore_branch(original_snapshot, replace_controller=True)
                self.assertEqual(replacement.writer.manifest['policy_identity']['controller'], 'male-control')
                np.testing.assert_array_equal(replacement.policy.hidden.numpy(), 0.)
                step(replacement, 'replacement-step')
            finally:
                replacement.close()
            report['replacement'] = {'run_id': replacement_path.name, 'from': 'male-original', 'to': 'male-control', 'fresh_hidden': True, 'ticks': 1}
            report['status'] = 'passed'
        except BaseException as error:
            report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:4096]})
            raise
        finally:
            report.update(sources_after=hashes(), wall_seconds=time.monotonic() - started)
            report['sources_unchanged'] = report['sources_before'] == report['sources_after']
            if not report['sources_unchanged']:
                report['status'] = 'failed'
            with (output / 'report.json').open('x') as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
        self.assertEqual(report['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
