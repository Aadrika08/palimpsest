# Navigation-v3 matched-budget attempt 2

The separately frozen second invocation at source commit
`e691591cc74009b358be7bd306557dc5fb59b21c` failed before training on
8 October 2026. The user-systemd service exited with status 1 after 1.971 seconds,
1.401 seconds of CPU time and a displayed 35.6M memory peak.

The corrected runner passed its invocation guard and durably reserved the
enclosing attempt and seed-10 pair. The supervised child then failed while
importing its training stack:

```text
ModuleNotFoundError: No module named 'httpx'
```

The import chain reaches `verify_endurance` through the navigation-v2 trainer,
recovery trainer/data/collector and body-adaptation/runtime verification modules.
This is an environment/import failure, not a measured model outcome. The pair
receipt records `training_attempted: false` and both seed-10 arms as
`not_started`. Seeds 11 and 12 never started; no models or successful completion
were published. Held-out status remains `locked_unopened`, and qualification
claims remain empty.

The supervisor records child exit code 1 after 0.40756976199918427 seconds,
2,940 stderr bytes, zero stdout bytes, no signals, no survivors and no supervisor
errors. These are the retained supervisor observations, not a new runtime audit.
The enclosing failure receipt and original attempt files remain immutable.

Attempt 2 is consumed. This finite execution lane ends with an inconclusive
dependency failure; it authorizes no attempt 3, dependency installation, further
training, development evaluation or held-out access. Any future navigation
execution needs a new prospective design decision and independent review.

The eight original JSON/log artifacts are retained byte-for-byte under
`m7-navigation-v3-matched-budget-attempt-2/evidence/`. Their sizes, hashes and
original paths are recorded in that directory's parent `verification.json`.
The execution manifest self-digest is
`41dea77f3705dbd3842c5138c031a0c143fe7efb35b0c4ba53890aac6597262f`.
No scientific gate or historical score changes as a result of this report.
