"""Small native fixtures; no Engine, inference, stepping or full study jobs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import mujoco
import numpy as np
from palimpsest.snapshots import save_snapshot, state_digest

ROOT = Path(__file__).resolve().parents[2]


def fixture(folder):
    model = mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><joint type="slide"/><geom size="0.1"/></body></worldbody></mujoco>')
    native = mujoco.MjData(model)
    native.timer.duration[:] = 2
    raw = dict(native_data=native.__getstate__(), application=dict(source_run_id='source', event_prefix=['event'], tick=220),
               observation={'action': np.array([1., 2.])}, rng={'state': np.array([1, 2], dtype=np.uint64)})
    raw['native_sha256'] = hashlib.sha256(raw['native_data']).hexdigest()
    normalized = copy.deepcopy(raw)
    del normalized['application']['source_run_id'], normalized['application']['event_prefix']
    raw_final = state_digest(normalized)
    native.timer.duration[:] = 0
    normalized['native_data'] = native.__getstate__()
    normalized['native_sha256'] = hashlib.sha256(normalized['native_data']).hexdigest()
    folder.mkdir(parents=True)
    for name, state in (('final-raw.snp',raw), ('final-normalized.snp',normalized)):
        save_snapshot(state,folder/name)
    row = dict(unit_id='overhead/0/null', kind='execution_overhead', seed=0, condition='null',status='completed',
               raw_snapshot_path=str(folder/'final-raw.snp'),matched_snapshot_path=str(folder/'final-normalized.snp'),
               raw_snapshot_state_sha256=state_digest(raw),raw_final_state_sha256=raw_final,
               raw_native_sha256=raw['native_sha256'],matched_native_sha256=normalized['native_sha256'],
               final_state_sha256=state_digest(normalized), final_state_normalization=dict(
                   recorder_fields=['application.source_run_id','application.event_prefix'],native_fields=['timer.duration'],mujoco_version=mujoco.__version__))
    return row,raw,normalized


class StateAuditTests(unittest.TestCase):
    def module(self):
        path=ROOT/'paper/scripts/audit_authority_state.py'
        self.assertTrue(path.exists(), 'state audit is not implemented')
        spec=importlib.util.spec_from_file_location('state_audit',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_large_rng_integers_are_finite_without_float_coercion(self):
        self.assertEqual(self.module().finite_counts({'rng':{'state':2**128-1}})['scalars'],1)

    def test_exact_native_canonicalization_and_source_files_unchanged(self):
        audit=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs/paper-generator-tests') as tmp:
            root=Path(tmp);row,raw,normalized=fixture(root/'execution_overhead/overhead__0__null')
            before={p:p.read_bytes() for p in root.rglob('*.snp')}
            report=audit.audit_unit(row,root)
            self.assertEqual(report['status'],'passed')
            self.assertTrue(report['canonical_state_matches'])
            self.assertGreater(report['finite']['raw']['arrays'],0)
            self.assertGreater(report['finite']['raw_native']['arrays'],0)
            self.assertEqual(report['finite']['raw_native'],report['finite']['normalized_native'])
            self.assertEqual(before,{p:p.read_bytes() for p in before})
            self.assertEqual(report['raw_file_sha256'],hashlib.sha256(before[Path(row['raw_snapshot_path'])]).hexdigest())

    def test_nonfinite_container_and_native_arrays_rejected(self):
        audit=self.module()
        for where in ('container','native','scalar'):
            with self.subTest(where=where), tempfile.TemporaryDirectory(dir=ROOT/'runs/paper-generator-tests') as tmp:
                root=Path(tmp);row,raw,normalized=fixture(root/'execution_overhead/overhead__0__null')
                if where=='container':raw['observation']['action'][0]=np.nan
                elif where=='scalar':raw['observation']['x']=np.float64(np.inf)
                else:
                    native=mujoco.MjData.__new__(mujoco.MjData);native.__setstate__(raw['native_data']);native.qpos[0]=np.inf
                    raw['native_data']=native.__getstate__();raw['native_sha256']=hashlib.sha256(raw['native_data']).hexdigest()
                path=Path(row['raw_snapshot_path']);path.unlink();save_snapshot(raw,path)
                row['raw_snapshot_state_sha256']=state_digest(raw);row['raw_native_sha256']=raw['native_sha256']
                report=audit.audit_unit(row,root)
                self.assertEqual(report['status'],'failed')
                self.assertIn('nonfinite',report['error'])

    def test_normalized_scientific_tamper_rejected_even_with_updated_row_hash(self):
        audit=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs/paper-generator-tests') as tmp:
            root=Path(tmp);row,raw,normalized=fixture(root/'execution_overhead/overhead__0__null')
            normalized['observation']['action'][0]+=1
            path=Path(row['matched_snapshot_path']);path.unlink();save_snapshot(normalized,path)
            row['final_state_sha256']=state_digest(normalized)
            report=audit.audit_unit(row,root)
            self.assertEqual(report['status'],'failed')
            self.assertIn('canonical',report['error'])

    def test_missing_file_path_escape_and_incomplete_status_preserved(self):
        audit=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs/paper-generator-tests') as tmp:
            root=Path(tmp);row,_,_=fixture(root/'execution_overhead/overhead__0__null')
            row['raw_snapshot_path']=str(root/'other.snp')
            self.assertEqual(audit.audit_unit(row,root)['status'],'failed')
            row['status']='incomplete'
            self.assertEqual(audit.audit_unit(row,root)['status'],'not audited')

    def test_cli_preserves_forty_denominators_inventory_binding_and_exclusive_output(self):
        from test_authority_evidence import fixture as campaign_fixture
        audit=self.module()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs/paper-generator-tests') as tmp:
            root=Path(tmp);row,_,_=fixture(root/'execution_overhead/overhead__0__null')
            _,summary,_=campaign_fixture()
            costs=[r for r in summary['rows'] if r['kind']=='execution_overhead']
            for r in costs: r['status']='incomplete'
            costs[0].update(row)
            inventory=[dict(path=str(p.relative_to(root)),type='file',size_bytes=p.stat().st_size,
                            sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in root.rglob('*.snp')]
            (root/'analysis').mkdir();inv=root/'analysis/raw-inventory.json';inv.write_text(json.dumps(inventory))
            source=root/'summary.json';source.write_text(json.dumps(summary))
            args=['--summary',str(source),'--raw-root',str(root),'--output',str(root/'audit.json')]
            self.assertEqual(audit.main(args),1)
            result=json.loads((root/'audit.json').read_text())
            self.assertEqual(result['counts'],{'passed':1,'failed':0,'not audited':39})
            self.assertEqual(len(result['rows']),40)
            before=(root/'audit.json').read_bytes();self.assertEqual(audit.main(args),1)
            self.assertEqual((root/'audit.json').read_bytes(),before)
            inventory[0]['sha256']='0'*64;inv.write_text(json.dumps(inventory))
            self.assertEqual(audit.audit_summary(summary,root)['counts']['failed'],1)
            summary['identity']['commit']='a'*40
            with self.assertRaises(ValueError):audit.audit_summary(summary,root)


if __name__=='__main__':unittest.main()
