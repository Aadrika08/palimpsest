# M5 bounded development acquisition batch

This is a prepared runner, not a batch result, held-out protocol freeze or R2
qualification. The first manual pilot remains separate: its collected actual E
has support local=1 changed/paired=1 unchanged, so `fit(E)` returns empty U under
the unchanged four-support threshold. Pilot report:
`runs/m5-first-history-20261002/report.json`, SHA256
`86b60449c5c097b5cdd48a1620d8e277c47b8b838752e9626c1dd6b3d7cf31ab`.
The pilot is not counted toward either new history.

`scripts/acquire_memory_history.py` fixes eight fresh UUID recording jobs: seeds
0,1,2,3 for local_cue, then the same four seeds for paired_cue. Each is a fresh
manual CPU development-history/change case with unknown M, empty E/U and one
episode. These are distinct seeded simulation acquisitions, not a claim of IID
biological samples or qualified transfer. They counterbalance the declared
side/relation and fact-order bits; these four seeds do not span all eight
three-bit identifier permutations. The existing case/world/Engine/replay code is
unchanged. Held-out seeds, replay, branches, parameter tuning and retries are absent.

All jobs use exactly the previously declared public acquisition schedule: north
heading, x=-1.3 lane, lower y=-1.1 and upper y=.6, cue/reference tick300, return
at330, max600 control ticks, velocity .65 and existing proximity/heading checks.
Access remains `privileged-manual-pose-supervision`; the action helper sees only
that public schedule, actual pose and tick. Regime, hidden gate mechanism, truth
and U never guide its actions. Coverage stops the driver after the return phase;
gate/cue failures are recorded afterward and make it fail. Operator blindness,
external knowledge and source authenticity remain unverified.

The parent launches only one child at a time through existing `bounded_process`:
160-second child deadline, 150-second internal wall bound, 192 MiB recording
quota, 1 MiB per-stream logs and its existing TERM/KILL process-group cleanup.
No failed/gapped run is retried, replaced or removed. Normal Engine cleanup is
attempted; timeouts and cleanup errors remain explicit. Worst-case recording
quotas total 1.5 GiB plus bounded logs/reports. Runtime execution requires the
exclusive slot; preparation and `--plan-only` launch no simulator or model.

Each manifest binds its exact case, acquisition driver SHA, public schedule hash,
and batch protocol. The parent independently exhausts the existing artifact
reader for terminal counts and chunk hashes, checks source/lock/upstream identity,
exact initial unknown bank/empty E/U, recorded case/controller/quota, consecutive
sensor coverage, scheduled trigger and declared gate outcome. The collector
additionally reconstructs cue triggers, validates every complete bank/U and links
nearest actually observed before/after evidence. Neither the schedule nor private
geometry manufactures E. Admission fails on incompatible identities or missing
coverage. Source identity is retained at start/end; mutation makes the batch
incomplete.

Each regime's collector receives all four intended run paths separately.
`collect_history` alone constructs E and calls `fit(E)`; regime, case, source
metadata and evaluator truth do not enter fitting. A rejected source leaves a
rejected group. Admitted gaps/partial histories retain full linked audit output and
abstention, and remain incomplete. Outputs include per-child reports/supervisor
logs, both collector bundles and their SHA256 hashes, E/source hashes, observed
support and actual U rules. Full recordings remain available. Batch completion
means admitted coverage, not a required learned relation or research effect;
empty U is an honest result. Frames are never independent samples.

The collector aggregate input cap is now 512 MiB per history because four
84.3 MB measured pilot-size runs exceed 256 MiB. Its protocol hash binds the cap;
all existing 16-run, E1024/4MiB and whole-bundle8MiB bounds remain unchanged.
Oversized inputs reject before reader exhaustion; there is no truncation.

Pure checks:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_memory_acquisition test_memory_history test_memory_cases test_memory_experiment test_memory_task test_memory test_records -v
```

Prepared execution command, **not run in this slice** (output must be new):

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/acquire_memory_history.py \
  --repo "$PWD" \
  --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn \
  --output "$PWD/runs/m5-acquisition-batch-20261002"
```

Add `--plan-only` to inspect the fixed jobs without runtime work or output writes.
Review/commit/source freeze and exclusive runtime allocation remain pending.
