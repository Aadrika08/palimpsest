# Static creator and generated-source evidence

All selected inputs below match the accepted inventory. No NumPy/Torch initializer
ran during this inspection. The creator ordering is a prediction for the pinned
clean route; ordinary02 observed terminal identities, not first creation.

`numpy/random/__init__.py:180` imports `_pickle`; `_pickle.py:1` imports
`numpy.random.bit_generator` first. Their SHA256s are
`f354e19dec60e6e98de566700f94d1cb335cd98a7e775e01e940bb3418152a1f` and
`e224bda1fbefb83d0a28cb51a5911d06c947efd6e584af30b63ab179637f81c1`.
The254,072B bit_generator DSO is
`d25ee62c3eafa15e48b6488207a6a3db76744e2f636c578da3df10575810452d`;
the276,728B _common DSO is
`17f99f57cd1e129065457dbbe17099120a54a3249149457b7a2f5bac254d4745`.

In bit_generator, PyInit at0xeb99 returns the module definition; exec slot2 enters
0x9bc5. Its exec calls PyImport_AddModule for cython_runtime at0x9c5e and
_cython_3_0_12 at0x9d9b. It adds cython_function_or_method at0x9e6b, then imports
numpy.random._common at0xb2dc. That nested exec adds generator at0x7db0 before the
outer creator returns. Reentrant observation is therefore necessary, and creator
close can bind both declared dispatch keys. Root re-read the relevant objdump
snippets; no target ELF executed. The standard
[Cython exec initialization](https://github.com/cython/cython/blob/3.0.12/Cython/Compiler/ModuleNode.py#L2815-L2827)
and [shared type helper](https://github.com/cython/cython/blob/3.0.12/Cython/Utility/CommonStructures.c#L40-L70)
support this interpretation. Unexpected ordering or dispatch keys must refuse.

Reproducible inert commands from the CPU checkout:

```sh
objdump -d --start-address=0x9c42 --stop-address=0x9e75 runs/puck-cpu-install-01/site/numpy/random/bit_generator.cpython-311-x86_64-linux-gnu.so
objdump -d --start-address=0xb2d5 --stop-address=0xb2e8 runs/puck-cpu-install-01/site/numpy/random/bit_generator.cpython-311-x86_64-linux-gnu.so
objdump -d --start-address=0x7cc4 --stop-address=0x7db5 runs/puck-cpu-install-01/site/numpy/random/_common.cpython-311-x86_64-linux-gnu.so
```

The observed _remote_module_non_scriptable has a scratch path, so it cannot be
treated as an installed SITE file. Its original temporary source bytes were not
retained. Authenticated instantiator.py (5,510B,
`567d1314ee27ff0b3bd22e7c4d1157246469de25e7a3183d96debe167b193615`)
and remote_module_template.py (3,463B,
`0ff1856bbd031b5298d46c06c0502abc20bd804f42c1949ed4127e8c773660cc`)
provide a fixed prospective source. The retained derivation AST-checks the
non-scriptable call, True branch, literal template strings and seven string
arguments. Only stdlib AST/literal/string operations execute.

The [rendered helper](generated/_remote_module_non_scriptable.py) is2,355B,
SHA256 `8205b16956fb264841ecd8644784a0d157f87df79b17c16825dc1163433ce5d8`.
Independent static reconstruction and a fresh output-only reproduction agree.
This is prospective registered code, not a recovered hash of the old scratch file.
The existing held finder can serve this registered name from a separate package
root while Torch writes its unused scratch duplicate. The helper's top level
imports and defines functions; RPC/CUDA operations remain inside their uncalled
bodies. Actual held qualification must verify this route. Original Torch
[licence](TORCH-LICENSE) and [notice](TORCH-NOTICE) are retained unchanged.
