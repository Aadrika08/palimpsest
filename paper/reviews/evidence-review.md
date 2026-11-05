# Final evidence and numeric PDF review

Reviewed source commit: `a6f505b680688f86db6cc03dcdab8b6156565c2c`.

Reviewed PDF: `paper/build/palimpsest-systems-paper.pdf`, 10 pages, SHA256
`5df95e2ad463a9880726ebfc27a55d05766a2b119888c4be18f9f187b0b54525`.
Its hash matches `paper/build/verification.json`; that record names the reviewed
source commit. All recorded build-input hashes match the current files.

## Verdict

**Approved within this evidence/numeric review scope. No Critical or Important
findings.** The actual rendered text and numerical tables agree with the retained
rows and derived evidence. This verdict does not establish successful fresh-
environment reproduction, independent-machine qualification, public artifact
availability, or venue acceptance.

## Checks and observations

- The primary identity is execution commit
  `cc57edf9f70323926237d887d766627d8c9cdd42`, protocol SHA256
  `570a4afe8179425bb2b25b86364470af34052ecc4929b74f207c279076728860`.
  All 111 declared descriptors are accounted for: 110 completed and one
  incomplete offline unit. Analysis success is not treated as 111 successful
  executions. The retained summary is byte-identical to the final campaign's
  `analysis/summary.json` by SHA256.
- Fault accounting is 50 completed, 35 explicit detections partitioned as
  23 interface / 6 diagnostic / 6 label-guard, 12 recoveries, no reported silent
  invalid acceptance, and C3 benign rejection 0/3. There are 50 known baseline
  claims: 41 false and 9 true; accepted-and-explicitly-false count is 41. Table 1
  presents conformance rather than treating predicates as software competitors.
  Its caption correctly limits S1/B2 diagnostic divergence and distinguishes
  R1/R2 labeling guards from automatic production refusal.
- Continuation is 10/10 pairs. The five replay trajectories retain all four
  conditions; branch comparison covers 92 ticks after the eight-tick prefix,
  and action/policy reports each cover 100 source ticks. All five operation
  units' replay reports name their corresponding RQ2 source IDs and pass at
  100 ticks. The generator's retained-source and snapshot bindings pass.
- Independently recomputed every matched-set gate and the per-seed ratios
  before their median/IQR. All ten whole four-condition sets match actions,
  220 total ticks and canonical final state. Paired medians are
  68.0280409687%, 5.9587964051%, and 18.0352356952%; storage maximum is
  186.0445965161% and IQR is 38.2466913147 percentage points. Background minimum
  is -1.5513101622%. Null/storage median wall times are 14.0148323349 and
  16.5046435251 ms per measured tick. Maximum storage producer backpressure is
  4.5483963129 seconds. Displayed rounding agrees. Figure 3 generation retains
  negative values and outliers on a regular numeric axis, with distinct marks.
- Independently recomputed all seven operation medians/IQRs with n=5. Capture,
  serialize, read, restore-plus-first-tick and recorded-stream decode are in ms;
  action/policy replay are in seconds. The source confirms an already-open
  capture/restore owner, decode-only iteration of 100 records, and complete
  100-tick replay calls including startup/comparison/recording. PDF wording
  reflects those different scopes.
- Re-read all three retained S1 NPZs with pickle disabled and checked their row
  hashes. Pose velocity-command errors are 0.0319381356, 0.0275598466 and
  0.0270598233; heading errors are 0.0136870146, 0.0192768574 and 0.0260514021
  radians. Both full-state components are zero for all three seeds. Table 2
  preserves the two coordinates and does not imply a physical-distance norm or
  isolate a single omitted state mechanism.
- The retained inventory audit reports 2,938 regular files, 4,620,576,732 bytes,
  no errors and no symlinks; its inventory hash matches the retained inventory.
  The cost-state audit is bound to the current summary/inventory hashes and
  reports 40/40 passed. Independently spot-checked final raw published rows and
  reran snapshot/inventory/finite/canonical checks for seed-0 storage (the largest
  cost outlier) and seed-7 background (the negative overhead): both pass and
  published rows equal the summary. The paper correctly calls this a post-run
  audit, outside timing windows, rather than benchmark-time finite enforcement.
- The original offline descriptor remains incomplete with reason `campaign
  output admission cap`. The separately retained operational follow-up has
  `status: failed` and `replaces_scientific_row: false`. Its stderr confirms
  checkout creation followed by offline installation failure for the missing
  locked torch 2.9.0 wheel. No FLYNN run in that new environment is evidenced.
  Section 4.5 and ARTIFACT.md disclose both outcomes without replacing the
  scientific denominator. Prior initial and source-drift attempts remain bound
  in the verification input inventory.

## Verification performed and limits

The seven-file generator `--check` completed successfully against the actual
primary summary, manifest, frozen protocol and retained fault trace root.
Additional read-only Python checks recomputed row accounting, matched sets,
paired statistics, operation statistics, NPZ component errors, PDF/build-input
hashes and representative raw-state audit results. PDF text was extracted and
reviewed against these values. No scientific/model/physics jobs, regeneration,
PDF edits, full inventory rehash, or full 40-pair audit rerun were performed in
this review. The complete retained inventory/audit reports were checked for
binding and scope; only the stated raw samples were independently rechecked.
All-page visual inspection and combined test execution belong to the separate
integration lane. This review writes only this report and creates no commit.
