# Bounded distributed publication profile/admission map

Read-only source review at `5408f55fd9cc704edea9bd3b73dfcb4914e82987`, source worktree `/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03`, branch `research/puck-cpu-distributed-publication-profile-v1`. No tests, target imports, census, actual configuration, allocation, Git/auth mutation or repository edits were performed. This note is the only written artifact.

## Decision: amend the prospective v5 contract, keep allocation05

Use one explicit reviewed prospective v5 source amendment that admits exactly **four original-preparation export replacements**: existing `_autograd` plus the three distributed children. Keep kind/version/allocation `(puck-cpu-held-runtime-allocation-v5, 5, 5)` and output `runs/puck-cpu-held-qualification-05`. Do not introduce v6 with allocation/output05; that would violate the existing closed identity relation. A genuine v6 would mean allocation06/output06 and is unnecessary while actual05 controls have never existed.

The old one-row candidate, proof, source commit and authored results remain immutable historical evidence. They need not remain accepted by newly amended current v5 source. State that change directly in the prospective decision; never relabel the old one-row authored PASS as proof for current four-row source. Preserve v1–v4 behavior and restrictions exactly. A path-existence read found no `runs/puck-cpu-held-qualification-05`; this is not a fresh runtime/resource admission or a complete control inventory. The accepted observation03 report independently records actual05 configuration/output absent.

No new runtime attachment, input role, variant selector, source-reader or protocol is needed. Existing candidate byte pins plus independently duplicated fixed replacement constants close the admitted semantics. The reviewed static source-proof packet binds observation03 selection. Subsequent actual05 frozen controls bind the selected candidate/proof/current source bytes. The held run must still prove actual creator closure and complete dispatch under the existing runtime mechanism.

## Exact candidate relation

Let H be the immutable candidate held by preparation01; A the existing one-row autograd candidate; C the new prospective distributed candidate.

1. A = H with exactly `_autograd` replaced by its existing 41-name publication row. Preserve A and its proof bytes.
2. C = A with exactly three distributed native-create rows replaced by the rows below.
3. The parent and independent auditor need only enforce the closed runtime relation C = H with **exactly all four** replacements at their original indices. They do not dynamically read A, observation03 or a proposal. The static proof separately proves both relations, including equality of the autograd row in A and C.

| Child | Exact Python producer | Raw attribute path | Phase | Complete delegate roster |
|---|---|---|---|---|
| `torch._C._autograd` | `torch.autograd` | `['torch','_C','_autograd']` | `module_exec_publish` | Existing unchanged 41-name constant |
| `torch._C._distributed_autograd` | `torch.distributed.autograd` | `['torch','_C','_distributed_autograd']` | `module_exec_publish` | Exact accepted observation03 sorted 11-name array |
| `torch._C._distributed_c10d` | `torch.distributed` | `['torch','_C','_distributed_c10d']` | `module_exec_publish` | Exact accepted observation03 sorted 69-name array |
| `torch._C._distributed_rpc` | `torch.distributed.rpc` | `['torch','_C','_distributed_rpc']` | `module_exec_publish` | Exact accepted observation03 sorted 29-name array |

Each new row has exactly `name, producer, phase, attributes, class_binding, delegate_attributes`, with `class_binding=None`; all delegate arrays are fixed literal sorted distinct names, not a caller-supplied allowlist. The old H row for every target must occur once and equal exactly `{name: target, producer: 'torch._C', phase: 'native_create', attributes: [suffix], class_binding: None}`. Require all four old targets uniquely, build a deep copy with those four replacements, and compare the entire candidate canonically. This rejects a one-row candidate, partial combinations, added row fields, target duplicates and any unrelated top-level/profile change.

The real profile has 38 exports. A has 35 `native_create`, one publication and two `module_exec` (`torch.classes`, `torch.ops`). C must have 32 `native_create`, four publications and the same two `module_exec`: 34 exports unchanged from H, or 35 unchanged from A. Preserve all module paths, namespaces, additional helper bytes, module_changes, native_origins, native_cache, static source fields and existing candidate-wide observation02 provenance. The four creator packages already have correct physical Python source mappings under root0 in A; no module-map change is needed.

## Minimal files / exact touch map

| File / current lines | Needed change or invariant |
|---|---|
| `scripts/qualify_puck_cpu_held_runtime.py:35–50` | Keep exact existing AUTOGRAD_EXPORT; add three fixed complete distributed replacement constants, preferably one fixed four-row tuple. Do not import the auditor or load a runtime proposal. |
| Parent `219–233` | Extend `validate_publication_candidate(H,C)` from one exact old row/replacement to exactly four. Full candidate equality remains the guard. No configurable changed rows. |
| Parent `172–216,236–266` | Schema, identity/output, 16 roles, preparation acceptance and exact four-source delta remain unchanged. Only candidate input may differ; all other 15 pin dictionaries stay exact; candidate path and digest must both differ from H. Distinct canonical path plus semantic equality is already sufficient; an additional runtime hardcoded candidate-path constraint provides no unbound semantic check. The concrete freeze selects the exact path/hash. |
| Parent `565–581,638–667` | Existing v5 code already holds H, checks retained `control/candidate.json`, reconstructs historical dependencies, attaches C and permits only import_profile substitution. Keep this mechanism. No changes needed unless a bounded authored regression demonstrates a defect. All prepared roots/files/distributions/stage identities remain original. |
| Parent `369–389` | Existing worker proof derives **all** publication rows from the candidate and compares exact sorted proof. Already works for four; add four-row regression coverage, not a new receipt version. |
| `scripts/audit_puck_cpu_held_runtime.py:29–45,237–247` | Independently duplicate the same fixed four rows and enforce the same full candidate relation; never import parent constants for acceptance. |
| Held auditor `210–269,595–623` | Keep 24-source/16-role closure, old-preparation handling, exact four-source delta, current-vs-historical dependency projection and original data binding unchanged. |
| Held auditor `453–467,638–640` | Existing publication proof and historical/current candidate/dependency digests scale to four rows. Keep exact full lists; test missing/extra/rebound proof per child. |
| `docs/plans/puck-cpu-distributed-publication-profile-v1.json` | New C only; never overwrite A or H. Candidate-wide observation02 hashes remain unchanged. |
| `docs/plans/puck-cpu-distributed-publication-profile-v1/source-proof.json` | New static decision/source-attribution proof described below. No actual05 control or invocation. |
| Existing one-row JSON/proof and actual03 archive | Read/pin only, no edits. Preserve all previous failure packets and actual observations. |

No planned changes to `puck_dependency_bindings.py`, `puck_dependency_imports.py`, bootstrap, registration, staging, namespace, observer or runtime qualification are required for the profile correction. `puck_dependency_bindings.py:87–105` already validates finite publication rows with physical Python producers; `284–297,330–400` checks active innermost creator, raw edge/cache identity, finite growth, reference stability, exact creator-close roster and final completion. `puck_dependency_imports.py:258–271` already emits every closed published row. CPU registration attachment at `puck_cpu_registration.py:239–252,279–294` already changes only profile/module registration over fixed four staged package roots. Do not weaken those mechanisms if a new test fails.

## Source and input pin strategy

The current runtime source roster remains 24 paths and worker source roster remains 10. The exact delta against original preparation01 remains `{scripts/puck_worker_bootstrap.py, scripts/qualify_puck_cpu_held_runtime.py, src/palimpsest/puck_dependency_bindings.py, src/palimpsest/puck_dependency_imports.py}`. Three were already changed for the publication mechanism; only the parent constants/guard need a further change from current5408. Every one of the 24 source pin rows is recalculated from the selected current bytes for the future freeze; the old preparation source rows/capsules remain exact. Existing v5 requires that exact changed-path set, so no source allowlist extension is necessary.

The held auditor is not a member of the 24 producer-source paths. Bind its new exact source digest independently in the frozen auditor CLI/control manifest and resulting self-source field, along with the external observer's exact source/command. Do not pretend its modified bytes inherit the historical19723 auditor's PASS. The historical preparation acceptance continues to bind the historical v1 auditor SHA and exact old configuration/result/audit/externally-observed CLI.

Keep all 16 input roles and all 15 noncandidate pins unchanged. In particular the existing observation configuration/report/result/audit/index roles continue to mean observation02 and keep their exact hashes and schema. Do not replace them with observation03 just because its rosters informed this later source decision. Keep old candidate-wide `configuration_sha256`, `observation_report_sha256`, `outcome_audit_sha256`, `retained_inventory_sha256`, `template_sha256`, module mapping and generated helper provenance unchanged.

Runtime has no uncovered dynamic check requiring an observation03 attachment: reviewed literal expected rows are source-pinned; C is byte-pinned and semantically exact; historical H and staged bytes are held; worker/auditor prove exact current closure. Re-parsing observation03 at runtime would add roles/protocol without strengthening those checks. Observation03/source attribution belongs to the static prospective proof, which the future reviewed control manifest also pins without making it a runtime authority input.

## New static proof contents / pins

Record full path/size/SHA pins for H, A, C; both source transitions; every unchanged section; all four exact replacement rows; duplicate/missing target checks; exact 41/11/69/29 arrays; fixed declared PyTorch commit `0fabc3ba44823f257e70ce397d989c8de5e362c1`; creator/publication/close source references already retained in the preflight packet; branch/roster attribution and the terminal-only nature of observation03. Bind parent and independent auditor replacement constants to those exact arrays, without runtime code sharing or a self-referential proof hash. Freeze the manifest only after source/proof bytes are final, so it can pin every changed producer/auditor/profile/proof path with no hash cycle.

Immutable A:

- `docs/plans/puck-cpu-autograd-publication-profile-v1.json`: 342451B, SHA256 `ddc770acca34f849b2234db155ea477438560e3e4a58685a2c11632c44e93648`.
- Its `source-proof.json`: 6376B, SHA256 `745e4677e9998351880cc4dfd419b7a43496c9eb009b86db3c44a02e0cd548cd`.
- Authoritative H pin from archived preparation01 `raw/configuration.json`: `docs/plans/puck-cpu-observed-import-profile-candidate-01.json`, 340908B, SHA256 `d20076cd2e1961d1514bb135746b1701a14567136b80ee073fecedb389f929df`. The one-row source proof's inspection copy at `docs/reports/puck-cpu-held-qualification-04/inspection/profile-candidate.json` has the same size/hash; do not replace the preparation's original pin with this inspection path.

Accepted observation03 source `32d1dc690d93ffdfa820bcbe871515266acde5b0`, controls `c998fa3842d8efb2103ec8d23c9bc0eb2f04764b`, archived/byte-complete source head5408. Bind the following exact artifact pins in the prospective source proof (all under `docs/reports/puck-cpu-characterization-03/`):

| Artifact | Bytes | SHA256 |
|---|---:|---|
| `controls/docs/plans/puck-cpu-runtime-characterization-03.json` | 20311 | `69cc87fb68e3c745196b3435c4caaa547ad3bb120ceac6d4834d6b24eecb4e49` |
| `raw/configuration.json` | 17146 | `239efab01fba514d2bc90e7ecf8203032475b37f05a08437a2aedc1d5b2e1e91` |
| `raw/result.json` | 838 | `9670bdf9d297dd14459912d0a71d55a75da13b8723b4f5d79d88dc6c12748569` |
| `raw/payload/imports.json` | 540404 | `083dc25d6942329ee47113af9d0d65c390e901f3505f47e22a29697673e046db` |
| `outcome-audit-03.json` | 5015 | `465b8e30496aae9df13fc4411060cc4cfe98f793d27f4738490f50149cec9a5a` |
| `evidence-index.json` | 42234 | `4f45a7917e0374a9f9948eaa0aa18ddaff15c194cb911c69ad2d31f53120c421` |
| `raw/observer-external-cli-transport.json` | 1940 | `cf0aa869200d07b74be7a40e89a6de8213dd9bbc6ecba1628b8ab0684c7865d3` |
| `observer-external-tool.json` | 3189 | `7f29350d82689256279ddae6929d6cb3e19c85849d2e56ffaec0cf53247d9389` |
| `independent-result-review.json` | 20934 | `74bb2a1fdc7f5b809d6fbbf0c0152e155d858837c99a160b6379eccdfeea2262` |

Do not confuse the frozen pretty configuration digest69cc with the compact retained configuration digest239e. The raw report records all three rosters stable and exact (11/69/29, zero missing/extra) but `profile_accepted=False` and `runtime_qualified=False`. Its metadata binds terminal native child/cache/raw edges, not creator-close lifecycle. The source proof must retain that boundary and remain `actual05_configuration_created=False`, `actual05_invoked=False`, with all authority false.

## Tests to extend / exact regressions

1. `tests/test_puck_cpu_held_amendment05.py:36–100`: expand authored candidate_pair to all four old targets and a complete four-row current candidate. Keep the 41-name autograd array unchanged; independently author/hardcode the three arrays from retained observation03, not producer constants. Positive parent/auditor semantic checks; unchanged15 roles, source set4, negative imports, limits, output05 and old preparation acceptance.
2. Same file `104–205`: retain closed v5 identity and every old v1–v4 rejection. Add explicit rejection of the old one-row A under current v5, each partial two/three-row combination, a fifth changed export, target duplicates/missing target in both old/new candidates, extra allowlist/attachment fields, v6/ID5 aliases, any change to the 15 other pins, and both source-path/hash drift outside the existing four-source delta.
3. Same file `208–255`: parameterize every target and both consumers. Refuse wrong creator/raw path/phase/class, missing/extra/duplicate/unsorted dispatch names, wrong 11/69/29 lists, one changed 41-name autograd entry, metadata/provenance/module-map/namespace/generated helper/native cache/module_changes/native origins edits, export reordering and extra row/top-level fields. Rebind all candidate/config/outcome/transport hashes so rejection proves semantics, not just stale digests.
4. `tests/test_puck_cpu_held_amendment05_integration.py:32–126,131–240` and opt-in fixture construction in `test_puck_cpu_held_parent_integration.py:48`: author all four physical Python creators, native children and finite dispatch sets; include nested fresh imports after c10d/RPC publication while their creator remains open. Prepare with historical source/candidate and retain its original dependency/stage controls; current four-row v5 must pass separate CLI, API audit and independent CLI audit, with exact four closed publications, historical/current dependency/candidate digests distinct and physical/staged roots/distributions/identities unchanged. Preserve all original result and failed attempt bytes. Refuse full rebinding of any published proof (drop/extra/late/substituted delegate or missing creator close), old-candidate substitution, reentry and stage/closure drift. These are authored assertions only, not installed Torch proof.
5. Existing generic mechanism coverage stays in `tests/test_puck_published_exports.py:79–181`, `test_puck_published_export_receipts.py:63–173`, `test_puck_published_export_integration.py:18`. Reuse/extend only multi-creator/nested-creator cases actually needed by the three rows. Do not change mechanism source or broaden other32 native declarations speculatively.
6. Source-proof/data regression: exact H→A and A→C relations, all hashes above, candidate-wide observation02 provenance unchanged, candidate arrays equal accepted03 measured arrays and independently attributed source sets, all creator maps already physical Python, and all declarations/proof claims false. A mismatched or only-count-equal roster must refuse the static source exit. This validation reads retained data only; it must not import Torch or invoke the observation again.
7. Keep `tests/test_puck_cpu_held_observer.py:149–178` v4/v5 output isolation/reentry checks unchanged. Observer v5 identity/output routing already exists and needs no new epoch branch.

Current test fixture/source may be updated to the newly explicit prospective four-row v5 contract; the old one-row candidate/proof/authored source/logs remain pinned history, not a compatibility mode. Preserve the old records and document the source transition instead of keeping an obsolete positive test against current bytes.

## Finite exit / what remains unproved

Stop this source unit after the new candidate/proof, two independently implemented constant/semantic validators, and focused metadata + authored four-creator integration pass review. Then separately review/freeze actual05 controls and fresh source/input/resource/stage state. No actual05 is authorized by this map. No new retry is implicit. Observation03 did not prove held creator-close timing; only the eventual frozen held run can supply that scoped evidence. No numerical/model/renderer/episode/study/hardware qualification follows from these source/data checks.
