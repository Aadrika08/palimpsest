# Memory terminal attribution: exit lost during travel

8 October 2026. The first bounded unit of the
[renewed simulation goal](../plans/simulation-completion-next-goal.md) completed
once. **The recorded local-null/own failure is attributable to field of view.**
This is an explanation of a retained observation, not a repaired controller,
successful memory study or physical qualification.

## What happened

The selected route-z exit was visible when selected at tick 864. It remained
selected for 16 completed controls, through tick 879. At sensor-only boundary
880 its bearing was -90.89036046215705 degrees, outside the frozen inclusive
±90-degree field of view. Its distance was 0.4524476273240058 m, within the 4 m
range, and no circular occluder blocked it. Thus FOV was the only failed sensing
predicate. The existing supervisor then raised `CueUnavailable` as declared.

| Boundary | Exit bearing | Distance | Exit visible | Recorded transition |
|---|---:|---:|---|---|
| 864 | -30.125848° | 0.579121 m | yes | Detour arrival; exit selected |
| 879 | -89.644788° | 0.451881 m | yes | Last completed control |
| 880 | -90.890360° | 0.452448 m | no | Terminal packet; no bridge/control |

The actual terminal pose was `(0.7973421216011047, 1.2063382863998413,
1.112785481989304)` in metres/radians, taken from the last control's `next_pose`.
This was a loss during travel, rather than immediate absence at the first exit
handoff observed in the window. First selection is explicitly window-scoped;
no claim about unexamined earlier history is needed.

The [retained result](memory-terminal-attribution-evidence/result.json) includes
all 65 reconstructed observations, the 64 recorded selections and separate
range/FOV/occlusion predicates. All reconstructed packets matched the recorded
packets. Only controls 816–879 and terminal packet 880 were analyzed. The existing
reader streamed all 153 rows solely to validate recording counts and checksums.

## Fixed scope and execution evidence

- [Protocol](../plans/memory-terminal-attribution.md): one invocation, 300 seconds,
  aggregate 128 MiB, 2 GiB free floor and 64 MiB headroom; zero retries.
- [Registration](memory-terminal-attribution-evidence/registration.json):
  SHA-256 `c9a1176499a2795525c6470e8fafbfcb9fd4db9d0a50c1c6a2b648bba6253e7a`,
  committed at `88b26e2` before execution; implementation `cf2fa63`.
- Twelve input files (35,318,397 bytes) and 52 source/protocol files (969,112
  bytes) were pinned and verified before and after; registration bytes also
  matched. Original raw chunks and scientific outputs were not rewritten.
- [Invocation](memory-terminal-attribution-evidence/invocation.json): exit 0,
  0.390343 seconds outer under `timeout --signal=KILL 300s`; the evaluator used
  0.329008 seconds and closed inside its original deadline.
- Zero native owners, physics steps, fitting, SNP decoding, supervisor/policy
  replay or held-out access. Reading retained control poses is not a new run.
- Runtime and published result/consumed receipts are byte-identical. The
  [independent verification](memory-terminal-attribution-evidence/independent-verification.json)
  found no discrepancies across all 64 files, copies, clocks and retained
  readout. It recomputed distance/bearing from reported poses without decoding
  the recording again; raw pose/occluder reconstruction was not repeated.
- Runtime plus publication occupied 177,016 bytes after independent verification,
  below 128 MiB; the check observed 12,844,363,776 free bytes. These are
  point-in-time measurements, not reservations or guarantees for later work.

The registration binds machine-local retained inputs. Published receipts support
review; reproducing raw attribution elsewhere requires those original recording
files and the pinned source/runtime. Raw NPZ chunks are not duplicated into Git.

The frozen protocol retains its pre-execution Task 2 checklist because its bytes
are registered. This report records that task's execution and close; the protocol
is not edited after consumption.

## Software verification

The final required suite passed **1,168 tests**, with 24 skipped and 39 warnings,
in 353.00 seconds (354.464 seconds outer). The post-review focused suite passed
43 tests. Commands and exact outputs are in the
[software receipt](memory-terminal-attribution-evidence/software.json) and
[final log](memory-terminal-attribution-evidence/full-suite-final.txt).

One independent source review found no Critical issue and two Important issues:
registration self-integrity and missing/duplicate bridge-event admission. Both
were reproduced and fixed with regression checks before registration. An added
guard binds imported project code to the hashed checkout. The review's minor
failure-receipt integrity gap is explicitly deferred; a failed invocation would
need independent post-exit byte verification before any unchanged-input claim.
The actual invocation succeeded and reported before/after integrity.

The preliminary full suite (1,162 passing tests) is retained but does not qualify
the later review changes; the final full run does. Synthetic tests supply software
evidence only. Exact red-test transcripts retain pytest's trailing whitespace;
source, tests and plan changes pass the scoped whitespace check.

## What changes next

The selected pilot remains **22/24 goals**, with own/sham local-null scores of
900 and **`mechanism_observed=False`**. Its shorter failed path remains a failed
frozen predicate. This diagnostic neither regrades that result nor demonstrates
the sham arm's terminal geometry independently.

The [prospective nine-condition design](../plans/memory-confirmatory-v3-design.md)
uses capped goal-reaching cost as a proposed primary endpoint, retaining actual
path length and terminal causes separately. It requires independently generated
families, counterbalancing, oracle isolation and a full matched control matrix.
It is not a frozen native allocation or a completed study.

The next concrete design question is how to qualify **continued target visibility
during null route-z travel** under the existing sensor/controller contract. A
finite arrival-only waypoint survey cannot answer this observed failure. Any new
geometry/profile/controller behavior must have its own prospective identities
and affected feasibility gate. Enlarging FOV or suppressing the exception would
change the scientific task and is not established as a repair by this evidence.
The exact family generator, feasibility matrix, sample size, analysis margins and
aggregate native resource budget remain to be frozen before further collection.

Memory/R2, learned puck, MaleCNS navigation, browser/lab acceptance, adequate
Afterimage, artistic/operator acceptance and final release delivery remain open.
CI and the physical rover remain outside this goal.
