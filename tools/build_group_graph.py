"""Reduce the FAFB neuron graph to a signed 63-group transition matrix."""
from __future__ import annotations

import gzip
import json
import math
import struct
import sys
from pathlib import Path


def build(binary: Path, metadata: Path, output: Path) -> dict:
    raw = gzip.decompress(binary.read_bytes())
    n, edge_count = struct.unpack_from("<II", raw)
    meta_offset = 8 + edge_count * 12
    groups = [struct.unpack_from("<BH", raw, meta_offset + i * 3)[1] for i in range(n)]
    info = json.loads(metadata.read_text(encoding="utf-8"))
    group_count = info["group_count"]
    weights = [[0.0] * group_count for _ in range(group_count)]
    edge_counts = [[0] * group_count for _ in range(group_count)]
    for edge in range(edge_count):
        pre, post, weight = struct.unpack_from("<IIf", raw, 8 + edge * 12)
        a, b = groups[pre], groups[post]
        weights[a][b] += weight
        edge_counts[a][b] += 1
    # Row L1 normalization retains sign and prevents giant groups dominating.
    for row in weights:
        scale = sum(abs(x) for x in row) or 1.0
        for j, value in enumerate(row):
            row[j] = round(value / scale, 8)
    result = {
        "source": "FlyWire FAFB v783; derived from snedea/flybrain connectome.bin.gz",
        "neuron_count": n,
        "edge_count": edge_count,
        "groups": info["groups"],
        "weights": weights,
        "edge_counts": edge_counts,
        "sha256": __import__("hashlib").sha256(binary.read_bytes()).hexdigest(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2] / "flybrain" / "data"
    out = Path(__file__).resolve().parents[1] / "web" / "data" / "group_graph.json"
    result = build(root / "connectome.bin.gz", root / "neuron_meta.json", out)
    assert result["neuron_count"] == 139_255
    assert result["edge_count"] == 2_698_236
    assert len(result["weights"]) == 63
    print(f"wrote {out}: {result['neuron_count']} neurons, {result['edge_count']} edges -> 63 groups")

