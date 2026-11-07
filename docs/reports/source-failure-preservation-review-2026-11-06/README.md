# Source failure-preservation software evidence

The canonical prepared source bootstrap now retains failed snapshot/recording
write bytes through an opt-in `preserve_failed` mode. Snapshot serialization,
recorder quotas, exclusive creation and successful publication stay unchanged.
Legacy callers keep their existing defaults; canonical Engine creation selects
the recorder option. The future source owner must explicitly select it for SNP
saving. Retained pending bytes remain chargeable and require separate admission.

The bounded change passed independent production review and a scoped test fix
review: **SPEC PASS / QUALITY APPROVED**, with no residual findings. The first
review requested replacing a success-patched legacy asset boundary in one test.
The active test instead requires a dedicated sentinel through the old writer
signature before acquisition; it proves keyword omission, not legacy asset
verification. Original tests, failures and review remain recorded historically.

| Evidence | Result |
| --- | --- |
| Corrected RED before production changes | 42 failed, 21 passed, 0.70 s |
| Initial GREEN | 63 passed, 0.65 s |
| Covering bootstrap/recorder/background units | 119 passed, 3.37 s |
| Changed sentinel node after review | 1 passed, 0.19 s |
| Final dedicated file after review | 63 passed, 0.64 s |

These scopes overlap and must not be added. The unchanged covering suite was
not rerun after the test-only correction. The implementation report gives the
clean environment, interpreter and retained fixture paths. Disk failures are
injected into real writers; controlled native/ML boundaries are confined to
authored bootstrap fixtures. No actual source/model/native experiment ran.

[manifest.json](manifest.json) binds four changed source/test files and thirteen
byte-exact copied text artifacts. Raw logs and reports are preserved verbatim,
including incidental whitespace; they are exempt from editorial whitespace
normalization. The README and changed source/test files have a separate scoped
whitespace check. Retained external test fixtures are not a portable runtime.

This is a preservation prerequisite, not the complete source vertical path.
Atomic capacity reservation, source production, nested teardown improvements,
continuous source/model custody, raw auditing/conversion/replay integration,
accepted Q/L/F/R, accounting, namespace coverage and exact execution approval
remain open. Unit runtimes are not measured experiment costs. No research CPU
debit, provider adoption, paid compute, CI run, publication or deletion authority
follows. Raw deletion stays disabled; the full project remains incomplete.
