# Integration verification — 25 October 2026

The full four-pass run on `b36b46b0c8cf544dc22c67fb82fd4c1049c71119`
finished with **6,349 passed, 11 failed and 88 skipped**. It is not a passing
integration result. Source and documentation stayed fixed during that run.

| Pass | Result |
| --- | --- |
| Ordinary | 6,312 passed, 5 failed, 88 skipped; 1,540.31 s |
| Process-isolated | 7 passed; 9.46 s |
| Runs-directory fixtures | 5 failed; 13.30 s |
| Tmpfs fixtures | 30 passed, 1 failed; 25.23 s |

The [retained log](main-integration-2026-10-25/tests.log) and
[check index](main-integration-2026-10-25/checks.json) preserve the outcomes,
host/package versions and artifact hashes. The runner selected every
non-integration file; the 88 skips include historical frozen protocols and
disabled runtime opt-ins. Deselections partition the four passes and are not
additional missing tests.

## Repairs and diagnosis

Five authored CPU fixture tests failed because the installed dynamic loader and
libc no longer matched historical native hashes. The isolated diagnostic retained
`Original CPU native input changed`. The fixture now binds current external
library, executable and loader-cache bytes in its copied baseline/native
documents. **All five pass in 46.53 s.** Production admission, historical source
profiles and actual qualification evidence are unchanged. The fixture still
requires its declared Linux paths and interpreter; this does not establish
portability or qualify the updated host runtime.

The other six failures stopped on `Collection root or ancestor changed while
held`. A copied-source diagnostic retained the original comparison and added
the changed ancestor and stat fields to its error. All six intended checks pass
in a coordinated quiet window. A controlled unrelated `/tmp` sibling
creation/removal reproduces the refusal: device/inode/mode/size/link count stay
fixed while the directory's mtime/ctime change. This proves the interference
mechanism, **not the responsible path or actor in the original run**. All six
unmodified pytest cases also pass together in 7.35 s. No production guard or
assertion was relaxed; a quiet complete rerun is still required.

The canonical runner also dropped all documented opt-in flags through `env -i`.
It now forwards a fixed list of present test flags and output/asset paths, with
quoted values, while retaining its clean environment and fixed thread/EGL/CUDA
settings. The executable-spy regression exercises all three runner routes:
9 failures/3 passes before the fix, then **12 passes**. It starts no model or
namespace workload. A separate `PALIMPSEST_SIMULATION_TESTS=1` intervention run
passes **6 tests without skips**, including its actual upstream EGL edit test.

README/setup/testing instructions now use published main and the canonical
runner, distinguish retired memory v1 from current work, and point to the
600-frame/120-second guided package. The runbook and requirements matrix retain
the outstanding scientific, human and delivery gates.

## Delivery state

The live remote check still finds main at `2814138` and the feature branch at
`cfddb09`; [PR #184](https://github.com/Aadrika08/palimpsest/pull/184) is draft.
Its existing hosted fixture run failed collection under the older workflow.
The owner's configured credential still lacks `workflow` scope. The other local
account and connected GitHub app lack repository write access. The local CI
repair has not run remotely, and no merge or force-push occurred.

The project-code/new-parameter licence decision has been requested and remains
unresolved, as do intended use, human viewing/listening and independent operator
acceptance. No complete green candidate suite, hosted CI pass, scientific
qualification or final release is claimed by these targeted rechecks.
