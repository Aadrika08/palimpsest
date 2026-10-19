"""Software fixtures for the v5 runner; no Playwright, browser, owner or lease."""
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from palimpsest.storage import StorageBudget, StorageLimits

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('manual_v5_fixture', ROOT / 'scripts/manual_lab_refresh_v5.py')
v5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v5)
GiB = 1024**3


def even(count, period=1000 / 30, offset=0.):
    return [offset + index * period for index in range(count)]


def cycle(ordinal, idle, streaming, stamps=None, acks=(20., 25.), status='passed'):
    stamps = even(120) if stamps is None else stamps
    return {'ordinal': ordinal, 'cadence': {'display_commits_ms': stamps, 'started_ms': 0., 'ended_ms': 4000.,
            'acknowledgement_raw_ms': list(acks)}, 'replay': {'mode': 'Action replay', 'result': {'status': status}},
            'idle_gc': {'listeners': idle, 'nodes': 1500, 'js_heap_used': 4 * 1024**2},
            'streaming_raw': {'listeners': streaming, 'nodes': 1500, 'js_heap_used': 5 * 1024**2},
            'reloaded': ordinal % 5 == 4}


class Cadence(unittest.TestCase):
    def test_runner_mirrors_the_ui_constants(self):
        text = (ROOT / 'ui/tests/measurement.ts').read_text()
        literal = re.search(r'CADENCE_ACCEPTANCE=\{([^}]*)\}', text).group(1)
        ui = {key: int(value) for key, value in (item.split(':') for item in literal.split(','))}
        self.assertEqual(ui, v5.CADENCE)

    def test_decided_tolerance(self):
        verdict = v5.cadence_verdict([(even(240), 0., 8000.)], [20.])
        self.assertTrue(verdict['passed'])
        self.assertAlmostEqual(verdict['mean_hz'], 30.)
        self.assertAlmostEqual(verdict['interarrival_p99_ms'], 1000 / 30)
        coalesced = [stamp for index, stamp in enumerate(even(240)) if index != 120]
        self.assertTrue(v5.cadence_verdict([(coalesced, 0., 8000.)], [20.])['passed'])
        self.assertFalse(v5.cadence_verdict([(even(225, 35.7), 0., 8041.)], [20.])['passed'])  # 27.98 Hz
        gappy, stamp = [], 0.
        for index in range(240):
            gappy.append(stamp)
            stamp += 80 if index % 30 == 0 else 32
        verdict = v5.cadence_verdict([(gappy, 0., gappy[-1] + 1)], [20.])
        self.assertGreaterEqual(verdict['mean_hz'], 29)
        self.assertFalse(verdict['passed'])
        self.assertFalse(v5.cadence_verdict([(even(240), 0., 8000.)], [150.])['passed'])
        self.assertFalse(v5.cadence_verdict([(even(240), 0., 8000.)], [])['passed'])
        self.assertFalse(v5.cadence_verdict([([], 0., 8000.)], [20.])['passed'])

    def test_pooled_windows_do_not_count_gaps_between_windows(self):
        windows = [(even(120, offset=10_000. * index), 10_000. * index, 10_000. * index + 4000.) for index in range(3)]
        verdict = v5.cadence_verdict(windows, [20.] * 6)
        self.assertEqual(verdict['display_updates'], 360)
        self.assertAlmostEqual(verdict['mean_hz'], 30.)
        self.assertTrue(verdict['passed'])


class Listeners(unittest.TestCase):
    def verdict(self, idle, streaming=None):
        streaming = streaming or [value + 900 for value in idle]
        return v5.listener_verdict([cycle(index, idle[index], streaming[index]) for index in range(len(idle))])

    def test_reclaimed_streaming_growth_passes(self):
        result = self.verdict([257, 256, 258, 256, 257, 259, 256, 258, 257], [363, 1044, 1520, 600, 4400, 7700, 980, 2000, 512])
        self.assertTrue(result['passed'])
        self.assertTrue(all(value > 0 for value in result['listeners']['streaming_minus_idle_gc']))

    def test_monotonic_unreclaimed_growth_fails(self):
        result = self.verdict([250 + 20 * index for index in range(30)])
        self.assertFalse(result['passed'])
        self.assertGreater(result['listeners']['unreclaimed_growth'], result['listeners']['allowance'])

    def test_bounded_growth_within_allowance_passes(self):
        self.assertTrue(self.verdict([250 + index for index in range(30)])['passed'])

    def test_too_few_cycles_fail(self):
        self.assertFalse(self.verdict([250, 250])['passed'])


class DomGate(unittest.TestCase):
    def cycles(self, nodes):
        return [{**cycle(index, 256, 1100), 'idle_gc': {'listeners': 256, 'nodes': value, 'js_heap_used': 4 * 1024**2}}
                for index, value in enumerate(nodes)]

    def test_v4_dom_growth_fails_and_bounded_nodes_pass(self):
        v4_session = [1816, 1918, 2020, 2122, 1200, 2161, 2263, 2365, 2467, 1545, 2506, 2608, 2710, 2812, 1890, 2869, 2953]
        result = v5.listener_verdict(self.cycles(v4_session))
        self.assertTrue(result['listeners']['passed'])
        self.assertFalse(result['dom_nodes']['passed'])
        self.assertFalse(result['passed'])
        bounded = [1500, 1520, 1490, 1510, 1200, 1505, 1515, 1495, 1500, 1210, 1508, 1512, 1499, 1502, 1205]
        self.assertTrue(v5.listener_verdict(self.cycles(bounded))['passed'])
        self.assertEqual(v5.DOM_ALLOWANCE['min_cycles'], 3)

    def test_evaluation_gates_dom_nodes(self):
        with tempfile.TemporaryDirectory() as directory:
            v5.configure(endurance_seconds=3600, cycle_seconds=120)
            root = Evaluation().phase(Path(directory))
            path = next(root.glob('endurance/test-results/*/lab-endurance.json'))
            data = json.loads(path.read_text())
            for index, item in enumerate(data['cycles']):
                item['idle_gc']['nodes'] = 1500 + 70 * index
            path.write_text(json.dumps(data))
            result = v5.evaluate(root)
            self.assertFalse(result['passed'])
            self.assertFalse(result['checks']['listener_growth']['dom_nodes']['passed'])


class Detached(unittest.TestCase):
    def test_progress_heartbeat_is_atomic_and_counts_cycles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            v5.configure(phase=root / 'phase', endurance_seconds=3600, cycle_seconds=120)
            report = root / 'phase/endurance/test-results/x/lab-endurance.json'
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps({'cycles': [{}, {}, {}]}))
            with patch.object(v5, 'free_bytes', return_value=5 * GiB):
                v5.write_progress('endurance', status='running')
            progress = json.loads((root / 'phase/progress.json').read_text())
            self.assertEqual((progress['schema'], progress['status'], progress['phase']), ('manual-lab-refresh-v5-progress', 'running', 'endurance'))
            self.assertEqual((progress['endurance_cycles_completed'], progress['endurance_cycles_expected']), (3, 30))
            self.assertEqual(progress['pid'], v5.os.getpid())
            self.assertIn('updated_utc', progress)
            self.assertEqual(progress['free_bytes']['dev_shm'], 5 * GiB)
            self.assertFalse(list((root / 'phase').glob('*.tmp')))

    def test_checked_wait_refreshes_the_heartbeat(self):
        class Done:
            returncode = 0
            calls = 0
            def poll(self):
                self.calls += 1
                return None if self.calls < 3 else 0
        with ExitStack() as stack:
            for name in ('observe', 'BUDGET', 'check_server_logs', 'shm_floors'):
                stack.enter_context(patch.object(v5, name))
            beat = stack.enter_context(patch.object(v5, 'write_progress'))
            v5.checked_wait(Done(), 30, v5.time.monotonic(), 60, phase='acceptance')
            beat.assert_called_with('acceptance', status='running')

    def test_detached_command_has_no_tty_or_parent_dependency(self):
        command = v5.detached_command()
        self.assertEqual(command[:2], ['systemd-run', '--user'])
        for flag in ('--unit=palimpsest-lab-v5', '--collect', f'--working-directory={v5.ROOT}',
                     '--setenv=PYTHONPATH=src:scripts', '--setenv=TMPDIR=/tmp', '--property=StandardInput=null'):
            self.assertIn(flag, command)
        path = next(item for item in command if item.startswith('--setenv=PATH='))
        self.assertIn(str(v5.NODE.parent), path)
        self.assertTrue(path.split('=', 2)[2].endswith(':/usr/bin:/bin'))
        self.assertFalse({'--pty', '-t', '--wait', '-P', '--pipe'} & set(command))
        tail = command[command.index('/usr/bin/flock'):]
        self.assertEqual(tail[:3], ['/usr/bin/flock', '-w', '300'])
        self.assertEqual(tail[-1], '--launch')
        self.assertIn('timeout', tail)
        self.assertEqual(v5.outer_command(), tail[tail.index('timeout'):])


class BrowserFilesystems(unittest.TestCase):
    def free(self, tmp, shm):
        return patch.object(v5, 'free_bytes', side_effect=lambda path: {'/tmp': tmp, '/dev/shm': shm}[path])

    def test_floors_refuse_low_dev_shm_and_tmp(self):
        with self.free(4 * GiB, GiB // 2), self.assertRaisesRegex(RuntimeError, 'dev_shm_free_bytes'):
            v5.shm_floors()
        with self.free(GiB, 4 * GiB), self.assertRaisesRegex(RuntimeError, 'tmp_free_bytes'):
            v5.shm_floors()
        with self.free(4 * GiB, 4 * GiB):
            self.assertEqual(v5.shm_floors(), {'tmp_free_bytes': 4 * GiB, 'dev_shm_free_bytes': 4 * GiB})

    def test_preflight_records_space_and_versions(self):
        with ExitStack() as stack:
            stack.enter_context(self.free(5 * GiB, 7 * GiB))
            stack.enter_context(patch.object(v5, 'version', side_effect=lambda argv: ' '.join(map(str, argv))))
            stack.enter_context(patch.object(v5, 'pin', return_value={'sha256': 'abc', 'bytes': 1}))
            usage = stack.enter_context(patch.object(v5.shutil, 'disk_usage'))
            usage.return_value.free = 12 * GiB
            facts = v5.preflight_facts()
            self.assertEqual((facts['tmp_free_bytes'], facts['dev_shm_free_bytes'], facts['project_free_bytes']),
                             (5 * GiB, 7 * GiB, 12 * GiB))
            self.assertEqual(set(facts['browsers']), {'chromium', 'chromium_binary_sha256', 'playwright', 'node'})
            usage.return_value.free = 9 * GiB
            with self.assertRaisesRegex(RuntimeError, 'initial floor'):
                v5.preflight_facts()

    def test_browser_phase_failure_is_recorded_not_raised(self):
        class Done:
            returncode = 1
            def poll(self):
                return 1
        self.assertEqual(v5.checked_wait(Done(), 30, v5.time.monotonic(), 60, require_success=False), 1)
        with self.assertRaisesRegex(RuntimeError, 'Child exited 1'):
            v5.checked_wait(Done(), 30, v5.time.monotonic(), 60)

    def test_continuing_floor_stops_a_running_phase(self):
        class Child:
            returncode = None
            def poll(self):
                return None
        with ExitStack() as stack:
            stack.enter_context(patch.object(v5, 'observe'))
            stack.enter_context(patch.object(v5, 'BUDGET'))
            stack.enter_context(patch.object(v5, 'check_server_logs'))
            stack.enter_context(self.free(4 * GiB, GiB // 4))
            with self.assertRaisesRegex(RuntimeError, 'dev_shm_free_bytes'):
                v5.checked_wait(Child(), 30, v5.time.monotonic(), 60)


class Commands(unittest.TestCase):
    def test_preflight_phases_and_environment(self):
        self.assertEqual(v5.COMMANDS['preflight'][-2:], ['run', 'test:browser-shm'])
        acceptance, endurance = v5.environment('acceptance'), v5.environment('endurance')
        self.assertEqual((acceptance['PALIMPSEST_MEASURE_UI'], acceptance['PALIMPSEST_REQUIRE_UI_TARGETS']), ('1', '1'))
        self.assertEqual((endurance['PALIMPSEST_ENDURANCE_SECONDS'], endurance['PALIMPSEST_ENDURANCE_CYCLE_SECONDS']), ('3600', '120'))
        probe = v5.COMMANDS['endurance']
        self.assertIn('lab_chromium_resource_probe.py', probe[2])
        self.assertEqual(probe[probe.index('--shm-dir') + 1], '/dev/shm')
        self.assertEqual(v5.COMMANDS['acceptance'][-2:], ['tests/lab.spec.ts', 'tests/recorded-snapshots.spec.ts'])
        self.assertNotEqual(v5.PORTS['acceptance'], v5.PORTS['endurance'])
        self.assertEqual(v5.expected_cycles(3600, 120), 30)
        limits = v5.deadlines(3600)
        self.assertGreater(limits['worker'], 3600 + 900)
        self.assertLess(limits['worker'], limits['supervisor'])
        self.assertLess(limits['supervisor'], limits['publication'])
        self.assertLess(limits['publication'], limits['outer'])

    def test_selection_listing(self):
        report = {'suites': [{'specs': [{'file': 'lab.spec.ts', 'title': 'a'}],
                              'suites': [{'specs': [{'file': 'lab.spec.ts', 'title': 'b'}]}]}]}
        self.assertEqual(v5.selected_tests(report), [('lab.spec.ts', 'a'), ('lab.spec.ts', 'b')])
        with self.assertRaises(AssertionError):
            v5.selected_tests({'suites': [], 'errors': ['bad']})


class Evaluation(unittest.TestCase):
    def phase(self, root, *, cycles=30, failures=(), idle=None, bundle=True, close='closed'):
        acceptance = root / 'acceptance/test-results/workflow'
        acceptance.mkdir(parents=True)
        commits = even(240)
        (acceptance / 'ui-performance.json').write_text(json.dumps({'raw_timestamps_ms': {'dom_sample_commit': commits},
            'started_ms': 0., 'ended_ms': 8000., 'commands': [{'ack_ms': 20.}] * 12}))
        (acceptance / 'owner-close.json').write_text(json.dumps({'http_status': 200, 'response': {'status': close}}))
        (root / 'acceptance/exports').mkdir()
        (root / 'acceptance/exports/a.svg').write_text('<svg/>')
        if bundle:
            (root / 'acceptance/exports/b.zip').write_bytes(b'PK')
        (root / 'acceptance/playwright-results.json').write_text(json.dumps({'stats': {'expected': 8, 'unexpected': 0, 'skipped': 0, 'flaky': 0}}))
        (root / 'endurance/test-results/endurance').mkdir(parents=True)
        (root / 'endurance/playwright-results.json').write_text(json.dumps({'stats': {'expected': 1, 'unexpected': 0, 'skipped': 0, 'flaky': 0}}))
        idle = idle or [256] * cycles
        (root / 'endurance/test-results/endurance/lab-endurance.json').write_text(json.dumps({
            'configuration': {'seconds': 3600, 'cycle_seconds': 120, 'stream_seconds': 4, 'cycles': 30},
            'cycles': [cycle(index, idle[index], idle[index] + 1000) for index in range(cycles)],
            'network_failures': list(failures), 'page_errors': []}))
        return root

    def judge(self, **options):
        with tempfile.TemporaryDirectory() as directory:
            v5.configure(endurance_seconds=3600, cycle_seconds=120)
            return v5.evaluate(self.phase(Path(directory), **options))

    def test_complete_evidence_passes(self):
        result = self.judge()
        self.assertTrue(result['passed'], json.dumps(result, default=str)[:2000])
        self.assertEqual(result['checks']['endurance_cycles']['reloads'], 6)

    def test_owner_writer_statistics_are_recorded_without_a_new_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            v5.configure(endurance_seconds=3600, cycle_seconds=120)
            root = self.phase(Path(directory))
            stats = {'mode': 'background', 'written_items': 40, 'max_queued_items': 3, 'backpressure_events': 1,
                     'backpressure_seconds': .25, 'queued_items': 0, 'pending_bytes': 0, 'max_items': 16, 'error': None}
            for name, phase, writer in (('a' * 32, 'acceptance', stats), ('b' * 32, 'endurance', {**stats, 'written_items': 2}),
                                        ('c' * 32, 'endurance', None)):
                (root / phase / 'runs' / name).mkdir(parents=True)
                (root / phase / 'runs' / name / 'supervisor.json').write_text(json.dumps({'status': 'closed', 'recording_writer': writer}))
            result = v5.evaluate(root)
            self.assertTrue(result['passed'])
            writers = result['recorded']['recording_writers']
            self.assertEqual((writers['owners'], writers['background'], writers['synchronous']), (3, 2, 1))
            self.assertEqual((writers['written_items'], writers['max_queued_items'], writers['backpressure_events']), (42, 3, 2))
            self.assertAlmostEqual(writers['backpressure_seconds'], .5)
            self.assertEqual(writers['errors'], [])
            self.assertEqual(len(writers['per_owner']), 3)

    def test_each_missing_or_failed_part_fails(self):
        cases = {'cycles': {'cycles': 29},
                 'network': {'failures': [{'error': 'net::ERR_INSUFFICIENT_RESOURCES'}]},
                 'listeners': {'idle': [250 + 20 * index for index in range(30)]},
                 'bundle': {'bundle': False}, 'close': {'close': 'failed'}}
        for name, options in cases.items():
            with self.subTest(name):
                self.assertFalse(self.judge(**options)['passed'])


class Publication(unittest.TestCase):
    def run_publish(self, fault=None):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            phase, publication = root / 'phase', root / 'publication'
            (phase / 'endurance/runs/x').mkdir(parents=True)
            (phase / 'endurance/runs/x/recording.npz').write_bytes(b'big')
            (phase / 'worker.json').write_text('{}')
            registration = root / 'registration.json'
            registration.write_text('{}')
            budget = StorageBudget((phase, publication), StorageLimits(max_bytes=16 * 1024**2, min_free_bytes=0))
            for name, value in {'ROOT': root, 'PHASE': phase, 'PUBLICATION': publication,
                                'REGISTRATION': registration, 'BUDGET': budget}.items():
                stack.enter_context(patch.object(v5, name, value))
            stack.enter_context(patch('palimpsest.storage.Path.home', return_value=root))
            if fault == 'refusal':
                (publication / 'publication.json').mkdir(parents=True)
            clock = [0.]
            stack.enter_context(patch.object(v5.time, 'monotonic', side_effect=lambda: clock[0]))
            if fault == 'deadline':
                clock[0] = 10_000.
            code = v5.publish({'status': 'passed'}, 0., 5000.)
            result = json.loads((phase / 'result.json').read_text())
            if fault is None:
                self.assertFalse((publication / 'phase/endurance/runs/x/recording.npz').exists())
                self.assertTrue((publication / 'phase/worker.json').exists())
            return code, result['status']

    def test_publication_success_and_failures(self):
        self.assertEqual(self.run_publish(), (0, 'passed'))
        for fault in ('refusal', 'deadline'):
            with self.subTest(fault):
                self.assertEqual(self.run_publish(fault), (1, 'failed'))


if __name__ == '__main__':
    unittest.main()
