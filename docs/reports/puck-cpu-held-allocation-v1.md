# CPU held allocation: frozen controls, authored evidence, no actual admission

**Configuration and independent auditor are ready; the actual CPU allocation is
NOT ADMITTED.** At the [fresh resource preflight](puck-cpu-held-allocation-v1/preparation-01-resource-preflight.json),
2026-10-15T13:08:01.377406+00:00, MemAvailable was2,852,470,784B,
below the frozen preparation floor4,294,967,296B. Project/tmp free bytes were
99,317,600,256/4,988,243,968. All40 source/input pins matched and all actual
paths were absent. No actual parent or namespace was invoked, no allocation was
consumed, and no actual preparation, four-import qualification or outcome audit
has run. The installed CPU tree remains **UNSTAGED and UNQUALIFIED**.

The [prospective freeze](puck-cpu-held-allocation-v1/controls/puck-cpu-held-preparation-01-freeze.json)
binds source commit `01f7248f9a8e16fd54ef0a52a8b27eb5d6cf059c` and outer-control
freeze commit `7d368ebb91ee7e1d917190ae936e4cca12835618`. The corrected canonical
[preparation configuration](puck-cpu-held-allocation-v1/controls/puck-cpu-held-preparation-01.json)
is7,903B, SHA256 `38134e016eff974e06806f1ac74492dc51e0a5721d8cd13d1123a1fd950fe8a6`,
with24 source pins and16 input roles. The independent stdlib-only
[auditor](puck-cpu-held-allocation-v1/final-source/scripts/audit_puck_cpu_held_runtime.py)
is58,090B, SHA256 `19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9`.
The exact observer and parent pins are retained in the [machine report](puck-cpu-held-allocation-v1.json).
Independent review grants GO for **one actual PREPARE only after fresh resource
admission**; it supplies no actual runtime acceptance. Qualification JSON remains
unwritten until a real successful preparation result and independent audit exist.

Before invocation, metadata inspection found six accepted SITE files above the
old16MiB inherited file ceiling; `torch/lib/libtorch_cpu.so` is432,273,704B.
The [two retained authored failures](puck-cpu-held-allocation-v1/file-limit/red-01/runs/puck-cpu-held-preparation-01-external-cli.stderr)
separate [EFBIG at16MiB](puck-cpu-held-allocation-v1/file-limit/red-01/runs/puck-cpu-held-preparation-01-external-cli-transport.json)
from the [inability to raise the observer's inherited hard limit](puck-cpu-held-allocation-v1/file-limit/red-02/runs/puck-cpu-held-preparation-01-external-cli.stderr)
after correcting only the parent. Preparation and the outer inherited hard
ceiling now allow1GiB; qualification remains16MiB. External stream acceptance
remains16MiB per stream and parent output remains64MiB. A real original-Python
child writing17MiB passes after both corrections; its [zero-exit receipt](puck-cpu-held-allocation-v1/file-limit/green-01/runs/puck-cpu-held-preparation-01-external-cli-transport.json)
is retained while inert payload bytes are excluded. These controls reproduce
file-limit inheritance; they do not stage the actual package tree. The original
7,901B configuration, SHA256 `230a0e7955c01bcf0c56163d602ba0630be0f48d6dfc102c5400a52bae9773ee`,
is preserved [byte-for-byte from commit026ec3c](puck-cpu-held-allocation-v1/superseded-uninvoked-026ec3c/docs/plans/puck-cpu-held-preparation-01.json).
It was never invoked and was superseded prospectively, without consuming an attempt.

The [configuration-generation record](puck-cpu-held-allocation-v1/configuration-generation.json)
and root's separate data-only plan comparison (`fa8f8c`) agree on27,255 files,
1,318,494,346 content bytes, directory counts2,074/2/0/0 across SITE, `/usr`,
`/etc` and generated roots,71 distributions and two native-cache bindings.
No actual payload census or copy supports that metadata-only agreement; content
bytes are not RAM admission. The CPU finite optional-miss roster is exactly
`numpy._distributor_init_local` and `org`. Bounded review of the authenticated
407B NumPy source (SHA256 `20acb64c7c26bb9520063b556f06c3f47f80a7cb9a509a0f2766ed43825ab5da`)
supports its optional local-module probe. Actual held admission must prove both
absences; all other misses remain fatal. The historical GPU proposal stays unadmitted.

| Retained authored route | Observed outcome |
| --- | --- |
| [Auditor GREEN01 attempted](puck-cpu-held-allocation-v1/verification-logs/auditor-integration-green-01.pytest.log) | Both parent phases complete; qualification audit rejects `claims` versus `qualification_claims` schema mismatch. |
| [Auditor GREEN02](puck-cpu-held-allocation-v1/verification-logs/auditor-integration-green-02.pytest.log) | Both API audits pass; nonzero external exit and same-size staged-byte changes reject;1 pass in5.59s. |
| [Final combined authored route](puck-cpu-held-allocation-v1/fixtures/affected-green-01/authored-audit-test-observations.json) | Preparation1.329039411s; separate imports2.510672863s; both API audits PASS. |
| [Real auditor CLI](puck-cpu-held-allocation-v1/fixtures/affected-green-01/authored-prepare-audit-cli-transport.json) | Original isolated Python, observed exit0 in0.678721657s; published and stdout PASS bytes identical, stderr empty. |
| Final affected source checks |55 passed in7.91s; root-observed terminal `8a51d2`, session70669. |

The final fixture uses four tiny version-only NumPy/Torch/torchvision/MuJoCo
stand-ins and18 copied files/4,038,871B, including only eight original baseline
native leaves. Only its cloned parent lowers RAM floors to128MiB; production
floors remain4GiB/2GiB. Its enhanced export/cache rows are empty. Separate authored
nonempty producer-export, origin-policy and cache receipt cases check schema
compatibility and refusal of missing proof; actual predicted bindings remain
unqualified. The auditor verifies exact support-source receipts, all four file
plans and directories, tmpfs identities, transport, baseline hashes and closure
without importing parent validators or vendor packages. Both mount wrappers must
contain exactly their declared names on both census passes.

Final [parent preparation](puck-cpu-held-allocation-v1/fixtures/affected-green-01/runs/puck-cpu-held-preparation-01/result.json)
and [qualification](puck-cpu-held-allocation-v1/fixtures/affected-green-01/runs/puck-cpu-held-qualification-01/result.json)
close descriptors5→5 with no children or non-main threads. The auditor API closes
13→13; its real CLI closes4→4. Qualification records PID/PPID/PGID/SID2/1/2/2
and [three tracked descendants, normal exit, no survivors](puck-cpu-held-allocation-v1/fixtures/affected-green-01/runs/puck-cpu-held-qualification-01/supervision.json).
Preparation uses group supervision and retains no process-count peak. RSS/process
checks are sampled operational evidence. The auditor has a120s normal deadline,
130s kernel SIGALRM stop and512MiB address-space ceiling; a short authored timer
regression proves hard termination without entering failure publication.
[Owned fixture tmpfs cleanup](puck-cpu-held-allocation-v1/fixtures/affected-green-01/authored-stage-cleanup.json)
records the stage absent after verification.

The [source-verification ledger](puck-cpu-held-allocation-v1/source-verification.json)
distinguishes archived console files from tool-observed results; no final55-test
console log is invented. Earlier API audit results were held in memory: the old
auditor source and a separate failure JSON were not retained. The actual archived
GREEN01 traceback and parent receipts remain available; no missing audit receipt
is reconstructed. The [evidence index](puck-cpu-held-allocation-v1/evidence-index.json)
indexes399 files/4,828,702B and excludes itself. Including the index, the capsule
contains400 files/4,982,265B, below20MiB; its index SHA256 is
`2443cce0cce94a3abfdc8a1a2c2147332c897300d232e1d4232ffa97438687f5`.
All394 copied originals have path, size and SHA256 provenance; the two root-owned
records remain in place unchanged. `.gitattributes` preserves bytes and exempts
only required blank EOFs in fixture distribution METADATA from whitespace checks.
Authored inert `.pyc` data is preserved as `.bin` with original paths indexed.
No vendor payload, host ELF payload, cache artifact or protected catalog is archived.

Next obtain fresh resources meeting the unchanged preparation floor, recheck the
frozen controls/pins and absent paths, invoke preparation once, retain its external
outcome and independently audit it. Only then freeze and review qualification
using the actual preparation pin. A required cache, version, custody, cleanup or
normal-exit failure stops the lane and retains its allocation without implicit
retry. The real recorded/replayed/exported episode remains the next user-visible
milestone after actual held qualification and its episode/catalog contract.
All seven release gates and33 requirement/gate statuses, scientific/catalog/navigation
decisions and consumed histories remain unchanged; see the [allocation contract](../plans/puck-cpu-held-allocation-v1.md)
and [prior source checkpoint](puck-cpu-held-parent-v1.md).
