# Independent final review of the restore v2 candidate

7 October 2026. Fresh-context read-only reviewer `restore_v2_final_review` reviewed
`f539d4021b21464b6af77e92e129b26b4d7e9da4..ce5c18cfa957b5d4946aa17aabe917f22cc5cb45`,
the whole diff, proposal, report, committed evidence and executor ledger.

## Assessment

Ready for publication as a prospective software candidate. Critical, Important
and Minor findings: **none**. No plan deviation requires correction.

The reviewer confirmed raw SHA verification before mapping; matching 15-field
layouts backed by disjoint reversible eight-byte probes; copied-state masking of
exactly 120 duration bytes per side; derived checksums separate from raw hashes;
and exact comparison of remaining typed state. Explicit opt-in, legacy
`state_equal`, false native prerequisites and empty qualification claims remain.
All seven new cases were inspected, including synthetic SNP integration and
preservation of the original failed close.

Independently ran **14 selected synthetic tests: 14 passed in 2.33 s**. Inspected
the committed seven expected RED failures, 45 focused passes, and full-suite
960 passes / 24 skips / 39 warnings. Existing isolated synthetic physics tests
in the full suite are software validation. Checkout remained clean at `ce5c18c`.

Exact independently executed command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src:scripts /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python -m pytest -p no:cacheprovider -q tests/test_memory_restore_offline_readout.py::test_v2_candidate_excludes_only_durations_and_keeps_raw_integrity tests/test_memory_restore_offline_readout.py::test_v2_registered_candidate_reports_both_comparisons_without_promoting_gate tests/test_memory_restore_offline_readout.py::test_native_byte_attribution_proves_timer_bytes_without_hiding_other_state tests/test_memory_restore_offline_readout.py::test_native_decoder_omits_owned_views_of_unpopulated_arena_fields tests/test_memory_restore_diagnostic.py::test_compare_localizes_typed_components_without_mutating_or_normalizing_more tests/test_memory_restore_diagnostic.py::test_compare_preserves_native_bytes_and_extra_application_fields tests/test_memory_restore_diagnostic.py::test_comparison_never_hides_signed_zero_or_dtype_changes tests/test_memory_restore_diagnostic.py::test_offline_native_decode_exposes_changed_field_without_stepping
```

## Declined to judge and executor rulings

- Fresh native qualification and retained-pair re-scoring were excluded; no
  retained snapshots were decoded. Ruling: keep the prospective activation
  boundary and old failures unchanged. Cost: qualification remains unresolved.
- Arbitrary controllers consuming durations were not universally proved
  equivalent. Ruling: retain the declared observational-metadata assumption and
  require profile/controller scrutiny before activation. Cost if wrong: such a
  controller could require an exact duration contract instead.
- Broader seeds, trajectories, pilot, navigation, held-out, hardware and operator
  claims were excluded. Ruling: keep their separate gates open. Cost: this
  candidate proves none of those outcomes.
- The reviewer inspected the preservation record without repeating the complete
  ignored-evidence inventory audit. Ruling: retain the executor's actual current
  documentary rehash as the preservation evidence. Cost if wrong: independent
  review alone would not detect a mistaken inventory record.
- CI, network publication and full-suite repetition were excluded from review.
  Ruling: use the current full-suite evidence for unchanged code; verify account,
  remote head and PR metadata during publication; honor the user's CI exclusion.
  Cost: no CI or independent repeated full-suite assurance.
- Preserve this plan's ignored workspace and historical evidence instead of
  generic skill cleanup. Ruling: immutable evidence and review handoff take
  precedence. Cost: small retained disk footprint.

Executor severity assessment agrees: no corrections or deferred minors.
No second review or repeated full-suite run is needed for this documentary
record. Candidate equality supplies no qualification success.
