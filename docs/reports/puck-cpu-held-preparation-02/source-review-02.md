# Source review 02: CPU preparation epoch 02 for epoch 11

**Range:** `1126b71..8f3a138` on `research/puck-cpu-optional-import-contract-v2`
(PR #177). **Reviewer:** separate read-only review agent. **Verdict: APPROVE**, with
no Critical findings.

## Confirmed

- **Distinct identity.** Preparation02 has v12 kind, version and allocation id, its
  own output `runs/puck-cpu-held-preparation-02` and a `-02` stage parent. Its output
  and stage are reserved by existence checks, and the observer creates them exclusively.
- **Epoch 11 binds only preparation02.** It requires the v12 prior and outcome, audit
  v12 with allocation 12, pinned auditor `04192a3b…`, the 02 transport, an identical
  stage, root and 24 sources, and dev/inode staged roots in both parent and auditor.
- **Old epochs unchanged.** Epochs 1–10 and preparation01 are unchanged. An AST diff
  of the prepare branch against the preparation01 qualifier shows only the output
  name and outcome kind changed.
- **Pins are consistent.** The parent's auditor pin equals the current auditor bytes.
  There is no circularity: the auditor accepts preparation02 by its own bytes.

## Procedure requirements (Important)

1. Run from `/home/utkarsh/.codex/worktrees/0071/brain` with root unchanged. Inputs
   keep preparation01's candidate; change only kind, version, id, stage and sources.
2. The externally observed auditor CLI record must exactly match preparation01's shape:
   - fields `{kind, command, observed_returncode, elapsed_seconds, published, stdout, stderr}`
   - the bare 15-element argv
   - byte-identical stdout and published bytes
   - empty stderr, audit < 120s, record < 130s

   A malformed record would consume runtime11. Validate the epoch-11 configuration
   offline with `validate_preparation_acceptance` and the auditor's `configuration` +
   `preparation_epoch` before freezing.
3. Re-derive the attempt-11 controls on preparation02 and add boot-id and staged-root
   stat guards before every one-shot step.

## Minor

- The auditor has no negative tests for preparation02 acceptance. Tests may be added
  later without forcing a preparation03.
- Custody binds dev/inode, not boot; the external boot-id guard covers this.
- The runtime11 timing margin is thinner by about 5s from declared-absence rechecks
  (estimate).

**Reviewer runs:** 903 unit and 8 integration cases passed. A v12 configuration
derived from preparation01 passes the parent and auditor validators offline. At
boot `7f875223…`, all input, native and alias pins are unchanged.
