# M6 puck construction v3: strict native-data equality failed

The two-owner construction gate **failed** its frozen full-native-data equality
criterion. Both owners individually constructed the derived model, applied the
authored layout, rendered both cameras and closed normally at zero simulated
time, zero control ticks and zero physics steps. Their model/profile identity,
full native model, declared qpos/qvel/controls/forces, task state and both camera
hashes match. Their 347,881-byte native-data containers differ at **986 bytes**.
The matching fields do not replace the failed criterion or qualify the gate.

The one approved attempt used source
`b28ad05b62a4885b3d744450d7c214da35cd4201` and the unchanged
[v3 protocol](../plans/m6-puck-construction-v3.json). Outer supervision returned
exit 1 in **3.331930 seconds**; the inner verifier ended after **3.146767 seconds**
with `Fresh-owner equality failed: full_native_data`. Each owner returned exit
0. All current/retired renderer receipts show closure, both exact child PID/start
identities and process groups were absent, source hashes remained unchanged,
and finalization-error lists were empty. The actual slot was released; there
was no retry or further native job.

The [evidence index](m6-puck-construction-v3.json) pins both terminal reports,
launcher, prepared plan and independent stdlib/NumPy audit. The audit rehashed
74 source files and 24 primary retained files (1,177,555 bytes), checked all four
RGB arrays as uint8[128,128,3], and retained every differing half-open byte range.
It did not deserialize native containers or import MuJoCo/Torch. Root separately
recomputed the same inventories, cleanup, equality results and byte differences.

The raw native containers and strict failed result remain unchanged. Their byte
interpretation requires a separate read-only investigation against pinned
MuJoCo 3.3.6 serialization source; unknown contents are not normalized, zeroed or
excluded on the basis of this result. The prior
[v1](m6-puck-construction-v1.md) and [v2](m6-puck-construction-v2.md) failures
remain retained. No criterion revision or subsequent construction, mechanics,
learning, Engine/snapshot/replay or physical qualification is authorized here.
