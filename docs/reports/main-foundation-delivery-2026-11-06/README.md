# Verified foundation delivery on main

[PR185](https://github.com/Aadrika08/palimpsest/pull/185) merged on
5 November 2026 at 19:36 UTC as
`530ffe6d3e43b33e425dfa41a9e491e1df09afc9`.

The retained [hosted run](https://github.com/Aadrika08/palimpsest/actions/runs/42087513935)
passed both jobs at exact head `4c50fb7f5d40c5e1fd47f5e0af8bc267c558cf7f`:
6,585 source tests passed, 318 historical tests skipped, all four canonical
passes completed, 48 preflight checks passed and frontend succeeded. The
redundant push event was cancelled. Earlier installation and fixture failures
remain separately retained; their exact scope is not overwritten by this pass.

[Delivery verification](delivery-verification.json) records the fetched remote
main, both merge parents and tree identity. Main's complete tree equals the
tested head's tree, `0d5fe6cf32ab2bf8d78a5527ecf107550257328c`.
The [manifest](manifest.json) binds the byte-identical copied success log and
verification receipt. Original records remain in the CI repair worktree.

This delivers the reviewed authority/replay artifact and proof-first source
foundation. It does not include the newer local numeric-preservation branch or
prove the entire project, actual research/runtime qualification, licensing,
human acceptance or paper/archive release complete. Raw deletion remains
disabled. Automatic post-merge main checks are tracked separately and are not
assumed green from tree equivalence alone.
