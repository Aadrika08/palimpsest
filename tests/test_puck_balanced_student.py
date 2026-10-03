"""Pure fixed-adapter and fake-owner checks, not native/model qualification."""
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from palimpsest import puck_balanced_student as student, puck_student as historical
from palimpsest import puck_balanced, puck_model, puck_learning as learning, puck_profile as puck
from palimpsest.records import iter_ticks
from palimpsest.snapshots import state_digest
import test_puck_student as base
from test_puck_balanced import protocol_fixture

ROOT=Path(__file__).resolve().parents[1]
gate=base.gate


def identity(seed=21):
    entry=student.model_entry(ROOT,seed)
    return {'training_seed':seed,'training_report_sha256':entry['files']['report.json'],
        'checkpoint_sha256':entry['files']['checkpoint.npz'],'protocol_sha256':entry['files']['protocol.json'],
        'training_objective_sha256':puck_balanced.PROTOCOL_SHA256,'learning_protocol_sha256':learning.PROTOCOL_SHA256,
        'supervisor_source_sha256':hashlib.sha256((ROOT/'src/palimpsest/puck_learning.py').read_bytes()).hexdigest()}


@contextmanager
def balanced_fixture():
    """Reuse the historical fake-resource fixture, translate only its envelope."""
    actual_owner=gate.owner
    def routed(config):
        config=dict(config)
        config['learning_student_balanced']=config.pop('learning_student')
        return actual_owner(config)
    with patch.object(base,'student',student),patch.object(base,'identity',identity),\
         patch.object(gate,'balanced_student_sources',return_value={'fixture':'source'}),\
         patch.object(gate,'owner',side_effect=routed):
        yield base.StudentFixtures()


class BalancedStudentFixtures(unittest.TestCase):
    def test_fixed_plan_aliases_default_binding_and_sources(self):
        self.assertIs(student.action,historical.action);self.assertIs(student.decide,historical.decide)
        self.assertEqual(student.plan(ROOT),historical.plan(ROOT))
        spec=student.protocol(ROOT);old=historical.protocol(ROOT)
        for key in ('limits','runtime','derivatives','own_state','replay','source_snapshots'):
            self.assertEqual(spec[key],old[key])
        self.assertNotEqual(spec['models_manifest'],old['models_manifest'])
        self.assertEqual(spec['decision_source']['sha256'],hashlib.sha256((ROOT/'src/palimpsest/puck_student.py').read_bytes()).hexdigest())
        from palimpsest import puck_development
        self.assertEqual(puck_development.protocol(ROOT)['models_manifest'],old['models_manifest'])
        with patch.object(gate,'sources',return_value={'fixture':'source'}):
            self.assertNotIn(student.PROTOCOL_PATH,gate.student_sources(ROOT))
            self.assertIn(student.PROTOCOL_PATH,gate.balanced_student_sources(ROOT))
        for seed in (True,21.,20,24):
            with self.assertRaises(ValueError):student.model_entry(ROOT,seed)

    def test_strict_balanced_envelope_and_default_rejection(self):
        row=student.plan(ROOT)[0]
        with tempfile.TemporaryDirectory() as tmp,patch.object(student,'admit_bundle',return_value=(Path(tmp),identity())):
            config={'repo':str(ROOT),'output':str(Path(tmp)/row['id']),'row':row,'sources':{},
                'learning_student_balanced':student.PROTOCOL_SHA256,'bundle_root':tmp}
            student.admit_config(config,ROOT)
            with self.assertRaises(ValueError):historical.admit_config(config,ROOT)
            for extra in ({'learning_student':historical.PROTOCOL_SHA256},{'learning_teacher':'x'},
                          {'learning_student_development':'x'},{'ticks':1}):
                with self.assertRaises(ValueError):student.admit_config(config|extra,ROOT)
            for extra in ({'seed':6000.},{'max_ticks':120.},{'model_seed':22},{'seed':6200}):
                with self.assertRaises(ValueError):student.admit_config(config|{'row':row|extra},ROOT)

    def test_real_numeric_bundle_reader_and_pin_failures_before_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/'seed-21';directory.mkdir();protocol=protocol_fixture()
            proto=puck_model.canonical(protocol);(directory/'protocol.json').write_bytes(proto)
            checkpoint=puck_model.checkpoint_bytes({n:np.zeros(s,np.float32) for n,s in puck_model.SHAPES.items()})
            (directory/'checkpoint.npz').write_bytes(checkpoint)
            report={'status':'completed','training_completed':True,'training_seed':21,'held_out_used':False,
                'qualification_claims':[],'finalization_errors':[],'training_objective_sha256':puck_balanced.PROTOCOL_SHA256,
                'protocol_sha256':puck_model.sha(proto),'selected_epoch':1,
                'history':[{'epoch':e,'train_ticks':5710,'dev_ticks':1314,'weighted_train_loss':.4,'dev_loss':.2} for e in range(1,31)],
                'files':[{'path':n,'bytes':len(b),'sha256':puck_model.sha(b)} for n,b in (('protocol.json',proto),('checkpoint.npz',checkpoint))]}
            (directory/'report.json').write_bytes(puck_model.canonical(report))
            entry={'seed':21,'directory':'seed-21','files':{n:hashlib.sha256((directory/n).read_bytes()).hexdigest() for n in ('protocol.json','report.json','checkpoint.npz')}}
            with patch.object(student,'model_entry',return_value=entry),patch.object(puck_model,'make_model') as constructor:
                _,pins=student.admit_bundle(ROOT,tmp,21)
                self.assertEqual(pins['training_objective_sha256'],puck_balanced.PROTOCOL_SHA256)
                self.assertEqual(pins['supervisor_source_sha256'],protocol['source_hashes']['src/palimpsest/puck_learning.py'])
                with self.assertRaises(ValueError):puck_model.read_bundle(directory,entry['files']['report.json'],ROOT,21)
                for name in entry['files']:
                    original=(directory/name).read_bytes();(directory/name).write_bytes(original+b'changed')
                    with self.assertRaises(ValueError):student.admit_bundle(ROOT,tmp,21)
                    (directory/name).write_bytes(original)
                constructor.assert_not_called()
            with patch.object(student,'admit_bundle',return_value=(directory,identity())),\
                 patch.object(puck_balanced,'read_bundle',return_value=({},identity()|{'checkpoint_sha256':'0'*64})),\
                 patch.object(puck_model,'make_model') as constructor:
                with self.assertRaises(ValueError):student.load(ROOT,tmp,21)
                constructor.assert_not_called()

    def test_balanced_application_keeps_objective_identity_and_rejects_old_schema(self):
        row=student.plan(ROOT)[0];w=base.world();c=base.contact(0);state=puck.initialize(w,row['case']);pins=identity()
        app=student.application(ROOT,row,{}, {},'a'*64,pins,state,w,c,learning.initial_cursor())
        self.assertEqual(app['kind'],'puck-balanced-student-application-v1')
        self.assertEqual(app['model_identity']['training_objective_sha256'],puck_balanced.PROTOCOL_SHA256)
        with self.assertRaises(ValueError):historical.validate_application(app,ROOT,row,{}, {},'a'*64,pins,0,state_digest(app))
        for name in ('checkpoint_sha256','training_objective_sha256','supervisor_source_sha256'):
            bad=copy.deepcopy(app);bad['model_identity'][name]='0'*64
            with self.assertRaises(ValueError):student.validate_application(bad,ROOT,row,{}, {},'a'*64,pins,0,state_digest(bad))
        with balanced_fixture() as f:f.test_snapshot_pins_and_restored_cursor_reproduce_policy_input()

    def test_shared_decision_real_record_and_parameter_guard(self):
        with balanced_fixture() as f:
            f.test_decision_uses_before_mode_once_and_saturation_reaches_real_task_boundary()
            f.test_real_record_roundtrip_action_replay_and_policy_staging()
            f.test_live_parameter_guard_checks_exact_checkpoint_values()

    def test_real_owner_route_and_all_fake_native_derivatives(self):
        with balanced_fixture() as f,tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=student.plan(ROOT);out=root/rows[0]['id']
            code,result,_,apps,_=f.run_owner(out);self.assertEqual(code,0,result.get('error'))
            manifest=json.loads((out/'recording/manifest.json').read_text())
            self.assertEqual(manifest['schema'],'puck-balanced-student-v1')
            student.admit_source(manifest,ROOT,rows[2],{'fixture':'source'},identity())
            with self.assertRaises(ValueError):historical.admit_source(manifest,ROOT,rows[2],{'fixture':'source'},identity())
            reference=list(iter_ticks(out/'recording'))
            for index in (1,2,3):
                dest=root/rows[index]['id'];code,receipt,_,_,calls=f.run_owner(dest,derivative=index,source=(out,result,apps))
                self.assertEqual(code,0,receipt.get('error'));self.assertEqual(calls,0 if index==2 else 4 if index==1 else 10)
                actual=list(iter_ticks(dest/'recording'));expected=reference[1:5] if index==1 else reference
                self.assertEqual(len(actual),len(expected))
                for a,b in zip(actual,expected):gate.same_row(a,b)

    def test_owner_rollback_restore_admission_and_fixture_host_isolation(self):
        with balanced_fixture() as f:
            f.test_owner_invalid_action_and_record_failure_keep_completed_cursor_uncommitted()
            f.test_owner_rejects_historical_application_before_restore()
            f.test_fixture_restores_preloaded_torch_and_host_version()


if __name__=='__main__':unittest.main()
