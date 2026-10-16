"""Guard-only authored workloads; no installed imports or runtime qualification."""
import json
import textwrap

import pytest

from test_puck_worker_dependencies import dependency_fixture


@pytest.mark.parametrize('size', [128, 512, 2048])
def test_authored_cache_workload_records_real_guard_cost(tmp_path, size):
    body = textwrap.dedent('''\
        import sys, time, types
        deps = admission._dependencies
        names = ['fixture_guard_cost_'+str(index) for index in range(SIZE)]
        assert not any(name in sys.modules or name in deps.loading for name in names)
        previous_profile = sys.getprofile()
        calls = 0
        def profile(frame, event, value):
            nonlocal calls
            if (event == 'c_call' and value.__name__ == 'keys'
                    and value.__self__ is deps.loaded):
                calls += 1
        try:
            for name in names:
                deps.loading.add(name)
                sys.modules[name] = types.ModuleType(name)
            samples = []
            for sample in range(3):
                start = time.perf_counter_ns()
                for repeat in range(3):
                    admission._check(full=False)
                samples.append(time.perf_counter_ns()-start)
            sys.setprofile(profile)
            admission._check(full=False)
        finally:
            sys.setprofile(previous_profile)
            for name in names:
                sys.modules.pop(name, None)
                deps.loading.discard(name)
        return {'synthetic_cache_entries':SIZE, 'checks_per_sample':3,
            'elapsed_ns':samples, 'dependency_keys_calls_per_profiled_check':calls,
            'cache_clean':not any(name in sys.modules for name in names),
            'allowances_clean':not any(name in deps.loading for name in names)}
        ''').replace('SIZE', str(size))
    result, _ = dependency_fixture(tmp_path, body)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    entry = receipt['entry_result']
    assert entry['synthetic_cache_entries'] == size
    assert entry['cache_clean'] is entry['allowances_clean'] is True
    assert len(entry['elapsed_ns']) == 3
    assert all(type(value) is int and value > 0 for value in entry['elapsed_ns'])
    assert receipt['runtime_qualified'] is receipt['collection_authorized'] is False
    print(json.dumps({'kind':'authored-guard-cost-v1', **entry}, sort_keys=True))


@pytest.mark.parametrize('allowance', ['source', 'dependency', 'lying-false'])
def test_inflight_cache_allowances_remain_accepted(tmp_path, allowance):
    body = textwrap.dedent('''\
        import sys, types
        name = 'fixture_inflight_cache'
        old = admission._dependencies.loading
        class FalseMembership(set):
            def __contains__(self, key): return False
        loading = admission._loading if ALLOWANCE == 'source' else old
        if ALLOWANCE == 'lying-false':
            loading = admission._dependencies.loading = FalseMembership(old)
        try:
            loading.add(name)
            sys.modules[name] = types.ModuleType(name)
            admission._check(full=False)
        finally:
            sys.modules.pop(name, None)
            loading.discard(name)
            admission._dependencies.loading = old
        return {'accepted':True}
        ''').replace('ALLOWANCE', repr(allowance))
    result, _ = dependency_fixture(tmp_path, body)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['entry_result'] == {'accepted':True}


@pytest.mark.parametrize('defect', ['unknown', 'lying-true', 'callback-removal'])
def test_cache_denial_poisons_and_closes_even_after_cleanup(tmp_path, defect):
    body = textwrap.dedent('''\
        import sys, types
        deps = admission._dependencies
        original = deps.loading
        class TrueMembership(set):
            def __contains__(self, key): return True
        class RemovingName(str):
            def split(self, *args):
                deps.loading.discard(str(self))
                return super().split(*args)
        name = RemovingName('fixture_guard_denial') if DEFECT == 'callback-removal' else 'fixture_guard_denial'
        if DEFECT == 'lying-true': deps.loading = TrueMembership(original)
        if DEFECT == 'callback-removal': deps.loading.add(str(name))
        sys.modules[name] = types.ModuleType(str(name))
        try:
            admission._check(full=False)
        except RuntimeError as first:
            assert str(first) == 'Unregistered module cache entry: fixture_guard_denial'
            assert admission._first_failure is first
            assert admission._children == []
        else:
            raise AssertionError('UNREGISTERED_CACHE_ACCEPTED')
        finally:
            sys.modules.pop(name, None)
            deps.loading.discard(str(name))
            deps.loading = original
        try:
            admission._check(full=False)
        except RuntimeError as poisoned:
            assert str(poisoned) == 'Bootstrap inactive or poisoned'
            assert admission._first_failure is poisoned.__cause__
        else:
            raise AssertionError('FAILED_GUARD_REARMED')
        sys.stderr.write('CACHE_REFUSAL_AND_POISON_CONFIRMED\\n')
        return {}
        ''').replace('DEFECT', repr(defect))
    result, _ = dependency_fixture(tmp_path, body)
    assert result.returncode != 0 and result.stdout == ''
    assert 'CACHE_REFUSAL_AND_POISON_CONFIRMED' in result.stderr, result.stderr
    assert 'Unregistered module cache entry: fixture_guard_denial' in result.stderr
