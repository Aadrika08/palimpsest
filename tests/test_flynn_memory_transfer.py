"""Pure neural-runner contracts; fixtures are not actual acquisition or inference."""
import copy
from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from palimpsest import memory, memory_experiment as experiment
from palimpsest.snapshots import state_digest


class FlynnTransferBoundaries(unittest.TestCase):
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('flynn_transfer',
            self.repo/'scripts/verify_flynn_memory_transfer.py')
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.histories = {role:{'e':experiment.make_history(seed,relation),'path':role+'.json','sha256':'0'*64}
            for role,seed,relation in [('own',0,'local_cue'),('swapped',9,'paired_cue')]}
        for value in self.histories.values():
            value['u']=memory.fit(value['e'])

    def plan(self):
        with patch.object(self.runner.common,'load_histories',return_value=self.histories), \
                patch.object(self.runner,'source_identity',return_value={'fixture':True}):
            return self.runner.make_plan(self.repo,self.root/'assets',self.root/'output',self.root/'history')

    def test_fixed_twelve_stage_plan_has_only_declared_resource_access(self):
        plan = self.plan()
        self.assertEqual([j['stage'] for j in plan['jobs']],list(self.runner.STAGES))
        self.assertEqual(len({j['run_id'] for j in plan['jobs']}),12)
        self.assertEqual({j['case']['seed'] for j in plan['jobs']},{16})
        self.assertTrue(all(j['case']['acquisition'] for j in plan['jobs']))
        for job in plan['jobs']:
            if job['stage'] in ('source','policy-anchor','oracle'):
                self.assertIsNone(job['selector'])
            else:
                resource = job['selector']['resource']
                self.assertEqual(resource,self.histories['own']['e'] if job['stage']=='retrieval' else None)
            self.assertIsNone(job['oracle_evidence'])
        self.assertEqual(plan['protocol']['aggregate_max_bytes'],4*1024**3)
        self.assertEqual(plan['protocol']['outer_timeout_seconds'],1980)
        forged = copy.deepcopy(plan['jobs'][0])
        forged['case']['acquisition']=False
        with self.assertRaises(ValueError):
            self.runner.validate_job(forged,prepared=True)
        self.histories['own']['e']['episodes'][0]['trigger']['cue_id']=plan['jobs'][0]['case']['cue_id']
        with self.assertRaisesRegex(ValueError,'evidence IDs overlap'):
            self.plan()
        forged = copy.deepcopy(plan['jobs'][1])
        forged['selector']=plan['jobs'][2]['selector']
        with self.assertRaises(ValueError):
            self.runner.validate_job(forged,prepared=True)

    def test_controller_preparation_excludes_only_explicit_fresh_fields(self):
        source = {'identity':{'policy':None,'torch':None,'model_sha256':'a'*64},
            'rng':{'torch_cpu':None,'torch_cuda':[],'numpy':[1,2]},'policy':None,
            'integration':np.array([1.,2.]),'native_data':b'fixture',
            'environment':{'goal':np.array([-.5,-2.7],np.float32)},
            'application':{key:None for key in ('controller','controller_tensors','manual_action',
                'pending_commands','receipts','original_commands','revision','source_run_id','event_prefix')}}
        source['application'].update(memory={'m':{'facts':[{'status':'observed'}]},'e':[],
            'u':memory.artifact(method='empty-v1'),'cursor':{'tick':299},'detector':{'tick':299}},
            world_task_state={'applied':False},eyes={'left':True,'right':True},total_tick=300)
        anchor = copy.deepcopy(source)
        anchor['policy']=np.ones(4)
        anchor['identity'].update(policy={'device':'cpu'},torch={'version':'fixture'})
        anchor['rng'].update(torch_cpu=np.array([2,3],np.uint8))
        for key in ('controller','controller_tensors','manual_action','pending_commands','receipts',
                    'original_commands','revision','source_run_id','event_prefix'):
            anchor['application'][key]='explicit fresh fixture'
        expected = self.runner.replacement_preserved(source)
        self.assertEqual(self.runner.replacement_preserved(anchor),expected)
        mutations = [lambda x:x['integration'].__setitem__(0,3.),
            lambda x:x['identity'].__setitem__('model_sha256','b'*64),
            lambda x:x['rng']['numpy'].__setitem__(0,7),
            lambda x:x['application']['memory']['cursor'].__setitem__('tick',300),
            lambda x:x['application']['memory'].__setitem__('u',memory.artifact('local_cue')),
            lambda x:x['application']['world_task_state'].__setitem__('applied',True)]
        for mutate in mutations:
            altered = copy.deepcopy(anchor)
            mutate(altered)
            self.assertNotEqual(self.runner.replacement_preserved(altered),expected)

    def test_neural_step_calls_real_method_without_motor_override_and_binds_rows(self):
        observation = {'cam_left':np.zeros((2,2,3),np.uint8),'cam_right':np.ones((2,2,3),np.uint8),
            'sensors':{'collision':False,'collision_angle':None,'wind_direction':[1.,0.]}}
        result = {'action':np.array([.25,-.1],np.float32),'encoded_input':np.zeros(4813,np.float32),
            'raw_output':np.array([.03,-.02],np.float32)}
        events = []
        original = Mock(return_value=result)
        def event(kind,**values):
            events.append({'kind':kind,'episode':0,'episode_step':300,'tick':300,**values})
        engine = SimpleNamespace(controller='flynn',policy=SimpleNamespace(act=original),_event=event,
            submit=Mock(return_value={'status':'queued'}),advance=Mock(return_value={'phase':'paused'}))
        self.runner.audit_policy(engine)
        self.assertIs(engine.policy.act(observation),result)
        original.assert_called_once_with(observation)
        self.runner.policy_step(engine,300)
        engine.advance.assert_called_once_with()
        command = engine.submit.call_args.args[0]
        self.assertEqual(command['kind'],'step')
        self.assertNotIn('payload',command)
        row = {'tick':300,**observation,**result,'sensors':np.array([0.,0.,1.,0.],np.float32)}
        events.extend([{'kind':'command_received','command':command},
            {'kind':'memory_cue','episode_step':300,'bearing':[1.,0.]}])
        data = {'events':events,'rows':[row]}
        self.runner.policy_bindings(data)
        altered = copy.deepcopy(data)
        altered['rows'][0]['action'][0]=.3
        with self.assertRaisesRegex(ValueError,'binding differs'):
            self.runner.policy_bindings(altered)
        altered = copy.deepcopy(data)
        altered['events'][-1]['bearing']=[0.,1.]
        with self.assertRaisesRegex(ValueError,'declared bearing'):
            self.runner.policy_bindings(altered)
        altered = copy.deepcopy(data)
        altered['events'].append({'kind':'command_received','command':{'kind':'set_action'}})
        with self.assertRaisesRegex(ValueError,'motor/intervention'):
            self.runner.policy_bindings(altered)
        with self.assertRaisesRegex(ValueError,'undeclared inputs'):
            engine.policy.act({**observation,'private_pose':[0,0,0]})
        self.assertEqual(original.call_count,1)

    def test_task_failure_is_narrow_and_snapshot_cap_precedes_publication(self):
        report = {'final_phase':'failed','outcome':{'type':'CueUnavailable','message':'goal_cue_unavailable:marker'}}
        self.assertTrue(self.runner.task_failure(report))
        for outcome in ({'type':'ValueError','message':'model input'},
                {'type':'CueUnavailable','message':'unrelated'},{}):
            self.assertFalse(self.runner.task_failure({**report,'outcome':outcome}))
        storage = Mock()
        cap = self.runner._SnapshotBudget(storage)
        with self.assertRaisesRegex(ValueError,'16 MiB'):
            cap.check(16*1024**2+1,path=self.root/'initial.snp')
        storage.check.assert_not_called()
        cap.check(16*1024**2,path=self.root/'initial.snp')
        storage.check.assert_called_once()

    def test_first_infrastructure_failure_keeps_unattempted_stages_without_children(self):
        plan = self.plan()
        # All native/model boundaries are mocked; this only checks parent accounting.
        real_budget = self.runner.budget(plan['output'])
        def lease():
            Path(plan['output']).mkdir()
            return nullcontext(real_budget)
        with patch.object(self.runner.common,'load_histories',return_value=self.histories), \
                patch.object(self.runner,'source_identity',return_value=plan['source_identity']), \
                patch.object(self.runner,'budget',return_value=real_budget), \
                patch.object(real_budget,'lock',side_effect=lease), \
                patch.object(self.runner.shutil,'disk_usage',return_value=SimpleNamespace(free=16*1024**3)), \
                patch.object(self.runner,'bounded_process',return_value={'status':'timeout','returncode':None}) as child:
            result = self.runner.run_verifier(plan)
        self.assertEqual(result['status'],'mechanism_unverified')
        self.assertEqual(len(result['runs']),1)
        self.assertEqual(len(result['unattempted_stages']),11)
        child.assert_called_once()
        self.assertFalse(result['replay_executed'])
        self.assertTrue(result['source_unchanged'])
        self.assertTrue((self.root/'output/transfer-report.json').is_file())

    def test_prepared_plan_hash_preserves_exact_job_ids_and_rejects_tampering(self):
        plan = self.plan()
        path = self.root/'prepared-plan.json'
        path.write_text(json.dumps(plan))
        expected = self.runner.common._hash(path)
        self.assertEqual(self.runner.read_prepared_plan(path,expected),plan)
        altered = copy.deepcopy(plan)
        altered['jobs'][0]['run_id']='0'*32
        path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError,'plan hash differs'):
            self.runner.read_prepared_plan(path,expected)


if __name__=='__main__':
    unittest.main()
