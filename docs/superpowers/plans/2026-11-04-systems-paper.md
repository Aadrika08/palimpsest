# Palimpsest Systems Paper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a venue-neutral, evidence-traceable Palimpsest systems-paper package and verified PDF without making unsupported scientific claims.

**Architecture:** A human-readable claim ledger is the source of truth for quantitative and scope claims. A small Python generator validates that ledger against committed evidence and emits LaTeX inputs; the manuscript consumes only those generated inputs for central results. A Makefile builds and verifies the package while preserving unresolved submission decisions in an explicit checklist.

**Tech Stack:** Python 3.11 standard library, YAML only if already available through the locked environment, LaTeX/BibTeX, Make, Poppler for render verification.

**Spec:** `docs/superpowers/specs/2026-11-04-systems-paper-design.md`

## Global Constraints

- Do not launch new scientific, human, artistic, or hardware studies.
- Do not modify existing reports, raw results, historical profiles, or qualification pins.
- Every central quantitative claim must resolve to a committed source and evidence class.
- Keep development, held-out, fixture, runtime, browser, human, and physical scopes distinct.
- Missing licences, author metadata, DOI, venue, or independent reproduction remain explicit blockers.
- Final output path is `paper/build/palimpsest-systems-paper.pdf`.

## Review Focus

- Missing evidence source: generation must fail with a claim identifier and absent path.
- Source wording drift: validation must reject a required evidence anchor that no longer occurs.
- Unsupported scope escalation: the ledger must reject unknown evidence classes and qualification wording inconsistent with the declared class.
- Stale generated files: verification must fail when ledger input is newer than generated outputs.
- Broken paper build: verification must detect missing PDF, unresolved references, missing citations, and empty pages.

---

### Task 1: Claim ledger and evidence generator

**Files:**
- Create: `paper/evidence/claims.yaml`
- Create: `paper/scripts/build_evidence.py`
- Create: `paper/tests/test_build_evidence.py`
- Create: `paper/generated/.gitkeep`

**Interfaces:**
- Consumes: committed Markdown/JSON evidence under `docs/` and repository Git identity.
- Produces: `load_claims(path: Path) -> list[Claim]`, `validate_claims(repo: Path, claims: list[Claim]) -> list[str]`, and generated `paper/generated/claims.tex` plus `paper/generated/results-table.tex`.

- [ ] Write generator tests for valid ledger generation, absent evidence paths, source-hash drift, missing anchors/JSON pointers, duplicate or contradictory active claims, invalid supersession, unknown evidence classes, prohibited capability wording, and deterministic output.
- [ ] Run `uv run --no-sync python -m unittest discover -s paper/tests -v` and confirm the new tests fail because the generator is absent.
- [ ] Implement the typed claim loader with `status`, `supersedes`, `source_sha256`, `experimental_unit`, and optional `json_pointer`; add validation rules, deterministic LaTeX escaping, and output generation using the Python standard library and JSON-compatible YAML syntax.
- [ ] Populate the ledger with historical experiment revisions and the parity, development, endurance, browser, memory, puck, and MaleCNS claims used by the manuscript; keep the paper-build head out of the ledger.
- [ ] Run the unit tests and `uv run --no-sync python paper/scripts/build_evidence.py --check` and require both to pass.

### Task 2: Manuscript, diagrams, and bibliography

**Files:**
- Create: `paper/main.tex`
- Create: `paper/references.bib`
- Create: `paper/figures/architecture.tex`
- Create: `paper/figures/lifecycle.tex`
- Create: `paper/figures/evidence-ladder.tex`
- Create: `paper/figures/results-summary.tex`
- Create: `paper/Makefile`
- Create: `paper/README.md`

**Interfaces:**
- Consumes: generated `claims.tex` and `results-table.tex` from Task 1.
- Produces: a self-contained venue-neutral manuscript and documented build commands.

- [ ] Draft the abstract and introduction around the approved central claim and contributions.
- [ ] Write related work using primary sources for FlyGym/NeuroMechFly, FLYNN/connectome-constrained controllers, replayable simulation, and reproducible computational experiments.
- [ ] Write system design and protocol sections that separate authority, observation, intervention, replay, custody, and evidence classes.
- [ ] Write evaluation and case-study sections using generated quantitative inputs; state experimental units and avoid statistical inference unsupported by the retained studies.
- [ ] Add limitations, ethics, licence status, negative results, and conclusion.
- [ ] Create four vector diagrams with only standard LaTeX/TikZ primitives or a dependency-free fallback.
- [ ] Add Make targets for evidence generation, PDF compilation, cleanup, and verification.

### Task 3: Submission and artifact package

**Files:**
- Create: `paper/SUBMISSION_CHECKLIST.md`
- Create: `paper/ARTIFACT.md`
- Create: `paper/CITATION.cff.template`
- Modify: `README.md`

**Interfaces:**
- Consumes: the paper build and repository evidence boundaries.
- Produces: an explicit human-decision checklist, reproduction instructions, citation template, and discoverable paper entry point.

- [ ] Record author, venue, licence, DOI, disclosure, and independent-reproduction blockers without inventing values.
- [ ] Document the minimal artifact, exact build commands, expected outputs, retained local-only evidence, and excluded 12 GB raw-run tree.
- [ ] Add a citation template with placeholders clearly marked as unresolved rather than installing it as final root metadata.
- [ ] Add a concise README link to the paper package and preserve existing project-status boundaries.
- [ ] Run a link/path audit over every file referenced by the paper package.

### Task 4: Build and visual verification

**Files:**
- Create: `paper/build/palimpsest-systems-paper.pdf`
- Create: `paper/build/verification.json`
- Create: `paper/build/rendered/` page images for inspection, excluded from Git if appropriate.
- Create: `paper/scripts/verify_paper.py`
- Create: `paper/tests/test_verify_paper.py`

**Interfaces:**
- Consumes: Tasks 1-3 and installed LaTeX/Poppler tools.
- Produces: rendered PDF plus machine-readable verification of page count, text presence, references, and artifact hashes.

- [ ] Write verifier tests for stale generated output, missing PDF, unresolved references/citations, missing expected text, invalid page count, and deterministic verification metadata; watch them fail before implementing the verifier.
- [ ] Implement `verify_paper.py` to inspect source/generated mtimes and hashes, LaTeX logs, `pdfinfo`, extracted PDF text, page count, expected sections, and output hashes.
- [ ] Run evidence generation and unit tests from a clean generated-output state.
- [ ] Compile with `pdflatex`, `bibtex`, `pdflatex`, `pdflatex`; use `latexmk` only when available and equivalent.
- [ ] Fail on LaTeX errors, undefined references/citations, overfull boxes that clip content, or missing expected sections.
- [ ] Render every PDF page to PNG and visually inspect layout, diagrams, tables, references, headers, and page numbering.
- [ ] Record PDF SHA-256, page count, compiler version, paper-build source commit, dirty-state note, and checks in `verification.json`.
- [ ] Run `make -C paper verify` as the terminal package check.

### Task 5: Final evidence review

**Files:**
- Modify: `paper/main.tex`
- Modify: `paper/evidence/claims.yaml`
- Modify: `paper/SUBMISSION_CHECKLIST.md`

**Interfaces:**
- Consumes: completed manuscript, generated files, PDF, and verification record.
- Produces: a reviewed draft whose claims do not exceed their evidence.

- [ ] Trace every abstract and conclusion sentence to the claim ledger or mark it as design description.
- [ ] Recheck denominators, units, seeds, repetitions, development/held-out labels, and independent-sample wording.
- [ ] Confirm failed and unopened gates are stated consistently with `docs/requirements-evidence.md` and `docs/plans/project-completion-2026-10-23.md`.
- [ ] Confirm current branch, remote, exact head, CI state, and PDF hash before reporting completion.
- [ ] Mark the goal complete only if no required build or evidence work remains; otherwise report the exact submission blockers separately from draft completion.
