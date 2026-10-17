"""Policy v5 stock absence in the real held worker; tiny authored packages only.

No installed runtime, protected input or allocation runs. Declared absent and
declared unavailable names must look like stock CPython misses to bare
find_spec and import, without poison. Undeclared requests keep poisoning;
v1-v4 keep their exact semantics. Present hidden files sit in the held root,
which is not on sys.path, and held packages have __path__ == [], so their
HIDDEN_TARGET_RAN marker only shows the guard itself never loads them. The
discriminating never-executes proof is the frozen __hello__ later-finder case.
Success cases require a body-completion marker, so the initial RED (v5 refused
as an unknown descriptor) can never satisfy them.
"""
import json
import textwrap

import pytest

from test_puck_cpu_runtime_entry import CPU_VERSIONS, ORDER, cpu_policy, cpu_setup
from test_puck_tmpfs_dependencies import authored
from test_puck_worker_bootstrap import descriptor
from test_puck_worker_dependencies import dependency_fixture


BASE_MISSING = ['numpy._distributor_init_local', 'org', 'torch._rocm_init']
HIDDEN = ['networkx', 'pandas', 'sklearn', 'torch._cxx_pytree']
PRESENT = {'networkx': 'networkx.py', 'pandas': 'pandas/__init__.py',
           'torch._cxx_pytree': 'torch/_cxx_pytree.py', 'tabulate': 'tabulate.py',
           'foreign_present': 'foreign_present.py'}
_PRELUDE = '''\
import importlib, importlib.util, types
owner = sys.meta_path[0].owner
sys.stderr.write('V5_BODY_ENTERED\\n')
'''


def run(code='', *, version=5, negatives=(), hidden=HIDDEN, present=(), registered=(),
        defect=None, dependency_version=3, change=None, exports=(), native_cache=(), registration_change=None):
    def packages(deps, root):
        cpu_setup(deps, root, defect, dependency_version)
        for name in present:
            relative = PRESENT[name]; path = root/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            # Unreachable to stock finders; see the __hello__ case for a resolvable target.
            path.write_text('raise AssertionError("HIDDEN_TARGET_RAN")\n')
            deps['roots'][0]['files'].append(descriptor(path, relative))
            if name in registered:
                deps['modules'].append(dict(name=name, root_index=0, path=relative, kind='python',
                                            is_package=relative.endswith('/__init__.py')))
        if exports: deps['import_profile']['exports'].extend(exports)
        if native_cache:
            deps['import_profile'].update(kind='puck-producer-import-profile-v2', version=2,
                                          native_cache=list(native_cache))
        if code:
            path = root/'torch/__init__.py'
            path.write_text(path.read_text()+_PRELUDE+textwrap.dedent(code)
                +"\nsys.stderr.write('V5_CASE_COMPLETED\\n')\n")
        deps['roots'][0]['files'] = sorted(
            [descriptor(root/row['path'], row['path']) for row in deps['roots'][0]['files']],
            key=lambda row: row['path'])

    def policy(reg, source):
        cpu_policy(reg, source); q = reg['qualification']
        q.update(kind='puck-held-runtime-import-qualification-v'+str(version), version=version,
                 negative_imports=sorted(BASE_MISSING+list(negatives)))
        if version == 5: q['hidden_imports'] = sorted(hidden)
        if change: change(q)
        if registration_change: registration_change(reg)

    with authored() as base:
        result, _ = dependency_fixture(base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
            mutate=packages, source_change=policy, native=bool(native_cache))
    print(json.dumps({'kind': 'authored-v5-stock-absence-case-v1', 'worker_returncode': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr}, sort_keys=True))
    return result


def succeeded(result, version=5):
    assert result.returncode == 0, result.stderr
    assert 'V5_BODY_ENTERED\n' in result.stderr and 'V5_CASE_COMPLETED\n' in result.stderr
    # HIDDEN_TARGET_RAN alone is not discriminating (held root unreachable to stock finders).
    assert 'HIDDEN_TARGET_RAN' not in result.stderr and 'DEFAULT_ENTRY_RAN' not in result.stderr
    receipt = json.loads(result.stdout); entry = receipt['entry_result']
    assert entry['kind'] == 'puck-held-runtime-import-qualification-result-v2'
    assert entry['version'] == 2 and entry['qualification_version'] == version
    assert [row['name'] for row in entry['imports']] == ORDER
    assert {row['name']: row['version'] for row in entry['imports']} == CPU_VERSIONS
    for value in (receipt, entry):
        assert value['runtime_qualified'] is value['native_authorized'] is False
        assert value['collection_authorized'] is value['executable'] is False
        assert value['qualification_claims'] == []
    assert receipt['dependencies_qualified'] is False
    return receipt


def poisoned(result, reason):
    assert result.returncode != 0 and result.stdout == ''
    assert 'V5_BODY_ENTERED\n' in result.stderr and 'V5_CASE_COMPLETED\n' in result.stderr, result.stderr
    assert reason in result.stderr, result.stderr
    assert 'HIDDEN_TARGET_RAN' not in result.stderr and 'DEFAULT_ENTRY_RAN' not in result.stderr


def refused_before_initializers(result, reason):
    assert result.returncode != 0 and result.stdout == ''
    assert reason in result.stderr, result.stderr
    for marker in ('NUMERICAL_INIT_RAN', 'V5_BODY_ENTERED', 'HIDDEN_TARGET_RAN', 'DEFAULT_ENTRY_RAN'):
        assert marker not in result.stderr


def test_v5_declared_absent_names_are_stock_misses_without_poison():
    receipt = succeeded(run('''
        assert owner._reg['qualification']['version'] == 5
        def add(names):  # torch._dynamo.trace_rules.add: bare probe, no handler
            return [importlib.util.find_spec(name) for name in names]
        assert add(['tabulate', 'tensorflow']) == [None, None]
        assert importlib.util.find_spec('torch._rocm_init') is None
        for name in ('tabulate', 'torch._rocm_init'):
            try:
                importlib.import_module(name)
            except ModuleNotFoundError as error:
                assert type(error) is ModuleNotFoundError and error.name == name, (type(error), error.name)
            else:
                raise AssertionError('DECLARED_ABSENT_LOADED')
        try:
            import tensorflow
        except ImportError:
            pass
        assert not {'tabulate', 'tensorflow', 'torch._rocm_init'} & set(sys.modules)
        assert owner._state == 'active' and owner._first_failure is None
        owner.recheck()
    ''', negatives=['tabulate', 'tensorflow']))
    assert receipt['expected_missing_imports'] == sorted(BASE_MISSING+['tabulate', 'tensorflow'])
    assert receipt['expected_hidden_imports'] == HIDDEN
    assert receipt['denied_imports'] == [
        'numpy._distributor_init_local', 'org', 'tabulate', 'tensorflow', 'torch._rocm_init']
    assert receipt['stdlib_cache_aliases'] == {'__mp_main__': '__main__'}


def test_v5_hidden_present_modules_never_execute():
    # Stock-miss answers and receipt for present hidden names. Their files are
    # unreachable to stock finders anyway; the later-finder __hello__ case is
    # the discriminating proof that a resolvable declared name never executes.
    receipt = succeeded(run('''
        assert [importlib.util.find_spec(n) for n in ('networkx', 'pandas', 'sklearn')] == [None]*3
        assert importlib.util.find_spec('torch._cxx_pytree') is None
        for name in ('networkx', 'pandas', 'sklearn', 'torch._cxx_pytree'):
            try:
                importlib.import_module(name)
            except ModuleNotFoundError as error:
                assert type(error) is ModuleNotFoundError and error.name == name, (type(error), error.name)
            else:
                raise AssertionError('HIDDEN_LOADED')
        try:
            from . import _cxx_pytree
        except ImportError:
            pass
        else:
            raise AssertionError('HIDDEN_LOADED')
        assert not {'networkx', 'pandas', 'sklearn', 'torch._cxx_pytree'} & set(sys.modules)
        assert owner._state == 'active' and owner._first_failure is None
        owner.recheck()
    ''', present=['networkx', 'pandas', 'torch._cxx_pytree']))
    assert receipt['expected_missing_imports'] == BASE_MISSING
    assert receipt['expected_hidden_imports'] == HIDDEN
    assert receipt['denied_imports'] == sorted(
        ['numpy._distributor_init_local', 'org']+HIDDEN)


def test_v5_receipt_reports_only_names_actually_requested():
    receipt = succeeded(run('assert owner._state == "active"\n', negatives=['tabulate']))
    assert receipt['expected_missing_imports'] == sorted(BASE_MISSING+['tabulate'])
    assert receipt['expected_hidden_imports'] == HIDDEN
    assert receipt['denied_imports'] == ['numpy._distributor_init_local', 'org']


@pytest.mark.parametrize('request_kind,name', [('import', 'foreign_optional'), ('find_spec', 'foreign_probe'),
    ('import', 'foreign_present'), ('find_spec', 'networkx.algorithms')])
def test_v5_undeclared_request_still_poisons_even_when_caught(request_kind, name):
    action = ('importlib.import_module(name)' if request_kind == 'import' else
              'sys.meta_path[0].find_spec(name)' if '.' in name else 'importlib.util.find_spec(name)')
    poisoned(run('''
        name = %r
        try:
            %s
        except ImportError:
            pass
        assert owner._state == 'failed' and name not in sys.modules
    ''' % (name, action), present=['foreign_present']),
        'Unregistered local or external dependency import: '+name)


@pytest.mark.parametrize('registered', [False, True])
def test_v5_declared_absent_but_present_refuses_before_initializers(registered):
    result = run(negatives=['tabulate'], present=['tabulate'], registered=['tabulate'] if registered else [],
                 defect='before-init')
    refused_before_initializers(result, 'Absent import overlaps a registered module' if registered
                                else 'Absent import has a physical package namespace alternative: tabulate')


_EXPORT = dict(name='torch.hidden_parent.child', producer='torch', phase='module_exec',
               attributes=['hidden_parent_child'], class_binding=None)
_CACHE = dict(name='hidden_cache', producer='fixture_dep._native', phase='module_exec',
              delegate_attributes=[])


@pytest.mark.parametrize('defect', ['registered', 'registered-present', 'registered-package', 'export-parent',
    'native-cache',
    'local', 'stdlib', 'negative', 'negative-parent', 'negative-child', 'empty', 'unsorted', 'duplicate',
    'prefix', 'reserved', 'too-many', 'not-list', 'non-string'])
def test_v5_hidden_declaration_is_strict_before_initializers(defect):
    hidden = list(HIDDEN); negatives = []; present = []; registered = []; exports = []; change = None
    native_cache = []
    reason = 'Expected missing imports must be sorted, unique and nonoverlapping'
    custody = 'Hidden import overlaps a registered dependency module, namespace or export: '
    if defect == 'registered': hidden.append('fixture_dep'); reason = custody+'fixture_dep'
    elif defect == 'registered-present':
        present = registered = ['networkx']; reason = custody+'networkx'
    elif defect == 'registered-package': hidden.append('mujoco'); reason = custody+'mujoco'
    elif defect == 'export-parent':
        hidden.append('torch.hidden_parent'); exports = [_EXPORT]; reason = custody+'torch.hidden_parent'
    elif defect == 'native-cache':
        hidden.append('hidden_cache'); native_cache = [_CACHE]; reason = custody+'hidden_cache'
    elif defect == 'local':
        hidden.append('palimpsest.optional'); reason = 'Expected missing import overlaps authenticated local source'
    elif defect == 'stdlib':
        hidden.append('json.optional'); reason = 'Explicit non-stdlib local module name required'
    elif defect in ('negative', 'negative-parent', 'negative-child'):
        negatives = ['tabulate']
        hidden.append({'negative': 'tabulate', 'negative-parent': 'tabulate.extra'}.get(defect, 'tabulate'))
        if defect == 'negative-child': negatives = ['tabulate.extra']
        reason = 'Expected hidden imports must be disjoint from expected missing imports'
    elif defect == 'empty': hidden = []; reason = 'Bounded expected missing import declaration required'
    elif defect == 'unsorted': change = lambda q: q['hidden_imports'].reverse()
    elif defect == 'duplicate': hidden.append('networkx')
    elif defect == 'prefix': hidden.append('networkx.algorithms')
    elif defect == 'reserved':
        hidden.append('_puck_held_file_bootstrap'); reason = 'Bounded expected missing import declaration required'
    elif defect == 'too-many':
        hidden = ['hidden_'+str(i).zfill(3) for i in range(129)]
        reason = 'Bounded expected missing import declaration required'
    elif defect == 'not-list':
        change = lambda q: q.update(hidden_imports='networkx')
        reason = 'Bounded expected missing import declaration required'
    else:
        change = lambda q: q.update(hidden_imports=[1]); reason = 'Bounded expected missing import declaration required'
    refused_before_initializers(run(negatives=negatives, hidden=hidden, present=present, registered=registered,
        exports=exports, native_cache=native_cache, change=change, defect='before-init'), reason)


@pytest.mark.parametrize('version,key', [(5, False), (4, True), (3, True)])
def test_hidden_declaration_key_belongs_only_to_v5(version, key):
    def change(q):
        if key: q['hidden_imports'] = ['networkx']
        else: del q['hidden_imports']
    refused_before_initializers(run(version=version, change=change, defect='before-init'),
                                'Exact fixed runtime qualification descriptor required')


@pytest.mark.parametrize('declared', ['negative', 'hidden'])
def test_v5_later_meta_path_finder_resolving_a_declared_name_poisons(declared):
    # The frozen __hello__ module is resolvable by the original FrozenImporter
    # and is not a stdlib_module_names entry, so returning None would load it.
    poisoned(run('''
        try:
            importlib.util.find_spec('__hello__')
        except ImportError:
            pass
        else:
            raise AssertionError('LATER_FINDER_IGNORED')
        assert owner._state == 'failed' and '__hello__' not in sys.modules
        assert '__hello__' in owner._denied_imports
    ''', negatives=['__hello__'] if declared == 'negative' else [],
        hidden=HIDDEN+(['__hello__'] if declared == 'hidden' else [])),
        'Declared unavailable import resolved by a later finder: __hello__')


def test_v5_keeps_q4_stdlib_baseline_guard():
    poisoned(run('''
        assert owner._stdlib_names is sys.stdlib_module_names
        original = sys.stdlib_module_names
        sys.stdlib_module_names = frozenset(list(original))  # frozenset(frozenset) is identity
        assert sys.stdlib_module_names is not original and sys.stdlib_module_names == original
        try:
            owner._import_recheck()
        except RuntimeError as error:
            assert str(error) == 'Q4 stdlib name baseline changed', str(error)
        else:
            raise AssertionError('Q4_BASELINE_IGNORED')
        finally:
            sys.stdlib_module_names = original
        assert owner._state == 'failed'
    '''), 'Q4 stdlib name baseline changed')


def test_v5_keeps_q4_cache_boundary():
    poisoned(run('''
        sys.modules['fixture_v5_unknown'] = types.ModuleType('fixture_v5_unknown')
        try:
            owner._import_recheck()
        except RuntimeError as error:
            assert str(error) == 'Unregistered module cache entry: fixture_v5_unknown', str(error)
        else:
            raise AssertionError('Q4_CACHE_IGNORED')
        finally:
            sys.modules.pop('fixture_v5_unknown', None)
    '''), 'Unregistered module cache entry: fixture_v5_unknown')


@pytest.mark.parametrize('field', ['negative_imports', 'hidden_imports'])
def test_v5_declared_rosters_are_bound_for_the_worker_lifetime(field):
    poisoned(run('''
        owner._reg['qualification'][%r].append('zz_unreviewed')
        try:
            owner._import_recheck()
        except RuntimeError as error:
            assert str(error) == 'Expected missing import declaration changed', str(error)
        else:
            raise AssertionError('ROSTER_CHANGE_IGNORED')
    ''' % field), 'Expected missing import declaration changed')


def test_v5_emits_q4_phase_and_guard_diagnostics():
    result = run('assert owner._trace_enabled and owner._guard_enabled\n')
    succeeded(result)
    records = [json.loads(line) for line in result.stderr.splitlines() if line.startswith('{')]
    assert [row['phase'] for row in records if row['kind'] == 'puck-worker-phase-v1'][:6] == [
        'bootstrap.enter', 'source.ready', 'dependencies.enter', 'dependencies.ready', 'bootstrap.ready',
        'entry.enter']
    assert any(row['kind'] == 'puck-worker-guard-cost-v1' for row in records)


@pytest.mark.parametrize('dependency_version', [1, 2])
def test_v5_requires_v3_tmpfs_custody_before_initializers(dependency_version):
    refused_before_initializers(run(defect='before-init', dependency_version=dependency_version),
        'Four-import qualification requires admitted v3 tmpfs dependency custody')


def test_v4_declared_absence_keeps_explicit_denial_and_receipt():
    receipt = succeeded(run('''
        try:
            importlib.util.find_spec('tabulate')
        except ModuleNotFoundError as error:
            assert str(error) == 'Explicit qualification import denial: tabulate', str(error)
        else:
            raise AssertionError('V4_DENIAL_RELAXED')
        assert owner._state == 'active'
    ''', version=4, negatives=['tabulate']), version=4)
    assert 'expected_hidden_imports' not in receipt
    assert receipt['denied_imports'] == ['numpy._distributor_init_local', 'org', 'tabulate']


def test_v4_has_no_hidden_names_and_still_poisons_a_caught_request():
    poisoned(run('''
        try:
            import networkx
        except ImportError:
            pass
    ''', version=4, present=['networkx']), 'Unregistered local or external dependency import: networkx')


def test_v5_worker_clock_extends_only_with_the_exact_epoch14_registration():
    succeeded(run('''
        import time
        remaining = owner._deadline - time.monotonic()
        assert 300 < remaining <= 360, remaining
        assert owner._dependencies.provider._deadline == owner._deadline
    ''', registration_change=lambda reg: reg.update(deadline_seconds=360)))


def test_v5_worker_clock_defaults_to_the_original_180_seconds():
    succeeded(run('''
        import time
        remaining = owner._deadline - time.monotonic()
        assert 120 < remaining <= 180, remaining
        assert 'deadline_seconds' not in owner._reg
    '''))


@pytest.mark.parametrize('version,seconds', [(5, 180), (5, 361), (5, True), (5, 360.0), (5, '360'), (4, 360)])
def test_extended_worker_clock_is_exact_and_policy_v5_only(version, seconds):
    refused_before_initializers(run(version=version, defect='before-init',
        registration_change=lambda reg: reg.update(deadline_seconds=seconds)),
        'Exact extended worker deadline requires qualification v5')
