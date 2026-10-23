"""Driver contract without simulation or model execution."""
import unittest
import record_route_material as material


class Supervisor:
    def __init__(self, premature=False):
        self.tick = 0
        self.phase = 'paused'
        self.calls = []
        self.premature = premature
    def describe(self, run):
        return {'status': 'ready', 'state': {'phase': self.phase, 'total_tick': self.tick,
                'episode': 0, 'revision': 0}, 'sample': {}}
    def call(self, run, kind, command):
        self.calls.append((kind, command))
        if kind == 'snapshot':
            return {'snapshot_id': 'snapshot'}
        assert command['expected_state'] == self.phase
        if command['kind'] == 'step':
            self.tick += 1
            if self.premature: self.phase = 'terminated'
        elif command['kind'] == 'run':
            self.tick = 600
            self.phase = 'truncated'
        return {'status': 'queued'}


class RouteTests(unittest.TestCase):
    def test_snapshot_at_exact_boundary_then_natural_parent_end(self):
        supervisor = Supervisor()
        snapshot = material.parent_sequence(supervisor, 'parent')
        self.assertEqual(snapshot, 'snapshot')
        self.assertEqual(len([x for x in supervisor.calls if x[0] == 'command' and x[1]['kind'] == 'step']), 100)
        self.assertEqual(supervisor.calls[100][0], 'snapshot')
        self.assertEqual(supervisor.phase, 'truncated')
    def test_early_outcome_fails_without_new_seed_or_retry(self):
        supervisor = Supervisor(premature=True)
        with self.assertRaises(ValueError): material.parent_sequence(supervisor, 'parent')
        self.assertEqual(supervisor.tick, 1)

