"""Prospective q4 semantics in the real held worker, with tiny authored CPU modules.

No production guard is substituted. The qualified entry imports an authored
NumPy initializer containing each body; preflight must remain unreachable.
Every case requires its body-completion marker, so descriptor-only refusal is
the initial RED and can never accidentally satisfy a negative behavior case.
"""
import json
import textwrap

import pytest

from test_puck_cpu_runtime_entry import CPU_VERSIONS, ORDER, cpu_policy, cpu_setup
from test_puck_tmpfs_dependencies import authored
from test_puck_worker_bootstrap import descriptor
from test_puck_worker_dependencies import dependency_fixture


_PRELUDE = '''\
import os, sys, types
owner = sys.meta_path[0].owner
deps = owner._dependencies
assert owner._reg['qualification']['version'] == 4
sys.stderr.write('Q4_BODY_ENTERED\\n')

def expect_refusal(action=None, restore=None, reason=None):
    first = None
    try:
        try:
            (owner._import_recheck if action is None else action)()
        except (RuntimeError, ValueError, TimeoutError) as error:
            first = error
            assert owner._first_failure is error, 'Q4_FIRST_EXCEPTION_REPLACED'
            assert owner._state == 'failed', 'Q4_REFUSAL_DID_NOT_POISON'
            assert owner._children == [] and owner._early_runtime_fds == [], 'Q4_OWNED_LISTS_NOT_EMPTIED'
            if reason is not None:
                assert str(error) == reason, (str(error), reason)
        else:
            raise AssertionError('Q4_EXPECTED_REFUSAL_SKIPPED')
    finally:
        if restore is not None:
            restore()
    try:
        owner._import_recheck()
    except RuntimeError as poisoned:
        assert str(poisoned) == 'Bootstrap inactive or poisoned'
        assert poisoned.__cause__ is first and owner._first_failure is first, 'Q4_FIRST_FAILURE_CHAIN_CHANGED'
    else:
        raise AssertionError('Q4_POISON_REARMED')
'''


def run_q4(body):
    def packages(deps, root):
        cpu_setup(deps, root)
        path = root/'numpy/__init__.py'
        path.write_text(path.read_text()+_PRELUDE+textwrap.dedent(body)
            +"\nsys.stderr.write('Q4_CASE_COMPLETED\\n')\n")
        deps['roots'][0]['files'] = sorted(
            [descriptor(root/row['path'], row['path']) for row in deps['roots'][0]['files']],
            key=lambda row:row['path'])

    def policy(reg, source):
        cpu_policy(reg, source)
        reg['qualification'].update(kind='puck-held-runtime-import-qualification-v4', version=4)

    with authored() as base:
        result, _ = dependency_fixture(base, 'raise AssertionError("Q4_PREFLIGHT_RAN")',
            mutate=packages, source_change=policy)
    print(json.dumps({'kind':'authored-q4-guard-contract-case-v1',
        'worker_returncode':result.returncode, 'stdout':result.stdout, 'stderr':result.stderr},
        sort_keys=True))
    return result


def succeeded(result):
    assert result.returncode == 0, result.stderr
    assert 'Q4_BODY_ENTERED\n' in result.stderr and 'Q4_CASE_COMPLETED\n' in result.stderr
    receipt = json.loads(result.stdout)
    entry = receipt['entry_result']
    assert entry['kind'] == 'puck-held-runtime-import-qualification-result-v2'
    assert entry['version'] == 2 and entry['qualification_version'] == 4
    assert [row['name'] for row in entry['imports']] == ORDER
    assert {row['name']:row['version'] for row in entry['imports']} == CPU_VERSIONS
    for value in (receipt, entry):
        assert value['runtime_qualified'] is value['native_authorized'] is False
        assert value['collection_authorized'] is value['executable'] is False
        assert value['qualification_claims'] == []


def refused(result):
    assert result.returncode != 0 and result.stdout == ''
    assert 'Q4_BODY_ENTERED\n' in result.stderr, result.stderr
    assert 'Q4_CASE_COMPLETED\n' in result.stderr, result.stderr
    assert 'Q4_PREFLIGHT_RAN' not in result.stderr


def test_q4_accepts_registered_numpy_while_its_initializer_is_inflight():
    succeeded(run_q4('''
        assert 'numpy' in deps.loading and 'numpy' not in deps.loaded
        assert sys.modules['numpy'].__dict__ is globals()
        owner._import_recheck()
        assert owner._state == 'active' and owner._first_failure is None
    '''))


def test_q4_unknown_cache_name_retains_exact_refusal_close_and_poison():
    refused(run_q4('''
        name = 'fixture_q4_unknown'
        assert name not in sys.modules
        sys.modules[name] = types.ModuleType(name)
        def restore():
            sys.modules.pop(name, None)
        expect_refusal(restore=restore, reason='Unregistered module cache entry: '+name)
    '''))


@pytest.mark.parametrize('receiver', ['cache', 'source-loaded', 'source-loading',
    'dependency-loaded', 'dependency-loading', 'stdlib'])
def test_q4_rejects_container_subclasses_before_their_hooks(receiver):
    refused(run_q4('''
        events = []
        def hook(*args, **kwargs):
            events.append('hook')
            raise AssertionError('Q4_CONTAINER_HOOK_RAN')
        class BadDict(dict):
            __iter__ = hook
            __len__ = hook
            __contains__ = hook
            items = hook
            keys = hook
            get = hook
        class BadSet(set):
            __iter__ = hook
            __len__ = hook
            __contains__ = hook
            __or__ = hook
            __ror__ = hook
        class BadFrozen(frozenset):
            __iter__ = hook
            __len__ = hook
            __contains__ = hook
        receiver = RECEIVER
        if receiver == 'cache':
            previous = sys.modules
            sys.modules = BadDict(previous)
            def restore():
                sys.modules = previous
        elif receiver == 'stdlib':
            previous = sys.stdlib_module_names
            sys.stdlib_module_names = BadFrozen(previous)
            def restore():
                sys.stdlib_module_names = previous
        else:
            target, attribute = ((owner, '_loaded') if receiver == 'source-loaded' else
                (owner, '_loading') if receiver == 'source-loading' else
                (deps, 'loaded') if receiver == 'dependency-loaded' else (deps, 'loading'))
            previous = getattr(target, attribute)
            setattr(target, attribute, BadDict(previous) if attribute in ('loaded', '_loaded') else BadSet(previous))
            def restore():
                setattr(target, attribute, previous)
        expect_refusal(restore=restore)
        assert events == [], 'Q4_CONTAINER_HOOK_RAN'
    '''.replace('RECEIVER', repr(receiver))))


@pytest.mark.parametrize('receiver', ['cache', 'source-loaded', 'dependency-loading'])
def test_q4_rejects_str_subclass_names_before_hash_lookup_or_split(receiver):
    refused(run_q4('''
        armed = False
        events = []
        class Key(str):
            def __hash__(self):
                if armed:
                    events.append('hash')
                    raise AssertionError('Q4_NAME_HOOK_RAN')
                return str.__hash__(self)
            def __eq__(self, other):
                if armed:
                    events.append('equality')
                    raise AssertionError('Q4_NAME_HOOK_RAN')
                return str.__eq__(self, other)
            def split(self, *args, **kwargs):
                events.append('split')
                raise AssertionError('Q4_NAME_HOOK_RAN')
        receiver = RECEIVER
        if receiver == 'source-loaded':
            previous = owner._loaded
            replacement = dict(previous)
            original = next(iter(replacement))
            binding = replacement.pop(original)
            replacement[Key(original)] = binding
            owner._loaded = replacement
        else:
            key = Key('json.fixture_q4_subclass')
            if receiver == 'cache':
                sys.modules[key] = types.ModuleType(str(key))
            else:
                deps.loading.add(key)
        armed = True
        def restore():
            global armed
            armed = False
            if receiver == 'source-loaded':
                owner._loaded = previous
            elif receiver == 'cache':
                sys.modules.pop(key, None)
            else:
                deps.loading.discard(key)
        expect_refusal(restore=restore)
        assert events == [], 'Q4_NAME_HOOK_RAN'
    '''.replace('RECEIVER', repr(receiver))))


@pytest.mark.parametrize('mutation', ['cache-object', 'cache-key', 'allowance-content',
    'allowance-receiver', 'second-export'])
def test_q4_late_observed_change_cannot_escape_fail_closed_snapshot(mutation):
    refused(run_q4('''
        mutation = MUTATION
        original_write = os.write
        original_loading = owner._loading
        loading_contents = set(original_loading)
        original_active = dict(deps.bindings.active)
        original_json = sys.modules['json']
        before = 'json.fixture_q4_before'
        after = 'json.fixture_q4_after'
        module = types.ModuleType(before)
        fired = False
        if mutation == 'cache-key':
            sys.modules[before] = module
        if mutation == 'allowance-content':
            original_loading.add(before)
        def write(fd, payload):
            global fired
            result = original_write(fd, payload)
            if b'"kind":"puck-worker-guard-cost-v1"' not in payload:
                return result
            if not fired and ((mutation == 'second-export' and b'"section":"custody"' in payload)
                    or (mutation != 'second-export' and b'"active":null' in payload)):
                fired = True
                if mutation == 'cache-object':
                    sys.modules['json'] = types.ModuleType('json')
                elif mutation == 'cache-key':
                    sys.modules.pop(before)
                    sys.modules[after] = module
                elif mutation == 'allowance-content':
                    original_loading.remove(before)
                    original_loading.add(after)
                elif mutation == 'allowance-receiver':
                    owner._loading = set(original_loading)
                else:
                    deps.bindings.active['fixture_q4_late_export'] = sys.modules['sys']
            owner._guard_next = 0
            return result
        def restore():
            os.write = original_write
            sys.modules['json'] = original_json
            sys.modules.pop(before, None)
            sys.modules.pop(after, None)
            owner._loading = original_loading
            original_loading.clear()
            original_loading.update(loading_contents)
            deps.bindings.active.clear()
            deps.bindings.active.update(original_active)
        owner._guard_next = 0
        os.write = write
        expect_refusal(restore=restore)
        assert fired, 'Q4_LATE_MUTATION_NOT_REACHED'
    '''.replace('MUTATION', repr(mutation))))


def test_q4_completion_counter_callback_cannot_change_cache_after_late_check():
    refused(run_q4('''
        original_json = sys.modules['json']
        original_completed = owner._guard_checks[False][1]
        fired = False
        class Completed(int):
            def __add__(self, value):
                global fired
                fired = True
                sys.modules['json'] = types.ModuleType('json')
                return int(self)+value
        owner._guard_checks[False][1] = Completed(original_completed)
        def restore():
            sys.modules['json'] = original_json
            owner._guard_checks[False][1] = original_completed
        expect_refusal(restore=restore)
        assert fired, 'Q4_COMPLETION_CALLBACK_NOT_REACHED'
    '''))


def test_q4_stdlib_name_baseline_cannot_be_replaced_or_widened():
    refused(run_q4('''
        previous = sys.stdlib_module_names
        sys.stdlib_module_names = frozenset(previous) | {'fixture_q4_widened'}
        def restore():
            sys.stdlib_module_names = previous
        expect_refusal(restore=restore)
    '''))


def test_q4_nested_guard_and_real_dependency_publication_keep_outer_snapshot():
    succeeded(run_q4('''
        import fixture_dep
        assert deps.loaded['fixture_dep'][0] is fixture_dep
        assert fixture_dep.answer == 43
        original_write = os.write
        fired = False
        nested_before = owner._guard_nested
        def write(fd, payload):
            global fired
            if not fired and b'"kind":"puck-worker-guard-cost-v1"' in payload:
                fired = True
                owner._import_recheck()
            return original_write(fd, payload)
        owner._guard_next = 0
        os.write = write
        try:
            owner._import_recheck()
        finally:
            os.write = original_write
        assert fired and owner._guard_nested == nested_before+1
        assert owner._guard_depth == 0 and owner._guard_current is None
        assert owner._state == 'active' and owner._first_failure is None
        assert deps.loaded['fixture_dep'][0] is sys.modules['fixture_dep']
    '''))


def test_q4_preserves_main_alias_identity_refusal_and_poison():
    refused(run_q4('''
        previous = sys.modules['__mp_main__']
        sys.modules['__mp_main__'] = types.ModuleType('foreign')
        def restore():
            sys.modules['__mp_main__'] = previous
        expect_refusal(restore=restore, reason='Runtime qualification stdlib alias identity changed')
    '''))


def test_q4_keeps_final_real_deadline_after_late_diagnostic_write():
    refused(run_q4('''
        original_write = os.write
        fired = False
        def write(fd, payload):
            global fired
            result = original_write(fd, payload)
            if b'"kind":"puck-worker-guard-cost-v1"' in payload:
                if b'"active":null' in payload:
                    fired = True
                    owner._deadline = 0
                else:
                    owner._guard_next = 0
            return result
        def restore():
            os.write = original_write
        owner._guard_next = 0
        os.write = write
        expect_refusal(restore=restore, reason='Fresh worker deadline exhausted')
        assert fired, 'Q4_FINAL_DEADLINE_WRITE_NOT_REACHED'
    '''))


@pytest.mark.parametrize('count', [65536, 65537])
def test_q4_cache_name_ceiling_has_exact_boundary_and_one_over(count):
    body = '''
        target = TARGET
        original_count = len(sys.modules)
        assert original_count < target
        names = ['json.fixture_q4_cache_'+str(i) for i in range(target-original_count)]
        module = types.ModuleType('json.fixture_q4_cache')
        for name in names:
            sys.modules[name] = module
        assert len(sys.modules) == target
        def restore():
            for name in names:
                sys.modules.pop(name, None)
        if target == 65536:
            try:
                owner._import_recheck()
            finally:
                restore()
        else:
            expect_refusal(restore=restore)
        assert len(sys.modules) == original_count
    '''.replace('TARGET', str(count))
    result = run_q4(body)
    (succeeded if count == 65536 else refused)(result)


@pytest.mark.parametrize('count', [65536, 65537])
def test_q4_combined_allowance_ceiling_counts_duplicate_input_entries(count):
    body = '''
        target = TARGET
        source_before = set(owner._loading)
        dependency_before = set(deps.loading)
        exported = deps.bindings.recheck()
        aliases = {'__mp_main__'} if '__mp_main__' in sys.modules else set()
        def allowance_count():
            return (2+len(aliases)+len(owner._loaded)+len(owner._loading)
                +len(deps.loaded)+len(deps.loading)+len(exported))
        initial_count = allowance_count()
        extra = target-initial_count
        assert extra > 0
        names = ['json.fixture_q4_allowance_'+str(i) for i in range((extra+1)//2)]
        for name in names[:extra//2]:
            owner._loading.add(name)
            deps.loading.add(name)
        if extra % 2:
            owner._loading.add(names[-1])
        assert allowance_count() == target
        assert len(owner._loading | deps.loading) < target
        def restore():
            owner._loading.clear()
            owner._loading.update(source_before)
            deps.loading.clear()
            deps.loading.update(dependency_before)
        if target == 65536:
            try:
                owner._import_recheck()
            finally:
                restore()
        else:
            expect_refusal(restore=restore)
        assert owner._loading == source_before and deps.loading == dependency_before
    '''.replace('TARGET', str(count))
    result = run_q4(body)
    (succeeded if count == 65536 else refused)(result)
