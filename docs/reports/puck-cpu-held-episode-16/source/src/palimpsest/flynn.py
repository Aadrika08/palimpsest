"""A guarded upstream FLYNN bridge, intended for one dedicated worker process."""

import csv
import hashlib
import importlib
from pathlib import Path
import sys

from palimpsest.assets import MAPPING_NAMES, UPSTREAM_COMMIT, sha256_file


def import_upstream(repo_root: Path, module_name: str):
    """Use the upstream import graph in the isolated simulation worker."""
    upstream = (Path(repo_root) / "upstream/fly-gym").resolve()
    if not upstream.is_dir():
        raise FileNotFoundError(f"Missing upstream checkout: {upstream}")
    if str(upstream) not in sys.path:
        sys.path.insert(0, str(upstream))
    module = importlib.import_module(module_name)
    if not Path(module.__file__).resolve().is_relative_to(upstream):
        raise ImportError(f"{module_name} was imported outside pinned upstream: {module.__file__}")
    return module


def _ids_digest(ids):
    digest = hashlib.sha256()
    for neuron_id in ids:
        digest.update(f"{neuron_id}\n".encode("ascii"))
    return digest.hexdigest()


def load_policy(repo_root: Path, edge_path: Path, checkpoint: Path, device: str, seed: int):
    """Reconstruct upstream architecture and reject differing checkpoint graph buffers."""
    import torch

    edge_path, checkpoint = Path(edge_path).resolve(), Path(checkpoint).resolve()
    if not edge_path.is_file() or not checkpoint.is_file():
        raise FileNotFoundError("Verified graph and checkpoint required; run palimpsest assets fetch")
    requested = torch.device(device)
    if requested.type not in {"cpu", "cuda"}:
        raise ValueError("Specify cpu or cuda explicitly; there is no device fallback")
    if requested.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(f"Requested device {device} is unavailable; there is no CPU fallback")
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError("seed must be an integer in [0, 2**63)")
    torch.manual_seed(seed)
    utils = import_upstream(repo_root, "core.utils")
    agent_class = import_upstream(repo_root, "agents.connectome_rnn_agent").ConnectomeAgent
    config = import_upstream(repo_root, "shared_config")
    names = ("photoreceptor_left_csv", "photoreceptor_right_csv", "tactile_left_csv",
             "tactile_right_csv", "descending_neurons_csv", "cell_types_csv", "wind_sensing_csv")
    paths = {key: str(edge_path.parent / name) for key, name in zip(names, MAPPING_NAMES)}
    for path in paths.values():
        if not Path(path).is_file():
            raise FileNotFoundError(f"Required neuron mapping is missing: {path}")
    with open(paths["cell_types_csv"], newline="") as stream:
        columns = csv.DictReader(stream).fieldnames or []
        if not {"primary_type", "type"}.intersection(columns):
            raise ValueError("Cell type mapping has no type column; refusing upstream single-type fallback")
    cell, positions, splits, id2idx = utils.build_connectome_cell(
        edge_path=str(edge_path), device=requested, dtype=config.DTYPE, **paths,
        target_rho=config.TARGET_RHO, leak_alpha=config.LEAK_ALPHA, activation=config.ACTIVATION,
        train_rnn_weights=False, train_readout_head=True,
        batch_chunk=config.BATCH_CHUNK, row_tile_size=config.ROW_TILE_SIZE)
    agent = agent_class(cell, photoreceptor_positions=positions, input_splits=splits,
                        dtype=config.DTYPE, input_scale_init=config.INPUT_SCALE_INIT).to(requested)
    mappings = {}
    for name in MAPPING_NAMES:
        with (edge_path.parent / name).open(newline="") as stream:
            ids = {int(row["root_id"]) for row in csv.DictReader(stream)}
        missing = sorted(ids.difference(id2idx))
        mappings[name] = {"count": len(missing), "ids_sha256": _ids_digest(missing), "sample": missing[:10]}
        if name == "descending_neurons.csv" and not ids.intersection(id2idx):
            raise ValueError("No descending neuron IDs match; refusing upstream first-neuron output fallback")
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if not isinstance(state, dict):
        raise ValueError("Checkpoint must contain the upstream tensor state_dict")
    reconstructed = agent.state_dict()
    structural = [name for name, _ in agent.named_buffers() if name in reconstructed]
    for name in structural:
        expected, found = reconstructed[name].cpu(), state.get(name)
        if not isinstance(found, torch.Tensor) or expected.dtype != found.dtype or not torch.equal(expected, found):
            raise ValueError(f"Checkpoint structural buffer differs from reconstructed graph: {name}")
    agent.load_state_dict(state, strict=True)
    agent.eval()
    agent.requires_grad_(False)
    ordered_ids = sorted(id2idx, key=id2idx.__getitem__)
    provenance = {
        "upstream_commit": UPSTREAM_COMMIT, "seed": seed,
        "requested_device": device, "device": str(agent.device), "dtype": str(config.DTYPE),
        "edge_sha256": sha256_file(edge_path), "checkpoint_sha256": sha256_file(checkpoint),
        "neuron_count": len(ordered_ids), "ordered_neuron_ids_sha256": _ids_digest(ordered_ids),
        "ordered_neuron_ids_encoding": "decimal ID followed by LF, ascending tensor index",
        "mapping_ids_not_in_graph": mappings,
        "unknown_cell_type_count": int((cell.neuron_type_ids == 0).sum().item()),
        "checkpoint_structural_buffers": structural,
        "provenance_limit": "Buffers bind graph structure and mappings; legacy checkpoint contains no original training neuron IDs or training lineage.",
    }
    return FlynnPolicy(agent, agent.device, config.DTYPE, utils.obs_to_torch, provenance)


class FlynnPolicy:
    def __init__(self, agent, device, dtype, reference_converter, provenance):
        import torch
        self.torch = torch
        self.agent, self.device, self.dtype = agent, device, dtype
        self.reference_converter, self.provenance = reference_converter, provenance
        self.failure_diagnostics = {}
        self._current_raw_output = None
        self.agent.cell.register_forward_pre_hook(self._check_input)
        self.agent.cell.register_forward_hook(self._check_output)
        self.reset()

    def reset(self):
        self.hidden = self.torch.zeros(1, self.agent.cell.N, device=self.device, dtype=self.dtype)
        self.agent.reset_vision_state()

    def _finite(self, value, name):
        if not bool(self.torch.isfinite(value).all()):
            self.failure_diagnostics.update({
                "tensor": name, "dtype": str(value.dtype), "shape": list(value.shape),
                "nan_count": int(self.torch.isnan(value).sum().item()),
                "positive_inf_count": int(self.torch.isposinf(value).sum().item()),
                "negative_inf_count": int(self.torch.isneginf(value).sum().item()),
                "sample": self._sample(value),
            })
            if self._current_raw_output is not None:
                self.failure_diagnostics["raw_output"] = self._sample(self._current_raw_output)
            raise ValueError(f"Nonfinite {name}; inference stopped without output sanitization")

    def _sample(self, value):
        return [repr(item) for item in value.detach().reshape(-1)[:8].cpu().tolist()]

    def observation(self, rawobs):
        """Preserve upstream image conversion while allowing only declared sensors."""
        import numpy as np
        torch = self.torch
        result = {}
        for name in ("cam_left", "cam_right"):
            image = rawobs[name]
            if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) <= 0:
                raise ValueError(f"{name} must be a nonempty HWC uint8 RGB image in 0..255")
            result[name] = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0).to(device=self.device).to(dtype=torch.float32)
        sensors = rawobs["sensors"]
        result["sensors"] = {}
        for name in ("collision", "collision_angle", "wind_direction"):
            if name not in sensors:
                raise ValueError(f"Missing declared sensor: {name}")
        for name in ("collision", "collision_angle"):
            raw_value = sensors[name]
            if name == "collision_angle" and raw_value is None:
                raw_value = 0.
            scalar = np.asarray(raw_value)
            if scalar.size != 1 or scalar.dtype.kind not in "biuf":
                raise ValueError(f"{name} must be a numeric scalar")
            value = torch.as_tensor(scalar.reshape(()), device=self.device, dtype=self.dtype).view(1)
            self._finite(value, name)
            result["sensors"][name] = value
        raw_wind = np.asarray(sensors["wind_direction"])
        if raw_wind.shape != (2,) or raw_wind.dtype.kind not in "biuf":
            raise ValueError("wind_direction must be a numeric vector of length 2")
        wind = torch.as_tensor(raw_wind, device=self.device, dtype=self.dtype).view(1, 2)
        self._finite(wind, "wind_direction")
        result["sensors"]["wind_direction"] = wind
        return result

    def _check_input(self, module, inputs):
        hidden, encoded = inputs[:2]
        self._finite(hidden, "incoming hidden state")
        self._finite(encoded, "encoded cell input")
        self._encoded = encoded.detach().clone()

    def _check_output(self, module, inputs, output):
        hidden, raw = output
        self._current_raw_output = raw.detach()
        self._finite(raw, "raw cell output before upstream sanitization")
        self._finite(hidden, "outgoing hidden state")
        if tuple(raw.shape) != (1, 2) or tuple(hidden.shape) != (1, self.agent.cell.N):
            self.failure_diagnostics.update({"tensor": "cell output/hidden state",
                "raw_output_shape": list(raw.shape), "hidden_shape": list(hidden.shape),
                "expected_raw_output_shape": [1, 2], "expected_hidden_shape": [1, self.agent.cell.N],
                "raw_output": self._sample(self._current_raw_output)})
            raise ValueError("Cell output/hidden state shape is incompatible with one policy step")
        self._raw = raw.detach().clone()

    def _clone(self, state):
        if state is None:
            return None
        if isinstance(state, dict):
            return {key: self._clone(value) for key, value in state.items()}
        return state.detach().clone()

    def _state(self):
        return (self.hidden.clone(), self._clone(self.agent.state_vision_left), self._clone(self.agent.state_vision_right))

    def _restore(self, state):
        self.hidden, self.agent.state_vision_left, self.agent.state_vision_right = state

    def _tensors(self, state, prefix=""):
        if isinstance(state, dict):
            for name in sorted(state):
                yield from self._tensors(state[name], f"{prefix}/{name}")
        elif state is not None:
            yield prefix, state

    def _run(self, obs):
        self._finite(self.hidden, "incoming hidden state")
        for eye in (self.agent.state_vision_left, self.agent.state_vision_right):
            for _, value in self._tensors(eye):
                self._finite(value, "incoming retina state")
        x = self.agent.obs_to_x(obs)
        self._finite(x, "photoreceptor input")
        hidden, action = self.agent.step(self.hidden, obs, x=x)
        self._finite(hidden, "final hidden state")
        self._finite(action, "final action")
        for eye in (self.agent.state_vision_left, self.agent.state_vision_right):
            for _, value in self._tensors(eye):
                self._finite(value, "outgoing retina state")
        return hidden, action, self._encoded, self._raw

    def _difference(self, actual, reference):
        if actual.shape != reference.shape or actual.dtype != reference.dtype:
            raise ValueError("Parity tensor shape/dtype mismatch")
        error = float((actual - reference).abs().max().item()) if actual.numel() else 0.
        return bool(self.torch.allclose(actual, reference, atol=1e-6, rtol=1e-6)), error

    def act(self, rawobs, check_parity=False):
        self.failure_diagnostics = {}
        self._current_raw_output = None
        before = self._state()
        parity = {"checked": False}
        try:
            with self.torch.inference_mode():
                restricted = self.observation(rawobs)
                actual = self._run(restricted)
                self.hidden = actual[0]
                after = self._state()
                if check_parity:
                    self._restore(before)
                    reference_obs = self.reference_converter(rawobs, device=self.device, dtype=self.dtype)
                    reference = self._run(reference_obs)
                    self.hidden = reference[0]
                    reference_state = self._state()
                    comparisons = {name: self._difference(actual[index], reference[index])
                                   for name, index in (("hidden", 0), ("action", 1), ("encoded_input", 2), ("raw_output", 3))}
                    for name in ("cam_left", "cam_right"):
                        _, error = self._difference(restricted[name], reference_obs[name])
                        comparisons[name] = (bool(self.torch.equal(restricted[name], reference_obs[name])), error)
                    for index, eye in ((1, "left_retina"), (2, "right_retina")):
                        ours, theirs = list(self._tensors(after[index])), list(self._tensors(reference_state[index]))
                        if [name for name, _ in ours] != [name for name, _ in theirs]:
                            raise ValueError("Parity retina state structure mismatch")
                        for (name, value), (_, ref) in zip(ours, theirs):
                            comparisons[eye + name] = self._difference(value, ref)
                    parity = {"checked": True, "ok": all(value[0] for value in comparisons.values()),
                              "max_abs_errors": {name: value[1] for name, value in comparisons.items()},
                              "atol": 1e-6, "rtol": 1e-6}
                    if not parity["ok"]:
                        raise ValueError(f"Upstream parity failed: {parity}")
                    self._restore(after)
                return {"action": actual[1].squeeze(0).cpu().numpy().copy(),
                        "encoded_input": actual[2].reshape(-1).cpu().numpy().copy(),
                        "raw_output": actual[3].squeeze(0).cpu().numpy().copy(), "parity": parity}
        except BaseException:
            self._restore(before)
            raise
