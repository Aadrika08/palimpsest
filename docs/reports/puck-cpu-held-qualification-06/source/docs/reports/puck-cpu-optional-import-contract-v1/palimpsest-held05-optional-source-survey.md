# Held05 optional-import source survey

**Actual05 remains consumed FAIL. No new absence is admitted and no06 is authorized.** The product exit remains a real episode recording/replay/export bundle.

Offline coverage: **1,760/1,760** registered Python sources (1,759 SITE +1 generated), **33,719,650B**, **2,460,194 AST nodes**. All parse and match pinned inventory/generated hashes; fingerprints are rechecked. The four named families cover1,205 Python files. No source was imported or executed.

The JSON retains every source hash/path and193 caught-import statements (182 with explicit ImportError/ModuleNotFoundError),26 imports under other try handlers, and115 syntactic find_spec/import_module/__import__ sites.47 have nonliteral request expressions. AST-complete file coverage is not executed-path or dynamic-request completeness.

## Priority evidence

- `torch.cuda:63` imports absent `pynvml`; source catch sites113/117 swallow the error. CUDA source SHA256 `9ba786aee9b5aac710f49c3beade1722610a0d6d8ec406fad9a9793df1316e99`. The named staged CUDA/init and memory source leaves match inventory; this is not a full staged census.
- `torch.utils.data.datapipes.utils.common:25` calls `dill_available()`; `_import_utils:23` passes literal `dill` to `_check_module_exists`, whose line15 `find_spec(name)` catches ImportError at17. `datapipe:17` also calls `import_dill()`. These callers are registered and present in the retained ordinary03 cache. `dill` is absent from the module map, SITE file inventory and71-wheel list.
- A registered `torch.cuda.memory` file remains present; its later error does not turn it into a missing-name candidate. The existing negatives `numpy._distributor_init_local`, `org`, `torch._rocm_init` remain unchanged. From-imported `_cudart`/`_initExtension` can be native attributes; their absent file correspondence does not justify a negative module.

## Finite missing-name review list

These14 exact first-absent prefixes are **review candidates, not a blanket negative roster**. Caller/cache facts are static retained data. Full literal requests and predicates are in JSON; a from-import member can be an attribute rather than a module.

| First absent prefix | Caller(s):line | Requester in03 cache | Source predicate / caveat |
| --- | --- | --- | --- |
| `dill` | torch.utils.data.datapipes.utils.common:25, torch.utils._import_utils:23, torch.utils._import_utils:15, torch.utils.data.datapipes.datapipe:17 | yes | literal-bound eager helper |
| `OpenGL_accelerate` | OpenGL.acceleratesupport:9;11 other caught sites (JSON) | yes | conditional; exact predicates retained in JSON |
| `accimage` | torchvision.transforms._functional_pil:12, torchvision.transforms.functional:15, torchvision.transforms.transforms:12 | yes | unconditional caught try |
| `av` | torchvision.io.video:17, torchvision.io.video_reader:26 | yes | unconditional caught try |
| `colorama` | torch._inductor.runtime.runtime_utils:106 | yes | unconditional caught try |
| `defusedxml` | PIL.Image:62, torchvision.datasets.voc:8 | yes | unconditional caught try |
| `gmpy` | mpmath.libmp.backend:73 | yes | MPMATH_NOGMPY absent from frozen environment; gmpy is fallback after gmpy2 failure |
| `gmpy2` | mpmath.libmp.backend:70 | yes | MPMATH_NOGMPY absent from frozen environment; gmpy is fallback after gmpy2 failure |
| `monkeytype` | torch.jit._monkeytype_config:16–24 (first import16) | yes | unconditional caught try |
| `opt_einsum` | torch.backends.opt_einsum:12 | yes | unconditional caught try |
| `pydot` | torch.fx.passes.graph_drawer:24 | yes | TYPE_CHECKING else branch; caller cached in03 |
| `pynvml` | torch.cuda:63 | yes | CPU hip=None source; actual05 confirms this branch reached |
| `torchdistx` | torch.distributed.fsdp._init_utils:55 | yes | unconditional caught try |
| `tqdm` | torch.hub:64 | yes | unconditional caught try |

## Remaining direct Torch sites

These requester modules are all present in the retained03 cache; all six names are absent from the exact map and SITE inventory. Their source hashes are in JSON.

- `monkeytype`: `torch.jit._monkeytype_config:16`, handler25, fallback26. Unconditional module-body try; first absent import16 skips the remaining17–24 imports after catch. Fallback _IS_MONKEYTYPE_INSTALLED=False.
- `opt_einsum`: `torch.backends.opt_einsum:12`, handler13, fallback14. Unconditional module-body try; fallback _opt_einsum=None.
- `pydot`: `torch.fx.passes.graph_drawer:24`, handler27, fallback28. Runtime else arm of imported typing.TYPE_CHECKING; exact module source imports TYPE_CHECKING at6 and does not rebind it. Catch ModuleNotFoundError; HAS_PYDOT=False and pydot=None.
- `colorama`: `torch._inductor.runtime.runtime_utils:106`, handler109, fallback110. Unconditional module-body try; ModuleNotFoundError fallback HAS_COLORAMA=False and colorama=None.
- `torchdistx`: `torch.distributed.fsdp._init_utils:55`, handler56, fallback57. Unconditional module-body from-import; ImportError fallback _TORCHDISTX_AVAIL=False.
- `tqdm`: `torch.hub:64`, handler65, fallback66. Unconditional module-body from-import; ImportError fallback assigns the local _Faketqdm wrapper.

Of47 syntactically nonliteral probes, exact source binds the dill helper site and the11-name polyfill-loop site. The remaining45 sites are grouped by module/caller in JSON; they are review obligations, not proof that45 probes execute or require new negatives.

## Exclusions and unresolved cases

- Exclude the eager `amdsmi` branch (`hip=None` in exact torch.version:8), `libfb` (`torch._environment.is_fbcode` returnsFalse), eager logging `triton` (`disable_progress=True`), and `sage` (required SAGE environment keys absent). Deferred probes with these names remain separate; no future-path claim follows.
- `optree` at `_pytree:177` is metadata.version caught by PackageNotFoundError, not an import request. MuJoCo’s eager `__import__("pkgutil")` names trusted stdlib, not a missing vendor.
- The eager Dynamo polyfill loop at loader:29 has11 names in its literal tuple; all11 derived fullnames are already registered. Its constructed syntax needs no inferred negative name.
- Other literal dynamic probes are deferred: gmpy2, IPython, pycosat, pysat, z3, mpl_toolkits, triton and torch_xla. Static function placement alone cannot show whether another eager caller invokes them. The47 nonliteral sites include the separately bound dill and polyfill cases; others stay explicit obligations, not automatic runtime blockers or admitted names.
- Conditional execution, dynamic strings/callbacks, alias rebinding, custom import APIs, native-created attributes and arbitrary future module paths are not proved complete. Absence means only the exact retained inventory/map, never global sys.path absence. Ordinary03 cache presence records a loaded caller, not an attempted-missing-import trace.

## Bounds and pins

120-second initial scan; at most2,000 files,4MiB/source,128MiB aggregate source,250,000 AST nodes/file,4,000,000 total nodes,100,000 recorded sites and16MiB JSON. Initial scan34.656s. Inputs: candidate `6532308a…`, inventory `d1dac91f…`; complete pins and source hashes are in JSON. No Git, network, new namespace/probe, vendor/operator/model/catalog/study invocation, package installation or repository write occurred.
