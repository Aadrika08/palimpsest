"""Explicit public-namespace/input authoring; no native/model imports or discovery.

Only execute-preparation hashes explicitly selected runtime/model files. The
caller meters the completed process (including this helper's final receipt I/O);
receipts retain sampled SELF plus waited CHILDREN CPU, including failures.
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
import subprocess
import sys
import time

MiB=1024**2
MAX_JSON_BYTES=2*MiB
MAX_OUTPUT_BYTES=8*MiB
MAX_INPUT_FILES=4096
MAX_INPUT_BYTES=64*1024**3
PLAN_NAME='project-completion-2026-11-05.md'
PUBLIC_RANGES=(('puck-collection',6110,6113),('puck-development',6120,6123),
    ('puck-held-out',6200,6207),('MaleCNS-development',3130,3133),
    ('MaleCNS-held-out',3120,3127),('conservative-training-seeds',10,12))
LIMITATIONS='ID/seed projection only; no geometry, pretraining, or sampling-disjointness claim'


class PreparationFailure(RuntimeError):
    """An irreversible failed preparation attempt retains its receipt/artifacts."""


def _hash(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}',value) is None:
        raise ValueError('Expected an externally pinned SHA256')
    return value


def _absolute(value):
    if type(value) is not str or not Path(value).is_absolute() or '..' in Path(value).parts:
        raise ValueError('Expected an explicit absolute path without parent traversal')
    return Path(value)


def _row(row):
    if type(row) is not dict or set(row)!={'path','sha256','size_bytes'}:
        raise ValueError('Malformed explicit descriptor')
    _absolute(row['path']); _hash(row['sha256'])
    if type(row['size_bytes']) is not int or not 0<=row['size_bytes']<=MAX_INPUT_BYTES:
        raise ValueError('Invalid bounded descriptor size')
    return copy.deepcopy(row)


def namespace_documents(approved_plan_descriptor):
    """Pure public-ID projection; the caller authenticates the supplied plan."""
    plan=_row(approved_plan_descriptor)
    reserved=sorted({seed for _,first,last in PUBLIC_RANGES for seed in range(first,last+1)})
    roots=[{'root_id':f'audit-navigation-{index+1}','scenario':'reproduction',
        'texture':'checker','seed':91001+index} for index in range(4)]
    source={'schema':'change-audit-public-namespace-source-v1','approved_plan':plan,
        'public_reserved_ranges':[{'cohort':cohort,'first_id':first,'last_id_inclusive':last}
            for cohort,first,last in PUBLIC_RANGES],
        'reserved_seed_ids':reserved,'candidate_roots':roots,'limitations':LIMITATIONS,
        'scope':'approved-public-cohort-ids-only','protected_catalogs_read':False}
    projection={'schema':'change-audit-pilot-namespace-projection-v1','roots':copy.deepcopy(roots),
        'reserved_seed_ids':list(reserved),'source':None,
        'scope':'approved-public-cohort-ids-only','protected_catalogs_read':False}
    return source,projection


def write_json(path,value):
    """Exclusive finite bounded JSON; retain any partial failed publication."""
    path=Path(path)
    payload=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if len(payload)>MAX_JSON_BYTES: raise ValueError('Control JSON exceeds 2MiB')
    with path.open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    descriptor=os.open(path.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
    try: os.fsync(descriptor)
    finally: os.close(descriptor)
    return {'path':str(path),'sha256':hashlib.sha256(payload).hexdigest(),'size_bytes':len(payload)}


def describe_file(path):
    """Hash one explicit file, canonicalizing a supplied symlink alias only."""
    resolved=_absolute(str(path)).resolve(strict=True)
    if not resolved.is_file(): raise ValueError('Explicit input must resolve to a regular file')
    with resolved.open('rb') as stream:
        before=os.fstat(stream.fileno())
        if before.st_size>MAX_INPUT_BYTES: raise ValueError('Explicit input exceeds 64GiB')
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
        after=os.fstat(stream.fileno())
    current=resolved.stat()
    identity=lambda state:(state.st_dev,state.st_ino,state.st_size,state.st_mtime_ns,state.st_ctime_ns)
    if identity(before)!=identity(after) or identity(before)!=identity(current):
        raise ValueError('Explicit input changed while hashing: '+str(resolved))
    return {'path':str(resolved),'sha256':digest,'size_bytes':before.st_size}


def source_state(repo,source_files):
    """Exact tracked Git HEAD; never enumerate untracked data or catalog contents."""
    repo=Path(repo)
    head=subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],check=True,
        capture_output=True,text=True).stdout.strip()
    dirty=subprocess.run(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],check=True,
        capture_output=True,text=True).stdout
    relative=[str(Path(path).relative_to(repo)) for path in source_files]
    tracked=subprocess.run(['git','-C',str(repo),'ls-files','--error-unmatch','--',*relative],
        capture_output=True,text=True)
    return {'head':head,'tracked_clean':not dirty,'selected_sources_tracked':tracked.returncode==0}


def _runtime_identity():
    return {'executable':str(Path(sys.executable).resolve(strict=True)),'version':sys.version,
        'scope':'current-interpreter-version-only'}


def _cpu():
    own=resource.getrusage(resource.RUSAGE_SELF); children=resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime+own.ru_stime+children.ru_utime+children.ru_stime


def _normalize_config(config):
    required={'repo_root','asset_root','prepared_graph_directory','source_commit','source_files',
        'runtime_files','model_files','python_executable'}
    if type(config) is not dict or set(config)!=required:
        raise ValueError('Preparation requires an exact explicit file-list configuration')
    if type(config['source_commit']) is not str or re.fullmatch('[0-9a-f]{40}',config['source_commit']) is None:
        raise ValueError('Exact full source HEAD required')
    result=copy.deepcopy(config); aliases=[]; seen=set(); total=0
    for key in ('repo_root','asset_root','prepared_graph_directory'):
        path=_absolute(config[key]).resolve(strict=True)
        if not path.is_dir(): raise ValueError('Explicit root must be an existing directory')
        result[key]=str(path)
    if not Path(result['prepared_graph_directory']).is_relative_to(result['asset_root']):
        raise ValueError('Prepared graph directory must be inside the explicit asset root')
    for group in ('source_files','runtime_files','model_files'):
        paths=config[group]
        if type(paths) is not list or not paths or len(paths)>MAX_INPUT_FILES:
            raise ValueError('Each explicit source/runtime/model list must be nonempty and bounded')
        normalized=[]
        for requested in paths:
            path=_absolute(requested).resolve(strict=True)
            if not path.is_file(): raise ValueError('Selected input is not a regular file')
            if path in seen: raise ValueError('Duplicate resolved explicit input: '+str(path))
            if group=='source_files' and not path.is_relative_to(result['repo_root']):
                raise ValueError('Selected project source escaped its pinned repository')
            seen.add(path); normalized.append(str(path)); total+=path.stat().st_size
            aliases.append({'requested':requested,'resolved':str(path)})
        result[group]=normalized
    if len(seen)>MAX_INPUT_FILES or total>MAX_INPUT_BYTES:
        raise ValueError('Explicit input inventory exceeds count/byte bounds')
    result['python_executable']=str(_absolute(config['python_executable']).resolve(strict=True))
    aliases.append({'requested':config['python_executable'],'resolved':result['python_executable']})
    return result,aliases


def roster_document(config,files,runtime_metadata):
    """Pure authoring of the exact pilot.py input-roster schema."""
    if type(files) is not list or not 1<=len(files)<=MAX_INPUT_FILES:
        raise ValueError('A bounded explicit descriptor roster is required')
    rows=[_row(row) for row in files]
    if len({row['path'] for row in rows})!=len(rows): raise ValueError('Duplicate roster descriptor')
    if sum(row['size_bytes'] for row in rows)>MAX_INPUT_BYTES: raise ValueError('Roster exceeds input-byte bound')
    if type(runtime_metadata) is not dict or not runtime_metadata:
        raise ValueError('Explicit limited runtime metadata required')
    return {'schema':'change-audit-input-roster-v1',
        **{key:config[key] for key in ('repo_root','asset_root','prepared_graph_directory','source_commit')},
        'files':sorted(rows,key=lambda row:row['path']),'runtime_metadata':copy.deepcopy(runtime_metadata)}


def _check_source(config,source_getter):
    expected={'head':config['source_commit'],'tracked_clean':True,'selected_sources_tracked':True}
    if source_getter(config['repo_root'],config['source_files'])!=expected:
        raise ValueError('Source must be exact clean HEAD with every selected source tracked')


def prepare(*,mode,output,approved_plan,expected_plan_sha256,config=None,config_path=None,expected_config_sha256=None,
            _source_state=source_state,_runtime_identity=_runtime_identity,_cpu=_cpu,_clock=time.monotonic):
    """One attempt. Actual preparation requires caller-finalized process accounting."""
    started,cpu_started=_clock(),_cpu()
    if mode not in ('plan-only','execute-preparation'): raise ValueError('Unknown preparation mode')
    output=_absolute(str(output))
    if any(path.is_symlink() for path in (output,*output.parents)): raise ValueError('Output cannot traverse symlinks')
    output.mkdir(parents=False,exist_ok=False)
    report={'schema':'change-audit-input-preparation-receipt-v1','mode':mode,'status':'failed',
        'research_execution_started':mode=='execute-preparation','protected_catalogs_read':False,
        'sampling_eligibility_verified':False,'certified_improvement':False,'runtime_qualification':False,
        'requires_parent_final_process_accounting':True,'cpu_accounting_complete':False,'errors':[],
        'accounting_scope':'delta RUSAGE_SELF plus waited RUSAGE_CHILDREN through final sample; caller must meter whole completed process including receipt I/O',
        'limits':{'max_input_files':MAX_INPUT_FILES,'max_input_bytes':MAX_INPUT_BYTES,
            'max_control_file_bytes':MAX_JSON_BYTES,'max_output_bytes':MAX_OUTPUT_BYTES}}
    used=0
    def publish(name,value):
        nonlocal used
        # Worst-case per-file pre-admission bounds this fresh output without a tree scan.
        if used+MAX_JSON_BYTES>MAX_OUTPUT_BYTES: raise ValueError('Preparation output exceeds 8MiB envelope')
        row=write_json(output/name,value); used+=row['size_bytes']; return row
    try:
        if config_path is not None:
            if mode!='execute-preparation' or config is not None or expected_config_sha256 is None:
                raise ValueError('Frozen config path is exclusive to explicit execute-preparation')
            config=_read_frozen(config_path,expected_config_sha256)
        elif expected_config_sha256 is not None:
            raise ValueError('Config checksum requires its explicit path')
        _hash(expected_plan_sha256)
        plan_path=_absolute(str(approved_plan))
        if plan_path.name!=PLAN_NAME or plan_path.parent.name!='plans' or plan_path.parent.parent.name!='docs':
            raise ValueError('Only the explicitly approved public completion plan is admitted')
        plan=describe_file(plan_path)
        if plan['sha256']!=expected_plan_sha256: raise ValueError('Externally pinned approved plan checksum differs')
        source,projection=namespace_documents(plan)
        report['namespace_source']=publish('namespace-source.json',source)
        projection['source']=report['namespace_source']
        report['namespace_projection']=publish('namespace-projection.json',projection)
        if mode=='plan-only':
            if config is not None: raise ValueError('Plan-only does not accept a runtime/model file list')
        else:
            normalized,aliases=_normalize_config(config)
            _check_source(normalized,_source_state)
            runtime=_runtime_identity()
            if (type(runtime) is not dict or set(runtime)!={'executable','version','scope'} or
                    str(_absolute(runtime['executable']).resolve(strict=True))!=normalized['python_executable'] or
                    type(runtime['version']) is not str or not runtime['version']):
                raise ValueError('Explicit Python identity must match the executing interpreter')
            descriptors=[]
            groups={}
            for group in ('source_files','runtime_files','model_files'):
                groups[group]=[describe_file(path) for path in normalized[group]]
                descriptors.extend(groups[group])
            python_descriptor=describe_file(normalized['python_executable'])
            for implicit in (python_descriptor,plan,report['namespace_source']):
                if not any(row['path']==implicit['path'] for row in descriptors): descriptors.append(implicit)
            metadata={'python':{**runtime,'file':python_descriptor},'explicit_runtime_files':groups['runtime_files'],
                'explicit_model_files':groups['model_files'],'explicit_source_files':groups['source_files'],
                'explicit_path_resolution':aliases,'dependency_completeness_claimed':False,
                'scope':'explicit selected file identities only; no package closure or runtime qualification claim'}
            roster=roster_document(normalized,descriptors,metadata)
            _check_source(normalized,_source_state)
            for row in descriptors:
                if describe_file(row['path'])!=row: raise ValueError('Explicit pinned input changed before publication')
            report['input_roster']=publish('input-roster.json',roster)
            report['source_commit']=normalized['source_commit']
        if describe_file(plan['path'])!=plan: raise ValueError('Approved public plan changed during preparation')
        if config_path is not None:
            _read_frozen(config_path,expected_config_sha256)
        report['status']='completed'
    except BaseException as error:
        report['errors'].append({'type':type(error).__name__,'message':str(error)[:2048]})
    report['observed_self_and_waited_children_cpu_seconds']=max(0.,_cpu()-cpu_started)
    report['observed_wall_seconds']=max(0.,_clock()-started)
    if not math.isfinite(report['observed_self_and_waited_children_cpu_seconds']) or not math.isfinite(report['observed_wall_seconds']):
        raise PreparationFailure('Nonfinite accounting; retained artifacts cannot authorize further preparation')
    publish('preparation-receipt.json',report)
    if report['status']!='completed': raise PreparationFailure('Preparation failed; retained '+str(output/'preparation-receipt.json'))
    return report


def _read_frozen(path,expected):
    path=_absolute(str(path)).resolve(strict=True)
    with path.open('rb') as stream: payload=stream.read(MAX_JSON_BYTES+1)
    if len(payload)>MAX_JSON_BYTES: raise ValueError('Explicit preparation config exceeds 2MiB')
    if hashlib.sha256(payload).hexdigest()!=_hash(expected): raise ValueError('Frozen preparation config checksum differs')
    def reject(value): raise ValueError('Nonfinite JSON constant: '+value)
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('Duplicate config key: '+key)
            result[key]=value
        return result
    def finite_float(value):
        result=float(value)
        if not math.isfinite(result): raise ValueError('Nonfinite JSON number')
        return result
    return json.loads(payload,parse_constant=reject,parse_float=finite_float,object_pairs_hook=unique)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=('plan-only','execute-preparation'))
    parser.add_argument('--output',required=True); parser.add_argument('--approved-plan',required=True)
    parser.add_argument('--expected-plan-sha256',required=True)
    parser.add_argument('--config'); parser.add_argument('--expected-config-sha256')
    args=parser.parse_args(argv)
    if args.mode=='execute-preparation':
        if not args.config or not args.expected_config_sha256:
            raise ValueError('Explicit execute-preparation requires frozen config and its external SHA256')
        config_path=args.config
    else:
        if args.config or args.expected_config_sha256: raise ValueError('Plan-only cannot select runtime/model inputs')
        config_path=None
    result=prepare(mode=args.mode,output=args.output,approved_plan=args.approved_plan,
        expected_plan_sha256=args.expected_plan_sha256,config_path=config_path,
        expected_config_sha256=args.expected_config_sha256)
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
