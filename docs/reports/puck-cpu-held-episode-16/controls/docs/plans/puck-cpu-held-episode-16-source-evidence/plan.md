# Allocation 16: one held public manual episode on preparation04

Goal: a single separately admitted, observed and independently audited held
episode. Worker A records the source episode and worker B replays it from A's
read-only output:

- seed 7, 48 ticks, actions at ticks 0 and 24;
- renderer criteria as frozen in the source (Mesa llvmpipe, EGL);
- 42 declared-absent names and 4 hidden names;
- clocks: parent 1200/1215/1230s, each worker 600s, observer 1260/1275s;
- run ids `6bdba8da…` (source) and `3cdc557f…` (replay), distinct from
  characterization-04's.

All seven release gates stay open.

## History

- **Attempts 01–11 and admissions 10-01/02 and 11b:** recorded exactly as in the
  reviewed-GO attempt-14 packet.
- **Runtime14:** accepted import route only (`AUDIT_PASS_IMPORT_ROUTE_ONLY`;
  controls `eb34d5c`, outcome `4fd4f68`). It consumed admission14 and
  preparation03.
- **Preparations 02 and 03:** accepted and consumed. Their stages were retired by
  `retire-consumed-stages.py`, with lstat identity and a content census recorded
  first (`docs/reports/puck-cpu-held-preparation-04/records/retire-consumed-stages.json`).
- **Characterization-04:** accepted observation; audit PASS by `1608a3d7`;
  archive `PASS_ARCHIVED_AND_BOUND`.
- **Preparation04 (v15):** accepted.
  - result `a76b6148…`;
  - stage `/tmp/palimpsest-puck-cpu-held-04`, roots at device 55, inodes
    317249–317252;
  - boot `7f875223…`;
  - audit v15 `987224d8…` and CLI record `3523c1da…`;
  - allocation-16 acceptance PASS.
- **d83dab3:** never invoked.

## Method

This packet ports the attempt-14 packet. The attempt-14 lineage (`4fd4f68`) is
merged byte-identically as `75df4db`.

- **Configuration (`port.py`):** the exact shape that `run_puck_cpu_held_episode.py`
  and `audit_puck_cpu_held_episode.py` validate, using the parent's
  `canonical()`. Before any freeze, both parent validators and both
  episode-auditor validators accept it (`canonical-preflight.py`).
- **Admission (`admission-port.py`):** the attempt-14 history functions with
  counted edits, plus new history for runtime14, admission14,
  preparation02/03 retired, characterization-04 and preparation04. It re-hashes
  the preparation04 staged forest twice, the SITE, the v6 natives, the EGL
  vendor JSON and the interpreter prefix.
- **History:** RED first, then GREEN.
- **Freeze:** if consumed `docs/reports` packets would push the admission's Held
  entries or bytes near the 40,000-entry / 2 GiB ceilings, they are bound through
  their committed evidence-index hashes (user decision). The files the history
  checks read stay individually pinned.
