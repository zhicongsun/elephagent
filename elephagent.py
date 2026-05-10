#!/usr/bin/env python3
"""Project-local agent memory and tool adapter.

The source of truth lives in .agent/. This CLI renders the files that Codex,
Claude Code, and Cursor already know how to read.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any


VERSION = "0.1.1"

MEMORY_FILES = [
    ".agent/memory/index.md",
    ".agent/memory/decisions.md",
    ".agent/memory/workflows.md",
    ".agent/memory/pitfalls.md",
    ".agent/memory/glossary.md",
]

GENERATED_PATHS = {
    "codex_agents": "AGENTS.md",
    "claude_memory": "CLAUDE.md",
    "cursor_rule": ".cursor/rules/agent-memory.mdc",
    "claude_mcp": ".mcp.json",
    "cursor_mcp": ".cursor/mcp.json",
    "codex_mcp": ".codex/config.toml",
}

SKILLS_DIR = ".agent/skills"
CLAUDE_SKILLS_DIR = ".claude/skills"
CURSOR_SKILLS_DIR = ".cursor/rules"

DEFAULT_REMEMBER_SKILL = """\
# Remember

Use this skill to save valuable information from the current conversation to shared agent memory.

## When to invoke

- The user says "help me remember", "save this", "记下来", or similar
- A decision, workflow, pitfall, or term worth preserving surfaces in conversation

## Steps

1. Identify the topic: `decisions`, `workflows`, `pitfalls`, `glossary`, or `log` (default)
2. Call MCP tool `agent_memory_append` with the note and topic
3. Run `elephagent build` so all platform adapters are updated
4. Confirm to the user what was saved and where

## Topic guide

| Topic | When to use |
|-------|-------------|
| decisions | Architecture or tech choices |
| workflows | Repeatable processes |
| pitfalls | Mistakes to avoid |
| glossary | Project-specific terms |
| log | General observations (default) |
"""

DEFAULT_INIT_MEMORY_SKILL = """\
# Init Memory

Use this skill to initialize the shared agent memory system in the current project.

## When to invoke

- The user says "initialize memory sharing", "set up agent memory", "init memory", or similar
- The `.agent/` directory does not exist yet in the project

## Steps

1. Run `elephagent init` in the project root
2. Report which files were created
3. Remind the user to commit `.agent/`, `CLAUDE.md`, `AGENTS.md`, and `.cursor/` to Git so teammates can share the memory

## Notes

- Safe to run multiple times; existing files are not overwritten unless `--force` is passed
- If `.agent/` already exists, tell the user and skip
"""

DEFAULT_CHECK_MEMORY_SKILL = """\
# Check Memory

Use this skill to check the health of the shared agent memory system.

## When to invoke

- The user says "check memory", "memory status", "check memory setup", "doctor", or similar
- Something seems wrong with memory loading or generated files are missing

## Steps

1. Run `elephagent doctor` in the project root
2. Read the output and summarize:
   - Which checks passed (`[ok]`)
   - Which checks warned (`[warn]`) — explain what the warning means and how to fix it
   - Which checks failed (`[fail]`) — tell the user exactly what to do
3. If everything is OK, confirm the setup is healthy

## Notes

- `[warn]` items are non-blocking but worth fixing (e.g. missing Git remote, potential secret in env)
- `[fail]` items mean something is broken and must be resolved before memory syncing works
"""

DEFAULT_SYNC_MEMORY_SKILL = """\
# Sync Memory

Use this skill to commit and push the latest agent memory and tool changes to Git.

## When to invoke

- The user says "sync memory", "push memory", "share memory with team", or similar
- After a session where new memories were added and the user wants to persist them

## Steps

1. Run `elephagent sync` in the project root
2. Report what was committed and whether the push succeeded
3. If `--no-push` is needed (e.g. no remote configured), run `elephagent sync --no-push` instead

## Notes

- `sync` runs `build` first, then `git add`, `git pull --rebase`, `git commit`, and `git push`
- If there is nothing new to commit, the command exits cleanly with a message
- Merge conflicts in `.agent/memory/` files must be resolved manually before retrying
"""

DEFAULT_ADD_SKILL_SKILL = """\
# Add Skill

Use this skill to create a new shared agent skill available across Claude Code, Cursor, and Codex.

## When to invoke

- The user says "add skill <name>", "create skill <name>", "new skill <name>", or similar

## Steps

1. Extract the skill name from the user's message (lowercase, hyphens for spaces)
2. Run `elephagent skill add <name>` in the project root
3. Open `.agent/skills/<name>.md` and help the user fill in:
   - **When to invoke**: what phrases or situations trigger this skill
   - **Steps**: the exact actions the AI should take
   - **Notes**: edge cases or caveats
4. Run `elephagent build` to generate platform files
5. Tell the user the skill is now available as `/<name>` in Claude Code

## Notes

- The skill name becomes the slash command in Claude Code (e.g. `add-skill` → `/add-skill`)
- Use `--force` to overwrite an existing skill: `elephagent skill add <name> --force`
- After editing, always run `build` to keep Cursor and Codex in sync
"""

DEFAULT_SKILLS: dict[str, str] = {
    "init-memory": DEFAULT_INIT_MEMORY_SKILL,
    "remember": DEFAULT_REMEMBER_SKILL,
    "check-memory": DEFAULT_CHECK_MEMORY_SKILL,
    "sync-memory": DEFAULT_SYNC_MEMORY_SKILL,
    "add-skill": DEFAULT_ADD_SKILL_SKILL,
}

DEFAULT_MCP_SERVER = {
    "type": "stdio",
    "command": "python3",
    "args": [".agent/tools/mcp_server.py"],
    "env": {},
    "env_vars": [],
}

DEFAULT_MCP_SERVER_SOURCE = r'''#!/usr/bin/env python3
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


SERVER_VERSION = "0.1.1"


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
    return f"Appended to {rel(path)}. Run `elephagent build` to refresh generated adapter files."


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
                    "serverInfo": {"name": "elephagent", "version": SERVER_VERSION},
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
'''


def find_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        if (path / ".agent").is_dir():
            return path
    for path in [current, *current.parents]:
        if (path / ".git").exists():
            return path
    return current


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == content:
                return
        except OSError:
            pass
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def write_if_missing(path: Path, content: str, force: bool = False) -> bool:
    if path.exists() and not force:
        return False
    write_text(path, content)
    return True


def default_config(root: Path) -> dict[str, Any]:
    return {
        "version": 1,
        "project_name": root.name,
        "memory_files": MEMORY_FILES,
        "memory_snapshot_max_bytes": 40000,
        "generated": GENERATED_PATHS,
    }


def default_registry() -> dict[str, Any]:
    return {
        "version": 1,
        "mcpServers": {
            "agent-memory": DEFAULT_MCP_SERVER,
        },
    }


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def load_config(root: Path) -> dict[str, Any]:
    config = default_config(root)
    user_config = read_json(root / ".agent" / "config.json", {})
    config.update(user_config)
    config.setdefault("generated", {}).update(user_config.get("generated", {}))
    return config


def load_registry(root: Path) -> dict[str, Any]:
    registry = read_json(root / ".agent" / "tools" / "registry.json", default_registry())
    registry.setdefault("version", 1)
    registry.setdefault("mcpServers", {})
    registry["mcpServers"].setdefault("agent-memory", DEFAULT_MCP_SERVER)
    return registry


def create_default_memory(root: Path, force: bool = False) -> list[str]:
    files = {
        ".agent/memory/index.md": """# Agent Memory Index

This directory is the platform-neutral source of truth for coding agents working in this repository.

## How Agents Should Use This

- Read this file first when starting work in the repository.
- Search the rest of `.agent/memory/` when architecture, workflows, decisions, pitfalls, or terminology matter.
- Add durable notes with `elephagent remember "..."`.
- Do not store secrets, tokens, credentials, or private machine paths in shared memory.

## Current Project Notes

- The shared memory and tool layer is managed by `elephagent.py`.
- Generated platform files are derived from `.agent/`.
""",
        ".agent/memory/decisions.md": """# Decisions

Record durable architecture and workflow decisions here.
""",
        ".agent/memory/workflows.md": """# Workflows

Record repeatable project workflows here.

## Agent Memory Workflow

1. Edit `.agent/memory/*.md` or run `elephagent remember "..."`.
2. Run `elephagent build`.
3. Commit `.agent/` and the generated adapter files.
""",
        ".agent/memory/pitfalls.md": """# Pitfalls

Record mistakes agents should avoid repeating here.
""",
        ".agent/memory/glossary.md": """# Glossary

Record project-specific terms here.
""",
    }

    written = []
    for name, content in files.items():
        if write_if_missing(root / name, content, force=force):
            written.append(name)
    (root / ".agent" / "memory" / "log").mkdir(parents=True, exist_ok=True)
    return written


def init_command(args: argparse.Namespace) -> int:
    root = find_root()
    if not (root / ".git").exists():
        print("No Git repository detected. Initializing one now...")
        subprocess.run(["git", "init"], cwd=root, capture_output=True, check=True)
        print("Git repository initialized.")
    (root / ".agent" / "tools").mkdir(parents=True, exist_ok=True)
    (root / ".cursor" / "rules").mkdir(parents=True, exist_ok=True)
    (root / ".codex").mkdir(parents=True, exist_ok=True)

    created = []
    if write_if_missing(root / ".agent" / "config.json", json.dumps(default_config(root), indent=2) + "\n", args.force):
        created.append(".agent/config.json")
    if write_if_missing(root / ".agent" / "tools" / "registry.json", json.dumps(default_registry(), indent=2) + "\n", args.force):
        created.append(".agent/tools/registry.json")
    if write_if_missing(root / ".agent" / "tools" / "mcp_server.py", DEFAULT_MCP_SERVER_SOURCE, args.force):
        created.append(".agent/tools/mcp_server.py")
    if write_if_missing(root / ".agent" / ".gitignore", "local/\n*.secret.*\n.env\n", args.force):
        created.append(".agent/.gitignore")
    gitattributes_content = (
        "# Append-only memory files: keep all lines from both sides on conflict.\n"
        ".agent/memory/*.md merge=union\n"
        ".agent/memory/log/*.md merge=union\n"
    )
    if write_if_missing(root / ".gitattributes", gitattributes_content, args.force):
        created.append(".gitattributes")
    created.extend(create_default_memory(root, force=args.force))

    skills_dir = root / SKILLS_DIR
    skills_dir.mkdir(parents=True, exist_ok=True)
    for skill_name, skill_content in DEFAULT_SKILLS.items():
        skill_path = skills_dir / f"{skill_name}.md"
        if write_if_missing(skill_path, skill_content, args.force):
            created.append(f"{SKILLS_DIR}/{skill_name}.md")

    if not args.no_build:
        build_command(args)

    if created:
        print("Created:")
        for item in created:
            print(f"  {item}")
    else:
        print("Agent kit layout already exists.")
    return 0


def memory_snapshot(root: Path, config: dict[str, Any]) -> str:
    limit = int(config.get("memory_snapshot_max_bytes", 40000))
    chunks: list[str] = []
    total = 0
    for item in config.get("memory_files", MEMORY_FILES):
        path = root / item
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").strip()
        chunk = f"### {item}\n\n{text}\n"
        if total + len(chunk.encode("utf-8")) > limit:
            chunks.append("\n_Additional memory omitted because `memory_snapshot_max_bytes` was reached._\n")
            break
        chunks.append(chunk)
        total += len(chunk.encode("utf-8"))
    return "\n".join(chunks).strip() or "_No memory files found._"


def generated_notice() -> str:
    return "> Generated by `elephagent build`. Edit `.agent/` instead of this file."


def render_claude_skill(skill_name: str, content: str) -> str:
    first_line = content.splitlines()[0].lstrip("# ").strip() if content.strip() else skill_name
    return f"---\nname: {skill_name}\ndescription: {first_line}\n---\n\n{content}"


def render_cursor_skill(skill_name: str, content: str) -> str:
    first_line = content.splitlines()[0].lstrip("# ").strip() if content.strip() else skill_name
    return f"""---
description: "{first_line}"
globs: ""
alwaysApply: false
---

{generated_notice()}

{content.strip()}
"""


def render_agents_skills_section(root: Path) -> str:
    skills_dir = root / SKILLS_DIR
    if not skills_dir.exists():
        return ""
    skill_files = sorted(skills_dir.glob("*.md"))
    if not skill_files:
        return ""
    chunks = ["## Skills\n"]
    for skill_file in skill_files:
        content = skill_file.read_text(encoding="utf-8").strip()
        chunks.append(f"### {skill_file.stem}\n\n{content}\n")
    return "\n".join(chunks)


def render_agents_md(root: Path, config: dict[str, Any]) -> str:
    skills_section = render_agents_skills_section(root)
    skills_block = f"\n{skills_section}\n" if skills_section else ""
    return f"""# AGENTS.md

{generated_notice()}

## Shared Agent Home

This repository stores platform-neutral agent memory and tool definitions under `.agent/`.

When working here:

- Read `.agent/memory/index.md` before making changes.
- Search `.agent/memory/` for decisions, workflows, pitfalls, and terms before assuming project conventions.
- Use MCP tools generated from `.agent/tools/registry.json` when your client supports MCP.
- Treat `.agent/` as version-controlled shared context.
- Do not store secrets, tokens, credentials, or private machine paths in `.agent/`.
- Add durable discoveries with `elephagent remember "..."`, then run `elephagent build`.
{skills_block}
## Memory Snapshot

{memory_snapshot(root, config)}
"""


def render_claude_md(config: dict[str, Any]) -> str:
    imports = "\n".join(f"@{path}" for path in config.get("memory_files", MEMORY_FILES))
    return f"""# CLAUDE.md

{generated_notice()}

This repository uses `.agent/` as the shared, Git-synced memory and tool layer for Claude Code, Codex, Cursor, and other agents.

Follow these rules:

- Read the imported memory files before making durable project assumptions.
- Use `.mcp.json` for project-scoped MCP tools.
- Add lasting notes with `elephagent remember "..."`, then run `elephagent build`.
- Never write secrets into `.agent/`.

## Imported Shared Memory

{imports}
"""


def render_cursor_rule(root: Path, config: dict[str, Any]) -> str:
    return f"""---
description: "Shared repository agent memory and tool workflow."
globs: ""
alwaysApply: true
---

# Shared Agent Home

{generated_notice()}

This repository stores platform-neutral agent memory and tool definitions under `.agent/`.

- Read `.agent/memory/index.md` before making changes.
- Search `.agent/memory/` for decisions, workflows, pitfalls, and project terminology.
- Use `.cursor/mcp.json` for project-scoped MCP tools.
- Add durable discoveries with `elephagent remember "..."`, then run `elephagent build`.
- Never write secrets into `.agent/`.

## Memory Snapshot

{memory_snapshot(root, config)}
"""


def as_env_reference(name: str, platform: str) -> str:
    if platform == "cursor":
        return f"${{env:{name}}}"
    return f"${{{name}}}"


def render_mcp_json(registry: dict[str, Any], platform: str) -> dict[str, Any]:
    servers: dict[str, Any] = {}
    for name, server in registry.get("mcpServers", {}).items():
        server_type = server.get("type", "stdio")
        rendered: dict[str, Any] = {}

        if server_type in ("http", "streamable-http"):
            rendered["type"] = "http"
            rendered["url"] = server["url"]
            if server.get("headers"):
                rendered["headers"] = dict(server["headers"])
            if server.get("bearer_token_env_var"):
                token = as_env_reference(server["bearer_token_env_var"], platform)
                rendered.setdefault("headers", {})["Authorization"] = f"Bearer {token}"
        else:
            rendered["command"] = server["command"]
            args = list(server.get("args", []))
            if platform == "cursor":
                args = [
                    arg.replace(".agent/", "${workspaceFolder}/.agent/", 1)
                    if isinstance(arg, str) and arg.startswith(".agent/")
                    else arg
                    for arg in args
                ]
            rendered["args"] = args
            env = dict(server.get("env", {}))
            for env_name in server.get("env_vars", []):
                env[env_name] = as_env_reference(env_name, platform)
            if env:
                rendered["env"] = env

        servers[name] = rendered

    return {"mcpServers": servers}


def toml_string(value: str) -> str:
    return json.dumps(value)


def toml_array(values: list[str]) -> str:
    return "[" + ", ".join(toml_string(str(value)) for value in values) + "]"


def render_codex_toml(registry: dict[str, Any]) -> str:
    lines = [
        "# Generated by `elephagent build`. Edit `.agent/tools/registry.json` instead.",
        "",
    ]
    for name, server in registry.get("mcpServers", {}).items():
        table = f'mcp_servers.{toml_string(name)}'
        lines.append(f"[{table}]")
        server_type = server.get("type", "stdio")
        if server_type in ("http", "streamable-http"):
            lines.append(f"url = {toml_string(server['url'])}")
            if server.get("bearer_token_env_var"):
                lines.append(f"bearer_token_env_var = {toml_string(server['bearer_token_env_var'])}")
            if server.get("headers"):
                header_items = ", ".join(
                    f"{toml_string(str(key))} = {toml_string(str(value))}"
                    for key, value in server["headers"].items()
                )
                lines.append(f"http_headers = {{ {header_items} }}")
        else:
            lines.append(f"command = {toml_string(server['command'])}")
            if server.get("args"):
                lines.append(f"args = {toml_array(server['args'])}")
            if server.get("env_vars"):
                lines.append(f"env_vars = {toml_array(server['env_vars'])}")
            if server.get("env"):
                lines.append("")
                lines.append(f"[{table}.env]")
                for key, value in server["env"].items():
                    lines.append(f"{key} = {toml_string(str(value))}")
        lines.append("")
    return "\n".join(lines)


def build_command(args: argparse.Namespace) -> int:
    root = find_root()
    if not (root / ".agent").exists():
        print("No .agent directory found. Run `elephagent init` first.", file=sys.stderr)
        return 1

    config = load_config(root)
    registry = load_registry(root)
    generated = config.get("generated", GENERATED_PATHS)

    outputs = {
        generated.get("codex_agents", "AGENTS.md"): render_agents_md(root, config),
        generated.get("claude_memory", "CLAUDE.md"): render_claude_md(config),
        generated.get("cursor_rule", ".cursor/rules/agent-memory.mdc"): render_cursor_rule(root, config),
        generated.get("claude_mcp", ".mcp.json"): json.dumps(render_mcp_json(registry, "claude"), indent=2) + "\n",
        generated.get("cursor_mcp", ".cursor/mcp.json"): json.dumps(render_mcp_json(registry, "cursor"), indent=2) + "\n",
        generated.get("codex_mcp", ".codex/config.toml"): render_codex_toml(registry),
    }

    fallbacks: list[tuple[str, str]] = []
    for path_name, content in outputs.items():
        try:
            write_text(root / path_name, content)
        except PermissionError:
            fallback_name = path_name.replace("/", "__")
            fallback = root / ".agent" / "generated" / fallback_name
            write_text(fallback, content)
            fallbacks.append((path_name, rel(root, fallback)))

    skill_outputs: list[str] = []
    skills_dir = root / SKILLS_DIR
    if skills_dir.exists():
        for skill_file in sorted(skills_dir.glob("*.md")):
            skill_name = skill_file.stem
            content = skill_file.read_text(encoding="utf-8")
            claude_path = root / CLAUDE_SKILLS_DIR / skill_name / "SKILL.md"
            cursor_path = root / CURSOR_SKILLS_DIR / f"{skill_name}.mdc"
            write_text(claude_path, render_claude_skill(skill_name, content))
            write_text(cursor_path, render_cursor_skill(skill_name, content))
            skill_outputs.append(f"{CLAUDE_SKILLS_DIR}/{skill_name}/SKILL.md")
            skill_outputs.append(f"{CURSOR_SKILLS_DIR}/{skill_name}.mdc")

    print("Generated adapter files:")
    for path_name in outputs:
        print(f"  {path_name}")
    for path_name in skill_outputs:
        print(f"  {path_name}")
    for original, fallback in fallbacks:
        print(f"  warning: could not write {original}; wrote fallback {fallback}", file=sys.stderr)
    return 0


def remember_command(args: argparse.Namespace) -> int:
    root = find_root()
    if not (root / ".agent").exists():
        print("No .agent directory found. Creating one first.")
        init_args = argparse.Namespace(force=False, no_build=True)
        init_command(init_args)

    today = dt.date.today().isoformat()
    note = " ".join(args.note).strip()
    if not note:
        print("Nothing to remember.", file=sys.stderr)
        return 1

    topic = args.topic
    if topic == "log":
        path = root / ".agent" / "memory" / "log" / f"{today}.md"
    else:
        path = root / ".agent" / "memory" / f"{topic}.md"

    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        write_text(path, f"# {path.stem}\n\n")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {note}\n")

    index_path = root / ".agent" / "memory" / "index.md"
    if index_path.exists():
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n- {today}: {note}\n")

    if not args.no_build:
        build_command(args)

    print(f"Remembered in {rel(root, path)}")
    return 0


def skill_add_command(args: argparse.Namespace) -> int:
    root = find_root()
    if not (root / ".agent").exists():
        init_command(argparse.Namespace(force=False, no_build=True))

    skill_name = args.name.strip().lower().replace(" ", "-")
    skill_path = root / SKILLS_DIR / f"{skill_name}.md"

    if skill_path.exists() and not args.force:
        print(f"Skill already exists: {rel(root, skill_path)}. Use --force to overwrite.", file=sys.stderr)
        return 1

    if skill_name == "remember":
        content = DEFAULT_REMEMBER_SKILL
    else:
        content = f"# {skill_name.capitalize()}\n\nDescribe when and how to use this skill.\n\n## Steps\n\n1. Step one\n2. Step two\n"

    write_text(skill_path, content)
    print(f"Created skill: {rel(root, skill_path)}")

    if not args.no_build:
        build_command(args)
    return 0


def tool_add_command(args: argparse.Namespace) -> int:
    root = find_root()
    if not (root / ".agent").exists():
        init_command(argparse.Namespace(force=False, no_build=True))
    registry_path = root / ".agent" / "tools" / "registry.json"
    registry = load_registry(root)

    if args.url:
        server: dict[str, Any] = {"type": "http", "url": args.url}
        if args.bearer_token_env_var:
            server["bearer_token_env_var"] = args.bearer_token_env_var
    else:
        if not args.command:
            print("Provide --command for stdio tools or --url for HTTP tools.", file=sys.stderr)
            return 1
        server = {
            "type": "stdio",
            "command": args.command,
            "args": args.arg or [],
            "env": dict(item.split("=", 1) for item in (args.env or [])),
            "env_vars": args.env_var or [],
        }

    registry.setdefault("mcpServers", {})[args.name] = server
    write_json(registry_path, registry)
    if not args.no_build:
        build_command(args)
    print(f"Added MCP server `{args.name}`.")
    return 0


def tool_list_command(args: argparse.Namespace) -> int:
    root = find_root()
    registry = load_registry(root)
    for name, server in registry.get("mcpServers", {}).items():
        if server.get("type") in ("http", "streamable-http"):
            print(f"{name}: http {server.get('url')}")
        else:
            cmd = " ".join([server.get("command", ""), *server.get("args", [])])
            print(f"{name}: stdio {cmd}".rstrip())
    return 0


def sync_command(args: argparse.Namespace) -> int:
    root = find_root()
    if not (root / ".git").exists():
        print("This folder is not a Git repository. Run `git init` and add a remote before `elephagent.py sync`.", file=sys.stderr)
        return 1
    build_command(args)
    message = args.message or "Sync agent memory and tools"
    tracked = [
        ".agent",
        "AGENTS.md",
        "CLAUDE.md",
        ".cursor",
        ".codex",
        ".mcp.json",
    ]

    result = subprocess.run(["git", "add", *tracked], cwd=root)
    if result.returncode != 0:
        return result.returncode

    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root)
    if diff.returncode == 0:
        print("No agent memory or tool changes to commit.")
    else:
        result = subprocess.run(["git", "commit", "-m", message], cwd=root)
        if result.returncode != 0:
            return result.returncode

    has_upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=root,
        capture_output=True,
    ).returncode == 0

    if has_upstream:
        result = subprocess.run(["git", "pull", "--rebase"], cwd=root)
        if result.returncode != 0:
            return result.returncode

    if not args.no_push:
        return subprocess.run(["git", "push"], cwd=root).returncode
    return 0


def doctor_command(args: argparse.Namespace) -> int:
    root = find_root()
    problems = 0
    warnings = 0

    def ok(message: str) -> None:
        print(f"[ok] {message}")

    def warn(message: str) -> None:
        nonlocal warnings
        warnings += 1
        print(f"[warn] {message}")

    def fail(message: str) -> None:
        nonlocal problems
        problems += 1
        print(f"[fail] {message}")

    if (root / ".agent").is_dir():
        ok(".agent directory exists")
    else:
        fail(".agent directory is missing")

    git_check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if git_check.returncode == 0:
        ok("folder is inside a Git work tree")
    else:
        warn("folder is not a Git repository yet; run `git init` and add a remote before using `sync`")

    config_path = root / ".agent" / "config.json"
    registry_path = root / ".agent" / "tools" / "registry.json"
    for path in [config_path, registry_path]:
        try:
            read_json(path, {})
            ok(f"{rel(root, path)} is valid JSON")
        except Exception as exc:
            fail(f"{rel(root, path)} is invalid JSON: {exc}")

    config = load_config(root)
    for key, path_name in config.get("generated", GENERATED_PATHS).items():
        path = root / path_name
        if path.exists():
            ok(f"{path_name} exists")
        else:
            warn(f"{path_name} is missing; run `elephagent build`")

    registry = load_registry(root)
    for name, server in registry.get("mcpServers", {}).items():
        if server.get("type") in ("http", "streamable-http"):
            if not server.get("url"):
                fail(f"MCP server {name} is missing url")
        else:
            command = server.get("command")
            if not command:
                fail(f"MCP server {name} is missing command")
            elif shutil.which(command) is None:
                warn(f"MCP server {name} command is not on PATH: {command}")
            for key, value in server.get("env", {}).items():
                lowered = key.lower()
                if any(token in lowered for token in ["token", "secret", "password", "api_key", "apikey"]):
                    if not str(value).startswith("${"):
                        warn(f"MCP server {name} may contain a literal secret in env.{key}")

    print(f"Doctor finished with {problems} problem(s), {warnings} warning(s).")
    return 1 if problems else 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="elephagent.py",
        description="Git-synced agent memory and tool adapters for Codex, Claude Code, and Cursor.",
    )
    parser.add_argument("--version", action="version", version=f"elephagent {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create .agent/ and generated platform adapter files.")
    init.add_argument("--force", action="store_true", help="Overwrite existing managed source files.")
    init.add_argument("--no-build", action="store_true", help="Skip rendering platform adapter files.")
    init.set_defaults(func=init_command)

    build = sub.add_parser("build", help="Render platform adapter files from .agent/.")
    build.set_defaults(func=build_command)

    remember = sub.add_parser("remember", help="Append a durable note to shared agent memory.")
    remember.add_argument("note", nargs="+")
    remember.add_argument("--topic", default="log", help="log, decisions, workflows, pitfalls, glossary, or a custom file stem.")
    remember.add_argument("--no-build", action="store_true", help="Skip rendering platform adapter files.")
    remember.set_defaults(func=remember_command)

    skill = sub.add_parser("skill", help="Manage shared agent skills.")
    skill_sub = skill.add_subparsers(dest="skill_command", required=True)

    skill_add = skill_sub.add_parser("add", help="Create a new skill in .agent/skills/ and generate platform files.")
    skill_add.add_argument("name", help="Skill name (e.g. remember).")
    skill_add.add_argument("--force", action="store_true", help="Overwrite existing skill file.")
    skill_add.add_argument("--no-build", action="store_true", help="Skip rendering platform adapter files.")
    skill_add.set_defaults(func=skill_add_command)

    tool = sub.add_parser("tool", help="Manage shared MCP tool registry.")
    tool_sub = tool.add_subparsers(dest="tool_command", required=True)

    tool_add = tool_sub.add_parser("add", help="Add or replace an MCP server in .agent/tools/registry.json.")
    tool_add.add_argument("name")
    tool_add.add_argument("--command", help="Stdio server command.")
    tool_add.add_argument("--arg", action="append", help="Argument for stdio server command. Repeat for multiple args.")
    tool_add.add_argument("--env", action="append", help="Static env pair KEY=VALUE. Avoid secrets here.")
    tool_add.add_argument("--env-var", action="append", help="Environment variable name to forward by reference.")
    tool_add.add_argument("--url", help="HTTP MCP server URL.")
    tool_add.add_argument("--bearer-token-env-var", help="Environment variable used as HTTP bearer token.")
    tool_add.add_argument("--no-build", action="store_true")
    tool_add.set_defaults(func=tool_add_command)

    tool_list_parser = tool_sub.add_parser("list", help="List registered MCP servers.")
    tool_list_parser.set_defaults(func=tool_list_command)

    sync = sub.add_parser("sync", help="Build, commit, pull --rebase, and push agent memory/tool changes.")
    sync.add_argument("-m", "--message", help="Commit message.")
    sync.add_argument("--no-push", action="store_true", help="Commit locally without pushing.")
    sync.set_defaults(func=sync_command)

    doctor = sub.add_parser("doctor", help="Check the shared agent setup.")
    doctor.set_defaults(func=doctor_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
