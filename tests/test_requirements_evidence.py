import re
from pathlib import Path


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


def test_release_matrix_links_are_portable():
    text = MATRIX.read_text()
    destinations = rows(r"\[[^\]]+\]\(([^)]+)\)", text)
    destinations += rows(r"^\[[^\]]+\]:\s*(\S+)", text)
    local = []
    for destination in destinations:
        target = destination.strip("<>").split("#", 1)[0]
        if not target or "://" in target:
            continue
        local.append(target)
    assert not any(Path(target).parts[:2] == ("..", "runs") for target in local)
    missing = [target for target in local if not (MATRIX.parent / target).resolve().exists()]
    assert missing == []
