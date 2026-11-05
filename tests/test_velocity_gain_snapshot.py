"""Pure authored snapshots; no native runtime or population claim."""
import copy
import numpy as np
import pytest
from palimpsest import snapshots
from palimpsest.velocity_gain_snapshot import derive_gain_snapshot


def fixture():
    value = {key: None for key in snapshots.SNAPSHOT_KEYS}
    value.update(native_data=b'authored native placeholder',
        policy={'hidden': np.array([[1., 2.]], dtype=np.float32)},
        rng={'torch': b'authored rng'}, application={'counter': 12},
        identity={'policy': {'class': 'palimpsest.velocity_gain.VelocityGainPolicy',
            'device': 'cpu', 'dtype': 'torch.float32', 'provenance': {
                'schema': 'flynn-velocity-gain-v1',
                'base_policy_class': 'palimpsest.flynn.FlynnPolicy',
                'base_policy_provenance': {'checkpoint_sha256': 'a' * 64},
                'velocity_gain': {'numerator': 1, 'denominator': 1}}}})
    return value


@pytest.mark.parametrize('gain,ratio', [(1,(1,1)),(.5,(1,2)),(.75,(3,4)),(1.25,(5,4))])
def test_exactly_gain_identity_changes_and_source_is_untouched(gain, ratio):
    original = fixture(); before = snapshots.state_digest(original)
    output = derive_gain_snapshot(original, gain, expected_snapshot_sha256=before)
    derived, receipt = output['snapshot'], output['receipt']
    p = derived['identity']['policy']['provenance']
    assert p['velocity_gain'] == dict(zip(('numerator','denominator'),ratio))
    reverted = copy.deepcopy(derived)
    reverted['identity']['policy']['provenance']['velocity_gain'] = {'numerator':1,'denominator':1}
    assert snapshots.state_digest(reverted) == before == snapshots.state_digest(original)
    assert receipt['source_state_sha256'] == before
    assert receipt['derived_state_sha256'] == snapshots.state_digest(derived)
    assert receipt['changed_paths'] == ([] if gain == 1 else ['identity.policy.provenance.velocity_gain'])
    assert receipt['runtime_restoration_verified'] is False
    derived['policy']['hidden'][0,0] = 99
    assert original['policy']['hidden'][0,0] == 1


@pytest.mark.parametrize('path,value', [
    (('identity','policy','class'),'palimpsest.flynn.FlynnPolicy'),
    (('identity','policy','device'),'cuda'),
    (('identity','policy','provenance','base_policy_class'),'arbitrary.Policy'),
    (('identity','policy','provenance','velocity_gain'),{'numerator':1,'denominator':2}),
    (('identity','policy','provenance','velocity_gain'),{'numerator':True,'denominator':1}),
])
def test_nonbaseline_and_unregistered_identities_refuse(path,value):
    original = fixture(); cursor = original
    for key in path[:-1]: cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(ValueError):
        derive_gain_snapshot(original,.5,expected_snapshot_sha256=snapshots.state_digest(original))


def test_unbound_mutated_or_incomplete_snapshot_refuses():
    original = fixture(); expected = snapshots.state_digest(original)
    original['rng']['torch'] = b'changed'
    with pytest.raises(ValueError):
        derive_gain_snapshot(original,.5,expected_snapshot_sha256=expected)
    original = fixture(); original.pop('observation')
    with pytest.raises(ValueError):
        derive_gain_snapshot(original,.5,expected_snapshot_sha256=snapshots.state_digest(original))


@pytest.mark.parametrize('gain',[True,0,.6,float('nan')])
def test_unregistered_gain_refuses(gain):
    original = fixture()
    with pytest.raises(ValueError):
        derive_gain_snapshot(original,gain,expected_snapshot_sha256=snapshots.state_digest(original))
