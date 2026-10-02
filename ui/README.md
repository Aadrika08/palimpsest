# Interactive lab UI

Node 24.21.0 is pinned in `.node-version`. Dependencies use exact versions and `package-lock.json`.

```sh
mise exec node@24.21.0 -- npm ci
mise exec node@24.21.0 -- npm run build
```

The local Python lab serves `dist/` and `/api/v1` on the same origin. Rebuild the UI after changes and use that lab URL for interactive workflows. `npm run dev` serves the layout separately; the API intentionally rejects requests from a different origin/port. No external fonts or runtime services are used.

For an isolated verification server, run from the repository root after preparing the Python simulation environment:

```sh
PYTHONPATH=src MUJOCO_GL=egl .venv/bin/python ui/tests/serve_lab.py
```

This serves port 8766 and writes runs/exports under ignored `ui/.lab-test-runs/` and `ui/.lab-test-exports/`, separate from Playwright cleanup. It downloads no assets.

Browser verification operates against the actual running lab with a manual CPU controller and real simulation; it never substitutes mock samples. It creates recorded runs and generated exports under the server's configured output root.

```sh
PALIMPSEST_LAB_URL=http://127.0.0.1:8766 npm run test:browser
```

Chromium defaults to `/usr/bin/chromium`; set `PALIMPSEST_BROWSER` for another local Chromium binary. The workflow checks applied manual blur clearing, page reload recovery, pause/step, live obstacle relocation with exactly one applied receipt, validated goal movement, actual black pixels after an eye mask, snapshot, two sequential branches with a declared edit on the second branch, provenance and geometry comparison, recorded playback, SVG download, responsive layout and browser errors. A separate replay workflow checks action/policy verification reports, transport pause, real WebSocket disconnect, status-only reload recovery, explicit resume, stop, disabled live edits and an authenticated bundle whose replay report and member checksums are verified. Screenshots and traces go to ignored `test-results/`.

UI geometry is actual worker/recorded data. The live world depicts the current boundary; inputs/actions explicitly identify the preceding transition that used them. Comparison uses the left run's geometry at its last recorded transition per episode and labels this limitation. Playback invokes neither inference nor physics; action and policy replay are distinct supervised server operations. World edits can be previewed while paused or running and are validated again at the application boundary. Snapshots require a paused boundary. Queued commands are displayed as queued until authoritative receipts report application or rejection. Session credentials stay in memory and authenticated headers/first WebSocket frame; downloads never carry credentials in URLs.
