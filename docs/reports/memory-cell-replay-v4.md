# Actual recurrent-cell replay source evidence

The new compact consumer invokes the actual guarded upstream FLYNN cell directly
from retained encoded inputs. It bypasses retina processing, observation
construction, Agent.step and the Engine. Every raw output and upstream-mapped
float32 action must match bit-for-bit. Velocity uses Torch `tanh(raw) * 3` and
heading uses `pi * tanh(raw)`; no sanitization or tolerance hides a difference.
Source replay starts at zero hidden and checks its final hidden against the
acquired source SNP. Conditions start at that acquired hidden; their computed
final digest is not an independently verified endpoint.

The public consumer requires the pinned full-model manifest/provenance and actual
upstream agent/cell types, CPU float32, one thread, recorded runtime profile and
live graph/parameter equality with the source snapshot. It exhausts the strict
compact reader and holds prospective local behavior and three upstream source
descriptors through return. Supplied compact bytes and decoded snapshot state are
fingerprinted again. The caller must retain authenticated snapshot-file,
loaded-model asset and execution custody; this numerical consumer does not
establish those obligations or authorize an owner.

The temporary tiny graph/checkpoint tests use the actual pinned upstream cell and
guarded policy loader. Reference rows are recorded through FlynnPolicy.act, then
replayed through the direct cell seam. They cover source and condition starts,
wrong interior input/raw/action, multiplier-one regression, wrong state/weights/
graph/runtime, cursor/dtype/shape/nonfinite values, source endpoint and late
deadline/parameter/snapshot/output drift. Synthetic model pins are refused by the
public family consumer; no override manufactures original-model admission.

Observed RED `2bb6d98` failed at the missing replay module. The initial run also
collected 14 imported historical tests; fixture imports were narrowed to avoid
duplicate collection. Test-state fingerprinting initially passed Torch tensors
to the scientific NumPy hash API and was corrected in the test helper.
Independent review then reproduced actual guard mutation of the caller's original
diagnostics dictionary. RED `2cb3f81` retains the failing deep-content regression:
a prepend nonfinite hook runs before the real finite guard. Fix `1869954` uses
temporary replay diagnostics and restores the original object, contents, policy
state, raw references and alpha-cache state on success or failure. Independent
prepend NaN and wrong-shape cases verify the repair.

Final combined affected suite: **328 passed**, no skips, in **119.20 s**: 24 new
cell tests, 15 historical FLYNN tests and 289 compact/raw/source/pair/retained/
staged checks. Independent final review passed 41 focused checks in 2.29 s and
the two additional faithful guard-failure checks. All 21 local behavior pins,
three upstream file pins, fresh import without Torch/MuJoCo/Engine, compile and
diff checks pass. Tests reported 44 existing upstream/Torch warnings concerning
tensor-copy construction, sparse CSR beta support and TF32 API deprecation.
The full repository/native/asset-backed suites did not run in this source unit.

Runtime: Python 3.11.15 / NumPy 2.2.5 / Torch 2.9.0 on CPU, one thread. Upstream
HEAD is `8d964599119b420de67ee259434d273651a1a76d`. Prospective compact protocol
SHA is `cbdf034970963a847d42fabc879cc4596a99c8c1b58311561a6c678233e9c4fa`.
Reviewed implementation SHA is
`3ec5b8bc41f22e14118b024aeada0612c7e0694a6777ffc9c1825c88e107c4ac`;
test SHA is `32115e1f4ca35f4f35a13b9a5fb799684d9d9a8a694cbfe2d6667e6835c0f442`.

No real FLYNN checkpoint, retained recording/SNP, native owner, family study,
held-out input or navigation attempt was opened or run. No evidence was pruned.
The cloned upstream source was pinned; numerical tests used generated temporary
graph/checkpoint data only. This proves source integration with the actual cell,
not full-model qualification, camera/renderer/physics/Engine replay or scientific
acceptance. Deadline checks detect overruns after calls; they are not preemption
or a timing bound. All protocol grants/qualification claims remain false. No
permanent evidence entry, snapshot or resource allowance is added.

Next: freeze and independently review bounded full-model replay qualification
with exact model/input/runtime custody, then bind its proof into condition/case
close within existing receipt and time/storage limits. Complete pruning,
namespace/allocation and native launcher admission remain required.
