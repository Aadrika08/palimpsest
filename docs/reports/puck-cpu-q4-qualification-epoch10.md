# Q4 CPU qualification source epoch 10

Source commit `cbe48b339f4839ec4d2b5ef153d0dc0820be712e` adds explicit
allocation-v10 dispatch in the parent, observer and independent auditor. Only
validated epoch 10 selects nested qualification-v4/result-v2 with explicit
qualification_version=4. Parent helpers default to 3; old epochs 1–9 still select
q3. The independent auditor reconstructs both tags itself. Bootstrap and fixed
qualification entry remain byte-identical to PR #174.

No installed runtime, real actual 10 controls/admission/allocation, protected
inputs, CI or rover work was invoked. All seven simulation-release gates remain
open. This source path is the prerequisite to fresh separately reviewed controls
and data-only admission, then one admitted runtime invocation.

## Evidence

The test-first plan and tests were committed at `0cb3755`. Final regression
passed 732 cases in 122.64s, including 51 new cases. This is 732, not 783: the 51 new
cases also passed an earlier run. All old/new metadata, exact-five preparation
projection, candidate D/19-name policy, noncandidate inputs, aliases/limits,
observer exclusivity, helper defaults and mismatched tags are covered.

The complete tiny authored route passes parent→q4 worker→independent API and CLI
audits, with normal closure and all authority flags false. The actual q4 worker
registration and result carry 4. Targeted independent registration/result checks
reject q3 under 10; valid legacy 9 rejects q4. These targeted checks use the real
held reader and assert the specific gate messages; they are not a second full
allocation with rebound outer receipts. Optional guard-cost rows may be absent
without changing audit acceptance.

Forty retained authored files total 255,291 bytes: current worker capsule, source/
dependency controls, logs, parent result, original preparation anchors, transport
and API/CLI/no-cost audit receipts. All 136 validation source copies match their
command pins. See [outcome](../plans/puck-cpu-q4-qualification-epoch10/outcome.json)
and [validation notes](../plans/puck-cpu-q4-qualification-epoch10/validation-notes.json).

The first mixed batch had an incorrect integration basetemp; the second still
selected copied epoch 9 numeric identities while reading output 10. Both fixture
mistakes are retained. After correction, integration-red03 reached the intended
unsupported-epoch 10 refusal before any production edit. Metadata RED likewise
proved the missing 10/new-helper behavior. These were authored fixtures, not
retries of consumed real attempts.

## Boundaries and next action

The fixture uses 18 missing names and 128 MiB resource floors; production still
requires 19 names and 2 GiB, with its unchanged 180s normal limit. Candidate D,
original preparation anchors, source/input schemas, environment and output/
cleanup conditions are unchanged. Hostile-code, atomicity, installed performance,
physics, renderer, inference or scientific qualification does not follow.

After independent source review/publication: create a distinct fresh control
packet from the fixed source, preserve consumed 01–09 evidence and all historical
missing receipts, review exact controls, then perform fresh full byte/custody/
resource admission. Only after those checks may actual 10 be invoked once. The
product exit remains one real recorded/snapshotted/replayed/exported public
episode after runtime and separate operator/renderer qualification.
## Independent review and archive

The fresh [whole-branch review](../plans/puck-cpu-q4-qualification-epoch10/whole-branch-review.json)
found no critical or important findings. One cosmetic issue remains: existing
zero-prefix error labels render epoch 10 as 010; numeric identities, paths and
refusal behavior are correct. Source bytes stay unchanged.

The sealed packet contains 242 artifacts / 3,373,267 bytes / eight empty files,
including 38 final source paths. Its verifier passes against retained originals
and source Git. The forty authored witnesses are selected evidence, not a complete
portable rerunnable fixture/staging tree. The index SHA-256 is `501c202b7ea2bda918fb0b55c8eac09eeba7b759f101f0d70e8dfddab13602e7`.
