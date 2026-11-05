#!/usr/bin/env python3
"""Export the paper's three vector figures as standalone PDFs; no experiments."""
from pathlib import Path
import subprocess

PAPER = Path(__file__).resolve().parents[1]
HEADER = r"""\documentclass[10pt,border=2pt]{standalone}
\usepackage[T1]{fontenc}
\usepackage{lmodern,tikz,booktabs,array,tabularx,amsmath}
\usetikzlibrary{arrows.meta,positioning,fit,plotmarks}
\definecolor{palblue}{HTML}{245A7A}
\definecolor{palgreen}{HTML}{2D7B64}
\definecolor{palgold}{HTML}{B27A20}
\begin{document}
"""


def main():
    # Keep wrappers outside build/figures: TeX searches its output directory
    # first, so matching wrapper names there would shadow the source inputs.
    output = PAPER / 'build' / 'standalone-figures'
    output.mkdir(parents=True, exist_ok=True)
    bodies = {
        'authority-sequence': r'\input{figures/authority-sequence.tex}',
        'replay-matrix': r'\begin{minipage}{6.86in}\input{figures/replay-matrix.tex}\end{minipage}',
        'overhead-plot': r'\input{generated/overhead-plot.tex}',
    }
    for name, body in bodies.items():
        source = output / (name + '.tex')
        source.write_text(HEADER + body + '\n' + r'\end{document}' + '\n')
        result = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error',
                                 '-output-directory=' + str(output), str(source)],
                                cwd=PAPER, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stdout[-3000:] + result.stderr[-3000:])
        print(output / (name + '.pdf'))


if __name__ == '__main__':
    main()
