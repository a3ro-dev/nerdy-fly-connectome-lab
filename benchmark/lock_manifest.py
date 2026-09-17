"""Write and hash the preregistered protocol before any AGY run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from benchmark.tasks.definitions import TASKS


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def build_manifest(model: str = "gemini-3.8-flash-low", effort: str = "low") -> dict:
    return {
        "schema_version": 1,
        "locked": True,
        "tasks": TASKS,
        "conditions": {
            "identity": "identity matrix; no graph propagation",
            "real": "signed 16-group MaleCNS-derived propagation",
        },
        "extension_conditions": {
            "shuffled": "matched group-label permutation",
            "rewired": "matched directed in/out-degree-preserving edge swaps",
        },
        "seeds": [101, 202, 303],
        "model": model,
        "effort": effort,
        "tool_set": ["AGY workspace file tools", "nerdy-fly MCP tools"],
        "budget": {"fly_steps": 30, "agy_timeout_seconds": 300},
        "grading_rules": "Deterministic exact-file or fixed unittest graders defined per task.",
        "primary_metrics": ["success", "paired_success_difference", "wall_clock_time", "tool_calls", "model_calls", "failure_recovery_rate", "unnecessary_tool_calls", "verification_success", "budget_efficiency"],
        "secondary_metrics": ["memory_reads", "memory_writes", "replanning_frequency", "tool_selection_accuracy", "abandonment_rate", "state_transition_count", "prediction_error_dynamics"],
        "exclusion_rules": "Exclude only documented infrastructure failures before agent execution; retain agent failures and timeouts.",
        "statistics": {"binary": "exact McNemar test on paired task-seed outcomes", "continuous": "paired bootstrap 95% confidence interval with fixed seed 4409 and 10000 resamples", "effect_size": "paired mean or median difference as appropriate", "reporting": "all seeds and per-category results"},
    }


def lock(path: Path, model: str, effort: str) -> str:
    if path.exists():
        raise FileExistsError(f"locked manifest already exists: {path}")
    manifest = build_manifest(model, effort)
    digest = hashlib.sha256(canonical(manifest)).hexdigest()
    payload = {**manifest, "sha256": digest}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return digest


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    print(lock(root / "manifests/primary.json", "gemini-3.8-flash-low", "low"))
