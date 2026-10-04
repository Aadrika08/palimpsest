"""Synthetic state-machine evidence, never native acquisition/route evidence."""
import copy
import importlib
import math
import unittest

from palimpsest import memory, memory_experiment, memory_decision_world as world


def scene(case, token=0, blocked=None):
    return {'cues':[{'id':case['cue_id'],'xy':case['cue_xy'],'state':token}],
        'landmarks':[{'id':i,'xy':xy} for i,xy in case['landmarks'].items()],
        'passages':[{'subject_id':f['subject_id'],'inspection_landmark_id':f['inspection_landmark_id'],
                     'passability':'blocked' if f['subject_id']==blocked else 'open'} for f in case['facts']],
        'common_goal_id':case['common_goal_id']}


def config(condition, resource=None):
    return {'version':1,'condition':condition,'limit':1,'resource':resource,
            'resource_sha256':memory.sha256(resource),'provenance_sha256':world.PROFILE_SHA256}


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.memory_decision'), 'memory-v2 supervisor is required')
        self.task = importlib.import_module('palimpsest.memory_decision')
        self.case = world.make_case(0, 'local_cue', 'change')
        self.tick = 0
        self.position = self.case['start_pose'][:2]
        self.yaw = 0.

    def packet(self, tick=None, token=0, blocked=None, target=None):
        if target is not None:
            xy = self.case['landmarks'][target]
            if xy != self.position:
                self.yaw = math.atan2(xy[1]-self.position[1],xy[0]-self.position[0])
            self.position = xy.copy()
        return self.task.capture_symbolic(scene(self.case,token,blocked), [*self.position,self.yaw],
            [[*xy,.4] for xy in world.PROFILE['obstacles']], episode_id='episode-0', tick=self.tick if tick is None else tick)

    def step(self,state,**kwargs):
        result = self.task.advance_memory(state,self.packet(**kwargs))
        self.tick += 1
        return result

    def acquired(self):
        state = self.task.initialize(self.case)
        original = copy.deepcopy(state)
        self.assertTrue(all(f['status']=='unknown' for f in state['m']['facts']))
        for _ in range(40):
            sup = state['supervisor']
            if sup['phase']=='await_decision':
                break
            target = sup['waypoint_ids'][sup['waypoint_index']]
            state,_,_ = self.step(state,target=target)
        self.assertEqual(state['supervisor']['phase'],'await_decision')
        self.assertTrue(all(f['status']=='observed' and f['estimate']=='open' and
                            f['evidence']['episode_id']=='episode-0' for f in state['m']['facts']))
        self.assertEqual(state['initial_m'],original['initial_m'])
        self.assertGreater(self.tick, 2)
        return state

    def commit(self,condition='no-U',u=None,resource=None):
        state=self.acquired()
        state=self.task.configure_selector(state,config(condition,resource),u)
        state=self.task.arm(state,self.tick)
        for offset in range(3):
            state,_,audit=self.step(state,token=int(offset>=1))
        return state,audit

    def test_real_packet_evidence_required_for_prefix_and_explicit_decision_boundary(self):
        state=self.acquired()
        with self.assertRaises(ValueError):
            self.task.arm(self.task.initialize(self.case),0)
        armed=self.task.arm(state,self.tick)
        self.assertEqual(armed['supervisor']['decision_tick'],self.tick+2)
        self.assertIsNone(armed['supervisor']['route_id'])
        self.assertEqual(state['supervisor']['decision_tick'],None)
        with self.assertRaises(ValueError):
            self.task.arm(armed,self.tick)
        broken=copy.deepcopy(state)
        broken['supervisor']['waypoint_ids'][0]='secret-target'
        with self.assertRaises(ValueError):
            self.task.validate_state(broken)

    def test_matching_selector_changes_route_under_same_categorical_policy(self):
        no_u,_=self.commit()
        preferred=world.public_graph(self.case)['routes'][0]
        self.assertEqual(no_u['supervisor']['route_id'],preferred['route_id'])
        self.setUp()
        own,audit=self.commit('own',memory.artifact('local_cue'))
        other=world.public_graph(self.case)['routes'][1]
        self.assertEqual(own['supervisor']['route_id'],other['route_id'])
        self.assertEqual(own['supervisor']['attempts'],1)
        self.assertEqual(len(own['requests']),1)  # unchosen work is retained
        self.assertTrue(any(item['kind']=='memory_commitment' for item in audit))
        self.assertGreater(other['cost'],preferred['cost'])
        self.assertEqual(own['e'],no_u['e'])

    def test_blocked_route_uses_retreat_then_replans_and_never_crosses_uncertain(self):
        state,_=self.commit()
        graph=world.public_graph(self.case)
        first=graph['routes'][0]
        state,_,audit=self.step(state,token=1,blocked=first['subject_id'],target=first['inspection_landmark_id'])
        self.assertEqual(state['supervisor']['phase'],'retreat')
        self.assertEqual(state['supervisor']['waypoint_ids'],first['retreat_ids'])
        for target in first['retreat_ids']:
            state,_,audit=self.step(state,token=1,blocked=first['subject_id'],target=target)
        self.assertEqual(state['supervisor']['route_id'],graph['routes'][1]['route_id'])
        self.assertEqual(state['supervisor']['attempts'],2)
        self.assertEqual(state['supervisor']['costs']['replans'],1)
        self.assertEqual(state['supervisor']['phase'],'follow_route')

    def test_goal_does_not_clear_or_wait_for_unchosen_requests(self):
        state,_=self.commit('own',memory.artifact('local_cue'))
        route=next(r for r in world.public_graph(self.case)['routes'] if r['route_id']==state['supervisor']['route_id'])
        for target in route['waypoint_ids'][:-1]:
            state,_,_=self.step(state,token=1,target=target)
        self.assertTrue(self.task.goal_allowed(state))
        self.assertTrue(state['requests'])
        state=self.task.mark_goal(state)
        self.assertEqual(state['supervisor']['phase'],'goal')
        self.assertTrue(state['requests'])
        with self.assertRaises(ValueError):
            self.task.mark_goal(self.task.initialize(self.case))

    def test_missing_required_bearing_rejects_without_pose_fallback_and_duplicates_are_exact(self):
        state=self.task.initialize(self.case)
        packet=self.packet()
        advanced,bearing,_=self.task.advance_memory(state,packet)
        self.assertEqual(self.task.advance_memory(advanced,packet),(advanced,bearing,[]))
        bad=copy.deepcopy(packet)
        bad['landmarks']=[]
        bad['arrivals']=[]
        with self.assertRaises(self.task.CueUnavailable):
            self.task.advance_memory(state,bad)
        self.assertEqual(state['supervisor']['phase'],'acquire')
        bad=copy.deepcopy(packet)
        bad['arrivals']=['hidden-landmark']
        with self.assertRaises(ValueError):
            self.task.advance_memory(state,bad)

    def test_all_nine_selector_resources_are_bounded_and_only_selected_by_selector(self):
        state=self.acquired()
        for condition in memory_experiment.CONDITIONS:
            resource=({'version':1,'episodes':[]} if condition=='retrieval' else
                      [self.case['facts'][0]['id']] if condition=='oracle' else None)
            artifact=(memory.artifact('local_cue') if condition in ('own','swapped','sham','hand-authored') else memory.artifact())
            branch=self.task.configure_selector(state,config(condition,resource),artifact)
            self.assertEqual(branch['m'],state['m'])
            self.assertEqual(branch['e'],state['e'])
            self.assertEqual(branch['supervisor'],state['supervisor'])
            with self.assertRaises(ValueError):
                self.task.configure_selector(state,config(condition,{'private_gold':True}),artifact)

    def test_waypoint_prefix_and_inspection_deadlines_fail_without_rescue(self):
        state=self.task.initialize(self.case)
        for _ in range(301):
            state,_,_=self.step(state)
            if state['supervisor']['phase']=='failure':
                break
        self.assertEqual(state['supervisor']['failure_reason'],'waypoint_timeout')
        state=self.task.initialize(self.case)
        state['supervisor']['waypoint_deadline_tick']=1500
        # Frozen maximum waypoint limit is itself validated.
        with self.assertRaises(ValueError):
            self.task.validate_state(state)

    def test_all_nine_conditions_execute_shared_commitment_and_retain_resource_boundaries(self):
        preferred=world.public_graph(self.case)['routes'][0]['route_id']
        other=world.public_graph(self.case)['routes'][1]['route_id']
        history=memory_experiment.make_history(200,'local_cue')  # synthetic historical fixture
        own=memory.fit(history)
        swapped=memory.fit(memory_experiment.make_history(300,'paired_cue'))
        expected={'own':other,'sham':other,'swapped':preferred,'no-U':preferred,
                  'hand-authored':other,'history-independent':other,'traversal':other,'retrieval':other,'oracle':other}
        baseline=None
        for condition in memory_experiment.CONDITIONS:
            self.setUp()
            artifact=own if condition in ('own','sham') else swapped if condition=='swapped' else memory.artifact('local_cue') if condition=='hand-authored' else memory.artifact()
            resource=history if condition=='retrieval' else [self.case['facts'][0]['id']] if condition=='oracle' else None
            state,audit=self.commit(condition,artifact,resource)
            self.assertEqual(state['supervisor']['route_id'],expected[condition],condition)
            selection=next(item['selection'] for item in state['last_decisions'] if item['kind']=='memory_selection')
            self.assertLessEqual(len(selection['target_ids']),1)
            if condition in ('own','sham'):
                normalized={k:v for k,v in state.items() if k not in ('u','selector')}
                if baseline is None:
                    baseline=normalized
                else:
                    self.assertEqual(normalized,baseline)

    def test_unresolved_inspection_exhausts_150_ticks_without_authorizing_crossing(self):
        state,_=self.commit()
        route=world.public_graph(self.case)['routes'][0]
        packet=self.packet(token=1,target=route['inspection_landmark_id'])
        for p in packet['passages']:
            p['passability']='unobserved'  # explicit fault-injected sensor fixture
        state,_,_=self.task.advance_memory(state,packet)
        self.tick+=1
        self.assertEqual(state['supervisor']['phase'],'inspect')
        deadline=state['supervisor']['inspection_deadline_tick']
        self.assertEqual(deadline,self.tick-1+150)
        while self.tick<=deadline:
            packet=self.packet(token=1)
            for p in packet['passages']:
                p['passability']='unobserved'
            state,_,_=self.task.advance_memory(state,packet)
            self.tick+=1
        self.assertEqual(state['supervisor']['phase'],'failure')
        self.assertEqual(state['supervisor']['failure_reason'],'inspection_timeout')
        self.assertFalse(state['supervisor']['inspection_authorized'])

    def test_invalid_phase_route_and_forged_authorization_rejected(self):
        state=self.acquired()
        for changes in ({'phase':'follow_route'}, {'phase':'retreat'}, {'inspection_authorized':True}):
            bad=copy.deepcopy(state)
            bad['supervisor'].update(changes)
            with self.assertRaises(ValueError):
                self.task.validate_state(bad)
