# Finite expected-missing imports: source implementation

## Scope and working behavior

Base9b478a5 (draftPR135). Previous turn made progress: admitted preparation01
passed, qualification01 failed and was independently audited. Both are consumed.
The first cause numpy._distributor_init_local informs this source-only change;
no actual stage or installed payload read is repeated. All seven release gates
remain open, and the three study decisions remain pending.

New qualification descriptor-v2 within bootstrap-v3 permits a sorted finite list
of1..128 unique exact ASCII nonstdlib names, each at most512 characters. Prefix
overlap, wildcards, reserved bootstrap identities and local source roots refuse.
Descriptor-v1 keeps its original fixed org denial; bootstrap-v1/v2 and dependency
registration-v1/v2 schemas remain unchanged. The fixed three-import entry stays fixed.

HeldDependencyNamespace.require_absent_imports performs full custody recheck and
validates absence against physical modules, namespaces and declared profile
exports, including inactive/prepared exports. Child names require a registered
package/namespace parent and use its actual mapped root/path; canonical paths
are also checked conservatively across all admitted package roots. Full censuses
include empty dirs; .py/direct and tagged .pyc/native suffixes and same-stem
directories refuse. Similar prefix siblings do not collide. System-image roots
are not import namespaces. Absence is scoped to admitted package namespaces,
never host-wide absence. Parent-miss semantics remain Python's ordinary semantics.

Bootstrap validates the entire declared list at admission and checks the exact
requested name against fresh full custody before each exempt denial. Only after
validation succeeds does it raise exact ModuleNotFoundError with name=fullname
without poisoning or ambient fallback. Other misses, collisions, drift or guard
errors poison and retain first cause. Frozen declarations are captured as a tuple;
receipts distinguish declared expected_missing_imports from observed denied_imports.
All authority fields remain false. Existing trusted-source/native/stdlib/lease/
process/operational bounds are not expanded into hostile in-process proof.

## Verification so far

- Provider53RED0.41s (missing API), then53GREEN0.21s by bounded builder.
- Worker collection first hit a reserved pytest parameter name; corrected in
  authored tests before production changes. Then the3 real root/child/relative
  successes RED0.25s at missing descriptor-v2; integrated24GREEN10.02s.
- First affected run:292passed/1failed89.96s. Existing
  test_support_dispatch_is_checked_before_new_profile_callbacks[validate_profile]
  refused a changed held ancestor before its intended assertion. Its two isolated
  support_dispatch cases pass2.45s. Cause of ancestor change was initially unknown.
- Second affected run:288passed/5failed80.42s, again early held-ancestor refusals:
  test_fixed_entry_retains_no_success_when_import_or_identity_gate_fails[fail-AUTHORED_IMPORT_FAILURE];
  test_declared_export_is_prepared_before_later_cache_publication_without_hooks;
  test_export_declarations_never_allow_wrong_objects_or_later_drift[class];
  test_explicit_module_transition_uses_original_producer_class[replace];
  test_generated_classes_bind_each_invocation_to_held_factory_code_and_base.
  No guards changed; a bounded authored copied-source diagnostic is investigating
  the offending ancestor. No full affected-suite pass is claimed yet.

## Prospective configuration and remaining gap

[Proposal](../plans/puck-v3-expected-missing-imports-proposal.json) names only
numpy._distributor_init_local and org with exact candidate-source and retained
dependency/outcome references. It is non-executable and not an admission freeze.
The existing actual parent remains allocation01/descriptor-v1 only. A separately
numbered parent/capsule/allocation and prospective scope decision, complete bounds,
independent exact-freeze review and outcome audit are required for any later run.
No ordinary observation refresh, actual retry, model/scene/catalog/study/physics/
collection/fitting/browser/operator or rover work follows from this source change.

## Authored ancestor diagnostic

A copied-fixture diagnostic (only exception detail changed in copied authenticated
source) ran10 passes then failed probe10 at12.242s: exact ancestor/tmp, with
mtime/ctime changing from1792035719158135178 to1792035731371245388. FD and named
identity otherwise agreed. Actor unknown. One equivalent worktree/runs fixture
passed1.379s, answer43. This identifies the diagnostic failure, not every prior
full-slice failure. [Retained diagnostic](puck-v3-expected-missing-imports-diagnostic/observation.json).
Root will use owned worktree/runs pytest basetemp; no production guard is changed.

## Owned-storage regression result and measured native limitation

Owned basetemp run:288passed/5failed94.14s. No ancestor refusal in the five
reported failures. Existing native positives failed:
- test_explicit_origin_policy_works_in_complete_worker_without_changing_v1;
- test_native_export_is_bound_before_create_module_guard[native_create-True];
- test_native_extension_initializes_from_held_file_and_is_observed;
- test_held_directory_origin_loads_authored_sibling_and_observes_exact_target[$ORIGIN];
- same native-origin test[$ORIGIN/../lib].

Two bounded authored C probes then measured the raw identity assumption. On
Btrfs native fstat/pathstat(dev57,inode26746125), maps(dev29,same inode); helper
dev57vs29,inode26746124. On tmpfs native/helper fstat/pathstat/maps all dev55,
inodes1761200/1761194. Both functions return47. Current native target check
refuses Btrfs and accepts tmpfs. Own map_files readlink succeeds; following stat
is denied errno1 on both. Raw stdout/stderr and authored C retained beside the
ancestor diagnostic. The underlying filesystem mechanism is not yet established.
This is an inherited native identity limitation; missing-import policy was not
invoked in these two probes. Native checks remain unchanged. A native object
identity contract on the actual filesystem is required before another real
runtime allocation. No path-only whitelist is accepted as identity proof.

Default pytest:10 collection errors2.28s. FastAPI absent in test_lab.py and
test_male_lab.py; httpx absent in test_male_recovery_collection.py,
test_male_recovery_data.py,test_train_male_recovery.py,
test_verify_body_adaptation.py,test_verify_body_runtime.py,
test_verify_body_turns.py,test_verify_task_phases.py,test_verify_task_starts.py.
No default or full affected-suite pass is claimed.

## Independent source close and next action

Fresh whole-branch review off25cb3a found no concrete Critical/Important/Minor
source defect;90 authored+legacy entry checks pass20.27s independently. Proposal
identities and false authority verified. [Review](puck-v3-expected-missing-imports-review.md).
Broader affected slice and default suite remain unqualified as recorded above.
The source policy unit is reviewed; actual runtime compatibility is not proved.
[Next source deliverable](puck-v3-native-filesystem-identity-next.md) is an explicit
native mapped-object identity contract for the actual filesystem, with authored
proof and a separately reviewed configuration proposal. No actual retry follows.
