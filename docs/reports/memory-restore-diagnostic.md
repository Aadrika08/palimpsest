# Restore diagnostic: implemented tooling, admission stop

4 October 2026. **The registered diagnostic invocation was refused before any
job allocation or native owner.** No post-state was captured, so the original
restore mismatch remains unlocalized. Restore repair, fresh qualification and
the paired pilot are unattempted. No retry occurred.

[Approved contract](../plans/memory-restore-diagnostic.md),
[prospective registration](memory-restore-diagnostic-evidence/registration.json),
[exact invocation](memory-restore-diagnostic-evidence/native-launch.json),
[original error log](memory-restore-diagnostic-evidence/native-invocation.log),
[admission-stop receipt](memory-restore-diagnostic-evidence/admission-stop.json).

## What was implemented

The worker has an opt-in `--retain-repeat-state` private option, refused for
non-repeat operations. Existing job/protocol and snapshot container schemas are
unchanged. Default workers publish the original digest only. Opted-in workers
save the **same captured post-state used to calculate that digest**, before
cleanup, together with its checksum, component hashes and initial receipt IDs.
There is no additional engine capture or physics step.

Existing condition/receipt normalization is factored into inspectable pure-state
helpers without changing what is excluded or compared. The diagnostic driver
supports an exploratory two-restore diagnosis and a separate fixed-profile,
eight-fresh-prerequisite qualification mode. Its comparison retains exact typed
state, signed-zero/dtype/shape differences, native bytes and every application
field, with bounded human-readable differences and complete component hashes.

An offline decoder exposes named plain numeric MjData fields, native timer,
warning, solver and contact arrays plus a serialized model hash. It uses trusted
same-version snapshot deserialization and calls no reset, forward, policy or
physics step. The named inventory is not a complete interpretation of opaque
native bytes; it cannot authorize ignoring residual differences. Neither driver
mode has native qualification evidence from this attempt.

## The exact failure and narrow launcher fix

Contract commit `96f8ef9` precedes implementation `91b9c16`; machine registration
commit `b067b9c` precedes the one invocation. Registration binds the selected .25 m
profile, audited prior south-prefix source SNP, prepared assets/history/source and
all339 retained prior-study files. The output was registered as
`runs/memory-restore-diagnostic-20261004T152633Z`.

The launcher checked Git cleanliness, opened the new documentary
`docs/reports/memory-restore-diagnostic-evidence/native-invocation.log`, then started
the diagnostic child. That newly untracked file made the child's repeated
clean-checkout admission fail with:

```text
ValueError: Native admission requires a clean implementation checkout
```

This was a launcher ordering defect introduced by this branch, not a native
restore or task failure. The child exited1 before preparation/output creation.
Post-stop inspection confirms the registered output is absent, with zero
allocated jobs, zero native owners and zero new native controls. No stage report
or scientific-close receipt exists; none is fabricated. The exclusive invocation
marker and failed log are retained.

[Executed launcher](memory-restore-diagnostic-evidence/executed-launcher.py) is an
exact copy of the implementation used for this attempt; its SHA256 is
`c24516f216806564db538eca5cd0ae6d684f6ae9dbe672f28e5425d512985c42`.
The delivery launcher writes the live log inside this plan's ignored workspace
and publishes it only after the child exits. A regression creates a real temporary
Git repository and checks cleanliness across the parent-to-child admission
boundary while substituting a process stub. It failed with the exact untracked
log, then passed after that single fix. It starts no native policy or experiment.
[RED](memory-restore-diagnostic-evidence/launcher-red.log),
[GREEN](memory-restore-diagnostic-evidence/launcher-green.log).

The corrected launcher has **not** run another native attempt. The original
registration, marker and output path remain consumed by this attempted invocation;
they are not reused. A successful software regression does not qualify native
restore admission or repair the original post-state discrepancy.

## Validation and evidence limits

The diagnostic tests cover exact digest-input retention/default behavior,
normalization and state changes, copy checksum/invariant/overwrite refusal,
missing/corrupt final states, source receipt binding, started-but-unscored owner
accounting, deadline/storage refusal, signed zero and dtype differences,
offline native field localization and the launcher admission boundary.

Before the invocation, focused checks passed69 tests and the full local suite
passed930 /skipped24, with39 warnings, in102.70 s. After the launcher fix,
all16 diagnostic software tests passed and the full suite passed931 /skipped24,
with39 warnings, in98.02 s. Independent review then identified one Important
software issue in the unexecuted qualification mode: a passing flag could survive
a failed final provenance check or a deadline crossed during receipt publication.
Both were reproduced through production `main` with completed-owner software
fixtures, observed failing, then fixed to invalidate promotion on failed close.
All18 diagnostic tests pass. The final post-review full suite passed
**933 /skipped24**, with39 warnings, in101.73 s.
[Final full-suite log](memory-restore-diagnostic-evidence/reviewed-full-suite.log). [Review regression RED](memory-restore-diagnostic-evidence/readout-red.log),
[GREEN](memory-restore-diagnostic-evidence/readout-green.log).
[Independent review](memory-restore-diagnostic-evidence/final-review.md) found
no other Important findings and no Critical or Minor findings. The exact
registered driver is preserved as
[executed-driver.py](memory-restore-diagnostic-evidence/executed-driver.py); delivery
fixes do not retroactively qualify the refused invocation. RED/GREEN and full output
are in the evidence directory.
These are software/fixture checks; they do not establish completed native diagnosis,
deterministic restore, passing prerequisites, R2 benefit or physical qualification.
CI remains excluded.

The audited source SNP remains local and intact, SHA256
`c839fae1fe3d981cf4b7073970f7eb06d5738f009d6cb23f249408fd227cf6bf`.
It was not copied into a diagnostic stage because admission stopped first.
Raw prior NPZ/SNP payloads remain local. Compact Git metadata are not a replay
bundle. Post-stop integrity checks and report/publication work add no native
measurements and do not pretend to extend a scientific readout deadline.
[Publication integrity](memory-restore-diagnostic-evidence/publication-integrity.json)
checks all339 prior recovery files and all24 historical abort files unchanged.

## What remains

The recovery-study evidence still shows six of eight prerequisite gates passing.
Both prior five-tick restore traces and recorded final memory/world state match,
but full post-state hashes differ. This attempt adds no evidence about the cause.

Next is a **separately registered diagnostic study** using the corrected launcher,
a new output path and exclusive invocation marker. Freeze its implementation and
registration, retain the previous refusal, then run one two-restore diagnostic
pair. Stop if the discrepancy is unlocalized, does not reproduce, or requires a
scientific-contract amendment. Make no speculative normalization change.

Only a demonstrated repair preserving the existing contract permits one new
eight-prerequisite qualification attempt. Pilot, R2 benefit, R3 navigation, learned
puck capability, held-out, hardware/operator and exhibition gates remain open.

Repository-local author Aadrika Maurya <aadrikamaurya@gmail.com>. Publish as
Aadrika08, stacked on PR #69 against `research/memory-travel-recovery-study`.
Main remains `ee6bf61ea8faec02d5522c7eee30ab7cf333f29d`; no merge or CI work.
