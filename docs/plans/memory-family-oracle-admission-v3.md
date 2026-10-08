# Memory family v3 raw oracle admission

8 October 2026. Software-only implementation plan, based on `e100275` and the
[family oracle contract](memory-family-oracle-v3.md). This unit reads one
explicitly registered source/own-continuation pair. It does not discover a
donor, launch an owner, allocate a study, inspect a matrix result, or qualify the
family runtime.

## Deliverable

Add `scripts/memory_family_oracle_admission_v3.py` with one public function,
`admit_oracle_pair`. The caller supplies the canonical case; independent frozen
plan, protocol, source-identity and history hashes; and two exact registration
descriptors naming the source and retained `own` continuation. The function
validates the bytes and provenance for that pair, projects the complete decoded
events and motor rows into the existing pure oracle, validates the resulting
proof, and returns the proof plus its oracle-only selector resource.

The adapter must never enumerate a run directory to select among donors. It must
not use goal, outcome, commitment, final memory, report geometry or a recorded
target list to choose a pair or compute gold. The existing pure module remains
the only owner of packet, schedule, gate, occupancy, donor replay and gold-target
semantics.

The fixed call is:

```python
admit_oracle_pair(
    case, source, post,
    *, plan_path, plan_sha256, protocol_sha256,
    source_identity_sha256, history_bundle_path, history_bundle_sha256,
    deadline=None,
)
```

Each run descriptor has exactly `run_id`, `run_path`, `job_path`,
`supervisor_path`, `attempted` and `cleanup`; the post descriptor additionally
has `condition: 'own'` and `source_snapshot_sha256`. The return value has exactly
`proof`, `proof_sha256` and `selector_resource`.

## Fixed input and trust boundary

Each source/post descriptor has exact registered run, job, owner, supervision,
attempt and cleanup identities. The post descriptor is fixed to condition
`own` and binds the source snapshot checksum. Run IDs are distinct canonical
UUIDs. All descriptor paths and artifact bytes are untrusted; the expected
case and expected hash bindings are independent caller inputs.

For each explicitly named run, admission must validate:

- safe non-symlink paths and bounded, duplicate-key/nonfinite-safe JSON;
- the registered slot/job/run join, exact case and source identity, CPU FLYNN
  controller, scenario, seed, operation, condition and recording ceiling;
- one matching owner, stopped-owner cleanup receipt, completed bounded
  supervision receipt and bounded logs;
- a terminal manifest, complete ordered events, safe ordered chunks, chunk
  checksums/schema/counts and a stable before/after fingerprint;
- exact policy-call bindings on the full decoded rows before reducing them to
  `{episode,tick,pose,next_pose}` for the pure oracle;
- one registered initial snapshot, its file checksum and durable event prefix;
  the post job/manifest/restore lineage must point to that exact source snapshot;
- strict worker reports coherent with the admitted raw terminal state; report
  outcome fields may be authenticated but never supply oracle gold; and
- a bounded history bundle whose file hash, E hash, fitted U and recorded own
  selector/U provenance all agree.

Reuse the strict readers in `palimpsest.artifacts`, exhaustive chunk validation
in `palimpsest.records.iter_ticks`, snapshot registration and replay helpers,
owner-exit check, policy-binding audit and recording digest. Do not call the old
pilot `read_raw`, `native_manifest_matches`, `audit_run` or generic condition
replay unchanged: their parsing, protocol and condition assumptions are frozen
to earlier studies.

Bindings passed to `memory_family_oracle_v3.oracle_evidence` are derived from
the admitted bytes. They contain the independent protocol, plan and source
identity hashes; source/post run and recording digests; exact report and source
snapshot file hashes; and recorded own selector, U, E and history-bundle hashes.
The adapter immediately calls `validate_oracle_evidence` with the same decoded
inputs and exposes the proof only through `selector_resource('oracle', ...)`.

## Verification and limits

Add `tests/test_memory_family_oracle_admission_v3.py` with one synthetic on-disk
source/own pair assembled from the existing oracle fixture. The passing case
must prove a change row end to end and preserve the input tree. Focused mutation
coverage must reject byte/count/sequence drift, duplicate or unsafe JSON paths,
wrong run/job/owner/supervision joins, non-own or substitute donors, source
snapshot/prefix/restore mismatch, history/selector/U mismatch, report/raw
terminal mismatch and fingerprint drift before a proof is returned. Existing
pure-oracle tests retain coverage of all 48 rows, kinds, schedules, closure sides
and semantic tampering; this adapter test must not duplicate that matrix.

Run the focused admission/oracle suites, affected memory suites, Python compile
checks and `git diff --check`. Have an independent reviewer inspect the final
diff for donor selection, self-authentication, event filtering, TOCTOU and
non-oracle proof leakage. Record exact results in a report before publishing a
draft PR stacked on #98.

This unit admits one already completed software pair. Native producer/job
schemas, historical namespace inventory, storage/time allocation, matrix
completeness, development inference and held-out collection remain separate
future gates. No native owner or model runs in this unit.
