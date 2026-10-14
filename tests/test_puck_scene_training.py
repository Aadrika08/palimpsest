"""Source-shaped authored training metadata; no actual model bundles."""
import copy
import hashlib
import importlib
import importlib.util
import json
import pytest
from test_puck_scene_retained import training


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()+b'\n'


def sha(value): return hashlib.sha256(value if type(value) is bytes else raw(value)).hexdigest()


def report(status='failed'):
    protocol=training()
    return {'status':status,'training_completed':status=='completed','training_seed':21,
        'protocol_sha256':sha(protocol),'held_out_used':False,'qualification_claims':[],
        'finalization_errors':[],'elapsed_seconds_before_report_staging':1.0,
        'files':[{'path':'protocol.json','sha256':sha(protocol),'bytes':len(raw(protocol))}]}


def prepared():
    protocol=training()
    return {'status':'prepared','training_performed':False,'protocol':protocol,'protocol_sha256':sha(protocol)}


def index():
    return {'models':[{'seed':21,'directory':'seed-21','files':{
        'protocol.json':sha(training()), 'report.json':sha(report()), 'checkpoint.npz':'c'*64}}],
        'producer_commit':'a'*40,'qualification_claims':[]}


def parse(value,kind):
    name='palimpsest.puck_scene_training'
    assert importlib.util.find_spec(name), 'Training metadata codec missing'
    return importlib.import_module(name).parse_puck_training_document(raw(value),kind=kind)


@pytest.mark.parametrize('kind,builder',[('training_report',report),('prepared_training',prepared),('model_index',index)])
def test_typed_training_metadata_codec_preserves_bytes_and_no_authority(kind,builder):
    value=builder();before=copy.deepcopy(value);result=parse(value,kind)
    assert value==before
    assert result['document_kind']==kind and result['document_sha256']==sha(value)
    assert result['inventory_complete'] is False and result['executable'] is False
    assert result['qualification_claims']==[]
    assert all(mention['scene_id']!=21 for mention in result['mentions'])


def test_prepared_wrapper_preserves_only_embedded_training_scene_and_paths():
    result=parse(prepared(),'prepared_training')
    assert result['mentions']==[{'scene_id':6000,'split':'train','pointer':'/protocol/sources/0/seed','catalog_sha256':None}]
    assert [r['pointer'] for r in result['references']]==['/protocol/collection_report','/protocol/sources/0']


def test_training_report_ledger_binds_protocol_bytes_from_document_directory():
    result=parse(report(),'training_report')
    ref=result['references'][0]
    assert ref['kind']=='training_protocol' and ref['path']=='protocol.json'
    assert ref['path_base']=='document_directory' and ref['expected_model_seed']==21
    assert ref['size_bytes']==len(raw(training()))


def test_index_model_seeds_are_not_scene_mentions_and_paths_need_recorded_cwd():
    result=parse(index(),'model_index')
    assert result['mentions']==[]
    assert [(r['kind'],r['path']) for r in result['references']]==[
        ('training_protocol','seed-21/protocol.json'),('training_report','seed-21/report.json')]
    assert all(r['expected_model_seed']==21 for r in result['references'])


@pytest.mark.parametrize('status',['failed','running','completed'])
def test_failed_and_partial_training_reports_do_not_hide_scene_dependencies(status):
    value=report(status);value['files']=[]
    result=parse(value,'training_report')
    assert result['missing_pins']==['/files/protocol.json']
    assert result['references']==[]


@pytest.mark.parametrize('kind,builder',[('training_report',report),('prepared_training',prepared),('model_index',index)])
@pytest.mark.parametrize('hidden',[{'sceneIds':[6110]},{'layout':{'seed':6110}},{'world':{'goal_xy':[1.,2.]}}])
def test_training_families_reject_untyped_scene_aliases(kind,builder,hidden):
    value=builder();value['metadata']=hidden
    with pytest.raises(ValueError):parse(value,kind)


@pytest.mark.parametrize('defect',['alias','digest','bytes','path','duplicate','heldout','protocol-in-ledger'])
def test_training_report_rejects_conflicting_or_invalid_ledger(defect):
    value=report()
    if defect=='alias':value['training_seed']=True
    elif defect=='digest':value['files'][0]['sha256']='d'*64
    elif defect=='bytes':value['files'][0]['bytes']=True
    elif defect=='path':value['files'][0]['path']='../protocol.json'
    elif defect=='duplicate':value['files'].append(copy.deepcopy(value['files'][0]))
    elif defect=='heldout':value['held_out_used']=True
    else:value['files'][0]['path']='unexpected.json'
    with pytest.raises(ValueError):parse(value,'training_report')


@pytest.mark.parametrize('defect',['hash','performed','status','unknown-key','nested-seed'])
def test_prepared_wrapper_rejects_changed_proof_or_hidden_fields(defect):
    value=prepared()
    if defect=='hash':value['protocol_sha256']='d'*64
    elif defect=='performed':value['training_performed']=True
    elif defect=='status':value['status']='completed'
    elif defect=='unknown-key':value['scene_seed']=6110
    else:
        value['protocol']['metadata']={'sceneSeed':6110};value['protocol_sha256']=sha(value['protocol'])
    with pytest.raises(ValueError):parse(value,'prepared_training')


@pytest.mark.parametrize('defect',['seed','files','directory','duplicate-model','unknown-row','hidden-geometry'])
def test_model_index_requires_typed_unique_model_receipts(defect):
    value=index();row=value['models'][0]
    if defect=='seed':row['seed']=True
    elif defect=='files':row['files']['protocol.json']='invalid'
    elif defect=='directory':row['directory']='/absolute/seed-21'
    elif defect=='duplicate-model':value['models'].append(copy.deepcopy(row))
    elif defect=='unknown-row':row['scene_id']=6110
    else:value['world']={'goal_xy':[1.,2.]}
    with pytest.raises(ValueError):parse(value,'model_index')
