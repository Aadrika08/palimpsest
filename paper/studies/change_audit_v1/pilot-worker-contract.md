# Bounded audit worker contract

This standalone research artifact uses actual CPU FLYNN only when explicitly
invoked by the admitted parent. Software tests inject ordinary authored state
and doubles. Those tests qualify neither native restoration nor model behavior,
sampling eligibility, capability thresholds or certified improvement. The worker
never registers the adapter with generic replay.

## API and frozen input

`prepare_anchor(config, output, *, storage_budget)` prepares one paused, gain-one
anchor with zero policy forwards and zero control ticks.

`execute_condition(config, output, anchor_descriptor, gain, *, storage_budget)`
loads a fresh Engine, wraps its policy at the declared gain, derives the complete
snapshot identity from the externally expected original state digest, restores
with `replace_controller=False`, verifies every scientific field before the first
tick, and performs its own policy inference. Gains are exactly 1, .5, .75, 1.25.

`config` is an exact dictionary with these keys:

- `root_id`: bounded printable identifier;
- `repo_root`, `asset_root`, `prepared_graph_directory`: absolute paths;
- `scenario`: reproduction, sparse-navigation, vision-ablation or texture-variation;
- `texture`: checker, or realistic only for texture-variation;
- `seed`: integer in [0, 2**31);
- `ticks`: integer in [1,64], frozen by the parent to 64 for this pilot;
- `check_parity`: false;
- `device`: cpu;
- `controller`: flynn;
- `input_files`: unique `{path, sha256, size_bytes}` rows, absolute regular files
  without symlink traversal. The parent supplies the complete externally frozen
  source, dependency/model, prepared graph and namespace-projection roster.

The original `anchor_descriptor` is exactly `{path, file_sha256, state_sha256}`.
The file checksum and typed-state digest are checked independently before a
condition creates an Engine and again after close. All input roster pins are
also rechecked after close. Four roots can be four seeds of one approved profile.
The parent freezes all four anchor descriptors before executing any condition,
including the SHA256 of each descriptor JSON file in the immutable condition
manifest. CLI condition admission requires that externally frozen descriptor-file
checksum, independently of the SNP ZIP checksum and typed-state digest.

## Actual runtime lifecycle

Before any model load, the production binding checks the loaded `assets`,
`engine`, `flynn`, `snapshots`, `velocity_gain` and `velocity_gain_snapshot` module
file paths against `config.repo_root/src/palimpsest`. Hashing a different source
clone does not satisfy this guard. These location checks supplement the parent's
source-file hashes; they do not replace them. Injected core tests bypass
production, and production-factory tests explicitly mock module file locations.

The production binding uses `Engine.open`, preserving its metadata, diagnostics,
recording cap and setup-failure cleanup. Inside the isolated sequential worker it
temporarily replaces `assets.prepare_graph` with the existing-cache validation
branch only: validate the pinned existing archive, prepared marker, edge and
mapping files, then return the edge. No extraction function is called. The
original module binding is restored in `finally`, including setup failures.
This is not safe to invoke concurrently with another Engine opener in the same
process; the parent must use isolated sequential worker processes.

The wrapper's provenance is recorded as a standalone audit adapter. A forward
pre-hook is prepended to the actual cell so attempts are counted even when a
later validation hook rejects the input. A successful condition requires exactly
one forward attempt per completed control tick. Commands use ordinary single
`step` submissions with current state, episode and revision. No action override
is used. Natural termination/truncation retains the actual prefix and its stop
reason, without reset or padding. Engine failure, inference failure, equality
mismatch, input mutation or close failure fails the job. The worker always
attempts close, preserves both primary and close errors, and returns only after
close and pin rechecks.

Equality excludes exactly `application.source_run_id` and
`application.event_prefix`, which identify the destination recorder. Native,
controller/retina/RNG, observation, identity, all other application fields and
all other snapshot fields remain in the typed-state hash. The expected gain
identity has already been changed by the pure derivation; no gain identity field
is removed from this comparison.

## Artifacts and bounds

Each fresh output directory retains its recording, one exclusive stage report,
and (for conditions) a derivation receipt. Preparation saves one original
`anchor.snp`. Gain one reuses that exact original path and saves no extra SNP;
each other gain saves one `derived.snp`, with no duplicate initial SNP. Thus the
parent's four roots and sixteen conditions retain four original plus twelve
derived SNPs. Each serialized SNP is admitted against a 16MiB proxy cap before
file publication. Each recording, including setup and adapter metadata, has a
15MiB cap. Control JSON is finite, exclusive and at most 128KiB per file. The
worker never deletes retained evidence or retries a job.

Public production APIs require a supplied budget of at most 512MiB with at
least 6GiB free-space floor. The parent owns the one writer lease; the child
never obtains another lease. The CLI creates a shared-root budget with 16MiB
concurrent log/control headroom, and accepts only frozen production config.
The parent provides the process watchdog, 120s including setup, aggregate CPU
accounting, 30-minute pilot ceiling, bounded native logs and worst-case global
admission. The worker's cooperative Python checks are not a process watchdog.

Every report retains `sampling_eligibility_verified=false`,
`certified_improvement=false`, and `runtime_qualification=false`.
`before_first_tick_equal` is an engineering equality observation scoped by
`actual_scope`; injected tests never receive the production scope. The optional
contact fraction is explicitly pre-control input-contact ticks divided by
completed own-policy ticks, an engineering observation with no inferential claim.

The CLI requires `--mode`, `--config`, `--expected-config-sha256`, `--output`,
`--pilot-root`; condition mode also requires `--anchor`,
`--expected-anchor-sha256` and `--gain`. Both config and descriptor checksums bind
the exact bounded bytes decoded, and both files are rechecked before CLI success.
The Python `execute_condition` API continues to accept an externally bound
descriptor dictionary. The CLI has no
fixture or alternate-engine argument. Config or descriptor checksum mutation causes a failing
exit even if an earlier stage report was written; the parent must accept a job
only after both its process exit and final artifacts are checked.
