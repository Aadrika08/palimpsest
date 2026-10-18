"""Exact absent-import proofs use authored package censuses only."""
import hashlib
import importlib.machinery
import signal
import threading

import pytest

from test_puck_dependency_files import held, setup


def add_file(reg, root, relative, *, index=0, payload=b"inert\n"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    reg['roots'][index]['files'].append({'path':relative, 'size_bytes':len(payload),
        'sha256':hashlib.sha256(payload).hexdigest()})
    reg['roots'][index]['files'].sort(key=lambda row:row['path'])


def add_package_root(reg, tmp_path):
    root = tmp_path / 'other-packages'
    root.mkdir()
    reg['roots'].append({'root':str(root), 'kind':'package', 'files':[]})
    add_file(reg, root, 'retained.txt', index=1)
    return root


@pytest.mark.parametrize('names', [('absent_top',), ('demo.optional',),
    ('absent_top', 'demo.optional'), tuple('absent_'+str(i).zfill(3) for i in range(128))])
def test_exact_absent_names_are_proved_from_active_held_packages(tmp_path, names):
    root, leaf, reg, path = setup(tmp_path)
    with held(reg, path) as holder:
        assert holder.require_absent_imports(names) is None
        assert holder.read(0, 'demo/__init__.py') == b'value = 7\n'


@pytest.mark.parametrize('names', [[], (), ['demo.optional'], ('demo.optional', 'demo.optional'),
    ('z_absent', 'a_absent'), ('demo.optional', 'demo.optional.child'), ('demo.*',),
    ('demo.é',), ('os.optional',), ('a'*513,), (True,),
    tuple('absent_'+str(i).zfill(3) for i in range(129))])
def test_invalid_absent_contract_poisons_even_when_caught(tmp_path, names):
    root, leaf, reg, path = setup(tmp_path)
    with pytest.raises(RuntimeError, match='failed before context exit'):
        with held(reg, path) as holder:
            with pytest.raises(ValueError): holder.require_absent_imports(names)
            with pytest.raises(RuntimeError): holder.read(0, 'demo/__init__.py')
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


@pytest.mark.parametrize('name', ['demo', 'demo.empty', 'unknown.child', 'demo.optional.child'])
def test_existing_package_empty_directory_or_unregistered_parent_is_refused(tmp_path, name):
    root, leaf, reg, path = setup(tmp_path)
    with pytest.raises(ValueError):
        with held(reg, path) as holder: holder.require_absent_imports((name,))
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


COLLISIONS = [('', 'directory'), ('', 'file'), ('.py', 'file'), ('.pyc', 'file'),
    *[(suffix, 'file') for suffix in importlib.machinery.EXTENSION_SUFFIXES],
    ('tagged-bytecode', 'file')]


@pytest.mark.parametrize('name,stem', [('absent_top', 'absent_top'), ('demo.optional', 'demo/optional')])
@pytest.mark.parametrize('suffix,kind', COLLISIONS)
def test_inert_physical_import_alternatives_refuse_absence(tmp_path, name, stem, suffix, kind):
    root, leaf, reg, path = setup(tmp_path)
    if kind == 'directory': (root / stem).mkdir()
    elif suffix == 'tagged-bytecode':
        parent, _, last = stem.rpartition('/')
        add_file(reg, root, (parent+'/' if parent else '')+'__pycache__/'+last+'.cpython-311.pyc')
    else: add_file(reg, root, stem+suffix)
    with pytest.raises(ValueError):
        with held(reg, path) as holder: holder.require_absent_imports((name,))


@pytest.mark.parametrize('relative', ['demo/optional_extra.py', 'demo/optional_extra',
    'demo/__pycache__/optional_extra.cpython-311.pyc', 'demo/optional.py.backup'])
def test_physical_prefix_siblings_do_not_expand_exact_absence(tmp_path, relative):
    root, leaf, reg, path = setup(tmp_path)
    if relative.endswith('optional_extra'): (root / relative).mkdir()
    else: add_file(reg, root, relative)
    with held(reg, path) as holder: holder.require_absent_imports(('demo.optional',))


@pytest.mark.parametrize('name,stem', [('absent_top', 'absent_top.py'), ('demo.optional', 'demo/optional.py')])
def test_canonical_alternative_in_another_package_root_is_refused(tmp_path, name, stem):
    root, leaf, reg, path = setup(tmp_path)
    other = add_package_root(reg, tmp_path)
    add_file(reg, other, stem, index=1)
    with pytest.raises(ValueError):
        with held(reg, path) as holder: holder.require_absent_imports((name,))


@pytest.mark.parametrize('present', [False, True])
def test_child_absence_uses_remapped_package_parent_path(tmp_path, present):
    root, leaf, reg, path = setup(tmp_path)
    add_file(reg, root, 'relocated/__init__.py')
    reg['modules'][0]['path'] = 'relocated/__init__.py'
    if present: add_file(reg, root, 'relocated/optional.py')
    holder = held(reg, path)
    if present:
        with pytest.raises(ValueError):
            with holder: holder.require_absent_imports(('demo.optional',))
    else:
        with holder: holder.require_absent_imports(('demo.optional',))


@pytest.mark.parametrize('present', [False, True])
def test_child_absence_uses_registered_namespace_parent_path(tmp_path, present):
    root, leaf, reg, path = setup(tmp_path)
    add_file(reg, root, 'demo/relocated/data.txt')
    reg['namespaces'] = [{'name':'demo.ns', 'root_index':0, 'path':'demo/relocated'}]
    if present: (root / 'demo/relocated/optional').mkdir()
    holder = held(reg, path)
    if present:
        with pytest.raises(ValueError):
            with holder: holder.require_absent_imports(('demo.ns.optional',))
    else:
        with holder: holder.require_absent_imports(('demo.ns.optional',))


def test_registered_module_name_cannot_be_hidden_by_different_physical_mapping(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    add_file(reg, root, 'demo/elsewhere.py')
    reg['modules'].append({'name':'demo.optional', 'root_index':0, 'path':'demo/elsewhere.py',
        'kind':'python', 'is_package':False})
    with pytest.raises(ValueError):
        with held(reg, path) as holder: holder.require_absent_imports(('demo.optional',))


@pytest.mark.parametrize('export', ['demo.optional', 'demo.optional.child'])
def test_declared_export_is_refused_before_it_can_be_prepared_or_cached(tmp_path, export):
    root, leaf, reg, path = setup(tmp_path)
    reg.update(kind='puck-worker-dependencies-v2', version=2,
        import_profile={'exports':[{'name':export, 'producer':'demo', 'phase':'module_exec',
            'attributes':['optional'], 'class_binding':None}], 'module_changes':[], 'native_origins':[]})
    with pytest.raises(ValueError):
        with held(reg, path) as holder: holder.require_absent_imports(('demo.optional',))


@pytest.mark.parametrize('lifetime', ['new', 'closed'])
def test_absent_proof_requires_active_lifetime(tmp_path, lifetime):
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    if lifetime == 'closed':
        with holder: pass
    with pytest.raises(RuntimeError): holder.require_absent_imports(('demo.optional',))


def test_absent_proof_checks_whole_namespace_before_evaluating_retained_census(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    with pytest.raises(RuntimeError, match='failed before context exit'):
        with held(reg, path) as holder:
            (root / 'unrelated-empty-directory').mkdir()
            with pytest.raises(RuntimeError): holder.require_absent_imports(('demo.optional',))
            with pytest.raises(RuntimeError): holder.read(0, 'demo/__init__.py')
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


def test_offthread_absent_proof_poisons_without_releasing_owner_signal(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    failures = []
    with pytest.raises(RuntimeError, match='failed before context exit'):
        with held(reg, path) as holder:
            handler = signal.getsignal(signal.SIGIO)
            def misuse():
                try: holder.require_absent_imports(('demo.optional',))
                except BaseException as error: failures.append(error)
            thread = threading.Thread(target=misuse)
            thread.start(); thread.join()
            assert len(failures) == 1 and isinstance(failures[0], RuntimeError)
            assert 'original main thread' in str(failures[0])
            assert signal.getsignal(signal.SIGIO) is handler
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL
