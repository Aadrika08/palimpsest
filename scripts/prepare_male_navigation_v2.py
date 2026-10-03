"""Pinned navigation advice-data admission only; no training or native execution."""
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
SELF_SHA = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
PROTOCOL = 'docs/plans/m7-navigation-data-v2-protocol.json'
PROTOCOL_SHA = 'd2b998cdd4763a4b173bfe712ba0c50d19c7cfd56b68e44c395c575cdcfa2feb'
MiB = 1024**2
MAX_JSON, MAX_TRANSFER = 4*MiB, 8*MiB
RAW_PAYLOAD_FIELDS = ('cam_left', 'cam_right', 'sensors', 'action', 'simulation_time', 'eyes')


def file_sha(path, maximum=160*MiB, deadline=math.inf):
    path = Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size > maximum:
        raise ValueError('Missing, nonregular or oversized pinned input: '+str(path))
    h = hashlib.sha256(); total = 0
    with path.open('rb') as stream:
        while block := stream.read(MiB):
            check_deadline(deadline); total += len(block)
            if total > maximum: raise ValueError('Growing pinned file exceeds read cap')
            h.update(block)
    return h.hexdigest()


def read_json(path, maximum=MAX_JSON, expected=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file(): raise ValueError('Regular JSON input required')
    with path.open('rb') as stream: payload = stream.read(maximum+1)
    if len(payload)>maximum: raise ValueError('JSON read cap exceeded')
    if expected is not None and hashlib.sha256(payload).hexdigest()!=expected: raise ValueError('Pinned document changed')
    return json.loads(payload, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def protocol():
    return read_json(ROOT/PROTOCOL, expected=PROTOCOL_SHA)


def check_deadline(deadline):
    if time.monotonic()>deadline: raise TimeoutError('Navigation data completion deadline exceeded')


def historical_identity(p, deadline, *, enforce=True):
    h = p['source_binding']['old_historical_reader']; root = Path(h['root'])
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,timeout=5).strip()
    if enforce and head!=h['head']: raise ValueError('Historical reader HEAD changed')
    names = subprocess.check_output(['git','ls-files','src','scripts'],cwd=root,text=True,timeout=5).splitlines()
    if len(names)>1024: raise ValueError('Historical source inventory cap exceeded')
    sources = {n:file_sha(root/n, MAX_JSON, deadline) for n in names if n.endswith('.py')}
    pin = h['all_tracked_project_python_inventory']
    digest = hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()
    if enforce and (len(sources)!=pin['count'] or digest!=pin['canonical_map_sha256']): raise ValueError('Historical Python inventory changed')
    if enforce and (sources.get('scripts/prepare_male_recovery_data.py')!=h['adapter_sha256'] or
            any(sources.get(n)!=value for n,value in h['code'].items())):
        raise ValueError('Historical adapter/dependency changed')
    return {'head':head, 'root':str(root), 'sources':sources}


def helpers():
    # Called only in the parent; historical child dispatch precedes these imports.
    from palimpsest import artifacts, male_model
    from palimpsest.records import iter_ticks
    import prepare_male_recovery_data as old
    import collect_male_navigation_v2 as navigation
    return artifacts, male_model, iter_ticks, old, navigation


def reader_identity(deadline, *, enforce=True):
    names = subprocess.check_output(['git','ls-files','src','scripts'],cwd=ROOT,text=True,timeout=5).splitlines()
    if len(names)>1024: raise ValueError('Current reader source inventory cap exceeded')
    names = sorted({n for n in names if n.endswith('.py')} | {SCRIPT.relative_to(ROOT).as_posix()})
    sources = {n:file_sha(ROOT/n, MAX_JSON, deadline) for n in names}
    if enforce and sources[SCRIPT.relative_to(ROOT).as_posix()]!=SELF_SHA: raise ValueError('Loaded adapter bytes changed')
    return sources


def output_path(output, p):
    artifacts, *_ = helpers(); output = artifacts._safe_path(output)
    roots = [Path(item['path']).parent for item in p['immutable_inputs'].values()]
    roots += [Path(p[k]['path']).parent for k in ('old_baseline_document','old_recovery_document')]
    roots += [Path(p['source_binding']['old_historical_reader']['root']),
              Path(p['immutable_inputs']['accepted_collection']['path']).parents[2]]
    for root in roots:
        root = artifacts._safe_path(root)
        if output==root or root in output.parents or output in root.parents:
            raise ValueError('Output overlaps immutable corpus/producer/control tree')
    return output


def pinned_documents(p, deadline):
    documents = {}
    for name,item in p['immutable_inputs'].items():
        check_deadline(deadline)
        path = Path(item['path'])
        if path.stat().st_size!=item['bytes']: raise ValueError('Pinned document size changed')
        documents[name] = read_json(path, expected=item['sha256'])
    for name in ('old_baseline_document','old_recovery_document'):
        item=p[name]; documents[name]=read_json(item['path'],expected=item['sha256'])
    return documents


def write_payload(path, payload, maximum, deadline, validate=lambda: None, budget=None):
    path=Path(path)
    if len(payload)>maximum: raise ValueError('Publication payload exceeds cap')
    if path.exists(): raise FileExistsError('Fresh immutable destination required')
    if budget is not None: budget.check(len(payload),path=path)
    pending=path.with_name(path.name+'.pending')
    with pending.open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    validate(); check_deadline(deadline)
    if path.exists(): raise FileExistsError('Destination appeared during final sync')
    pending.replace(path)  # Last operation: no fallible cleanup after admission.


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',', ':'),allow_nan=False)+'\n').encode()


def imported_historical_sources(identity):
    root=Path(identity['root']); loaded={}
    for name,module in list(sys.modules.items()):
        file=getattr(module,'__file__',None)
        if not file: continue
        path=Path(file).resolve()
        if path.is_relative_to(root/'src') or path.is_relative_to(root/'scripts'):
            rel=path.relative_to(root).as_posix()
            if rel not in identity['sources'] or file_sha(path,MAX_JSON)!=identity['sources'][rel]:
                raise ValueError('Imported historical helper path/hash differs')
            loaded[name]={'path':str(path),'sha256':identity['sources'][rel]}
        elif name=='palimpsest' or name.startswith('palimpsest.') or name in ('prepare_male_recovery_data','collect_male_recovery'):
            raise ValueError('Historical child imported current project code')
    required=set(protocol()['source_binding']['old_historical_reader']['code']) | {'scripts/prepare_male_recovery_data.py'}
    if not required.issubset({Path(v['path']).relative_to(root).as_posix() for v in loaded.values()}):
        raise ValueError('Missing actual historical helper import')
    if len(loaded)>128 or {'torch','mujoco'}&set(sys.modules): raise ValueError('Forbidden or excessive historical imports')
    return dict(sorted(loaded.items()))


def historical_after(path, p, identity, deadline):
    """Fixed child publication receipt; never substitutes changed reader pins."""
    value={};errors=[]
    try:
        value['historical_identity']=historical_identity(p,deadline,enforce=False)
        if value['historical_identity']!=identity:errors.append('Historical source drift during extraction')
    except Exception as error:errors.append('Historical after: '+type(error).__name__+': '+str(error)[:256])
    item=p['immutable_inputs']['old_manifest']
    try:
        file=Path(item['path']);value['old_manifest']={'bytes':file.stat().st_size,'sha256':file_sha(file,MAX_JSON,deadline)}
        if value['old_manifest']['sha256']!=item['sha256']:errors.append('Old data manifest drift')
    except Exception as error:errors.append('Old manifest after: '+type(error).__name__+': '+str(error)[:256])
    try:value['imported_sources']=imported_historical_sources(identity)
    except Exception as error:errors.append('Import after: '+type(error).__name__+': '+str(error)[:256])
    value.update(status='obtained-historical-after',errors=errors,qualification_claims=[])
    write_payload(path,canonical(value),MAX_JSON,math.inf)
    if errors:raise ValueError('; '.join(errors)[:1024])
    check_deadline(deadline)


def historical_child(context_path):
    p=protocol(); context=read_json(context_path)
    if (set(context)!={'output','deadline','protocol_sha256','script_sha256','historical_identity'} or
            context['protocol_sha256']!=PROTOCOL_SHA or context['script_sha256']!=SELF_SHA or
            type(context['deadline']) is not float or not math.isfinite(context['deadline'])):
        raise ValueError('Fixed historical child context differs')
    output=Path(context['output']).absolute(); deadline=context['deadline']
    # Direct child invocation cannot use immutable inputs as an output target.
    roots=[Path(x['path']).parent for x in p['immutable_inputs'].values()]
    roots += [Path(p[k]['path']).parent for k in ('old_baseline_document','old_recovery_document')]
    roots += [Path(p['source_binding']['old_historical_reader']['root']),Path(p['immutable_inputs']['accepted_collection']['path']).parents[2]]
    for root in roots:
        resolved=root.resolve();actual=output.resolve()
        if actual==resolved or actual.is_relative_to(resolved) or resolved.is_relative_to(actual): raise ValueError('Child output overlaps immutable input tree')
    if Path(context_path).resolve()!=output.resolve()/'historical-context.json': raise ValueError('Exclusive child context path differs')
    identity=historical_identity(p,deadline)
    if identity!=context['historical_identity']: raise ValueError('Historical child startup source differs')
    if any(n=='palimpsest' or n.startswith('palimpsest.') for n in sys.modules): raise ValueError('Child must start before project imports')
    historical=Path(identity['root']); sys.path[:0]=[str(historical/'src'),str(historical/'scripts')]
    try:
        import numpy as np
        import prepare_male_recovery_data as old
        if {'torch','mujoco'}&set(sys.modules):raise ValueError('Forbidden historical imports')
        data,manifest=old.prepare(Path(p['old_baseline_document']['path']),Path(p['old_recovery_document']['path']),deadline=deadline)
        expected=read_json(p['immutable_inputs']['old_manifest']['path'],expected=p['immutable_inputs']['old_manifest']['sha256'])
        if manifest!=expected: raise ValueError('Historical derived manifest differs from published old corpus')
        arrays={}; mapping=[]
        for split in ('train','dev'):
            for episode in data[split]:
                index=len(mapping);prefix=f'source{index:03d}'
                arrays[prefix+'_features']=episode['features'];arrays[prefix+'_targets']=episode['targets']
                mapping.append({'split':split,'run_id':episode['run_id'],'episode':episode['episode'],'ticks':len(episode['targets']),'prefix':prefix})
        if len(mapping)!=14 or data['held_out']: raise ValueError('Historical fixed source roster differs')
        metadata={'derived_manifest':manifest,'arrays':mapping,'imported_sources':imported_historical_sources(identity),'historical_identity':identity}
        stream=io.BytesIO();np.savez(stream,**arrays)
        write_payload(output/'historical-arrays.npz',stream.getvalue(),MAX_TRANSFER,deadline,
            lambda:historical_after(output/'historical-after-arrays.json',p,identity,deadline))
        write_payload(output/'historical-result.json',canonical(metadata),MAX_JSON,deadline,
            lambda:historical_after(output/'historical-after-result.json',p,identity,deadline))
    except Exception as error:
        try:historical_after(output/'historical-after-failure.json',p,identity,deadline)
        except Exception as diagnostic:error.add_note('Historical after failure: '+str(diagnostic)[:1024])
        raise


def read_old_transfer(output, old_manifest, identity):
    import numpy as np
    metadata=read_json(output/'historical-result.json')
    if metadata['derived_manifest']!=old_manifest or metadata['historical_identity']!=identity: raise ValueError('Historical transfer manifest/identity differs')
    imported=metadata['imported_sources']; required=set(protocol()['source_binding']['old_historical_reader']['code']) | {'scripts/prepare_male_recovery_data.py'}
    seen=set();root=Path(identity['root'])
    if not isinstance(imported,dict) or len(imported)>128: raise ValueError('Historical import attestation exceeds cap')
    for item in imported.values():
        path=Path(item['path'])
        if not path.is_absolute() or path.is_symlink() or not path.is_relative_to(root): raise ValueError('Historical import path differs')
        rel=path.relative_to(root).as_posix();seen.add(rel)
        if identity['sources'].get(rel)!=item['sha256'] or file_sha(path,MAX_JSON)!=item['sha256']: raise ValueError('Historical import attestation changed')
    if not required.issubset(seen): raise ValueError('Missing attested historical import')
    ordered=[(split,item) for split in ('train','dev') for item in old_manifest['ordered_sources'][split]]
    mapping=metadata['arrays']
    if len(mapping)!=14 or len(ordered)!=14: raise ValueError('Historical transfer roster differs')
    expected={}
    for i,(item,(split,frozen)) in enumerate(zip(mapping,ordered,strict=True)):
        if item!={'split':split,'run_id':frozen['run_id'],'episode':frozen['episode'],'ticks':frozen['ticks'],'prefix':f'source{i:03d}'}: raise ValueError('Historical transfer order/cursor differs')
        expected[item['prefix']+'_features']=(item['ticks'],388);expected[item['prefix']+'_targets']=(item['ticks'],2)
    path=output/'historical-arrays.npz';file_sha(path,MAX_TRANSFER)
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist()
        if any(x.compress_type!=zipfile.ZIP_STORED for x in infos): raise ValueError('Compressed historical transfer refused')
        if len(infos)!=28 or {x.filename for x in infos}!={n+'.npy' for n in expected} or sum(x.file_size for x in infos)>MAX_TRANSFER: raise ValueError('Unsafe/extra historical NPZ members')
        for info in infos:
            with archive.open(info) as member:
                version=np.lib.format.read_magic(member)
                if version not in ((1,0),(2,0)): raise ValueError('Unsupported transfer NPY header')
                reader=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
                shape,fortran,dtype=reader(member,max_header_size=2048)
                if shape!=expected[info.filename[:-4]] or fortran or dtype!=np.float32: raise ValueError('Unsafe transfer array shape/dtype')
    data={'train':[],'dev':[],'held_out':[]}
    with np.load(path,allow_pickle=False) as arrays:
        for item,(split,frozen) in zip(mapping,ordered,strict=True):
            features=arrays[item['prefix']+'_features'].copy();targets=arrays[item['prefix']+'_targets'].copy()
            if not np.isfinite(features).all() or not np.isfinite(targets).all() or hashlib.sha256(features.tobytes()+targets.tobytes()).hexdigest()!=frozen['feature_target_sha256']: raise ValueError('Historical feature/target bytes differ')
            data[split].append({'run_id':item['run_id'],'episode':item['episode'],'features':features,'targets':targets})
    return data


def geometry_digests(world):
    artifacts, *_=helpers();world=artifacts._world(world)
    zero=lambda x:0.0 if x==0.0 else x
    heading=math.fmod(world['pose'][2],math.tau)
    if heading<0: heading+=math.tau
    if heading==math.tau: heading=0.0
    obstacles=sorted(tuple(zero(x) for x in item) for item in world['obstacles'])
    layout={'arena':zero(world['arena']).hex(),'obstacles':[[x.hex() for x in item] for item in obstacles]}
    scene={**layout,'goal':[zero(x).hex() for x in world['goal']],
           'pose':[zero(world['pose'][0]).hex(),zero(world['pose'][1]).hex(),zero(heading).hex()]}
    digest=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',', ':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()
    return {'layout':digest(layout),'full_scene':digest(scene)}


def raw_payload_update(h, raw):
    import numpy as np
    for name in RAW_PAYLOAD_FIELDS:
        a=np.asarray(raw[name])
        if a.dtype.kind not in 'biuf' or not np.isfinite(a).all(): raise ValueError('Invalid raw episode payload')
        h.update(canonical({'field':name,'shape':list(a.shape),'dtype':a.dtype.str,'bytes':a.nbytes}))
        h.update(a.tobytes(order='C'))


def initial_world(run, episode=0):
    artifacts, *_=helpers();manifest=artifacts._manifest(run);events=artifacts._events(run)
    authored=[x for x in events if x['kind']=='recovery_world_authored']
    if authored:
        if len(authored)!=1 or episode!=0 or manifest.get('profile')!='teacher-recovery-development-v3': raise ValueError('Unsupported authored old scene')
        context=manifest['recovery_world_override'];digest=hashlib.sha256(json.dumps(context,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()
        if (authored[0].get('context')!=context or authored[0].get('override_sha256')!=digest or
                manifest.get('recovery_world_override_sha256')!=digest or manifest.get('initial_world')!=context['new_world']):
            raise ValueError('Old authored scene binding differs')
        return artifacts._world(context['new_world'])
    starts=[x for x in events if x['kind']=='episode_started' and x.get('episode')==episode]
    if len(starts)!=1: raise ValueError('Unique initial world required')
    return artifacts._world(starts[0]['world'])


def disjoint_sources(old_sources, new_sources):
    seen_ids=set();payloads=set();new_groups={}
    for source in [*old_sources,*new_sources]:
        key=(source['run_id'],source['episode'])
        if key in seen_ids: raise ValueError('Duplicate source episode')
        seen_ids.add(key)
        for field in ('feature_target_sha256','raw_payload_sha256'):
            key=(field,source[field])
            if key in payloads: raise ValueError('Duplicate complete source payload')
            payloads.add(key)
    for i,a in enumerate(old_sources):
        for b in old_sources[i+1:]:
            if a['split']!=b['split'] and any(a['geometry'][k]==b['geometry'][k] for k in ('layout','full_scene')):
                raise ValueError('Old train/dev geometry overlaps')
    for source in new_sources:
        if any(any(source['geometry'][k]==old['geometry'][k] for k in ('layout','full_scene')) for old in old_sources):
            raise ValueError('New/old corpus geometry overlaps')
        group=new_groups.setdefault(source['scene_seed'],[])
        if group and (source['geometry']!=group[0]['geometry'] or source['initial_fingerprint']!=group[0]['initial_fingerprint']):
            raise ValueError('Same new scene scientific initial differs')
        for seed,others in new_groups.items():
            if seed!=source['scene_seed'] and any(source['geometry'][k]==others[0]['geometry'][k] for k in ('layout','full_scene')):
                raise ValueError('Distinct new scene geometry repeats')
        group.append(source)
    if set(new_groups)!={3100,3101,3102,3103} or any(sorted(x['learner_seed'] for x in group)!=[10,11,12] for group in new_groups.values()):
        raise ValueError('Exact three-learner scene replication required')


def admit_collection(p, documents):
    *_,nav=helpers();report=documents['accepted_collection'];terminal=documents['collection_terminal'];enclosing=documents['collection_enclosing'];drain=documents['exec_drain']
    if (report.get('status')!='completed-collection' or report.get('profile')!=nav.PROFILE or report.get('study_sha256')!=nav.PLAN_SHA or
            report.get('contact_profile_sha256')!=nav.PROFILE_SHA or report.get('qualification_claims')!=[] or
            report.get('owners_completed')!=12 or type(report.get('numeric_ticks')) is not int or report['numeric_ticks']!=5080 or
            list(report.get('cases',{}))!=[x['id'] for x in nav.CASES] or report.get('source_pins')!=report.get('final_source_pins') or
            report.get('assets_before')!=report.get('assets_after') or report.get('assets_before',{}).get('ok') is not True or
            report.get('identities_before')!=report.get('identities_after') or 'error' in report): raise ValueError('Accepted fixed navigation collection required')
    for value,key in ((terminal,'cleanup'),(enclosing,'outer_cleanup')):
        cleanup=value.get(key,{})
        if (value.get('status')!='completed-collection' or value.get('controls_unchanged') is not True or
                cleanup.get('sampler_stopped') is not True or any(cleanup.get(n)!=[] for n in ('forced_signals','survivors','sample_errors','conflicting_owned_identities')) or 'error' in value):
            raise ValueError('Normal clean collection enclosure required')
    if (terminal.get('inventories_unchanged') is not True or enclosing.get('outer_inventory_unchanged') is not True or
            terminal.get('report_sha256')!=p['immutable_inputs']['accepted_collection']['sha256'] or
            terminal.get('head')!=p['source_binding']['navigation_producer_commit'] or
            drain.get('exec_exitcode')!=0 or type(drain.get('exec_exitcode')) is not int or drain.get('matching_survivors')!=[] or drain.get('forced_signals')!=[]):
        raise ValueError('Collection normal drain/inventory binding differs')
    for key in ('collector_supervisor','launcher_supervisor'):
        value=documents[key]
        if value.get('status')!='completed' or type(value.get('returncode')) is not int or value['returncode']!=0 or 'error' in value or 'failure' in value:
            raise ValueError('Failed collection supervisor cannot admit data')
    return report


def episode_source(run, episode, split, features, targets, deadline, *, world=None):
    artifacts, _, iter_ticks, *_=helpers();digest=hashlib.sha256();count=0
    for raw in iter_ticks(run/'recording'):
        check_deadline(deadline)
        if raw['episode']==episode:raw_payload_update(digest,raw);count+=1
    if count!=len(targets): raise ValueError('Complete raw episode count differs')
    return {'run_id':artifacts._manifest(run)['run_id'],'episode':episode,'split':split,'ticks':count,
        'path':str(run),'feature_target_sha256':hashlib.sha256(features.tobytes()+targets.tobytes()).hexdigest(),
        'raw_payload_sha256':digest.hexdigest(),'raw_payload_fields':list(RAW_PAYLOAD_FIELDS),
        'geometry':geometry_digests(initial_world(run,episode) if world is None else world)}


def advice_arrays(rows, deadline):
    import numpy as np
    _,model,*_=helpers();features=[];targets=[]
    for raw in rows:
        check_deadline(deadline)
        if len(targets)>=600: raise ValueError('Navigation source row cap exceeded')
        features.append(model.features(raw));target=np.asarray(raw['nav_advice_action'])
        if target.shape!=(2,) or target.dtype!=np.float32 or not np.isfinite(target).all():
            raise ValueError('Exact returned advice target required')
        targets.append(target.copy())
    if not targets: raise ValueError('Complete nonempty advice source required')
    return np.stack(features),np.stack(targets)



def validate_after(path, p, reader, historical, documents, checks, deadline, budget=None):
    """Two fixed after receipts, including obtainable changed bytes before refusal."""
    *_,old,_=helpers();value={};errors=[]
    for name,operation in (
        ('reader',lambda:reader_identity(deadline,enforce=False)),
        ('historical',lambda:historical_identity(p,deadline,enforce=False))):
        try:value[name]=operation()
        except Exception as error:errors.append(name+': '+type(error).__name__+': '+str(error)[:256])
    value['documents']={}
    for name,item in {**p['immutable_inputs'],**{k:p[k] for k in ('old_baseline_document','old_recovery_document')}}.items():
        try:
            file=Path(item['path']);observed={'bytes':file.stat().st_size,'sha256':file_sha(file,MAX_JSON,deadline)}
            value['documents'][name]=observed
            if observed['sha256']!=item['sha256']: errors.append('Changed document: '+name)
        except Exception as error:errors.append(name+': '+type(error).__name__+': '+str(error)[:256])
    value['sources']=[]
    for run,files in checks:
        observed={'path':str(run)}
        try:observed['files']=old.inventory(run,files,deadline)
        except Exception as error:
            errors.append(str(run)+': '+type(error).__name__+': '+str(error)[:256]);observed['files']=[]
            # Retain obtainable expected file bytes even when exact inventory refuses.
            for item in files:
                file=run/item['path'];entry={'path':item['path']}
                try:entry.update(bytes=file.stat().st_size,sha256=file_sha(file,160*MiB,deadline))
                except Exception as diagnostic:entry['error']=type(diagnostic).__name__+': '+str(diagnostic)[:128]
                observed['files'].append(entry)
        value['sources'].append(observed)
    if value.get('reader')!=reader:errors.append('Current reader drift')
    if value.get('historical')!=historical:errors.append('Historical reader drift')
    value.update(status='obtained-after-inventory',errors=errors,qualification_claims=[])
    # Failure evidence may be late; it never admits the final data manifest.
    write_payload(path,canonical(value),MAX_JSON,math.inf,budget=budget)
    if errors:raise ValueError('; '.join(errors)[:1024])
    check_deadline(deadline)

def prepare(output, deadline=None):
    started=time.monotonic();deadline=started+180 if deadline is None else min(deadline,started+180)
    p=protocol();artifacts,model,iter_ticks,old,nav=helpers();reader=reader_identity(deadline)
    documents=pinned_documents(p,deadline);report=admit_collection(p,documents)
    historical=historical_identity(p,deadline);output=output_path(output,p)
    from palimpsest.storage import StorageBudget,StorageLimits
    from palimpsest.evaluate import bounded_process
    budget=StorageBudget((output,),StorageLimits(max_bytes=64*MiB,min_free_bytes=1024**3))
    budget.check(48*MiB,path=output);output.mkdir(parents=True,exist_ok=False)
    context={'output':str(output),'deadline':float(deadline),'protocol_sha256':PROTOCOL_SHA,'script_sha256':SELF_SHA,'historical_identity':historical}
    write_payload(output/'historical-context.json',canonical(context),MAX_JSON,deadline,budget=budget)
    result=bounded_process([sys.executable,'-I',str(SCRIPT),'--historical-old-data-child',str(output/'historical-context.json')],
        output/'historical-supervision',min(120,max(0.001,deadline-time.monotonic())),log_max_bytes=MiB,storage_budget=budget)
    if result.get('status')!='completed' or result.get('returncode')!=0 or 'failure' in result or 'error' in result:
        error=ValueError('Historical source child did not complete normally')
        try:validate_after(output/'after-historical-child-failure.json',p,reader,historical,documents,[],deadline,budget)
        except Exception as diagnostic:error.add_note('After child failure: '+str(diagnostic)[:1024])
        raise error
    budget.check(0,path=output);old_manifest=documents['old_manifest'];data=read_old_transfer(output,old_manifest,historical)
    if old.validate_splits(data)!={'train':2117,'dev':1228,'held_out':0}: raise ValueError('Old fixed arm counts differ')
    roots={};checks=[];old_sources=[];new_sources=[];old_bytes=new_bytes=0
    for entry in documents['old_baseline_document']['runs']:
        run=Path(p['old_baseline_document']['path']).parent/'runs'/entry['run_id'];roots[entry['run_id']]=run
        files=old.inventory(run,entry['files'],deadline);checks.append((run,files));old_bytes+=sum(x['bytes'] for x in files)
    for entry in old_manifest['recovery_admission']:
        run=Path(entry['path']);roots[entry['run_id']]=run
        files=old.inventory(run,entry['files'],deadline);checks.append((run,files));old_bytes+=sum(x['bytes'] for x in files)
    for split in ('train','dev'):
        for ep in data[split]: old_sources.append(episode_source(roots[ep['run_id']],ep['episode'],split,ep['features'],ep['targets'],deadline))
    augmented={'train':list(data['train']),'dev':list(data['dev']),'held_out':[]}
    for case in nav.CASES:
        check_deadline(deadline);item=report['cases'][case['id']];root=Path(p['immutable_inputs']['accepted_collection']['path']).parent
        stage=root/case['id'];run=artifacts._safe_path(item['run']);artifacts._id(run.name)
        if (run.parent!=stage or item.get('case')!=case or item.get('status')!='completed-recording' or
                item.get('result_path')!=str(stage/'result.json')): raise ValueError('Fixed navigation source path/case differs')
        owner=read_json(stage/'result.json',expected=item['result_sha256']);identity=report['identities_before'][str(case['learner_seed'])]
        if (owner.get('case')!=case or owner.get('outcome')!=item.get('outcome') or item.get('contact_incidence')!=owner.get('contact_incidence') or
                item.get('supervision',{}).get('status')!='completed' or item['supervision'].get('returncode')!=0 or
                'failure' in item['supervision'] or 'error' in item['supervision']): raise ValueError('Navigation owner normal identity/outcome differs')
        count=nav.admit_record(run,owner,identity);manifest=artifacts._manifest(run)
        if any(manifest.get(k) is not None for k in ('parent_run_id','replay_source_run_id','replay_mode','initial_memory')): raise ValueError('Navigation branch/replay lineage refused')
        prefix=run.relative_to(root).as_posix()+'/'
        files=[{'path':name[len(prefix):],'bytes':(root/name).stat().st_size,'sha256':value}
            for name,value in report['artifacts_sha256'].items() if name.startswith(prefix)]
        files=old.inventory(run,files,deadline);checks.append((run,files));new_bytes+=sum(x['bytes'] for x in files)
        features,targets=advice_arrays(iter_ticks(run/'recording'),deadline)
        ep={'run_id':run.name,'episode':0,'features':features,'targets':targets}
        if len(targets)!=count: raise ValueError('Complete navigation advice sequence differs')
        source=episode_source(run,0,'train',ep['features'],ep['targets'],deadline,world=owner['initial_world'])
        source.update(scene_seed=case['scene_seed'],learner_seed=case['learner_seed'],initial_fingerprint=owner['initial_fingerprint'],
            outcome=owner['outcome'],label='returned-analytic-teacher-advice',files=files)
        new_sources.append(source);augmented['train'].append(ep)
    if len(checks)!=26 or old_bytes>3*1024**3 or new_bytes>3*1024**3 or old_bytes+new_bytes>6*1024**3: raise ValueError('Separate corpus byte/source budget differs')
    if old.validate_splits(augmented,check_counts=False)!={'train':7197,'dev':1228,'held_out':0}: raise ValueError('Augmented exact arm counts differ')
    disjoint_sources(old_sources,new_sources)
    manifest={'status':'prepared-navigation-advice-research-only','schema_version':1,'protocol_sha256':PROTOCOL_SHA,'qualification_claims':[],
        'input_documents':p['immutable_inputs'],'historical_reader':historical,'current_reader_sources':reader,'adapter_sha256':SELF_SHA,
        'feature_protocol':model.FEATURE_PROTOCOL,'feature_protocol_sha256':model.digest(model.FEATURE_PROTOCOL),
        'old_manifest_sha256':p['immutable_inputs']['old_manifest']['sha256'],'old_sources':old_sources,'new_sources':new_sources,
        'counts':p['counts'],'source_bytes':{'old':old_bytes,'new':new_bytes,'combined':old_bytes+new_bytes},
        'labels':{'old':'unchanged executed targets','new':'nav_advice_action'},'raw_payload_fields':list(RAW_PAYLOAD_FIELDS),
        'arms':{'old':old_manifest['ordered_sources'],'augmented':{split:[{'run_id':ep['run_id'],'episode':ep['episode'],'ticks':len(ep['targets']),
            'feature_target_sha256':hashlib.sha256(ep['features'].tobytes()+ep['targets'].tobytes()).hexdigest()} for ep in augmented[split]] for split in ('train','dev','held_out')}}}
    validate_after(output/'after-admission.json',p,reader,historical,documents,checks,deadline,budget)
    budget.check(0,path=output)
    validate=lambda:validate_after(output/'after-final-sync.json',p,reader,historical,documents,checks,deadline,budget)
    write_payload(output/'data-manifest.json',canonical(manifest),MAX_JSON,deadline,validate,budget)
    return manifest


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--historical-old-data-child',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if args.historical_old_data_child is not None:
        if args.output is not None: parser.error('Child context only')
        historical_child(args.historical_old_data_child);return 0
    if args.output is None: parser.error('Fresh --output required')
    output=output_path(args.output,protocol())
    if output.exists(): raise FileExistsError('Fresh output required')
    try: prepare(output)
    except Exception as error:
        if output.is_dir():
            try: write_payload(output/'failure.json',canonical({'status':'failed-admission','error':{'type':type(error).__name__,'message':str(error)[:1024]},'qualification_claims':[]}),MAX_JSON,math.inf)
            except Exception as diagnostic:error.add_note('Failure evidence also failed: '+str(diagnostic)[:256])
        raise
    return 0


if __name__=='__main__': raise SystemExit(main())
