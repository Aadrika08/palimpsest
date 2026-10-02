# M6 puck construction gate v3 — prepared, not executed

This gate precedes the separate ten-owner mechanics gate in the
[pushing protocol](m6-puck-pushing-protocol.json). It admits exactly two fresh
serialized processes. Each constructs the pinned checker environment, compiles
the exact derived thin-disk XML once, atomically installs it, applies the same
authored mechanics layout 5990 at time zero, and retains both 128×128 RGB camera
images. The existing upstream constructor also compiles its baseline and renders
its reset observation; the gate does not call `env.step` or `mj_step`. It runs no
policy, teacher, training or mechanics episode.

The [v3 construction protocol](m6-puck-construction-v3.json) pins the module, parent
protocol, upstream revision, constructor arguments, runtime and limits. Compare
the two complete native model/data hashes, model/profile identity, qpos/qvel/
zero-control/zero-force state and retained camera hashes. Require zero time and
unchanged state after explicit rendering, clean old/new renderer disposal, no
global control callback, no surviving exact child PID/process-group identities,
and unchanged source hashes. A mismatch is a retained failure, not a reason to
relax equality or retry. Native determinism and successful compilation remain
unmeasured until the approved execution passes.

The [v1 launcher failure](../reports/m6-puck-construction-v1.md) and
[v2 pre-install admission failure](../reports/m6-puck-construction-v2.md) remain
retained with their original protocol and raw outputs. V3 changes the module
pin after separating shared native array/binding/quaternion validation from
the authored task goal domain. Generic owner admission accepts only the pinned
upstream constructor domain ±5.5; `native_state` still requires the authored
task goal within ±5. The fixture with goal `[5.25, -5.25]` reproduced v2's failure
before this correction and now reaches the authored reset; values beyond ±5.5
and nonunit quaternions still fail admission. All 58 focused pure checks pass.
This is fixture verification, not successful native construction. The original
task/XML/layout, two owners, zero steps, comparisons and budgets are unchanged.
Use a fresh v3 output and reviewed launcher, with the inner verifier alone
holding the lifetime writer lease.

Per owner: 60 seconds; parent internal bound: 150 seconds. The retained outer
launcher must run `timeout --signal=TERM --kill-after=15s 180s` around the script,
inside existing `bounded_process(..., timeout=200)`. This preserves separate
owner and outer cleanup bounds. Logs are capped at 1 MiB each; the complete gate
has 64 MiB storage and a 1 GiB free-space floor. Native model/data containers are
each capped at 8 MiB, each camera file at 64 KiB, each JSON at 4 MiB. No model
assets are required. The script requires a fresh output path and exact committed
HEAD argument. Root must review and grant the serialized actual slot first.

Proposed child-parent command, to be placed in the retained outer launcher:

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/verify_puck_construction.py \
  --repo . --expected-commit FROZEN_FULL_COMMIT --output runs/NEW-CONSTRUCTION-ROOT
```

Installation validates the fixed compiled delta, named ordering, addresses,
dimensions, collision bounds, inertia, actuator and camera transforms, and cached
owner fields. Staged renderer/scene failures leave the old owner intact and close
the new renderer. An old renderer's close failure after the commit is terminal;
the caller still owns the new renderer and must close it. The gate retains both
handles and checks their native contexts are freed independently.

The authored reset adapter accepts one exact layout and no repeated reset. It
stages new data, temporarily applies the allowed joint-range/colour/goal-site
arrays, calls `mj_forward` once, then commits data and caches. On failure it
restores the model arrays and leaves the old data/caches intact. The reset adapter
does not sample RNG, step, render or invoke upstream reset. Future Engine wiring
must call it after the existing upstream reset, which rewrites XY locks.

The frozen XML's two-value cylinder site size retains MuJoCo's unused third
component of 0.005. The validator checks that compiled default without changing
the XML or puck parameters. [MuJoCo 3.3.6 site defaults](https://mujoco.readthedocs.io/en/3.3.6/XMLreference.html#body-site),
[pinned parser](https://github.com/google-deepmind/mujoco/blob/3.3.6/src/xml/xml_native_reader.cc#L1742).

This is construction, identity and resource-lifecycle evidence only. It does not
establish contact stability, pushing, learned capability, Engine integration,
snapshot/replay qualification or physical behavior. No Engine, UI, worker,
snapshot or replay source is changed in this slice.
