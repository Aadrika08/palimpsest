# Held public manual episode (allocation 16): first accepted episode bundle

**Allocation 16 ran once and completed normally in 695.41s. Its independent episode
audit passed, and the independent outcome review passed with no findings.**

Inside the held, import-guarded sandbox, the episode ran with:

- source `cbda0d9` and preparation04's staged forest;
- numpy 2.2.5, torch 2.9.0+cpu, mujoco 3.3.6 and gymnasium 1.2.1;
- the profile `reproduction`, checker texture, manual controller, seed 7.

It ran these steps:

1. A guarded source worker registered the tick-0 snapshot and recorded 48/48 ticks
   under the frozen schedule (set_action [1,0] at tick 0 and [1,0.5] at tick 24).
2. It rendered every frame through Mesa llvmpipe over EGL (OpenGL 4.6 Compatibility
   Profile, Mesa 26.2.2).
3. It closed normally and exported the source bundle.
4. A fresh replay worker reproduced the recording: 48 ticks and 100 events compared,
   with no divergence.
5. It exported the replay bundle.

Process creation was zero, with no guard refusals. Only the 21 declared absent
imports were denied. The outcome is `AUDIT_PASS_HELD_EPISODE_ONLY`.

**What this establishes:** milestone 1's engineering, operator and renderer route
for one bounded public episode. It covers recording, the registered snapshot,
tick-by-tick replay against a comparison frozen before execution, portable bundles
validated byte-for-byte, and normal cleanup.

**What it does not establish:**

- runtime qualification (`runtime_qualified` stays false);
- any controller or policy capability, or any scientific or study result;
- determinism on another host, Mesa version or boot.

All seven release gates remain open.

## Chain (boot `7f875223…`, each step run once and independently reviewed)

| Step | Result |
| --- | --- |
| Source review 7 | APPROVE |
| Guarded rehearsal 07 | Both phases pass at 600s (user-chosen clock) |
| Characterization-04 | Observed in 33.1s; audit PASS; 0 undeclared misses |
| Candidate 02 | Derived offline: 1,147 modules, 21 declared misses |
| Preparation02/03 stages | Retired with a full census, to free `/tmp` |
| Preparation04 (allocation 15) | Prepared in 22.9s; v15 audit PASS |
| Allocation-16 controls | Review GO with one fix (observer-guard FD expectation 4→5) |
| Admission16 | `DATA_ONLY_ADMITTED` in 18.8s (37,982 held entries; history bound through evidence indexes) |
| Admission review | GO |
| Runtime16 | Source 323.7s, replay 366.5s; peak RSS 975 / 1,031 MB |
| Episode audit | PASS, verifying 48 compared ticks, 384 frames, both bundles, provenance and baseline |
| Outcome review | `PASS_HELD_EPISODE_OUTCOME_RECORD_ONLY` |

## Evidence

The [packet](puck-cpu-held-episode-16/) holds 283 artifacts. Artifact hashes and
originals are verified. The packet's legacy `verify_evidence.py` cannot check the
five fly-gym source paths, because they live in the submodule rather than the
superproject tree. Root re-verified all 103 archived source paths separately:
98 against `cbda0d9`, and 5 through the fly-gym gitlink `8d96459`. All match.

## Next

Milestone 1's episode route is accepted. Remaining milestones:

- valid memory results;
- capable puck and MaleCNS controllers;
- the six-artwork lab;
- human acceptance;
- reproducible delivery.

Guard custody is still about 75% of worker time, and a lab or operator route will
likely need the held-set reduction that was deferred.
