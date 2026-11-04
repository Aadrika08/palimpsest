# Palimpsest systems paper artifact

## Scope

The minimal artifact supports the paper's systems/reproducibility claims:

- source and asset manifests;
- fixture tests and operating documentation;
- retained Markdown/JSON evidence indexes used by the paper;
- the hash-bound paper claim ledger and generator;
- LaTeX manuscript, bibliography and vector figures;
- final PDF and machine-readable verification record.

It does not package the full local `runs/` directory, downloaded restricted
assets, model-hosting credentials, held-out data, unfinished studies, or artwork
inputs whose public redistribution has not been approved.

## Build environment

- Python 3.11 or newer; paper scripts use only the standard library.
- GNU Make.
- TeX Live with `pdflatex`, `bibtex`, `tikz`, `booktabs`, `natbib`, `microtype`
  and `hyperref`.
- Poppler tools `pdfinfo`, `pdftotext` and `pdftoppm` for verification.

The project runtime itself remains pinned by `.python-version`, `uv.lock`, the
upstream gitlink and asset manifests. A paper build does not download or execute
the full controller assets.

## Reproduce the paper

From the repository root with the prepared environment:

```sh
make -C paper evidence PYTHON=.venv/bin/python
make -C paper paper PYTHON=.venv/bin/python
make -C paper verify PYTHON=.venv/bin/python
```

Expected retained outputs:

- `paper/generated/claims.tex`
- `paper/generated/results-table.tex`
- `paper/build/palimpsest-systems-paper.pdf`
- `paper/build/verification.json`

The evidence generator exits nonzero when a source path is absent, a complete
source-file hash changes, an anchor or JSON pointer does not resolve, active
claims conflict, supersession is invalid, or wording exceeds its evidence class.
Generated LaTeX must be byte-identical under `--check`.

## Evidence locations

The claim ledger references compact retained reports under `docs/reports/`.
Those reports bind historical source revisions, execution records, raw ledgers
and hashes. The largest raw-run tree is intentionally local: at the time of paper
construction, `runs/` was approximately 12 GiB. Copying it into Git would neither
grant redistribution rights nor provide a usable minimal artifact.

The paper uses these evidence categories:

| Category | What it supports | What it does not support |
| --- | --- | --- |
| Fixture | Source contracts and authored fault cases | Full model/runtime or scientific outcome |
| Runtime | Named simulator/controller execution | Browser usability, held-out inference or physical behavior |
| Browser | Named end-to-end UI session | Human artistic acceptance or cross-platform usability |
| Development | Frozen development protocol outcomes | Held-out generalization or population claims |
| Held-out | Only a prospectively protected evaluation | Biological validity without an appropriate study |
| Human/physical | Separate acceptance or deployment records | Nothing is promoted from simulation automatically |

## Local-only and third-party material

The FLYNN graph and checkpoint are distributed under terms recorded in
`THIRD_PARTY_NOTICES.md` and are not copied into this paper package. Raw runs may
contain derived arrays from those assets and require a licence review before
public deposit. The paper's compact tables report aggregate values and provenance
without redistributing those assets.

## Independent reproduction

Independent clean-machine reproduction has not yet been performed. The eventual
archive review must record:

1. archive checksum and exact commit;
2. OS, Python, TeX and Poppler versions;
3. evidence, build and verify command exits;
4. generated-file and final-PDF hashes;
5. any permitted deviations from the documented environment.

A successful local developer build is not a substitute for this gate.
