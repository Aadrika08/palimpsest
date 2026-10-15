"""One frozen ordinary CPU import observation; no held-runtime qualification."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUTPUT='runs/puck-cpu-runtime-characterization-02'
SITE='runs/puck-cpu-install-01/site'
WORKER='scripts/characterize_puck_runtime_imports.py'
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
ACCEPTED_SHA='32605ca0d48537a6eabf98a54d605ad23bf525456760d83726381aeaf38e3e96'
ARCHIVE='docs/reports/puck-cpu-retained-admission-02'
PRIOR_ARCHIVE='docs/reports/puck-cpu-characterization-01'
PRIOR_PINS=dict(
    prior_configuration=dict(path=PRIOR_ARCHIVE+'/frozen-configuration.json',size_bytes=9898,
        sha256='b11daf4719daf3a838ece18cf6c0604875d3fcba65b0ab0b5354b9428be6b8ca'),
    prior_result=dict(path=PRIOR_ARCHIVE+'/raw/result.json',size_bytes=613,
        sha256='bd700625635bd47a170b70ce955097c47c0e4a27c1c3d9a04c137461d848288a'),
    prior_audit=dict(path=PRIOR_ARCHIVE+'/failure-audit-01.json',size_bytes=1509,
        sha256='26dd167d4d06ce4a8d45598a06dcd5c0e5a6c1b171550cfa11c0b039b655fbf9'))
NATIVE_METADATA_PIN=dict(path='docs/plans/puck-cpu-characterization-native-metadata-05.json',
    size_bytes=1618086,sha256='64a9e46f60700f12712262879547fbf26d785fb8a825098940e6494482dae2aa')
MiB=1024**2
VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',torchvision='0.24.0+cpu',mujoco='3.3.6')
ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',
    HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/scratch',PATH='/nonexistent',TZ='UTC',
    CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',
    OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0')
LIMITS=dict(normal_seconds=180,child_hard_seconds=190,hard_seconds=195,
    rss_bytes=1536*MiB,address_space_bytes=8192*MiB,output_bytes=64*MiB,
    scratch_bytes=64*MiB,file_bytes=8*MiB,min_free_bytes=4096*MiB,
    min_available_ram_bytes=2048*MiB,max_processes=3,max_fds=40000)
ROLES=dict(baseline='docs/plans/puck-python-louvain-host-baseline-v1.json',
    inventory='runs/puck-cpu-retained-admission-02/inventory.json',
    layout='docs/reports/puck-cpu-install-01/wheel-layout.json',
    accepted_result='runs/puck-cpu-retained-admission-02/result.json',
    accepted_snapshot='runs/puck-cpu-retained-admission-02/snapshot.json',
    accepted_audit=ARCHIVE+'/acceptance-audit-03.json',
    accepted_configuration='docs/plans/puck-cpu-retained-admission-02.json',
    accepted_index=ARCHIVE+'/evidence-index.json',
    native_metadata=NATIVE_METADATA_PIN['path'],
    **{role:row['path'] for role,row in PRIOR_PINS.items()})
SOURCES=tuple(sorted(('scripts/characterize_puck_cpu_runtime.py',WORKER,
    'scripts/build_puck_python_louvain.py','scripts/install_puck_cpu.py',
    'scripts/acquire_puck_cpu_payloads.py',
    'scripts/admit_puck_retained_installation.py','src/palimpsest/__init__.py',
    'src/palimpsest/bounded_qualification.py','src/palimpsest/evaluate.py',
    'src/palimpsest/puck_execution_files.py','src/palimpsest/puck_retained_installation.py',
    'src/palimpsest/puck_build_inputs.py','src/palimpsest/puck_package_payloads.py',
    'docs/plans/puck-cpu-characterization-v2.md')))
PRIOR_SOURCES=tuple(path.replace('puck-cpu-characterization-v2.md','puck-cpu-characterization-v1.md')
                    for path in SOURCES)
ROSTER_OUTPUT='runs/puck-cpu-runtime-characterization-03'
OBSERVATION_ARCHIVE='docs/reports/puck-cpu-characterization-02'
OBSERVATION_PINS=dict(
    observation_configuration=dict(path=OBSERVATION_ARCHIVE+'/frozen-configuration.json',size_bytes=13940,
        sha256='4b98ff368e97351b2079ff44c75cb910d08559e5e037a6afc4887c28cd38fea8'),
    observation_result=dict(path=OBSERVATION_ARCHIVE+'/raw/result.json',size_bytes=837,
        sha256='c3959dbb45d760c59e953caf11d05993c97c0d3912a801d957cf6f8dcbcfb3ff'),
    observation_report=dict(path=OBSERVATION_ARCHIVE+'/raw/payload/imports.json',size_bytes=534299,
        sha256='f5c307bd361cd97e0f5a912610e2e639d62aa410aca4c393719667b24654b448'),
    observation_audit=dict(path=OBSERVATION_ARCHIVE+'/outcome-audit-02.json',size_bytes=1452,
        sha256='68db69256149ca20d4b698860898d33c4e6cbee2b840e4eeeb2fd5f21359eff3'),
    observation_index=dict(path=OBSERVATION_ARCHIVE+'/evidence-index.json',size_bytes=17046,
        sha256='c827dc11dd3bcfe60a3020dccc008c385c779f19f60ad2bf6f930d69fcd654da'),
    observation_terminal=dict(path=OBSERVATION_ARCHIVE+'/external-terminal-observations.json',size_bytes=1170,
        sha256='32ed28951e741dc00de6daa9f168347520361b17d26f99ee908e0b1eef1162c5'))
DISTRIBUTED_PROPOSAL_PIN=dict(
    path='docs/reports/puck-cpu-export-phase-preflight-v1/notes/distributed-rosters/review.json',
    size_bytes=11683,sha256='de1aa2a7c7a0832b59f72cc07ffee5965a37657618ef8f70ea8f08238a815e04')
ROSTER_ROLES=dict(ROLES,**{role:row['path'] for role,row in OBSERVATION_PINS.items()},
    distributed_proposal=DISTRIBUTED_PROPOSAL_PIN['path'])
ROSTER_SOURCES=tuple(sorted(set(SOURCES)-{'docs/plans/puck-cpu-characterization-v2.md'}|{
    'docs/plans/puck-cpu-distributed-roster-observation-01-proposal.md',
    'scripts/observe_puck_cpu_runtime_characterization.py',
    'scripts/audit_puck_cpu_runtime_characterization.py',
    *(OBSERVATION_ARCHIVE+'/'+name for name in ('audit-support-characterization-v1.py',
        'audit-helper-install-v1.py','audit-helper-admission-v3.py'))}))
DISTRIBUTED_NAMES=tuple('torch._C.'+suffix for suffix in (
    '_distributed_autograd','_distributed_c10d','_distributed_rpc'))
CLAIMS=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,
    study_authorized=False,executable=False,qualification_claims=[])
PROBE="""import json,os,pathlib,stat,sys
parent_net,site,hidden=sys.argv[1:]
assert os.readlink('/proc/self/ns/net')!=parent_net
assert all(not line.split() or line.split()[0] in ('Iface','lo') for line in pathlib.Path('/proc/net/route').read_text().splitlines())
assert all(line.split()[-1]=='lo' for line in pathlib.Path('/proc/net/ipv6_route').read_text().splitlines() if line.split())
assert os.statvfs(site).f_flag & os.ST_RDONLY
assert not pathlib.Path(hidden).exists()
assert not pathlib.Path('/scratch/pycache').stat().st_mode & 0o077
assert not list(pathlib.Path('/scratch/pycache').iterdir())
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert sys.pycache_prefix=='/scratch/pycache'
p=pathlib.Path('/scratch/tmp/probe');p.write_bytes(b'bounded');p.unlink()
print(json.dumps(dict(kind='cpu-characterization-namespace-v1',network_isolated=True,site_readonly=True,project_hidden=True,private_pycache_empty=True)))
"""


def fingerprint(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)


def read(path,maximum):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=maximum:
            raise ValueError('Bounded single-link input required')
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(maximum+1)
        if (len(raw)!=before.st_size or fingerprint(os.fstat(fd))!=fingerprint(before)
                or fingerprint(Path(path).lstat())!=fingerprint(before)):
            raise ValueError('Input changed while read')
        return raw
    finally:os.close(fd)


def validate_configuration(config):
    if type(config) is dict and config.get('kind')=='puck-cpu-runtime-characterization-v2':
        if (set(config)!={'kind','version','output','site_root','sources','inputs','roles','limits','environment','expected_versions'}
                or type(config.get('version')) is not int or config['version']!=2
                or config.get('output')!=ROSTER_OUTPUT or config.get('site_root')!=SITE
                or config.get('roles')!=ROSTER_ROLES or config.get('limits')!=LIMITS
                or config.get('environment')!=ENVIRONMENT or config.get('expected_versions')!=VERSIONS
                or type(config.get('sources')) is not list):
            raise ValueError('Exact distributed CPU characterization configuration required')
        for row in config['sources']:
            if (type(row) is not dict or set(row)!={'path','size_bytes','sha256'}
                    or type(row['size_bytes']) is not int or not 0<row['size_bytes']<=MiB
                    or type(row['sha256']) is not str or len(row['sha256'])!=64
                    or any(c not in '0123456789abcdef' for c in row['sha256'])):
                raise ValueError('Exact distributed CPU source pin required')
        if tuple(row['path'] for row in config['sources'])!=ROSTER_SOURCES:
            raise ValueError('Exact distributed CPU source closure required')
        if config['inputs']!=required_roster_input_rows(read_observation_configuration()):
            raise ValueError('Exact distributed CPU characterization input closure required')
        return
    if (set(config)!={'kind','version','output','site_root','sources','inputs','roles','limits','environment','expected_versions'}
            or type(config.get('version')) is not int or config.get('kind')!='puck-cpu-runtime-characterization-v1' or config.get('version')!=1
            or config.get('output')!=OUTPUT or config.get('site_root')!=SITE
            or config.get('roles')!=ROLES or config.get('limits')!=LIMITS
            or config.get('environment')!=ENVIRONMENT or config.get('expected_versions')!=VERSIONS
            or tuple(row['path'] for row in config['sources'])!=SOURCES):
        raise ValueError('Exact CPU characterization configuration required')
    if config['inputs']!=required_input_rows(read_prior_configuration()):
        raise ValueError('Exact CPU characterization input closure required')


def read_observation_configuration():
    row=OBSERVATION_PINS['observation_configuration'];raw=read(ROOT/row['path'],MiB)
    if len(raw)!=row['size_bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
        raise ValueError('Frozen observation02 configuration bytes differ')
    return json.loads(raw)


def required_roster_input_rows(observation):
    if (type(observation) is not dict or observation.get('kind')!='puck-cpu-runtime-characterization-v1'
            or observation.get('output')!=OUTPUT):
        raise ValueError('Frozen observation02 scope differs')
    validate_configuration(observation)
    rows={row['path']:dict(row) for row in observation['inputs']}
    rows.update((row['path'],dict(row)) for row in OBSERVATION_PINS.values())
    rows[DISTRIBUTED_PROPOSAL_PIN['path']]=dict(DISTRIBUTED_PROPOSAL_PIN)
    for row in observation['sources']:
        path=OBSERVATION_ARCHIVE+'/source/'+row['path'];rows[path]=dict(row,path=path)
    if len(rows)!=63:raise ValueError('Distributed CPU input closure differs')
    return [rows[path] for path in sorted(rows)]


def distributed_expected(proposal):
    acceptance=proposal.get('acceptance',{})
    if (proposal.get('kind')!='distributed-export-prospective-roster-review-v1'
            or proposal.get('upstream_commit')!='0fabc3ba44823f257e70ce397d989c8de5e362c1'
            or proposal.get('proposal_counts')!={'autograd':11,'c10d':69,'rpc':29}
            or set(acceptance)!={'actual_configuration_created','collection_authorized','dispatch_roster_observed',
                'executable','native_authorized','qualification_claims','replacement_phase_accepted',
                'runtime_qualified','study_authorized'}
            or any(acceptance[k] is not False for k in acceptance if k!='qualification_claims')
            or acceptance['qualification_claims']!=[]
            or type(proposal.get('proposed_rows')) is not dict
            or set(proposal['proposed_rows'])!={'autograd','c10d','rpc'}):
        raise ValueError('Exact prospective distributed source proposal required')
    expected={}
    for key,name,producer in zip(('autograd','c10d','rpc'),DISTRIBUTED_NAMES,
            ('torch.distributed.autograd','torch.distributed','torch.distributed.rpc'),strict=True):
        row=proposal['proposed_rows'][key];names=row.get('delegate_attributes')
        if (set(row)!={'name','producer','phase','attributes','class_binding','delegate_attributes'}
                or row['name']!=name or row['producer']!=producer or row['phase']!='module_exec_publish'
                or row['attributes']!=name.split('.') or row['class_binding'] is not None
                or type(names) is not list or len(names)!=proposal['proposal_counts'][key]
                or any(type(item) is not str or not item or len(item)>512 or '\0' in item for item in names)
                or names!=sorted(set(names))):
            raise ValueError('Distributed proposal target, phase or bounded names differ')
        expected[name]=list(names)
    return expected


def read_prior_configuration():
    row=PRIOR_PINS['prior_configuration'];raw=read(ROOT/row['path'],MiB)
    if len(raw)!=row['size_bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
        raise ValueError('Frozen prior configuration bytes differ')
    return json.loads(raw)


def required_input_rows(prior):
    """Derive this epoch's 12 role pins and 16+14 historical source pins."""
    prior_roles={role:path for role,path in ROLES.items() if role not in PRIOR_PINS}
    prior_roles['native_metadata']='docs/plans/puck-cpu-characterization-native-metadata-04.json'
    if (prior.get('kind')!='puck-cpu-runtime-characterization-v1' or type(prior.get('version')) is not int
            or prior['version']!=1 or prior.get('output')!='runs/puck-cpu-runtime-characterization-01'
            or prior.get('site_root')!=SITE or prior.get('roles')!=prior_roles
            or prior.get('limits')!=LIMITS or prior.get('environment')!=ENVIRONMENT
            or prior.get('expected_versions')!=VERSIONS
            or tuple(row['path'] for row in prior['sources'])!=PRIOR_SOURCES):
        raise ValueError('Frozen prior characterization configuration differs')
    old_inputs={row['path']:row for row in prior['inputs']}
    accepted_caps={path for path in old_inputs if path.startswith(ARCHIVE+'/source/')}
    if (len(prior['inputs'])!=25 or len(accepted_caps)!=16
            or set(old_inputs)!=set(prior_roles.values())|accepted_caps):
        raise ValueError('Frozen prior characterization input closure differs')
    rows={path:dict(row) for path,row in old_inputs.items() if path!=prior_roles['native_metadata']}
    rows[NATIVE_METADATA_PIN['path']]=dict(NATIVE_METADATA_PIN)
    rows.update((row['path'],dict(row)) for row in PRIOR_PINS.values())
    for row in prior['sources']:
        path=PRIOR_ARCHIVE+'/source/'+row['path'];rows[path]=dict(row,path=path)
    if len(rows)!=42:raise ValueError('CPU characterization input closure differs')
    return [rows[path] for path in sorted(rows)]


def validate_prior_characterization(config,result,audit,pins):
    for row in required_input_rows(config):
        if pins.get(row['path'])!=row:
            raise ValueError('Prior characterization input pins differ')
    prior_sha=PRIOR_PINS['prior_configuration']['sha256']
    closure=result.get('closure',{});elapsed=result.get('elapsed_seconds')
    verified=audit.get('verified',{})
    if (result.get('kind')!='puck-cpu-characterization-outcome-v1' or result.get('status')!='FAIL'
            or result.get('configuration_sha256')!=prior_sha
            or result.get('error_type')!='RuntimeError' or result.get('error')!='CPU worker did not complete normally'
            or any(result.get(key) is not False for key in CLAIMS if key!='qualification_claims')
            or result.get('qualification_claims')!=[]
            or type(elapsed) not in (int,float) or not 0<elapsed<LIMITS['normal_seconds']
            or closure.get('active_children')!=[] or closure.get('active_non_main_threads')!=[]
            or closure.get('all_handles_closed') is not True or closure.get('all_receipts_fsynced') is not True
            or type(closure.get('fd_count_before')) is not int or closure['fd_count_before']<0
            or type(closure.get('fd_count_after')) is not int or closure['fd_count_before']!=closure['fd_count_after']
            or audit.get('kind')!='cpu-characterization-independent-failure-audit-v1'
            or audit.get('status')!='PRESERVED_FAILURE_VERIFIED'
            or any(audit.get(key) is not False for key in (*CLAIMS,'native_qualified','ordinary_imports_observed','target_code_executed_by_auditor') if key!='qualification_claims')
            or audit.get('qualification_claims')!=[] or verified.get('configuration_sha256')!=prior_sha
            or verified.get('parent_result_sha256')!=PRIOR_PINS['prior_result']['sha256']
            or type(verified.get('worker_returncode')) is not int or verified['worker_returncode']!=1
            or 'worker_failure' not in verified or verified['worker_failure'] is not None
            or verified.get('first_import')!='numpy'
            or verified.get('reported_error_type')!='builtins.ImportError'
            or verified.get('source_pins')!=14 or verified.get('input_pins')!=25
            or verified.get('archived_acceptance_source_pins')!=16):
        raise ValueError('Prior characterization must retain its exact normal failed outcome')


def validate_observation02(config,result,report,audit,index,terminal,pins):
    for row in required_roster_input_rows(config):
        if pins.get(row['path'])!=row:
            raise ValueError('Observation02 historical input pin differs')
    config_sha=OBSERVATION_PINS['observation_configuration']['sha256']
    report_sha=OBSERVATION_PINS['observation_report']['sha256']
    closure=result.get('closure',{});verified=audit.get('verified',{})
    if (result.get('kind')!='puck-cpu-characterization-outcome-v1' or result.get('status')!='observed'
            or result.get('configuration_sha256')!=config_sha or result.get('report_sha256')!=report_sha
            or any(k in result for k in ('error','error_type'))
            or any(result.get(k) is not False for k in CLAIMS if k!='qualification_claims')
            or result.get('qualification_claims')!=[] or result.get('versions')!=VERSIONS
            or result.get('namespace_probe_completed') is not True
            or result.get('accepted_package_preparation_preserved') is not True
            or result.get('worker_supervision_status')!='completed'
            or not finite(result.get('elapsed_seconds'),LIMITS['normal_seconds'])
            or closure.get('active_children')!=[] or closure.get('active_non_main_threads')!=[]
            or closure.get('all_handles_closed') is not True or closure.get('all_receipts_fsynced') is not True
            or type(closure.get('fd_count_before')) is not int or closure['fd_count_before']<0
            or type(closure.get('fd_count_after')) is not int or closure['fd_count_after']!=closure['fd_count_before']
            or report.get('kind')!='puck-runtime-import-characterization-result-v3'
            or type(report.get('version')) is not int or report['version']!=3
            or report.get('profile')!='cpu-four-imports-v1' or report.get('status')!='observed'
            or report.get('versions')!=VERSIONS or report.get('expected_versions')!=VERSIONS
            or report.get('observation_errors')!=[] or report.get('environment_delta') is not None
            or report.get('observation_scope')!='completed_imports' or 'error' in report
            or any(report.get(k) is not False for k in CLAIMS if k!='qualification_claims')
            or report.get('qualification_claims')!=[]
            or audit.get('kind')!='cpu-characterization-independent-outcome-audit-v2'
            or audit.get('status')!='PASS' or audit.get('expected_outcome')!='success'
            or type(audit.get('caller_supplied_observed_parent_exit_code')) is not int
            or audit['caller_supplied_observed_parent_exit_code']!=0
            or audit.get('ordinary_imports_observed') is not True
            or any(audit.get(k) is not False for k in (*CLAIMS,'native_qualified','target_code_executed_by_auditor') if k!='qualification_claims')
            or audit.get('qualification_claims')!=[]
            or any(verified.get(k)!=v for k,v in dict(configuration_sha256=config_sha,report_sha256=report_sha,
                result_sha256=OBSERVATION_PINS['observation_result']['sha256'],source_pins=14,input_pins=42,
                accepted_source_capsules=16,prior_source_capsules=14,parent_status='observed',
                worker_status='observed',worker_returncode=0,baseline_after_present=True).items())
            or index.get('kind')!='cpu-characterization-evidence-index-v2'
            or index.get('actual_retry_performed') is not False or index.get('original_output')!=OUTPUT
            or terminal.get('kind')!='cpu-characterization-external-terminal-observations-v2'
            or terminal.get('configuration_sha256')!=config_sha or terminal.get('actual_retry_performed') is not False
            or type(terminal.get('actual',{}).get('exit_code')) is not int or terminal['actual']['exit_code']!=0
            or terminal.get('outcome_audit',{}).get('status')!='PASS'
            or type(terminal['outcome_audit'].get('exit_code')) is not int or terminal['outcome_audit']['exit_code']!=0):
        raise ValueError('Observation02 must retain its exact scoped normal success')


def finite(value,maximum):
    return type(value) in (int,float) and math.isfinite(value) and 0<=value<maximum


def validate_distributed_report(report,request_sha,worker_sha,expected):
    fields={'kind','version','status','request_sha256','source_sha256','environment_sha256',
        'python_version','executable_path','pid','ppid','runtime_qualified','collection_authorized',
        'executable','qualification_claims','versions','imports','cache','maps','baseline_maps',
        'environment_delta','observation_errors','profile','expected_versions','pycache_prefix',
        'native_authorized','study_authorized','distributed_exports','observation_scope','seconds'}
    if (type(report) is not dict or set(report)!=fields
            or report['kind']!='puck-runtime-import-characterization-result-v4'
            or type(report['version']) is not int or report['version']!=4
            or report['profile']!='cpu-distributed-terminal-v1' or report['status']!='observed'
            or report['request_sha256']!=request_sha or report['source_sha256']!=worker_sha
            or report['versions']!=VERSIONS or report['expected_versions']!=VERSIONS
            or any(report[k] is not False for k in CLAIMS if k!='qualification_claims')
            or report['qualification_claims']!=[] or report['observation_errors']!=[]
            or report['environment_delta'] is not None or report['observation_scope']!='completed_imports'
            or report['pycache_prefix']!='/scratch/pycache' or report['executable_path']!=PYTHON
            or report['environment_sha256']!=hashlib.sha256((json.dumps(ENVIRONMENT,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
            or type(report['python_version']) is not str or not report['python_version'].startswith('3.11.15 ')
            or len(report['python_version'])>4096 or type(report['pid']) is not int or report['pid']<=0
            or type(report['ppid']) is not int or report['ppid']<0
            or not finite(report['seconds'],LIMITS['normal_seconds'])
            or type(report['imports']) is not list or len(report['imports'])!=4):
        raise ValueError('Complete fixed CPU distributed import report required')
    for row,name in zip(report['imports'],VERSIONS,strict=True):
        if (type(row) is not dict or set(row)!={'name','status','seconds','cache_entries'}
                or row['name']!=name or row['status']!='observed'
                or not finite(row['seconds'],LIMITS['normal_seconds'])
                or type(row['cache_entries']) is not int or not 0<=row['cache_entries']<=8192):
            raise ValueError('Complete ordered CPU imports required')
    if (type(report['cache']) is not dict or type(report['maps']) is not dict
            or type(report['baseline_maps']) is not dict):
        raise ValueError('Complete independent cache/maps observations required')
    value=report['distributed_exports']
    if (type(value) is not dict or set(value)!={'kind','version','capture_point','stable',
            'profile_accepted','runtime_qualified','modules'}
            or value['kind']!='puck-cpu-distributed-exports-v1' or type(value['version']) is not int
            or value['version']!=1 or value['capture_point']!='after_four_fixed_imports'
            or value['stable'] is not True or value['profile_accepted'] is not False
            or value['runtime_qualified'] is not False or type(value['modules']) is not list
            or len(value['modules'])!=3 or set(expected)!=set(DISTRIBUTED_NAMES)):
        raise ValueError('Complete stable fixed distributed projection required')
    def text(item,maximum=4096):
        if item is not None and (type(item) is not str or len(item)>maximum or '\0' in item):
            raise ValueError('Bounded distributed metadata text required')
    def paths(items):
        if type(items) is not list or len(items)>128 or any(type(item) is not str for item in items):
            raise ValueError('Bounded distributed metadata paths required')
        for item in items:text(item)
    for row,name in zip(value['modules'],DISTRIBUTED_NAMES,strict=True):
        if (type(row) is not dict or set(row)!={'name','raw_attribute_identity','cache_identity',
                'metadata','delegate_attributes','comparison'} or row['name']!=name
                or row['raw_attribute_identity'] is not True or row['cache_identity'] is not True):
            raise ValueError('Exact distributed target and identity required')
        names=row['delegate_attributes'];metadata=row['metadata'];comparison=row['comparison']
        if (type(names) is not list or len(names)>4096
                or any(type(item) is not str or not item or len(item)>512 or '\0' in item for item in names)
                or names!=sorted(set(names))):
            raise ValueError('Bounded sorted distinct observed dispatch required')
        missing=sorted(set(expected[name])-set(names));extra=sorted(set(names)-set(expected[name]))
        if (type(comparison) is not dict or set(comparison)!={'expected','missing','extra','matches'}
                or comparison['expected']!=expected[name] or comparison['missing']!=missing
                or comparison['extra']!=extra or type(comparison['matches']) is not bool
                or comparison['matches']!=(not missing and not extra)):
            raise ValueError('Exact distributed source comparison required')
        if (type(metadata) is not dict or set(metadata)!={'name','module_type','file','package','loader_type','spec','path'}
                or metadata['name']!=name or metadata['module_type']!='builtins.module'):
            raise ValueError('Exact distributed metadata required')
        text(metadata['file']);text(metadata['package']);text(metadata['loader_type'],512);paths(metadata['path'])
        spec=metadata['spec']
        if spec is not None:
            if type(spec) is not dict or set(spec)!={'name','origin','loader_type','submodule_search_locations'}:
                raise ValueError('Exact distributed spec metadata required')
            text(spec['name'],512);text(spec['origin']);text(spec['loader_type'],512)
            if spec['submodule_search_locations'] is not None:paths(spec['submodule_search_locations'])
    if (len((json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())>256*1024
            or len((json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())>MiB):
        raise ValueError('Distributed projection/report exceeds byte bounds')


def validate_native_metadata(native):
    if (native.get('kind')!='puck-cpu-characterization-native-metadata-v5'
            or native.get('root_scope')!='installed_shared_objects_and_interpreter'
            or native.get('errors')!=[] or native.get('oversized_native_files')!=[]
            or native.get('status')!='COMPLETE' or native.get('required_missing_names')!=[]
            or type(native.get('native_files')) is not list or not 1<=len(native['native_files'])<=128
            or type(native.get('aliases')) is not list or len(native['aliases'])>256):
        raise ValueError('Incomplete native metadata cannot define a mount set')
    seen=set()
    for row in native['native_files']:
        path=row['path']
        if (type(path) is not str or not (path.startswith('/usr/lib/') or path in ('/usr/bin/ldconfig','/etc/ld.so.cache'))
                or str(Path(path))!=path or '..' in Path(path).parts or path in seen
                or type(row['size_bytes']) is not int or not 0<=row['size_bytes']<=64*MiB
                or type(row['sha256']) is not str or len(row['sha256'])!=64
                or any(c not in '0123456789abcdef' for c in row['sha256'])):
            raise ValueError('Unsupported native metadata file')
        seen.add(path)


def sandbox_command(baseline,native,payload,request,*,probe=False):
    cmd=['/usr/bin/bwrap','--unshare-all','--unshare-user','--as-pid-1',
        '--disable-userns','--die-with-parent','--cap-drop','ALL','--clearenv',
        '--hostname','palimpsest-cpu-observation','--ro-bind',baseline['python_prefix'],baseline['python_prefix']]
    paths={row['path'] for row in native['native_files']}
    for row in baseline['external_libraries']:paths.add((row.get('realpath') or row['path']))
    for path in sorted(paths):cmd+=['--ro-bind',path,path]
    aliases=dict(baseline['host_path_aliases'])
    for path,target in native['aliases']:
        if path in aliases and aliases[path]!=target:raise ValueError('Conflicting host alias')
        aliases[path]=target
    for path,target in sorted(aliases.items(),key=lambda item:(item[0].count('/'),item[0])):
        cmd+=['--symlink',target,path]
    cmd+=['--ro-bind',str(ROOT/SITE),str(ROOT/SITE),'--ro-bind',str(ROOT/WORKER),'/driver.py',
        '--ro-bind',str(request),'/request.json','--bind',str(payload),'/output',
        '--size',str(LIMITS['scratch_bytes']),'--tmpfs','/scratch']
    for name in ('home','tmp','pycache'):cmd+=['--dir','/scratch/'+name,'--chmod','0700','/scratch/'+name]
    cmd+=['--symlink','scratch/tmp','/tmp','--proc','/proc','--remount-ro','/proc',
        '--dev','/dev','--remount-ro','/dev','--remount-ro','/']
    for key,value in ENVIRONMENT.items():cmd+=['--setenv',key,value]
    cmd+=['--chdir','/scratch',PYTHON,'-I','-S','-B','-X','pycache_prefix=/scratch/pycache']
    return cmd+(['-c',PROBE,os.readlink('/proc/self/ns/net'),str(ROOT/SITE),str(ROOT/'docs')]
                if probe else ['/driver.py','/request.json',hashlib.sha256(request.read_bytes()).hexdigest()])


def execute(config,digest,started):
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
    import build_puck_python_louvain as build
    from palimpsest import bounded_qualification as bounds
    from palimpsest.puck_retained_installation import AdmissionInputs,HeldInstalledFiles
    from admit_puck_retained_installation import completion_state
    roster=config['kind']=='puck-cpu-runtime-characterization-v2'
    roles=ROSTER_ROLES if roster else ROLES
    output=ROOT/config['output'];deadline=started+LIMITS['normal_seconds'];state={};result=dict(CLAIMS)
    rows=sorted(config['sources']+config['inputs']+[config['_configuration_row']],key=lambda r:r['path'])
    limits=resource.getrlimit(resource.RLIMIT_NOFILE)
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    if (min(limits)<LIMITS['max_fds'] or available<LIMITS['min_available_ram_bytes']
            or shutil.disk_usage(ROOT).free<LIMITS['min_free_bytes']):
        raise ValueError('CPU characterization resource admission failed')
    resource.setrlimit(resource.RLIMIT_NOFILE,(LIMITS['max_fds'],LIMITS['max_fds']))
    resource.setrlimit(resource.RLIMIT_AS,(LIMITS['address_space_bytes'],LIMITS['address_space_bytes']))
    resource.setrlimit(resource.RLIMIT_FSIZE,(LIMITS['file_bytes'],LIMITS['file_bytes']))
    with AdmissionInputs(ROOT,rows,deadline):pass
    bounds.reserve_output(output,{'sources':{'root':str(ROOT),'files':rows},'installed':{'root':str(ROOT/SITE)}})
    for name in ('payload','probe-logs','worker-logs'):(output/name).mkdir(mode=0o700)
    bounds.write_new(output/'configuration.json',{k:v for k,v in config.items() if not k.startswith('_')})
    before_fds=len(os.listdir('/proc/self/fd'))
    result.update(kind='puck-cpu-characterization-outcome-v2' if roster else 'puck-cpu-characterization-outcome-v1',
        status='FAIL',configuration_sha256=digest)
    last=[0.];parent_peak=[0]
    def check():
        now=time.monotonic()
        if now>=deadline:raise TimeoutError('CPU characterization normal deadline')
        if now-last[0]<.05:return
        last[0]=now
        parent_rss=int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
        parent_peak[0]=max(parent_peak[0],parent_rss)
        if parent_rss>LIMITS['rss_bytes']:raise ValueError('CPU parent sampled RSS stop')
        if (shutil.disk_usage(ROOT).free<LIMITS['min_free_bytes'] or
                bounds._output_bytes(output,max_files=64,max_directories=8)>LIMITS['output_bytes']):
            raise ValueError('CPU characterization disk/output limit')
    try:
        with bounds.hard_guard(started+LIMITS['hard_seconds'],state):
            with AdmissionInputs(ROOT,rows,deadline) as inputs:
                get=lambda role:inputs.read_json(roles[role])
                old,audit,snapshot,accepted=(get(role) for role in ('accepted_result','accepted_audit','accepted_snapshot','accepted_configuration'))
                pins={row['path']:row for row in rows}
                validate_prior_characterization(*(get(role) for role in ('prior_configuration','prior_result','prior_audit')),pins)
                def observation_history():
                    if roster:
                        validate_observation02(*(get(role) for role in ('observation_configuration','observation_result',
                            'observation_report','observation_audit','observation_index','observation_terminal')),pins)
                observation_history()
                if (old['status']!='PASS' or old['claims']['package_preparation_accepted'] is not True
                        or any(old['claims'].get(k) is not False for k in ('runtime_qualified','numerical_imports_executed','study_authorized','collection_authorized'))
                        or audit['status']!='PASS' or audit['package_preparation_accepted'] is not True
                        or old['configuration_sha256']!=ACCEPTED_SHA or audit['verified']['configuration_sha256']!=ACCEPTED_SHA
                        or pins[ROLES['accepted_configuration']]['sha256']!=ACCEPTED_SHA
                        or old['snapshot_sha256']!=pins[ROLES['accepted_snapshot']]['sha256']
                        or snapshot['site_root']!=str(ROOT/SITE)):
                    raise ValueError('Accepted package preparation binding differs')
                for row in accepted['sources']:
                    archived=pins[ARCHIVE+'/source/'+row['path']]
                    if any(archived[k]!=row[k] for k in ('size_bytes','sha256')):raise ValueError('Historical frozen source differs')
                inventory,layout,baseline,native=(get(role) for role in ('inventory','layout','baseline','native_metadata'))
                validate_native_metadata(native)
                files=inventory['entries'];directories=layout['predicted_destination_directories']
                if len(files)!=27225 or len(directories)!=2074 or sum(r['size_bytes'] for r in files)!=1304701872:
                    raise ValueError('Accepted measured namespace differs')
                def native_checks():
                    if len(native['native_files'])>128 or len(native['aliases'])>256:raise ValueError('Native metadata bound')
                    for row in native['native_files']:
                        if not (row['path'].startswith('/usr/lib/') or row['path'] in ('/usr/bin/ldconfig','/etc/ld.so.cache')):
                            raise ValueError('Unexpected native input path')
                        if build.file_row(Path(row['path']),deadline,single_link=False)!={k:row[k] for k in ('size_bytes','sha256')}:
                            raise ValueError('Native input identity changed')
                    for path,target in native['aliases']:
                        if os.readlink(path)!=target:raise ValueError('Native alias changed')
                native_checks();before=build.verify_baseline(baseline,deadline)
                bounds.write_new(output/'baseline-before.json',before)
                with HeldInstalledFiles(ROOT/SITE,files,directories,deadline,check=check) as held:
                    request=dict(kind='puck-runtime-import-characterization-v2',version=2,
                        site_root=str(ROOT/SITE),output_root='/output',environment=ENVIRONMENT,
                        expected_versions=VERSIONS,pycache_prefix='/scratch/pycache')
                    if roster:
                        expected=distributed_expected(get('distributed_proposal'))
                        request.update(kind='puck-runtime-import-characterization-v3',version=3,distributed_expected=expected)
                    bounds.write_new(output/'request.json',request)
                    for probe,name in ((True,'probe'),(False,'worker')):
                        command=sandbox_command(baseline,native,output/'payload',output/'request.json',probe=probe)
                        bounds.write_new(output/(name+'-invocation.json'),dict(command=command,configuration_sha256=digest))
                        observed=bounds.supervised(command,output/(name+'-logs'),cwd=ROOT,
                            normal_deadline=deadline,hard_deadline=started+LIMITS['child_hard_seconds'],
                            rss_bytes=LIMITS['rss_bytes'],output_bytes=LIMITS['output_bytes'],
                            min_free_bytes=LIMITS['min_free_bytes'],max_processes=LIMITS['max_processes'],
                            output_root=output,output_namespace_limits=(64,8),guard_state=state,log_mode='direct')
                        bounds.write_new(output/(name+'-supervision.json'),observed)
                        if observed['status']!='completed':raise RuntimeError('CPU '+name+' did not complete normally')
                        if probe:
                            namespace=json.loads(read(output/'probe-logs/stdout.log',MiB))
                            if namespace!={'kind':'cpu-characterization-namespace-v1','network_isolated':True,'site_readonly':True,'project_hidden':True,'private_pycache_empty':True}:
                                raise ValueError('Namespace probe receipt differs')
                            bounds.write_new(output/'namespace.json',namespace)
                    report_raw=read(output/'payload/imports.json',MiB);report=json.loads(report_raw)
                    if roster:
                        if (json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()!=report_raw:
                            raise ValueError('Canonical distributed worker report required')
                        validate_distributed_report(report,hashlib.sha256(read(output/'request.json',MiB)).hexdigest(),
                            pins[WORKER]['sha256'],expected)
                    elif (report['kind']!='puck-runtime-import-characterization-result-v3' or report['status']!='observed'
                            or report['request_sha256']!=hashlib.sha256(read(output/'request.json',MiB)).hexdigest()
                            or report['source_sha256']!=pins[WORKER]['sha256']
                            or report['versions']!=VERSIONS or [r['name'] for r in report['imports']]!=list(VERSIONS)
                            or any(report.get(k) is not False for k in ('runtime_qualified','native_authorized','collection_authorized','study_authorized','executable'))
                            or report['qualification_claims']!=[]):raise ValueError('CPU import observation differs')
                    after=build.verify_baseline(baseline,deadline);native_checks()
                    if before!=after:raise ValueError('Trusted baseline changed')
                    bounds.write_new(output/'baseline-after.json',after)
                    validate_prior_characterization(*(get(role) for role in ('prior_configuration','prior_result','prior_audit')),pins)
                    observation_history()
                    held.recheck();inputs.recheck();check()
                    result.update(report_sha256=hashlib.sha256(read(output/'payload/imports.json',MiB)).hexdigest(),
                        versions=VERSIONS,namespace_probe_completed=True,worker_supervision_status=observed['status'],
                        accepted_package_preparation_preserved=True)
                inputs.recheck()
            result['status']='observed'
    except Exception as error:result.update(status='FAIL',error_type=type(error).__name__,error=str(error))
    result['closure']=completion_state(before_fds);result['elapsed_seconds']=time.monotonic()-started
    result['sampled_parent_peak_rss_bytes']=parent_peak[0]
    bounds.write_new(output/'result.json',result);check();completion_state(before_fds)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',required=True);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();started=time.monotonic()
    if os.getpgrp()!=os.getpid():os.setsid()
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,LIMITS['hard_seconds'])
    try:
        configuration=Path(args.configuration);raw=read(configuration,MiB)
        if hashlib.sha256(raw).hexdigest()!=args.sha256:raise ValueError('Configuration SHA differs')
        config=json.loads(raw);validate_configuration(config)
        if config['kind']=='puck-cpu-runtime-characterization-v2':
            if (str(configuration)!=args.configuration or not configuration.is_absolute()
                    or not configuration.is_relative_to(ROOT) or configuration.resolve(strict=True)!=configuration
                    or (json.dumps(config,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()!=raw):
                raise ValueError('Canonical root-contained frozen distributed configuration required')
        for row in config['sources']:
            source=read(ROOT/row['path'],MiB)
            if (hashlib.sha256(source).hexdigest()!=row['sha256']
                    or (config['kind']=='puck-cpu-runtime-characterization-v2' and len(source)!=row['size_bytes'])):
                raise ValueError('Trusted source differs')
        if (Path(sys.executable).resolve()!=Path(PYTHON) or not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode)
                or os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH')):
            raise ValueError('Original isolated CPU interpreter and loader environment required')
        if os.path.lexists(ROOT/config['output']):raise ValueError('CPU observation allocation already reserved')
        sys.pycache_prefix=str(ROOT/config['output']/'unused-parent-pycache')
        config['_configuration_row']=dict(path=configuration.relative_to(ROOT).as_posix(),size_bytes=len(raw),sha256=args.sha256)
        result=execute(config,args.sha256,started)
        print(json.dumps(result,sort_keys=True),flush=True)
        return 0 if (result['status']=='observed' and not any(k in result for k in ('error','error_type'))
                     and time.monotonic()-started<LIMITS['normal_seconds']) else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
