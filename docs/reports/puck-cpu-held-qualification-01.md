# CPU held qualification 01: consumed failure, acceptance audit FAIL

**The separately frozen actual qualification ran once and failed.** Its allocation
is consumed. The frozen acceptance auditor also exited 1/FAIL because the external
parent exit was nonzero. This is not a passing failure-preservation or staged-byte
audit. No retry is authorized and no attempt 02 has been created. All seven release
gates remain open; no successful four-import, native, operator, renderer, model,
episode, collection, study or release qualification is claimed.

The [fresh preflight](puck-cpu-held-qualification-01/resource-preflight-01.json)
at 2026-10-15T13:36:52.312180+00:00 admitted MemAvailable 3,683,385,344 B,
above the unchanged 2 GiB qualification floor, with project free 99,297,153,024 B
and tmpfs free 3,684,331,520 B. It checked 41 source/input/preparation pins,
four control/interpreter pins, two preparation-audit pins, matching staged-root
identities and absent qualification paths. The parent's own
[admission receipt](puck-cpu-held-qualification-01/raw/resource-admission.json)
records MemAvailable 3,661,852,672 B. Admission permitted one invocation; it did
not promise success.

The [reviewed configuration](puck-cpu-held-qualification-01/controls/puck-cpu-held-qualification-01.json)
is 8,065 B, SHA256 `3de376aef0bfec46aa9a8042706c40954ea0a5cc4425d51ad4f09525bcf930fb`,
with 24 sources, 16 input roles and the real successful preparation-result pin.
The [final freeze](puck-cpu-held-qualification-01/controls/puck-cpu-held-qualification-01-freeze.json)
retains the independent one-invocation review and original preparation acceptance.
The unchanged auditor is SHA256
`19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9`;
the observer and other source controls remain frozen.

| Actual terminal | Retained outcome |
| --- | --- |
| [External parent transport](puck-cpu-held-qualification-01/external/puck-cpu-held-qualification-01-external-cli-transport.json) | Exit 1, no timeout, 35.648024933995 s; root terminal `f36da7`. |
| [Parent result](puck-cpu-held-qualification-01/raw/result.json) | FAIL in 35.534725778969 s; held-four-import observation false; descriptors 5 → 5, no children/non-main threads. |
| [Worker stderr](puck-cpu-held-qualification-01/raw/logs/stderr.log) | 1,650 B traceback ending in `ModuleNotFoundError: No module named 'torch._C'`; worker stdout is 0 B. |
| [Frozen acceptance audit](puck-cpu-held-qualification-01/audit/palimpsest-puck-cpu-held-qualification-01-audit-01.json) | FAIL: `Normal external transport exit required`. |
| [External auditor transport](puck-cpu-held-qualification-01/audit/palimpsest-puck-cpu-held-qualification-01-audit-01.external-cli.json) | Exit 1 in 0.064102378965 s; published/stdout bytes identical, stderr 0 B; root terminal `58cf49`. |

The worker reached Torch initialization through the authenticated import path.
The traceback identifies `torch/__init__.py:427`, `from torch._C import *`, and
ends with the missing-module exception above. These terminal records establish
the visible failure, not its underlying cause. Static diagnosis is separate;
this report does not infer a missing file, an incorrect descriptor or a native
loader defect from the exception alone. No successful worker completion receipt
was emitted.

[Supervision](puck-cpu-held-qualification-01/raw/supervision.json) records worker
return 1, no matching survivors, three tracked descendant identities and sampled
peak RSS 284,078,080 B. Parent closure reports no remaining children or non-main
threads and descriptors 5 → 5. Those operational cleanup receipts do not convert
the failed import into accepted qualification. Process/RSS enforcement remains
sampled evidence, without a hard timing or hostile-code containment claim.

The parent result is 618 B, SHA256
`224cb9bdb18228f6e8da7a47e7455cd604a6e756df5fd017294b9221f26d9299`;
the external transport SHA256 is
`1d73292daf60bad403faf1166b2af4ba2c3660eb2851c917fb351f1288729746`.
The acceptance-audit FAIL is 617 B, SHA256
`0d0277ec73fdbd1658ff0448d715732843ac59f68d02c7bdb8835b3aaa484a0e`.
It rejects the nonzero external exit before a post-qualification staged census.
It therefore supplies no post-failure staged-byte acceptance, independent failure
preservation PASS, or successful audit closure claim. The
[earlier preparation PASS](puck-cpu-held-preparation-01.md) remains a dated accepted
data-preparation observation; it is not continuous post-failure custody or a
qualification result.

The [machine report](puck-cpu-held-qualification-01.json) and
[evidence index](puck-cpu-held-qualification-01/evidence-index.json) preserve all
10 regular run files / 4,272,240 B, both external transports and their streams,
fresh preflight, exact configuration/freeze and unchanged auditor/observer source.
All 22 copied originals are byte-identical, with original paths, sizes and SHA256
values indexed, including zero-byte streams. `.gitattributes` disables text
conversion. Empty raw `outer` and `payload` directories and the absent
`baseline-after.json` are declared in the index; no missing terminal or console
is reconstructed. The capsule contains 25 files / 4,362,123 B, below 20 MiB.
Its index excludes itself and records 24 entries / 4,355,767 B, SHA256
`ed80850b0e208dd41114eea7948edf30d5f201e77ae584002472d25334f58c4d`.
The [observation ledger](puck-cpu-held-qualification-01/observation-ledger.json)
distinguishes raw transport records from historical source-test observations.
The prior 55 checks were not rerun for this report.

This publication task inspected only completed receipt/control/source files. It
did not read or recount installed/staged payloads, import numerical packages,
rerun the auditor, alter controls or consume another allocation. Artifact-copy
verification is separate from runtime acceptance. Preserve this failure and its
frozen controls while the bounded static diagnosis proceeds; any future change
needs its own reviewed scope and explicit allocation decision. Scientific,
catalog, navigation and release decisions remain unchanged.
