# Source vertical slice: independent source/spec review

2026-11-06. Reviewed the 130-line contract, including its final private replay-seam proposal,
and adopted `source-authority-next-action-review.md`, then the named source implementations.
Source/docs only; root-supplied b7a967026d1261b20450024e271f7cfc790dfd17 was not independently
checked. No imports, tests, execution, payload reads/hashes, HEAD/dependency/service/CI/native
inspection or git changes. Only this report written. Existing implementation changes underway
elsewhere are not reviewed or claimed tested here.

## Verdict

**NO: not yet implementation-ready under the exact frozen requirements and ownership list.**
The six adopted decisions are implementable. Keep the substantive conditional workload,
genuine RuntimeHandle/HeldReplayFiles, shared canonical Engine owner and independent numerical
qualifier. Fix the following six bounded engineering items; none requires a new user policy
decision, fabricated authority, prior Q, weaker custody or an always-refusing substitute.

## 1. Preserve errors where they originate, not only in the parent ExitStack

The contract requires every body/teardown exception as an ordered structured group. Existing
holders drain resources but discard information before a parent can recover it:

- `memory_source_runtime_closure_v1.py:609–620`: RuntimeHandle._release retains only its first
  holder-close error. `_poison` and enter/recheck/exit paths can replace the triggering error.
- Its `_SourceNamespaceFiles` inherits `puck_execution_files.py:116–130`: _close retains only
  the first OSError, and a non-OSError BaseException interrupts the remaining FD drain.
- `memory_family_replay_custody_v4.py:113–133` retains later FD errors as text notes; its
  __exit__ likewise turns exit-recheck failures into notes. Those are not original exceptions.
- `engine.py:1725–1765`: close uses `error or caught`; independent pending-command and
  environment failures can be discarded. Renderer/env finally nesting and writer.close can
  replace earlier failures. `Engine.open` failure cleanup at :533–548 has nested replacement
  paths before an Engine is returned. A wrapper around Engine.close cannot repair these.
- `records.py:345–361`: close's nested finally can replace flush/stop errors with events-close
  errors. Preserve this only on the new source preservation path; do not redesign recording.

Minimum amendment: authorize narrow source-specific structured-error behavior in the two
custody modules, canonical Engine open/close paths and preservation-enabled RunWriter close.
Use explicit ordered collection plus BaseExceptionGroup; keep ordinary legacy defaults.
In the runtime module override `_SourceNamespaceFiles._close` locally rather than editing
the shared Puck core. Ensure its inherited enter/recheck poison paths cannot lose the triggering
error either. Give RuntimeHandle and HeldReplayFiles an exact-bool source preservation opt-in,
default false, selected only by the fixed new parent. Do not expose callbacks or foreign handles.
Drain all FDs/contexts even for BaseException, mark inactive before release, retain the original
body first, then ordered teardown failures. Parent aggregates nested groups without duplicating
the same exception. Explicitly own focused authored compatibility tests for these extra files.
The already approved save_snapshot/RunWriter partial-file flag remains necessary and separate;
retaining bytes does not prove error preservation or successful teardown.

## 2. Approve the private per-row hook, including exceptional exits

**Approve the proposed `_replay_rows(..., custody_check=None)` seam in principle.**
`memory_family_cell_replay_v4.py:51–129` only checks time within its row loop. Whole-call checks
miss row-time custody mutations, and separate source calls reset hidden state each time.
Keep None legacy behavior; the new qualifier alone creates the checker, and no public entry,
job or serialized record accepts one. Check before/after each core row and around the complete
operation, with lease/model/input identities held through restoration and release.
Amend exceptional-exit semantics: run the exit custody check even if the cell raises, preserve
that body plus check failure, and restore state, diagnostics and every cache independently
even if an earlier restoration step raises. The present finally starts with policy._restore;
if that raises, later attribute/cache restoration is skipped. Scope this strengthened path to
non-None internally supplied custody checking; do not duplicate the arithmetic or relax guards.
Add the named replay source/test files to the approved ownership list explicitly.

## 3. Freeze a namespace/directory adapter that actually meets the contract

`HeldReplayFiles` permits 512 leaves, 1 GiB per file, 2 GiB total (:17–19,59–90).
Its exact-subtree walk infers directories solely from leaves, rejects an empty subtree and
cannot represent extra declared empty directories. Namespace/closure schemas permit far larger
rosters and explicitly require empty-directory closure. Runtime's `_SourceNamespaceFiles` does
represent declared empty directories, but `_edge` (:506–507) intentionally checks only dev/ino/mode
for ancestors outside selected roots. It cannot alone meet this contract's full-stat ancestors.

Minimum amendment: name a private parent-owned full-stat directory/closure adapter, inside the
new parent file, which holds every registered directory and ancestor FD, verifies the exact
declared children including empty directories, and performs the same before/after edge checks.
Retain genuine RuntimeHandle for runtime leaves and genuine HeldReplayFiles for other bounded
leaf batches. Batching must not apply an exact-subtree check to an incomplete batch; the complete
directory adapter owns that check. Explicitly cap non-runtime leaf sizes to the genuine holder's
1 GiB limit or name the genuine bounded current-byte holder for larger declared files.
Maintain one path/inode registry across runtime and additional holders: repeated equal references
reuse their owner, while conflicting descriptors and different paths to one inode fail.
Attach full-stat supplemental ancestor custody to runtime roots as well. Never change old
ancestor checks to edge-only or treat two independently authorized namespaces as one export.

## 4. Correct the prospective output roster bound

Section 7 reserves concrete final and pending leaf paths, but J.output_roster allows only 256
Slots and Slot has no variable-family syntax. At P=38, final raw/report/owner/SNP leaves=43,
numeric leaves=83, controls/future/failure leaves=43: 169 total. Raw temporary reservations add
39, numeric pending reservations add83: **291 before metadata/control pending reservations**.
Minimum amendment: raise J.output_roster to 512 and enumerate all concrete prospective names
using the fixed 38-partition ceiling. Validate the resulting canonical J byte/node caps; no
wildcard Slot or unnamed writable headroom. Actual inventories still contain only actual leaves.
This changes a roster cardinality, not the 640 MiB physical allocation or any permission.

## 5. Define the fixed asynchronous producer-control rendezvous

run_attempt is synchronous and receives only two byte arguments; ControlSupervisor is supplied
by an independent external observer after the producer segment closes, before E. Freeze that
handoff explicitly so it neither waits for run_attempt's return nor invents observation.
Minimum amendment: the enclosing observer owns only the precreated producer supervisor/stdout/
stderr slots; parent owns cleanup. Name the existing owner intent and closed worker-report as
the producer segment's start/completion signals, with observer timestamps independently
recorded and bound to this attempt/job. Parent performs a bounded fixed-path readiness wait
under the remaining outer deadline, then holds and validates the three closed observer files
and cleanup before A/E. No callback, subprocess, provider selector or mutable accepted flag.
No input hold of that producer branch occurs while observer publication can still mutate it.
Missing/invalid controls fail the attempt; they are not a pre-producer prerequisite that makes
their own production impossible. This is an external-observer precondition, not a built backend.

## 6. Define truthful model closure and authored numerical evidence

FlynnPolicy has _state/_restore (`flynn.py:193–196`) but no close API. Neither Engine.close nor
dropping one local variable establishes that a model/native runtime has been unloaded.
Minimum amendment: define `Replay.policy_closed` as release of all source-owned policy/model/
cache/diagnostic references after verified replay restoration, including audit_policy's bound
closure (`memory_decision_pilot.py:532–545`). Name the owner cleanup operation and observable
postcondition; keep native/process lifetime closure an external obligation. Do not call an
imaginary policy.close or set policy_closed merely because Engine.close returned.
Keep separate actual and authored guard paths. A real tiny Flynn/upstream cell exercises
numerics/restoration without full-model identity claims. A 4813-wide authored numerical vertical
must pin its own fixed fixture model/runtime facts and use the real core, never patch actual
identity guards to succeed. The contract's explicit fallback to writer/SNP/A/V/C plus qualifier
preload refusal and separate tiny-core tests is truthful **partial delivery**, not full vertical
acceptance. Establish that positive authored fixture during implementation before claiming it.

## Sound parts to retain

- Job/J/P/authorization and A/E/V/C/Q references avoid self-hashes and Q-needs-Q; candidate Q
  remains unaccepted, and detached outcome follows actual input-stack drain.
- Shared Engine.open canonical mode is real (:346–515); original source application checks
  (`raw_audit_v4.py:459–494`) accept the source cursor/world semantics without old envelope reuse.
- Direct base16/companion3 dimensions match compact ROW_FIELDS (:35–52) and Engine.tick
  (:1186–1193): 19534+112=19646 bytes/row. Original pixels/events/SNP and all physical copies
  remain separately charged. The 964 KiB combined metadata sum and 8 MiB atomic subdivision
  are coherent; generic decoder maxima must never replace those admission checks.
- Precreating sibling phase directories and holding conversion only after V/C/log closure
  resolves the stated ancestor-mutation conflict without weakening full-stat custody.
- The additive preservation flag reaches synchronous :302 cleanup as well as background
  publication; no second serializer or source export/repair/delete path is needed.

After these explicit amendments, proceed with the six substantive modules and scoped authored
tests. This review proves neither runtime/native/full-model feasibility nor any passing test.
Actual CPU adoption, independent namespace exports, authenticated load/resources/capacity/GO,
external backend, accepted actual Q, source L, F/R, later conditions and the full study remain absent.
