"""Direct bounded source 16+3 codec; exact physical bytes, no admission flags."""
from __future__ import annotations
import hashlib
import io
import math
import struct
import zipfile
from scripts import memory_family_source_records_vnext as wire
from scripts import memory_family_compact_v4 as compact
BASE={name:(dtype,shape) for name,dtype,shape,_ in compact.ROW_FIELDS}
COMPANION=dict(latency=('<f8',()),step_latency=('<f8',()),population_stats=('<f8',(3,4)))
RAW={name:BASE[name] for name in compact.RETAINED}
RAW.update({name:('|u1',(128,128,3)) for name in compact.CAMERAS}); RAW.update(COMPANION)


def _encode_npz(arrays):
    import numpy as np
    with io.BytesIO() as output:
        np.savez(output,**arrays); return output.getvalue()


def _decode_npz(payload,spec,count,canonical=True):
    import numpy as np
    wire.integer(count,1,1200)
    if type(payload) is not bytes: raise ValueError('NPZ bytes required')
    maximum=sum((128+math.prod((count,*shape))*np.dtype(dtype).itemsize) for dtype,shape in spec.values())
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos=archive.infolist(); names=[i.filename for i in infos]
            if (len(names)!=len(spec) or set(names)!={name+'.npy' for name in spec} or len(names)!=len(set(names))
                    or archive.comment or any(i.flag_bits or i.compress_type!=zipfile.ZIP_STORED or i.comment for i in infos)
                    or sum(i.file_size for i in infos)>maximum): raise ValueError('NPZ members/expansion differ')
            # Reject trailing garbage before any array allocation.
            eocd=payload.rfind(b'PK\x05\x06')
            if eocd<0 or eocd+22!=len(payload): raise ValueError('NPZ trailing bytes/comment')
            result={}
            for name,(dtype,shape) in spec.items():
                raw=archive.read(name+'.npy'); stream=io.BytesIO(raw)
                if np.lib.format.read_magic(stream)!=(1,0): raise ValueError('NPY version differs')
                found,fortran,dt=np.lib.format.read_array_header_1_0(stream,max_header_size=128)
                expected_shape=(count,*shape)
                if found!=expected_shape or dt.str!=dtype or dt.hasobject or fortran or stream.tell()!=128 or len(raw)!=128+math.prod(found)*dt.itemsize: raise ValueError('NPY shape/dtype/header/expansion differs')
                array=np.frombuffer(raw,dtype=dt,offset=128).reshape(found)
                if dt.kind in 'fc' and not np.isfinite(array).all(): raise ValueError('Nonfinite source array')
                result[name]=array.copy()
        if canonical and _encode_npz(result)!=payload: raise ValueError('NPZ bytes not canonical')
        return result
    except (OSError,zipfile.BadZipFile,KeyError,EOFError,struct.error) as error: raise ValueError('Invalid bounded NPZ') from error


def convert_source(job,closed_source,A,E,live_inputs):
    from scripts.memory_source_parent_entry_vnext import _require_role
    _require_role(job,live_inputs,'conversion'); return _convert_source_core(job,closed_source,A,E,live_inputs)


def _convert_authored_source(job,closed_source,A,E,live_inputs):
    from scripts.memory_source_parent_entry_vnext import _require_role
    _require_role(job,live_inputs,'conversion',True); return _convert_source_core(job,closed_source,A,E,live_inputs)


def _convert_source_core(job,closed,A,E,lease):
    import numpy as np
    from scripts.memory_family_source_raw_audit_vnext import _inspect_closed,_verify_registration
    from scripts.memory_source_parent_entry_vnext import _lease_kind,_publish_bytes,_publication_floor
    independently,data=_inspect_closed(job,closed,lease); wire._literal(A,independently)
    authored=_lease_kind(lease)=='authored'; _verify_registration(job,closed,A,E,lease)
    run=job['source_run_id']; case=job['case']; k=f'output/controls/{run}'; prefix=f"output/.pending/{case['case_id']}/source/numeric/"
    A_d=wire.describe(k+'/raw-audit/audit.json',wire.encode(A,131072)); E_d=wire.describe(k+'/registration/registration.json',wire.encode(E,65536))
    if E['snapshot']!=closed.snapshot or E['raw_audit']!=A_d or E['job']!=closed.job: raise ValueError('Conversion registration differs')
    roster={row['path']:row for row in wire.output_roster(case['case_id'],run)}; files={}; raw_rows=data['rows']; projected=data['projected']
    def emit(relative,payload):
        lease.recheck(); absolute=prefix+relative
        if sum(len(value) for value in files.values())+len(payload)>32*wire.MiB: raise ValueError('Candidate physical cap')
        desc=_publish_bytes(job,absolute,payload,roster,minimum_free_bytes=_publication_floor(lease)); files[absolute]=payload; lease.recheck(); return desc
    legacy_manifest=emit('base/legacy-manifest.json',data['manifest_bytes']); legacy_events=emit('base/legacy-events.jsonl',data['events_bytes'])
    base_chunks=[]; companions=[]
    for index,start in enumerate(range(0,len(raw_rows),32)):
        lease.recheck(); segment=projected[start:start+32]; count=len(segment)
        base_arrays={name:np.stack([row[name] for row in segment]) for name in BASE}
        comp_arrays={name:np.stack([row[name] for row in raw_rows[start:start+32]]) for name in COMPANION}
        base_payload=_encode_npz(base_arrays); companion_payload=_encode_npz(comp_arrays)
        for arrays,payload,spec in [(base_arrays,base_payload,BASE),(comp_arrays,companion_payload,COMPANION)]:
            decoded=_decode_npz(payload,spec,count)
            if any(decoded[name].tobytes()!=value.tobytes() for name,value in arrays.items()): raise ValueError('Encoded source storage differs')
        base_d=emit(f'base/chunks/{index:06}.npz',base_payload); comp_d=emit(f'numeric/{index:06}.npz',companion_payload)
        base_chunks.append(dict(index=index,file=base_d,episode=0,start=start,count=count,arrays={name:dict(dtype=dtype,shape=list(shape)) for name,(dtype,shape) in BASE.items()},raw_chunk=closed.raw_chunks[index],raw_sequence=data['chunks'][index]['sequence']))
        companions.append(dict(index=index,base_chunk=base_d,companion=comp_d,arrays={name:dict(dtype=dtype,shape=list(shape)) for name,(dtype,shape) in COMPANION.items()}))
        lease.recheck()
    index_d=emit('base/chunk-index.json',wire.encode(dict(schema=wire.record_schema('base-index',authored),chunks=base_chunks),32768))
    numeric_index_d=emit('numeric-index.json',wire.encode(dict(schema=wire.record_schema('numeric-index',authored),chunks=companions),32768))
    ticks=sorted({math.floor(i*(len(raw_rows)-1)/5) for i in range(6)}|set(range(max(0,len(raw_rows)-2),len(raw_rows))))
    frames=dict(tick=np.array(ticks,dtype='<i8'),raw_cam_left=np.stack([raw_rows[tick]['raw_cam_left'] for tick in ticks]),raw_cam_right=np.stack([raw_rows[tick]['raw_cam_right'] for tick in ticks]))
    frames_d=emit('base/audit-frames.npz',_encode_npz(frames))
    reference=dict(kind='original-source',source_run_id=run,snapshot=closed.snapshot,raw_audit=A_d,producer_registration=E_d)
    common=dict(profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],case_id=case['case_id'],source_run_id=run,operation='source',condition=None,first_tick=0,last_tick=len(raw_rows)-1,snapshot_reference=reference,claims=wire.CLAIMS.copy())
    base=dict(schema=wire.record_schema('base-manifest',authored),recording_format='palimpsest-source-base-vnext-v1',**common,rows=len(raw_rows),chunks=len(base_chunks),events=len(data['events']),legacy_manifest=legacy_manifest,legacy_events=legacy_events,chunk_index=index_d,audit_frames=frames_d,audit_schedule=dict(event_tick=None,decision_tick=None),snapshot_prefix=closed.prefix,sequences=A['sequences'])
    base_d=emit('base/manifest.json',wire.encode(base,65536))
    names=data['manifest']['population_names']
    top=dict(schema=wire.record_schema('numeric-manifest',authored),recording_format='palimpsest-source-numeric-vnext-v1',**common,row_count=len(raw_rows),chunk_count=len(base_chunks),base_manifest=base_d,base_files=sorted([wire.describe(p,v) for p,v in files.items() if p.startswith(prefix+'base/')],key=lambda d:d['path']),numeric_index=numeric_index_d,raw_audit=A_d,producer_registration=E_d,population=dict(names=names,columns=['count','mean','min','max'],scale=[-1.0,1.0]))
    manifest_d=emit('manifest.json',wire.encode(top,65536)); inventory=sorted([wire.describe(p,v) for p,v in files.items()],key=lambda d:d['path'])
    lease._hold_stage(inventory,exact=(prefix.rstrip('/'),))
    _compare_candidate(job,closed,A,E,lease,inventory,data)
    dense=19646*len(raw_rows); pixels=98304*len(ticks); total=sum(d['size_bytes'] for d in inventory); event_bytes=len(data['events_bytes'])
    metadata_bytes=sum(d['size_bytes'] for d in inventory if d['path'].endswith('.json'))
    if metadata_bytes>wire.MiB or total-dense-pixels-event_bytes>wire.MiB: raise ValueError('Candidate metadata/overhead cap')
    V=dict(schema=wire.record_schema('numeric-conversion',authored),profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_registration=E_d,raw_audit=A_d,snapshot=closed.snapshot,case_id=case['case_id'],source_run_id=run,numeric_manifest=manifest_d,inventory=inventory,comparison=dict(rows=len(raw_rows),base_arrays=16,companion_arrays=3,all_raw_fields_equal=True,selected_pixels_equal=True,event_bytes_equal=True,manifest_bytes_equal=True),ledger=dict(candidate_bytes=total,dense_bytes=dense,selected_pixel_bytes=pixels,event_bytes=event_bytes,metadata_physical_bytes=metadata_bytes,overhead_bytes=total-dense-pixels-event_bytes),status='candidate-unqualified',claims=wire.CLAIMS.copy())
    V_d=lease._publish(k+'/conversion/conversion.json',V,131072)
    C=dict(schema=wire.record_schema('numeric-commit',authored),profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],producer_registration=E_d,raw_audit=A_d,snapshot=closed.snapshot,conversion=V_d,numeric_manifest=manifest_d,status='candidate-unqualified',claims=wire.CLAIMS.copy())
    C_d=lease._publish(k+'/conversion/commit.json',C,16384); lease._hold_stage([V_d,C_d],exact=(k+'/conversion',)); return V,C


def _compare_candidate(job,closed,A,E,lease,inventory,data=None):
    import numpy as np
    from scripts.memory_family_source_raw_audit_vnext import _inspect_closed
    from scripts.memory_source_parent_entry_vnext import _lease_kind
    if data is None:
        independent,data=_inspect_closed(job,closed,lease); wire._literal(independent,A)
    authored=_lease_kind(lease)=='authored'; by_path={d['path']:d for d in inventory}; prefix=f"output/.pending/{job['case']['case_id']}/source/numeric/"
    def read(relative,cap=32*wire.MiB):
        path=prefix+relative
        if path not in by_path: raise ValueError('Candidate leaf absent from inventory')
        return lease._raw(by_path[path],cap)
    top=wire.decode(read('manifest.json',65536),65536); base=wire.decode(read('base/manifest.json',65536),65536)
    wire.schema(top,'numeric-manifest',authored); wire.schema(base,'base-manifest',authored)
    wire.fields(top,('schema','recording_format','profile','source_closure','case_id','source_run_id','operation','condition','row_count','chunk_count','first_tick','last_tick','base_manifest','base_files','numeric_index','raw_audit','producer_registration','snapshot_reference','population','claims'))
    wire.fields(base,('schema','recording_format','profile','source_closure','case_id','source_run_id','operation','condition','rows','chunks','events','first_tick','last_tick','legacy_manifest','legacy_events','chunk_index','audit_frames','audit_schedule','snapshot_prefix','snapshot_reference','sequences','claims'))
    A_d=wire.describe(f"output/controls/{job['source_run_id']}/raw-audit/audit.json",wire.encode(A,131072))
    E_d=wire.describe(f"output/controls/{job['source_run_id']}/registration/registration.json",wire.encode(E,65536))
    reference=dict(kind='original-source',source_run_id=job['source_run_id'],snapshot=closed.snapshot,raw_audit=A_d,producer_registration=E_d)
    for value in (base,top): wire._literal(value['snapshot_reference'],reference)
    for name,relative in [('legacy_manifest','base/legacy-manifest.json'),('legacy_events','base/legacy-events.jsonl'),('chunk_index','base/chunk-index.json'),('audit_frames','base/audit-frames.npz')]: wire._literal(base[name],by_path[prefix+relative])
    wire._literal(base['audit_schedule'],dict(event_tick=None,decision_tick=None))
    wire._literal(base['recording_format'],'palimpsest-source-base-vnext-v1')
    wire._literal(top['recording_format'],'palimpsest-source-numeric-vnext-v1')
    wire._literal(top['base_manifest'],by_path[prefix+'base/manifest.json']); wire._literal(top['numeric_index'],by_path[prefix+'numeric-index.json'])
    wire._literal(top['raw_audit'],A_d); wire._literal(top['producer_registration'],E_d)
    wire._literal(top['base_files'],sorted([desc for path,desc in by_path.items() if path.startswith(prefix+'base/')],key=lambda d:d['path']))
    from palimpsest.profiles import POPULATIONS
    wire._literal(top['population'],dict(names=list(POPULATIONS),columns=['count','mean','min','max'],scale=[-1.0,1.0]))

    index=wire.decode(read('base/chunk-index.json',32768),32768); numeric=wire.decode(read('numeric-index.json',32768),32768)
    wire.fields(index,('schema','chunks')); wire.fields(numeric,('schema','chunks'))
    if index['schema']!=wire.record_schema('base-index',authored) or numeric['schema']!=wire.record_schema('numeric-index',authored): raise ValueError('Index domain')
    chunks=index['chunks']; companions=numeric['chunks']; rows=data['rows']; projected=data['projected']
    expected={prefix+p for p in ('manifest.json','numeric-index.json','base/manifest.json','base/legacy-manifest.json','base/legacy-events.jsonl','base/chunk-index.json','base/audit-frames.npz')}
    expected|={prefix+f'base/chunks/{i:06}.npz' for i in range((len(rows)+31)//32)}; expected|={prefix+f'numeric/{i:06}.npz' for i in range((len(rows)+31)//32)}
    if set(by_path)!=expected or len(by_path)!=len(inventory): raise ValueError('Candidate exact physical roster')
    if read('base/legacy-manifest.json',65536)!=data['manifest_bytes'] or read('base/legacy-events.jsonl',7*wire.MiB)!=data['events_bytes']: raise ValueError('Legacy byte copies differ')
    if len(chunks)!=len(companions) or len(chunks)!=(len(rows)+31)//32: raise ValueError('Numeric partition count')
    for i,(chunk,companion) in enumerate(zip(chunks,companions)):
        start=i*32; count=min(32,len(rows)-start); lease.recheck()
        wire.fields(chunk,('index','file','episode','start','count','arrays','raw_chunk','raw_sequence')); wire.fields(companion,('index','base_chunk','companion','arrays'))
        wire._literal(chunk['file'],by_path[prefix+f'base/chunks/{i:06}.npz']); wire._literal(companion['companion'],by_path[prefix+f'numeric/{i:06}.npz'])
        wire._literal(chunk['arrays'],{name:dict(dtype=dtype,shape=list(shape)) for name,(dtype,shape) in BASE.items()})
        wire._literal(companion['arrays'],{name:dict(dtype=dtype,shape=list(shape)) for name,(dtype,shape) in COMPANION.items()})
        if chunk['index']!=i or chunk['start']!=start or chunk['count']!=count or chunk['episode']!=0 or companion['index']!=i or companion['base_chunk']!=chunk['file'] or chunk['raw_chunk']!=closed.raw_chunks[i] or chunk['raw_sequence']!=data['chunks'][i]['sequence']: raise ValueError('Numeric partition binding differs')
        base_values=_decode_npz(read(f'base/chunks/{i:06}.npz'),BASE,count); comp_values=_decode_npz(read(f'numeric/{i:06}.npz'),COMPANION,count)
        for name,array in base_values.items():
            if array.tobytes()!=np.stack([row[name] for row in projected[start:start+count]]).tobytes(): raise ValueError('Base row bits differ from raw')
        for name,array in comp_values.items():
            if array.tobytes()!=np.stack([row[name] for row in rows[start:start+count]]).tobytes(): raise ValueError('Companion row bits differ from raw')
        lease.recheck()
    ticks=sorted({math.floor(i*(len(rows)-1)/5) for i in range(6)}|set(range(max(0,len(rows)-2),len(rows))))
    frames=_decode_npz(read('base/audit-frames.npz'),compact.FRAME_FIELDS,len(ticks))
    if frames['tick'].tolist()!=ticks or any(frames[name].tobytes()!=np.stack([rows[tick][name] for tick in ticks]).tobytes() for name in ('raw_cam_left','raw_cam_right')): raise ValueError('Selected source pixels differ')
    wire._literal(base['rows'],len(rows)); wire._literal(base['chunks'],len(chunks)); wire._literal(base['events'],len(data['events']))
    if base['sequences']!=A['sequences'] or base['snapshot_prefix']!=closed.prefix or top['row_count']!=len(rows) or top['chunk_count']!=len(chunks): raise ValueError('Numeric rederived sequences/cursors differ')
    for manifest in (base,top):
        for key,value in dict(profile=job['readset']['profile'],source_closure=job['readset']['source_closure'],case_id=job['case']['case_id'],source_run_id=job['source_run_id'],operation='source',condition=None,first_tick=0,last_tick=len(rows)-1).items(): wire._literal(manifest[key],value)
    lease.recheck(); return data,top
