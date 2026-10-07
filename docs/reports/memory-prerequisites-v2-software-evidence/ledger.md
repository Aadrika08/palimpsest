# Memory prerequisite campaign software development ledger

7 October 2026. This directory is ignored development evidence outside the three
scientific budget roots. It is not a registration, native run or scientific close.

The source defines one selected profile and eight cells: four full, two prefix,
two restored continuations. The dedicated new driver retains the unchanged worker
protocol, original first-six predicates and exact prescribed fresh south-prefix
source. It reuses existing owner/raw/SNP/state/storage helpers; pilot, held-out,
R2 release and hardware gates remain locked. The driver can only provisionally
pass; a fresh independent audit must recompute all eight cells and the candidate
pair before publishing the authoritative close. Legacy raw equality remains a
separate reported result.

Red evidence:

- `driver-red.txt`: 1 expected failure in 0.03 s before the new module existed.
- `driver-receipts-red.txt`: fixture checkout identity failures. The production
  job validator correctly rejected the first temporary fixture; its worker module
  path was then bound to that fixture. This was a test setup correction.
- `driver-serialization-red.txt`: 2 failed, 1 passed in 0.70 s. Independent
  comparison incorrectly treated JSON lists and original tuples as different;
  canonical JSON comparison fixed that rejection. A failed first mandatory cell
  also lacked allocated/started inventories in the failed close; the auditor now
  gathers those before the driver disposition gate.

Green evidence:

- `driver-first-green.txt`: 3 passed in 0.73 s after those two fixes.
- `driver-focused-green.txt`: 28 passed in 12.74 s, under the shared
  `/tmp/palimpsest-software-tests.lock`. Contract/pin/environment changes refuse
  before any owner; aggregate reservation refuses the next allocation; failed
  mandatory cells stop later owners. Independent negative fixtures cover wrong
  namespace, extra allocation, active owner, control count/trace/invariant/state
  changes, source receipt, supervision/internal cap, initial/post corruption,
  historical/raw mutation, expired readout, late close, storage recount and a
  failed false-close write. The last case removes the authoritative path and
  retains the original bytes as `scientific-close.invalidated.json`.
- `git diff --check` returned zero with no output at the final source freeze.

The focused fixtures use real immutable job validation, SNP containers and
checksums, source/component/invariant readers, candidate copy projection and
control publication. Native asset preflight/source inventory, policy/worker/raw
camera execution, duration decoder probing, Git admission and PID observations
are explicit software doubles. The fixture-only StorageBudget uses min-free=0
because `/tmp` is a small tmpfs; production remains 8 GiB / 2 GiB free / 64 MiB
headroom. Synthetic completed owners are not measured FLYNN/camera evidence.
Launcher tests own the separate real temporary-Git/subprocess admission rehearsal.

Exact focused command (from the new worktree):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src:scripts:tests OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' flock /tmp/palimpsest-software-tests.lock /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python -m pytest -q tests/test_memory_prerequisites_v2.py
```

Driver/test source is frozen for root integration and independent review. No
native owner, real source SNP read, actual registration, full suite, commit or
push was performed by this lane. Root owns the whole watchdog, detached-owner
cleanup/publication, registration preparation, full suite, branch review and any
subsequent approved scientific invocation.

Static review caveat sent to root: exact runtime identity and fixed environment
are checked, but the approved package/Python version constants are not an
additional registration predicate. The currently pinned baseline versions are
the approved ones; a different self-consistent runtime registration deserves an
explicit version gate before prospective admission.

Fresh branch review confirmed that runtime caveat and identified a second issue:
a recorded first repeat with bad retained state/invariant/count could consume the
second repeat before final readout stopped the campaign. Root authorized one
focused driver/test fix pass, leaving production clock edits to root.

- `driver-review-red.txt`: 8 failed, 28 deselected in 2.66 s. Four self-consistent
  unapproved runtime fixtures previously reached provisional pass. Missing or
  corrupt first-repeat post state, a false invariant, and four continuation ticks
  each incorrectly admitted `restore-2` before later failure.
- The driver now separately requires Python major/minor 3.11, NumPy 2.2.5,
  MuJoCo 3.3.6 and Torch 2.9.0. Each repeat must have true invariants, exactly five
  continuation controls and an immediately audited initial/post/component/receipt
  binding before admitting another owner.
- `driver-review-green.txt`: 36 passed in 11.09 s under the shared test lock.
  All four failed-first-repeat cases retain seven allocated jobs and explicitly
  leave `restore-2` unattempted.
- The temporary campaign setup now writes a launcher marker with original
  monotonic start and registration SHA for root's separate original-clock fix.
  This lane did not modify the production driver clock or watchdog.

Source is frozen again after this fix pass; no native/registration allocation,
full-suite execution, commit or push was performed by this lane.

An additional reviewer finding concerned hard-timeout process containment. Root
requested one actual POSIX lifecycle test of the existing campaign adapter and
shared runner, with admission/Git/free-space/native work replaced by temporary
fixtures. The actual Python spawning and GNU timeout behavior remain real. The
harmless pipeline ignores TERM; an external ancestor kills its process group
after 5 s. Stdout/stderr go to a temporary file rather than inherited pipes.

- `launcher-lifecycle-red.txt`: 1 failed, 12 deselected in 5.08 s. The hard
  ancestor exited but supervised Python PID 1236482 (start 8666468, PGID 1236481)
  and pipeline PID 1236485 (start 8666476, PGID 1236485) remained live in detached
  groups. The test finally killed only fixture PIDs with matching starttime and
  PGID; no user/native owner or user storage lease was touched.
- Root owns the new-mode-only containment fix; this lane owns only the appended
  lifecycle regression in `tests/test_memory_prerequisites_v2_launcher.py`.
