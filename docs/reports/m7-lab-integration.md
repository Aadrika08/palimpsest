# Male pilot lab integration

At `1f07644`, both fixed CPU pilot controllers pass the separately supervised
native/EGL mechanism gate. Each source executes three ticks, restores two ticks
from a native snapshot, and passes both three-tick executable action and policy
replays at the existing 1e-6 floating tolerances. Camera/integer fields compare
exactly. Malformed hidden state and changed policy identity reject before native
mutation; original-to-control replacement starts fresh hidden state and steps.

The test passes in 15.575 seconds; its 180-second supervisor exits zero in
17.577 seconds. All nine recording manifests complete and source hashes remain
unchanged. The [retained index](m7-lab-integration.json) records source/artifact
hashes, exact policy identities, per-run results and explicit limitations.

These owners run sequentially inside one supervised process. Spawned live Lab
owners, browser behavior and navigation/held-out qualification remain separate
unexecuted gates. No topology benefit, biological input mapping, endurance or
physical result is implied. Sources and runs remain unchanged; ordinary upstream
Pyparsing, sparse CSR and TF32 API warnings are retained in stderr.

Node 24.21.0 cached offline installation, production build, seven measurement
checks and memory annotation checks also pass; logs are hash-indexed. No browser
was executed by these build/fixture checks.
