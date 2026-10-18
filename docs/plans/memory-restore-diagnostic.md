# Restore diagnosis, repair and fresh qualification

Approved in conversation on 4 October 2026. Parent `63c5f35`, draft PR #69;
branch `research/memory-restore-diagnostic`. Native inline execution, one final
independent review, incremental commits and a stacked draft PR. Repository-local
author Aadrika Maurya <aadrikamaurya@gmail.com>, publication as Aadrika08.
Main remains unchanged. CI is excluded.

## Goal and boundaries

Locate the state difference blocking memory qualification, make one
evidence-supported implementation fix if possible without changing the scientific
contract, and run one fresh qualification attempt after such a repair. Stop before
the paired pilot. Preserve the prior six passing prerequisite gates and failed
restore pair, historical ENOSPC recordings and all immutable evidence. No fitting,
navigation, puck, held-out, hardware or exhibition work.

## Task 1: state retention and independently registered diagnosis

Add opt-in repeat-state retention to the existing worker, disabled by default and
refused for other operations. Keep existing job/protocol formats and normalization.
Save the same captured post-state that supplied the worker digest, before engine
cleanup, as an immutable SNP. Retain checksum, component hashes and source receipt
IDs. Do not recapture, advance physics or change normalization. Existing initial
SNPs provide the initial state; compare their invariants under the existing rule.

Add `scripts/memory_restore_diagnostic.py` with `diagnose` and `qualify` modes,
using existing private job validation, bounded process supervision, storage
controls and raw auditors. Commit implementation, this contract and machine
registration before any native owner. Registration binds source/assets/history,
implementation, outputs, selected .25 m profile, prior inventory and budgets.

Copy the prior audited south-prefix SNP byte-for-byte into the new diagnostic
stage, preserving original lineage. Source run `2f1ac4fbae794737b174e6e1fc2a7541`;
SNP SHA256 `c839fae1fe3d981cf4b7073970f7eb06d5738f009d6cb23f249408fd227cf6bf`;
condition invariant `86fa2ebcee8305a1b39c779a9a52e7c844345142fdbc4fd19175584a695a8b78`;
profile `7faba0a56d129ea051d5c28a019964034b546923dbe49cedb3a605af84437ec3`.
The local snapshot lives under the retained recovery-study prerequisite run's
`snapshots/initial.snp`. Refuse mismatched checksum, invariant or compatibility;
do not migrate or regenerate the source to evade admission.

Launch exactly two sequential five-tick CPU FLYNN restore jobs, using existing
travel-feasibility restore-1/restore-2 specs. The diagnostic is exploratory, not
prerequisite gate evidence. Compare every non-timing control field, initial
invariants and complete normalized post-state components. Publish differing paths,
types, shapes and bounded value/byte differences. Opaque native-byte or decoded
field differences alone do not establish a causal explanation.

One diagnostic invocation: 900 s total from admission through readout, first
600 s for preparation/owners/cleanup and 300 s reserved for readout, no transfer.
Existing restore 150/160 s internal/external limits and 10 s cleanup reserve.
One CPU owner at a time; no automatic or manual retry. External wrapper 890 s,
TERM then KILL after 5 s. Existing 8 GiB phase cap, 10 GiB admission free space,
2 GiB continuing floor, 64 MiB headroom, 512 MiB recording /16 MiB SNP /1 MiB
log caps. Retained-source copying and checks count inside these budgets.

## Task 2: supported repair or explicit stop

Make a repair only when retained diagnostic data demonstrate an implementation
defect violating the existing contract. Add a regression reproducing the identified
discrepancy first; observe RED, make the smallest fix, then GREEN. Commit separately.
Do not remove differing components, add numerical tolerance, change normalization,
geometry or controller behavior to make hashes equal. If mismatch does not
reproduce, remains unlocalized, or requires changing the scientific contract,
stop with a diagnosis report and mark repair/qualification unattempted. No guessed
fix or repeated diagnostic invocation.

## Task 3: one fresh qualification after a supported repair

Freeze and prospectively register the repaired implementation and new source
identity. Use the already selected .25 m profile; no candidate reselection or
historical passing-run substitution. Run eight fresh prerequisites in existing
order: south-no-event, south-change, north-no-event, north-change, south-prefix,
north-prefix, restore-1, restore-2. Both restores start from the new south-prefix
SNP. Retain both post-states and independently require the existing invariant,
raw audit, exact non-timing trace and normalized full-state equality gates.

4,300 s preparation/prerequisites and 600 s cleanup/readout, 4,900 s total, no
allocation transfer; external wrapper 4,890 s with 5 s kill grace. Existing full
720/730, prefix 360/370, repeat 150/160 s internal/external limits and storage
rules remain. Stop at first gate/infrastructure failure. No retry or pilot.

## Task 4: testing, independent readout and publication

Tests cover default/opt-in worker capture of the exact digest input, copy integrity,
existing normalization, component differences, missing/corrupt final states,
allocated/started/unscored owners, deadlines and storage refusal. Run focused
snapshot/worker tests and the full local software suite before native qualification;
quote actual counts and skips. Test doubles are software evidence, not native proof.

Rehash indexed evidence, account for every allocated/started job, and verify exact
PID/starttime/PGID owners exited inside the invocation's namespace. Never recheck
those namespace-relative PIDs from an unrelated later shell. Record incomplete,
failed and unattempted dispositions without promoting missing/corrupt evidence.
Independent readout, source/history rechecks, copies, analysis and close receipts
must finish inside scientific deadlines. Prose, review and Git publication occur
after close and do not add native measurements.

Publish diagnosis, any repair rationale, fresh gate outcomes, resources and limits.
Compact metadata are exact checked copies; raw NPZ/SNP payloads remain local.
Git publication is not a self-contained replay bundle. All eight passing would
qualify this prerequisite milestone only; R2 benefit/pilot remain separate.

Obtain one independent final whole-branch review. Fix important documentary/software
issues with tests, preserving the executed implementation and original receipts;
never claim a later repair retroactively qualifies an earlier native run. Push the
stacked draft PR against `research/memory-travel-recovery-study`, no merge.
