# Puck collection envelope: source evidence

`admit_collection_envelope` consumes bounded immutable JSON bytes and supplied
source/runtime observations. It checks the externally expected description hash,
four admitted collection-layout identities, the historically pinned original
model-index metadata, all twelve scene-major/seed-minor invocations, exact runtime
and source observations, one-attempt description and frozen resource ledgers.
It returns isolated copies with `executable: false` and no qualification claims.
The existing owner rejects that complete returned object before runtime imports.

Within the unchanged 160 MiB owner cap, 8 MiB snapshot, two 1 MiB logs and 1 MiB
combined metadata leave 149 MiB recording. The child/parent/return/hard ledger
remains 2160/50/50/10 seconds with 2210/2260/2270 boundaries. Collection interval
entries remain at most 57,600 before other metadata; global retained namespace
and reservation admission remain separate. No file is published by this API.

The initial test fixture incorrectly called the public minter with locked IDs;
that invocation refused before any mint. The fixture was corrected to synthetic
metadata, the preliminary implementation removed, and faithful RED `5c4ea49`
then reproduced all 33 missing-checker failures. A test import-path correction
uses the same scripts path as the existing native-boundary fixtures. Final new
tests pass **33/33**; the affected five-file suite passes **110 tests in 1.59s**:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  ../r0-reproduction/.venv/bin/python -m pytest -q \
  tests/test_puck_collection_admission.py tests/test_puck_on_policy_native_interval.py \
  tests/test_puck_on_policy_interval.py tests/test_puck_on_policy.py tests/test_records.py
```

Fresh import excludes Torch/MuJoCo/Engine/model; compilation, unchanged frozen
v3 protocol SHA `fe8b2615f965a114274a13aeb2d49c26d3f79e0920eee72bce4eb671adff3d13`
and whitespace checks pass. Historical modules, protocols and profile checks
remain unchanged. Independent review is the publication gate.

The expected description digest is a caller trust boundary. This API neither
discovers source files nor proves the supplied closure complete nor measures a
runtime. It checks canonical layout identities rather than registry/scene
publication provenance. It reads the committed original-index metadata in tests,
never checkpoint bytes. It does not consume an attempt, enforce live deadlines,
lease processes, monitor RSS/storage, qualify native capture or close an owner.
Historical construction/mechanics/learning/bundle profile-pin conflicts still
require a separately reviewed v3 execution/provenance adapter. Native routes,
collection, fitting, development, held-out and power-loss qualification stay
closed. CI and the physical rover remain excluded.
