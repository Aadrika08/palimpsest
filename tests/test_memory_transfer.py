"""Pure transfer preparation checks; fixtures do not establish actual transfer."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import numpy as np

from palimpsest import memory, memory_experiment as experiment


class VerifierBoundaries(unittest.TestCase):
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('verify_memory_transfer',
            self.repo / 'scripts/verify_memory_transfer.py')
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.histories = {role: {'e': experiment.make_history(seed, relation)}
            for role, seed, relation in [('own', 0, 'local_cue'), ('swapped', 9, 'paired_cue')]}
        for role, value in self.histories.items():
            value.update(u=memory.fit(value['e']), path=role+'.json', sha256='0'*64)

    def plan(self, output=None):
        with patch.object(self.runner, 'load_histories', return_value=self.histories):
            return self.runner.make_plan(self.repo, self.root/'assets', output or self.root/'comparison')

    def test_fixed_source_override_is_bounded_and_keeps_continuation_separate(self):
        case = experiment.make_world_case(8, 'local_cue', 'development-test', acquisition=True)
        other = experiment.make_world_case(9, 'paired_cue', 'development-test', acquisition=True)
        pose = [-1.3, .626, math.pi/2]
        schedule = case['acquisition_schedule']
        self.assertEqual(self.runner.source_action(schedule, pose, 199), experiment.acquisition_action(schedule, pose, 199))
        for tick in (200, 299):
            action = self.runner.source_action(schedule, pose, tick)
            self.assertEqual(action, [0., -.35])
            self.assertEqual(action, self.runner.source_action(other['acquisition_schedule'], pose, tick))
        self.assertEqual(self.runner.source_action(schedule, [-1.3,.626,math.pi/20], 299), [0.,0.])
        for tick in (True, -1, 300):
            with self.assertRaises(ValueError):
                self.runner.source_action(schedule, pose, tick)
        self.assertEqual(self.runner.cue_action([1.,0.]), [.65,0.])
        self.assertEqual(self.runner.PROTOCOL['version'], 2)
        self.assertEqual(self.runner.SOURCE_PREPARATION['access'], 'privileged-manual-pose-supervision')
        self.assertFalse(self.runner.SOURCE_PREPARATION['uses_u'])

    def test_visibility_admission_requires_recorded_cues_landmarks_and_evidence(self):
        from palimpsest import memory_task
        case = experiment.make_world_case(8, 'local_cue', 'development-test', acquisition=True)
        world = {'cues':[{'id':case['cue_id'],'xy':case['cue_xy'],'state':0}],
            'landmarks':[{'id':case['common_goal_id'],'xy':case['goal_xy']}] +
                [{'id':f['inspection_landmark_id'],'xy':case['inspection_xy'][i]} for i,f in enumerate(case['facts'])],
            'passages':[{'subject_id':f['subject_id'],'inspection_landmark_id':f['inspection_landmark_id'],
                'passability':'open'} for f in case['facts']], 'common_goal_id':case['common_goal_id']}
        packets = [memory_task.capture_symbolic(world,pose,[],episode_id='episode-0',tick=tick)
            for tick,pose in [(29,[-1.3,-1.1,math.pi/2]),(199,[-1.3,.626,math.pi/2]),
                              (299,[-1.3,.626,math.pi/20])]]
        m = memory.seed_m(case['facts'], [])
        for packet in packets[:2]:
            m = memory.revise(m, None, {'event_id':None,'target_ids':[],'reason':'no_rule'},
                packet['passages'],episode_id='episode-0',tick=packet['tick'])[0]
        state = {'m':m,'episode_id':'episode-0'}
        events = [{'kind':'memory_sensed','episode':0,'episode_step':p['tick'],'tick':p['tick'],'packet':p} for p in packets]
        admitted = self.runner.preparation_packet(events,case,state,299)
        self.assertEqual(admitted,packets[-1])
        self.runner.evidence_backed_source(m,events,'episode-0')
        angle=next(v['bearing_rad'] for v in packets[-1]['landmarks'] if v['id']==case['common_goal_id'])
        state.update(active=None,cursor={'episode_id':'episode-0','tick':299,
            'packet_sha256':memory.sha256(packets[-1]),'common_goal_id':case['common_goal_id'],
            'bearing':[math.cos(angle),math.sin(angle)]}, detector={'tick':299,'cues':[{
                'id':case['cue_id'],'state':0,'observation_id':memory_task._sensor_id('episode-0',299,'cue',case['cue_id'])}]})
        self.runner.packet_cursor(packets[-1],state)
        for section,key,value in [('cursor','packet_sha256','0'*64),('cursor','bearing',[1.,0.]),
                                  ('detector','tick',298)]:
            bad=copy.deepcopy(state)
            bad[section][key]=value
            with self.assertRaises(ValueError):
                self.runner.packet_cursor(packets[-1],bad)
        for mutate in (
            lambda p:p['landmarks'].pop(0),
            lambda p:p['cues'].clear(),
            lambda p:p['passages'][0].__setitem__('passability','open'),
            lambda p:p.__setitem__('tick',298)):
            bad = copy.deepcopy(events)
            mutate(bad[-1]['packet'])
            with self.assertRaises(ValueError):
                self.runner.preparation_packet(bad,case,state,299)
        bad_m = copy.deepcopy(m)
        bad_m['facts'][0]['evidence']['id']='fabricated-evidence'
        with self.assertRaises(ValueError):
            self.runner.evidence_backed_source(bad_m,events,'episode-0')

    def test_source_override_controls_and_declaration_cannot_be_relabelled(self):
        case = experiment.make_world_case(8,'local_cue','development-test',acquisition=True)
        pose=np.array([-1.3,.626,math.pi/2],np.float64)
        rows=[{'tick':t,'pose':pose.copy(),'action':np.array([0.,-.35],np.float64)} for t in range(200,300)]
        events=[{'kind':'source_preparation_input','episode':0,'episode_step':t,'tick':t,
            'pose':pose.tolist(),'action':[0.,-.35], 'source_preparation_sha256':self.runner.SOURCE_PREPARATION_SHA256}
            for t in range(200,300)]
        data={'rows':rows,'events':events}
        self.runner.source_controls(data,case)
        for mutate in (
            lambda d:d['events'].pop(),
            lambda d:d['rows'][0]['action'].__setitem__(0,.65),
            lambda d:d['events'][0]['pose'].__setitem__(2,0.),
            lambda d:d['events'][0].__setitem__('source_preparation_sha256','0'*64)):
            bad=copy.deepcopy(data)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.runner.source_controls(bad,case)
        fixture=self.fixture('anchor')
        self.admit(fixture)
        for mutate in (
            lambda f:f[1]['manifest'].__setitem__('source_preparation_sha256','0'*64),
            lambda f:next(e for e in f[1]['events'] if e['kind']=='source_preparation_declared')
                ['protocol'].__setitem__('uses_u',0),
            lambda f:next(e for e in f[1]['events'] if e['kind']=='source_preparation_declared')
                .__setitem__('sequence',1000)):
            bad=copy.deepcopy(fixture)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.admit(bad)

    def fixture(self, stage='own', *, failed=False):
        job = next(j for j in self.plan()['jobs'] if j['stage']==stage)
        job['expected_non_u'] = {'native': 'fixture-hash'}
        run = Path(job['output'])
        run.mkdir(parents=True)
        u = (memory.artifact(method='empty-v1') if stage in ('source', 'no-U') else
             self.histories['swapped' if stage=='swapped' else 'own']['u'])
        native = {'application': {'world_task_state': {'case': job['case']}, 'event_prefix':{'event_count':1000},
            'memory': {'u': u, 'cursor': {'bearing': [1., 0.],'tick':299,'episode_id':'episode-0',
                'packet_sha256':'0'*64,'common_goal_id':job['case']['common_goal_id']}, 'episode_id':'episode-0',
                       'm':memory.seed_m(job['case']['facts'],[])}}}
        outcome = ({'type': 'CueUnavailable', 'reason': 'runtime_failure',
            'message': 'goal_cue_unavailable: fixture', 'episode': 0, 'steps': 301} if failed else None)
        report = {'status': 'recorded', 'stage': stage, 'run_path': str(run),
            'initial_non_u': job['expected_non_u'], 'final_phase': 'failed' if failed else 'paused',
            'outcome': outcome, 'steps': 300 if stage in ('source', 'anchor') else 301,
            'final_memory': {'requests': [{'fact_id': 'fixture-fact'}] if failed else [], 'active': None}}
        manifest = {'memory_case': job['case'], 'memory_case_sha256': memory.sha256(job['case']),
            'transfer_protocol': self.runner.PROTOCOL, 'transfer_protocol_sha256': self.runner.PROTOCOL_SHA256,
            'transfer_driver_sha256': job['source_identity']['driver_sha256'], 'transfer_stage': stage,
            'source_preparation_protocol':self.runner.SOURCE_PREPARATION,
            'source_preparation_sha256':self.runner.SOURCE_PREPARATION_SHA256,
            'acquisition_schedule_override':self.runner.ACQUISITION_OVERRIDE,
            'controller': 'manual', 'requested_device': 'cpu', 'seed': 8,
            'recording_max_bytes': self.runner.PROTOCOL['recording_max_bytes'],
            'close_reason': 'operator_closed', 'status': 'failed' if failed else 'completed',
            'final_phase': report['final_phase'], 'last_outcome': outcome, 'total_tick': report['steps']}
        events = [{'kind': 'environment', **{k: job['source_identity'][k]
            for k in ('source_sha256', 'lock_sha256', 'upstream_commit')}}]
        rows = [] if stage=='anchor' else [{'episode': 0, 'tick': 300,
            'action': np.array([.65, 0.], dtype=np.float64)}]
        if stage not in ('source', 'anchor'):
            events.append({'kind': 'transfer_driver_input', 'episode': 0, 'episode_step': 300,
                'bearing_tick': 299, 'bearing': [1., 0.], 'action': [.65, 0.]})
            if failed:
                events += [{'kind': 'memory_cue', 'episode_step': 300, 'bearing': [1., 0.]},
                    {'kind': 'transfer_driver_input', 'episode': 0, 'episode_step': 301,
                     'bearing_tick': 300, 'bearing': [1., 0.], 'action': [.65, 0.]},
                    {'kind': 'runtime_failure', 'episode': 0, 'episode_step': 301, 'error': outcome}]
        events.append({'kind':'source_preparation_declared','sequence':0,
            'protocol':self.runner.SOURCE_PREPARATION,'source_preparation_sha256':self.runner.SOURCE_PREPARATION_SHA256,
            'override':self.runner.ACQUISITION_OVERRIDE})
        if stage not in ('source','anchor'):
            from palimpsest import memory_task
            case=job['case']
            world={'cues':[{'id':case['cue_id'],'xy':case['cue_xy'],'state':1}],
                'landmarks':[{'id':case['common_goal_id'],'xy':case['goal_xy']}]+
                    [{'id':f['inspection_landmark_id'],'xy':case['inspection_xy'][i]} for i,f in enumerate(case['facts'])],
                'passages':[{'subject_id':f['subject_id'],'inspection_landmark_id':f['inspection_landmark_id'],
                             'passability':'open'} for f in case['facts']], 'common_goal_id':case['common_goal_id']}
            packet=memory_task.capture_symbolic(world,[-1.3,.626,math.pi/20],[],episode_id='episode-0',tick=300)
            events.append({'kind':'memory_sensed','episode':0,'episode_step':300,'tick':300,'packet':packet})
            report['visibility_admission']={'300':memory.sha256(packet)}
            angle=next(v['bearing_rad'] for v in packet['landmarks'] if v['id']==case['common_goal_id'])
            bearing=[math.cos(angle),math.sin(angle)]
            state={'m':{'facts':case['facts']},'active':None,
                'cursor':{'episode_id':'episode-0','tick':300,'packet_sha256':memory.sha256(packet),
                          'common_goal_id':case['common_goal_id'],'bearing':bearing},
                'detector':{'tick':300,'cues':[{'id':case['cue_id'],'state':1,
                    'observation_id':memory_task._sensor_id('episode-0',300,'cue',case['cue_id'])}]}}
            report['boundary_memory']={'300':self.runner.packet_cursor(packet,state)}
            events.append({'kind':'memory_inspected','episode_step':300,
                'memory':{'active':None,'facts':case['facts'],'facts_truncated':0}})
            if failed:
                next(e for e in events if e['kind']=='memory_cue')['bearing']=bearing
                events[3]['bearing']=bearing
                events[3]['action']=self.runner.cue_action(bearing)
            else:
                events.append({'kind':'memory_cue','episode_step':300,'bearing':bearing})
        data = {'run': run, 'manifest': manifest, 'events': events, 'rows': rows}
        return job, data, report, native

    def admit(self, fixture):
        job, data, report, native = fixture
        (Path(job['output'])/'transfer-worker.json').write_text(json.dumps(report))
        # Numeric/native readers have separate real-format checks below and in
        # snapshot tests. These fixtures isolate admission, not physics.
        with patch.object(self.runner, 'read_run', return_value=data), \
             patch.object(self.runner, '_initial_snapshot', return_value=(native, {}, [])), \
             patch.object(self.runner, 'invariant_hashes', return_value={'native': 'fixture-hash'}), \
             patch.object(self.runner, 'load_histories', return_value=self.histories):
            return self.runner.validate_stage(job, {'status': 'completed', 'returncode': 0})

    def test_recorded_actions_exact_ticks_native_u_and_failed_attempt_boundary(self):
        for stage in ('swapped', 'sham', 'no-U'):
            self.admit(self.fixture(stage))
        good = self.fixture()
        self.admit(good)
        for mutate in (
            lambda f: f[1]['rows'][0]['action'].__setitem__(0, .66),
            lambda f: f[1]['rows'][0].__setitem__('action', np.array([.65, 0.], np.float32)),
            lambda f: f[1]['events'][1].__setitem__('episode_step', 301),
            lambda f: f[2]['boundary_memory']['300']['cursor'].__setitem__('packet_sha256','0'*64),
            lambda f: f[3]['application']['memory'].__setitem__('u', self.histories['swapped']['u']),
            lambda f: f[1]['manifest'].__setitem__('last_outcome', {'type': 'forged'})):
            bad = copy.deepcopy(good)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.admit(bad)
        failed = self.fixture(failed=True)
        self.admit(failed)
        for mutate in (
            lambda f: f[1]['events'].pop(3),  # missing last attempted driver tick
            lambda f: f[1]['events'].insert(4, copy.deepcopy(f[1]['events'][3])),
            lambda f: next(e for e in f[1]['events'] if e['kind']=='runtime_failure').__setitem__('episode_step', 302),
            lambda f: f[1]['manifest'].__setitem__('close_reason', 'forced_cleanup')):
            bad = copy.deepcopy(failed)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.admit(bad)

    def test_anchor_and_source_require_paused_exact_pre_event_boundary(self):
        anchor = self.fixture('anchor')
        self.admit(anchor)
        for mutate in (
            lambda f: f[2].__setitem__('steps', 299),
            lambda f: f[2].__setitem__('final_phase', 'terminated'),
            lambda f: f[3]['application']['memory']['cursor'].__setitem__('tick',298),
            lambda f: f[3]['application']['memory'].__setitem__('u', memory.artifact(method='empty-v1'))):
            bad = copy.deepcopy(anchor)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.admit(bad)
        source = self.fixture('source')
        # A short/fabricated row list cannot enter collector/source checks.
        with self.assertRaisesRegex(ValueError, 'exact pre-event prefix'):
            self.admit(source)
        source[2]['final_phase'] = source[1]['manifest']['final_phase'] = 'terminated'
        with self.assertRaisesRegex(ValueError, 'finish paused'):
            self.admit(source)

    def test_history_pins_refit_identity_plan_bounds_and_first_failure_stop(self):
        inputs = {}
        for role, value in self.histories.items():
            path = self.root/(role+'.json')
            path.write_text(json.dumps({'e': value['e'], 'u': value['u'],
                'history_sha256': memory.sha256(value['e'])}))
            inputs[role] = (path.name, self.runner._hash(path))
        with patch.object(self.runner, 'HISTORY_INPUTS', inputs):
            self.assertEqual(self.runner.load_histories(self.root)['own']['u'], self.histories['own']['u'])
            bundle = json.loads((self.root/'own.json').read_text())
            bundle['u'] = self.histories['swapped']['u']
            (self.root/'own.json').write_text(json.dumps(bundle))
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                self.runner.load_histories(self.root)
            inputs['own'] = ('own.json', self.runner._hash(self.root/'own.json'))
            with self.assertRaisesRegex(ValueError, 'E-only refit'):
                self.runner.load_histories(self.root)
        plan = self.plan()
        self.assertEqual([j['stage'] for j in plan['jobs']], list(self.runner.STAGES))
        self.assertEqual(len({j['run_id'] for j in plan['jobs']}), 6)
        self.assertEqual(plan['protocol']['source_prefix_ticks'], 300)
        self.assertEqual(plan['protocol']['remaining_ticks'], 300)
        self.assertEqual(plan['protocol']['retries'], 0)
        self.assertTrue(all(j['case']['seed']==8 and j['case']['split']=='development-test' for j in plan['jobs']))
        self.assertFalse(Path(plan['output']).exists())
        with patch.object(self.runner, 'bounded_process', return_value={'status': 'timeout', 'returncode': -15}) as child, \
             patch.object(self.runner, 'print', create=True):
            result = self.runner.run_verifier(plan)
        self.assertEqual(child.call_count, 1)
        self.assertEqual(result['status'], 'mechanism_unverified')
        self.assertEqual(result['runs'][0]['stage'], 'source')
        self.assertIn('no retry', result['first_failure']['message'])
        self.assertEqual(json.loads((Path(plan['output'])/'transfer-report.json').read_text()), result)
        for bearing in ([0., 0.], [True, 0.], [float('nan'), 0.], [1., 0., 99], {'pose': [0, 0, 0]}):
            with self.assertRaises(ValueError):
                self.runner.cue_action(bearing)
        self.assertEqual(self.runner.cue_action([0., -1.]), [.65, -math.pi/2])

    def test_expected_engine_failure_preserves_terminal_status_and_chunk_hashes(self):
        from palimpsest.engine import Engine
        from palimpsest.memory_task import CueUnavailable
        from palimpsest.records import RunWriter
        from test_engine import SmallEnv
        run = self.root/uuid.uuid4().hex
        engine = Engine(SmallEnv(), RunWriter(run/'recording', {'run_id': run.name}),
            scenario='sparse-navigation')
        self.runner._command_step(engine, [.65, .125], 'fixture')
        engine._fail(CueUnavailable('goal_cue_unavailable: fixture'))
        engine.close()
        data = self.runner.read_run(run)
        self.assertEqual(data['manifest']['status'], 'failed')
        self.assertEqual(data['manifest']['final_phase'], 'failed')
        self.assertEqual(data['manifest']['close_reason'], 'operator_closed')
        self.assertEqual(data['manifest']['last_outcome']['type'], 'CueUnavailable')
        np.testing.assert_array_equal(data['rows'][0]['action'], np.array([.65, .125], np.float64))
        chunk = next(p for p in data['paths'] if p.suffix=='.npz')
        chunk.write_bytes(chunk.read_bytes()+b'corruption')
        with self.assertRaises(ValueError):
            self.runner.read_run(run)


class TransferPreparation(unittest.TestCase):
    def test_shared_selector_preserves_nine_conditions_and_no_event_bypass(self):
        fixture, truth = experiment.make_case(8, 'local_cue', 'development-test')
        own = experiment.make_history(0, 'local_cue')
        swapped = experiment.make_history(9, 'paired_cue')
        own_u, swapped_u = memory.fit(own), memory.fit(swapped)
        artifacts = {'own': own_u, 'swapped': swapped_u, 'sham': copy.deepcopy(own_u),
            'no-U': memory.artifact(method='empty-v1'), 'hand-authored': memory.artifact('local_cue')}
        facts = fixture['m']['facts']
        local = next(f['id'] for f in facts if f['associations'][0]['relation'] == 'local_cue')
        paired = next(f['id'] for f in facts if f['associations'][0]['relation'] == 'paired_cue')
        expected = dict(zip(experiment.CONDITIONS,
            ([local], [paired], [local], [], [local], [facts[0]['id']], [facts[0]['id']], [local], [local])))
        before = copy.deepcopy((fixture, own, artifacts))
        for condition in experiment.CONDITIONS:
            kwargs = {'u': artifacts[condition]} if condition in artifacts else (
                {'history': own} if condition == 'retrieval' else
                {'gold_target_ids': truth['gold_target_ids']} if condition == 'oracle' else {})
            with patch.object(memory, 'fit', side_effect=AssertionError('selector cannot fit')):
                selection = experiment.selection_for_condition(condition, fixture['m'], fixture['trigger'], **kwargs)
            self.assertEqual(selection['target_ids'], expected[condition])
            with patch.object(memory, 'select', side_effect=AssertionError('no-event must bypass')):
                null = experiment.selection_for_condition(condition, fixture['m'], None, **kwargs)
                self.assertEqual(null, {'event_id': None, 'target_ids': [], 'reason': 'no_rule'})
        self.assertEqual((fixture, own, artifacts), before)
        comparison = experiment.compare_conditions(fixture, own, swapped, truth)
        self.assertEqual({r['condition']: r['selection']['target_ids'] for r in comparison['results']}, expected)

    def test_selector_rejects_wrong_resources_and_dangling_gold(self):
        fixture, _ = experiment.make_case(8, 'local_cue', 'development-test')
        m, event = fixture['m'], fixture['trigger']
        for condition, kwargs in [('unknown', {}), ('own', {}), ('retrieval', {}),
                ('traversal', {'u': memory.artifact('local_cue')}),
                ('own', {'u': memory.artifact('local_cue'), 'gold_target_ids': []}),
                ('oracle', {'gold_target_ids': ['not-a-fact']}),
                ('oracle', {'gold_target_ids': [m['facts'][0]['id']] * 2})]:
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                experiment.selection_for_condition(condition, m, event, **kwargs)
        with self.assertRaises(ValueError):
            experiment.selection_for_condition('no-U', m, event, u=memory.artifact(method='empty-v1'), limit=True)


if __name__ == '__main__':
    unittest.main()
