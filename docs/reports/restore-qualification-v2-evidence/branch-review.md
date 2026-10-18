# Fresh restore branch review

Independent source reviewer `restore_v2_branch_review` reviewed the approved plan and the complete implementation through 6b43427; 35eed71 changed only launcher tests. No native study, snapshot decoding, tests or leases were run by the reviewer.

Two Important findings were found and addressed in 5bbdb69:

- Interruption/finalization: the one GNU TERM890/KILL5 watchdog now encloses the entire supervised launcher, including the pipeline, rechecks, cleanup and publication. The inner pipeline has no second watchdog. Raising TERM handling remains installed through finalization; nonzero/watchdog/interruption invalidates the close. Two TERM cases and the complete-supervision command checks failed before the fix, then passed.
- Native accounting: before each new owner, reserve its entire bounded recording/SNP/control/log allowance against the same three-root budget. The unchanged worker's run-root-only budget cannot then consume sibling bytes reserved at admission; concurrent logs retain the existing 64 MiB headroom. A sparse occupied-sibling fixture failed before the reservation and passed afterward. This is an observation/reservation, not an atomic quota against unrelated writers.

Candidate projection and independent source/job/raw/post integrity were reviewed without findings. No deferred minors or declined material source judgments were reported. Fresh registration and actual native outcomes were not judged by that source review and remain separate checks.

Root final verification after the fix: 100 focused checks passed; 1,015 full-suite checks passed, 24 opt-in checks skipped, 39 existing warnings. The skips and completed-owner fixtures provide no asset-backed qualification.
