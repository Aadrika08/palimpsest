# Goal: finish Palimpsest in simulation

**Outcome:** deliver a locally installable Palimpsest release with an inspectable
simulation lab, qualified supported controllers, complete memory and MaleCNS
research, all six usable artwork experiences, and a reproducible handoff accepted
by the user and an independent operator. Start the physical rover only after
simulation acceptance. CI stays outside this goal.

This is the current execution guide for the existing
[completion goal](simulation-completion-next-goal.md). It clarifies order and
completion criteria; the frozen study protocols and original acceptance
thresholds remain binding.

## Current position

- Reviewed source work includes memory compact auditing, source sealing, staged
  pair admission and retained-only reading through PR #115; puck registry,
  interval recording, collection descriptions and historical bundle provenance
  through PR #116. These are software prerequisites, not executed studies.
- All seven simulation release gates remain open. Historical failed capability
  results and consumed navigation attempts remain unchanged.
- At **2026-10-14 15:39 UTC**, this checkout's filesystem had
  **100,710,133,760 bytes free (~93.8 GiB)**. This exceeds the frozen memory
  minimum of **63,786,975,232 bytes (~59.4 GiB)**. The earlier disk shortage is
  resolved at this observation; allocation and launcher admission are still open.
- Recheck required model, upstream and retained evidence inventories after the
  disk cleanup. Free space alone does not establish that inputs remain present
  or valid. Recheck space immediately before each admitted stage.

## Immediate goal: complete the two execution paths

Finish the memory and puck paths from admitted inputs to independently checked
terminal evidence. Each implementation unit must produce working code, meaningful
failure tests, a reviewed commit and a draft PR. Documentation records the result;
it does not substitute for the missing behavior.

### 1. Memory: prove replay, close cases, then admit collection

- [ ] Implement bounded recurrent-cell replay from every retained
  `encoded_input`, using the pinned model and correct initial policy state:
  reset for a source, acquired shared SNP state for a condition. Compare every
  `raw_output` and action under the frozen contract. Deliberately wrong input,
  state, model identity and output must fail. This does not prove camera,
  renderer, physics or full Engine replay.
- [ ] Implement all nine condition seals and whole-case close, binding raw
  audit, retained source, shared SNP, histories, selector identities, pair
  receipts and byte limits. Test failure, missing/extra entries, input drift,
  aliasing and incomplete publication; preserve quarantine on uncertain close.
- [ ] Implement and review raw pruning only after the required audit, replay,
  durable compact re-read and commit gates pass. Prove complete raw-tree absence
  and the one-active-owner rule without orphaning shared snapshot references.
- [ ] Resolve namespace coverage and verify upstream, assets, runtime, cleanup,
  process, storage and source identities. Independently review the complete
  prospective allocation/launcher amendment before permitting a native owner.

**Exit:** one complete memory execution path is admitted under the unchanged
48-family / 144-case / 1,296-condition-cell / 1,440-owner development contract.
All required prerequisites pass, and no unresolved admission finding remains.
Source tests alone do not satisfy this exit.

### 2. Puck: complete provenance and owner admission

- [ ] Freeze a bounded supplied-original-byte positive check for models 21–23.
  Verify the immutable index and original report/protocol/checkpoint bytes;
  qualify the new provenance facade without changing historical loaders or pins.
- [ ] Bind current execution source closure and runtime to exact registry,
  scene, model, invocation and filesystem custody. Complete process supervision,
  storage limits, interval recording, owner/manifest close and attempt receipts.
- [ ] Independently verify the complete collection path, including strict
  historical/new envelope separation and development/held-out inaccessibility.
  Freeze the reviewed source/runtime/input identities before numerical work.

**Exit:** registry/reservation, eight-scene minting and twelve-owner collection
can execute through one reviewed, bounded path. Collection remains unauthorized
until its exact execution admission passes; a non-executable description cannot
be treated as an owner grant.

Memory and puck source work may proceed independently. Serialize actual model,
native and study stages within their existing budgets.

## Then perform the fixed evaluations

### 3. Memory development and held-out research

- [ ] Execute the complete admitted development block in frozen owner order.
  Independently audit every case and all nine conditions; recompute the full
  analysis with family-level uncertainty and required controls.
- [ ] Retain every natural failure with its frozen capped score. An acquisition,
  audit, infrastructure or invariant failure stops the phase under its contract.
  Do not replace cases or silently retry owners.
- [ ] Freeze and independently admit the separate held-out phase before opening
  its inputs, then execute and audit it without development-driven tuning.

**Exit:** complete valid development and held-out evidence supports a positive
or null scientific conclusion. Missing cells or invalid prerequisites are not
an acceptable null result.

### 4. Learned puck capability

- [ ] Run the fixed twelve-owner collection (maximum 7,200 intervals). Require
  every owner to be admitted and at least one motivating-condition row from
  each original collector model. A failed coverage gate stops before fitting.
- [ ] Prepare the fixed ordered corpus and fit all three relabeled models with
  the unchanged 30-epoch learning/selection contract. Admit all bundles and the
  fixed four-owner native/replay mechanism before development.
- [ ] Run the exact 24-owner development pass. Each relabeled model must reach
  **at least 3/4 goals**; retain original-model paired outcomes and every failure.
- [ ] Only after development passes and a separate held-out protocol, retention
  budget and execution admission pass, run the fixed paired held-out evaluation.
  Each relabeled model must reach **at least 6/8 goals**.

**Exit:** all required models meet both capability thresholds, mechanism replay
passes and the supported controller integrates into the lab. A failed study
produces a retained result and a new prospective decision, not an automatic retry.

### 5. MaleCNS navigation

Preserve consumed attempts 1 and 2. No attempt 3 is authorized by this goal or
the disk cleanup. Prepare the concrete amendment/alternative decision needed to
resume this lane. Any approved new study must retain matched budgets, multiple
seeds and the unchanged **3/4 development / 6/8 held-out per-seed** thresholds.
Useful navigation remains required; a null topology advantage is permissible.

## Finish the product and acceptance

### 6. Lab and six artwork encounters

- [ ] Verify the integrated lab on real assets and a browser: install, launch,
  inspection, interventions, pause/step/reset, snapshots/branches, replay,
  comparison, exports, recovery and required endurance.
- [ ] Complete sufficient portable inputs and declared-duration encounters for
  Afterimage; One map, many possible lives; Counterfactual choir; Borrowed body;
  Atlas of what disappears; The space between two flies.
- [ ] Verify actual visual/audio/keyboard/viewport behavior, faithful mappings,
  provenance, stop/recovery controls and scientific-limit labels. Afterimage's
  current short sample does not satisfy sustained-use acceptance.

### 7. Human acceptance and integrated delivery

- [ ] Present concrete visual/audio encounters for the user's artistic review.
- [ ] Have an independent operator install and complete all six modes using the
  written runbook; retain full session and recovery records.
- [ ] Integrate reviewed branches in dependency order when landing is authorized.
  Reverify the final candidate, installation, reproduction, licences, measured
  limits and every requirement-to-evidence link. Keep commits and pushes under
  the repository-local identity and Aadrika08 account.

**Project completion:** all seven simulation gates satisfy their original exits
on the integrated candidate, including human acceptance. Report each gate as
passed, failed or incomplete with its evidence. Do not declare the project done
while a required capability or acceptance gate remains open.

## First action when pursuing this goal

Start with **memory recurrent-cell replay**, based on PR #115, while the
independent puck execution/custody contract is prepared from PR #116. Freeze each
unit's precise interfaces, source/runtime identities and bounded verification
before implementation or actual-input execution. Preserve every failed attempt;
no blind retries, held-out tuning, threshold reduction or physical rover work.
