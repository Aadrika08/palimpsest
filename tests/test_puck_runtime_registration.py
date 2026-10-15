"""Registration construction uses only authored temporary package payloads."""
import hashlib
import importlib
import importlib.machinery
import importlib.util
import json
import os
import time

import pytest

NAME = 'palimpsest.puck_runtime_registration'


def api():
    assert importlib.util.find_spec(NAME) is not None, 'Runtime registration builder missing'
    return importlib.import_module(NAME)


def setup(tmp_path):
    site = tmp_path / 'site'; site.mkdir()
    payloads = {'demo/__init__.py': b'# package\n', 'demo/core.py': b'value = 1\n',
                'demo/__pycache__/inert.pyc': b'inert, never loaded',
                'demo-1.2.dist-info/METADATA': b'Metadata-Version: 2.1\nName: demo\nVersion: 1.2\n\n'}
    for path, data in payloads.items():
        leaf = site / path; leaf.parent.mkdir(parents=True, exist_ok=True); leaf.write_bytes(data)
    (site / 'demo' / 'empty').mkdir()
    modules = [row(site, 'demo', 'demo/__init__.py'), row(site, 'demo.core', 'demo/core.py')]
    observation = {'cache': {'modules': modules}, 'maps': {'images': []},
                   'baseline_maps': {'images': []}}
    return site, observation, {'exports': [], 'module_changes': [], 'native_origins': []}, payloads


def row(site, name, path=None, *, spec=True):
    return {'name': name, 'file': str(site / path) if path is not None else None,
            'spec_name': name if spec else None, 'classification': 'module'}


def build(site, observation, profile):
    return api().build_registration(str(site), observation, profile, deadline=time.monotonic() + 30)


def test_complete_regular_census_hashes_inert_bytes_and_metadata(tmp_path):
    site, observation, profile, payloads = setup(tmp_path)
    result = build(site, observation, profile)
    assert set(result) == {'kind', 'version', 'roots', 'modules', 'namespaces', 'distributions', 'import_profile'}
    assert result['kind'] == 'puck-worker-dependencies-v2' and result['version'] == 2
    assert result['roots'] == [{'root': str(site), 'kind': 'package', 'files': [
        {'path': name, 'size_bytes': len(payloads[name]), 'sha256': hashlib.sha256(payloads[name]).hexdigest()}
        for name in sorted(payloads)]}]
    assert result['modules'] == [dict(name='demo', root_index=0, path='demo/__init__.py', kind='python', is_package=True),
                                 dict(name='demo.core', root_index=0, path='demo/core.py', kind='python', is_package=False)]
    assert result['namespaces'] == []
    assert result['distributions'] == [dict(name='demo', version='1.2', root_index=0,
                                          metadata_path='demo-1.2.dist-info/METADATA')]
    assert result['import_profile'] == profile
    assert json.dumps(result, allow_nan=False)


def test_namespace_and_replaced_module_are_attached_to_exact_sources(tmp_path):
    site, observation, profile, _ = setup(tmp_path)
    (site / 'demo' / 'space').mkdir(); (site / 'demo' / 'space' / 'child.py').write_bytes(b'x=1\n')
    observation['cache']['modules'] += [row(site, 'demo.space'), row(site, 'demo.space.child', 'demo/space/child.py')]
    observation['cache']['modules'][1] = row(site, 'demo.core', spec=False)
    profile['module_changes'] = [{'name': 'demo.core', 'kind': 'replace',
        'class_binding': {'kind': 'direct', 'producer': 'demo', 'attributes': ['CustomModule']}}]
    result = build(site, observation, profile)
    assert result['namespaces'] == [dict(name='demo.space', root_index=0, path='demo/space')]
    assert next(v for v in result['modules'] if v['name'] == 'demo.core')['path'] == 'demo/core.py'


def test_exports_even_filebacked_specless_native_children_are_not_physical(tmp_path):
    site, observation, profile, _ = setup(tmp_path)
    native = 'demo/native' + importlib.machinery.EXTENSION_SUFFIXES[0]
    (site / native).write_bytes(b'authored-native-placeholder')
    observation['cache']['modules'] += [row(site, 'demo.native', native), row(site, 'demo.native.virtual', native, spec=False)]
    profile['exports'] = [dict(name='demo.native.virtual', producer='demo.native', phase='native_create',
                               attributes=['virtual'], class_binding=None)]
    result = build(site, observation, profile)
    assert {v['name'] for v in result['modules']} == {'demo', 'demo.core', 'demo.native'}


@pytest.mark.parametrize('kind', ['missing', 'ambiguous', 'virtual', 'spec-alias', 'missing-parent',
                                  'wrong-parent', 'missing-producer', 'namespace-missing', 'namespace-file'])
def test_incomplete_identity_or_parent_maps_fail_explicitly(tmp_path, kind):
    site, observation, profile, _ = setup(tmp_path)
    if kind in ('missing', 'ambiguous'):
        observation['cache']['modules'][1] = row(site, 'demo.core', spec=False)
        profile['module_changes'] = [dict(name='demo.core', kind='replace',
            class_binding=dict(kind='direct', producer='demo', attributes=['CustomModule']))]
        if kind == 'missing': (site / 'demo' / 'core.py').unlink()
        else:
            (site / 'demo' / 'core').mkdir(); (site / 'demo' / 'core' / '__init__.py').write_bytes(b'')
    elif kind == 'virtual': observation['cache']['modules'].append(row(site, 'unknown', spec=False))
    elif kind == 'spec-alias': observation['cache']['modules'][1]['spec_name'] = 'demo.other'
    elif kind == 'missing-parent': observation['cache']['modules'].pop(0)
    elif kind == 'wrong-parent': observation['cache']['modules'][1]['file'] = str(site / 'demo-1.2.dist-info' / 'METADATA')
    elif kind == 'missing-producer':
        profile['exports'] = [dict(name='demo.virtual', producer='demo.missing', phase='module_exec',
                                   attributes=['virtual'], class_binding=None)]
    elif kind == 'namespace-missing': observation['cache']['modules'].append(row(site, 'demo.absent'))
    else:
        (site / 'demo' / 'space').write_bytes(b'not directory')
        observation['cache']['modules'].append(row(site, 'demo.space'))
    with pytest.raises(ValueError): build(site, observation, profile)


@pytest.mark.parametrize('kind', ['symlink', 'fifo', 'selected-alias', 'ancestor-link'])
def test_no_symlinks_special_entries_or_selected_inode_aliases(tmp_path, kind):
    site, observation, profile, _ = setup(tmp_path)
    if kind == 'symlink': (site / 'alias').symlink_to(site / 'demo' / 'core.py')
    elif kind == 'fifo': os.mkfifo(site / 'pipe')
    elif kind == 'selected-alias': os.link(site / 'demo' / 'core.py', site / 'alias')
    else:
        linked = tmp_path / 'link'; linked.symlink_to(site, target_is_directory=True); site = linked
    with pytest.raises((ValueError, OSError)): build(site, observation, profile)


def test_external_hardlink_is_allowed_without_claiming_external_namespace(tmp_path):
    site, observation, profile, _ = setup(tmp_path)
    os.link(site / 'demo' / 'core.py', tmp_path / 'external')
    assert len(build(site, observation, profile)['roots'][0]['files']) == 4


@pytest.mark.parametrize('metadata', [b'Name: demo\nName: other\nVersion: 1\n\n', b'Name: demo\n\n',
                                     b'Name: demo\nVersion: 1\n\xff', b'not a header\n'])
def test_metadata_requires_single_utf8_name_and_version(tmp_path, metadata):
    site, observation, profile, _ = setup(tmp_path)
    (site / 'demo-1.2.dist-info' / 'METADATA').write_bytes(metadata)
    with pytest.raises(ValueError): build(site, observation, profile)


def test_duplicate_normalized_distribution_names_fail(tmp_path):
    site, observation, profile, _ = setup(tmp_path)
    second = site / 'second.dist-info'; second.mkdir()
    (second / 'METADATA').write_bytes(b'Name: Demo\nVersion: 2\n\n')
    with pytest.raises(ValueError): build(site, observation, profile)


@pytest.mark.parametrize('field,value', [('MAX_FILES', 3), ('MAX_FILE_BYTES', 1), ('MAX_TOTAL_BYTES', 1),
                                       ('MAX_CENSUS_ENTRIES', 2), ('MAX_REGISTRATION_BYTES', 1),
                                       ('MAX_METADATA_BYTES', 1)])
def test_resource_limits_fail_closed(tmp_path, monkeypatch, field, value):
    site, observation, profile, _ = setup(tmp_path)
    monkeypatch.setattr(api(), field, value)
    with pytest.raises(ValueError): build(site, observation, profile)


@pytest.mark.parametrize('deadline', [True, float('nan'), float('inf'), -1, 'later'])
def test_invalid_deadline_fails_before_census(tmp_path, deadline):
    with pytest.raises(ValueError): api().build_registration(str(tmp_path / 'missing'), {}, {}, deadline=deadline)


def test_overlong_future_deadline_fails(tmp_path):
    with pytest.raises(ValueError): api().build_registration(str(tmp_path), {}, {}, deadline=time.monotonic() + 181)


def test_exact_driver_aliases_and_stdlib_are_excluded(tmp_path):
    site, observation, profile, _ = setup(tmp_path)
    observation['cache']['modules'] += [row(site, 'json'), row(site, '__main__', spec=False),
                                        row(site, '__mp_main__', spec=False)]
    assert len(build(site, observation, profile)['modules']) == 2


def test_untrusted_map_path_rejected_without_system_payload_io(tmp_path, monkeypatch):
    site, observation, profile, _ = setup(tmp_path)
    observation['maps']['images'] = [{'path': '/etc/never-read-this'}]
    with pytest.raises(ValueError, match='system image'): build(site, observation, profile)


def test_system_selection_is_exact_nonbaseline_canonical_paths_only(tmp_path):
    site, observation, profile, _ = setup(tmp_path)
    observation['baseline_maps']['images'] = [{'path': '/usr/lib/baseline.so'}]
    observation['maps']['images'] = [{'path': '/usr/lib/baseline.so'}, {'path': str(site / 'demo' / 'core.py')},
                                     {'path': '/usr/lib/authored-selection-only.so'}]
    assert api()._system_paths(str(site), observation) == ['authored-selection-only.so']
    observation['maps']['images'].append({'path': '/usr/lib/../etc/no'})
    with pytest.raises(ValueError): api()._system_paths(str(site), observation)


def test_leaf_modification_during_stream_fails(tmp_path, monkeypatch):
    site, observation, profile, _ = setup(tmp_path)
    original = api().os.read; changed = False
    def read(fd, count):
        nonlocal changed
        data = original(fd, count)
        if data and not changed:
            changed = True
            (site / 'demo' / 'core.py').write_bytes(b'value = 2\n')
        return data
    monkeypatch.setattr(api().os, 'read', read)
    with pytest.raises(RuntimeError): build(site, observation, profile)


def test_namespace_mutation_during_hash_fails(tmp_path, monkeypatch):
    site, observation, profile, _ = setup(tmp_path)
    original = api().os.read; changed = False
    def read(fd, count):
        nonlocal changed
        data = original(fd, count)
        if data and not changed:
            changed = True
            (site / 'demo' / 'empty').rmdir()
        return data
    monkeypatch.setattr(api().os, 'read', read)
    with pytest.raises((RuntimeError, OSError)): build(site, observation, profile)


@pytest.mark.parametrize('defect', [None, 'missing', 'physical', 'legacy'])
def test_explicit_cache_profile_maps_only_retained_virtual_identities(tmp_path, defect):
    site, observation, profile, _ = setup(tmp_path)
    native='demo/native'+importlib.machinery.EXTENSION_SUFFIXES[0]
    (site/native).write_bytes(b'authored native bytes, never executed')
    observation['cache']['modules'] += [row(site,'demo.native',native),
        dict(name='cache_only_demo',file=None,spec_name=None,classification='virtual')]
    profile.update(kind='puck-producer-import-profile-v2',version=2,native_cache=[
        dict(name='cache_only_demo',producer='demo.native',phase='module_exec',delegate_attributes=[])])
    if defect=='missing':observation['cache']['modules'].pop()
    if defect=='physical':observation['cache']['modules'][-1]['file']=str(site/native)
    snapshot=api()._Snapshot(time.monotonic()+30)
    try:
        census=snapshot.census(str(site))
        def mapped():
            return api()._module_maps(str(site),observation,profile,census,allow_native_cache=defect!='legacy')
        if defect:
            with pytest.raises(ValueError):mapped()
        else:
            modules,namespaces=mapped()
            assert {r['name'] for r in modules}=={'demo','demo.core','demo.native'}
            assert namespaces==[]
    finally:snapshot.close()
