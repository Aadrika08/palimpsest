"""Pure symbolic fixtures, not embodied performance evidence."""

import copy
import math
import unittest
from unittest.mock import patch

from palimpsest import memory, memory_task


def bank():
    return {'version': 1, 'facts': [
        {'id': f'fact-{letter}', 'subject_id': f'passage-{letter}',
         'kind': 'passability', 'estimate': None, 'status': 'unknown',
         'associations': [{'cue_id': 'cue', 'relation': relation}],
         'inspection_landmark_id': f'marker-{letter}', 'evidence': None,
         'revision': 0, 'origin': 'initial_unknown'}
        for letter, relation in zip('ab', memory.RELATIONS)]}


def world(token=0):
    return {'cues': [{'id': 'cue', 'xy': [2., 0.], 'state': token}],
            'landmarks': [{'id': 'goal', 'xy': [3., 0.]},
                          {'id': 'marker-a', 'xy': [1., 1.]},
                          {'id': 'marker-b', 'xy': [1., -1.]}],
            'passages': [{'subject_id': 'passage-a', 'inspection_landmark_id': 'marker-a', 'passability': 'blocked'},
                         {'subject_id': 'passage-b', 'inspection_landmark_id': 'marker-b', 'passability': 'open'}],
            'common_goal_id': 'goal'}


class MemoryTaskTests(unittest.TestCase):
    def setUp(self):
        self.task = memory_task

    def state(self, relation='local_cue'):
        return self.task.initialize(bank(), {'version': 1, 'episodes': []},
                                    memory.artifact(relation), 'live')

    def packet(self, tick, token=0, pose=(0., 0., 0.), scene=None, occluders=()):
        return self.task.capture_symbolic(world(token) if scene is None else scene, pose, occluders,
                                          episode_id='live', tick=tick)

    def test_sensor_visibility_never_exposes_hidden_occupancy_or_geometry(self):
        packet = self.packet(0)
        changed = world()
        changed['passages'][0]['passability'] = 'open'
        self.assertEqual(packet, self.packet(0, scene=changed))
        self.assertEqual([p['passability'] for p in packet['passages']], ['unobserved', 'unobserved'])
        self.assertEqual(set(packet), {'version', 'id', 'episode_id', 'tick', 'common_goal_id', 'cues', 'landmarks', 'passages'})
        self.assertAlmostEqual(next(m['bearing_rad'] for m in packet['landmarks'] if m['id'] == 'marker-a'), math.pi / 4)
        close = self.packet(0, pose=(.5, .6, 0.))
        self.assertEqual(close['passages'][0]['passability'], 'blocked')
        hidden = self.packet(0, pose=(.5, .6, 0.), occluders=((.75, .8, .1),))
        self.assertEqual(hidden['passages'][0]['passability'], 'unobserved')
        self.assertNotIn('marker-a', [p['id'] for p in hidden['landmarks']])
        self.assertEqual(self.packet(0, pose=(0., 0., math.pi))['cues'], [])
        far = world()
        far['cues'][0]['xy'] = [4.01, 0.]
        self.assertEqual(self.packet(0, scene=far)['cues'], [])
        tangent = self.packet(0, occluders=((1., .25, .25),))
        self.assertEqual(tangent['cues'], [])
        for pose, occluders in (((float('nan'), 0., 0.), ()), ((0., 0., 0.), ((1., 1., -1.),))):
            with self.assertRaises(ValueError):
                self.packet(0, pose=pose, occluders=occluders)

    def test_no_u_still_assimilates_all_direct_evidence_and_duplicates_are_noops(self):
        initial = self.state(None)
        original = copy.deepcopy(initial)
        packet = self.packet(0, pose=(.5, .6, 0.))
        state, cue, audit = self.task.advance_memory(initial, packet)
        self.assertEqual(initial, original)
        self.assertEqual(state['m']['facts'][0]['estimate'], 'blocked')
        self.assertEqual(state['m']['facts'][0]['status'], 'observed')
        self.assertIsNone(state['active'])
        self.assertEqual(state['e'], original['e'])
        self.assertTrue(audit)
        repeated, repeated_cue, repeated_audit = self.task.advance_memory(state, packet)
        self.assertEqual((repeated, repeated_cue, repeated_audit), (state, cue, []))
        self.assertAlmostEqual(cue[0], 2.5 / math.hypot(2.5, -.6))

    def test_freshness_ids_and_common_goal_cannot_be_rewritten(self):
        state, _, _ = self.task.advance_memory(self.state(), self.packet(0))
        changed = self.packet(0, token=1)
        future = self.packet(2)
        wrong = self.packet(1)
        wrong['passages'][0]['id'] = self.packet(0)['passages'][0]['id']
        goal = self.packet(1)
        goal['common_goal_id'] = 'marker-a'
        conflict = self.packet(1)
        conflict['passages'].append({**conflict['passages'][0], 'passability': 'open'})
        for invalid in (changed, future, wrong, goal, conflict):
            with self.subTest(packet=invalid):
                with self.assertRaises(ValueError):
                    self.task.advance_memory(state, invalid)
        state, _, _ = self.task.advance_memory(state, self.packet(1))
        with self.assertRaises(ValueError):
            self.task.advance_memory(state, self.packet(0))

    def test_consecutive_changes_reinspect_without_preemption_and_can_retry_after_timeout(self):
        state, _, _ = self.task.advance_memory(self.state(), self.packet(0))
        state, cue, audit = self.task.advance_memory(state, self.packet(1, 1))
        self.assertEqual(state['active']['fact_id'], 'fact-a')
        self.assertEqual(state['active']['deadline_tick'], 201)
        self.assertAlmostEqual(cue[0], math.sqrt(.5))
        self.assertAlmostEqual(cue[1], math.sqrt(.5))
        self.assertEqual(state['m']['facts'][0]['status'], 'uncertain')
        self.assertIsNone(state['m']['facts'][0]['estimate'])
        for tick in range(2, 202):
            state, cue, audit = self.task.advance_memory(state, self.packet(tick, 0))
            if tick < 201:
                self.assertEqual(state['active']['deadline_tick'], 201)
        self.assertIsNone(state['active'])
        self.assertEqual(cue, [1., 0.])
        self.assertIn('timeout', [item.get('status') for item in audit])
        state, _, _ = self.task.advance_memory(state, self.packet(202, 1))
        self.assertEqual(state['active']['deadline_tick'], 402)

    def test_visibility_gap_does_not_invent_a_trigger_and_pending_target_waits(self):
        state, _, _ = self.task.advance_memory(self.state(), self.packet(0))
        hidden = world(1)
        hidden['cues'][0]['xy'] = [-2., 0.]
        state, _, _ = self.task.advance_memory(state, self.packet(1, scene=hidden))
        state, _, _ = self.task.advance_memory(state, self.packet(2, 1))
        self.assertIsNone(state['active'])
        blocked = world(0)
        state, cue, _ = self.task.advance_memory(state, self.packet(3, scene=blocked, occluders=((.5, .5, .1),)))
        self.assertEqual(cue, [1., 0.])
        self.assertIsNone(state['active'])
        self.assertEqual(len(state['requests']), 1)
        state, _, _ = self.task.advance_memory(state, self.packet(4, 0))
        self.assertEqual(state['active']['started_tick'], 4)

    def test_fresh_passage_resolves_inspection_missing_required_cue_fails_without_fallback(self):
        state, _, _ = self.task.advance_memory(self.state(), self.packet(0))
        active, _, _ = self.task.advance_memory(state, self.packet(1, 1))
        with self.assertRaises(self.task.CueUnavailable):
            self.task.advance_memory(active, self.packet(2, 1, occluders=((.5, .5, .1),)))
        resolved, _, _ = self.task.advance_memory(active, self.packet(2, 1, pose=(.5, .6, 0.)))
        self.assertIsNone(resolved['active'])
        self.assertEqual(resolved['m']['facts'][0]['estimate'], 'blocked')
        with self.assertRaises(self.task.CueUnavailable):
            self.task.advance_memory(self.state(), self.packet(0, pose=(0., 0., math.pi)))
        self.assertEqual(active['active']['started_tick'], 1)

    def test_reset_preserves_swapped_u_and_inspection_is_bounded(self):
        initial = self.state()
        state, _, _ = self.task.advance_memory(initial, self.packet(0, pose=(.5, .6, 0.)))
        state['u'] = memory.artifact('paired_cue')
        reset = self.task.reset(state, 'next')
        self.assertEqual(reset['m'], initial['m'])
        self.assertEqual((reset['e'], reset['u']), (state['e'], state['u']))
        self.assertEqual((reset['cursor'], reset['active'], reset['requests'], reset['last_decisions']), (None, None, [], []))
        self.assertEqual(reset['episode_id'], 'next')
        inspected = self.task.inspect(state)
        self.assertNotIn('e', inspected)
        self.assertEqual(inspected['hashes']['e'], memory.sha256(state['e']))
        self.assertLessEqual(len(inspected['facts']), 16)
        self.assertLessEqual(len(inspected['recent_decisions']), 8)
        for mutate in (lambda s: s.update(privileged=True),
                       lambda s: s['cursor'].update(tick=True),
                       lambda s: s['detector'].update(tick=99)):
            invalid = copy.deepcopy(state)
            mutate(invalid)
            with self.assertRaises(ValueError):
                self.task.validate_state(invalid)

    def test_malformed_entity_references_fail_validation(self):
        invalid = world()
        invalid['passages'][0]['inspection_landmark_id'] = []
        with self.assertRaises(ValueError):
            self.packet(0, scene=invalid)
        state, _, _ = self.task.advance_memory(self.state(), self.packet(0))
        state, _, _ = self.task.advance_memory(state, self.packet(1, 1))
        state['active']['fact_id'] = []
        with self.assertRaises(ValueError):
            self.task.validate_state(state)

    def test_declared_baselines_share_selection_without_hidden_motor_inputs(self):
        from palimpsest import memory_experiment as experiment
        history = experiment.make_history(0, 'local_cue')
        for condition in experiment.CONDITIONS:
            with self.subTest(condition=condition):
                u = (memory.artifact(method='empty-v1') if condition in
                     ('no-U', 'history-independent', 'traversal', 'retrieval', 'oracle') else
                     memory.artifact('paired_cue' if condition == 'swapped' else 'local_cue'))
                resource = history if condition == 'retrieval' else ['fact-b'] if condition == 'oracle' else None
                config = {'version': 1, 'condition': condition, 'limit': 1,
                          'resource': resource, 'resource_sha256': memory.sha256(resource),
                          'provenance_sha256': '1'*64}
                original = self.task.initialize(bank(), {'version': 1, 'episodes': []}, u, 'live')
                state = self.task.configure_selector(original, config)
                untouched = copy.deepcopy((original, config))
                with patch.object(experiment, 'selection_for_condition', wraps=experiment.selection_for_condition) as dispatch, \
                     patch.object(memory, 'fit', side_effect=AssertionError('Live dispatch cannot fit')):
                    state, _, audit = self.task.advance_memory(state, self.packet(0))
                    # Validator accepts resources without invoking the selector.
                    self.assertEqual(dispatch.call_count, 0)
                    state, bearing, audit = self.task.advance_memory(state, self.packet(1, 1))
                    self.assertEqual(dispatch.call_count, 1)
                target = 'fact-b' if condition in ('swapped', 'oracle') else 'fact-a'
                selected = next(e['selection'] for e in audit if e['kind']=='memory_selection')
                self.assertEqual(selected['target_ids'], [] if condition == 'no-U' else [target])
                self.assertEqual((original, config), untouched)
                self.assertEqual(state['e'], original['e'])
                self.assertEqual(state['u'], u)
                self.assertEqual(self.task.validate_state(state), state)
                reset = self.task.reset(state, 'next')
                self.assertEqual(reset['selector'], config)
                self.assertEqual((reset['version'], reset['cursor'], reset['active']), (2, None, None))
                self.assertEqual(bearing, [1.,0.] if condition=='no-U' else
                                 [math.cos(-math.pi/4 if target=='fact-b' else math.pi/4),
                                  math.sin(-math.pi/4 if target=='fact-b' else math.pi/4)])

    def test_selector_resources_are_bounded_condition_specific_and_hash_bound(self):
        from palimpsest import memory_experiment as experiment
        config = {'version':1, 'condition':'retrieval', 'limit':1,
                  'resource':experiment.make_history(0,'local_cue'),
                  'resource_sha256':'0'*64, 'provenance_sha256':'1'*64}
        config['resource_sha256'] = memory.sha256(config['resource'])
        state = self.task.configure_selector(self.state(None), config)
        self.assertEqual(state['version'], 2)
        for mutate in (lambda c:c.update(condition='own'),
                       lambda c:c.update(resource_sha256='0'*64),
                       lambda c:c.update(provenance_sha256=True),
                       lambda c:c.update(limit=True),
                       lambda c:c.update(limit=2),
                       lambda c:c.update(version=True),
                       lambda c:c.update(resource=None),
                       lambda c:c.update(private_world={'truth':'blocked'})):
            bad = copy.deepcopy(config); mutate(bad)
            with self.assertRaises(ValueError):
                self.task.configure_selector(self.state(None), bad)
        oracle={**config,'condition':'oracle','resource':['missing']}
        oracle['resource_sha256']=memory.sha256(oracle['resource'])
        with self.assertRaises(ValueError):
            self.task.configure_selector(self.state(None),oracle)
        bad=copy.deepcopy(state);bad['selector']['resource']['episodes'][0]['id']='tampered'
        with self.assertRaises(ValueError):self.task.validate_state(bad)
        with patch.object(self.task,'MAX_SELECTOR_BYTES',len(memory.canonical_bytes(config))-1):
            with self.assertRaisesRegex(ValueError,'byte limit'):
                self.task.configure_selector(self.state(None),config)
        legacy=self.state()
        self.assertNotIn('selector',legacy)
        self.assertEqual(self.task.validate_state(legacy),legacy)
        self.assertEqual(self.task.reset(legacy,'next')['version'],1)

    def test_own_dispatch_is_exact_legacy_update_parity(self):
        legacy=self.state()
        configured=self.task.configure_selector(legacy,{'version':1,'condition':'own','limit':1,
            'resource':None,'resource_sha256':memory.sha256(None),'provenance_sha256':'1'*64})
        for packet in (self.packet(0),self.packet(1,1),self.packet(2,1,pose=(.5,.6,0.))):
            legacy,bearing,audit=self.task.advance_memory(legacy,packet)
            configured,other_bearing,other_audit=self.task.advance_memory(configured,packet)
            comparable=copy.deepcopy(configured);comparable.pop('selector');comparable['version']=1
            self.assertEqual((comparable,other_bearing,other_audit),(legacy,bearing,audit))


if __name__ == '__main__':
    unittest.main()
