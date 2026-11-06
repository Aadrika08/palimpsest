# Independent historical-pin policy review

**FAIL — proposed registry scope needs five corrections before implementation.**

Review is source-only. No pytest/collection, repository import, model/native/runtime, raw/SNP/protected payload read, production edit, dependency operation or HEAD change was performed. Only this report is written. `.codegraph/` is absent in the reviewed worktree. Billing/quota is unknown. The diagnosis artifacts and supplied execution results remain historical evidence, not executions by this reviewer.

## Mechanism judgment

The four-file mechanism is appropriate under the accepted ADR: add a distinct case-publication group; load the real base `behavior_sources` plus condition/publication `source_pins`; reject conflicting path pins; preserve all existing groups and ownership; choose exact node first then function fallback; condition a skip on actual drift. Reject duplicate IDs and base-plus-exact registrations, including within one group. Never catch a production refusal to skip, patch a production guard, forge accepted qualification, rewrite frozen JSON or blanket-skip a module.

The supplied 93-pin metadata says every pin matches fixed main `5547efc6dd7210e7a35aa02536140c351c7104b1` and records Engine plus memory_decision drift. I read the metadata and the refusing call chain; I did not rehash/history-verify its 93 files. The old helper loads retained-condition pins, whereas compact's active profile is case-publication. They are different contracts. The new helper is itself pinned: changing it introduces expected historical drift until a separately reviewed prospective epoch; never repin merely to make this suite green.

The isolated log establishes one old numeric failure before its conversion assertion, without new-terminal-codec import: 1 failed / 0.21 s, exit 1. The supplied combined record has 111 failures + 13 errors = 124 recorded failing/error nodes, 235 passes and 2 skips. Those 124 nodes are distinct from the 101 proposed function/exact-parameter entries and from source-derived transitive candidates. Neither static reachability nor a broad ValueError assertion proves a newly measured failure.

## Required scope corrections

1. Remove `source_qualification_v2::test_duplicate_output_is_not_a_new_attempt`. A failed first audit still creates an occupied output. The second `_execute` refuses it and the before/after inventory assertion remains meaningful. Both launches are recorded before the audit accounting failure; no preservation-success assertion exists.
2. Remove `source_qualification_v2::test_closure_final_recheck_prevents_export`. `harness(final_check=True)` fails at check number four. `_execute_core` checks once initially, before owner launch, after owner launch, then before audit launch. This is an early closure refusal, not a post-audit dependency.
3. Remove `source_qualification_v2::test_parent_keeps_venv_alias_and_independent_audit_command`. Commands, `-B`, environment and `calls == ['owner','audit']` are meaningful on a refused audit. `launch` appends the audit record before checking its unsuccessful accounting.
4. Remove `source_qualification_v2::test_parent_records_and_passes_inherited_cpu_clamp`. Requests, job records and launch-control bytes are produced before auditor acceptance. Preserve this launch-accounting check.
5. Replace the function-wide raw `test_rejects_size_caps_before_hashing_oversized_file` entry with `[recording]`, `[events]`, `[report]` only. Keep `[snapshot]` active. In source mode `_with_snapshot` enters `compact.bound_payload` before `_audit_raw_run`/`_audit_candidate`; the changed snapshot has the old descriptor size and fails at `bound_payload`'s stat/size check before canonical identity (`raw_audit:1022-1037`, `compact:491-494`). Its invariant remains exercised even though it currently reaches descriptor-size mismatch rather than a later raw inventory cap.

These corrections yield 99 registry strings (four removals and one function replaced by three exact nodes), not 99 collected tests. No further subtraction is supported by this source review. Static eligibility does not authorize implementation or execution.

## Complete classification of the 101 proposed entries

Names below are verbatim registry entries. Line numbers refer to the test function in each named file. `SKIP` means eligible only while this group's real pins drift, not an instruction to skip unconditionally. `ACTIVE` means remove the proposed entry. `REFINE` is the exact-parameter change above. Function entries include all parameter branches unless explicitly refined.

### tests/test_memory_family_numeric_preservation_v2.py

13 functions unconditionally construct local fixture -> declared_receipt -> canonical identity (58,74-86); five consume module public_raw -> real auditor (281-310). No authored-current-profile opt-in. All 18 proposed mappings are justified by this prerequisite; pure canonical/limit/import/NPY-parser tests stay active.

| Entry | Line | Classification |
| --- | ---: | --- |
| `test_exact_roundtrip_and_partial_partition` | 133 | SKIP |
| `test_converter_refuses_numeric_domain_without_coercion` | 181 | SKIP |
| `test_population_other_domains_are_ineligible` | 198 | SKIP |
| `test_envelope_exact_schema_and_bijection` | 209 | SKIP |
| `test_rehashed_companion_archive_corruption` | 243 | SKIP |
| `test_unchanged_public_raw_receipt_and_all_row_proof` | 314 | SKIP |
| `test_rehashed_numeric_bits_fail_at_exact_field_tick` | 327 | SKIP |
| `test_population_row_and_column_permutation_fail_raw_proof` | 345 | SKIP |
| `test_old_base_proof_is_not_bypassed` | 356 | SKIP |
| `test_actual_serialized_byte_accounting_and_external_combined_bound` | 366 | SKIP |
| `test_each_partial_companion_matches_independent_zip_npy_size_model` | 416 | SKIP |
| `test_complete_operation_maximum_has_every_row_and_actual_serialized_ledger` | 441 | SKIP |
| `test_nested_exact_schema_fields` | 460 | SKIP |
| `test_sign_of_zero_is_preserved_and_not_equated_in_raw_proof` | 480 | SKIP |
| `test_valid_v1_metadata_can_exhaust_combined_v2_budget_without_padding_conversion_json` | 495 | SKIP |
| `test_rehashed_receipt_counts_must_match_the_exact_base` | 559 | SKIP |
| `test_numpy_timing_scalars_are_exact_but_python_values_are_not_coerced` | 572 | SKIP |
| `test_raw_audit_declaration_has_its_original_canonical_byte_bound` | 587 | SKIP |

### tests/test_memory_family_source_seal_v2.py

All 30 functions call local fixture before the tested mutation/early gate. Fixture (28-44) calls imported producer.fixture (39-76), which requires a successful unchanged raw-auditor subprocess. Importing that function does not register producer module's autouse authored_current_profile in this module. Even the three registration/control preflight functions at 651/676/690 need that baseline receipt, so their whole-function mappings are justified under the no-body-edits scope. Pure import remains active.

| Entry | Line | Classification |
| --- | ---: | --- |
| `test_public_numeric_source_roundtrip_retains_originals` | 47 | SKIP |
| `test_source_fixture_is_accepted_by_unchanged_public_raw_audit` | 83 | SKIP |
| `test_change_and_restore_during_final_rename_is_refused` | 118 | SKIP |
| `test_invalid_input_fails_before_candidate_writes` | 141 | SKIP |
| `test_occupied_or_aliased_namespace_is_never_reused` | 161 | SKIP |
| `test_publication_failures_preserve_raw_and_partials` | 184 | SKIP |
| `test_rehashed_numeric_candidate_must_match_raw` | 234 | SKIP |
| `test_actual_disk_reread_detects_changed_candidate` | 250 | SKIP |
| `test_raw_backed_reader_retains_input_witnesses_until_return` | 267 | SKIP |
| `test_reader_rejects_changed_disk_or_unknown_members` | 287 | SKIP |
| `test_deadline_never_returns_accepted_result` | 300 | SKIP |
| `test_late_descriptor_close_failure_is_quarantined` | 320 | SKIP |
| `test_quarantine_failure_is_indeterminate_and_retains_evidence` | 337 | SKIP |
| `test_ledger_accounts_unique_physical_paths_and_all_reserved_metadata` | 353 | SKIP |
| `test_valid_raw_that_cannot_fit_combined_metadata_is_retained_failure` | 389 | SKIP |
| `test_rehashed_published_numeric_bits_reach_raw_comparison` | 407 | SKIP |
| `test_candidate_file_witness_survives_final_rename` | 432 | SKIP |
| `test_additional_controls_are_held_charged_and_bound_in_conversion` | 457 | SKIP |
| `test_auxiliary_control_can_make_combined_overhead_ineligible` | 470 | SKIP |
| `test_auxiliary_control_change_and_restore_at_rename_is_refused` | 481 | SKIP |
| `test_duplicate_registered_physical_role_counts_once_but_real_copy_counts_twice` | 498 | SKIP |
| `test_invalid_additional_controls_fail_before_writes` | 515 | SKIP |
| `test_evidence_root_replacement_and_restore_is_refused` | 549 | SKIP |
| `test_unbounded_disk_inventory_is_refused_before_opening_payloads` | 564 | SKIP |
| `test_indeterminate_writer_marker_never_proves_process_success` | 578 | SKIP |
| `test_rehashed_base_snapshot_metadata_must_match_held_original_snp` | 611 | SKIP |
| `test_registration_preflight_rejects_nondevelopment_before_case_construction` | 651 | SKIP |
| `test_registration_descriptor_root_is_refused_before_any_payload_open` | 676 | SKIP |
| `test_control_descriptor_roots_are_refused_before_control_payload_open` | 690 | SKIP |
| `test_review_fix1_prepared_marker_change_restore_during_real_rename_is_refused` | 717 | SKIP |

### tests/test_memory_case_publication_profile_v1.py

All three compare historical source identity or generator descriptors against current source. Other historical-byte/contract/closure/empty-trust and refresh-refusal assertions remain active. The initializer test also contains independent path assertions, but its first identity call prevents reaching them; this proposal loses that coverage and must disclose it rather than claim replacement.

| Entry | Line | Classification |
| --- | ---: | --- |
| `test_prospective_profiles_exist_and_bind_exact_current_source` | 37 | SKIP |
| `test_profile_generator_checks_without_rewriting_registered_bytes` | 106 | SKIP |
| `test_initializer_source_binding_does_not_relax_evidence_paths` | 114 | SKIP |

### tests/test_memory_family_source_runtime_v2.py

Two authored-owner tests reach the unchanged public auditor: first requires a valid receipt; second requires the specific prefix-diff refusal after source identity. Other owner/early-admission tests remain active. No authored profile opt-in is imported.

| Entry | Line | Classification |
| --- | ---: | --- |
| `test_acquired_source_emits_exact_v4_manifest_and_report` | 224 | SKIP |
| `test_invalid_prefix_is_rejected_by_unchanged_raw_audit` | 370 | SKIP |

### tests/test_memory_family_raw_audit_v4.py

_audit_candidate (725-752) checks canonical identity before inventory/terminal/row proofs. Specified wrong-field values are syntactically valid, including swapped, so all five listed fields reach it. Raw run_id and symlink siblings reject earlier and remain active. Snapshot prebinding is the additional exception below. Existing seven old-group entries remain untouched.

| Entry | Line | Classification |
| --- | ---: | --- |
| `test_rejects_normal_episode_terminal_spliced_before_natural_failure` | 504 | SKIP |
| `test_rejects_inexact_sensor_only_natural_failure` | 611 | SKIP |
| `test_rejects_external_hardlink_to_any_raw_file` | 726 | SKIP |
| `test_rejects_undeclared_policy_sensor_even_when_hash_is_rebound` | 737 | SKIP |
| `test_rejects_invalid_or_unbound_all_tick_values` | 765 | SKIP |
| `test_rejects_terminal_and_condition_oracle_mismatch` | 794 | SKIP |
| `test_rejects_source_restore_lineage_or_snapshot_mutation` | 822 | SKIP |
| `test_rejects_size_caps_before_hashing_oversized_file` | 897 | REFINE |
| `test_rejects_wrong_run_case_condition_or_source_identity[case_id]` | 674 | SKIP |
| `test_rejects_wrong_run_case_condition_or_source_identity[condition]` | 674 | SKIP |
| `test_rejects_wrong_run_case_condition_or_source_identity[source_run_id]` | 674 | SKIP |
| `test_rejects_wrong_run_case_condition_or_source_identity[source_snapshot_sha256]` | 674 | SKIP |
| `test_rejects_wrong_run_case_condition_or_source_identity[source_identity_sha256]` | 674 | SKIP |
| `test_rejects_mutated_spliced_or_aliased_raw_tree[chunk-byte]` | 695 | SKIP |
| `test_rejects_mutated_spliced_or_aliased_raw_tree[foreign-event]` | 695 | SKIP |
| `test_rejects_mutated_spliced_or_aliased_raw_tree[eyes-event]` | 695 | SKIP |
| `test_rejects_mutated_spliced_or_aliased_raw_tree[hardlink-alias]` | 695 | SKIP |
| `test_rejects_mutated_spliced_or_aliased_raw_tree[extra-file]` | 695 | SKIP |

### tests/test_memory_family_source_qualification_v2.py

Harness (49-192) uses authored owner but executes the unchanged independent auditor without an authored-current-profile opt-in. Later cleanup/export/publication checks need auditor success; broadly asserting stopped does not exercise those later mechanisms when the guard refuses. The four launch/early-closure exceptions stay active. All listed late/publication parameter variants remain eligible; details follow the table.

| Entry | Line | Classification |
| --- | ---: | --- |
| `test_duplicate_output_is_not_a_new_attempt` | 258 | ACTIVE |
| `test_closure_final_recheck_prevents_export` | 352 | ACTIVE |
| `test_terminal_export_control_identity_corruption_prevents_seal` | 358 | SKIP |
| `test_parent_keeps_venv_alias_and_independent_audit_command` | 373 | ACTIVE |
| `test_postseal_final_read_failure_quarantines_without_deletion` | 382 | SKIP |
| `test_held_input_exit_failure_is_quarantined_before_terminal` | 538 | SKIP |
| `test_controls_remain_bound_after_creation_until_export` | 593 | SKIP |
| `test_original_freeze_teardown_drift_is_caught_under_lease` | 613 | SKIP |
| `test_parent_calls_real_public_numeric_writer_and_rereader` | 639 | SKIP |
| `test_parent_censuses_ancillary_control_prefix_and_zero_leases` | 699 | SKIP |
| `test_parent_complete_census_refuses_unaccounted_or_oversize_outputs` | 727 | SKIP |
| `test_control_census_stays_held_across_real_numeric_publication` | 753 | SKIP |
| `test_terminal_failure_quarantines_numeric_candidate` | 777 | SKIP |
| `test_indeterminate_public_writer_is_stopped_and_never_resumed_by_reader` | 803 | SKIP |
| `test_writer_lease_teardown_error_is_not_a_successful_parent` | 820 | SKIP |
| `test_fresh_controlled_home_bootstraps_before_parent_lease` | 877 | SKIP |
| `test_parent_records_and_passes_inherited_cpu_clamp` | 892 | ACTIVE |
| `test_v4_parent_and_child_hold_independently_same_deadline` | 1011 | SKIP |
| `test_v4_full_combined_metadata_sum_includes_freeze_job_logs_tail` | 1064 | SKIP |
| `test_v4_new_copy_and_stage_created_manifest_remain_charged` | 1118 | SKIP |
| `test_v4_one_byte_over_retains_failure` | 1135 | SKIP |
| `test_v4_consistent_json_cannot_qualify_accounting_backend` | 1150 | SKIP |
| `test_v4_added_requirements_copies_count_in_combined_metadata` | 1159 | SKIP |
| `test_v4_parent_only_late_close_retains_and_quarantines_provisional_marker` | 1239 | SKIP |
| `test_raw_and_snapshot_remain_after_pass_or_failure[False]` | 289 | SKIP |
| `test_actual_new_profile_file_bytes_are_checked_and_held[True]` | 848 | SKIP |
| `test_independent_auditor_rejects_corrupt_authored_source[raw-hash]` | 306 | SKIP |
| `test_independent_auditor_rejects_corrupt_authored_source[event-mapping]` | 306 | SKIP |
| `test_independent_auditor_rejects_corrupt_authored_source[snapshot-prefix]` | 306 | SKIP |
| `test_rewritten_control_cannot_be_rebound_into_export[cleanup.json]` | 519 | SKIP |

## Qualification branch reachability and preserved siblings

- `raw_and_snapshot_remain_after_pass_or_failure[False]` requires preserved status and marker; `[True]` only tests failed-owner retention and stays active. Owner failure prevents audit (parent 996-1002).
- `actual_new_profile_file_bytes_are_checked_and_held[True]` mutates profile after real numeric reread; `[False]` rejects the changed profile before owner and stays active (test 848-874).
- Corrupt-source `[raw-hash]`, `[event-mapping]`, `[snapshot-prefix]` require independent semantic audit; `[report]` breaks equality between owner outcome and worker report before audit (parent 996-1002), so stays active. Snapshot-prefix case deliberately rebinds the snapshot/report digest, allowing the parent descriptor check before the later intended prefix rejection.
- Rewritten-control `[cleanup.json]` occurs after successful audit (parent 1042); `[owner-supervisor.json]` and `[job.json]` violate held/creation-pinned controls before audit and stay active (test 518-535, parent 854-864,979-990).
- All seven complete-census variants are late dependencies: their corruption is injected after owner creation, but parent control census/zero-lease/registered-output checks occur after successful audit (1058-1063). `StorageBudget.usage` counts hardlinks/bytes without the later zero-byte-lease rule; these are not equivalent early checks. Keep their function entry.
- All three stage-created-copy variants at 1117-1132 need later combined-metadata accounting. The rejected 950000-byte variant is below the one-file control cap and total allocation; its intended rejection remains after audit, so retain the whole function entry.
- All other proposed qualification entries require a real seal/read/marker/quarantine, an after-audit cleanup mutation or successful preservation status. A teardown callback can run after early failure, but tests asserting the numeric marker/quarantine still need publication and remain eligible.
- Keep unknown-CPU/non-drained-owner, failed-owner-outcome, child runtime-handle teardown, profile-metadata rejection, pure ledger/layout/admission and all originally excluded early cases active. Preserve source-profile refusal, empty accepted execution/qualification sets, authored-current-profile modules and current-semantic copies. No new mapping to those modules is justified.

## Meaningful verification required after authorized implementation

1. Source-only diff review: only helper, conftest, helper tests and ADR may change. Read back all three frozen profile bytes and production guard source unchanged against the agreed baseline; verify each real pin at an ancestor, preserving the supplied 93-pin evidence. Reject conflicting union pins; demonstrate the loader uses the actual case-publication documents and preserves old group ownership.
2. Helper tests on temporary authored source bytes: all pins matching causes no skip; one drift/missing file causes explicit historical reason; equal duplicate pin accepted, conflict rejected; exact lookup and base fallback behave correctly; unrelated node never skips; duplicate ID and same-function base/exact ambiguity fail. Isolate/clear cached drift when varying authored cases so cache order cannot fake coverage.
3. Focused collection only for registry target modules, plus the existing relevant current-semantics/profile modules: require every exact node to exist exactly once, every base entry to match collected descendants, and all exclusion siblings plus the five corrections to have no new historical marker. Source existence alone cannot validate parameter order/escaping/default IDs. Include `[snapshot]`, all four removed qualification functions and every mixed sibling listed above in this audit. Collection imports modules, so this is a future authorized check, not performed here.
4. Run the shared helper tests and explicit still-active early cases in an isolated evidence directory; keep production refusal tests unpatched. Then run the originally authorized Task 4 legacy/new focused set with passed/skipped/errors separately reported. Do not infer current semantic coverage from a historical skip or use a passing broad-negative result as proof a late corruption callback was reached.
5. The mapping extends beyond the original four-file combined run. Any authorized execution of source-seal/runtime/qualification tests is a separate bounded authored-test verification decision; no full suite, native owner, real model, retained/raw/SNP dataset or paid research work follows automatically from this review. If only collection is authorized for those modules, report their execution as unverified.

## Boundaries and disposition

The supplied static-transitive inventory is a candidate locator, not measured failure evidence. The 101 classifications above were inspected through source/fixture/control-flow branches; no claims of passing execution or exact collected IDs are made. The policy proposal is reviewable once the five corrections are made, but the combined test-policy gate stays blocked until authorized implementation and meaningful verification. This report grants no production, code-acceptance, qualification, runtime or research approval.

Memory was used only for repository custody and test-boundary guidance (MEMORY.md:416-418); present classification uses current source and supplied metadata, not unverified remembered state.
