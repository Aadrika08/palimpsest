# Bounded upstream numerical reconstruction

Source: https://github.com/noumenal-ai/anytime-anywhere-pac-bayes
Pinned source revision: `862dcb02c0dffeefd6955293345770f726d8ef95`.

The unchanged, reviewed `scripts/reproduce_headline.py` ran with Python 3.11.15
and NumPy 2.2.5 from the existing Palimpsest environment. No installation was
performed. Execution returned 0 in 0.3314 seconds. Numerical reconstruction used 13 selected upstream files (12,752,817 bytes).
Six additional Lean files were subsequently retained for read-only assumptions
audit, bringing all selected upstream inputs to 12,833,025 bytes.
Paths are preserved; this is not a full repository checkout. Each download matched its Git blob identity,
and each SHA-256 matched a subsequent readback.

## Scope of successful checks

- Remote-sensing paired means: 100/100 exact.
- Walsh-acquisition paired means: 100/100 exact.
- Remote-sensing radius comparisons: 100/100 exact.
- Walsh radius comparisons: zero; the records have no `r_raw_hex`, and the
  upstream script skips that comparison. The `100/100` printed label alone
  must not be interpreted as checking Walsh radii.
- All 200 rounds use `n_stop = 32768`. This script does not empirically
  validate optional stopping or adaptivity for a new Palimpsest workflow.
- Held-out percentages are parsed from released `primary.tsv` summaries:
  remote 1.4744%, 1.3587%, 0.4141%; Walsh 0.1819%, 0.2880%, 0.4605%.
  The script checks their opposite directions. It does not regenerate those
  held-out evaluations or refit models. The changing held-out denominator
  prevents reading these as a direct cross-budget or cross-substrate comparison.

No original model execution, training, full experimental replication, Lean
compilation, theorem verification, or Palimpsest runtime experiment occurred.
The upstream README also states its Lean checkout cannot compile standalone
because toolchain and imported overlay sources are missing.

## Evidence

`download-inventory.json` binds selected inputs and source URLs to SHA-256 and
Git blob identities. `upstream-tree.json` is the exact pinned GitHub API tree.
`reproduction.json` records command, environment, timing, output scope and failed
initial attempts. `stdout.log` and `stderr.log` retain the completed command's
output. `readback.json` records hash verification and per-schema assertion counts.
`SHA256SUMS` binds all retained files except itself.

Initial sandbox initialization and clone/write attempts under
`/tmp/palimpsest-pacbayes-feasibility-20261105` failed on quota; those partial
paths were preserved. Parent explicitly redirected this lane to its writable
research worktree. No deletion, output replacement, paid compute or publication
was performed.

To repeat only this numerical reconstruction from these retained inputs:

```sh
cd upstream
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python scripts/reproduce_headline.py
```
