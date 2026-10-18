# Repair campaign receipt publication without another study

7 October 2026. Software-only follow-through for the approved implementation;
the failed native allocation is consumed and preserved in
[PR #90](https://github.com/Aadrika08/palimpsest/pull/90).

The driver duplicates complete audit reports under `owners[].audit` after already
retaining the same completed owner results under `attempted[]`. With eight real
memory maps, its final receipt exceeds the unchanged 1 MiB cap. Final timestamps
then fail to persist and the independent auditor reads a stale checkpoint.

1. Extend the existing synthetic eight-owner fixture with realistically large
   nested memory and receipt identities. Run the actual driver-to-independent-
   auditor publication path and observe the envelope failure before changing code.
2. Omit only the driver's redundant nested owner audit payload; keep owner
   identity, disposition and gate summary, complete attempt reports, raw paths,
   allocated/started inventories and independent recomputation. Independent close
   retains its own full audits. Leave gates, source identity, deadlines and the
   1 MiB cap unchanged. Add no dependency or new abstraction.
3. Run the realistic regression and focused campaign/restore/publication checks.
   Obtain independent diff review, commit and publish this separate branch.

No actual registration, native invocation, retained SNP decode, original-data
comparison, scientific readout or corrective study belongs to this repair.
Software fixture success does not qualify the failed campaign. Historical source,
registration, checkpoint, close, markers and outputs remain immutable. The
eight-cell prerequisite and downstream pilot remain open. A later readout or new
native study requires a separately approved finite plan.
