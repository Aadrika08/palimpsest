# MaleCNS v4 stage S0z — PASSED (18 November 2026)

Owner GO and ruling (2026-11-18): "derived arrays" in the protocol's S1 precondition is read as the
pinned schedule derivation and rosters (decisions log). S0z is a pin plus independent compact
audit; it wrote no data arrays. Independently reviewed twice (approve with changes, applied).

| Item | Value |
| --- | --- |
| Audit | `passed`, no failures, `torch_imported: false`; S0f record/chain, 11 outputs re-hashed, manifest pin, structure, old corpus equals S0c, commits/linkage/S0e counts, S0e-A audit passed (no waiver) |
| Corpus pin | `corpus-pin.json` sha256 `f6115c1e03d5aec37ac2463cc833bbd8fbea06403a8ae1c98e6a3f049b6b29b7`; chain S0a→S0z; 10 old + 12 advice + 4 dev = 26 unique fingerprints; no `arrays` key |
| Audit sha256 | `2bef156950ddea57191dd0e5ade16326d90f08f1f53c820f46b70f33b7230119` |
| Dry load of what S1 consumes | `read_corpus_pin` accepts it; `derive_schedules` sha `81cd9a49…` (old N 2,117 q 21 r 1,623; augmented N 7,197 q 6 r 2,898) |
| Charged CPU | **0.726466 s** (worst case 305) |

S1 prerequisites remaining (not part of S0z): stage P re-run covering the S0z controller/audit and
the S1 data child (new manifest + GO, 125 CPU-s worst case); S1 execution manifest and review; then S2
(needs a v4 Engine binding and an engine.py type allow-list entry — see `docs/reports/male-v4-s2/NOTES.md`;
protocol amendment + review required).

Operator note: the first post-run script assumed a flat roster list (the pin stores it by group);
all values verified correct.
