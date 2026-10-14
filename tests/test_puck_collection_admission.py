"""Pure supplied-byte admission; no model or native runtime is opened."""
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from palimpsest import puck_on_policy as p

ROOT = Path(__file__).parents[1]
MiB = 1024**2
RUNTIME = {'python':'3.11.15','numpy':'2.2.5','torch':'2.9.0','mujoco':'3.3.6',
           'backend':'egl','device':'cpu','training_and_inference_threads':1}
LIMITS = {'owner_seconds':180,'owner_bytes':160*MiB,'snapshot_bytes':8*MiB,
          'stdout_bytes':MiB,'stderr_bytes':MiB,'metadata_bytes':MiB,
          'recording_bytes':149*MiB,'intervals':600,'active_children':1,
          'stage_bytes':3*1024**3,'rss_bytes':1024**3,'free_bytes':1024**3,
          'retained_bytes':16*1024**3,'child_seconds':2160,'parent_seconds':50,
          'return_seconds':50,'hard_margin_seconds':10,'internal_seconds':2210,
          'normal_seconds':2260,'hard_seconds':2270}


def canonical(value):
    return json.dumps(value,allow_nan=False,sort_keys=True,separators=(',',':')).encode()+b'\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(ordinal=0):
    # Synthetic metadata only; the public minter correctly refuses reserved IDs.
    rows = [p._row(scene_id,slot) for slot,scene_id in enumerate(p.RESERVED_SCENE_IDS)]
    entries = []
    for row in rows[:4]:
        entries.append({'scene_id':row['seed'],'slot':row['slot'],'split':row['split'],
                        'layout':row,**p.scene_candidate_identities(row)})
    projection = canonical({'version':1,'kind':'puck-on-policy-collection-projection-v1',
                            'scene_ids':[6110,6111,6112,6113],'scenes':entries})
    index = (ROOT/'docs/plans/m6-puck-student-models-v1.json').read_bytes()
    sources = {name:'a'*64 for name in ('src/palimpsest/__init__.py',
        'src/palimpsest/puck_on_policy.py','src/palimpsest/puck_collection_admission.py')}
    owners = []
    for scene in (6110,6111,6112,6113):
        for seed in (21,22,23):
            owner_id = f'collection-{scene}-seed-{seed}'
            owners.append({'owner_id':owner_id,'scene_id':scene,'model_seed':seed,
                'argv':['/python','/reviewed-owner','--owner',owner_id],
                'environment':{'MUJOCO_GL':'egl','OMP_NUM_THREADS':'1'},
                'cwd':'/project','output':f'/evidence/collection/{owner_id}'})
    freeze = {'version':1,'kind':'puck-collection-source-freeze-v1',
        'protocol_sha256':p.PROTOCOL_SHA256,'stage':'collection',
        'projection_sha256':sha(projection),'model_index_sha256':sha(index),
        'sources':sources,'runtime':RUNTIME,'upstream_sha256':'b'*64,
        'limits':LIMITS,'attempt':1,'output_root':'/evidence/collection',
        'owners':owners,'qualification_claims':[],'executable':False}
    envelope = {'version':1,'kind':'puck-collection-source-envelope-v1',
        'protocol_sha256':p.PROTOCOL_SHA256,'execution_freeze_sha256':sha(canonical(freeze)),
        'ordinal':ordinal,'owner':owners[ordinal],'attempt':1,
        'projection_sha256':sha(projection),'model_index_sha256':sha(index),
        'sources_sha256':sha(canonical(sources)),'runtime_sha256':sha(canonical(RUNTIME)),
        'qualification_claims':[],'executable':False}
    return dict(envelope_raw=canonical(envelope), execution_freeze_raw=canonical(freeze),
        expected_execution_freeze_sha256=sha(canonical(freeze)),
        collection_projection_raw=projection,original_model_index_raw=index,
        source_before=copy.deepcopy(sources),source_after=copy.deepcopy(sources),
        runtime_observation={**RUNTIME,'upstream_sha256':'b'*64})


def admit(sample):
    name = 'palimpsest.puck_collection_admission'
    assert importlib.util.find_spec(name) is not None, 'Collection envelope checker missing'
    return importlib.import_module(name).admit_collection_envelope(**sample)


@pytest.mark.parametrize('ordinal', range(12))
def test_all_twelve_exact_owners_are_non_executable_and_defensively_copied(ordinal):
    sample = fixture(ordinal)
    before = copy.deepcopy(sample)
    result = admit(sample)
    assert result['owner']['scene_id'] == 6110 + ordinal//3
    assert result['owner']['model_seed'] == 21 + ordinal%3
    assert result['limits']['recording_bytes'] == 149*MiB
    assert result['executable'] is False
    assert result['qualification_claims'] == []
    result['owner']['argv'].append('mutated')
    result['limits']['recording_bytes'] = 0
    assert sample == before
    from scripts.verify_puck_mechanics import owner
    with pytest.raises(ValueError,match='not qualified'):
        owner(admit(sample))


@pytest.mark.parametrize('field,value', [('ordinal',True),('ordinal',1.0),('ordinal',12),
    ('attempt',2),('attempt',True),('executable',True),('qualification_claims',['passed'])])
def test_envelope_aliases_retries_and_qualification_are_rejected(field,value):
    sample = fixture()
    envelope = json.loads(sample['envelope_raw']);envelope[field] = value
    sample['envelope_raw'] = canonical(envelope)
    with pytest.raises(ValueError): admit(sample)


@pytest.mark.parametrize('defect', ['source-before','source-after','initializer','runtime',
    'upstream','model-index','projection','freeze-pin','reordered','limit','limit-alias',
    'held-out','extra-field','noncanonical'])
def test_rejects_drift_mixed_provenance_and_expanded_allocation(defect):
    sample = fixture()
    if defect in ('source-before','source-after'):
        sample[defect.replace('-','_')]['src/palimpsest/__init__.py'] = 'c'*64
    elif defect == 'initializer':
        freeze = json.loads(sample['execution_freeze_raw'])
        del freeze['sources']['src/palimpsest/__init__.py']
        sample['execution_freeze_raw'] = canonical(freeze)
        sample['expected_execution_freeze_sha256'] = sha(sample['execution_freeze_raw'])
    elif defect in ('runtime','upstream'):
        sample['runtime_observation']['device' if defect=='runtime' else 'upstream_sha256'] = 'cuda' if defect=='runtime' else 'c'*64
    elif defect in ('model-index','projection'):
        key = 'original_model_index_raw' if defect=='model-index' else 'collection_projection_raw'
        sample[key] += b' '
    elif defect == 'freeze-pin': sample['expected_execution_freeze_sha256'] = 'c'*64
    elif defect == 'noncanonical': sample['envelope_raw'] += b' '
    else:
        freeze = json.loads(sample['execution_freeze_raw'])
        if defect=='reordered': freeze['owners'][0],freeze['owners'][1] = freeze['owners'][1],freeze['owners'][0]
        elif defect in ('limit','limit-alias'): freeze['limits']['owner_bytes'] = 161*MiB if defect=='limit' else float(160*MiB)
        elif defect=='held-out': freeze['owners'][0]['scene_id'] = 6200
        else: freeze['held_out_path'] = '/held-out'
        sample['execution_freeze_raw'] = canonical(freeze)
        sample['expected_execution_freeze_sha256'] = sha(sample['execution_freeze_raw'])
        envelope = json.loads(sample['envelope_raw'])
        envelope['execution_freeze_sha256'] = sample['expected_execution_freeze_sha256']
        sample['envelope_raw'] = canonical(envelope)
    with pytest.raises(ValueError): admit(sample)
