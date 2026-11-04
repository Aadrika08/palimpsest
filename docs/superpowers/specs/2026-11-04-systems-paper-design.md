# Palimpsest Systems Paper Design

## Intent

Produce a venue-neutral systems/reproducibility paper that presents Palimpsest as
an inspectable experimental instrument for embodied neural controllers. The paper
must be useful to researchers who need to intervene on, branch, replay, compare,
and audit controller experiments without confusing operational checks with
scientific capability.

The paper is not a completion report for every Palimpsest milestone. It converts
the strongest already-verified contribution into a focused manuscript and leaves
failed or unopened scientific gates explicit.

## Audience and success

The primary audience is researchers building embodied neural-controller or
connectome-constrained simulation experiments. Success means:

- a reviewer can state the contribution in one sentence;
- every quantitative claim resolves to a retained repository source and exact
  source revision or historical scope;
- the paper distinguishes fixture, browser, runtime, development, held-out,
  human, and physical evidence;
- a clean checkout can regenerate the manuscript tables and compile the PDF;
- unresolved licensing, author, archival, and independent-reproduction work is
  visible in a submission checklist rather than silently filled in.

## Central claim

Palimpsest adds an inspectable and provenance-preserving experiment layer around
embodied neural controllers: declared observation boundaries, full-state
snapshots, validated interventions, sequential branches, distinct playback,
action-replay and policy-replay modes, bounded artifact publication, and retained
failure evidence.

The paper may claim that these mechanisms were implemented and verified in their
reported scopes. It may not claim that memory improves behavior, connectome
topology improves navigation, learned puck manipulation succeeds, artwork has
human acceptance, or a physical rover is qualified.

## Contributions

1. An architecture that separates authoritative simulation state, controller
   inputs, UI presentation, and recorded evidence.
2. A branch/replay protocol that distinguishes playback, recorded-action replay,
   and live policy recomputation under explicit compatibility checks.
3. Implemented evidence-custody, recording, replay, and export mechanisms that
   retain source identity and failure outcomes. The prospective memory-case
   publication contract is design/future work until its implementation and
   actual qualification are complete.
4. A case-based evaluation spanning upstream FLYNN parity, intervention and
   continuation, mixed-workload endurance, browser operation, and negative
   capability results without converting them into positive claims.

## Paper shape

The manuscript will use a conventional systems-paper structure:

1. Abstract
2. Introduction
3. Related work
4. System design
5. Evidence and experiment protocol
6. Evaluation
7. Case studies and negative results
8. Limitations, ethics, and licensing
9. Conclusion

Four primary figures are planned:

- architecture and authority boundaries;
- intervention, snapshot, branch, replay, and publication lifecycle;
- evidence-scope ladder from fixture to physical/human acceptance;
- quantitative results summary (parity, development outcomes, endurance, and
  known failed gates).

## Evidence policy

- `paper/evidence/claims.yaml` is the paper's claim ledger. Each entry names its
  scope, status, source file, source hash, source lines or machine-readable JSON
  pointer, source revision, experimental unit, evidence class, and permitted
  wording. Superseded claims identify their successor.
- `paper/scripts/build_evidence.py` validates the ledger and generates LaTeX
  tables/macros under `paper/generated/`.
- Generated values must come from committed reports or compact machine-readable
  indexes. Historical raw runs may be cited by their retained hashes without
  being copied into Git.
- Missing, hash-drifted, duplicate-active, or contradictory evidence fails
  generation. Markdown evidence requires both a full-file hash and an anchor;
  machine-readable JSON pointers are preferred where committed indexes exist.
  No generator may mutate existing reports or raw results.
- Development episodes, ticks, intervals, seeds, and repeated measurements are
  not automatically independent samples. The manuscript will identify the
  experimental unit for each result.

## Artifact and build

- Source format: LaTeX with a small local style surface and BibTeX references.
- Build entry point: `paper/Makefile` with `make -C paper evidence`, `paper`, and
  `verify` targets.
- Preferred compiler: `latexmk` plus `pdflatex`; if unavailable, the build must
  report the exact missing dependency and leave the generated manuscript sources
  verifiable.
- Final PDF: `paper/build/palimpsest-systems-paper.pdf`.
- The PDF is rendered to page images and visually checked for clipping, broken
  references, illegible figures, and malformed tables.
- Commit the ledger, generator, manuscript, generated LaTeX, final PDF, and
  verification JSON. Ignore rendered page PNGs and LaTeX intermediate files.

## Submission blockers

The package must include an explicit checklist for items that cannot be decided
from repository evidence:

- final author order, affiliations, and corresponding author;
- venue and formatting template;
- root project-code licence and newly trained parameter licence;
- DOI/archive deposit and public readback;
- independent clean-machine reproduction;
- any disclosure required for tool-assisted authoring.

These blockers do not prevent creation of a complete draft, but they prevent the
package from being labelled submitted or camera-ready.

## Non-goals and anti-goals

- Do not launch new memory, navigation, puck, artwork, human, or hardware studies.
- Do not reopen consumed allocations or held-out sets.
- Do not copy the entire local `runs/` tree into the paper package.
- Do not infer biological validity from graph compatibility or simulator parity.
- Do not use passing fixtures as evidence of runtime or scientific qualification.
- Do not hide null results, failed thresholds, skips, or provenance limitations.
- Do not invent authors, permissions, licences, acceptance records, or DOI values.

## Builder decisions

The builder may choose typography, diagram layout, and prose transitions. The
builder may shorten the manuscript to fit a later venue, but must preserve the
claim ledger, limitation statements, and generated quantitative values. New
experiments or materially stronger claims require a new approved protocol.
