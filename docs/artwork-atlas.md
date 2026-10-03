# Atlas of what disappears

The offline SVG compares the pinned MaleCNS v1.0 reduced neighborhood before
and after explicitly selected node isolation. It reuses the graph validator and
directed reachability calculation from the reduced-model pilot. It executes no
controller and changes no model checkpoint or graph source.

```sh
palimpsest atlas --graph /path/to/reduced-neighborhood-v1b/graph.json \
  --graph-manifest data/manifests/malecns-reduced-neighborhood-v1.json \
  --cut-node 12781 --output exports/atlas.svg
```

Repeat `--cut-node` for up to 32 distinct existing body IDs; omit it for a no-op.
Isolation removes all incident edges while retaining the original IDs and
artificial input/endpoint query sets. A lost pair means an input had a directed
path to one endpoint before isolation and has none afterward. Counts ignore edge
weight and do not estimate causal influence, memory or behavioural competence.
The source is a capped extracted neighborhood, not a complete connectome.

Both panels use the same fixed circular layout in sorted ID order. Positions are
not anatomical coordinates. Dark filled nodes are the two endpoints; orange
filled nodes lose a path to at least one endpoint. Crosses indicate isolated
nodes and dashed orange edges indicate removed connections. Tooltips identify
directed endpoints and positive synapse counts; they do not imply physiological
signs. The embedded JSON preserves all nodes/edges, before/after query results,
exact cuts, topology hashes, source graph/extraction/manifest hashes, licence,
attribution, extraction boundaries and renderer hash. No external resources,
scripts, inferred labels or fabricated activity are added.

Input limits and pinned graph integrity are inherited from `male_model.load_graph`.
Outputs are capped at 2 MiB and created exclusively under the existing managed
storage limits. Invalid IDs, duplicate IDs, malformed/corrupt input, source
changes and existing output paths fail. Only an incomplete output created by the
current export is removed on failure; source files are preserved.

Run the fixture check with:

```sh
PYTHONPATH=src:tests python -m unittest test_atlas -v
```

The fixture checks direction-sensitive lost paths, no-op and endpoint isolation,
input rejection, embedded identities, XML escaping, exclusive creation, byte
bounds and partial-output cleanup. Actual source/export and visual observations
are separate evidence. This mode does not complete exhibition-duration or
independent-operator gates, and makes no population-wide sex inference.

Actual pinned-graph exports passed for no-op and node 12781 isolation. Isolation
removed 135 edges and lost 137 input–endpoint pairs: 136 to 12781 and one to 556329.
Independent forward traversal confirmed the retained metrics; no-op lost none.
Chromium rendered both panels without text clipping, external requests or errors;
the screenshot was visually inspected. See the [evidence index](reports/m9-atlas.json).
