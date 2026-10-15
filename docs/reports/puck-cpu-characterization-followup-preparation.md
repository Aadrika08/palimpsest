# CPU follow-up preparation after failed characterization01

The [actual01 failure](puck-cpu-characterization-01.md) is preserved and independently
audited. This record reports source/static corrections only. No actual02 CPU
imports, held qualification or simulator episode ran.

The CPU worker now retains bounded exception causes and contexts rather than
losing NumPy's underlying failure behind its wrapper: at most8 entries and2,048
message characters per entry, with explicit cycle/depth/message truncation and
suppression handling. Legacy request-v1 error details remain unchanged. All six
new authored cases failed before the fix; the affected suite then passed208 checks.
Final review identified an inner exception whose string formatting could erase the
primary report. That additional authored regression failed before the fix; chain
diagnostics are now best-effort and keep an explicit incomplete marker. The final
affected suite passes209 checks in6.62s (session73621, terminal22e3d7, exit0), using
`--basetemp=runs/cpu-characterization-chain-review-GREEN-01`.

The separately reviewed data-only [metadata05 helper](puck-cpu-characterization-preparation/native-metadata-05.py)
returned0 in0.181258s reported terminal time. It parsed trusted ELF metadata and
hashed selected files; it executed no target package or native initializer.
[Metadata05](../plans/puck-cpu-characterization-native-metadata-05.json) is COMPLETE
within its narrow static scope:29 host files,23 aliases and39 inspected system/
prefix ELFs. It explicitly adds host zlib and changes the17 known bare-zlib edges
to its exact reachable host fallback; all other04 fields or their overwritten
values, the old edges and optional `_crypt` absence are retained. It does not
establish every other packaged-provider lookup or prove the sole actual cause.

The [machine record](puck-cpu-characterization-followup-preparation.json) retains
source/artifact hashes and actual outcomes. Independent review caught and corrected
helper cache lookup and whole-publication timing/flush gaps before this sole
metadata invocation.
No original observation or metadata output was overwritten.

The [prospective02 proposal](../plans/puck-cpu-characterization-02-proposal.md)
identifies the remaining concrete work: parent epoch/source binding, metadata-v5
admission, exact02 configuration and independent outcome auditor, then a new
source/configuration review and fresh resource admission. The old01 configuration
is historical and cannot authorize the changed worker. No02 execution readiness
or release-gate closure is claimed.
