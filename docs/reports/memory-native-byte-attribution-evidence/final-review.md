# Independent final branch review

Fresh-context reviewer `/root/native_attribution_final_review`, read-only.
Range `29b01b535d2e09f257f47811b7dbccbaf906b52c` through
`56b7a5580ec95cedf556014e066f2fe0b2db7282`.

## Verdict and findings

Ready for draft publication after one report correction. No blocking software
issue found. Critical: none. Minor: none.

**Important, report accuracy:** report line 103 said the focused/full software
checks execute no physics. The archived full-suite log includes
`PhysicsSnapshots::test_actual_physics_continues_with_stale_derived_cache_preserved`;
`tests/test_snapshots.py:37`, `:52`, and `:59` call real `mujoco.mj_step` on
synthetic fixtures. Limit no-physics to the new checks and offline readout;
describe full-suite simulator exercises as software validation.

Executor verified these source calls and the archived warning/log entries, and
corrected the report accordingly. This is an editorial correction, with no code
or executed-study change; no new prose-mirroring test or repeated full suite was
added. The registered readout still records zero physics steps. The exact RED
log's trailing whitespace is intentional evidence preservation.

## Strengths

- Exact round trips, unique contiguous eight-byte probes, exact restoration,
  complete differing-offset coverage, and exact right-payload equality after
  timer-only substitution establish the attribution. Unrelated state differences
  remain unexplained and prevent a successful attribution claim.
- Eligibility/ownership observations avoid reading unbacked AR contents. Reviewed
  MuJoCo 3.3.6 dual eligibility and conditional serialization support the actual
  model-specific interpretation.
- No-kind registrations retain the previous path. Unsupported versions, malformed
  probes, altered round trips, and failed close checks fail closed.
- Registration, commit history, execution and publication hashes support the
  prospective sequence. Full-state equality stays false; qualification stays empty.

## Independent verification

The permitted synthetic test file passed **14 in 0.96 s**. Registration and
analysis hashes match their receipts; all three archived drivers match current
source byte hashes. Repository status remained clean during review.

## Declined to judge

- Retained-payload truth by independent decoding/replay: expressly excluded.
- All 473 historical files' current integrity: preservation receipts inspected,
  without independently rehashing each historical file.
- Full-suite results by rerunning: archived 953 passed/24 skipped log inspected;
  only the allowed synthetic subset was repeated.
- Current owner liveness, fresh qualification, broader reproducibility and hardware
  behavior: outside scope and unsupported by this readout.

No scientific driver, retained-snapshot decoding, PID probe, cleanup, CI, network
publication or repository mutation was performed by the reviewer.

## Executor rulings

1. Preserve ignored workspace and consumed marker despite generic skill cleanup;
   immutable research evidence takes precedence. Cost if wrong: small disk use.
2. Accept the registered retained-pair audit and serialization proof without a
   second decoder replay by the reviewer. One bounded invocation was authorized.
   Cost if wrong: independent replication remains necessary before broader claims.
3. Accept the executor's post-close rehash of all 473 files, with the reviewer
   checking receipts rather than repeating the full inventory read. Cost if wrong:
   independent preservation verification remains absent.
4. Accept the archived full-suite execution and selected independent software
   checks; documentation-only changes do not justify another full run. Cost if
   wrong: a reviewer has not independently reproduced the full suite.
5. Keep historical cleanup separate from current liveness and leave qualification,
   broader reproducibility and physical gates open. Cost if wrong: later measured
   qualification remains necessary.

No deferred minors and no software fix pass required.
