"""Authored JSON dependency chains; no actual catalogs, models or native owners."""
import copy
import time
import pytest
from palimpsest import puck_scene_reference_resolution as s
from test_puck_scene_training import raw, sha, training, report, prepared, index
from test_puck_scene_reference_resolution import documents as historical_documents


def documents():
    docs=historical_documents();catalog,manifest,collector=docs
    protocol=training();protocol['collection_report']={'path':collector['path'],'sha256':sha(collector['raw'])}
    protocol['sources'][0].update(path='/authored/recording',manifest_sha256=sha(manifest['raw']),
        source_hashes={'manifest.json':sha(manifest['raw'])})
    protocol_raw=raw(protocol)
    result=report();result.update(protocol_sha256=sha(protocol_raw))
    result['files'][0].update(sha256=sha(protocol_raw),bytes=len(protocol_raw))
    result['files'].append({'path':'checkpoint.npz','sha256':'c'*64,'bytes':123});result_raw=raw(result)
    model_index=index();model_index['models'][0]['files'].update({'protocol.json':sha(protocol_raw),'report.json':sha(result_raw)})
    wrapper=prepared();wrapper.update(protocol=protocol,protocol_sha256=sha(protocol_raw))
    docs.extend([{'path':'/authored/models/seed-21/protocol.json','kind':'training_protocol','raw':protocol_raw},
        {'path':'/authored/models/seed-21/report.json','kind':'training_report','raw':result_raw},
        {'path':'/authored/model-index.json','kind':'model_index','raw':raw(model_index)},
        {'path':'/authored/prepared.json','kind':'prepared_training','raw':raw(wrapper)}])
    return docs


def resolve(docs, origins=None):
    return s.resolve_retained_puck_documents(docs,deadline=time.monotonic()+10,origins=origins)


def test_full_selected_training_chain_resolves_scene_without_making_model_seed_scene():
    result=resolve(documents(),origins={'/authored/model-index.json':'/authored/models'})
    assert result['declared_reference_closure_resolved'] is True
    assert {row['scene_id'] for row in result['variants']}=={6000}
    occurrences=result['variants'][0]['occurrences']
    assert any(row['document_path']=='/authored/prepared.json' and row['pointer']=='/protocol/sources/0/seed' for row in occurrences)
    assert result['inventory_complete'] is False and result['executable'] is False


def test_training_report_local_ledger_reference_never_uses_registered_historical_cwd():
    docs=documents();docs=[doc for doc in docs if doc['kind']!='model_index']
    result=resolve(docs,origins={'/authored/models/seed-21/report.json':'/different/historical/cwd'})
    assert result['declared_reference_closure_resolved'] is True
    link=next(row for row in result['resolved_references'] if row['document_path'].endswith('/seed-21/report.json'))
    assert link['path']=='/authored/models/seed-21/protocol.json'


def test_index_relative_paths_require_explicit_origin():
    result=resolve(documents())
    assert result['declared_reference_closure_resolved'] is False
    assert sum(row['reason']=='relative_reference_without_recorded_cwd' for row in result['unresolved_references'])==2


@pytest.mark.parametrize('defect',['model-seed','bytes','missing-protocol','relocated-protocol'])
def test_correct_byte_hash_alone_does_not_bind_conflicting_or_missing_protocol(defect):
    docs=documents();docs=[doc for doc in docs if doc['kind'] not in ('model_index','prepared_training')]
    result=next(doc for doc in docs if doc['kind']=='training_report')
    import json
    value=json.loads(result['raw'])
    if defect=='model-seed':value['training_seed']=22
    elif defect=='bytes':value['files'][0]['bytes']+=1
    elif defect=='missing-protocol':docs=[doc for doc in docs if doc['kind']!='training_protocol']
    else:next(doc for doc in docs if doc['kind']=='training_protocol')['path']='/other/protocol.json'
    result['raw']=raw(value)
    evidence=resolve(docs)
    assert evidence['declared_reference_closure_resolved'] is False
    assert evidence['unresolved_references']


def test_new_families_work_in_selected_file_custody(tmp_path):
    entries=[]
    # Prepared wrapper uses only explicitly absolute historical references.
    for doc in documents():
        if doc['kind']=='model_index':continue
        name=str(len(entries))+'.json';(tmp_path/name).write_bytes(doc['raw'])
        entries.append({'path':name,'kind':doc['kind'],'size_bytes':len(doc['raw']),'sha256':sha(doc['raw'])})
    registration=raw({'id':'puck-retained-scene-inputs-v1','version':1,
        'roots':[{'root':str(tmp_path),'files':entries}],'origins':[]})
    with s.HeldRetainedPuckDocuments(registration,expected_sha256=sha(registration),deadline=time.monotonic()+10) as held:
        assert held.snapshot()['registered_document_bytes_authenticated'] is True
        assert held.snapshot()['inventory_complete'] is False
        held.recheck()


def development_documents():
    from test_puck_scene_reports import development_report, owner_result
    from test_puck_scene_catalog import catalog
    from test_puck_scene_retained import manifest
    catalog_value=catalog();catalog_value['layouts'][0].update(seed=6100,split='closed_loop_dev')
    catalog_raw=raw(catalog_value)
    owner=owner_result();owner['row'].update(seed=6100,id='student-dev-6100-seed21',case='student-dev-6100-seed21');owner['student_identity']['pushing_protocol_sha256']=sha(catalog_raw)
    owner_raw=raw(owner)
    recording=manifest('puck-student-development-v1');recording.update(row=copy.deepcopy(owner['row']),
        seed=6100,split='closed_loop_dev',pushing_protocol_sha256=sha(catalog_raw))
    recording_raw=raw(recording)
    report_value=development_report();report_value['owners'][0].update(owner['row']);report_value['owners'][0].update(output='/authored/dev/scene21',
        result_sha256=sha(owner_raw),manifest_sha256=sha(recording_raw),result=copy.deepcopy(owner))
    return [{'path':'/authored/catalog.json','kind':'task_catalog','raw':catalog_raw},
        {'path':'/authored/dev/scene21/result.json','kind':'owner_result','raw':owner_raw},
        {'path':'/authored/dev/scene21/recording/manifest.json','kind':'recording_manifest','raw':recording_raw},
        {'path':'/authored/dev/report.json','kind':'development_report','raw':raw(report_value)}]


def test_development_report_binds_parent_roster_through_declared_result_and_manifest():
    result=resolve(development_documents())
    assert result['declared_reference_closure_resolved'] is True
    assert {row['scene_id'] for row in result['variants']}=={6100}
    assert {item['document_path'] for item in result['variants'][0]['occurrences']}=={
        '/authored/dev/report.json','/authored/dev/scene21/result.json','/authored/dev/scene21/recording/manifest.json'}


@pytest.mark.parametrize('defect',['model-seed','row-boundary','embedded-result','catalog'])
def test_development_owner_reference_requires_actual_row_and_embedded_content_agreement(defect):
    import json
    docs=development_documents();child=json.loads(docs[1]['raw']);parent=json.loads(docs[3]['raw'])
    if defect=='model-seed':
        child['row']['model_seed']=22;child['student_identity']['model_identity']['training_seed']=22
    elif defect=='row-boundary':child['row']['boundary']='different'
    elif defect=='embedded-result':child['model_calls']=1
    else:child['student_identity']['pushing_protocol_sha256']='e'*64
    docs[1]['raw']=raw(child);parent['owners'][0]['result_sha256']=sha(docs[1]['raw']);docs[3]['raw']=raw(parent)
    result=resolve(docs)
    assert result['declared_reference_closure_resolved'] is False
    assert result['unresolved_references']


@pytest.mark.parametrize('embedded', [False, True])
def test_development_parent_scene_resolves_from_genuine_result_without_manifest(embedded):
    import json
    docs=development_documents();docs=[doc for doc in docs if doc['kind']!='recording_manifest']
    value=json.loads(docs[-1]['raw']);value['owners'][0].pop('manifest_sha256')
    if not embedded:value['owners'][0].pop('result')
    docs[-1]['raw']=raw(value)
    evidence=resolve(docs)
    assert evidence['declared_reference_closure_resolved'] is True
    assert any(row['document_path']=='/authored/dev/report.json' for row in evidence['variants'][0]['occurrences'])


def test_declared_embedded_result_without_output_can_bind_parent_scene_from_own_catalog_pin():
    import json
    docs=development_documents();docs=[doc for doc in docs if doc['kind'] in ('task_catalog','development_report')]
    value=json.loads(docs[-1]['raw']);owner=value['owners'][0]
    for key in ('manifest_sha256','result_sha256','output'):owner.pop(key)
    docs[-1]['raw']=raw(value)
    evidence=resolve(docs)
    assert evidence['declared_reference_closure_resolved'] is True
    assert len(evidence['variants'][0]['occurrences'])==2


def test_baseline_dependency_checks_owner_and_snapshot_receipts():
    import json
    from test_puck_scene_reports import owner_result, snapshot
    docs=development_documents();parent=json.loads(docs[-1]['raw'])
    first=json.loads(docs[1]['raw']);first['snapshots']={'initial':snapshot()}
    first_raw=raw(first);docs[1]['raw']=first_raw
    docs[1]['path']='/authored/dev/student-dev-6100-seed21/result.json'
    docs[2]['path']='/authored/dev/student-dev-6100-seed21/recording/manifest.json'
    parent['owners'][0].update(output='/authored/dev/student-dev-6100-seed21',
        result=copy.deepcopy(first),result_sha256=sha(first_raw))
    second=owner_result(22);second['row'].update(seed=6100,id='student-dev-6100-seed22',case='student-dev-6100-seed22')
    second['student_identity']['pushing_protocol_sha256']=first['student_identity']['pushing_protocol_sha256']
    second['initial_match']={'status':'failed','reference':{
        'owner_id':'student-dev-6100-seed21','result_sha256':sha(first_raw),'snapshot_sha256':'f'*64}}
    parent['owners'].append({**second['row'],'status':'failed','output':'/authored/dev/scene22','result':second})
    docs[-1]['raw']=raw(parent)
    evidence=resolve(docs)
    baseline=next(row for row in evidence['unresolved_references'] if row['pointer'].endswith('/initial_match/reference'))
    assert baseline['reason']=='target_baseline_snapshot_differs'
    assert evidence['declared_reference_closure_resolved'] is False


def test_report_recording_manifest_must_agree_with_full_owner_row_and_model():
    import json
    docs=development_documents();child=json.loads(docs[2]['raw']);parent=json.loads(docs[-1]['raw'])
    child['row']['model_seed']=child['model_identity']['training_seed']=22
    docs[2]['raw']=raw(child);parent['owners'][0]['manifest_sha256']=sha(docs[2]['raw']);docs[-1]['raw']=raw(parent)
    evidence=resolve(docs)
    assert any(row['reason']=='target_recording_row_differs' for row in evidence['unresolved_references'])


def test_explicit_report_catalog_cannot_bypass_conflicting_external_result_catalog():
    import json
    docs=development_documents();docs=[doc for doc in docs if doc['kind']!='recording_manifest']
    child=json.loads(docs[1]['raw']);parent=json.loads(docs[-1]['raw'])
    parent['pushing_protocol_sha256']=sha(docs[0]['raw']);owner=parent['owners'][0]
    owner.pop('result');owner.pop('manifest_sha256')
    other_catalog=json.loads(docs[0]['raw']);other_catalog['layouts'][0]['goal_xy'][0]=1.75
    other_raw=raw(other_catalog);child['student_identity']['pushing_protocol_sha256']=sha(other_raw)
    docs[1]['raw']=raw(child);owner['result_sha256']=sha(docs[1]['raw']);docs[-1]['raw']=raw(parent)
    docs.append({'path':'/authored/other-catalog.json','kind':'task_catalog','raw':other_raw})
    evidence=resolve(docs)
    assert any(row['reason']=='target_catalog_pin_differs' for row in evidence['unresolved_references'])
    assert len(evidence['variants'])==2


def test_model_index_checks_declared_checkpoint_receipt_in_pinned_training_report():
    import json
    docs=documents();child=next(doc for doc in docs if doc['kind']=='training_report')
    value=json.loads(child['raw']);value['files'][1]['sha256']='f'*64
    child['raw']=raw(value);parent=next(doc for doc in docs if doc['kind']=='model_index')
    value=json.loads(parent['raw']);value['models'][0]['files']['report.json']=sha(child['raw']);parent['raw']=raw(value)
    evidence=resolve(docs,origins={'/authored/model-index.json':'/authored/models'})
    assert any(row['reason']=='target_model_file_receipt_differs' for row in evidence['unresolved_references'])


@pytest.mark.parametrize('objective_pin', ['invalid','f'*64])
def test_balanced_training_report_objective_must_bind_pinned_protocol(objective_pin):
    import json
    docs=documents();docs=[doc for doc in docs if doc['kind'] not in ('model_index','prepared_training')]
    protocol=next(doc for doc in docs if doc['kind']=='training_protocol')
    value=json.loads(protocol['raw']);value.update(schema='puck-balanced-training-v1',
        balanced_objective={'path':'/authored/objective.json','sha256':'a'*64})
    protocol['raw']=raw(value)
    result=next(doc for doc in docs if doc['kind']=='training_report');value=json.loads(result['raw'])
    value.update(protocol_sha256=sha(protocol['raw']),training_objective_sha256=objective_pin)
    value['files'][0].update(sha256=sha(protocol['raw']),bytes=len(protocol['raw']));result['raw']=raw(value)
    if objective_pin=='invalid':
        with pytest.raises(ValueError):resolve(docs)
    else:
        evidence=resolve(docs)
        assert any(row['reason']=='target_training_objective_differs' for row in evidence['unresolved_references'])


def test_manifest_model_hashes_must_match_declared_report_model_identity():
    import json
    docs=development_documents();child=json.loads(docs[2]['raw']);parent=json.loads(docs[-1]['raw'])
    child['model_identity']['checkpoint_sha256']='f'*64
    docs[2]['raw']=raw(child);parent['owners'][0]['manifest_sha256']=sha(docs[2]['raw']);docs[-1]['raw']=raw(parent)
    evidence=resolve(docs)
    assert any(row['reason']=='target_model_identity_differs' for row in evidence['unresolved_references'])
