# Qualification 11 (packet 11b): CPU runtime import route on preparation02

Goal: one separately admitted, observed and independently audited normal
four-import completion under missing-import policy v5 (epoch 11). The run consumes
the accepted preparation02 forest. All seven release gates stay open.

Packet d83dab3 was reviewed NO-GO and was never invoked: the reboot destroyed
preparation01's tmpfs forest. Preparation02 (v12, approved source `8f3a138`) then
ran once at boot `7f875223…` and was accepted. Its evidence commit is `facc2a7`:
- result `4ef13965…`, stage `/tmp/palimpsest-puck-cpu-held-02`;
- roots dev 55, inodes 10400–10403;
- audit v12 `fe155208…` and preparation01-shaped CLI record `50e452aa…`.

This packet reuses d83dab3's paths and controls. It changes only what preparation02
requires and fixes the review-01 findings:
- **Configuration:** relative to d83dab3, only stage_parent, the qualifier source
  pin (8f3a138) and the four preparation02 acceptance pins change. Bytes are
  compact canonical. Before any freeze, the configuration was validated offline
  with the parent's `validate_configuration` and `validate_preparation_acceptance`
  and the auditor's `configuration`, `preparation_epoch` and
  `historical_acceptance` (review-02 Important 2).
- **Runner:** binds preparation02 through the current auditor (v12 config,
  outcome, prepbase, namespace command, `historical_acceptance`). It keeps the
  legacy authenticated reader for Held, plan, forest and baseline, whose
  functions are identical.
- **History:**
  - Preparation01 is recorded as superseded: stage lost, not required, and
    unable to satisfy epoch 11.
  - Attempts 01–10 and admissions 10-01/02 remain consumed.
  - d83dab3 is recorded as never invoked (39 absent outputs, a byte-identical
    port of review 01, and Git-object pins in the freeze).
  - The 35 empty directories in the historical runs must stay empty (M3).
- **Distinct names:** the 11b /tmp outputs (`/tmp/palimpsest-held11b-*` and
  `…-11b-admission-01` / `…-11b-audit-01`) keep d83dab3's absence evidence
  meaningful.

Observed history: RED had 33 cases, 7 errors and 26 passes (the new
preparation02, unexecuted, preparation01 and empty-directory helpers were
missing). GREEN: all 33 pass. A first history-impl run failed on a template-name
literal before it edited the runner; that failure is retained. Fabricated and
changed cases are refused at authenticated hash pins (immutability), not by
semantic predicates (M2).

Next steps:
1. Freeze and derive the fixed wrapper, envelope, corrected guard and tools.
   These add the C1 stage/boot guard before every one-shot step, and I1/M1 in
   collect-outcome.
2. Run the metadata-only self-check and the entry-ceiling model.
3. Independent controls review, then push.
4. One admission, one runtime and one audit under unchanged 180s/2GiB limits.
   The preparation02 stage is never touched by these controls except through
   those guarded steps.
