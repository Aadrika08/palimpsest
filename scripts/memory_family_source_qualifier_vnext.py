"""Fixed independent genesis cell qualifier. Produces an unaccepted candidate only."""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
import sys
from scripts import memory_family_source_records_vnext as wire


def _authored_identity(job,lease):
    auth=wire.decode(lease._authorization_bytes,262144); descriptor=lease._load['model']['manifest']
    if descriptor['path']!=job['workspace_root']+'/freeze/metadata/authored-model-identity.json': raise ValueError('Authored model fixed identity slot differs')
    value=wire.decode(lease._read(descriptor,262144),262144)
    wire.fields(value,('schema','fixture_id','input_width','hidden_width','runtime_sources','model_sources','weights','graph','python_version','torch_version','dtype','device','threads','training','requires_grad','scope','claims'))
    wire.schema(value,'model-identity',True)
    for name,literal in dict(fixture_id=auth['fixture_id'],input_width=4813,dtype='torch.float32',device='cpu',threads=1,training=False,requires_grad=False,scope='software-unit-only').items(): wire._literal(value[name],literal)
    wire.integer(value['hidden_width'],1,4096); wire.text(value['python_version']); wire.text(value['torch_version'])
    for name,maximum in [('runtime_sources',64),('model_sources',64),('weights',32),('graph',32)]:
        wire._descriptors(value[name],maximum,cap=1024*wire.MiB)
        if not value[name]: raise ValueError('Empty authored identity roster')
        for row in value[name]:
            if not row['path'].startswith(job['workspace_root']+'/') and not (name=='runtime_sources' and wire._authored_external_source(row)): raise ValueError('Authored identity outside fixture')
            wire._literal(lease._registry.binding(row['path']).descriptor,row)
    wire._literal(value['runtime_sources'],lease._load['runtime_requirements']['pins']['required_sources'])
    model=lease._load['model']
    if model['checkpoint'] not in value['weights'] or any(row not in value['graph'] for row in model['graph']): raise ValueError('Authored model frozen references differ')
    return value


def _guard_policy(job,lease,policy):
    from palimpsest.flynn import FlynnPolicy
    from scripts.memory_source_parent_entry_vnext import _lease_kind
    from scripts.memory_family_cell_replay_v4 import _pinned_policy
    lease.recheck()
    if _lease_kind(lease)=='actual':
        _pinned_policy(policy)
    else:
        identity=_authored_identity(job,lease); torch=policy.torch
        if (type(policy) is not FlynnPolicy or type(policy.agent).__module__!='agents.connectome_rnn_agent'
                or type(policy.agent).__name__!='ConnectomeAgent' or type(policy.agent.cell).__module__!='models.connectome_rnn_model'
                or type(policy.agent.cell).__name__!='LeakyConnectomeRNNCell' or policy.agent.cell.Nin!=4813
                or policy.agent.cell.N!=identity['hidden_width'] or str(policy.device)!='cpu' or policy.dtype!=torch.float32
                or torch.get_num_threads()!=1 or any(module.training for module in policy.agent.modules())
                or any(value.requires_grad for value in policy.agent.parameters())
                or identity['python_version']!='.'.join(map(str,sys.version_info[:3]))
                or identity['torch_version']!=str(torch.__version__)):
            raise ValueError('Fixed authored Flynn/cell/tensor/runtime identity differs')
        module_sources={row['path'] for row in identity['model_sources']}
        for name in ('agents.connectome_rnn_agent','models.connectome_rnn_model'):
            if str(Path(sys.modules[name].__file__).absolute()) not in module_sources: raise ValueError('Authored upstream module source differs')
        model=lease._load['model']
        if policy.provenance['checkpoint_sha256']!=model['checkpoint']['sha256'] or policy.provenance['edge_sha256']!=model['graph'][0]['sha256'] or policy.provenance['seed']!=job['case']['seed']: raise ValueError('Authored policy pins differ')
    lease.recheck()


def qualify_source(job,closed_source,live_inputs):
    from scripts.memory_source_parent_entry_vnext import _require_role
    _require_role(job,live_inputs,'qualifier'); return _qualify_source_core(job,closed_source,live_inputs)


def _qualify_authored_source(job,closed_source,live_inputs):
    from scripts.memory_source_parent_entry_vnext import _require_role
    _require_role(job,live_inputs,'qualifier',True); return _qualify_source_core(job,closed_source,live_inputs)


def _state(policy):
    from palimpsest.snapshots import state_digest
    def array(value):
        if type(value) is dict: return {key:array(item) for key,item in value.items()}
        return None if value is None else value.detach().cpu().numpy().copy()
    return state_digest(tuple(array(item) for item in policy._state()))


def _cache(policy):
    from palimpsest.snapshots import state_digest
    cell=policy.agent.cell; result={}
    for name in ('_cached_alphas','_alphas_dirty'):
        value=getattr(cell,name,None)
        if hasattr(value,'detach'): value=value.detach().cpu().numpy().copy()
        result[name]=dict(present=hasattr(cell,name),value=value)
    return state_digest(result)


def _qualify_source_core(job,closed,lease):
    from palimpsest import snapshots
    from palimpsest.flynn import load_policy
    from scripts.memory_family_cell_replay_v4 import _replay_rows
    from scripts.memory_family_source_raw_audit_vnext import _inspect_closed,_verify_registration
    from scripts.memory_family_source_numeric_vnext import _compare_candidate
    from scripts.memory_family_source_runtime_vnext import _OwnedPolicyReferences,_release_source_owned_policy_refs,_LoadedPolicyIdentity
    from scripts.memory_source_parent_entry_vnext import _lease_kind
    authored=_lease_kind(lease)=='authored'; run=job['source_run_id']; k=f'output/controls/{run}'
    A,data=_inspect_closed(job,closed,lease)
    def record(relative,cap):
        absolute=job['workspace_root']+'/'+relative; binding=lease._registry.binding(absolute)
        return wire.decode(lease._read(binding.descriptor,cap),cap),dict(binding.descriptor,path=relative)
    E,E_d=record(k+'/registration/registration.json',65536)
    _verify_registration(job,closed,A,E,lease)
    V,V_d=record(k+'/conversion/conversion.json',131072); C,C_d=record(k+'/conversion/commit.json',16384)
    wire.schema(V,'numeric-conversion',authored); wire.schema(C,'numeric-commit',authored)
    if C['conversion']!=V_d or C['numeric_manifest']!=V['numeric_manifest']: raise ValueError('Qualifier V/C binding differs')
    data,manifest=_compare_candidate(job,closed,A,E,lease,V['inventory'],data)
    wire.fields(V,('schema','profile','source_closure','producer_registration','raw_audit','snapshot','case_id','source_run_id','numeric_manifest','inventory','comparison','ledger','status','claims'))
    wire.fields(C,('schema','profile','source_closure','producer_registration','raw_audit','snapshot','conversion','numeric_manifest','status','claims'))
    A_d=wire.describe(k+'/raw-audit/audit.json',wire.encode(A,131072))
    for value in (V,C):
        for name,expected in dict(profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_registration=E_d,raw_audit=A_d,snapshot=closed.snapshot,status='candidate-unqualified').items(): wire._literal(value[name],expected)
    wire._literal(V['case_id'],job['case']['case_id']); wire._literal(V['source_run_id'],run)
    wire._literal(V['comparison'],dict(rows=len(data['rows']),base_arrays=16,companion_arrays=3,all_raw_fields_equal=True,selected_pixels_equal=True,event_bytes_equal=True,manifest_bytes_equal=True))
    inventory=wire._descriptors(V['inventory'],83,False,32*wire.MiB)
    total=sum(row['size_bytes'] for row in inventory); dense=19646*len(data['rows'])
    import math
    selected={math.floor(i*(len(data['rows'])-1)/5) for i in range(6)}|set(range(max(0,len(data['rows'])-2),len(data['rows'])))
    pixels=98304*len(selected); event_bytes=len(data['events_bytes'])
    wire._literal(V['ledger'],dict(candidate_bytes=total,dense_bytes=dense,selected_pixel_bytes=pixels,event_bytes=event_bytes,metadata_physical_bytes=sum(row['size_bytes'] for row in inventory if row['path'].endswith('.json')),overhead_bytes=total-dense-pixels-event_bytes))
    if total>32*wire.MiB or not 0<=total-dense-pixels-event_bytes<=wire.MiB: raise ValueError('Qualifier independent physical ledger differs')
    manifest_path=f"output/.pending/{job['case']['case_id']}/source/numeric/manifest.json"
    expected_manifest=next(row for row in inventory if row['path']==manifest_path)
    wire._literal(V['numeric_manifest'],expected_manifest); wire._literal(C['numeric_manifest'],expected_manifest)

    # No policy acquisition occurs before all raw, SNP, candidate and identity leases.
    if authored: _authored_identity(job,lease)
    model=lease._load['model']; refs=_OwnedPolicyReferences(); policy=agent=checker=custody_check=None; failures=[]; replay=None
    try:
        lease.recheck()
        policy=load_policy(Path(lease._roots['repo']),Path(model['graph'][0]['path']),Path(model['checkpoint']['path']),'cpu',job['case']['seed'])
        refs.policy=policy; agent=refs.agent=policy.agent; _guard_policy(job,lease,policy)
        tensors_before=snapshots.state_digest(snapshots.controller_hashes(policy)); state_before=_state(policy); cache_before=_cache(policy)
        checker=refs.custody_check=_LoadedPolicyIdentity(job,lease,refs)
        refs.replay_rows=data['rows']; refs.decoded_snapshot=data['snapshot']
        replay=refs.replay_result=_replay_rows(policy=policy,rows=refs.replay_rows,source_snapshot=refs.decoded_snapshot,operation='source',first_tick=0,input_width=4813,deadline=lease._deadline_ns/1e9,custody_check=checker)
        tensors_after=snapshots.state_digest(snapshots.controller_hashes(policy)); state_after=_state(policy); cache_after=_cache(policy)
        if (tensors_before,state_before,cache_before)!=(tensors_after,state_after,cache_after): raise ValueError('Qualifier state/cache/tensors were not restored')
        _guard_policy(job,lease,policy); lease.recheck()
        replay=dict(replay,input_width=4813,first_tick=0,last_tick=len(data['rows'])-1,source_hidden_sha256=snapshots.state_digest(data['snapshot']['policy']['hidden']),tensors_before_sha256=tensors_before,tensors_after_sha256=tensors_after,state_before_sha256=state_before,state_after_sha256=state_after,cache_before_sha256=cache_before,cache_after_sha256=cache_after,source_bytes_unchanged=True)
        if replay['final_hidden_sha256']!=replay['source_hidden_sha256']: raise ValueError('Qualifier acquired endpoint digest differs')
    except BaseException as error:
        lease._state='poisoned'; failures.append(error)
    finally:
        try: _release_source_owned_policy_refs(refs)
        except BaseException as error: failures.append(error)
        policy=agent=checker=custody_check=None
        data=None
    if failures: raise wire.errors('Source independent qualifier failed',failures)
    replay['policy_closed']=True
    load=lease._load; provenance=load['provenance']
    Q=dict(schema=wire.record_schema('qualification-candidate',authored),profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_plan=job['readset']['producer_plan'],job=closed.job,producer_registration=E_d,raw_audit=V['raw_audit'],snapshot=closed.snapshot,numeric_conversion=V_d,numeric_commit=C_d,numeric_manifest=V['numeric_manifest'],case_id=job['case']['case_id'],case_sha256=__import__('palimpsest.memory',fromlist=['sha256']).sha256(job['case']),source_run_id=run,attempt_id=job['attempt_id'],authorization_sha256=hashlib.sha256(lease._authorization_bytes).hexdigest(),load_environment=job['readset']['load_environment'],runtime=dict(reference=load['runtime_reference'],owner_source=load['runtime_requirements']['pins']['owner_source'],loaded_sources=load['runtime_requirements']['pins']['required_sources'],interpreter={key:provenance['interpreter'][key] for key in ('path','size_bytes','sha256')},python_version=provenance['interpreter']['python_version'],torch_version='2.9.0',device='cpu',dtype='torch.float32',threads=1),model=model,namespaces=dict(history=job['readset']['history_namespace'],training=job['readset']['training_namespace']),replay=replay,scope='software-unit-only' if authored else 'encoded-source-cell',status='candidate-unaccepted',claims=wire.CLAIMS.copy())
    Q_d=lease._publish(k+'/qualifier/candidate.json',Q,131072)
    lease._hold_stage([Q_d],exact=(k+'/qualifier',)); lease.recheck(); return Q
