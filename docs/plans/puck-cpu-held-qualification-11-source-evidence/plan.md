# Qualification 11: CPU runtime import route under policy v5

Goal: one separately admitted, observed and independently audited normal
four-import completion under missing-import policy v5 (epoch 11). All seven full
simulation-release gates stay open; operator/renderer qualification and the
public episode remain separate later work.

Use source `1126b71` (v5 implementation plus review follow-ups), original
preparation01, candidate D, the exact 32-name absent roster, the 4-name hidden
roster carried by the qualifier, unchanged environment and 180s/2GiB limits.
Retain consumed qualifications 01-10, admission10-01 (failed, canonical bytes)
and admission10-02 (admitted, consumed by runtime10). No silent retry.

Carried lessons from attempt 10:
1. Write the configuration with the authenticated canonical compact serializer
   from the start; canonical preflight compares the formatter AST and bytes.
2. Use the corrected pre-admission guard history read
   `json.loads((ROOT/(...)).read_bytes())`; never call `read_bytes` on a str.

Steps:
1. Assemble the v11 configuration and baseline runner mechanically from the
   admission amendment02 controls. Prove 26 small history checks RED, then
   GREEN after adding consumed runtime10/admission10-02 history. No SITE/staged
   payload reads, admission, observer, auditor or runtime during assembly.
2. Freeze distinct11 metadata retaining every attempt-10 pin, archive the five
   replaced live sources through the terminal10 packet, and add terminal10,
   admission01/02 and the v2 optional-import contract evidence. Then derive the
   fixed wrapper/envelope, corrected guard template and run-once tools; run the
   authenticated metadata-only self-check; commit; independent controls review;
   push before any admission.
3. Fresh full data-only admission11 once under the fixed envelope; independent
   receipt review; fresh pre-observer guard; sole runtime11 invocation.
4. Bind the audit to the measured transport digest, run the auditor once,
   collect terminal metadata, independently review and archive the outcome.
   Never convert failure into acceptance or retry implicitly.

Observed history RED: 26 cases, 7 errors / 4 failures / 15 passes (missing
10/admission02 helpers, 16 vs 17 historical absences, admission01 still
requiring an absent runtime10 allocation). GREEN: all 26 pass. Canonical
preflight: 9,130B compact configuration accepted by the qualifier and auditor
validators. A scratch metadata probe (not retained; the control self-check
repeats it) found the 32 absent names undeclared and absent from the planned
held forests, and the 4 hidden names undeclared.

Scope: import-route evidence only. No operator, renderer, physics, inference,
collection, protected inputs, studies, CI, cloud or rover execution.
