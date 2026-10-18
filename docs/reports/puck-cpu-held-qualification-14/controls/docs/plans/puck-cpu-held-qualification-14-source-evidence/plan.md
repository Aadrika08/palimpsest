# Qualification 14: extended-clock CPU import route on preparation03

Goal: one separately admitted, observed and independently audited normal
four-import completion under policy v5, with the user-approved extended clocks:

| Component | Clocks |
|---|---|
| Parent | 360s normal / 375s child-hard / 390s hard |
| Worker | 360s |
| Observer | 400s normal / 415s hard |
| Observer wrapper | ≥ 440s |

All seven release gates stay open.

History:
- **Runtime11** (packet 11b, controls `27780dd`, outcome `92de987`) is
  `FAILED_CONSUMED`. The parent hit its 180s deadline during `import mujoco`;
  the policy v5 imports returned through Torchvision.
- **Admission11b** was admitted and consumed by that single runtime.
- **Preparation02** was accepted and consumed by runtime11. Its stage is
  retained and is never read or stat-checked here.
- **Preparation03** (v13, source `f05bd69`, evidence `44e9712`) is accepted:
  - result `c7e6c0e8…`;
  - stage `/tmp/palimpsest-puck-cpu-held-03`, roots at device 55, inodes
    43194–43197;
  - boot `7f875223…`;
  - audit v13 `c5c7da42…` and CLI record `53b7f6e5…`.
- Still recorded: attempts 01–10, admissions 10-01/02, the never-invoked
  d83dab3 packet and preparation01 (superseded).

This packet ports the reviewed-GO 11b packet to distinct `qualification-14`
names. The 11b packet, its outcome and the preparation02 evidence came in through
merge `54c8b15`, byte-identical with their Git provenance.

Changes from 11b:
- **Configuration:** only kind/version/id 14, `QUALIFY14_LIMITS`, the -03 stage,
  three f05bd69 source pins and the four preparation03 acceptance pins change.
  Bytes are compact canonical. Before the freeze, the configuration passed the
  parent's `validate_configuration` and `validate_preparation_acceptance` and the
  auditor's `configuration`, `preparation_epoch` and `historical_acceptance`
  (review-04 Important 2).
- **Admission:** binds preparation03, asserts the 360/375/390s clocks, and adds
  runtime11, admission11b and preparation02 history. Empty directories go from
  35 to 41 and process identities from 15 to 18.
- **Run controls, at freeze:**
  - the stage/boot guard is rebound to preparation03;
  - observer wrapper 440s with outer term 450s; audit and admission wrappers
    unchanged;
  - collect-outcome checks parent elapsed < 360, transport elapsed < 400,
    registration `deadline_seconds` 360 and each import below 360s.

Observed history RED: 41 cases, 9 errors / 6 failures / 26 passes (the
preparation03, runtime11, admission11b and preparation02 helpers were missing,
and the absence and empty-directory counts were stale). GREEN: all 41 pass.

Scope: import-route evidence only. No operator, renderer, physics, inference,
collection, protected inputs, studies, CI, cloud or rover execution.
