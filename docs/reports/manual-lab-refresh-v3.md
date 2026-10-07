# Manual lab refresh v3 retained failure

The approved fresh allocation failed in 15.301984 seconds. Exactly one browser
workflow was selected; the production build passed. Its first manual native owner
completed 56 recorded ticks and closed with HTTP 200 / status closed at paused
revision 6. Its 121,470,976-byte recording reservation was admitted under the
approved managed 256 MiB budget. The previous 128 MiB quota refusal did not recur.

The failure occurred at `validPlacement()` (`ui/tests/lab.spec.ts:6`, called at
line 53). Chromium reported `net::ERR_INSUFFICIENT_RESOURCES` for a placement
preview, surfaced as `TypeError: Failed to fetch`. It did not return an HTTP error.
In the retained Playwright trace, `1-trace.network:69` has status -1 at
2026-10-07T16:32:23.707Z for POST
`/runs/d2fba77749974bae92665d1ef0a2629c/previews`, command move_goal to [-5,0],
expected revision 6. Matching console error is at `1-trace.trace:586`.
The preceding [-5,-5] candidate returned the expected HTTP 400 response,
"Placement intersects obstacle 0"; its earlier request appears at network line 70.

No cause for the exhausted browser resource has been established. The trace
supports neither a storage increase nor a UI workaround. Preview response bodies
are not explicitly consumed by the test helper; consuming them is possible
hygiene, not a demonstrated remedy. No code repair, retry or gate weakening follows
from this failed allocation. Original v1/v2/v3 phases and their markers remain.

The initial automatic snapshot exists. The requested paused snapshot, both
branches, comparison, SVG and acceptance screenshots were not reached.
This is not a passing manual browser workflow or evidence of human usability.

Original cleanup receipts record all 18 observed descendant identities exited,
no worker survivors requiring kill, no parent live survivors, group cleanup passed
and lease free. Server logs include application shutdown complete without errors.
These are original observations; later retained readback does not replace process
namespace evidence or prove broad tracker reliability. The software-only tracker
fixture characterizes pipe EOF, not the causal explanation of the v2 incident.

The [retained ZIP](manual-lab-refresh-v3-evidence/retained-records.zip) contains all
36 original phase, raw first-run, built-UI, registration and test-result records.
Each member was independently compared byte-for-byte against its source.
ZIP: 5,315,010 bytes; SHA256
`4b5649a6bcfbc01469153b3ca0bf92bc5996be8715ef72cd463bd557f8d2f798`.
[Publication inventory](manual-lab-refresh-v3-evidence/publication-index.json)
binds member hashes; [publication receipt](manual-lab-refresh-v3-evidence/publication.json)
retains the failed terminal disposition. Post-close byte-preserving packaging adds
no qualification or extra workflow. Qualification claims remain empty.

Required software suite: 973 passed, 24 skipped, 40 warnings in 110.10 seconds;
native qualification opt-ins disabled. The build and selected real-browser attempt
above are separate actual results. Independent source review found no Critical or
Important issue. Deferred minor: v3 write_json redundantly sets the same grace bound
already supplied by exit_grace; behavior is correct.

The browser gate stays open. Next work needs a prospective, diagnostic allocation
that can identify the Chromium resource failure before proposing another workflow.
Memory, learned-model capability, artistic acceptance and rover gates are unchanged.
