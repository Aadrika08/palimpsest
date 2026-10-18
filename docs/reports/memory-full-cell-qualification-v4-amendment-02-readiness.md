# Memory qualification amendment 02: source ready, execution pending

Independent review approved source commit
`d6ce5fc27127c4baeece233359720f565f0421df` and the exact
[execution freeze](../plans/memory-full-cell-qualification-v4-amendment-02-execution.json).
Its SHA256 is
`1bfc3245c30130bcb72e5d5d2afc2fae99f6a0052e117dea001d98d40e52cd2f`.
No blocking source or freeze findings remain. **Explicit user approval is still
required before one attempt 02 invocation.** No attempt 02 directory has been
reserved, and no actual qualification has run under this amendment.

The [amendment](../plans/memory-full-cell-qualification-v4-amendment-02.md)
registers the original interpreter's exact 21,662,864-byte size and unchanged
SHA, preserving the generic 1 MiB unknown-metadata cap. It preserves the original
model, three traces, seed, 737 positives, four negatives, maximum 1,470 cell calls
and all process/time/storage limits. It holds the prior failure, freeze and seven
output files as additional metadata. Attempt 01 remains consumed and unchanged.

## Evidence and scope

- The amendment's 19 authored metadata/temporary-file tests and the existing
  89 qualification/custody tests passed: **108 tests in 2.18 seconds**. Independent
  review repeated the same slice: **108 passed in 2.19 seconds**.
- Meaningful rejection checks include incorrect runtime size/hash, changed
  original inputs/limits, wrong prior failure, numeric type aliases and a mixed
  approval receipt. The 21,662,864-byte holder test uses an authored sparse file.
- Independent review verified the exact 166-file source closure, immutable prior
  index/freeze hashes and all seven lossless prior output copies. No protected
  model/raw/SNP/ZIP/runtime-binary content was opened for these source checks.
- These results establish source readiness. They do not establish a passing
  full-model replay, family admission, pruning, fitting, held-out or scientific
  claim. All seven simulation release gates remain open.

## Exact prospective invocation

Only after actual user approval of this freeze, invoke once from
`/home/utkarsh/Work/shraddha/brain/.worktrees/memory-replay-custody-v4`:

```sh
CUDA_VISIBLE_DEVICES="" MKL_NUM_THREADS=1 MUJOCO_GL=egl \
NUMEXPR_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. \
/home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python \
  -m scripts.qualify_memory_full_cell_v4 \
  --freeze docs/plans/memory-full-cell-qualification-v4-amendment-02-execution.json \
  --freeze-sha256 1bfc3245c30130bcb72e5d5d2afc2fae99f6a0052e117dea001d98d40e52cd2f \
  --approved-amendment-sha256 1bfc3245c30130bcb72e5d5d2afc2fae99f6a0052e117dea001d98d40e52cd2f
```

The confirmation flag records trusted operator approval; it is not approval
itself. The runner reserves the distinct attempt before protected access and
owns its timeout/worker supervision. Require an externally observed exit 0,
complete custody and terminal receipts, successful negatives and an independent
result audit before accepting a pass. Missing inputs, drift, limits or cleanup
failure consume this allocation; retain the failure and do not retry.

CPU-only, zero native owners and zero physics steps remain fixed. Internal,
normal-return and hard supervision limits are 600/650/660 seconds. The sampled
6 GiB RSS stop threshold is not a hard memory bound. Output is capped at 128 MiB,
with a 2 GiB free-space floor. Recheck disk immediately before an approved run.
