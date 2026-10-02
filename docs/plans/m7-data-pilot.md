# M7 bounded MaleCNS data pilot

Checked 2026-10-02. This is an access/provenance pilot for PRD §10.3 and implementation-plan M7, not a circuit extraction, trained profile, or R3 completion. It changes no controller, sensor mapping or graph.

## Sources and acquired asset

The latest listed [official release](https://male-cns.janelia.org/release/) is v1.0, dated 2026-06-08. The [download page](https://male-cns.janelia.org/download/) names `male-cns:v1.0` and links the dataset to [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Preserve source attribution and identify later modifications; this does not determine the terms of female-derived assets.

Only curated annotations were downloaded, after `git check-ignore` confirmed the asset path is ignored. An exclusive-create download pinned GCS generation `1780494878811468`, checked Content-Length, and enforced a 20 MiB stream cap. HTTP 200 yielded **14,483,314 bytes**, SHA-256 `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`. Exact URLs, response headers and UTC times are in [the manifest](../../data/manifests/malecns-pilot.json). `ARROW1` header/footer bytes identify the container; they do not validate its schema.

The full connection file was HEAD-only: HTTP 200, **1,051,241,946 bytes**, generation `1780494887545976`; no body or SHA-256 was acquired. Neurotransmitter, synapse, volume and morphology assets were not fetched.

## Actual readers and public API

The existing lab-hardening Python 3.11.15 environment has pandas 2.2.3 but no PyArrow, neuprint-python, alternate Feather reader or Rscript. `pandas.read_feather` failed with `ImportError: Missing optional dependency 'pyarrow'.` No package was installed or binary-format parser implemented. The raw annotation table's column names, types, row count and candidate rows remain **unverified**.

The official [neuprint-python 0.6.4 client documentation](https://connectome-neuprint.github.io/neuprint-python/docs/client.html) describes JSON custom queries; its [version-pinned implementation](https://github.com/connectome-neuprint/neuprint-python/blob/0.6.4/neuprint/client.py) supplies the HTTP route. Using Python stdlib, no Authorization header and no credential search:

- GET `/api/serverinfo` returned HTTP 200, `IsPublic=true`, server 1.9.5. Its announcement says existing API tokens no longer work following the August 2026 authentication migration. No existing token was assumed valid.
- GET `/api/version` confirmed 1.9.5. GET `/api/dbmeta/datasets` exceeded the 65,536-byte cap and was deliberately not parsed.
- POST `/api/custom/custom`, with explicit dataset `male-cns:v1.0`, succeeded: HTTP 200, 1,785 bytes, two rows. This demonstrates public access for this exact bounded query at this time, not guaranteed access to every endpoint or a credentialed client.

The manifest preserves the exact query, response schema, hash and returned property keys. This is a verified API result, **not** a verification of Feather schema. `keys(n)` contained `roiInfo` and predicted neurotransmitter properties, but their values were not requested.

| bodyId | type | instance | somaSide | status | pre | post |
| --- | --- | --- | --- | --- | ---: | ---: |
| 12781 | DNge104 | DNge104_R | R | Traced | 3831 | 13487 |
| 556329 | DNge104 | DNge104_L | L | Traced | 4034 | 14095 |

These identifiers originated as official documentation examples and are now annotation-confirmed candidates. `cropped` returned null and is absent from both property-key lists: completeness/truncation is **unknown**, not false. `somaSide` records the returned soma-side annotation; it does not establish output laterality. Pre/post totals are annotations, not an extracted circuit or physiological weights.

## Next extraction boundary, still provisional

A small next feasibility check could use this pair as candidate endpoints and inspect their direct incoming partners. It must first count the proposed extraction, then reject an oversized result explicitly rather than silently truncating it. Proposed engineering limits are 256 nodes, 4,096 directed edges and 4 MiB JSON with a 30-second request timeout; these are resource caps, not scientific success thresholds. The present API probes used 65,536-byte response caps and a 25-second timeout. No adjacency query ran in this pilot.

Endpoint fan-in is only an output-neighborhood candidate. Selecting a sensory population requires independent anatomical/functional documentation, annotation coverage and an actual directed path check. No population is assigned to the rover's symbolic cue, camera or action dimensions here. Before freezing an extraction, record:

1. Explicit retained neuron IDs, API/raw-table schema and dataset snapshot identity; type/side coverage and missing-value policy; ROI and truncation eligibility without interpreting absent properties as negative evidence.
2. Directed edges and chosen synapse-confidence/weight rule, including zero/duplicate handling. Use total connection counts or nonoverlapping primary-ROI accounting; overlapping ROI rows must not be summed as independent edges. Check the [official query contracts](https://connectome-neuprint.github.io/neuprint-python/docs/queries.html), not example tuple-variable names.
3. Retained sensory-to-output reachability and every cut input/output: incoming partners outside the chosen fan-in, inputs to its upstream nodes, omitted neuropils and downstream populations. Quantify omitted synapse-count mass when available; no such coverage was measured here.
4. Whether counts define topology or initialize trainable weights; predicted neurotransmitter values, uncertainties and absent values remain separate from measured physiology.

If this reduced boundary lacks documented sensory input or exceeds the caps, report that result and revisit circuit choice before implementing a model. A later supported interface needs a separately trained/calibrated male-ID profile, size-matched controls, equal information/training budgets and multiple training seeds. Female-trained parameters must not be loaded onto these IDs. Nothing in this pilot establishes a compatible trained model, topology benefit or biological sensor mapping.

## Local evidence and checks

`data/assets/malecns-metadata/` contains the annotation asset and four small acquisition/read/API records. All assets remain ignored. The manifest is an explicitly tracked exception to the repository-wide `data/` ignore rule; the rule was not changed and raw assets remain ignored. No graph extraction, model job or authenticated query was performed.

Validation is limited to JSON parsing, manifest-to-capture consistency, asset size/SHA-256 and `git diff --check`. Feather row validation is blocked on the missing reader. This bounded pilot is finished; full M7/R3 gates remain open.

Root review independently parsed the manifest and rechecked the annotation asset size and SHA-256. The reviewed manifest SHA-256 is `4aae4865f533fc6c94880ea8cb5b473d33a191fa78b09cbb8d74ec55927268ff`.
