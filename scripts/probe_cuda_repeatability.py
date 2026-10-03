"""Repeat the pinned recurrent cell's CUDA kernels with frozen inputs in one bounded worker."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

from palimpsest.evaluate import bounded_process


TRIALS = 30
PREFIX_TICKS = 8
WORKSPACE = ":4096:8"


def worker(config):
    if "torch" in sys.modules or os.environ.get("CUBLAS_WORKSPACE_CONFIG") != WORKSPACE:
        raise RuntimeError("A fresh worker with CUBLAS_WORKSPACE_CONFIG=:4096:8 is required before importing torch")
    import numpy as np
    import torch
    import mujoco
    from palimpsest.assets import sha256_file
    from palimpsest.engine import Engine
    from palimpsest.snapshots import _torch_profile

    root, assets, output = (Path(config[key]) for key in ("repo", "assets", "output"))
    torch.use_deterministic_algorithms(False)
    engine = Engine.open(root, assets, output / "recording", controller="flynn", device="cuda", seed=config["seed"])
    results = []
    try:
        engine.submit({"id": "start-prefix", "kind": "run", "expected_state": "paused", "expected_episode": 0})
        for tick in range(PREFIX_TICKS):
            state = engine.advance()
            if state["phase"] != "running" or state["total_tick"] != tick + 1:
                raise RuntimeError(f"Prefix did not execute exactly one nonterminal tick: {state}")
        engine.submit({"id": "pause-for-probe", "kind": "pause", "expected_state": "running", "expected_episode": 0})
        state = engine.advance()
        if state["phase"] != "paused" or state["total_tick"] != PREFIX_TICKS:
            raise RuntimeError(f"Probe boundary is not paused after {PREFIX_TICKS} ticks: {state}")
        engine.writer.flush()

        with torch.inference_mode():
            cell = engine.policy.agent.cell
            hidden = engine.policy.hidden.clone()
            policy_state = engine.policy._state()
            try:
                result = engine.policy.act(engine.observation)
            finally:
                engine.policy._restore(policy_state)
            encoded = torch.as_tensor(result["encoded_input"], device=hidden.device, dtype=hidden.dtype).reshape(1, -1)
            weight = torch.sparse_csr_tensor(cell.W_crow_indices, cell.W_col_indices, cell.W_values,
                                             size=tuple(cell.W_size.tolist()))
            # Freeze this once: index_add trials must not inherit sparse_mm variation.
            pre = torch.sparse.mm(weight, hidden.t()).t() + cell.bias

            def tensor_identity(value):
                return {"shape": list(value.shape), "dtype": str(value.dtype), "device": str(value.device),
                        "sha256": hashlib.sha256(value.detach().cpu().numpy().tobytes()).hexdigest()}

            frozen = {name: tensor_identity(value) for name, value in
                      (("hidden", hidden), ("encoded_input", encoded), ("pre_with_bias", pre), ("input_nodes", cell.input_nodes))}
            operations = (("sparse_mm", lambda: torch.sparse.mm(weight, hidden.t()).t()),
                          ("index_add", lambda: pre.index_add(1, cell.input_nodes, encoded)))
            for deterministic in (False, True):
                torch.use_deterministic_algorithms(deterministic)
                for name, operation in operations:
                    measurement = {"operation": name, "deterministic": deterministic,
                                   "flags": _torch_profile(), "trials_requested": TRIALS,
                                   "trials": 0, "identical_trials": 0, "max_abs_delta": None,
                                   "reference": "first trial; identical_trials includes that first trial"}
                    first = None
                    try:
                        for _ in range(TRIALS):
                            value = operation()
                            if not bool(torch.isfinite(value).all()):
                                raise ValueError("Kernel returned nonfinite values")
                            if first is None:
                                first = value.clone()
                            delta = float((first - value).abs().max().item()) if value.numel() else 0.
                            measurement["max_abs_delta"] = max(measurement["max_abs_delta"] or 0., delta)
                            measurement["identical_trials"] += int(torch.equal(first, value))
                            measurement["trials"] += 1
                        measurement["status"] = "completed"
                    except (RuntimeError, ValueError) as error:
                        measurement.update(status="failed", error={"type": type(error).__name__, "message": str(error)})
                    results.append(measurement)

        events = [json.loads(line) for line in (engine.writer.path / "events.jsonl").read_text().splitlines()]
        source_paths = [Path(__file__).resolve(), root / "uv.lock", root / "model_manifests/flynn-full-vision.json",
                        root / "upstream/fly-gym/models/connectome_rnn_model.py", *sorted((root / "src/palimpsest").glob("*.py"))]
        report = {"schema_version": 1, "status": "completed", "configuration": config,
                  "scope": "Repeated kernels in one process with identical frozen inputs; not a full-policy continuation test",
                  "prefix_ticks": PREFIX_TICKS, "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
                  "prefix_deterministic_algorithms": False, "frozen_inputs": frozen, "measurements": results,
                  "all_operations_completed": all(item["status"] == "completed" for item in results),
                  "versions": {"python": platform.python_version(), "torch": str(torch.__version__),
                               "torch_cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
                               "numpy": np.__version__, "mujoco": mujoco.__version__, "platform": platform.platform()},
                  "device": {"name": torch.cuda.get_device_name(hidden.device),
                             "capability": list(torch.cuda.get_device_capability(hidden.device))},
                  "diagnostics": next(event["report"] for event in events if event["kind"] == "diagnostics"),
                  "source_sha256": {str(path.relative_to(root)): sha256_file(path) for path in source_paths},
                  "provenance": engine.policy.provenance, "run_id": engine.run_id}
    finally:
        torch.use_deterministic_algorithms(False)
        engine.close()
    manifest = json.loads((output / "recording/manifest.json").read_text())
    if manifest["status"] != "completed" or manifest["final_phase"] != "paused":
        raise RuntimeError("Probe recording did not close successfully at its paused boundary")
    with (output / "probe.json").open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new directory; never overwritten")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=180, help="wall seconds including model loading")
    args = parser.parse_args(argv)
    if not 0 <= args.seed < 2**31 or not 1 <= args.timeout <= 3600:
        parser.error("seed must be in [0, 2**31); timeout must be 1–3600 seconds")
    config = {key: str(value.resolve()) if isinstance(value, Path) else value for key, value in vars(args).items()}
    env = os.environ.copy()
    env["CUBLAS_WORKSPACE_CONFIG"] = WORKSPACE
    env.setdefault("MUJOCO_GL", "egl")
    env["OMP_NUM_THREADS"] = "2"
    env["MPLBACKEND"] = "Agg"
    supervisor = bounded_process([sys.executable, str(Path(__file__).resolve()), "--worker", json.dumps(config)],
                                 args.output.resolve(), args.timeout, env)
    if supervisor["status"] != "completed":
        print(json.dumps(supervisor, indent=2))
        return 1
    result = json.loads((args.output / "probe.json").read_text())
    print(json.dumps({"output": config["output"], "measurements": result["measurements"]}, indent=2, allow_nan=False))
    return 0 if result["all_operations_completed"] else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(json.loads(sys.argv[2]))
    else:
        raise SystemExit(main())
