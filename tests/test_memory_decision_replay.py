"""Pure historical/v2 replay admission and provenance dispatch."""
import unittest
from palimpsest import memory,replay,memory_experiment,memory_decision_world as world


class DecisionReplayTests(unittest.TestCase):
    def test_historical_reader_and_v2_reader_dispatch_by_scenario_without_relabeling(self):
        self.assertTrue(hasattr(replay,'recorded_memory_case'),'scenario-dispatched reader is required')
        for scenario,case in (('memory-passages',memory_experiment.make_world_case(0,'local_cue','development-test')),
                              (world.SCENARIO,world.make_case(0,'local_cue','change'))):
            manifest={'memory_case':case,'memory_case_sha256':memory.sha256(case),
                      'acquisition_protocol_sha256':case['acquisition_protocol_sha256']}
            self.assertEqual(replay.recorded_memory_case(manifest,scenario),case)
            with self.assertRaises(ValueError):
                replay.recorded_memory_case(manifest,world.SCENARIO if scenario=='memory-passages' else 'memory-passages')
        self.assertIsNone(replay.recorded_memory_case({},'reproduction'))

    def test_v2_provenance_includes_both_runtime_modules_while_legacy_keys_stay_fixed(self):
        hashes={key:'a'*64 for key in replay._RUNTIME}
        hashes.update({'src/palimpsest/memory_decision.py':'b'*64,'src/palimpsest/memory_decision_world.py':'c'*64})
        event={'kind':'environment','source_sha256':hashes,'lock_sha256':'d'*64,'upstream_commit':'e'*40}
        changed={**event,'source_sha256':{**hashes,'src/palimpsest/memory_decision.py':'f'*64}}
        replay._compatible([event],[changed],'flynn','memory-passages')
        with self.assertRaises(ValueError):
            replay._compatible([event],[changed],'flynn',world.SCENARIO)
