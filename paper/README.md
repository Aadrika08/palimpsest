# Authority-aware replay manuscript

The venue-neutral paper is `main.tex`. It replaces the historical feature and
capability inventory with one semantic-contract argument and RQ1–RQ4. The
venue-neutral layout includes the evaluation tables, three figures and references;
a submission venue determines the final template and length.

The execution study is `studies/authority_replay_v1/`. Its predeclared protocol
was committed and then frozen before the result-producing campaign. This is not
an independent public preregistration. Fixed seeds are engineering repeatability
units, and seed 0 was used in disclosed harness-development smoke checks; they
are not held out.

## Build and evidence binding

Build from the repository root using the locked lab dependencies, TeX Live
(`pdflatex` and `bibtex`), and Poppler (`pdfinfo` and `pdftotext`):

```sh
uv sync --locked --extra simulation --extra lab
make -C paper verify PYTHON="$(pwd)/.venv/bin/python"
```

`make -C paper paper` builds the PDF without writing verification metadata.
The build reads retained evidence and never launches experiments. This host's
prepared interpreter is `/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python`.
See `ARTIFACT.md` for execution identities, retained attempts and post-run audits.

The manuscript consumes only these focused generated inputs:

- `generated/authority-claims.tex`
- `generated/fault-matrix.tex`
- `generated/replay-table.tex`
- `generated/overhead-table.tex`
- `generated/operation-table.tex`
- `generated/overhead-plot.tex`
- `generated/snapshot-ablation.tex`

Generation refuses missing or inconsistent evidence. The historical
`claims.tex`, development smoke measurements and expected fault responses do not
supply results. Verification checks exact generation, input hashes, citations,
overflow, missing sections and unresolved placeholders. Every final PDF page
also requires visual inspection.

The two static figures are vector TikZ/table sources. Authority ticks are
symbolic, and the replay matrix describes this system's execution/validation
semantics. Neither is a measured performance plot or a competitor comparison.
`make -C paper figures PYTHON="$(pwd)/.venv/bin/python"` also exports all three
figures as standalone vector PDFs under `paper/build/figures/`.
