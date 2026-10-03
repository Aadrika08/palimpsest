"""Pure M/E/U protocol checks; no simulation/model imports or qualification."""

import copy
import contextlib
import inspect
import io
import json
from pathlib import Path
import tempfile
import unittest

from palimpsest import memory


def observation(subject='passage-a', value='open', tick=1, episode='live', ident=None):
    return {'id': ident or f'{episode}-{subject}-{tick}', 'episode_id': episode,
            'tick': tick, 'subject_id': subject, 'passability': value}


def trigger(tick=2, episode='live'):
    return {'id': f'{episode}-change-{tick}', 'episode_id': episode, 'tick': tick,
            'kind': 'cue_changed', 'cue_id': 'cue', 'before': 0, 'after': 1,
            'before_observation_id': f'{episode}-cue-{tick-1}',
            'observation_id': f'{episode}-cue-{tick}'}


def bank():
    facts, samples = [], []
    for letter, relation in zip('ab', memory.RELATIONS):
        sample = observation(f'passage-{letter}')
        samples.append(sample)
        facts.append({'id': f'fact-{letter}', 'subject_id': sample['subject_id'],
            'kind': 'passability', 'estimate': 'open', 'status': 'observed',
            'associations': [{'cue_id': 'cue', 'relation': relation}],
            'inspection_landmark_id': f'marker-{letter}',
            'evidence': {key: sample[key] for key in ('id', 'episode_id', 'tick')},
            'revision': 0, 'origin': 'observed'})
    return memory.seed_m(facts, samples)


def history(count=4, changed='local_cue'):
    episodes = []
    for index in range(count):
        episode = f'past-{index}'
        checks = []
        for relation in memory.RELATIONS:
            subject = f'old-{index}-{relation}'
            checks.append({'subject_id': subject, 'relation': relation,
                'before': observation(subject, 'open', 1, episode),
                'after': observation(subject, 'blocked' if relation == changed else 'open', 3, episode)})
        episodes.append({'id': episode, 'trigger': trigger(2, episode), 'checks': checks})
    return {'version': 1, 'episodes': episodes}


class MemoryProtocol(unittest.TestCase):
    def test_cli_fits_bounded_history_and_rejects_invalid_input(self):
        from palimpsest.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'history.json'
            source.write_text(json.dumps(history()))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['memory-fit', str(source)]), 0)
            self.assertEqual(json.loads(output.getvalue()), memory.fit(history()))
            for invalid in ('{"version":1,"episodes":[],"gold":[]}', ' ' * (memory.MAX_STATE_BYTES + 1)):
                source.write_text(invalid)
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(['memory-fit', str(source)]), 1)

    def test_history_fit_transfers_to_new_ids_and_abstains_without_evidence(self):
        e, m, event = history(), bank(), trigger()
        original = copy.deepcopy((e, m, event))
        u = memory.fit(e)
        self.assertEqual(list(inspect.signature(memory.fit).parameters), ['e'])
        self.assertEqual(u['provenance']['history_sha256'], memory.sha256(e))
        self.assertEqual(u['provenance']['support']['local_cue'], {'observed': 4, 'changed': 4})
        self.assertEqual(memory.select(m, event, u)['target_ids'], ['fact-a'])
        self.assertEqual(memory.select(m, event, memory.fit(history(changed='paired_cue')))['target_ids'], ['fact-b'])
        self.assertEqual((e, m, event), original)
        for insufficient in (history(3), history(changed=None)):
            self.assertEqual(memory.fit(insufficient)['payload']['rules'], [])
        unobserved = history()
        unobserved['episodes'][0]['checks'][1]['after']['passability'] = 'unobserved'
        self.assertEqual(memory.fit(unobserved)['payload']['rules'], [])
        self.assertEqual(memory.fit(unobserved)['provenance']['support']['paired_cue']['observed'], 3)
        boundary = history()
        boundary['episodes'][0]['checks'][0]['after']['passability'] = 'open'
        boundary['episodes'][0]['checks'][1]['after']['passability'] = 'blocked'
        self.assertEqual(memory.fit(boundary)['payload']['rules'][0]['relation'], 'local_cue')
        conflicted = history()
        first, second = conflicted['episodes'][0]['checks']
        second['subject_id'] = first['subject_id']
        for key in ('before', 'after'):
            second[key]['subject_id'] = first['subject_id']
        self.assertEqual(memory.fit(conflicted)['payload']['rules'], [])
        self.assertEqual(memory.fit(conflicted)['provenance']['support']['local_cue']['observed'], 3)

    def test_reconsideration_is_not_replacement_and_all_conditions_assimilate(self):
        m, event = bank(), trigger()
        selected = memory.select(m, event, memory.artifact('local_cue'))
        original = copy.deepcopy(m)
        changed, events, requests = memory.revise(m, event, selected, [], episode_id='live', tick=2)
        self.assertEqual(m, original)
        self.assertEqual(changed['facts'][0]['estimate'], 'open')
        self.assertEqual(changed['facts'][0]['status'], 'uncertain')
        self.assertEqual(events[0]['reason'], 'reconsider')
        self.assertEqual(len(requests), 1)
        again, repeated, requests = memory.revise(changed, event, selected, [], episode_id='live', tick=2)
        self.assertEqual(again, changed)
        self.assertEqual(repeated, [])
        # Task ingestion cursor suppresses the repeated deterministic request.
        self.assertEqual(requests, [{'event_id': event['id'], 'fact_id': 'fact-a', 'requested_tick': 2}])
        later = trigger(4)
        later_selection = memory.select(changed, later, memory.artifact('local_cue'))
        _, _, requests = memory.revise(changed, later, later_selection, [], episode_id='live', tick=4)
        self.assertEqual(requests, [{'event_id': later['id'], 'fact_id': 'fact-a', 'requested_tick': 4}])
        samples = [observation('passage-a', 'blocked', 2), observation('passage-b', 'blocked', 2)]
        revised, events, requests = memory.revise(m, event, selected, samples, episode_id='live', tick=2)
        self.assertEqual(requests, [])
        self.assertTrue(all(f['estimate'] == 'blocked' and f['status'] == 'observed' for f in revised['facts']))
        no_u = memory.select(m, event, memory.artifact(method='empty-v1'))
        unguided, _, requests = memory.revise(m, event, no_u, samples, episode_id='live', tick=2)
        self.assertEqual(requests, [])
        self.assertEqual([f['estimate'] for f in unguided['facts']], ['blocked', 'blocked'])
        unchanged, _, _ = memory.revise(m, None, {'event_id': None, 'target_ids': [], 'reason': 'no_rule'},
            [observation(tick=2)], episode_id='live', tick=2)
        self.assertEqual(unchanged['facts'][0]['revision'], 0)
        self.assertEqual(unchanged['facts'][0]['evidence']['tick'], 2)
        duplicate, events, requests = memory.revise(unchanged, event, selected,
            [observation(tick=2), observation(tick=2)], episode_id='live', tick=2)
        self.assertEqual((duplicate, events, requests), (unchanged, [], []))

    def test_stale_future_wrong_episode_unobserved_and_conflicted_live_evidence(self):
        m, event = bank(), trigger()
        selection = memory.select(m, event, memory.artifact('local_cue'))
        for invalid in (observation(tick=3), observation(tick=2, episode='other')):
            with self.assertRaises(ValueError):
                memory.revise(m, event, selection, [invalid], episode_id='live', tick=2)
        for invalid in (trigger(3), trigger(2, 'other')):
            with self.assertRaises(ValueError):
                memory.revise(m, invalid, memory.select(m, invalid, memory.artifact('local_cue')), [], episode_id='live', tick=2)
        neutral = {'event_id': None, 'target_ids': [], 'reason': 'no_rule'}
        for sample in (observation(value='blocked', tick=0), observation(value='unobserved', tick=2)):
            changed, events, requests = memory.revise(m, None, neutral, [sample], episode_id='live', tick=2)
            self.assertEqual((changed, events, requests), (m, [], []))
        checks = [observation(value='open', tick=2, ident='one'), observation(value='blocked', tick=2, ident='two')]
        conflicted, events, requests = memory.revise(m, event, selection, checks, episode_id='live', tick=2)
        fact = conflicted['facts'][0]
        self.assertEqual((fact['estimate'], fact['status']), ('open', 'uncertain'))
        self.assertEqual(events[-1]['reason'], 'conflict')
        self.assertEqual(events[-1]['evidence_ids'], ['one', 'two'])
        resolved, _, _ = memory.revise(conflicted, None, neutral, [observation(value='blocked', tick=3)], episode_id='live', tick=3)
        self.assertEqual(resolved['facts'][0]['status'], 'observed')
        retained_conflict, _, _ = memory.revise(m, None, neutral, [observation(value='blocked', tick=1, ident='other-id')], episode_id='live', tick=1)
        self.assertEqual(retained_conflict['facts'][0]['status'], 'uncertain')
        with self.assertRaisesRegex(ValueError, 'reused'):
            memory.revise(m, None, neutral, [observation(value='blocked')], episode_id='live', tick=1)
        with self.assertRaisesRegex(ValueError, 'reused'):
            memory.revise(m, None, neutral, [checks[0], {**checks[0], 'passability': 'blocked'}], episode_id='live', tick=2)

    def test_unknown_initial_state_needs_no_truth_and_known_seeds_need_samples(self):
        m = bank()
        with self.assertRaises(ValueError):
            memory.seed_m(m['facts'], [])
        samples = [observation('passage-a'), observation('passage-b'),
                   observation('passage-a', 'blocked', ident='conflicting-seed')]
        with self.assertRaisesRegex(ValueError, 'Conflicted'):
            memory.seed_m(m['facts'], samples)
        m['facts'][0].update(estimate=None, status='unknown', evidence=None, origin='initial_unknown')
        m = memory.validate_m(m)
        event = trigger()
        selection = memory.select(m, event, memory.artifact('local_cue'))
        uncertain, _, _ = memory.revise(m, event, selection, [], episode_id='live', tick=2)
        self.assertIsNone(uncertain['facts'][0]['estimate'])
        self.assertEqual(uncertain['facts'][0]['origin'], 'initial_unknown')
        observed, _, _ = memory.revise(uncertain, None, {'event_id': None, 'target_ids': [], 'reason': 'no_rule'},
            [observation(tick=3)], episode_id='live', tick=3)
        self.assertEqual(observed['facts'][0]['origin'], 'observed')

    def test_schema_hashes_caps_and_dangling_references_fail_explicitly(self):
        m, event, u = bank(), trigger(), memory.artifact('local_cue')
        self.assertEqual(memory.canonical_bytes({'b': 1, 'a': 'é'}), '{"a":"é","b":1}'.encode())
        for value in (float('nan'), float('inf'), (1,), {1: 'bad'}):
            with self.assertRaises(ValueError):
                memory.canonical_bytes(value)
        for mutate in (lambda x: x.update(gold=[]), lambda x: x['facts'][0].update(revision=True),
                       lambda x: x['facts'].append(copy.deepcopy(x['facts'][0])),
                       lambda x: x.update(facts=x['facts'] * 129),
                       lambda x: x['facts'][0].update(estimate='invented')):
            bad = copy.deepcopy(m)
            mutate(bad)
            with self.assertRaises(ValueError):
                memory.validate_m(bad)
        for mutate in (lambda x: x['payload']['rules'][0].update(value='blocked'),
                       lambda x: x['payload'].update(rules=x['payload']['rules'] * 2),
                       lambda x: x.update(payload_sha256='0' * 64),
                       lambda x: x['provenance'].update(method='x' * 9000)):
            bad = copy.deepcopy(u)
            mutate(bad)
            with self.assertRaises(ValueError):
                memory.validate_u(bad)
        for limit in (-1, True, 9):
            with self.assertRaises(ValueError):
                memory.select(m, event, u, limit=limit)
        self.assertEqual(memory.select(m, event, u, limit=0)['reason'], 'budget')
        with self.assertRaises(ValueError):
            memory.revise(m, event, {'event_id': event['id'], 'target_ids': ['missing'], 'reason': 'matched'}, [], episode_id='live', tick=2)
        bad = history()
        bad['episodes'][0]['checks'][0]['after']['episode_id'] = 'wrong'
        with self.assertRaises(ValueError):
            memory.fit(bad)
        bad = history()
        bad['episodes'] *= 257
        with self.assertRaises(ValueError):
            memory.fit(bad)
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            memory.validate_e({'version': 1, 'episodes': [{'id': 'x' * memory.MAX_STATE_BYTES}]})


if __name__ == '__main__':
    unittest.main()
