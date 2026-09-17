"""Auditable FlyOS task runtime."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .controller import CAPABILITIES, Condition, Controller
from .memory import MemoryStore
from .providers import Provider, deterministic_mock
from .tools import CapabilityRegistry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskState:
    run_id: str
    task: str
    condition: str
    seed: int
    budget: int
    created_at: str
    status: str = "active"
    verified: bool = False
    steps: int = 0
    observations: list[dict[str, Any]] = field(default_factory=list)


class FlyRuntime:
    def __init__(self, root: str | Path, condition: Condition | str = Condition.REAL, seed: int = 0, providers: list[Provider] | None = None):
        self.root = Path(root).resolve()
        graph = self.root / "web/data/male_common_graph.json"
        self.controller = Controller.from_artifact(graph, condition, seed)
        self.seed = seed
        self.providers = providers or [deterministic_mock()]
        self.registry = CapabilityRegistry()
        self.task: TaskState | None = None
        self.trace: list[dict[str, Any]] = []
        self.memory: MemoryStore | None = None

    def _record(self, event: str, **payload: Any) -> dict[str, Any]:
        row = {
            "time": _now(), "event": event,
            "run_id": self.task.run_id if self.task else None,
            "step": self.task.steps if self.task else 0,
            "controller_state": self.controller.state.public(),
            **payload,
        }
        self.trace.append(row)
        if self.task:
            path = self.root / "benchmark/runs" / self.task.run_id / "events.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        return row

    def create_task(self, task: str, budget: int = 20, run_id: str | None = None) -> dict[str, Any]:
        if not task.strip() or not 1 <= budget <= 1000:
            raise ValueError("task and budget are invalid")
        identifier = run_id or str(uuid.uuid4())
        self.task = TaskState(identifier, task.strip(), self.controller.condition.value, self.seed, budget, _now())
        self.memory = MemoryStore(self.root / "benchmark/runs" / identifier / "memory.jsonl")
        signal = self.controller.observe(task)
        self.controller.propagate(signal)
        scores = self.controller.score_capabilities(CAPABILITIES)
        self._record("task_created", task=task, budget=budget, controller_fingerprint=self.controller.fingerprint(), capability_scores=scores)
        return self.status()

    def observe(self, observation: str | dict[str, Any]) -> dict[str, Any]:
        self._require_task()
        signal = self.controller.observe(observation)
        recurrent = self.controller.propagate(signal)
        scores = self.controller.score_capabilities(CAPABILITIES)
        self.task.observations.append({"time": _now(), "summary": str(observation)[:1000]})
        self._record("observation", summary=str(observation)[:1000], recurrent=recurrent, capability_scores=scores)
        return {"state": self.controller.state.public(), "capability_scores": scores}

    def route(self, requested: str | None = None) -> dict[str, Any]:
        self._require_task()
        provider = self.controller.select_model(self.providers, requested)
        tool = self.controller.select_tool(self.registry.tools.values(), requested)
        decision = self.controller.decide_continue_or_act(self.task.budget - self.task.steps, self.task.verified)
        result = {"decision": decision, "requested": requested, "provider": provider.name if provider else None, "tool": tool.name if tool else None, "top_capabilities": sorted(self.controller.last_capability_scores.items(), key=lambda item: item[1], reverse=True)[:5]}
        self._record("route", **result)
        return result

    def delegate(self, operation: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_task()
        provider = self.controller.select_model(self.providers, operation)
        if provider is None:
            raise RuntimeError("no available provider")
        result = provider.call(operation, self.task.task, context or {})
        self.task.steps += 1
        self._record("model_result", provider=provider.name, operation=operation, result_summary=str(result)[:2000])
        return result

    def update_result(self, result: dict[str, Any]) -> dict[str, Any]:
        self._require_task()
        reward = self.controller.update_from_result(result)
        self.task.steps += 1
        self.task.verified = self.task.verified or bool(result.get("verified"))
        decision = self.controller.decide_continue_or_act(self.task.budget - self.task.steps, self.task.verified)
        if decision in {"stop", "budget_exhausted"}:
            self.task.status = decision
        self._record("result", reward=reward, decision=decision, result=result)
        return {"reward": reward, "decision": decision, "state": self.controller.state.public()}

    def store_memory(self, kind: str, content: str, confidence: float, source: str, provenance: dict[str, Any], reason: str) -> dict[str, Any]:
        self._require_task()
        item = self.memory.write(kind, content, confidence, source, provenance, reason)
        self._record("memory_write", memory_id=item.id, kind=kind, reason=reason)
        return asdict(item)

    def retrieve_memory(self, query: str, limit: int = 4, reason: str = "task relevance") -> list[dict[str, Any]]:
        self._require_task()
        result = self.memory.retrieve(query, limit, reason)
        self._record("memory_read", query=query[:500], count=len(result), reason=reason)
        return result

    def status(self) -> dict[str, Any]:
        return {
            "task": asdict(self.task) if self.task else None,
            "condition": self.controller.condition.value,
            "controller_state": self.controller.state.public(),
            "providers": [{"name": p.name, "available": p.available, "reason": p.unavailable_reason} for p in self.providers],
            "tools": self.registry.metadata(),
        }

    def _require_task(self) -> None:
        if self.task is None:
            raise RuntimeError("create a task first")
