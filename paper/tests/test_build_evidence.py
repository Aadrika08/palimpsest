import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_evidence import generate_outputs, load_claims, validate_claims  # noqa: E402


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class EvidenceBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        (self.repo / "docs").mkdir()
        self.source_bytes = b"Result: 28 / 30 goals on development seeds.\n"
        (self.repo / "docs" / "result.md").write_bytes(self.source_bytes)

    def tearDown(self):
        self.temp.cleanup()

    def claim(self, **overrides):
        base = {
            "id": "flynn_development_goals",
            "claim_key": "flynn.development.goals",
            "title": "FLYNN development goals",
            "status": "active",
            "supersedes": None,
            "source": "docs/result.md",
            "source_sha256": digest(self.source_bytes),
            "anchor": "28 / 30 goals",
            "json_pointer": None,
            "expected_value": None,
            "source_revision": "abc1234",
            "evidence_class": "development",
            "experimental_unit": "seeded episode",
            "value": "28/30",
            "unit": "goal episodes",
            "permitted_wording": "FLYNN reached the goal in 28 of 30 development episodes.",
            "latex_macro": "FlynnDevelopmentGoals",
            "table_group": "Reproduction",
        }
        base.update(overrides)
        return base

    def write_ledger(self, claims):
        path = self.repo / "claims.yaml"
        path.write_text(json.dumps({"schema_version": 1, "claims": claims}), encoding="utf-8")
        return path

    def test_valid_ledger_generates_deterministic_latex(self):
        claims = load_claims(self.write_ledger([self.claim()]))
        self.assertEqual(validate_claims(self.repo, claims), [])
        first = generate_outputs(self.repo, claims, self.repo / "generated")
        second = generate_outputs(self.repo, claims, self.repo / "generated-again")
        self.assertEqual(first["claims.tex"], second["claims.tex"])
        self.assertIn(r"\newcommand{\FlynnDevelopmentGoals}{28/30}", first["claims.tex"])
        self.assertIn("seeded episode", first["results-table.tex"])

    def test_missing_evidence_path_is_reported(self):
        claims = load_claims(self.write_ledger([self.claim(source="docs/missing.md")]))
        self.assertIn("flynn_development_goals: missing source docs/missing.md", validate_claims(self.repo, claims))

    def test_source_hash_drift_is_reported(self):
        claims = load_claims(self.write_ledger([self.claim(source_sha256="0" * 64)]))
        errors = validate_claims(self.repo, claims)
        self.assertTrue(any("source hash mismatch" in error for error in errors))

    def test_missing_anchor_is_reported(self):
        claims = load_claims(self.write_ledger([self.claim(anchor="31 / 30 goals")]))
        errors = validate_claims(self.repo, claims)
        self.assertIn("flynn_development_goals: anchor not found", errors)

    def test_json_pointer_checks_expected_value(self):
        payload = {"runs": {"goals": 28}}
        data = json.dumps(payload, sort_keys=True).encode()
        (self.repo / "docs" / "result.json").write_bytes(data)
        claim = self.claim(
            source="docs/result.json",
            source_sha256=digest(data),
            anchor=None,
            json_pointer="/runs/goals",
            expected_value=29,
        )
        errors = validate_claims(self.repo, load_claims(self.write_ledger([claim])))
        self.assertTrue(any("JSON pointer value mismatch" in error for error in errors))

    def test_duplicate_active_claim_key_with_conflicting_value_is_reported(self):
        other = self.claim(id="flynn_goals_other", value="29/30", latex_macro="FlynnGoalsOther")
        claims = load_claims(self.write_ledger([self.claim(), other]))
        errors = validate_claims(self.repo, claims)
        self.assertTrue(any("conflicting active claim_key" in error for error in errors))

    def test_invalid_supersession_is_reported(self):
        active = self.claim(id="new", supersedes="old", latex_macro="NewClaim")
        old = self.claim(id="old", status="active", latex_macro="OldClaim")
        errors = validate_claims(self.repo, load_claims(self.write_ledger([old, active])))
        self.assertIn("new: superseded claim old must have status superseded", errors)

    def test_unknown_evidence_class_is_reported(self):
        claims = load_claims(self.write_ledger([self.claim(evidence_class="scientific")]))
        self.assertIn("flynn_development_goals: unknown evidence class scientific", validate_claims(self.repo, claims))

    def test_development_claim_cannot_use_qualification_wording(self):
        claim = self.claim(permitted_wording="The controller is qualified and proves an advantage.")
        errors = validate_claims(self.repo, load_claims(self.write_ledger([claim])))
        self.assertTrue(any("prohibited wording" in error for error in errors))

    def test_duplicate_latex_macro_is_reported(self):
        other = self.claim(
            id="other",
            claim_key="other.key",
            value="28/30",
            latex_macro="FlynnDevelopmentGoals",
        )
        errors = validate_claims(self.repo, load_claims(self.write_ledger([self.claim(), other])))
        self.assertTrue(any("duplicate latex_macro" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
