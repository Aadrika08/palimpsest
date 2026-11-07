"""Genuine generated tiny Flynn/upstream-cell numerics, no production weights."""
import copy
import pytest
from test_memory_family_cell_replay_v4 import sample, request, policy_state_digest
from scripts import memory_family_cell_replay_v4 as replay


@pytest.fixture(scope='module')
def fixture_class(tmp_path_factory):
    import test_flynn
    directory=tmp_path_factory.mktemp('retained-tiny-model')
    class RetainedDirectory:
        def __init__(self,*args,**kwargs): self.name=str(directory)
        def cleanup(self): pass
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(test_flynn.tempfile,'TemporaryDirectory',RetainedDirectory)
        test_flynn.FlynnTests.setUpClass()
    yield test_flynn.FlynnTests
    # Fixture artifacts deliberately retained; no cleanup/native state claims.


def test_single_trace_checks_every_row_and_restoration(sample):
    calls=[]; policy=sample['policy']; before=policy_state_digest(policy)
    result=replay._replay_rows(**request(sample), custody_check=lambda: calls.append(policy_state_digest(policy)))
    assert result['rows_checked']==3 and result['source_endpoint_verified']
    assert len(calls)>=11
    assert policy_state_digest(policy)==before


def test_custody_body_failure_still_restores_and_final_checks(sample):
    policy=sample['policy']; before=policy_state_digest(policy); calls=[]
    body=KeyboardInterrupt('row custody'); tail=OSError('exit custody')
    def check():
        calls.append(1)
        if len(calls)==4: raise body
        if len(calls)==5: raise tail
    with pytest.raises(BaseExceptionGroup) as caught:
        replay._replay_rows(**request(sample),custody_check=check)
    from test_memory_source_structured_teardown_vnext import flatten
    assert flatten(caught.value)==[body,tail]
    assert len(calls)>=6
    assert policy_state_digest(policy)==before


def test_bad_custody_callable_refuses_before_mutation(sample):
    before=policy_state_digest(sample['policy'])
    with pytest.raises(ValueError): replay._replay_rows(**request(sample),custody_check=True)
    assert policy_state_digest(sample['policy'])==before


def test_legacy_none_core_still_computes_whole_trace_and_restores(sample):
    policy=sample['policy']; before=policy_state_digest(policy)
    result=replay._replay_rows(**request(sample))
    assert result['rows_checked']==3 and result['source_endpoint_verified']
    assert policy_state_digest(policy)==before
    wrong=request(sample); wrong['rows']=copy.deepcopy(wrong['rows']); wrong['rows'][1]['raw_output']+=1
    with pytest.raises(ValueError,match='raw output'): replay._replay_rows(**wrong)
    assert policy_state_digest(policy)==before
