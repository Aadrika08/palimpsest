# Component-wise restore ablation (authority_component_v1)

**Status: drafted, not run.** Scope, the `final` budget lane, the 16th arm, a smoke run on seed 1000 and a 64-tick
horizon were approved by the owner on 2026-11-23 (recorded in `protocol.json` `authority.owner_decisions`). The run itself needs, in order: these tests passing, an independent AI review (recorded as AI
review, not human acceptance), and an explicit owner run GO written to `go.json` as
`{"go": true, "protocol_sha256": "<sha256 of protocol.json>", "by": "...", "date": "...", "words": "..."}`.
`runner.py` refuses to run without a matching `go.json`. Nobody but the owner writes that file's GO.

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
