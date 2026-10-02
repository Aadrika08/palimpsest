# M7 v2: development admission failed

All 24 fixed development owners completed normally, but the predeclared admission
rule failed: original training seed 11 reached only 1/4 goals. Each original
model had to reach at least 2/4. Recorded held-out seeds 1012–1015 and closed-loop
held-out scenes 1200–1207 remain locked and unopened. No winning seed was selected,
and no threshold, model or scene was replaced.

| Training seed | Original: goals / stalled / time limit | Rewired: goals / stalled / time limit |
| --- | --- | --- |
| 10 | 2 / 2 / 0 | 1 / 3 / 0 |
| 11 | 1 / 3 / 0 | 1 / 2 / 1 |
| 12 | 3 / 1 / 0 | 1 / 2 / 1 |

The batch ran once from `26483f854378040b237d77dbf9f86116bc6f69f2`, using the
unchanged [v2 protocol](../plans/m7-training-v2-protocol.md) and the six
[Stage B models](m7-training-v2-stage-b.md). It recorded 7,668 ticks across scenes
1100–1103, with one natural episode per owner and a 600-tick maximum. The evaluator
took 685.476 seconds; external supervision completed with exit 0 in 685.771 seconds.
These operational results do not turn the failed task threshold into a pass.

The [evidence index](m7-training-v2-stage-c.json) contains every planned outcome,
all six model identities, twelve paired start receipts and the seven component
hashes for each of the four shared initial worlds. All models had exactly matching
physical state, declared policy inputs, environment identity and environment RNG
for each scene before control moved. The independent NumPy-only audit re-read all
records, checked the fixed response-to-action mapping, and rehashed source, assets,
models and retained inventories. It imported neither Torch nor MuJoCo. All 24 owners
closed with exit 0; all 29 observed process/start identities were absent afterward.

The first audit incorrectly expected 24 handles in the final cleanup list. The
supervisor retains the latest eight completed handles, while each of the 24 rows
already contains its close receipt. The original audit script and assertion
failure are retained. The corrected audit checked all 24 receipts, the exact final
eight-handle subset and process absence; no runtime rerun or product change occurred.

The frozen bounds were 1,800 seconds internally, TERM at 1,860 seconds with a
15-second KILL grace inside 1,880-second supervision, 160 MiB per record/snapshot,
4 GiB aggregate, a 1 GiB free-space floor and 1 MiB per log. The retained primary
inventory is 1,538,567,533 bytes. Source, assets and model bundles were unchanged at
terminal validation and the independent audit. Raw artifacts remain locally
retained; their immutable hashes are in the index and primary reports.

These are development outcomes, not held-out evidence or a topology advantage.
No follow-on tuning, training, held-out execution or R3 qualification is included.
