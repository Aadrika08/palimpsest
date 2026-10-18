"""Authored byte fixtures only; no original checkpoint or native input opened."""
import copy
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).parents[1]
SOURCE_PATHS = ('scripts/train_puck.py', 'src/palimpsest/puck_model.py',
    'src/palimpsest/puck_learning.py', 'src/palimpsest/puck_profile.py',
    'src/palimpsest/artifacts.py', 'src/palimpsest/records.py',
    'src/palimpsest/storage.py', 'docs/plans/m6-puck-learning-v2.json',
    'docs/plans/m6-puck-pushing-protocol-v5.json')
SHAPES = {'0.weight':(32,9),'0.bias':(32,), '2.weight':(32,32),
          '2.bias':(32,), '4.weight':(2,32),'4.bias':(2,)}


def raw(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def adapter():
    name = 'palimpsest.puck_bundle_provenance'
    assert importlib.util.find_spec(name) is not None, 'Supplied-byte provenance adapter absent'
    return importlib.import_module(name)


def fixture(seed=21):
    sources = {path:('authored '+path).encode() for path in SOURCE_PATHS}
    task = {'learning':{'epochs':30,'architecture':[8,32,2]}}
    sources[SOURCE_PATHS[-1]] = raw(task)
    learning = {'task_protocol':{'path':SOURCE_PATHS[-1],'sha256':sha(sources[SOURCE_PATHS[-1]])},
                'teacher_source_sha256':sha(sources['src/palimpsest/puck_profile.py']),
                'learning':{'architecture':[9,32,32,2]},
                'action_arithmetic':{'scaling':'float64 before .4'}}
    sources[SOURCE_PATHS[-2]] = raw(learning)
    expected = {path:sha(value) for path,value in sources.items()}
    protocol = {'schema':'puck-training-v1','learning_protocol_sha256':expected[SOURCE_PATHS[-2]],
        'training_seed':seed,'learning':{'epochs':30,'architecture':[9,32,32,2]},
        'action_arithmetic':learning['action_arithmetic'],'source_hashes':expected,
        'collection_report':{'path':'/authored/collection.json','sha256':'c'*64},
        'held_out_used':False,'qualification_claims':[]}
    stream = io.BytesIO()
    np.savez(stream,**{name:np.full(shape,.125,np.float32) for name,shape in SHAPES.items()})
    payloads = {'protocol.json':raw(protocol),'checkpoint.npz':stream.getvalue()}
    report = {'status':'completed','training_completed':True,'training_seed':seed,
        'held_out_used':False,'qualification_claims':[],'finalization_errors':[],
        'protocol_sha256':sha(payloads['protocol.json']),'selected_epoch':2,
        'history':[{'epoch':i,'dev_loss':.5 if i == 1 else .25} for i in range(1,31)],
        'files':[{'path':name,'sha256':sha(value),'bytes':len(value)} for name,value in payloads.items()]}
    payloads['report.json'] = raw(report)
    return {'seed':seed,'bundle_payloads':payloads,'historical_source_payloads':sources,
            'expected_source_hashes':expected,'expected_collection_sha256':'c'*64}


def amend(sample, filename, mutate):
    before = sample['bundle_payloads'][filename]
    value = json.loads(sample['bundle_payloads'][filename]);mutate(value)
    sample['bundle_payloads'][filename] = raw(value)
    if filename == 'protocol.json' and sample['bundle_payloads'][filename] != before:
        report = json.loads(sample['bundle_payloads']['report.json'])
        report['protocol_sha256'] = sha(sample['bundle_payloads'][filename])
        report['files'][0].update(sha256=report['protocol_sha256'],bytes=len(sample['bundle_payloads'][filename]))
        sample['bundle_payloads']['report.json'] = raw(report)


@pytest.mark.process_isolated  # needs no torch, threads or children left by other tests (docs/testing.md)
@pytest.mark.parametrize('seed',[21,22,23])
def test_private_lineage_preserves_arrays_and_historical_identity_without_torch(seed):
    sample = fixture(seed);before = copy.deepcopy(sample)
    arrays, identity = adapter()._validate_lineage(**sample)
    assert identity['training_seed'] == seed
    assert identity['supervisor_source_sha256'] == sample['expected_source_hashes'][SOURCE_PATHS[2]]
    assert identity['checkpoint_sha256'] == sha(sample['bundle_payloads']['checkpoint.npz'])
    for name,shape in SHAPES.items():
        assert arrays[name].shape == shape
        assert arrays[name].dtype == np.float32
        assert np.all(arrays[name] == .125)
    arrays['0.bias'][0] = 7
    identity['historical_source_hashes']['src/palimpsest/puck_profile.py'] = 'changed'
    assert sample == before
    assert 'torch' not in sys.modules
    assert 'mujoco' not in sys.modules


@pytest.mark.parametrize('defect', ['failed','training-false','heldout','claims','finalization',
    'seed-alias','epoch-alias','selection-alias','selection-tie','history-short','negative-loss',
    'infinite-loss','ledger-bytes-alias','ledger-order','protocol-seed-alias','learning',
    'arithmetic','source-map','collection','protocol-heldout'])
def test_private_lineage_rejects_rebound_invalid_report_or_protocol(defect):
    sample = fixture()
    def mutate_report(r):
        if defect == 'failed': r['status']='failed'
        elif defect == 'training-false': r['training_completed']=False
        elif defect == 'heldout': r['held_out_used']=True
        elif defect == 'claims': r['qualification_claims']=['qualified']
        elif defect == 'finalization': r['finalization_errors']=['failed']
        elif defect == 'seed-alias': r['training_seed']=21.0
        elif defect == 'epoch-alias': r['history'][0]['epoch']=True
        elif defect == 'selection-alias': r['selected_epoch']=2.0
        elif defect == 'selection-tie': r['selected_epoch']=3
        elif defect == 'history-short': r['history'].pop()
        elif defect == 'negative-loss': r['history'][0]['dev_loss']=-1
        elif defect == 'infinite-loss': r['history'][0]['dev_loss']='Infinity'
        elif defect == 'ledger-bytes-alias': r['files'][0]['bytes']=float(r['files'][0]['bytes'])
        elif defect == 'ledger-order': r['files'].reverse()
    def mutate_protocol(p):
        if defect == 'protocol-seed-alias': p['training_seed']=21.0
        elif defect == 'learning': p['learning']['architecture']=[8,32,2]
        elif defect == 'arithmetic': p['action_arithmetic']={'scaling':'float32'}
        elif defect == 'source-map': p['source_hashes']['src/palimpsest/puck_profile.py']='0'*64
        elif defect == 'collection': p['collection_report']['sha256']='0'*64
        elif defect == 'protocol-heldout': p['held_out_used']=True
    amend(sample,'report.json',mutate_report)
    amend(sample,'protocol.json',mutate_protocol)
    with pytest.raises(ValueError): adapter()._validate_lineage(**sample)


@pytest.mark.parametrize('defect',['source-change','source-extra','source-missing','source-oversize',
    'bundle-extra','bundle-missing','report-duplicate','checkpoint-corrupt','checkpoint-oversize'])
def test_private_lineage_rejects_incomplete_or_unsafe_supplied_bytes(defect):
    sample = fixture()
    sources=sample['historical_source_payloads'];bundle=sample['bundle_payloads']
    if defect=='source-change':sources[SOURCE_PATHS[3]]+=b' '
    elif defect=='source-extra':sources['extra']=b''
    elif defect=='source-missing':del sources[SOURCE_PATHS[3]]
    elif defect=='source-oversize':sources[SOURCE_PATHS[3]]=b'x'*(1024**2+1)
    elif defect=='bundle-extra':bundle['extra']=b''
    elif defect=='bundle-missing':del bundle['checkpoint.npz']
    elif defect=='report-duplicate':bundle['report.json']=b'{"status":"completed","status":"failed"}'
    elif defect=='checkpoint-corrupt':bundle['checkpoint.npz']=b'broken'
    elif defect=='checkpoint-oversize':bundle['checkpoint.npz']=b'x'*(1024**2+1)
    with pytest.raises(ValueError):adapter()._validate_lineage(**sample)


@pytest.mark.parametrize('seed',[True,21.0,20,24])
def test_production_facade_refuses_seed_aliases_and_unknown_models(seed):
    sample=fixture()
    with pytest.raises(ValueError):adapter().admit_original_bundle_bytes(seed=seed,
        original_model_index_raw=(ROOT/'docs/plans/m6-puck-student-models-v1.json').read_bytes(),
        bundle_payloads=sample['bundle_payloads'],historical_source_payloads=sample['historical_source_payloads'])


def test_production_facade_rejects_authored_bundle_before_json_or_npz_decode():
    sample=fixture();sample['bundle_payloads']['report.json']=b'not JSON'
    with pytest.raises(ValueError,match='artifact pin'):
        adapter().admit_original_bundle_bytes(seed=21,
            original_model_index_raw=(ROOT/'docs/plans/m6-puck-student-models-v1.json').read_bytes(),
            bundle_payloads=sample['bundle_payloads'],historical_source_payloads=sample['historical_source_payloads'])


def test_production_facade_rejects_rewritten_index_without_any_pin_override():
    sample=fixture()
    index=json.loads((ROOT/'docs/plans/m6-puck-student-models-v1.json').read_bytes())
    index['models'][0]['files']={name:sha(value) for name,value in sample['bundle_payloads'].items()}
    with pytest.raises(ValueError,match='index'):
        adapter().admit_original_bundle_bytes(seed=21,original_model_index_raw=raw(index),
            bundle_payloads=sample['bundle_payloads'],historical_source_payloads=sample['historical_source_payloads'])


def test_private_lineage_rejects_unrepresentable_json_integer_loss():
    sample=fixture()
    amend(sample,'report.json',lambda report:report['history'][0].update(dev_loss=10**1000))
    with pytest.raises(ValueError):adapter()._validate_lineage(**sample)


@pytest.mark.parametrize('defect',['task-pin','teacher-pin','arithmetic-missing'])
def test_historical_source_links_cannot_be_changed_even_with_rebound_source_ledger(defect):
    sample=fixture()
    spec=json.loads(sample['historical_source_payloads'][SOURCE_PATHS[-2]])
    if defect=='task-pin':spec['task_protocol']['sha256']='0'*64
    elif defect=='teacher-pin':spec['teacher_source_sha256']='0'*64
    else:del spec['action_arithmetic']
    source=raw(spec);sample['historical_source_payloads'][SOURCE_PATHS[-2]]=source
    sample['expected_source_hashes'][SOURCE_PATHS[-2]]=sha(source)
    def update(protocol):
        protocol['source_hashes']=sample['expected_source_hashes']
        protocol['learning_protocol_sha256']=sha(source)
    amend(sample,'protocol.json',update)
    with pytest.raises(ValueError):adapter()._validate_lineage(**sample)


def test_bad_npz_is_rejected_after_its_report_ledger_is_rebound():
    sample=fixture();sample['bundle_payloads']['checkpoint.npz']=b'not a numeric archive'
    def update(report):
        report['files'][1].update(bytes=21,sha256=sha(sample['bundle_payloads']['checkpoint.npz']))
    amend(sample,'report.json',update)
    with pytest.raises(ValueError,match='checkpoint'):
        adapter()._validate_lineage(**sample)
