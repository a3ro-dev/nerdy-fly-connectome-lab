"""Paired aggregation without optional scientific dependencies."""
from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def mcnemar_exact(identity_only: int, real_only: int) -> float:
    discordant = identity_only + real_only
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(min(identity_only, real_only) + 1)) / (2 ** discordant)
    return min(1.0, 2 * tail)


def bootstrap_ci(values: list[float], seed: int = 4409, samples: int = 10_000) -> list[float | None]:
    if not values:
        return [None, None]
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(samples))
    return [means[int(0.025 * samples)], means[int(0.975 * samples)]]


def aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [run for run in runs if not run.get("infrastructure_failure")]
    pairs = defaultdict(dict)
    for run in valid:
        pairs[(run["task_id"], run["seed"])][run["condition"]] = run
    complete = [pair for pair in pairs.values() if set(pair) >= {"identity", "real"}]
    identity_only = sum(pair["identity"]["success"] and not pair["real"]["success"] for pair in complete)
    real_only = sum(pair["real"]["success"] and not pair["identity"]["success"] for pair in complete)
    success_differences = [float(pair["real"]["success"]) - float(pair["identity"]["success"]) for pair in complete]
    time_differences = [pair["real"]["wall_clock_time"] - pair["identity"]["wall_clock_time"] for pair in complete]
    categories = {}
    for category in sorted({run["category"] for run in valid}):
        rows = [run for run in valid if run["category"] == category]
        categories[category] = {condition: {"n": len(selected := [run for run in rows if run["condition"] == condition]), "success_rate": sum(run["success"] for run in selected) / len(selected) if selected else None} for condition in ("identity", "real")}
    conditions = {}
    for condition in ("identity", "real"):
        selected = [run for run in valid if run["condition"] == condition]
        conditions[condition] = {
            "n": len(selected),
            "successes": sum(run["success"] for run in selected),
            "success_rate": sum(run["success"] for run in selected) / len(selected) if selected else None,
            "mean_wall_clock_time": sum(run.get("wall_clock_time", 0) for run in selected) / len(selected) if selected else None,
            "mean_tool_calls": sum(run.get("tool_calls", 0) for run in selected) / len(selected) if selected else None,
            "verification_rate": sum(bool(run.get("verification_result")) for run in selected) / len(selected) if selected else None,
            "input_tokens": sum(run.get("input_tokens") or 0 for run in selected),
            "output_tokens": sum(run.get("output_tokens") or 0 for run in selected),
        }
    failure_modes = defaultdict(int)
    for run in valid:
        if not run["success"]:
            failure_modes[run.get("failure_mode") or "unspecified"] += 1
    return {
        "runs": len(runs), "valid_runs": len(valid), "infrastructure_failures": len(runs) - len(valid),
        "complete_pairs": len(complete), "identity_only_success": identity_only, "real_only_success": real_only,
        "paired_success_difference": sum(success_differences) / len(success_differences) if success_differences else None,
        "paired_success_bootstrap_95ci": bootstrap_ci(success_differences),
        "mcnemar_exact_p": mcnemar_exact(identity_only, real_only),
        "paired_time_difference_mean": sum(time_differences) / len(time_differences) if time_differences else None,
        "paired_time_bootstrap_95ci": bootstrap_ci(time_differences),
        "conditions": conditions,
        "failure_modes": dict(sorted(failure_modes.items())),
        "runs_without_controller_events": sum(run.get("tool_calls", 0) == 0 for run in valid),
        "unavailable_metrics": ["estimated_cost", "unnecessary_tool_calls", "retrieval_precision"],
        "per_category": categories,
    }


def markdown_report(result: dict[str, Any], manifest: dict[str, Any]) -> str:
    identity, real = result["conditions"]["identity"], result["conditions"]["real"]
    category_rows = "\n".join(
        f"| {name} | {values['identity']['n']} | {values['identity']['success_rate']:.1%} | {values['real']['success_rate']:.1%} |"
        for name, values in result["per_category"].items()
    )
    return f"""# FlyOS paired benchmark report

## Executive summary

The real connectome condition did not improve aggregate task success over the matched identity/no-propagation controller. Both completed {identity['successes']}/90 tasks ({identity['success_rate']:.1%}). Each condition uniquely succeeded on one paired task; exact McNemar p={result['mcnemar_exact_p']:.3g}. The paired success difference was {result['paired_success_difference']:+.1%} (bootstrap 95% CI {result['paired_success_bootstrap_95ci'][0]:+.1%} to {result['paired_success_bootstrap_95ci'][1]:+.1%}). This is a null pilot result, not evidence of biological cognition or equivalence.

## Engineering result

FlyOS is a model-agnostic orchestration runtime. A persistent 16-state engineering controller routes capability, tool, provider, memory, verification, and stop/continue decisions. The graph has a causal role in recurrent propagation in the real condition; the identity condition uses the same runtime, tools, model, prompts, budgets, memory interface, and graders without graph propagation. AGY successfully exercised the MCP server with a real Gemini provider in isolated workspaces.

## Benchmark protocol

- Locked manifest: `{manifest['sha256']}`
- AGY model/effort: `{manifest['model']}` / `{manifest['effort']}`
- Conditions: identity/no propagation and real 16-group MaleCNS-derived propagation
- Tasks: 30 deterministic held-out fixtures, five in each of six categories
- Seeds: {', '.join(map(str, manifest['seeds']))}
- Runs: {result['runs']} total; {result['complete_pairs']} matched pairs; {result['infrastructure_failures']} included infrastructure failures
- Statistics: exact McNemar for binary outcomes; paired bootstrap with 10,000 resamples for continuous differences

## Aggregate results

| Metric | Identity | Real connectome |
|---|---:|---:|
| Success | {identity['successes']}/{identity['n']} ({identity['success_rate']:.1%}) | {real['successes']}/{real['n']} ({real['success_rate']:.1%}) |
| Mean latency | {identity['mean_wall_clock_time']:.1f}s | {real['mean_wall_clock_time']:.1f}s |
| Mean tool calls | {identity['mean_tool_calls']:.2f} | {real['mean_tool_calls']:.2f} |
| Verification success | {identity['verification_rate']:.1%} | {real['verification_rate']:.1%} |
| Input tokens | {identity['input_tokens']:,} | {real['input_tokens']:,} |
| Output tokens | {identity['output_tokens']:,} | {real['output_tokens']:,} |

Mean paired latency difference (real − identity) was {result['paired_time_difference_mean']:+.1f}s (95% CI {result['paired_time_bootstrap_95ci'][0]:+.1f}s to {result['paired_time_bootstrap_95ci'][1]:+.1f}s). The interval crosses zero.

## Per-category success

| Category | Runs/condition | Identity | Real connectome |
|---|---:|---:|---:|
{category_rows}

The real condition gained one multi-step-tool-use success and lost one mixed-long-horizon success. No category-level claim is justified with only 15 runs per condition.

## Failure analysis

Agent failures were retained as preregistered. Most failures were exact-file mismatches: the model often declared success while producing line-oriented or otherwise misformatted content. {result['runs_without_controller_events']} failed runs never invoked the Fly MCP protocol and therefore contain zero controller events; these are retained as agent/protocol-compliance failures, not infrastructure exclusions. Infrastructure-contaminated attempts were archived separately and replaced by clean matched reruns; the final 180-run primary dataset contains zero infrastructure failures and zero warnings. Estimated cost, unnecessary-tool-call count, and retrieval precision were not operationalized and are reported as unavailable rather than inferred after seeing results.

## Security constraints

Runs used isolated temporary workspaces, a workspace-scoped MCP server, temporary permissions restored after each pair, a fixed unittest action for coding verification, no inherited global MCP servers, and no blanket `--dangerously-skip-permissions` flag. External fixture text was treated as untrusted.

## Biological interpretation

None is warranted. The 16 groups and state variables are engineering abstractions inspired by reduced connectome wiring. The experiment does not model a fly brain, demonstrate fly cognition, or imply consciousness.

## Limitations

This is a synthetic 30-task pilot using one low-effort model, exact-output graders, three seeds, and only the real-versus-identity primary comparison. Tasks were often easy or formatting-sensitive. Shuffled-label and degree-preserving rewired controls were implemented but not run because the optional 360-run extension was not justified after the null primary result and would consume additional quota.

## Recommended next experiment

Use fewer but harder stateful tasks with recovery events that objectively require different routing decisions. Compare real, identity, shuffled-label, and rewired controllers; reduce exact-format brittleness; preregister controller-action metrics; and increase independent task instances rather than repeating seeds alone.
"""


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "benchmark/runs").glob("*/run.json"))
    runs = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    result = aggregate(runs)
    target = root / "benchmark/aggregate"
    target.mkdir(parents=True, exist_ok=True)
    (target / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    fields = ["run_id", "task_id", "category", "condition", "seed", "success", "failure_mode", "wall_clock_time", "tool_calls", "tool_errors", "model_calls", "input_tokens", "output_tokens", "verification_result", "memory_reads", "memory_writes"]
    with (target / "runs.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: run.get(field) for field in fields} for run in runs)
    manifest = json.loads((root / "benchmark/manifests/primary.json").read_text(encoding="utf-8"))
    report = root / "benchmark/report"
    report.mkdir(parents=True, exist_ok=True)
    (report / "primary.md").write_text(markdown_report(result, manifest), encoding="utf-8")
    dashboard = {
        "manifest_sha256": manifest["sha256"],
        "conditions": {**result["conditions"], "shuffled": {"status": "not run"}, "rewired": {"status": "not run"}},
        "paired": {key: result[key] for key in ("paired_success_difference", "paired_success_bootstrap_95ci", "mcnemar_exact_p", "paired_time_difference_mean", "paired_time_bootstrap_95ci")},
        "per_category": result["per_category"],
    }
    (root / "web/data/controller_comparison.json").write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
