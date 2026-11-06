"""Conditional PURE terminal codec, Task4a; no actual receipt adapter.

TerminalProof/source replay and raw origin are caller premises. Read validates
stored format and opaque commitments, not original retained values or timings.
Convert/prove compare supplied raw bytes/arrays exactly. Neither grants custody,
qualification, physical lifetime accounting, publication or pruning authority.
"""
from __future__ import annotations

import copy
import hashlib
import io
import math
from pathlib import Path
import zipfile

import numpy as np

from palimpsest import artifacts, memory, snapshots
from palimpsest import memory_decision_world as world, memory_transition_vnext as transition
from palimpsest.profiles import validate_decision
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_numeric_preservation_v2 as numeric
from scripts import memory_family_terminal_audit_vnext as audit
from scripts import memory_family_raw_audit_v4 as legacy
from scripts import memory_family_oracle_admission_v3 as admission

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / 'docs/plans/memory-terminal-numeric-pure-vnext-v1-protocol.json'
TERMINAL_PATH = ROOT / 'docs/plans/memory-terminal-vnext-v1-protocol.json'
MiB = compact.MiB
BASE_SCHEMA = 'memory-family-compact-pure-manifest-vnext-v1'
BASE_FORMAT = 'palimpsest-family-compact-pure-vnext-v1'
NUMERIC_SCHEMA = 'memory-family-numeric-pure-manifest-vnext-v1'
NUMERIC_FORMAT = 'palimpsest-family-numeric-pure-compact-vnext-v1'
BASE_KEYS = compact.MANIFEST_FIELDS | {'context', 'terminal_proof'}
NUMERIC_KEYS = numeric.ENVELOPE_FIELDS | {'context', 'terminal_proof'}
RAW_KEYS = {'terminal_raw', 'recorded_manifest_bytes', 'recorded_events_bytes', 'snapshot_reference'}
FIXED = {'numeric-pure-vnext.json', 'numeric-index.json', 'terminal-proof.json', 'context.json',
    'base/manifest.json', 'base/legacy-manifest.json', 'base/legacy-events.jsonl',
    'base/chunk-index.json', 'base/audit-frames.npz'}
BASE_ARRAYS = {n: (d, s) for n, d, s, _ in compact.ROW_FIELDS}
RAW_ARRAYS = {n: (d, s) for n, d, s, _ in compact.ROW_FIELDS[:len(compact.RETAINED)]}
RAW_ARRAYS.update({name: ('|u1', (128, 128, 3)) for name in compact.CAMERAS})
RAW_ARRAYS.update(numeric.NUMERIC_FIELDS)


def _require(value, message):
    if not value:
        raise ValueError(message)


def _same(left, right):
    _require(memory.canonical_bytes(left) == memory.canonical_bytes(right), 'PURE binding differs')


def _fields(value, keys):
    compact._fields(value, keys, 'PURE object')


def _integer(value, maximum=2100):
    _require(type(value) is int and 0 <= value <= maximum, 'Invalid PURE exact counter')
    return value


def _file_descriptor(path, payload):
    return compact._descriptor(path.relative_to(ROOT).as_posix(), payload)


def _profile_contract():
    return {'schema': 'memory-terminal-numeric-pure-protocol-vnext-v1', 'status': 'PROPOSED-UNQUALIFIED',
        'terminal_profile': _file_descriptor(TERMINAL_PATH, artifacts._read(TERMINAL_PATH, MiB)),
        'inherited_base_protocol': _file_descriptor(compact.PROTOCOL_PATH, compact.PROTOCOL_BYTES),
        'inherited_numeric_protocol': _file_descriptor(numeric.PROTOCOL_PATH, numeric.PROTOCOL_BYTES),
        'schemas': {'base': BASE_SCHEMA, 'base_format': BASE_FORMAT, 'numeric': NUMERIC_SCHEMA,
            'numeric_format': NUMERIC_FORMAT, 'base_keys': sorted(BASE_KEYS), 'numeric_keys': sorted(NUMERIC_KEYS),
            'base_index': 'memory-family-compact-chunk-index-v1', 'numeric_index': 'memory-family-numeric-chunk-index-v2',
            'index_keys': sorted(compact.INDEX_FIELDS), 'base_entry_keys': sorted(compact.INDEX_ENTRY_FIELDS),
            'numeric_entry_keys': sorted(numeric.ENTRY_FIELDS), 'raw_keys': sorted(RAW_KEYS)},
        'members': {'fixed': sorted(FIXED), 'base_partition': 'base/chunks/{index:06d}.npz',
            'numeric_partition': 'numeric/{index:06d}.npz', 'count': '9+2*ceil(rows/32)'},
        'row': {'base_fields': [{'name': n, 'dtype': d, 'shape': list(s)} for n,d,s,_ in compact.ROW_FIELDS],
            'numeric_fields': [{'name': n, 'dtype': d, 'shape': list(s)} for n,(d,s) in numeric.NUMERIC_FIELDS.items()],
            'dense_bytes': 19646, 'partition_rows': 32, 'population': numeric.PROTOCOL['population']},
        'limits': {'rows': 900, 'chunks': 29, 'events': 50000, 'events_bytes': 5*MiB,
            'event_line_bytes': MiB,
            'total_bytes': 25*MiB, 'combined_overhead_bytes': MiB, 'context_bytes': 16384,
            'metadata_role_bytes': MiB, 'source_snapshot_bytes': 16*MiB,
            'audit_frame_bytes': 1572864, 'audit_frame_formula': 'count*98312+4096',
            'base_partition_formula': 'count*19534+8192', 'numeric_partition_formula': 'count*112+4096',
            'source_commit_bytes_when_present': 16384, 'source_conversion_bytes_when_present': 65536},
        'extensions': {'operation': 'condition', 'raw_audit': None, 'source_identity': None,
            'zero': 'null first/last; empty indexes; no partitions; typed empty audit arrays',
            'audit_schedule_keys': ['decision_tick', 'event_tick'], 'snapshot_event_prefix': None,
            'snapshot_conversion_hash': 'supplied conditional source CONVERSION digest',
            'containers': 'ZIP_STORED, exact member census, NPY v1.0 C order 128-byte header; exact re-encoding'},
        'accounting': {'external': 'complete distinct external metadata cost; includes floor, not added twice',
            'floor': ['canonical proof', 'canonical Context', 'raw_manifest D bytes', 'worker_report D bytes', 'job D bytes'],
            'overhead': 'bundle bytes + external - verified dense - selected pixels - copied events',
            'physical': 'prospective declared serialized costs only; raw/SNP separate; no lifetime/RSS/peak pass'},
        'scope': {'read': 'stored format/opaque commitments only; no original raw timing or all-array authentication',
            'convert_prove': 'exact supplied raw comparison; origin and independently established proof remain premises',
            'future': 'actual receipt/held conversion identity waits for separately reviewed Task4b after Task3b; never relabel PURE'},
        'claims': {'actual_acceptance': False, 'physical_lifetime_accounted': False, 'publication_authorized': False,
            'pruning_authorized': False, 'source_qualified': False, 'condition_qualified': False,
            'model_replay_performed': False, 'inherited': copy.deepcopy(compact.PROTOCOL['claims'])}}


def _json(payload, label):
    _require(type(payload) is bytes and len(payload) <= MiB, 'PURE metadata role exceeds cap')
    return compact._canonical(payload, label)


def _bind_descriptor(value, payload, maximum):
    transition.validate_descriptor_vnext(value, max_bytes=maximum)
    _require(type(payload) is bytes and len(payload) <= maximum, 'PURE payload exceeds role cap')
    _require(value['size_bytes'] == len(payload) and value['sha256'] == hashlib.sha256(payload).hexdigest(),
        'PURE input descriptor differs')


def _proof(receipt, context):
    _fields(receipt, audit.PROOF_KEYS)
    _require(receipt['schema'] == 'memory-terminal-proof-vnext-v1', 'Invalid PURE TerminalProof schema')
    c = transition.validate_context_vnext(context)
    _same(c['profile'], PROTOCOL['terminal_profile'])
    payload = memory.canonical_bytes(receipt)
    _require(len(payload) <= MiB, 'PURE proof exceeds metadata cap')
    for role, cap in (('context',16384), ('job',MiB), ('raw_manifest',MiB),
            ('raw_events',5*MiB), ('worker_report',MiB), ('source_snapshot',16*MiB)):
        transition.validate_descriptor_vnext(receipt[role], max_bytes=cap)
        _require(receipt[role]['size_bytes'] > 0, 'PURE immutable input must be nonempty')
    _bind_descriptor(receipt['context'], memory.canonical_bytes(c), 16384)
    _same(receipt['source_snapshot'], c['source_snapshot'])
    b, n = _integer(receipt['boundary_tick']), _integer(receipt['row_count'], 900)
    _require(b == c['schedule']['boundary_tick'] and b > 0 and b+n <= 2100, 'PURE boundary differs')
    _require(_integer(receipt['chunk_count'],29) == (n+31)//32, 'PURE partition count differs')
    _same(receipt['first_motor_tick'], b if n else None)
    _same(receipt['last_motor_tick'], b+n-1 if n else None)
    for name in ('world_applied', 'trigger_reached', 'decision_reached', 'goal'):
        _require(type(receipt[name]) is bool, 'PURE proof boolean differs')
    _require(type(receipt['path_length']) is float and math.isfinite(receipt['path_length'])
        and receipt['path_length'] >= 0., 'Invalid PURE path length')
    outcome = receipt['outcome']
    _require(type(outcome) is dict, 'Invalid PURE outcome')
    tail = receipt['terminal_sensor_tick'] is not None
    _require(type(outcome.get('reason')) is str, 'Invalid PURE outcome reason')
    if tail:
        _require(_integer(receipt['terminal_sensor_tick']) == b+n and n<900 and b+n<min(2100,b+900),
            'Invalid PURE terminal tail')
        _fields(outcome, {'reason','episode','steps','type','message','policy_diagnostics'})
        _require(outcome['reason']=='runtime_failure' and outcome['type'] in ('CueUnavailable','ValueError')
            and type(outcome['message']) is str and outcome['policy_diagnostics']=={}, 'Invalid PURE natural cause')
        _require(len(outcome['message'].encode('utf-8'))<=512,'PURE exception exceeds bound')
    else:
        _require(n > 0 and receipt['decision_reached'], 'Normal PURE terminal lacks reached decision')
        _fields(outcome, {'reason','episode','steps','final_distance'})
        _require(outcome['reason'] in ('goal','stalled','collision','time_limit')
            and type(outcome['final_distance']) is float and math.isfinite(outcome['final_distance'])
            and outcome['final_distance'] >= 0., 'Invalid PURE normal outcome')
    _require(type(outcome['episode']) is int and outcome['episode']==0
        and type(outcome['steps']) is int and outcome['steps']==b+n, 'PURE outcome interval differs')
    _same(receipt['goal'], outcome['reason']=='goal')
    _require(_integer(receipt['capped_ticks'],900) == (n if receipt['goal'] else 900), 'PURE score differs')
    _require(n or receipt['path_length']==0., 'Zero PURE path differs')
    for name in ('trace_digest','row_sequence_sha256','camera_sequence_sha256','invariant'):
        compact._digest(receipt[name])
    _same(receipt['invariant'],c['source_invariant_sha256'])
    for name in ('witnesses','commits'):
        refs = receipt[name]
        _require(type(refs) is list and len(refs)<=2, 'Invalid PURE references')
        previous = -1
        for ref in refs:
            _fields(ref, {'sequence','sha256'}); sequence = _integer(ref['sequence'],49999)
            compact._digest(ref['sha256']); _require(sequence > previous, 'Duplicate/unordered PURE reference')
            previous = sequence
    _require(len(receipt['commits']) <= len(receipt['witnesses']), 'PURE commit has no witness')
    return c, copy.deepcopy(receipt)


def _safe_rows(rows):
    audit._decoded_rows(rows,900,384*MiB)  # exact safe types before any NumPy coercion
    for row in rows:
        _require(type(row['episode']) is int and row['episode']==0, 'Invalid PURE episode')
        _integer(row['tick'])
        for name,(dtype,shape) in RAW_ARRAYS.items():
            numeric._numeric_array(row[name],dtype,shape,name)
    return compact._project_rows(rows,'condition') if rows else []


def _encode_partition(rows):
    """Fixed 16+3 partition primitive; no proof/admission semantics."""
    _require(type(rows) is list and 1<=len(rows)<=32, 'Invalid PURE partition rows')
    projected = _safe_rows(rows)
    base = compact._npz({name:np.stack([r[name] for r in projected]) for name in BASE_ARRAYS})
    extra = compact._npz({name:np.stack([r[name] for r in rows]) for name in numeric.NUMERIC_FIELDS})
    return base,extra


def _read_arrays(payload, schema, count, maximum, label):
    _require(type(payload) is bytes and len(payload)<=maximum, 'PURE array role exceeds cap')
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members=archive.infolist()
            _require(len(members)==len(schema) and {m.filename for m in members}=={n+'.npy' for n in schema}
                and not archive.comment, 'Invalid PURE ZIP members')
            for member in members:
                _require(member.compress_type==zipfile.ZIP_STORED and not member.comment and not member.flag_bits,
                    'Invalid PURE ZIP metadata')
                dtype,shape=schema[member.filename[:-4]]
                expected=128+count*math.prod(shape)*np.dtype(dtype).itemsize
                _require(member.file_size==expected, 'Invalid PURE NPY byte length')
                stream=io.BytesIO(archive.read(member))
                _require(np.lib.format.read_magic(stream)==(1,0), 'Invalid PURE NPY version')
                actual,fortran,dt=np.lib.format.read_array_header_1_0(stream)
                _require(actual==(count,*shape) and not fortran and dt.str==dtype and stream.tell()==128,
                    'Invalid PURE NPY header')
        arrays=compact._read_npz(payload,schema,count,label)
        _require(compact._npz(arrays)==payload,'Invalid PURE noncanonical/trailing ZIP bytes')
        return arrays
    except (zipfile.BadZipFile, OSError, EOFError, TypeError, AttributeError) as error:
        raise ValueError('Invalid PURE array container') from error


def _snapshot(value,c):
    result=compact._snapshot(value,'condition',c['run_id'],c['case_id'])
    _same(result['source_run_id'],c['source_run_id'])
    _same({k:result[k] for k in ('path','size_bytes','sha256')},c['source_snapshot'])
    return result


def _recording(manifest_bytes,event_bytes,c,p):
    _bind_descriptor(p['raw_manifest'],manifest_bytes,MiB)
    _bind_descriptor(p['raw_events'],event_bytes,5*MiB)
    m=artifacts._json(manifest_bytes)
    _require(type(m) is dict and audit._writer(m)==manifest_bytes, 'PURE recorded manifest encoding differs')
    _require(type(event_bytes) is bytes and event_bytes.endswith(b'\n'), 'Invalid PURE event bytes')
    events=[]
    for line in event_bytes.splitlines(keepends=True):
        _require(len(line.rstrip(b'\n')) <= MiB, 'PURE event line exceeds inherited cap')
        event=artifacts._json(line)
        _require(audit._writer(event)==line, 'PURE event writer encoding differs')
        events.append(event)
    audit._events(events,c['run_id'])
    b,n=p['boundary_tick'],p['row_count']; tail=p['terminal_sensor_tick'] is not None
    case=world.validate_case(m.get('memory_case'))
    expected={'run_id':c['run_id'],'memory_case_sha256':c['case_sha256'],'seed':case['seed'],
        'acquisition_protocol_sha256':case['acquisition_protocol_sha256'],'controller':'flynn',
        'requested_device':'cpu','teacher_privileged':False,'texture':'checker',
        'scenario':validate_decision(world.SCENARIO,'checker','flynn',profile_sha256=case['profile_sha256']),
        'recording_format':'palimpsest-npz-v1','recording_max_bytes':384*MiB,
        'parent_run_id':c['source_run_id'],'memory_terminal_vnext_mode':'memory-terminal-vnext-v1',
        'memory_terminal_vnext_context_sha256':memory.sha256(c),'memory_terminal_vnext_context':p['context'],
        'close_reason':'operator_closed','recorded_ticks':n,'recorded_chunks':p['chunk_count'],
        'recorded_events':len(events),'total_tick':b+n,'last_outcome':p['outcome'],
        'status':'failed' if tail else 'completed',
        'final_phase':'failed' if tail else ('truncated' if p['outcome']['reason']=='time_limit' else 'terminated')}
    for name,value in expected.items():
        _require(name in m,'Missing PURE recording field'); _same(m[name],value)
    _same(memory.sha256(case),c['case_sha256']); _same(case['case_id'],c['case_id']); _same(case['kind'],c['kind'])
    _require(case['version']==3 and 'memory_family_oracle_admission_v3' not in m, 'Invalid PURE case/admission envelope')
    prefix=m.get('parent_event_prefix'); _fields(prefix,{'sha256','size_bytes','event_count'})
    compact._digest(prefix['sha256']); _require(_integer(prefix['size_bytes'],7*MiB)>0
        and _integer(prefix['event_count'],50000)>0,'Invalid PURE source prefix')
    audit._metrics(m.get('metrics'))
    ws=world.validate_state(m.get('world_state'))
    _same(ws['case'],case); _same(ws['applied'],p['world_applied'])
    _same(ws['last_tick'],b+n if tail else b+n-1)
    _same(ws['acquired_state_sha256'],c['source_invariant_sha256'])
    for name,wn in (('boundary_tick','armed_boundary_tick'),('event_tick','event_tick'),('decision_tick','decision_tick')):
        _same(ws[wn],c['schedule'][name])
    chunks=audit._chunks(events,b,n)
    raw_schema={name:{'dtype':d,'shape':list(s)} for name,(d,s) in RAW_ARRAYS.items()}
    for e in chunks:
        _fields(e,{'sequence','kind','path','sha256','episode','start','count','arrays'})
        _same(e['arrays'],raw_schema)
    sensed=[e for e in events if e['kind']=='memory_sensed']
    _same([e['tick'] for e in sensed],list(range(b,b+n+int(tail))))
    _same(p['decision_reached'],any(e['tick']>=c['schedule']['decision_tick'] for e in sensed))
    witnesses=[e for e in events if e['kind']=='memory_transition_witness_vnext']
    commits=[e for e in events if e['kind']=='memory_transition_commit_vnext']
    _same(p['witnesses'],[audit._reference(e) for e in witnesses])
    _same(p['commits'],[audit._reference(e) for e in commits])
    previous=memory.sha256(c); witnessed={}
    for index,event in enumerate(witnesses):
        body=event.get('witness')
        encoded=transition.terminal_event_bytes_vnext('memory_transition_witness_vnext',body,
            **{k:event[k] for k in ('sequence','run_id','episode','tick','episode_step')})
        _require(encoded==audit._writer(event),'PURE witness envelope differs')
        _same(body['context_sha256'],memory.sha256(c)); _same(body['job_sha256'],p['job']['sha256'])
        _same(body['index'],index); _same(body['previous_sha256'],previous)
        for role in ('cue_event','gate_event','intervention_event','sensed_event'):
            ref=body['reach'][role]
            if type(ref) is dict and set(ref)=={'sequence','sha256'}:
                _require(ref['sequence']<event['sequence'] and ref['sequence']<len(events),'Future PURE reference')
                target=events[ref['sequence']]
                _same(ref,audit._reference(target))
                kind={'cue_event':'memory_world_changed','gate_event':'memory_world_changed',
                    'intervention_event':'intervention','sensed_event':'memory_sensed'}[role]
                _require(target['kind']==kind,'PURE reference role differs')
                if role in ('cue_event','gate_event'):
                    _same(target.get('detail',{}).get('kind'),
                        'memory_cue_changed' if role=='cue_event' else 'memory_gate_applied')
                if role=='sensed_event':
                    _same(target['tick'],body['tick'])
                    _same(memory.sha256(target.get('packet')),body['packet_sha256'])
        previous=memory.sha256(body); witnessed[previous]=event
    for event in commits:
        body=event.get('commit')
        encoded=transition.terminal_event_bytes_vnext('memory_transition_commit_vnext',body,
            **{k:event[k] for k in ('sequence','run_id','episode','tick','episode_step')})
        _require(encoded==audit._writer(event),'PURE commit envelope differs')
        _same(body['context_sha256'],memory.sha256(c))
        prior=witnessed.get(body['witness_sha256'])
        _require(prior is not None and prior['sequence']<event['sequence'] and prior['tick']==event['tick']
            and prior['witness']['result']=='returned','PURE commit witness differs')
        _same(body['memory_sha256'],prior['witness']['local_memory_sha256'])
        _same(body['lifecycle'],prior['witness']['local_lifecycle'])
    trigger=any(e['witness']['trigger'] is not None for e in witnesses) or any(
        e['kind']=='memory_decision' and e.get('detail',{}).get('kind')=='memory_trigger' for e in events)
    _same(p['trigger_reached'],trigger)
    _require(len(legacy._policy_calls(events))==n,'PURE policy count differs')
    failures=[e for e in events if e['kind']=='runtime_failure']
    if tail:
        _require(len(failures)==1 and not any(e['kind']=='episode_finished' for e in events), 'PURE failure count differs')
        failure=failures[0]; _same(failure['error'],p['outcome'])
        _require(failure['tick']==b+n and all(e['kind']=='chunk' for e in events[failure['sequence']+1:]),
            'PURE postterminal progress')
        _require(witnesses and witnesses[-1]['tick']==b+n,'PURE failure lacks terminal witness')
        w=witnesses[-1]['witness']
        if w['result']=='raised':
            _same(w['exception'],{k:p['outcome'][k] for k in ('type','message')})
            _require(p['outcome']['type']=='CueUnavailable','Invalid raised PURE cause')
        else:
            _require(w['result']=='returned' and p['outcome']['type']=='ValueError'
                and p['outcome']['message'].startswith('Memory-v2 supervisor failure: ')
                and any(e['tick']==b+n for e in commits),'Invalid returned PURE failure')
    else:
        _require(not failures,'Normal PURE terminal has failure')
        legacy._normal_condition_terminal(events,m,{'manifest_status':'completed','final_phase':m['final_phase'],
            'total_ticks':b+n,'last_tick':b+n-1},c['schedule'])
        finish=next(e for e in events if e['kind']=='episode_finished')
        _same(finish['outcome'],p['outcome']); _same(finish['metrics'],m['metrics'])
    return m,events,chunks


def _raw(raw,c,p):
    _fields(raw,RAW_KEYS); tr=raw['terminal_raw']; _fields(tr,audit._RAW_KEYS); _fields(tr['descriptors'],audit._DESCRIPTORS)
    _require(type(raw['recorded_manifest_bytes']) is bytes and len(raw['recorded_manifest_bytes'])<=MiB
        and type(raw['recorded_events_bytes']) is bytes and len(raw['recorded_events_bytes'])<=5*MiB,
        'PURE recorded payload type/cap differs')
    for role in audit._DESCRIPTORS: _same(tr['descriptors'][role],p[role])
    _same(tr['job'],p['job'])
    _bind_descriptor(p['worker_report'],memory.canonical_bytes(tr['worker_report']),MiB)
    _require(audit._writer(tr['manifest'])==raw['recorded_manifest_bytes'], 'PURE supplied manifest bytes differ')
    _require(type(tr['events']) is list and len(tr['events'])<=50000,'Invalid PURE supplied events')
    _require(b''.join(audit._writer(e) for e in tr['events'])==raw['recorded_events_bytes'], 'PURE supplied event bytes differ')
    m,events,chunks=_recording(raw['recorded_manifest_bytes'],raw['recorded_events_bytes'],c,p)
    report=tr['worker_report']; _fields(report,admission.REPORT_FIELDS)
    _same(report,{'schema':admission.REPORT_SCHEMA,'run_id':c['run_id'],'case_id':c['case_id'],
        'operation':'condition','condition':c['condition'],'status':'recorded','acquired':True,
        'snapshot_sha256':c['source_snapshot']['sha256'],'source_snapshot_sha256':c['source_snapshot']['sha256'],
        'total_ticks':p['boundary_tick']+p['row_count'],'final_phase':m['final_phase'],'world_state':m['world_state']})
    projected=_safe_rows(tr['rows'])
    _require(len(projected)==p['row_count'],'PURE supplied row count differs')
    _same([r['tick'] for r in projected],list(range(p['boundary_tick'],p['boundary_tick']+p['row_count'])))
    for name,actual in (('trace_digest',compact._trace_digest(projected)),
            ('row_sequence_sha256',compact._sequence_hash(projected,('row_digest',))),
            ('camera_sequence_sha256',compact._sequence_hash(projected,compact.DIGEST_FIELDS[:-1]))):
        _same(actual,p[name])
    audit._policy(tr['rows'],events)
    path=0.
    for row in tr['rows']: path+=float(np.linalg.norm(row['next_pose'][:2]-row['pose'][:2]))
    _same(path,p['path_length'])
    return projected,chunks,_snapshot(raw['snapshot_reference'],c)


def _scope(compared=False,rows=0):
    return {'raw_comparison_performed':compared,'rows_checked':rows,'actual_acceptance':False,
        'source_qualified':False,'condition_qualified':False,'model_replay_performed':False,
        'physics_replay_performed':False,'full_pixel_replay':False,'stage_peak_accounted':False,
        'evidence':'exact-supplied-raw-comparison' if compared else 'stored-format-and-opaque-commitments-only'}


def _ledger(bundle,c,p,selected,external):
    floor=len(memory.canonical_bytes(p))+len(memory.canonical_bytes(c))+sum(p[k]['size_bytes'] for k in ('raw_manifest','worker_report','job'))
    _require(type(external) is int and external>=floor,'PURE external metadata below mandatory floor')
    total=sum(map(len,bundle.values()))+external
    dense=p['row_count']*19646; pixels=selected*98304; events=len(bundle['base/legacy-events.jsonl'])
    overhead=total-dense-pixels-events
    _require(0<=overhead<=MiB and total<=25*MiB,'PURE combined recording/metadata cap exceeded')
    return {'recording_bytes':total,'bundle_bytes':total-external,'dense_bytes':dense,
        'selected_pixel_bytes':pixels,'event_bytes':events,'overhead_bytes':overhead,
        'external_overhead_bytes':external,'mandatory_external_metadata_floor':floor,
        'stage_peak_accounted':False,'snapshot_accounted':False,'physical_lifetime_accounted':False}


def convert_terminal_numeric_vnext(raw, *, receipt, context, external_overhead_bytes):
    """Encode and verify supplied raw; independent proof validity remains a premise."""
    c,p=_proof(receipt,context); projected,chunks,snapshot=_raw(raw,c,p)
    bundle={'context.json':memory.canonical_bytes(c),'terminal-proof.json':memory.canonical_bytes(p),
        'base/legacy-manifest.json':raw['recorded_manifest_bytes'],'base/legacy-events.jsonl':raw['recorded_events_bytes']}
    entries=[]; companions=[]
    for i,chunk in enumerate(chunks):
        start=i*32; rows=raw['terminal_raw']['rows'][start:start+chunk['count']]
        base,extra=_encode_partition(rows); path=f'chunks/{i:06d}.npz'; extra_path=f'numeric/{i:06d}.npz'
        bundle['base/'+path]=base; bundle[extra_path]=extra
        entry={'index':i,'path':path,'sha256':hashlib.sha256(base).hexdigest(),'episode':0,
            'start':chunk['start'],'count':chunk['count'],'arrays':compact._row_schema(),
            'legacy_sequence':chunk['sequence'],'legacy_path':chunk['path'],'legacy_sha256':chunk['sha256']}
        entries.append(entry)
        companions.append({'index':i,'base_chunk':copy.deepcopy(entry),'companion':compact._descriptor(extra_path,extra),'arrays':numeric._schema()})
    bundle['base/chunk-index.json']=memory.canonical_bytes({'schema':'memory-family-compact-chunk-index-v1','chunks':entries})
    bundle['numeric-index.json']=memory.canonical_bytes({'schema':'memory-family-numeric-chunk-index-v2','chunks':companions})
    schedule={k:c['schedule'][k] for k in ('event_tick','decision_tick')}
    selected=compact.audit_ticks([r['tick'] for r in projected],**schedule) if projected else ()
    by_tick={r['tick']:r for r in raw['terminal_raw']['rows']}
    frames={'tick':np.asarray(selected,dtype='<i8'), **{name:np.stack([by_tick[t][name] for t in selected])
        if selected else np.empty((0,128,128,3),dtype='|u1') for name in ('raw_cam_left','raw_cam_right')}}
    bundle['base/audit-frames.npz']=compact._npz(frames)
    bm={'schema':BASE_SCHEMA,'recording_format':BASE_FORMAT,'protocol_sha256':PROTOCOL_SHA256,
        'run_id':c['run_id'],'case_id':c['case_id'],'operation':'condition','condition':c['condition'],
        'row_count':p['row_count'],'chunk_count':p['chunk_count'],'event_count':len(raw['terminal_raw']['events']),
        'first_tick':p['first_motor_tick'],'last_tick':p['last_motor_tick'],
        **{key:compact._descriptor(path,bundle['base/'+path]) for key,path in (
            ('legacy_manifest','legacy-manifest.json'),('legacy_events','legacy-events.jsonl'),
            ('chunk_index','chunk-index.json'),('audit_frames','audit-frames.npz'))},
        'audit_schedule':schedule,'snapshot_event_prefix':None,'snapshot_reference':snapshot,
        'non_chunk_sequences_sha256':memory.sha256([e['sequence'] for e in raw['terminal_raw']['events'] if e['kind']!='chunk']),
        'legacy_chunks_sha256':memory.sha256([[e[k] for k in ('sequence','path','sha256','episode','start','count','arrays')] for e in chunks]),
        **{key:p[key] for key in ('trace_digest','row_sequence_sha256','camera_sequence_sha256')},
        'claims':copy.deepcopy(compact.PROTOCOL['claims']),
        'context':compact._descriptor('context.json',bundle['context.json']),
        'terminal_proof':compact._descriptor('terminal-proof.json',bundle['terminal-proof.json'])}
    bundle['base/manifest.json']=memory.canonical_bytes(bm)
    nm={'schema':NUMERIC_SCHEMA,'recording_format':NUMERIC_FORMAT,'protocol':copy.deepcopy(PROFILE_DESCRIPTOR),
        'base_protocol':copy.deepcopy(PROFILE_DESCRIPTOR),**{k:bm[k] for k in numeric.IDENTITY_FIELDS},
        'base_manifest':compact._descriptor('base/manifest.json',bundle['base/manifest.json']),
        'base_files':[compact._descriptor(path,bundle[path]) for path in sorted(bundle) if path.startswith('base/')],
        'numeric_index':compact._descriptor('numeric-index.json',bundle['numeric-index.json']),
        'raw_audit':None,'source_identity':None,'population':copy.deepcopy(numeric.PROTOCOL['population']),
        'claims':copy.deepcopy(numeric.PROTOCOL['claims']),'context':copy.deepcopy(bm['context']),
        'terminal_proof':copy.deepcopy(bm['terminal_proof'])}
    bundle['numeric-pure-vnext.json']=memory.canonical_bytes(nm)
    prove_terminal_numeric_vnext(raw,bundle,p,external_overhead_bytes=external_overhead_bytes)
    return bundle


def read_terminal_numeric_vnext(bundle, *, receipt, external_overhead_bytes):
    """Read stored format/commitments; raw timing/all-array truth is not available."""
    _require(type(bundle) is dict and all(type(k) is str and type(v) is bytes for k,v in bundle.items())
        and FIXED.issubset(bundle),'Invalid PURE bundle')
    _require(sum(map(len,bundle.values()))<=25*MiB,'PURE bundle exceeds total cap')
    c,p=_proof(receipt,_json(bundle['context.json'],'PURE Context'))
    _same(_json(bundle['terminal-proof.json'],'PURE proof'),p)
    _require(bundle['terminal-proof.json']==memory.canonical_bytes(receipt),'PURE copied proof differs')
    bm=_json(bundle['base/manifest.json'],'PURE base manifest'); _fields(bm,BASE_KEYS)
    nm=_json(bundle['numeric-pure-vnext.json'],'PURE numeric manifest'); _fields(nm,NUMERIC_KEYS)
    _require(bm['schema']==BASE_SCHEMA and bm['recording_format']==BASE_FORMAT
        and bm['protocol_sha256']==PROTOCOL_SHA256 and nm['schema']==NUMERIC_SCHEMA
        and nm['recording_format']==NUMERIC_FORMAT and nm['raw_audit'] is None and nm['source_identity'] is None,
        'PURE manifest contract differs')
    _same(nm['protocol'],PROFILE_DESCRIPTOR); _same(nm['base_protocol'],PROFILE_DESCRIPTOR)
    _same(bm['claims'],compact.PROTOCOL['claims']); _same(nm['claims'],numeric.PROTOCOL['claims'])
    _same(nm['population'],numeric.PROTOCOL['population'])
    expected={'run_id':c['run_id'],'case_id':c['case_id'],'operation':'condition','condition':c['condition'],
        'row_count':p['row_count'],'chunk_count':p['chunk_count'],'first_tick':p['first_motor_tick'],'last_tick':p['last_motor_tick']}
    for key,value in expected.items(): _same(bm[key],value); _same(nm[key],value)
    for manifest in (bm,nm):
        for key,path in (('context','context.json'),('terminal_proof','terminal-proof.json')):
            compact._check_descriptor(manifest[key],path,bundle[path])
    _same(bm['audit_schedule'],{k:c['schedule'][k] for k in ('event_tick','decision_tick')})
    _require(bm['snapshot_event_prefix'] is None,'PURE condition has source snapshot prefix')
    snapshot=_snapshot(bm['snapshot_reference'],c)
    m,events,chunks=_recording(bundle['base/legacy-manifest.json'],bundle['base/legacy-events.jsonl'],c,p)
    _same(bm['event_count'],len(events))
    for key,path in (('legacy_manifest','legacy-manifest.json'),('legacy_events','legacy-events.jsonl'),
            ('chunk_index','chunk-index.json'),('audit_frames','audit-frames.npz')):
        compact._check_descriptor(bm[key],path,bundle['base/'+path])
    compact._check_descriptor(nm['base_manifest'],'base/manifest.json',bundle['base/manifest.json'])
    compact._check_descriptor(nm['numeric_index'],'numeric-index.json',bundle['numeric-index.json'])
    index=_json(bundle['base/chunk-index.json'],'PURE chunk index'); _fields(index,compact.INDEX_FIELDS)
    ni=_json(bundle['numeric-index.json'],'PURE numeric index'); _fields(ni,compact.INDEX_FIELDS)
    _require(index['schema']=='memory-family-compact-chunk-index-v1' and ni['schema']=='memory-family-numeric-chunk-index-v2'
        and type(index['chunks']) is list and type(ni['chunks']) is list
        and len(index['chunks'])==len(ni['chunks'])==p['chunk_count'],'PURE partition index differs')
    paths=FIXED|{f'base/chunks/{i:06d}.npz' for i in range(p['chunk_count'])}|{f'numeric/{i:06d}.npz' for i in range(p['chunk_count'])}
    _require(set(bundle)==paths,'PURE member census differs')
    _same(nm['base_files'],[compact._descriptor(path,bundle[path]) for path in sorted(paths) if path.startswith('base/')])
    rows=[]
    for i,(entry,extra,chunk) in enumerate(zip(index['chunks'],ni['chunks'],chunks)):
        _fields(entry,compact.INDEX_ENTRY_FIELDS); _fields(extra,numeric.ENTRY_FIELDS)
        path=f'chunks/{i:06d}.npz'; count=min(32,p['row_count']-i*32)
        expected={'index':i,'path':path,'sha256':hashlib.sha256(bundle['base/'+path]).hexdigest(),
            'episode':0,'start':p['boundary_tick']+i*32,'count':count,'arrays':compact._row_schema(),
            'legacy_sequence':chunk['sequence'],'legacy_path':chunk['path'],'legacy_sha256':chunk['sha256']}
        _same(entry,expected); _same(extra['index'],i); _same(extra['base_chunk'],entry); _same(extra['arrays'],numeric._schema())
        ep=f'numeric/{i:06d}.npz'; compact._check_descriptor(extra['companion'],ep,bundle[ep])
        base=_read_arrays(bundle['base/'+path],BASE_ARRAYS,count,count*19534+8192,'PURE base partition')
        additional=numeric._read_numeric_npz(bundle[ep],count)
        for offset in range(count):
            rows.append({'episode':0,'tick':entry['start']+offset,
                **{name:array[offset].copy() for name,array in base.items()},
                **{name:array[offset].copy() for name,array in additional.items()}})
    for row in rows:
        _require(row['eyes'].all() and np.array_equal(row['cam_left_sha256'],row['raw_cam_left_sha256'])
            and np.array_equal(row['cam_right_sha256'],row['raw_cam_right_sha256']),'PURE eye commitments differ')
    path_length=0.
    for row in rows:
        path_length+=float(np.linalg.norm(row['next_pose'][:2]-row['pose'][:2]))
    _same(path_length,p['path_length'])
    for key,actual in (('trace_digest',compact._trace_digest(rows)),
            ('row_sequence_sha256',compact._sequence_hash(rows,('row_digest',))),
            ('camera_sequence_sha256',compact._sequence_hash(rows,compact.DIGEST_FIELDS[:-1]))):
        _same(actual,bm[key]); _same(actual,p[key])
    _same(bm['non_chunk_sequences_sha256'],memory.sha256([e['sequence'] for e in events if e['kind']!='chunk']))
    _same(bm['legacy_chunks_sha256'],memory.sha256([[e[k] for k in ('sequence','path','sha256','episode','start','count','arrays')] for e in chunks]))
    selected=compact.audit_ticks([r['tick'] for r in rows],**bm['audit_schedule']) if rows else ()
    frames=_read_arrays(bundle['base/audit-frames.npz'],compact.FRAME_FIELDS,len(selected),
        min(1572864,len(selected)*98312+4096),'PURE audit frames')
    _same(frames['tick'].tolist(),list(selected)); selected_frames={}
    by_tick={row['tick']:row for row in rows}
    for i,tick in enumerate(selected):
        selected_frames[tick]={name:frames[name][i].copy() for name in ('raw_cam_left','raw_cam_right')}
        for name,array in selected_frames[tick].items():
            _require(bytes.fromhex(snapshots.state_digest(array))==by_tick[tick][name+'_sha256'].tobytes(),
                'PURE selected pixels differ')
    ledger=_ledger(bundle,c,p,len(selected),external_overhead_bytes)
    return {'manifest':copy.deepcopy(nm),'base_manifest':copy.deepcopy(bm),'rows':rows,
        'legacy_manifest_bytes':bundle['base/legacy-manifest.json'],'legacy_events_bytes':bundle['base/legacy-events.jsonl'],
        'events':[copy.deepcopy(e) for e in events if e['kind']!='chunk'],'selected_frames':selected_frames,
        'snapshot_reference':snapshot,'trace_digest':bm['trace_digest'],'terminal_proof':p,'context':c,
        'byte_ledger':ledger,'preservation':_scope()}


def prove_terminal_numeric_vnext(raw,bundle,receipt, *, external_overhead_bytes):
    """Compare every stored base/companion field to supplied raw exactly."""
    read=read_terminal_numeric_vnext(bundle,receipt=receipt,external_overhead_bytes=external_overhead_bytes)
    projected,_,snapshot=_raw(raw,read['context'],read['terminal_proof'])
    _same(snapshot,read['snapshot_reference'])
    for raw_row,projected_row,stored in zip(raw['terminal_raw']['rows'],projected,read['rows']):
        for name in (*BASE_ARRAYS,*numeric.NUMERIC_FIELDS):
            left=raw_row[name] if name in numeric.NUMERIC_FIELDS else projected_row[name]
            right=stored[name]
            _require(left.dtype.str==right.dtype.str and left.shape==right.shape and left.tobytes()==right.tobytes(),
                'PURE supplied raw array differs: '+name)
    for tick,frames in read['selected_frames'].items():
        original=raw['terminal_raw']['rows'][tick-read['terminal_proof']['boundary_tick']]
        for name,array in frames.items():
            _require(original[name].dtype.str==array.dtype.str and original[name].shape==array.shape
                and original[name].tobytes()==array.tobytes(),'PURE supplied selected pixel differs')
    _require(read['legacy_manifest_bytes']==raw['recorded_manifest_bytes']
        and read['legacy_events_bytes']==raw['recorded_events_bytes'],'PURE recorded copy differs')
    read['preservation']=_scope(True,len(read['rows']))
    return read


PROTOCOL_BYTES=artifacts._read(PROTOCOL_PATH,MiB)
PROTOCOL=compact._canonical(PROTOCOL_BYTES,'PURE numeric profile')
_require(memory.canonical_bytes(_profile_contract())==PROTOCOL_BYTES,'PURE numeric profile differs from fixed contract')
PROTOCOL_SHA256=hashlib.sha256(PROTOCOL_BYTES).hexdigest()
PROFILE_DESCRIPTOR=_file_descriptor(PROTOCOL_PATH,PROTOCOL_BYTES)
