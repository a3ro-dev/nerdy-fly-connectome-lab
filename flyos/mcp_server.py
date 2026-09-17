"""Minimal MCP 2025-11-25 stdio server for FlyOS."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .runtime import FlyRuntime


TOOLS = [
    {"name": "fly_create_task", "description": "Create an isolated FlyOS task.", "inputSchema": {"type": "object", "properties": {"task": {"type": "string"}, "budget": {"type": "integer", "minimum": 1, "maximum": 1000}, "run_id": {"type": "string"}}, "required": ["task"]}},
    {"name": "fly_observe", "description": "Feed an observation into recurrent controller state.", "inputSchema": {"type": "object", "properties": {"observation": {}}, "required": ["observation"]}},
    {"name": "fly_get_state", "description": "Read auditable controller and task state.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "fly_retrieve_memory", "description": "Retrieve a bounded set of transparent memories.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 0, "maximum": 20}, "reason": {"type": "string"}}, "required": ["query"]}},
    {"name": "fly_store_memory", "description": "Write an explicit memory event with provenance.", "inputSchema": {"type": "object", "properties": {"kind": {"enum": ["working", "episodic", "task", "persistent"]}, "content": {"type": "string"}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}, "source": {"type": "string"}, "provenance": {"type": "object"}, "reason": {"type": "string"}}, "required": ["kind", "content", "confidence", "source", "reason"]}},
    {"name": "fly_route", "description": "Compute controller-gated capability, provider, tool, and next-action scores.", "inputSchema": {"type": "object", "properties": {"requested": {"type": "string"}}}},
    {"name": "fly_delegate", "description": "Invoke the selected available model provider.", "inputSchema": {"type": "object", "properties": {"operation": {"enum": ["reason", "generate", "review", "inspect", "verify"]}, "context": {"type": "object"}}, "required": ["operation"]}},
    {"name": "fly_review", "description": "Delegate candidate review through the selected provider.", "inputSchema": {"type": "object", "properties": {"candidate": {"type": "string"}, "context": {"type": "object"}}, "required": ["candidate"]}},
    {"name": "fly_act", "description": "Verify a state transition and update reward/prediction error. For coding fixtures set verification_type=unittest to run the fixed safe unittest command in the workspace.", "inputSchema": {"type": "object", "properties": {"result": {"type": "object", "properties": {"state_changed": {"type": "boolean"}, "verified": {"type": "boolean"}, "verification_type": {"enum": ["unittest"]}}}}, "required": ["result"]}},
    {"name": "fly_get_status", "description": "Read task, providers, tools, state, and budget status.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "fly_get_trace", "description": "Read concise auditable events; no hidden chain-of-thought is stored.", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 200}}}},
]


class Server:
    def __init__(self, root: Path, condition: str, seed: int):
        self.runtime = FlyRuntime(root, condition, seed)

    def call(self, name: str, args: dict[str, Any]) -> Any:
        runtime = self.runtime
        if name == "fly_create_task": return runtime.create_task(args["task"], args.get("budget", 20), args.get("run_id"))
        if name == "fly_observe": return runtime.observe(args["observation"])
        if name in {"fly_get_state", "fly_get_status"}: return runtime.status()
        if name == "fly_retrieve_memory": return runtime.retrieve_memory(args["query"], args.get("limit", 4), args.get("reason", "task relevance"))
        if name == "fly_store_memory": return runtime.store_memory(args["kind"], args["content"], args["confidence"], args["source"], args.get("provenance", {}), args["reason"])
        if name == "fly_route": return runtime.route(args.get("requested"))
        if name == "fly_delegate": return runtime.delegate(args["operation"], args.get("context"))
        if name == "fly_review": return runtime.delegate("review", {**args.get("context", {}), "candidate": args["candidate"]})
        if name == "fly_act":
            result = dict(args["result"])
            if result.get("verification_type") == "unittest":
                completed = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=Path.cwd(), capture_output=True, text=True, timeout=60, shell=False)
                result.update({
                    "verified": completed.returncode == 0,
                    "verification_returncode": completed.returncode,
                    "verification_stdout": completed.stdout[-2000:],
                    "verification_stderr": completed.stderr[-2000:],
                })
            return runtime.update_result(result)
        if name == "fly_get_trace": return runtime.trace[-args.get("limit", 50):]
        raise KeyError(f"unknown tool: {name}")

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        identifier = message.get("id")
        method = message.get("method")
        if identifier is None:
            return None
        try:
            if method == "initialize":
                version = message.get("params", {}).get("protocolVersion", "2025-11-25")
                result = {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "nerdy-fly-agent", "version": "0.1.0"}, "instructions": "Use fly_create_task once, fly_observe and fly_route before decisions, and fly_act only with objectively observed state changes."}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = message.get("params", {})
                value = self.call(params["name"], params.get("arguments", {}))
                text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                result = {"content": [{"type": "text", "text": text}], "structuredContent": value, "isError": False}
            else:
                return {"jsonrpc": "2.0", "id": identifier, "error": {"code": -32601, "message": f"method not found: {method}"}}
            return {"jsonrpc": "2.0", "id": identifier, "result": result}
        except Exception as exc:
            if method == "tools/call":
                error = {"error": f"{type(exc).__name__}: {exc}"}
                return {"jsonrpc": "2.0", "id": identifier, "result": {"content": [{"type": "text", "text": json.dumps(error)}], "structuredContent": error, "isError": True}}
            return {"jsonrpc": "2.0", "id": identifier, "error": {"code": -32603, "message": f"{type(exc).__name__}: {exc}"}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("FLYOS_ROOT", Path(__file__).resolve().parents[1])))
    parser.add_argument("--condition", choices=("identity", "real", "shuffled", "rewired"), default=os.environ.get("FLYOS_CONDITION", "real"))
    parser.add_argument("--seed", type=int, default=int(os.environ.get("FLYOS_SEED", "0")))
    args = parser.parse_args()
    server = Server(args.root, args.condition, args.seed)
    for line in sys.stdin:
        try:
            message = json.loads(line)
            response = server.handle(message)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
        except Exception as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"{type(exc).__name__}: {exc}"}}, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
