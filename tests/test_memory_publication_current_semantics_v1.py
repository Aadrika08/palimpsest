"""NEW current-profile regression IDs; historical frozen IDs stay historical.

These tests deliberately reuse the original assertion functions and their full
parameter matrices against explicit test-owned current-source profiles. Their
new node IDs are not an acceptance or unskip of any historical protocol. No
qualification/execution pin is populated, and no model/physics owner runs.
"""
from memory_publication_authored_profiles import authored_current_profile
from test_memory_family_retained_source_v4 import (
    test_retained_reader_checks_source_after_fake_raw_removal as test_current_retained_source_attestation,
    test_exact_raw_parent_options as test_current_exact_raw_parent_options,
    test_retained_reader_rejects_unaccounted_or_changed_evidence as test_current_retained_source_forgeries,
    test_retained_reader_holds_namespace_until_return as test_current_retained_namespace_custody,
)
from test_memory_family_producer_v4 import (
    test_read_keeps_output_identity_and_bytes_until_return as test_current_source_output_custody,
    test_read_keeps_source_and_case_namespace_until_return as test_current_source_case_namespace_custody,
)
from test_memory_family_oracle_admission_v4 import (
    test_admits_all_nine_exact_condition_identity_mappings_read_only as test_current_nine_condition_mappings,
    test_rejects_snapshot_or_receipt_mutation_alias_and_path_following as test_current_pair_snapshot_aliases,
    test_rejects_prior_own_receipt_alias_mutation_or_wrong_identity as test_current_prior_own_aliases,
    test_prior_own_nested_values_bind_current_source_and_own_mapping as test_current_prior_own_nested_binding,
    test_admission_keeps_all_input_bindings_until_return as test_current_pair_input_custody,
    test_admission_deadline_includes_final_descriptor_reread as test_current_pair_final_deadline,
    test_final_snapshot_reread_rechecks_ancestor_edges as test_current_pair_ancestor_recheck,
)
from test_memory_family_condition_close_v4 import (
    test_caller_descriptor_mutation_cannot_rebind_validated_registration as test_current_registration_copy_on_entry,
)
