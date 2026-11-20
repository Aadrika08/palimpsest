# MaleCNS v4 stage P3: result (PASSED)

Stage P3 ran once on 2026-11-20 under owner GO (`go-P3.json`, pinned to tree head `408b2c81b355c80389660c355db3ad8c5b235a2e`),
with the A2 erratum 1 acknowledgement recorded in `decisions-2026-11-08.md`. `scientific_attempt: false`.

| Gate item | Observed |
| --- | --- |
| Unit | receipt `complete`, `drained`, returncode 0, no survivors; ledger `charged` P3 row |
| Cost | **29.042 CPU-s** measured (wall 31.0 s) against the 125 CPU-s reservation; manifest estimate 15 to 20 CPU-s |
| Report | `status: passed`, exactly 3 probes (`S2-binding`, `S2-owner-worker`, `S2`), each passed |
| Imports | no unresolved import, no optional-unresolved, no denied open, no reasons, `male-v4-data` never opened |
| Runtime | torch 2.9.0+cu128 with `torch_cuda_initialized: false`, CUDA_VISIBLE_DEVICES empty, mujoco 3.3.6 |
| EGL | exactly one non-null `runtime.egl`, from `S2` |
| Locator | `port-pins.json` sha256 `278219f4b364ae53d4942c2020cf69dd100cad376c5a320b0e4a1c88633dbb69` as predicted |

Navigation lane charged through P3: 808.744 + 29.042 = 837.785 CPU-s of 14,400. S2's worst case is 4,435 CPU-s, so spend
through S2 stays under the 5,643.168 CPU-s ceiling for S3. This is an import check only: no checkpoint was opened and
no capability result exists. S2 (development evaluation) still needs its own manifest, review and owner GO.
