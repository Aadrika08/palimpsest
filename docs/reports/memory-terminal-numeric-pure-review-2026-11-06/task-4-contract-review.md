# Task4a/4b bounded source contract review

**FAIL — two contract clarifications required before fixture/code work.**

Reviewed the uncommitted Task4a/4b plan against unchanged source at
`5148b3c8062f6911ec6a4417dd8eed4f902bca2d`. This is a source-only contract review,
not a failing runtime/test result. The root's new codec-profile and external-floor
decisions override the older preflight recommendation. Scope is the split,
input/wire bindings, field/role caps and byte ledger only; no full-plan reaudit.

## Required fixes

### 1. Freeze the exact nested audit_schedule shape

Plan lines293–295 preserve inherited index fields and say `audit_schedule equals
Context`, but the inherited base manifest emits exactly
`{event_tick,decision_tick}` (`memory_family_compact_v4.py:684`), whereas
Context.schedule also contains `boundary_tick` (Task1 profile's exact Schedule
schema). Literal equality and inherited nested shape are different wire choices.

**Required contract:** retain base audit_schedule exact keys
`{event_tick,decision_tick}`, equal the corresponding projection of validated
Context.schedule. Bind boundary_tick separately through TerminalProof and row
interval checks. Alternatively root may explicitly choose all three fields for
the new pure schema; in that case declare that nested-shape change explicitly
and reject the old two-field shape. Do not leave the fixture author to decide.

### 2. Freeze per-API proof bindings and the limit of reader-only preservation

The plan names an exact TerminalProof premise and exhaustive byte equality, but
does not give the required binding checks for all three API surfaces. The raw
inputs available to convert/prove differ materially from those available to
read. Source facts:

- Task3a binds canonical Context/report bytes and deterministic writer
  manifest/event bytes; raw.job is only a descriptor
  (`memory_family_terminal_audit_vnext.py:427–436`).
- Task3a's proof contains exact counts/interval, descriptors and the three
  sequence/trace commitments (`terminal_audit_vnext.py:467–476`).
- The inherited row digest explicitly excludes latency and step_latency
  (`compact_v4.py:551–554`, `raw_audit_v4.py:373–375`). A compact reader also lacks
  most original camera pixels, so it cannot rederive each original row_digest
  from the retained fields. Checking the stored digest-array sequence against
  the proof does not independently authenticate all retained array values.
- Numeric V2 distinguishes a stored-only read from a raw comparison, and only
  its prove API compares all companion fields to supplied raw bytes
  (`numeric_preservation_v2.py:200–206,300–314`).

**Required contract:** make the following explicit in the plan/profile before
tests select behavior:

1. Every entry point validates the exact TerminalProof schema/types/coherence;
   read requires `terminal-proof.json == canonical_bytes(receipt)`, and every
   base/envelope proof/Context descriptor binds its fixed actual copied member.
   The proof's original Context descriptor remains unmodified and binds the
   same canonical Context bytes/hash/size. Revalidate Context against the exact
   Task1 profile named by the new codec profile.
2. Convert/prove require the five terminal_raw descriptors to equal the five
   proof descriptors exactly; raw.job equals the proof job D. Bind canonical
   worker_report bytes and both supplied recorded byte strings to their proof
   descriptors. The decoded manifest/events must encode to those exact supplied
   recorded bytes. No job-body or physical-original claim follows.
3. Both layers, copied manifest/events, actual partition census and proof agree
   on owner/case/condition, operation=condition, counts, motor interval and
   applicable terminal facts. Bind proof boundary/source_snapshot/invariant to
   Context; preserve original outcome/goal/capped_ticks/path and terminal-sensor
   relationship without replaying or inventing the source proof. Bind the
   witnessed/committed references to their copied event identities where
   available. Source replay validity remains the stated Task3a premise.
4. Reader recomputes sequence/ASCII-trace hashes from the decoded stored digest
   arrays, compares them to both manifest and proof, validates selected pixels
   against camera digests, and checks copied bytes/index/chunk mappings. State
   explicitly that these are stored-format/commitment checks, not rederivation
   of original per-row digests or proof authentication of timing values.
5. Convert/prove independently project supplied raw rows, rederive all original
   row/camera/trace commitments, compare them to the proof, then compare every
   retained base field and all three companion fields by dtype/shape/tobytes,
   plus selected pixels and copied metadata/event bytes. Only a performed raw
   comparison may report `raw_comparison_performed=true` or equivalent. A plain
   read retains false. No new timing digest/receipt authority is required;
   freeze the honest conditional scope instead.

These obligations do not ask Task4 to repeat Task3's source replay, fabricate a
receipt, change Task3a's proof schema, or implement Task4b. They prevent a weaker
reader or swapped input from being mistaken for the promised raw byte proof.

## Contract portions that pass this review

- The distinct PURE schemas, exactly-null raw_audit/source_identity with
  nonnull refusal, false inherited claims, and deferred actual4b contract avoid
  legacy-receipt impersonation. Old whole readers must refuse this wire. No
  public adapter or always-raising stub belongs in4a.
- The third owned profile has an acyclic identity: Task1 terminal_profile plus
  immutable parent descriptors; base.protocol_sha256 and envelope protocol /
  base_protocol identify the new profile. Context.profile still identifies
  Task1. No self-code hash, accepted pin or Context substitution is introduced.
  Plan line361's phrase “profile identifies that shared code closure” must be
  read subject to line322: a later external closure binds code/profile; the new
  profile itself must not acquire a self/source-code hash.
- The exact nine fixed members plus two per32-row partition agree with the
 16 base arrays and three numeric companions. Zero has exactly nine members,
  empty indexes, no partitions, typed zero-sized audit arrays, null motor
  endpoints, and empty SHA256 sequence/trace commitments. There is no dummy
  row/image or partition0. Canonical re-encoding and predecode fixed stored-ZIP /
  NPY schema checks are required; whole old readers cannot supply zero support.
- Conditional snapshot_reference correctly retains the source CONVERSION hash
  as an explicitly supplied premise, not something manufactured from Context.
- Role bounds preserve the16KiB Context,5MiB events,16MiB SNP identity and stricter
  inherited actual commit/conversion payload bounds. Individual1MiB metadata
  bounds do not grant extra aggregate capacity. The partition/frame formulas
  charge container bytes and permit the empty typed audit container.
- `T=sum(bundle bytes)+external`, with external the complete distinct declared
  metadata cost at least canonical proof + canonical Context + declared
  manifest/report/job bytes, avoids adding the floor twice. Subtract only
  verified19646*n dense bytes,98304*selected_count pixels, and the single actual
  copied event payload from T to obtain overhead. Require a nonboolean
  nonnegative external integer, nonnegative computed ledger components,25MiB
  total and1MiB combined overhead. No descriptor-controlled count may provide
  subtraction credit before actual array/census checks.
- The external floor is deliberately a declared-copy premise. Unknown physical
  extra copies, original raw/source allocations, lifetime/RSS and stage peaks
  remain unproved. These are not free copies or deletion authority.
- Genuine Task3a fixtures0/1/2/31/32/33 may exercise conversion where they fit.
  Private900 partition coverage is only numeric wire coverage. The preflight's
  authored normal900 recording is7,012,715 bytes and remains a5MiB resource
  refusal; this review did not execute it or establish a fitting900 positive.

## Evidence and stop state

Read only the revised plan, Task4 preflight, Task1 profile and relevant compact,
numeric and Task3a source. No source code, tests or profile files were edited;
no tests/imports/probes, native/model/raw/SNP/protected input access, CI,
dependency work, cleanup or subagents were used. Only this review report was
written. HEAD remains the baseline above. No working-set or CodeGraph MCP tools
were available, and this worktree has no .codegraph directory.

All actual qualification, admission, publication, GO and pruning gates remain
closed. Root can resolve the two bounded contract points without widening the
task, then authorize implementation against that exact contract.
