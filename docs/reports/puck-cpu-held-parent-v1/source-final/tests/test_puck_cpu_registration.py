"""Byte-only CPU planning from tiny authored, externally pinned receipts."""
import copy
import hashlib
import importlib
import importlib.util
import json
import time

import pytest

NAME = 'palimpsest.puck_cpu_registration'
EXT = 'demo/_core.cpython-311-x86_64-linux-gnu.so'


def api():
    assert importlib.util.find_spec(NAME) is not None, 'CPU byte planner is missing'
    return importlib.import_module(NAME)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path, raw=b'inert authored bytes'):
    return dict(path=path, size_bytes=len(raw), sha256=sha(raw))


def case():
    entries = sorted([row('demo/__init__.py'), row(EXT),
                      row('demo/__pycache__/inert.pyc'),
                      row('demo-1.dist-info/METADATA', b'Name: demo\nVersion: 1\n')], key=lambda r:r['path'])
    directories = ['demo', 'demo-1.dist-info', 'demo/__pycache__', 'empty', 'empty/nested']
    inventory = dict(kind='puck-cpu-installed-files-v1', entries=entries,
                     file_count=4, directory_count=5, total_bytes=sum(r['size_bytes'] for r in entries))
    collisions = dict(case_sensitive_linux_paths=True, destination_directory_coownership_is_allowed=True,
                      **{k:[] for k in ('destination_regular_directory_path_conflicts',
                         'destination_regular_path_collisions_including_entrypoint_wrappers',
                         'source_file_ancestor_conflicts', 'source_regular_directory_path_conflicts',
                         'source_regular_path_collisions')})
    metadata = next(r for r in entries if r['path'].endswith('/METADATA'))
    layout = dict(kind='palimpsest-cpu-wheel-install-layout-v1', version=1,
                  predicted_destination_directories=directories,
                  predicted_empty_destination_directories=['empty/nested'], collisions=collisions,
                  wheels=[dict(name='demo', version='1', metadata_path=metadata['path'], metadata_sha256=metadata['sha256'])])
    modules = [dict(name='demo', root_index=0, path='demo/__init__.py', kind='python', is_package=True),
               dict(name='demo._core', root_index=0, path=EXT, kind='extension', is_package=False),
               dict(name='_generated', root_index=3, path='_generated.py', kind='python', is_package=False)]
    profile = dict(kind='puck-producer-import-profile-v2', version=2, exports=[], module_changes=[],
                   native_origins=[dict(name='demo._core', policy='held-directory-observed-v1')],
                   native_cache=[dict(name='cython_runtime', producer='demo._core', phase='module_exec', delegate_attributes=[])])
    candidate = dict(kind='puck-cpu-observed-import-profile-candidate-v1', version=1,
                     module_paths=modules, namespaces=[], import_profile=profile,
                     additional_package_inputs=[dict(root='docs/authored/generated', files=[row('_generated.py')])],
                     expected_versions=dict(numpy='1', torch='1+cpu', torchvision='1+cpu', mujoco='1'),
                     native_phase_qualified=False, held_runtime_qualified=False, native_authorized=False,
                     collection_authorized=False, study_authorized=False, executable=False, qualification_claims=[])
    native = dict(kind='puck-cpu-characterization-native-metadata-v5', status='COMPLETE',
                  root_scope='installed_shared_objects_and_interpreter', errors=[], oversized_native_files=[],
                  required_missing_names=[], native_files=[row('/etc/ld.so.cache'), row('/usr/bin/ldconfig'),
                                                          row('/usr/lib/libauthored.so.1')],
                  aliases=[['/lib', 'usr/lib'], ['/usr/lib/libauthored.so', 'libauthored.so.1']])
    return dict(inventory=inventory, layout=layout, candidate=candidate, native=native)


def encoded(data):
    raw = {k:(json.dumps(v, sort_keys=True, indent=2, allow_nan=False)+'\n').encode() for k,v in data.items()}
    pins = {k:dict(size_bytes=len(v), sha256=sha(v)) for k,v in raw.items()}
    return raw, pins


def build(data=None, **kwargs):
    raw, pins = encoded(case() if data is None else data)
    return api().build_cpu_source_registration(*(raw[k] for k in ('inventory','layout','candidate','native')),
        expected_pins=kwargs.pop('expected_pins', pins), site_root=kwargs.pop('site_root','/unread/site'),
        generated_root=kwargs.pop('generated_root','/unread/generated'),
        deadline=kwargs.pop('deadline',time.monotonic()+30), **kwargs)


def staged(source):
    result = copy.deepcopy(source)
    result.update(kind='puck-worker-dependencies-v3', version=3, native_identity='tmpfs-raw-dev-inode-v1')
    for index, root in enumerate(result['roots']):
        root.update(root='/unread/stage/root-'+str(index).zfill(4), kind='package')
    return result


def attach(source=None, candidate=None, **kwargs):
    raw = json.dumps(case()['candidate'] if candidate is None else candidate).encode()
    return api().attach_cpu_candidate(staged(build()) if source is None else source, raw,
        expected_sha256=kwargs.pop('expected_sha256',sha(raw)), deadline=kwargs.pop('deadline',time.monotonic()+30), **kwargs)


def test_planner_maps_four_roots_and_keeps_every_byte_inert_until_attachment():
    data=case();before=copy.deepcopy(data);source=build(data)
    assert data==before
    assert [(r['root'],r['kind']) for r in source['roots']]==[
        ('/unread/site','package'),('/usr','system_images'),('/etc','system_images'),('/unread/generated','package')]
    assert source['roots'][0]['files']==data['inventory']['entries']
    assert source['roots'][1]['files']==[row('bin/ldconfig'),row('lib/libauthored.so.1')]
    assert source['roots'][2]['files']==[row('ld.so.cache')]
    assert source['roots'][3]['files']==[row('_generated.py')]
    assert source['modules']==source['namespaces']==[]
    assert source['import_profile']==dict(exports=[],module_changes=[],native_origins=[])
    assert source['distributions']==[dict(name='demo',version='1',root_index=0,metadata_path='demo-1.dist-info/METADATA')]
    prepared=staged(source);old=copy.deepcopy(prepared);final=attach(prepared,data['candidate'])
    assert prepared==old and final['roots']==old['roots'] and final['distributions']==old['distributions']
    assert final['modules']==data['candidate']['module_paths'] and final['import_profile']==data['candidate']['import_profile']
    final['modules'][0]['name']='mutated'
    assert data==before and prepared==old


@pytest.mark.parametrize('defect',['missing-role','extra-role','size-bool','wrong-hash','wrong-size','extra-pin-field'])
def test_all_input_pins_are_exact_and_typed(defect):
    data=case();raw,pins=encoded(data)
    if defect=='missing-role':del pins['native']
    elif defect=='extra-role':pins['extra']=pins['native']
    elif defect=='size-bool':pins['native']['size_bytes']=True
    elif defect=='wrong-hash':pins['native']['sha256']='0'*64
    elif defect=='wrong-size':pins['native']['size_bytes']+=1
    else:pins['native']['path']='ambient'
    with pytest.raises(ValueError):build(data,expected_pins=pins)


def test_all_authentication_precedes_any_json_planning():
    raw,pins=encoded(case());raw['inventory']=b'{';pins['inventory']=dict(size_bytes=1,sha256=sha(b'{'))
    pins['native']['sha256']='0'*64
    with pytest.raises(ValueError,match='native'):
        api().build_cpu_source_registration(*(raw[k] for k in ('inventory','layout','candidate','native')),
            expected_pins=pins,site_root='/unread/site',generated_root='/unread/generated',deadline=time.monotonic()+30)


@pytest.mark.parametrize('raw',[b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}',
                                b'['*34+b'0'+b']'*34, b'{}'])
def test_bounded_json_refuses_duplicates_nonfinite_depth_and_wrong_schema(raw):
    rows,pins=encoded(case());rows['inventory']=raw;pins['inventory']=dict(size_bytes=len(raw),sha256=sha(raw))
    with pytest.raises(ValueError):
        api().build_cpu_source_registration(*(rows[k] for k in ('inventory','layout','candidate','native')),
            expected_pins=pins,site_root='/unread/site',generated_root='/unread/generated',deadline=time.monotonic()+30)


@pytest.mark.parametrize('defect',['inventory-count','inventory-count-bool','inventory-bytes','directory-count',
    'descriptor-size-bool','duplicate-file','unsorted-files','path-traversal','missing-parent','file-directory',
    'duplicate-directory','wrong-empty-directory','collision','metadata-hash','missing-wheel','duplicate-wheel',
    'native-incomplete','native-error','native-missing','native-path','native-duplicate','native-size-bool',
    'native-alias-duplicate','native-alias-file','candidate-authority','candidate-authority-missing','candidate-version-bool',
    'candidate-root','module-missing','module-index-bool','generated-missing','generated-root-relative',
    'native-cache-producer','native-cache-phase','profile-version'])
def test_authenticated_inconsistent_plans_are_refused(defect):
    d=case();i,l,c,n=(d[k] for k in ('inventory','layout','candidate','native'))
    if defect=='inventory-count':i['file_count']+=1
    elif defect=='inventory-count-bool':i['file_count']=True
    elif defect=='inventory-bytes':i['total_bytes']+=1
    elif defect=='directory-count':i['directory_count']+=1
    elif defect=='descriptor-size-bool':i['entries'][0]['size_bytes']=True
    elif defect=='duplicate-file':i['entries'][1]=copy.deepcopy(i['entries'][0])
    elif defect=='unsorted-files':i['entries'].reverse()
    elif defect=='path-traversal':i['entries'][0]['path']='../escape'
    elif defect=='missing-parent':l['predicted_destination_directories'].remove('demo')
    elif defect=='file-directory':l['predicted_destination_directories'].append('demo/__init__.py');l['predicted_destination_directories'].sort();i['directory_count']+=1
    elif defect=='duplicate-directory':l['predicted_destination_directories'].append('demo')
    elif defect=='wrong-empty-directory':l['predicted_empty_destination_directories']=['demo']
    elif defect=='collision':l['collisions']['source_regular_path_collisions']=['demo']
    elif defect=='metadata-hash':l['wheels'][0]['metadata_sha256']='0'*64
    elif defect=='missing-wheel':l['wheels']=[]
    elif defect=='duplicate-wheel':l['wheels'].append(copy.deepcopy(l['wheels'][0]))
    elif defect=='native-incomplete':n['status']='PARTIAL'
    elif defect=='native-error':n['errors']=['failed readelf']
    elif defect=='native-missing':n['required_missing_names']=['missing.so']
    elif defect=='native-path':n['native_files'][0]['path']='/home/unregistered.so'
    elif defect=='native-duplicate':n['native_files'].append(copy.deepcopy(n['native_files'][0]))
    elif defect=='native-size-bool':n['native_files'][0]['size_bytes']=True
    elif defect=='native-alias-duplicate':n['aliases'].append(n['aliases'][0])
    elif defect=='native-alias-file':n['aliases'].append(['/usr/lib/libauthored.so.1','other'])
    elif defect=='candidate-authority':c['executable']=True
    elif defect=='candidate-authority-missing':del c['study_authorized']
    elif defect=='candidate-version-bool':c['version']=True
    elif defect=='candidate-root':c['additional_package_inputs'].append(copy.deepcopy(c['additional_package_inputs'][0]))
    elif defect=='module-missing':c['module_paths'][0]['path']='absent.py'
    elif defect=='module-index-bool':c['module_paths'][0]['root_index']=True
    elif defect=='generated-missing':c['additional_package_inputs'][0]['files'][0]['path']='other.py'
    elif defect=='generated-root-relative':c['additional_package_inputs'][0]['root']='../generated'
    elif defect=='native-cache-producer':c['import_profile']['native_cache'][0]['producer']='demo'
    elif defect=='native-cache-phase':c['import_profile']['native_cache'][0]['phase']='guess'
    else:c['import_profile']['version']=True
    with pytest.raises(ValueError):build(d)


@pytest.mark.parametrize('kwargs',[dict(site_root='/usr/site'),dict(generated_root='/unread/site/generated'),
    dict(generated_root='relative'),dict(deadline=True),dict(deadline=float('nan')),
    dict(deadline=0),dict(deadline=time.monotonic()+181)])
def test_invalid_roots_and_deadlines_refuse_without_payload_access(kwargs):
    with pytest.raises(ValueError):build(**kwargs)


@pytest.mark.parametrize('defect',['wrong-hash','not-v3','identity','root-count','root-order','root-kind',
                                  'root-file','module-file','distribution-drift'])
def test_attachment_refuses_wrong_stage_or_candidate(defect):
    candidate=case()['candidate'];source=staged(build());kwargs={}
    if defect=='wrong-hash':kwargs['expected_sha256']='0'*64
    elif defect=='not-v3':source['version']=2;source['kind']='puck-worker-dependencies-v2';del source['native_identity']
    elif defect=='identity':source['native_identity']='anything'
    elif defect=='root-count':source['roots'].pop()
    elif defect=='root-order':source['roots'][1],source['roots'][2]=source['roots'][2],source['roots'][1]
    elif defect=='root-kind':source['roots'][1]['kind']='system_images'
    elif defect=='root-file':source['roots'][3]['files'][0]['sha256']='0'*64
    elif defect=='module-file':source['roots'][0]['files']=[r for r in source['roots'][0]['files'] if r['path']!='demo/__init__.py']
    else:source['distributions'][0]['metadata_path']='absent/METADATA'
    with pytest.raises(ValueError):attach(source,candidate,**kwargs)


@pytest.mark.parametrize('defect',['legacy-profile','missing-profile','bad-versions','oversized-file','oversized-total','oversized-native','metadata-cap'])
def test_profile_and_resource_contracts_cannot_be_silently_weakened(defect,monkeypatch):
    data=case()
    if defect=='legacy-profile':data['candidate']['import_profile']=dict(exports=[],module_changes=[],native_origins=[])
    elif defect=='missing-profile':del data['candidate']['import_profile']
    elif defect=='bad-versions':data['candidate']['expected_versions']['numpy']=True
    elif defect=='oversized-file':data['inventory']['entries'][0]['size_bytes']=2*1024**3+1
    elif defect=='oversized-total':
        rows=[row('large'+str(i)) for i in range(9)]
        for item in rows:item['size_bytes']=2*1024**3
        data['inventory']['entries']=rows
    elif defect=='oversized-native':data['native']['native_files'][0]['size_bytes']=64*1024**2+1
    else:monkeypatch.setattr(api(),'MAX_METADATA_BYTES',100)
    with pytest.raises(ValueError):build(data)
