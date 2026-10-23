"""Driver contract fixtures; no renderer, model or native allocation."""
import unittest
from record_choir_material import drive

class Engine:
    def __init__(self, length=600, failed=False):
        self.total_tick=0; self.episode=0; self.phase='paused'; self.tick=0
        self.length=length; self.failed=failed; self.pending=None; self.seeds=[]
    def submit(self, c):
        assert c['expected_state']==self.phase and c['expected_episode']==self.episode
        self.pending=c
        return {'status':'queued'}
    def advance(self):
        c=self.pending; self.pending=None
        if c and c['kind']=='reset':
            self.seeds.append(c['payload']['seed']); self.episode+=1; self.tick=0; self.phase='paused'
        elif c and c['kind']=='run': self.phase='running'
        if self.phase=='running':
            self.total_tick+=1; self.tick+=1
            if self.tick==self.length: self.phase='terminated'
            if self.failed: self.phase='failed'

class ChoirMaterialTests(unittest.TestCase):
    def test_exact_target_and_final_natural_episode(self):
        for length, expected in [(600,6000),(599,6589),(100,6000)]:
            e=Engine(length); result=drive(e,lambda _:None)
            self.assertEqual(result['intervals'],expected)
            self.assertEqual(e.phase,'terminated')
            self.assertEqual(e.seeds,list(range(1,e.episode+1)))
    def test_exhaustion_and_failure_do_not_continue(self):
        e=Engine(1)
        with self.assertRaisesRegex(ValueError,'allocation exhausted'): drive(e,lambda _:None)
        self.assertEqual(e.episode,63)
        e=Engine(failed=True)
        with self.assertRaisesRegex(ValueError,'engine failed'): drive(e,lambda _:None)
        self.assertEqual(e.total_tick,1)
    def test_interval_ceiling_and_unexpected_pause(self):
        with self.assertRaisesRegex(ValueError,'ceiling'): drive(Engine(7000),lambda _:None)
