# One interruption, two traces — obstacle allocation

Prospective follow-up to the [agent curatorial review](../reports/artwork-curatorial-review-2026-10-22.md).
The prior goal-edit pair remains intact. This allocation addresses the short
branch with a different declared intervention; it is not a confirmatory experiment.

## Frozen execution

- Fresh `runs/route-obstacle-material-2026-10-22-v1`, clean committed sources.
- Existing public LabSupervisor path, reproduction/checker, FLYNN CPU, seed 0.
- Step parent exactly 100 ticks, register its snapshot, continue unchanged to
  natural termination or the existing 600-tick episode limit. Close owner.
- Restore that snapshot once with the same controller and one edit:
  `{"kind":"move_obstacle","index":0,"xy":[0.75,-0.75]}`.
  Continue once to natural termination or the existing episode limit.
- No reset, replacement controller, eye mask, goal edit, seed selection or retry.
  If the parent cannot reach tick 100 or the placement fails, retain the failure.
  Overlap, early termination and null response remain valid outcomes.
- Same 300 s outer watchdog, 60 s boundary waits, 1 MiB log caps, 2 GiB aggregate
  recording budget and 2 GiB free-space floor. At most one lab owner at a time;
  verify recorded owner identities are gone after shutdown.

The chosen edit was checked against the previous seed-0 tick-100 snapshot using
the public dry-run validator, without running a candidate continuation. New
center distance to rover is 1.95363 (>0.7 clearance), nearest other obstacle
1.73198 (>0.8), and unchanged goal 5.69391 (>0.65). Live restoration must still
validate placement. This uses previously observed world geometry, not a blind
allocation or a new navigation benchmark.

## Verification and presentation

Audit snapshot identity, parent event prefix, policy/RNG/eyes and the sole edit.
Obstacle relocation intentionally changes its two position coordinates, zeros
their velocities, updates joint limits and map, refreshes derived state and
invalidates geometry caches. Verify those changes independently; do not assert
that the complete integration vector is unchanged.

Compare every exported coordinate to the records. Report both natural outcomes
and lengths. Define the common post-snapshot window as tick 100 through the
earlier final tick; display full unchanged routes and explicitly label their
unequal ranges. Retain fixed arena axes and solid/dashed line distinction.
Put the overlay before detailed provenance so the comparison is immediately
available. Captions name the obstacle edit, unchanged goal, source and snapshot.

Build a fresh package with unchanged Afterimage, Choir, Atlas and specimen
derivatives. Check archive readback, all hashes, offline desktop/mobile layout,
keyboard provenance controls, no autoplay and exact geometry. Repeat the two
changed static modes' 600-second automated sessions; carry forward only the
unchanged modes' prior duration evidence. Human acceptance remains separate.

Exit: the actual intervention and continuations are readable and auditable.
Visible route separation, positive memory effects, physical drawing and human
exhibition acceptance are not required or claimed.
