# Puck-v3 interval adapter source boundary

This slice implements the pre-action decision and pure completion-admission
parts of the frozen on-policy plan. It does not route a native owner, step an
environment, publish a recording, discover a registry, or access retained
models/scenes. Historical owner envelopes and recording schemas are unchanged.
The frozen protocol bytes remain at SHA-256
`fe8b2615f965a114274a13aeb2d49c26d3f79e0920eee72bce4eb671adff3d13`.

`puck_on_policy.stage_interval(sensors, world, teacher_mode, own, model, *,
terminal_reason, capture_query_state)` returns a fresh staged decision. It
prepares float32 sensors8/features9 with the own BEFORE-mode bit, queries the
unchanged teacher once, checks BEFORE/AFTER-mode agreement and query isolation,
then calls the existing student decision once. The float64 teacher target and
predicted/executed student actions occupy separate fields. The adapter performs
no action execution; a later owner may execute only `staged['row']['action']`.
No condition filters a valid interval. Its row tick is the existing zero-based
record tick; its candidate cursor tick is the next completed interval.

The v3 numeric row uses `teacher_query_mode_before` and
`teacher_query_mode_after`, preserving the same uint8 mode codes while keeping
the historical `teacher_mode_before`/`teacher_mode_after` columns absent.
The unchanged historical teacher-data reader therefore rejects v3 rows rather
than interpreting the executed student `action` as a teacher target. The
unchanged historical student action-replay reader also rejects the v3 row's
teacher-prefixed fields. V3 completion admission checks the exact new row
fields; copying a historical mode column into it also fails admission.

The explicit capture callback must return exactly `native_state`, `observation`,
`python_rng`, `numpy_rng`, `torch_rng`, `environment_rng`, and `space_rng`.
Typed `state_digest` hashes the returned state together with the live sensor
packet, independently prepared features, own cursor, and world before and after
the teacher query. Immediate hashes detect mutation even when the callback
returns the same mutable object. Student inference also cannot change the live
sensor packet, own cursor, world, or staged feature/transition bytes. The
callback must observe rather than mutate state. These synthetic checks prove
the comparison mechanism only: a later native capture implementation needs
separate coverage and isolation qualification for all relevant native caches,
effective observations, and Python/NumPy/Torch/environment/space RNG states.

`puck_on_policy.admit_completed_interval(staged, own, teacher_mode, *,
completed_tick, publication_receipt)` returns `(next_own, next_teacher_mode)`.
It verifies the unchanged predecessor, strict contiguous completed tick,
sensor-derived transition, exact typed features/modes/actions, and a receipt
whose typed digest equals exactly:

```python
{
    'version': 1,
    'kind': 'puck-on-policy-row-publication-v1',
    'protocol_sha256': puck_on_policy.PROTOCOL_SHA256,
    'status': 'published',
    'completed_tick': completed_tick,
    'row_sha256': state_digest(staged['row']),
    'staged_sha256': state_digest(staged),
}
```

This is a new adapter-only receipt, not an alteration of a historical schema.
The receipt is supplied evidence, not authenticated proof: the pure function
cannot establish that a native step completed or that a durable writer really
published the bound row. The later native/writer owner must produce it only
after successful completed-step and atomic-row publication admission, then
install both returned cursors together. A step/record failure must produce no
successful receipt and stop the batch. Natural terminal intervals remain
retainable; the next decision rejects any non-`None` terminal reason. There is
no rollback of a physics step, cursor repair, retry, or partial row promotion.

Verification used Python 3.11.15 and NumPy 2.2.5 from the existing reproduction
environment, with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.`. The initial RED
commit rejects the absent API; the second RED commit reproduces inference
mutation of retained sensors/world. The GREEN focused interval suite passes
10 tests and the complete affected on-policy synthetic suite passes 49 tests.
The schema-repair RED faithfully showed the historical teacher reader accepting
the student action as its target while ignoring the separate teacher label;
the new column names close that collision without editing either old reader.
Synthetic calls replace the numerical inference boundary; no Torch or MuJoCo
runtime is imported. Compilation, fresh imports, protocol-byte identity and
diff-whitespace checks passed. Broader
execution/training/development/held-out qualification is outside this slice.
