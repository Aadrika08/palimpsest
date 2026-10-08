# Navigation-v3 matched-budget attempt 1

The single frozen invocation at source commit
`148142b2086b93bdc1b3f0016ec070f99a20823f` stopped before reservation on
8 October 2026. The user-systemd service exited with status 1 after 700 ms,
431 ms of CPU time and a 21.7 MiB memory peak.

The retained journal records the exact failure:

```text
ValueError: Runner argv differs from frozen invocation
```

The manifest stores `runner_argv` as the interpreter followed by the script and
its arguments. Python exposes `sys.argv` beginning with the script, so the guard
compared two representations that cannot be equal in a normal interpreter
launch. The failure happened in `main()` before `execute()`, before creation of
the enclosing output directory or durable attempt receipt. The frozen output
path remains absent. No corpus, model, Torch, MuJoCo, training, simulator,
development scene or held-out input was opened.

The invocation is consumed and will not be retried. Any corrected execution
requires a separately numbered prospective manifest, a faithful process-level
regression, resealed source identities and independent review before launch.

Evidence:

- execution manifest self-digest:
  `c7bbd686b74282ea579662ecf938073152ec1261be89163d37f8f4841c3195f7`
- retained journal: `m7-navigation-v3-matched-budget-attempt-1/journal.log`
- journal SHA-256:
  `51773fc00774b4a3f781fbc96df4c5a642a436afb4bae2a581a34b1243071db2`
- journal size: 2,794 bytes in 10 lines
- qualification claims: none

