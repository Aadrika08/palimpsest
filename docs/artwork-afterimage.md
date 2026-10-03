# Afterimage: bounded offline model portrait

This implements one M9 Afterimage mode from PRD §20. The artifact is labelled **“Authored model portrait — offline inference / recorded playback; not fly perception or biological activity.”** It uses the separately trained fixed male model as an authored response mechanism. It does not establish biological perception, causal memory effects, model generalization, or an exhibition involving a real visitor. Other artwork modes are outside this slice.

## Explicit input and rights statement

Supply one JSON manifest beside one pre-sized `.npy` file. No video decoder, resize, crop, camera capture, network access or automatic stimulus selection is provided. NPY version 1 or 2 must contain exactly a C-order `uint8` array shaped `T × 128 × 128 × 3`, with 1–600 frames and no trailing payload, object dtype or pickle. Header length is capped at 4 KiB; the complete NPY at 32 MiB; manifest at 1 MiB. Filenames are local basenames, and symlink paths are rejected.

```json
{
  "schema_version": 1,
  "title": "Authored colour sequence",
  "creator": "Operator name",
  "frame_file": "frames.npy",
  "frame_file_sha256": "REPLACE_WITH_SHA256_OF_EXACT_NPY_FILE",
  "source_times_seconds": [0.0, 0.04, 0.12],
  "rights": {
    "basis": "self_created",
    "statement": "I created these abstract frames and authorize local processing and retention.",
    "attribution": "Operator name",
    "authorized_processing_and_retention": true,
    "subject_consent": "no_identifiable_people"
  }
}
```

Every frame requires a finite, nonnegative, strictly increasing source timestamp (at most `1e12` seconds); sequence span is at most 120 seconds. These are operator-declared source times, not camera-verified acquisition times. Rights basis must be `self_created`, `permission`, `licensed` or `public_domain`. The subject statement must be `no_identifiable_people` or `permission_confirmed`. All text fields are bounded to 1,024 characters. The declaration is the operator's statement, **not independently verified consent, ownership or public exhibition permission**. The tool cannot detect people or validate licenses; personal imagery must be supplied only with appropriate authorization. Records retain the complete RGB frames, so the input statement explicitly covers processing **and retention**. SVG exports omit photographs but retain attribution, rights statements, hashes and responses; these metadata may also be personal information.

## One invocation per frame

The operator chooses exactly one fixed `male-original` or `male-control` model, using the existing hash-pinned asset manifest and `male-reduced-v1/` directory. CPU only, inference seed 0. The loader initializes its wrapper, then the recording sequence resets once at its start and carries hidden state through all frames. Exactly one `MalePolicy.act` is called per input frame; there is no per-frame reset, interpolation, dropped frame, fabricated neural population, policy feedback or simulated environment.

The supplied RGB frame is copied identically into both declared camera inputs. Contact and contact angle are fixed at 0; relative bearing is fixed at `[1, 0]`. This duplicated-image and fixed-sensor mapping is an explicit authored artificial interface, **not biological stereo vision or sensor mapping**. The existing wrapper's learned 388-feature encoder and actual 136-element encoded input / two-element raw readout are used unchanged.

For frame index `i`, the record contains external `source_timestamp_seconds`, `model_time_seconds = (i + 1) × 0.02`, and separately measured `inference_wall_seconds`. The first is declared source time, the second a fixed model index, the third offline wall latency. None is represented as physical motion or a live playback rate. Slow CPU inference does not stretch or fabricate the model step. Recorded action units retain the upstream `3 × tanh(raw[0])` velocity and `π × tanh(raw[1])` heading scaling.

The non-physics RunWriter schema contains exactly both effective RGB inputs, fixed float32 sensors, float32 encoded/raw/action outputs, int64 frame index and float64 source/model/wall times, with one episode numbered 0. No dummy pose, reward, world or retina data are added. This has its own bounded validator on top of `records.iter_ticks`; it does not call the simulator-specific artifact reader. The recording manifest retains source NPY/manifest/frame hashes, complete declared input provenance, model/checkpoint/protocol/topology/ordered-ID identity and the relevant implementation-file hashes. Inputs, implementation files and pinned assets are revalidated before terminal publication. Failures remain non-completed recordings and cannot render.

## Fixed response-to-line mapping

`response-plane-v1` maps each recorded action directly:

```text
x = 360 × action[0] / 3
y = −360 × action[1] / π
```

The axes stay fixed at ±360. The SVG joins every point chronologically and marks the sequence start in red. Coincident and null responses remain in the point list; no autoscale, smoothing, jitter or integrated virtual motion is introduced. A one-frame or wholly coincident sequence remains visible through its start marker. This is a response-plane portrait, not a physical route. The full precision frame → response → point mapping, source/model/time identities and exact mapping constants are retained in SVG metadata; displayed point coordinates use nine significant digits. Accessible title and description identify the artifact and its limitations. No scripts, external references or embedded photos are emitted.

## Commands and bounds

Global `--repo` / `--assets` flags precede the command. The record output basename must be a fresh canonical hexadecimal UUID; omitting `--output` generates one under `REPO/runs/afterimage/`. The model assets must remain outside managed output roots.

```sh
PYTHONPATH=src .venv/bin/python -m palimpsest --assets /path/to/assets/flynn afterimage record /path/to/stimulus.json --controller male-original --output /path/to/runs/0123456789abcdef0123456789abcdef
PYTHONPATH=src .venv/bin/python -m palimpsest afterimage render /path/to/runs/0123456789abcdef0123456789abcdef --output /path/to/exports/portrait.svg
```

Record uses the existing per-user `StorageBudget` writer lease and `bounded_process` child with a fixed 120-second wall timeout including loading, process-group TERM/KILL cleanup, one CPU thread environment and capped stdout/stderr of at most 1 MiB each. The parent preflights the full 96 MiB recording allowance plus `2 × log cap + 8 MiB` concurrent headroom; writer/chunk checks enforce the 96 MiB recording cap. This remains below the 128 MiB per-run envelope including bounded logs/supervisor metadata. Existing aggregate byte, free-space and run-count flags still apply. No child reacquires the parent writer lease. Incomplete recordings and supervisor/log evidence remain for diagnosis; there is no automatic retry.

Rendering is a separate operation and does not import Torch or MuJoCo. Actual-inference records also require a completed exit-0, 120-second supervisor receipt; synthetic fixtures remain visibly labelled and do not claim that runtime gate. It only accepts a completed, validated Afterimage record of at most 600 rows / 96 MiB. It checks chunk hashes, exact dtypes/shapes, source-frame hashes, both camera channels, declared sensors, indices/times, finite diagnostics and action scaling. It exhausts the existing validated iterator before publication. SVG output is capped at 4 MiB, uses exclusive creation and existing aggregate/free-space/export-count admission, and must be outside the source run / any `recording` directory. If publication fails, only that operation's partial SVG is removed; pre-existing files are preserved.

## Verification and actual mechanism evidence

The focused `test_afterimage` suite uses clearly labelled **synthetic fixture verification**. It covers shape/dtype/layout/header-payload and input-budget rejection; rights, timestamp and hash rejection; exact source/response alignment; reset/carry behavior; coincident points and deterministic rendering; corrupted/interrupted recordings; final source/asset failure; exclusive output / partial cleanup; bounded CLI dispatch; and rendering in a fresh process with no Torch/MuJoCo import. These checks do not constitute actual trained-model portrait or visitor/exhibition validation.

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_afterimage -v
```

The [actual eight-frame mechanism gate and browser evidence](reports/m9-afterimage-validation.md) passed on frozen source `2ed2c10`. The verification script authored nonhuman geometric RGB frames, recorded the fixed `male-original` model and compared every encoded input, raw readout and action with a fresh CPU model carrying hidden state after one initial reset. All maximum absolute differences were 0.0 under `atol=rtol=1e-6`. Two fresh no-Torch/no-MuJoCo renders produced identical SVG bytes; a separate browser check and visual inspection passed. Source, input and pinned asset hashes remained unchanged, and all owned child processes were cleaned up.

The [retained preview](reports/m9-afterimage-preview.png) shows the actual small-extent response trace on fixed axes; no autoscaling or artistic expressiveness claim follows. This is one generated eight-frame fixture and one fixed model, not visitor input, biological perception, generalization or an exhibition-duration/independent-operator qualification. Future mechanism checks use `scripts/verify_afterimage.py` with a fresh output directory and the declared bounded runtime protocol; earlier evidence remains tied to its measured source and inputs.
