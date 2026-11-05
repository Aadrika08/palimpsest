"""Lightweight protocol, identity, and append-only campaign contracts.

This module does not execute experiments. A declared row is an accounting unit,
including when its execution fails or is stopped before completion.
"""
from dataclasses import dataclass, field, fields
import fcntl
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any


@dataclass(frozen=True)
class FaultCase:
    id: str
    family: str
    path: str
    seeds: list[int]
    variants: list[str]
    conditions: list[str]
    injection_stage: str
    naive_predicate: str
    semantic_oracle: str
    expected_outcome: str
    timeout_seconds: int
    max_output_bytes: int


@dataclass(frozen=True)
class Protocol:
    schema_version: int
    study_id: str
    resources: dict[str, Any]
    comparison_policy: dict[str, Any]
    fault_cases: tuple[FaultCase, ...]
    continuation: dict[str, Any]
    replay: dict[str, Any]
    execution_overhead: dict[str, Any]
    operation_cost: dict[str, Any]
    offline_reproduction: dict[str, Any]
    protocol_revision: int = 1
    # Loader metadata, not part of the frozen JSON schema or constructor.
    _content_sha256: str = field(init=False, repr=False, compare=False, default="")


STATUSES = ("completed", "failed", "refused", "timeout", "incomplete")
FAULT_IDS = ("A1", "A2", "A3", "R1", "R2", "S1", "S2", "D1", "D2",
             "C1", "C2", "C3", "P1", "B1", "B2", "E1", "E2", "E3")
OVERHEAD_CONDITIONS = ["null", "synchronous", "background", "background_storage"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_finite(value: object) -> None:
    """Reject JSON-incompatible values and non-finite numbers at any depth."""
    if isinstance(value, float):
        require(math.isfinite(value), "numeric fields must be finite")
    elif isinstance(value, dict):
        require(all(isinstance(k, str) for k in value), "JSON keys must be strings")
        for child in value.values():
            validate_finite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            validate_finite(child)
    else:
        require(value is None or type(value) in (str, int, bool), "unsupported JSON value")


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(data: str) -> Any:
    value = json.loads(data, object_pairs_hook=_object)
    validate_finite(value)
    return value


def _keys(value: object, expected: set[str], label: str) -> None:
    require(isinstance(value, dict) and set(value) == expected, f"invalid {label} fields")


def _seeds(value: object, expected: list[int], label: str) -> None:
    require(isinstance(value, list) and all(type(v) is int for v in value)
            and value == expected, f"invalid {label} seeds")


def load_protocol(path: Path) -> Protocol:
    content = path.read_bytes()
    raw = parse_json(content.decode("utf-8"))
    _keys(raw, {f.name for f in fields(Protocol) if f.init} - ({'protocol_revision'} if 'protocol_revision' not in raw else set()), "protocol")
    revision = raw.get('protocol_revision', 1)
    require(type(revision) is int and revision in (1, 2, 3), 'unsupported protocol revision')
    require(type(raw["schema_version"]) is int and raw["schema_version"] == 1, "unsupported schema version")
    require(raw["study_id"] == "authority_replay_v1", "unsupported study ID")
    resources = raw["resources"]
    expected_bounds = {"unit_timeout_seconds": 900, "campaign_timeout_seconds": 14400,
                       "ordinary_unit_max_output_bytes": 512 * 1024**2,
                       "offline_unit_max_output_bytes": 10 * 1024**3,
                       "campaign_max_output_bytes": ({1: 16, 2: 13, 3: 12}[revision]) * 1024**3,
                       "minimum_free_bytes": 6 * 1024**3}
    _keys(resources, set(expected_bounds) | {"raw_output_root", "sequential", "cpu_only", "stop_rules"}, "resources")
    for key, expected in expected_bounds.items():
        require(type(resources[key]) is int and resources[key] == expected, f"invalid resource bound: {key}")
    require(resources["sequential"] is True and resources["cpu_only"] is True, "study must be sequential and CPU-only")
    require(resources["raw_output_root"] == "runs/paper-authority-replay-v1", "invalid raw output root")
    require(isinstance(resources["stop_rules"], list) and len(resources["stop_rules"]) == 4
            and all(isinstance(x, str) and x for x in resources["stop_rules"]), "missing stop rules")
    comparison = raw["comparison_policy"]
    _keys(comparison, {"exact_fields", "float_dtype", "atol", "rtol", "identical_nan_positions", "nonfinite_policy", "scope", "first_divergence", "freeze"}, "comparison")
    require(comparison["exact_fields"] == ["integer", "boolean", "identity", "shape", "event", "source_identity", "asset_identity"]
            and comparison["float_dtype"] == "float32" and comparison["atol"] == 1e-6
            and comparison["rtol"] == 1e-6 and comparison["identical_nan_positions"] is False
            and comparison["nonfinite_policy"] == "reject_nonfinite_scientific_arrays"
            and comparison["scope"] == "CPU/same-version/same-architecture"
            and comparison["first_divergence"] == ["field", "tick"], "invalid frozen comparison policy")
    require(isinstance(raw["fault_cases"], list), "fault_cases must be a list")
    cases = []
    for case in raw["fault_cases"]:
        _keys(case, {f.name for f in fields(FaultCase)}, "fault case")
        case_id = case["id"]
        require(case_id in FAULT_IDS, "undeclared fault case")
        runtime = case_id[0] in {"A", "R", "S", "D", "B"}
        _seeds(case["seeds"], ([0] if case_id.startswith("D") else [0, 1, 2]) if runtime else [], case_id)
        require(case["path"] == ("runtime" if runtime else "fixture_subprocess" if case_id == "P1" else "fixture"), "invalid fault path")
        require(case["conditions"] == (["benign_control"] if case_id == "C3" else ["fault"]), "undeclared fault condition")
        variants = case["variants"]
        require(isinstance(variants, list) and variants and all(isinstance(v, str) and v and "/" not in v for v in variants)
                and len(set(variants)) == len(variants), "invalid fault variants")
        expected_variants = {"D1": ["source", "lock", "hash"], "D2": ["graph", "checkpoint", "mapping"],
                             "C1": ["same_byte_replace"], "C2": ["edit_restore"],
                             "C3": ["sibling_operation_1", "sibling_operation_2", "sibling_operation_3"],
                             "P1": ["before_chunk_rename", "after_rename_before_event", "before_terminal_manifest"],
                             "E1": ["payload_bound_1", "payload_bound_2", "payload_bound_3"],
                             "E2": ["queue_bound_1", "queue_bound_2", "queue_bound_3"], "E3": ["write", "flush", "fsync"]}
        require(variants == expected_variants.get(case_id, ["default"]), "undeclared fault variants")
        require(type(case["timeout_seconds"]) is int and case["timeout_seconds"] == 900
                and type(case["max_output_bytes"]) is int and case["max_output_bytes"] == 512 * 1024**2, "invalid fault bounds")
        for name in ("family", "injection_stage", "naive_predicate", "semantic_oracle", "expected_outcome"):
            require(isinstance(case[name], str) and bool(case[name]), f"missing {name}")
        require(case["expected_outcome"] in {"explicit_detection", "correct_recovery", "benign_acceptance"}, "invalid expected outcome")
        cases.append(FaultCase(**case))
    require([c.id for c in cases] == list(FAULT_IDS), "missing, duplicate, or reordered fault cases")
    section_fields = {
        "continuation": {"seeds", "prefix_ticks", "continuation_ticks", "path", "controller", "device", "experimental_unit", "metrics"},
        "replay": {"seeds", "prefix_ticks", "source_ticks", "path", "controller", "device", "experimental_unit", "conditions", "metrics"},
        "execution_overhead": {"seeds", "conditions", "order", "fresh_process_per_condition", "warmup_ticks", "measured_ticks", "exclude_open_time", "cache_policy", "matched_fields", "unmatched_policy", "metrics", "covariates"},
        "operation_cost": {"seeds", "source", "source_condition", "metrics", "null_writer_replay_timings", "pass_threshold"},
        "offline_reproduction": {"repetitions", "scope", "full_flynn", "duration_seconds", "setup", "independent_machine_reproduction", "external_gate"},
    }
    if revision >= 2:
        section_fields['execution_overhead'].add('terminal_policy')
    for name, expected in section_fields.items():
        _keys(raw[name], expected, name)
        if "seeds" in expected:
            _seeds(raw[name]["seeds"], list(range(10 if name in ("continuation", "execution_overhead") else 5)), name)
        if "metrics" in expected:
            require(isinstance(raw[name]["metrics"], list) and raw[name]["metrics"]
                    and all(isinstance(x, str) and x for x in raw[name]["metrics"]), f"missing {name} metrics")
    for name, ticks in (("continuation", "continuation_ticks"), ("replay", "source_ticks")):
        section = raw[name]
        require(type(section["prefix_ticks"]) is int and section["prefix_ticks"] == 8
                and type(section[ticks]) is int and section[ticks] == 100
                and section["path"] == "runtime" and section["controller"] == "flynn"
                and section["device"] == "cpu", f"invalid {name} execution bounds")
    require(raw["replay"]["conditions"] == ["branch", "playback", "action_replay", "policy_replay"], "invalid replay conditions")
    overhead = raw["execution_overhead"]
    if revision >= 2:
        require(overhead['terminal_policy'] == 'reset_same_seed', 'invalid overhead terminal policy')
    require(overhead["conditions"] == OVERHEAD_CONDITIONS and overhead["order"] == "cyclic_rotation_by_seed_mod_4"
            and type(overhead["warmup_ticks"]) is int and overhead["warmup_ticks"] == 20
            and type(overhead["measured_ticks"]) is int and overhead["measured_ticks"] == 200
            and overhead["fresh_process_per_condition"] is True and overhead["exclude_open_time"] is True
            and overhead["matched_fields"] == ["actions_sha256", "tick_count", "final_state_sha256"], "invalid matched overhead protocol")
    operations = raw["operation_cost"]
    require(operations["source"] == "replay" and operations["source_condition"] == "background_storage"
            and operations["null_writer_replay_timings"] is False and operations["pass_threshold"] is None, "invalid operation-cost source")
    offline = raw["offline_reproduction"]
    require(type(offline["repetitions"]) is int and offline["repetitions"] == 1
            and offline["scope"] == "same-host clean-checkout" and offline["full_flynn"] is True
            and type(offline["duration_seconds"]) is int and offline["duration_seconds"] == 55
            and offline["setup"] is True and offline["independent_machine_reproduction"] is False, "invalid reproduction scope")
    protocol = Protocol(**{**raw, "fault_cases": tuple(cases)})
    object.__setattr__(protocol, "_content_sha256", hashlib.sha256(content).hexdigest())
    return protocol


def declared_units(protocol: Protocol) -> list[dict[str, object]]:
    """Expand fixed denominators; replay modes remain paired in one source row."""
    units: list[dict[str, object]] = []
    for case in protocol.fault_cases:
        for seed in case.seeds or [None]:
            for variant in case.variants:
                for condition in case.conditions:
                    units.append({"unit_id": f"fault/{case.id}/{variant}/{condition}/seed-{seed if seed is not None else 'none'}",
                                  "kind": "fault", "case_id": case.id, "seed": seed, "variant": variant, "condition": condition})
    for kind in ("continuation", "replay", "execution_overhead", "operation_cost"):
        section = getattr(protocol, kind)
        for seed in section["seeds"]:
            if kind == "execution_overhead":
                rotation = seed % 4
                conditions = section["conditions"][rotation:] + section["conditions"][:rotation]
                for ordinal, condition in enumerate(conditions):
                    units.append({"unit_id": f"overhead/{seed}/{condition}", "kind": kind, "seed": seed,
                                  "condition": condition, "condition_ordinal": ordinal})
            else:
                units.append({"unit_id": f"{kind}/{seed}", "kind": kind, "seed": seed})
    units.append({"unit_id": "offline_reproduction/0", "kind": "offline_reproduction", "repetition": 0})
    return units


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _asset_path(root: Path, name: str) -> Path:
    relative = Path(name)
    require(not relative.is_absolute() and relative.parts and all(p not in (".", "..") for p in relative.parts), "unsafe asset path")
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), "asset escapes root")
    require(not any(p.is_symlink() for p in (path, *path.parents) if p != root.parent), "asset symlinks are unsupported")
    return path


def campaign_identity(repo: Path, protocol: Path, assets: Path) -> dict[str, object]:
    """Bind a clean source commit and verify pinned assets without writing them.

    Prepared graph metadata is optional until graph preparation; when present,
    its edge and mappings are verified too. Drivers must prepare/verify the full
    runtime before freezing identity and recheck identity after each unit.
    """
    repo, protocol, assets = repo.resolve(), protocol.resolve(), assets.resolve()
    require(not _git(repo, "status", "--porcelain", "--untracked-files=normal"), "campaign requires a clean Git checkout")
    source_paths = [Path(p) for p in _git(repo, "ls-files").splitlines()
                    if p.endswith((".py", ".toml", ".lock")) and p.startswith(("src/", "scripts/", "paper/studies/", "pyproject.", "uv.lock"))]
    upstream = repo / "upstream/fly-gym"
    if upstream.is_dir():
        source_paths.extend(p.relative_to(repo) for p in upstream.rglob("*.py") if ".git" not in p.parts)
    require(bool(source_paths), "runtime source files missing")
    manifest_path = repo / "model_manifests/flynn-full-vision.json"
    manifest = parse_json(manifest_path.read_text())
    asset_hashes: dict[str, str] = {}

    def verify(name: str, item: dict[str, object]) -> None:
        path = _asset_path(assets, name)
        require(path.is_file(), f"asset missing: {name}")
        digest = sha256_file(path)
        require(path.stat().st_size == item["size_bytes"] and digest == item["sha256"], f"asset identity mismatch: {name}")
        asset_hashes[name] = digest

    for item in manifest["files"]:
        verify(item["path"], item)
    archive = next((item for item in manifest["files"] if item["id"] == "graph_archive"), None)
    if archive and "graph" in manifest:
        prepared = assets / f"graph-{archive['sha256']}" / "palimpsest-prepared.json"
        if prepared.exists():
            metadata = parse_json(prepared.read_text())
            require(metadata["archive_sha256"] == archive["sha256"], "asset prepared archive identity mismatch")
            edge = prepared.parent / metadata["edge_path"]
            verify(str(edge.relative_to(assets)), manifest["graph"]["edge_identity"])
            # Reuse the production read-only contract: verify Git source bytes,
            # preserved archive bytes, and their pinned CRLF-to-LF equivalence.
            from palimpsest.assets import _check_mappings
            mappings = manifest["graph"]["mapping_files"]
            _check_mappings(repo, edge.parent, mappings, copy_missing=False)
            for item in mappings:
                verify(str((edge.parent / item["path"]).relative_to(assets)), item.get("archive_identity", item))
                source_paths.append(Path(item["source_path"]))
            asset_hashes[str(prepared.relative_to(assets))] = sha256_file(prepared)
    return {"commit": _git(repo, "rev-parse", "HEAD"), "protocol_sha256": sha256_file(protocol),
            "runtime_source_sha256": {str(p): sha256_file(repo / p) for p in sorted(set(source_paths))},
            "asset_manifest_sha256": {str(manifest_path.relative_to(repo)): sha256_file(manifest_path)},
            "asset_sha256": dict(sorted(asset_hashes.items()))}


def prepare_output_root(path: Path) -> None:
    require(not path.is_symlink(), "output root must not be a symlink")
    if path.exists():
        require(path.is_dir() and not any(path.iterdir()), "output root must be an empty directory; non-empty root refused")
    else:
        path.mkdir(parents=True)


def read_rows(path: Path) -> list[dict[str, object]]:
    data = path.read_text()
    require(not data or data.endswith("\n"), f"incomplete row append: {path}")
    rows = []
    for line in data.splitlines():
        require(bool(line.strip()), f"blank row in {path}")
        row = parse_json(line)
        require(isinstance(row, dict) and isinstance(row.get("unit_id"), str) and bool(row["unit_id"]), "row requires a non-empty unit_id")
        rows.append(row)
    return rows


def append_row(path: Path, row: dict[str, object]) -> None:
    validate_finite(row)
    require(isinstance(row, dict) and isinstance(row.get("unit_id"), str) and bool(row["unit_id"]), "row requires a non-empty unit_id")
    encoded = json.dumps(row, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n"
    # The campaign is sequential; flock also protects accidental parallel appends.
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        existing = read_rows(path)
        ids = [item["unit_id"] for item in existing]
        require(len(ids) == len(set(ids)) and row["unit_id"] not in ids, "duplicate unit_id; retries are undeclared")
        stream.write(encoded)
        stream.flush()
