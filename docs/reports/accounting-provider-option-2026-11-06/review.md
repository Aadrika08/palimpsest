# Independent bounded provider-option review

Decision: **APPROVE for prospective user choice only.** The option is an
UNADOPTED boundary-change proposal, not an endpoint supplied under the existing
contract, an adopted exemption, a verified launcher or actual source GO.

Reviewed only `docs/plans/memory-accounting-provider-option.md`,
`docs/plans/memory-source-accounting-contract-next.md`, and retained selected
`time.c`, `resuse.h`, `system.h` and source/fetch manifests in this directory.
No archive expansion, installed-binary inspection, runtime/protected-data read,
probe or test was performed. Manifest hashes were read as provenance claims;
they were not independently recomputed. External linked manuals were not fetched.

## Source findings

- `time.c:717–739` forks one direct child, waits for it with `waitpid(..., 0)`,
  then reads `getrusage(RUSAGE_CHILDREN)`. This is a final waited-child endpoint,
  not provider-self accounting or a service-wide/escaped-descendant counter.
  Descendant inclusion remains conditional on the adopted OS semantics and
  intervening parents actually waiting; direct-child exit alone proves no
  descendant closure.
- `time.c:460–463,514–517` and `resuse.h`'s `TV_MSEC` truncate each normalized
  nonnegative user/system timeval to centiseconds using integer division.
  Therefore each term loses less than 0.01 seconds and the sum satisfies
  `L <= C < L + 0.02 seconds`. This bounds representation loss relative to the
  returned OS counter, not physical CPU error, execution-limit overshoot or
  omitted processes. Exact arithmetic and per-invocation interval summation are
  appropriate; no floating-point rounding assumption is needed.
- The provider's formatting, flushing and exit CPU occur outside its child
  total (`time.c:754–772`). The option expressly exposes and proposes exempting
  that tail (option lines 35–38), keeps whole-operation fields null, and requires
  prospective approval of both the exemption and upper-endpoint charge. This
  honestly differs from the current contract's all-project-process boundary.
- `fflush` at `time.c:757` neither establishes filesystem durability nor has
  its return value checked here. The option correctly leaves durable,
  authenticated publication/readback as a separate implementation gate.

## Conditions retained for a later frozen launcher

These qualify approval of the decision package; none is satisfied by this review:

1. Define “fresh” as a provider with no earlier accumulated waited-child CPU;
   account for exec prefixes and inherited accounting state. Qualify executable,
   platform, normalized counter representation and exact `%U`/`%S` output format.
2. Prove disjoint coverage, including every bespoke launcher, administrator,
   watchdog, preparation/acceptance reader, publication and teardown role. Do not
   add a service counter to overlapping GNU child totals or add an inner timed
   job again through its outer waited ancestor. Manager ownership alone proves
   neither process-tree disjointness nor closure.
3. Establish final waits and closure on failure/signalling paths too. A killed
   intermediate parent can leave descendants unaccounted despite a valid-looking
   direct-child receipt. Missing/nonfinal output or coverage makes usage unknown;
   provider failure cannot authorize retry or erase failed-work charges.
4. Freeze finite final receipt/readback roles. Exempt only specifically admitted
   standard providers, never a bespoke final reader by relabelling it. Retain the
   provider-own unmeasured tail explicitly; do not present the covered-scope upper
   endpoint as a whole-operation bound or a prelaunch never-exceed guarantee.

The option already requires these coverage, failure, provenance and close/readback
gates in general terms. No material source error or mandatory architecture change
was found. Prior accounting reconciliation, unchanged stage/lane/project caps,
resource/storage limits and separate source/held-out approval remain required.
