# python-louvain wheel build: prospective v1 proposal

Status: design only. No backend payload acquisition, tool installation, source
extraction, build or target-library import is authorized by this document alone.
The active simulation goal permits preparing a concrete bounded configuration;
independent exact-source/config review must precede its actual invocation.
Consumed numerical runtime/study stages remain unchanged.

## Inputs and one proposed backend

Reuse the authenticated python-louvain0.16 source from
[package acquisition01](../reports/puck-cpu-payload-verification-v1.md).
Its204,641B SHA256 is b7ba2df5002fd28d3ee789a49532baad11fe648e4f2117cf0798e7520a1da56b.
The read-only source inspection found a666B setup.py,38B setup.cfg, no pyproject,
community package, networkx/numpy requirement declarations and bin/community script.
A build must not import the target community library or install its requirements.

The proposed backend is setuptools84.0.0, not a floating latest dependency.
[Official release metadata](https://pypi.org/pypi/setuptools/84.0.0/json) advertises
Python>=3.10 and the following non-yanked wheel:

- Filename: setuptools-84.0.0-py3-none-any.whl.
- URL: https://files.pythonhosted.org/packages/95/9c/c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/setuptools-84.0.0-py3-none-any.whl.
- Size:818,216B; SHA25651a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670.
- Advertised metadata SHA2563ef2975718dd31cabdd5829455e9b868ca14dbf79ed8fed2de0af4e87347006e,
  not independently read or verified from the actual wheel yet.
- Requires-Dist is nonempty but all entries are extras-gated; no extras are selected.

The versioned [backend source](https://raw.githubusercontent.com/pypa/setuptools/v84.0.0/setuptools/build_meta.py)
starts wheel build requirements with an empty list and implements build_wheel via
bdist_wheel. Its [initializer](https://raw.githubusercontent.com/pypa/setuptools/v84.0.0/setuptools/__init__.py)
exposes vendored dependencies; the [wheel command](https://raw.githubusercontent.com/pypa/setuptools/v84.0.0/setuptools/command/bdist_wheel.py)
uses that available packaging/wheel path. This supports a preliminary one-wheel
external tool closure. Actual wheel contents, vendor completeness and installed
tool namespace still need verification before treating the closure as proved.
Do not add pip/build/wheel/NumPy/NetworkX merely from a generic build recipe.

Retain the existing exact CPython3.11.15 executable pin. Read-only tool discovery
found UV0.9.25 at /home/utkarsh/.local/bin/uv and bubblewrap0.12.0 at /usr/bin/bwrap;
availability is not a passing namespace or build preflight.

## Smallest next implementation

1. Acquire the one exact backend archive under separately declared package-only
   bounds and verify full SHA, METADATA, every member and RECORD with the existing
   payload verifier. Stage/census its complete tool namespace separately from
   numerical runtime inputs; use no dependency resolution or implicit downloads.
2. Prepare a fresh bounded source extraction that refuses traversal, symlinks,
   hard links, special members, duplicate/aliased paths and expansion overflow.
   Pin every extracted source member and keep source, tools, build scratch,
   temporary files, logs and wheel output disjoint.
3. Prove a fail-closed network/process/filesystem namespace with an authored
   fixture before executing the backend. Freeze the trusted host/CPython stdlib,
   extension and ELF baseline explicitly. Hashing the executable alone does not
   freeze that baseline. Offline/no-index flags do not isolate source subprocesses.
4. Implement one fixed driver using P -I -S, only the staged backend path, a cleared
   environment and empty user-configuration home. Route generated build/egg-info
   files to scratch with the source read-only. Direct build_meta.build_wheel and
   its global-option routing are candidates, not tested commands; verify them on
   an authored source fixture first. Do not add pyproject or modify source inputs.
5. Independently review the exact source/configuration; invoke once, preserve any
   failure and audit the terminal outcome. Acceptance requires exactly one
   python_louvain-0.16-py3-none-any.whl, full payload/metadata/RECORD verification,
   retained digest/size, unchanged source hashes and no owned survivors.

Proposed initial build allocation, to be finalized with the exact driver:
120s wall,60s CPU,512MiB address space,256MiB aggregate writable storage,4MiB
logs,8MiB wheel output and one invocation without automatic retry. No mount,
privilege, process namespace or source-execution probe has run yet.

This build output would complete one missing package artifact. Installed runtime
relocation/scripts, licences, native/EGL paths, tmpfs custody, four-import
qualification and the complete simulator episode remain separate exits.
