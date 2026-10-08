"""Bounded matched-budget ORIGINAL-topology trainer; no simulator or held-out route."""
import argparse
import hashlib
import importlib
import importlib.metadata
import io
import math
import os
from pathlib import Path
import platform
import resource
import sys
import time

from palimpsest import artifacts, male_matched_budget, male_model
from palimpsest.storage import StorageBudget, StorageLimits
import prepare_male_navigation_v2 as data_reader
import train_male_reduced as fitter


ROOT = Path(__file__).resolve().parents[1]
SELF_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
SCHEDULER_SHA = hashlib.sha256(Path(male_matched_budget.__file__).read_bytes()).hexdigest()
PROTOCOL_PATH = "docs/plans/m7-navigation-v3-matched-budget-protocol.json"
PROTOCOL_SHA = "ecfafd2b6bedaf5d073e0bf32571d1978084ec7ddfb0e8c6c98a298d38d70732"
DATA_SHA = "47c4523c40e485ba4839cc80c9db891761791b801cc777755028122a1dbacb41"
ARMS = ("old-corpus", "augmented")
SEEDS = (10, 11, 12)
MiB = 1024**2
GiB = 1024**3
MAX_JSON = 4 * MiB
MAX_FILE = 8 * MiB
PAIR_BYTES = 64 * MiB
AGGREGATE_BYTES = 256 * MiB
RSS_BYTES = GiB
PAIR_SECONDS = 600
FUTURE_SOURCES = (
    "docs/plans/m7-navigation-v3-matched-budget-protocol.json",
    "src/palimpsest/male_matched_budget.py",
    "scripts/train_male_navigation_v3.py",
    "tests/test_male_navigation_v3.py",
    "scripts/train_male_recovery.py",
    "scripts/prepare_male_recovery_data.py",
)


def protocol():
    value = data_reader.read_json(ROOT / PROTOCOL_PATH, expected=PROTOCOL_SHA)
    if value.get("id") != male_matched_budget.PROTOCOL_ID or value.get("version") != 1:
        raise ValueError("Frozen navigation-v3 protocol differs")
    return value


def planned_models():
    return tuple((seed, arm) for seed in SEEDS for arm in ARMS)


def fixed_training(seed, arm):
    if type(seed) is not int or seed not in SEEDS or arm not in ARMS:
        raise ValueError("Fixed seed 10/11/12 and old-corpus/augmented arm required")
    value = protocol()
    numerics = value["training"]["numerics"]
    budget = value["matched_budget"]
    selected = value["training"]["selected_checkpoint"]
    settings = {
        "training_seed": seed,
        "arm": arm,
        "graph_variant": "original",
        "schedule_version": value["sampler"]["schedule_version"],
        "real_row_presentations": budget["real_loss_bearing_row_presentations_per_model"],
        "rows_per_update": budget["real_loss_bearing_rows_per_update"],
        "optimizer_updates": budget["optimizer_updates_per_model"],
        "selected_optimizer_update": selected["selected_optimizer_updates"],
        "dev_rows": value["corpora"]["recorded_development"]["row_count"],
        "optimizer": numerics["optimizer"],
        "learning_rate": numerics["learning_rate"],
        "gradient_norm_cap": numerics["gradient_norm_cap"],
        "dtype": numerics["dtype"],
        "device": numerics["device"],
        "threads": numerics["threads"],
        "qualification_claims": [],
    }
    if (settings["real_row_presentations"] != 46_080 or
            settings["rows_per_update"] != 32 or settings["optimizer_updates"] != 1_440 or
            settings["selected_optimizer_update"] != 1_440 or settings["dev_rows"] != 1_228 or
            (settings["optimizer"], settings["learning_rate"], settings["gradient_norm_cap"],
             settings["dtype"], settings["device"], settings["threads"]) !=
            ("Adam", .001, 1., "float32", "cpu", 1)):
        raise ValueError("Frozen matched training-and-selection clock differs")
    return settings


def _manifest_sources(rows):
    if not isinstance(rows, list):
        raise ValueError("Manifest source roster must be a list")
    result = []
    for row in rows:
        if not isinstance(row, dict) or any(key not in row for key in
                ("run_id", "episode", "ticks", "feature_target_sha256")):
            raise ValueError("Manifest source identity is incomplete")
        result.append(male_matched_budget.SourceIdentity(
            row["run_id"], row["episode"], row["feature_target_sha256"], row["ticks"]))
    return tuple(result)


def admit_schedules(manifest, seed):
    """Admit only the exact manifest rosters and hash both schedules without data reads."""
    fixed_training(seed, ARMS[0])
    value = protocol()
    if not isinstance(manifest, dict) or set(manifest.get("arms", {})) != {"old", "augmented"}:
        raise ValueError("Exact old and augmented manifest arms required")
    old_arm, augmented_arm = manifest["arms"]["old"], manifest["arms"]["augmented"]
    if (set(old_arm) != {"train", "dev", "held_out"} or
            set(augmented_arm) != {"train", "dev", "held_out"} or
            old_arm["held_out"] != [] or augmented_arm["held_out"] != []):
        raise ValueError("Training manifest must contain no held-out rows")
    expected_dev = [{"run_id": row["run_id"], "episode": 0, "ticks": row["rows"],
                     "feature_target_sha256": row["feature_target_sha256"]}
                    for row in value["corpora"]["recorded_development"]["sequence_order"]]
    if old_arm["dev"] != expected_dev or augmented_arm["dev"] != expected_dev:
        raise ValueError("Exact shared recorded-development roster required")
    old_rows = tuple(value["corpora"]["old_corpus"]["source_rows_in_manifest_order"])
    augmented_rows = tuple(value["corpora"]["augmented"]["source_rows_in_manifest_order"])
    old = _manifest_sources(old_arm["train"])
    augmented = _manifest_sources(augmented_arm["train"])
    if (tuple(source.rows for source in old) != old_rows or
            tuple(source.rows for source in augmented) != augmented_rows or
            augmented[:len(old)] != old):
        raise ValueError("Exact corpus row roster and old prefix required")
    schedules = {name: male_matched_budget.build_schedule(sources, seed)
                 for name, sources in ((ARMS[0], old), (ARMS[1], augmented))}
    for name, key in ((ARMS[0], "old_corpus"), (ARMS[1], "augmented")):
        schedule = schedules[name]
        if (schedule.presentations != 46_080 or schedule.rows_per_update != 32 or
                len(schedule.updates) != 1_440 or
                schedule.remainder_allocations != tuple(value["sampler"]["remainder_allocation"][key]) or
                schedule.source_presentations != tuple(
                    value["sampler"]["per_source_total_presentations"][key]) or
                hashlib.sha256(schedule.canonical_bytes()).hexdigest() != schedule.sha256 or
                len(schedule.canonical_bytes()) > MAX_FILE):
            raise ValueError("Canonical matched-budget schedule differs")
    if schedules[ARMS[0]].remainder_starts != schedules[ARMS[1]].remainder_starts[:len(old)]:
        raise ValueError("Shared old-source remainder starts differ between arms")
    return schedules


def admit_model_context(graph, context, args):
    """Recheck the original graph, extraction manifest, and cell pins returned by V2."""
    study = protocol()
    inputs = study["immutable_inputs"]
    actual_paths = {name: Path(os.path.abspath(getattr(args, name)))
                    for name in ("graph", "graph_manifest", "cell_source")}
    declared_paths = {
        "graph": Path(os.path.abspath(inputs["graph"]["path"])),
        "graph_manifest": Path(os.path.abspath(inputs["graph_manifest"]["path"])),
        "cell_source": Path(os.path.abspath(inputs["cell_source"]["path"])),
    }
    expected = {
        str(actual_paths["graph"]): inputs["graph"]["sha256"],
        str(actual_paths["graph_manifest"]): inputs["graph_manifest"]["sha256"],
        str(actual_paths["cell_source"]): inputs["cell_source"]["sha256"],
    }
    if (actual_paths != declared_paths or not isinstance(graph, dict) or
            graph.get("source_graph_sha256") != study["training"]["model"]["graph_sha256"] or
            graph.get("graph_manifest_sha256") != inputs["graph_manifest"]["sha256"] or
            not isinstance(context, dict) or context.get("model_inputs") != expected):
        raise ValueError("Pinned original graph, extraction manifest, or cell context differs")
    return expected


def source_identity(deadline, expected=None):
    value = protocol()
    pinned = value["behavior_source_admission"]["existing_hashes"]
    names = tuple(sorted(set(pinned) | set(FUTURE_SOURCES)))
    observed = {name: data_reader.file_sha(ROOT / name, MAX_JSON, deadline) for name in names}
    if any(observed.get(name) != digest for name, digest in pinned.items()):
        raise ValueError("Pinned local behavior source changed")
    if (observed["scripts/train_male_navigation_v3.py"] != SELF_SHA or
            observed["src/palimpsest/male_matched_budget.py"] != SCHEDULER_SHA):
        raise ValueError("Loaded navigation-v3 source differs from admitted bytes")
    if expected is not None and observed != expected:
        raise ValueError("Navigation-v3 behavior source changed during training")
    return observed


def _attempt_path(output):
    return output.with_name(output.name + ".attempt.json")


def _failure_path(output):
    return output.with_name(output.name + ".failure.json")


def preflight_output(value, seed, study):
    output = artifacts._safe_path(value)
    if output.name != f"seed-{seed}" or not output.parent.is_dir():
        raise ValueError("Fresh existing-parent seed-N output required")
    if output.exists() or _attempt_path(output).exists() or _failure_path(output).exists():
        raise FileExistsError("Navigation-v3 seed attempt is already consumed")
    for item in study["immutable_inputs"].values():
        source = Path(os.path.abspath(item["path"])).parent
        if output.parent == source or output.parent in source.parents or source in output.parent.parents:
            raise ValueError("Managed output overlaps an immutable input tree")
    return output


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_artifact(path, payload, deadline, storage_budget, maximum):
    if len(payload) > maximum:
        raise ValueError("Navigation-v3 artifact exceeds its byte cap")
    data_reader.check_deadline(deadline)
    storage_budget.check(len(payload), path=path)
    with Path(path).open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    data_reader.check_deadline(deadline)
    return {"path": Path(path).name, "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload)}


def reserve_attempt(output, seed, deadline, storage_budget):
    path = _attempt_path(Path(output))
    payload = male_model.canonical({
        "id": "male-navigation-v3-pair-attempt-v1",
        "study_protocol_sha256": PROTOCOL_SHA,
        "training_seed": seed,
        "output": str(Path(output).absolute()),
        "models": [{"seed": item_seed, "arm": arm} for item_seed, arm in planned_models()],
        "retry_allowed": False,
        "qualification_claims": [],
    })
    item = _write_artifact(path, payload, deadline, storage_budget, MAX_JSON)
    _fsync_directory(path.parent)
    return {**item, "path": str(path.absolute())}


def initial_report(seed, attempt):
    return {
        "status": "running-navigation-v3-training",
        "training_completed": False,
        "training_attempted": False,
        "training_seed": seed,
        "study_protocol_sha256": PROTOCOL_SHA,
        "data_manifest_sha256": DATA_SHA,
        "attempt": attempt,
        "study_models": [{"seed": item_seed, "arm": arm, "status":
                          ("not_started" if item_seed != seed else "owned_by_this_pair")}
                         for item_seed, arm in planned_models()],
        "models": {arm: {"status": "not_started"} for arm in ARMS},
        "files": [],
        "held_out_status": "locked_unopened",
        "held_out_used_for_selection": False,
        "qualification_claims": [],
    }


def publish_failure(output, report, error, deadline, storage_budget):
    report.update(status="failed-navigation-v3-training", training_completed=False,
                  error={"type": type(error).__name__, "message": str(error)[:1024]})
    path = _failure_path(Path(output))
    item = _write_artifact(path, male_model.canonical(report), math.inf,
                           storage_budget, MAX_JSON)
    _fsync_directory(path.parent)
    return item


def _completed_report(value):
    return (isinstance(value, dict) and
            value.get("status") == "completed-navigation-v3-training" and
            value.get("training_completed") is True and
            isinstance(value.get("models"), dict) and
            set(value["models"]) == set(ARMS) and
            all(value["models"][arm].get("status") == "completed" for arm in ARMS) and
            value.get("held_out_status") == "locked_unopened" and
            value.get("qualification_claims") == [])


def success_admitted(output, expected_report_sha=None):
    """A report is success evidence only with its completion receipt and no failure."""
    output = Path(output)
    if (_failure_path(output).exists() or not _attempt_path(output).is_file() or
            not (output / "report.json").is_file() or
            not (output / "publication.json").is_file() or
            (output / "report.pending").exists() or
            (output / "publication.pending").exists()):
        return False
    try:
        payload = artifacts._read(output / "report.json", MAX_JSON)
        report_value = artifacts._json(payload)
        receipt = data_reader.read_json(output / "publication.json", MAX_JSON)
    except (OSError, ValueError):
        return False
    digest = hashlib.sha256(payload).hexdigest()
    return (_completed_report(report_value) and receipt == {
        "id": "male-navigation-v3-publication-v1",
        "status": "durably-published",
        "study_protocol_sha256": PROTOCOL_SHA,
        "report_sha256": digest,
        "report_size_bytes": len(payload),
        "qualification_claims": [],
    } and (expected_report_sha is None or digest == expected_report_sha))


def publish_success(output, deadline, validate, storage_budget, staged):
    """Durably publish the report, then a receipt required for V3 admission."""
    output = Path(output)
    pending, report = output / "report.pending", output / "report.json"
    publication_pending, publication = (output / "publication.pending",
                                        output / "publication.json")
    if (not isinstance(staged, dict) or staged.get("path") != "report.pending" or
            not isinstance(staged.get("sha256"), str) or
            type(staged.get("size_bytes")) is not int):
        raise ValueError("Exact staged V3 report identity required")
    if (_failure_path(output).exists() or report.exists() or publication.exists() or
            publication_pending.exists()):
        raise FileExistsError("Fresh failure-free V3 publication paths required")
    payload = artifacts._read(pending, MAX_JSON)
    if (len(payload) != staged["size_bytes"] or
            hashlib.sha256(payload).hexdigest() != staged["sha256"] or
            not _completed_report(artifacts._json(payload))):
        raise ValueError("Staged V3 report identity changed")
    validate()
    data_reader.check_deadline(deadline)
    pending.replace(report)
    _fsync_directory(output)
    receipt = {
        "id": "male-navigation-v3-publication-v1",
        "status": "durably-published",
        "study_protocol_sha256": PROTOCOL_SHA,
        "report_sha256": staged["sha256"],
        "report_size_bytes": staged["size_bytes"],
        "qualification_claims": [],
    }
    _write_artifact(publication_pending, male_model.canonical(receipt), deadline,
                    storage_budget, MAX_JSON)
    publication_pending.replace(publication)
    _fsync_directory(output)  # Required final durability boundary.
    return receipt


def rss_bytes():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def check_resources(deadline):
    data_reader.check_deadline(deadline)
    observed = rss_bytes()
    if observed > RSS_BYTES:
        raise MemoryError(f"Navigation-v3 pair RSS exceeds {RSS_BYTES} bytes")
    return observed


def pre_runtime(*, require_lazy=True):
    expected = protocol()["training"]["runtime"]
    observed = {"python": platform.python_version(),
                "numpy": importlib.metadata.version("numpy"),
                "torch_distribution": importlib.metadata.version("torch")}
    if observed != {key: expected[key] for key in observed}:
        raise ValueError("Frozen Python/NumPy/Torch distribution runtime differs")
    forbidden = {"mujoco"} | ({"torch"} if require_lazy else set())
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or forbidden & set(sys.modules):
        raise ValueError("Heavy runtime must remain absent with CUDA hidden before admission")
    return observed


def cpu_runtime(torch_module):
    expected = protocol()["training"]["runtime"]
    observed = {**pre_runtime(require_lazy=False), "torch_build": torch_module.__version__}
    if (observed != expected or torch_module.get_num_threads() != 1 or
            torch_module.cuda.is_initialized()):
        raise ValueError("Frozen CPU one-thread Torch runtime differs")
    return observed


def validate_prepared_data(data, schedules):
    numpy = importlib.import_module("numpy")
    for arm in ARMS:
        split = data.get(arm)
        if not isinstance(split, dict) or split.get("held_out") != [] or len(split.get("dev", ())) != 4:
            raise ValueError("Prepared arm split contract differs")
        episodes = split.get("train")
        schedule = schedules[arm]
        if not isinstance(episodes, list) or len(episodes) != len(schedule.sources):
            raise ValueError("Prepared training source count differs")
        for episode, source in zip(episodes, schedule.sources, strict=True):
            features, targets = episode.get("features"), episode.get("targets")
            if (episode.get("run_id") != source.run_id or episode.get("episode") != source.episode or
                    not isinstance(features, numpy.ndarray) or not isinstance(targets, numpy.ndarray) or
                    features.dtype != numpy.float32 or targets.dtype != numpy.float32 or
                    features.shape != (source.rows, 388) or targets.shape != (source.rows, 2) or
                    not numpy.isfinite(features).all() or not numpy.isfinite(targets).all() or
                    hashlib.sha256(features.tobytes() + targets.tobytes()).hexdigest() !=
                    source.feature_target_sha256):
                raise ValueError("Prepared finite float32 source bytes/order differ from schedule")
    old_dev, augmented_dev = data[ARMS[0]]["dev"], data[ARMS[1]]["dev"]
    for left, right, expected in zip(old_dev, augmented_dev,
                                     protocol()["corpora"]["recorded_development"]["sequence_order"],
                                     strict=True):
        if ((left is not right and any(left.get(key) != right.get(key)
                                       for key in ("run_id", "episode"))) or
                left.get("run_id") != expected["run_id"] or
                len(left.get("targets", ())) != expected["rows"]):
            raise ValueError("Recorded-development roster differs between arms")


def run_update_units(model, optimizer, data, schedule, torch_module, loss_function,
                     deadline, resource_check=check_resources):
    """Execute a pre-admitted schedule; generic enough for synthetic boundary tests."""
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not parameters:
        raise ValueError("Matched trainer requires trainable parameters")
    model.train()
    if hasattr(model, "cell"):
        model.cell.invalidate_caches()
    total, count = 0., 0
    carried = {}
    for unit in schedule.updates:
        resource_check(deadline)
        if unit.rows != schedule.rows_per_update:
            raise ValueError("Optimizer unit does not contain the exact real-row budget")
        optimizer.zero_grad(set_to_none=True)
        summed = None
        for index, fragment in enumerate(unit.fragments):
            episode = data["train"][fragment.source_index]
            if fragment.reset_before:
                hidden = model.reset()
            else:
                previous = carried.get(fragment.source_index)
                if index != 0 or previous is None or previous[0] != fragment.start:
                    raise ValueError("Hidden continuation does not match the admitted fragment")
                hidden = previous[1].detach()
            inputs = torch_module.from_numpy(
                episode["features"][fragment.start:fragment.stop]).unsqueeze(1)
            targets = torch_module.from_numpy(
                episode["targets"][fragment.start:fragment.stop]).unsqueeze(1)
            hidden, actions = model(inputs, hidden)
            values = loss_function(actions, targets)
            if values.numel() != fragment.rows or not torch_module.isfinite(values).all():
                raise ValueError("Nonfinite or wrong-count fragment loss")
            part = values.sum()
            summed = part if summed is None else summed + part
            total += float(values.detach().sum())
            count += values.numel()
            carried[fragment.source_index] = (fragment.stop, hidden)
        loss = summed / schedule.rows_per_update
        if not torch_module.isfinite(loss).all():
            raise ValueError("Nonfinite matched-update loss")
        loss.backward()
        torch_module.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
        optimizer.step()
        if any(not torch_module.isfinite(parameter).all() for parameter in parameters):
            raise ValueError("Nonfinite male parameters after optimizer step")
    resource_check(deadline)
    if count != schedule.presentations or len(schedule.updates) * schedule.rows_per_update != count:
        raise ValueError("Executed matched budget differs from admitted schedule")
    if not math.isfinite(total) or total < 0:
        raise ValueError("Accumulated matched training loss is invalid")
    return {"optimizer_updates": len(schedule.updates), "real_row_presentations": count,
            "train_loss": total / count}


def fit_terminal(graph, data, cell_source, schedule, settings, torch_module, deadline):
    model = fitter.make_model(graph, cell_source, settings["training_seed"])
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch_module.optim.Adam(parameters, lr=settings["learning_rate"])
    result = run_update_units(model, optimizer, data, schedule, torch_module,
                              fitter.loss_for, deadline)
    names = [name for name, parameter in model.named_parameters() if parameter.requires_grad]
    terminal_state = {name: value.detach().cpu().clone()
                      for name, value in model.state_dict().items()}
    result.update(selected_optimizer_update=len(schedule.updates),
                  selected_real_row_presentations=schedule.presentations,
                  selection="terminal-only-before-recorded-development",
                  trainable_parameters=sum(parameter.numel() for parameter in parameters),
                  trainable_names=names)
    development = fitter.evaluate(model, data["dev"], deadline,
                              {"window": 32, "training_seed": settings["training_seed"]})
    if (type(development.get("ticks")) is not int or development["ticks"] != 1_228 or
            any(type(development.get(key)) not in (int, float) or
            type(development.get(key)) is bool or
            not math.isfinite(development[key]) or development[key] < 0
            for key in ("loss", "velocity_mae", "wrapped_heading_mae_radians"))):
        raise ValueError("Terminal recorded-development metrics differ")
    result["recorded_development"] = development
    return model, terminal_state, result


def _load_torch():
    return importlib.import_module("torch")


def _load_v2():
    """Load the retained-input admission/publication owner only after reservation."""
    return importlib.import_module("train_male_navigation_v2")


def train(args):
    started = time.monotonic()
    deadline = started + PAIR_SECONDS
    study = protocol()
    fixed_training(args.training_seed, ARMS[0])
    output = preflight_output(args.output, args.training_seed, study)
    check_resources(deadline)
    before_sources = source_identity(deadline)
    pre_runtime()
    aggregate = StorageBudget((output.parent,), StorageLimits(
        max_bytes=AGGREGATE_BYTES, min_free_bytes=GiB, max_runs=3,
        max_snapshots=1, max_exports=1))
    pair = StorageBudget((output,), StorageLimits(max_bytes=PAIR_BYTES, min_free_bytes=GiB))
    report = active = attempt = context = runtime = None
    try:
        with aggregate.lock():
            aggregate.check(PAIR_BYTES, path=output)
            check_resources(deadline)
            attempt = reserve_attempt(output, args.training_seed, deadline, aggregate)
            report = initial_report(args.training_seed, attempt)
            trainer_v2 = _load_v2()
            source_identity(deadline, before_sources)
            admitted_output, data, graph, context = trainer_v2.prepare(args, deadline)
            if admitted_output != output:
                raise ValueError("V2 admission returned a different output")
            admit_model_context(graph, context, args)
            schedules = admit_schedules(context["manifest"], args.training_seed)
            validate_prepared_data(data, schedules)
            source_identity(deadline, before_sources)
            check_resources(deadline)
            output.mkdir(exist_ok=False)
            _fsync_directory(output.parent)

            def write(name, payload, maximum=MAX_FILE):
                if sum(path.stat().st_size for path in output.iterdir() if path.is_file()) + len(payload) > PAIR_BYTES:
                    raise ValueError("Navigation-v3 pair payload cap exceeded")
                item = trainer_v2.write_artifact(output / name, payload, deadline, pair, maximum)
                report["files"].append(item)
                return item

            trainer_v2.check_context(context, deadline, output / "before-fit.json", pair)
            pair_protocol = {
                "id": male_matched_budget.PROTOCOL_ID,
                "seed": args.training_seed,
                "training": {arm: fixed_training(args.training_seed, arm) for arm in ARMS},
                "schedule_sha256": {arm: schedules[arm].sha256 for arm in ARMS},
                "source_code": before_sources,
                "model_inputs": context["model_inputs"],
                "admitted_manifest_sha256": DATA_SHA,
                "study_protocol_sha256": PROTOCOL_SHA,
                "held_out_status": "locked_unopened",
                "qualification_claims": [],
            }
            report["protocol_sha256"] = male_model.digest(pair_protocol)
            write("protocol.json", male_model.canonical(pair_protocol), MAX_JSON)
            write("original-graph.json", male_model.canonical(graph))
            for arm in ARMS:
                write(arm + "-schedule.json", schedules[arm].canonical_bytes())
            source_identity(deadline, before_sources)
            check_resources(deadline)

            torch_module = _load_torch()  # Sole heavy import, after complete admission and schedule publication.
            torch_module.set_num_threads(1)
            torch_module.use_deterministic_algorithms(True)
            runtime = cpu_runtime(torch_module)
            report["runtime"] = runtime
            roster = None
            for arm in ARMS:
                active = arm
                report["models"][arm] = {"status": "running"}
                report["training_attempted"] = True
                settings = pair_protocol["training"][arm]
                model, terminal_state, result = fit_terminal(
                    graph, data[arm], args.cell_source, schedules[arm], settings,
                    torch_module, deadline)
                if (result["optimizer_updates"] != 1_440 or
                        result["real_row_presentations"] != 46_080 or
                        result["selected_optimizer_update"] != 1_440 or
                        result["selected_real_row_presentations"] != 46_080):
                    raise ValueError("Completed model differs from matched terminal budget")
                if roster is None:
                    roster = result["trainable_names"]
                elif result["trainable_names"] != roster:
                    raise ValueError("Paired trainable parameter roster differs")
                trainer_v2.check_context(context, deadline, output / f"after-{arm}.json", pair)
                source_identity(deadline, before_sources)
                check_resources(deadline)
                checkpoint = {
                    "format": "palimpsest-male-reduced-v1",
                    "protocol_sha256": report["protocol_sha256"],
                    "schedule_sha256": schedules[arm].sha256,
                    "selected_optimizer_update": 1_440,
                    "selected_real_row_presentations": 46_080,
                    "graph_sha256": male_model.digest(graph),
                    "ordered_ids_sha256": graph["ordered_ids_sha256"],
                    "state_dict": terminal_state,
                }
                buffer = io.BytesIO()
                torch_module.save(checkpoint, buffer)
                checkpoint_item = write(arm + ".pt", buffer.getvalue())
                report["models"][arm] = {"status": "completed", **result,
                                         "schedule_sha256": schedules[arm].sha256,
                                         "checkpoint": checkpoint_item,
                                         "graph_variant": "original"}
                del model, terminal_state, checkpoint, buffer
                active = None
            report.update(status="completed-navigation-v3-training", training_completed=True,
                          elapsed_seconds_before_publication=time.monotonic() - started)
            trainer_v2.check_context(context, deadline, output / "after-fit.json", pair)
            source_identity(deadline, before_sources)
            check_resources(deadline)
            aggregate.check(0, path=output)
            report["success_admission"] = {
                "requires": ["normal_return", "report.json", "publication.json",
                             "no_seed_failure_receipt"],
                "publication_id": "male-navigation-v3-publication-v1",
            }
            staged = trainer_v2.stage_report(output, report, deadline, pair)

        def final_admission():
            if cpu_runtime(torch_module) != runtime:
                raise ValueError("Runtime changed during navigation-v3 training")
            trainer_v2.check_context(context, deadline, output / "after-final-sync.json", pair)
            source_identity(deadline, before_sources)
            check_resources(deadline)
            aggregate.check(0, path=output)

        publish_success(output, deadline, final_admission, pair, staged)
        return report
    except BaseException as error:
        if report is None and _attempt_path(output).exists():
            marker = {"path": str(_attempt_path(output).absolute())}
            report = initial_report(args.training_seed, marker)
        if report is not None:
            if active is not None:
                report["models"][active] = {"status": "failed",
                                             "error": {"type": type(error).__name__,
                                                       "message": str(error)[:1024]}}
            try:
                publish_failure(output, report, error, math.inf, aggregate)
            except BaseException as diagnostic:
                error.add_note("Failure retention also failed: " + str(diagnostic)[:256])
        raise


def main(argv=None):
    study = protocol()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-seed", type=int, choices=SEEDS, required=True)
    parser.add_argument("--graph", type=Path,
                        default=Path(study["immutable_inputs"]["graph"]["path"]))
    parser.add_argument("--graph-manifest", type=Path,
                        default=Path(study["immutable_inputs"]["graph_manifest"]["path"]))
    parser.add_argument("--cell-source", type=Path,
                        default=Path(study["immutable_inputs"]["cell_source"]["path"]))
    parser.add_argument("--output", type=Path, required=True,
                        help="Fresh aggregate-root/seed-N pair directory")
    train(parser.parse_args(argv))


if __name__ == "__main__":
    main()
