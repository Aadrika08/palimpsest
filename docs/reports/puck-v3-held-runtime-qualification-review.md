# Held-runtime source and exact-freeze review

Independent fresh whole-branch review covered ce4b55f..875f8bb33e0059d3cb51162ffa140a0eecb82239.
Original verdict: SOURCE NO-GO and exact preparation-freeze NO-GO.
One Important finding; no Critical or additional Important/Minor findings.

The allocation hard_guard ended before success transport and failure publication/transport.
A real-guard authored probe with a0.1s hard deadline returned normally after0.362s
when failure publication was delayed. The reviewer ran65 authored checks13.37s,
verified the13 source descriptors185699B, retained observation/candidate, canonical
freeze, environment, versions, allocation limits and absent actual markers.
Original unexecuted freeze SHA be4582e0981e90e7057a096e2856a0634734ef9aa8a77770ca1a84fa287d853d
is retained separately. It was never invoked and grants no admission.

## One fix pass

Root regraded the finding Important and kept both terminal paths within the outer
hard_guard. Two authored subprocess regressions use the real watchdog and owned
process group, authenticate fault-injected copied source and delay success stdout
or failure outcome publication2s with a0.3s hard clock. Both RED: success exited0
at2.091s; failure exited1 at2.074s. Both now end by SIGKILL within1.5s, preserving
exclusive markers and any already published terminal. Parent suite15passed6.01s;
full affected slice216passed75.84s. No second whole-source review or independent
post-fix source-GO is claimed. Exact refreshed-freeze admission is separate.
Default repository suite remains10 collection errors1.96s (FastAPI/httpx absent).

## Declined scope and rulings

- Installed dependency completeness, payload identity, filesystem suitability and
  staging feasibility require the actual bounded preparation; authored checks
  cannot establish them. Cost if mistaken: unsound runtime admission.
- Import compatibility/performance require the separately pinned held invocation;
  preparation alone imports no numerical package. Cost if mistaken: false compatibility.
- Fresh interpreter identity and FD/free-space readiness are launcher admission
  checks, not facts supplied by code review. Cost if stale: admission must refuse.
- Default full-suite success is unavailable in this interpreter; no install or
  broad passing claim follows. Cost if ignored: hidden integration failures.
- Hard RSS/WCET, hostile-source containment, transient/JIT/native closure, escaped
  descendants and physical/scientific validity remain outside this operational
  mechanism. Cost if overstated: unsupported execution or scientific authority.
- Exact qualification-freeze readiness and actual terminal cleanup/outcome require
  real preparation pins and independent outcome audit; no receipt is synthesized.
  Cost if skipped: a run admits its own selection or incomplete terminal.

No actual installed-site scan/hash/import or study ran during source review.
