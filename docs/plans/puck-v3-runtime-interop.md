# Resolve numerical runtime import contracts before collection

Continue the full simulation release goal from PR #131 (`d58f49c`). The current
worker preflights stdlib and authored dependencies, but has not imported the actual
numerical configuration through its held finder. No collection/study GO follows.

The static installed-source audit identifies real gaps: Torch publishes ops/classes
and native-produced submodules directly into sys.modules; current cache validation
refuses these. NumPy temporarily sets two environment flags unless predeclared.
Torch and MuJoCo load libraries/plugins by package paths. File-FD loading also
fails the existing authored origin-relative dependency fixture. Do not guess that
normal numerical import or an ordinary module list qualifies the held route.

1. Add a bounded stdlib characterization worker. It imports only NumPy, Torch and
   MuJoCo from one exact site root, under an exact prospective environment. Record
   actual cache identities/aliases/producer attributes, raw versions and persistent
   mapped file observations. Metadata inspection must not invoke framework
   __getattr__. Bound request64KiB, output1MiB, cache8192, attribute edges262144,
   maps4MiB/65536lines. This is development characterization, not qualification.
2. After source tests and preflight review, invoke that characterization exactly
   once in a fresh process using the existing bounded supervisor: 60s normal,
   70s hard, 1GiB sampled parent+child RSS, 64MiB output, 1GiB free floor and at
   most one child process. Preserve its request/source/invocation/log/report and
   failure if any. No automatic retries or stage/scientific authority. No model,
   scene, catalog, retained study, original qualification or fitting access.
3. Use the actual finite observations to define a prospective dependency profile:
   explicit source-bound virtual exports, no prefix wildcard or ambient fallback.
   Test a held-directory-descriptor native route on authored libraries. Keep the
   old exact-file descriptor route as v1; document any changed pre-initialization
   guarantee, live edge/lease checks and mapped-inode postcheck before adoption.
4. Freeze/review exact source/runtime/dependency/environment/input registration
   before any held numerical qualification. Binding all-file package custody and
   import results is not complete native/transient/JIT closure or collection GO.
5. Continue into authenticated worker episode dispatch and complete parent seals,
   identity/progress/escaped-descendant handling, lease/resources/clock acceptance.
   Actual collection waits for the complete reviewed path and pending catalog policy.

All seven release gates remain open. Memory amendment02 and prospective navigation
remain pending; no consumed attempt or threshold changes. CI/physical rover remain
excluded; the six artworks remain simulation-first.

Progress: source characterizer and fixed parent are implemented. All cache identities
are retained; direct producer edges are restricted to exceptional identities
(aliases, missing/nonstandard spec, missing file or ModuleType subclass), with
explicit output scope. This prospective shape amendment precedes the one actual
observation and is covered by authored fixtures. Source review and results are
recorded in `docs/reports/puck-v3-runtime-interop-source.md`.
