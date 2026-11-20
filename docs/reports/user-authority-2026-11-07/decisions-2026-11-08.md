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
| **D2 for puck S1** — byte-reading tracked copies of authored held-out 6200–6207 rows for S1 calibration and the S1 ID comparison; never loading into reset/simulator; not reusable for S2/S8a | `f885fc8d…286b` | **Granted (scope S1 only)**; GO record `palimpsest-authored-test-evidence/puck-v4-go/d2-scope-s1.json` |
| **Puck S1 GO + D8 audit GO** | `f885fc8d…286b` | **Granted**; S1 attempt 1 ran: refused (0 collisions, 63 ambiguous = one FLYNN cell-type table content), 86.61 + 0.07 CPU-s charged; see `docs/reports/puck-v4-s1-2026-11-08/` |
| **After S1 refusal: amend vs record blocked** | `f885fc8d…286b` | **Amend** — draft a disclosed, independently reviewed Amendment 1 (one-content non-scene allowlist) and one new S1 attempt; amendment text and the new S1 GO each still need explicit owner approval |

Note (2026-11-09): the attempt-1 evidence README says "No retry is permitted"; that was true
under the base protocol. Puck v4 Amendment 1 (proposed) permits exactly one more attempt; see
`docs/reports/puck-v4-s1-attempt-2/MANIFEST.md`. The attempt-1 evidence is unchanged.

## 9 November 2026

| Decision | Protocol (sha256) | Owner answer |
| --- | --- | --- |
| Puck v4 **Amendment 1** (one-content non-scene allowlist; exactly one more S1 attempt; attempt-2 refusal ends puck v4) | `8d8529712614292ba470ce88f60aaad7d061a1732851627f3be0e1e8c0d1b20f` | **Approved** |
| MaleCNS v4 **Amendment 1 erratum 1** (window derivation H3; v4-copy redirects and two ported files H1) | `cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477` | **Acknowledged** |
| **GO puck S1 attempt 2** + D8 audit (stages `S1-attempt-2`, `S1-attempt-2-audit`; worst case 660 + 120 CPU-s), conditional on frozen-window checks | `8d852971…b20f` | **Granted** |

## 18 November 2026

| Decision | Applies to | Owner answer |
| --- | --- | --- |
| Reading of protocol sentence "S1 does not start before S0z review passes and derived arrays are published": "derived arrays" = the pinned schedule derivation and rosters (no array bundle; v3's trainer derived arrays in-process, hash-gated, and so does v4's S1) | MaleCNS v4 protocol `cd4eb130…` | **Accepted** (no amendment) |
| GO MaleCNS v4 stage S0z (pin + independent compact audit; `scientific_attempt: true`) | S0z manifest | **Granted** |
| Acknowledge MaleCNS v4 stage **P2** (smaller import re-probe of the 6 new/changed entries: S0z controller, S0z audit, S1 data child + its T-f closure, S1, S2; P2 failure treated as P failure) and **GO P2** (worst case 125 CPU-s) | P2 manifest | **Acknowledged and granted** (19 Nov 2026) |

| Decision | Applies to | Owner answer |
| --- | --- | --- |
| **A2** — MaleCNS v4 Amendment 2: `NavigationBindingV4`, five-line `engine.py` allow-list hunk, S2 owner worker/index publisher, tests, stage P3 gate. Source scope only; no run authorised. | `docs/plans/m7-navigation-v4-amendment-2.json` sha256 `c4cd3a506b0b468b0d6d4d359dff7ecbd3b3bf0c25c6fe9360207282249f8d6f`; base protocol `cd4eb130…` unchanged | **Approved** (19 Nov 2026) |

## 20 November 2026

| Decision | Applies to | Owner answer |
| --- | --- | --- |
| **A2 erratum 1** — wording mismatches 1 to 5 of `docs/reports/male-v4-stage-p3/MANIFEST.md` (no index builder: the binding reads S1 directly, A2's second option; `graph_sha256` and `ordered_ids_sha256` are re-derived, not S1 report fields; `success_admitted` is a predicate; `reduce`/`check_protocol` are same-module; `--s1-output` bound to the hard-coded S1 tree). A2 file unchanged; P3 covers 3 entries, not 4. Row id: `a2-erratum-1` | A2 sha `c4cd3a50…8d6f`; base protocol `cd4eb130…` | **Acknowledged** (20 Nov 2026) |
| **GO MaleCNS v4 stage P3** (navigation lane, import probe of `S2-binding`, `S2-owner-worker`, `S2`; worst case 125 CPU-s; one attempt; `scientific_attempt: false`) | `docs/reports/male-v4-stage-p3/MANIFEST.md` | **Granted** (20 Nov 2026) |
