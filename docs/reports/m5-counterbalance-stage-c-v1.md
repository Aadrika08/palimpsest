# M5 Stage C v1: zero-owner admission failure

The single authorized Stage C launch at frozen source `a1815763db70152a21b4796ea89015c382ff08eb` failed before starting its first owner. No native owner, policy call, numeric tick, selection comparison or task outcome exists. All forty planned owners remain unattempted. This is infrastructure failure, not a negative task result or R2/held-out evidence; no retry was performed.

The first job was s24/local_cue/change's zero-tick anchor, `522beb4299c54c8096e70f63843d0067`. `validate_job` joined `Path(job['root_output'])/'runs'/artifacts._id(job['run_id'])`, but the unchanged shared `_id` validates canonical spelling and returns a `uuid.UUID`. Joining that object to `Path` raises `TypeError: unsupported operand type(s) for /: 'PosixPath' and 'UUID'`. A read-only reconstruction of the exact first job from the retained plan reproduced the same error with the real frozen validator. The previous bookkeeping fixture mocked that validator; its successful pure checks did not cover this concrete happy path.

The supervisor exited 1 after 9.439746912 seconds; outer wall including cleanup was 10.339206121 seconds, with 0.070377947 seconds cleanup. Both observed non-launcher PID/start identities are absent; there are no surviving owned processes, forced signals, watchdog signal messages or monitor errors. The supervisor's combined `timeout_or_external_failure` flag is true because of the nonzero exit; no elapsed watchdog timeout is evidenced. The exclusive runtime slot was released at terminal cleanup.

Read-only audit rehashed all 291 frozen identity files (149 tracked source/tests/lock, 122 upstream and 20 assets), checked exact before/after inventory equality, the empty owner directory, and terminal PID absence. The original source, prepared IDs, controls and failed output remain retained unchanged. Primary pins:

- Prepared plan: `271aeb35ccd0dc839cb0ee23a633a15d91e7831236358fc81fb979e1e39382ab`.
- Ignored launcher: `8a6280a9cd50b223d84effadb2322730a4a39dfcdf0884a5b2f745ff2836f7c0`.
- `runs/m5-counterbalance-stage-c-20261003/comparison-report.json`: `9e6ed998ed4ef25fb3398129bdacfd440075f4cbd7e5ebb656ac1ab35d4f811a`.
- `runs/m5-counterbalance-stage-c-launch-a181576/launch.json`: `997f4b39a9803c1d4da81d3c538e0441920b26c7ccff7c213c70b897d7d8fb61`.
- Before/after/prepared inventory: `dd0beafc117e7844374e06fa5e3aec5681583c35145651fec677fd71f2d16b12`.

The [JSON index](m5-counterbalance-stage-c-v1.json) retains all forty unattempted IDs, exact supervision/cleanup, primary controls and output file hashes; its scope excludes ignored bytecode caches and contains no native/recording artifacts. The next authorized source-only fix validates the UUID separately and joins its original validated string, with a real validator happy/malformed/path fixture. Any future gate requires a separately frozen v2 plan, fresh forty IDs, fresh controls/output and another explicit GO. Existing source, task and resource limits are unchanged.
