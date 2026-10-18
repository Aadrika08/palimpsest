"""The one shared test policy for pins frozen before main's integration (PR #179, 8626ecb).

See docs/plans/frozen-source-pins-after-integration.md. A finished protocol froze the
exact bytes of some repository files, or an absolute repository location. Integration
changed main's working tree, so a test that runs such a protocol against the CURRENT
tree now meets the production refusal (for example "Behavior source differs: engine").

The policy:

- Production refusal logic is never changed or bypassed.
- Every affected test is listed below by protocol. ``tests/conftest.py`` skips it with
  an explicit historical reason, but only while one of that protocol's pins actually
  differs in this checkout.
- ``tests/test_frozen_pins.py`` checks every byte pin against the file at a commit in
  main's history instead, so the pins stay proven to name real historical bytes.
- Resuming a line on main means re-pinning through a new prospective amendment, after
  which its tests run against the current tree again.
"""
from __future__ import annotations

import functools
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'docs/plans/frozen-source-pins-after-integration.md'


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(path):
    return json.loads((ROOT / path).read_bytes())


def git(*args, cwd=ROOT):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, timeout=120).stdout


def show(commit, path):
    """File bytes at commit, or None if absent there."""
    result = subprocess.run(['git', 'show', f'{commit}:{path}'], cwd=ROOT, capture_output=True, timeout=120)
    return result.stdout if result.returncode == 0 else None


@functools.lru_cache(maxsize=None)
def commit_holding(path, digest):
    """The newest commit in HEAD's history whose file at path has this SHA-256, or None."""
    for commit in git('rev-list', 'HEAD', '--', path).decode().split():
        raw = show(commit, path)
        if raw is not None and sha256(raw) == digest:
            return commit
    return None


def files_at(commit, directory, suffix=''):
    """Sorted file paths under directory at commit."""
    names = git('ls-tree', '-r', '--name-only', commit, '--', directory).decode().split('\n')
    return sorted(name for name in names if name and name.endswith(suffix) and '/' not in name[len(directory) + 1:])


def _memory_v4_pins():
    rows = _json('docs/plans/memory-family-compact-evidence-v4-directory-census-v1-protocol.json')['behavior_sources']
    return {row['path']: row['sha256'] for row in rows}


def _puck_learning_pins():
    spec = _json('docs/plans/m6-puck-learning-v2.json')
    return {spec['task_protocol']['path']: spec['task_protocol']['sha256'],
            'src/palimpsest/puck_profile.py': spec['teacher_source_sha256']}


def _puck_mechanics_pins():
    return {'src/palimpsest/puck_profile.py': _json('docs/plans/m6-puck-mechanics-v5.json')['puck_module_sha256']}


def _navigation_v2_pins():
    return dict(_json('docs/plans/m7-navigation-v2-checkpoint-support-v1.json')['reader_sources'])


def _navigation_v3_pins():
    return dict(_json('docs/plans/m7-navigation-v3-matched-budget-protocol.json')
                ['behavior_source_admission']['existing_hashes'])


def _navigation_v3_root():
    output = _json('docs/plans/m7-navigation-v3-matched-budget-execution-v2.json')['output']
    return output[:output.index('/runs/')]


def _full_cell_root():
    return _json('docs/plans/memory-full-cell-qualification-v4-execution.json')['repo_root']


# name -> (byte pins loader or None, frozen repository root loader or None, affected tests)
PROTOCOLS = {
    'memory-family-compact-v4': (_memory_v4_pins, None, (
        'tests/test_memory_directory_census_protocol_v1.py::test_active_profile_preserves_original_and_all_scientific_fields',
        'tests/test_memory_family_compact_v4.py::test_protocol_binds_exact_present_sources_including_source_producer',
        'tests/test_memory_family_condition_close_v4.py::test_caller_descriptor_mutation_cannot_rebind_validated_registration',
        'tests/test_memory_family_condition_close_v4.py::test_default_missing_qualification_refuses_before_source_raw_or_output',
        'tests/test_memory_family_condition_close_v4.py::test_mutation_during_internal_replay_cannot_publish',
        'tests/test_memory_family_condition_close_v4.py::test_named_output_directory_replacement_is_quarantined',
        'tests/test_memory_family_condition_close_v4.py::test_postcommit_anchor_close_failure_is_quarantined',
        'tests/test_memory_family_condition_close_v4.py::test_postcommit_context_validation_retains_marker_and_quarantines',
        'tests/test_memory_family_condition_close_v4.py::test_publication_faults_never_admit_or_delete_raw',
        'tests/test_memory_family_condition_close_v4.py::test_real_raw_conversion_pair_seals_with_authored_cell_seams',
        'tests/test_memory_family_condition_close_v4.py::test_rejects_cross_bound_registration_and_retains_raw',
        'tests/test_memory_family_condition_close_v4.py::test_replay_failure_or_wrong_identity_quarantines',
        'tests/test_memory_family_condition_close_v4.py::test_replay_primary_survives_composite_held_output_teardown_failure',
        'tests/test_memory_family_oracle_admission_v4.py::test_admission_deadline_includes_final_descriptor_reread',
        'tests/test_memory_family_oracle_admission_v4.py::test_admission_keeps_all_input_bindings_until_return',
        'tests/test_memory_family_oracle_admission_v4.py::test_admits_all_nine_exact_condition_identity_mappings_read_only',
        'tests/test_memory_family_oracle_admission_v4.py::test_compact_reader_never_accepts_a_failed_source_and_requires_the_receipt',
        'tests/test_memory_family_oracle_admission_v4.py::test_failed_condition_requires_and_accepts_only_exact_natural_failure_receipt',
        'tests/test_memory_family_oracle_admission_v4.py::test_final_snapshot_reread_rechecks_ancestor_edges',
        'tests/test_memory_family_oracle_admission_v4.py::test_oracle_fixture_reuses_donor_source_across_zip_time_boundary',
        'tests/test_memory_family_oracle_admission_v4.py::test_oracle_requires_prior_own_receipt_and_non_oracle_rejects_one',
        'tests/test_memory_family_oracle_admission_v4.py::test_prior_own_nested_values_bind_current_source_and_own_mapping',
        'tests/test_memory_family_oracle_admission_v4.py::test_raw_receipt_integer_fields_reject_numeric_aliases',
        'tests/test_memory_family_oracle_admission_v4.py::test_receipt_contract_rejects_rebound_nested_numeric_aliases',
        'tests/test_memory_family_oracle_admission_v4.py::test_rejects_condition_snapshot_bound_to_another_source_run',
        'tests/test_memory_family_oracle_admission_v4.py::test_rejects_prior_own_receipt_alias_mutation_or_wrong_identity',
        'tests/test_memory_family_oracle_admission_v4.py::test_rejects_rebound_raw_inventory_outside_frozen_authority_limits',
        'tests/test_memory_family_oracle_admission_v4.py::test_rejects_rebound_restore_or_commitment_semantic_forgery',
        'tests/test_memory_family_oracle_admission_v4.py::test_rejects_rebound_terminal_semantic_forgery',
        'tests/test_memory_family_oracle_admission_v4.py::test_rejects_receipt_compact_identity_and_selector_cross_binding',
        'tests/test_memory_family_oracle_admission_v4.py::test_rejects_snapshot_or_receipt_mutation_alias_and_path_following',
        'tests/test_memory_family_producer_v4.py::test_canonical_snapshot_resolves_staging_and_final_without_extra_directory',
        'tests/test_memory_family_producer_v4.py::test_compact_overhead_accepts_exact_cap_and_rejects_one_byte_over',
        'tests/test_memory_family_producer_v4.py::test_marker_sync_and_quarantine_failure_cannot_admit_source',
        'tests/test_memory_family_producer_v4.py::test_mutation_at_receipt_boundary_quarantines_and_keeps_raw',
        'tests/test_memory_family_producer_v4.py::test_postcommit_descriptor_teardown_cannot_reclassify_publication',
        'tests/test_memory_family_producer_v4.py::test_prepared_marker_does_not_skip_final_output_proof',
        'tests/test_memory_family_producer_v4.py::test_publication_faults_are_quarantined',
        'tests/test_memory_family_producer_v4.py::test_quarantine_publication_failure_remains_indeterminate',
        'tests/test_memory_family_producer_v4.py::test_read_keeps_output_identity_and_bytes_until_return',
        'tests/test_memory_family_producer_v4.py::test_read_keeps_raw_inventory_until_return',
        'tests/test_memory_family_producer_v4.py::test_read_keeps_source_and_case_namespace_until_return',
        'tests/test_memory_family_producer_v4.py::test_rebound_legacy_whitespace_is_not_raw_byte_equality',
        'tests/test_memory_family_producer_v4.py::test_rebound_numeric_candidate_still_requires_raw_equality',
        'tests/test_memory_family_producer_v4.py::test_rebound_seal_receipt_rejects_float_descriptor_sizes',
        'tests/test_memory_family_producer_v4.py::test_refuses_invalid_input_without_output_mutation',
        'tests/test_memory_family_producer_v4.py::test_refuses_unaccounted_staging_entries_before_writes',
        'tests/test_memory_family_producer_v4.py::test_seals_exact_source_without_copying_snapshot_or_deleting_raw',
        'tests/test_memory_family_producer_v4.py::test_support_boundary_accepts_equality_and_rejects_one_over',
        'tests/test_memory_family_producer_v4.py::test_unsealed_source_and_postwrite_failure_are_not_readable',
        'tests/test_memory_family_raw_audit_v4.py::test_audits_one_closed_run_read_only_and_publishes_exclusively',
        'tests/test_memory_family_raw_audit_v4.py::test_direct_file_cli_publishes_the_same_source_contract',
        'tests/test_memory_family_raw_audit_v4.py::test_mutation_after_initial_scan_rolls_back_exclusive_link',
        'tests/test_memory_family_raw_audit_v4.py::test_protocol_binds_raw_auditor_and_import_is_pure',
        'tests/test_memory_family_raw_audit_v4.py::test_public_entry_rejects_absolute_deadline_beyond_300_seconds',
        'tests/test_memory_family_raw_audit_v4.py::test_rejects_preexisting_converter_shaped_or_spliced_receipt',
        'tests/test_memory_family_raw_audit_v4.py::test_retains_a_natural_condition_failure_without_a_replacement',
        'tests/test_memory_family_retained_source_v4.py::test_exact_raw_parent_options',
        'tests/test_memory_family_retained_source_v4.py::test_known_condition_namespace_is_only_inspected_as_names',
        'tests/test_memory_family_retained_source_v4.py::test_retained_reader_checks_source_after_fake_raw_removal',
        'tests/test_memory_family_retained_source_v4.py::test_retained_reader_holds_namespace_until_return',
        'tests/test_memory_family_retained_source_v4.py::test_retained_reader_rejects_unaccounted_or_changed_evidence',
        'tests/test_memory_staged_pair_v4.py::test_marker_and_ancestor_remain_bound_through_full_pair_proof',
        'tests/test_memory_staged_pair_v4.py::test_staged_admission_accepts_audited_natural_failure',
        'tests/test_memory_staged_pair_v4.py::test_staged_admission_rejects_missing_or_mixed_source_commit',
        'tests/test_memory_staged_pair_v4.py::test_staged_pairs_preserve_portable_receipts_and_never_mutate_inputs',
    )),
    'm6-puck-learning-v2': (_puck_learning_pins, None, (
        'tests/test_puck_balanced.py::PuckBalancedTests::test_exact_partition_stop_priority_signs_and_fixed_weight_mass',
        'tests/test_puck_balanced.py::PuckBalancedTests::test_objective_source_and_protocol_byte_changes_are_rejected',
        'tests/test_puck_balanced.py::PuckBalancedTests::test_protocol_rejects_seed_types_objective_aliases_order_and_selection_changes',
        'tests/test_puck_balanced.py::PuckBalancedTests::test_separate_reader_rejects_default_schema_corruption_and_wrong_epoch',
        'tests/test_puck_balanced_development.py::BalancedDevelopmentFixtures::test_actual_evaluator_selector_all_outcomes_failure_retention_and_deadlines',
        'tests/test_puck_balanced_development.py::BalancedDevelopmentFixtures::test_actual_owner_route_real_records_and_rng_mismatch_before_prediction_one',
        'tests/test_puck_balanced_development.py::BalancedDevelopmentFixtures::test_fixed_fresh_envelope_and_protocol_pins_reject_before_bundle',
        'tests/test_puck_balanced_development.py::BalancedDevelopmentFixtures::test_scientific_and_goal_asts_rows_limits_and_default_bindings_unchanged',
        'tests/test_puck_balanced_development.py::BalancedDevelopmentFixtures::test_scientific_fingerprints_and_each_model_admission_use_historical_checks',
        'tests/test_puck_balanced_student.py::BalancedStudentFixtures::test_balanced_application_keeps_objective_identity_and_rejects_old_schema',
        'tests/test_puck_balanced_student.py::BalancedStudentFixtures::test_fixed_plan_aliases_default_binding_and_sources',
        'tests/test_puck_balanced_student.py::BalancedStudentFixtures::test_owner_rollback_restore_admission_and_fixture_host_isolation',
        'tests/test_puck_balanced_student.py::BalancedStudentFixtures::test_real_numeric_bundle_reader_and_pin_failures_before_model',
        'tests/test_puck_balanced_student.py::BalancedStudentFixtures::test_real_owner_route_and_all_fake_native_derivatives',
        'tests/test_puck_balanced_student.py::BalancedStudentFixtures::test_shared_decision_real_record_and_parameter_guard',
        'tests/test_puck_balanced_student.py::BalancedStudentFixtures::test_strict_balanced_envelope_and_default_rejection',
        'tests/test_puck_collection.py::CollectionFixtures::test_fake_native_owner_isolates_and_restores_preexisting_torch_module',
        'tests/test_puck_collection.py::CollectionFixtures::test_initial_only_envelope_rejects_restore_later_cursor_and_wrong_identity',
        'tests/test_puck_collection.py::CollectionFixtures::test_owner_discrepancy_is_retained_before_step_with_zero_executed_ticks',
        'tests/test_puck_collection.py::CollectionFixtures::test_owner_natural_task_failure_completes_record_then_data_admission_rejects',
        'tests/test_puck_collection.py::CollectionFixtures::test_owner_record_failure_does_not_commit_own_mode',
        'tests/test_puck_collection.py::CollectionFixtures::test_plan_only_exact_twenty_fresh_teacher_rows_and_budget',
        'tests/test_puck_development.py::DevelopmentFixtures::test_actual_owner_initial_match_real_record_and_rng_mismatch_before_action_one',
        'tests/test_puck_development.py::DevelopmentFixtures::test_admission_and_lease_exit_are_inside_internal_deadline',
        'tests/test_puck_development.py::DevelopmentFixtures::test_each_model_threshold_all_rows_and_no_winning_seed_selection',
        'tests/test_puck_development.py::DevelopmentFixtures::test_plan_and_fresh_typed_envelope_reject_before_bundle_read',
        'tests/test_puck_development.py::DevelopmentFixtures::test_real_filesystem_stage_all_outcomes_and_infra_stop_retains_unstarted_rows',
        'tests/test_puck_development.py::DevelopmentFixtures::test_scientific_match_includes_all_non_torch_rng_and_exact_defined_state',
        'tests/test_puck_learning.py::PuckLearningTests::test_completed_fixed_fixture_batch_preserves_labels_and_source_hashes',
        'tests/test_puck_learning.py::PuckLearningTests::test_fixed_batch_failure_keeps_all_plan_rows_and_returns_no_training_data',
        'tests/test_puck_learning.py::PuckLearningTests::test_nine_terminal_zero_labels_still_fail_and_ten_pass',
        'tests/test_puck_learning.py::PuckLearningTests::test_protocol_preserves_all_frozen_layouts_training_and_bounds',
        'tests/test_puck_learning.py::PuckLearningTests::test_record_roundtrip_reconstructs_mode_and_rejects_each_corruption',
        'tests/test_puck_learning.py::PuckLearningTests::test_v1_cursor_and_record_identity_cannot_be_readmitted_as_v2',
        'tests/test_puck_model.py::PuckCheckpointTests::test_prepare_and_pinned_bundle_use_all_twenty_sources_without_torch',
        'tests/test_puck_student.py::StudentFixtures::test_fixed_plan_and_exact_envelope_before_any_model_or_native_load',
        'tests/test_puck_student.py::StudentFixtures::test_fixture_restores_preloaded_torch_and_host_version',
        'tests/test_puck_student.py::StudentFixtures::test_live_parameter_guard_checks_exact_checkpoint_values',
        'tests/test_puck_student.py::StudentFixtures::test_owner_actual_branch_keeps_teacher_fields_absent_and_commits_after_record',
        'tests/test_puck_student.py::StudentFixtures::test_owner_invalid_action_and_record_failure_keep_completed_cursor_uncommitted',
        'tests/test_puck_student.py::StudentFixtures::test_owner_native_and_action_policy_replays_match_every_real_record_field',
        'tests/test_puck_student.py::StudentFixtures::test_owner_rejects_historical_application_before_restore',
        'tests/test_puck_student.py::StudentFixtures::test_snapshot_pins_and_restored_cursor_reproduce_policy_input',
    )),
    'm6-puck-mechanics-v5': (_puck_mechanics_pins, None, (
        'tests/test_puck_collection.py::CollectionFixtures::test_fixture_success_report_is_exact_trainer_handoff_and_re_admits_sources',
        'tests/test_puck_collection.py::CollectionFixtures::test_late_final_validation_cannot_publish_passed_stage',
        'tests/test_puck_collection.py::CollectionFixtures::test_natural_outcomes_complete_all_twenty_but_admission_blocks_batch',
        'tests/test_puck_collection.py::CollectionFixtures::test_stage_failure_retains_twenty_rows_and_final_checks',
        'tests/test_puck_mechanics.py::MechanicsFixtures::test_first_supervisor_exception_retains_all_unstarted_rows',
        'tests/test_puck_mechanics.py::MechanicsFixtures::test_historical_construction_pin_is_not_silently_promoted',
        'tests/test_puck_mechanics.py::MechanicsFixtures::test_v5_mechanics_changes_only_identity_and_version_notes',
    )),
    'm7-navigation-v2-checkpoint-support-v1': (_navigation_v2_pins, None, (
        'tests/test_male_navigation_v2_checkpoint_support.py::AdmissionTests::test_all_local_behavior_sources_are_pinned_before_import',
        'tests/test_male_navigation_v2_checkpoint_support.py::PublicationTests::test_import_does_not_load_torch_or_simulator',
    )),
    'm7-navigation-v3-matched-budget': (_navigation_v3_pins, _navigation_v3_root, (
        'tests/test_male_navigation_v3.py::MatchedBudgetTrainer::test_graph_cell_and_loaded_source_drift_stop_before_torch',
        'tests/test_male_navigation_v3_execution.py::NavigationV3ExecutionTests::test_main_accepts_real_python_argv_shape_and_checks_interpreter',
        'tests/test_male_navigation_v3_execution.py::NavigationV3ExecutionTests::test_manifest_freezes_exact_order_command_environment_inputs_and_limits',
        'tests/test_male_navigation_v3_execution.py::NavigationV3ExecutionTests::test_static_source_roster_closes_lazy_navigation_imports',
    )),
    'memory-full-cell-qualification-v4': (None, _full_cell_root, (
        'tests/test_memory_full_cell_amendment_02.py::test_amendment_accepts_exact_runtime_size_and_preserved_prior_failure',
        'tests/test_memory_full_cell_amendment_02.py::test_missing_or_different_confirmation_refuses_before_reservation',
        'tests/test_memory_full_cell_amendment_02.py::test_parent_refuses_mixed_confirmation_in_attempt_receipt',
        'tests/test_memory_full_cell_qualification_v4.py::test_valid_current_freeze_loads_without_opening_its_protected_inputs',
    )),
}


def pins(name):
    loader = PROTOCOLS[name][0]
    return loader() if loader else {}


def frozen_root(name):
    loader = PROTOCOLS[name][1]
    return loader() if loader else None


@functools.lru_cache(maxsize=None)
def drift(name):
    """Why this checkout differs from the protocol's frozen pins; empty when it does not."""
    reasons = []
    for path, digest in sorted(pins(name).items()):
        current = ROOT / path
        if not current.is_file() or sha256(current.read_bytes()) != digest:
            reasons.append(f'{path} differs from its pin {digest[:12]}')
    root = frozen_root(name)
    if root is not None and root != str(ROOT):
        reasons.append(f'frozen to repository {root}, this checkout is {ROOT}')
    return tuple(reasons)


def skip_reason(name):
    return (f'historical frozen pin ({name}): ' + '; '.join(drift(name)) +
            f'. The protocol stays bound to its commit; resume it on main by re-pinning through a new '
            f'prospective amendment ({POLICY}).')


def affected_tests():
    """Each listed test node id (without parameters) mapped to its protocol name."""
    result = {}
    for name, (_, _, tests) in PROTOCOLS.items():
        for test in tests:
            if test in result:
                raise ValueError('Test listed under two frozen protocols: ' + test)
            result[test] = name
    return result
