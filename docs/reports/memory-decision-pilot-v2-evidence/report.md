# Selected memory decision pilot v2 result

8 October 2026. The separately approved six-case/four-condition pilot completed
once: all six fresh acquisitions and 24 continuations received independent raw
audits, and 22 continuations reached goals. Authoritative close reports
`pilot_complete=True`, `mandatory_pass=True`, **`mechanism_observed=False`**.
The null case's own and sham conditions failed naturally with `CueUnavailable`;
both retain the frozen 900-tick failure score. No case was replaced or rerun.
Memory/R2 and the simulation-first project remain incomplete.

The [frozen plan](../plans/memory-decision-pilot-v2.md) records its pre-execution
state. Its statements that execution had not started are historical, unchanged
registration inputs. This report records the subsequent approved execution.
The pilot builds on the [passing selected-profile v3 prerequisites](memory-prerequisites-v3.md).

## Implementation and verification

Implementation commit `1856835` adds an explicit versioned admission bridge,
30 registered owner slots, a bounded registration preparer, an original-clock
launcher and independent close. It reuses the existing native worker, storage,
supervisor and raw auditors. Legacy protocols remain available with their original
defaults. Controller, world geometry, sensor/task contracts, assets and historical
U were preserved; the new worker derivation is explicit in registration.

Admission checks the old authoritative registration/close and exact retained
inventories, executable/runtime identity, source derivation and resource bounds
before model import or owner allocation. Full audits stay in bounded individual
files; driver and close reference them by path/hash. Independent close re-reads
the jobs, supervision, raw records and source snapshots within the original
invocation, checks pair predicates and retained same-namespace owner exits, then
publishes its result. It starts no additional native owners or physics controls.

The final local software suite passed **1,146 tests, 24 skipped**, exit 0,
287.41 seconds (292.186 seconds outer wall time). One whole-branch review found
0 Critical and 3 Important issues: exact runtime equality, current helper pins
and native float32 action-threshold arithmetic. All three were fixed and verified.
Earlier failed software runs are retained; the initial full suite's three child
import failures were resolved by an explicit checkout `PYTHONPATH` in the test
invocation. See [software evidence and reproduction](memory-decision-pilot-v2-software-evidence/implementation.md).
Tests and optional skips do not supply scientific or capability qualification.

## Allocation consumed

| Allocation | Approved cap | Observed retained result |
|---|---:|---|
| Registration, including its commit | 180 s | 17.961 s preparer; 18.088 s outer; exit 0 |
| One native invocation | 6,600 s | 2,847.971 s outer; exit 0 |
| Independent close | 600 s, also original global deadline | Close 344.767 s after readout start, 255.233 s before its deadline |
| Native owners | 30 maximum, serialized | Exactly 6 acquisition + 24 continuation owners |
| New aggregate storage | 8 GiB + continuing 2 GiB free floor and 64 MiB headroom | Within cap; exact post-publication receipt is linked below |
| Retries / corrective studies / fallback profiles | 0 | 0 |

Registration commit `d54a7df` pins implementation `1856835`, the six resolved
cases, existing selected .25 m profile, historical U, runtime and 30 exact slots.
Registration SHA-256:
`61b295030e692c580331d5ab282ab380da87e7b7d3718f4e31809238835543a1`.
Python 3.11.15, MuJoCo 3.3.6, NumPy 2.2.5 and Torch 2.9.0 CPU were pinned;
one numerical thread, EGL and disabled CUDA were retained.

The driver started at `2026-10-08T02:22:26.080052+00:00`. Close completed
2,839.800 seconds from its retained original monotonic origin. The outer wrapper
receipt reports the entire invocation separately. Driver preliminary status is
`pilot-provisional-pass`, with `pilot_complete=False`; only the independent
`scientific-close.json` supplies the authoritative complete result. Its
`new_native_owners=0` and `physics_steps=0` mean the **close** introduced no new
simulation, not that the preceding 30 owners did not run. Total newly issued
controls retained by close: 12,102. All 30 owner exit checks passed in the original
process namespace; later byte checks do not independently requalify process exits.

## Observed outcomes

Each table value is the retained capped continuation score, excluding acquisition.
Goal success uses actual continuation ticks; audited natural task failure receives
900. Every four-condition pair passed own/sham trace identity and the opportunity
gate. All six prefixes acquired their two real open observations and a fresh
pre-event snapshot; four continuations use that case's exact source bytes.

| Case | Own | Swapped | No-U | Sham | Goals |
|---|---:|---:|---:|---:|---:|
| local_cue-south | 246 | 528 | 528 | 246 | 4/4 |
| local_cue-north | 220 | 569 | 569 | 220 | 4/4 |
| paired_cue-south | 246 | 528 | 528 | 246 | 4/4 |
| paired_cue-north | 220 | 569 | 569 | 220 | 4/4 |
| local-null | **900, failed** | 198 | 198 | **900, failed** | 2/4 |
| paired-no-event | 197 | 197 | 197 | 197 | 4/4 |

The four change cases have retained `m_caused_route_difference=True` and
`closed_route_cost_observed=True`. Own/sham first commit to route-z; swapped/no-U
first commit to the subsequently blocked route-a, inspect, retreat and replan to
route-z. Own/sham need one inspection and zero replans; swapped/no-U need two
inspections and one replan. South paths are 5.927794 m versus 13.227118 m; north
paths are 5.368053 m versus 14.305063 m. First commitments occur at tick 729,
before the fresh post-event passage samples. No separator bypass is reported.

In local-null, own/sham also select route-z while swapped/no-U select route-a.
Own/sham terminate after **153 actual continuation ticks**, phase `failed`, at
880 total ticks including acquisition. The audited exception is
`CueUnavailable`, with message
`selected_waypoint_unavailable: memory-v2-00000192-local_cue-null-0-subject-z-exit`.
Each has one unavailable cue, one inspection and no replan. Swapped/no-U reach
the goal after 198 ticks, with one inspection, no replan and no unavailable cue.
These are admitted task failures, with independent raw terminal proof, rather
than infrastructure interruptions. Their full 900 scores remain visible.

The frozen null false-targeting predicate compares **scored path length**:
own must travel farther than no-U. Its retained own/sham path is
3.769848166935070 m; swapped/no-U path is 4.967686942831037 m. Early failure
ends the own path sooner, so `false_targeting_cost_observed=False` and the
composite `mechanism_observed=False`. Failure-score disadvantage does not change
that prospective predicate. Replacing path cost with the 900 score after seeing
the result would be retrospective re-scoring, and was not done.

Paired-no-event has identical outcomes across all four conditions: route-a,
197 ticks, 4.945465 m, one inspection, no replans or unavailable cues. Its first
commitment is tick 727; it has no event or post-event samples.

[Results metadata](memory-decision-pilot-v2-evidence/results.json) retains every
owner's exact ticks, goal, path, inspection/replan/unavailable counts, commitment
and sample ticks, bypasses, outcome and failure disposition, plus all six pair
predicates. Complete independent audits are retained separately. There are no
incomplete or unattempted slots, retries or hidden failed conditions.

## Preserved and portable evidence

An independent post-exit **byte-only** check found 0 errors: all 1,151 protected
files across 18 roots (4,400,592,526 bytes) retain exact paths, sizes and hashes,
with no additions. The new native-output tree has exactly 725 files
(2,766,687,296 bytes): 723 indexed artifacts plus execution and close. Its canonical
inventory hash is
`c5f531a808fd9a563dcbc37131ad423e40bfc935ed28677257b0900f59364675`.
See [integrity receipt](memory-decision-pilot-v2-evidence/post-exit-integrity.json).
The legacy prerequisite result with 67 differing native bytes remains failed;
its timer-aware candidate result remains distinct and unchanged.

Authoritative documents are copied byte-for-byte into the publication directory:

- [Execution](memory-decision-pilot-v2-evidence/execution.json):
  `6eb2da1c07a54ed2a1cdabfd7324ee7d19241c437cd72dc8b766a5b860ed0724`.
- [Independent close](memory-decision-pilot-v2-evidence/scientific-close.json):
  `ca92aaf06a964ec26daf651ff9203fa313039179a3840b66e107a2977699102d`.
- [Preparation tool receipt](memory-decision-pilot-v2-evidence/preparation-result.json)
  and [invocation/cleanup receipt](memory-decision-pilot-v2-evidence/invocation-result.json).
- [Publication anchors and resource receipt](memory-decision-pilot-v2-evidence/publication.json)
  and [per-file index](memory-decision-pilot-v2-evidence/publication-index.json).

The portable ZIP contains unchanged non-NPZ output, control and frozen publication
inputs, including opaque SNP bytes, jobs, logs, complete audits and raw event
streams. **390 NPZ recording chunks (2,616,936,288 bytes) remain local**, indexed
by exact path, size and SHA-256; they were not duplicated into Git. This documentary
bundle allows byte/metadata inspection but is not a complete portable camera/raw
scientific replay package without those original chunks. Archive membership is
frozen before ZIP/index creation, so final anchor/readback receipts are external
to the archive and documented rather than recursively included.

Run this byte-only verification from a fresh checkout, without project imports,
physics, SNP/NPZ decoding or scientific re-scoring:

```sh
python - <<'PY'
from pathlib import Path
import hashlib, json, zipfile
p = Path('docs/reports/memory-decision-pilot-v2-evidence')
a = json.loads((p/'publication.json').read_text())
for row in a['anchors']:
    data = (p/row['path']).read_bytes()
    assert len(data) == row['bytes']
    assert hashlib.sha256(data).hexdigest() == row['sha256']
index = json.loads((p/'publication-index.json').read_text())
members = {r['archive_member']: r for r in index['files'] if r['archive_member']}
with zipfile.ZipFile(p/a['archive']['path']) as z:
    assert z.testzip() is None
    assert len(z.infolist()) == len(members) and set(z.namelist()) == set(members)
    for name, row in members.items():
        data = z.read(name)
        assert len(data) == row['bytes']
        assert hashlib.sha256(data).hexdigest() == row['sha256']
print('Publication anchors, ZIP CRCs, membership and every entry SHA verified')
PY
```

Post-exit work consists of byte packaging, integrity checks, prose and Git
publication only. The original raw-output/control roots and every protected input
remain untouched. Archive readback does not replace original independent close.

## Decision and remaining project work

The pilot establishes audited exploratory route/cost differences on these fixed
change scenes and a reproducible natural null-case task failure. The complete
pilot's absent frozen composite mechanism is a valid negative result. The six
variants are correlated development cases: matching south/north outcomes across
cue regimes are not independent replications. No confidence interval, population
effect, held-out benefit, biological learning or physical claim follows.

The next scientific decision is prospective: choose how a future study should
measure failure-aware null cost, and whether the declared visibility/task behavior
needs a separately bounded diagnostic. The current report cannot establish why
the selected exit bearing became unavailable beyond its audited terminal reason.
Any changed metric or scientific source requires a new versioned protocol and
approved finite allocation. The current two failed arms remain failed; no rescue
study, additional owner, decoder/comparator pass or new analysis was executed.

The full nine-condition matched-control memory development and held-out study
has not run. Memory/R2 remains false, qualification claims remain empty, and
held-out data remains unused. Learned puck and MaleCNS navigation capability,
adequate Afterimage and the complete artwork experience, browser acceptance,
human artistic/operator acceptance and final installation/evidence handoff remain
open in the [simulation-first completion goal](../plans/simulation-first-completion-goal.md).
This allocation authorizes no CI work, merge or physical rover/artwork activity.
