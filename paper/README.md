# Palimpsest systems paper

This directory contains the venue-neutral paper draft and its evidence-bound
build. The manuscript presents Palimpsest as an inspectable experiment layer; it
does not claim successful memory transfer, connectome-topology advantage, learned
puck manipulation, human artistic acceptance, or physical deployment.

## Build

From the repository root:

```sh
make -C paper evidence PYTHON=.venv/bin/python
make -C paper paper PYTHON=.venv/bin/python
make -C paper verify PYTHON=.venv/bin/python
```

In a linked worktree, point `PYTHON` at the prepared repository environment or
use a Python 3.11+ interpreter; the paper scripts use only the standard library.
The deterministic fallback compiler sequence is `pdflatex`, `bibtex`,
`pdflatex`, `pdflatex`.

The final PDF is written to `paper/build/palimpsest-systems-paper.pdf`.
Quantitative inputs in `paper/generated/` are produced from
`paper/evidence/claims.yaml`; edit the ledger or source evidence, never generated
LaTeX directly.
