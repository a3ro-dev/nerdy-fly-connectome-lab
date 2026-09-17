"""Deterministic graders and fixture materialization."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any


def safe_path(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"unsafe fixture path: {relative}")
    target = root.joinpath(*parts).resolve()
    if root.resolve() not in target.parents:
        raise ValueError(f"path escapes fixture: {relative}")
    return target


def materialize(task: dict[str, Any], workspace: Path) -> str:
    workspace.mkdir(parents=True, exist_ok=False)
    for relative, content in task["files"].items():
        path = safe_path(workspace, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
    return snapshot_hash(workspace)


def snapshot_hash(workspace: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in workspace.rglob("*") if item.is_file() and ".agents" not in item.parts):
        digest.update(path.relative_to(workspace).as_posix().encode() + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def grade(task: dict[str, Any], workspace: Path) -> dict[str, Any]:
    spec = task["grader"]
    if spec["type"] == "exact_files":
        checks = {}
        for relative, expected in spec["expected"].items():
            path = safe_path(workspace, relative)
            checks[relative] = path.exists() and path.read_text(encoding="utf-8") == expected
        return {"success": all(checks.values()), "checks": checks, "type": "exact_files"}
    if spec["type"] == "command":
        completed = subprocess.run(spec["command"], cwd=workspace, capture_output=True, text=True, timeout=60, shell=False)
        return {"success": completed.returncode == 0, "returncode": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:], "type": "command"}
    raise ValueError(f"unknown grader type: {spec['type']}")
