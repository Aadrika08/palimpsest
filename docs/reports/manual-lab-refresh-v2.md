# Actual manual browser refresh v2: retained failure

7 October 2026. The corrected selector selected exactly the intended existing
workflow once. The UI build passed, and the actual browser ran against the local
server. The approved single allocation failed after 101.130 seconds and was not
retried. Manual workflow, sequential branch/comparison/export and clean owner
qualification remain open.

The source run `014130c7ea654d5dab1ba6a262696036` reached its paused snapshot.
The first branch `a003ec57c55246b486c1d197f24930bc` received HTTP 202 but failed
recording admission. Its actual close receipt records a `StorageLimitError`:
8,354,907 existing bytes + 121,470,976 reserved bytes + 10,485,760 headroom =
140,311,643 bytes, exceeding the configured 128 MiB by 6,093,915 bytes. The
600-tick recording reservation is made by `worker.py` before branch recording.
The UI correctly disables Step in failed state; the unchanged test timed out after
90 seconds waiting for it. The second branch, comparison and SVG export were not
reached. This was not another selector failure or evidence of a Step-button defect.

Shutdown completed. The worker separately killed one observed surviving Python
`multiprocessing.resource_tracker` child: PID 1115879, start ticks 8191409, group
1115591, parent server PID 1115704. Its persistence mechanism remains unproven.
This required kill independently fails the strict cleanup gate. The parent
observed no live survivors and released writer ownership before returning 1;
these are retained observations from the invocation namespace, not later PID probes.
The finally-close attachment returned HTTP 200 with status `failed`, preserving
the runtime failure. No desktop/mobile acceptance screenshots were reached.

The [execution](manual-lab-refresh-v2-evidence/execution.json) and original
publication receipt remain failed, with empty qualification claims. A checked
[fresh archive](manual-lab-refresh-v2-evidence/fresh-records.zip) contains all 41
fresh phase, built-UI and test-result files, including original recordings/SNPs,
server logs, Playwright trace, failure screenshot and owner-close attachment.
ZIP bytes: 5,586,196; SHA256
`05b78f76db7d08c0e836f6b08df4fc1ec48a077c318e822f9c3b0f2b550dc8dc`.
The [index](manual-lab-refresh-v2-evidence/publication-index.json) binds every
member to its unchanged original hash. Packaging was a post-failure byte-preserving
handoff, not a restarted deadline, browser run or scientific close. Combined roots
used 24,414,764 bytes after packaging, below the unchanged 1 GiB ceiling.

Three focused software tests passed before admission, including real filesystem
publication refusal, TERM/deadline failure handling and the worker exception
handler. These do not replace the actual failed browser outcome. Registration
binds 206 source/runtime/dependency pins; original v1/v2 evidence and consumed
markers remain unchanged.

The next proposal must first test reservation arithmetic and resource-tracker
lifetime using small software fixtures. A larger managed-storage allocation within
the same 1 GiB aggregate needs an explicit new registration; source/recorder
admission and failure predicates stay intact. Resolve tracker shutdown before
freezing a separately approved browser phase. No native, UI, export or human gate
was qualified by this failure.
