# Integrated source workload independent implementation review

SPEC: FAIL — four bounded contract gaps below.
QUALITY: CHANGES REQUESTED.

Review basis: frozen source-vertical-slice-contract.md plus all six implementation-rulings.md decisions; source-vertical-review-brief.md; implementation report; current named source/tests and retained logs. Root supplies base e0c1e5c764f77867c74ed2f275251d5dfba226d7 and scope. I did not run git, imports, tests, probes, payload reads/hashes, services, CI or network. No source/test changes were made. This report is the only review artifact written.

## Findings, in priority order

### 1. P1 — actual namespace coverage is not deeply validated before runtime/model acquisition

Location: `scripts/memory_family_source_records_vnext.py:430-433`, `:526-550`; acquisition order at `scripts/memory_source_parent_entry_vnext.py:528-546`.

The actual coverage branch checks the outer keys and fixed top-level literals only. It does not validate `sources` as exactly the two fixed source/kind rows, each row's exact keys, or the three bounded integer limits. `validate_held_namespaces` subsequently uses `zip(two_bindings, coverage['sources'])`, so a third source row is silently ignored; extra keys in either consumed row are also ignored. The two actual exports can declare a wrong kind consistently with their corresponding coverage rows because neither actual branch fixes historical/training kinds. This can admit a coverage object outside the frozen original schema, and malformed metadata reaches genuine runtime acquisition before the later checks.

Minimal correction: add a fixed actual coverage validator before `input_closure`/execution. Require exact two ordered source IDs with their fixed historical/training kinds, exact row/NamespaceExpected keys and typed bounded counts/hashes, exact-int limits 1..128/32MiB/100000, and all specified equalities. Reuse original pure v3 rules where appropriate; do not accept the authored schema or fabricate authority. Make the consumer require exact cardinality rather than rely on truncating zip. Add metadata-only refusals for a third source, wrong kind, row extra key, bool/oversized limits, proving refusal before RuntimeHandle entry.

### 2. P1 — raw per-leaf caps are checked after a write can exceed them

Location: `scripts/memory_family_source_runtime_vnext.py:87-102`, `:60-72`; `src/palimpsest/records.py:215-235`, `:241-257`; `scripts/memory_source_parent_entry_vnext.py:355-360`.

The source budget receives only the recording-directory path and incoming byte count. `_check_output_budget` checks each leaf's CURRENT size, while `_admit_source_write` admits against aggregate raw/atomic/report/free-space limits. It cannot distinguish an event append from a manifest replacement. Consequently, an event append can take `events.jsonl` from below 7MiB to above 7MiB; a manifest payload between 64KiB and 7MiB can likewise be published. The next scan may refuse, but the reserved physical leaf cap has already been exceeded. This violates the fixed-roster and ruling6 requirement that admission precede writes; aggregate headroom is not per-leaf admission.

Minimal correction: carry the fixed physical write target/operation through the existing source-only budget seam so events use existing-size-plus-incoming, and manifests/chunks use exact prospective target/pending sizes and their individual caps. Preserve the legacy default seam/behavior. Keep post-write checks. Add near-cap event append and oversized manifest cases that assert refusal before any write or pending allocation and retain the original bytes.

### 3. P1 — publication and failure diagnostics can replace original exceptions

Location: `scripts/memory_source_parent_entry_vnext.py:403-411`, `:421-423`, `:579-581`, `:655-676`.

`_publish_bytes` wraps writing/fsync in `finally: os.close(fd)`, and parent-directory fsync in the same pattern. If write/fsync and close both raise, close replaces the originating exception instead of preserving both original objects in order. Separately, `_failure` protects only its final publication: the preceding output inventory `os.stat` catches only FileNotFoundError, and record construction/notes are outside that protection. An I/O/permission/not-a-directory error while collecting failure diagnostics escapes `_failure` and prevents `_execute` from raising its retained original body/teardown group. These are precisely failure paths where the contract requires diagnostics never to displace the primary.

Minimal correction: use the package-local source error accumulator at both originating publication cleanup sites, with body first and close second. Wrap the entire best-effort diagnostic operation, including inventory/construction, and append any diagnostic failure to the existing failure list before raising the complete group. Preserve every existing pending/final prefix. Add paired write-or-fsync plus close failures, and a diagnostic stat failure after a primary body error; assert original exception identity/order and all attempted closes.

### 4. P2 — per-command/per-row loaded identity checks are narrower than the frozen contract

Location: `scripts/memory_family_source_runtime_vnext.py:129-160`; `scripts/memory_family_source_qualifier_vnext.py:30-53`, `:128-135`; `scripts/memory_family_cell_replay_v4.py:64-66`, `:88-115`.

Section3 explicitly requires loaded model tensor/runtime/provenance identity checks around every queued command/advance and every replay row. The owner calls `_guard_policy` only once after Engine.open; subsequent `check_source` checks storage/lease/deadline, not loaded tensors or runtime identity. The qualifier's row callback calls `_guard_policy`, whose actual branch runs `_pinned_policy` (type/module/provenance pins), without controller-tensor hashes or the runtime eval/no-grad/thread/version checks. The core's `_runtime` and tensor comparisons occur at replay entry/exit. Those end checks are useful, but they do not implement the required intervening checks. This is a literal contract gap, not a claim of hostile Python isolation or observed numeric corruption in the retained positive.

Minimal correction: construct a fixed source-owned identity checker after successful policy load, binding the expected immutable tensor digest plus actual runtime/provenance identity. Invoke it around owner commands/capture/close and through the existing qualifier custody seam before/after rows, keeping mutable recurrent state/caches separate. Retain it only in the owned reference container and clear it during disposal. Leave the old default replay path and actual identity guard unchanged. Add a bounded authored mutation/refusal case at a command/row boundary, verifying that the next operation is not executed and cleanup still drains.

## Checked positive mechanisms and evidence

- Exact sibling lease dispatch and disjoint new record schemas are real; actual entry is a conditional workload mechanism, not an always-refusing stub and not an independent GO/authentication service.
- The parent registers genuine RuntimeHandle owners first, deduplicates same-path descriptors, checks file inode aliases, batches genuine additional holders, and stages exact closed trees. The owner uses real canonical Engine.open, queued policy processing, original SNP capture, close, and source-owned reference release.
- Raw audit independently decodes held raw/SNP bytes and invokes the original row/policy/symbolic oracle algorithms. Numeric conversion writes and rereads genuine 16+3 arrays and physical legacy copies. Qualifier loads a new policy and calls the real whole-trace numerical replay with custody callbacks and independent restoration.
- Package-local `_source_errors` avoids a new Engine/RunWriter dependency on research scripts. Reviewed canonical cleanup branches attempt independent drains; default branches remain separate. The originating parent publisher gap above is additional to those repaired primitives.
- The generated fixture imports its copied upstream cell/agent code and uses real FlynnPolicy with Nin4813/N12 and generated weights/graph/mappings. Its MuJoCo/environment acquisition geometry and native serialization remain controlled authored boundaries. The runtime executable/distribution bytes are fixture premises, not the executing installed runtime's qualification.
- Read retained green04: 57 passed; green05: 164 passed; green06: 44 passed including the full-parent positive and real early-termination test. These scopes overlap and are not a combined all-green count. I did not rerun them. The report supplies the latest 20-row/157-event artifact details; I did not open or hash those retained output payloads.
- The full-parent test directly asserts authored candidate scope, 4813 input width, numerical endpoint equality, state restoration, disposal, and absence of acceptance/lifetime outputs. It does not cover the four negative cases above. Earlier failed waves and the earlier full-parent pass remain historical evidence. Early RED03/GREEN01 tiny-fixture cleanup is disclosed; later retained evidence does not retroactively preserve it.

## Limits and disposition

The reported authored positive is meaningful integrated software evidence. It is not actual full-model/native/source feasibility, accepted Q, or a cost measurement; unit elapsed times and resource ceilings must not become experiment costs. Actual external authorization/GO, provider/backend, load/isolation/resources, two independently authorized namespace exports, accepted Q and L/F/R remain absent.

Return the four grouped fixes to the same implementer, with only focused new/changed verification justified by those fixes. No unchanged broad reruns, alternative architecture, actual payload access or scientific execution is requested by this review. Root retains integration judgment.
