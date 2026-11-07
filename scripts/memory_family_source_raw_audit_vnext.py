"""Independent direct source raw audit. No old admission envelopes are relabeled."""
from __future__ import annotations
import copy
import hashlib
import io
from pathlib import Path
import zipfile
from scripts import memory_family_source_records_vnext as wire


def audit_source(job,closed_source,live_inputs):
    from scripts.memory_source_parent_entry_vnext import _require_role
    _require_role(job,live_inputs,'raw-audit'); return _audit_source_core(job,closed_source,live_inputs)


def _audit_authored_source(job,closed_source,live_inputs):
    from scripts.memory_source_parent_entry_vnext import _require_role
    _require_role(job,live_inputs,'raw-audit',True); return _audit_source_core(job,closed_source,live_inputs)


def _snapshot(job,closed,lease):
    from palimpsest import snapshots
    lease.recheck(); absolute=job['workspace_root']+'/'+closed.snapshot['path']
    binding=lease._registry.binding(absolute)
    payload=lease._raw(closed.snapshot,16*wire.MiB)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        infos=archive.infolist(); names=[item.filename for item in infos]
        if (len(infos)>8192 or len(names)!=len(set(names)) or 'metadata.json' not in names
                or sum(item.file_size for item in infos)>16*wire.MiB
                or archive.getinfo('metadata.json').file_size>8*wire.MiB
                or any(item.compress_type!=zipfile.ZIP_STORED or item.flag_bits or item.is_dir() for item in infos)):
            raise ValueError('Bounded original SNP archive differs')
    # Original serializer/decoder through the already-owned FD, never a named reopen.
    result=snapshots.read_snapshot(Path('/proc/self/fd')/str(binding.fd))
    lease.recheck()
    snapshots.validate_decision_snapshot(result)
    return result


def _inspect_closed(job,closed,lease):
    from palimpsest import artifacts,memory,snapshots,profiles,memory_decision_world as world
    from scripts import memory_family_raw_audit_v4 as old, memory_family_compact_v4 as compact
    from scripts import memory_family_oracle_v3 as oracle
    from scripts.memory_family_oracle_admission_v3 import _policy_bindings
    from scripts.memory_family_source_numeric_vnext import _decode_npz,RAW
    from scripts.memory_family_source_runtime_vnext import ClosedSource
    from scripts.memory_source_parent_entry_vnext import _lease_kind
    if type(closed) is not ClosedSource or closed is not lease._closed_source: raise TypeError('Parent-owned ClosedSource required')
    authored=_lease_kind(lease)=='authored'; run=job['source_run_id']; case=job['case']; r=f"output/.pending/{case['case_id']}/.raw/{run}"
    expected_paths=[r+'/recording/manifest.json',r+'/recording/events.jsonl',r+'/worker-report.json',*[f'{r}/recording/chunks/{i:06}.npz' for i in range((closed.boundary+31)//32)]]
    inventory=[closed.raw_manifest,closed.raw_events,closed.worker_report,*closed.raw_chunks]
    if sorted(d['path'] for d in inventory)!=sorted(expected_paths): raise ValueError('Closed raw roster differs')
    lease._hold_stage([*inventory,closed.owner,closed.snapshot],exact=(r,f"output/.pending/{case['case_id']}/source/snapshots"))
    manifest_raw=lease._raw(closed.raw_manifest,65536); events_raw=lease._raw(closed.raw_events,7*wire.MiB)
    manifest=artifacts._json(manifest_raw); report=wire.decode(lease._raw(closed.worker_report,32768),32768); owner=wire.decode(lease._raw(closed.owner,16384),16384)
    wire.schema(owner,'owner',authored); wire.schema(report,'worker-report',authored)
    wire.fields(owner,('schema','profile','source_closure','producer_plan','job','case_id','case_sha256','source_run_id','owner_source','operation','condition','status','claims'))
    wire.fields(report,('schema','job','source_run_id','case_id','case_sha256','operation','condition','status','snapshot','total_ticks','final_phase','world_state','event_prefix','claims'))
    for record in (owner,report):
        for name,value in dict(job=closed.job,source_run_id=run,case_id=case['case_id'],case_sha256=memory.sha256(case),operation='source',condition=None).items(): wire._literal(record[name],value)
    wire._literal(owner['status'],'owner-intent-unqualified'); wire._literal(report['status'],'recorded-unqualified'); wire._literal(report['snapshot'],closed.snapshot)
    registration=manifest.get('memory_source_registration_vnext')
    wire.fields(registration,('schema','profile','source_closure','producer_plan','job','case','source_run_id','operation','condition'))
    if registration['schema']!=wire.record_schema('raw-registration',authored): raise ValueError('Raw registration domain')
    for name,value in dict(profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_plan=job['readset']['producer_plan'],job=closed.job,case=case,source_run_id=run,operation='source',condition=None).items(): wire._literal(registration[name],value)
    if 'memory_family_oracle_admission_v3' in manifest: raise ValueError('Old admission envelope forbidden')
    for name,value in dict(run_id=run,controller='flynn',profile='flynn',texture='checker',seed=case['seed'],requested_device='cpu',teacher_privileged=False,recording_max_bytes=512*wire.MiB,status='completed',source_bootstrap_epoch='canonical-prepared-vnext-v1',memory_case=case,memory_case_sha256=memory.sha256(case),scenario=profiles.validate_decision('memory-decision-v2','checker','flynn',profile_sha256=case['profile_sha256']),final_phase='paused',parent_run_id=None,parent_event_prefix=None,last_outcome=None,population_names=list(profiles.POPULATIONS) if hasattr(profiles,'POPULATIONS') else manifest.get('population_names')).items(): wire._literal(manifest.get(name),value)
    if not events_raw.endswith(b'\n') or not 1<=events_raw.count(b'\n')<=50000: raise ValueError('Raw event lines/count')
    events=[artifacts._json(line) for line in events_raw.splitlines()]
    oracle._events(copy.deepcopy(events),run,'source raw events')
    if any(event.get('kind') in old.FORBIDDEN_EVENTS|{'application_restored','memory_selector_configured','memory_decision_armed','intervention','memory_world_changed'} for event in events): raise ValueError('Forbidden source event')
    for event in events:
        if event['kind']!='chunk' and event.get('run_id')!=run: raise ValueError('Raw run-bound canonical UUID differs')
    chunks=[event for event in events if event['kind']=='chunk']; rows=[]
    for index,(event,desc) in enumerate(zip(chunks,closed.raw_chunks)):
        lease.recheck(); count=wire.integer(event['count'],1,32)
        if event['path']!=f'chunks/{index:06}.npz' or event['start']!=len(rows) or event['episode']!=0 or event['sha256']!=desc['sha256'] or count!=min(32,closed.boundary-len(rows)): raise ValueError('Raw chunk range/hash differs')
        wire._literal(event['arrays'],{name:dict(dtype=dtype,shape=list(shape)) for name,(dtype,shape) in RAW.items()})
        arrays=_decode_npz(lease._raw(desc,7*wire.MiB),RAW,count,canonical=False)
        for offset in range(count): rows.append(dict(episode=0,tick=event['start']+offset,**{name:array[offset].copy() for name,array in arrays.items()}))
        lease.recheck()
    if not 1<=len(rows)==closed.boundary<=1200 or len(chunks)!=len(closed.raw_chunks) or len(chunks)!=(len(rows)+31)//32: raise ValueError('Source raw exact row/chunk count')
    if manifest.get('recorded_ticks')!=len(rows) or manifest.get('recorded_chunks')!=len(chunks) or manifest.get('recorded_events')!=len(events): raise ValueError('Raw writer terminal counts differ')
    snapshot=_snapshot(job,closed,lease); app=snapshot['application']
    parsed,task,state,boundary=old._source_application(app,case,run,report)
    if report['final_phase']!='paused' or report['total_ticks']!=len(rows): raise ValueError('Source report terminal differs')
    compact._prefix(closed.prefix,events_raw)
    if app['event_prefix']!=closed.prefix or report['event_prefix']!=closed.prefix: raise ValueError('Source SNP event prefix differs')
    registered=[event for event in events if event['kind']=='snapshot_registered']
    if len(registered)!=1 or registered[0].get('initial') is not True or registered[0].get('filename')!='initial.snp' or registered[0].get('sha256')!=closed.snapshot['sha256'] or registered[0]['sequence']!=closed.prefix['event_count']: raise ValueError('Sole source SNP registration/prefix cut differs')
    projection,camera_sha,row_sha=old._audit_rows(rows,'source'); projected=compact._project_rows(rows,'source')
    oracle._source_evidence(case,parsed,events,copy.deepcopy(projection)); calls=old._policy_calls(events); _policy_bindings(dict(events=events,rows=rows))
    sequences=dict(camera_sha256=camera_sha,row_sha256=row_sha,non_chunk_sequences_sha256=memory.sha256([e['sequence'] for e in events if e['kind']!='chunk']),legacy_chunks_sha256=memory.sha256([[e[key] for key in ('sequence','path','sha256','episode','start','count','arrays')] for e in chunks]),trace_sha256=compact._trace_digest(projected))
    if camera_sha!=compact._sequence_hash(projected,compact.DIGEST_FIELDS[:-1]) or row_sha!=compact._sequence_hash(projected,('row_digest',)): raise ValueError('Independent row/camera digest differs')
    recording=sum(d['size_bytes'] for d in inventory if d!=closed.worker_report); support=closed.worker_report['size_bytes']; total=recording+support
    wire.integer(total,1,512*wire.MiB)
    A=dict(schema=wire.record_schema('raw-audit',authored),profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_plan=job['readset']['producer_plan'],job=closed.job,case_id=case['case_id'],case_sha256=memory.sha256(case),source_run_id=run,owner=closed.owner,worker_report=closed.worker_report,snapshot=closed.snapshot,raw_inventory=dict(files=sorted(inventory,key=lambda d:d['path']),file_count=len(inventory),recording_bytes=recording,support_bytes=support,total_bytes=total),counts=dict(rows=len(rows),chunks=len(chunks),events=len(events),first_tick=0,last_tick=len(rows)-1),prefix=closed.prefix,terminal=dict(manifest_status='completed',phase='paused',episode=0,total_ticks=len(rows),last_tick=len(rows)-1,world_state_sha256=memory.sha256(state),memory_state_sha256=memory.sha256(task),application_sha256=memory.sha256(app),unarmed=True),policy=dict(calls=len(calls),bindings_sha256=memory.sha256([{key:e[key] for key in ('tick','observation_sha256','cameras_sha256','result_sha256')} for e in calls])),sequences=sequences,claims=wire.CLAIMS.copy())
    lease.recheck()
    return A,dict(rows=rows,snapshot=snapshot,manifest=manifest,manifest_bytes=manifest_raw,events=events,events_bytes=events_raw,projected=projected,chunks=chunks)


def _audit_source_core(job,closed,lease):
    A,_=_inspect_closed(job,closed,lease)
    descriptor=lease._publish(f"output/controls/{job['source_run_id']}/raw-audit/audit.json",A,131072)
    lease._hold_stage([descriptor],exact=(f"output/controls/{job['source_run_id']}/raw-audit",)); return A


def _verify_registration(job,closed,A,E,lease):
    from scripts.memory_source_parent_entry_vnext import _lease_kind
    authored=_lease_kind(lease)=='authored'; wire.schema(E,'producer-registration',authored)
    wire.fields(E,('schema','profile','source_closure','producer_plan','case','source_run_id','job','owner_record','snapshot','raw_audit','controls','claims'))
    A_d=wire.describe(f"output/controls/{job['source_run_id']}/raw-audit/audit.json",wire.encode(A,131072))
    expected=dict(profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_plan=job['readset']['producer_plan'],case=job['case'],source_run_id=job['source_run_id'],job=closed.job,owner_record=closed.owner,snapshot=closed.snapshot,raw_audit=A_d)
    for name,value in expected.items(): wire._literal(E[name],value)
    controls=E['controls']; wire.fields(controls,('job','supervisor','stdout','stderr','cleanup','audit'))
    wire._literal(controls['job'],closed.job); wire._literal(controls['audit'],A_d)
    for name,filename in [('supervisor','supervisor.json'),('stdout','stdout'),('stderr','stderr'),('cleanup','cleanup.json')]:
        relative=f"output/controls/{job['source_run_id']}/producer/{filename}"
        binding=lease._registry.binding(job['workspace_root']+'/'+relative)
        wire._literal(controls[name],dict(binding.descriptor,path=relative))
    lease.recheck()
