"""Swappable model providers; unavailable providers never fabricate output."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.request import Request, urlopen


@dataclass
class Provider:
    name: str
    capabilities: set[str]
    invoke: Callable[[str, str, dict[str, Any]], dict[str, Any]]
    available: bool = True
    unavailable_reason: str | None = None
    cost_class: int = 0
    latency_class: int = 0

    def call(self, operation: str, task: str, context: dict[str, Any]) -> dict[str, Any]:
        if operation not in {"reason", "generate", "review", "inspect", "verify"}:
            raise ValueError(f"unsupported operation: {operation}")
        if not self.available:
            raise RuntimeError(self.unavailable_reason or f"provider {self.name} is unavailable")
        return self.invoke(operation, task, context)

    def think(self, task: str, context: dict[str, Any], constraints: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.call("reason", task, {**context, "constraints": constraints or {}})

    def inspect(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        return self.call("inspect", task, context)

    def code(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        return self.call("generate", task, context)

    def review(self, task: str, candidate: str, context: dict[str, Any]) -> dict[str, Any]:
        return self.call("review", task, {**context, "candidate": candidate})

    def synthesize(self, inputs: list[str], context: dict[str, Any]) -> dict[str, Any]:
        return self.call("generate", "Synthesize the supplied inputs", {**context, "inputs": inputs})


def deterministic_mock(name: str = "mock") -> Provider:
    def invoke(operation: str, task: str, context: dict[str, Any]) -> dict[str, Any]:
        return {"provider": name, "operation": operation, "text": f"{operation}: {task}", "context_keys": sorted(context)}
    return Provider(name, {"planning", "summarization", "synthesis", "verification"}, invoke)


def ollama_provider(model: str = "qwen3.5:2b", endpoint: str = "http://127.0.0.1:11434/api/chat") -> Provider:
    def invoke(operation: str, task: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = json.dumps({"operation": operation, "task": task, "context": context}, ensure_ascii=False)
        body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": False}).encode()
        with urlopen(Request(endpoint, data=body, headers={"Content-Type": "application/json"}), timeout=120) as response:
            payload = json.load(response)
        return {"provider": f"ollama:{model}", "operation": operation, "text": payload["message"]["content"]}
    return Provider(f"ollama:{model}", {"coding", "research", "planning", "critique", "summarization", "synthesis", "verification"}, invoke, cost_class=0, latency_class=1)
