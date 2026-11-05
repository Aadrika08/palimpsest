# Exact change-audit numerical checker

`check.py` uses only the Python standard library. It imports no Palimpsest runtime,
model, simulator, numerical dependency or formal-verification toolchain. It
performs no I/O, launches no processes and mutates no supplied records.

`check_audit(spec, rows, expected_protocol_sha256=..., expected_spec_sha256=...)`
checks one fixed grid of declared families and contrasts. Expected digests must
come from the caller's independently frozen specification, not be reconstructed
from an untrusted proposed replacement. The spec digest is SHA-256 of ASCII JSON
with sorted keys, separators `(',', ':')`, `ensure_ascii=True`, and
`allow_nan=False`. The return includes the digest of row-by-row canonical JSON
followed by a newline for every row, in the supplied order.

## Input schema

`immutableAuditSpec-v1` has exactly these fields:

- `schema`: `immutableAuditSpec-v1`;
- `protocol_sha256`: lowercase 64-character SHA-256;
- `family_ids`: complete unique ordered list of family IDs;
- `family_count`: positive integer equal to that roster's length;
- `contrast_ids`: complete unique ordered list of fixed contrast IDs;
- `alpha`: exact rational strictly between zero and one;
- `fixed_lambda`: exact rational in `(0, 1]`, chosen outside this checker;
- `upper_log_budget`: positive exact rational `q` at most 64;
- `log_evidence`: exactly `method`, `terms`, `proof_receipt_sha256`.

Every rational is exactly `{"numerator": integer, "denominator": positive integer}`.
Booleans and floats, including nonfinite floats, are rejected. IDs use 1–128 ASCII
letters, digits, underscore, hyphen, period or colon. The log-evidence method is
`exp-taylor-lower-v1`; the receipt hash is a reference only, never authenticated or
authoritative here. The checker does not accept a `lean_certified` flag.

Each observation has exactly `family_id`, `contrast_id`, `status`, and
`loss_difference`. Every planned family/contrast combination must occur exactly
once, with status `completed` and exact rational loss difference in `[-1,1]`.
Missing, refused, failed, incomplete, unregistered, duplicate or extra observations
raise `ValueError`; no subset is silently scored. The caller retains all original
records and failed checker outcomes separately. Duplicate JSON keys must be
rejected by any external JSON decoder before constructing the dictionaries.

## Arithmetic and limits

For `K` fixed contrasts, the checker requires the exact finite Taylor lower sum

`sum(q**k / k!, k=0..terms-1) > K / alpha`.

Since `q > 0`, this sum is below `exp(q)`, so its checked inequality establishes
`q > log(K/alpha)` conservatively. An insufficient lower sum refuses even if a
longer sum could establish the inequality. No floating-point logarithm or
exponential is evaluated, and no provided `q` is trusted without this check.

For each contrast it computes, exactly:

`upper = mean(loss_difference) + q / (fixed_lambda * family_count) + fixed_lambda / 2`.

Resource limits are 4,096 families, 64 contrasts, 256 Taylor terms, at most 128 bits
in each supplied integer component, and 4,096 bits in accumulated rational sums,
Taylor terms/sums and final endpoints. Resource overflow refuses; it never rounds,
clips a scientific value, or switches to floating point. The finite Taylor
bound and input-size limits make checking costs bounded; they do not establish
an operational runtime SLA.

## Evidence boundary

`numerical_improvement` is true only when the computed upper endpoint is strictly
negative. An endpoint equal to zero is inconclusive. Every result sets:

- `sampling_eligibility_verified: false`;
- `theorem_receipt_verified: false`;
- `certified_improvement: false`.

Those values remain false even for negative numerical endpoints and plausible
receipt hashes. Completeness and exact arithmetic do not establish fresh sampling,
family independence, correct loss/contrast construction, prior or lambda selection,
protocol precommitment, adaptive validity, theorem applicability or proof-kernel
execution. This is a numerical enclosure checker, not a sampling/theorem bridge.

## Verification

```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -m unittest discover -s paper/studies/change_audit_v1/tests -v
```

The initial TDD run retained in `tdd-red.log` has 20 expected assertion failures
because the checker did not exist. First green attempt retained one message-case
mismatch (`tdd-green-attempt-01.log`), then `tdd-green.log` passed all 20 tests.
A later resource-growth regression failed as expected in `tdd-red-resource.log`;
after tightening exact-rational work bounds, `tdd-green-final.log` passes 21 tests.
These are synthetic arithmetic/schema tests, not experimental observations.

## Closed Lean numerical-witness emission

`emit.py::emit_lean_certificate` calls this checker and returns `lean_source` plus
metadata. It performs no file I/O, subprocess invocation or Lean execution.
The expected protocol and spec hashes remain mandatory independent inputs.
Only validated rational literals and hexadecimal identities enter Lean text;
family and contrast IDs stay in metadata and never become Lean identifiers/code.

The generated source imports `ChangeAudit.Numerical` and invokes
`rational_family_log_enclosure` with the exact `K`, `alpha`, `q` and Taylor term
count. Its finite inequality is discharged with
`norm_num [Finset.sum_range_succ, Nat.factorial]`. Each contrast embeds the complete
loss-difference list in registered family order, proves its length and exact
rational mean, and proves its real-valued conservative endpoint equals the
checker result. An endpoint below zero receives a strict-negative numerical
lemma; otherwise a nonnegative lemma is emitted. User-supplied input-row order
is preserved by the observation hash, while loss-list order uses the independently
registered family roster.

Code-generation limits are **128 families, 8 contrasts, 32 Taylor terms** and
**256 KiB for the entire canonical ASCII-JSON serialized return value** (source
and metadata together). Export limits are deliberately tighter than the generic
numerical checker; larger exports refuse without changing checker semantics.
The source is generated, not compiled: metadata always marks source compilation,
sampling eligibility, theorem application, theorem receipt and certified
improvement false. Even a later compiled numerical witness would not establish
the stochastic sampling premises or bind simulator behavior to the theorem.

`tests/test_emit.py` covers the exact `-1/4` example, heterogeneous row ordering,
nonnegative/zero endpoints, code-like identifiers, incomplete grids, identity
drift and generation/byte caps. `tdd-emit-red.log` retains ten expected failures
before implementation; `tdd-emit-green.log` retains ten passing tests. No Lean
compiler was invoked by those tests or this source lane.
