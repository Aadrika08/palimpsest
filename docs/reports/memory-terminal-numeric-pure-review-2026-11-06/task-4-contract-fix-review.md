# Task4 contract fix rereview

**PASS — the two previously required contract fixes are resolved.**

This is a bounded source-only rereview of the current uncommitted plan at
unchanged HEAD `5148b3c8062f6911ec6a4417dd8eed4f902bca2d`. It checks only the two
findings in `task-4-contract-review.md`, plus the supplied frame-cap clarification.
It is readiness for scoped Task4a source implementation, not implementation
completion, passing tests, actual receipt acceptance or scientific qualification.

1. **Exact audit_schedule shape — resolved.** Plan lines295–297 now require
   exactly `event_tick,decision_tick`, equal the Context.schedule projection.
   Boundary tick remains separately bound through proof and row intervals.
   This removes the inherited two-field versus full three-field ambiguity.
2. **Per-API proof bindings and preservation scope — resolved.** Plan
   lines328–354 explicitly require exact proof validation, copied proof equality,
   copied-member descriptors, original Context identity and profile bindings;
   convert/prove bind the five input descriptors, job descriptor, report and
   exact supplied writer bytes. Counts, intervals, terminal relationships and
   available event references must agree. Read recomputes the available stored
   sequence/trace commitments and selected-camera checks but explicitly cannot
   authenticate all retained values or timing fields from opaque row digests.
   Read reports raw comparison false and actual acceptance false. Convert
   checks its actual encoded result against supplied raw; prove performs the
   exact raw comparison. Only a performed comparison may report true, and
   actual acceptance remains false. No Task3a schema change, fabricated receipt
   or absent public adapter is introduced.

The explicit frame-cap statement at lines367–369 correctly preserves the
unchanged limit: sixteen camera pairs already occupy1.5MiB before headers;
container bytes can therefore force refusal. Dropping selected frames or
raising the cap is forbidden. This is a capacity constraint, not new positive
fixture evidence.

No remaining material gap was found in these two fixes. The prior scoped pass
on the other wire/profile/accounting choices is unchanged; this is not a fresh
full-plan audit. Implement against the exact new checks and preserve the
reader-only versus raw-comparison distinction in API results, profile and tests.

Only this rereview report was written. No tests/imports/probes, code/test/profile
edits, protected/raw/SNP/native/model access, CI, dependencies, cleanup, agents
or HEAD change occurred. Git status still showed only the existing plan
modification among tracked files. All actual qualification, admission,
publication, GO and pruning gates remain closed; Task4b still waits for its
separate genuine receipt/held-input contract after3b.
