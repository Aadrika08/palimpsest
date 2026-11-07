import pytest
from scripts import memory_family_source_runtime_vnext as owner


def test_role_rejects_foreign_before_engine_import():
    with pytest.raises(TypeError): owner.produce_source({},object())
    with pytest.raises(TypeError): owner._produce_authored_source({},object())


@pytest.mark.parametrize('kind,amount,totals,free,floor',[
    ('raw',1,dict(raw=512*1024**2-32768,snapshot=0,candidate=0,controls=0,atomic=0),2**40,0),
    ('snapshot',16*1024**2+1,dict(raw=0,snapshot=0,candidate=0,controls=0,atomic=0),2**40,0),
    ('raw',1,dict(raw=0,snapshot=0,candidate=0,controls=0,atomic=0),32769,1),
    ('snapshot',1,dict(raw=0,snapshot=16*1024**2,candidate=0,controls=0,atomic=0),2**40,0),
])
def test_fixed_write_admission_refuses_component_or_incoming_floor(kind,amount,totals,free,floor):
    with pytest.raises(ValueError): owner._admit_source_write({},totals,amount,kind,free,floor)


def test_free_floor_is_inclusive_after_incoming_and_report_reservation():
    totals=dict(raw=0,snapshot=0,candidate=0,controls=0,atomic=0)
    owner._admit_source_write({},totals,1,'raw',32770,1)


@pytest.mark.parametrize('operation',['manifest','event','chunk-event'])
def test_fix1_raw_leaf_admission_before_writer_publication(tmp_path,operation):
    from palimpsest.records import RunWriter
    from scripts import memory_family_source_records_vnext as wire
    import numpy as np
    class FixedTargetBudget:
        def check(self,size,*,path):
            if path.name in ('manifest.json','events.jsonl') or path.suffix=='.npz':
                owner._validate_raw_write_target(tmp_path/'recording',path,size)
    if operation=='manifest':
        with pytest.raises(ValueError): RunWriter(tmp_path/'recording',{'oversized':'x'*65536},preserve_failed=True,storage_budget=FixedTargetBudget())
        assert not (tmp_path/'recording/manifest.json').exists() and not (tmp_path/'recording/manifest.tmp').exists()
        return
    writer=RunWriter(tmp_path/'recording',{},preserve_failed=True,storage_budget=FixedTargetBudget())
    if operation=='chunk-event': writer.tick(0,0,action=np.zeros(2,dtype='<f4'))
    with (writer.path/'events.jsonl').open('r+b') as stream:
        stream.truncate(7*wire.MiB-1)
    before=(writer.path/'events.jsonl').stat().st_size
    try:
        with pytest.raises(ValueError):
            if operation=='event': writer.event('cannot-fit')
            else: writer.flush()
        assert (writer.path/'events.jsonl').stat().st_size==before
        assert not (writer.path/'chunks/000000.npz').exists() and not (writer.path/'chunks/000000.tmp').exists()
    finally: writer._broken=True; writer.close()


def test_fix1_default_recorder_budget_call_path_stays_legacy(tmp_path):
    from palimpsest.records import RunWriter
    import numpy as np
    calls=[]
    class Budget:
        def check(self,size,*,path): calls.append(path)
    writer=RunWriter(tmp_path/'recording',{},storage_budget=Budget())
    writer.event('authored'); writer.tick(0,0,action=np.zeros(2,dtype='<f4')); writer.finish({}); writer.close()
    assert calls and all(path==writer.path for path in calls)
