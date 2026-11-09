# Puck v4 S1 attempt 2 — execution manifest (prepared, not run)

Protocol: Amendment 1, sha256 `8d8529712614292ba470ce88f60aaad7d061a1732851627f3be0e1e8c0d1b20f`
(base `f885fc8d…`). Attempt 1: `docs/reports/puck-v4-s1-2026-11-08/` (refused, 0 collisions).

- **Launcher stages:** `S1-attempt-2` (RuntimeMaxSec 655, worst case 660 CPU-s) and
  `S1-attempt-2-audit` (RuntimeMaxSec 115, worst case 120). The launcher refuses a repeated
  (lane, stage) key.
- **Admission GO:** stage `S1`, scope `S1`, `protocol_sha256` = Amendment 1 hash,
  `supersedes_protocol_state` exact. D2 GO (scope S1) reused. Launcher GOs name the stages above.
- **Attempt ledger:** the constant `ATTEMPT_2_LEDGER`
  (`palimpsest-authored-test-evidence/puck-v4-s1-attempt-2-ledger`); execute refuses any other
  ledger and refuses unless attempt 1's base-protocol receipt is on record. The builder always
  excludes this ledger, so creating it cannot change the declaration.
- **Allowlist binding:** the code allowlist must equal `amendment_1.change.non_scene_content_allowlist`
  at protocol load; the D8 audit checks every `non_scene_asset_mentions` row against the protocol.
- **Final-blocked rule:** any refusal of attempt 2, including a refusal before the attempt
  receipt is written (the launcher has already reserved the stage), ends puck v4.
- **Frozen window before execute:** all agents stopped; no repository edits; fresh `ls-remote`
  compared with the reviewed advertisement (no fetch); declaration rebuilt with
  `--compare-manifest`; `--calibrate` with the D2 GO; timed dry check with the exact ledger,
  output and calibration record showing no blockers and projection + preflight <= 528 CPU-s.
