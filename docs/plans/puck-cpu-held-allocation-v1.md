# CPU held allocation01: configuration, observation and independent audit

This is the next bounded implementation step in checkpoint A of the active
simulation-release goal. It must lead to the actual runtime and episode; source
checks alone cannot finish that checkpoint. PR148 is the unchanged source base.

## Contract

1. Freeze the canonical production preparation configuration, exact 24-source
   roster and 16 input roles, accepted package/observation02 identities, four
   roots and original interpreter/native baseline. Keep 4GiB preparation and
   2GiB qualification RAM floors. Preparation has a1GiB file ceiling matching
   its admitted package leaves; qualification keeps16MiB. The previous16MiB
   preparation ceiling could not copy six accepted libraries and is corrected
   prospectively before allocation. Metadata/log and64MiB output bounds stay.
2. Select exactly `numpy._distributor_init_local` and `org` as finite expected
   misses for the new CPU v3 allocation. Authenticated NumPy source explicitly
   probes the first optional name; neither has a declared module mapping. The
   provider must prove absence in the held namespace. All other misses remain
   fatal. The old GPU/v2 proposal and consumed attempts remain unchanged.
3. Implement a small external CLI observer. Authenticate the canonical config,
   invoke only the fixed isolated original-Python parent command, retain new
   stdout/stderr files, observed exit/elapsed and byte hashes, and refuse any
   existing external artifact or parent output. Bound external collection to
   210s plus 5s cleanup, with an outer 225s alarm. Its inherited file hard
   ceiling permits1GiB preparation payloads; external streams are read/accepted
   only up to16MiB each. This records transport only;
   the parent and independent auditor own runtime/byte acceptance.
4. Implement an independent stdlib-only auditor. Authenticate configuration,
   source/input pins, exact external transport, phase/result/supervision/closure,
   baseline summaries and current trusted bytes. Independently derive and census
   all four staged file/directory plans, stream their hashes and check tmpfs
   root identities and candidate/distribution mappings. Qualification additionally
   binds the exact successful preparation result, worker registration/dependency
   identities, four versions, cache bindings and finite missing-import roster.
   Never import target packages or parent validators to audit their results.
5. Review the exact configuration, observer, auditor and tests independently.
   Freeze their hashes before actual invocation. Admit fresh resources first.
   Run actual preparation once only if admitted, then retain and independently
   audit its observed outcome. A failed allocation stays consumed and halts this
   lane. Do not create qualification JSON with an invented preparation hash.
6. Only after a passing preparation audit can the qualification configuration be
   frozen with its actual result pin, independently reviewed and invoked once.
   Qualify/audit the exact held four-import runtime before the separately declared
   real simulator episode, replay and export.

## Verification and stop conditions

Use real tiny child processes for observer success/failure/timeout/refusal tests.
Use authored metadata and tmpfs trees for auditor positives and meaningful byte,
namespace, identity, transport and semantic tamper negatives. Retain RED/GREEN
outcomes; use an actual authored CLI seam to check integration before the real
stack. These fixtures grant no installed-runtime, model or scientific authority.

No new navigation/memory study, protected catalog read, renderer/operator session,
CI change, merge, cloud purchase or physical work is admitted by this unit. All
seven release gates stay open. RAM snapshots are transient; no known failed
admission should be invoked just to obtain another failure artifact.
