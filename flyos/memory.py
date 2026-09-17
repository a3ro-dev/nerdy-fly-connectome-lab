"""Bounded, transparent JSONL memory independent of model conversations."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORDS = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")


@dataclass(frozen=True)
class Memory:
    id: str
    kind: str
    content: str
    confidence: float
    created_at: str
    source: str
    provenance: dict[str, Any]
    write_reason: str


class MemoryStore:
    def __init__(self, path: str | Path, max_items: int = 1000):
        self.path = Path(path)
        self.max_items = max_items

    def _rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines()[-self.max_items:]:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def write(self, kind: str, content: str, confidence: float, source: str, provenance: dict[str, Any], reason: str) -> Memory:
        if kind not in {"working", "episodic", "task", "persistent"}:
            raise ValueError("invalid memory kind")
        if not content.strip() or not 0 <= confidence <= 1:
            raise ValueError("memory content and confidence are invalid")
        created = datetime.now(timezone.utc).isoformat()
        identifier = __import__("hashlib").sha256(f"{created}\0{content}".encode()).hexdigest()[:16]
        item = Memory(identifier, kind, content[:4000], confidence, created, source, provenance, reason)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(asdict(item), ensure_ascii=False, separators=(",", ":")) + "\n")
        return item

    def retrieve(self, query: str, limit: int = 4, reason: str = "task relevance") -> list[dict[str, Any]]:
        limit = max(0, min(limit, 20))
        terms = {word.lower() for word in WORDS.findall(query)}
        ranked = []
        rows = self._rows()
        for age, row in enumerate(reversed(rows)):
            overlap = len(terms & {word.lower() for word in WORDS.findall(str(row.get("content", "")))})
            if overlap:
                ranked.append((overlap, float(row.get("confidence", 0)), -age, row))
        ranked.sort(reverse=True, key=lambda item: item[:3])
        return [{**item[3], "retrieval_reason": reason, "age_events": -item[2]} for item in ranked[:limit]]
