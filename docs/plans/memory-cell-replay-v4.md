# Memory compact recurrent-cell replay

Implement the first execution-goal unit from PR #115. Add
`scripts/memory_family_cell_replay_v4.py` with a production
`replay_compact_cell` consumer for the guarded actual `FlynnPolicy`, strict compact
bundle, independent raw receipt and authenticated decoded source SNP. Its caller
must keep model/source/input custody open throughout invocation; this function
does not grant admission, open protected assets, launch an owner or publish a
receipt. Integrating it into durable condition/case close and qualifying the
actual full-model input path remain required.

The function admits only the pinned CPU float32 FLYNN profile and actual upstream
agent/cell types. Compare live parameter and graph-buffer hashes to the acquired
snapshot and hold the prospective local behavior source files through return.
Compare snapshot runtime/provenance and exact recorded input shape (4813).
Require source rows start at zero and condition rows at the acquired source
boundary. Validate snapshot hidden/retina state via the existing snapshot staging
contract. Bind case, run, source reference and unchanged false claims.

Call `policy.agent.cell` directly with `(1,1,4813)` encoded inputs and exactly
`checkpoint_steps=False, store_sequence=False`; never rerun retina/observation,
Agent.step or the Engine. Compare every finite float32 raw output and upstream
Torch action bit-for-bit (velocity multiplier 3, heading multiplier pi).
Source starts zero hidden and must finish at the acquired source hidden exactly.
Condition starts that hidden; return its computed final hidden digest without
claiming independent endpoint validation. Recheck deadline/runtime/live immutable
tensors and supplied inputs through return. Preserve caller policy state,
diagnostics, hooks and alpha-cache state on success and failure.

Meaningful numerical tests use the real pinned upstream cell, a temporary tiny
graph/checkpoint and actual `FlynnPolicy.act` recording to derive independent
reference rows. Private dimension-general replay tests verify the real cell seam;
public family admission refuses these synthetic model pins. No synthetic original
positive or callback replacement. Exercise wrong interior input, raw/action,
initial hidden, final source hidden, graph/parameter identity, dtype/shape/tick,
nonfinite data, runtime and deadlines. Existing pure compact/pair/source tests
remain green. Imports stay lazy and no Engine or MuJoCo runs. These synthetic
checks cannot qualify real FLYNN replay or change pruning/allocation grants.

After independent source review, freeze a separate bounded real-model replay
qualification with exact input/model/runtime custody and retained no-retry failure
evidence. No permanent entry or resource allowance is added by this source unit.
