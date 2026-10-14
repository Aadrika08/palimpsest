# Fresh puck worker: authenticated local source

Continue the approved simulation goal and PR #128 (`eb96a19`). Implement the
missing fresh-process source boundary before local/model/native imports. This
unit supplies an executable bootstrap preflight, not collection authority.

Use a fixed short stdlib seed under the existing 4096-byte argv-element cap.
Run `python -I -B -S -c <seed>`; the seed opens a regular nofollow bootstrap,
checks its external SHA, and compiles those authenticated bytes. The bootstrap
then authenticates its canonical external-SHA registration and the existing
stdlib held-file implementation before importing it from authenticated bytes.
Keep the seed descriptor and source/runtime custody alive through the entry.

Registration binds exact source descriptors and module/namespace mappings,
interpreter descriptor/version, complete environment, cwd and exact argv prefix.
Append its externally supplied own SHA to that prefix to avoid a circular hash.
Compare kernel cmdline and sys.orig_argv, actual process/start/parent/group and
running interpreter inode. Require fresh isolated flags and no preloaded local
or third-party modules. Local Python loads only from held registered bytes;
unregistered local/third-party imports, bytecode and native alternatives reject.
Check complete Python/XML census under package/scripts/upstream and bind loaded
module objects/specs/origins and local function code identities through close.

Preserve source/input ceilings and a bounded <=180-second worker deadline.
The fixed public entry returns bootstrap/source evidence only. Preserve empty
qualification claims and false dependency/runtime/native/collection grants.
The interpreter object and measured Python version are scoped facts; stdlib,
ELF dependencies, external packages and native images remain a trusted/unqualified
boundary. This is not a sandbox against malicious admitted Python.

- [ ] Observe fresh-child REDs for missing API; wrong source/runtime/argv/env;
  foreign imports, namespace gaps, drift and loaded-code replacement.
- [ ] Implement stdlib seed, strict registration, held-source finder and the
  fixed executable preflight entry; keep every refusal terminal.
- [ ] Independently review the branch, run focused/affected checks serially and
  retain default-suite limitations and exact source evidence.
- [ ] Commit/push a stacked draft PR and synchronize goal/matrix. Continue the
  separate dependency/native admission and complete durable collection launcher.

The full twelve-owner allocation and historical owner denial stay unchanged.
Memory amendment02, catalog access and navigation decisions remain pending.
No actual study/registry/model/native stage; CI and physical rover excluded.
