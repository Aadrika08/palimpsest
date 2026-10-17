"""Native metadata v6: explicit dynamic-loaded host leaves for the held episode.

Authored metadata only. v6 admits up to 256 leaves of at most 256 MiB each
(libLLVM is about 171 MB), declares dlopen-only leaves explicitly instead of
inferring them from ELF walks, and pins the one GLVND EGL vendor JSON that the
parent stages under the control tree. v5 keeps its exact contract.
"""
import copy
import hashlib
import json

import pytest

from test_puck_cpu_registration import api, build, case, row


VENDOR=b'{\n    "file_format_version" : "1.0.0",\n    "ICD" : {\n        "library_path" : "libEGL_mesa.so.0"\n    }\n}\n'
MiB=1024**2


def big(path,size):
    return dict(path=path,size_bytes=size,sha256='a'*64)


def v6_case():
    data=case();native=data['native']
    leaves=['/usr/lib/libEGL.so.1.1.0','/usr/lib/libEGL_mesa.so.0.0.0','/usr/lib/libLLVM.so.22.1',
            '/usr/lib/libOpenGL.so.0.0.0','/usr/lib/libglfw.so.3.4']
    native.update(kind='puck-cpu-characterization-native-metadata-v6',
        root_scope='installed_shared_objects_interpreter_and_declared_dynamic_leaves',
        native_files=sorted(native['native_files']+[big(path,171*MiB if 'LLVM' in path else MiB) for path in leaves],
                            key=lambda r:r['path']),
        aliases=native['aliases']+[['/usr/lib/libEGL_mesa.so.0','libEGL_mesa.so.0.0.0']],
        dynamic_leaves=list(leaves),
        egl_vendor=dict(path='/usr/share/glvnd/egl_vendor.d/50_mesa.json',size_bytes=len(VENDOR),
                        sha256=hashlib.sha256(VENDOR).hexdigest(),library_path='libEGL_mesa.so.0'))
    return data


def test_v6_plans_large_declared_dynamic_leaves_into_the_system_roots():
    result=build(v6_case())
    usr={row['path']:row for row in result['roots'][1]['files']}
    assert usr['lib/libLLVM.so.22.1']['size_bytes']==171*MiB and 'lib/libglfw.so.3.4' in usr
    assert [r['path'] for r in result['roots'][2]['files']]==['ld.so.cache']


def test_v6_admits_exactly_256_leaves_of_256_mib():
    data=v6_case();native=data['native']
    extra=['/usr/lib/libmesa%03d.so'%i for i in range(256-len(native['native_files']))]
    native['native_files']=sorted(native['native_files']+[big(p,256*MiB) for p in extra],key=lambda r:r['path'])
    assert len(native['native_files'])==256
    build(data)


@pytest.mark.parametrize('defect',['leaf-too-large','too-many','v5-large-leaf','scope','extra-key',
    'dynamic-unsorted','dynamic-missing-file','dynamic-outside-lib','dynamic-empty','vendor-path','vendor-library',
    'vendor-unresolved','vendor-size','vendor-extra','status','errors'])
def test_native_metadata_contracts_are_exact(defect):
    data=v6_case() if not defect.startswith('v5') else case();native=data['native']
    if defect=='leaf-too-large':native['native_files'][-2]['size_bytes']=256*MiB+1
    elif defect=='too-many':
        extra=['/usr/lib/libmesa%03d.so'%i for i in range(257-len(native['native_files']))]
        native['native_files']=sorted(native['native_files']+[big(p,1) for p in extra],key=lambda r:r['path'])
    elif defect=='v5-large-leaf':
        native['native_files']=sorted(native['native_files']+[big('/usr/lib/libLLVM.so.22.1',171*MiB)],key=lambda r:r['path'])
    elif defect=='scope':native['root_scope']='installed_shared_objects_and_interpreter'
    elif defect=='extra-key':native['inferred_dynamic']=[]
    elif defect=='dynamic-unsorted':native['dynamic_leaves'].reverse()
    elif defect=='dynamic-missing-file':native['dynamic_leaves'].append('/usr/lib/libunlisted.so')
    elif defect=='dynamic-outside-lib':native['dynamic_leaves']=sorted(native['dynamic_leaves']+['/usr/bin/ldconfig'])
    elif defect=='dynamic-empty':native['dynamic_leaves']=[]
    elif defect=='vendor-path':native['egl_vendor']['path']='/etc/glvnd/50_mesa.json'
    elif defect=='vendor-library':native['egl_vendor']['library_path']='/usr/lib/libEGL_mesa.so.0'
    elif defect=='vendor-unresolved':native['egl_vendor']['library_path']='libEGL_other.so.0'
    elif defect=='vendor-size':native['egl_vendor']['size_bytes']=0
    elif defect=='vendor-extra':native['egl_vendor']['dlopen']=True
    elif defect=='status':native['status']='PARTIAL'
    else:native['errors']=['authored']
    with pytest.raises(ValueError):build(data)


def test_v5_keeps_its_exact_contract():
    build(case())
    data=case();data['native']['native_files'].append(big('/usr/lib/libzz.so',64*MiB+1))
    with pytest.raises(ValueError):build(data)


def test_staged_egl_vendor_json_is_exactly_the_pinned_host_bytes():
    native=v6_case()['native']
    assert api().egl_vendor_control(native,VENDOR)==VENDOR
    assert api().EGL_VENDOR_CONTROL=='/puck/control/egl-vendor.json'


@pytest.mark.parametrize('defect',['bytes-differ','library','extra-top','extra-icd','not-bytes','version-type'])
def test_staged_egl_vendor_json_refuses_any_other_bytes(defect):
    native=v6_case()['native']
    payloads={'library':{'file_format_version':'1.0.0','ICD':{'library_path':'libEGL_nvidia.so.0'}},
              'extra-top':{'file_format_version':'1.0.0','ICD':{'library_path':'libEGL_mesa.so.0'},'extra':1},
              'extra-icd':{'file_format_version':'1.0.0','ICD':{'library_path':'libEGL_mesa.so.0','api_version':'1.5'}},
              'version-type':{'file_format_version':1,'ICD':{'library_path':'libEGL_mesa.so.0'}}}
    if defect=='bytes-differ':payload=VENDOR+b' '
    elif defect=='not-bytes':payload=VENDOR.decode()
    else:
        # Re-pin the metadata to the altered bytes so only the content rule can refuse.
        payload=json.dumps(payloads[defect]).encode()
        native['egl_vendor'].update(size_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
    with pytest.raises(ValueError):api().egl_vendor_control(native,payload)


def test_egl_vendor_requires_v6_metadata():
    with pytest.raises(ValueError):api().egl_vendor_control(case()['native'],VENDOR)
