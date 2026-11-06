# Historical test-pin policy implementation — reviewed 100-entry amendment

**Implemented and scoped-committed; independent code review and Task4 acceptance remain open.** Commit `e620b345233bdb873d0ca48d4a2639fde1206e32`, parent `65b6789cff2f08f1e2b33875a41432145b05c1e2`, branch `research/memory-vnext-spec-v1`. This is authored software/test policy, not actual runtime, research, qualification, adoption, GO or raw-deletion acceptance.

## Delivered scope

Exactly five owned files are committed: `tests/frozen_pins.py`, `tests/conftest.py`, `tests/test_frozen_pins.py`, `tests/test_memory_case_publication_profile_v1.py` and `docs/plans/frozen-source-pins-after-integration.md`. Root's separate `docs/plans/memory-terminal-vnext-implementation.md` remains unstaged and excluded. `commit-readback.json` and `post-commit-readback.json` verify exact file ownership and committed bytes. No production reader, generator, frozen JSON, schema, trust constants, legacy guard, Task4 profile or unrelated test body changed.

The distinct `memory-family-compact-v4-case-publication-v1` group loads the real active compact `behavior_sources` plus condition/publication `source_pins`, a union of **93 unique named paths**. Equal path/digest duplicates are accepted; conflicting duplicates fail. All93 frozen byte pins remain verified at main ancestor `5547efc6dd7210e7a35aa02536140c351c7104b1`; no digest is copied into helper code or repinned to current bytes. Existing129 registrations and original99 reviewed strings keep their owners. The reviewed one-node amendment produces **100 strings:81 functions,19 exact parameter nodes**, not100 collected tests.

Exact-node lookup precedes function fallback. Duplicate IDs and function-plus-exact ambiguity fail even within one group. A historical skip requires actual selected-group drift; there is no blanket file skip, xfail, caught-production-refusal skip or production-reader mock. The helper and conftest self-pin drift remains historical. Appending the counterpart also causes expected drift of the pinned profile-test file; no pin refresh is authorized.

## Original mixed test and active counterpart

The entire original profile-test module text is preserved as a prefix of the amended file, matching HEAD65b before amendment. All original AST nodes, the mixed function body, generator import, live closure assertion and decorators are unchanged. Its single existing node was added to the historical group. It now skips on real drift; **its live-current-closure assertion did not pass**.

The appended `test_declared_profile_metadata_and_empty_real_trust_remain_active` has no decorators, registry owner, skip or xfail. It executed successfully in the fresh wave. Apart from its scope docstring, its body is AST-identical to the independent original body after removing only the generator import and live-closure assertion. It preserves all three canonical read calls, exact12-member required-root literal, exact5-member excluded set and six assertion sites: uniqueness, required subset, excluded paths across all three lists, sorted unique publication pins, empty execution trust and empty qualification trust. It establishes declared metadata/empty-trust coverage, **not completeness of the current import closure**. Proof: `profile-body-preservation.json`, source diff and fresh collection markers.

## Fresh amendment verification

Amendment evidence: `legacy-pin-policy-evidence/20261106T045532915674Z-amendment/` relative to this SDD directory. Each invocation retains fresh command/environment, full log, exit code and exclusive pytest basetemp. The prior99-entry evidence is separately retained at `legacy-pin-policy-evidence/20261106T044123346083Z/`; its report is `legacy-pin-policy-implementation-v1-retained.md`.

| Fresh wave | Measured result | Exit |
| --- | --- | --- |
| `amendment-count-red` | 1 failed: existing99 versus required100 before registry change | 1 |
| `amendment-mechanics-history-green` | **31 passed,0 skipped,0 failed,0 errors**,1.83s | 0 |
| `amendment-collection` | **1,233 collected,0 errors**,1.47s; all100-entry marker audit passed | 0 |
| `amendment-early-profile` | **54 passed,4 skipped,0 failed,0 errors**,20.20s | 0 |
| `amendment-source-guard-readback` | named frozen/guard/trust/source bytes unchanged; unpatched active-profile guard refuses `Behavior source differs: engine` | 0 |

Collection covers the same20 inspected authored modules. Every base entry has collected descendants; all19 exact parameter entries exist once. It observed **307 new-group descendants**, **716 related-module nodes without the new group**, all20 prior explicit early exclusion nodes, and the new counterpart exactly once unmarked. The original mixed function appears once with the new historical owner/skip under real drift. Previous99 entries and all old group ownership are unchanged. `collection-audit.json` retains every node, owner and reason. No fixture executed during collection.

The fresh execution wave selected all seven profile-test functions and every prior explicit early case. The counterpart passed, while the unchanged original mixed function and the three existing source-identity-dependent profile functions are the **four historical skips**. The four review-removed qualification checks, six unknown-CPU/non-drained owner variants, failed-owner/report/profile/control siblings, raw snapshot/run-id/symlink siblings, pure numeric/raw gates and unpatched historical-refusal test executed successfully. Exact selectors are in `early-case-selectors.json`. Later mapped source-seal/runtime/qualification fixtures remain collection-only; no broader late-case execution occurred.

## Reused prior original-four-file execution

**This is prior timed execution, not a post-amendment rerun:** `236 passed,126 skipped,0 failed,0 errors in93.90s`, exit0, retained under the earlier evidence's `task4-original-four/`.

| File | Passed | Skipped | Failed | Errors |
| --- | ---: | ---: | ---: | ---: |
| `test_memory_family_terminal_numeric_vnext.py` | 68 | 0 | 0 | 0 |
| `test_memory_family_numeric_preservation_v2.py` | 5 | 124 | 0 | 0 |
| `test_memory_family_compact_v4.py` | 40 | 2 | 0 | 0 |
| `test_memory_family_terminal_audit_vnext.py` | 123 | 0 | 0 | 0 |
| Total | 236 | 126 | 0 | 0 |

Reuse is authorized by the reviewed amendment and root's explicit marker-identity ruling. All four modules' source bytes and all362 exact node IDs, registered owners, skip polarity and xfail polarity match the prior collection. The amendment changes no helper function/conftest behavior beyond the one registry tuple string in a different module. `original-four-source-before.json`, `original-four-reuse-proof.json` and the labelled one-line `amendment-only-helper.patch` retain the proof. Full old/new reasons are retained in `original-four-reason-readback.json`: reason text changes because the newly appended profile-test source is itself a frozen pin. **Literal reason text is not claimed identical.**

The124 new-group and2 prior compact-group skips remain lost historical execution coverage, never passes or qualification. The active metadata counterpart preserves only its named independent assertions; it does not replace historical numeric/raw/live-closure semantic qualification.

## Retained failures and custody

No earlier failing evidence was overwritten or relabelled as passing:

- Initial mechanics RED:6 failed,2 passed,21 deselected. It caught missing exact-node marking, base/exact ambiguity acceptance and absent union/lookup APIs.
- Misnamed intermediate `mechanics-history-green`:7 failed,22 passed because an edit-script syntax error prevented any helper change; it remained RED. Corrected initial mechanics/history then measured31 passed.
- Initial collection:250 collected,17 collection errors followed by an audit internal assertion, exit3. Individual collection error details were obscured by that audit assertion. Correcting the evidence harness's cwd/sys.path behavior alone yielded the retained1,232-node passing audit; no dependency installation or registry expansion occurred for that correction.
- Initial early active wave: **1 failed,53 passed,0 skipped,0 errors**,21.23s. The unchanged mixed assertion `generator.local_python_closure(ROOT,required)<=set(paths)` found extra `src/palimpsest/memory_transition_vnext.py`. It was reported immediately before any scope/map change. Later assertions in that original invocation were **not reached**. The independently reviewed amendment preserves its full historical body and adds the active counterpart, rather than claiming the old closure assertion passed.
- Fresh amendment RED:1 failed because99 had not yet become100; fresh amended checks above then passed within their explicit scope.

## Sources, environment and limits

Before the original93-pin provenance wave, named paths were inspected. Inspection stopped at `model_manifests/flynn-full-vision.json`; root explicitly authorized only that named JSON configuration metadata. No referenced model/graph/array/checkpoint/native/catalog payload was dereferenced. The exact pin inventory and metadata allowance remain in prior evidence. No all-tracked-files hashing or protected retained raw/SNP read occurred. Authored temporary test files/containers are distinct from actual retained evidence.

Both original and fresh invocations replace the environment, equivalent to `env -i`, with exactly PATH=/usr/bin:/bin, PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=src:scripts:tests, LC_ALL=C.UTF-8, OMP_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1, MKL_NUM_THREADS=1, NUMEXPR_NUM_THREADS=1, MUJOCO_GL=egl and empty CUDA_VISIBLE_DEVICES. Interpreter: `/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B`. Detailed commands are retained per wave. Account quota is unknown. No whole-repository suite, actual model/native owner, runtime service, research, paid CI, dependency installation, cleanup, push or sub-agent was performed.

`baseline.json` and fresh `source-readback.json` verify the three frozen JSON profiles, production compact/raw/condition/replay/publication guards, qualification/execution trust roots, Engine and memory_decision unchanged. `generator-unchanged.json` separately verifies generator bytes against base HEAD. Current historical drift consists of Engine, memory_decision, conftest, frozen_pins and the profile-test file. Production's direct active-profile refusal is retained. `git diff --check`/staged check passed; post-commit bytes and five-file scope were read back. Only root's implementation plan remains unstaged.

Self-review found no scope or policy bypass. Fresh independent **code** review still follows; the earlier source-only proposal PASS is not implementation acceptance. Actual qualification/admission/research/GO/raw-deletion gates remain closed, and no Task4 acceptance is asserted. Memory was used only for general custody/claim guidance at MEMORY.md:416-418; all source/test facts here are current evidence.

## Exact installed100 entries

```text
tests/test_memory_case_publication_profile_v1.py::test_prospective_profiles_exist_and_bind_exact_current_source
tests/test_memory_case_publication_profile_v1.py::test_profile_generator_checks_without_rewriting_registered_bytes
tests/test_memory_case_publication_profile_v1.py::test_initializer_source_binding_does_not_relax_evidence_paths
tests/test_memory_case_publication_profile_v1.py::test_complete_declared_closure_excludes_output_cycles_and_real_trust
tests/test_memory_family_numeric_preservation_v2.py::test_exact_roundtrip_and_partial_partition
tests/test_memory_family_numeric_preservation_v2.py::test_converter_refuses_numeric_domain_without_coercion
tests/test_memory_family_numeric_preservation_v2.py::test_population_other_domains_are_ineligible
tests/test_memory_family_numeric_preservation_v2.py::test_envelope_exact_schema_and_bijection
tests/test_memory_family_numeric_preservation_v2.py::test_rehashed_companion_archive_corruption
tests/test_memory_family_numeric_preservation_v2.py::test_unchanged_public_raw_receipt_and_all_row_proof
tests/test_memory_family_numeric_preservation_v2.py::test_rehashed_numeric_bits_fail_at_exact_field_tick
tests/test_memory_family_numeric_preservation_v2.py::test_population_row_and_column_permutation_fail_raw_proof
tests/test_memory_family_numeric_preservation_v2.py::test_old_base_proof_is_not_bypassed
tests/test_memory_family_numeric_preservation_v2.py::test_actual_serialized_byte_accounting_and_external_combined_bound
tests/test_memory_family_numeric_preservation_v2.py::test_each_partial_companion_matches_independent_zip_npy_size_model
tests/test_memory_family_numeric_preservation_v2.py::test_complete_operation_maximum_has_every_row_and_actual_serialized_ledger
tests/test_memory_family_numeric_preservation_v2.py::test_nested_exact_schema_fields
tests/test_memory_family_numeric_preservation_v2.py::test_sign_of_zero_is_preserved_and_not_equated_in_raw_proof
tests/test_memory_family_numeric_preservation_v2.py::test_valid_v1_metadata_can_exhaust_combined_v2_budget_without_padding_conversion_json
tests/test_memory_family_numeric_preservation_v2.py::test_rehashed_receipt_counts_must_match_the_exact_base
tests/test_memory_family_numeric_preservation_v2.py::test_numpy_timing_scalars_are_exact_but_python_values_are_not_coerced
tests/test_memory_family_numeric_preservation_v2.py::test_raw_audit_declaration_has_its_original_canonical_byte_bound
tests/test_memory_family_raw_audit_v4.py::test_rejects_normal_episode_terminal_spliced_before_natural_failure
tests/test_memory_family_raw_audit_v4.py::test_rejects_inexact_sensor_only_natural_failure
tests/test_memory_family_raw_audit_v4.py::test_rejects_external_hardlink_to_any_raw_file
tests/test_memory_family_raw_audit_v4.py::test_rejects_undeclared_policy_sensor_even_when_hash_is_rebound
tests/test_memory_family_raw_audit_v4.py::test_rejects_invalid_or_unbound_all_tick_values
tests/test_memory_family_raw_audit_v4.py::test_rejects_terminal_and_condition_oracle_mismatch
tests/test_memory_family_raw_audit_v4.py::test_rejects_source_restore_lineage_or_snapshot_mutation
tests/test_memory_family_raw_audit_v4.py::test_rejects_size_caps_before_hashing_oversized_file[recording]
tests/test_memory_family_raw_audit_v4.py::test_rejects_size_caps_before_hashing_oversized_file[events]
tests/test_memory_family_raw_audit_v4.py::test_rejects_size_caps_before_hashing_oversized_file[report]
tests/test_memory_family_raw_audit_v4.py::test_rejects_wrong_run_case_condition_or_source_identity[case_id]
tests/test_memory_family_raw_audit_v4.py::test_rejects_wrong_run_case_condition_or_source_identity[condition]
tests/test_memory_family_raw_audit_v4.py::test_rejects_wrong_run_case_condition_or_source_identity[source_run_id]
tests/test_memory_family_raw_audit_v4.py::test_rejects_wrong_run_case_condition_or_source_identity[source_snapshot_sha256]
tests/test_memory_family_raw_audit_v4.py::test_rejects_wrong_run_case_condition_or_source_identity[source_identity_sha256]
tests/test_memory_family_raw_audit_v4.py::test_rejects_mutated_spliced_or_aliased_raw_tree[chunk-byte]
tests/test_memory_family_raw_audit_v4.py::test_rejects_mutated_spliced_or_aliased_raw_tree[foreign-event]
tests/test_memory_family_raw_audit_v4.py::test_rejects_mutated_spliced_or_aliased_raw_tree[eyes-event]
tests/test_memory_family_raw_audit_v4.py::test_rejects_mutated_spliced_or_aliased_raw_tree[hardlink-alias]
tests/test_memory_family_raw_audit_v4.py::test_rejects_mutated_spliced_or_aliased_raw_tree[extra-file]
tests/test_memory_family_source_qualification_v2.py::test_terminal_export_control_identity_corruption_prevents_seal
tests/test_memory_family_source_qualification_v2.py::test_postseal_final_read_failure_quarantines_without_deletion
tests/test_memory_family_source_qualification_v2.py::test_held_input_exit_failure_is_quarantined_before_terminal
tests/test_memory_family_source_qualification_v2.py::test_controls_remain_bound_after_creation_until_export
tests/test_memory_family_source_qualification_v2.py::test_original_freeze_teardown_drift_is_caught_under_lease
tests/test_memory_family_source_qualification_v2.py::test_parent_calls_real_public_numeric_writer_and_rereader
tests/test_memory_family_source_qualification_v2.py::test_parent_censuses_ancillary_control_prefix_and_zero_leases
tests/test_memory_family_source_qualification_v2.py::test_parent_complete_census_refuses_unaccounted_or_oversize_outputs
tests/test_memory_family_source_qualification_v2.py::test_control_census_stays_held_across_real_numeric_publication
tests/test_memory_family_source_qualification_v2.py::test_terminal_failure_quarantines_numeric_candidate
tests/test_memory_family_source_qualification_v2.py::test_indeterminate_public_writer_is_stopped_and_never_resumed_by_reader
tests/test_memory_family_source_qualification_v2.py::test_writer_lease_teardown_error_is_not_a_successful_parent
tests/test_memory_family_source_qualification_v2.py::test_fresh_controlled_home_bootstraps_before_parent_lease
tests/test_memory_family_source_qualification_v2.py::test_v4_parent_and_child_hold_independently_same_deadline
tests/test_memory_family_source_qualification_v2.py::test_v4_full_combined_metadata_sum_includes_freeze_job_logs_tail
tests/test_memory_family_source_qualification_v2.py::test_v4_new_copy_and_stage_created_manifest_remain_charged
tests/test_memory_family_source_qualification_v2.py::test_v4_one_byte_over_retains_failure
tests/test_memory_family_source_qualification_v2.py::test_v4_consistent_json_cannot_qualify_accounting_backend
tests/test_memory_family_source_qualification_v2.py::test_v4_added_requirements_copies_count_in_combined_metadata
tests/test_memory_family_source_qualification_v2.py::test_v4_parent_only_late_close_retains_and_quarantines_provisional_marker
tests/test_memory_family_source_qualification_v2.py::test_raw_and_snapshot_remain_after_pass_or_failure[False]
tests/test_memory_family_source_qualification_v2.py::test_actual_new_profile_file_bytes_are_checked_and_held[True]
tests/test_memory_family_source_qualification_v2.py::test_independent_auditor_rejects_corrupt_authored_source[raw-hash]
tests/test_memory_family_source_qualification_v2.py::test_independent_auditor_rejects_corrupt_authored_source[event-mapping]
tests/test_memory_family_source_qualification_v2.py::test_independent_auditor_rejects_corrupt_authored_source[snapshot-prefix]
tests/test_memory_family_source_qualification_v2.py::test_rewritten_control_cannot_be_rebound_into_export[cleanup.json]
tests/test_memory_family_source_runtime_v2.py::test_acquired_source_emits_exact_v4_manifest_and_report
tests/test_memory_family_source_runtime_v2.py::test_invalid_prefix_is_rejected_by_unchanged_raw_audit
tests/test_memory_family_source_seal_v2.py::test_public_numeric_source_roundtrip_retains_originals
tests/test_memory_family_source_seal_v2.py::test_source_fixture_is_accepted_by_unchanged_public_raw_audit
tests/test_memory_family_source_seal_v2.py::test_change_and_restore_during_final_rename_is_refused
tests/test_memory_family_source_seal_v2.py::test_invalid_input_fails_before_candidate_writes
tests/test_memory_family_source_seal_v2.py::test_occupied_or_aliased_namespace_is_never_reused
tests/test_memory_family_source_seal_v2.py::test_publication_failures_preserve_raw_and_partials
tests/test_memory_family_source_seal_v2.py::test_rehashed_numeric_candidate_must_match_raw
tests/test_memory_family_source_seal_v2.py::test_actual_disk_reread_detects_changed_candidate
tests/test_memory_family_source_seal_v2.py::test_raw_backed_reader_retains_input_witnesses_until_return
tests/test_memory_family_source_seal_v2.py::test_reader_rejects_changed_disk_or_unknown_members
tests/test_memory_family_source_seal_v2.py::test_deadline_never_returns_accepted_result
tests/test_memory_family_source_seal_v2.py::test_late_descriptor_close_failure_is_quarantined
tests/test_memory_family_source_seal_v2.py::test_quarantine_failure_is_indeterminate_and_retains_evidence
tests/test_memory_family_source_seal_v2.py::test_ledger_accounts_unique_physical_paths_and_all_reserved_metadata
tests/test_memory_family_source_seal_v2.py::test_valid_raw_that_cannot_fit_combined_metadata_is_retained_failure
tests/test_memory_family_source_seal_v2.py::test_rehashed_published_numeric_bits_reach_raw_comparison
tests/test_memory_family_source_seal_v2.py::test_candidate_file_witness_survives_final_rename
tests/test_memory_family_source_seal_v2.py::test_additional_controls_are_held_charged_and_bound_in_conversion
tests/test_memory_family_source_seal_v2.py::test_auxiliary_control_can_make_combined_overhead_ineligible
tests/test_memory_family_source_seal_v2.py::test_auxiliary_control_change_and_restore_at_rename_is_refused
tests/test_memory_family_source_seal_v2.py::test_duplicate_registered_physical_role_counts_once_but_real_copy_counts_twice
tests/test_memory_family_source_seal_v2.py::test_invalid_additional_controls_fail_before_writes
tests/test_memory_family_source_seal_v2.py::test_evidence_root_replacement_and_restore_is_refused
tests/test_memory_family_source_seal_v2.py::test_unbounded_disk_inventory_is_refused_before_opening_payloads
tests/test_memory_family_source_seal_v2.py::test_indeterminate_writer_marker_never_proves_process_success
tests/test_memory_family_source_seal_v2.py::test_rehashed_base_snapshot_metadata_must_match_held_original_snp
tests/test_memory_family_source_seal_v2.py::test_registration_preflight_rejects_nondevelopment_before_case_construction
tests/test_memory_family_source_seal_v2.py::test_registration_descriptor_root_is_refused_before_any_payload_open
tests/test_memory_family_source_seal_v2.py::test_control_descriptor_roots_are_refused_before_control_payload_open
tests/test_memory_family_source_seal_v2.py::test_review_fix1_prepared_marker_change_restore_during_real_rename_is_refused
```
