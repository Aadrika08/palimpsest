"""AUTHORED preparation04: the held episode closure prepares once; no installed vendors.

The authored project replaces the characterization02 bindings with authored
characterization-04 documents, an authored native metadata v6 built from real
host rows (the nine baseline paths, the startup locale/gconv leaves and the Mesa
EGL vendor library) and an episode candidate 02. The real CLI stages it into a
new private tmpfs stage and copies the episode worker closure, including the two
empty upstream __init__ files, into its one source capsule.
"""
import json
import os
from pathlib import Path
import secrets
import shutil

import pytest

from test_puck_cpu_held_parent_integration import AUTHORED, ROOT, digest, project, run_cli, write

OUTPUT='runs/puck-cpu-held-preparation-04'
NATIVE06=json.loads((ROOT/'docs/plans/puck-cpu-characterization-native-metadata-06.json').read_bytes())
LIBRARIES=('ld-linux-x86-64.so.2','libc.so.6','libdl.so.2','libm.so.6','libpthread.so.0','librt.so.1','libutil.so.1')
LEAVES=['/usr/lib/gconv/gconv-modules.cache','/usr/lib/libEGL_mesa.so.0.0.0','/usr/lib/locale/C.utf8/LC_CTYPE',
        '/usr/lib/locale/locale-archive']
# The real 171 MB LLVM leaf exceeds the legacy 64 MiB builder hashing cap.
LLVM='/usr/lib/libLLVM.so.22.1'
EMPTY=('upstream/fly-gym/core/__init__.py','upstream/fly-gym/environment/__init__.py')


def episode_project(tmp_path):
    root,api,inputs,_=project(tmp_path)
    for name in api.PREPARATION04_SOURCES:
        if (root/name).exists():continue
        source=ROOT/name
        raw=b'' if name in EMPTY else source.read_bytes() if source.is_file() else ('# AUTHORED '+name+'\n').encode()
        write(root,name,raw)
    rows={r['path']:r for r in NATIVE06['native_files']}
    nine=sorted(['/etc/ld.so.cache']+['/usr/lib/'+name for name in LIBRARIES])
    baseline=json.loads((root/inputs['baseline']['path']).read_bytes())
    def put(role,value,name=None):
        inputs[role]=write(root,name or 'docs/authored/episode-'+role+'.json',value)
    put('native',dict(kind='puck-cpu-characterization-native-metadata-v6',status='COMPLETE',
        root_scope='installed_shared_objects_interpreter_and_declared_dynamic_leaves',errors=[],oversized_native_files=[],
        required_missing_names=[],native_files=[rows[p] for p in sorted(nine+LEAVES+[LLVM])],
        aliases=sorted(baseline['host_path_aliases']+[['/usr/lib/libEGL_mesa.so.0','libEGL_mesa.so.0.0.0']]),
        dynamic_leaves=LEAVES,egl_vendor=NATIVE06['egl_vendor'],provenance=dict(authored_scope=AUTHORED),
        limitations=[AUTHORED]))
    linked=('inventory','layout','native','baseline','accepted_result','accepted_snapshot','accepted_audit',
            'accepted_configuration','accepted_index')
    put('observation_configuration',dict(kind='puck-cpu-runtime-characterization-v3',version=3,
        roles={('native_metadata' if r=='native' else r):inputs[r]['path'] for r in linked},
        inputs=[inputs[r] for r in linked],expected_versions=dict(api.EPISODE_VERSIONS),authored_scope=AUTHORED))
    images=[dict(path=p) for p in sorted(nine+[api.PYTHON]+[p for p in LEAVES if 'EGL' not in p])]
    for role,phase in (('observation_report','source'),('observation_replay_report','replay')):
        put(role,dict(api.CLAIMS,kind='puck-episode-characterization-result-v1',version=1,status='observed',phase=phase,
            versions=dict(api.EPISODE_VERSIONS),expected_versions=dict(api.EPISODE_VERSIONS),
            baseline_maps=dict(images=images),authored_scope=AUTHORED))
    put('observation_result',dict(api.CLAIMS,kind='puck-cpu-characterization-outcome-v3',version=3,status='observed',
        versions=dict(api.EPISODE_VERSIONS),configuration_sha256=inputs['observation_configuration']['sha256'],
        source_report_sha256=inputs['observation_report']['sha256'],
        replay_report_sha256=inputs['observation_replay_report']['sha256'],authored_scope=AUTHORED))
    shas={role:inputs[role]['sha256'] for role in ('observation_configuration','observation_result','observation_report','observation_replay_report')}
    put('observation_audit',dict(kind='cpu-episode-characterization-outcome-audit-v1',status='PASS',authored_scope=AUTHORED,
        verified=dict(configuration_sha256=shas['observation_configuration'],result_sha256=shas['observation_result'],
            source_report_sha256=shas['observation_report'],replay_report_sha256=shas['observation_replay_report'])))
    put('observation_index',dict(kind='cpu-episode-characterization-evidence-index-v1',authored_scope=AUTHORED,
        entries=[dict(inputs[role],path=path) for role,path in api.EPISODE_OBSERVATION_PATHS.items()]))
    candidate=json.loads((root/inputs['candidate']['path']).read_bytes())
    for key in ('observation_report_sha256','configuration_sha256'):candidate.pop(key)
    candidate.update(kind='puck-cpu-episode-import-profile-candidate-v2',version=2,expected_versions=dict(api.EPISODE_VERSIONS),
        characterization_configuration_sha256=shas['observation_configuration'],
        observation_reports=dict(source=shas['observation_report'],replay=shas['observation_replay_report']),
        observation_result_sha256=shas['observation_result'],outcome_audit_sha256=inputs['observation_audit']['sha256'],
        native_metadata_sha256=inputs['native']['sha256'])
    put('candidate',candidate)
    sources=[dict(path=name,size_bytes=len(raw),sha256=digest(raw))
             for name in api.PREPARATION04_SOURCES for raw in ((root/name).read_bytes(),)]
    return root,api,inputs,sources


@pytest.fixture
def stage():
    path=Path('/tmp/palimpsest-puck-cpu-held-04-authored-'+secrets.token_hex(4))
    yield path
    if path.exists():
        for parent,directories,_ in os.walk(path):
            for name in directories:os.chmod(os.path.join(parent,name),0o700)
        shutil.rmtree(path)


def test_authored_preparation04_stages_the_episode_closure_once(tmp_path,stage):
    root,api,inputs,sources=episode_project(tmp_path)
    config=api.configuration_template(phase='prepare',root=str(root),stage_parent=str(stage),sources=sources,
        inputs=inputs,negative_imports=['org'])
    config.update(kind='puck-cpu-held-runtime-allocation-v15',version=15,allocation_id=15,
                  expected_versions=dict(api.EPISODE_VERSIONS))
    code,stdout,stderr=run_cli(root,api,'prepare04',config)
    result_path=root/OUTPUT/'result.json'
    prepared=json.loads(result_path.read_bytes()) if result_path.exists() else None
    assert code==0,(code,stdout,stderr,prepared)
    assert stdout==result_path.read_bytes() and prepared['status']=='prepared' and prepared['allocation_id']==15
    assert prepared['kind']=='puck-cpu-held-runtime-outcome-v15' and prepared['stage_parent']==str(stage)
    staged=stage/'inputs'
    assert sorted(p.name for p in staged.iterdir())==['root-0000','root-0001','root-0002','root-0003']
    for leaf in LEAVES+[LLVM]:assert (staged/'root-0001'/leaf[len('/usr/'):]).is_file()
    capsule=root/OUTPUT/'parent-source'
    assert not (root/OUTPUT/'worker-source').exists()
    assert all((capsule/name).read_bytes()==(root/name).read_bytes() for name in api.PREPARATION04_SOURCES)
    assert all((capsule/name).stat().st_size==0 for name in EMPTY)
    assert (root/OUTPUT/'control/candidate.json').read_bytes()==(root/inputs['candidate']['path']).read_bytes()
    dependencies=json.loads((root/OUTPUT/'payload/dependencies.json').read_bytes())
    assert dependencies['import_profile']==json.loads((root/inputs['candidate']['path']).read_bytes())['import_profile']
    code,_,_=run_cli(root,api,'prepare04-again',config)
    assert code!=0 and json.loads(result_path.read_bytes())==prepared
