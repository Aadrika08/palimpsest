# Staged memory pair admission: source evidence

The new read-only `admit_staged_compact_pair` entry point resolves only its
registered canonical case paths through `.pending/<case>`, holds the source
commit and complete read-only directory/file identities, and runs the existing
nine-condition pair proof. Returned receipts keep final portable paths. The
existing final-bundle API does not admit staged inputs. No directory alias,
snapshot copy, receipt publication or additional permanent file is created.

RED `e549bb0` retained 19 failures for the missing entry point. After
implementation, all 19 tests passed, covering nine conditions, audited natural
failure, marker identity/type tampering, missing markers, quarantine/temporary
markers, mixed final aliases, late marker drift and mutation-free admission.
The full five-file affected slice passes **262 tests in 88.87 seconds**:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  ../r0-reproduction/.venv/bin/python -m pytest -q \
  tests/test_memory_staged_pair_v4.py tests/test_memory_family_producer_v4.py \
  tests/test_memory_family_oracle_admission_v4.py \
  tests/test_memory_family_raw_audit_v4.py tests/test_memory_family_compact_v4.py
```

All 18 behavior-source pins, pure import without Torch/MuJoCo/Engine/model,
compilation and whitespace checks pass. The prospective protocol SHA is
`2530626bffc785388322750c4665010968edd12ed7ea22205106c55c21105b4e`.
Only this branch's changed behavior pin was resealed; historical receipts and
frozen protocol bytes remain on their original branches. Independent review is
the next publication gate.

This admits supplied compact bundles and immutable receipt/marker bindings. It
does not authenticate native job/control/cleanup assertions or independently
reconstruct bytes omitted by compaction. Existing raw-receipt authority boundaries
remain in force. It is one prerequisite of condition closure, not complete
condition/case publication, recurrent-cell qualification, pruning or allocation.
All claims remain false. No model, native owner, retained run, development or
held-out block was opened. CI and the physical rover remain excluded.
