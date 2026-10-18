# Independent source review 01: policy v5 and epoch 11

**Range:** `d03b85d..ec4de6b` (`bf6b980` tests, `ec4de6b` implementation).
**Reviewer:** separate read-only review agent; it did not edit, commit or run
qualification/admission. **Verdict: APPROVE**, with no Critical or Important findings.

## Confirmed

- **Fail closed.** Every exception in a declared-name path, including a later
  finder resolving the name, a finder without `find_spec` or a failed absence
  check, poisons the guard. Undeclared names still reach the unchanged poisoning
  raise. Hidden matching is exact (`networkx.algorithms` still poisons).
- **No custody bypass via `None`.** The worker runs `-I -B -S -c`, and the bootstrap
  asserts isolated/no-site/no-bytecode. On CPython 3.11.15, `sys.path` holds only the
  stdlib zip, `lib/python3.11` and `lib-dynload`, and `meta_path` holds only the three
  stdlib finders. No declared name exists there. Held packages have
  `__path__ == []`, so dotted names cannot resolve through `PathFinder`.
- **Old behavior is unchanged.** v1–v4 parse and acceptance paths are unchanged.
  Hidden handling and the receipt field are gated on v5. The epoch 6–10 rosters
  remain pinned, and epoch 10 rejects the epoch-11 roster.
- **Exact rosters.** The 32 absent names equal census `non_stdlib_missing` and
  emulation `denied`. The 4 hidden names equal emulation `refused`. None overlaps
  runtime10's 1,783 registered modules, 38 exports or native-cache names.

## Minor findings and disposition

1. No offline run used the exact v5 semantics. **Done:**
   `diagnostics/v5-semantics.json` shows all four imports complete, every declared
   name requested, no hidden module executed and no other unregistered request.
2. Native-cache overlap untested (a mutation survived): add a test.
3. `HIDDEN_TARGET_RAN` assertion is vacuous; the `__hello__` later-finder test is
   the discriminating proof (a mutation removing `_stock_miss` fails it). Clarify.
4. Finders run again after `_stock_miss`; anything loaded in that window is caught
   by the q4 cache recheck before any receipt. Document it.
5. Hidden-roster refusals reuse absent-roster messages. Not changed (cosmetic).
6. Held distribution metadata still lists the hidden packages. Documented in the plan.

Optional hardening is accepted: refuse `expected_hidden_imports` in receipts
other than v5. It is stricter only and changes no outcome.

## Reviewer verification

- Ran: v5 worker + amendment11 tests, 104 passed. amendment11 integration, 1 passed.
- Ran a regression set of 185 cases: 184 passed. The one failure, a q4
  container-subclass case reporting "Collection root or ancestor changed", passed
  on isolated rerun under both basetemps (harness flake).
- Ran two mutation checks in a scratch copy.
