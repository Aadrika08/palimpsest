"""Pure fixtures for the proposed puck profile; no native dynamics evidence."""
import copy
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from palimpsest.body_profile import GROUND_SUPPORT, ROBOT_GEOMS

ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / 'upstream/fly-gym/environment/mujoco_model_random_obstacles.xml'
NAMES = ['floor', 'wall_n', 'wall_s', 'wall_e', 'wall_w',
         *[f'obstacle{i}' for i in range(20)], *sorted(ROBOT_GEOMS)]
OWNERSHIP = {'base_body_id': 21, 'robot_bodies': [], 'geometries': [
    {'geom_id': i, 'name': name, 'body_id': 21 if name in ROBOT_GEOMS else 0,
     'body_name': 'base' if name in ROBOT_GEOMS else 'world',
     'owner': 'robot' if name in ROBOT_GEOMS else 'world'} for i, name in enumerate(NAMES)]}


def pair(a, b, distance=-.001):
    support = 'floor' in (a, b) and any(n in GROUND_SUPPORT for n in (a, b))
    incident = any(n in ROBOT_GEOMS for n in (a, b))
    return {'geom_ids': [NAMES.index(a), NAMES.index(b)], 'geom_names': [a, b],
            'distance_m': distance, 'allowed_ground_support': support,
            'classification': 'rover_ground_support' if support else
                              'unexpected_robot_contact' if incident else 'world_only',
            'rejects_fit': incident and not support}


def raw_contacts(tick, pairs=()):
    if tick == 0:
        return {'kind': 'initial_forwarded', 'time_s': 0., 'pairs': list(pairs)}
    start = (tick - 1) * .02
    return {'tick': tick - 1, 'start_time_s': start, 'callback_count': 10,
            'stages': [{'stage': i, 'time_s': start + i * .002,
                        'control': [.4, .4], 'pairs': copy.deepcopy(list(pairs))} for i in range(10)],
            'end': {'data_time_s': tick * .02, 'contact_cache_time_s': start + .018,
                    'pairs': copy.deepcopy(list(pairs))},
            'contact': any(p['rejects_fit'] for p in pairs),
            'coverage_passed': True, 'coverage_errors': []}


def world(tick=0, *, rover=(-.55, 0., 0.), puck=(0., 0., .062),
          velocity=(0., 0.), goal=(1., 0.)):
    return {'time_s': tick * .02, 'rover_pose': list(rover), 'puck_xyz': list(puck),
            'puck_velocity_xy': list(velocity), 'goal_xy': list(goal)}


class PuckProfileTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.puck_profile'),
                             'pure puck profile is not implemented')
        self.p = importlib.import_module('palimpsest.puck_profile')

    def contacts(self, tick, pairs=()):
        return self.p.classify_contacts(raw_contacts(tick, pairs), OWNERSHIP,
                                        tick=tick, time_s=tick * .02)

    def test_protocol_and_layouts_are_pinned_not_arbitrary_seed_generation(self):
        protocol = self.p.load_protocol(ROOT)
        self.assertEqual(len(protocol['layouts']), 32)
        splits = {'train': range(6000, 6016), 'recorded_dev': range(6016, 6020),
                  'closed_loop_dev': range(6100, 6104), 'held_out': range(6200, 6208)}
        for split, seeds in splits.items():
            for seed in seeds:
                item = self.p.layout(ROOT, seed, split)
                self.assertEqual((item['seed'], item['split']), (seed, split))
                self.assertGreater(math.dist(item['puck_xy'], item['rover_pose'][:2]), .55)
                self.assertGreater(math.dist(item['puck_xy'], item['goal_xy']), .99)
        self.assertEqual(self.p.layout(ROOT, 6000, 'train')['rover_pose'], [-1.3, -.6, .3])
        for seed, split in [(6000, 'held_out'), (9999, 'train'), (True, 'train')]:
            with self.assertRaises(ValueError):
                self.p.layout(ROOT, seed, split)
        a = self.p.layout(ROOT, 6000, 'train')
        a['goal_xy'][0] = 999
        self.assertEqual(self.p.layout(ROOT, 6000, 'train')['goal_xy'], [.6, -.3])

    def test_protocol_tampering_and_oversized_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'docs/plans/m6-puck-pushing-protocol.json'
            target.parent.mkdir(parents=True)
            target.write_bytes((ROOT / target.relative_to(root)).read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'protocol'):
                self.p.load_protocol(root)
            target.write_bytes(b' ' * (128 * 1024 + 1))
            with self.assertRaisesRegex(ValueError, 'bound'):
                self.p.load_protocol(root)

    @unittest.skipUnless(XML.is_file(), 'initialize the pinned local upstream submodule for XML checks')
    def test_derived_xml_preserves_topology_and_compiles_no_native_model(self):
        before = XML.read_bytes()
        actual = self.p.derive_xml(ROOT)
        self.assertEqual(len(actual), 16778)
        self.assertEqual(hashlib.sha256(actual).hexdigest(),
                         'f6a781836d21c5fd8ffb6b1e35f7ca47586772e11e2b1329695a6965ea5fb06a')
        source, derived = ET.fromstring(before), ET.fromstring(actual)
        self.assertEqual([(e.tag, e.get('name')) for e in source.iter()],
                         [(e.tag, e.get('name')) for e in derived.iter()])
        body = derived.find("./worldbody/body[@name='obstacle0_body']")
        self.assertEqual(body.find('geom').get('size'), '0.25 0.06 0')
        self.assertEqual(body.find('inertial').get('diaginertia'),
                         '0.00420625 0.00420625 0.0078125')
        self.assertEqual([j.get('axis') for j in body.findall('joint')],
                         ['1 0 0', '0 1 0', '0 0 1'])
        self.assertEqual(XML.read_bytes(), before)

    @unittest.skipUnless(XML.is_file(), 'initialize the pinned local upstream submodule for XML checks')
    def test_xml_mutation_duplicate_missing_or_extra_topology_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol = root / 'docs/plans/m6-puck-pushing-protocol.json'
            protocol.parent.mkdir(parents=True)
            protocol.write_bytes((ROOT / protocol.relative_to(root)).read_bytes())
            target = root / XML.relative_to(ROOT)
            target.parent.mkdir(parents=True)
            source = XML.read_bytes()
            for changed in (source.replace(b'obstacle0_body', b'different_body'),
                            source.replace(b'<worldbody>', b'<worldbody><body name="obstacle0_body"/>'),
                            source.replace(b'mass="30"', b'mass="31"', 1), b' ' * 131073):
                target.write_bytes(changed)
                with self.subTest(changed=changed[:30]), self.assertRaises(ValueError):
                    self.p.derive_xml(root)

    def test_native_state_reads_current_qpos_not_stale_derived_positions(self):
        qpos = np.zeros(10, dtype=np.float64)
        qpos[:7] = [1., 2., .2, math.sqrt(.5), 0., 0., math.sqrt(.5)]
        qpos[7:] = [2., 3., -.001]
        data = SimpleNamespace(qpos=qpos, qvel=np.array([.4, .2, 0.]), time=.02,
                               xpos=np.full((30, 3), 999.), geom_xpos=np.full((32, 3), -999.))
        state = self.p.native_state(data, base_qpos_adr=0, puck_qpos_adrs=[7, 8, 9],
                                   puck_dof_adrs=[0, 1, 2], goal_xy=[1., 4.])
        self.assertEqual(state['puck_xyz'], [2., 3., .061])
        self.assertAlmostEqual(state['rover_pose'][2], math.pi / 2)
        vector = self.p.project(state, self.contacts(1, [pair('base_geom', 'obstacle0')]))
        self.assertEqual(vector.dtype, np.float32)
        np.testing.assert_allclose(vector, [1/14, -1/14, 2/14, 0, .1, -.2, 1, 0], atol=1e-7)
        data.qpos[3:7] = 0
        with self.assertRaisesRegex(ValueError, 'quaternion'):
            self.p.native_state(data, base_qpos_adr=0, puck_qpos_adrs=[7, 8, 9],
                                puck_dof_adrs=[0, 1, 2], goal_xy=[1., 4.])

    def test_native_binding_and_array_guards(self):
        data = SimpleNamespace(qpos=np.array([0., 0., .2, 1., 0., 0., 0., 0., 0., 0.]),
                               qvel=np.zeros(3), time=0.)
        good = dict(base_qpos_adr=0, puck_qpos_adrs=[7, 8, 9], puck_dof_adrs=[0, 1, 2], goal_xy=[1., 0.])
        for bad in ({'puck_qpos_adrs': [6, 8, 9]}, {'puck_qpos_adrs': [7, 7, 9]},
                    {'puck_dof_adrs': [0, 1, 3]}, {'base_qpos_adr': True}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.p.native_state(data, **(good | bad))
        data.qvel[0] = float('nan')
        with self.assertRaises(ValueError):
            self.p.native_state(data, **good)

    def test_floor_support_is_not_push_and_rover_contact_is_intended(self):
        summary = self.contacts(1, [pair('obstacle0', 'floor'),
                                    pair('floor', 'left_wheel_geom')])
        self.assertFalse(summary['rover_puck_contact'])
        self.assertFalse(summary['other_robot_contact'])
        self.assertTrue(summary['puck_floor_support'])
        self.assertEqual(summary['failure'], None)
        self.assertAlmostEqual(summary['contact_cache_time_s'], .018)
        self.assertEqual(summary['time_s'], .02)
        touched = self.contacts(1, [pair('obstacle0', 'base_geom', -.02)])
        self.assertTrue(touched['rover_puck_contact'])
        self.assertFalse(touched['other_robot_contact'])
        self.assertIsNone(touched['failure'])
        self.assertEqual(touched['rover_puck_max_penetration_m'], .02)

    def test_initial_cache_is_explicit_and_not_previous_control_interval(self):
        summary = self.contacts(0, [pair('obstacle0', 'floor')])
        self.assertTrue(summary['initial_forwarded'])
        self.assertEqual(summary['contact_cache_time_s'], 0.)
        self.assertEqual(self.p.project(world(), summary).shape, (8,))
        with self.assertRaises(ValueError):
            self.p.classify_contacts(raw_contacts(0), OWNERSHIP, tick=1, time_s=.02)

    def test_contact_failures_are_named_not_body_fit_rejection(self):
        cases = [(pair('floor', 'base_geom'), 'unexpected_robot_contact'),
                 (pair('base_geom', 'wall_n'), 'unexpected_robot_contact'),
                 (pair('obstacle0', 'wall_e'), 'puck_wall_contact'),
                 (pair('obstacle0', 'base_geom', -.02001), 'puck_penetration')]
        for contact, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(self.contacts(1, [contact])['failure'], reason)

    def test_contact_interval_rejects_missing_stale_or_fabricated_endpoint(self):
        original = raw_contacts(1, [pair('obstacle0', 'floor')])
        variants = []
        for key, value in [('tick', 1), ('callback_count', 9), ('coverage_passed', False),
                           ('coverage_errors', ['missing stage']), ('start_time_s', .002)]:
            variants.append(original | {key: value})
        for path, value in [(('stages', 9, 'time_s'), .02),
                            (('end', 'contact_cache_time_s'), .02),
                            (('end', 'data_time_s'), .018),
                            (('stages', 4, 'control'), [.5, .4]),
                            (('end', 'pairs'), [])]:
            changed = copy.deepcopy(original)
            cursor = changed
            for key in path[:-1]: cursor = cursor[key]
            cursor[path[-1]] = value
            variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.p.classify_contacts(changed, OWNERSHIP, tick=1, time_s=.02)

    def test_contact_identity_and_counts_cannot_be_spoofed(self):
        for update in ({'geom_names': ['obstacle0', 'base_geom']},
                       {'geom_ids': [999, 0]}, {'distance_m': float('nan')},
                       {'classification': 'rover_ground_support'}):
            changed = raw_contacts(0, [pair('obstacle0', 'floor') | update])
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.p.classify_contacts(changed, OWNERSHIP, tick=0, time_s=0.)
        changed = copy.deepcopy(OWNERSHIP)
        changed['geometries'][-1]['owner'] = 'world'
        with self.assertRaises(ValueError):
            self.p.classify_contacts(raw_contacts(0), changed, tick=0, time_s=0.)
        with self.assertRaises(ValueError):
            self.contacts(0, [pair('obstacle0', 'floor')] * 129)

    def test_project_rejects_stale_nonfinite_out_of_range_and_privileged_extras(self):
        for changed in (world() | {'time_s': .02}, world(puck=(6., 0., .062)),
                        world(velocity=(2.001, 0.)), world(goal=(float('nan'), 0.)),
                        world() | {'camera': []}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.p.project(changed, self.contacts(0))

    def test_dwell_requires_puck_displacement_prior_contact_and_stopped_speed(self):
        initial = world(puck=(0., 0., .062), goal=(1., 0.))
        state = self.p.initialize(initial, 'episode-a')
        original = copy.deepcopy(state)
        for tick in range(1, 10):
            state, reward = self.p.advance(state, world(tick, puck=(.8, 0., .062), velocity=(.03, 0.)),
                                            self.contacts(tick, [pair('base_geom', 'obstacle0')]), [0., 0.])
        self.assertEqual(state['dwell_ticks'], 9)
        self.assertIsNone(state['reason'])
        state, reward = self.p.advance(state, world(10, puck=(.8, 0., .062)), self.contacts(10), [0., 0.])
        self.assertEqual(state['reason'], 'puck_goal')
        self.assertEqual(reward, 0.)
        self.assertEqual(original['tick'], 0)
        with self.assertRaises(ValueError):
            self.p.advance(state, world(11), self.contacts(11), [0., 0.])
        for no_contact, start in [(True, initial), (False, world(puck=(.7, 0., .062)))]:
            state = self.p.initialize(start, 'episode-b')
            for tick in range(1, 12):
                state, _ = self.p.advance(state, world(tick, puck=(.8, 0., .062)),
                    self.contacts(tick, [pair('obstacle0', 'floor')] if no_contact else
                                  [pair('base_geom', 'obstacle0')]), [0., 0.])
            self.assertIsNone(state['reason'])

    def test_dwell_resets_when_moving_and_rover_goal_alone_does_not_pass(self):
        state = self.p.initialize(world(), 'episode-a')
        state, reward = self.p.advance(state, world(1, puck=(.9, 0., .062)),
                         self.contacts(1, [pair('base_geom', 'obstacle0')]), [0., 0.])
        self.assertAlmostEqual(reward, .9)
        self.assertEqual(state['dwell_ticks'], 1)
        state, _ = self.p.advance(state, world(2, puck=(.9, 0., .062), velocity=(.03001, 0.)),
                                 self.contacts(2), [0., 0.])
        self.assertEqual(state['dwell_ticks'], 0)
        other = self.p.initialize(world(), 'episode-b')
        other, _ = self.p.advance(other, world(1, rover=(1., 0., 0.)), self.contacts(1), [0., 0.])
        self.assertIsNone(other['reason'])

    def test_failures_precede_success_and_final_interval_is_retained(self):
        cases = [(world(1, puck=(5.001, 0., .062)), (), 'out_of_bounds'),
                 (world(1, puck=(0., 0., .083)), (), 'puck_height'),
                 (world(1, velocity=(2.001, 0.)), (), 'puck_speed'),
                 (world(1), [pair('base_geom', 'wall_n')], 'unexpected_robot_contact')]
        for current, pairs, reason in cases:
            before = self.p.initialize(world(), 'episode-a')
            state, _ = self.p.advance(before, current, self.contacts(1, pairs), [0., 0.])
            self.assertEqual((state['tick'], state['reason']), (1, reason))
            self.assertEqual(before['tick'], 0)

    def test_stall_requires_both_bodies_still_and_nonzero_command(self):
        state = self.p.initialize(world(), 'episode-a')
        for tick in range(1, 100):
            state, _ = self.p.advance(state, world(tick), self.contacts(tick), [.2, 0.])
        self.assertIsNone(state['reason'])
        state, _ = self.p.advance(state, world(100), self.contacts(100), [.2, 0.])
        self.assertEqual(state['reason'], 'stalled')
        state = self.p.initialize(world(), 'episode-b')
        for tick in range(1, 101):
            state, _ = self.p.advance(state, world(tick), self.contacts(tick), [.05, 0.])
        self.assertEqual(state['stall_ticks'], 0)
        state, _ = self.p.advance(state, world(101, puck=(.002, 0., .062)),
                                 self.contacts(101), [.2, 0.])
        self.assertEqual(state['stall_ticks'], 0)

    def test_tick_600_is_natural_limit_and_stale_steps_do_not_mutate(self):
        state = self.p.initialize(world(), 'episode-a')
        for tick in range(1, 601):
            state, _ = self.p.advance(state, world(tick), self.contacts(tick), [0., 0.])
        self.assertEqual((state['tick'], state['reason']), (600, 'time_limit'))
        before = self.p.initialize(world(), 'episode-b')
        for action in ([float('nan'), 0.], [.401, 0.], [0.]):
            with self.assertRaises(ValueError):
                self.p.advance(before, world(1), self.contacts(1), action)
        with self.assertRaises(ValueError):
            self.p.advance(before, world(2), self.contacts(2), [0., 0.])
        self.assertEqual(before['tick'], 0)

    def test_corrupted_initial_progress_and_distance_fail_without_mutation(self):
        original = self.p.initialize(world(), 'episode-a')
        for bad in ({'had_contact': True}, {'previous_distance': .5},
                    {'previous_puck_xy': [.5, 0.]}, {'initial_puck_xy': [6., 0.]},
                    {'protocol_sha256': '0'*64}, {'dwell_ticks': 1}):
            changed = original | bad
            retained = copy.deepcopy(changed)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.p.advance(changed, world(1), self.contacts(1), [0., 0.])
            self.assertEqual(changed, retained)

    def test_goal_dwell_cannot_override_failure_in_final_interval(self):
        state = self.p.initialize(world(), 'episode-a')
        for tick in range(1, 10):
            state, _ = self.p.advance(state, world(tick, puck=(.9, 0., .062)),
                self.contacts(tick, [pair('base_geom', 'obstacle0')]), [0., 0.])
        state, _ = self.p.advance(state, world(10, puck=(.9, 0., .062)),
                                 self.contacts(10, [pair('base_geom', 'wall_n')]), [0., 0.])
        self.assertEqual(state['reason'], 'unexpected_robot_contact')
        self.assertEqual(state['tick'], 10)

    def test_nonfinite_derived_reward_and_malformed_ownership_fail(self):
        with self.assertRaises(ValueError):
            self.p.advance(self.p.initialize(world(), 'episode-a'),
                           world(1, puck=(1.7e308, 1.7e308, .062)), self.contacts(1), [0., 0.])
        ownership = copy.deepcopy(OWNERSHIP)
        del ownership['geometries'][0]['owner']
        with self.assertRaises(ValueError):
            self.p.classify_contacts(raw_contacts(0), ownership, tick=0, time_s=0.)

    def test_demonstrator_stop_turn_approach_push_and_zero_aim(self):
        cases = [(world(rover=(-1., 0., 0.)), [.25, 0.]),
                 (world(rover=(-.55, 0., 0.)), [.2, 0.]),
                 (world(rover=(-.55, 0., .12)), [.2, -.12]),
                 (world(rover=(-.55, 0., .120001)), [0., -.120001]),
                 (world(rover=(-1., 0., 1.)), [0., -.4]),
                 (world(goal=(.18, 0.), rover=(0., 0., 2.)), [0., 0.]),
                 (world(puck=(1., 0., .062)), [0., 0.]),
                 (world(rover=(-.55, .06, 0.)), [.2, 0.])]
        for state, expected in cases:
            with self.subTest(state=state):
                action = self.p.demonstrate(state)
                np.testing.assert_allclose(action, expected, rtol=0, atol=1e-12)
                self.assertEqual(self.p.demonstrate(state), action)

    def test_demonstrator_aim_switch_and_lateral_boundaries(self):
        # The behind point is exactly x=0 here, so .08 has no subtraction
        # rounding ambiguity. Crossing it switches back to behind-point aim.
        inside = world(puck=(.55, 0., .062), rover=(.08, 0., 0.))
        self.assertEqual(self.p.demonstrate(inside), [.2, 0.])
        self.assertEqual(self.p.demonstrate(world(puck=(.55, 0., .062),
                           rover=(.080001, 0., 0.))), [0., .4])
        self.assertEqual(self.p.demonstrate(world(rover=(-.55, .060001, 0.))), [.25, 0.])
        # At axial .35 the aim is behind the rover, so the heading rule wins;
        # the axial condition never bypasses alignment.
        self.assertEqual(self.p.demonstrate(world(rover=(-.35, 0., 0.))), [0., .4])
        self.assertEqual(self.p.demonstrate(world(rover=(-.63, 0., 0.))), [.2, 0.])
        self.assertEqual(self.p.demonstrate(world(rover=(-.630001, 0., 0.))), [.25, 0.])

    def test_import_and_pure_use_never_imports_torch_or_mujoco(self):
        code = ('import sys; from palimpsest.puck_profile import load_protocol; '
                'load_protocol(sys.argv[1]); '
                'assert not ({"torch", "mujoco", "glfw"} & set(sys.modules))')
        result = subprocess.run([sys.executable, '-c', code, str(ROOT)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
