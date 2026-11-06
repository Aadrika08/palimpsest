from types import SimpleNamespace
import pytest
from scripts.memory_family_source_runtime_vnext import _OwnedPolicyReferences, _release_source_owned_policy_refs


def test_release_detaches_audit_and_clears_all_owned_references():
    class Policy:
        def act(self): return 'class'
    policy = Policy(); cell = SimpleNamespace(_cached_alphas=object(), _alphas_dirty=False)
    policy.agent = SimpleNamespace(cell=cell)
    policy._raw = object(); policy._encoded = object(); policy._current_raw_output = object()
    refs = _OwnedPolicyReferences(); engine = SimpleNamespace(policy=policy, teacher=object())
    refs.engine = engine; refs.policy = policy; refs.agent = policy.agent
    refs.custody_check = lambda: engine
    policy.act = lambda: engine
    _release_source_owned_policy_refs(refs)
    assert policy.act() == 'class'
    assert engine.policy is engine.teacher is None
    assert cell._cached_alphas is None and cell._alphas_dirty
    assert all(getattr(refs, name) is None for name in refs.__slots__ if name != 'audit_act_had_instance_value')
    assert refs.audit_act_had_instance_value is False


def test_release_restores_original_instance_act_and_drains_despite_error():
    class Policy:
        def __setattr__(self,name,value):
            if name=='_raw' and getattr(self,'reject_raw',False): raise KeyboardInterrupt('raw release')
            object.__setattr__(self,name,value)
    original=lambda: 'original'; policy=Policy(); policy.act=lambda:'audit'; policy._raw=object(); policy.reject_raw=True
    policy.agent=SimpleNamespace(cell=SimpleNamespace(_cached_alphas=object(),_alphas_dirty=False))
    refs=_OwnedPolicyReferences(); refs.policy=policy; refs.agent=policy.agent; refs.engine=SimpleNamespace(policy=policy,teacher=object())
    refs.audit_act_had_instance_value=True; refs.audit_act_original_value=original; engine=refs.engine
    with pytest.raises(BaseExceptionGroup): _release_source_owned_policy_refs(refs)
    assert policy.act is original and engine.policy is engine.teacher is None
    assert all(getattr(refs,name) is None for name in refs.__slots__ if name!='audit_act_had_instance_value')
    assert policy.agent.cell._cached_alphas is None
