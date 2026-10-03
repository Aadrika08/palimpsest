"""Pure fixtures for the proposed puck profile; no native dynamics evidence."""
import copy
import hashlib
import importlib
import importlib.util
import json
import math
import pickle
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
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

    def test_v5_preserves_historical_protocols_and_numeric_task_contract(self):
        pins={'m6-puck-pushing-protocol.json':'8a7f14ee69fe386fe1150b644e71737a5e39ab3c8c4987d7cdf61277796f3bac',
              'm6-puck-pushing-protocol-v2.json':'fd8dbcea35d226bed522d02f27f7bc11149ac77f72ca49838493489e330eb88c',
              'm6-puck-pushing-protocol-v3.json':'7129265b8483e6932a7745f6af77176855139aab398bd229b78430fe8ae87534',
              'm6-puck-pushing-protocol-v4.json':'edf868c868922a3d7a946e705553c7144509a2a6af7f208e399f63346d2b20b9'}
        for name,sha in pins.items():
            self.assertEqual(hashlib.sha256((ROOT/'docs/plans'/name).read_bytes()).hexdigest(),sha)
        old=json.loads((ROOT/'docs/plans/m6-puck-pushing-protocol-v4.json').read_text())
        new=self.p.load_protocol(ROOT)
        self.assertEqual(new['id'],'m6-puck-pushing-plan-v5')
        new['id']=old['id'];new['demonstrator']['id']=old['demonstrator']['id']
        new['demonstrator']['stop_distance_m']=old['demonstrator']['stop_distance_m']
        new['learning_admission']=old['learning_admission']
        self.assertEqual(new,old)

    def test_historical_task_cursors_not_reinterpreted_as_v5(self):
        for old in ('8a7f14ee69fe386fe1150b644e71737a5e39ab3c8c4987d7cdf61277796f3bac',
                    'fd8dbcea35d226bed522d02f27f7bc11149ac77f72ca49838493489e330eb88c',
                    '7129265b8483e6932a7745f6af77176855139aab398bd229b78430fe8ae87534',
                    'edf868c868922a3d7a946e705553c7144509a2a6af7f208e399f63346d2b20b9'):
            state=self.p.initialize(world(),'old-episode');state['protocol_sha256']=old
            with self.assertRaisesRegex(ValueError,'Incompatible'):
                self.p.advance(state,world(1),self.contacts(1),[0.,0.])

    def test_protocol_tampering_and_oversized_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / self.p.PROTOCOL_PATH
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
            protocol = root / self.p.PROTOCOL_PATH
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

    def test_demonstrator_explicit_modes_arrival_alignment_stop_and_bounds(self):
        cases = [(world(rover=(-1., 0., 0.)), 'approach', [.25, 0.], 'approach'),
                 (world(rover=(-.55, 0., 0.)), 'approach', [.2, 0.], 'push'),
                 (world(rover=(-.55, 0., .12)), 'approach', [.2, -.12], 'push'),
                 (world(rover=(-.55, 0., .120001)), 'push', [0., -.120001], 'push'),
                 (world(rover=(-1., 0., 1.)), 'push', [0., -.4], 'approach'),
                 (world(goal=(.18, 0.), rover=(0., 0., 2.)), 'push', [0., 0.], 'push'),
                 (world(puck=(1., 0., .062)), 'approach', [0., 0.], 'approach'),
                 (world(rover=(-.55, .06, 0.)), 'approach', [.2, 0.], 'push'),
                 # Arrival alone cannot admit push; lateral corridor still applies.
                 (world(rover=(-.55, .060001, 0.)), 'approach', [0., -.4], 'approach')]
        for state, mode, expected, next_mode in cases:
            with self.subTest(state=state, mode=mode):
                original=copy.deepcopy(state)
                action, after = self.p.demonstrate(state, mode)
                np.testing.assert_allclose(action, expected, rtol=0, atol=1e-12)
                self.assertEqual(after, next_mode)
                self.assertEqual(self.p.demonstrate(state, mode), (action, after))
                self.assertEqual(state, original)
        # Exact arrival bound, and a ready point just beyond it: mode matters.
        arrived=world(puck=(.55,0.,.062),rover=(.08,0.,0.))
        outside=world(puck=(.55,0.,.062),rover=(.080001,0.,0.))
        self.assertEqual(self.p.demonstrate(arrived,'approach'),([.2,0.],'push'))
        self.assertEqual(self.p.demonstrate(outside,'approach'),([-.25,0.],'approach'))
        self.assertEqual(self.p.demonstrate(outside,'push'),([.2,0.],'push'))
        for mode in (None, True, 1, 'fixed', '', [], 'recover'):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.p.demonstrate(world(),mode)
        with self.assertRaises(TypeError): self.p.demonstrate(world())

    def test_signed_approach_alignment_tie_wrap_and_stop(self):
        # A behind point directly rearward requires reverse, not a pi-radian turn.
        cases=[(world(rover=(-.4,0.,0.)),[-.25,0.]),
               (world(rover=(.4,0.,math.pi),goal=(-1.,0.)),[-.25,0.]),
               (world(rover=(-.4,0.,.12)),[-.25,-.12]),
               (world(rover=(-.4,0.,.120001)),[0.,-.120001]),
               # Exactly equal absolute +/-pi/2 errors choose forward (negative turn).
               (world(puck=(.55,0.,.062),goal=(1.55,0.),rover=(0.,1.,0.)),[0.,-.4]),
               (world(rover=(.45,0.,math.pi-.01)),[.25,.01]),
               (world(rover=(.45,0.,-math.pi+.01)),[.25,-.01]),
               (world(rover=(-.4,0.,0.),goal=(.18,0.)),[0.,0.])]
        for value,expected in cases:
            with self.subTest(value=value):
                action,mode=self.p.demonstrate(value,'approach')
                np.testing.assert_allclose(action,expected,rtol=0,atol=1e-12)
                self.assertEqual(mode,'approach')
        # Existing push travel remains positive at the same rear-target geometry.
        self.assertEqual(self.p.demonstrate(world(rover=(-.4,0.,0.)),'push'),([.2,0.],'push'))

    def test_stop_at_task_radius_is_inclusive_and_retains_carried_mode(self):
        for mode in ('approach', 'push'):
            for distance in (0., .19, math.nextafter(.2, 0.), .2):
                # Geometry outside the ready corridor would otherwise change push mode.
                self.assertEqual(self.p.demonstrate(world(rover=(0.,0.,2.),goal=(distance,0.)),mode),
                                 ([0.,0.],mode))
            outside=world(goal=(math.nextafter(.2, math.inf),0.))
            self.assertEqual(self.p.demonstrate(outside,mode),([.2,0.],'push'))

    def test_v4_retained_reverse_choice_is_turn_only_and_reflected(self):
        # Exact v2 action161/188 worlds, retained audit b2b0cf7c...ca39421.
        first=world(161,rover=(-.10557864384951335,.025780470462970276,.012211822488032919),
                    puck=(.3417668301639983,-.02281179279051964,.060402737920408796),
                    velocity=(.36158623204097373,-.020400357509611246),goal=(1.2,0.))
        returned=world(188,rover=(-.060754749893484276,-.0011209739238077347,-.6506301818704533),
                       puck=(.3880176726862764,-.03851541145471215,.05999990569249625),
                       velocity=(-6.261345744802956e-20,-1.805099186540132e-20),goal=(1.2,0.))
        first['time_s']=3.219999999999867;returned['time_s']=3.7599999999998075
        for reflect in (False,True):
            a,b=copy.deepcopy(first),copy.deepcopy(returned)
            if reflect:
                for value in (a,b):
                    for key in ('rover_pose','puck_xyz','goal_xy','puck_velocity_xy'):
                        value[key][:2]=[-v for v in value[key][:2]]
                    value['rover_pose'][2]+=math.pi
            self.assertEqual(self.p.demonstrate(a,'push'),([0.,.4],'approach'))
            # Corridor re-entry alone must not change the carried recovery mode.
            self.assertEqual(self.p.demonstrate(b,'approach'),([0.,.4],'approach'))
            self.assertEqual(self.p.demonstrate(b,'push'),([0.,.4],'push'))

    def test_retained_v1_tick109_keeps_goal_aim_only_in_push_mode(self):
        x,y,yaw=-.46742095296335834,.016918583801692796,.03331900718597027
        for value in (world(rover=(x,y,yaw),goal=(1.2,0.)),
                      world(rover=(-x,-y,yaw+math.pi),goal=(-1.2,0.))):
            action,mode=self.p.demonstrate(value,'push')
            np.testing.assert_allclose(action,[.2,-yaw],rtol=0,atol=1e-12)
            self.assertEqual(mode,'push')
            action,mode=self.p.demonstrate(value,'approach')
            np.testing.assert_allclose(action,[0.,.16876197027012038],rtol=0,atol=1e-12)
            self.assertEqual(mode,'approach')

    def test_import_and_pure_use_never_imports_torch_or_mujoco(self):
        code = ('import sys; from palimpsest.puck_profile import load_protocol; '
                'load_protocol(sys.argv[1]); '
                'assert not ({"torch", "mujoco", "glfw"} & set(sys.modules))')
        result = subprocess.run([sys.executable, '-c', code, str(ROOT)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


class FixtureModel:
    """Array-only owner fixture, never a MuJoCo model or physics substitute."""
    def __init__(self):
        self.nq, self.nv, self.nu, self.nbody = 71, 70, 2, 26
        self.njnt, self.ngeom, self.ncam, self.nsite, self.na = 65, 32, 2, 1, 0
        self.opt = SimpleNamespace(timestep=.002, integrator=0, disableflags=0, gravity=np.array([0., 0., -9.81]))
        self.names = {'body': ['world', *[f'obstacle{i}_body' for i in range(20)],
                             'base', 'left_wheel', 'right_wheel', 'front_caster_mount', 'caster_wheel'],
                      'joint': [*[f'obstacle{i}_{axis}' for i in range(20) for axis in 'xyz'],
                                'base_free', 'left_hinge', 'right_hinge', 'caster_swivel', 'caster_axle'],
                      'geom': NAMES, 'camera': ['cam_left', 'cam_right'], 'site': ['goal_site'],
                      'actuator': ['left_motor', 'right_motor']}
        shapes = {'body_pos': (26, 3), 'body_quat': (26, 4), 'body_ipos': (26, 3), 'body_iquat': (26, 4),
                  'body_mass': (26,), 'body_inertia': (26, 3), 'body_parentid': (26,),
                  'jnt_type': (65,), 'jnt_bodyid': (65,), 'jnt_axis': (65, 3), 'jnt_pos': (65, 3),
                  'jnt_limited': (65,), 'jnt_range': (65, 2), 'jnt_qposadr': (65,), 'jnt_dofadr': (65,),
                  'geom_type': (32,), 'geom_bodyid': (32,), 'geom_pos': (32, 3), 'geom_quat': (32, 4),
                  'geom_size': (32, 3), 'geom_friction': (32, 3), 'geom_solref': (32, 2),
                  'geom_solimp': (32, 5), 'geom_priority': (32,), 'geom_condim': (32,),
                  'geom_contype': (32,), 'geom_conaffinity': (32,), 'geom_rgba': (32, 4),
                  'geom_aabb': (32, 6), 'geom_rbound': (32,),
                  'site_pos': (1, 3), 'site_size': (1, 3), 'site_type': (1,), 'site_quat': (1, 4),
                  'cam_pos': (2, 3), 'cam_quat': (2, 4), 'cam_fovy': (2,),
                  'actuator_trnid': (2, 2), 'actuator_trntype': (2,), 'actuator_gear': (2, 6),
                  'actuator_ctrlrange': (2, 2), 'actuator_ctrllimited': (2,), 'qpos0': (71,)}
        for name, shape in shapes.items(): setattr(self, name, np.zeros(shape))
        self.body_quat[:, 0] = self.body_iquat[:, 0] = self.geom_quat[:, 0] = 1
        self.site_quat[:, 0] = self.cam_quat[:, 0] = 1
        self.body_pos[1:21, 2] = .8
        self.body_pos[21] = [0, 0, .11]
        self.body_mass[1:21] = 30
        self.body_inertia[1:21] = 2
        self.jnt_type[:60] = 2
        self.jnt_type[61:] = 3
        self.jnt_axis[:60] = np.tile(np.eye(3), (20, 1))
        self.jnt_qposadr[:] = [*range(61), 67, 68, 69, 70]
        self.jnt_dofadr[:] = [*range(61), 66, 67, 68, 69]
        self.jnt_limited[:60] = 1
        self.jnt_range[:60] = [-1e-6, 1e-6]
        self.jnt_bodyid[:60] = np.repeat(np.arange(1, 21), 3)
        puck = NAMES.index('obstacle0')
        self.geom_bodyid[puck] = 1
        self.geom_type[puck] = 5
        self.geom_size[puck] = [.4, .8, 0]
        self.geom_rgba[:] = 1
        self.geom_contype[:] = self.geom_conaffinity[:] = 1
        self.actuator_trnid[:] = [[61, -1], [62, -1]]
        self.actuator_gear[:, 0] = 3
        self.actuator_ctrlrange[:] = [-2, 2]
        self.actuator_ctrllimited[:] = 1
        self.qpos0[60:67] = [0, 0, .11, 1, 0, 0, 0]

    def __getstate__(self):
        return pickle.dumps(self.__dict__, protocol=4)  # Only locally created fixture state.

    def __setstate__(self, raw):
        self.__dict__.update(pickle.loads(raw))

    def geom(self, name): return SimpleNamespace(id=self.names['geom'].index(name))
    def body(self, name): return SimpleNamespace(id=self.names['body'].index(name))


class FixtureData:
    def __init__(self, model):
        self.model = model
        self.qpos, self.qvel = model.qpos0.copy(), np.zeros(model.nv)
        self.ctrl, self.qfrc_applied = np.zeros(model.nu), np.zeros(model.nv)
        self.xfrc_applied = np.zeros((model.nbody, 6))
        self.time = 0.


class FixtureRenderer:
    def __init__(self, model, *, height=128, width=128):
        self.model, self.height, self.width = model, height, width
        self.closed = 0
        self.fail_close = False

    def close(self):
        self.closed += 1
        if self.fail_close: raise RuntimeError('fixture renderer close failure')


class PuckInstallationTests(unittest.TestCase):
    def setUp(self):
        PuckProfileTests.setUp(self)
        self.assertTrue(hasattr(self.p, 'install_fixed_model'), 'staged installation is missing')
        self.assertTrue(hasattr(self.p, 'authored_reset'), 'authored reset adapter is missing')
        self.old = FixtureModel()
        self.new = copy.deepcopy(self.old)
        puck = NAMES.index('obstacle0')
        self.new.body_pos[1] = [0, 0, .062]
        self.new.body_mass[1] = .25
        self.new.body_inertia[1] = [.00420625, .00420625, .0078125]
        self.new.jnt_range[:3] = [[-5.5, 5.5], [-5.5, 5.5], [-.002, .002]]
        self.new.geom_size[puck] = [.25, .06, 0]
        self.new.geom_friction[puck] = [.25, .005, .0001]
        self.new.geom_priority[puck], self.new.geom_condim[puck] = 1, 3
        self.new.geom_solref[puck] = [.004, 1]
        self.new.geom_solimp[puck] = [.95, .99, .001, .5, 2]
        self.new.geom_rgba[puck] = [.9, .7, .1, 1]
        self.new.geom_aabb[puck] = [0, 0, 0, .25, .25, .06]
        self.new.geom_rbound[puck] = math.hypot(.25, .06)
        self.new.site_type[0] = 5
        # MuJoCo 3.3.6 site size has a .005 third default even for cylinders.
        self.new.site_size[0] = [.45, .001, .005]
        self.new.site_pos[0] = [0, 0, .001]
        self.renderers = []
        def renderer(*args, **kwargs):
            result = FixtureRenderer(*args, **kwargs)
            self.renderers.append(result)
            return result
        objects = SimpleNamespace(**{f'mjOBJ_{key.upper()}': key for key in self.old.names})
        self.mj = SimpleNamespace(__version__='3.3.6', mjtObj=objects, MjData=FixtureData,
            MjModel=FixtureModel, Renderer=renderer, get_mjcb_control=lambda: None,
            mj_name2id=lambda model, kind, name: model.names[kind].index(name),
            mj_id2name=lambda model, kind, index: model.names[kind][index],
            MjvScene=lambda model, maxgeom: SimpleNamespace(model=model, maxgeom=maxgeom),
            mj_setConst=lambda model, data: None, mj_resetData=lambda model, data: None,
            mj_forward=lambda model, data: None)
        self.native = patch.dict(sys.modules, {'mujoco': self.mj})
        self.native.start()
        self.addCleanup(self.native.stop)
        self.compile = patch.object(FixtureModel, 'from_xml_string', create=True,
                                    side_effect=lambda xml: self.new)
        self.compile.start()
        self.addCleanup(self.compile.stop)
        from palimpsest.snapshots import _bindings
        self.env = SimpleNamespace(model=self.old, data=FixtureData(self.old),
            renderer=FixtureRenderer(self.old), _view_scn=SimpleNamespace(maxgeom=10000),
            window=None, _view_ctx=None, W=128, H=128, n_obstacles=1, k_nearest=5,
            frame_skip=10, texture_mode='checker', render_mode=None, arena=7., max_steps=600,
            _t=0, _action_scale=2., _obstacle_xy=np.zeros((1, 2), np.float32),
            _goal_xy=np.zeros(2, np.float32), _prev_xy=np.zeros(2, np.float32),
            _last_action=np.zeros(2, np.float32), _speed=0., _stall_steps=0,
            explore_binsize=.2, visited=set(), path_to_draw=None, target_to_draw=None,
            base_body_id=21, planner=SimpleNamespace(_cached_occ='old'))
        vars(self.env).update(_bindings(self.env, self.old))

    def test_install_rebinds_and_closes_only_retired_renderer(self):
        old_renderer = self.env.renderer
        identity = self.p.install_fixed_model(self.env, ROOT)
        self.assertIs(self.env.model, self.new)
        self.assertIs(self.env.data.model, self.new)
        self.assertIs(self.env.renderer.model, self.new)
        self.assertEqual((old_renderer.closed, self.env.renderer.closed), (1, 0))
        self.assertEqual(identity['protocol_sha256'], self.p.PROTOCOL_SHA256)
        self.assertEqual(self.env._puck_bindings['puck_qpos_adrs'], [0, 1, 2])
        np.testing.assert_array_equal(self.env.model.geom_contype[NAMES.index('obstacle1'):NAMES.index('obstacle19')+1], 0)
        with self.assertRaises(ValueError): self.p.install_fixed_model(self.env, ROOT)

    def test_constructor_goal_outside_task_domain_is_admitted_before_authored_reset(self):
        # The pinned arena=7 reset samples each goal coordinate in [-5.5, 5.5].
        goal = [5.25, -5.25]
        self.env._goal_xy[:] = goal
        self.old.site_pos[self.env.goal_site_id, :2] = goal
        with self.assertRaisesRegex(ValueError, 'Goal outside fixed arena'):
            self.p.native_state(self.env.data, base_qpos_adr=60,
                puck_qpos_adrs=[0, 1, 2], puck_dof_adrs=[0, 1, 2], goal_xy=goal)
        self.p.install_fixed_model(self.env, ROOT)
        state = self.p.authored_reset(self.env, ROOT, 5990, 'mechanics', 'construction-only')
        self.assertEqual(state['tick'], 0)
        np.testing.assert_array_equal(self.env._goal_xy, np.asarray([1.2, 0.], np.float32))

    def test_constructor_goal_outside_pinned_reset_domain_is_rejected_before_compile(self):
        for goal in ([5.5001, 0.], [0., -5.5001]):
            self.env._goal_xy[:] = goal
            self.old.site_pos[self.env.goal_site_id, :2] = self.env._goal_xy
            with self.subTest(goal=goal), self.assertRaisesRegex(ValueError, 'constructor reset domain'):
                self.p.install_fixed_model(self.env, ROOT)
        self.assertIs(self.env.model, self.old)
        self.assertEqual(self.renderers, [])

    def test_constructor_admission_still_rejects_nonunit_native_quaternion(self):
        self.env.data.qpos[63:67] = [2., 0., 0., 0.]
        with self.assertRaisesRegex(ValueError, 'Unit base quaternion'):
            self.p.install_fixed_model(self.env, ROOT)
        self.assertIs(self.env.model, self.old)
        self.assertEqual(self.renderers, [])

    def test_install_rejects_live_wrong_settings_or_stale_ids_before_compile(self):
        original = vars(self.env).copy()
        for key, value in [('W', 84), ('n_obstacles', 2), ('_t', 1), ('window', object()),
                           ('cam_left_id', 1), ('_action_scale', 3.)]:
            setattr(self.env, key, value)
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.p.install_fixed_model(self.env, ROOT)
            vars(self.env).clear()
            vars(self.env).update(original)
        self.assertEqual(self.renderers, [])

    def test_staged_structural_or_transform_changes_leave_old_owner_intact(self):
        for field, index, value in [('nq', None, 72), ('body_mass', 1, .26),
                                  ('geom_aabb', (NAMES.index('obstacle0'), 5), .8),
                                  ('actuator_gear', (0, 0), 4), ('cam_pos', (0, 0), .5),
                                  ('jnt_axis', (0, 0), 0), ('jnt_range', (0, 1), 5.4)]:
            baseline = copy.deepcopy(self.new)
            if index is None: setattr(self.new, field, value)
            else: getattr(self.new, field)[index] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.p.install_fixed_model(self.env, ROOT)
            self.assertIs(self.env.model, self.old)
            self.assertEqual(self.env.renderer.closed, 0)
            self.new = baseline

    def test_scene_allocation_failure_closes_staged_renderer_only(self):
        self.mj.MjvScene = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('scene failure'))
        with self.assertRaisesRegex(RuntimeError, 'scene failure'):
            self.p.install_fixed_model(self.env, ROOT)
        self.assertIs(self.env.model, self.old)
        self.assertEqual(self.env.renderer.closed, 0)
        self.assertEqual([r.closed for r in self.renderers], [1])

    def test_wrong_staged_renderer_and_callback_are_rejected_without_commit(self):
        self.mj.get_mjcb_control = lambda: object()
        with self.assertRaises(ValueError): self.p.install_fixed_model(self.env, ROOT)
        self.assertEqual(self.renderers, [])
        self.mj.get_mjcb_control = lambda: None
        def wrong_renderer(model, **kwargs):
            result = FixtureRenderer(model, height=64)
            self.renderers.append(result)
            return result
        self.mj.Renderer = wrong_renderer
        with self.assertRaises(ValueError): self.p.install_fixed_model(self.env, ROOT)
        self.assertIs(self.env.model, self.old)
        self.assertEqual((self.env.renderer.closed, self.renderers[0].closed), (0, 1))

    def test_old_renderer_close_failure_is_terminal_after_owner_commit(self):
        old_renderer = self.env.renderer
        old_renderer.fail_close = True
        with self.assertRaisesRegex(RuntimeError, 'close failure'):
            self.p.install_fixed_model(self.env, ROOT)
        self.assertIs(self.env.model, self.new)
        self.assertEqual((old_renderer.closed, self.env.renderer.closed), (1, 0))
        self.env.renderer.close()  # The terminal caller still owns the new renderer.

    def test_authored_reset_replaces_reset_locks_at_zero_time_without_step(self):
        self.p.install_fixed_model(self.env, ROOT)
        self.env.model.jnt_range[:2] = [[1.1, 1.2], [2.1, 2.2]]
        self.env.model.geom_rgba[NAMES.index('obstacle0')] = .5
        old_data = self.env.data
        state = self.p.authored_reset(self.env, ROOT, 6000, 'train', 'episode-puck')
        self.assertIsNot(self.env.data, old_data)
        np.testing.assert_array_equal(self.env.data.qpos[:3], [-.4, -.3, 0.])
        np.testing.assert_array_equal(self.env.data.qpos[60:63], [-1.3, -.6, .1])
        np.testing.assert_array_equal(self.env.model.jnt_range[:3], [[-5.5, 5.5], [-5.5, 5.5], [-.002, .002]])
        self.assertEqual((state['tick'], state['episode_id']), (0, 'episode-puck'))
        self.assertEqual(self.env.data.time, 0.)
        self.assertTrue(np.all(self.env.data.ctrl == 0) and np.all(self.env.data.qvel == 0))
        self.assertIsNone(self.env.planner._cached_occ)

    def test_authored_reset_rejects_layout_before_mutation_and_rolls_back_forward_failure(self):
        self.p.install_fixed_model(self.env, ROOT)
        model, data = self.env.model, self.env.data
        arrays = {key: getattr(model, key).copy() for key in ('jnt_range', 'geom_rgba', 'site_pos')}
        self.mj.mj_forward = lambda *args: (_ for _ in ()).throw(RuntimeError('forward failure'))
        for seed, split, error in [(6000, 'held_out', ValueError), (6000, 'train', RuntimeError)]:
            with self.assertRaises(error):
                self.p.authored_reset(self.env, ROOT, seed, split, 'episode-puck')
            self.assertIs(self.env.data, data)
            for key, value in arrays.items(): np.testing.assert_array_equal(getattr(model, key), value)
        self.env.data.time = .02
        with self.assertRaises(ValueError):
            self.p.authored_reset(self.env, ROOT, 6000, 'train', 'episode-puck')

    def test_authored_reset_rejects_changed_non_puck_range(self):
        self.p.install_fixed_model(self.env, ROOT)
        self.env.model.jnt_range[3] = [-1., 1.]
        with self.assertRaises(ValueError):
            self.p.authored_reset(self.env, ROOT, 6000, 'train', 'episode-puck')


if __name__ == '__main__':
    unittest.main()
