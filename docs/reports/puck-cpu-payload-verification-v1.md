# CPU package payload verification v1

## Result

Package acquisition01 passed once, followed by an independent terminal audit GO.
All71 archives are retained:70 wheels and the locked python-louvain0.16 source
archive. This closes the full-payload verification gap in the CPU candidate.
It does not complete the installed runtime or any simulation release gate.

| Actual evidence | Result |
| --- | ---: |
| Downloaded archives / bytes | 71 / 385,328,518 |
| Wheels with complete payload and RECORD checks | 70 |
| Wheel entries / regular files | 28,237 / 26,913 |
| Decoded wheel bytes | 1,304,650,469 |
| Licence candidates inventoried in retained archives | 95 |
| Acquisition elapsed / parent exit | 55.276314082s / 0 |
| Sampled combined parent/worker RSS peak | 92,393,472B |
| Retained namespace | 147 single-link regular files / 3 directories |
| Retained logical bytes | 390,202,259 |
| Independent audit elapsed / exit | 7.575929912s / 0 |
| Live worker-group members / exact acquisition routes at audit | 0 / 0 |

The report counts decoded archive members, not an installed namespace or a RAM
reservation. Sampling and the watchdog are operational limits, not hard RSS/WCET
proof. Licence content remains in the authenticated archives; licence acceptance
is false. Neither source code nor numerical packages were installed or executed.

## Exact invocation and retained evidence

Source commit: eeb82bf03d41fb819a29e639bf341b6b2cb59206.
The [configuration](../plans/puck-cpu-payload-acquisition-01.json) is2,642B,
SHA25691d1dcaabb34f4177650c3c72d2295233bd42814dcd433b369be3e0f8b1c5402.
Independent SOURCE/CONFIG GO preceded this sole invocation:

```bash
/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11 \
-I -S -B scripts/acquire_puck_cpu_payloads.py \
--configuration docs/plans/puck-cpu-payload-acquisition-01.json \
--sha256 91d1dcaabb34f4177650c3c72d2295233bd42814dcd433b369be3e0f8b1c5402
```

The external exec handle21273 ended with chunk8e93d1/exit0. This observation is
separate from the child's own receipt. Normal600s/hard615s,20s socket operations,
1GiB sampled RSS/2GiB worker address space,256 FDs, one worker,4GiB disk floor,
2GiB available-RAM admission and512MiB retained-output limits applied. The live
worker PGID2331707 and exact configuration command routes were independently empty.

The [evidence index](puck-cpu-payload-verification-v1.json) binds the complete local
ignored runs/puck-cpu-payload-acquisition-01 namespace and committed byte-identical
[terminal outcome](puck-cpu-payload-acquisition-01/outcome.json),
[worker result](puck-cpu-payload-acquisition-01/worker-result.json) and
[independent audit](puck-cpu-payload-acquisition-01/audit.json).
The [exact audit stdin program](puck-cpu-payload-acquisition-01/audit-program.py)
is retained as historical evidence, not a product command to rerun into old paths.
The auditor's180s/2GiB read-only stdlib audit independently hashed all raw archives,
checked all manifests and streamed every regular wheel member, CRC, size, hash,
RECORD, metadata identity and WHEEL declaration. It did not call the production
verifier as its proof. Parent exit attribution remains explicitly external.

The [original CPU candidate](../plans/puck-cpu-runtime-candidate-v1.json), assessment,
pyproject.toml and production uv.lock remain unchanged. That candidate is a
historical metadata-only input; this new report supplies actual payload evidence.
Its installed/runtime/study authority remains false. Archives and member manifests
remain local ignored raw evidence with pinned public acquisition URLs and hashes.

## Source checks and review

The [preparation plan](../plans/puck-cpu-payload-acquisition-v1.md) fixes the scope.
The verifier reads only caller-owned descriptors and does not extract code.
The entry fetches one exact HTTPS URL per archive, refuses redirects and proxies,
checks whole hashes before member verification and retains failed bytes.
Stable exclusive archive names remain unchanged throughout concurrent monitoring;
only a verified manifest plus successful audited outcome admits their bytes.

| Authored verification | Actual result |
| --- | --- |
| Verifier TDD sequence | 17 missing-API RED;17 GREEN;32 missing-check RED;58 GREEN; final70 GREEN in0.12s |
| Acquisition/supervisor initial intended RED | 28 failed /1 legacy control passed /34 deselected in0.27s |
| Initial integrated source slice | 133 passed in3.12s |
| Final complete payload/acquisition/supervisor slice | 135 passed in3.15s |
| Affected legacy parent, characterization and registration slice | 70 passed in8.07s |

An initial root RED launch could not create its owned basetemp under the managed
worktree's default read-only sandbox. The same source tests with authorized write
access produced the intended RED above. This was a test-launch issue, not an
actual acquisition attempt.

Review found two connected publication races: temporary two-link publication
violated the monitor's single-link policy, and removing a sampled partial filename
could race the monitor's lstat. Both were reproduced with real files. The repaired
stable-name lifecycle passes both regressions; the supervisor checks remain strict
and its legacy32-file/two-directory default is unchanged. Package preparation
explicitly declares160 files/three directories. Final independent source/config
review found no remaining concrete Critical/Important/Minor issue.

Default pytest remains unqualified: it stopped with10 collection errors in1.85s
before implementation. Missing FastAPI affects test_lab and test_male_lab;
missing httpx affects test_male_recovery_collection, test_male_recovery_data,
test_train_male_recovery, test_verify_body_adaptation, test_verify_body_runtime,
test_verify_body_turns, test_verify_task_phases and test_verify_task_starts.
The focused passes above do not claim a passing complete suite.

## Authenticated source inspection and next exit

A separate read-only post-acquisition inspection checked the locked204,641B
python-louvain tarball hash b7ba2df5002fd28d3ee789a49532baad11fe648e4f2117cf0798e7520a1da56b.
Its64 regular/directory entries total745,075B; no source was extracted or executed.
There is no pyproject.toml. setup.py is666B with SHA256
f21829ac7e1966d2552664824aabc53352534f777fa8a57c591245b04cb6ce22:
it imports setuptools.setup, declares community, networkx/numpy requirements and
the bin/community script. setup.cfg is a38B egg_info configuration.
The index retains selected source-file and licence hashes. Existing r0-reproduction
and lab-hardening environment metadata has packaging26.3 and no pip/setuptools/
wheel/build distribution, so no existing build backend was silently assumed.

The [prospective build proposal](../plans/puck-python-louvain-build-v1-proposal.md)
selects an exact backend candidate without claiming its payload/tool closure or
build route is qualified. Next: authenticate that backend/tool closure,
review a finite isolated source/scratch/wheel-output build configuration, build the
python-louvain wheel once and pass it through the same payload verifier.
Then perform actual installation with .data/script relocation and a complete
installed namespace/licence audit, finish CPU/native/EGL staging and custody,
qualify the exact four-import runtime, and prove the full simulator episode route.

No model, SNP, protected catalog, renderer context, physics, training, collection,
new navigation/memory study, browser/human session or rover work ran. All seven
simulation release gates remain open. Consumed numerical preparation/qualification/
observations and navigation attempts were not retried.
