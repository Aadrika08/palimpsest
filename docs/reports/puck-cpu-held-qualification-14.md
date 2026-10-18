# CPU qualification 14: first accepted held four-import route

**Runtime14 completed normally in 202.54s, and its independent v14 audit passed.**
Under missing-import policy v5, the held CPU worker imported, in order:

- numpy 2.2.5
- torch 2.9.0+cpu
- torchvision 0.24.0+cpu
- mujoco 3.3.6

All 32 declared-absent and 4 hidden names were requested and denied, and nothing
else was. Source, input and staged custody held. The outcome is
`AUDIT_PASS_IMPORT_ROUTE_ONLY`, and the independent outcome review is
`PASS_IMPORT_ROUTE_OUTCOME_RECORD_ONLY` with no findings.

**What this establishes:** the held import route only.

**What it does not establish:**

- runtime qualification (`runtime_qualified` stays false)
- numerical, model, physics, renderer, operator, inference, study, collection or
  release acceptance
- full native-closure coverage
- reproducibility on another boot or stage
- any timing guarantee

All seven release gates remain open; no real episode or renderer has run.

## Sequence (all once, boot `7f875223…`)

1. **Source change.** Runtime11 failed on the 180s deadline after policy v5 had
   succeeded, and the user chose to raise the time limit. Source `f05bd69` adds
   preparation03 and epoch 14, with qualification clocks of 360/375/390s and the
   worker's own deadline at 360s. Source review 04 approved it, with guard logic
   unchanged.
2. **Preparation03 (v13).** It prepared in 26.2s, and its independent audit
   passed ([packet](puck-cpu-held-preparation-03/)).
3. **Controls.** Controls review 01 returned GO at CONTROL `eb34d5c`.
4. **Admission.** The pre-admission guard passed. Admission14 was
   `DATA_ONLY_ADMITTED` in 20.4s, with peak 34,337 held files (limit 40,000), and
   its independent review was GO. The pre-observer guard then passed.
5. **Runtime14.** Observer exit 0 in 202.77s. Supervision completed with no
   surviving processes, and peak RSS was 845MB.
6. **Audit.** The v14 audit passed in 12.9s.
7. **Outcome.** The collected outcome is `AUDIT_PASS_IMPORT_ROUTE_ONLY`, and the
   independent outcome review is PASS.

## Timing

| Import | Seconds |
| --- | --- |
| numpy | 8.7 |
| torch | 21.5 |
| torchvision | 103.2 |
| mujoco | 30.5 |

Worker entry returned at 192.2s, and the parent returned at 202.5s against the
360s limit, a margin of about 157s. Guard checks took about 132s of the 190.6s
measured: custody 81.4s and bindings 49.6s. The original 180s limit is still not
met; this run passed only under the extended clock.

## Next (milestone 1)

Separately qualify the finite public operator/renderer route and produce the
first real episode bundle. The offline census on branch
`research/public-episode-census-v1` sizes that work: 308 modules to register,
10 new declared absences, git/metadata policy for diagnostics, and child
processes. Guard cost scales with native libraries, so the episode allocation's
clock must be sized the same way.

Evidence: [packet](puck-cpu-held-qualification-14/) (169 artifacts, verified
against originals). Controls and reviews are in
`docs/plans/puck-cpu-held-qualification-14*`.
