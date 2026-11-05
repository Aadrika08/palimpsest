# Prospective memory-v4 order: static bounded-imbalance check

This is **STATIC_ONLY** source/design validation. It does not amend a registered
protocol, accept a runtime observer, open protected data, construct a case, grant
study admission, or authorize execution. No model, simulator, SciPy solver or
Palimpsest runtime was imported. Original schedules and profiles remain unchanged.

## Inputs and identity

- Pinned assignment source `src/palimpsest/memory_decision_world.py` SHA-256:
  `d518e0cdaa6ac2352c7ed681ca85d7722708b50feb106ad0f9cb8c3f6fa75991`.
- Canonical 48-assignment roster SHA-256:
  `f8faddb5156c46e6898b2a8a1dfd329297349e49b30999b05102e533afed25cd`.
- Canonical existing candidate JSON SHA-256:
  `d0c5ded906cb80b8294b37a2bc9654f80b0d11d9fa03657248df394687b99409`.

Candidate: `docs/reports/memory-v4-order-bounded-imbalance-candidate-2026-11-05.json`.
`assignment-roster.json` retains the exact static assignments; `static-counts.json`
retains recomputed counts and all 48 proposed process orders. Roster derivation
reads literal factor tables from the pinned source AST and applies the documented
`divmod(row,4)` assignment arithmetic. It never imports that source or calls case
construction. The production validator instead requires a caller-supplied exact
roster and three independently frozen expected digests. Digests computed from an
untrusted replacement are not authority. Solver status and self-reported
`integer_constraints_verified` do not substitute for recomputed counts.

Canonical digest encoding is ASCII JSON with sorted keys, separators `(',', ':')`,
`ensure_ascii=True`, and `allow_nan=False`; the pretty-printed retained file hashes
therefore differ from these canonical object identities.

## Recomputed result

Every row proposes `source`, then `own`, then a cyclic shift of these eight:
`swapped`, `sham`, `no-U`, `hand-authored`, `history-independent`, `traversal`,
`retrieval`, `oracle`. No condition is duplicated or omitted. Each shift occurs
six times among 48 families and twice within each of south/north/tie's 16 families.
Consequently every other condition occupies each of the eight remaining positions
six times overall and twice per cost stratum. The three kinds retain this family's
order; repeating three kinds does not create extra independent families.

For every non-own condition and remaining position, the six rows contain exactly
three `regimebit=1` and three `relation_side=1` assignments. Each public binary
factor has **two through four ones**, not exactly three. Histograms below count
all eight conditions times eight positions (64 entries per factor):

| Public factor | 2 ones | 3 ones | 4 ones |
| --- | ---: | ---: | ---: |
| fact_first_side | 24 | 16 | 24 |
| subject_first_side | 32 | 0 | 32 |
| route_first_side | 8 | 48 | 8 |
| schedule_index | 24 | 16 | 24 |

This is a bounded-imbalance candidate, **not exact public-factor balance**.
The naive `shift=row%8` schedule is rejected because it aliases the hidden factors
with position despite matching aggregate shift and stratum counts.

## Limits and unresolved confounds

`own` is always first after source, so own-versus-reference comparisons do not
counterbalance own's process position. This checker grants no wall-time causal
claim. Restoring the same declared simulation state does not establish absence
of runtime contamination, thermal/load effects, omitted state, numerical drift or
an independently qualified serialization observer; those remain execution gates.

Balancing the two hidden columns separately is not joint factorial balance.
`hidden-joint-diagnostic.json` retains the 2x2 joint table for each condition and
position. Six rows cannot be evenly divided across all four joint combinations;
higher-order/public-hidden interaction balance and independence are not established.
The result explicitly leaves `higher_order_balance_verified` false. No statistical
or capability outcome, positive or null, follows from these static counts.

The proposed permutation needs a separately reviewed prospective order protocol,
source/profile/digest updates and tests before any study. It must preserve original
analysis controls/margins and separate development/held-out boundaries; the
validator itself neither selects a held-out block nor opens an allocation.

## Source checks

New files: `scripts/memory_family_order_v4.py` and
`tests/test_memory_family_order_v4.py`. The pure validator accepts only 48 canonical
unique rows, exactly three named strata of 16, six typed binary columns and 48
integer shifts in 0..7. It rejects bool-as-int, unknown/partial/duplicate rows,
source/design/candidate identity drift and an admission-granting candidate.

Actual TDD: `tdd-red.log` records 12 expected assertion failures while the validator
was absent. `tdd-green.log` then records 12 passing tests. A bounded metadata
conversion regression in `tdd-red-metadata.log` reproduced an oversized integer's
float-conversion overflow; range checking before conversion fixes it.
`tdd-green-final.log` records **13 passing tests**. These are source/static tests,
not simulation observations. No code was committed by this lane before review.

```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -m unittest discover -s tests -p test_memory_family_order_v4.py -v
```
