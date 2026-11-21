# AAAI-27 W23 build. Needs aaai2027.{sty,bst} from https://aaai.org/authorkit27/ (not committed).
.PHONY: pdf
pdf:
	mkdir -p build
	TEXINPUTS=..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build aaai27-w23.tex
	cd build && BIBINPUTS=..:: BSTINPUTS=..:: bibtex aaai27-w23
	TEXINPUTS=..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build aaai27-w23.tex
	TEXINPUTS=..:: BIBINPUTS=.:: pdflatex -interaction=nonstopmode -halt-on-error -output-directory=build aaai27-w23.tex
