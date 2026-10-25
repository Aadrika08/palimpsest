# Running the source tests

Use the canonical runner. It runs every non-integration test file in four passes:

```sh
scripts/run_tests.sh                       # the whole non-integration suite
scripts/run_tests.sh -- tests/test_x.py -k name   # chosen tests, pass-1 rules
scripts/run_tests.sh --integration         # the *_integration.py files
```

It exits nonzero if any pass fails, and removes its temporary directories when it
finishes. The README's `uv run --no-sync pytest -q` remains a quick fixture
check; it does not reproduce this environment.

## What the runner sets up, and why

- **Interpreter.** It uses the main checkout's `.venv` (CPython 3.11.15). This is
  the environment prepared with the `simulation` and `lab` extras and the `dev`
  group, so `fastapi 0.142.2` and `httpx 0.28.1` are present for the lab tests.
  - Override it with `PALIMPSEST_PYTHON`.
  - Do not use or modify the `r0-reproduction` venv. Recorded evidence was made
    with it, and it lacks the lab packages.
- **A clean environment** (`env -i`):
  - The import path is `src`, `scripts` and `tests`. Tests import script modules
    by name, and some subprocess cases import test helpers such as
    `test_puck_execution`.
  - `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and
    `NUMEXPR_NUM_THREADS` are all `1`, with `MUJOCO_GL=egl` and an empty
    `CUDA_VISIBLE_DEVICES`. Memory campaign checks require exactly this:
    "Campaign requires one CPU thread, EGL and disabled CUDA".
  - `TMPDIR=/tmp`, the locale is `C.UTF-8`, and `PATH` is `/usr/bin:/bin`.
- **No bytecode in the tree.** The runner uses `PYTHONDONTWRITEBYTECODE=1` and
  `python -B`. Test subprocesses started with `python -I` ignore that variable,
  so they also pass `-B`.
  - Several qualification tests take an inventory of the source tree and refuse
    any `__pycache__` ("Qualification source has unbound bytecode").
  - If a crashed run leaves caches behind, remove them before running again:
    `find src scripts -name __pycache__ -prune -exec rm -rf {} +`.
- **Four passes and three basetemps.**
  - **Pass 1:** every test with none of the `runs_basetemp`, `tmpfs_basetemp` or
    `process_isolated` markers,
    with `--basetemp` outside the repository, on the project disk
    (`~/.cache/palimpsest-pytest/...`).
    - Allocation tests refuse temporary roots inside the repository: "Allocation
      root overlaps an immutable input".
    - Namespace and bwrap tests refuse `/tmp`, because it overlaps the fixed
      sandbox `/tmp` and a private tmpfs mount.
    - Keeping it off `/tmp` also preserves tmpfs headroom.
  - **Pass 1b:** the tests marked `process_isolated`, in their own process with
    the same basetemp. Five test functions check that nothing imported torch
    or left threads or children: "Auditor must have no children or other
    threads", "Unexpected admission child process", and
    `'torch' not in sys.modules`. After hundreds of earlier tests in the same
    process, that is not true, although each passes alone.
  - **Pass 2:** the tests marked `runs_basetemp`, with `--basetemp` under the
    repository's ignored `runs/` directory. These five tests assert "Use
    persistent runs/ basetemp".
  - **Pass 3:** the tests marked `tmpfs_basetemp`, with `--basetemp` on tmpfs
    (`/tmp/palimpsest-pytest/...`). These 25 test functions hold dependency files
    whose native identity requires tmpfs ("Native identity requires tmpfs"), or
    check raw tmpfs inode identity ("V3 owner transaction namespace changed").
    The pass is small, which keeps `/tmp` headroom.
  - The integration files all assert a `runs/` basetemp, so `--integration` uses
    one.
  - Other tests that need a real tmpfs make their own directories under `/tmp`.
  - Keep at least 2 GB of `/tmp` free. Never use `/tmp` as the basetemp for the
    whole suite: pytest keeps every test's directory until the run ends, which
    can fill the tmpfs.
  - Do not run Python without `-B` in the tree while a run is in progress. Any
    `__pycache__` it writes fails the inventory tests.
- **Opt-in heavier checks.** Set `PALIMPSEST_SIMULATION_TESTS=1` for real EGL
  world and scene cases. `PALIMPSEST_MALE_TORCH_CHECKS=1` and
  `PALIMPSEST_MALE_RUNTIME_TESTS=1` cover the MaleCNS runtime windows.
  The clean environment forwards these explicit values, plus
  `PALIMPSEST_TEST_PUCK_TORCH`, `PALIMPSEST_BUILD_NAMESPACE_TEST` and
  `PALIMPSEST_INSTALL_FIXTURE` for their separately selected checks. They remain
  disabled unless set to exactly `1`.
  `PALIMPSEST_MALE_RUNTIME_OUTPUT` must name a new directory for retained actual
  MaleCNS evidence; `PALIMPSEST_TEST_ASSETS` optionally selects its asset root.
  These paths are also forwarded, including spaces. For example:

  ```sh
  PALIMPSEST_MALE_RUNTIME_TESTS=1 \
    PALIMPSEST_MALE_RUNTIME_OUTPUT="$PWD/runs/male-runtime-new-session" \
    scripts/run_tests.sh -- tests/test_male_runtime.py
  ```

  Choose a fresh output name for each session. Default fixture passes do not
  establish that any opt-in runtime check ran.

## Frozen pins after integration

Finished studies froze the exact bytes of some source files. Integrating every
branch into `main` changed those files, so tests of those historical protocols
are either checked against the pinned commit or skipped as historical, through
`tests/frozen_pins.py`. See
[frozen-source-pins-after-integration](plans/frozen-source-pins-after-integration.md).

The [retained-condition source revision](plans/memory-retained-condition-v1.md)
resumes memory-v4 checks against the integrated source with a separately named
prospective profile. Its new tests do not use historical skips. Both earlier
profiles remain checked against Git history; no old scientific evidence is
rebound to the new source.
