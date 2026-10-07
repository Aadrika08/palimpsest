# Software repair for the oversized memory campaign receipt

7 October 2026. The real v2 campaign remains failed in
[PR #90](https://github.com/Aadrika08/palimpsest/pull/90) and
[its retained report](memory-prerequisites-v2.md). This separate branch repairs
the publisher using synthetic software checks. No new registration, native owner,
retained-state decode/comparison, scientific readout or qualification ran.

The driver previously merged full independent owner audits into a receipt that
already contained complete attempt reports. Eight real memory maps and receipt
identities made its final envelope exceed the unchanged 1 MiB cap. Timestamps
could not persist; the independent auditor subsequently read the old checkpoint
and stopped. Raising the cap or synthesizing missing timestamps would not address
this duplication.

The fix is three production lines in `scripts/memory_prerequisites_v2.py`: after
driver analysis finishes, remove only each owner summary's redundant `audit`
payload. Keep identity/disposition/gate/error summaries, full attempts, raw paths,
cleanup, allocated/started inventories, comparisons and original-clock fields.
The independent auditor still recomputes all evidence and retains complete owner
audits in its own close. Mandatory gates, state contract, exclusions, failure
behavior, legacy helpers and storage limits are unchanged.

One realistic regression extends the existing eight-owner fixture with 727
synthetic source receipts and large nested memory maps. It exercises the real
driver and independent-auditor publication paths; trusted-native duration probing
and owner execution remain test doubles. It checks all eight owners, complete
attempt reports, full independent audits, unchanged driver receipt during audit,
persisted original-clock fields, bounded JSON envelopes and the driver's
non-authoritative status.

The new regression first failed with the exact envelope exception: 1 failed in
2.74 seconds. After the fix, it passed in 1.81 seconds, with synthetic driver and
independent-close envelopes of 533,498 and 555,774 bytes. The initial green
wrapper then failed in metadata postprocessing because its glob also followed
pytest's current symlink; this is explicitly disclosed in `green.json` and was
resolved by deduplicated byte observation, without changing the test or rerunning
it to hide the error. A subsequent normal focused bundle confirmed the regression
and related campaign/restore/storage paths: **152 passed in 37.11 seconds, exit 0**.
Source and prose whitespace checks passed. The full branch check flags original
trailing whitespace in the retained verbatim pytest failure log; that evidence
was preserved rather than reformatted. The full suite was not repeated for this
three-line change; the earlier 1,064-test summary belongs to the pre-campaign v2 implementation.

[Red/green/focused records](memory-campaign-receipt-size-evidence/focused.json)
and [independent static review](memory-campaign-receipt-size-evidence/review.json)
are retained. Review found no material issue in the code, regression or prospective
plan; its reviewer did not run tests. A synthetic passing close is not a passing
native campaign. Complete attempt reports still share the existing 1 MiB ceiling;
future growth exceeding it must stop publication rather than silently truncating
evidence or relaxing the cap.

The [next finite proposal](../plans/memory-prerequisites-v3.md) requests a new
180-second registration plus one 4,900-second fresh eight-cell invocation,
8 GiB aggregate, zero retries/corrective studies. It remains **unapproved and
unstarted**. All eight cells, the selected profile, a new south-prefix and existing
scientific gates are preserved. The current prerequisite gate, pilot, R2 and
held-out work remain open. No CI, merge or physical rover work followed.
