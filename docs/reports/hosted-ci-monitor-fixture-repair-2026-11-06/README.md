# Authored monitor fixture repair

Hosted [run 42079043646](https://github.com/Aadrika08/palimpsest/actions/runs/42079043646)
at `8cbeff2` passed the main source pass (6,516), process-isolated pass (7) and tmpfs
pass (57), with 318 historical skips. Five authored amendment fixtures failed
during preparation, before their historical auditor. The original console
truncated the parent JSON, so its **exact hosted error remains unknown**.

A controlled local authored parent reproduced a concrete mechanism: simulated
8 GiB admission followed by a 3 GiB supervisor sample fails the unchanged 4 GiB
monitor floor before launching its worker. This proves that mechanism, not the
historical hosted free-byte value or cause. Original production/archive hashes
remained unchanged. The [diagnosis](diagnosis.md), [parent result](authored-parent-probe.json)
and [decoded diagnostic](authored-parent-diagnostic.log) preserve that distinction.

The fixture correction extends its existing explicit synthetic capacity to the
real supervisor call inside the authenticated authored clone. It restores the
sampler in finally and preserves production thresholds, supervisor behavior,
RSS/FD/output/process checks and original archive bytes. A new regression proves
real low-capacity refusal and restoration after success, exception and foreign
root rejection. Added bounded failure diagnostics expose future parent errors.

All 8 focused checks passed in 55.39 seconds. The [independent review](independent-review.md)
approved this two-file test/workflow repair without rerunning tests. Hosted
preflight includes the new integration-file node. No full local suite or fresh
hosted success is claimed by this packet; no merge has occurred.

[Manifest](manifest.json) binds seven exact copied records. Original logs,
authored source trees and the initial syntax-error probe remain under ignored
runs paths. No actual research, model/native qualification, protected read,
evidence deletion, pruning or production-capacity claim follows from this work.
