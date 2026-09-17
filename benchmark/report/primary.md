# FlyOS paired benchmark report

## Executive summary

The real connectome condition did not improve aggregate task success over the matched identity/no-propagation controller. Both completed 65/90 tasks (72.2%). Each condition uniquely succeeded on one paired task; exact McNemar p=1. The paired success difference was +0.0% (bootstrap 95% CI -3.3% to +3.3%). This is a null pilot result, not evidence of biological cognition or equivalence.

## Engineering result

FlyOS is a model-agnostic orchestration runtime. A persistent 16-state engineering controller routes capability, tool, provider, memory, verification, and stop/continue decisions. The graph has a causal role in recurrent propagation in the real condition; the identity condition uses the same runtime, tools, model, prompts, budgets, memory interface, and graders without graph propagation. AGY successfully exercised the MCP server with a real Gemini provider in isolated workspaces.

## Benchmark protocol

- Locked manifest: `04420dac4c59e6f595cf34d6bda99c3a2beb890b3f6a630cb7e1737283a7ade6`
- AGY model/effort: `gemini-3.8-flash-low` / `low`
- Conditions: identity/no propagation and real 16-group MaleCNS-derived propagation
- Tasks: 30 deterministic held-out fixtures, five in each of six categories
- Seeds: 101, 202, 303
- Runs: 180 total; 90 matched pairs; 0 included infrastructure failures
- Statistics: exact McNemar for binary outcomes; paired bootstrap with 10,000 resamples for continuous differences

## Aggregate results

| Metric | Identity | Real connectome |
|---|---:|---:|
| Success | 65/90 (72.2%) | 65/90 (72.2%) |
| Mean latency | 89.4s | 88.0s |
| Mean tool calls | 6.73 | 6.96 |
| Verification success | 72.2% | 72.2% |
| Input tokens | 12,999,741 | 13,291,102 |
| Output tokens | 145,385 | 150,479 |

Mean paired latency difference (real − identity) was -1.4s (95% CI -7.7s to +3.5s). The interval crosses zero.

## Per-category success

| Category | Runs/condition | Identity | Real connectome |
|---|---:|---:|---:|
| coding_debugging | 15 | 100.0% | 100.0% |
| data_file_analysis | 15 | 46.7% | 46.7% |
| mixed_long_horizon | 15 | 66.7% | 60.0% |
| multi_step_tool_use | 15 | 80.0% | 86.7% |
| planning_verification_recovery | 15 | 80.0% | 80.0% |
| research_retrieval | 15 | 60.0% | 60.0% |

The real condition gained one multi-step-tool-use success and lost one mixed-long-horizon success. No category-level claim is justified with only 15 runs per condition.

## Failure analysis

Agent failures were retained as preregistered. Most failures were exact-file mismatches: the model often declared success while producing line-oriented or otherwise misformatted content. 16 failed runs never invoked the Fly MCP protocol and therefore contain zero controller events; these are retained as agent/protocol-compliance failures, not infrastructure exclusions. Infrastructure-contaminated attempts were archived separately and replaced by clean matched reruns; the final 180-run primary dataset contains zero infrastructure failures and zero warnings. Estimated cost, unnecessary-tool-call count, and retrieval precision were not operationalized and are reported as unavailable rather than inferred after seeing results.

## Security constraints

Runs used isolated temporary workspaces, a workspace-scoped MCP server, temporary permissions restored after each pair, a fixed unittest action for coding verification, no inherited global MCP servers, and no blanket `--dangerously-skip-permissions` flag. External fixture text was treated as untrusted.

## Biological interpretation

None is warranted. The 16 groups and state variables are engineering abstractions inspired by reduced connectome wiring. The experiment does not model a fly brain, demonstrate fly cognition, or imply consciousness.

## Limitations

This is a synthetic 30-task pilot using one low-effort model, exact-output graders, three seeds, and only the real-versus-identity primary comparison. Tasks were often easy or formatting-sensitive. Shuffled-label and degree-preserving rewired controls were implemented but not run because the optional 360-run extension was not justified after the null primary result and would consume additional quota.

## Recommended next experiment

Use fewer but harder stateful tasks with recovery events that objectively require different routing decisions. Compare real, identity, shuffled-label, and rewired controllers; reduce exact-format brittleness; preregister controller-action metrics; and increase independent task instances rather than repeating seeds alone.
