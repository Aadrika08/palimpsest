"""Temporary authored inputs only; public original positive remains unqualified."""
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from test_puck_collection_admission import fixture as envelope_fixture
from test_puck_bundle_provenance import fixture as bundle_fixture


def module():
    name = 'palimpsest.puck_execution'
    assert importlib.util.find_spec(name) is not None, 'Held collection execution context absent'
    return importlib.import_module(name)


def raw(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def sha(value):
    return hashlib.sha256(value).hexdigest()


def write_role(root, payloads):
    root.mkdir(parents=True)
    entries=[]
    for name, payload in sorted(payloads.items()):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
        entries.append({'path':name,'size_bytes':len(payload),'sha256':sha(payload)})
    return {'root':str(root),'files':entries}


def fixture(root, ordinal=0):
    m=module(); e=envelope_fixture(ordinal); b=bundle_fixture(21+ordinal%3)
    source_payloads={name:('authored '+name).encode() for name in m.REQUIRED_SOURCES}
    roles={'sources':write_role(root/'source',source_payloads),
        'projection':write_role(root/'projection',{'collection.json':e['collection_projection_raw']}),
        'index':write_role(root/'index',{'models.json':e['original_model_index_raw']}),
        'bundle':write_role(root/'bundle',b['bundle_payloads']),
        'historical':write_role(root/'historical',b['historical_source_payloads']),
        'runtime':write_role(root/'runtime',{'python3.11':b'authored runtime; never executed'})}
    freeze=json.loads(e['execution_freeze_raw'])
    freeze['sources']={name:sha(value) for name,value in source_payloads.items()}
    for owner in freeze['owners']:owner['cwd']=roles['sources']['root']
    freeze_raw=raw(freeze)
    envelope=json.loads(e['envelope_raw'])
    envelope.update(execution_freeze_sha256=sha(freeze_raw),owner=freeze['owners'][ordinal],
                    sources_sha256=sha(raw(freeze['sources'])))
    roles['admission']=write_role(root/'admission',{'freeze.json':freeze_raw,'envelope.json':raw(envelope)})
    custody={'version':1,'kind':'puck-collection-custody-v1','owner_ordinal':ordinal,
        'execution_freeze_sha256':sha(freeze_raw),'roles':roles,
        'executable':False,'qualification_claims':[]}
    def admit(**values):
        from palimpsest.puck_bundle_provenance import _validate_lineage
        assert values['original_model_index_raw']==e['original_model_index_raw']
        return _validate_lineage(seed=values['seed'],bundle_payloads=values['bundle_payloads'],
            historical_source_payloads=values['historical_source_payloads'],
            expected_source_hashes=b['expected_source_hashes'],expected_collection_sha256='c'*64)
    return custody,admit


def context(root, ordinal=0):
    custody,admit=fixture(root,ordinal)
    return module()._HeldCollectionExecution(raw(custody),sha(raw(custody)),time.monotonic()+30,
        bundle_admitter=admit,runtime_pin=custody['roles']['runtime']['files'][0]),custody


@pytest.mark.parametrize('ordinal',range(12))
def test_held_context_binds_all_collection_owners_and_defensive_metadata(tmp_path,ordinal):
    execution,custody=context(tmp_path/'case',ordinal)
    with execution:
        value=execution.description
        assert value['owner']['scene_id']==6110+ordinal//3
        assert value['model']['seed']==21+ordinal%3
        assert value['executable'] is False
        value['owner']['model_seed']=999
        assert execution.description['owner']['model_seed']==21+ordinal%3
        execution.recheck()
    with pytest.raises(RuntimeError):execution.recheck()


@pytest.mark.parametrize('defect',['pin','ordinal-alias','ordinal-range','extra-role',
    'missing-role','unknown-size','runtime-cap','claims','grant','source-missing'])
def test_custody_admission_rejects_invalid_metadata_before_opening(tmp_path,defect):
    custody,admit=fixture(tmp_path/'case')
    if defect=='ordinal-alias':custody['owner_ordinal']=0.0
    elif defect=='ordinal-range':custody['owner_ordinal']=12
    elif defect=='extra-role':custody['roles']['extra']=custody['roles']['index']
    elif defect=='missing-role':del custody['roles']['runtime']
    elif defect=='unknown-size':custody['roles']['runtime']['files'][0]['size_bytes']=None
    elif defect=='runtime-cap':custody['roles']['runtime']['files'][0]['size_bytes']=32*1024**2+1
    elif defect=='claims':custody['qualification_claims']=['passed']
    elif defect=='grant':custody['executable']=True
    elif defect=='source-missing':custody['roles']['sources']['files'].pop()
    payload=raw(custody);expected='0'*64 if defect=='pin' else sha(payload)
    with pytest.raises((ValueError,RuntimeError)):
        with module()._HeldCollectionExecution(payload,expected,time.monotonic()+30,
                bundle_admitter=admit,runtime_pin={'path':'python3.11','size_bytes':32,
                    'sha256':sha(b'authored runtime; never executed')}):
            pytest.fail('Malformed custody entered')


@pytest.mark.parametrize('role',['sources','admission','projection','index','bundle','historical','runtime'])
def test_file_drift_after_admission_poison_and_close_every_role(tmp_path,role):
    execution,custody=context(tmp_path/'case')
    with pytest.raises((ValueError,RuntimeError)):
        with execution:
            entry=custody['roles'][role]['files'][0]
            path=Path(custody['roles'][role]['root'])/entry['path']
            path.write_bytes(path.read_bytes()+b'changed')
            execution.recheck()
    with pytest.raises(RuntimeError):execution.recheck()


def test_unregistered_source_or_bundle_entry_is_not_hidden_by_supplied_roster(tmp_path):
    for role,path in [('sources','src/palimpsest/extra.py'),('bundle','extra.json')]:
        execution,custody=context(tmp_path/role)
        extra=Path(custody['roles'][role]['root'])/path;extra.parent.mkdir(parents=True,exist_ok=True)
        extra.write_bytes(b'unregistered')
        with pytest.raises(ValueError):
            with execution:pytest.fail('Unregistered input entered')


@pytest.mark.parametrize('path',['src/palimpsest/__pycache__/stale.pyc',
    'upstream/fly-gym/new/unregistered.xml','scripts/new/deep/unregistered.py'])
def test_unregistered_transitive_source_and_bytecode_are_rejected(tmp_path,path):
    execution,custody=context(tmp_path/'case')
    extra=Path(custody['roles']['sources']['root'])/path
    extra.parent.mkdir(parents=True,exist_ok=True);extra.write_bytes(b'foreign source')
    with pytest.raises(ValueError):
        with execution:pytest.fail('Unregistered transitive code entered')


def test_non_code_upstream_readme_is_not_mistaken_for_executable_source(tmp_path):
    execution,custody=context(tmp_path/'case')
    path=Path(custody['roles']['sources']['root'])/'upstream/fly-gym/README.md'
    path.write_text('Authored non-executable upstream text')
    with execution:execution.recheck()


def test_public_context_cannot_bind_foreign_import_root_even_with_original_runtime_descriptor(tmp_path):
    custody,_=fixture(tmp_path/'case')
    custody['roles']['runtime']['files']=[copy.deepcopy(module().RUNTIME_PIN)]
    with pytest.raises(ValueError,match='source root'):
        module().HeldCollectionExecution(raw(custody),sha(raw(custody)),time.monotonic()+30)


def test_failed_body_does_not_bypass_final_custody_check(tmp_path):
    execution,custody=context(tmp_path/'case')
    with pytest.raises((RuntimeError,ValueError),match='changed|differ'):
        with execution:
            path=Path(custody['roles']['bundle']['root'])/'report.json'
            path.write_bytes(b'changed')
            raise LookupError('body failed')
    with pytest.raises(RuntimeError):execution.recheck()


def test_public_context_refuses_authored_runtime_without_original_binary_access(tmp_path):
    custody,_=fixture(tmp_path/'case')
    with pytest.raises(ValueError,match='runtime'):
        with module().HeldCollectionExecution(raw(custody),sha(raw(custody)),time.monotonic()+30):
            pytest.fail('Public runtime pin substituted')


def test_parameter_check_before_materialization_poisons_context(tmp_path):
    execution,_=context(tmp_path/'case')
    with pytest.raises(RuntimeError,match='failed'):
        with execution:
            with pytest.raises(RuntimeError,match='materialized'):execution.check_parameters()
            with pytest.raises(RuntimeError,match='failed'):execution.recheck()


@pytest.mark.parametrize('scenario',['model','parameter-drift','file-after-inference','wrong-goal',
    'second-model','training-mode','terminal'])
def test_actual_unchanged_cpu_model_and_interval_seam_on_authored_inputs(tmp_path,scenario):
    script=r'''
import sys
from pathlib import Path
import numpy as np
import torch
from test_puck_execution import context
from palimpsest import puck_model,puck_learning
execution,custody=context(Path(sys.argv[1]))
scenario=sys.argv[2]
verified=False
with execution:
    model=execution.materialize_original_model()
    execution.check_parameters()
    assert not model.training
    assert all(np.all(value.detach().numpy()==.125) for value in model.state_dict().values())
    if scenario=='second-model':
        try:execution.materialize_original_model()
        except RuntimeError:
            try:execution.recheck()
            except RuntimeError:verified=True
            else:raise AssertionError('Repeated construction did not poison context')
        else:raise AssertionError('Repeated model construction accepted')
    elif scenario in ('parameter-drift','training-mode'):
        if scenario=='training-mode':model.train()
        else:
            with torch.no_grad():model[0].bias[0]+=1
        try:execution.check_parameters()
        except ValueError:verified=True
        else:raise AssertionError('Changed parameter accepted')
    else:
        sensors=np.array([.55/14,0,1.55/14,0,0,0,0,0],np.float32)
        world={'time_s':0.,'rover_pose':[-1.05,-.5,0.], 'puck_xyz':[-.5,-.5,.062],
            'puck_velocity_xy':[0.,0.], 'goal_xy':execution.description['scene']['layout']['goal_xy']}
        capture={'native_state':b'authored','observation':sensors.copy(),'python_rng':[1],
            'numpy_rng':np.array([2],np.uint32),'torch_rng':b'authored','environment_rng':[3],
            'space_rng':{'action':[4],'observation':[5]}}
        if scenario=='wrong-goal':world['goal_xy']=[99.,99.]
        inferred=[]
        original=puck_model.predict
        def change(*args):
            answer=original(*args)
            inferred.append(True)
            if scenario=='file-after-inference':
                (Path(custody['roles']['bundle']['root'])/'checkpoint.npz').write_bytes(b'changed')
            return answer
        puck_model.predict=change
        try:
            staged=execution.stage_interval(sensors,world,'approach',puck_learning.initial_cursor(),
                terminal_reason='goal' if scenario=='terminal' else None,capture_query_state=lambda:capture)
        except (ValueError,RuntimeError):
            assert scenario!='model'
            assert len(inferred)==(1 if scenario=='file-after-inference' else 0)
            verified=True
        else:
            assert scenario=='model'
            assert staged['row']['action'].dtype==np.float64
            assert staged['row']['student_inputs'].shape==(9,)
            assert np.array_equal(staged['row']['action'],puck_model.predict(model,staged['row']['student_inputs']))
            verified=True
'''
    # Failed/poisoned contexts deliberately raise on nominal close.
    script="try:\n"+''.join('    '+line+'\n' for line in script.splitlines())+"except (ValueError,RuntimeError):\n    assert scenario!='model'\nassert verified\n"
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path/'case'),scenario],
        capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stderr
