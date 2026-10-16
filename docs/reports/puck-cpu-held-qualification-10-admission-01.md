# Qualification 10 data-admission 01: consumed before payload checks

The reviewed controls were committed and pushed at `b3d50f5` before execution
([PR176](https://github.com/Aadrika08/palimpsest/pull/176)). They bound source
`e723db0` / implementation `cbe48b3`, 1,998 pins / 107,657,006B, original preparation,
candidate D, nineteen negative names and unchanged 180s/2GiB qualification limits.
Thirteen small history checks and the metadata self-check pass; independent
controls review found no findings. Those checks did not prove canonical JSON bytes.

The fresh pre-admission guard passed with 47 committed controls, 79 retained
historical metadata files, twenty distinct absences and current resource checks.
The sole fixed admission invocation returned 1 normally in 0.116932s externally
(0.164563s through the tool wrapper), with no timeout. It failed at admission
line 367: the authenticated reader requires sorted compact canonical JSON plus
LF, while the new configuration was pretty-printed with indent=2. Its SHA binding
passed; its canonical-byte check failed. This authoring defect was not caught by
the earlier semantic metadata checks or source review.

No freeze/manifest holding, plan validation, SITE or staged-payload census was
reached. No DATA_ONLY_ADMITTED receipt exists. Failure telemetry records held
close completed, FD4→4 and no current-process children/non-main threads. This is
failure cleanup observation, not completed custody or runtime-parent closure.
The runtime observer was never invoked; actual10 remains uninvoked. Attempts
01–09 remain consumed and unchanged. All seven simulation-release gates stay open.

The [independent outcome review](puck-cpu-held-qualification-10-admission-01/observations/palimpsest-held10-admission01-outcome-review.json)
confirms the failure boundary and causal formatting mismatch. The closed packet
contains 89 artifacts / 1,341,886B / six empty files, including 47 exact original
control paths and 27 source paths. Verification against retained originals and
source Git passes; committed-membership verification is required before publishing.
No failed receipt or original frozen control was replaced.

The separately named [admission amendment02](../plans/puck-cpu-held-qualification-10-admission-amendment-02/plan.md)
now contains only a corrected prospective configuration and canonical preflight.
Its new test and RED were committed first at `fa0db6f`: the unchanged pretty bytes
are refused. The corrected compact file passes the same preflight in 0.064032s;
its formatter AST matches the authenticated reader, and every parsed value is
unchanged. The new file is 8,988B, SHA256
`4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170`.
This is metadata proof only, not a new admission or runtime result.

Next: create distinct amendment02 runner/freeze/wrapper/envelope/output paths,
retain admission01 failure, independently review and push those controls, then
make one fresh full data-only admission. Only after it passes and its receipt is
independently reviewed may a fresh guard precede the sole actual10 observer and
audit. No operator/renderer, physics, inference, scientific or rover claim follows.
