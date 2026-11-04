import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_paper import inspect_paper  # noqa: E402


class PaperVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[2]
        cls.pdf = cls.repo / "paper" / "build" / "palimpsest-systems-paper.pdf"
        cls.log = cls.repo / "paper" / "build" / "main.log"
        if not cls.pdf.is_file() or not cls.log.is_file():
            raise unittest.SkipTest("paper PDF must be built before verifier tests")

    def test_missing_pdf_is_reported(self):
        errors, _ = inspect_paper(
            self.repo,
            self.repo / "paper" / "build" / "missing.pdf",
            self.log,
            [],
            [],
            ["Introduction"],
            1,
        )
        self.assertIn("missing PDF", errors)

    def test_unresolved_reference_and_overfull_box_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "paper.log"
            log.write_text("LaTeX Warning: There were undefined references.\nOverfull \\hbox\n")
            errors, _ = inspect_paper(
                self.repo, self.pdf, log, [], [], ["Introduction"], 1
            )
        self.assertIn("LaTeX log contains undefined references", errors)
        self.assertIn("LaTeX log contains overfull boxes", errors)

    def test_stale_generated_output_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            generated = root / "generated.tex"
            source = root / "claims.yaml"
            generated.write_text("old")
            source.write_text("new")
            now = time.time()
            os.utime(generated, (now - 10, now - 10))
            os.utime(source, (now, now))
            errors, _ = inspect_paper(
                self.repo, self.pdf, self.log, [source], [generated], ["Introduction"], 1
            )
        self.assertTrue(any("stale generated output" in error for error in errors))

    def test_missing_expected_text_is_reported(self):
        errors, _ = inspect_paper(
            self.repo,
            self.pdf,
            self.log,
            [],
            [],
            ["THIS SECTION DOES NOT EXIST"],
            1,
        )
        self.assertIn("PDF missing expected text: THIS SECTION DOES NOT EXIST", errors)

    def test_minimum_page_count_is_enforced(self):
        errors, _ = inspect_paper(
            self.repo, self.pdf, self.log, [], [], ["Introduction"], 999
        )
        self.assertTrue(any("page count" in error for error in errors))

    def test_blank_middle_page_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tex = root / "blank.tex"
            tex.write_text(
                r"\documentclass{article}\begin{document}First page"
                r"\newpage\null\newpage Last page\end{document}",
                encoding="utf-8",
            )
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "blank.tex"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            errors, _ = inspect_paper(
                self.repo,
                root / "blank.pdf",
                root / "blank.log",
                [],
                [],
                ["First page", "Last page"],
                3,
            )
        self.assertIn("PDF page 2 is blank", errors)

    def test_pdf_is_bound_to_all_build_input_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            paper = repo / "paper"
            paper.mkdir()
            pdf = repo / "paper.pdf"
            log = repo / "paper.log"
            pdf.write_bytes(self.pdf.read_bytes())
            log.write_text(self.log.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            inputs = [paper / "main.tex", paper / "references.bib"]
            for source in inputs:
                source.write_text(source.name, encoding="utf-8")
                os.utime(source, (pdf.stat().st_mtime - 10, pdf.stat().st_mtime - 10))
            errors, metadata = inspect_paper(
                repo,
                pdf,
                log,
                [],
                [],
                ["Introduction"],
                1,
                build_inputs=inputs,
            )
        self.assertEqual(errors, [])
        self.assertEqual(
            sorted(metadata["build_input_sha256"]),
            ["paper/main.tex", "paper/references.bib"],
        )

    def test_pdf_older_than_build_input_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "newer.tex"
            source.write_text("changed")
            future = self.pdf.stat().st_mtime + 10
            os.utime(source, (future, future))
            errors, _ = inspect_paper(
                self.repo,
                self.pdf,
                self.log,
                [],
                [],
                ["Introduction"],
                1,
                build_inputs=[source],
            )
        self.assertTrue(any("PDF older than build input" in error for error in errors))

    def test_success_metadata_is_deterministic(self):
        args = (
            self.repo,
            self.pdf,
            self.log,
            [self.repo / "paper" / "evidence" / "claims.yaml"],
            [self.repo / "paper" / "generated" / "claims.tex"],
            ["Introduction", "System Design", "Evaluation", "Limitations and Threats to Validity"],
            5,
        )
        first_errors, first = inspect_paper(*args)
        second_errors, second = inspect_paper(*args)
        self.assertEqual(first_errors, [])
        self.assertEqual(first, second)
        self.assertEqual(first["page_count"], 7)
        self.assertRegex(first["pdf_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
