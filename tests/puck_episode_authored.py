"""AUTHORED held-episode project: a clone of the repository sources over tiny authored data.

Shared by the characterization-04, preparation04, allocation-16 and episode
audit tests. The clone keeps every script and palimpsest module byte-for-byte
except (a) the episode entry, replaced by tests/authored_puck_held_episode.py,
and (b) the explicit authored-scale constants patched below (accepted pins and
site counts, RAM floor). Upstream fly-gym files are authored. Native metadata
v6 is authored from real host rows. Nothing here claims real acceptance.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
AUTHORED='AUTHORED fixture only; no real package acceptance or independent audit'
VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',mujoco='3.3.6',gymnasium='1.2.1')
NATIVE06=json.loads((ROOT/'docs/plans/puck-cpu-characterization-native-metadata-06.json').read_bytes())
NINE=sorted(['/etc/ld.so.cache']+['/usr/lib/'+n for n in ('ld-linux-x86-64.so.2','libc.so.6','libdl.so.2','libm.so.6',
    'libpthread.so.0','librt.so.1','libutil.so.1')])
LEAVES=['/usr/lib/gconv/gconv-modules.cache','/usr/lib/libEGL_mesa.so.0.0.0','/usr/lib/locale/C.utf8/LC_CTYPE',
        '/usr/lib/locale/locale-archive']
UPSTREAM={'upstream/fly-gym/core/__init__.py':b'','upstream/fly-gym/environment/__init__.py':b'',
    'upstream/fly-gym/core/astar.py':b'# AUTHORED fly-gym stand-in\n',
    'upstream/fly-gym/environment/mujoco_model_random_obstacles.xml':b'<mujoco model="authored"/>\n',
    'upstream/fly-gym/environment/mujoco_two_cam_env_random_obstacles.py':b'# AUTHORED fly-gym stand-in\n'}
CHARACTERIZATION='scripts/characterize_puck_cpu_episode.py'
CHAR_AUDITOR='scripts/audit_puck_cpu_episode_characterization.py'
REAL={'accepted':'32605ca0d48537a6eabf98a54d605ad23bf525456760d83726381aeaf38e3e96',
      'native':'48ca37b1c45366bcd53ac195277ade6236537f89a720b50591906764eaf72569',
      'observation02':'4b98ff368e97351b2079ff44c75cb910d08559e5e037a6afc4887c28cd38fea8'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def pretty(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def write(root,name,value):
    raw=value if type(value) is bytes else canonical(value)
    path=root/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.exists():path.unlink()
    path.write_bytes(raw)
    return dict(path=name,size_bytes=len(raw),sha256=sha(raw))


def patch(root,name,pairs):
    """Replace each authored-scale constant exactly once in one cloned file."""
    path=root/name;raw=path.read_bytes()
    for old,new in pairs:
        assert raw.count(old)==1,(name,old);raw=raw.replace(old,new)
    path.write_bytes(raw)


def episode_project(tmp_path,*,defect=None):
    """Authored project root with site, accepted receipts, native v6 and patched clones."""
    root=tmp_path/'authored-episode-project';root.mkdir(mode=0o700)
    for path in [*sorted(ROOT.glob('scripts/*.py')),*sorted(ROOT.glob('src/palimpsest/*.py'))]:
        write(root,path.relative_to(ROOT).as_posix(),path.read_bytes())
    for name in ('pyproject.toml','uv.lock','model_manifests/flynn-full-vision.json',
                 'docs/plans/puck-python-louvain-host-baseline-v1.json'):
        write(root,name,(ROOT/name).read_bytes())
    for name,raw in UPSTREAM.items():write(root,name,raw)
    fake=(ROOT/'tests/authored_puck_held_episode.py').read_bytes()
    if defect is not None:
        assert fake.count(b'AUTHORED_DEFECT = None\n')==1
        fake=fake.replace(b'AUTHORED_DEFECT = None\n',('AUTHORED_DEFECT = '+repr(defect)+'\n').encode())
    write(root,'src/palimpsest/puck_held_episode.py',fake)
    site=root/'runs/puck-cpu-install-01/site';entries=[];wheels=[]
    for name,version in VERSIONS.items():
        source=('__version__ = '+repr(version)+'\n').encode()
        write(site,name+'/__init__.py',source);entries.append(dict(path=name+'/__init__.py',size_bytes=len(source),sha256=sha(source)))
        metadata=('Name: '+name+'\nVersion: '+version+'\n\n').encode();path=name+'-'+version+'.dist-info/METADATA'
        write(site,path,metadata);entries.append(dict(path=path,size_bytes=len(metadata),sha256=sha(metadata)))
        wheels.append(dict(name=name,version=version,metadata_path=path,metadata_sha256=sha(metadata)))
    directories=sorted([w['metadata_path'].split('/')[0] for w in wheels]+list(VERSIONS))
    inventory=dict(kind='puck-cpu-installed-files-v1',entries=sorted(entries,key=lambda r:r['path']),file_count=len(entries),
                   directory_count=len(directories),total_bytes=sum(r['size_bytes'] for r in entries))
    inputs={'inventory':write(root,'runs/puck-cpu-retained-admission-02/inventory.json',inventory)}
    collisions=dict(case_sensitive_linux_paths=True,destination_directory_coownership_is_allowed=True,
        **{k:[] for k in ('destination_regular_directory_path_conflicts','destination_regular_path_collisions_including_entrypoint_wrappers',
            'source_file_ancestor_conflicts','source_regular_directory_path_conflicts','source_regular_path_collisions')})
    inputs['layout']=write(root,'docs/reports/puck-cpu-install-01/wheel-layout.json',dict(kind='palimpsest-cpu-wheel-install-layout-v1',
        version=1,predicted_destination_directories=directories,predicted_empty_destination_directories=[],
        collisions=collisions,wheels=wheels,authored_scope=AUTHORED))
    inputs['baseline']=write(root,'docs/plans/puck-python-louvain-host-baseline-v1.json',
                             (ROOT/'docs/plans/puck-python-louvain-host-baseline-v1.json').read_bytes())
    baseline=json.loads((root/inputs['baseline']['path']).read_bytes())
    rows={r['path']:r for r in NATIVE06['native_files']}
    inputs['native']=write(root,'docs/plans/puck-cpu-characterization-native-metadata-06.json',pretty(dict(
        kind='puck-cpu-characterization-native-metadata-v6',status='COMPLETE',
        root_scope='installed_shared_objects_interpreter_and_declared_dynamic_leaves',errors=[],oversized_native_files=[],
        required_missing_names=[],native_files=[rows[p] for p in sorted(NINE+LEAVES)],
        aliases=sorted(baseline['host_path_aliases']+[['/usr/lib/libEGL_mesa.so.0','libEGL_mesa.so.0.0.0']]),
        dynamic_leaves=LEAVES,egl_vendor=NATIVE06['egl_vendor'],provenance=dict(authored_scope=AUTHORED),limitations=[AUTHORED])))
    inputs['accepted_configuration']=write(root,'docs/plans/puck-cpu-retained-admission-02.json',pretty(dict(
        kind='cpu-retained-installation-admission-v2',version=2,inputs=[inputs['layout']],authored_scope=AUTHORED)))
    inputs['accepted_snapshot']=write(root,'runs/puck-cpu-retained-admission-02/snapshot.json',dict(
        kind='cpu-retained-installation-snapshot-v2',site_root=str(site),configuration_sha256=inputs['accepted_configuration']['sha256']))
    inputs['accepted_result']=write(root,'runs/puck-cpu-retained-admission-02/result.json',dict(
        kind='cpu-retained-installation-admission-result-v2',status='PASS',site_root=str(site),
        configuration_sha256=inputs['accepted_configuration']['sha256'],snapshot_sha256=inputs['accepted_snapshot']['sha256'],
        file_count=inventory['file_count'],directory_count=inventory['directory_count'],regular_file_bytes=inventory['total_bytes'],
        claims=dict(package_preparation_accepted=True,runtime_qualified=False,numerical_imports_executed=False,
                    study_authorized=False,collection_authorized=False)))
    inputs['accepted_audit']=write(root,'docs/reports/puck-cpu-retained-admission-02/acceptance-audit-03.json',dict(
        status='PASS',package_preparation_accepted=True,verified=dict(configuration_sha256=inputs['accepted_configuration']['sha256'])))
    retained=canonical(json.loads((root/inputs['accepted_configuration']['path']).read_bytes()))
    index=[dict(inputs[r],path=p) for r,p in (('inventory','raw/inventory.json'),('accepted_result','raw/result.json'),
        ('accepted_snapshot','raw/snapshot.json'),('accepted_audit','acceptance-audit-03.json'))]
    index.append(dict(path='raw/configuration.json',size_bytes=len(retained),sha256=sha(retained)))
    inputs['accepted_index']=write(root,'docs/reports/puck-cpu-retained-admission-02/evidence-index.json',dict(
        kind='retained-admission-02-evidence-index-v1',entries=index))
    inherited=('accepted_audit','accepted_configuration','accepted_index','accepted_result','accepted_snapshot','baseline','inventory','layout')
    observation02=write(root,'docs/reports/puck-cpu-characterization-02/frozen-configuration.json',pretty(dict(
        kind='puck-cpu-runtime-characterization-v1',version=1,roles={r:inputs[r]['path'] for r in inherited},
        inputs=sorted([inputs[r] for r in inherited],key=lambda r:r['path']),authored_scope=AUTHORED)))
    counts=b'SITE_COUNTS=(%d,%d,%d)' % (inventory['file_count'],inventory['directory_count'],inventory['total_bytes'])
    for name in (CHARACTERIZATION,CHAR_AUDITOR):
        if not (root/name).exists():continue
        patch(root,name,[(REAL['accepted'].encode(),inputs['accepted_configuration']['sha256'].encode()),
            (REAL['native'].encode(),inputs['native']['sha256'].encode()),(b'size_bytes=17199',b'size_bytes=%d' % inputs['native']['size_bytes']),
            (REAL['observation02'].encode(),observation02['sha256'].encode()),
            (b'size_bytes=13940',b'size_bytes=%d' % observation02['size_bytes']),
            (b'SITE_COUNTS=(27225,2074,1304701872)',counts),
            (b'min_available_ram_bytes=2048*MiB',b'min_available_ram_bytes=128*MiB')])
    return dict(root=root,site=site,inputs=inputs,observation02=observation02,inventory=inventory)


def load(path,name):
    import importlib.util
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def run(command,root,timeout=180):
    env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    process=subprocess.Popen(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:stdout,stderr=process.communicate(timeout=timeout)
    except BaseException:
        os.killpg(process.pid,signal.SIGKILL);process.communicate();raise
    return process.returncode,stdout,stderr


def characterize(project):
    """Freeze, observe and independently audit one authored characterization-04."""
    root=project['root'];parent=load(root/CHARACTERIZATION,'authored_characterization04_parent_'+str(id(project)))
    config=parent.configuration(parent.source_rows());raw=pretty(config)
    path=root/'docs/authored/characterization-04-configuration.json';write(root,'docs/authored/characterization-04-configuration.json',raw)
    code,stdout,stderr=run([PYTHON,'-I','-S','-B',str(root/'scripts/observe_puck_cpu_episode_characterization.py'),
        '--configuration',str(path),'--sha256',sha(raw)],root,480)
    transport=root/(parent.OUTPUT+'-external-cli-transport.json')
    return dict(project,configuration=path,configuration_raw=raw,parent=parent,observer=(code,stdout,stderr),
                transport=transport)


def audit_characterization(characterized,output_name='docs/authored/outcome-audit-04.json'):
    root=characterized['root'];transport=characterized['transport'];output=root/output_name
    output.parent.mkdir(parents=True,exist_ok=True)
    code,stdout,stderr=run([PYTHON,'-I','-S','-B',str(root/CHAR_AUDITOR),'--configuration',str(characterized['configuration']),
        '--sha256',sha(characterized['configuration_raw']),'--transport',str(transport),
        '--transport-sha256',sha(transport.read_bytes()),'--output',str(output)],root,330)
    return code,(json.loads(output.read_bytes()) if output.exists() else None),stdout,stderr,output
