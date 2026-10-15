# Actual CPU metadata observation03

One frozen, independently reviewed invocation completed normally and its separate
independent CLI audit passed. The three terminal distributed rosters match the
11/69/29-name source proposals exactly. **This accepts ordinary metadata evidence
only; profile acceptance and held-runtime qualification remain false.**

## Controls and actual execution

Source is `32d1dc690d93ffdfa820bcbe871515266acde5b0`; controls were committed and
pushed at `c998fa3842d8efb2103ec8d23c9bc0eb2f04764b` before invocation. The
[execution plan](../plans/puck-cpu-runtime-characterization-03-execution.md),
[control manifest](../plans/puck-cpu-runtime-characterization-03-controls.json) and
[independent control review](puck-cpu-characterization-03-controls-review.json)
bind the original isolated CPU interpreter, 19 sources, 63 inputs and 19 roles.
The canonical configuration SHA256 is
`69cc87fb68e3c745196b3435c4caaa547ad3bb120ceac6d4834d6b24eecb4e49`.

Data-only admission exited 0 with `DATA_ONLY_ADMITTED` in 7.749 s. It rehashed all
27,225 SITE files / 2,074 directories / 1,304,701,872B, the declared 29 native files
and 23 aliases, plus the trusted interpreter's 4,233 files and 1,048 symlinks.
Immediate prelaunch admission rechecked all seven committed controls, all four
output absences, 96,778,465,280B free project disk, 3,928,092,672B MemAvailable and
65,536 soft descriptors, against unchanged 4 GiB / 2 GiB / 40,000 floors.

The observer was invoked once, with existing session 79047 polled to its final
normal exit 0. Its receipt reports 14.163679150 s and no timeout. The parent reports
14.076115132 s, four exact versions and complete namespace/worker supervision.
The sole independent auditor invocation exited 0 and published `PASS` in 3.557829455 s.
The concretized command was recorded before that invocation, appending only the
measured transport SHA256
`cf0aa869200d07b74be7a40e89a6de8213dd9bbc6ecba1628b8ab0684c7865d3`
to the frozen prefix. External terminal records are retained separately from
program PASS documents; the records honestly identify the tool's combined output.
Reported durations and sampled RSS are operational observations, not timing bounds.

## Measured result and its limits

| Child | Observed dispatch names | Missing | Extra | Stable raw/cache identity |
| --- | ---: | ---: | ---: | --- |
| `torch._C._distributed_autograd` | 11 | 0 | 0 | Pass |
| `torch._C._distributed_c10d` | 69 | 0 | 0 | Pass |
| `torch._C._distributed_rpc` | 29 | 0 | 0 | Pass |

Exact sorted names and plain-module/shared-file metadata are retained in the
[raw report](puck-cpu-characterization-03/raw/payload/imports.json) and verified by
[the independent outcome audit](puck-cpu-characterization-03/outcome-audit-03.json).
NumPy 2.2.5, Torch 2.9.0+cpu, torchvision 0.24.0+cpu and MuJoCo 3.3.6 imported in that
fixed order. Parent descriptors stayed 5 → 5 with no active child/non-main thread;
all handles and receipts closed. Both child supervisors completed 0 with no matching
survivor. The observer's five sampled PID/start identities had no sampled survivor;
the independent auditor rechecked their absence. This is neither exhaustive nor
atomic PID-lifetime proof. Worker stderr retains a 194 B `reduce_op` deprecation
warning from the unchanged cache inspector; no warning suppression was added.

The audit verified current SITE/native/interpreter bytes, before/after summaries,
source/input/history bindings and preserved eight originally missing receipts.
Original failed installer/admission/observation01 and held qualifications01–04
remain failed and consumed. No actual05 configuration/output exists. Terminal
rosters do not establish creator-close timing, intermediate publication, private
build provenance, held/native/renderer qualification or physical behavior.
No model, scene, protected catalogue, operator, renderer, episode or study ran.

## Retained proof and next action

[The evidence index](puck-cpu-characterization-03/evidence-index.json) binds 116
artifacts / 9,164,930B, including two empty files: 19 current source capsules,
63 input capsules, five committed controls, 18 raw files, external tool records,
independent peer review and the reused packet byte verifier. Copies compare
against originals; directly retained tool records have no separate original
stream. The independent peer read/hash review finds no material issue and did
not rerun the auditor, installed census or target code. Packet/Git validation is
a separate root check.

The pre-freeze manifest construction initially refused an incorrect worker
filename before creating the manifest or invoking anything; its correction changed
no source/configuration/admission bytes. A later audit-command preparation refused
an overbroad file-stat comparison after reading the receipt. The exact failing
pre-read fields were not retained; the recorded correction uses the established
seven-field identity contract, excluding access time. That failure is preserved
in `audit-preparation-error-01.json`, before the sole auditor invocation. No
observation/auditor retry or frozen-control change occurred.

The generic packet verifier passed original-byte/source-commit checks before
commit. Require this command after committing the packet to check every archived
byte against Git too; it reads data only and never repeats the observation:

```bash
python -I -S -B docs/reports/puck-cpu-characterization-03/verify_evidence.py --originals --git-revision HEAD
```

**Next:** attribute every measured name against the retained creator/closure proof,
review the explicit three-row prospective profile and closed parent/auditor
admission, then separately freeze actual05 only after that source exit. Preserve
the one-row candidate and the other 32 declarations. The product milestone remains
one admitted real episode with verified recording, replay and portable export.
All seven release gates remain open; physical rover work follows accepted simulation.

The initial post-commit archive check caught three indexed input copies omitted
by the existing `runs/` Git ignore rule. The [archive correction](puck-cpu-characterization-03-archive-correction.json)
retains that failed check and force-adds only the exact three unchanged files.
The index, original evidence and runtime sources remain unchanged; no actual
observation or outcome-auditor invocation was repeated.
