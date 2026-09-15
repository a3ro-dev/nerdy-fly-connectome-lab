"""Create a non-destructive experiment-state snapshot before upgrades."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / "work/snapshots" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target.mkdir(parents=True, exist_ok=False)
    paths = [
        "work/explorer_checkpoint.json", "work/reasoner_checkpoint.json",
        "work/internet_events.jsonl", "work/reasoning_events.jsonl", "work/talk_events.jsonl",
        "web/data/internet_status.json", "web/data/internet_page.json", "web/data/reasoning_status.json",
        "web/data/reasoner_intent.json", "web/data/discovered_lessons.json", "web/data/mock_mailbox.json",
    ]
    copied = []
    for relative in paths:
        source = root / relative
        if source.exists():
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination); copied.append(relative)
    corpus = root / "work/corpus"
    manifest = []
    for path in sorted(corpus.glob("*.json")):
        data = path.read_bytes()
        manifest.append({"name":path.name,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
    metadata = {"created_at":datetime.now(timezone.utc).isoformat(),"copied":copied,"corpus_files":manifest,"corpus_total_bytes":sum(item["bytes"] for item in manifest)}
    (target / "snapshot_manifest.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    print(target)


if __name__ == "__main__": main()
