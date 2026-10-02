"""Source-only admission/counter tests; no ML or physics runtime imported."""
import ast
import copy
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import collect_male_recovery as recovery


def teacher_fixture():
    path = ROOT / 'upstream/fly-gym/agents/teacher_analytic_agent.py'
    recovery.upstream_contract(ROOT)
    tree = ast.parse(path.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'PlannerAnalyticTeacher')
    methods = {'_bad_contact_edge', '_choose_recovery_turn_dir', '_recovery_action',
               '_start_recovery', '_step_recovery', '_should_trigger_recovery', 'act'}
    cls.body = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in methods]
    namespace = {'np': np, 'pid_line_follower': lambda **kw: np.array([.7, .2], np.float32)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), str(path), 'exec'), namespace)
    teacher = namespace['PlannerAnalyticTeacher'].__new__(namespace['PlannerAnalyticTeacher'])
    teacher._rec_phase = None; teacher._rec_step_count = 0; teacher._rec_turn_dir = 1.
    teacher._prev_bad_contact = False; teacher.recovery_back_steps = 40; teacher.recovery_turn_steps = 5
    teacher.pid_state = object(); teacher.obstacle_disc_r = .4
    teacher.planner = SimpleNamespace(plan=lambda **kw: None)
    teacher._get_base_xy_yaw = lambda env: (np.array([0., 0.]), 0.)
    teacher._get_goal_xy = lambda env: np.array([2., 0.])
    teacher._get_obstacles_xy = lambda env: np.array([[1., 0.]])
    class Env:
        model = SimpleNamespace(opt=SimpleNamespace(timestep=.002))
        frame_skip = 10
        contact = True
        angle = .1
        calls = 0
        def _has_collision(self):
            self.calls += 1
            return (True, np.zeros(3), self.angle) if self.contact else (False, None, None)
    return teacher, Env()


class RecoveryContracts(unittest.TestCase):
    def test_actual_pinned_teacher_45_back_queries_latched_contact_and_clearance(self):
        camera_tree = ast.parse((ROOT / 'upstream/fly-gym/environment/mujoco_two_cam_env_random_obstacles.py').read_text())
        camera = next(node for node in ast.walk(camera_tree) if isinstance(node, ast.FunctionDef) and node.name == '_render_camera')
        self.assertFalse({'path_to_draw', 'target_to_draw'} & {node.attr for node in ast.walk(camera) if isinstance(node, ast.Attribute)})
        self.assertEqual([node.func.attr for node in ast.walk(camera) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)],
                         ['update_scene', 'render'])
        teacher, env = teacher_fixture(); rows = []
        for tick in range(47):
            env.contact = tick == 0
            query = recovery.query_teacher(teacher, env)
            rows.append({**query, 'tick': tick, 'stage0_intended_contact': tick == 0,
                         'action': recovery.executed_action(tick, query['expert_action'])})
        self.assertEqual(rows[0]['after']['count'], 1)
        self.assertTrue(rows[1]['before']['previous_bad_contact'])
        self.assertFalse(rows[1]['contact']['bad'])
        self.assertTrue(rows[1]['after']['previous_bad_contact'])
        self.assertEqual(rows[43]['after']['count'], 44)
        self.assertEqual(rows[44]['after']['phase'], None)
        for row in rows[:45]:
            self.assertEqual(row['expert_action'], np.array([-.35, -.1], np.float32).tolist())
        result = recovery.score_coverage(rows)
        self.assertTrue(result['passed']); self.assertEqual(result['first_cycle']['queries'], 45)
        no_reverse = copy.deepcopy(rows)
        for row in no_reverse: row['action'] = [.7, 0.]
        self.assertFalse(recovery.score_coverage(no_reverse)['actual_post_prefix_reverse'])
        # Independent sensor sample every query; teacher samples only inactive/final queries.
        self.assertEqual(env.calls, 47 + 4)

    def test_clear_then_new_rising_edge_and_same_query_completion_restart(self):
        teacher, env = teacher_fixture()
        for tick in range(45):
            env.contact = tick < 44
            recovery.query_teacher(teacher, env)
        self.assertFalse(teacher._prev_bad_contact)
        env.contact = True; env.angle = -.2
        row = recovery.query_teacher(teacher, env)
        self.assertTrue(row['transition']['started']); self.assertEqual(row['after']['direction'], 1.)
        # Actual boundary semantics with a deliberately authored valid counter state.
        teacher._rec_step_count = 44; teacher._prev_bad_contact = False
        env.angle = .2
        row = recovery.query_teacher(teacher, env)
        self.assertTrue(row['transition']['completed']); self.assertTrue(row['transition']['started'])
        self.assertEqual(row['after']['count'], 1)
        self.assertEqual(row['expert_action'], np.array([-.35, -.1], np.float32).tolist())

    def test_incomplete_cycle_cannot_be_scored_complete_and_labels_are_separate(self):
        teacher, env = teacher_fixture(); rows = []
        for tick in range(44):
            row = recovery.query_teacher(teacher, env)
            rows.append({**row, 'tick': tick, 'stage0_intended_contact': True,
                         'action': recovery.executed_action(tick, row['expert_action'])})
            expected = np.array([.7, 0.], np.float32).tolist() if tick < 32 else row['expert_action']
            self.assertEqual(recovery.executed_action(tick, row['expert_action']), expected)
        self.assertFalse(recovery.score_coverage(rows)['passed'])
        from palimpsest.engine import _action
        self.assertEqual(recovery.executed_action(0, rows[0]['expert_action']), _action([.7, 0.], manual=False).tolist())
        self.assertNotEqual(recovery.executed_action(0, rows[0]['expert_action']), rows[0]['expert_action'])
        broken = copy.deepcopy(rows[0]); broken['after']['count'] = 2
        with self.assertRaises(ValueError): recovery.validate_query(broken)
        completed = {'status': 'failed-functional', 'protocol_status': 'completed', 'owners_completed': 2,
                     'snapshot_files': 2, 'cases': {case['id']: {'status': 'completed-recording'} for case in recovery.CASES}}
        supervision = {'status': 'failed', 'returncode': 1}
        self.assertTrue(recovery.supervision_matches(completed, supervision))
        self.assertFalse(recovery.supervision_matches(completed, {**supervision, 'failure': 'LogLimit'}))
        self.assertFalse(recovery.supervision_matches({**completed, 'owners_completed': 1}, supervision))

    def test_pure_initial_clearance_rejects_and_resource_plan_is_bounded(self):
        self.assertEqual(set(recovery.geometry_preflight()), {case['id'] for case in recovery.CASES})
        from palimpsest.memory_world import validate_layout
        with self.assertRaises(ValueError): validate_layout(start_pose=[-.1, 0., 0.], goal_xy=[2., 0.])
        observation = {key: np.zeros((128, 128, 3), np.uint8) for key in ('cam_left', 'cam_right')}
        estimate = recovery.admission(observation)
        self.assertLess(estimate['aggregate_bytes'], 1024**3)
        self.assertEqual(estimate['allowances']['snapshot_bytes'], 2 * 16 * 1024**2)
        with self.assertRaises(ValueError): recovery.executed_action(120, [.7, 0.])
        teacher = SimpleNamespace(_rec_phase=None, _rec_step_count=0, _rec_turn_dir=1., _prev_bad_contact=False,
            recovery_back_steps=40, recovery_turn_steps=5, _xy_prev=None, _path=None,
            pid_state={'integral': 0.}, planner=SimpleNamespace(cache=None))
        env = SimpleNamespace(data=SimpleNamespace(time=0., qvel=np.zeros(2), ctrl=np.zeros(2)),
            _t=0, _speed=0., _stall_steps=0, _last_action=np.zeros(2), path_to_draw=None, target_to_draw=None,
            planner=SimpleNamespace(_cached_occ=None, _cached_obstacles_hash=None, _cached_clearance=None),
            visited={(0, 0)}, _bin_of=lambda *args: (0, 0), _base_xy=lambda: np.zeros(2), explore_binsize=.5, _prev_xy=np.zeros(2))
        engine = SimpleNamespace(controller='teacher', phase='paused', total_tick=0, episode_step=0, episode=0,
                                 task_state=None, memory=None, env=env, teacher=teacher)
        from palimpsest.engine import _teacher_fingerprint
        engine._teacher_reset_identity = _teacher_fingerprint(teacher)
        recovery.fresh_boundary(engine)
        teacher.pid_state['integral'] = .1
        with self.assertRaisesRegex(ValueError, 'untouched fresh'): recovery.fresh_boundary(engine)
        teacher.pid_state['integral'] = 0.
        env._prev_xy = np.array([.1, 0.])
        with self.assertRaisesRegex(ValueError, 'untouched fresh'): recovery.fresh_boundary(engine)

    def test_contact_admission_accepts_only_support_world_and_intended_robot_pair(self):
        pair = {'classification': 'unexpected_robot_contact', 'geom_names': ['base_geom', 'obstacle1']}
        interval = {'coverage_passed': True, 'callback_count': 10,
                    'stages': [{'pairs': [pair]} for _ in range(10)], 'end': {'pairs': [pair]}}
        self.assertTrue(recovery.contact_admission(interval, {'base_geom'}))
        for names in (['base_geom', 'obstacle0'], ['base_geom', 'left_wheel'], ['base_geom', 'unknown']):
            interval['stages'][0]['pairs'][0] = {**pair, 'geom_names': names}
            with self.assertRaises(ValueError): recovery.contact_admission(interval, {'base_geom', 'left_wheel'})

    def test_existing_loader_rejects_distinct_profile_before_reading_labels(self):
        from palimpsest.records import RunWriter
        from palimpsest.male_model import prepare_splits
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / uuid.uuid4().hex
            writer = RunWriter(run / 'recording', {'run_id': run.name, 'controller': 'teacher',
                'profile': recovery.PROFILE, 'teacher_privileged': True})
            writer.finish({}); writer.close()
            with self.assertRaisesRegex(ValueError, 'independent root teacher'):
                prepare_splits({'train': [run], 'dev': [run], 'held_out': [run]})


if __name__ == '__main__': unittest.main()
