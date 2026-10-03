"""Pure trainer-contract/publication fixtures; no actual Torch or fitting."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import train_male_recovery as trainer
import train_male_reduced as original


def history():
    return {'selected_epoch':3,'history':[{'epoch':i,'train_ticks':2117,
        'train_loss':.1,'dev':{'ticks':1228,'loss':.05 if i in (3,4) else .1,
        'velocity_mae':.1,'wrapped_heading_mae_radians':.1}} for i in range(1,21)]}


class RecoveryTraining(unittest.TestCase):
    def test_exact_pair_settings_reuse_numerical_helpers_without_v2_admission(self):
        self.assertIs(trainer.fit,original.fit)
        self.assertIs(trainer.evaluate,original.evaluate)
        self.assertIs(trainer.make_model,original.make_model)
        self.assertIs(trainer.rewire,original.rewire)
        p=trainer.data_reader.protocol()
        for seed in (10,11,12):
            value=trainer.fixed_training(seed)
            for key,expected in p['training'].items():self.assertEqual(value[key],expected)
            self.assertEqual((value['training_seed'],value['rewiring_seed']),(seed,seed))
            self.assertEqual(value['variants'],['original','degree_rewired'])
            self.assertEqual(value['data_manifest_sha256'],trainer.DATA_SHA256)
            self.assertEqual((value['epochs'],value['window']),(20,32))
            from palimpsest.male_research import validate_training
            with self.assertRaises(ValueError):validate_training(value)
        for seed in (0,13,True):
            with self.assertRaises(ValueError):trainer.fixed_training(seed)

    def test_all_epochs_counts_finite_losses_and_earliest_exact_tie_required(self):
        trainer.validate_fit(history())
        for edit in ('last_epoch','train_count','dev_count','selection','nonfinite'):
            result=copy.deepcopy(history())
            if edit=='last_epoch':result['history'].pop()
            if edit=='train_count':result['history'][0]['train_ticks']=1983
            if edit=='dev_count':result['history'][0]['dev']['ticks']=0
            if edit=='selection':result['selected_epoch']=4
            if edit=='nonfinite':result['history'][0]['dev']['loss']=float('nan')
            with self.assertRaises(ValueError):trainer.validate_fit(result)

    def test_fresh_pair_root_cannot_manage_any_input_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);prepared=root/'data'/'data-manifest.json'
            baseline=root/'baseline'/'collection.json';recovery=root/'recovery'/'report.json'
            manifest={'baseline_collection':{'path':str(baseline)},'recovery_report':{'path':str(recovery)}}
            for path in (prepared,baseline,recovery):path.parent.mkdir(exist_ok=True)
            for output in (root/'seed-10',prepared.parent/'seed-10',baseline.parent/'new'/'seed-10',recovery.parent/'new'/'seed-10'):
                with self.assertRaisesRegex(ValueError,'input'):trainer.output_path(output,10,prepared,manifest)
            self.assertEqual(trainer.output_path(root/'fresh'/'seed-10',10,prepared,manifest),root/'fresh'/'seed-10')
            with self.assertRaises(ValueError):trainer.output_path(root/'fresh'/'wrong',10,prepared,manifest)

    def test_final_sync_source_deadline_and_no_overwrite_guards(self):
        for failure in ('fsync','source','deadline',None):
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);checks=[]
                def validate():
                    checks.append('source-after-fsync')
                    if failure=='source':raise ValueError('changed raw source')
                if failure=='fsync':
                    with patch.object(trainer.os,'fsync',side_effect=OSError('injected sync failure')):
                        with self.assertRaises(OSError):trainer.stage_report(root,{},time.monotonic()+2)
                elif failure in ('source','deadline'):
                    trainer.stage_report(root,{},time.monotonic()+2)
                    with self.assertRaises((ValueError,TimeoutError)):
                        trainer.publish_report(root,0. if failure=='deadline' else time.monotonic()+2,validate)
                else:
                    trainer.stage_report(root,{'status':'fixture'},time.monotonic()+2)
                    trainer.publish_report(root,time.monotonic()+2,validate)
                    before=(root/'report.json').read_bytes()
                    with self.assertRaises(FileExistsError):trainer.stage_report(root,{},time.monotonic()+2)
                    with self.assertRaises(FileExistsError):trainer.publish_report(root,time.monotonic()+2,validate)
                    self.assertEqual((root/'report.json').read_bytes(),before)
                self.assertEqual((root/'report.json').exists(),failure is None)
                self.assertEqual((root/'report.pending').exists(),failure is not None)
                if failure!='fsync':self.assertIn('source-after-fsync',checks)

    def test_artifact_bounds_and_fsync_failure_keep_diagnostic_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(ValueError):trainer.write_artifact(root/'large',b'x'*(trainer.MAX_FILE+1),time.monotonic()+2)
            self.assertFalse((root/'large').exists())
            with patch.object(trainer.os,'fsync',side_effect=OSError('injected')):
                with self.assertRaises(OSError):trainer.write_artifact(root/'partial',b'fixture',time.monotonic()+2)
            self.assertEqual((root/'partial').read_bytes(),b'fixture')

    def test_cli_has_no_heldout_input_and_fresh_import_is_lazy(self):
        env={**os.environ,'PYTHONPATH':os.pathsep.join((str(ROOT/'src'),str(ROOT/'scripts')))}
        command=[sys.executable,str(ROOT/'scripts/train_male_recovery.py')]
        help_result=subprocess.run(command+['--help'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(help_result.returncode,0)
        self.assertNotIn('--held-out',help_result.stdout)
        rejected=subprocess.run(command+['--training-seed','10','--output','unused','--held-out','forbidden'],
            cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(rejected.returncode,2)
        lazy=subprocess.run([sys.executable,'-c',"import train_male_recovery,sys; assert not ({'torch','mujoco'} & set(sys.modules))"],
            cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(lazy.returncode,0,lazy.stderr[-1024:])

    def test_existing_production_bundle_refuses_new_research_report_before_torch(self):
        from palimpsest.male_policy import _bundle
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            report=json.dumps({'status':'completed-research-training'}).encode()
            (root/'report.json').write_bytes(report)
            for name in ('protocol.json','original-graph.json','original.pt','degree_rewired-graph.json','degree_rewired.pt'):
                (root/name).write_bytes(b'fixture')
            with self.assertRaisesRegex(ValueError,'completed bounded training report'):
                _bundle(root,'original',hashlib.sha256(report).hexdigest(),root/'graph',root/'graph-manifest')


if __name__=='__main__':unittest.main()
