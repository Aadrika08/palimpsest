"""Real CPU-parent CLI seams using AUTHORED modules, never installed vendors.

Receipt/audit/index documents below are self-consistent test inputs, not claims
of an independent audit or acceptance of the actual CPU installation.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import secrets
import shutil
import signal
import subprocess
import time

import pytest


ROOT=Path(__file__).resolve().parents[1]
PARENT='scripts/qualify_puck_cpu_held_runtime.py'
BASELINE='docs/plans/puck-python-louvain-host-baseline-v1.json'
NATIVE='docs/plans/puck-cpu-characterization-native-metadata-05.json'
AUTHORED='AUTHORED fixture only; no real package acceptance or independent audit'
LIBRARIES=('ld-linux-x86-64.so.2','libc.so.6','libdl.so.2','libm.so.6',
           'libpthread.so.0','librt.so.1','libutil.so.1')


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def write(root,name,value):
    raw=value if type(value) is bytes else canonical(value)
    path=root/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);path.write_bytes(raw)
    return dict(path=name,size_bytes=len(raw),sha256=digest(raw))


def project(tmp_path,*,rocm_probe=False,binding_failure=False,published_export=False,autograd_publication=False,caught_optional_import=False,pillow_origins=False,stock_absence_probe=False,worker_delay_seconds=None):
    project=tmp_path/'authored-project';project.mkdir(mode=0o700)
    current=load(ROOT/PARENT,'cpu_authored_current_parent')
    marker=b'min_available_ram_bytes=(4096 if phase==\'prepare\' else 2048)*MiB'
    replacement=b'min_available_ram_bytes=128*MiB'
    for name in current.SOURCES:
        raw=(ROOT/name).read_bytes()
        if name==PARENT:
            # The real legacy auditor labels these inert fixtures explicitly.
            # Adapt only this authenticated test clone; production acceptance
            # continues to require the ordinary actual-data scope.
            scope=b"audit.get('evidence_scope')!='ordinary CPU held allocation only'"
            authored_scope=b"audit.get('evidence_scope')!='AUTHORED fixture only'"
            changes=[(marker,replacement,1),(scope,authored_scope,1)]
            roster=b"PREPARATION_NEGATIVE_IMPORTS=['numpy._distributor_init_local','org']"
            authored_roster=b"PREPARATION_NEGATIVE_IMPORTS=['org']"
            if roster in raw:changes.append((roster,authored_roster,1))
            admission=b'def resource_admission(config):\n'
            synthetic_admission=(
                b'def _authored_supervised(bounds,*args,**kwargs):\n'
                b'    # Synthetic capacity is AUTHORED fixture data, not production guard qualification.\n'
                b"    assert ROOT.name=='authored-project', 'Synthetic capacity requires the authored project'\n"
                b'    original=bounds.shutil.disk_usage\n'
                b'    try:\n'
                b'        bounds.shutil.disk_usage=lambda path: original(path)._replace(free=8*1024**3)\n'
                b'        return bounds.supervised(*args,**kwargs)\n'
                b'    finally:bounds.shutil.disk_usage=original\n\n\n'+admission+
                b'    # Synthetic capacity is AUTHORED fixture data, never a host measurement.\n'
                b"    assert ROOT.name=='authored-project', 'Synthetic capacity requires the authored project'\n"
                b'    authored_disk_free_bytes=authored_tmpfs_free_bytes=8*1024**3\n')
            changes.extend([(admission,synthetic_admission,1),
                (b'observed=bounds.supervised(command,',b'observed=_authored_supervised(bounds,command,',1),
                (b'shutil.disk_usage(ROOT).free',b'(authored_disk_free_bytes)',2),
                (b'shutil.disk_usage(parent).free',b'(authored_tmpfs_free_bytes)',2)])
            changed=raw
            for before,after,count in changes:
                assert changed.count(before)==count
                changed=changed.replace(before,after)
            restored=changed
            for before,after,_ in reversed(changes):restored=restored.replace(after,before)
            assert restored==raw
            raw=changed
        write(project,name,raw)
    api=load(project/PARENT,'cpu_authored_cloned_parent')
    assert all(v['min_available_ram_bytes']==128*1024**2 for v in api.LIMITS.values())
    for phase in current.LIMITS:
        expected=dict(current.LIMITS[phase],min_available_ram_bytes=128*1024**2)
        assert api.LIMITS[phase]==expected
    inputs={}
    def document(role,value):
        inputs[role]=write(project,'docs/authored/'+role+'.json',dict(value,authored_scope=AUTHORED))
    site=project/api.SITE;site.mkdir(mode=0o700,parents=True)
    entries=[];modules=[];wheels=[]
    for name,version in api.VERSIONS.items():
        source=("__version__ = "+repr(version)+"\n").encode()
        package=(rocm_probe or autograd_publication) and name=='torch'
        if rocm_probe and name=='torch':
            source+=b'try:\n    from . import _rocm_init\nexcept ImportError:\n    OPTIONAL_ROCM_ABSENT = True\n'
        if published_export and name=='torch':
            source+=(b'import sys, types\n'
                     b'def answer():\n    return 47\n'
                     b"authored_child = types.ModuleType('torch.authored_publication')\n"
                     b'authored_child.__file__ = __file__\n'
                     b'authored_child.answer = answer\n'
                     b"sys.modules['torch.authored_publication'] = authored_child\n"
                     b'import _authored_cpu_generated\n')
        if autograd_publication and name=='torch':
            source+=b'import torch._C\nimport torch.autograd\nimport torch.distributed\nimport torch.distributed.autograd\nimport torch.distributed.rpc\n'
        if caught_optional_import and name=='torch':
            assert autograd_publication, 'The caught optional seam follows all four authored creators'
            source+=b'try:\n    import pynvml\nexcept ImportError:\n    AUTHORED_OPTIONAL_PYNVML_ABSENT = True\n'
        if pillow_origins and name=='torchvision':source+=b'import PIL\n'
        if worker_delay_seconds and name=='mujoco':
            # Scaled clock tests: a held import that outlasts one epoch's clock.
            source+=b'import time\ntime.sleep('+str(worker_delay_seconds).encode()+b')\n'
        if stock_absence_probe and name=='torchvision':
            # Bare trace_rules-style probes and a caught import of declared names.
            source+=(b'import importlib.util\n'
                     b"assert [importlib.util.find_spec(n) for n in ('tabulate','networkx','pandas','sklearn')]==[None]*4\n"
                     b'try:\n    import backports_abc\nexcept ImportError:\n    AUTHORED_OPTIONAL_BACKPORTS_ABC_ABSENT = True\n')
        module_path=name+'/__init__.py' if package else name+'.py'
        write(site,module_path,source)
        entries.append(dict(path=module_path,size_bytes=len(source),sha256=digest(source)))
        modules.append(dict(name=name,root_index=0,path=module_path,kind='python',is_package=package))
        metadata=(f'Name: {name}\nVersion: {version}\n\n').encode()
        path=name+'-'+version+'.dist-info/METADATA';write(site,path,metadata)
        entries.append(dict(path=path,size_bytes=len(metadata),sha256=digest(metadata)))
        wheels.append(dict(name=name,version=version,metadata_path=path,metadata_sha256=digest(metadata)))
    if autograd_publication:
        import importlib.machinery
        import sysconfig
        from test_puck_cpu_held_amendment05 import PUBLICATION_EXPORTS
        # Keep the old fixture switch, now exercising all four declarations.
        # Every creator crosses a distinct fresh physical import while its
        # published module is empty, then fills the exact roster before close.
        for row in PUBLICATION_EXPORTS:
            producer=row['producer'];name=row['name'];attribute=name.rsplit('.',1)[1]
            helper='_authored_publication_gate_'+attribute.lstrip('_')
            source=(b'import sys, types, torch\n'
                    b'def authored_delegate():\n    return 47\n'+
                    ('torch._C.'+attribute+' = types.ModuleType('+repr(name)+')\n').encode()+
                    ('torch._C.'+attribute+'.__file__ = __file__\n').encode()+
                    ('sys.modules['+repr(name)+'] = torch._C.'+attribute+'\n').encode()+
                    ('import '+helper+'\n').encode()+
                    ('for name in '+repr(row['delegate_attributes'])+':\n    setattr(torch._C.'+attribute+', name, authored_delegate)\n').encode())
            path=producer.replace('.','/')+'/__init__.py';write(site,path,source)
            entries.append(dict(path=path,size_bytes=len(source),sha256=digest(source)))
            modules.append(dict(name=producer,root_index=0,path=path,kind='python',is_package=True))
            helper_source=b'AUTHORED_PUBLICATION_GATE = True\n'
            path=helper+'.py';write(site,path,helper_source)
            entries.append(dict(path=path,size_bytes=len(helper_source),sha256=digest(helper_source)))
            modules.append(dict(name=helper,root_index=0,path=path,kind='python',is_package=False))
        extension='torch/_C'+importlib.machinery.EXTENSION_SUFFIXES[0]
        native=project/'authored-autograd.c'
        native.write_text('#include <Python.h>\n'
            'static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"torch._C",NULL,-1,NULL};\n'
            'PyMODINIT_FUNC PyInit__C(void){return PyModule_Create(&mod);}\n')
        subprocess.run(['cc','-shared','-fPIC','-I'+sysconfig.get_paths()['include'],str(native),
                        '-o',str(site/extension)],check=True,capture_output=True,timeout=15)
        raw=(site/extension).read_bytes()
        entries.append(dict(path=extension,size_bytes=len(raw),sha256=digest(raw)))
        modules.append(dict(name='torch._C',root_index=0,path=extension,kind='extension',is_package=False))
    if pillow_origins:
        from test_puck_pillow_native_origins import authored_pillow_images
        images=authored_pillow_images(site,project/'authored-pillow-build',python_extensions=True)
        for image in images:
            path=str(image.relative_to(site));raw=image.read_bytes()
            entries.append(dict(path=path,size_bytes=len(raw),sha256=digest(raw)))
            if path.startswith('PIL/'):
                modules.append(dict(name='PIL.'+image.name.split('.',1)[0],root_index=0,
                    path=path,kind='extension',is_package=False))
        source=b'from . import _imaging\nfrom . import _imagingft\n'
        write(site,'PIL/__init__.py',source)
        entries.append(dict(path='PIL/__init__.py',size_bytes=len(source),sha256=digest(source)))
        modules.append(dict(name='PIL',root_index=0,path='PIL/__init__.py',kind='python',is_package=True))
    inert=b'inert authored bytecode data, never executed'
    write(site,'inert.pyc',inert);entries.append(dict(path='inert.pyc',size_bytes=len(inert),sha256=digest(inert)))
    (site/'empty/nested').mkdir(mode=0o700,parents=True)
    directories=sorted([r['metadata_path'].split('/')[0] for r in wheels]+['empty','empty/nested']+
        (['torch'] if rocm_probe or autograd_publication else [])+
        (['torch/autograd','torch/distributed','torch/distributed/autograd','torch/distributed/rpc'] if autograd_publication else [])+
        (['PIL','pillow.libs'] if pillow_origins else []))
    inventory=dict(kind='puck-cpu-installed-files-v1',entries=sorted(entries,key=lambda r:r['path']),
                   file_count=len(entries),directory_count=len(directories),total_bytes=sum(r['size_bytes'] for r in entries))
    # Inventory has an exact schema, so its authorship label lives in this test.
    inputs['inventory']=write(project,'docs/authored/inventory.json',inventory)
    collisions=dict(case_sensitive_linux_paths=True,destination_directory_coownership_is_allowed=True,
        **{k:[] for k in ('destination_regular_directory_path_conflicts',
            'destination_regular_path_collisions_including_entrypoint_wrappers','source_file_ancestor_conflicts',
            'source_regular_directory_path_conflicts','source_regular_path_collisions')})
    document('layout',dict(kind='palimpsest-cpu-wheel-install-layout-v1',version=1,
        predicted_destination_directories=directories,predicted_empty_destination_directories=['empty/nested'],
        collisions=collisions,wheels=wheels))
    baseline_raw=(ROOT/BASELINE).read_bytes();baseline=json.loads(baseline_raw)
    # Authored fixtures bind current host files; historical qualification pins stay frozen.
    baseline_api=load(ROOT/'scripts/build_puck_python_louvain.py','cpu_authored_baseline')
    prefix=baseline_api.prefix_inventory(Path(baseline['python_prefix']),time.monotonic()+60)
    baseline.update(prefix,regular_file_count=len(prefix['files']),
        symlink_count=len(prefix['symlinks']),
        regular_file_bytes=sum(row[1] for row in prefix['files']))
    for row in baseline['external_libraries']:
        if row.get('load_paths'):
            row['realpath']=str(Path(row['load_paths'][0]).resolve(strict=True))
    for row in [*baseline['external_libraries'], baseline['bwrap_executable']]:
        if row is not None:
            payload=Path(row.get('realpath',row.get('path'))).read_bytes()
            row.update(size=len(payload),sha256=digest(payload))
    inputs['baseline']=write(project,'docs/authored/baseline.json',baseline)
    native05=json.loads((ROOT/NATIVE).read_bytes())
    selected=sorted(['/etc/ld.so.cache']+['/usr/lib/'+name for name in LIBRARIES])
    native_rows={r['path']:r for r in native05['native_files']}
    for path in selected:
        payload=Path(path).read_bytes()
        native_rows[path]=dict(native_rows[path],size_bytes=len(payload),sha256=digest(payload))
    document('native',dict(kind='puck-cpu-characterization-native-metadata-v5',status='COMPLETE',
        root_scope='installed_shared_objects_and_interpreter',errors=[],oversized_native_files=[],required_missing_names=[],
        native_files=[native_rows[p] for p in selected],aliases=copy.deepcopy(baseline['host_path_aliases'])))
    helper=b'AUTHORED_PROSPECTIVE_HELPER = True\n';helper_name='_authored_cpu_generated.py'
    inputs['generated']=write(project,'docs/authored/generated/'+helper_name,helper)
    modules.append(dict(name='_authored_cpu_generated',root_index=3,path=helper_name,kind='python',is_package=False))
    document('accepted_configuration',dict(kind='cpu-retained-installation-admission-v2',version=2,inputs=[inputs['layout']]))
    document('accepted_snapshot',dict(kind='cpu-retained-installation-snapshot-v2',site_root=str(site),
        configuration_sha256=inputs['accepted_configuration']['sha256']))
    document('accepted_result',dict(kind='cpu-retained-installation-admission-result-v2',status='PASS',site_root=str(site),
        configuration_sha256=inputs['accepted_configuration']['sha256'],snapshot_sha256=inputs['accepted_snapshot']['sha256'],
        file_count=inventory['file_count'],directory_count=inventory['directory_count'],regular_file_bytes=inventory['total_bytes'],
        claims=dict(package_preparation_accepted=True,runtime_qualified=False,numerical_imports_executed=False,
                    study_authorized=False,collection_authorized=False)))
    document('accepted_audit',dict(status='PASS',package_preparation_accepted=True,
        verified=dict(configuration_sha256=inputs['accepted_configuration']['sha256'])))
    accepted_names=dict(inventory='raw/inventory.json',accepted_result='raw/result.json',
        accepted_snapshot='raw/snapshot.json',accepted_audit='acceptance-audit-03.json',accepted_configuration='raw/configuration.json')
    document('accepted_index',dict(kind='retained-admission-02-evidence-index-v1',
        entries=[dict(inputs[role],path=path) for role,path in accepted_names.items()]))
    linked_roles=('inventory','layout','native','baseline','accepted_result','accepted_snapshot',
                  'accepted_audit','accepted_configuration','accepted_index')
    document('observation_configuration',dict(kind='puck-cpu-runtime-characterization-v1',version=1,
        roles={('native_metadata' if role=='native' else role):inputs[role]['path'] for role in linked_roles},
        inputs=[inputs[role] for role in linked_roles],expected_versions=dict(api.VERSIONS)))
    baseline_images=sorted([*selected,api.PYTHON])
    document('observation_report',dict(api.CLAIMS,kind='puck-runtime-import-characterization-result-v3',version=3,
        status='observed',versions=dict(api.VERSIONS),imports=[dict(name=n,version=v) for n,v in api.VERSIONS.items()],
        baseline_maps=dict(images=[dict(path=p) for p in baseline_images])))
    document('observation_result',dict(api.CLAIMS,status='observed',versions=dict(api.VERSIONS),
        report_sha256=inputs['observation_report']['sha256'],configuration_sha256=inputs['observation_configuration']['sha256']))
    document('observation_audit',dict(status='PASS',ordinary_imports_observed=True,
        verified=dict(result_sha256=inputs['observation_result']['sha256'],report_sha256=inputs['observation_report']['sha256'])))
    observation_names=dict(observation_configuration='frozen-configuration.json',observation_report='raw/payload/imports.json',
                           observation_result='raw/result.json',observation_audit='outcome-audit-02.json')
    document('observation_index',dict(kind='cpu-characterization-evidence-index-v2',
        entries=[dict(inputs[role],path=path) for role,path in observation_names.items()]))
    exports=([dict(name='torch._authored_missing',producer='torch',phase='module_exec',
                   attributes=['_authored_missing'],class_binding=None)] if binding_failure else [])
    if published_export:
        exports.append(dict(name='torch.authored_publication',producer='torch',phase='module_exec_publish',
                            attributes=['authored_child'],class_binding=None,delegate_attributes=['answer']))
    if autograd_publication:
        exports.extend(dict(name=row['name'],producer='torch._C',phase='native_create',
                            attributes=[row['name'].rsplit('.',1)[1]],class_binding=None)
                       for row in PUBLICATION_EXPORTS)
    document('candidate',dict(kind='puck-cpu-observed-import-profile-candidate-v1',version=1,
        expected_versions=dict(api.VERSIONS),module_paths=sorted(modules,key=lambda r:r['name']),namespaces=[],
        import_profile=dict(kind='puck-producer-import-profile-v2',version=2,exports=exports,module_changes=[],native_origins=[],native_cache=[]),
        additional_package_inputs=[dict(root='docs/authored/generated',files=[dict(inputs['generated'],path=helper_name)])],
        retained_inventory_sha256=inputs['inventory']['sha256'],observation_report_sha256=inputs['observation_report']['sha256'],
        configuration_sha256=inputs['observation_configuration']['sha256'],outcome_audit_sha256=inputs['observation_audit']['sha256'],
        native_phase_qualified=False,held_runtime_qualified=False,native_authorized=False,
        collection_authorized=False,study_authorized=False,executable=False,qualification_claims=[]))
    assert set(inputs)==set(api.INPUT_ROLES)
    sources=[dict(path=name,size_bytes=len((project/name).read_bytes()),sha256=digest((project/name).read_bytes())) for name in api.SOURCES]
    return project,api,inputs,sources


def run_cli(root,api,phase,config):
    raw=canonical(config);configuration=root/('authored-'+phase+'-configuration.json');configuration.write_bytes(raw)
    command=[api.PYTHON,'-I','-S','-B',str(root/PARENT),'--configuration',str(configuration),'--sha256',digest(raw)]
    env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    started=time.monotonic()
    process=subprocess.Popen(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:
        stdout,stderr=process.communicate(timeout=60)
    except BaseException:
        os.killpg(process.pid,signal.SIGKILL);process.communicate();raise
    elapsed=time.monotonic()-started
    if process.returncode:
        diagnostic=dict(phase=phase,returncode=process.returncode)
        if stderr:diagnostic['stderr_tail']=stderr[-2048:].decode('utf-8','replace')
        try:
            if len(stdout)>64*1024:raise ValueError('Parent stdout exceeds diagnostic bound')
            parent=json.loads(stdout)
            diagnostic['parent']={key:parent[key] for key in ('kind','status','error_type','error','elapsed_seconds') if key in parent}
        except (ValueError,TypeError) as error:
            diagnostic['parent_decode_error']=str(error)
        try:
            output=root/(api.allocation_output(config) if hasattr(api,'allocation_output') else api.OUTPUTS[config['phase']])
            with (output/'supervision.json').open('rb') as stream:raw_supervision=stream.read(64*1024+1)
            if len(raw_supervision)>64*1024:raise ValueError('Supervision exceeds diagnostic bound')
            observed=json.loads(raw_supervision)
            diagnostic['supervision']={key:observed[key] for key in ('status','failure','returncode','pid','matching_survivors','sampled_peak_rss_bytes') if key in observed}
        except (OSError,ValueError,TypeError,KeyError) as error:
            diagnostic['supervision_read_error']=str(error)
        print('AUTHORED CLI failure diagnostic:',json.dumps(diagnostic,sort_keys=True))
    if b'CPU held-runtime resource admission failed' in stderr:
        parent=Path(config['stage_parent']).parent
        available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
        print('AUTHORED post-failure resource sample:',dict(
            nofile=resource.getrlimit(resource.RLIMIT_NOFILE),mem_available_bytes=available,
            disk_free_bytes=shutil.disk_usage(root).free,tmpfs_free_bytes=shutil.disk_usage(parent).free,
            limits=config['limits']))
    channels={}
    for name,payload in (('stdout',stdout),('stderr',stderr)):
        leaf='authored-'+phase+'-cli.'+name
        (root/leaf).write_bytes(payload)
        channels[name]=dict(path=leaf,size_bytes=len(payload),sha256=digest(payload))
    receipt=dict(kind='authored-cpu-parent-cli-transport-v1',authored_scope=AUTHORED,
        command=command,configuration_sha256=digest(raw),observed_returncode=process.returncode,
        elapsed_seconds=elapsed,**channels)
    receipt_raw=canonical(receipt);assert len(receipt_raw)<=64*1024
    (root/('authored-'+phase+'-transport.json')).write_bytes(receipt_raw)
    return process.returncode,stdout,stderr


def test_authored_admission_uses_synthetic_capacity_only_in_its_bound_clone(tmp_path, monkeypatch):
    original=(ROOT/PARENT).read_bytes()
    root,api,_,sources=project(tmp_path)
    assert (ROOT/PARENT).read_bytes()==original
    assert next(row for row in sources if row['path']==PARENT)['sha256']==digest((root/PARENT).read_bytes())
    monkeypatch.setattr(api.shutil,'disk_usage',lambda path: pytest.fail('Authored admission sampled host capacity'))
    config=dict(stage_parent='/tmp/authored-capacity-probe',limits=api.LIMITS['prepare'])
    admission=api.resource_admission(config)
    assert admission['disk_available_bytes']==admission['tmpfs_available_bytes']==8*1024**3
    monkeypatch.setattr(api,'ROOT',tmp_path/'foreign-project')
    with pytest.raises(AssertionError,match='Synthetic capacity requires the authored project'):
        api.resource_admission(config)


def test_authored_monitor_preserves_the_real_floor_and_restores_its_sampler(tmp_path, monkeypatch):
    root,api,_,_=project(tmp_path)
    bounds=load(ROOT/'src/palimpsest/bounded_qualification.py','authored_capacity_real_monitor')
    real_supervised=bounds.supervised
    usage=shutil.disk_usage(tmp_path)._replace(free=3*1024**3)
    low_capacity=lambda path: usage
    monkeypatch.setattr(bounds.shutil,'disk_usage',low_capacity)
    command=[api.PYTHON,'-B','-c','print("AUTHORED monitor only")']
    arguments=dict(cwd=tmp_path,normal_deadline=time.monotonic()+3,hard_deadline=time.monotonic()+4,
        rss_bytes=256*1024**2,output_bytes=1024**2,min_free_bytes=4*1024**3,log_mode='direct')
    low=tmp_path/'real-floor';low.mkdir()
    refused=real_supervised(command,low,**arguments)
    assert refused['status']=='failed' and refused['failure']=='free-space floor' and refused['pid'] is None
    authored=tmp_path/'authored-capacity';authored.mkdir()
    observed=api._authored_supervised(bounds,command,authored,**arguments)
    assert observed['status']=='completed' and observed['returncode']==0 and observed['failure'] is None
    assert bounds.supervised is real_supervised and bounds.shutil.disk_usage is low_capacity
    with pytest.raises(ValueError,match='Qualification process scope is invalid'):
        api._authored_supervised(bounds,command,authored,**dict(arguments,process_scope='invalid'))
    assert bounds.shutil.disk_usage is low_capacity
    monkeypatch.setattr(api,'ROOT',tmp_path/'foreign-project')
    with pytest.raises(AssertionError,match='Synthetic capacity requires the authored project'):
        api._authored_supervised(bounds,command,authored,**arguments)
    assert bounds.shutil.disk_usage is low_capacity


def test_actual_authored_prepare_then_separate_held_four_import_cli(tmp_path):
    root,api,inputs,sources=project(tmp_path)
    stage=Path('/tmp')/('palimpsest-puck-cpu-held-authored-'+secrets.token_hex(12))
    assert not stage.exists()
    try:
        config=api.configuration_template(phase='prepare',root=str(root),stage_parent=str(stage),
            sources=sources,inputs=inputs,negative_imports=['org'])
        code,stdout,stderr=run_cli(root,api,'prepare',config)
        result_path=root/api.OUTPUTS['prepare']/'result.json'
        retained=result_path.read_bytes() if result_path.exists() else b''
        assert code==0,(code,stdout,stderr,retained)
        prepare_code=code
        prep=json.loads(retained);assert json.loads(stdout)==prep and prep['status']=='prepared'
        assert prep['held_four_imports_observed'] is False
        dependencies=json.loads((root/api.OUTPUTS['prepare']/'payload/dependencies.json').read_bytes())
        assert [len(r['files']) for r in dependencies['roots']]==[9,7,1,1]
        assert (stage/'inputs/root-0000/empty/nested').is_dir()
        assert (stage/'inputs/root-0000/inert.pyc').read_bytes()==b'inert authored bytecode data, never executed'
        identities=[(stage/'inputs'/('root-'+str(i).zfill(4))).stat() for i in range(4)]
        preparation=dict(path=str(result_path.relative_to(root)),size_bytes=len(retained),sha256=digest(retained))
        qualify=api.configuration_template(phase='qualify',root=str(root),stage_parent=str(stage),
            sources=sources,inputs=inputs,negative_imports=['org'],preparation=preparation)
        code,stdout,stderr=run_cli(root,api,'qualify',qualify)
        final_path=root/api.OUTPUTS['qualify']/'result.json'
        final_raw=final_path.read_bytes() if final_path.exists() else b''
        assert code==0,(code,stdout,stderr,final_raw)
        qualify_code=code;qualify_stdout=stdout;qualify_stderr=stderr
        final=json.loads(final_raw);assert json.loads(stdout)==final and final['status']=='imports_completed'
        assert final['held_four_imports_observed'] is True
        worker=json.loads((root/api.OUTPUTS['qualify']/'logs/stdout.log').read_bytes())
        assert [(r['name'],r['version']) for r in worker['entry_result']['imports']]==list(api.VERSIONS.items())
        assert worker['dependencies']['root_count']==4 and worker['dependencies']['file_count']==18
        for outcome in (prep,final):
            assert all(outcome[k] is False for k in api.CLAIMS if k!='qualification_claims')
            assert outcome['qualification_claims']==[] and outcome['elapsed_seconds']<180
            assert outcome['closure']['active_children']==outcome['closure']['active_non_main_threads']==[]
            assert outcome['closure']['fd_count_before']==outcome['closure']['fd_count_after']
        for i,before in enumerate(identities):
            after=(stage/'inputs'/('root-'+str(i).zfill(4))).stat()
            assert (before.st_dev,before.st_ino)==(after.st_dev,after.st_ino)
        code,_,stderr=run_cli(root,api,'qualify-rerun',qualify)
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert final_path.read_bytes()==final_raw
        assert (root/'authored-qualify-cli.stdout').read_bytes()==qualify_stdout
        assert (root/'authored-qualify-cli.stderr').read_bytes()==qualify_stderr
        for label,observed in (('prepare',prepare_code),('qualify',qualify_code),('qualify-rerun',code)):
            path=root/('authored-'+label+'-transport.json')
            assert path.is_file(),'Observed external CLI transport receipt is missing: '+label
            raw=path.read_bytes();assert len(raw)<=64*1024
            transport=json.loads(raw)
            assert transport['kind']=='authored-cpu-parent-cli-transport-v1'
            assert transport['observed_returncode']==observed
            assert transport['authored_scope']==AUTHORED
            assert 0<transport['elapsed_seconds']<60
            configuration=root/('authored-'+label+'-configuration.json')
            assert transport['configuration_sha256']==digest(configuration.read_bytes())
            assert transport['command']==[api.PYTHON,'-I','-S','-B',str(root/PARENT),
                '--configuration',str(configuration),'--sha256',transport['configuration_sha256']]
            for channel in ('stdout','stderr'):
                name='authored-'+label+'-cli.'+channel;payload=(root/name).read_bytes()
                assert transport[channel]==dict(path=name,size_bytes=len(payload),sha256=digest(payload))
        print(dict(authored_prepare_status=prep['status'],authored_qualify_status=final['status'],
                   prepare_seconds=prep['elapsed_seconds'],qualify_seconds=final['elapsed_seconds'],
                   rerun_refused=True,files=18,actual_vendor_imports=False))
    finally:
        if stage.exists():
            assert stage.is_dir() and not stage.is_symlink()
            shutil.rmtree(stage)
