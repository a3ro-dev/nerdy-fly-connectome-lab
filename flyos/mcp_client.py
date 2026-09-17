"""Small MCP stdio client for explicitly configured external tool servers."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class MCPStdioClient:
    """Consume MCP tools without a shell or model-generated command line."""

    def __init__(self, command: list[str], cwd: Path | None = None):
        if not command:
            raise ValueError("an explicit server command is required")
        self.command = list(command)
        self.cwd = cwd
        self.process: subprocess.Popen[str] | None = None
        self.next_id = 1

    def start(self) -> "MCPStdioClient":
        self.process = subprocess.Popen(
            self.command, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1, shell=False,
        )
        self.request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "flyos", "version": "0.1.0"}})
        return self

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("MCP client is not started")
        identifier = self.next_id
        self.next_id += 1
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}) + "\n")
        self.process.stdin.flush()
        while line := self.process.stdout.readline():
            response = json.loads(line)
            if response.get("id") != identifier:
                continue
            if "error" in response:
                raise RuntimeError(response["error"].get("message", "MCP request failed"))
            return response["result"]
        raise RuntimeError("MCP server closed the connection")

    def list_tools(self) -> list[dict[str, Any]]:
        return self.request("tools/list", {})["tools"]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self) -> None:
        if not self.process:
            return
        process = self.process
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if process.stdin:
            process.stdin.close()
        if process.stdout:
            process.stdout.close()
        self.process = None

    def __enter__(self) -> "MCPStdioClient":
        return self.start()

    def __exit__(self, *_: object) -> None:
        self.close()
