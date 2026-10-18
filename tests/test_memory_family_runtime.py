"""Family runtime contracts using synthetic packets and mocked native boundaries."""
import copy
import unittest
from unittest.mock import patch

from palimpsest import memory, memory_decision as decision, memory_decision_world as world, replay
from palimpsest.engine import Engine
from palimpsest.profiles import validate_decision
from palimpsest import snapshots
from test_memory_decision import config
import test_memory_decision as decision_fixtures
import test_memory_decision_engine as engine_fixtures


class FamilyRuntimeTests(unittest.TestCase):
    def acquired(self, row, *, split='development', block=0):
        fixture = decision_fixtures.DecisionTests()
        fixture.setUp()
        fixture.case = world.make_family_case(split, block, row, 'change')
        fixture.position = fixture.case['start_pose'][:2]
        return fixture, fixture.acquired()

    def test_both_schedules_commit_only_after_the_declared_event_interval(self):
        schedules = set()
        for row in (0, 4):
            fixture, state = self.acquired(row)
            schedule = world.registered_profile(fixture.case['profile_sha256'])['arm_schedule']
            schedules.add((schedule['event_offset'], schedule['decision_offset']))
            boundary = fixture.tick
            state = decision.arm(state, boundary)
            self.assertEqual(state['supervisor']['decision_tick'], boundary + schedule['decision_offset'])
            for offset in range(schedule['decision_offset'] + 1):
                state, _, audit = fixture.step(state, token=int(offset >= schedule['event_offset']))
                commits = [item for item in audit if item['kind'] == 'memory_commitment']
                self.assertEqual(bool(commits), offset == schedule['decision_offset'])
                if offset < schedule['decision_offset']:
                    self.assertIsNone(state['supervisor']['route_id'])
            bad = copy.deepcopy(state)
            bad['supervisor']['decision_tick'] += 1
            with self.assertRaises(ValueError):
                decision.validate_state(bad)
        self.assertEqual(schedules, {(1, 2), (2, 3)})

    def test_selectors_follow_fact_mappings_with_independently_ordered_ids(self):
        for row in range(48):
            for condition in ('no-U', 'own'):
                fixture, state = self.acquired(row)
                graph = state['graph']
                chosen = min(graph['routes'], key=lambda route: (route['cost'], route['route_id']))
                if condition == 'own':
                    chosen = next(route for route in graph['routes']
                                  if route['subject_id'] != fixture.case['closure_subject_id'])
                artifact = memory.artifact(fixture.case['regime']) if condition == 'own' else memory.artifact()
                state = decision.configure_selector(state, config(condition), artifact)
                state = decision.arm(state, fixture.tick)
                schedule = world.registered_profile(fixture.case['profile_sha256'])['arm_schedule']
                for offset in range(schedule['decision_offset'] + 1):
                    state, _, _ = fixture.step(state, token=int(offset >= schedule['event_offset']))
                self.assertEqual(state['supervisor']['route_id'], chosen['route_id'], (row, condition))

    def test_graph_requires_exact_registered_profile_version(self):
        state = decision.initialize(world.make_family_case('development', 0, 0, 'change'))
        for version, profile in ((2, state['graph']['profile_sha256']),
                                 (3, world.PROFILE_SHA256), (True, world.PROFILE_SHA256),
                                 (3, 'f' * 64)):
            bad = copy.deepcopy(state)
            bad['graph'].update(version=version, profile_sha256=profile)
            with self.assertRaises(ValueError):
                decision.validate_state(bad)
        old = decision.initialize(world.make_case(0, 'local_cue', 'change'))
        self.assertEqual(old['graph']['version'], 2)
        self.assertEqual(decision.validate_state(old), old)

    def test_private_profile_metadata_preserves_legacy_and_identifies_family(self):
        old = validate_decision(world.SCENARIO, 'checker', 'flynn')
        self.assertEqual(old['version'], 2)
        self.assertEqual(old['label'], 'Memory decision (development)')
        for profile_hash in world.FAMILY_PROFILE_HASHES:
            profile = validate_decision(world.SCENARIO, 'checker', 'flynn', profile_sha256=profile_hash)
            self.assertEqual(profile['version'], 3)
            self.assertEqual(profile['label'], 'Memory family (development)')
            self.assertEqual(profile['world_protocol_sha256'], profile_hash)
            for key in ('id', 'max_steps', 'observation_profile', 'devices', 'controller_threads'):
                self.assertEqual(profile[key], old[key])

    def test_both_split_seed_boundaries_enter_the_actual_mocked_engine(self):
        helpers = engine_fixtures.DecisionEngineTests()
        helpers.setUp()
        self.addCleanup(helpers.doCleanups)
        for split in ('development', 'held-out'):
            for block in (0, 2**23 - 1):
                helpers.case = world.make_family_case(split, block, 47, 'change')
                admitted = Engine._memory_restore(helpers.case, world.SCENARIO, 'flynn', 'cpu', None, False, None)
                self.assertEqual(admitted[0], helpers.case)
                engine = helpers.engine()
                self.assertEqual(engine.seed, helpers.case['seed'])

    def test_mocked_engine_acquired_restore_retains_selector_and_schedule_invariants(self):
        helpers = engine_fixtures.DecisionEngineTests()
        helpers.setUp()
        self.addCleanup(helpers.doCleanups)
        for split, block, row in (('development', 0, 0), ('development', 0, 4),
                                  ('held-out', 2**23 - 1, 47)):
            fixture, state = self.acquired(row, split=split, block=block)
            helpers.case = fixture.case
            engine = helpers.engine()
            self.assertEqual(engine.memory['graph']['version'], 3)
            self.assertTrue(all(fact['status'] == 'unknown' for fact in engine.memory['m']['facts']))
            engine.memory = state
            engine.total_tick = engine.episode_step = fixture.tick
            engine.world_task_state['last_tick'] = fixture.tick - 1
            engine.env.data.qpos[:] = [*fixture.position, fixture.yaw]
            before = helpers.snapshot(engine)
            engine.configure_memory_selector(config('own'), memory.artifact(fixture.case['regime']))
            self.assertEqual(decision.invariant_hashes(before), decision.invariant_hashes(helpers.snapshot(engine)))
            engine.arm_memory_decision()
            schedule = world.registered_profile(fixture.case['profile_sha256'])['arm_schedule']
            self.assertEqual(engine.world_task_state['event_tick'], fixture.tick + schedule['event_offset'])
            self.assertEqual(engine.world_task_state['decision_tick'], fixture.tick + schedule['decision_offset'])
            source = helpers.snapshot(engine)
            with patch.object(snapshots, 'restore', side_effect=lambda saved, env, **kwargs:
                              (env._get_obs(), saved['application'])):
                branch = helpers.engine(restore_snapshot=source)
            self.assertEqual(branch.memory, engine.memory)
            self.assertEqual(branch.world_task_state, engine.world_task_state)
            self.assertEqual(decision.invariant_hashes(source), decision.invariant_hashes(helpers.snapshot(branch)))
            bad = copy.deepcopy(source)
            bad['application']['memory']['supervisor']['decision_tick'] += 1
            with patch('palimpsest.records.RunWriter') as writer, self.assertRaises(ValueError):
                Engine.open(helpers.root, helpers.root, helpers.root / 'never-created', controller='flynn',
                            device='cpu', seed=fixture.case['seed'], scenario=world.SCENARIO,
                            memory_case=fixture.case, restore_snapshot=bad)
            writer.assert_not_called()

    def test_replay_admits_exact_family_cases_and_binds_existing_runtime_sources(self):
        for kind in ('change', 'null', 'no-event'):
            case = world.make_family_case('development', 0, 2, kind)
            manifest = {'memory_case': case, 'memory_case_sha256': memory.sha256(case),
                        'acquisition_protocol_sha256': case['acquisition_protocol_sha256']}
            self.assertEqual(replay.recorded_memory_case(manifest, world.SCENARIO), case)
            with self.assertRaises(ValueError):
                replay.recorded_memory_case(manifest, 'memory-passages')
            bad = copy.deepcopy(manifest)
            bad['memory_case']['row'] = 0
            with self.assertRaises(ValueError):
                replay.recorded_memory_case(bad, world.SCENARIO)
        hashes = {key: 'a' * 64 for key in replay._RUNTIME + replay._DECISION_RUNTIME}
        event = {'kind': 'environment', 'source_sha256': hashes,
                 'lock_sha256': 'd' * 64, 'upstream_commit': 'e' * 40}
        replay._compatible([event], [event], 'flynn', world.SCENARIO)
        changed = {**event, 'source_sha256': {**hashes, 'src/palimpsest/memory_decision_world.py': 'b' * 64}}
        with self.assertRaises(ValueError):
            replay._compatible([event], [changed], 'flynn', world.SCENARIO)
