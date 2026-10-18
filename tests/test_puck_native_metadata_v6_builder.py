"""Read-only native metadata v6 builder over an authored host tree.

The builder unions the v5 closure with the observed episode native maps,
re-hashes every leaf on the host, adds only verified SONAME aliases, declares
the dynamic leaves explicitly, pins the EGL vendor JSON and validates the
result with the v6 planner contract. It never writes outside its new output.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sysconfig

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/build_puck_native_metadata_v6.py'
VENDOR=b'{\n    "file_format_version" : "1.0.0",\n    "ICD" : {\n        "library_path" : "libEGL_authored.so.0"\n    }\n}\n'


def api():
    spec=importlib.util.spec_from_file_location('native_v6_builder_test',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def sha(raw):return hashlib.sha256(raw).hexdigest()


def library(host,name,soname):
    source=host/'authored.c';source.write_text('int authored_symbol(void){return 7;}\n')
    target=host/'usr/lib'/name;target.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['cc','-shared','-fPIC','-Wl,-soname,'+soname,str(source),'-o',str(target)],check=True,capture_output=True,timeout=30)
    source.unlink()
    if soname!=name:(host/'usr/lib'/soname).symlink_to(name)
    return target


def row(host,path):
    raw=(host/path.lstrip('/')).read_bytes();return dict(path=path,size_bytes=len(raw),sha256=sha(raw))


@pytest.fixture
def case(tmp_path):
    host=tmp_path/'host';(host/'etc').mkdir(parents=True);(host/'usr/bin').mkdir(parents=True)
    (host/'etc/ld.so.cache').write_bytes(b'AUTHORED cache');(host/'usr/bin/ldconfig').write_bytes(b'AUTHORED ldconfig')
    library(host,'libbase.so.1.0','libbase.so.1');library(host,'libEGL_authored.so.0.0.0','libEGL_authored.so.0')
    library(host,'libgallium-authored.so','libgallium-authored.so')
    (host/'usr/lib/gconv').mkdir();(host/'usr/lib/gconv/gconv-modules.cache').write_bytes(b'AUTHORED gconv')
    vendor=host/'usr/share/glvnd/egl_vendor.d/50_authored.json';vendor.parent.mkdir(parents=True);vendor.write_bytes(VENDOR)
    v5=dict(kind='puck-cpu-characterization-native-metadata-v5',status='COMPLETE',
        root_scope='installed_shared_objects_and_interpreter',errors=[],oversized_native_files=[],required_missing_names=[],
        native_files=[row(host,'/etc/ld.so.cache'),row(host,'/usr/bin/ldconfig'),row(host,'/usr/lib/libbase.so.1.0')],
        aliases=[['/lib','usr/lib'],['/usr/lib/libbase.so.1','libbase.so.1.0']],installed_DSO_metadata=[])
    observed=dict(kind='diagnostic-held-episode-native-maps-v1',diagnostic_only=True,host=[
        dict(row(host,path),realpath=None,during_rendering=True,source_end=True,replay_end=True) for path in
        ('/etc/ld.so.cache','/usr/lib/gconv/gconv-modules.cache','/usr/lib/libEGL_authored.so.0.0.0',
         '/usr/lib/libbase.so.1.0','/usr/lib/libgallium-authored.so')],site_mapped_source_end=[])
    paths={}
    for name,value in (('v5',v5),('observed',observed)):
        path=tmp_path/(name+'.json');path.write_text(json.dumps(value,indent=1));paths[name]=path
    dynamic=['/usr/lib/gconv/gconv-modules.cache','/usr/lib/libEGL_authored.so.0.0.0','/usr/lib/libgallium-authored.so']
    return dict(host=host,v5=paths['v5'],observed=paths['observed'],vendor='/usr/share/glvnd/egl_vendor.d/50_authored.json',
                dynamic=dynamic,output=tmp_path/'native-06.json')


def build(case,**changes):
    arguments=dict(v5=case['v5'],observed=case['observed'],vendor=case['vendor'],output=case['output'],
                   host_root=case['host'],dynamic_leaves=case['dynamic'])
    arguments.update(changes)
    return api().build(**arguments)


def test_builder_unions_rehashes_declares_and_validates(case):
    summary=build(case)
    document=json.loads(case['output'].read_bytes())
    assert document['kind']=='puck-cpu-characterization-native-metadata-v6'
    assert [r['path'] for r in document['native_files']]==['/etc/ld.so.cache','/usr/bin/ldconfig',
        '/usr/lib/gconv/gconv-modules.cache','/usr/lib/libEGL_authored.so.0.0.0','/usr/lib/libbase.so.1.0',
        '/usr/lib/libgallium-authored.so']
    assert document['dynamic_leaves']==case['dynamic']
    assert ['/usr/lib/libEGL_authored.so.0','libEGL_authored.so.0.0.0'] in document['aliases']
    assert ['/usr/lib/libbase.so.1','libbase.so.1.0'] in document['aliases'] and ['/lib','usr/lib'] in document['aliases']
    assert not any(alias[0].endswith('gallium-authored.so') for alias in document['aliases'])
    assert document['egl_vendor']==dict(path=case['vendor'],size_bytes=len(VENDOR),sha256=sha(VENDOR),
                                        library_path='libEGL_authored.so.0')
    inputs={r['role']:r for r in document['provenance']['inputs']}
    assert inputs['metadata05']['sha256']==sha(case['v5'].read_bytes())
    assert inputs['observed_native_maps']['sha256']==sha(case['observed'].read_bytes())
    assert document['provenance']['helper']['sha256']==sha(SCRIPT.read_bytes())
    assert summary['status']=='VALID' and summary['native_file_count']==6 and summary['output_sha256']==sha(case['output'].read_bytes())
    from palimpsest.puck_cpu_registration import egl_vendor_control
    assert egl_vendor_control(document,VENDOR)==VENDOR


def test_builder_is_deterministic(case,tmp_path):
    build(case);first=case['output'].read_bytes()
    build(case,output=tmp_path/'again.json')
    assert (tmp_path/'again.json').read_bytes()==first


@pytest.mark.parametrize('defect',['host-changed','observed-outside-usr','undeclared-dynamic','declared-unknown',
    'soname-link-missing','vendor-unresolved','output-exists','symlink-leaf'])
def test_builder_refuses_inconsistent_inputs(case,defect):
    host=case['host']
    if defect=='host-changed':(host/'usr/lib/gconv/gconv-modules.cache').write_bytes(b'AUTHORED changed')
    elif defect=='observed-outside-usr':
        value=json.loads(case['observed'].read_text());(host/'opt').mkdir();(host/'opt/x.so').write_bytes(b'x')
        value['host'].append(dict(row(host,'/opt/x.so'),realpath=None,during_rendering=True,source_end=True,replay_end=True))
        case['observed'].write_text(json.dumps(value))
    elif defect=='undeclared-dynamic':case['dynamic']=case['dynamic'][1:]
    elif defect=='declared-unknown':case['dynamic']=sorted(case['dynamic']+['/usr/lib/libunlisted.so'])
    elif defect=='soname-link-missing':(host/'usr/lib/libEGL_authored.so.0').unlink()
    elif defect=='vendor-unresolved':
        raw=VENDOR.replace(b'libEGL_authored.so.0',b'libEGL_other.so.0');(host/case['vendor'].lstrip('/')).write_bytes(raw)
    elif defect=='output-exists':case['output'].write_bytes(b'existing')
    else:
        leaf=host/'usr/lib/libgallium-authored.so';real=host/'usr/lib/libgallium-real.so';leaf.rename(real);leaf.symlink_to(real.name)
    before=case['output'].read_bytes() if case['output'].exists() else None
    with pytest.raises((ValueError,FileExistsError)):build(case)
    assert (case['output'].read_bytes() if case['output'].exists() else None)==before


def test_builder_constant_declares_the_episode_dynamic_leaves_explicitly():
    m=api()
    assert list(m.EPISODE_DYNAMIC_LEAVES)==sorted(set(m.EPISODE_DYNAMIC_LEAVES))
    assert {'/usr/lib/libEGL_mesa.so.0.0.0','/usr/lib/libLLVM.so.22.1','/usr/lib/libgallium-26.2.2-arch1.1.so',
            '/usr/lib/libEGL.so.1.1.0','/usr/lib/libOpenGL.so.0.0.0','/usr/lib/libGLdispatch.so.0.0.0',
            '/usr/lib/locale/locale-archive'}<=set(m.EPISODE_DYNAMIC_LEAVES)
    assert all(path.startswith('/usr/lib/') for path in m.EPISODE_DYNAMIC_LEAVES)
