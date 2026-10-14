"""Authored historical catalogs; no actual project or held-out catalog reads."""
import copy
import hashlib
import importlib
import importlib.util
import json

import pytest


def raw(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def subject():
    name='palimpsest.puck_scene_catalog'
    assert importlib.util.find_spec(name) is not None,'Historical catalog normalization missing'
    return importlib.import_module(name)


def catalog():
    return {'id':'m6-puck-pushing-plan-v5','version':1,'layouts':[
        {'seed':6000,'split':'train','rover_pose':[-1,0,0],'puck_xy':[0,0],
         'goal_xy':[1.5,0],'initial_qvel':'all zeros'},
        {'seed':6200,'split':'held_out','rover_pose':[-1,.5,0],'puck_xy':[0,.5],
         'goal_xy':[1.5,.5],'initial_qvel':'all zeros'}],
        'physics_cases':[{'seed':5100,'id':'fixture','action':[.1,.1],'check':'fixture',
         'puck_xy':[0,-.5],'goal_xy':[1.5,-.5],'rover_pose':[-1,-.5,0],'ticks':20}],
        'model_seed':6110,'output_bytes':6120,'sha256':'a'*64}


def test_actual_historical_normalization_preserves_payload_and_reports_catalog_exposure():
    value=catalog();result=subject().parse_task_catalog(raw(value))
    assert [x['scene_id'] for x in result['scenes']]==[6000,6200,5100]
    assert result['held_out_catalog_read'] is True
    assert result['held_out_runtime_opened'] is False
    assert result['inventory_complete'] is False and result['executable'] is False
    assert result['qualification_claims']==[]
    first=result['scenes'][0]
    assert first['payload_sha256']==hashlib.sha256(raw(value['layouts'][0])).hexdigest()
    assert first['pointer']=='/layouts/0' and first['split']=='train'
    physics={k:value['physics_cases'][0][k] for k in ('seed','rover_pose','puck_xy','goal_xy')}
    physics.update(split='mechanics',initial_qvel='all zeros')
    assert result['scenes'][2]['payload_sha256']==hashlib.sha256(raw(physics)).hexdigest()
    assert result['document_sha256']==hashlib.sha256(raw(value)).hexdigest()


def test_geometry_domains_match_v3_without_inventing_legacy_slot():
    from palimpsest import puck_on_policy as adapter
    legacy=catalog()['layouts'][0]
    row={'version':1,'kind':adapter.SCHEMA,'seed':7100,'slot':0,
         'split':adapter.COLLECTION_SPLIT,
         'rover_pose':list(map(float,legacy['rover_pose'])),
         'puck_xy':list(map(float,legacy['puck_xy'])),
         'goal_xy':list(map(float,legacy['goal_xy'])),'initial_qvel':'all zeros'}
    expected=adapter.scene_candidate_identities(row)
    actual=subject().parse_task_catalog(raw(catalog()))['scenes'][0]
    for key in ('canonical_scene_sha256','scientific_initial_sha256'):
        assert actual[key]==expected[key]
    assert actual['payload_sha256']!=expected['payload_sha256']
    assert 'slot' not in actual and 'layout' not in actual


@pytest.mark.parametrize('number',range(1,6))
def test_exact_historical_task_versions_are_supported(number):
    value=catalog();value['id']=f'm6-puck-pushing-plan-v{number}'
    assert len(subject().parse_task_catalog(raw(value))['scenes'])==3


@pytest.mark.parametrize('defect',[
 'schema','version','float-id','bool-id','negative-id','duplicate','layout-extra',
 'layout-missing','wrong-split','nonzero-velocity','nonfinite','signed-zero',
 'wrong-vector','arena','reserved-id','reserved-physics','heldout-wrong-split',
 'train-heldout-label','extra-scene-roster','missing-physics','empty-layouts'])
def test_unsupported_or_ambiguous_scene_catalog_fails_closed(defect):
    value=catalog();row=value['layouts'][0]
    if defect=='schema':value['id']='unknown-puck-plan'
    elif defect=='version':value['version']=True
    elif defect=='float-id':row['seed']=6000.0
    elif defect=='bool-id':row['seed']=True
    elif defect=='negative-id':row['seed']=-1
    elif defect=='duplicate':value['layouts'].append(copy.deepcopy(row))
    elif defect=='layout-extra':row['scene_id']=6001
    elif defect=='layout-missing':del row['goal_xy']
    elif defect=='wrong-split':row['split']='unknown'
    elif defect=='nonzero-velocity':row['initial_qvel']='unknown'
    elif defect=='nonfinite':row['goal_xy'][0]=float('inf')
    elif defect=='signed-zero':row['puck_xy'][0]=-0.0
    elif defect=='wrong-vector':row['rover_pose']=[0,0]
    elif defect=='arena':row['goal_xy'][0]=99
    elif defect=='reserved-id':row['seed']=6110
    elif defect=='reserved-physics':value['physics_cases'][0]['seed']=6120
    elif defect=='heldout-wrong-split':value['layouts'][1]['split']='train'
    elif defect=='train-heldout-label':row['split']='held_out'
    elif defect=='extra-scene-roster':value['scene_ids']=[7000]
    elif defect=='missing-physics':del value['physics_cases']
    elif defect=='empty-layouts':value['layouts']=[]
    # Nonfinite source bytes are deliberately emitted by permissive authored JSON.
    payload=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    with pytest.raises((ValueError,TypeError)):
        subject().parse_task_catalog(payload)


@pytest.mark.parametrize('payload',[b'{"id":"x","id":"x"}',b'{"x":NaN}',b'[]',b'{}',b'x',b'x'*(4*1024**2+1)],ids=['duplicate-key','nonfinite','array','empty','syntax','oversize'])
def test_bounded_strict_json_is_required(payload):
    with pytest.raises(ValueError):subject().parse_task_catalog(payload)


def test_no_catalog_exposure_claim_when_fixture_contains_no_held_out_row():
    value=catalog();value['layouts']=value['layouts'][:1]
    assert subject().parse_task_catalog(raw(value))['held_out_catalog_read'] is False


def test_distinct_payloads_of_same_geometry_are_not_conflated():
    first=catalog();second=catalog();second['layouts'][0]['seed']=6001
    a=subject().parse_task_catalog(raw(first))['scenes'][0]
    b=subject().parse_task_catalog(raw(second))['scenes'][0]
    assert a['canonical_scene_sha256']==b['canonical_scene_sha256']
    assert a['scientific_initial_sha256']==b['scientific_initial_sha256']
    assert a['payload_sha256']!=b['payload_sha256']


def test_results_are_independent_defensive_documents():
    value=catalog();result=subject().parse_task_catalog(raw(value))
    result['scenes'][0]['scene_id']=99
    assert subject().parse_task_catalog(raw(value))['scenes'][0]['scene_id']==6000
