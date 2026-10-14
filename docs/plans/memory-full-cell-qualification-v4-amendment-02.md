# Full-model cell qualification amendment 02

**Status:** prepared for source/freeze review and user approval; not execution
permission. This is one new allocation, not unused capacity from attempt 01.

## Reason and preserved baseline

Attempt 01 on source `59270515f93a9c93820cb105fb5dec82e9744d4a` failed during
runtime-file custody before numerical worker launch. The original interpreter
is regular, single-link and 21,662,864 bytes; its SHA remains
`572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a`.
The unknown-size 1 MiB descriptor was incorrect. The
[failure index](../reports/memory-full-cell-qualification-v4-attempt-01-evidence/index.json)
and [original freeze](../reports/memory-full-cell-qualification-v4-attempt-01-evidence/execution-freeze.json)
remain byte-identical. Original source is retained in Git; PR #118 stays on the
consumed failure. No recorded result or model/input byte is corrected.

## Exact amendment

Use schema `memory-full-cell-qualification-v4-amendment-02` and attempt number 2
in a distinct `runs/memory-full-cell-qualification-v4-attempt-02` directory.
Register the runtime file with its exact 21,662,864-byte size and unchanged SHA;
remove only that descriptor's unknown-size `max_bytes` field. The generic 1 MiB
unknown-metadata cap stays unchanged. Metadata custody additionally holds the
committed prior index, original freeze and all seven original output files.
Source custody pins this new plan and the current executable source closure.

Everything else remains fixed: original raw root and 45-file roster, all model
assets/mappings, metadata, interpreter path, environment, seed 400 and traces
`e91cf0a8efbe4712b01a0a469991fcb8`, `e0277617fcd64bc0b1314f723b45b30f`,
`4c41bdc2007940a9bbade1f65add77b9`. All 737 positive cells, bitwise actions/raw
outputs and three hidden endpoints must pass. The four original negatives and
1,470-call maximum remain unchanged. No source trace, perturbation or model may
be replaced after observing an outcome.

## Invocation and admission

The existing runner recognizes only the original schema and this exact amendment.
It binds the immutable prior failure and compares every unchanged input role to
the original freeze. The parent and worker receive the same amendment identity.
The default invocation also requires
`--approved-amendment-sha256 <exact-reviewed-freeze-sha256>`; a missing or different
value refuses before reservation/protected access. This flag records the trusted
operator's confirmation. It cannot replace actual user approval.

Use the registered Python/module with the exact new freeze path and SHA. Retain
all original environment values. The parent and worker inherit the same owned
timeout group; no new physics or model owner path is introduced. Source and
freeze GO plus explicit user approval are required before the one invocation.
There is no automatic invocation or third-attempt grant.

## Unchanged limits and result boundary

CPU / float32 / one numerical thread; Python 3.11.15, NumPy 2.2.5, Torch 2.9.0
and the authentic recorded Torch profile. Zero GPU, Engine, MuJoCo decoder, physics
steps, native owners, fitting, family development or held-out access.

600 seconds internal from the new reservation, 650 seconds normal return and
660 seconds hard supervision; sampled 6 GiB RSS at 0.05-second intervals, 2 GiB
free-space floor, 128 MiB total new output, 1 MiB per log/result and unchanged
process/drainage/publication guards. Missing inputs, mismatches, limits or cleanup
failure consume this allocation and stop. Preserve every failure without retry.

Acceptance requires timely external exit 0, no failure marker, complete immutable
custody, all positive/negative checks and independently audited evidence. A pass
qualifies only full-model encoded-cell replay for these historical traces. All
family/pruning/held-out/scientific grants remain false; the seven release gates,
condition/case close and physical rover deferral remain unchanged.

## Source checks before approval

Temporary metadata tests must reject wrong prior failure, changed original roles,
unknown/incorrect runtime size or hash, altered limits, type aliases and approval
identity mismatch. Verify old freeze/evidence byte identities and propagation of
the new schema, attempt number and confirmation through parent/worker argv.
Run the affected custody/qualification checks and obtain independent source and
exact-freeze review. These tests must not start this actual allocation or open
model/raw/SNP inputs.
