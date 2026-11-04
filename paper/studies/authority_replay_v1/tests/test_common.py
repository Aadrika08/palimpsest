"""Contract tests: reject changed denominators, identities, and destructive output reuse."""
import importlib
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def common():
    # Import inside the fixture so the initial RED run reports missing interfaces.
    return importlib.import_module("paper.studies.authority_replay_v1.common")


@pytest.fixture
def protocol(common):
    return common.load_protocol(ROOT / "protocol.json")


def test_public_contract_exists(common):
    for name in ("Protocol", "FaultCase", "load_protocol", "campaign_identity",
                 "prepare_output_root", "append_row", "declared_units"):
        assert hasattr(common, name)


@pytest.mark.parametrize("mutation", ["version", "unknown", "condition", "seed", "nan", "case"])
def test_rejects_invalid_protocol(common, tmp_path, mutation):
    raw = json.loads((ROOT / "protocol.json").read_text())
    if mutation == "version":
        raw["schema_version"] = True
    elif mutation == "unknown":
        raw["unregistered"] = 1
    elif mutation == "condition":
        raw["fault_cases"][0]["conditions"] = ["invented_control"]
    elif mutation == "seed":
        raw["continuation"]["seeds"] = [0, 0]
    elif mutation == "nan":
        raw["comparison_policy"]["atol"] = float("nan")
    else:
        raw["fault_cases"][1]["id"] = "A1"
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        common.load_protocol(path)


def test_exact_unit_expansion_and_cyclic_order(common, protocol):
    units = common.declared_units(protocol)
    assert len(units) == 111
    assert len({unit["unit_id"] for unit in units}) == 111
    counts = {kind: sum(u["kind"] == kind for u in units) for kind in
              ("fault", "continuation", "replay", "execution_overhead", "operation_cost", "offline_reproduction")}
    assert counts == {"fault": 50, "continuation": 10, "replay": 5,
                      "execution_overhead": 40, "operation_cost": 5, "offline_reproduction": 1}
    fault_counts = {case.id: sum(u.get("case_id") == case.id for u in units)
                    for case in protocol.fault_cases}
    assert fault_counts == {"A1": 3, "A2": 3, "A3": 3, "R1": 3, "R2": 3,
                           "S1": 3, "S2": 3, "D1": 3, "D2": 3, "C1": 1,
                           "C2": 1, "C3": 3, "P1": 3, "B1": 3, "B2": 3,
                           "E1": 3, "E2": 3, "E3": 3}
    assert {u["seed"] for u in units if u["kind"] == "continuation"} == set(range(10))
    assert {u["seed"] for u in units if u["kind"] == "replay"} == set(range(5))
    assert {u["variant"] for u in units if u.get("case_id") == "D1"} == {"source", "lock", "hash"}
    assert {u["variant"] for u in units if u.get("case_id") == "D2"} == {"graph", "checkpoint", "mapping"}
    assert {u["condition"] for u in units if u.get("case_id") == "C3"} == {"benign_control"}
    assert all(u["condition"] == "fault" for u in units if u["kind"] == "fault" and u["case_id"] != "C3")
    for seed, expected in enumerate([
        ["null", "synchronous", "background", "background_storage"],
        ["synchronous", "background", "background_storage", "null"],
        ["background", "background_storage", "null", "synchronous"],
        ["background_storage", "null", "synchronous", "background"],
    ]):
        matched = [u for u in units if u["kind"] == "execution_overhead" and u["seed"] == seed]
        assert [u["condition"] for u in matched] == expected
        assert [u["condition_ordinal"] for u in matched] == [0, 1, 2, 3]


def test_protocol_resource_and_comparison_bounds(protocol):
    assert protocol.resources["unit_timeout_seconds"] == 900
    assert protocol.resources["campaign_timeout_seconds"] == 14400
    assert protocol.resources["ordinary_unit_max_output_bytes"] == 536870912
    assert protocol.resources["offline_unit_max_output_bytes"] == 2147483648
    assert protocol.resources["campaign_max_output_bytes"] == 8589934592
    assert protocol.resources["minimum_free_bytes"] == 6442450944
    assert protocol.comparison_policy["atol"] == 1e-6
    assert protocol.comparison_policy["rtol"] == 1e-6
    assert protocol.comparison_policy["identical_nan_positions"] is True
    assert protocol.execution_overhead["warmup_ticks"] == 20
    assert protocol.execution_overhead["measured_ticks"] == 200


def test_output_root_refuses_existing_content_without_mutation(common, tmp_path):
    root = tmp_path / "new"
    common.prepare_output_root(root)
    marker = root / ".hidden"
    marker.write_bytes(b"retained")
    with pytest.raises(ValueError, match="non-empty"):
        common.prepare_output_root(root)
    assert marker.read_bytes() == b"retained"


def test_rows_are_append_only_and_unique(common, tmp_path):
    path = tmp_path / "rows.jsonl"
    row = {"unit_id": "fault/A1/default/fault/seed-0", "status": "failed", "metrics": {"seconds": 0.0}}
    common.append_row(path, row)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="duplicate"):
        common.append_row(path, row)
    assert path.read_bytes() == original
    common.append_row(path, {**row, "unit_id": "another"})
    assert path.read_bytes().startswith(original)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_append_rejects_nested_nonfinite_numbers(common, tmp_path, value):
    path = tmp_path / "rows.jsonl"
    with pytest.raises(ValueError, match="finite"):
        common.append_row(path, {"unit_id": "a", "metrics": {"nested": [value]}})
    assert not path.exists()


def test_append_refuses_damaged_existing_log(common, tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_bytes(b'{"unit_id":"first"}\n{"unit_id":')
    before = path.read_bytes()
    with pytest.raises(ValueError):
        common.append_row(path, {"unit_id": "second"})
    assert path.read_bytes() == before


def test_campaign_identity_binds_clean_commit_protocol_sources_and_assets(common, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src/runtime.py").write_text("VALUE = 1\n")
    (repo / "model_manifests").mkdir()
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "checkpoint.bin").write_bytes(b"pinned")
    import hashlib
    manifest = {"files": [{"id": "checkpoint", "path": "checkpoint.bin", "size_bytes": 6,
                            "sha256": hashlib.sha256(b"pinned").hexdigest()}]}
    (repo / "model_manifests/flynn-full-vision.json").write_text(json.dumps(manifest))
    protocol_path = repo / "protocol.json"
    protocol_path.write_text("{}\n")
    for args in (["init", "-q"], ["add", "."], ["-c", "user.name=Study Test", "-c", "user.email=study@example.invalid", "commit", "-qm", "fixture"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    identity = common.campaign_identity(repo, protocol_path, assets)
    assert identity["commit"] == subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    assert identity["protocol_sha256"] == hashlib.sha256(b"{}\n").hexdigest()
    assert identity["runtime_source_sha256"]["src/runtime.py"] == hashlib.sha256(b"VALUE = 1\n").hexdigest()
    assert identity["asset_sha256"]["checkpoint.bin"] == hashlib.sha256(b"pinned").hexdigest()
    assert identity["asset_manifest_sha256"]["model_manifests/flynn-full-vision.json"]
    (assets / "checkpoint.bin").write_bytes(b"drift!")
    with pytest.raises(ValueError, match="asset"):
        common.campaign_identity(repo, protocol_path, assets)
    (assets / "checkpoint.bin").write_bytes(b"pinned")
    (repo / "src/runtime.py").write_text("VALUE = 2\n")
    with pytest.raises(ValueError, match="clean"):
        common.campaign_identity(repo, protocol_path, assets)
