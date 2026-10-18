# Manual lab Chromium resource diagnostic v1 — proposal only

No allocation is approved. This document authorizes no invocation, native owner,
browser run, code change or retry. Finish the separately scoped memory campaign
first; root must serialize any later diagnostic against all writer/native
campaigns. The consumed v1/v2/v3 phases, markers and retained evidence are immutable.

## Retained observation and question

[v3 failed](../reports/manual-lab-refresh-v3.md) in 15.301984 seconds. Its first
manual owner recorded 56 ticks and closed with HTTP 200/status closed at paused
revision 6. The 121,470,976-byte recording reservation was admitted under 256 MiB.
At `ui/tests/lab.spec.ts:53`, `validPlacement()` sent `move_goal [-5,-5]`, received
the expected HTTP 400, skipped the existing goal `[-5,-3]`, then sent `[-5,0]`.
Chromium reported `net::ERR_INSUFFICIENT_RESOURCES`/`Failed to fetch`, with no HTTP
response. All 18 observed descendant identities exited; no kill or live survivor
was required. The paused snapshot, branches, comparison and export were not reached.

The exhausted resource and its cause remain unknown. Distinguish a browser
transport failure without HTTP response from an HTTP quota refusal and an engine
failure using contemporaneous browser, server and owner records. The helper leaves
preview bodies unconsumed, while `ui/src/api.ts:7` consumes JSON in the ordinary
viewer path. This difference is an observation, not an established remedy; no
response-body change, storage increase or UI workaround is proposed.

## Smallest prospective exposure

Prepare a separately reviewable, pinned diagnostic runner using the existing built
viewer, pinned Playwright/Chromium and local server/process/storage helpers. Do not
rerun the full manual workflow or edit its acceptance test. Before approval, freeze
source/runtime/dependency and built-UI hashes, exact argv/environment, fresh absent
output paths, exclusive launch marker, fixed setup commands and all caps below.
Preparation and source-only checks need their own authorized scope; none run here.

Use one server, one browser context/tab and one fresh `sparse-navigation`, `checker`,
manual/CPU, seed-0 owner. Keep it paused and advance with exactly 56 sequential
Step commands, checking each authoritative applied receipt and tick before the
next. There is no public native tick ceiling, so do not use Start/free-running plus
polling as a purported hard bound. Recreate the retained setup through public
validated commands: action `[1,0]` at authoritative `total_tick=7`, `[0,0]` at 17,
`[0,0.8]` at 20, `[0,0]` at 23; obstacle 0 to `[-5,-5]` at 46; goal to `[-5,-3]`
and left-eye false/right-eye true at 55; then the final Step to 56. These
payloads/tick boundaries come from retained `recording/events.jsonl`, not SNP decode.

At the fresh paused revision, plan exactly two sequential browser-fetch POSTs to
`/api/v1/runs/{id}/previews`: `move_goal [-5,-5]`, then `move_goal [-5,0]`, both with
that same observed revision. Preserve the helper's response-consumption pattern
during the sequence. No placement search, extra preview, reload or request retry.
Record the actual revision; never forge the old revision 6. Paused stepping changes
revision and stream timing from the original running history, so this is a bounded
exposure to the same two preview payloads, not an exact replay. Nonreproduction is
inconclusive. Send the second only after the expected first HTTP 400; an unexpected
setup/state/first-preview outcome ends the attempt with fewer than two requests.

## New proposed caps, requiring separate approval

These are fresh prospective limits, not unused or borrowed v3 budget. Numeric reuse
does not reopen the failed allocation.

| Resource | Frozen proposed maximum |
| --- | --- |
| Invocations | One diagnostic launch; zero corrective attempts/retries |
| Owners/control | One native owner; exactly 56 ticks; 63 setup commands maximum (56 Step + four action + two intervention + one eye-mask); no Start/reset |
| Diagnostic previews | One planned two-request sequence; at most two POSTs total; zero setup preview searches |
| Other lifecycle | One owner-create and at most one owner-close request; one browser context/tab and at most one viewer WebSocket handshake; zero requested snapshots, branches, comparisons or exports; automatic initial snapshot only |
| Time from launch marker | Exposure finishes by 120 s; teardown by 150 s; terminal receipt by 170 s; outer TERM at 175 s/KILL after 5 s; aggregate 180 s |
| Managed runs/exports | 256 MiB; retain existing reservation and actual-write refusal; do not shrink the established 600-tick reservation merely because only 56 ticks are requested |
| Aggregate writes | 1 GiB including controls, recording, raw capture and final receipts; initial free floor 4 GiB, continuing floor 2 GiB |
| Raw capture | 64 MiB combined; each text/stdout/stderr stream 1 MiB; no unbounded trace or netlog |
| Cleanup | One collective natural-exit grace of at most 2 s within teardown; exact PID/start-ticks/process-group checks; matching survivors killed and attempt failed |

The existing reservation was already admitted at 256 MiB; there is no observed
reason to raise it. The smaller owner/tick/request scope and 180-second aggregate
are new reductions from v3's three-owner/360-second workflow. The 1 GiB aggregate,
free-space floors, stream cap and identity/grace rules reuse reviewed mechanisms
under a new allocation. A capture cap, deadline, disconnect or survivor is a terminal
failure: preserve partial output, perform bounded cleanup and stop. Do not truncate
silently, reconnect automatically, delete output to continue or launch again.

## Capture and disposition

Capture UTC and monotonic timestamps, raw Playwright trace, Chromium network events
(request IDs, payloads, response status/headers or loading-failure error), console
and page errors, WebSocket events, server/owner logs, command receipts and storage
admission/actual-write records. Keep browser-fetch behavior unchanged; post-sequence
network body retrieval, when available, is evidence capture rather than a repair.
Record instrumentation overhead and any unavailable capture explicitly.

For this campaign's observed descendants only, retain PID/start-ticks/group and
unprivileged `/proc` FD counts/limits, RSS and thread counts at baseline, 1 Hz during
the at-most-120-second exposure, immediately around both previews and on failure.
Retain ordinary host observations at the same times: memory/swap availability,
load, readable CPU/memory/I/O pressure, system open-file count and free disk bytes.
Keep raw readings and sampling gaps. Use ordinary read access only: no privileged
tracing, limit/configuration changes, new framework or all-systems audit.

After the two previews or any terminal failure, retain the close outcome, graceful
server shutdown, every observed descendant identity's exit outcome and released
ownership; any forced cleanup remains failure. Preserve v3's failure and retain
the diagnostic's separately allocated local raw records, hashes and disposition.
Neither a reproduced error nor a clean diagnostic passes the full browser workflow
or identifies cause by itself. Correlation is not causal proof. Propose an
implementation only if these observations support a specific mechanism, then seek
a separate preparation/verification allocation; no automatic remediation run.

No model rescue, held-out experiment, native SNP decoding, hardware, CI, scientific
qualification, artistic/human-usability acceptance or browser-gate closure belongs
to this diagnostic. Qualification claims remain empty.
