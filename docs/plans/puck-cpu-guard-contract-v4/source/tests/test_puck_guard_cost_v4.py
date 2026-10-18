"""Q4 authored timings following semantic/source review; no runtime qualification.

This changes the guard contract and initializer context relative to PR169's
historical original. It does not establish equivalent semantics or installed
throughput. No installed package or native extension is used by these cases.
"""
import json
import textwrap

import pytest

from test_puck_guard_contract_v4 import run_q4, succeeded


@pytest.mark.parametrize('size', [128, 512, 2048])
def test_q4_authored_cache_workload_records_bounded_light_guard_samples(size):
    body = textwrap.dedent('''\
        import json, time
        names = ['fixture_guard_cost_'+str(index) for index in range(SIZE)]
        assert not any(name in sys.modules or name in deps.loading for name in names)
        previous_profile = sys.getprofile()
        profile_calls = 0
        def profile(frame, event, value):
            global profile_calls
            if (event == 'c_call' and value.__name__ == 'keys'
                    and value.__self__ is deps.loaded):
                profile_calls += 1
        try:
            for name in names:
                deps.loading.add(name)
                sys.modules[name] = types.ModuleType(name)
            samples = []
            for sample in range(3):
                started = time.perf_counter_ns()
                for repeat in range(3):
                    owner._check(full=False)
                samples.append(time.perf_counter_ns()-started)
            sys.setprofile(profile)
            owner._check(full=False)
        finally:
            sys.setprofile(previous_profile)
            for name in names:
                sys.modules.pop(name, None)
                deps.loading.discard(name)
        row = {'kind':'authored-q4-guard-cost-v1', 'qualification_version':4,
            'synthetic_cache_entries':SIZE, 'checks_per_sample':3,
            'elapsed_ns':samples,
            'dependency_keys_calls_per_profiled_check':profile_calls,
            'cache_clean':not any(name in sys.modules for name in names),
            'allowances_clean':not any(name in deps.loading for name in names),
            'profile_restored':sys.getprofile() is previous_profile}
        sys.stderr.write(json.dumps(row, sort_keys=True)+'\\n')
        ''').replace('SIZE', str(size))
    result = run_q4(body)
    succeeded(result)
    rows = []
    for line in result.stderr.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if type(value) is dict and value.get('kind') == 'authored-q4-guard-cost-v1':
            rows.append(value)
    assert len(rows) == 1, result.stderr
    row = rows[0]
    assert row['qualification_version'] == 4
    assert row['synthetic_cache_entries'] == size and row['checks_per_sample'] == 3
    assert len(row['elapsed_ns']) == 3
    assert all(type(value) is int and value > 0 for value in row['elapsed_ns'])
    assert type(row['dependency_keys_calls_per_profiled_check']) is int
    assert row['dependency_keys_calls_per_profiled_check'] >= 0
    assert row['cache_clean'] is row['allowances_clean'] is row['profile_restored'] is True
    print(json.dumps(row, sort_keys=True))
