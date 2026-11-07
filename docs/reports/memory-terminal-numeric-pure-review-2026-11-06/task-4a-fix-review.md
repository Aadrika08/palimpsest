# Task4a round1 scoped fix rereview

**Scoped spec: PASS. Scoped quality: APPROVED.** The single P2 finding from
`task-4a-review.md` is resolved. No material breakage introduced by this fix was
found. This is not overall Task4a acceptance or combined-suite GREEN.

Reviewed exact diff `4fd9cb8379dfc46934783eab7388287d6b8b29bb` →
`65b6789cff2f08f1e2b33875a41432145b05c1e2`: only the authorized codec and test
files changed,18 insertions/1 deletion. No unrelated reaudit was performed.

At `scripts/memory_family_terminal_numeric_vnext.py:321`, the common
`_recording` validator now compares the ordered ticks returned by the inherited
field-validating policy helper with `list(range(b,b+n))`. This closes the
reader's known tick2099 versus motor interval20..20 gap. Equality also preserves
the prior count obligation, rejects missing/extra/reordered policy calls, and
requires an empty list for zero rows. Existing `_events` validation already
requires exact integer ticks and matching episode_step, so boolean/numeric
equality does not weaken the new check. The common path covers all three APIs;
it adds no replay, proof field, cap, pin or authority claim.

The new test at `tests/test_memory_family_terminal_numeric_vnext.py:494`
reproduces the exact reviewed mutation after establishing a valid one-row
bundle and false reader authority/comparison flags. It rebinds the affected
descriptors/proof and matches `PURE policy interval differs`, ensuring it tests
the intended coherence check rather than earlier hash rejection. It explicitly
distinguishes this mutated proof from a genuinely replayed Task3a proof.

Read the actual three retained round1 logs and verified their hashes:

| Evidence | Observed result | SHA256 |
| --- | --- | --- |
| `task-4-evidence/round1/red.log` |1 failed,67 deselected,0.52s; `DID NOT RAISE ValueError` | `efb626808ce32ebdd891d62ea90c54b8f9b57351dc36d3c5c6521f06602c9f4d` |
| `task-4-evidence/round1/focused-green.log` |2 passed,66 deselected,0.72s | `6bcf820a66a210d5993f67121099de1b13d7563dcd78e0303f3a0e543001f3af` |
| `task-4-evidence/round1/final-green.log` |68 passed,31.39s; no reported warnings/skips | `e8b9944ab09b77dcccc50556269f8785dd50ed17250391023bf1d59e5dc4ec0a` |

These are retained implementer test results, not reviewer reruns. The report
records the approved sanitized environment and fresh basetemps. The own-file
final run includes the existing zero and positive prefix coverage, providing
regression evidence for the tightened common predicate. Diff whitespace check
also passed during this rereview. The profile JSON is unchanged at SHA256
`1592d4a5bcf74489b7895e8340119cfa78b6b35720ee8d9be367dc4cf21ed6f4`.

**Combined verification remains separately BLOCKED.** The prior combined result
is111 failed,235 passed,2 skipped,13 errors, with the known prior engine pin
drift. This review does not rerun, waive, repin or resolve that boundary. The
separate policy proposal review and root's acceptance decision remain open;
68 own-file passes do not imply combined GREEN or actual qualification.

Only this rereview report was written. No tests/imports/probes, implementation,
profile, legacy, pin, HEAD, qualification, CI, actual-data, dependency, cleanup
or agent action occurred. HEAD readback was
`65b6789cff2f08f1e2b33875a41432145b05c1e2`; the root-owned plan remained the only
tracked uncommitted change. Stopped after the scoped rereview.
