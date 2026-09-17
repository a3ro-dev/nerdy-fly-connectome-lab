"""Recurrent controller backed by the repository's 16-group graph artifact.

State labels are engineering abstractions. They are not biological variables.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping


CAPABILITIES = (
    "coding", "debugging", "research", "retrieval", "planning",
    "document_analysis", "data_analysis", "mathematics", "vision",
    "web_navigation", "file_manipulation", "shell_execution",
    "api_interaction", "critique", "verification", "summarization",
    "synthesis", "memory_retrieval", "memory_consolidation",
)

TOKEN_CAPABILITIES = {
    "coding": ("code", "implement", "function", "feature", "python", "javascript"),
    "debugging": ("bug", "debug", "failure", "broken", "traceback", "fix"),
    "research": ("research", "source", "evidence", "paper", "citation", "find"),
    "retrieval": ("retrieve", "lookup", "search", "locate", "remember"),
    "planning": ("plan", "schedule", "steps", "strategy"),
    "document_analysis": ("document", "pdf", "report", "text"),
    "data_analysis": ("data", "csv", "table", "statistics", "analyze"),
    "mathematics": ("calculate", "equation", "math", "number", "sum"),
    "vision": ("image", "visual", "screenshot", "diagram"),
    "web_navigation": ("web", "browser", "website", "url"),
    "file_manipulation": ("file", "folder", "write", "rename", "create"),
    "shell_execution": ("shell", "command", "terminal", "test", "run"),
    "api_interaction": ("api", "endpoint", "request", "json"),
    "critique": ("critique", "review", "audit", "weakness"),
    "verification": ("verify", "validate", "check", "prove", "test"),
    "summarization": ("summarize", "summary", "condense"),
    "synthesis": ("synthesize", "combine", "reconcile", "integrate"),
    "memory_retrieval": ("previous", "memory", "prior", "resume"),
    "memory_consolidation": ("store", "retain", "save", "memorize"),
}


class Condition(str, Enum):
    IDENTITY = "identity"
    REAL = "real"
    SHUFFLED = "shuffled"
    REWIRED = "rewired"


@dataclass
class ControllerState:
    sensory_input_salience: float = 0.0
    integration_state: float = 0.0
    working_memory_pressure: float = 0.0
    retrieval_pressure: float = 0.0
    exploration_drive: float = 0.0
    exploitation_drive: float = 0.0
    uncertainty: float = 0.5
    prediction_error: float = 0.0
    action_readiness: float = 0.0
    model_selection_preference: float = 0.0
    tool_selection_preference: float = 0.0
    persistence_write_memory_pressure: float = 0.0
    recurrent: list[float] = field(default_factory=lambda: [0.0] * 16)
    step: int = 0

    def public(self) -> dict[str, Any]:
        result = asdict(self)
        result["recurrent"] = [round(value, 6) for value in self.recurrent]
        return result


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _identity(size: int) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(size)] for i in range(size)]


def _permuted(matrix: list[list[float]], seed: int) -> list[list[float]]:
    order = list(range(len(matrix)))
    random.Random(seed).shuffle(order)
    return [[matrix[order[i]][order[j]] for j in range(len(order))] for i in range(len(order))]


def _rewired(matrix: list[list[float]], seed: int) -> list[list[float]]:
    """Swap directed endpoints while retaining each node's in/out edge counts."""
    size = len(matrix)
    edges = {(i, j): matrix[i][j] for i in range(size) for j in range(size) if matrix[i][j]}
    rng = random.Random(seed)
    keys = list(edges)
    for _ in range(max(100, len(keys) * 20)):
        first, second = rng.sample(keys, 2)
        a, b = first
        c, d = second
        replacements = (a, d), (c, b)
        if a == c or b == d or replacements[0] in edges or replacements[1] in edges:
            continue
        first_weight, second_weight = edges.pop(first), edges.pop(second)
        edges[replacements[0]], edges[replacements[1]] = first_weight, second_weight
        keys.remove(first); keys.remove(second); keys.extend(replacements)
    result = [[0.0] * size for _ in range(size)]
    for (i, j), value in edges.items():
        result[i][j] = value
    return result


class Controller:
    def __init__(self, graph: Mapping[str, Any], condition: Condition | str = Condition.REAL, seed: int = 0):
        self.groups = tuple(graph["groups"])
        if len(self.groups) != 16:
            raise ValueError("FlyOS currently requires the repository's 16-group graph")
        source = [[float(value) for value in row] for row in graph["weights"]]
        self.condition = Condition(condition)
        self.seed = seed
        self.matrix = {
            Condition.IDENTITY: _identity(16),
            Condition.REAL: source,
            Condition.SHUFFLED: _permuted(source, seed),
            Condition.REWIRED: _rewired(source, seed),
        }[self.condition]
        self.state = ControllerState()
        self.last_capability_scores = {name: 0.0 for name in CAPABILITIES}

    @classmethod
    def from_artifact(cls, path: str | Path, condition: Condition | str = Condition.REAL, seed: int = 0) -> "Controller":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")), condition, seed)

    def observe(self, observation: str | Mapping[str, Any]) -> list[float]:
        text = observation if isinstance(observation, str) else json.dumps(observation, sort_keys=True)
        lowered = text.lower()
        capability_signal = {
            name: min(1.0, sum(token in lowered for token in tokens) / 2)
            for name, tokens in TOKEN_CAPABILITIES.items()
        }
        group_signal = [0.0] * 16
        mapping = {
            "visual_sensory": capability_signal["vision"],
            "other_sensory": max(capability_signal["research"], capability_signal["retrieval"]),
            "visual_processing": max(capability_signal["document_analysis"], capability_signal["data_analysis"]),
            "learning_memory": max(capability_signal["memory_retrieval"], capability_signal["memory_consolidation"]),
            "central_complex": max(capability_signal["planning"], capability_signal["mathematics"]),
            "central_other": max(capability_signal["synthesis"], capability_signal["critique"]),
            "descending": max(capability_signal["shell_execution"], capability_signal["api_interaction"]),
            "ascending": capability_signal["verification"],
            "vnc_intrinsic": max(capability_signal["coding"], capability_signal["debugging"]),
            "motor_efferent": max(capability_signal["file_manipulation"], capability_signal["web_navigation"]),
            "modulatory_endocrine": 0.25 + 0.5 * self.state.prediction_error,
        }
        for name, value in mapping.items():
            group_signal[self.groups.index(name)] = value
        self.state.sensory_input_salience = _clamp(sum(group_signal) / 4)
        self._observed_capabilities = capability_signal
        return group_signal

    def propagate(self, input_signal: Iterable[float], rounds: int = 4) -> list[float]:
        signal = list(input_signal)
        if len(signal) != 16:
            raise ValueError("input signal must contain 16 values")
        current = self.state.recurrent[:]
        for _ in range(rounds):
            propagated = [sum(current[i] * self.matrix[i][j] for i in range(16)) for j in range(16)]
            current = [math.tanh(signal[j] + 0.35 * current[j] + 0.65 * propagated[j]) for j in range(16)]
        self.state.recurrent = current
        self.state.step += 1
        self.compute_attention()
        return current

    def compute_attention(self) -> dict[str, float]:
        activity = {name: abs(self.state.recurrent[i]) for i, name in enumerate(self.groups)}
        s = self.state
        s.integration_state = _clamp((activity["central_complex"] + activity["central_other"]) / 2)
        s.working_memory_pressure = _clamp(activity["learning_memory"] + 0.25 * s.uncertainty)
        s.retrieval_pressure = _clamp(activity["ascending"] + 0.4 * s.uncertainty)
        s.exploration_drive = _clamp(activity["other_sensory"] + 0.5 * s.prediction_error)
        s.exploitation_drive = _clamp(activity["descending"] + 0.5 * (1 - s.uncertainty))
        s.action_readiness = _clamp((activity["motor_efferent"] + s.integration_state) / 2)
        s.model_selection_preference = _clamp((activity["central_other"] + activity["learning_memory"]) / 2)
        s.tool_selection_preference = _clamp((activity["descending"] + activity["motor_efferent"]) / 2)
        s.persistence_write_memory_pressure = _clamp(activity["learning_memory"] + 0.4 * s.prediction_error)
        return s.public()

    def score_capabilities(self, available_capabilities: Iterable[str]) -> dict[str, float]:
        s = self.state
        gates = {
            "research": s.exploration_drive, "retrieval": s.retrieval_pressure,
            "memory_retrieval": s.retrieval_pressure, "memory_consolidation": s.persistence_write_memory_pressure,
            "planning": s.integration_state, "synthesis": s.integration_state,
            "verification": max(s.uncertainty, s.prediction_error), "critique": s.uncertainty,
            "shell_execution": s.tool_selection_preference, "file_manipulation": s.action_readiness,
            "web_navigation": s.exploration_drive, "api_interaction": s.tool_selection_preference,
        }
        observed = getattr(self, "_observed_capabilities", {})
        scores = {
            name: round(_clamp(0.7 * observed.get(name, 0.0) + 0.3 * gates.get(name, s.integration_state)), 6)
            for name in available_capabilities if name in CAPABILITIES
        }
        self.last_capability_scores = scores
        return scores

    def _select(self, candidates: Iterable[Any], requested: str | None = None) -> Any | None:
        ranked = []
        for candidate in candidates:
            if not getattr(candidate, "available", True):
                continue
            capabilities = set(getattr(candidate, "capabilities", ()))
            score = sum(self.last_capability_scores.get(name, 0.0) for name in capabilities)
            if requested in capabilities:
                score += 1.0
            score -= 0.05 * float(getattr(candidate, "cost_class", 0))
            score -= 0.02 * float(getattr(candidate, "latency_class", 0))
            ranked.append((score, str(getattr(candidate, "name", "")), candidate))
        return max(ranked, default=(0.0, "", None), key=lambda item: (item[0], item[1]))[2]

    def select_model(self, providers: Iterable[Any], requested: str | None = None) -> Any | None:
        return self._select(providers, requested)

    def select_tool(self, tools: Iterable[Any], requested: str | None = None) -> Any | None:
        return self._select(tools, requested)

    def update_prediction_error(self, predicted_reward: float, observed_reward: float) -> float:
        error = max(-1.0, min(1.0, observed_reward - predicted_reward))
        self.state.prediction_error = abs(error)
        self.state.uncertainty = _clamp(0.8 * self.state.uncertainty + 0.2 * abs(error))
        return error

    def update_from_result(self, result: Mapping[str, Any]) -> float:
        verified = bool(result.get("verified", False))
        changed = bool(result.get("state_changed", False))
        failed = bool(result.get("error"))
        reward = (0.6 if verified else 0.0) + (0.3 if changed else 0.0) - (0.5 if failed else 0.0)
        # State-transition verification prevents repeated no-op calls earning reward.
        reward = reward if changed or verified else min(reward, 0.0)
        self.update_prediction_error(float(result.get("predicted_reward", 0.5)), reward)
        if verified:
            self.state.uncertainty *= 0.6
        return reward

    def decide_continue_or_act(self, budget_remaining: int, verified: bool = False) -> str:
        if verified:
            return "stop"
        if budget_remaining <= 0:
            return "budget_exhausted"
        if self.state.uncertainty > 0.65:
            return "verify"
        if self.state.action_readiness >= 0.35:
            return "act"
        return "continue"

    def fingerprint(self) -> str:
        payload = json.dumps({"condition": self.condition.value, "seed": self.seed, "matrix": self.matrix}, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()
