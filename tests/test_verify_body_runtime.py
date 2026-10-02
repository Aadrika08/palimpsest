"""Pure verification-harness checks; no real body load or owner launch."""
import copy
from pathlib import Path
import sys
import unittest
import numpy as np

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import verify_body_runtime as verify
from palimpsest import body_profile as body
import test_verify_body_gains as fixtures


class HarnessChecks(unittest.TestCase):
    def row(self):
        mj,env=fixtures.GainChecks().probe()
        probe=body.ContactProbe(mj,env)
        probe.install();probe.begin(0)
        for index in range(10):
            env.data.time=index*.002
            mj.callback(env.model,env.data)
        env.data.time=.02
        interval=probe.end();probe.close()
        arrays=body.contact_arrays(interval)
        # Recorded nominal zero must map to exactly zero stage controls.
        arrays['body_stage_controls'][:]=0.
        row={'episode':0,'tick':0,'simulation_time':np.array(.02),
             'body_nominal_action':np.zeros(2,np.float64),'body_nominal_control':np.zeros(2,np.float32),
             'action':np.zeros(2,np.float64),'control':np.zeros(2,np.float64),
             'body_encoder_before':np.zeros(2,np.float64),'body_encoder_after':np.zeros(2,np.float64),
             'body_encoder_increment':np.zeros(2,np.float64),'body_dt':np.array(.02),**arrays}
        manifest={'body_profile_identity':body.profile_identity(),'body_contact_ownership':probe.ownership}
        return row,manifest

    def test_raw_audit_accepts_complete_packet_and_rejects_padding_counts_controls(self):
        row,manifest=self.row()
        result=verify.audit_ticks([row],manifest)
        self.assertEqual(result['pre_control_stages'],10)
        self.assertEqual(result['end_caches'],1)
        for field,index,value in [('body_contact_ids',(0,1,0),1),('body_contact_counts',(0,),129),
                                  ('body_contact_classes',(0,0),1),('body_stage_controls',(0,0),.1),
                                  ('body_encoder_increment',(0,),.1)]:
            bad=copy.deepcopy(row);bad[field][index]=value
            with self.assertRaises(ValueError):
                verify.audit_ticks([bad],manifest)
        self.assertEqual(verify.PROTOCOL['source_ticks'],36)
        self.assertEqual(verify.PROTOCOL['owners'],['source','restored','actions','policy'])
        self.assertEqual(verify.PROTOCOL['source_ticks'],sum(verify.PROTOCOL[k] for k in ('warmup_ticks','continuation_ticks','reset_ticks')))


if __name__=='__main__':
    unittest.main()
