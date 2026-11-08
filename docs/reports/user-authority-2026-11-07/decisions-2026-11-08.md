# Owner decisions — 8 November 2026

Recorded from the owner's direct answers in the interactive session. Each entry
names the exact protocol bytes it applies to.

| Decision | Protocol (sha256) | Owner answer |
| --- | --- | --- |
| MaleCNS v4 defaults 1–8 | m7-navigation-v4-regenerated-matched-budget-protocol.json `6f535edb…ad88` (carried into `238bc160…94f8`) | Accept all recommended defaults |
| Puck v4 D1–D9 | m6-puck-navigation-v4-regenerated-on-policy-relabeling-protocol.json `f885fc8d…286b` | Accept all (held-out = authored 6200–6207; D8 120 s audit kill; D9 S1 before S0) |
| Manifest reviewer (both) | both protocols | Fresh AI reviewer agent; recorded as AI review, not human acceptance |
| **A1** — MaleCNS v4 Amendment 1 (producer ports + rebuilt S0d/S0e controllers) | `238bc160d26c70273765eb1d51f8280383f99a88bc8f26ec4a829048552594f8` | **Approved** |

A1 is a source-behaviour change relative to the earlier data/path-only overlay
choice; it was presented as such, with the alternative (MaleCNS v4 blocked at
S0e). No stage GO is implied by any entry: every stage still needs its own
reviewed execution manifest and an explicit owner GO.
