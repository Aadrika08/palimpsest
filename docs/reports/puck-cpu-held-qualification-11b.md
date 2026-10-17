# CPU qualification 11 (packet 11b): import policy v5 works; deadline exceeded

**Runtime11 failed normally after 180.30s: the parent's normal-return deadline
fired while `import mujoco` was in progress.** No import refusal or guard poison
was recorded before the kill. The policy v5 fix for runtime10's blocker worked:
Torchvision, including `torch._dynamo`, returned under the guard. Attempt 11 is
consumed. The installed import route remains unqualified, and all seven release
gates remain open.

## Sequence (all once, boot `7f875223…`)

1. **Preparation02 (v12):** prepared in 21.9s and independently audited PASS
   ([packet](puck-cpu-held-preparation-02/)), replacing preparation01's stage,
   which a reboot erased.
2. **Controls:** packet 11b at CONTROL `27780dd`. Review 01 was NO-GO
   (stage lost); review 02 was GO.
3. **Guards and admission:** the pre-admission guard passed with stage and boot
   checks. Admission11b was `DATA_ONLY_ADMITTED` in 14.2s with peak 34,032 held
   files and FD 4→4; its independent review was GO. The pre-observer guard passed.
4. **Runtime11:** exit 1 at 180.30s, `TimeoutError: CPU allocation normal return
   deadline`. The worker was terminated, with no survivors and peak RSS 845MB.
5. **Audit:** one run, FAIL (`Normal external transport exit required`), as
   expected for a nonzero transport.
6. **Outcome:** recorded as `FAILED_CONSUMED`. The independent outcome review is
   `PASS_FAILED_OUTCOME_RECORD_NO_RUNTIME_ACCEPTANCE` with no findings.

## Where time went

| Phase | Wall s | Guard s |
| --- | --- | --- |
| dependency setup | 16.8 | 0.9 |
| numpy | 7.8 | 6.2 |
| torch | 20.5 | 12.3 |
| torchvision | 101.3 | 73.3 |
| mujoco (to the kill) | 10.3+ | 10.3+ |

The guard took 112.8s of 166.5s (68%): custody 66.5s and bindings 45.3s. Each
newly loaded native library triggers a full check costing about 0.8s, and
binding checks grow with the number of loaded modules. The same four imports take
4.9s unguarded. The v2 contract's 135–145s estimate missed about 40 late
native-library full checks and mujoco's library-heavy load.

## Next

Fitting a fixed deadline requires guard cost changes: incremental custody per
native load with full verification at phase boundaries, and indexed binding
checks. Alternatively, a new epoch with a different deadline. Either is a new
reviewed source epoch plus a new preparation, because epoch 11 requires
preparation02's exact sources.

Evidence: [packet](puck-cpu-held-qualification-11b/) (175 artifacts, verified
against originals). Controls and reviews are in
`docs/plans/puck-cpu-held-qualification-11*`.
