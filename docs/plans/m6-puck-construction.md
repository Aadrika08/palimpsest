# M6 puck construction gate v4 — prepared, not executed

This gate precedes the separate ten-owner mechanics gate in the
[pushing protocol](m6-puck-pushing-protocol.json). It admits exactly two fresh
serialized processes. Each constructs the pinned checker environment, compiles
the exact derived thin-disk XML once, atomically installs it, applies the same
authored mechanics layout 5990 at time zero, and retains both 128×128 RGB camera
images. The existing upstream constructor also compiles its baseline and renders
its reset observation; the gate does not call `env.step` or `mj_step`. It runs no
policy, teacher, training or mechanics episode.

The [v4 construction protocol](m6-puck-construction-v4.json) pins the module, parent
protocol, upstream revision, constructor arguments, runtime and limits. Compare
the complete native model hashes, defined native-data bytes, model/profile identity, qpos/qvel/
zero-control/zero-force state and retained camera hashes. Require zero time and
unchanged state after explicit rendering, clean old/new renderer disposal, no
global control callback, no surviving exact child PID/process-group identities,
and unchanged source hashes. A mismatch is a retained failure, not a reason to
relax the frozen v4 comparison or retry. Successful individual construction was
measured in v3; its strict full-native-data equality gate failed and stays failed.

The [v1 launcher failure](../reports/m6-puck-construction-v1.md) and
[v2 pre-install admission failure](../reports/m6-puck-construction-v2.md) remain
retained with their original protocol and raw outputs. V3 changes the module
pin after separating shared native array/binding/quaternion validation from
the authored task goal domain. Generic owner admission accepts only the pinned
upstream constructor domain ±5.5; `native_state` still requires the authored
task goal within ±5. The fixture with goal `[5.25, -5.25]` reproduced v2's failure
before this correction and now reaches the authored reset; values beyond ±5.5
and nonunit quaternions still fail admission. All 58 focused pure checks pass.
Those pure checks are fixture verification. The original
task/XML/layout, two owners, zero steps, comparisons and budgets are unchanged.
Use a fresh v4 output and reviewed launcher, with the inner verifier alone
holding the lifetime writer lease.

V3's [strict failed equality result](../reports/m6-puck-construction-v3.md) and
[complete byte/source map](../reports/m6-puck-construction-v3-byte-map.md) remain
unchanged. V4 is a prospective comparison revision for this same fixed scene
and MuJoCo 3.3.6 x86-64 ABI. The protocol pins the exact 162-field size-prefix
layout, complete embedded model hash, dimensions and sparse rows. It retains
both raw blobs/hashes and the exact within-owner pre/post-render data-hash guard.
Across owners it compares every byte except 15 `timer.duration` doubles, four
tail-padding bytes per 576-byte contact, and three sparse-array allocation tails
after the validated contiguous 50-entry extent (capacity 110). This excludes
exactly 1,344 bytes and compares the remaining 346,537 bytes exactly, including
prefixes, timer counts, contact fields, integration state and active sparse data.
No data is zeroed or normalized. Wrong format/ABI/model/length/dimensions/extent
or any other differing byte fails; new differences are not silently excluded.
This does not change native snapshot/restore validation or any puck runtime code.

Pure byte fixtures cover allowed regions and rejected mutations of all named
protected categories, plus malformed equal inputs on both sides. Synthetic
fixture model bytes have an explicitly separate test hash; they are not native
model evidence. The v4 gate still needs a reviewed source freeze and actual GO.

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
