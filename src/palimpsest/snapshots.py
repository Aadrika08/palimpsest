"""Complete snapshots at paused, committed tick boundaries.

The container is a plain dict: version/identity, native_data (MuJoCo native
bytes, never pickle), environment/controller/RNG state, observation/application.
Native bytes deliberately retain derived post-step caches. Restore never calls
reset, forward, observation or policy. Files are exclusive ZIP containers with
JSON and bounded, non-object .npy arrays; immutable weights remain external.
Only snapshots from trusted, version-matching runs should be restored: MuJoCo's
native decoder is not a sandbox for hostile input.
Profile identity is a compatibility guard; continuation qualification is measured
on the same host and numeric/rendering regime, not guaranteed across machines.
"""

import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import random
import struct
import sys
import zipfile


SCHEMA_VERSION = 1
MAX_BYTES = 512 * 1024 * 1024
MAX_METADATA = 8 * 1024 * 1024
MAX_ENTRIES = 8192
MUTABLE_MODEL_ARRAYS = ("jnt_range", "geom_rgba", "site_pos")
ENV_STATE = ("_obstacle_xy", "_goal_xy", "_prev_xy", "_speed", "_t", "visited",
             "_last_action", "_stall_steps", "_action_scale", "path_to_draw", "target_to_draw")
ENV_PROFILE = ("W", "H", "max_steps", "n_obstacles", "goal_radius", "goal_bonus",
               "ctrl_penalty", "contact_penalty", "arena", "render_mode", "explore_binsize",
               "time_penalty", "prog_scale", "frame_skip", "stall_threshold", "stall_limit",
               "end_on_collision", "texture_mode", "k_nearest", "_action_scale")
TEACHER_STATE = ("_prev_bad_contact", "_rec_phase", "_rec_step_count", "_rec_turn_dir",
                 "contact_point", "contact_angle", "_xy_prev", "_path")
VFH_STATE = ("primary_hist", "binary_hist", "prev_steering_dir", "prev_path_dir")
ASTAR_CACHE = ("_cached_occ", "_cached_obstacles_hash", "_cached_clearance", "_W", "_H", "_origin")
SNAPSHOT_KEYS = {"schema_version", "identity", "native_data", "native_sha256", "integration_enum",
                 "integration", "environment", "policy", "teacher", "rng", "observation", "application"}


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def state_digest(value):
    """Exact typed-state hash; dictionary/set order is not scientific state."""
    import numpy as np

    def digest(item, depth=0):
        if depth > 64:
            raise ValueError("Snapshot nesting exceeds limit")
        parts = [type(item).__name__.encode()]
        if isinstance(item, (np.ndarray, np.generic)):
            array = _array(np.asarray(item))
            parts += [array.dtype.str.encode(), json.dumps(array.shape).encode(), array.tobytes()]
        elif type(item) is bytes:
            if len(item) > MAX_BYTES:
                raise ValueError("Snapshot bytes exceed limit")
            parts.append(item)
        elif type(item) is dict:
            if any(type(key) is not str for key in item):
                raise TypeError("Snapshot dictionary keys must be strings")
            for key in sorted(item):
                parts += [key.encode(), digest(item[key], depth + 1)]
        elif type(item) in (list, tuple, set):
            children = [digest(child, depth + 1) for child in item]
            parts += sorted(children) if type(item) is set else children
        elif item is None or type(item) in (bool, int, float, str):
            parts.append(json.dumps(item, allow_nan=False, separators=(",", ":")).encode())
        else:
            raise TypeError("Unsupported scientific state value")
        result = hashlib.sha256()
        for part in parts:
            result.update(len(part).to_bytes(8, "big"))
            result.update(part)
        return result.digest()

    return digest(value).hex()


def invariant_hashes(snapshot):
    """U-only comparison excludes U and declared destination recorder identities."""
    if type(snapshot) is not dict or set(snapshot) != SNAPSHOT_KEYS:
        raise ValueError("Incomplete scientific snapshot")
    application = dict(snapshot["application"])
    memory = dict(application.pop("memory"))
    memory.pop("u")
    # These identify the destination recording, not the restored computation.
    application.pop("source_run_id")
    application.pop("event_prefix")
    components = {key: value for key, value in snapshot.items() if key != "application"}
    components.update(M=memory.pop("m"), E=memory.pop("e"),
                      memory_supervisor=memory, application=application)
    return {key: state_digest(value) for key, value in components.items()}


def controller_hashes(policy):
    """Hash actual immutable tensors, separately from declared checkpoint lineage."""
    if policy is None:
        return None
    return {kind: state_digest({name: tensor.detach().cpu().numpy() for name, tensor in values})
            for kind, values in (("graph_buffers", policy.agent.named_buffers()),
                                 ("parameters", policy.agent.named_parameters()))}


def _class(value):
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _array(value):
    if value.dtype.kind not in "buif" or value.dtype.itemsize not in (1, 2, 4, 8) or value.dtype.fields or value.ndim > 8 or value.nbytes > MAX_BYTES:
        raise ValueError("Snapshot arrays require bounded plain bool/integer/float dtypes")
    return value


def _copy(value, depth=0):
    import numpy as np
    if depth > 64:
        raise ValueError("Snapshot nesting exceeds limit")
    if isinstance(value, np.ndarray):
        return _array(value).copy()
    if isinstance(value, np.generic):
        _array(np.asarray(value))
        return value.copy()
    if value is None or type(value) in (bool, int, str, bytes):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Nonfinite scalar snapshot value")
        return value
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise TypeError("Snapshot dictionary keys must be strings")
        return {key: _copy(item, depth + 1) for key, item in value.items()}
    if type(value) in (list, tuple, set):
        return type(value)(_copy(item, depth + 1) for item in value)
    raise TypeError(f"Unsupported snapshot value: {_class(value)}")


def _fields(obj, names):
    return {"values": {name: _copy(getattr(obj, name)) for name in names if hasattr(obj, name)},
            "absent": [name for name in names if not hasattr(obj, name)]}


def _validate_fields(state, names):
    if set(state) != {"values", "absent"} or type(state["values"]) is not dict or type(state["absent"]) is not list:
        raise ValueError("Invalid snapshot field container")
    keys, absent = set(state["values"]), state["absent"]
    if len(absent) != len(set(absent)) or keys.intersection(absent) or keys.union(absent) != set(names):
        raise ValueError("Missing or unknown snapshot state fields")
    return _copy(state)


def _apply_fields(obj, state):
    for name, value in state["values"].items():
        setattr(obj, name, value)
    for name in state["absent"]:
        if hasattr(obj, name):
            delattr(obj, name)


def _number(value, name, minimum=None):
    import numpy as np
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)) or not np.isfinite(value) or minimum is not None and value < minimum:
        raise ValueError(f"Invalid numeric snapshot state: {name}")


def _points(value, name, width, single=False):
    import numpy as np
    if value is None:
        return
    array = np.asarray(value)
    if array.dtype.kind not in "iuf" or not np.isfinite(array).all() or (array.shape != (width,) if single else array.ndim != 2 or array.shape[1] != width):
        raise ValueError(f"Invalid point/path snapshot state: {name}")


def _model_digest(model):
    import mujoco
    canonical = mujoco.MjModel.__new__(mujoco.MjModel)
    canonical.__setstate__(model.__getstate__())
    for name in MUTABLE_MODEL_ARRAYS:
        getattr(canonical, name).fill(0)
    return _sha(canonical.__getstate__())


def _torch_profile():
    torch = sys.modules.get("torch")
    if torch is None:
        return None
    result = {"version": str(torch.__version__), "threads": torch.get_num_threads(),
            "interop_threads": torch.get_num_interop_threads(),
            "deterministic": torch.are_deterministic_algorithms_enabled(),
            "deterministic_warn_only": torch.is_deterministic_algorithms_warn_only_enabled(),
            "matmul_precision": torch.get_float32_matmul_precision(),
            "matmul_tf32": torch.backends.cuda.matmul.allow_tf32,
            "cudnn_tf32": torch.backends.cudnn.allow_tf32,
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
            "cuda_runtime": torch.version.cuda, "cudnn_version": torch.backends.cudnn.version(),
            "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "NVIDIA_TF32_OVERRIDE": os.environ.get("NVIDIA_TF32_OVERRIDE"),
            "initialized_cuda_devices": []}
    # Do not initialize CUDA in CPU profiles merely to collect metadata.
    if torch.cuda.is_initialized():
        result["initialized_cuda_devices"] = [
            {"index": index, "name": torch.cuda.get_device_name(index),
             "capability": list(torch.cuda.get_device_capability(index))}
            for index in range(torch.cuda.device_count())]
    return result


def _identity(env, policy, teacher):
    import mujoco
    import numpy as np
    renderer = getattr(env, "renderer", None)
    result = {"mujoco": mujoco.__version__, "numpy": np.__version__,
              "python": list(sys.version_info[:3]), "platform": sys.platform,
              "machine": platform.machine(),
              "byteorder": sys.byteorder, "pointer_bits": struct.calcsize("P") * 8,
              "environment_class": _class(env), "model_sha256": _model_digest(env.model),
              "environment_profile": _fields(env, ENV_PROFILE), "torch": _torch_profile(),
              "renderer": None if renderer is None else {"height": renderer.height, "width": renderer.width,
                  "context_class": _class(renderer._gl_context), "requested_backend": os.environ.get("MUJOCO_GL"),
                  "requested_egl_device": os.environ.get("MUJOCO_EGL_DEVICE_ID")},
              "policy": None, "teacher": None}
    if hasattr(env, '_body_profile_identity'):
        result['body_profile'] = _copy(env._body_profile_identity)
    if hasattr(env, "planner"):
        result["environment_planner"] = {"class": _class(env.planner), "spec": _copy(vars(env.planner.spec))}
    if policy is not None:
        result["policy"] = {"class": _class(policy), "device": str(policy.device),
                            "dtype": str(policy.dtype), "provenance": _copy(policy.provenance)}
    if teacher is not None:
        result["teacher"] = {"class": _class(teacher), "device": str(teacher.device),
            "settings": _copy({k: v for k, v in vars(teacher).items() if k not in TEACHER_STATE and k not in ("device", "pid_state", "planner")}),
            "planner_class": _class(teacher.planner),
            "planner_settings": _copy({k: v for k, v in vars(teacher.planner).items() if k not in VFH_STATE})}
    return result


def _spaces(env):
    def walk(space, path):
        yield path, space
        children = getattr(space, "spaces", None)
        if isinstance(children, dict):
            for key, child in children.items():
                yield from walk(child, path + "/" + key)
        elif isinstance(children, tuple):
            for index, child in enumerate(children):
                yield from walk(child, path + "/" + str(index))
    for name in ("action_space", "observation_space"):
        if hasattr(env, name):
            yield from walk(getattr(env, name), name)


def _generator_state(generator):
    return None if generator is None else _copy(generator.bit_generator.state)


def _rng(env):
    import numpy as np
    torch = sys.modules.get("torch")
    state = {"python": random.getstate(), "numpy": np.random.get_state(),
             "environment": _generator_state(getattr(env, "np_random", None)),
             "environment_seed": getattr(env, "_np_random_seed", None),
             "spaces": {path: _generator_state(vars(space).get("_np_random")) for path, space in _spaces(env)},
             "torch_cpu": None, "torch_cuda": []}
    if torch is not None:
        state["torch_cpu"] = torch.get_rng_state().cpu().numpy().copy()
        if torch.cuda.is_initialized():
            state["torch_cuda"] = [value.cpu().numpy().copy() for value in torch.cuda.get_rng_state_all()]
    return _copy(state)


def _new_generator(state):
    import numpy as np
    if state is None:
        return None
    name = state.get("bit_generator")
    if name not in {"PCG64", "PCG64DXSM", "MT19937", "Philox", "SFC64"}:
        raise ValueError("Unsupported NumPy bit generator")
    generator = np.random.Generator(getattr(np.random, name)())
    generator.bit_generator.state = state
    return generator


def _stage_rng(state, env):
    import numpy as np
    state = _copy(state)
    if set(state) != {"python", "numpy", "environment", "environment_seed", "spaces", "torch_cpu", "torch_cuda"}:
        raise ValueError("Missing/unknown RNG snapshot state")
    random.Random().setstate(state["python"])
    np.random.RandomState().set_state(state["numpy"])
    generator = _new_generator(state["environment"])
    spaces = dict(_spaces(env))
    if set(spaces) != set(state["spaces"]):
        raise ValueError("Snapshot Gym spaces differ")
    generators = {key: _new_generator(value) for key, value in state["spaces"].items()}
    torch = sys.modules.get("torch")
    cpu, cuda = None, []
    if state["torch_cpu"] is not None:
        if torch is None:
            raise ValueError("Snapshot requires initialized Torch runtime")
        cpu = torch.from_numpy(_array(state["torch_cpu"]))
        torch.Generator(device="cpu").set_state(cpu)
        if state["torch_cuda"]:
            if not torch.cuda.is_initialized() or len(state["torch_cuda"]) != torch.cuda.device_count():
                raise ValueError("Snapshot CUDA device RNG regime differs")
            for index, value in enumerate(state["torch_cuda"]):
                item = torch.from_numpy(_array(value))
                torch.Generator(device=f"cuda:{index}").set_state(item)
                cuda.append(item)
    elif state["torch_cuda"]:
        raise ValueError("CUDA RNG state requires CPU Torch state")
    return state, generator, spaces, generators, cpu, cuda


def capture(env, observation, *, policy=None, teacher=None, application: dict):
    """Copy one committed boundary; caller owns pause/queue-cut/CUDA synchronization."""
    import mujoco
    import numpy as np
    if type(application) is not dict:
        raise TypeError("application must be pure-state dict")
    if getattr(env, "window", None) is not None or getattr(env, "_view_ctx", None) is not None:
        raise ValueError("Snapshot profile supports headless environments only")
    if hasattr(env, '_body_profile_identity'):
        if mujoco.get_mjcb_control() is not None:
            raise ValueError('Body snapshots require no active global control callback')
        if application.get('scenario') == 'adaptive-encoder-homing':
            from .body_homing import validate_snapshot_application
        elif application.get('scenario') == 'adaptive-wheel-calibration':
            from .body_adaptation import validate_snapshot_application
        else:
            from .body_profile import validate_snapshot_application
        validate_snapshot_application(application, env, env.model, env.data)
    native = env.data.__getstate__()
    if len(native) > MAX_BYTES:
        raise ValueError("Native snapshot exceeds byte limit")
    integration = np.empty(mujoco.mj_stateSize(env.model, mujoco.mjtState.mjSTATE_INTEGRATION))
    mujoco.mj_getState(env.model, env.data, integration, mujoco.mjtState.mjSTATE_INTEGRATION)
    policy_state = None
    if policy is not None:
        def tensor(value):
            return None if value is None else {k: tensor(v) for k, v in value.items()} if isinstance(value, dict) else value.detach().cpu().numpy().copy()
        if getattr(policy, 'snapshot_kind', None) == 'male-reduced-v1':
            policy_state = {'kind': 'male-reduced-v1', 'hidden': tensor(policy.hidden),
                            'failure_diagnostics': _copy(policy.failure_diagnostics)}
            _male_state(policy_state)
        else:
            policy_state = {"hidden": tensor(policy.hidden), "left": tensor(policy.agent.state_vision_left),
                            "right": tensor(policy.agent.state_vision_right), "failure_diagnostics": _copy(getattr(policy, "failure_diagnostics", {}))}
    teacher_state = None if teacher is None else {"state": _fields(teacher, TEACHER_STATE),
        "pid": _fields(teacher.pid_state, ("integral", "last_error")), "planner": _fields(teacher.planner, VFH_STATE)}
    return _copy({"schema_version": SCHEMA_VERSION, "identity": _identity(env, policy, teacher),
        "native_data": native, "native_sha256": _sha(native), "integration_enum": int(mujoco.mjtState.mjSTATE_INTEGRATION),
        "integration": integration, "environment": _fields(env, ENV_STATE),
        "policy": policy_state, "teacher": teacher_state, "rng": _rng(env),
        "observation": observation, "application": application})


def _male_state(state):
    """Pure validation of the one supported male hidden-state snapshot contract."""
    import numpy as np
    if type(state) is not dict or set(state) != {'kind', 'hidden', 'failure_diagnostics'} or state['kind'] != 'male-reduced-v1':
        raise ValueError('invalid male snapshot policy state')
    hidden, diagnostics = state['hidden'], state['failure_diagnostics']
    if not isinstance(hidden, np.ndarray) or hidden.shape != (1, 138) or hidden.dtype != np.float32 or not np.isfinite(hidden).all():
        raise ValueError('male snapshot hidden shape/dtype/value differs')
    if (type(diagnostics) is not dict or diagnostics and (set(diagnostics) != {'type', 'message'} or
            any(type(diagnostics[key]) is not str or len(diagnostics[key]) > limit
                for key, limit in (('type', 128), ('message', 512))))):
        raise ValueError('invalid bounded male snapshot diagnostics')
    return hidden.copy(), dict(diagnostics)


def _stage_policy(state, policy):
    import numpy as np
    if policy is None:
        if state is not None:
            raise ValueError("Snapshot controller differs")
        return None
    torch = policy.torch
    if getattr(policy, 'snapshot_kind', None) == 'male-reduced-v1':
        hidden, diagnostics = _male_state(state)
        if policy.agent.cell.N != 138 or str(policy.device) != 'cpu' or policy.dtype != torch.float32:
            raise ValueError('male snapshot destination profile differs')
        return (torch.as_tensor(hidden, device=policy.device, dtype=policy.dtype),), diagnostics
    if type(state) is not dict or set(state) != {"hidden", "left", "right", "failure_diagnostics"} or type(state["failure_diagnostics"]) is not dict:
        raise ValueError("Missing policy snapshot state")
    def tensor(value, shape):
        if not isinstance(value, np.ndarray) or value.shape != shape or str(value.dtype) != str(policy.hidden.detach().cpu().numpy().dtype) or not np.isfinite(value).all():
            raise ValueError("Policy snapshot tensor shape/dtype/value mismatch")
        return torch.as_tensor(value.copy(), device=policy.device, dtype=policy.dtype)
    hidden = tensor(state["hidden"], (1, policy.agent.cell.N))
    eyes = []
    for name, eye in (("left", state["left"]), ("right", state["right"])):
        if eye is None:
            eyes.append(None)
        else:
            if set(eye) != {"L1", "L2", "L3"}:
                raise ValueError("Retina snapshot layers differ")
            values = {}
            for key, value in eye.items():
                grid = getattr(policy.agent, f"grid_{key}_{name}")
                values[key] = tensor(value, (1, 0 if grid is None else grid.shape[1]))
            eyes.append(values)
    return (hidden, *eyes), _copy(state["failure_diagnostics"])


def _bindings(env, model):
    import mujoco
    import numpy as np
    if not hasattr(env, "base_body_id"):
        return {}
    def ident(kind, name):
        found = mujoco.mj_name2id(model, kind, name)
        if found < 0:
            raise ValueError(f"Restored model missing {name}")
        return found
    result = {}
    for field, kind, name in (("base_body_id", mujoco.mjtObj.mjOBJ_BODY, "base"),
        ("goal_site_id", mujoco.mjtObj.mjOBJ_SITE, "goal_site"),
        ("left_hinge_id", mujoco.mjtObj.mjOBJ_JOINT, "left_hinge"),
        ("right_hinge_id", mujoco.mjtObj.mjOBJ_JOINT, "right_hinge"),
        ("cam_left_id", mujoco.mjtObj.mjOBJ_CAMERA, "cam_left"),
        ("cam_right_id", mujoco.mjtObj.mjOBJ_CAMERA, "cam_right")):
        result[field] = ident(kind, name)
    for field, kind, suffix in (("obstacle_ids", mujoco.mjtObj.mjOBJ_GEOM, ""),
        ("obstacle_body_ids", mujoco.mjtObj.mjOBJ_BODY, "_body"),
        ("obstacle_x_joint_ids", mujoco.mjtObj.mjOBJ_JOINT, "_x"),
        ("obstacle_y_joint_ids", mujoco.mjtObj.mjOBJ_JOINT, "_y")):
        result[field] = [ident(kind, f"obstacle{i}{suffix}") for i in range(env.n_obstacles)]
    for axis in ("x", "y"):
        result[f"_obstacle_{axis}_qposadr"] = np.array([model.jnt_qposadr[jid] for jid in result[f"obstacle_{axis}_joint_ids"]], dtype=np.int32)
    return result


def restore(snapshot, env, *, policy=None, teacher=None, replace_controller=False):
    """Validate/stage before replacing source state; return independent rawobs/app."""
    import mujoco
    import numpy as np
    snp = _copy(snapshot)
    if type(snp) is not dict or set(snp) != SNAPSHOT_KEYS or type(snp.get("schema_version")) is not int or snp["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported snapshot schema version")
    expected_identity, actual_identity = snp.get('identity'), _identity(env, policy, teacher)
    if replace_controller:
        # Explicit controller replacement keeps world state, not controller/Torch state.
        expected_identity = {k: v for k, v in expected_identity.items() if k not in ('policy', 'teacher', 'torch')}
        actual_identity = {k: v for k, v in actual_identity.items() if k not in ('policy', 'teacher', 'torch')}
        snp['policy'] = snp['teacher'] = None
        current_rng = _rng(env)
        for name in ('torch_cpu', 'torch_cuda'):
            snp['rng'][name] = current_rng[name]
    if expected_identity != actual_identity:
        raise ValueError("Snapshot model/runtime/profile identity differs")
    native = snp["native_data"]
    if type(native) is not bytes or not native or len(native) > MAX_BYTES or _sha(native) != snp["native_sha256"]:
        raise ValueError("Invalid native snapshot bytes/hash")
    state = _validate_fields(snp["environment"], ENV_STATE)
    if hasattr(env, "base_body_id") and state["absent"]:
        raise ValueError("Incomplete upstream environment snapshot; capture after reset")
    for name in ("_obstacle_xy", "_goal_xy", "_prev_xy", "_last_action"):
        if name in state["values"]:
            value, current = state["values"][name], getattr(env, name)
            if not isinstance(value, np.ndarray) or value.shape != current.shape or value.dtype != current.dtype or not np.isfinite(value).all():
                raise ValueError(f"Environment state shape/dtype differs: {name}")
    for name in ("_t", "_stall_steps"):
        if name in state["values"] and (type(state["values"][name]) is not int or state["values"][name] < 0):
            raise ValueError(f"Invalid environment counter: {name}")
    for name in ("_speed", "_action_scale"):
        if name in state["values"]:
            _number(state["values"][name], name, minimum=0)
            if name == "_action_scale" and state["values"][name] == 0:
                raise ValueError("Action scale must be positive")
    _points(state["values"].get("path_to_draw"), "path_to_draw", 2)
    _points(state["values"].get("target_to_draw"), "target_to_draw", 2, single=True)
    if "visited" in state["values"]:
        visited = state["values"]["visited"]
        if type(visited) is not set or any(type(item) is not tuple or len(item) != 2 or any(not isinstance(x, (int, np.integer)) for x in item) for item in visited):
            raise ValueError("Invalid environment visited bins")
    policy_state = _stage_policy(snp["policy"], None if replace_controller else policy)
    teacher_state = snp["teacher"]
    if teacher is not None and not replace_controller:
        teacher_state = {"state": _validate_fields(teacher_state["state"], TEACHER_STATE),
                         "pid": _validate_fields(teacher_state["pid"], ("integral", "last_error")),
                         "planner": _validate_fields(teacher_state["planner"], VFH_STATE)}
        if set(teacher_state["state"]["absent"]).difference({"contact_angle"}) or teacher_state["pid"]["absent"] or teacher_state["planner"]["absent"]:
            raise ValueError("Incomplete teacher snapshot state")
        values = teacher_state["state"]["values"]
        if type(values["_prev_bad_contact"]) not in (bool, np.bool_) or values["_rec_phase"] not in (None, "back", "turn", "forward") or type(values["_rec_step_count"]) is not int or values["_rec_step_count"] < 0:
            raise ValueError("Invalid teacher collision/recovery snapshot state")
        _number(values["_rec_turn_dir"], "teacher._rec_turn_dir")
        if values["_rec_turn_dir"] not in (-1., 1.):
            raise ValueError("Teacher recovery direction must be -1 or 1")
        if values.get("contact_angle") is not None:
            _number(values["contact_angle"], "teacher.contact_angle")
        for key, width, single in (("contact_point", 3, True), ("_xy_prev", 2, True), ("_path", 2, False)):
            _points(values[key], "teacher." + key, width, single)
        for key, value in teacher_state["pid"]["values"].items():
            _number(value, "teacher.pid." + key)
        for key in ("prev_steering_dir", "prev_path_dir"):
            value = teacher_state["planner"]["values"][key]
            if value is not None:
                _number(value, "teacher.planner." + key)
            elif key == "prev_steering_dir":
                raise ValueError("Teacher previous steering direction cannot be null")
        for key in ("primary_hist", "binary_hist"):
            value = teacher_state["planner"]["values"][key]
            current = getattr(teacher.planner, key)
            if not isinstance(value, np.ndarray) or value.shape != current.shape or value.dtype != current.dtype or not np.isfinite(value).all():
                raise ValueError("Teacher histogram shape/dtype differs")
    elif teacher_state is not None:
        raise ValueError("Snapshot teacher differs")
    rng = _stage_rng(snp["rng"], env)
    if type(snp["application"]) is not dict:
        raise ValueError("Invalid application snapshot")
    if type(snp["observation"]) is not dict:
        raise ValueError("Invalid raw observation snapshot")
    if hasattr(env, "base_body_id"):
        for name in ("cam_left", "cam_right"):
            image = snp["observation"].get(name)
            if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.shape != (env.renderer.height, env.renderer.width, 3):
                raise ValueError("Raw observation camera shape/dtype differs")
        if type(snp["observation"].get("sensors")) is not dict:
            raise ValueError("Raw observation sensor state missing")
    data = mujoco.MjData.__new__(mujoco.MjData)
    data.__setstate__(native)
    model = data.model
    if _model_digest(model) != snp["identity"]["model_sha256"]:
        raise ValueError("Native snapshot model identity differs")
    enum = mujoco.mjtState.mjSTATE_INTEGRATION
    if snp["integration_enum"] != int(enum):
        raise ValueError("Snapshot integration enum differs")
    audit = np.empty(mujoco.mj_stateSize(model, enum))
    mujoco.mj_getState(model, data, audit, enum)
    if not isinstance(snp["integration"], np.ndarray) or snp["integration"].dtype != audit.dtype or snp["integration"].shape != audit.shape or not np.array_equal(snp["integration"].view(np.uint8), audit.view(np.uint8)):
        raise ValueError("Snapshot integration audit differs")
    if hasattr(env, '_body_profile_identity'):
        if mujoco.get_mjcb_control() is not None:
            raise ValueError('Body snapshots require no active global control callback')
        if snp['application'].get('scenario') == 'adaptive-encoder-homing':
            from .body_homing import validate_snapshot_application
        elif snp['application'].get('scenario') == 'adaptive-wheel-calibration':
            from .body_adaptation import validate_snapshot_application
        else:
            from .body_profile import validate_snapshot_application
        validate_snapshot_application(snp['application'], env, model, data)
    elif 'body_state' in snp['application']:
        raise ValueError('Body state requires a loaded compensation profile')
    updates = _bindings(env, model)
    renderer = None
    if snp["identity"]["renderer"] is not None:
        renderer = mujoco.Renderer(model, height=snp["identity"]["renderer"]["height"],
                                   width=snp["identity"]["renderer"]["width"])
        updates["renderer"] = renderer
    try:
        if hasattr(env, "_view_scn"):
            updates["_view_scn"] = mujoco.MjvScene(model, maxgeom=env._view_scn.maxgeom)
    except BaseException:
        if renderer is not None:
            renderer.close()
        raise
    # All fallible validation/allocation above; the owner commits while paused.
    old_renderer = getattr(env, "renderer", None)
    env.model, env.data = model, data
    for key, value in updates.items():
        setattr(env, key, value)
    _apply_fields(env, state)
    if hasattr(env, "planner"):
        for name in ASTAR_CACHE:
            setattr(env.planner, name, None)
    if policy is not None and not replace_controller:
        if getattr(policy, 'snapshot_kind', None) == 'male-reduced-v1':
            policy.hidden = policy_state[0][0]
            policy.agent.cell.invalidate_caches()
        else:
            policy._restore(policy_state[0])
            policy._current_raw_output = None
            policy.agent.cell._cached_alphas = None
            policy.agent.cell._alphas_dirty = True
        policy.failure_diagnostics = policy_state[1]
    if teacher is not None and not replace_controller:
        _apply_fields(teacher, teacher_state["state"])
        _apply_fields(teacher.pid_state, teacher_state["pid"])
        _apply_fields(teacher.planner, teacher_state["planner"])
    random.setstate(rng[0]["python"])
    np.random.set_state(rng[0]["numpy"])
    if rng[1] is not None:
        env.np_random = rng[1]
    if hasattr(env, "_np_random_seed"):
        env._np_random_seed = rng[0]["environment_seed"]
    for key, space in rng[2].items():
        space._np_random = rng[3][key]
    if rng[4] is not None:
        torch = sys.modules["torch"]
        torch.set_rng_state(rng[4])
        if rng[5]:
            torch.cuda.set_rng_state_all(rng[5])
    if old_renderer is not None:
        old_renderer.close()
    return snp["observation"], snp["application"]


def save_snapshot(snapshot, path, *, storage_budget=None, preflight_bytes=0):
    """Write an exclusive bounded container and return its exact byte count.

    Optional preflight bytes estimate subsequent recording needs; they are
    checked with the actual serialized snapshot before any disk write.
    """
    import numpy as np
    if type(preflight_bytes) is not int or preflight_bytes < 0:
        raise ValueError("preflight_bytes must be a nonnegative integer")
    if preflight_bytes and storage_budget is None:
        raise ValueError("Snapshot preflight requires a storage budget")
    entries = {}
    def encode(value, depth=0):
        if depth > 64:
            raise ValueError("Snapshot nesting exceeds limit")
        if isinstance(value, (np.ndarray, np.generic)) or type(value) is bytes:
            is_array = not isinstance(value, bytes)
            name = f"state/{len(entries)}." + ("npy" if is_array else "bin")
            if is_array:
                stream = io.BytesIO()
                np.save(stream, _array(np.asarray(value)), allow_pickle=False)
                payload = stream.getvalue()
            else:
                payload = value
            entries[name] = payload
            return {"kind": "array" if isinstance(value, np.ndarray) else "scalar" if is_array else "bytes",
                    "entry": name, "size": len(payload), "sha256": _sha(payload)}
        if type(value) is dict:
            return {"kind": "dict", "items": [[key, encode(item, depth + 1)] for key, item in value.items()]}
        if type(value) in (list, tuple, set):
            return {"kind": type(value).__name__, "items": [encode(item, depth + 1) for item in value]}
        return value
    metadata = json.dumps({"format": "palimpsest.snapshot", "schema_version": SCHEMA_VERSION,
                           "container": encode(_copy(snapshot))}, allow_nan=False, separators=(",", ":")).encode()
    if len(metadata) > MAX_METADATA or len(entries) + 1 > MAX_ENTRIES or sum(map(len, entries.values())) + len(metadata) > MAX_BYTES:
        raise ValueError("Snapshot container exceeds limits")
    with io.BytesIO() as staging:
        with zipfile.ZipFile(staging, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("metadata.json", metadata)
            for name, payload in entries.items():
                archive.writestr(name, payload)
        payload = staging.getvalue()
    if len(payload) > MAX_BYTES:
        raise ValueError("Snapshot container exceeds limits")
    path = Path(path)
    if storage_budget is not None:
        storage_budget.check(len(payload) + preflight_bytes, path=path)
    with path.open("xb") as stream:
        try:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            path.unlink()
            raise
    return len(payload)


def read_snapshot(path):
    """Read bounded arrays without pickle; native decode happens only in restore."""
    import numpy as np
    if Path(path).stat().st_size > MAX_BYTES:
        raise ValueError("Snapshot file exceeds limit")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(infos) > MAX_ENTRIES or len(names) != len(set(names)) or sum(info.file_size for info in infos) > MAX_BYTES:
            raise ValueError("Snapshot archive exceeds limits or duplicates entries")
        if "metadata.json" not in names or archive.getinfo("metadata.json").file_size > MAX_METADATA:
            raise ValueError("Missing/oversized snapshot metadata")
        metadata = json.loads(archive.read("metadata.json"))
        if metadata.get("format") != "palimpsest.snapshot" or metadata.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported snapshot file format/version")
        used = {"metadata.json"}
        def decode(node, depth=0):
            if depth > 64:
                raise ValueError("Snapshot nesting exceeds limit")
            if type(node) is not dict:
                if node is None or type(node) in (str, int, bool) or type(node) is float and math.isfinite(node):
                    return node
                raise ValueError("Invalid snapshot JSON node")
            kind = node.get("kind")
            if kind in ("array", "scalar", "bytes"):
                name = node["entry"]
                if name not in names or name in used or archive.getinfo(name).file_size != node["size"]:
                    raise ValueError("Invalid snapshot entry reference")
                used.add(name)
                payload = archive.read(name)
                if _sha(payload) != node["sha256"]:
                    raise ValueError("Snapshot entry hash differs")
                if kind == "bytes":
                    return payload
                # Validate header and byte count BEFORE NumPy can allocate from
                # an attacker-controlled shape; only our plain .npy versions.
                stream = io.BytesIO(payload)
                version = np.lib.format.read_magic(stream)
                if version not in ((1, 0), (2, 0)):
                    raise ValueError("Unsupported numeric array format")
                reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
                shape, fortran, dtype = reader(stream, max_header_size=4096)
                if dtype.kind not in "buif" or dtype.itemsize not in (1, 2, 4, 8) or dtype.fields or len(shape) > 8 or any(type(size) is not int or size < 0 for size in shape):
                    raise ValueError("Unsupported numeric array dtype/shape")
                count = math.prod(shape)
                if count * dtype.itemsize > MAX_BYTES or stream.tell() + count * dtype.itemsize != len(payload):
                    raise ValueError("Invalid numeric array byte count")
                value = np.frombuffer(payload, dtype=dtype, count=count, offset=stream.tell()).reshape(shape, order="F" if fortran else "C").copy()
                if kind == "scalar" and value.shape != ():
                    raise ValueError("Invalid array payload")
                return value if kind == "array" else value[()]
            if kind == "dict":
                result = {}
                for key, value in node["items"]:
                    if type(key) is not str or key in result:
                        raise ValueError("Invalid/duplicate snapshot dictionary key")
                    result[key] = decode(value, depth + 1)
                return result
            if kind in ("list", "tuple", "set"):
                values = [decode(value, depth + 1) for value in node["items"]]
                return {"list": list, "tuple": tuple, "set": set}[kind](values)
            raise ValueError("Unknown snapshot node kind")
        result = decode(metadata["container"])
        if used != set(names) or type(result) is not dict:
            raise ValueError("Unknown entries or invalid snapshot root")
        return result
