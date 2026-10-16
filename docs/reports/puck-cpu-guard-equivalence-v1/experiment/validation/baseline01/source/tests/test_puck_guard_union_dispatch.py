"""Authored real-worker counterexample for changing per-key union dispatch."""
import json
import textwrap

from test_puck_worker_dependencies import dependency_fixture


def test_source_allowance_reflected_union_failure_is_not_skipped(tmp_path):
    body = textwrap.dedent('''\
        import sys
        previous = admission._loading
        events = []
        class ReflectedFailure(RuntimeError):
            pass
        class ReflectedAllowance(set):
            def __ror__(self, other):
                events.append('source.__ror__')
                raise ReflectedFailure('SOURCE_UNION_REFLECTED_FAILURE')
        admission._loading = ReflectedAllowance(previous)
        try:
            admission._check(full=False)
        except ReflectedFailure as first:
            assert events == ['source.__ror__'], events
            assert admission._first_failure is first
            assert admission._children == []
        else:
            raise AssertionError('SOURCE_UNION_REFLECTED_FAILURE_SKIPPED')
        finally:
            admission._loading = previous
        try:
            admission._check(full=False)
        except RuntimeError as poisoned:
            assert str(poisoned) == 'Bootstrap inactive or poisoned'
            assert admission._first_failure is poisoned.__cause__
        else:
            raise AssertionError('FAILED_GUARD_REARMED')
        sys.stderr.write('SOURCE_UNION_DISPATCH_POISON_AND_CLOSE_CONFIRMED\\n')
        return {}
        ''')
    result, _ = dependency_fixture(tmp_path, body)
    print(json.dumps({'kind':'authored-guard-union-dispatch-v1',
        'worker_returncode':result.returncode,'stdout':result.stdout,
        'stderr':result.stderr}, sort_keys=True))
    assert result.returncode != 0 and result.stdout == ''
    assert 'SOURCE_UNION_DISPATCH_POISON_AND_CLOSE_CONFIRMED' in result.stderr, result.stderr
    assert 'SOURCE_UNION_REFLECTED_FAILURE' in result.stderr, result.stderr
    assert 'SOURCE_UNION_REFLECTED_FAILURE_SKIPPED' not in result.stderr
