"""Aggregate the 63-group FAFB graph into the shared 16-group ontology."""
from __future__ import annotations

import json
from pathlib import Path

from common_groups import GROUPS, female_group, normalize


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = json.loads((root / "web/data/group_graph.json").read_text(encoding="utf-8"))
    mapping = [female_group(g["name"], g["region"]) for g in source["groups"]]
    matrix = [[0.0] * len(GROUPS) for _ in GROUPS]
    edge_counts = [[0] * len(GROUPS) for _ in GROUPS]
    neurons = [0] * len(GROUPS)
    for old, group in enumerate(mapping):
        neurons[group] += source["groups"][old]["neuron_count"]
        for old_post, weight in enumerate(source["weights"][old]):
            matrix[group][mapping[old_post]] += weight
            edge_counts[group][mapping[old_post]] += source["edge_counts"][old][old_post]
    result = {
        "sex": "female", "dataset": "FlyWire FAFB v783",
        "source_neurons": source["neuron_count"], "source_edges": source["edge_count"],
        "source_sha256": source["sha256"], "groups": GROUPS,
        "group_neurons": neurons, "weights": normalize(matrix), "edge_counts": edge_counts,
    }
    target = root / "web/data/female_common_graph.json"
    target.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    assert sum(neurons) == source["neuron_count"]
    print(f"wrote {target}")


if __name__ == "__main__":
    main()

