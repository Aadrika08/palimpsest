"""Provider-neutral source wire values. No record establishes execution authority."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import PurePosixPath
import re
import uuid

MiB = 1024**2
CLAIMS = dict(actual_acceptance=False, source_qualified=False, model_qualified=False,
              allocation_authorized=False, publication_authorized=False, go_authorized=False)
PHASES = ('producer','raw-audit','registration','conversion','qualifier','acceptance',
          'resource-lifetime','finalization','consumption','final-accounting')
LIMITS = dict(source_steps=1200,source_seconds=360,cleanup_seconds=10,outer_wall_seconds=900,
    outer_cpu_seconds=1800,rss_bytes=8589934592,raw_bytes=512*MiB,snapshot_bytes=16*MiB,
    candidate_bytes=32*MiB,controls_bytes=8*MiB,atomic_bytes=8*MiB,headroom_bytes=64*MiB,
    total_new_bytes=640*MiB,min_free_bytes=6442450944,metadata_bytes=MiB)


from palimpsest.records import _source_errors as errors


def fields(value, names):
    if type(value) is not dict or set(value) != set(names): raise ValueError('Exact record fields differ')
    return value


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high: raise ValueError('Integer outside bound')
    return value


def text(value, maximum=4096):
    if (type(value) is not str or not value or len(value.encode('utf-8')) > maximum
            or not value.isprintable()): raise ValueError('Invalid bounded printable text')
    return value


def digest(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None: raise ValueError('Invalid digest')
    return value


def run_id(value):
    if type(value) is not str or str(uuid.UUID(value)) != value: raise ValueError('Noncanonical UUID')
    return value


def path(value, absolute=False):
    text(value)
    if (value.startswith('/') != absolute or '\\' in value or ':' in value
            or (value != '/' and any(p in ('','.','..') or len(p.encode()) > 255
                for p in value[1 if absolute else 0:].split('/')))
            or len(PurePosixPath(value).parts) > 32): raise ValueError('Noncanonical path')
    return value


def descriptor(value, absolute=False, maximum=2**40, minimum=0):
    fields(value, ('path','size_bytes','sha256')); path(value['path'],absolute)
    integer(value['size_bytes'],minimum,maximum); digest(value['sha256'])
    return dict(value)


def describe(path_value, raw):
    path(path_value)
    return dict(path=path_value,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def _structure(value, depth=0, count=None):
    if count is None: count=[0]
    count[0] += 1
    if depth > 32 or count[0] > 20000: raise ValueError('JSON structural limit')
    if type(value) is str:
        if len(value.encode()) > 4096: raise ValueError('JSON string limit')
    elif type(value) is dict:
        for key, item in value.items():
            if type(key) is not str: raise ValueError('JSON keys must be strings')
            _structure(key,depth+1,count); _structure(item,depth+1,count)
    elif type(value) is list:
        for item in value: _structure(item,depth+1,count)
    elif type(value) is float:
        if not math.isfinite(value): raise ValueError('Nonfinite JSON')
    elif value is not None and type(value) not in (int,bool): raise ValueError('Non-JSON value')


def encode(value, maximum=MiB):
    _structure(value)
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    if len(raw)>maximum: raise ValueError('JSON byte limit')
    return raw


def decode(raw, maximum=MiB):
    if type(raw) is not bytes or len(raw)>maximum: raise ValueError('JSON byte limit/type')
    # Bound nesting before the parser can recurse or allocate deeply nested values.
    depth=0; quoted=False; escape=False
    for byte in raw:
        if quoted:
            if escape: escape=False
            elif byte == 92: escape=True
            elif byte == 34: quoted=False
        elif byte == 34: quoted=True
        elif byte in (91,123):
            depth+=1
            if depth>32: raise ValueError('JSON structural limit')
        elif byte in (93,125): depth-=1
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    def bad(_): raise ValueError('Nonfinite JSON')
    try: value=json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)
    except (UnicodeError,RecursionError) as error: raise ValueError('Invalid bounded JSON') from error
    if encode(value,maximum)!=raw: raise ValueError('Noncanonical JSON bytes')
    return value


def schema(value, name, authored=False):
    expected='memory-source-'+('authored-' if authored else '')+name+'-vnext-v1'
    if value.get('schema') != expected: raise ValueError('Source record domain/schema differs')
    claims=value.get('claims')
    if type(claims) is not dict or set(claims)!=set(CLAIMS) or any(item is not False for item in claims.values()): raise ValueError('Source claims differ')
    return value


def output_roster(case_id, run):
    text(case_id,255); path(case_id); run_id(run)
    if '/' in case_id: raise ValueError('Case must be one component')
    b=f'output/.pending/{case_id}'; r=f'{b}/.raw/{run}'; s=f'{b}/source'; k=f'output/controls/{run}'
    rows=[]
    def add(role,p,cap): rows.append(dict(role=role,path=p,max_bytes=cap))
    add('raw-manifest',r+'/recording/manifest.json',65536)
    add('raw-events',r+'/recording/events.jsonl',7*MiB)
    add('worker-report',r+'/worker-report.json',32768)
    for i in range(38): add(f'raw-chunk-{i:06}',f'{r}/recording/chunks/{i:06}.npz',7*MiB)
    add('owner',s+'/owner.json',16384); add('snapshot',s+'/snapshots/initial.snp',16*MiB)
    numeric=[('numeric-manifest','manifest.json',65536),('base-manifest','base/manifest.json',65536),
        ('legacy-manifest','base/legacy-manifest.json',65536),('legacy-events','base/legacy-events.jsonl',7*MiB),
        ('base-index','base/chunk-index.json',32768),('audit-frames','base/audit-frames.npz',8*98304+4096),
        ('numeric-index','numeric-index.json',32768)]
    numeric += [(f'base-chunk-{i:06}',f'base/chunks/{i:06}.npz',768*1024) for i in range(38)]
    numeric += [(f'companion-{i:06}',f'numeric/{i:06}.npz',16384) for i in range(38)]
    for role,p,cap in numeric: add(role,s+'/numeric/'+p,cap)
    controls=[('supervisor','producer/supervisor.json',65536),('producer-stdout','producer/stdout',262144),
        ('producer-stderr','producer/stderr',262144),('cleanup','producer/cleanup.json',65536),
        ('audit','raw-audit/audit.json',131072),('registration','registration/registration.json',65536),
        ('conversion','conversion/conversion.json',131072),('commit','conversion/commit.json',16384),
        ('candidate','qualifier/candidate.json',131072),('outcome','final-accounting/outcome.json',32768)]
    for phase in PHASES[1:]:
        for stream in ('stdout','stderr'): controls.append((phase+'-'+stream,phase+'/'+stream,16384))
    for phase,name in [('acceptance','acceptance'),('resource-lifetime','lifetime'),('finalization','finalization'),
                       ('consumption','registration'),('final-accounting','accounting')]:
        controls.append(('future-'+phase,phase+'/'+name+'.json',262144))
    for phase in PHASES: controls.append(('failure-'+phase,'failures/'+phase+'/failure.json',32768))
    for role,p,cap in controls: add(role,k+'/'+p,cap)
    add('pending-raw-manifest',r+'/recording/manifest.tmp',7*MiB)
    for i in range(38): add(f'pending-raw-chunk-{i:06}',f'{r}/recording/chunks/{i:06}.tmp',7*MiB)
    for role,p,cap in numeric: add('pending-'+role,s+'/numeric/'+p+'.pending',cap)
    for role,p,cap in controls: add('pending-'+role,k+'/'+p+'.pending',cap)
    add('pending-owner',s+'/owner.json.pending',16384)
    add('pending-worker-report',r+'/worker-report.json.pending',32768)
    assert len(rows)==336
    return sorted(rows,key=lambda row:(row['role'],row['path']))


def _validate_authored_namespace_binding(value, fixture_id, workspace_root):
    fields(value,('schema','purpose','fixture_id','coverage_contract','root','export','scope','claims'))
    schema(value,'namespace-export-binding',True); text(fixture_id); path(workspace_root,True)
    purpose=value['purpose']
    if purpose not in ('pre-heldout-development-history','training-namespace'): raise ValueError('Namespace purpose')
    if value['fixture_id']!=fixture_id or value['scope']!='software-unit-only': raise ValueError('Fixture identity')
    root=workspace_root+'/freeze/namespaces/'+purpose
    if value['root']!=root: raise ValueError('Namespace outside fixed fixture root')
    coverage=descriptor(value['coverage_contract'],True,MiB,1)
    export=descriptor(value['export'],True,32*MiB,1)
    if coverage['path']!=workspace_root+'/freeze/metadata/authored-namespace-coverage.json' or export['path']!=root+'/namespace-export.json':
        raise ValueError('Namespace fixed paths differ')
    return decode(encode(value))


def _validate_authored_namespace_coverage(value,fixture_id):
    fields(value,('schema','fixture_id','scope','sources','file_allowlist','max_identity_characters','max_metadata_bytes','max_values','claims'))
    schema(value,'namespace-coverage',True)
    if value['fixture_id']!=fixture_id or value['scope']!='software-unit-only' or value['file_allowlist']!=['namespace-export.json']:
        raise ValueError('Authored coverage identity')
    _validate_namespace_expectations(value)
    return decode(encode(value))


def _validate_namespace_expectations(value):
    integer(value['max_identity_characters'],1,128); integer(value['max_metadata_bytes'],1,32*MiB); integer(value['max_values'],1,100000)
    if type(value['sources']) is not list or len(value['sources'])!=2: raise ValueError('Namespace source pair')
    for row,(source,kind) in zip(value['sources'], [('pre-heldout-development-history','historical'),('training-namespace','training')]):
        fields(row,('source_id','kind','expected'))
        if row['source_id']!=source or row['kind']!=kind: raise ValueError('Namespace kind/order')
        expected=row['expected']; names=('known_sources','historical_run_ids','historical_authored_ids','training_seeds')
        fields(expected,('entries','files','bytes','inventory_sha256','export_bytes','export_sha256',
            *[name+suffix for name in names for suffix in ('_count','_sha256')]))
        integer(expected['entries'],1,1); integer(expected['files'],1,1)
        integer(expected['export_bytes'],1,value['max_metadata_bytes'])
        if expected['bytes']!=expected['export_bytes']: raise ValueError('One-file namespace')
        integer(expected['bytes'],1,value['max_metadata_bytes']); digest(expected['inventory_sha256']); digest(expected['export_sha256'])
        for name in names: integer(expected[name+'_count'],1 if name=='known_sources' else 0,100000); digest(expected[name+'_sha256'])
        if kind=='historical' and expected['training_seeds_count']!=0: raise ValueError('Historical seeds must be empty')
        if sum(expected[name+'_count'] for name in names)>value['max_values']: raise ValueError('Namespace value cap')


def _validate_actual_namespace_coverage(value):
    fields(value,('schema','coverage_status','allocation_authorized','reason','source_ids','export_schema','file_allowlist','sources','max_identity_characters','max_metadata_bytes','max_values'))
    for name,literal in dict(schema='memory-family-namespace-coverage-v3',coverage_status='resolved',allocation_authorized=True,reason=None,source_ids=['pre-heldout-development-history','training-namespace'],export_schema='memory-family-namespace-export-v3',file_allowlist=['namespace-export.json']).items(): _literal(value[name],literal)
    _validate_namespace_expectations(value)
    return decode(encode(value))


# Fixed source-only authored harness exception. These are unit code identities,
# never an assertion of complete installed interpreter/native runtime custody.
HARNESS_SOURCES = tuple('scripts/'+name for name in (
    'memory_source_parent_entry_vnext.py','memory_family_source_records_vnext.py',
    'memory_family_source_runtime_vnext.py','memory_family_source_raw_audit_vnext.py',
    'memory_family_source_numeric_vnext.py','memory_family_source_qualifier_vnext.py',
    'memory_source_runtime_closure_v1.py','memory_family_replay_custody_v4.py',
    'memory_family_cell_replay_v4.py','memory_family_compact_v4.py','memory_family_raw_audit_v4.py',
    'memory_family_oracle_v3.py','memory_family_oracle_admission_v3.py',
    'memory_decision_pilot.py','verify_flynn_memory_transfer.py')) + tuple('src/palimpsest/'+name for name in (
    '__init__.py','assets.py','engine.py','records.py','snapshots.py','held_provenance.py',
    'memory.py','memory_decision.py','memory_decision_world.py','memory_task.py','memory_world.py',
    'profiles.py','flynn.py','artifacts.py','male_policy.py','evaluate.py'))


def _authored_external_source(row):
    from pathlib import Path
    root=Path(__file__).absolute().parents[1]
    return row['path'] in {str(root/name) for name in HARNESS_SOURCES}


def record_schema(name,authored=False): return 'memory-source-'+('authored-' if authored else '')+name+'-vnext-v1'


def _literal(value,expected):
    if encode(value)!=encode(expected): raise ValueError('Typed literal differs')


def _list(value,maximum,minimum=0):
    if type(value) is not list or not minimum<=len(value)<=maximum: raise ValueError('List bound')
    return value


def _descriptors(value,maximum=32768,absolute=True,cap=2**40):
    rows=_list(value,maximum)
    for row in rows: descriptor(row,absolute,cap)
    paths=[row['path'] for row in rows]
    if paths!=sorted(set(paths)): raise ValueError('Descriptor roster not sorted/distinct')
    return rows


def _tree(value):
    fields(value,('root','directories','files')); root=path(value['root'],True)
    directories=_list(value['directories'],60000)
    for relative in directories: path(relative)
    if directories!=sorted(set(directories)): raise ValueError('Directory order')
    for relative in directories:
        parent=relative.rpartition('/')[0]
        if parent and parent not in directories: raise ValueError('Missing explicit directory parent')
    files=_descriptors(value['files'])
    for row in files:
        if not row['path'].startswith(root+'/'): raise ValueError('File outside declared root')
        relative=row['path'][len(root)+1:]; parent=relative.rpartition('/')[0]
        if parent and parent not in directories: raise ValueError('Missing file parent')
    if 1+len(directories)+len(files)>60000 or sum(row['size_bytes'] for row in files)>16*1024*MiB: raise ValueError('Tree cap')


def _readset(value):
    names=dict(profile='profile',source_closure='source-closure',producer_plan='plan',load_environment='load',resources='resources',history_namespace='history',training_namespace='training')
    fields(value,names)
    for name,filename in names.items():
        descriptor(value[name],maximum=MiB,minimum=1)
        if value[name]['path']!='freeze/metadata/'+filename+'.json': raise ValueError('Fixed readset path differs')


def _job(value,authored):
    from palimpsest import memory_decision_world as world
    fields(value,('schema','operation','condition','split','block','row','kind','case','source_run_id','attempt_id','readset','workspace_root','output_root','limits'))
    if value['schema']!=record_schema('job',authored): raise ValueError('Job schema/domain')
    for key,literal in dict(operation='source',condition=None,split='development',block=0,row=0,kind='change',output_root='output',limits=LIMITS).items(): _literal(value[key],literal)
    world.validate_case(value['case']); _literal(value['case'],world.make_family_case('development',0,0,'change'))
    run_id(value['source_run_id']); run_id(value['attempt_id']); path(value['workspace_root'],True); _readset(value['readset'])
    if authored and not value['workspace_root'].startswith(('/var/tmp/source-vertical-','/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-')): raise ValueError('Unregistered authored evidence root')


def _load(value,authored):
    from scripts.memory_source_runtime_closure_v1 import validate_runtime_reference, validate_runtime_pin_requirements
    fields(value,('schema','runtime_reference','runtime_requirements','model','provenance','roots','environment','working_directory','python_path','native_libraries','claims'))
    schema(value,'load-environment',authored); validate_runtime_reference(value['runtime_reference'])
    requirements=value['runtime_requirements']; fields(requirements,('roots','pins'))
    roots=_list(requirements['roots'],16,1)
    for root in roots: path(root,True)
    if roots!=sorted(set(roots)) or any(a.startswith(b+'/') or b.startswith(a+'/') for i,a in enumerate(roots) for b in roots[i+1:]): raise ValueError('Runtime root overlap')
    validate_runtime_pin_requirements(requirements['pins'])
    pins=requirements['pins']
    if pins['pyvenv_config']['path']!=str(PurePosixPath(pins['python_alias']).parent.parent/'pyvenv.cfg'): raise ValueError('Pinned pyvenv lexical path')
    model=value['model']; fields(model,('manifest','checkpoint','graph','mapping','upstream_sources','upstream_commit','controller','device','dtype','input_width','threads','training','requires_grad'))
    for name in ('manifest','checkpoint'): descriptor(model[name],True,2**40,1)
    for name,maximum in [('graph',32),('mapping',32),('upstream_sources',64)]:
        _descriptors(model[name],maximum)
        if not model[name]: raise ValueError('Empty model input roster')
    if re.fullmatch('[0-9a-f]{40}',model['upstream_commit']) is None: raise ValueError('Upstream commit')
    for key,literal in dict(controller='flynn',device='cpu',dtype='torch.float32',input_width=4813,threads=1,training=False,requires_grad=False).items(): _literal(model[key],literal)
    from palimpsest.held_provenance import held_provenance
    held_provenance(**value['provenance'])
    if value['provenance']['interpreter']['python_version']!='3.11.15': raise ValueError('Pinned interpreter version differs')
    if value['environment']!=value['provenance']['environment']: raise ValueError('Environment/provenance differ')
    fields(value['environment'],value['environment'])
    if len(value['environment'])>128: raise ValueError('Environment cap')
    for key,item in value['environment'].items(): text(key); text(item)
    path(value['working_directory'],True)
    for root in _list(value['python_path'],32): path(root,True)
    _descriptors(value['native_libraries'],1024)
    registered=_list(value['roots'],21)
    roles=[]
    for row in registered:
        fields(row,('role','path')); path(row['path'],True); roles.append(row['role'])
        if row['role'] not in ('repo','assets','runtime','history','training') and re.fullmatch('runtime-(?:0[0-9]|1[0-5])',row['role']) is None: raise ValueError('Root role')
    if len(roles)!=len(set(roles)) or not {'repo','assets','history','training'}<=set(roles): raise ValueError('Root roles missing/duplicate')


def validate_attempt(job_bytes,authorization_bytes,authored,read):
    """Fixed parent uses a fixed no-follow metadata reader; no public role accepts it."""
    job=decode(job_bytes,262144); _job(job,authored)
    auth=decode(authorization_bytes,262144); schema(auth,'attempt-authorization',authored)
    common=('schema','attempt_id','source_run_id','job','readset','workspace_root','resource_contract','phases','issued_monotonic_ns','deadline_monotonic_ns','claims')
    fields(auth,(*common,'fixture_id','scope') if authored else (*common,'operator_binding','process_roster','clock_domain'))
    for key in ('attempt_id','source_run_id','readset','workspace_root'): _literal(auth[key],job[key])
    _literal(auth['job'],describe('freeze/metadata/job.json',job_bytes)); _literal(auth['resource_contract'],job['readset']['resources'])
    issued=integer(auth['issued_monotonic_ns'],0,2**63-1); deadline=integer(auth['deadline_monotonic_ns'],issued+1,2**63-1)
    import time
    if not issued<=time.monotonic_ns()<deadline or deadline-issued>900_000_000_000: raise ValueError('Authorization deadline interval')
    phases=_list(auth['phases'],10,5)
    if phases[:5]!=list(PHASES[:5]) or phases!=[p for p in PHASES if p in phases]: raise ValueError('Finite phase order')
    if authored:
        text(auth['fixture_id']); _literal(auth['scope'],'software-unit-only')
    else:
        text(auth['clock_domain']); operator=auth['operator_binding']; fields(operator,('authority_id','decision_id','go_record','resource_admission','load_admission'))
        text(operator['authority_id']); text(operator['decision_id'])
        for name in ('go_record','resource_admission','load_admission'): descriptor(operator[name],True,MiB,1)
        rows=_list(auth['process_roster'],7,1); role_names=[]; allowed={'trusted-parent','workload','watchdog','accountant','independent-acceptor','finalizer','consumer'}
        for row in rows:
            fields(row,('role','parent_role','phases','max_threads','max_children','cpu_scope'))
            if row['role'] not in allowed or row['parent_role'] not in allowed|{None}: raise ValueError('Process role')
            role_names.append(row['role']); integer(row['max_threads'],1,64); integer(row['max_children'],0,16); text(row['cpu_scope'])
            if not set(_list(row['phases'],10))<=set(PHASES): raise ValueError('Process phases')
        if len(role_names)!=len(set(role_names)) or 'workload' not in role_names: raise ValueError('Process roster')
        parents={row['role']:row['parent_role'] for row in rows}
        for role in parents:
            seen=set(); current=role
            while current is not None:
                if current in seen or current not in parents: raise ValueError('Process parent closure/cycle')
                seen.add(current); current=parents[current]
    workspace=job['workspace_root']; metadata={}
    caps=dict(profile=262144,source_closure=MiB,producer_plan=262144,load_environment=262144,resources=65536,history_namespace=524288,training_namespace=524288)
    for name,desc in job['readset'].items():
        if time.monotonic_ns()>=deadline: raise TimeoutError('Source preflight deadline')
        raw=read(workspace+'/'+desc['path'],caps[name])
        if time.monotonic_ns()>=deadline: raise TimeoutError('Source preflight deadline')
        _literal(describe(desc['path'],raw),desc); metadata[name]=decode(raw,caps[name])
    if read(workspace+'/freeze/metadata/job.json',262144)!=job_bytes or read(workspace+'/freeze/metadata/authorization.json',262144)!=authorization_bytes: raise ValueError('Frozen job/auth bytes differ')
    load=metadata['load_environment']; _load(load,authored)
    output=workspace+'/output'; frozen_metadata=workspace+'/freeze/metadata'
    for row in load['roots']:
        selected=row['path']
        if any(selected==target or selected.startswith(target+'/') or target.startswith(selected+'/') for target in (output,frozen_metadata)):
            raise ValueError('Declared source root overlaps output/frozen metadata')
    resources=metadata['resources']; schema(resources,'resource-contract',authored)
    fields(resources,('schema','limits','fixture','capacity','claims') if authored else ('schema','limits','allocation_reference','load_admission','prior_reconciliation','accounting_boundary','whole_operation_cpu_upper_ns','capacity','claims'))
    _literal(resources['limits'],LIMITS)
    if authored:
        _literal(resources['fixture'],dict(fixture_id=auth['fixture_id'],scope='software-unit-only'))
    else:
        for name in ('allocation_reference','load_admission','prior_reconciliation'): descriptor(resources[name],True,MiB,1)
        _literal(resources['accounting_boundary'],'all-project-processes'); _literal(resources['whole_operation_cpu_upper_ns'],None)
    capacity=resources['capacity']; fields(capacity,('frozen_input_bytes','frozen_input_files','frozen_input_directories','reserved_output_directories','required_free_bytes'))
    integer(capacity['frozen_input_bytes'],0,2**40); integer(capacity['frozen_input_files'],0,60000); integer(capacity['frozen_input_directories'],0,60000)
    integer(capacity['reserved_output_directories'],1,4096); integer(capacity['required_free_bytes'],0 if authored else LIMITS['min_free_bytes'],2**63-1)
    closure=metadata['source_closure']; schema(closure,'software-closure',authored); fields(closure,('schema','roots','standalones','entry_sources','claims'))
    for tree in _list(closure['roots'],16): _tree(tree)
    _descriptors(closure['standalones'],1024); _descriptors(closure['entry_sources'],64)
    expected_files=('memory_source_parent_entry_vnext.py','memory_family_source_records_vnext.py','memory_family_source_runtime_vnext.py','memory_family_source_raw_audit_vnext.py','memory_family_source_numeric_vnext.py','memory_family_source_qualifier_vnext.py')
    source_names={PurePosixPath(row['path']).name for row in closure['entry_sources']}
    if not set(expected_files)<=source_names: raise ValueError('New source closure incomplete')
    pins=load['runtime_requirements']['pins']
    if PurePosixPath(pins['owner_source']['path']).name!='memory_family_source_runtime_vnext.py': raise ValueError('New owner pin missing')
    required={encode(row) for row in pins['required_sources']}
    if any(encode(row) not in required for row in closure['entry_sources']): raise ValueError('Runtime omits new source dependencies')
    profile=metadata['profile']; schema(profile,'software-profile',authored)
    fields(profile,('schema','source_closure','entrypoints','load_environment','codec','claims'))
    _literal(profile['source_closure'],job['readset']['source_closure']); _literal(profile['load_environment'],job['readset']['load_environment'])
    _literal(profile['entrypoints'],dict(parent='scripts/memory_source_parent_entry_vnext.py:run_attempt',producer='scripts/memory_family_source_runtime_vnext.py:produce_source',raw_auditor='scripts/memory_family_source_raw_audit_vnext.py:audit_source',converter='scripts/memory_family_source_numeric_vnext.py:convert_source',qualifier='scripts/memory_family_source_qualifier_vnext.py:qualify_source'))
    _literal(profile['codec'],dict(chunk_rows=32,base_arrays=16,companion_arrays=3,input_width=4813,source_rows_max=1200,numeric_format='palimpsest-source-numeric-vnext-v1'))
    plan=metadata['producer_plan']; schema(plan,'producer-plan',authored)
    fields(plan,('schema','profile','source_closure','case','source_run_id','source_job','inputs','output_roster','namespace','resource_envelope','claims'))
    for name in ('profile','source_closure'): _literal(plan[name],job['readset'][name])
    _literal(plan['case'],job['case']); _literal(plan['source_run_id'],job['source_run_id'])
    _literal(plan['source_job'],dict(role='source-job',path='freeze/metadata/job.json',max_bytes=262144))
    expected_inputs=[dict(role=name,path=job['readset'][name]['path'],max_bytes=caps[name]) for name in job['readset'] if name!='producer_plan']
    expected_inputs.extend([dict(role='source-job',path='freeze/metadata/job.json',max_bytes=262144),dict(role='authorization',path='freeze/metadata/authorization.json',max_bytes=262144)])
    if authored:
        identity_path=workspace+'/freeze/metadata/authored-model-identity.json'
        if load['model']['manifest']['path']!=identity_path: raise ValueError('Authored model identity fixed path')
        identity_raw=read(identity_path,262144)
        _literal(dict(describe('identity',identity_raw),path=identity_path),load['model']['manifest'])
        identity=decode(identity_raw,262144)
        fields(identity,('schema','fixture_id','input_width','hidden_width','runtime_sources','model_sources','weights','graph','python_version','torch_version','dtype','device','threads','training','requires_grad','scope','claims'))
        schema(identity,'model-identity',True)
        for name,literal in dict(fixture_id=auth['fixture_id'],input_width=4813,dtype='torch.float32',device='cpu',threads=1,training=False,requires_grad=False,scope='software-unit-only').items(): _literal(identity[name],literal)
        integer(identity['hidden_width'],1,4096); text(identity['python_version']); text(identity['torch_version'])
        for name,cap in [('runtime_sources',64),('model_sources',64),('weights',32),('graph',32)]:
            _descriptors(identity[name],cap,cap=1024*MiB)
            for row in identity[name]:
                if not row['path'].startswith(workspace+'/') and not (name=='runtime_sources' and _authored_external_source(row)): raise ValueError('Authored model identity outside fixture')
        metadata['authored_identity']=identity
        expected_inputs.append(dict(role='authored-model-identity',path='freeze/metadata/authored-model-identity.json',max_bytes=262144))

    _literal(plan['inputs'],sorted(expected_inputs,key=lambda row:(row['role'],row['path'])))
    _literal(plan['output_roster'],output_roster(job['case']['case_id'],job['source_run_id']))
    _literal(plan['namespace'],dict(history=job['readset']['history_namespace'],training=job['readset']['training_namespace'])); _literal(plan['resource_envelope'],job['readset']['resources'])
    coverage_desc=None
    for name,purpose in [('history_namespace','pre-heldout-development-history'),('training_namespace','training-namespace')]:
        binding=metadata[name]
        if authored: _validate_authored_namespace_binding(binding,auth['fixture_id'],workspace)
        else:
            fields(binding,('schema','purpose','authority_reference','coverage_contract','root','export','scope','claims')); schema(binding,'namespace-export-binding')
            _literal(binding['scope'],'namespace-only'); descriptor(binding['authority_reference'],True,MiB,1)
            path(binding['root'],True); descriptor(binding['coverage_contract'],True,MiB,1); descriptor(binding['export'],True,32*MiB,1)
            if binding['export']['path']!=binding['root']+'/namespace-export.json': raise ValueError('Namespace export path')
        _literal(binding['purpose'],purpose)
        if coverage_desc is not None: _literal(binding['coverage_contract'],coverage_desc)
        coverage_desc=binding['coverage_contract']
    coverage_raw=read(coverage_desc['path'],MiB); _literal(dict(describe('coverage',coverage_raw),path=coverage_desc['path']),coverage_desc)
    coverage=decode(coverage_raw)
    if authored: _validate_authored_namespace_coverage(coverage,auth['fixture_id'])
    else: _validate_actual_namespace_coverage(coverage)
    metadata['coverage']=coverage
    if authored: _authored_preload_paths(job,metadata,read)
    input_closure(job,auth,metadata,authored)
    _output_census(job,resources)
    return job,auth,metadata


def _authored_preload_paths(job,metadata,read):
    workspace=job['workspace_root']; load=metadata['load_environment']
    def within(value):
        path(value,True)
        if not value.startswith(workspace+'/'): raise ValueError('Authored selected path outside frozen fixture')
    for tree in metadata['source_closure']['roots']: within(tree['root'])
    for row in load['roots']: within(row['path'])
    within(load['working_directory'])
    for value in load['python_path']+load['runtime_requirements']['roots']: within(value)
    pins=load['runtime_requirements']['pins']; within(pins['python_alias'])
    for name in ('python_elf','pyvenv_config'): within(pins[name]['path'])
    model=load['model']
    selected=[model['manifest'],model['checkpoint'],*model['graph'],*model['mapping'],*model['upstream_sources'],*load['native_libraries']]
    selected.extend(load['runtime_reference'][name] for name in ('recipe','manifest','ledger'))
    within(load['provenance']['interpreter']['path']); within(load['provenance']['upstream']['path'])
    for row in selected: within(row['path'])
    # Genuine pure runtime readers validate its internal selection before any
    # RuntimeHandle can open generated payloads; source-only standalones are the
    # one fixed external harness exception, never installed binary assets.
    from scripts import memory_source_runtime_closure_v1 as runtime
    reference=load['runtime_reference']
    manifest_raw=read(reference['manifest']['path'],16*MiB)
    manifest=runtime.validate_runtime_manifest(manifest_raw,reference,required_roots=tuple(load['runtime_requirements']['roots']),required_pins=pins,output_root=workspace+'/output')
    for tree in manifest['roots']: within(tree['root'])
    for row in manifest['standalones']:
        if not _authored_external_source(row): within(row['path'])
    recipe_raw=read(reference['recipe']['path'],65536)
    recipe=runtime.validate_preparation_recipe(recipe_raw,reference,manifest)
    ledger_raw=read(reference['ledger']['path'],262144)
    runtime.validate_preparation_ledger(ledger_raw,reference,manifest,recipe)
    ledger=decode(ledger_raw,262144)
    for row in ledger['retained_files']: within(row['path'])


def _output_census(job,resources):
    root=job['workspace_root']; roster=output_roster(job['case']['case_id'],job['source_run_id'])
    directories=reserved_directories(job)
    if len(directories)!=resources['capacity']['reserved_output_directories']: raise ValueError('Reserved output directory census differs')
    for relative in directories:
        full=root+'/'+relative; state=os.stat(full,follow_symlinks=False)
        if not __import__('stat').S_ISDIR(state.st_mode): raise ValueError('Output reservation not real directory')
        expected={name.rsplit('/',1)[-1] for name in directories if name.rpartition('/')[0]==relative}
        with os.scandir(full) as entries:
            names=set()
            for entry in entries:
                if len(names)>=len(expected) or entry.name not in expected: raise ValueError('Existing/unreserved output child')
                names.add(entry.name)
        if names!=expected: raise ValueError('Output reserved child absent')


def reserved_directories(job):
    b=f"output/.pending/{job['case']['case_id']}"; r=b+'/.raw/'+job['source_run_id']; s=b+'/source'; k='output/controls/'+job['source_run_id']
    dirs={'output','output/.pending',b,b+'/.raw',r,s,s+'/snapshots',s+'/numeric',s+'/numeric/base',s+'/numeric/base/chunks',s+'/numeric/numeric','output/controls',k,k+'/failures'}
    dirs.update(k+'/'+phase for phase in PHASES); dirs.update(k+'/failures/'+phase for phase in PHASES)
    return sorted(dirs)


def input_closure(job,auth,metadata,authored):
    workspace=job['workspace_root']; load=metadata['load_environment']; closure=metadata['source_closure']; rows=[]; trees=[]
    for desc in job['readset'].values(): rows.append(dict(desc,path=workspace+'/'+desc['path']))
    rows.extend([dict(describe('job',encode(job,262144)),path=workspace+'/freeze/metadata/job.json'),dict(describe('auth',encode(auth,262144)),path=workspace+'/freeze/metadata/authorization.json')])
    for tree in closure['roots']: trees.append(tree); rows.extend(tree['files'])
    rows.extend(closure['standalones']); rows.extend(closure['entry_sources'])
    model=load['model']; rows.extend([model['manifest'],model['checkpoint'],*model['graph'],*model['mapping'],*model['upstream_sources'],*load['native_libraries']])
    reference=load['runtime_reference']; rows.extend(reference[name] for name in ('recipe','manifest','ledger'))
    pins=load['runtime_requirements']['pins']; rows.extend([pins['python_elf'],pins['owner_source'],pins['pyvenv_config'],*pins['required_sources']])
    provenance=load['provenance']; interpreter={key:provenance['interpreter'][key] for key in ('path','size_bytes','sha256')}; rows.append(interpreter)
    rows.extend(dict(row,path=provenance['upstream']['path']+'/'+row['path']) for row in provenance['upstream']['files'])
    for binding in (metadata['history_namespace'],metadata['training_namespace']):
        rows.extend([binding['coverage_contract'],binding['export']]); trees.append(dict(root=binding['root'],directories=[],files=[binding['export']]))
        if not authored: rows.append(binding['authority_reference'])
    if authored:
        for name in ('runtime_sources','model_sources','weights','graph'): rows.extend(metadata['authored_identity'][name])
    if not authored:
        rows.extend(auth['operator_binding'][name] for name in ('go_record','resource_admission','load_admission'))
        rows.extend(metadata['resources'][name] for name in ('allocation_reference','load_admission','prior_reconciliation'))
    unique={}
    for row in rows:
        descriptor(row,True)
        if row['path'] in unique: _literal(row,unique[row['path']])
        unique[row['path']]=row
        if authored and not row['path'].startswith(workspace+'/') and not _authored_external_source(row): raise ValueError('Authored payload outside fixture')
        if row['path'].startswith(workspace+'/output/'): raise ValueError('Input/output overlap')
    return list(unique.values()),trees


def validate_held_namespaces(job,auth,metadata,lease):
    """Reuse unchanged v3 list/identity and ledger semantics on held export bytes."""
    from scripts import memory_family_allocation_v3 as allocation
    from palimpsest import artifacts,memory
    coverage=metadata['coverage']; exports=[]
    if type(coverage['sources']) is not list or len(coverage['sources'])!=2: raise ValueError('Namespace exact source pair')
    _validate_namespace_expectations(coverage)
    for index,binding in enumerate((metadata['history_namespace'],metadata['training_namespace'])):
        row=coverage['sources'][index]
        payload=lease._read(binding['export'],coverage['max_metadata_bytes']); export=artifacts._json(payload)
        if payload!=memory.canonical_bytes(export): raise ValueError('Namespace export noncanonical')
        fields(export,('schema','source_id','kind','known_sources','historical_run_ids','historical_authored_ids','training_seeds'))
        if export['schema']!='memory-family-namespace-export-v3' or export['source_id']!=binding['purpose'] or export['source_id']!=row['source_id'] or export['kind']!=row['kind']: raise ValueError('Namespace export identity')
        def known(value):
            if type(value) is not str or not value or len(value)>coverage['max_identity_characters'] or allocation._held_out(value): raise ValueError('Namespace known-source identity')
        allocation._validated_list(export['known_sources'],'Known sources',known)
        allocation._validated_list(export['historical_run_ids'],'Historical run IDs',allocation._uuid)
        allocation._validated_list(export['historical_authored_ids'],'Historical authored IDs',allocation._identifier)
        def seed(value): integer(value,0,2**32-1)
        allocation._validated_list(export['training_seeds'],'Training seeds',seed)
        if not export['known_sources'] or export['kind']=='historical' and export['training_seeds']: raise ValueError('Namespace export values')
        names=('known_sources','historical_run_ids','historical_authored_ids','training_seeds')
        if sum(len(export[name]) for name in names)>coverage['max_values']: raise ValueError('Namespace total values')
        mode=lease._registry.binding(binding['export']['path']).identity[2]
        ledger=[dict(path='namespace-export.json',kind='file',executable=bool(mode & __import__('stat').S_IXUSR),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())]
        actual=dict(entries=1,files=1,bytes=len(payload),inventory_sha256=memory.sha256(ledger),export_bytes=len(payload),export_sha256=hashlib.sha256(payload).hexdigest())
        for name in names: actual[name+'_count']=len(export[name]); actual[name+'_sha256']=memory.sha256(export[name])
        _literal(actual,row['expected']); exports.append(export)
    for name in ('known_sources','historical_run_ids','historical_authored_ids','training_seeds'):
        if set(exports[0][name]) & set(exports[1][name]): raise ValueError('Duplicate namespace identity across exports')
    for export in exports:
        if job['source_run_id'].replace('-','') in export['historical_run_ids'] or job['case']['case_id'] in export['historical_authored_ids'] or job['case']['seed'] in export['training_seeds']:
            raise ValueError('Selected source collides with frozen namespace')
    lease.recheck()
