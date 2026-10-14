"""Registry dependency resolution from authored bytes and temporary files only."""
import copy
import hashlib
import json
import stat
import time

import pytest
from palimpsest import puck_on_policy as p, puck_scene_reference_resolution as subject
from test_puck_on_policy import inventory_snapshot, fake_candidate
from test_puck_scene_reference_resolution import documents as historical_documents, raw


def sha(payload):return hashlib.sha256(payload).hexdigest()


def registry_documents():
    inventory=inventory_snapshot();occupied=p._validate_inventory(inventory,p.PROTOCOL_SHA256)
    inventory_raw=raw(inventory)
    reservation={'version':1,'kind':'puck-on-policy-reservation-v1','lineage_sha256':p.PROTOCOL_SHA256,
        'scene_ids':list(p.RESERVED_SCENE_IDS),'inventory_before_sha256':sha(inventory_raw),
        'inventory_after_sha256':sha(inventory_raw),'inventory':inventory,**occupied}
    reservation_raw=raw(reservation)
    entries=[]
    for slot,scene in enumerate(p.RESERVED_SCENE_IDS):
        split=p.COLLECTION_SPLIT if slot<4 else p.DEVELOPMENT_SPLIT
        layout=fake_candidate(scene,slot,split)
        entries.append({'scene_id':scene,'slot':slot,'split':split,'layout':layout,**p.scene_candidate_identities(layout)})
    scene={'version':1,'kind':'puck-on-policy-scene-manifest-v1','lineage_sha256':p.PROTOCOL_SHA256,
        'reservation_sha256':sha(reservation_raw),'scene_ids':list(p.RESERVED_SCENE_IDS),'scenes':entries}
    scene_raw=raw(scene)
    projection_raw=p._collection_projection_bytes(scene)
    commit=p._commit_receipt('scene-manifest.json',scene,scene_raw);commit_raw=raw(commit)
    identity=[1,2,stat.S_IFREG|0o444,1,len(scene_raw),3,4]
    commit_identity=[1,3,stat.S_IFREG|0o444,1,len(commit_raw),3,4]
    admission=p._admission_receipt('scene-manifest.json',scene_raw,identity,commit_raw,commit_identity,commit)
    return [{'path':'/authored/registry/inventory.json','kind':'on_policy_inventory','raw':inventory_raw},
        {'path':'/authored/reserved/reservation.json','kind':'on_policy_reservation','raw':reservation_raw},
        {'path':'/authored/scenes/scene-manifest.json','kind':'on_policy_scene_manifest','raw':scene_raw},
        {'path':'/authored/collection/projection.json','kind':'on_policy_collection_projection','raw':projection_raw},
        {'path':'/authored/scenes/scene-manifest.json.commit.json','kind':'on_policy_publication_commit','raw':commit_raw},
        {'path':'/authored/scenes/scene-manifest.json.admission.json','kind':'on_policy_publication_admission','raw':raw(admission)}]


def resolve(docs,**kwargs):
    assert hasattr(subject,'resolve_puck_registry_documents'),'Registry reference resolution missing'
    return subject.resolve_puck_registry_documents(docs,deadline=kwargs.get('deadline',time.monotonic()+10))


def test_complete_declared_registry_edges_resolve_without_claiming_prior_geometry():
    docs=registry_documents();before=copy.deepcopy(docs);result=resolve(docs)
    assert docs==before
    assert result['declared_registry_references_resolved'] is True
    assert result['unresolved_references']==[]
    assert [row['scene_id'] for row in result['variants']]==list(p.RESERVED_SCENE_IDS)
    assert [len(row['occurrences']) for row in result['variants']]==[2,2,2,2,1,1,1,1]
    assert {row['scene_id'] for row in result['unbound_scene_declarations']}=={6000}
    assert len(result['unminted_reservations'])==16
    for key in ('inventory_complete','source_closure_authenticated','executable','reservation_authorized','collection_authorized'):
        assert result[key] is False
    assert result['qualification_claims']==[]
    assert resolve(list(reversed(docs)))==result


@pytest.mark.parametrize('defect',['missing-reservation','wrong-reservation-pin','wrong-commit-size',
    'wrong-target-digest','wrong-admission-receipt','wrong-local-target-kind'])
def test_pinned_registry_dependencies_and_receipt_content_must_agree(defect):
    docs=registry_documents()
    if defect=='missing-reservation':docs.pop(1)
    elif defect=='wrong-reservation-pin':
        value=json.loads(docs[2]['raw']);value['reservation_sha256']='f'*64;docs[2]['raw']=raw(value)
    elif defect=='wrong-commit-size':
        value=json.loads(docs[4]['raw']);value['manifest_bytes']+=1;docs[4]['raw']=raw(value)
        value=json.loads(docs[5]['raw']);value['receipt_sha256']=sha(docs[4]['raw']);value['receipt_bytes']=len(docs[4]['raw']);value['receipt_identity'][4]=len(docs[4]['raw']);docs[5]['raw']=raw(value)
    elif defect=='wrong-target-digest':
        value=json.loads(docs[4]['raw']);value['manifest_sha256']='f'*64;docs[4]['raw']=raw(value)
    elif defect=='wrong-admission-receipt':
        value=json.loads(docs[5]['raw']);value['receipt_sha256']='f'*64;docs[5]['raw']=raw(value)
    else:docs[2]['kind']='on_policy_collection_projection';docs[2]['raw']=docs[3]['raw']
    result=resolve(docs)
    assert result['declared_registry_references_resolved'] is False
    assert result['unresolved_references']
    assert result['inventory_complete'] is False


def test_publication_names_use_document_directory_not_process_cwd():
    docs=registry_documents();docs[2]['path']='/other/scene-manifest.json'
    result=resolve(docs)
    assert result['declared_registry_references_resolved'] is False
    assert any(row['reason']=='unregistered_target' for row in result['unresolved_references'])


def test_digest_link_preserves_all_identical_reservation_locations():
    docs=registry_documents();docs.append({**docs[1],'path':'/authored/reserved-copy/reservation.json'})
    result=resolve(docs)
    assert result['declared_registry_references_resolved'] is True
    binding=next(row for row in result['resolved_references'] if row['document_path']==docs[2]['path'])
    assert binding['paths']==['/authored/reserved-copy/reservation.json','/authored/reserved/reservation.json']
    assert len(result['unminted_reservations'])==24


def test_new_registry_families_integrate_with_historical_reference_custody(tmp_path):
    docs=registry_documents()+historical_documents()
    result=subject.resolve_retained_puck_documents(docs,deadline=time.monotonic()+10)
    assert result['registry']['declared_registry_references_resolved'] is True
    assert {row['scene_id'] for row in result['variants']}=={6000,*p.RESERVED_SCENE_IDS}
    assert result['declared_reference_closure_resolved'] is False
    assert result['registry']['unbound_scene_declarations']
    root=tmp_path/'files';root.mkdir();files=[]
    for index,doc in enumerate(docs):
        path=f'{index}.json';(root/path).write_bytes(doc['raw'])
        files.append({'path':path,'kind':doc['kind'],'size_bytes':len(doc['raw']),'sha256':sha(doc['raw'])})
    # Selected custody tests use standalone inventory/projection (no fabricated
    # relocation of path-bearing historical reports or publication receipts).
    selected=[entry for entry in files if entry['kind'] in ('on_policy_inventory','on_policy_collection_projection')]
    registration=raw({'id':'puck-retained-scene-inputs-v1','version':1,'roots':[{'root':str(root),'files':selected}],'origins':[]})
    with subject.HeldRetainedPuckDocuments(registration,expected_sha256=sha(registration),deadline=time.monotonic()+10) as held:
        assert held.snapshot()['registered_document_bytes_authenticated'] is True
        assert held.snapshot()['registry']['unminted_reservations']
        held.recheck()


def test_registry_only_dispatch_has_no_historical_parser_requirement():
    docs=registry_documents();result=subject.resolve_retained_puck_documents(docs,deadline=time.monotonic()+10)
    assert result['registry']['declared_registry_references_resolved'] is True
    assert len(result['variants'])==8
    assert result['declared_reference_closure_resolved'] is False


@pytest.mark.parametrize('defect',['duplicates','extra','unknown-kind','path','not-bytes'])
def test_ambiguous_registered_registry_views_refuse(defect):
    docs=registry_documents()
    if defect=='duplicates':docs.append(copy.deepcopy(docs[0]))
    elif defect=='extra':docs[0]['complete']=True
    elif defect=='unknown-kind':docs[0]['kind']='unknown'
    elif defect=='path':docs[0]['path']='/authored/../inventory.json'
    else:docs[0]['raw']=bytearray(docs[0]['raw'])
    with pytest.raises(ValueError):resolve(docs)


@pytest.mark.parametrize('deadline',[True,-1,float('nan'),float('inf')])
def test_registry_resolution_deadline_is_bounded(deadline):
    with pytest.raises((ValueError,TimeoutError)):resolve(registry_documents(),deadline=deadline)
