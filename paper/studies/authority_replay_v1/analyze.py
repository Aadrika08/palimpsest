"""Pure deterministic analysis: validate the whole denominator before summarizing."""
import argparse
import csv
import json
from pathlib import Path
import statistics

if __package__:
    from .common import (Protocol, STATUSES, declared_units, load_protocol, parse_json,
                         prepare_output_root, read_rows, require, validate_finite)
else:
    from common import (Protocol, STATUSES, declared_units, load_protocol, parse_json,
                        prepare_output_root, read_rows, require, validate_finite)


OUTCOME_FLAGS = ("silent_acceptance", "explicit_detection", "correct_recovery", "benign_false_rejection")


def _validate_identity(identity: dict[str, object]) -> None:
    expected = {"commit", "protocol_sha256", "runtime_source_sha256", "asset_manifest_sha256", "asset_sha256"}
    require(isinstance(identity, dict) and set(identity) == expected, "invalid campaign identity fields")

    def digest(value: object, length: int) -> bool:
        return isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value)

    require(digest(identity["commit"], 40) and digest(identity["protocol_sha256"], 64), "invalid campaign identity digest")
    for name in ("runtime_source_sha256", "asset_manifest_sha256", "asset_sha256"):
        values = identity[name]
        require(isinstance(values, dict) and bool(values)
                and all(isinstance(k, str) and bool(k) and digest(v, 64) for k, v in values.items()), f"invalid campaign identity: {name}")


def _validate_rows(protocol: Protocol, rows: list[dict[str, object]], identity: dict[str, object]) -> list[dict[str, object]]:
    _validate_identity(identity)
    require(identity["protocol_sha256"] == protocol._content_sha256,
            "campaign identity does not match loaded protocol bytes")
    expected = {u["unit_id"]: u for u in declared_units(protocol)}
    indexed = {}
    for row in rows:
        validate_finite(row)
        require(isinstance(row, dict), "row must be an object")
        unit_id = row.get("unit_id")
        require(isinstance(unit_id, str) and unit_id in expected, f"undeclared unit: {unit_id}")
        require(unit_id not in indexed, f"duplicate unit: {unit_id}")
        require(type(row.get("schema_version")) is int and row["schema_version"] == protocol.schema_version, "row schema mismatch")
        require(row.get("study_id") == protocol.study_id, "row study mismatch")
        require(row.get("identity") == identity, f"campaign identity drift: {unit_id}")
        require(row.get("status") in STATUSES, f"invalid row status: {unit_id}")
        require(isinstance(row.get("metrics"), dict), f"metrics must be an object: {unit_id}")
        for name in OUTCOME_FLAGS:
            require(name not in row or type(row[name]) is bool, f"semantic outcome flag must be boolean: {name}")
        for name, value in expected[unit_id].items():
            require(row.get(name) == value and type(row.get(name)) is type(value), f"unit descriptor mismatch: {unit_id}/{name}")
        indexed[unit_id] = row
    require(set(indexed) == set(expected), f"missing declared units: {sorted(set(expected) - set(indexed))}")
    return [indexed[unit_id] for unit_id in expected]


def load_complete_rows(protocol: Protocol, row_paths: list[Path], identity: dict[str, object]) -> list[dict[str, object]]:
    rows = [row for path in row_paths for row in read_rows(path)]
    return _validate_rows(protocol, rows, identity)


def _statistics(values: list[float]) -> dict[str, object]:
    if len(values) == 1:
        q1 = q3 = values[0]
    else:
        q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return {"n": len(values), "median": statistics.median(values), "minimum": min(values),
            "maximum": max(values), "q1": q1, "q3": q3, "iqr": q3 - q1}


def summarize(protocol: Protocol, rows: list[dict[str, object]]) -> dict[str, object]:
    require(bool(rows), "campaign has no rows")
    identity = rows[0].get("identity")
    require(isinstance(identity, dict) and bool(identity), "campaign identity missing")
    ordered = _validate_rows(protocol, rows, identity)
    by_kind = {}
    for kind in dict.fromkeys(row["kind"] for row in ordered):
        group = [row for row in ordered if row["kind"] == kind]
        # All rows remain available; only completed, eligible rows contribute timings.
        eligible = [row for row in group if row["status"] == "completed" and row.get("timing_eligible", True) is True]
        metric_names = sorted({key for row in eligible for key, value in row["metrics"].items() if type(value) in (int, float)})
        metrics = {key: _statistics([row["metrics"][key] for row in eligible if type(row["metrics"].get(key)) in (int, float)])
                   for key in metric_names}
        outcomes = {name: {"true": sum(r.get(name) is True for r in group), "reported": sum(name in r for r in group)} for name in OUTCOME_FLAGS}
        by_kind[kind] = {"denominator": len(group), "status_counts": {s: sum(r["status"] == s for r in group) for s in STATUSES},
                         "semantic_outcomes": outcomes, "metrics": metrics}
    return {"schema_version": 1, "study_id": protocol.study_id, "identity": identity,
            "declared_units": len(ordered), "status_counts": {s: sum(r["status"] == s for r in ordered) for s in STATUSES},
            "by_kind": by_kind, "failures": [r for r in ordered if r["status"] != "completed"], "rows": ordered,
            "statistics_policy": "Completed eligible scalar values only; inclusive quartiles; failures remain in every denominator and raw row set.",
            "reproduction_scope": protocol.offline_reproduction["scope"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--self-check", action="store_true", help="Validate protocol and expansion without producing scientific results.")
    parser.add_argument("--rows", type=Path, nargs="+")
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    protocol = load_protocol(args.protocol)
    if args.self_check:
        units = declared_units(protocol)
        require(len(units) == len({u["unit_id"] for u in units}), "duplicate declared IDs")
        print(f"PASS: {protocol.study_id}: {len(units)} declared units (protocol validation only; no experiment executed)")
        return 0
    if not (args.rows and args.identity and args.output):
        parser.error("analysis requires --rows, --identity and --output")
    identity = parse_json(args.identity.read_text())
    summary = summarize(protocol, load_complete_rows(protocol, args.rows, identity))
    prepare_output_root(args.output)
    for name, value in (("summary.json", summary), ("failures.json", summary["failures"])):
        (args.output / name).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    with (args.output / "rows.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["unit_id", "kind", "status", "row_json"])
        for row in summary["rows"]:
            writer.writerow([row["unit_id"], row["kind"], row["status"], json.dumps(row, sort_keys=True, allow_nan=False)])
    print(f"PASS: validated {summary['declared_units']} rows; wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
