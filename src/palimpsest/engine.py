"""Single-owner simulation execution with recorded command boundaries."""

from collections import deque
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import threading
import time
import uuid
from .male_policy import CONTROLLERS as MALE_CONTROLLERS, validate_identity


PHASES = {"paused", "running", "terminated", "truncated", "stopped", "failed"}
KINDS = {"run", "pause", "step", "stop", "reset", "set_action", "set_eyes", "intervene", "calibration-next"}


class CommandRejected(ValueError):
    """A command failed validation before its requested mutation."""


def _seed(value):
    if type(value) is not int or not 0 <= value < 2**31:
        raise ValueError("seed must be an integer in [0, 2**31)")
    return value


def _action(value, manual=False):
    import numpy as np

    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    result = np.asarray(value)
    if result.shape != (2,) or result.dtype.kind not in "iuf" or not np.isfinite(result).all():
        raise ValueError("action must contain two finite numbers: velocity and heading")
    if manual and (abs(float(result[0])) > 3 or abs(float(result[1])) > math.pi):
        raise ValueError("manual velocity must be within +/-3 and heading within +/-pi")
    result = result.astype(np.float64 if manual else np.float32)
    if not np.isfinite(result).all():
        raise ValueError("action exceeds float32 range")
    return result


def _teacher_fingerprint(teacher):
    """Bind reset behavior to the supplied initial teacher, including its nested state."""
    if teacher is None:
        return None
    import numpy as np

    def describe(value, depth=0):
        if depth > 32:
            raise ValueError("teacher reset baseline nesting exceeds limit")
        if value is None or type(value) in (str, bool, int, float):
            return value
        if isinstance(value, np.generic):
            value = np.asarray(value)
        if isinstance(value, np.ndarray):
            if value.dtype.hasobject:
                raise ValueError("teacher reset baseline cannot contain object arrays")
            return {"dtype": value.dtype.str, "shape": list(value.shape),
                    "sha256": hashlib.sha256(value.tobytes()).hexdigest()}
        if isinstance(value, (list, tuple)):
            return {type(value).__name__: [describe(item, depth + 1) for item in value]}
        if isinstance(value, dict):
            if any(type(key) is not str for key in value):
                raise ValueError("teacher reset baseline keys must be strings")
            return {key: describe(item, depth + 1) for key, item in value.items()}
        kind = f"{type(value).__module__}.{type(value).__qualname__}"
        if kind == "torch.device":
            return {"class": kind, "value": str(value)}
        if hasattr(value, "__dict__") and not callable(value):
            return {"class": kind, "state": describe(vars(value), depth + 1)}
        raise ValueError(f"unsupported teacher reset baseline value: {kind}")

    encoded = json.dumps(describe(teacher), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class Engine:
    MAX_QUEUE = 128
    MAX_IDS = 4096

    def __init__(self, env, writer, controller="manual", policy=None, teacher=None, seed=0,
                 scenario="reproduction", texture="checker", *, memory_case=None,
                 restore_snapshot=None, replace_controller=False, memory_u=None):
        import numpy as np

        if controller not in {"manual", "teacher", "flynn", *MALE_CONTROLLERS}:
            raise ValueError("unknown controller")
        if (controller in {"flynn", *MALE_CONTROLLERS} and policy is None) or (controller == "teacher" and teacher is None):
            raise ValueError("selected controller must be supplied")
        if controller in MALE_CONTROLLERS:
            from .profiles import validate
            validate(scenario, texture, controller)
            identity = validate_identity(policy.provenance.get('policy_identity'), controller)
            writer.manifest['policy_identity'] = identity
        dt = float(env.model.opt.timestep * env.frame_skip)
        if not math.isclose(dt, .02, rel_tol=0., abs_tol=1e-12):
            raise ValueError("this profile requires a 0.02-second control interval")
        self._owner = threading.get_ident()
        self.env, self.writer = env, writer
        self.controller, self.policy, self.teacher = controller, policy, teacher
        self.scenario, self.texture = scenario, texture
        from .memory_reference import REFERENCES
        self.reference_mode = scenario if scenario in REFERENCES else None
        self.memory_case, restore_snapshot, memory_u = self._memory_restore(
            memory_case, scenario, controller,
            str(getattr(policy or teacher, 'device', 'cpu' if self.reference_mode else '')),
            restore_snapshot, replace_controller, memory_u)
        if self.memory_case is not None:
            from .memory import sha256
            writer.manifest.update(memory_case=copy.deepcopy(self.memory_case),
                memory_case_sha256=sha256(self.memory_case),
                acquisition_protocol_sha256=self.memory_case['acquisition_protocol_sha256'])
        self.memory = self.world_task_state = None
        self.task_state = None
        self.body_state = None
        self.composition = None
        if scenario in ("calibrated-wheel-compensation", "adaptive-wheel-calibration", "adaptive-encoder-homing"):
            from .profiles import validate
            validate(scenario, texture, controller)
        if scenario in ('exploration-landmarks', 'encoder-homing') and controller == 'teacher':
            raise ValueError('Declared tasks cannot use the privileged geometry teacher')
        self.revision = 0
        self.eyes = {"left": True, "right": True}
        self.last_transition = None
        self._initial_teacher = copy.deepcopy(teacher) if controller == "teacher" else None
        self._teacher_reset_identity = _teacher_fingerprint(self._initial_teacher)
        self.seed = _seed(seed)
        if scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing') and self.seed != 1:
            raise ValueError('Measured calibration requires its declared seed 1')
        if restore_snapshot is not None and self.seed != self.memory_case['seed']:
            raise ValueError('Continuation seed differs from its exact acquisition case')
        self.run_id = writer.manifest.get("run_id", uuid.uuid4().hex)
        self.parent_run_id = None
        self.parent_event_prefix = None
        self.phase = "paused"
        self.episode = self.total_tick = self.episode_step = 0
        self.manual_action = np.zeros(2, dtype=np.float64)
        self.metrics = {}
        self.last_outcome = None
        self._episode_finished = False
        self._pending = deque()
        self._receipts, self._originals = {}, {}
        self._closed = self._restored = self._recording_failed = False
        self._session_exhausted = False
        self._reset_world()
        self._event("engine_opened", controller=controller, control_interval_seconds=dt)
        self._episode_started()
        if restore_snapshot is not None:
            from .memory import sha256
            from .snapshots import state_digest
            admission = {'source_run_id': restore_snapshot['application']['source_run_id'],
                'source_controller': restore_snapshot['application']['controller'],
                'snapshot_state_sha256': state_digest(restore_snapshot),
                'native_sha256': restore_snapshot['native_sha256'],
                'case_sha256': sha256(self.memory_case),
                'replace_controller': replace_controller,
                'memory_u_sha256': None if memory_u is None else sha256(memory_u)}
            if self.reference_mode:
                from .memory_reference import PROTOCOL, PROTOCOL_SHA256
                admission.update(mode=self.reference_mode, protocol_sha256=PROTOCOL_SHA256,
                                 source_scenario=restore_snapshot['application']['scenario'])
                self.writer.manifest.update(memory_reference_admission=admission, memory_reference_protocol=PROTOCOL)
                self._event('memory_reference_admitted', admission=admission)
            else:
                self.writer.manifest['memory_continuation_admission'] = admission
                self._event('memory_continuation_admitted', admission=admission)
            if memory_u is not None:
                self.restore_memory_branch(restore_snapshot, memory_u)
            else:
                self.restore_branch(restore_snapshot, replace_controller=replace_controller)

    @classmethod
    def _validate_memory_case(cls, value, scenario, controller):
        if value is None:
            return None
        from .memory_experiment import validate_world_case
        case = validate_world_case(value)
        if scenario != 'memory-passages' or controller == 'teacher' or case['acquisition'] and controller != 'manual':
            raise ValueError('Runtime memory case requires its declared profile/manual acquisition controller')
        return case

    @classmethod
    def _memory_restore(cls, value, scenario, controller, device,
                        snapshot, replace_controller, u):
        """One narrow atomic continuation exception; ordinary admission is unchanged."""
        if type(replace_controller) is not bool:
            raise ValueError('Controller replacement must be an explicit boolean')
        from .memory_reference import REFERENCES, validate_source
        reference = scenario in REFERENCES
        if snapshot is None:
            if reference or replace_controller or u is not None:
                raise ValueError('Memory continuation requires its source snapshot')
            return cls._validate_memory_case(value, scenario, controller), None, None
        from . import memory, memory_experiment, memory_task, memory_world
        from .snapshots import MAX_BYTES, MAX_METADATA, SCHEMA_VERSION, SNAPSHOT_KEYS
        case = memory_experiment.validate_world_case(value)
        if not case['acquisition'] or not reference and (scenario != 'memory-passages' or controller != 'flynn' or device != 'cpu'):
            raise ValueError('Atomic memory continuation requires an acquisition case and CPU FLYNN')
        if replace_controller and u is not None:
            raise ValueError('Controller and U replacement must be separate boundaries')
        if (type(snapshot) is not dict or set(snapshot) != SNAPSHOT_KEYS or
                type(snapshot.get('schema_version')) is not int or snapshot['schema_version'] != SCHEMA_VERSION):
            raise ValueError('Unsupported continuation snapshot')
        native = snapshot['native_data']
        if (type(native) is not bytes or not native or len(native) > MAX_BYTES or
                hashlib.sha256(native).hexdigest() != snapshot['native_sha256']):
            raise ValueError('Invalid continuation native bytes/hash')
        state = snapshot['application']
        if type(state) is not dict:
            raise ValueError('Continuation lacks application state')
        encoded = json.dumps(state, allow_nan=False, sort_keys=True, separators=(',', ':')).encode()
        if len(encoded) > MAX_METADATA:
            raise ValueError('Continuation application exceeds snapshot metadata bound')
        if reference:
            validate_source(snapshot, scenario, controller, device, replace_controller, u)
            world = memory_world.validate_state(state.get('world_task_state'))
            if memory.canonical_bytes(world.get('case')) != memory.canonical_bytes(case) or _seed(state.get('seed')) != case['seed']:
                raise ValueError('Reference case/seed differs from source')
            return case, copy.deepcopy(snapshot), None
        expected_controller = 'manual' if replace_controller else 'flynn'
        if (state.get('controller') != expected_controller or state.get('phase') != 'paused' or
                state.get('scenario') != scenario or state.get('execution_mode') not in ('live', 'policy', 'actions') or
                (replace_controller or u is not None) and state['execution_mode'] == 'actions'):
            raise ValueError('Continuation requires the declared paused source controller/mode')
        if _seed(state.get('seed')) != case['seed']:
            raise ValueError('Continuation source seed differs from its acquisition case')
        world = memory_world.validate_state(state.get('world_task_state'))
        if memory.canonical_bytes(world.get('case')) != memory.canonical_bytes(case):
            raise ValueError('Continuation case differs from destination')
        memory_task.validate_state(state.get('memory'))
        # Full application/tensor/runtime/RNG validation still precedes native mutation
        # in the existing restoration, after the fixed destination policy is loaded.
        return case, copy.deepcopy(snapshot), None if u is None else memory.validate_u(u)

    @classmethod
    def open(cls, repo_root, asset_root, output, controller="manual", device="cpu", seed=0,
             max_bytes=2 * 1024**3, scenario="reproduction", texture="checker", run_id=None,
             storage_budget=None, memory_case=None, expected_policy_identity=None, *, research_binding=None,
             restore_snapshot=None, replace_controller=False, memory_u=None):
        """Create an actual pinned runtime. The caller owns its process watchdog."""
        from .assets import load_manifest, prepare_graph, sha256_file, verify_assets
        from .doctor import diagnose
        from .records import RunWriter
        from .profiles import validate, configure_world, POPULATIONS

        if controller not in {"manual", "teacher", "flynn", *MALE_CONTROLLERS} or device not in {"cpu", "cuda"}:
            raise ValueError("unknown controller or device")
        if controller in MALE_CONTROLLERS and device != 'cpu':
            raise ValueError('Male pilot controllers require CPU')
        if controller not in MALE_CONTROLLERS and expected_policy_identity is not None:
            raise ValueError('Male policy identity requires a male controller')
        seed = _seed(seed)
        from .memory_reference import REFERENCES
        if scenario in REFERENCES:
            from .profiles import validate_reference
            profile = validate_reference(scenario, texture, controller)
        else:
            profile = validate(scenario, texture, controller)
        if scenario in ('calibrated-wheel-compensation','adaptive-wheel-calibration','adaptive-encoder-homing') and device != 'cpu':
            raise ValueError('Wheel calibration profiles require CPU')
        if scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing') and seed != 1:
            raise ValueError('Measured calibration requires its declared seed 1')
        memory_case, restore_snapshot, memory_u = cls._memory_restore(
            memory_case, scenario, controller, device, restore_snapshot, replace_controller, memory_u)
        if restore_snapshot is not None and seed != memory_case['seed']:
            raise ValueError('Continuation seed differs from its exact acquisition case')
        case_manifest = {}
        if memory_case is not None:
            from .memory import sha256
            case_manifest = {'memory_case': memory_case, 'memory_case_sha256': sha256(memory_case),
                'acquisition_protocol_sha256': memory_case['acquisition_protocol_sha256']}
        run_id = uuid.uuid4().hex if run_id is None else uuid.UUID(run_id).hex
        root, assets = Path(repo_root).resolve(), Path(asset_root).resolve()
        research_manifest = {}
        if research_binding is not None:
            from .male_research import Binding
            admitted = type(research_binding) is Binding
            if not admitted:
                from .male_recovery_research import Binding as RecoveryBinding
                admitted = type(research_binding) is RecoveryBinding
            if not admitted:
                from .male_recovery_heldout import Binding as RecoveryHeldoutBinding
                admitted = type(research_binding) is RecoveryHeldoutBinding
            if not admitted or controller not in MALE_CONTROLLERS or memory_case is not None:
                raise ValueError('unsupported trusted research binding')
            identity, research_arguments = research_binding.resolve(root, assets, controller, device, scenario, texture, expected_policy_identity)
            research_manifest = {'research': research_binding.provenance()}
        elif controller in MALE_CONTROLLERS:
            from .male_policy import resolve_profile
            identity, _ = resolve_profile(root, assets, controller, expected_policy_identity)
        os.environ.setdefault("MUJOCO_GL", "egl")
        os.environ.setdefault("MPLBACKEND", "Agg")
        writer = RunWriter(Path(output), {
            "schema_version": 1, "run_id": run_id, "profile": controller,
            "scenario": profile, "texture": texture, "population_names": list(POPULATIONS) if controller == 'flynn' else [],
            "population_columns": ["count", "mean", "min", "max"], "population_scale": [-1., 1.],
            "controller": controller, "seed": seed, "requested_device": device,
            "teacher_privileged": controller == "teacher",
            "observation_profile": profile['observation_profile'],
            "tick_contract": "input and pose before step; control, next_pose, reward and time after step",
            "sensor_order": ["collision", "collision_angle", "wind_cos", "wind_sin"],
            "control_interval_seconds": .02,
            "continuation_contract": {"float_atol": 1e-6, "float_rtol": 1e-6,
                "integer_and_camera_exact": True,
                "scope": "matching software/hardware regime; compare before claiming repeatability",
                "cuda_limit": "upstream CSR inference can vary even with identical inputs and deterministic algorithms enabled"},
            **case_manifest, **research_manifest,
        }, max_bytes=max_bytes, storage_budget=storage_budget)
        env = None
        try:
            diagnosis = diagnose(root, assets)
            writer.event("diagnostics", run_id=writer.manifest["run_id"], report=diagnosis)
            required = [check for check in diagnosis["checks"]
                        if check["name"] in {"python", "upstream"} or check["name"].startswith("dependency:")]
            if any(check["status"] != "ok" for check in required):
                raise RuntimeError("runtime diagnostics failed; see diagnostics event")
            import numpy as np
            import random
            import torch
            from .flynn import import_upstream, load_policy

            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)
            torch.set_num_threads(2)
            reference = import_upstream(root, "run_connectome_rnn_checkpoint")
            env = reference._make_env(None, profile['n_obstacles'], texture_mode=texture)
            configure_world(env)
            policy = teacher = None
            if controller == "flynn":
                if not verify_assets(root, assets)["ok"]:
                    raise ValueError("missing or corrupt pinned model assets")
                edge = prepare_graph(root, assets)
                item = next(item for item in load_manifest(root)["files"] if item["id"] == "checkpoint")
                policy = load_policy(root, edge, assets / item["path"], device, seed)
                writer.event("policy_loaded", run_id=writer.manifest["run_id"], provenance=policy.provenance)
            elif controller == "teacher":
                teacher = reference.PlannerAnalyticTeacher(arena_half_extent=env.arena, device="cpu")
            elif controller in MALE_CONTROLLERS:
                from .male_policy import load_pinned_policy
                if research_binding is None:
                    policy = load_pinned_policy(root, assets, controller, seed, identity)
                else:
                    policy = research_binding.load_policy(research_arguments, seed)
                    policy.provenance.update(policy_identity=identity, model_manifest_sha256=identity['model_manifest_sha256'],
                                             research=research_binding.provenance())
                writer.manifest['policy_identity'] = policy.provenance['policy_identity']
                writer.event('policy_loaded', run_id=writer.manifest['run_id'], provenance=policy.provenance)
            writer.event("environment", run_id=writer.manifest["run_id"], upstream_commit=load_manifest(root)["upstream_commit"],
                         lock_sha256=sha256_file(root / "uv.lock"),
                         source_sha256={str(path.relative_to(root)): sha256_file(path)
                                        for path in sorted((root / "src/palimpsest").glob("*.py"))})
            return cls(env, writer, controller, policy, teacher, seed, scenario, texture, memory_case=memory_case,
                       restore_snapshot=restore_snapshot, replace_controller=replace_controller, memory_u=memory_u)
        except BaseException as error:
            try:
                writer.finish({"error": {"type": type(error).__name__, "message": str(error)}}, status="failed")
            finally:
                try:
                    if env is not None:
                        try:
                            env.renderer.close()
                        finally:
                            env.close()
                finally:
                    writer.close()
            raise

    def _owner_only(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError("engine state belongs to its creating thread")

    def _active(self):
        self._owner_only()
        if self._closed:
            raise RuntimeError("engine is closed")

    def _event(self, kind, **data):
        self.writer.event(kind, run_id=self.run_id, episode=self.episode, tick=self.total_tick,
                          episode_step=self.episode_step, **data)

    def _reset_world(self, *, calibration_session=None):
        # Fixture environments reset themselves; the production environment uses real MjData.
        if type(self.env.data).__module__.split(".", 1)[0] == "mujoco":
            import mujoco
            mujoco.mj_resetData(self.env.model, self.env.data)
        self.observation, _ = self.env.reset(seed=self.seed)
        if self.scenario == 'memory-passages' or self.reference_mode:
            from . import memory, memory_task, memory_world
            self.world_task_state = memory_world.configure(self.env, memory_world.initial_state(case=self.memory_case))
            episode_id = f'episode-{self.episode}'
            if self.memory is None:
                self.memory = memory_task.initialize(
                    memory.seed_m(memory_world.initial_facts(self.world_task_state), []), {'version': 1, 'episodes': []},
                    memory.artifact(method='empty-v1'), episode_id=episode_id)
            else:
                self.memory = memory_task.reset(self.memory, episode_id=episode_id)
            self.observation = self.env._get_obs()
        if self.scenario in ('exploration-landmarks', 'encoder-homing'):
            from . import task_profiles
            task_profiles.configure_world(self.env)
            self.task_state = task_profiles.initialize(self.scenario, f'episode-{self.episode}',
                task_profiles.encoder_angles(self.env), task_profiles.body_calibration(self.env))
            self.observation = self.env._get_obs()
        if self.scenario == 'calibrated-wheel-compensation':
            from . import body_profile
            self.body_state = body_profile.configure(self.env, f'episode-{self.episode}')
            self.observation = self.env._get_obs()
        if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing'):
            from . import body_adaptation
            self.body_state = body_adaptation.configure(self.env,episode=self.episode,session=calibration_session)
            self.observation = self.env._get_obs()
        if self.scenario == 'adaptive-encoder-homing':
            from . import body_homing
            self.task_state = body_homing.initial_task(self.body_state)
            self.composition = body_homing.context()
        if type(self.env.model).__module__.startswith("mujoco"):
            from .profiles import validate_world
            validate_world(self.env, require_route=self.scenario == 'sparse-navigation')
        if self.controller in {"flynn", *MALE_CONTROLLERS}:
            self.policy.reset()
        elif self.controller == "teacher":
            self.teacher = copy.deepcopy(self._initial_teacher)
        self.manual_action[:] = 0.
        self.last_transition = None
        self.metrics = {"reward": 0., "contact_ticks": 0, "path_length": 0.}
        self._episode_finished = False

    def _episode_started(self):
        if "initial_world" not in self.writer.manifest:
            self.writer.manifest["initial_world"] = self.world()
        if self.memory is not None and 'initial_memory' not in self.writer.manifest:
            from .memory import sha256
            self.writer.manifest['initial_memory'] = {
                key: sha256(self.memory[key]) for key in ('m', 'e', 'u')}
        if self.task_state is not None:
            from .task_profiles import PROTOCOL
            self.writer.manifest['task_protocol'] = copy.deepcopy(PROTOCOL)
            self.writer.manifest['task_calibration'] = copy.deepcopy(self.task_state['odometry']['calibration'])
            self.writer.manifest['task_profile_sha256'] = self.task_state['profile_sha256']
        if self.body_state is not None:
            if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing'):
                from .body_adaptation import PROTOCOL, IDENTITY, inspect
                identity, body_view, event_kind = copy.deepcopy(IDENTITY), inspect(self.body_state), 'body_calibration_started'
            else:
                from .body_profile import PROTOCOL, profile_identity
                identity, body_view, event_kind = profile_identity(), self.body_state, 'body_loaded'
            self.writer.manifest['body_protocol'] = copy.deepcopy(PROTOCOL)
            self.writer.manifest['body_profile_identity'] = identity
            self.writer.manifest['body_contact_ownership'] = copy.deepcopy(self.env._body_contact_ownership)
            self.writer.manifest['body_runtime_world_profile'] = copy.deepcopy(self.env._body_runtime_world_profile)
            self._event('body_world_provenance', detail=self.env._body_runtime_world_profile)
            self._event(event_kind, identity=identity, state=body_view,
                        contact_ownership=self.env._body_contact_ownership,
                        actuator_gear=self.env.model.actuator_gear.tolist(), world=self.world())
        if self.scenario == 'adaptive-encoder-homing':
            from .body_homing import provenance
            self.writer.manifest['composition_provenance'] = provenance(self.env, self.world())
            self._event('body_homing_started', detail=self.writer.manifest['composition_provenance'],
                        derivation=self.composition['derivation'])
        self._event("episode_started", seed=self.seed, goal=self.env._goal_xy.tolist(),
                    obstacles=self.env._obstacle_xy.tolist(), initial_qpos=self.env.data.qpos.tolist(),
                    initial_qvel=self.env.data.qvel.tolist(),
                    reset_protocol=("authored measured calibration lane; fixed left gear .8, explicit probe/fitted reset, fresh encoders/controller"
                                    if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing') else
                                    "authored calibrated development lane; fixed left gear .8, loaded gains, fresh encoders/controller"
                                    if self.body_state is not None else
                                    "authored declared task layout; fresh local encoder, supervisor and controller state"
                                    if self.task_state is not None else
                                    "authored memory development layout; initial M, retained E/U, fresh episodic state"
                                    if self.memory is not None else "fresh physics and controller episode state; upstream seeded layout"),
                    world=self.world(), revision=self.revision, eyes=self.eyes)

    def _end_episode(self, reason, **details):
        if not self._episode_finished:
            self.last_outcome = {"reason": reason, "episode": self.episode,
                                 "steps": self.episode_step, **details}
            self._event("episode_finished", outcome=self.last_outcome, metrics=self.metrics)
            self._episode_finished = True

    def _validate_command(self, value):
        if not isinstance(value, dict) or not {"id", "kind", "expected_state", "expected_episode"} <= set(value) or set(value) - {"id", "kind", "expected_state", "expected_episode", "expected_revision", "payload"}:
            raise ValueError("command keys must be id, kind, expected_state, expected_episode, optional payload")
        if not isinstance(value["id"], str) or not 1 <= len(value["id"]) <= 128:
            raise ValueError("command id must contain 1 to 128 characters")
        if not isinstance(value["kind"], str) or value["kind"] not in KINDS or not isinstance(value["expected_state"], str) or value["expected_state"] not in PHASES:
            raise ValueError("unknown command kind or expected state")
        if type(value["expected_episode"]) is not int or value["expected_episode"] < 0:
            raise ValueError("expected_episode must be a nonnegative integer")
        if 'expected_revision' in value and (type(value['expected_revision']) is not int or value['expected_revision'] < 0):
            raise ValueError('expected_revision must be a nonnegative integer')
        if value["kind"] == "intervene":
            # Validate the small wire shape before copying or retaining any payload.
            from .interventions import _xy
            payload = value.get("payload", {})
            if not isinstance(payload, dict) or len(payload) not in (2, 3):
                raise ValueError("intervene requires only kind, xy and optional obstacle index")
            kind = payload.get("kind")
            if kind not in ("move_goal", "move_obstacle"):
                raise ValueError("unsupported intervention kind")
            keys = {"kind", "xy", "index"} if kind == "move_obstacle" else {"kind", "xy"}
            if set(payload) != keys:
                raise ValueError("invalid intervention payload keys")
            _xy(payload["xy"])
            if kind == "move_obstacle" and (type(payload["index"]) is not int or payload["index"] < 0):
                raise ValueError("obstacle index must be a nonnegative integer")
        command = copy.deepcopy(value)
        payload = command.setdefault("payload", {})
        if not isinstance(payload, dict):
            raise ValueError("command payload must be an object")
        try:
            json.dumps(command, allow_nan=False)
        except (ValueError, TypeError) as error:
            raise ValueError("command must contain finite JSON values") from error
        kind = command["kind"]
        if kind == "set_eyes":
            if set(payload) != {'left', 'right'} or any(type(v) is not bool for v in payload.values()):
                raise ValueError('set_eyes requires boolean left and right enabled flags')
        elif kind == "set_action":
            if set(payload) != {"action"}:
                raise ValueError("set_action requires only an action vector")
            _action(payload["action"], manual=True)
            if self.body_state is not None and self.scenario not in ('adaptive-wheel-calibration', 'adaptive-encoder-homing'):
                from .body_profile import plan_action
                plan_action(payload['action'])
        elif kind == "reset":
            if set(payload) - {"seed"}:
                raise ValueError("reset accepts only an optional seed")
            if "seed" in payload:
                _seed(payload["seed"])
        elif kind != "intervene" and payload:
            raise ValueError(f"{kind} does not accept a payload")
        return command

    def submit(self, command):
        self._active()
        command = self._validate_command(command)
        identifier = command["id"]
        if identifier in self._originals:
            if command != self._originals[identifier]:
                raise ValueError("command id was already used with different content")
            return copy.deepcopy(self._receipts[identifier])
        if self._recording_failed:
            raise RuntimeError("recording failed; a new session is required")
        if len(self._pending) >= self.MAX_QUEUE:
            raise RuntimeError("command queue is full")
        if self._session_exhausted or len(self._originals) >= self.MAX_IDS:
            error = RuntimeError("idempotency limit reached; a new session is required")
            self._session_exhausted = True
            self._fail(error)
            raise error
        receipt = {"id": identifier, "kind": command["kind"], "status": "queued",
                   "received_run_id": self.run_id, "received_episode": self.episode,
                   "received_tick": self.total_tick}
        try:
            self._event("command_received", command=command, receipt=receipt)
        except Exception as error:
            self._fail(error)
            raise
        self._originals[identifier] = command
        self._receipts[identifier] = receipt
        self._pending.append(command)
        return copy.deepcopy(receipt)

    def _command_result(self, command, status, **data):
        result = {**self._receipts[command["id"]], "status": status,
                  "applied_run_id": self.run_id, "applied_episode": self.episode,
                  "applied_tick": self.total_tick, "applied_revision": self.revision, **data}
        self._event("command_" + status, id=command["id"], command_kind=command["kind"], result=result)
        self._receipts[command["id"]] = result

    def _apply(self, command):
        kind, payload = command["kind"], command["payload"]
        if command["expected_state"] != self.phase or command["expected_episode"] != self.episode:
            raise CommandRejected("stale expected state or episode")
        if command.get('expected_revision', self.revision) != self.revision:
            raise CommandRejected('stale expected revision')
        if kind != "reset" and self.phase not in {"paused", "running"}:
            raise CommandRejected("terminal episode requires an explicit reset")
        adaptive = self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing')
        if self.reference_mode and kind not in ('run', 'pause', 'step', 'stop'):
            raise CommandRejected('Fixed reference permits only run, pause, step and stop')
        if kind == 'calibration-next' and not adaptive:
            raise CommandRejected('calibration-next requires measured calibration profile')
        if adaptive and kind in ('run','step') and self.body_state['phase'] not in ('collecting','fitted'):
            raise CommandRejected('Complete calibration trial waits for explicit calibration-next or Reset')
        if adaptive and kind == 'intervene':
            raise CommandRejected('Measured calibration retains its declared authored world')
        if adaptive and kind == 'reset' and payload.get('seed',self.seed)!=1:
            raise CommandRejected('Measured calibration retains declared seed 1')
        if kind == "step":
            if self.phase != "paused":
                raise CommandRejected("step requires a paused engine")
        elif kind == "run":
            self.phase = "running"
        elif kind == "pause":
            self.phase = "paused"
        elif kind == "stop":
            self.phase = "stopped"
            self.manual_action[:] = 0.
            if self.task_state is not None:
                self.env.data.ctrl[:] = 0.
            self._end_episode("user_stop")
        elif kind == "reset":
            self._end_episode("reset")
            self.seed = payload.get("seed", self.seed)
            self.episode += 1
            self.episode_step = 0
            self._reset_world()
            self.phase = "paused"
            self.last_outcome = None
            self._episode_started()
        elif kind == 'calibration-next':
            from . import body_adaptation
            try:
                next_session = body_adaptation.calibration_next(self.body_state,application_phase=self.phase)
                body_adaptation.validate_native(self.body_state,self.env.model,self.env.data,self.env)
            except ValueError as error:
                raise CommandRejected(str(error)) from error
            # All logical preconditions checked before closing/resetting native state.
            self._end_episode('calibration_next')
            self.episode = next_session['episode']
            self.episode_step = 0
            self._reset_world(calibration_session=next_session)
            self.phase = 'paused'
            self.last_outcome = None
            self._episode_started()
        elif kind == "set_action":
            if self.controller != "manual":
                raise CommandRejected("set_action requires the manual controller")
            if self.body_state is not None:
                from .body_profile import plan_action
                try:
                    if adaptive:
                        from .body_adaptation import plan_action as measured_plan
                        measured_plan(self.body_state,payload['action'])
                    else:
                        plan_action(payload['action'])
                except ValueError as error:
                    raise CommandRejected(str(error)) from error
            self.manual_action = _action(payload["action"], manual=True)
        elif kind == "set_eyes":
            self.eyes = payload.copy()
            self.last_transition = None
            self._event('eyes_changed', eyes=self.eyes)
        elif kind == "intervene":
            from .interventions import apply_intervention
            try:
                result = apply_intervention(self.env, payload, teacher=self.teacher)
            except ValueError as error:
                raise CommandRejected(str(error)) from error
            self.observation = self.env._get_obs()
            self.last_transition = None
            self._event("intervention", id=command["id"], change=result)
        if kind != 'set_action':
            self.revision += 1
        self._command_result(command, "applied")
        return kind == "step"

    def _fail(self, error, command=None):
        self.phase = "failed"
        self.revision += 1
        self.manual_action[:] = 0.
        if self.task_state is not None:
            self.env.data.ctrl[:] = 0.
        self.last_outcome = {"reason": "runtime_failure", "episode": self.episode,
                             "steps": self.episode_step, "type": type(error).__name__,
                             "message": str(error), "policy_diagnostics": getattr(self.policy, "failure_diagnostics", None)}
        if command is not None:
            self.last_outcome["command_id"] = command["id"]
            self._receipts[command["id"]] = {**self._receipts[command["id"]], "status": "failed",
                "applied_run_id": self.run_id, "applied_episode": self.episode,
                "applied_tick": self.total_tick, "reason": str(error)}
        try:
            self._event("runtime_failure", error=self.last_outcome)
            self._episode_finished = True
        except (OSError, ValueError, RuntimeError):
            self._recording_failed = True

    def _step(self, action_override=None):
        import numpy as np
        from .evaluate import outcome

        obs = self.observation
        task_hold = False
        if self.task_state is not None:
            from . import task_profiles
            packet = task_profiles.capture(self.env, self.task_state, self.episode_step)
            if self.scenario == 'adaptive-encoder-homing':
                self.composition['encoder_packet'] = {key: copy.deepcopy(packet[key]) for key in ('tick', 'time_s', 'angles_rad')}
            self._event('task_sensed', packet=packet)
            self.task_state, bearing, task_hold, decisions = task_profiles.advance(self.task_state, packet)
            for decision in decisions:
                self._event('task_decision', detail=decision)
            self._event('task_cue', bearing=bearing, hold=task_hold)
            self._event('task_inspected', task=copy.deepcopy(self.task_state))
            obs = {**obs, 'sensors': {**obs['sensors'], 'wind_direction': bearing}}
            if bool(obs['sensors']['collision']):
                raise ValueError('Declared task contact: control halted before physics step')
        reference_inputs = None
        if self.reference_mode:
            from . import memory, memory_reference, memory_task, memory_world
            if (memory.sha256(self.memory) != self._reference_memory_sha256
                    or action_override is not None and self.writer.manifest.get('execution_mode') != 'actions'):
                raise ValueError('Reference memory changed or undeclared action override')
            self.world_task_state, changes = memory_world.advance_world(self.env, self.world_task_state, self.episode_step)
            if changes:
                self.revision += 1
            for change in changes:
                self._event('memory_world_changed', detail=change)
                if change['kind'] == 'memory_gate_applied':
                    self._event('intervention', change=change['intervention'], origin='memory_world_schedule')
                    if self.teacher is not None:
                        from .interventions import invalidate_geometry
                        retained = memory_reference.teacher_control_hash(self.teacher)
                        invalidate_geometry(self.env, self.teacher)
                        if memory_reference.teacher_control_hash(self.teacher) != retained:
                            raise ValueError('Teacher invalidation changed retained control state')
                        self._event('memory_reference_teacher_invalidated',
                            cleared=['environment-map-cache', 'drawing', 'teacher-path'],
                            retained=['PID', 'reverse-recovery', 'VFH-hysteresis'], retained_state_sha256=retained)
            if changes:
                obs = self.observation = self.env._get_obs()
            world, pose, occluders = memory_world.sensing_inputs(self.env, self.world_task_state)
            packet = memory_task.capture_symbolic(world, pose, occluders, episode_id='episode-0', tick=self.episode_step)
            self._event('memory_reference_sensed', packet=packet, role='audit-only-no-memory-advance',
                        frozen_memory_sha256=self._reference_memory_sha256)
            if self.reference_mode == 'memory-reference-sensor-only':
                reference_inputs = memory_reference.sensor_input(packet, bool(obs['sensors']['collision']))
                self._event('memory_reference_input', inputs=reference_inputs)
                obs = {**obs, 'sensors': {**obs['sensors'], 'wind_direction': reference_inputs['bearing']}}
            elif self.reference_mode == 'memory-reference-original-flynn':
                self._event('memory_reference_input', inputs={'collision': bool(obs['sensors']['collision']),
                    'collision_angle': None if obs['sensors']['collision_angle'] is None else float(obs['sensors']['collision_angle']),
                    'wind_direction': list(map(float, obs['sensors']['wind_direction']))}, cameras='recorded-rgb-eyes',
                    unequal_information='upstream-bearing-derived-from-true-pose-and-goal')
            else:
                self._event('memory_reference_input', inputs={'pose': pose,
                    'goal_xy': list(map(float, self.env._goal_xy)),
                    'obstacles_xy': self.env._obstacle_xy.tolist()}, privileged=True)
        elif self.memory is not None:
            from . import memory_task, memory_world
            self.world_task_state, changes = memory_world.advance_world(self.env, self.world_task_state, self.episode_step)
            if changes:
                self.revision += 1
            for change in changes:
                self._event('memory_world_changed', detail=change)
                if change['kind'] == 'memory_gate_applied':
                    self._event('intervention', change=change['intervention'], origin='memory_world_schedule')
            if changes:
                obs = self.observation = self.env._get_obs()
            world, pose, occluders = memory_world.sensing_inputs(self.env, self.world_task_state)
            packet = memory_task.capture_symbolic(world, pose, occluders,
                episode_id=self.memory['episode_id'], tick=self.episode_step)
            self._event('memory_sensed', packet=packet)
            self.memory, bearing, decisions = memory_task.advance_memory(self.memory, packet)
            for decision in decisions:
                self._event('memory_decision', detail=decision,
                            route_anchor={'stage': 'pre-control', 'xy': pose[:2]})
            self._event('memory_cue', bearing=bearing,
                        raw_upstream_bearing=list(map(float, obs['sensors']['wind_direction'])))
            self._event('memory_inspected', memory=memory_task.inspect(self.memory))
            obs = {**obs, 'sensors': {**obs['sensors'], 'wind_direction': bearing}}
        sensors = obs["sensors"]
        sensor_vector = np.array([float(sensors["collision"]),
                                 0. if sensors["collision_angle"] is None else float(sensors["collision_angle"]),
                                 *sensors["wind_direction"]], dtype=np.float32)
        if sensor_vector.shape != (4,) or not np.isfinite(sensor_vector).all():
            raise ValueError("invalid declared sensors; world not stepped")
        raw_cameras = {name: obs[name].copy() for name in ("cam_left", "cam_right")}
        cameras = self.effective_cameras()
        if any(image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) == 0 for image in cameras.values()):
            raise ValueError("camera observations must be HWC uint8 RGB arrays")
        pose = np.array([*self.env._base_xy(), self.env._base_yaw()], dtype=np.float64)
        started = time.perf_counter()
        neural = {}
        if action_override is not None:
            action = action_override
        elif self.reference_mode == 'memory-reference-sensor-only':
            from .memory_reference import sensor_action
            action = sensor_action(reference_inputs)
        elif self.controller in {"flynn", *MALE_CONTROLLERS}:
            projected = {**cameras, "sensors": {name: copy.deepcopy(sensors[name])
                         for name in ("collision", "collision_angle", "wind_direction")}}
            result = self.policy.act(projected)
            action = result["action"]
            neural = {key: result[key] for key in ("encoded_input", "raw_output")}
        elif self.controller == "teacher":
            action = self.teacher.act(self.env)
        else:
            action = self.manual_action
        action = _action(action, manual=self.controller == "manual")
        if task_hold:
            if action_override is not None and np.any(action != 0.):
                raise ValueError('Recorded action violates stopped-dwell hold')
            action = np.zeros(2, dtype=action.dtype)
        latency = time.perf_counter() - started
        started = time.perf_counter()
        body_arrays = {}
        if self.body_state is not None:
            from . import body_profile
            try:
                body_step = body_profile.step
                if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing'):
                    from .body_adaptation import step as body_step
                result, state, packet, body_arrays = body_step(self.env, self.body_state,
                    (np.zeros(2, dtype=np.float64) if task_hold else self.manual_action)
                    if self.scenario == 'adaptive-encoder-homing' else self.manual_action,
                    self.episode_step, action_override=action_override)
            except body_profile.BodyFailure as error:
                self._event('body_failed', detail=error.packet, reason=str(error))
                raise
            self.body_state = state
            action = np.asarray(packet['command']['applied_action'], np.float64)
            body_view = state
            if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing'):
                from .body_adaptation import inspect
                body_view = inspect(state)
            self._event('body_measured', detail=body_profile.measurement_event(packet), state=body_view)
            next_obs, reward, terminated, truncated, info = result
        else:
            next_obs, reward, terminated, truncated, info = self.env.step(action)
        step_latency = time.perf_counter() - started
        recorded_step = self.episode_step
        populations = self._population_stats() if action_override is None else []
        self.total_tick += 1
        self.episode_step += 1
        self.observation = next_obs
        next_pose = np.array([*self.env._base_xy(), self.env._base_yaw()], dtype=np.float64)
        self.writer.tick(self.episode, recorded_step, **cameras, sensors=sensor_vector, action=action,
                         control=self.env.data.ctrl.copy(), pose=pose, next_pose=next_pose,
                         reward=np.array(reward), simulation_time=np.array(self.env.data.time),
                         latency=np.array(latency), step_latency=np.array(step_latency), **neural, **body_arrays,
                         raw_cam_left=raw_cameras['cam_left'], raw_cam_right=raw_cameras['cam_right'],
                         eyes=np.array([self.eyes['left'], self.eyes['right']], dtype=np.bool_), revision=np.array(self.revision),
                         population_stats=np.array([[p[key] for key in ('count', 'mean', 'min', 'max')]
                                                    for p in populations], dtype=np.float64).reshape(-1, 4))
        self.last_transition = {"episode": self.episode, "tick": recorded_step,
            **cameras, "sensors": sensor_vector.copy(), "eyes": self.eyes.copy(),
            "action": action.copy(), "control": self.env.data.ctrl.copy(), **neural, **body_arrays,
            "populations": populations, "latency": latency, "step_latency": step_latency}
        self.metrics["reward"] += float(reward)
        self.metrics["contact_ticks"] += int(bool(sensors["collision"]))
        self.metrics["path_length"] += float(np.linalg.norm(next_pose[:2] - pose[:2]))
        if self.task_state is not None:
            # Goal distance/reward remain evaluator data, never a task cue or
            # completion criterion. No hidden true-pose speed establishes dwell.
            reason = ('collision' if next_obs['sensors']['collision'] else
                      'stalled' if info.get('stalled') else
                      'task_completed' if self.task_state['phase'] == 'complete' else
                      'time_limit' if truncated else None)
            terminated = reason in ('collision', 'stalled', 'task_completed')
        elif self.memory is not None and (self.memory['active'] is not None or self.memory['requests']):
            # Reaching the common goal does not complete a pending inspection.
            reason = ('stalled' if info.get('stalled') else
                      'collision' if self.env.end_on_collision and next_obs['sensors']['collision'] else
                      'time_limit' if truncated else None)
            terminated = reason in ('stalled', 'collision')
        else:
            reason = outcome(terminated, truncated, info, self.env.goal_radius)
        if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing') and not reason:
            if self.body_state['phase'] in ('trial_complete','fit_complete','rejected'):
                self.phase = 'paused'
                self.revision += 1
                from .body_adaptation import inspect
                self._event('body_calibration_boundary', state=inspect(self.body_state))
        if reason:
            self.phase = "terminated" if terminated else "truncated"
            self.revision += 1
            if self.task_state is not None:
                self.env.data.ctrl[:] = 0.
                details = {'upstream_goal_distance_m': float(info['dist_to_goal']),
                           'task_phase': self.task_state['phase'],
                           'completed_inspection_ids': self.task_state['completed_ids']}
                if self.scenario in ('encoder-homing','adaptive-encoder-homing'):
                    from .memory_world import START_POSE
                    body_homing_origin = None
                    if self.scenario == 'adaptive-encoder-homing':
                        from .body_homing import PROTOCOL as homing_protocol
                        body_homing_origin = homing_protocol['body_protocol']['start_pose'][:2]
                    odometry = self.task_state['odometry']
                    details.update(evaluator_actual_home_distance_m=math.dist(next_pose[:2],
                        body_homing_origin if self.scenario == 'adaptive-encoder-homing' else START_POSE[:2]),
                        estimated_home_distance_m=math.hypot(odometry['x_m'], odometry['y_m']))
                self._end_episode(reason, **details)
            else:
                self._end_episode(reason, final_distance=float(info["dist_to_goal"]))

    def advance(self, action_override=None):
        self._active()
        if self._recording_failed or self._session_exhausted:
            return self.public_state()
        active_command = None
        try:
            if action_override is not None:
                action_override = _action(action_override, manual=self.controller == 'manual')
                self.writer.manifest.update(execution_mode='actions', inference_executed=False,
                                            population_names=[])
            single_step = False
            while self._pending:
                command = active_command = self._pending.popleft()
                try:
                    single_step = self._apply(command)
                except CommandRejected as error:
                    self._command_result(command, "rejected", reason=str(error))
                active_command = None
                if single_step:
                    break
            if single_step or self.phase == "running":
                if self.writer.manifest.get('execution_mode') == 'actions' and action_override is None:
                    raise ValueError('Action replay requires a recorded action before stepping')
                self._step(action_override)
        except Exception as error:
            self._fail(error, active_command)
        return self.public_state()

    def public_state(self):
        self._owner_only()
        body_view = self.body_state
        if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing'):
            from .body_adaptation import inspect
            body_view = inspect(self.body_state)
        return copy.deepcopy({"run_id": self.run_id, "parent_run_id": self.parent_run_id,
                              "controller": self.controller, "phase": self.phase,
                              "scenario": self.scenario, "texture": self.texture,
                              "revision": self.revision, "eyes": self.eyes,
                              "simulation_time": float(self.env.data.time),
                              "episode": self.episode, "episode_step": self.episode_step,
                              "total_tick": self.total_tick, "pending_commands": len(self._pending),
                              "metrics": self.metrics, "last_outcome": self.last_outcome,
                              "task": self.task_state,
                              **({"body": body_view} if self.body_state is not None else {}),
                              "closed": self._closed})

    @property
    def receipts(self):
        self._owner_only()
        return copy.deepcopy(self._receipts)

    def world(self):
        self._owner_only()
        env = self.env
        return {'arena': float(env.arena), 'pose': [*map(float, env._base_xy()), float(env._base_yaw())],
                'obstacles': [[*map(float, env.data.geom_xpos[index, :2]), float(env.model.geom_size[index, 0])]
                              for index in env.obstacle_ids],
                'goal': [*map(float, env._goal_xy), float(env.model.site_size[env.goal_site_id, 0])]}

    def effective_cameras(self):
        self._owner_only()
        result = {name: self.observation[name].copy() for name in ('cam_left', 'cam_right')}
        for eye, enabled in self.eyes.items():
            if not enabled:
                result['cam_' + eye].fill(0)
        return result

    def _population_stats(self):
        if self.controller in MALE_CONTROLLERS:
            return []
        agent = getattr(self.policy, 'agent', None)
        if agent is None:
            return []
        import torch
        result = []
        for name in ('visual_left', 'visual_right', 'descending'):
            if name == 'descending':
                indices = agent.cell.output_nodes
            else:
                eye = name.split('_')[1]
                segments = [agent.input_splits['pr_' + layer + '_' + eye] for layer in ('L1', 'L2', 'L3')]
                indices = torch.cat([agent.cell.input_nodes[start:end] for start, end in segments]).unique()
            values = self.policy.hidden[0, indices]
            count = values.numel()
            result.append({'name': name, 'count': count, 'mean': float(values.mean()) if count else 0.,
                           'min': float(values.min()) if count else 0., 'max': float(values.max()) if count else 0.,
                           'scale': [-1., 1.]})
        return result

    def preview(self, payload):
        self._active()
        if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing'):
            raise ValueError('Measured calibration retains its declared authored world')
        if self.phase not in {'paused', 'running'}:
            raise ValueError('Preview requires an active episode')
        from .interventions import apply_intervention
        return {'revision': self.revision, 'change': apply_intervention(self.env, payload, dry_run=True)}

    def pause_for_disconnect(self):
        """Owner-only safety boundary, independent of ordinary command capacity."""
        self._active()
        self.manual_action[:] = 0.
        if self.task_state is not None:
            self.env.data.ctrl[:] = 0.
        if self._recording_failed:
            return self.public_state()
        try:
            while self._pending:
                self._command_result(self._pending.popleft(), 'rejected', reason='browser disconnected')
            if self.phase == 'running':
                self.phase = 'paused'
            self.revision += 1
            self._event('browser_disconnected', revision=self.revision, manual_action=[0., 0.])
        except Exception as error:
            self._fail(error)
        return self.public_state()

    def application_state(self):
        self._active()
        if self.phase != "paused":
            raise ValueError("application snapshots require a paused boundary")
        try:
            self.writer.flush()
        except Exception as error:
            self._fail(error)
            raise
        digest, size, count = hashlib.sha256(), 0, 0
        with (self.writer.path / "events.jsonl").open("rb") as events:
            while data := events.read(1024 * 1024):
                digest.update(data)
                size += len(data)
                count += data.count(b"\n")
        from .snapshots import controller_hashes
        return copy.deepcopy({"schema_version": 7 if self.scenario == 'adaptive-encoder-homing' else 6 if self.scenario == 'adaptive-wheel-calibration' else 5 if self.body_state is not None else 4,
            **({"composition": self.composition} if self.scenario == 'adaptive-encoder-homing' else {}),
            **({"body_state": self.body_state} if self.body_state is not None else {}), "source_run_id": self.run_id,
            "execution_mode": self.writer.manifest.get('execution_mode', 'live'),
            "memory": self.memory, "world_task_state": self.world_task_state,
            "task_state": self.task_state,
            "controller_tensors": controller_hashes(self.policy) if self.memory is not None else None,
            "revision": self.revision, "eyes": self.eyes, "scenario": self.scenario, "texture": self.texture,
            "event_prefix": {"sha256": digest.hexdigest(), "size_bytes": size, "event_count": count},
            "teacher_reset_identity": self._teacher_reset_identity,
            "controller": self.controller, "episode": self.episode, "total_tick": self.total_tick,
            "episode_step": self.episode_step, "phase": self.phase, "manual_action": self.manual_action.tolist(),
            "metrics": self.metrics, "last_outcome": self.last_outcome, "seed": self.seed,
            "episode_finished": self._episode_finished, "pending_commands": list(self._pending),
            "session_exhausted": self._session_exhausted, "recording_failed": self._recording_failed,
            "receipts": self._receipts, "original_commands": self._originals})

    def validate_application(self, state):
        """Validate a copied description before the snapshot layer mutates the world."""
        self._active()
        if self.phase != "paused" or self.total_tick or self.episode or self._originals or self._restored:
            raise ValueError("application restore requires a fresh paused destination")
        state = copy.deepcopy(state)
        if (type(state) is dict and state.get('schema_version') == 2 and self.scenario != 'memory-passages'
                and not {'memory', 'world_task_state', 'controller_tensors', 'execution_mode'} & state.keys()):
            # Legacy application snapshots have no artificial-memory state.
            state.update(schema_version=3, memory=None, world_task_state=None, controller_tensors=None, execution_mode='live')
        if (type(state) is dict and state.get('schema_version') == 3
                and self.scenario not in ('exploration-landmarks', 'encoder-homing') and 'task_state' not in state):
            state.update(schema_version=4, task_state=None)
        expected = {"schema_version", "source_run_id", "event_prefix", "teacher_reset_identity", "controller", "episode", "total_tick",
                    "revision", "eyes", "scenario", "texture",
                    "episode_step", "phase", "manual_action", "metrics", "last_outcome", "seed",
                    "episode_finished", "pending_commands", "session_exhausted", "recording_failed",
                    "receipts", "original_commands", "memory", "world_task_state", "controller_tensors", "execution_mode", "task_state"}
        schema = 4
        if self.body_state is not None:
            schema = 7 if self.scenario == 'adaptive-encoder-homing' else 6 if self.scenario == 'adaptive-wheel-calibration' else 5
            expected.add("body_state")
            if self.scenario == 'adaptive-encoder-homing':
                expected.add("composition")
        if not isinstance(state, dict) or set(state) != expected or type(state["schema_version"]) is not int or state["schema_version"] != schema or state["controller"] != self.controller or state["phase"] != "paused":
            raise ValueError("incompatible application state or non-paused snapshot")
        if state["teacher_reset_identity"] != self._teacher_reset_identity:
            raise ValueError("teacher reset baseline identity differs")
        if state['execution_mode'] not in ('live', 'policy', 'actions'):
            raise ValueError('Unknown snapshot execution mode')
        try:
            json.dumps(state, allow_nan=False)
        except (ValueError, TypeError) as error:
            raise ValueError("application state must contain finite JSON values") from error
        for key in ("episode", "total_tick", "episode_step", "revision"):
            if type(state[key]) is not int or state[key] < 0:
                raise ValueError(f"invalid {key}")
        if state['scenario'] != self.scenario or state['texture'] != self.texture:
            raise ValueError('Snapshot scenario/texture differs')
        if type(state['eyes']) is not dict or set(state['eyes']) != {'left', 'right'} or any(type(v) is not bool for v in state['eyes'].values()):
            raise ValueError('Invalid snapshot eye settings')
        if state["episode_step"] > state["total_tick"] or state["episode_step"] > 600:
            raise ValueError("invalid episode step count")
        if self.body_state is not None:
            if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing'):
                from .body_adaptation import IDENTITY, validate_session
                if self.env._body_profile_identity != IDENTITY or state['seed']!=1:
                    raise ValueError('Adaptive profile/seed differs')
                state['body_state'] = validate_session(state['body_state'],episode=state['episode'],episode_step=state['episode_step'])
                if state['body_state']['phase']=='fitted_terminal':
                    raise ValueError('Terminal calibration state cannot restore as paused')
            else:
                from .body_profile import validate_state
                state['body_state'] = validate_state(state['body_state'], self.env._body_profile_identity,
                    episode=state['episode'], episode_step=state['episode_step'])
        if self.scenario == 'memory-passages' or self.reference_mode:
            from . import memory_task, memory_world
            from .snapshots import controller_hashes
            state['memory'] = memory_task.validate_state(state['memory'])
            state['world_task_state'] = memory_world.validate_state(state['world_task_state'])
            if state['world_task_state'].get('case') != self.memory_case:
                raise ValueError('Snapshot runtime memory case differs from destination')
            if self.memory_case is not None and state['memory']['initial_m'] != {'version': 1, 'facts': memory_world.initial_facts(state['world_task_state'])}:
                raise ValueError('Snapshot initial factual bank differs from its runtime case')
            cursor = state['memory']['cursor']
            previous = state['episode_step'] - 1 if state['episode_step'] else None
            memory_previous = previous
            if self.reference_mode:
                from .memory_reference import validate_memory
                validate_memory(state['memory'])
                if state['episode'] != 0 or state['total_tick'] != state['episode_step'] or not 300 <= state['episode_step'] <= 600:
                    raise ValueError('Reference requires its single bounded source episode')
                memory_previous = 299
            if (state['memory']['episode_id'] != f"episode-{state['episode']}" or
                    (None if cursor is None else cursor['tick']) != memory_previous or
                    state['world_task_state']['last_tick'] != previous):
                raise ValueError('Memory/world cursor differs from paused application boundary')
            if state['controller_tensors'] != controller_hashes(self.policy):
                raise ValueError('Actual graph buffers or learned parameters differ')
        elif any(state[key] is not None for key in ('memory', 'world_task_state', 'controller_tensors')):
            raise ValueError('Memory state requires the memory task profile')
        if self.scenario == 'adaptive-encoder-homing':
            from .body_homing import validate_components
            validate_components(state)
        elif self.task_state is not None:
            from .task_profiles import validate_state
            state['task_state'] = validate_state(state['task_state'])
            task = state['task_state']
            if (task['scenario'] != self.scenario or task['profile_sha256'] != self.task_state['profile_sha256']
                    or task['episode_id'] != f"episode-{state['episode']}"
                    or task['last_tick'] != (state['episode_step'] - 1 if state['episode_step'] else None)
                    or task['phase'] == 'complete'):
                raise ValueError('Task identity/cursor differs from paused application boundary')
        elif state['task_state'] is not None:
            raise ValueError('Task state requires a declared exploration/homing profile')
        if not isinstance(state["source_run_id"], str) or not state["source_run_id"] or state["source_run_id"] == self.run_id or type(state["episode_finished"]) is not bool:
            raise ValueError("invalid source identity or episode flag")
        if state["session_exhausted"] is not False or state["recording_failed"] is not False:
            raise ValueError("a failed recording or exhausted session cannot continue")
        prefix = state["event_prefix"]
        if not isinstance(prefix, dict) or set(prefix) != {"sha256", "size_bytes", "event_count"} or any(type(prefix[key]) is not int or prefix[key] < 0 for key in ("size_bytes", "event_count")) or not isinstance(prefix["sha256"], str) or len(prefix["sha256"]) != 64 or any(char not in "0123456789abcdef" for char in prefix["sha256"]):
            raise ValueError("invalid durable event prefix")
        _action(state["manual_action"], manual=True)
        if self.body_state is not None:
            if self.scenario in ('adaptive-wheel-calibration', 'adaptive-encoder-homing'):
                from .body_adaptation import plan_action
                if state['body_state']['phase']=='fitted':
                    plan_action(state['body_state'],state['manual_action'])
                elif state['manual_action'] != [0.,0.]:
                    raise ValueError('Fixed probe cannot retain user manual intent')
            else:
                from .body_profile import plan_action
                plan_action(state['manual_action'])
        _seed(state["seed"])
        originals, receipts, pending = state["original_commands"], state["receipts"], state["pending_commands"]
        if not isinstance(originals, dict) or not isinstance(receipts, dict) or set(originals) != set(receipts) or len(originals) > self.MAX_IDS or not isinstance(pending, list) or len(pending) > self.MAX_QUEUE:
            raise ValueError("invalid command history or queue")
        for identifier, original in originals.items():
            if self._validate_command(original) != original or original["id"] != identifier or not isinstance(receipts[identifier], dict) or receipts[identifier].get("id") != identifier or receipts[identifier].get("status") not in {"queued", "applied", "rejected", "failed"}:
                raise ValueError("invalid idempotency record")
        pending = [self._validate_command(command) for command in pending]
        if len({command["id"] for command in pending}) != len(pending) or any(originals.get(command["id"]) != command for command in pending) or {command["id"] for command in pending} != {identifier for identifier, receipt in receipts.items() if receipt["status"] == "queued"}:
            raise ValueError("pending commands do not match receipt history")
        metrics = state["metrics"]
        if not isinstance(metrics, dict) or set(metrics) != {"reward", "contact_ticks", "path_length"} or any(type(metrics[key]) not in (int, float) for key in metrics) or type(metrics["contact_ticks"]) is not int or metrics["contact_ticks"] < 0 or metrics["path_length"] < 0:
            raise ValueError("invalid metrics")
        if state["last_outcome"] is not None and not isinstance(state["last_outcome"], dict):
            raise ValueError("invalid last outcome")
        return state

    def restore_application(self, state):
        state = self.validate_application(state)
        self.parent_run_id = state["source_run_id"]
        self.parent_event_prefix = state["event_prefix"]
        for name in ("episode", "total_tick", "episode_step", "phase", "metrics", "last_outcome", "seed", "revision", "eyes", "memory", "world_task_state", "task_state"):
            setattr(self, name, state[name])
        if self.body_state is not None:
            self.body_state = state['body_state']
        if self.scenario == 'adaptive-encoder-homing':
            self.composition = copy.deepcopy(state['composition'])
        self.manual_action = _action(state["manual_action"], manual=True)
        self._episode_finished = state["episode_finished"]
        self._pending = deque(state["pending_commands"])
        self.writer.manifest['initial_world'] = self.world()
        self.writer.manifest['execution_mode'] = state['execution_mode']
        if self.memory is not None:
            from .memory import sha256
            self.writer.manifest['initial_memory'] = {key: sha256(self.memory[key]) for key in ('m', 'e', 'u')}
        self._receipts, self._originals = state["receipts"], state["original_commands"]
        self._restored = True
        try:
            self._event("application_restored", parent_run_id=self.parent_run_id,
                        parent_event_prefix=self.parent_event_prefix, world=self.world(),
                        revision=self.revision, eyes=self.eyes)
        except Exception as error:
            self._fail(error)
            raise

    def restore_branch(self, snapshot, *, replace_controller=False):
        """Restore a registered snapshot, explicitly distinguishing controller replacement."""
        from .snapshots import restore
        state = copy.deepcopy(snapshot['application'])
        previous = state['controller']
        reference_transaction = self.reference_mode and state['scenario'] == 'memory-passages'
        if reference_transaction:
            state['scenario'] = self.scenario
        cancelled = [command['id'] for command in state['pending_commands']]
        if replace_controller:
            state.update(controller=self.controller, teacher_reset_identity=self._teacher_reset_identity,
                         pending_commands=[], receipts={}, original_commands={}, manual_action=[0., 0.])
            if self.memory is not None:
                from .snapshots import controller_hashes
                state['controller_tensors'] = controller_hashes(self.policy)
        self.validate_application(state)
        observation, _ = restore(snapshot, self.env, policy=self.policy, teacher=self.teacher,
                                 replace_controller=replace_controller)
        self.observation = observation
        self.restore_application(state)
        self.last_transition = None
        if replace_controller:
            self.revision += 1
            self._event('controller_replaced', old=previous, new=self.controller,
                        cancelled_source_commands=cancelled, revision=self.revision,
                        fresh_state=['controller', 'torch_rng', 'manual_intent', 'command_history'],
                        retained_state=['world', 'environment', 'python_numpy_environment_rng', 'eyes'])
        if self.reference_mode:
            from . import memory, memory_reference, snapshots
            self._reference_memory_sha256 = memory.sha256(self.memory)
            if reference_transaction:
                if not replace_controller:
                    self.revision += 1
                current = snapshots.capture(self.env, self.observation, policy=self.policy, teacher=self.teacher,
                                            application=self.application_state())
                expected = memory_reference.preservation_hash(snapshot, replace_controller)
                actual = memory_reference.preservation_hash(current, replace_controller)
                if (expected != actual or self.revision != snapshot['application']['revision'] + 1
                        or self.memory != snapshot['application']['memory']):
                    raise ValueError('Reference profile transaction changed an invariant state')
                self._event('memory_reference_profile_changed', old='memory-passages', new=self.scenario,
                    preserved_sha256=actual, replaced_controller=replace_controller,
                    frozen_memory_sha256=self._reference_memory_sha256)
        return self.public_state()

    def restore_homing_derivation(self, snapshot, *, snapshot_sha256, report, report_sha256):
        from .body_homing import SCENARIO, derive_snapshot, normalized_reference
        if self.scenario != SCENARIO:
            raise ValueError('Historical fitted derivation requires the homing composition')
        derived = derive_snapshot(snapshot, snapshot_sha256=snapshot_sha256,
                                  report=report, report_sha256=report_sha256)
        reference = normalized_reference(derived)
        self.restore_branch(derived)
        from .snapshots import capture
        actual = capture(self.env, self.observation, application=self.application_state())
        if normalized_reference(actual) != reference:
            raise ValueError('Actual homing initial differs from exact derivation reference')
        from .body_homing import provenance
        from .task_profiles import PROTOCOL
        self.writer.manifest.update(composition_provenance=provenance(self.env,self.world()),
            task_protocol=copy.deepcopy(PROTOCOL), task_profile_sha256=self.task_state['profile_sha256'],
            task_calibration=copy.deepcopy(self.task_state['odometry']['calibration']))
        self._event('body_homing_derived', reference_sha256=reference,
                    derivation=self.composition['derivation'])
        return reference

    def restore_memory_branch(self, snapshot, u):
        """Restore a fresh destination, replace U only, verify before publication."""
        from .memory import validate_u
        from .snapshots import capture, invariant_hashes
        u = validate_u(u)
        if self.scenario != 'memory-passages' or snapshot['application'].get('memory') is None:
            raise ValueError('U-only branches require a complete memory snapshot')
        if snapshot['application'].get('execution_mode') == 'actions':
            raise ValueError('U-only branches cannot continue an action-replay stream')
        expected = invariant_hashes(snapshot)
        self.restore_branch(snapshot)
        def current():
            return invariant_hashes(capture(self.env, self.observation, policy=self.policy,
                teacher=self.teacher, application=self.application_state()))
        if current() != expected:
            raise ValueError('Restored scientific state differs before U replacement')
        previous = self.memory['u']
        self.memory['u'] = u
        if current() != expected:
            raise ValueError('Scientific state changed outside U replacement')
        from .memory import sha256
        self.writer.manifest['initial_memory'] = {
            key: sha256(self.memory[key]) for key in ('m', 'e', 'u')}
        self._event('memory_u_replaced', old_u=previous, new_u=u, invariant_hashes=expected)
        return self.public_state()

    def close(self):
        self._owner_only()
        if self._closed:
            return
        error = None
        try:
            try:
                while self._pending and not self._recording_failed:
                    self._command_result(self._pending.popleft(), "rejected", reason="engine closed before application")
            except Exception as caught:
                error = caught
                self._fail(caught)
            try:
                try:
                    renderer = getattr(self.env, "renderer", None)
                    if renderer is not None:
                        renderer.close()
                finally:
                    self.env.close()
            except Exception as caught:
                error = error or caught
                self._fail(caught)
            if not self._recording_failed:
                self.writer.finish({"run_id": self.run_id, "parent_run_id": self.parent_run_id,
                                    "parent_event_prefix": self.parent_event_prefix,
                                    "final_phase": self.phase, "last_outcome": self.last_outcome,
                                    "metrics": self.metrics, "total_tick": self.total_tick,
                                    "close_reason": "operator_closed"},
                                   status="failed" if self.phase == "failed" else "completed")
        finally:
            self._closed = True
            self.writer.close()
        if error is not None:
            raise error
