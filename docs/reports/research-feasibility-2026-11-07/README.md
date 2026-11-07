# Research lane feasibility — 7 November 2026

Metadata/receipt arithmetic only. No research process ran; no protected or
held-out input was opened. These are planning findings, not measured study costs.

## Memory (12 CPU-hour lane): full protocol does not fit on current evidence

- Population per block (`docs/plans/memory-family-allocation-admission-v3-protocol.json`):
  48 families x 3 kinds = 144 source owners + 1,296 condition owners. Two blocks:
  **2,880 fresh workers**.
- Only CPU evidence for a FLYNN worker: four zero-tick anchor workers, mean
  **25.1557 CPU-s** (`docs/reports/memory-numeric-source-software-2026-11-06/historical-startup-cost-planning-scenario.json`).
- Transfer scenario: 2,880 x 25.1557 = 72,448 CPU-s = **20.1 CPU-h before any tick**,
  168 % of the 43,200 CPU-s lane; 15.0 CPU-s per worker is all the lane allows.
  The development block alone (1,440 workers) uses 36,224 s on startup, leaving
  6,976 s for ticks.
- This is a transfer assumption (fresh process per owner, historical startup),
  not a measurement. Amortized startup is not permitted by the current fresh-owner
  contracts. The protocol, cohorts and lane cap are unchanged.
- Status: **blocked on budget** unless a single measured development case shows
  per-worker CPU far below the transfer figure. That case is affordable (source
  cap 1,800 CPU-s = 4.2 % of the lane; at most ~3.9 GiB storage) but needs a
  production freeze-metadata builder, runtime manifest, namespace exports,
  launcher with CPU census, independent review, and an exact owner stage GO. The
  nine-condition route (handoff amendment, Tasks 2b/3b/4b/5, condition runner) is
  not implemented.

## MaleCNS (4 CPU-hour lane): fits on expected cost; worst-case limits do not

- Protocol: `docs/plans/m7-navigation-v3-matched-budget*.{md,json}`; six models
  (old/augmented x seeds 10/11/12), dev 3130–3133 (>=3/4 per augmented seed),
  held-out 3120–3127 (>=6/8) only after a separate GO.
- Attempts 1 and 2 are consumed (argv mismatch; `ModuleNotFoundError: httpx` in the
  frozen interpreter via `verify_endurance` at import time).
- Expected (wall-rate extrapolation): <= ~4,250 s. Sum of stage worst-case limits:
  15,340 s > 14,400 s lane. Needs an admission rule that charges actual CPU and
  refuses any stage whose worst case would cross the remaining lane.
- Missing: dependency-closure probe/fix, attempt-3 manifest, dev evaluator
  (`scripts/evaluate_male_navigation_v3.py`), 3130–3133 disjointness admission.

## Puck (5 CPU-hour lane): longest path

- Protocol: `docs/plans/m6-puck-navigation-v3-on-policy-relabeling*`. No v3 stage
  attempted; all earlier attempts 0/4.
- Worst-case stage limits 19,440 s > 18,000 s lane; expected ~1,600 s (wall-rate).
  Worst-case retention 17.4375 GiB > 16 GiB cap.
- Missing: registry discovery/identity projection, collection launcher/bootstrap,
  data preparation, v3 trainer, mechanism admission, 24-owner dev evaluator.

All prior study figures are wall seconds; no process CPU has been measured for
memory, puck or MaleCNS. Research CPU charged to date: audit 1,222.455497 s;
final 158.40 s (fresh reproduction v2); other lanes 0.
