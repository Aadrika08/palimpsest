# CPU phase diagnostics: source verified, runtime still open

A stalled held CPU qualification can now retain bounded phase information on
stderr instead of only an empty worker log. Implementation `5ccde54d` changes
only the seeded bootstrap and fixed qualifier; test-first commit `54e85ada`
precedes it. [The source plan](../plans/puck-cpu-runtime-phase-trace-v1.md) keeps
this prerequisite tied to the real recorded/replayed/exported episode goal.

The validated CPU qualification-v3 descriptor selects 18 nominal checkpoints:
bootstrap/source/dependency readiness, entry invocation, before/after each fixed
import, entry return/snapshot readiness and final close. No new schema, flag,
environment, argv, namespace, loader or provider is introduced. Qualification-v1/v2
stay silent; older owners without the private optional hook retain their behavior.

The trace component permits at most 24 attempted writes / 16 KiB encoded bytes,
with bounded phase names. Ordinary telemetry failures and short writes permanently
disable it. Cancellation closes owned holders and propagates. Existing poison,
first-failure and reverse-close behavior remain; stdout is still one terminal
receipt after successful close. A final clock check follows the last marker.

Markers are diagnostic-only. Import return precedes version/guard acceptance,
and even all 18 markers can precede final deadline refusal and empty stdout.
The first marker follows registration parsing. This is not complete/authentic
trace or class-slot-binding proof, hard timing, or installed-runtime acceptance.
The trace cap does not cover unrelated vendor stderr or blocking-write latency.

## Verification and retained failures

Final disjoint authored validation passes **217 cases**:

| Batch | Result | Scope |
| --- | --- | --- |
| Private nearest/consumer suite | 214 passed in 119.86s | 21 new trace cases, bootstrap/legacy entries, dependency/native/missing-import checks and parent/auditor/observer contracts. |
| Persistent historical-publication integrations | 3 passed in 46.53s | Tiny authored05/06/07 packages/native images, legacy and current outcomes, separate audits and cleanup. |

Both outer commands returned 0 normally, with empty command stderr. These are
pytest-reported durations, not runtime timing qualifications. Earlier 52/85/86
and 13-case runs overlap the final set and are not added again. No installed
Torch/Pillow/MuJoCo, renderer, model or scientific allocation ran in this unit.

Genuine initial REDs retain 13 failures/two legacy passes, plus the separate
cancellation failure. Independent review found a nested-write latch bug; its
new case failed with `TRACE_LATCH_REARMED` before the one-way disable fix.
A later consumer run exposed three old-bootstrap/new-qualifier missing-hook
failures; capturing the optional diagnostic hook fixed that compatibility break
without changing import or admission behavior.

Other failed runs remain preserved. Green01 passed 80 cases and failed one when a legacy
environment-tamper test encountered the unchanged ancestor-identity guard first.
Consumers01 passed 127 and failed four, including the three hook failures and a tiny native
mapped-image refusal on persistent fixture storage. Final worker/native tests use
private namespace tmpfs; historical integrations explicitly require persistent
project paths. These passes do not identify a changed ancestor, establish Btrfs
causality, or qualify persistent installed-native handling. No guard was relaxed.

Independent source review and final small-log consistency review found no remaining
material source findings after the two corrections. The reviewer did not rerun
tests. Its current source pins match the implementation; root independently binds
those source files to Git in the retained byte verifier.

The [evidence index](puck-cpu-runtime-phase-trace-v1/evidence-index.json) retains
36 artifacts / 217,571 B / 11 empty files: three source/test capsules, all eleven
batch stdout/stderr pairs and root command/result records, exact pre-fix reentrant
source, three reviews, the terminal observation and reused verifier. Initial RED
test source evolved before later cases; do not assign those early runs to final
test bytes. Raw failure logs keep their original whitespace. Whitespace checking excludes
only those five immutable failure stdout logs. Archive/original and
frozen source-Git equality pass; after committing, also verify archive Git bytes.

## Next finite boundary

Actual 07 remains failed and consumed; its missing final receipts stay missing.
No 08 configuration, admission program or invocation is created here. Old parent,
auditor, observer, candidate D, configuration and freeze bytes are unchanged.
The changed qualifier is a fifth preparation-relative source path; existing 05–07
predicates remain strict and cannot admit this source epoch by implication.

Define and independently review the distinct diagnostic epoch, preserving the
remaining inputs, nineteen absences, staging identities and limits. Fresh full
byte/custody/resource admission must precede at most one separately frozen runtime
invocation and independent outcome audit. Runtime/operator/renderer admission,
one real recorded/replayed/exported episode and all seven release gates remain
open. Full-repository tests, CI and physical rover checks were not run.
