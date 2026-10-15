# CPU runtime footprint: metadata evidence and admission gaps

## Result

The CPU alternative now has exact wheel metadata rather than an assumed size.
Assessment02 completed with **70 wheels**, comprising **71 candidate distributions
including the unresolved source-only python-louvain0.16**. The complete unchanged
project simulation, lab and development requirement graph reaches every selected
wheel; Linux/CPython3.11 markers and extras yield no version conflict. The initial
manual tally of71 wheels was corrected by the independent audit before publication.

| Metadata evidence | Independently checked value |
| --- | ---: |
| Selected archives, declared sizes | 385,123,877B |
| ZIP-directory declared expanded bytes | 1,304,650,469B |
| Non-directory archive entries | 26,913 |
| 4KiB rounded-file estimate | 1,372,884,992B |
| HTTP requests / body bytes read | 493 / 3,841,841B |
| Largest response body | 1,451,979B |

The original CUDA registration is8,172,376,285 logical bytes. The new figures are
archive metadata estimates, **not a measured installed namespace or a qualified
runtime**. Do not treat the difference as a measured performance improvement.

The official [PyTorch previous-version instructions](https://pytorch.org/get-started/previous-versions/#v290)
provide the matching2.9.0/0.24.0 CPU channel. The retained
[Torch CPU index](https://download.pytorch.org/whl/cpu/torch/) and
[torchvision CPU index](https://download.pytorch.org/whl/cpu/torchvision/)
supply exact CPython311/manylinux2_28/x86_64 archive names and SHA declarations.
Torch2.9.0+cpu declares682,736,265 expanded bytes; torchvision0.24.0+cpu declares
6,099,565. Its torch==2.9.0 requirement accepts the local +cpu version under the
inspected packaging26.3 rules. No active CPU Torch requirement adds NVIDIA/Triton.
The unchanged production uv.lock still selects CUDA; no installation lock was
silently changed.

## Acquisition, failure and audit

[Assessment01](puck-cpu-footprint-01/failure.json) is a terminal failed metadata
probe. pandas returned a non-ASCII License email Header object; JSON serialization
failed, including final-summary publication. Its raw summary consequently remains
in_progress. The executed process exited1 (tool session47110, final chunkf4d6d7);
that exit and the separately retained failure record establish terminal failure.
38 completed wheel rows, the acquired pandas metadata and request records remain
unchanged. A local reproduction confirmed the exact TypeError, and converting
metadata header values to strings made serialization succeed.

[Assessment02](puck-cpu-footprint-02/assessment.json) is separately numbered and
exited0 (tool session79183, final chunk80d7cb). Its script changes only the report
directory and header/string normalization. It completed at2026-10-15T04:27:03Z.
This is metadata acquisition, not a numerical experiment or a new runtime allocation.
No consumed preparation, qualification, observation or navigation command ran.

Both directories retain the exact throwaway assessment script, official index
HTML, METADATA members, ZIP-entry metadata and request records. The scripts are
historical research artifacts, not product/installation entry points; do not rerun
them into retained output directories. No archive member code was installed or
executed. Bounded requests read indexes, ZIP directories and selected METADATA
members, with 8MiB response/32MiB total body limits, 20s request timeout and a480s
between-request deadline check. That clock is not a hard supervisor bound.
Requests require allowed HTTPS hosts, strong ETags, conditional range reads,
HTTP206 and exact Content-Range. Full archive payload hashes were not calculated.
The [Simple Repository metadata contract](https://packaging.python.org/en/latest/specifications/simple-repository-api/#serve-distribution-metadata-in-the-simple-repository-api)
distinguishes separately served metadata from the archive; metadata is not full
payload verification.

Independent offline audit confirmed all70 metadata hashes, identities,
Requires-Dist fields, entry sizes/counts and all68 ordinary URL/hash/size references
against uv.lock; the two CPU references match the retained index HTML. All70 wheel
tags match the host CPython3.11/Linux supported tags, and all Requires-Python
fields accept3.11.15. No symlink/special-mode archive entries were found. Request
records comprise70 HEAD/200,421 GET/206 and two index GET/200 responses.
Root's separate [offline cross-check](puck-cpu-footprint-02/crosscheck.json) checked
112 active requirement edges and reproduced counts/sums; its initial asserted
71-wheel tally failed before output and was corrected to70. This is data checking,
not a passing software test suite or an actual numerical import result.

## Candidate and resource decision

The [prospective candidate](../plans/puck-cpu-runtime-candidate-v1.json) pins71
versions and exact evidence references, with every execution/qualification/study
flag false. Its [host snapshot](puck-cpu-footprint-02/host-metadata.json) measured
3,877,453,824B MemAvailable. Rounded wheel files plus the proposed2GiB worker
sampled-RSS threshold and1GiB additional available-RAM reserve require a planning
estimate of4,594,110,464B. Adding the historical49 external CUDA-observation images
as a proxy gives5,132,641,600B. **Neither scenario fits that RAM snapshot.**
The external set is a historical proxy; it is not the required CPU/EGL closure.
These estimates exclude the source build and directory/installer overhead, are
not RAM reservations, and do not establish hard memory limits. Disk/tmpfs capacity
and live RAM must be admitted again on the final exact configuration.

Shared tmpfs staging is also conditional. An independent metadata-only inspection
observed /dev/shm root mtime/ctime change1792038148382361054 to1792038183965238478ns,
same dev32/inode1, without creating files itself. Its actor is unknown. The full
ancestor guard therefore correctly refuses unrelated sibling churn even below a
mode0700 private child. Precreate inputs/site, inputs/native, inputs/registration,
scratch and outputs before custody; put mutable scratch/output entries outside
fully censused input roots. Mount flags and effective access suggest candidate
locations, but no execution/LSM or uninterrupted custody interval was proved.
No privileges or mounts were changed.

## Remaining work before actual execution

- Build and hash an exact python-louvain0.16 wheel in a separately admitted bounded
  build configuration; its locked204,641B sdist is not an assessed installed wheel.
- Verify full archive hashes, RECORD and installed namespaces, relocation/generated
  files, actual tmpfs allocation and licences. Licence fields/file names are not
  a bundled-licence audit; PyOpenGL and seaborn have no retained licence field,
  expression or License-File declaration in this metadata.
- Integrate the [reviewed four-import entry](puck-cpu-runtime-entry-source.md)
  into a separately numbered exact CPU parent/configuration. The allocation01
  parent remains three-import and consumed. The new source includes torchvision;
  an import result still does not prove its operators/codecs or inference.
- Specify the exact interpreter/stdlib trusted baseline, all native origins and
  external-library paths, EGL vendor/renderer configuration and shared-root custody.
  Do not assume this exact interpreter needs copying: historical maps contain no
  lib-dynload images. CPU Torch does not establish software-only rendering.
- Complete whole-stage resource/process/clock admission and a separately numbered
  prospective configuration/observation decision, independent exact review,
  bounded authorized execution and independent terminal outcome audit.

No installation, source build, actual NumPy/Torch/torchvision/MuJoCo import,
model/scene/catalog/study access, inference, renderer context, physics, collection,
training, browser/human session or rover work ran. All seven simulation release
gates remain open. Source and metadata progress do not close them.
