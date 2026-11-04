#!/usr/bin/env python3
"""Verify the rendered paper and write a deterministic evidence record."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


LOG_FAILURES = {
    "undefined citations": "LaTeX log contains undefined citations",
    "undefined references": "LaTeX log contains undefined references",
    "LaTeX Error": "LaTeX log contains errors",
    "Overfull \\hbox": "LaTeX log contains overfull boxes",
    "Overfull \\vbox": "LaTeX log contains overfull boxes",
}


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _run(*command: str) -> str:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return result.stdout


def inspect_paper(
    repo: Path,
    pdf: Path,
    log: Path,
    source_inputs: list[Path],
    generated_outputs: list[Path],
    expected_text: list[str],
    minimum_pages: int,
) -> tuple[list[str], dict[str, object]]:
    del repo  # Kept in the interface for future repository-relative checks.
    errors: list[str] = []
    if not pdf.is_file():
        return ["missing PDF"], {}
    if not log.is_file():
        errors.append("missing LaTeX log")
        log_text = ""
    else:
        log_text = log.read_text(encoding="utf-8", errors="replace")
    for marker, message in LOG_FAILURES.items():
        if marker.casefold() in log_text.casefold() and message not in errors:
            errors.append(message)

    for generated in generated_outputs:
        if not generated.is_file():
            errors.append(f"missing generated output: {generated.name}")
            continue
        for source in source_inputs:
            if source.is_file() and source.stat().st_mtime_ns > generated.stat().st_mtime_ns:
                errors.append(
                    f"stale generated output: {generated.name} is older than {source.name}"
                )
                break

    try:
        info = _run("pdfinfo", str(pdf))
        text = _run("pdftotext", str(pdf), "-")
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"PDF inspection failed: {exc}")
        return errors, {}

    match = re.search(r"^Pages:\s+(\d+)\s*$", info, re.MULTILINE)
    page_count = int(match.group(1)) if match else 0
    if page_count < minimum_pages:
        errors.append(f"page count {page_count} is below minimum {minimum_pages}")
    for expected in expected_text:
        if expected not in text:
            errors.append(f"PDF missing expected text: {expected}")

    metadata: dict[str, object] = {
        "schema_version": 1,
        "pdf_sha256": _sha256(pdf),
        "pdf_bytes": pdf.stat().st_size,
        "page_count": page_count,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text_characters": len(text),
        "expected_text": expected_text,
        "checks": {
            "latex_log_clean": not any(message.startswith("LaTeX log") for message in errors),
            "generated_outputs_fresh": not any("generated output" in error for error in errors),
            "minimum_page_count": page_count >= minimum_pages,
            "expected_text_present": not any("missing expected text" in error for error in errors),
        },
    }
    return errors, metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    paper = repo / "paper"
    pdf = paper / "build" / "palimpsest-systems-paper.pdf"
    log = paper / "build" / "main.log"
    sources = [paper / "evidence" / "claims.yaml"]
    generated = [paper / "generated" / "claims.tex", paper / "generated" / "results-table.tex"]
    expected = [
        "Introduction",
        "System Design",
        "Evidence Protocol",
        "Evaluation",
        "Limitations and Threats to Validity",
        "Ethics, Licensing, and Artifact Status",
        "Conclusion",
        "References",
    ]
    errors, metadata = inspect_paper(repo, pdf, log, sources, generated, expected, 5)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    metadata["source_commit"] = _run("git", "-C", str(repo), "rev-parse", "HEAD").strip()
    status = _run("git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no").strip()
    metadata["dirty_state_note"] = "tracked changes present during verification" if status else "tracked worktree clean"
    metadata["compiler_version"] = _run("pdflatex", "--version").splitlines()[0]
    metadata["poppler_pdfinfo_version"] = subprocess.run(
        ["pdfinfo", "-v"], text=True, capture_output=True, check=True
    ).stderr.splitlines()[0]
    if args.write:
        output = paper / "build" / "verification.json"
        output.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
