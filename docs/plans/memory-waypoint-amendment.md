# Memory waypoint amendment: acquisition and prerequisite qualification

Approved in conversation on 4 October 2026. Base `c0606da`. Preserve the original
memory-v2 failure and profile. This authorizes implementation, up to three fixed
development acquisition probes, eight mandatory prerequisites, audited readout,
incremental commits, push as Aadrika08 and a draft PR stacked on #66. No merge,
paired pilot, fitting, held-out access or hardware work.

## Frozen candidates and interfaces

Keep obstacles, start, inspection/crossing/exit/detour points, decision and goal.
Order radii 1.4, 1.3, 1.2 metres. For each south chain let
`c=(-.8-sqrt(2*r-1), -r)`, `theta=asin((r-1)/r)`, and, for i=1..7,
`a=theta-(theta+4*pi/3)*i/7`, `p=c+r*(cos(a),sin(a))`.
Round to 12 decimal places; north mirrors y. Append the existing decision node.
Declare all candidate coordinates/hashes before any native probe. No subsequent
candidate edits, extra candidates or retries. Stop development at the first
independently audited prefix that obtains both real open observations and returns.
The selected profile is frozen for all mandatory prerequisites.

Resolve geometry, manifests, snapshots and audits by registered profile hash.
The original profile remains the default and its cases/readers remain valid.
Packet version 2, task-state version 3, application snapshot version 8 and
snapshot-container version 1 stay unchanged. The headless profile remains absent
from the lab API. Unknown M, CPU FLYNN, 4 m/90-degree half-FOV, circular occlusion,
.75 m sampling, .35 m visible arrival and CueUnavailable remain unchanged.

Analyze arrival neighborhoods and heading variation, retain unsafe combinations
explicitly, and never interpret centerline or conditional sampled geometry as
native feasibility. Preserve exact policy/input bindings and raw packet/M replay.

## Execution and stopping

Global cap 7200 seconds including preflight/admission/cleanup/audit: development
1200, mandatory prerequisites 5400, readout 600. No time transfer. One CPU owner
at a time. Prefix internal/external 360/370 seconds; full prerequisite 720/730;
restore 150/160. Reserve existing 10-second owner cleanup and phase cleanup.
Unattempted work stays explicit if admission cannot accommodate an owner.

Development uses seed-400 south-prefix, once per candidate in fixed order. A
candidate task failure may advance to the next predeclared candidate; source,
raw-audit, ownership or infrastructure failure ends development immediately.
All failed evidence is retained. If none qualifies, prerequisites are unattempted.
The eight existing prerequisites are north/south open-route completion,
north/south blocked-route retreat/replanning, both acquisition prefixes and two
five-tick deterministic restores. First mandatory failure stops later owners.
No pilot follows this run even if all pass.

Keep 1200 acquisition/900 continuation/2100 total ticks at .02 s, attempts 2,
inspection 150 and waypoint 300 ticks. Global new outputs <=8 GiB, require 10 GiB
free initially and maintain 2 GiB; 64 MiB control headroom. Recordings <=512 MiB,
SNP <=16 MiB, each stdout/stderr <=1 MiB. No historical evidence deletion.

## Work, verification and publication

1. Geometry registry, legacy compatibility, case/hash-bound private admission,
   snapshot rejection and independent arrival/heading analysis; red-green checks.
2. Opt-in amendment runner with frozen candidate ledger, larger owner deadlines,
   selected-profile binding, strict infrastructure stops and truthful unattempted
   ledger; red-green checks and complete default software regression.
3. Freeze executable/source/input identities, execute once under the caps, audit
   all attempted recordings and cleanup, publish evidence and actual limitations.

Use repo-local Aadrika Maurya <aadrikamaurya@gmail.com>, push the fresh
`research/memory-waypoint-amendment` branch, draft PR base
`research/memory-v2-feasibility`. Main remains unchanged. GitHub billing/spending
restriction is an external CI prerequisite, independent of local checks.

Qualification establishes development feasibility only. R2, paired memory benefit,
puck/navigation capability, held-out and physical/operator gates remain open.
