# Read-only prepared asset resolver implementation

Baseline: 0e21d0b5584abae9a1adf9dafb72ca605dc64c64. Owned deliverables only `src/palimpsest/assets.py` and new `tests/test_assets_prepared_readonly.py`. Parent owns the tracked contract document; its concurrent modification is excluded from this worker commit.

## Behavior

Appended `resolve_prepared_assets_readonly(repo_root: Path, asset_root: Path) -> dict`. Returns exactly archive/checkpoint/edge Paths. It canonicalizes safe roots only after inspecting their spelling and every ancestor type, checks named directories and regular leaves without accepting symlinks, uses the real `load_manifest`, and validates original archive/checkpoint identities. It reads only the exact prepared graph directory/metadata/manifest edge member. Prepared metadata has a pre-open 1 MiB size check and a bounded limit+1 byte read before decoding; duplicates, nonfinite values (including exponent overflow), altered keys/values/nested mappings, and Python-equal-but-JSON-different numeric types refuse. Mapping checks use unchanged `_check_mappings(..., copy_missing=False)` after every source/prepared mapping leaf type is checked. No preparation/acquisition/repair/fallback/write occurs.

Parent ruling during implementation: safe relative repo/asset root inputs are allowed and normalize to absolute canonical output Paths. Reject lexical `..`, every symlink root/ancestor/named input, and nonregular leaves; do not change CWD. A positive relative-root test records the ruling. This generic helper does not relax the future frozen-source job's independent exact absolute-root admission rule.

## Retained TDD and final evidence

Every run used a fresh `mktemp -d /var/tmp/palimpsest-readonly-{red,iteration,final}-XXXXXXXX` parent and previously absent `$run_dir/fixtures` pytest basetemp. All authored files and logs are retained. Fixtures clone only named static project `model_manifests/flynn-full-vision.json` metadata and replace identities with tiny authored file bytes; real `load_manifest` parses the written synthetic manifest. No manifest/guard validator patches. Side-effect denial patches are active only during the actual resolver call. Before/after retained-tree snapshots check names, bytes, symlink targets, inode/device, modes, sizes, mtime/ctime; CWD remains unchanged. No fixture deletion or cleanup helper exists.

Exact command environment, each run:

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_assets_prepared_readonly.py FLAGS --basetemp="$run_dir/fixtures" > "$run_dir/pytest.log" 2>&1
```

- RED, FLAGS `-q -x`: `/var/tmp/palimpsest-readonly-red-jqabCYBv/pytest.log`, 1 failed in 0.10 s, expected `AttributeError` because the new resolver did not exist. No implementation preceded this failure.
- Iteration, FLAGS `-q -x`: `/var/tmp/palimpsest-readonly-iteration-MGJKDp0T/pytest.log`, 222 passed in 1.01 s.
- Final settled code, FLAGS `-q`: `/var/tmp/palimpsest-readonly-final-5cuEE3jh/pytest.log`, 222 passed in 1.00 s. This command was prefixed by `/usr/bin/time -f 'wall_seconds=%e user_seconds=%U system_seconds=%S max_rss_kib=%M' -o "$run_dir/time.txt"`; retained time.txt reports wall 1.22 s, user 0.86 s, system 0.34 s, max RSS 50428 KiB.

The 222 cases cover: two successful path/CRLF/relative-root cases; missing each of 19 roles; wrong size/hash for every 17 payload leaves; all six metadata identity fields missing/wrong/type; complete metadata entries for all seven mappings; bool/int and float/int distinction; duplicate/nonfinite/nonobject/malformed JSON; extra metadata key; wrong/unsafe metadata paths; unsafe trusted manifest members; no edge search; root symlink/ancestor/traversal; every named leaf replaced by symlink/directory/FIFO; symlinked named directories; missing roots/prepared directory; exact 1 MiB boundary/one-over pre-open refusal; and seven separately rebound archive hashes that still fail the required CRLF-to-LF source relationship.

## Preservation and self-review

`git show 0e21d0b:src/palimpsest/assets.py` was retained as `readonly-assets-evidence/baseline-assets.py`. Python AST comparison parsed baseline/current source, stripped only the appended resolver from the current module, and asserted complete AST equality. PASS: all 21 existing top-level nodes, including imports/constants/all function bodies/defaults, unchanged. Evidence: `readonly-assets-evidence/ast-preservation.txt`. `git diff --check` passed. Manual diff review checked bounded decoding, exact JSON identity comparisons, canonical path handling before reads, no graph search, no-writes/no-repair, all mapping source/archive checks, unchanged preparer/Engine/defaults/pins, and no framework/qualification marker. Final tracked status before commit showed only the two owned files plus the parent-owned contract document.

## Limits and outstanding gates

This establishes current byte/path read-only verification on authored fixtures. It does not establish continuous FD custody, hostile-process isolation, provenance/permissions, actual assets readiness, real source/backend/wrapper qualification, runtime/model/native behavior, scientific results, or deletion authority. No actual asset/checkpoint/graph/mapping/native/runtime/catalog/raw/SNP payload was read or hashed; no network/dependencies/probe/research/CI/push/deletion/worker agents. No old `tests/test_assets.py` or broader suite was run, as explicitly prohibited. Independent spec/code review belongs to root and has not yet occurred. Full goal remains active; user CPU-provider/export/GO inputs remain missing, raw deletion disabled, 24 CPU-hour lanes 1/12/5/4/2 unchanged, actual qualified experiment cost unmeasured, account quota UNKNOWN. These ordinary authored tests are not a research run or qualification.

Commit: `482589b` (`feat: verify prepared FLYNN assets without writes`). Post-commit readback shows exactly the two owned files, 447 inserted lines; working-tree status contains only the parent-owned tracked contract modification.
