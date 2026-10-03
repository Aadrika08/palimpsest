import os
from pathlib import Path
import tempfile
import unittest
from palimpsest.profiles import SCENARIOS, validate


class ProfileTests(unittest.TestCase):
    def test_reproduction_dimensions_and_explicit_texture_variation(self):
        profile = validate('reproduction', 'checker', 'flynn')
        self.assertEqual((profile['width'], profile['height'], profile['n_obstacles'], profile['arena'], profile['max_steps']),
                         (128, 128, 20, 7., 600))
        for name in SCENARIOS:
            self.assertEqual(validate(name, 'checker', 'manual')['id'], name)
        self.assertEqual(validate('sparse-navigation', 'checker', 'teacher')['n_obstacles'], 5)
        self.assertEqual(validate('texture-variation', 'realistic', 'flynn')['texture'], 'realistic')
        for args in [('reproduction', 'realistic', 'flynn'), ('unknown', 'checker', 'manual'),
                     ('memory-passages', 'checker', 'teacher'),
                     ('reproduction', 'checker', 'replacement'), ('reproduction', 'unknown', 'manual')]:
            with self.assertRaises(ValueError):
                validate(*args)


@unittest.skipUnless(os.environ.get('PALIMPSEST_SIMULATION_TESTS') == '1', 'actual EGL scene checks are opt-in')
class ActualScenarios(unittest.TestCase):
    def test_all_scenarios_masks_and_explicit_controller_replacement(self):
        import numpy as np
        from palimpsest.engine import Engine
        from palimpsest.snapshots import capture
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            for index, scenario in enumerate(SCENARIOS):
                texture = 'realistic' if scenario == 'texture-variation' else 'checker'
                engine = Engine.open(root, root / 'data/assets/flynn', Path(directory) / str(index),
                                     scenario=scenario, texture=texture, seed=validate(scenario, texture, 'manual').get('seed', 0))
                try:
                    self.assertEqual(len(engine.world()['obstacles']), 5 if scenario == 'sparse-navigation' else 20)
                    if scenario == 'sparse-navigation':
                        for number in range(5, 20):
                            geom = engine.env.model.geom(f'obstacle{number}').id
                            self.assertEqual(engine.env.model.geom_contype[geom], 0)
                            self.assertEqual(engine.env.model.geom_conaffinity[geom], 0)
                            self.assertEqual(engine.env.model.geom_rgba[geom, 3], 0)
                            self.assertGreater(engine.env.data.geom_xpos[geom, 0], engine.env.arena)
                    engine.submit({'id': 'mask', 'kind': 'set_eyes', 'expected_state': 'paused',
                        'expected_episode': 0, 'payload': {'left': False, 'right': True}})
                    engine.advance()
                    engine.submit({'id': 'step', 'kind': 'step', 'expected_state': 'paused', 'expected_episode': 0})
                    self.assertEqual(engine.advance()['phase'], 'paused')
                    self.assertTrue((engine.last_transition['cam_left'] == 0).all())
                    if scenario == 'reproduction':
                        snapshot = capture(engine.env, engine.observation, application=engine.application_state())
                        world, rng, source_id = engine.world(), engine.env.np_random.bit_generator.state, engine.run_id
                finally:
                    engine.close()
            branch = Engine.open(root, root / 'data/assets/flynn', Path(directory) / 'replacement', controller='teacher')
            try:
                branch.restore_branch(snapshot, replace_controller=True)
                np.testing.assert_array_equal(branch.world()['pose'], world['pose'])
                self.assertEqual(branch.writer.manifest['initial_world'], world)
                self.assertEqual(branch.eyes, {'left': False, 'right': True})
                self.assertEqual(branch.env.np_random.bit_generator.state, rng)
                self.assertIsNone(branch.teacher._rec_phase)
                self.assertEqual(branch.parent_run_id, source_id)
                self.assertEqual(branch.receipts, {})
                branch.submit({'id': 'new-step', 'kind': 'step', 'expected_state': 'paused', 'expected_episode': 0})
                self.assertEqual(branch.advance()['phase'], 'paused')
            finally:
                branch.close()
