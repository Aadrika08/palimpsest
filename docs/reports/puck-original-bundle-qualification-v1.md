# Original puck bundles: qualification attempt 01 passed

The single registered invocation on source
`2264ddd136021b882f372bad4c2c34ffecb79507` passed, and independent evidence audit
accepted that scoped result. All three original models (seeds 21,22,23) passed
the fixed byte-provenance facade, strict unchanged CPU model materialization and
one zero-input probe each. All **18 prescribed negatives** rejected. This
qualifies original-bundle admission/materialization only; learned manipulation,
collection execution, held-out and all seven release gates remain open.

The [lossless evidence index](puck-original-bundle-qualification-v1-attempt-01-evidence/index.json)
retains all seven original output files, 11,006 bytes, and a byte-identical
[freeze](puck-original-bundle-qualification-v1-attempt-01-evidence/execution-freeze.json).
Freeze SHA256:
`15e8c12ab7a744647f08be42387d5043a4ef966466c63b5b6917dfacae8e2c3c`.
No checkpoint or stored parameter payload is copied into the evidence bundle.
The allocation is consumed; this passing result does not grant another invocation.

## Observed execution and audit

- External `/usr/bin/time` recorded **1.86 seconds, exit 0**. Tool session 80681
  was observed terminal; the elapsed value is the external observer's measurement,
  not a delayed-poll wall upper bound or universal timing bound.
- The original supervisor completed with exit 0, no failure and no matching live
  group survivors. It recorded **1.759933 seconds** from reservation to observation;
  the terminal record reports **1.784745 seconds**. Original parent PID was 9;
  worker PID/process group was 13. Later PID scans from a different execution
  namespace were not used as cleanup proof.
- Sampled peak parent-plus-worker RSS was **581,300,224 bytes** at 0.05-second
  intervals, below the frozen 1 GiB stop threshold. This is sampled operational
  evidence, not a hard memory bound. Both retained logs are empty. The original
  output namespace contains seven regular single-link files, no extras or failure
  marker, and totals 11,006 bytes within the 16 MiB cap.
- Each model performed one CPU call: exactly **three total**. Six negatives per
  model rejected altered report/protocol/checkpoint, wrong seed, changed historical
  source and changed live parameters. Original parameter bytes were restored and
  rechecked. Zero native owners, physics steps, fitting, scene/registry opens,
  held-out access or GPU initialization occurred.
- Observed runtime was Python 3.11.15, NumPy 2.2.5, Torch 2.9.0, CPU, one thread,
  deterministic algorithms enabled and CUDA uninitialized. Parent and worker
  image identities matched the held original interpreter before bundle custody.
- Independent read-only audit held and stream-hashed all **115 inputs /
  23,995,828 bytes**, the exact freeze and all output records through final checks.
  All source/historical/original bundle/runtime hashes and regular single-link
  identities matched. Canonical control types, attempt/hash bindings, process
  identity receipts, clocks, limits and false claims passed.
- Using only stdlib ZIP/NPY metadata and raw stored array bytes, the auditor bound
  all **18 parameter hashes** to **17,304 original parameter bytes**. It checked
  the fixed zero-input hashes and struct-packed float64 action hashes, without
  importing NumPy/Torch, constructing models or performing additional inference.
  The audit added zero model calls and did not rerun the attempt.

The three zero-input responses are diagnostic probes; they are not rollout
outcomes, task scores or evidence of useful manipulation. Only the nine registered
report/protocol/checkpoint parts are covered; existing training logs and other
unconsumed files are outside whole-folder namespace qualification.

## Source and freeze verification

**288 affected tests passed in 26.13 seconds**, independently repeated as 288 in
26.18 seconds. This includes 34 runner checks, 34 operational-guard checks and
220 inherited custody/envelope/provenance/interval checks. Authored model positives
use the actual unchanged Torch MLP in isolated subprocesses on temporary arrays;
public original positives come only from the actual registered attempt above.
The nine historical source exports are byte-identical to producer Git commit
`82e2bd97b37832c2a7f84f6eda6a3eca98e02362` and its fixed provenance hashes.

Independent review approved exact source/freeze before invocation. Review fixes
bound running interpreter objects, held inputs through terminal fsync/final close,
and bounded metadata discovery. The original three-part facade correctly leaves
unconsumed historical training logs outside its supplied-byte contract. Legacy
loaders, protocol/index pins and native owner denial remain unchanged.
The broader repository/browser/native suites remain unqualified as recorded in
the [previous source report](puck-v3-execution-custody.md); no new broad-suite pass
is inferred from this focused source slice or qualification.

## Next required work

Bind these admitted original models into the complete collection execution path:
durable registry/scene/owner reservations, fresh-worker source/runtime/dependency
admission, exact invocation, lease/process/RSS/storage supervision and complete
native interval/owner/collection publication. Preserve four collection scenes,
twelve owners times 600 intervals and all unchanged study limits. Independently
review the exact execution allocation before collection. Memory amendment 02
still requires its separately requested approval. CI and physical rover excluded.
