"""Stream the canonical MaleCNS v1.0 edge table into the 16-group ontology."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.ipc as ipc

from common_groups import GROUPS, male_group, normalize

NT_SIGN = {
    "acetylcholine": 1, "dopamine": 1, "octopamine": 1, "serotonin": 1,
    "gaba": -1, "glutamate": -1, "histamine": -1, "unclear": 0,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table(path: Path) -> pa.Table:
    return ipc.open_file(pa.memory_map(str(path))).read_all()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data = root / "data/male-cns-v1.0"
    annotation_path = data / "body-annotations-male-cns-v1.0-minconf-0.5.feather"
    nt_path = data / "body-neurotransmitters-male-cns-v1.0.feather"
    edge_path = data / "connectome-weights-male-cns-v1.0-minconf-0.5.feather"

    annotations = table(annotation_path)
    rows = annotations.select(
        ["bodyId", "superclass", "class", "subclass", "fruDsx", "status"]
    ).to_pylist()
    # The downloadable annotation table contains non-neuronal and unassigned
    # bodies. Match the release's graph-audit convention: require an assigned
    # superclass and exclude records explicitly labelled Glia.
    rows = [row for row in rows if row["superclass"] and row["status"] != "Glia"]
    rows.sort(key=lambda row: row["bodyId"])
    body_ids = np.fromiter((row["bodyId"] for row in rows), dtype=np.int64)
    body_group = np.fromiter((male_group(row) for row in rows), dtype=np.uint8)

    nts = table(nt_path).select(["body", "consensus_nt"]).sort_by([("body", "ascending")])
    nt_ids = nts["body"].combine_chunks().to_numpy(zero_copy_only=False)
    positions = np.searchsorted(nt_ids, body_ids)
    present = (positions < len(nt_ids)) & (nt_ids[np.minimum(positions, len(nt_ids) - 1)] == body_ids)
    nt_names = np.full(len(body_ids), "unclear", dtype=object)
    nt_names[present] = np.asarray(nts["consensus_nt"].take(pa.array(positions[present])).to_pylist(), dtype=object)
    signs = np.fromiter((NT_SIGN.get(name or "unclear", 0) for name in nt_names), dtype=np.int8)

    matrix = np.zeros((len(GROUPS), len(GROUPS)), dtype=np.float64)
    pair_counts = np.zeros_like(matrix, dtype=np.int64)
    source_pairs = kept_pairs = kept_synapses = 0
    reader = ipc.open_file(pa.memory_map(str(edge_path)))
    for batch_index in range(reader.num_record_batches):
        batch = reader.get_batch(batch_index)
        source_pairs += batch.num_rows
        pre = batch[0].to_numpy(zero_copy_only=False)
        post = batch[1].to_numpy(zero_copy_only=False)
        weight = batch[2].to_numpy(zero_copy_only=False)
        pi, qi = np.searchsorted(body_ids, pre), np.searchsorted(body_ids, post)
        valid = (pi < len(body_ids)) & (qi < len(body_ids))
        valid &= body_ids[np.minimum(pi, len(body_ids) - 1)] == pre
        valid &= body_ids[np.minimum(qi, len(body_ids) - 1)] == post
        valid &= signs[np.minimum(pi, len(body_ids) - 1)] != 0
        if not valid.any():
            continue
        pi, qi, weight = pi[valid], qi[valid], weight[valid]
        flat = body_group[pi].astype(np.int64) * len(GROUPS) + body_group[qi]
        signed = weight * signs[pi]
        matrix += np.bincount(flat, weights=signed, minlength=len(GROUPS) ** 2).reshape(matrix.shape)
        pair_counts += np.bincount(flat, minlength=len(GROUPS) ** 2).reshape(matrix.shape)
        kept_pairs += len(weight)
        kept_synapses += int(weight.sum())
        if batch_index % 250 == 0:
            print(f"batch {batch_index}/{reader.num_record_batches}: {kept_pairs:,} retained signed pairs", flush=True)

    group_neurons = np.bincount(body_group, minlength=len(GROUPS)).tolist()
    nt_counts = {name: int((nt_names == name).sum()) for name in sorted(set(nt_names))}
    result = {
        "sex": "male", "dataset": "MaleCNS v1.0", "license": "CC-BY",
        "annotation_rows": annotations.num_rows,
        "publication_neurons": 166691,
        "retained_neurons": len(body_ids),
        "neuron_filter": "assigned superclass and status != Glia",
        "source_edge_pairs": source_pairs,
        "kept_signed_edge_pairs": kept_pairs, "kept_synapses": kept_synapses,
        "groups": GROUPS, "group_neurons": group_neurons,
        "weights": normalize(matrix.tolist()), "edge_counts": pair_counts.tolist(),
        "neurotransmitter_counts": nt_counts,
        "source_sha256": {
            annotation_path.name: sha256(annotation_path), nt_path.name: sha256(nt_path), edge_path.name: sha256(edge_path),
        },
    }
    target = root / "web/data/male_common_graph.json"
    target.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    assert sum(group_neurons) == len(body_ids)
    assert len(result["weights"]) == len(GROUPS)
    print(f"wrote {target}: {kept_pairs:,} pairs, {kept_synapses:,} synapses")


if __name__ == "__main__":
    main()
