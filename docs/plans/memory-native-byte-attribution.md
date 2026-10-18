# One registered native byte-attribution readout

7 October 2026. User `continue` resumes the next boundary recorded in PR #72:
attribute the retained 72-byte mismatch and verify actual model arena eligibility.
Parent `29b01b5`; branch `research/memory-native-byte-attribution`; draft PR stacked
on #72. Repo-local Aadrika Maurya <aadrikamaurya@gmail.com>, push as Aadrika08.
Main unchanged; CI excluded. Account quota telemetry unavailable.

Reuse `memory_restore_offline_readout` and its guards, raw/post audits, immutable
inventories, deadline/close handling and full-state comparison. Add one optional
registered `readout_kind=native-byte-attribution-v1`. Preserve all old executions,
registrations, markers and reports. Commit this contract, software and machine
registration before one new invocation with a fresh output and exclusive marker.
Same limits: 300 s total, external 290 s TERM/5 s KILL, output 64 MiB, logs/controls
1 MiB, trusted input SNP 16 MiB, admission free space 10 GiB, ongoing 2 GiB floor
with 64 MiB headroom. No retry or evidence deletion.

After independently auditing the same two retained five-control restores:

1. Deserialize trusted same-version native bytes into local data objects; require
   byte-identical deserialize/serialize round trips before mapping.
2. For each side, change each timer duration on the decoded copy using a finite
   float64 probe that changes all eight representation bytes. Require exactly
   eight contiguous serialized bytes, matching the old/probe representation and
   no changes elsewhere. Restore the original value and require its exact bytes.
3. Record all differing offsets and their unique timer-index mapping. Copy only
   right-side timer durations into the left decoded object and test exact full
   serialized equality with the right original. This is a byte attribution probe,
   never a saved snapshot repair or amended comparison/qualification rule.
4. Record actual decoded solver, noslip_iterations, nA, nefc, and ownership/base/
   shape of the two suspect AR arrays without reading unbacked array contents.
   Use reviewed MuJoCo 3.3.6 dual-solver eligibility predicate, with source links.
5. Report the existing repaired decoder's field comparison and omissions, the
   unchanged full-state result, attribution coverage and any unexplained bytes.

Stop on any unsupported version, non-identical round trip or nonlocal probe.
Attribution failure/partial coverage remains an exploratory result, never a gate
pass. No native worker, neural inference, reset/forward/step, current PID probe,
physics replay, state migration, normalization amendment, qualification, pilot,
held-out or physical claim. Two restore attempts from one frozen source/profile/
seed are the experimental unit, not ten independent samples.

Leave one focused synthetic software regression covering timer-only and unrelated
state differences, plus reuse the launcher admission/exclusive-marker check.
Run the relevant existing tests and full local suite. Keep exact executed code
and compact indexed receipts in docs; raw SNP/NPZ stay local. One final independent
read-only branch review; fix Important/Critical software issues, then publish the
draft. Stop at the findings: any contract proposal/fresh qualification is separate.
