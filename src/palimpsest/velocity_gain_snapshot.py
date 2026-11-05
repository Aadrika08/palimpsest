"""Pure, externally bound gain-only derivation; ordinary restore stays strict."""
import copy
import re

from . import snapshots
from .velocity_gain import RATIOS, SCHEMA, _canonical


def derive_gain_snapshot(snapshot, gain, *, expected_snapshot_sha256):
    """Keep complete state, changing one declared baseline action parameter.

    The digest must come from the registered original snapshot, not a discovered
    candidate. This is an identity derivation, not native snapshot validation,
    actual restoration evidence, or permission to replace the controller.
    """
    if (type(expected_snapshot_sha256) is not str
            or re.fullmatch('[0-9a-f]{64}', expected_snapshot_sha256) is None):
        raise ValueError('An externally expected original state digest is required')
    if type(gain) not in (int, float) or gain not in RATIOS:
        raise ValueError('Unregistered velocity gain')
    if type(snapshot) is not dict or set(snapshot) != snapshots.SNAPSHOT_KEYS:
        raise ValueError('Incomplete original snapshot')
    original = copy.deepcopy(snapshot)
    if snapshots.state_digest(original) != expected_snapshot_sha256:
        raise ValueError('Original snapshot identity differs')
    try:
        identity = original['identity']['policy']
        provenance = identity['provenance']
        ratio = provenance['velocity_gain']
        valid = (type(identity) is dict and set(identity) == {'class','device','dtype','provenance'}
            and identity['class'] == 'palimpsest.velocity_gain.VelocityGainPolicy'
            and identity['device'] == 'cpu' and identity['dtype'] == 'torch.float32'
            and type(provenance) is dict
            and set(provenance) == {'schema','base_policy_class','base_policy_provenance','velocity_gain'}
            and provenance['schema'] == SCHEMA
            and provenance['base_policy_class'] == 'palimpsest.flynn.FlynnPolicy'
            and type(provenance['base_policy_provenance']) is dict
            and type(ratio) is dict and set(ratio) == {'numerator','denominator'}
            and type(ratio['numerator']) is int and type(ratio['denominator']) is int
            and ratio == {'numerator':1,'denominator':1})
    except (TypeError, KeyError):
        valid = False
    if not valid:
        raise ValueError('Expected a registered CPU float32 baseline gain-one identity')
    _canonical(provenance)
    numerator, denominator = RATIOS[float(gain)]
    derived = copy.deepcopy(original)
    derived['identity']['policy']['provenance']['velocity_gain'] = {
        'numerator': numerator, 'denominator': denominator}
    receipt = {'schema': 'flynn-velocity-gain-snapshot-derivation-v1',
        'source_state_sha256': expected_snapshot_sha256,
        'derived_state_sha256': snapshots.state_digest(derived),
        'changed_paths': ([] if (numerator, denominator) == (1, 1)
                          else ['identity.policy.provenance.velocity_gain']),
        'source_gain': {'numerator':1,'denominator':1},
        'destination_gain': {'numerator':numerator,'denominator':denominator},
        'runtime_restoration_verified': False, 'sampling_eligibility_verified': False,
        'certified_improvement': False}
    return {'snapshot': derived, 'receipt': receipt}
