# R0 reproduction evidence — 2 October 2026

M0 is complete for the pinned FLYNN full-vision profile on the development laptop. Later milestones are not qualified by this report. The machine-readable [evidence index](r0-2026-10-02.json) contains per-episode results, chunk hashes, neuron-order digest, mapping coverage and exact resource measurements.

## Executed checks

- 62 local fixture tests passed, without skips; [GitHub CPU fixture CI](https://github.com/Aadrika08/palimpsest/actions/runs/36966522233) also passed for `818fd3e`.
- Both downloaded assets, the extracted graph and all seven mapping files passed pinned identity checks. Archived CRLF mappings remain unchanged; separate Git LF identities and normalized equality are checked.
- MuJoCo 3.3.6 rendered through EGL on the NVIDIA GeForce RTX 4050 Laptop GPU. Runtime: Python 3.11.15, Torch 2.9.0, float32, two CPU threads, Linux x86_64, NVIDIA driver 610.57.04. Dependencies are locked in `uv.lock`.
- The original single-episode teacher reference reached the goal in 366 ticks. FLYNN reached it in 375 ticks with parity checked at every tick, including camera conversion, effective neural input, unsanitized readout, action, hidden state and retina state. The largest measured absolute discrepancy was `1.1920928955078125e-07`, within `atol=rtol=1e-6`.
- The full graph has 138,584 neurons and 5,342,446 edge-list rows. Checkpoint structural buffers exactly matched reconstruction before weights were loaded. This establishes present compatibility, not original training lineage.
- Every numeric chunk in the reference and two completed development batches passed integrity/schema/count checks. All 30 paired initial states and policy inputs matched exactly: seed, obstacle/goal positions, qpos/qvel, both camera arrays, contact/bearing sensors and pose.

## Development batch

Seeds 0–29, one fixed pretrained policy, 600-tick limit, 20 ms control interval, full input/action recording, sequential runs. These are development smoke seeds, not held-out test data. The teacher uses privileged geometry and is not an equal-information comparator.

| Observed result | Privileged teacher | FLYNN, CUDA |
| --- | ---: | ---: |
| Goal episodes | 30 / 30 | 28 / 30 |
| Time limits | 0 | 2 |
| Recorded control ticks | 8,654 | 10,611 |
| Controller latency p50 / p95 | 3.17 / 10.08 ms | 4.48 / 8.84 ms |
| Rollout wall time | 95.45 s | 120.17 s |
| Real-time factor | 1.81 | 1.77 |
| Peak process RSS | 783.4 MiB | 1571.0 MiB |
| Peak Torch CUDA tensor allocation | 0 | 141.2 MiB |

FLYNN timed out on seed 8 (remaining distance 2.370) and seed 23 (4.894). Torch allocation excludes driver, renderer, and other GPU allocations. Timing includes observation rendering and numeric chunk publication, excludes model loading, final summary publication and teardown. Loading took 4.85 s for the teacher worker and 19.03 s for FLYNN. Parity was disabled in this batch; its execution cost is confined to the separate reference run.

Upstream reset retains physics state and the teacher's previous path direction. Development batches therefore explicitly start fresh physics with `mj_resetData`, use upstream seeded layout generation, and reconstruct the teacher each episode. The earlier batch without this protocol was interrupted and excluded (`runs/teacher-dev-30`). Original single-episode reference bundles remain retained. Policy preprocessing, simulation substeps and action conversion were unchanged.

## Limits and retained evidence

The source checkpoint has no embedded training graph/ordered-ID lineage. Fifteen descending-neuron IDs and four wind-sensor IDs are absent from this edge list; upstream skips them. There are 1,467 graph neurons without assigned cell types. Exact missing-ID counts/digests are recorded, not replaced with fabricated mappings.

Raw bundles remain local and ignored by Git (about 2.0 GiB for the three indexed bundles): `runs/flynn-reference-1/`, `runs/teacher-independent-30/`, and `runs/flynn-independent-30/`. Each retains supervisor status/logs and `recording/{manifest.json,events.jsonl,chunks/}`. Cameras are lossless uint8 arrays; encoded inputs and raw readouts are retained for FLYNN. These are not full continuation snapshots. Full-model CPU performance, other hardware, memory learning, MaleCNS, topology comparisons and physical rover safety remain untested.

Verify the retained bundles again with a new output filename:

```sh
uv run --no-sync python scripts/verify_reproduction.py \
  --reference runs/flynn-reference-1 \
  --teacher runs/teacher-independent-30 \
  --flynn runs/flynn-independent-30 \
  --output runs/reverified-r0.json
```
