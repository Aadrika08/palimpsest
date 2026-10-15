# Memory directory census: source evidence

Source `adbbfdfa30d5a2c96fbb0777cbc0e6840f48094d` resolves the measured held-directory enumeration gap in the
authored memory path on Btrfs and tmpfs. The source-to-condition audit, conversion,
pair, seal and fresh-reader route now passes on both. This closes the filesystem
implementation gap; actual family qualification/admission, case closure, CPU
configuration and all seven simulation release gates remain unfinished.

[The evidence index](memory-directory-census-v1-source.json) pins all16 changed
source/test/profile files, preserved originals and two lossless diagnostics.
[The prior failed source result](memory-condition-seal-v1-source.md) remains
historical and unchanged. No protected full model or actual qualification/study ran.

## Measured mechanism and corrected observation

The [initial diagnostic](memory-directory-census-v1-evidence/diagnostic-initial-confounded.json)
reported agreement, but its lseek(SEEK_CUR) metadata probe refreshed directory
state. It is preserved as confounded evidence. The
[corrected diagnostic](memory-directory-census-v1-evidence/diagnostic-corrected.json)
uses fstat and fdinfo metadata without seeking except in one explicitly labelled
comparison arm. On Python3.11.15/kernel7.2.5-3-omarchy, the first held/old-description
duplicate listings on Btrfs omitted entries created afterward. Fresh openat('.')
and fresh pathname enumeration included them. The discrepancy repeated after a
second create; tmpfs agreed across methods. Device/inode/mode stayed unchanged.

[CPython3.11.15 source](https://github.com/python/cpython/blob/v3.11.15/Modules/posixmodule.c#L3890-L3995)
duplicates the supplied directory FD and rewinds after listing. Upstream
[Btrfs6.12 source](https://github.com/torvalds/linux/blob/v6.12/fs/btrfs/inode.c#L5478-L5509)
provides an explanatory per-open-directory limit/seek mechanism. This source
analogy does not verify the exact host kernel binary. The local measurements
justify opening a fresh description rather than trusting a repeated old listing.

## Implemented behavior and unchanged contract

[The shared helper](../../scripts/memory_directory_census_v1.py) opens '.' relative
to the held directory with directory/no-follow/close-on-exec flags. It bounds
scandir, checks held/fresh full directory metadata, uses supplied deadlines and
closes only its owned descriptor/iterator, retaining primary errors and cleanup
diagnostics. The caller still binds named edges. It does not seek, use proc paths,
change cwd, follow children or modify the caller's descriptor/cursor.

All producer and condition held-FD directory listings use this helper. Existing
exact namespace comparisons, named edges, held leaves, schema, row/chunk/file/byte
limits, marker-last publication and quarantine remain. Censuses cap at64 names;
supported namespaces top out at38 chunks. Normal deadlines are unchanged; bounded
cleanup does not restart a time budget or become impossible after normal expiry.
Filesystem syscalls and cleanup remain cooperatively controlled, not hard-WCET proof.

The separately named [base profile](../plans/memory-family-compact-evidence-v4-directory-census-v1-protocol.json)
changes only behavior-source identities and source-revision metadata. Tests compare
all other fields against the original protocol, preserving every scientific,
ordering, schema, storage and false-claim field. The
[condition extension](../plans/memory-condition-seal-v1-directory-census-v1-protocol.json)
selects that base and refreshed source pins while preserving prior contract fields.
Raw audit and replay admission derive the actual selected protocol path. There is
no caller or environment protocol override, global monkeypatch or hash cycle.

Original base/condition JSON files, original qualifier and amendment02 freeze,
empty trust anchor and old branch heads2514c47/a1cf849 remain intact. The current
prospective source cannot invoke the original frozen capsule; historical artifacts
are not relabelled. The [plan](../plans/memory-directory-census-v1.md) records the
source-only scope and finite exit.

## Verification

| Scope | Actual result |
| --- | --- |
| New profile selection before implementation | RED3 failed,0.13s |
| Census32, profile3 and admission53 | Root88 passed,0.25s |
| Six formerly failing Btrfs cases | 6 passed,14.55s |
| Full condition file on Btrfs | 33 passed,84.40s |
| Same condition file on tmpfs | 33 passed,47.93s |
| Eight affected legacy files | Root369 passed,27 warnings,114.57s |
| Independent source review | No concrete Critical/Important/Minor finding; reviewer ran no tests |

The eight files cover compact conversion/read, raw audit, pair admission, source
publication, retained-source reading, staged pairs, cell replay and replay custody.
Cell coverage uses the actual upstream numerical cell on tiny fixtures. Positive
condition orchestration substitutes private qualification/model/replay seams.
There is no full-suite or protected-full-model qualification claim. Historical
failures, the confounded probe and exact successful source results are retained.

## Next work under the full goal

The public route still refuses because trust pins are empty. Historical seed400
qualification cannot serve generated family-case seeds under exact snapshot/policy
provenance; a reviewed binding is still required. Memory amendment02 remains
uninvoked. Oracle/own ordering, pruning and complete case/family admission stay open.
Continue the complete resource-feasible CPU runtime proposal and the family proof
binding; actual stages require their exact prospective admission and outcome audit.
The lab, six artworks, human sessions and integrated reproducible delivery remain
required before the separate physical rover decision.
