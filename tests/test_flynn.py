import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from palimpsest.flynn import import_upstream, load_policy


REPO = Path(__file__).resolve().parents[1]
HAS_ML = all(importlib.util.find_spec(name) is not None for name in ("torch", "numpy", "pandas"))


class ImportTests(unittest.TestCase):
    def test_module_import_is_lazy(self):
        result = subprocess.run([sys.executable, "-c",
            "import sys; import palimpsest.flynn; "
            "assert not ({'torch', 'numpy', 'pandas', 'mujoco'} & set(sys.modules))"],
            capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(HAS_ML, "simulation dependencies unavailable; run uv sync --extra simulation")
class FlynnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        import torch
        cls.np, cls.torch = np, torch
        cls.temp = tempfile.TemporaryDirectory()
        cls.graph = Path(cls.temp.name)
        cls.edge = cls.graph / "connections_princeton.csv"
        cls.edge.write_text("pre,post,weight\n" + "".join(f"{100+i},{100+(i+1)%12},1\n" for i in range(12)))
        mappings = {
            "visual_column_L1_L2_L3_rear_view_left.csv": "root_id,type,x,y\n100,L1,0,0\n101,L2,0,0\n102,L3,0,0\n999,L1,0,0\n",
            "visual_column_L1_L2_L3_rear_view_right.csv": "root_id,type,x,y\n103,L1,0,0\n104,L2,0,0\n105,L3,0,0\n",
            "head_bristles_left.csv": "root_id\n106\n",
            "head_bristles_right.csv": "root_id\n107\n",
            "descending_neurons.csv": "root_id\n108\n109\n",
            "JO-C_and_JO-E.csv": "root_id\n110\n111\n",
            "consolidated_cell_types.csv": "root_id,primary_type\n" + "".join(f"{100+i},A\n" for i in range(12)),
        }
        for name, text in mappings.items():
            (cls.graph / name).write_text(text)
        cls.utils = import_upstream(REPO, "core.utils")
        agent_class = import_upstream(REPO, "agents.connectome_rnn_agent").ConnectomeAgent
        with contextlib.redirect_stdout(io.StringIO()):
            cell, positions, splits, _ = cls.utils.build_connectome_cell(
                str(cls.edge), torch.device("cpu"), torch.float32,
                photoreceptor_left_csv=str(cls.graph / "visual_column_L1_L2_L3_rear_view_left.csv"),
                photoreceptor_right_csv=str(cls.graph / "visual_column_L1_L2_L3_rear_view_right.csv"),
                tactile_left_csv=str(cls.graph / "head_bristles_left.csv"),
                tactile_right_csv=str(cls.graph / "head_bristles_right.csv"),
                descending_neurons_csv=str(cls.graph / "descending_neurons.csv"),
                cell_types_csv=str(cls.graph / "consolidated_cell_types.csv"),
                wind_sensing_csv=str(cls.graph / "JO-C_and_JO-E.csv"))
        agent = agent_class(cell, positions, splits)
        cls.checkpoint = cls.graph / "fixture.pt"
        torch.save(agent.state_dict(), cls.checkpoint)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.policy = load_policy(REPO, self.edge, self.checkpoint, "cpu", seed=7)
        self.obs = {"cam_left": self.np.full((8, 8, 3), 123, dtype=self.np.uint8),
                    "cam_right": self.np.full((8, 8, 3), 75, dtype=self.np.uint8),
                    "sensors": {"collision": 0, "collision_angle": 0., "wind_direction": [0.5, -0.2],
                                "vec_to_goal": [999., 888.], "vec_left_to_goal": [777., 666.],
                                "vec_right_to_goal": [555., 444.]}}

    def test_loader_records_order_and_structural_identity(self):
        provenance = self.policy.provenance
        self.assertEqual(provenance["neuron_count"], 12)
        self.assertEqual(len(provenance["ordered_neuron_ids_sha256"]), 64)
        self.assertIn("cell.input_nodes", provenance["checkpoint_structural_buffers"])
        self.assertEqual(provenance["mapping_ids_not_in_graph"]["visual_column_L1_L2_L3_rear_view_left.csv"]["count"], 1)

    def test_camera_conversion_matches_reference_without_privileged_sensors(self):
        converted = self.policy.observation(self.obs)
        reference = self.utils.obs_to_torch(self.obs, self.policy.device, self.policy.dtype)
        for eye in ("cam_left", "cam_right"):
            self.assertTrue(self.torch.equal(converted[eye], reference[eye]))
            self.assertEqual(converted[eye].max().item(), 123 if eye == "cam_left" else 75)
        self.assertEqual(set(converted["sensors"]), {"collision", "collision_angle", "wind_direction"})

    def test_parity_preserves_single_step_hidden_and_retinal_evolution(self):
        with contextlib.redirect_stdout(io.StringIO()):
            plain = load_policy(REPO, self.edge, self.checkpoint, "cpu", seed=7)
        for intensity in (123, 13, 209):
            self.obs["cam_left"].fill(intensity)
            actual = self.policy.act(self.obs, check_parity=True)
            expected = plain.act(self.obs)
            self.assertTrue(actual["parity"]["ok"])
            self.np.testing.assert_array_equal(actual["action"], expected["action"])
            self.assertTrue(self.torch.equal(self.policy.hidden, plain.hidden))
            for eye in ("state_vision_left", "state_vision_right"):
                for layer, tensor in getattr(self.policy.agent, eye).items():
                    self.assertTrue(self.torch.equal(tensor, getattr(plain.agent, eye)[layer]))
        self.assertEqual(actual["action"].shape, (2,))
        self.assertEqual(actual["raw_output"].shape, (2,))
        self.assertEqual(actual["encoded_input"].shape, (10,))
        self.assertFalse(self.policy.hidden.requires_grad)

    def test_privileged_sensor_changes_do_not_change_actions(self):
        first = self.policy.act(self.obs)["action"]
        self.policy.reset()
        for name in ("vec_to_goal", "vec_left_to_goal", "vec_right_to_goal"):
            self.obs["sensors"][name] = [float("nan"), float("inf")]
        self.obs["sensors"]["true_pose"] = "must never be inspected"
        second = self.policy.act(self.obs)["action"]
        self.np.testing.assert_array_equal(first, second)

    def test_nonfinite_cell_readout_fails_before_sanitization_and_restores_state(self):
        self.policy.act(self.obs)
        hidden = self.policy.hidden.clone()
        retina = {name: value.clone() for name, value in self.policy.agent.state_vision_left.items()}
        with self.torch.no_grad():
            self.policy.agent.cell.readout_head[-1].bias[0] = float("nan")
        with self.assertRaisesRegex(ValueError, "raw cell output"):
            self.policy.act(self.obs)
        diagnostic = self.policy.failure_diagnostics
        self.assertIn("raw cell output", diagnostic["tensor"])
        self.assertEqual(diagnostic["shape"], [1, 2])
        self.assertEqual(diagnostic["nan_count"], 1)
        self.assertEqual(diagnostic["positive_inf_count"], 0)
        self.assertEqual(diagnostic["negative_inf_count"], 0)
        self.assertIn("nan", diagnostic["raw_output"])
        self.assertLessEqual(len(diagnostic["sample"]), 8)
        json.dumps(diagnostic, allow_nan=False)
        self.assertTrue(self.torch.equal(self.policy.hidden, hidden))
        for name, value in retina.items():
            self.assertTrue(self.torch.equal(self.policy.agent.state_vision_left[name], value))
        with self.torch.no_grad():
            self.policy.agent.cell.readout_head[-1].bias[0] = 0.
        self.policy.act(self.obs)
        self.assertEqual(self.policy.failure_diagnostics, {})

    def test_nonfinite_hidden_is_rejected(self):
        self.policy.hidden[0, 0] = float("inf")
        with self.assertRaisesRegex(ValueError, "hidden"):
            self.policy.act(self.obs)
        self.assertEqual(self.policy.failure_diagnostics["positive_inf_count"], 1)
        self.assertLessEqual(len(self.policy.failure_diagnostics["sample"]), 8)
        json.dumps(self.policy.failure_diagnostics, allow_nan=False)

    def test_wrong_cell_shape_has_bounded_diagnostics(self):
        def wrong_shape(module, inputs, output):
            hidden, raw = output
            return hidden, self.torch.cat([raw, raw[:, :1]], dim=1)
        hook = self.policy.agent.cell.register_forward_hook(wrong_shape, prepend=True)
        self.addCleanup(hook.remove)
        with self.assertRaisesRegex(ValueError, "shape"):
            self.policy.act(self.obs)
        self.assertEqual(self.policy.failure_diagnostics["raw_output_shape"], [1, 3])
        self.assertEqual(len(self.policy.failure_diagnostics["raw_output"]), 3)
        json.dumps(self.policy.failure_diagnostics, allow_nan=False)

    def test_nonfinite_outgoing_hidden_is_rejected_even_with_finite_readout(self):
        with self.torch.no_grad():
            self.policy.agent.cell.bias[0] = float("nan")
        with self.assertRaisesRegex(ValueError, "outgoing hidden"):
            self.policy.act(self.obs)

    def test_finite_raw_output_retains_upstream_action_scaling(self):
        with self.torch.no_grad():
            self.policy.agent.cell.readout_head[-1].weight.zero_()
            self.policy.agent.cell.readout_head[-1].bias[:] = self.torch.tensor([100., -100.])
        result = self.policy.act(self.obs, check_parity=True)
        self.np.testing.assert_array_equal(result["raw_output"], [100., -100.])
        self.assertEqual(result["action"][0], 3.)
        self.assertAlmostEqual(result["action"][1], -self.np.pi, places=6)

    def test_nonfinite_allowed_sensor_is_rejected(self):
        self.obs["sensors"]["wind_direction"] = [float("nan"), 0]
        with self.assertRaisesRegex(ValueError, "wind_direction"):
            self.policy.act(self.obs)

    def test_missing_declared_sensors_are_rejected(self):
        for name in ("collision", "collision_angle", "wind_direction"):
            with self.subTest(sensor=name):
                saved = self.obs["sensors"].pop(name)
                with self.assertRaisesRegex(ValueError, name):
                    self.policy.act(self.obs)
                self.obs["sensors"][name] = saved

    def test_none_collision_angle_matches_upstream_and_numeric_arrays_are_valid(self):
        self.obs["sensors"]["collision_angle"] = None
        self.obs["sensors"]["collision"] = self.np.array([0.])
        self.assertTrue(self.policy.act(self.obs, check_parity=True)["parity"]["ok"])
        self.obs["sensors"]["collision"] = self.np.array([0., 1.])
        with self.assertRaisesRegex(ValueError, "collision.*scalar"):
            self.policy.act(self.obs)

    def test_reset_clears_both_state_kinds(self):
        self.policy.act(self.obs)
        self.policy.reset()
        self.assertEqual(self.policy.hidden.count_nonzero().item(), 0)
        self.assertIsNone(self.policy.agent.state_vision_left)
        self.assertIsNone(self.policy.agent.state_vision_right)

    def test_structural_checkpoint_mismatch_with_equal_shapes_is_rejected(self):
        state = self.torch.load(self.checkpoint, weights_only=True)
        state["cell.input_nodes"] = state["cell.input_nodes"].flip(0)
        bad = self.graph / "wrong-order.pt"
        self.torch.save(state, bad)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "cell.input_nodes"):
            load_policy(REPO, self.edge, bad, "cpu", seed=7)


if __name__ == "__main__":
    unittest.main()
