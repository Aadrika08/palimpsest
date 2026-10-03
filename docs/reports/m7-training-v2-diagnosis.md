# M7 v2: seed 11 contact-stall diagnosis

The [failed development admission](m7-training-v2-stage-c.md) is retained unchanged.
A read-only inspection found sustained contact with continued forward commands in
all three failed seed 11 original runs. It found no concrete implementation defect
in the checked input, action, continuity or termination paths. This is a scoped
finding, not proof that every implementation path is correct.

| Scene | Outcome / ticks | Final goal distance | Contact ticks in final 50 | Distance moved in final 50 |
| --- | --- | --- | --- | --- |
| 1100 | stalled / 327 | 6.661 m | 48 | 0.01134 m |
| 1101 | goal / 295 | 0.796 m | 0 | 1.23663 m |
| 1102 | stalled / 215 | 3.738 m | 50 | 0.00710 m |
| 1103 | stalled / 389 | 2.515 m | 50 | 0.05401 m |

The failed runs' final 50 velocity commands averaged 0.695, 0.709 and 0.680;
mean absolute heading commands were 0.083, 0.114 and 0.031 radians. These are
command units, not measured body speeds. The recorded motion reached the native
stall rule exactly: 50 consecutive steps moving less than 0.002 m while the
velocity-command magnitude exceeded 0.05. The successful run entered the fixed
0.8 m goal radius without contact.

Recomputed wheel controls matched the pinned upstream projection exactly. Goal
bearing reconstructed from the recorded pose and fixed goal differed by at most
`5.15e-8`; recorded pose continuity was exact. All three stall outcomes occurred
at the first step satisfying the frozen rule, rather than a watchdog timeout.
The trainer carries hidden state between 32-tick windows and detaches its gradient;
it does not reset hidden state at those boundaries.

The already-used 1,983 training ticks contain **zero contact ticks, zero nonzero
collision angles and one constant velocity target**, float32 0.7. There are no
reverse-velocity targets; 31 heading targets exceed pi/2 in magnitude. Thus the
training rows did not exercise contact-conditioned recovery or variable-speed
handling. This is an observed coverage gap and a plausible contributor to the
recorded behavior, not a proved causal explanation or an authorized tuning plan.

The [compact evidence index](m7-training-v2-diagnosis.json) pins all four inspected
development runs, the eight training runs, their complete source inventory reports,
the independent Stage C audit and the checked implementation sources. The checks
used stdlib/NumPy records only: no Torch/MuJoCo imports, new inference, hidden-state
intervention or held-out reads. Held-out stages remain locked and unopened.
