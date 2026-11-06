# Implementation rulings after contract review

These additive engineering decisions preserve the reviewed actual schemas,
external authority requirements and physical output caps. They require source
implementation and independent review; they are not measured execution facts.

1. In the private authored domain only, `Model.manifest` denotes the AD of
   `W/freeze/metadata/authored-model-identity.json`, containing the exact
   `AuthoredModelIdentity` of contract section14. Declare this initial input as
   Slot role `authored-model-identity`, maximum262144 bytes, and include it in
   frozen-input census and continuous custody. It introduces no Readset key or
   output slot. Its fixture_id joins authorization, resources and namespace
   coverage/bindings. The ordinary prepared-assets manifest remains separately
   held/pinned in SourceClosure at the authored repo's
   `model_manifests/flynn-full-vision.json`. Validate both separately; never feed
   model-identity JSON to the ordinary assets parser. Actual Model.manifest and
   full-model guard semantics are unchanged. Cost if wrong: rework of the
   authored attachment/loader and tests before actual source integration.

2. Keep the source-generated ordered exception-group helper in the existing
   package module `palimpsest.records`, for example `_source_errors`. The new
   research records module can import/re-export it as `errors`; Engine and
   RunWriter must use the package-local helper. Avoid a new `palimpsest` library
   dependency on the repository's top-level `scripts` namespace. Keep the same
   original-exception ordering, source-group marker and identity deduplication;
   one implementation, no generic framework. Add authored coverage with research
   script imports denied, proving opt-in recorder/canonical cleanup succeeds or
   preserves original failure without importing research modules. Cost if wrong:
   bounded package-boundary/helper compatibility rework before delivery.

3. Authored units may run the six orchestration modules and project library
   from their real worktree source paths. Their explicitly named source files
   may be external AD standalones in SourceClosure and authored
   ModelIdentity.runtime_sources, continuously held at those real paths. Freeze
   a literal source-only roster justified by the fixed implementation imports;
   do not discover arbitrary files or include interpreter/native/runtime/model
   binary payloads. This is a narrow exception to authored fixture containment
   for unit-harness source identities only. Generated weights, graphs, mappings,
   namespace data and metadata remain in the fresh fixture. Copied model/upstream
   source files may be model_sources only when actually imported from there.
   Never label unused source copies as loaded sources or build another package
   isolation system merely to relocate the unit harness. The tiny authored
   RuntimeHandle fixture establishes only its own current bytes, not provenance
   or qualification of the executing installed runtime. Actual Python/Torch/
   device/dtype/thread observations remain separate numeric-core checks. Authored
   reports and candidate records must state this limited harness scope and bind
   actual source origins; actual execution closure/admission remains unchanged.
   Cost if wrong: bounded authored origin/guard/fixture rework before integration,
   with no valid actual qualification inferred from these units.

4. Place the bounded full-parent authored regression below a fresh per-run
   directory in `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence`,
   outside repository/assets, with its temp/scratch children precreated before
   leases. Verify spelling and symlink-free ancestors; retain all earlier
   failures. `/var/tmp` full-stat mutations made the prior test environment
   unsuitable. This changes only ordinary test placement and TMPDIR, not any
   ancestor/byte/alias/namespace/deadline guard or actual research permission.
   The /var/tmp preference in the implementation brief was a quota-related
   engineering choice. No further run-to-pass loop is authorized if the same
   instability occurs at the new location. Cost if wrong: retain an incomplete
   unit attempt and diagnose its named ancestor before more test execution.

5. Use Owner.status=`owner-intent-unqualified` for the durable pre-Engine intent
   signal, replacing the earlier contract literal `recorded-unqualified` in
   Owner only. Worker Report.status remains `recorded-unqualified`, published
   only after genuine successful close. Keep both exact schemas and every false
   scope claim otherwise unchanged. An intent cannot establish recording or
   qualification. Cost if wrong: bounded literal/validator compatibility rework
   before any actual record is collected; no historical schema is relabeled.

6. Update only the explicitly named canonical cleanup assertions whose old
   expectations deliberately allowed replacement of the body error or a bare
   teardown error. Require original body plus all teardown errors and actual
   resource drain, retaining the prior expectations/diff in the implementation
   record. Legacy default behavior remains unchanged. Add fixed source-owned
   write admission through the existing Engine/RunWriter/SNP budget seam:
   component/atomic/headroom and free-minus-incoming checks must precede writes,
   with post-write verification, including the reserved raw report share. A
   later report-time rejection cannot substitute for preventing an earlier
   storage overshoot. No new public callback, recorder rewrite or cap increase.
   Cost if wrong: bounded budget/cleanup-test rework before source qualification;
   quota refusal must retain incomplete evidence, never become accepted success.
   The approved assertion set is bootstrap's
   `test_close_error_preserves_failed_recording_and_environment_cleanup`,
   `test_open_failure_with_renderer_close_error_still_closes_env_and_real_writer`,
   `test_real_writer_broken_budget_keeps_original_failure_semantics`, and the
   preservation test's
   `test_canonical_engine_handoff_preserves_real_writer_manifest_failure`.
   Other existing assertions are outside this amendment.

7. In the new source owner only, expand the existing short `policy_step`
   orchestration into the same real Engine submit/advance protocol so a fixed
   loaded-identity check can run between them. Preserve command ID
   `neural-{engine.episode_step}`, kind `step`, expected paused state and current
   episode; require the same controller/policy/phase and queued-result checks.
   Check before submit, between submit and advance, and after advance. Reuse
   Engine, world, controller and arithmetic unchanged; the old helper/default
   path stays unchanged. Test a generated-policy mutation during real submit,
   refusing advance and draining pending commands/resources. Cost if wrong:
   bounded orchestration/test rework before actual source qualification.

No actual model/native/runtime/namespace payload access, experiment, provider
adoption, execution approval, accepted Q/L/F/R, CPU debit or deletion follows.
