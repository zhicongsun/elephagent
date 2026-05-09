#!/usr/bin/env python3
"""Small MCP server for repository-local agent memory.

It exposes .agent/memory as MCP resources and a few tools:
- agent_memory_read
- agent_memory_search
- agent_memory_append
- agent_tool_registry
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any


SERVER_VERSION = "0.1.0"


def find_root() -> Path:
    start = Path(os.environ.get("AGENT_KIT_ROOT", os.getcwd())).resolve()
    for path in [start, *start.parents]:
        if (path / ".agent").is_dir():
            return path
    return start


ROOT = find_root()
AGENT_DIR = ROOT / ".agent"
MEMORY_DIR = AGENT_DIR / "memory"
REGISTRY_PATH = AGENT_DIR / "tools" / "registry.json"


def memory_files() -> list[Path]:
    if not MEMORY_DIR.exists():
        return []
    return sorted(
        path
        for path in MEMORY_DIR.rglob("*.md")
        if path.is_file() and ".git" not in path.parts
    )


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_memory(name: str | None = None) -> str:
    files = memory_files()
    if name:
        normalized = name.replace("\\", "/").strip("/")
        candidates = [
            MEMORY_DIR / normalized,
            MEMORY_DIR / f"{normalized}.md",
            ROOT / normalized,
        ]
        for candidate in candidates:
            candidate = candidate.resolve()
            if candidate.is_file() and MEMORY_DIR.resolve() in [candidate.parent, *candidate.parents]:
                return f"# {rel(candidate)}\n\n{read_text(candidate)}"
        raise ValueError(f"Memory file not found: {name}")

    chunks = []
    for path in files:
        chunks.append(f"# {rel(path)}\n\n{read_text(path).strip()}")
    return "\n\n---\n\n".join(chunks) if chunks else "No memory files found."


def search_memory(query: str, limit: int = 20) -> str:
    needle = query.lower().strip()
    if not needle:
        raise ValueError("query is required")

    matches = []
    for path in memory_files():
        for lineno, line in enumerate(read_text(path).splitlines(), start=1):
            if needle in line.lower():
                matches.append(f"{rel(path)}:{lineno}: {line}")
                if len(matches) >= limit:
                    return "\n".join(matches)
    return "\n".join(matches) if matches else "No matches."


def append_memory(note: str, topic: str = "log") -> str:
    if not note.strip():
        raise ValueError("note is required")

    today = dt.date.today().isoformat()
    if topic == "log":
        path = MEMORY_DIR / "log" / f"{today}.md"
    else:
        safe_topic = topic.strip().lower().replace(" ", "-")
        path = MEMORY_DIR / f"{safe_topic}.md"

    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"# {path.stem}\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {note.strip()}\n")
    return f"Appended to {rel(path)}. Run `python3 agent_kit.py build` to refresh generated adapter files."


def read_registry() -> str:
    if not REGISTRY_PATH.exists():
        return "No tool registry found."
    return read_text(REGISTRY_PATH)


def tool_list() -> list[dict[str, Any]]:
    return [
        {
            "name": "agent_memory_read",
            "description": "Read repository-local shared agent memory. Omit file to read all memory files.",
            "inputSchema": {
                "type": "object",
                "properties": {"file": {"type": "string"}},
                "additionalProperties": False,
            },
        },
        {
            "name": "agent_memory_search",
            "description": "Search repository-local shared agent memory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "agent_memory_append",
            "description": "Append a durable note to repository-local shared agent memory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "note": {"type": "string"},
                    "topic": {"type": "string", "description": "log, decisions, workflows, pitfalls, glossary, or a custom file stem"},
                },
                "required": ["note"],
                "additionalProperties": False,
            },
        },
        {
            "name": "agent_tool_registry",
            "description": "Read the repository-local MCP tool registry.",
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "agent_memory_read":
        return read_memory(arguments.get("file"))
    if name == "agent_memory_search":
        return search_memory(str(arguments["query"]), int(arguments.get("limit", 20)))
    if name == "agent_memory_append":
        return append_memory(str(arguments["note"]), str(arguments.get("topic", "log")))
    if name == "agent_tool_registry":
        return read_registry()
    raise ValueError(f"Unknown tool: {name}")


def resources_list() -> list[dict[str, str]]:
    return [
        {
            "uri": f"agent-memory://{rel(path)}",
            "name": rel(path),
            "description": "Repository-local agent memory",
            "mimeType": "text/markdown",
        }
        for path in memory_files()
    ]


def resource_read(uri: str) -> dict[str, str]:
    prefix = "agent-memory://"
    if not uri.startswith(prefix):
        raise ValueError(f"Unsupported resource URI: {uri}")
    path = (ROOT / uri[len(prefix) :]).resolve()
    if not path.is_file() or MEMORY_DIR.resolve() not in [path.parent, *path.parents]:
        raise ValueError(f"Resource not found: {uri}")
    return {"uri": uri, "mimeType": "text/markdown", "text": read_text(path)}


def response(msg_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    return payload


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}

    if method == "notifications/initialized":
        return None

    try:
        if method == "initialize":
            return response(
                msg_id,
                {
                    "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                    "capabilities": {"tools": {}, "resources": {}},
                    "serverInfo": {"name": "agent-kit", "version": SERVER_VERSION},
                },
            )
        if method == "tools/list":
            return response(msg_id, {"tools": tool_list()})
        if method == "tools/call":
            text = call_tool(str(params["name"]), params.get("arguments") or {})
            return response(msg_id, {"content": [{"type": "text", "text": text}]})
        if method == "resources/list":
            return response(msg_id, {"resources": resources_list()})
        if method == "resources/read":
            return response(msg_id, {"contents": [resource_read(str(params["uri"]))]})
        return response(msg_id, error={"code": -32601, "message": f"Method not found: {method}"})
    except Exception as exc:
        return response(msg_id, error={"code": -32000, "message": str(exc)})


def iter_messages() -> Any:
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            break
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith(b"content-length:"):
            length = int(stripped.split(b":", 1)[1].strip())
            while True:
                header = sys.stdin.buffer.readline()
                if header in (b"\r\n", b"\n", b""):
                    break
            body = sys.stdin.buffer.read(length)
            yield json.loads(body.decode("utf-8"))
        else:
            yield json.loads(stripped.decode("utf-8"))


def send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    for message in iter_messages():
        result = handle(message)
        if result is not None:
            send(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
