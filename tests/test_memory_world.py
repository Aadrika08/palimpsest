"""Pure development geometry/schedule checks; no MuJoCo/model execution."""

import copy
import importlib.util
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from palimpsest import memory_world as world


def environment():
    positions = world.validate_layout()
    return SimpleNamespace(n_obstacles=20, obstacle_ids=list(range(20)), arena=7., goal_site_id=0,
        model=SimpleNamespace(geom_type=[5] * 20, geom_size=[[.4, .8, 0.] for _ in range(20)], site_size=[[.25]]),
        data=SimpleNamespace(geom_xpos=[[*xy, .8] for xy in positions]),
        _goal_xy=[-1., 0.], _base_xy=lambda: [-2.5, 0.], _base_yaw=lambda: 0.)


class DevelopmentWorld(unittest.TestCase):
    def test_real_clearance_projection_opens_and_closes_the_local_apertures(self):
        positions = world.validate_layout()
        circles = [[*xy, .4] for xy in positions]
        self.assertEqual(world.passage_status(circles), {'passage-a': 'open', 'passage-b': 'open'})
        for index, subject in enumerate(world.SUBJECTS):
            changed = copy.deepcopy(positions)
            changed[index + 3] = world.CLOSED_GATES[index]
            world.validate_layout(changed)
            actual = world.passage_status([[*xy, .4] for xy in changed])
            self.assertEqual(actual[subject], 'blocked')
            self.assertEqual(actual[world.SUBJECTS[1-index]], 'open')
        # A circle outside the crossing segment only projects its nearby cap.
        posts = [[*xy, .4] for xy in world.POSTS]
        self.assertEqual(world.passage_status(posts + [[1.65, -1., .4]])['passage-a'], 'open')
        self.assertEqual(world.passage_status(posts + [[1.5, -1., .4]])['passage-a'], 'blocked')
        self.assertEqual(world.passage_status(posts + [[10., -1., 1.]])['passage-a'], 'open')
        self.assertTrue(all(f['status'] == 'unknown' and f['estimate'] is None and f['evidence'] is None for f in world.initial_facts()))
        invalid = copy.deepcopy(positions)
        invalid[1] = invalid[0]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            world.validate_layout(invalid)
        invalid = copy.deepcopy(positions)
        invalid[0] = [-2.5, 0.]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            world.validate_layout(invalid)
        invalid = copy.deepcopy(positions)
        invalid[0] = [-1., 0.]
        with self.assertRaisesRegex(ValueError, 'overlap'):
            world.validate_layout(invalid)

    def test_schedule_flips_once_and_logs_geometric_changes_or_explicit_failure(self):
        env, state = environment(), world.initial_state(change_tick=1)
        original = copy.deepcopy(state)
        state, events = world.advance_world(env, state, 0)
        self.assertEqual(events, [])
        self.assertEqual(original['last_tick'], None)
        def edit(env, intervention):
            env.data.geom_xpos[intervention['index']][:2] = intervention['xy']
            return {'kind': 'move_obstacle', 'index': intervention['index'], 'new': {'xy': intervention['xy']}}
        with patch.object(world, 'apply_intervention', side_effect=edit) as apply:
            state, events = world.advance_world(env, state, 1)
            self.assertEqual(state['gate_result'], 'closed')
            self.assertEqual(events[-1]['before']['passage-a'], 'open')
            self.assertEqual(events[-1]['after']['passage-a'], 'blocked')
            replayed, repeat = world.advance_world(env, state, 1)
            self.assertEqual((replayed, repeat), (state, []))
            self.assertEqual(apply.call_count, 1)
        with self.assertRaisesRegex(ValueError, 'Stale'):
            world.advance_world(env, state, 0)
        with self.assertRaisesRegex(ValueError, 'consecutive'):
            world.advance_world(env, state, 3)
        for bad in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                world.advance_world(env, state, bad)
        env, state = environment(), world.initial_state(change_tick=0)
        with patch.object(world, 'apply_intervention', side_effect=ValueError('Placement intersects rover')):
            failed, events = world.advance_world(env, state, 0)
        self.assertEqual(failed['gate_result'], 'rejected')
        self.assertEqual(events[1]['kind'], 'memory_gate_rejected')
        self.assertEqual(events[-1]['before'], events[-1]['after'])
        self.assertEqual(failed['cue_state'], 1)
        null = world.initial_state(close_subject_id=None, change_tick=0)
        with patch.object(world, 'apply_intervention') as apply:
            null, events = world.advance_world(environment(), null, 0)
            apply.assert_not_called()
        self.assertEqual(null['gate_result'], 'not_requested')
        self.assertEqual(events[-1]['before'], events[-1]['after'])

    def test_sensor_adapter_reads_actual_geometry_and_rejects_incompatible_body(self):
        env, state = environment(), world.initial_state()
        public, pose, circles = world.sensing_inputs(env, state)
        self.assertEqual(set(public), {'cues', 'landmarks', 'passages', 'common_goal_id'})
        self.assertEqual(pose, [-2.5, 0., 0.])
        self.assertEqual(len(circles), 20)
        env.data.geom_xpos[3][:2] = [0., -1.]
        changed, _, _ = world.sensing_inputs(env, state)
        self.assertEqual(changed['passages'][0]['passability'], 'blocked')
        self.assertEqual(state['applied'], False)  # Truth is not the schedule label.
        public['cues'][0]['xy'][0] = 123.
        self.assertEqual(world.sensing_inputs(env, state)[0]['cues'][0]['xy'][0], -1.2)
        env.model.geom_size[0][0] = .2
        with self.assertRaisesRegex(ValueError, 'radius'):
            world.sensing_inputs(env, state)
        with self.assertRaises(ValueError):
            world.validate_state({'extra': 1})
        with self.assertRaises(ValueError):
            world.initial_state(change_tick=True)
        malformed = world.initial_state()
        malformed.update(applied=True, cue_state=1)
        with self.assertRaises(ValueError):
            world.validate_state(malformed)

    @unittest.skipUnless(importlib.util.find_spec('palimpsest.memory_task'), 'pure task sensor not yet available')
    def test_actual_sensor_contract_visibility_locality_and_hidden_changes(self):
        from palimpsest.memory_task import capture_symbolic
        public, pose, circles = world.sensing_inputs(environment(), world.initial_state())
        packet = capture_symbolic(public, pose, circles, episode_id='fixture', tick=0)
        self.assertEqual({item['id'] for item in packet['landmarks']},
                         {'common-goal', 'inspect-passage-a', 'inspect-passage-b'})
        self.assertEqual([p['passability'] for p in packet['passages']], ['unobserved', 'unobserved'])
        nearby = capture_symbolic(public, [-1.2, -1., 0.], circles, episode_id='fixture', tick=0)
        self.assertEqual(nearby['passages'][0]['passability'], 'open')
        hidden = copy.deepcopy(public)
        hidden['passages'][0]['passability'] = 'blocked'
        self.assertEqual(capture_symbolic(hidden, pose, circles, episode_id='fixture', tick=0), packet)
        behind = capture_symbolic(public, [*pose[:2], math.pi], circles, episode_id='fixture', tick=0)
        self.assertEqual(behind['landmarks'], [])


if __name__ == '__main__':
    unittest.main()
