# Fresh puck worker bootstrap: source and child evidence

The stdlib seed now authenticates bootstrap bytes before compile, and a real
fresh child binds the running original interpreter before executing the
source-supplied held-file implementation. Local package, scripts namespace and
registered upstream Python paths load only through authenticated held bytes.
The executable public entry performs source preflight and emits a terminal
receipt. External dependencies and native/numerical collection remain denied.

Base PR #128: `eb96a19522561b34b2a0d97e0f04558361429828`.
Reviewed initial source: `875da74afcfc07fe761a4afa115cdf7c5c335f61`.
Final corrected/tested source: `0629f43009fcaa53a7f9590381d0ee54eabe4b91`.

## Working execution boundary

Use `scripts.puck_worker_bootstrap.command(...)` to construct the exact isolated
invocation. Its fixed seed is below the existing 4096-byte argv-element ceiling;
it is not the complete bootstrap embedded in one oversized argument. It opens
the supplied bootstrap nofollow, checks regular single-link type/size/SHA, then
compiles those bytes while keeping the descriptor open. The canonical externally
hashed registration binds that source, the source roster/import mappings, exact
interpreter descriptor/version, environment/cwd and argv prefix. Its external
own-SHA suffix avoids a circular registration hash.

The observed kernel cmdline and sys.orig_argv must both match the complete
invocation. Fresh isolated/no-site/no-bytecode/unoptimized flags, exact complete
environment/cwd, PID/start/parent identity and dedicated session/group are checked.
CPython locale coercion must be accounted for by an explicitly declared locale;
the authored fixtures use LC_ALL/LANG=C.UTF-8. The actual unchanged 21,662,864-byte
original interpreter is streamed and compared with /proc/self/exe object identity
before compiling the held-file support module. A byte-identical other inode fails
before that module executes. Later custody retains source, registration and runtime
objects through the entry and final close.

The exact Python/XML census under package/scripts/upstream has the existing
4096-entry/32-depth ceilings. Every Python file except the seeded bootstrap has an
explicit import mapping; support code is authenticated and dispatch-bound too.
Namespaces use observed held directories without ambient search-path fallback.
Unregistered local/external imports and module-cache insertion reject. Module
objects/specs/origins/search routes, class slots/bases/member rosters, imported
function aliases, method/property wrappers and function code identities stay bound.
Failures poison custody; restoring an environment after a caught failure cannot
rearm it. Entry result data cannot overwrite receipt identity or authority fields.

This uses the existing held-file implementation rather than a duplicate full
custody engine. Source descriptors remain <=512 files, <=1 MiB/file and <=64 MiB;
source plus fixed interpreter inputs remain <=80 MiB. Registration/receipt are
<=1 MiB, entry data <=64 KiB, and the internal absolute deadline <=180 seconds.
A deadline observation is not a hard process bound: parent supervision and drain
remain required. No cap or collection owner/native denial was changed.

The flag/import choices were checked against the official
[CPython 3.11 command-line reference](https://docs.python.org/3.11/using/cmdline.html)
and [importlib reference](https://docs.python.org/3.11/library/importlib.html), then
observed on the target 3.11.15 interpreter in real children. Documentation currently
serves the 3.11 maintenance line; the tests establish this target behavior.

## Observed verification and corrections

Plan/API RED commit `2560f3b`: 15 missing-bootstrap failures in 0.12 seconds.
Initial implementation: one actual-child environment failure and 14 negatives
in 0.76 seconds; those negatives were not credited until declared locale correction
and specific refusal-reason assertions established their intended paths.
Initial green: 15 passes in 1.87 seconds. The holder needs both its private initial
bootstrap load and an ordinary mapped package route for later consumers; initial
mapping refusal was corrected before the intended namespace/cache/spec REDs were
measured. Three intended REDs reproduced in 0.68 seconds; all 18 then passed.
An actual interpreter-before-holder marker RED reproduced in 0.18 seconds; streamed
initial image binding fixed it. Further inode and caught-failure characterization
checks exercise existing behavior rather than claiming new missing-feature REDs.
Source commit `875da74` passed 21 checks in 3.18 seconds.

Independent whole-branch review found two Important defects: replacing a module's
class and replacing an imported held-local function alias both emitted success
with answer 99 instead of the authored 43. Root's one dispatch fix pass added
those cases plus changed method-wrapper and support-holder dispatch: four REDs in
1.58 seconds, then all 25 passed after correction. Class slots, all imported
function slots, wrappers and the support module are now captured; dispatch is
checked before invoking support guards. No independent exact-source GO or runtime
GO is claimed from the initial review. Independent corrected-source test repetition
is verification evidence, not a second code review.

Final focused: **25 passed, 4.59 seconds root / 4.60 seconds independent**.
Final serialized affected: **1301 passed, six deselected, 66.09 seconds root /
67.33 seconds independent**, exit0. The affected command is the exact 25-file
command in [PR #128's report](puck-v3-inventory-scope-source.md) with
`tests/test_puck_worker_bootstrap.py` added and the same six inherited mechanics
construction-pin/missing-httpx exclusions. `git diff --check` passes.

Default command, same environment:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -m pytest -q -x --tb=short
```

Result: **one collection error in 0.30 seconds**, tests/test_lab.py cannot import
FastAPI. No repository-wide suite pass is claimed. Earlier retained source/custody
anomalies remain in their reports; these passing runs do not establish their cause.

## Qualification limits and next complete path

Tests run real isolated stdlib children, read/hash the original interpreter, and
use authored temporary source/namespace fixtures. They do not run original-bundle
qualification, actual inventory/catalog/retained scans, model/native collection,
training or evaluation. Inherited affected checks use synthetic CPU/native fixtures.
No original model/study allocation is consumed or retried by this preflight.

Receipts leave runtime/dependency/native/collection/executable grants false and
qualification claims empty. CPython stdlib and interpreter ELF dependencies remain
an explicit trusted/unqualified boundary. Binding Python's image/version is not
qualification of NumPy/Torch/MuJoCo, EGL, CPU/thread configuration or loaded native
images. This is not a sandbox against arbitrary admitted Python, hostile host
behavior, mutable program data or arbitrary dynamic execution. Output is terminal
stdout transport after final recheck/close, not durable parent publication or
post-close custody. Parent comparison, lease, descendants, sampled resource checks
and durable receipts remain incomplete. Existing synthetic runtime observations in
HeldCollectionExecution must not become measured runtime evidence.

Next implement the separately reviewed dependency/native import path, then bind
this worker to the existing inventory/reservation, collection envelope/model/scene
custody, interval/clock ledger, exact-environment supervision and durable terminal
publication. Existing supervisor inherits environment and checks an owned process
group; exact environment and descendants escaping groups still need explicit
launcher work. Review/freeze the complete execution before any actual stage.
Memory amendment02, catalog access and prospective navigation decisions remain
pending. All seven simulation gates remain open; CI/physical rover stay excluded.
