"""Separately frozen CPU preparation and held four-import qualification.

The parent is trusted after its source freeze. A passing terminal observes held
imports only; it grants no numerical, renderer, collection or study authority.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import stat
import sys
import threading
import tempfile
import time
import types

ROOT=Path(__file__).resolve().parents[1]
MiB=1024**2
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
INTERPRETER=dict(path=PYTHON,size_bytes=21662864,sha256='572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a')
BOOTSTRAP='scripts/puck_worker_bootstrap.py'
SITE='runs/puck-cpu-install-01/site'
OUTPUTS=dict(prepare='runs/puck-cpu-held-preparation-01',qualify='runs/puck-cpu-held-qualification-01')
QUALIFY02='runs/puck-cpu-held-qualification-02'
QUALIFY03='runs/puck-cpu-held-qualification-03'
QUALIFY04='runs/puck-cpu-held-qualification-04'
QUALIFY05='runs/puck-cpu-held-qualification-05'
QUALIFY06='runs/puck-cpu-held-qualification-06'
QUALIFY07='runs/puck-cpu-held-qualification-07'
QUALIFY08='runs/puck-cpu-held-qualification-08'
QUALIFY09='runs/puck-cpu-held-qualification-09'
PILLOW_NATIVE_ORIGINS=(
    dict(name='PIL._imaging',policy='held-directory-observed-v1'),
    dict(name='PIL._imagingft',policy='held-directory-observed-v1'),
)
AUTOGRAD_EXPORT=dict(name='torch._C._autograd',producer='torch.autograd',
    phase='module_exec_publish',attributes=['torch','_C','_autograd'],class_binding=None,
    delegate_attributes=[
        'CreationMeta','DeviceType','ProfilerEvent','SavedTensor','TensorGeometry','_InputMetadata',
        '_KinetoEvent','_ProfilerDisableOptions','_ProfilerResult','_add_metadata_json','_clear_callbacks',
        '_disable_profiler','_disable_profiler_legacy','_enable_profiler','_enable_profiler_legacy',
        '_enable_record_function','_get_creation_meta','_get_current_graph_task_keep_graph',
        '_get_data_attr','_get_sequence_nr','_kineto_step','_pop_saved_tensors_default_hooks',
        '_prepare_profiler','_profiler_enabled','_profiler_type','_push_saved_tensors_default_hooks',
        '_record_function_with_args_enter','_record_function_with_args_exit','_saved_tensors_hooks_disable',
        '_saved_tensors_hooks_enable','_saved_tensors_hooks_get_disabled_error_message',
        '_saved_tensors_hooks_is_enabled','_saved_tensors_hooks_set_tracing','_set_creation_meta',
        '_set_empty_test_observer','_soft_assert_raises','_supported_activities',
        '_toggle_collection_dynamic','_top_saved_tensors_default_hooks','_unsafe_set_version_counter',
        'kineto_available',
    ])
DISTRIBUTED_EXPORTS=(
    dict(name='torch._C._distributed_autograd',producer='torch.distributed.autograd',
        phase='module_exec_publish',attributes=['torch', '_C', '_distributed_autograd'],class_binding=None,
        delegate_attributes=[
            'DistAutogradContext','_current_context','_get_debug_info','_get_max_id','_init',
            '_is_valid_context','_new_context','_release_context','_retrieve_context','backward',
            'get_gradients',
        ]),
    dict(name='torch._C._distributed_c10d',producer='torch.distributed',
        phase='module_exec_publish',attributes=['torch', '_C', '_distributed_c10d'],class_binding=None,
        delegate_attributes=[
            'AllToAllOptions','AllgatherOptions','AllreduceCoalescedOptions','AllreduceOptions',
            'Backend','BarrierOptions','BroadcastOptions','BuiltinCommHookType','DDPLoggingData',
            'DebugLevel','ErrorType','FakeProcessGroup','FakeWork','FileStore','GatherOptions',
            'GradBucket','HashStore','Logger','OpType','PrefixStore','ProcessGroup',
            'ProcessGroupGloo','ReduceOp','ReduceOptions','ReduceScatterOptions','Reducer',
            'ScatterOptions','Store','TCPStore','Work','WorkInfo','WorkResult',
            '_ControlCollectives','_DMAConnectivity','_DistributedBackendOptions',
            '_ProcessGroupWrapper','_Request','_Response','_StoreCollectives','_SymmetricMemory',
            '_WorkerServer','_allow_inflight_collective_as_graph_input','_broadcast_coalesced',
            '_compute_bucket_assignment_by_size','_create_work_from_future',
            '_current_process_group','_detect_dma_connectivity','_dump_fr_trace',
            '_dump_fr_trace_json','_get_handler','_get_handler_names','_get_work_registry_size',
            '_make_nccl_premul_sum','_register_builtin_comm_hook','_register_comm_hook',
            '_register_process_group','_register_work','_resolve_process_group',
            '_set_allow_inflight_collective_as_graph_input','_set_global_rank','_set_process_group',
            '_set_thread_isolation_mode','_test_python_store','_unregister_all_process_groups',
            '_unregister_process_group','_verify_params_across_processes','get_debug_level',
            'set_debug_level','set_debug_level_from_env',
        ]),
    dict(name='torch._C._distributed_rpc',producer='torch.distributed.rpc',
        phase='module_exec_publish',attributes=['torch', '_C', '_distributed_rpc'],class_binding=None,
        delegate_attributes=[
            'PyRRef','RemoteProfilerManager','RpcAgent','RpcBackendOptions','TensorPipeAgent',
            'WorkerInfo','_TensorPipeRpcBackendOptionsBase','_cleanup_python_rpc_handler',
            '_delete_all_user_and_unforked_owner_rrefs','_destroy_rref_context',
            '_disable_jit_rref_pickle','_disable_server_process_global_profiler',
            '_enable_jit_rref_pickle','_enable_server_process_global_profiler',
            '_get_current_rpc_agent','_invoke_remote_builtin','_invoke_remote_python_udf',
            '_invoke_remote_torchscript','_invoke_rpc_builtin','_invoke_rpc_python_udf',
            '_invoke_rpc_torchscript','_is_current_rpc_agent_set','_reset_current_rpc_agent',
            '_rref_context_get_debug_info','_set_and_start_rpc_agent','_set_profiler_node_id',
            '_set_rpc_timeout','enable_gil_profiling','get_rpc_timeout',
        ]),
)
DIAGNOSTIC_BINDINGS='src/palimpsest/puck_dependency_bindings.py'
PREPARATION_NEGATIVE_IMPORTS=['numpy._distributor_init_local','org']
QUALIFY03_NEGATIVE_IMPORTS=PREPARATION_NEGATIVE_IMPORTS+['torch._rocm_init']
QUALIFY06_NEGATIVE_IMPORTS=sorted(QUALIFY03_NEGATIVE_IMPORTS+[
    'OpenGL_accelerate','accimage','av','colorama','defusedxml','dill','flint',
    'gmpy','gmpy2','monkeytype','opt_einsum','pydot','pynvml','torchdistx','tqdm','triton',
])
LEGACY_AUDITOR_SHA256='19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9'
VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',torchvision='0.24.0+cpu',mujoco='3.3.6')
ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',
    HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/puck/source',PATH='/nonexistent',TZ='UTC',
    CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',
    OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0')
WORKER_SOURCES=tuple(sorted((BOOTSTRAP,'src/palimpsest/__init__.py',
    'src/palimpsest/puck_execution_files.py','src/palimpsest/puck_dependency_files.py',
    'src/palimpsest/puck_dependency_bindings.py','src/palimpsest/puck_dependency_imports.py',
    'src/palimpsest/puck_native_origins.py','src/palimpsest/puck_native_identity.py',
    'src/palimpsest/puck_worker_preflight.py','src/palimpsest/puck_runtime_qualification.py')))
SOURCES=tuple(sorted(set(WORKER_SOURCES)|{
    'scripts/qualify_puck_cpu_held_runtime.py','scripts/stage_puck_cpu_held_runtime.py',
    'scripts/qualify_puck_held_runtime.py','scripts/build_puck_python_louvain.py',
    'scripts/acquire_puck_cpu_payloads.py','src/palimpsest/bounded_qualification.py',
    'src/palimpsest/evaluate.py','src/palimpsest/puck_build_inputs.py',
    'src/palimpsest/puck_package_payloads.py','src/palimpsest/puck_retained_installation.py',
    'src/palimpsest/puck_runtime_registration.py','src/palimpsest/puck_runtime_staging.py',
    'src/palimpsest/puck_cpu_registration.py','src/palimpsest/puck_cpu_namespace.py'}))
INPUT_ROLES=tuple(sorted(('inventory','layout','candidate','native','baseline','generated',
    'accepted_result','accepted_snapshot','accepted_audit','accepted_configuration','accepted_index',
    'observation_configuration','observation_report','observation_result','observation_audit','observation_index')))
CLAIMS=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,
    study_authorized=False,executable=False,qualification_claims=[])
LIMITS={phase:dict(normal_seconds=180,child_hard_seconds=190,hard_seconds=200,
    rss_bytes=2048*MiB,address_space_bytes=8192*MiB,output_bytes=64*MiB,
    scratch_bytes=64*MiB,file_bytes=(1024 if phase=='prepare' else 16)*MiB,min_free_bytes=4096*MiB,
    min_available_ram_bytes=(4096 if phase=='prepare' else 2048)*MiB,
    min_tmpfs_free_bytes=(2048 if phase=='prepare' else 256)*MiB,
    max_processes=3,max_fds=40000) for phase in ('prepare','qualify')}


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def digest(raw):return hashlib.sha256(raw).hexdigest()


def relative(value):
    if (type(value) is not str or not value or value.startswith('/') or '\\' in value
            or any(v in ('','.','..') for v in value.split('/')) or len(value)>4096):
        raise ValueError('Canonical relative CPU input path required')
    return value


def pin(row):
    if (type(row) is not dict or set(row)!={'path','size_bytes','sha256'}
            or type(row['size_bytes']) is not int or not 0<row['size_bytes']<=16*MiB
            or type(row['sha256']) is not str or re.fullmatch('[0-9a-f]{64}',row['sha256']) is None):
        raise ValueError('Exact bounded CPU input pin required')
    relative(row['path']);return row


def read(path,maximum,expected=None):
    """Initial bounded nofollow read before importing any repository helpers."""
    path=Path(path);fds=[]
    if not path.is_absolute() or str(path)!=os.fspath(path) or any(p in ('.','..') for p in path.parts):
        raise ValueError('Absolute CPU control path required')
    try:
        fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
        for name in path.parts[1:-1]:
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
        leaf=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);fds.append(leaf)
        before=os.fstat(leaf)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=maximum:
            raise ValueError('CPU control is not bounded single-link regular data')
        with os.fdopen(os.dup(leaf),'rb') as handle:raw=handle.read(maximum+1)
        identity=lambda v:(v.st_dev,v.st_ino,v.st_mode,v.st_size,v.st_mtime_ns,v.st_ctime_ns,v.st_nlink)
        if identity(before)!=identity(os.fstat(leaf)) or identity(before)!=identity(os.stat(path.name,dir_fd=fd,follow_symlinks=False)) or len(raw)!=before.st_size:
            raise ValueError('CPU control changed while read')
        if expected is not None and digest(raw)!=expected:raise ValueError('CPU input SHA differs')
        return raw
    finally:
        for fd in reversed(fds):os.close(fd)


def decode(raw):
    def pairs(rows):
        result={}
        for key,value in rows:
            if key in result:raise ValueError('Duplicate CPU control key')
            result[key]=value
        return result
    def bad(_):raise ValueError('Nonfinite CPU control value')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=bad);pending=[(value,0)];count=0
    while pending:
        item,depth=pending.pop();count+=1
        if count>524288 or depth>32:raise ValueError('CPU control tree ceiling')
        if type(item) is float and not math.isfinite(item):raise ValueError('Nonfinite CPU control number')
        if type(item) is dict:pending.extend((v,depth+1) for v in item.values())
        elif type(item) is list:pending.extend((v,depth+1) for v in item)
    return value


def _negative_imports(names):
    if (type(names) is not list or not 1<=len(names)<=128 or names!=sorted(set(names))
            or any(type(n) is not str or len(n)>512 or re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',n,flags=re.ASCII) is None
                   or n.split('.')[0] in ('palimpsest','__main__','__mp_main__','_puck_held_file_bootstrap') for n in names)
            or any(n.startswith(p+'.') for i,n in enumerate(names) for p in names[:i])):
        raise ValueError('Exact finite CPU missing-import roster required')


def configuration_template(*,phase,root,stage_parent,sources,inputs,negative_imports,preparation=None,preparation_acceptance=None):
    result=dict(kind='puck-cpu-held-runtime-allocation-v1',version=1,phase=phase,allocation_id=1,
        root=root,stage_parent=stage_parent,sources=sources,inputs=inputs,interpreter=dict(INTERPRETER),
        environment=dict(ENVIRONMENT),expected_versions=dict(VERSIONS),limits=copy.deepcopy(LIMITS[phase]),
        negative_imports=negative_imports,claims=copy.deepcopy(CLAIMS))
    if preparation_acceptance is not None:
        if preparation is not None:raise ValueError('One CPU preparation epoch required')
        result.update(kind='puck-cpu-held-runtime-allocation-v2',version=2,allocation_id=2,
                      preparation_acceptance=preparation_acceptance)
    elif phase=='qualify':result['preparation']=preparation
    return result


def validate_configuration(config):
    keys={'kind','version','phase','allocation_id','root','stage_parent','sources','inputs',
          'interpreter','environment','expected_versions','limits','negative_imports','claims'}
    phase=config.get('phase') if type(config) is dict else None
    kind=config.get('kind') if type(config) is dict else None
    epoch=9 if kind=='puck-cpu-held-runtime-allocation-v9' else 8 if kind=='puck-cpu-held-runtime-allocation-v8' else 7 if kind=='puck-cpu-held-runtime-allocation-v7' else 6 if kind=='puck-cpu-held-runtime-allocation-v6' else 5 if kind=='puck-cpu-held-runtime-allocation-v5' else 4 if kind=='puck-cpu-held-runtime-allocation-v4' else 3 if kind=='puck-cpu-held-runtime-allocation-v3' else 2 if kind=='puck-cpu-held-runtime-allocation-v2' else 1
    amended=epoch in (2,3,4,5,6,7,8,9)
    if amended:keys.add('preparation_acceptance')
    elif phase=='qualify':keys.add('preparation')
    if (phase not in LIMITS or set(config)!=keys or (amended and phase!='qualify')
            or config['kind']!='puck-cpu-held-runtime-allocation-v'+str(epoch)
            or type(config['version']) is not int or config['version']!=epoch
            or type(config['allocation_id']) is not int or config['allocation_id']!=epoch
            or config['root']!=str(ROOT) or canonical(config['limits'])!=canonical(LIMITS[phase])
            or config['interpreter']!=INTERPRETER or canonical(config['environment'])!=canonical(ENVIRONMENT)
            or config['expected_versions']!=VERSIONS or canonical(config['claims'])!=canonical(CLAIMS)):
        raise ValueError('Exact CPU allocation configuration required')
    stage=config['stage_parent']
    if (type(stage) is not str or Path(stage).parent!=Path('/tmp') or str(Path(stage))!=stage
            or not re.fullmatch(r'/tmp/palimpsest-puck-cpu-held-[A-Za-z0-9_-]+',stage)):
        raise ValueError('Private CPU tmpfs allocation path required')
    sources=config['sources'];inputs=config['inputs']
    if (type(sources) is not list or [pin(r)['path'] for r in sources]!=list(SOURCES)
            or type(inputs) is not dict or set(inputs)!=set(INPUT_ROLES)):
        raise ValueError('Exact CPU source/input closure required')
    for row in inputs.values():pin(row)
    if amended:
        acceptance=config['preparation_acceptance']
        if type(acceptance) is not dict or set(acceptance)!={'configuration','result','independent_audit','externally_observed_auditor_cli'}:
            raise ValueError('Exact CPU historical preparation acceptance required')
        for row in acceptance.values():pin(row)
        if acceptance['result']['path']!=OUTPUTS['prepare']+'/result.json':raise ValueError('Exact CPU preparation receipt required')
    elif phase=='qualify':
        pin(config['preparation'])
        if config['preparation']['path']!=OUTPUTS['prepare']+'/result.json':raise ValueError('Exact CPU preparation receipt required')
    _negative_imports(config['negative_imports'])
    if epoch in (3,4,5) and config['negative_imports']!=QUALIFY03_NEGATIVE_IMPORTS:
        raise ValueError('Exact CPU qualification0'+str(epoch)+' missing-import roster required')
    if epoch in (6,7,8,9) and config['negative_imports']!=QUALIFY06_NEGATIVE_IMPORTS:
        raise ValueError('Exact CPU qualification0'+str(epoch)+' missing-import roster required')


def allocation_output(config):
    validate_configuration(config)
    if config['version']==9:return QUALIFY09
    if config['version']==8:return QUALIFY08
    if config['version']==7:return QUALIFY07
    if config['version']==6:return QUALIFY06
    if config['version']==5:return QUALIFY05
    if config['version']==4:return QUALIFY04
    if config['version']==3:return QUALIFY03
    return QUALIFY02 if config['version']==2 else OUTPUTS[config['phase']]


def validate_publication_candidate(prior,current,*,pillow_origins=False):
    if type(prior) is not dict or type(current) is not dict:
        raise ValueError('CPU publication candidate objects required')
    profile=prior.get('import_profile')
    rows=profile.get('exports') if type(profile) is dict else None
    if type(rows) is not list or any(type(row) is not dict for row in rows):
        raise ValueError('Historical CPU export declarations required')
    expected=copy.deepcopy(prior)
    for replacement in (AUTOGRAD_EXPORT,*DISTRIBUTED_EXPORTS):
        targets=[i for i,row in enumerate(rows) if row.get('name')==replacement['name']]
        old=dict(name=replacement['name'],producer='torch._C',phase='native_create',
                 attributes=[replacement['attributes'][-1]],class_binding=None)
        if len(targets)!=1 or rows[targets[0]]!=old:
            raise ValueError('Exact historical publication export declaration required')
        expected['import_profile']['exports'][targets[0]]=copy.deepcopy(replacement)
    if pillow_origins:
        origins=profile.get('native_origins')
        if type(origins) is not list or any(type(row) is not dict or type(row.get('name')) is not str for row in origins):
            raise ValueError('Historical native origin declarations required')
        names=[row['name'] for row in origins]
        if names!=sorted(set(names)) or set(names)&{row['name'] for row in PILLOW_NATIVE_ORIGINS}:
            raise ValueError('Historical Pillow origins must be undeclared in a sorted unique roster')
        expected['import_profile']['native_origins']=sorted(
            copy.deepcopy(origins)+list(PILLOW_NATIVE_ORIGINS),key=lambda row:row['name'])
    if canonical(current)!=canonical(expected):
        raise ValueError('CPU candidate must change only four publication and two Pillow origin declarations'
                         if pillow_origins else 'CPU publication candidate must change only the exact four declarations')


def validate_preparation_acceptance(config,blobs):
    """Bind historical data acceptance without assigning its old source proof to new bytes."""
    validate_configuration(config)
    if config['version'] not in (2,3,4,5,6,7,8,9):raise ValueError('CPU amendment02–09 configuration required')
    acceptance=config['preparation_acceptance'];values={}
    for role,row in acceptance.items():
        raw=blobs[role]
        if len(raw)!=row['size_bytes'] or digest(raw)!=row['sha256']:raise ValueError('Historical CPU preparation pin differs')
        value=decode(raw)
        if type(value) is not dict:raise ValueError('Historical CPU preparation object required')
        if role in ('configuration','result') and canonical(value)!=raw:raise ValueError('Canonical historical CPU preparation bytes required')
        values[role]=value
    prior,prep,audit,cli=(values[k] for k in ('configuration','result','independent_audit','externally_observed_auditor_cli'))
    validate_configuration(prior)
    if prior['version']!=1 or prior['phase']!='prepare':raise ValueError('Historical CPU preparation01 required')
    shared=('root','stage_parent','inputs','interpreter','environment','expected_versions','negative_imports','claims')
    if config['version'] in (3,4,5,6,7,8,9):
        if prior['negative_imports']!=PREPARATION_NEGATIVE_IMPORTS:
            raise ValueError('Exact historical CPU preparation missing-import roster required')
        shared=tuple(k for k in shared if k!='negative_imports')
    if config['version'] in (5,6,7,8,9):
        shared=tuple(k for k in shared if k!='inputs')
        if (any(prior['inputs'][k]!=config['inputs'][k] for k in INPUT_ROLES if k!='candidate')
                or any(prior['inputs']['candidate'][k]==config['inputs']['candidate'][k] for k in ('path','sha256'))):
            raise ValueError('CPU publication amendment must change only a distinct candidate pin')
    if any(prior[k]!=config[k] for k in shared):raise ValueError('CPU amendment changed prepared data or policy')
    changed={old['path'] for old,new in zip(prior['sources'],config['sources']) if old!=new}
    if config['version'] in (8,9):
        if changed!={BOOTSTRAP,'scripts/qualify_puck_cpu_held_runtime.py',DIAGNOSTIC_BINDINGS,
                     'src/palimpsest/puck_dependency_imports.py','src/palimpsest/puck_runtime_qualification.py'}:
            raise ValueError('CPU diagnostic0'+str(config['version'])+' requires exactly five changed source paths')
    elif config['version'] in (5,6,7):
        if changed!={BOOTSTRAP,'scripts/qualify_puck_cpu_held_runtime.py',DIAGNOSTIC_BINDINGS,'src/palimpsest/puck_dependency_imports.py'}:
            raise ValueError('CPU publication amendment requires exactly four changed source paths')
    elif config['version']==4:
        if not {BOOTSTRAP,DIAGNOSTIC_BINDINGS}<=changed or not changed<={BOOTSTRAP,DIAGNOSTIC_BINDINGS,'scripts/qualify_puck_cpu_held_runtime.py'}:
            raise ValueError('CPU diagnostic amendment must change bootstrap and bindings and only optional parent')
    elif BOOTSTRAP not in changed or not changed<={BOOTSTRAP,'scripts/qualify_puck_cpu_held_runtime.py'}:
        raise ValueError('CPU amendment source changes must be bootstrap and optional parent only')
    false_claims=lambda value:any(value.get(k)!=v or type(value.get(k)) is not type(v) for k,v in CLAIMS.items())
    def closed(value,expected):
        row=value.get('closure',{})
        return (row.get('active_children')==[] and row.get('active_non_main_threads')==[]
                and type(row.get('fd_count_before')) is int and row['fd_count_before']==expected
                and type(row.get('fd_count_after')) is int and row['fd_count_before']==row['fd_count_after'])
    def elapsed(value,maximum):
        return type(value) in (int,float) and math.isfinite(value) and 0<value<maximum
    if (prep.get('kind')!='puck-cpu-held-runtime-outcome-v1' or type(prep.get('version')) is not int or prep['version']!=1
            or type(prep.get('allocation_id')) is not int or prep['allocation_id']!=1
            or prep.get('phase')!='prepare' or prep.get('status')!='prepared' or any(k in prep for k in ('error','error_type'))
            or prep.get('held_four_imports_observed') is not False or false_claims(prep)
            or prep.get('configuration_sha256')!=acceptance['configuration']['sha256']
            or prep.get('stage_parent')!=prior['stage_parent'] or prep.get('sources')!=prior['sources']
            or prep.get('inputs')!=prior['inputs'] or not closed(prep,5) or not elapsed(prep.get('elapsed_seconds'),180)):
        raise ValueError('Historical CPU preparation receipt differs or failed')
    dep=pin(prep.get('dependencies'))
    if dep['path']!='payload/dependencies.json':raise ValueError('Historical CPU dependency path differs')
    if (audit.get('kind')!='puck-cpu-held-runtime-independent-audit-v1' or type(audit.get('version')) is not int or audit['version']!=1
            or audit.get('status')!='PASS' or audit.get('phase')!='prepare' or audit.get('observed_status')!='prepared'
            or any(k in audit for k in ('error','error_type'))
            or audit.get('held_four_imports_observed') is not False or false_claims(audit)
            or type(audit.get('external_returncode')) is not int or audit['external_returncode']!=0
            or audit.get('auditor_source_sha256')!=LEGACY_AUDITOR_SHA256
            or audit.get('configuration_sha256')!=acceptance['configuration']['sha256']
            or audit.get('result_sha256')!=acceptance['result']['sha256'] or audit.get('dependencies_sha256')!=dep['sha256']
            or type(audit.get('root_count')) is not int or audit['root_count']!=4
            or audit.get('evidence_scope')!='ordinary CPU held allocation only'
            or type(audit.get('transport_sha256')) is not str or re.fullmatch('[0-9a-f]{64}',audit['transport_sha256']) is None
            or not closed(audit,4) or not elapsed(audit.get('elapsed_seconds'),120)):
        raise ValueError('Historical CPU independent audit failed or provenance differs')
    cli_keys={'kind','command','observed_returncode','elapsed_seconds','published','stdout','stderr'}
    if (set(cli) not in (cli_keys,cli_keys|{'at','scope'})
            or cli['kind']!='externally-observed-cpu-auditor-cli-v1'
            or type(cli['observed_returncode']) is not int or cli['observed_returncode']!=0
            or not elapsed(cli['elapsed_seconds'],130)):
        raise ValueError('Historical CPU auditor CLI did not return normally')
    if 'at' in cli and (type(cli['at']) is not str or not 0<len(cli['at'])<=128
            or cli['scope']!='fresh read-only current-byte audit of prepared data; no preparation or qualification allocation invoked'):
        raise ValueError('Historical CPU auditor CLI metadata differs')
    for channel in ('published','stdout','stderr'):
        row=cli[channel]
        if (type(row) is not dict or set(row)!={'path','size_bytes','sha256'}
                or type(row['path']) is not str or not row['path'].startswith('/') or str(Path(row['path']))!=row['path']):
            raise ValueError('Historical CPU auditor CLI channel differs')
        if (type(row['size_bytes']) is not int or not 0<=row['size_bytes']<=16*MiB
                or type(row['sha256']) is not str or re.fullmatch('[0-9a-f]{64}',row['sha256']) is None):
            raise ValueError('Historical CPU auditor CLI channel pin differs')
    expected={k:acceptance['independent_audit'][k] for k in ('size_bytes','sha256')}
    if (any({k:cli[name][k] for k in expected}!=expected for name in ('published','stdout'))
            or cli['stderr']['size_bytes']!=0 or cli['stderr']['sha256']!=digest(b'')):
        raise ValueError('Historical CPU auditor CLI stdout/publication differs')
    command=cli['command']
    if (type(command) is not list or len(command)!=15
            or command[10] not in (str(ROOT/'authored-prepare-transport.json'),str(ROOT/'runs/puck-cpu-held-preparation-01-external-cli-transport.json'))
            or command!=[PYTHON,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),
                '--configuration',str(ROOT/acceptance['configuration']['path']),'--sha256',acceptance['configuration']['sha256'],
                '--transport',command[10],'--transport-sha256',audit.get('transport_sha256'),'--output',cli['published']['path']]):
        raise ValueError('Historical CPU auditor CLI command differs')
    return prior,prep


def qualification_command(worker_command):
    # bwrap's PID1 remains the real observable parent. The trusted PID2 launcher
    # creates the dedicated session, then exec preserves the exact frozen argv.
    launcher='import os,sys;os.setsid();os.execv(sys.argv[1],sys.argv[1:])'
    if type(worker_command) is not list or worker_command[:4]!=[PYTHON,'-I','-B','-S']:
        raise ValueError('Exact original isolated CPU worker command required')
    return [PYTHON,'-I','-B','-S','-c',launcher]+list(worker_command)


def worker_registration(source_files,dependency_raw,*,negative_imports):
    _negative_imports(negative_imports)
    if [pin(r)['path'] for r in source_files]!=list(WORKER_SOURCES):raise ValueError('Exact CPU worker source closure required')
    bootstrap=next(r for r in source_files if r['path']==BOOTSTRAP)
    raw=read(ROOT/BOOTSTRAP,MiB,bootstrap['sha256'])
    if len(raw)!=bootstrap['size_bytes']:raise ValueError('CPU bootstrap size differs')
    api=types.ModuleType('_frozen_cpu_bootstrap_api');api.__file__=str(ROOT/BOOTSTRAP)
    exec(compile(raw,api.__file__,'exec'),api.__dict__)
    prefix=api.command(PYTHON,'/puck/source/'+BOOTSTRAP,bootstrap['sha256'],'/puck/control/worker-registration.json','0'*64)[:-1]
    modules=[]
    for row in source_files:
        if row['path']==BOOTSTRAP:continue
        name=row['path'][4:-3].replace('/','.')
        if name.endswith('.__init__'):name=name[:-9]
        modules.append(dict(name=name,path=row['path']))
    result=dict(kind='puck-worker-source-bootstrap-v3',version=3,source_root='/puck/source',
        source_files=copy.deepcopy(source_files),modules=modules,namespaces=[],
        runtime=dict(root=str(Path(PYTHON).parent),files=[dict(api.RUNTIME_PIN)],python_version='3.11.15'),
        environment=dict(ENVIRONMENT),cwd='/puck/source',argv_prefix=prefix,
        dependencies=dict(path='/puck/control/dependencies.json',size_bytes=len(dependency_raw),sha256=digest(dependency_raw)),
        qualification=dict(kind='puck-held-runtime-import-qualification-v3',version=3,
            expected_versions=dict(VERSIONS),stdlib_cache_aliases={'__mp_main__':'__main__'},negative_imports=list(negative_imports)),
        qualification_claims=[],executable=False)
    worker_raw=api.canonical(result)
    return result,prefix+[digest(worker_raw)]


def validate_worker_result(result,*,registration_sha256,dependency_sha256,dependencies,negative_imports):
    dep=result.get('dependencies',{});entry=result.get('entry_result',{});imports=entry.get('imports',[])
    count=sum(len(r['files']) for r in dependencies['roots'])
    byte_count=sum(f['size_bytes'] for r in dependencies['roots'] for f in r['files'])
    caches=sorted(dependencies['import_profile'].get('native_cache',[]),key=lambda r:r['name'])
    publications=[{key:row[key] for key in ('name','producer','phase','attributes','delegate_attributes')}
        for row in sorted(dependencies['import_profile'].get('exports',[]),key=lambda r:r['name'])
        if row.get('phase')=='module_exec_publish']
    if (result.get('kind')!='puck-worker-source-bootstrap-receipt-v1'
            or result.get('registration_sha256')!=registration_sha256
            or result.get('interpreter_object_bound') is not True or result.get('python_version')!='3.11.15'
            or any(result.get(k) is not False for k in ('runtime_qualified','dependencies_qualified','native_authorized','collection_authorized','executable'))
            or result.get('qualification_claims')!=[] or result.get('expected_missing_imports')!=negative_imports
            or type(result.get('denied_imports')) is not list or not set(result['denied_imports'])<=set(negative_imports)
            or dep.get('registration_sha256')!=dependency_sha256 or dep.get('native_identity')!='tmpfs-raw-dev-inode-v1'
            or type(dep.get('root_count')) is not int or dep['root_count']!=4
            or type(dep.get('file_count')) is not int or dep['file_count']!=count
            or type(dep.get('input_bytes')) is not int or dep['input_bytes']!=byte_count
            or dep.get('native_cache_modules',[])!=caches
            or (dep.get('published_export_modules')!=publications if publications
                else 'published_export_modules' in dep)
            or entry.get('kind')!='puck-held-runtime-import-qualification-result-v2'
            or type(entry.get('version')) is not int or entry['version']!=2
            or type(entry.get('qualification_version')) is not int or entry['qualification_version']!=3
            or entry.get('status')!='imports_completed' or entry.get('held_imports_observed') is not True
            or [r.get('name') for r in imports]!=list(VERSIONS)
            or {r['name']:r.get('version') for r in imports}!=VERSIONS):
        raise ValueError('CPU held-import terminal is incomplete or differs from frozen request')


def validate_observation_links(config,blobs):
    pins=config['inputs'];frozen=decode(blobs['observation_configuration'])
    roles=('inventory','layout','native','baseline','accepted_result','accepted_snapshot',
           'accepted_audit','accepted_configuration','accepted_index')
    if (frozen.get('kind')!='puck-cpu-runtime-characterization-v1'
            or type(frozen.get('version')) is not int or frozen['version']!=1
            or type(frozen.get('roles')) is not dict or type(frozen.get('inputs')) is not list):
        raise ValueError('Authenticated CPU observation configuration differs')
    old_rows={r['path']:r for r in frozen['inputs']}
    if len(old_rows)!=len(frozen['inputs']):raise ValueError('Duplicated frozen CPU observation input')
    for role in roles:
        name='native_metadata' if role=='native' else role
        if frozen['roles'].get(name)!=pins[role]['path'] or old_rows.get(pins[role]['path'])!=pins[role]:
            raise ValueError('Current CPU metadata differs from frozen observation role: '+role)
    bindings={
        'accepted_index':('retained-admission-02-evidence-index-v1',{
            'inventory':'raw/inventory.json','accepted_result':'raw/result.json',
            'accepted_snapshot':'raw/snapshot.json','accepted_audit':'acceptance-audit-03.json',
            'accepted_configuration':'raw/configuration.json'}),
        'observation_index':('cpu-characterization-evidence-index-v2',{
            'observation_configuration':'frozen-configuration.json','observation_report':'raw/payload/imports.json',
            'observation_result':'raw/result.json','observation_audit':'outcome-audit-02.json'})}
    for role,(kind,paths) in bindings.items():
        index=decode(blobs[role]);entries=index.get('entries')
        if index.get('kind')!=kind or type(entries) is not list or not 1<=len(entries)<=512:
            raise ValueError('CPU evidence index schema differs')
        indexed={r['path']:r for r in entries}
        if len(indexed)!=len(entries):raise ValueError('Duplicated CPU evidence index row')
        for name,path in paths.items():
            expected=dict(pins[name],path=path)
            if role=='accepted_index' and name=='accepted_configuration':
                # The accepted parent retained compact JSON+LF, while its frozen
                # external configuration keeps its original pretty bytes.
                retained=canonical(decode(blobs[name]))
                expected=dict(path=path,size_bytes=len(retained),sha256=digest(retained))
            if indexed.get(path)!=expected:
                raise ValueError('CPU evidence index byte binding differs: '+name)


def verify_staged_roots(stage_parent,dependencies,expected):
    roots=dependencies.get('roots')
    names=['root-'+str(i).zfill(4) for i in range(4)]
    if (type(roots) is not list or len(roots)!=4 or type(expected) is not list or len(expected)!=4
            or [r.get('root') for r in roots]!=['/puck/staged/inputs/'+name for name in names]):
        raise ValueError('CPU prepared root ordering or private paths differ')
    parent=os.open(stage_parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);inputs=None
    try:
        inputs=os.open('inputs',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
        for i,name in enumerate(names):
            row=expected[i]
            if (type(row) is not dict or set(row)!={'root_index','device','inode'}
                    or any(type(v) is not int for v in row.values()) or row['root_index']!=i):
                raise ValueError('CPU prepared root identity schema differs')
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=inputs)
            try:
                state=os.fstat(fd);named=os.stat(name,dir_fd=inputs,follow_symlinks=False)
                if ((state.st_dev,state.st_ino)!=(row['device'],row['inode'])
                        or (named.st_dev,named.st_ino)!=(row['device'],row['inode'])
                        or not stat.S_ISDIR(state.st_mode) or stat.S_IMODE(state.st_mode)!=0o700):
                    raise ValueError('CPU prepared root object was replaced')
            finally:os.close(fd)
    finally:
        if inputs is not None:os.close(inputs)
        os.close(parent)


def validate_inputs(config,blobs):
    validate_observation_links(config,blobs)
    get=lambda role:decode(blobs[role]);pins=config['inputs']
    accepted,snapshot,audit,accepted_config=(get(k) for k in ('accepted_result','accepted_snapshot','accepted_audit','accepted_configuration'))
    candidate,observation,observed,audit02=(get(k) for k in ('candidate','observation_report','observation_result','observation_audit'))
    if (accepted.get('kind')!='cpu-retained-installation-admission-result-v2' or accepted.get('status')!='PASS'
            or accepted.get('claims',{}).get('package_preparation_accepted') is not True
            or any(accepted['claims'].get(k) is not False for k in ('runtime_qualified','numerical_imports_executed','study_authorized','collection_authorized'))
            or accepted.get('configuration_sha256')!=pins['accepted_configuration']['sha256']
            or accepted.get('snapshot_sha256')!=pins['accepted_snapshot']['sha256']
            or accepted.get('site_root')!=str(ROOT/SITE) or snapshot.get('site_root')!=str(ROOT/SITE)
            or audit.get('status')!='PASS' or audit.get('package_preparation_accepted') is not True
            or audit.get('verified',{}).get('configuration_sha256')!=pins['accepted_configuration']['sha256']
            or snapshot.get('configuration_sha256')!=pins['accepted_configuration']['sha256']):
        raise ValueError('Accepted CPU package data binding differs')
    inventory,layout=get('inventory'),get('layout')
    if (accepted.get('file_count')!=inventory.get('file_count') or accepted.get('directory_count')!=inventory.get('directory_count')
            or accepted.get('regular_file_bytes')!=inventory.get('total_bytes')
            or len(layout.get('predicted_destination_directories',[]))!=inventory.get('directory_count')):
        raise ValueError('Accepted CPU package size or directory binding differs')
    layout_pins=[r for r in accepted_config.get('inputs',[]) if r['path']==pins['layout']['path']]
    if layout_pins!=[pins['layout']]:raise ValueError('Accepted CPU layout pin differs')
    if (observed.get('status')!='observed' or observed.get('report_sha256')!=pins['observation_report']['sha256']
            or observed.get('configuration_sha256')!=pins['observation_configuration']['sha256']
            or observation.get('kind')!='puck-runtime-import-characterization-result-v3'
            or observation.get('versions')!=VERSIONS or observed.get('versions')!=VERSIONS
            or candidate.get('expected_versions')!=VERSIONS
            or candidate.get('observation_report_sha256')!=pins['observation_report']['sha256']
            or candidate.get('configuration_sha256')!=pins['observation_configuration']['sha256']
            or candidate.get('outcome_audit_sha256')!=pins['observation_audit']['sha256']
            or candidate.get('retained_inventory_sha256')!=pins['inventory']['sha256']
            or audit02.get('status')!='PASS' or audit02.get('ordinary_imports_observed') is not True
            or audit02.get('verified',{}).get('result_sha256')!=pins['observation_result']['sha256']
            or audit02['verified'].get('report_sha256')!=pins['observation_report']['sha256']
            or any(observed.get(k) is not False for k in CLAIMS if k!='qualification_claims')
            or observed.get('qualification_claims')!=[]):raise ValueError('Accepted ordinary CPU observation binding differs')
    additional=candidate.get('additional_package_inputs',[])
    if len(additional)!=1 or len(additional[0].get('files',[]))!=1:
        raise ValueError('Exact generated CPU helper input required')
    generated=additional[0]['files'][0]
    if pins['generated']!=dict(generated,path=additional[0]['root']+'/'+generated['path']):
        raise ValueError('Generated CPU helper pin differs')
    return inventory,layout,candidate,observation


def resource_admission(config):
    limits=config['limits'];parent=Path(config['stage_parent']).parent
    available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    if (any(v!=resource.RLIM_INFINITY and v<limits['max_fds'] for v in (soft,hard))
            or available<limits['min_available_ram_bytes'] or shutil.disk_usage(ROOT).free<limits['min_free_bytes']
            or shutil.disk_usage(parent).free<limits['min_tmpfs_free_bytes']):
        raise ValueError('CPU held-runtime resource admission failed')
    flags=os.statvfs(parent).f_flag
    if flags & (os.ST_RDONLY|os.ST_NOEXEC):raise ValueError('CPU staging tmpfs must be writable and executable')
    from palimpsest.puck_native_identity import require_tmpfs_descriptor
    # The native identity API deliberately admits regular files only. Probe a
    # fresh named file, closing/removing it before any allocation is reserved.
    fd,probe=tempfile.mkstemp(prefix='.palimpsest-cpu-tmpfs-probe-',dir=parent)
    identity=None
    try:
        identity=require_tmpfs_descriptor(fd)
        named=os.stat(probe,follow_symlinks=False)
        if (named.st_dev,named.st_ino)!=identity:raise ValueError('CPU tmpfs probe edge changed')
    finally:
        state=os.fstat(fd);os.close(fd)
        named=os.stat(probe,follow_symlinks=False)
        if (named.st_dev,named.st_ino)!=(state.st_dev,state.st_ino):
            raise ValueError('CPU tmpfs probe cleanup edge changed')
        os.unlink(probe)
    return dict(mem_available_bytes=available,tmpfs_available_bytes=shutil.disk_usage(parent).free,
                disk_available_bytes=shutil.disk_usage(ROOT).free)


def closure(before):
    children=Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split()
    threads=[t.name for t in threading.enumerate() if t is not threading.main_thread()]
    after=len(os.listdir('/proc/self/fd'))
    if children or threads or before!=after:raise ValueError('CPU parent process/thread/descriptor closure failed')
    return dict(active_children=[],active_non_main_threads=[],fd_count_before=before,fd_count_after=after)


def create_capsule(directory,names,source_bytes,write):
    for prefix in ('src/palimpsest','scripts','upstream/fly-gym'):
        (directory/prefix).mkdir(mode=0o700,parents=True,exist_ok=True)
    for name in names:
        target=directory/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        write(target,source_bytes[name])


def execute(config,raw,started):
    # All repository imports occur only after main authenticates their source bytes.
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
    import qualify_puck_held_runtime as controls
    import build_puck_python_louvain as baseline_api
    from palimpsest import bounded_qualification as bounds
    from palimpsest.puck_retained_installation import AdmissionInputs
    from palimpsest.puck_cpu_registration import build_cpu_source_registration,attach_cpu_candidate
    from palimpsest.puck_cpu_namespace import sandbox_command
    phase=config['phase'];limits=config['limits'];output=ROOT/allocation_output(config);stage=Path(config['stage_parent'])
    amended=config['version'] in (2,3,4,5,6,7,8,9)
    rows=config['sources']+list(config['inputs'].values())
    unique={r['path']:r for r in rows}
    if len(unique)!=len(rows):raise ValueError('Overlapping CPU source/input pins')
    admission=resource_admission(config)
    if phase=='prepare' and os.path.lexists(stage):raise FileExistsError('CPU tmpfs allocation already exists')
    if phase=='qualify':
        if amended:
            acceptance=config['preparation_acceptance'];rows+=list(acceptance.values())
            prior_raw=read(ROOT/acceptance['configuration']['path'],MiB,acceptance['configuration']['sha256'])
            prior=decode(prior_raw);validate_configuration(prior)
            if config['version'] in (5,6,7,8,9):rows.append(prior['inputs']['candidate'])
            old_configuration=OUTPUTS['prepare']+'/configuration.json'
            if acceptance['configuration']['path']!=old_configuration:
                rows.append(dict(acceptance['configuration'],path=old_configuration))
            for capsule,names in (('parent-source',SOURCES),('worker-source',WORKER_SOURCES)):
                rows.extend(dict(row,path=OUTPUTS['prepare']+'/'+capsule+'/'+row['path']) for row in prior['sources'] if row['path'] in names)
            if len({r['path'] for r in rows})!=len(rows):raise ValueError('Overlapping CPU amendment source/input pins')
        else:rows=rows+[config['preparation']]
    deadline=started+limits['normal_seconds'];state={};before_fds=len(os.listdir('/proc/self/fd'))
    bounds.reserve_output(output,dict(sources=dict(root=str(ROOT),files=rows)))
    for name in ('logs','control','payload'):(output/name).mkdir(mode=0o700)
    result=dict(CLAIMS,kind='puck-cpu-held-runtime-outcome-v'+str(config['version']),version=config['version'],phase=phase,allocation_id=config['allocation_id'],
                configuration_sha256=digest(raw),status='FAIL',held_four_imports_observed=False)
    bounds.write_new(output/'configuration.json',config)
    bounds.write_new(output/'resource-admission.json',admission)
    try:
        with bounds.hard_guard(started+limits['hard_seconds'],state):
            with AdmissionInputs(ROOT,sorted(rows,key=lambda r:r['path']),deadline) as inputs:
                blobs={role:read(ROOT/row['path'],16*MiB,row['sha256']) for role,row in config['inputs'].items()}
                inventory,layout,candidate,observation=validate_inputs(config,blobs)
                baseline=decode(blobs['baseline']);native=decode(blobs['native'])
                def native_checks():
                    for row in native['native_files']:
                        if baseline_api.file_row(Path(row['path']),deadline,single_link=False)!={k:row[k] for k in ('size_bytes','sha256')}:
                            raise ValueError('Original CPU native input changed')
                    for path,target in native['aliases']:
                        if os.readlink(path)!=target:raise ValueError('Original CPU native alias changed')
                native_checks()
                baseline_before=baseline_api.verify_baseline(baseline,deadline)
                bounds.write_new(output/'baseline-before.json',baseline_before)
                source_bytes={r['path']:read(ROOT/r['path'],MiB,r['sha256']) for r in config['sources']}
                generated_root=str((ROOT/config['inputs']['generated']['path']).parent)
                source_reg=build_cpu_source_registration(blobs['inventory'],blobs['layout'],blobs['candidate'],blobs['native'],
                    expected_pins={k:{x:config['inputs'][k][x] for x in ('size_bytes','sha256')} for k in ('inventory','layout','candidate','native')},
                    site_root=str(ROOT/SITE),generated_root=generated_root,deadline=deadline)
                if phase=='prepare':
                    os.mkdir(stage,0o700);os.chmod(stage,0o700)
                    driver_source=output/'parent-source';worker_source=output/'worker-source'
                    for directory,names in ((driver_source,SOURCES),(worker_source,WORKER_SOURCES)):
                        create_capsule(directory,names,source_bytes,controls.write)
                    copy_raw=json.dumps(source_reg,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode();controls.write(output/'control/copy-registration.json',copy_raw,16*MiB)
                    for role in ('candidate','layout'):controls.write(output/('control/'+role+'.json'),blobs[role],16*MiB)
                    request=dict(registration=dict(path='/puck/control/copy-registration.json',sha256=digest(copy_raw)),
                        candidate=dict(path='/puck/control/candidate.json',sha256=digest(blobs['candidate'])),
                        layout=dict(path='/puck/control/layout.json',sha256=digest(blobs['layout'])))
                    request_raw=canonical(request);controls.write(output/'control/stage-request.json',request_raw)
                    command=[PYTHON,'-I','-S','-B','/puck/source/scripts/stage_puck_cpu_held_runtime.py',digest(request_raw)]
                    sandbox_source=driver_source
                else:
                    if amended:
                        old_blobs={role:read(ROOT/row['path'],MiB,row['sha256']) for role,row in acceptance.items()}
                        prior,prep=validate_preparation_acceptance(config,old_blobs)
                        if read(ROOT/old_configuration,MiB,acceptance['configuration']['sha256'])!=old_blobs['configuration']:
                            raise ValueError('Historical CPU preparation configuration copy differs')
                        for capsule,names in (('parent-source',SOURCES),('worker-source',WORKER_SOURCES)):
                            for row in prior['sources']:
                                if row['path'] in names:read(ROOT/OUTPUTS['prepare']/capsule/row['path'],MiB,row['sha256'])
                    else:prep=decode(read(ROOT/config['preparation']['path'],MiB,config['preparation']['sha256']))
                    if not amended and (prep.get('status')!='prepared' or prep.get('phase')!='prepare' or prep.get('stage_parent')!=str(stage)
                            or prep.get('sources')!=config['sources'] or prep.get('inputs')!=config['inputs']
                            or any(prep.get(k) is not False for k in CLAIMS if k!='qualification_claims')
                            or prep.get('qualification_claims')!=[]):raise ValueError('CPU preparation receipt differs or failed')
                    prepared=ROOT/OUTPUTS['prepare'];dep=prep['dependencies']
                    dependency_raw=read(prepared/'payload/dependencies.json',16*MiB,dep['sha256'])
                    if len(dependency_raw)!=dep['size_bytes']:raise ValueError('CPU prepared registration size differs')
                    dependencies=decode(dependency_raw);expected=dependencies
                    if config['version'] in (5,6,7,8,9):
                        old_pin=prior['inputs']['candidate']
                        old_raw=read(ROOT/old_pin['path'],16*MiB,old_pin['sha256'])
                        if len(old_raw)!=old_pin['size_bytes']:raise ValueError('Historical candidate size differs')
                        validate_publication_candidate(decode(old_raw),candidate,pillow_origins=config['version'] in (7,8,9))
                        if (read(prepared/'control/candidate.json',16*MiB,old_pin['sha256'])!=old_raw
                                or attach_cpu_candidate(dependencies,old_raw,expected_sha256=old_pin['sha256'],deadline=deadline)!=dependencies):
                            raise ValueError('Historical candidate/prepared dependency profile differs')
                        expected=copy.deepcopy(dependencies)
                        expected['import_profile']=copy.deepcopy(candidate['import_profile'])
                    attached=attach_cpu_candidate(dependencies,blobs['candidate'],expected_sha256=config['inputs']['candidate']['sha256'],deadline=deadline)
                    if (attached!=expected or dependencies.get('distributions')!=source_reg['distributions']
                            or any(a.get('files')!=b['files'] for a,b in zip(dependencies['roots'],source_reg['roots']))):
                        raise ValueError('CPU prepared bytes/profile differ from accepted source plan')
                    if config['version'] in (5,6,7,8,9):
                        dependencies=attached;dependency_raw=canonical(attached)[:-1]
                    if amended:
                        audit=decode(old_blobs['independent_audit'])
                        if (audit.get('file_count')!=sum(len(r['files']) for r in dependencies['roots'])
                                or audit.get('input_bytes')!=sum(f['size_bytes'] for r in dependencies['roots'] for f in r['files'])):
                            raise ValueError('Historical CPU independent audit data counts differ')
                    verify_staged_roots(str(stage),dependencies,prep['staged_roots'])
                    controls.write(output/'control/dependencies.json',dependency_raw,16*MiB)
                    files=[r for r in config['sources'] if r['path'] in WORKER_SOURCES]
                    sandbox_source=output/'worker-source' if amended else prepared/'worker-source'
                    if amended:create_capsule(sandbox_source,WORKER_SOURCES,source_bytes,controls.write)
                    for row in files:read(sandbox_source/row['path'],MiB,row['sha256'])
                    worker,command=worker_registration(files,dependency_raw,negative_imports=config['negative_imports'])
                    worker_raw=json.dumps(worker,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
                    controls.write(output/'control/worker-registration.json',worker_raw)
                    command=qualification_command(command)
                    generated_root=None
                command=sandbox_command(baseline,native,sorted(r['path'] for r in observation['baseline_maps']['images']),
                    phase=phase,stage_parent=str(stage),source_root=str(sandbox_source),control_root=str(output/'control'),
                    output_root=str(output/'payload'),command=command,environment=ENVIRONMENT,
                    site_root=str(ROOT/SITE) if phase=='prepare' else None,generated_root=generated_root,
                    scratch_bytes=limits['scratch_bytes'])
                bounds.write_new(output/'invocation.json',dict(command=command,configuration_sha256=digest(raw)))
                observed=bounds.supervised(command,output/'logs',cwd=ROOT,normal_deadline=deadline,
                    hard_deadline=started+limits['child_hard_seconds'],rss_bytes=limits['rss_bytes'],
                    output_bytes=limits['output_bytes'],min_free_bytes=limits['min_free_bytes'],
                    max_processes=limits['max_processes'],output_root=output,guard_state=state,
                    output_namespace_limits=(128,16),log_mode='direct',
                    process_scope='descendants' if phase=='qualify' else 'group')
                bounds.write_new(output/'supervision.json',observed)
                if observed['status']!='completed':raise ValueError('CPU '+phase+' worker failed; retained logs are authoritative')
                if phase=='prepare':
                    stage_receipt=decode(read(output/'payload/stage.json',MiB))
                    dependency_raw=read(output/'payload/dependencies.json',16*MiB,stage_receipt['dependencies']['sha256'])
                    if stage_receipt.get('status')!='prepared':raise ValueError('CPU staging terminal differs')
                    verify_staged_roots(str(stage),decode(dependency_raw),stage_receipt['staged_roots'])
                    result.update(status='prepared',stage_parent=str(stage),dependencies=stage_receipt['dependencies'],
                        staged_roots=stage_receipt['staged_roots'],sources=config['sources'],inputs=config['inputs'])
                else:
                    worker_result=decode(read(output/'logs/stdout.log',MiB))
                    validate_worker_result(worker_result,registration_sha256=digest(worker_raw),dependency_sha256=digest(dependency_raw),
                        dependencies=decode(dependency_raw),negative_imports=config['negative_imports'])
                    verify_staged_roots(str(stage),dependencies,prep['staged_roots'])
                    result.update(status='imports_completed',held_four_imports_observed=True,worker_stdout_sha256=digest(read(output/'logs/stdout.log',MiB)))
                native_checks()
                baseline_after=baseline_api.verify_baseline(baseline,deadline)
                if baseline_before!=baseline_after:raise ValueError('Original trusted CPU baseline changed')
                bounds.write_new(output/'baseline-after.json',baseline_after)
                inputs.recheck()
    except Exception as error:result.update(status='FAIL',error_type=type(error).__name__,error=str(error))
    result['closure']=closure(before_fds);result['elapsed_seconds']=time.monotonic()-started
    if time.monotonic()>=deadline:raise TimeoutError('CPU allocation normal return deadline')
    bounds.write_new(output/'result.json',result)
    closure(before_fds)
    if time.monotonic()>=deadline:raise TimeoutError('CPU publication return deadline')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--configuration',required=True,type=Path);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();started=time.monotonic()
    if os.getpgrp()!=os.getpid():os.setsid()
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,200)
    try:
        raw=read(args.configuration,MiB,args.sha256);config=decode(raw);validate_configuration(config)
        if canonical(config)!=raw:raise ValueError('Canonical CPU configuration bytes required')
        for row in config['sources']:
            if len(read(ROOT/row['path'],MiB,row['sha256']))!=row['size_bytes']:raise ValueError('CPU frozen source size differs')
        if (str(Path(sys.executable).resolve())!=PYTHON or not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode)
                or os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH')):
            raise ValueError('Original isolated CPU parent interpreter required')
        if os.path.lexists(ROOT/allocation_output(config)):raise FileExistsError('CPU allocation already reserved')
        sys.pycache_prefix=str(ROOT/allocation_output(config)/'unused-parent-pycache')
        for key in ('NOFILE','AS','FSIZE'):
            value=config['limits'][{'NOFILE':'max_fds','AS':'address_space_bytes','FSIZE':'file_bytes'}[key]]
            resource.setrlimit(getattr(resource,'RLIMIT_'+key),(value,value))
        result=execute(config,raw,started)
        print(canonical(result).decode(),end='',flush=True)
        return 0 if result['status'] in ('prepared','imports_completed') and time.monotonic()<started+180 else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
