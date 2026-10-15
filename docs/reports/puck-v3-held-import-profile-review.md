# Held-import profile: independent review and root fix pass

Independent read-only reviewer:601ee9e against8cca8ba. Verdict: changes requested,
three Important findings, no Critical or Minor findings. No second review follows.

| Finding | Reproduced result before fix | Fix in a57cb0d | Regression |
| --- | --- | --- | --- |
| Retained original module metadata unsealed after replacement | Changing delegated original spec.name to foreign exited0/answer51 | Preserve/recheck separate original metadata seal | test_review_retained_original_metadata_is_bound_after_replacement |
| Proxy delegate can switch to unrelated module | Switching delegate exited0/answer99 | Bound direct module/class/function reference edges at phase close, with4,096-edge ceiling and exact identity rechecks | test_review_proxy_delegate_cannot_switch_to_unrelated_module |
| Instance callback shadows authenticated class method | Shadowing bindings.recheck admitted foreign cached export and exited0 | Exact helper receiver/type, no instance method shadows, authenticated class dispatch and direct seal checks | test_review_instance_shadow_cannot_authorize_foreign_export; test_review_other_helper_receivers_cannot_shadow_recheck |

All six parameterized regression cases failed first6.85s, then passed6.65s. Root's
complete affected suite passes149 checks61.66s. The default repository suite still
stops at10 FastAPI/httpx collection errors1.83s. This is root regression evidence,
not an independently issued final-source GO or actual runtime qualification.

Independent focused evidence before the fix:49 checks38.09s sequentially. The
preceding concurrent run had48 passes/one held-ancestor refusal37.62s while the
reviewer also created temporary probe directories. Preserve that contaminated run
and the reported explanation; do not count it as green or silently discard it.

## Rulings and declined scope

- Installed-stack compatibility, actual native-create availability, scientific/
  runtime/physical qualification: not established by this source unit. These
  remain explicit future gates. Treating source fixtures as qualification would
  overstate support and is forbidden.
- Factory association: trust held initialization, bind actual compiled factory/
  method objects plus local name/base and captured per-call class identity. No
  hostile in-process arbitrary construction provenance claim. Cost if wrong:
  qualification would overstate enforcement.
- Delegate correction: capture bounded direct module/class/function reference
  edges instead of freezing arbitrary mutable data or adding another profile
  schema. These explicit captured edges are checked for exact identity. New
  mutable data/defaults/closures are not comprehensively frozen. Cost if wrong:
  an undeclared dispatch mechanism could remain outside this trust boundary;
  actual qualification must still review the supported source and behavior.
- Equal-comparing scalar metadata: reviewer reproduced acceptance and classified
  it as inherited, not a new identity regression. Retain the trusted-scalar
  limitation; exact loader/spec/class/code identities remain enforced. Cost if
  wrong: metadata observations could be misleading under hostile in-process code;
  this implementation does not claim that isolation model.
- Native directory origin: trusted initialization followed by persistent image/
  target/namespace checks; no race prevention. Cost if wrong: swapped native code
  can execute before later refusal. The strict leaf-FD default stays separate.
- Workflow: inline integration plus one bounded independent native-helper task,
  then one fresh whole-branch review. All Important findings enter this one
  RED/GREEN fix pass; no deferred minors were reported. No merge is authorized
  by this report. The externally managed worktree remains for further work.
