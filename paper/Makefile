PYTHON ?= python3
PDFLATEX ?= pdflatex
BIBTEX ?= bibtex
BUILD := build
PDF := $(BUILD)/palimpsest-systems-paper.pdf

.PHONY: all evidence paper verify clean

all: paper

evidence:
	$(PYTHON) scripts/build_evidence.py

paper: authority-evidence
	mkdir -p $(BUILD)
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) main.tex
	cp references.bib $(BUILD)/references.bib
	cd $(BUILD) && $(BIBTEX) main
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) main.tex
	$(PDFLATEX) -interaction=nonstopmode -halt-on-error -output-directory=$(BUILD) main.tex
	cp $(BUILD)/main.pdf $(PDF)

verify: paper
	$(PYTHON) -B scripts/build_authority_evidence.py $(AUTHORITY_ARGS) --check
	$(PYTHON) scripts/verify_paper.py --write

clean:
	rm -f $(BUILD)/main.aux $(BUILD)/main.bbl $(BUILD)/main.blg \
		$(BUILD)/main.log $(BUILD)/main.out $(BUILD)/main.pdf $(BUILD)/main.toc

# Frozen authority/replay campaign inputs. Generation never launches study jobs.
AUTHORITY_EVIDENCE ?= evidence/authority-replay-v1
AUTHORITY_PROTOCOL ?= studies/authority_replay_v1/protocol.json
AUTHORITY_TRACE_ROOT ?= $(AUTHORITY_EVIDENCE)/fault-traces
AUTHORITY_ARGS = --summary $(AUTHORITY_EVIDENCE)/summary.json --manifest $(AUTHORITY_EVIDENCE)/campaign-manifest.json --protocol $(AUTHORITY_PROTOCOL) --trace-root $(AUTHORITY_TRACE_ROOT) --output generated

.PHONY: authority-evidence authority-evidence-check

authority-evidence:
	$(PYTHON) -B scripts/build_authority_evidence.py $(AUTHORITY_ARGS)

authority-evidence-check:
	$(PYTHON) -B scripts/build_authority_evidence.py $(AUTHORITY_ARGS) --check
