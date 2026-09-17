"""Capability registry with explicit risk and permission metadata."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    provider: str
    capabilities: set[str]
    invoke: Callable[[dict[str, Any]], dict[str, Any]]
    risk_level: str = "low"
    read_write: str = "read"
    latency_class: int = 0
    cost_class: int = 0
    required_permission: str = "none"
    available: bool = True

    def call(self, arguments: dict[str, Any], granted_permissions: set[str]) -> dict[str, Any]:
        if not self.available:
            raise RuntimeError(f"tool {self.name} is unavailable")
        if self.required_permission != "none" and self.required_permission not in granted_permissions:
            raise PermissionError(f"tool {self.name} requires {self.required_permission}")
        return self.invoke(arguments)


class CapabilityRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self.tools[tool.name] = tool

    def metadata(self) -> list[dict[str, Any]]:
        return [{
            "name": tool.name, "provider": tool.provider,
            "capabilities": sorted(tool.capabilities), "risk_level": tool.risk_level,
            "read_write": tool.read_write, "latency_class": tool.latency_class,
            "cost_class": tool.cost_class, "required_permission": tool.required_permission,
            "availability": tool.available,
        } for tool in self.tools.values()]
