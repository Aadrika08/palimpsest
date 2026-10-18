# CPU export preflight: all 35 remaining creation declarations reviewed

The bounded source sweep is complete: **32 source-supported creation rows and
three rows requiring correction**. No additional creation-phase conflict was
found among the 32. This is a source creation/attachment result; the installed
runtime and replacement profile remain unqualified. All seven release gates
stay open. The next product exit is still a real recorded/replayed/exported CPU
simulation episode.

The [complete 35-row map](puck-cpu-export-phase-preflight-v1/source-map.json)
retains each unchanged declaration, proposed creator/raw path where different,
exact source ranges, build/dispatch assumptions, visible lifecycle and limits.
The unchanged one-row candidate remains SHA256
`ddc770acca34f849b2234db155ea477438560e3e4a58685a2c11632c44e93648`.
No production source, profile or actual configuration was changed by this review.

## Results and the remaining question

The32 rows retain source support for native_create. They cover AOTI, CPU,
Dynamo and its four children, export and its constants child, six generated
function namespaces, functionalization, functorch, instruction counting, ITT,
JIT/tree views/tensor expressions, lazy and its TS backend, monitor, nativert,
ONNX, profiler, return types, verbose, cpp and cpp.nn. Conditional/generated
members stay subject to the existing runtime dispatch capture and checks.
The source map does not invent static dispatch rosters for those 32 rows.

Nontrivial source details remain explicit: Dynamo's autograd_compiler canonical
module name uses the raw compiled_autograd attribute; eval_frame gains more
bindings before the native root returns. AOTI's second initializer reopens its
child during that same native phase. JIT imports atexit eagerly before native
return; its installed print callback imports sys only when invoked. USE_ITT
controls ITT creation; generated templates and helpers determine some dispatch
members. These observations are not an exhaustive transitive-import trace or
proof that every future mutation is absent.

| Child requiring correction | Physical Python creator | Proposed dispatch count |
| --- | --- | --- |
| torch._C._distributed_autograd | torch.distributed.autograd | 11 |
| torch._C._distributed_c10d | torch.distributed | 69 for Linux/Gloo |
| torch._C._distributed_rpc | torch.distributed.rpc | 29 for TensorPipe |

All three are created by callbacks invoked after native root creation. C10d and
RPC publish their children before fresh nested Python imports, requiring the
explicit publication contract. Autograd's visible eager Python source has no
fresh import after publication; publication handling is a conservative proposal.
No replacement phase is admitted by this map.

The counts in the table are **proposals, not observed runtime rosters**.
The [branch-separated analysis](puck-cpu-export-phase-preflight-v1/notes/distributed-rosters/literal-rosters.json)
retains every proposed name and source branch. Installed Caffe2Targets metadata
positively declares distributed/Gloo/RPC/TensorPipe, but exported downstream
definitions do not establish the complete private torch_python build flags.
NCCL/MPI/XCCL/UCC/NVSHMEM alternatives remain unproved for exact roster selection.
Zero unresolved *creation-classification rows* does not resolve this roster gap.

## Finite next action

The [prospective three-module observation](../plans/puck-cpu-distributed-roster-observation-01-proposal.md)
is the one remaining group from this sweep. Reuse the ordinary fixed four-import
path to capture only bounded raw terminal dispatch metadata for the three
already-present children. Preserve disagreements for source attribution; do not
expand an allowlist, import a missing child separately or use held05 as a scout.
Terminal roster evidence cannot prove intermediate publication or creator-close
timing. Those remain separate source/held-runtime obligations.

The proposal has independent review but is not an executable configuration.
Implement and verify the smallest fixed projection, freeze exact new controls
and obtain independent review before one separately numbered actual observation.
After a passing observation/audit, review the complete explicit prospective
profile and exact parent/auditor transition before actual held05 freeze. Do not
reopen the 35-row sweep or add unrelated hardening.

## Evidence and verification

The [evidence index](puck-cpu-export-phase-preflight-v1/evidence-index.json)
retains **65 indexed artifacts / 1,792,892 B**, including one empty stderr file.
All 42 exact package-declared upstream files match their Git blob SHA1 and SHA256
pins at revision 0fabc3ba44823f257e70ce397d989c8de5e362c1. Seven selected installed
Python/build/header files match the accepted inventory. This is selected-file
verification, not a new full installed/staged-tree census or binary provenance.
The packet also preserves both source lanes, branch rosters, unchanged candidate,
the observation proposal and the exact existing dispatch-seal source.

One read-only CMake source retrieval timed out; its failure is recorded, the
other 36 verified files were retained, and only the missing read request was
repeated. No runtime experiment was retried. The initial artifact verifier rejected
valid empty conditional-branch lists on unconditional rows; its original source
is retained and the assertion now accepts the declared container types. The
corrected standalone check passes all 65 artifact fingerprints/original bytes,
42 Git blobs, seven selected-file pins, all 35 declarations/classification totals,
source ranges, false authority and the unchanged candidate:

```sh
PYTHONDONTWRITEBYTECODE=1 python docs/reports/puck-cpu-export-phase-preflight-v1/verify_map.py --originals
```

Root reviewed the 14-row core lane; an independent agent reviewed the 18-row
standard lane and the written prospective observation. Neither review found a
material issue within the declared source scope. Artifact checks do not prove
the analysis by themselves.

Qualifications01–04 remain failed and consumed. All six actual05 configuration,
freeze/output/report paths remain absent in the data-owning checkout. No vendor
import, operator, renderer, model, scene, protected catalog, episode or study ran.
Full repository tests and CI were not run for this source-only evidence change.
