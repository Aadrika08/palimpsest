"""Frozen geometry and sensor fixtures; no native controller qualification."""
import copy
import importlib
import math
import unittest


class DecisionWorldTests(unittest.TestCase):
    def world(self):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.memory_decision_world'),
                             'memory-v2 world is required')
        return importlib.import_module('palimpsest.memory_decision_world')

    def test_frozen_candidate_has_open_crossings_closed_exclusion_and_no_end_bypass(self):
        world = self.world()
        for seed in (0, 1):
            for mirrored in (False, True):
                case = world.make_case(seed, 'local_cue', 'change', mirrored)
                report = world.geometry_check(case)
                self.assertTrue(report['valid'], report)
                self.assertEqual(len(world.PROFILE['obstacles']), 20)
                self.assertTrue(all(report['checks'].values()), report)
                self.assertEqual(case['profile_sha256'], world.PROFILE_SHA256)
                self.assertTrue(all(f['status'] == 'unknown' and f['evidence'] is None
                                    for f in case['facts']))
                graph = world.public_graph(case)
                self.assertLess(graph['routes'][0]['cost'], graph['routes'][1]['cost'])
                self.assertNotIn('xy', repr(graph))
                self.assertNotIn('closure_subject_id', graph)
                self.assertEqual(graph['routes'][0]['subject_id'], case['closure_subject_id'])
        case = world.make_case(0, 'local_cue', 'null')
        self.assertIsNone(case['closure_subject_id'])
        bad = copy.deepcopy(case)
        bad['start_pose'][0] = 0.
        with self.assertRaises(ValueError):
            world.validate_case(bad)

    def test_packet_v2_arrivals_are_visible_only_and_geometry_never_escapes(self):
        world = self.world()
        from palimpsest import memory_decision as decision
        private = {'cues': [], 'landmarks': [{'id': 'goal', 'xy': [.2, 0.]},
                    {'id': 'hidden', 'xy': [-.2, 0.]}], 'passages': [], 'common_goal_id': 'goal'}
        packet = decision.capture_symbolic(private, [0., 0., 0.], [], episode_id='episode-0', tick=0)
        self.assertEqual(packet['version'], 2)
        self.assertEqual(packet['arrivals'], ['goal'])
        self.assertEqual(packet['landmarks'], [{'id': 'goal', 'bearing_rad': 0.}])
        self.assertFalse(any(word in repr(packet) for word in ('distance', "'xy'", 'yaw')))
        occluded = decision.capture_symbolic(private, [0., 0., 0.], [[.1, 0., .05]], episode_id='episode-0', tick=0)
        self.assertEqual(occluded['arrivals'], [])
        far = copy.deepcopy(private)
        far['landmarks'][0]['xy'] = [.351, 0.]
        self.assertEqual(decision.capture_symbolic(far, [0., 0., 0.], [], episode_id='episode-0', tick=0)['arrivals'], [])

    def test_public_retreat_and_prefix_edges_have_clear_visible_authored_successors(self):
        world = self.world()
        for mirrored in (False, True):
            case = world.make_case(0, 'paired_cue', 'change', mirrored)
            report = world.geometry_check(case)
            self.assertTrue(report['checks']['authored_chains_clear'], report)
            self.assertTrue(report['checks']['authored_successors_forward_visible'], report)
            graph = world.public_graph(case)
            self.assertEqual(graph['acquisition_ids'][-1], graph['decision_landmark_id'])
            self.assertTrue(all(route['retreat_ids'][-1] == graph['decision_landmark_id'] for route in graph['routes']))
