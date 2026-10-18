# Held-runtime qualification01: consumed terminal failure

Exact admitted freeze6382710ba0a2dd29e3c42aa60ff2cfd8804e03c6faf11ea7c6a1cdee714a1446
was invoked once. Parent exit1 in28.075810656s externally,27.977489195s internally;
child exit1, sampled parent-plus-child peak191426560B, matching survivors empty,
no supervisor resource-stop failure and no external timeout. The process failed
its import contract, not its stated resource ceilings. This is operational
process-group evidence only, not proof about escaped descendants.

Fixed entry began NumPy and failed before any completed three-import result.
Retained child stderr identifies the first cause: unregistered
`numpy._distributor_init_local`, requested from NumPy _distributor_init.py:13.
The optional probe was caught by package code, but the undeclared import poisoned
the bootstrap; the first cause survives in the final traceback. Torch and MuJoCo
were not reached by the sequential fixed entry. No inference, renderer/MjModel,
physics, collection or scientific attempt was requested. No runtime/native/
collection/release authority was granted. All receipt authority remains false.

Raw worker/parent/launcher logs, invocations, registration, source/input/freeze
identities and terminal are preserved with qualification-manifest.json.
Preparation01 and qualification01 are consumed; neither may be repeated. No
ordinary observation refresh or automatic amendment/retry follows.

Next source-only unit: define and test a finite declared expected-missing-import
contract tied to the registered dependency namespace, including root/child names,
exact ModuleNotFoundError identity, refusal when a target exists, poisoning for
undeclared misses, and no ambient fallback. Use authored fixtures and retained
evidence. A later actual allocation requires its own prospectively reviewed
identity, scope and decision; this failure is never rewritten as a pass.
