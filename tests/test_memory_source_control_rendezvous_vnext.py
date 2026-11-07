import pytest
from scripts import memory_source_parent_entry_vnext as parent


def test_rendezvous_refuses_foreign_lease_before_wait():
    with pytest.raises(TypeError): parent._await_producer_controls({},object())


def test_exclusive_control_publication_consumes_pending_atomically(tmp_path):
    from scripts import memory_family_source_records_vnext as wire
    import uuid
    root=tmp_path/'attempt'; root.mkdir()
    job=dict(workspace_root=str(root),case=dict(case_id='authored'),source_run_id=str(uuid.uuid4()),schema=wire.record_schema('job',True),limits=wire.LIMITS.copy())
    for directory in wire.reserved_directories(job): (root/directory).mkdir(exist_ok=True)
    relative=f"output/controls/{job['source_run_id']}/producer/supervisor.json"
    roster={row['path']:row for row in wire.output_roster('authored',job['source_run_id'])}
    result=parent._publish_bytes(job,relative,b'{"authored":"publisher-unit-only"}',roster)
    assert (root/relative).read_bytes()==b'{"authored":"publisher-unit-only"}'
    assert not (root/(relative+'.pending')).exists()
    with pytest.raises(FileExistsError): parent._publish_bytes(job,relative,b'other',roster)
    assert result['size_bytes']==34


def test_control_min_free_admission_precedes_pending_allocation(tmp_path,monkeypatch):
    from scripts import memory_family_source_records_vnext as wire
    from types import SimpleNamespace
    import uuid
    root=tmp_path/'attempt'; root.mkdir()
    job=dict(workspace_root=str(root),case=dict(case_id='authored'),source_run_id=str(uuid.uuid4()),schema=wire.record_schema('job',True),limits=wire.LIMITS.copy())
    for directory in wire.reserved_directories(job): (root/directory).mkdir(exist_ok=True)
    relative=f"output/controls/{job['source_run_id']}/producer/stdout"
    roster={row['path']:row for row in wire.output_roster('authored',job['source_run_id'])}
    monkeypatch.setattr(parent.os,'statvfs',lambda path:SimpleNamespace(f_bavail=10,f_frsize=1))
    with pytest.raises(ValueError,match='before write'): parent._publish_bytes(job,relative,b'ab',roster,minimum_free_bytes=9)
    assert not (root/relative).exists() and not (root/(relative+'.pending')).exists()


@pytest.mark.parametrize('stage',['write','pending-fsync','parent-fsync'])
def test_fix1_publication_preserves_body_and_close_objects(tmp_path,monkeypatch,stage):
    import os,uuid
    from scripts import memory_family_source_records_vnext as wire
    root=tmp_path/'attempt'; root.mkdir(); run=str(uuid.uuid4())
    job=dict(workspace_root=str(root),case=dict(case_id='authored'),source_run_id=run,schema=wire.record_schema('job',True),limits=wire.LIMITS.copy())
    for directory in wire.reserved_directories(job): (root/directory).mkdir(exist_ok=True)
    relative=f'output/controls/{run}/producer/stdout'; roster={row['path']:row for row in wire.output_roster('authored',run)}
    body=KeyboardInterrupt('publication body'); closing=OSError('publication close'); real_write=os.write; real_fsync=os.fsync; real_close=os.close
    syncs=[]; closes=[]
    def write(fd,payload):
        if stage=='write': real_write(fd,payload[:1]); raise body
        return real_write(fd,payload)
    def fsync(fd):
        syncs.append(fd)
        if stage=='pending-fsync' or stage=='parent-fsync' and len(syncs)==2: raise body
        real_fsync(fd)
    def close(fd):
        closes.append(fd); real_close(fd)
        if stage!='parent-fsync' or len(closes)==2: raise closing
    monkeypatch.setattr(os,'write',write); monkeypatch.setattr(os,'fsync',fsync); monkeypatch.setattr(os,'close',close)
    with pytest.raises(BaseExceptionGroup) as caught: parent._publish_bytes(job,relative,b'authored',roster)
    assert caught.value.exceptions==(body,closing)
    assert len(closes)==(2 if stage=='parent-fsync' else 1)
    assert (root/(relative if stage=='parent-fsync' else relative+'.pending')).exists()


def test_fix1_failure_inventory_error_cannot_replace_primary(tmp_path,monkeypatch):
    import json,time,uuid
    from scripts import memory_family_source_records_vnext as wire
    job=dict(attempt_id=str(uuid.uuid4()),source_run_id=str(uuid.uuid4()),workspace_root=str(tmp_path),case=dict(case_id='authored'),readset={})
    raw=wire.encode(job); auth=dict(deadline_monotonic_ns=time.monotonic_ns()+10_000_000_000)
    lease=parent._AuthoredLiveInputLease(parent._AUTHORED_TOKEN,job=job,authorization=auth,job_bytes=raw,authorization_bytes=b'{}')
    primary=ValueError('body'); diagnostic=PermissionError('stat'); failures=[primary]
    def fail(*args,**kwargs): raise diagnostic
    monkeypatch.setattr(parent.os,'stat',fail)
    parent._failure(job,lease,failures,dict(capacity=dict(required_free_bytes=0)))
    assert failures==[primary,diagnostic]
