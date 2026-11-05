# Change-audit runtime pilot v1

This is the engineering pilot authorized by the proof-first completion plan. It has no inferential or capability-success claim. Pilot observations must never be reused in a later confirmatory audit or held-out study. No runtime has launched.

## Fixed action change and restoration

Use the pinned full CPU FLYNN controller with baseline velocity gain 1 and candidate gains 1/2, 3/4 and 5/4. Each condition runs its own inference; never rescale or replay another condition's recorded action. Scale only the outgoing velocity coordinate, retaining heading, observation access, encoded input, raw network output and native action conversion/clipping. The adapter is isolated from existing frozen behavior modules. Its immutable gain and baseline-policy identity must enter snapshot identity/provenance.

Capture the complete paused native/environment/application/controller/retina/RNG/observation state before observations. A gain-only snapshot derivation must bind the original snapshot hash, admit only the registered baseline/candidate gain difference, preserve every other byte/value, and restore through the ordinary complete-state path. `replace_controller=True` is forbidden because that path intentionally drops controller and Torch RNG state. Verify the restored state's equality before any candidate tick. Keep original and derived snapshots and derivation receipts.

## Execution limits and admission

One sequential CPU worker at a time; four fixed scenario roots and four gains give 16 conditions. Each condition has at most 64 ticks, 120 seconds including load/restore, no retries, and no continuation after a failure. A natural terminal outcome is retained with its actual observed prefix, never silently reset or padded into 64 successful ticks. The entire pilot has a 30-minute wall ceiling and at most one aggregate process CPU-hour, charged to the audit lane within the 24-hour project allocation. Capture actual process/descendant accounting, including failed prerequisites and terminated jobs. Unknown accounting prevents further admission.

Retained output including snapshots, recordings, logs, supervision and incomplete files is at most 512MiB; maintain 6GiB disk reserve. Use the existing single-writer storage budget, bounded native logs and process-group timeout. Admit fixed per-file/count bounds before launch; refuse if the full worst-case allocation cannot fit. Never delete old or partial evidence.

Before choosing concrete scenario/seed roots, inspect the public scenario definitions and disjoint identity projections; do not open protected catalogs or held-out metadata. Freeze the four roots, gain order, source SHA, dependency/model hashes, actual runtime configuration, all limits and expected namespace projection hashes in an immutable run manifest before inference. There is no permission to change roots after results or substitute a failed input.

## Software verification before launch

Use actual red/green tests for gain validation, exactly one delegated inference, untouched heading/observations/raw output, no mutation of the returned base action, rejection/rollback on invalid or overflowing output, and snapshot-state delegation. Test a pure snapshot derivation against unauthorized identity/state changes. Independently review the adapter, derivation, process accounting and full output admission before the actual pilot.

Report engineering identity/restoration/logging/resource results separately from arithmetic checks, sampling eligibility, capability thresholds and the paper's empirical conclusions. Passing this pilot cannot discharge the Lean sampling premises.
