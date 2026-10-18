"""Publication controls only: temporary files and mocked completed-worker records."""
from contextlib import ExitStack
import ast
import importlib.util
import json
import signal
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from palimpsest.storage import StorageBudget, StorageLimits

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/manual_lab_refresh_v2.py'
spec = importlib.util.spec_from_file_location('manual_lab_refresh_v2', SCRIPT)
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class PublicationControls(unittest.TestCase):
    def run_fixture(self, fault=None):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory, ExitStack() as patches:
            root = Path(directory)
            (root / 'home').mkdir()
            phase, publication = root / 'phase', root / 'publication'
            registration = root / 'registration.json'
            registration.write_text(json.dumps({'schema': 'manual-lab-refresh-v2', 'code_base': producer.BASE,
                'sources': {}, 'commands': {'selection': producer.SELECTION, 'build': producer.BUILD,
                    'server': producer.SERVER, 'browser': producer.BROWSER},
                'cached_dependencies': {}, 'runtime_versions': {}}))
            budget = StorageBudget((phase, publication), StorageLimits(max_bytes=16 * 1024**2, min_free_bytes=0))
            clock, before_receipt = [0.], []
            original_write = producer.write_json

            def complete(*args, **kwargs):
                (phase / 'worker.json').write_text(json.dumps({'status': 'passed', 'process': {}, 'owned_survivors_requiring_kill': []}))
                (phase / 'processes.json').write_text('[]')
                return {'status': 'completed', 'returncode': 0}

            def write(path, value, target_budget):
                if path == publication / 'publication.json':
                    before_receipt.append(json.loads((phase / 'result.json').read_text())['status'])
                    if fault == 'refusal':
                        path.mkdir(exist_ok=True)  # A real filesystem refusal, not a mocked writer error.
                    if fault == 'term':
                        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                original_write(path, value, target_budget)
                if path == publication / 'publication.json' and fault == 'deadline':
                    clock[0] = 346.
                if path == phase / 'result.json' and value['status'] == 'passed' and fault == 'canonical-deadline':
                    clock[0] = 346.

            for name, value in {'ROOT': root, 'PHASE': phase, 'PUBLICATION': publication,
                                'REGISTRATION': registration, 'BUDGET': budget}.items():
                patches.enter_context(patch.object(producer, name, value))
            patches.enter_context(patch('palimpsest.storage.Path.home', return_value=root / 'home'))
            patches.enter_context(patch.object(producer.subprocess, 'check_output', side_effect=lambda argv, **kw: 'v24.21.0\n' if argv[-1] == '--version' else ''))
            patches.enter_context(patch.object(producer.subprocess, 'run'))
            patches.enter_context(patch.object(producer.socket, 'socket'))
            patches.enter_context(patch('shutil.disk_usage', return_value=SimpleNamespace(free=8 * 1024**3)))
            patches.enter_context(patch.object(producer, 'pins', return_value={}))
            patches.enter_context(patch.object(producer, 'cached_dependencies', return_value={}))
            patches.enter_context(patch.object(producer, 'bounded_process', side_effect=complete))
            patches.enter_context(patch.object(producer, 'cleanup_check', return_value={'passed': True}))
            patches.enter_context(patch.object(producer.time, 'monotonic', side_effect=lambda: clock[0]))
            patches.enter_context(patch.object(producer, 'write_json', side_effect=write))
            try:
                code = producer.launch()
            except BaseException as error:
                self.fail(f'Publication escaped without a failed receipt: {type(error).__name__}: {error}')
            result = json.loads((phase / 'result.json').read_text())
            self.assertEqual(before_receipt[0], 'pending-publication')
            self.assertTrue((phase / 'launched.json').is_file())
            return code, result

    def test_worker_interrupt_clears_provisional_pass(self):
        # Execute the actual handler against the post-update state; no timing race.
        worker = next(node for node in ast.parse(SCRIPT.read_text()).body
                      if isinstance(node, ast.FunctionDef) and node.name == 'worker')
        handler = next(node for node in worker.body if isinstance(node, ast.Try)).handlers[0]
        result = {'status': 'passed'}
        body = ast.Module(body=handler.body, type_ignores=[])
        exec(compile(body, str(SCRIPT), 'exec'), {'result': result, 'error': KeyboardInterrupt()})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure']['type'], 'KeyboardInterrupt')

    def test_reserved_publication_root_and_completed_records(self):
        code, result = self.run_fixture()
        self.assertEqual((code, result['status']), (0, 'passed'))

    def test_write_refusal_interrupt_and_late_final_write_fail_closed(self):
        for fault in ('refusal', 'term', 'deadline', 'canonical-deadline'):
            with self.subTest(fault=fault):
                code, result = self.run_fixture(fault)
                self.assertEqual((code, result['status']), (1, 'failed'))


if __name__ == '__main__':
    unittest.main()
