"""Pure matched-budget schedule checks; no corpus, Torch, MuJoCo, or simulator."""
from dataclasses import FrozenInstanceError
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

try:
    from palimpsest import male_matched_budget as budget
except ImportError as error:  # RED until Task 1's module exists.
    budget = None
    IMPORT_ERROR = error
else:
    IMPORT_ERROR = None

try:
    import train_male_navigation_v3 as trainer
except ImportError as error:  # RED until Task 2's trainer exists.
    trainer = None
    TRAINER_IMPORT_ERROR = error
else:
    TRAINER_IMPORT_ERROR = None


OLD_ROWS = (277, 182, 315, 245, 199, 265, 243, 257, 67, 67)
AUGMENTED_ROWS = OLD_ROWS + (600, 485, 496, 600, 196, 600, 600, 243, 198, 600, 276, 186)
OLD_REMAINDER = (212, 140, 242, 188, 153, 203, 186, 197, 51, 51)
AUGMENTED_REMAINDER = (111, 73, 127, 99, 80, 107, 98, 103, 27, 27, 242, 195,
                       200, 242, 79, 242, 241, 98, 80, 241, 111, 75)
OLD_PRESENTATIONS = (6029, 3962, 6857, 5333, 4332, 5768, 5289, 5594, 1458, 1458)
AUGMENTED_PRESENTATIONS = (1773, 1165, 2017, 1569, 1274, 1697, 1556, 1645, 429,
                           429, 3842, 3105, 3176, 3842, 1255, 3842, 3841, 1556,
                           1268, 3841, 1767, 1191)


class MatchedBudgetSchedule(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(budget, f"missing pure scheduler: {IMPORT_ERROR}")

    def sources(self, rows):
        return tuple(budget.SourceIdentity(
            run_id=f"{index + 1:032x}", episode=0,
            feature_target_sha256=f"{index + 1:064x}", rows=count)
            for index, count in enumerate(rows))

    def exposures(self, schedule):
        counts = [[0] * source.rows for source in schedule.sources]
        for update in schedule.updates:
            self.assertEqual(sum(piece.stop - piece.start for piece in update.fragments),
                             schedule.rows_per_update)
            for piece in update.fragments:
                for row in range(piece.start, piece.stop):
                    counts[piece.source_index][row] += 1
        return tuple(tuple(source) for source in counts)

    def test_frozen_arms_match_real_row_and_update_budgets(self):
        cases = (
            (OLD_ROWS, 21, 1623, OLD_REMAINDER, OLD_PRESENTATIONS),
            (AUGMENTED_ROWS, 6, 2898, AUGMENTED_REMAINDER, AUGMENTED_PRESENTATIONS),
        )
        schedules = []
        for rows, sweeps, remainder, allocations, presentations in cases:
            schedule = budget.build_schedule(self.sources(rows), seed=10)
            schedules.append(schedule)
            self.assertEqual((schedule.presentations, schedule.rows_per_update), (46080, 32))
            self.assertEqual((schedule.full_sweeps, schedule.remainder_rows), (sweeps, remainder))
            self.assertEqual(schedule.remainder_allocations, allocations)
            self.assertEqual(schedule.source_presentations, presentations)
            self.assertEqual(len(schedule.updates), 1440)
            observed = self.exposures(schedule)
            for index, counts in enumerate(observed):
                self.assertEqual(set(counts), {sweeps, sweeps + 1})
                self.assertEqual(counts.count(sweeps + 1), allocations[index])
                self.assertEqual(sum(counts), presentations[index])
            self.assertEqual(sum(map(sum, observed)), 46080)
        self.assertEqual(schedules[0].remainder_starts,
                         schedules[1].remainder_starts[:len(OLD_ROWS)])

    def test_fragments_mark_source_resets_update_continuations_and_wraps(self):
        sources = self.sources((1, 31, 32, 33))
        schedule = budget.build_schedule(sources, seed=6, presentations=104,
                                         rows_per_update=8)
        self.assertEqual((schedule.full_sweeps, schedule.remainder_rows), (1, 7))
        self.assertEqual(schedule.remainder_allocations, (0, 2, 2, 3))
        self.assertEqual(schedule.remainder_starts, (0, 30, 9, 3))
        self.assertEqual(
            tuple((f.source_index, f.start, f.stop, f.reset_before)
                  for f in schedule.fragments),
            ((0, 0, 1, True), (1, 0, 31, True), (2, 0, 32, True),
             (3, 0, 33, True), (1, 30, 31, True), (1, 0, 1, True),
             (2, 9, 11, True), (3, 3, 6, True)))
        self.assertEqual(
            tuple((f.source_index, f.start, f.stop, f.reset_before)
                  for f in schedule.updates[0].fragments),
            ((0, 0, 1, True), (1, 0, 7, True)))
        self.assertEqual(
            tuple((f.source_index, f.start, f.stop, f.reset_before)
                  for f in schedule.updates[1].fragments),
            ((1, 7, 15, False),))
        replay = budget.build_schedule(sources, seed=6, presentations=104,
                                       rows_per_update=8)
        self.assertEqual(schedule.canonical_bytes(), replay.canonical_bytes())
        self.assertEqual(schedule.sha256,
                         hashlib.sha256(schedule.canonical_bytes()).hexdigest())
        self.assertNotEqual(schedule.canonical_bytes(), budget.build_schedule(
            sources, seed=7, presentations=104, rows_per_update=8).canonical_bytes())
        self.assertEqual(json.loads(schedule.canonical_bytes())["protocol_id"],
                         "M7-NAV-V3-MATCHED-BUDGET-1")
        self.assertNotIn("torch", sys.modules)
        self.assertNotIn("mujoco", sys.modules)

    def test_hamilton_ties_and_invalid_inputs_fail_closed(self):
        tie = budget.build_schedule(self.sources((1, 1, 1)), seed=0,
                                    presentations=4, rows_per_update=2)
        self.assertEqual(tie.remainder_allocations, (1, 0, 0))
        with self.assertRaises(FrozenInstanceError):
            tie.seed = 1
        source = self.sources((2,))[0]
        for operation in (
            lambda: budget.build_schedule((), seed=0, presentations=2, rows_per_update=2),
            lambda: budget.build_schedule((source, source), seed=0, presentations=4,
                                          rows_per_update=2),
            lambda: budget.build_schedule([source], seed=0, presentations=2,
                                          rows_per_update=2),
            lambda: budget.build_schedule((source,), seed=True, presentations=2,
                                          rows_per_update=2),
            lambda: budget.build_schedule((source,), seed=0, presentations=3,
                                          rows_per_update=2),
            lambda: budget.build_schedule((source,), seed=0,
                                          presentations=sys.maxsize + 1,
                                          rows_per_update=1),
            lambda: budget.SourceIdentity("not-hex", 0, "0" * 64, 1),
            lambda: budget.SourceIdentity("0" * 32, 0, "0" * 64, True),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(ValueError):
                    operation()


class MatchedBudgetTrainer(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(trainer, f"missing V3 trainer: {TRAINER_IMPORT_ERROR}")

    @staticmethod
    def manifest():
        def entries(rows, offset=0):
            return [{"run_id": f"{offset + index + 1:032x}", "episode": 0,
                     "ticks": count,
                     "feature_target_sha256": f"{offset + index + 1:064x}"}
                    for index, count in enumerate(rows)]
        old = entries(OLD_ROWS)
        augmented = copy.deepcopy(old) + entries(
            AUGMENTED_ROWS[len(OLD_ROWS):], len(OLD_ROWS))
        development = [
            {"run_id": row["run_id"], "episode": 0, "ticks": row["rows"],
             "feature_target_sha256": row["feature_target_sha256"]}
            for row in trainer.protocol()["corpora"]["recorded_development"]["sequence_order"]
        ]
        return {"arms": {
            "old": {"train": old, "dev": development, "held_out": []},
            "augmented": {"train": augmented, "dev": copy.deepcopy(development),
                          "held_out": []},
        }}

    def test_contract_admits_exact_six_models_and_canonical_schedules(self):
        self.assertEqual(trainer.planned_models(), tuple(
            (seed, arm) for seed in (10, 11, 12)
            for arm in ("old-corpus", "augmented")))
        schedules = trainer.admit_schedules(self.manifest(), 10)
        for arm, expected in (("old-corpus", OLD_PRESENTATIONS),
                              ("augmented", AUGMENTED_PRESENTATIONS)):
            schedule = schedules[arm]
            settings = trainer.fixed_training(10, arm)
            self.assertEqual((settings["real_row_presentations"],
                              settings["optimizer_updates"],
                              settings["selected_optimizer_update"]),
                             (46080, 1440, 1440))
            self.assertEqual(schedule.source_presentations, expected)
            self.assertEqual(len(schedule.updates), 1440)
            self.assertEqual(schedule.sha256,
                             hashlib.sha256(schedule.canonical_bytes()).hexdigest())
        self.assertEqual(schedules["old-corpus"].sources,
                         schedules["augmented"].sources[:len(OLD_ROWS)])

        for mutation in ("old_length", "prefix", "dev", "held_out"):
            changed = self.manifest()
            if mutation == "old_length": changed["arms"]["old"]["train"][0]["ticks"] += 1
            if mutation == "prefix": changed["arms"]["augmented"]["train"][0]["feature_target_sha256"] = "f" * 64
            if mutation == "dev": changed["arms"]["augmented"]["dev"].reverse()
            if mutation == "held_out": changed["arms"]["old"]["held_out"] = [{"forbidden": True}]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                trainer.admit_schedules(changed, 10)

        valid = schedules["old-corpus"]
        with patch.object(budget, "build_schedule", return_value=valid):
            with self.assertRaisesRegex(ValueError, "schedule"):
                trainer.admit_schedules(self.manifest(), 10)

    def prepared_fixture(self):
        import numpy as np

        episodes, sources = [], []
        for index, rows in enumerate((2, 3)):
            features = np.full((rows, 388), index / 10, dtype=np.float32)
            targets = np.full((rows, 2), .1 + index / 10, dtype=np.float32)
            digest = hashlib.sha256(features.tobytes() + targets.tobytes()).hexdigest()
            source = budget.SourceIdentity(f"{index + 1:032x}", 0, digest, rows)
            sources.append(source)
            episodes.append({"run_id": source.run_id, "episode": 0,
                             "features": features, "targets": targets})
        development = [
            {"run_id": row["run_id"], "episode": 0,
             "targets": np.zeros((row["rows"], 2), dtype=np.float32)}
            for row in trainer.protocol()["corpora"]["recorded_development"]["sequence_order"]
        ]
        data = {arm: {"train": copy.deepcopy(episodes),
                      "dev": copy.deepcopy(development), "held_out": []}
                for arm in trainer.ARMS}
        schedules = {arm: types.SimpleNamespace(sources=tuple(sources))
                     for arm in trainer.ARMS}
        return np, data, schedules

    def test_prepared_arrays_reject_nonfinite_wrong_dtype_and_wrong_order(self):
        np, data, schedules = self.prepared_fixture()
        trainer.validate_prepared_data(data, schedules)
        for mutation in ("nonfinite", "dtype", "order"):
            changed = copy.deepcopy(data)
            if mutation == "nonfinite":
                changed["old-corpus"]["train"][0]["targets"][0, 0] = np.nan
            if mutation == "dtype":
                changed["old-corpus"]["train"][0]["features"] = changed[
                    "old-corpus"]["train"][0]["features"].astype(np.float64)
            if mutation == "order":
                changed["old-corpus"]["train"].reverse()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                trainer.validate_prepared_data(changed, schedules)

    def test_update_runner_resets_sources_detaches_continuations_and_steps_once(self):
        schedule = budget.build_schedule(
            (budget.SourceIdentity("1" * 32, 0, "1" * 64, 5),
             budget.SourceIdentity("2" * 32, 0, "2" * 64, 3)),
            seed=10, presentations=8, rows_per_update=4)
        events = []

        class Scalar:
            def __init__(self, value): self.value = value
            def __add__(self, other): return Scalar(self.value + other.value)
            def __truediv__(self, value): return Scalar(self.value / value)
            def backward(self): events.append(("backward", self.value))
            def __float__(self): return float(self.value)

        class Values:
            def __init__(self, count): self.count = count
            def sum(self): return Scalar(self.count)
            def numel(self): return self.count
            def detach(self): return self

        class Hidden:
            def __init__(self, source): self.source = source
            def detach(self): events.append(("detach", self.source)); return self

        class Tensor:
            def __init__(self, rows): self.rows = rows
            def unsqueeze(self, dimension): self.dimension = dimension; return self

        class Model:
            def __init__(self): self.parameter = types.SimpleNamespace(requires_grad=True)
            def parameters(self): return [self.parameter]
            def train(self): events.append("train")
            def reset(self):
                source = sum(event == "reset" for event in events)
                events.append("reset")
                return Hidden(source)
            def __call__(self, inputs, hidden):
                events.append(("forward", tuple(inputs.rows), hidden.source))
                return hidden, object()

        class Optimizer:
            def zero_grad(self, *, set_to_none): events.append("zero_grad")
            def step(self): events.append("step")

        finite = types.SimpleNamespace(all=lambda: True)
        fake_torch = types.SimpleNamespace(
            from_numpy=lambda rows: Tensor(rows), isfinite=lambda value: finite,
            nn=types.SimpleNamespace(utils=types.SimpleNamespace(
                clip_grad_norm_=lambda parameters, cap, error_if_nonfinite: events.append("clip"))))
        data = {"train": [
            {"features": list(range(5)), "targets": list(range(5))},
            {"features": list(range(10, 13)), "targets": list(range(10, 13))},
        ]}
        result = trainer.run_update_units(
            Model(), Optimizer(), data, schedule, fake_torch,
            lambda actions, targets: Values(len(targets.rows)), time.monotonic() + 2,
            resource_check=lambda deadline: events.append("resource"))
        self.assertEqual(result, {"optimizer_updates": 2,
                                  "real_row_presentations": 8,
                                  "train_loss": 1.0})
        self.assertEqual(events.count("reset"), 2)
        self.assertEqual(sum(event == "zero_grad" for event in events), 2)
        self.assertEqual([event for event in events if isinstance(event, tuple)
                          and event[0] == "backward"],
                         [("backward", 1.0), ("backward", 1.0)])
        self.assertEqual(sum(event == "clip" for event in events), 2)
        self.assertEqual(sum(event == "step" for event in events), 2)
        self.assertEqual([event for event in events if isinstance(event, tuple)
                          and event[0] == "detach"], [("detach", 0)])
        self.assertEqual([event[1] for event in events if isinstance(event, tuple)
                          and event[0] == "forward"],
                         [(0, 1, 2, 3), (4,), (10, 11, 12)])

    def test_update_runner_rejects_wrong_count_nonfinite_loss_and_parameters(self):
        schedule = budget.build_schedule(
            (budget.SourceIdentity("1" * 32, 0, "1" * 64, 4),),
            seed=10, presentations=4, rows_per_update=4)

        class Tensor:
            def __init__(self, rows): self.rows = rows
            def unsqueeze(self, dimension): return self

        class Hidden:
            def detach(self): return self

        class Scalar:
            finite = True
            def __init__(self, value): self.value = value
            def __truediv__(self, denominator): return Scalar(self.value / denominator)
            def backward(self): pass
            def __float__(self): return float(self.value)

        class Values:
            def __init__(self, count, finite=True): self.count, self.finite = count, finite
            def numel(self): return self.count
            def sum(self): return Scalar(self.count)
            def detach(self): return self

        class Parameter:
            requires_grad = True
            def __init__(self, finite=True): self.finite = finite

        class Model:
            def __init__(self, parameter): self.parameter = parameter
            def parameters(self): return [self.parameter]
            def train(self): pass
            def reset(self): return Hidden()
            def __call__(self, inputs, hidden): return hidden, object()

        optimizer = types.SimpleNamespace(zero_grad=lambda **kwargs: None, step=lambda: None)
        data = {"train": [{"features": list(range(4)), "targets": list(range(4))}]}
        for failure in ("count", "loss", "parameter"):
            parameter = Parameter(finite=failure != "parameter")
            values = Values(3 if failure == "count" else 4, finite=failure != "loss")
            finite = lambda value: types.SimpleNamespace(
                all=lambda: getattr(value, "finite", True))
            fake_torch = types.SimpleNamespace(
                from_numpy=lambda rows: Tensor(rows), isfinite=finite,
                nn=types.SimpleNamespace(utils=types.SimpleNamespace(
                    clip_grad_norm_=lambda *args, **kwargs: None)))
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                trainer.run_update_units(
                    Model(parameter), optimizer, data, schedule, fake_torch,
                    lambda actions, targets: values, time.monotonic() + 2,
                    resource_check=lambda deadline: None)

    def test_terminal_state_is_copied_before_recorded_development_evaluation(self):
        events = []

        class State:
            def __init__(self, value): self.value = value
            def detach(self): return self
            def cpu(self): return self
            def clone(self):
                events.append(("clone", self.value))
                return State(self.value)

        class Parameter:
            requires_grad = True
            def numel(self): return 1

        state = State(7)
        model = types.SimpleNamespace(
            parameters=lambda: [Parameter()],
            named_parameters=lambda: [("weight", Parameter())],
            state_dict=lambda: {"weight": state})
        torch_module = types.SimpleNamespace(
            optim=types.SimpleNamespace(Adam=lambda parameters, lr: object()))
        schedule = types.SimpleNamespace(updates=(object(), object()), presentations=8)

        def evaluate(model, development, deadline, settings):
            events.append(("evaluate", state.value))
            state.value = 99
            return {"ticks": 1228, "loss": .1, "velocity_mae": .2,
                    "wrapped_heading_mae_radians": .3}

        with (patch.object(trainer.fitter, "make_model", return_value=model),
              patch.object(trainer, "run_update_units", return_value={
                  "optimizer_updates": 2, "real_row_presentations": 8,
                  "train_loss": .1}),
              patch.object(trainer.fitter, "evaluate", side_effect=evaluate)):
            _, terminal, result = trainer.fit_terminal(
                {}, {"dev": object()}, Path("cell"), schedule,
                {"training_seed": 10, "learning_rate": .001}, torch_module,
                time.monotonic() + 2)
        self.assertEqual(events, [("clone", 7), ("evaluate", 7)])
        self.assertEqual(terminal["weight"].value, 7)
        self.assertEqual(result["selected_optimizer_update"], 2)
        self.assertEqual(state.value, 99)

    def test_attempt_is_durable_fresh_and_failure_keeps_later_arm_not_started(self):
        class Budget:
            def check(self, additional, *, path): return {"additional_bytes": additional}

        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            output = parent / "seed-10"
            receipt = trainer.reserve_attempt(output, 10, time.monotonic() + 2, Budget())
            self.assertTrue(Path(receipt["path"]).is_file())
            self.assertFalse(output.exists())
            with self.assertRaises(FileExistsError):
                trainer.reserve_attempt(output, 10, time.monotonic() + 2, Budget())

            report = trainer.initial_report(10, receipt)
            report["models"]["old-corpus"] = {"status": "failed"}
            trainer.publish_failure(output, report, ValueError("first arm failed"),
                                    time.monotonic() + 2, Budget())
            retained = json.loads((parent / "seed-10.failure.json").read_text())
            self.assertEqual(retained["models"]["augmented"]["status"], "not_started")
            self.assertEqual(retained["error"]["type"], "ValueError")
            self.assertFalse((output / "report.json").exists())

    def test_output_preflight_rejects_overlap_stale_and_consumed_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            managed, inputs = root / "managed", root / "inputs"
            managed.mkdir(); inputs.mkdir()
            study = {"immutable_inputs": {"fixture": {"path": str(inputs / "data.json")}}}
            output = managed / "seed-10"
            self.assertEqual(trainer.preflight_output(output, 10, study), output)

            with self.assertRaisesRegex(ValueError, "overlaps"):
                trainer.preflight_output(inputs / "seed-10", 10, study)
            for consumed in (output, trainer._attempt_path(output), trainer._failure_path(output)):
                if consumed == output:
                    consumed.mkdir()
                else:
                    consumed.write_text("consumed")
                with self.subTest(consumed=consumed), self.assertRaises(FileExistsError):
                    trainer.preflight_output(output, 10, study)
                if consumed == output:
                    consumed.rmdir()
                else:
                    consumed.unlink()

    def test_graph_cell_and_loaded_source_drift_stop_before_torch(self):
        class FakeBudget:
            def __init__(self, *args, **kwargs): pass
            def check(self, additional, *, path): return {}
            def lock(self): return self
            def __enter__(self): return self
            def __exit__(self, *args): return None

        admitted = trainer.source_identity(time.monotonic() + 5)
        pinned_name = next(iter(trainer.protocol()["behavior_source_admission"]["existing_hashes"]))
        def changed_hash(path, *args):
            name = Path(path).relative_to(trainer.ROOT).as_posix()
            return "0" * 64 if name == pinned_name else admitted[name]
        with patch.object(trainer.data_reader, "file_sha", side_effect=changed_hash):
            with self.assertRaisesRegex(ValueError, "Pinned local behavior"):
                trainer.source_identity(time.monotonic() + 5)

        study = trainer.protocol()
        args = types.SimpleNamespace(
            graph=Path(study["immutable_inputs"]["graph"]["path"]),
            graph_manifest=Path(study["immutable_inputs"]["graph_manifest"]["path"]),
            cell_source=Path(study["immutable_inputs"]["cell_source"]["path"]))
        expected = {
            str(Path(os.path.abspath(args.graph))):
                study["immutable_inputs"]["graph"]["sha256"],
            str(Path(os.path.abspath(args.graph_manifest))):
                study["immutable_inputs"]["graph_manifest"]["sha256"],
            str(Path(os.path.abspath(args.cell_source))):
                study["immutable_inputs"]["cell_source"]["sha256"],
        }
        graph = {"source_graph_sha256": study["training"]["model"]["graph_sha256"],
                 "graph_manifest_sha256":
                     study["immutable_inputs"]["graph_manifest"]["sha256"]}
        context = {"model_inputs": expected}
        trainer.admit_model_context(graph, context, args)
        for drift in ("graph", "graph-manifest", "cell", "path"):
            changed_graph, changed_context = copy.deepcopy(graph), copy.deepcopy(context)
            if drift == "graph":
                changed_graph["source_graph_sha256"] = "0" * 64
            elif drift == "path":
                changed_args = copy.copy(args)
                changed_args.cell_source = Path("/fixture/substitute-cell")
            else:
                path = args.graph_manifest if drift == "graph-manifest" else args.cell_source
                changed_context["model_inputs"][str(Path(os.path.abspath(path)))] = "0" * 64
            with self.subTest(model_drift=drift), self.assertRaises(ValueError):
                trainer.admit_model_context(
                    changed_graph, changed_context,
                    changed_args if drift == "path" else args)

        for drift in ("graph", "cell", "source"):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "seed-10"
                args = types.SimpleNamespace(training_seed=10, output=output,
                                             graph=Path("graph"), graph_manifest=Path("manifest"),
                                             cell_source=Path("cell"))
                calls = 0

                def sources(deadline, expected=None):
                    nonlocal calls
                    calls += 1
                    if drift == "source" and calls == 2:
                        raise ValueError("loaded source drift")
                    return {}

                fake_v2 = types.SimpleNamespace(
                    prepare=lambda args, deadline: (_ for _ in ()).throw(
                        ValueError(drift + " drift")))
                with (patch.object(trainer, "StorageBudget", FakeBudget),
                      patch.object(trainer, "check_resources", return_value=0),
                      patch.object(trainer, "source_identity", side_effect=sources),
                      patch.object(trainer, "pre_runtime", return_value={}),
                      patch.object(trainer, "_load_v2", return_value=fake_v2),
                      patch.object(trainer, "_load_torch",
                                   side_effect=AssertionError("Torch crossed failed admission"))):
                    with self.assertRaisesRegex(ValueError, "drift"):
                        trainer.train(args)
                self.assertTrue(trainer._attempt_path(output).is_file())
                retained = json.loads(trainer._failure_path(output).read_text())
                self.assertEqual(retained["models"]["old-corpus"]["status"], "not_started")
                self.assertEqual(retained["models"]["augmented"]["status"], "not_started")

    def test_storage_file_and_pair_caps_stop_before_torch(self):
        class RejectingBudget:
            def __init__(self, *args, **kwargs): pass
            def lock(self): return self
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def check(self, additional, *, path): raise RuntimeError("storage cap")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "seed-10"
            args = types.SimpleNamespace(training_seed=10, output=output,
                                         graph=Path("graph"), graph_manifest=Path("manifest"),
                                         cell_source=Path("cell"))
            with (patch.object(trainer, "StorageBudget", RejectingBudget),
                  patch.object(trainer, "check_resources", return_value=0),
                  patch.object(trainer, "source_identity", return_value={}),
                  patch.object(trainer, "pre_runtime", return_value={}),
                  patch.object(trainer, "_load_v2",
                               side_effect=AssertionError("input admission crossed storage cap"))):
                with self.assertRaisesRegex(RuntimeError, "storage cap"):
                    trainer.train(args)
            self.assertFalse(trainer._attempt_path(output).exists())

        class Budget:
            def check(self, additional, *, path): return {}

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oversized"
            with self.assertRaisesRegex(ValueError, "byte cap"):
                trainer._write_artifact(path, b"xx", time.monotonic() + 2, Budget(), 1)
            self.assertFalse(path.exists())

        class FakeBudget(Budget):
            def __init__(self, *args, **kwargs): pass
            def lock(self): return self
            def __enter__(self): return self
            def __exit__(self, *args): return None

        class Schedule:
            sha256 = "a" * 64
            def canonical_bytes(self): return b"{}"

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "seed-10"
            args = types.SimpleNamespace(training_seed=10, output=output,
                                         graph=Path("graph"), graph_manifest=Path("manifest"),
                                         cell_source=Path("cell"))
            fake_v2 = types.SimpleNamespace(
                prepare=lambda args, deadline: (
                    output, {arm: object() for arm in trainer.ARMS},
                    {"ordered_ids_sha256": "ids"}, {"manifest": {}, "model_inputs": {}}),
                check_context=lambda *args, **kwargs: None,
                write_artifact=trainer._write_artifact)
            with (patch.object(trainer, "PAIR_BYTES", 16),
                  patch.object(trainer, "StorageBudget", FakeBudget),
                  patch.object(trainer, "check_resources", return_value=0),
                  patch.object(trainer, "source_identity", return_value={}),
                  patch.object(trainer, "pre_runtime", return_value={}),
                  patch.object(trainer, "_load_v2", return_value=fake_v2),
                  patch.object(trainer, "admit_model_context"),
                  patch.object(trainer, "admit_schedules",
                               return_value={arm: Schedule() for arm in trainer.ARMS}),
                  patch.object(trainer, "validate_prepared_data"),
                  patch.object(trainer, "_load_torch",
                               side_effect=AssertionError("Torch crossed pair cap"))):
                with self.assertRaisesRegex(ValueError, "payload cap"):
                    trainer.train(args)
            self.assertTrue(trainer._failure_path(output).is_file())

    def test_pair_owner_reserves_before_admission_and_stops_after_first_arm_failure(self):
        class FakeBudget:
            def __init__(self, *args, **kwargs): pass
            def check(self, additional, *, path): return {"additional_bytes": additional}
            def lock(self): return self
            def __enter__(self): return self
            def __exit__(self, *args): return None

        class Schedule:
            sha256 = "a" * 64
            def canonical_bytes(self): return b"{}"

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "seed-10"
            args = types.SimpleNamespace(training_seed=10, output=output,
                                         graph=Path("graph"), graph_manifest=Path("manifest"),
                                         cell_source=Path("cell"))
            calls = []

            def load_v2():
                self.assertTrue((Path(directory) / "seed-10.attempt.json").is_file())
                calls.append("admission")
                return types.SimpleNamespace(
                    prepare=lambda args, deadline: (
                        output, {arm: object() for arm in trainer.ARMS},
                        {"ordered_ids_sha256": "ids"},
                        {"manifest": {}, "model_inputs": {}}),
                    check_context=lambda *args, **kwargs: None,
                    write_artifact=trainer._write_artifact,
                    stage_report=lambda root, report, deadline, budget: trainer._write_artifact(
                        root / "report.pending", b"{}", deadline, budget, trainer.MAX_JSON),
                    publish_report=lambda *args, **kwargs: self.fail("failed pair published success"))

            def load_torch():
                self.assertTrue((output / "old-corpus-schedule.json").is_file())
                self.assertTrue((output / "augmented-schedule.json").is_file())
                calls.append("torch")
                return types.SimpleNamespace(
                    set_num_threads=lambda value: None,
                    use_deterministic_algorithms=lambda value: None)

            def fail_fit(*args, **kwargs):
                calls.append("old-corpus")
                raise ValueError("injected first-arm failure")

            with (patch.object(trainer, "StorageBudget", FakeBudget),
                  patch.object(trainer, "check_resources", return_value=0),
                  patch.object(trainer, "source_identity", return_value={}),
                  patch.object(trainer, "pre_runtime", return_value={}),
                  patch.object(trainer, "_load_v2", side_effect=load_v2),
                  patch.object(trainer, "admit_model_context"),
                  patch.object(trainer, "admit_schedules",
                               return_value={arm: Schedule() for arm in trainer.ARMS}),
                  patch.object(trainer, "validate_prepared_data"),
                  patch.object(trainer, "_load_torch", side_effect=load_torch),
                  patch.object(trainer, "cpu_runtime", return_value={}),
                  patch.object(trainer, "fit_terminal", side_effect=fail_fit)):
                with self.assertRaisesRegex(ValueError, "first-arm failure"):
                    trainer.train(args)
            self.assertEqual(calls, ["admission", "torch", "old-corpus"])
            failure = json.loads((Path(directory) / "seed-10.failure.json").read_text())
            self.assertEqual(failure["models"]["old-corpus"]["status"], "failed")
            self.assertEqual(failure["models"]["augmented"]["status"], "not_started")
            self.assertFalse((output / "report.json").exists())

    def test_v3_success_requires_report_rename_directory_sync_and_completion_receipt(self):
        class Budget:
            def check(self, additional, *, path): return {}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "seed-10"
            trainer.reserve_attempt(output, 10, time.monotonic() + 2, Budget())
            output.mkdir()
            payload = json.dumps({
                "status": "completed-navigation-v3-training",
                "training_completed": True,
                "models": {arm: {"status": "completed"} for arm in trainer.ARMS},
                "held_out_status": "locked_unopened",
                "qualification_claims": [],
            }, sort_keys=True, separators=(",", ":")).encode()
            staged = trainer._write_artifact(output / "report.pending", payload,
                                             time.monotonic() + 2, Budget(), trainer.MAX_JSON)
            completion = trainer.publish_success(
                output, time.monotonic() + 2, lambda: None, Budget(), staged)
            self.assertTrue((output / "report.json").is_file())
            self.assertTrue((output / "publication.json").is_file())
            self.assertFalse((output / "report.pending").exists())
            self.assertEqual(completion["report_sha256"], staged["sha256"])
            self.assertTrue(trainer.success_admitted(output, staged["sha256"]))

    def test_publication_faults_are_retained_and_never_admitted(self):
        class FakeBudget:
            def __init__(self, *args, **kwargs): pass
            def check(self, additional, *, path): return {}
            def lock(self): return self
            def __enter__(self): return self
            def __exit__(self, *args): return None

        class Schedule:
            sha256 = "a" * 64
            def canonical_bytes(self): return b"{}"

        real_replace = Path.replace
        real_sync = trainer._fsync_directory
        for failure in ("report-rename", "completion-rename", "report-fsync",
                        "completion-fsync", "final-source", "final-runtime"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "seed-10"
                args = types.SimpleNamespace(training_seed=10, output=output,
                                             graph=Path("graph"), graph_manifest=Path("manifest"),
                                             cell_source=Path("cell"))
                runtime_calls = 0

                def context(context, deadline, receipt, budget):
                    if failure == "final-source" and Path(receipt).name == "after-final-sync.json":
                        raise ValueError("injected final source drift")

                fake_v2 = types.SimpleNamespace(
                    prepare=lambda args, deadline: (
                        output, {arm: object() for arm in trainer.ARMS},
                        {"ordered_ids_sha256": "ids"},
                        {"manifest": {}, "model_inputs": {}}),
                    check_context=context,
                    write_artifact=trainer._write_artifact,
                    stage_report=lambda root, report, deadline, budget: trainer._write_artifact(
                        root / "report.pending", trainer.male_model.canonical(report),
                        deadline, budget, trainer.MAX_JSON),
                    publish_report=lambda *args, **kwargs: self.fail(
                        "V3 used the non-durable historical publisher"))

                fake_torch = types.SimpleNamespace(
                    set_num_threads=lambda value: None,
                    use_deterministic_algorithms=lambda value: None,
                    save=lambda checkpoint, stream: stream.write(b"checkpoint"))

                def runtime(torch_module):
                    nonlocal runtime_calls
                    runtime_calls += 1
                    if failure == "final-runtime" and runtime_calls == 2:
                        raise ValueError("injected final runtime drift")
                    return {"runtime": "fixed"}

                def replace(path, target):
                    if (failure == "report-rename" and Path(path).name == "report.pending") or (
                            failure == "completion-rename" and
                            Path(path).name == "publication.pending"):
                        raise OSError("injected publication rename failure")
                    return real_replace(path, target)

                output_syncs = 0
                def sync(path):
                    nonlocal output_syncs
                    if Path(path) == output:
                        output_syncs += 1
                    if ((failure == "report-fsync" and output_syncs == 1) or
                            (failure == "completion-fsync" and output_syncs == 2)):
                        raise OSError("injected publication directory fsync failure")
                    return real_sync(path)

                fit = lambda *args, **kwargs: (
                    object(), {"weight": 1},
                    {"optimizer_updates": 1440, "real_row_presentations": 46080,
                     "selected_optimizer_update": 1440,
                     "selected_real_row_presentations": 46080,
                     "trainable_names": ["weight"], "recorded_development": {"ticks": 1228}})
                with (patch.object(trainer, "StorageBudget", FakeBudget),
                      patch.object(trainer, "check_resources", return_value=0),
                      patch.object(trainer, "source_identity", return_value={}),
                      patch.object(trainer, "pre_runtime", return_value={}),
                      patch.object(trainer, "_load_v2", return_value=fake_v2),
                      patch.object(trainer, "admit_model_context"),
                      patch.object(trainer, "admit_schedules",
                                   return_value={arm: Schedule() for arm in trainer.ARMS}),
                      patch.object(trainer, "validate_prepared_data"),
                      patch.object(trainer, "_load_torch", return_value=fake_torch),
                      patch.object(trainer, "cpu_runtime", side_effect=runtime),
                      patch.object(trainer, "fit_terminal", side_effect=fit),
                      patch.object(Path, "replace", new=replace),
                      patch.object(trainer, "_fsync_directory", side_effect=sync)):
                    with self.assertRaises((OSError, ValueError)):
                        trainer.train(args)
                self.assertTrue(trainer._failure_path(output).is_file())
                self.assertFalse(trainer.success_admitted(output))
                self.assertEqual((output / "publication.json").exists(),
                                 failure == "completion-fsync")

    def test_admission_stops_before_heavy_import_on_limits_or_heldout_cli(self):
        with patch.object(trainer, "rss_bytes", return_value=trainer.GiB + 1):
            with self.assertRaisesRegex(MemoryError, "RSS"):
                trainer.check_resources(time.monotonic() + 2)
        with self.assertRaises(TimeoutError): trainer.check_resources(0)

        fake_torch = types.SimpleNamespace(
            __version__="2.9.0+cu128", get_num_threads=lambda: 1,
            cuda=types.SimpleNamespace(is_initialized=lambda: False))
        version = lambda name: "2.2.5" if name == "numpy" else "2.9.0"
        with (patch.object(trainer.platform, "python_version", return_value="3.11.15"),
              patch.object(trainer.importlib.metadata, "version", side_effect=version),
              patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": ""}),
              patch.dict(sys.modules, {"torch": fake_torch})):
            self.assertEqual(trainer.cpu_runtime(fake_torch)["torch_build"], "2.9.0+cu128")

        env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(Path(__file__).resolve().parents[1] / "src"),
                                                              str(Path(__file__).resolve().parents[1] / "scripts")))}
        command = "import train_male_navigation_v3,sys; assert not ({'torch','mujoco'} & set(sys.modules))"
        imported = subprocess.run([sys.executable, "-c", command], env=env,
                                  capture_output=True, text=True, timeout=15)
        self.assertEqual(imported.returncode, 0, imported.stderr[-1000:])
        rejected = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/train_male_navigation_v3.py"),
             "--training-seed", "10", "--output", "unused", "--held-out", "3120"],
            env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(rejected.returncode, 2)
        self.assertFalse(Path("unused").exists())


if __name__ == "__main__":
    unittest.main()
