# Puck learning v2 — prospective stop mechanics gate

**Passed once** on source `f5d9ba1897dc2dab815c3a6713adb077ff3564f7`.
This gate tests the new teacher's 0.2 m stop boundary, task mechanics and native
continuation/replay. The sensor-only learning cursor has pure fixture evidence;
this gate does not execute it or collect the fresh learning dataset.

All ten owners completed within the unchanged ten-owner, 600-tick episode,
600/660/+15/680 s and 1 GiB limits. Outer exit was 0 after 44.946819119 s;
the inner gate took 44.678747372 s. There were 1569 recorded intervals and
13 retained snapshots.

| Owners | Recorded intervals | Actual result |
| --- | ---: | --- |
| Zero, positive fixed push, negative fixed push | 120 each | Fixed mechanics horizons completed |
| Positive teacher | 359 | Natural goal; final distance 0.16228323241680062 m |
| Negative teacher | 359 | Natural goal; final distance 0.17220720095507097 m |
| Tick-one, first-contact, first-dwell continuations | 4 each | Every numeric field matched its own new source window exactly |
| Action replay | 120 | Exact new fixed-action source parity; zero teacher calls |
| Policy replay | 359 | Natural goal; exact new teacher source parity |

The positive teacher's first contact was completed tick 112 and its first dwell
tick was 350. All three continuation boundaries retained the exact corresponding
native snapshot/application identity. These are new measured trajectories;
historical 361-tick trajectories and their parity results are not transferred.

All 83 pinned source files remained unchanged. Every owner restored its contact
callback, closed native resources and preserved its full model hash. All ten owner
groups and all 12 sampled PID/start identities were absent after completion.
No forced signals, survivors, sampler errors or finalization errors occurred.
The outer supervisor drained bounded logs, and the slot was explicitly released
before the read-only audits.

The local NumPy-only audit passed on its first invocation in 2.224334523 s. It
rehashed 146 retained files totaling 197,307,021 bytes and checked all 1569 rows,
raw contacts/stages, native poses, independent teacher/mode/task arithmetic,
snapshot payloads and exact continuation/replay dtype, shape and bytes. A separate
root audit also passed first in 3.815330632 s, checking 146 outer and 140 inner
references. Neither audit imported MuJoCo/Torch or constructed a native runtime.
Hashes, original report inventories and both audit scripts are bound in the
[compact evidence index](m6-puck-learning-v2-mechanics-v1.json).

The [rejected v1 collection](m6-puck-teacher-collection-v1.md) remains unchanged and
ineligible for training. The [v2 plan](../plans/m6-puck-learning-v2.md) still requires
separate approval for a fresh complete 20-owner collection with the same ten-stop
label admission, followed by separate training/dev/held-out gates. This result
establishes no learned or physical pushing capability.
