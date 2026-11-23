# AAAI-27 W23 build. Needs aaai2027.{sty,bst} from https://aaai.org/authorkit27/ (not committed).
.PHONY: pdf
pdf:
	mkdir -p build
	TEXINPUTS=..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build aaai27-w23.tex
	cd build && BIBINPUTS=..:: BSTINPUTS=..:: bibtex aaai27-w23
	TEXINPUTS=..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build aaai27-w23.tex
	TEXINPUTS=..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build aaai27-w23.tex

# Anonymized source bundle for upload: only files the draft loads, full-line TeX comments stripped
# (they carry repo paths, project name and commit hashes), project/commit macros dropped, then a leak check.
# Output: build/anon-src.zip
GEN = authority-claims audit-affordability male-v4-development fault-matrix replay-table snapshot-ablation overhead-table overhead-plot operation-table
FIG = authority-sequence replay-matrix
.PHONY: anon
anon:
	mkdir -p build/anon-src/generated build/anon-src/figures build/anon-aux
	for n in $(GEN); do grep -v '^[[:space:]]*%' ../generated/$$n.tex | grep -vE 'newcommand\{.(StudyCommit|ProtocolHash)\}' > build/anon-src/generated/$$n.tex; done
	for n in $(FIG); do grep -v '^[[:space:]]*%' ../figures/$$n.tex > build/anon-src/figures/$$n.tex; done
	grep -v '^[[:space:]]*%' aaai27-w23.tex > build/anon-src/aaai27-w23.tex
	cp references.bib build/anon-src/
	cd build && ! grep -rniE 'palimpsest|aadrika|utkarsh|maurya|shraddha|volnlabs|claude|anthropic|worktree|@[a-z0-9.-]+\.[a-z]|[0-9a-f]{40}|[0-9a-f]{64}|/home/|github\.com/(Aadrika|pro-)' $(addprefix anon-src/generated/,$(addsuffix .tex,$(GEN))) $(addprefix anon-src/figures/,$(addsuffix .tex,$(FIG))) anon-src/aaai27-w23.tex anon-src/references.bib
	cd build/anon-src && TEXINPUTS=../..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../anon-aux aaai27-w23.tex >/dev/null
	cd build/anon-aux && BIBINPUTS=../anon-src:: BSTINPUTS=../..:: bibtex aaai27-w23 >/dev/null
	cd build/anon-src && for i in 1 2; do TEXINPUTS=../..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../anon-aux aaai27-w23.tex >/dev/null; done
	! grep -E 'undefined' build/anon-aux/aaai27-w23.log && grep -q bibitem build/anon-aux/aaai27-w23.bbl && echo anon-src builds with references
	cd build && ! pdftotext anon-aux/aaai27-w23.pdf - | grep -iE 'palimpsest|aadrika|utkarsh|maurya|shraddha|claude|anthropic'
	cd build && zip -qFS anon-src.zip $(addprefix anon-src/generated/,$(addsuffix .tex,$(GEN))) $(addprefix anon-src/figures/,$(addsuffix .tex,$(FIG))) anon-src/aaai27-w23.tex anon-src/references.bib
