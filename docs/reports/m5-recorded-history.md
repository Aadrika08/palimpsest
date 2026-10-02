# M5 recorded development history

Eight fresh simulation acquisitions completed at frozen source
`1cb70a3df6619083e4abbc080566971b91a10a19`: four seeds (0–3) per local/paired
regime, 410 ticks each, 3,280 total ticks and 674,361,116 recording bytes.
Both four-episode histories have no gaps. Source identity stayed unchanged.
All eight terminal recordings/chunk hashes were validated, normal Engine cleanup
recorded `operator_closed`, no cleanup errors occurred, and stderr was empty.
The runtime slot was released; no retry or replacement run occurred.

| History | Local observed/changed | Paired observed/changed | Fitted rule | E bytes | U payload/envelope bytes |
|---|---:|---:|---|---:|---:|
| Local | 4/4 | 4/0 | cue_changed → local_cue | 7,610 | 108/590 |
| Paired | 4/0 | 4/4 | cue_changed → paired_cue | 7,610 | 109/591 |

The collector reconstructed E exclusively from recorded declared sensor packets,
recorded triggers and public bank associations. It called `fit(E)` only after
admission; regime, geometry, gold, test bank and acquisition metadata did not
enter fitting. Live M started unknown; live E/U remained empty during acquisition.
The privileged manual driver used actual pose and the fixed public schedule.
Checks establish no engine U guidance, not operator blindness or source
authenticity beyond local recording integrity. These are distinct seeded
simulation episodes, not IID biological samples. No held-out execution, embodied
transfer, closed-loop comparison or R2 completion is claimed.

[Compact report](m5-recorded-history.json) records per-run identities, content
hashes, cleanup and support. Full recordings and collector links remain required
for audit; the compact report does not replace them. The retained artifacts are
hash-pinned rather than signed authenticity evidence:

| Artifact | Repository-relative path | SHA256 |
|---|---|---|
| Batch report | runs/m5-acquisition-batch-20261002/batch-report.json | `561f502b12ffc0069c1b5ba64084dcc4bc453324c88e29fa8a2e48721daff4b7` |
| Batch plan | runs/m5-acquisition-batch-20261002/batch-plan.json | `c27f963407b0446c2a8cd78af46a687ac385cb0d5f61b6c5547caf95de30380c` |
| Local collector | runs/m5-acquisition-batch-20261002/local_cue-history.json | `016c5b5e9472b116d065fb922b32d64089db6e27839aec09d751238f8ce7ffc1` |
| Paired collector | runs/m5-acquisition-batch-20261002/paired_cue-history.json | `64628e37cc6e861194f810baa92926eba8f57260047cdd8ad320a4601023d213` |

Batch protocol SHA256:
`077c558062f9c55416ebe0e46ae8e05d3887e2cef8cc94b89cbd756f1fdebdde`.
Canonical source-identity SHA256:
`ae4ddc8ad65a0288ceb3aed2aa26ce2b45780e6c33b128e402628b8c9246421a`.
The [batch protocol](../plans/m5-acquisition-batch.md) preserves acquisition
access, bounds, identities and the executed command. The first one-episode pilot
was excluded from both new histories and previously produced abstention.
