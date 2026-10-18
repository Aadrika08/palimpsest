import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
PRD = ROOT / "docs/borrowed-body-prd-v1.md"
MATRIX = ROOT / "docs/requirements-evidence.md"
STATUSES = {"passed", "failed", "limited", "deferred"}
GATES = {
    "SIM-LAB",
    "SIM-MEMORY",
    "SIM-TASKS",
    "SIM-MALECNS",
    "SIM-ARTWORK",
    "SIM-OPERATOR",
    "SIM-HANDOFF",
}


def rows(pattern, text):
    return re.findall(pattern, text, flags=re.MULTILINE)


def heading_slugs(path):
    slugs, seen = set(), {}
    for line in path.read_text().splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        heading = re.sub(r"[`*_~]", "", match.group(1)).casefold()
        slug = re.sub(r"[^\w\- ]", "", heading)
        slug = re.sub(r"\s+", "-", slug.strip())
        duplicate = seen.get(slug, 0)
        seen[slug] = duplicate + 1
        slugs.add(slug if duplicate == 0 else f"{slug}-{duplicate}")
    return slugs


def link_errors(source, text):
    destinations = rows(r"\[[^\]]+\]\(([^)]+)\)", text)
    destinations += rows(r"^\[[^\]]+\]:\s*(\S+)", text)
    ignored_runs, missing, fragments = [], [], []
    for destination in destinations:
        destination = destination.strip("<>")
        if "://" in destination:
            continue
        target, separator, fragment = destination.partition("#")
        resolved = source if not target else (source.parent / target).resolve()
        if resolved.is_relative_to(ROOT / "runs"):
            ignored_runs.append(destination)
        if not resolved.exists():
            missing.append(destination)
        elif (
            separator
            and resolved.suffix.casefold() == ".md"
            and unquote(fragment).casefold() not in heading_slugs(resolved)
        ):
            fragments.append(destination)
    return ignored_runs, missing, fragments


def test_every_prd_requirement_has_one_explicit_status():
    expected = rows(r"^\|\s*((?:LAB|MEM|ART|HW)-\d{3})\s*\|", PRD.read_text())
    actual = rows(
        r"^\|\s*((?:LAB|MEM|ART|HW)-\d{3})\s*\|\s*([a-z]+)\s*\|",
        MATRIX.read_text(),
    )
    assert len(expected) == len(set(expected)) == 26
    assert len(actual) == len({requirement for requirement, _ in actual}) == 26
    assert {requirement for requirement, _ in actual} == set(expected)
    assert {status for _, status in actual} <= STATUSES
    status_by_requirement = dict(actual)
    assert status_by_requirement["HW-001"] == "deferred"
    assert all(status != "deferred" for key, status in actual if key != "HW-001")


def test_every_simulation_completion_gate_has_one_explicit_status():
    actual = rows(
        r"^\|\s*(SIM-[A-Z]+)\s*\|\s*([a-z]+)\s*\|",
        MATRIX.read_text(),
    )
    assert len(actual) == len({gate for gate, _ in actual}) == len(GATES)
    assert {gate for gate, _ in actual} == GATES
    assert {status for _, status in actual} <= STATUSES
    assert all(status != "deferred" for _, status in actual)
    assert dict(actual)["SIM-LAB"] == "failed"


def test_release_matrix_links_are_portable(tmp_path):
    ignored_runs, missing, fragments = link_errors(MATRIX, MATRIX.read_text())
    assert ignored_runs == []
    assert missing == []
    assert fragments == []
    target = tmp_path / "target.md"
    target.write_text("# Present heading\n")
    source = tmp_path / "source.md"
    source.write_text("[missing](target.md#absent-heading)\n")
    # The authored pair may sit under a runs/ basetemp, so only its missing/fragment results are asserted.
    _, missing, fragments = link_errors(source, source.read_text())
    assert (missing, fragments) == ([], ["target.md#absent-heading"])
