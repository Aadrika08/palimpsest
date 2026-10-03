"""Pure balanced development routing; fake owners confer no native qualification."""
import ast
import copy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from palimpsest import puck_balanced_development as dev, puck_development as historical
from palimpsest import puck_balanced_student as student, puck_student as original
from palimpsest.records import iter_ticks
from palimpsest.snapshots import state_digest
import test_puck_development as base
import test_puck_student as owner_fixtures
from test_puck_balanced_student import identity

ROOT=Path(__file__).resolve().parents[1]
gate=base.gate;evaluator=base.evaluator


@contextmanager
def fixtures():
    """Adapt only the historical authored-fixture envelope; run the actual owner."""
    actual_owner=gate.owner
    def routed(config):
        config=dict(config)
        assert config.pop('learning_student_development')==historical.PROTOCOL_SHA256
        config['learning_student_balanced_development']=dev.PROTOCOL_SHA256
        return actual_owner(config)
    with patch.object(base,'dev',dev),patch.object(base,'student',student),patch.object(base,'identity',identity),\
         patch.object(owner_fixtures,'student',student),patch.object(owner_fixtures,'identity',identity),\
         patch.object(gate,'balanced_development_sources',return_value={'fixture':'source'}),\
         patch.object(gate,'owner',side_effect=routed):
        yield base.DevelopmentFixtures()


class BalancedDevelopmentFixtures(unittest.TestCase):
    def test_scientific_and_goal_asts_rows_limits_and_default_bindings_unchanged(self):
        def functions(path):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)}
        old=functions(ROOT/'src/palimpsest/puck_development.py');new=functions(ROOT/'src/palimpsest/puck_balanced_development.py')
        for name in ('plan','scientific_initial','initial_match','admission'):self.assertEqual(old[name],new[name],name)
        spec=dev.protocol(ROOT);previous=historical.protocol(ROOT)
        for key in ('initialization','limits','runtime','scene_order','model_order','max_ticks',
                    'owners','goals_each_model_required','held_out','completion','fresh_only','layout_split','owner_order'):
            self.assertEqual(spec[key],previous[key],key)
        self.assertEqual(dev.plan(ROOT),historical.plan(ROOT))
        self.assertEqual(evaluator.bindings(False),(historical,original,evaluator.development_sources,'learning_student_development'))
        self.assertEqual(evaluator.bindings(True),(dev,student,gate.balanced_development_sources,'learning_student_balanced_development'))
        for value in (None,0,1,'balanced'):
            with self.assertRaises(ValueError):evaluator.bindings(value)
        with patch.object(gate,'sources',return_value={'fixture':'source'}):
            self.assertNotIn(dev.PROTOCOL_PATH,gate.development_sources(ROOT))
            self.assertIn(dev.PROTOCOL_PATH,gate.balanced_development_sources(ROOT))

    def test_fixed_fresh_envelope_and_protocol_pins_reject_before_bundle(self):
        row=dev.plan(ROOT)[0]
        with tempfile.TemporaryDirectory() as tmp,patch.object(student,'admit_bundle',return_value=(Path(tmp),identity())) as bundle:
            config={'repo':str(ROOT),'output':str(Path(tmp)/row['id']),'row':row,'sources':{},
                'learning_student_balanced_development':dev.PROTOCOL_SHA256,'bundle_root':tmp,'initial_reference':None}
            self.assertEqual(dev.admit_config(config,ROOT)['ticks'],600)
            with self.assertRaises(ValueError):historical.admit_config(config,ROOT)
            for extra in ({'seed':6100.},{'seed':6200},{'model_seed':True},{'model_seed':21.},
                          {'max_ticks':600.},{'kind':'policy-replay'},{'max_bytes':float(row['max_bytes'])}):
                bundle.reset_mock()
                with self.assertRaises(ValueError):dev.admit_config(config|{'row':row|extra},ROOT)
                bundle.assert_not_called()
            for extra in ({'source_output':tmp},{'start_tick':0},{'learning_student_development':historical.PROTOCOL_SHA256},
                          {'learning_student_balanced':student.PROTOCOL_SHA256},{'initial_reference':{}},
                          {'learning_student_balanced_development':'0'*64}):
                bundle.reset_mock()
                with self.assertRaises(ValueError):dev.admit_config(config|extra,ROOT)
                bundle.assert_not_called()
        actual_read=dev._read
        def changed(path,cap):
            raw=actual_read(path,cap)
            return raw+b'changed' if Path(path).name=='puck_development.py' else raw
        with patch.object(dev,'_read',side_effect=changed):
            with self.assertRaises(ValueError):dev.protocol(ROOT)

    def test_scientific_fingerprints_and_each_model_admission_use_historical_checks(self):
        with fixtures() as f:
            f.test_scientific_match_includes_all_non_torch_rng_and_exact_defined_state()
            f.test_each_model_threshold_all_rows_and_no_winning_seed_selection()
            row=dev.plan(ROOT)[0];app=f.snapshot(row)['application']
            with self.assertRaises(ValueError):historical.validate_initial(app,ROOT,row,{'fixture':'source'},
                {'fixture':'profile'},'a'*64,identity())
            altered=copy.deepcopy(app);altered['model_identity']['training_objective_sha256']='0'*64
            with self.assertRaises(ValueError):dev.validate_initial(altered,ROOT,row,{'fixture':'source'},
                {'fixture':'profile'},'a'*64,identity())

    def test_actual_owner_route_real_records_and_rng_mismatch_before_prediction_one(self):
        with fixtures() as f,tempfile.TemporaryDirectory() as tmp:
            rows=dev.plan(ROOT);out=Path(tmp)/rows[0]['id']
            code,result,env,apps,calls=f.run_owner(out,development_row=rows[0])
            self.assertEqual(code,0,result.get('error'));self.assertEqual((calls,env.steps,result['ticks']),(10,10,10))
            self.assertEqual(set(result['snapshots']),{'initial'})
            self.assertEqual(apps[0]['kind'],'puck-balanced-student-development-application-v1')
            manifest=json.loads((out/'recording/manifest.json').read_text())
            self.assertEqual(manifest['schema'],'puck-balanced-student-development-v1')
            self.assertEqual(manifest['model_identity'],identity())
            reference={'owner_id':rows[0]['id'],'result_sha256':gate.digest(out/'result.json'),
                'snapshot_sha256':result['snapshots']['initial']['sha256']}
            for row,mismatch in ((rows[1],False),(rows[2],True)):
                destination=Path(tmp)/row['id']
                code,result,env,apps,calls=f.run_owner(destination,development_row=row,initial_reference=reference,rng_mismatch=mismatch)
                self.assertEqual(code,int(mismatch),result.get('error'))
                self.assertEqual((calls,env.steps),(0,0) if mismatch else (10,10))
                self.assertEqual(result['initial_match']['status'],'failed' if mismatch else 'passed')
                numeric=list(iter_ticks(destination/'recording'));self.assertEqual(len(numeric),0 if mismatch else 10)
                self.assertTrue(all(not any(k.startswith('teacher') for k in r) for r in numeric))
            with tempfile.TemporaryDirectory() as failing:
                code,result,env,_,calls=f.run_owner(Path(failing)/rows[0]['id'],development_row=rows[0],bad_action=True)
                self.assertEqual((code,calls,env.steps),(1,1,0));self.assertEqual(result['own_supervisor_cursor']['tick'],0)

    def test_actual_evaluator_selector_all_outcomes_failure_retention_and_deadlines(self):
        real_main=evaluator.main;real_writer=base.RunWriter
        def selected(args):args.balanced=True;return real_main(args)
        def writer(path,manifest):
            assert manifest['schema']=='puck-student-development-v1'  # Historical helper's authored fixture only.
            return real_writer(path,{**manifest,'schema':'puck-balanced-student-development-v1'})
        with fixtures() as f,patch.object(evaluator,'main',side_effect=selected),patch.object(base,'RunWriter',side_effect=writer):
            f.test_real_filesystem_stage_all_outcomes_and_infra_stop_retains_unstarted_rows()
            f.test_admission_and_lease_exit_are_inside_internal_deadline()


if __name__=='__main__':unittest.main()
