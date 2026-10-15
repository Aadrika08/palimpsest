# CPU export-binding diagnostics: source verified

The narrow diagnostic patch is implemented at
`cc82991610a75ac0d06805e2b1b93d539e81f349`. All **202 affected checks pass in
113.47 s**, external normal exit0/113.625131920s (terminal `ae10ab`). Independent
read-only code/test review reports no material findings. This is authored source
evidence; actual qualification03 remains failed and consumed, its exact row is
unknown, and no04 configuration or invocation exists.

`_resolve` keeps its signature and raw module/class dictionary lookup. A missing
attribute now reports its component and zero-based index. Only that resolver call
in `ExportBindings.complete` is wrapped with producer, phase, export and full
declared path, explicitly raised from the original RuntimeError. Formatting uses
validated bounded string metadata, not module/object representations or dynamic
hooks. Class binding, seal capture, recheck order and every success/refusal remain
unchanged. Other resolver callers retain their original metadata context.

Three new checks first fail on the old generic error in1.32s (terminal `6b8248`),
then pass in1.27s (terminal `5e5542`). The authored three-row case exercises both
completion phases: the first resolves, the second nested path fails, the third
stays untouched, no attribute hook runs, and the original RuntimeError remains
the cause. A fresh held authored worker produces no success receipt or execution
past the failed import, retaining the chained context. The six-file affected wave
also covers native-create timing, class/factory anchors, native caches, drift and
dispatch refusal, held files, source bootstrap and CPU entry rules. Tests use
authored packages with tmpfs scratch; no installed vendor runtime is invoked.

A separately retained authored observation reuses that same held fixture. Its
driver exits0 normally (terminal `87b627`) because the expected worker exits1,
with0B stdout and2,420B stderr, SHA256
`a50e462edd63e3712a07dc729e2bc296cca836008ea0f17a5c643112dca0c229`:

```
RuntimeError: Dependency producer attribute binding is missing: component 'unavailable' at index 1
...
RuntimeError: Dependency export binding resolution failed: producer='fixture_dep.producer'; phase='module_exec'; export='fixture_dep.cache_name'; attributes=['nested', 'unavailable']
```

These invented fixture names are not Torch observations. The trace demonstrates
the diagnostic and preserved cause, not the missing03 row or native qualification.
[Exact source/check/fixture index](puck-cpu-binding-diagnostics-v1/evidence-index.json)
retains the source/diff, historical bindings, commands/logs/results, observation
drivers, complete authored fixture and raw worker streams. Source SHA256 is
`b686c841ee95a0bd6c86bd9183cf0609990038b2666ed2aa924c4321f2a6caae`.
The actual execution worktree retains its old23,102B bindings source and every
frozen03 control; it has not received this patch. No full repository suite ran.

Next: implement and independently review a closed qualification04 source epoch
for this exact diagnostic support-source delta. Preserve v1–v3, the historical
preparation/source capsules, four acceptance anchors, all16 data inputs, exact
missing-import roster, versions, limits and false authority. Existing parent and
auditor source-epoch contracts currently refuse changed bindings; do not bypass
that refusal or add a configurable allowlist. A future actual diagnostic run
requires exact reviewed controls, a fresh capsule, current staged-byte checks and
fresh resource admission. Its retained context may identify the binding; only
observed evidence can support a later profile/phase correction. Do not rerun01–03.
Passing held qualification still precedes the recorded/replayed/exported episode.
All seven release gates, study/catalog decisions and CI/physical deferral remain
unchanged. Source test totals close no runtime, model, artwork or human gate.
