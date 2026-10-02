# M6 puck mechanics v4 — teacher goals, replay admission failure

The single approved gate at `102084740589ea8e39e33f7979a52364c642d7e9`
**failed** at fixed-action replay admission. Both signed-approach analytical
teachers reached the unchanged puck goal, and all three four-tick native
continuations matched their source rows exactly. This is partial simulator
mechanics evidence; the full gate did not pass. No retry or source change
occurred during execution. [Earlier v3 evidence](m6-puck-mechanics-v3.md) remains
unchanged.

| Planned owner | Recorded ticks | Result |
| --- | ---: | --- |
| zero, seed 5990 | 120 | Passed; no puck XY motion or rover-puck contact |
| push-positive, seed 5991 | 120 | Passed; fixed positive push |
| push-negative, seed 5992 | 120 | Passed; reflected fixed push |
| teacher-positive, seed 5993 | 361 | Passed; `puck_goal`, final distance .159238796 m |
| teacher-negative, seed 5994 | 361 | Passed; `puck_goal`, final distance .169534687 m |
| continue-tick1 | 4 | Passed; exact source successors from completed tick 1 |
| continue-contact | 4 | Passed; exact source successors from completed tick 112 |
| continue-dwell | 4 | Passed; exact source successors from completed tick 352 |
| replay-actions | 0 | Failed before first control; mode type rejected |
| replay-policy | 0 | Not started |

Both teachers used 15 negative-velocity approach commands. The positive teacher
issued 238 moving, 102 turn-only and 21 stopped commands; the negative teacher
issued 236, 107 and 18 respectively. First positive contact was completed tick
112. Its first qualifying dwell was completed tick 352, followed by the unchanged
ten-tick success criterion at 361. Native continuation retained the carried
teacher mode and compared every recorded field's dtype, shape and bytes, including
task hashes. It does not establish policy replay, which was never started.

The exact failure is `ValueError: Fixed action replay has incompatible recorded
mode`. `packet` writes scalar `uint8` mode fields; `RunWriter` preserves that
schema, and `iter_ticks` indexes each stacked chunk into `numpy.uint8` scalars.
The actual values have shape `()`, dtype `uint8` and fixed code 0.
`action_for` nevertheless requires an `np.ndarray`, rejecting the valid scalar
before executing an action. The direct fixture supplied zero-dimensional arrays
and missed this reader boundary. The proposed narrow fix is `np.asarray` at that
boundary, preserving exact dtype, scalar shape and code checks, with a real
writer/reader roundtrip regression. It is not a teacher or physics change, and
does not turn this retained failure into a pass.

Outer supervision exited 1 after **54.292402173 s**; inner elapsed time was
**54.043675787 s**. All nine created owners restored callbacks and closed both
renderers. No forced signals, sampler errors, survivors or finalization errors
were reported. All 11 observed PID/start identities and nine owner groups were
independently absent; the native slot was explicitly released. All 81 source
hashes and each owner's full model hash stayed unchanged. The failed replay
record remains `running` with zero published rows; its failure is retained in
the owner and gate reports.

The [JSON index](m6-puck-mechanics-v4.json) pins controls, protocols, raw reports,
record manifests and audits. The local NumPy-only audit passed in **3.290 s**,
checking **1,094 rows**, 12 snapshot receipts and **122 indexed files /
139,043,624 bytes**. Root's independent audit passed in **3.033 s**, checking
the same rows, snapshots, identities and both 361-command teacher sequences.
Both audits reconstructed contact/task/mode outcomes and exact continuation
rows without importing MuJoCo or Torch or restoring native state. The actual
derivative owners restored native state; the three continuations then executed
their exact windows, while action replay failed before its first control.

Raw output is `runs/m6-puck-mechanics-v4-20261003/`; retained controls and local
audit are under `runs/m6-puck-mechanics-v4-prepared/`. The inner report SHA is
`a96f808c0fbd725ac690a5de8e7f7d2e5c0424f0b4549a581e665498a28d4c3b`;
the outer report SHA is
`68664434e692c665b47484df2cdb2f708b21a76a3cf655db6028db3c4c65aa0b`.

Teacher collection and training remain closed. The two development layouts do
not demonstrate a learned pushing capability, held-out performance or physical
contact behavior. A future learning contract must address teacher-mode
observability before any demonstration or training execution.
