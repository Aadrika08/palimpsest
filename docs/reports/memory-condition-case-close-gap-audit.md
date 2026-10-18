# Memory condition/case close: verified source gaps

Read-only audit of the clean memory worktree, branch
research/memory-cell-qualification-amendment-02 at2514c47. The puck branch does
not contain this implementation. No model, raw SNP, catalog or retained-study
payload was opened; no memory amendment/owner/replay command ran.

## Frozen-order conflict

The [analysis](https://github.com/Aadrika08/palimpsest/blob/2514c47/scripts/memory_family_analysis_v3.py#L122-L123)
rotates the nine canonical conditions left by family row. Canonical own is first,
oracle last. The independently derived [static audit](memory-condition-case-close-gap-audit.json)
confirms oracle comes before own in42/48 family rows, covering126/144 cases.
This is a schedule fact, not a study result.

[Oracle admission](https://github.com/Aadrika08/palimpsest/blob/2514c47/scripts/memory_family_oracle_admission_v4.py#L927-L938)
requires a durable prior-own receipt bound to the exact case/source, and
[_condition_mapping](https://github.com/Aadrika08/palimpsest/blob/2514c47/scripts/memory_family_oracle_admission_v4.py#L545-L547)
refuses without it. The [frozen compact plan](https://github.com/Aadrika08/palimpsest/blob/2514c47/docs/plans/memory-family-compact-evidence-v4.md#L299-L315)
requires sealing/pruning each condition before advancing to the next owner.
Its scientific evaluator also requires an isolated non-oracle own continuation
as donor. These requirements cannot all be met by simply connecting the existing
APIs for the complete balanced schedule.

Resolve this prospectively before all-nine/case-close execution. Do not silently
reorder conditions, add donor owners, invent a prior-own receipt, defer oracle
close while retaining an extra raw owner, or replace the donor proof with a weaker
claim. A proposed derivation/ordering amendment must preserve the scientific
estimand or explicitly describe/review its change. No amendment is authorized by
this audit.

## Missing implementation

The real pinned-model consumer
[replay_compact_cell](https://github.com/Aadrika08/palimpsest/blob/2514c47/scripts/memory_family_cell_replay_v4.py#L157-L210)
returns in-memory data. It does not publish a durable receipt or load/authenticate
model/SNP paths on the caller's behalf. Source sealing does not invoke this
consumer. No durable condition seal or case close currently exists.

The next coherent independent source slice is a durable single-condition seal:
consume an immutable registration/terminal-export descriptor, hold the canonical
source/SNP/model/runtime/source identities across the entire operation, recompute
raw proof, convert and reread, call the production cell consumer internally, apply
staged pair admission, and publish commit last with quarantine on uncertain
publication. Retain raw evidence until the reviewed pruning route applies.
A returned retained-source dictionary does not preserve the reader's already
closed custody contexts. Caller callbacks or supplied replay-passed dictionaries
cannot replace the internal replay call.

Persist replay/real-qualification binding inside prospectively versioned existing
receipts. Frozen accounting permits41 files per condition, no additional replay.json;
it permits three case files and454 total entries per case. Do not add an unbudgeted
permanent file. Meaningful authored tests cover derivation/custody, replay failure,
forged/missing qualification, wrong source/condition/run, history/selector drift,
late mutation, quotas, commit faults, immutable retries and quarantine. Orchestration
fixtures must remain labelled and cannot establish full-model qualification.

After resolving the oracle/order contract, reuse the seal for all nine conditions
and implement case close: exact registered order, ten distinct runs, sole shared
SNP, every receipt and quota, no raw residue, commit-last no-replace publication
and durable parent fsync. A trusted real qualification descriptor still requires
approved amendment02, one admitted execution and independent successful close.
There is no actual passing qualification receipt to synthesize or reuse.

This audit changes no frozen study protocol, experiment allocation or release
status. All seven simulation gates remain open.
