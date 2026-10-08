"""One-shot admission and execution for navigation-v2 diagnosis amendment v1."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time

import diagnose_male_navigation_v2 as diagnosis


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = REPO_ROOT
AMENDMENT_PATH = REPO_ROOT / "docs/plans/m7-navigation-v2-failure-diagnosis-amendment-v1.json"
AMENDMENT_SHA256 = "94dc0b7ead6942bc13c568f9d8e2c77af7604fe3fbaa5ea55b013f000933c41c"
CLARIFICATION_PATH = REPO_ROOT / "docs/plans/m7-navigation-v2-failure-diagnosis-amendment-v1-clarification.md"
CLARIFICATION_SHA256 = "2d03e2aaedc8ada337a0b8315126eb665c8f6667273ea8306303f8bb7227f588"
FIXED_ANALYZER_SHA256 = "a9242aad83fb69a12fd351eaa9af826bbe1df05be166094f8cb54d944509ace7"
FAILED_ANALYZER_SHA256 = "ce0f9e0126ce31a0c356678386f44097cebe0115332e1967e87d4053737e92c9"
MiB = 1024**2


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _bound(value):
    return {"sha256": _sha(_canonical(value)), "value": value}


def _contract(protocol):
    analysis = protocol["analysis"]
    return {
        "numeric_fields": _bound(analysis["numeric_fields"]),
        "thresholds": _bound(analysis["thresholds"]),
        "case_order": _bound([case["id"] for case in protocol["cases"]]),
        "cases": _bound(protocol["cases"]),
        "per_run_measures": _bound(analysis["per_run_measures"]),
        "classification": _bound(analysis["classification"]),
        "aggregate_by": _bound(analysis["aggregate_by"]),
        "arms": _bound(analysis["arms"]),
        "pairing": _bound(analysis["pairing"]),
        "input": _bound(protocol["input"]),
        "limits": _bound(protocol["limits"]),
    }


def _pinned_local(item, label):
    if not isinstance(item, dict) or set(item) != {"path", "sha256"} or not diagnosis._hex_digest(item["sha256"]):
        raise ValueError(f"invalid {label} binding")
    relative = item["path"]
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError(f"unsafe {label} path")
    path = REPO_ROOT / relative
    payload = diagnosis._read_bytes(path, MiB, label)
    if _sha(payload) != item["sha256"]:
        raise ValueError(f"{label} hash differs")
    return payload


def validate_amendment(value):
    if not isinstance(value, dict) or set(value) != {
            "admission", "execution", "preserved_contract", "prior_attempt",
            "qualification_claims", "schema", "scope", "source_correction", "status"}:
        raise ValueError("amendment fields differ")
    if (value["schema"] != "m7-navigation-v2-failure-diagnosis-amendment-v1" or
            value["status"] != "prospective-frozen-before-amended-trajectory-decode" or
            value["qualification_claims"] != []):
        raise ValueError("amendment identity or claims differ")
    execution = value["execution"]
    if execution != {
            "amended_invocations_allowed": 1,
            "fresh_output_relative": "runs/m7-navigation-v2-failure-diagnosis-amendment-v1-d582eca",
            "global_retained_attempt_ordinal": 2,
            "no_third_attempt": True,
            "on_any_mismatch_or_failure": "retain failure evidence and stop permanently"}:
        raise ValueError("amendment execution boundary differs")
    admission = value["admission"]
    if (admission.get("all_24_owner_results_before_any_trajectory_decode") is not True or
            admission.get("ledger_paths_forbid_scene_ids") != list(range(3120, 3128)) or
            set(admission.get("owner_result_contract", {})) != {"case", "executed_ticks", "outcome", "status"} or
            admission.get("producer_cross_contract") !=
            "run_episode string -> owner_payload JSON -> diagnosis owner-result admission"):
        raise ValueError("amendment owner-result admission differs")
    prior = value["prior_attempt"]
    if not isinstance(prior, dict) or set(prior) != {"original_protocol", "failure", "execution"}:
        raise ValueError("amendment prior-attempt bindings differ")
    for name, expected in {
            "original_protocol": "242fad46433241697bb7d7731e692cd1b42918b3788a8f816c6c8a9e9271b5e3",
            "failure": "850b64c7e5b2200b921a7d20e5f173b4db53796956528cec8f99f060b7cfc474",
            "execution": "4d89617dfe00c2988b75d22c3efad9c7cad45734161b4e5279c09444b72ad8ab"}.items():
        if prior.get(name, {}).get("sha256") != expected:
            raise ValueError(f"amendment {name} pin differs")
        _pinned_local(prior[name], f"prior {name}")
    protocol = diagnosis.load_protocol()
    if value["preserved_contract"] != _contract(protocol):
        raise ValueError("amendment changes the frozen analysis contract")
    correction = value["source_correction"]
    expected_correction = {
        "allowed_changed_lines": 1,
        "before_line": "    outcome = result.get(\"outcome\", {}).get(\"reason\")",
        "diff_sha256": "04aef1aa4f8326d00048b6ea14d61699f7e0fc2e9008111eaea09166e6e063fe",
        "failed": {"commit": "2f0a425b7c541b9d972b7a5d8263b2a85f072340", "sha256": FAILED_ANALYZER_SHA256},
        "after_line": "    outcome = result.get(\"outcome\")",
        "fixed": {"commit": "d582eca99a8526c97e7c8d7ac33d44636c32d070", "sha256": FIXED_ANALYZER_SHA256},
    }
    if correction != expected_correction:
        raise ValueError("amendment source correction differs")
    analyzer = Path(diagnosis.__file__)
    payload = diagnosis._read_bytes(analyzer, MiB, "fixed analyzer source")
    if _sha(payload) != FIXED_ANALYZER_SHA256:
        raise ValueError("fixed analyzer source hash differs")
    text = payload.decode()
    before, after = correction["before_line"], correction["after_line"]
    if text.count(after) != 1 or before in text:
        raise ValueError("fixed analyzer correction is not unique")
    if _sha(text.replace(after, before, 1).encode()) != FAILED_ANALYZER_SHA256:
        raise ValueError("fixed analyzer differs by more than the allowed line")
    clarification = diagnosis._read_bytes(CLARIFICATION_PATH, MiB, "metadata-read clarification")
    if _sha(clarification) != CLARIFICATION_SHA256:
        raise ValueError("metadata-read clarification hash differs")
    return value


def load_amendment(path=AMENDMENT_PATH):
    payload = diagnosis._read_bytes(path, MiB, "amendment protocol")
    if _sha(payload) != AMENDMENT_SHA256:
        raise ValueError("amendment protocol hash differs")
    value = json.loads(payload, object_pairs_hook=diagnosis._pairs, parse_constant=diagnosis._constant)
    return validate_amendment(value)


def validate_ledger_paths(ledger, protocol, amendment):
    if not isinstance(ledger, dict):
        raise ValueError("amendment ledger is not an object")
    run_root = protocol["input"]["run_root_relative"]
    prefix = run_root + "/"
    cases = {case["id"] for case in protocol["cases"]}
    held_out = amendment["admission"]["ledger_paths_forbid_scene_ids"]
    pattern = re.compile(r"(?:^|[-_/])(?:" + "|".join(map(str, held_out)) + r")(?:[-_/.]|$)")
    root_files = {".palimpsest-storage.lock", "progress.json", "report.json"}
    for relative in ledger:
        parts = relative.split("/") if isinstance(relative, str) else []
        if (not isinstance(relative, str) or not relative.startswith(prefix) or
                any(part in {"", ".", ".."} for part in parts) or "\\" in relative):
            raise ValueError("unsafe amended ledger path")
        tail = relative[len(prefix):]
        first = tail.split("/", 1)[0]
        if pattern.search(relative):
            raise ValueError("held-out scene appears in amended ledger")
        if first.startswith("dev-"):
            if first not in cases:
                raise ValueError("unknown development case in amended ledger")
        elif first not in root_files:
            raise ValueError("unexpected root file in amended ledger")
    return True


def admit_owner_result(result, case):
    if not isinstance(result, dict):
        raise ValueError("owner result is not an object")
    if "outcome" not in result:
        raise ValueError("owner result outcome is missing")
    outcome = result["outcome"]
    if type(outcome) is not str:
        raise ValueError("owner result outcome must be a string")
    if outcome not in {"goal", "stalled", "time_limit"}:
        raise ValueError("owner result outcome is invalid")
    expected_case = {key: case[key] for key in ("id", "scene_seed", "training_seed", "arm")}
    if (result.get("status") != "completed-recording" or result.get("case") != expected_case or
            type(result.get("executed_ticks")) is not int or result["executed_ticks"] != case["ticks"] or
            outcome != case["outcome"]):
        raise ValueError("owner result schema or outcome differs from frozen case")
    return outcome


def prevalidate_owner_results(producer, index_path, protocol, amendment, deadline):
    diagnosis._deadline(deadline)
    producer = Path(producer).resolve()
    index, _ = diagnosis._load_index(producer, index_path, protocol)
    ledger = index["copied_root_raw_files"]
    validate_ledger_paths(ledger, protocol, amendment)
    pins = {}
    for case in protocol["cases"]:
        diagnosis._deadline(deadline)
        relative = f"{protocol['input']['run_root_relative']}/{case['id']}/result.json"
        if relative not in ledger:
            raise ValueError("owner result is absent from amended ledger")
        path = diagnosis._safe_file(producer, relative)
        pin = ledger[relative]
        if path.stat().st_size != pin.get("bytes") or diagnosis._file_sha(path) != pin.get("sha256"):
            raise ValueError("owner result differs from amended ledger")
        result = diagnosis._read_json(path, 4 * MiB)
        admit_owner_result(result, case)
        pins[case["id"]] = pin["sha256"]
    if len(pins) != 24:
        raise ValueError("amendment did not prevalidate all 24 owner results")
    return {"owner_results": len(pins), "owner_result_pins_sha256": _sha(_canonical(pins)),
            "trajectory_members_decoded": 0, "held_out_paths": 0}


def _protocol_payload(protocol):
    frozen = diagnosis.load_protocol()
    return diagnosis.PROTOCOL_PATH.read_bytes() if protocol == frozen else _canonical(protocol)


def _write_if_absent(output, name, payload, maximum):
    path = output / name
    if not path.exists():
        diagnosis._write_output(output, name, payload, maximum)


def execute_amendment(producer, index_path, output, protocol, amendment,
                      amendment_payload, clarification_payload):
    diagnosis.validate_protocol(protocol)
    validate_amendment(amendment)
    if (_sha(amendment_payload) != AMENDMENT_SHA256 or
            json.loads(amendment_payload, object_pairs_hook=diagnosis._pairs,
                       parse_constant=diagnosis._constant) != amendment):
        raise ValueError("amendment payload differs")
    if _sha(clarification_payload) != CLARIFICATION_SHA256:
        raise ValueError("clarification payload differs")
    expected = (ROOT / amendment["execution"]["fresh_output_relative"]).resolve(strict=False)
    if Path(output).absolute().resolve(strict=False) != expected:
        raise ValueError("amendment requires the exact fresh output")
    started = time.monotonic()
    deadline = started + protocol["limits"]["deadline_seconds"]
    producer, index_path, output = diagnosis._prepare_output(producer, index_path, output, protocol)
    maximum = protocol["limits"]["max_output_bytes"]
    phase = "publish-contract"
    try:
        diagnosis._write_output(output, "protocol.json", _protocol_payload(protocol), maximum)
        diagnosis._write_output(output, "amendment.json", amendment_payload, maximum)
        diagnosis._write_output(output, "metadata-read-clarification.md", clarification_payload, maximum)
        phase = "prevalidate-owner-results"
        prevalidation = prevalidate_owner_results(producer, index_path, protocol, amendment, deadline)
        phase = "analyze-trajectories"
        analyzer_before = diagnosis._file_sha(Path(diagnosis.__file__))
        runner_before = diagnosis._file_sha(Path(__file__))
        if analyzer_before != FIXED_ANALYZER_SHA256:
            raise ValueError("fixed analyzer source changed before amended analysis")
        report = diagnosis.analyze(producer, index_path, protocol, deadline=deadline)
        analyzer_after = diagnosis._file_sha(Path(diagnosis.__file__))
        runner_after = diagnosis._file_sha(Path(__file__))
        if analyzer_after != analyzer_before or runner_after != runner_before:
            raise ValueError("amended diagnosis source changed during execution")
        report.update({
            "protocol_sha256": _sha(_protocol_payload(protocol)),
            "analysis_source_sha256": analyzer_after,
            "amendment_sha256": AMENDMENT_SHA256,
            "amendment_runner_sha256": runner_after,
            "metadata_read_clarification_sha256": CLARIFICATION_SHA256,
            "amended_attempt": 2,
            "prevalidation": prevalidation,
            "invocation": {"producer_root": str(producer), "development_index": str(index_path),
                           "output": str(output)},
        })
        phase = "publish-report"
        diagnosis._write_output(output, "report.json", report, maximum)
        receipt = {
            "schema": "m7-navigation-v2-failure-diagnosis-amendment-execution-v1",
            "status": "completed-amended-diagnosis",
            "amended_attempt": 2,
            "amendment_sha256": AMENDMENT_SHA256,
            "analysis_source_sha256": analyzer_after,
            "amendment_runner_sha256": runner_after,
            "metadata_read_clarification_sha256": CLARIFICATION_SHA256,
            "protocol_sha256": report["protocol_sha256"],
            "report_sha256": diagnosis._file_sha(output / "report.json"),
            "prevalidation": prevalidation,
            "elapsed_seconds": time.monotonic() - started,
            "held_out_accessed": False,
            "model_or_simulator_executed": False,
            "r3_complete": False,
            "qualification_claims": [],
            "no_third_attempt": True,
        }
        diagnosis._deadline(deadline)
        diagnosis._write_output(output, "amendment-execution.json", receipt, maximum)
        return report
    except BaseException as error:
        (output / "report.json").unlink(missing_ok=True)
        (output / "amendment-execution.json").unlink(missing_ok=True)
        failure = {
            "schema": "m7-navigation-v2-failure-diagnosis-amendment-execution-v1",
            "status": "failed-amended-diagnosis",
            "phase": phase,
            "error": {"type": type(error).__name__, "message": str(error)[:2048]},
            "amended_attempt": 2,
            "amendment_sha256": AMENDMENT_SHA256,
            "metadata_read_clarification_sha256": CLARIFICATION_SHA256,
            "r3_complete": False,
            "qualification_claims": [],
            "no_third_attempt": True,
        }
        _write_if_absent(output, "amendment-failure.json", failure, maximum)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-root", type=Path, required=True)
    parser.add_argument("--index", type=Path, default=diagnosis.PROTOCOL_PATH.parent.parent / "reports/m7-navigation-development-v2.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        amendment_payload = AMENDMENT_PATH.read_bytes()
        clarification_payload = CLARIFICATION_PATH.read_bytes()
        value = load_amendment()
        report = execute_amendment(args.producer_root, args.index, args.output,
                                   diagnosis.load_protocol(), value,
                                   amendment_payload, clarification_payload)
        print(json.dumps({"status": "completed-amended-diagnosis", "runs": len(report["runs"]),
                          "numeric_ticks": report["numeric_ticks"], "output": str(args.output)},
                         sort_keys=True, allow_nan=False))
        return 0
    except BaseException as error:
        print(json.dumps({"status": "failed-amended-diagnosis", "error": str(error)[:2048]},
                         sort_keys=True, allow_nan=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
