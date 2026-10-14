"""Authored retained/catalog references; no real retained inputs are opened."""
import copy
import hashlib
import importlib
import importlib.util
import json
import time

import pytest

from test_puck_scene_catalog import catalog, raw


def module():
    name = 'palimpsest.puck_scene_reference_resolution'
    assert importlib.util.find_spec(name), 'Bounded retained reference resolution missing'
    return importlib.import_module(name)


def sha(payload): return hashlib.sha256(payload).hexdigest()


def manifest(catalog_raw=None):
    catalog_raw = raw(catalog()) if catalog_raw is None else catalog_raw
    row = {'id': 'teacher-6000', 'case': 'teacher-6000', 'kind': 'root',
           'seed': 6000, 'split': 'train', 'max_ticks': 600, 'max_bytes': 160*1024**2}
    return {'schema': 'puck-demonstration-v1', 'protocol_sha256': 'a'*64,
        'pushing_protocol_sha256': sha(catalog_raw), 'learning_protocol_sha256': 'b'*64,
        'teacher_source_sha256': 'c'*64, 'supervisor_source_sha256': 'd'*64,
        'teacher_id': 'authored-teacher', 'learning_feature_id': 'authored-feature',
        'row': row, 'seed': 6000, 'split': 'train', 'episodes': 1,
        'source': None, 'source_hashes': {}, 'profile_identity': {},
        'full_model_sha256': 'e'*64, 'contact_ownership': {}, 'record_contract': 'authored',
        'initial_supervisor': {'version': 1, 'protocol_sha256': 'b'*64, 'tick': 0, 'mode': 'approach'},
        'status': 'failed'}


def report(manifest_raw, catalog_raw, recording='/authored/recording'):
    row = manifest(catalog_raw)['row']
    return {'status': 'failed', 'commit': '1'*40, 'pushing_protocol_sha256': sha(catalog_raw),
        'learning_protocol_sha256': 'b'*64, 'teacher_source_sha256': 'c'*64,
        'supervisor_source_sha256': 'd'*64, 'teacher_id': 'authored-teacher',
        'learning_feature_id': 'authored-feature', 'source_hashes': {},
        'sources': [{'seed': 6000, 'split': 'train', 'path': recording, 'manifest_sha256': sha(manifest_raw)}],
        'owners': [{**row, 'status': 'not_started'}], 'admission': {'status': 'not_started', 'rows': []},
        'qualification_claims': [], 'finalization_errors': []}


def documents():
    cat_raw = raw(catalog()); manifest_raw = raw(manifest(cat_raw))
    return [{'path': '/authored/catalog.json', 'kind': 'task_catalog', 'raw': cat_raw},
        {'path': '/authored/recording/manifest.json', 'kind': 'recording_manifest', 'raw': manifest_raw},
        {'path': '/authored/report.json', 'kind': 'teacher_collection_report',
         'raw': raw(report(manifest_raw, cat_raw))}]


def resolve(docs, **kwargs):
    return module().resolve_retained_puck_documents(docs,
        deadline=kwargs.pop('deadline', time.monotonic()+10), **kwargs)


def test_failed_and_not_started_mentions_resolve_genuine_catalog_identities():
    docs = documents(); before = copy.deepcopy(docs)
    result = resolve(docs)
    assert docs == before
    assert result['declared_reference_closure_resolved'] is True
    assert result['unresolved_references'] == [] and result['unresolved_mentions'] == []
    assert len(result['variants']) == 1 and result['variants'][0]['scene_id'] == 6000
    assert len(result['variants'][0]['occurrences']) >= 4
    assert {row['document_path'] for row in result['variants'][0]['occurrences']} == {
        '/authored/report.json', '/authored/recording/manifest.json'}
    expected = hashlib.sha256(raw(catalog()['layouts'][0])).hexdigest()
    assert result['variants'][0]['payload_sha256'] == expected
    assert result['resolved_references'][0]['path'] == '/authored/recording/manifest.json'
    assert result['held_out_catalog_read'] is True
    for key in ('inventory_complete', 'source_closure_authenticated', 'executable',
                'reservation_authorized', 'collection_authorized', 'held_out_runtime_opened'):
        assert result[key] is False
    assert result['qualification_claims'] == []
    assert resolve(list(reversed(docs))) == result


@pytest.mark.parametrize('defect', ['missing-target', 'wrong-digest', 'null-digest',
    'wrong-target-kind', 'catalog-missing', 'catalog-wrong', 'scene-conflict'])
def test_unresolved_reference_or_scene_never_silently_disappears(defect):
    docs = documents()
    if defect == 'missing-target': docs.pop(1)
    elif defect == 'wrong-digest':
        value=json.loads(docs[2]['raw']);value['sources'][0]['manifest_sha256']='f'*64;docs[2]['raw']=raw(value)
    elif defect == 'null-digest':
        value=json.loads(docs[2]['raw']);value['sources'][0]['manifest_sha256']=None;docs[2]['raw']=raw(value)
    elif defect == 'wrong-target-kind':
        docs[1]['kind']='task_catalog';docs[1]['raw']=docs[0]['raw']
        value=json.loads(docs[2]['raw']);value['sources'][0]['manifest_sha256']=sha(docs[1]['raw']);docs[2]['raw']=raw(value)
    elif defect == 'catalog-missing': docs.pop(0)
    elif defect == 'catalog-wrong':
        value=catalog();value['layouts'][0]['goal_xy'][0]=1.75;docs[0]['raw']=raw(value)
    elif defect == 'scene-conflict':
        value=json.loads(docs[1]['raw']);value['seed']=6001;value['row']['seed']=6001;docs[1]['raw']=raw(value)
        value=json.loads(docs[2]['raw']);value['sources'][0]['manifest_sha256']=sha(docs[1]['raw']);docs[2]['raw']=raw(value)
    result=resolve(docs)
    assert result['declared_reference_closure_resolved'] is False
    assert result['unresolved_references'] or result['unresolved_mentions'] or result['missing_pins']
    assert result['inventory_complete'] is False


def test_explicit_recorded_cwd_is_required_for_relative_directory_references():
    docs=documents();value=json.loads(docs[2]['raw']);value['sources'][0]['path']='recording';docs[2]['raw']=raw(value)
    assert resolve(docs)['declared_reference_closure_resolved'] is False
    result=resolve(docs,origins={'/authored/report.json':'/authored'})
    assert result['declared_reference_closure_resolved'] is True
    assert result['resolved_references'][0]['path']=='/authored/recording/manifest.json'


def test_training_source_geometry_is_resolved_through_exact_manifest_reference():
    docs=documents(); manifest_sha=sha(docs[1]['raw']); report_sha=sha(docs[2]['raw'])
    protocol={'schema':'puck-training-v1','learning_protocol_sha256':'b'*64,'training_seed':6110,
        'learning':{},'action_arithmetic':'authored','checkpoint':'authored',
        'collection_report':{'path':'/authored/report.json','sha256':report_sha},
        'sources':[{'seed':6000,'split':'train','ticks':32,'manifest_sha256':manifest_sha,
            'source_hashes':{},'feature_sha256':'a'*64,'target_sha256':'b'*64,'path':'/authored/recording'}],
        'source_hashes':{},'limits':{}}
    docs.append({'path':'/authored/protocol.json','kind':'training_protocol','raw':raw(protocol)})
    result=resolve(docs)
    assert result['declared_reference_closure_resolved'] is True
    assert [row['scene_id'] for row in result['variants']]==[6000]
    assert any(row['document_path']=='/authored/protocol.json' for row in result['variants'][0]['occurrences'])


def test_authentic_catalog_variants_are_retained_across_retained_records():
    docs=documents();changed=catalog();changed['layouts'][0]['goal_xy'][0]=1.75;payload=raw(changed)
    docs += [{'path':'/authored/other-catalog.json','kind':'task_catalog','raw':payload},
             {'path':'/authored/other-manifest.json','kind':'recording_manifest','raw':raw(manifest(payload))}]
    result=resolve(docs)
    assert len(result['variants'])==2
    assert result['id_variants']==[{'scene_id':6000,'variant_indices':[0,1]}]
    assert result['legacy_scene_rows_compatible'] is False


@pytest.mark.parametrize('defect',['duplicate','path','kind','fields','bytes','origins'])
def test_ambiguous_registered_byte_views_refuse(defect):
    docs=documents();kwargs={}
    if defect=='duplicate':docs.append(copy.deepcopy(docs[0]))
    elif defect=='path':docs[0]['path']='/authored/../catalog.json'
    elif defect=='kind':docs[0]['kind']='unknown'
    elif defect=='fields':docs[0]['complete']=True
    elif defect=='bytes':docs[0]['raw']=bytearray(docs[0]['raw'])
    else:kwargs['origins']={'/unregistered/document.json':'/authored'}
    with pytest.raises(ValueError):resolve(docs,**kwargs)


@pytest.mark.parametrize('deadline',[True,-1,float('nan'),float('inf')])
def test_deadline_bound_refuses(deadline):
    with pytest.raises((ValueError,TimeoutError)):resolve(documents(),deadline=deadline)


def registration(tmp_path):
    docs=documents();root=tmp_path/'authored';root.mkdir()
    cat=docs[0]['raw'];man=docs[1]['raw'];rep=raw(report(man,cat,str(root/'recording')))
    payloads={'catalog.json':('task_catalog',cat),'recording/manifest.json':('recording_manifest',man),
              'report.json':('teacher_collection_report',rep)}
    files=[]
    for path,(kind,payload) in sorted(payloads.items()):
        leaf=root/path;leaf.parent.mkdir(parents=True,exist_ok=True);leaf.write_bytes(payload)
        files.append({'path':path,'size_bytes':len(payload),'sha256':sha(payload),'kind':kind})
    value={'id':'puck-retained-scene-inputs-v1','version':1,'roots':[{'root':str(root),'files':files}],'origins':[]}
    return root,raw(value)


def held(registration_raw,**kwargs):
    return module().HeldRetainedPuckDocuments(registration_raw,
        expected_sha256=kwargs.pop('expected_sha256',sha(registration_raw)),
        deadline=kwargs.pop('deadline',time.monotonic()+10),**kwargs)


def test_actual_held_file_custody_resolves_and_protects_independent_receipt(tmp_path):
    root,reg=registration(tmp_path)
    with held(reg) as sources:
        result=sources.snapshot()
        assert result['declared_reference_closure_resolved'] is True
        assert result['registered_document_bytes_authenticated'] is True
        assert result['inventory_complete'] is False
        result['variants'].clear()
        assert len(sources.snapshot()['variants'])==1
        sources.recheck()
    for op in (sources.snapshot,sources.recheck,sources.__enter__):
        with pytest.raises(RuntimeError):op()


@pytest.mark.parametrize('change',['edit','extra-link','symlink','snapshot-copy'])
def test_held_payload_or_edge_drift_poisons_context(tmp_path,monkeypatch,change):
    root,reg=registration(tmp_path);sources=held(reg)
    with pytest.raises((RuntimeError,ValueError,OSError)):
        with sources:
            leaf=root/'catalog.json'
            if change=='edit':leaf.write_bytes(b'changed')
            elif change=='extra-link':
                import os;os.link(leaf,root/'extra')
            elif change=='symlink':leaf.rename(root/'original');leaf.symlink_to(root/'original')
            else:
                original=module().copy.deepcopy
                def drift(value):
                    result=original(value);leaf.write_bytes(b'changed');return result
                monkeypatch.setattr(module().copy,'deepcopy',drift)
            sources.snapshot()
    with pytest.raises(RuntimeError):sources.snapshot()


def test_body_failure_remains_primary_if_final_file_check_also_fails(tmp_path):
    root,reg=registration(tmp_path);failure=LookupError('authored body failure')
    with pytest.raises(LookupError) as caught:
        with held(reg):
            (root/'catalog.json').write_bytes(b'changed')
            raise failure
    assert caught.value is failure
    assert failure.__notes__


def test_external_registration_hash_is_required_before_any_input_open(tmp_path):
    _,reg=registration(tmp_path)
    with pytest.raises(ValueError):held(reg,expected_sha256='0'*64)


def test_recorded_root_cwd_is_a_valid_explicit_origin():
    docs=documents()
    for doc in docs:doc['path']=doc['path'].removeprefix('/authored')
    value=json.loads(docs[2]['raw']);value['sources'][0]['path']='recording';docs[2]['raw']=raw(value)
    assert resolve(docs,origins={'/report.json':'/'})['declared_reference_closure_resolved'] is True


def test_caught_payload_failure_cannot_end_as_successful_custody_close(tmp_path):
    root,reg=registration(tmp_path)
    with pytest.raises(RuntimeError):
        with held(reg) as sources:
            (root/'catalog.json').write_bytes(b'changed')
            with pytest.raises((ValueError,RuntimeError)):sources.recheck()


@pytest.mark.parametrize('cap',['MAX_FILES','MAX_TOTAL_BYTES','MAX_METADATA_BYTES','MAX_REFERENCES','MAX_OCCURRENCES','MAX_VARIANTS'])
def test_resolution_source_caps_refuse_partial_success(monkeypatch,cap):
    monkeypatch.setattr(module(),cap,0)
    with pytest.raises(ValueError):resolve(documents())


@pytest.mark.parametrize('defect',['duplicate-key','unknown-field','overlap','descriptor-order',
    'bad-kind','bad-size','bad-hash','unregistered-origin','duplicate-origin','noncanonical'])
def test_registration_errors_refuse_before_payload_custody(tmp_path,defect):
    _,reg=registration(tmp_path);value=json.loads(reg)
    if defect=='unknown-field':value['complete']=True
    elif defect=='overlap':value['roots'].append(copy.deepcopy(value['roots'][0]))
    elif defect=='descriptor-order':value['roots'][0]['files'].reverse()
    elif defect=='bad-kind':value['roots'][0]['files'][0]['kind']='model'
    elif defect=='bad-size':value['roots'][0]['files'][0]['size_bytes']=True
    elif defect=='bad-hash':value['roots'][0]['files'][0]['sha256']='A'*64
    elif defect=='unregistered-origin':value['origins']=[{'document_path':'/absent.json','cwd':'/authored'}]
    elif defect=='duplicate-origin':
        value['origins']=[{'document_path':str(__import__('pathlib').Path(value['roots'][0]['root'])/'report.json'),'cwd':'/authored'}]*2
    payload=raw(value)
    if defect=='duplicate-key':payload=payload.replace(b'"version":1',b'"version":1,"version":1')
    elif defect=='noncanonical':payload=payload.rstrip(b'\n')
    with pytest.raises(ValueError):held(payload)


def test_held_receipt_prefix_is_inside_the_registered_metadata_ceiling(tmp_path,monkeypatch):
    _,reg=registration(tmp_path)
    with held(reg) as sources:full=sources.snapshot()
    del full['registration_sha256'];del full['registered_document_bytes_authenticated']
    cap=len(json.dumps(full,sort_keys=True,separators=(',',':'),allow_nan=False).encode())+1
    monkeypatch.setattr(module(),'MAX_METADATA_BYTES',cap)
    with pytest.raises(ValueError):
        with held(reg):pass


def test_snapshot_copy_deadline_failure_poison_closes(tmp_path,monkeypatch):
    _,reg=registration(tmp_path)
    with pytest.raises(TimeoutError):
        with held(reg) as sources:
            original=module().copy.deepcopy
            def late(value):
                result=original(value)
                monkeypatch.setattr(module().time,'monotonic',lambda:float('inf'))
                return result
            monkeypatch.setattr(module().copy,'deepcopy',late)
            sources.snapshot()


def protocol_document(docs,path='/authored/recording',manifest_raw=None):
    payload=docs[1]['raw'] if manifest_raw is None else manifest_raw
    return {'schema':'puck-training-v1','learning_protocol_sha256':'b'*64,'training_seed':21,
        'learning':{},'action_arithmetic':'authored','checkpoint':'authored',
        'collection_report':{'path':'/authored/report.json','sha256':sha(docs[2]['raw'])},
        'sources':[{'seed':6000,'split':'train','ticks':32,'manifest_sha256':sha(payload),
            'source_hashes':{},'feature_sha256':'a'*64,'target_sha256':'b'*64,'path':path}],
        'source_hashes':{},'limits':{}}


def test_report_reference_cannot_silently_change_catalog_identity():
    docs=documents();changed=catalog();changed['layouts'][0]['goal_xy'][0]=1.75
    changed_raw=raw(changed);changed_manifest=raw(manifest(changed_raw))
    docs[1]['raw']=changed_manifest;docs[2]['raw']=raw(report(changed_manifest,docs[0]['raw']))
    docs.append({'path':'/authored/catalog2.json','kind':'task_catalog','raw':changed_raw})
    result=resolve(docs)
    assert result['declared_reference_closure_resolved'] is False
    assert any(ref['reason']=='target_catalog_pin_differs' for ref in result['unresolved_references'])
    assert len(result['variants'])==2  # conflicting authentic occurrences are still retained


def test_training_sources_must_match_the_pinned_collection_report_paths_and_pins():
    docs=documents();changed=manifest(docs[0]['raw']);changed['status']='completed';changed=raw(changed)
    docs.append({'path':'/authored/other-recording/manifest.json','kind':'recording_manifest','raw':changed})
    protocol=protocol_document(docs,path='/authored/other-recording',manifest_raw=changed)
    docs.append({'path':'/authored/protocol.json','kind':'training_protocol','raw':raw(protocol)})
    result=resolve(docs)
    assert result['declared_reference_closure_resolved'] is False
    assert any(ref['reason']=='collection_report_source_roster_differs' for ref in result['unresolved_references'])
    assert any(ref['path']=='/authored/other-recording/manifest.json' for ref in result['resolved_references'])


def test_training_report_source_roster_order_is_part_of_reference_binding():
    docs=documents();other=manifest(docs[0]['raw']);other['seed']=6200;other['split']='held_out'
    other['row'].update(seed=6200,split='held_out',id='teacher-6200',case='teacher-6200');payload=raw(other)
    docs.append({'path':'/authored/other/manifest.json','kind':'recording_manifest','raw':payload})
    rep=json.loads(docs[2]['raw']);rep['sources'].append({'seed':6200,'split':'held_out','path':'/authored/other','manifest_sha256':sha(payload)})
    rep['owners'].append({**other['row'],'status':'not_started'});docs[2]['raw']=raw(rep)
    protocol=protocol_document(docs)
    extra={**protocol['sources'][0],'seed':6200,'split':'held_out','path':'/authored/other','manifest_sha256':sha(payload)}
    protocol['sources']=[extra,protocol['sources'][0]]
    docs.append({'path':'/authored/protocol.json','kind':'training_protocol','raw':raw(protocol)})
    result=resolve(docs)
    assert result['declared_reference_closure_resolved'] is False
    assert any(ref['reason']=='collection_report_source_roster_differs' for ref in result['unresolved_references'])
