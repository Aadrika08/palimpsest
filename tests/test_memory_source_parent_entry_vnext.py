import pytest
from scripts import memory_source_parent_entry_vnext as parent


def test_entry_rejects_noncanonical_before_output():
    with pytest.raises(ValueError): parent.run_attempt(b'{}',b'{}')
    with pytest.raises(ValueError): parent._run_authored_attempt(b'{}',b'{}')


def test_private_leases_and_foreign_or_subclass_refusal():
    with pytest.raises((TypeError,ValueError)): parent._LiveInputLease(None)
    class Foreign: pass
    with pytest.raises(TypeError): parent._lease_kind(Foreign())


def test_real_authored_source_writer_snp_audit_codec_and_independent_cell(tmp_path,monkeypatch):
    from memory_source_vnext_fixture import build,observer
    fixture=build(tmp_path/'attempt',monkeypatch)
    thread,failures=observer(fixture)
    import sys
    audit_events=[]; audit_enabled=[True]
    def audit_event(event,args):
        if audit_enabled[0] and event in ('os.mkdir','os.rename','os.remove','os.link','os.rmdir'):
            selected=[str(item) for item in args if isinstance(item,(str,bytes))]
            if any(item.startswith('/var/tmp') for item in selected): audit_events.append((event,selected))
    sys.addaudithook(audit_event)
    try:
        result=parent._run_authored_attempt(fixture.job_bytes,fixture.authorization_bytes)
    finally:
        thread.join(timeout=12)
        audit_enabled[0]=False
        print('AUTHORED FILESYSTEM EVENTS',audit_events)
    assert not failures and not thread.is_alive()
    assert result['status']=='candidate-unaccepted'
    assert result['schema']=='memory-source-authored-attempt-outcome-vnext-v1'
    assert all(value is False for value in result['claims'].values())
    from scripts import memory_family_source_records_vnext as wire
    Q=wire.decode((fixture.root/result['qualification_candidate']['path']).read_bytes(),131072)
    assert Q['scope']=='software-unit-only'
    assert Q['replay']['input_width']==4813
    assert Q['replay']['rows_checked']>=1 and Q['replay']['policy_closed'] is True
    assert Q['replay']['final_hidden_sha256']==Q['replay']['source_hidden_sha256']
    assert Q['replay']['state_before_sha256']==Q['replay']['state_after_sha256']
    assert not list((fixture.root/'output').glob('**/acceptance.json'))
    assert not list((fixture.root/'output').glob('**/lifetime.json'))


@pytest.mark.parametrize('defect',['actual-entry','auth-fixture','output-extra','job-bool'])
def test_authority_domain_and_frozen_refusals_precede_runtime_or_output(tmp_path,monkeypatch,defect):
    from memory_source_vnext_fixture import build
    from scripts import memory_family_source_records_vnext as wire
    fixture=build(tmp_path/'attempt',monkeypatch)
    def forbidden(*args,**kwargs): raise AssertionError('Runtime payload opened before preflight refusal')
    monkeypatch.setattr(parent.RuntimeHandle,'__enter__',forbidden)
    entry=parent._run_authored_attempt
    if defect=='actual-entry': entry=parent.run_attempt
    elif defect=='auth-fixture':
        fixture.auth['fixture_id']='wrong-fixture'
        fixture.authorization_bytes=wire.encode(fixture.auth,262144)
        (fixture.root/'freeze/metadata/authorization.json').write_bytes(fixture.authorization_bytes)
    elif defect=='output-extra': (fixture.root/'output/extra').write_bytes(b'retained unexpected fixture')
    else:
        fixture.job['block']=False; fixture.job_bytes=wire.encode(fixture.job,262144)
    with pytest.raises(ValueError): entry(fixture.job_bytes,fixture.authorization_bytes)
    assert not list((fixture.root/'output').glob('**/owner.json'))
    assert not list((fixture.root/'output').glob('**/candidate.json'))


def test_real_owner_early_termination_retains_failure_prefix_without_completion(tmp_path,monkeypatch):
    from memory_source_vnext_fixture import build,observer,AuthoredEnvironment
    from scripts import memory_family_source_records_vnext as wire
    fixture=build(tmp_path/'attempt',monkeypatch)
    ordinary=AuthoredEnvironment.step
    def stalled(env,action):
        obs,reward,terminated,truncated,info=ordinary(env,action)
        return obs,reward,terminated,truncated,dict(info,stalled=True)
    monkeypatch.setattr(AuthoredEnvironment,'step',stalled)
    thread,failures=observer(fixture)
    try:
        with pytest.raises(BaseExceptionGroup): parent._run_authored_attempt(fixture.job_bytes,fixture.authorization_bytes)
    finally: thread.join(timeout=12)
    assert not failures and not thread.is_alive()
    base=fixture.root/f"output/.pending/{fixture.job['case']['case_id']}"
    assert (base/'source/owner.json').exists()
    assert not (base/f".raw/{fixture.job['source_run_id']}/worker-report.json").exists()
    assert not (base/'source/snapshots/initial.snp').exists()
    controls=fixture.root/f"output/controls/{fixture.job['source_run_id']}"
    assert not (controls/'qualifier/candidate.json').exists()
    assert not (controls/'final-accounting/outcome.json').exists()
    failure=wire.decode((controls/'failures/producer/failure.json').read_bytes(),32768)
    assert failure['status']=='failed-unqualified' and failure['phase']=='producer'
    assert failure['retained'] and all(value is False for value in failure['claims'].values())


@pytest.mark.parametrize('boundary',['owner','replay'])
@pytest.mark.parametrize('defect',['tensor','provenance','training'])
def test_fix1_loaded_tensor_mutation_refuses_next_operation_and_drains(tmp_path,monkeypatch,boundary,defect):
    from memory_source_vnext_fixture import build,observer,AuthoredEnvironment
    from palimpsest import flynn
    fixture=build(tmp_path/'attempt',monkeypatch); policies=[]; steps=[]; rows=[]; original_load=flynn.load_policy; original_step=AuthoredEnvironment.step
    def corrupt(policy):
        if defect=='tensor':
            with policy.torch.no_grad(): policy.agent.r_scale.add_(1)
        elif defect=='provenance': policy.provenance['authored_boundary_mutation']=True
        else: policy.agent.train(True)
    def load(*args,**kwargs):
        policy=original_load(*args,**kwargs); policies.append(policy)
        if boundary=='replay' and len(policies)==2:
            def mutate(cell,inputs,outputs):
                rows.append(1)
                corrupt(policy)
            policy.agent.cell.register_forward_hook(mutate)
        return policy
    def step(env,action):
        steps.append(1); result=original_step(env,action)
        if boundary=='owner':
            corrupt(policies[0])
        return result
    monkeypatch.setattr(flynn,'load_policy',load); monkeypatch.setattr(AuthoredEnvironment,'step',step)
    thread,failures=observer(fixture)
    try:
        with pytest.raises(BaseExceptionGroup): parent._run_authored_attempt(fixture.job_bytes,fixture.authorization_bytes)
    finally: thread.join(timeout=12)
    assert not failures and not thread.is_alive()
    assert len(steps)==1 if boundary=='owner' else len(rows)==1
    assert all('act' not in vars(policy) for policy in policies)
    controls=fixture.root/f"output/controls/{fixture.job['source_run_id']}"
    assert not (controls/'qualifier/candidate.json').exists() and not (controls/'final-accounting/outcome.json').exists()


def test_fix1_submit_mutation_refuses_advance_and_drains_pending_command(tmp_path,monkeypatch):
    from memory_source_vnext_fixture import build,observer
    from palimpsest.engine import Engine
    fixture=build(tmp_path/'attempt',monkeypatch); engines=[]; advances=[]
    submit=Engine.submit; advance=Engine.advance
    def mutated(engine,command):
        result=submit(engine,command); engines.append(engine)
        with engine.policy.torch.no_grad(): engine.policy.agent.r_scale.add_(1)
        return result
    def advanced(engine,*args,**kwargs):
        advances.append(1); return advance(engine,*args,**kwargs)
    monkeypatch.setattr(Engine,'submit',mutated); monkeypatch.setattr(Engine,'advance',advanced)
    thread,failures=observer(fixture)
    try:
        with pytest.raises(BaseExceptionGroup): parent._run_authored_attempt(fixture.job_bytes,fixture.authorization_bytes)
    finally: thread.join(timeout=12)
    assert not failures and not thread.is_alive()
    assert len(engines)==1 and advances==[]
    engine=engines[0]
    assert not engine._pending and engine._closed and engine.env.closed and engine.writer._events.closed
    assert engine.policy is engine.teacher is None
