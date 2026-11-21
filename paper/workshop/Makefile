# AAAI-27 W23 build. Needs aaai2027.{sty,bst} from https://aaai.org/authorkit27/ (not committed).
.PHONY: pdf
pdf:
	mkdir -p build
	TEXINPUTS=..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build aaai27-w23.tex
	cd build && BIBINPUTS=..:: BSTINPUTS=..:: bibtex aaai27-w23
	TEXINPUTS=..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build aaai27-w23.tex
	TEXINPUTS=..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build aaai27-w23.tex

# Anonymized source bundle for upload: generated/figures with full-line TeX comments stripped
# (they carry repo paths, project name and commit hashes), then a leak check. Output: build/anon-src.zip
.PHONY: anon
anon:
	mkdir -p build/anon-src/generated build/anon-src/figures build/anon-aux
	for f in ../generated/*.tex; do grep -v '^[[:space:]]*%' $$f | grep -v 'newcommand{.StudyCommit}' > build/anon-src/generated/$$(basename $$f); done
	for f in ../figures/*.tex; do grep -v '^[[:space:]]*%' $$f > build/anon-src/figures/$$(basename $$f); done
	grep -v '^[[:space:]]*%' aaai27-w23.tex > build/anon-src/aaai27-w23.tex
	cp references.bib build/anon-src/
	! grep -rniE 'palimpsest|aadrika|utkarsh|maurya|shraddha|volnlabs|cc57edf|/home/|github\.com/(Aadrika|pro-)' build/anon-src
	cd build/anon-src && TEXINPUTS=../..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=../anon-aux aaai27-w23.tex >/dev/null && echo anon-src builds
	cd build && zip -qrFS anon-src.zip anon-src
