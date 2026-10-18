# Manual lab refresh stopped at test selection

7 October 2026. One fresh software/simulator QA pass was consumed under the
[frozen plan](../plans/manual-lab-refresh.md), producer
`ffe3e7794458d583865e55cc7b25c6151efb03c2`, stacked on artifact-reader fix
`1031c5a`. The UI build passed and the loopback lab server started. Playwright
returned **1, “No tests found.”** before the browser workflow or any native
simulation owner began. The phase failed; it supplies no browser/native or
artwork qualification. Zero corrective attempts were allocated and none occurred.

[Structured report](manual-lab-refresh.json) indexes thirteen byte-identical
retained-file copies and a separate diagnostic source excerpt.
The original ignored phase and consumed marker remain unchanged. These control
copies are forensic evidence, not instructions to launch another pass.

## What ran and what did not

The [registration](manual-lab-refresh-evidence/registration.json) fixes the exact
build/server/browser argv and 204 source/runtime identities. It records unchanged
upstream `8d964599119b420de67ee259434d273651a1a76d`, Python 3.11.15, Node 24.21.0,
MuJoCo 3.3.6 and cached dependency metadata including Playwright 1.63.0 and
Vite 8.3.2. Cached locks, seven top-level versions and 26 installed-manifest
entries matched. This verifies declared cached metadata, not every package byte
or a fresh installation. No dependency or asset download occurred.

The [stdout log](manual-lab-refresh-evidence/supervision/stdout.log) retains the
successful TypeScript/Vite build, its three output files, and selection error.
The [server log](manual-lab-refresh-evidence/server.stderr.log) retains startup
and `Application shutdown complete.` The source reached its HTTP session
readiness check before invoking Playwright. No workflow test body ran; the
[browser receipt](manual-lab-refresh-evidence/browser-last-run.json) says failed
with an empty failed-test list. The Chromium version command was a setup probe,
not a browser session. No recordings, SVGs, owner-close attachment, browser trace
or desktop/mobile screenshots were produced.

The worker retained `RuntimeError: Child exited 1`; the parent retained an
empty-message `AssertionError` after rejecting the failed supervisor/worker.
The terminal command and supervisor returned 1. Parent elapsed time before
receipt publication was **3.409 seconds**, worker elapsed **2.515 seconds**;
these are not end-to-end terminal wall-time measurements. Normal-path browser
and server return-code fields were never assigned; do not infer them from the
failure-path receipts.

## Selector diagnosis and cleanup

The frozen selector was:

```text
--grep "^actual local manual workflow, snapshots, sequential branches, comparison and export$"
```

The target exists at `ui/tests/lab.spec.ts:21`. Installed Playwright gives its
file suite the relative filename, collects parent suite titles, appends the test
title/tags, and applies CLI grep to that joined string. The grep input therefore
contains `lab.spec.ts` before `actual …`; the leading `^actual` rejects it.
[Primary source excerpts](manual-lab-refresh-evidence/selector-source.txt)
retain file/line references. Common/runner/util source hashes were collected
after stopping, distinct from the original 204-pin registration. This diagnosis
explains the selection failure, not a product workflow failure or pass.

Independent read-only audits verified the launch-to-registration hash and all
204 pins. Worker PID/start identity, its process group and all five sampled
descendant identities were absent. No observed survivor required forced cleanup;
the original receipt reports the storage lease released. Publication checks
acquired no new lease and invoked no test, browser or native owner. Process
sampling is not proof about an unobserved transient process.

Retained controls/logs/build/browser-results occupied **328,744 bytes in 21
files**, including empty lock files, below the frozen 1 GiB aggregate ceiling.
The 360-second aggregate, 330-second supervisor, outer TERM at 350 seconds plus
five-second KILL grace, 128 MiB managed roots, three-owner/two-snapshot/one-export
ceilings and 1 MiB logs were not exhausted. Storage observations are not an
atomic filesystem quota. Deadline and detached-browser teardown paths were not
exercised by this early failure.

Before launch, control checking caught and repaired an observation exception
that could bypass child cleanup. Its real harmless Python-child fixture first
failed, then confirmed termination and a failed receipt. The final
[control check](manual-lab-refresh-evidence/control-check.py) also checked the
consumed marker, nonzero child, deadline and log cap. Those checks supply no
browser/native evidence. Shutdown completion and failed-supervisor rejection
were strengthened before registration; no controls changed after invocation.

## Concrete next decision

Do not repair or rerun `manual-lab-refresh-v1`. A separately named prospective
phase could select the unchanged pinned `tests/lab.spec.ts:21`, omit the faulty
grep, and permit one metadata-only selection preflight plus one actual workflow
invocation. Freeze exact identities/argv first, require the preflight to select
exactly this one test before starting any server/native owner, and retain the
same 360-second/1 GiB/three-owner/one-export caps with zero corrective attempts.
This is a proposal requiring the owner's explicit allocation decision under
the exhausted phase's stopping rule, not a newly frozen or executed phase.

The current goal remains incomplete: fresh lab workflow evidence, timer-aware
restore/memory studies, learned puck/navigation capabilities, adequate six-mode
artwork materials and human/operator acceptance remain open. The material pass
has its own consumed allocation and separate pending proposal. Main and the
physical rover remain unchanged; CI, held-out access and model fitting were not
part of this pass. `qualification_claims` remains empty.
