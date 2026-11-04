PYTHON ?= python3
PDFLATEX ?= pdflatex
BIBTEX ?= bibtex
BUILD := build
PDF := $(BUILD)/palimpsest-systems-paper.pdf

.PHONY: all evidence paper verify clean

all: paper

evidence:
	$(PYTHON) scripts/build_evidence.py

paper: evidence
	mkdir -p $(BUILD)
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) main.tex
	cp references.bib $(BUILD)/references.bib
	cd $(BUILD) && $(BIBTEX) main
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) main.tex
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) main.tex
	cp $(BUILD)/main.pdf $(PDF)

verify: paper
	$(PYTHON) scripts/build_evidence.py --check
	$(PYTHON) scripts/verify_paper.py --write

clean:
	rm -f $(BUILD)/main.aux $(BUILD)/main.bbl $(BUILD)/main.blg \
		$(BUILD)/main.log $(BUILD)/main.out $(BUILD)/main.pdf $(BUILD)/main.toc
