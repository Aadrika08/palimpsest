# Component-wise restore ablation (authority_component_v1)

**Status: ran once, 2026-11-23, completed.** Owner run GO recorded in `go.json` (protocol sha256 `b6e6e956...`;
`protocol.json` stays frozen, so its `status` field still reads as it did at GO). Attempt 1 ran at commit
`afb50cc` (tag `authority-component-v1-run`): 6/6 seeds and 96/96 rows completed, no refusals, no identity drift,
2,851 CPU-s (final lane: 3,450.84 of 7,200 used including the 441.07 CPU-s smoke run). Retained evidence:
`paper/evidence/authority-component-v1/` (raw per-tick arrays, 3.6 GB, kept locally under `runs/` with sha256s in
`arrays-manifest.json`). Paper numbers come from `paper/scripts/build_component_ablation.py`.

Outcome (descriptive, n=6, FLYNN sparse-navigation on CPU): stale recurrent controller hidden state alone changed the
first restored action (6/6) and restoring it alone repaired it (6/6), contradicting the pre-registered expectation
that no single component would. Stale observation, physics and retina state first moved the action beyond the 1e-6
tolerance at restored ticks 1, 2 and 5-10. Over 64 ticks (comparing qpos, qvel, ctrl, hidden, action, retinas and
revision; reward and termination not compared), stale wrapper fields changed nothing and stale application state
changed only the revision counter; the step between snapshot and post-step state consumed no RNG state. Restoring physics plus observation, hidden
and retina removed every divergence except that revision counter (6/6).

Question: the parent study's S1 unit showed that restoring physics alone changes the first FLYNN action, but not
which unrestored component causes it. This study restores 16 hybrid snapshots per seed (full, pose-only, seven
leave-one-out, six add-one-in, and observation+hidden+retina together) built from a source capture and a one-step-later donor capture, through the
production `Engine.restore_branch` path. See `protocol.json` for the fixed arms, harness checks H1/H2,
analysis rules, the 4,500 CPU-s ceiling and the stop rules.

Tests (pure logic; the real-controller smoke test is opt-in with `PALIMPSEST_COMPONENT_SMOKE=1`, uses non-study
seed 1000 through the CLI entry point; owner-approved, charged to the final lane):

```
../../.venv/bin/python -B -m pytest -q -p no:cacheprovider paper/studies/authority_component_v1/tests \
  --basetemp /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-<tag>
```

Run (after GO, from a clean checkout):

```
python -B paper/studies/authority_component_v1/runner.py --output runs/paper-authority-component-v1/<fresh>
```
