# Third-party notices

These notices describe third-party materials; they do not assign a license to Palimpsest's own code. Python packages retain their respective licenses, available in their installed distributions.

## FLYNN upstream code

The `upstream/fly-gym` submodule is [ben-gitdev/fly-gym](https://github.com/ben-gitdev/fly-gym), pinned at `8d964599119b420de67ee259434d273651a1a76d`. Its own code is licensed under MIT, copyright (c) 2026 Benquan Wang. The full license and copyright notice are retained in [upstream/fly-gym/LICENSE](upstream/fly-gym/LICENSE); preserve them with redistributed copies or substantial portions of the upstream software.

Attribution: Wang and Chen, [FLYNN: Robust Neural Network for Robot Navigation using Fly Brain Topology](https://arxiv.org/abs/2607.00025). Palimpsest uses the pinned upstream simulation, analytical teacher, recurrent model, and sensory/action path through a separate bounded harness; the upstream checkout remains unchanged.

## FlyWire graph and FLYNN checkpoint

The [pinned hosting card](https://huggingface.co/datasets/benquan1/fly-gym-trained-policies/blob/507bef22433c83db3581abd1ab393b25c3aa4989/README.md) identifies both assets below as **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**:

| Asset | Attribution and scope |
| --- | --- |
| `drosophila adult connectome.7z` | FlyWire Consortium / FlyWire FAFB v783 connectivity, obtained via [philshiu/Drosophila_brain_model](https://github.com/philshiu/Drosophila_brain_model), distributed by the FLYNN authors. Includes the edge list and mapping CSVs. |
| `connectome_rnn_dagger_princeton_full_vision.pt` | Trained FLYNN checkpoint distributed by the FLYNN authors; the hosting card identifies its incorporated FlyWire connectivity as subject to the same terms. |

License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) and [legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode). Retain attribution, the license link, supplied notices, and any change indication on reuse or redistribution; the license restricts commercial use. See also [FlyWire's terms](https://flywire.ai/tos) and the retained [upstream data-source notice](upstream/fly-gym/connectomes/drosophila%20adult%20connectome/data%20source.txt). Upstream's MIT code license does not relicense these assets.

The [model manifest](model_manifests/flynn-full-vision.json) pins the hosting revision, archive/checkpoint hashes, extracted edge identity, and mapping identities. Prepared graph/mapping bytes are preserved from the verified archive. Mapping copies in upstream Git use LF endings; archived copies use CRLF and are verified as otherwise byte-identical. This file verification does not prove the legacy checkpoint's original training graph or ordered neuron IDs.

## MaleCNS reduced pilot

The separate `male-cns:v1.0` dataset is published under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), as stated on its
[official download page](https://male-cns.janelia.org/download/) (checked
2 October 2026). Attribution: FlyEM (HHMI Janelia), University of Cambridge
(Department of Zoology), MRC Laboratory of Molecular Biology, and Google Research.
These terms do not change the female-derived FLYNN assets' separate terms above.

The committed `data/assets/flynn/male-reduced-v1/` bundle incorporates a modified,
bounded extraction: 138 neurons and 1,647 directed connections selected around
DNge104 endpoints 12781 and 556329. The [extraction manifest](data/manifests/malecns-reduced-neighborhood-v1.json)
records queries, thresholds, hashes, boundary exclusions and source attribution.
`source-graph.json` preserves that extraction. `original-graph.json` adds the
authored input/output interface; `degree_rewired-graph.json` is an explicitly
rewired control. Neither graph is a complete connectome or an anatomical sensor
map. Preserve the attribution, licence link and modification descriptions when
redistributing the incorporated data.

The two checkpoints were produced by this project's bounded teacher-imitation
pilot using the pinned upstream MIT recurrent code. They contain separately
trained artificial encoder/readout parameters and fixed graph-derived weights;
female pretrained parameters were not transplanted. Exact graph/checkpoint,
training report and protocol bytes are pinned by the
[seven-file bundle manifest](data/manifests/male-reduced-policy-v1.json).
Historical local paths in the protocol identify the recorded training sources;
they are provenance, not installation paths. The raw teacher recordings remain
separate local evidence and are not included in this small inference bundle.
This notice does not assign a licence to Palimpsest's own code or new parameters.
