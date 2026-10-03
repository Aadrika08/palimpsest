# Six-mode offline handoff: bounded proposal

Status: root approved the source implementation scope; fixed manifest, driver and
focused fixture check implemented. No actual input copies or curated exports have
been created. Base `cfab86b20db95e1b1bf7ab2673dad8b96b4f06c0`, isolated
`feat/artwork-handoff`. This is an **agent-operated, one-pass export smoke** for
M9/M10 handoff, with no independent-operator, exhibition-duration or R5 qualification.
No new inference, camera capture, native simulation, browser, audio playback,
training, network transfer or input modification is proposed.

## Curated inputs and portability

Use two completed, four-tick CPU FLYNN branch recordings, their unchanged coincident
routes, and the completed eight-frame Afterimage recording. Reuse the left FLYNN
recording for both the simulated Borrowed Body route and the choir. The graph and
anatomical pair already have committed sources and actual offline/browser evidence.
The chosen choir lasts **0.08 s**, and Afterimage covers **0.16 model seconds / 0.5
source seconds**. No looping, time stretching, autoscaling or invented activity.

The proposed portable folder has exactly **19 files / 4,852,480 bytes**. Paths below
are relative to that folder. UUID basenames and every source byte remain unchanged.
The one source manifest will contain these relative paths, byte counts and hashes;
original producer paths/identities are separate descriptive provenance, never paths
the portable driver follows. Reject missing/extra files, symlinks, path traversal,
wrong lengths/hashes and output/source overlap before any CLI call. No credentials
or tokens were observed in the selected provenance; existing export secret-field
checks remain active. Do not rewrite historical local paths inside original records.

Local origin prefixes, relative to `/home/utkarsh/Work/shraddha/brain/.worktrees/`:

- `F`: `lab-hardening/runs/m3-offline-full-20261002/full-flynn/runs/`
- `A`: `artwork-afterimage/runs/afterimage-geometric-v1-20261002/`
- `R`: this checkout at the pinned base. Graph, specimens, notices and manifests are tracked.

| Portable path | Original source | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `runs/90323804f1e94f13ad710d561f557590/recording/manifest.json` | `F` + UUID/path | 3096 | `a11e1ee9c83a9fd3b6ec425d15ae3b527ad73f6639f8b0beea1bb6f85c173f2f` |
| `runs/90323804f1e94f13ad710d561f557590/recording/events.jsonl` | `F` + UUID/path | 19293 | `509a36c20c994090d97e9bf42317d1b66de76cdc784043950e7c6fdf32874a1a` |
| `runs/90323804f1e94f13ad710d561f557590/recording/chunks/000000.npz` | `F` + UUID/path | 868906 | `fc06e4de218795b01f86abecdc1290770d2b3f952b01566f153f9a63af1bdd6b` |
| `runs/b1012576189c4385be6eee4180a2e99c/recording/manifest.json` | `F` + UUID/path | 3096 | `7db030ba55db33c6fcf441529b7d59d7ebc7aaa19ac666216e20c61f28f527ca` |
| `runs/b1012576189c4385be6eee4180a2e99c/recording/events.jsonl` | `F` + UUID/path | 19730 | `3a2cdc016089a589b12a8c27806793ede3e90dc862a24e9ee8169dbb30d8a6c7` |
| `runs/b1012576189c4385be6eee4180a2e99c/recording/chunks/000000.npz` | `F` + UUID/path | 868906 | `d8760cc8c36a714dcdeb105cff286f82451410cc36b8a036ea1676b12ef5b1c6` |
| `runs/98bfc18865194759987879b7444f48b1/recording/manifest.json` | `A` + UUID/path | 4135 | `aac8da5e82573f93dc907c8d274d1b114bc34550aedc38c58ae6495780af535a` |
| `runs/98bfc18865194759987879b7444f48b1/recording/events.jsonl` | `A` + UUID/path | 703 | `c9b65d09d05effeb47239d7eeea3cfb27bd2e3cd8ef3e36caafc4166e068d537` |
| `runs/98bfc18865194759987879b7444f48b1/recording/chunks/000000.npz` | `A` + UUID/path | 793908 | `07ea5ca341b8f77f6567aff45527010a744d4c0547b9ca0f1faed2ae4acd61a9` |
| `runs/98bfc18865194759987879b7444f48b1/supervisor.json` | `A` + UUID/path | 339 | `16496feb4b3b340dadcfb456913a6318afd6eecce0e61544111b42d44a071f5b` |
| `stimulus/afterimage/stimulus.json` | `A/stimulus/stimulus.json` | 767 | `bbed979ac3e8bcd8adeb9edb0ee5a64892c004e3236b53076f5b64926469276f` |
| `stimulus/afterimage/frames.npy` | `A/stimulus/frames.npy` | 393344 | `b5c4dbb082d50f0bec73225fb7529e24e0a410250b3fd92cbe52cc5b91b222e1` |
| `graph/source-graph.json` | `R/data/assets/flynn/male-reduced-v1/source-graph.json` | 101560 | `5aba0fef99afba666b88e40fc535091454e46d9330580d9280b203e8da0abac0` |
| `graph/extraction.json` | `R/data/manifests/malecns-reduced-neighborhood-v1.json` | 5364 | `7a205342b4ada8ab8b78d6ca866c61735003e601531c65a1c1b6c819df00026f` |
| `specimens/pair.json` | `R/data/assets/specimens/dnge104-v1/pair.json` | 2374 | `4651c8d7f0e891e059b8b21fb74369088c4b454b78a7e0981fc4b85967248f68` |
| `specimens/male-12781.swc` | `R/data/assets/specimens/dnge104-v1/male-12781.swc` | 552929 | `84f14c2f8b98da664db2c322c6f3f47f83b61c412207bddfa67e2315b86fc699` |
| `specimens/female-720575940640723315.swc` | `R/data/assets/specimens/dnge104-v1/female-720575940640723315.swc` | 1202717 | `999ab8934af1b912a6dc5d9f411913b264cb1f49dc6c9512f7cf2f15bda2847a` |
| `specimens/provenance.json` | `R/data/assets/specimens/dnge104-v1/provenance.json` | 4632 | `c2e507891165f92d0681b5e3960dedf49912f4b913cf95f2658b13b4cec9e765` |
| `THIRD_PARTY_NOTICES.md` | `R/THIRD_PARTY_NOTICES.md` | 6681 | `436aa6169cfda0e793f3742e3c8642ba21d7038bf0413a2f9cfad2c92a24f280` |

The recording subsets alone are 10 files / **2,582,112 bytes**: left 891,295;
right 891,732; Afterimage 799,085. Both FLYNN copies retain **every numeric chunk and
event**, including neural telemetry, cameras, source IDs and parent hash references.
Afterimage additionally requires its completed `supervisor.json`; source stimulus
and frames are included for direct inspection although rendering only requires the
recorded copies and embedded stimulus metadata. Its declared creator is
`scripts/verify_afterimage.py`: authored nonhuman geometry, not a visitor image.
That rights declaration remains an operator statement, not independently verified
consent or newly granted redistribution rights.

Full original run directories are respectively 8 files / 2,065,473 bytes;
8 / 2,066,252; and 8 / 799,695. **Do not copy them wholesale.** Native snapshots,
snapshot index, process/log/result files, parent runs, checkpoints, retina weights
and upstream code are not required by these exporters. Their original evidence
stays intact. Label each copied run a **derivative source subset, not a restorable
run bundle**: native continuation, action/policy replay and source-lineage
re-execution are unsupported. Parent identifiers remain historical references,
not a claim that their referenced snapshots are present or newly certified.

Portability is an explicit local folder handoff plus this repository revision and
Python 3.11 / NumPy 2.2.5 (existing locked environment; no new dependencies).
Only the plan, source manifest, driver and check are candidates for Git; no ignored
raw records/checkpoints are silently added. After approval, make byte-preserving,
exclusive local copies of this allowlist; the driver consumes an explicitly
supplied relocated folder, with no fallback to these machine-specific origins and
no download/archive extractor. A fresh clone still needs this declared source
folder and cached Python/NumPy. No model assets or initialized upstream submodule
are needed for the six export paths. Preserve the bundled separate MaleCNS CC BY
and FlyWire CC BY-NC notices without inventing a licence for new project work.

## Exactly six existing commands

`REPO` is the source checkout; `INPUT` is the relocated curated folder; `OUT` is a
new empty directory outside `INPUT` and all asset paths. `PY` is the Python
interpreter. Commands below are Bash arrays for exact quoting; the driver will
store and invoke equivalent argument lists, without a shell. All outputs share
one managed destination. CLI writer leases are acquired sequentially by the
existing commands; the driver must not hold an outer writer lease.

```bash
export PYTHONPATH="$REPO/src"
cmd=("$PY" -m palimpsest --repo "$REPO")
limits=(--storage-max-bytes 67108864 --min-free-bytes 1073741824 --max-exports 6 --log-max-bytes 262144)
left="$INPUT/runs/90323804f1e94f13ad710d561f557590"
right="$INPUT/runs/b1012576189c4385be6eee4180a2e99c"
portrait="$INPUT/runs/98bfc18865194759987879b7444f48b1"

"${cmd[@]}" afterimage render "$portrait" --output "$OUT/afterimage.svg" "${limits[@]}"
"${cmd[@]}" export "$left" --format svg --output "$OUT/borrowed-body.svg" "${limits[@]}"
"${cmd[@]}" compare "$left" "$right" --output "$OUT/one-map-many-lives.html" "${limits[@]}"
"${cmd[@]}" sonify "$left" --population visual_left --population visual_right --population descending --episode 0 --output "$OUT/counterfactual-choir.wav" "${limits[@]}"
"${cmd[@]}" atlas --graph "$INPUT/graph/source-graph.json" --graph-manifest "$INPUT/graph/extraction.json" --cut-node 12781 --output "$OUT/atlas.svg" "${limits[@]}"
"${cmd[@]}" specimens "$INPUT/specimens/pair.json" --output "$OUT/space-between-two-flies.svg" "${limits[@]}"
```

Borrowed Body is explicitly a **recorded simulated route**, not pen marks or a
physical drawing. The two comparison traces may coincide and must both remain.
The choir is composed model telemetry, not biological audio. The atlas is structural
reachability, not inferred impaired behaviour. Specimens remain unregistered
anatomical panels with unequal coverage. Preserve current visible labels and all
embedded source/model/mask/U/parent/mapping metadata; do not add arbitrary artworks.

## Minimum driver, bounds and acceptance

The implementation adds `docs/artwork-handoff.json`,
`scripts/verify_artwork_handoff.py`, and `tests/test_artwork_handoff.py`. It reuses current
`artifacts._load`, Afterimage's recording reader, graph/pair validators, existing
CLI dispatch and `evaluate.bounded_process`; do not edit their implementations.
Prefer one supervised child making the six fixed CLI dispatches sequentially in
the same process, so there is one owned process group and no new scheduler or
per-mode supervisor tree. Record equivalent six CLI argument lists. Deny importing
Torch/MuJoCo in that child and assert neither loaded at completion.

Proposed ceilings: source folder **8 MiB / exactly 19 files**; six outputs plus
receipts/logs **64 MiB**; **1 GiB free-space floor**; one **120 s** bounded child for
input admission, all six commands, artifact/readback checks, input/source rehash and
worker receipt; **150 s** normal enclosing entry-through-drain/publication/return
acceptance. Use the existing bounded-process TERM/3 s KILL cleanup and retained
256 KiB stdout/stderr prefixes. Freeze the exact existing outer termination and
failure-cleanup invocation during controls review before any actual run; it must
terminate the complete driver and account for its owned child, not merely reject
late success. No additional supervisor implementation is in this product slice.
These are proposed finite caps, not measured throughput or exhibition duration.
Parent acceptance explicitly requires completed exit zero **and** the supervised
child's finite elapsed time within 120 s; a late zero exit is a failure.

Storage is **not an atomic 64 MiB quota**. The driver recounts before commands and
at finalization; each existing CLI separately preflights its complete payload.
The two log prefixes can grow by at most 512 KiB in total. Existing JSON publication
uses a temporary sibling and a 4 MiB per-payload cap, so its old and temporary
versions may coexist until replacement. These checks and bounded logs constrain
the admitted writer, but cannot reserve filesystem capacity against unrelated
writers or prove an instantaneous aggregate peak. The final retained inventory
must fit 64 MiB; exhaustion fails rather than deleting inputs or old evidence.
Separately reviewed outer controls must cover main-process termination/drain and
full 150 s normal invocation acceptance; the driver's own counter is not an
independent measurement of interpreter entry or completed process return.

All six rows exist as `not_started` at entry. First source/CLI/timeout/quota/readback
failure stops the pass; no retry or overwrite. Preserve completed outputs, logs,
failure and untouched rows; existing exporters alone remove their own partial
new artifact on write failure. Never delete the handoff folder or originals.
Pass requires six successful dispatches; parsed SVG/HTML/WAV labels and embedded
identities/counts agree with admitted inputs; both comparison identities and four
recorded ticks survive; choir is 3,840 PCM frames at 48 kHz; Afterimage retains all
eight points; atlas records 135 cut edges / 137 lost input–endpoint pairs; anatomy
retains 37,007 segments. Validate embedded metadata through existing readers or
stdlib XML/HTML/RIFF inspection, not screenshot assertions. Input/source hashes
must match before/after; exclusive outputs, time/storage limits, drained logs and
owned-process cleanup all pass. No new display/audio or perceptual quality claim.

The one meaningful check will stage real small completed-record fixtures in a
temporary relocated input folder, use actual input/hash/CLI-path construction and
exclusive publication, and prove one corruption causes failure before any export
and preserves the fixed remaining rows. Mock only command execution/supervision
for the control-flow portion; no global writer lease, native runtime or model.
Existing mode-level exporter tests already cover mapping mathematics. The actual
curated one-pass smoke remains a separate reviewed runtime-slot action.

## Single manifest and receipt shape

Use one small explicit JSON manifest, not a registry: version/id, exact source-file
allowlist `{path, size_bytes, sha256, original_source}`, three original run IDs,
six fixed command/output rows, limits, existing evidence references and blank
human declaration fields. Those fields can be `operator`, `custodian`,
`intended_audience`, `approved_sharing`, `retention_review_date`,
`disposition_record`; null means not supplied, never permission or expiry.
Keep original rights/licence text in the original files. No automatic sharing,
deletion, consent verification or independent-operator signature.

One receipt records `agent_operated: true`, `qualification_claims: []`, overall
operational status, manifest hash, runtime/source identity, source hashes/bytes
before and after, all six command rows with status/returncode/elapsed/output hashes,
per-output semantic checks, supervisor/log/cleanup references and declarations as
supplied. Record subprocess `elapsed_seconds` separately from enclosing elapsed;
do not call a prepublication timestamp complete process-return time. Do not index
an open log prefix as a final drained file. No duration-loop or generic session
declaration framework is needed.

The driver's source inventory is explicitly a **selected-file** inventory: the
offline CLI/readers/renderers, direct project helpers, this driver and manifests/
lock metadata. It is not a whole-source-tree or Python-library integrity claim.
The separately reviewed actual controls bind the full tracked source tree and
runtime identity independently; imported stdlib/NumPy implementation bytes are
not represented by the driver's selected-file hashes.

## Existing evidence and documentation correction

Source verification: `PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_artwork_handoff -v`
passed seven checks in 0.176 s without skips. Fixtures use one locally authored
completed record and mock command execution/supervision; a separate route readback
uses the existing pure SVG exporter without a CLI lease. Corruption, symlinks,
fixed command order, stop-on-first-failure, independent failure rehash, exclusive
destination, runtime-import refusal and late publication are covered. No external
raw recording or global writer lease is used. The initial missing-driver red and
missing failure-rehash result remain in local `runs/artwork-handoff-source-checks/`.
Root's follow-up child-bound check first reproduced acceptance of a completed
120.001 s receipt; the explicit elapsed guard then passed all seven checks in
0.250 s. Both `late-child-red.log` and `child-bound-fixed.log` are retained there.

Current passive read-only admission on this base completed in 0.296 s: both FLYNN
records through `artifacts._load` (left lineage also checked), completed Afterimage
through its reader, graph through `load_graph`, and pair through `load_pair`.
No Torch/MuJoCo import, export, copy, writer lease or simulator was involved.
That is source selection evidence, not the prospective relocated CLI smoke.

Historical sources: [Afterimage](../reports/m9-afterimage-validation.md),
[atlas](../reports/m9-atlas.json), [specimens](../reports/m9-specimens.md), and
[recorded choir/comparison/browser receipts](../artwork-mappings.md#recorded-comparison-browser-evidence).
The existing comparison/choir reports pin the exact chosen branch and null-route
pair; their historical producer identities must stay separate from the new exporter
revision. Keep all prior failures/evidence untouched.

After approval, update only the handoff links in [the runbook](../exhibition-runbook.md)
and narrow consistency wording in [mappings](../artwork-mappings.md): initial
source-slice/browser-pending statements at lines 167–169 and 181–185 describe their
historical stage; later desktop/mobile/keyboard/print browser evidence passed at
lines 191–195. Screen-reader validation, independent operation, perceptual quality,
full declared exhibition duration and physical work remain open. Root-owned
README, progress, requirements and integration status documents remain untouched.
