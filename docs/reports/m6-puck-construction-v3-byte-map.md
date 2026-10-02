# M6 puck v3: source mapping of native-data differences

All **986 differing bytes** in the retained native-data containers are mapped;
none remain unclassified. This read-only investigation does not change the
[strict failed v3 result](m6-puck-construction-v3.md), mutate either container,
or qualify stepping, restoration or pushing. The
[index](m6-puck-construction-v3-byte-map.json) pins the analysis script, complete
field/range map and official MuJoCo 3.3.6 source files used.

The script follows the serializer's size-prefixed field order, checks matching
prefixes, validates its embedded model against the separately retained model,
and accounts for 162 fields through the exact 347,881-byte EOF. It uses only
stdlib byte inspection: no MuJoCo/Torch import, native deserialization, compiler
or new owner. The serializer writes raw structs and full declared array
capacities, beyond the integration-state subset.
[Serializer](https://github.com/google-deepmind/mujoco/blob/3.3.6/python/mujoco/structs_wrappers.cc#L717),
[framing](https://github.com/google-deepmind/mujoco/blob/3.3.6/python/mujoco/serialization.h#L50).

| Field's half-open byte range | Differing bytes | Source-bound interpretation |
| --- | ---: | --- |
| `timer` [279971, 280211) | 70 | Only duration doubles differ; call counts and padding match. |
| `contact` [331125, 334581) | 20 | Only trailing offsets 572–575 of 576-byte structs differ; every declared contact field matches. |
| `iM_colind` [341289, 341729) | 180 | Differences occur only after the 50 active entries. |
| `iM` [341737, 342617) | 356 | Differences occur only after the 50 active entries. |
| `iLD` [342625, 343505) | 360 | Differences occur only after the 50 active entries. |

`mjTimerStat` contains a duration and count; `mjContact` contains 65 doubles and
13 integers, followed by four alignment bytes on the observed x86-64 ABI.
The six-contact payload confirms that 576-byte stride. Thus the contact
differences are C layout padding, while timer durations are diagnostic values.
[Struct definitions](https://github.com/google-deepmind/mujoco/blob/3.3.6/include/mujoco/mjdata.h#L121).

The matching island row counts and contiguous row addresses identify exactly
50 populated sparse entries. Allocation and serialization reserve `nC=110`
entries for each of the three island arrays; the block-diagonal copy populates
only the active rows. All 50 active entries match byte-for-byte. The unused
tail contents have no assigned numerical/physical interpretation here; this
trace does not identify which prior allocation supplied them.
[Array capacities](https://github.com/google-deepmind/mujoco/blob/3.3.6/include/mujoco/mjxmacro.h#L818),
[population call](https://github.com/google-deepmind/mujoco/blob/3.3.6/src/engine/engine_island.c#L524),
[sparse copy](https://github.com/google-deepmind/mujoco/blob/3.3.6/src/engine/engine_util_sparse.c#L1146).

Every other mapped field matches, alongside the independently checked model,
task, control/state and camera hashes. This binds the interpretation to the
retained files, reported runtime version and hashed official 3.3.6 source;
it is not a provenance claim about a rebuilt library or arbitrary ABI/version.

No additional native diagnostic is needed to locate this mismatch. A future,
separately reviewed construction protocol could retain both full raw blobs and
the within-owner render-mutation check, while comparing all defined fields
exactly and documenting only these source-derived exclusions: timer duration,
contact tail padding and sparse allocation tails beyond validated active rows.
It must fail on any new/unmapped difference and retain the existing native
snapshot/restore hash contract. No such comparison change or further gate has
been implemented or authorized by this report.
