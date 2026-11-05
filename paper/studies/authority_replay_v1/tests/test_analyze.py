"""Whole-campaign acceptance must never silently omit a failed or altered unit."""
import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def campaign():
    common = importlib.import_module("paper.studies.authority_replay_v1.common")
    analyze = importlib.import_module("paper.studies.authority_replay_v1.analyze")
    protocol = common.load_protocol(ROOT / "protocol.json")
    identity = {"commit": "a" * 40, "protocol_sha256": hashlib.sha256((ROOT / "protocol.json").read_bytes()).hexdigest(),
                "runtime_source_sha256": {"src/runtime.py": "c" * 64},
                "asset_manifest_sha256": {"model_manifests/flynn-full-vision.json": "d" * 64},
                "asset_sha256": {"checkpoint": "e" * 64}}
    rows = [{**unit, "schema_version": 1, "study_id": protocol.study_id,
             "identity": copy.deepcopy(identity), "status": "completed", "metrics": {"wall_seconds": 1.0}}
            for unit in common.declared_units(protocol)]
    return analyze, protocol, identity, rows


def write_rows(tmp_path, rows):
    path = tmp_path / "rows.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path


def test_complete_rows_keep_failures_and_declared_order(campaign, tmp_path):
    analyze, protocol, identity, rows = campaign
    rows[0].update(status="failed", error="original failure")
    path = write_rows(tmp_path, list(reversed(rows)))
    loaded = analyze.load_complete_rows(protocol, [path], identity)
    assert [r["unit_id"] for r in loaded] == [r["unit_id"] for r in rows]
    assert loaded[0]["status"] == "failed"
    assert loaded[0]["error"] == "original failure"


@pytest.mark.parametrize("entrypoint", ["load_complete_rows", "summarize"])
@pytest.mark.parametrize("drift", ["foreign_identity", "changed_protocol_bytes"])
def test_rejects_consistent_rows_bound_to_other_protocol_bytes(campaign, tmp_path, entrypoint, drift):
    analyze, protocol, identity, rows = campaign
    if drift == "foreign_identity":
        identity["protocol_sha256"] = "0" * 64
        for row in rows:
            row["identity"] = copy.deepcopy(identity)
    else:
        # Identical parsed values, different exact bytes: canonical JSON hashing
        # would silently miss this change to the frozen protocol artifact.
        path = tmp_path / "changed-protocol.json"
        path.write_bytes((ROOT / "protocol.json").read_bytes() + b" ")
        common = importlib.import_module("paper.studies.authority_replay_v1.common")
        protocol = common.load_protocol(path)
    assert len(rows) == 111
    assert all(row["identity"] == identity for row in rows)
    with pytest.raises(ValueError, match="protocol"):
        if entrypoint == "load_complete_rows":
            analyze.load_complete_rows(protocol, [write_rows(tmp_path, rows)], identity)
        else:
            analyze.summarize(protocol, rows)


@pytest.mark.parametrize("problem", ["duplicate", "missing", "undeclared", "descriptor", "status", "schema", "study", "nonfinite"])
def test_rejects_invalid_row_sets(campaign, tmp_path, problem):
    analyze, protocol, identity, rows = campaign
    if problem == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif problem == "missing":
        rows.pop()
    elif problem == "undeclared":
        rows[0]["unit_id"] += "/retry-1"
    elif problem == "descriptor":
        rows[0]["condition"] = "invented_control"
    elif problem == "status":
        rows[0]["status"] = "retried"
    elif problem == "schema":
        rows[0]["schema_version"] = True
    elif problem == "study":
        rows[0]["study_id"] = "another_study"
    else:
        rows[0]["metrics"] = {"nested": [float("nan")]}
    with pytest.raises(ValueError):
        analyze.load_complete_rows(protocol, [write_rows(tmp_path, rows)], identity)


@pytest.mark.parametrize("key", ["commit", "protocol_sha256", "runtime_source_sha256", "asset_manifest_sha256", "asset_sha256"])
def test_rejects_any_identity_drift(campaign, tmp_path, key):
    analyze, protocol, identity, rows = campaign
    rows[0]["identity"][key] = "drift"
    with pytest.raises(ValueError, match="identity"):
        analyze.load_complete_rows(protocol, [write_rows(tmp_path, rows)], identity)


def test_duplicate_keys_and_truncated_logs_are_refused(campaign, tmp_path):
    analyze, protocol, identity, rows = campaign
    path = write_rows(tmp_path, rows)
    with path.open("a") as stream:
        stream.write('{"unit_id":"a","unit_id":"b"}\n')
    with pytest.raises(ValueError):
        analyze.load_complete_rows(protocol, [path], identity)
    path.write_text(json.dumps(rows[0]))  # No terminal newline: incomplete append.
    with pytest.raises(ValueError):
        analyze.load_complete_rows(protocol, [path], identity)


def test_summary_is_deterministic_and_keeps_failed_denominators(campaign):
    analyze, protocol, _, rows = campaign
    rows[0].update(status="failed", error="retained")
    rows[1]["status"] = "refused"
    rows[2]["status"] = "timeout"
    rows[3]["status"] = "incomplete"
    result = analyze.summarize(protocol, rows)
    assert result == analyze.summarize(protocol, list(reversed(rows)))
    assert result["declared_units"] == 111
    assert result["status_counts"] == {"completed": 107, "failed": 1, "refused": 1, "timeout": 1, "incomplete": 1}
    assert result["by_kind"]["fault"]["denominator"] == 50
    assert result["by_kind"]["fault"]["status_counts"]["completed"] == 46
    assert {r["unit_id"] for r in result["failures"]} == {r["unit_id"] for r in rows[:4]}
    assert result["failures"][0]["error"] == "retained"
    assert len(result["rows"]) == 111


def test_summary_numeric_statistics_and_raw_pairs(campaign):
    analyze, protocol, _, rows = campaign
    continuation = [r for r in rows if r["kind"] == "continuation"]
    for i, row in enumerate(continuation):
        row["metrics"]["wall_seconds"] = float(i)
    result = analyze.summarize(protocol, rows)
    stats = result["by_kind"]["continuation"]["metrics"]["wall_seconds"]
    assert stats == {"n": 10, "median": 4.5, "minimum": 0.0, "maximum": 9.0, "q1": 2.25, "q3": 6.75, "iqr": 4.5}
    assert [r["metrics"]["wall_seconds"] for r in result["rows"] if r["kind"] == "continuation"] == [float(i) for i in range(10)]


def test_summary_cannot_bypass_completeness_validation(campaign):
    analyze, protocol, _, rows = campaign
    with pytest.raises(ValueError):
        analyze.summarize(protocol, rows[:-1])


def test_semantic_outcomes_are_independent_of_execution_status(campaign):
    analyze, protocol, _, rows = campaign
    rows[0].update(status="refused", explicit_detection=True, correct_recovery=False)
    rows[1].update(status="completed", silent_acceptance=True)
    rows[2].update(status="completed", correct_recovery=True)
    control = next(r for r in rows if r.get("case_id") == "C3")
    control["benign_false_rejection"] = True
    result = analyze.summarize(protocol, rows)
    assert result["by_kind"]["fault"]["semantic_outcomes"] == {
        "silent_acceptance": {"true": 1, "reported": 1},
        "explicit_detection": {"true": 1, "reported": 1},
        "correct_recovery": {"true": 1, "reported": 2},
        "benign_false_rejection": {"true": 1, "reported": 1},
    }
    assert result["status_counts"]["refused"] == 1


@pytest.mark.parametrize("identity", [{}, {"commit": "a" * 40}, {"commit": "not-a-sha", "protocol_sha256": "b" * 64,
                        "runtime_source_sha256": {}, "asset_manifest_sha256": {}, "asset_sha256": {}}])
def test_invalid_expected_identity_is_rejected(campaign, tmp_path, identity):
    analyze, protocol, _, rows = campaign
    for row in rows:
        row["identity"] = identity
    with pytest.raises(ValueError, match="identity"):
        analyze.load_complete_rows(protocol, [write_rows(tmp_path, rows)], identity)


def test_analyzer_cli_generates_complete_reviewable_outputs(campaign, tmp_path):
    import subprocess
    import sys
    _, _, identity, rows = campaign
    identity_path = tmp_path / "identity.json"
    identity_path.write_text(json.dumps(identity))
    row_path = write_rows(tmp_path, rows)
    output = tmp_path / "summary"
    command = [sys.executable, "-B", str(ROOT / "analyze.py"), "--protocol", str(ROOT / "protocol.json"),
               "--rows", str(row_path), "--identity", str(identity_path), "--output", str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads((output / "summary.json").read_text())["declared_units"] == 111
    assert json.loads((output / "failures.json").read_text()) == []
    import csv
    with (output / "rows.csv").open() as stream:
        assert len(list(csv.DictReader(stream))) == 111
    before = (output / "summary.json").read_bytes()
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert (output / "summary.json").read_bytes() == before
