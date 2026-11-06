# Legacy frozen-pin diagnosis — proposal only

No production code, protocol JSON, frozen pins, schema, trust anchors, dependency environment or test policy was changed. Only this diagnosis directory was written. No actual model/raw/SNP/catalog payload was inspected; the sole pytest invocation used one pre-existing authored numeric node. No model/runtime qualification is claimed.

## Finding and measured evidence

The legacy failure is the intended production source-identity refusal against the active case-publication profile. It is independently reproducible without importing the new terminal numeric codec or its test module. It is not evidence that the new codec mutates legacy globals.

- `scripts/memory_family_compact_v4.py:26` selects `memory-family-compact-evidence-v4-case-publication-v1-protocol.json`; `behavior_source_identities` at lines 226–240 reads only declared source bytes and refuses the first mismatch.
- `tests/test_memory_family_numeric_preservation_v2.py:135 → fixture:86 → declared_receipt:58 → raw_audit.canonical_source_identity:106 → compact.behavior_source_identities:240` is the fresh failure chain. Failure happens before any conversion assertion.
- Fresh exact node `tests/test_memory_family_numeric_preservation_v2.py::test_exact_roundtrip_and_partial_partition[source-1]`: **1 failed in 0.21 s, exit 1**, `ValueError: Behavior source differs: engine`. Its command/environment, full output and exit record are `isolated-01-command.json`, `isolated-01.log`, `isolated-01-exit.json`; its fresh basetemp is retained.
- Supplied `task-4-evidence/final-green.log` is RED despite its prospective filename: inventory says **111 failed, 235 passed, 2 skipped, 13 errors**, and all 124 recorded failure/error messages say `Behavior source differs: engine`. That aggregate was read, not rerun here. Supplied 67 new-codec passes do not make the combined gate green.
- Fixed main is `5547efc6dd7210e7a35aa02536140c351c7104b1`, an ancestor of the inspected HEAD. All **93** unique byte pins in the active base behavior sources plus condition/publication source pins match the file at that fixed main commit. `source-pin-evidence.json` records each named source path/digest comparison; this was not an all-tracked-file hash.
- Current Engine SHA256 `7001059ce5c8b7b7659cbbe848ce01d1bbadf9e32215d9fa0aa11738eb10ccc4`, 110241 bytes, differs from frozen `f3a3cbf3537583151ab2f4d68fa83078f0988e853b7c9ca9adfc2cf841447d0b`, 99631 bytes. Source history places the private transition persistence/strict path guard change at Task 2a `8970a96`.
- There is a **second** current drift after Engine: `src/palimpsest/memory_decision.py` is `064c589f33711b4afd5de995f0132562cd5808ca1b420444a24c68ddeadb8526`, 33942 bytes, versus frozen `f22e72166fbd8a7cf7c1d01a9535f202e7f6b99246c298bc970274a04c863982`, 32168 bytes (Task 1 source history includes `7f3c783` and `5d9c204`). Removing the first refusal would merely expose this second drift.
- Active profile JSON bytes and `scripts/memory_family_compact_v4.py` are exactly unchanged from fixed main. Current active protocol SHA256 is `84ab31e256880723a08ffda265898d560f1b130b498630086c315196321b3285`; compact source SHA256 is `d3ae9db80d9b3420b30af6045fb3f0b3880ea81fec0c3194fa0f598bd0ed0309`.
- During diagnosis root authorized concurrent Task 4 review-candidate commit `4fd9cb8379dfc46934783eab7388287d6b8b29bb`, child of handoff HEAD `5148b3c`. Its three new files are outside the legacy behavior-source closure. Parent confirmed Engine and memory_decision unchanged by that commit. Diagnosis made no HEAD change.

## Why the existing skip group is insufficient

`tests/frozen_pins.py:_memory_v4_pins` reads the older retained-condition JSON, not the active case-publication JSON. Reusing that loader for newly affected current-profile tests would attach the wrong historical contract. Existing IDs already owned by the old group must not be duplicated or silently reassigned; their historical reasons remain intact. `affected_tests()` rejects duplicate registry keys.

The accepted ADR `docs/plans/frozen-source-pins-after-integration.md` permits conditional historical test skips with real JSON pin loaders and historical-byte verification. It forbids changing production refusals or silently updating frozen protocols. Use that policy here; no prospective re-pin or runtime bypass is proposed.

## Direct and transitive dependencies

| Tests | Source dependency | Proposed handling |
| --- | --- | --- |
| numeric_preservation_v2 | 13 functions call local fixture → declared receipt → canonical source identity; 5 use public_raw → unchanged public auditor | Register the 18 explicit functions below; leave canonical metadata, pure limit/import and bounded NPY parser tests active. |
| raw_audit_v4 | Public auditor enters canonical source identity before inventory/row/terminal semantic checks | Existing 7 registry entries remain owned by old profile. Add only listed missing guard-dependent assertions/parameters. Keep pure terminal validators, pure limits, deadline gates and pre-source path rejection parameters active. |
| compact_v4 | Direct source-binding assertion already registered; other authored converter/read fixtures do not call canonical source identity | Add no new blanket entries. Existing historical canonical/source-binding IDs remain owned by their group; all pure codec checks stay active. |
| oracle_admission_v4 | _fixture calls raw_audit.canonical_source_identity; module explicitly imports autouse authored_current_profile | Existing historical IDs stay owned by old group. Remaining pure protocol/import tests stay active; no new entries. |
| retained_condition_profile_v1 | Two historical successor-identity assertions already registered | Add no duplicate IDs. |
| case_publication_v1 | Historical rejection test explicitly selects old JSON; published-case fixtures explicitly install authored current profile | Keep all these tests active, especially production-refusal and empty-trust negatives. |
| case_publication_profile_v1 | 3 functions compare live source identities or generator-produced descriptors to frozen profile | Register exactly 3 below. Historical-byte/contract/closure-membership and accepted-source refresh rejection tests stay active. |
| source_seal_v2 | local fixture → imported producer.fixture → raw auditor subprocess | 30 explicit fixture callers below. Importing a producer function does **not** bring the producer module's autouse fixture into this caller module. Keep pure import check active. |
| source_runtime_v2 | 2 authored owner tests call public raw auditor | Register exactly 2 below; all other pure owner/admission/layout/early refusal tests remain active. No runtime was executed here. |
| source_qualification_v2 | harness → authored owner → unchanged auditor subprocess → optional numeric publication | Explicit later-stage functions/parameters below are historical candidates. Keep accounting, failed-owner and child-teardown cases that never launch auditor active; exact late/success parameter entries prevent over-skipping mixed tests. |
| producer/condition_close/retained_source/retained_condition/replay_custody/retained_case/case_publisher/current_semantics | Explicit authored_current_profile opt-in, or explicit authored published template | Keep existing authored semantics active; do not expand the registry to these modules. Their historical IDs already listed elsewhere stay unchanged. |
| terminal_audit_vnext/terminal_numeric_vnext | Import only pure authored raw/compact row constructors | No registry addition. Pure helper imports alone do not reach the frozen guard. |
| staged_pair_v4 | Imports oracle fixture without importing autouse authored profile | All four guarded historical functions already registered; add no duplicate entries. |

A source-only transitive search found source_seal, source_runtime and source_qualification beyond the original seven direct files. This is why a numeric-file-only registry fix is incomplete.

## Proposed ownership and mechanism — four files only

1. `tests/frozen_pins.py`: add distinct `memory-family-compact-v4-case-publication-v1` group. Loader reads `behavior_sources` from the active base JSON and `source_pins` from condition/publication JSON, merges actual path→digest pairs, rejects conflicting duplicate path pins. The union is currently 93 named source/config/document/test files. Do not copy digests into test source, mutate JSON, or reuse retained-condition pins. Retain existing groups/IDs. Adding the helper's own source bytes to drift is expected: tests/frozen_pins.py itself is in the historical publication closure.
2. `tests/conftest.py`: support exact parametrized-node lookup **first**, then existing unparametrized function lookup. Apply the existing skip only when that selected group's actual pins drift. This preserves untouched assertions and early-gate parameter cases. No monkeypatching live readers, fixture-wide guard bypass, file-wide skips, catch-and-skip-on-ValueError, or xfail.
3. `tests/test_frozen_pins.py`: retain all existing historical, uniqueness, real-drift and stale-function checks. Extend existence checking to understand exact parameter suffixes, and verify exact IDs against focused collection; test exact-first lookup, fallback lookup, unrelated nodes remaining active, all-pins-match producing no skip, one-pin drift producing an explicit reason, and ambiguous duplicate/base-plus-exact registrations failing rather than masking ownership. Use authored temporary source files for mechanics. Historical verification must still establish every one of the 93 real JSON pins at an ancestor commit (already independently checked against fixed main here).
4. ADR: document the new historical case-publication group, actual JSON sources, the explicit function/parameter policy and reduced historical execution coverage. Distinguish skipped historical assertions from current semantic replacements and passing checks.

`proposed-node-registry.json` below is a concrete source-derived review proposal, not installed policy. Its exact parameter IDs must be validated by focused collection before implementation acceptance. Unparametrized entries include all their parameters; exact entries intentionally preserve independent early-gate variants. Existing registered IDs must be rejected from this addition. No edits to the original test bodies are needed under the parameter-aware approach.

### tests/test_memory_family_numeric_preservation_v2.py

```text
test_exact_roundtrip_and_partial_partition
test_converter_refuses_numeric_domain_without_coercion
test_population_other_domains_are_ineligible
test_envelope_exact_schema_and_bijection
test_rehashed_companion_archive_corruption
test_unchanged_public_raw_receipt_and_all_row_proof
test_rehashed_numeric_bits_fail_at_exact_field_tick
test_population_row_and_column_permutation_fail_raw_proof
test_old_base_proof_is_not_bypassed
test_actual_serialized_byte_accounting_and_external_combined_bound
test_each_partial_companion_matches_independent_zip_npy_size_model
test_complete_operation_maximum_has_every_row_and_actual_serialized_ledger
test_nested_exact_schema_fields
test_sign_of_zero_is_preserved_and_not_equated_in_raw_proof
test_valid_v1_metadata_can_exhaust_combined_v2_budget_without_padding_conversion_json
test_rehashed_receipt_counts_must_match_the_exact_base
test_numpy_timing_scalars_are_exact_but_python_values_are_not_coerced
test_raw_audit_declaration_has_its_original_canonical_byte_bound
```

### tests/test_memory_family_source_seal_v2.py

```text
test_public_numeric_source_roundtrip_retains_originals
test_source_fixture_is_accepted_by_unchanged_public_raw_audit
test_change_and_restore_during_final_rename_is_refused
test_invalid_input_fails_before_candidate_writes
test_occupied_or_aliased_namespace_is_never_reused
test_publication_failures_preserve_raw_and_partials
test_rehashed_numeric_candidate_must_match_raw
test_actual_disk_reread_detects_changed_candidate
test_raw_backed_reader_retains_input_witnesses_until_return
test_reader_rejects_changed_disk_or_unknown_members
test_deadline_never_returns_accepted_result
test_late_descriptor_close_failure_is_quarantined
test_quarantine_failure_is_indeterminate_and_retains_evidence
test_ledger_accounts_unique_physical_paths_and_all_reserved_metadata
test_valid_raw_that_cannot_fit_combined_metadata_is_retained_failure
test_rehashed_published_numeric_bits_reach_raw_comparison
test_candidate_file_witness_survives_final_rename
test_additional_controls_are_held_charged_and_bound_in_conversion
test_auxiliary_control_can_make_combined_overhead_ineligible
test_auxiliary_control_change_and_restore_at_rename_is_refused
test_duplicate_registered_physical_role_counts_once_but_real_copy_counts_twice
test_invalid_additional_controls_fail_before_writes
test_evidence_root_replacement_and_restore_is_refused
test_unbounded_disk_inventory_is_refused_before_opening_payloads
test_indeterminate_writer_marker_never_proves_process_success
test_rehashed_base_snapshot_metadata_must_match_held_original_snp
test_registration_preflight_rejects_nondevelopment_before_case_construction
test_registration_descriptor_root_is_refused_before_any_payload_open
test_control_descriptor_roots_are_refused_before_control_payload_open
test_review_fix1_prepared_marker_change_restore_during_real_rename_is_refused
```

### tests/test_memory_case_publication_profile_v1.py

```text
test_prospective_profiles_exist_and_bind_exact_current_source
test_profile_generator_checks_without_rewriting_registered_bytes
test_initializer_source_binding_does_not_relax_evidence_paths
```

### tests/test_memory_family_source_runtime_v2.py

```text
test_acquired_source_emits_exact_v4_manifest_and_report
test_invalid_prefix_is_rejected_by_unchanged_raw_audit
```

### tests/test_memory_family_raw_audit_v4.py

```text
test_rejects_normal_episode_terminal_spliced_before_natural_failure
test_rejects_inexact_sensor_only_natural_failure
test_rejects_external_hardlink_to_any_raw_file
test_rejects_undeclared_policy_sensor_even_when_hash_is_rebound
test_rejects_invalid_or_unbound_all_tick_values
test_rejects_terminal_and_condition_oracle_mismatch
test_rejects_source_restore_lineage_or_snapshot_mutation
test_rejects_size_caps_before_hashing_oversized_file
test_rejects_wrong_run_case_condition_or_source_identity[case_id]
test_rejects_wrong_run_case_condition_or_source_identity[condition]
test_rejects_wrong_run_case_condition_or_source_identity[source_run_id]
test_rejects_wrong_run_case_condition_or_source_identity[source_snapshot_sha256]
test_rejects_wrong_run_case_condition_or_source_identity[source_identity_sha256]
test_rejects_mutated_spliced_or_aliased_raw_tree[chunk-byte]
test_rejects_mutated_spliced_or_aliased_raw_tree[foreign-event]
test_rejects_mutated_spliced_or_aliased_raw_tree[eyes-event]
test_rejects_mutated_spliced_or_aliased_raw_tree[hardlink-alias]
test_rejects_mutated_spliced_or_aliased_raw_tree[extra-file]
```

### tests/test_memory_family_source_qualification_v2.py

```text
test_duplicate_output_is_not_a_new_attempt
test_closure_final_recheck_prevents_export
test_terminal_export_control_identity_corruption_prevents_seal
test_parent_keeps_venv_alias_and_independent_audit_command
test_postseal_final_read_failure_quarantines_without_deletion
test_held_input_exit_failure_is_quarantined_before_terminal
test_controls_remain_bound_after_creation_until_export
test_original_freeze_teardown_drift_is_caught_under_lease
test_parent_calls_real_public_numeric_writer_and_rereader
test_parent_censuses_ancillary_control_prefix_and_zero_leases
test_parent_complete_census_refuses_unaccounted_or_oversize_outputs
test_control_census_stays_held_across_real_numeric_publication
test_terminal_failure_quarantines_numeric_candidate
test_indeterminate_public_writer_is_stopped_and_never_resumed_by_reader
test_writer_lease_teardown_error_is_not_a_successful_parent
test_fresh_controlled_home_bootstraps_before_parent_lease
test_parent_records_and_passes_inherited_cpu_clamp
test_v4_parent_and_child_hold_independently_same_deadline
test_v4_full_combined_metadata_sum_includes_freeze_job_logs_tail
test_v4_new_copy_and_stage_created_manifest_remain_charged
test_v4_one_byte_over_retains_failure
test_v4_consistent_json_cannot_qualify_accounting_backend
test_v4_added_requirements_copies_count_in_combined_metadata
test_v4_parent_only_late_close_retains_and_quarantines_provisional_marker
test_raw_and_snapshot_remain_after_pass_or_failure[False]
test_actual_new_profile_file_bytes_are_checked_and_held[True]
test_independent_auditor_rejects_corrupt_authored_source[raw-hash]
test_independent_auditor_rejects_corrupt_authored_source[event-mapping]
test_independent_auditor_rejects_corrupt_authored_source[snapshot-prefix]
test_rewritten_control_cannot_be_rebound_into_export[cleanup.json]
```

## Explicit active exclusions and coverage limits

- Numeric `test_protocol_canonical_exact_base_and_population_provenance`, `test_limits_exact_ceiling_and_single_byte_over`, `test_import_has_no_model_or_native_side_effect`, and `test_untrusted_npy_dimensions_refuse_before_allocation_under_small_process_limit` stay active.
- Raw normal-terminal exact/malformed validator tests, raw limits and invalid/expired deadline tests stay active. Exact `test_rejects_wrong_run_case_condition_or_source_identity[run_id]` and `test_rejects_mutated_spliced_or_aliased_raw_tree[symlink]` reject before source identity and stay active.
- Qualification `test_unknown_cpu_or_non_drained_owner_prevents_raw_audit`, `test_failed_owner_outcome_blocks_audit_even_with_raw_report`, `test_v4_handle_teardown_failure_cannot_return_preserved` stay active. Mixed `[failed=True]`, early profile `[late=False]`, corrupt report `[report]`, and early rewritten-control `[owner-supervisor.json]`/`[job.json]` variants stay active. Their sibling late/success cases are listed using exact pytest suffixes above (`[True]`/`[False]` are pytest default IDs, not argument names).
- Historical profile rejection, historical JSON-byte preservation, empty accepted execution/qualification trust, accepted-profile refresh refusal, and authored current semantic copies stay active.
- Several raw/qualification negatives currently accept a broad ValueError or merely require status=stopped. A guard refusal can make those appear green before the intended corrupt evidence or later callback is examined. The proposed skip honestly removes that misleading historical execution claim where source identity is a prerequisite; it does **not** replace lost semantic coverage. Pure early-gate cases must remain active. Independent review should inspect this reachability classification, especially every mixed qualification branch, before installing the list.
- No new codec corruption/roundtrip failures were demonstrated here. The isolated test establishes that the legacy failure exists without new-codec import; it does not prove every possible shared-state interaction absent.
- No complete focused post-policy suite, full repository suite, new policy tests or collection validation was run in this diagnosis. No statement that a future full suite will be green is justified. The explicit transitive inventory addresses known missing-registry pin dependencies; unrelated failures and additional dynamic dependencies remain possible.
- New-codec 67 passed is supplied evidence. Combined 111 failed/235 passed/2 skipped/13 errors is supplied evidence. Fresh measured evidence is only the one isolated old numeric failure plus source/history checks. A later conditional skip is a **skip**, never a pass or qualification.

## Acceptance checks after independent review and authorized implementation

Run focused shared-helper tests and collection validation for the exact added nodes; verify all JSON byte pins against HEAD ancestry, uniqueness including exact-vs-base conflicts, unchanged production guards/JSON bytes, all excluded early gates still collected without this skip, and unpatched historical drift refusal. Then rerun the originally authorized Task 4 legacy/new focused set in a fresh exclusive evidence directory and distinguish passed/skipped/error totals. Do not silently broaden this authored allowance into full repository execution or actual runtime/model work. A full-suite run requires its own explicit scope decision. If pin-only errors remain, trace the missing dependency rather than adding a blanket module entry or weakening the runtime check.

Memory quick pass used only the general repository custody/claim-boundary guidance at MEMORY.md:416–418; current facts above were verified from present source and evidence. Quota/account billing remains unknown; no paid or research action occurred.
