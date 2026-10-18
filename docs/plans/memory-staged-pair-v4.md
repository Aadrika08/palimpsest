# Memory staged compact-pair admission

This continues the approved compact-v4 producer sequence after source sealing.
The next bounded unit is read-only admission inside `.pending/<case>` before
condition/case publication. It does not close a condition or case, prune raw
files, run a recurrent cell, allocate owners, or open native/model/held-out assets.

`admit_staged_compact_pair` takes the existing pair arguments plus an immutable
canonical source commit descriptor. Source/condition conversion descriptors name
their final portable `cases/<case>/...` paths. A private, explicitly scoped root
resolver maps only this case to `.pending/<case>` while opening files. Returned
receipts keep canonical portable paths; no `.pending/cases` alias or file copy is
created. Histories and independent raw receipts retain their existing root paths.

Require the exact source commit schema, protocol, case/run, conversion descriptor
and false claims through a held descriptor. Reject quarantine, a temporary
source marker, a missing marker, another case, symlinks/aliases and mixed staging
and final inputs. Exhaust the existing nine-condition pair proof without
weakening its full read-only directory/file fingerprints. The existing public
final-bundle entry point and output schema remain unchanged.

Tests use temporary synthetic bundles and SNPs only: all nine conditions, natural
failure, canonical output paths, final reader refusal of staged inputs, marker
identity/type/byte changes, source/ancestor drift, staging/final alias rejection,
and mutation-free admission. Reseal only this prospective branch's behavior pins;
historical protocol bytes and receipts stay on their original branches.

Ruling: full condition/case close follows staged admission and recurrent-cell/
pruning gates. Retaining simultaneous real source and condition raw trees would
violate the one-raw-run allocation, so this unit cannot authorize collection.
No new permanent file or byte allowance is introduced. All qualification claims
remain false; CI and the physical rover stay excluded.

Progress: design recorded; RED and GREEN results follow in the evidence report.
