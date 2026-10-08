"""Pure contracts for the prospective puck on-policy layout source slice."""
import importlib
import importlib.util
import inspect
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from palimpsest import puck_profile as puck


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_IDS = list(range(7100, 7108))
EXPECTED = [
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7100,
     'split': 'on_policy_collection', 'slot': 0,
     'rover_pose': [-1.25, -0.75, 0.25], 'puck_xy': [-0.5, -0.5],
     'goal_xy': [0.5, -0.5], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7101,
     'split': 'on_policy_collection', 'slot': 1,
     'rover_pose': [-1.375, 0.0, -0.25], 'puck_xy': [-0.5, -0.25],
     'goal_xy': [0.75, 0.0], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7102,
     'split': 'on_policy_collection', 'slot': 2,
     'rover_pose': [-1.5, 0.0, 0.375], 'puck_xy': [-0.5, 0.25],
     'goal_xy': [1.0, 0.0], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7103,
     'split': 'on_policy_collection', 'slot': 3,
     'rover_pose': [-1.25, 0.75, -0.375], 'puck_xy': [-0.5, 0.5],
     'goal_xy': [1.25, 0.5], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7104,
     'split': 'on_policy_development', 'slot': 4,
     'rover_pose': [-1.125, -0.75, 0.5], 'puck_xy': [-0.25, -0.5],
     'goal_xy': [0.875, -0.375], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7105,
     'split': 'on_policy_development', 'slot': 5,
     'rover_pose': [-1.25, 0.0, -0.5], 'puck_xy': [-0.25, -0.25],
     'goal_xy': [1.125, -0.375], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7106,
     'split': 'on_policy_development', 'slot': 6,
     'rover_pose': [-1.0, 0.0, 0.125], 'puck_xy': [-0.25, 0.25],
     'goal_xy': [1.375, 0.375], 'initial_qvel': 'all zeros'},
    {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': 7107,
     'split': 'on_policy_development', 'slot': 7,
     'rover_pose': [-1.125, 0.75, -0.125], 'puck_xy': [-0.25, 0.5],
     'goal_xy': [1.625, 0.375], 'initial_qvel': 'all zeros'},
]


def subject():
    spec = importlib.util.find_spec('palimpsest.puck_on_policy')
    if spec is None:
        raise AssertionError('pure puck on-policy layout minter is missing')
    return importlib.import_module('palimpsest.puck_on_policy')


class StopBeforeNative(Exception):
    pass


class PuckOnPolicyLayoutTests(unittest.TestCase):
    def test_fixed_finite_domain_is_deterministic_one_to_one_and_task_valid(self):
        on_policy = subject()
        first = on_policy.mint_layouts(FIXTURE_IDS)
        second = on_policy.mint_layouts(tuple(FIXTURE_IDS))
        self.assertEqual(first, EXPECTED)
        self.assertEqual(second, EXPECTED)
        self.assertIsNot(first, second)
        self.assertEqual(len({row['seed'] for row in first}), 8)
        scientific = {(tuple(row['rover_pose']), tuple(row['puck_xy']), tuple(row['goal_xy']))
                      for row in first}
        complete = {json.dumps(row, sort_keys=True, separators=(',', ':')) for row in first}
        self.assertEqual((len(scientific), len(complete)), (8, 8))
        for row in first:
            self.assertTrue(all(math.isfinite(value) for value in
                                row['rover_pose'] + row['puck_xy'] + row['goal_xy']))
            self.assertLessEqual(max(map(abs, row['rover_pose'][:2] + row['puck_xy'] + row['goal_xy'])), 5)
            self.assertLessEqual(abs(row['rover_pose'][2]), math.pi)
            self.assertGreater(math.dist(row['rover_pose'][:2], row['puck_xy']), .55)
            self.assertGreater(math.dist(row['puck_xy'], row['goal_xy']), .99)
        first[0]['rover_pose'][0] = 99
        self.assertEqual(on_policy.mint_layouts(FIXTURE_IDS), EXPECTED)

    def test_bad_domains_duplicates_and_occupied_ids_fail_without_writing(self):
        on_policy = subject()
        bad = [
            FIXTURE_IDS[:-1],
            FIXTURE_IDS + [7108],
            [*FIXTURE_IDS[:-1], FIXTURE_IDS[-2]],
            list(reversed(FIXTURE_IDS)),
            [True, *FIXTURE_IDS[1:]],
            [2**31, *FIXTURE_IDS[1:]],
        ]
        with tempfile.TemporaryDirectory() as directory:
            previous = os.getcwd()
            try:
                os.chdir(directory)
                for values in bad:
                    with self.subTest(values=values), self.assertRaises(ValueError):
                        on_policy.mint_layouts(values)
                with self.assertRaisesRegex(ValueError, 'collision'):
                    on_policy.mint_layouts(FIXTURE_IDS, occupied_scene_ids=[7000, 7103, 7200])
            finally:
                os.chdir(previous)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_reserved_roster_is_locked_without_invoking_it(self):
        on_policy = subject()
        protocol = json.loads((ROOT / 'docs/plans/m6-puck-navigation-v3-on-policy-relabeling-protocol.json').read_text())
        reserved = protocol['scene_reservations']['collection'] + protocol['scene_reservations']['development']
        self.assertEqual(tuple(reserved), on_policy.RESERVED_SCENE_IDS)
        with patch.object(on_policy, 'RESERVED_SCENE_IDS', (FIXTURE_IDS[0],)):
            with self.assertRaisesRegex(ValueError, 'locked'):
                on_policy.mint_layouts(FIXTURE_IDS)
            row = EXPECTED[0]
            with self.assertRaisesRegex(ValueError, 'locked'):
                on_policy.admit_layout(row, seed=row['seed'], split=row['split'])

    def test_layout_admission_rejects_tamper_and_returns_fresh_exact_rows(self):
        on_policy = subject()
        for expected in EXPECTED:
            actual = on_policy.admit_layout(expected, seed=expected['seed'], split=expected['split'])
            self.assertEqual(actual, expected)
            self.assertIsNot(actual, expected)
            self.assertIsNot(actual['rover_pose'], expected['rover_pose'])
        mutations = []
        for key, value in (
                ('version', 2), ('kind', 'puck-layout-v1'), ('seed', 7999),
                ('split', 'train'), ('slot', 7), ('initial_qvel', [])):
            changed = json.loads(json.dumps(EXPECTED[0])); changed[key] = value; mutations.append(changed)
        for key, index in (('rover_pose', 0), ('puck_xy', 1), ('goal_xy', 0)):
            changed = json.loads(json.dumps(EXPECTED[0])); changed[key][index] += .125; mutations.append(changed)
        changed = json.loads(json.dumps(EXPECTED[0])); changed['extra'] = True; mutations.append(changed)
        for changed in mutations:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                on_policy.admit_layout(changed, seed=7100, split='on_policy_collection')
        with self.assertRaises(ValueError):
            on_policy.admit_layout(EXPECTED[0], seed=7101, split='on_policy_collection')
        with self.assertRaises(ValueError):
            on_policy.admit_layout(EXPECTED[0], seed=7100, split='on_policy_development')

    def test_reset_seam_is_keyword_only_and_reaches_only_the_existing_native_boundary(self):
        on_policy = subject()
        layout_signature = inspect.signature(puck.layout)
        self.assertEqual(str(layout_signature), '(repo_root, seed, split)')
        signature = inspect.signature(puck.authored_reset)
        self.assertEqual(list(signature.parameters),
                         ['env', 'repo_root', 'seed', 'split', 'episode_id', 'explicit_layout'])
        self.assertEqual(signature.parameters['explicit_layout'].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertIsNone(signature.parameters['explicit_layout'].default)
        with self.assertRaises(TypeError):
            puck.authored_reset(object(), ROOT, 7100, 'on_policy_collection', 'fixture', EXPECTED[0])
        with self.assertRaises(ValueError):
            puck.layout(ROOT, 7100, 'on_policy_collection')

        ranges = np.zeros((65, 2))
        ranges[3:60] = [-1e-6, 1e-6]
        ranges[2] = [-.002, .002]
        model = SimpleNamespace(jnt_range=ranges)
        env = SimpleNamespace(model=model, _puck_profile_identity={
            'protocol_sha256': puck.PROTOCOL_SHA256, 'model_sha256': 'fixture-model'},
            _puck_bindings={})
        fake_mujoco = SimpleNamespace(MjData=lambda _model: (_ for _ in ()).throw(StopBeforeNative()))
        with patch.dict(sys.modules, {'mujoco': fake_mujoco}), \
                patch.object(puck, '_admit_owner', return_value=({}, {})), \
                patch('palimpsest.snapshots._model_digest', return_value='fixture-model'):
            with self.assertRaises(StopBeforeNative):
                puck.authored_reset(env, ROOT, 6000, 'train', 'historical-default')
            with self.assertRaises(StopBeforeNative):
                puck.authored_reset(env, ROOT, 7100, 'on_policy_collection', 'fixture-explicit',
                                    explicit_layout=on_policy.mint_layouts(FIXTURE_IDS)[0])
            with self.assertRaises(ValueError):
                puck.authored_reset(env, ROOT, 7100, 'on_policy_collection', 'fixture-missing')

    def test_fresh_import_does_not_load_torch_or_mujoco(self):
        code = (f"import sys; sys.path.insert(0, {str(ROOT / 'src')!r}); "
                "import palimpsest.puck_on_policy, palimpsest.puck_profile; "
                "bad=sorted({'torch','mujoco'} & set(sys.modules)); "
                "assert not bad, bad")
        result = subprocess.run([sys.executable, '-I', '-c', code], text=True,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
