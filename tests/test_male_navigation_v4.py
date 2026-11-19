"""v4 matched-budget schedule and S1 trainer checks on synthetic tiny corpora only.

No real corpus, graph, checkpoint, simulator or held-out input is opened. Torch is used
only for a tiny synthetic Linear model in the end-to-end trainer fixture.
"""
from dataclasses import FrozenInstanceError
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from palimpsest import male_matched_budget as v3_budget
from palimpsest import male_matched_budget_v4 as budget
import train_male_navigation_v4 as trainer

ROOT = Path(__file__).resolve().parents[1]
V4_DOMAIN = "M7-NAV-V4-REGEN-MATCHED-BUDGET-1"
# v3 reference bytes stay untouched (sha256 at base 7d342b1).
V3_FILES = {
    "src/palimpsest/male_matched_budget.py":
        "79bd896d1a52ebfe8c9b9b82df3d6b25f673d722f10841d56db1d4caebe6fde5",
    "scripts/train_male_navigation_v3.py":
        "9002eafda586e0b1d73578c6af2d3d9ce930e6bb77e205f120d90ea61742ad86",
    "scripts/run_male_navigation_v3_training.py":
        "e49137faed814d4c2de42712b7463bb598be4fc53edce244827287f70c30708c",
    "tests/test_male_navigation_v3.py":
        "a10e8c33636e40f5298e5953461c0a395db33525eac1510896b0a3083117f558",
    "tests/test_male_navigation_v3_execution.py":
        "f39020aa1e77406d356ce7ff0793119b691313724440e849ea1f47294e30ff9d",
}

# v3 sampler fixtures (v2 reference lengths): domain-independent arrays.
OLD_ROWS = (277, 182, 315, 245, 199, 265, 243, 257, 67, 67)
AUGMENTED_ROWS = OLD_ROWS + (600, 485, 496, 600, 196, 600, 600, 243, 198, 600, 276, 186)
OLD_REMAINDER = (212, 140, 242, 188, 153, 203, 186, 197, 51, 51)
AUGMENTED_REMAINDER = (111, 73, 127, 99, 80, 107, 98, 103, 27, 27, 242, 195,
                       200, 242, 79, 242, 241, 98, 80, 241, 111, 75)
OLD_PRESENTATIONS = (6029, 3962, 6857, 5333, 4332, 5768, 5289, 5594, 1458, 1458)
AUGMENTED_PRESENTATIONS = (1773, 1165, 2017, 1569, 1274, 1697, 1556, 1645, 429,
                           429, 3842, 3105, 3176, 3842, 1255, 3842, 3841, 1556,
                           1268, 3841, 1767, 1191)
# v4-domain remainder starts of the same fixture (frozen golden values).
V4_STARTS = {
    10: (91, 111, 27, 190, 70, 60, 81, 236, 61, 58, 119, 390, 280, 400, 50, 293, 107, 138,
         90, 371, 97, 64),
    11: (81, 40, 176, 226, 134, 238, 170, 191, 43, 51, 161, 228, 193, 310, 179, 365, 156,
         12, 119, 132, 262, 27),
    12: (157, 96, 74, 197, 7, 19, 5, 100, 28, 25, 342, 424, 326, 31, 73, 93, 519, 4, 108,
         539, 88, 4),
}


def sources(rows, offset=0):
    return tuple(budget.SourceIdentity(f"{offset + index + 1:032x}", 0,
                                       f"{offset + index + 1:064x}", count)
                 for index, count in enumerate(rows))


def independent_start(seed, source, domain=V4_DOMAIN):
    payload = domain.encode() + b"\0" + str(seed).encode() + b"\0" + source.identity.encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % source.rows


def exposures(schedule):
    counts = [[0] * source.rows for source in schedule.sources]
    for update in schedule.updates:
        assert sum(piece.rows for piece in update.fragments) == schedule.rows_per_update
        for piece in update.fragments:
            for row in range(piece.start, piece.stop):
                counts[piece.source_index][row] += 1
    return tuple(tuple(source) for source in counts)


# --------------------------------------------------------------------------- synthetic corpus

OLD_TINY = (64,) * 8 + (40, 40)
ADVICE_TINY = (64,) * 12
DEV_TINY = (8,) * 4


def manifest_value(old_rows=OLD_TINY, advice_rows=ADVICE_TINY, dev_rows=DEV_TINY, arrays=None):
    """A v4 data manifest; with ``arrays`` (dict) it also fills real float32 sources."""
    def entry(index, rows):
        run_id = f"{index + 1:032x}"
        if arrays is None:
            digest = f"{index + 1:064x}"
        else:
            import numpy as np
            rng = np.random.default_rng(index)
            features = (rng.standard_normal((rows, 388)) * .1).astype(np.float32)
            targets = np.stack([rng.uniform(0, 1, rows), rng.uniform(-.5, .5, rows)], 1).astype(np.float32)
            digest = hashlib.sha256(features.tobytes() + targets.tobytes()).hexdigest()
            arrays[digest + "/features"], arrays[digest + "/targets"] = features, targets
        return {"run_id": run_id, "episode": 0, "ticks": rows, "feature_target_sha256": digest}
    old = [entry(index, rows) for index, rows in enumerate(old_rows)]
    advice = [entry(100 + index, rows) for index, rows in enumerate(advice_rows)]
    dev = [entry(200 + index, rows) for index, rows in enumerate(dev_rows)]
    return {
        "status": "prepared-navigation-advice-research-only", "qualification_claims": [],
        "labels": {"old": "unchanged executed targets", "new": "nav_advice_action"},
        "arms": {"old": {"train": old, "dev": dev, "held_out": []},
                 "augmented": {"train": copy.deepcopy(old) + advice, "dev": copy.deepcopy(dev),
                               "held_out": []}},
        "new_sources": [{"run_id": row["run_id"], "scene_seed": scene, "learner_seed": learner}
                        for row, (scene, learner) in zip(advice, budget.ADVICE_ORDER)],
    }


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def write_corpus(root, with_arrays=True, manifest=None, **pin_changes):
    """Write a synthetic data manifest, array bundle and S0z pin record; return paths."""
    import numpy as np
    root = Path(root)
    arrays = {} if with_arrays else None
    value = manifest_value(arrays=arrays) if manifest is None else manifest
    raw = canonical(value)
    (root / "data-manifest.json").write_bytes(raw)
    stream = io.BytesIO()
    np.savez(stream, **(arrays or {"empty": np.zeros(1, np.float32)}))
    (root / "arrays.npz").write_bytes(stream.getvalue())   # the data child's transient file (not pinned)
    (root / "locator.json").write_bytes(b'{"synthetic": true}')

    def pin(path):
        data = path.read_bytes()
        return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    record = {"schema": trainer.CORPUS_PIN_SCHEMA, "protocol_sha256": trainer.PROTOCOL_SHA256,
              "stage": "S0z", "status": "passed", "qualification_claims": [],
              "data_manifest": pin(root / "data-manifest.json"),
              "reader": {"t_f": {"path": str(root / "t-f"), "head": "a" * 40},
                         "t_h": {"path": str(root / "t-h"), "head": "b" * 40},
                         "locator": pin(root / "locator.json"), "data_root": str(root / "s0f-data")},
              **pin_changes}
    (root / "corpus-pin.json").write_bytes(canonical(record))
    return root / "corpus-pin.json", record, arrays


def write_go(root, pin_path, derivation_sha, name="go.json", **changes):
    value = {"decision": "GO", "lane": "navigation", "stage": "S1",
             "protocol_sha256": trainer.PROTOCOL_SHA256,
             "corpus_pin_sha256": hashlib.sha256(Path(pin_path).read_bytes()).hexdigest(),
             "schedule_derivation_sha256": derivation_sha,
             "granted_by": "fixture owner", "granted_at": "2026-11-09T00:00:00Z", **changes}
    path = Path(root) / name
    path.write_bytes(canonical({k: v for k, v in value.items() if v is not None}))
    return path


class Temp(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)


# --------------------------------------------------------------------------- schedule

class ScheduleV4(unittest.TestCase):
    def test_v3_reference_files_are_unchanged(self):
        for name, digest in V3_FILES.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(v3_budget.PROTOCOL_ID, "M7-NAV-V3-MATCHED-BUDGET-1")

    def test_v3_frozen_arm_fixture_passes_with_v4_domain(self):
        cases = ((OLD_ROWS, 21, 1623, OLD_REMAINDER, OLD_PRESENTATIONS),
                 (AUGMENTED_ROWS, 6, 2898, AUGMENTED_REMAINDER, AUGMENTED_PRESENTATIONS))
        for seed in (10, 11, 12):
            built = []
            for rows, sweeps, remainder, allocations, presentations in cases:
                schedule = budget.build_schedule(sources(rows), seed=seed)
                built.append(schedule)
                self.assertEqual((schedule.presentations, schedule.rows_per_update), (46080, 32))
                self.assertEqual((schedule.full_sweeps, schedule.remainder_rows), (sweeps, remainder))
                self.assertEqual(schedule.remainder_allocations, allocations)
                self.assertEqual(schedule.source_presentations, presentations)
                self.assertEqual(len(schedule.updates), 1440)
                observed = exposures(schedule)
                for index, counts in enumerate(observed):
                    self.assertEqual(set(counts), {sweeps, sweeps + 1})
                    self.assertEqual(counts.count(sweeps + 1), allocations[index])
                    self.assertEqual(sum(counts), presentations[index])
                self.assertEqual(sum(map(sum, observed)), 46080)
                self.assertEqual(schedule.remainder_starts,
                                 tuple(independent_start(seed, s) for s in schedule.sources))
                self.assertEqual(json.loads(schedule.canonical_bytes())["protocol_id"], V4_DOMAIN)
            self.assertEqual(built[1].remainder_starts, V4_STARTS[seed])
            self.assertEqual(built[0].remainder_starts, built[1].remainder_starts[:len(OLD_ROWS)])
            v3 = v3_budget.build_schedule(sources(AUGMENTED_ROWS), seed=seed)
            self.assertNotEqual(v3.remainder_starts, built[1].remainder_starts)
            self.assertNotEqual(v3.sha256, built[1].sha256)

    def test_v4_rule_is_the_v3_rule_except_the_domain_string(self):
        for rows, seed in ((OLD_ROWS, 10), ((1, 31, 32, 33), 6)):
            kwargs = {} if rows == OLD_ROWS else {"presentations": 104, "rows_per_update": 8}
            with patch.object(budget, "PROTOCOL_ID", v3_budget.PROTOCOL_ID):
                same = budget.build_schedule(sources(rows), seed, **kwargs).canonical_bytes()
            self.assertEqual(same, v3_budget.build_schedule(sources(rows), seed, **kwargs).canonical_bytes())

    def test_fragments_mark_source_resets_update_continuations_and_wraps(self):
        fixture = sources((1, 31, 32, 33))
        schedule = budget.build_schedule(fixture, seed=9, presentations=104, rows_per_update=8)
        self.assertEqual((schedule.full_sweeps, schedule.remainder_rows), (1, 7))
        self.assertEqual(schedule.remainder_allocations, (0, 2, 2, 3))
        self.assertEqual(schedule.remainder_starts, (0, 5, 1, 32))
        self.assertEqual(
            tuple((f.source_index, f.start, f.stop, f.reset_before) for f in schedule.fragments),
            ((0, 0, 1, True), (1, 0, 31, True), (2, 0, 32, True), (3, 0, 33, True),
             (1, 5, 7, True), (2, 1, 3, True), (3, 32, 33, True), (3, 0, 2, True)))
        self.assertEqual(tuple((f.source_index, f.start, f.stop, f.reset_before)
                               for f in schedule.updates[0].fragments),
                         ((0, 0, 1, True), (1, 0, 7, True)))
        self.assertEqual(tuple((f.source_index, f.start, f.stop, f.reset_before)
                               for f in schedule.updates[1].fragments), ((1, 7, 15, False),))
        replay = budget.build_schedule(fixture, seed=9, presentations=104, rows_per_update=8)
        self.assertEqual(schedule.canonical_bytes(), replay.canonical_bytes())
        self.assertEqual(schedule.sha256, hashlib.sha256(schedule.canonical_bytes()).hexdigest())
        self.assertNotEqual(schedule.canonical_bytes(), budget.build_schedule(
            fixture, seed=6, presentations=104, rows_per_update=8).canonical_bytes())

    def test_hamilton_ties_and_invalid_inputs_fail_closed(self):
        tie = budget.build_schedule(sources((1, 1, 1)), seed=0, presentations=4, rows_per_update=2)
        self.assertEqual(tie.remainder_allocations, (1, 0, 0))
        with self.assertRaises(FrozenInstanceError):
            tie.seed = 1
        source = sources((2,))[0]
        for operation in (
            lambda: budget.build_schedule((), seed=0, presentations=2, rows_per_update=2),
            lambda: budget.build_schedule((source, source), seed=0, presentations=4, rows_per_update=2),
            lambda: budget.build_schedule([source], seed=0, presentations=2, rows_per_update=2),
            lambda: budget.build_schedule((source,), seed=True, presentations=2, rows_per_update=2),
            lambda: budget.build_schedule((source,), seed=0, presentations=3, rows_per_update=2),
            lambda: budget.build_schedule((source,), seed=0, presentations=sys.maxsize + 1,
                                          rows_per_update=1),
            lambda: budget.SourceIdentity("not-hex", 0, "0" * 64, 1),
            lambda: budget.SourceIdentity("0" * 32, 0, "0" * 64, True),
        ):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                operation()


class DerivationV4(unittest.TestCase):
    def raw(self, value=None):
        raw = canonical(manifest_value() if value is None else value)
        return raw, hashlib.sha256(raw).hexdigest()

    def test_derivation_from_pinned_manifest_is_pure_and_replay_identical(self):
        raw, digest = self.raw()
        first, second = budget.derive(raw, digest), budget.derive(raw, digest)
        self.assertEqual(first["bytes"], second["bytes"])
        self.assertEqual(first["sha256"], hashlib.sha256(first["bytes"]).hexdigest())
        document = first["document"]
        self.assertEqual((document["protocol_id"], document["data_manifest_sha256"]), (V4_DOMAIN, digest))
        self.assertEqual((document["presentations"], document["rows_per_update"],
                          document["optimizer_updates"], document["dev_rows"]), (46080, 32, 1440, 32))
        for arm, rows in (("old-corpus", OLD_TINY), ("augmented", OLD_TINY + ADVICE_TINY)):
            value = document["arms"][arm]
            self.assertEqual(value["N"], sum(rows))
            self.assertEqual((value["q"], value["r"]), divmod(46080, sum(rows)))
            self.assertEqual(sum(value["remainder_allocations"]), value["r"])
            self.assertEqual(sum(value["per_source_totals"]), 46080)
            self.assertEqual(sorted(value["seeds"]), ["10", "11", "12"])
            for seed, item in value["seeds"].items():
                schedule = first["schedules"][int(seed), arm]
                self.assertEqual(item["schedule_sha256"], schedule.sha256)
                self.assertEqual(item["remainder_starts"],
                                 [independent_start(int(seed), s) for s in schedule.sources])
        # A fresh isolated interpreter reproduces the bytes without importing Torch/MuJoCo.
        script = ("import hashlib,sys;from palimpsest import male_matched_budget_v4 as b;"
                  "raw=sys.stdin.buffer.read();d=b.derive(raw,hashlib.sha256(raw).hexdigest());"
                  "print(d['sha256']);print(sorted({'torch','mujoco','numpy'}&set(sys.modules)))")
        child = subprocess.run([sys.executable, "-c", script], input=raw, capture_output=True, check=True,
                               env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
        self.assertEqual(child.stdout.decode().split("\n")[:2], [first["sha256"], "[]"])

    def test_unpinned_v3_or_changed_manifest_bytes_are_refused(self):
        raw, digest = self.raw()
        for operation, message in (
            (lambda: budget.derive(raw + b" ", digest), "pin"),
            (lambda: budget.derive(raw, budget.V3_DATA_SHA256), "47c4523c"),
            (lambda: budget.derive(raw, "0" * 63), "hexadecimal"),
            (lambda: budget.derive(b"not json", hashlib.sha256(b"not json").hexdigest()), "JSON"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                operation()

    def test_structural_admission_refuses_any_other_roster(self):
        def nine_old(v):
            v["arms"]["old"]["train"].pop()
            v["arms"]["augmented"]["train"].pop(9)

        def advice_order(v):
            v["new_sources"][0], v["new_sources"][1] = v["new_sources"][1], v["new_sources"][0]

        def recovery_long(v):
            for arm in ("old", "augmented"):
                v["arms"][arm]["train"][9]["ticks"] = 121

        def advice_long(v):
            v["arms"]["augmented"]["train"][-1]["ticks"] = 601

        def eleven_advice(v):
            v["arms"]["augmented"]["train"].pop()
            v["new_sources"].pop()

        def dev_differs(v):
            v["arms"]["augmented"]["dev"].reverse()

        def three_dev(v):
            for arm in ("old", "augmented"):
                v["arms"][arm]["dev"].pop()

        def prefix(v):
            v["arms"]["augmented"]["train"][0]["feature_target_sha256"] = "f" * 64

        def held_out(v):
            v["arms"]["old"]["held_out"] = [copy.deepcopy(v["arms"]["old"]["dev"][0])]

        def duplicate(v):
            for arm in ("old", "augmented"):
                v["arms"][arm]["dev"][0] = copy.deepcopy(v["arms"]["old"]["train"][0])

        def labels(v):
            v["labels"]["new"] = "relabelled"

        def extra_field(v):
            v["arms"]["old"]["train"][0]["weight"] = 2

        for mutation in (nine_old, advice_order, recovery_long, advice_long, eleven_advice,
                         dev_differs, three_dev, prefix, held_out, duplicate, labels, extra_field):
            value = manifest_value()
            mutation(value)
            raw, digest = self.raw(value)
            with self.subTest(mutation=mutation.__name__), self.assertRaises(ValueError):
                budget.derive(raw, digest)


# --------------------------------------------------------------------------- trainer admission

class TrainerAdmission(Temp):
    def test_protocol_pins_v4_and_refuses_the_v3_protocol(self):
        study = trainer.protocol()
        self.assertEqual(study["id"], V4_DOMAIN)
        with self.assertRaisesRegex(trainer.Refusal, "v3"):
            trainer.protocol(ROOT / "docs/plans/m7-navigation-v3-matched-budget-protocol.json")
        changed = self.root / "protocol.json"
        changed.write_bytes((ROOT / trainer.PROTOCOL_PATH).read_bytes() + b"\n")
        with self.assertRaisesRegex(trainer.Refusal, "pin"):
            trainer.protocol(changed)
        self.assertEqual(trainer.planned_models(),
                         tuple((seed, arm) for seed in (10, 11, 12) for arm in ("old-corpus", "augmented")))
        for seed, arm in trainer.planned_models():
            settings = trainer.fixed_training(seed, arm, study)
            self.assertEqual((settings["real_row_presentations"], settings["rows_per_update"],
                              settings["optimizer_updates"], settings["selected_optimizer_update"],
                              settings["learning_rate"], settings["gradient_norm_cap"]),
                             (46080, 32, 1440, 1440, .001, 1.))
        for seed, arm in ((13, "augmented"), (10, "rewired"), (True, "augmented")):
            with self.assertRaises(trainer.Refusal):
                trainer.fixed_training(seed, arm, study)
        drifted = copy.deepcopy(study)
        drifted["matched_budget"]["optimizer_updates_per_model"] = 1441
        with self.assertRaises(trainer.Refusal):
            trainer.fixed_training(10, "augmented", drifted)

    def test_corpus_pin_refuses_unpinned_v3_and_unpassed_corpora(self):
        path, record, _ = write_corpus(self.root, with_arrays=False)
        admitted, digest = trainer.read_corpus_pin(path)
        self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(admitted, record)
        with self.assertRaisesRegex(trainer.Refusal, "Unpinned"):
            trainer.read_corpus_pin(None)
        v3_manifest = {**record["data_manifest"], "sha256": trainer.V3_DATA_SHA256}
        for changes, message in (
            ({"schema": "m7-navigation-v4-pin-record-1"}, "Unpinned"),
            ({"protocol_sha256": trainer.V3_PROTOCOL_SHA256}, "v3"),
            ({"stage": "S0f"}, "Unpinned"),
            ({"status": "pending"}, "Unpinned"),
            ({"data_manifest": v3_manifest}, "47c4523c"),
            ({"reader": None}, "reader"),
            ({"reader": {"t_f": {"path": "rel", "head": "a" * 40}}}, "reader"),
        ):
            target = self.root / f"pin-{message}-{len(changes)}-{list(changes)[0]}.json"
            target.write_bytes(canonical({**record, **changes}))
            with self.subTest(changes=list(changes)), self.assertRaisesRegex(trainer.Refusal, message):
                trainer.read_corpus_pin(target)
        # The derivation hashes the manifest bytes again; a post-pin rewrite is refused.
        (self.root / "data-manifest.json").write_bytes(canonical(manifest_value()) + b" ")
        with self.assertRaisesRegex(trainer.Refusal, "differ"):
            trainer.derive_schedules(record)
        with self.assertRaisesRegex(trainer.Refusal, "47c4523c"):
            trainer.derive_schedules({**record, "data_manifest": v3_manifest})

    def test_go_names_lane_stage_protocol_pin_and_derivation(self):
        path, record, _ = write_corpus(self.root, with_arrays=False)
        _, pin_sha = trainer.read_corpus_pin(path)
        derivation = trainer.derive_schedules(record)
        go = write_go(self.root, path, derivation["sha256"])
        self.assertEqual(trainer.check_go(go, trainer.PROTOCOL_SHA256, pin_sha, derivation["sha256"]),
                         hashlib.sha256(go.read_bytes()).hexdigest())
        for changes, message in (({"stage": "S2"}, "stage S1"), ({"lane": "puck"}, "lane"),
                                 ({"decision": "NO-GO"}, "GO record"),
                                 ({"protocol_sha256": trainer.V3_PROTOCOL_SHA256}, "v3"),
                                 ({"corpus_pin_sha256": "0" * 64}, "corpus pin"),
                                 ({"schedule_derivation_sha256": "0" * 64}, "derivation"),
                                 ({"granted_by": " "}, "granted_by"), ({"granted_at": None}, "granted_at")):
            bad = write_go(self.root, path, derivation["sha256"], name=f"go-{list(changes)[0]}.json", **changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(trainer.Refusal, message):
                trainer.check_go(bad, trainer.PROTOCOL_SHA256, pin_sha, derivation["sha256"])

    def test_research_stage_detection_needs_the_runner_work_leaf(self):
        cgroup = self.root / "cgroup"
        (self.root / "fs/unit/sup").mkdir(parents=True)
        (self.root / "fs/unit/work").mkdir()
        cgroup.write_text("0::/unit/work\n")
        self.assertTrue(trainer.inside_research_stage(cgroup, str(self.root / "fs")))
        cgroup.write_text("0::/unit\n")
        self.assertFalse(trainer.inside_research_stage(cgroup, str(self.root / "fs")))
        self.assertFalse(trainer.inside_research_stage(self.root / "missing", str(self.root / "fs")))
        self.assertNotIn("cpu.stat", Path(trainer.__file__).read_text())

    def test_plan_only_is_default_and_never_imports_torch_or_opens_arrays(self):
        path, record, _ = write_corpus(self.root, with_arrays=False)
        (self.root / "arrays.npz").unlink()  # Plan-only must not need any array file.
        script = ("import json,sys,io,contextlib;import train_male_navigation_v4 as t;"
                  "out=io.StringIO()\nwith contextlib.redirect_stdout(out): code=t.main(sys.argv[1:])\n"
                  "print(json.dumps({'code':code,'out':json.loads(out.getvalue()),"
                  "'heavy':sorted({'torch','mujoco'}&set(sys.modules))}))")
        env = {**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'scripts'}"}
        for argv in ([], ["--corpus-pin", str(path)], ["--plan-only", "--corpus-pin", str(path)]):
            child = subprocess.run([sys.executable, "-c", script, *argv], capture_output=True,
                                   check=True, env=env)
            value = json.loads(child.stdout.decode().strip().splitlines()[-1])
            with self.subTest(argv=argv):
                self.assertEqual((value["code"], value["out"]["mode"], value["heavy"]), (0, "plan-only", []))
                self.assertEqual(len(value["out"]["models"]), 6)
                if argv:
                    self.assertEqual(value["out"]["schedule_derivation_sha256"],
                                     trainer.derive_schedules(record)["sha256"])

    def test_go_route_refusals_happen_before_any_output_or_torch(self):
        path, record, _ = write_corpus(self.root)
        derivation = trainer.derive_schedules(record)
        go = write_go(self.root, path, derivation["sha256"])
        output = self.root / "s1"
        hooks = types.SimpleNamespace(inside_stage=lambda: False, args=None,
                                      load_torch=lambda: self.fail("Torch imported"))
        cases = (
            (["--plan-only", "--go", str(go), "--corpus-pin", str(path), "--output", str(output)], "exclusive"),
            (["--go", str(go), "--output", str(output)], "Unpinned"),
            (["--go", str(go), "--corpus-pin", str(path)], "--output"),
            (["--go", str(go), "--corpus-pin", str(path), "--output", str(output)], "run_research_stage"),
        )
        for argv, message in cases:
            stdout = io.StringIO()
            with self.subTest(message=message), contextlib.redirect_stdout(stdout):
                self.assertEqual(trainer.main(argv, hooks=hooks), 2)
            self.assertIn(message, json.loads(stdout.getvalue())["reason"])
            self.assertFalse(output.exists())
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                trainer.main(["--held-out"], hooks=hooks)

    def test_array_bundle_must_match_every_pinned_source_exactly(self):
        import numpy as np
        path, record, arrays = write_corpus(self.root)
        rosters = trainer.derive_schedules(record)["rosters"]
        data = trainer.load_arrays(self.root / "arrays.npz", rosters)
        self.assertEqual([len(e["targets"]) for e in data["augmented"]["train"]],
                         list(OLD_TINY + ADVICE_TINY))
        self.assertIs(data["old-corpus"]["dev"], data["augmented"]["dev"])
        for mutation in ("value", "extra", "dtype"):
            changed = dict(arrays)
            key = next(iter(changed))
            if mutation == "value":
                changed[key] = changed[key].copy()
                changed[key][0, 0] += 1
            if mutation == "extra":
                changed["held-out/features"] = np.zeros((1, 388), np.float32)
            if mutation == "dtype":
                changed[key] = changed[key].astype(np.float64)
            stream = io.BytesIO()
            np.savez(stream, **changed)
            target = self.root / f"arrays-{mutation}.npz"
            target.write_bytes(stream.getvalue())
            with self.subTest(mutation=mutation), self.assertRaises(trainer.Refusal):
                trainer.load_arrays(target, rosters)


# --------------------------------------------------------------------------- update runner

class UpdateRunner(unittest.TestCase):
    def test_one_zero_grad_backward_clip_step_per_32_real_rows(self):
        schedule = budget.build_schedule(
            (budget.SourceIdentity("1" * 32, 0, "1" * 64, 50), budget.SourceIdentity("2" * 32, 0, "2" * 64, 30)),
            seed=10, presentations=96, rows_per_update=32)
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
            def detach(self): events.append("detach"); return self

        class Tensor:
            def __init__(self, rows): self.rows = rows
            def unsqueeze(self, dimension): return self

        class Model:
            parameter = types.SimpleNamespace(requires_grad=True)
            def parameters(self): return [self.parameter]
            def train(self): pass
            def reset(self): events.append("reset"); return Hidden()
            def __call__(self, inputs, hidden):
                events.append(("rows", len(inputs.rows)))
                return hidden, None

        class Optimizer:
            def zero_grad(self, *, set_to_none): events.append("zero_grad")
            def step(self): events.append("step")

        finite = types.SimpleNamespace(all=lambda: True)
        fake = types.SimpleNamespace(
            from_numpy=Tensor, isfinite=lambda value: finite,
            nn=types.SimpleNamespace(utils=types.SimpleNamespace(
                clip_grad_norm_=lambda parameters, cap, error_if_nonfinite: events.append(("clip", cap)))))
        data = {"train": [{"features": list(range(50)), "targets": list(range(50))},
                          {"features": list(range(30)), "targets": list(range(30))}]}
        result = trainer.run_update_units(Model(), Optimizer(), data, schedule, fake,
                                          lambda actions, targets: Values(len(targets.rows)), lambda: None)
        self.assertEqual(result, {"optimizer_updates": 3, "real_row_presentations": 96, "train_loss": 1.0})
        kinds = [e if isinstance(e, str) else e[0] for e in events
                 if e in ("zero_grad", "step") or isinstance(e, tuple) and e[0] in ("backward", "clip")]
        self.assertEqual(kinds, ["zero_grad", "backward", "clip", "step"] * 3)
        self.assertEqual([e for e in events if isinstance(e, tuple) and e[0] == "backward"],
                         [("backward", 1.0)] * 3)
        self.assertEqual(sum(e[1] for e in events if isinstance(e, tuple) and e[0] == "rows"), 96)
        self.assertEqual(sum(e == ("clip", 1.) for e in events), 3)

    def test_update_runner_is_the_v3_runner_body(self):
        import ast

        def body(path):
            tree = ast.parse(Path(path).read_text())
            function = next(node for node in tree.body
                            if isinstance(node, ast.FunctionDef) and node.name == "run_update_units")
            # Drop the docstring; v3 passed its own pair deadline to the resource check.
            return ast.dump(ast.Module(function.body[1:], [])).replace("Name(id='deadline', ctx=Load())", "")

        self.assertEqual(body(ROOT / "scripts/train_male_navigation_v3.py"), body(trainer.__file__))


# --------------------------------------------------------------------------- end to end (synthetic)

class TinyHooks(trainer.Hooks):
    """Synthetic graph and a tiny Linear model; the real loss and recorded-dev evaluator."""

    def __init__(self, test):
        super().__init__()
        self.test, self.calls = test, []

    def admit_model_inputs(self, study):
        return ({"ordered_ids_sha256": "a" * 64, "ids": [1, 2]}, {"synthetic": "0" * 64})

    def make_model(self, graph, seed):
        import torch
        torch.manual_seed(seed)

        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.linear = torch.nn.Linear(388, 2)
                self.mix = torch.nn.Linear(2, 2)
                self.cell = types.SimpleNamespace(invalidate_caches=lambda: None)

            def reset(self):
                return torch.zeros(1, 2)

            def forward(self, inputs, hidden):
                actions = self.linear(inputs) + self.mix(hidden)
                return torch.tanh(actions[-1]), actions

        return Tiny()

    def evaluate(self, model, episodes, deadline, training):
        output = Path(self.test.output)
        self.calls.append(sorted(path.name for path in output.iterdir()))
        if getattr(self.test, "fail_at", None) == len(self.calls):
            raise ValueError("synthetic recorded-development fault")
        return super().evaluate(model, episodes, deadline, training)

    def derive_data(self, record, derivation, output):
        return self.test.root / "arrays.npz"      # stands in for the S0f-reader child (own tests below)

    def inside_stage(self):
        return True

    def runtime(self, study, torch_module=None):
        return {"synthetic": torch_module is not None}


class EndToEnd(Temp):
    def setUp(self):
        super().setUp()
        import torch
        deterministic = torch.are_deterministic_algorithms_enabled()
        threads = torch.get_num_threads()
        self.addCleanup(torch.use_deterministic_algorithms, deterministic)
        self.addCleanup(torch.set_num_threads, threads)
        self.pin, self.record, _ = write_corpus(self.root)
        self.derivation = trainer.derive_schedules(self.record)
        self.go = write_go(self.root, self.pin, self.derivation["sha256"])
        self.output = self.root / "s1"
        self.argv = ["--go", str(self.go), "--corpus-pin", str(self.pin), "--output", str(self.output)]

    def run_main(self, hooks):
        import torch
        counts = {"zero_grad": 0, "step": 0}
        step, zero_grad = torch.optim.Adam.step, torch.optim.Optimizer.zero_grad

        def counted_step(optimizer, *args, **kwargs):
            counts["step"] += 1
            return step(optimizer, *args, **kwargs)

        def counted_zero(optimizer, *args, **kwargs):
            counts["zero_grad"] += 1
            return zero_grad(optimizer, *args, **kwargs)

        with patch.object(torch.optim.Adam, "step", counted_step), \
                patch.object(torch.optim.Optimizer, "zero_grad", counted_zero), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                code = trainer.main(self.argv, hooks=hooks)
            except ValueError as error:
                code = error
        return code, counts

    def test_six_terminal_models_then_one_publication(self):
        import torch
        hooks = TinyHooks(self)
        code, counts = self.run_main(hooks)
        self.assertEqual(code, 0)
        self.assertEqual(counts, {"zero_grad": 6 * 1440, "step": 6 * 1440})
        report = trainer.success_admitted(self.output)
        self.assertIsNotNone(report)
        self.assertEqual([(m["seed"], m["arm"]) for m in report["models"]], list(trainer.planned_models()))
        for position, model in enumerate(report["models"]):
            self.assertEqual((model["optimizer_updates"], model["real_row_presentations"],
                              model["selected_optimizer_update"], model["recorded_development"]["ticks"]),
                             (1440, 46080, 1440, 32))
            seed, arm = trainer.planned_models()[position]
            self.assertEqual(model["schedule_sha256"], self.derivation["schedules"][seed, arm].sha256)
            # Terminal-only: when model k is evaluated, only earlier checkpoints exist and no report.
            self.assertEqual([name for name in hooks.calls[position] if name.endswith(".pt")],
                             sorted(f"seed-{s}-{a}.pt" for s, a in trainer.planned_models()[:position]))
            self.assertFalse({"report.json", "publication.json"} & set(hooks.calls[position]))
            checkpoint = torch.load(self.output / model["checkpoint"]["path"], weights_only=True)
            self.assertEqual(set(checkpoint), {"format", "protocol_sha256", "graph_sha256",
                                               "ordered_ids_sha256", "state_dict"})
            self.assertEqual(checkpoint["protocol_sha256"], report["run_protocol_sha256"])
        self.assertEqual(report["schedule_derivation_sha256"], self.derivation["sha256"])
        self.assertEqual((self.output / "schedule-derivation.json").read_bytes(), self.derivation["bytes"])
        self.assertEqual(report["held_out_status"], "locked_unopened")
        self.assertNotIn("cpu_seconds", json.dumps(report))
        # One attempt: the consumed output refuses a second run.
        with self.assertRaisesRegex(trainer.Refusal, "consumed"):
            trainer.preflight_output(self.output)
        # A tampered checkpoint, missing receipt or retained failure is never success.
        (self.output / "publication.json").rename(self.output / "receipt.moved")
        self.assertIsNone(trainer.success_admitted(self.output))

    def test_first_fault_is_retained_and_later_models_stay_not_started(self):
        self.fail_at = 3
        hooks = TinyHooks(self)
        code, counts = self.run_main(hooks)
        self.assertIsInstance(code, ValueError)
        self.assertEqual(counts["step"], 3 * 1440)
        failure = json.loads((self.output / "failure.json").read_text())
        self.assertEqual([m["status"] for m in failure["models"]],
                         ["completed", "completed", "failed", "not_started", "not_started", "not_started"])
        self.assertFalse((self.output / "report.json").exists())
        self.assertFalse((self.output / "publication.json").exists())
        self.assertIsNone(trainer.success_admitted(self.output))
        self.assertEqual(sorted(p.name for p in self.output.glob("*.pt")),
                         ["seed-10-augmented.pt", "seed-10-old-corpus.pt"])

    def test_publication_refuses_incomplete_reports(self):
        self.output.mkdir()
        report = trainer.initial_report("0" * 64, "1" * 64, self.derivation)
        with self.assertRaisesRegex(ValueError, "six-model"):
            trainer.publish_success(self.output, report)
        self.assertFalse((self.output / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
