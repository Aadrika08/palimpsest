# CPU characterization01: preserved NumPy import failure

The separately frozen ordinary CPU characterization **failed**, exit1 after
8.909677214978728s. The namespace probe passed; the worker failed on the first
NumPy import, before reporting any package version. Torch, torchvision and MuJoCo
were not reached. This is an engineering preparation result, not runtime,
renderer, operator, model, collection or scientific qualification. All seven
release gates remain open.

The [machine-readable report](puck-cpu-characterization-01.json) and
[byte index](puck-cpu-characterization-01/evidence-index.json) retain all39 source/
input pins, the exact configuration,14 raw files, audit programs/helpers and the
externally observed terminal results. The complete installed package tree remains
local; its measured census is preserved in the input capsule rather than copying
1.3GB into Git. The source freeze is `9b41aa0ab3bd205800ca85e0311b06decf89a504`.

## Actual outcome

The [frozen prospective contract](puck-cpu-characterization-01/source/docs/plans/puck-cpu-characterization-v1.md)
and [configuration](puck-cpu-characterization-01/frozen-configuration.json)
retain SHA256 `b11daf4719daf3a838ece18cf6c0604875d3fcba65b0ab0b5354b9428be6b8ca`.
The [parent result](puck-cpu-characterization-01/raw/result.json) is FAIL with
RuntimeError `CPU worker did not complete normally`. The
[namespace probe](puck-cpu-characterization-01/raw/probe-supervision.json)
returned0; the [worker supervision](puck-cpu-characterization-01/raw/worker-supervision.json)
returned1 with no monitor failure or matching group survivors. Direct logs closed
normally. Sampled parent RSS peaked at79,261,696B, parent+worker at104,083,456B;
these are sampled measurements, not hard memory bounds.

The [import report](puck-cpu-characterization-01/raw/payload/imports.json) retains
NumPy's generic outer ImportError, failed first-import row, empty version map,
postfailure module-cache metadata and persistent before/after mapped-image
snapshots. Its20KB publication is complete and hash-bound by worker stdout.
Neither persistent snapshots nor a failed import establish transient native closure.

The parent records zero children/non-main threads and descriptors5→5. The original
post-baseline receipt is absent because the normal route stopped before it; it
has not been invented or backfilled. The sole actual allocation is consumed.
The 202 passing source checks were authored/legacy fixtures; they did not predict
or establish success of this real package stack.

## Independent preservation audit

The [separate audit](puck-cpu-characterization-01/failure-audit-01.json) returned0
in5.887243352015503s with status **PRESERVED_FAILURE_VERIFIED**, all runtime/
native/collection/study authority false and no target code executed by the auditor.
It checks all39 source/input pins and16 historical admission source capsules,
all27,225 current files/2,074 directories/1,304,701,872B,28 native files/22aliases,
4,233 declared interpreter files/1,048 symlinks and5,388 receipt fingerprints.
It verifies the probe/worker/report/result failure bindings and eight missing
postfailure/historical receipts remaining absent. The original installation01 and
retained admission01 failures are unchanged; admission02's package-data acceptance
remains its separate scoped result.

[Audit source](puck-cpu-characterization-01/failure-audit-v1.py), hash-checked
support helpers and [external terminal observations](puck-cpu-characterization-01/external-terminal-observations.json)
are retained. The planned successful-outcome auditor was never invoked because
its actual-exit0 prerequisite failed. Preserving a failure is not accepting the
characterization or runtime. Current declared baseline identities were verified;
there is no fabricated original after-baseline receipt.

## Static diagnosis and prospective correction

Static inspection exposes a concrete loader-path omission. NumPy's extension
requires its OpenBLAS library, which requires its gfortran library, which names
`libz.so.1`. Metadata04 resolves that bare name to
`torchvision.libs/libz.81d90590.so.1` through a global SONAME index. NumPy's declared
RPATHs reach `numpy.libs`; that directory has no zlib, and the unrelated provider
has another filename. The frozen namespace has no host zlib leaf or alias and
no loader-path override. A matching SONAME in an unrelated directory is not a
loader-discoverable pathname; see the [loader's documented search rules](https://man7.org/linux/man-pages/man8/ld.so.8.html).

This is a **likely cause**, not the observed underlying exception or proof of a
sole cause. NumPy chains its generic wrapper, but characterization01's bounded
error summary retained only the outer message. Both limitations stay explicit.
Do not reinterpret the generic message as evidence of a malformed installation.

The next narrow engineering changes are bounded CPU-only cause/context reporting
with cycle/depth/message limits and metadata05 selecting the exact host zlib file,
its authenticated alias and static dependencies. Keep existing namespace/resource
limits and package bytes; do not preload torchvision's provider or invent a SITE
alias. Freeze and independently review a distinct characterization02 before any
actual invocation. No automatic retry, model/scene/catalog access, scientific
allocation, changed threshold or release-gate closure follows from this report.
