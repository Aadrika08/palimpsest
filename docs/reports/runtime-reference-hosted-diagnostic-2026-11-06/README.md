# Hosted supervisor diagnostic

PR187 run [42129292624](https://github.com/Aadrika08/palimpsest/actions/runs/42129292624)
at `4a59e7a776331f402302579fcf7fb20781d31fe2` failed. Ordinary checks
passed7,035 with318 skips; isolated checks had6 passes and1 failure;
persistent checks passed5 and tmpfs checks passed57. Total7,103 passes,
318 skips,1 failure. Frontend passed. Original API response and warning-bearing
log are retained here. The duplicate push run42129260349 was cancelled.

The failed child-retention fixture expected exit7 but observed null. In
`bounded_qualification.supervised`, a null return code means no child was
launched. Its initial observation can refuse on parent RSS, free space, output
size or elapsed deadline. The existing assertion did not include the retained
supervision record in its failure output; CI's final disposable-fixture cleanup
removed that record. The exact hosted refusal reason is unknown.

The logged5.0GiB available at setup describes the workspace mount, whereas this
fixture uses `/home/fixture/.cache`; it does not establish that mount's free
space at the failed observation. No multi-GiB growth from the added fixtures was
established. Memory or deadline pressure also remains possible. Production
supervisor, wheel parent, runner, workflow and this fixture's behavior were
unchanged from the earlier passing source.

The diagnostic change adds the full observation as assertion context to the
three state assertions. It changes no production code, limits, selection,
deadlines or expected result. A fresh focused run passed1 check in0.27s:
exit7, failure null, no matching survivors. Its log and original supervision
record are retained here. The earlier full local canonical pass remains a
separate7,104-pass result; neither local result clears the hosted failure.

An independent read-only diagnosis confirmed the no-launch path and the
missing hosted reason. Next: one exact-head hosted validation with this added
diagnostic, retaining any failure before deciding a fix. Do not blindly relax
guards or claim an environmental cause. PR187 must remain unmerged until the
required exact-head checks pass. Research/account quota is independently
unknown; included CI minutes are user-reported. No research execution,
source03 service, actual preservation comparison, protected reads or raw
deletion is authorized by this diagnostic.
