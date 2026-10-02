"""Synthetic recorded fixtures; no simulator or physically acquired history."""
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import numpy as np

from palimpsest import artifacts, memory, memory_task
from palimpsest.records import RunWriter


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        artifacts._CACHE.clear()

    def collect(self, paths):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.memory_history'), 'collector missing')
        return importlib.import_module('palimpsest.memory_history').collect_history(paths)

    def recording(self, *, episodes=1, episode_numbers=None, missing=False, unchanged=False, no_event=False, controller='manual'):
        run = self.root / uuid.uuid4().hex
        writer = RunWriter(run / 'recording', {'run_id': run.name, 'controller': controller,
            'teacher_privileged': controller == 'teacher', 'scenario': {'id': 'memory-passages'}})
        writer.event('engine_opened', run_id=run.name, controller=controller)
        facts = [{'id': name, 'subject_id': subject, 'kind': 'passability', 'estimate': None,
            'status': 'unknown', 'associations': [{'cue_id': 'cue', 'relation': relation}],
            'inspection_landmark_id': landmark, 'evidence': None, 'revision': 0,
            'origin': 'initial_unknown'} for name, subject, relation, landmark in (
                ('fact-a', 'passage-a', 'local_cue', 'inspect-a'),
                ('fact-b', 'passage-b', 'paired_cue', 'inspect-b'))]
        initial = memory.seed_m(facts, [])
        empty = memory.artifact(method='empty-v1')
        writer.manifest['initial_memory'] = {'m': memory.sha256(initial),
            'e': memory.sha256({'version': 1, 'episodes': []}), 'u': memory.sha256(empty)}
        for episode in range(episodes) if episode_numbers is None else episode_numbers:
            state = memory_task.initialize(initial, {'version': 1, 'episodes': []}, empty, f'episode-{episode}')
            writer.event('episode_started', run_id=run.name, episode=episode, episode_step=0, tick=episode * 5,
                world={'arena': 7., 'pose': [0., 0., 0.], 'obstacles': [], 'goal': [1., 0., .1]})
            for tick in range(5):
                packet = memory_task.capture_symbolic({'common_goal_id': 'goal',
                    'cues': [{'id': 'cue', 'xy': [.2, 0.], 'state': int(tick >= 2 and not no_event)}],
                    'landmarks': [{'id': 'goal', 'xy': [1., 0.]}, {'id': 'inspect-a', 'xy': [.5, .2]},
                        {'id': 'inspect-b', 'xy': [.5, -.2]}],
                    'passages': [{'subject_id': 'passage-a', 'inspection_landmark_id': 'inspect-a',
                        'passability': 'open' if tick < 2 or unchanged else 'blocked'},
                        {'subject_id': 'passage-b', 'inspection_landmark_id': 'inspect-b', 'passability': 'open'}]},
                    [0., 0., 0.], [], episode_id=f'episode-{episode}', tick=tick)
                # Fixture omissions are explicit declared samples, not negative labels.
                if tick in (1, 2) or missing and tick >= 2:
                    packet['passages'][0]['passability'] = 'unobserved'
                common = {'run_id': run.name, 'episode': episode, 'episode_step': tick, 'tick': episode * 5 + tick}
                writer.event('memory_sensed', **common, packet=packet)
                state, _, decisions = memory_task.advance_memory(state, packet)
                for decision in decisions:
                    writer.event('memory_decision', **common, detail=decision)
                writer.event('memory_inspected', **common, memory=memory_task.inspect(state))
                writer.tick(episode, tick, pose=np.zeros(3), next_pose=np.zeros(3),
                    sensors=np.array([0., 0., 1., 0.]), reward=np.array(0.), simulation_time=np.array((tick + 1) * .02))
            writer.event('episode_finished', run_id=run.name, episode=episode, episode_step=5, tick=(episode + 1) * 5,
                outcome={'reason': 'fixture_finished'})
        writer.finish({'final_phase': 'paused'})
        return run

    def edit_events(self, run, edit):
        path = run / 'recording/events.jsonl'
        events = [json.loads(line) for line in path.read_text().splitlines()]
        edit(events)
        path.write_text(''.join(json.dumps(event) + '\n' for event in events))

    def test_nearest_visible_samples_fit_and_link_original_evidence(self):
        result = self.collect([self.recording(episodes=4, controller='teacher')])
        self.assertEqual(result['u']['payload']['rules'], [{'trigger': 'cue_changed', 'relation': 'local_cue'}])
        self.assertEqual(result['independence']['scope'], 'no_engine_u_guidance')
        self.assertFalse(result['independence']['operator_blindness_verified'])
        self.assertEqual(result['sources'][0]['controller'], 'teacher')
        self.assertTrue(result['sources'][0]['teacher_privileged'])
        self.assertEqual(result['u']['provenance']['history_sha256'], memory.sha256(result['e']))
        check = result['e']['episodes'][0]['checks'][0]
        self.assertEqual((check['before']['tick'], check['after']['tick']), (0, 3))
        self.assertEqual((check['before']['passability'], check['after']['passability']), ('open', 'blocked'))
        link = result['links'][0]['checks'][0]
        self.assertEqual((link['before']['tick'], link['after']['tick']), (0, 3))
        self.assertIn('event_sequence', link['after'])
        self.assertEqual(result, self.collect([self.root / result['sources'][0]['run_id']]))

    def test_occluded_is_unobserved_and_null_is_unchanged(self):
        missing = self.collect([self.recording(episodes=4, missing=True)])
        self.assertEqual(missing['u']['payload']['rules'], [])
        self.assertEqual(missing['u']['provenance']['support']['local_cue']['observed'], 0)
        self.assertEqual(missing['e']['episodes'][0]['checks'][0]['after']['passability'], 'unobserved')
        self.assertEqual(missing['links'][0]['checks'][0]['gap'], ['after_unobserved'])
        unchanged = self.collect([self.recording(episodes=4, unchanged=True)])
        self.assertEqual(unchanged['u']['payload']['rules'], [])
        self.assertEqual(unchanged['u']['provenance']['support']['local_cue'], {'observed': 4, 'changed': 0})

    def test_run_namespaces_prevent_reused_episode_and_sensor_ids(self):
        first, second = self.recording(), self.recording()
        result = self.collect([second, first])
        self.assertEqual(result, self.collect([first, second]))
        episode_ids = [episode['id'] for episode in result['e']['episodes']]
        self.assertEqual(len(set(episode_ids)), 2)
        self.assertEqual({link['source_episode_id'] for link in result['links']}, {'episode-0'})
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.collect([first, first])

    def test_reader_integrity_and_terminal_state_are_not_bypassed(self):
        run = self.recording()
        chunk = run / 'recording/chunks/000000.npz'
        chunk.write_bytes(chunk.read_bytes() + b'bad')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.collect([run])
        run = self.recording()
        path = run / 'recording/manifest.json'
        manifest = json.loads(path.read_text())
        manifest['status'] = 'running'
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'completed'):
            self.collect([run])

    def test_source_change_during_fitting_rejects_the_bundle(self):
        run = self.recording()
        original_fit = memory.fit
        def change_source(e):
            result = original_fit(e)
            path = run / 'recording/manifest.json'
            path.write_text(path.read_text() + '\n')
            return result
        with patch.object(memory, 'fit', side_effect=change_source):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.collect([run])

    def test_guidance_incomplete_bank_and_hash_mismatches_reject(self):
        for defect in ('u', 'bank', 'hash'):
            run = self.recording()
            def mutate(events):
                inspected = next(e['memory'] for e in events if e['kind'] == 'memory_inspected')
                if defect == 'u':
                    inspected['u'] = memory.artifact('local_cue')
                    inspected['hashes']['u'] = memory.sha256(inspected['u'])
                elif defect == 'bank':
                    inspected['facts_truncated'] = 1
                else:
                    inspected['hashes']['m'] = '0' * 64
            self.edit_events(run, mutate)
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                self.collect([run])

    def test_trigger_requires_consecutive_visible_cue_evidence(self):
        run = self.recording()
        def mutate(events):
            packet = next(e['packet'] for e in events if e['kind'] == 'memory_sensed' and e['episode_step'] == 1)
            packet['cues'] = []
        self.edit_events(run, mutate)
        with self.assertRaisesRegex(ValueError, 'cue|trigger'):
            self.collect([run])

    def test_empty_or_out_of_order_recordings_do_not_establish_acquisition(self):
        run = self.root / uuid.uuid4().hex
        writer = RunWriter(run / 'recording', {'run_id': run.name, 'controller': 'manual',
            'teacher_privileged': False, 'scenario': {'id': 'memory-passages'}})
        writer.event('engine_opened', run_id=run.name, controller='manual')
        writer.finish({'final_phase': 'paused'})
        with self.assertRaisesRegex(ValueError, 'tick'):
            self.collect([run])
        run = self.recording()
        def reverse_boundary(events):
            a = next(i for i, e in enumerate(events) if e['kind'] == 'memory_sensed')
            b = next(i for i, e in enumerate(events) if e['kind'] == 'memory_inspected')
            events[a], events[b] = events[b], events[a]
            for sequence, event in enumerate(events):
                event['sequence'] = sequence
        self.edit_events(run, reverse_boundary)
        with self.assertRaisesRegex(ValueError, 'order'):
            self.collect([run])

    def test_private_world_geometry_does_not_enter_history_or_fitting(self):
        run = self.recording()
        before = self.collect([run])
        def change_world(events):
            next(e['world'] for e in events if e['kind'] == 'episode_started')['obstacles'] = [[.5, 0., .4]]
        self.edit_events(run, change_world)
        after = self.collect([run])
        self.assertEqual(before['e'], after['e'])
        self.assertEqual(before['u'], after['u'])
        self.assertNotEqual(before['sources'][0]['recording_sha256'], after['sources'][0]['recording_sha256'])

    def test_no_trigger_remains_an_audited_gap_and_hidden_goal_route_rejects(self):
        result = self.collect([self.recording(no_event=True)])
        self.assertEqual(result['e']['episodes'], [])
        self.assertEqual(result['u']['payload']['rules'], [])
        self.assertEqual(result['links'][0]['gap'], ['no_observed_trigger'])
        run = self.recording()
        def hide_goal(events):
            packet = next(e['packet'] for e in events if e['kind'] == 'memory_sensed')
            packet['landmarks'] = [landmark for landmark in packet['landmarks'] if landmark['id'] != 'goal']
        self.edit_events(run, hide_goal)
        with self.assertRaisesRegex(ValueError, 'visible|goal'):
            self.collect([run])

    def test_outer_tick_and_all_event_run_ids_bind_recording_lineage(self):
        for defect in ('outer_tick', 'opened_run', 'world_run'):
            run = self.recording(episodes=2)
            def mutate(events):
                if defect == 'outer_tick':
                    next(e for e in events if e['kind'] == 'memory_sensed' and e['episode'] == 1)['tick'] += 1
                else:
                    kind = 'engine_opened' if defect == 'opened_run' else 'episode_started'
                    next(e for e in events if e['kind'] == kind)['run_id'] = uuid.uuid4().hex
            self.edit_events(run, mutate)
            with self.subTest(defect=defect), self.assertRaisesRegex(ValueError, 'tick|run'):
                self.collect([run])
        with self.assertRaisesRegex(ValueError, 'episode'):
            self.collect([self.recording(episode_numbers=[0, 2])])


if __name__ == '__main__':
    unittest.main()
