# CPU qualification 08: deadline failure with diagnostic boundaries

**The sole qualification 08 invocation failed at the unchanged 180-second
normal-return deadline. It is consumed; the installed runtime is not qualified.**
The diagnostic trace records NumPy and Torch returning. Its last observed marker
is entry into Torchvision, with no later marker. This narrows the observed
boundary; it does not establish timeout causality or a complete/authentic trace.
No episode, operator, renderer, model, study or release evidence is added.

## Controls and fresh admission

Source `f5523dc69c8d05ee2f3ff1118c633512c4b6a2e0` and pushed control commit
`2f74653367f14f0156479a52314f625d7400fc57` precede execution. Configuration 08 is
8,985 bytes, SHA256 `67076970caffe64b6162c4344f11d943b620dd2e0fb43ace72e39f508fa7ee60`.
The corrected freeze is 184,287 bytes, SHA256
`5b7d2b7814e9a3af61a1915f8b03f566949ae52c8cdc3e3ac912c22040e3d28a`,
with 749 unique pins totaling 58,476,477 bytes. Candidate D, all fifteen other
input pins, four original preparation anchors, nineteen absences, source path
rosters, environment, interpreter and resource limits remain unchanged. Only 08
admits the qualifier as the fifth preparation-relative source change; old 05–07
exact-four predicates remain strict.

Independent review caught a pre-invocation read-role defect: four historical 07
streams were first held as metadata and later requested as bytes. A warm-read
regression reproduced the real custody refusal; assigning their raw roles at the
shared manifest read fixed it. All five small control cases pass. The initial
four cases are included in those five. Both REDs and the uninvoked first control
revision are retained. No allocation or admission was consumed by those checks.
Both independent control reviews then found no remaining material issue. The
4,194-byte external coordinator differs from reviewed 07 only in 08 names and
freeze size/SHA; external budgets remain 145/240/145 seconds with the existing
outer termination envelope.

The one fresh data-only admission returned zero normally in **33.702206s**
(source 33.522233s). Published result and stdout are identical: 4,471 bytes,
SHA256 `099456da7ad8b2771566f753e5e58c8065061c9201357f789055399875aef4af`.
It completed all eight phases, full installed SITE and staged byte/custody checks,
native/interpreter/baseline checks, two forest censuses, final SITE metadata and
full held-content recheck: 32,318 files totaling 1,491,044,408 bytes. The staged
plan remains 27,255 files in four roots; SITE remains 27,225 files. Nineteen
negative imports and all twelve historical missing receipts were checked. It
closed FD4→4 with no children/extra threads; six recorded 06/07 PID/start samples
were absent. Independent small-receipt review passed without rehashing payloads.
This is dated pre-run data acceptance, not runtime or post-failure acceptance.

The fresh pre-observer guard rechecked all 749 pins, the admission binding and
twelve future-output absences. Available RAM was 3,873,497,088 bytes; project disk
64,523,853,824 bytes; executable tmpfs 3,344,674,816 bytes. The qualification RAM
floor stayed 2 GiB and its normal-return deadline stayed 180s.

## One runtime invocation and one independent refusal

The observer's external coordinator returned 1 normally in **180.463841s**, with
no external timeout. The parent transport reports return 1/no observer timeout
in 180.406979s. Its complete measured transport is 951 bytes, SHA256
`d80f60a10cf611c660e5bda25bf6f055c49415686681db33ca6ae44f868841b4`.
Parent stderr records the normal-return deadline; parent stdout is empty.

The worker's stderr contains eleven diagnostic records (1,469 bytes). Times below
are relative to the first validated-bootstrap trace clock, not the parent clock.
Return markers precede the corresponding version/guard acceptance; none replaces
the absent terminal four-import receipt.

| Observed boundary | Enter (s) | Return marker (s) |
| --- | ---: | ---: |
| Dependency setup | 0.060496 | 22.404091 |
| NumPy import | 28.676469 | 38.084061 |
| Torch import | 39.832563 | 79.741130 |
| Torchvision import | 81.564484 | Not observed |
| MuJoCo import | Not observed | Not observed |

The final result and baseline-after receipts are absent. Worker stdout is empty;
there is no completed four-import or parent-closure receipt. Supervision records
SIGTERM/−15, sampled peak RSS 610,668,544 bytes and no sampled matching survivors.
Its three recorded PID/start pairs are `(3996069,54384185)`,
`(3996070,54384185)` and `(3996071,54384186)`. These are bounded operational
observations, not exhaustive process-lifetime proof or hard WCET.

The auditor command was concretely bound to the measured transport SHA after the
observer finished. Its one CLI invocation returned 1 normally in **0.115966s**.
It published a 616-byte generic-v1 FAIL receipt, SHA256
`93fb936dcf82bcf46a592026e8744c5900bf5bd9b283465d5e5dfad13d346ba9`,
with `Normal external transport exit required`. This is the expected early
refusal of a failed transport, not a v8 acceptance or a fresh payload audit.
No complete post-08 installed/staged custody pass has run.

## Next product action

Preserve consumed attempts 01–08 and their missing receipts. Investigate repeated
guard computation with bounded authored measurements, then make only a proven
redundancy correction that preserves acceptance/refusal and custody checks.
Source inspection identifies repeated module-state scans, native/full-check
boundaries and cache-set construction as candidates; their elapsed contribution
has not been measured. Existing leases already avoid repeated bulk content
hashing, so full checks must not be described as re-reading 1.3 GiB each time.

A last marker cannot prove the failing operation or explain 07. Do not increase
the deadline, weaken checks, retry 08 or create 09 controls from this report.
Review and verify any source correction before separately freezing a future
execution. The product exit remains one real episode recorded, replayed and
exported after runtime and operator/renderer admission. All seven release gates,
artistic/operator acceptance and the final integrated release remain open.
CI, full-repository tests and physical rover work are outside this runtime unit.

## Preserved evidence

The byte-preserving packet contains 135 artifacts, 13,569,797 bytes and eight
empty files. It binds all 26 source files to source commit f5523dc and all 33
control files to control commit 2f74653, plus the 27 unchanged input origins,
actual allocation files, inner and outer streams, terminal observations,
measured audit command, guards and independent reviews. It does not recursively
duplicate the older 749-pin history. Independent outcome review confirms the
failed/consumed boundary without a cause or acceptance claim.

The archive/original/source-Git verifier passed. It checks this retained packet,
not current installed/staged payload custody:

```sh
python docs/reports/puck-cpu-held-qualification-08/verify_evidence.py --originals
```

Add `--git-revision <evidence-commit>` to verify the committed archive bytes.
