#!/usr/bin/env python3
"""Validate the paper claim ledger and generate deterministic LaTeX inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EVIDENCE_CLASSES = {
    "fixture",
    "runtime",
    "browser",
    "development",
    "held_out",
    "human",
    "physical",
    "design",
}
PROHIBITED_BY_CLASS = {
    "fixture": ("scientifically qualified", "proves an advantage", "held-out"),
    "runtime": ("scientifically qualified", "proves an advantage"),
    "browser": ("scientifically qualified", "proves an advantage"),
    "development": ("scientifically qualified", "proves an advantage", "held-out success"),
    "design": ("implemented and qualified", "measured result"),
}


@dataclass(frozen=True)
class Claim:
    id: str
    claim_key: str
    title: str
    status: str
    supersedes: str | None
    source: str
    source_sha256: str
    anchor: str | None
    json_pointer: str | None
    expected_value: Any
    source_revision: str
    evidence_class: str
    experimental_unit: str
    value: str
    unit: str
    permitted_wording: str
    latex_macro: str
    table_group: str


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must start with '/'")
    current = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def load_claims(path: Path) -> list[Claim]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("claims"), list):
        raise ValueError("claim ledger must have schema_version 1 and a claims list")
    return [Claim(**entry) for entry in payload["claims"]]


def validate_claims(repo: Path, claims: list[Claim]) -> list[str]:
    errors: list[str] = []
    by_id: dict[str, Claim] = {}
    active_by_key: dict[str, Claim] = {}
    macro_owner: dict[str, str] = {}

    for claim in claims:
        if claim.id in by_id:
            errors.append(f"{claim.id}: duplicate claim id")
        by_id[claim.id] = claim
        if claim.status not in {"active", "superseded"}:
            errors.append(f"{claim.id}: unknown status {claim.status}")
        if claim.evidence_class not in EVIDENCE_CLASSES:
            errors.append(f"{claim.id}: unknown evidence class {claim.evidence_class}")
        if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", claim.latex_macro):
            errors.append(f"{claim.id}: invalid latex_macro {claim.latex_macro}")
        elif claim.latex_macro in macro_owner:
            errors.append(
                f"{claim.id}: duplicate latex_macro {claim.latex_macro} "
                f"(also {macro_owner[claim.latex_macro]})"
            )
        else:
            macro_owner[claim.latex_macro] = claim.id

        if claim.status == "active":
            prior = active_by_key.get(claim.claim_key)
            if prior and prior.value != claim.value:
                errors.append(
                    f"{claim.id}: conflicting active claim_key {claim.claim_key} "
                    f"with {prior.id}"
                )
            active_by_key[claim.claim_key] = claim

        source = repo / claim.source
        if not source.is_file():
            errors.append(f"{claim.id}: missing source {claim.source}")
            continue
        if _sha256(source) != claim.source_sha256:
            errors.append(f"{claim.id}: source hash mismatch for {claim.source}")
            continue
        if bool(claim.anchor) == bool(claim.json_pointer):
            errors.append(f"{claim.id}: exactly one of anchor or json_pointer is required")
        elif claim.anchor:
            if claim.anchor not in source.read_text(encoding="utf-8"):
                errors.append(f"{claim.id}: anchor not found")
        else:
            try:
                actual = _json_pointer(json.loads(source.read_text(encoding="utf-8")), claim.json_pointer or "")
            except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                errors.append(f"{claim.id}: invalid JSON pointer: {exc}")
            else:
                if actual != claim.expected_value:
                    errors.append(
                        f"{claim.id}: JSON pointer value mismatch: "
                        f"expected {claim.expected_value!r}, got {actual!r}"
                    )

        lowered = claim.permitted_wording.casefold()
        for phrase in PROHIBITED_BY_CLASS.get(claim.evidence_class, ()):
            if phrase in lowered:
                errors.append(
                    f"{claim.id}: prohibited wording {phrase!r} for {claim.evidence_class} evidence"
                )

    for claim in claims:
        if claim.supersedes:
            prior = by_id.get(claim.supersedes)
            if prior is None:
                errors.append(f"{claim.id}: supersedes unknown claim {claim.supersedes}")
            elif prior.status != "superseded":
                errors.append(
                    f"{claim.id}: superseded claim {claim.supersedes} must have status superseded"
                )
    return errors


def _latex(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def generate_outputs(repo: Path, claims: list[Claim], output_dir: Path) -> dict[str, str]:
    del repo  # Reserved for future machine-readable table inputs.
    active = sorted((claim for claim in claims if claim.status == "active"), key=lambda item: item.id)
    macros = ["% Generated by paper/scripts/build_evidence.py; do not edit."]
    for claim in active:
        macros.append(f"\\newcommand{{\\{claim.latex_macro}}}{{{_latex(claim.value)}}}")
    macros.append("")

    rows = [
        "% Generated by paper/scripts/build_evidence.py; do not edit.",
        r"\begin{tabular}{p{0.25\linewidth}p{0.15\linewidth}p{0.18\linewidth}p{0.27\linewidth}}",
        r"\toprule",
        r"Result & Value & Evidence & Experimental unit \\",
        r"\midrule",
    ]
    for claim in active:
        rows.append(
            f"{_latex(claim.title)} & {_latex(claim.value + ' ' + claim.unit).strip()} & "
            f"{_latex(claim.evidence_class)} & {_latex(claim.experimental_unit)} \\\\"
        )
    rows.extend([r"\bottomrule", r"\end{tabular}", ""])
    outputs = {"claims.tex": "\n".join(macros), "results-table.tex": "\n".join(rows)}
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    ledger = args.ledger or repo / "paper" / "evidence" / "claims.yaml"
    output = args.output or repo / "paper" / "generated"
    claims = load_claims(ledger)
    errors = validate_claims(repo, claims)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.check:
        with tempfile_directory() as temp:
            expected = generate_outputs(repo, claims, temp)
        stale = [name for name, content in expected.items() if not (output / name).is_file() or (output / name).read_text(encoding="utf-8") != content]
        if stale:
            print(f"stale generated evidence: {', '.join(stale)}", file=sys.stderr)
            return 1
    else:
        generate_outputs(repo, claims, output)
    return 0


class tempfile_directory:
    def __enter__(self) -> Path:
        import tempfile

        self._temp = tempfile.TemporaryDirectory()
        return Path(self._temp.name)

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._temp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
