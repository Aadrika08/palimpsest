# M6 loaded body calibration: development runtime

This slice adds **Calibrated wheel compensation (development)**, a manual CPU/checker profile. It loads a fixed simulator fit into a deterministically constructed body with left motor gear `3 * .8` and unchanged right gear, wheel radius and track. It does not fit or update coefficients online, change odometry, implement learning, or qualify physical actuation or navigation.

## Evidence and fixed identity

The canonical in-code artifact in [body_profile.py](../../src/palimpsest/body_profile.py) retains the accepted gain report SHA256 `9d2cd4729d32f84b490db3a6726764111989fcc80be74c7a2ba44a97cb419331`, diagnostic protocol SHA256 `bf883b89156201ccd35659fa7971fda507876e357c733356ed3eec59bac760f0`, baseline model SHA256 `c4d30fef8fbe05739e72e762d10d2dc435c1c831993a32d0662560d494b158e5`, and perturbed model SHA256 `bf3ca4b0d32600444e0f23e658c790da50a7675fb3c26fee8f9b0a16e0839d67`. No ignored raw report must be present to open the profile. The fit values and rejection bounds are copied exactly, rather than refitted on runtime observations.

The baseline gains are `[14.878897911022118, 14.878897948225164]`; loaded measured gains are `[11.851776561760323, 14.374415787256368]` rad/s per control. Ratio bound `1.5` and control limit `2` remain unchanged. Fit development bounds retain 20% relative RMS and 20% between-trial agreement, with 400 accepted pooled samples. The observed agreement ratios are 11.9500% and 3.13385%.

[The separate six-trial compensation report](../reports/m6-body-compensation.md) records the earlier fixed-command ±.3 simulator comparison. Its report SHA256 is `f5a5d617ceb4dbddf32e7e589748f6245c041312f60dbb4147ac985b170d6856`. That evidence supports the narrow straight-motion development comparison; it did not test this product profile, native continuation or executable replay. Mixed controls, transient response, held-out bodies, task performance and physical motors remain unqualified.

## Runtime contract

Reset uses the already authored memory-world obstacle layout without its task supervisor or gate schedule, starting at `[-3.5, 0, 0]` with goal `[-3.5, 3]`. The historical calibration world PROFILE SHA `ed6d7996b1c5dd412621533ebc87c0712ef3ed618031167774f27e313371379c` remains in the artifact. Runtime setup separately pins authoring source `508d7c53cf78e8a26a2c459e2b6e2a02c8c0823535005a19668a31717f0dbb12` and semantic PROFILE SHA `cbc3f2cfbcf0ef25efb260f21771fe0ac52f4bd0b1a78b8e0dfd64378febe753`. Only the three declared source-metadata fields are excluded from the latter; altered authoring source or geometry still rejects. Full current world PROFILE, including memory/sensor producer hashes, is recorded separately in manifest and a provenance event. The recorded initial world and `body_loaded` event describe the actual profile world and motor gears. The normal seeded reset is followed by explicit deterministic authoring before any step or initial snapshot.

Manual command history retains nominal `[velocity, heading]`. The exact pinned converter gives nominal `ctrlL=2v-heading`, `ctrlR=2v+heading`. `compensate_wheels` applies the loaded nominal/measured gain ratios; the proven inverse produces an effective action with an exact float32 control roundtrip. There are no direct runtime writes to `data.ctrl`, hidden clamps or fallbacks. Saturating nominal/effective requests reject before physical stepping. Keyboard magnitudes are nominal velocity `.3` and heading `.2`; all nine held-key combinations pass the control limits. Other profiles retain their existing keyboard values.

Action replay supplies the recorded effective action once, validates it against the retained nominal command, and does not compensate it again. Manual policy replay executes the same nominal commands through compensation. Both produce the same semantic body events, encoder cursor and contact arrays; no replay-mode flag enters body state.

The bounded `body_state` holds only fixed identity, episode/tick cursor, phase (`loaded` or `compensating`), previous raw hinge angles and native time. It has no history buffer or fitted updates. Pause/resume retains it; reset clears the episodic cursor and nominal intent while retaining the immutable loaded fit and gear identity. A failed contact/coverage/control/rate measurement fails execution and retains its interval evidence.

## Contact and recording contract

The shared read-only `mjcb_control` probe requires MuJoCo 3.3.6, Euler, `.002` physics interval, ten stages per `.02` control tick, and contact/actuation enabled. It refuses a pre-existing callback and removes its own callback in `finally`. The exact base-descendant body/geometry partition is validated and named once in manifest/event evidence.

Each tick retains all ten pre-control contact caches plus the unchanged final cache. The latter refers to the last pre-integration stage, rather than a new endpoint evaluation. Ground support is allowed only for the three named rover wheel geoms against floor. Unexpected robot/self/body-world contact rejects. All world-only pairs remain recorded and may move; this is neither a stationary-world nor a continuous-collision claim.

Numeric NPZ tick fields use fixed `11 × 128` contact slots: IDs `int16[...,2]`, distances `float64`, classes `uint8`, counts `int16[11]`, cache times `float64[11]`, and actual stage controls `float64[10,2]`. Counts delimit valid entries; every unused slot is zero. Classes are 0 padding, 1 world-only, 2 allowed rover-floor, 3 unexpected robot. Actual counts over 128 reject without truncation. Raw encoder before/after/increment, measured dt and nominal action/control are also retained. Concise JSON events carry summaries and state, preserving the existing 32 MiB event-reader cap. A rejected interval retains its bounded full packet instead of producing a successful numeric tick.

The worker admission estimate includes 32 KiB numeric/body-summary allowance plus 4 KiB overhead per tick. Existing per-write aggregate, recording, snapshot, log and free-disk checks remain active. Full failure packets are capped at 512 KiB. This is bounded storage, not a motion-safety guarantee.

## Native continuation and compatibility

Body application snapshots alone use schema 5 with `body_state`; inactive profiles keep the exact schema-4 application form and existing legacy migrations. Snapshot container version stays 1. A conditional body identity is added only for this profile. Motor gear is immutable model identity, not an added mutable-model array.

Application and native restore validate the fixed profile/artifact/model identity, typed bounded state, paused phase, episode/tick cursor, and exact raw encoder/time equality against staged native data before replacing the destination. Capture/restore require no active global callback. Renderer rebuild follows the existing native restore order and introduces no `mj_forward`. Replay additionally binds the shared body module source and compares every raw body numeric array, including counts and padding, in both modes.

## Prepared checks and pending actual protocol

The fixture-only checks exercise exact ±.3/zero mapping, all keyboard combinations, saturation, callback coverage/cleanup/contact rejection, overflow, deterministic padding, malformed application/native cursor rejection, once-only action replay, application restoration, pause/resume/reset and unchanged legacy application form. The diagnostic protocol SHA remains unchanged after helper extraction.

```bash
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover -s tests -p test_body_profile.py
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover -s tests -p 'test_verify_body*.py'
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover -s tests -p test_engine.py
```

Actual runtime and UI verification is **pending parent review, source freeze and exclusive execution authorization**. Proposed bounded development gate, without retries or changed thresholds:

1. Create one real manual CPU/checker source through `Engine.open`, seed 1, this profile, EGL and two CPU threads. Register its initial native snapshot before control. Use the existing storage lease and bounded-process watchdog, exclusive output, source/artifact/script hashes and explicit terminal cleanup.
2. Set nominal `[.3, 0]`; warm run1 + pause + 23 steps gives exactly 24 ticks, then capture a native snapshot. Continue run1 + pause + 3 steps under the same command for exactly four ticks and retain complete raw arrays and cameras. Run/pause is included in this accounting, with no extra undisclosed tick. Reset to seed 1; assert fresh body cursor, same fixed gear/fit and zero nominal intent, then take eight nominal `[-.3, 0]` ticks. Clear input and close normally. Early failure remains a failed gate.
3. Open a fresh same-profile owner after source close, restore the paused snapshot, and take the identical four commands. Compare body state, raw encoder/contact/control arrays and all existing physical fields using the established `1e-6` floating tolerance and exact integer/camera equality. Check native identity, callback cleanup and normal owner disposition.
4. Close before each next owner. Run both executable actions and manual-policy replay from the registered initial snapshot; require complete semantic-event/tick parity, including reset and every body numeric field. Require unchanged source files and immutable source evidence, normal exit and no owned live descendants/listener.
5. Separately build/typecheck the small UI profile/keyboard glue and exercise the real profile, pause/reset/snapshot/replay through the existing authenticated UI/API workflow. A source-only fixture pass does not qualify any of these pending actual gates.

This gate would qualify only loaded-calibration software execution and continuation on its measured simulator/runtime. It would not establish a new gain fit, online adaptation, improved mixed-command navigation, held-out task performance, biological mapping or physical motor safety.

Preparation check result (2026-10-02, uncommitted slice based on `96ca2114dbce37d75cd42bd4acf23a07bc0803a0`): 10 body fixture checks, 13 shared diagnostic/compensation checks, 16 Engine checks and 7 worker checks passed. Replay validation passed 2 checks with 4 actual-runtime opt-in checks skipped; profile validation passed 1 check with 1 actual-runtime opt-in check skipped. Total: 49 passed, 5 explicit skips. Python compilation and `git diff --check` passed. The actual new profile/native continuation/replay and UI build/browser gates above remain pending; these results do not substitute for them.


The prepared harness is [verify_body_runtime.py](../../scripts/verify_body_runtime.py). Its pure raw-packet/accounting regression is [test_verify_body_runtime.py](../../tests/test_verify_body_runtime.py); one check passed without loading a simulator or launching an owner. Syntax/help and diff checks passed. Product code remains frozen while this harness is reviewed.

After parent review, commit/freeze and exclusive actual authorization only:

```bash
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 ../lab-hardening/.venv/bin/python scripts/verify_body_runtime.py \
  --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn \
  --output runs/m6-body-runtime-development-20261002
```

The four child watchdogs are 180 seconds each. Fixed limits are 64 MiB per recording, 1 GiB aggregate output, 1 GiB free-disk floor, 1 MiB report/result/read bounds, 1 MiB per native log stream and 8 MiB concurrent headroom. The parent holds the existing storage lease; children share its budget without taking another lease. The source performs exactly 36 ticks (episode 0: 28, episode 1: 8); the fresh restored owner records episode-0 ticks 24–27; each replay must compare all 36 source ticks. Before valid restore, malformed typed encoders and a finite application/native encoder mismatch must each reject with destination snapshot hash and native model/data addresses unchanged.

Source recordings, the progress snapshot, loaded assets and harness/runtime hashes are checked for immutability. The harness retains failed child/result/supervisor/native logs and pending stage rows. It creates no server or listener. Finite 0.25-second descendant samples and final PID/start-time checks establish only the observed owned-process cleanup. The existing `bounded_process` performs TERM/KILL cleanup on its owned process groups after leader exit; this harness does not invent stronger signal-disposition evidence or claim to observe every transient process. Normal child return code 0, recording completion, Engine cleanup and callback removal are required; unobserved transient descendants remain a sampling limitation.


V1's single zero-tick startup rejection is retained in [its report/index](../reports/m6-body-runtime-v1.md), committed as `8e42cef` after frozen source `fd2d70d`. The source-inclusive historical world PROFILE pin was stale after an optional runtime-case authoring change. V2 separates historical fit-world identity, actual authoring source and semantic geometry as described above. A pure regression accepts memory/sensor source metadata changes while still rejecting changed geometry, undeclared metadata exclusions, authoring source or malformed full PROFILE identity. This fresh-setup compatibility rule does **not** broaden historical replay compatibility: replay retains the existing strict same-software source checks, including memory/bridge modules. The new guard does not alter commands, fitting, settling, control/rate/contact limits or scene parameters. A fresh actual v2 invocation is pending review/freeze and explicit authorization; the v1 failure is not reclassified as a pass.
