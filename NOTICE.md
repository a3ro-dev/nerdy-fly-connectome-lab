# Data and attribution notice

`web/data/male_common_graph.json` is an aggregate derived from the canonical
Janelia FlyEM MaleCNS v1.0 annotation, neurotransmitter, and min-confidence 0.5
weight tables downloaded from <https://male-cns.janelia.org/download/>. Janelia
marks these downloads CC-BY. Exact source hashes are embedded in the artifact
and listed in `REPORT.md`.

`web/data/female_common_graph.json` and `web/data/group_graph.json` are derived
aggregates of the FlyWire FAFB v783 female adult fly-brain connectome. The
immediate packaged binary source was
[`snedea/flybrain`](https://github.com/snedea/flybrain), commit `9191824`, whose
code is MIT licensed. The source binary SHA-256 is
`fbf8d440ca1207c7573e1acdd2366f9d0beb9b533c1710f21681264f81b1cc49`.

Scientific source: Dorkenwald, Matsliah, Sterling et al., “Neuronal wiring
diagram of an adult brain,” *Nature* 634, 124–138 (2024),
<https://doi.org/10.1038/s41586-024-07558-y>.

Redistributors must preserve applicable attribution and comply with the
original data terms.
