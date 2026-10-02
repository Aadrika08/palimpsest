# M6 puck construction v4: passed the zero-step gate

The separately reviewed [v4 contract](../plans/m6-puck-construction-v4.json)
passed on frozen source `3e1e2b8b3dbe6fb1b5b1e7e32277f29bc562c7f5`. Exactly two
fresh owners compiled and installed the derived thin-disk model, applied layout
5990, rendered both cameras and closed at zero simulated time, zero control ticks
and zero physics steps. Outer supervision returned exit 0 in **3.729543 seconds**;
the inner verifier completed in **3.565935 seconds**. No retry occurred.

The model/profile, full native model, declared state/control/force, task and
camera hashes match. All **346,537 compared native-data bytes** match, with
defined-byte SHA256
`1e78dcbab047899f3af791c670a8cba0a7f5fe9b24af32ea66cd9a919ae8f340`.
The two unmodified raw native-data containers differ at **443 bytes**, all within
the 1,344 prospectively declared timer-duration, contact-padding and unused
sparse-tail bytes. Exact within-owner pre/post-render native-data hashes remained
unchanged. This is the frozen v4 comparison, not full raw-container equality.

The [evidence index](m6-puck-construction-v4.json) pins the terminal reports,
launcher/plan, source inventory and independent audits. The local stdlib/NumPy
audit rehashed 76 source files and all 24 primary retained files (1,198,404 bytes),
validated size prefixes and sparse extents against the previously reviewed v3
source map, checked current qpos/zero controls and all four uint8[128,128,3]
camera arrays, and independently recomputed the allowed-byte mask and defined
hash without importing the v4 comparison helper or any native runtime. Root's
separate audit rehashed all 18 inner artifacts and recomputed the same results
in 0.077810 seconds.

Both owner exit codes were 0. All current/retired renderer receipts show closure;
both exact PID/start identities and process groups were absent. Finalization
errors were empty and all frozen source hashes were unchanged. The actual slot
was released at terminal, before read-only auditing. The original
[v3 strict failure](m6-puck-construction-v3.md), [source map](m6-puck-construction-v3-byte-map.md),
and every prior artifact remain unchanged.

This establishes this fixed model's construction, defined initial-state equality,
rendering and cleanup under v4. It does not establish stepped contact stability,
pushing, learned control, native continuation/replay, Engine/UI integration or
physical behavior. The ten-owner mechanics verifier is the next separately
reviewed gate; no mechanics execution is included here.
