# M5 remaining development: fixed profile source contract

Source implementation only, based on `5edc302`. The [approved continuation plan](m5-counterbalanced-development.md#approved-remaining-development-scope-3-october-2026) fixes forty remaining cells / ten four-cell chunks, all nine conditions and the fixed lower-goal-route estimand. No admission, model/native job, new control freeze, held-out access or acquisition is authorized here.

Extend only `scripts/verify_memory_counterbalance.py` and `scripts/verify_memory_counterbalance_comparison.py`, plus one focused pure test module. Keep current workers/readers, case generator, source preparation/goal move, Engine, sensors and controller unchanged. Historical B/C3/C4 defaults, job fields and scientific protocol remain intact; source-file provenance changes are new authoring identities and never rewrite old artifacts.

Admission has ten explicit `remaining-01` through `remaining-10` profiles, each with the exact four cells in the existing plan, stages source/policy-anchor/probe, twelve owners, 1,204 maximum ticks, 6 GiB allowance, 2 GiB floor, 64 MiB headroom and 1,980-second parent bound (12 × 160 + 60). Historical default B keeps its eight cells, 24 owners and 3,900-second bound. A profile digest determines the fixed cells/protocol; no arbitrary cell/schedule input, global monkeypatch or copied runner is allowed.

Comparison has ten matching fixed profiles, stages anchor plus the existing nine conditions, forty owners / 10,800 maximum ticks, 10 GiB allowance and 6,460-second parent bound. Core own/swapped/sham/no-U inherit the shared own selector and full strict C4 non-U guard; other five conditions retain declared resource/configuration differences. Target limit, dtype/device, visibility, evidence/gold, natural failure/censoring, no-event absence and null confirmation semantics are unchanged.

New comparison lineage is explicit bounded metadata: version 1; matching admission protocol SHA; absolute admission plan/report paths; exact SHA256 of each. It is mandatory in new comparison plans and runtime jobs, reconciled with every binding and current fixed admission validator. The plan and terminal report must independently admit that exact chunk, all unique source/anchor/probe joins, original restoration predecessors, registered SNP/worker/recording hashes and complete pin coverage. Caller-supplied binding hashes alone cannot replace the plan-level lineage. Legacy comparisons keep original B constants and reject new lineage arguments/fields.

`make_plan`/`load_bindings` accept this metadata only for a remaining profile. `verify_binding` requires the separately frozen expected lineage for that route, while its historical default remains unchanged. CLI selects only named fixed profiles; new comparison preparation additionally requires exact admission plan/report SHA arguments. No future oracle gold or unacquired SNP is placed in a prepared plan. Historical repo/path checks remain exact; a future admission and its comparisons execute from one reviewed physical authoring path rather than weakening old B path admission.

Pure checks must prove the forty-cell complement and ten profiles, original protocol/default equality, real matching/rejected admission and comparison validators, cross-chunk/substituted lineage rejection, full strict-core negative guards, and null/no-event parity. Fixtures may model future metadata but are never actual acquired evidence. No new producer data is generated.

The smallest later control review is chunk 1 only: s24/local/null, s24/local/no-event, s24/paired/change, s24/paired/null. Freeze twelve fresh admission IDs/source-case pins and the finite outer cleanup/inventory contract first. Its passed immutable report would then permit a separate forty-owner comparison plan with exact lineage pins. This document prepares neither controls nor runtime; root review and separate GO remain necessary.

The historical comparison protocol's admission-helper SHA remains the original
`ffb7fa9d3b84441c6fa05945b893d4c4028481502d80355f8e951e5238d30927`
for old-contract readmission, not a claim about current execution bytes. Current
executor `source_identity` independently binds actual helper/driver bytes and is
recomputed before/after execution. New profiles additionally require their protocol,
plan and job executor helper pins to equal actual current helper bytes; pure
validators reject stale/fabricated executor hashes. Old raw records are unchanged.

Pre-execution checks use `PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest tests.test_memory_full_development -v`, without writer leases, model/native jobs or retained input dependencies. Final result: six tests passed in 16.309 seconds, no skips. The first draft fixture raised `KeyError: 'task_pass'` by asking `condition_readout` for the evaluator field; corrected to the helper's existing `worker_task_pass`. The transcribed first error and captured final check log are retained under ignored `runs/full-development-source-check/`. This fixture correction does not alter runtime behavior or historical results.
