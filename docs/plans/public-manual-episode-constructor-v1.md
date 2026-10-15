# Public manual environment constructor

This bounded source change lets `Engine.open(controller="manual")` import the
pinned public `environment.mujoco_two_cam_env_random_obstacles.MuJoCoTwoCamEnv`
through the existing guarded `import_upstream` helper. It avoids importing the
checkpoint runner and its training, agent and model modules for manual control.
All other controllers retain their existing runner construction path.

The constructor preserves the runner's arguments: cameras 128 by 128, horizon 600,
the validated scenario obstacle count, arena extent 7, `render_mode=None`,
`end_on_collision=False`, goal/contact bonuses 0, time penalty .01, progress
scale 10, control penalty .001 and the validated texture. Width, height, horizon
and arena come from the existing validated profile. Unspecified class defaults
remain unchanged, including constructor `seed=None`, frame skip 10, goal
radius .8, exploration bin .2, stall threshold .002 and stall limit 50.

Keep Python/NumPy/Torch seeding, Torch's two threads, world configuration and
the later `Engine` reset with its declared seed in their current order. Keep
diagnostics, provenance, recording and failure cleanup unchanged. The helper
lives in `engine.py`, already covered by replay's exact source identity. No
public factory, `Engine.open` signature, replay API, recording or snapshot
schema changes are needed.

Verification uses authored environments and fake vendor/diagnostic/asset
boundaries only. It checks the selected import path, exact constructor
arguments, ordering, old controller branches, validation and cleanup through
the real `Engine.open`, initialization, reset and `RunWriter` code. It does not
execute upstream, Torch, NumPy, MuJoCo, renderers, operators or model assets.

This source seam does not admit an actual episode. `render_mode=None` still
creates a renderer and camera observations. Ordinary diagnostics still query
distribution metadata, Git, GPU information and asset verification. Exact
runtime/source/XML/operator/renderer admission, finite episode controls,
snapshot/replay comparison and portable evidence validation remain separate.
