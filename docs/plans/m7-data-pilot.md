# M7 bounded MaleCNS data pilot

Checked 2026-10-02. This is an access/provenance and reduced-topology pilot for PRD §10.3 and implementation-plan M7. A candidate neighborhood is now extracted below; it is not a validated biological circuit, trained profile, or R3 completion. No controller or sensor mapping has changed.

## Sources and acquired asset

The latest listed [official release](https://male-cns.janelia.org/release/) is v1.0, dated 2026-06-08. The [download page](https://male-cns.janelia.org/download/) names `male-cns:v1.0` and links the dataset to [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Preserve source attribution and identify later modifications; this does not determine the terms of female-derived assets.

Only curated annotations were downloaded, after `git check-ignore` confirmed the asset path is ignored. An exclusive-create download pinned GCS generation `1780494878811468`, checked Content-Length, and enforced a 20 MiB stream cap. HTTP 200 yielded **14,483,314 bytes**, SHA-256 `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`. Exact URLs, response headers and UTC times are in [the manifest](../../data/manifests/malecns-pilot.json). `ARROW1` header/footer bytes identify the container; they do not validate its schema.

The full connection file was HEAD-only: HTTP 200, **1,051,241,946 bytes**, generation `1780494887545976`; no body or SHA-256 was acquired. Neurotransmitter, synapse, volume and morphology assets were not fetched.

## Actual readers and public API

The first read through the existing lab-hardening environment failed because PyArrow was absent; that failed capture remains retained. A separate, ignored `malecns-pilot/.venv` now pins **PyArrow 25.0.1** with Python 3.11.15. The [official Arrow reader](https://arrow.apache.org/docs/python/feather.html) verified **211,577 rows and 36 columns**. The two candidate rows match the API on bodyId/type/instance/status/somaSide. All column types and null counts are retained; `cropped` is absent. The running M3 environment and project lockfile were unchanged.

The official [neuprint-python 0.6.4 client documentation](https://connectome-neuprint.github.io/neuprint-python/docs/client.html) describes JSON custom queries; its [version-pinned implementation](https://github.com/connectome-neuprint/neuprint-python/blob/0.6.4/neuprint/client.py) supplies the HTTP route. Using Python stdlib, no Authorization header and no credential search:

- GET `/api/serverinfo` returned HTTP 200, `IsPublic=true`, server 1.9.5. Its announcement says existing API tokens no longer work following the August 2026 authentication migration. No existing token was assumed valid.
- GET `/api/version` confirmed 1.9.5. GET `/api/dbmeta/datasets` exceeded the 65,536-byte cap and was deliberately not parsed.
- POST `/api/custom/custom`, with explicit dataset `male-cns:v1.0`, succeeded: HTTP 200, 1,785 bytes, two rows. This demonstrates public access for this exact bounded query at this time, not guaranteed access to every endpoint or a credentialed client.

The manifest preserves the exact query, response schema, hash and returned property keys. The API response and separately verified Feather schema remain distinct records. `keys(n)` contained `roiInfo` and predicted neurotransmitter properties, but their values were not requested.

| bodyId | type | instance | somaSide | status | pre | post |
| --- | --- | --- | --- | --- | ---: | ---: |
| 12781 | DNge104 | DNge104_R | R | Traced | 3831 | 13487 |
| 556329 | DNge104 | DNge104_L | L | Traced | 4034 | 14095 |

These identifiers originated as official documentation examples and are now annotation-confirmed candidates. `cropped` returned null and is absent from both property-key lists: completeness/truncation is **unknown**, not false. `somaSide` records the returned soma-side annotation; it does not establish output laterality. Pre/post totals are annotations, not an extracted circuit or physiological weights.

## Initial extraction proposal and unresolved biological boundary

A small next feasibility check could use this pair as candidate endpoints and inspect their direct incoming partners. It must first count the proposed extraction, then reject an oversized result explicitly rather than silently truncating it. Proposed engineering limits are 256 nodes, 4,096 directed edges and 4 MiB JSON with a 30-second request timeout; these are resource caps, not scientific success thresholds. The present API probes used 65,536-byte response caps and a 25-second timeout. No adjacency query ran in the initial annotation slice; the follow-up below records bounded extraction.

Endpoint fan-in is only an output-neighborhood candidate. Selecting a sensory population requires independent anatomical/functional documentation, annotation coverage and an actual directed path check. No population is assigned to the rover's symbolic cue, camera or action dimensions here. Before freezing an extraction, record:

1. Explicit retained neuron IDs, API/raw-table schema and dataset snapshot identity; type/side coverage and missing-value policy; ROI and truncation eligibility without interpreting absent properties as negative evidence.
2. Directed edges and chosen synapse-confidence/weight rule, including zero/duplicate handling. Use total connection counts or nonoverlapping primary-ROI accounting; overlapping ROI rows must not be summed as independent edges. Check the [official query contracts](https://connectome-neuprint.github.io/neuprint-python/docs/queries.html), not example tuple-variable names.
3. Retained sensory-to-output reachability and every cut input/output: incoming partners outside the chosen fan-in, inputs to its upstream nodes, omitted neuropils and downstream populations. Quantify omitted synapse-count mass when available; no such coverage was measured here.
4. Whether counts define topology or initialize trainable weights; predicted neurotransmitter values, uncertainties and absent values remain separate from measured physiology.

If this reduced boundary lacks documented sensory input or exceeds the caps, report that result and revisit circuit choice before implementing a model. A later supported interface needs a separately trained/calibrated male-ID profile, size-matched controls, equal information/training budgets and multiple training seeds. Female-trained parameters must not be loaded onto these IDs. Nothing in this pilot establishes a compatible trained model, topology benefit or biological sensor mapping.

## Local evidence and checks

`data/assets/malecns-metadata/` contains the annotation asset and five small acquisition/read/API records, including the initial failed reader attempt. All assets remain ignored. The manifest is an explicitly tracked exception to the repository-wide `data/` ignore rule; the rule was not changed and raw assets remain ignored. The initial annotation slice performed no graph extraction; the follow-up below is separately indexed. No model job or authenticated query was performed.

Validation covers JSON parsing, manifest-to-capture consistency, asset size/SHA-256, raw schema/candidate matching and `git diff --check`. Reproduce the raw read with `.venv/bin/python scripts/inspect_malecns_annotations.py` after installing the pinned isolated reader above. This bounded pilot is finished; full M7/R3 gates remain open.

Root review independently parsed the manifest and rechecked the annotation asset size and SHA-256. The initial pre-reader manifest SHA-256 was `4aae4865f533fc6c94880ea8cb5b473d33a191fa78b09cbb8d74ec55927268ff`.

The reader is [a runnable check](../../scripts/inspect_malecns_annotations.py); it rejects changed asset bytes and raw/API candidate contradictions. Reading annotations does not resolve candidate truncation, sensory mappings or directed circuit eligibility.

## Reduced topology follow-up

The count-only public query found **3,550 Neuron inputs / 3,741 directed connections /
21,773 summed connection weight** into the two endpoints. This exceeds the
proposed 256-node cap. A feasibility grid gave:

| Minimum input connection weight | Input neurons | Connections | Weight |
| ---: | ---: | ---: | ---: |
| 1 | 3,550 | 3,741 | 21,773 |
| 2 | 2,470 | 2,582 | 20,614 |
| 5 | 1,136 | 1,170 | 16,804 |
| 10 | 501 | 514 | 12,522 |
| 20 | 136 | 144 | 7,526 |
| 50 | 41 | 44 | 4,692 |

The chosen engineering reduction uses the lowest listed threshold fitting the
node cap: endpoints plus their inputs with total connection weight at least 20.
It then retains every positive-weight directed connection induced by those IDs.
This selection followed resource counts, before training or task outcomes; it
is not an anatomical completeness threshold or a held-out scientific protocol.

[The extractor](../../scripts/extract_malecns_pilot.py) freezes the dataset,
endpoint IDs, selection rule, 256-node/4,096-edge caps, four-MiB response cap and
30-second request timeout. It counts before fetching, rejects oversized or
inconsistent results, preserves every query/response hash, and verifies the
induced graph still contains the selected strong endpoint inputs. Connection
`weight` follows the [official total-weight query contract](https://github.com/connectome-neuprint/neuprint-python/blob/0.6.4/neuprint/queries/connectivity.py);
overlapping ROI rows are not summed.

Actual extraction on 2026-10-02 produced **138 nodes and 1,647 directed edges**,
summed internal weight **18,787**. The induced graph retains endpoint input weight
**7,603 / 21,773 (34.92%)**; 7,526 above counts only strong selecting edges, while
7,603 includes additional weak endpoint edges among retained nodes. The omitted
Neuron-only boundary remains large: **57,331 incoming edges / weight 341,520** and
**71,933 outgoing edges / weight 454,980**. Non-Neuron segments are outside these
counts. Counts are anatomical connection annotations, not physiological efficacy.

The exact IDs, annotations, directed edges and cut-boundary totals are in the
ignored `data/assets/malecns-metadata/reduced-neighborhood-v1b/graph.json`, SHA256
`5aba0fef99afba666b88e40fc535091454e46d9330580d9280b203e8da0abac0`.
[The tracked manifest](../../data/manifests/malecns-reduced-neighborhood-v1.json)
binds the graph, final extractor source, raw records, dataset, source licence and
attribution. The earlier extraction remains retained separately. The API accepts
the named dataset but provided no immutable server snapshot identifier.

Reproduce in a new output directory:

```sh
python scripts/extract_malecns_pilot.py --output data/assets/malecns-new-extraction
PYTHONPATH=src:tests python -m unittest test_malecns_pilot -v
```

The actual final extraction passed schema/count/identity/boundary checks. Two
offline fixture tests also passed (0.007 s), covering complete extraction and
rejection of oversized/contradictory query results. Neither result validates a
biological camera/cue mapping, a closed biological circuit, a trained male-ID
controller or topology benefit. A later interface may explicitly use artificial
boundary encoders, but must remain labelled as such and receive separate training
and matched-control evaluation. M7/R3 remains open.
