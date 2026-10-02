# Wheel-response diagnostic v1 rejection

The fixed eight-trial diagnostic at `27b9990` is **rejected**, with unchanged
sources and no accepted gains. It finishes in 30.362 seconds. Every trial records
one settling interval and stops: the global contact allowlist incorrectly treats
stationary authored obstacle-to-floor support as a forbidden rover contact.
There is no 100-interval fit support, baseline gain or perturbation contrast.

All eight observed intervals have the expected ten timed callback packets and
valid cached-end equality. Each child restores its callback and closes Engine;
its rejected trial exits nonzero. This proves the diagnostic retained its failure,
not contact-free rover movement or adaptation. Root checked all child result
hashes and the coverage/cleanup fields.

The [evidence index](m6-body-gain-diagnostic.json) retains exact protocol/source,
model/gear/world and child result identities. Raw contact packets remain local.
A separately versioned correction may classify verified stationary obstacle
support explicitly; it must preserve every pair and the existing trial/fit limits.
No fit thresholds, control amplitudes, settling windows or geometry are tuned
from this failed attempt. V1 remains unchanged before any new execution.
