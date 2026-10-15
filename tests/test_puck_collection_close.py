"""Real disk close/reduction on authored rows; no original model or study."""
import importlib
import importlib.util
from pathlib import Path
import pytest
from test_puck_on_policy_native_interval import NativeIntervalTests
from palimpsest import puck_on_policy as p


def api():
    name='palimpsest.puck_collection_close'
    assert importlib.util.find_spec(name), 'Durable collection close API missing'
    return importlib.import_module(name)


def test_no_durable_owner_close_for_unfinished_prefix(tmp_path):
    module=api()
    fixture=NativeIntervalTests(methodName='runTest');fixture.setUp()
    try:
        writer=p.PuckIntervalWriter(fixture.path,max_bytes=2*1024**2)
        fixture.publish(writer)
        scene=scene_entry(0)
        with pytest.raises(ValueError,match='initial|layout|terminal'):
            module.close_owner_recording(tmp_path,owner=owner(0),scene=scene,
                recording_path=fixture.path,execution_freeze_sha256='a'*64,
                reservation_sha256='b'*64)
        assert not (tmp_path/'owner-terminal.json.admission.json').exists()
    finally:fixture.doCleanups()


def owner(ordinal):
    scene,seed=6110+ordinal//3,21+ordinal%3
    return {'ordinal':ordinal,'owner_id':f'collection-{scene}-seed-{seed}',
            'scene_id':scene,'model_seed':seed}


def scene_entry(slot):
    layout=p._row(6110+slot,slot)
    layout['split']=p.COLLECTION_SPLIT
    return {'scene_id':6110+slot,'slot':slot,'split':p.COLLECTION_SPLIT,
            **p.scene_candidate_identities(layout),'layout':layout}


@pytest.mark.parametrize('ordinal',[-1,True,12])
def test_invalid_fixed_owner_roster_refuses_before_data(tmp_path,ordinal):
    module=api()
    with pytest.raises(ValueError,match='ordinal'):
        module.close_owner_recording(tmp_path,owner={'ordinal':ordinal},scene=scene_entry(0),
            recording_path=tmp_path/'absent',execution_freeze_sha256='a'*64,reservation_sha256='b'*64)


def test_natural_episode_entry_exists_without_changing_historical_denial():
    module=api()
    assert callable(module.run_collection_episode)
    from scripts.verify_puck_mechanics import owner as historical
    with pytest.raises(ValueError,match='not qualified'):historical({'puck_on_policy':{}})
