"""v4 S2/S3 evaluator gates on synthetic owner results; no simulator, scene, checkpoint or held-out input."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from palimpsest import male_navigation_research_v4 as research
import evaluate_male_navigation_v4 as evaluator
import train_male_navigation_v4 as trainer

ROOT = Path(__file__).resolve().parents[1]
DEV = (3160, 3161, 3162, 3163)
HELD = tuple(range(3170, 3178))


def sha(text):
    return hashlib.sha256(str(text).encode()).hexdigest()


def owner_result(case, goal, ticks=None):
    scene = case['scene_seed']
    reason = 'goal' if goal else 'collision'
    ticks = ticks or 100 + scene % 50
    return {'status': 'completed-recording', 'case': copy.deepcopy(case), 'teacher_queries': 0,
            'initial_fingerprint': {'inputs': sha(f'inputs-{scene}'), 'state': sha(f'state-{scene}')},
            'geometry': {'layout': sha(f'layout-{scene}'), 'full_scene': sha(f'full-{scene}')},
            'raw_payload_sha256': sha(case['id']), 'ticks': ticks, 'executed_ticks': ticks,
            'final_state': {'phase': 'terminated', 'episode': 0, 'total_tick': ticks,
                            'last_outcome': {'reason': reason}}}


def prior():
    return {'sources': [{'geometry': {'layout': sha(f'layout-{s}'), 'full_scene': sha(f'full-{s}')},
                         'initial_fingerprint': {'inputs': sha(f'inputs-{s}')},
                         'raw_payload_sha256': sha(f'payload-{s}')}
                        for s in (1000, 1008, 2100, 3100, 3103)]}


def goals_owner(goals, calls=None, mutate=None):
    """Owner returning goal per (scene, seed, arm) from ``goals``; optional per-case mutation."""
    def owner(case):
        if calls is not None:
            calls.append(case['id'])
        result = owner_result(case, goals(case))
        if mutate is not None:
            mutate(case, result)
        return result
    return owner


def augmented_goals(per_seed_scenes):
    """Augmented seed s scores at scenes per_seed_scenes[s]; the old arm never scores."""
    return lambda case: case['arm'] == 'augmented' and case['scene_seed'] in per_seed_scenes[case['training_seed']]


PASS = {10: DEV[:3], 11: DEV[1:], 12: DEV}


class Temp(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, name, value):
        path = self.root / name
        path.write_bytes(json.dumps(value, sort_keys=True).encode())
        return path


class Plan(unittest.TestCase):
    def test_exact_development_case_order_and_frozen_protocol_ids(self):
        self.assertEqual(len(evaluator.CASES), 24)
        self.assertEqual([(c['scene_seed'], c['training_seed'], c['arm']) for c in evaluator.CASES],
                         [(scene, seed, arm) for scene in DEV for seed in (10, 11, 12)
                          for arm in ('old-corpus', 'augmented')])
        self.assertEqual(evaluator.CASES[0]['id'], 'dev-3160-seed-10-old-corpus')
        study = trainer.protocol()
        used = evaluator.check_protocol(study)
        self.assertFalse(used & set(DEV + HELD))
        for path, value in ((('fresh_evaluation', 'development', 'scene_ids'), [3160, 3161, 3162, 3164]),
                            (('fresh_evaluation', 'held_out', 'scene_ids'), list(range(3170, 3177))),
                            (('fresh_evaluation', 'held_out', 'threshold_change'), True),
                            (('fresh_evaluation', 'development', 'gate'), 'each augmented seed >= 2 of 4'),
                            (('scene_id_disjointness', 'candidate_screen', 'used_ranges_on_record'),
                             ['3160-3163'])):
            changed = copy.deepcopy(study)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(evaluator.Refusal):
                evaluator.check_protocol(changed)
        with self.assertRaises(evaluator.Refusal):
            evaluator.check_case({**evaluator.CASES[0], 'scene_seed': 3170}, evaluator.CASES)

    def test_no_module_constant_exposes_held_out_cases(self):
        for name, value in vars(evaluator).items():
            if isinstance(value, (tuple, list)) and value and isinstance(value[0], dict):
                with self.subTest(name=name):
                    self.assertFalse({c.get('scene_seed') for c in value} & set(HELD))


class NativeScoring(unittest.TestCase):
    def test_goal_only_from_a_native_natural_boundary_within_600_ticks(self):
        case = evaluator.CASES[0]
        self.assertTrue(evaluator.native_goal(owner_result(case, True)))
        self.assertFalse(evaluator.native_goal(owner_result(case, False)))
        cap = owner_result(case, False, ticks=600)
        cap['final_state'].update(phase='truncated', last_outcome={'reason': 'time_limit'})
        self.assertFalse(evaluator.native_goal(cap))
        invalid = []
        for mutation in ('early_time_limit', 'over_cap', 'tick_mismatch', 'executed', 'episode',
                         'unknown', 'running'):
            result = owner_result(case, True)
            if mutation == 'early_time_limit':
                result['final_state'].update(phase='truncated', last_outcome={'reason': 'time_limit'})
            if mutation == 'over_cap':
                result['ticks'] = result['executed_ticks'] = result['final_state']['total_tick'] = 601
            if mutation == 'tick_mismatch':
                result['final_state']['total_tick'] += 1
            if mutation == 'executed':
                result['executed_ticks'] += 1
            if mutation == 'episode':
                result['final_state']['episode'] = 1
            if mutation == 'unknown':
                result['final_state']['last_outcome'] = {'reason': 'rescued'}
            if mutation == 'running':
                result['final_state']['phase'] = 'paused'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                evaluator.native_goal(result)
            invalid.append(mutation)
        self.assertEqual(len(invalid), 7)


class Development(unittest.TestCase):
    def test_exact_order_and_per_augmented_seed_three_of_four_gate(self):
        calls = []
        report = evaluator.development(goals_owner(augmented_goals(PASS), calls), prior())
        self.assertEqual(calls, [case['id'] for case in evaluator.CASES])
        admission = report['admission']
        self.assertEqual((report['status'], admission['status']), ('completed', 'passed-gate'))
        self.assertEqual(admission['goals_by_seed_arm'],
                         {'10:old-corpus': 0, '10:augmented': 3, '11:old-corpus': 0, '11:augmented': 3,
                          '12:old-corpus': 0, '12:augmented': 4})
        self.assertEqual(admission['old_arm'], 'reported-not-gated')
        self.assertEqual(admission['held_out_status'], 'eligible-pending-separate-owner-go')
        self.assertEqual(sorted(admission['matched_scene_initials']), [str(s) for s in DEV])
        self.assertEqual(admission['paired_scene_differences']['3160:10'], 1)
        # One augmented seed at 2/4 fails, even though the other seeds and the old arm are perfect.
        failing = {**PASS, 11: DEV[:2]}
        old_perfect = lambda case: case['arm'] == 'old-corpus' or augmented_goals(failing)(case)
        report = evaluator.development(goals_owner(old_perfect), prior())
        self.assertEqual(report['admission']['status'], 'failed-gate')
        self.assertEqual(report['admission']['goals_by_seed_arm']['11:augmented'], 2)
        self.assertEqual(report['admission']['held_out_status'], 'locked-permanently')

    def test_all_six_owners_of_each_scene_share_the_scientific_initial(self):
        def fingerprint(case, result):
            if case['id'] == 'dev-3161-seed-12-augmented':
                result['initial_fingerprint']['state'] = sha('other')

        def geometry(case, result):
            if case['id'] == 'dev-3162-seed-10-old-corpus':
                result['geometry']['full_scene'] = sha('moved goal')

        for mutate in (fingerprint, geometry):
            report = evaluator.development(goals_owner(augmented_goals(PASS), mutate=mutate), prior())
            with self.subTest(mutate=mutate.__name__):
                self.assertEqual(report['admission']['status'], 'not-admitted')
                self.assertIn('scientific initial', report['admission']['error'])

    def test_disjointness_against_prior_s0_and_other_fresh_scenes(self):
        source = prior()['sources'][3]

        def prior_layout(case, result):
            if case['scene_seed'] == 3163:
                result['geometry']['layout'] = source['geometry']['layout']

        def prior_input(case, result):
            if case['scene_seed'] == 3160:
                result['initial_fingerprint']['inputs'] = source['initial_fingerprint']['inputs']

        def prior_payload(case, result):
            if case['id'] == 'dev-3162-seed-11-augmented':
                result['raw_payload_sha256'] = source['raw_payload_sha256']

        def fresh_layout(case, result):
            if case['scene_seed'] == 3161:
                result['geometry']['layout'] = sha('layout-3160')

        def fresh_payload(case, result):
            if case['id'] == 'dev-3163-seed-10-old-corpus':
                result['raw_payload_sha256'] = sha('dev-3160-seed-10-old-corpus')

        for mutate in (prior_layout, prior_input, prior_payload, fresh_layout, fresh_payload):
            report = evaluator.development(goals_owner(augmented_goals(PASS), mutate=mutate), prior())
            with self.subTest(mutate=mutate.__name__):
                self.assertEqual(report['admission']['status'], 'not-admitted')
                self.assertIn('repeat', report['admission']['error'])
                self.assertEqual(report['admission']['held_out_status'], 'locked-permanently')

    def test_teacher_access_or_incomplete_recording_is_not_admitted(self):
        def teacher(case, result):
            if case['id'] == 'dev-3160-seed-11-augmented':
                result['teacher_queries'] = 1
        report = evaluator.development(goals_owner(augmented_goals(PASS), mutate=teacher), prior())
        self.assertEqual(report['admission']['status'], 'not-admitted')

    def test_kill_or_timeout_is_operational_and_never_a_non_goal(self):
        calls = []

        def owner(case):
            calls.append(case['id'])
            if case['id'] == 'dev-3161-seed-10-augmented':
                raise TimeoutError('RuntimeMaxSec kill')
            return owner_result(case, augmented_goals(PASS)(case))

        report = evaluator.development(owner, prior())
        self.assertEqual(report['status'], 'operational-failure')
        self.assertEqual(len(calls), 8)
        rows = list(report['cases'].values())
        self.assertEqual(rows[7]['status'], 'operational-failure')
        self.assertEqual(rows[7]['error']['type'], 'TimeoutError')
        self.assertEqual({row['status'] for row in rows[8:]}, {'not_started'})
        admission = report['admission']
        self.assertEqual(admission['status'], 'not-admitted-operational-failure')
        self.assertEqual(set(admission['goals_by_seed_arm'].values()), {0})
        self.assertEqual(admission['held_out_status'], 'locked-permanently')
        killed = evaluator.development(lambda case: {'status': 'killed'}, prior())
        self.assertEqual(killed['admission']['status'], 'not-admitted-operational-failure')
        self.assertEqual(len([r for r in killed['cases'].values() if r['status'] == 'not_started']), 23)


class HeldOut(Temp):
    def setUp(self):
        super().setUp()
        report = evaluator.development(goals_owner(augmented_goals(PASS)), prior())
        self.dev_report = self.root / 'dev'
        self.dev_report.mkdir()
        evaluator.publish_report(self.dev_report, report)
        self.dev_report = self.dev_report / 'report.json'
        self.report_sha = hashlib.sha256(self.dev_report.read_bytes()).hexdigest()
        self.dev_go = self.write('s2-go.json', {'decision': 'GO', 'lane': 'navigation', 'stage': 'S2',
                                                'protocol_sha256': trainer.PROTOCOL_SHA256,
                                                's1_report_sha256': '0' * 64, 'granted_by': 'owner',
                                                'granted_at': '2026-11-09'})
        self.go = self.write('s3-go.json', self.go_value())
        self.ledger = self.write('ledger.jsonl', {'lane': 'navigation', 'stage': 'S2', 'event': 'charged',
                                                  'cpu_seconds': 4000.0})

    def go_value(self, **changes):
        return {'decision': 'GO', 'lane': 'navigation', 'stage': 'S3', 'protocol_sha256': trainer.PROTOCOL_SHA256,
                'development_report_sha256': self.report_sha, 'granted_by': 'owner',
                'granted_at': '2026-11-10', **changes}

    def test_held_out_unreachable_without_development_pass_and_separate_go(self):
        with self.assertRaises(evaluator.Refusal):
            evaluator.held_out(lambda case: self.fail('owner ran'), prior(),
                               evaluator.HeldOutAdmission(
                                   tuple({'id': f'held-out-{s}-seed-{d}-{a}', 'scene_seed': s,
                                          'training_seed': d, 'arm': a}
                                         for s in HELD for d in (10, 11, 12) for a in ('old-corpus', 'augmented')),
                                   self.report_sha, '0' * 64, 0.))
        failing = evaluator.development(goals_owner(augmented_goals({**PASS, 12: DEV[:2]})), prior())
        (self.root / 'failed').mkdir()
        evaluator.publish_report(self.root / 'failed', failing)
        go_failed = self.write('go-failed.json', self.go_value(
            development_report_sha256=hashlib.sha256((self.root / 'failed/report.json').read_bytes()).hexdigest()))
        cases = (
            ((self.root / 'failed/report.json', go_failed, self.ledger, self.dev_go), 'development pass'),
            ((self.dev_report, self.root / 'missing.json', self.ledger, self.dev_go), None),
            ((self.dev_report, self.dev_go, self.ledger, self.dev_go), 'separate'),
            ((self.dev_report, self.write('g1.json', self.go_value(stage='S2')), self.ledger, self.dev_go), 'S3'),
            ((self.dev_report, self.write('g2.json', self.go_value(development_report_sha256='0' * 64)),
              self.ledger, self.dev_go), 'S3'),
            ((self.dev_report, self.write('g3.json', self.go_value(protocol_sha256=trainer.V3_PROTOCOL_SHA256)),
              self.ledger, self.dev_go), 'v3'),
            ((self.dev_report, self.write('g4.json', self.go_value(granted_by='')), self.ledger, self.dev_go), 'S3'),
            ((self.dev_report, self.go, self.write('over.jsonl', {'lane': 'navigation', 'stage': 'S2',
                                                                   'event': 'charged', 'cpu_seconds': 5642.0}),
              self.dev_go), 'exceeds'),
        )
        for arguments, message in cases:
            with self.subTest(message=message):
                with self.assertRaises((evaluator.Refusal, OSError, ValueError)) as caught:
                    evaluator.admit_held_out(*arguments)
                if message:
                    self.assertIn(message, str(caught.exception))

    def test_admitted_held_out_fixes_3170_3177_and_six_of_eight(self):
        admission = evaluator.admit_held_out(self.dev_report, self.go, self.ledger, self.dev_go)
        self.assertEqual([(c['scene_seed'], c['training_seed'], c['arm']) for c in admission.cases],
                         [(s, d, a) for s in HELD for d in (10, 11, 12) for a in ('old-corpus', 'augmented')])
        self.assertAlmostEqual(admission.lane_charge_through_s2, 4001.832)
        calls = []
        six = {10: HELD[:6], 11: HELD[2:], 12: HELD}
        report = evaluator.held_out(goals_owner(augmented_goals(six), calls), prior(), admission)
        self.assertEqual(len(calls), 48)
        self.assertEqual(report['admission']['status'], 'passed-gate')
        self.assertEqual(report['admission']['threshold_per_augmented_seed'], 6)
        self.assertEqual(report['development_report_sha256'], self.report_sha)
        with self.assertRaisesRegex(evaluator.Refusal, 'admit_held_out'):
            evaluator.held_out(goals_owner(augmented_goals(six)), prior(), admission)  # Consumed.
        again = evaluator.admit_held_out(self.dev_report, self.go, self.ledger, self.dev_go)
        five = {**six, 11: HELD[3:]}
        report = evaluator.held_out(goals_owner(augmented_goals(five)), prior(), again)
        self.assertEqual(report['admission']['status'], 'failed-gate')
        self.assertEqual(report['admission']['goals_by_seed_arm']['11:augmented'], 5)


class Cli(Temp):
    def published_s1(self):
        output = self.root / 's1'
        output.mkdir()
        report = {'id': trainer.REPORT_ID, 'status': 'completed-navigation-v4-training',
                  'training_completed': True, 'held_out_status': 'locked_unopened', 'qualification_claims': [],
                  'models': []}
        for seed, arm in trainer.planned_models():
            item = trainer.write_exclusive(output / f'seed-{seed}-{arm}.pt', f'{seed}{arm}'.encode())
            report['models'].append({'seed': seed, 'arm': arm, 'status': 'completed', 'checkpoint': item,
                                     'optimizer_updates': 1440, 'selected_optimizer_update': 1440,
                                     'real_row_presentations': 46080})
        trainer.publish_success(output, report)
        return output

    def invoke(self, argv):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = evaluator.main(argv)
        return code, json.loads(stdout.getvalue())

    def test_plan_only_default_lists_development_only(self):
        code, value = self.invoke([])
        self.assertEqual((code, value['mode'], len(value['cases'])), (0, 'plan-only', 24))
        self.assertFalse({c['scene_seed'] for c in value['cases']} & set(HELD))
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            evaluator.main(['--held-out'])

    def test_go_route_requires_admitted_s1_named_go_and_never_binds_native_owner(self):
        s1 = self.published_s1()
        with self.assertRaisesRegex(evaluator.Refusal, 'exact tree the binding loads'):
            evaluator.admit_candidates(s1)
        sha = hashlib.sha256((s1 / 'report.json').read_bytes()).hexdigest()
        with patch.object(research, 'S1_OUTPUT', s1):
            with self.assertRaisesRegex(evaluator.Refusal, 'binding constant'):
                evaluator.admit_candidates(s1)
        patcher = patch.multiple(research, S1_OUTPUT=s1, REPORT_SHA256=sha)
        patcher.start(); self.addCleanup(patcher.stop)
        _, s1_sha = evaluator.admit_candidates(s1)
        output = self.root / 'eval'
        go = self.write('go.json', {'decision': 'GO', 'lane': 'navigation', 'stage': 'S2',
                                    'protocol_sha256': trainer.PROTOCOL_SHA256, 's1_report_sha256': s1_sha,
                                    'amendment_2_sha256': evaluator.AMENDMENT_SHA256,
                                    'granted_by': 'owner', 'granted_at': '2026-11-09'})
        no_amendment = self.write('no-amendment.json', {'decision': 'GO', 'lane': 'navigation', 'stage': 'S2',
                                  'protocol_sha256': trainer.PROTOCOL_SHA256, 's1_report_sha256': s1_sha,
                                  'granted_by': 'owner', 'granted_at': '2026-11-09'})
        wrong = self.write('wrong.json', {'decision': 'GO', 'lane': 'navigation', 'stage': 'S3',
                                          'protocol_sha256': trainer.PROTOCOL_SHA256, 's1_report_sha256': s1_sha,
                                          'amendment_2_sha256': evaluator.AMENDMENT_SHA256,
                                          'granted_by': 'owner', 'granted_at': '2026-11-09'})
        extra = ['--assets', str(self.root / 'assets'), '--corpus-pin', str(self.root / 'pin.json')]
        for argv, message in ((['--go', str(go)], '--s1-output'),
                              (['--go', str(wrong), '--s1-output', str(s1), '--output', str(output), *extra], 'stage S2'),
                              (['--go', str(no_amendment), '--s1-output', str(s1), '--output', str(output), *extra],
                               'amendment 2'),
                              (['--go', str(go), '--s1-output', str(s1), '--output', str(output), *extra],
                               'run_research_stage'),
                              (['--plan-only', '--go', str(go)], 'exclusive')):
            code, value = self.invoke(argv)
            with self.subTest(message=message):
                self.assertEqual((code, value['status']), (2, 'refused'))
                self.assertIn(message, value['reason'])
                self.assertFalse(output.exists())
        with self.assertRaisesRegex(evaluator.Refusal, 'run_development'):
            evaluator.native_owner(evaluator.CASES[0])
        (s1 / 'publication.json').unlink()
        with self.assertRaisesRegex(evaluator.Refusal, 'terminal S1'):
            evaluator.admit_candidates(s1)


if __name__ == '__main__':
    unittest.main()
