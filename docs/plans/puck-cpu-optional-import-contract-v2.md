# CPU optional-import contract v2: stock absence semantics

Runtime10 is a consumed failure. Its first worker refusal is unregistered
`backports_abc`, requested by `numpy.random._common` while Torchvision imports
`torch._dynamo`. This contract replaces the planned one-name successor: offline
evidence shows that adding only `backports_abc` would make attempt 11 fail too.
It does not admit an episode, qualify the runtime or close any release gate.

## Evidence (diagnostic only, not admission)

All files are in [the v2 evidence directory](../reports/puck-cpu-optional-import-contract-v2/diagnostics/).
Each probe ran once offline in a read-only `bwrap` sandbox against the retained
held site with the qualification environment. Site metadata (path, size, mtime,
ctime of every entry) is identical before and after all probes. The sixteen
diagnosed held files match `runs/puck-cpu-retained-admission-02/inventory.json`.

1. **`backports_abc` is optional and caught.** `numpy/random/_common` and nine
   pandas/SciPy extensions embed Cython 3.0.11/3.0.12 `__Pyx_patch_abc`. Upstream
   Cython 3.0.12 `Utility/Coroutine.c` (file hash matches its wheel RECORD) imports
   `backports_abc` "if available" and calls `PyErr_Clear()` on failure; module
   initialization continues and returns 0. The name is absent from the held
   site and the admission inventory.
2. **Census.** With a passive tail finder, the unguarded four imports complete
   (numpy 2.2.5, torch 2.9.0+cpu, torchvision 0.24.0+cpu, mujoco 3.3.6) and make
   32 non-stdlib requests that no finder resolves: the frozen nineteen,
   `backports_abc`, and twelve names from `torch._dynamo.trace_rules`.
3. **The current raise semantics cannot pass.** `trace_rules.add()` calls bare
   `importlib.util.find_spec()` for every `THIRDPARTY_SKIPLIST` name at import,
   with no exception handler. A finder that raises `ModuleNotFoundError` for
   declared names fails Torchvision at `trace_rules.py:3664`: on `tqdm` (already
   a frozen negative) with nineteen plus `backports_abc`, and on `fx2trt_oss`
   with all 32. Returning `None` for exactly the 32 names completes all four imports.
4. **Registration gaps.** Emulating the guard with runtime10's 1,783 registered
   dependency modules finds four more refusals: `networkx`, `pandas` and `sklearn`
   (present in the held site, unregistered, probed only by `trace_rules.add`) and
   `torch.utils._cxx_pytree` (present; stock import raises `ImportError` because
   `optree` is absent, and `_functional_collectives` catches it and falls back to
   `torch.utils._pytree`). Its pre-raise code imports only already-loaded modules.
5. **Exact v5 semantics pass offline.** With all 36 declared names unresolvable by
   every finder and runtime10's registry, the four imports complete with the
   expected versions, request every declared name, execute no hidden module and
   make no other unregistered request.
6. **Deadline margin is tight.** `backports_abc` is requested after 70% of
   Torchvision's 990 module loads; runtime10 reached it at about 106s guarded.
   Linear extrapolation projects about 135-145s for all four imports against the
   unchanged 180s deadline. This is an estimate, not a timing proof.

## Decision

Add missing-import policy **v5**. It inherits every v4 (q4) behavior and changes
only declared names:

- `negative_imports` (declared **absent**, exact sorted 32 names): verify held
  absence exactly as v2–v4 do, record the denial, verify that every remaining
  original meta-path finder returns `None`, then return `None`. Stock import
  machinery raises `ModuleNotFoundError` for `import`; `find_spec` returns `None`.
- `hidden_imports` (declared **unavailable**, exact sorted names `networkx`,
  `pandas`, `sklearn`, `torch.utils._cxx_pytree`): must not be stdlib, local
  source or registered dependency modules. Record the denial, verify remaining
  finders return `None`, and return `None`. Hidden modules never execute.
- Any remaining finder that resolves a declared name poisons the guard. Every
  undeclared unregistered request still poisons, even when the caller catches it.
- The receipt keeps `expected_missing_imports`, adds `expected_hidden_imports`
  and reports `denied_imports` as the sorted union actually requested.

The deviations from stock are explicit: hidden packages are unavailable, so
Dynamo's skip list omits their directories, and `_cxx_pytree` reports
`ModuleNotFoundError` instead of its optree message. Held distribution metadata
still lists networkx, pandas and scikit-learn although importing them fails.
None of these admits
`torch.compile`, CUDA or any operator. Policies v1–v4 and consumed epochs 1–10
keep their old behavior and bytes.

## Implementation and verification

1. RED tests first, then the smallest bootstrap change; follow the q4 pattern in
   `f89c330`/`1fa9421`.
2. Add CPU qualification epoch 11 (`puck-cpu-held-runtime-allocation-v11`,
   policy v5, both exact rosters) to the parent qualifier, transport observer and
   independent auditor; follow epoch10 in `0cb3755`/`cbe48b3`.
3. Required regression cases: declared absent via `find_spec` and `import`
   (no poison, recorded); hidden present module never executes; undeclared
   request still poisons; declared absent but present refuses before initializers;
   hidden name registered or local refuses; a later finder resolving a declared
   name poisons; v4 and epochs 1–10 unchanged.
4. Independent source review, then the existing frozen-controls, fresh-admission
   and single-invocation sequence for attempt 11 under unchanged 180s/2GiB limits.

**Status (2026-10-16):** `bf6b980` (RED) and `ec4de6b` (implementation) pass the
new and affected suites. Independent review of `d03b85d..ec4de6b` approved with
no Critical or Important findings; it confirmed the rosters equal the census and
emulation evidence, v1–v4 and epochs 1–10 are unchanged, and returning `None`
cannot reach the held site because the worker's `sys.path` is stdlib-only.
Minor follow-ups (native-cache overlap test, test-comment accuracy, a
documented recheck window, receipt-field hardening) are applied separately.

Passing source tests and these diagnostics are not installed-runtime qualification.
