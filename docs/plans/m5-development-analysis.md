# Fixed development paired readout

`scripts/analyze_memory_matrix.py` reads up to twelve explicitly hash-pinned,
completed comparison reports: historical C3/C4 and the ten remaining profiles.
It reuses the existing fixed-profile and bounded JSON readers. It does not launch
owners, load models, open held-out cases, alter reports or replace their raw audits.

The output lists each observed cell, missing cells, all nine targeting/task/timing
readouts and paired own-versus-reference differences. It retains the eight shared
seed namespaces, regime, schedule and physical closure side. Historical C3's
broader forks stay separate from C4/new strict core forks; other conditions retain
their declared configuration/resource differences. A full 48-cell readout does
not mark R2 or held-out qualification complete.

Timing differences are `own - reference`, computed only when both boundaries were
observed. Missing own/reference/both timings remain explicitly censored; no timeout
is substituted. Null confirmations are never stale corrections. Descriptive
stratum means include their paired denominator and missing counts, without a
significance test, independent-frame inference or route-independent effect claim.
The original per-fact observations/confirmations and uncertainty intervals remain
in the readout. These are declared report readouts, not newly reconstructed events.

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest tests.test_memory_matrix_analysis
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/analyze_memory_matrix.py \
  --report EXACT_REPORT_SHA256 /absolute/path/comparison-report.json
```

Repeat `--report` for each completed profile. The JSON goes to stdout; choosing a
new receipt path is the caller's responsibility. The program rejects duplicate,
incomplete, failed or foreign profiles and checks input hashes again before output.
No report or runtime experiment was executed by this source declaration.
