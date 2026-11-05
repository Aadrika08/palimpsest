# Explicit audit input preparation

`prepare_inputs.py` is stdlib source authoring and explicit file hashing. It
imports no native runtime or model and never runs a pilot. Its independent
software fixtures use tiny authored files, a temporary Git repository, and
injected interpreter/source-state metadata. Fixture acceptance is not scientific
or runtime qualification.

`namespace_documents(plan_descriptor)` is pure. It describes only the public
cohort IDs named in the approved completion plan: puck 6110–6113, 6120–6123 and
6200–6207; MaleCNS 3130–3133 and 3120–3127; conservative training seeds 10, 11 and
12. The four proposed roots are reproduction/checker seeds 91001–91004. The
namespace source retains the approved public plan's exact file descriptor and
states that no geometry, pretraining or sampling disjointness is established.
No protected catalog or held-out metadata is opened to construct this projection.

The CLI has two explicit modes:

- `plan-only --approved-plan PATH --expected-plan-sha256 SHA --output FRESH_DIR`
  writes immutable `namespace-source.json`, the exact `pilot.py` namespace
  projection schema, and a preparation receipt. It does not accept runtime/model
  paths or read those files.
- `execute-preparation` additionally requires `--config PATH` and
  `--expected-config-sha256 SHA`. It hashes only the explicitly selected files,
  emits the exact `pilot.py` input-roster schema, and retains its receipt. This
  is research preparation and must be externally admitted and metered. There
  are no retries, asset downloads, archive extraction or package scanning.

The execute config has exactly these fields:

- `repo_root`, `asset_root`, `prepared_graph_directory`: absolute existing paths;
- `source_commit`: exact full Git HEAD;
- `source_files`, `runtime_files`, `model_files`: nonempty explicit file lists;
- `python_executable`: explicit interpreter path, resolving to the current
  executing Python executable.

Selected project source files must be within the pinned repository and tracked.
The actual tracked tree must be clean at that exact HEAD before and after
hashing. The caller supplies the complete desired source/runtime/model closure;
this helper does not discover it or certify completeness. Interpreter version,
its file identity, the selected runtime/model/source descriptors and requested
to resolved path mappings enter runtime metadata. Dependency completeness is
explicitly false. This metadata grants no claim that the installed environment
is usable or fully captured.

Each explicit symlink alias is resolved to its physical regular-file target.
Canonical targets become roster paths, so the worker's regular-file checks do
not traverse those aliases. Duplicate canonical targets across the three
explicit file lists are rejected. An explicitly listed interpreter or approved
plan is included only once when the implicit required descriptors are added.
The approved plan and generated namespace source are included in the roster.
The helper rechecks every pinned file descriptor after the final Git check and
rechecks the approved plan and frozen config before success. Config checksums
bind the exact bytes decoded; nonfinite numbers and duplicate JSON keys fail.
No recursive file discovery is performed, and the caller must select approved
source/assets/runtime files rather than protected catalogs.

Output directories are fresh and cannot traverse symlinks. Every JSON file uses
exclusive publication, finite values, file fsync and parent-directory fsync.
Any failed or partial artifacts are retained. Bounds are 2MiB per control JSON,
8MiB total authored output, 4096 selected/retained input descriptors and 64GiB
aggregate retained input-file sizes. These are inventory bounds; verification
can hash a selected input twice. Actual process wall/CPU admission and resource
ceilings belong to the caller.

Every attempt that enters preparation retains a success/failure receipt when
the destination is writable, including config-hash, source-state, hashing and
publication failures. An invalid mode or unavailable/existing output directory
fails before a new receipt can be published there. The receipt samples the
change in `RUSAGE_SELF + RUSAGE_CHILDREN` after the final checks, including waited
Git subprocesses and failed work. It honestly sets
`requires_parent_final_process_accounting=true` and
`cpu_accounting_complete=false`: the caller must meter the completed process,
including final receipt serialization, fsync, output and exit, and charge this
preparation to the approved research budget before further admission. A receipt
with unknown final accounting does not itself authorize a pilot.

All scientific/qualification flags remain false. Public namespace IDs alone do
not establish independent sampling, complete pretraining identity or scene and
geometry disjointness. The parent retains independent roster review, exact
source/runtime/input verification, full storage admission and all study gates.
