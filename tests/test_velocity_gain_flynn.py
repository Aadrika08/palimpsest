"""Tiny authored FLYNN graph integration, never pretrained-model evidence."""
import contextlib
import io
import pytest

import test_flynn as legacy
from palimpsest.flynn import load_policy
from palimpsest.velocity_gain import VelocityGainPolicy


@pytest.fixture(scope='module')
def graph():
    if not legacy.HAS_ML:
        pytest.skip('Tiny FLYNN fixture requires simulation Python dependencies')
    legacy.FlynnTests.setUpClass()
    try:
        yield legacy.FlynnTests
    finally:
        legacy.FlynnTests.tearDownClass()


@pytest.mark.parametrize('gain',[1,.5,.75,1.25])
def test_actual_recurrent_retinal_state_and_snapshot_delegation(graph,gain):
    fixture = graph()
    fixture.setUp()
    with contextlib.redirect_stdout(io.StringIO()):
        reference = load_policy(legacy.REPO,graph.edge,graph.checkpoint,'cpu',seed=7)
    wrapped = VelocityGainPolicy(fixture.policy,gain)
    original = wrapped._state()
    actual = wrapped.act(fixture.obs,check_parity=False)
    expected = reference.act(fixture.obs,check_parity=False)
    np,torch = graph.np,graph.torch
    assert actual['action'][0] == expected['action'][0]*np.float32(gain)
    assert actual['action'][1:].tobytes() == expected['action'][1:].tobytes()
    assert actual['encoded_input'].tobytes() == expected['encoded_input'].tobytes()
    assert actual['raw_output'].tobytes() == expected['raw_output'].tobytes()
    assert torch.equal(wrapped.hidden,reference.hidden)
    for eye in ('state_vision_left','state_vision_right'):
        ours,theirs=getattr(wrapped.agent,eye),getattr(reference.agent,eye)
        assert set(ours)==set(theirs)
        assert all(torch.equal(ours[key],theirs[key]) for key in ours)
    wrapped._restore(original)
    assert torch.equal(fixture.policy.hidden,original[0])
    restored = original[0].clone()+1
    wrapped.hidden = restored
    assert fixture.policy.hidden is restored
    wrapped.reset()
    assert torch.count_nonzero(fixture.policy.hidden)==0
